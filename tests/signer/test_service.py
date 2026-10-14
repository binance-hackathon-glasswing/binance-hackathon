"""IDEA-047 S01-S05: signing requests through the database and the signer host service (real PostgreSQL)."""
from contextlib import redirect_stdout
from dataclasses import replace
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import traceback
from unittest.mock import patch

from larp.execution import Blocked, Conflict, Executor, Payload
from larp.execution_live import signing
from larp.execution_live.signing import RemoteSigner, request_document
from larp.execution_live.store import ExecutionStore
from larp.storage.postgres import IntegrityError, doc
from tests.execution.test_postgres_execution import ExecutionGuards
from tests.execution_fixtures import FakeDecoder, FakeVenue, ROUTER, TOKEN, finalized, intent
from tests.host_support import BUILD, synthetic_release
from tests.support import DatabaseCase

HAS_ETH = importlib.util.find_spec('eth_account') is not None


class RemoteFixture(RemoteSigner):
    mode = 'fake'  # the W04 Executor accepts fake capability bundles only; the port itself is the live one


class SigningCase(DatabaseCase):
    def setUp(self):
        if not HAS_ETH:
            self.skipTest('signer dependency not installed')
        super().setUp()
        from eth_account import Account
        self.account = Account.create()
        self.wallet = self.account.address.lower()
        self.execution = ExecutionStore(self.store, run_id='run', wallet=self.wallet)
        self.guards = ExecutionGuards(self.execution)
        self.venue = FakeVenue(self.execution)
        self.now, self.signer_now, self.ticks = 12, None, 0
        self.service = self.signer()
        self.remote = RemoteFixture(execution=self.execution, guards=self.guards, clock_s=lambda: self.now,
                                 sleep=self.pump, monotonic=self.tick, timeout_s=5, poll_s=1)
        self.executor = Executor(self.execution, self.guards, self.venue, self.remote, FakeDecoder())

    def signer(self, **kwargs):
        return signer_service(self, **kwargs)

    def tick(self):
        self.ticks += 1
        return self.ticks

    def pump(self, seconds):
        self.service.once()

    def authorized(self, **changes):
        i = intent(wallet=self.wallet, **changes)
        self.executor.create(i, 10)
        self.executor.prepare(i.key, 11)
        state = self.executor.authorize(i.key, 12)
        return state, state.attempts[-1]

    def request(self, state, attempt, gates=None, now=12, **changes):
        gates = gates or self.guards.snapshot(state.intent, now)
        value = {**request_document(state, attempt, gates, now), **changes}
        return signing.submit(self.store, value), value

    def signatures(self):
        with self.store.transaction() as db:
            return db.execute('SELECT attempt_id,signed FROM execution_signatures ORDER BY 1').fetchall()

    def refusals(self):
        with self.store.transaction() as db:
            return dict(db.execute('SELECT request_id,reason FROM signing_refusals').fetchall())

    def assert_refusal(self, request_id, fragment):
        self.service.once()
        self.assertEqual(self.signatures(), [])
        self.assertIn(fragment, self.refusals()[request_id])


def signer_service(case, **kwargs):
    from larp.signer.service import SignerService
    return SignerService(store=case.store, run_id='run', wallet=case.wallet,
                         credentials=dict(WALLET_PRIVATE_KEY=case.account.key.hex()),
                         clock_s=lambda: case.now if case.signer_now is None else case.signer_now, **kwargs)


class SigningProtocol(SigningCase):
    def test_s03_approve_signed_once_through_the_executor_and_verifies(self):
        state, attempt = self.authorized()
        self.now = 13
        signed = self.executor.sign(state.intent.key, 13).attempts[-1]
        self.assertEqual(signed.state, 'SIGNED_DURABLE')
        from larp.signer.local import verify
        stored = self.execution.lookup(attempt.attempt_id, attempt.payload.hash)
        self.assertTrue(verify(attempt.payload, stored))
        self.assertEqual((signed.raw_hex, signed.tx_hash), (stored.raw_hex, stored.tx_hash))
        from eth_account import Account
        self.assertEqual(Account.recover_transaction(stored.raw_hex).lower(), self.wallet)
        before = self.signatures()
        # A second pass, a restarted signer and a duplicate request change nothing.
        self.assertEqual(self.service.once(), 0)
        self.service = self.signer()
        self.assertEqual(self.service.once(), 0)
        with self.store.transaction() as db:
            request_id, raw = db.execute('SELECT request_id,request FROM signing_requests').fetchone()
        self.assertEqual(signing.submit(self.store, json.loads(bytes(raw))), request_id)
        self.assertEqual(self.service.once(), 0)
        self.assertEqual(self.signatures(), before)
        self.assertEqual(self.refusals(), {})
        # The executor's port returns the stored bytes without a new request.
        self.assertEqual(self.remote.sign(attempt.attempt_id, attempt.payload, attempt.epoch, attempt.guard_version),
                         stored)

    def test_s02_timeout_and_refusal_reach_the_caller(self):
        state, attempt = self.authorized()
        self.remote.sleep = lambda s: None
        with self.assertRaisesRegex(Blocked, 'signer timeout'):
            self.remote.sign(attempt.attempt_id, attempt.payload, attempt.epoch, attempt.guard_version)
        self.signer_now = 500  # the signer's clock is past the gate window
        self.remote.sleep = self.pump
        with self.assertRaisesRegex(Blocked, 'signer refused: .*stale/expired'):
            self.remote.sign(attempt.attempt_id, attempt.payload, attempt.epoch, attempt.guard_version)
        self.signer_now = None  # a fresh request for the same attempt is answered
        self.now = 13
        stored = self.remote.sign(attempt.attempt_id, attempt.payload, attempt.epoch, attempt.guard_version)
        self.assertEqual(len(self.signatures()), 1)
        self.assertTrue(self.remote.verify(attempt.payload, stored))
        with self.assertRaisesRegex(Blocked, 'does not match'):
            self.remote.sign(attempt.attempt_id, replace(attempt.payload, nonce=7), attempt.epoch,
                             attempt.guard_version)

    def test_s01_requests_are_immutable_and_bound_to_one_payload(self):
        state, attempt = self.authorized()
        request_id, value = self.request(state, attempt)
        self.assertEqual(signing.submit(self.store, value), request_id)  # identical re-send: no-op
        other = {**value, 'payload_hash': 'f' * 64}
        with self.assertRaises(Conflict):
            signing.submit(self.store, other)
        with self.assertRaises(IntegrityError):  # the database itself refuses another payload for the attempt
            with self.store.transaction() as db:
                db.execute('INSERT INTO signing_requests VALUES(%s,%s,%s,%s,%s,%s)',
                           ('x' * 64, 'run', attempt.attempt_id, 'f' * 64, b'{}', 12))
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM signing_requests').fetchone()[0], 1)


class SignerRefusals(SigningCase):
    def test_s04_quarantined_or_fenced_run(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, attempt)
        self.store.quarantine('run')
        self.assert_refusal(request_id, 'Quarantined or stale owner')

    def test_s04_fenced_to_another_epoch(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, attempt)
        self.store.takeover('run', self.epoch, offline=True)
        self.assert_refusal(request_id, 'stale owner')

    def test_s04_unknown_attempt(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, replace(attempt, attempt_id='not-registered'))
        self.assert_refusal(request_id, 'unknown registered execution attempt')

    def test_s04_aborted_attempt(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, attempt)
        self.executor.abort_unbroadcast(state.intent.key, 13)
        self.assert_refusal(request_id, 'not the active step')

    def test_s04_payload_hash_differs_from_the_attempt(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, replace(attempt, payload=replace(attempt.payload, gas=1)))
        self.assert_refusal(request_id, 'does not match the registered attempt')

    def test_s04_authority_differs_from_the_attempt(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, replace(attempt, epoch=attempt.epoch + 1,
                                                    guard_version=attempt.guard_version + 1))
        self.assert_refusal(request_id, 'stale signing authority')

    def test_s04_gate_window_or_intent_expired_by_the_signer_clock(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, attempt)
        self.signer_now = 43  # gates expire at observed + 30
        self.assert_refusal(request_id, 'stale/expired')
        gates = replace(self.guards.snapshot(state.intent, 12), expires_at=5000)
        request_id, _ = self.request(state, attempt, gates=gates)
        self.signer_now = 1000  # intent valid_until
        self.assert_refusal(request_id, 'stale/expired')

    def test_s04_signer_clock_behind_the_request(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, attempt)
        self.signer_now = 9  # observed at 12, two seconds of skew allowed
        self.assert_refusal(request_id, 'clock is behind')

    def test_s04_nonce_differs_from_the_payload(self):
        state, attempt = self.authorized()
        gates = replace(self.guards.snapshot(state.intent, 12), nonce=5)
        request_id, _ = self.request(state, attempt, gates=gates)
        self.assert_refusal(request_id, 'nonce mismatch')

    def test_s04_allow_list_is_enforced_on_the_signer(self):
        """A compromised primary authorizes a bad approve; the signer's own validate_payload refuses it."""
        cases = {
            'spender': lambda i, n: Payload(56, i.wallet, i.pay_token, 0, n, 100000, 1,
                                            '0x095ea7b3' + '0' * 24 + TOKEN[2:] + format(i.amount, '064x')),
            'amount': lambda i, n: Payload(56, i.wallet, i.pay_token, 0, n, 100000, 1,
                                           '0x095ea7b3' + '0' * 24 + ROUTER[2:] + format(i.amount + 1, '064x')),
            'destination': lambda i, n: Payload(56, i.wallet, ROUTER, 0, n, 100000, 1,
                                                '0x095ea7b3' + '0' * 24 + ROUTER[2:] + format(i.amount, '064x')),
            'selector': lambda i, n: Payload(56, i.wallet, i.pay_token, 0, n, 100000, 1,
                                             '0xa9059cbb' + '0' * 24 + ROUTER[2:] + format(i.amount, '064x')),
        }
        for number, (name, build) in enumerate(cases.items()):
            with self.subTest(name=name):
                self.venue.approve = build
                with patch('larp.execution.validate_payload'):
                    state, attempt = self.authorized(intent_id=f'bad-{number}')
                request_id, _ = self.request(state, attempt)
                self.service.once()
                self.assertEqual(self.signatures(), [])
                self.assertIn(request_id, self.refusals())
                self.executor.abort_unbroadcast(state.intent.key, 13)

    def test_s04_swap_needs_a_verified_decoder(self):
        state, attempt = self.authorized()
        self.now = 13
        self.executor.sign(state.intent.key, 13)
        sent = self.executor.broadcast(state.intent.key, 14).attempts[-1]
        self.venue.outcomes[sent.tx_hash] = finalized(sent, sender=self.wallet)
        self.executor.reconcile(state.intent.key, 17)
        self.guards.nonce = 1
        self.executor.prepare(state.intent.key, 18)
        state = self.executor.authorize(state.intent.key, 19)
        swap = state.attempts[-1]
        self.assertEqual(swap.step, 'SWAP')
        request_id, _ = self.request(state, swap, now=19)
        self.now = 19
        self.service.once()
        self.assertIn('verified router', self.refusals()[request_id])
        self.assertEqual(len(self.signatures()), 1)  # the approval only
        # The decoder is the only barrier: with one, the same swap is signed.
        self.service = self.signer(decoder=FakeDecoder())
        request_id, _ = self.request(state, swap, now=20)
        self.now = 20
        self.service.once()
        self.assertEqual(len(self.signatures()), 2)

    def test_r2_mistyped_gates_are_refused_and_the_cycle_continues(self):
        """IDEA-047 R2: a malformed request is refused; the next valid one is signed in the same cycle."""
        state, attempt = self.authorized()
        good = self.guards.snapshot(state.intent, 12)
        bad = {}
        for name, change in (('observed_at', '12'), ('expires_at', None), ('epoch', True), ('state_version', 1.0),
                             ('nonce', '7'), ('risk_valid', 1)):
            bad[name], _ = self.request(state, attempt, gates=replace(good, **{name: change}))
        valid, _ = self.request(state, attempt, gates=good)
        self.service.once()
        refusals = self.refusals()
        for name, request_id in bad.items():
            with self.subTest(field=name):
                self.assertIn('malformed signing request', refusals[request_id])
        self.assertNotIn(valid, refusals)
        self.assertEqual([row[0] for row in self.signatures()], [attempt.attempt_id])

    def test_r2_an_unexpected_data_error_is_a_refusal_but_an_outage_is_not(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, attempt)
        with patch('larp.signer.service.validate_sequence', side_effect=TypeError('shape')):
            self.service.once()
        self.assertEqual(self.refusals()[request_id], 'malformed signing request: TypeError')
        from larp.storage.postgres import Unavailable
        other, _ = self.request(state, attempt, gates=replace(self.guards.snapshot(state.intent, 12), observed_at=13))
        with patch.object(type(self.service), '_sign', side_effect=Unavailable('database down')):
            with self.assertRaises(Unavailable):
                self.service.once()
        self.assertNotIn(other, self.refusals())

    def test_s04_another_runs_request_is_never_answered(self):
        self.store.initialize('run2', 'wallet-2', 56, doc(dict(balances=dict(USDT=1))))
        state, attempt = self.authorized()
        value = {**request_document(state, attempt, self.guards.snapshot(state.intent, 12), 12), 'run_id': 'run2'}
        signing.submit(self.store, value)
        self.assertEqual(self.service.once(), 0)
        self.assertEqual((self.signatures(), self.refusals()), ([], {}))


class SignerCommand(SigningCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        keys = self.dir / 'keys'
        keys.mkdir(mode=0o700)
        self.key = keys / 'wallet.key'
        self.key.write_text(self.account.key.hex() + '\n')
        os.chmod(self.key, 0o600)
        dsn = self.dir / 'dsn'
        dsn.write_text(self.store._dsn)
        self.store.initialize('live-run', self.wallet, 56, doc(dict(balances=dict(USDT=1))), mode='dev')
        self.config = dict(schema='SignerService.v1', run_id='live-run', build_id=BUILD, mode='dev',
                           wallet_address=self.wallet, key_file=str(self.key), interval_seconds=1,
                           database_dsn_file=str(dsn))

    def write(self, config=None, pin=True):
        raw = json.dumps(config or self.config).encode()
        path = self.dir / 'signer.json'
        path.write_bytes(raw)
        root, manifest = synthetic_release(self.tmp.name, {'signer': raw} if pin else {})
        return ['--config', str(path), '--manifest', str(manifest), '--root', str(root)]

    def main(self, command, args, **kwargs):
        from larp.signer.service import main
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([command] + args, sleep=lambda s: None, **kwargs)
        return code, out.getvalue()

    def unquarantine(self):
        import psycopg
        with psycopg.connect(self.store._dsn) as db:
            db.execute("UPDATE runs SET quarantined=false WHERE run_id='live-run'")

    def test_s05_check_and_run(self):
        self.assertEqual(self.main('check', self.write())[0], 0)
        code, out = self.main('run', self.write(), max_cycles=1)
        self.assertEqual((code, json.loads(out)['reason']), (3, 'QUARANTINED'))  # new runs start quarantined
        self.unquarantine()
        code, out = self.main('run', self.write(), max_cycles=2)
        self.assertEqual(code, 0)
        self.assertIn('"signing_enabled": true', out)

    def test_s05_refusals_exit_4_without_key_material(self):
        marker = self.account.key.hex()[2:]
        cases = {
            'unpinned config': (self.config, False),
            'offline mode': ({**self.config, 'mode': 'offline'}, True),
            'secret id': ({**self.config, 'runtime_secret_id': 'x'}, True),
            'key value': ({**self.config, 'wallet_private_key': marker}, True),
            'two key sources': ({**self.config, 'key_credential': 'wallet-key'}, True),
            'other build': ({**self.config, 'build_id': 'c' * 40}, True),
            'runtime database role': ({k: v for k, v in self.config.items() if k != 'database_dsn_file'} | dict(
                database_host='h', database_user='larp_runtime', database_name='larp', database_ca_file='/x',
                database_ca_sha256='0', region='ap-southeast-2'), True),
        }
        for name, (config, pin) in cases.items():
            with self.subTest(name=name):
                code, out = self.main('run', self.write(config, pin))
                self.assertEqual(code, 4)
                self.assertIn('START_REFUSED', out)
                self.assertNotIn(marker, out)
        self.unquarantine()
        for name, config in {'wallet differs from the run': {**self.config, 'wallet_address': '0x' + '9' * 40},
                             'mode differs from the run': {**self.config, 'mode': 'live'}}.items():
            with self.subTest(name=name):
                self.assertEqual(self.main('run', self.write(config))[0], 4)
        os.chmod(self.key, 0o640)
        code, out = self.main('run', self.write())
        self.assertEqual((code, json.loads(out)['reason']), (4, 'KEY_REFUSED'))
        self.assertNotIn(marker, out)
        os.chmod(self.key, 0o600)
        from eth_account import Account
        self.key.write_text(Account.create().key.hex())  # a key for another wallet
        code, out = self.main('run', self.write())
        self.assertEqual((code, json.loads(out)['reason']), (4, 'KEY_REFUSED'))

    def test_s05_systemd_credential_directory(self):
        config = {k: v for k, v in self.config.items() if k != 'key_file'} | dict(key_credential='wallet.key')
        self.unquarantine()
        args = self.write(config)
        code, out = self.main('run', args, max_cycles=1, environ={})
        self.assertEqual((code, json.loads(out)['reason']), (4, 'KEY_REFUSED'))
        code, out = self.main('run', args, max_cycles=1, environ={'CREDENTIALS_DIRECTORY': str(self.key.parent)})
        self.assertEqual(code, 0, out)

    def test_s05_failure_output_has_no_key_material(self):
        marker = self.account.key.hex()[2:]
        self.unquarantine()
        with patch('larp.signer.service.SignerService.once', side_effect=RuntimeError(marker)):
            code, out = self.main('run', self.write(), max_cycles=1)
        self.assertEqual((code, json.loads(out.splitlines()[-1])['reason']), (1, 'SIGNER_FAILED'))
        self.assertNotIn(marker, out)


import tests.runtime.test_anchors_roles as roles  # noqa: E402  (module import: its TestCases are not re-collected)


class SigningRoles(SigningCase):
    """The same flow as the real database roles: the execution service asks, the signer answers (S01)."""

    def setUp(self):
        super().setUp()
        import psycopg
        script = (roles.ROOT / 'deploy/postgres/roles.sql').read_text()
        with psycopg.connect(self.store._dsn) as db:
            if not db.execute("SELECT 1 FROM pg_roles WHERE rolname='rds_iam'").fetchone():
                db.execute('CREATE ROLE rds_iam')
            database = db.execute('SELECT current_database()').fetchone()[0]
            db.execute(script.replace('ON DATABASE larp ', 'ON DATABASE ' + database + ' ')
                       .replace('SCHEMA public ', 'SCHEMA ' + self.schema + ' '))
        self.as_role = {r: roles.RoleStore(self.store._dsn, r)
                        for r in ('larp_runtime', 'larp_execution', 'larp_signer', 'larp_archive')}
        self.execution = ExecutionStore(self.as_role['larp_execution'], run_id='run', wallet=self.wallet)
        self.guards = ExecutionGuards(self.execution)
        self.venue = FakeVenue(self.execution)
        self.remote = RemoteFixture(execution=self.execution, guards=self.guards, clock_s=lambda: self.now,
                                    sleep=self.pump, monotonic=self.tick, timeout_s=5, poll_s=1)
        self.executor = Executor(self.execution, self.guards, self.venue, self.remote, FakeDecoder())
        from larp.signer.service import SignerService
        self.service = SignerService(store=self.as_role['larp_signer'], run_id='run', wallet=self.wallet,
                                     credentials=dict(WALLET_PRIVATE_KEY=self.account.key.hex()),
                                     clock_s=lambda: self.now if self.signer_now is None else self.signer_now)

    def refused_as(self, role, *statements):
        from larp.storage.postgres import Unavailable
        for sql in statements:
            with self.subTest(role=role, sql=sql), self.assertRaises(Unavailable):
                with self.as_role[role].transaction() as db:
                    db.execute(sql)

    def test_s01_grants_suffice_for_signing_and_refusing(self):
        state, attempt = self.authorized()
        self.signer_now = 5
        with self.assertRaisesRegex(Blocked, 'signer refused: signer clock is behind'):
            self.remote.sign(attempt.attempt_id, attempt.payload, attempt.epoch, attempt.guard_version)
        self.signer_now, self.now = None, 13
        self.assertEqual(self.executor.sign(state.intent.key, 13).attempts[-1].state, 'SIGNED_DURABLE')
        self.assertEqual(len(self.signatures()), 1)

    def test_s01_requests_and_refusals_are_append_only_and_role_bound(self):
        state, attempt = self.authorized()
        request_id, _ = self.request(state, attempt)
        self.signer_now = 5
        self.service.once()
        self.refused_as('larp_signer', "INSERT INTO signing_attempts VALUES('a','run','k','p')",
                     "INSERT INTO signing_requests VALUES('r','run','a','p','\\x00',1)",
                     "UPDATE signing_refusals SET reason='x'", 'DELETE FROM signing_refusals',
                     'DELETE FROM signing_requests', "UPDATE signing_requests SET requested_s=0")
        self.refused_as('larp_execution', "INSERT INTO signing_refusals VALUES('%s','run','x',1)" % request_id,
                     "UPDATE signing_requests SET requested_s=0", 'DELETE FROM signing_requests',
                     "UPDATE signing_attempts SET payload_hash='x'", 'DELETE FROM signing_refusals')
        self.refused_as('larp_runtime', 'SELECT * FROM signing_requests', 'SELECT * FROM signing_refusals')
        from larp.storage.backup import select_sql
        with self.as_role['larp_archive'].transaction() as db:  # the daily backup exports all three
            for table in ('signing_attempts', 'signing_requests', 'signing_refusals'):
                self.assertEqual(len(db.execute(*select_sql(db, table)).fetchall()), 1)

"""IDEA-047 U01: the uploader service delivers committed round logs with the audit secret only."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import traceback
import unittest
from unittest.mock import patch

from larp.audit.delivery import DeliveryWorker
from larp.audit.protocol import sign
from larp.audit.service import Secret, SecretUnavailable, StartRefused, Uploader, load_uploader_secret, main
from larp.runtime.fixtures import FakeReceiver
from larp.storage.postgres import doc
from tests.audit.test_protocol import event
from tests.host_support import BUILD, synthetic_release
from tests.support import DatabaseCase

WALLET = '0x' + 'a' * 40
SECRET = 'e' * 64


class Client:
    def __init__(self, values):
        self.values = values

    def get_secret_value(self, SecretId):
        if isinstance(self.values, Exception):
            raise self.values
        return dict(SecretString=json.dumps(self.values))


class SecretLoading(unittest.TestCase):
    def test_only_the_audit_secret_is_accepted(self):
        self.assertEqual(load_uploader_secret(Client(dict(AI_SEEDS_SECRET=SECRET)), 'id', WALLET), SECRET)
        self.assertEqual(load_uploader_secret(Client(dict(AI_SEEDS_SECRET=SECRET, AI_SEEDS_ADDRESS=WALLET.upper()
                                                          .replace('0X', '0x'))), 'id', WALLET), SECRET)
        for values in (dict(AI_SEEDS_SECRET=SECRET, WALLET_PRIVATE_KEY='1' * 64),
                       dict(AI_SEEDS_SECRET=SECRET, BINANCE_SECRET_KEY='x'),
                       dict(AI_SEEDS_SECRET='short'), {}, dict(AI_SEEDS_SECRET=SECRET, AI_SEEDS_ADDRESS='0x' + 'b' * 40),
                       ['not', 'an', 'object'], RuntimeError('provider text ' + SECRET)):
            with self.subTest(values=values if isinstance(values, Exception) else sorted(values)):
                try:
                    load_uploader_secret(Client(values), 'id', WALLET)
                except Exception:
                    self.assertNotIn(SECRET, traceback.format_exc())
                else:
                    self.fail('accepted')

    def test_secret_repr_hides_the_value_but_signs_with_it(self):
        secret = Secret(SECRET)
        self.assertNotIn(SECRET, repr(secret) + str(secret) + f'{secret}')
        self.assertEqual(sign(secret, 'PUT', '/p', 1, 'n', WALLET, b'{}'), sign(SECRET, 'PUT', '/p', 1, 'n', WALLET, b'{}'))

    def test_r14_fetch_failures_are_retryable_and_hide_provider_text(self):
        for error in (TimeoutError(SECRET), RuntimeError('provider credential ' + SECRET)):
            with self.subTest(kind=type(error).__name__):
                try:
                    load_uploader_secret(Client(error), 'synthetic-id', WALLET)
                except SecretUnavailable:
                    self.assertNotIn(SECRET, traceback.format_exc())
                else:
                    self.fail('fetch failure was not retryable')

    def test_r14_malformed_provider_response_is_a_permanent_refusal(self):
        for response in ({}, {'SecretString': None}, {'SecretString': b'bytes'}, []):
            with self.subTest(response=response), patch.object(Client, 'get_secret_value', return_value=response):
                with self.assertRaises(StartRefused):
                    load_uploader_secret(Client({}), 'synthetic-id', WALLET)


class UploaderFetchRestart(unittest.TestCase):
    def test_r14_pinned_release_fetch_failure_exits_1_before_opening_database(self):
        with tempfile.TemporaryDirectory() as directory:
            config = dict(schema='UploaderService.v1', run_id='synthetic-run', build_id=BUILD, mode='dev',
                          wallet_address=WALLET, uploader_secret_id='synthetic-id', region='ap-southeast-2',
                          interval_seconds=1, database_dsn_file='/synthetic/not-contacted')
            raw = json.dumps(config).encode()
            path = Path(directory) / 'uploader.json'
            path.write_bytes(raw)
            root, manifest = synthetic_release(directory, {'uploader': raw})
            args = ['run', '--config', str(path), '--manifest', str(manifest), '--root', str(root)]
            for error in (TimeoutError(SECRET), RuntimeError('throttle ' + SECRET)):
                with self.subTest(kind=type(error).__name__), patch('larp.runtime.database.open_service_store') as db:
                    out = io.StringIO()
                    with redirect_stdout(out):
                        code = main(args, client_factory=lambda region: Client(error), max_cycles=1)
                    self.assertEqual(code, 1)
                    self.assertEqual(json.loads(out.getvalue())['reason'], 'UPLOADER_FAILED')
                    self.assertNotIn(SECRET, out.getvalue())
                    db.assert_not_called()


class UploaderDelivery(DatabaseCase):
    def test_u01_drains_due_chunks_and_follows_the_owner_epoch(self):
        for identity in ('e1', 'e2'):
            self.store.commit(self.batch(identity, audit=[event(identity, identity)]))
        receiver = FakeReceiver()
        uploader = Uploader(self.store, 'run', 'wallet', DeliveryWorker(self.store, receiver, retry_ms=1), batch=1)
        self.assertEqual(uploader.once(100), 1)  # bounded per cycle
        self.store.takeover('run', self.epoch, offline=True)  # a new owner: the uploader follows it
        self.assertEqual(uploader.once(101), 1)
        self.assertEqual(uploader.once(102), 0)
        self.assertEqual(len(receiver.stored), 2)
        self.assertEqual(self.store.metrics('run').read()['audit_pending'], 0)

    def test_u01_keeps_delivering_while_quarantined(self):
        self.store.commit(self.batch(audit=[event()]))
        self.store.quarantine('run')
        receiver = FakeReceiver()
        self.assertEqual(Uploader(self.store, 'run', 'wallet', DeliveryWorker(self.store, receiver)).once(100), 1)
        self.assertEqual(len(receiver.stored), 1)


class UploaderCommand(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        dsn = Path(self.tmp.name) / 'dsn'
        dsn.write_text(self.store._dsn)
        self.store.initialize('live-run', WALLET, 56, doc(dict(balances=dict(USDT=1))), mode='dev')
        self.config = dict(schema='UploaderService.v1', run_id='live-run', build_id=BUILD, mode='dev',
                           wallet_address=WALLET, uploader_secret_id='larp/uploader', region='ap-southeast-2',
                           interval_seconds=1, database_dsn_file=str(dsn))
        self.received = []

    def args(self, config=None, pin=True):
        raw = json.dumps(config or self.config).encode()
        path = Path(self.tmp.name) / 'uploader.json'
        path.write_bytes(raw)
        root, manifest = synthetic_release(self.tmp.name, {'uploader': raw} if pin else {})
        return ['--config', str(path), '--manifest', str(manifest), '--root', str(root)]

    def run_main(self, command, args, values=None):
        def receiver(address, secret):
            self.received.append((address, secret))
            return FakeReceiver()
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([command] + args, client_factory=lambda region: Client(values or dict(AI_SEEDS_SECRET=SECRET)),
                        receiver_factory=receiver, sleep=lambda s: None, max_cycles=2)
        return code, out.getvalue()

    def test_u01_check_and_run(self):
        self.assertEqual(self.run_main('check', self.args())[0], 0)
        code, out = self.run_main('run', self.args())
        self.assertEqual(code, 0, out)
        self.assertEqual(self.received, [(WALLET, SECRET)])
        self.assertNotIn(SECRET, out)

    def test_r14_failed_fetch_then_restart_delivers_committed_log(self):
        from larp.audit.protocol import build_event
        audit = build_event(event_id='evt-r14', round_id='round-r14', version_id='synthetic', decision_ids=[],
                            address=WALLET, timestamp_ms=100, input_record={'synthetic': True},
                            rationale='synthetic hold', output='HOLD', orders=[])
        # Seed a committed outbox fixture without activating the dev-mode run. Uploads must also drain while
        # quarantined; no coordinator or signing authority is needed to reproduce the startup-fetch failure.
        e = audit.read()
        with self.store.transaction() as db:
            db.execute('INSERT INTO audit_events VALUES(%s,%s,%s,%s,%s)',
                       ('live-run', e['event_id'], e['round_id'], audit.payload, e['timestamp_ms']))
            for index, body in enumerate(e['chunks']):
                db.execute('INSERT INTO audit_chunks(run_id,event_id,chunk_index,body) VALUES(%s,%s,%s,%s)',
                           ('live-run', e['event_id'], index, body.encode()))
        args = self.args()
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(['run', *args], client_factory=lambda region: Client(TimeoutError(SECRET)), max_cycles=1)
        self.assertEqual(code, 1)
        self.assertNotIn(SECRET, out.getvalue())
        self.assertEqual(self.store.metrics('live-run').read()['audit_pending'], 1)
        code, out = self.run_main('run', args)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.store.metrics('live-run').read()['audit_pending'], 0)

    def test_u01_refusals_exit_4_without_secrets(self):
        cases = {
            'unpinned config': (self.config, False),
            'offline mode': ({**self.config, 'mode': 'offline'}, True),
            'runtime secret id': ({**self.config, 'runtime_secret_id': 'larp/runtime'}, True),
            'wallet key file': ({**self.config, 'key_file': '/etc/larp/signer/wallet.key'}, True),
            'other build': ({**self.config, 'build_id': 'c' * 40}, True),
            # IDEA-047 R1: an attempt cap would latch a delivery HALT; an old config cannot keep it.
            'max_attempts cap': ({**self.config, 'max_attempts': 8}, True),
            'backoff below retry': ({**self.config, 'retry_ms': 30000, 'max_backoff_ms': 1000}, True),
            'signer database role': ({k: v for k, v in self.config.items() if k != 'database_dsn_file'} | dict(
                database_host='h', database_user='larp_signer', database_name='larp', database_ca_file='/x',
                database_ca_sha256='0'), True),
        }
        for name, (config, pin) in cases.items():
            with self.subTest(name=name):
                code, out = self.run_main('run', self.args(config, pin))
                self.assertEqual((code, json.loads(out)['reason']), (4, 'START_REFUSED'))
        code, out = self.run_main('run', self.args(), dict(AI_SEEDS_SECRET=SECRET, WALLET_MNEMONIC='w ' * 12))
        self.assertEqual((code, json.loads(out)['reason']), (4, 'START_REFUSED'))
        self.assertNotIn(SECRET, out)
        self.assertNotIn('w w w', out)
        code, out = self.run_main('run', self.args({**self.config, 'wallet_address': '0x' + 'c' * 40}))
        self.assertEqual((code, json.loads(out.splitlines()[-1])['reason']), (4, 'START_REFUSED'))
        self.assertEqual(self.received[-1][0], '0x' + 'c' * 40)  # refused at the first cycle: run wallet differs

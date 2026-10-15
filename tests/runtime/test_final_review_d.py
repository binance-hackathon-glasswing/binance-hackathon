"""IDEA-049 final review D: runtime, release and hosting requirements (D-REQ-003/018/023/035/055/059/062/070/076/
085/103/105/111/135).

Criteria pre-registered in docs/ledger/IDEA-049-D.md §4.2 before these tests ran. Real PostgreSQL where a store is
involved; fakes only at external boundaries (receiver, S3, Secrets Manager, venue/chain, downloads).
"""

import base64
import hashlib
import json
import re
import subprocess
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.execution import canonical as execution_canonical, digest as execution_digest
from larp.runtime.coordinator import halt_reasons
from larp.runtime.maintenance import HOUR_MS, Maintenance
from larp.runtime.supervision import Guard, Sessions
from larp.storage.archive import S3Archive
from larp.storage.backup import export
import tests.execution.test_section_c_signed_state as execution_state_tests
import tests.runtime.test_release_bundle as bundle_tests
import tests.runtime.test_round_driver_service as service_tests
from tests.runtime.test_round_driver_service import RUN, SECOND, Execution, FencedVenue
from tests.storage.test_archive import FakeS3
from tests.support import DatabaseCase

ROOT = Path(__file__).resolve().parents[2]
DAY_MS = 86_400_000


# --- D-REQ-003 / 018: a broadcast swap reaches its round log before finality (#28) -------------------------------

class SwapStaysUnconfirmed(FencedVenue):
    """The approval finalizes; the swap stays UNKNOWN until `swap_final` is set."""

    swap_final = False

    def outcome(self, tx_hash):
        a = self.attempt(tx_hash)
        if a is not None and a.step == 'SWAP' and not self.swap_final:
            return super(FencedVenue, self).outcome(tx_hash)
        return super().outcome(tx_hash)


class PendingBroadcast(service_tests.ServiceHarness):
    def audit_events(self, round_id):
        with self.store.transaction() as db:
            return [Document(bytes(r[0])).read() for r in db.execute(
                'SELECT document FROM audit_events WHERE run_id=%s AND round_id=%s', (RUN, round_id))]

    def journal_kinds(self):
        return [b.read()['event']['kind'] for b in self.store.journal(RUN)]

    def test_d_req_003_a_broadcast_swap_is_logged_before_finality(self):
        driver = self.service_driver()
        with patch.object(service_tests, 'FencedVenue', SwapStaysUnconfirmed):
            execution = Execution(self, remote=False)
        venue = execution.venue
        driver.once(self.w.clock())
        [round_id] = self.planned()

        def swap_broadcast():
            return any(a.step == 'SWAP' and a.broadcast_at is not None
                       for k in self.keys() for a in execution.registry.load(k).attempts)
        self.assertTrue(self.run_both(driver, execution, until=swap_broadcast))
        for _ in range(3):  # the swap stays unconfirmed; the runtime ingests the broadcast fact and logs the round
            self.w.clock.now += SECOND
            execution.once(self.w.clock())
            driver.once(self.w.clock())
        swap = venue.broadcasts[-1]
        events = self.audit_events(round_id)
        self.assertEqual(len(events), 1, 'a broadcast swap must reach a round log before its receipt is final')
        orders = json.loads(events[0]['log'])['data']['orders']
        self.assertEqual([o.get('tx_hash') for o in orders], [swap])
        # D-RV-01: a log closes the SQL row, but settlement still owns a logically open round.
        self.assertIn(round_id, dict(self.store.open_rounds(RUN)))
        self.assertEqual(self.store.metrics(RUN).read()['open_rounds'], 1)
        facts = [b.read()['event']['observation']['kind'] for b in self.store.journal(RUN)
                 if b.read()['event']['kind'] == 'OBSERVATION']
        self.assertIn('BROADCAST_ATTEMPTED', facts)
        self.assertNotIn('FILL', facts)
        # Finality arrives later: settled into the journal, the round closes, and no second log is written.
        venue.swap_final = True
        self.assertTrue(self.run_both(driver, execution, until=lambda: self.closed(round_id)))
        self.assertEqual(len(self.audit_events(round_id)), 1)
        self.assertNotIn(round_id, dict(self.store.open_rounds(RUN)))
        self.assertEqual(self.store.metrics(RUN).read()['open_rounds'], 0)
        self.assertEqual(self.store.load(RUN).read()['projection']['portfolio']['positions']['NVDAB']['units'], 0)
        head, expected = self.replay_head(driver)
        self.assertEqual(head, expected)

    def test_d_req_018_an_unlogged_open_round_past_the_deadline_is_overdue(self):
        driver = self.service_driver()
        execution = Execution(self, remote=False)
        execution.venue.finalize = False  # nothing ever confirms: the intent never reaches a disposition
        driver.once(self.w.clock())
        [round_id] = self.planned()

        def approval_sent():
            return any(a.step == 'APPROVE' and a.broadcast_at is not None
                       for k in self.keys() for a in execution.registry.load(k).attempts)
        self.assertTrue(self.run_both(driver, execution, until=approval_sent))
        self.assertEqual(self.audit_events(round_id), [])
        started = self.store.load(RUN).read()['projection']['round_records'][round_id]['started_ms']
        after_deadline = (started // DAY_MS + 1) * DAY_MS + 2 * HOUR_MS + SECOND
        self.w.clock.now = after_deadline
        actions = Guard(self.store, RUN, max_failures=3, clear_after=1).evaluate(after_deadline)
        self.assertIn('HALT:DELIVERY_DEADLINE', actions)
        self.assertIn('DELIVERY_DEADLINE', halt_reasons(self.store.load(RUN).read()['projection']))


# --- D-REQ-070: a transient Secrets Manager failure restarts instead of refusing (#43) ----------------------------

class SecretStore:
    def __init__(self, error=None, secret=None):
        self.error, self.secret = error, secret

    def get_secret_value(self, SecretId):
        if self.error is not None:
            raise self.error
        return {'SecretString': self.secret}


class TransientSecrets(unittest.TestCase):
    VALUE = 's3cret-value'

    def errors(self):
        from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError
        transient = [ClientError({'Error': {'Code': code, 'Message': self.VALUE}}, 'GetSecretValue')
                     for code in ('ThrottlingException', 'InternalServiceError', 'ServiceUnavailable')]
        transient += [EndpointConnectionError(endpoint_url='https://secretsmanager.invalid'),
                      ReadTimeoutError(endpoint_url='https://secretsmanager.invalid'),
                      RuntimeError('unclassified failure carrying ' + self.VALUE)]
        definite = [ClientError({'Error': {'Code': code, 'Message': self.VALUE}}, 'GetSecretValue')
                    for code in ('ResourceNotFoundException', 'AccessDeniedException')]
        return transient, definite

    def test_d_req_070_transient_secret_errors_restart_and_definite_ones_refuse(self):
        from larp.runtime.credentials import load_runtime_secrets
        from larp.runtime.live import LiveStartRefused
        transient, definite = self.errors()
        for error in transient:
            with self.subTest(transient=type(error).__name__):
                with self.assertRaises(Exception) as caught:
                    load_runtime_secrets(SecretStore(error), 'larp/runtime')
                self.assertNotIsInstance(caught.exception, LiveStartRefused)
                self.assertNotIn(self.VALUE, str(caught.exception))
        for error in definite:
            with self.subTest(definite=error.response['Error']['Code']):
                with self.assertRaises(LiveStartRefused) as caught:
                    load_runtime_secrets(SecretStore(error), 'larp/runtime')
                self.assertNotIn(self.VALUE, str(caught.exception))
        with self.assertRaises(LiveStartRefused):
            load_runtime_secrets(SecretStore(secret='not json'), 'larp/runtime')

    def test_d_req_070_the_service_exits_restartable_on_a_transient_secret_error(self):
        import tempfile
        from larp.runtime import service
        from larp.runtime.credentials import load_runtime_secrets
        transient, _ = self.errors()
        try:
            load_runtime_secrets(SecretStore(transient[0]), 'larp/runtime')
        except Exception as error:  # whatever the loader raises for a throttled read
            raised = error
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'runtime.json'
            raw = json.dumps(dict(schema='RuntimeService.v1', run_id='r', build_id='a' * 40, max_failures=3,
                                  clear_after=2, interval_seconds=5, database_dsn_file='/synthetic')).encode()
            config.write_bytes(raw)
            (Path(directory) / 'manifest.json').write_bytes(b'{}')
            manifest = dict(build_id='a' * 40, runtime_config_sha256=hashlib.sha256(raw).hexdigest())
            with patch('larp.runtime.preflight.verify_release', return_value=manifest), \
                    patch('larp.runtime.service.open_store'), patch('larp.runtime.service.verify_registered_manifest'), \
                    patch('larp.runtime.credentials.runtime_secrets', side_effect=raised), patch('builtins.print'):
                code = service.main(['run', '--config', str(config), '--manifest', str(Path(directory) / 'manifest.json'),
                                     '--root', directory])
        self.assertEqual(code, 1)  # systemd restarts exit 1; it never restarts exit 4


# --- D-REQ-076: a hung cycle ends the process so the supervisor restarts it (#35) ---------------------------------

class HungDriver:
    def __init__(self, block):
        self.block, self.release, self.calls = block, threading.Event(), 0

    def once(self, now_ms):
        self.calls += 1
        if self.block:
            self.release.wait(5)
        return {}


class Watchdog(DatabaseCase):
    def service(self, driver, hung):
        from larp.runtime.service import Service

        def on_hang(code):
            with self.store.transaction() as db:
                open_sessions = db.execute('SELECT count(*) FROM process_sessions WHERE ended_ms IS NULL').fetchone()[0]
            hung.append((code, open_sessions))
            driver.release.set()
        clock = [1_000]

        def clock_ms():
            clock[0] += 1
            return clock[0]
        return Service(self.store, 'run', 'build-1', guard=Guard(self.store, 'run', max_failures=3, clear_after=1),
                       driver=driver, clock_ms=clock_ms, interval_s=0, sleep=lambda s: None,
                       cycle_timeout_s=0.2, on_hang=on_hang)

    def test_d_req_076_a_hung_cycle_exits_for_a_supervised_restart(self):
        hung = []
        driver = HungDriver(block=True)
        started = time.monotonic()
        self.service(driver, hung).run(max_cycles=1)
        self.assertEqual(hung, [(1, 1)])  # exit status 1 while the session is still open (a crash on restart)
        self.assertLess(time.monotonic() - started, 4)

    def test_d_req_076_a_cycle_that_finishes_in_time_never_triggers_it(self):
        hung = []
        driver = HungDriver(block=False)
        self.service(driver, hung).run(max_cycles=5)
        time.sleep(0.3)
        self.assertEqual((hung, driver.calls), ([], 5))

    def test_d_req_076_dev_and_live_configs_need_a_cycle_timeout(self):
        from larp.runtime.service import validate_config
        base = dict(schema='RuntimeService.v1', run_id='r', build_id='b', max_failures=3, clear_after=2,
                    interval_seconds=5, database_dsn_file='/synthetic')
        validate_config(dict(base))  # offline: optional
        for mode in ('dev', 'live'):
            with self.subTest(mode=mode):
                with self.assertRaises(ContractError):
                    validate_config(dict(base, mode=mode))
                for bad in (0, -1, None, 'x', float('nan')):
                    with self.assertRaises(ContractError):
                        validate_config(dict(base, mode=mode, cycle_timeout_seconds=bad))
                validate_config(dict(base, mode=mode, cycle_timeout_seconds=600))


# --- D-REQ-035 / 036 / 085: journal upload after an incident; superseded archive failures (#64.1) ----------------

class Archive(DatabaseCase):
    def worker(self, client=None, **kwargs):
        self.client = client or FakeS3()
        archive = S3Archive(self.client, bucket='fixture', account_id='123456789012',
                            kms_key='arn:synthetic:key', prefix='archive/development', retention_days=90)
        return Maintenance(self.store, archive, backup_interval_ms=24 * HOUR_MS, retry_ms=1000, **kwargs)

    def backups(self):
        with self.store.transaction() as db:
            return [r[0] for r in db.execute("SELECT slot_ms FROM archive_outbox WHERE kind='backup' ORDER BY 1")]

    def test_d_req_035_an_incident_triggers_an_extra_journal_upload(self):
        worker = self.worker()
        worker.prepare('run', 100)
        self.assertEqual(len(self.backups()), 1)
        Sessions(self.store, 'run').begin(session_id='s1', build_id='b', now_ms=200)
        Sessions(self.store, 'run').begin(session_id='s2', build_id='b', now_ms=300)  # s1 never ended: RESTART
        worker.prepare('run', HOUR_MS + 100)
        self.assertEqual(len(self.backups()), 2, 'an incident since the last backup triggers one more upload')
        worker.prepare('run', HOUR_MS + 200)
        worker.prepare('run', 2 * HOUR_MS + 100)
        self.assertEqual(len(self.backups()), 2, 'the same incident is uploaded once')
        Guard(self.store, 'run', max_failures=1, clear_after=1)._halt('REPEATED_FAILURES', 3 * HOUR_MS, {})
        worker.prepare('run', 3 * HOUR_MS + 100)
        self.assertEqual(len(self.backups()), 3)
        for _ in range(10):
            worker.once('run', 3 * HOUR_MS + 200)
        self.assertEqual(sum('/backup/' in k for k in self.client.objects), 3)

    def test_d_req_089_incident_backups_are_rate_limited_and_acked_payloads_released(self):
        worker = self.worker()
        worker.prepare('run', 100)
        for n in range(30):  # a crash loop: a RESTART incident every ~10 s, maintenance every minute
            Sessions(self.store, 'run').begin(session_id=f's{n}', build_id='b', now_ms=1_000 + n * 10_000)
            worker.prepare('run', 1_000 + n * 10_000 + 5_000)
        self.assertEqual(len(self.backups()), 2, 'at most one incident backup per hour')
        Sessions(self.store, 'run').begin(session_id='later', build_id='b', now_ms=HOUR_MS + 400_000)
        worker.prepare('run', HOUR_MS + 500_000)
        self.assertEqual(len(self.backups()), 3)
        for _ in range(10):
            worker.once('run', HOUR_MS + 600_000)
        with self.store.transaction() as db:
            rows = db.execute("SELECT status,length(payload),sha256,acknowledgement IS NOT NULL FROM archive_outbox "
                              "ORDER BY kind,slot_ms").fetchall()
        self.assertTrue(rows and all(status == 'ACK' and size == 0 and len(sha) == 64 and receipt
                                     for status, size, sha, receipt in rows), rows)
        self.assertTrue(worker.health('run', HOUR_MS + 600_000).read()['healthy'])

    def test_d_req_085_a_newer_ack_supersedes_an_exhausted_slot_in_archive_health(self):
        class Down:
            def put(self, *args, **kwargs):
                from larp.storage.postgres import Unavailable
                raise Unavailable('synthetic outage')
        down = Maintenance(self.store, Down(), backup_interval_ms=24 * HOUR_MS, max_attempts=1, retry_ms=1000)
        down.prepare('run', 100)
        for _ in range(4):
            down.once('run', 10_000)
        health = down.health('run', 10_000).read()
        self.assertIn('ARCHIVE_DELIVERY_BLOCKED', health['reasons'])  # still visible while nothing newer exists
        self.assertEqual(health['missed'], {'anchor': [0], 'backup': [0]})
        worker = self.worker()
        worker.prepare('run', DAY_MS + 100)  # the next hour's anchor and the next day's backup
        for _ in range(4):
            worker.once('run', DAY_MS + 200)
        health = worker.health('run', DAY_MS + 300).read()
        self.assertNotIn('ARCHIVE_DELIVERY_BLOCKED', health['reasons'])
        self.assertTrue(health['healthy'])
        self.assertEqual(health['missed'], {'anchor': [0], 'backup': [0]})  # still reported, never backfilled


# --- D-REQ-059: no live activation with OPEN or DRAFT deviations --------------------------------------------------

class LiveActivation(DatabaseCase):
    WALLET = '0x' + '5' * 40

    def setUp(self):
        super().setUp()
        from larp.storage.postgres import doc
        for run_id, mode in (('live-run', 'live'), ('dev-run', 'dev')):
            self.store.initialize(run_id, self.WALLET if mode == 'live' else '0x' + '6' * 40, 56,
                                  doc(dict(balances=dict(USDT=100, BNB=10))), mode=mode)

    def manifest(self, *, open_rows, draft_rows):
        return Document.from_dict(dict(schema='ReleaseManifest.v1', build_id='b' * 40, repository='https://x',
                                       release_register=dict(schema='ReleaseRegister.v1', services_sha256='1' * 64,
                                                             deviations_sha256='2' * 64, services=1, deviations=2,
                                                             open_deviations=open_rows, draft_deviations=draft_rows)))

    def activate(self, run_id, wallet, manifest):
        from larp.runtime.service import activate_run
        config = dict(run_id=run_id, mode='live' if run_id == 'live-run' else 'dev', wallet_address=wallet,
                      build_id='b' * 40)
        return activate_run(config, self.store, manifest, reviewer='Reviewer', review_ref='IDEA-049', now_ms=1)

    def test_d_req_059_live_activation_refuses_open_or_draft_deviations(self):
        from larp.runtime.service import StartRefused
        for open_rows, draft_rows in ((['DEV-18'], ['DEV-18']), ([], ['DEV-01'])):
            with self.subTest(open=open_rows, draft=draft_rows):
                with self.assertRaises(StartRefused):
                    self.activate('live-run', self.WALLET, self.manifest(open_rows=open_rows, draft_rows=draft_rows))
                self.assertTrue(self.store.load('live-run').read()['quarantined'])
        legacy = Document.from_dict({k: v for k, v in self.manifest(open_rows=[], draft_rows=[]).read().items()})
        register = dict(legacy.read()['release_register']); register.pop('draft_deviations')
        with self.assertRaises(StartRefused):  # a register that does not say which rows are draft cannot pass
            self.activate('live-run', self.WALLET, Document.from_dict(dict(legacy.read(), release_register=register)))
        # A development rehearsal may run before the freeze; a final register activates the live run.
        self.assertTrue(self.activate('dev-run', '0x' + '6' * 40,
                                      self.manifest(open_rows=['DEV-18'], draft_rows=['DEV-01']))['activated'])
        self.assertTrue(self.activate('live-run', self.WALLET, self.manifest(open_rows=[], draft_rows=[]))['activated'])

    def test_d_req_059_the_register_reports_its_draft_rows(self):
        from larp.runtime.register import load_register
        register = load_register(ROOT)
        rows = json.loads((ROOT / 'config/release/deviations.v1.json').read_text())['rows']
        self.assertEqual(register['draft_deviations'], sorted(r['id'] for r in rows if r['status'] == 'DRAFT'))


# --- D-REQ-055: reproducible bundle kept by CI on the branches that ship (#49) -----------------------------------

class ReproducibleBundle(bundle_tests.ReleaseBundle):
    def test_d_req_055_bundle_archive_is_byte_reproducible(self):
        digests = []
        for now in (1_000_000.0, 2_000_000.0):
            with patch('time.time', return_value=now):
                digests.append(self.build()['sha256'])
        self.assertEqual(digests[0], digests[1])


for _name in [n for n in dir(bundle_tests.ReleaseBundle) if n.startswith('test_')]:
    setattr(ReproducibleBundle, _name, None)  # only this module's test runs here; the originals run in their module


class ContinuousIntegration(unittest.TestCase):
    def test_d_req_055_ci_keeps_the_bundle_and_runs_on_the_branches_that_ship(self):
        workflow = (ROOT / '.github/workflows/runtime.yml').read_text(encoding='utf-8')
        push = re.search(r'push:\s*\n(?:\s*#.*\n)*\s*branches:\s*\[([^\]]*)\]', workflow)
        branches = {b.strip().strip('\'"') for b in push.group(1).split(',')} if push else set()
        for branch in ('main', 'codex/system-testing-*', 'review/final-*'):
            self.assertIn(branch, branches)
        upload = re.search(r'uses:\s*actions/upload-artifact@([0-9a-f]{40})\b(.*?)(?:\n\s*- |\Z)', workflow, re.S)
        self.assertIsNotNone(upload, 'the host-bundle job must upload the bundle it hashed, pinned by commit SHA')
        self.assertIn('larp-bundle', upload.group(2))


# --- D-REQ-062: no credential is tracked in the repository (G-41 "CI scan on every push") ------------------------

PUBLIC_TEST_VECTORS = {'5f3a0123456789abcdef0123456789abcdef0123456789abcdef9b2c7e1d4a6f'}  # PROTOCOL.md §2
SECRET_PATTERNS = (
    ('private key block', re.compile(rb'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----')),
    ('AWS access key ID', re.compile(rb'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b')),
    ('populated hex secret', re.compile(rb'\b(?:AI_SEEDS_SECRET|WALLET_PRIVATE_KEY|PRIVATE_KEY)\b["\']?\s*[=:]\s*["\']?'
                                        rb'(?:0x)?([0-9a-fA-F]{64})\b')),
    ('populated AWS secret key', re.compile(rb'\baws_secret_access_key\b["\']?\s*[=:]\s*["\']?[A-Za-z0-9/+]{40}\b',
                                            re.I)),
    ('populated mnemonic', re.compile(rb'\bWALLET_MNEMONIC\b["\']?\s*[=:]\s*["\']?(?:[a-z]{3,8} ){11,23}[a-z]{3,8}\b')),
)
FORBIDDEN_FILES = re.compile(r'(^|/)(\.env(\.[^/]*)?|[^/]*\.tfstate(\.backup)?|id_rsa|id_ed25519|[^/]*\.pem|'
                             r'[^/]*\.key)$')
ALLOWED_FILES = re.compile(r'(\.example(\.[a-z]+)?|\.example\.env|\.example\.tfvars)$')


def credential_findings(files):
    """[(path, kind)] for every credential-looking item in `files` ({path: bytes})."""
    findings = []
    for path, raw in files.items():
        if FORBIDDEN_FILES.search(path) and not ALLOWED_FILES.search(path):
            findings.append((path, 'credential file'))
        if path.endswith('.tfvars') and not ALLOWED_FILES.search(path):
            findings.append((path, 'populated tfvars'))
        for kind, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(raw):
                value = match.group(1) if match.groups() else match.group(0)
                if value is not None and value.decode('ascii', 'replace').lower() in PUBLIC_TEST_VECTORS:
                    continue
                findings.append((path, kind))
    return findings


class CredentialScan(unittest.TestCase):
    def test_d_req_062_the_scanner_flags_each_planted_kind(self):
        planted = {
            'a.txt': b'-----BEGIN EC PRIVATE' + b' KEY-----\nAAAA\n',  # split so this file does not match
            'b.txt': b'key AKIA' + b'ABCDEFGHIJKLMNOP' + b' here',
            'c.json': b'{"AI_SEEDS_SECRET": "' + b'ab' * 32 + b'"}',
            'd.env.sample': b'WALLET_PRIVATE_KEY=0x' + b'cd' * 32,
            'e.ini': b'aws_secret_access_key = ' + b'A' * 40,
            'f.txt': b'WALLET_MNEMONIC="' + b' '.join([b'word'] * 12) + b'"',
            'deploy/aws/development.tfvars': b'x = 1',
            '.env': b'',
            'state/terraform.tfstate': b'{}',
        }
        found = {path for path, _ in credential_findings(planted)}
        self.assertEqual(found, set(planted))
        harmless = {'p.md': b'AI_SEEDS_SECRET=<secret issued at registration> or AI_SEEDS_SECRET=...',
                    'q.md': b'Secret `5f3a0123456789abcdef0123456789abcdef0123456789abcdef9b2c7e1d4a6f`',
                    'r.py': b"secret='5f3a0123456789abcdef0123456789abcdef0123456789abcdef9b2c7e1d4a6f'",
                    'deploy/aws/development.example.tfvars': b'x = 1',
                    'config/hosts/evidence.example.env': b'LARP_SEC_USER_AGENT=example'}
        self.assertEqual(credential_findings(harmless), [])

    def test_d_req_062_no_credentials_are_tracked(self):
        names = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], capture_output=True, check=True,
                               timeout=60).stdout.decode('utf-8').split('\0')
        files = {}
        for name in filter(None, names):
            path = ROOT / name
            if path.is_file() and path.stat().st_size <= 5 * 1024 * 1024:
                files[name] = path.read_bytes()
        self.assertEqual(credential_findings(files), [])


# --- D-REQ-023: backups carry no usable signed bytes (#23; fix owned by C) ----------------------------------------

def signed_forms(raw_hex):
    """Every usable form of signed bytes: hex in either case, with or without 0x, and the raw bytes."""
    body = raw_hex.removeprefix('0x')
    return {body.lower().encode(), body.upper().encode(), bytes.fromhex(body)}


def signed_bytes_found(backup, raw_hex):
    """[(table, row, column)] of every exported cell, decoded, that holds `raw_hex` in a usable form (#23)."""
    found, forms = [], signed_forms(raw_hex)
    payload = backup.payload
    if any(form in payload for form in forms) or base64.b64encode(bytes.fromhex(raw_hex[2:])) in payload:
        found.append(('payload', None, None))
    for table, item in backup.read()['tables'].items():
        for index, row in enumerate(item['rows']):
            for column, value in zip(item['columns'], row):
                raw = base64.b64decode(value['bytes']) if type(value) is dict else str(value).encode()
                if any(form in raw for form in forms):
                    found.append((table, index, column))
    return found


def synthetic_signed_transaction():
    """A validly signed BSC transaction from a throwaway key: never funded, never broadcast."""
    from eth_account import Account
    signed = Account.create().sign_transaction(dict(chainId=56, nonce=0, gas=21000, gasPrice=1, value=0,
                                                    to='0x' + '2' * 40, data=b''))
    return '0x' + bytes(signed.raw_transaction).hex()


class SignedBytesInBackups(DatabaseCase):
    def test_d_req_023_backups_carry_no_usable_signed_bytes(self):
        raw_hex = '0x' + 'f8' * 120  # synthetic, never a real transaction
        state = json.dumps(dict(status='ACTIVE', attempts=[dict(state='SIGNED_DURABLE', raw_hex=raw_hex,
                                                                tx_hash='0x' + 'a' * 64)])).encode()
        with self.store.transaction() as db:
            db.execute('INSERT INTO execution_records VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                       ('key-1', 'run', '0x' + '1' * 40, 56, False, 1, state, 's' * 64))
        backup = export(self.store)
        payload = backup.payload
        needle = raw_hex[2:].encode()
        self.assertNotIn(needle, payload)
        self.assertNotIn(base64.b64encode(state), payload)
        self.assertNotIn(base64.b64encode(bytes.fromhex(raw_hex[2:])), payload)
        self.assertEqual(signed_bytes_found(backup, raw_hex), [])  # WR-D2a: every nested cell, decoded

    def forged(self, key, state):
        with self.store.transaction() as db:
            db.execute('INSERT INTO execution_records VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                       (key, 'run', '0x' + key[-1] * 40, 56, True, 1, state, 's' * 64))

    def test_d_req_023_forged_rows_carry_no_signed_bytes(self):
        raw_hex = synthetic_signed_transaction()
        attempt = dict(state='SIGNED_DURABLE', tx_hash='0x' + 'a' * 64)
        self.forged('key-1', json.dumps(dict(attempts=[dict(attempt, signedTransaction=raw_hex)])).encode())
        self.forged('key-2', json.dumps(dict(attempts=[dict(attempt, extra=dict(deep=[dict(raw_hex=raw_hex)]))]))
                    .encode())
        self.forged('key-3', json.dumps(dict(attempts=[dict(attempt, note=raw_hex.upper()[2:])])).encode())
        self.forged('key-4', b'not json ' + raw_hex.encode() + bytes.fromhex(raw_hex[2:]))
        self.forged('key-5', json.dumps(dict(attempts=[attempt])).encode())
        event = json.dumps(dict(type='SIGNED', raw_hex=raw_hex)).encode()
        with self.store.transaction() as db:
            db.execute('INSERT INTO execution_journal VALUES(%s,%s,%s,%s,%s,%s)',
                       ('key-5', 1, event, 's' * 64, '0' * 64, 'h' * 64))
        self.assertEqual(signed_bytes_found(export(self.store), raw_hex), [])


class LegacySignedState(execution_state_tests.SignedState):
    """WR-D2b/d: a legitimately signed execution whose state still holds `raw_hex`, as rows written before C-FND-010."""

    def setUp(self):
        super().setUp()
        self.raw_hex = self.signature.raw_hex
        with self.store.transaction() as db:
            state, = db.execute('SELECT state FROM execution_records WHERE economic_key=%s', (self.key,)).fetchone()
            value = json.loads(bytes(state))
            value['attempts'][-1]['raw_hex'] = self.raw_hex
            self.state_hash = execution_digest(value)
            revision, event, prior = db.execute(
                'SELECT revision,event,previous_hash FROM execution_journal WHERE economic_key=%s '
                'ORDER BY revision DESC LIMIT 1', (self.key,)).fetchone()
            db.execute('UPDATE execution_records SET state=%s,state_hash=%s WHERE economic_key=%s',
                       (execution_canonical(value).encode(), self.state_hash, self.key))
            db.execute('UPDATE execution_journal SET state_hash=%s,head=%s WHERE economic_key=%s AND revision=%s',
                       (self.state_hash, execution_digest([prior, json.loads(bytes(event)), self.state_hash]),
                        self.key, revision))
        self.assertEqual(self.registry.load(self.key).attempts[-1].raw_hex, self.raw_hex)  # a loadable legacy row

    def rows(self, store, table):
        with store.transaction() as db:
            return [[{'bytes': base64.b64encode(bytes(v)).decode()} if isinstance(v, (bytes, memoryview)) else v
                     for v in row]
                    for row in db.execute(f'SELECT * FROM {table} ORDER BY 1,2')]

    def target(self):
        import psycopg
        import uuid
        from psycopg.conninfo import make_conninfo
        from larp.storage.postgres import PostgresStore
        schema = 'larp_d_restore_' + uuid.uuid4().hex
        with psycopg.connect(self.admin_dsn) as db:
            db.execute('CREATE SCHEMA ' + schema)

        def cleanup():
            with psycopg.connect(self.admin_dsn) as db:
                db.execute('DROP SCHEMA ' + schema + ' CASCADE')
        self.addCleanup(cleanup)
        target = PostgresStore(make_conninfo(self.admin_dsn, options='-c search_path=' + schema))
        target.migrate()
        return target

    def assert_restored_closed(self, target):
        from larp.execution import Conflict
        from larp.execution_live.store import ExecutionStore
        restored = target.load('run').read()
        self.assertTrue(restored['quarantined'])
        self.assertEqual(restored['epoch'], self.store.load('run').read()['epoch'] + 1)
        with target.transaction() as db:
            state, = db.execute('SELECT state FROM execution_records WHERE economic_key=%s', (self.key,)).fetchone()
        self.assertFalse(any(form in bytes(state) for form in signed_forms(self.raw_hex)))
        registry = ExecutionStore(target, run_id='run', wallet=execution_state_tests.WALLET)
        with self.assertRaises(Conflict):
            registry.load(self.key)
        with self.assertRaises(Conflict):
            registry.lookup(self.attempt.attempt_id, self.attempt.payload.hash)

    def test_d_req_023_a_legacy_signed_state_is_redacted_and_restores_closed(self):
        from larp.storage.backup import restore
        backup = export(self.store)
        self.assertEqual(signed_bytes_found(backup, self.raw_hex), [])
        tables = backup.read()['tables']
        records = tables['execution_records']
        row = next(r for r in records['rows'] if r[0] == self.key)
        self.assertEqual(row[records['columns'].index('state_hash')], self.state_hash)
        self.assertEqual(tables['execution_journal']['rows'], self.rows(self.store, 'execution_journal'))
        target = self.target()
        restore(target, backup)
        self.assert_restored_closed(target)

    def test_d_req_023_restoring_an_old_backup_drops_signed_bytes(self):
        from larp.storage.backup import restore
        from larp.storage.postgres import digest, doc
        tables = export(self.store).read()['tables']
        records = tables['execution_records']
        state = records['columns'].index('state')
        with self.store.transaction() as db:
            raw, = db.execute('SELECT state FROM execution_records WHERE economic_key=%s', (self.key,)).fetchone()
        for row in records['rows']:
            if row[0] == self.key:  # as the export before this fix wrote it: the state unchanged, bytes included
                row[state] = {'bytes': base64.b64encode(bytes(raw)).decode()}
        old = doc(dict(schema='Backup.v1', sha256=digest(doc(tables).payload), tables=tables))
        self.assertNotEqual(signed_bytes_found(old, self.raw_hex), [])
        target = self.target()
        restore(target, old)
        self.assert_restored_closed(target)


for _name in [n for n in dir(execution_state_tests.SignedState) if n.startswith('test_')]:
    setattr(LegacySignedState, _name, None)  # only this module's tests run here; the originals run in their module


# --- D-REQ-030 / 032: a rejected plan keeps the round's accepted evidence (#51) -----------------------------------

class RejectedPlan(DatabaseCase):
    def test_d_req_032_a_rejected_plan_keeps_the_rounds_evidence_updates(self):
        import tests.audit.test_round_logging as logging_tests
        from larp.runtime.coordinator import Coordinator
        from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePolicy
        from larp.runtime.replay import replay
        from larp.storage.postgres import PostgresStore, doc
        from tests.support import request
        updates = dict(evidence={'ISSUER': dict(version=3, latch='ADVERSE')}, evidence_versions={'ISSUER': 3})

        def builder(current, req, assessment, now_ms):
            return dict(projection=current['projection'], reservations=current['reservations']), dict(updates)
        planner = logging_tests.Planned([logging_tests.intent('x')],
                                        [dict(intent_id='intent:x', asset='USDT', units=1000)])  # > balance

        def coordinator(store):
            return Coordinator(store, FakeAssessor(), FakePolicy(), planner, execution=FakeExecution(), run_id='run',
                               version_id='synthetic', profile_hash='a' * 64, address=logging_tests.ADDRESS,
                               clock_ms=lambda: logging_tests.NOW, context_builder=builder)
        coordinator(self.store).start('r', request('BUY'), logging_tests.NOW)
        projection = self.store.load('run').read()['projection']
        self.assertEqual({k: projection.get(k) for k in updates}, updates)
        with self.store.transaction() as db:
            logs = [json.loads(Document(bytes(r[0])).read()['log'])['data'] for r in db.execute(
                "SELECT document FROM audit_events WHERE run_id='run' AND round_id='r'")]
        self.assertEqual(len(logs), 1)
        self.assertIn('COMMIT_REJECTED', logs[0]['output']['errors'])
        journal, expected = self.store.journal('run'), self.store.verify('run')
        initial = doc(self.store.load('run').read()['initial'])
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        head = replay(journal, initial, self.store, run_id='run', wallet_id='wallet', chain_id=56,
                      version_id='synthetic', profile_hash='a' * 64, address=logging_tests.ADDRESS, policy=FakePolicy(),
                      planner=planner, execution=FakeExecution(), reducer=None, context_builder=builder)
        self.assertEqual(head, expected)


# --- D-REQ-105 / 103 / 111 / 135: hosting definitions --------------------------------------------------------------

class HostingDefinitions(unittest.TestCase):
    def terraform(self, name):
        return (ROOT / 'deploy/aws' / name).read_text(encoding='utf-8')

    def unit(self, name):
        return (ROOT / 'deploy/systemd' / name).read_text(encoding='utf-8')

    def blocks(self, text, kind):
        return re.findall(r'resource "%s" "\w+" \{(?:(?!\nresource ).)*' % kind, text, re.S)

    def default(self, name):
        block = re.search(r'variable "%s" \{(?:(?!\nvariable ).)*' % name, self.terraform('variables.tf'), re.S)
        found = block and re.search(r'default\s*=\s*"?([^"\n]+)"?', block.group(0))
        return found.group(1).strip() if found else None

    def value(self, body, attribute):
        found = re.search(r'%s\s*=\s*(?:format\("[^"]*",\s*)?(var\.\w+|"[^"]*"|[0-9.]+)' % attribute, body)
        if not found:
            return None
        token = found.group(1).strip('"')
        return self.default(token[4:]) if token.startswith('var.') else token

    def test_d_req_105_instance_status_failure_reboots_the_host(self):
        alarms = [b for b in self.blocks(self.terraform('monitoring.tf'), 'aws_cloudwatch_metric_alarm')
                  if 'StatusCheckFailed_Instance' in b]
        self.assertTrue(alarms, 'an instance-status alarm is required')
        self.assertTrue(any('aws_instance.host' in b and ':ec2:reboot' in b for b in alarms))

    def test_d_req_103_a_budget_covers_the_whole_credit_period(self):
        budgets = self.blocks(self.terraform('budget.tf'), 'aws_budgets_budget')
        self.assertTrue(any('MONTHLY' in b for b in budgets))  # the monthly pace budget stays
        whole = [b for b in budgets if 'time_period_end' in b]
        self.assertTrue(whole, 'a budget over the whole credit period is required')
        end = self.value(whole[0], 'time_period_end') or ''
        self.assertGreaterEqual(end[:10], '2027-01-01')
        self.assertEqual(float(self.value(whole[0], 'limit_amount')), 100.0)

    def test_d_req_135_evidence_poller_cannot_reach_instance_metadata(self):
        self.assertRegex(self.unit('larp-evidence.service'), r'(?m)^IPAddressDeny=.*\b169\.254\.169\.254(/32)?\b')

    def test_d_req_111_runtime_starts_after_time_sync(self):
        after = ' '.join(re.findall(r'(?m)^After=(.*)$', self.unit('larp-runtime.service')))
        self.assertIn('time-sync.target', after.split())


if __name__ == '__main__':
    unittest.main()

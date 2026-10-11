"""Anchor verification (IDEA-042 A1-A3; IDEA-036 #3, #5, #6) and least-privilege database roles (G1-G2)."""

from contextlib import contextmanager
from pathlib import Path

from larp.contracts import Document
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePlanner, FakePolicy, settle
from larp.runtime.maintenance import ANCHOR_FIELDS, HOUR_MS, Maintenance, verify_anchors
from larp.storage.archive import S3Archive
from larp.storage.backup import export, restore
from larp.storage.execution_store import PostgresExecutionStore
from larp.storage.postgres import IntegrityError, PostgresStore, Unavailable, doc
from tests.storage.test_archive import FakeS3
from tests.support import DatabaseCase, request

NOW = 1791590400000
ROOT = Path(__file__).resolve().parents[2]


class Rounds(DatabaseCase):
    def coordinator(self, store=None):
        return Coordinator(store or self.store, FakeAssessor(), FakePolicy(), FakePlanner(), execution=FakeExecution(),
                           run_id='run', version_id='synthetic', profile_hash='a' * 64, address='0x' + '1' * 40,
                           clock_ms=lambda: NOW)

    def hold(self, name, store=None):
        self.coordinator(store).start(name, request('HOLD', job=name), NOW)


class Anchors(Rounds):
    def anchor(self, now):
        Maintenance(self.store, S3Archive(FakeS3(), bucket='fixture', account_id='123456789012', kms_key='k',
                                          prefix='archive/dev', retention_days=90),
                    backup_interval_ms=24 * HOUR_MS).prepare('run', now)
        with self.store.transaction() as db:
            return [Document(bytes(r[0])).read() for r in db.execute(
                "SELECT payload FROM archive_outbox WHERE run_id='run' AND kind='anchor' ORDER BY slot_ms")]

    def test_a1_a3_every_anchor_verifies_and_carries_no_content(self):
        self.hold('r1')
        self.anchor(NOW)
        self.hold('r2')
        anchors = self.anchor(NOW + HOUR_MS)  # both hourly anchors, as read back
        self.assertEqual(len(anchors), 2)
        for a in anchors:
            self.assertEqual(set(a), ANCHOR_FIELDS)  # identifiers, times and hashes only
        self.assertEqual(verify_anchors(self.store, 'run', anchors)['latest_sequence'], anchors[-1]['sequence'])
        with self.assertRaises(IntegrityError):
            verify_anchors(self.store, 'run', [dict(anchors[0], note='free text')])

    def test_a1_a_journal_rewritten_after_anchoring_fails(self):
        self.hold('r1')
        self.hold('r2')
        anchors = self.anchor(NOW)
        journal = [d.read() for d in self.store.journal('run')]
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        self.store.initialize('run', 'wallet', 56, doc(dict(balances=dict(USDT=100, BNB=10, NVDAB=0))))
        self.store.takeover('run', 1, offline=True)
        journal[0]['event']['record']['errors'].append('REWRITTEN')  # a self-consistent rewrite of round 1
        for batch in journal:
            self.store.commit(doc(batch))
        self.store.verify('run')  # the rewritten chain is internally consistent ...
        with self.assertRaises(IntegrityError):
            verify_anchors(self.store, 'run', anchors)  # ... but not the anchored one

    def test_a2_a_restore_behind_the_latest_anchor_is_stale(self):
        self.hold('r1')
        old = export(self.store)
        self.hold('r2')
        anchors = self.anchor(NOW)
        verify_anchors(self.store, 'run', anchors)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs, archive_clock, archive_outbox CASCADE')
        restore(self.store, old)
        with self.assertRaises(IntegrityError):
            verify_anchors(self.store, 'run', anchors)


class RoleStore(PostgresStore):
    """Connects as the test superuser, then runs every transaction as `role` (SET LOCAL ROLE)."""

    def __init__(self, dsn, role):
        super().__init__(dsn)
        self.role = role

    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET LOCAL ROLE ' + self.role)
            yield db


class Roles(Rounds):
    def setUp(self):
        super().setUp()
        import psycopg
        script = (ROOT / 'deploy/postgres/roles.sql').read_text()
        with psycopg.connect(self.store._dsn) as db:
            if not db.execute("SELECT 1 FROM pg_roles WHERE rolname='rds_iam'").fetchone():
                db.execute('CREATE ROLE rds_iam')
            database = db.execute('SELECT current_database()').fetchone()[0]
            db.execute(script.replace('ON DATABASE larp ', 'ON DATABASE ' + database + ' ')
                       .replace('SCHEMA public ', 'SCHEMA ' + self.schema + ' '))
        self.as_role = {r: RoleStore(self.store._dsn, r) for r in ('larp_runtime', 'larp_execution', 'larp_signer')}

    def test_g2_runtime_runs_rounds_settlement_and_close(self):
        runtime = self.as_role['larp_runtime']
        c = self.coordinator(runtime)
        c.start('r', request('BUY'), NOW)
        tx = '0x' + 'b' * 64
        for kind, name in (('BROADCAST_ATTEMPTED', 'b'), ('FINAL_SUCCESS', 'f')):
            c.observe(name, doc(dict(kind=kind, observation_id=name, round_id='r', tx_hash=tx, simulated=True)), settle)
        c.recover(NOW + 1)
        self.assertEqual(runtime.load('run').read()['projection']['balances']['NVDAB'], 2)
        for sql in ('SELECT * FROM execution_signatures', 'SELECT * FROM executions',
                    "UPDATE runs SET initial='\\x00'::bytea", 'DELETE FROM events'):
            with self.subTest(sql), self.assertRaises(Unavailable):
                with runtime.transaction() as db:
                    db.execute(sql)

    def test_g2_execution_store_and_claims_but_never_the_journal(self):
        self.coordinator().start('r', request('BUY'), NOW)
        command_id = self.store.load('run').read()['projection']['round_records']['r']['plan']['intents'][0]['intent_id']
        execution = self.as_role['larp_execution']
        self.assertEqual(execution.claim_command('run', command_id, self.epoch, 'key-1', NOW).read()['command_id'],
                         command_id)
        store = PostgresExecutionStore(execution, 'run')
        store.ensure()
        store.advance_guard()
        self.assertEqual(store.authority(), (self.epoch, 2))
        for sql in ("INSERT INTO events VALUES('run','x',99,'\\x00','h','h','h','h','\\x00')",
                    'SELECT * FROM execution_signatures', "UPDATE runs SET projection='\\x00'::bytea"):
            with self.subTest(sql), self.assertRaises(Unavailable):
                with execution.transaction() as db:
                    db.execute(sql)

    def test_g2_signer_registry_only(self):
        signer = self.as_role['larp_signer']
        with signer.transaction() as db:
            db.execute("INSERT INTO execution_signatures VALUES('attempt-1','payload-hash','{}')")
        for sql in ('SELECT * FROM runs', 'SELECT * FROM executions', "DELETE FROM execution_signatures"):
            with self.subTest(sql), self.assertRaises(Unavailable):
                with signer.transaction() as db:
                    db.execute(sql)

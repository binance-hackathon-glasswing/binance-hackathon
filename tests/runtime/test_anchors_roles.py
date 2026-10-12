"""Anchor verification (IDEA-042 A1-A3; IDEA-036 #3, #5, #6) and least-privilege database roles (G1-G2, §4 X2)."""

from contextlib import contextmanager
from pathlib import Path

from larp.contracts import Document
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePlanner, FakePolicy, settle
from larp.runtime.maintenance import ANCHOR_FIELDS, HOUR_MS, Maintenance, verify_anchors
from larp.storage.archive import S3Archive
from larp.storage.backup import export, restore, select_sql
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
        self.as_role = {r: RoleStore(self.store._dsn, r) for r in ('larp_runtime', 'larp_execution', 'larp_signer', 'larp_archive')}

    def refused(self, role, *statements):
        for sql in statements:
            with self.subTest(role=role, sql=sql), self.assertRaises(Unavailable):
                with self.as_role[role].transaction() as db:
                    db.execute(sql)

    def execution_rows(self):
        """One row in each execution table, written as the execution service and the signer would."""
        with self.as_role['larp_execution'].transaction() as db:
            db.execute("INSERT INTO execution_records VALUES('key-1','run','0xw',56,false,1,'\\x00','s')")
            db.execute("UPDATE execution_records SET revision=2 WHERE economic_key='key-1'")
            db.execute("INSERT INTO execution_journal VALUES('key-1',1,'\\x00','s','p','h')")
            db.execute("INSERT INTO execution_observations VALUES('key-1:final','run','\\x00','o')")
        with self.as_role['larp_signer'].transaction() as db:
            db.execute("SELECT epoch FROM runs WHERE run_id='run' FOR UPDATE")  # the registry write is fenced
            db.execute("INSERT INTO execution_signatures VALUES('attempt-1','run','p','\\x00','g')")

    def test_g2_runtime_runs_rounds_settlement_and_close(self):
        runtime = self.as_role['larp_runtime']
        c = self.coordinator(runtime)
        c.start('r', request('BUY'), NOW)
        tx = '0x' + 'b' * 64
        for kind, name in (('BROADCAST_ATTEMPTED', 'b'), ('FINAL_SUCCESS', 'f')):
            c.observe(name, doc(dict(kind=kind, observation_id=name, round_id='r', tx_hash=tx, simulated=True)), settle)
        c.recover(NOW + 1)
        self.assertEqual(runtime.load('run').read()['projection']['balances']['NVDAB'], 2)
        self.execution_rows()
        with runtime.transaction() as db:  # settlement reads the public execution facts
            self.assertEqual(db.execute('SELECT count(*) FROM execution_journal').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM execution_observations').fetchone()[0], 1)
        self.refused('larp_runtime', 'SELECT * FROM execution_signatures', 'SELECT * FROM execution_records',
                     "INSERT INTO execution_observations VALUES('x','run','\\x00','o')",
                     "UPDATE runs SET initial='\\x00'::bytea", 'DELETE FROM events')

    def test_g2_execution_service_store_and_commands_but_never_the_journal(self):
        self.coordinator().start('r', request('BUY'), NOW)
        command_id = self.store.load('run').read()['projection']['round_records']['r']['plan']['intents'][0]['intent_id']
        execution = self.as_role['larp_execution']
        self.assertEqual(execution.command('run', command_id, self.epoch, NOW).read()['command_id'], command_id)
        self.execution_rows()
        with execution.transaction() as db:  # reads signed bytes to broadcast them
            self.assertEqual(db.execute('SELECT count(*) FROM execution_signatures').fetchone()[0], 1)
        self.refused('larp_execution', "INSERT INTO events VALUES('run','x',99,'\\x00','h','h','h','h','\\x00')",
                     "UPDATE runs SET projection='\\x00'::bytea",
                     "INSERT INTO execution_signatures VALUES('a2','run','p','\\x00','g')",
                     "UPDATE execution_journal SET head='x'", 'DELETE FROM execution_journal',
                     "UPDATE execution_observations SET observation_hash='x'", 'DELETE FROM execution_records')

    def test_g2_signer_registry_only(self):
        self.execution_rows()
        self.refused('larp_signer', 'SELECT * FROM execution_records', 'SELECT * FROM execution_journal',
                     'SELECT * FROM execution_observations', 'SELECT * FROM commands',
                     "UPDATE runs SET projection='\\x00'::bytea", "UPDATE execution_signatures SET signed_hash='x'",
                     'DELETE FROM execution_signatures')

    def test_g2_v8_archive_backs_up_execution_tables_without_signed_bytes(self):
        self.execution_rows()
        with self.as_role['larp_archive'].transaction() as db:  # the daily backup exports all four (IDEA-042 §4 X2)
            for table in ('execution_records', 'execution_journal', 'execution_signatures', 'execution_observations'):
                self.assertEqual(len(db.execute(*select_sql(db, table)).fetchall()), 1)
        self.refused('larp_archive', 'SELECT signed FROM execution_signatures', 'SELECT * FROM execution_signatures',
                     "UPDATE execution_records SET terminal=true", 'DELETE FROM execution_signatures',
                     "INSERT INTO execution_observations VALUES('x','run','\\x00','o')")

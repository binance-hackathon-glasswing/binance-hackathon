"""C-REQ-012/036/037: legitimately produced PostgreSQL state has no signed bytes."""
import base64
import json
import uuid

from larp.execution import Blocked, Conflict, Executor, Signed
from larp.execution_live.store import ExecutionStore
from larp.storage.backup import export, restore
from larp.storage.postgres import PostgresStore
from tests.execution import test_postgres_execution as fixtures
from tests.execution_fixtures import FakeDecoder, FakeVenue, WALLET, intent
from tests.support import DatabaseCase


class SignedState(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.registry = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.guards = fixtures.ExecutionGuards(self.registry)
        self.venue = FakeVenue(self.registry)
        self.restart()
        self.key = intent().key
        self.executor.create(intent(), 10)
        self.executor.prepare(self.key, 11)
        self.executor.authorize(self.key, 12)
        self.state = self.executor.sign(self.key, 13)
        self.attempt = self.state.attempts[-1]
        self.signature = self.registry.lookup(self.attempt.attempt_id, self.attempt.payload.hash)

    def restart(self):
        registry = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.executor = Executor(registry, self.guards, self.venue, fixtures.RegistrySigner(registry), FakeDecoder())

    def test_c_req_012_signed_bytes_only_exist_in_restricted_registry(self):
        self.assertIsNone(self.state.attempts[-1].raw_hex)
        with self.store.transaction() as db:
            state = bytes(db.execute('SELECT state FROM execution_records WHERE economic_key=%s', (self.key,)).fetchone()[0])
            journal = b''.join(bytes(row[0]) for row in db.execute('SELECT event FROM execution_journal'))
        self.assertNotIn(self.signature.raw_hex.encode(), state)
        self.assertNotIn(self.signature.raw_hex.encode(), journal)
        self.assertEqual(self.registry.load(self.key).attempts[-1].tx_hash, self.signature.tx_hash)

    def test_c_req_012_logical_backup_of_real_execution_has_no_raw_bytes(self):
        tables = export(self.store).read()['tables']
        for table in ('execution_records', 'execution_journal'):
            for row in tables[table]['rows']:
                for value in row:
                    if type(value) is dict and 'bytes' in value:
                        raw = base64.b64decode(value['bytes'])
                        self.assertNotIn(self.signature.raw_hex.encode(), raw)
        self.assertEqual(tables['execution_signatures']['rows'], [])

    def test_c_req_036_restart_broadcasts_original_registry_bytes_once(self):
        self.restart()
        sent = self.executor.broadcast(self.key, 14)
        self.registry.check_broadcast(self.signature, self.attempt.epoch, self.attempt.guard_version)
        self.restart()
        self.executor.broadcast(self.key, 15)
        self.assertEqual(self.venue.broadcasts, [self.signature.tx_hash])
        self.assertEqual(sent.attempts[-1].tx_hash, self.signature.tx_hash)

    def test_c_req_036_missing_registry_cannot_fall_back_to_state_bytes(self):
        with self.store.transaction() as db:
            db.execute('DELETE FROM execution_signatures')
        self.restart()
        with self.assertRaises(Blocked):
            self.executor.broadcast(self.key, 14)
        self.assertEqual(self.registry.load(self.key).attempts[-1].state, 'SIGNED_DURABLE')
        self.assertEqual(self.venue.broadcasts, [])

    def test_c_req_036_corrupt_registry_refuses_before_possible_send(self):
        with self.store.transaction() as db:
            db.execute("UPDATE execution_signatures SET signed_hash='corrupt'")
        self.restart()
        with self.assertRaises((Blocked, Conflict)):
            self.executor.broadcast(self.key, 14)
        self.assertEqual(self.registry.load(self.key).attempts[-1].state, 'SIGNED_DURABLE')
        self.assertEqual(self.venue.broadcasts, [])

    def test_c_req_037_forged_raw_bytes_cannot_reuse_a_possible_send_hash(self):
        self.executor.broadcast(self.key, 14)
        with self.assertRaises(Conflict):
            self.registry.check_broadcast(Signed(self.signature.raw_hex + '00', self.signature.tx_hash),
                                          self.attempt.epoch, self.attempt.guard_version)

    def test_c_req_037_restored_backup_is_quarantined_without_signature_authority(self):
        import psycopg
        from psycopg.conninfo import make_conninfo
        schema = 'larp_c_restore_' + uuid.uuid4().hex
        with psycopg.connect(self.admin_dsn) as db:
            db.execute('CREATE SCHEMA ' + schema)
        def cleanup():
            with psycopg.connect(self.admin_dsn) as db:
                db.execute('DROP SCHEMA ' + schema + ' CASCADE')
        self.addCleanup(cleanup)
        target = PostgresStore(make_conninfo(self.admin_dsn, options='-c search_path=' + schema))
        target.migrate()
        restore(target, export(self.store))
        self.assertTrue(target.load('run').read()['quarantined'])
        restored = ExecutionStore(target, run_id='run', wallet=WALLET)
        self.assertEqual(restored.load(self.key).attempts[-1].tx_hash, self.signature.tx_hash)
        self.assertIsNone(restored.lookup(self.attempt.attempt_id, self.attempt.payload.hash))

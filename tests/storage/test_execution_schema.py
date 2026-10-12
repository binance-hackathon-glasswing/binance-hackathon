"""The execution service's store in the migrations, and in backups (IDEA-042 §4 X1, X2).

Migration 008 adopts Isaac's proposed schema (`larp/execution_live/store.py:SCHEMA`, IDEA-039). On a tree that has
his module, the test below recreates the four tables from his DDL and shows the catalogue is unchanged.
"""

import importlib.util

from larp.storage.backup import export, restore
from tests.support import DatabaseCase

TABLES = ('execution_records', 'execution_journal', 'execution_signatures', 'execution_observations')


class ExecutionSchema(DatabaseCase):
    def catalogue(self):
        with self.store.transaction() as db:
            columns = db.execute(
                'SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns '
                'WHERE table_schema=current_schema() AND table_name=ANY(%s) ORDER BY 1,ordinal_position',
                (list(TABLES),)).fetchall()
            constraints = db.execute(
                "SELECT conrelid::regclass::text,contype,pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid::regclass::text=ANY(%s) ORDER BY 1,2,3", (list(TABLES),)).fetchall()
            indexes = db.execute(
                'SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname=current_schema() '
                'AND tablename=ANY(%s) ORDER BY 1,2', (list(TABLES),)).fetchall()
        return columns, constraints, [(t, n, d.replace(self.schema + '.', '')) for t, n, d in indexes]

    def test_x1_migrations_create_the_four_tables_and_the_wallet_barrier(self):
        columns, _, indexes = self.catalogue()
        self.assertEqual(sorted({c[0] for c in columns}), sorted(TABLES))
        barrier = [d for _, n, d in indexes if n == 'execution_wallet_barrier']
        self.assertEqual(len(barrier), 1)
        self.assertIn('WHERE (NOT terminal)', barrier[0])
        with self.store.transaction() as db:
            self.assertIsNone(db.execute("SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() "
                                         "AND table_name='commands' AND column_name='execution_key'").fetchone())

    def test_x1_same_as_the_execution_owners_schema(self):
        if importlib.util.find_spec('larp.execution_live') is None:
            self.skipTest("Isaac's larp.execution_live is not on this tree (runs after integration)")
        from larp.execution_live.store import SCHEMA
        before = self.catalogue()
        with self.store.transaction() as db:
            db.execute('DROP TABLE ' + ','.join(TABLES))
            db.execute(SCHEMA.replace(' IF NOT EXISTS', ''))
        self.assertEqual(self.catalogue(), before)

    def test_x2_backup_round_trip_keeps_the_execution_rows(self):
        rows = dict(
            execution_records=('key-1', 'run', '0x' + '1' * 40, 56, False, 1, b'{"state":1}', 's' * 64),
            execution_journal=('key-1', 1, b'{"event":1}', 's' * 64, '0' * 64, 'h' * 64),
            execution_signatures=('attempt-1', 'run', 'p' * 64, b'{"raw":"0x00"}', 'g' * 64),
            execution_observations=('key-1:final', 'run', b'{"kind":"FILL"}', 'o' * 64))
        with self.store.transaction() as db:
            for table in TABLES:
                db.execute(f'INSERT INTO {table} VALUES({",".join(["%s"] * len(rows[table]))})', rows[table])
        backup = export(self.store)
        self.assertTrue(set(TABLES) <= set(backup.read()['tables']))
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs, archive_clock, archive_outbox CASCADE')
            for table in TABLES:
                self.assertEqual(db.execute(f'SELECT count(*) FROM {table}').fetchone()[0], 0)
        restore(self.store, backup)
        with self.store.transaction() as db:
            for table in TABLES:
                with self.subTest(table):
                    restored = [tuple(bytes(v) if isinstance(v, memoryview) else v for v in r)
                                for r in db.execute(f'SELECT * FROM {table}').fetchall()]
                    self.assertEqual(restored, [rows[table]])

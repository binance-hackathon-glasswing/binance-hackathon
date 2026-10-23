"""IDEA-085 R1-R6: pooled connections for the hosted IAM store; a plain DSN store keeps one connection per transaction."""
import threading
import unittest
from unittest.mock import Mock, patch

import psycopg
from psycopg.pq import TransactionStatus

from larp.runtime.database import IamPostgresStore
from larp.storage.postgres import SOCKET_OPTIONS, IntegrityError, PostgresStore, Unavailable
from tests.support import DatabaseCase

CONFIG = dict(database_host='synthetic.rds.invalid', database_user='larp_runtime', region='synthetic',
              database_name='larp_test', database_ca_file='/synthetic/ca')


class FakeConnection:
    """Enough of psycopg.Connection for the pool: status, statements, commit/rollback/close."""

    def __init__(self, fail_first=None):
        self.closed = self.broken = False
        self.info = Mock(transaction_status=TransactionStatus.IDLE)
        self.statements, self.commits, self.rollbacks = [], 0, 0
        self.fail_first = fail_first

    def execute(self, sql, *args):
        if self.fail_first is not None:
            error, self.fail_first = self.fail_first, None
            self.broken = True
            raise error
        self.statements.append(sql)
        self.info.transaction_status = TransactionStatus.INTRANS

    def commit(self):
        self.commits += 1
        self.info.transaction_status = TransactionStatus.IDLE

    def rollback(self):
        self.rollbacks += 1
        self.info.transaction_status = TransactionStatus.IDLE

    def close(self):
        self.closed = True


def iam_store():
    rds = Mock()
    rds.generate_db_auth_token.side_effect = lambda **kw: f'synthetic-token-{rds.generate_db_auth_token.call_count}'
    return IamPostgresStore(CONFIG, rds), rds


class PoolUnit(unittest.TestCase):
    def setUp(self):
        self.made = []
        def connect(dsn, **kw):
            self.made.append(FakeConnection())
            return self.made[-1]
        patcher = patch('psycopg.connect', side_effect=connect)
        self.connect = patcher.start()
        self.addCleanup(patcher.stop)

    def test_r1_fifty_transactions_one_login_one_connection(self):
        store, rds = iam_store()
        for _ in range(50):
            with store.transaction() as db:
                db.execute('SELECT 1')
        self.assertEqual(rds.generate_db_auth_token.call_count, 1)
        self.assertEqual(len(self.made), 1)
        self.assertEqual(self.made[0].commits, 50)
        self.assertFalse(self.made[0].closed)
        dsn = self.connect.call_args.args[0]
        for part in ('sslmode=verify-full', 'sslrootcert=/synthetic/ca', 'user=larp_runtime', 'synthetic-token-1'):
            self.assertIn(part, dsn)
        self.assertNotIn('token', repr(store))
        store.close()
        self.assertTrue(self.made[0].closed)

    def test_r2_old_connection_replaced_at_checkout_never_mid_transaction(self):
        store, rds = iam_store()
        clock = [1000.0]
        with patch('larp.storage.postgres.time.monotonic', side_effect=lambda: clock[0]):
            with store.transaction() as db:
                clock[0] += store.MAX_CONNECTION_AGE_S + 1  # ages while in use: finishes normally, not pooled
                db.execute('SELECT 1')
            self.assertTrue(self.made[0].closed)
            self.assertEqual(self.made[0].commits, 1)
            with store.transaction():
                pass
            clock[0] += store.MAX_CONNECTION_AGE_S  # idle in the pool past the maximum age
            with store.transaction():
                pass
        self.assertEqual(len(self.made), 3)
        self.assertTrue(self.made[1].closed)
        self.assertEqual(rds.generate_db_auth_token.call_count, 3)

    def test_r2_at_most_four_idle_connections(self):
        store, _ = iam_store()
        contexts = [store.transaction() for _ in range(6)]
        for context in contexts:
            context.__enter__()
        for context in contexts:
            context.__exit__(None, None, None)
        self.assertEqual(len(self.made), 6)
        self.assertEqual(len(store._idle), store.MAX_IDLE_CONNECTIONS)
        self.assertEqual(sum(c.closed for c in self.made), 2)

    def test_r4_caller_error_rolls_back_and_reuses_a_clean_connection(self):
        store, _ = iam_store()
        with self.assertRaises(ValueError):
            with store.transaction():
                raise ValueError('caller refused')
        self.assertEqual((self.made[0].rollbacks, self.made[0].commits), (1, 0))
        with store.transaction():
            pass
        self.assertEqual(len(self.made), 1)

    def test_r4_broken_connection_is_discarded(self):
        store, _ = iam_store()
        with self.assertRaises(Unavailable):
            with store.transaction() as db:
                db.broken = True
                raise psycopg.OperationalError('server closed the connection')
        self.assertTrue(self.made[0].closed)
        with store.transaction():
            pass
        self.assertEqual(len(self.made), 2)

    def test_r4_idle_pooled_connection_closed_by_server_is_replaced_once(self):
        store, rds = iam_store()
        with store.transaction():
            pass
        self.made[0].fail_first = psycopg.OperationalError('terminating connection due to administrator command')
        with store.transaction() as db:
            db.execute('SELECT 1')
        self.assertEqual(len(self.made), 2)
        self.assertTrue(self.made[0].closed)
        self.assertEqual(self.made[1].commits, 1)
        self.assertEqual(rds.generate_db_auth_token.call_count, 2)

    def test_r4_fresh_connection_failure_is_not_retried(self):
        store, _ = iam_store()
        self.connect.side_effect = lambda dsn, **kw: self.made.append(
            FakeConnection(fail_first=psycopg.OperationalError('timeout'))) or self.made[-1]
        with self.assertRaises(Unavailable) as raised:
            with store.transaction():
                self.fail('caller work must not run')
        self.assertEqual(len(self.made), 1)
        self.assertNotIn('token', str(raised.exception))

    def test_r4_failure_after_caller_work_is_never_retried(self):
        store, _ = iam_store()
        with store.transaction():
            pass
        calls = []
        with self.assertRaises(Unavailable):
            with store.transaction() as db:
                calls.append(1)
                db.broken = True
                raise psycopg.OperationalError('connection lost mid-transaction')
        self.assertEqual(calls, [1])
        self.assertEqual(len(self.made), 1)

    def test_r4_connect_failure_maps_to_unavailable_without_dsn(self):
        store, _ = iam_store()
        self.connect.side_effect = psycopg.OperationalError('connection to server at "synthetic.rds.invalid" failed')
        with self.assertRaises(Unavailable) as raised:
            with store.transaction():
                pass
        self.assertEqual(str(raised.exception), 'Database transaction failed; signing blocked')

    def test_r6_plain_store_opens_and_closes_one_connection_per_transaction(self):
        store = PostgresStore('postgresql://synthetic/larp_test')
        for _ in range(3):
            with store.transaction():
                pass
        self.assertEqual(len(self.made), 3)
        self.assertTrue(all(c.closed and c.commits == 1 for c in self.made))
        self.assertEqual(store._idle, [])


    def test_rv1_every_connection_bounds_a_dead_socket(self):
        """IDEA-085 RV1: a pooled connection idles up to 600 s, so a vanished server must fail it in seconds."""
        store, _ = iam_store()
        with store.transaction():
            pass
        with PostgresStore('postgresql://synthetic/larp_test').transaction():
            pass
        self.assertEqual(len(self.connect.call_args_list), 2)
        for call in self.connect.call_args_list:
            self.assertEqual(call.kwargs, SOCKET_OPTIONS)
        self.assertEqual((SOCKET_OPTIONS['connect_timeout'], SOCKET_OPTIONS['keepalives'],
                          SOCKET_OPTIONS['tcp_user_timeout']), (5, 1, 30000))
        store.close()

class PooledStore(PostgresStore):
    REUSE_CONNECTIONS = True


class PoolDatabase(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.pooled = PooledStore(self.store._dsn)
        self.addCleanup(self.pooled.close)

    def pid(self, db):
        return db.execute('SELECT pg_backend_pid()').fetchone()[0]

    def test_rv1_socket_options_reach_the_real_connection(self):
        with self.pooled.transaction() as db:
            params = db.info.get_parameters()
            self.assertEqual((params['keepalives'], params['keepalives_idle'], params['keepalives_count'],
                              params['tcp_user_timeout']), ('1', '30', '3', '30000'))

    def test_r3_reused_connection_keeps_no_transaction_settings(self):
        with self.pooled.transaction() as db:
            first = self.pid(db)
            self.assertEqual(db.execute('SHOW statement_timeout').fetchone()[0], '15s')
        with self.pooled.transaction() as db:
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            self.assertEqual(db.execute('SHOW transaction_read_only').fetchone()[0], 'on')
        connection, _ = self.pooled._idle[-1]
        defaults = connection.execute("SELECT current_setting('statement_timeout'), current_setting('lock_timeout'), "
                                      "current_setting('transaction_read_only'), "
                                      "current_setting('transaction_isolation')").fetchone()
        connection.rollback()
        self.assertEqual(defaults, ('0', '0', 'off', 'read committed'))
        with self.pooled.transaction() as db:
            self.assertEqual(self.pid(db), first)
            self.assertEqual(db.execute('SHOW transaction_read_only').fetchone()[0], 'off')
            db.execute('CREATE TEMP TABLE pool_probe(x int) ON COMMIT DROP')
            db.execute('INSERT INTO pool_probe VALUES (1)')

    def test_r4_server_terminated_idle_connection_is_replaced(self):
        with self.pooled.transaction() as db:
            first = self.pid(db)
        with psycopg.connect(self.admin_dsn, autocommit=True) as admin:
            admin.execute('SELECT pg_terminate_backend(%s)', (first,))
        with self.pooled.transaction() as db:
            self.assertNotEqual(self.pid(db), first)
        self.assertEqual(self.pooled.verify('run'), self.store.verify('run'))

    def test_r4_termination_after_caller_work_is_unavailable_not_retried(self):
        runs = []
        with self.assertRaises(Unavailable):
            with self.pooled.transaction() as db:
                runs.append(self.pid(db))
                with psycopg.connect(self.admin_dsn, autocommit=True) as admin:
                    admin.execute('SELECT pg_terminate_backend(%s)', (runs[0],))
                db.execute('SELECT 1')
        self.assertEqual(len(runs), 1)
        with self.pooled.transaction() as db:
            self.assertNotEqual(self.pid(db), runs[0])

    def test_r4_integrity_error_mapping_and_reuse_after_rollback(self):
        with self.pooled.transaction() as db:
            first = self.pid(db)
        with self.assertRaises(IntegrityError) as raised:
            with self.pooled.transaction() as db:
                db.execute("INSERT INTO runs(run_id,wallet_id,chain_id) VALUES ('run','w',56)")
        self.assertIn('23', str(raised.exception))
        with self.pooled.transaction() as db:
            self.assertEqual(self.pid(db), first)
            self.assertEqual(db.execute("SELECT count(*) FROM runs WHERE run_id='run'").fetchone()[0], 1)

    def test_r5_nested_transactions_use_two_connections(self):
        with self.pooled.transaction() as outer:
            with self.pooled.transaction() as inner:
                self.assertNotEqual(self.pid(outer), self.pid(inner))
        self.assertEqual(len(self.pooled._idle), 2)

    def test_r5_threads_never_share_a_connection_in_use(self):
        in_use, lock, errors, pids = set(), threading.Lock(), [], set()
        def work():
            try:
                for _ in range(25):
                    with self.pooled.transaction() as db:
                        pid = self.pid(db)
                        with lock:
                            if pid in in_use:
                                errors.append(pid)
                            in_use.add(pid)
                            pids.add(pid)
                        db.execute('SELECT count(*) FROM events')
                        with lock:
                            in_use.discard(pid)
            except Exception as exc:  # pragma: no cover - reported below
                errors.append(repr(exc))
        threads = [threading.Thread(target=work) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(60)
        self.assertEqual(errors, [])
        self.assertLessEqual(len(self.pooled._idle), self.pooled.MAX_IDLE_CONNECTIONS)
        self.assertLessEqual(len(pids), 8 + 4)  # never one connection per transaction (200)


if __name__ == '__main__':
    unittest.main()

"""The W04 execution machine on PostgreSQL (DR-04; IDEA-042 item 2, criteria E1-E3).

E2 uses Isaac's own W04 suite as the contract: `PostgresW04` inherits every test of
`tests/test_w04_execution.py::ExecutionTests` unchanged and swaps only the storage fixture.
"""

import re

from larp.execution import Conflict
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePlanner, FakePolicy
from larp.storage.execution_store import PostgresExecutionStore
from larp.storage.postgres import Conflict as StoreConflict
from tests import test_w04_execution as w04
from tests.execution_fixtures import FakeDecoder, FakeGuards, FakeSigner, FakeVenue
from tests.support import DatabaseCase, request

NOW = 1791590400000


class _Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class _Registry:
    """The fixture signer writes SQLite-style SQL to `store.db`; run it against the PostgreSQL signer registry."""

    def __init__(self, store):
        self.store = store

    def execute(self, sql, params=()):
        sql = re.sub(r'\bsignatures\b', 'execution_signatures', sql).replace('?', '%s')
        with self.store.transaction() as db:
            cursor = db.execute(sql, params)
            return _Rows(cursor.fetchall() if cursor.description else [])


class PostgresFixture:
    """The W04 fixture API on top of PostgresExecutionStore; only the storage differs from SQLiteFixture."""

    def __init__(self, store, run_id):
        self.inner = PostgresExecutionStore(store, run_id)
        self.inner.ensure()
        self.store, self.run_id, self.db = store, run_id, _Registry(store)

    @property
    def fail_next(self):
        return self.inner.before_write is not None

    @fail_next.setter
    def fail_next(self, value):
        def fault():
            self.inner.before_write = None
            raise OSError('injected storage fault')
        self.inner.before_write = fault if value else None

    def close(self):
        pass  # state lives in PostgreSQL; a "restart" opens a new fixture on the same schema

    def authority(self):
        return self.inner.authority()

    def advance_authority(self, epoch=False):
        self.inner.advance_guard()
        if epoch:
            with self.store.transaction() as db:
                db.execute('UPDATE runs SET epoch=epoch+1 WHERE run_id=%s', (self.run_id,))

    def check_authority(self, epoch, version):
        self.inner.check_authority(epoch, version)

    def load(self, key):
        return self.inner.load(key)

    def commit(self, previous, current, event, epoch, guard_version):
        return self.inner.commit(previous, current, event, epoch, guard_version)

    def events(self):
        return self.inner.events()


class PostgresW04(DatabaseCase, w04.ExecutionTests):
    def setUp(self):
        DatabaseCase.setUp(self)
        self.pg = self.store  # the PostgreSQL store; self.store becomes the W04 storage fixture
        w04.ExecutionTests.setUp(self)

    def attach(self):
        self.store = PostgresFixture(self.pg, 'run')
        self.guards = FakeGuards(self.store)
        self.signer = FakeSigner(self.store)
        self.venue = FakeVenue(self.store)
        self.decoder = FakeDecoder()
        self.engine = w04.Executor(self.store, self.guards, self.venue, self.signer, self.decoder)

    def tearDown(self):
        w04.ExecutionTests.tearDown(self)

    def test_e1_signed_bytes_never_in_events_and_barrier_spans_runs(self):
        state = self.signed_approve()
        raw = state.attempts[-1].raw_hex
        self.assertTrue(raw)
        self.assertNotIn(raw, str(self.store.events()))
        with self.pg.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_signatures').fetchone()[0], 1)


class ClaimCommand(DatabaseCase):
    def planned(self):
        Coordinator(self.store, FakeAssessor(), FakePolicy(), FakePlanner(), execution=FakeExecution(), run_id='run',
                    version_id='synthetic', profile_hash='a' * 64, address='0x' + '1' * 40,
                    clock_ms=lambda: NOW).start('r', request('BUY'), NOW)
        return self.store.load('run').read()['projection']['round_records']['r']['plan']['intents'][0]['intent_id']

    def test_e3_one_command_one_execution(self):
        command_id = self.planned()
        first = self.store.claim_command('run', command_id, self.epoch, 'key-1', NOW)
        self.assertEqual(first.read()['command_id'], command_id)
        self.assertEqual(self.store.claim_command('run', command_id, self.epoch, 'key-1', NOW).read(), first.read())
        with self.assertRaises(StoreConflict):
            self.store.claim_command('run', command_id, self.epoch, 'key-2', NOW)
        with self.assertRaises(StoreConflict):
            self.store.claim_command('run', command_id, self.epoch + 1, 'key-1', NOW)  # stale owner
        with self.assertRaises(StoreConflict):
            self.store.claim_command('run', command_id, self.epoch, 'key-1', NOW + 10 ** 9)  # expired

    def test_e3_claim_refused_while_halted(self):
        from larp.runtime.supervision import Guard
        command_id = self.planned()
        Guard(self.store, 'run', max_failures=3, clear_after=2).evaluate(NOW - 1)  # clock HALT
        with self.assertRaises(StoreConflict):
            self.store.claim_command('run', command_id, self.epoch, 'key-1', NOW)

    def test_e1_authority_fences_on_owner_epoch(self):
        store = PostgresExecutionStore(self.store, 'run')
        store.ensure()
        epoch, version = store.authority()
        self.assertEqual(epoch, self.epoch)
        store.advance_guard()
        with self.assertRaises(Conflict):
            store.check_authority(epoch, version)
        store.check_authority(epoch, version + 1)

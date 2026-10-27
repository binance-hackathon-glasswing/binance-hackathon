"""Synthetic PostgreSQL races only; no live signer, network venue or wallet."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from larp.execution import Conflict, Executor, StateVersionConflict
from larp.execution_live.loop import ExecutionLoop
from larp.execution_live.guards import LiveGuards
from larp.runtime.coordinator import batch_for
from tests.execution.test_postgres_execution import ExecutionGuards, RegistrySigner
from larp.execution_live.store import ExecutionStore
from tests.support import DatabaseCase
from tests.execution_fixtures import intent, WALLET, FakeVenue, FakeDecoder


class PrepareFencing(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.execution_store = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.guards = ExecutionGuards(self.execution_store)
        self.venue = FakeVenue(self.execution_store)
        self.executor = Executor(self.execution_store, self.guards, self.venue,
                                 RegistrySigner(self.execution_store), FakeDecoder())
    def concurrent_prepare(self, change=lambda case: None):
        i = intent()
        self.executor.create(i, 10)
        estimate = self.venue.estimate_gas
        def slow(payload):
            self.store.commit(batch_for(self.store.load('run'), 'concurrent', dict(kind='SYNTHETIC')))
            change(self)
            return estimate(payload)
        self.venue.estimate_gas = slow
        return i

    def test_fence_reads_do_not_reload_the_full_projection(self):
        epoch, version = self.execution_store.authority()
        with patch.object(self.store, 'load', side_effect=AssertionError('full projection reload')):
            self.assertEqual(self.execution_store.authority(), (epoch, version))
            self.assertEqual(self.execution_store.execution_authority(), (epoch, epoch))

    def test_benign_runtime_write_during_prepare_uses_one_probe(self):
        i = self.concurrent_prepare()
        state = self.executor.prepare(i.key, 11)
        self.assertEqual(state.attempts[-1].state, 'PREPARED')
        self.assertEqual(state.prepare_probes, 1)
        self.assertEqual(self.venue.quote_calls, 1)
        self.assertFalse(self.venue.broadcasts)
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_signatures').fetchone()[0], 0)

    def test_changed_prerequisites_never_prepare(self):
        for name in ('risk_valid', 'reservation_valid', 'version_valid', 'clock_trusted'):
            with self.subTest(name=name):
                # Separate economic intent and cleanup for each existing fixture instance.
                self.guards.changes.clear()
                i = intent(intent_id=name)
                self.executor.create(i, 10)
                self.venue.estimate_gas = lambda payload: self.guards.changes.update({name: False}) or 100000
                state = self.executor.prepare(i.key, 11)
                self.assertFalse(state.attempts)
                self.assertIsNotNone(state.blocked_reason)
                self.executor.abort_unsigned(i.key, 12)

    def test_nonce_changed_during_io_refuses(self):
        i = self.concurrent_prepare(lambda case: setattr(case.guards, 'nonce', 1))
        state = self.executor.prepare(i.key, 11)
        self.assertFalse(state.attempts)
        self.assertIn('nonce', state.blocked_reason)

    def test_owner_changed_during_io_refuses(self):
        i = self.concurrent_prepare(lambda case: case.store.takeover('run', 2, offline=True))
        with self.assertRaises(Conflict):
            self.executor.prepare(i.key, 11)
        self.assertFalse(self.executor._load(i.key).attempts)

    def test_race_after_final_refresh_is_still_fenced(self):
        i = intent(); self.executor.create(i, 10)
        snapshot = self.guards.snapshot
        calls = [0]
        def racing(value, now):
            gates = snapshot(value, now); calls[0] += 1
            if calls[0] == 2:
                self.store.commit(batch_for(self.store.load('run'), 'too-late', dict(kind='SYNTHETIC')))
            return gates
        self.guards.snapshot = racing
        with self.assertRaises(Conflict):
            self.executor.prepare(i.key, 11)
        self.assertFalse(self.executor._load(i.key).attempts)

    def test_actual_completion_time_enforces_expiry_and_margin(self):
        for end in (1000, 980):
            with self.subTest(end=end):
                i = intent(intent_id=str(end), authority_margin=30)
                self.executor.create(i, 10)
                self.executor.clock_s = lambda: end
                state = self.executor.prepare(i.key, 11)
                self.assertFalse(state.attempts)
                self.assertIsNotNone(state.blocked_reason)
                self.assertEqual(state.last_observed_at, end)
                self.executor.abort_unsigned(i.key, end)

    def test_clock_passes_expiry_during_final_guard_io(self):
        i = intent(); self.executor.create(i, 10)
        ticks = iter((20, 1000))
        self.executor.clock_s = lambda: next(ticks)
        state = self.executor.prepare(i.key, 11)
        self.assertFalse(state.attempts)
        self.assertIsNotNone(state.blocked_reason)

    def test_backwards_preparation_clock_refuses(self):
        i = intent(); self.executor.create(i, 10)
        self.executor.clock_s = lambda: 9
        state = self.executor.prepare(i.key, 11)
        self.assertFalse(state.attempts)
        self.assertIn('clock regression', state.blocked_reason)


class GuardAcquisition(unittest.TestCase):
    def guards(self, *, nonce_hook=lambda: None, auth_hook=lambda: None):
        state = dict(epoch=1, version=1)
        store = SimpleNamespace(authority=lambda: (state['epoch'], state['version']),
                                execution_authority=lambda: (state['epoch'], state['epoch']))
        def nonce(wallet):
            nonce_hook(); return 0
        def authorization(*args):
            auth_hook()
            return dict(expires_at=1000, audit_durable=True, reservation_valid=True, version_valid=True,
                        risk_valid=True, health_valid=True, clock_trusted=True)
        guards = LiveGuards(store=store, market=SimpleNamespace(mode='live'),
                            chain=SimpleNamespace(mode='live', nonce=nonce), authorization=authorization)
        guards._open_state = lambda *args: (True, True)
        return state, guards

    def test_version_advanced_by_rpc_is_captured_after_io(self):
        state, guards = self.guards(nonce_hook=lambda: state.update(version=2))
        self.assertEqual(guards.snapshot(intent(), 10).state_version, 2)

    def test_owner_changed_by_rpc_refuses(self):
        state, guards = self.guards(nonce_hook=lambda: state.update(epoch=2))
        with self.assertRaises(Conflict):
            guards.snapshot(intent(), 10)

    def test_version_changed_during_authorization_refuses(self):
        state, guards = self.guards(auth_hook=lambda: state.update(version=2))
        with self.assertRaises(Conflict):
            guards.snapshot(intent(), 10)

    def test_native_route_still_requires_explicit_authorization(self):
        for allowed in (False, True):
            with self.subTest(allowed=allowed):
                _, guards = self.guards()
                guards.authorization = lambda *args: dict(expires_at=1000, native_resource_route_valid=allowed)
                gates = guards.snapshot(intent(kind='GAS_TOP_UP'), 10)
                self.assertEqual(gates.token_market_open, allowed)
                self.assertEqual(gates.underlying_market_open, allowed)

    def test_loop_classifies_version_conflict_without_exception_text(self):
        loop = ExecutionLoop.__new__(ExecutionLoop)
        loop._commands = lambda now: []
        loop._active = lambda: ['synthetic-intent']
        loop._unpublished_terminal = lambda: []
        loop.service = SimpleNamespace(advance=Mock(side_effect=StateVersionConflict('private exception text')))
        summary = loop.once(10000)
        self.assertEqual(summary['blocked'], [['synthetic-intent', 'StateVersionConflict']])
        self.assertNotIn('private exception text', str(summary))

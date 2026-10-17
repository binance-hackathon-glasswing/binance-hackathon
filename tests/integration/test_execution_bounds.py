"""IDEA-076 EB3/5: real coordinator/PostgreSQL durability and recorded-port replay."""
from datetime import datetime, timezone

from larp.contracts import Document
from larp.integration.replay import replay_live
from larp.integration.runtime import ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection
from larp.integration.settlement import ExecutionBridge, settle
from larp.runtime.coordinator import Coordinator
from larp.runtime.driver import SessionCalendar
from larp.runtime.fixtures import FakeAssessor
from larp.storage.postgres import doc
from tests.strategy.test_execution_bounds import milliseconds
from tests.strategy.test_s1_plan import snap
from tests.support import DatabaseCase, request


class DurableBudget(DatabaseCase):
    def setUp(self):
        super().setUp()
        snapshot = snap()
        self.context = snapshot.context.read()
        self.profile = self.context['profile']
        self.h = Document.from_dict(self.profile).digest('StrategyProfile.v1')
        self.now = milliseconds('2026-10-12T14:00:00Z')
        self.initial = initial_projection(self.context['portfolio'])
        self.initial['portfolio']['risk']['day'] = '2026-10-09'
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        self.store.initialize('run', 'fake-wallet', 56, doc(self.initial))
        self.store.takeover('run', 1, offline=True)
        self.calendar = SessionCalendar(dict(schema='USRegularSessions.v1', calendar_id='SYNTHETIC_B6',
            sessions=[dict(session_index=79+k, open_at=day+'T13:30:00Z', close_at=day+'T20:00:00Z')
                      for k, day in enumerate(('2026-10-09', '2026-10-12', '2026-10-13', '2026-10-14'))]))

    def market(self, now_ms):
        at = datetime.fromtimestamp(now_ms/1000, timezone.utc).isoformat()
        return [dict(m, observed_at=at, available_at=at, close_at=at, quotes=[])
                for m in self.context['markets']]

    def coordinator(self):
        builder = ContextBuilder(profile=self.profile, profile_hash=self.h, run_id='run', issuers={},
            market=self.market, health=lambda c: self.context['health'], calendar=self.calendar)
        return Coordinator(self.store, FakeAssessor(), StrategyPolicy(),
            RuntimePlanner(job_validity_ms=60000, job_max_attempts=3, issuers={}), execution=ExecutionBridge(),
            run_id='run', version_id='fixture-build', profile_hash=self.h, address='0x'+'1'*40,
            context_builder=builder, initial_policy_state=initial_policy_state('run', self.profile),
            clock_ms=lambda: self.now)

    def start(self, coordinator, round_id):
        req = request(job=round_id, cutoff=self.now).read()
        req['policy_profile_hash'] = self.h
        return coordinator.start(round_id, doc(req), self.now)

    def test_closed_rounds_restart_and_duplicate_round_cannot_restore_attempts(self):
        for ordinal in range(1, 4):
            self.start(self.coordinator(), 'round-'+str(ordinal))
            state = self.store.load('run').read()
            counts = state['projection']['execution_attempt_budget']['counts']
            self.assertTrue(counts)
            self.assertEqual(set(counts.values()), {ordinal})
            self.assertFalse(state['projection']['round_records'])
            self.assertIsNotNone(self.store.receipt('run', 'close:round-'+str(ordinal)))
        before = self.store.load('run').read()['projection']['execution_attempt_budget']
        self.start(self.coordinator(), 'round-3')
        self.assertEqual(self.store.load('run').read()['projection']['execution_attempt_budget'], before)
        self.start(self.coordinator(), 'round-4')
        record = self.store.event('run', 'plan:round-4')['record']
        self.assertIn('LEG_ATTEMPT_LIMIT', record['plan']['reasons'])
        self.assertFalse(record['plan']['quote_requests'])
        self.assertEqual(self.store.load('run').read()['projection']['execution_attempt_budget'], before)
        self.assertTrue(self.store.metrics('run').read()['audit_pending'])

    def test_budget_survives_midnight_weekend_and_resets_at_next_open(self):
        self.now = milliseconds('2026-10-09T14:00:00Z')
        self.start(self.coordinator(), 'friday')
        before = self.store.load('run').read()['projection']['execution_attempt_budget']
        self.now = milliseconds('2026-10-11T14:00:00Z')
        self.start(self.coordinator(), 'weekend')
        self.assertEqual(self.store.load('run').read()['projection']['execution_attempt_budget'], before)
        self.now = milliseconds('2026-10-12T14:00:00Z')
        self.start(self.coordinator(), 'monday')
        after = self.store.load('run').read()['projection']['execution_attempt_budget']
        self.assertEqual(after['session'], 80)
        self.assertEqual(set(after['counts'].values()), {1})

    def test_exact_replay_reconstructs_budget_without_live_calendar_or_market(self):
        coordinator = self.coordinator()
        for n in range(1, 5):
            self.start(coordinator, 'round-'+str(n))
        expected = self.store.verify('run')
        batches = self.store.journal('run')
        def gone(*args):
            raise AssertionError('Replay must not call a live port')
        coordinator.context_builder.market = gone
        coordinator.context_builder.calendar = gone
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        actual = replay_live(batches, doc(self.initial), self.store, builder=coordinator.context_builder,
            run_id='run', wallet_id='fake-wallet', chain_id=56, version_id='fixture-build', profile_hash=self.h,
            address='0x'+'1'*40, policy=StrategyPolicy(),
            planner=RuntimePlanner(job_validity_ms=60000, job_max_attempts=3, issuers={}),
            execution=ExecutionBridge(), reducer=settle, initial_policy_state=initial_policy_state('run', self.profile))
        self.assertEqual(actual, expected)
        self.assertEqual(set(self.store.load('run').read()['projection']['execution_attempt_budget']['counts'].values()),
                         {3})

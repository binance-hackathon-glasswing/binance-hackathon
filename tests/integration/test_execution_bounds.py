"""IDEA-076 EB3/5: real coordinator/PostgreSQL durability and recorded-port replay."""
from datetime import datetime, timedelta, timezone

from larp.contracts import ContractError, Document
from larp.integration.replay import replay_live
from larp.integration.runtime import ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection
from larp.integration.settlement import ExecutionBridge, settle
from larp.research.fixtures import changed, with_quotes
from larp.runtime.coordinator import Coordinator
from larp.runtime.driver import EXPIRED_REASON, DayRoll, SessionCalendar
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
        self.quote_template = None
        self.initial = initial_projection(self.context['portfolio'])
        self.initial['portfolio']['risk']['day'] = '2026-10-09'
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        self.store.initialize('run', 'fake-wallet', 56, doc(self.initial))
        self.store.takeover('run', 1, offline=True)
        self.calendar = SessionCalendar(dict(schema='USRegularSessions.v1', calendar_id='SYNTHETIC_B6',
            sessions=[dict(session_index=79+k, open_at=day+'T13:30:00Z', close_at=day+'T20:00:00Z')
                      for k, day in enumerate(('2026-10-09', '2026-10-12', '2026-10-13', '2026-10-14',
                                               '2026-10-15', '2026-10-16', '2026-10-19', '2026-10-20',
                                               '2026-10-21', '2026-10-22'))]))

    def market(self, now_ms):
        now = datetime.fromtimestamp(now_ms/1000, timezone.utc)
        at = now.isoformat()
        quotes = [dict(q, observed_at=at, available_at=at, expires_at=(now+timedelta(seconds=30)).isoformat())
                  for q in self.quote_template or []]
        return [dict(m, observed_at=at, available_at=at, close_at=at, quotes=quotes)
                for m in self.context['markets'] if m['symbol'] == 'NVDAB']

    def coordinator(self):
        builder = ContextBuilder(profile=self.profile, profile_hash=self.h, run_id='run', issuers={},
            market=self.market, health=lambda c: self.context['health'], calendar=self.calendar)
        return Coordinator(self.store, FakeAssessor(), StrategyPolicy(),
            RuntimePlanner(job_validity_ms=60000, job_max_attempts=3, issuers={}), execution=ExecutionBridge(),
            run_id='run', version_id='fixture-build', profile_hash=self.h, address='0x'+'1'*40,
            context_builder=builder, initial_policy_state=initial_policy_state('run', self.profile),
            clock_ms=lambda: self.now)

    def start(self, coordinator, round_id, *, parent=None):
        midnight = self.now - self.now % 86400000
        DayRoll(coordinator, window_ms=60000)(midnight, self.market(midnight))
        req = request(job=round_id, cutoff=self.now).read()
        req['policy_profile_hash'] = self.h
        return coordinator.start(round_id, doc(req), self.now,
                                 **(dict(execution_parent_round=parent) if parent else {}))

    def test_quote_child_reuses_parent_and_replays_from_the_parent_journal(self):
        coordinator = self.coordinator()
        self.start(coordinator, 'parent')
        original = self.store.load('run').read()['projection']['execution_attempt_budget']
        snapshot = changed(snap(), markets=[m for m in self.context['markets'] if m['symbol'] == 'NVDAB'])
        self.quote_template = with_quotes(snapshot).context.read()['markets'][0]['quotes']
        self.assertTrue(self.quote_template)
        self.start(coordinator, 'parent/quote1', parent='parent')
        record = self.store.load('run').read()['projection']['round_records']['parent/quote1']
        intent = record['plan']['intents'][0]
        self.assertEqual(intent['execution_bounds']['ordinal'], 1)
        from larp.execution_live.service import map_command
        from larp.strategy.execution_bounds import permitted
        mapped = map_command(dict(kind='EXECUTION_REQUEST', command_id=intent['intent_id'], payload=intent,
            round_id='parent/quote1', decision_id=intent['decision_id'], expires_ms=intent['expires_ms']),
            run_id='run', wallet='0x'+'1'*40, version_id='fixture-build', router='0x'+'2'*40,
            token_decimals={m['symbol']: m['decimals'] for m in self.context['markets']}, now_ms=self.now,
            limits=dict(per_trade_cap_units=self.profile['per_trade_cap_units'], max_gas=100000,
                        max_gas_price=1, gas_budget=100000))
        self.assertTrue(permitted(self.store.load('run').read()['projection'], mapped, self.now))
        self.assertEqual(self.store.load('run').read()['projection']['execution_attempt_budget']['counts'],
                         original['counts'])
        self.assertEqual(self.store.load('run').read()['projection']['execution_attempt_budget']['closed'],
                         {'DISCRETIONARY:BUY:NVDAB': 1})
        coordinator.observe('child-aborted', doc(dict(schema='ExecutionObservation.v1', run_id='run',
            wallet_id='fake-wallet', round_id='parent/quote1', intent_id=intent['intent_id'], event_id='child-aborted',
            kind='NOT_SUBMITTED', settlement='FINAL', origin='EXECUTION_RECONCILER',
            observed_at=datetime.fromtimestamp(self.now/1000, timezone.utc).isoformat(),
            intent_terminal=True, round_terminal=True)), settle)
        coordinator.close('parent/quote1', self.now, 'COMPLETE')
        # Even an explicit old-parent reference after an aborted intent must
        # consume a new attempt; replay cannot silently reopen its first slot.
        self.start(coordinator, 'new-chain', parent='parent')
        record = self.store.load('run').read()['projection']['round_records']['new-chain']
        retry = record['plan']['intents'][0]
        self.assertEqual(retry['execution_bounds']['ordinal'], 2)
        coordinator.observe('retry-aborted', doc(dict(schema='ExecutionObservation.v1', run_id='run',
            wallet_id='fake-wallet', round_id='new-chain', intent_id=retry['intent_id'], event_id='retry-aborted',
            kind='NOT_SUBMITTED', settlement='FINAL', origin='EXECUTION_RECONCILER',
            observed_at=datetime.fromtimestamp(self.now/1000, timezone.utc).isoformat(),
            intent_terminal=True, round_terminal=True)), settle)
        coordinator.close('new-chain', self.now, 'COMPLETE')
        self.assert_replay(coordinator)

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
        self.assert_replay(coordinator)
        self.assertEqual(set(self.store.load('run').read()['projection']['execution_attempt_budget']['counts'].values()),
                         {3})

    def assert_replay(self, coordinator):
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

# --- IDEA-097 S4-F1 ER1–ER3, ER5: an expired command the execution service never claimed gives its attempt back ---

LEG = 'DISCRETIONARY:BUY:NVDAB'


def unclaimed_fact(intent, round_id, event_id, now_ms, **extra):
    return dict(schema='ExecutionObservation.v1', run_id='run', wallet_id='fake-wallet', round_id=round_id,
                intent_id=intent['intent_id'], event_id=event_id, kind='NOT_SUBMITTED', settlement='FINAL',
                origin='EXECUTION_RECONCILER', observed_at=datetime.fromtimestamp(now_ms / 1000, timezone.utc).isoformat(),
                intent_terminal=True, round_terminal=True, **extra)


class RefundUnclaimed(DurableBudget):
    """Runs only the S4-F1 tests on DurableBudget's fixture (the inherited EB3/5 tests run once, in DurableBudget)."""
    test_quote_child_reuses_parent_and_replays_from_the_parent_journal = None
    test_closed_rounds_restart_and_duplicate_round_cannot_restore_attempts = None
    test_budget_survives_midnight_weekend_and_resets_at_next_open = None
    test_exact_replay_reconstructs_budget_without_live_calendar_or_market = None

    def child(self, coordinator, round_id):
        self.quote_template = None  # the parent only asks for a quote; its child plans the intent
        self.start(coordinator, round_id.split('/')[0])
        snapshot = changed(snap(), markets=[m for m in self.context['markets'] if m['symbol'] == 'NVDAB'])
        self.quote_template = with_quotes(snapshot).context.read()['markets'][0]['quotes']
        self.start(coordinator, round_id, parent=round_id.split('/')[0])
        return self.store.load('run').read()['projection']['round_records'][round_id]['plan']['intents'][0]

    def budget(self):
        return self.store.load('run').read()['projection']['execution_attempt_budget']

    def test_er2_unclaimed_expiry_gives_the_latest_attempt_back_and_replays_exactly(self):
        coordinator = self.coordinator()
        intent = self.child(coordinator, 'a/quote1')
        self.assertEqual((intent['execution_bounds']['ordinal'], self.budget()['counts'][LEG]), (1, 1))
        coordinator.observe('a-expired', doc(unclaimed_fact(intent, 'a/quote1', 'a-expired', self.now, reason=EXPIRED_REASON,
                                                  attempt_refund=True)), settle)
        coordinator.close('a/quote1', self.now, 'COMPLETE')
        self.assertNotIn(LEG, self.budget()['counts'])
        self.assertNotIn(LEG, self.budget()['closed'])
        # The next chain plans the same leg at ordinal 1 again: the expired command spent nothing.
        retry = self.child(coordinator, 'b/quote1')
        self.assertEqual(retry['execution_bounds']['ordinal'], 1)
        coordinator.observe('b-expired', doc(unclaimed_fact(retry, 'b/quote1', 'b-expired', self.now, reason=EXPIRED_REASON,
                                                  attempt_refund=True)), settle)
        coordinator.close('b/quote1', self.now, 'COMPLETE')
        self.assertNotIn(LEG, self.budget()['counts'])
        self.assert_replay(coordinator)

    def test_er1_er3_no_refund_without_the_flag_or_for_a_refused_intent(self):
        coordinator = self.coordinator()
        intent = self.child(coordinator, 'a/quote1')
        # ER1/ER3: the old fact shape (no flag) keeps the attempt spent, as before this change.
        coordinator.observe('a-expired', doc(unclaimed_fact(intent, 'a/quote1', 'a-expired', self.now, reason=EXPIRED_REASON)),
                            settle)
        coordinator.close('a/quote1', self.now, 'COMPLETE')
        self.assertEqual(self.budget()['counts'][LEG], 1)
        retry = self.child(coordinator, 'b/quote1')
        self.assertEqual(retry['execution_bounds']['ordinal'], 2)
        # A refused intent (another reason) never refunds; the validator refuses the flag there (ER4).
        with self.assertRaises(ContractError):
            coordinator.observe('b-refused', doc(unclaimed_fact(retry, 'b/quote1', 'b-refused', self.now,
                                                      reason='ABORTED_BEFORE_SWAP_BROADCAST', attempt_refund=True)),
                                settle)
        coordinator.observe('b-refused', doc(unclaimed_fact(retry, 'b/quote1', 'b-refused', self.now,
                                                  reason='ABORTED_BEFORE_SWAP_BROADCAST')), settle)
        coordinator.close('b/quote1', self.now, 'COMPLETE')
        self.assertEqual(self.budget()['counts'][LEG], 2)
        self.assert_replay(coordinator)

    def test_er3_an_older_ordinal_or_another_session_is_not_refunded(self):
        from larp.integration.settlement import refund_attempt
        bounds = dict(session_index=80, leg=LEG, ordinal=1)
        for budget in (dict(session=80, counts={LEG: 2}, closed={LEG: 2}),   # a later attempt exists
                       dict(session=81, counts={LEG: 1}, closed={LEG: 1}),   # the session moved on
                       dict(session=80, counts={}, closed={})):              # nothing to give back
            projection = dict(execution_attempt_budget=dict(budget, counts=dict(budget['counts']),
                                                            closed=dict(budget['closed'])))
            refund_attempt(projection, dict(execution_bounds=bounds))
            self.assertEqual(projection['execution_attempt_budget'], budget)
        projection = dict(execution_attempt_budget=dict(session=80, counts={LEG: 3}, closed={LEG: 2}))
        refund_attempt(projection, dict(execution_bounds=dict(bounds, ordinal=3)))
        self.assertEqual(projection['execution_attempt_budget'], dict(session=80, counts={LEG: 2}, closed={LEG: 2}))
        for missing in (dict(), dict(execution_attempt_budget=None)):  # non-S1 rounds have no budget
            refund_attempt(missing, dict(execution_bounds=bounds))
            refund_attempt(dict(execution_attempt_budget=dict(session=80, counts={LEG: 1}, closed={})), dict())

    def test_rv01_broadcast_supporting_approval_cannot_refund(self):
        coordinator = self.coordinator()
        intent = self.child(coordinator, 'a/quote1')
        before = self.budget()
        coordinator.observe('approve', doc(dict(schema='ExecutionObservation.v1', run_id='run', wallet_id='fake-wallet',
            round_id='a/quote1', intent_id=intent['intent_id'], event_id='approve', kind='BROADCAST_ATTEMPTED',
            observed_at=datetime.fromtimestamp(self.now / 1000, timezone.utc).isoformat(), step='approve',
            tx_hash='0x' + 'a' * 64)), settle)
        with self.assertRaises(ContractError):
            coordinator.observe('bad-refund', doc(unclaimed_fact(intent, 'a/quote1', 'bad-refund', self.now,
                reason=EXPIRED_REASON, attempt_refund=True)), settle)
        self.assertEqual(self.budget(), before)
        coordinator.observe('ordinary-abort', doc(unclaimed_fact(intent, 'a/quote1', 'ordinary-abort', self.now,
            reason='ABORTED_BEFORE_SWAP_BROADCAST')), settle)
        coordinator.close('a/quote1', self.now, 'COMPLETE')
        self.assertEqual(self.budget()['counts'][LEG], 1)
        self.assert_replay(coordinator)

    def test_rv01_real_expire_skips_claimed_and_refunds_unclaimed(self):
        from unittest.mock import patch
        from larp.runtime.driver import ServiceExecution
        coordinator = self.coordinator()
        intent = self.child(coordinator, 'a/quote1')
        execution = ServiceExecution(coordinator, '0x' + '1' * 40, grace_ms=0)
        now = intent['expires_ms']
        with patch.object(execution, '_records', return_value={execution.key(intent['intent_id'])}):
            self.assertEqual(execution.expire(now), [])
        self.assertEqual(self.budget()['counts'][LEG], 1)
        self.assertEqual(execution.expire(now), [intent['intent_id']])
        self.assertNotIn(LEG, self.budget()['counts'])
        self.assertEqual(execution.expire(now), [])
        coordinator.close('a/quote1', now, 'COMPLETE')
        self.assert_replay(coordinator)

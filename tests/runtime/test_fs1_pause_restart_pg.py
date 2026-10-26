"""IDEA-108 RG-3: the F-127 activation schedule on real PostgreSQL with the FS1 self-check profile.

Self-check BUY, SELL and DONE; the project is paused across midnight; it restarts two hours after midnight (as on
2026-10-29T02:00Z); the day rolls late because the run is flat; the scored run's first plan after `trade_after`
buys. A control without the restart roll shows the failure the fix removes. Each leg uses a new coordinator, so
everything authoritative comes from PostgreSQL, and the journal replays exactly.
"""
from copy import deepcopy
from datetime import datetime

from larp.contracts import Document
from larp.integration.replay import replay_live
from larp.integration.runtime import (ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state,
                                      initial_projection, ledger_from)
from larp.integration.settlement import ExecutionBridge, settle
from larp.research.fixtures import changed, with_quotes
from larp.runtime.coordinator import Coordinator
from larp.runtime.driver import DayRoll
from larp.storage.postgres import doc
from tests.integration.test_settlement import observation
from tests.strategy.test_equal_weight import with_state
from tests.strategy.test_fs1_self_check import DURING, at_time
from tests.support import DatabaseCase, request

RUN = 'synthetic-run'
RESTART = '2026-10-11T02:00:00Z'  # two hours after the midnight the paused run missed (F-127: Oct 29 02:00Z)
# First scored plan: after trade_after (2026-10-11T00:00Z) and the restart, inside the fixture's one synthetic session
# (open 2026-10-10T13:30Z, valid to the next open 2026-10-11T13:30Z under KIT_OPEN_STATE hours, tests/strategy/test_s2_weekend.py).
FIRST_SCORED = '2026-10-11T03:00:00Z'
WINDOW_MS = 300_000  # the production window (larp/runtime/gate_a.py DAY_ROLL_MS), unchanged by the fix


def buying(plan):
    # FS1 enters in two steps: a fresh BUY quote request, then the order; either shows the book is being built.
    return [i['symbol'] for key in ('intents', 'quote_requests', 'execution_attempts')
            for i in plan[key] if i['side'] == 'BUY']


def ms(value):
    return int(datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp() * 1000)


class PauseAcrossMidnight(DatabaseCase):
    def start(self):
        self.fixture = at_time(DURING)
        context = self.fixture.context.read()
        self.p, self.ph = context['profile'], self.fixture.policy_profile_hash
        self.initial = initial_projection(context['portfolio'])
        self.store.initialize(RUN, 'fake-wallet', 56, doc(self.initial))
        self.store.takeover(RUN, 1, offline=True)
        self.rows, self.context = [], context

        def calendar(_):  # the leg's own fixture: its session and execution window
            return dict(index=self.context['session_index'], remaining=10)
        calendar.window = lambda _: self.context['execution_session']
        self.builder = ContextBuilder(profile=self.p, profile_hash=self.ph, run_id=RUN, issuers={},
                                      market=lambda _: deepcopy(self.rows), health=lambda _: self.context['health'],
                                      calendar=calendar)

    def coordinator(self, now):
        # A new coordinator each time: a process restart between legs.
        return Coordinator(self.store, None, StrategyPolicy(),
                           RuntimePlanner(job_validity_ms=60000, job_max_attempts=3), execution=ExecutionBridge(),
                           run_id=RUN, version_id='fs1-pause', profile_hash=self.ph, address='0x' + '1' * 40,
                           context_builder=self.builder, initial_policy_state=initial_policy_state(RUN, self.p),
                           clock_ms=lambda: now)

    def observe_rows(self, fixture):
        self.context = fixture.context.read()
        current = self.store.load(RUN).read()
        snapshot = changed(fixture, portfolio=ledger_from(current['projection'], current['reservations']))
        if current.get('policy_state'):
            snapshot = with_state(snapshot, current['policy_state']['data'])
        self.rows[:] = with_quotes(snapshot).context.read()['markets']

    def leg(self, name, at, *, fill=True):
        fixture = at_time(at)
        now = int(fixture.observed_at.timestamp() * 1000)
        self.observe_rows(fixture)
        coordinator = self.coordinator(now)
        req = request(job=name, cutoff=now).read()
        req.update(run_id=RUN, policy_profile_hash=self.ph, evidence_refs=[])
        coordinator.start(name, doc(req), now, use_accepted_evidence=True)
        result = self.store.event(RUN, 'plan:' + name)['record']['plan']
        if fill:
            for k, planned in enumerate(result['intents']):
                f = dict(symbol=planned['symbol'], side=planned['side'], fee_units=0,
                         token_units=planned['min_receive_units'] if planned['side'] == 'BUY' else planned['pay_units'],
                         cash_units=planned['pay_units'] if planned['side'] == 'BUY' else planned['min_receive_units'])
                for kind, fields in [('BROADCAST_ATTEMPTED', {}), ('FILL', f)]:
                    event = name + '-' + str(k) + '-' + kind
                    o = observation(planned, name, event, kind, observed_at=fixture.observed_at.isoformat(),
                                    tx_hash='0x' + format(len(name) * 100 + k + 1, '064x'), **fields)
                    coordinator.observe(event, Document.from_dict(o), settle)
        coordinator.close(name, now, 'COMPLETE')
        return result

    def self_check(self):
        bought = self.leg('self-check-buy', DURING)
        self.assertEqual([(i['symbol'], i['side']) for i in bought['intents']], [('SKHYB', 'BUY')])
        sold = self.leg('self-check-sell', DURING)
        self.assertEqual([(i['symbol'], i['side']) for i in sold['intents']], [('SKHYB', 'SELL')])
        done = self.leg('self-check-done', DURING)
        self.assertEqual(done['risk_state']['activation_self_check'], 'DONE')
        current = self.store.load(RUN).read()
        self.assertTrue(DayRoll.flat(current))  # paused flat (F-127 10:00Z)
        return current

    def risk_day(self):
        projection = self.store.load(RUN).read()['projection']
        return (projection.get('risk_state') or projection['portfolio']['risk'])['day']

    def test_rg3_paused_flat_restart_rolls_late_and_the_scored_run_buys(self):
        self.start()
        self.self_check()
        before_day = self.risk_day()
        restart = ms(RESTART)
        self.observe_rows(at_time(RESTART))
        roll = DayRoll(self.coordinator(restart), window_ms=WINDOW_MS)
        self.assertTrue(roll.due(self.store.load(RUN).read(), restart))
        self.assertEqual(roll(restart, deepcopy(self.rows)), 'ROLLED')
        event = self.store.event(RUN, 'day:' + RESTART[:10])
        self.assertTrue(event['late_flat'])
        self.assertEqual((before_day < RESTART[:10], self.risk_day()), (True, RESTART[:10]))
        self.assertIsNone(roll(restart + 60_000, deepcopy(self.rows)))  # once per day
        scored = self.leg('scored-first', FIRST_SCORED, fill=False)
        self.assertTrue(buying(scored), scored)
        self.assertNotIn('NEW_RISK_HALTED', {r['reason'] for r in scored['rejections']})
        self.replay()

    def test_rg3_control_without_the_restart_roll_the_scored_day_buys_nothing(self):
        self.start()
        self.self_check()
        scored = self.leg('scored-first', FIRST_SCORED, fill=False)
        self.assertFalse(buying(scored))
        self.assertIn('NEW_RISK_HALTED', {r['reason'] for r in scored['rejections']})

    def replay(self):
        journal, expected = self.store.journal(RUN), self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        dead = lambda *a: (_ for _ in ()).throw(AssertionError('external port called in replay'))
        self.builder.market = self.builder.calendar = self.builder.health = dead
        actual = replay_live(journal, doc(self.initial), self.store, builder=self.builder, run_id=RUN,
                             wallet_id='fake-wallet', chain_id=56, version_id='fs1-pause', profile_hash=self.ph,
                             address='0x' + '1' * 40, policy=StrategyPolicy(),
                             planner=RuntimePlanner(job_validity_ms=60000, job_max_attempts=3),
                             execution=ExecutionBridge(), reducer=settle,
                             initial_policy_state=initial_policy_state(RUN, self.p))
        self.assertEqual(actual, expected)

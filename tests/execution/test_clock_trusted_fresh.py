"""IDEA-111: `clock_trusted` compares the last decision with a clock read after the projection, not the cycle start.

The TEMP-SC run (2026-10-28) approved three times and never swapped: the cycle that prepared each swap started
before the runtime committed a round, so the cycle's `now` was more than a second behind `last_decision_ms`.
Synthetic store only; the numbers are the 04:01 case from that run.
"""
import unittest
from unittest.mock import patch

from larp.storage.postgres import doc
from larp.execution_live.loop import RunAuthorization
from tests.execution import test_execution_loop as loop_fixtures
from tests.execution import test_router_wiring as wiring
from tests.execution_fixtures import intent

BUILD = 'version'
CYCLE_NOW = 1793160060           # the cycle started at or before 04:01:00Z
LAST_DECISION_MS = 1793160062036  # the runtime's round committed during that cycle


class Store:
    """The journal reads `RunAuthorization.facts` makes, with every fact except the clock passing."""

    def __init__(self, *, last_decision_ms=LAST_DECISION_MS, halt=None):
        self.economic = intent(version_id=BUILD)
        self.loaded = 0
        record = dict(plan=dict(intents=[dict(intent_id=self.economic.intent_id)]), final_intents=[])
        self.projection = dict(registered_version=dict(build_id=BUILD), last_decision_ms=last_decision_ms,
                               round_records={self.economic.round_id: record}, portfolio={})
        if halt:
            self.projection['halt'] = dict(reasons={halt: {}})
        self.record = record

    def verified_snapshot(self, run_id, full=True):
        return None

    def load(self, run_id):
        self.loaded += 1
        return doc(dict(mode='offline', quarantined=False, projection=self.projection,
            reservations=[dict(intent_id=self.economic.intent_id, asset=a, units=1) for a in ('USDT', 'BNB')]))

    def event(self, run_id, event_id):
        return dict(kind='ROUND_PLANNED', record=self.record)


class Clock:
    """Records whether the projection had been loaded when it was read."""

    def __init__(self, store, *readings):
        self.store, self.readings, self.reads = store, list(readings), []

    def __call__(self):
        self.reads.append(self.store.loaded)
        return self.readings.pop(0)


def facts(store, clock=None, now_s=CYCLE_NOW):
    return RunAuthorization(store, run_id='run', build_id=BUILD, clock_s=clock).facts(store.economic, now_s)


class FreshDecisionClock(unittest.TestCase):
    def test_ct1_round_committed_mid_cycle_is_trusted_with_a_fresh_reading(self):
        store = Store()
        stale = RunAuthorization(store, run_id='run', build_id=BUILD).facts(store.economic, CYCLE_NOW)
        self.assertFalse(stale['clock_trusted'])  # the TEMP-SC refusal, unchanged without a clock
        fresh = facts(store, Clock(store, CYCLE_NOW + 3))
        self.assertTrue(fresh['clock_trusted'])
        self.assertEqual({k: v for k, v in fresh.items() if k != 'clock_trusted'},
                         {k: v for k, v in stale.items() if k != 'clock_trusted'})
        self.assertTrue(all(fresh[k] is True for k in ('audit_durable', 'reservation_valid', 'version_valid',
                                                        'risk_valid', 'health_valid')))

    def test_ct2_genuine_clock_problems_still_refuse(self):
        cases = {
            'reading behind the last decision': (Store(), CYCLE_NOW + 1),
            'reading behind the cycle': (Store(last_decision_ms=1000), CYCLE_NOW - 1),
            'non-integer reading': (Store(), float(CYCLE_NOW + 3)),
            'CLOCK halt': (Store(halt='CLOCK'), CYCLE_NOW + 3),
        }
        for name, (store, reading) in cases.items():
            with self.subTest(name):
                self.assertFalse(facts(store, Clock(store, reading))['clock_trusted'])
        # PR325-RV01: at now_s 0 a True reading (== 1) passes the backward and decision checks, so only the type
        # check can refuse it.
        store = Store(last_decision_ms=0)
        self.assertTrue(facts(store, Clock(store, 1), now_s=0)['clock_trusted'])
        self.assertFalse(facts(store, Clock(store, True), now_s=0)['clock_trusted'])

    def test_ct2_tolerance_boundary_is_unchanged(self):
        store = Store(last_decision_ms=(CYCLE_NOW + 2) * 1000 + 1000)
        self.assertTrue(facts(store, Clock(store, CYCLE_NOW + 2))['clock_trusted'])
        store = Store(last_decision_ms=(CYCLE_NOW + 2) * 1000 + 1001)
        self.assertFalse(facts(store, Clock(store, CYCLE_NOW + 2))['clock_trusted'])

    def test_ct3_clock_is_read_once_after_the_projection_load(self):
        store = Store()
        clock = Clock(store, CYCLE_NOW + 3)
        facts(store, clock)
        self.assertEqual(clock.reads, [1])

    def test_ct1_other_facts_keep_the_callers_time(self):
        store = Store()
        seen = []
        def permitted(projection, economic, now_ms):
            seen.append(now_ms)
            return True
        with patch('larp.strategy.execution_bounds.permitted', permitted):
            facts(store, Clock(store, CYCLE_NOW + 3))
        self.assertEqual(seen, [CYCLE_NOW * 1000])  # the risk windows keep the caller's time, not the fresh reading


class Wiring(unittest.TestCase):
    setUp = loop_fixtures.Composition.setUp
    pin = wiring.ExecutionService.pin

    def test_ct4_executor_clock_reaches_the_guard_authorization(self):
        clock = lambda: CYCLE_NOW
        loop = wiring.build_execution(self.pin(), loop_fixtures.Store(), self.secrets, clock_s=clock)
        executor = loop.service.executor
        self.assertIs(executor.clock_s, clock)
        self.assertIs(executor.guards.authorization.clock_s, clock)


if __name__ == '__main__':
    unittest.main()

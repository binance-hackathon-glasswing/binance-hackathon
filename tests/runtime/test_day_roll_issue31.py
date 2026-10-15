"""IDEA-050 D31 (#31 acceptance 2-3): the UTC day roll across days, restarts and missed boundaries.

D31-1..D31-5 run the real driver, `DayRoll` and `Service` on disposable PostgreSQL with the synthetic ports of
`tests/runtime/test_round_driver_service.py`. D31-6 runs the real planner on the research fixtures. Nothing is signed.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from larp.contracts import Document
from larp.research.fixtures import changed, with_quotes
from larp.risk.accounting import roll_day
from larp.risk.planner import plan
from larp.runtime.coordinator import batch_for
from larp.runtime.service import Service
from larp.runtime.supervision import Guard
from larp.strategy.policy import decide
from larp.strategy.schema import equity, market_view
from tests.risk.test_live_resource_receipts import gas_quote
from tests.runtime.test_round_driver_service import RUN, SECOND, VERSION, ServiceHarness
from tests.strategy.live_fixtures import live_snapshot
from tests.strategy.test_equal_weight import ew

WINDOW = 15 * 60 * SECOND  # the E8 test value; the production value is a team decision (#31)
PRICE = 100_000_000  # the pipeline fixture's mark


def midnight_after(day, days=1):
    return int((datetime.fromisoformat(day).replace(tzinfo=timezone.utc) + timedelta(days=days)).timestamp() * 1000)


def date_of(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat()


class Crash(Exception):
    pass


class DayRollHarness(ServiceHarness):
    def setUp(self):
        super().setUp()
        self.price = PRICE

    def priced(self, now_ms):
        return [dict(m, price_units=self.price) for m in self.market(now_ms)]

    def driver(self, *, rounds=False):
        driver = self.service_driver(market=self.priced, day_roll_window_ms=WINDOW, cadence=rounds)
        if not rounds:
            driver.work.next = lambda now_ms, epoch: None  # the roll alone; D31-5 keeps the rounds
        return driver

    def risk(self):
        projection = self.store.load(RUN).read()['projection']
        return projection.get('risk_state') or projection['portfolio']['risk']

    def rolls(self):
        return [d.read()['event'] for d in self.store.journal(RUN) if d.read()['event']['kind'] == 'DAY_ROLLED']

    def expected_anchor(self, driver, now_ms):
        current = self.store.load(RUN).read()
        builder = driver.coordinator.context_builder
        marks = market_view(self.priced(now_ms), builder.universe, datetime.fromtimestamp(now_ms / 1000, timezone.utc),
                            self.profile)
        return int(equity(current['projection']['portfolio'], marks))

    def at(self, ms):
        self.w.clock.now = ms
        return ms


class ConsecutiveDays(DayRollHarness):
    def test_d31_1_one_roll_per_day_over_three_days_in_one_process(self):
        start = self.risk()['day']
        driver = self.driver()
        anchors = []
        for n, price in ((1, PRICE), (2, PRICE * 9 // 10), (3, PRICE * 11 // 10)):
            self.price = price
            now = self.at(midnight_after(start, n) + 60 * SECOND)
            self.assertEqual(driver.once(now)['day_roll'], 'ROLLED')
            day = date_of(now)
            event = self.store.event(RUN, 'day:' + day)
            self.assertEqual((event['day'], event['boundary']),
                             (day, datetime.fromtimestamp(midnight_after(start, n) / 1000, timezone.utc).isoformat()))
            self.assertEqual(event['anchor_units'], self.expected_anchor(driver, now))
            self.assertEqual((self.risk()['day'], self.risk()['day_anchor_units']), (day, event['anchor_units']))
            anchors.append(event['anchor_units'])
            self.at(now + 5 * 60 * SECOND)  # still inside the window: the same day never rolls twice
            self.assertNotIn('day_roll', driver.once(self.w.clock()))
        self.assertEqual(len(set(anchors)), 3)  # each day's anchor is that day's marks
        self.assertEqual([e['day'] for e in self.rolls()], [date_of(midnight_after(start, n)) for n in (1, 2, 3)])
        head, expected = self.replay_head(driver)
        self.assertEqual(head, expected)


class RestartAcrossMidnight(DayRollHarness):
    def service(self, driver):
        return Service(self.store, RUN, VERSION, guard=Guard(self.store, RUN, max_failures=3, clear_after=2),
                       driver=driver, clock_ms=self.w.clock, sleep=lambda s: None)

    def test_d31_2_a_restarted_service_rolls_once_after_midnight(self):
        start = self.risk()['day']
        midnight = midnight_after(start)
        self.at(midnight - 60 * SECOND)
        self.assertEqual(self.service(self.driver()).run(max_cycles=1), 0)
        self.assertEqual((self.rolls(), self.risk()['day']), ([], start))  # not due before midnight
        self.at(midnight + 2 * 60 * SECOND)
        self.assertEqual(self.service(self.driver()).run(max_cycles=1), 0)
        self.assertEqual(self.risk()['day'], date_of(midnight))
        self.at(midnight + 4 * 60 * SECOND)
        self.assertEqual(self.service(self.driver()).run(max_cycles=1), 0)
        self.assertEqual([e['day'] for e in self.rolls()], [date_of(midnight)])
        head, expected = self.replay_head(self.driver())
        self.assertEqual(head, expected)

    def test_d31_2_a_crash_after_the_roll_commits_does_not_roll_again(self):
        start = self.risk()['day']
        midnight = midnight_after(start)
        crashing = self.driver()

        def crash(now_ms, epoch):
            raise Crash()
        crashing.work.next = crash  # the process dies after the roll, before the cycle's round
        self.at(midnight + 60 * SECOND)
        with self.assertRaises(Crash):
            self.service(crashing).run(max_cycles=1)
        self.assertEqual(self.risk()['day'], date_of(midnight))
        self.at(midnight + 2 * 60 * SECOND)
        self.assertEqual(self.service(self.driver()).run(max_cycles=1), 0)  # RESTART incident, then a cycle
        self.assertEqual([e['day'] for e in self.rolls()], [date_of(midnight)])


class MissedBoundary(DayRollHarness):
    def test_d31_3_a_missed_window_blocks_the_day_and_the_next_midnight_rolls(self):
        start = self.risk()
        missed = midnight_after(start['day'])
        driver = self.driver()
        self.at(missed + WINDOW + 60 * SECOND)  # the process was down through the whole window
        self.assertEqual(driver.once(self.w.clock())['day_roll'], 'OUTSIDE_WINDOW')
        self.price = PRICE // 2  # a post-loss mark later the same day must never become the anchor
        self.at(missed + 6 * 3_600_000)
        self.assertEqual(driver.once(self.w.clock())['day_roll'], 'OUTSIDE_WINDOW')
        self.assertEqual(self.risk(), start)
        self.assertEqual(self.rolls(), [])
        self.assertIsNone(self.store.event(RUN, 'day:' + date_of(missed)))
        self.price = PRICE * 3 // 4
        now = self.at(midnight_after(start['day'], 2) + 60 * SECOND)
        self.assertEqual(driver.once(now)['day_roll'], 'ROLLED')
        [event] = self.rolls()
        self.assertEqual(event['day'], date_of(now))
        self.assertEqual(event['anchor_units'], self.expected_anchor(driver, now))
        self.assertIsNone(self.store.event(RUN, 'day:' + date_of(missed)))
        head, expected = self.replay_head(driver)
        self.assertEqual(head, expected)


class Latches(DayRollHarness):
    def test_d31_4_the_roll_keeps_the_run_latches_and_clears_only_the_daily_halt(self):
        current = self.store.load(RUN)
        projection = current.read()['projection']
        risk = dict(projection.get('risk_state') or projection['portfolio']['risk'])
        risk.update(peak_units=risk['peak_units'] * 2, run_halt=True, deep_cut=True, daily_halt=True)
        projection['risk_state'] = risk
        self.store.commit(batch_for(current, 'test:latches', dict(kind='SYNTHETIC'), projection=projection))
        driver = self.driver()
        now = self.at(midnight_after(risk['day']) + 60 * SECOND)
        self.assertEqual(driver.once(now)['day_roll'], 'ROLLED')
        rolled = self.risk()
        self.assertEqual({k: rolled[k] for k in ('peak_units', 'run_halt', 'deep_cut')},
                         {k: risk[k] for k in ('peak_units', 'run_halt', 'deep_cut')})
        self.assertEqual((rolled['day'], rolled['daily_halt'], rolled['day_anchor_units']),
                         (date_of(now), False, self.store.event(RUN, 'day:' + date_of(now))['anchor_units']))


class RoundsReadTheRoll(DayRollHarness):
    def round_risk(self, round_id):
        record = self.store.load(RUN).read()['projection']['round_records'][round_id]
        return record['policy_input']['context']['portfolio']['risk']

    def test_d31_5_a_round_after_the_roll_sees_the_new_day(self):
        start = self.risk()['day']
        driver = self.driver(rounds=True)
        now = self.at(midnight_after(start) + 60 * SECOND)
        summary = driver.once(now)
        self.assertEqual(summary['day_roll'], 'ROLLED')
        self.assertIsNotNone(summary['round_id'])
        self.assertEqual(self.round_risk(summary['round_id'])['day'], date_of(now))

    def test_d31_5_a_round_on_a_missed_day_sees_the_stale_day(self):
        start = self.risk()['day']
        driver = self.driver(rounds=True)
        summary = driver.once(self.at(midnight_after(start) + WINDOW + 60 * SECOND))
        self.assertEqual(summary['day_roll'], 'OUTSIDE_WINDOW')
        self.assertIsNotNone(summary['round_id'])
        self.assertEqual(self.round_risk(summary['round_id'])['day'], start)


def yesterday(s):
    """The snapshot with its risk state one UTC day behind: the boundary was missed."""
    c = s.context.read()
    c['portfolio']['risk']['day'] = (s.observed_at.date() - timedelta(days=1)).isoformat()
    return changed(s, portfolio=c['portfolio'])


def rolled(s, **latches):
    """The risk state as `DayRoll` commits it: `roll_day` at today's midnight, anchored at the snapshot's marks."""
    c = s.context.read()
    c['portfolio']['risk'].update(latches)
    marks = market_view(c['markets'], s.universe, s.observed_at, c['profile'])
    midnight = s.observed_at.replace(hour=0, minute=0, second=0, microsecond=0)
    ledger = roll_day(Document.from_dict(c['portfolio']), boundary=midnight.isoformat(),
                      anchor_units=int(equity(c['portfolio'], marks))).read()
    return changed(s, portfolio=ledger)


def buys(s):
    r = plan(s, decide(s, s.policy_state)).read()
    return [i for i in r['intents'] if i['side'] == 'BUY'], {x['reason'] for x in r['rejections']}


def top_ups(s):
    r = plan(changed(s, gas_quotes=[gas_quote(s)]), None).read()
    return ([i for i in r['intents'] if i.get('kind') == 'GAS_TOP_UP'], {x['reason'] for x in r['rejections']},
            [q for q in r['quote_requests'] if q.get('kind') == 'GAS_TOP_UP'])


class PlannerGate(unittest.TestCase):
    """D31-6: entries and gas top-ups resume only after a valid new-day anchor; the run latches survive it."""

    def entry(self):
        s = with_quotes(ew())
        self.assertTrue(buys(s)[0])  # the control: today's anchor, the planner buys
        return s

    def gas(self):
        s = live_snapshot(gas_low=True, held={'NVDAB': 4000, 'GOOGLB': 4000, 'TSLAB': 4000, 'MSFTB': 4000})
        self.assertTrue(top_ups(s)[0])
        return s

    def test_d31_6_a_stale_day_refuses_entries_until_the_roll(self):
        stale = yesterday(self.entry())
        intents, reasons = buys(stale)
        self.assertEqual(intents, [])
        self.assertIn('NEW_RISK_HALTED', reasons)
        intents, reasons = buys(rolled(stale))
        self.assertTrue(intents)
        self.assertNotIn('NEW_RISK_HALTED', reasons)

    def test_d31_6_a_stale_day_refuses_gas_top_ups_until_the_roll(self):
        stale = yesterday(self.gas())
        intents, reasons, requests = top_ups(stale)
        self.assertEqual((intents, requests), ([], []))
        self.assertIn('GAS_TOP_UP_SPENDING_BLOCKED', reasons)
        intents, reasons, _ = top_ups(rolled(stale))
        self.assertEqual(len(intents), 1)
        self.assertNotIn('GAS_TOP_UP_SPENDING_BLOCKED', reasons)

    def test_d31_6_the_roll_does_not_lift_a_run_latch(self):
        # `update_risk` latches run_halt at 92% of the peak and deep_cut at 88%, so deep_cut never comes alone.
        for latches in (dict(run_halt=True), dict(run_halt=True, deep_cut=True)):
            with self.subTest(**latches):
                intents, reasons = buys(rolled(yesterday(self.entry()), **latches))
                self.assertEqual(intents, [])
                self.assertIn('NEW_RISK_HALTED', reasons)
                intents, _, _ = top_ups(rolled(yesterday(self.gas()), **latches))
                self.assertEqual(intents, [])  # the reason depends on the path, as in the barrier test


if __name__ == '__main__':
    unittest.main()

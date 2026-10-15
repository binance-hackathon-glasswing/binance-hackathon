"""IDEA-049-D WR-T1..6: real driver/coordinator/planner on PostgreSQL; synthetic external inputs."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from larp.contracts import Document
from larp.integration.runtime import initial_projection
from larp.research.fixtures import snapshot
from larp.runtime.coordinator import batch_for
from larp.runtime.service import Service
from larp.runtime.supervision import Guard
from larp.strategy.schema import equity, market_view
from tests.runtime.test_round_driver_service import RUN, SECOND, VERSION, ServiceHarness, pipeline

WINDOW = 15 * 60 * SECOND  # fixture only; the production window remains a team decision


def midnight(day, days=1):
    return int((datetime.fromisoformat(day).replace(tzinfo=timezone.utc) + timedelta(days=days)).timestamp() * 1000)


def date_of(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat()


class EntryMarket:
    """Synthetic fresh marks/history and exact-input RFQs; never calls a venue."""
    def __init__(self):
        self.price = 100_000_000
        self.requests = []

    def context(self, now):
        s = snapshot(now=datetime.fromtimestamp(now / 1000, timezone.utc))
        return s.context.read()

    def __call__(self, now):
        return [dict(m, price_units=self.price) for m in self.context(now)['markets']]

    def observe(self, request):
        self.requests.append(dict(request))
        now = self.clock()
        market = next(m for m in self(now) if m['symbol'] == request['symbol'])
        pay = request['pay_units']
        units = pay * 10**market['decimals'] * 10000 // (market['price_units'] * 10010)
        at = datetime.fromtimestamp(now / 1000, timezone.utc)
        market['quotes'] = [dict(quote_id='wr-t-buy-' + str(pay), side='BUY', token_units=units,
            amount_kind='EXACT_IN', pay_asset='USDT', pay_units=pay, cash_units=pay,
            min_receive_units=units * 9980 // 10000, fee_units=0, gas_bnb_units=10000,
            route_valid=True, slippage_bps=20, impact_bps=10, quoted_depth_units=units * 100,
            observed_at=at.isoformat(), available_at=at.isoformat(),
            expires_at=(at + timedelta(seconds=30)).isoformat(), origin='SCRIPTED_FAKE')]
        return market


class DailyAnchorWindow(ServiceHarness):
    def prepare(self, *, rounds=False, gas=False, flat=False, **latches):
        # Seed the initial database state, rather than forging a risk event that replay cannot reproduce.
        self.initial = pipeline.pipeline_ledger()
        self.initial['risk'].update(peak_units=205_000_000, daily_halt=True, **latches)
        if flat:
            for position in self.initial['positions'].values():
                self.initial['cash_units'] += position['cost_basis_units']
                position.update(units=0, cost_basis_units=0)
        if gas:
            self.initial['bnb_units'] = 60_000
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        self.store.initialize(RUN, 'fake-wallet', 56, Document.from_dict(initial_projection(self.initial)))
        self.epoch = self.store.takeover(RUN, 1, offline=True)
        current = self.store.load(RUN)
        projection = current.read()['projection']
        projection['registered_version'] = dict(build_id=VERSION, manifest_sha256='0' * 64)
        self.store.commit(batch_for(current, 'version:fixture', dict(kind='VERSION_REGISTERED',
                                    version=projection['registered_version']), projection=projection))
        self.world(['EXSEMI_Q2_8K'], now_ms=getattr(self, 'world_number', 0) + 1)
        self.world_number = getattr(self, 'world_number', 0) + 1  # distinct neutral evidence stores
        self.feed = EntryMarket()
        self.feed.clock = self.w.clock
        self.gas = gas
        return self.driver(rounds=rounds)

    def driver(self, *, rounds=False):
        from larp.research.fixtures import synthetic_profile
        changes = dict(gas_floor_bnb_units=100_000, gas_top_up_cash_units=1_000_000) if self.gas else {}
        with patch('tests.runtime.test_round_driver_service.synthetic_profile',
                   side_effect=lambda **kw: synthetic_profile(**kw, **changes)):
            driver = self.service_driver(market=self.feed, day_roll_window_ms=WINDOW,
                                         cadence=rounds, max_quote_rounds=1 if rounds and not self.gas else 0)
        driver.coordinator.context_builder.series = lambda now: self.feed.context(now)['series']
        if not rounds:
            driver.work.next = lambda now, epoch: None
        return driver

    def risk(self):
        p = self.store.load(RUN).read()['projection']
        return p.get('risk_state') or p['portfolio']['risk']

    def events(self, kind):
        return [b.read()['event'] for b in self.store.journal(RUN) if b.read()['event']['kind'] == kind]

    def tick(self, driver, now):
        self.w.clock.now = now
        return driver.once(now)

    def plan_for(self, summary):
        self.assertIsNotNone(summary['round_id'], summary)
        rid = summary.get('quote_round_id', summary['round_id'])
        return self.store.event(RUN, 'plan:' + rid)['record']['plan']

    def stable_latches(self, before):
        self.assertEqual({k: self.risk()[k] for k in ('peak_units', 'run_halt', 'deep_cut')},
                         {k: before[k] for k in ('peak_units', 'run_halt', 'deep_cut')})

    def replay(self, driver):
        with patch.object(pipeline, 'pipeline_ledger', return_value=deepcopy(self.initial)):
            head, expected = self.replay_head(driver)
        self.assertEqual(head, expected)

    def service(self, driver):
        return Service(self.store, RUN, VERSION, guard=Guard(self.store, RUN, max_failures=3, clear_after=2),
                       driver=driver, clock_ms=self.w.clock, sleep=lambda s: None)

    def crash(self, driver, now):
        service = self.service(driver)
        service.sessions.begin(session_id=service.session_id, build_id=VERSION, now_ms=now)
        self.tick(driver, now)  # process dies with its session open, as in the existing Restart harness
        return service.session_id

    def test_wr_t1_consecutive_days_in_one_run(self):
        driver = self.prepare(run_halt=True, deep_cut=True)
        before = self.risk()
        anchors = []
        for n, price in enumerate((100_000_000, 90_000_000, 110_000_000), 1):
            self.feed.price = price
            boundary = midnight(before['day'], n)
            now = boundary + 60 * SECOND
            self.assertEqual(self.tick(driver, now)['day_roll'], 'ROLLED')
            day = date_of(now)
            event = self.store.event(RUN, 'day:' + day)
            self.assertEqual(event['boundary'], datetime.fromtimestamp(boundary / 1000, timezone.utc).isoformat())
            marks = market_view(self.feed(now), driver.coordinator.context_builder.universe,
                                datetime.fromtimestamp(now / 1000, timezone.utc), self.profile)
            expected = int(equity(self.store.load(RUN).read()['projection']['portfolio'], marks))
            self.assertEqual((event['anchor_units'], self.risk()['day_anchor_units']), (expected, expected))
            self.assertEqual(self.risk()['day'], day)
            self.assertFalse(self.risk()['daily_halt'])
            self.stable_latches(before)
            anchors.append(expected)
            for later in (5 * 60 * SECOND, 23 * 3_600_000):
                self.assertNotIn('day_roll', self.tick(driver, boundary + later))
        self.assertEqual(len(set(anchors)), 3)
        self.assertEqual([e['day'] for e in self.events('DAY_ROLLED')],
                         [date_of(midnight(before['day'], n)) for n in (1, 2, 3)])
        self.replay(driver)

    def test_wr_t2_a_missed_boundary_blocks_that_day_and_the_next_one_rolls(self):
        driver = self.prepare()
        before = self.risk()
        self.feed.price = 50_000_000
        for offset in (30 * 60 * SECOND, 12 * 3_600_000, 24 * 3_600_000 - 60 * SECOND):
            self.assertEqual(self.tick(driver, midnight(before['day']) + offset)['day_roll'], 'OUTSIDE_WINDOW')
            self.assertEqual(self.risk(), before)
            self.assertEqual(self.events('DAY_ROLLED'), [])
        now = midnight(before['day'], 2) + 60 * SECOND
        self.assertEqual(self.tick(driver, now)['day_roll'], 'ROLLED')
        [event] = self.events('DAY_ROLLED')
        self.assertEqual((event['day'], event['anchor_units']), (date_of(now), 190_000_000))
        self.assertIsNone(self.store.event(RUN, 'day:' + date_of(midnight(before['day']))))
        self.replay(driver)

    def test_wr_t3_a_restart_across_midnight_rolls_exactly_once(self):
        driver = self.prepare()
        boundary = midnight(self.risk()['day'])
        crashed = self.crash(driver, boundary - 30 * SECOND)
        self.w.clock.now = boundary + 60 * SECOND
        driver_b = self.driver()
        self.assertEqual(self.service(driver_b).run(max_cycles=1), 0)
        [incident] = self.events('INCIDENT')
        self.assertEqual(incident['incident']['type'], 'RESTART')
        self.assertEqual(incident['incident']['previous_sessions'], [crashed])
        self.w.clock.now = boundary + 5 * 60 * SECOND
        driver_c = self.driver()
        self.assertEqual(self.service(driver_c).run(max_cycles=1), 0)
        self.assertEqual([e['day'] for e in self.events('DAY_ROLLED')], [date_of(boundary)])
        self.replay(driver_c)

    def test_wr_t3b_a_restart_after_the_window_never_resets_from_a_post_loss_mark(self):
        driver = self.prepare()
        before = self.risk()
        boundary = midnight(before['day'])
        self.crash(driver, boundary - 30 * SECOND)
        self.feed.price = 50_000_000
        for offset in (30 * 60 * SECOND, 12 * 3_600_000):
            self.w.clock.now = boundary + offset
            self.assertEqual(self.service(self.driver()).run(max_cycles=1), 0)
            self.assertEqual(self.risk(), before)
            self.assertEqual(self.events('DAY_ROLLED'), [])
        self.assertEqual(self.events('INCIDENT')[0]['incident']['type'], 'RESTART')

    def test_wr_t4_stock_entries_resume_only_after_a_valid_new_day_anchor(self):
        driver = self.prepare(rounds=True)
        before = self.risk()
        blocked = self.plan_for(self.tick(driver, midnight(before['day']) + 30 * 60 * SECOND))
        self.assertFalse([i for i in blocked['intents'] if i['side'] == 'BUY'])
        self.assertIn('NEW_RISK_HALTED', {r['reason'] for r in blocked['rejections']})
        summary = self.tick(driver, midnight(before['day'], 2) + 60 * SECOND)
        self.assertEqual(summary['day_roll'], 'ROLLED')
        resumed = self.plan_for(summary)
        self.assertTrue([i for i in resumed['intents'] if i['side'] == 'BUY'], resumed)
        self.stable_latches(before)
        self.assertFalse(self.risk()['daily_halt'])

    def test_wr_t5_gas_top_ups_resume_only_after_a_valid_new_day_anchor(self):
        driver = self.prepare(rounds=True, gas=True)
        before = self.risk()
        blocked = self.plan_for(self.tick(driver, midnight(before['day']) + 30 * 60 * SECOND))
        self.assertIn('GAS_TOP_UP_SPENDING_BLOCKED', {r['reason'] for r in blocked['rejections']})
        self.assertFalse([i for i in blocked['intents'] + blocked['quote_requests'] if i['symbol'] == 'BNB'])
        summary = self.tick(driver, midnight(before['day'], 2) + 60 * SECOND)
        self.assertEqual(summary['day_roll'], 'ROLLED')
        resumed = self.plan_for(summary)
        self.assertNotIn('GAS_TOP_UP_SPENDING_BLOCKED', {r['reason'] for r in resumed['rejections']})
        self.assertTrue([q for q in resumed['quote_requests'] if q['symbol'] == 'BNB'])
        self.stable_latches(before)

    def test_wr_t6_a_valid_anchor_does_not_clear_run_halt_or_deep_cut(self):
        # Deep cut is reached after the lower run-halt threshold; use reachable persisted states.
        for latches in (dict(run_halt=True), dict(run_halt=True, deep_cut=True)):
            for gas in (False, True):
                with self.subTest(latches=latches, gas=gas):
                    # No remaining holding to liquidate: the planner must expose its entry/gas refusal.
                    driver = self.prepare(rounds=True, gas=gas, flat=True, **latches)
                    before = self.risk()
                    summary = self.tick(driver, midnight(before['day']) + 60 * SECOND)
                    self.assertEqual(summary['day_roll'], 'ROLLED')
                    result = self.plan_for(summary)
                    self.assertIn('GAS_TOP_UP_SPENDING_BLOCKED' if gas else 'NEW_RISK_HALTED',
                                  {r['reason'] for r in result['rejections']})
                    self.assertFalse([i for i in result['intents'] if i['side'] == 'BUY'])
                    self.assertFalse([q for q in result['quote_requests'] if q['symbol'] == 'BNB'])
                    self.assertFalse(self.risk()['daily_halt'])
                    self.stable_latches(before)

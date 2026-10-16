"""IDEA-055 PR 4, S1-S16: self-healing chain-balance reconciliation ("chain wins", owner decisions 2026-10-16).

S1, S2 and S12's planner part are pure. The rest run the real driver, coordinator, planner and settlement on
disposable PostgreSQL with a synthetic chain and synthetic marks. No credentials, network, signing or upload.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import unittest

from larp.contracts import ContractError, Document
from larp.execution_live.balances import read_balances
from larp.execution_live.chain import DependencyUnavailable
from larp.integration.runtime import initial_projection
from larp.research.fixtures import changed, snapshot, with_quotes
from larp.risk.planner import plan
from larp.runtime.coordinator import batch_for
from larp.runtime.driver import BalanceCheck, DayRoll, RuntimeHealth, ShadowExecution
from larp.storage.postgres import IntegrityError, doc
from larp.strategy.policy import decide
from tests.runtime.test_balance_reconciliation import HASH, HEIGHT, INTERVAL, MAX_AGE, MINUTE, WALLET, chain_for, \
    ledger, observe
from tests.runtime.test_daily_anchor_window import EntryMarket
from tests.runtime.test_round_driver_service import RUN, SECOND, VERSION, ServiceHarness, pipeline
from tests.strategy.test_equal_weight import ew

JUMP_BPS = 3000
DAY = '2026-10-10'
START = int(datetime(2026, 10, 10, 14, tzinfo=timezone.utc).timestamp() * 1000)
FLATTEN = int(datetime(2026, 10, 21, 1, tzinfo=timezone.utc).timestamp() * 1000)
PRICE = 100_000_000


# ---------------------------------------------------------------------------------------------- S1, S2 (pure)
class Pure(unittest.TestCase):
    def test_s1_an_unsolicited_token_is_listed_and_never_a_surplus(self):
        from larp.risk.reconcile import compare_balances
        book = ledger()
        o = observe(chain_for(book))
        o['tokens']['XYZB'] = dict(contract='0x' + '7' * 40, decimals=18, units=5 * 10**18)
        check = compare_balances(book, o, settled_block=None)
        self.assertEqual((check['status'], check['surplus'], check['deficits']), ('MATCH', [], {}))
        self.assertEqual(check['unsolicited'], ['XYZB'])
        self.assertNotIn('XYZB', check['assets'])

    def test_s2_adjust_ledger_sets_units_and_keeps_the_cost(self):
        from larp.risk.reconcile import adjust_ledger
        book = ledger()
        before = deepcopy(book)
        after = adjust_ledger(book, [dict(asset='USDT', chain_units=179_000_003),
                                     dict(asset='BNB', chain_units=999_000),
                                     dict(asset='NVDAB', chain_units=4000, decimals=4),
                                     dict(asset='SKHYB', chain_units=7, decimals=4)])
        self.assertEqual((after['cash_units'], after['bnb_units']), (179_000_003, 999_000))
        self.assertEqual(after['positions']['NVDAB'], dict(units=4000, decimals=4, cost_basis_units=2000 * 10_000))
        self.assertEqual(after['positions']['SKHYB'], dict(units=7, decimals=4, cost_basis_units=0))
        self.assertEqual(book, before)
        for bad in (dict(asset='XYZB', chain_units=1, decimals=4), dict(asset='NVDAB', chain_units=-1, decimals=4),
                    dict(asset='NVDAB', chain_units=1, decimals=6)):
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                adjust_ledger(book, [bad])


# ---------------------------------------------------------------------------------------------- S12 planner
class ReverseSplitPlanner(unittest.TestCase):
    def buys(self, r, symbol):
        return ([i['cash_units'] + i['fee_units'] for i in r['intents'] if i['symbol'] == symbol and i['side'] == 'BUY']
                + [q['pay_units'] for q in r['quote_requests'] if q['symbol'] == symbol and q['side'] == 'BUY'])

    def test_s12_no_oversized_buy_and_no_risk_update_under_a_hold(self):
        s = with_quotes(ew(held={'NVDAB': 4000, 'GOOGLB': 4000, 'TSLAB': 4000}))
        base = plan(s, decide(s, s.policy_state)).read()
        [base_buy] = self.buys(base, 'MSFTB')
        c = s.context.read()
        markets = [dict(m, price_units=2 * m['price_units']) if m['symbol'] == 'NVDAB' else m for m in c['markets']]
        jumped = changed(s, markets=markets, price_jump_hold={'NVDAB': PRICE})
        r = plan(jumped, decide(jumped, jumped.policy_state)).read()
        self.assertLessEqual(sum(self.buys(r, 'MSFTB')), base_buy)
        self.assertTrue(self.buys(r, 'MSFTB'))
        self.assertFalse([i for i in r['intents'] + r['quote_requests'] if i['symbol'] == 'NVDAB'])
        latches = ('daily_halt', 'run_halt', 'deep_cut', 'peak_units', 'day_anchor_units')
        self.assertEqual({k: r['risk_state'][k] for k in latches},
                         {k: c['portfolio']['risk'][k] for k in latches})  # latches and peak as they were
        self.assertEqual(r['loss_stops_deferred'], ['NVDAB'])

    def test_s12_a_one_name_book_is_sized_from_the_lower_mark(self):
        # Added after the mutation run: in the three-name book the gross cap alone already bounds the buy.
        s = with_quotes(ew(held={'NVDAB': 4000}))
        base = plan(s, decide(s, s.policy_state)).read()
        [(symbol, base_buy)] = [(i['symbol'], i['cash_units'] + i['fee_units']) for i in base['intents']
                                if i['side'] == 'BUY'] or [(q['symbol'], q['pay_units']) for q in base['quote_requests']
                                                           if q['side'] == 'BUY'][:1]
        c = s.context.read()
        markets = [dict(m, price_units=2 * m['price_units']) if m['symbol'] == 'NVDAB' else m for m in c['markets']]
        jumped = changed(s, markets=markets, price_jump_hold={'NVDAB': PRICE})
        r = plan(jumped, decide(jumped, jumped.policy_state)).read()
        self.assertTrue(self.buys(r, symbol))
        self.assertLessEqual(sum(self.buys(r, symbol)), base_buy)

    def test_s11_the_flatten_waits_for_a_held_symbol_only(self):
        # Added after the mutation run: a mandatory sale of a symbol under a hold waits; other names still sell.
        s = ew(held={'NVDAB': 4000, 'GOOGLB': 4000}, profile_changes={'flatten_start': '2026-10-10T13:00:00Z',
                                                                     'new_risk_end': '2026-10-10T12:00:00Z'})
        c = s.context.read()
        markets = [dict(m, price_units=m['price_units'] // 2) if m['symbol'] == 'NVDAB' else m for m in c['markets']]
        jumped = changed(s, markets=markets, price_jump_hold={'NVDAB': PRICE})
        r = plan(jumped, decide(jumped, jumped.policy_state)).read()
        status = {q['symbol']: q['status'] for q in r['requirements']}
        self.assertEqual(status['NVDAB'], 'BLOCKED_PRICE_JUMP')
        self.assertFalse([i for i in r['intents'] + r['quote_requests'] if i['symbol'] == 'NVDAB'])
        self.assertTrue([i for i in r['intents'] + r['quote_requests'] if i['symbol'] == 'GOOGLB'])


# ---------------------------------------------------------------------------------------------- driver harness
class Marks(EntryMarket):
    """EntryMarket with a per-symbol price."""

    def __init__(self):
        super().__init__()
        self.prices = {}

    def __call__(self, now):
        return [dict(m, price_units=self.prices.get(m['symbol'], self.price)) for m in self.context(now)['markets']]


class AdoptionHarness(ServiceHarness):
    """A neutral-evidence world (no exit), shadow execution, synthetic chain and marks, rounds only on request."""

    def prepare(self, *, gas=False, cash=None, bnb=None, held=2000, raw=None, extra=None, jump=True, rpc_fail=False):
        initial = pipeline.pipeline_ledger()
        initial['risk'].update(day=DAY, daily_halt=False)
        initial['positions']['NVDAB'].update(units=held, cost_basis_units=held * 10_000)
        if cash is not None:
            initial['cash_units'] = cash
        if bnb is not None:
            initial['bnb_units'] = bnb
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        self.store_initial = Document.from_dict(initial_projection(initial))
        self.store.initialize(RUN, 'fake-wallet', 56, self.store_initial)
        self.epoch = self.store.takeover(RUN, 1, offline=True)
        current = self.store.load(RUN)
        projection = current.read()['projection']
        projection['registered_version'] = dict(build_id=VERSION, manifest_sha256='0' * 64)
        self.store.commit(batch_for(current, 'version:fixture', dict(kind='VERSION_REGISTERED',
                                    version=projection['registered_version']), projection=projection))
        self.world(['EXSEMI_Q2_8K'], now_ms=START)
        self.feed = Marks()
        self.feed.clock = self.w.clock
        from unittest.mock import patch
        from larp.research.fixtures import synthetic_profile
        changes = dict(gas_floor_bnb_units=100_000, gas_top_up_cash_units=1_000_000) if gas else {}
        with patch('tests.runtime.test_round_driver_service.synthetic_profile',
                   side_effect=lambda **kw: synthetic_profile(**kw, **changes)):
            driver = self.service_driver(market=self.feed, cadence=True)
        c = driver.coordinator
        c.context_builder.series = lambda now: self.feed.context(now)['series']
        driver.execution = ShadowExecution(c)
        driver.work.cadence = MINUTE
        self.rounds_on = False
        cadence = driver.work._cadence
        driver.work.next = lambda now_ms, epoch: cadence(now_ms) if self.rounds_on else None
        book = self.store.load(RUN).read()['projection']['portfolio']
        self.chain = chain_for(book, **(raw or {}))
        self.extra, self.stuck = extra, False

        def read(now_ms):
            if rpc_fail:
                raise DependencyUnavailable('RPC unavailable')
            if not self.stuck:
                self.chain.height += 1  # finalized blocks advance between reads (IDEA-055 R1)
            o = read_balances(self.chain, wallet=WALLET, observed_at='x')
            if self.extra:
                o['tokens'].update(self.extra)
            return o
        check = BalanceCheck(c, read, interval_ms=INTERVAL, max_age_ms=MAX_AGE)
        driver.balance_check = check
        c.context_builder.health = RuntimeHealth(self.store, RUN, self.epoch, balances=check)
        if jump:
            c.context_builder.price_jump = dict(bps=JUMP_BPS, hold_ms=MAX_AGE)
        return driver

    # -- helpers
    def projection(self):
        return self.store.load(RUN).read()['projection']

    def book(self):
        return self.projection()['portfolio']

    def health(self, driver):
        return driver.coordinator.context_builder.health(self.store.load(RUN).read())

    def events(self, kind):
        return [d.read()['event'] for d in self.store.journal(RUN) if d.read()['event']['kind'] == kind]

    def incidents(self, kind):
        return [e['incident'] for e in self.events('INCIDENT') if e['incident']['type'] == kind]

    def audits(self):
        with self.store.transaction() as db:
            return db.execute('SELECT count(*) FROM audit_events WHERE run_id=%s', (RUN,)).fetchone()[0]

    def tick(self, driver, ms=SECOND):
        self.w.clock.now += ms
        return driver.once(self.w.clock())

    def round(self, driver, at=None):
        """One cadence round at the next minute (or at `at`); returns (summary, plan record)."""
        self.w.clock.now = at if at is not None else (self.w.clock.now // MINUTE + 1) * MINUTE
        self.rounds_on = True
        try:
            summary = driver.once(self.w.clock())
        finally:
            self.rounds_on = False
        self.assertIsNotNone(summary['round_id'], summary)
        return summary, self.store.event(RUN, 'plan:' + summary['round_id'])['record']


class Adoption(AdoptionHarness):
    def test_s3_a_single_bad_read_is_never_adopted(self):
        driver = self.prepare(raw=dict(NVDAB=2010))
        self.assertEqual(self.tick(driver)['balance_check'], 'SURPLUS_ONLY')
        self.chain.tokens['NVDAB'] = 2000  # the confirming read disagrees: the first was wrong
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'MATCH')
        self.assertEqual((self.events('BALANCE_ADJUSTED'), self.book()['positions']['NVDAB']['units']), ([], 2000))
        self.chain.tokens['NVDAB'] = 2010
        self.assertEqual(self.tick(driver, INTERVAL)['balance_check'], 'SURPLUS_ONLY')
        self.chain.tokens['NVDAB'] = 2020  # two mismatching reads that disagree: nothing adopted
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'SURPLUS_ONLY')
        self.assertEqual(self.events('BALANCE_ADJUSTED'), [])
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')  # the newer read, read again
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 2020)

    def test_s4_the_confirming_check_runs_a_minute_later(self):
        driver = self.prepare(raw=dict(NVDAB=2010))
        self.tick(driver)
        self.assertNotIn('balance_check', self.tick(driver, MINUTE - SECOND))
        self.assertEqual(self.tick(driver, SECOND)['balance_check'], 'ADJUSTED')

    def test_s5_resource_activity_between_the_checks_prevents_adoption(self):
        driver = self.prepare(raw=dict(NVDAB=2010))
        self.assertEqual(self.tick(driver)['balance_check'], 'SURPLUS_ONLY')
        self.round(driver)
        # PR115-C04: a hold-only round is wallet-neutral. Actual resource activity, even if completed
        # between reads, still invalidates the candidate and requires a new quiet pair of reads.
        for suffix, units in [('reserve', 1), ('release', -1)]:
            current = self.store.load(RUN)
            self.store.commit(batch_for(current, 'fixture:s5:' + suffix,
                dict(kind='INCIDENT', incident=dict(type='FIXTURE_RESOURCE')),
                reservation_deltas=[dict(intent_id='s5', asset='USDT', units=units)]))
        self.assertNotEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')
        self.assertEqual(self.events('BALANCE_ADJUSTED'), [])
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 2010)

    def test_s6_a_dividend_multiplier_is_adopted_with_its_incident(self):
        driver = self.prepare(raw=dict(NVDAB=2010))
        cost = self.book()['positions']['NVDAB']['cost_basis_units']
        audits = self.audits()
        self.assertEqual(self.tick(driver)['balance_check'], 'SURPLUS_ONLY')
        self.assertTrue(self.health(driver)['new_spending_ok'])
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')
        self.assertTrue(self.health(driver)['new_spending_ok'])
        projection = self.projection()
        self.assertEqual(projection['portfolio']['positions']['NVDAB'], dict(units=2010, decimals=4,
                                                                             cost_basis_units=cost))
        self.assertEqual(projection['balances']['NVDAB'], 2010)
        [event] = self.events('BALANCE_ADJUSTED')
        [adjustment] = event['adjustments']
        [incident] = self.incidents('BALANCE_ADJUSTED')
        for row in (adjustment, incident):
            self.assertEqual((row['asset'], row['ledger_before'], row['chain_units'], row['delta'], row['reason']),
                             ('NVDAB', 2000, 2010, 10, 'SURPLUS'))
            self.assertEqual(row['confirm_block'], row['first_block'] + 1)  # R1: a strictly newer block
            self.assertEqual(len(row['first_observation_sha256']), 64)
            self.assertEqual(len(row['confirm_observation_sha256']), 64)
        self.assertEqual(self.audits(), audits)  # not a round: no ai-seeds log
        self.assertFalse(projection.get('round_records'))
        self.assertEqual(self.tick(driver, INTERVAL)['balance_check'], 'MATCH')

    def test_s7_usdt_dust_is_adopted(self):
        driver = self.prepare()
        cash = self.book()['cash_units']
        self.chain.tokens['USDT'] = (cash + 3) * 10**12 + 5
        self.tick(driver)
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')
        self.assertEqual(self.book()['cash_units'], cash + 3)
        self.assertEqual(self.incidents('BALANCE_ADJUSTED')[0]['reason'], 'SURPLUS')

    def test_s8_a_ledger_restored_from_an_old_backup_is_resynced_and_trading_resumes(self):
        driver = self.prepare(raw=dict(NVDAB=1500))
        self.assertEqual(self.tick(driver)['balance_check'], 'DEFICIT')
        self.assertEqual(self.incidents('BALANCE_DEFICIT')[0]['deficits'], {'NVDAB': 500})
        self.assertFalse(self.health(driver)['new_spending_ok'])  # the D1 window
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 1500)
        self.assertEqual(self.incidents('BALANCE_ADJUSTED')[0]['reason'], 'DEFICIT')
        self.assertEqual(self.projection()['balance_check'].get('deficits'), {})
        self.assertTrue(self.health(driver)['new_spending_ok'])
        _, record = self.round(driver)
        context = record['policy_input']['context']
        self.assertEqual(context['portfolio']['positions']['NVDAB']['units'], 1500)
        self.assertTrue(context['health']['new_spending_ok'])

    def test_s9_an_adopted_bnb_deficit_allows_gas_top_ups_again(self):
        driver = self.prepare(gas=True, bnb=60_000, raw=dict(BNB=50_000 * 10**12))
        self.assertEqual(self.tick(driver)['balance_check'], 'DEFICIT')
        _, record = self.round(driver)
        self.assertIn('GAS_TOP_UP_SPENDING_BLOCKED', {r['reason'] for r in record['plan']['rejections']})
        # A blocked, hold-only round no longer starves confirmation (PR115-C04).
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')
        self.assertEqual(self.book()['bnb_units'], 50_000)
        _, record = self.round(driver)
        self.assertNotIn('GAS_TOP_UP_SPENDING_BLOCKED', {r['reason'] for r in record['plan']['rejections']})
        self.assertTrue([q for q in record['plan']['quote_requests'] if q['symbol'] == 'BNB'])

    def test_s10_a_large_adopted_deficit_trips_the_run_loss_stop(self):
        driver = self.prepare()
        cash = self.book()['cash_units']
        self.chain.tokens['USDT'] = (cash - 20_000_000) * 10**12  # 10 % of equity drained
        self.tick(driver)
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')
        _, record = self.round(driver)
        self.assertTrue(record['plan']['risk_state']['run_halt'])

    def test_s1_an_unsolicited_token_is_never_adopted(self):
        driver = self.prepare(extra=dict(XYZB=dict(contract='0x' + '7' * 40, decimals=18, units=10**18)))
        positions = deepcopy(self.book()['positions'])
        self.assertEqual(self.tick(driver)['balance_check'], 'MATCH')
        self.tick(driver, MINUTE)
        self.tick(driver, INTERVAL)
        self.assertEqual((self.events('BALANCE_ADJUSTED'), self.book()['positions']), ([], positions))
        self.assertEqual(self.events('BALANCE_CHECKED')[0]['check']['unsolicited'], ['XYZB'])


class PriceJump(AdoptionHarness):
    def split(self, driver, *, price, units):
        """A round at the old marks, then one at `price` while the chain holds `units` NVDAB."""
        self.assertEqual(self.tick(driver)['balance_check'], 'MATCH')
        self.round(driver)
        self.feed.prices['NVDAB'] = price
        self.chain.tokens['NVDAB'] = units
        return self.round(driver)

    def test_s11_a_forward_split_is_held_adopted_and_flattened_in_full(self):
        driver = self.prepare()
        peak = self.book()['risk']['peak_units']
        _, record = self.split(driver, price=PRICE // 2, units=4000)
        hold = self.projection()['price_jump']['NVDAB']
        self.assertEqual((hold['reference_price_units'], hold['price_units']), (PRICE, PRICE // 2))
        self.assertEqual(record['policy_input']['context']['price_jump_hold'], {'NVDAB': PRICE})
        plan_ = record['plan']
        self.assertFalse([i for i in plan_['intents'] + plan_['quote_requests'] if i['symbol'] == 'NVDAB'])
        risk = plan_['risk_state']
        self.assertEqual((risk['daily_halt'], risk['run_halt'], risk['deep_cut'], risk['peak_units']),
                         (False, False, False, peak))
        self.assertEqual(plan_['loss_stops_deferred'], ['NVDAB'])
        self.assertEqual(self.tick(driver)['balance_check'], 'SURPLUS_ONLY')  # immediate, not in 10 minutes
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 4000)
        self.assertEqual(self.projection()['price_jump'], {})
        _, record = self.round(driver)
        risk = record['plan']['risk_state']
        self.assertEqual((risk['daily_halt'], risk['run_halt']), (False, False))
        self.assertEqual(record['policy_input']['context']['price_jump_hold'], {})
        _, record = self.round(driver, at=FLATTEN)
        [requirement] = [r for r in record['plan']['requirements'] if r['symbol'] == 'NVDAB']
        self.assertIn('TERMINAL_FLATTEN', requirement['reasons'])
        self.assertEqual((requirement['held_units'], requirement['remaining_sell_units']), (4000, 4000))
        sells = ([i['token_units'] for i in record['plan']['intents'] if i['symbol'] == 'NVDAB']
                 + [q['pay_units'] for q in record['plan']['quote_requests'] if q['symbol'] == 'NVDAB'])
        self.assertEqual(sells, [4000])

    def test_s12_a_reverse_split_never_raises_the_peak(self):
        driver = self.prepare(held=2000)
        peak = self.book()['risk']['peak_units']
        _, record = self.split(driver, price=PRICE * 2, units=1000)
        self.assertEqual(record['plan']['risk_state']['peak_units'], peak)
        self.tick(driver)
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')
        self.assertEqual(self.book()['positions']['NVDAB']['units'], 1000)
        _, record = self.round(driver)
        self.assertFalse(record['plan']['risk_state']['run_halt'])
        self.assertFalse(record['plan']['risk_state']['daily_halt'])

    def test_s13_without_a_check_the_hold_expires_and_the_stops_evaluate(self):
        driver = self.prepare(rpc_fail=True)
        self.assertEqual(self.tick(driver)['balance_check'], 'SKIPPED:RPC_UNAVAILABLE')
        self.round(driver)
        self.feed.prices['NVDAB'] = PRICE // 2
        _, record = self.round(driver)
        self.assertFalse(record['plan']['risk_state']['daily_halt'])
        until = self.projection()['price_jump']['NVDAB']['until_ms']
        _, record = self.round(driver, at=(until // MINUTE + 1) * MINUTE)
        self.assertEqual(record['policy_input']['context']['price_jump_hold'], {})
        self.assertTrue(record['plan']['risk_state']['daily_halt'])

    def test_s14_the_day_roll_waits_while_a_hold_is_active(self):
        driver = self.prepare()
        c = driver.coordinator
        roll = DayRoll(c, window_ms=60 * MINUTE)
        midnight = int(datetime(2026, 10, 11, tzinfo=timezone.utc).timestamp() * 1000)
        current = self.store.load(RUN)
        projection = current.read()['projection']
        projection['price_jump'] = {'NVDAB': dict(reference_price_units=PRICE, price_units=PRICE // 2,
                                                  jump_ms=midnight - MINUTE, until_ms=midnight + MAX_AGE)}
        self.store.commit(batch_for(current, 'fixture:hold', dict(kind='INCIDENT', incident=dict(type='FIXTURE')),
                                    projection=projection))
        self.w.clock.now = midnight + MINUTE
        observations = self.feed(self.w.clock())
        self.assertEqual(roll(self.w.clock(), observations), 'PRICE_JUMP_HOLD')
        self.assertEqual(roll(midnight + MAX_AGE + MINUTE, self.feed(midnight + MAX_AGE + MINUTE)), 'ROLLED')

    def test_s15_replay_reproduces_adjustments_and_refuses_a_tampered_one(self):
        driver = self.prepare()
        self.split(driver, price=PRICE // 2, units=4000)
        self.tick(driver)
        self.tick(driver, MINUTE)
        self.round(driver)
        self.assertTrue(self.events('BALANCE_ADJUSTED'))
        journal = list(self.store.journal(RUN))
        head, expected = self.replay_head(driver)
        self.assertEqual(head, expected)
        # Cut the journal at the tampered event: later batches carry full projections that would hide it.
        index = next(i for i, d in enumerate(journal) if d.read()['event']['kind'] == 'BALANCE_ADJUSTED')
        b = json.loads(json.dumps(journal[index].read()))
        b['projection']['portfolio']['positions']['NVDAB']['units'] += 1
        b['projection']['balances']['NVDAB'] += 1
        tampered = journal[:index] + [doc(b)]
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        self.replay(driver, journal[:index + 1])  # the untampered prefix replays
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        with self.assertRaises(IntegrityError):
            self.replay(driver, tampered)

    def replay(self, driver, journal):
        from larp.integration.replay import replay_live
        from larp.integration.runtime import RuntimePlanner, StrategyPolicy, initial_policy_state
        from larp.integration.settlement import ExecutionBridge, settle
        initial = self.store_initial
        return replay_live(journal, initial, self.store, builder=driver.coordinator.context_builder, run_id=RUN,
                           wallet_id='fake-wallet', chain_id=56, version_id=VERSION, profile_hash=self.h,
                           address='0x' + '1' * 40, policy=StrategyPolicy(),
                           planner=RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                           execution=ExecutionBridge(), reducer=settle,
                           initial_policy_state=initial_policy_state(RUN, self.profile), require_version=True)

    def replay_head(self, driver):
        journal, expected = list(self.store.journal(RUN)), self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        return self.replay(driver, journal), expected


# ---------------------------------------------------------------------------------------------- PR 4 review fixes
class ReviewFixes(AdoptionHarness):
    """IDEA-055 R1-R3 (section B review of PR #115, wtvlol's ALLPR-R1)."""

    def hold(self, jump_ms):
        current = self.store.load(RUN)
        projection = current.read()['projection']
        projection['price_jump'] = {'NVDAB': dict(reference_price_units=PRICE, price_units=PRICE // 2,
                                                  jump_ms=jump_ms, until_ms=jump_ms + MAX_AGE)}
        self.store.commit(batch_for(current, f'fixture:hold:{jump_ms}', dict(kind='INCIDENT',
                                    incident=dict(type='FIXTURE')), projection=projection))

    def test_r1_a_hold_before_the_first_read_cannot_shorten_the_confirmation(self):
        driver = self.prepare(raw=dict(NVDAB=2010))
        check, t = driver.balance_check, self.w.clock() + SECOND
        self.hold(t)
        self.assertEqual(check(t), 'SURPLUS_ONLY')
        first_block = self.chain.height
        self.assertTrue(check.due(t + SECOND, self.projection()))  # the jump trigger still fires
        self.assertEqual(check(t + SECOND), 'SURPLUS_ONLY')  # too early: no adoption
        self.assertEqual(self.events('BALANCE_ADJUSTED'), [])
        self.assertEqual(check(t + MINUTE), 'ADJUSTED')  # retry_ms after the *first* read
        [adjustment] = self.events('BALANCE_ADJUSTED')[0]['adjustments']
        self.assertEqual(adjustment['first_block'], first_block)  # the early check did not replace the candidate

    def test_r1_a_first_read_in_the_same_millisecond_as_the_hold(self):
        driver = self.prepare(raw=dict(NVDAB=2010))
        check, t = driver.balance_check, self.w.clock() + SECOND
        self.assertEqual(check(t), 'SURPLUS_ONLY')
        self.hold(t)
        self.assertTrue(check.due(t + SECOND, self.projection()))
        self.assertNotEqual(check(t + SECOND), 'ADJUSTED')
        self.assertNotEqual(check(t + SECOND + SECOND), 'ADJUSTED')
        self.assertEqual(self.events('BALANCE_ADJUSTED'), [])
        self.assertEqual(check(t + SECOND + MINUTE), 'ADJUSTED')

    def test_r1_a_stuck_node_cannot_confirm_its_own_read(self):
        driver = self.prepare(raw=dict(NVDAB=2010))
        self.assertEqual(self.tick(driver)['balance_check'], 'SURPLUS_ONLY')
        self.stuck = True  # the same finalized block a minute later
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'SURPLUS_ONLY')
        self.assertEqual(self.events('BALANCE_ADJUSTED'), [])
        self.stuck = False
        self.assertEqual(self.tick(driver, MINUTE)['balance_check'], 'ADJUSTED')

    def test_r2_a_hold_across_the_end_of_the_window_defers_the_roll(self):
        driver = self.prepare()
        roll = DayRoll(driver.coordinator, window_ms=5 * MINUTE)
        midnight = int(datetime(2026, 10, 11, tzinfo=timezone.utc).timestamp() * 1000)
        self.hold(midnight - MINUTE)
        at = lambda ms: roll(midnight + ms, self.feed(midnight + ms))
        self.assertEqual(at(MINUTE), 'PRICE_JUMP_HOLD')
        self.assertEqual(at(10 * MINUTE), 'PRICE_JUMP_HOLD')  # past the window, still held
        fresh = DayRoll(driver.coordinator, window_ms=5 * MINUTE)  # reconstruct from the same persisted run
        self.assertEqual(fresh(midnight + 10 * MINUTE, self.feed(midnight + 10 * MINUTE)), 'PRICE_JUMP_HOLD')
        current = self.store.load(RUN)
        projection = current.read()['projection']
        projection['price_jump'] = {}  # a balance check cleared the hold
        self.store.commit(batch_for(current, 'fixture:cleared', dict(kind='INCIDENT', incident=dict(type='FIXTURE')),
                                    projection=projection))
        self.assertEqual(fresh(midnight + 12 * MINUTE, self.feed(midnight + 12 * MINUTE)), 'ROLLED')
        self.assertEqual(self.events('DAY_ROLLED')[0]['day'], '2026-10-11')

    def test_r3_a_match_just_after_the_jump_keeps_the_hold_a_later_one_clears_it(self):
        driver = self.prepare()
        self.assertEqual(self.tick(driver)['balance_check'], 'MATCH')
        self.round(driver)
        self.feed.prices['NVDAB'] = PRICE // 2  # the mark halves; the chain is unchanged (yet)
        _, record = self.round(driver)
        self.assertEqual(record['plan']['loss_stops_deferred'], ['NVDAB'])
        self.assertEqual(self.tick(driver)['balance_check'], 'MATCH')  # the immediate check
        self.assertIn('NVDAB', self.projection()['price_jump'])  # a block read seconds after the jump: kept
        self.assertNotIn('balance_check', self.tick(driver, MINUTE - 3 * SECOND))
        self.assertEqual(self.tick(driver, 3 * SECOND)['balance_check'], 'MATCH')  # retry_ms later, not 10 min
        self.assertEqual(self.projection()['price_jump'], {})
        _, record = self.round(driver)
        self.assertTrue(record['plan']['risk_state']['daily_halt'])  # a genuine drop: the stops evaluate


class SecondReview(AdoptionHarness):
    hold = ReviewFixes.hold
    replay = PriceJump.replay
    replay_head = PriceJump.replay_head

    def test_rr2_r1_an_early_contradiction_requires_a_new_confirming_pair(self):
        for middle in (2000, 2020):
            with self.subTest(intervening_units=middle):
                driver = self.prepare(raw=dict(NVDAB=2010))
                check, t = driver.balance_check, self.w.clock()
                self.assertEqual(check(t), 'SURPLUS_ONLY')
                self.chain.tokens['NVDAB'] = middle
                self.w.clock.now = t + SECOND
                self.assertNotEqual(check(self.w.clock()), 'ADJUSTED')
                self.chain.tokens['NVDAB'] = 2010
                self.w.clock.now = t + MINUTE
                self.assertEqual(check(self.w.clock()), 'SURPLUS_ONLY')
                self.assertEqual(self.events('BALANCE_ADJUSTED'), [])
                self.w.clock.now = t + 2 * MINUTE
                self.assertEqual(check(self.w.clock()), 'ADJUSTED')

    def test_rr2_r2_restart_after_clear_still_rolls_and_replays_the_deferred_day(self):
        driver = self.prepare()
        midnight = int(datetime(2026, 10, 11, tzinfo=timezone.utc).timestamp() * 1000)
        self.hold(midnight - MINUTE)
        roll = DayRoll(driver.coordinator, window_ms=5 * MINUTE)
        self.assertEqual(roll(midnight + MINUTE, self.feed(midnight + MINUTE)), 'PRICE_JUMP_HOLD')
        self.assertEqual(self.projection()['day_roll_deferred_ms'], midnight)
        current = self.store.load(RUN)
        projection = current.read()['projection']
        projection['price_jump'] = {}
        self.store.commit(batch_for(current, 'rr2:hold-cleared', dict(kind='INCIDENT', incident=dict(type='FIXTURE')),
                                    projection=projection))
        # The process dies after the balance check clears the hold, before the roll executes.
        restarted = DayRoll(driver.coordinator, window_ms=5 * MINUTE)
        self.assertEqual(restarted(midnight + 12 * MINUTE, self.feed(midnight + 12 * MINUTE)), 'ROLLED')
        self.assertNotIn('day_roll_deferred_ms', self.projection())
        actual, expected = self.replay_head(driver)
        self.assertEqual(actual, expected)

    def test_rr2_r2_a_day_never_deferred_in_its_window_stays_outside(self):
        driver = self.prepare()
        midnight = int(datetime(2026, 10, 11, tzinfo=timezone.utc).timestamp() * 1000)
        roll = DayRoll(driver.coordinator, window_ms=5 * MINUTE)
        self.assertEqual(roll(midnight + 10 * MINUTE, self.feed(midnight + 10 * MINUTE)), 'OUTSIDE_WINDOW')
        self.assertEqual(self.events('DAY_ROLL_DEFERRED'), [])


# ---------------------------------------------------------------------------------------------- S16 configuration
class Settings(unittest.TestCase):
    BLOCK = dict(balance_rpc_url='https://rpc.invalid/', balance_rpc_source_id='synthetic-rpc',
                 balance_check_interval_ms=INTERVAL, balance_check_max_age_ms=MAX_AGE, price_jump_check_bps=JUMP_BPS)

    def test_s16_dev_and_live_need_the_price_jump_setting(self):
        from larp.runtime.service import balance_settings
        for mode in ('dev', 'live'):
            with self.subTest(mode=mode, missing=True), self.assertRaises(ContractError):
                balance_settings({k: v for k, v in self.BLOCK.items() if k != 'price_jump_check_bps'}, mode)
            for bad in (0, 10_001, '3000', True):
                with self.subTest(mode=mode, bad=bad), self.assertRaises(ContractError):
                    balance_settings(dict(self.BLOCK, price_jump_check_bps=bad), mode)
            self.assertEqual(balance_settings(self.BLOCK, mode)['price_jump_bps'], JUMP_BPS)

    def test_s16_the_example_sets_3000(self):
        from pathlib import Path
        example = json.loads((Path(__file__).resolve().parents[2] / 'config/runtime/runtime.example.json').read_text())
        self.assertEqual(example['driver']['price_jump_check_bps'], 3000)

    def test_s16_build_driver_gives_the_builder_the_guard(self):
        from larp.runtime.service import build_driver
        from tests.runtime import test_driver as driver_tests
        case = driver_tests.Composition('test_d7_valid_configuration_builds_real_ports_that_pass_the_live_start_check')
        case.setUp()
        self.addCleanup(case.doCleanups)
        driver = build_driver(case.config(**self.BLOCK), driver_tests.Store(), case.secrets)
        self.assertEqual(driver.coordinator.context_builder.price_jump, dict(bps=JUMP_BPS, hold_ms=MAX_AGE))
        plain = build_driver(case.config(), driver_tests.Store(), case.secrets)
        self.assertIsNone(plain.coordinator.context_builder.price_jump)


if __name__ == '__main__':
    unittest.main()

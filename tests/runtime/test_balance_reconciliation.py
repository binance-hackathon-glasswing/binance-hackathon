"""IDEA-055 B1-B9 (#36): chain-balance reconciliation that detects a mismatch and stops new risk.

B1, B2 and B7 are pure. B3-B6, B8 and B9 run the real driver, coordinator, planner and settlement on disposable
PostgreSQL with a synthetic chain. No credentials, network, signing or upload.
"""

from contextlib import contextmanager
from copy import deepcopy
from fractions import Fraction
import json
import unittest

from larp.contracts import ContractError, Document
from larp.execution import USDT
from larp.execution_live.chain import Blocked, DependencyUnavailable, Rpc
from larp.marketdata.port import TOKENS
from tests.runtime.test_round_driver_service import RUN, SECOND, Execution, HAS_ETH, ServiceHarness

WALLET = '0x' + '4' * 40
HASH = '0x' + 'a' * 64
HEIGHT = 1_000
MINUTE = 60 * SECOND
INTERVAL, MAX_AGE = 10 * MINUTE, 30 * MINUTE


def word(n):
    return '0x' + format(n, '064x')


class Chain:
    """A synthetic BSC node: one finalized block, native and ERC-20 balances, nonces. Records every call."""

    def __init__(self, *, native, tokens, decimals, latest=7, pending=7, height=HEIGHT):
        self.native, self.tokens, self.decimals = native, dict(tokens), dict(decimals)
        self.latest, self.pending, self.height = latest, pending, height
        self.recheck_hash, self.chain_id, self.calls, self.fail = HASH, 56, [], None

    def call(self, method, params):
        self.calls.append((method, params))
        if self.fail is not None:
            raise self.fail
        if method == 'eth_chainId':
            return hex(self.chain_id)
        if method == 'eth_getBlockByNumber':
            tag = params[0]
            return dict(number=hex(self.height), hash=HASH if tag == 'finalized' else self.recheck_hash)
        if method == 'eth_getBalance':
            assert params == [WALLET, hex(self.height)], params
            return hex(self.native)
        if method == 'eth_call':
            target, tag = params
            assert tag == hex(self.height), tag
            asset = next(a for a, c in contracts().items() if c == target['to'])
            if target['data'] == '0x313ce567':
                return word(self.decimals[asset])
            assert target['data'] == '0x70a08231' + '0' * 24 + WALLET[2:], target['data']
            return word(self.tokens.get(asset, 0))
        if method == 'eth_getTransactionCount':
            return hex(self.latest if params[1] == 'latest' else self.pending)
        raise AssertionError(method)


def contracts():
    return {'USDT': USDT, **TOKENS}


def ledger(**units):
    held = dict(NVDAB=2000, GOOGLB=0, TSLAB=0, MSFTB=0)
    held.update({k: v for k, v in units.items() if k in held})
    return dict(cash_units=units.get('cash', 179_000_000), bnb_units=units.get('bnb', 1_000_000), bnb_decimals=6,
                positions={s: dict(units=u, decimals=4, cost_basis_units=u * 10_000) for s, u in held.items()})


def chain_for(book, **raw):
    """A chain that holds exactly what `book` says, unless `raw` overrides an asset's raw units."""
    tokens = {'USDT': book['cash_units'] * 10**12, **{s: p['units'] for s, p in book['positions'].items()}}
    tokens.update({k: v for k, v in raw.items() if k != 'BNB'})
    decimals = {'USDT': 18, **{s: 4 for s in TOKENS}}
    return Chain(native=raw.get('BNB', book['bnb_units'] * 10**12), tokens=tokens, decimals=decimals)


def observe(chain):
    from larp.execution_live.balances import read_balances
    return read_balances(chain, wallet=WALLET, observed_at='2026-10-20T14:00:00+00:00')


# ---------------------------------------------------------------------------------------------- B1 observation
class Observation(unittest.TestCase):
    def test_b1_every_read_uses_one_finalized_block(self):
        book = ledger()
        chain = chain_for(book)
        o = observe(chain)
        self.assertEqual((o['schema'], o['chain_id'], o['wallet']), ('ChainBalances.v1', 56, WALLET))
        self.assertEqual((o['block_number'], o['block_hash']), (HEIGHT, HASH))
        self.assertEqual(o['native_wei'], book['bnb_units'] * 10**12)
        self.assertEqual(set(o['tokens']), set(contracts()))
        self.assertEqual(o['tokens']['USDT'], dict(contract=USDT, decimals=18, units=book['cash_units'] * 10**12))
        self.assertEqual(o['tokens']['NVDAB']['units'], 2000)
        self.assertEqual((o['latest_nonce'], o['pending_nonce']), (7, 7))
        balance_reads = [p for m, p in chain.calls if m in ('eth_getBalance', 'eth_call')]
        self.assertEqual(len(balance_reads), 1 + 2 * len(contracts()))
        self.assertTrue(all(p[-1] == hex(HEIGHT) for p in balance_reads))
        rechecks = [p for m, p in chain.calls if m == 'eth_getBlockByNumber' and p[0] == hex(HEIGHT)]
        last_read = max(i for i, (m, _) in enumerate(chain.calls) if m in ('eth_getBalance', 'eth_call'))
        self.assertTrue(rechecks and chain.calls.index(('eth_getBlockByNumber', rechecks[-1])) > last_read)

    def test_b1_a_changed_block_hash_or_chain_refuses(self):
        chain = chain_for(ledger())
        chain.recheck_hash = '0x' + 'b' * 64
        with self.assertRaises(Blocked):
            observe(chain)
        chain = chain_for(ledger())
        chain.chain_id = 1
        with self.assertRaises(Blocked):
            observe(chain)

    def test_decimals_are_reused_once_two_reads_agree(self):
        # #96: decimals() is a contract constant. It is asked for until two reads agree, then never again.
        from larp.execution_live.balances import DecimalsCache, read_balances
        chain, cache = chain_for(ledger()), DecimalsCache()

        def asked():
            found = [p for m, p in chain.calls if m == 'eth_call' and p[0]['data'] == '0x313ce567']
            chain.calls.clear()
            return len(found)
        first = read_balances(chain, wallet=WALLET, observed_at='a', decimals=cache)
        self.assertEqual(asked(), len(contracts()))
        read_balances(chain, wallet=WALLET, observed_at='a', decimals=cache)
        self.assertEqual(asked(), len(contracts()))
        self.assertEqual(cache.confirmed, {'USDT': 18, **{s: 4 for s in TOKENS}})
        third = read_balances(chain, wallet=WALLET, observed_at='a', decimals=cache)
        self.assertEqual(len(chain.calls), 6 + len(contracts()))  # 12 RPC calls once confirmed
        self.assertEqual(asked(), 0)
        self.assertEqual(third, first)

    def test_one_bad_decimals_answer_is_never_kept(self):
        from larp.execution_live.balances import DecimalsCache, read_balances
        chain, cache = chain_for(ledger()), DecimalsCache()
        chain.decimals['USDT'] = 9  # a plausible but wrong answer, once
        read_balances(chain, wallet=WALLET, observed_at='a', decimals=cache)
        chain.decimals['USDT'] = 18
        read_balances(chain, wallet=WALLET, observed_at='a', decimals=cache)
        self.assertNotIn('USDT', cache.confirmed)
        o = read_balances(chain, wallet=WALLET, observed_at='a', decimals=cache)
        self.assertEqual((cache.confirmed['USDT'], o['tokens']['USDT']['decimals']), (18, 18))
        # An implausible value is refused and never cached.
        chain, cache = chain_for(ledger()), DecimalsCache()
        chain.decimals['USDT'] = 78
        with self.assertRaises(Blocked):
            read_balances(chain, wallet=WALLET, observed_at='a', decimals=cache)
        self.assertEqual((cache.confirmed, cache.last), ({}, {}))


class Memory:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


class Opener:
    def open(self, request, timeout):
        body = json.loads(request.data)

        @contextmanager
        def response():
            class R:
                def read(self, n):
                    return json.dumps(dict(jsonrpc='2.0', id=body['id'], result=word(18))).encode()
            yield R()
        return response()


class RpcAllowlist(unittest.TestCase):
    def rpc(self):
        return Rpc('https://rpc.invalid/', artifacts=Memory(), source_id='synthetic', opener=Opener())

    def test_b1_eth_call_is_limited_to_decimals_and_balance_of_on_pinned_contracts(self):
        rpc = self.rpc()
        balance_of = '0x70a08231' + '0' * 24 + WALLET[2:]
        self.assertEqual(rpc.call('eth_call', [dict(to=TOKENS['NVDAB'], data='0x313ce567'), hex(HEIGHT)]), word(18))
        self.assertEqual(rpc.call('eth_call', [dict(to=USDT, data=balance_of), hex(HEIGHT)]), word(18))
        refused = {
            'transfer selector': [dict(to=USDT, data='0xa9059cbb' + '0' * 128), hex(HEIGHT)],
            'other contract': [dict(to='0x' + '9' * 40, data='0x313ce567'), hex(HEIGHT)],
            'latest tag': [dict(to=USDT, data='0x313ce567'), 'latest'],
            'extra field': [dict(to=USDT, data='0x313ce567', value='0x1'), hex(HEIGHT)],
            'malformed address': [dict(to=USDT, data='0x70a08231' + '1' * 64), hex(HEIGHT)],
            'trailing bytes': [dict(to=USDT, data=balance_of + '00'), hex(HEIGHT)],
            'no block': [dict(to=USDT, data='0x313ce567')],
        }
        for name, params in refused.items():
            with self.subTest(name), self.assertRaises(Blocked):
                rpc.call('eth_call', params)


# ---------------------------------------------------------------------------------------------- B2 comparison
class Comparison(unittest.TestCase):
    def compare(self, book, chain, settled_block=None):
        from larp.risk.reconcile import compare_balances
        return compare_balances(book, observe(chain), settled_block=settled_block)

    def test_b2_classes(self):
        book = ledger()
        match = self.compare(book, chain_for(book))
        self.assertEqual((match['schema'], match['status'], match['deficits']), ('BalanceCheck.v1', 'MATCH', {}))
        self.assertEqual(match['block_number'], HEIGHT)
        dust = self.compare(book, chain_for(book, USDT=book['cash_units'] * 10**12 + 10**12 - 1))
        self.assertEqual((dust['status'], dust['deficits']), ('MATCH', {}))  # below one ledger unit: floored away
        surplus = self.compare(book, chain_for(book, USDT=book['cash_units'] * 10**12 + 3 * 10**12, SKHYB=5))
        self.assertEqual((surplus['status'], surplus['surplus']), ('SURPLUS_ONLY', ['SKHYB', 'USDT']))
        self.assertEqual(surplus['assets']['USDT']['difference'], 3)
        deficit = self.compare(book, chain_for(book, NVDAB=1500, BNB=(book['bnb_units'] - 40) * 10**12))
        self.assertEqual((deficit['status'], deficit['deficits']), ('DEFICIT', {'BNB': 40, 'NVDAB': 500}))
        self.assertEqual(deficit['assets']['NVDAB'], dict(ledger_units=2000, chain_units=1500, difference=-500,
                                                          **{'class': 'DEFICIT'}))

    def test_b2_skips_and_refusals(self):
        book = ledger()
        pending = chain_for(book)
        pending.pending = 8
        self.assertEqual((self.compare(book, pending)['status'], self.compare(book, pending)['reason']),
                         ('SKIPPED', 'PENDING_NONCE'))
        behind = self.compare(book, chain_for(book), settled_block=HEIGHT + 1)
        self.assertEqual((behind['status'], behind['reason']), ('SKIPPED', 'BLOCK_BEHIND_LEDGER'))
        self.assertEqual(self.compare(book, chain_for(book), settled_block=HEIGHT)['status'], 'MATCH')
        unknown = deepcopy(book)
        unknown['positions']['XYZB'] = dict(units=1, decimals=4, cost_basis_units=0)
        with self.assertRaises(ContractError):
            self.compare(unknown, chain_for(book))
        finer = deepcopy(book)
        finer['positions']['NVDAB']['decimals'] = 6  # the ledger cannot be finer than the chain
        with self.assertRaises(ContractError):
            self.compare(finer, chain_for(book))

    def test_b2_spendable_view_subtracts_deficits_and_never_goes_negative(self):
        from larp.risk.reconcile import spendable_view
        book = ledger()
        before = deepcopy(book)
        view = spendable_view(book, {'NVDAB': 500, 'USDT': 10**12, 'BNB': 40})
        self.assertEqual((view['positions']['NVDAB']['units'], view['cash_units'], view['bnb_units']),
                         (1500, 0, book['bnb_units'] - 40))
        self.assertEqual(book, before)
        self.assertEqual(spendable_view(book, {}), book)
        # After the capped sale settles, the ledger keeps only the phantom units: the view of them is zero.
        after_sale = deepcopy(book)
        after_sale['positions']['NVDAB']['units'] = 500
        self.assertEqual(spendable_view(after_sale, {'NVDAB': 500})['positions']['NVDAB']['units'], 0)


# ---------------------------------------------------------------------------------------------- B7 BNB bound
class BnbBound(unittest.TestCase):
    def test_b7_bnb_held_under_the_live_gas_policy_is_immaterial(self):
        from larp.strategy.profiles import build_live_profiles
        from tests.strategy.live_fixtures import registry, summary
        s = summary().read()
        for name, profile in build_live_profiles(summary(), registry()).items():
            p = profile.read()
            held = p['gas_floor_bnb_units'] + p['gas_top_up_min_receive_units']
            value = Fraction(held * s['bnb_price_units'], 10**s['bnb_decimals'])
            with self.subTest(profile=name):
                self.assertLessEqual(value, Fraction(5, 100) * p['expected_equity_units'])


# ---------------------------------------------------------------------------------------------- driver (PostgreSQL)
class ReconcileHarness(ServiceHarness):
    def setUp(self):
        super().setUp()
        self.chain = None

    def book(self):
        return self.store.load(RUN).read()['projection']['portfolio']

    def build(self, *, rounds=False, **raw):
        from larp.runtime.driver import BalanceCheck, RuntimeHealth
        from larp.execution_live.balances import read_balances
        driver = self.service_driver()
        if not rounds:
            driver.work.next = lambda now_ms, epoch: None
        self.chain = chain_for(self.book(), **raw)
        c = driver.coordinator
        check = BalanceCheck(c, lambda now_ms: read_balances(self.chain, wallet=WALLET, observed_at='x'),
                             interval_ms=INTERVAL, max_age_ms=MAX_AGE)
        driver.balance_check = check
        c.context_builder.health = RuntimeHealth(self.store, RUN, self.epoch, balances=check)
        return driver

    def health(self, driver):
        return driver.coordinator.context_builder.health(self.store.load(RUN).read())

    def events(self, kind):
        return [d.read()['event'] for d in self.store.journal(RUN) if d.read()['event']['kind'] == kind]

    def incidents(self, kind):
        return [e for e in self.events('INCIDENT') if e['incident']['type'] == kind]

    def tick(self, driver, ms=SECOND):
        self.w.clock.now += ms
        return driver.once(self.w.clock())


class Startup(ReconcileHarness):
    def test_b3_no_new_spending_before_this_process_checks(self):
        driver = self.build()
        self.assertEqual((self.health(driver)['balances_ok'], self.health(driver)['new_spending_ok']), (False, False))
        self.assertEqual(self.tick(driver)['balance_check'], 'MATCH')
        self.assertEqual((self.health(driver)['balances_ok'], self.health(driver)['new_spending_ok']), (True, True))
        [event] = self.events('BALANCE_CHECKED')
        self.assertEqual(event['check']['status'], 'MATCH')
        self.w.clock.now += SECOND
        restarted = self.build()  # a new process: the journaled MATCH is not its own
        self.assertFalse(self.health(restarted)['balances_ok'])
        self.assertEqual(self.tick(restarted)['balance_check'], 'MATCH')
        self.assertTrue(self.health(restarted)['balances_ok'])

    def test_b3_one_check_per_interval(self):
        driver = self.build()
        self.tick(driver)
        self.assertNotIn('balance_check', self.tick(driver, MINUTE))
        self.assertEqual(self.tick(driver, INTERVAL)['balance_check'], 'MATCH')
        self.assertTrue(self.health(driver)['balances_ok'])
        # Unchanged within the hour: checked, but not journaled again (each commit copies the projection).
        self.assertEqual(len(self.events('BALANCE_CHECKED')), 1)
        self.tick(driver, 60 * MINUTE)
        self.assertEqual(len(self.events('BALANCE_CHECKED')), 2)


class Surplus(ReconcileHarness):
    def test_b4_a_surplus_is_recorded_once_and_adopted_at_the_confirming_check(self):
        # Changed by the owner decisions of 2026-10-16 (D2: a surplus on our own assets is adopted; PR 4 S6). It used
        # to assert that the ledger never changes.
        cost = self.book()['positions']['NVDAB']['cost_basis_units']
        driver = self.build(NVDAB=2500)
        self.assertEqual(self.tick(driver)['balance_check'], 'SURPLUS_ONLY')
        self.assertTrue(self.health(driver)['new_spending_ok'])
        self.assertEqual(len(self.incidents('BALANCE_SURPLUS')), 1)
        self.assertEqual(self.incidents('BALANCE_SURPLUS')[0]['incident']['assets'], ['NVDAB'])
        self.assertEqual(self.tick(driver, INTERVAL)['balance_check'], 'ADJUSTED')
        self.assertEqual(len(self.incidents('BALANCE_SURPLUS')), 1)  # not repeated for the same asset
        self.assertTrue(self.health(driver)['new_spending_ok'])
        after = self.store.load(RUN).read()['projection']
        self.assertEqual(after['portfolio']['positions']['NVDAB'], dict(units=2500, decimals=4, cost_basis_units=cost))
        self.assertEqual(after['balances']['NVDAB'], 2500)


class Deficit(ReconcileHarness):
    def test_b5_a_deficit_blocks_new_spending_and_caps_the_mandatory_sale(self):
        # The D1 window: until the confirming check adopts the chain units (PR 4 S8), new spending waits and the sale
        # is capped. The first check never rewrites the ledger.
        before = deepcopy(self.store.load(RUN).read()['projection'])
        driver = self.build(rounds=True, NVDAB=1500)
        summary = self.tick(driver)
        self.assertEqual(summary['balance_check'], 'DEFICIT')
        self.assertEqual(len(self.incidents('BALANCE_DEFICIT')), 1)
        self.assertEqual(self.incidents('BALANCE_DEFICIT')[0]['incident']['deficits'], {'NVDAB': 500})
        record = self.store.event(RUN, 'plan:' + summary['round_id'])['record']  # closed rounds leave round_records
        context = record['policy_input']['context']
        self.assertEqual(context['portfolio']['positions']['NVDAB']['units'], 1500)
        self.assertEqual((context['health']['balances_ok'], context['health']['new_spending_ok']), (False, False))
        plan = record['plan']
        self.assertFalse([r for r in plan['rejections'] if r.get('reason') == 'EXECUTION_BLOCKED'])
        sells = ([i['token_units'] for i in plan['intents'] if i['symbol'] == 'NVDAB' and i['side'] == 'SELL']
                 + [q['pay_units'] for q in plan['quote_requests'] if q['symbol'] == 'NVDAB' and q['side'] == 'SELL'])
        self.assertEqual(sells, [1500])  # the chain units, never the ledger's 2000
        after = self.store.load(RUN).read()['projection']
        self.assertEqual((after['portfolio']['positions'], after['balances']),
                         (before['portfolio']['positions'], before['balances']))  # the ledger is never rewritten


class Stale(ReconcileHarness):
    def test_b6_an_unavailable_node_stops_new_spending_only_after_the_max_age(self):
        driver = self.build()
        self.assertEqual(self.tick(driver)['balance_check'], 'MATCH')
        self.chain.fail = DependencyUnavailable('RPC unavailable')
        self.assertEqual(self.tick(driver, INTERVAL)['balance_check'], 'SKIPPED:RPC_UNAVAILABLE')
        self.assertEqual(self.events('BALANCE_CHECKED')[-1]['check']['reason'], 'RPC_UNAVAILABLE')
        self.assertTrue(self.health(driver)['balances_ok'])
        self.w.clock.now += MAX_AGE - INTERVAL
        self.assertFalse(self.health(driver)['balances_ok'])
        self.chain.fail = None
        self.assertEqual(self.tick(driver)['balance_check'], 'MATCH')  # retried within a minute of the failure
        self.assertTrue(self.health(driver)['balances_ok'])

    def test_b6_nothing_is_read_or_journaled_while_something_is_in_flight(self):
        driver = self.build(rounds=True)
        driver.balance_check.next_ms = 10**15  # plan the round first, without a check
        self.tick(driver)
        self.assertTrue(self.store.load(RUN).read()['reservations'])
        driver.balance_check.next_ms = 0
        calls = len(self.chain.calls)
        self.assertEqual(driver.balance_check(self.w.clock()), 'IN_FLIGHT')
        self.assertEqual((len(self.chain.calls), self.events('BALANCE_CHECKED')), (calls, []))


class Replay(ReconcileHarness):
    def test_b8_replay_reproduces_checks_incidents_and_the_deficit_view(self):
        driver = self.build(rounds=True, NVDAB=2500)
        self.tick(driver)  # SURPLUS_ONLY, then the filing round
        self.chain.tokens['NVDAB'] = 1500
        driver.work.next = lambda now_ms, epoch: None
        driver.balance_check.next_ms = 0
        driver.balance_check(self.w.clock())  # in flight: skipped without a commit
        head, expected = self.replay_head(driver)
        self.assertEqual(head, expected)
        self.assertTrue(self.events('BALANCE_CHECKED'))

    def test_b8_settled_block_follows_applied_receipts(self):
        if not HAS_ETH:
            self.skipTest('signer dependency not installed')
        driver = self.service_driver()
        execution = Execution(self, remote=True)
        driver.once(self.w.clock())
        [round_id] = self.planned()
        self.assertTrue(self.run_both(driver, execution, until=lambda: self.closed(round_id)))
        blocks = [d.read()['event']['observation']['receipt']['block_number'] for d in self.store.journal(RUN)
                  if d.read()['event']['kind'] == 'OBSERVATION' and 'receipt' in d.read()['event']['observation']]
        self.assertTrue(blocks)
        self.assertEqual(self.store.load(RUN).read()['projection']['settled_block'], max(blocks))


# ---------------------------------------------------------------------------------------------- B9 configuration
class Settings(unittest.TestCase):
    BLOCK = dict(balance_rpc_url='https://rpc.invalid/', balance_rpc_source_id='synthetic-rpc',
                 balance_check_interval_ms=INTERVAL, balance_check_max_age_ms=MAX_AGE,
                 price_jump_check_bps=3000)  # required with the others since PR 4 (S16)

    def test_b9_dev_and_live_need_every_balance_setting(self):
        from larp.runtime.service import balance_settings
        self.assertIsNone(balance_settings({}, 'offline'))
        for mode in ('dev', 'live'):
            for key in self.BLOCK:
                with self.subTest(mode=mode, missing=key), self.assertRaises(ContractError):
                    balance_settings({k: v for k, v in self.BLOCK.items() if k != key}, mode)
            self.assertEqual(balance_settings(self.BLOCK, mode)['interval_ms'], INTERVAL)
        for bad in (dict(balance_check_max_age_ms=INTERVAL - 1), dict(balance_check_interval_ms=0),
                    dict(balance_rpc_url='http://rpc.invalid/')):
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                balance_settings(dict(self.BLOCK, **bad), 'dev')

    def test_b9_the_example_names_every_balance_setting(self):
        from pathlib import Path
        example = json.loads((Path(__file__).resolve().parents[2] / 'config/runtime/runtime.example.json').read_text())
        self.assertTrue(set(self.BLOCK) <= set(example['driver']))
        self.assertEqual((example['driver']['balance_check_interval_ms'], example['driver']['balance_check_max_age_ms']),
                         (INTERVAL, MAX_AGE))


class Composition(unittest.TestCase):
    def test_b9_build_driver_wires_the_check_into_runtime_health(self):
        from larp.runtime.service import build_driver
        from tests.runtime import test_driver as driver_tests
        case = driver_tests.Composition('test_d7_valid_configuration_builds_real_ports_that_pass_the_live_start_check')
        case.setUp()
        self.addCleanup(case.doCleanups)
        driver = build_driver(case.config(**Settings.BLOCK), driver_tests.Store(), case.secrets)
        self.assertIsNotNone(driver.balance_check)
        self.assertIs(driver.coordinator.context_builder.health.balances, driver.balance_check)
        plain = build_driver(case.config(), driver_tests.Store(), case.secrets)
        self.assertIsNone(plain.balance_check)


if __name__ == '__main__':
    unittest.main()

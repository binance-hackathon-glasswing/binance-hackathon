"""IDEA-086 P1-P4: token basis check BV1-BV4 and ratio-scaled valuation BV5, on synthetic cases and on the real
2026-10-23 Web3 responses (docs/build/evidence/basis-sample-20261023/sample.json)."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import unittest

from larp.contracts import Document, TargetKind
from larp.marketdata.basis import BasisVerifier
from larp.marketdata.port import MarketPort, TOKENS
from larp.marketdata.web3 import encoded
from larp.research.fixtures import snapshot
from larp.strategy.policy import decide
from larp.strategy.schema import market_view

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = json.loads((ROOT / 'docs/build/evidence/basis-sample-20261023/sample.json').read_text())['fields_0452Z']
EXPECTED = {s: v['underlyingTicker'] for s, v in SAMPLE.items()}
PINNED = dict(NVDAB='NVDA', GOOGLB='GOOGL', TSLAB='TSLA', MSFTB='MSFT', SKHYB='SKHY')


def responses(symbol):
    """The three rows the market port reads for one token, rebuilt from the recorded sample."""
    v = SAMPLE[symbol]
    row = dict(tokenSymbol=v['tokenSymbol'], tokenContractAddress=v['tokenContractAddress'],
               binanceChainId=v['binanceChainId'], platformId=v['platformId'], assetType=v['assetType'],
               decimals='18', underlyingTicker=v['underlyingTicker'], tokenToShareRatio=v['tokenToShareRatio'],
               tokenPrice=v['tokenPrice'], referencePrice=v['referencePrice'], statusInfo={'openState': v['openState']})
    u = v['underlying_market']
    underlying = dict(binanceChainId='56', tokenContractAddress=u['tokenContractAddress'], platformId=u['platformId'],
                      assetType=u['assetType'], statusInfo={'openState': u['openState']})
    price = dict(v['price_endpoint'])
    return row, underlying, price


class BasisChecks(unittest.TestCase):
    def setUp(self):
        self.verify = BasisVerifier(EXPECTED)

    def check(self, symbol='NVDAB', row=None, underlying=None, price=None, verifier=None):
        r, u, p = responses(symbol)
        return (verifier or self.verify)(symbol, row or r, underlying or u, price or p)

    def test_registry_pins_match_the_observed_tickers(self):
        self.assertEqual(EXPECTED, PINNED)

    def test_p2_all_five_real_rows_pass_with_no_reason(self):
        for symbol in TOKENS:
            with self.subTest(symbol=symbol):
                ok, reasons, ratio = self.check(symbol)
                self.assertEqual((ok, reasons), (True, []))
                self.assertEqual(ratio, Decimal(SAMPLE[symbol]['tokenToShareRatio']))

    def test_p1_bv1_identity(self):
        r, u, p = responses('NVDAB')
        cases = {
            'token contract': (dict(r, tokenContractAddress=TOKENS['GOOGLB']), u, p),
            'underlying contract': (r, dict(u, tokenContractAddress=TOKENS['GOOGLB']), p),
            'price contract': (r, u, dict(p, tokenContractAddress=TOKENS['GOOGLB'])),
            'symbol': (dict(r, tokenSymbol='NVDA'), u, p),
            'chain': (dict(r, binanceChainId='1'), u, p),
            'underlying chain': (r, dict(u, binanceChainId='1'), p),
            'platform': (dict(r, platformId='ondo'), u, p),
            'underlying platform': (r, dict(u, platformId='ondo'), p),
            'asset type': (r, dict(u, assetType=2), p),
        }
        for name, (row, underlying, price) in cases.items():
            with self.subTest(case=name):
                ok, reasons, _ = BasisVerifier(EXPECTED)('NVDAB', row, underlying, price)
                self.assertFalse(ok)
                self.assertIn('BV1_IDENTITY', reasons)

    def test_p1_bv2_pinned_underlying(self):
        r, _, _ = responses('NVDAB')
        ok, reasons, _ = self.check(row=dict(r, underlyingTicker='AMD'))
        self.assertEqual((ok, reasons), (False, ['BV2_UNDERLYING']))
        ok, reasons, _ = BasisVerifier(dict(EXPECTED, NVDAB='AMD'))('NVDAB', *responses('NVDAB'))
        self.assertEqual((ok, reasons), (False, ['BV2_UNDERLYING']))
        ok, reasons, _ = BasisVerifier({k: v for k, v in EXPECTED.items() if k != 'NVDAB'})('NVDAB', *responses('NVDAB'))
        self.assertEqual((ok, reasons), (False, ['BV2_UNDERLYING']))

    def test_p1_bv3_ratio_band_and_missing(self):
        r, _, _ = responses('TSLAB')
        for value, reason in (('0.999', 'BV3_RATIO_RANGE'), ('1.0501', 'BV3_RATIO_RANGE'), (None, 'BV3_RATIO_MISSING'),
                              ('NaN', 'BV3_RATIO_MISSING'), ('', 'BV3_RATIO_MISSING'), (1, 'BV3_RATIO_MISSING')):
            with self.subTest(ratio=value):
                row = dict(r, tokenToShareRatio=value)
                ok, reasons, ratio = BasisVerifier(EXPECTED)('TSLAB', row, *responses('TSLAB')[1:])
                self.assertFalse(ok)
                self.assertIn(reason, reasons)
                self.assertIsNone(ratio)

    def test_p1_bv3_ratio_ratchet(self):
        r, u, p = responses('MSFTB')
        base = Decimal(r['tokenToShareRatio'])
        self.assertTrue(self.verify('MSFTB', r, u, p)[0])
        lower = str(base - Decimal('0.0001'))
        down = dict(r, tokenToShareRatio=lower,
                    tokenPrice=str(Decimal(r['referencePrice']) * Decimal(lower)))
        ok, reasons, _ = self.verify('MSFTB', down, u, dict(p, tokenPrice=r['referencePrice']))
        self.assertEqual((ok, reasons), (False, ['BV3_RATIO_DECREASED']))
        jump = str(base * Decimal('1.0101'))
        up = dict(r, tokenToShareRatio=jump, tokenPrice=str(Decimal(r['referencePrice']) * Decimal(jump)))
        ok, reasons, _ = self.verify('MSFTB', up, u, dict(p, tokenPrice=r['referencePrice']))
        self.assertEqual((ok, reasons), (False, ['BV3_RATIO_STEP']))
        # A refused observation never moves the ratchet; a small rise is accepted and then becomes the floor.
        small = str(base * Decimal('1.0001'))
        rise = dict(r, tokenToShareRatio=small, tokenPrice=str(Decimal(r['referencePrice']) * Decimal(small)))
        self.assertTrue(self.verify('MSFTB', rise, u, dict(p, tokenPrice=r['referencePrice']))[0])
        self.assertEqual(self.verify('MSFTB', r, u, p)[1], ['BV3_RATIO_DECREASED'])

    def test_p1_bv4_mark_integrity(self):
        r, u, p = responses('NVDAB')
        mark = Decimal(r['tokenPrice'])
        off = dict(r, tokenPrice=str(mark * Decimal('1.00011')))  # 1.1 bp from referencePrice x ratio
        ok, reasons, _ = BasisVerifier(EXPECTED)('NVDAB', off, u, p)
        self.assertFalse(ok)
        self.assertIn('BV4_MARK', reasons)
        inside = dict(p, tokenPrice=str(Decimal(p['tokenPrice']) * Decimal('1.0024')))  # 24 bp from the mark
        self.assertTrue(BasisVerifier(EXPECTED)('NVDAB', r, u, inside)[0])
        outside = dict(p, tokenPrice=str(Decimal(p['tokenPrice']) * Decimal('1.0026')))
        ok, reasons, _ = BasisVerifier(EXPECTED)('NVDAB', r, u, outside)
        self.assertEqual((ok, reasons), (False, ['BV4_ENDPOINT']))
        for field, row, price in (('row tokenPrice', dict(r, tokenPrice=None), p),
                                  ('referencePrice', dict(r, referencePrice='x'), p),
                                  ('price tokenPrice', r, dict(p, tokenPrice='0'))):
            with self.subTest(field=field):
                ok, reasons, _ = BasisVerifier(EXPECTED)('NVDAB', row, u, price)
                self.assertFalse(ok)
                self.assertIn('BV4_PRICE_MISSING', reasons)

    def test_unknown_symbol_or_bad_pins_refuse_construction(self):
        for bad in ({'NVDA': 'NVDA'}, {'NVDAB': ''}, {'NVDAB': 7}, []):
            with self.subTest(pins=bad), self.assertRaises(ValueError):
                BasisVerifier(bad)


class SampleClient:
    """Serves the recorded 2026-10-23 rows through the real MarketPort parsing path."""
    def __init__(self, mutate=None):
        self.rows = {s: responses(s) for s in TOKENS}
        if mutate:
            mutate(self.rows)

    def request(self, method, endpoint, params):
        stamp = '2026-10-23T04:52:00Z'
        if endpoint == 'market/rwa/tokens':
            body = [self.rows[s][0] for s in TOKENS]
        elif endpoint == 'market/rwa/underlying-market':
            body = next(v[1] for s, v in self.rows.items() if TOKENS[s] == params['tokenContractAddress'])
        elif endpoint == 'market/rwa/price':
            body = [next(v[2] for s, v in self.rows.items() if TOKENS[s] == params['tokenContractAddresses'])]
        else:
            raise AssertionError(endpoint)
        return dict(response={'data': body}, available_at=stamp, artifact_sha256=hashlib.sha256(encoded(body)).hexdigest())


def no_cost(symbol):
    from larp.marketdata.web3 import Unavailable
    raise Unavailable('transport_error')


class PortWiring(unittest.TestCase):
    def rows(self, verifier, mutate=None):
        return {m['symbol']: m for m in MarketPort(SampleClient(mutate), '0x' + '1' * 40, basis_verifier=verifier,
                                                    cost_observation=no_cost)(0)}

    def test_p2_port_marks_all_five_verified_and_records_no_reason(self):
        rows = self.rows(BasisVerifier(EXPECTED))
        self.assertEqual({s: (m['basis_verified'], m['basis_checks']) for s, m in rows.items()},
                         {s: (True, []) for s in TOKENS})
        view = market_view(list(rows.values()), tuple(TOKENS), datetime(2026, 10, 23, 4, 52, 30, tzinfo=timezone.utc),
                           {'quote_age_seconds': 60})
        self.assertTrue(all(view[s] is not None and view[s]['basis_verified'] for s in TOKENS))

    def test_p4_price_units_are_the_ratio_scaled_mark(self):
        rows = self.rows(BasisVerifier(EXPECTED))
        for symbol, m in rows.items():
            with self.subTest(symbol=symbol):
                per_share = Decimal(SAMPLE[symbol]['price_endpoint']['tokenPrice'])
                ratio = Decimal(SAMPLE[symbol]['tokenToShareRatio'])
                self.assertEqual(m['price_units'], int(per_share * ratio * 1000000))
                self.assertEqual(m['token_to_share_ratio'], str(ratio))
        msft = rows['MSFTB']['price_units'] / (Decimal(SAMPLE['MSFTB']['price_endpoint']['tokenPrice']) * 1000000)
        self.assertAlmostEqual(float(msft), 1.0013139648, places=6)

    def test_without_verifier_behaviour_is_unchanged(self):
        rows = self.rows(None)
        for symbol, m in rows.items():
            with self.subTest(symbol=symbol):
                self.assertFalse(m['basis_verified'])
                self.assertEqual(m['basis_checks'], ['NO_VERIFIER'])
                self.assertEqual(m['price_units'], int(Decimal(SAMPLE[symbol]['price_endpoint']['tokenPrice']) * 1000000))
                self.assertNotIn('token_to_share_ratio', m)

    def test_a_failed_check_is_unverified_with_its_reason_and_other_names_unaffected(self):
        def repoint(rows):
            r, u, p = rows['GOOGLB']
            rows['GOOGLB'] = (dict(r, underlyingTicker='GOOG'), u, p)
        rows = self.rows(BasisVerifier(EXPECTED), repoint)
        self.assertEqual((rows['GOOGLB']['basis_verified'], rows['GOOGLB']['basis_checks']), (False, ['BV2_UNDERLYING']))
        self.assertTrue(all(rows[s]['basis_verified'] for s in TOKENS if s != 'GOOGLB'))


class PolicyEndToEnd(unittest.TestCase):
    """P3: the EQUAL_WEIGHT policy, fed the basis outcome the real port produces, enters instead of holding."""
    EW = {"baseline": "EQUAL_WEIGHT", "operating_name_weight": [1, 5], "operating_gross_weight": [4, 5],
          "regime_gross_weight": [4, 5], "top_up_below_gross_weight": [3, 4]}

    def decide_with(self, verifier):
        rows = MarketPort(SampleClient(), '0x' + '1' * 40, basis_verifier=verifier, cost_observation=no_cost)(0)
        verified = {m['symbol']: m['basis_verified'] for m in rows}
        s = snapshot(profile_changes=self.EW)
        c = deepcopy(s.context.read())
        for m in c['markets']:
            m['basis_verified'] = verified[m['symbol']]
        s = replace(s, context=Document.from_dict(c))
        return {t.symbol: t for t in decide(s, s.policy_state).targets}

    def test_p3_with_verifier_entries_are_planned(self):
        targets = self.decide_with(BasisVerifier(EXPECTED))
        self.assertTrue(any(t.kind == TargetKind.TARGET_WEIGHT and t.weight == Fraction(1, 5) for t in targets.values()))
        self.assertFalse(any(t.reason == 'MISSING_MARKET_OR_BASIS' for t in targets.values()))

    def test_p3_without_verifier_every_name_is_held_as_today(self):
        targets = self.decide_with(None)
        self.assertTrue(targets)
        self.assertTrue(all((t.kind, t.reason) == (TargetKind.KEEP_QUANTITY, 'MISSING_MARKET_OR_BASIS')
                            for t in targets.values()))


if __name__ == '__main__':
    unittest.main()

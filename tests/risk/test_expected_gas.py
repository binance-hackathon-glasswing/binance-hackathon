"""IDEA-088 QV6: reserved gas and expected gas in the planner (SJ-11-QV01).

The run-3 S1 profile's action budget (the reservation) and sizing budget (the expected fee), valued at its BNB price,
are expressed in the fixture ledger's BNB units (6 decimals at 1 USDT per BNB), so each keeps its USDT value.
"""
from fractions import Fraction
import json
from pathlib import Path
import unittest

from larp.research.fixtures import changed, snapshot, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.schema import ceil

S1 = json.loads((Path(__file__).resolve().parents[2] /
                 'docs/build/evidence/s1-rehearsal-profile-20261023/rehearsal-s1-deterministic.json').read_bytes())


def fixture_units(budget):
    summary = S1['quote_cost_summary']
    return ceil(Fraction(budget * summary['bnb_price_units'], 10**summary['bnb_decimals']))


RESERVED = fixture_units(S1['gas_action_budget_units'])  # about 0.277 USDT
EXPECTED = fixture_units(S1['gas_sizing_budget_units'])  # about 0.058 USDT


def planned(gas, expected=None):
    s = with_quotes(snapshot(profile_changes={'cost_reserve_units': 1_000_000}), gas=gas)
    if expected is not None:
        c = s.context.read()
        for m in c['markets']:
            for q in m['quotes']:
                q['expected_gas_bnb_units'] = expected
        s = changed(s, markets=c['markets'])
    return plan(s, decide(s, s.policy_state)).read()


class ExpectedGas(unittest.TestCase):
    def test_qv6_reserved_gas_alone_fails_the_entry_cost_cap(self):
        result = planned(RESERVED)
        self.assertEqual(result['intents'], [])
        self.assertIn('ENTRY_COST_CAP', [r['reason'] for r in result['rejections']])

    def test_qv6_expected_gas_prices_the_entry_and_the_full_reservation_is_kept(self):
        result = planned(RESERVED, EXPECTED)
        [intent] = result['intents']
        [delta] = result['reservation_deltas']
        self.assertEqual((intent['side'], intent['gas_bnb_units'], delta['bnb_units']), ('BUY', RESERVED, RESERVED))
        self.assertNotIn('ENTRY_COST_CAP', [r['reason'] for r in result['rejections']])

    def test_qv6_expected_gas_must_lie_inside_the_reservation(self):
        for expected in (RESERVED + 1, 0, -1, '57775'):
            with self.subTest(expected=expected):
                result = planned(RESERVED, expected)
                self.assertEqual(result['intents'], [])
                self.assertIn('QUOTE_ROUTE_OR_SLIPPAGE', [r['reason'] for r in result['rejections']])

    def test_qv6_an_expected_gas_equal_to_the_reservation_changes_nothing(self):
        without, equal = planned(10_000), planned(10_000, 10_000)
        self.assertEqual([(i['symbol'], i['token_units'], i['gas_bnb_units']) for i in without['intents']],
                         [(i['symbol'], i['token_units'], i['gas_bnb_units']) for i in equal['intents']])
        self.assertEqual(without['reservation_deltas'][0]['bnb_units'], equal['reservation_deltas'][0]['bnb_units'])


if __name__ == '__main__':
    unittest.main()

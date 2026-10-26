"""IDEA-090 F9 (S2-F4): a better-than-mark BUY quote is completed by a second follow-up round.

When the follow-up's quote would receive more tokens than the target, the planner asks for a smaller quote
(`BUY_RECEIVE_TARGET_REQUOTE`). With one follow-up round the driver stopped there and the round planned nothing.
Synthetic prices, no venue calls.
"""
import json
from pathlib import Path
import unittest

from larp.research.fixtures import changed, with_quotes
from larp.strategy import execution_bounds as bounds
from tests.strategy.test_execution_bounds import at, run

ROOT = Path(__file__).resolve().parents[2]


def follow_up(snapshot, plan, round_id, *, spread_bps):
    authority = bounds.parent_authority(dict(round_id=round_id, policy_input=dict(context=snapshot.context.read()),
                                             plan=plan))
    child = changed(snapshot, execution_attempt_budget=plan['execution_attempt_budget'], execution_parent=authority)
    return with_quotes(child, spread_bps=spread_bps)


class SecondFollowUp(unittest.TestCase):
    def test_f9_a_better_than_mark_quote_is_bought_on_the_parents_attempt(self):
        snapshot = at('2026-10-10T14:00:00Z')
        parent = run(snapshot)
        [asked] = parent['quote_requests']
        first = follow_up(snapshot, parent, 'parent', spread_bps=-10)  # 10 bps better than the mark
        child = run(first)
        self.assertEqual(child['intents'], [])
        [smaller] = child['quote_requests']
        self.assertEqual((smaller['symbol'], smaller['side']), (asked['symbol'], asked['side']))
        self.assertLess(smaller['pay_units'], asked['pay_units'])
        self.assertIn('BUY_RECEIVE_TARGET_REQUOTE', [r['reason'] for r in child['rejections']])
        second = run(follow_up(first, child, 'parent/quote1', spread_bps=-10))
        [intent] = second['intents']
        self.assertEqual((intent['symbol'], intent['pay_units']), (asked['symbol'], smaller['pay_units']))
        leg = intent['execution_bounds']['leg']
        self.assertEqual(intent['execution_bounds']['ordinal'], 1)
        self.assertEqual(second['execution_attempt_budget']['counts'], {leg: 1})

    def test_f9_the_example_runtime_allows_the_second_follow_up(self):
        driver = json.loads((ROOT / 'config/runtime/runtime.example.json').read_text())['driver']
        self.assertGreaterEqual(driver['max_quote_rounds'], 2)


if __name__ == '__main__':
    unittest.main()

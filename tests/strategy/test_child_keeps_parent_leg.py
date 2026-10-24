"""IDEA-090 F8 (S2-F3): a quote follow-up plans the leg its parent requested.

Run 4, 06:45Z: the parent round requested a TSLAB quote; in the follow-up the fresh prices made NVDAB's notional
marginally larger (every unheld S1 name targets the same weight), so the child requested NVDAB, spent NVDAB's attempt
and never used TSLAB's executable quote. Synthetic prices, no venue calls.
"""
import unittest

from larp.research.fixtures import changed, with_quotes
from larp.strategy import execution_bounds as bounds
from tests.strategy.test_execution_bounds import at, run

STAMP = '2026-10-10T14:00:00Z'


def parent_and_child(bump):
    """The parent's plan and its quote follow-up's snapshot, with `bump` added to other names' prices in the child."""
    snapshot = at(STAMP)
    parent = run(snapshot)
    authority = bounds.parent_authority(dict(round_id='parent', policy_input=dict(context=snapshot.context.read()),
                                             plan=parent))
    child = changed(with_quotes(snapshot), execution_attempt_budget=parent['execution_attempt_budget'],
                    execution_parent=authority)
    asked = parent['quote_requests'][0]['symbol']
    markets = child.context.read()['markets']
    for m in markets:
        if m['symbol'] != asked:
            m['price_units'] += bump.get(m['symbol'], 0)
    return parent, changed(child, markets=markets), asked


class ChildKeepsParentLeg(unittest.TestCase):
    def test_f8_a_follow_up_plans_its_parents_leg_when_another_leg_is_marginally_larger(self):
        for bump in ({'NVDAB': 1}, {'NVDAB': 1, 'TSLAB': 2, 'MSFTB': 3, 'SKHYB': 4}, {'TSLAB': 250}):
            with self.subTest(bump=bump):
                parent, child, asked = parent_and_child(bump)
                result = run(child)
                self.assertEqual([i['symbol'] for i in result['intents']], [asked], result['quote_requests'])
                self.assertEqual(result['quote_requests'], [])
                leg = 'DISCRETIONARY:BUY:' + asked
                self.assertEqual(result['intents'][0]['execution_bounds']['ordinal'], 1)  # the parent's attempt
                self.assertEqual(result['execution_attempt_budget']['counts'], {leg: 1})  # no other leg spent

    def test_f8_a_fresh_round_does_not_reorder_legs_on_a_sub_unit_price_move(self):
        snapshot = at(STAMP)
        first = run(snapshot)['quote_requests'][0]['symbol']
        markets = snapshot.context.read()['markets']
        for m in markets:
            if m['symbol'] != first:
                m['price_units'] += 1
        self.assertEqual(run(changed(snapshot, markets=markets))['quote_requests'][0]['symbol'], first)

    def test_f8_a_parent_from_another_session_does_not_steer_the_order(self):
        parent, child, asked = parent_and_child({'NVDAB': 300})  # NVDAB larger by whole cash units
        context = child.context.read()
        stale = dict(context['execution_parent'], session_index=context['session_index'] - 1)
        result = run(changed(child, execution_parent=stale))
        self.assertNotIn(asked, [i['symbol'] for i in result['intents']])


if __name__ == '__main__':
    unittest.main()

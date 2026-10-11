"""IDEA-037 R01: hard-line reductions survive settlement and persisted risk-state reload."""
from fractions import Fraction
import unittest

from larp.contracts import Document
from larp.research.fixtures import changed, fill_fixture, reserve_fixture, with_quotes
from larp.risk.accounting import advance_accounting
from larp.risk.planner import plan
from larp.strategy.schema import equity, markets, profile, value
from tests.strategy.test_equal_weight import ew


class TrimReplanning(unittest.TestCase):
    def settled_child(self, s, *, gas=10000, spread_bps=10):
        # Each round obtains fresh exact-size quotes; install the planner's persisted risk state,
        # then use the real accounting reducer for the committed reservation and final fill.
        s = with_quotes(s, policy=False, gas=gas, spread_bps=spread_bps)
        result = plan(s, None)
        self.assertEqual(len(result.read()['intents']), 1)
        reserved = reserve_fixture(s, result)
        ledger = reserved.context.read()['portfolio']
        ledger['risk'] = result.read()['risk_state']
        ledger = advance_accounting(Document.from_dict(ledger),
                                   fill_fixture(s, result.read()['intents'][0], gas=gas)).read()
        # Canonical bytes round trip models a process restart (no local latch survives).
        ledger = Document.from_dict(ledger).read()
        context = s.context.read()
        context['portfolio'] = ledger
        context['markets'] = [dict(m, quotes=[]) for m in context['markets']]
        return changed(s, **context)

    def exposure(self, s):
        c = s.context.read()
        m = markets(s, profile(s))
        safe = equity(c['portfolio'], m) - c['profile']['cost_reserve_units']
        return c, m, safe

    def test_gross_trim_continues_below_trigger_until_target_after_reload(self):
        s = ew(held=dict.fromkeys(('NVDAB', 'GOOGLB', 'TSLAB', 'MSFTB'), 4600))
        # Zero-cost controls isolate obligation completion from the existing dust/gas policy.
        s = self.settled_child(s, gas=0, spread_bps=0)
        c, m, safe = self.exposure(s)
        gross = sum(value(p['units'], m[n]) for n, p in c['portfolio']['positions'].items())
        self.assertTrue(safe * Fraction(4, 5) < gross < safe * Fraction(9, 10))
        self.assertTrue(plan(s, None).read()['requirements'])
        for _ in range(4):
            result = plan(s, None).read()
            if not result['requirements']:
                break
            s = self.settled_child(s, gas=0, spread_bps=0)
        else:
            self.fail('gross reduction did not finish')
        c, m, safe = self.exposure(s)
        self.assertLessEqual(sum(value(p['units'], m[n]) for n, p in c['portfolio']['positions'].items()),
                             safe * Fraction(4, 5))
        self.assertFalse(result['risk_state']['cap_trims']['gross'])
        self.assertEqual(result['risk_state']['cap_trims']['gross_shares'], {})

    def test_costly_gross_trim_keeps_dust_residual_explicit(self):
        s = ew(held=dict.fromkeys(('NVDAB', 'GOOGLB', 'TSLAB', 'MSFTB'), 4600))
        for _ in range(4):
            s = self.settled_child(s)
        result = plan(with_quotes(s, policy=False), None).read()
        self.assertTrue(result['requirements'])
        self.assertTrue(result['risk_state']['cap_trims']['gross'])
        self.assertFalse(result['intents'])
        self.assertTrue(all(r['status'] == 'DUST_OR_UNEXECUTABLE' for r in result['requirements']))

    def test_capped_name_trim_continues_below_trigger_until_target(self):
        s = ew(held={'NVDAB': 5200}, profile_changes={'per_trade_cap_units': 6000000})
        s = self.settled_child(s)
        c, m, safe = self.exposure(s)
        self.assertTrue(safe / 5 < value(c['portfolio']['positions']['NVDAB']['units'], m['NVDAB']) < safe / 4)
        self.assertTrue(plan(s, None).read()['requirements'])
        for _ in range(10):
            result = plan(s, None).read()
            if not result['requirements']:
                break
            s = self.settled_child(s)
        else:
            self.fail('name reduction did not finish')
        c, m, safe = self.exposure(s)
        self.assertLessEqual(value(c['portfolio']['positions']['NVDAB']['units'], m['NVDAB']), safe / 5)
        self.assertEqual(result['risk_state']['cap_trims']['names'], [])

    def test_no_trim_for_drift_without_a_prior_trigger(self):
        s = ew(held=dict.fromkeys(('NVDAB', 'GOOGLB', 'TSLAB', 'MSFTB'), 4250))
        self.assertFalse(plan(s, None).read()['requirements'])
        self.assertFalse(plan(ew(held={'NVDAB': 4800}), None).read()['requirements'])

    def test_execution_block_keeps_obligation_and_missing_mark_cannot_clear_it(self):
        s = self.settled_child(ew(held={'NVDAB': 5200}, profile_changes={'per_trade_cap_units': 6000000}))
        c = s.context.read()
        c['health']['integrity_ok'] = False
        blocked = plan(changed(s, **c), None).read()
        self.assertFalse(blocked['intents'])
        self.assertIn('NVDAB', blocked['risk_state']['cap_trims']['names'])
        c['markets'] = [dict(m, quality='UNAVAILABLE') if m['symbol'] == 'NVDAB' else m for m in c['markets']]
        missing = plan(changed(s, **c), None).read()
        self.assertIn('NVDAB', missing['risk_state']['cap_trims']['names'])
        self.assertEqual(missing['requirements'][0]['status'], 'BLOCKED')

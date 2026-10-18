"""OP-01 prospective regressions: synthetic accounting and real verifier, no network."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from larp.intelligence.common import IntelligenceError
from larp.intelligence.model_budget import ModelBudget
from tests.intelligence.test_aiand_routing import Routing


def policy(start=1000):
    return dict(schema='OpenAIPacing.v1', total_micro_usd=50_000_000,
                prior_spent_micro_usd=2_000_000, start_ms=start,
                end_ms=start+4000, period_ms=1000)


class Pacing(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'budget.sqlite'; self.now=1000; self.p=policy()

    def init(self):
        return ModelBudget.initialize(self.path,'paced',initial_spent=2_000_000,
            total=50_000_000,reserve=0,pacing=self.p,clock_ms=lambda:self.now)

    def reopen(self, **kw):
        return ModelBudget(self.path,'paced',total=50_000_000,reserve=0,
                           pacing=kw.get('pacing',self.p),clock_ms=lambda:self.now)

    def test_period_carry_forward_and_final_release(self):
        b=self.init(); self.assertEqual(b.snapshot()['available_micro_usd'],12_000_000)
        token=b.admit(1_000_000,'one'); b.settle(token,500_000)
        self.now=2000
        self.assertEqual(self.reopen().snapshot()['available_micro_usd'],23_500_000)
        self.now=4000
        self.assertEqual(b.snapshot()['available_micro_usd'],47_500_000)
        self.assertFalse(b.snapshot()['external_only'])

    def test_temporary_refusal_recovers_next_period(self):
        b=self.init(); token=b.admit(12_000_000,'first')
        with self.assertRaises(IntelligenceError): b.admit(1,'paced')
        self.assertFalse(self.reopen().snapshot()['external_only'])
        b.settle(token,None); self.now=2000
        self.assertIsNotNone(self.reopen().admit(12_000_000,'later'))

    def test_atomic_workers_do_not_overspend_period_or_latch(self):
        self.init()
        def attempt(n):
            try: return self.reopen().admit(8_000_000,str(n))
            except IntelligenceError: return None
        with ThreadPoolExecutor(max_workers=4) as pool: tokens=list(pool.map(attempt,range(4)))
        self.assertEqual(sum(t is not None for t in tokens),1)
        self.assertFalse(self.reopen().snapshot()['external_only'])

    def test_policy_binding_and_legacy_bypass_refused(self):
        self.init()
        with self.assertRaises(IntelligenceError): ModelBudget(self.path,'paced',reserve=0)
        changed=deepcopy(self.p); changed['end_ms']+=1
        with self.assertRaises(IntelligenceError): self.reopen(pacing=changed)
        with self.assertRaises(FileExistsError): self.init()


class Preferred(unittest.TestCase):
    def setUp(self):
        # Reuse only the synthetic HTTP/evidence fixture, not its legacy test cases.
        self.fx=Routing(); self.fx.setUp(); self.addCleanup(self.fx.doCleanups)
        f=self.fx; (f.root/'openai-budget.sqlite').unlink()
        f.s['schema']='AIandRouting.v3'
        f.s['openai_pacing']=policy(f.w.clock())
        ModelBudget.initialize(f.root/'openai-budget.sqlite',f.s['budget_account'],
            initial_spent=2_000_000,total=50_000_000,reserve=0,
            pacing=f.s['openai_pacing'],clock_ms=f.w.clock)

    def test_openai_is_first_and_aiand_reviews_original_evidence(self):
        f=self.fx; _,result=f.run_assessment(f.build())
        self.assertEqual(f.calls[0][0],'openai')
        self.assertEqual(result['routing']['stages'][0]['stage'],'openai-primary')
        self.assertTrue(any(c[:3]==('aiand','moonshotai/kimi-k3','high') for c in f.calls))
        self.assertEqual(result['routing']['budget']['reserve_micro_usd'],0)

    def test_missing_openai_key_uses_high_effort_fallback(self):
        f=self.fx; _,result=f.run_assessment(f.build(key=False))
        self.assertEqual(f.calls[0][:3],('aiand','moonshotai/kimi-k3','high'))
        self.assertEqual(result['status'],'ASSESSED')

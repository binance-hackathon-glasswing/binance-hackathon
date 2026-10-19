"""IDEA083 AB/IR179 red-first regressions: synthetic workers, no provider network."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import tempfile
import threading
import unittest

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError
from larp.intelligence.config import load_config
from tests.intelligence import test_openai_pacing as preferred


def candidate(status='ASSESSED', finding='same', identity='primary'):
    return dict(status=status, result_id=identity, reasons=[], findings=[dict(type=finding)],
                event_findings=[], falsifiers=[], claims=[dict(text='immutable primary claim')],
                rationale='immutable primary rationale', confidence=dict(level='HIGH'))


class BudgetContract(unittest.TestCase):
    def test_config_supports_180_seconds_but_preserves_six_tools(self):
        for mode in ('development', 'shadow'):
            self.assertEqual(load_config(mode).max_deadline_ms, 180000)
            self.assertEqual(load_config(mode).max_tool_calls, 6)

    def test_one_budget_contract_bounds_stage_shares_and_tool_allocations(self):
        from larp.intelligence.time_budget import stage_limits, reviewer_tools
        for total, primary in ((180000,60000),(120000,40000),(60000,20000),(600,200)):
            self.assertEqual(stage_limits(total), (primary, min(90000,total-primary)))
        for total in (0,180001,True,'180000'):
            with self.subTest(total=total),self.assertRaises(IntelligenceError):stage_limits(total)
        self.assertEqual(reviewer_tools(6,3,2), (2,1))
        self.assertEqual(reviewer_tools(6,0,2), (3,3))
        self.assertEqual(reviewer_tools(2,2,2), (0,0))


class ReviewOutcomes(unittest.TestCase):
    def test_full_b11_matrix_is_deterministic_and_does_not_mutate_primary(self):
        from larp.intelligence.routing import review_outcome
        kinds=('confirm','different','abstain','timeout','error')
        for primary_status in ('ASSESSED','ABSTAIN','ERROR','TIMEOUT','NOT_RUN'):
            for a in kinds:
                for b in kinds:
                    primary=candidate(primary_status)
                    original=deepcopy(primary)
                    replies=[]
                    for n,kind in enumerate((a,b)):
                        replies.append(candidate({'confirm':'ASSESSED','different':'ASSESSED','abstain':'ABSTAIN',
                                                  'timeout':'UNAVAILABLE','error':'UNAVAILABLE'}[kind],
                                                 'different' if kind=='different' else 'same',str(n)))
                    selected,outcome,verdicts=review_outcome(primary,replies)
                    if primary_status=='ASSESSED':
                        expected='DISSENT' if any(k in ('different','abstain') for k in (a,b)) else \
                                 'CONFIRMED' if 'confirm' in (a,b) else 'INCOMPLETE'
                        self.assertEqual(outcome,expected)
                        if expected!='DISSENT':self.assertEqual(selected,primary)
                        else:self.assertEqual(selected['status'],'ABSTAIN')
                    else:
                        assessed=[r for r in replies if r['status']=='ASSESSED']
                        if len(assessed)==2 and a!=b:
                            self.assertEqual((selected['status'],outcome),('ABSTAIN','DISSENT'))
                        elif assessed:
                            self.assertEqual((selected['result_id'],outcome),(assessed[0]['result_id'],'FALLBACK'))
                        else:self.assertEqual((selected,outcome),(None,'NONE_AVAILABLE'))
                    self.assertEqual(len(verdicts),2)
                    self.assertEqual(primary,original)


class ParallelRouting(unittest.TestCase):
    def setUp(self):
        fixture=preferred.Preferred();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.fx=fixture.fx

    def test_both_reviewers_enter_transport_before_either_completes(self):
        f=self.fx; original=f.aiand; barrier=threading.Barrier(2,timeout=2); entered=set();lock=threading.Lock()
        def simultaneous(*args):
            import json
            model=json.loads(args[2])['model']
            with lock:
                first=model not in entered; entered.add(model)
            if first:barrier.wait()
            return original(*args)
        f.aiand=simultaneous
        _,result=f.run_assessment(f.build())
        self.assertEqual(len(entered),2)
        self.assertEqual(len([s for s in result['routing']['stages'] if s['stage'].startswith('external-review')]),2)
        self.assertIn(result['routing']['review_outcome'],('CONFIRMED','DISSENT','INCOMPLETE','FALLBACK'))
        self.assertLessEqual(result['budget_used']['tool_calls'],6)

    def test_primary_timeout_starts_reviewers_but_retains_owned_lane(self):
        f=self.fx; old_primary=f.openai; old_review=f.aiand
        primary_entered=threading.Event();release=threading.Event();reviewed=threading.Event()
        calls=[];lock=threading.Lock()
        def primary(*args):
            primary_entered.set()
            release.wait(3)
            return old_primary(*args)
        def review(*args):
            import json
            with lock:
                calls.append(json.loads(args[2])['model'])
                if len(set(calls))==2:reviewed.set()
            return old_review(*args)
        f.openai=primary;f.aiand=review
        router=f.build();req=f.w.request(['EXSEMI_Q3_8K'],issuer_id=preferred.fixtures.EXSEMI,
                                       job_id='bounded-primary',deadline_ms=600)
        from larp.runtime.deferred_models import DeferredAssessments
        q=DeferredAssessments(router,root=f.root/'deferred',run_id=req.read()['run_id'],build_id='e'*40,
                              profile_hash=req.read()['policy_profile_hash'])
        def cleanup():release.set();q.finished.wait(4)
        self.addCleanup(cleanup)
        self.assertTrue(q.submit('bounded-primary',req));self.assertTrue(primary_entered.wait(1))
        try:
            self.assertTrue(reviewed.wait(1.5),'both reviewers must start before late primary exits')
            self.assertFalse(q.finished.is_set())
            self.assertFalse(q.submit('second',req))
        finally:release.set()
        self.assertTrue(q.finished.wait(3))
        value=q.ready()
        self.assertEqual(value['audit']['events'][-1]['kind'],'RESULT')
        self.assertEqual(len(value['result']['routing']['stages']),3)
        q.ack('bounded-primary')


class ConcurrentAudit(unittest.TestCase):
    def test_simultaneous_callbacks_form_one_valid_durable_chain(self):
        from larp.runtime.deferred_models import DeferredAssessments
        with tempfile.TemporaryDirectory() as tmp:
            q=DeferredAssessments(object(),root=tmp,run_id='r',build_id='b'*40,profile_hash='a'*64)
            path=q.root/'parallel.jsonl';path.touch(mode=0o600)
            q._append(path,dict(kind='REQUEST'))
            barrier=threading.Barrier(2)
            def write(stage):
                barrier.wait()
                for i in range(15):q._append(path,dict(kind='MODEL_REQUEST',stage=stage,index=i))
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(write,('reviewer-0','reviewer-1')))
            events=q._read(path)
            self.assertEqual(len(events),31)
            self.assertEqual({e['stage'] for e in events[1:]},{'reviewer-0','reviewer-1'})

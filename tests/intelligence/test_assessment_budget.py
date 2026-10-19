"""IDEA083 AB/IR179 red-first regressions: synthetic workers, no provider network."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError, digest
from larp.intelligence.config import load_config
from tests.intelligence import test_openai_pacing as preferred


def candidate(status='ASSESSED', finding='same', identity='primary'):
    return dict(status=status, result_id=identity, reasons=[], findings=[dict(type=finding)],
                event_findings=[], falsifiers=[], claims=[dict(text='immutable primary claim')],
                rationale='immutable primary rationale', confidence=dict(level='HIGH'))


class BudgetContract(unittest.TestCase):
    def test_completed_stage_remains_eligible_while_its_finalizer_is_owned(self):
        from larp.intelligence.models import RuleBaselineModel
        from larp.intelligence.scenarios import build_world,EXSEMI
        from larp.intelligence.time_budget import ACTIVE_DEADLINE
        entered=threading.Event();release=threading.Event();owned=[]
        class Finalizer:
            def set(self,value):return ACTIVE_DEADLINE.set(value)
            def get(self):return ACTIVE_DEADLINE.get()
            def reset(self,token):
                entered.set();release.wait(3);ACTIVE_DEADLINE.reset(token)
        world=build_world(['EXSEMI_Q2_8K','EXSEMI_Q3_8K'])
        assessor=world.assessor(RuleBaselineModel(world.clock))
        req=world.request(['EXSEMI_Q3_8K'],issuer_id=EXSEMI,job_id='finalizer',deadline_ms=300)
        with patch('larp.intelligence.agent.ACTIVE_DEADLINE',Finalizer()):
            task=assessor.start(req,worker_owner=owned.append)
            try:
                self.assertTrue(entered.wait(1))
                task.wait()
                self.assertTrue(owned[0].is_alive())
                self.assertEqual(task.result().read()['status'],'ASSESSED')
            finally:release.set();task.worker.join(2)

    def test_config_supports_180_seconds_but_preserves_six_tools(self):
        for mode in ('development', 'shadow'):
            self.assertEqual(load_config(mode).max_deadline_ms, 180000)
            self.assertEqual(load_config(mode).max_tool_calls, 6)

    def test_one_budget_contract_bounds_stage_shares_and_tool_allocations(self):
        from larp.intelligence.time_budget import stage_limits, reviewer_tools
        for total, primary in ((180000,60000),(120000,40000),(60000,20000),(600,200),(1,0)):
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

    def test_dispatch_tool_allocations_enforce_global_six_calls(self):
        f=self.fx;aiand=f.aiand;openai=f.openai
        def greedy(state):
            return dict(action='CALL_TOOL',tool='prior_context',args=dict(metric='revenue')) if state['remaining_tool_calls'] \
                else dict(action='FINISH',claims=state['claimable'],notes='synthetic tool-budget test')
        def primary(url,headers,raw,timeout):
            status,reply=openai(url,headers,raw,timeout);body=json.loads(raw);payload=json.loads(reply)
            payload['output'][0]['content'][0]['text']=json.dumps(greedy(json.loads(body['input'].split('\n',1)[1])))
            return status,json.dumps(payload).encode()
        def reviewer(url,headers,raw,timeout):
            status,reply,metadata=aiand(url,headers,raw,timeout);body=json.loads(raw);payload=json.loads(reply)
            payload['choices'][0]['message']['content']=json.dumps(greedy(json.loads(body['messages'][1]['content'])))
            return status,json.dumps(payload).encode(),metadata
        f.openai=primary;f.aiand=reviewer
        _,value=f.run_assessment(f.build())
        records={s['stage']:json.loads(f.w.artifacts.get(s['result_artifact'])) for s in value['routing']['stages']}
        self.assertEqual([records[s]['budget_used']['tool_calls'] for s in
                          ('openai-primary','external-review-0','external-review-1')],[3,2,1])
        self.assertEqual(value['budget_used']['tool_calls'],6)

    def test_request_boundary_accepts_180_seconds_and_refuses_larger_without_dispatch(self):
        from larp.contracts import ContractError
        from larp.runtime.schema import assessment_request
        f=self.fx;router=f.build()
        for total in (60000,180000,180001):
            with self.subTest(total=total):
                req=f.w.request(['EXSEMI_Q3_8K'],issuer_id=preferred.fixtures.EXSEMI,job_id='boundary',deadline_ms=total)
                if total>180000:
                    with self.assertRaises(ContractError):assessment_request(req,req.read()['run_id'],req.read()['policy_profile_hash'],f.w.clock())
                    before=len(f.calls)
                    self.assertEqual(router.assess(req).read()['status'],'REJECTED_REQUEST')
                    self.assertEqual(len(f.calls),before)
                else:
                    assessment_request(req,req.read()['run_id'],req.read()['policy_profile_hash'],f.w.clock())
                    self.assertNotEqual(router.assess(req).read()['status'],'REJECTED_REQUEST')

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

    def test_b11_matrix_both_completion_orders_preserve_artifacts_and_consumer_contract(self):
        from larp.intelligence.routing import review_outcome
        from larp.intelligence.roundlog import model_trace
        from larp.runtime.schema import assessment_result
        f=self.fx;router=f.build()
        _,first=f.run_assessment(router)
        template=json.loads(f.w.artifacts.get(first['routing']['primary_result']['artifact']))
        make=router.make_assessor
        kinds=('confirm','different','abstain','timeout','error')
        for primary_status in ('ASSESSED','ABSTAIN','ERROR','TIMEOUT','NOT_RUN'):
            for a in kinds:
                for b in kinds:
                    outcomes=[]
                    for first_reviewer in (0,1):
                        with self.subTest(primary=primary_status,a=a,b=b,first=first_reviewer):
                            finished=threading.Event();barrier=threading.Barrier(2,timeout=2)
                            def stage_assessor(model):
                                assessor=make(model)
                                def assess(r,start,validated,cancel,io):
                                    label=assessor.request_namespace.rstrip(':')
                                    kind=primary_status if label=='openai-primary' else (a,b)[int(label[-1])]
                                    value=deepcopy(template)
                                    value.update(job_id=r['job_id'],cutoff_ms=r['cutoff_ms'],started_ms=start,completed_ms=f.w.clock())
                                    value['model']=model.identity.record()
                                    value['model_hash']=model.identity.model_hash
                                    value['model_io']=dict(steps=[],tool_calls=[],cot=[],model_called=False,
                                                           requests_started=0,no_model_call_reason='SYNTHETIC_MATRIX')
                                    value['budget_used']=dict(tool_calls=0,model_steps=0,elapsed_ms=0)
                                    value['status']={'confirm':'ASSESSED','different':'ASSESSED','abstain':'ABSTAIN',
                                                     'timeout':'UNAVAILABLE','error':'UNAVAILABLE'}.get(kind,kind)
                                    if value['status'] in ('ERROR','TIMEOUT','NOT_RUN'):value['status']='UNAVAILABLE'
                                    value['reasons']=[] if value['status']=='ASSESSED' else ['SYNTHETIC_'+kind.upper()]
                                    if kind=='different':value['findings']=[];value['event_findings']=[];value['falsifiers']=[]
                                    value.pop('result_id',None)
                                    value['result_id']='res:'+digest('larp.intel.result.v1',value)
                                    if label.startswith('external-review'):
                                        barrier.wait()
                                        if int(label[-1])!=first_reviewer:self.assertTrue(finished.wait(2))
                                        else:finished.set()
                                    return Document.from_dict(value)
                                assessor._assess=assess
                                return assessor
                            router.make_assessor=stage_assessor
                            saved=router.openai
                            if primary_status=='NOT_RUN':router.openai=None
                            req=f.w.request(['EXSEMI_Q3_8K'],issuer_id=preferred.fixtures.EXSEMI,
                                            job_id='matrix',deadline_ms=180000)
                            try:value=router.assess(req).read()
                            finally:router.openai=saved
                            assessment_result(Document.from_dict(value),req,f.w.clock())
                            records={s['stage']:json.loads(f.w.artifacts.get(s['result_artifact']))
                                     for s in value['routing']['stages']}
                            expected,outcome,_=review_outcome(records.get('openai-primary'),
                                [records['external-review-0'],records['external-review-1']])
                            self.assertEqual(value['routing']['review_outcome'],outcome)
                            self.assertEqual(value['status'],expected['status'] if expected else 'UNAVAILABLE')
                            if value['status']=='ASSESSED':
                                selected=value['routing']['selected_result']
                                original=json.loads(f.w.artifacts.get(selected['artifact']))
                                self.assertEqual(selected['result_id'],original['result_id'])
                                self.assertNotEqual(value['result_id'],original['result_id'])
                                for key in ('claims','findings','event_findings','rationale','confidence'):
                                    self.assertEqual(value[key],original[key])
                            else:
                                self.assertFalse(value['claims']);self.assertIsNone(value['proposed_thesis'])
                            self.assertTrue(all(v['model'] for v in value['routing']['reviewers']))
                            self.assertEqual(model_trace(value)['routing'],value['routing'])
                            outcomes.append(Document.from_dict(value).payload)
                    self.assertEqual(outcomes[0],outcomes[1])

    def test_unsigned_cutoff_fences_late_workers_and_late_usage_stays_unknown(self):
        import sqlite3
        from larp.intelligence.roundlog import model_trace
        f=self.fx;original=f.openai;entered=threading.Event();release=threading.Event()
        def blocked(*args):
            entered.set();self.assertTrue(release.wait(4));return original(*args)
        f.openai=blocked;router=f.build()
        self.addCleanup(release.set)
        req=f.w.request(['EXSEMI_Q3_8K'],issuer_id=preferred.fixtures.EXSEMI,job_id='unsigned-late',deadline_ms=300)
        first=router.assess(req).read()
        self.assertTrue(entered.is_set())
        before=len(f.calls)
        self.assertEqual(router.assess(req).read()['status'],'UNAVAILABLE')
        self.assertEqual(len(f.calls),before)
        release.set()
        for worker in router._workers:worker.join(2)
        with sqlite3.connect(f.root/'openai-budget.sqlite') as db:
            charges=db.execute("SELECT state FROM charges WHERE request_id LIKE 'openai-primary:%'").fetchall()
        self.assertTrue(charges)
        self.assertTrue(all(row==('UNKNOWN',) for row in charges))
        self.assertNotEqual(first['routing']['primary_result']['result_id'],first['result_id'])

    def test_absolute_deadline_includes_payload_preparation(self):
        f=self.fx;router=f.build();model=router.external[0]
        keep=model._keep
        def expire(raw):
            ref=keep(raw);f.w.clock.advance(181000);return ref
        with patch.object(model,'_keep',side_effect=expire):
            router.openai=None
            _,value=f.run_assessment(router)
        self.assertFalse(f.calls)
        self.assertEqual(value['status'],'UNAVAILABLE')
        self.assertEqual(len(value['routing']['reviewers']),2)

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
        from larp.intelligence.roundlog import model_trace
        trace=model_trace(value['result'])
        self.assertTrue(trace['late_calls'])
        self.assertIn('Late audit-only reply',trace['cot'])
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

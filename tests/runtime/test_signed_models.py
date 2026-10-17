"""SLM-01: bounded asynchronous models; synthetic providers, no keys or network."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.runtime import gate_a, gate_a_check
from tests.runtime.test_gate_a import assembled, profile
from tests.runtime.test_model_routing_preparation import RAW, PIN


def request():
    return Document.from_dict(dict(schema='AssessmentRequest.v1', run_id='r', job_id='job', issuer_id='issuer',
        policy_profile_hash='a'*64, context_hash='b'*64, cutoff_ms=1000, evidence_refs=[],
        budget=dict(tool_calls=3, deadline_ms=1000)))


class Blocking:
    def __init__(self):
        self.entered, self.release = threading.Event(), threading.Event()
        self.calls, self.audit_hook = 0, None

    def assess(self, req):
        self.calls += 1
        self.audit_hook(dict(kind='MODEL_REQUEST', stage='routine', request={'prompt': 'original evidence'}))
        self.entered.set()
        if not self.release.wait(5):
            raise TimeoutError('synthetic test did not release worker')
        self.audit_hook(dict(kind='MODEL_RESPONSE', stage='routine',
                             response={'reasoning_summary': 'provider summary', 'status': 'OK'}))
        return Document.from_dict(dict(schema='AssessmentResult.v2', run_id='r', job_id='job',
            issuer_id='issuer', policy_profile_hash='a'*64, context_hash='b'*64, cutoff_ms=1000,
            started_ms=1000, completed_ms=1100, expiry_ms=2000, model_hash='c'*64, prompt_hash='d'*64,
            rationale='synthetic assessment', model_io=dict(cot=['provider summary'], model_called=True)))


class DeferredModels(unittest.TestCase):
    def queue(self, assessor, root, **changes):
        from larp.runtime.deferred_models import DeferredAssessments
        return DeferredAssessments(assessor, root=root, run_id='r', build_id='e'*40,
                                   profile_hash='a'*64, **changes)

    def test_slm2_blocked_model_returns_control_and_never_starts_a_second_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            model=Blocking(); self.addCleanup(model.release.set)
            q=self.queue(model,tmp)
            self.assertTrue(q.submit('round',request()))
            self.assertTrue(model.entered.wait(1))
            self.assertIsNone(q.ready())
            self.assertFalse(q.submit('other',request()))
            self.assertEqual(model.calls,1)
            self.assertEqual(q.round_ids(),{'round'})
            model.release.set(); self.assertTrue(q.finished.wait(1))
            ready=q.ready()
            self.assertEqual(ready['request'],request().read())
            self.assertEqual(ready['result']['model_io']['cot'],['provider summary'])
            self.assertEqual([e['kind'] for e in ready['audit']['events']],
                             ['REQUEST','MODEL_REQUEST','MODEL_RESPONSE','RESULT'])
            q.ack('round'); self.assertIsNone(q.ready()); self.assertFalse(q.busy)

    def test_slm5_restart_retains_original_result_and_does_not_call_model_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            model=Blocking();model.release.set();q=self.queue(model,tmp)
            q.submit('round',request());self.assertTrue(q.finished.wait(1))
            restarted=self.queue(model,tmp)
            ready=restarted.ready()
            self.assertEqual(ready['result']['job_id'],'job')
            self.assertEqual(ready['audit']['events'][2]['response']['reasoning_summary'],'provider summary')
            self.assertEqual(model.calls,1)
            restarted.ack('round')
            self.assertIsNone(self.queue(model,tmp).ready())

    def test_slm5_interrupted_chain_preserves_completed_io_without_inventing_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            model=Blocking();self.addCleanup(model.release.set);q=self.queue(model,tmp)
            q.submit('round',request());self.assertTrue(model.entered.wait(1))
            restarted=self.queue(model,tmp)
            ready=restarted.ready()
            self.assertIsNone(ready['result'])
            self.assertEqual(ready['audit']['state'],'INTERRUPTED')
            self.assertEqual(ready['audit']['events'][1]['stage'],'routine')
            self.assertFalse(restarted.submit('other',request()))
            model.release.set();self.assertTrue(q.finished.wait(1))

    def test_slm3_other_run_profile_and_changed_trace_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            model=Blocking();model.release.set();q=self.queue(model,tmp)
            bad=request().read();bad['run_id']='other'
            with self.assertRaises(ContractError):q.submit('round',Document.from_dict(bad))
            q.submit('round',request());self.assertTrue(q.finished.wait(1))
            path=next(Path(tmp).rglob('*.jsonl'));path.write_bytes(path.read_bytes().replace(b'original evidence',b'changed evidence'))
            with self.assertRaises(ContractError):self.queue(model,tmp)


class SignedPreparation(unittest.TestCase):
    def prepared(self, **changes):
        return assembled(**dict(model_routing_raw=RAW, model_routing_sha256=PIN,
            execution='service', adoption_ref='SLM synthetic reviewed decision', **changes))

    def test_slm7_signed_rehearsal_pins_scope_without_constructing_models(self):
        with patch('socket.create_connection',side_effect=AssertionError('no network')):
            files=self.prepared()
        c=json.loads(files['runtime.json']);report=json.loads(files['preparation-report.json'])
        self.assertEqual((c['mode'],c['driver']['execution'],c['driver']['intelligence_mode']),('dev','service','live'))
        self.assertEqual(c['driver']['model_adoption_ref'],'SLM synthetic reviewed decision')
        self.assertEqual(files['model-routing.json'],RAW)
        self.assertFalse(report['signing_enabled'])
        self.assertEqual(report['execution'],'service')
        values={n:json.loads(raw) for n,raw in files.items() if n.endswith('.json')}
        gate_a_check.check_scope(values,report)
        for mutate in (lambda v:v['runtime.json']['driver'].pop('model_adoption_ref'),
                       lambda v:v['runtime.json']['driver'].update(intelligence_mode='shadow'),
                       lambda v:v['initial-state.json'].update(mode='live')):
            changed=deepcopy(values);mutate(changed)
            with self.assertRaises(ContractError):gate_a_check.check_scope(changed,report)

    def test_slm1_signed_preparation_requires_explicit_review_and_routing(self):
        with self.assertRaises(ContractError):assembled(execution='service')
        for ref in (None,'', '  '):
            with self.subTest(ref=ref),self.assertRaises(ContractError):
                assembled(model_routing_raw=RAW,model_routing_sha256=PIN,execution='service',adoption_ref=ref)

    def test_slm7_final_scope_requires_final_profile_and_preserves_shadow_default(self):
        with self.assertRaises(ContractError):self.prepared(runtime_mode='live')
        from larp.strategy.profiles import build_live_profiles
        p=build_live_profiles(Document.from_dict(profile()['quote_cost_summary']),
            Document.from_dict(json.loads((gate_a.ROOT/'config/intelligence/red_flags.v1.json').read_bytes())))['FINAL']
        files=self.prepared(runtime_mode='live',profile_raw=p.payload)
        values={n:json.loads(raw) for n,raw in files.items() if n.endswith('.json')}
        report=json.loads(files['preparation-report.json'])
        self.assertEqual(values['initial-state.json']['mode'],'live')
        self.assertEqual(values['uploader.json']['mode'],'live')
        gate_a_check.check_scope(values,report)
        original=assembled();c=json.loads(original['runtime.json'])
        self.assertEqual((c['mode'],c['driver']['execution'],c['driver']['assessor']),('dev','shadow','deterministic'))


class OutageLimiter(unittest.TestCase):
    def test_slm4_pending_or_failed_assessment_cannot_expire_an_accepted_cut(self):
        from larp.strategy.policy import decide
        from tests.strategy.test_s1_plan import snap, settled, NAMES, AT_60
        state=settled([3,5])
        state['s1']['limiter']=dict(level='CAUTION', expires_session=83, used_evidence_ids=['accepted-cut'],
                                    healthy_sessions=0, counted_session=80)
        for session in range(81,90):
            snapshot=snap({n:AT_60 for n in NAMES},state=state,session_index=session,
                          exposure_evidence=[],assessment_available=False)
            state=decide(snapshot,snapshot.policy_state).next_policy_state.data.read()
            self.assertEqual(state['s1']['limiter']['level'],'CAUTION')
            self.assertEqual(state['s1']['limiter']['healthy_sessions'],0)


from tests.runtime.test_round_driver_service import ServiceHarness


class SignedIntegration(ServiceHarness):
    def queue(self, driver, model):
        from larp.runtime.deferred_models import DeferredAssessments
        q=DeferredAssessments(model,root=Path(self.tmp.name)/'deferred',run_id=driver.coordinator.run_id,
            build_id=driver.coordinator.version_id,profile_hash=driver.coordinator.profile_hash)
        driver.assessments=q
        return q

    def seed_pending(self, driver, model):
        from larp.contracts import Document
        c=driver.coordinator
        item=driver.work.next(self.w.clock(),self.epoch)
        req=driver.work.request(item,self.store.load(c.run_id).read(),self.w.clock())
        self.store.open_round(c.run_id,item['round_id'],req,self.epoch)
        q=self.queue(driver,model)
        q.submit(item['round_id'],req)
        return q,item,req

    def test_slm2_real_mandatory_planner_and_halt_continue_while_model_is_blocked(self):
        from tests.integration.test_evidence_pipeline import evidence_state, RUN
        from larp.runtime.coordinator import batch_for
        from larp.runtime.supervision import Guard
        driver=self.service_driver(cadence=True)
        model=Blocking();self.addCleanup(model.release.set)
        q,item,req=self.seed_pending(driver,model)
        self.assertTrue(model.entered.wait(1))
        _,state,_=evidence_state(['EXSEMI_402_8K'],self.profile,world=self.w)
        current=self.store.load(RUN);projection=current.read()['projection']
        projection['evidence']={req.read()['issuer_id']:state}
        self.store.commit(batch_for(current,'seed-accepted',dict(kind='TEST_ACCEPTED_EVIDENCE'),projection=projection))
        summary=driver.once(self.w.clock())
        self.assertTrue(self.commands())
        planned=self.planned()
        self.assertTrue(any(i['mandatory'] and i['side']=='SELL' for r in planned.values() for i in r['plan']['intents']))
        self.assertFalse(q.finished.is_set())
        Guard(self.store,RUN,max_failures=3,clear_after=2)._halt('CLOCK',self.w.clock(),{})
        with patch.object(driver.execution,'settle_open',wraps=driver.execution.settle_open) as settle:
            driver.once(self.w.clock())
            self.assertTrue(settle.called)
        self.assertIn('CLOCK',self.store.load(RUN).read()['projection']['halt']['reasons'])
        model.release.set();self.assertTrue(q.finished.wait(1))

    def test_slm3_valid_result_uses_existing_evidence_acceptance_and_original_context(self):
        from larp.intelligence.models import RuleBaselineModel
        driver=self.service_driver()
        model=self.w.assessor(RuleBaselineModel(self.w.clock))
        q,item,req=self.seed_pending(driver,model)
        self.assertTrue(q.finished.wait(2))
        summary=driver.once(self.w.clock())
        record=self.store.event(driver.coordinator.run_id,'plan:'+item['round_id'])['record']
        self.assertEqual(record['request'],req.read())
        self.assertTrue(any(d['decision']=='ACCEPT' for d in record['evidence_decisions']))
        self.assertIsNotNone(record['assessment'])
        self.assertFalse(q.busy)
        self.assertTrue(self.commands())  # real I3 commands from verified evidence, fake external boundaries

    def test_slm3_expired_result_grants_no_evidence_but_preserves_its_io_in_round_log(self):
        from larp.intelligence.models import RuleBaselineModel
        from larp.contracts import Document
        from larp.runtime.coordinator import batch_for
        driver=self.service_driver()
        delegate=self.w.assessor(RuleBaselineModel(self.w.clock))
        class Expired:
            def assess(inner,request):
                result=delegate.assess(request).read()
                result['expiry_ms']=self.w.clock()
                result['model_io']['cot']=['original provider summary']
                if inner.audit_hook:
                    inner.audit_hook(dict(kind='MODEL_RESPONSE',stage='routine',
                        response=dict(reasoning_summary='original provider summary')))
                return Document.from_dict(result)
        q,item,req=self.seed_pending(driver,Expired())
        self.assertTrue(q.finished.wait(2))
        driver.once(self.w.clock())
        log=self.logs()[item['round_id']]
        self.assertIsNone(log['input']['assessment'])
        self.assertEqual(log['input']['assessment_audit']['events'][-1]['result']['model_io']['cot'],
                         ['original provider summary'])
        self.assertEqual(log['cot'],['original provider summary'])
        self.assertEqual(log['orders'],[])

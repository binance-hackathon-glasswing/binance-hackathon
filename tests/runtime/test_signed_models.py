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

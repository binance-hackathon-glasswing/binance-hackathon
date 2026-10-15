"""IDEA-057 prospective component acceptance. Synthetic HTTP only; no keys or network.

AR1 fixed wire/metadata/provenance; AR2 exact identity/effort and refusals; AR3 durable
atomic admission/unknown usage; AR4 external-first and credit fallback; AR5 shared
deadline/tools and failed review; AR6 trace/consumer identities; AR7 runtime wiring.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest

from larp.contracts import Document
from larp.intelligence.aiand import AIandChatModel, ENDPOINT
from larp.intelligence.common import IntelligenceError
from larp.intelligence.model_budget import ModelBudget
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.routing import build_routed_assessor, _review_reasons
from larp.intelligence.roundlog import model_trace
from larp.intelligence.scenarios import build_world, EXSEMI
from larp.intelligence.gate import initial_state, accept
from larp.runtime.schema import assessment_result
from tests.intelligence.test_providers import request

ROOT = Path(__file__).resolve().parents[2]
AIAND_KEY, OPENAI_KEY = 'synthetic-aiand-key-only-001', 'synthetic-openai-key-only-001'
FINISH = dict(action='FINISH', claims=[], notes='synthetic result')


def spec():
    return json.loads((ROOT/'config/intelligence/aiand-routing.example.json').read_text())


def decide(state):
    if state['gaps'] and state['remaining_tool_calls']:
        gap = state['gaps'][0]
        return dict(action='CALL_TOOL', tool=gap['tool'], args=gap['args'])
    return dict(action='FINISH', claims=state['claimable'], notes='synthetic claims')


def chat_reply(body, output=FINISH):
    return dict(model=body['model'], choices=[dict(finish_reason='stop', message=dict(
        role='assistant', content=json.dumps(output), reasoning_content='Synthetic reasoning.',
        reasoning='Synthetic reasoning.'))], usage=dict(prompt_tokens=100, completion_tokens=20))


class AIandWire(unittest.TestCase):
    def setUp(self):
        self.w = build_world(['EXSEMI_Q2_8K'])
        self.sent = []

    def build(self, mutate=lambda p,h: None, *, status=200, change=None):
        setting = spec()['routine']
        def send(url, headers, raw, timeout):
            body = json.loads(raw)
            self.sent.append((url, headers, body, raw, timeout))
            payload = chat_reply(body)
            meta = {'x-model': body['model'], 'x-reasoning-effort': body['reasoning_effort'],
                    'x-request-id': 'synthetic-request', 'set-cookie': 'never capture'}
            mutate(payload, meta)
            return status, json.dumps(payload).encode(), meta
        args = dict(model_id=setting['model_id'], effort=setting['effort'], catalog=setting['catalog'],
                    api_key=AIAND_KEY, prompt_text=self.w.config.prompt_text,
                    prompt_sha256=self.w.config.prompt_sha256, clock_ms=self.w.clock,
                    artifacts=self.w.artifacts, transport=send, max_output_tokens=4096)
        args.update(change or {})
        return AIandChatModel(**args)

    def test_ar1_fixed_endpoint_bearer_json_reasoning_and_exact_artifacts(self):
        model = self.build()
        result = model.step(request(), 5000).read()
        url, headers, body, raw, timeout = self.sent[0]
        self.assertEqual(url, ENDPOINT)
        self.assertEqual(headers['Authorization'], 'Bearer '+AIAND_KEY)
        self.assertEqual((body['reasoning_effort'],body['max_completion_tokens'],body['stream']), ('low',4096,False))
        self.assertEqual(body['response_format'], {'type':'json_object'})
        self.assertEqual((result['status'],result['output'],result['reasoning_summary']), ('OK',FINISH,'Synthetic reasoning.'))
        self.assertEqual(result['usage'],dict(input_tokens=100,output_tokens=20))
        self.assertEqual(self.w.artifacts.get(result['request_payload_artifact']),raw)
        self.assertNotIn('set-cookie',result['provider_metadata'])
        self.assertTrue(result['raw_response_artifact'])
        self.assertNotIn(AIAND_KEY,repr(model))
        self.assertTrue(all(AIAND_KEY.encode() not in b for b in self.w.artifacts.blobs.values()))

    def test_ar2_header_and_body_identity_effort_length_refusal_usage_and_json(self):
        cases = [
            lambda p,h: h.update({'x-model':'zai-org/glm-5.3-flash'}),
            lambda p,h: h.update({'x-reasoning-effort':'high'}),
            lambda p,h: h.pop('x-reasoning-effort'),
            lambda p,h: p.update(model='another/model'),
            lambda p,h: p['choices'][0].update(finish_reason='length'),
            lambda p,h: p['choices'][0]['message'].update(refusal='no'),
            lambda p,h: p['choices'][0]['message'].update(content='not json'),
            lambda p,h: p['choices'][0]['message'].update(reasoning='different'),
            lambda p,h: p['usage'].update(prompt_tokens=-1),
            lambda p,h: p['choices'].append(deepcopy(p['choices'][0])),
        ]
        for mutate in cases:
            with self.subTest(mutate=mutate):
                result=self.build(mutate).step(request(),5000).read()
                self.assertEqual(result['status'],'ERROR')
                self.assertIsNone(result['output'])
                self.assertIsNotNone(result['raw_response_artifact'])

    def test_ar2_case_insensitive_catalog_identity_but_no_other_model(self):
        value=self.build(lambda p,h:(p.update(model=p['model'].upper()),h.update({'x-model':h['x-model'].upper()}))).step(request(),5000).read()
        self.assertEqual(value['status'],'OK')

    def test_ar2_refuse_alias_endpoint_unsupported_effort_or_bad_catalog_before_transport(self):
        for change in [dict(model_id='auto'), dict(endpoint='https://evil.test/v1/chat/completions'),
                       dict(effort='none'),dict(effort='medium'),dict(catalog={})]:
            with self.subTest(change=change), self.assertRaises(IntelligenceError): self.build(change=change)
        self.assertFalse(self.sent)

    def test_ar2_credential_reflection_body_or_header_is_not_captured(self):
        for mutate in [lambda p,h:p['choices'][0]['message'].update(content=AIAND_KEY),
                       lambda p,h:h.update({'x-request-id':AIAND_KEY})]:
            before=set(self.w.artifacts.blobs)
            value=self.build(mutate).step(request(),5000).read()
            self.assertEqual(value['error'],'CREDENTIAL_REFLECTION')
            for ref in set(self.w.artifacts.blobs)-before:
                self.assertNotIn(AIAND_KEY.encode(),self.w.artifacts.get(ref))


class BudgetAdmission(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'openai-budget.sqlite'

    def init(self, **kw):
        return ModelBudget.initialize(self.path,'test-account',initial_spent=kw.pop('initial_spent',0),**kw)

    def test_ar3_explicit_initialization_prior_usage_and_no_reset(self):
        with self.assertRaises(IntelligenceError): ModelBudget(self.path,'test-account')
        self.assertFalse(self.path.exists())
        self.init(initial_spent=5_000_000)
        again=ModelBudget(self.path,'test-account')
        self.assertEqual(again.snapshot()['available_micro_usd'],35_000_000)
        with self.assertRaises(FileExistsError): self.init()
        with self.assertRaises(IntelligenceError): ModelBudget(self.path,'different-account')
        self.path.unlink()
        with self.assertRaises(IntelligenceError): again.snapshot()
        self.assertFalse(self.path.exists())

    def test_ar3_atomic_cross_worker_reservations_and_latched_switch(self):
        b=self.init()
        with ThreadPoolExecutor(max_workers=4) as pool:
            tokens=list(pool.map(lambda n:ModelBudget(self.path,'test-account').admit(25_000_000,str(n)),range(4)))
        self.assertEqual(sum(t is not None for t in tokens),1)
        self.assertTrue(b.snapshot()['external_only'])
        b.settle(next(t for t in tokens if t),100)
        self.assertIsNone(b.admit(1,'new-run-new-wallet'))
        self.assertEqual(b.snapshot()['charged_micro_usd'],100)

    def test_ar3_unknown_usage_and_settlement_persist(self):
        b=self.init(); token=b.admit(1000,'one'); b.settle(token,None)
        self.assertEqual(ModelBudget(self.path,'test-account').snapshot()['charged_micro_usd'],1000)
        with self.assertRaises(IntelligenceError): b.settle(token,0)


class Routing(unittest.TestCase):
    def setUp(self):
        self.w=build_world(['EXSEMI_Q2_8K','EXSEMI_Q3_8K'])
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.s=spec(); self.calls=[]; self.openai_error=None; self.fail_external=False; self.delay=1
        ModelBudget.initialize(self.root/'openai-budget.sqlite',self.s['budget_account'],initial_spent=0)

    def aiand(self,url,headers,raw,timeout):
        body=json.loads(raw); self.calls.append(('aiand',body['model'],body['reasoning_effort'],timeout))
        self.w.clock.advance(self.delay)
        if self.fail_external: return 402,b'{"error":{"code":"insufficient_credits"}}',{}
        state=json.loads(body['messages'][1]['content'])
        return 200,json.dumps(chat_reply(body,decide(state))).encode(),{
            'x-model':body['model'],'x-reasoning-effort':body['reasoning_effort']}

    def openai(self,url,headers,raw,timeout):
        body=json.loads(raw); self.calls.append(('openai',body['model'],'medium',timeout))
        self.w.clock.advance(self.delay)
        if self.openai_error:
            return 429,json.dumps({'error':dict(code=self.openai_error,type=self.openai_error)}).encode()
        output=decide(json.loads(body['input']))
        return 200,json.dumps(dict(model=body['model'],status='completed',output=[dict(type='message',content=[
            dict(type='output_text',text=json.dumps(output))])],usage=dict(input_tokens=100,output_tokens=20))).encode()

    def build(self, *, key=True):
        secrets={'LARP_AIAND_API_KEY':AIAND_KEY}
        if key: secrets['LARP_MODEL_API_KEY']=OPENAI_KEY
        return build_routed_assessor(self.s,registry=self.w.registry,reader=self.w.reader,config=self.w.config,
            clock_ms=self.w.clock,artifacts=self.w.artifacts,secrets=secrets,budget_root=self.root,
            transports={'aiand':self.aiand,'openai':self.openai})

    def run_assessment(self, router, **kw):
        r=self.w.request(['EXSEMI_Q3_8K'],issuer_id=EXSEMI,job_id='routing',**kw)
        result=router.assess(r)
        assessment_result(result,r,self.w.clock())
        return r,result.read()

    def test_ar4_external_first_then_sol_and_full_consumer_trace(self):
        router=self.build(); r,value=self.run_assessment(router)
        self.assertEqual(self.calls[0][:3],('aiand','zai-org/glm-5.3','low'))
        self.assertTrue(any(c[0]=='openai' for c in self.calls))
        self.assertLessEqual(value['budget_used']['tool_calls'],6)
        self.assertLessEqual(value['model_io']['requests_started'],10)
        self.assertLessEqual(value['budget_used']['elapsed_ms'],60000)
        self.assertEqual(value['model_hash'],router.model.identity.model_hash)
        self.assertTrue(all(self.w.artifacts.get(s['result_artifact']) for s in value['routing']['stages']))
        trace=model_trace(value)
        self.assertEqual(len({c['request_id'] for c in trace['calls']}),len(trace['calls']))
        self.assertTrue(any(c['model']['provider']=='aiand' for c in trace['calls']))
        self.assertTrue(any(c['model']['provider']=='openai' for c in trace['calls']))
        state=initial_state(EXSEMI,r.read()['policy_profile_hash'])
        decision,_=accept(state,Document.from_dict(value),profile_hash=r.read()['policy_profile_hash'],now_ms=self.w.clock())
        self.assertEqual(decision,'ACCEPT')
        for key in (AIAND_KEY,OPENAI_KEY): self.assertNotIn(key,json.dumps(value))

    def test_ar4_budget_limit_routes_difficult_work_externally_and_survives_restart(self):
        b=ModelBudget(self.root/'openai-budget.sqlite',self.s['budget_account']); b.admit(40_000_000,'prior-run')
        router=self.build(); _,value=self.run_assessment(router)
        self.assertFalse(any(c[0]=='openai' for c in self.calls))
        self.assertTrue(any(c[:3]==('aiand','moonshotai/kimi-k3','high') for c in self.calls))
        self.assertTrue(value['routing']['budget']['external_only'])
        self.calls.clear(); self.run_assessment(self.build())
        self.assertFalse(any(c[0]=='openai' for c in self.calls))

    def test_ar4_credit_refusal_falls_back_but_rate_limit_does_not_latch(self):
        self.openai_error='rate_limit_exceeded'; _,value=self.run_assessment(self.build())
        self.assertTrue(any(c[0]=='openai' for c in self.calls))
        self.assertFalse(value['routing']['budget']['external_only'])
        self.calls.clear(); self.openai_error='insufficient_quota'
        _,value=self.run_assessment(self.build())
        self.assertTrue(value['routing']['budget']['external_only'])
        self.assertEqual(value['routing']['budget']['reason'],'OPENAI_CREDIT_EXHAUSTED')
        self.assertTrue(any(c[0]=='aiand' and c[2]=='high' for c in self.calls))

    def test_ar4_current_prepaid_credit_error_code_also_latches(self):
        self.openai_error='credit_balance_exhausted'
        _,value=self.run_assessment(self.build())
        self.assertTrue(value['routing']['budget']['external_only'])
        self.assertEqual(value['routing']['budget']['reason'],'OPENAI_CREDIT_EXHAUSTED')

    def test_ar4_missing_openai_key_uses_external_hard_review_and_stable_identity(self):
        router=self.build(key=False)
        self.assertEqual(router.model.identity,self.build(key=True).model.identity)
        self.run_assessment(router)
        self.assertFalse(any(c[0]=='openai' for c in self.calls))
        self.assertTrue(any(c[0]=='aiand' and c[2]=='high' for c in self.calls))

    def test_ar5_all_external_failure_cannot_clear_or_propose_thesis(self):
        self.fail_external=True
        _,value=self.run_assessment(self.build(key=False))
        self.assertEqual(value['status'],'UNAVAILABLE')
        self.assertFalse(value['claims'] or value['findings'] or value['event_findings'])
        self.assertIsNone(value['proposed_thesis'])
        self.assertLessEqual(len(self.calls),3)

    def test_ar5_shared_deadline_no_fresh_minute_for_review(self):
        self.delay=400
        _,value=self.run_assessment(self.build(key=False),deadline_ms=500)
        self.assertNotEqual(value['status'],'ASSESSED')
        self.assertTrue(all(c[3]<=.5 for c in self.calls))
        self.assertLessEqual(value['model_io']['requests_started'],2)

    def test_ar6_invalid_requests_do_not_dispatch(self):
        r=self.w.request(['EXSEMI_Q3_8K'],issuer_id=EXSEMI,job_id='bad',tool_calls=99)
        value=self.build().assess(r).read()
        self.assertEqual(value['status'],'REJECTED_REQUEST'); self.assertFalse(self.calls)

    def test_ar6_router_uses_independent_items_coverage_and_seeded_clean_audits(self):
        clean=dict(status='ASSESSED',coverage=dict(complete=True),missingness=[],conflicts=[])
        r=dict(issuer_id='fictional',evidence_refs=[],cutoff_ms=1)
        self.assertEqual(_review_reasons(clean,r,0,'fixed'),[])
        self.assertIn('SEEDED_CLEAN_CASE_AUDIT',_review_reasons(clean,r,10000,'fixed'))
        self.assertIn('INDEPENDENT_ITEM_CANDIDATE',_review_reasons(dict(clean,red_flag_checks=[{}]),r,0,'fixed'))

    def test_ar6_review_job_scope_is_preserved(self):
        r=self.w.request(['EXSEMI_Q3_8K'],issuer_id=EXSEMI,job_id='review-job')
        raw=r.read(); raw['review']=dict(job_id='review-job',statement_ids=['statement:synthetic'])
        value=self.build(key=False).assess(Document.from_dict(raw)).read()
        self.assertEqual(value['review_scope'],raw['review'])
        self.assertEqual(value['job_id'],'review-job')

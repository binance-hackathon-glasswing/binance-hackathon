"""PC-AUDIT01 portable regressions. Synthetic transports only; never paid inference."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from larp.contracts import Document
from larp.intelligence import bakeoff
from larp.intelligence.scenarios import EXSEMI, build_world
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.common import IntelligenceError, sha256_hex
from tests.intelligence import test_aiand_routing, test_roundlog, test_openai_pacing


def assert_wire(test, world, result):
    for step in result['model_io']['steps']:
        if 'response' not in step:
            continue
        wire = json.loads(world.artifacts.get(step['response']['request_payload_artifact']))
        sent = json.loads(wire['input'].split('\n', 1)[1]) if 'input' in wire else json.loads(wire['messages'][-1]['content'])
        test.assertEqual(step['request']['input'], sent)


def v4(spec):
    value = deepcopy(spec)
    value['schema'] = 'AIandRouting.v4'
    value['openai_max_output_tokens'] = value.pop('max_output_tokens')
    value['routine']['max_output_tokens'] = 4096
    prompt = test_aiand_routing.ROOT/'config/intelligence/prompts/routing/review.v2.md'
    for entry in value['external_reviewers']:
        entry['max_output_tokens'] = 16000
        entry['prompt'] = dict(name=prompt.name, sha256=sha256_hex(prompt.read_bytes()))
    return value


class DispatchSnapshot(unittest.TestCase):
    def test_earlier_normalized_requests_equal_exact_http_inputs_after_multiple_tools(self):
        w = build_world(['EXSEMI_Q2_8K', 'EXSEMI_Q3_8K'])
        helper = test_roundlog.ModelTraces(); helper.w = w
        def decide(state):
            if state['gaps'] and state['remaining_tool_calls']:
                gap = state['gaps'][0]
                return dict(action='CALL_TOOL', tool=gap['tool'], args=gap['args'])
            return dict(action='FINISH', claims=state['claimable'], notes='synthetic')
        result = w.assessor(helper.hosted(decide)).assess(
            w.request(['EXSEMI_Q3_8K'], issuer_id=EXSEMI, job_id='snapshot')).read()
        steps = result['model_io']['steps']
        self.assertGreaterEqual(len(steps), 3)
        for step in steps:
            wire = json.loads(w.artifacts.get(step['response']['request_payload_artifact']))
            sent = json.loads(wire['messages'][-1]['content'])
            self.assertEqual(step['request']['input'], sent)

    def test_nested_values_tool_error_and_provider_error_cannot_mutate_sent_requests(self):
        from larp.intelligence.agent import _State, EvidenceAssessor
        original_view, original_tool = _State._view, EvidenceAssessor._call_tool
        for outcome in ('normal', 'tool_error', 'provider_error', 'truncated'):
            w = build_world(['EXSEMI_Q2_8K', 'EXSEMI_Q3_8K'])
            helper = test_roundlog.ModelTraces(); helper.w = w
            calls = []
            def view(state, *args):
                if not state.tool_results:
                    state.tool_results.append(dict(nested=dict(values=['initial'])))
                result = original_view(state, *args)
                if outcome == 'truncated':
                    result['tool_results'].append(dict(padding='x'*100000))
                return result
            def tool(assessor, state, *args):
                state.tool_results[0]['nested']['values'].append(dict(changed=True))
                return original_tool(assessor, state, *args)
            def decide(state):
                calls.append(deepcopy(state))
                if outcome == 'provider_error' and len(calls) > 1:
                    raise OSError('synthetic adapter failure')
                if len(calls) == 1 and outcome == 'tool_error':
                    return dict(action='CALL_TOOL', tool='fetch_document', args=dict(accession='absent', name='absent'))
                if state['gaps'] and state['remaining_tool_calls'] and len(calls) < 4:
                    gap=state['gaps'][0]
                    return dict(action='CALL_TOOL', tool=gap['tool'], args=gap['args'])
                return dict(action='FINISH', claims=state['claimable'])
            with self.subTest(outcome=outcome), patch.object(_State, '_view', view), patch.object(EvidenceAssessor, '_call_tool', tool):
                result = w.assessor(helper.hosted(decide)).assess(
                    w.request(['EXSEMI_Q3_8K'], issuer_id=EXSEMI, job_id=outcome)).read()
                assert_wire(self, w, result)
                if outcome == 'provider_error':
                    self.assertEqual(result['status'], 'UNAVAILABLE')
                    self.assertIn('request', result['model_io']['steps'][-1])
                if outcome == 'truncated':
                    self.assertTrue(result['coverage']['model_input_truncated'])
                    for step in result['model_io']['steps']:
                        self.assertLessEqual(len(Document.from_dict(step['request']['input']).payload),
                                             w.config.limits['max_model_input_chars'])
                if outcome == 'tool_error':
                    self.assertEqual(result['model_io']['tool_calls'][0]['status'], 'ERROR')

    def test_abandoned_inflight_hash_equals_original_transport_bytes(self):
        from larp.intelligence.providers import AnthropicMessagesModel
        from tests.intelligence.test_providers import SECRET, anthropic_reply
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        w = build_world(['EXSEMI_Q2_8K', 'EXSEMI_Q3_8K']); sent = []
        def send(url, headers, raw, timeout):
            body=json.loads(raw); state=json.loads(body['messages'][0]['content'])
            sent.append(raw)
            if len(sent) == 1:
                gap=state['gaps'][0]
                output=dict(action='CALL_TOOL', tool=gap['tool'], args=gap['args'])
            else:
                entered.set(); release.wait(3)
                output=dict(action='FINISH', claims=[])
            return 200, json.dumps(anthropic_reply(output)(body)).encode()
        model=AnthropicMessagesModel(model_id='synthetic-model', api_key=SECRET, prompt_text=w.config.prompt_text,
            prompt_sha256=w.config.prompt_sha256, clock_ms=w.clock, artifacts=w.artifacts, transport=send)
        task=w.assessor(model).start(w.request(['EXSEMI_Q3_8K'], issuer_id=EXSEMI, job_id='inflight', deadline_ms=100))
        try:
            self.assertTrue(entered.wait(1))
            task.wait(); result=task.result().read()
            self.assertEqual(result['status'], 'UNAVAILABLE')
            assert_wire(self, w, result)
            self.assertEqual(result['model_io']['in_flight']['request_payload_sha256'], sha256_hex(sent[-1]))
            frozen=Document.from_dict(result).payload
        finally:
            release.set(); task.worker.join(2)
        self.assertEqual(Document.from_dict(result).payload, frozen)

    def test_parallel_deferred_hooks_and_final_records_equal_actual_wire(self):
        fx=test_openai_pacing.Preferred(); fx.setUp(); self.addCleanup(fx.doCleanups)
        f=fx.fx; router=f.build(); events=[]
        request=f.w.request(['EXSEMI_Q3_8K'], issuer_id=EXSEMI, job_id='deferred-snapshots')
        result=router.assess_deferred(request, audit_hook=lambda event: events.append(deepcopy(event))).read()
        requests={e['request']['request_id']: e['request'] for e in events if e['kind']=='MODEL_REQUEST'}
        assert_wire(self, f.w, result)
        self.assertGreaterEqual(len(result['routing']['stages']), 3)
        for step in result['model_io']['steps']:
            self.assertEqual(step['request'], requests[step['request']['request_id']])


class RejectedUsage(unittest.TestCase):
    def test_length_reply_retains_usage_and_specific_cause_without_output(self):
        helper = test_aiand_routing.AIandWire(); helper.setUp()
        def truncate(payload, headers):
            payload['choices'][0].update(finish_reason='length')
            payload['usage'].update(completion_tokens=4096,
                                    completion_tokens_details={'reasoning_tokens': 4096})
        from tests.intelligence.test_providers import request
        result = helper.build(truncate).step(request(), 5000).read()
        self.assertEqual(result['status'], 'ERROR')
        self.assertIsNone(result['output'])
        self.assertEqual(result['error'], 'AIAND_TOKEN_LIMIT')
        self.assertEqual(result['usage'], dict(input_tokens=100, output_tokens=4096))
        self.assertEqual(result['finish_reason'], 'length')
        self.assertEqual(result['usage_details']['reasoning_tokens'], 4096)

    def test_eleven_truncated_synthetic_replies_remain_unusable_and_reconcile_45056_tokens(self):
        from tests.intelligence.test_providers import request
        helper=test_aiand_routing.AIandWire(); helper.setUp()
        replies=[]
        for n in range(11):
            def mutate(p, h):
                p['choices'][0].update(finish_reason='length')
                p['usage']['completion_tokens']=4096
                p['choices'][0]['message']['content']='{"action":"FINISH","claims":'
            replies.append(helper.build(mutate).step(request(), 5000).read())
        self.assertTrue(all(r['status']=='ERROR' and r['output'] is None for r in replies))
        self.assertEqual(sum(r['usage']['output_tokens'] for r in replies), 45056)

    def test_malformed_output_provider_error_late_reply_and_unknown_usage(self):
        from tests.intelligence.test_providers import request
        helper=test_aiand_routing.AIandWire(); helper.setUp()
        cases=[('bad_json', lambda p,h:p['choices'][0]['message'].update(content='bad'), True),
               ('provider', lambda p,h:p.update(error=dict(code='synthetic')), True),
               ('multiple', lambda p,h:p['choices'].append(deepcopy(p['choices'][0])), True),
               ('bad_usage', lambda p,h:p['usage'].update(completion_tokens=True), False),
               ('no_usage', lambda p,h:p.pop('usage'), False)]
        for name, mutate, known in cases:
            with self.subTest(name=name):
                reply=helper.build(mutate).step(request(),5000).read()
                self.assertEqual(reply['status'],'ERROR')
                self.assertEqual(reply['usage_known'], known)
                self.assertIsNone(reply['output'])
                if known:self.assertEqual(reply['usage']['output_tokens'],20)
                else:self.assertIsNone(reply['usage']['output_tokens'])
        model=helper.build()
        transport=model._transport
        def late(*args):
            value=transport(*args); helper.w.clock.advance(6000); return value
        model._transport=late
        reply=model.step(request(),5000).read()
        self.assertEqual(reply['status'],'TIMEOUT')
        self.assertEqual(reply['usage']['output_tokens'],20)


class StageCaps(unittest.TestCase):
    def test_candidate_and_legacy_specs_preserve_exact_caps_on_wire(self):
        from larp.intelligence.routing import validate_routing_spec
        from larp.runtime.gate_a import model_routing_report
        candidate=json.loads((test_aiand_routing.ROOT/'config/intelligence/aiand-routing.repair.example.json').read_bytes())
        validate_routing_spec(candidate)
        self.assertEqual(model_routing_report(candidate, '0'*64)['completion_limits']['external_reviewers'], [16000,16000])
        for repaired in (False, True):
            fx=test_openai_pacing.Preferred(); fx.setUp(); self.addCleanup(fx.doCleanups)
            f=fx.fx
            if repaired:f.s=v4(f.s)
            bodies=[]; external=f.aiand; primary=f.openai
            def aiand(*args):
                bodies.append(json.loads(args[2])); return external(*args)
            def openai(*args):
                bodies.append(json.loads(args[2])); return primary(*args)
            f.aiand=aiand; f.openai=openai
            _, result=f.run_assessment(f.build())
            self.assertTrue(bodies)
            for body in bodies:
                cap=body.get('max_completion_tokens', body.get('max_output_tokens'))
                self.assertEqual(cap,16000 if repaired and 'messages' in body else 4096)
            for stage in result['routing']['stages']:
                self.assertIn('budget_allowed',stage)
            self.assertEqual(result['budget_allowed']['deadline_ms'], 60000)

    def test_v4_refuses_missing_boolean_unbounded_and_mixed_legacy_caps(self):
        from larp.intelligence.routing import validate_routing_spec
        source=json.loads((test_aiand_routing.ROOT/'config/intelligence/aiand-routing.openai-trial.example.json').read_bytes())
        for cap in (None, True, 0, -1, 16001, '16000'):
            for where in ('openai','routine','reviewer'):
                spec=v4(source)
                if where=='openai':spec['openai_max_output_tokens']=cap
                elif where=='routine':spec['routine']['max_output_tokens']=cap
                else:spec['external_reviewers'][0]['max_output_tokens']=cap
                with self.subTest(cap=cap,where=where),self.assertRaises(IntelligenceError):
                    validate_routing_spec(spec)
        for spec in (v4(source),source):
            spec['max_output_tokens' if spec['schema'].endswith('v4') else 'openai_max_output_tokens']=4096
            with self.assertRaises(IntelligenceError):validate_routing_spec(spec)


class CitationContract(unittest.TestCase):
    def test_private_failure_counterparts_abstain_without_dropping_bad_claims(self):
        from larp.intelligence.models import ScriptedModel
        for defect in ('span_text', 'metric', 'item', 'record', 'document', 'off_by_one',
                       'unknown_claim', 'unknown_statement', 'schema'):
            w=build_world(['EXSEMI_Q2_8K','EXSEMI_Q3_8K'])
            def decide(state):
                if state['gaps'] and state['remaining_tool_calls']:
                    gap=state['gaps'][0]
                    return dict(action='CALL_TOOL',tool=gap['tool'],args=gap['args'])
                claims=deepcopy(state['claimable'])
                numeric=next(c for c in claims if c['metric']=='revenue' and 'Revenue |' in c['span']['text'])
                if defect=='span_text':numeric['span']['text'] += ' invented'
                elif defect=='metric':numeric['metric']='eps_diluted'
                elif defect=='item':
                    claims.append(dict(kind='EVENT',metric='ITEM:1.01',source=dict(record_id=w.record('EXSEMI_Q3_8K')['record_id'])))
                elif defect=='record':numeric['source']['record_id']=w.record('EXSEMI_Q2_8K')['record_id']
                elif defect=='document':numeric['span']['doc']='0'*64
                elif defect=='off_by_one':numeric['span']['start']+=1
                elif defect=='unknown_claim':numeric['citation_handle']='invented'
                elif defect=='unknown_statement':numeric['statement']=dict(unknown='not in contract')
                output=dict(action='FINISH',claims=claims)
                if defect=='schema':output['explanation']='extra top-level field'
                return output
            model=ScriptedModel(w.clock,[dict(output=decide)])
            result=w.assessor(model).assess(w.request(['EXSEMI_Q3_8K'],issuer_id=EXSEMI,job_id=defect)).read()
            with self.subTest(defect=defect):
                self.assertEqual(result['status'],'ABSTAIN')
                self.assertEqual(result['claims'],[])
                self.assertIsNone(result['proposed_thesis'])
                if defect!='schema':self.assertTrue(result['rejected_claims'])

    def test_unicode_repeated_text_keeps_exact_character_and_statement_provenance(self):
        from larp.intelligence.facts import extract_document
        from larp.intelligence.verify import fact_as_claim, verify_claim, claim_schema_error
        w=build_world(['EXSEMI_Q2_8K'])
        line='Revenue for the third quarter of fiscal 2027 was $35.1 billion.'
        text='préface 🧪\n'+line+'\n'+line
        sha=sha256_hex(text.encode()); texts={sha:text}
        facts=extract_document(text,sha,w.registry.by_issuer(EXSEMI),dict(accession='synthetic',record_id='r'))
        claims=[fact_as_claim(f) for f in facts if f['metric']=='revenue']
        self.assertEqual(len(claims),2)
        for claim in claims:self.assertIsNone(verify_claim(claim,texts)[1])
        bad=deepcopy(claims[0]); bad['span']['start']=len(text[:bad['span']['start']].encode())
        self.assertIsNotNone(verify_claim(bad,texts)[1])
        bad=deepcopy(claims[1]); bad['period_span']=claims[0]['period_span']
        self.assertIsNotNone(verify_claim(bad,texts)[1])
        bad=deepcopy(claims[0]);bad['statement']=dict(unrecognized='ignored previously')
        self.assertEqual(claim_schema_error(bad),'STATEMENT_MALFORMED')


class ReportingBudget(unittest.TestCase):
    def result(self, elapsed=120000, bound=180000):
        w = build_world(['EXSEMI_Q2_8K'])
        value = w.assessor(RuleBaselineModel(w.clock)).assess(
            w.request(['EXSEMI_Q2_8K'], issuer_id=EXSEMI, job_id='report')).read()
        value['budget_used']['elapsed_ms'] = elapsed
        value['budget_allowed'] = dict(deadline_ms=bound, tool_calls=6)
        return value

    def test_mixed_bounds_and_equality(self):
        results = [self.result(bound=b) for b in (180000, 60000, 90000, 120000)]
        self.assertEqual(bakeoff.metrics(results)['latency_ms']['within_deadline'], 2)

    def test_missing_bound_is_unknown(self):
        value = self.result(elapsed=1); value.pop('budget_allowed')
        self.assertEqual(bakeoff.metrics([value])['latency_ms']['within_deadline'], 0)
        self.assertEqual(bakeoff.metrics([value])['latency_ms']['unknown_deadline'], 1)

    def test_invalid_bounds_overrun_historical_override_and_unavailable(self):
        for bound in (None, True, '180000', 0, -1, 180001):
            with self.subTest(bound=bound):
                value=self.result(elapsed=1,bound=bound)
                self.assertEqual(bakeoff.metrics([value])['latency_ms']['unknown_deadline'],1)
        value=self.result(elapsed=120001,bound=120000)
        self.assertEqual(bakeoff.metrics([value])['latency_ms']['over_deadline'],1)
        value=self.result()
        self.assertEqual(bakeoff.metrics([value],historical_deadline_ms=60000)['latency_ms']['within_deadline'],0)
        value['status']='UNAVAILABLE'; value['reasons']=['ROUTING_GROUP_BUSY']
        report=bakeoff.metrics([value])
        self.assertEqual(report['latency_ms']['usable_within_deadline'],0)
        self.assertEqual(report['timing']['busy_not_started_jobs'],1)
        self.assertIsNone(report['timing']['per_result'][0]['usable_result_delay_ms'])

    def test_raw_recovery_is_additive_preserves_frozen_m5_and_checks_hashes(self):
        from tests.intelligence.test_providers import request
        helper=test_aiand_routing.AIandWire(); helper.setUp()
        def mutate(p,h):
            p['choices'][0].update(finish_reason='length')
            p['usage']['completion_tokens']=4096
        reply=helper.build(mutate).step(request(),5000).read()
        # Portable historical normalized shape: originals remain immutable.
        reply.update(error='AIAND_INCOMPLETE_OR_MULTIPLE_CHOICES', usage=dict(input_tokens=0,output_tokens=0))
        reply.pop('finish_reason'); reply.pop('usage_known')
        value=self.result()
        value['model']=dict(provider='aiand')
        value['model_io']=dict(steps=[dict(request=request().read(),response=reply)],tool_calls=[],requests_started=1)
        original=deepcopy(value)
        metrics=bakeoff.metrics([value],artifact_reader=helper.w.artifacts.get)
        self.assertEqual(metrics['schema_valid_denominator'],1)
        self.assertEqual(metrics['schema_valid_numerator'],0)
        self.assertEqual(metrics['failure_causes']['token_limit'],1)
        self.assertEqual(metrics['usage']['recovered_output_tokens'],4096)
        self.assertEqual(value,original)
        with self.assertRaises(IntelligenceError):
            bakeoff.metrics([value],artifact_reader=lambda ref:b'wrong')

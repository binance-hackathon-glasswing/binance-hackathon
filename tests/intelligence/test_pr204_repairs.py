"""PC-AUDIT01 portable regressions. Synthetic transports only; never paid inference."""
from copy import deepcopy
import json
import unittest

from larp.contracts import Document
from larp.intelligence import bakeoff
from larp.intelligence.scenarios import EXSEMI, build_world
from larp.intelligence.models import RuleBaselineModel
from tests.intelligence import test_aiand_routing, test_roundlog


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

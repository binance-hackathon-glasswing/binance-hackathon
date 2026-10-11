"""IDEA-041 AC-5.1/5.2: model I/O records and ModelTrace.v1 for the official round log (I5).

Keegan's round-log builder is not published yet (due Oct 14); these tests check the producer side. The test
against his builder is NOT RUN until then.
"""

import json
import time
import unittest

from larp.contracts import Document
from larp.intelligence.models import RuleBaselineModel, ScriptedModel
from larp.intelligence.providers import AnthropicMessagesModel
from larp.intelligence.roundlog import TRUNCATED, model_trace
from larp.intelligence.scenarios import EXSEMI, build_world
from larp.runtime.schema import assessment_result
from tests.intelligence.test_providers import SECRET, anthropic_reply


class ModelTraces(unittest.TestCase):
    def setUp(self):
        self.w = build_world(["EXSEMI_Q2_8K", "EXSEMI_Q3_8K"])

    def run_model(self, model, **kw):
        request = self.w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="trace", **kw)
        result = self.w.assessor(model).assess(request)
        return request, result.read()

    def hosted(self, decide, summary="I closed the prior-guidance gap, then confirmed the extracted facts.",
               sleep_s=0.0):
        def send(url, headers, body, timeout_s):
            if sleep_s:
                time.sleep(sleep_s)
            self.w.clock.advance(700)
            sent = json.loads(body)
            state = json.loads(sent["messages"][0]["content"])
            return 200, json.dumps(anthropic_reply(decide(state), summary=summary)(sent)).encode()
        return AnthropicMessagesModel(model_id="example-model-id", api_key=SECRET, prompt_text=self.w.config.prompt_text,
                                      prompt_sha256=self.w.config.prompt_sha256, clock_ms=self.w.clock,
                                      artifacts=self.w.artifacts, transport=send)

    def test_assessed_rule_baseline(self):
        request, result = self.run_model(RuleBaselineModel(self.w.clock))
        assessment_result(Document.from_dict(result), request, self.w.clock())
        trace = model_trace(result)
        self.assertTrue(trace["model_called"])
        self.assertIsNone(trace["no_model_call_reason"])
        self.assertEqual(len(trace["calls"]), len(result["model_io"]["steps"]))
        self.assertTrue(all(c["request_sha256"] for c in trace["calls"]))
        self.assertIn("Rule baseline:", trace["cot"])  # the baseline's own step note, verbatim
        self.assertIn(result["rationale"], trace["cot"])
        self.assertEqual(len(trace["tool_calls"]), result["budget_used"]["tool_calls"])

    def test_hosted_summary_is_verbatim_and_bytes_are_addressed(self):
        summary = "I closed the prior-guidance gap, then confirmed the extracted facts."
        decide = lambda s: ({"action": "CALL_TOOL", "tool": s["gaps"][0]["tool"], "args": s["gaps"][0]["args"]}
                            if s["gaps"] and s["remaining_tool_calls"] else
                            {"action": "FINISH", "claims": s["claimable"], "notes": "ok"})
        _, result = self.run_model(self.hosted(decide, summary))
        trace = model_trace(result)
        self.assertEqual(result["status"], "ASSESSED")
        self.assertIn(f"provider reasoning summary: {summary}", trace["cot"])
        for call in trace["calls"]:
            self.assertEqual(self.w.artifacts.get(call["request_artifact"]) is not None, True)
            self.assertEqual(self.w.artifacts.get(call["response_artifact"]) is not None, True)
            self.assertNotIn(SECRET.encode(), self.w.artifacts.get(call["request_artifact"]))
        self.assertNotIn(SECRET, json.dumps(trace))

    def test_no_summary_is_said_not_invented(self):
        decide = lambda s: {"action": "FINISH", "claims": s["claimable"], "notes": "ok"}
        _, result = self.run_model(self.hosted(decide, summary=None))
        self.assertIn("no reasoning summary returned", model_trace(result)["cot"])

    def test_abstain_unavailable_and_rejected_say_what_happened(self):
        _, abstain = self.run_model(ScriptedModel(self.w.clock, [{"output": {"action": "SELL"}}]))
        self.assertEqual(abstain["status"], "ABSTAIN")
        self.assertTrue(model_trace(abstain)["model_called"])
        decide = lambda s: {"action": "FINISH", "claims": [], "notes": "late"}
        _, late = self.run_model(self.hosted(decide, sleep_s=1.0), deadline_ms=200)
        trace = model_trace(late)
        self.assertEqual(late["status"], "UNAVAILABLE")
        self.assertEqual((trace["model_called"], trace["requests_started"], trace["calls"]), (True, 1, []))
        self.assertIn("in flight at the deadline", trace["cot"])
        request = self.w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="bad", tool_calls=99)
        rejected = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(request).read()
        trace = model_trace(rejected)
        self.assertEqual((trace["model_called"], trace["no_model_call_reason"]),
                         (False, "BUDGET_EXCEEDS_DECLARATION"))
        self.assertIn("No model call: BUDGET_EXCEEDS_DECLARATION.", trace["cot"])

    def test_no_usable_evidence_records_no_model_call(self):
        request = Document.from_dict(dict(self.w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="none").read(),
                                          evidence_refs=[{"record_id": "rec:missing", "available_ms": 0}]))
        result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(request).read()
        self.assertEqual((result["status"], result["model_io"]["model_called"],
                          result["model_io"]["no_model_call_reason"]), ("UNAVAILABLE", False, "NO_USABLE_EVIDENCE"))

    def test_cot_truncation_is_marked(self):
        _, result = self.run_model(RuleBaselineModel(self.w.clock))
        cot = model_trace(result, max_cot_chars=200)["cot"]
        self.assertEqual(len(cot), 200)
        self.assertTrue(cot.endswith(TRUNCATED))


if __name__ == "__main__":
    unittest.main()

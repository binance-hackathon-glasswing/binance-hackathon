"""IDEA-041 AC-2.4: the bake-off harness computes its metrics from real assessor results (synthetic filings here;
the real-filing run is NOT RUN until the team supplies a key, budget and the SEC User-Agent)."""

import unittest

from larp.intelligence import bakeoff
from larp.intelligence.models import RuleBaselineModel, ScriptedModel
from larp.intelligence.scenarios import EXSEMI, build_world
from tests.intelligence import test_roundlog

KEYS = ["EXSEMI_Q3_8K", "EXSEMI_402_8K", "EXSEMI_502_8K"]


class Bakeoff(unittest.TestCase):
    def test_metrics_and_report(self):
        w = build_world(["EXSEMI_Q2_8K"] + KEYS)
        helper = test_roundlog.ModelTraces()
        helper.w = w
        rule = lambda s: ({"action": "CALL_TOOL", "tool": s["gaps"][0]["tool"], "args": s["gaps"][0]["args"]}
                          if s["gaps"] and s["remaining_tool_calls"] else
                          {"action": "FINISH", "claims": s["claimable"], "notes": "ok"})
        candidates = {"baseline": RuleBaselineModel(w.clock), "hosted": helper.hosted(rule),
                      "broken": ScriptedModel(w.clock, [{"output": {"action": "SELL"}}])}
        requests = [w.request([k], issuer_id=EXSEMI, job_id=f"bake-{k}") for k in KEYS]
        results = bakeoff.run(candidates, requests, w.assessor)
        report = bakeoff.report(results, baseline_name="baseline",
                                filings=[{"accession": w.record(k)["accession"]} for k in KEYS], commit="test",
                                generated_ms=w.clock(),
                                identities={n: m.identity.record() for n, m in candidates.items()})
        hosted, broken = report["candidates"]["hosted"]["metrics"], report["candidates"]["broken"]["metrics"]
        self.assertEqual(hosted["assessments"], 3)
        self.assertEqual(hosted["schema_valid_rate"], 1.0)
        self.assertEqual(hosted["claim_verification_pass_rate"], 1.0)
        self.assertEqual(hosted["finding_agreement_with_baseline"], 1.0)
        self.assertLessEqual(hosted["tool_calls"]["max"], 6)
        self.assertEqual(hosted["latency_ms"]["within_deadline"], 3)
        self.assertEqual(broken["schema_valid_rate"], 0.0)
        self.assertEqual(broken["status_counts"], {"ABSTAIN": 3})
        self.assertEqual(len(report["per_filing"]), 3)
        self.assertIsNone(report["candidates"]["baseline"]["metrics"]["finding_agreement_with_baseline"])


class ReviewMetrics(unittest.TestCase):
    """R15: provider errors are not schema-invalid replies. R10: calls abandoned at the deadline are counted."""

    def setUp(self):
        self.w = build_world(["EXSEMI_Q2_8K"] + KEYS)

    def anthropic(self, send):
        from larp.intelligence.providers import AnthropicMessagesModel
        from tests.intelligence.test_providers import SECRET
        return AnthropicMessagesModel(model_id="example-model-id", api_key=SECRET, prompt_text=self.w.config.prompt_text,
                                      prompt_sha256=self.w.config.prompt_sha256, clock_ms=self.w.clock,
                                      artifacts=self.w.artifacts, transport=send)

    def test_http_errors_are_provider_errors_not_invalid_replies(self):
        statuses = iter([429, 500, 503])
        model = self.anthropic(lambda url, headers, body, timeout_s: (next(statuses), b'{"type":"error"}'))
        requests = [self.w.request([k], issuer_id=EXSEMI, job_id=f"err-{k}") for k in KEYS]
        metrics = bakeoff.metrics(bakeoff.run({"m": model}, requests, self.w.assessor)["m"])
        self.assertEqual(metrics["model_replies"], 0)
        self.assertIsNone(metrics["schema_valid_rate"])
        self.assertEqual(metrics["provider_errors"], 3)

    def test_calls_abandoned_at_the_deadline_are_counted(self):
        import json
        import time
        from tests.intelligence.test_providers import FINISH, anthropic_reply

        def slow(url, headers, body, timeout_s):
            time.sleep(0.6)
            return 200, json.dumps(anthropic_reply(FINISH)(json.loads(body))).encode()
        requests = [self.w.request([k], issuer_id=EXSEMI, job_id=f"slow-{k}", deadline_ms=150) for k in KEYS[:2]]
        metrics = bakeoff.metrics(bakeoff.run({"m": self.anthropic(slow)}, requests, self.w.assessor)["m"])
        self.assertEqual(metrics["status_counts"], {"UNAVAILABLE": 2})
        self.assertEqual(metrics["cost_micro_usd"]["calls_abandoned_at_deadline"], 2)
        self.assertTrue(metrics["cost_micro_usd"]["lower_bound"])

    def test_timed_out_calls_make_cost_a_lower_bound(self):
        model = self.anthropic(lambda url, headers, body, timeout_s: (_ for _ in ()).throw(TimeoutError()))
        requests = [self.w.request([KEYS[0]], issuer_id=EXSEMI, job_id="timeout")]
        metrics = bakeoff.metrics(bakeoff.run({"m": model}, requests, self.w.assessor)["m"])
        self.assertEqual(metrics["cost_micro_usd"]["calls_without_usage"], 1)
        self.assertTrue(metrics["cost_micro_usd"]["lower_bound"])


if __name__ == "__main__":
    unittest.main()

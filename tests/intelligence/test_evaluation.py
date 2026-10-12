"""Pre-registered synthetic evaluation (IDEA-025 §5; IDEA-031 AC-E01..E03 with eval_thresholds.v2.json)."""

import json
import unittest
from fractions import Fraction

from larp.intelligence.config import CONFIG_DIR
from larp.intelligence.evaluation import evaluate, score
from larp.intelligence.models import RuleBaselineModel


class SyntheticEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate()

    def test_v1_thresholds_file_is_kept_unchanged_and_v2_is_used(self):
        v1 = json.loads((CONFIG_DIR / "eval_thresholds.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(v1["agent"]["unsupported_acceptance__max"], [0, 1])
        v2 = json.loads((CONFIG_DIR / "eval_thresholds.v2.json").read_text(encoding="utf-8"))
        self.assertEqual(v2["agent"]["numerical_precision__min"], [1, 1])

    def test_every_preregistered_check_passes(self):
        failed = [c for c in self.report["checks"] if not c["pass"]]
        self.assertEqual(failed, [])
        self.assertEqual(self.report["acceptance"], "PASS")

    def test_retrieval_ablation_is_not_called_llm_value(self):
        comparison = self.report["comparison"]
        self.assertEqual(comparison["kind"], "RETRIEVAL_ABLATION_NOT_LLM_VALUE")
        self.assertEqual(comparison["verdict"], "SUPPORTED_ON_SYNTHETIC_PACK")
        self.assertGreaterEqual(Fraction(*comparison["gain"]), Fraction(1, 4))
        self.assertEqual(self.report["model_vs_deterministic"]["status"], "NOT_RUN")

    def test_e02_statement_classes_are_scored(self):
        classes = self.report["metrics"]["agent"]["statement_classes"]
        self.assertEqual(set(classes), {"ATTRIBUTED_REPORT", "FORECAST", "CONDITIONAL_RISK", "ANNOUNCED_FUTURE",
                                        "OCCURRED"})
        self.assertEqual(self.report["metrics"]["agent"]["false_positives"]["statements"], 0)

    def test_report_is_labelled_synthetic(self):
        self.assertTrue(self.report["synthetic"])
        self.assertIn("not evidence", self.report["note"])
        self.assertEqual(len(self.report["pack_digest"]), 64)


class PrecisionScoringTests(unittest.TestCase):
    def run_with(self, claims, statements=(), exhaustive=True):
        labels = {"status": "ASSESSED", "exhaustive": exhaustive,
                  "facts": [{"kind": "REPORTED", "metric": "revenue", "period": "FY2027-Q3", "value": "35.1",
                             "unit": "USD", "scale_exp10": 9}],
                  "events": ["ITEM:2.02"], "statements": [["IMPAIRMENT", "FORECAST"]]}
        result = {"status": "ASSESSED", "claims": claims, "event_statements": list(statements), "findings": [],
                  "falsifiers": [], "rejected_claims": [], "missingness": [], "coverage": {"complete": True},
                  "budget_used": {"tool_calls": 0, "elapsed_ms": 5}}
        return score([{"case": {"labels": labels}, "result": result, "probes": [], "spans_ok": True}])

    def claim(self, value, metric="revenue", kind="REPORTED"):
        return {"kind": kind, "metric": metric, "period": "FY2027-Q3", "unit": "USD", "scale_exp10": 9,
                "value": [int(Fraction(value) * 10), 10], "span": {"doc": "d", "start": 0, "end": 1, "text": "x"}}

    def test_e01_unexpected_outputs_are_false_positives(self):
        event = lambda metric: {"kind": "EVENT", "metric": metric, "period": None, "unit": None, "scale_exp10": 0}
        exact = self.run_with([self.claim("35.1"), event("ITEM:2.02")],
                              [{"event": "IMPAIRMENT", "semantics": {"assertion": "FORECAST"}}])
        self.assertEqual((exact["numerical_precision"], exact["event_precision"], exact["statement_precision"]),
                         ([1, 1], [1, 1], [1, 1]))
        extra = self.run_with([self.claim("35.1"), self.claim("1.2", metric="net_income"),
                               event("ITEM:2.02"), event("IMPAIRMENT")],
                              [{"event": "IMPAIRMENT", "semantics": {"assertion": "FORECAST"}},
                               {"event": "DELISTING", "semantics": {"assertion": "CONDITIONAL_RISK"}}])
        self.assertEqual(extra["numerical_precision"], [1, 2])
        self.assertEqual(extra["event_precision"], [1, 2])
        self.assertEqual(extra["statement_precision"], [1, 2])
        self.assertEqual(extra["false_positives"], {"numerical": 1, "events": 1, "statements": 1, "findings": 0})
        self.assertIsNone(self.run_with([self.claim("1.2", metric="net_income")], exhaustive=False)["numerical_precision"])


class ModelArmHarnessTests(unittest.TestCase):
    def test_e03_both_arms_share_inputs_and_a_fake_is_harness_only(self):
        report = evaluate(model_arm={"name": "rule-as-fake", "fake": True,
                                     "factory": lambda world: RuleBaselineModel(world.clock)})
        arm = report["model_vs_deterministic"]
        self.assertEqual((arm["status"], arm["identical_inputs"], arm["tool_budget"]), ("HARNESS_ONLY", True, 6))
        self.assertEqual(arm["deterministic"], arm["model_arm"])  # same model on the same inputs scores the same


if __name__ == "__main__":
    unittest.main()

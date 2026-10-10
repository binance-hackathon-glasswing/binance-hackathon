"""Pre-registered synthetic evaluation (IDEA-025 §5): thresholds frozen in eval_thresholds.v1.json."""

import json
import unittest
from fractions import Fraction

from larp.intelligence.config import CONFIG_DIR
from larp.intelligence.evaluation import evaluate


class SyntheticEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate()

    def test_thresholds_file_is_the_frozen_version(self):
        thresholds = json.loads((CONFIG_DIR / "eval_thresholds.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(thresholds["agent"]["unsupported_acceptance__max"], [0, 1])
        self.assertEqual(thresholds["agent"]["max_tool_calls__max"], 6)

    def test_every_preregistered_check_passes(self):
        failed = [c for c in self.report["checks"] if not c["pass"]]
        self.assertEqual(failed, [])
        self.assertEqual(self.report["acceptance"], "PASS")

    def test_agent_versus_simple_baseline(self):
        comparison = self.report["comparison"]
        self.assertEqual(comparison["verdict"], "SUPPORTED_ON_SYNTHETIC_PACK")
        self.assertGreaterEqual(Fraction(*comparison["gain"]), Fraction(1, 4))

    def test_report_is_labelled_synthetic(self):
        self.assertTrue(self.report["synthetic"])
        self.assertIn("not evidence", self.report["note"])
        self.assertEqual(len(self.report["pack_digest"]), 64)


if __name__ == "__main__":
    unittest.main()

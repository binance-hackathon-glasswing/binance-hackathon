"""IDEA-031 AC-E04: independently labelled real-document evaluation path (NOT RUN today)."""

import json
import os
import tempfile
import unittest

from larp.intelligence.realeval import admissible, run, score, wilson
from larp.intelligence.config import CONFIG_DIR

CRITERIA = json.loads((CONFIG_DIR / "real_eval_criteria.v1.json").read_text())


class RealEvalTests(unittest.TestCase):
    def test_without_manifest_it_is_not_run(self):
        report = run(None)
        self.assertEqual((report["status"], report["reason"]),
                         ("NOT_RUN", "NO_INDEPENDENTLY_LABELLED_RIGHTS_CLEARED_MANIFEST"))
        self.assertFalse(report["promotion_authorized"])

    def manifest(self, **changes):
        docs = [{"doc_id": f"d{i}", "path": f"/tmp/elsewhere/d{i}.htm", "sha256": "0" * 64, "split": "HELD_OUT",
                 "rights": {"cleared": True, "licence_id": "CC-BY-4.0"}} for i in range(60)]
        m = {"schema": "RealEvalManifest.v1", "synthetic": False, "documents": docs,
             "labels": {"annotators": ["ann-1", "ann-2"], "implementers": ["impl-1"], "frozen_commit": "a" * 40,
                        "frozen_before_predictions": True, "items": {}}}
        m.update(changes)
        return m

    def test_synthetic_or_non_independent_manifests_are_refused(self):
        self.assertEqual(admissible(self.manifest(), CRITERIA), [])
        self.assertIn("SYNTHETIC_NOT_ADMISSIBLE", admissible(self.manifest(synthetic=True), CRITERIA))
        overlap = self.manifest()
        overlap["labels"]["annotators"] = ["impl-1", "ann-2"]
        self.assertIn("ANNOTATORS_NOT_INDEPENDENT_OF_IMPLEMENTERS", admissible(overlap, CRITERIA))
        unfrozen = self.manifest()
        unfrozen["labels"]["frozen_before_predictions"] = False
        self.assertIn("LABELS_NOT_FROZEN_BEFORE_PREDICTIONS", admissible(unfrozen, CRITERIA))
        small = self.manifest(documents=self.manifest()["documents"][:10])
        self.assertIn("TOO_FEW_HELD_OUT_DOCUMENTS", admissible(small, CRITERIA))
        inside = self.manifest()
        inside["documents"][0]["path"] = os.path.join(os.getcwd(), "docs", "x.htm")
        self.assertIn("DOCUMENT_INSIDE_REPOSITORY", admissible(inside, CRITERIA))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.json")
            with open(path, "w") as handle:
                json.dump(self.manifest(synthetic=True), handle)
            self.assertEqual(run(path)["status"], "REFUSED")

    def test_scoring_counts_false_positives_with_wilson_intervals(self):
        rows = [{"doc_id": "a", "split": "HELD_OUT",
                 "expected": {"findings": ["IMPAIRMENT"], "statements": [["OFFICER_DEPARTURE", "ANNOUNCED_FUTURE"]]},
                 "predicted": {"findings": ["IMPAIRMENT", "CYBERSECURITY_INCIDENT"],
                               "statements": [["OFFICER_DEPARTURE", "OCCURRED"]]}}]
        out = score(rows)
        self.assertEqual((out["findings"]["tp"], out["findings"]["fp"], out["findings"]["fn"]), (1, 1, 0))
        self.assertEqual(out["findings"]["false_positives"], [["a", "CYBERSECURITY_INCIDENT"]])
        self.assertEqual((out["statements"]["tp"], out["statements"]["fp"], out["statements"]["fn"]), (0, 1, 1))
        low, high = wilson(9, 10)
        self.assertTrue(0.59 < low < 0.6 and 0.98 < high < 0.99)
        self.assertIsNone(wilson(0, 0))


if __name__ == "__main__":
    unittest.main()

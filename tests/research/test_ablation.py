"""IDEA-031 AC-E06: ablation study specification; NOT_RUN without an EXP record and rights-cleared data."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from larp.research import ablation

SHARED = {"sizing_rule": "declared-vol-v1", "risk_profile_hash": "b" * 64, "execution_model": "rfq-exact-size-v1",
          "cost_model": "observed-gas-spread-v1", "starting_cash_units": 200_000_000, "primary_horizon_sessions": 5,
          "entry_exit_reentry_policy_hash": "c" * 64, "correction_policy": "latch-until-source-correction"}


def spec(**changes):
    arms = {name: dict(SHARED, evidence_inputs=list(ablation.EVIDENCE[name]), authority="SHADOW_EVALUATION")
            for name in ablation.ARMS}
    s = {"schema": "AblationStudy.v1", "exp_id": "EXP-999", "study_id": "ABLATION-UNIT-CHECK",
         "secondary_horizons_are_diagnostics_only": True,
         "dataset": {"rights_cleared": True, "point_in_time": True, "sha256": "d" * 64}, "arms": arms}
    s.update(changes)
    return s


class AblationTests(unittest.TestCase):
    def test_not_run_without_exp_record_or_rights_cleared_data(self):
        report = ablation.run(spec(dataset={}), {}, {}).read()
        self.assertEqual(report["status"], "NOT_RUN")
        self.assertIn("NO_COMMITTED_EXP_RECORD", report["reasons"])
        self.assertIn("NO_RIGHTS_CLEARED_POINT_IN_TIME_DATA", report["reasons"])
        self.assertFalse(report["promotion_authorized"])

    def test_arms_may_differ_only_in_evidence_inputs(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ablation, "LEDGER", Path(tmp)):
            (Path(tmp) / "EXP-999.md").write_text("synthetic registration stub for ABLATION-UNIT-CHECK")
            self.assertEqual(ablation.validate(spec()), ["NO_COMMITTED_EXP_RECORD"])  # not tracked by git
            with patch.object(ablation, "_committed", lambda path: True):
                self.assertEqual(ablation.validate(spec()), [])
                self.assertIn("NO_COMMITTED_EXP_RECORD", ablation.validate(spec(study_id="OTHER-STUDY")))
        with tempfile.TemporaryDirectory() as tmp, patch.object(ablation, "LEDGER", Path(tmp)), \
                patch.object(ablation, "_committed", lambda path: True):
            (Path(tmp) / "EXP-999.md").write_text("synthetic registration stub for ABLATION-UNIT-CHECK")
            s = spec()
            s["arms"]["FREE_NEWS"]["sizing_rule"] = "bigger"
            self.assertIn("ARMS_DIFFER_BEYOND_EVIDENCE_INPUTS", ablation.validate(s))
            s = spec()
            s["arms"]["UNCERTAIN_EVENTS"]["authority"] = "LIVE"
            self.assertIn("ARM_AUTHORITY_UNCERTAIN_EVENTS", ablation.validate(s))
            self.assertIn("PRIMARY_HORIZON_NOT_FROZEN",
                          ablation.validate(spec(secondary_horizons_are_diagnostics_only=False)))


if __name__ == "__main__":
    unittest.main()

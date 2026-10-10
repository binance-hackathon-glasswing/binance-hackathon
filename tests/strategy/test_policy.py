from dataclasses import replace
from datetime import timedelta
from fractions import Fraction
import unittest

from larp.contracts import ContractError, Document, TargetKind
from larp.integration.contract import context_hash
from larp.research.fixtures import snapshot, changed, with_quotes
from larp.strategy.features import features, declared_weight
from larp.strategy.policy import decide


class PolicyTests(unittest.TestCase):
    def feature(self, s, series=None):
        c = s.context.read()
        m = c["markets"][0]
        return features(Document.from_dict(series or c["series"][m["symbol"]]),
                        cutoff=s.observed_at, expected_entity=m["underlying_id"], max_age_seconds=864000)

    def assessment(self, s, **changes):
        """EvidenceContext.v1 (IDEA-031) for the first market. Before IDEA-031 this helper built a dict bound to the
        policy's own ThesisContext digest, a shape no evidence producer emitted (IDEA-030 R02)."""
        m = s.context.read()["markets"][0]
        now_ms = int(s.observed_at.timestamp() * 1000)
        record = {"schema": "EvidenceContext.v1", "run_id": s.run_id, "issuer_id": m["underlying_id"],
                  "underlying_id": m["underlying_id"], "token": m["symbol"],
                  "policy_profile_hash": s.policy_profile_hash, "state_version": 1, "as_of_ms": now_ms,
                  "latest_cutoff_ms": now_ms, "assessed_until_ms": now_ms + 60_000, "status": "ADVERSE",
                  "status_reasons": [], "availability": "AVAILABLE", "quality": "VERIFIED", "review_complete": True,
                  "falsifier_findings": [{"predicate_id": "fixture-reporting-integrity", "finding_id": "find:x",
                                          "supported": True, "verifier_accepted": True,
                                          "supporting_spans": ["synthetic span"],
                                          "resolution_rule": "SOURCE_CORRECTED_OR_WITHDRAWN"}],
                  "statements_pending": [], "statements_exhausted": [], "due_reviews": [], "thesis_status": None,
                  "last_rejection": None}
        record.update(changes)
        record["context_hash"] = context_hash(record)
        return record

    def test_future_perturbation_does_not_change_decisions_or_features(self):
        s = snapshot()
        original = decide(s, s.policy_state)
        c = s.context.read()
        for series in c["series"].values():
            future = dict(series["bars"][-1], session_index=999, close_units=999999999,
                          close_at=(s.observed_at + timedelta(days=1)).isoformat(),
                          available_at=(s.observed_at + timedelta(days=1)).isoformat())
            series["bars"].append(future)
        altered = changed(s, series=c["series"])
        after = decide(altered, altered.policy_state)
        self.assertEqual(original.targets, after.targets)
        self.assertEqual(original.next_policy_state.data, after.next_policy_state.data)
        self.assertEqual(self.feature(s), self.feature(altered))

    def test_missing_gapped_zero_and_wrong_entity_history_have_no_sizing_fallback(self):
        s = snapshot()
        series = s.context.read()["series"]["NVDAB"]
        for bad in (dict(series, bars=series["bars"][-20:]),
                    dict(series, entity_id="wrong"),
                    dict(series, bars=[dict(b, close_units=100) for b in series["bars"]]),
                    dict(series, bars=series["bars"][:30] + series["bars"][31:])):
            f = self.feature(s, bad)
            self.assertNotEqual(f.read()["status"], "VALID")
            with self.assertRaises(ContractError):
                declared_weight(f)

    def test_declared_formula_and_entity_metadata(self):
        f = self.feature(snapshot())
        self.assertEqual(declared_weight(f), min(Fraction(1, 5), Fraction(10**9, 200 * f.read()["sigma_5session_ppb"])))
        self.assertEqual(f.read()["instrument_kind"], "UNDERLYING_SHARE")

    def test_corporate_action_mismatch_and_late_availability(self):
        s = snapshot()
        series = s.context.read()["series"]["NVDAB"]
        series["bars"][-1]["corporate_action_version"] = "unreconciled-split"
        self.assertEqual(self.feature(s, series).read()["reasons"], ["CORPORATE_ACTION_OR_BAR_QUALITY"])
        series = s.context.read()["series"]["NVDAB"]
        series["bars"][-1]["available_at"] = (s.observed_at + timedelta(seconds=1)).isoformat()
        self.assertEqual(self.feature(s, series).read()["status"], "MISSING")

    def test_shadow_and_explicit_bounded_variant(self):
        for mode, expected in (("SHADOW", TargetKind.KEEP_QUANTITY), ("BOUNDED_FALSIFIER", TargetKind.EXIT)):
            s = snapshot(held={"NVDAB": 2000}, profile_changes={"evidence_mode": mode})
            s = changed(s, assessments=[self.assessment(s)])
            result = decide(s, s.policy_state)
            target = next(t for t in result.targets if t.symbol == "NVDAB")
            self.assertEqual(target.kind, expected)
            self.assertTrue(result.next_policy_state.data.read()["shadow_findings"])

    def test_stale_assessment_cannot_clear_reentry(self):
        s = snapshot()
        st = replace(s.policy_state, data=Document.from_dict({"lifecycle": {
            "NVDAB": {"ever_held": True, "last_review_session": 70}}}))
        s = replace(s, policy_state=st)
        now_ms = int(s.observed_at.timestamp() * 1000)
        a = self.assessment(s, status="CLEAR", assessed_until_ms=now_ms, falsifier_findings=[])
        result = decide(changed(s, assessments=[a]), st)
        self.assertEqual(result.next_policy_state.data.read()["evidence_rejections"], [])
        self.assertEqual(next(t for t in result.targets if t.symbol == "NVDAB").kind, TargetKind.KEEP_QUANTITY)

    def test_horizon_reviews_without_forced_turnover(self):
        s = snapshot(held={"NVDAB": 2000})
        state = replace(s.policy_state, data=Document.from_dict({"lifecycle": {
            "NVDAB": {"ever_held": True, "last_review_session": 70}}}))
        s = replace(s, policy_state=state)
        p = decide(s, state)
        self.assertTrue(p.next_policy_state.data.read()["reviews"])
        self.assertEqual(next(t for t in p.targets if t.symbol == "NVDAB").kind, TargetKind.KEEP_QUANTITY)

    def test_live_config_and_stale_state_rejected(self):
        with self.assertRaises(ContractError):
            s = snapshot(profile_changes={"mode": "LIVE"})
            decide(s, s.policy_state)
        s = snapshot()
        with self.assertRaises(ContractError):
            decide(s, replace(s.policy_state, version=1))

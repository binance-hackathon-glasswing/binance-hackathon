from dataclasses import replace
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import json
from pathlib import Path
import unittest

from larp.contracts import ContractError, Document, TargetKind
from larp.research.fixtures import snapshot, changed, with_quotes
from larp.strategy.features import features, declared_weight
from larp.strategy.policy import decide
from larp.strategy.assessments import epoch_ms


class PolicyTests(unittest.TestCase):
    def feature(self, s, series=None):
        c = s.context.read()
        m = c["markets"][0]
        return features(Document.from_dict(series or c["series"][m["symbol"]]),
                        cutoff=s.observed_at, expected_entity=m["underlying_id"], max_age_seconds=864000)

    def assessment(self, s):
        m = s.context.read()["markets"][0]
        context = s.policy_state.data.read().get("evidence_contexts", {}).get(
            m["underlying_id"], {"thesis": None, "known_facts": []})
        h = Document.from_dict(context).digest("larp.intel.context.v1")
        now = epoch_ms(s.observed_at)
        return {"schema": "AssessmentResult.v1", "issuer_id": m["underlying_id"], "job_id": "fixture-job",
                "run_id": s.run_id, "policy_profile_hash": s.policy_profile_hash,
                "context_hash": h, "model_hash": "a" * 64, "prompt_hash": "b" * 64,
                "cutoff_ms": now, "completed_ms": now, "expiry_ms": now + 60000, "status": "ASSESSED",
                "missingness": [], "conflicts": [], "novelty": {"prior_not_checked": False},
                "proposed_thesis": {"status": "BROKEN", "based_on_context_hash": h},
                "evidence_used": [{"record_id": "fixture-record", "available_ms": now, "content_hash": "c" * 64}],
                "claims": [{"fact_id": "fixture-fact", "source": {"record_id": "fixture-record", "available_ms": now},
                            "span": {"doc": "d" * 64, "text": "synthetic verified span"}}],
                "falsifiers": [{"falsifier_id": "fixture-reporting-integrity", "state": "FIRED", "fact_ids": ["fixture-fact"]}]}

    def assessed(self, s, a):
        context = s.policy_state.data.read().get("evidence_contexts", {}).get(
            a["issuer_id"], {"thesis": None, "known_facts": []})
        request = {"schema": "AssessmentRequest.v1", "context": context,
                   **{k: a[k] for k in ("job_id", "run_id", "issuer_id", "context_hash", "policy_profile_hash", "cutoff_ms")}}
        return changed(s, assessments=[a], assessment_requests={a["issuer_id"]: request})

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
            s = self.assessed(s, self.assessment(s))
            result = decide(s, s.policy_state)
            target = next(t for t in result.targets if t.symbol == "NVDAB")
            self.assertEqual(target.kind, expected)
            self.assertTrue(result.next_policy_state.data.read()["shadow_findings"])

    def test_stale_assessment_cannot_clear_reentry(self):
        s = snapshot()
        st = replace(s.policy_state, data=Document.from_dict({"lifecycle": {
            "NVDAB": {"ever_held": True, "last_review_session": 70}}}))
        s = replace(s, policy_state=st)
        a = self.assessment(s)
        a.update(expiry_ms=epoch_ms(s.observed_at), falsifiers=[])
        result = decide(self.assessed(s, a), st)
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

    def test_actual_producer_payload_reaches_shadow_and_bounded_policy(self):
        fixture = json.loads((Path(__file__).parent / "fixtures/assessment-producer.json").read_text())
        for mode in ("SHADOW", "BOUNDED_FALSIFIER"):
            a, request = fixture["result"].copy(), fixture["request"].copy()
            s = snapshot(held={"NVDAB": 2000}, now=datetime.fromtimestamp(a["completed_ms"] / 1000, timezone.utc),
                profile_changes={"evidence_mode": mode,
                "falsifier_ids": [f["falsifier_id"] for f in a["falsifiers"]]})
            # Bind public producer fixture to this test run/profile; retain its
            # actual context, claims, timestamps and falsifier vocabulary.
            for document in (a, request):
                document.update(run_id=s.run_id, policy_profile_hash=s.policy_profile_hash)
            c = s.context.read()
            c["markets"][0]["underlying_id"] = a["issuer_id"]
            c["series"]["NVDAB"]["entity_id"] = a["issuer_id"]
            state = replace(s.policy_state, data=Document.from_dict({"evidence_contexts": {
                a["issuer_id"]: request["context"]}}))
            s = replace(changed(s, markets=c["markets"], series=c["series"], assessments=[a],
                               assessment_requests={a["issuer_id"]: request}), policy_state=state)
            result = decide(s, state)
            data = result.next_policy_state.data.read()
            self.assertTrue(data["shadow_findings"])
            self.assertIn("ASSESSMENT_ACCEPTED", [d["reason"] for d in data["assessment_diagnostics"]])
            target = next(t for t in result.targets if t.symbol == "NVDAB")
            self.assertEqual(target.kind, TargetKind.EXIT if mode == "BOUNDED_FALSIFIER" else TargetKind.KEEP_QUANTITY)
            # A claimed comparison absent from its committed harness finding
            # cannot borrow a current fact's support and authorize the overlay.
            corrupt = json.loads(json.dumps(a))
            for finding in corrupt["findings"]:
                if finding["type"] == "GUIDANCE_LOWERED":
                    finding["finding_id"] = "find:unverified"
            bad = changed(s, assessments=[corrupt])
            rejected = decide(bad, state).next_policy_state.data.read()
            self.assertFalse(rejected["shadow_findings"])
            self.assertFalse(rejected["blocked"])

    def test_assessment_diagnostics_context_and_fresh_review(self):
        s = snapshot(profile_changes={"assessment_required": True})
        a = self.assessment(s)
        a.update(falsifiers=[], proposed_thesis={"status": "INTACT", "based_on_context_hash": a["context_hash"]})
        valid = self.assessed(s, a)
        first = decide(valid, valid.policy_state)
        self.assertEqual(next(t for t in first.targets if t.symbol == "NVDAB").kind, TargetKind.TARGET_WEIGHT)
        # Lifecycle changes do not invalidate an unchanged issuer thesis context.
        following = replace(valid, policy_state=first.next_policy_state)
        self.assertEqual(next(t for t in decide(following, following.policy_state).targets
                              if t.symbol == "NVDAB").kind, TargetKind.TARGET_WEIGHT)
        for patch, expected in (({"expiry_ms": epoch_ms(s.observed_at)}, "ASSESSMENT_STALE_OR_FUTURE"),
                                ({"completed_ms": epoch_ms(s.observed_at) + 1}, "ASSESSMENT_STALE_OR_FUTURE"),
                                ({"context_hash": "e" * 64}, "ASSESSMENT_IDENTITY_MISMATCH"),
                                ({"status": "UNAVAILABLE"}, "ASSESSMENT_NOT_ASSESSED")):
            bad = changed(valid, assessments=[{**a, **patch}])
            result = decide(bad, bad.policy_state)
            self.assertEqual(next(t for t in result.targets if t.symbol == "NVDAB").kind, TargetKind.KEEP_QUANTITY)
            self.assertIn(expected, [d["reason"] for d in result.next_policy_state.data.read()["assessment_diagnostics"]])
        legacy = changed(s, assessments=[{"schema": "AssessmentResult.v1", "symbol": "NVDAB"}])
        self.assertEqual(decide(legacy, legacy.policy_state).next_policy_state.data.read()["assessment_diagnostics"][0]["reason"],
                         "ASSESSMENT_SCHEMA_UNRECOGNISED")

    def test_unsupported_falsifier_and_changed_issuer_context_cannot_authorize(self):
        s = snapshot(held={"NVDAB": 2000}, profile_changes={"evidence_mode": "BOUNDED_FALSIFIER"})
        a = self.assessment(s)
        a["falsifiers"][0]["fact_ids"] = ["nonexistent-fact"]
        result = decide(self.assessed(s, a), s.policy_state)
        self.assertFalse(result.next_policy_state.data.read()["blocked"])
        self.assertIn("ASSESSMENT_FALSIFIER_UNSUPPORTED", [d["reason"] for d in result.next_policy_state.data.read()["assessment_diagnostics"]])
        a = self.assessment(s)
        valid = self.assessed(s, a)
        state = replace(s.policy_state, data=Document.from_dict({"evidence_contexts": {
            a["issuer_id"]: {"thesis": {"version": 2}, "known_facts": []}}}))
        bad = replace(valid, policy_state=state)
        result = decide(bad, state)
        self.assertFalse(result.next_policy_state.data.read()["blocked"])
        self.assertEqual(result.next_policy_state.data.read()["assessment_diagnostics"][0]["reason"], "ASSESSMENT_STALE_CONTEXT")

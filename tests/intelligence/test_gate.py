"""Result acceptance: stale/late/duplicate rejection, and timeouts never making evidence look clear."""

import unittest

from larp.intelligence.agent import context_hash
from larp.intelligence.fakes import MemoryEvidenceStore
from larp.intelligence.features import feature_row
from larp.intelligence.gate import accept, initial_state, state_document
from larp.intelligence.models import RuleBaselineModel, ScriptedModel
from larp.intelligence.scenarios import EXSEMI, PROFILE, build_world, make_model, prior_thesis
from larp.intelligence.common import forbidden_key_paths


class GateTests(unittest.TestCase):
    def setUp(self):
        self.w = build_world(["EXSEMI_Q2_8K", "EXSEMI_Q3_8K", "EXSEMI_502_8K", "EXSEMI_402_8K"])
        self.context = prior_thesis(self.w.config, EXSEMI)
        self.state = dict(initial_state(EXSEMI, PROFILE), context=self.context, context_hash=context_hash(self.context))

    def assess(self, refs, model="rule", context=None, job="job:g"):
        request = self.w.request(refs, issuer_id=EXSEMI, job_id=job, context=context or self.context)
        return self.w.assessor(make_model(self.w, model)).assess(request)

    def test_accepting_an_assessment_moves_the_context_and_rejects_late_results_for_the_old_one(self):
        first = self.assess(["EXSEMI_Q3_8K"], job="job:1")
        self.w.clock.advance(1000)  # a later cutoff: not a replay of the same assessment
        late = self.assess(["EXSEMI_Q3_8K"], job="job:2")  # computed for the same, now obsolete, context
        decision, state = accept(self.state, first, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual(decision, "ACCEPT")
        self.assertNotEqual(state["context_hash"], self.state["context_hash"])
        self.assertEqual(state["context"]["thesis"]["status"], "BROKEN")
        self.assertEqual(state["evidence_gate"], "ADVERSE")
        self.assertEqual(accept(state, late, profile_hash=PROFILE, now_ms=self.w.clock())[0], "REJECT_STALE_CONTEXT")
        self.assertEqual(accept(state, first, profile_hash=PROFILE, now_ms=self.w.clock())[0], "DUPLICATE")
        state_document(state)  # persists as a canonical document

    def test_profile_expiry_order_and_issuer_rejections(self):
        result = self.assess(["EXSEMI_Q3_8K"])
        expiry = result.read()["expiry_ms"]
        self.assertEqual(accept(self.state, result, profile_hash="b" * 64, now_ms=self.w.clock())[0], "REJECT_PROFILE")
        self.assertEqual(accept(self.state, result, profile_hash=PROFILE, now_ms=expiry)[0], "REJECT_EXPIRED")
        later = dict(self.state, latest_cutoff_ms=self.w.clock() + 1)
        self.assertEqual(accept(later, result, profile_hash=PROFILE, now_ms=self.w.clock())[0], "REJECT_OUT_OF_ORDER")
        other = dict(self.state, issuer_id="FIXTURE-CIK-9900002")
        self.assertEqual(accept(other, result, profile_hash=PROFILE, now_ms=self.w.clock())[0], "REJECT_WRONG_ISSUER")

    def test_timeout_after_clear_evidence_never_stays_clear(self):
        clear = self.assess(["EXSEMI_502_8K"], job="job:clear")
        decision, state = accept(self.state, clear, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual((decision, state["evidence_gate"]), ("ACCEPT", "CLEAR"))
        self.w.clock.advance(1000)
        timeout = self.assess(["EXSEMI_502_8K"], model="timeout", context=state["context"], job="job:t")
        self.assertEqual(timeout.read()["status"], "UNAVAILABLE")
        decision, after = accept(state, timeout, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual((decision, after["evidence_gate"], after["availability"]), ("ACCEPT", "UNKNOWN", "UNAVAILABLE"))
        self.assertEqual(after["context_hash"], state["context_hash"])  # no thesis change from a timeout
        self.assertEqual(feature_row(timeout, after).read()["evidence_gate"], "UNKNOWN")

    def test_abstention_or_timeout_never_clears_adverse_findings(self):
        bad = self.assess(["EXSEMI_402_8K"], job="job:402")
        _, state = accept(self.state, bad, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual(state["evidence_gate"], "ADVERSE")
        held = state["unresolved_adverse"]
        for model in ("timeout", "fabricated_claim"):
            with self.subTest(model=model):
                self.w.clock.advance(1000)
                result = self.assess(["EXSEMI_502_8K"], model=model, context=state["context"], job=f"job:{model}")
                decision, after = accept(state, result, profile_hash=PROFILE, now_ms=self.w.clock())
                self.assertEqual((decision, after["evidence_gate"]), ("ACCEPT", "ADVERSE"))
                self.assertEqual(after["unresolved_adverse"][:len(held)], held)

    def test_verified_filer_events_survive_an_abstaining_model(self):
        result = self.assess(["EXSEMI_402_8K"], model="fabricated_claim", job="job:abstain-402")
        self.assertEqual(result.read()["status"], "ABSTAIN")
        self.assertIn("ITEM:4.02", {f["type"] for f in result.read()["event_findings"]})
        decision, state = accept(self.state, result, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual((decision, state["evidence_gate"]), ("ACCEPT", "ADVERSE"))

    def test_stale_source_cannot_be_clear(self):
        request = self.w.request(["EXSEMI_502_8K"], issuer_id=EXSEMI, job_id="job:stale", context=self.context,
                                 source_health={"status": "OK", "last_success_ms": self.w.clock() - 36_000_000})
        result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(request)
        self.assertIn("SOURCE_STALE", result.read()["missingness"])
        _, state = accept(self.state, result, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual(state["evidence_gate"], "UNKNOWN")
        self.assertIn("SOURCE_STALE", state["gate_reasons"])

    def test_untrusted_instructions_or_unchecked_priors_cannot_be_clear(self):
        w = build_world(["EXSEMI_INJECTION_8K", "EXSEMI_Q2_8K", "EXSEMI_Q3_10Q_COMPACT"])
        context = prior_thesis(w.config, EXSEMI)
        state = dict(initial_state(EXSEMI, PROFILE), context=context, context_hash=context_hash(context))
        cases = ((["EXSEMI_INJECTION_8K"], 6, "UNTRUSTED_INSTRUCTIONS_IN_EVIDENCE"),
                 (["EXSEMI_Q3_10Q_COMPACT"], 0, "PRIOR_NOT_CHECKED"))
        for refs, calls, reason in cases:
            with self.subTest(reason=reason):
                request = w.request(refs, issuer_id=EXSEMI, job_id=f"job:{reason}", context=context, tool_calls=calls)
                result = w.assessor(RuleBaselineModel(w.clock)).assess(request)
                _, after = accept(state, result, profile_hash=PROFILE, now_ms=w.clock())
                self.assertEqual(after["evidence_gate"], "UNKNOWN")
                self.assertIn(reason, after["gate_reasons"])
        request = w.request(["EXSEMI_Q3_10Q_COMPACT"], issuer_id=EXSEMI, job_id="job:agent", context=context)
        _, after = accept(state, w.assessor(RuleBaselineModel(w.clock)).assess(request), profile_hash=PROFILE,
                          now_ms=w.clock())
        self.assertEqual(after["evidence_gate"], "CLEAR")  # the agent checked the earlier filing

    def test_feature_rows_are_point_in_time_and_carry_no_trade_fields(self):
        result = self.assess(["EXSEMI_Q3_8K"])
        row = feature_row(result).read()
        r = result.read()
        self.assertEqual(row["as_of_ms"], r["cutoff_ms"])
        self.assertGreaterEqual(row["available_ms"], row["as_of_ms"])
        self.assertEqual((row["impact_ordinal"], row["n_falsifiers_fired"], row["confidence_calibrated"]), (0, 1, False))
        self.assertEqual(forbidden_key_paths(row), [])

    def test_feature_availability_is_completion_time_not_cutoff(self):
        request = self.w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="job:queued", context=self.context)
        cutoff = request.read()["cutoff_ms"]
        self.w.clock.advance(600_000)  # the job waited ten minutes before it ran
        model = ScriptedModel(self.w.clock, [{"latency_ms": 100, "output": {"action": "FINISH", "claims": [],
                                                                           "notes": "queued"}}])
        result = self.w.assessor(model).assess(request)
        r, row = result.read(), feature_row(result).read()
        self.assertEqual((r["started_ms"], r["completed_ms"]), (cutoff + 600_000, cutoff + 600_100))
        self.assertEqual((row["as_of_ms"], row["available_ms"]), (cutoff, cutoff + 600_100))
        self.assertGreater(row["available_ms"], cutoff + r["budget_used"]["elapsed_ms"])  # the old, look-ahead date

    def test_state_and_review_jobs_persist_through_the_store_port(self):
        from larp.intelligence.demo import _persist
        result = self.assess(["EXSEMI_Q3_8K"])
        decision, state = accept(self.state, result, profile_hash=PROFILE, now_ms=self.w.clock())
        persisted = _persist(self.w, EXSEMI, self.state, decision, state, result.read())
        self.assertEqual(persisted["receipt"]["status"], "COMMITTED")
        self.assertEqual(self.w.store.read_state(EXSEMI).read(), state)
        self.assertTrue(all(job["job_id"] in self.w.store.jobs for job in persisted["batch"]["jobs"]))
        self.assertIsInstance(self.w.store, MemoryEvidenceStore)


if __name__ == "__main__":
    unittest.main()

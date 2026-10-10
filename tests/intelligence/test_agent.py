"""Bounded evidence agent behind assess(Document) -> Document. Synthetic world, fake models only."""

import json
import unittest

from larp.contracts import ContractError, Document
from larp.intelligence.common import FORBIDDEN_KEYS, forbidden_key_paths
from larp.intelligence.models import RuleBaselineModel, ScriptedModel
from larp.intelligence.scenarios import EXMEM, EXSEMI, build_world, make_model, prior_thesis


def compatible_with_runtime_schema(request: Document, result: Document, now_ms: int) -> None:
    """Copy of the checks in larp/runtime/schema.py on origin/codex/runtime-audit-platform @ 955cfc2
    (assessment_request / assessment_result), kept here so this branch tests compatibility without
    importing another owner's unmerged module."""
    r, a = request.read(), result.read()
    if (r.get("schema"), type(r["cutoff_ms"])) != ("AssessmentRequest.v1", int) or r["cutoff_ms"] > now_ms:
        raise ContractError("request")
    budget = r["budget"]
    if not (0 <= budget["tool_calls"] <= 6 and 0 < budget["deadline_ms"] <= 60000):
        raise ContractError("budget")
    for ref in r["evidence_refs"]:
        if not ref["source"] or ref["quality"] not in ("VALID", "MISSING", "STALE", "UNKNOWN", "SYNTHETIC"):
            raise ContractError("ref")
        if ref["observed_ms"] > r["cutoff_ms"] or ref["available_ms"] > r["cutoff_ms"] or len(ref["content_hash"]) != 64:
            raise ContractError("ref time/hash")
    for key in ("job_id", "run_id", "issuer_id", "context_hash", "policy_profile_hash"):
        if a.get(key) != r.get(key):
            raise ContractError("identity")
    if a.get("schema") != "AssessmentResult.v1" or type(a["expiry_ms"]) is not int or a["expiry_ms"] <= now_ms:
        raise ContractError("expiry")
    if {"orders", "side", "targets", "buy", "sell"} & {k.lower() for k in a}:
        raise ContractError("authority")
    for key in ("model_hash", "prompt_hash", "rationale", "model_io"):
        if not a.get(key):
            raise ContractError("provenance")
    for key in ("claims", "novelty", "conflicts", "missingness", "confidence", "falsifiers", "review_requests"):
        if key not in a:
            raise ContractError(f"vocabulary {key}")


class AgentHarness(unittest.TestCase):
    def world(self, *keys):
        self.w = build_world(list(keys))
        self.context = prior_thesis(self.w.config, EXSEMI)
        return self.w

    def assess(self, refs, *, model=None, issuer=EXSEMI, **kwargs):
        kwargs.setdefault("context", self.context)
        request = self.w.request(refs, issuer_id=issuer, job_id=kwargs.pop("job_id", "job:test"), **kwargs)
        model = model or RuleBaselineModel(self.w.clock)
        result = self.w.assessor(model).assess(request)
        self.request_doc = request
        return result.read(), result

    def tools(self, result):
        return [(c["tool"], c["args"].get("metric") or c["args"].get("name"), c["status"])
                for c in result["model_io"]["tool_calls"]]


class DemonstrationTraceTests(AgentHarness):
    def test_autonomous_tool_selection_and_thesis_revision(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        result, doc = self.assess(["EXSEMI_Q3_8K"])
        self.assertEqual(result["status"], "ASSESSED")
        self.assertEqual(self.tools(result), [("fetch_document", "exsm-ex991-q3.htm", "OK"),
                                              ("prior_context", "revenue", "OK"),
                                              ("prior_context", "gross_margin", "NO_PRIOR"),
                                              ("compare_facts", "revenue", "OK")])
        thesis = result["proposed_thesis"]
        self.assertEqual((thesis["previous_version"], thesis["version"]), (3, 4))
        self.assertEqual((thesis["previous_status"], thesis["status"]), ("INTACT", "BROKEN"))
        self.assertEqual(thesis["fired_falsifiers"], ["F-REVENUE-GUIDANCE-CUT"])
        types = {f["type"] for f in result["findings"]}
        self.assertTrue({"GUIDANCE_LOWERED", "REPORTED_ABOVE_PRIOR_GUIDANCE"} <= types)
        self.assertEqual(result["impact"], "MIXED")
        novelty = {(c["metric"], c["kind"], c["period"], c["scale_exp10"]): c["novelty"] for c in result["claims"]}
        self.assertEqual(novelty[("revenue", "GUIDANCE", "FY2027-Q4", 9)], "CHANGED")
        self.assertEqual(novelty[("revenue", "REPORTED", "FY2027-Q2", 6)], "UNCHANGED")
        self.assertIn("PRIOR_MISSING:gross_margin:REPORTED:FY2027-Q3", result["missingness"])
        self.assertEqual({r["reason"] for r in result["review_requests"]}, {"AWAIT_COMPARISON_BASIS"})
        self.assertLessEqual(result["budget_used"]["tool_calls"], 6)
        self.assertLessEqual(len(result["rationale"].split(". ")), 3)
        self.assertFalse(result["confidence"]["calibrated"])
        compatible_with_runtime_schema(self.request_doc, doc, self.w.clock())

    def test_simple_baseline_cannot_see_the_guidance_cut(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        result, _ = self.assess(["EXSEMI_Q3_8K"], tool_calls=0)
        self.assertEqual(result["budget_used"]["tool_calls"], 0)
        self.assertNotIn("GUIDANCE_LOWERED", {f["type"] for f in result["findings"]})
        self.assertEqual(result["proposed_thesis"]["status"], "UNKNOWN")
        self.assertIn("EXHIBIT_NOT_LOADED:0009900001-26-000187:exsm-ex991-q3.htm", result["missingness"])
        self.assertEqual({f["falsifier_id"]: f["state"] for f in result["falsifiers"]}["F-REVENUE-GUIDANCE-CUT"], "UNKNOWN")

    def test_justified_abstention_on_contradiction_with_prior_filing(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K", "EXSEMI_Q3_8KA")
        result, doc = self.assess(["EXSEMI_Q3_8KA"])
        self.assertEqual((result["status"], result["reasons"]), ("ABSTAIN", ["CONFLICTING_EVIDENCE"]))
        self.assertEqual([(c["metric"], c["period"]) for c in result["conflicts"]], [("revenue", "FY2027-Q3")])
        self.assertEqual(result["conflicts"][0]["accessions"], ["0009900001-26-000187", "0009900001-26-000190"])
        self.assertIsNone(result["proposed_thesis"])
        self.assertEqual(result["claims"], [])
        self.assertIn("CONFLICT_RESOLUTION", {r["reason"] for r in result["review_requests"]})
        self.assertEqual(result["confidence"]["level"], "UNKNOWN")
        self.assertIn("prior_context", [c["tool"] for c in result["model_io"]["tool_calls"]])
        compatible_with_runtime_schema(self.request_doc, doc, self.w.clock())


class EvidenceSemanticsTests(AgentHarness):
    def test_missing_prior_guidance_stays_missing_and_no_consensus_is_invented(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K", "EXSEMI_FY28_GUIDE_8K")
        result, _ = self.assess(["EXSEMI_FY28_GUIDE_8K"])
        self.assertEqual(result["status"], "ASSESSED")
        claim = next(c for c in result["claims"] if c["kind"] == "GUIDANCE")
        self.assertEqual((claim["period"], claim["novelty"]), ("FY2028-Q1", "NO_PRIOR_AVAILABLE"))
        self.assertIn("PRIOR_MISSING:revenue:GUIDANCE:FY2028-Q1", result["missingness"])
        self.assertEqual({f["falsifier_id"]: f["state"] for f in result["falsifiers"]}["F-REVENUE-GUIDANCE-CUT"], "UNKNOWN")
        self.assertEqual(result["proposed_thesis"]["status"], "UNKNOWN")
        visible = json.dumps({k: v for k, v in result.items() if k != "model_io"}).lower()
        self.assertNotIn("consensus", visible)
        self.assertNotIn("estimate", visible)
        self.assertIn("no earlier comparison point", result["rationale"].lower())

    def test_duplicate_evidence_counts_once(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        single, _ = self.assess(["EXSEMI_Q3_8K"], job_id="job:a")
        double, _ = self.assess(["EXSEMI_Q3_8K", "EXSEMI_Q3_8K"], job_id="job:a")
        self.assertEqual(len(double["evidence_used"]), 1)
        self.assertEqual(double["claims"], single["claims"])
        self.assertEqual(double["assessment_key"], single["assessment_key"])

    def test_foreign_issuer_items_do_not_apply_and_currency_is_kept(self):
        self.world("EXMEM_Q3_6K")
        result, _ = self.assess(["EXMEM_Q3_6K"], issuer=EXMEM, context=prior_thesis(self.w.config, EXMEM))
        self.assertEqual(result["status"], "ASSESSED")
        self.assertEqual({c["unit"] for c in result["claims"] if c["kind"] != "EVENT"}, {"KRW"})
        self.assertEqual({f["falsifier_id"]: f["state"] for f in result["falsifiers"]}["F-ITEM-4.02"], "NOT_APPLICABLE")
        self.assertEqual(result["instrument_scope"]["token_underlying_status"], "UNVERIFIED")

    def test_restatement_fires_declared_falsifiers(self):
        self.world("EXSEMI_402_8K")
        result, _ = self.assess(["EXSEMI_402_8K"])
        states = {f["falsifier_id"]: f["state"] for f in result["falsifiers"]}
        self.assertEqual((states["F-ITEM-4.02"], states["F-RESTATEMENT"]), ("FIRED", "FIRED"))
        self.assertEqual((result["impact"], result["severity"], result["proposed_thesis"]["status"]), ("ADVERSE", 3, "BROKEN"))

    def test_point_in_time_index_hides_later_filings(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        request = self.w.request(["EXSEMI_Q2_8K"], issuer_id=EXSEMI, job_id="job:pit", context=self.context).read()
        request["cutoff_ms"] = self.w.record("EXSEMI_Q3_8K")["available_ms"] - 1
        result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(Document.from_dict(request)).read()
        accessions = {c["source"]["accession"] for c in result["claims"]}
        self.assertEqual(accessions, {"0009900001-26-000101"})
        self.assertNotIn("0009900001-26-000187", json.dumps(result["model_io"]))

    def test_future_or_tampered_refs_are_not_used(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        request = self.w.request(["EXSEMI_Q3_8K", "EXSEMI_Q2_8K"], issuer_id=EXSEMI, job_id="job:refs",
                                 context=self.context).read()
        request["evidence_refs"][0]["available_ms"] = request["cutoff_ms"] + 1
        request["evidence_refs"][1]["content_hash"] = "0" * 64
        result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(Document.from_dict(request)).read()
        self.assertEqual((result["status"], result["reasons"]), ("UNAVAILABLE", ["NO_USABLE_EVIDENCE"]))
        self.assertTrue(any(m.startswith("FUTURE_EVIDENCE_REF") for m in result["missingness"]))
        self.assertTrue(any(m.startswith("EVIDENCE_HASH_MISMATCH") for m in result["missingness"]))

    def test_superseded_revision_ref_assesses_the_latest_revision(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        old = self.w.record("EXSEMI_Q3_8K")
        accession, name = old["accession"], "exsm-ex991-q3.htm"
        spec = next(s for s in self.w.source.filings[9900001] if s["accession"] == accession)
        content = next(d["content"] for d in spec["documents"] if d["name"] == name)
        self.w.source.replace_document(accession, name, content + b"<p>Clarified.</p>")
        self.w.ingestor.poll(EXSEMI, recheck=frozenset({accession}))
        request = self.w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="job:rev", context=self.context).read()
        request["evidence_refs"] = [dict(request["evidence_refs"][0], record_id=old["record_id"], content_hash=old["content_hash"])]
        result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(Document.from_dict(request)).read()
        self.assertIn(f"REVISION_SUPERSEDED_REF:{accession}", result["missingness"])
        self.assertEqual(result["evidence_used"][0]["record_id"], self.w.record("EXSEMI_Q3_8K")["record_id"])


class RequestValidationTests(AgentHarness):
    def test_stale_context_and_budget_violations_are_rejected_before_any_model_call(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        base = self.w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="job:v", context=self.context).read()
        cases = {
            "STALE_OR_MISMATCHED_CONTEXT_HASH": dict(base, context_hash="f" * 64),
            "BUDGET_EXCEEDS_DECLARATION": dict(base, budget={"tool_calls": 7, "deadline_ms": 60000}),
            "TOOL_NOT_ALLOWLISTED": dict(base, allowed_tools=["fetch_document", "web_search"]),
            "CUTOFF_IN_FUTURE": dict(base, cutoff_ms=self.w.clock() + 1),
            "UNKNOWN_ISSUER": dict(base, issuer_id="NVDA"),
            "SCHEMA": dict(base, schema="AssessmentRequest.v0"),
        }
        cases["BUDGET_EXCEEDS_DECLARATION_TIME"] = dict(base, budget={"tool_calls": 6, "deadline_ms": 60001})
        for reason, request in cases.items():
            with self.subTest(reason=reason):
                model = ScriptedModel(self.w.clock, [{"output": {"action": "FINISH", "claims": [], "notes": "x"}}])
                result = self.w.assessor(model).assess(Document.from_dict(request)).read()
                self.assertEqual(result["status"], "REJECTED_REQUEST")
                self.assertEqual(result["reasons"], [reason.replace("_TIME", "")])
                self.assertEqual(model.calls, 0)

    def test_stale_context_after_thesis_update(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        old_context = prior_thesis(self.w.config, EXSEMI, version=2)
        request = self.w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="job:old", context=old_context).read()
        request["context"] = self.context  # thesis moved on; the hash no longer matches
        result = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(Document.from_dict(request)).read()
        self.assertEqual(result["reasons"], ["STALE_OR_MISMATCHED_CONTEXT_HASH"])


class BudgetAndFailureTests(AgentHarness):
    def test_disallowed_tool_requests_are_recorded_errors(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        script = [{"output": {"action": "CALL_TOOL", "tool": name, "args": {"url": "https://attacker.invalid"}}}
                  for name in ("http_get", "sign_transaction", "broadcast")]
        script.append({"output": {"action": "FINISH", "claims": [], "notes": "done"}})
        result, _ = self.assess(["EXSEMI_Q3_8K"], model=ScriptedModel(self.w.clock, script))
        self.assertEqual([c["error"] for c in result["model_io"]["tool_calls"]], ["TOOL_NOT_ALLOWED"] * 3)
        self.assertEqual(result["status"], "ASSESSED")

    def test_tool_budget_is_never_exceeded(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        looping = ScriptedModel(self.w.clock, [{"latency_ms": 10, "output": {
            "action": "CALL_TOOL", "tool": "prior_context", "args": {"metric": "revenue"}}}])
        result, _ = self.assess(["EXSEMI_Q3_8K"], model=looping, tool_calls=3)
        self.assertEqual(result["budget_used"]["tool_calls"], 3)
        self.assertIn("TOOL_BUDGET_EXHAUSTED", result["missingness"])
        self.assertEqual(looping.calls, 4)

    def test_time_budget_stops_a_slow_tool_loop(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        slow = ScriptedModel(self.w.clock, [{"latency_ms": 25_000, "output": {
            "action": "CALL_TOOL", "tool": "prior_context", "args": {"metric": "revenue"}}}])
        result, _ = self.assess(["EXSEMI_Q3_8K"], model=slow)
        self.assertEqual((result["status"], result["reasons"]), ("UNAVAILABLE", ["MODEL_TIMEOUT"]))
        self.assertLessEqual(result["budget_used"]["elapsed_ms"], 60001)

    def test_missing_artifact_is_a_tool_error_not_a_crash(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        sha = next(d["text_sha256"] for d in self.w.record("EXSEMI_Q3_8K")["documents"] if d["role"] == "EXHIBIT")
        del self.w.artifacts.blobs[sha]
        result, _ = self.assess(["EXSEMI_Q3_8K"])
        self.assertEqual(result["status"], "ASSESSED")
        self.assertIn("TOOL_ERROR:fetch_document:ARTIFACT_MISSING", result["missingness"])
        self.assertEqual(result["proposed_thesis"]["status"], "UNKNOWN")
        self.assertEqual(result["confidence"]["level"], "LOW")

    def test_corrupted_artifact_and_reader_exceptions_are_contained(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        sha = next(d["text_sha256"] for d in self.w.record("EXSEMI_Q3_8K")["documents"] if d["role"] == "EXHIBIT")
        self.w.artifacts.blobs[sha] = b"tampered"
        result, _ = self.assess(["EXSEMI_Q3_8K"])
        self.assertIn("TOOL_ERROR:fetch_document:ARTIFACT_INTEGRITY_ERROR", result["missingness"])
        reader = self.w.reader
        original = reader.text

        def flaky(digest):
            if digest != next(d["text_sha256"] for d in self.w.record("EXSEMI_Q3_8K")["documents"] if d["role"] == "PRIMARY"):
                raise RuntimeError("synthetic disk error")
            return original(digest)

        reader.text = flaky
        assessor = self.w.assessor(RuleBaselineModel(self.w.clock))
        assessor.reader = reader
        request = self.w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="job:flaky", context=self.context)
        result = assessor.assess(request).read()
        self.assertIn("TOOL_ERROR:fetch_document:TOOL_EXCEPTION:RuntimeError", result["missingness"])

    def test_model_timeout_error_and_invalid_output(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        cases = (
            (make_model(self.w, "timeout"), "UNAVAILABLE", "MODEL_TIMEOUT"),
            (ScriptedModel(self.w.clock, [{"error": "HTTP 500"}]), "UNAVAILABLE", "MODEL_ERROR"),
            (ScriptedModel(self.w.clock, [{"output": {"action": "FINISH", "claims": [], "notes": "x", "score": 0.7}}]),
             "ABSTAIN", "MODEL_OUTPUT_INVALID"),
            (ScriptedModel(self.w.clock, [{"output": {"action": "FINISH", "claims": [], "extra": 1}}]),
             "ABSTAIN", "MODEL_OUTPUT_SCHEMA"),
        )
        for model, status, reason in cases:
            with self.subTest(reason=reason):
                result, doc = self.assess(["EXSEMI_Q3_8K"], model=model)
                self.assertEqual((result["status"], result["reasons"]), (status, [reason]))
                self.assertIsNone(result["proposed_thesis"])
                self.assertEqual(result["claims"], [])
                self.assertTrue(result["review_requests"])

        class Exploding:
            identity = RuleBaselineModel(self.w.clock).identity

            def step(self, request, remaining_ms):
                raise RuntimeError("adapter defect")

        result, _ = self.assess(["EXSEMI_Q3_8K"], model=Exploding())
        self.assertEqual((result["status"], result["reasons"]), ("UNAVAILABLE", ["MODEL_ERROR"]))


class InjectionAndAuthorityTests(AgentHarness):
    def test_prompt_injection_is_reported_and_has_no_authority(self):
        self.world("EXSEMI_INJECTION_8K")
        result, _ = self.assess(["EXSEMI_INJECTION_8K"])
        self.assertEqual(result["status"], "ASSESSED")
        self.assertIn("UNTRUSTED_INSTRUCTIONS_IN_EVIDENCE", result["missingness"])
        self.assertEqual(forbidden_key_paths({k: v for k, v in result.items() if k != "model_io"}), [])
        self.assertNotIn("attacker.invalid", json.dumps(result["model_io"]["tool_calls"]))
        self.assertNotIn("BUY", result["rationale"])

    def test_compliant_model_outputs_are_rejected(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K", "EXSEMI_INJECTION_8K")
        for spec, refs, reason in (("trade_field", ["EXSEMI_INJECTION_8K"], "MODEL_OUTPUT_TRADE_FIELD"),
                                   ("fabricated_claim", ["EXSEMI_Q3_8K"], "UNSUPPORTED_CLAIM"),
                                   ("consensus_claim", ["EXSEMI_Q3_8K"], "UNSUPPORTED_CLAIM")):
            with self.subTest(spec=spec):
                result, _ = self.assess(refs, model=make_model(self.w, spec))
                self.assertEqual((result["status"], result["reasons"]), ("ABSTAIN", [reason]))
                self.assertEqual(result["claims"], [])
                self.assertEqual(forbidden_key_paths({k: v for k, v in result.items() if k != "model_io"}), [])
        result, _ = self.assess(["EXSEMI_Q3_8K"], model=make_model(self.w, "consensus_claim"))
        self.assertEqual(result["rejected_claims"][0]["reason"], "KIND_NOT_ALLOWED")

    def test_results_never_carry_trade_vocabulary_or_probabilities(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        result, _ = self.assess(["EXSEMI_Q3_8K"])
        public = {k: v for k, v in result.items() if k != "model_io"}
        self.assertEqual(forbidden_key_paths(public), [])
        self.assertNotIn("probability", json.dumps(public).lower())
        self.assertTrue({"buy", "sell", "orders", "side"} <= FORBIDDEN_KEYS)

    def test_identical_inputs_give_identical_bytes(self):
        payloads = []
        for _ in range(2):
            self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
            payloads.append(self.assess(["EXSEMI_Q3_8K"])[1].payload)
        self.assertEqual(payloads[0], payloads[1])


if __name__ == "__main__":
    unittest.main()

"""Bounded evidence agent behind assess(Document) -> Document. Synthetic world, fake models only."""

import json
import threading
import time
import unittest

from larp.contracts import ContractError, Document
from larp.intelligence.agent import EvidenceAssessor, context_hash
from larp.intelligence.common import FORBIDDEN_KEYS, forbidden_key_paths
from larp.intelligence.features import feature_row
from larp.intelligence.gate import accept, initial_state
from larp.intelligence.models import RuleBaselineModel, ScriptedModel
from larp.intelligence.scenarios import (
    EXMEM, EXSEMI, PROFILE, build_world, cover, doc, make_model, prior_thesis,
)

Q4_GUIDE = "For the fourth quarter of fiscal 2027, the company expects revenue to be ${} billion."


def eight_k(accession, acceptance, lines, items=("7.01",)):
    """A test-only synthetic 8-K whose primary document carries `lines` (not part of the evaluation pack)."""
    return dict(cik=9900001, accession=accession, form="8-K", items=list(items), acceptance=acceptance, documents=[
        doc(f"exsm-8k-{accession[-6:]}.htm", "8-K", cover("Example Semiconductor Corp", "8-K", list(items), lines))])


# Common "no event" boilerplate (PR #4 review, R3 re-check): negation before, after or governing the keyword.
NEGATED_BOILERPLATE = (
    ("IMPAIRMENT", "The company recorded no impairment in the quarter."),
    ("IMPAIRMENT", "An impairment charge was not required in the quarter."),
    ("IMPAIRMENT", "Management concluded that goodwill impairment was not necessary."),
    ("IMPAIRMENT", "We did not identify any events or circumstances that would indicate an impairment."),
    ("RESTATEMENT", "The Audit Committee concluded that a restatement of prior financial statements is not required."),
)
# Modal, conditional and forward-looking boilerplate (risk factors, outlook): possible or planned, not reported.
HYPOTHETICAL_BOILERPLATE = (
    ("IMPAIRMENT", "Goodwill impairment could result if the operating results of the segment decline."),
    ("IMPAIRMENT", "We expect to record an impairment charge in the fourth quarter."),
    ("RESTATEMENT", "Any future restatement of our financial statements would harm investor confidence."),
    ("DELISTING", "There is a risk that our common stock could be delisted from the exchange."),
    ("CYBERSECURITY_INCIDENT", "A cybersecurity incident could disrupt our operations."),
    ("OFFICER_DEPARTURE", "Our Chief Executive Officer may resign at any time."),
)
RISK_LINES = [HYPOTHETICAL_BOILERPLATE[0][1], HYPOTHETICAL_BOILERPLATE[5][1]]
NEW_RISK = "We expect to record a goodwill impairment charge in the fourth quarter of fiscal 2027."
# Expected verifier reason for a claim that the statement is an occurred issuer event (IDEA-031: the reason names
# the statement's assertion class instead of the former single EVENT_HYPOTHETICAL).
UNASSERTED = {"NEGATED_BOILERPLATE": (NEGATED_BOILERPLATE, lambda s: "EVENT_NEGATED"),
              "HYPOTHETICAL_BOILERPLATE": (HYPOTHETICAL_BOILERPLATE, lambda s: "EVENT_NOT_OCCURRED:" + (
                  "FORECAST" if s.startswith("We expect") else "CONDITIONAL_RISK"))}

EXTRA = {
    "G1_36": eight_k("0009900001-26-000301", "2026-07-01T20:00:00+00:00", [Q4_GUIDE.format("36.0")]),
    "G2_32": eight_k("0009900001-26-000302", "2026-08-15T20:00:00+00:00", [Q4_GUIDE.format("32.0")]),
    "G2_SPLIT": eight_k("0009900001-26-000304", "2026-08-15T20:00:00+00:00",
                        [Q4_GUIDE.format("32.0"), Q4_GUIDE.format("33.5")]),
    "G3_34": eight_k("0009900001-26-000303", "2026-09-20T20:00:00+00:00", [Q4_GUIDE.format("34.0")]),
    "NEGATED_BOILERPLATE": eight_k("0009900001-26-000305", "2026-10-02T20:00:00+00:00",
                                   [sentence for _, sentence in NEGATED_BOILERPLATE], items=("2.02",)),
    "HYPOTHETICAL_BOILERPLATE": eight_k("0009900001-26-000306", "2026-10-02T21:00:00+00:00",
                                        [sentence for _, sentence in HYPOTHETICAL_BOILERPLATE], items=("8.01",)),
    # The same risk-factor statements a month apart, then again with one new statement.
    "RISK_PRIOR": eight_k("0009900001-26-000307", "2026-09-01T20:00:00+00:00", RISK_LINES, items=("8.01",)),
    "RISK_REPEATED": eight_k("0009900001-26-000308", "2026-10-03T20:00:00+00:00", RISK_LINES, items=("8.01",)),
    "RISK_NEW": eight_k("0009900001-26-000309", "2026-10-03T21:00:00+00:00", RISK_LINES + [NEW_RISK], items=("8.01",)),
}


def cite(state, sentence):
    """A span for `sentence` in whichever loaded document contains it."""
    d = next(x for x in state["documents"] if sentence in x["excerpt"])
    start = d["excerpt"].index(sentence)
    return {"doc": d["text_sha256"], "start": start, "end": start + len(sentence), "text": sentence}


def comparisons(result):
    """Every comparison the agent computed, from the tool results it saw (kept for audit)."""
    last = result["model_io"]["steps"][-1]["request"]["input"]
    return [c for t in last["tool_results"] if t["tool"] == "compare_facts" for c in t["comparisons"]]


def compatible_with_runtime_schema(request: Document, result: Document, now_ms: int) -> None:
    """The runtime's own boundary checks (larp/runtime/schema.py, integrated on this branch) plus the result
    vocabulary the integration adapters read."""
    from larp.runtime.schema import assessment_request, assessment_result
    r, a = request.read(), result.read()
    assessment_request(request, r["run_id"], r["policy_profile_hash"], now_ms)
    assessment_result(result, request, now_ms)
    for key in ("claims", "novelty", "conflicts", "missingness", "confidence", "falsifiers", "review_requests",
                "event_statements", "retained_facts", "coverage"):
        if key not in a:
            raise ContractError(f"vocabulary {key}")


class AgentHarness(unittest.TestCase):
    def world(self, *keys):
        self.w = build_world(list(keys), extra_filings=EXTRA)
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


class GuidanceBasisTests(AgentHarness):
    def test_only_the_latest_prior_guidance_classifies_an_update(self):
        self.world("G1_36", "G2_32", "G3_34")  # 36.0 -> 32.0 -> 34.0 for the same quarter
        result, _ = self.assess(["G3_34"])
        self.assertEqual(result["status"], "ASSESSED")
        types = {f["type"] for f in result["findings"]}
        self.assertIn("GUIDANCE_RAISED", types)
        self.assertNotIn("GUIDANCE_LOWERED", types)  # versus the superseded 36.0, kept only for audit
        states = {f["falsifier_id"]: f["state"] for f in result["falsifiers"]}
        self.assertEqual(states["F-REVENUE-GUIDANCE-CUT"], "NOT_FIRED")
        self.assertEqual(result["proposed_thesis"]["status"], "INTACT")
        audit = {(c["relation"], c["applicable"], c.get("not_applicable")) for c in comparisons(result)}
        self.assertEqual(audit, {("HIGHER", True, None), ("LOWER", False, "SUPERSEDED_PRIOR_GUIDANCE")})

    def test_contemporaneous_conflicting_guidance_gives_no_basis(self):
        self.world("G1_36", "G2_SPLIT", "G3_34")  # the latest prior filing states 32.0 and 33.5
        result, doc = self.assess(["G3_34"])
        self.assertIn("PRIOR_GUIDANCE_CONFLICT:revenue:FY2027-Q4", result["missingness"])
        self.assertFalse({"GUIDANCE_RAISED", "GUIDANCE_LOWERED"} & {f["type"] for f in result["findings"]})
        self.assertEqual({f["falsifier_id"]: f["state"] for f in result["falsifiers"]}["F-REVENUE-GUIDANCE-CUT"],
                         "UNKNOWN")
        self.assertEqual(result["proposed_thesis"]["status"], "UNKNOWN")
        self.assertIn("CONFLICT_RESOLUTION", {r["reason"] for r in result["review_requests"]})
        self.assertEqual({c.get("not_applicable") for c in comparisons(result)},
                         {"CONFLICTING_PRIOR_GUIDANCE", "SUPERSEDED_PRIOR_GUIDANCE"})
        state = dict(initial_state(EXSEMI, PROFILE), context=self.context, context_hash=context_hash(self.context))
        _, after = accept(state, doc, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertNotEqual(after["evidence_gate"], "CLEAR")
        self.assertIn("PRIOR_GUIDANCE_CONFLICT:revenue:FY2027-Q4", after["gate_reasons"])


class ClaimBindingTests(AgentHarness):
    def finish_with(self, claims):
        return ScriptedModel(self.w.clock, [{"output": {"action": "FINISH", "claims": claims, "notes": "x"}}])

    def assert_abstains(self, result, reason):
        self.assertEqual((result["status"], result["reasons"]), ("ABSTAIN", ["UNSUPPORTED_CLAIM"]))
        self.assertEqual([r["reason"] for r in result["rejected_claims"]], [reason])
        self.assertIsNone(result["proposed_thesis"])
        self.assertEqual(result["claims"], [])
        self.assertIn("REASSESS_AFTER_ABSTENTION", {r["reason"] for r in result["review_requests"]})

    def test_malformed_nested_claims_abstain_instead_of_crashing(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        cases = {
            "SOURCE_MALFORMED": {"kind": "REPORTED", "source": "oops"},
            "SPAN_MALFORMED": {"kind": "REPORTED", "metric": "revenue", "span": "x"},
            "RANGE_MALFORMED": {"kind": "REPORTED", "metric": "revenue", "range": 1},
            "UNIT_MALFORMED": {"kind": "REPORTED", "metric": "revenue", "unit": ["USD"]},
            "METRIC_MALFORMED": {"kind": "EVENT", "metric": {"IMPAIRMENT": 1}},
            "CLAIM_MALFORMED": 7,
        }
        cases["SPAN_MALFORMED_DOC"] = {"kind": "EVENT", "metric": "IMPAIRMENT",
                                       "span": {"doc": ["a"], "start": 0, "end": 1, "text": "x"}}
        for name, claim in cases.items():
            with self.subTest(case=name):
                result, doc = self.assess(["EXSEMI_Q3_8K"], model=self.finish_with([claim]), job_id=f"job:{name}")
                self.assert_abstains(result, name.replace("_DOC", ""))
                compatible_with_runtime_schema(self.request_doc, doc, self.w.clock())

    def test_a_prior_filing_span_cannot_be_passed_off_as_current_evidence(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        old = "Revenue for the second quarter of fiscal 2027 was $30.04 billion."
        current_record = self.w.record("EXSEMI_Q3_8K")

        def claim(source):
            def finish(state):
                c = {"kind": "REPORTED", "metric": "revenue", "period": "FY2027-Q2", "value": "30.04", "unit": "USD",
                     "scale_exp10": 9, "span": cite(state, old), "period_span": None}
                if source is not None:
                    c["source"] = source
                return {"action": "FINISH", "claims": [c], "notes": "x"}
            return ScriptedModel(self.w.clock, [
                {"output": {"action": "CALL_TOOL", "tool": "prior_context", "args": {"metric": "revenue"}}},
                {"output": finish}])

        cases = (({"record_id": current_record["record_id"]}, "SPAN_NOT_IN_SOURCE_RECORD"),
                 (None, "CLAIM_NOT_FROM_ASSESSED_FILING"),
                 ({"accession": current_record["accession"]}, "CLAIM_NOT_FROM_ASSESSED_FILING"))
        for source, reason in cases:
            with self.subTest(source=source):
                result, _ = self.assess(["EXSEMI_Q3_8K"], model=claim(source), job_id=f"job:{reason}:{bool(source)}")
                self.assert_abstains(result, reason)

    def test_a_negated_or_hypothetical_event_claim_abstains_and_creates_no_adverse_finding(self):
        for key, (sentences, reason) in UNASSERTED.items():
            self.world(key)
            state = dict(initial_state(EXSEMI, PROFILE), context=self.context, context_hash=context_hash(self.context))
            for i, (metric, sentence) in enumerate(sentences):
                with self.subTest(sentence=sentence):
                    model = ScriptedModel(self.w.clock, [{"output": lambda st, metric=metric, sentence=sentence: {
                        "action": "FINISH", "notes": "x",
                        "claims": [{"kind": "EVENT", "metric": metric, "span": cite(st, sentence)}]}}])
                    result, doc = self.assess([key], model=model, job_id=f"job:{key}:{i}")
                    self.assert_abstains(result, reason(sentence))
                    self.assertNotIn(metric, {f["type"] for f in result["event_findings"]})
                    _, after = accept(state, doc, profile_hash=PROFILE, now_ms=self.w.clock())
                    self.assertNotIn(metric, {a["type"] for a in after["unresolved_adverse"]})

    def test_the_baseline_finds_no_event_in_negated_or_hypothetical_boilerplate(self):
        for key, (sentences, _) in UNASSERTED.items():
            with self.subTest(world=key):
                self.world(key)
                result, doc = self.assess([key])
                adverse = {metric for metric, _ in sentences}
                self.assertFalse(adverse & {c["metric"] for c in result["claims"] if c["kind"] == "EVENT"})
                self.assertFalse(adverse & {f["type"] for f in result["event_findings"]})
                states = {f["falsifier_id"]: f["state"] for f in result["falsifiers"]}
                self.assertNotEqual(states["F-RESTATEMENT"], "FIRED")
                state = dict(initial_state(EXSEMI, PROFILE), context=self.context,
                             context_hash=context_hash(self.context))
                _, after = accept(state, doc, profile_hash=PROFILE, now_ms=self.w.clock())
                self.assertFalse(adverse & {a["type"] for a in after["unresolved_adverse"]})


class StatementTests(AgentHarness):
    """Statements about events (formerly "hypothetical events") are kept with their semantics, never as findings;
    first-seen ones are sent for bounded review (IDEA-031 S2.1/S2.4)."""

    def outcome(self, refs):
        result, doc = self.assess(refs)
        state = dict(initial_state(EXSEMI, PROFILE), context=self.context, context_hash=context_hash(self.context))
        _, after = accept(state, doc, profile_hash=PROFILE, now_ms=self.w.clock())
        return result, after, feature_row(doc, after).read()

    def test_first_seen_statements_are_kept_reviewed_and_never_adverse(self):
        self.world("HYPOTHETICAL_BOILERPLATE")
        result, after, row = self.outcome(["HYPOTHETICAL_BOILERPLATE"])
        self.assertEqual(result["status"], "ASSESSED")
        self.assertIn(("prior_context", "STATEMENTS", "NO_PRIOR"), self.tools(result))
        self.assertEqual(sorted((h["event"], h["novelty"]) for h in result["event_statements"]),
                         sorted((metric, "FIRST_SEEN") for metric, _ in HYPOTHETICAL_BOILERPLATE))
        self.assertEqual({h["statement"] for h in result["event_statements"]},
                         {sentence for _, sentence in HYPOTHETICAL_BOILERPLATE})
        self.assertEqual({h["semantics"]["assertion"] for h in result["event_statements"]},
                         {"CONDITIONAL_RISK", "FORECAST"})
        # The only finding is the fixture 8-K's own Item 8.01 (impact UNKNOWN); nothing comes from the statements.
        self.assertEqual([(f["type"], f["impact"]) for f in result["findings"]], [("ITEM:8.01", "UNKNOWN")])
        self.assertEqual(after["unresolved_adverse"], [])
        self.assertIn("REVIEW_NEW_STATEMENT", {r["reason"] for r in result["review_requests"]})
        self.assertEqual(after["evidence_gate"], "UNKNOWN")
        self.assertIn("PENDING_STATEMENT_REVIEW", after["gate_reasons"])
        self.assertEqual((row["n_statements_new"], row["n_statements_repeated"]), (6, 0))
        self.assertEqual(row["statement_types_new"], sorted({m for m, _ in HYPOTHETICAL_BOILERPLATE}))

    def test_boilerplate_repeated_from_an_earlier_filing_is_not_new(self):
        self.world("RISK_PRIOR", "RISK_REPEATED")
        result, after, row = self.outcome(["RISK_REPEATED"])
        self.assertEqual({h["novelty"] for h in result["event_statements"]}, {"REPEATED"})
        self.assertNotIn("REVIEW_NEW_STATEMENT", {r["reason"] for r in result["review_requests"]})
        self.assertNotIn("PENDING_STATEMENT_REVIEW", after["gate_reasons"])
        self.assertEqual((row["n_statements_new"], row["n_statements_repeated"]), (0, 2))

    def test_only_the_statement_absent_from_earlier_filings_is_first_seen(self):
        self.world("RISK_PRIOR", "RISK_NEW")
        result, after, row = self.outcome(["RISK_NEW"])
        new = [h for h in result["event_statements"] if h["novelty"] == "FIRST_SEEN"]
        self.assertEqual([(h["event"], h["statement"]) for h in new], [("IMPAIRMENT", NEW_RISK)])
        self.assertEqual(len(result["event_statements"]), 3)
        self.assertNotIn("IMPAIRMENT", {f["type"] for f in result["event_findings"]})
        self.assertIn("PENDING_STATEMENT_REVIEW", after["gate_reasons"])
        self.assertEqual((row["n_statements_new"], row["statement_types_new"]), (1, ["IMPAIRMENT"]))

    def test_a_model_may_claim_a_statement_with_its_label_and_semantics(self):
        self.world("HYPOTHETICAL_BOILERPLATE")
        sentence = HYPOTHETICAL_BOILERPLATE[3][1]
        model = ScriptedModel(self.w.clock, [{"output": lambda st: {
            "action": "FINISH", "notes": "x",
            "claims": [{"kind": "EVENT", "metric": "STATEMENT:DELISTING", "span": cite(st, sentence),
                        "statement": {"assertion": "CONDITIONAL_RISK"}}]}}])
        result, _ = self.assess(["HYPOTHETICAL_BOILERPLATE"], model=model)
        self.assertEqual((result["status"], result["rejected_claims"]), ("ASSESSED", []))
        self.assertIn("STATEMENT:DELISTING", {c["metric"] for c in result["claims"] if c["model_confirmed"]})
        self.assertNotIn("DELISTING", {f["type"] for f in result["event_findings"]})

    def test_a_model_claiming_wrong_statement_semantics_abstains(self):
        self.world("HYPOTHETICAL_BOILERPLATE")
        sentence = HYPOTHETICAL_BOILERPLATE[3][1]
        model = ScriptedModel(self.w.clock, [{"output": lambda st: {
            "action": "FINISH", "notes": "x",
            "claims": [{"kind": "EVENT", "metric": "STATEMENT:DELISTING", "span": cite(st, sentence),
                        "statement": {"assertion": "OCCURRED"}}]}}])
        result, _ = self.assess(["HYPOTHETICAL_BOILERPLATE"], model=model)
        self.assert_abstains(result, "EVENT_SEMANTICS_MISMATCH")
        self.assertTrue(result["retained_facts"])  # supported harness facts kept for audit, status unchanged
        self.assertFalse(result["coverage"]["complete"] and result["status"] == "ASSESSED")


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
        self.assertLessEqual(result["budget_used"]["elapsed_ms"], 60000)

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


class DeadlineTests(AgentHarness):
    def test_a_blocked_evidence_read_is_abandoned_at_the_deadline(self):
        self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
        release = threading.Event()
        reader = self.w.reader
        original = reader.text

        def blocked(digest):
            release.wait(30)  # a store read that ignores every deadline
            return original(digest)

        reader.text = blocked
        model = ScriptedModel(self.w.clock, [{"output": {"action": "FINISH", "claims": [], "notes": "late"}}])
        assessor = EvidenceAssessor(registry=self.w.registry, reader=reader, model=model, config=self.w.config,
                                    clock_ms=self.w.clock)
        request = self.w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="job:blocked", context=self.context,
                                 deadline_ms=500)
        started = time.monotonic()
        doc = assessor.assess(request)
        waited = time.monotonic() - started
        release.set()
        result = doc.read()
        self.assertLess(waited, 5)  # bounded by the 0.5 s deadline, not by the 30 s read
        self.assertEqual((result["status"], result["reasons"]), ("UNAVAILABLE", ["ASSESSMENT_DEADLINE_EXCEEDED"]))
        self.assertEqual((result["claims"], result["proposed_thesis"]), ([], None))
        self.assertIn("RETRY_AFTER_UNAVAILABLE", {r["reason"] for r in result["review_requests"]})
        compatible_with_runtime_schema(request, doc, self.w.clock())
        for worker in [t for t in threading.enumerate() if t.name == "larp-assess:job:blocked"]:
            worker.join(10)
            self.assertFalse(worker.is_alive())
        self.assertEqual(model.calls, 0)  # after release the abandoned worker made no model call
        state = dict(initial_state(EXSEMI, PROFILE), context=self.context, context_hash=context_hash(self.context))
        decision, after = accept(state, doc, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual((decision, after["evidence_gate"], after["availability"]), ("ACCEPT", "UNKNOWN", "UNAVAILABLE"))


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
        keys = set()

        def collect(value):
            if type(value) is dict:
                keys.update(k.lower() for k in value)
                for item in value.values():
                    collect(item)
            elif type(value) is list:
                for item in value:
                    collect(item)

        collect(public)
        self.assertFalse({k for k in keys if "prob" in k})
        self.assertTrue({"buy", "sell", "orders", "side"} <= FORBIDDEN_KEYS)

    def test_identical_inputs_give_identical_bytes(self):
        payloads = []
        for _ in range(2):
            self.world("EXSEMI_Q2_8K", "EXSEMI_Q3_8K")
            payloads.append(self.assess(["EXSEMI_Q3_8K"])[1].payload)
        self.assertEqual(payloads[0], payloads[1])


if __name__ == "__main__":
    unittest.main()

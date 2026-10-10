"""IDEA-031 AC-L01..L07, L09: statement identity, review lifecycle, corrections, freshness and work bounds."""

import dataclasses
import unittest

from larp.intelligence import lifecycle
from larp.intelligence.agent import context_hash
from larp.intelligence.gate import accept, consume, initial_state, lifecycle_policy_from
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import EXSEMI, PROFILE, build_world, cover, doc, prior_thesis

RISKS = ["A cybersecurity incident could disrupt our operations.",
         "Our Chief Executive Officer may resign at any time.",
         "We expect to record an impairment charge in the fourth quarter of fiscal 2027."]


def eight_k(accession, acceptance, lines, items=("8.01",)):
    return dict(cik=9900001, accession=accession, form="8-K", items=list(items), acceptance=acceptance, documents=[
        doc(f"exsm-8k-{accession[-6:]}.htm", "8-K", cover("Example Semiconductor Corp", "8-K", list(items), lines))])


EXTRA = {
    "RISKS": eight_k("0009900001-26-000401", "2026-10-02T21:00:00+00:00", RISKS),
    "CLEAN": eight_k("0009900001-26-000402", "2026-10-03T21:00:00+00:00",
                     ["The company held its annual meeting of stockholders."]),
    "OCCURRED": eight_k("0009900001-26-000403", "2026-10-04T21:00:00+00:00",
                        ["We recorded a goodwill impairment charge of $1.2 billion in the quarter."]),
}
SIG = lambda text, assertion="CONDITIONAL_RISK", actor="ISSUER", event="CYBERSECURITY_INCIDENT": lifecycle.signature(
    event, {"assertion": assertion, "actor": actor, "temporal": "UNKNOWN", "effective": None}, text)


class Harness(unittest.TestCase):
    def setUp(self):
        self.w = build_world(["RISKS", "CLEAN", "OCCURRED"], extra_filings=EXTRA)
        context = prior_thesis(self.w.config, EXSEMI)
        self.state = dict(initial_state(EXSEMI, PROFILE, lifecycle_policy=lifecycle_policy_from(self.w.config)),
                          context=context, context_hash=context_hash(context))

    def run_one(self, key, state=None, job="job", tool_calls=6, model=None):
        state = state or self.state
        request = self.w.request([key], issuer_id=EXSEMI, job_id=job, context=state["context"], tool_calls=tool_calls)
        result = self.w.assessor(model or RuleBaselineModel(self.w.clock)).assess(request)
        decision, after = accept(state, result, profile_hash=PROFILE, now_ms=self.w.clock())
        self.assertEqual(decision, "ACCEPT", result.read()["status"])
        return result.read(), after


class ReviewLoopTests(Harness):
    def test_l01_same_document_rereview_is_acknowledged_not_an_endless_loop(self):
        first, state = self.run_one("RISKS", job="j1")
        self.assertEqual({s["novelty"] for s in first["event_statements"]}, {"FIRST_SEEN"})
        self.assertIn("REVIEW_NEW_STATEMENT", {r["reason"] for r in first["review_requests"]})
        self.assertEqual({s["status"] for s in state["statements"].values()}, {"PENDING_REVIEW"})
        self.assertIn("PENDING_STATEMENT_REVIEW", state["gate_reasons"])
        self.w.clock.advance(6 * 3_600_000)
        second, state = self.run_one("RISKS", state=state, job="j2")
        self.assertEqual({s["novelty"] for s in second["event_statements"]}, {"ALREADY_SEEN"})
        self.assertNotIn("REVIEW_NEW_STATEMENT", {r["reason"] for r in second["review_requests"]})
        self.assertEqual({s["status"] for s in state["statements"].values()}, {"ACKNOWLEDGED"})
        self.assertNotIn("PENDING_STATEMENT_REVIEW", state["gate_reasons"])
        ids = set(state["statements"])
        self.w.clock.advance(6 * 3_600_000)
        third, state = self.run_one("RISKS", state=state, job="j3")
        self.assertEqual(set(state["statements"]), ids)  # stable identity, nothing re-opened
        self.assertFalse([r for r in third["review_requests"] if r["reason"] == "REVIEW_NEW_STATEMENT"])

    def test_l05_unrelated_clean_document_does_not_erase_pending_concerns(self):
        _, state = self.run_one("RISKS", job="j1")
        _, state = self.run_one("OCCURRED", state=state, job="j2")
        self.assertEqual(state["evidence_gate"], "ADVERSE")
        self.w.clock.advance(1000)
        _, state = self.run_one("CLEAN", state=state, job="j3")
        self.assertEqual(state["evidence_gate"], "ADVERSE")
        self.assertIn("IMPAIRMENT", {a["type"] for a in state["unresolved_adverse"]})
        self.assertIn("PENDING_REVIEW", {s["status"] for s in state["statements"].values()})

    def test_l06_clear_ages_to_stale_and_expired_input_cannot_refresh_it(self):
        result, state = self.run_one("CLEAN", job="j1")
        self.assertEqual(state["evidence_gate"], "CLEAR", state["gate_reasons"])
        until = state["assessed_until_ms"]
        self.assertEqual(until, result["expiry_ms"])
        self.assertEqual(consume(state, until - 1)["evidence_gate"], "CLEAR")
        self.assertEqual(consume(state, until)["evidence_gate"], "STALE")
        self.w.clock.advance(1000)
        request = self.w.request(["CLEAN"], issuer_id=EXSEMI, job_id="j2", context=state["context"])
        late = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(request)
        decision, after = accept(state, late, profile_hash=PROFILE, now_ms=late.read()["expiry_ms"] + 1)
        self.assertEqual(decision, "REJECT_EXPIRED")
        self.assertEqual(after["last_rejection"]["decision"], "REJECT_EXPIRED")
        self.assertEqual(after["assessed_until_ms"], until)
        self.assertEqual(consume(after, late.read()["expiry_ms"] + 1)["evidence_gate"], "STALE")


class CorrectionTests(Harness):
    def revise(self, key, new_line):
        spec = EXTRA[key]
        content = cover("Example Semiconductor Corp", "8-K", list(spec["items"]), [new_line])
        self.w.source.replace_document(spec["accession"], spec["documents"][0]["name"], content)
        self.w.clock.advance(60_000)
        outcome = self.w.ingestor.poll(EXSEMI, recheck=frozenset({spec["accession"]})).read()
        self.assertEqual(len(outcome["revisions"]), 1)

    def test_l04_correction_resolves_latch_by_rule_and_keeps_history(self):
        _, state = self.run_one("OCCURRED", job="j1")
        self.assertEqual(state["evidence_gate"], "ADVERSE")
        latch = state["unresolved_adverse"][0]
        self.assertEqual(latch["resolution_rule"], "SOURCE_CORRECTED_OR_WITHDRAWN")
        self.revise("OCCURRED", "The company held a routine board meeting in the quarter.")
        _, after = self.run_one("OCCURRED", state=state, job="j2")
        self.assertNotIn("IMPAIRMENT", {a["type"] for a in after["unresolved_adverse"]})
        self.assertEqual([r["resolution"] for r in after["resolved_adverse"] if r["type"] == "IMPAIRMENT"],
                         ["CORRECTED"])

    def test_l04_revision_that_keeps_the_event_does_not_resolve(self):
        _, state = self.run_one("OCCURRED", job="j1")
        self.revise("OCCURRED", "We recorded a goodwill impairment charge of $1.3 billion in the quarter.")
        _, after = self.run_one("OCCURRED", state=state, job="j2")
        self.assertIn("IMPAIRMENT", {a["type"] for a in after["unresolved_adverse"]})

    def test_l04_corrected_statement_is_kept_with_status(self):
        _, state = self.run_one("RISKS", job="j1")
        self.revise("RISKS", RISKS[0])
        _, after = self.run_one("RISKS", state=state, job="j2")
        statuses = {s["text"]: s["status"] for s in after["statements"].values()}
        self.assertEqual(statuses[RISKS[1]], "CORRECTED")
        self.assertEqual(len(after["statements"]), 3)


class IdentityTests(unittest.TestCase):
    def test_l02_paraphrase_substantive_change_and_uncertain_match(self):
        base = SIG("A cybersecurity incident could disrupt our operations.")
        for text in ("A cybersecurity incident may disrupt our operations.",
                     "Our operations could be disrupted by a cybersecurity incident."):
            with self.subTest(text=text):
                self.assertIn(lifecycle.relation(SIG(text), base), ("EXACT", "SEMANTIC_SAME"))
        dated = SIG("We expect to record an impairment charge in the fourth quarter of fiscal 2027.",
                    "FORECAST", event="IMPAIRMENT")
        moved = SIG("We expect to record an impairment charge in the fourth quarter of fiscal 2028.",
                    "FORECAST", event="IMPAIRMENT")
        self.assertEqual(lifecycle.relation(moved, dated), "SUBSTANTIVE_CHANGE")
        third = SIG("A cybersecurity incident could disrupt our operations.", actor="THIRD_PARTY")
        self.assertEqual(lifecycle.relation(third, base), "SUBSTANTIVE_CHANGE")
        # Role nouns such as "customers" are anchors (red team S4-A f04), so the gray-zone example avoids them.
        wider = SIG("A cybersecurity incident could disrupt our operations and harm our reputation significantly.")
        self.assertEqual(lifecycle.relation(wider, base), "UNCERTAIN_MATCH")
        other_event = SIG("A cybersecurity incident could disrupt our operations.", event="IMPAIRMENT")
        self.assertEqual(lifecycle.relation(other_event, base), "UNRELATED")

    def test_l03_missing_history_is_not_first_seen(self):
        sig = SIG("A cybersecurity incident could disrupt our operations.")
        args = dict(max_comparisons=10)
        self.assertEqual(lifecycle.novelty(sig, [], checked=False, history_complete=True, **args)["label"],
                         "PRIOR_NOT_CHECKED")
        self.assertEqual(lifecycle.novelty(sig, [], checked=True, history_complete=False, **args)["label"],
                         "HISTORY_UNAVAILABLE")
        self.assertEqual(lifecycle.novelty(sig, [], checked=True, history_complete=True, **args)["label"],
                         "FIRST_SEEN")
        priors = [{"id": f"p{i}", "fingerprint": SIG(f"unrelated text number {i} about suppliers")} for i in range(20)]
        bounded = lifecycle.novelty(sig, priors, checked=True, history_complete=True, max_comparisons=5)
        self.assertEqual((bounded["label"], bounded["compared"], bounded["truncated"]), ("HISTORY_UNAVAILABLE", 5, True))

    def test_l03_agent_without_prior_lookup_reports_prior_not_checked(self):
        w = build_world(["RISKS"], extra_filings=EXTRA)
        request = w.request(["RISKS"], issuer_id=EXSEMI, job_id="j0", tool_calls=0,
                            context=prior_thesis(w.config, EXSEMI))
        result = w.assessor(RuleBaselineModel(w.clock)).assess(request).read()
        self.assertEqual({s["novelty"] for s in result["event_statements"]}, {"PRIOR_NOT_CHECKED"})


class BoundedReviewTests(unittest.TestCase):
    POLICY = {"review_base_delay_ms": 1000, "max_review_attempts": 3, "max_backoff_ms": 100_000}

    def test_l07_bounded_backoff_then_exhausted_without_human(self):
        registry = {}
        item = {"statement_id": "stmt:x", "event": "IMPAIRMENT", "novelty": "FIRST_SEEN", "statement": "s"}
        entry = lifecycle.observe(registry, item, result_id="r0", now_ms=0, complete=True, policy=self.POLICY)
        self.assertEqual((entry["status"], entry["review"]["next_due_ms"]), ("PENDING_REVIEW", 1000))
        dues = []
        for attempt in range(1, 4):
            entry = lifecycle.observe(registry, dict(item, novelty="ALREADY_SEEN"), result_id=f"r{attempt}",
                                      now_ms=attempt * 10_000, complete=False, policy=self.POLICY)
            dues.append(entry["review"]["next_due_ms"])
        self.assertEqual(entry["status"], "REVIEW_EXHAUSTED")
        self.assertEqual(dues[:2], [10_000 + 2000, 20_000 + 4000])  # exponential backoff
        self.assertIsNone(dues[2])
        self.assertEqual(lifecycle.due_reviews(registry, 10 ** 12), [])
        again = lifecycle.observe(registry, dict(item, novelty="ALREADY_SEEN"), result_id="r9", now_ms=10 ** 6,
                                  complete=True, policy=self.POLICY)
        self.assertEqual(again["status"], "REVIEW_EXHAUSTED")  # no endless reopening


class LargeFilingTests(unittest.TestCase):
    def test_l09_large_filing_reports_truncated_coverage_and_is_never_clear(self):
        quarters = ("first", "second", "third", "fourth")
        numeric = [f"Revenue for the {q} quarter of fiscal {2001 + y} was ${y + 1}.{i} billion."
                   for y in range(60) for i, q in enumerate(quarters)]
        risks = [f"A cybersecurity incident affecting our {w} systems in region {n} could disrupt our operations."
                 for n in range(300) for w in ("billing",)]
        filler = ["This paragraph describes general business operations in neutral terms for readers."] * 14000
        big = eight_k("0009900001-26-000499", "2026-10-05T21:00:00+00:00", numeric + risks + filler)
        w = build_world(["BIG"], extra_filings={"BIG": big})
        config = dataclasses.replace(w.config, limits=dict(w.config.limits, max_document_chars=1_000_000,
                                                           max_facts_per_document=100,
                                                           max_statements_per_document=50,
                                                           max_statement_comparisons=200))
        w.config = config
        request = w.request(["BIG"], issuer_id=EXSEMI, job_id="big", context=prior_thesis(config, EXSEMI))
        result = w.assessor(RuleBaselineModel(w.clock)).assess(request).read()
        cov = result["coverage"]
        self.assertFalse(cov["complete"])
        self.assertTrue(cov["documents_truncated"])
        self.assertGreater(cov["facts_truncated"], 0)
        self.assertGreater(cov["statements_truncated"], 0)
        self.assertLessEqual(len(result["event_statements"]), 50)
        self.assertLessEqual(cov["statement_comparisons"], 2 * 200 * 50)
        self.assertIn("COVERAGE_TRUNCATED", result["missingness"])
        state = dict(initial_state(EXSEMI, PROFILE), context=request.read()["context"],
                     context_hash=request.read()["context_hash"])
        decision, after = accept(state, w.assessor(RuleBaselineModel(w.clock)).assess(request), profile_hash=PROFILE,
                                 now_ms=w.clock())
        self.assertNotEqual(after["evidence_gate"], "CLEAR")


if __name__ == "__main__":
    unittest.main()

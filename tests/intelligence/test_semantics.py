"""IDEA-031 AC-S01..S11: event semantics and signed/kind numeric verification (synthetic sentences only)."""

from fractions import Fraction
import hashlib
import unittest

from larp.intelligence.facts import extract_document, issuer_names, normalized
from larp.intelligence.issuers import IssuerRegistry
from larp.intelligence.scenarios import EXSEMI, FIXTURE_REGISTRY
from larp.intelligence.semantics import classify_event, classify_source_statement, finding_eligible
from larp.intelligence.verify import fact_as_claim, verify_claim

REGISTRY = IssuerRegistry.from_dict(FIXTURE_REGISTRY)
ENTRY = REGISTRY.by_issuer(EXSEMI)
DOC_MS = 1791331200000  # 2026-10-07T00:00:00Z: the synthetic document's own date


def facts_of(text, doc_ms=DOC_MS):
    sha = hashlib.sha256(text.encode()).hexdigest()
    source = {"record_id": "rec:t", "accession": "0009900001-26-000999", "doc_name": "t.htm",
              "available_ms": doc_ms + 1, "original_ms": doc_ms}
    return sha, extract_document(text, sha, ENTRY, source)


def claim(text, metric, start_text=None, **extra):
    sha = hashlib.sha256(text.encode()).hexdigest()
    quoted = start_text or text
    start = text.index(quoted)
    c = {"kind": "EVENT", "metric": metric, "span": {"doc": sha, "start": start, "end": start + len(quoted),
                                                    "text": quoted},
         "source": {"record_id": "rec:t", "accession": "a", "doc_name": "t", "available_ms": DOC_MS + 1,
                    "original_ms": DOC_MS}}
    c.update(extra)
    return verify_claim(c, {sha: text}, None, issuer_names=issuer_names(ENTRY))


def sem(text, event, trigger):
    start = text.index(trigger)
    return classify_event(text, start, start + len(trigger), event=event, document_ms=DOC_MS,
                          issuer_names=issuer_names(ENTRY))


def findings(facts):
    return {f["metric"] for f in facts if f["kind"] == "EVENT" and not f["metric"].startswith("STATEMENT:")}


def statements(facts):
    return {(f["metric"], f["statement"]["assertion"], f["statement"]["actor"]) for f in facts
            if f["metric"].startswith("STATEMENT:")}


class EventSemanticsTests(unittest.TestCase):
    def test_s01_heading_is_not_an_occurrence(self):
        text = "Impairment of goodwill"
        self.assertEqual(sem(text, "IMPAIRMENT", "Impairment")["assertion"], "MENTION_ONLY")
        _, facts = facts_of(text)
        self.assertFalse(findings(facts))
        fact, reason = claim(text, "IMPAIRMENT", "Impairment")
        self.assertIsNone(fact)
        self.assertEqual(reason, "EVENT_NOT_ASSERTED")
        control = "We recorded a goodwill impairment charge of $1.2 billion."
        self.assertIn("IMPAIRMENT", findings(facts_of(control)[1]))
        self.assertIsNotNone(claim(control, "IMPAIRMENT", "impairment")[0])

    def test_s02_competitor_incident_is_third_party(self):
        text = "Our competitor reported a cybersecurity incident."
        s = sem(text, "CYBERSECURITY_INCIDENT", "cybersecurity incident")
        self.assertEqual(s["actor"], "THIRD_PARTY")
        self.assertFalse(finding_eligible(s))
        _, facts = facts_of(text)
        self.assertFalse(findings(facts))
        self.assertIn(("STATEMENT:CYBERSECURITY_INCIDENT", "OCCURRED", "THIRD_PARTY"), statements(facts))
        self.assertEqual(claim(text, "CYBERSECURITY_INCIDENT", "cybersecurity incident")[1],
                         "EVENT_NOT_ISSUER:THIRD_PARTY")
        supplier = "We were notified of a cybersecurity incident at one of our suppliers."
        self.assertEqual(sem(supplier, "CYBERSECURITY_INCIDENT", "cybersecurity incident")["actor"], "THIRD_PARTY")
        control = "On October 5, 2026, the company identified a cybersecurity incident affecting certain internal systems."
        s = sem(control, "CYBERSECURITY_INCIDENT", "cybersecurity incident")
        self.assertEqual((s["assertion"], s["actor"], s["temporal"]), ("OCCURRED", "ISSUER", "CURRENT"))

    def test_s03_rumor_is_attributed_report(self):
        text = "The CEO is rumored to resign."
        s = sem(text, "OFFICER_DEPARTURE", "CEO is rumored to resign")
        self.assertEqual((s["assertion"], s["attribution"]), ("ATTRIBUTED_REPORT", "ATTRIBUTED_TO_OTHERS"))
        self.assertFalse(findings(facts_of(text)[1]))
        self.assertEqual(claim(text, "OFFICER_DEPARTURE", "CEO is rumored to resign")[1],
                         "EVENT_NOT_OCCURRED:ATTRIBUTED_REPORT")

    def test_s04_announced_future_departure_keeps_both_dimensions(self):
        text = "The CEO announced plans to resign effective November 30."
        s = sem(text, "OFFICER_DEPARTURE", "CEO announced plans to resign")
        self.assertEqual((s["assertion"], s["effective"], s["temporal"]), ("ANNOUNCED_FUTURE", "2026-11-30", "FUTURE"))
        eight_k = ("On October 7, 2026, the company's Chief Financial Officer notified the Board of a decision to resign "
                   "as Chief Financial Officer, effective November 30, 2026.")
        _, facts = facts_of(eight_k)
        self.assertFalse(findings(facts))
        kept = [f for f in facts if f["metric"] == "STATEMENT:OFFICER_DEPARTURE"]
        self.assertEqual([(f["statement"]["assertion"], f["statement"]["effective"]) for f in kept],
                         [("ANNOUNCED_FUTURE", "2026-11-30")])
        past = "The CFO resigned effective October 1, 2026."
        self.assertEqual(sem(past, "OFFICER_DEPARTURE", "CFO resigned")["assertion"], "OCCURRED")

    def test_s05_negation_scope_and_mixed_clauses(self):
        mixed = "We recorded an impairment charge and did not record a restructuring charge."
        self.assertEqual(sem(mixed, "IMPAIRMENT", "impairment")["assertion"], "OCCURRED")
        self.assertIn("IMPAIRMENT", findings(facts_of(mixed)[1]))
        for text, trigger, event in (("We did not record an impairment charge.", "impairment", "IMPAIRMENT"),
                                     ("No cybersecurity incident has had a material effect on our business.",
                                      "cybersecurity incident", "CYBERSECURITY_INCIDENT")):
            with self.subTest(text=text):
                self.assertEqual(sem(text, event, trigger)["assertion"], "NEGATED")
                self.assertFalse(facts_of(text)[1])

    def test_s06_quoted_third_party_and_historical_repetition(self):
        quoted = '"We expect a cybersecurity incident," said an analyst.'
        s = sem(quoted, "CYBERSECURITY_INCIDENT", "cybersecurity incident")
        self.assertEqual((s["attribution"], s["actor"]), ("QUOTED_THIRD_PARTY", "THIRD_PARTY"))
        self.assertFalse(findings(facts_of(quoted)[1]))
        historical = "In fiscal 2019, we restated our financial statements."
        s = sem(historical, "RESTATEMENT", "restated")
        self.assertEqual((s["assertion"], s["temporal"]), ("OCCURRED", "HISTORICAL"))
        self.assertFalse(findings(facts_of(historical)[1]))
        self.assertEqual(claim(historical, "RESTATEMENT", "restated")[1], "EVENT_NOT_CURRENT:HISTORICAL")

    def test_s07_allegations_and_proposed_rules(self):
        aliases = {EXSEMI: ["Example Semiconductor"]}
        complaint = classify_source_statement(
            "The SEC filed a complaint alleging that Example Semiconductor misstated revenue.",
            source_kind="AGENCY", actor="SEC", aliases=aliases)
        self.assertIn("COMPLAINT_OR_CHARGE", complaint["actions"])
        self.assertEqual(complaint["certainty"], ["ALLEGATION_NOT_FINDING"])
        self.assertEqual(complaint["issuer_relations"][0]["effect"], "UNKNOWN")
        proposed = classify_source_statement("BIS published a proposed rule on advanced computing exports.",
                                             source_kind="AGENCY", actor="BIS", aliases=aliases)
        self.assertEqual((proposed["actions"], proposed["certainty"]), (["PROPOSED_RULE"], ["PROPOSAL_NOT_EFFECTIVE"]))
        final = classify_source_statement("BIS issued a final rule amending the Export Administration Regulations.",
                                          source_kind="AGENCY", actor="BIS", aliases=aliases)
        self.assertIn("FINAL_RULE", final["actions"])
        self.assertNotIn("PROPOSED_RULE", final["actions"])
        alleged = "A lawsuit alleges that the company suffered a cybersecurity incident."
        self.assertEqual(sem(alleged, "CYBERSECURITY_INCIDENT", "cybersecurity incident")["assertion"],
                         "ATTRIBUTED_REPORT")

    def test_s10_development_claim_has_no_invented_relation(self):
        text = ("A China-based company announced it had developed a chip that it says outperforms leading "
                "accelerators.")
        out = classify_source_statement(text, source_kind="NEWS", actor="publisher",
                                        aliases={"NVDA": ["NVIDIA"], "SKHY": ["SK hynix"]})
        self.assertEqual((out["statement_type"], out["certainty"], out["issuer_relations"]),
                         ("DEVELOPMENT_CLAIM", ["ATTRIBUTED_TO_ANNOUNCER"], []))
        named = classify_source_statement(text + " Analysts compared it with NVIDIA products.", source_kind="NEWS",
                                          actor="publisher", aliases={"NVDA": ["NVIDIA"], "SKHY": ["SK hynix"]})
        self.assertEqual(named["issuer_relations"], [{"issuer_id": "NVDA", "relation": "MENTIONED_IN_SOURCE",
                                                      "effect": "UNKNOWN", "basis": "name appears in this source text"}])

    def test_statement_claims_must_match_recomputed_semantics(self):
        text = "The CEO announced plans to resign effective November 30."
        ok, reason = claim(text, "STATEMENT:OFFICER_DEPARTURE", text,
                           statement={"assertion": "ANNOUNCED_FUTURE", "effective": "2026-11-30"})
        self.assertIsNone(reason)
        self.assertEqual(ok["statement"]["assertion"], "ANNOUNCED_FUTURE")
        _, reason = claim(text, "STATEMENT:OFFICER_DEPARTURE", text, statement={"assertion": "OCCURRED"})
        self.assertEqual(reason, "EVENT_SEMANTICS_MISMATCH")
        occurred = "We recorded a goodwill impairment charge of $1.2 billion."
        self.assertEqual(claim(occurred, "STATEMENT:IMPAIRMENT", occurred)[1], "STATEMENT_IS_ISSUER_OCCURRENCE")


def number_claim(text, quoted, kind, value=None, rng=None, unit="USD", scale=9, period=None, metric="revenue",
                 period_text=None):
    sha = hashlib.sha256(text.encode()).hexdigest()
    start = text.index(quoted)
    c = {"kind": kind, "metric": metric, "period": period, "value": value, "range": rng, "unit": unit,
         "scale_exp10": scale, "span": {"doc": sha, "start": start, "end": start + len(quoted), "text": quoted}}
    if period_text:
        p = text.index(period_text)
        c["period_span"] = {"doc": sha, "start": p, "end": p + len(period_text), "text": period_text}
    return verify_claim(c, {sha: text}, None)


class NumericTests(unittest.TestCase):
    REV = "Revenue for the third quarter of fiscal 2027 was $35.1 billion."

    def test_s08_sign_and_kind_mutations_with_unchanged_span(self):
        control = number_claim(self.REV, self.REV, "REPORTED", "35.1", period="FY2027-Q3")
        self.assertIsNone(control[1])
        self.assertEqual(number_claim(self.REV, self.REV, "REPORTED", "-35.1", period="FY2027-Q3")[1],
                         "SIGN_MISMATCH")
        self.assertEqual(number_claim(self.REV, self.REV, "GUIDANCE", "35.1", period="FY2027-Q3")[1],
                         "KIND_NOT_SUPPORTED:REPORTED")

    def test_s08_losses_and_parentheses(self):
        for text in ("Net loss for the third quarter of fiscal 2027 was $1.2 billion.",
                     "Net loss for the third quarter of fiscal 2027 was $(1.2) billion."):
            with self.subTest(text=text):
                _, facts = facts_of(text)
                net = [f for f in facts if f["metric"] == "net_income"]
                self.assertEqual([normalized(f) for f in net], [Fraction(-12, 10) * 10 ** 9])
                self.assertIsNone(number_claim(text, text, "REPORTED", "-1.2", metric="net_income")[1])
                self.assertEqual(number_claim(text, text, "REPORTED", "1.2", metric="net_income")[1], "SIGN_MISMATCH")
        table = "(in millions)\n | Q3 FY27\nNet income (loss) | $(1,234)"
        _, facts = facts_of(table)
        cells = [f for f in facts if f["metric"] == "net_income"]
        self.assertEqual([normalized(f) for f in cells], [Fraction(-1234) * 10 ** 6])
        for f in cells:
            self.assertIsNone(verify_claim(fact_as_claim(f), {f["span"]["doc"]: table}, None)[1])
            flipped = dict(fact_as_claim(f), value=[1234, 1])
            self.assertEqual(verify_claim(flipped, {f["span"]["doc"]: table}, None)[1], "TABLE_VALUE_SIGN_MISMATCH")

    def test_s09_guidance_kind_ranges_and_change_amounts(self):
        guide = "For the fourth quarter of fiscal 2027, the company expects revenue to be $33.0 billion."
        quoted = guide[guide.index("revenue"):]
        self.assertIsNone(number_claim(guide, quoted, "GUIDANCE", "33.0")[1])
        self.assertEqual(number_claim(guide, quoted, "REPORTED", "33.0")[1], "KIND_NOT_SUPPORTED:GUIDANCE")
        ranged = "The company expects revenue to be between $30.0 billion and $32.0 billion."
        q = ranged[ranged.index("revenue"):]
        self.assertIsNone(number_claim(ranged, q, "GUIDANCE", rng=["30.0", "32.0"])[1])
        self.assertEqual(number_claim(ranged, q, "GUIDANCE", "30.0")[1], "RANGE_BOUND_CLAIMED_AS_POINT")
        self.assertEqual(number_claim(ranged, q, "GUIDANCE", "32.0")[1], "RANGE_BOUND_CLAIMED_AS_POINT")
        change = "Revenue increased by $2.0 billion in the quarter."
        self.assertEqual(number_claim(change, change, "REPORTED", "2.0")[1], "CHANGE_AMOUNT_NOT_LEVEL")
        self.assertFalse([f for f in facts_of(change)[1] if f["metric"] == "revenue"])

    def test_extracted_facts_still_round_trip(self):
        for text in (self.REV, "Net loss for the third quarter of fiscal 2027 was $1.2 billion.",
                     "For the fourth quarter of fiscal 2027, the company expects revenue to be $33.0 billion, "
                     "plus or minus 2%.",
                     "We recorded a goodwill impairment charge of $1.2 billion.",
                     "The CEO announced plans to resign effective November 30."):
            sha, facts = facts_of(text)
            self.assertTrue(facts, text)
            for f in facts:
                with self.subTest(text=text, metric=f["metric"]):
                    verified, reason = verify_claim(fact_as_claim(f), {sha: text}, None,
                                                    issuer_names=issuer_names(ENTRY))
                    self.assertIsNone(reason)
                    self.assertEqual(verified["fact_id"], f["fact_id"])


if __name__ == "__main__":
    unittest.main()

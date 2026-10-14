"""IDEA-031 S4(A): independent red-team probes of the evidence-semantics layer (synthetic sentences only).

Every test asserts the CORRECT behaviour under the IDEA-031 S2 contract, so a failing test is a defect found,
not a broken test. Controls (valid inputs that must keep working) are marked "CONTROL". Severity tags:
P1 = false adverse finding / false occurrence / wrong signed or kind number accepted; P2 = true occurrence missed
or non-actionable semantics mislabelled; P3 = cosmetic. Synthetic probes show paths, not real-text error rates.

The synthetic document is the issuer's own filing (issuer_source=True), dated 2026-10-07 UTC, for the fixture
issuer "Example Semiconductor Corp". "Acme" is a fictional non-issuer company.
"""

import hashlib
import unittest

from larp.intelligence import lifecycle
from larp.intelligence.facts import extract_document, issuer_names, normalized
from larp.intelligence.issuers import IssuerRegistry
from larp.intelligence.scenarios import EXSEMI, FIXTURE_REGISTRY
from larp.intelligence.semantics import classify_event, classify_source_statement
from larp.intelligence.verify import compare, fact_as_claim, verify_claim

ENTRY = IssuerRegistry.from_dict(FIXTURE_REGISTRY).by_issuer(EXSEMI)
NAMES = issuer_names(ENTRY)
DOC_MS = 1791331200000  # 2026-10-07T00:00:00Z


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def extract(text):
    source = {"record_id": "rec:rt", "accession": "0009900001-26-000777", "doc_name": "rt.htm",
              "available_ms": DOC_MS + 1, "original_ms": DOC_MS}
    return extract_document(text, _sha(text), ENTRY, source)


def findings(text):
    """Plain event metrics (finding-eligible issuer occurrences) the extractor emits."""
    return {f["metric"] for f in extract(text) if f["kind"] == "EVENT" and not f["metric"].startswith("STATEMENT:")}


def statement_facts(text, event):
    return [f["statement"] for f in extract(text) if f["metric"] == "STATEMENT:" + event]


def sem(text, event, trigger):
    start = text.index(trigger)
    return classify_event(text, start, start + len(trigger), event=event, document_ms=DOC_MS, issuer_names=NAMES)


def event_claim(text, metric, quoted=None, statement=None):
    quoted = quoted or text
    start = text.index(quoted)
    claim = {"kind": "EVENT", "metric": metric,
             "span": {"doc": _sha(text), "start": start, "end": start + len(quoted), "text": quoted},
             "source": {"record_id": "rec:rt", "accession": "a", "doc_name": "rt", "available_ms": DOC_MS + 1,
                        "original_ms": DOC_MS}}
    if statement is not None:
        claim["statement"] = statement
    return verify_claim(claim, {_sha(text): text}, None, issuer_names=NAMES)


def num_claim(text, kind, value=None, rng=None, metric="revenue", quoted=None, unit="USD", scale=9):
    quoted = quoted or text
    start = text.index(quoted)
    claim = {"kind": kind, "metric": metric, "value": value, "range": rng, "unit": unit, "scale_exp10": scale,
             "span": {"doc": _sha(text), "start": start, "end": start + len(quoted), "text": quoted}}
    return verify_claim(claim, {_sha(text): text}, None)[1]  # None = accepted


def numeric_facts(text, metric):
    return [f for f in extract(text) if f["metric"] == metric]


# ===================================================================== A. false adverse findings (P1)
class FalseAdverseFindings(unittest.TestCase):
    """Text that does not assert the ISSUER's own CURRENT OCCURRED event must never yield a plain event finding,
    and the verifier must reject a model claim of the plain event on it (verifier parity)."""

    def assertNoFinding(self, text, event):
        self.assertNotIn(event, findings(text), "extractor emitted a finding")
        fact, reason = event_claim(text, event)
        self.assertIsNone(fact, "verifier accepted a plain-event claim")

    def test_a01_passive_by_agent_third_party(self):
        # Passive voice / reduced relative with a by-agent after the predicate: the customer or supplier recorded
        # the charge. Expected actor THIRD_PARTY. (The by-phrase is not adjacent to the trigger, so
        # COMPLEMENT_THIRD misses it, and the actor search only looks left of the predicate.)
        for text in ("Impairment charges were recorded by our largest customer.",
                     "An impairment charge was recorded by one of our suppliers.",
                     "The impairment charge recorded by our customer reduced its demand."):
            with self.subTest(text=text):
                self.assertNoFinding(text, "IMPAIRMENT")

    def test_a04_supplier_ceo_prepositional_possessor(self):
        # "The CEO of our largest supplier": the officer belongs to the supplier. THIRD_PARTY.
        self.assertNoFinding("The CEO of our largest supplier resigned.", "OFFICER_DEPARTURE")

    def test_a05_named_company_possessive_officer(self):
        # "Acme's CFO": a named other company's officer. Expected THIRD_PARTY (or at least not ISSUER).
        self.assertNoFinding("Acme's CFO stepped down last week.", "OFFICER_DEPARTURE")

    def test_a06_object_of_occurrence_verb_is_competitor(self):
        # Nasdaq delisted the COMPETITOR (object position); the issuer is not delisted. THIRD_PARTY.
        self.assertNoFinding("Nasdaq delisted our competitor.", "DELISTING")

    def test_a07_named_other_company_subject(self):
        # A named non-issuer company is the subject; issuer_source must not default it to ISSUER.
        self.assertNoFinding("Acme Corp reported a cybersecurity incident.", "CYBERSECURITY_INCIDENT")

    def test_a08_appositive_mentioning_the_company(self):
        # Appositive "a supplier to the company": the nearest mention ("the company") wins, but the subject
        # is Acme, a supplier. THIRD_PARTY.
        self.assertNoFinding("Acme, a supplier to the company, experienced a cybersecurity incident.",
                             "CYBERSECURITY_INCIDENT")

    def test_a09_curly_single_quoted_third_party_speech(self):
        # Quoted third-party speech using typographic single quotes; "We" inside the quote is Acme.
        self.assertNoFinding("Acme Corp said: ‘We suffered a cybersecurity incident.’",
                             "CYBERSECURITY_INCIDENT")

    def test_a10_relative_clause_about_other_company_officer(self):
        # Biographical relative clause: Smith resigned as Acme's CEO in the past; he JOINED our board.
        self.assertNoFinding("Mr. Smith, who resigned as CEO of Acme Corp, joined our board.", "OFFICER_DEPARTURE")

    def test_a11_reported_that_clause_about_other_company(self):
        # Embedded clause: what we were informed of is Acme's CEO resigning. THIRD_PARTY.
        self.assertNoFinding("Our board was informed that Acme's CEO resigned.", "OFFICER_DEPARTURE")

    def test_a12_hypothetical_scenario_without_modal(self):
        # Hypothetical framed by "in a scenario where" with no modal verb. Expected CONDITIONAL_RISK (not OCCURRED).
        self.assertNoFinding("In a scenario where we suffered a cybersecurity incident, losses increase by 10%.",
                             "CYBERSECURITY_INCIDENT")

    def test_a13_item_1c_process_boilerplate(self):
        # Item 1C risk-management boilerplate: a simulated incident, and a generic "when ... is detected"
        # procedure. Neither is an occurrence. Expected MENTION_ONLY/CONDITIONAL_RISK, not OCCURRED.
        for text in ("Our tabletop exercise simulated a cybersecurity incident in which attackers compromised our "
                     "systems.",
                     "Our incident response plan describes the steps taken when a cybersecurity incident is detected."):
            with self.subTest(text=text):
                self.assertNoFinding(text, "CYBERSECURITY_INCIDENT")

    def test_a15_accounting_policy_definition(self):
        # 10-K accounting-policy definition: "is recognized when" is generic present, not a recorded charge.
        self.assertNoFinding("An impairment loss is recognized when the carrying amount of goodwill exceeds its "
                             "fair value.", "IMPAIRMENT")

    def test_a16_table_of_contents_line(self):
        # A table-of-contents entry with dot leaders and a page number asserts nothing. Expected MENTION_ONLY.
        self.assertNoFinding("Table of Contents: Impairment Charges Recognized ..... 45", "IMPAIRMENT")

    def test_a17_historical_without_year_digits(self):
        # 10-Q comparative "in the prior year period" (singular; HISTORICAL_MARK only knows "prior years") and
        # "Last year": the charge is historical. Expected temporal HISTORICAL, no current finding.
        for text in ("In the prior year period, we recorded an impairment charge of $1.2 billion.",
                     "Last year, we recorded an impairment charge."):
            with self.subTest(text=text):
                self.assertNoFinding(text, "IMPAIRMENT")

    def test_a19_effective_as_of_close_of_business_future_date(self):
        # "effective as of the close of business on November 30, 2026" (document 2026-10-07): the resignation is
        # tendered but not yet effective. Expected ANNOUNCED_FUTURE with effective 2026-11-30, not OCCURRED.
        text = "The CFO resigned, effective as of the close of business on November 30, 2026."
        self.assertNoFinding(text, "OFFICER_DEPARTURE")
        kept = statement_facts(text, "OFFICER_DEPARTURE")
        self.assertEqual([(s["assertion"], s["effective"]) for s in kept], [("ANNOUNCED_FUTURE", "2026-11-30")])

    def test_a20_announced_upcoming_departure(self):
        # "announced the upcoming departure": an announcement of a future event. Expected ANNOUNCED_FUTURE.
        self.assertNoFinding("The company announced the upcoming departure of its CFO.", "OFFICER_DEPARTURE")


# ===================================================================== B. missed true occurrences (P2)
class MissedIssuerOccurrences(unittest.TestCase):
    """Clear issuer current occurrences that must become a finding (and verify as the plain event)."""

    def assertFinding(self, text, event):
        self.assertIn(event, findings(text))
        fact, reason = event_claim(text, event)
        self.assertIsNone(reason)

    def test_b01_negation_in_trailing_relative_clause(self):
        # "which did not affect our liquidity" negates the effect, not the charge. Expected OCCURRED/ISSUER/CURRENT.
        self.assertFinding("We recorded a non-cash goodwill impairment charge of $1.2 billion, which did not affect "
                           "our liquidity.", "IMPAIRMENT")

    def test_b02_item_105_materiality_negation(self):
        # Standard Item 1.05 phrasing: the incident occurred; only its material impact is negated.
        self.assertFinding("On October 5, 2026, we identified a cybersecurity incident, which has not had a material "
                           "impact on our operations.", "CYBERSECURITY_INCIDENT")

    def test_b03_concessive_negation_does_not_scope_over_main_clause(self):
        # "Although no restatement was required in prior years, we restated our fiscal 2027 first quarter results."
        # The negation and "prior years" belong to the concessive clause. Expected OCCURRED/CURRENT for "restated".
        self.assertFinding("Although no restatement was required in prior years, we restated our fiscal 2027 first "
                           "quarter results.", "RESTATEMENT")

    def test_b04_quoted_named_officer_of_issuer(self):
        # Issuer press-release quote attributed to its CEO by name + title. Expected QUOTED_ISSUER, OCCURRED, ISSUER.
        self.assertFinding('"We identified a cybersecurity incident on October 5," said Jane Doe, our Chief Executive '
                           'Officer.', "CYBERSECURITY_INCIDENT")

    def test_b05_old_year_in_biographical_clause(self):
        # The 2015 year belongs to "who joined"; the resignation is current. Expected temporal CURRENT.
        self.assertFinding("Our CFO, who joined in 2015, resigned on October 1.", "OFFICER_DEPARTURE")

    def test_b06_effective_date_shortly_before_document(self):
        # Document 2026-10-07: "resigned effective September 30" is 2026-09-30 (past), not 2027-09-30.
        text = "The CFO resigned effective September 30."
        s = sem(text, "OFFICER_DEPARTURE", "CFO resigned")
        self.assertEqual((s["assertion"], s["effective"]), ("OCCURRED", "2026-09-30"))

    def test_b07_board_accepted_resignation(self):
        # "The Board accepted the resignation of the CEO" asserts the departure occurred.
        self.assertFinding("The Board accepted the resignation of the Chief Executive Officer.", "OFFICER_DEPARTURE")


# ===================================================================== C. event controls (must keep passing)
class EventControls(unittest.TestCase):
    def test_c01_control_recorded_impairment(self):
        # CONTROL: OCCURRED/ISSUER/CURRENT finding; plain claim verifies; STATEMENT claim is rejected.
        text = "We recorded a goodwill impairment charge of $1.2 billion."
        self.assertIn("IMPAIRMENT", findings(text))
        self.assertIsNone(event_claim(text, "IMPAIRMENT")[1])
        self.assertEqual(event_claim(text, "STATEMENT:IMPAIRMENT")[1], "STATEMENT_IS_ISSUER_OCCURRENCE")

    def test_c02_control_competitor_officer_possessive(self):
        # CONTROL: "Our competitor's CEO resigned." -> STATEMENT OCCURRED THIRD_PARTY; a STATEMENT claim stating
        # THIRD_PARTY verifies; one stating ISSUER is a semantics mismatch.
        text = "Our competitor's CEO resigned."
        self.assertFalse(findings(text))
        self.assertEqual([(s["assertion"], s["actor"]) for s in statement_facts(text, "OFFICER_DEPARTURE")],
                         [("OCCURRED", "THIRD_PARTY")])
        self.assertIsNone(event_claim(text, "STATEMENT:OFFICER_DEPARTURE",
                                      statement={"assertion": "OCCURRED", "actor": "THIRD_PARTY"})[1])
        self.assertEqual(event_claim(text, "STATEMENT:OFFICER_DEPARTURE", statement={"actor": "ISSUER"})[1],
                         "EVENT_SEMANTICS_MISMATCH")

    def test_c03_control_former_ceo_2019_noun_phrase(self):
        # CONTROL: "Following the resignation of our former CEO in 2019" -> no current finding.
        text = "Following the resignation of our former CEO in 2019, we appointed a new CEO."
        self.assertFalse(findings(text))
        self.assertIsNone(event_claim(text, "OFFICER_DEPARTURE")[0])

    def test_c04_control_negations(self):
        # CONTROL: "has not been", "there has been no", "no longer" -> nothing asserted, no facts.
        for text, event in (("We have not been the subject of a cybersecurity incident.", "CYBERSECURITY_INCIDENT"),
                            ("There has been no cybersecurity incident.", "CYBERSECURITY_INCIDENT"),
                            ("We no longer believe that our financial statements should be restated.", "RESTATEMENT")):
            with self.subTest(text=text):
                self.assertFalse(findings(text))
                self.assertIsNone(event_claim(text, event)[0])

    def test_c05_control_counterfactual_inversion(self):
        # CONTROL: "Had we recorded an impairment, ..." -> CONDITIONAL_RISK statement, no finding.
        text = "Had we recorded an impairment, our earnings would have declined."
        self.assertFalse(findings(text))
        self.assertEqual([s["assertion"] for s in statement_facts(text, "IMPAIRMENT")], ["CONDITIONAL_RISK"])

    def test_c06_control_resigned_effective_future_date(self):
        # CONTROL: past-tense "resigned" with a later effective date -> ANNOUNCED_FUTURE, effective kept; the plain
        # event claim fails and the STATEMENT claim with matching semantics verifies.
        text = "The CEO resigned, effective December 31, 2026."
        self.assertFalse(findings(text))
        self.assertIsNone(event_claim(text, "OFFICER_DEPARTURE")[0])
        self.assertIsNone(event_claim(text, "STATEMENT:OFFICER_DEPARTURE",
                                      statement={"assertion": "ANNOUNCED_FUTURE", "effective": "2026-12-31"})[1])

    def test_c07_control_shares_delisted_and_historical_year(self):
        # CONTROL: issuer delisting is a finding; "In 2024 we recorded" is HISTORICAL (not a finding).
        self.assertIn("DELISTING", findings("Our shares were delisted from Nasdaq."))
        historical = "In 2024 we recorded an impairment charge."
        self.assertFalse(findings(historical))
        self.assertEqual(event_claim(historical, "IMPAIRMENT")[1], "EVENT_NOT_CURRENT:HISTORICAL")

    def test_c08_control_competitors_including_list(self):
        # CONTROL: "Several competitors, including Acme, experienced ..." -> THIRD_PARTY.
        text = "Several competitors, including Acme, experienced a cybersecurity incident."
        self.assertFalse(findings(text))
        self.assertEqual(event_claim(text, "CYBERSECURITY_INCIDENT")[1], "EVENT_NOT_ISSUER:THIRD_PARTY")


# ===================================================================== D. numeric sign / kind / range / change
class NumericProbes(unittest.TestCase):
    def test_tolerance_must_be_bound_to_the_same_amount(self):
        text = "The company expects revenue of $30 billion, an increase of 10% over last year."
        claim = fact_as_claim(numeric_facts(text, "revenue")[0])
        claim["span"] = {"doc": _sha(text), "start": 0, "end": len(text), "text": text}
        for value in ("10", "30", "-10"):
            with self.subTest(value=value):
                self.assertEqual(verify_claim(dict(claim, tolerance_pct=value), {_sha(text): text})[1],
                                 "TOLERANCE_NOT_STATED")
        control = "The company expects revenue of $30 billion, plus or minus 10%."
        fact = numeric_facts(control, "revenue")[0]
        self.assertIsNone(verify_claim(fact_as_claim(fact), {_sha(control): control})[1])
        self.assertEqual(verify_claim(dict(fact_as_claim(fact), tolerance_pct=None), {_sha(control): control})[1],
                         "TOLERANCE_NOT_STATED")
        self.assertEqual(verify_claim(dict(fact_as_claim(fact), range=["30", "10"]), {_sha(control): control})[1],
                         "POINT_AND_RANGE")

    def test_negative_guidance_tolerance_and_loss_range_use_ordered_bounds(self):
        for guidance in ("The company expects net loss for Q3 FY27 of $1.0 billion, plus or minus 10%.",
                         "The company expects net loss for Q3 FY27 of $0.9 billion to $1.1 billion."):
            prior = numeric_facts(guidance, "net_income")[0]
            self.assertIsNone(verify_claim(fact_as_claim(prior), {_sha(guidance): guidance})[1])
            for level, expected in (("0.85", "ABOVE"), ("1.0", "WITHIN"), ("1.15", "BELOW")):
                text = f"Net loss for Q3 FY27 was ${level} billion."
                with self.subTest(guidance=guidance, level=level):
                    self.assertEqual(compare(numeric_facts(text, "net_income")[0], prior)["relation"], expected)

    def test_d01_second_metric_sign_borrowed_from_first(self):
        # P1. Whole-sentence span: the loss form of the FIRST metric ("Net loss") is applied to every number, so a
        # claim net_income = -0.3 (the second metric is "net income of $0.3 billion", i.e. +0.3) must fail.
        text = "Net loss was $1.2 billion, compared with net income of $0.3 billion."
        self.assertIsNotNone(num_claim(text, "REPORTED", "-0.3", metric="net_income"))

    def test_d02_prior_period_loss_sign_lost(self):
        # P1. "compared with a net loss of $0.4 billion": +0.4 net income is wrong-signed and must fail.
        text = "Net income was $1.2 billion, compared with a net loss of $0.4 billion a year ago."
        self.assertIsNotNone(num_claim(text, "REPORTED", "0.4", metric="net_income"))

    def test_d03_change_amount_noun_improvement(self):
        # P1. "an improvement of $0.3 billion" is a change amount, not the net_income level.
        text = "Net loss was $1.2 billion, an improvement of $0.3 billion."
        self.assertIsNotNone(num_claim(text, "REPORTED", "-0.3", metric="net_income"))

    def test_d04_as_expected_is_still_reported(self):
        # P1. "As expected, revenue was $35.1 billion." is a REPORTED result; GUIDANCE must fail, REPORTED must pass,
        # and the extractor must label it REPORTED.
        text = "As expected, revenue was $35.1 billion."
        self.assertIsNotNone(num_claim(text, "GUIDANCE", "35.1"))
        self.assertIsNone(num_claim(text, "REPORTED", "35.1"))
        self.assertEqual({f["kind"] for f in numeric_facts(text, "revenue")}, {"REPORTED"})

    def test_d05_expected_amount_after_reported_amount(self):
        # P1. "$33.0 billion we expected" is the prior expectation, not reported revenue: REPORTED 33.0 must fail.
        text = "Revenue was $35.1 billion, compared to the $33.0 billion we expected."
        self.assertIsNotNone(num_claim(text, "REPORTED", "33.0"))
        self.assertIsNone(num_claim(text, "REPORTED", "35.1"))  # control within the same sentence

    def test_d06_analyst_estimate_is_not_reported(self):
        # P1. Consensus/analyst estimates have no admissible source: never REPORTED revenue, never extracted as such.
        text = "Analysts estimate revenue of $36.0 billion."
        self.assertIsNotNone(num_claim(text, "REPORTED", "36.0"))
        self.assertFalse([f for f in numeric_facts(text, "revenue") if f["kind"] == "REPORTED"])

    def test_d07_in_the_range_of_point_claim(self):
        # P1. "in the range of $30.0 billion to $32.0 billion" is a range; a point at one bound must fail and the
        # extractor must emit the range, not the low bound as a point.
        text = "The company expects revenue in the range of $30.0 billion to $32.0 billion."
        quoted = text[text.index("revenue"):]
        self.assertIsNotNone(num_claim(text, "GUIDANCE", "30.0", quoted=quoted))
        facts = numeric_facts(text, "revenue")
        self.assertTrue(facts)
        self.assertTrue(all(f["range"] is not None and f["value"] is None for f in facts), facts)

    def test_d08_other_range_forms_point_claim(self):
        # P1. Ranges without "between": "$30.0-$32.0 billion" and "$30.0 billion to $32.0 billion". A point claim at
        # either bound must fail (only "between ... and/to" is recognised as a range today).
        for text, point in (("The company expects revenue of $30.0-$32.0 billion.", "30.0"),
                            ("The company expects revenue of $30.0 billion to $32.0 billion.", "32.0")):
            with self.subTest(text=text):
                quoted = text[text.index("revenue"):]
                self.assertIsNotNone(num_claim(text, "GUIDANCE", point, quoted=quoted))

    def test_d10_level_after_change_verb(self):
        # P2. "increased 10% to $35.1 billion" states the new LEVEL; the REPORTED 35.1 claim must pass and the
        # extractor should emit it (press-release phrasing; currently both rejected/skipped).
        text = "Revenue increased 10% to $35.1 billion."
        self.assertIsNone(num_claim(text, "REPORTED", "35.1"))
        self.assertEqual([normalized(f) for f in numeric_facts(text, "revenue")], [35100000000])

    def test_d11_control_parenthesised_negative_non_loss_metric(self):
        # CONTROL: "Operating income was $(0.5) billion." -> -0.5 passes, +0.5 fails.
        text = "Operating income was $(0.5) billion."
        self.assertIsNone(num_claim(text, "REPORTED", "-0.5", metric="operating_income"))
        self.assertEqual(num_claim(text, "REPORTED", "0.5", metric="operating_income"), "SIGN_MISMATCH")

    def test_d12_control_guided_loss(self):
        # CONTROL: guided net loss -> GUIDANCE -0.5 passes; +0.5 and REPORTED fail.
        text = "The company expects a net loss of $0.5 billion."
        quoted = text[text.index("net loss"):]
        self.assertIsNone(num_claim(text, "GUIDANCE", "-0.5", metric="net_income", quoted=quoted))
        self.assertEqual(num_claim(text, "GUIDANCE", "0.5", metric="net_income", quoted=quoted), "SIGN_MISMATCH")
        self.assertEqual(num_claim(text, "REPORTED", "-0.5", metric="net_income", quoted=quoted),
                         "KIND_NOT_SUPPORTED:GUIDANCE")

    def test_d13_control_range_claim_and_change_amount(self):
        # CONTROL: a correctly claimed range passes; a level with a trailing change amount passes and the change
        # amount itself fails.
        text = "The company expects revenue in the range of $30.0 billion to $32.0 billion."
        quoted = text[text.index("revenue"):]
        self.assertIsNone(num_claim(text, "GUIDANCE", rng=["30.0", "32.0"], quoted=quoted))
        level = "Revenue was $35.1 billion, which included an increase of $2.0 billion from acquisitions."
        self.assertIsNone(num_claim(level, "REPORTED", "35.1"))
        self.assertEqual(num_claim(level, "REPORTED", "2.0"), "CHANGE_AMOUNT_NOT_LEVEL")


# ===================================================================== E. regulatory statements
class RegulatoryProbes(unittest.TestCase):
    def test_e01_proposed_amendments_to_final_rule(self):
        # P2. A proposal that refers to an existing final rule is a PROPOSAL (not effective), not an action taken.
        out = classify_source_statement("The SEC proposed amendments that would modify the final rule adopted in "
                                        "2024.", source_kind="AGENCY", actor="SEC", aliases={})
        self.assertIn("PROPOSED_RULE", out["actions"])
        self.assertNotIn("AGENCY_ACTION_TAKEN", out["certainty"])


# ===================================================================== F. statement identity
def _sig(text, event, trigger):
    return lifecycle.signature(event, sem(text, event, trigger), text)


class IdentityProbes(unittest.TestCase):
    def rel(self, a, b, event, trigger):
        return lifecycle.relation(_sig(b, event, trigger), _sig(a, event, trigger))

    def test_f01_control_modal_paraphrase(self):
        # CONTROL: "could" -> "may" with passive reordering is the same statement.
        self.assertIn(self.rel("A cybersecurity incident could disrupt our operations.",
                               "Our operations may be disrupted by a cybersecurity incident.",
                               "CYBERSECURITY_INCIDENT", "cybersecurity incident"), ("EXACT", "SEMANTIC_SAME"))

    def test_f02_control_gray_zone_extension(self):
        # CONTROL: an added consequence is exposed as UNCERTAIN_MATCH, not merged.
        self.assertEqual(self.rel("A cybersecurity incident could disrupt our operations.",
                                  "A cybersecurity incident could disrupt our operations and harm our reputation.",
                                  "CYBERSECURITY_INCIDENT", "cybersecurity incident"), "UNCERTAIN_MATCH")

    def test_f03_changed_quarter_is_substantive(self):
        # P2. Date change (fourth -> third quarter) of an expected charge is SUBSTANTIVE_CHANGE; it must not be
        # merged into the earlier registry entry (which would skip review).
        a = ("We expect to record an impairment charge of approximately $1.2 billion related to our memory business "
             "in the fourth quarter.")
        b = a.replace("fourth quarter", "third quarter")
        self.assertEqual(self.rel(a, b, "IMPAIRMENT", "impairment"), "SUBSTANTIVE_CHANGE")
        policy = {"review_base_delay_ms": 1000, "max_review_attempts": 3, "max_backoff_ms": 10000}
        registry = {}
        for text, rid in ((a, "r1"), (b, "r2")):
            sig = _sig(text, "IMPAIRMENT", "impairment")
            lifecycle.observe(registry, {"statement_id": lifecycle.statement_id(sig), "event": "IMPAIRMENT",
                                         "semantics": sem(text, "IMPAIRMENT", "impairment"), "novelty": "FIRST_SEEN",
                                         "fingerprint": sig, "statement": text, "accession": rid, "record_id": rid,
                                         "content_hash": rid},
                              result_id=rid, now_ms=DOC_MS, complete=True, policy=policy)
        self.assertEqual(len(registry), 2, "changed statement silently merged into the earlier entry")

    def test_f04_changed_third_party_actor_is_substantive(self):
        # P2. Supplier -> customer changes the actor of the risk: SUBSTANTIVE_CHANGE.
        a = ("A cybersecurity incident at one of our key suppliers could disrupt our manufacturing operations and "
             "harm our results.")
        self.assertEqual(self.rel(a, a.replace("suppliers", "customers"), "CYBERSECURITY_INCIDENT",
                                  "cybersecurity incident"), "SUBSTANTIVE_CHANGE")

    def test_f05_changed_officer_is_substantive(self):
        # P2. CEO -> CFO changes who may depart: SUBSTANTIVE_CHANGE.
        a = ("Our Chief Executive Officer may resign at any time, and the loss of key personnel could harm our "
             "business and results of operations.")
        b = a.replace("Chief Executive Officer", "Chief Financial Officer")
        self.assertEqual(self.rel(a, b, "OFFICER_DEPARTURE", "Officer may resign"), "SUBSTANTIVE_CHANGE")

    def test_f06_changed_scale_word_is_substantive(self):
        # P2. "$1.2 billion" -> "$1.2 million" is an amount change (anchor "$1.2" ignores the scale word).
        a = "We expect to record an impairment charge of $1.2 billion in the fourth quarter of fiscal 2027."
        self.assertEqual(self.rel(a, a.replace("billion", "million"), "IMPAIRMENT", "impairment"),
                         "SUBSTANTIVE_CHANGE")


if __name__ == "__main__":
    unittest.main()

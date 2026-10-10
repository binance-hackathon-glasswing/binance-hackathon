"""Fact extraction, claim verification, rounding-aware conflicts and comparisons."""

from fractions import Fraction
import unittest

from larp.intelligence.facts import KEYWORD_EVENTS, extract_document, item_events, normalized, parse_period, periods_in
from larp.intelligence.issuers import IssuerRegistry
from larp.intelligence.scenarios import EXMEM, EXSEMI, FILINGS, FIXTURE_REGISTRY
from larp.intelligence.text import document_text
from larp.intelligence.verify import compare, detect_conflicts, fact_as_claim, verify_claim

REGISTRY = IssuerRegistry.from_dict(FIXTURE_REGISTRY)


def extract(key, index, accession=None, issuer=EXSEMI):
    spec = FILINGS[key]
    d = spec["documents"][index]
    saved = document_text(d["content"], d["name"], d.get("content_type"))
    source = {"record_id": f"rec:{key}", "accession": accession or spec["accession"], "doc_name": d["name"],
              "available_ms": 1, "original_ms": 0}
    return saved, extract_document(saved.text, saved.text_sha256, REGISTRY.by_issuer(issuer), source)


def pick(facts, kind, metric, period, scale=None):
    return [f for f in facts if (f["kind"], f["metric"], f["period"]) == (kind, metric, period)
            and (scale is None or f["scale_exp10"] == scale)]


class PeriodTests(unittest.TestCase):
    def test_canonical_periods(self):
        cases = {"third quarter of fiscal 2027": "FY2027-Q3", "Q3 FY27": "FY2027-Q3", "fiscal 2027 first quarter": "FY2027-Q1",
                 "Q1 2026": "2026-Q1", "fiscal year 2026": "FY2026", "the third fiscal quarter of 2027": "FY2027-Q3",
                 "third quarter of 2026": "2026-Q3", "Q2'26": "2026-Q2"}
        for text, label in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_period(text), label)
        self.assertIsNone(parse_period("Q3 FY27 versus Q2 FY27"))  # ambiguous: two periods
        self.assertEqual([p[0] for p in periods_in("Q3 FY27 versus Q2 FY27")], ["FY2027-Q3", "FY2027-Q2"])
        self.assertIsNone(parse_period("in 2026"))  # a bare year is not a period


class ExtractionTests(unittest.TestCase):
    def test_press_release_text_and_table_facts(self):
        _, facts = extract("EXSEMI_Q3_8K", 1)
        text_rev = pick(facts, "REPORTED", "revenue", "FY2027-Q3", 9)[0]
        table_rev = pick(facts, "REPORTED", "revenue", "FY2027-Q3", 6)[0]
        self.assertEqual((text_rev["value"], text_rev["unit"], text_rev["precision_exp10"]), ([351, 10], "USD", 8))
        self.assertEqual((table_rev["value"], table_rev["precision_exp10"]), ([35082, 1], 6))
        self.assertIn("Revenue | $35,082", table_rev["span"]["text"])
        guide = pick(facts, "GUIDANCE", "revenue", "FY2027-Q4")[0]
        self.assertEqual((guide["value"], guide["tolerance_pct"]), ([33, 1], [2, 1]))
        margin = pick(facts, "REPORTED", "gross_margin", "FY2027-Q2")[0]
        self.assertEqual((margin["value"], margin["unit"]), ([751, 10], "PERCENT"))
        self.assertEqual(detect_conflicts(facts), [])  # "$35.1 billion" agrees with "35,082" million

    def test_every_extracted_fact_passes_the_verifier(self):
        for key, index, issuer in (("EXSEMI_Q3_8K", 1, EXSEMI), ("EXSEMI_Q2_8K", 1, EXSEMI),
                                   ("EXSEMI_Q3_10Q_COMPACT", 0, EXSEMI), ("EXMEM_Q3_6K", 1, EXMEM),
                                   ("EXSEMI_402_8K", 0, EXSEMI), ("EXMEM_CYBER_6K", 0, EXMEM)):
            saved, facts = extract(key, index, issuer=issuer)
            self.assertTrue(facts, key)
            for f in facts:
                with self.subTest(key=key, metric=f["metric"], period=f["period"]):
                    verified, reason = verify_claim(fact_as_claim(f), {saved.text_sha256: saved.text}, None)
                    self.assertIsNone(reason)
                    self.assertEqual(normalized(verified), normalized(f))

    def test_korean_won_scales_and_currency(self):
        _, facts = extract("EXMEM_Q3_6K", 1, issuer=EXMEM)
        text_rev = pick(facts, "REPORTED", "revenue", "2026-Q3", 12)[0]
        table_rev = pick(facts, "REPORTED", "revenue", "2026-Q3", 9)[0]
        self.assertEqual((text_rev["unit"], table_rev["unit"]), ("KRW", "KRW"))
        self.assertEqual(normalized(text_rev), Fraction(2445, 100) * 10 ** 12)
        self.assertIn("Korean won", table_rev["scale_span"]["text"])
        self.assertEqual(detect_conflicts(facts), [])

    def test_events_from_item_metadata_and_keywords(self):
        _, facts = extract("EXSEMI_402_8K", 0)
        self.assertIn("RESTATEMENT", {f["metric"] for f in facts})
        record = {"record_id": "r", "accession": "a", "items": ["4.02"], "available_ms": 1, "original_ms": 0}
        self.assertEqual([f["metric"] for f in item_events(record)], ["ITEM:4.02"])
        negated = document_text(b"<p>The company recorded no impairment in the quarter.</p>", "n.htm")
        self.assertEqual(extract_document(negated.text, negated.text_sha256, REGISTRY.by_issuer(EXSEMI),
                                          {"accession": "a"}), [])

    def test_per_share_scope_is_ambiguous_when_an_issuer_has_several_listings(self):
        saved = document_text(b"<p>Diluted earnings per share for the third quarter of 2026 was KRW 3,200.</p>", "e.htm")
        facts = extract_document(saved.text, saved.text_sha256, REGISTRY.by_issuer(EXMEM), {"accession": "a"})
        self.assertEqual(facts[0]["security_scope"], "AMBIGUOUS")
        domestic = extract_document(saved.text.replace("KRW 3,200", "$1.20"), saved.text_sha256,
                                    REGISTRY.by_issuer(EXSEMI), {"accession": "a"})
        self.assertEqual(domestic[0]["security_scope"], "XFIX:EXSM")


INCOME_TABLE = (
    b"<p>Condensed statements of income</p>"
    b"<table><tr><td>(In millions, except per share data)</td></tr><tr><td></td><td>Q3 FY27</td><td>Q2 FY27</td></tr>"
    b"<tr><td>Revenue</td><td>$35,082</td><td>$30,040</td></tr>"
    b"<tr><td>Diluted EPS</td><td>$1.20</td><td>$1.05</td></tr></table>")
INCOME_PROSE = (b"<p>Revenue for the third quarter of fiscal 2027 was $35.1 billion, and diluted earnings per share "
                b"for the third quarter of fiscal 2027 was $1.20.</p>")


class PerShareScaleTests(unittest.TestCase):
    def facts(self, html):
        saved = document_text(html, "income.htm")
        return saved, extract_document(saved.text, saved.text_sha256, REGISTRY.by_issuer(EXSEMI),
                                       {"accession": "a"})

    def test_per_share_rows_keep_their_amounts_under_the_exception(self):
        saved, facts = self.facts(INCOME_TABLE)
        eps = {f["period"]: f for f in facts if f["metric"] == "eps_diluted"}
        self.assertEqual({p: (normalized(f), f["scale_exp10"]) for p, f in eps.items()},
                         {"FY2027-Q3": (Fraction(6, 5), 0), "FY2027-Q2": (Fraction(21, 20), 0)})
        revenue = pick(facts, "REPORTED", "revenue", "FY2027-Q3", 6)[0]
        self.assertEqual(normalized(revenue), 35082 * 10 ** 6)  # the exception does not unscale other rows
        texts = {saved.text_sha256: saved.text}
        for f in facts:
            with self.subTest(metric=f["metric"], period=f["period"]):
                self.assertIsNone(verify_claim(fact_as_claim(f), texts, None)[1])
        wrong = dict(fact_as_claim(eps["FY2027-Q3"]), scale_exp10=6)  # $1.2 million per share
        self.assertEqual(verify_claim(wrong, texts, None)[1], "SCALE_NOT_STATED")

    def test_table_and_equivalent_prose_agree(self):
        saved, facts = self.facts(INCOME_TABLE + INCOME_PROSE)
        prose_eps = [f for f in facts if f["metric"] == "eps_diluted" and f["basis"] == "SENTENCE_V1"]
        self.assertEqual([(f["period"], normalized(f), f["scale_exp10"]) for f in prose_eps],
                         [("FY2027-Q3", Fraction(6, 5), 0)])
        self.assertEqual({normalized(f) for f in pick(facts, "REPORTED", "revenue", "FY2027-Q3")},
                         {Fraction(351, 10) * 10 ** 9, 35082 * 10 ** 6})
        self.assertEqual(detect_conflicts(facts), [])  # "$35.1 billion" ~ 35,082 million; $1.20 = $1.20
        texts = {saved.text_sha256: saved.text}
        self.assertEqual(verify_claim(dict(fact_as_claim(prose_eps[0]), scale_exp10=6), texts, None)[1],
                         "SCALE_NOT_STATED")

    def test_scaled_table_without_the_exception_gives_no_per_share_fact(self):
        _, facts = self.facts(INCOME_TABLE.replace(b"(In millions, except per share data)", b"(In millions)"))
        self.assertEqual([f for f in facts if f["metric"] == "eps_diluted"], [])
        self.assertTrue(pick(facts, "REPORTED", "revenue", "FY2027-Q3", 6))


# Common "no event" boilerplate: negation before the keyword, after it, or on the verb that governs it.
NEGATED_EVENTS = (
    ("IMPAIRMENT", "The company recorded no impairment in the quarter."),
    ("IMPAIRMENT", "No goodwill or intangible asset impairment charges were recognized."),
    ("IMPAIRMENT", "There were no indicators of impairment."),
    ("IMPAIRMENT", "An impairment charge was not required in the quarter."),
    ("IMPAIRMENT", "Management concluded that goodwill impairment was not necessary."),
    ("IMPAIRMENT", "We did not identify any events or circumstances that would indicate an impairment."),
    ("RESTATEMENT", "The Audit Committee concluded that a restatement of prior financial statements is not required."),
)
# Modal, conditional and forward-looking wording (risk factors, outlook): possible or planned, not reported.
HYPOTHETICAL_EVENTS = (
    ("IMPAIRMENT", "Goodwill impairment could result if the operating results of the segment decline."),
    ("IMPAIRMENT", "We may be required to record an impairment of goodwill in future periods."),
    ("IMPAIRMENT", "If our stock price declines, we might recognize an impairment charge."),
    ("IMPAIRMENT", "We expect to record an impairment charge in the fourth quarter."),
    ("RESTATEMENT", "Any future restatement of our financial statements would harm investor confidence."),
    ("DELISTING", "There is a risk that our common stock could be delisted from the exchange."),
    ("CYBERSECURITY_INCIDENT", "A cybersecurity incident could disrupt our operations."),
    ("OFFICER_DEPARTURE", "Our Chief Executive Officer may resign at any time."),
)
AFFIRMED_EVENTS = (
    ("IMPAIRMENT", "The company recorded a goodwill impairment of $12 million in the quarter."),
    ("IMPAIRMENT", "We recorded a goodwill impairment of $12 million; further impairments may follow."),
    ("OFFICER_DEPARTURE", "On May 12, 2026, the Chief Financial Officer resigned."),
    ("IMPAIRMENT", "We recorded an impairment charge on the Boise facility, but no restructuring charge was required."),
    ("OFFICER_DEPARTURE", "The Chief Financial Officer will resign effective no later than November 30, 2026."),
    ("RESTATEMENT", "The Audit Committee concluded that the previously issued financial statements "
                    "should no longer be relied upon."),
)


class NegationScopeTests(unittest.TestCase):
    """The extractor and the verifier read an event's whole clause, in both directions, for negation and for
    hypothetical wording."""

    def check(self, metric, sentence, *quotes):
        """Whether the extractor finds `metric`, and the verifier's reason for a claim quoting each of `quotes`."""
        saved = document_text(f"<p>{sentence}</p>".encode(), "n.htm")
        facts = extract_document(saved.text, saved.text_sha256, REGISTRY.by_issuer(EXSEMI), {"accession": "a"})
        events = {f["metric"] for f in facts if f["kind"] == "EVENT"}
        texts = {saved.text_sha256: saved.text}
        reasons = []
        for quoted in quotes:
            start = saved.text.index(quoted)
            claim = {"kind": "EVENT", "metric": metric,
                     "span": {"doc": saved.text_sha256, "start": start, "end": start + len(quoted), "text": quoted}}
            reasons.append(verify_claim(claim, texts, None)[1])
        return metric in events, reasons

    def test_negated_or_hypothetical_events_give_no_fact_and_are_not_verified(self):
        patterns = dict(KEYWORD_EVENTS)
        for events, reason in ((NEGATED_EVENTS, "EVENT_NEGATED"), (HYPOTHETICAL_EVENTS, "EVENT_HYPOTHETICAL")):
            for metric, sentence in events:
                with self.subTest(sentence=sentence):
                    keyword = patterns[metric].search(sentence).group(0)
                    self.assertEqual(self.check(metric, sentence, sentence, keyword), (False, [reason] * 2))

    def test_affirmed_events_still_give_a_fact_and_verify(self):
        for metric, sentence in AFFIRMED_EVENTS:
            with self.subTest(sentence=sentence):
                self.assertEqual(self.check(metric, sentence, sentence), (True, [None]))


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.saved, facts = extract("EXSEMI_Q3_8K", 1)
        self.texts = {self.saved.text_sha256: self.saved.text}
        self.fact = pick(facts, "REPORTED", "revenue", "FY2027-Q3", 9)[0]
        self.table = pick(facts, "REPORTED", "revenue", "FY2027-Q2", 6)[0]

    def rejected(self, claim):
        return verify_claim(claim, self.texts, None)[1]

    def test_tampering_is_rejected_with_a_reason(self):
        good = fact_as_claim(self.fact)
        span = good["span"]
        cases = {
            "SPAN_TEXT_MISMATCH": dict(good, span=dict(span, text=span["text"].replace("35.1", "39.1"))),
            "SPAN_OFFSETS_INVALID": dict(good, span=dict(span, start=-1)),
            "SPAN_DOCUMENT_NOT_LOADED": dict(good, span=dict(span, doc="0" * 64)),
            "NUMBER_NOT_IN_SPAN": dict(good, value="36.1"),
            "SCALE_NOT_STATED": dict(good, scale_exp10=6),
            "UNIT_NOT_STATED": dict(good, unit="KRW"),
            "PERIOD_NOT_STATED": dict(good, period="FY2027-Q4"),
            "KIND_NOT_ALLOWED": dict(good, kind="CONSENSUS"),
            "METRIC_NOT_IN_SPAN": dict(good, metric="net_income"),
            "VALUE_MALFORMED": dict(good, value="35.1e0"),
            "ITEM_NOT_IN_RECORD": {"kind": "EVENT", "metric": "ITEM:4.02", "source": {"record_id": "r"}},
        }
        for reason, claim in cases.items():
            with self.subTest(reason=reason):
                self.assertEqual(self.rejected(claim), reason)

    def test_years_and_dates_inside_the_span_are_not_stated_amounts(self):
        self.assertEqual(self.rejected(dict(fact_as_claim(self.fact), value="2027")), "NUMBER_NOT_IN_SPAN")

    def test_table_value_must_be_the_last_cell_in_the_span(self):
        claim = fact_as_claim(self.table)
        self.assertIsNone(self.rejected(claim))
        self.assertEqual(self.rejected(dict(claim, value=[35082, 1])), "TABLE_VALUE_NOT_LAST_CELL")

    def test_malformed_nested_fields_are_rejected_before_use(self):
        good = fact_as_claim(self.fact)
        cases = {
            "SOURCE_MALFORMED": [dict(good, source="oops"), dict(good, source={"record_id": ["r"]}),
                                 dict(good, source={"url": "x"})],
            "SPAN_MALFORMED": [dict(good, span="x"), dict(good, span=dict(good["span"], doc=["a"])),
                               dict(good, span=dict(good["span"], start="0"))],
            "PERIOD_SPAN_MALFORMED": [dict(good, period_span=7)],
            "RANGE_MALFORMED": [dict(good, range=1), dict(good, range=["1"])],
            "METRIC_MALFORMED": [dict(good, metric=["revenue"])],
            "UNIT_MALFORMED": [dict(good, unit={"USD": 1})],
            "SCALE_MALFORMED": [dict(good, scale_exp10="9")],
            "CLAIM_UNKNOWN_FIELD": [dict(good, confidence="high")],
            "CLAIM_MALFORMED": [5, None, ["claim"]],
        }
        for reason, claims in cases.items():
            for claim in claims:
                with self.subTest(reason=reason, claim=str(claim)[:60]):
                    self.assertEqual(verify_claim(claim, self.texts, {})[1], reason)

    def test_provenance_comes_from_the_record_holding_the_cited_document(self):
        claim = dict(fact_as_claim(self.fact), source={"record_id": "rec:current", "accession": "forged"})
        record = {"record_id": "rec:current", "accession": "0009900001-26-000187", "available_ms": 5,
                  "original_ms": 4, "items": [], "documents": [{"name": "ex991.htm", "text_sha256": self.saved.text_sha256}]}
        fact, reason = verify_claim(claim, self.texts, {"rec:current": record})
        self.assertIsNone(reason)
        self.assertEqual(fact["source"], {"record_id": "rec:current", "accession": "0009900001-26-000187",
                                          "doc_name": "ex991.htm", "available_ms": 5, "original_ms": 4})
        other = dict(record, documents=[{"name": "other.htm", "text_sha256": "1" * 64}])
        self.assertEqual(verify_claim(claim, self.texts, {"rec:current": other})[1], "SPAN_NOT_IN_SOURCE_RECORD")
        self.assertEqual(verify_claim(claim, self.texts, {})[1], "SOURCE_RECORD_UNKNOWN")
        self.assertEqual(verify_claim(dict(claim, source=None), self.texts, {})[1], "SOURCE_RECORD_UNKNOWN")

    def test_period_and_scale_spans_belong_to_the_cited_statement(self):
        claim = fact_as_claim(self.table)  # "Revenue | $35,082 | $30,040", column Q2 FY27
        q3_header = fact_as_claim(pick(extract("EXSEMI_Q3_8K", 1)[1], "REPORTED", "revenue", "FY2027-Q3", 6)[0])
        self.assertEqual(self.rejected(dict(claim, period="FY2027-Q3", period_span=q3_header["period_span"])),
                         "PERIOD_NOT_TABLE_COLUMN")  # the other column's header
        self.assertEqual(self.rejected(dict(claim, scale_span=None)), "SCALE_SPAN_NOT_TABLE_SCALE")
        self.assertEqual(self.rejected(dict(claim, scale_exp10=0, scale_span=None)), "SCALE_NOT_STATED")
        self.assertEqual(self.rejected(dict(claim, scale_exp10=9)), "SCALE_NOT_STATED")
        prose = fact_as_claim(self.fact)
        copy = dict(self.texts, **{"a" * 64: self.saved.text})  # same words, another loaded document
        moved = dict(prose, period_span=dict(prose["period_span"], doc="a" * 64))
        self.assertEqual(verify_claim(moved, copy, None)[1], "PERIOD_SPAN_OTHER_DOCUMENT")
        elsewhere = self.saved.text.index("fourth quarter of fiscal 2027")
        span = {"doc": self.saved.text_sha256, "start": elsewhere, "end": elsewhere + len("fourth quarter of fiscal 2027"),
                "text": "fourth quarter of fiscal 2027"}
        self.assertEqual(self.rejected(dict(prose, period="FY2027-Q4", period_span=span)), "PERIOD_SPAN_OUTSIDE_STATEMENT")

    def test_negated_events_are_not_verified(self):
        saved = document_text(b"<p>The company recorded no impairment in the quarter.</p>"
                              b"<p>The company recorded an impairment of goodwill.</p>", "n.htm")
        texts = {saved.text_sha256: saved.text}

        def claim(sentence):
            start = saved.text.index(sentence)
            return {"kind": "EVENT", "metric": "IMPAIRMENT",
                    "span": {"doc": saved.text_sha256, "start": start, "end": start + len(sentence), "text": sentence}}

        self.assertEqual(verify_claim(claim("impairment in the quarter"), texts, None)[1], "EVENT_NEGATED")
        self.assertEqual(verify_claim(claim("The company recorded no impairment in the quarter."), texts, None)[1],
                         "EVENT_NEGATED")
        self.assertEqual(verify_claim(claim("recorded no"), texts, None)[1], "EVENT_NOT_IN_SPAN")
        fact, reason = verify_claim(claim("impairment of goodwill"), texts, None)
        self.assertIsNone(reason)
        self.assertEqual((fact["metric"], fact["value"], fact["period"]), ("IMPAIRMENT", None, None))

    def test_claimed_precision_is_recomputed_from_the_span(self):
        fact, reason = verify_claim(dict(fact_as_claim(self.fact), precision_exp10=0), self.texts, None)
        self.assertIsNone(reason)
        self.assertEqual(fact["precision_exp10"], 8)


class ComparisonTests(unittest.TestCase):
    def base(self, **kw):
        fact = {"fact_id": kw.pop("fact_id", "f"), "kind": "GUIDANCE", "metric": "revenue", "period": "FY2027-Q4",
                "value": [36, 1], "range": None, "tolerance_pct": None, "unit": "USD", "scale_exp10": 9,
                "precision_exp10": 8, "security_scope": "ISSUER", "source": {"accession": "a"}}
        fact.update(kw)
        return fact

    def test_guidance_and_reported_comparisons(self):
        lowered = compare(self.base(fact_id="n", value=[33, 1]), self.base(fact_id="p"))
        self.assertEqual((lowered["relation"], lowered["delta"]), ("LOWER", [-3000000000, 1]))
        self.assertEqual(compare(self.base(value=[3604, 100], precision_exp10=7), self.base())["relation"], "EQUAL")
        prior = self.base(fact_id="p", period="FY2027-Q3", value=[325, 10], tolerance_pct=[2, 1])
        for value, relation in (([351, 10], "ABOVE"), ([32, 1], "WITHIN"), ([31, 1], "BELOW")):
            with self.subTest(value=value):
                self.assertEqual(compare(self.base(kind="REPORTED", period="FY2027-Q3", value=value), prior)["relation"],
                                 relation)

    def test_incomparable_units_instruments_and_period_bases(self):
        prior = self.base(fact_id="p")
        for change in ({"unit": "KRW"}, {"security_scope": "AMBIGUOUS"}, {"period": "2027-Q4"}, {"metric": "net_income"}):
            with self.subTest(change=change):
                self.assertEqual(compare(self.base(**change), prior)["relation"], "INCOMPARABLE")

    def test_contradictory_reported_values_conflict_across_filings(self):
        _, original = extract("EXSEMI_Q3_8K", 1)
        _, amended = extract("EXSEMI_Q3_8KA", 1)
        conflicts = detect_conflicts(original + amended)
        self.assertEqual([(c["metric"], c["period"]) for c in conflicts], [("revenue", "FY2027-Q3")])
        self.assertEqual(len(conflicts[0]["accessions"]), 2)


if __name__ == "__main__":
    unittest.main()

"""IDEA-044 intelligence/source regressions; synthetic documents and injected HTTP only."""

from dataclasses import replace
import copy
import json
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from larp.intelligence.agent import build_request, EMPTY_CONTEXT
from larp.intelligence.common import IntelligenceError
from larp.intelligence.edgar import EdgarHttpSource, _urllib_get, listing_rows
from larp.intelligence.gate import accept, initial_state
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.redflags import load_predicates, verify_item
from larp.intelligence.scenarios import EXSEMI, PROFILE, RUN_ID, build_world, doc, page, p
from larp.intelligence.tools import PortEvidenceReader
from tests.intelligence.test_ingest import IngestHarness, AT_2030


class EdgarBoundaries(unittest.TestCase):
    def test_default_transport_refuses_redirects_and_disables_environment_proxies(self):
        def opener(*handlers):
            redirect = next(h for h in handlers if isinstance(h, urllib.request.HTTPRedirectHandler))
            self.assertIsNone(redirect.redirect_request(None, None, 302, "found", {}, "https://attacker.invalid"))
            self.assertEqual(next(h for h in handlers if isinstance(h, urllib.request.ProxyHandler)).proxies, {})

            class Refusal:
                def open(self, request, timeout):
                    raise urllib.error.HTTPError(request.full_url, 302, "found", {}, None)
            return Refusal()

        with patch("larp.intelligence.edgar.urllib.request.build_opener", side_effect=opener):
            self.assertEqual(_urllib_get("https://www.sec.gov/file", {}, 1), (302, None, b""))

    def test_bound_is_enforced_for_injected_and_default_readers(self):
        class Reply:
            status, headers = 200, {}
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
            def read(self, size):
                self.size = size
                return b"1234"

        reply = Reply()
        with patch("larp.intelligence.edgar.MAX_RESPONSE_BYTES", 3), \
                patch("larp.intelligence.edgar.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = reply
            source = EdgarHttpSource("Test reviewer@fixture.invalid", sleep=lambda _: None)
            self.assertEqual(source.list_filings(1).status, "UNAVAILABLE")
            self.assertEqual(reply.size, 4)
            injected = EdgarHttpSource("Test reviewer@fixture.invalid", sleep=lambda _: None,
                                       http_get=lambda *_: (200, "application/json", b"1234"))
            self.assertEqual(injected.list_filings(1).status, "UNAVAILABLE")

    def test_userinfo_and_odd_ports_are_refused_before_network(self):
        calls = []
        source = EdgarHttpSource("Test reviewer@fixture.invalid", http_get=lambda *args: calls.append(args))
        for url in ("https://user:pass@www.sec.gov/x", "https://www.sec.gov:444/x",
                    "https://www.sec.gov:bad/x", "http://www.sec.gov/x"):
            with self.subTest(url=url), self.assertRaises(IntelligenceError):
                source._fetch(url)
        self.assertEqual(calls, [])

    def test_structurally_malformed_listings_are_not_empty_successes(self):
        for value in ({}, {"filings": []}, {"filings": {"recent": []}},
                      {"filings": {"recent": {}}}, {"filings": {"recent": {"form": ["8-K"]}}},
                      {"filings": {"recent": {"accessionNumber": [], "form": ["8-K"]}}},
                      {"filings": {"recent": {"accessionNumber": "not-a-list"}}}):
            with self.subTest(value=value), self.assertRaises(IntelligenceError):
                listing_rows(value)
        self.assertEqual(listing_rows({"filings": {"recent": {"accessionNumber": [], "form": []}}}), ())

    def test_malformed_history_metadata_is_partial_without_network_escape(self):
        for filings in ([], {"recent": {}, "files": "not-an-array"}):
            raw = json.dumps({"cik": "1", "filings": filings}).encode()
            source = EdgarHttpSource("Test reviewer@fixture.invalid", sleep=lambda _: None,
                                     http_get=lambda *_: (200, "application/json", raw))
            result = source.list_filings(1, (0, 1))
            if type(filings) is list:
                self.assertEqual(result.status, "INVALID")
            else:
                self.assertEqual(result.history_status, "PARTIAL")


class EdgarCoverage(IngestHarness):
    def test_document_limit_is_visible_to_assessor_and_gate(self):
        self.config = replace(self.config, limits=dict(self.config.limits, max_documents_per_filing=1))
        self.ingestor = self.make_ingestor()
        spec = self.add("EXSEMI_Q3_8K")
        outcome = self.poll()
        record = self.records()[0]
        self.assertTrue(record["incomplete"])
        self.assertFalse(outcome["coverage_complete"])
        later = self.poll()  # the bound is permanent; it stays on the record, not on the issuer
        self.assertTrue(later["coverage_complete"])
        self.assertEqual(self.cursor()["health"]["status"], "OK")
        self.assertTrue(self.records()[-1]["incomplete"])
        request = build_request(job={"job_id": "bounded-read"}, run_id=RUN_ID, issuer_id=EXSEMI,
                                records=[record], cutoff_ms=self.clock(), context=EMPTY_CONTEXT,
                                policy_profile_hash=PROFILE, allowed_tools=list(self.config.tools), tool_calls=6,
                                deadline_ms=60000, source_health=self.cursor()["health"])
        from larp.intelligence.agent import EvidenceAssessor
        result = EvidenceAssessor(registry=self.registry, reader=PortEvidenceReader(self.store, self.artifacts),
                                  config=self.config, clock_ms=self.clock,
                                  model=RuleBaselineModel(self.clock)).assess(request)
        self.assertFalse(result.read()["coverage"]["complete"])
        decision, state = accept(initial_state(EXSEMI, PROFILE), result, profile_hash=PROFILE, now_ms=self.clock())
        self.assertEqual(decision, "ACCEPT")
        self.assertNotEqual(state["evidence_gate"], "CLEAR")
        self.config = replace(self.config, limits=dict(self.config.limits, max_documents_per_filing=6))
        self.ingestor = self.make_ingestor()
        self.assertEqual(len(self.poll(recheck=frozenset({spec["accession"]}))["revisions"]), 1)
        self.assertFalse(self.records()[-1]["incomplete"])
        self.assertEqual(self.cursor()["health"]["status"], "OK")

    def test_index_recovery_with_same_document_bytes_creates_complete_revision(self):
        self.config = replace(self.config, limits=dict(self.config.limits, max_fetch_attempts=1))
        self.ingestor = self.make_ingestor()
        spec = self.add("EXSEMI_Q3_8K")
        original = self.source.fetch_filing
        self.source.fetch_filing = lambda *args: replace(original(*args), index_status="FAILED")
        self.poll()
        self.assertTrue(self.records()[0]["incomplete"])
        self.source.fetch_filing = original
        outcome = self.poll(recheck=frozenset({spec["accession"]}))
        self.assertEqual(len(outcome["revisions"]), 1)
        self.assertFalse(self.records()[-1]["incomplete"])
        self.assertEqual(self.records()[-1]["revision"], 1)
        self.assertTrue(outcome["coverage_complete"])

    def test_retry_and_dead_letter_keep_source_incomplete_until_recovery(self):
        spec = self.add("EXSEMI_402_8K", acceptance=AT_2030)
        key = spec["accession"], spec["documents"][0]["name"]
        self.source.failing_documents[key] = 3
        for _ in range(3):
            self.assertFalse(self.poll()["coverage_complete"])
            self.assertEqual(self.cursor()["health"]["status"], "INCOMPLETE")
        # Once dead-lettered, the unreadable filing is a MISSING record (FILING_UNREADABLE to
        # assessments) and no longer stalls the whole issuer on ordinary polls.
        self.assertTrue(self.poll()["coverage_complete"])
        self.assertEqual(self.cursor()["health"]["status"], "OK")
        self.assertIn(spec["accession"], self.cursor()["dead_letter"])
        self.assertEqual(self.records()[-1]["quality"], "MISSING")
        self.assertTrue(self.poll(recheck=frozenset({spec["accession"]}))["coverage_complete"])
        self.assertEqual(self.cursor()["dead_letter"], {})

    def with_rows(self, *rows):
        original = self.source.list_filings
        def listing(*args, **kwargs):
            result = original(*args, **kwargs)
            recent = result.submissions["filings"]["recent"]
            for accession, form, acceptance, primary in rows:
                for key, value in (("accessionNumber", accession), ("form", form), ("items", ""),
                                   ("acceptanceDateTime", acceptance), ("filingDate", acceptance[:10]),
                                   ("reportDate", ""), ("primaryDocument", primary)):
                    recent[key].append(value)
            return result
        self.source.list_filings = listing

    def test_only_in_scope_or_undatable_listing_gaps_mark_coverage_incomplete(self):
        from larp.intelligence.ingest import ALL_PERIODIC_AND_CURRENT
        entry = self.registry.by_issuer(EXSEMI)
        unexpected = sorted(f for f in ALL_PERIODIC_AND_CURRENT if entry.form_class(f) is None)[0]
        old, recent = "2010-03-01T16:00:00-05:00", "2026-10-01T20:00:00+00:00"
        cases = [((("0009900001-10-000001", "8-K", old, ""), ("0009900001-10-000002", unexpected, old, "a.htm")),
                  True),
                 ((("0009900001-26-000901", "8-K", recent, ""),), False),
                 ((("0009900001-26-000902", unexpected, recent, "a.htm"),), False),
                 ((("0009900001-26-000903", "8-K", "not-a-time", ""),), False)]
        for rows, complete in cases:
            with self.subTest(rows=rows):
                self.setUp()
                self.with_rows(*rows)
                outcome = self.poll()
                self.assertEqual(outcome["coverage_complete"], complete)
                self.assertEqual(self.cursor()["health"]["status"], "OK" if complete else "INCOMPLETE")
                self.assertEqual(self.poll()["coverage_complete"], complete)  # relisting is judged the same

    def test_malformed_rows_of_unwatched_forms_are_not_coverage_gaps(self):
        # IDEA-044 V12: a readable form that no issuer class watches cannot hide watched evidence.
        from larp.intelligence.ingest import ALL_PERIODIC_AND_CURRENT
        entry = self.registry.by_issuer(EXSEMI)
        watched = next(f for f in ("8-K", "6-K") if entry.form_class(f) is not None)
        other = sorted(f for f in ALL_PERIODIC_AND_CURRENT if entry.form_class(f) is None)[0]
        recent = "2026-10-01T20:00:00+00:00"
        cases = [((("0009900001-26-000911", "4", recent, ""),), True),
                 ((("0009900001-26-000912", "SC 13G", "not-a-time", ""),), True),
                 ((("0009900001-26-000913", watched, recent, ""),), False),
                 ((("0009900001-26-000914", other, recent, ""),), False),
                 ((("0009900001-26-000915", "", recent, ""),), False)]
        for rows, complete in cases:
            with self.subTest(rows=rows):
                self.setUp()
                self.with_rows(*rows)
                outcome = self.poll()
                self.assertEqual(outcome["coverage_complete"], complete)
                self.assertEqual(self.cursor()["health"]["status"], "OK" if complete else "INCOMPLETE")
                self.assertEqual(outcome["malformed_rows"], 0 if complete else 1)
                self.assertEqual(self.poll()["coverage_complete"], complete)

    def test_bad_listing_preserves_unavailable_health_without_records(self):
        self.add("EXSEMI_Q3_8K")
        original = self.source.list_filings
        def broken(*args, **kwargs):
            listing = original(*args, **kwargs)
            listing.submissions["filings"]["recent"]["form"] = "8-K"
            return listing
        self.source.list_filings = broken
        self.assertEqual(self.poll()["status"], "INVALID_SOURCE")
        self.assertEqual(self.cursor()["health"]["status"], "UNAVAILABLE")
        self.assertEqual(self.records(), [])

    def test_failed_recheck_retries_without_repeating_recheck_flag(self):
        spec = self.add("EXSEMI_Q3_8K")
        self.poll()
        name = spec["documents"][0]["name"]
        self.source.replace_document(spec["accession"], name, spec["documents"][0]["content"] + b"<p>Correction.</p>")
        self.source.failing_documents[spec["accession"], name] = 1
        failed = self.poll(recheck=frozenset({spec["accession"]}))
        self.assertEqual(failed["retry_pending"], [spec["accession"]])
        self.assertFalse(failed["coverage_complete"])
        recovered = self.poll()
        self.assertEqual(len(recovered["revisions"]), 1)
        self.assertTrue(recovered["coverage_complete"])
        self.assertEqual(self.cursor()["pending"], {})
        self.assertEqual(len(self.records()), 2)


class FindingsAndClocks(unittest.TestCase):
    def test_same_event_in_two_filings_retains_both_correction_obligations(self):
        specs = {key: dict(cik=9900001, accession=f"0009900001-26-00030{i}", form="8-K", items=[],
                           acceptance=f"2026-10-0{i + 6}T21:00:00+00:00",
                           documents=[doc(f"{key}.htm", "8-K", page(p(
                               f"We recorded an impairment charge of ${i + 1}.2 billion.")))])
                 for i, key in enumerate(("A", "B"))}
        world = build_world(["A", "B"], extra_filings=specs)
        request = world.request(["A", "B"], issuer_id=EXSEMI, job_id="two-supports")
        result = world.assessor(RuleBaselineModel(world.clock)).assess(request)
        findings = [f for f in result.read()["findings"] if f["type"] == "IMPAIRMENT"]
        self.assertEqual({s["accession"] for f in findings for s in f["sources"]},
                         {s["accession"] for s in specs.values()})
        _, state = accept(initial_state(EXSEMI, PROFILE), result, profile_hash=PROFILE, now_ms=world.clock())
        world.source.replace_document(specs["A"]["accession"], "A.htm", page(p("The earlier disclosure is corrected.")))
        world.clock.advance(1)
        world.ingestor.poll(EXSEMI, recheck=frozenset({specs["A"]["accession"]}))
        correction = world.assessor(RuleBaselineModel(world.clock)).assess(world.request(
            ["A"], issuer_id=EXSEMI, job_id="correct-one", context=state["context"]))
        before = copy.deepcopy(state)
        _, after = accept(state, correction, profile_hash=PROFILE, now_ms=world.clock())
        self.assertEqual(state, before)
        self.assertEqual(after["evidence_gate"], "ADVERSE")
        self.assertTrue(any(s["accession"] == specs["B"]["accession"]
                            for a in after["unresolved_adverse"] for s in a["sources"]))

    def test_future_source_success_is_not_fresh_at_cutoff(self):
        world = build_world(["EXSEMI_402_8K"])
        request = world.request(["EXSEMI_402_8K"], issuer_id=EXSEMI, job_id="future-health",
                                source_health={"status": "OK", "last_success_ms": world.clock() + 1})
        result = world.assessor(RuleBaselineModel(world.clock)).assess(request).read()
        self.assertIn("SOURCE_STALE", result["missingness"])
        self.assertFalse(result["coverage"]["complete"])

    def test_future_event_does_not_verify_even_with_available_text(self):
        world = build_world(["EXSEMI_402_8K"])
        record = world.record("EXSEMI_402_8K")
        texts = {d["text_sha256"]: world.reader.text(d["text_sha256"]) for d in record["documents"]}
        predicates, digest = load_predicates()
        args = dict(record=record, texts=texts, issuer_names=("Example Semiconductor Corp",),
                    filer_class="DOMESTIC", set_sha256=digest)
        self.assertFalse(verify_item(predicates["RF1-ITEM-4.02"], cutoff_ms=record["original_ms"] - 1, **args)["verified"])
        self.assertTrue(verify_item(predicates["RF1-ITEM-4.02"], cutoff_ms=record["original_ms"], **args)["verified"])

"""Point-in-time ingestion through the store port. Synthetic filings and fakes only."""

import hashlib
import json
import unittest

from larp.contracts import Document
from larp.intelligence.common import forbidden_key_paths
from larp.intelligence.config import load_config
from larp.intelligence.edgar import EdgarHttpSource, parse_acceptance_ms
from larp.intelligence.fakes import FakeClock, FakeFilingSource, MemoryArtifacts, MemoryEvidenceStore
from larp.intelligence.ingest import Ingestor
from larp.intelligence.issuers import IssuerRegistry
from larp.intelligence.scenarios import ENTITIES, EXMEM, EXSEMI, FILINGS, FIXTURE_REGISTRY, RUN_ID, cover, doc
from larp.intelligence.text import text_from_saved

MIN = 60_000
Q2_TODAY = "2026-10-01T19:00:00+00:00"
AT_2030 = "2026-10-01T20:30:00+00:00"


class IngestHarness(unittest.TestCase):
    def setUp(self):
        self.config = load_config("development")
        self.registry = IssuerRegistry.from_dict(FIXTURE_REGISTRY)
        # Fixture filings below are re-timed around this clock with acceptance overrides.
        self.clock = FakeClock(parse_acceptance_ms("2026-10-01T21:00:00+00:00"))
        self.source = FakeFilingSource(self.clock, ENTITIES)
        self.store, self.artifacts = MemoryEvidenceStore(), MemoryArtifacts()
        self.ingestor = self.make_ingestor()

    def make_ingestor(self, store=None):
        return Ingestor(registry=self.registry, source=self.source, store=store or self.store, artifacts=self.artifacts,
                        config=self.config, clock_ms=self.clock, run_id=RUN_ID, synthetic=True)

    def add(self, key, visible_ms=None, **override):
        spec = dict(FILINGS[key], **override)
        self.source.add(spec["cik"], accession=spec["accession"], form=spec["form"], items=spec["items"],
                        acceptance=spec["acceptance"], documents=spec["documents"], visible_ms=visible_ms)
        return spec

    def poll(self, issuer=EXSEMI, **kwargs):
        return self.ingestor.poll(issuer, **kwargs).read()

    def records(self, issuer=EXSEMI):
        return [d.read() for d in self.store.records(issuer)]

    def cursor(self, issuer=EXSEMI):
        return self.store.read_cursor("sec-edgar", issuer).read()


class DeliveryTests(IngestHarness):
    def test_records_jobs_and_cursor_commit_together(self):
        self.add("EXSEMI_Q2_8K", acceptance=Q2_TODAY), self.add("EXSEMI_Q3_8K")
        self.add("EXSEMI_402_8K", acceptance="2026-09-01T00:00:00+00:00")  # before the 30-day live floor
        self.clock.advance(5 * MIN)
        outcome = self.poll()
        self.assertEqual((outcome["status"], len(outcome["new_records"]), len(outcome["jobs"])), ("OK", 2, 2))
        cursor = self.cursor()
        self.assertEqual(cursor["version"], 1)
        self.assertEqual(cursor["watermark_ms"], parse_acceptance_ms(FILINGS["EXSEMI_Q3_8K"]["acceptance"]))
        for record in self.records():
            self.assertEqual(record["available_ms"], self.clock())
            self.assertLess(record["original_ms"], record["available_ms"])
            self.assertEqual(record["available_basis"], "FIRST_RETRIEVAL")
            self.assertEqual(record["quality"], "SYNTHETIC")

    def test_duplicate_delivery_creates_nothing_new(self):
        self.add("EXSEMI_Q3_8K")
        first = self.poll()
        jobs = dict(self.store.jobs)
        second = self.poll()
        self.assertEqual((len(second["new_records"]), second["jobs"], second["duplicates"]), (0, [], 1))
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(self.store.jobs, jobs)
        self.assertEqual(len(first["jobs"]), 1)

    def test_replayed_batch_is_idempotent_and_tampered_replay_is_an_integrity_error(self):
        self.add("EXSEMI_Q3_8K")
        outcome = self.poll()
        batch = Document(self.store.batches[outcome["batch_id"]])
        self.assertEqual(self.store.commit(batch).read()["status"], "IDEMPOTENT")
        tampered = batch.read()
        tampered["records"] = []
        self.assertEqual(self.store.commit(Document.from_dict(tampered)).read()["status"], "INTEGRITY_ERROR")

    def test_lost_acknowledgement_then_repoll_does_not_duplicate(self):
        self.add("EXSEMI_Q3_8K")
        self.store.lose_next_ack = True
        with self.assertRaises(ConnectionError):
            self.poll()
        self.clock.advance(MIN)
        again = self.poll()
        self.assertEqual((again["status"], again["new_records"], again["duplicates"]), ("OK", [], 1))
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(len(self.store.jobs), 1)

    def test_late_delivery_is_ingested_once_and_flagged(self):
        early = self.add("EXSEMI_Q2_8K", acceptance=Q2_TODAY, visible_ms=self.clock() + 30 * MIN)
        self.add("EXSEMI_Q3_8K")
        self.clock.advance(10 * MIN)
        self.assertEqual(len(self.poll()["new_records"]), 1)
        self.clock.advance(30 * MIN)
        outcome = self.poll()
        self.assertEqual(outcome["late"], [early["accession"]])
        late = next(r for r in self.records() if r["accession"] == early["accession"])
        self.assertTrue(late["late_delivery"])
        self.assertEqual(late["available_ms"], self.clock())  # never backdated to acceptance time
        self.assertEqual(self.cursor()["watermark_ms"], parse_acceptance_ms(FILINGS["EXSEMI_Q3_8K"]["acceptance"]))

    def test_outage_then_catch_up(self):
        self.add("EXSEMI_Q2_8K", acceptance=Q2_TODAY)
        self.poll()
        self.source.available = False
        self.clock.advance(10 * MIN)
        down = self.poll()
        self.assertEqual((down["status"], down["new_records"], down["jobs"]), ("SOURCE_UNAVAILABLE", [], []))
        health = self.cursor()["health"]
        self.assertEqual((health["status"], health["consecutive_failures"]), ("UNAVAILABLE", 1))
        # Two filings are accepted while the source is down.
        self.add("EXSEMI_Q3_8K", acceptance="2026-10-01T21:15:00+00:00")
        self.add("EXSEMI_402_8K", acceptance="2026-10-01T21:40:00+00:00")
        self.clock.advance(60 * MIN)
        self.assertEqual(self.poll()["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(self.cursor()["health"]["consecutive_failures"], 2)
        self.source.available = True
        self.clock.advance(60 * MIN)
        back = self.poll()
        self.assertEqual((back["status"], len(back["new_records"]), len(back["jobs"]), back["late"]), ("OK", 2, 2, []))
        self.assertEqual(self.cursor()["health"]["status"], "OK")
        caught = [r for r in self.records() if r["accession"] != FILINGS["EXSEMI_Q2_8K"]["accession"]]
        self.assertTrue(all(r["available_ms"] == self.clock() > r["original_ms"] for r in caught))
        self.assertEqual(self.poll()["new_records"], [])


class RevisionAndFailureTests(IngestHarness):
    def test_changed_bytes_create_a_linked_revision(self):
        spec = self.add("EXSEMI_Q3_8K")
        self.poll()
        before = self.records()[0]
        name = spec["documents"][1]["name"]
        self.source.replace_document(spec["accession"], name, spec["documents"][1]["content"] + b"<p>Corrected.</p>")
        self.clock.advance(MIN)
        self.assertEqual(self.poll()["revisions"], [])  # no recheck requested: nothing re-fetched
        outcome = self.poll(recheck=frozenset({spec["accession"]}))
        self.assertEqual(len(outcome["revisions"]), 1)
        revisions = sorted(self.records(), key=lambda r: r["revision"])
        self.assertEqual([r["revision"] for r in revisions], [0, 1])
        self.assertEqual(revisions[1]["supersedes"], before["content_hash"])
        self.assertEqual(revisions[0], before)  # history is never rewritten
        unchanged = self.poll(recheck=frozenset({spec["accession"]}))
        self.assertEqual((unchanged["revisions"], unchanged["duplicates"]), ([], 1))

    def test_primary_fetch_failure_retries_then_dead_letters(self):
        spec = self.add("EXSEMI_402_8K", acceptance=AT_2030)
        self.source.failing_documents[(spec["accession"], spec["documents"][0]["name"])] = 99
        for attempt in (1, 2):
            outcome = self.poll()
            self.assertEqual(outcome["retry_pending"], [spec["accession"]])
            self.assertEqual(self.cursor()["pending"][spec["accession"]]["attempts"], attempt)
        final = self.poll()
        self.assertEqual((final["dead_letter"], final["jobs"]), ([spec["accession"]], []))
        record = self.records()[0]
        self.assertEqual(record["quality"], "MISSING")
        self.assertEqual(self.poll()["new_records"], [])

    def test_exhibit_failure_records_an_incomplete_filing_after_retries(self):
        spec = self.add("EXSEMI_Q3_8K")
        self.source.failing_documents[(spec["accession"], spec["documents"][1]["name"])] = 99
        self.poll(), self.poll()
        final = self.poll()
        self.assertEqual(len(final["jobs"]), 1)
        record = self.records()[0]
        self.assertTrue(record["incomplete"])
        self.assertEqual([d["status"] for d in record["documents"]], ["OK", "FAILED"])

    def test_concurrent_pollers_conflict_instead_of_double_writing(self):
        self.add("EXSEMI_Q3_8K")
        store = self.store

        class StaleView:  # a second poller that read the cursor before the first one committed
            synthetic = True

            def read_cursor(self, source_id, issuer_id):
                return None

            def commit(self, batch):
                return store.commit(batch)

            def records(self, issuer_id):
                return store.records(issuer_id)

        self.poll()
        self.clock.advance(MIN)  # an identical replay would be IDEMPOTENT; this one differs
        outcome = self.make_ingestor(store=StaleView()).poll(EXSEMI).read()
        self.assertEqual((outcome["status"], outcome["receipt"]["status"], outcome["jobs"]), ("CONFLICT", "CONFLICT", []))
        self.assertEqual(len(self.records()), 1)


class SourceIdentityAndScopeTests(IngestHarness):
    def test_artifacts_hold_exact_bytes_behind_every_recorded_hash(self):
        self.add("EXMEM_Q3_6K", acceptance="2026-10-01T07:00:00+00:00")
        self.poll(EXMEM)
        record = self.records(EXMEM)[0]
        self.assertEqual(len(record["documents"]), 3)
        for item in record["documents"]:
            saved, raw = self.artifacts.get(item["text_sha256"]), self.artifacts.get(item["raw_sha256"])
            self.assertEqual(hashlib.sha256(saved).hexdigest(), item["text_sha256"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item["raw_sha256"])
            self.assertEqual(len(saved), item["text_bytes"])
            text_from_saved(saved)
        notice = next(d for d in record["documents"] if d["doc_type"] == "EX-99.2")
        self.assertEqual((notice["encoding"], notice["decode_lossy"]), ("cp1252", False))
        self.assertIn("“year-end dividend”", text_from_saved(self.artifacts.get(notice["text_sha256"])))

    def test_identity_mismatch_ingests_nothing(self):
        self.add("EXSEMI_Q3_8K")
        self.source.entities[9900001] = "Some Other Company"
        outcome = self.poll()
        self.assertEqual((outcome["status"], self.records()), ("INVALID_SOURCE", []))

    def test_foreign_issuer_forms_and_unexpected_forms(self):
        self.add("EXMEM_Q3_6K", acceptance="2026-10-01T07:00:00+00:00")
        self.source.add(9900002, accession="0009900002-26-000050", form="10-K", items=[],
                        acceptance="2026-10-01T10:00:00+00:00",
                        documents=[doc("x.htm", "10-K", cover("Example Memory Co., Ltd.", "10-K", [], ["x"]))])
        self.source.add(9900002, accession="0009900002-26-000051", form="4", items=[],
                        acceptance="2026-10-01T11:00:00+00:00",
                        documents=[doc("f4.xml", "4", b"<ownershipDocument/>")])
        outcome = self.poll(EXMEM)
        self.assertEqual(len(outcome["new_records"]), 1)
        self.assertEqual(outcome["unexpected_forms"], [["0009900002-26-000050", "10-K"]])
        self.assertEqual(outcome["ignored_forms"], 2)
        self.assertEqual(self.records(EXMEM)[0]["form_class"], "CURRENT")

    def test_backfill_ingests_an_old_window_without_moving_the_watermark(self):
        self.add("EXSEMI_Q3_8K")
        self.poll()
        watermark = self.cursor()["watermark_ms"]
        old = self.add("EXSEMI_Q2_8K", acceptance="2026-06-01T20:00:00+00:00")
        self.assertEqual(self.poll()["new_records"], [])  # older than the live floor
        window = (parse_acceptance_ms("2026-05-01T00:00:00+00:00"), parse_acceptance_ms("2026-07-01T00:00:00+00:00"))
        outcome = self.poll(mode="BACKFILL", window=window)
        self.assertEqual(len(outcome["new_records"]), 1)
        record = next(r for r in self.records() if r["accession"] == old["accession"])
        self.assertEqual((record["ingest_mode"], record["late_delivery"]), ("BACKFILL", False))
        self.assertEqual(record["available_ms"], self.clock())
        self.assertEqual(self.cursor()["watermark_ms"], watermark)
        job = self.store.jobs[outcome["jobs"][0]]
        self.assertGreater(Document(job).read()["priority"], 50)

    def test_backfill_reads_historical_submissions_files(self):
        accession, history = "0009900001-25-000050", "CIK0009900001-submissions-001.json"
        primary = FILINGS["EXSEMI_Q2_8K"]["documents"][0]
        base = f"https://www.sec.gov/Archives/edgar/data/9900001/{accession.replace('-', '')}/"
        columns = ("accessionNumber", "form", "items", "acceptanceDateTime", "filingDate", "reportDate", "primaryDocument")
        root = {"cik": "9900001", "name": "Example Semiconductor Corp",
                "filings": {"recent": {k: [] for k in columns},
                            "files": [{"name": history, "filingCount": 1, "filingFrom": "2025-06-01",
                                       "filingTo": "2025-06-30"}]}}
        older = {"accessionNumber": [accession], "form": ["8-K"], "items": ["2.02,9.01"],
                 "acceptanceDateTime": ["2025-06-02T20:20:00.000Z"], "filingDate": ["2025-06-02"],
                 "reportDate": [""], "primaryDocument": [primary["name"]]}
        index = (f'<table><tr><td>1</td><td>Current report</td><td><a href="/Archives/edgar/data/9900001/'
                 f'{accession.replace("-", "")}/{primary["name"]}">{primary["name"]}</a></td><td>8-K</td>'
                 f'<td>100</td></tr></table>').encode()
        routes = {"https://data.sec.gov/submissions/CIK0009900001.json": (200, "application/json", json.dumps(root).encode()),
                  f"https://data.sec.gov/submissions/{history}": (200, "application/json", json.dumps(older).encode()),
                  f"{base}{accession}-index.htm": (200, "text/html", index),
                  base + primary["name"]: (200, "text/html", primary["content"])}
        requested = []

        def http_get(url, headers, timeout):
            requested.append(url)
            return routes.get(url, (404, None, b""))

        source = EdgarHttpSource("LARP synthetic test contact@university.edu.sg", http_get=http_get,
                                 clock_ms=self.clock, sleep=lambda s: None)
        ingestor = Ingestor(registry=self.registry, source=source, store=self.store, artifacts=self.artifacts,
                            config=self.config, clock_ms=self.clock, run_id=RUN_ID, synthetic=True)
        live = ingestor.poll(EXSEMI).read()
        self.assertEqual((live["new_records"], live["history_status"]), ([], "NOT_REQUESTED"))
        self.assertNotIn(f"https://data.sec.gov/submissions/{history}", requested)
        window = (parse_acceptance_ms("2025-06-01T00:00:00+00:00"), parse_acceptance_ms("2025-06-30T00:00:00+00:00"))
        routes[f"https://data.sec.gov/submissions/{history}"] = (503, None, b"")
        partial = ingestor.poll(EXSEMI, mode="BACKFILL", window=window).read()
        self.assertEqual((partial["status"], partial["new_records"]), ("PARTIAL_HISTORY", []))
        self.assertEqual([(f["name"], f["status"], f["error"]) for f in partial["history_files"]],
                         [(history, "FAILED", "HTTP 503")])
        routes[f"https://data.sec.gov/submissions/{history}"] = (200, "application/json", json.dumps(older).encode())
        outcome = ingestor.poll(EXSEMI, mode="BACKFILL", window=window).read()
        self.assertEqual((outcome["status"], outcome["history_status"], len(outcome["new_records"])), ("OK", "OK", 1))
        self.assertEqual(outcome["history_files"][0]["response_sha256"], hashlib.sha256(json.dumps(older).encode()).hexdigest())
        record = next(r for r in self.records() if r["accession"] == accession)
        self.assertEqual((record["ingest_mode"], record["original_ms"]),
                         ("BACKFILL", parse_acceptance_ms("2025-06-02T20:20:00+00:00")))
        self.assertEqual(self.artifacts.get(record["documents"][0]["raw_sha256"]), primary["content"])

    def test_future_dated_rows_are_rejected(self):
        future = self.add("EXSEMI_Q3_8K", acceptance="2026-10-02T20:00:00+00:00")
        outcome = self.poll()
        self.assertEqual((outcome["rejected_future"], outcome["new_records"]), ([future["accession"]], []))

    def test_jobs_use_the_runtime_vocabulary_and_carry_no_trade_command(self):
        self.add("EXSEMI_402_8K", acceptance=AT_2030), self.add("EXSEMI_Q3_8K")
        self.poll()
        jobs = [Document(raw).read() for raw in self.store.jobs.values()]
        for job in jobs:
            self.assertEqual((job["lane"], job["missed"], job["payload"]["kind"]), ("evidence", "catch_up", "ASSESS_FILING"))
            self.assertGreater(job["valid_until_ms"], job["due_ms"])
            self.assertGreaterEqual(job["max_attempts"], 1)
            self.assertEqual(forbidden_key_paths(job), [])
        by_item = {Document(raw).read()["payload"]["accession"]: Document(raw).read()["priority"]
                   for raw in self.store.jobs.values()}
        self.assertLess(by_item[FILINGS["EXSEMI_402_8K"]["accession"]], by_item[FILINGS["EXSEMI_Q3_8K"]["accession"]])


if __name__ == "__main__":
    unittest.main()

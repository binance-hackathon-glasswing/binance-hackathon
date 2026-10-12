"""IDEA-041 AC-1.1..1.3: live preflight, terms captures, the live poll runner, its gap report and the durable EDGAR
store. Fake transports and clocks only; the 24-hour live run itself is NOT RUN here (it needs the host, the SEC
contact identity and the terms captures)."""

from dataclasses import replace
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError
from larp.intelligence.config import load_config
from larp.intelligence.fakes import FakeClock, FakeFilingSource
from larp.intelligence.ingest import Ingestor
from larp.intelligence.issuers import IssuerRegistry
from larp.intelligence.scenarios import ENTITIES, FIXTURE_REGISTRY, FILINGS
from larp.sources import live
from larp.sources.ingest import SourceIngestor
from larp.sources.register import CONFIG as REGISTER, live_preflight, load_register
from larp.sources.store import FileArtifacts, SQLiteEvidenceStore, SQLiteSourceStore
from larp.sources.transport import AllowlistedClient
from tests.sources.test_sources import FakeNet, doj

AGENT = "LARP test runner ops@larp-test.invalid"  # reserved .invalid domain: never a real contact
HOUR = 3_600_000
T0 = 1791590400000  # 2026-10-10T00:00:00Z


def with_terms(sources: dict) -> dict:
    return {k: replace(s, rights=dict(s.rights, terms_evidence_sha256="a" * 64)) for k, s in sources.items()}


class Preflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sources = load_register()[0]
        self.env = {"LARP_SEC_USER_AGENT": AGENT, "LARP_ARTIFACT_ROOT": self.tmp.name}

    def test_ready_register_and_environment_pass(self):
        self.assertEqual(live_preflight(with_terms(self.sources), self.env), [])

    def test_committed_register_is_refused_until_terms_are_captured(self):
        reasons = live_preflight(self.sources, self.env)
        enabled = sorted(s.source_id for s in self.sources.values() if s.enabled)
        self.assertEqual(reasons, [f"TERMS_EVIDENCE_MISSING:{s}" for s in enabled])
        self.assertNotIn("ftc-press", enabled)  # stays disabled until its connectivity is resolved

    def test_each_missing_piece_refuses(self):
        ready = with_terms(self.sources)
        repo = str(REGISTER.parents[2])
        cases = {
            "USER_AGENT_MISSING:sec-press:LARP_SEC_USER_AGENT": {"LARP_SEC_USER_AGENT": None},
            "SEC_USER_AGENT_INVALID:LARP_SEC_USER_AGENT": {"LARP_SEC_USER_AGENT": "LARP <contact email>"},
            "ARTIFACT_ROOT_MISSING:LARP_ARTIFACT_ROOT": {"LARP_ARTIFACT_ROOT": None},
            "ARTIFACT_ROOT_NOT_ABSOLUTE": {"LARP_ARTIFACT_ROOT": "relative/dir"},
            "ARTIFACT_ROOT_INSIDE_REPOSITORY": {"LARP_ARTIFACT_ROOT": os.path.join(repo, "data", "artifacts")},
        }
        for reason, change in cases.items():
            env = {k: v for k, v in dict(self.env, **change).items() if v is not None}
            with self.subTest(reason=reason):
                self.assertIn(reason, live_preflight(ready, env))
        one_missing = dict(ready, **{"doj-press": self.sources["doj-press"]})
        self.assertEqual(live_preflight(one_missing, self.env), ["TERMS_EVIDENCE_MISSING:doj-press"])

    def test_cli_preflight_refuses_and_reports_unset_live_parameters(self):
        self.assertEqual(live.main(["preflight"], env={}), 1)
        self.assertTrue(any(r.startswith("INTELLIGENCE_CONFIG_REFUSED:live")
                            for r in live.preflight({"LARP_SEC_USER_AGENT": AGENT})))

    def test_malformed_terms_hash_is_refused_by_the_loader(self):
        path = Path(self.tmp.name) / "sources.json"
        path.write_text(REGISTER.read_text("utf-8").replace('"terms_evidence_sha256": null', '"terms_evidence_sha256": "x"', 1))
        with self.assertRaises(IntelligenceError):
            load_register(path)

    def test_uncommitted_code_is_refused(self):
        with self.assertRaises(SystemExit):
            live.require_committed({"commit": "abc", "dirty": True}, allow_dirty=False)
        live.require_committed({"commit": "abc", "dirty": False}, allow_dirty=False)


class Terms(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sources = load_register()[0]
        self.artifacts = FileArtifacts(os.path.join(self.tmp.name, "artifacts"))

    def test_capture_stores_bytes_follows_same_host_redirects_and_refuses_others(self):
        def fetch(url, headers, timeout):
            if url == "https://www.sec.gov/privacy":
                return 301, {"Location": "/privacy-notice"}, b""
            if url == "https://www.sec.gov/privacy-notice":
                return 200, {"Content-Type": "text/html"}, b"<html>synthetic SEC terms page</html>"
            if url.startswith("https://www.justice.gov/"):
                return 302, {"Location": "https://elsewhere.test/terms"}, b""
            if url.startswith("https://www.archives.gov/"):
                return 500, {}, None
            return 200, {}, ("synthetic terms for " + url).encode()
        rows = {r["source_id"]: r for r in live.capture_terms(self.sources, fetch, self.artifacts, lambda: T0, sec_user_agent=AGENT)}
        self.assertEqual(rows["sec-press"]["status"], "CAPTURED")
        self.assertEqual(rows["sec-press"]["final_url"], "https://www.sec.gov/privacy-notice")
        self.assertEqual(self.artifacts.get(rows["sec-press"]["sha256"]), b"<html>synthetic SEC terms page</html>")
        self.assertEqual(rows["doj-press"]["status"], "REFUSED")
        self.assertEqual(rows["fr-bis"]["status"], "FAILED")
        self.assertEqual(rows["sec-press"]["captured_utc"], "2026-10-10T00:00:00Z")
        self.assertNotIn("ftc-press", rows)

    def test_register_update_touches_only_the_captured_values(self):
        copy = Path(self.tmp.name) / "sources.v1.json"
        shutil.copy(REGISTER, copy)
        rows = [{"source_id": "sec-press", "status": "CAPTURED", "sha256": "b" * 64, "captured_utc": "2026-10-12T08:00:00Z"},
                {"source_id": "doj-press", "status": "FAILED"}]
        self.assertEqual(live.write_register_terms(copy, rows), ["sec-press"])
        before, after = REGISTER.read_text("utf-8").splitlines(), copy.read_text("utf-8").splitlines()
        changed = [(a, b) for a, b in zip(before, after) if a != b]
        self.assertEqual(len(before), len(after))
        self.assertEqual(len(changed), 1)  # the sec-press rights line holds both values
        sources = load_register(copy)[0]
        self.assertEqual(sources["sec-press"].rights["terms_evidence_sha256"], "b" * 64)
        self.assertEqual(sources["sec-press"].rights["terms_checked"], "2026-10-12")
        self.assertIsNone(sources["doj-press"].rights["terms_evidence_sha256"])


class FakeIngestor:
    def __init__(self, fail=(), raise_on=()):
        self.calls, self.fail, self.raise_on = [], set(fail), set(raise_on)

    def poll(self, ident):
        self.calls.append(ident)
        if ident in self.raise_on:
            raise RuntimeError("boom")
        return {"status": "SOURCE_UNAVAILABLE" if ident in self.fail else "OK", "pages": 1, "new": [], "versions": [],
                "withdrawn": [], "rejected": [], "truncated": False}


class FakeEdgar(FakeIngestor):
    def poll(self, ident):
        out = super().poll(ident)
        return Document.from_dict({"status": out["status"], "new_records": [], "revisions": [], "late": [],
                                   "dead_letter": [], "jobs": []})


class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.register = load_register()[0]
        self.clock = FakeClock(T0)
        self.log = live.PollLog(Path(self.tmp.name) / "live" / live.LOG_NAME)

    def runner(self, sources=None, edgar=None):
        return live.LiveRunner(register=self.register, issuers=["ISS-A", "ISS-B"], source_ingestor=sources or FakeIngestor(),
                               edgar_ingestor=edgar or FakeEdgar(), log=self.log, clock_ms=self.clock,
                               sleep=lambda s: self.clock.advance(int(s * 1000)), edgar_interval_ms=300_000,
                               commit="test-commit")

    def cadences(self, runner):
        return {t.key: t.cadence_ms for t in runner.targets}

    def test_cadence_is_respected_and_a_day_passes_the_gap_report(self):
        runner = self.runner()
        runner.run(T0 + 24 * HOUR)
        lines = self.log.lines()
        for key, cadence in self.cadences(runner).items():
            starts = [l["started_ms"] for l in lines if l["target"] == key]
            with self.subTest(target=key):
                self.assertGreater(len(starts), 1)
                self.assertTrue(all(b - a >= cadence for a, b in zip(starts, starts[1:])))
        enabled = sorted(s.source_id for s in self.register.values() if s.enabled)
        self.assertEqual(sorted(k[7:] for k in self.cadences(runner) if k.startswith("source:")), enabled)
        report = live.gap_report(lines, cadences=self.cadences(runner), start_ms=T0, end_ms=T0 + 24 * HOUR)
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["commits"], ["test-commit"])

    def test_failures_and_exceptions_are_logged_and_do_not_stop_other_targets(self):
        runner = self.runner(sources=FakeIngestor(fail={"doj-press"}, raise_on={"ec-press"}))
        lines = runner.tick()
        by_target = {l["target"]: l for l in lines}
        self.assertEqual(by_target["source:doj-press"]["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual((by_target["source:ec-press"]["status"], by_target["source:ec-press"]["error"]),
                         ("EXCEPTION", "RuntimeError"))
        self.assertEqual(by_target["edgar:ISS-A"]["status"], "OK")
        self.assertEqual(len(lines), len(runner.targets))

    def test_restart_resumes_cadence_from_the_log(self):
        self.runner().tick()
        self.clock.advance(60_000)
        restarted = self.runner()
        self.assertEqual(restarted.tick(), [])  # nothing is due yet; no burst of requests after a restart

    def test_gap_report_failures_explanations_and_short_windows(self):
        runner = self.runner(sources=FakeIngestor(fail={"doj-press"}))
        runner.run(T0 + 24 * HOUR)
        lines, cadences = self.log.lines(), self.cadences(runner)
        report = live.gap_report(lines, cadences=cadences, start_ms=T0, end_ms=T0 + 24 * HOUR)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(report["targets"]["source:doj-press"]["successful_polls"], 0)
        incident = [{"target": "source:doj-press", "from_ms": T0, "to_ms": T0 + 24 * HOUR, "reason": "INC-1 DOJ outage"}]
        explained = live.gap_report(lines, cadences=cadences, start_ms=T0, end_ms=T0 + 24 * HOUR, incidents=incident)
        self.assertEqual(explained["verdict"], "PASS")
        short = live.gap_report(lines, cadences=cadences, start_ms=T0, end_ms=T0 + HOUR, incidents=incident)
        self.assertEqual(short["verdict"], "INCONCLUSIVE")
        with open(self.log.path, "a") as handle:
            handle.write('{"torn')
        self.assertEqual(live.gap_report(self.log.lines(), cadences=cadences, start_ms=T0, end_ms=T0 + 24 * HOUR,
                                         incidents=incident)["verdict"], "FAIL")


class RealIngestorsUnderTheRunner(unittest.TestCase):
    """The runner with the real source ingestor (fake network) and the real EDGAR ingestor on the durable store."""

    def test_one_tick_ingests_and_restart_keeps_records(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        clock = FakeClock(T0)
        register, aliases, sha = load_register()
        register = {"doj-press": register["doj-press"]}
        net = FakeNet({register["doj-press"].listing_url: [(200, {}, doj([("1", "Routine release", "<p>Routine.</p>",
                                                                             1791500000, 1791500000)]))]})
        artifacts = FileArtifacts(str(root / "artifacts"))
        sources = SourceIngestor(register=register, register_sha256=sha, aliases=aliases,
                                 client=AllowlistedClient(net, sleep=lambda s: None),
                                 store=SQLiteSourceStore(str(root / "sources.sqlite")), artifacts=artifacts,
                                 clock_ms=clock)
        registry = IssuerRegistry.from_dict(FIXTURE_REGISTRY)
        filing = FILINGS["EXSEMI_402_8K"]
        fake = FakeFilingSource(clock, ENTITIES)
        fake.add(filing["cik"], accession=filing["accession"], form=filing["form"], items=filing["items"],
                 acceptance="2026-10-09T21:00:00+00:00", documents=filing["documents"])
        store_path = str(root / "evidence.sqlite")
        edgar = Ingestor(registry=registry, source=fake, store=SQLiteEvidenceStore(store_path), artifacts=artifacts,
                         config=load_config(), clock_ms=clock, run_id="test")
        runner = live.LiveRunner(register=register, issuers=[e.issuer_id for e in registry.entries],
                                 source_ingestor=sources, edgar_ingestor=edgar,
                                 log=live.PollLog(root / "live" / live.LOG_NAME), clock_ms=clock)
        lines = {l["target"]: l for l in runner.tick()}
        self.assertEqual(lines["source:doj-press"]["new"], 1)
        self.assertEqual(lines["edgar:FIXTURE-CIK-9900001"]["new"], 1)
        reopened = SQLiteEvidenceStore(store_path)
        records = [d.read() for d in reopened.records("FIXTURE-CIK-9900001")]
        self.assertEqual([r["accession"] for r in records], [filing["accession"]])
        self.assertEqual(len(reopened.jobs()), 1)
        self.assertIsNotNone(reopened.read_cursor("sec-edgar", "FIXTURE-CIK-9900001"))


class EvidenceStore(unittest.TestCase):
    def test_compare_and_set_and_idempotent_batches(self):
        store = SQLiteEvidenceStore(":memory:")
        cursor = {"schema": "EvidenceCursor.v1", "issuer_id": "I", "version": 1}
        batch = {"schema": "IngestionBatch.v1", "batch_id": "b1", "source_id": "sec-edgar", "issuer_id": "I",
                 "expected_cursor_version": 0, "cursor": cursor, "jobs": [{"job_id": "j1", "x": 1}],
                 "records": [{"record_id": "r1", "accession": "A"}]}
        self.assertEqual(store.commit(Document.from_dict(batch)).read()["status"], "COMMITTED")
        self.assertEqual(store.commit(Document.from_dict(batch)).read()["status"], "IDEMPOTENT")
        stale = dict(batch, batch_id="b-stale", records=[])  # expects cursor version 0, store is at 1
        self.assertEqual(store.commit(Document.from_dict(stale)).read()["status"], "CONFLICT")
        reused = dict(batch, batch_id="b1", expected_cursor_version=1)
        self.assertEqual(store.commit(Document.from_dict(reused)).read()["status"], "INTEGRITY_ERROR")
        changed_job = dict(batch, batch_id="b2", expected_cursor_version=1, jobs=[{"job_id": "j1", "x": 2}])
        self.assertEqual(store.commit(Document.from_dict(changed_job)).read()["status"], "INTEGRITY_ERROR")
        self.assertEqual(len(store.records("I")), 1)
        state = {"schema": "EvidenceStateBatch.v1", "batch_id": "s1", "issuer_id": "I", "expected_state_version": 0,
                 "state": {"version": 1}}
        self.assertEqual(store.commit(Document.from_dict(state)).read()["status"], "COMMITTED")
        self.assertEqual(store.read_state("I").read(), {"version": 1})


if __name__ == "__main__":
    unittest.main()

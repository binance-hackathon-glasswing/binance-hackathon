"""IDEA-041 AC-1.1..1.3: live preflight, terms captures, the live poll runner, its gap report and the durable EDGAR
store. Fake transports and clocks only; the 24-hour live run itself is NOT RUN here (it needs the host, the SEC
contact identity and the terms captures)."""

from contextlib import contextmanager
from dataclasses import replace
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


@contextmanager
def unset_live_parameter(name="reassess_delay_ms"):
    """LV-01 committed the live values; a copy with one unset keeps the live refusal under test."""
    from larp.intelligence import config
    original = config.load_config
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "intelligence"
        shutil.copytree(config.CONFIG_DIR, base)
        raw = json.loads((base / "intelligence.v1.json").read_text("utf-8"))
        raw["parameters"][name]["live"] = None
        (base / "intelligence.v1.json").write_text(json.dumps(raw), "utf-8")
        with patch.object(config, "load_config", lambda mode="development", base_dir=base: original(mode, base_dir)):
            yield

AGENT = "LARP test runner ops@larp-test.invalid"  # reserved .invalid domain: never a real contact
HOUR = 3_600_000
T0 = 1791590400000  # 2026-10-10T00:00:00Z


def with_terms(sources: dict, artifacts=None) -> dict:
    return {k: replace(s, rights=dict(s.rights, terms_evidence_sha256=(
        artifacts.put(("Synthetic terms fixture for " + s.rights["terms_url"]).encode()) if artifacts else "a" * 64)))
        for k, s in sources.items()}


def edgar_ready(artifacts=None) -> dict:
    from larp.sources.register import load_edgar_terms
    return dict(load_edgar_terms(), terms_evidence_sha256=(
        artifacts.put(b"Synthetic EDGAR terms fixture") if artifacts else "e" * 64))


class Preflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sources = load_register()[0]
        self.env = {"LARP_SEC_USER_AGENT": AGENT, "LARP_ARTIFACT_ROOT": self.tmp.name}
        self.artifacts = FileArtifacts(os.path.join(self.tmp.name, "artifacts"))

    def test_ready_register_and_environment_pass(self):
        self.assertEqual(live_preflight(with_terms(self.sources, self.artifacts), self.env,
                                        edgar=edgar_ready(self.artifacts)), [])

    def test_committed_register_is_refused_until_terms_are_captured(self):
        from larp.sources.register import load_edgar_terms
        reasons = live_preflight(self.sources, self.env)
        enabled = sorted(s.source_id for s in self.sources.values() if s.enabled)
        # Either state of the committed register: a missing hash is refused, and a recorded hash still needs its
        # retained bytes (none exist in this empty artifact root).
        edgar = load_edgar_terms()
        hashes = {s: self.sources[s].rights.get("terms_evidence_sha256") for s in enabled}
        hashes["sec-edgar"] = edgar["terms_evidence_sha256"]
        missing = [f"TERMS_EVIDENCE_MISSING:{s}" for s in enabled if not hashes[s]]
        missing += [] if hashes["sec-edgar"] else ["TERMS_EVIDENCE_MISSING:sec-edgar"]
        unavailable = [f"TERMS_ARTIFACT_UNAVAILABLE:{s}" for s in sorted(hashes) if hashes[s]]
        self.assertEqual(reasons, missing + unavailable)
        absent = {k: replace(s, rights=dict(s.rights, terms_evidence_sha256=None)) for k, s in self.sources.items()}
        self.assertEqual(live_preflight(absent, self.env, edgar=dict(edgar, terms_evidence_sha256=None)),
                         [f"TERMS_EVIDENCE_MISSING:{s}" for s in enabled] + ["TERMS_EVIDENCE_MISSING:sec-edgar"])
        self.assertNotIn("ftc-press", enabled)  # stays disabled until its connectivity is resolved

    def test_each_missing_piece_refuses(self):
        ready = with_terms(self.sources, self.artifacts)
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
                self.assertIn(reason, live_preflight(ready, env, edgar=edgar_ready(self.artifacts)))
        source = ready["doj-press"]
        one_missing = dict(ready, **{"doj-press": replace(source, rights=dict(source.rights, terms_evidence_sha256=None))})
        self.assertEqual(live_preflight(one_missing, self.env, edgar=edgar_ready(self.artifacts)),
                         ["TERMS_EVIDENCE_MISSING:doj-press"])

    def test_cli_preflight_refuses_and_reports_unset_live_parameters(self):
        self.assertEqual(live.main(["preflight"], env={}), 1)
        self.assertFalse(any(r.startswith("INTELLIGENCE_CONFIG_REFUSED")
                             for r in live.preflight({"LARP_SEC_USER_AGENT": AGENT})))
        with unset_live_parameter():
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
        live.require_committed({"commit": "abc", "dirty": False, "pushed": True}, allow_dirty=False)


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
        rows = {r["source_id"]: r for r in live.capture_terms(self.sources, fetch, self.artifacts, lambda: T0,
                                                              user_agents={"LARP_SEC_USER_AGENT": AGENT})}
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
        self.assertEqual(sources["doj-press"].rights, load_register(REGISTER)[0]["doj-press"].rights)


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


class DurableStoreUnderTheAssessor(unittest.TestCase):
    """R01 (Keith P1): the assessor reads evidence on its own worker thread, so the durable store must serve it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_assessor_worker_thread_reads_the_sqlite_store(self):
        from larp.intelligence.models import RuleBaselineModel
        from larp.intelligence.scenarios import EXSEMI, build_world
        store = SQLiteEvidenceStore(os.path.join(self.tmp.name, "evidence.sqlite"))
        w = build_world(["EXSEMI_Q2_8K", "EXSEMI_Q3_8K"], store=store)
        result = w.assessor(RuleBaselineModel(w.clock)).assess(
            w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="sqlite")).read()
        self.assertEqual(result["status"], "ASSESSED", result["reasons"])

    def test_concurrent_reads_from_several_threads(self):
        import threading
        from larp.intelligence.scenarios import EXSEMI, build_world
        store = SQLiteEvidenceStore(os.path.join(self.tmp.name, "evidence.sqlite"))
        build_world(["EXSEMI_Q2_8K"], store=store)
        errors, counts = [], []

        def read():
            try:
                for _ in range(20):
                    counts.append(len(store.records(EXSEMI)))
                    store.read_cursor("sec-edgar", EXSEMI)
            except Exception as exc:  # noqa: BLE001 - the failure itself is the result
                errors.append(exc)
        threads = [threading.Thread(target=read) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(set(counts), {1})

    def test_bakeoff_wiring_runs_on_the_durable_store(self):
        """`run_bakeoff` itself, with the EDGAR source and the preflight faked (no network, no credentials)."""
        import argparse
        from unittest import mock
        from larp.intelligence import config as intel_config, edgar
        from larp.intelligence.fakes import FakeFilingSource
        from larp.intelligence.issuers import IssuerRegistry
        filing = FILINGS["EXSEMI_402_8K"]
        now = live.epoch_ms()
        fake = FakeFilingSource(live.epoch_ms, ENTITIES)
        fake.add(filing["cik"], accession=filing["accession"], form=filing["form"], items=filing["items"],
                 acceptance=live.iso(now - 2 * 86_400_000).replace("Z", "+00:00"), documents=filing["documents"])
        args = argparse.Namespace(config_mode="development", days=30, per_issuer=5, min_filings=1, max_filings=25,
                                  candidate=None, price=None)
        with mock.patch.object(live, "_env_root", lambda env, mode="live": Path(self.tmp.name)), \
                mock.patch.object(intel_config, "load_registry", lambda: IssuerRegistry.from_dict(FIXTURE_REGISTRY)), \
                mock.patch.object(edgar, "EdgarHttpSource", lambda agent, clock_ms: fake):
            report = live.run_bakeoff({"LARP_SEC_USER_AGENT": AGENT}, args, "test-commit")
        metrics = report["candidates"]["rule-baseline"]["metrics"]
        self.assertEqual(metrics["assessments"], 1)
        self.assertEqual(metrics["status_counts"], {"ASSESSED": 1})
        self.assertTrue(all(Path(p).exists() for p in report["written_to"]))


class TornTail(unittest.TestCase):
    """R04 (Keith P2): a torn last line stays visible and never swallows the next complete record."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "live" / live.LOG_NAME
        self.path.parent.mkdir(parents=True)
        self.torn = b'{"schema":"LivePoll.v1","target":"edgar:ISS-A"'
        self.path.write_bytes(self.torn)
        self.clock = FakeClock(T0)

    def runner(self):
        return live.LiveRunner(register={}, issuers=["ISS-A"], source_ingestor=FakeIngestor(), edgar_ingestor=FakeEdgar(),
                               log=live.PollLog(self.path), clock_ms=self.clock, edgar_interval_ms=300_000,
                               commit="test-commit")

    def test_append_after_a_torn_tail_keeps_both(self):
        log = live.PollLog(self.path)
        ok = {"schema": "LivePoll.v1", "target": "edgar:ISS-A", "cadence_ms": 300_000, "started_ms": T0,
              "finished_ms": T0 + 5, "commit": "c", "status": "OK"}
        log.append(ok)
        lines = log.lines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].get("corrupt"))
        self.assertEqual(lines[1], ok)
        self.assertTrue(self.path.read_bytes().startswith(self.torn))  # the damaged bytes are kept, not rewritten
        report = live.gap_report(lines, cadences={"edgar:ISS-A": 300_000}, start_ms=T0, end_ms=T0 + 300_000)
        self.assertEqual(report["corrupt_log_lines"], 1)

    def test_restart_after_a_torn_tail_resumes_cadence(self):
        self.assertEqual(len(self.runner().tick()), 1)
        self.clock.advance(60_000)
        self.assertEqual(self.runner().tick(), [])  # the poll written after the torn tail is read back
        self.clock.advance(60_000)
        self.assertEqual(self.runner().tick(), [])
        lines = live.PollLog(self.path).lines()
        self.assertEqual([bool(l.get("corrupt")) for l in lines], [True, False])


class TermsUserAgentAndEdgar(unittest.TestCase):
    """R08 (Keegan 5): terms pages are fetched with the declared agent; EDGAR's terms are part of preflight."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sources = load_register()[0]
        self.artifacts = FileArtifacts(os.path.join(self.tmp.name, "artifacts"))
        self.sent = []

    def fetch(self, url, headers, timeout):
        self.sent.append((url, headers))
        return 200, {"Content-Type": "text/html"}, ("synthetic terms for " + url).encode()

    def test_sec_hosts_get_the_declared_agent_and_edgar_is_captured(self):
        from larp.sources.register import load_edgar_terms
        rows = {r["source_id"]: r for r in live.capture_terms(
            self.sources, self.fetch, self.artifacts, lambda: T0, user_agents={"LARP_SEC_USER_AGENT": AGENT},
            edgar=load_edgar_terms())}
        self.assertEqual(rows["sec-edgar"]["status"], "CAPTURED")
        for url, headers in self.sent:
            with self.subTest(url=url):
                if "sec.gov" in url:
                    self.assertEqual(headers["User-Agent"], AGENT)
                else:
                    self.assertNotIn("@", headers["User-Agent"])  # no SEC contact sent to other publishers

    def test_missing_agent_fails_without_fetching(self):
        from larp.sources.register import load_edgar_terms
        rows = {r["source_id"]: r for r in live.capture_terms(
            self.sources, self.fetch, self.artifacts, lambda: T0, user_agents={}, edgar=load_edgar_terms())}
        for source_id in ("sec-press", "sec-edgar"):
            self.assertEqual((rows[source_id]["status"], rows[source_id]["error"]),
                             ("FAILED", "USER_AGENT_NOT_CONFIGURED"))
        self.assertFalse([u for u, _ in self.sent if "sec.gov" in u])

    def test_preflight_requires_edgar_terms(self):
        from larp.sources.register import load_edgar_terms
        env = {"LARP_SEC_USER_AGENT": AGENT, "LARP_ARTIFACT_ROOT": self.tmp.name}
        edgar = dict(load_edgar_terms(), terms_evidence_sha256=None)
        self.assertIn("TERMS_EVIDENCE_MISSING:sec-edgar",
                      live_preflight(with_terms(self.sources, self.artifacts), env, edgar=edgar))
        self.assertEqual(live_preflight(with_terms(self.sources, self.artifacts), env, edgar=edgar_ready(self.artifacts)), [])

    def test_register_update_covers_edgar(self):
        from larp.sources.register import load_edgar_terms
        copy = Path(self.tmp.name) / "sources.v1.json"
        shutil.copy(REGISTER, copy)
        rows = [{"source_id": "sec-edgar", "status": "CAPTURED", "sha256": "d" * 64, "captured_utc": "2026-10-13T08:00:00Z"}]
        self.assertEqual(live.write_register_terms(copy, rows), ["sec-edgar"])
        self.assertEqual(load_edgar_terms(copy)["terms_evidence_sha256"], "d" * 64)
        self.assertEqual(load_edgar_terms(copy)["terms_checked"], "2026-10-13")
        self.assertEqual(load_register(copy)[0]["sec-press"].rights, load_register()[0]["sec-press"].rights)


class GapReportUsesLoggedCadence(unittest.TestCase):
    """R13 (Keegan nit): each gap is judged against the cadence the runner logged, not the report's CLI value."""

    @staticmethod
    def line(ms, cadence=None):
        out = {"schema": "LivePoll.v1", "target": "edgar:ISS-A", "started_ms": ms, "finished_ms": ms + 5, "status": "OK"}
        if cadence is not None:
            out["cadence_ms"] = cadence
        return out

    def test_logged_cadence_decides(self):
        slow = [self.line(T0 + i * 600_000, 600_000) for i in range(145)]  # every 10 min for a day
        report = live.gap_report(slow, cadences={"edgar:ISS-A": 600_000}, start_ms=T0, end_ms=T0 + 24 * HOUR)
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertEqual(report["targets"]["edgar:ISS-A"]["logged_cadences_ms"], [600_000])
        # Review of R13: a run that logs a slower cadence than declared cannot pass by its own account.
        report = live.gap_report(slow, cadences={"edgar:ISS-A": 250_000}, start_ms=T0, end_ms=T0 + 24 * HOUR)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(report["targets"]["edgar:ISS-A"]["slower_than_declared"])
        twelve_hourly = [self.line(T0 + i * 12 * HOUR, 12 * HOUR) for i in range(3)]
        report = live.gap_report(twelve_hourly, cadences={"edgar:ISS-A": 300_000}, start_ms=T0, end_ms=T0 + 25 * HOUR)
        self.assertEqual(report["verdict"], "FAIL")
        gapped = [self.line(T0 + i * 300_000, 300_000) for i in range(289) if i not in (100, 101)]
        report = live.gap_report(gapped, cadences={"edgar:ISS-A": 900_000}, start_ms=T0, end_ms=T0 + 24 * HOUR)
        self.assertEqual(report["verdict"], "FAIL")  # a 15 min gap at a logged 5 min cadence
        legacy = [self.line(T0 + i * 600_000) for i in range(145)]  # lines without cadence_ms: declared cadence
        report = live.gap_report(legacy, cadences={"edgar:ISS-A": 200_000}, start_ms=T0, end_ms=T0 + 24 * HOUR)
        self.assertEqual(report["verdict"], "FAIL")


if __name__ == "__main__":
    unittest.main()

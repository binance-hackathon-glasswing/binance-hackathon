"""IDEA-033 R15–R24: regressions for the 2026-10-11 code review of PR #7 at `b26ca09`.

Each test asserts the correct behaviour, so on the unfixed code a failure is the defect reproduced. Controls
(valid paths that must keep working) are marked CONTROL. Real modules throughout; the model is the rule
baseline, and source, market and execution ports are fakes. The R15/R16 store cases need the disposable
PostgreSQL in LARP_TEST_DATABASE_URL and skip without it.
"""

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
import os
import unittest
import uuid

from larp.contracts import Document
from larp.integration.contract import accept_for_strategy
from larp.integration.runtime import (
    ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection,
)
from larp.intelligence.agent import _State
from larp.intelligence.facts import extract_document, numbers_in
from larp.intelligence.gate import accept, consume, initial_state, lifecycle_policy_from
from larp.intelligence.issuers import IssuerRegistry
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import EXMEM, EXSEMI, FIXTURE_REGISTRY, build_world, prior_thesis
from larp.intelligence.text import document_text
from larp.intelligence.tools import prior_context
from larp.research.evaluation import evaluate
from larp.research.fixtures import changed, synthetic_profile
from larp.strategy.schema import markets as strategy_markets
from tests.integration.test_evidence_pipeline import (
    EXTRA as PIPE_EXTRA, RUN, context_for, evidence_state, pipeline_ledger, profile_hash, request_for,
    strategy_snapshot,
)
from tests.redteam.test_integration_redteam import P, gate_result
import tests.research.test_research as research

HOUR = 3_600_000
HEALTHY = {"integrity_ok": True, "journal_ok": True, "ownership_ok": True, "clock_ok": True}


def ms_of(s):
    return int(s.observed_at.timestamp() * 1000)


def due_statement_state():
    """A real evidence state whose first-seen statements are pending review, and the world clock it was built on."""
    p = synthetic_profile()
    w, state, _ = evidence_state(["EXSEMI_STATEMENTS_8K"], p)
    pending = [s for s in state["statements"].values() if s["status"] == "PENDING_REVIEW"]
    assert pending, "fixture must leave statements pending review"
    return w, state


# ============================================================================ R15 job identity
class JobIdentity(unittest.TestCase):
    def test_r15_same_review_payload_in_two_rounds_has_identical_job_bytes(self):
        """P1. A statement review planned again at a later round, with the evidence state unchanged, must be
        byte-identical (the store refuses a reused job ID with a changed definition)."""
        w, state = due_statement_state()
        due = min(s["review"]["next_due_ms"] for s in state["statements"].values()
                  if s["status"] == "PENDING_REVIEW")
        planner = RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3)
        jobs = []
        for offset in (HOUR, 2 * HOUR):
            now = datetime.fromtimestamp((due + offset) / 1000, timezone.utc)
            s = strategy_snapshot(now=now)
            s = changed(s, assessments=[context_for(s, state)])
            jobs.append({j["job_id"]: Document.from_dict(j).payload for j in planner.plan(s, None).read()["jobs"]})
        self.assertTrue(jobs[0], "a due statement review must produce a job")
        self.assertEqual(jobs[0], jobs[1])

    def test_r15_policy_review_in_one_session_has_identical_job_bytes(self):
        """P1. Policy reviews are keyed by session; two rounds in the same session must plan the same bytes."""
        s = strategy_snapshot(held={"NVDAB": 300})
        p = s.context.read()["profile"]
        builder = ContextBuilder(profile=p, profile_hash=s.policy_profile_hash, run_id=s.run_id, issuers={},
                                 market=lambda now: s.context.read()["markets"], health=lambda current: HEALTHY,
                                 calendar=lambda now: {"index": 80, "remaining": 10})
        projection = initial_projection(s.context.read()["portfolio"])
        review = SimpleNamespace(next_policy_state=SimpleNamespace(data=Document.from_dict(
            {"reviews": [{"symbol": "NVDAB", "reason": "HORIZON_REASSESSMENT"}]})))
        planner = RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3)
        out = []
        for offset in (0, HOUR):
            context, updates = builder({"projection": projection, "reservations": []}, {}, None, ms_of(s) + offset)
            projection = dict(projection, **updates)
            snap = SimpleNamespace(context=Document.from_dict(context))
            out.append([Document.from_dict(j).payload for j in planner._jobs(snap, review, ms_of(s) + offset)])
        self.assertTrue(out[0])
        self.assertEqual(out[0], out[1])


# ============================================================================ store harness (R15/R16)
class StoreCase(unittest.TestCase):
    def setUp(self):
        dsn = os.environ.get("LARP_TEST_DATABASE_URL")
        if not dsn:
            self.skipTest("Disposable PostgreSQL not configured")
        import psycopg
        from psycopg.conninfo import make_conninfo
        from larp.storage.postgres import PostgresStore, doc as sdoc
        self.admin, self.schema = dsn, "larp_cr_" + uuid.uuid4().hex
        with psycopg.connect(dsn) as db:
            db.execute("CREATE SCHEMA " + self.schema)
        self.addCleanup(self._drop)
        self.store = PostgresStore(make_conninfo(dsn, options="-c search_path=" + self.schema))
        self.store.migrate()
        self.w = build_world(["EXSEMI_STATEMENTS_8K", "OCCURRED_8K"], extra_filings=PIPE_EXTRA)
        self.store.initialize(RUN, "fake-wallet", 56, sdoc(initial_projection(pipeline_ledger())))
        self.store.takeover(RUN, 1, offline=True)
        self.market_error = None

    def _drop(self):
        import psycopg
        with psycopg.connect(self.admin) as db:
            db.execute("DROP SCHEMA " + self.schema + " CASCADE")

    def market(self, now_ms):
        if self.market_error:
            raise self.market_error
        at = datetime.fromtimestamp(now_ms / 1000, timezone.utc).isoformat()
        return [{"schema": "MarketObservation.v1", "symbol": symbol,
                 "underlying_id": EXSEMI if symbol == "NVDAB" else "fixture-issuer-" + symbol,
                 "token_id": "fixture-token-" + symbol, "decimals": 4, "currency": "USDT", "money_scale": 1_000_000,
                 "price_units": 100_000_000, "source_id": "SCRIPTED_FAKE", "content_hash": "f" * 64,
                 "quality": "VALID", "observed_at": at, "available_at": at, "close_at": at, "token_open": True,
                 "underlying_open": True, "basis_verified": False, "quotes": []}
                for symbol in ("NVDAB", "GOOGLB", "TSLAB", "MSFTB")]

    def coordinator(self, profile):
        from larp.runtime.coordinator import Coordinator
        from larp.runtime.fixtures import FakeExecution
        self.h = profile_hash(profile)
        builder = ContextBuilder(profile=profile, profile_hash=self.h, run_id=RUN,
                                 issuers={EXSEMI: {"token": "NVDAB", "underlying_id": EXSEMI}}, market=self.market,
                                 health=lambda current: HEALTHY, calendar=lambda now: {"index": 80, "remaining": 10},
                                 lifecycle_policy=lifecycle_policy_from(self.w.config))
        return Coordinator(self.store, self.w.assessor(RuleBaselineModel(self.w.clock)), StrategyPolicy(),
                           RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3), execution=FakeExecution(),
                           run_id=RUN, version_id="code-review-fixture", profile_hash=self.h,
                           address="0x" + "3" * 40, context_builder=builder,
                           initial_policy_state=initial_policy_state(RUN, profile), clock_ms=self.w.clock)

    def evidence(self):
        return self.store.load(RUN).read()["projection"].get("evidence", {}).get(EXSEMI) or initial_state(
            EXSEMI, self.h, lifecycle_policy=lifecycle_policy_from(self.w.config))

    def planned(self, round_id):
        return [d.read()["event"]["record"] for d in self.store.journal(RUN)
                if d.read()["event"]["kind"] == "ROUND_PLANNED" and d.read()["event"]["record"]["round_id"] == round_id][0]

    def jobs(self):
        with self.store.transaction() as db:
            return sorted(r[0] for r in db.execute("SELECT job_id FROM jobs WHERE run_id=%s", (RUN,)))


class StoreRegressions(StoreCase):
    def test_r15_rounds_replanning_an_unchanged_review_commit(self):
        """P1. Rounds 2 and 3 run after the statement review is due, with no new accepted evidence (the assessor
        is unavailable). Both plan the same review; both rounds must commit, with one stored job."""
        c = self.coordinator(synthetic_profile())
        c.start("r1", request_for(self.w, ["EXSEMI_STATEMENTS_8K"], self.evidence(), self.h, RUN, "job:r1"),
                self.w.clock())
        self.assertTrue(self.evidence()["statements"])

        class Unavailable:
            def assess(self, request):
                raise RuntimeError("synthetic outage")
        c.assessor = Unavailable()
        self.w.clock.advance(7 * HOUR)
        c.start("r2", request_for(self.w, ["EXSEMI_STATEMENTS_8K"], self.evidence(), self.h, RUN, "job:r2"),
                self.w.clock())
        first = self.jobs()
        self.assertTrue(first, "the due review must be queued")
        self.w.clock.advance(HOUR)
        c.start("r3", request_for(self.w, ["EXSEMI_STATEMENTS_8K"], self.evidence(), self.h, RUN, "job:r3"),
                self.w.clock())
        self.assertEqual(self.jobs(), first)
        self.assertEqual(self.store.metrics(RUN).read()["open_rounds"], 0)

    def test_r16_context_failure_still_latches_the_adverse_finding(self):
        """P1. The market port fails in the round that carries an impairment. The evidence must still be
        accepted and committed (ADVERSE latch), and the round record keeps the assessment; no policy runs."""
        c = self.coordinator(synthetic_profile(falsifier_ids=["IMPAIRMENT"]))
        self.market_error = RuntimeError("synthetic market timeout")
        c.start("r1", request_for(self.w, ["OCCURRED_8K"], self.evidence(), self.h, RUN, "job:r1"), self.w.clock())
        record = self.planned("r1")
        self.assertTrue(any(e.startswith("CONTEXT_UNAVAILABLE") for e in record["errors"]), record["errors"])
        self.assertIsNone(record["proposal_id"])
        self.assertIsNotNone(record["assessment"])
        state = self.store.load(RUN).read()["projection"]["evidence"][EXSEMI]
        self.assertIn("IMPAIRMENT", [a["type"] for a in state["unresolved_adverse"]])
        self.assertEqual(self.store.load(RUN).read()["reservations"], [])


# ============================================================================ R17 reductions
class MandatoryReductions(unittest.TestCase):
    CHANGES = {"falsifier_ids": ["F-ITEM-4.02"], "falsifier_authority": "MANDATORY_REDUCTION"}

    def build(self, markets, policy_data=None):
        p = synthetic_profile(**self.CHANGES)
        _, state, _ = evidence_state(["EXSEMI_402_8K"], p)
        s = strategy_snapshot(self.CHANGES, held={"NVDAB": 300})
        markets = markets(s.context.read()["markets"])
        builder = ContextBuilder(profile=p, profile_hash=s.policy_profile_hash, run_id=s.run_id,
                                 issuers={EXSEMI: {"token": "NVDAB", "underlying_id": EXSEMI}},
                                 market=lambda now: markets, health=lambda current: HEALTHY,
                                 calendar=lambda now: {"index": 80, "remaining": 10})
        projection = dict(initial_projection(s.context.read()["portfolio"]), evidence={EXSEMI: state})
        current = {"projection": projection, "reservations": [],
                   "policy_state": None if policy_data is None else dict(initial_policy_state(s.run_id, p),
                                                                         data=policy_data)}
        context, _ = builder(current, {}, None, ms_of(s))
        return s, state, context

    def test_r17_control_valid_record_creates_the_reduction(self):
        """CONTROL. A valid record under MANDATORY_REDUCTION still produces exactly one constraint."""
        _, _, context = self.build(lambda ms: ms)
        self.assertEqual([r["symbol"] for r in context["reduction_constraints"]], ["NVDAB"])

    def test_r17_unusable_market_rejected_by_strategy_creates_no_reduction(self):
        """P1. The strategy reads a STALE quote as no market (UNKNOWN_TOKEN); the planner must not get a
        mandatory reduction from that same record."""
        s, _, context = self.build(lambda ms: [dict(m, quality="STALE") if m["symbol"] == "NVDAB" else m
                                               for m in ms])
        s2 = changed(s, markets=context["markets"], assessments=context["assessments"])
        profile = s2.context.read()["profile"]
        _, rejected = accept_for_strategy(context["assessments"], s2, strategy_markets(s2, profile), {}, profile)
        self.assertIn("UNKNOWN_TOKEN", [r["reason"] for r in rejected])
        self.assertEqual(context["reduction_constraints"], [])

    def test_r17_stale_evidence_version_creates_no_reduction(self):
        """P1. A record older than the version the policy already accepted is STALE_EVIDENCE_VERSION for the
        strategy, and so cannot become a mandatory reduction either."""
        _, state, context = self.build(lambda ms: ms, policy_data={"evidence_versions": {"NVDAB": 10 ** 6}})
        self.assertEqual(context["reduction_constraints"], [])


# ============================================================================ R18 bounded reviews
class BoundedReviews(unittest.TestCase):
    STATEMENT = {"statement_id": "stmt:x", "event": "IMPAIRMENT", "novelty": "FIRST_SEEN", "accession": "A",
                 "record_id": "r0", "content_hash": "h0", "statement": "We may record an impairment."}

    def pending(self):
        st = initial_state("ISS", P)
        used = [{"record_id": "r0", "accession": "A", "revision": 0, "content_hash": "h0", "quality": "OK"}]
        decision, st = accept(st, gate_result("R0", st, 1000, used=used, event_statements=[self.STATEMENT]),
                              profile_hash=P, now_ms=1000)
        self.assertEqual((decision, st["statements"]["stmt:x"]["status"]), ("ACCEPT", "PENDING_REVIEW"))
        return st

    def test_r18_abstaining_reassessments_exhaust_the_review(self):
        """P2. Reassessments at each due time that abstain must count as attempts: after max_review_attempts
        the statement is REVIEW_EXHAUSTED and no review is due any more."""
        st = self.pending()
        for i in range(st["lifecycle"]["max_review_attempts"]):
            due = st["statements"]["stmt:x"]["review"]["next_due_ms"]
            self.assertIsNotNone(due, f"attempt {i}")
            decision, st = accept(st, gate_result(f"A{i}", st, due, status="ABSTAIN"), profile_hash=P, now_ms=due)
            self.assertEqual(decision, "ACCEPT")
        self.assertEqual(st["statements"]["stmt:x"]["status"], "REVIEW_EXHAUSTED")
        self.assertEqual(consume(st, 10 ** 13)["due_reviews"], [])

    def test_r18_control_result_before_the_due_time_is_not_an_attempt(self):
        """CONTROL. A result accepted before the review is due does not consume an attempt."""
        st = self.pending()
        due = st["statements"]["stmt:x"]["review"]["next_due_ms"]
        _, st = accept(st, gate_result("early", st, due - 1, status="ABSTAIN"), profile_hash=P, now_ms=due - 1)
        self.assertEqual(st["statements"]["stmt:x"]["review"]["attempts"], 0)
        self.assertEqual(st["statements"]["stmt:x"]["status"], "PENDING_REVIEW")


# ============================================================================ R19 KRW ranges
class KrwRanges(unittest.TestCase):
    def facts(self, html):
        saved = document_text(html, "e.htm")
        source = {"record_id": "rec:x", "accession": "0000000001-26-000001", "doc_name": "e.htm",
                  "available_ms": 1, "original_ms": 0}
        entry = IssuerRegistry.from_dict(FIXTURE_REGISTRY).by_issuer(EXMEM)
        return [f for f in extract_document(saved.text, saved.text_sha256, entry, source) if f["kind"] != "EVENT"]

    def test_r19_hyphenated_range_upper_bound_is_not_negative(self):
        """P1. "1.2-1.5 trillion won" must never yield operating income of -1.5 trillion."""
        facts = self.facts(b"<p>Operating profit for the third quarter of 2026 was 1.2-1.5 trillion won.</p>")
        self.assertEqual([f["value"] for f in facts if f["value"] and f["value"][0] < 0], [])
        self.assertEqual(numbers_in("1.2-1.5"), numbers_in("1.2 1.5"))

    def test_r19_control_written_negative_amounts_keep_their_sign(self):
        """CONTROL. A genuinely signed KRW amount still reads negative; a plain one positive."""
        loss = self.facts(b"<p>Operating income (loss) for the third quarter of 2026 was -0.3 trillion won.</p>")
        self.assertEqual([f["value"] for f in loss], [[-3, 10]])
        plain = self.facts(b"<p>Operating profit for the third quarter of 2026 was 1.5 trillion won.</p>")
        self.assertEqual([f["value"] for f in plain], [[3, 2]])
        self.assertEqual(numbers_in("(1.2) and -3"), numbers_in("-1.2 and -3"))


# ============================================================================ R20 prior history
class PriorHistory(unittest.TestCase):
    def state(self, earlier):
        current = {"record_id": "cur", "accession": "C", "original_ms": 100, "quality": "VALID", "documents": []}
        by_accession = {"C": current, **{r["accession"]: r for r in earlier}}
        return SimpleNamespace(
            index=SimpleNamespace(all_by_id={"cur": current}, by_accession=by_accession),
            current_records=["cur"], current_accessions={"C"}, context_facts=[], facts={}, loaded=set(),
            queried_prior=set(), history_complete={}, prior_fact_ids=set(), missing=[],
            coverage={"prior_records_truncated": 0, "prior_records_scanned": 0},
            config=SimpleNamespace(limits={"max_prior_records": 10}))

    def test_r20_failed_earlier_document_leaves_history_incomplete(self):
        """P2. An earlier filing whose document failed to retrieve was not checked: not FIRST_SEEN territory."""
        st = self.state([{"record_id": "e1", "accession": "E1", "original_ms": 50, "quality": "VALID",
                          "documents": [{"name": "ex99.htm", "status": "FAILED"}]}])
        prior_context(st, {"metric": "STATEMENTS"})
        self.assertIs(st.history_complete["STATEMENTS"], False)

    def test_r20_missing_earlier_filing_leaves_history_incomplete(self):
        """P2. An earlier filing whose primary document never arrived (quality MISSING) was not checked either."""
        st = self.state([{"record_id": "e1", "accession": "E1", "original_ms": 50, "quality": "MISSING",
                          "documents": []}])
        prior_context(st, {"metric": "STATEMENTS"})
        self.assertIs(st.history_complete["STATEMENTS"], False)

    def test_r20_control_readable_history_is_complete(self):
        """CONTROL. Readable earlier filings (here without documents to load) give complete history."""
        st = self.state([{"record_id": "e1", "accession": "E1", "original_ms": 50, "quality": "VALID",
                          "documents": []}])
        prior_context(st, {"metric": "STATEMENTS"})
        self.assertIs(st.history_complete["STATEMENTS"], True)


# ============================================================================ R21 model input cap
class ModelInputCap(unittest.TestCase):
    def state(self, documents, cap):
        entry = SimpleNamespace(issuer_id="ISS", entity_name="Issuer", filer_class="DOMESTIC")
        config = SimpleNamespace(limits={"max_tool_result_chars": 20000, "max_model_input_chars": cap})
        st = _State(entry, SimpleNamespace(all_by_id={}, by_accession={}), config, 10, ("prior_context",),
                    {"known_facts": []})
        st.texts = {f"{i:064x}": "x" * 100 for i in range(documents)}
        return st

    def test_r21_model_never_receives_an_over_cap_input(self):
        """P2. Many documents exceed the cap even after one trimming pass: the view must fit or be refused."""
        st = self.state(3000, 20000)
        view = st.view([], 1)
        if view is not None:
            self.assertLessEqual(len(Document.from_dict(view).payload), 20000)
        self.assertTrue(st.coverage["model_input_truncated"])

    def test_r21_assessment_does_not_call_the_model_with_an_over_cap_input(self):
        """P2. End to end: with a tiny cap the model is never called; the result is incomplete, not a crash."""
        w = build_world(["EXSEMI_Q2_8K", "EXSEMI_Q3_8K"])
        w = replace(w, config=replace(w.config, limits=dict(w.config.limits, max_model_input_chars=200)))
        inner = RuleBaselineModel(w.clock)
        calls = []

        class Counting:
            identity = inner.identity

            def step(self, request, remaining_ms):
                calls.append(len(Document.from_dict(request.read()["input"]).payload))
                return inner.step(request, remaining_ms)
        request = w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="job:cap",
                            context=prior_thesis(w.config, EXSEMI))
        result = w.assessor(Counting()).assess(request).read()
        self.assertEqual([c for c in calls if c > 200], [])
        self.assertFalse(result["coverage"]["complete"])

    def test_r21_control_input_under_the_cap_is_unchanged(self):
        """CONTROL. A small input is passed whole and not marked truncated."""
        st = self.state(3, 400000)
        view = st.view([], 1)
        self.assertEqual(len(view["documents"]), 3)
        self.assertFalse(st.coverage["model_input_truncated"])


# ============================================================================ R22 comparison sources
class ComparisonSources(unittest.TestCase):
    def test_r22_comparison_findings_name_their_supporting_filing(self):
        """P1. GUIDANCE_LOWERED (a comparison) must carry the new fact's filing as its source, or its latch can
        never be resolved by SOURCE_CORRECTED_OR_WITHDRAWN."""
        w = build_world(["EXSEMI_Q2_8K", "EXSEMI_Q3_8K"])
        request = w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="job:src",
                            context=prior_thesis(w.config, EXSEMI))
        result = w.assessor(RuleBaselineModel(w.clock)).assess(request).read()
        lowered = [f for f in result["findings"] if f["type"] == "GUIDANCE_LOWERED"]
        self.assertTrue(lowered)
        accession = w.record("EXSEMI_Q3_8K")["accession"]
        for finding in lowered:
            self.assertEqual([s["accession"] for s in finding.get("sources") or []], [accession])
            self.assertTrue(all(s.get("record_id") for s in finding["sources"]))


# ============================================================================ R23 record cap
class RecordCap(unittest.TestCase):
    def test_r23_cap_keeps_the_most_recent_accession_not_the_largest_string(self):
        """P2. With 2000 older high-numbered accessions held, a newly assessed low-numbered accession must be
        kept as the correction baseline."""
        st = initial_state("ISS", P)
        old = {f"9999999999-26-{i:06d}": {"revision": 0, "record_id": f"o{i}", "content_hash": "h"}
               for i in range(2000)}
        st = dict(st, records_seen=dict(old), records_assessed=dict(old))
        used = [{"record_id": "new", "accession": "0000000001-26-000001", "revision": 0, "content_hash": "hn",
                 "quality": "OK"}]
        decision, st = accept(st, gate_result("R1", st, 5000, used=used), profile_hash=P, now_ms=5000)
        self.assertEqual(decision, "ACCEPT")
        self.assertIn("0000000001-26-000001", st["records_seen"])
        self.assertIn("0000000001-26-000001", st["records_assessed"])
        self.assertLessEqual(len(st["records_seen"]), 2000)

    def test_r23_cap_never_drops_a_latch_support(self):
        """P2. An accession supporting an unresolved latch is never evicted, however old."""
        st = initial_state("ISS", P)
        finding = {"finding_id": "f1", "type": "IMPAIRMENT", "impact": "ADVERSE",
                   "sources": [{"accession": "0000000000-26-000000", "record_id": "r0"}]}
        used = [{"record_id": "r0", "accession": "0000000000-26-000000", "revision": 0, "content_hash": "h0",
                 "quality": "OK"}]
        _, st = accept(st, gate_result("R0", st, 1000, findings=[finding], used=used), profile_hash=P, now_ms=1000)
        for batch in range(3):
            used = [{"record_id": f"n{batch}-{i}", "accession": f"9{batch}{i:08d}-26-000001", "revision": 0,
                     "content_hash": "h", "quality": "OK"} for i in range(1000)]
            t = 2000 + batch
            _, st = accept(st, gate_result(f"B{batch}", st, t, used=used), profile_hash=P, now_ms=t)
        self.assertIn("0000000000-26-000000", st["records_seen"])
        self.assertEqual([a["finding_id"] for a in st["unresolved_adverse"]], ["f1"])


# ============================================================================ R24 evaluation
class AbsoluteReturn(unittest.TestCase):
    def setUp(self):
        self.fixture = research.ResearchTests()

    def test_r24_losing_treatment_is_flagged_and_can_be_required_positive(self):
        """P1. Baseline loses 5%, treatment loses 2%: the paired rule passes, but the treatment lost money.
        IDEA-034 (user decision 2026-10-11) supersedes the R24 stopgap: a positive absolute return is mandatory
        under every support rule, and a treatment that confidently loses money is NOT_SUPPORTED. The R24 opt-in
        rule is redundant and no longer a registrable value."""
        losing = self.fixture.outcomes(baseline_net=-10_000_000, evidence_net=-4_000_000)
        plain = evaluate(Document.from_dict(self.fixture.registration()), losing).read()
        self.assertEqual((plain["status"], plain["reason"]), ("NOT_SUPPORTED", "TREATMENT_ABSOLUTE_NET_NOT_POSITIVE"))
        self.assertLess(plain["treatment_absolute_mean"][0], 0)
        self.assertIn("TREATMENT_ABSOLUTE_NET_NOT_POSITIVE", plain["warnings"])
        strict = self.fixture.registration(support_rule="LOWER_BOUND_ABOVE_MARGIN_AND_TREATMENT_NET_POSITIVE")
        self.assertEqual(evaluate(Document.from_dict(strict), losing).read()["status"], "NOT_RUN")

    def test_r24_profitable_treatment_supported_under_strict_rule(self):
        """The registered default rule (now always strict, IDEA-034) supports a profitable, better treatment,
        without a warning."""
        better = self.fixture.outcomes(baseline_net=50000, evidence_net=150000)
        report = evaluate(Document.from_dict(self.fixture.registration()), better).read()
        self.assertEqual(report["status"], "SUPPORTED")
        self.assertEqual(report.get("warnings", []), [])


if __name__ == "__main__":
    unittest.main()

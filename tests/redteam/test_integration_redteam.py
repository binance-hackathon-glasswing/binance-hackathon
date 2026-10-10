"""IDEA-031 S4: independent red-team probes of integration, free-source ingestion and evaluation.

Every test asserts the CORRECT behaviour under the IDEA-030 R02/R06/R07/R12 and IDEA-031 S2/S3 contracts
(AC-L*, AC-I*, AC-D*, AC-E*), so a failing test is a defect found, not a broken test. Controls (valid paths that
must keep working) are marked CONTROL. Severity tags in each docstring:
P1 = could create an unauthorized trading effect, lose/duplicate durable state, accept stale/wrong evidence or
bias an evaluation verdict; P2 = contract violation without direct trading/verdict effect; P3 = minor.

Real modules throughout; only external sources (fake transport), model (rule model), execution and market ports
are fakes. Some probes hand-write an AssessmentResult or EvidenceContext record because they target the
consumer's handling of that record. Synthetic probes show paths, not real-world rates.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import http.client
import itertools
import json
import os
import tempfile
import unittest
import uuid

from larp.contracts import ContractError, Document
from larp.integration.contract import (
    accept_for_strategy, authority, context_hash, mandatory_reductions,
)
from larp.integration.runtime import (
    ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection, ledger_from,
)
from larp.intelligence.agent import context_hash as state_context_hash
from larp.intelligence.evaluation import score as eval_score
from larp.intelligence.gate import accept, consume, initial_state, lifecycle_policy_from
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.realeval import admissible, run as realeval_run
from larp.intelligence.config import CONFIG_DIR
from larp.intelligence.scenarios import EXSEMI, PROFILE, build_world, prior_thesis
from larp.research import ablation
from larp.research.evaluation import evaluate as econ_evaluate
from larp.research.fixtures import changed, snapshot, synthetic_profile, with_quotes
from larp.risk.planner import plan
from larp.sources import cluster
from larp.sources.ingest import SourceIngestor
from larp.sources.register import load_register
from larp.sources.store import SQLiteSourceStore
from larp.sources.transport import AllowlistedClient, SourceError, allowed
from larp.strategy.policy import decide
from tests.integration.test_evidence_pipeline import (
    EXTRA as PIPE_EXTRA, RUN, evidence_state, pipeline_ledger, profile_hash, request_for,
    strategy_snapshot, context_for,
)
from tests.intelligence.test_lifecycle import EXTRA as LIFECYCLE_EXTRA
from tests.sources.test_sources import FakeNet, Harness as SourceHarness, doj, fr, rss

P = "p" * 64  # synthetic policy profile hash for hand-written gate inputs


# ============================================================================ helpers
def gate_result(rid, state, cutoff, *, findings=(), used=(), complete=True, missing=(), status="ASSESSED",
                issuer="ISS", **extra):
    """A hand-written AssessmentResult.v2 aimed at the gate (the consumer under test)."""
    r = {"schema": "AssessmentResult.v2", "result_id": rid, "issuer_id": issuer, "assessment_key": "k-" + rid,
         "policy_profile_hash": P, "context_hash": state["context_hash"], "expiry_ms": cutoff + 3_600_000,
         "cutoff_ms": cutoff, "started_ms": cutoff, "completed_ms": cutoff,
         "status": status, "reasons": [], "findings": list(findings), "event_findings": [],
         "falsifiers": [], "claims": [], "retained_facts": [], "event_statements": [], "evidence_used": list(used),
         "missingness": list(missing), "conflicts": [],
         "coverage": {"complete": complete, "prior_history": {"STATEMENTS": True}}, "novelty": {},
         "proposed_thesis": {"status": "INTACT"} if status == "ASSESSED" else None}
    r.update(extra)
    return Document.from_dict(r)


def adverse_state():
    """State with one IMPAIRMENT latch supported only by accession A revision 0."""
    st = initial_state("ISS", P)
    used = [{"record_id": "r0", "accession": "A", "revision": 0, "content_hash": "h0", "quality": "OK"}]
    finding = {"finding_id": "f1", "type": "IMPAIRMENT", "impact": "ADVERSE",
               "sources": [{"accession": "A", "record_id": "r0"}]}
    decision, st = accept(st, gate_result("R1", st, 1000, findings=[finding], used=used), profile_hash=P, now_ms=1000)
    assert decision == "ACCEPT" and st["evidence_gate"] == "ADVERSE"
    return st


def fixture_context(s, **changes):
    """A well-formed EvidenceContext.v1 for the fixture snapshot's first market (hash recomputed)."""
    m = s.context.read()["markets"][0]
    ms = int(s.observed_at.timestamp() * 1000)
    record = {"schema": "EvidenceContext.v1", "run_id": s.run_id, "issuer_id": m["underlying_id"],
              "underlying_id": m["underlying_id"], "token": m["symbol"], "policy_profile_hash": s.policy_profile_hash,
              "state_version": 3, "as_of_ms": ms, "latest_cutoff_ms": ms, "assessed_until_ms": ms + 600_000,
              "status": "CLEAR", "status_reasons": [], "availability": "AVAILABLE", "quality": "VERIFIED",
              "review_complete": True, "falsifier_findings": [], "statements_pending": [],
              "statements_exhausted": [], "due_reviews": [], "thesis_status": "INTACT", "last_rejection": None}
    record.update(changes)
    record["context_hash"] = context_hash(record)
    return record


def markets_of(s):
    return {m["symbol"]: m for m in s.context.read()["markets"]}


# ============================================================================ integration: contract and authority
class AuthorityProbes(unittest.TestCase):
    def test_c01_control_default_authority_is_shadow_and_only_mandatory_creates_constraints(self):
        """CONTROL. Default SHADOW; NONE/SHADOW/DISCRETIONARY_EXIT never create planner reduction constraints."""
        self.assertEqual(authority(synthetic_profile()), {"falsifier": "SHADOW", "statement": "SHADOW",
                                                          "max_context_age_ms": 3_600_000})
        p = synthetic_profile(falsifier_ids=["F-ITEM-4.02"])
        _, state, _ = evidence_state(["EXSEMI_402_8K"], p)
        for mode in ("NONE", "SHADOW", "DISCRETIONARY_EXIT"):
            s = strategy_snapshot({"falsifier_ids": ["F-ITEM-4.02"], "falsifier_authority": mode},
                                  held={"NVDAB": 300})
            ctx = context_for(s, state)
            self.assertEqual(mandatory_reductions([ctx], s.context.read()["profile"], {"NVDAB": 300}), [], mode)
        s = strategy_snapshot({"falsifier_ids": ["F-ITEM-4.02"], "falsifier_authority": "MANDATORY_REDUCTION"},
                              held={"NVDAB": 300})
        self.assertEqual(len(mandatory_reductions([context_for(s, state)], s.context.read()["profile"],
                                                  {"NVDAB": 300})), 1)

    def test_c02_mandatory_reduction_from_an_invalid_context_record(self):
        """P1. mandatory_reductions() turns ANY record into a forced sell: a hash-mismatched, wrong-run, expired
        record (which accept_for_strategy rejects) still yields max_units=0. Expected: only records that pass the
        same identity/hash/time validation as the strategy may create a reduction constraint."""
        p = synthetic_profile(falsifier_ids=["F-ITEM-4.02"], falsifier_authority="MANDATORY_REDUCTION")
        _, state, _ = evidence_state(["EXSEMI_402_8K"], p)
        s = strategy_snapshot({"falsifier_ids": ["F-ITEM-4.02"], "falsifier_authority": "MANDATORY_REDUCTION"},
                              held={"NVDAB": 300})
        forged = dict(context_for(s, state), run_id="some-other-run", as_of_ms=0, context_hash="0" * 64)
        accepted, rejections = accept_for_strategy([forged], s, markets_of(s), {}, s.context.read()["profile"])
        self.assertEqual(accepted, {})  # the strategy refuses it ...
        self.assertTrue(rejections)
        # ... so the planner must not receive a mandatory sell built from it.
        self.assertEqual(mandatory_reductions([forged], s.context.read()["profile"], {"NVDAB": 300}), [])

    def test_c03_context_builder_forces_a_sell_on_a_token_whose_issuer_does_not_match(self):
        """P1. ContextBuilder computes reduction_constraints from raw contexts, not from what the strategy
        accepts. If the market port says NVDAB's underlying is another issuer, the strategy rejects the context as
        WRONG_ISSUER, yet the planner still gets max_units=0 for NVDAB and requires a sale. Expected: no mandatory
        requirement from a context the strategy rejected for identity."""
        changes = {"falsifier_ids": ["F-ITEM-4.02"], "falsifier_authority": "MANDATORY_REDUCTION"}
        p = synthetic_profile(**changes)
        _, state, _ = evidence_state(["EXSEMI_402_8K"], p)
        s = snapshot(held={"NVDAB": 300}, profile_changes=changes)  # NVDAB underlying = fixture-issuer-NVDAB
        ledger = s.context.read()["portfolio"]
        projection = dict(initial_projection(ledger), evidence={EXSEMI: state})
        builder = ContextBuilder(profile=p, profile_hash=s.policy_profile_hash, run_id=s.run_id,
                                 issuers={EXSEMI: {"token": "NVDAB", "underlying_id": EXSEMI}},
                                 market=lambda now: s.context.read()["markets"],
                                 health=lambda current: s.context.read()["health"],
                                 calendar=lambda now: {"index": 80, "remaining": 10},
                                 series=lambda now: s.context.read()["series"])
        ms = int(s.observed_at.timestamp() * 1000)
        ctx, _ = builder({"projection": projection, "reservations": []}, {}, None, ms)
        s2 = changed(s, assessments=ctx["assessments"], reduction_constraints=ctx["reduction_constraints"])
        rejected = decide(s2, s2.policy_state).next_policy_state.data.read()["evidence_rejections"]
        self.assertIn("WRONG_ISSUER", [r["reason"] for r in rejected])
        forced = [r for r in plan(s2, None).read()["requirements"]
                  if any(str(x).startswith("EVIDENCE_FALSIFIER_MANDATORY") for x in r.get("reasons", []))]
        self.assertEqual(forced, [])

    def test_c04_mandatory_reduction_bypasses_cadence_minimum_but_not_journal_ownership_clock(self):
        """CONTROL. Mandatory sell ignores cadence and the minimum trade, but each of journal/ownership/clock
        gates and signing end still block it."""
        p = synthetic_profile(falsifier_ids=["F-ITEM-4.02"])
        _, state, _ = evidence_state(["EXSEMI_402_8K"], p)
        s = strategy_snapshot({"falsifier_ids": ["F-ITEM-4.02"], "falsifier_authority": "MANDATORY_REDUCTION"},
                              held={"NVDAB": 300})
        ctx = context_for(s, state)
        c = s.context.read()
        markets = [m if m["symbol"] == "NVDAB" else dict(m, basis_verified=False) for m in c["markets"]]
        s = changed(s, assessments=[ctx], markets=markets, last_discretionary_session=80,
                    reduction_constraints=mandatory_reductions([ctx], c["profile"], {"NVDAB": 300}))
        q = with_quotes(s)
        proposal = decide(q, q.policy_state)
        intents = plan(q, proposal).read()["intents"]
        self.assertEqual([(i["symbol"], i["side"], i["mandatory"]) for i in intents], [("NVDAB", "SELL", True)])
        for gate in ("journal_ok", "ownership_ok", "clock_ok"):
            broken = changed(q, health=dict(q.context.read()["health"], **{gate: False}))
            result = plan(broken, proposal).read()
            self.assertEqual(result["intents"], [], gate)
            self.assertIn(gate.upper(), result["rejections"][-1]["gates"])

    def test_c05_control_discretionary_exit_is_not_mandatory(self):
        """CONTROL. DISCRETIONARY_EXIT produces a policy EXIT that the planner treats as discretionary."""
        p = synthetic_profile(falsifier_ids=["F-ITEM-4.02"])
        _, state, _ = evidence_state(["EXSEMI_402_8K"], p)
        s = strategy_snapshot({"falsifier_ids": ["F-ITEM-4.02"], "falsifier_authority": "DISCRETIONARY_EXIT"},
                              held={"NVDAB": 3000})
        ctx = context_for(s, state)
        c = s.context.read()
        markets = [m if m["symbol"] == "NVDAB" else dict(m, basis_verified=False) for m in c["markets"]]
        s = changed(s, assessments=[ctx], markets=markets,
                    reduction_constraints=mandatory_reductions([ctx], c["profile"], {"NVDAB": 3000}))
        self.assertEqual(s.context.read()["reduction_constraints"], [])
        q = with_quotes(s)
        result = plan(q, decide(q, q.policy_state)).read()
        self.assertEqual(result["requirements"], [])
        self.assertTrue(all(i["mandatory"] is False for i in result["intents"]))


class ContextAcceptanceProbes(unittest.TestCase):
    def test_c06_non_integer_state_version_is_a_typed_rejection(self):
        """P2. A record with state_version "9" (string) and a valid hash crashes accept_for_strategy with
        TypeError (policy then fails for the whole round) instead of a typed MALFORMED rejection."""
        s = snapshot()
        record = fixture_context(s, state_version="9")
        try:
            accepted, rejections = accept_for_strategy([record], s, markets_of(s), {record["token"]: 3},
                                                       s.context.read()["profile"])
        except TypeError as exc:
            self.fail(f"untyped crash instead of a typed rejection: {exc!r}")
        self.assertEqual(accepted, {})
        self.assertIn("MALFORMED", [r["reason"] for r in rejections])

    def test_c07_unknown_status_or_missing_status_is_not_silently_used(self):
        """P2. A record with status "APPROVED" (not an evidence status) is accepted and passed to the strategy;
        one with no status field raises KeyError. Expected: typed MALFORMED rejection for both."""
        s = snapshot()
        for label, record in (("unknown", fixture_context(s, status="APPROVED")),
                              ("missing", {k: v for k, v in fixture_context(s).items() if k != "status"})):
            with self.subTest(label):
                record = dict(record)
                record["context_hash"] = context_hash(record)
                try:
                    accepted, rejections = accept_for_strategy([record], s, markets_of(s), {},
                                                               s.context.read()["profile"])
                except KeyError as exc:
                    self.fail(f"untyped crash: {exc!r}")
                self.assertEqual(accepted, {})
                self.assertIn("MALFORMED", [r["reason"] for r in rejections])

    def test_c08_control_clear_past_validity_reads_stale_and_older_version_is_rejected(self):
        """CONTROL. A CLEAR whose validity ended is read as STALE (not a fresh review); a lower state_version than
        the one already accepted is STALE_EVIDENCE_VERSION; a duplicate for the same token is DUPLICATE_CONTEXT."""
        s = snapshot()
        ms = int(s.observed_at.timestamp() * 1000)
        p = s.context.read()["profile"]
        stale = fixture_context(s, assessed_until_ms=ms)
        accepted, _ = accept_for_strategy([stale], s, markets_of(s), {}, p)
        self.assertEqual((accepted["NVDAB"]["status"], accepted["NVDAB"]["review_complete"]), ("STALE", False))
        old = fixture_context(s, state_version=2)
        accepted, rejections = accept_for_strategy([old], s, markets_of(s), {"NVDAB": 3}, p)
        self.assertEqual((accepted, [r["reason"] for r in rejections]), ({}, ["STALE_EVIDENCE_VERSION"]))
        good = fixture_context(s)
        _, rejections = accept_for_strategy([good, good], s, markets_of(s), {}, p)
        self.assertEqual([r["reason"] for r in rejections], ["DUPLICATE_CONTEXT"])
        # Policy chaining: once version 3 is accepted, a replayed version-2 context is refused in the next round.
        first = decide(changed(s, assessments=[good]), s.policy_state)
        nxt = first.next_policy_state
        s2 = replace(changed(s, assessments=[old]), policy_state=nxt)
        rej = decide(s2, nxt).next_policy_state.data.read()["evidence_rejections"]
        self.assertIn("STALE_EVIDENCE_VERSION", [r["reason"] for r in rej])


# ============================================================================ evidence gate (IssuerEvidenceState.v2)
class GateProbes(unittest.TestCase):
    def test_g01_latch_resolved_by_an_incomplete_assessment_of_the_revision(self):
        """P1. An ADVERSE latch (IMPAIRMENT from accession A rev 0) is resolved as CORRECTED by an ASSESSED result
        of A rev 1 whose coverage is incomplete (COVERAGE_TRUNCATED): the finding may simply not have been read.
        Expected: SOURCE_CORRECTED_OR_WITHDRAWN is satisfied only by a complete reading of the revision; the
        latch persists and the gate stays ADVERSE."""
        st = adverse_state()
        used = [{"record_id": "r1", "accession": "A", "revision": 1, "content_hash": "h1", "quality": "OK"}]
        decision, after = accept(st, gate_result("R2", st, 2000, used=used, complete=False,
                                                 missing=["COVERAGE_TRUNCATED"]), profile_hash=P, now_ms=2000)
        self.assertEqual(decision, "ACCEPT")
        self.assertEqual([a["type"] for a in after["unresolved_adverse"]], ["IMPAIRMENT"])
        self.assertEqual(consume(after, 2001)["evidence_gate"], "ADVERSE")

    def test_g02_control_latch_survives_unrelated_clean_abstain_and_expiry(self):
        """CONTROL. Unrelated clean result, an ABSTAIN with retained facts and the passage of time never clear
        the latch; ABSTAIN retained facts never change the thesis context nor make the gate CLEAR."""
        st = adverse_state()
        clean_used = [{"record_id": "rb", "accession": "B", "revision": 0, "content_hash": "hb", "quality": "OK"}]
        _, st = accept(st, gate_result("R2", st, 2000, used=clean_used), profile_hash=P, now_ms=2000)
        retained = [{"fact_id": "x", "kind": "REPORTED", "metric": "revenue", "source": {"available_ms": 1}}]
        decision, st2 = accept(st, gate_result("R3", st, 3000, status="ABSTAIN", retained_facts=retained),
                               profile_hash=P, now_ms=3000)
        self.assertEqual(decision, "ACCEPT")
        self.assertEqual(st2["context"], st["context"])
        view = consume(st2, 10 ** 13)
        self.assertEqual((view["evidence_gate"], [a["type"] for a in view["adverse"]]), ("ADVERSE", ["IMPAIRMENT"]))

    def test_g04_old_state_cannot_be_refreshed_by_an_out_of_order_or_expired_result(self):
        """CONTROL. An older cutoff is REJECT_OUT_OF_ORDER and an expired result REJECT_EXPIRED; neither changes
        evidence (version/latches), and both are visible as last_rejection."""
        st = adverse_state()
        decision, after = accept(st, gate_result("R0", st, 500), profile_hash=P, now_ms=1500)
        self.assertEqual(decision, "REJECT_OUT_OF_ORDER")
        self.assertEqual((after["version"], after["unresolved_adverse"]), (st["version"], st["unresolved_adverse"]))
        expired = gate_result("R9", st, 2000, expiry_ms=1999)
        decision, after = accept(st, expired, profile_hash=P, now_ms=2000)
        self.assertEqual((decision, after["last_rejection"]["decision"]), ("REJECT_EXPIRED", "REJECT_EXPIRED"))

    def test_g05_pending_statement_acknowledged_without_any_history_check(self):
        """P2. A statement PENDING_REVIEW is re-seen by a zero-tool-call assessment that performed no prior-history
        lookup (coverage.prior_history == {}). gate.accept computes history_checked = all({}.values()) == True and
        moves it to ACKNOWLEDGED. Expected (lifecycle contract): ACKNOWLEDGED only after a complete assessment
        WITH prior history checked; otherwise it stays PENDING_REVIEW (attempts + 1)."""
        w = build_world(["RISKS", "CLEAN", "OCCURRED"], extra_filings=LIFECYCLE_EXTRA)
        ctx = prior_thesis(w.config, EXSEMI)
        st = dict(initial_state(EXSEMI, PROFILE, lifecycle_policy=lifecycle_policy_from(w.config)), context=ctx,
                  context_hash=state_context_hash(ctx))

        def run(state, job, tools):
            req = w.request(["RISKS"], issuer_id=EXSEMI, job_id=job, context=state["context"], tool_calls=tools)
            res = w.assessor(RuleBaselineModel(w.clock)).assess(req)
            decision, after = accept(state, res, profile_hash=PROFILE, now_ms=w.clock())
            self.assertEqual(decision, "ACCEPT")
            return res.read(), after

        _, st = run(st, "j1", 6)
        self.assertEqual({s["status"] for s in st["statements"].values()}, {"PENDING_REVIEW"})
        w.clock.advance(6 * 3_600_000)
        second, st = run(st, "j2", 0)
        self.assertEqual(second["coverage"]["prior_history"], {})  # no history lookup happened
        self.assertEqual({s["status"] for s in st["statements"].values()}, {"PENDING_REVIEW"})

    def test_g06_malformed_result_is_a_typed_rejection(self):
        """P3. A v2 result lacking `findings`/`claims` (shape passes the runtime's assessment_result check) raises
        KeyError in gate.accept, so ContextBuilder fails and the whole round loses its context. Expected:
        REJECT_MALFORMED with state unchanged."""
        st = initial_state("ISS", P)
        r = gate_result("R1", st, 1000).read()
        for k in ("findings", "claims", "falsifiers"):
            r.pop(k)
        try:
            decision, after = accept(st, Document.from_dict(r), profile_hash=P, now_ms=1000)
        except KeyError as exc:
            self.fail(f"untyped crash: {exc!r}")
        self.assertEqual(decision, "REJECT_MALFORMED")
        self.assertEqual(after["version"], 0)


# ============================================================================ runtime adapter
class RuntimeAdapterProbes(unittest.TestCase):
    def test_r01_pending_buy_reservation_crashes_the_next_plan(self):
        """P1. The store keeps a BUY as asset/units rows (USDT + BNB). ledger_from() cannot recover the symbol
        (projection 'intent_symbols' is never written anywhere) nor the token units, so the reservation reaches
        the planner as {symbol: None, token_units: 0}; plan() then raises KeyError(None). Under the coordinator
        that is PLANNER_UNAVAILABLE for every round while a BUY is pending: mandatory requirements (terminal
        flatten, evidence reductions) and risk-state persistence are lost, and pending exposure is not counted.
        Expected: the plan completes, counts the pending buy in worst-case gross and blocks on WALLET_PENDING."""
        s = with_quotes(snapshot())
        proposal = decide(s, s.policy_state)
        planned = RuntimePlanner(job_validity_ms=60_000, job_max_attempts=3).plan(s, proposal).read()
        buy = planned["intents"][0]
        self.assertEqual(buy["side"], "BUY")
        rows = [dict(d) for d in planned["reservation_deltas"]]  # what the store returns as reservations
        ledger = ledger_from(initial_projection(s.context.read()["portfolio"]), rows)
        nxt = changed(s, portfolio=ledger)
        try:
            result = plan(nxt, None).read()
        except KeyError as exc:
            self.fail(f"planner crashed on a store BUY reservation: KeyError({exc})")
        self.assertIn("WALLET_PENDING", result["rejections"][-1]["gates"])
        m = markets_of(s)[buy["symbol"]]
        self.assertGreaterEqual(result["worst_case_gross_units"], buy["token_units"] * m["price_units"] // 10 ** 4)

    def test_r02_projection_with_an_unledgered_balance_is_refused(self):
        """P3. ledger_from() compares only assets the ledger lists. A settled balance for a token absent from the
        ledger's positions (e.g. SKHYB) passes silently. Expected: any balance/ledger disagreement is refused."""
        ledger = snapshot().context.read()["portfolio"]
        projection = initial_projection(ledger)
        projection["balances"]["SKHYB"] = 5000
        with self.assertRaises(ValueError):
            ledger_from(projection, [])

    def test_r03_control_runtime_vocabulary_is_consistent(self):
        """CONTROL. decision_id/amount/expires_ms/reservation deltas agree with the planner intent; a
        discretionary intent never outlives its proposal; replanning the same snapshot is byte-identical."""
        s = with_quotes(snapshot())
        proposal = decide(s, s.policy_state)
        rp = RuntimePlanner(job_validity_ms=60_000, job_max_attempts=3)
        a, b = rp.plan(s, proposal), rp.plan(s, proposal)
        self.assertEqual(a.payload, b.payload)
        out = a.read()
        intent = out["intents"][0]
        self.assertFalse(intent["mandatory"])
        self.assertLessEqual(intent["expires_ms"], int(proposal.valid_until.timestamp() * 1000))
        self.assertEqual(intent["amount"], str(intent["pay_units"] // 10 ** 6) + (
            "." + str(intent["pay_units"] % 10 ** 6).rjust(6, "0").rstrip("0") if intent["pay_units"] % 10 ** 6
            else ""))
        deltas = sorted((d["asset"], d["units"]) for d in out["reservation_deltas"])
        # IDEA-031 S4-B r01 fix: a BUY also records its incoming tokens as an INCOMING:<symbol> claim row.
        self.assertEqual(deltas, sorted([("USDT", intent["cash_units"] + intent["fee_units"]),
                                         ("BNB", intent["gas_bnb_units"]),
                                         ("INCOMING:" + intent["symbol"], intent["token_units"])]))

# ---------------------------------------------------------------------------- real PostgreSQL store
class StoreProbes(unittest.TestCase):
    def setUp(self):
        dsn = os.environ.get("LARP_TEST_DATABASE_URL")
        if not dsn:
            self.skipTest("Disposable PostgreSQL not configured")
        import psycopg
        from psycopg.conninfo import make_conninfo
        from larp.storage.postgres import PostgresStore
        self.admin, self.schema = dsn, "larp_rt_" + uuid.uuid4().hex
        with psycopg.connect(dsn) as db:
            db.execute("CREATE SCHEMA " + self.schema)
        self.addCleanup(self._drop)
        self.store = PostgresStore(make_conninfo(dsn, options="-c search_path=" + self.schema))
        self.store.migrate()
        self.w = build_world(["EXSEMI_Q2_8K", "EXSEMI_402_8K", "OCCURRED_8K"], extra_filings=PIPE_EXTRA)

    def _drop(self):
        import psycopg
        with psycopg.connect(self.admin) as db:
            db.execute("DROP SCHEMA " + self.schema + " CASCADE")

    def init(self, projection):
        from larp.storage.postgres import doc as sdoc
        self.store.initialize(RUN, "fake-wallet", 56, sdoc(projection))
        self.store.takeover(RUN, 1, offline=True)

    def market(self, now_ms):
        at = datetime.fromtimestamp(now_ms / 1000, timezone.utc)
        out = []
        for symbol in ("NVDAB", "GOOGLB", "TSLAB", "MSFTB"):
            quotes = []
            if symbol == "NVDAB":
                quotes.append({"quote_id": "fake-nvdab-sell", "side": "SELL", "token_units": 2000,
                               "cash_units": 19_980_000, "fee_units": 0, "gas_bnb_units": 10000, "route_valid": True,
                               "slippage_bps": 20, "impact_bps": 10, "available_at": at.isoformat(),
                               "observed_at": at.isoformat(), "expires_at": (at + timedelta(seconds=30)).isoformat()})
            out.append({"schema": "MarketObservation.v1", "symbol": symbol,
                        "underlying_id": EXSEMI if symbol == "NVDAB" else "fixture-issuer-" + symbol,
                        "token_id": "fixture-token-" + symbol, "decimals": 4, "currency": "USDT",
                        "money_scale": 1_000_000, "price_units": 100_000_000, "source_id": "SCRIPTED_FAKE",
                        "content_hash": "f" * 64, "quality": "VALID", "observed_at": at.isoformat(),
                        "available_at": at.isoformat(), "close_at": at.isoformat(), "token_open": True,
                        "underlying_open": True, "basis_verified": False, "quotes": quotes})
        return out

    def coordinator(self):
        from larp.runtime.coordinator import Coordinator
        from larp.runtime.fixtures import FakeExecution
        self.profile = synthetic_profile(falsifier_ids=["IMPAIRMENT"], falsifier_authority="MANDATORY_REDUCTION")
        self.h = profile_hash(self.profile)
        builder = ContextBuilder(profile=self.profile, profile_hash=self.h, run_id=RUN,
                                 issuers={EXSEMI: {"token": "NVDAB", "underlying_id": EXSEMI}}, market=self.market,
                                 health=lambda current: {"integrity_ok": True, "journal_ok": True,
                                                         "ownership_ok": True, "clock_ok": True},
                                 calendar=lambda now: {"index": 80, "remaining": 10},
                                 lifecycle_policy=lifecycle_policy_from(self.w.config))
        return Coordinator(self.store, self.w.assessor(RuleBaselineModel(self.w.clock)), StrategyPolicy(),
                           RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3), execution=FakeExecution(),
                           run_id=RUN, version_id="redteam-fixture", profile_hash=self.h,
                           address="0x" + "2" * 40, context_builder=builder,
                           initial_policy_state=initial_policy_state(RUN, self.profile))

    def evidence(self):
        return self.store.load(RUN).read()["projection"].get("evidence", {}).get(EXSEMI) or initial_state(
            EXSEMI, self.h, lifecycle_policy=lifecycle_policy_from(self.w.config))

    def commands(self):
        with self.store.transaction() as db:
            return db.execute("SELECT command_id FROM commands WHERE run_id=%s", (RUN,)).fetchall()

    def planned(self, round_id):
        return [d.read()["event"]["record"] for d in self.store.journal(RUN)
                if d.read()["event"]["kind"] == "ROUND_PLANNED" and d.read()["event"]["record"]["round_id"] == round_id][0]

    def test_s01_control_second_round_while_sell_pending_adds_nothing(self):
        """CONTROL (AC-I05). A new round with fresh evidence while the mandatory sell is pending adds no command
        or reservation (WALLET_PENDING) and persists the evidence state and risk state."""
        self.init(initial_projection(pipeline_ledger()))
        c = self.coordinator()
        c.start("r1", request_for(self.w, ["OCCURRED_8K"], self.evidence(), self.h, RUN, "job:r1"), self.w.clock())
        self.assertEqual(len(self.commands()), 1)
        before = sorted((r["intent_id"], r["asset"], r["units"]) for r in self.store.load(RUN).read()["reservations"])
        self.w.clock.advance(60_000)
        c.start("r2", request_for(self.w, ["OCCURRED_8K"], self.evidence(), self.h, RUN, "job:r2"), self.w.clock())
        self.assertEqual(len(self.commands()), 1)
        after = sorted((r["intent_id"], r["asset"], r["units"]) for r in self.store.load(RUN).read()["reservations"])
        self.assertEqual(after, before)
        record = self.planned("r2")
        self.assertIn("WALLET_PENDING", [g for r in record["plan"]["rejections"] for g in r.get("gates", [])])
        value = self.store.load(RUN).read()
        self.assertGreaterEqual(value["projection"]["evidence"][EXSEMI]["version"], 1)
        self.assertIsNotNone(value["projection"]["risk_state"])

    def test_s02_control_balance_mismatch_is_refused(self):
        """CONTROL. Projection balances that disagree with the ledger refuse the context: no command, no
        reservation, and the round records CONTEXT_UNAVAILABLE."""
        projection = initial_projection(pipeline_ledger())
        projection["balances"]["USDT"] += 1
        self.init(projection)
        c = self.coordinator()
        c.start("r1", request_for(self.w, ["OCCURRED_8K"], self.evidence(), self.h, RUN, "job:r1"), self.w.clock())
        self.assertEqual(self.commands(), [])
        self.assertEqual(self.store.load(RUN).read()["reservations"], [])
        self.assertTrue(any(e.startswith("CONTEXT_UNAVAILABLE") for e in self.planned("r1")["errors"]))


# ============================================================================ free sources
class SourceProbes(SourceHarness):
    def test_d01_allowlist_path_traversal(self):
        """P2. allowed() checks path.startswith(prefix) on the raw path, so 'https://www.sec.gov/news/../cgi-bin/x'
        and '/api/v1/documents-other' pass the SEC/FR allowlists although they address paths outside the prefix.
        Expected: dot segments (and prefix-without-boundary matches) are refused."""
        self.assertFalse(allowed(self.register["sec-press"], "https://www.sec.gov/news/../cgi-bin/browse-edgar"))
        self.assertFalse(allowed(self.register["sec-press"], "https://www.sec.gov/news/%2e%2e/cgi-bin/x"))

    def test_d03_non_oserror_network_failure_is_recorded_as_source_health(self):
        """P2. http.client.IncompleteRead (an HTTPException, not OSError) escapes AllowlistedClient and poll():
        no SOURCE_UNAVAILABLE outcome, no health update, no retry. Expected: any transport failure is a bounded,
        recorded source failure."""
        url = self.register["doj-press"].listing_url
        net = FakeNet({url: [http.client.IncompleteRead(b"partial")]})
        try:
            out = self.ingestor(net).poll("doj-press")
        except http.client.HTTPException as exc:
            self.fail(f"transport exception escaped poll(): {exc!r}")
        self.assertEqual(out["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(self.store.cursor("doj-press")["health"]["status"], "UNAVAILABLE")

    def test_d04_one_bad_timestamp_blocks_every_item_of_the_source(self):
        """P2. One listing item with an unparseable date makes parse() raise for the whole page, so the source is
        UNAVAILABLE on every poll and its valid items are never ingested. Expected: the bad item is rejected with
        a recorded reason and the others are ingested."""
        url = self.register["fr-bis"].listing_url
        good = {"document_number": "2026-50001", "title": "Export rule", "type": "Rule", "action": "Final rule.",
                "publication_date": "2026-10-09"}
        bad = dict(good, document_number="2026-50002", publication_date="09/10/2026")
        out = self.ingestor(FakeNet({url: [(200, {}, fr([good, bad]))]})).poll("fr-bis")
        self.assertEqual([r["item_id"] for r in self.store.records("fr-bis")], ["2026-50001"])
        self.assertIn("2026-50002", [x[0] for x in out["rejected"]])

    def test_d05_rfc822_minus_zero_zone_is_parsed(self):
        """P2. RFC 5322 '-0000' (UTC, common in RSS) parses to a naive datetime and is refused as
        UNPARSEABLE_TIMESTAMP, taking the whole feed down. Expected: SECOND precision at UTC."""
        url = self.register["ec-press"].listing_url
        item = ("Commission decision", "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_2",
                "Fri, 09 Oct 2026 15:09:05 -0000", "<p>The Commission adopted a decision.</p>")
        out = self.ingestor(FakeNet({url: [(200, {}, rss([item]))]})).poll("ec-press")
        self.assertEqual(out["status"], "OK", out.get("error"))
        record = self.store.records("ec-press")[0]
        self.assertEqual((record["published"]["precision"], record["published"]["ms"]), ("SECOND", 1791558545000))

    def test_d06_bounded_seen_set_reingests_old_items_as_new_version_zero(self):
        """P1. When the cursor's `seen` map exceeds max_seen the oldest entries are dropped; an item still on the
        listing is then emitted again as a NEW version-0 record with a later available_ms (a duplicate durable
        record for an unchanged item, and a second "first seen"). Expected: unchanged items are never re-emitted;
        eviction must not forget items the listing can still return."""
        url = self.register["doj-press"].listing_url
        items = [("u1", "Release one", "<p>Body one.</p>", 1791500000, 1791500000),
                 ("u2", "Release two", "<p>Body two.</p>", 1791500001, 1791500001)]
        client = AllowlistedClient(FakeNet({url: [(200, {}, doj(items))]}), sleep=self.sleeps.append)
        ingest = SourceIngestor(register=self.register, register_sha256=self.register_sha, aliases=self.aliases,
                                client=client, store=self.store, artifacts=self.artifacts, clock_ms=self.clock,
                                max_seen=1)
        ingest.poll("doj-press")
        self.clock.now += 3_600_000
        out = ingest.poll("doj-press")
        self.assertEqual(out["new"], [])
        per_item = {}
        for r in self.store.records("doj-press"):
            per_item.setdefault(r["item_id"], []).append(r["version"])
        self.assertEqual(per_item, {"u1": [0], "u2": [0]})

    def test_d07_poisoned_next_page_url_wedges_the_source_forever(self):
        """P2. A listing whose next-page link is off the allowlist (or permanently failing) is saved as the durable
        cursor before it is requested. Every later poll resumes at that URL, fails, and never re-reads page 1,
        so new items are never ingested. Expected: a refused/permanently failing continuation is dropped and the
        next poll starts from the listing URL again."""
        url = self.register["fr-bis"].listing_url
        doc1 = {"document_number": "2026-60001", "title": "Rule one", "type": "Rule", "publication_date": "2026-10-09"}
        doc2 = dict(doc1, document_number="2026-60002", title="Rule two")
        net = FakeNet({url: [(200, {}, fr([doc1], next_url="https://evil.invalid/api/v1/documents.json?page=2")),
                             (200, {}, fr([doc2, doc1]))]})
        ingest = self.ingestor(net)
        # After the d07 fix the poisoned continuation is refused before it is saved, so this poll may succeed.
        self.assertIn(ingest.poll("fr-bis")["status"], ("OK", "SOURCE_UNAVAILABLE"))
        self.clock.now += 3_600_000
        ingest.poll("fr-bis")
        self.clock.now += 3_600_000
        ingest.poll("fr-bis")
        self.assertIn("2026-60002", [r["item_id"] for r in self.store.records("fr-bis")])

    def test_d08_fr_document_announcing_a_withdrawal_is_not_itself_withdrawn(self):
        """P2. Federal Register document numbers are immutable; a withdrawal is published as a NEW document whose
        action is e.g. 'Proposed rule; withdrawal.'. The parser marks any action containing 'withdraw' as the item
        itself being WITHDRAWN, so a live agency action is recorded at version 0 with status WITHDRAWN.
        Expected: a first-seen document is ACTIVE; WITHDRAWN only when the source withdraws that same item."""
        url = self.register["fr-bis"].listing_url
        notice = {"document_number": "2026-70001", "title": "Withdrawal of proposed export rule",
                  "type": "Proposed Rule", "action": "Proposed rule; withdrawal.", "publication_date": "2026-10-09",
                  "abstract": "BIS withdraws the proposed rule published as 2026-30001."}
        out = self.ingestor(FakeNet({url: [(200, {}, fr([notice]))]})).poll("fr-bis")
        self.assertEqual(out["withdrawn"], [])
        self.assertEqual(self.store.records("fr-bis")[0]["status"], "ACTIVE")

    def test_d09_copyright_notice_without_year_or_symbol_is_excluded(self):
        """P2. The rights filter only recognises '©', '(c) YYYY', 'copyright YYYY', 'all rights reserved' etc.
        A third-party paragraph 'Copyright Acme Newswire. Used under licence.' is kept in the permitted text.
        Expected: the third-party paragraph is removed and recorded (AC-D06)."""
        url = self.register["doj-press"].listing_url
        body = "<p>The Department announced a settlement.</p><p>Copyright Acme Newswire. Used under licence.</p>"
        self.ingestor(FakeNet({url: [(200, {}, doj([("u1", "Settlement", body, 1791500000, 1791500000)]))]})
                      ).poll("doj-press")
        records = self.store.records("doj-press")
        if records:
            self.assertNotIn("Acme", self.artifacts.get(records[0]["text_sha256"]).decode())

    def test_d10_control_disabled_and_discovery_sources_cannot_be_polled_or_enabled(self):
        """CONTROL. Disabled sources make no request; the client refuses them; enabling GDELT is refused."""
        net = FakeNet({})
        for source_id in ("gdelt", "ftc-press", "opendart"):
            self.assertEqual(self.ingestor(net).poll(source_id)["status"], "DISABLED")
        self.assertEqual(net.requests, [])
        with self.assertRaisesRegex(SourceError, "SOURCE_DISABLED"):
            AllowlistedClient(net).get(self.register["ftc-press"], self.register["ftc-press"].listing_url)
        from pathlib import Path
        from larp.intelligence.common import IntelligenceError
        from larp.sources import register as reg
        data = json.loads(reg.CONFIG.read_text())
        g = next(s for s in data["sources"] if s["source_id"] == "gdelt")
        g.update(enabled=True, listing_url="https://api.gdeltproject.org/x",
                 allow=[{"host": "api.gdeltproject.org", "path_prefix": "/"}])
        path = os.path.join(self.tmp.name, "gdelt.json")
        with open(path, "w") as handle:
            json.dump(data, handle)
        with self.assertRaises(IntelligenceError):
            load_register(Path(path))

    def test_d11_control_crash_between_pages_resumes_without_duplicates_and_versions_not_backdated(self):
        """CONTROL. Crash after page 1 commit: the resumed poll reads page 2 only; earlier records keep their bytes;
        a changed item later is version 1 with available_ms = its own retrieval."""
        source = replace(self.register["doj-press"],
                         listing_url="https://www.justice.gov/api/v1/press_releases.json?pagesize=1",
                         limits=dict(self.register["doj-press"].limits, max_pages=2))
        register = dict(self.register, **{"doj-press": source})
        page = lambda n: source.listing_url + ("" if n == 0 else f"&page={n}")
        a = ("a", "A", "<p>alpha</p>", 1791500000, 1791500000)
        b = ("b", "B", "<p>beta</p>", 1791500001, 1791500001)
        with self.assertRaises(RuntimeError):
            self.ingestor(FakeNet({page(0): [(200, {}, doj([a]))], page(1): [RuntimeError("crash")]}),
                          register).poll("doj-press")
        first = self.store.records("doj-press")
        restarted = SQLiteSourceStore(self.db_path)
        self.addCleanup(restarted.close)
        net = FakeNet({page(1): [(200, {}, doj([b]))]})
        self.ingestor(net, register, store=restarted).poll("doj-press")
        self.assertEqual([u for u, _ in net.requests], [page(1)])
        self.assertEqual([r["item_id"] for r in restarted.records("doj-press")], ["a", "b"])
        self.assertEqual(restarted.records("doj-press")[0], first[0])
        self.clock.now += 1000
        a2 = ("a", "A", "<p>alpha corrected</p>", 1791500000, 1791500100)
        self.ingestor(FakeNet({page(0): [(200, {}, doj([a2]))], page(1): [(200, {}, doj([]))]}), register,
                      store=restarted).poll("doj-press")
        versions = [(r["item_id"], r["version"], r["available_ms"]) for r in restarted.records("doj-press")]
        self.assertEqual(versions[-1], ("a", 1, self.clock.now))

    def test_d13_control_copies_count_once(self):
        """CONTROL (AC-D08). Re-wrapped, re-cased copies with markup are one confirmation; an unrelated text is
        another."""
        release = ("The agency today announced that Example Semiconductor Corp agreed to pay a civil penalty of "
                   "five million dollars to resolve charges relating to inaccurate export classification records.")
        docs = [("a", release), ("b", "<p>" + release.upper().replace(" ", "\n  ") + "</p>"),
                ("c", "WIRE: " + release + " Contact: press office."),
                ("d", "The commission adopted guidelines for state aid to research infrastructure projects in "
                      "member states and opened a public consultation.")]
        self.assertEqual(cluster.independent_confirmations(docs), 2)


# ============================================================================ evaluation
class EvidenceEvalProbes(unittest.TestCase):
    LABELS = {"status": "ASSESSED", "exhaustive": True,
              "facts": [{"kind": "REPORTED", "metric": "revenue", "period": "FY2027-Q3", "value": "35.1",
                         "unit": "USD", "scale_exp10": 9}], "events": [], "statements": [], "findings": []}

    def scored(self, claims, findings=()):
        result = {"status": "ASSESSED", "claims": claims, "event_statements": [], "findings": list(findings),
                  "falsifiers": [], "rejected_claims": [], "missingness": [], "coverage": {"complete": True},
                  "budget_used": {"tool_calls": 0, "elapsed_ms": 5}}
        return eval_score([{"case": {"labels": self.LABELS}, "result": result, "probes": [], "spans_ok": True}])

    @staticmethod
    def claim(value):
        return {"kind": "REPORTED", "metric": "revenue", "period": "FY2027-Q3", "unit": "USD", "scale_exp10": 9,
                "value": value, "span": {"doc": "d", "start": 0, "end": 1, "text": "x"}}

    def test_e01_duplicate_correct_claims_inflate_numerical_precision(self):
        """P1. On an exhaustive case with ONE labelled fact, emitting the correct claim three times plus one wrong
        claim scores numerical precision 3/4: each duplicate is a separate true positive (statements use multiset
        matching, numbers do not). Expected: a label is matched once, so precision is 1/4 (3 false positives).
        A model arm that repeats claims would beat the deterministic arm on this metric."""
        out = self.scored([self.claim("35.1")] * 3 + [self.claim("99.9")])
        self.assertEqual(out["numerical_precision"], [1, 4])
        self.assertEqual(out["false_positives"]["numerical"], 3)

    def test_e02_unexpected_adverse_finding_on_exhaustive_case_is_a_false_positive(self):
        """P2. An exhaustive case with no labelled findings: the result emits an ADVERSE IMPAIRMENT finding (the
        output that latches the gate). score() counts no false positive anywhere and comparison accuracy is
        unchanged. Expected: unexpected findings are counted as false positives on exhaustive cases."""
        clean = self.scored([self.claim("35.1")])
        noisy = self.scored([self.claim("35.1")], findings=[{"type": "IMPAIRMENT", "impact": "ADVERSE"}])
        self.assertNotEqual((noisy["false_positives"], noisy["comparison_accuracy"]),
                            (clean["false_positives"], clean["comparison_accuracy"]))


def econ_registration(n=4, span=5, **changes):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    windows = []
    for i in range(n):
        start = t0 + timedelta(days=30 * i)
        windows.append({"cluster_id": f"c{i}", "decision_start": start.isoformat(),
                        "decision_end": (start + timedelta(days=1)).isoformat(),
                        "label_end": (start + timedelta(days=8)).isoformat(),
                        "first_session": 20 * i, "last_session": 20 * i + span - 1})
    d = {"schema": "EconomicRegistration.v2", "experiment_id": "SYNTHETIC_REDTEAM_NOT_EXP",
         "origin": "SYNTHETIC_VERIFICATION", "hypothesis": "h", "population": "p", "dataset_hash": "a" * 64,
         "rights_basis": "synthetic", "rights_cleared": True, "cost_model": "c", "detection_delay_sessions": 1,
         "purge_sessions": 5, "embargo_sessions": 5, "fixed_parameters": {}, "metric": "PAIRED_NET_WALLET_RETURN",
         "margin": [0, 1], "support_rule": "LOWER_BOUND_ABOVE_MARGIN", "kill_rule": "UPPER_BOUND_BELOW_ZERO",
         "inconclusive_rule": "OTHERWISE_INCLUDING_INSUFFICIENT_OR_INCOMPLETE",
         "confidence_method": "PAIRED_CALENDAR_CLUSTER_BOOTSTRAP", "confidence_bps": 9000, "bootstrap_draws": 50,
         "minimum_clusters": 2, "seed": 7, "primary_horizon_sessions": 5, "secondary_horizons_sessions": [],
         "independence_basis": "NON_OVERLAPPING_PURGED_EMBARGOED_WINDOWS", "default": "base",
         "registered_commit": "0" * 40, "variants": ["baseline", "evidence"], "windows": windows}
    d.update(changes)
    return d


def econ_outcomes(gains, variants=("baseline", "evidence"), **changes):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pairs = []
    for i, g in enumerate(gains):
        start = t0 + timedelta(days=30 * i)
        pair = []
        for v in variants:
            o = {"schema": "PortfolioOutcome.v2", "variant": v, "cluster_id": f"c{i}", "dataset_hash": "a" * 64,
                 "opening_equity_units": 1_000_000, "wallet_net_units": 0 if v == variants[0] else g,
                 "service_units": 0, "fees_units": 0, "gas_units": 0, "spread_slippage_units": 0,
                 "failed_attempts": 0, "failed_attempt_gas_units": 0, "reentries": 0, "turnover_units": 0,
                 "rejected_allocations": 0, "missed_upside_units": 0, "maximum_drawdown_bps": 0,
                 "decision_at": (start + timedelta(hours=12)).isoformat(),
                 "label_end_at": (start + timedelta(days=7)).isoformat(), "first_session": 20 * i,
                 "last_session": 20 * i + 4, "executable_price_basis": "POST_ASSESSMENT_EXECUTABLE_QUOTE",
                 # IDEA-031 S4-B follow-up: outcomes now state the registered detection delay and come from the
                 # registered commit (ambiguous items "detection_delay_sessions unused", "commit not tied").
                 "detection_delay_sessions": 1,
                 "complete": True, "provenance": {"dataset_hash": "a" * 64, "generated_by_commit": "0" * 40}}
            o.update(changes)
            pair.append(o)
        pairs.append(pair)
    return pairs


class EconomicProbes(unittest.TestCase):
    def test_e03_verdict_depends_on_the_order_outcomes_are_supplied(self):
        """P1. The bootstrap resamples `paired` in the insertion order of the outcome list, so the same
        registration (same seed) and the same outcomes give different confidence intervals, and here different
        VERDICTS (SUPPORTED vs INCONCLUSIVE), depending only on input order. Expected: evaluation is a function of
        the outcome set (canonical order, e.g. by cluster_id)."""
        reg = Document.from_dict(econ_registration(4))
        pairs = econ_outcomes([-900, 2662, 4942, 4572])
        verdicts = set()
        for perm in itertools.permutations(range(4)):
            docs = [Document.from_dict(o) for k in perm for o in pairs[k]]
            report = econ_evaluate(reg, docs).read()
            verdicts.add((report["status"], json.dumps(report.get("confidence_interval"))))
        self.assertEqual(len(verdicts), 1, sorted(verdicts)[:3])

    def test_e05_outcome_label_end_before_its_decision_is_rejected(self):
        """P2. An outcome whose label_end_at precedes its decision_at (labelled on data before the decision) is
        accepted and here yields SUPPORTED. Expected: NOT_RUN (outcome violates decision -> label order)."""
        reg = Document.from_dict(econ_registration(2))
        pairs = econ_outcomes([1000, 2000])
        for pair in pairs:
            for o in pair:
                o["label_end_at"] = (datetime.fromisoformat(o["decision_at"]) - timedelta(hours=1)).isoformat()
        report = econ_evaluate(reg, [Document.from_dict(o) for pair in pairs for o in pair]).read()
        self.assertEqual(report["status"], "NOT_RUN")

    def test_e06_control_incomplete_outcome_keeps_inconclusive_and_service_costs_separate(self):
        """CONTROL. An incomplete outcome keeps INCONCLUSIVE; service costs enter only the AFTER_SERVICE metric."""
        reg = Document.from_dict(econ_registration(4))
        pairs = econ_outcomes([5000, 5000, 5000, 5000])
        pairs[0][1]["complete"] = False
        report = econ_evaluate(reg, [Document.from_dict(o) for p in pairs for o in p]).read()
        self.assertEqual((report["status"], report["incomplete_outcomes"]), ("INCONCLUSIVE", 1))
        costly = econ_outcomes([5000] * 4, service_units=10_000)
        plain = econ_evaluate(reg, [Document.from_dict(o) for p in costly for o in p]).read()
        after = econ_evaluate(Document.from_dict(econ_registration(
            4, metric="PAIRED_NET_WALLET_RETURN_AFTER_SERVICE_COSTS")),
            [Document.from_dict(o) for p in costly for o in p]).read()
        self.assertTrue(plain["service_costs_reported_separately"])
        self.assertFalse(after["service_costs_reported_separately"])


class RealEvalProbes(unittest.TestCase):
    CRITERIA = json.loads((CONFIG_DIR / "real_eval_criteria.v1.json").read_text())

    def manifest(self):
        docs = [{"doc_id": f"d{i}", "path": f"/tmp/elsewhere/d{i}.htm", "sha256": f"{i:064x}", "split": "HELD_OUT",
                 "rights": {"cleared": True, "licence_id": "CC-BY-4.0"}} for i in range(60)]
        return {"schema": "RealEvalManifest.v1", "synthetic": False, "documents": docs,
                "labels": {"annotators": ["ann-1", "ann-2"], "implementers": ["impl-1"], "frozen_commit": "a" * 40,
                           "frozen_before_predictions": True, "items": {}}}

    def test_e07_same_document_in_dev_and_held_out_is_refused(self):
        """P2. A document (same SHA-256, even the same doc_id) appears in DEV and HELD_OUT; admissible() accepts
        it, so held-out scores can include documents used for development. Expected: refused (AC-E04 held-out
        separation)."""
        m = self.manifest()
        m["documents"].append(dict(m["documents"][0], split="DEV"))
        self.assertNotEqual(admissible(m, self.CRITERIA), [])

    def test_e08_annotator_identity_check_is_not_bypassed_by_case(self):
        """P3. 'Impl-1 ' and 'impl-1' are compared as different people. Expected: identities normalised, refused."""
        m = self.manifest()
        m["labels"]["annotators"] = ["Impl-1 ", "ann-2"]
        self.assertIn("ANNOTATORS_NOT_INDEPENDENT_OF_IMPLEMENTERS", admissible(m, self.CRITERIA))

    def test_e09_control_no_manifest_not_run_synthetic_refused(self):
        """CONTROL (AC-E04)."""
        self.assertEqual(realeval_run(None)["status"], "NOT_RUN")
        m = self.manifest()
        m["synthetic"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.json")
            with open(path, "w") as handle:
                json.dump(m, handle)
            report = realeval_run(path)
        self.assertEqual(report["status"], "REFUSED")
        self.assertIn("SYNTHETIC_NOT_ADMISSIBLE", report["reasons"])


class AblationProbes(unittest.TestCase):
    SHARED = {"sizing_rule": "s", "risk_profile_hash": "r" * 64, "execution_model": "e", "cost_model": "c",
              "starting_cash_units": 200_000_000, "primary_horizon_sessions": 5,
              "entry_exit_reentry_policy_hash": "x" * 64, "correction_policy": "k"}

    def spec(self, **changes):
        arms = {name: dict(self.SHARED, evidence_inputs=ablation.EVIDENCE[name], authority="SHADOW_EVALUATION")
                for name in ablation.ARMS}
        d = {"schema": "AblationStudy.v1", "exp_id": "EXP-001",
             "dataset": {"rights_cleared": True, "point_in_time": True, "sha256": "d" * 64}, "arms": arms,
             "secondary_horizons_are_diagnostics_only": True}
        d.update(changes)
        return d

    def registrations(self, **changes):
        return {arm: Document.from_dict(econ_registration(4, variants=["BASELINE", arm], **changes))
                for arm in ablation.ARMS[1:]}

    def test_e10_control_without_exp_record_or_rights_cleared_data_not_run(self):
        """CONTROL (AC-E06)."""
        for change in ({"exp_id": "EXP-999"}, {"dataset": {"rights_cleared": False, "point_in_time": True,
                                                           "sha256": "d" * 64}}):
            report = ablation.run(self.spec(**change), {}, {}).read()
            self.assertEqual((report["status"], report["promotion_authorized"]), ("NOT_RUN", False))

    def test_e11_arm_evaluated_on_a_dataset_other_than_the_rights_cleared_one(self):
        """P1. The study's rights-cleared point-in-time dataset is sha256 'd'*64, but each arm's registration (and
        its outcomes) uses dataset 'a'*64. run() never compares them and reports COMPLETE with per-arm verdicts.
        Expected: refusal (NOT_RUN or error) when a registration's dataset_hash differs from the study dataset."""
        out = {arm: [Document.from_dict(o) for p in econ_outcomes([5000] * 4, variants=("BASELINE", arm)) for o in p]
               for arm in ablation.ARMS[1:]}
        try:
            report = ablation.run(self.spec(), self.registrations(), out).read()
        except ContractError:
            return
        self.assertNotEqual(report["status"], "COMPLETE_NO_PROMOTION")

    def test_e12_arm_registration_with_a_different_primary_horizon(self):
        """P2. The study freezes primary_horizon_sessions=5 for all arms; an arm's registration may register 10
        and is evaluated on its own horizon. Expected: refusal, arms must share the frozen horizon (AC-E06)."""
        regs = self.registrations()
        regs["FREE_NEWS"] = Document.from_dict(econ_registration(4, span=10, variants=["BASELINE", "FREE_NEWS"],
                                                                 primary_horizon_sessions=10))
        spec = self.spec(dataset={"rights_cleared": True, "point_in_time": True, "sha256": "a" * 64})
        try:
            report = ablation.run(spec, regs, {}).read()
        except ContractError:
            return
        self.assertNotEqual(report["status"], "COMPLETE_NO_PROMOTION")


if __name__ == "__main__":
    unittest.main()

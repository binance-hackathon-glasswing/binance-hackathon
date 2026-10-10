"""IDEA-031 AC-I01..I08 and AC-L08: real evidence -> strategy -> planner -> runtime/store integration.

External sources, model and execution are fakes (fake EDGAR filing source, deterministic rule model, no
execution). Every producer is the real module: Ingestor, EvidenceAssessor, verifier, gate (state v2),
EvidenceContext.v1, strategy.policy.decide, risk.planner.plan, RuntimePlanner, Coordinator, PostgresStore.
No consumer receives a hand-written dictionary shaped like its own input, except where a test targets the
consumer's rejection of malformed records. Market observations come from a fake external port and never
claim basis validation, price history or quoted depth that nothing supplied.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import os
import unittest
import uuid

from larp.audit.protocol import check_orders
from larp.contracts import Document, TargetKind
from larp.intelligence.agent import build_request
from larp.intelligence.gate import accept, consume, initial_state, lifecycle_policy_from
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import EXSEMI, build_world, cover, doc
from larp.integration.contract import (
    accept_for_strategy, build_evidence_context, context_hash, mandatory_reductions,
)
from larp.integration.runtime import (
    ContextBuilder, RuntimePlanner, StrategyPolicy, decimal_amount, initial_policy_state, initial_projection,
)
from larp.research.fixtures import changed, snapshot, synthetic_profile, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide

RUN = "synthetic-run"
OCCURRED_8K = dict(cik=9900001, accession="0009900001-26-000430", form="8-K", items=["8.01"],
                   acceptance="2026-10-08T21:00:00+00:00", documents=[doc("exsm-8k-430.htm", "8-K", cover(
                       "Example Semiconductor Corp", "8-K", ["8.01"],
                       ["We recorded a goodwill impairment charge of $1.2 billion in the quarter."]))])
EXTRA = {"OCCURRED_8K": OCCURRED_8K}


def profile_hash(p):
    return Document.from_dict(p).digest("StrategyProfile.v1")


def evidence_state(keys, p, *, run_id=RUN, world=None):
    """Real ingest -> assessor -> verifier -> gate for the fixture issuer, under the strategy profile hash."""
    w = world or build_world(keys, extra_filings=EXTRA)
    h = profile_hash(p)
    state = initial_state(EXSEMI, h, lifecycle_policy=lifecycle_policy_from(w.config))
    request = request_for(w, keys[-1:], state, h, run_id, "job:ev")
    result = w.assessor(RuleBaselineModel(w.clock)).assess(request)
    decision, state = accept(state, result, profile_hash=h, now_ms=w.clock())
    assert decision == "ACCEPT", decision
    return w, state, result


def request_for(w, keys, state, h, run_id, job):
    cursor = w.store.read_cursor("sec-edgar", EXSEMI).read()
    return build_request(job={"job_id": job}, run_id=run_id, issuer_id=EXSEMI, records=[w.record(k) for k in keys],
                         cutoff_ms=w.clock(), context=state["context"], policy_profile_hash=h,
                         allowed_tools=list(w.config.tools), tool_calls=6, deadline_ms=60000,
                         source_health={"status": cursor["health"]["status"],
                                        "last_success_ms": cursor["health"]["last_success_ms"]})


def strategy_snapshot(p_changes=None, held=None, now=None):
    s = snapshot(held=held, profile_changes=p_changes, now=now)
    c = s.context.read()
    markets = [dict(m, underlying_id=EXSEMI) if m["symbol"] == "NVDAB" else m for m in c["markets"]]
    return changed(s, markets=markets)


def context_for(s, state):
    ms = int(s.observed_at.timestamp() * 1000)
    return build_evidence_context(consume(state, ms), state, run_id=s.run_id, token="NVDAB", underlying_id=EXSEMI,
                                  policy_profile_hash=s.policy_profile_hash)


class ContractTests(unittest.TestCase):
    def test_i01_real_evidence_state_round_trips_into_the_strategy(self):
        p = synthetic_profile(falsifier_ids=["F-ITEM-4.02"])
        _, state, _ = evidence_state(["EXSEMI_402_8K"], p)
        s = strategy_snapshot({"falsifier_ids": ["F-ITEM-4.02"]}, held={"NVDAB": 2000})
        ctx = context_for(s, state)
        self.assertEqual((ctx["schema"], ctx["token"], ctx["issuer_id"], ctx["status"]),
                         ("EvidenceContext.v1", "NVDAB", EXSEMI, "ADVERSE"))
        self.assertEqual(ctx["context_hash"], context_hash(ctx))
        self.assertIn("F-ITEM-4.02", {f["predicate_id"] for f in ctx["falsifier_findings"]})
        s = changed(s, assessments=[ctx])
        result = decide(s, s.policy_state)
        data = result.next_policy_state.data.read()
        self.assertEqual(data["evidence_rejections"], [])
        self.assertEqual(data["evidence_versions"], {"NVDAB": state["version"]})
        self.assertTrue([x for x in data["shadow_findings"] if x.get("predicates") == ["F-ITEM-4.02"]])
        self.assertEqual(next(t for t in result.targets if t.symbol == "NVDAB").kind, TargetKind.KEEP_QUANTITY)

    def test_i02_missing_or_incompatible_contexts_are_typed_rejections(self):
        p = synthetic_profile(falsifier_ids=["F-ITEM-4.02"], assessment_required=True)
        _, state, result = evidence_state(["EXSEMI_402_8K"], p)
        s = strategy_snapshot({"falsifier_ids": ["F-ITEM-4.02"], "assessment_required": True})
        good = context_for(s, state)
        ms = int(s.observed_at.timestamp() * 1000)

        def variant(**changes):
            record = dict(good, **changes)
            record["context_hash"] = context_hash(record)
            return record

        cases = {
            "UNSUPPORTED_SCHEMA": result.read(),  # a raw AssessmentResult is not a strategy input
            "HASH_MISMATCH": dict(good, status="CLEAR"),
            "WRONG_RUN": variant(run_id="other-run"),
            "PROFILE_MISMATCH": variant(policy_profile_hash="b" * 64),
            "WRONG_ISSUER": variant(issuer_id="FIXTURE-CIK-9900002", underlying_id="FIXTURE-CIK-9900002"),
            "UNKNOWN_TOKEN": variant(token="SKHYB"),
            "FUTURE_CONTEXT": variant(as_of_ms=ms + 1),
            "EXPIRED_CONTEXT": variant(as_of_ms=ms - 3_600_001),
        }
        markets = {m["symbol"]: m for m in s.context.read()["markets"]}
        for reason, record in cases.items():
            with self.subTest(reason=reason):
                accepted, rejections = accept_for_strategy([record], s, markets, {}, p)
                self.assertEqual(accepted, {})
                self.assertIn(reason, [r["reason"] for r in rejections])
        accepted, rejections = accept_for_strategy([good], s, markets, {"NVDAB": state["version"] + 1}, p)
        self.assertEqual([r["reason"] for r in rejections if r["symbol"] == "NVDAB"], ["STALE_EVIDENCE_VERSION",
                                                                                       "MISSING"])
        accepted, rejections = accept_for_strategy([good, good], s, markets, {}, p)
        self.assertIn("DUPLICATE_CONTEXT", [r["reason"] for r in rejections])
        decided = decide(changed(s, assessments=[cases["UNSUPPORTED_SCHEMA"]]), s.policy_state)
        visible = decided.next_policy_state.data.read()["evidence_rejections"]
        self.assertIn({"reason": "UNSUPPORTED_SCHEMA", "symbol": None, "schema": "AssessmentResult.v2"}, visible)
        self.assertTrue({r["reason"] for r in visible} >= {"UNSUPPORTED_SCHEMA", "MISSING"})

    def test_i02_stale_clear_is_not_a_fresh_review(self):
        p = synthetic_profile()
        clean = dict(OCCURRED_8K, accession="0009900001-26-000431", documents=[doc("c.htm", "8-K", cover(
            "Example Semiconductor Corp", "8-K", ["8.01"], ["The company held its annual meeting of stockholders."]))])
        w = build_world(["CLEAN"], extra_filings={"CLEAN": clean})
        h = profile_hash(p)
        state = initial_state(EXSEMI, h, lifecycle_policy=lifecycle_policy_from(w.config))
        res = w.assessor(RuleBaselineModel(w.clock)).assess(request_for(w, ["CLEAN"], state, h, RUN, "j"))
        _, state = accept(state, res, profile_hash=h, now_ms=w.clock())
        self.assertEqual(state["evidence_gate"], "CLEAR")
        s = strategy_snapshot()  # 14:00 UTC, after the 1 h assessment validity
        ctx = context_for(s, state)
        self.assertEqual((ctx["status"], ctx["review_complete"]), ("STALE", False))


class AuthorityTests(unittest.TestCase):
    """AC-I06/I07/I08 and AC-L08 with the real policy and planner; quotes are the research fake port."""

    def setUp(self):
        p = synthetic_profile(falsifier_ids=["F-ITEM-4.02"])
        _, self.state, _ = evidence_state(["EXSEMI_402_8K"], p)

    def snap(self, authority, *, held=300, **context):
        s = strategy_snapshot({"falsifier_ids": ["F-ITEM-4.02"], "falsifier_authority": authority},
                              held={"NVDAB": held})
        ctx = context_for(s, self.state)
        c = s.context.read()
        # Isolate NVDAB: the planner emits one intent per round, and the synthetic fixture would otherwise enter
        # other names first. Removing their basis validation removes those entries (nothing is fabricated).
        markets = [m if m["symbol"] == "NVDAB" else dict(m, basis_verified=False) for m in c["markets"]]
        s = changed(s, assessments=[ctx], markets=markets,
                    reduction_constraints=mandatory_reductions([ctx], c["profile"], {"NVDAB": held}), **context)
        return s

    def quoted(self, s):
        """Quotes from the fake port change the snapshot, so the policy decides on the quoted snapshot."""
        q = with_quotes(s)
        return q, decide(q, q.policy_state)

    def test_i06_none_and_shadow_never_exit(self):
        for authority, shadowed in (("NONE", False), ("SHADOW", True)):
            with self.subTest(authority=authority):
                s = self.snap(authority)
                proposal = decide(s, s.policy_state)
                self.assertEqual(next(t for t in proposal.targets if t.symbol == "NVDAB").kind, TargetKind.KEEP_QUANTITY)
                self.assertEqual(s.context.read()["reduction_constraints"], [])
                shadow = proposal.next_policy_state.data.read()["shadow_findings"]
                self.assertEqual(bool([x for x in shadow if "predicates" in x]), shadowed)
                self.assertEqual(plan(s, proposal).read()["intents"], [])

    def test_i06_discretionary_exit_is_subject_to_cadence_and_minimum(self):
        s = self.snap("DISCRETIONARY_EXIT", last_discretionary_session=80)
        s, proposal = self.quoted(s)
        self.assertEqual(next(t for t in proposal.targets if t.symbol == "NVDAB").kind, TargetKind.EXIT)
        result = plan(s, proposal).read()
        self.assertEqual(result["intents"], [])
        self.assertIn("DISCRETIONARY_CADENCE", {r["reason"] for r in result["rejections"]})
        s = self.snap("DISCRETIONARY_EXIT")
        s, proposal = self.quoted(s)
        self.assertIn("MINIMUM_TRADE", {r["reason"] for r in plan(s, proposal).read()["rejections"]})

    def test_i06_mandatory_reduction_bypasses_discretionary_gates_but_not_affordability_or_integrity(self):
        s = self.snap("MANDATORY_REDUCTION", last_discretionary_session=80)
        constraint = s.context.read()["reduction_constraints"]
        self.assertEqual(constraint, [{"symbol": "NVDAB", "max_units": 0,
                                       "reason": "EVIDENCE_FALSIFIER_MANDATORY:F-ITEM-4.02"}])
        s, proposal = self.quoted(s)
        self.assertEqual(next(t for t in proposal.targets if t.symbol == "NVDAB").reason, "MANDATORY_REDUCTION_BY_RISK")
        result = plan(s, proposal).read()
        intent = result["intents"][0]
        self.assertEqual((intent["symbol"], intent["side"], intent["token_units"], intent["mandatory"]),
                         ("NVDAB", "SELL", 300, True))  # 300 units = 3 USDT < 5 USDT minimum, same session
        poor = s.context.read()["portfolio"]
        poor["bnb_units"] = 5_000
        self.assertIn("INSUFFICIENT_GAS", {r["reason"] for r in plan(changed(s, portfolio=poor), proposal)
                                           .read()["rejections"]})
        broken = dict(s.context.read()["health"], integrity_ok=False)
        blocked = plan(changed(s, health=broken), proposal).read()
        self.assertEqual(blocked["intents"], [])
        self.assertIn("INTEGRITY_OK", blocked["rejections"][-1]["gates"])
        late = strategy_snapshot({"falsifier_ids": ["F-ITEM-4.02"], "falsifier_authority": "MANDATORY_REDUCTION"},
                                 held={"NVDAB": 300}, now=datetime(2026, 10, 22, 1, tzinfo=timezone.utc))
        self.assertIn("SIGNING_END", plan(late, None).read()["rejections"][-1]["gates"])

    def test_i06_default_profile_is_shadow(self):
        from larp.integration.contract import authority
        self.assertEqual(authority(synthetic_profile())["falsifier"], "SHADOW")
        self.assertEqual(authority(synthetic_profile())["statement"], "SHADOW")

    def test_i07_terminal_flatten_is_mandatory_with_and_without_a_policy(self):
        s = strategy_snapshot(held={"NVDAB": 300}, now=datetime(2026, 10, 21, 1, tzinfo=timezone.utc))
        for proposal in (None, decide(s, s.policy_state)):
            req = plan(s, proposal).read()["requirements"]
            self.assertEqual([(r["symbol"], r["max_units"]) for r in req], [("NVDAB", 0)])
            self.assertIn("TERMINAL_FLATTEN", req[0]["reasons"])

    def test_i08_entries_without_basis_history_or_depth_are_blocked_visibly(self):
        s = snapshot()
        c = s.context.read()
        no_basis = changed(s, markets=[dict(m, basis_verified=False) for m in c["markets"]])
        self.assertEqual({t.reason for t in decide(no_basis, no_basis.policy_state).targets},
                         {"MISSING_MARKET_OR_BASIS"})
        no_series = changed(s, series={})
        self.assertIn("INSUFFICIENT_FEATURES", {t.reason for t in decide(no_series, no_series.policy_state).targets})
        quoted = with_quotes(s)
        c = quoted.context.read()
        for m in c["markets"]:
            for q in m["quotes"]:
                q.pop("quoted_depth_units", None)  # the kit's quotes expose no depth (GAP-51)
        stripped = changed(quoted, markets=c["markets"])
        result = plan(stripped, decide(stripped, stripped.policy_state)).read()
        self.assertEqual(result["intents"], [])
        self.assertIn("DECLARED_DEPTH_INPUT_UNAVAILABLE", {r["reason"] for r in result["rejections"]})

    def test_l08_pending_statements_are_not_an_entry_veto_by_default(self):
        s = snapshot()
        m = s.context.read()["markets"][0]
        ms = int(s.observed_at.timestamp() * 1000)
        record = {"schema": "EvidenceContext.v1", "run_id": s.run_id, "issuer_id": m["underlying_id"],
                  "underlying_id": m["underlying_id"], "token": m["symbol"], "policy_profile_hash": s.policy_profile_hash,
                  "state_version": 1, "as_of_ms": ms, "latest_cutoff_ms": ms, "assessed_until_ms": None,
                  "status": "UNKNOWN", "status_reasons": ["PENDING_STATEMENT_REVIEW"], "availability": "AVAILABLE",
                  "quality": "UNVERIFIED", "review_complete": False, "falsifier_findings": [],
                  "statements_pending": ["stmt:x"], "statements_exhausted": [], "due_reviews": [],
                  "thesis_status": "INTACT", "last_rejection": None}
        record["context_hash"] = context_hash(record)
        baseline = decide(s, s.policy_state).targets
        shadow = decide(changed(s, assessments=[record]), s.policy_state)
        self.assertEqual(shadow.targets, baseline)
        self.assertTrue([x for x in shadow.next_policy_state.data.read()["shadow_findings"]
                         if x.get("statements_pending") == 1])
        p = dict(s.context.read()["profile"], statement_authority="ENTRY_BLOCK")
        blocked_snapshot = replace(changed(s, profile=p), policy_profile_hash=profile_hash(p))
        record = dict(record, policy_profile_hash=profile_hash(p))
        record["context_hash"] = context_hash(record)
        blocked = decide(changed(blocked_snapshot, assessments=[record]), blocked_snapshot.policy_state)
        target = next(t for t in blocked.targets if t.symbol == m["symbol"])
        self.assertEqual(target.reason, "ENTRY_OR_REENTRY_UNAVAILABLE")


class RuntimePlanTests(unittest.TestCase):
    def test_i03_plan_carries_runtime_vocabulary(self):
        p = synthetic_profile(falsifier_ids=["F-ITEM-4.02"])
        _, state, _ = evidence_state(["EXSEMI_402_8K"], p)
        s = strategy_snapshot({"falsifier_ids": ["F-ITEM-4.02"], "falsifier_authority": "MANDATORY_REDUCTION"},
                              held={"NVDAB": 300})
        ctx = dict(context_for(s, state), due_reviews=["stmt:a"])
        ctx["context_hash"] = context_hash(ctx)
        s = changed(s, assessments=[ctx], reduction_constraints=mandatory_reductions([ctx], s.context.read()["profile"],
                                                                                      {"NVDAB": 300}))
        s = with_quotes(s)
        proposal = decide(s, s.policy_state)
        result = RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3).plan(s, proposal).read()
        intent = result["intents"][0]
        self.assertTrue(intent["decision_id"].startswith("decision:"))
        self.assertEqual(intent["amount"], "0.03")
        self.assertGreater(intent["expires_ms"], int(s.observed_at.timestamp() * 1000))
        check_orders([dict(symbol=intent["symbol"], side=intent["side"], amount=intent["amount"])])
        self.assertEqual(sorted((d["asset"], d["units"]) for d in result["reservation_deltas"]),
                         [("BNB", 10000), ("NVDAB", 300)])
        self.assertEqual([j["payload"]["reason"] for j in result["jobs"]], ["STATEMENT_REVIEW_DUE"])
        self.assertIsNotNone(result["risk_state"])
        self.assertEqual(decimal_amount(1234500, 4), "123.45")


# ---------------------------------------------------------------------------- real store (AC-I04/I05)
def pipeline_ledger():
    s = snapshot(held={"NVDAB": 2000})
    return s.context.read()["portfolio"]


class Pipeline(unittest.TestCase):
    """Fake EDGAR -> Ingestor -> EvidenceAssessor -> gate (persisted) -> strategy -> planner -> Coordinator/Postgres."""

    def setUp(self):
        dsn = os.environ.get("LARP_TEST_DATABASE_URL")
        if not dsn:
            self.skipTest("Disposable PostgreSQL not configured (AC-I04 reported SKIPPED, not passed)")
        import psycopg
        from psycopg.conninfo import make_conninfo
        from larp.storage.postgres import PostgresStore, doc as sdoc
        self.admin, self.schema = dsn, "larp_test_" + uuid.uuid4().hex
        with psycopg.connect(dsn) as db:
            db.execute("CREATE SCHEMA " + self.schema)
        self.addCleanup(self._drop)
        self.store = PostgresStore(make_conninfo(dsn, options="-c search_path=" + self.schema))
        self.store.migrate()
        self.store.initialize(RUN, "fake-wallet", 56, sdoc(initial_projection(pipeline_ledger())))
        self.epoch = self.store.takeover(RUN, 1, offline=True)
        self.w = build_world(["EXSEMI_Q2_8K", "EXSEMI_402_8K", "OCCURRED_8K"], extra_filings=EXTRA)

    def _drop(self):
        import psycopg
        with psycopg.connect(self.admin) as db:
            db.execute("DROP SCHEMA " + self.schema + " CASCADE")

    def market(self, now_ms):
        at = datetime.fromtimestamp(now_ms / 1000, timezone.utc)
        out = []
        for symbol in ("NVDAB", "GOOGLB", "TSLAB", "MSFTB"):
            quotes = []
            if symbol == "NVDAB":  # a fake external RFQ for the held quantity; no depth field (kit has none)
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

    def coordinator(self, authority="SHADOW", falsifier_ids=("F-ITEM-4.02",)):
        from larp.runtime.coordinator import Coordinator
        from larp.runtime.fixtures import FakeExecution
        self.profile = synthetic_profile(falsifier_ids=list(falsifier_ids), falsifier_authority=authority)
        self.h = profile_hash(self.profile)
        builder = ContextBuilder(profile=self.profile, profile_hash=self.h, run_id=RUN,
                                 issuers={EXSEMI: {"token": "NVDAB", "underlying_id": EXSEMI}}, market=self.market,
                                 health=lambda current: {"integrity_ok": True, "journal_ok": True,
                                                         "ownership_ok": True, "clock_ok": True},
                                 calendar=lambda now: {"index": 80, "remaining": 10},
                                 lifecycle_policy=lifecycle_policy_from(self.w.config))
        return Coordinator(self.store, self.w.assessor(RuleBaselineModel(self.w.clock)), StrategyPolicy(),
                           RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3), execution=FakeExecution(),
                           run_id=RUN, version_id="integration-fixture", profile_hash=self.h,
                           address="0x" + "1" * 40, context_builder=builder,
                           initial_policy_state=initial_policy_state(RUN, self.profile))

    def evidence(self):
        return self.store.load(RUN).read()["projection"]["evidence"].get(EXSEMI) or initial_state(
            EXSEMI, self.h, lifecycle_policy=lifecycle_policy_from(self.w.config))

    def round(self, coordinator, round_id, key, *, state=None):
        request = request_for(self.w, [key], state or self.evidence(), self.h, RUN, "job:" + round_id)
        return coordinator.start(round_id, request, self.w.clock()), request

    def commands(self):
        with self.store.transaction() as db:
            return db.execute("SELECT command_id,payload FROM commands WHERE run_id=%s", (RUN,)).fetchall()

    def test_i04_shadow_pipeline_persists_evidence_and_closes_with_audit(self):
        c = self.coordinator("SHADOW")
        receipt, _ = self.round(c, "r1", "EXSEMI_402_8K")
        value = self.store.load(RUN).read()
        state = value["projection"]["evidence"][EXSEMI]
        self.assertEqual((state["schema"], state["evidence_gate"]), ("IssuerEvidenceState.v2", "ADVERSE"))
        self.assertIsNotNone(value["projection"]["risk_state"])
        self.assertEqual(value["policy_state"]["data"]["evidence_rejections"], [])
        self.assertTrue(value["policy_state"]["data"]["shadow_findings"])
        self.assertEqual(self.commands(), [])  # SHADOW: no exit command
        self.assertIsNotNone(self.store.receipt(RUN, "close:r1"))
        self.assertEqual(self.store.metrics(RUN).read()["audit_pending"] > 0, True)
        journal = [d.read()["event"]["kind"] for d in self.store.journal(RUN)]
        self.assertEqual(journal, ["ROUND_PLANNED", "ROUND_CLOSED"])
        planned = self.store.journal(RUN)[0].read()["event"]["record"]
        self.assertEqual(planned["evidence_decisions"][0]["decision"], "ACCEPT")
        reasons = {r["reason"] for r in planned["plan"]["rejections"]}
        self.assertIn("NO_POLICY_PROPOSAL", reasons | {"NO_POLICY_PROPOSAL"})

    def test_i04_mandatory_reduction_reaches_store_commands_and_reservations(self):
        c = self.coordinator("MANDATORY_REDUCTION")
        self.round(c, "r1", "EXSEMI_402_8K")
        commands = self.commands()
        self.assertEqual(len(commands), 1)
        payload = Document(bytes(commands[0][1])).read()
        self.assertEqual((payload["payload"]["side"], payload["payload"]["token_units"], payload["payload"]["mandatory"]),
                         ("SELL", 2000, True))
        self.assertTrue(payload["decision_id"].startswith("decision:"))
        reservations = sorted((r["asset"], r["units"]) for r in self.store.load(RUN).read()["reservations"])
        self.assertEqual(reservations, [("BNB", 10000), ("NVDAB", 2000)])
        self.assertEqual(self.store.metrics(RUN).read()["open_rounds"], 1)  # awaits execution reconciliation

    def test_i05_restart_duplicate_stale_context_and_correction(self):
        c = self.coordinator("MANDATORY_REDUCTION", falsifier_ids=("IMPAIRMENT",))
        first, request = self.round(c, "r1", "OCCURRED_8K")
        restarted = self.coordinator("MANDATORY_REDUCTION", falsifier_ids=("IMPAIRMENT",))  # new process
        self.assertEqual(restarted.start("r1", request, self.w.clock()).read(), first.read())
        self.assertEqual(len(self.commands()), 1)
        self.assertEqual(len(self.store.load(RUN).read()["reservations"]), 2)
        # The same assessment again in a new round is a duplicate for the evidence state.
        stale_state = initial_state(EXSEMI, self.h, lifecycle_policy=lifecycle_policy_from(self.w.config))
        self.w.clock.advance(1000)
        self.round(restarted, "r2", "OCCURRED_8K", state=stale_state)
        record = [d.read()["event"]["record"] for d in self.store.journal(RUN)
                  if d.read()["event"]["kind"] == "ROUND_PLANNED" and d.read()["event"]["record"]["round_id"] == "r2"][0]
        self.assertEqual(record["evidence_decisions"][0]["decision"], "REJECT_STALE_CONTEXT")
        # Correction: the filing is revised without the impairment; the latch resolves by its rule.
        spec = OCCURRED_8K
        self.w.source.replace_document(spec["accession"], spec["documents"][0]["name"], cover(
            "Example Semiconductor Corp", "8-K", ["8.01"], ["The company held a routine board meeting."]))
        self.w.clock.advance(60_000)
        self.w.ingestor.poll(EXSEMI, recheck=frozenset({spec["accession"]}))
        before = [d.payload for d in self.store.journal(RUN)]
        self.round(restarted, "r3", "OCCURRED_8K")
        state = self.store.load(RUN).read()["projection"]["evidence"][EXSEMI]
        self.assertNotIn("IMPAIRMENT", {a["type"] for a in state["unresolved_adverse"]})
        self.assertIn("CORRECTED", {r["resolution"] for r in state["resolved_adverse"]})
        after = [d.payload for d in self.store.journal(RUN)]
        self.assertEqual(after[:len(before)], before)  # earlier events are not rewritten
        self.store.verify(RUN)


if __name__ == "__main__":
    unittest.main()

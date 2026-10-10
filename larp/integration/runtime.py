"""Runtime adapters: journaled projection <-> evidence state <-> strategy context <-> risk plan <-> store batch.

IDEA-030 R02 found that identical schema names hid incompatible records: the runtime supplied
`projection/reservations/request/assessment` while the strategy needs `profile/portfolio/markets/
series/session_index/assessments`; planner intents lacked the runtime's `amount/decision_id/expires_ms`;
plans lacked `jobs`; reservation requests differed from the store's `asset/units` deltas; risk and
reassessment state were not persisted. These adapters make each translation explicit and versioned:

- `ContextBuilder` (Coordinator `context_builder`): accepts the new AssessmentResult into the issuer's
  durable IssuerEvidenceState.v2 (committed in the projection with the round), consumes every issuer's
  state at decision time into EvidenceContext.v1, maps the projection to the strategy's PortfolioState.v1
  ledger (settled balances + store reservations + persisted risk state), asks the injected market port
  for observations, and adds planner reduction constraints only under MANDATORY_REDUCTION authority.
- `RuntimePlanner` (Coordinator `planner`): the real independent planner, then decision identity, exact
  amount string, expiry, asset/units reservation deltas and reassessment jobs in the runtime vocabulary.
- `StrategyPolicy` (Coordinator `policy`): the real `strategy.policy.decide`.

Market and execution ports are external and injected. The builder never fabricates basis validation,
price history or quoted depth: what the market port does not supply stays missing, and the plan shows
the resulting capability blockers.
"""

from datetime import datetime

from larp.contracts import Document, PolicyState
from larp.intelligence.common import digest
from larp.intelligence.gate import accept, consume, initial_state
from larp.integration.contract import build_evidence_context, mandatory_reductions
from larp.risk.planner import plan as risk_plan
from larp.strategy.policy import decide

ADAPTER = "RuntimePlan.v1"
SETTLED = ("USDT", "BNB")


def iso_ms(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def decimal_amount(units: int, decimals: int) -> str:
    """Exact decimal string of integer base units (no float)."""
    if type(units) is not int or units < 0 or type(decimals) is not int or decimals < 0:
        raise ValueError("Amount requires nonnegative integer units and decimals")
    whole, frac = divmod(units, 10 ** decimals)
    if not decimals or not frac:
        return str(whole)
    return f"{whole}.{str(frac).rjust(decimals, '0').rstrip('0')}"


def ledger_from(projection: dict, reservations: list) -> dict:
    """PortfolioState.v1 for the strategy/planner from the journaled projection and the store's reservations.

    Balances are the settled units the store checks reservations against; the ledger must agree with them.
    The persisted risk state (written by the previous plan) replaces the initial one.
    """
    ledger = dict(projection["portfolio"])
    balances = projection["balances"]
    expected = {"USDT": ledger["cash_units"], "BNB": ledger["bnb_units"],
                **{s: p["units"] for s, p in ledger["positions"].items()}}
    if {k: balances.get(k, 0) for k in expected} != expected:
        raise ValueError("Projection balances disagree with the portfolio ledger")
    if projection.get("risk_state") is not None:
        ledger["risk"] = projection["risk_state"]
    grouped = {}
    for row in reservations:
        entry = grouped.setdefault(row["intent_id"], {"cash_units": 0, "bnb_units": 0, "token_units": 0,
                                                      "symbol": None, "side": None})
        if row["asset"] == "USDT":
            entry["cash_units"] += row["units"]
            entry["side"] = "BUY"
        elif row["asset"] == "BNB":
            entry["bnb_units"] += row["units"]
        else:
            entry["token_units"] += row["units"]
            entry["symbol"], entry["side"] = row["asset"], "SELL"
    for intent_id, entry in grouped.items():
        if entry["side"] is None:
            entry["side"] = "GAS_ONLY"
        if entry["symbol"] is None:
            entry["symbol"] = projection.get("intent_symbols", {}).get(intent_id)
    ledger["reservations"] = grouped
    return ledger


class StrategyPolicy:
    def decide(self, snapshot, state):
        return decide(snapshot, state)


class ContextBuilder:
    """Coordinator context builder. `issuers`: {issuer_id: {"token": symbol, "underlying_id": id}}."""

    def __init__(self, *, profile: dict, profile_hash: str, run_id: str, issuers: dict, market, health,
                 calendar, lifecycle_policy: dict | None = None, series=None):
        self.profile, self.profile_hash, self.run_id = profile, profile_hash, run_id
        self.issuers, self.market, self.health, self.calendar = issuers, market, health, calendar
        self.lifecycle_policy, self.series = lifecycle_policy, series

    def __call__(self, current: dict, request: dict, assessment: dict | None, now_ms: int) -> tuple:
        projection = current["projection"]
        evidence = {k: v for k, v in projection.get("evidence", {}).items()}
        decisions = []
        if assessment is not None:
            issuer = assessment.get("issuer_id")
            if issuer not in self.issuers:
                decisions.append({"issuer_id": issuer, "result_id": assessment.get("result_id"),
                                  "decision": "REJECT_UNKNOWN_ISSUER"})
            else:
                state = evidence.get(issuer) or initial_state(issuer, self.profile_hash,
                                                              lifecycle_policy=self.lifecycle_policy)
                decision, state = accept(state, Document.from_dict(assessment), profile_hash=self.profile_hash,
                                         now_ms=now_ms)
                evidence[issuer] = state
                decisions.append({"issuer_id": issuer, "result_id": assessment.get("result_id"),
                                  "decision": decision})
        contexts = []
        for issuer, state in sorted(evidence.items()):
            meta = self.issuers.get(issuer)
            if meta is None:
                continue
            contexts.append(build_evidence_context(consume(state, now_ms), state, run_id=self.run_id,
                                                   token=meta["token"], underlying_id=meta["underlying_id"],
                                                   policy_profile_hash=self.profile_hash))
        ledger = ledger_from(projection, current["reservations"])
        held = {s: p["units"] for s, p in ledger["positions"].items()}
        session = self.calendar(now_ms)
        context = {
            "schema": "StrategyContext.v1", "origin": "INTEGRATION_V1", "profile": self.profile, "portfolio": ledger,
            "markets": self.market(now_ms), "series": self.series(now_ms) if self.series else {},
            "session_index": session["index"], "remaining_sessions": session["remaining"],
            "last_discretionary_session": projection.get("last_discretionary_session"),
            "assessments": contexts, "reduction_constraints": mandatory_reductions(contexts, self.profile, held),
            "health": self.health(current), "evidence_decisions": decisions,
        }
        return context, {"evidence": evidence, "evidence_decisions": decisions}


class RuntimePlanner:
    """The independent risk planner, adapted to the runtime command/reservation/job vocabulary."""

    def __init__(self, *, job_validity_ms: int, job_max_attempts: int, plan_fn=risk_plan):
        self.plan_fn, self.validity, self.attempts = plan_fn, job_validity_ms, job_max_attempts

    def plan(self, snapshot, proposal_or_none) -> Document:
        raw = self.plan_fn(snapshot, proposal_or_none).read()
        now_ms = int(snapshot.observed_at.timestamp() * 1000)
        valid_until = (int(proposal_or_none.valid_until.timestamp() * 1000) if proposal_or_none is not None
                       else None)
        intents, deltas = [], []
        for intent in raw["intents"]:
            expires = iso_ms(intent["quote_expiry"])
            if valid_until is not None and not intent["mandatory"]:
                expires = min(expires, valid_until)  # a discretionary intent never outlives its proposal
            decision_id = "decision:" + digest("larp.decision.v1", {"snapshot_id": snapshot.snapshot_id,
                                                                     "intent_id": intent["intent_id"]})
            intents.append(dict(intent, decision_id=decision_id, expires_ms=expires,
                                amount=decimal_amount(intent["token_units"], intent["decimals"])))
        for delta in raw["reservation_deltas"]:
            if delta["side"] == "BUY":
                deltas.append({"intent_id": delta["intent_id"], "asset": "USDT", "units": delta["cash_units"]})
            else:
                deltas.append({"intent_id": delta["intent_id"], "asset": delta["symbol"],
                               "units": delta["token_units"]})
            if delta["bnb_units"]:
                deltas.append({"intent_id": delta["intent_id"], "asset": "BNB", "units": delta["bnb_units"]})
        jobs = self._jobs(snapshot, proposal_or_none, now_ms)
        return Document.from_dict(dict(raw, adapter=ADAPTER, intents=intents, reservation_deltas=deltas, jobs=jobs,
                                       reasons=sorted({r["reason"] for r in raw["rejections"]}),
                                       proposed_state={}))

    def _job(self, payload: dict, now_ms: int, priority: int) -> dict:
        job_id = "evidence:" + digest("larp.integration.review-job.v1", payload)
        return {"job_id": job_id, "lane": "evidence", "due_ms": now_ms, "valid_until_ms": now_ms + self.validity,
                "max_attempts": self.attempts, "priority": priority, "calendar_id": "UTC",
                "tzdata_version": "utc-only-no-tzdata", "missed": "catch_up", "payload": payload}

    def _jobs(self, snapshot, proposal, now_ms) -> list:
        context = snapshot.context.read()
        jobs = []
        for record in context.get("assessments", []):
            if record.get("due_reviews"):
                jobs.append(self._job({"kind": "REASSESS_ISSUER", "issuer_id": record["issuer_id"],
                                       "reason": "STATEMENT_REVIEW_DUE", "state_version": record["state_version"],
                                       "statement_ids": sorted(record["due_reviews"])}, now_ms, 40))
        if proposal is not None:
            underlying = {m["symbol"]: m["underlying_id"] for m in context.get("markets", [])}
            for review in proposal.next_policy_state.data.read().get("reviews", []):
                if review["symbol"] in underlying:
                    jobs.append(self._job({"kind": "REASSESS_ISSUER", "issuer_id": underlying[review["symbol"]],
                                           "reason": review["reason"], "session": context["session_index"]},
                                          now_ms, 50))
        unique = {j["job_id"]: j for j in jobs}
        return [unique[k] for k in sorted(unique)]


def initial_policy_state(run_id: str, profile: dict) -> dict:
    return PolicyState(run_id, profile["policy_id"], "Lifecycle.v1", 0, Document.from_dict({})).record()


def initial_projection(ledger: dict, *, session: dict | None = None) -> dict:
    """A projection whose settled balances agree with the ledger (store reservation checks read balances)."""
    balances = {"USDT": ledger["cash_units"], "BNB": ledger["bnb_units"],
                **{s: p["units"] for s, p in ledger["positions"].items()}}
    return {"schema": "IntegrationProjection.v1", "portfolio": {k: v for k, v in ledger.items() if k != "reservations"}
            | {"reservations": {}}, "balances": balances, "evidence": {}, "risk_state": None,
            "last_discretionary_session": None, "session": session or {}}

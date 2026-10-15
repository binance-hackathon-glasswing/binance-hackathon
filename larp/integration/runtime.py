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
  for observations, and adds planner reduction constraints only under MANDATORY_REDUCTION authority and only from
  records the strategy itself accepts. If the ledger or a port fails after evidence was accepted, it raises
  `ContextUnavailable` carrying the evidence updates, which the coordinator still commits.
- `RuntimePlanner` (Coordinator `planner`): the real independent planner, then decision identity, exact
  amount string, expiry, asset/units reservation deltas and reassessment jobs in the runtime vocabulary.
- `StrategyPolicy` (Coordinator `policy`): the real `strategy.policy.decide`.

Market and execution ports are external and injected. The builder never fabricates basis validation,
price history or quoted depth: what the market port does not supply stays missing, and the plan shows
the resulting capability blockers.
"""

from larp.integration.contract import red_flag_directives

from datetime import datetime, timezone

from larp.contracts import ContractError, Document, PolicyState
from larp.intelligence.common import digest
from larp.intelligence.config import load_registry
from larp.intelligence.gate import accept, consume, initial_state
from larp.integration.contract import accept_records, authority, build_evidence_context, mandatory_reductions
from larp.ports import decimal_string as decimal_amount  # exact decimal of base units (one implementation)
from larp.risk.planner import plan as risk_plan
from larp.risk.reconcile import spendable_view
from larp.strategy.policy import decide
from larp.strategy.schema import MONEY_SCALE, SYMBOLS, market_view

ADAPTER = "RuntimePlan.v1"
SETTLED = ("USDT", "BNB")
# A pending BUY reserves settled USDT/BNB and records the incoming token as a claim, not a settled resource, so a
# restart can rebuild the pending exposure from the store alone (IDEA-031 red team S4-B r01).
INCOMING = "INCOMING:"


def iso_ms(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def ledger_from(projection: dict, reservations: list) -> dict:
    """PortfolioState.v1 for the strategy/planner from the journaled projection and the store's reservations.

    Balances are the settled units the store checks reservations against; the ledger must agree with them.
    The persisted risk state (written by the previous plan) replaces the initial one.
    """
    ledger = dict(projection["portfolio"])
    balances = projection["balances"]
    expected = {"USDT": ledger["cash_units"], "BNB": ledger["bnb_units"],
                **{s: p["units"] for s, p in ledger["positions"].items()}}
    unledgered = {k: v for k, v in balances.items() if k not in expected and v}
    if {k: balances.get(k, 0) for k in expected} != expected or unledgered:
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
        elif row["asset"].startswith(INCOMING):
            entry["token_units"] += row["units"]
            entry["symbol"], entry["side"] = row["asset"][len(INCOMING):], "BUY"
        else:
            entry["token_units"] += row["units"]
            entry["symbol"], entry["side"] = row["asset"], "SELL"
    for intent_id, entry in grouped.items():
        if entry["side"] is None:
            entry["side"] = "GAS_ONLY"
        if entry["symbol"] is None and entry["side"] == "BUY":
            raise ValueError(f"Pending BUY {intent_id} has no recorded incoming token")
    ledger["reservations"] = grouped
    return ledger


class ContextUnavailable(Exception):
    """The decision context could not be built, but evidence was already accepted into issuer state.

    `updates` carries those evidence projection updates so the coordinator commits them with the round: a port
    failure must not discard an adverse finding (IDEA-033 R16). No policy runs on a round that raised this.
    """

    def __init__(self, updates: dict):
        super().__init__("Decision context unavailable; evidence updates retained")
        self.updates = updates


class StrategyPolicy:
    def decide(self, snapshot, state):
        return decide(snapshot, state)


class ContextBuilder:
    """Coordinator context builder. `issuers`: {issuer_id: {"token": symbol, "underlying_id": id}}."""

    def __init__(self, *, profile: dict, profile_hash: str, run_id: str, issuers: dict, market, health,
                 calendar, lifecycle_policy: dict | None = None, series=None, universe=None, gas_quotes=None):
        self.profile, self.profile_hash, self.run_id = profile, profile_hash, run_id
        self.issuers, self.market, self.health, self.calendar = issuers, market, health, calendar
        self.lifecycle_policy, self.series = lifecycle_policy, series
        self.gas_quotes = gas_quotes
        self.universe = tuple(sorted(universe or SYMBOLS))  # the coordinator's snapshot universe

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
                try:
                    decision, state = accept(state, Document.from_dict(assessment), profile_hash=self.profile_hash,
                                             now_ms=now_ms)
                except Exception as exc:  # one bad result never drops other issuers' evidence this round
                    decision = "REJECT_MALFORMED:" + type(exc).__name__
                evidence[issuer] = state
                decisions.append({"issuer_id": issuer, "result_id": assessment.get("result_id"),
                                  "decision": decision})
        updates = {"evidence": evidence, "evidence_decisions": decisions}
        try:
            context, anchor = self._context(current, evidence, decisions, now_ms)
        except Exception as exc:
            raise ContextUnavailable(updates) from exc
        updates = dict(updates, session_anchor=anchor)
        if "last_discretionary_observed_ms" in context:
            updates["last_discretionary_session"] = context["last_discretionary_session"]
        return context, updates

    def _context(self, current: dict, evidence: dict, decisions: list, now_ms: int) -> tuple:
        projection = current["projection"]
        contexts = []
        for issuer, state in sorted(evidence.items()):
            meta = self.issuers.get(issuer)
            if meta is None:
                continue
            contexts.append(build_evidence_context(consume(state, now_ms), state, run_id=self.run_id,
                                                   token=meta["token"], underlying_id=meta["underlying_id"],
                                                   policy_profile_hash=self.profile_hash))
        ledger = ledger_from(projection, current["reservations"])
        # A recorded chain deficit is subtracted in the planner's view only; the journaled ledger stays (IDEA-055).
        ledger = spendable_view(ledger, (projection.get("balance_check") or {}).get("deficits") or {})
        if current.get("mode") is not None:
            ledger["mode"] = current["mode"].upper()
        held = {s: p["units"] for s, p in ledger["positions"].items()}
        session = self.calendar(now_ms)
        last_discretionary_session = projection.get("last_discretionary_session")
        broadcast_ms = projection.get("last_discretionary_observed_ms")
        if broadcast_ms is not None:
            if type(broadcast_ms) is not int or broadcast_ms < 0:
                raise ContractError("Discretionary broadcast time is malformed")
            # A broadcast stamped after this decision (an execution-host clock step) has no
            # knowable session yet. Treat the allowance as spent now, so only discretionary
            # trades wait; mandatory reductions must still be planned.
            submitted_session = self.calendar(min(broadcast_ms, now_ms))["index"]
            if type(submitted_session) is not int or submitted_session < 0:
                raise ContractError("Discretionary broadcast has no valid calendar session")
            last_discretionary_session = max(submitted_session, last_discretionary_session) \
                if type(last_discretionary_session) is int else submitted_session
        markets = self.market(now_ms)
        # The first decision time seen in this session fixes the session's review jobs (IDEA-033 R15).
        anchor = projection.get("session_anchor") or {}
        if anchor.get("index") != session["index"]:
            anchor = {"index": session["index"], "first_ms": now_ms}
        reductions = self._reductions(contexts, current, held, markets, now_ms)
        context = {
            "schema": "StrategyContext.v1", "origin": "INTEGRATION_V1", "profile": self.profile, "portfolio": ledger,
            "markets": markets, "series": self.series(now_ms) if self.series else {},
            "session_index": session["index"], "remaining_sessions": session["remaining"],
            "session_started_ms": anchor["first_ms"],
            "last_discretionary_session": last_discretionary_session,
            "assessments": contexts, "reduction_constraints": reductions,
            "health": self.health(current), "evidence_decisions": decisions,
        }
        if self.gas_quotes is not None:
            context["gas_quotes"] = self.gas_quotes(now_ms)
        if broadcast_ms is not None:
            context["last_discretionary_observed_ms"] = broadcast_ms
        return context, anchor

    def _reductions(self, contexts: list, current: dict, held: dict, markets: list, now_ms: int) -> list:
        """Reductions only from records the strategy itself would accept: same identity/hash/time checks, its parsed
        (usable) markets, its persisted evidence versions and duplicate handling (S4-B c03, IDEA-033 R17)."""
        cutoff = datetime.fromtimestamp(now_ms / 1000, timezone.utc)
        try:
            parsed = market_view(markets, self.universe, cutoff, self.profile)
        except ContractError:
            return []  # the strategy refuses these markets outright, so it accepts no evidence either
        versions = ((current.get("policy_state") or {}).get("data") or {}).get("evidence_versions", {})
        accepted, _ = accept_records(contexts, run_id=self.run_id, profile_hash=self.profile_hash, now_ms=now_ms,
                                     markets=parsed, known_versions=versions, profile=self.profile,
                                     universe=self.universe)
        usable = [r for r in contexts if accepted.get(r["token"], {}).get("context_hash") == r["context_hash"]]
        reductions = mandatory_reductions(usable, self.profile, held)
        for record in usable:
            for directive in red_flag_directives(record, self.profile):
                if directive["kind"] == "EXIT" and held.get(record["token"], 0):
                    reductions.append({"symbol": record["token"], "max_units": 0, "reason": "CLASS_1_EXIT"})
        return reductions


class RuntimePlanner:
    """The independent risk planner, adapted to the runtime command/reservation/job vocabulary.

    `issuers` is the ContextBuilder's `{issuer_id: {"token": symbol, ...}}`; without it the canonical issuer registry
    names each token's issuer. A review job names that issuer, never the market's ticker (`underlying_id`): the evidence
    side accepts only canonical issuer IDs (#25, IDEA-049-D WR-D1)."""

    def __init__(self, *, job_validity_ms: int, job_max_attempts: int, plan_fn=risk_plan, issuers: dict | None = None):
        self.plan_fn, self.validity, self.attempts = plan_fn, job_validity_ms, job_max_attempts
        pairs = ([(i, m.get("token") if type(m) is dict else None) for i, m in issuers.items()] if issuers is not None
                 else [(e.issuer_id, e.token) for e in load_registry().entries])  # an unreadable registry refuses
        self.issuer_by_token = {}
        for issuer_id, token in pairs:
            if type(issuer_id) is not str or not issuer_id or type(token) is not str or token in self.issuer_by_token:
                raise ContractError("Each token needs exactly one issuer for review jobs")
            self.issuer_by_token[token] = issuer_id

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
            # The organiser's order amount is USDT spent for BUY, token quantity for SELL.
            # cash_units uses the planner's money scale; wallet USDT decimals are a separate execution concern.
            amount = (decimal_amount(intent["pay_units"], len(str(MONEY_SCALE)) - 1)
                      if intent["side"] == "BUY" else decimal_amount(intent["token_units"], intent["decimals"]))
            intents.append(dict(intent, decision_id=decision_id, expires_ms=expires, amount=amount))
        for delta in raw["reservation_deltas"]:
            if delta["side"] == "BUY":
                deltas.append({"intent_id": delta["intent_id"], "asset": "USDT", "units": delta["cash_units"]})
                deltas.append({"intent_id": delta["intent_id"], "asset": INCOMING + delta["symbol"],
                               "units": delta["token_units"]})
            else:
                deltas.append({"intent_id": delta["intent_id"], "asset": delta["symbol"],
                               "units": delta["token_units"]})
            if delta["bnb_units"]:
                deltas.append({"intent_id": delta["intent_id"], "asset": "BNB", "units": delta["bnb_units"]})
        jobs = self._jobs(snapshot, proposal_or_none, now_ms)
        return Document.from_dict(dict(raw, adapter=ADAPTER, intents=intents, reservation_deltas=deltas, jobs=jobs,
                                       reasons=sorted({r["reason"] for r in raw["rejections"]}),
                                       proposed_state={}))

    def _job(self, payload: dict, due_ms: int, priority: int) -> dict:
        """A job whose whole definition follows from its payload and due time, both covered by its ID: the store
        refuses a reused job ID with changed bytes, so a review planned again in a later round must be identical
        (IDEA-033 R15). Due times come from durable state, never from the planning round's clock."""
        job_id = "evidence:" + digest("larp.integration.review-job.v2", {"payload": payload, "due_ms": due_ms})
        return {"job_id": job_id, "lane": "evidence", "due_ms": due_ms, "valid_until_ms": due_ms + self.validity,
                "max_attempts": self.attempts, "priority": priority, "calendar_id": "UTC",
                "tzdata_version": "utc-only-no-tzdata", "missed": "catch_up", "payload": payload}

    def _jobs(self, snapshot, proposal, now_ms) -> list:
        context = snapshot.context.read()
        jobs = []
        for record in context.get("assessments", []):
            if record.get("due_reviews"):
                due = record.get("review_due_ms")
                jobs.append(self._job({"kind": "REASSESS_ISSUER", "issuer_id": record["issuer_id"],
                                       "reason": "STATEMENT_REVIEW_DUE", "state_version": record["state_version"],
                                       "statement_ids": sorted(record["due_reviews"])},
                                      due if type(due) is int else now_ms, 40))  # records predating review_due_ms
        if proposal is not None:
            quoted = {m["symbol"] for m in context.get("markets", [])}
            started = context.get("session_started_ms")
            for review in proposal.next_policy_state.data.read().get("reviews", []):
                issuer = self.issuer_by_token.get(review["symbol"])
                # A token without a registered issuer gets no review job: its ticker is not an issuer ID (fail closed).
                if review["symbol"] in quoted and issuer is not None:
                    jobs.append(self._job({"kind": "REASSESS_ISSUER", "issuer_id": issuer,
                                           "reason": review["reason"], "session": context["session_index"]},
                                          started if type(started) is int else now_ms, 50))
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

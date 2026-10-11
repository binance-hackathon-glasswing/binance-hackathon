"""Pure low-turnover candidate. DEVELOPMENT shadow is not live adoption.

Evidence arrives only as EvidenceContext.v1 (larp/integration/contract.py, IDEA-031): validated for
identity, version, time and hash, with typed rejections kept in the next policy state. What evidence
may do is the profile's configured authority (default SHADOW), never the evidence record itself.
"""

from dataclasses import replace
from datetime import timedelta
from fractions import Fraction

from larp.contracts import ContractError, Document, Proposal, Target, TargetKind
from larp.integration.contract import accept_for_strategy, authority
from .features import declared_weight, features
from .schema import fraction, instant, integer, markets, profile, value, equity
from .predicates import predicate_records, update_blocks


def decide(snapshot, state):
    if state != snapshot.policy_state:
        raise ContractError("Stale policy state")
    p = profile(snapshot)
    c = snapshot.context.read()
    now = snapshot.observed_at
    session = integer(c["session_index"])
    market = markets(snapshot, p)
    ledger = c["portfolio"]
    E = equity(ledger, market)
    if E <= 0:
        raise ContractError("No positive equity")
    data = state.data.read()
    lifecycle = dict(data.get("lifecycle", {}))
    blocked = dict(data.get("blocked", {}))
    finding_sessions = dict(data.get("finding_sessions", {}))
    registry = c.get("red_flag_predicates")
    classified = p.get("red_flag_policy") == "IDEA-035-B1"
    records = predicate_records(registry) if classified else {}
    if classified and Document.from_dict(registry).digest("RedFlagRegistry.v1") != p["predicate_registry_hash"]:
        raise ContractError("Predicate registry differs from the active profile")
    reviews, shadow, targets = [], [], []
    rights = authority(p)
    versions = dict(data.get("evidence_versions", {}))
    assessments, rejections = accept_for_strategy(c.get("assessments", []), snapshot, market, versions, p)
    for symbol, a in assessments.items():
        versions[symbol] = a["state_version"]
    terminal = now >= instant(p["flatten_start"])
    window_open = (instant(p["trade_after"]) <= now < instant(p["new_risk_end"])
                   and c["remaining_sessions"] >= p["minimum_remaining_sessions"])
    held = [s for s, pos in ledger["positions"].items() if pos["units"]]
    gross = sum((value(ledger["positions"][s]["units"], market[s]) / E for s in held), Fraction(0))
    candidates = []
    for symbol in snapshot.universe:
        units = ledger["positions"].get(symbol, {}).get("units", 0)
        m = market.get(symbol)
        old = lifecycle.get(symbol, {})
        last_review = old.get("last_review_session", session)
        if session < last_review:
            raise ContractError("Session clock moved backward")
        due = units > 0 and session - last_review >= 5
        if due:
            reviews.append({"symbol": symbol, "reason": "HORIZON_REASSESSMENT"})
        a = assessments.get(symbol)
        findings = [f for f in (a or {}).get("falsifier_findings", [])
                    if f.get("predicate_id") in p["falsifier_ids"]
                    and f.get("supported") is True and f.get("verifier_accepted") is True
                    and f.get("supporting_spans")]
        if classified:
            classified_findings = [f for f in findings if f["predicate_id"] in records]
            if a is not None:
                if any(type(f.get("finding_id")) is not str or not f["finding_id"] for f in classified_findings):
                    raise ContractError("Stable finding identity required for red-flag expiry")
                update_blocks(blocked, finding_sessions, symbol, classified_findings, session=session,
                              run_id=snapshot.run_id, registry=registry,
                              allow_resolution=a.get("review_complete") is True)
            elif blocked.get(symbol, {}).get("reason") == "CLASS_2_ENTRY_BLOCK":
                if session >= blocked[symbol]["expires_session"]:
                    blocked.pop(symbol)
        if not classified and a is not None and not findings and blocked.get(symbol, {}).get("reason") in (
                "VERIFIED_FALSIFIER", "MANDATORY_FALSIFIER_REDUCTION"):
            # The evidence state resolved the latch by its declared rule (correction/withdrawal of the source).
            blocked.pop(symbol)
            shadow.append({"symbol": symbol, "unblocked": "EVIDENCE_LATCH_RESOLVED"})
        if not classified and findings and rights["falsifier"] != "NONE":
            shadow.append({"symbol": symbol, "predicates": [f["predicate_id"] for f in findings],
                           "authority": rights["falsifier"]})
            if rights["falsifier"] == "DISCRETIONARY_EXIT":
                blocked[symbol] = {"reason": "VERIFIED_FALSIFIER", "run_id": snapshot.run_id}
            elif rights["falsifier"] == "MANDATORY_REDUCTION":
                # The reduction itself is a planner constraint (integration.contract.mandatory_reductions);
                # the policy only stops re-entry while the finding stands.
                blocked[symbol] = {"reason": "MANDATORY_FALSIFIER_REDUCTION", "run_id": snapshot.run_id}
        pending = (a or {}).get("statements_pending") or []
        if pending:
            shadow.append({"symbol": symbol, "statements_pending": len(pending), "authority": rights["statement"]})
        status = "HELD" if units else "UNBUILT"
        if terminal:
            targets.append(Target(symbol, TargetKind.EXIT, "TERMINAL_REQUIREMENT"))
            status = "FLAT_TERMINAL" if not units else "EXIT_REQUIRED"
        elif symbol in blocked:
            mandatory = blocked[symbol]["reason"] == "MANDATORY_FALSIFIER_REDUCTION"
            entry_only = blocked[symbol]["reason"] == "CLASS_2_ENTRY_BLOCK"
            targets.append(Target(symbol, TargetKind.EXIT if units and not mandatory and not entry_only
                                  else TargetKind.KEEP_QUANTITY,
                                  "CLASS_2_ENTRY_BLOCK" if entry_only else
                                  "MANDATORY_REDUCTION_BY_RISK" if mandatory else "BOUNDED_FALSIFIER"))
            status = "HELD_ENTRY_BLOCKED" if units and entry_only else "EXIT_REQUIRED" if units else "BLOCKED"
        elif m is None or not m.get("basis_verified"):
            targets.append(Target(symbol, TargetKind.KEEP_QUANTITY, "MISSING_MARKET_OR_BASIS"))
        elif p["baseline"] == "EQUAL_WEIGHT":
            # IDEA-037: no estimate, so no price-history features. Names are never sold on drift (the
            # planner's hard lines handle extremes). Only while gross is below the top-up threshold, a held
            # name below the equal weight is bought back up to it and unheld names are entry candidates.
            fresh_review = bool(a and a.get("review_complete") is True)
            if due and fresh_review:
                last_review = session
            weight = fraction(p["operating_name_weight"])
            below = gross < fraction(p["top_up_below_gross_weight"])
            gates = (window_open and (not p["assessment_required"] or fresh_review)
                     and not (rights["statement"] == "ENTRY_BLOCK" and pending))
            if units:
                if below and gates and value(units, m) < weight * (E - p["cost_reserve_units"]):
                    targets.append(Target(symbol, TargetKind.TARGET_WEIGHT, "TOP_UP_TO_EQUAL_WEIGHT", weight))
                else:
                    targets.append(Target(symbol, TargetKind.KEEP_QUANTITY,
                                          "REVIEW_PENDING" if due else "LOW_TURNOVER_HOLD"))
            else:
                previously_held = old.get("ever_held", False)
                entry_ok = gates and (not previously_held or fresh_review)
                if not entry_ok:
                    targets.append(Target(symbol, TargetKind.KEEP_QUANTITY, "ENTRY_OR_REENTRY_UNAVAILABLE"))
                elif not below:
                    targets.append(Target(symbol, TargetKind.KEEP_QUANTITY, "ABOVE_TOP_UP_THRESHOLD"))
                else:
                    candidates.append((m.get("measured_roundtrip_bps", 10**9), symbol, weight))
                if previously_held:
                    status = "CASH_REVIEW"
        else:
            series = c.get("series", {}).get(symbol)
            f = (features(Document.from_dict(series), cutoff=now, expected_entity=m["underlying_id"],
                          max_age_seconds=p["feature_age_seconds"],
                          expected_instrument="TOKEN" if p.get("series_kind") == "TOKEN" else "UNDERLYING_SHARE",
                          expected_token=m["token_id"] if p.get("series_kind") == "TOKEN" else None) if series else
                 Document.from_dict({"status": "MISSING"}))
            fresh_review = bool(a and a.get("review_complete") is True)
            if due and fresh_review:
                last_review = session
            if f.read()["status"] != "VALID":
                targets.append(Target(symbol, TargetKind.KEEP_QUANTITY, "INSUFFICIENT_FEATURES"))
            elif units:
                momentum = f.read()["momentum_5"]
                mom = Fraction(momentum[0], momentum[1])
                desired = min(declared_weight(f), fraction(p["operating_name_weight"]))
                current = value(units, m) / E
                if p["baseline"] == "PRICE_MOMENTUM" and mom < -Fraction(p["price_threshold_bps"], 10000):
                    targets.append(Target(symbol, TargetKind.EXIT, "PRICE_REASSESSMENT_EXIT"))
                elif due and fresh_review and abs(desired - current) > fraction(p["rebalance_band"]):
                    targets.append(Target(symbol, TargetKind.TARGET_WEIGHT, "REVIEW_RESIZE", desired))
                else:
                    targets.append(Target(symbol, TargetKind.KEEP_QUANTITY,
                                          "REVIEW_PENDING" if due else "LOW_TURNOVER_HOLD"))
            else:
                previously_held = old.get("ever_held", False)
                entry_ok = (window_open
                            and (not previously_held or fresh_review)
                            and (not p["assessment_required"] or fresh_review)
                            and not (rights["statement"] == "ENTRY_BLOCK" and pending))
                if p["baseline"] == "PRICE_MOMENTUM":
                    momentum = f.read()["momentum_5"]
                    entry_ok &= Fraction(momentum[0], momentum[1]) > Fraction(p["price_threshold_bps"], 10000)
                if entry_ok:
                    candidates.append((m.get("measured_roundtrip_bps", 10**9), symbol,
                                       min(declared_weight(f), fraction(p["operating_name_weight"]))))
                else:
                    targets.append(Target(symbol, TargetKind.KEEP_QUANTITY, "ENTRY_OR_REENTRY_UNAVAILABLE"))
                if previously_held:
                    status = "CASH_REVIEW"
        lifecycle[symbol] = {"status": status, "last_review_session": last_review,
                             "ever_held": bool(units or old.get("ever_held")),
                             "observed_session": session}
    gross_budget = min(fraction(p["operating_gross_weight"]), fraction(p["regime_gross_weight"]))
    slots = max(0, 4 - len(held))
    for _, symbol, weight in sorted(candidates):
        allowed = min(weight, max(Fraction(0), gross_budget - gross)) if slots else Fraction(0)
        if allowed:
            targets.append(Target(symbol, TargetKind.TARGET_WEIGHT, "UNVALIDATED_BASELINE_ENTRY", allowed))
            slots -= 1
            gross += allowed
        else:
            targets.append(Target(symbol, TargetKind.KEEP_QUANTITY, "NO_PORTFOLIO_CAPACITY"))
    following = replace(state, version=state.version + 1, data=Document.from_dict({**data,
        "lifecycle": lifecycle, "blocked": blocked, "reviews": reviews,
        "shadow_findings": shadow, "evidence_mode": p["evidence_mode"], "evidence_authority": rights,
        "evidence_versions": versions, "evidence_rejections": rejections,
        **({"finding_sessions": finding_sessions} if classified else {})}))
    return Proposal(snapshot.snapshot_id, state.policy_id, now + timedelta(seconds=p["proposal_seconds"]),
                    tuple(targets), following)

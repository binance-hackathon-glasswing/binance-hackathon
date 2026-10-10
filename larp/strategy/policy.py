"""Pure low-turnover candidate. DEVELOPMENT shadow is not live adoption."""

from dataclasses import replace
from datetime import timedelta
from fractions import Fraction

from larp.contracts import ContractError, Document, Proposal, Target, TargetKind
from .features import declared_weight, features
from .assessments import consume
from .schema import fraction, instant, integer, markets, profile, value, equity


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
    reviews, shadow, targets = [], [], []
    assessments, assessment_diagnostics = consume(snapshot, state, market, p["falsifier_ids"])
    terminal = now >= instant(p["flatten_start"])
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
        findings = (a or {}).get("findings", [])
        if findings:
            shadow.append({"symbol": symbol, "predicates": [f["predicate_id"] for f in findings]})
            if p["evidence_mode"] == "BOUNDED_FALSIFIER":
                blocked[symbol] = {"reason": "VERIFIED_FALSIFIER", "run_id": snapshot.run_id}
        status = "HELD" if units else "UNBUILT"
        if terminal:
            targets.append(Target(symbol, TargetKind.EXIT, "TERMINAL_REQUIREMENT"))
            status = "FLAT_TERMINAL" if not units else "EXIT_REQUIRED"
        elif symbol in blocked:
            targets.append(Target(symbol, TargetKind.EXIT if units else TargetKind.KEEP_QUANTITY,
                                  "BOUNDED_FALSIFIER"))
            status = "EXIT_REQUIRED" if units else "BLOCKED"
        elif m is None or not m.get("basis_verified"):
            targets.append(Target(symbol, TargetKind.KEEP_QUANTITY, "MISSING_MARKET_OR_BASIS"))
        else:
            series = c.get("series", {}).get(symbol)
            f = (features(Document.from_dict(series), cutoff=now, expected_entity=m["underlying_id"],
                          max_age_seconds=p["feature_age_seconds"]) if series else
                 Document.from_dict({"status": "MISSING"}))
            fresh_review = bool(a and a["fresh_review"])
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
                entry_ok = (instant(p["trade_after"]) <= now < instant(p["new_risk_end"])
                            and c["remaining_sessions"] >= p["minimum_remaining_sessions"]
                            and (not previously_held or fresh_review)
                            and (not p["assessment_required"] or fresh_review))
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
    held = [s for s, pos in ledger["positions"].items() if pos["units"]]
    gross = sum((value(ledger["positions"][s]["units"], market[s]) / E for s in held), Fraction(0))
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
        "shadow_findings": shadow, "assessment_diagnostics": assessment_diagnostics,
        "evidence_mode": p["evidence_mode"]}))
    return Proposal(snapshot.snapshot_id, state.policy_id, now + timedelta(seconds=p["proposal_seconds"]),
                    tuple(targets), following)

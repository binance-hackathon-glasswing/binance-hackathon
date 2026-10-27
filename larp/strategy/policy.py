"""Pure low-turnover candidate. DEVELOPMENT shadow is not live adoption.

Evidence arrives only as EvidenceContext.v1 (larp/integration/contract.py, IDEA-031): validated for
identity, version, time and hash, with typed rejections kept in the next policy state. What evidence
may do is the profile's configured authority (default SHADOW), never the evidence record itself.
"""

from dataclasses import replace
from datetime import timedelta
from fractions import Fraction

from larp.contracts import ContractError, Document, Proposal, Target, TargetKind
from larp.integration.contract import accept_for_strategy, authority, red_flag_directives
from .features import declared_weight, features
from .schema import fraction, instant, integer, markets, profile, ratio, value, equity, stock_capital_scale
from . import s1 as s1_plan
from . import scheduled_flatten, self_check
from .rehearsal_sizing import name_target as rehearsal_name_target
from .predicates import predicate_records, update_blocks, update_directive_blocks


def _cost_rank(market: dict) -> int:
    # Outside LIVE a cost may be explicitly unavailable (None); it ranks after every measured cost.
    cost = market.get("measured_roundtrip_bps")
    return 10**9 if cost is None else cost


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
    published = classified and "red_flag_authority" in p
    records = predicate_records(registry) if classified and not published else {}
    if classified and not published and Document.from_dict(registry).digest("RedFlagRegistry.v1") != p["predicate_registry_hash"]:
        raise ContractError("Predicate registry differs from the active profile")
    reviews, shadow, targets = [], [], []
    rights = authority(p)
    versions = dict(data.get("evidence_versions", {}))
    assessments, rejections = accept_for_strategy(c.get("assessments", []), snapshot, market, versions, p)
    for symbol, a in assessments.items():
        versions[symbol] = a["state_version"]
    terminal = now >= instant(p["flatten_start"])
    # IDEA-092 (S3): after the scheduled sell-all is DONE, S2 rebuilds its book; names held before may be bought again.
    fresh_book = scheduled_flatten.state(p, ledger.get("risk"), ledger, now) == "DONE"
    # IDEA-093 SC (GAP-74): the activation self-check's one BUY before trade_after, then FS1 as usual.
    check = self_check.config(p)
    check_phase = self_check.phase(p, ledger.get("risk"), ledger, now)
    window_open = (instant(p["trade_after"]) <= now < instant(p["new_risk_end"])
                   and c["remaining_sessions"] >= p["minimum_remaining_sessions"]
                   and not self_check.temp(p))  # IDEA-110: the temp policy buys only its self-check
    held = [s for s, pos in ledger["positions"].items() if pos["units"]]
    gross = sum((value(ledger["positions"][s]["units"], market[s]) / E for s in held), Fraction(0))
    candidates = []
    s1 = None
    if p["baseline"] == s1_plan.BASELINE:
        # IDEA-076: target gross = min(trend level, limiter level); the planner applies the loss ladder on top.
        cfg = s1_plan.config(p)
        before = dict(data.get("s1", {}))
        tokens = {sym: m["token_id"] for sym, m in market.items() if m is not None}
        series = {sym: v for sym, v in (c.get("series") or {}).items()
                  if type(v) is dict and (sym not in tokens or v.get("token_id") == tokens[sym])}
        trend = s1_plan.evaluate_trend(series, cutoff=now, cfg=cfg, previous_state=before.get("trend_state"),
                                       last_evaluated=before.get("trend_evaluated_session"),
                                       max_age_seconds=p["feature_age_seconds"])
        # An absent evidence input stays None: in DETERMINISTIC mode that session is not healthy (IDEA-076 L09).
        produced = c.get('exposure_input')
        complete = (produced.get('complete') is True and c.get('assessment_available') is not False
                    if type(produced) is dict else True)
        limiter, limiter_record = s1_plan.limiter_step(before.get("limiter"), session=session, cfg=cfg,
                                                       evidence=c.get("exposure_evidence") if produced is not None or c.get("assessment_available") is not False else None,
                                                       assessment=c.get("exposure_assessment") if c.get("assessment_available") is not False else None,
                                                       input_complete=complete)
        level = s1_plan.level_fraction(cfg, trend["state"], limiter["level"])
        applied = before.get("applied_target")
        # A level change ends per name (IDEA-076 R1): only the names still listed are moved to the new target, so
        # a name whose buy keeps being refused cannot hold the rest of the book in rebalance (no sale on drift).
        # `True` is the whole-book flag of a state written before per-name tracking.
        still = before.get("rebalance")
        rebalance = (set(snapshot.universe) if applied is None or fraction(applied) != level or still is True
                     else set(still) & set(snapshot.universe) if type(still) is list else set())
        s1 = dict(cfg=cfg, level=level, trend=trend, limiter=limiter, limiter_record=limiter_record,
                  rebalance=rebalance, pending=set(), seen=set(), capital_scale=stock_capital_scale(p, ledger, E))
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
        if published:
            directives = red_flag_directives(a, p) if a is not None else []
            shadow.append({"symbol": symbol, "red_flag_directives": directives,
                           "statements_pending": len((a or {}).get("statements_pending", []))})
            update_directive_blocks(blocked, finding_sessions, symbol, directives, session=session,
                run_id=snapshot.run_id, allow_resolution=bool(a and (a.get("review_complete") is True
                    or a.get("review_complete_excluding_timed_blocks") is True)))
        if classified and not published:
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
        elif symbol in blocked and not (s1 is not None
                and blocked[symbol]["reason"] == "CLASS_2_ENTRY_BLOCK"
                and m is not None and m.get("basis_verified")):
            mandatory = blocked[symbol]["reason"] == "MANDATORY_FALSIFIER_REDUCTION"
            entry_only = blocked[symbol]["reason"] == "CLASS_2_ENTRY_BLOCK"
            targets.append(Target(symbol, TargetKind.EXIT if units and not mandatory and not entry_only
                                  else TargetKind.KEEP_QUANTITY,
                                  "CLASS_2_ENTRY_BLOCK" if entry_only else
                                  "MANDATORY_REDUCTION_BY_RISK" if mandatory else
                                  "CLASS_1_EXIT" if blocked[symbol]["reason"] == "CLASS_1_EXIT" else "BOUNDED_FALSIFIER"))
            status = "HELD_ENTRY_BLOCKED" if units and entry_only else "EXIT_REQUIRED" if units else "BLOCKED"
        elif m is None or not m.get("basis_verified"):
            targets.append(Target(symbol, TargetKind.KEEP_QUANTITY, "MISSING_MARKET_OR_BASIS"))
        elif p["baseline"] == "EQUAL_WEIGHT":
            # IDEA-037: no estimate, so no price-history features. Names are never sold on drift (the
            # planner's hard lines handle extremes). Only while gross is below the top-up threshold, a held
            # name below the equal weight is bought back up to it and unheld names are entry candidates.
            fresh_review = bool(a and (a.get("review_complete") is True or
                (published and symbol not in blocked and a.get("review_complete_excluding_timed_blocks") is True)))
            if due and fresh_review:
                last_review = session
            weight = fraction(p["operating_name_weight"])
            below = gross < fraction(p["top_up_below_gross_weight"])
            gates = (window_open and (p.get("mode") != "LIVE" or type(m.get("measured_roundtrip_bps")) is int)
                     and (not p["assessment_required"] or fresh_review)
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
                    candidates.append((_cost_rank(m), symbol, weight))
                if previously_held:
                    status = "CASH_REVIEW"
        elif s1 is not None:
            # IDEA-075 §5.2: a level change moves every eligible name to level x w; otherwise only a top-up below
            # level - band buys, and nothing is sold on drift. Sells toward a lower level need no entry gates.
            fresh_review = bool(a and (a.get("review_complete") is True or
                (published and symbol not in blocked and a.get("review_complete_excluding_timed_blocks") is True)))
            if due and fresh_review:
                last_review = session
            want = s1["level"] * s1["cfg"]["weights"][symbol] * s1['capital_scale']
            want = rehearsal_name_target(p, s1['cfg'], want,
                level=s1['level'] * s1['capital_scale'], capital_scale=s1['capital_scale'],
                safe_equity=max(0, E - p['cost_reserve_units']),
                enabled=not ledger.get('risk', {}).get('deep_cut', False))
            gap = want * (E - p["cost_reserve_units"]) - value(units, m)
            gates = (symbol not in blocked and window_open and (p.get("mode") != "LIVE" or type(m.get("measured_roundtrip_bps")) is int)
                     and (not p["assessment_required"] or fresh_review)
                     and not (rights["statement"] == "ENTRY_BLOCK" and pending)
                     and (units or not old.get("ever_held", False) or fresh_review or fresh_book
                          or (check is not None and symbol == check["symbol"] and check_phase == "DONE"
                              and not old.get("self_check_cleared"))))
            step = p["minimum_trade_units"]
            check_buy = (check is not None and symbol == check["symbol"] and check_phase == "BUY" and not units
                         and symbol not in blocked
                         and (p.get("mode") != "LIVE" or type(m.get("measured_roundtrip_bps")) is int))
            s1["seen"].add(symbol)
            # RV01-3: reductions have an exact-quote cost gate; an entry-size floor must not silently
            # complete a pending cut. Keep the obligation until fills reach target or the level changes.
            costed_cut = p.get('s1_reduction_cost_cap_bps') == 50 and gap < 0
            if check_buy:
                targets.append(Target(symbol, TargetKind.TARGET_WEIGHT, "ACTIVATION_SELF_CHECK_BUY",
                                      Fraction(check["pay_units"], max(1, E - p["cost_reserve_units"]))))
            elif symbol in s1["rebalance"] and (costed_cut or gap <= -step or (gap >= step and gates)):
                targets.append(Target(symbol, TargetKind.TARGET_WEIGHT, "S1_LEVEL_CHANGE", want))
                s1["pending"].add(symbol)
            elif (symbol not in s1["rebalance"] and gates
                  and gross < (s1["level"] - s1["cfg"]["band"]) * s1['capital_scale']
                  and gap >= step):
                targets.append(Target(symbol, TargetKind.TARGET_WEIGHT, "S1_TOP_UP", want))
            else:
                targets.append(Target(symbol, TargetKind.KEEP_QUANTITY,
                                      "REVIEW_PENDING" if due else "LOW_TURNOVER_HOLD"))
            if symbol in s1["rebalance"] and gap >= step and not gates:
                s1["pending"].add(symbol)  # keep an unfilled buy pending while entry is blocked
            if symbol in blocked:
                status = "HELD_ENTRY_BLOCKED" if units else "BLOCKED"
            elif not units and old.get("ever_held", False):
                status = "CASH_REVIEW"
        else:
            series = c.get("series", {}).get(symbol)
            f = (features(Document.from_dict(series), cutoff=now, expected_entity=m["underlying_id"],
                          max_age_seconds=p["feature_age_seconds"],
                          expected_instrument="TOKEN" if p.get("series_kind") == "TOKEN" else "UNDERLYING_SHARE",
                          expected_token=m["token_id"] if p.get("series_kind") == "TOKEN" else None) if series else
                 Document.from_dict({"status": "MISSING"}))
            fresh_review = bool(a and (a.get("review_complete") is True or
                (published and symbol not in blocked and a.get("review_complete_excluding_timed_blocks") is True)))
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
                    candidates.append((_cost_rank(m), symbol,
                                       min(declared_weight(f), fraction(p["operating_name_weight"]))))
                else:
                    targets.append(Target(symbol, TargetKind.KEEP_QUANTITY, "ENTRY_OR_REENTRY_UNAVAILABLE"))
                if previously_held:
                    status = "CASH_REVIEW"
        lifecycle[symbol] = {"status": status, "last_review_session": last_review,
                             "ever_held": bool(units or old.get("ever_held")),
                             "observed_session": session}
        if check is not None and symbol == check["symbol"]:
            # SC: holding only the self-check does not block the scored run's entry; cleared once, then normal.
            if old.get("self_check_cleared"):
                lifecycle[symbol]["self_check_cleared"] = True
            elif check_phase == "DONE" and not units:
                lifecycle[symbol].update(ever_held=False, self_check_cleared=True)
    gross_budget = (min(fraction(p["operating_gross_weight"]), fraction(p["regime_gross_weight"]))
                    if candidates else Fraction(0))
    slots = max(0, 4 - len(held))
    for _, symbol, weight in sorted(candidates):
        allowed = min(weight, max(Fraction(0), gross_budget - gross)) if slots else Fraction(0)
        if allowed:
            targets.append(Target(symbol, TargetKind.TARGET_WEIGHT, "UNVALIDATED_BASELINE_ENTRY", allowed))
            slots -= 1
            gross += allowed
        else:
            targets.append(Target(symbol, TargetKind.KEEP_QUANTITY, "NO_PORTFOLIO_CAPACITY"))
    if s1 is not None:
        if 's5_entry_lot_units' in p:
            # Opening lots must form a valid proposal even if gas has little/no marked value:
            # five 19-USDT targets cannot be proposed against an 81-USDT cash-only wallet.
            safe = max(0, E - p['cost_reserve_units'])
            capacity = max(Fraction(0), s1['level'] * s1['capital_scale'] * safe
                - sum((value(ledger['positions'][s]['units'], market[s]) for s in held), Fraction(0)))
            openings = []
            for index, target in enumerate(targets):
                if target.kind is TargetKind.TARGET_WEIGHT:
                    gap = target.weight * safe - value(ledger['positions'][target.symbol]['units'], market[target.symbol])
                    if gap > 0:
                        openings.append((-gap, target.symbol, index))
            for negative_gap, symbol, index in sorted(openings):
                gap = -negative_gap
                if gap <= capacity:
                    capacity -= gap
                else:
                    targets[index] = Target(symbol, TargetKind.KEEP_QUANTITY, 'NO_PORTFOLIO_CAPACITY')
        # Names this round did not reach (blocked, unmarked) keep their place in the rebalance.
        s1["pending"] = sorted(s1["pending"] | (s1["rebalance"] - s1["seen"]))
    following = replace(state, version=state.version + 1, data=Document.from_dict({**data,
        "lifecycle": lifecycle, "blocked": blocked, "reviews": reviews,
        "shadow_findings": shadow, "evidence_mode": p["evidence_mode"], "evidence_authority": rights,
        "evidence_versions": versions, "evidence_rejections": rejections,
        **({"finding_sessions": finding_sessions} if classified else {}),
        **({"s1": {"trend_state": s1["trend"]["state"], "trend_evaluated_session": s1["trend"]["evaluated_session"],
                   "limiter": s1["limiter"], "applied_target": ratio(s1["level"]), "rebalance": s1["pending"]},
            "s1_round": {"target_gross": ratio(s1["level"]), "trend": s1["trend"], "limiter": s1["limiter_record"],
                         **({'stock_capital_scale': ratio(s1['capital_scale']),
                             'fundable_target_gross': ratio(s1['level'] * s1['capital_scale'])}
                            if p.get('s1_capital_basis') == 'EXCLUDE_GAS' else {}),
                         "rebalance": s1["pending"]}} if s1 is not None else {})}))
    return Proposal(snapshot.snapshot_id, state.policy_id, now + timedelta(seconds=p["proposal_seconds"]),
                    tuple(targets), following)

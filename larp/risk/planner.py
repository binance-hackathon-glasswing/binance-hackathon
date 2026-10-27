"""Independent constraints and staged exact-size quoting; requests, not authority.

One immediate child intent per wallet simplifies nonce ownership. Parent reduction
requirements retain every residual; re-plan on observed settlement, never assumed
sell proceeds. The runtime stores requests atomically and execution revalidates.
"""

from fractions import Fraction

from larp.contracts import ContractError, Document, TargetKind, validate_proposal
from larp.strategy.schema import (ceil, discretionary_cost_limit, equity, floor, fraction, instant, integer,
                                  markets, profile, ratio, value, stock_capital_scale)
from .accounting import update_risk
from .gas import plan_top_up
from larp.strategy import s1 as s1_plan
from larp.strategy import execution_bounds
from larp.strategy import scheduled_flatten, self_check
from larp.strategy.rehearsal_sizing import name_target as rehearsal_name_target


def _request(symbol, side, pay_units, m, mandatory):
    return {"schema": "MarketRequest.v1", "symbol": symbol, "side": side,
            "amount_kind": "EXACT_IN", "pay_asset": "USDT" if side == "BUY" else symbol,
            "pay_units": pay_units, "pay_decimals": 6 if side == "BUY" else m["decimals"],
            "mandatory": mandatory}


EXIT_SPLIT_HEADROOM_BPS = 100


def exit_parts(value_units, cap_units):
    """Balanced child count for a mandatory exit worth `value_units` (LD10-P03 D1).

    Each child stays at most cap/1.01 at the valuation used, so a quote slightly above
    the mark still fits the cap; a split never leaves a residual below cap/2.02."""
    if (type(value_units) not in (int, Fraction) or value_units < 0
            or type(cap_units) is not int or cap_units <= 0):
        raise ValueError("Exit split needs a non-negative value and a positive cap")
    return max(1, ceil(Fraction(value_units) * (10000 + EXIT_SPLIT_HEADROOM_BPS) / (10000 * cap_units)))


def _quote_at_cap(m, side, pay_units, p, now, target_units, mandatory=False):
    """Walk observed smaller exact-in quotes; otherwise request the next size."""
    rejections = []
    quotes = m.get("quotes", [])
    if type(quotes) is not list or any(type(q) is not dict for q in quotes):
        return None, None, ["QUOTE_COLLECTION_INVALID"], "BLOCKED_QUOTE"
    asset = "USDT" if side == "BUY" else m["symbol"]
    for _ in range(len(quotes) + 1):
        matches = [x for x in quotes if x.get("side") == side
                   and x.get("pay_asset") == asset and x.get("pay_units") == pay_units
                   and x.get("amount_kind") == "EXACT_IN"]
        if len(matches) > 1:
            return None, None, rejections + ["QUOTE_COLLECTION_AMBIGUOUS"], "BLOCKED_QUOTE"
        quote = matches[0] if matches else None
        if quote is None:
            return None, pay_units, rejections, "REQUOTE_REQUIRED" if rejections else "PENDING"
        try:
            valid = (quote.get("route_valid") is True and type(quote["quote_id"]) is str and bool(quote["quote_id"])
                     and instant(quote["available_at"]) <= now
                     and 0 <= (now - instant(quote["observed_at"])).total_seconds() <= p["quote_age_seconds"]
                     and now < instant(quote["expires_at"])
                     and integer(quote["slippage_bps"]) <= p["slippage_bps"]
                     and (mandatory or integer(quote["impact_bps"]) <= p["impact_bps"])
                     and (p.get("mode") != "LIVE" or quote.get("origin") == "WEB3_OPEN_API"))
            cash, fee, gas, q, minimum = [integer(quote[k]) for k in
                ("cash_units", "fee_units", "gas_bnb_units", "token_units", "min_receive_units")]
            valid &= (cash == pay_units and 0 < minimum <= q) if side == "BUY" else (q == pay_units and minimum <= cash)
            if "expected_gas_bnb_units" in quote:
                # IDEA-088: an expected fee inside the reserved gas; only the entry cost uses it.
                valid &= 0 < integer(quote["expected_gas_bnb_units"]) <= gas
            if p.get("mode") == "LIVE":
                output = q if side == "BUY" else cash
                valid &= (output > 0 and minimum > 0
                          and minimum >= floor(Fraction(output * (10000 - p["slippage_bps"]), 10000)))
        except (KeyError, ContractError, TypeError):
            valid = False
        if not valid:
            return None, None, rejections + ["QUOTE_ROUTE_OR_SLIPPAGE"], "BLOCKED_QUOTE"
        if side == "BUY" and q > target_units:
            smaller = min(pay_units - 1, floor(Fraction(pay_units * target_units, q)))
            rejections.append("BUY_RECEIVE_TARGET_REQUOTE")
        elif cash + fee <= p["per_trade_cap_units"]:
            return quote, None, rejections, "PENDING"
        elif side == "SELL" and mandatory:
            # A cap-ratio resize would leave an arbitrarily small, possibly unroutable residual.
            smaller = min(pay_units - 1, pay_units // exit_parts(cash + fee, p["per_trade_cap_units"]))
            rejections.append("EXECUTABLE_TRADE_CAP")
        else:
            smaller = min(pay_units - 1, floor(Fraction(pay_units * p["per_trade_cap_units"], cash + fee)))
            rejections.append("EXECUTABLE_TRADE_CAP")
        if smaller <= 0:
            return None, None, rejections, "DUST_OR_UNEXECUTABLE"
        pay_units = smaller
    raise ContractError("Nondecreasing re-quote chain")


def _class_1_latches(state):
    """Names with a CLASS_1_EXIT latch in the persisted policy state (#57, WR15).

    The policy alone sets and clears latches (IDEA-035, A8); the planner only reads the committed state, so
    the exit holds without a proposal or fresh evidence. A resolution decided this round applies next round."""
    blocked = state.data.read().get("blocked", {})
    if type(blocked) is not dict or any(type(b) is not dict or type(b.get("reason")) is not str
                                        for b in blocked.values()):
        raise ContractError("Persisted policy latches must be objects")
    return {symbol for symbol, b in blocked.items() if b["reason"] == "CLASS_1_EXIT"}


def plan(snapshot, proposal_or_none):
    c, now = snapshot.context.read(), snapshot.observed_at
    result = {"schema": "PlanResult.v1", "snapshot_id": snapshot.snapshot_id,
              "intents": [], "reservation_deltas": [], "requirements": [],
              "quote_requests": [], "rejections": [], "clamps": [],
              "next_policy_state": None, "risk_state": None,
              "authorization": "ATOMIC_COMMIT_AND_FRESH_EXECUTION_CHECKS_REQUIRED"}
    try:
        p = profile(snapshot)
        ledger = c["portfolio"]
        if (type(ledger) is not dict or type(ledger.get("positions")) is not dict
                or type(ledger.get("reservations")) is not dict
                or any(type(pos) is not dict for pos in ledger["positions"].values())
                or any(type(res) is not dict for res in ledger["reservations"].values())):
            raise ContractError("Portfolio positions and reservations must be objects")
        latched = _class_1_latches(snapshot.policy_state)
        invalid = {}
        market = markets(snapshot, p, invalid)
        # IDEA-055 PR 4: a held symbol whose mark jumped waits for a balance check. Until then it is not traded,
        # it is valued at the lower of its marks, and the loss stops are not evaluated (a split moves the price
        # before the balance check sees the new token count).
        hold = c.get("price_jump_hold") or {}
        if type(hold) is not dict or any(type(v) is not int or v <= 0 for v in hold.values()):
            raise ContractError("Price-jump holds must map symbols to positive prices")
        jumped = sorted(s for s in hold if type(ledger["positions"].get(s)) is dict
                        and ledger["positions"][s].get("units"))
        for symbol in jumped:
            if market.get(symbol) is not None:
                market[symbol] = dict(market[symbol], price_units=min(market[symbol]["price_units"], hold[symbol]))
        unvalued = sorted({s for s, pos in ledger["positions"].items()
                           if pos["units"] and market.get(s) is None}
                          | {v["symbol"] for v in ledger["reservations"].values()
                             if v["side"] == "BUY" and v.get("kind") != "GAS_TOP_UP"
                             and v.get("symbol") != "BNB" and market.get(v["symbol"]) is None})
        E = equity(ledger, market, allow_missing=True)
        recover = (p.get('run_halt_recovery_bps') == 500
                   and all(c.get('health', {}).get(k) is True for k in (
                       'integrity_ok', 'journal_ok', 'ownership_ok', 'clock_ok', 'new_spending_ok', 'balances_ok'))
                   and not ledger['reservations'] and not ledger.get('unreconciled_outcomes')
                   and not ledger.get('accounting_status'))
        # Incomplete valuation is not a loss observation. Preserve latches/peak;
        # block buys and use only the disclosed lower bound for healthy-name trims.
        risk_ledger = (ledger if unvalued or jumped else
                       update_risk(Document.from_dict(ledger), now=now, equity_units=E,
                                   recover_run_halt=recover).read())
        r = risk_ledger["risk"]
        result["risk_state"] = r
        if jumped:
            result["loss_stops_deferred"] = jumped
        result.update(valuation_status="LOWER_BOUND" if unvalued else "COMPLETE",
                      risk_equity_lower_bound_units=E, unvalued_symbols=unvalued)
        # One bad row makes only its own symbol unusable; it is recorded, never silently dropped (#45).
        result["rejections"].extend({"reason": "INVALID_MARKET_ROW", "symbol": s, "detail": invalid[s]}
                                    for s in sorted(invalid))
        if unvalued:
            result["rejections"].append({"reason": "PARTIAL_VALUATION_NEW_RISK_BLOCKED", "symbols": unvalued})
    except (KeyError, TypeError, ContractError, ValueError) as exc:
        # Invalid valuation is explicit; terminal holdings remain outstanding.
        result["rejections"].append({"reason": "INVALID_REQUIRED_INPUT", "detail": str(exc)})
        portfolio = c.get("portfolio")
        positions = portfolio.get("positions") if type(portfolio) is dict else None
        for symbol, pos in (positions.items() if type(positions) is dict else ()):
            if type(pos) is dict and type(pos.get("units")) is int and pos["units"] > 0:
                result["requirements"].append({"symbol": symbol, "status": "BLOCKED_INPUT",
                                               "held_units": pos["units"],
                                               "reason": "RISK_REEVALUATION_REQUIRED"})
        return Document.from_dict(result)
    targets = {}
    if proposal_or_none is not None:
        try:
            targets = {t.symbol: t for t in validate_proposal(snapshot, proposal_or_none, now=now)}
            result["next_policy_state"] = proposal_or_none.next_policy_state.record()
        except (ContractError, TypeError, AttributeError) as exc:
            result["rejections"].append({"reason": "INVALID_POLICY", "detail": str(exc)})
    else:
        result["rejections"].append({"reason": "NO_POLICY_PROPOSAL"})
    terminal = now >= instant(p["flatten_start"])
    cost_reserve = p["cost_reserve_units"]  # USDT cushion: capital, sizing and mandatory post-cost bounds
    cost_limit = discretionary_cost_limit(p)
    safe_equity = max(0, E - cost_reserve)
    # IDEA-076 (S1): its top level, five names, its hard name line and no gross trim line except the 12% deep cut
    # replace the proposal's 80% / four-name / 20% limits, which bind every other baseline unchanged.
    s1 = s1_plan.config(p) if p["baseline"] == s1_plan.BASELINE else None
    capital_scale = stock_capital_scale(p, ledger, E) if s1 else Fraction(1)
    s1_level = None
    if s1:
        # A hard-line HOLD-round trim still goes to the accepted reduced level, not always the high level.
        accepted_state = result["next_policy_state"] or snapshot.policy_state.record()
        applied = accepted_state["data"].get("s1", {}).get("applied_target")
        s1_level = min(s1["high"], fraction(applied)) if applied is not None else s1["high"]
        if s1_level <= 0:
            raise ContractError("S1 applied target must be positive")
        s1_level *= capital_scale
    max_positions = len(snapshot.universe) if s1 else 4
    gross_limit = s1["high"] * capital_scale if s1 else min(Fraction(4, 5), fraction(p["regime_gross_weight"]))
    if r["deep_cut"]:
        gross_limit = min(gross_limit, Fraction(2, 5))
    # IDEA-037: optional hard lines; drift between the cap and the line is held, not trimmed. The deep
    # drawdown cut always trims at its own limit. Trims still go back to the operating cap.
    hard_name = s1["hard"] if s1 else fraction(p.get("hard_name_weight", [1, 5]))
    if s1:
        trim_gross = gross_limit if r["deep_cut"] else Fraction(2)  # S1 has no gross line (IDEA-075 §5.2)
    else:
        trim_gross = (gross_limit if r["deep_cut"] or "hard_gross_weight" not in p
                      else max(gross_limit, fraction(p["hard_gross_weight"])))
    positions = ledger["positions"]
    held = {s: pos["units"] for s, pos in positions.items() if pos["units"]}
    # IDEA-092 (S3): from the scheduled time every held name is sold before any buy; DONE is committed with the risk state.
    scheduled = scheduled_flatten.state(p, r, ledger, now)
    if scheduled == "DONE":
        r["scheduled_flatten"] = "DONE"
    interim = scheduled == "PENDING"
    # IDEA-093 SC (GAP-74): the activation self-check; BOUGHT/DONE/EXPIRED are committed with the risk state.
    check = self_check.config(p)
    check_phase = self_check.phase(p, r, ledger, now)
    if self_check.recorded(check_phase) is not None:
        r[self_check.KEY] = self_check.recorded(check_phase)
    pending_buy = {}
    reserved_cash = reserved_bnb = 0
    for reservation in ledger["reservations"].values():
        reserved_cash += integer(reservation["cash_units"])
        reserved_bnb += integer(reservation["bnb_units"])
        if reservation["side"] == "BUY" and reservation.get("symbol") != "BNB":
            s = reservation["symbol"]
            pending_buy[s] = pending_buy.get(s, 0) + integer(reservation["token_units"])
    gross = sum((value(q + pending_buy.get(s, 0), market[s]) for s, q in held.items()
                 if market.get(s) is not None), Fraction(0))
    gross += sum((value(q, market[s]) for s, q in pending_buy.items()
                  if s not in held and market.get(s) is not None), Fraction(0))
    result["worst_case_gross_units"] = None if unvalued else ceil(gross)
    result["known_gross_units"] = ceil(gross)
    result["available_cash_units"] = max(0, ledger["cash_units"] - reserved_cash)
    # Hard lines start an obligation; crossing back below the trigger does not complete it.
    # This state is committed even on blocked rounds and restored independently of policy output.
    trim_state = r.get("cap_trims", {})
    durable_trims = s1 is not None or "hard_name_weight" in p or "hard_gross_weight" in p or "cap_trims" in r
    name_trims = set(trim_state.get("names", [])) & set(held)
    gross_trim = bool(trim_state.get("gross", False)) or gross > safe_equity * trim_gross
    gross_shares = dict(trim_state.get("gross_shares", {}))
    if not unvalued and (gross <= safe_equity * gross_limit or (s1 and not r["deep_cut"])):
        gross_trim = False
        gross_shares = {}
    cap_bounds = {}
    reasons = {}
    held_names = sorted(held)
    for index, symbol in enumerate(held_names):
        m, qty = market.get(symbol), held[symbol]
        if m is None:
            result["requirements"].append({"symbol": symbol, "held_units": qty, "max_units": 0,
                "remaining_sell_units": qty, "reasons": ["TERMINAL_FLATTEN" if terminal else "SCHEDULED_FLATTEN"
                                                         if interim else "RISK_REEVALUATION_REQUIRED"]
                + (["CLASS_1_EXIT"] if symbol in latched else []),
                "status": "BLOCKED_INPUT" if symbol in invalid else "BLOCKED_MARK"})
            continue
        cap = floor(hard_name * safe_equity * 10**m["decimals"] / m["price_units"])
        reason = []
        if s1:
            # A name over the hard line is sold back to its target: level x w, at most the top level x w.
            t = targets.get(symbol)
            name_target = s1_level * s1["weights"][symbol]
            name_target = rehearsal_name_target(p, s1, name_target, level=s1_level,
                capital_scale=capital_scale, safe_equity=safe_equity, enabled=not r['deep_cut'])
            if t is not None and t.kind is TargetKind.TARGET_WEIGHT:
                name_target = min(name_target, t.weight)
        else:
            name_target = fraction(p["operating_name_weight"])
        operating_cap = floor(name_target * safe_equity * 10**m["decimals"] / m["price_units"])
        # PF-05 (#55): a missing mark counted as 0 overstates every other name's weight, so incomplete
        # valuation never starts a hard-line trim. An obligation started under complete marks continues.
        if qty + pending_buy.get(symbol, 0) > cap and not unvalued:
            name_trims.add(symbol)
        if qty + pending_buy.get(symbol, 0) <= operating_cap:
            name_trims.discard(symbol)
        if symbol in name_trims:
            reason.append("POSITION_CAP")
            cap = operating_cap
        else:
            cap = qty
        if gross_trim and gross > safe_equity * gross_limit:
            # Freeze allocation shares when the obligation starts. Recomputing shares after each
            # settled child repeatedly trims completed names and creates an asymptotic micro-trade tail.
            if symbol not in gross_shares and durable_trims and not unvalued:
                gross_shares[symbol] = ratio(value(qty, m) / gross)
            # Incomplete valuation cannot establish allocation shares; retain existing ones, but
            # use conservative provisional bounds for names without a complete starting valuation.
            share = fraction(gross_shares[symbol]) if symbol in gross_shares else value(qty, m) / gross
            cap = min(cap, floor(share * safe_equity * gross_limit
                                 * 10**m["decimals"] / m["price_units"]))
            reason.append("DEEP_DRAWDOWN" if r["deep_cut"] else "GROSS_OR_REGIME_CAP")
        if index >= max_positions:
            cap = 0
            reason.append("POSITION_COUNT_CAP")
        if symbol in latched or (targets.get(symbol) is not None and targets[symbol].reason == "CLASS_1_EXIT"):
            cap = 0
            reason.append("CLASS_1_EXIT")
        if terminal:
            cap = 0
            reason.append("TERMINAL_FLATTEN")
        elif interim:
            cap = 0
            reason.append("SCHEDULED_FLATTEN")
        elif check_phase == "SELL" and symbol == check["symbol"]:
            cap = 0
            reason.append(self_check.REASON)
        for requirement in c.get("reduction_constraints", []):
            if requirement["symbol"] == symbol:
                bound = integer(requirement["max_units"])
                cap = min(cap, bound)
                reason.append(requirement["reason"])
        cap_bounds[symbol], reasons[symbol] = cap, reason
        if cap < qty:
            result["requirements"].append({"symbol": symbol, "held_units": qty,
                                           "max_units": cap, "remaining_sell_units": qty - cap,
                                           "reasons": reason,
                                           "status": "BLOCKED_PRICE_JUMP" if symbol in jumped else "PENDING"})
    if durable_trims:
        r["cap_trims"] = {"names": sorted(name_trims), "gross": gross_trim,
                          "gross_shares": gross_shares}
    # The nonce simplification also ensures pending trades cannot allocate twice.
    global_blocks = []
    for gate in ("integrity_ok", "journal_ok", "ownership_ok", "clock_ok"):
        if c.get("health", {}).get(gate) is not True:
            global_blocks.append(gate.upper())
    if ledger["reservations"]:
        global_blocks.append("WALLET_PENDING")
    if now >= instant(p["signing_end"]):
        global_blocks.append("SIGNING_END")
    if global_blocks:
        result["rejections"].append({"reason": "EXECUTION_BLOCKED", "gates": global_blocks})
        for req in result["requirements"]:
            req["status"] = "BLOCKED"
        return Document.from_dict(result)

    # Gas replenishment has its own round, no position slot or gross allocation.
    # A blocked top-up cannot hide mandatory sale requirements already recorded.
    gas_rows = p.get("quote_cost_summary", {}).get("symbols", {})
    sale_gas = min((gas_rows[req["symbol"]]["approve_gas_bnb_units"]
                    + gas_rows[req["symbol"]]["swap_gas_bnb_units"]
                    for req in result["requirements"] if req["symbol"] in gas_rows), default=0)
    mandatory_can_pay = bool(result["requirements"]) and ledger["bnb_units"] >= sale_gas
    gas_short = not terminal and not mandatory_can_pay and plan_top_up(snapshot, p, risk_ledger, result)
    if gas_short:
        if result["intents"] or result["quote_requests"]:
            return Document.from_dict(result)

    def urgency(req):
        # Class 1 / terminal first, then by notional at the current mark; token units say nothing
        # about value across decimals and prices (#64 item 3). Unmarked names go last in their class.
        m = market.get(req["symbol"])
        return (not {"CLASS_1_EXIT", "TERMINAL_FLATTEN", "SCHEDULED_FLATTEN"} & set(req["reasons"]), m is None,
                -value(req["remaining_sell_units"], m) if m is not None else 0, req["symbol"])

    actions = []
    for req in sorted(result["requirements"], key=urgency):
        if req["symbol"] in jumped:
            continue  # waits for the balance check; other symbols' trades go on
        actions.append((req["symbol"], "SELL", req["remaining_sell_units"], True, req["reasons"]))
    # No discretionary action while any mandatory obligation is outstanding.
    if not actions:
        count = len(set(held) | set(pending_buy))
        for symbol, t in sorted(targets.items()):
            if t.kind is TargetKind.KEEP_QUANTITY:
                continue
            if symbol in jumped:
                result["rejections"].append({"symbol": symbol, "reason": "PRICE_JUMP_HOLD"})
                continue
            m = market.get(symbol)
            if m is None:
                result["rejections"].append({"symbol": symbol, "reason": "MISSING_MARKET"})
                continue
            current = held.get(symbol, 0)
            name_cap = s1["high"] * s1["weights"][symbol] * capital_scale if s1 else fraction(p["operating_name_weight"])
            if s1:
                name_cap = rehearsal_name_target(p, s1, name_cap, level=s1_level,
                    capital_scale=capital_scale, safe_equity=safe_equity, enabled=not r['deep_cut'])
            desired = 0 if t.kind is TargetKind.EXIT else floor(
                min(t.weight, name_cap) * safe_equity * 10**m["decimals"] / m["price_units"])
            if (check_phase == "BUY" and symbol == check["symbol"]
                    and not instant(p["trade_after"]) <= now < instant(p["new_risk_end"])):
                # SC: before trade_after the planner itself bounds the self-check BUY to pay_units.
                desired = min(desired, current + floor(Fraction(check["pay_units"]) * 10**m["decimals"]
                                                       / m["price_units"]))
            if desired == current:
                continue
            side, q = ("BUY", desired - current) if desired > current else ("SELL", current - desired)
            if side == "BUY":
                if interim:
                    # A held name that cannot be sold this round must not let the book grow before it is flat.
                    result["rejections"].append({"symbol": symbol, "reason": "SCHEDULED_FLATTEN_PENDING"})
                    continue
                if (gas_short or unvalued or E <= 0 or r["daily_halt"] or r["run_halt"] or terminal
                        or c.get("health", {}).get("new_spending_ok", p.get("mode") != "LIVE") is not True
                        or now.date().isoformat() != r["day"]
                        or not (instant(p["trade_after"]) <= now < instant(p["new_risk_end"])
                                or (check_phase == "BUY" and symbol == check["symbol"]))):
                    result["rejections"].append({"symbol": symbol, "reason": "NEW_RISK_HALTED"})
                    continue
                if not current and count >= max_positions:
                    result["rejections"].append({"symbol": symbol, "reason": "POSITION_COUNT_CAP"})
                    continue
                ceiling = gross_limit if s1 else min(gross_limit, fraction(p["operating_gross_weight"]))
                capacity = max(Fraction(0), ceiling * safe_equity - gross)
                q = min(q, floor(capacity * 10**m["decimals"] / m["price_units"]))
            if s1:
                # IDEA-076 Q14: a per-name leg budget per session replaces the one-swap-per-session rule.
                legs = c.get("discretionary_legs") or {}
                if type(legs) is not dict or any(type(v) is not int or v < 0 for v in legs.values()):
                    raise ContractError("Discretionary leg counts must map symbols to counts")
                if legs.get(symbol, 0) >= s1["legs"]:
                    result["rejections"].append({"symbol": symbol, "reason": "DISCRETIONARY_CADENCE"})
                    continue
            elif c.get("last_discretionary_session") == c["session_index"]:
                result["rejections"].append({"symbol": symbol, "reason": "DISCRETIONARY_CADENCE"})
                continue
            if q > 0:
                actions.append((symbol, side, q, False, [t.reason]))

    if s1 and actions and not actions[0][3]:
        # IDEA-075 §5.2: sells first, then buys, largest gap first (by notional at the current mark).
        # IDEA-090 (S2-F3): a quote follow-up plans the leg its parent asked a quote for, and notionals compare in
        # whole cash units, so a sub-unit price move between the rounds cannot re-order near-equal legs.
        asked = execution_bounds.requested_legs(c)
        actions.sort(key=lambda a: (a[1] != "SELL", (a[0], a[1]) not in asked, -floor(value(a[2], market[a[0]])),
                                    a[0]))
    if p["baseline"] == "EQUAL_WEIGHT" and actions and not actions[0][3]:
        # Candidate selection and actual child execution must use the same cost
        # priority; alphabetical planning otherwise spends the daily slot first.
        # An explicitly unavailable cost (None outside LIVE) ranks last, like a missing one.
        cost = lambda symbol: market[symbol].get("measured_roundtrip_bps")
        actions.sort(key=lambda a: (a[1] != "SELL", 10**9 if cost(a[0]) is None else cost(a[0]), a[0]))
    attempt_budget = None
    if s1:
        try:
            execution_bounds.session(c)
            execution_bounds.cadence_policy(c)
            attempt_budget = execution_bounds.budget(c.get('execution_attempt_budget'), c['session_index'],
                                                      now_ms=int(now.timestamp() * 1000))
        except (ContractError, KeyError, TypeError):
            result['rejections'].append({'reason': 'EXECUTION_BOUNDS_INVALID'})
            return Document.from_dict(result)
        result['execution_attempt_budget'] = attempt_budget
        result['execution_attempts'] = []
    for symbol, side, quantity, mandatory, why in actions:
        m = market.get(symbol)
        if m is None:
            continue
        costed_reduction = (s1 is not None and side == 'SELL' and not mandatory
                            and why == ['S1_LEVEL_CHANGE'] and p.get('s1_reduction_cost_cap_bps') == 50)
        # IDEA-110: the micro self-check BUY replaces the minimum trade and bps entry cap with an absolute cost cap.
        micro_check = (side == 'BUY' and not mandatory and why == ['ACTIVATION_SELF_CHECK_BUY'] and check_phase == 'BUY'
                       and symbol == check['symbol'] and 'max_cost_units' in check)
        notional_cap = max(0, p["per_trade_cap_units"] - (cost_reserve if side == "BUY" else 0))
        if side == "SELL" and mandatory:
            # LD10-P03: balanced children; every child of a split exit stays economically executable.
            q = quantity // exit_parts(value(quantity, m), p["per_trade_cap_units"])
        else:
            q = min(quantity, floor(Fraction(notional_cap) * 10**m["decimals"] / m["price_units"]))
        req = next((r for r in result["requirements"] if r["symbol"] == symbol), None)
        if q <= p["dust_units"] or q <= 0:
            if req is not None:
                req["status"] = "DUST_OR_UNEXECUTABLE"
            result["rejections"].append({"symbol": symbol, "reason": "DUST_OR_UNEXECUTABLE"})
            continue
        if (not mandatory and not costed_reduction and not micro_check
                and value(q, m) < p["minimum_trade_units"]):
            result["rejections"].append({"symbol": symbol, "reason": "MINIMUM_TRADE"})
            continue
        if m.get("token_open") is not True or m.get("underlying_open") is not True:
            if req is not None:
                req["status"] = "BLOCKED_MARKET"
            result["rejections"].append({"symbol": symbol, "reason": "MARKET_CLOSED_OR_UNKNOWN"})
            continue
        bounds = None
        if s1:
            bounds, refused = execution_bounds.reserve(c, s1, attempt_budget, symbol, side, mandatory,
                                                       int(now.timestamp() * 1000), quotes=m.get('quotes', []))
            if refused:
                result['rejections'].append({'symbol': symbol, 'reason': refused})
                if req is not None:
                    req['status'] = refused
                continue
            result['execution_attempts'].append(dict(symbol=symbol, side=side, mandatory=mandatory,
                                                      authority=bounds))
        pay_units = floor(value(q, m)) if side == "BUY" else q
        quote, request_units, rejected, quote_status = _quote_at_cap(m, side, pay_units, p, now, quantity, mandatory)
        if s1 and (quote is not None or request_units is None):
            execution_bounds.close(attempt_budget, bounds)
        result["rejections"].extend({"symbol": symbol, "reason": reason} for reason in rejected)
        if quote is None:
            if req is not None:
                req["status"] = quote_status
            if request_units is not None:
                result["quote_requests"].append(_request(symbol, side, request_units, m, mandatory))
                if s1:
                    # One wallet leg's bounded quote chain at a time. Do not
                    # spend attempts for quotes the driver never requests.
                    break
            continue
        cash, fee, gas, q = [quote[k] for k in ("cash_units", "fee_units", "gas_bnb_units", "token_units")]
        if q <= p["dust_units"] or (not mandatory and not costed_reduction and not micro_check
                                    and value(q, m) < p["minimum_trade_units"]):
            if req is not None:
                req["status"] = "DUST_OR_UNEXECUTABLE"
            result["rejections"].append({"symbol": symbol, "reason": "DUST_OR_MINIMUM_TRADE"})
            continue
        # IDEA-088: the cost uses the expected fee when the quote gives one; reservation and gas checks keep `gas`.
        gas_value = ceil(Fraction(quote.get("expected_gas_bnb_units", gas) * ledger["bnb_price_units"],
                                  10**ledger["bnb_decimals"]))
        # RV01-2: the authorized minimum, not the displayed quote, is the executable cost bound.
        # Gas here is the declared expected allowance; the full action budget remains reserved below.
        minimum_buy = side == 'BUY' and p.get('entry_cost_basis') == 'AUTHORIZED_MINIMUM'
        mark = value(quote['min_receive_units'] if minimum_buy else q, m)
        proceeds = quote['min_receive_units'] if costed_reduction else cash
        cost = max(Fraction(0), cash - mark if side == "BUY" else mark - proceeds) + fee + gas_value
        if costed_reduction and cost * 10000 > mark * p['s1_reduction_cost_cap_bps']:
            result['rejections'].append({'symbol': symbol, 'reason': 'S1_REDUCTION_COST_CAP'})
            continue
        if cost > cost_limit and not mandatory:
            result["rejections"].append({"symbol": symbol, "reason": "COST_RESERVE_INSUFFICIENT"})
            continue
        if micro_check and cost > check['max_cost_units']:
            result["rejections"].append({"symbol": symbol, "reason": "SELF_CHECK_COST_CAP"})
            continue
        if not mandatory and side == "BUY":
            if not micro_check and cost * 10000 > mark * p.get("s5_entry_cost_cap_bps", 50):
                result["rejections"].append({"symbol": symbol, "reason": "ENTRY_COST_CAP"})
                continue
            if p.get("mode") == "LIVE":
                median = p["impact_median_bps"].get(symbol)
                if type(median) is not int or quote["impact_bps"] > min(50, 2 * median):
                    result["rejections"].append({"symbol": symbol, "reason": "ENTRY_IMPACT_CAP"})
                    continue
            else:
                depth = quote.get("quoted_depth_units")
                if type(depth) is not int or depth < 10 * q:
                    result["rejections"].append({"symbol": symbol, "reason": "DECLARED_DEPTH_INPUT_UNAVAILABLE"})
                    continue
        if gas > ledger["bnb_units"] - reserved_bnb:
            if req is not None:
                req["status"] = "BLOCKED_GAS"
            result["rejections"].append({"symbol": symbol, "reason": "INSUFFICIENT_GAS"})
            continue
        if side == "BUY":
            spend = cash + fee
            # The 20% uninvested floor counts free gas BNB, so four 20% names fit beside a gas reserve (IDEA-037).
            free_bnb = max(0, floor(Fraction((ledger["bnb_units"] - reserved_bnb - gas) * ledger["bnb_price_units"],
                                             10**ledger["bnb_decimals"])))
            if (spend > ledger["cash_units"] - reserved_cash
                    or ledger["cash_units"] + free_bnb - spend < ceil(
                        safe_equity * (1 - s1["high"]) if s1 else Fraction(safe_equity, 5))
                    or ledger["bnb_units"] - reserved_bnb - gas < p["exit_gas_reserve_units"]):
                result["rejections"].append({"symbol": symbol, "reason": "CASH_OR_EXIT_RESERVE"})
                continue
        else:
            spend = 0
            if q > positions[symbol]["units"]:
                raise ContractError("Planner oversell")
            if fee > cash + ledger["cash_units"]:
                if req is not None:
                    req["status"] = "BLOCKED_EXIT_FEE"
                result["rejections"].append({"symbol": symbol, "reason": "UNAFFORDABLE_EXIT_FEE"})
                continue
        if cost > cost_reserve and mandatory:
            # Tighten bounds only after this child passes every execution gate.
            adjusted_equity = max(0, E - ceil(cost))
            for requirement in result["requirements"]:
                if requirement["status"] in ("BLOCKED_MARK", "BLOCKED_INPUT"):
                    continue
                old_bound = requirement["max_units"]
                requirement["max_units"] = min(old_bound, floor(Fraction(old_bound * adjusted_equity, max(1, safe_equity))))
                requirement["remaining_sell_units"] = requirement["held_units"] - requirement["max_units"]
            quantity = req["remaining_sell_units"]
            result["clamps"].append({"symbol": symbol, "reason": "POST_QUOTE_COST_REDUCTION",
                                     "cost_units": ceil(cost)})
        if req is not None:
            req["status"] = "PARTIAL_REQUIRES_POST_FILL_REPLAN" if q < quantity else "AWAITING_SETTLEMENT"
        intent = {"symbol": symbol, "side": side, "token_units": q, "decimals": m["decimals"],
                  "cash_units": cash, "fee_units": fee, "gas_bnb_units": gas,
                  "mandatory": mandatory, "reasons": why, "quote_id": quote["quote_id"],
                  "quote_expiry": min(instant(quote["expires_at"]), instant(p["signing_end"])).isoformat(),
                  "parent_remaining_units": quantity - q,
                  "amount_kind": "EXACT_IN", "pay_asset": quote["pay_asset"], "pay_units": quote["pay_units"],
                  "min_receive_units": quote["min_receive_units"],
                  "receive_decimals": m["decimals"] if side == "BUY" else 6}
        if bounds is not None:
            intent['execution_bounds'] = bounds
        intent_id = Document.from_dict({"snapshot_id": snapshot.snapshot_id, **intent}).digest("EconomicIntent.v1")
        intent["intent_id"] = intent_id
        result["intents"].append(intent)
        result["reservation_deltas"].append({"intent_id": intent_id, "cash_units": spend,
                                              "bnb_units": gas, "symbol": symbol,
                                              "side": side, "token_units": q, "pay_units": intent["pay_units"],
                                              "min_receive_units": intent["min_receive_units"]})
        if q < quantity:
            result["clamps"].append({"symbol": symbol, "reason": "PER_TRADE_CAP",
                                     "requested_units": quantity, "planned_units": q})
        break
    return Document.from_dict(result)

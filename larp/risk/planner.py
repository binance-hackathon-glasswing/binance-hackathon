"""Independent constraints and staged exact-size quoting; requests, not authority.

One immediate child intent per wallet simplifies nonce ownership. Parent reduction
requirements retain every residual; re-plan on observed settlement, never assumed
sell proceeds. The runtime stores requests atomically and execution revalidates.
"""

from fractions import Fraction

from larp.contracts import ContractError, Document, TargetKind, validate_proposal
from larp.strategy.schema import (ceil, equity, floor, fraction, instant, integer,
                                  markets, profile, ratio, value)
from .accounting import update_risk


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
        market = markets(snapshot, p)
        E = equity(ledger, market)
        if E <= 0:
            raise ContractError("Nonpositive equity")
        risk_ledger = update_risk(Document.from_dict(ledger), now=now, equity_units=E).read()
        r = risk_ledger["risk"]
        result["risk_state"] = r
    except (KeyError, TypeError, ContractError, ValueError) as exc:
        # Invalid valuation is explicit; terminal holdings remain outstanding.
        result["rejections"].append({"reason": "INVALID_REQUIRED_INPUT", "detail": str(exc)})
        for symbol, pos in c.get("portfolio", {}).get("positions", {}).items():
            if pos.get("units", 0):
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
    cost_reserve = p["cost_reserve_units"]
    safe_equity = max(0, E - cost_reserve)
    gross_limit = min(Fraction(4, 5), fraction(p["regime_gross_weight"]))
    if r["deep_cut"]:
        gross_limit = min(gross_limit, Fraction(2, 5))
    positions = ledger["positions"]
    held = {s: pos["units"] for s, pos in positions.items() if pos["units"]}
    pending_buy = {}
    reserved_cash = reserved_bnb = 0
    for reservation in ledger["reservations"].values():
        reserved_cash += integer(reservation["cash_units"])
        reserved_bnb += integer(reservation["bnb_units"])
        if reservation["side"] == "BUY":
            s = reservation["symbol"]
            pending_buy[s] = pending_buy.get(s, 0) + integer(reservation["token_units"])
    gross = sum((value(q + pending_buy.get(s, 0), market[s]) for s, q in held.items()), Fraction(0))
    gross += sum((value(q, market[s]) for s, q in pending_buy.items() if s not in held), Fraction(0))
    result["worst_case_gross_units"] = ceil(gross)
    result["available_cash_units"] = max(0, ledger["cash_units"] - reserved_cash)
    cap_bounds = {}
    reasons = {}
    held_names = sorted(held)
    for index, symbol in enumerate(held_names):
        m, qty = market[symbol], held[symbol]
        cap = floor(Fraction(safe_equity, 5) * 10**m["decimals"] / m["price_units"])
        reason = []
        if qty + pending_buy.get(symbol, 0) > cap:
            reason.append("POSITION_CAP")
            cap = floor(fraction(p["operating_name_weight"]) * safe_equity
                        * 10**m["decimals"] / m["price_units"])
        else:
            cap = qty
        if gross > safe_equity * gross_limit:
            cap = min(cap, floor(Fraction(qty) * safe_equity * gross_limit / gross))
            reason.append("DEEP_DRAWDOWN" if r["deep_cut"] else "GROSS_OR_REGIME_CAP")
        if index >= 4:
            cap = 0
            reason.append("POSITION_COUNT_CAP")
        if terminal:
            cap = 0
            reason.append("TERMINAL_FLATTEN")
        for requirement in c.get("reduction_constraints", []):
            if requirement["symbol"] == symbol:
                bound = integer(requirement["max_units"])
                cap = min(cap, bound)
                reason.append(requirement["reason"])
        cap_bounds[symbol], reasons[symbol] = cap, reason
        if cap < qty:
            result["requirements"].append({"symbol": symbol, "held_units": qty,
                                           "max_units": cap, "remaining_sell_units": qty - cap,
                                           "reasons": reason, "status": "PENDING"})
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

    actions = []
    for req in sorted(result["requirements"], key=lambda x: (-x["remaining_sell_units"], x["symbol"])):
        actions.append((req["symbol"], "SELL", req["remaining_sell_units"], True, req["reasons"]))
    # No discretionary action while any mandatory obligation is outstanding.
    if not actions:
        count = len(set(held) | set(pending_buy))
        for symbol, t in sorted(targets.items()):
            if t.kind is TargetKind.KEEP_QUANTITY:
                continue
            m = market.get(symbol)
            if m is None:
                result["rejections"].append({"symbol": symbol, "reason": "MISSING_MARKET"})
                continue
            current = held.get(symbol, 0)
            desired = 0 if t.kind is TargetKind.EXIT else floor(
                min(t.weight, fraction(p["operating_name_weight"])) * safe_equity
                * 10**m["decimals"] / m["price_units"])
            if desired == current:
                continue
            side, q = ("BUY", desired - current) if desired > current else ("SELL", current - desired)
            if side == "BUY":
                if (r["daily_halt"] or r["run_halt"] or terminal
                        or now.date().isoformat() != r["day"]
                        or not instant(p["trade_after"]) <= now < instant(p["new_risk_end"])):
                    result["rejections"].append({"symbol": symbol, "reason": "NEW_RISK_HALTED"})
                    continue
                if not current and count >= 4:
                    result["rejections"].append({"symbol": symbol, "reason": "POSITION_COUNT_CAP"})
                    continue
                capacity = max(Fraction(0), min(gross_limit, fraction(p["operating_gross_weight"]))
                               * safe_equity - gross)
                q = min(q, floor(capacity * 10**m["decimals"] / m["price_units"]))
            if c.get("last_discretionary_session") == c["session_index"]:
                result["rejections"].append({"symbol": symbol, "reason": "DISCRETIONARY_CADENCE"})
                continue
            if q > 0:
                actions.append((symbol, side, q, False, [t.reason]))

    for symbol, side, quantity, mandatory, why in actions:
        m = market[symbol]
        notional_cap = max(0, p["per_trade_cap_units"] - (cost_reserve if side == "BUY" else 0))
        q = min(quantity, floor(Fraction(notional_cap) * 10**m["decimals"] / m["price_units"]))
        req = next((r for r in result["requirements"] if r["symbol"] == symbol), None)
        if q <= p["dust_units"] or q <= 0:
            if req is not None:
                req["status"] = "DUST_OR_UNEXECUTABLE"
            result["rejections"].append({"symbol": symbol, "reason": "DUST_OR_UNEXECUTABLE"})
            continue
        if not mandatory and value(q, m) < p["minimum_trade_units"]:
            result["rejections"].append({"symbol": symbol, "reason": "MINIMUM_TRADE"})
            continue
        if m.get("token_open") is not True or m.get("underlying_open") is not True:
            if req is not None:
                req["status"] = "BLOCKED_MARKET"
            result["rejections"].append({"symbol": symbol, "reason": "MARKET_CLOSED_OR_UNKNOWN"})
            continue
        quote = next((quote for quote in m.get("quotes", [])
                      if quote.get("side") == side and quote.get("token_units") == q), None)
        if quote is None:
            result["quote_requests"].append({"schema": "MarketRequest.v1", "symbol": symbol,
                                             "side": side, "token_units": q,
                                             "decimals": m["decimals"], "mandatory": mandatory})
            continue
        if (not quote.get("route_valid") or instant(quote["available_at"]) > now
                or not 0 <= (now - instant(quote["observed_at"])).total_seconds() <= p["quote_age_seconds"]
                or now >= instant(quote["expires_at"]) or quote["slippage_bps"] > p["slippage_bps"]
                or quote["impact_bps"] > p["impact_bps"]):
            result["rejections"].append({"symbol": symbol, "reason": "QUOTE_ROUTE_OR_SLIPPAGE"})
            continue
        cash, fee, gas = [integer(quote[k]) for k in ("cash_units", "fee_units", "gas_bnb_units")]
        if cash + fee > p["per_trade_cap_units"]:
            result["rejections"].append({"symbol": symbol, "reason": "EXECUTABLE_TRADE_CAP"})
            continue
        gas_value = ceil(Fraction(gas * ledger["bnb_price_units"], 10**ledger["bnb_decimals"]))
        mark = value(q, m)
        cost = max(Fraction(0), cash - mark if side == "BUY" else mark - cash) + fee + gas_value
        if cost > cost_reserve:
            result["rejections"].append({"symbol": symbol, "reason": "COST_RESERVE_INSUFFICIENT"})
            continue
        if not mandatory and side == "BUY":
            if cost * 10000 > mark * 50:
                result["rejections"].append({"symbol": symbol, "reason": "ENTRY_COST_CAP"})
                continue
            depth = quote.get("quoted_depth_units")
            if type(depth) is not int or depth < 10 * q:
                result["rejections"].append({"symbol": symbol, "reason": "DECLARED_DEPTH_INPUT_UNAVAILABLE"})
                continue
        if gas > ledger["bnb_units"] - reserved_bnb:
            result["rejections"].append({"symbol": symbol, "reason": "INSUFFICIENT_GAS"})
            continue
        if side == "BUY":
            spend = cash + fee
            if (spend > ledger["cash_units"] - reserved_cash
                    or ledger["cash_units"] - spend < ceil(Fraction(safe_equity, 5))
                    or ledger["bnb_units"] - reserved_bnb - gas < p["exit_gas_reserve_units"]):
                result["rejections"].append({"symbol": symbol, "reason": "CASH_OR_EXIT_RESERVE"})
                continue
        else:
            spend = 0
            if q > positions[symbol]["units"]:
                raise ContractError("Planner oversell")
        intent = {"symbol": symbol, "side": side, "token_units": q, "decimals": m["decimals"],
                  "cash_units": cash, "fee_units": fee, "gas_bnb_units": gas,
                  "mandatory": mandatory, "reasons": why, "quote_id": quote["quote_id"],
                  "quote_expiry": quote["expires_at"], "parent_remaining_units": quantity - q}
        intent_id = Document.from_dict({"snapshot_id": snapshot.snapshot_id, **intent}).digest("EconomicIntent.v1")
        intent["intent_id"] = intent_id
        result["intents"].append(intent)
        result["reservation_deltas"].append({"intent_id": intent_id, "cash_units": spend,
                                              "bnb_units": gas, "symbol": symbol,
                                              "side": side, "token_units": q})
        if q < quantity:
            result["clamps"].append({"symbol": symbol, "reason": "PER_TRADE_CAP",
                                     "requested_units": quantity, "planned_units": q})
        break
    return Document.from_dict(result)

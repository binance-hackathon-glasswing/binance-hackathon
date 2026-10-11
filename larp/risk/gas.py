"""I7: USDT -> native BNB is a wallet resource action, never a stock slot.

The coordinator must dispatch this PlanResult alone as its own round and apply
the same atomic reservation, fencing, signing and audit rules as stock intents.
"""

from fractions import Fraction

from larp.contracts import ContractError, Document
from larp.strategy.schema import ceil, instant, integer


def plan_top_up(snapshot, p, ledger, result):
    """True when gas needs attention; caller does not allocate stock buys in this round."""
    if "gas_floor_bnb_units" not in p:
        return False
    c, now = snapshot.context.read(), snapshot.observed_at
    if ledger["bnb_units"] >= p["gas_floor_bnb_units"]:
        return False
    blocked = (now >= instant(p["new_risk_end"]) or now >= instant(p["flatten_start"])
               or now < instant(p["trade_after"]) or result["unvalued_symbols"]
               or ledger["risk"]["daily_halt"] or ledger["risk"]["run_halt"]
               or ledger["risk"]["deep_cut"] or ledger["risk"]["day"] != now.date().isoformat()
               or c.get("health", {}).get("new_spending_ok", p.get("mode") != "LIVE") is not True)
    if blocked:
        result["rejections"].append({"symbol": "BNB", "reason": "GAS_TOP_UP_SPENDING_BLOCKED"})
        return True
    pay = p["gas_top_up_cash_units"]
    if pay > ledger["cash_units"]:
        result["rejections"].append({"symbol": "BNB", "reason": "GAS_TOP_UP_UNAVAILABLE_CASH"})
        return True
    if ledger["bnb_units"] == 0:
        result["rejections"].append({"symbol": "BNB", "reason": "FIRST_BNB_REQUIRED"})
        return True
    request = {"schema": "MarketRequest.v1", "symbol": "BNB", "kind": "GAS_TOP_UP",
               "side": "BUY", "amount_kind": "EXACT_IN", "pay_asset": "USDT",
               "pay_units": pay, "pay_decimals": 6, "mandatory": False}
    quote = next((q for q in c.get("gas_quotes", []) if q.get("kind") == "GAS_TOP_UP"
                  and q.get("symbol") == "BNB" and q.get("pay_units") == pay), None)
    if quote is None:
        result["quote_requests"].append(request)
        return True
    try:
        cash, fee, gas, receive, minimum = [integer(quote[k]) for k in
            ("cash_units", "fee_units", "gas_bnb_units", "token_units", "min_receive_units")]
        valid = (quote.get("side") == "BUY" and quote.get("pay_asset") == "USDT"
            and quote.get("amount_kind") == "EXACT_IN" and quote.get("route_valid") is True
            and quote.get("receive_asset") == "BNB" and quote.get("quote_id")
            and quote.get("receive_decimals") == ledger["bnb_decimals"]
            and (p.get("mode") != "LIVE" or quote.get("origin") == "WEB3_OPEN_API")
            and instant(quote["available_at"]) <= now
            and 0 <= (now - instant(quote["observed_at"])).total_seconds() <= p["quote_age_seconds"]
            and now < instant(quote["expires_at"])
            and integer(quote["slippage_bps"]) <= p["slippage_bps"]
            and integer(quote["impact_bps"]) <= p["impact_bps"]
            and cash == pay and 0 < p["gas_top_up_min_receive_units"] <= minimum <= receive
            and minimum >= receive * (10000 - p["slippage_bps"]) // 10000
            and 0 < gas <= min(ledger["bnb_units"], p["gas_top_up_max_gas_bnb_units"])
            and cash + fee <= min(ledger["cash_units"], p["per_trade_cap_units"]))
        if not valid:
            raise ContractError("Invalid top-up quote or unable to pay its gas")
    except (ContractError, KeyError, TypeError, ValueError):
        result["rejections"].append({"symbol": "BNB", "reason": "GAS_TOP_UP_QUOTE_OR_RESERVE"})
        return True
    intent = {"kind": "GAS_TOP_UP", "purpose": "GAS_TOPUP", "symbol": "BNB", "side": "BUY", "mandatory": False,
        "token_units": receive, "decimals": ledger["bnb_decimals"], "receive_asset": "BNB",
        "receive_decimals": ledger["bnb_decimals"], "cash_units": cash, "fee_units": fee,
        "gas_bnb_units": gas, "amount_kind": "EXACT_IN", "pay_asset": "USDT", "pay_units": pay,
        "min_receive_units": minimum, "quote_id": quote["quote_id"], "quote_expiry": quote["expires_at"],
        "parent_remaining_units": 0, "reasons": ["GAS_RESOURCE_FLOOR"], "own_round": True}
    intent["intent_id"] = Document.from_dict({"snapshot_id": snapshot.snapshot_id, **intent}).digest("EconomicIntent.v1")
    result["intents"].append(intent)
    result["reservation_deltas"].append({"intent_id": intent["intent_id"], "kind": "GAS_TOP_UP", "purpose": "GAS_TOPUP",
        "symbol": "BNB", "side": "BUY", "cash_units": cash + fee, "bnb_units": gas,
        "token_units": receive, "pay_units": pay, "min_receive_units": minimum})
    result["gas_top_up_value_units"] = ceil(Fraction(receive * ledger["bnb_price_units"], 10**ledger["bnb_decimals"]))
    return True

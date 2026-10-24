"""Single pure accounting reducer for confirmed observations and replay.

Intents/reservations are installed by the external atomic store. No quote, proposal,
pending transaction or approval can create a token holding. Average cost is explicit.
"""

from larp.contracts import ContractError, Document
from larp.strategy.schema import floor, instant, integer
from fractions import Fraction


def roll_day(portfolio: Document, *, boundary, anchor_units):
    """Caller must supply a trusted mark AT midnight, before that day's returns."""
    d = portfolio.read()
    boundary = instant(boundary)
    if any((boundary.hour, boundary.minute, boundary.second, boundary.microsecond)):
        raise ContractError("Day rollover requires a midnight boundary mark")
    date = boundary.date().isoformat()
    if date <= d["risk"]["day"]:
        raise ContractError("Cannot repeat or rewind daily anchor")
    integer(anchor_units, 1)
    d["risk"].update(day=date, day_anchor_units=anchor_units, daily_halt=False)
    return Document.from_dict(d)


def update_risk(portfolio: Document, *, now, equity_units):
    now = instant(now.isoformat())
    d = portfolio.read()
    r = d["risk"]
    integer(equity_units)
    peak = max(integer(r["peak_units"], 1), equity_units)
    r["peak_units"] = peak
    r["run_halt"] |= equity_units * 100 <= peak * 92
    r["deep_cut"] |= equity_units * 100 <= peak * 88
    if now.date().isoformat() == r["day"]:
        r["daily_halt"] |= equity_units * 100 <= integer(r["day_anchor_units"], 1) * 97
    # A missing boundary mark blocks new risk; never reset from a post-loss mark.
    return Document.from_dict(d)


def advance_accounting(portfolio: Document, observation: Document):
    d, e = portfolio.read(), observation.read()
    if d.get("schema") != "PortfolioState.v1" or e.get("schema") not in ("ExecutionObservation.v1", "ServiceCostObservation.v1"):
        raise ContractError("Unsupported accounting observation")
    if e.get("run_id") != d["run_id"] or e.get("wallet_id") != d["wallet_id"]:
        raise ContractError("Observed execution belongs to another wallet/run")
    digest = observation.digest("ExecutionObservation.v1")
    applied = d.setdefault("applied_events", {})
    event_id = e["event_id"]
    if event_id in applied:
        if applied[event_id] != digest:
            raise ContractError("Repeated event ID changed immutable payload")
        return portfolio
    if e["schema"] == "ServiceCostObservation.v1":
        instant(e["observed_at"])
        d["accounting"]["service_units"] += integer(e["cost_units"])
        applied[event_id] = digest
        return Document.from_dict(d)
    if e["kind"] not in ("FILL", "APPROVAL", "REVERT", "ABNORMAL"):
        raise ContractError("Only settled fills/approval/revert observations allowed")
    if e.get("settlement") != "FINAL":
        raise ContractError("Provisional events require execution/finality integration")
    if e.get("origin") not in ("SCRIPTED_FAKE", "EXECUTION_RECONCILER"):
        raise ContractError("Untrusted execution origin")
    if e.get("origin") == "SCRIPTED_FAKE" and d.get("mode") not in ("OFFLINE", "offline"):
        raise ContractError("Fake receipt cannot enter live accounting")
    instant(e["observed_at"])
    reservation = d["reservations"].get(e["intent_id"])
    if reservation is None:
        raise ContractError("Settlement has no committed intent reservation")
    if e.get("origin") == "EXECUTION_RECONCILER":
        _final_receipt(e, reservation)
        receipts = d.setdefault("applied_receipts", {})
        if e["tx_hash"] in receipts:
            raise ContractError("Receipt already accounted under another event identity")
    gas = integer(e["gas_bnb_units"])
    # Final gas is a chain fact: charge it even above the quote-sized reservation (#46, WR04). Only gas
    # above the actual balance is impossible on chain, so only that is an integrity failure.
    if gas > d["bnb_units"]:
        raise ContractError("Gas exceeds actual BNB balance")
    d["bnb_units"] -= gas
    over = max(0, gas - integer(reservation["bnb_units"]))
    if over:
        d["accounting"]["gas_over_reserve_bnb_units"] = d["accounting"].get("gas_over_reserve_bnb_units", 0) + over
    reservation["bnb_units"] -= gas - over
    gas_value = integer(e["gas_value_units"])
    d["accounting"]["gas_value_units"] += gas_value
    # Gas expense uses observed USDT valuation, not inferred token quote amounts.
    if e["kind"] == "ABNORMAL":
        from larp.ports import validate_execution_observation
        validate_execution_observation(e)
        # The existing portfolio is the last reconciled asset snapshot, not an assumed
        # normal fill. Exact chain deltas are retained separately until reconciliation.
        # All spending and economic reports remain blocked; no automatic clearing exists.
        d.setdefault("unreconciled_outcomes", {})[event_id] = e
        d["accounting_status"] = "QUARANTINED_UNRECONCILED"
    if e["kind"] == "FILL":
        symbol, side = reservation["symbol"], reservation["side"]
        if e["symbol"] != symbol or e["side"] != side:
            raise ContractError("Fill conflicts with committed intent")
        q, cash, fee = [integer(e[k]) for k in ("token_units", "cash_units", "fee_units")]
        if q == 0 or e.get("intent_terminal") is not True:
            raise ContractError("Invalid settled quantity")
        resource = reservation.get("kind") == "GAS_TOP_UP" or reservation.get("purpose") == "GAS_TOPUP"
        if resource and (symbol != "BNB" or side != "BUY"):
            raise ContractError("Invalid gas resource reservation")
        if not resource and symbol == "BNB":
            raise ContractError("BNB fill requires an explicit gas resource intent")
        position = None if resource else d["positions"][symbol]
        if side == "BUY":
            if (cash != integer(reservation["pay_units"], 1)
                    or q < integer(reservation["min_receive_units"], 1)):
                raise ContractError("Buy violates exact-input/minimum-receive reservation")
            if cash + fee > reservation["cash_units"] or cash + fee > d["cash_units"]:
                raise ContractError("Buy spends unreserved or unavailable cash")
            d["cash_units"] -= cash + fee
            if resource:
                d["bnb_units"] += q
                d["accounting"]["gas_top_up_cash_units"] = d["accounting"].get("gas_top_up_cash_units", 0) + cash + fee
            else:
                position["units"] += q
                position["cost_basis_units"] += cash + fee
        elif side == "SELL":
            if q != reservation["token_units"] or cash < integer(reservation["min_receive_units"]):
                raise ContractError("Sell violates exact-input/minimum-receive reservation")
            if q > position["units"]:
                raise ContractError("Oversell")
            basis = floor(Fraction(position["cost_basis_units"] * q, position["units"]))
            position["units"] -= q
            position["cost_basis_units"] -= basis
            d["cash_units"] += cash - fee
            if d["cash_units"] < 0:
                raise ContractError("Sale fee exceeds available cash")
            d["accounting"]["realized_units"] += cash - fee - basis
        else:
            raise ContractError("Unknown side")
        d["accounting"]["fees_units"] += fee
        if not resource:
            d["accounting"]["turnover_units"] += cash
    if e.get("intent_terminal") is True:
        del d["reservations"][e["intent_id"]]
    applied[event_id] = digest
    if e.get("origin") == "EXECUTION_RECONCILER":
        d["applied_receipts"][e["tx_hash"]] = digest
    return Document.from_dict(d)


def _final_receipt(e, reservation):
    """I4 proposed canonical receipt facts; execution owner proves the evidence.

    Hash checks are binding/shape checks, not an RPC finality proof. Runtime must
    persist trusted reconciler observations and reject untrusted producers.
    """
    def chain_hash(h):
        return (type(h) is str and len(h) == 66 and h.startswith("0x")
                and all(c in "0123456789abcdefABCDEF" for c in h[2:]))
    # PR #13 publishes canonical receipt evidence flat on ExecutionObservation.v1.
    # FINAL is the reconciler's finality attestation. Detailed nested receipt proof
    # is optional; if supplied it must agree with the flat record, never replace it.
    if (not chain_hash(e.get("tx_hash")) or not chain_hash(e.get("block_hash"))
            or e.get("canonical") is not True or not e.get("round_id")
            or e["round_id"] != reservation.get("round_id")):
        raise ContractError("Canonical final receipt and committed round identity required")
    receipt = e.get("receipt")
    if receipt is not None:
        if (type(receipt) is not dict or receipt.get("tx_hash") != e["tx_hash"]
                or receipt.get("block_hash") != e["block_hash"] or receipt.get("canonical") is not True
                or receipt.get("finality") != "FINAL" or receipt.get("chain_id") != 56):
            raise ContractError("Detailed receipt disagrees with final observation")
        integer(receipt.get("block_number"), 1)
        expected_status = 0 if e["kind"] == "REVERT" else 1
        if type(receipt.get("status")) is not int or receipt["status"] != expected_status:
            raise ContractError("Receipt status disagrees with accounting fact")
    if e["kind"] == "FILL" and e.get("intent_terminal") is not True:
        raise ContractError("Final fill must terminate the exact-input intent")
    if e["kind"] == "APPROVAL" and e.get("intent_terminal") is not False:
        raise ContractError("Approval cannot terminate a swap intent")
    terminal = e.get("intent_terminal")
    if type(terminal) is not bool:
        raise ContractError("Explicit intent termination required")


def economic_views(portfolio: Document, *, equity_units):
    d = portfolio.read()
    if d.get("unreconciled_outcomes"):
        raise ContractError("Economic views unavailable for unreconciled abnormal outcomes")
    wallet = integer(equity_units) - integer(d["opening_equity_units"])
    return Document.from_dict({"schema": "EconomicViews.v1", "wallet_net_units": wallet,
                              "off_wallet_service_units": d["accounting"]["service_units"],
                              "total_economic_net_units": wallet - d["accounting"]["service_units"],
                              "realized_units": d["accounting"]["realized_units"],
                              "gas_value_units": d["accounting"]["gas_value_units"],
                              "fees_units": d["accounting"]["fees_units"],
                              "bnb_units": d["bnb_units"],
                              "bnb_value_units": floor(Fraction(d["bnb_units"] * d["bnb_price_units"],
                                                               10**d["bnb_decimals"])),
                              "gas_top_up_cash_units": d["accounting"].get("gas_top_up_cash_units", 0)})

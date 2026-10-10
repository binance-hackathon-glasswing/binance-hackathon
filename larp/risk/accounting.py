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
    if e["kind"] not in ("FILL", "APPROVAL", "REVERT"):
        raise ContractError("Only settled fills/approval/revert observations allowed")
    if e.get("settlement") != "FINAL":
        raise ContractError("Provisional events require execution/finality integration")
    if e.get("origin") not in ("SCRIPTED_FAKE", "EXECUTION_RECONCILER"):
        raise ContractError("Untrusted execution origin")
    instant(e["observed_at"])
    reservation = d["reservations"].get(e["intent_id"])
    if reservation is None:
        raise ContractError("Settlement has no committed intent reservation")
    gas = integer(e["gas_bnb_units"])
    if gas > reservation["bnb_units"] or gas > d["bnb_units"]:
        raise ContractError("Gas exceeds committed reserve/actual balance")
    d["bnb_units"] -= gas
    reservation["bnb_units"] -= gas
    gas_value = integer(e["gas_value_units"])
    d["accounting"]["gas_value_units"] += gas_value
    # Gas expense uses observed USDT valuation, not inferred token quote amounts.
    if e["kind"] == "FILL":
        symbol, side = reservation["symbol"], reservation["side"]
        if e["symbol"] != symbol or e["side"] != side:
            raise ContractError("Fill conflicts with committed intent")
        q, cash, fee = [integer(e[k]) for k in ("token_units", "cash_units", "fee_units")]
        if q == 0 or q != reservation["token_units"] or e.get("intent_terminal") is not True:
            raise ContractError("Invalid settled quantity")
        position = d["positions"][symbol]
        if side == "BUY":
            if cash + fee > reservation["cash_units"] or cash + fee > d["cash_units"]:
                raise ContractError("Buy spends unreserved or unavailable cash")
            d["cash_units"] -= cash + fee
            position["units"] += q
            position["cost_basis_units"] += cash + fee
        elif side == "SELL":
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
        d["accounting"]["turnover_units"] += cash
    if e.get("intent_terminal") is True:
        del d["reservations"][e["intent_id"]]
    applied[event_id] = digest
    return Document.from_dict(d)


def economic_views(portfolio: Document, *, equity_units):
    d = portfolio.read()
    wallet = integer(equity_units) - integer(d["opening_equity_units"])
    return Document.from_dict({"schema": "EconomicViews.v1", "wallet_net_units": wallet,
                              "off_wallet_service_units": d["accounting"]["service_units"],
                              "total_economic_net_units": wallet - d["accounting"]["service_units"],
                              "realized_units": d["accounting"]["realized_units"],
                              "gas_value_units": d["accounting"]["gas_value_units"],
                              "fees_units": d["accounting"]["fees_units"]})

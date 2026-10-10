"""Owner-local v1 adapters to the kickoff's immutable Documents.

These schemas are proposed integration detail, not a competing shared port/store.
All money is USDT base units; token and BNB quantities have explicit decimals.
"""

from datetime import datetime, timezone
from fractions import Fraction

from larp.contracts import ContractError, Document

SYMBOLS = {"NVDAB", "GOOGLB", "SKHYB", "TSLAB", "MSFTB"}
MONEY_SCALE = 1_000_000


def instant(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("timezone required")
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ContractError("Explicit UTC-compatible timestamp required") from exc


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ContractError("Invalid integer quantity")
    return value


def fraction(value):
    if type(value) is not list or len(value) != 2:
        raise ContractError("Fraction must be [numerator, denominator]")
    return Fraction(integer(value[0]), integer(value[1], 1))


def ratio(value):
    return [value.numerator, value.denominator]


def floor(value):
    return value.numerator // value.denominator


def ceil(value):
    return -(-value.numerator // value.denominator)


def profile(snapshot):
    context = snapshot.context.read()
    p = context["profile"]
    if Document.from_dict(p).digest("StrategyProfile.v1") != snapshot.policy_profile_hash:
        raise ContractError("Profile hash mismatch")
    if p.get("schema") != "StrategyProfile.v1" or p.get("mode") != "OFFLINE_FIXTURE":
        raise ContractError("Live configuration unsupported until integration/adoption")
    if p.get("values_origin") != "SYNTHETIC" or not p.get("provenance"):
        raise ContractError("Fixture values need explicit provenance")
    if p["policy_id"] != snapshot.policy_state.policy_id:
        raise ContractError("Policy identity mismatch")
    if p["evidence_mode"] not in ("SHADOW", "BOUNDED_FALSIFIER"):
        raise ContractError("Unknown evidence mode")
    from larp.integration.contract import AuthorityError, authority
    try:
        authority(p)  # falsifier/statement authority (IDEA-031); defaults to SHADOW
    except AuthorityError as exc:
        raise ContractError(str(exc)) from exc
    if p["baseline"] not in ("DECLARED_EXPOSURE", "PRICE_MOMENTUM"):
        raise ContractError("Unknown baseline")
    for name in ("minimum_trade_units", "per_trade_cap_units", "cost_reserve_units",
                 "exit_gas_reserve_units", "dust_units", "quote_age_seconds",
                 "feature_age_seconds", "proposal_seconds", "slippage_bps", "impact_bps",
                 "price_threshold_bps", "review_sessions", "minimum_remaining_sessions"):
        integer(p[name])
    if p["proposal_seconds"] == 0 or p["review_sessions"] != 5:
        raise ContractError("Invalid expiry or declared review horizon")
    if p["per_trade_cap_units"] == 0:
        raise ContractError("Per-trade cap required")
    for name, maximum in (("operating_name_weight", Fraction(1, 5)),
                          ("operating_gross_weight", Fraction(4, 5)),
                          ("regime_gross_weight", Fraction(4, 5)),
                          ("rebalance_band", Fraction(1))):
        if fraction(p[name]) > maximum:
            raise ContractError("Configuration loosens declared cap")
    start, end, flatten, stop = [instant(p[n]) for n in
                               ("trade_after", "new_risk_end", "flatten_start", "signing_end")]
    if not start < end <= flatten < stop:
        raise ContractError("Terminal gates out of order")
    return p


def usable(observation, cutoff, max_age):
    try:
        times = [instant(observation[k]) for k in ("observed_at", "available_at", "close_at")]
        digest = observation["content_hash"]
        return (observation["quality"] == "VALID" and bool(observation["source_id"])
                and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
                and all(t <= cutoff for t in times)
                and 0 <= (cutoff - min(times)).total_seconds() <= max_age)
    except (KeyError, ContractError, TypeError):
        return False


def markets(snapshot, p):
    result = {}
    for m in snapshot.context.read().get("markets", []):
        symbol = m.get("symbol")
        if symbol not in snapshot.universe or symbol not in SYMBOLS or symbol in result:
            raise ContractError("Unknown or duplicate market entity")
        if m.get("schema") != "MarketObservation.v1":
            raise ContractError("Wrong market schema")
        integer(m["decimals"])
        if m["decimals"] > 30 or m["currency"] != "USDT" or m["money_scale"] != MONEY_SCALE:
            raise ContractError("Unsupported units/currency")
        if not m.get("token_id") or not m.get("underlying_id"):
            raise ContractError("Token/share identity required")
        integer(m["price_units"], 1)
        result[symbol] = m if usable(m, snapshot.observed_at, p["quote_age_seconds"]) else None
    return result


def value(units, m):
    return Fraction(units * m["price_units"], 10 ** m["decimals"])


def equity(ledger, market):
    total = Fraction(integer(ledger["cash_units"]))
    total += Fraction(integer(ledger["bnb_units"]) * integer(ledger["bnb_price_units"], 1),
                      10 ** integer(ledger["bnb_decimals"]))
    for symbol, position in ledger["positions"].items():
        units = integer(position["units"])
        if units:
            m = market.get(symbol)
            if m is None or position["decimals"] != m["decimals"]:
                raise ContractError("Held position lacks valid valuation/units")
            total += value(units, m)
    return floor(total)

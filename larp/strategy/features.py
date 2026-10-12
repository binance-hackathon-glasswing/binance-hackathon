"""Entity-keyed, point-in-time features. No price history or sizing fallback."""

from decimal import Decimal, ROUND_CEILING, localcontext
from fractions import Fraction

from larp.contracts import ContractError, Document
from .schema import instant, integer, ratio


def features(series: Document, *, cutoff, expected_entity, max_age_seconds,
             expected_instrument="UNDERLYING_SHARE", expected_token=None):
    d = series.read()
    base = {"schema": "PriceFeatures.v1", "entity_id": expected_entity,
            "cutoff": cutoff.isoformat(), "status": "MISSING", "reasons": [],
            "sigma_daily_ppb": None, "sigma_5session_ppb": None,
            "momentum_5": None, "eligible_closes": 0}
    required = ("source_id", "content_hash", "calendar_id", "corporate_action_version")
    if (d.get("schema") != "PriceSeries.v1" or d.get("entity_id") != expected_entity
            or any(not d.get(k) for k in required) or d.get("currency") != "USD"
            or d.get("instrument_kind") != expected_instrument
            or expected_token is not None and d.get("token_id") != expected_token
            or d.get("quality") != "VALID"):
        base["reasons"] = ["IDENTITY_UNITS_OR_PROVENANCE"]
        return Document.from_dict(base)
    integer(d["price_scale"], 1)
    rows = []
    seen = set()
    for bar in d.get("bars", []):
        close_at, available_at = instant(bar["close_at"]), instant(bar["available_at"])
        if close_at > cutoff or available_at > cutoff:
            continue
        sid = integer(bar["session_index"])
        if sid in seen:
            raise ContractError("Duplicate session observation")
        seen.add(sid)
        if (bar.get("corporate_action_version") != d["corporate_action_version"]
                or bar.get("quality") != "VALID"):
            base["reasons"] = ["CORPORATE_ACTION_OR_BAR_QUALITY"]
            return Document.from_dict(base)
        integer(bar["close_units"], 1)
        if available_at < close_at:
            raise ContractError("Bar available before close")
        rows.append(bar)
    rows.sort(key=lambda r: r["session_index"])
    base["eligible_closes"] = len(rows)
    if len(rows) < 61:
        base["reasons"] = ["INSUFFICIENT_60_SESSION_HISTORY"]
        return Document.from_dict(base)
    rows = rows[-61:]
    if any(b["session_index"] != a["session_index"] + 1
           or instant(b["close_at"]) <= instant(a["close_at"])
           for a, b in zip(rows, rows[1:])):
        base["reasons"] = ["MISSING_OR_UNORDERED_SESSION"]
        return Document.from_dict(base)
    if (cutoff - instant(rows[-1]["close_at"])).total_seconds() > max_age_seconds:
        base["reasons"] = ["STALE_HISTORY"]
        return Document.from_dict(base)
    with localcontext() as ctx:
        ctx.prec = 50
        returns = [(Decimal(b["close_units"]) / Decimal(a["close_units"])).ln()
                   for a, b in zip(rows, rows[1:])]
        mean = sum(returns) / Decimal(60)
        sigma = (sum((r - mean) ** 2 for r in returns) / Decimal(59)).sqrt()
        sigma5 = sigma * Decimal(5).sqrt()
        sd = int((sigma * 10**9).to_integral_value(rounding=ROUND_CEILING))
        sd5 = int((sigma5 * 10**9).to_integral_value(rounding=ROUND_CEILING))
    if sd5 <= 0:
        base["reasons"] = ["ZERO_VOLATILITY_NO_SIZING"]
        return Document.from_dict(base)
    base.update(status="VALID", reasons=[], sigma_daily_ppb=sd, sigma_5session_ppb=sd5,
                momentum_5=ratio(Fraction(rows[-1]["close_units"], rows[-6]["close_units"]) - 1),
                last_session=rows[-1]["session_index"], last_close_at=rows[-1]["close_at"],
                instrument_kind=d["instrument_kind"], price_scale=d["price_scale"],
                calendar_id=d["calendar_id"], corporate_action_version=d["corporate_action_version"],
                source_id=d["source_id"], content_hash=d["content_hash"])
    return Document.from_dict(base)


def declared_weight(feature):
    f = feature.read()
    if f["status"] != "VALID":
        raise ContractError("Declared sizing requires sufficient valid history")
    return min(Fraction(1, 5), Fraction(10**9, 200 * f["sigma_5session_ppb"]))

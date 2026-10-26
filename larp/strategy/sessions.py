"""I2 consumer: explicit token closes on a caller-supplied US session calendar.

The market owner supplies the frozen calendar (holidays included) and raw Web3
rows. No weekday calendar, fill-forward, share-price conversion or Ondo splice.
Web3 candle timestamps are explicitly declared as interval OPEN timestamps.
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from zoneinfo import ZoneInfo

from larp.contracts import ContractError, Document
from .schema import SYMBOLS, instant, integer

ET = ZoneInfo("America/New_York")


def _hash(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def token_sessions(capture: Document, calendar: Document, *, cutoff, price_scale=1_000_000,
                   allow_calendar_close=False, exact_prices=False):
    """TokenCandles.v1 + USRegularSessions.v1 -> PriceSeries.v1.

    Raw rows: [open, high, low, close, volume, timestamp_ms, tradeCount]. Missing
    trade intervals are missing data. A bar crossing 16:00 cannot stand for a
    16:00 close. Short (e.g. 13:00) calendar sessions stay missing under B3.
    Live history opts into exact rational scaling; legacy callers retain Decimal scaling.
    """
    d, cal = capture.read(), calendar.read()
    cutoff = instant(cutoff.isoformat())
    integer(price_scale, 1)
    if (d.get("schema") != "TokenCandles.v1" or d.get("symbol") not in SYMBOLS
            or not d.get("token_id") or not d.get("entity_id") or not d.get("source_id")
            or not _hash(d.get("content_hash")) or d.get("timestamp_kind") != "OPEN"
            or cal.get("schema") != "USRegularSessions.v1" or not cal.get("calendar_id")
            or not _hash(cal.get("content_hash"))):
        raise ContractError("Candle identity, timestamp convention and calendar provenance required")
    step = integer(d["bar_seconds"], 1)
    available = instant(d["available_at"])
    if available > cutoff:
        raise ContractError("Capture unavailable at cutoff")
    rows, seen = [], set()
    for raw in d["candles"]:
        if type(raw) is not list or len(raw) != 7:
            raise ContractError("Invalid Web3 candle row")
        try:
            ts = integer(int(raw[5])) if type(raw[5]) is str and raw[5].isdigit() else integer(raw[5])
        except (ContractError, ValueError):
            continue  # unusable rows leave an explicit missing session
        if ts in seen:
            raise ContractError("Duplicate raw candle")
        seen.add(ts)
        opened = instant("1970-01-01T00:00:00Z") + timedelta(milliseconds=ts)
        closed = opened + timedelta(seconds=step)
        try:
            if exact_prices:
                price = Decimal(str(raw[3]))
                if not price.is_finite() or price <= 0:
                    raise ValueError("nonpositive or nonrepresentable price")
                close = Fraction(price) * price_scale
            else:
                close = Decimal(str(raw[3])) * price_scale
                if not close.is_finite() or close <= 0:
                    raise ValueError("nonpositive or nonrepresentable price")
        except (InvalidOperation, ValueError) as exc:
            continue  # no fill-forward or fabricated close
        try:
            integer(raw[6], 1)
        except ContractError:
            continue  # no-trade intervals cannot supply an observed close
        rows.append((opened, closed, int(close)))
    rows.sort()
    if any(b[0] < a[1] for a, b in zip(rows, rows[1:])):
        raise ContractError("Overlapping raw intervals")
    first = rows[0][0].isoformat() if rows else None
    bars, missing, previous = [], [], None
    for session in cal["sessions"]:
        sid = integer(session["session_index"])
        opened, closed = instant(session["open_at"]), instant(session["close_at"])
        if previous is not None and (sid != previous[0] + 1 or opened <= previous[1]):
            raise ContractError("Calendar must retain consecutive, ordered session identities")
        previous = sid, closed
        local_open, local_close = opened.astimezone(ET), closed.astimezone(ET)
        if not opened < closed or local_open.date() != local_close.date():
            raise ContractError("Invalid regular session interval")
        if closed > cutoff:
            continue
        spans = [(a, b, price) for a, b, price in rows if a < closed and b > opened and b <= cutoff]
        complete = (local_open.hour == 9 and local_open.minute == 30
                    and ((local_close.hour == 16 and local_close.minute == 0)
                         or (allow_calendar_close and local_close.hour == 13 and local_close.minute == 0))
                    and local_open.second == local_close.second == 0
                    and bool(spans) and spans[0][0] <= opened
                    and spans[-1][1] == closed
                    and all(b[0] == a[1] for a, b in zip(spans, spans[1:])))
        if not complete:
            missing.append(sid)
            continue
        bars.append({"session_index": sid, "close_units": spans[-1][2],
                     "close_at": closed.isoformat(), "available_at": available.isoformat(),
                     "corporate_action_version": d["token_adjustment_version"], "quality": "VALID"})
    return Document.from_dict({"schema": "PriceSeries.v1", "entity_id": d["entity_id"],
        "token_id": d["token_id"], "symbol": d["symbol"], "instrument_kind": "TOKEN",
        "currency": "USD", "price_scale": price_scale, "source_id": d["source_id"],
        "content_hash": capture.digest("larp.token-session-input.v1"),
        "raw_content_hash": d["content_hash"], "calendar_id": cal["calendar_id"],
        "calendar_hash": cal["content_hash"], "corporate_action_version": d["token_adjustment_version"],
        "quality": "VALID", "first_candle_at": first, "missing_sessions": missing, "bars": bars})

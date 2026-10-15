"""Research estimators preserve clock-time adjacency and disclose gap coverage."""

import math
from datetime import datetime
from statistics import mean

BSTOCKS = ("NVDAB", "GOOGLB", "SKHYB", "TSLAB", "MSFTB")


def capture_cutoff_ms(capture, as_of_ms=None):
    """Saved-capture analysis has an explicit information cutoff, never wall time."""
    if as_of_ms is not None:
        if type(as_of_ms) is not int or as_of_ms < 0:
            raise ValueError("Capture cutoff must be nonnegative integer milliseconds")
        return as_of_ms
    captured = capture.get("report", {}).get("run_utc")
    if type(captured) is not str:
        raise ValueError("Capture cutoff missing; supply explicit as_of_ms")
    cutoff = datetime.fromisoformat(captured.replace("Z", "+00:00"))
    if cutoff.tzinfo is None:
        raise ValueError("Capture cutoff needs timezone")
    return int(cutoff.timestamp() * 1000)


def closed_bstock_bars(capture, bar, interval_ms, *, as_of_ms=None):
    """Read closed Web3 candles without moving rows across entities or versions.

    Identical pagination overlap is harmless; conflicting versions require an
    explicit reconciliation. A failed/missing response leaves that entity empty.
    Returned rows are OHLC, volume, trade count, keyed by interval-open time.
    """
    cutoff = capture_cutoff_ms(capture, as_of_ms)
    if type(interval_ms) is not int or interval_ms <= 0:
        raise ValueError("Positive candle interval required")
    result, current = {symbol: {} for symbol in BSTOCKS}, None
    for response in capture["raw"]:
        if response.get("endpoint") == "rwa/underlying-market":
            current = response.get("symbol")
            if current not in result:
                raise ValueError("Unknown entity marker")
        if response.get("bar") != bar:
            continue
        symbol = response.get("symbol", current)
        if symbol not in result:
            raise ValueError("Candle response lacks verified entity context")
        body = response.get("response", {})
        if type(body) is not dict or type(body.get("code")) is not int or body["code"] != 0:
            continue
        if type(body.get("data")) is not list:
            continue
        for candle in body["data"]:
            if type(candle) is not list or len(candle) != 7:
                raise ValueError("Malformed Web3 candle")
            stamp = candle[5]
            if type(stamp) is str and stamp.isdigit():
                stamp = int(stamp)
            if type(stamp) is not int or stamp < 0:
                raise ValueError("Candle timestamp must be integer milliseconds")
            if stamp + interval_ms > cutoff:
                continue
            if any(type(v) is bool for v in candle[:5]):
                raise ValueError("Boolean OHLC or volume is invalid")
            row = [float(v) for v in candle[:5]]
            if any(not math.isfinite(v) or v <= 0 for v in row[:4]) or not math.isfinite(row[4]) or row[4] < 0:
                raise ValueError("Finite positive OHLC and nonnegative volume required")
            trades = candle[6]
            if type(trades) is str and trades.isdigit():
                trades = int(trades)
            if trades is not None and (type(trades) is not int or trades < 0):
                raise ValueError("Invalid candle trade count")
            row.append(-1 if trades is None else trades)
            if stamp in result[symbol] and result[symbol][stamp] != row:
                raise ValueError("Conflicting versions of a saved candle")
            result[symbol][stamp] = row
    return {symbol: dict(sorted(rows.items())) for symbol, rows in result.items()}


def timed_returns(closes, interval):
    ts = sorted(closes)
    out, gaps = [], []
    for a, b in zip(ts, ts[1:]):
        if not all(math.isfinite(closes[t]) and closes[t] > 0 for t in (a, b)):
            raise ValueError("Finite positive prices required")
        ret = math.log(closes[b] / closes[a])
        (out if b - a == interval else gaps).append((b, ret, b - a))
    return out, gaps


def adjacent_pairs(returns, interval, category=None):
    """A return timestamp is its ending bar's start; retain both category tests."""
    ordered = sorted(returns)
    return [(a[1], b[1]) for a, b in zip(ordered, ordered[1:])
            if b[0] - a[0] == interval
            and (category is None or (category(a[0]) and category(b[0])))]


def roll_estimate(returns, interval, category=None):
    pairs = adjacent_pairs(returns, interval, category)
    if len(pairs) < 2:
        return float("nan"), float("nan"), len(pairs)
    x, y = zip(*pairs)
    mx, my = mean(x), mean(y)
    covariance = sum((a - mx) * (b - my) for a, b in pairs) / (len(pairs) - 1)
    vx = sum((a - mx)**2 for a in x)
    vy = sum((b - my)**2 for b in y)
    correlation = sum((a - mx) * (b - my) for a, b in pairs) / math.sqrt(vx * vy) if vx * vy else float("nan")
    return (2 * math.sqrt(-covariance) * 1e4 if covariance < 0 else float("nan"),
            correlation, len(pairs))


def ar_estimate(bars, interval):
    samples = []
    for a, b in zip(sorted(bars), sorted(bars)[1:]):
        if b - a != interval:
            continue
        if not all(math.isfinite(v) and v > 0 for v in
                   (bars[a][1], bars[a][2], bars[a][3], bars[b][1], bars[b][2])):
            raise ValueError("Finite positive OHLC required")
        close = math.log(bars[a][3])
        e0 = (math.log(bars[a][1]) + math.log(bars[a][2])) / 2
        e1 = (math.log(bars[b][1]) + math.log(bars[b][2])) / 2
        samples.append((close - e0) * (close - e1))
    estimate = 4 * mean(samples) if samples else float("nan")
    return math.sqrt(estimate) * 1e4 if estimate > 0 else float("nan"), len(samples)


def category_variance(closes, interval, categorize):
    returns, gaps = timed_returns(closes, interval)
    totals = {}
    for timestamp, r, _ in returns:
        category = categorize(timestamp)
        value = totals.setdefault(category, [0.0, 0])
        value[0] += r * r
        value[1] += 1
    return totals, gaps

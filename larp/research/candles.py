"""Research estimators preserve clock-time adjacency and disclose gap coverage."""

import math
from statistics import mean


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

"""EXP-007: does the basket trend guard cut drawdown at an acceptable cost? (rules in docs/ledger/EXP-007.md)

A (static 95%) vs B (trend guard: UP 95% / DOWN 60%) over every overlapping 10-session window of kit 1-hour token
bars, point-in-time inverse-volatility weights, both with the declared ladder. Reads the IDEA-106 snapshot
(tokens.json, underlying.json for NYSE session dates); prints a JSON report. Research only: no network.
Usage:  python -m tools.exp007.simulate --data DIR
"""
import argparse
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from statistics import mean, median, pstdev
from zoneinfo import ZoneInfo

import numpy as np

NAMES = ('GOOGLB', 'MSFTB', 'NVDAB', 'SKHYB', 'TSLAB')
ET = ZoneInfo('America/New_York')
HOUR_MS = 3_600_000
WINDOW, START_EQUITY, UP, DOWN, CAP, CUT_GROSS = 10, 200.0, 0.95, 0.60, 0.30, 0.40
LAST_SESSION = '2026-10-16'  # TRV-05: data ends at the Oct 16 close
CUTOFF_MS = int(datetime(2026, 10, 16, 20, tzinfo=timezone.utc).timestamp() * 1000)
SEED = 7  # fixed before the run (the criteria name no seed)


def _ms(day, hm):
    return int(datetime.fromisoformat(f'{day}T{hm}').replace(tzinfo=ET).timestamp() * 1000)


class Market:
    """Per session and name: the session close (last bar ending by 16:00 ET), the primary fill (open of the first
    1-hour bar starting at or after open + 30 min, else the next bar in the session, else the session close) and the
    session-close fill used by the execution sensitivity."""

    def __init__(self, tokens, sessions_all):
        bars = {k: sorted((int(r[5]), float(r[0]), float(r[3])) for r in tokens[k] if int(r[5]) + HOUR_MS <= CUTOFF_MS)
                for k in NAMES}
        self.first = {k: bars[k][0][0] for k in NAMES}
        start = min(self.first.values())
        self.sessions = [d for d in sessions_all if d <= LAST_SESSION and _ms(d, '16:00') > start + HOUR_MS]
        self.close, self.fill, self.fallbacks = {k: [] for k in NAMES}, {k: [] for k in NAMES}, dict(next_bar=0,
                                                                                                         close=0)
        for k in NAMES:
            starts = [b[0] for b in bars[k]]
            for d in self.sessions:
                close_ms, at = _ms(d, '16:00'), _ms(d, '10:00')
                i = bisect_right(starts, close_ms - HOUR_MS) - 1  # a missing session carries the last close
                c = bars[k][i][2] if i >= 0 else None
                self.close[k].append(c)
                j = bisect_left(starts, at)
                if j < len(starts) and starts[j] + HOUR_MS <= close_ms and starts[j] == at:
                    self.fill[k].append(bars[k][j][1])
                elif j < len(starts) and starts[j] + HOUR_MS <= close_ms:
                    self.fill[k].append(bars[k][j][1])
                    if c is not None:
                        self.fallbacks['next_bar'] += 1
                else:
                    self.fill[k].append(c)
                    if c is not None:
                        self.fallbacks['close'] += 1
        n = len(self.sessions)
        self.all_five = next(t for t in range(n) if all(self.close[k][t] is not None for k in NAMES))


def trend_states(market, n_avg=5, band=0.01):
    """State after each session close from the equal-weight basket index, starting UP; None before all five trade."""
    states, index, state = [None] * len(market.sessions), [], 'UP'
    for t in range(market.all_five, len(market.sessions)):
        if index:
            rets = [market.close[k][t] / market.close[k][t - 1] - 1 for k in NAMES]
            index.append(index[-1] * (1 + mean(rets)))
        else:
            index.append(1.0)
        if len(index) >= n_avg:
            r = index[-1] / mean(index[-n_avg:]) - 1
            state = 'UP' if r > band else 'DOWN' if r < -band else state
        states[t] = state
    return states


def weights(market, s):
    """IDEA-075 §5.1 at window start s from closes before s only: inverse sigma over the last 60 session log returns
    (>= 20, else the median sigma of the names that have 20), capped at 0.30 with the excess spread pro rata."""
    sig = {}
    for k in NAMES:
        px = [p for p in market.close[k][max(0, s - 61):s] if p is not None]
        rets = [math.log(b / a) for a, b in zip(px, px[1:])]
        sig[k] = pstdev(rets) if len(rets) >= 20 else None
    known = [v for v in sig.values() if v is not None]
    if not known:
        return None
    sig = {k: v if v is not None else median(known) for k, v in sig.items()}
    w = {k: 1 / max(v, 1e-12) for k, v in sig.items()}
    total = sum(w.values())
    w = {k: v / total for k, v in w.items()}
    for _ in NAMES:
        over = {k for k, v in w.items() if v > CAP + 1e-12}
        if not over:
            break
        excess = sum(w[k] - CAP for k in over)
        free = {k: v for k, v in w.items() if k not in over and v < CAP - 1e-12}
        for k in over:
            w[k] = CAP
        free_total = sum(free.values())
        for k, v in free.items():
            w[k] = v + excess * v / free_total
    return w


def window_starts(market, n_avg=5):
    """Windows need trend history (n_avg sessions with all five names before s), one name with 20 earlier
    sessions for sigma, and a fill session s + WINDOW for the flatten."""
    out = []
    for s in range(len(market.sessions) - WINDOW):
        if s - market.all_five >= n_avg and weights(market, s) is not None:
            out.append(s)
    return out


def run_window(market, s, guarded, states, bps, gas, fill='open', reset=False):
    """Build at session s's fill; after each close t = s..s+8 a level change trades at fill t+1; flatten at fill
    s+10. Drawdown and the ladder use session closes s..s+9. Returns (net return, max drawdown, level changes)."""
    c = bps / 10_000
    w = weights(market, s)
    price = market.fill if fill == 'open' else market.close
    cash, units = START_EQUITY, {k: 0.0 for k in NAMES}
    level = (UP if states[s - 1] == 'UP' else DOWN) if guarded else UP
    cut = block_dd = False
    peak, max_dd, changes = START_EQUITY, 0.0, 0

    def execute(target, t, allow_buys):
        nonlocal cash
        px = {k: price[k][t] for k in NAMES}
        eq = cash + sum(units[k] * px[k] for k in NAMES)
        legs = sorted(NAMES, key=lambda k: target[k] * eq - units[k] * px[k])  # sells first
        for k in legs:
            delta = target[k] * eq - units[k] * px[k]
            if abs(delta) < 1e-9 or (delta > 0 and not allow_buys):
                continue
            units[k] += delta / px[k]
            cash -= delta + abs(delta) * c + gas

    def gross_target():
        return min(level, CUT_GROSS) if cut else level

    execute({k: gross_target() * w[k] for k in NAMES}, s, True)
    prev_eq = START_EQUITY
    pending = None
    for t in range(s, s + WINDOW):
        if t > s and pending is not None:
            target, allow = pending
            execute(target, t, allow)
        pending = None
        eq = cash + sum(units[k] * market.close[k][t] for k in NAMES)
        peak = max(peak, eq)
        dd = 1 - eq / peak
        max_dd = max(max_dd, dd)
        block_day = eq / prev_eq - 1 <= -0.03
        block_dd = dd >= 0.08 or (block_dd and (not reset or dd >= 0.05))
        prev_eq = eq
        if t == s + WINDOW - 1:
            break
        reprice = False
        if dd >= 0.12 and not cut:
            cut, reprice = True, True
        if guarded:
            new = UP if states[t] == 'UP' else DOWN
            if new != level:
                level, reprice = new, True
                changes += 1
        if reprice:
            pending = ({k: gross_target() * w[k] for k in NAMES}, not (block_day or block_dd or cut))
    execute({k: 0.0 for k in NAMES}, s + WINDOW, False)
    final = cash
    return final / START_EQUITY - 1, max(max_dd, 1 - final / peak), changes


def block_bootstrap(values, block=10, n=10_000, seed=SEED):
    rng = np.random.default_rng(seed)
    d = np.asarray(values, dtype=float)
    starts = np.arange(len(d) - block + 1)
    k = math.ceil(len(d) / block)
    means = np.empty(n)
    for i in range(n):
        idx = (rng.choice(starts, k)[:, None] + np.arange(block)).ravel()[:len(d)]
        means[i] = d[idx].mean()
    return float(np.quantile(means, 0.05)), float(np.quantile(means, 0.95))


def evaluate(market, bps=25, gas=0.03, n_avg=5, band=0.01, fill='open', reset=False):
    states = trend_states(market, n_avg, band)
    starts = window_starts(market, n_avg)
    a = [run_window(market, s, False, states, bps, gas, fill, reset) for s in starts]
    b = [run_window(market, s, True, states, bps, gas, fill, reset) for s in starts]
    ret_d = [x[0] - y[0] for x, y in zip(b, a)]
    dd_d = [x[1] - y[1] for x, y in zip(b, a)]
    out = dict(windows=len(starts), non_overlapping=len(starts) // WINDOW,
               first_window=market.sessions[starts[0]], last_window_flatten=market.sessions[starts[-1] + WINDOW])
    for name, res in (('A_static', a), ('B_trend', b)):
        out[name] = dict(mean_ret_pct=100 * mean(x[0] for x in res), median_ret_pct=100 * median(x[0] for x in res),
                         mean_maxdd_pct=100 * mean(x[1] for x in res), median_maxdd_pct=100 * median(x[1] for x in res),
                         share_dd_ge_8=mean(x[1] >= 0.08 for x in res), mean_changes=mean(x[2] for x in res),
                         median_changes=median(x[2] for x in res))
    lo, hi = block_bootstrap(ret_d)
    dlo, dhi = block_bootstrap(dd_d)
    out['B_minus_A'] = dict(ret_mean_pct=100 * mean(ret_d), ret_ci90_pct=[100 * lo, 100 * hi],
                            maxdd_mean_pp=100 * mean(dd_d), maxdd_ci90_pp=[100 * dlo, 100 * dhi])
    out['share_DOWN_at_window_start'] = mean(states[s - 1] == 'DOWN' for s in starts)
    return out


def outcome(r):
    """The frozen decision rule at 25 bp; fewer than 5 non-overlapping windows is INCONCLUSIVE."""
    a, b = r['A_static'], r['B_trend']
    if r['non_overlapping'] < 5:
        return 'INCONCLUSIVE'
    if b['mean_maxdd_pct'] >= a['mean_maxdd_pct'] or b['mean_ret_pct'] < a['mean_ret_pct'] - 1.0:
        return 'NOT SUPPORTED'
    if (b['mean_maxdd_pct'] <= a['mean_maxdd_pct'] - 1.0 and b['mean_ret_pct'] >= a['mean_ret_pct'] - 0.5
            and b['median_changes'] <= 2):
        return 'SUPPORTED'
    return 'INCONCLUSIVE'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--data', required=True)
    args = parser.parse_args(argv)
    data = Path(args.data).expanduser()
    tokens = json.loads((data / 'tokens.json').read_text())
    underlying = json.loads((data / 'underlying.json').read_text())
    days = sorted({datetime.fromtimestamp(t, timezone.utc).astimezone(ET).date().isoformat()
                   for t, _ in underlying['NVDAB']['rows']})
    market = Market(tokens, days)
    primary = evaluate(market)
    report = dict(experiment='EXP-007', sessions=[market.sessions[0], market.sessions[-1], len(market.sessions)],
                  first_session_all_five=market.sessions[market.all_five], fill_fallbacks=market.fallbacks,
                  primary_25bp=primary, outcome=outcome(primary))
    report['sensitivity_reported_only'] = dict(
        cost_50bp=evaluate(market, bps=50), avg_3=evaluate(market, n_avg=3), avg_10=evaluate(market, n_avg=10),
        band_0p5=evaluate(market, band=0.005), band_2=evaluate(market, band=0.02),
        fill_next_close=evaluate(market, fill='close'), o1_reset_below_5=evaluate(market, reset=True))
    print(json.dumps(report, indent=1, default=lambda x: round(x, 4) if isinstance(x, float) else str(x)))


if __name__ == '__main__':
    main()

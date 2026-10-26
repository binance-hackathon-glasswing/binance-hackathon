"""IDEA-106 S6 offline backtest: S6 vs FS1-STATIC vs CONC3 over 10-session windows (rules in docs/ledger/IDEA-106.md).

Reads the snapshot written by fetch.py (data/idea106, git-ignored); prints a JSON report. Research only: no network,
no credentials, no runtime code. S6 is EXPERIMENTAL and must not be deployed (IDEA-106 "DO NOT DEPLOY").
Usage:  python -m tools.idea106.simulate [--data DIR]
"""
import argparse
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from itertools import combinations
import json
import math
from pathlib import Path
from statistics import mean, median, pstdev
from zoneinfo import ZoneInfo

import numpy as np

DATA = Path(__file__).resolve().parents[2] / 'data' / 'idea106'
NAMES = ('GOOGLB', 'MSFTB', 'NVDAB', 'SKHYB', 'TSLAB')
ET = ZoneInfo('America/New_York')
HOUR_MS = 3_600_000
WINDOW, START_EQUITY, GROSS = 10, 200.0, 0.95
MIN_TRADE, LEG_CAP = 18.637, 38.2
LAST_SESSION = '2026-10-26'
P_FIRST_SESSION = '2019-01-02'
# Central per side = round-trip spread / 2 + 1 bp impact + 2 bp slippage (FS1 quote summary, IDEA-106 Economics).
SPREAD_RT = dict(GOOGLB=3, MSFTB=17, NVDAB=4, SKHYB=2, TSLAB=5)
CENTRAL_BPS = {k: v / 2 + 3 for k, v in SPREAD_RT.items()}
COSTS = dict(central=(CENTRAL_BPS, 0.058), team=(25, 0.03), stress=(50, 0.03), gas_cap=(CENTRAL_BPS, 0.277))
CENTRAL_PER_SIDE = mean(CENTRAL_BPS.values())


class Market:
    """Point-in-time view: per session a fill time and prices, the score close, and marks up to each fill."""

    def __init__(self, sessions, fills, closes, carried, marks, fallbacks=None):
        self.sessions, self.fills, self.closes, self.carried = sessions, fills, closes, carried
        self.marks, self.fallbacks = marks, fallbacks or {}  # marks[t]: [(ms, prices)] after fill t-1 up to fill t


def _end_series(rows):
    bars = sorted((int(r[5]), float(r[3])) for r in rows)
    return [b[0] + HOUR_MS for b in bars], [b[1] for b in bars], [b[0] for b in bars]


def token_market(tokens, sessions_all):
    """T: kit 1-hour bars (OPEN-labelled, IDEA-105). Close = last bar ending at or before 16:00 ET; fill = close of the
    first full bar starting at or after open + 30 min, else the next bar in the session, else the session close."""
    series = {k: _end_series(tokens[k]) for k in NAMES}
    first = max(series[k][2][0] for k in NAMES)
    sessions = [d for d in sessions_all if datetime.fromisoformat(d + 'T16:00').replace(tzinfo=ET).timestamp() * 1000
                > first + HOUR_MS and d <= LAST_SESSION]
    fills, closes, carried, marks = [], [], [], []
    fallbacks = dict(next_bar=0, session_close=0)
    previous_fill = None
    for d in sessions:
        open_ms = int(datetime.fromisoformat(d + 'T09:30').replace(tzinfo=ET).timestamp() * 1000)
        close_ms = int(datetime.fromisoformat(d + 'T16:00').replace(tzinfo=ET).timestamp() * 1000)
        fill_ms = open_ms + 30 * 60_000 + HOUR_MS
        close_px, carry, fill_px = {}, {}, {}
        for k in NAMES:
            ends, px, starts = series[k]
            i = bisect_right(ends, close_ms) - 1
            close_px[k] = px[i] if i >= 0 else None
            carry[k] = i < 0 or datetime.fromtimestamp(starts[i] / 1000, ET).date().isoformat() != d
            j = bisect_right(starts, open_ms + 30 * 60_000 - 1)
            if j < len(starts) and ends[j] <= close_ms and starts[j] == open_ms + 30 * 60_000:
                fill_px[k] = px[j]
            elif j < len(starts) and ends[j] <= close_ms:
                fill_px[k] = px[j]
                fallbacks['next_bar'] += 1
            else:
                fill_px[k] = close_px[k]
                fallbacks['session_close'] += 1
        span = []
        if previous_fill is not None:
            for h in range(previous_fill + HOUR_MS, fill_ms, HOUR_MS):
                span.append((h, {k: _at(series[k], h) for k in NAMES}))
        fills.append((fill_ms, fill_px))
        closes.append(close_px)
        carried.append(carry)
        marks.append(span)
        previous_fill = fill_ms
    return Market(sessions, fills, closes, carried, marks, fallbacks)


def _at(series, ms):
    ends, px, _ = series
    i = bisect_right(ends, ms) - 1
    return px[i] if i >= 0 else None


def underlying_sessions(underlying):
    days = sorted({datetime.fromtimestamp(t, timezone.utc).astimezone(ET).date().isoformat()
                   for t, _ in underlying['NVDAB']['rows']})
    return [d for d in days if d <= LAST_SESSION]


def proxy_market(underlying):
    """P: underlying daily closes (research-only, D-09); signal at close t-1, fill at close t, marks at closes."""
    sessions = [d for d in underlying_sessions(underlying) if d >= P_FIRST_SESSION]
    closes = {k: [] for k in NAMES}
    for k in NAMES:
        rows = underlying[k]
        tz = ZoneInfo(rows['tz'])
        by_day = {datetime.fromtimestamp(t, timezone.utc).astimezone(tz).date().isoformat(): c for t, c in rows['rows']}
        keys, last, i = sorted(by_day), None, 0
        for d in sessions:  # latest local close on or before the US session date (only SKHYB differs)
            while i < len(keys) and keys[i] <= d:
                last = by_day[keys[i]]
                i += 1
            closes[k].append(last)
    fills, cl, carried, marks = [], [], [], []
    for t, d in enumerate(sessions):
        px = {k: closes[k][t] for k in NAMES}
        fills.append((t, px))
        cl.append(px)
        carried.append({k: False for k in NAMES})
        marks.append([])
    return Market(sessions, fills, cl, carried, marks)


def scores(market, t, lookback, names):
    """Score after session t's close: ln(C_t / C_{t-L}); a name with more than 2 carried closes is not eligible."""
    out = {}
    for k in names:
        a, b = market.closes[t - lookback][k], market.closes[t][k]
        if a and b and sum(market.carried[u][k] for u in range(t - lookback + 1, t + 1)) <= 2:
            out[k] = math.log(b / a)
    return out


def run_window(market, s, arm, cost):
    """One 10-session window: build at fill s, decide at fills s+1..s+8 on the previous close, flatten at fill s+9.
    arm: dict(kind='S6'|'STATIC', names, k, lookback, margin, budget, reverse, static_names)."""
    bps, gas = cost
    side = (lambda k: bps[k] / 10_000) if isinstance(bps, dict) else (lambda k: bps / 10_000)
    names = arm['names']
    k_held = arm['k']
    target_w = GROSS / k_held
    name_line = arm.get('name_line', 0.40 if k_held == 3 else target_w + 0.0833)
    cash, units = START_EQUITY, {k: 0.0 for k in names}
    state = dict(cost=0.0, swaps=0, min_leg=math.inf, cut=False, peak=START_EQUITY, max_dd=0.0,
                 block_dd=False, day=None, day_eq=START_EQUITY, block_day=False)
    held, swaps = set(), []

    def equity(prices):
        return cash + sum(units[k] * prices[k] for k in names)

    def trade(k, notional, price, discretionary=True):
        nonlocal cash
        legs = max(1, math.ceil(abs(notional) / LEG_CAP))
        if discretionary:
            state['min_leg'] = min(state['min_leg'], abs(notional) / legs)
        c = abs(notional) * side(k) + legs * gas
        if notional > 0:
            notional = min(notional, max(0.0, (cash - legs * gas) / (1 + side(k))))
            c = notional * side(k) + legs * gas
            if notional < MIN_TRADE:
                return 0.0
        units[k] += notional / price
        cash -= notional + c
        state['cost'] += c
        return c

    def mark(ms, prices):
        eq = equity(prices)
        day = datetime.fromtimestamp(ms / 1000, timezone.utc).date() if ms > 10**9 else ms
        if day != state['day']:
            state['day'], state['day_eq'], state['block_day'] = day, eq, False
        if eq / state['day_eq'] - 1 <= -0.03:
            state['block_day'] = True
        state['peak'] = max(state['peak'], eq)
        dd = 1 - eq / state['peak']
        state['max_dd'] = max(state['max_dd'], dd)
        if dd >= 0.08:
            state['block_dd'] = True
        elif dd < 0.05:
            state['block_dd'] = False
        if dd >= 0.12 and not state['cut']:
            state['cut'] = True
            gross = sum(units[k] * prices[k] for k in names) / eq
            if gross > 0.40:
                for k in names:
                    if units[k]:
                        trade(k, -units[k] * prices[k] * (1 - 0.40 / gross), prices[k], False)
        return eq

    def buys_ok():
        return not (state['block_day'] or state['block_dd'] or state['cut'])

    def to_target(k, prices, eq, w):
        delta = w * eq - units[k] * prices[k]
        if abs(delta) >= MIN_TRADE:
            trade(k, delta, prices[k])

    for t in range(s, s + WINDOW):
        for ms, prices in market.marks[t] if t > s else ():
            if all(prices[k] for k in names):
                mark(ms, prices)
        fill_ms, prices = market.fills[t]
        eq = mark(fill_ms, prices)
        if t == s + WINDOW - 1:
            for k in names:
                if units[k]:
                    trade(k, -units[k] * prices[k], prices[k], False)
            for sw in swaps:
                if sw['end_px'] is None:
                    sw['end_px'] = (prices[sw['in']], prices[sw['out']])
            break
        if t == s:
            if arm['kind'] == 'STATIC':
                held = set(arm['static_names'])
            else:
                sc = scores(market, t - 1, arm['lookback'], names)
                order = sorted(sc, key=lambda k: (-sc[k] if not arm['reverse'] else sc[k], k))
                held = set(order[:k_held])
            for k in sorted(held):
                to_target(k, prices, eq, target_w)
            continue
        if arm['kind'] == 'S6' and state['swaps'] < arm['budget'] and buys_ok():
            sc = scores(market, t - 1, arm['lookback'], names)
            sign = -1 if arm['reverse'] else 1
            inside = [k for k in held if k in sc]
            outside = [k for k in names if k not in held and k in sc]
            if inside and outside:
                worst = min(inside, key=lambda k: (sign * sc[k], k))
                best = max(outside, key=lambda k: (sign * sc[k], k))
                if sign * (sc[best] - sc[worst]) > arm['margin']:
                    before = state['cost']
                    position = units[worst] * prices[worst]
                    trade(worst, -position, prices[worst])
                    held.discard(worst)
                    eq = equity(prices)
                    to_target(best, prices, eq, target_w)
                    held.add(best)
                    state['swaps'] += 1
                    for sw in swaps:
                        if sw['in'] == worst and sw['end_px'] is None:
                            sw['end_px'] = (prices[sw['in']], prices[sw['out']])
                    swaps.append(dict(**{'in': best, 'out': worst}, start_px=(prices[best], prices[worst]),
                                      end_px=None, cost_frac=(state['cost'] - before) / max(position, 1e-9)))
        eq = equity(prices)
        for k in sorted(held):
            if units[k] * prices[k] / eq > name_line:
                to_target(k, prices, eq, target_w)
        gross = sum(units[k] * prices[k] for k in names) / eq
        if gross < GROSS - 0.05 and buys_ok():
            for k in sorted(held):
                if units[k] * prices[k] / eq < target_w:
                    to_target(k, prices, eq, target_w)
    final = cash
    rel = [(sw['end_px'][0] / sw['start_px'][0]) - (sw['end_px'][1] / sw['start_px'][1]) - sw['cost_frac']
           - 0.005 for sw in swaps if sw['end_px']]
    return dict(ret=final / START_EQUITY - 1, max_dd=state['max_dd'], swaps=state['swaps'], cost=state['cost'],
                min_leg=state['min_leg'], swap_excess=rel)


def block_bootstrap(values, block=10, n=10_000, seed=106):
    rng = np.random.default_rng(seed)
    d = np.asarray(values, dtype=float)
    if len(d) < block:
        return float('nan'), float('nan')
    starts = np.arange(len(d) - block + 1)
    k = math.ceil(len(d) / block)
    means = np.empty(n)
    for i in range(n):
        idx = (rng.choice(starts, k)[:, None] + np.arange(block)).ravel()[:len(d)]
        means[i] = d[idx].mean()
    return float(np.quantile(means, 0.05)), float(np.quantile(means, 0.95))


def s6(names=NAMES, **over):
    return dict(dict(kind='S6', names=tuple(names), k=3, lookback=10, margin=0.015, budget=6, reverse=False), **over)


def static(held, names=NAMES):
    return dict(kind='STATIC', names=tuple(names), k=len(held), static_names=tuple(held), lookback=10,
                name_line=0.35 if len(held) == 5 else 0.40 if len(held) == 3 else GROSS / len(held) + 0.11)


def window_starts(market, lookback=10):
    return list(range(lookback + 1, len(market.sessions) - WINDOW + 1))


def runs(market, arm, cost, starts):
    return [run_window(market, s, arm, cost) for s in starts]


def summary(results):
    r = [x['ret'] for x in results]
    dd = [x['max_dd'] for x in results]
    return dict(mean_ret_pct=100 * mean(r), median_ret_pct=100 * median(r), sd_ret_pct=100 * pstdev(r),
                share_ret_gt_0=mean(x > 0 for x in r), mean_maxdd_pct=100 * mean(dd), median_maxdd_pct=100 * median(dd),
                share_dd_ge_8=mean(x >= 0.08 for x in dd), share_dd_ge_12=mean(x >= 0.12 for x in dd),
                mean_swaps=mean(x['swaps'] for x in results), mean_cost_usdt=mean(x['cost'] for x in results))


def conc3(market, cost, starts, names=NAMES):
    books = [runs(market, static(c, names), cost, starts) for c in combinations(names, 3)]
    return [mean(b[i]['ret'] for b in books) for i in range(len(starts))]


def diff_stats(a, b):
    d = [x - y for x, y in zip(a, b)]
    lo, hi = block_bootstrap(d)
    return dict(mean_pct=100 * mean(d), ci90_pct=[100 * lo, 100 * hi], share_ahead=mean(x > 0 for x in d)), d, lo, hi


def break_even(market, starts, fs1_arm=None):
    fs1_arm = fs1_arm or static(NAMES)

    def gap(b):
        cost = (b, 0.058)
        return mean(x['ret'] - y['ret'] for x, y in zip(runs(market, s6(), cost, starts),
                                                          runs(market, fs1_arm, cost, starts)))
    lo, hi = 0.0, 500.0
    if gap(lo) <= 0:
        return 0.0
    if gap(hi) > 0:
        return hi
    for _ in range(25):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap(mid) > 0 else (lo, mid)
    return lo


def evaluate_t(market):
    starts = window_starts(market)
    central = COSTS['central']
    s6_c = runs(market, s6(), central, starts)
    fs1_c = runs(market, static(NAMES), central, starts)
    c3 = conc3(market, central, starts)
    out = dict(windows=len(starts), non_overlapping=len(starts) // WINDOW,
               first_window=market.sessions[starts[0]] if starts else None,
               last_window_end=market.sessions[starts[-1] + WINDOW - 1] if starts else None,
               sessions=[market.sessions[0], market.sessions[-1], len(market.sessions)],
               fill_fallbacks=market.fallbacks)
    out['S6'], out['FS1_STATIC'] = summary(s6_c), summary(fs1_c)
    out['CONC3_mean_ret_pct'] = 100 * mean(c3)
    b1, d1, lo1, hi1 = diff_stats([x['ret'] for x in s6_c], [x['ret'] for x in fs1_c])
    s_lo, s_hi = block_bootstrap([x['ret'] for x in s6_c])
    out['S6_minus_FS1'] = b1
    out['S6_ret_ci90_pct'] = [100 * s_lo, 100 * s_hi]
    b2, _, lo2, _ = diff_stats([x['ret'] for x in s6_c], c3)
    out['S6_minus_CONC3'] = b2
    costs = {}
    for name, cost in COSTS.items():
        a, b = runs(market, s6(), cost, starts), runs(market, static(NAMES), cost, starts)
        costs[name] = dict(S6_mean_ret_pct=100 * mean(x['ret'] for x in a),
                           FS1_mean_ret_pct=100 * mean(x['ret'] for x in b),
                           diff_mean_pct=100 * mean(x['ret'] - y['ret'] for x, y in zip(a, b)))
    out['costs'] = costs
    be = break_even(market, starts)
    out['break_even_per_side_bps'] = be
    non = starts[::WINDOW]
    idx = [starts.index(s) for s in non]
    share_non = mean(d1[i] > 0 for i in idx) if idx else float('nan')
    loo = {}
    for drop in NAMES:
        rest = tuple(k for k in NAMES if k != drop)
        a = runs(market, s6(rest), central, starts)
        b = runs(market, static(rest, rest), central, starts)
        loo[drop] = 100 * mean(x['ret'] - y['ret'] for x, y in zip(a, b))
    out['B6'] = dict(share_non_overlapping_ahead=share_non, leave_one_out_diff_mean_pct=loo)
    excess = [e for x in s6_c for e in x['swap_excess']]
    out['B7'] = dict(swaps=len(excess), mean_excess_over_cost_plus_50bp_pct=100 * mean(excess) if excess else None)
    incr = mean(x['cost'] - y['cost'] for x, y in zip(s6_c, fs1_c)) / START_EQUITY
    min_leg = min(x['min_leg'] for x in s6_c)
    variants = {}
    for name, arm in dict(K2=s6(k=2), L5=s6(lookback=5), L20=s6(lookback=20), REV3=s6(reverse=True),
                          margin0=s6(margin=0.0), no_budget=s6(budget=10**9)).items():
        st = window_starts(market, arm['lookback'])
        a, b = runs(market, arm, central, st), runs(market, static(NAMES), central, st)
        variants[name] = dict(windows=len(st), mean_ret_pct=100 * mean(x['ret'] for x in a),
                              diff_vs_FS1_mean_pct=100 * mean(x['ret'] - y['ret'] for x, y in zip(a, b)),
                              mean_maxdd_pct=100 * mean(x['max_dd'] for x in a))
    out['variants_reported_only'] = variants
    s, f = out['S6'], out['FS1_STATIC']
    gates = dict(
        B1=b1['mean_pct'] > 0 and lo1 > 0 and s_lo > 0,
        B2=b2['mean_pct'] > 0 and lo2 > 0,
        B3=costs['team']['diff_mean_pct'] > 0 and be >= 2 * CENTRAL_PER_SIDE,
        B4=(s['share_dd_ge_8'] <= f['share_dd_ge_8'] + 0.05 and s['share_dd_ge_8'] <= 0.15
            and s['share_dd_ge_12'] <= 0.05 and s['median_maxdd_pct'] <= 1.5 * f['median_maxdd_pct']),
        B5=s['mean_swaps'] <= 6 and incr <= 0.015 and min_leg >= MIN_TRADE,
        B6=share_non >= 0.6 and sum(v > 0 for v in loo.values()) >= 4,
        B7=bool(excess) and mean(excess) > 0)
    out['B5'] = dict(incremental_cost_pct_equity=100 * incr, min_discretionary_leg_usdt=min_leg)
    out['gates'] = gates
    return out, (hi1, s_hi)


def evaluate_p(market):
    starts = [s for s in window_starts(market)]
    central = COSTS['central']
    a, b = runs(market, s6(), central, starts), runs(market, static(NAMES), central, starts)
    stats, _, lo, hi = diff_stats([x['ret'] for x in a], [x['ret'] for x in b])
    s_lo, s_hi = block_bootstrap([x['ret'] for x in a])
    return dict(windows=len(starts), first_window=market.sessions[starts[0]], S6=summary(a), FS1_STATIC=summary(b),
                S6_minus_FS1=stats, S6_ret_ci90_pct=[100 * s_lo, 100 * s_hi], B8=hi >= 0), (hi, s_hi)


def outcome(t, t_hi, p, p_hi):
    gates = dict(t['gates'], B8=p['B8'])
    if t_hi[0] < 0 or p_hi[0] < 0 or t_hi[1] < 0 or not gates['B4']:
        return 'NOT SUPPORTED', gates
    if all(gates.values()):
        return 'SUPPORTED', gates
    return 'INCONCLUSIVE', gates


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--data', default=str(DATA))
    args = parser.parse_args(argv)
    data = Path(args.data)
    tokens = json.loads((data / 'tokens.json').read_text())
    underlying = json.loads((data / 'underlying.json').read_text())
    t_market = token_market(tokens, underlying_sessions(underlying))
    p_market = proxy_market(underlying)
    t, t_hi = evaluate_t(t_market)
    p, p_hi = evaluate_p(p_market)
    verdict, gates = outcome(t, t_hi, p, p_hi)
    print(json.dumps(dict(idea='IDEA-106', T=t, P=p, gates=gates, outcome=verdict), indent=1,
                     default=lambda x: round(x, 4) if isinstance(x, float) else str(x)))


if __name__ == '__main__':
    main()

"""IDEA-107 S7 offline backtest: build-time residual-reversal tilt vs FS1-STATIC vs TILT-AVG (rules: docs/ledger/IDEA-107.md).

Reuses the IDEA-106 snapshot readers, fill/mark conventions, costs and bootstrap (tools/idea106/simulate.py). Research
only: no network, no credentials, no runtime code. S7 is EXPERIMENTAL and must not be deployed (IDEA-107 "DO NOT DEPLOY").
Usage:  python -m tools.idea107.simulate --data ~/larp-idea106/snapshot-20261026
"""
import argparse
from datetime import datetime, timezone
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
from statistics import mean, median, pstdev, stdev

from tools.idea106 import simulate as s6sim

NAMES = s6sim.NAMES
WINDOW, START_EQUITY, GROSS = s6sim.WINDOW, s6sim.START_EQUITY, s6sim.GROSS
MIN_TRADE, LEG_CAP = s6sim.MIN_TRADE, s6sim.LEG_CAP
COSTS = s6sim.COSTS
CENTRAL_BPS, CENTRAL_GAS = COSTS['central']
FORM, VOL, MAX_CARRIED = 5, 20, 2
BASE_W = GROSS / 5          # 19%
OVER_W = 1.5 * BASE_W       # 28.5%
NAME_LINE = 0.35
FIRST_START = VOL + 1       # 21 closes before the build
SEED = 107
P1_LAST, P2_FIRST = '2022-12-30', '2023-01-03'
HASHES = {'tokens.json': '61f24e23abf70b7b8110cd460d1a3069d3d052b9e1b2ab17d01ce1c555ccc05c',
          'underlying.json': '19dd7f70814a3156a685c7b5d6373bc6fce57c9202f23394eca5896e9933dbe3'}


def zscores(market, t, names=NAMES, form=FORM, vol=VOL, residual=True, scale=True, exclude=()):
    """Signal after session t's close, from closes t - vol .. t only. Returns {name: z} for eligible names."""
    if t - vol < 0:
        return {}
    elig = []
    for k in names:
        if k in exclude:
            continue
        cl = [market.closes[u][k] for u in range(t - vol, t + 1)]
        if any(c is None or c <= 0 for c in cl):
            continue
        if sum(bool(market.carried[u][k]) for u in range(t - vol + 1, t + 1)) > MAX_CARRIED:
            continue
        elig.append(k)
    if not elig:
        return {}
    r = {k: [math.log(market.closes[u][k] / market.closes[u - 1][k]) for u in range(t - vol + 1, t + 1)] for k in elig}
    basket = [mean(r[k][i] for k in elig) for i in range(vol)]
    e = {k: [r[k][i] - basket[i] for i in range(vol)] if residual else r[k] for k in elig}
    out = {}
    for k in elig:
        formation = sum(e[k][vol - form:])
        if not scale:
            out[k] = formation
            continue
        sd = stdev(e[k])
        out[k] = formation / (sd * math.sqrt(form)) if sd > 0 else 0.0
    return out


def targets_from_z(z, names=NAMES, shape='S7'):
    """Rank by (z, name). S7: two lowest 28.5%, highest 0%, rest 19%. Fewer than 3 ranked names: all 19%."""
    w = {k: BASE_W for k in names}
    order = sorted(z, key=lambda k: (z[k], k))
    if len(order) < 3:
        return w
    if shape == 'S7':
        w[order[0]] = w[order[1]] = OVER_W
        w[order[-1]] = 0.0
    elif shape == 'MIRROR':
        w[order[-1]] = w[order[-2]] = OVER_W
        w[order[0]] = 0.0
    elif shape == 'TILT1':
        w[order[0]] = OVER_W
        w[order[-1]] = 0.5 * BASE_W
    else:
        raise ValueError(shape)
    return w


def equal_targets(names=NAMES):
    return {k: BASE_W for k in names}


def run_book(market, s, targets, cost):
    """One 10-session window with fixed per-name targets: build at fill s, hold (hard line, top-up band, ladder) through
    fills s+1..s+8, flatten at fill s+9. Mechanics identical to IDEA-106's FS1-STATIC path."""
    bps, gas = cost
    side = (lambda k: bps[k] / 10_000) if isinstance(bps, dict) else (lambda k: bps / 10_000)
    names = NAMES
    cash, units = START_EQUITY, {k: 0.0 for k in names}
    state = dict(cost=0.0, legs=0, min_leg=math.inf, cut=False, peak=START_EQUITY, max_dd=0.0,
                 block_dd=False, day=None, day_eq=START_EQUITY, block_day=False)
    held = [k for k in sorted(names) if targets[k] > 0]

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
        state['legs'] += legs
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
            break
        if t == s:
            for k in held:
                to_target(k, prices, eq, targets[k])
            continue
        eq = equity(prices)
        for k in held:
            if units[k] * prices[k] / eq > NAME_LINE:
                to_target(k, prices, eq, targets[k])
        gross = sum(units[k] * prices[k] for k in names) / eq
        if gross < GROSS - 0.05 and buys_ok():
            for k in held:
                if units[k] * prices[k] / eq < targets[k]:
                    to_target(k, prices, eq, targets[k])
    return dict(ret=cash / START_EQUITY - 1, max_dd=state['max_dd'], cost=state['cost'], legs=state['legs'],
                min_leg=state['min_leg'])


def s7_targets(market, s, shape='S7', **signal):
    return targets_from_z(zscores(market, s - 1, **signal), shape=shape)


def window_starts(market):
    return list(range(FIRST_START, len(market.sessions) - WINDOW + 1))


def run_arm(market, starts, cost, shape='S7', **signal):
    return [run_book(market, s, s7_targets(market, s, shape, **signal), cost) for s in starts]


def run_equal(market, starts, cost):
    return [run_book(market, s, equal_targets(), cost) for s in starts]


def tilt_books():
    out = []
    for zero in NAMES:
        rest = [k for k in NAMES if k != zero]
        for over in combinations(rest, 2):
            w = {k: BASE_W for k in NAMES}
            w[zero] = 0.0
            for k in over:
                w[k] = OVER_W
            out.append(w)
    return out


def tilt_avg(market, starts, cost):
    books = [[run_book(market, s, w, cost)['ret'] for s in starts] for w in tilt_books()]
    return [mean(b[i] for b in books) for i in range(len(starts))]


def summary(results):
    r = [x['ret'] for x in results]
    dd = [x['max_dd'] for x in results]
    return dict(mean_ret_pct=100 * mean(r), median_ret_pct=100 * median(r), sd_ret_pct=100 * pstdev(r),
                share_ret_gt_0=mean(x > 0 for x in r), mean_maxdd_pct=100 * mean(dd), median_maxdd_pct=100 * median(dd),
                share_dd_ge_8=mean(x >= 0.08 for x in dd), share_dd_ge_12=mean(x >= 0.12 for x in dd),
                mean_legs=mean(x['legs'] for x in results), mean_cost_usdt=mean(x['cost'] for x in results),
                min_discretionary_leg_usdt=min(x['min_leg'] for x in results))


def diff(a, b):
    d = [x - y for x, y in zip(a, b)]
    lo, hi = s6sim.block_bootstrap(d, seed=SEED)
    return dict(mean_pct=100 * mean(d), ci90_pct=[100 * lo, 100 * hi], share_ahead=mean(x > 0 for x in d),
                n=len(d)), d, lo, hi


def dd_gate(s, f):
    return (s['share_dd_ge_8'] <= f['share_dd_ge_8'] + 0.03 and s['share_dd_ge_12'] <= f['share_dd_ge_12'] + 0.02
            and s['median_maxdd_pct'] <= 1.25 * f['median_maxdd_pct'])


def impl_gate(s, f, incr):
    return s['min_discretionary_leg_usdt'] >= MIN_TRADE and s['mean_legs'] <= f['mean_legs'] + 2 and incr <= 0.0015


def break_even_gas(market, starts):
    def gap(g):
        cost = (CENTRAL_BPS, g)
        return mean(x['ret'] - y['ret'] for x, y in zip(run_arm(market, starts, cost), run_equal(market, starts, cost)))
    lo, hi = 0.0, 5.0
    if gap(lo) <= 0:
        return 0.0
    if gap(hi) > 0:
        return hi
    for _ in range(20):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap(mid) > 0 else (lo, mid)
    return lo


VARIANTS = dict(MIRROR=dict(shape='MIRROR'), RAW=dict(residual=False, scale=False), F10=dict(form=10),
                F20=dict(form=20), TILT1=dict(shape='TILT1'))


def variants(market, starts, fs1, extra=()):
    out = {}
    for name, kw in list(VARIANTS.items()) + list(extra):
        a = run_arm(market, starts, COSTS['central'], **kw)
        out[name] = dict(mean_ret_pct=100 * mean(x['ret'] for x in a),
                         diff_vs_FS1_mean_pct=100 * mean(x['ret'] - y['ret'] for x, y in zip(a, fs1)),
                         mean_maxdd_pct=100 * mean(x['max_dd'] for x in a))
    return out


def evaluate(market, label, decisive):
    starts = window_starts(market)
    central = COSTS['central']
    s7 = run_arm(market, starts, central)
    fs1 = run_equal(market, starts, central)
    out = dict(windows=len(starts), non_overlapping=len(starts[::WINDOW]),
               first_build=market.sessions[starts[0]], last_flatten=market.sessions[starts[-1] + WINDOW - 1],
               sessions=[market.sessions[0], market.sessions[-1], len(market.sessions)])
    if market.fallbacks:
        out['fill_fallbacks'] = market.fallbacks
    out['S7'], out['FS1_STATIC'] = summary(s7), summary(fs1)
    d, dv, lo, hi = diff([x['ret'] for x in s7], [x['ret'] for x in fs1])
    s_lo, s_hi = s6sim.block_bootstrap([x['ret'] for x in s7], seed=SEED)
    out['S7_minus_FS1'], out['S7_ret_ci90_pct'] = d, [100 * s_lo, 100 * s_hi]
    out['share_ahead_non_overlapping'] = mean(dv[i] > 0 for i in range(0, len(dv), WINDOW))
    incr = mean(x['cost'] - y['cost'] for x, y in zip(s7, fs1)) / START_EQUITY
    out['incremental_cost_pct_equity'] = 100 * incr
    picks = {}
    for s in starts:
        w = s7_targets(market, s)
        for k in NAMES:
            picks.setdefault(k, [0, 0])
            picks[k][0] += w[k] == OVER_W
            picks[k][1] += w[k] == 0.0
    out['picks_over_zero'] = picks
    out['dd_gate'] = dd_gate(out['S7'], out['FS1_STATIC'])
    out['impl_gate'] = impl_gate(out['S7'], out['FS1_STATIC'], incr)
    out['hi'], out['s_hi'] = hi, s_hi
    if not decisive:
        out['variants_reported_only'] = variants(market, starts, fs1)
        return out
    ta = tilt_avg(market, starts, central)
    out['TILT_AVG_mean_ret_pct'] = 100 * mean(ta)
    d3, _, lo3, _ = diff([x['ret'] for x in s7], ta)
    out['S7_minus_TILT_AVG'] = d3
    costs = {}
    for name in ('team', 'stress', 'gas_cap'):
        a, b = run_arm(market, starts, COSTS[name]), run_equal(market, starts, COSTS[name])
        costs[name] = dict(S7_mean_ret_pct=100 * mean(x['ret'] for x in a),
                           FS1_mean_ret_pct=100 * mean(x['ret'] for x in b),
                           diff_mean_pct=100 * mean(x['ret'] - y['ret'] for x, y in zip(a, b)))
    out['costs'] = costs
    be = break_even_gas(market, starts)
    out['break_even_gas_usdt_per_pair'] = be
    halves = {}
    for half, keep in (('P1', lambda s: market.sessions[s + WINDOW - 1] <= P1_LAST),
                       ('P2', lambda s: market.sessions[s] >= P2_FIRST)):
        idx = [i for i, s in enumerate(starts) if keep(s)]
        hd, _, _, _ = diff([s7[i]['ret'] for i in idx], [fs1[i]['ret'] for i in idx])
        halves[half] = dict(hd, S7_mean_ret_pct=100 * mean(s7[i]['ret'] for i in idx),
                            FS1_mean_ret_pct=100 * mean(fs1[i]['ret'] for i in idx),
                            S7=summary([s7[i] for i in idx]), FS1_STATIC=summary([fs1[i] for i in idx]))
    out['split'] = halves
    years = {}
    for i, s in enumerate(starts):
        years.setdefault(market.sessions[s][:4], []).append(dv[i])
    out['years_diff_mean_pct'] = {y: 100 * mean(v) for y, v in sorted(years.items())}
    out['variants_reported_only'] = variants(market, starts, fs1, [('NO_SKHY_SIGNAL', dict(exclude=('SKHYB',)))])
    out['gates'] = dict(
        G1=d['mean_pct'] > 0 and lo > 0 and s_lo > 0,
        G2=halves['P1']['mean_pct'] > 0 and halves['P2']['mean_pct'] > 0,
        G3=d3['mean_pct'] > 0 and lo3 > 0,
        G4=costs['team']['diff_mean_pct'] > 0 and costs['stress']['diff_mean_pct'] > 0 and be >= 2 * CENTRAL_GAS,
        G7=sum(v > 0 for v in out['years_diff_mean_pct'].values()) >= 5)
    return out


def outcome(p, t, g0=True):
    """Pre-registered decision rule (IDEA-107). p, t: evaluate() outputs for P (decisive) and T (confirmatory)."""
    gates = dict(G0=g0, **p['gates'], G5=p['dd_gate'] and t['dd_gate'], G6=t['hi'] >= 0,
                 G8=p['impl_gate'] and t['impl_gate'])
    not_supported = (p['hi'] < 0 or p['s_hi'] < 0 or t['hi'] < 0 or not gates['G5']
                     or (p['split']['P1']['mean_pct'] < 0 and p['split']['P2']['mean_pct'] < 0))
    if not_supported:
        return 'NOT SUPPORTED', gates
    if all(gates.values()):
        return 'SUPPORTED', gates
    return 'INCONCLUSIVE', gates


def check_hashes(data):
    for name, want in HASHES.items():
        got = hashlib.sha256((data / name).read_bytes()).hexdigest()
        if got != want:
            raise SystemExit(f'{name}: SHA-256 {got} != recorded {want}; refusing to run (IDEA-107)')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--data', default=str(s6sim.DATA))
    args = parser.parse_args(argv)
    data = Path(args.data).expanduser()
    check_hashes(data)
    tokens = json.loads((data / 'tokens.json').read_text())
    underlying = json.loads((data / 'underlying.json').read_text())
    t_market = s6sim.token_market(tokens, s6sim.underlying_sessions(underlying))
    p_market = s6sim.proxy_market(underlying)
    p = evaluate(p_market, 'P', decisive=True)
    t = evaluate(t_market, 'T', decisive=False)
    verdict, gates = outcome(p, t)
    print(json.dumps(dict(idea='IDEA-107', P=p, T=t, gates=gates, outcome=verdict), indent=1,
                     default=lambda x: round(x, 5) if isinstance(x, float) else str(x)))


if __name__ == '__main__':
    main()

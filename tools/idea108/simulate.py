"""IDEA-108 S8 offline backtest: earnings-calendar build tilt vs FS1-STATIC, TILT-AVG and PLACEBO (docs/ledger/IDEA-108.md).

Reuses the IDEA-106 snapshot readers, fill/mark conventions, costs and bootstrap and the IDEA-107 hold mechanics
(`run_book`). Research only: no network, no credentials, no runtime code. S8 is EXPERIMENTAL and must not be deployed
(IDEA-108 "DO NOT DEPLOY").
Usage:  python -m tools.idea108.simulate --data ~/larp-idea106/snapshot-20261026 [--out report.json]
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

from tools.idea106 import simulate as s6sim
from tools.idea107 import simulate as s7sim

NAMES = s6sim.NAMES
PREDICTABLE = ('GOOGLB', 'MSFTB', 'NVDAB', 'TSLAB')  # SEC filers (8-K Item 2.02); SKHYB is never an announcer
WINDOW, START_EQUITY, GROSS = s6sim.WINDOW, s6sim.START_EQUITY, s6sim.GROSS
MIN_TRADE = s6sim.MIN_TRADE
COSTS = s6sim.COSTS
CENTRAL_BPS, CENTRAL_GAS = COSTS['central']
BASE_W = GROSS / 5          # 19%
OVER_W = 0.285              # 1.5 x 19%: two 28.5 USDT legs under the 38.2 cap, inside FS1's 30% cap
ALL_M_OVER = {3: 0.25, 4: 0.2125}  # reported-only ALL_M variant (non-announcers at 10%)
SHIFT_DAYS, PLACEBO_DAYS, WIDE_DAYS = 364, 45, 5
SEED = 108
P_FIRST = '2019-01-02'
P1_LAST, P2_FIRST = '2022-12-30', '2023-01-03'
HASHES = s7sim.HASHES


def _d(iso):
    return date.fromisoformat(iso)


def _quarter(d):
    q0 = date(d.year, 3 * ((d.month - 1) // 3) + 1, 1)
    nxt = date(q0.year + (q0.month == 10), (q0.month + 2) % 12 + 1, 1)
    return q0, nxt - timedelta(days=1)


def aligned_closes(underlying):
    """All underlying sessions to LAST_SESSION with each name's latest local close on or before the US date
    (IDEA-106 proxy_market alignment, but from the first data row, not from 2019)."""
    sessions = s6sim.underlying_sessions(underlying)
    closes = {}
    for k in NAMES:
        rows = underlying[k]
        tz = ZoneInfo(rows['tz'])
        by_day = {datetime.fromtimestamp(t, timezone.utc).astimezone(tz).date().isoformat(): c for t, c in rows['rows']}
        keys, last, i, out = sorted(by_day), None, 0, []
        for d in sessions:
            while i < len(keys) and keys[i] <= d:
                last = by_day[keys[i]]
                i += 1
            out.append(last)
        closes[k] = out
    return sessions, closes


def announcement_days(sessions, closes, names=NAMES):
    """Per name, [(quarter_end_iso, day_iso)]: in each calendar quarter fully inside the data, the session with the
    largest |basket-residual daily log return| (ties -> earliest). Uses only closes inside that quarter (and the close
    before its first return)."""
    first, last = _d(sessions[0]), _d(sessions[-1])
    resid = {k: {} for k in names}
    for u in range(1, len(sessions)):
        r = {}
        for k in NAMES:
            a, b = closes[k][u - 1], closes[k][u]
            r[k] = math.log(b / a) if a and b and a > 0 and b > 0 else None
        if any(v is None for v in r.values()):
            continue
        basket = mean(r.values())
        for k in names:
            resid[k][sessions[u]] = r[k] - basket
    out = {k: [] for k in names}
    for k in names:
        by_q = {}
        for day, e in resid[k].items():
            q0, q1 = _quarter(_d(day))
            if q0 < first or q1 > last:  # quarter not fully inside the data
                continue
            best = by_q.get(q1)
            if best is None or abs(e) > abs(best[1]) or (abs(e) == abs(best[1]) and day < best[0]):
                by_q[q1] = (day, e)
        out[k] = sorted((q1.isoformat(), v[0]) for q1, v in by_q.items())
    return out


def covered(days, build_iso, flatten_iso, shift=SHIFT_DAYS, names=PREDICTABLE):
    """True when every predictable name has a detected day for each quarter the shifted window touches."""
    lo = _d(build_iso) + timedelta(days=1) - timedelta(days=shift)
    hi = _d(flatten_iso) - timedelta(days=shift)
    need = {_quarter(lo)[1].isoformat(), _quarter(hi)[1].isoformat()}
    return all(need <= {q for q, _ in days[k]} for k in names)


def announcers(days, decision_iso, build_iso, flatten_iso, shift=SHIFT_DAYS, wide=0, names=PREDICTABLE):
    """Names with a predicted reaction day p = a + shift in (build, flatten] (+-wide). Only quarters that ended
    strictly before the decision close are used (point in time)."""
    dec, lo, hi = _d(decision_iso), _d(build_iso) - timedelta(days=wide), _d(flatten_iso) + timedelta(days=wide)
    out = []
    for k in names:
        for q_end, a in days[k]:
            if _d(q_end) >= dec:
                continue
            p = _d(a) + timedelta(days=shift)
            if lo < p <= hi:
                out.append(k)
                break
    return tuple(sorted(out))


def targets(ann, all_m=False):
    """S8 weights from the announcer set: m in {1, 2} -> 28.5% each, the rest share 95% equally; else 19% each."""
    w = {k: BASE_W for k in NAMES}
    m = len(ann)
    if m in (1, 2):
        over = OVER_W
    elif all_m and m in ALL_M_OVER:
        over = ALL_M_OVER[m]
    else:
        return w
    rest = (GROSS - over * m) / (5 - m)
    for k in NAMES:
        w[k] = over if k in ann else rest
    return w


class Setup:
    """A market plus the date-only signal inputs for every window start."""

    def __init__(self, market, days, starts):
        self.market, self.days, self.starts = market, days, starts

    def dates(self, s):
        m = self.market.sessions
        return m[s - 1], m[s], m[s + WINDOW - 1]

    def ann(self, s, shift=SHIFT_DAYS, wide=0, names=PREDICTABLE):
        return announcers(self.days, *self.dates(s), shift=shift, wide=wide, names=names)


def p_starts(market, days):
    return [s for s in range(1, len(market.sessions) - WINDOW + 1)
            if market.sessions[s] >= P_FIRST and covered(days, market.sessions[s], market.sessions[s + WINDOW - 1])]


def t_starts(market):
    return list(range(1, len(market.sessions) - WINDOW + 1))


def run_s8(setup, cost, shift=SHIFT_DAYS, wide=0, names=PREDICTABLE, all_m=False):
    return [s7sim.run_book(setup.market, s, targets(setup.ann(s, shift, wide, names), all_m), cost)
            for s in setup.starts]


def run_fs1(setup, cost):
    return [s7sim.run_book(setup.market, s, s7sim.equal_targets(), cost) for s in setup.starts]


def tilt_avg(setup, cost, fs1):
    out = []
    for i, s in enumerate(setup.starts):
        m = len(setup.ann(s))
        if m not in (1, 2):
            out.append(fs1[i]['ret'])
            continue
        out.append(mean(s7sim.run_book(setup.market, s, targets(c), cost)['ret'] for c in combinations(PREDICTABLE, m)))
    return out


def diff(a, b):
    d = [x - y for x, y in zip(a, b)]
    lo, hi = s6sim.block_bootstrap(d, seed=SEED)
    return dict(mean_pct=100 * mean(d), ci90_pct=[100 * lo, 100 * hi], share_ahead=mean(x > 0 for x in d),
                share_behind=mean(x < 0 for x in d), n=len(d)), d, lo, hi


def mechanism(setup):
    """In tilt windows: mean hold price return (fill s -> fill s+9) of announcers minus non-announcers."""
    xs = []
    for s in setup.starts:
        ann = setup.ann(s)
        if len(ann) not in (1, 2):
            continue
        a, b = setup.market.fills[s][1], setup.market.fills[s + WINDOW - 1][1]
        r = {k: b[k] / a[k] - 1 for k in NAMES}
        xs.append(mean(r[k] for k in ann) - mean(r[k] for k in NAMES if k not in ann))
    lo, hi = s6sim.block_bootstrap(xs, seed=SEED) if len(xs) >= 10 else (float('nan'), float('nan'))
    return dict(tilt_windows=len(xs), mean_announcer_excess_pct=100 * mean(xs) if xs else None,
                ci90_pct=[100 * lo, 100 * hi], break_even_central_pct=0.61)


def break_even_gas(setup):
    def gap(g):
        cost = (CENTRAL_BPS, g)
        return mean(x['ret'] - y['ret'] for x, y in zip(run_s8(setup, cost), run_fs1(setup, cost)))
    lo, hi = 0.0, 5.0
    if gap(lo) <= 0:
        return 0.0
    if gap(hi) > 0:
        return hi
    for _ in range(20):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap(mid) > 0 else (lo, mid)
    return lo


def dd_gate(s, f):
    return (s['share_dd_ge_8'] <= f['share_dd_ge_8'] + 0.03 and s['share_dd_ge_12'] <= f['share_dd_ge_12'] + 0.02
            and s['median_maxdd_pct'] <= 1.25 * f['median_maxdd_pct'])


def impl_gate(s, f, incr):
    return s['min_discretionary_leg_usdt'] >= MIN_TRADE and s['mean_legs'] <= f['mean_legs'] + 4 and incr <= 0.0015


VARIANTS = dict(WITH_SKHY=dict(names=NAMES), WIDE=dict(wide=WIDE_DAYS), ALL_M=dict(all_m=True))


def evaluate(setup, decisive):
    market, starts = setup.market, setup.starts
    central = COSTS['central']
    s8, fs1 = run_s8(setup, central), run_fs1(setup, central)
    ms = [len(setup.ann(s)) for s in starts]
    out = dict(windows=len(starts), non_overlapping=len(starts[::WINDOW]),
               first_build=market.sessions[starts[0]], last_flatten=market.sessions[starts[-1] + WINDOW - 1],
               m_counts={str(m): ms.count(m) for m in range(6) if ms.count(m)},
               tilt_windows=sum(m in (1, 2) for m in ms))
    if market.fallbacks:
        out['fill_fallbacks'] = market.fallbacks
    out['S8'], out['FS1_STATIC'] = s7sim.summary(s8), s7sim.summary(fs1)
    d, dv, lo, hi = diff([x['ret'] for x in s8], [x['ret'] for x in fs1])
    s_lo, s_hi = s6sim.block_bootstrap([x['ret'] for x in s8], seed=SEED)
    out['S8_minus_FS1'], out['S8_ret_ci90_pct'] = d, [100 * s_lo, 100 * s_hi]
    tilt_idx = [i for i, m in enumerate(ms) if m in (1, 2)]
    out['S8_minus_FS1_tilt_windows_only'] = diff([s8[i]['ret'] for i in tilt_idx], [fs1[i]['ret'] for i in tilt_idx])[0] \
        if len(tilt_idx) >= 10 else dict(n=len(tilt_idx), mean_pct=100 * mean(dv[i] for i in tilt_idx) if tilt_idx else None)
    out['share_ahead_non_overlapping'] = mean(dv[i] > 0 for i in range(0, len(dv), WINDOW))
    incr = mean(x['cost'] - y['cost'] for x, y in zip(s8, fs1)) / START_EQUITY
    out['incremental_cost_pct_equity'] = 100 * incr
    picks = {k: sum(k in setup.ann(s) for s in starts if len(setup.ann(s)) in (1, 2)) for k in NAMES}
    out['overweight_counts'] = picks
    out['mechanism'] = mechanism(setup)
    out['dd_gate'] = dd_gate(out['S8'], out['FS1_STATIC'])
    out['impl_gate'] = impl_gate(out['S8'], out['FS1_STATIC'], incr)
    out['hi'], out['s_hi'] = hi, s_hi
    variants = {}
    for name, kw in VARIANTS.items():
        a = run_s8(setup, central, **kw)
        variants[name] = dict(mean_ret_pct=100 * mean(x['ret'] for x in a),
                              diff_vs_FS1_mean_pct=100 * mean(x['ret'] - y['ret'] for x, y in zip(a, fs1)),
                              mean_maxdd_pct=100 * mean(x['max_dd'] for x in a))
    out['variants_reported_only'] = variants
    ta = tilt_avg(setup, central, fs1)
    pl = run_s8(setup, central, shift=SHIFT_DAYS + PLACEBO_DAYS)
    out['TILT_AVG_mean_ret_pct'] = 100 * mean(ta)
    out['PLACEBO_mean_ret_pct'] = 100 * mean(x['ret'] for x in pl)
    d3, _, lo3, _ = diff([x['ret'] for x in s8], ta)
    d4, _, _, _ = diff([x['ret'] for x in s8], [x['ret'] for x in pl])
    out['S8_minus_TILT_AVG'], out['S8_minus_PLACEBO'] = d3, d4
    costs = {}
    for name in ('team', 'stress', 'gas_cap'):
        a, b = run_s8(setup, COSTS[name]), run_fs1(setup, COSTS[name])
        costs[name] = dict(S8_mean_ret_pct=100 * mean(x['ret'] for x in a),
                           FS1_mean_ret_pct=100 * mean(x['ret'] for x in b),
                           diff_mean_pct=100 * mean(x['ret'] - y['ret'] for x, y in zip(a, b)))
    out['costs'] = costs
    out['break_even_gas_usdt_per_pair'] = break_even_gas(setup)
    years = {}
    for i, s in enumerate(starts):
        years.setdefault(market.sessions[s][:4], []).append(dv[i])
    out['years_diff_mean_pct'] = {y: 100 * mean(v) for y, v in sorted(years.items())}
    if not decisive:
        return out
    halves = {}
    for half, keep in (('P1', lambda s: market.sessions[s + WINDOW - 1] <= P1_LAST),
                       ('P2', lambda s: market.sessions[s] >= P2_FIRST)):
        idx = [i for i, s in enumerate(starts) if keep(s)]
        hd, _, _, _ = diff([s8[i]['ret'] for i in idx], [fs1[i]['ret'] for i in idx])
        h_lo, h_hi = s6sim.block_bootstrap([s8[i]['ret'] for i in idx], seed=SEED)
        halves[half] = dict(hd, S8_mean_ret_pct=100 * mean(s8[i]['ret'] for i in idx),
                            FS1_mean_ret_pct=100 * mean(fs1[i]['ret'] for i in idx),
                            S8_ret_ci90_pct=[100 * h_lo, 100 * h_hi],
                            first_build=market.sessions[starts[idx[0]]], last_flatten=market.sessions[starts[idx[-1]] + WINDOW - 1],
                            S8=s7sim.summary([s8[i] for i in idx]), FS1_STATIC=s7sim.summary([fs1[i] for i in idx]))
    out['split'] = halves
    out['gates'] = dict(
        G1=d['mean_pct'] > 0 and lo > 0 and s_lo > 0,
        G2=halves['P1']['mean_pct'] > 0 and halves['P2']['mean_pct'] > 0,
        G3=d3['mean_pct'] > 0 and lo3 > 0 and d4['mean_pct'] > 0,
        G4=(costs['team']['diff_mean_pct'] > 0 and costs['stress']['diff_mean_pct'] > 0
            and out['break_even_gas_usdt_per_pair'] >= 2 * CENTRAL_GAS),
        G7=sum(v > 0 for v in out['years_diff_mean_pct'].values()) >= 5)
    return out


def outcome(p, t, g0=True):
    """Pre-registered decision rule (IDEA-108). p, t: evaluate() outputs for P (decisive) and T (confirmatory)."""
    gates = dict(G0=g0, **p['gates'], G5=p['dd_gate'] and t['dd_gate'], G6=t['hi'] >= 0,
                 G8=p['impl_gate'] and t['impl_gate'])
    gates = {k: gates[k] for k in sorted(gates)}
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
            raise SystemExit(f'{name}: SHA-256 {got} != recorded {want}; refusing to run (IDEA-108)')


def build(data):
    check_hashes(data)
    tokens = json.loads((data / 'tokens.json').read_text())
    underlying = json.loads((data / 'underlying.json').read_text())
    sessions, closes = aligned_closes(underlying)
    days = announcement_days(sessions, closes)
    p_market = s6sim.proxy_market(underlying)
    t_market = s6sim.token_market(tokens, s6sim.underlying_sessions(underlying))
    return Setup(p_market, days, p_starts(p_market, days)), Setup(t_market, days, t_starts(t_market)), days


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--data', default=str(s6sim.DATA))
    parser.add_argument('--out')
    args = parser.parse_args(argv)
    p_setup, t_setup, days = build(Path(args.data).expanduser())
    p = evaluate(p_setup, decisive=True)
    t = evaluate(t_setup, decisive=False)
    verdict, gates = outcome(p, t)
    report = json.dumps(dict(idea='IDEA-108', P=p, T=t, gates=gates, outcome=verdict,
                             announcement_days_last8={k: v[-8:] for k, v in days.items()}), indent=1,
                        default=lambda x: round(x, 5) if isinstance(x, float) else str(x))
    if args.out:
        Path(args.out).expanduser().write_text(report + '\n')
    print(report)


if __name__ == '__main__':
    main()

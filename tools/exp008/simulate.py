"""EXP-008: S1 vs EQUAL_WEIGHT over every overlapping 10-session window (rules in docs/ledger/EXP-008.md).

Reads the snapshot written by fetch.py; prints a JSON report. Research only: no I/O beyond data/exp008.
Usage:  python tools/exp008/simulate.py
"""
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from zoneinfo import ZoneInfo

import numpy as np

DATA = Path(__file__).resolve().parents[2] / "data" / "exp008"
NAMES = ("NVDAB", "GOOGLB", "SKHYB", "TSLAB", "MSFTB")
EW4 = ("NVDAB", "GOOGLB", "SKHYB", "TSLAB")  # MSFTB dropped: highest measured round trip (IDEA-063 C3)
ET, KST = ZoneInfo("America/New_York"), ZoneInfo("Asia/Seoul")
WINDOW, START_EQUITY, GAS = 10, 200.0, 0.03
FIRST_SESSION, LAST_SESSION = "2019-01-02", "2026-10-22"


def day(ts, tz):
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(tz).date().isoformat()


def underlying_series():
    raw = json.loads((DATA / "underlying.json").read_text())
    sessions = sorted({day(t, ET) for t, _ in raw["NVDAB"]["rows"]})
    sessions = [d for d in sessions if d <= LAST_SESSION]
    closes = {}
    for name in NAMES:
        rows = raw[name]
        by_day = {day(t, ZoneInfo(rows["tz"])): c for t, c in rows["rows"]}
        keys, out, last, i = sorted(by_day), [], None, 0
        for d in sessions:  # latest local close on or before the US session date (only SKHYB differs)
            while i < len(keys) and keys[i] <= d:
                last = by_day[keys[i]]
                i += 1
            out.append(last)
        closes[name] = out
    return sessions, closes


def token_series(sessions_all):
    raw = json.loads((DATA / "tokens.json").read_text())
    first = max(min(int(r[5]) for r in raw[n]) for n in NAMES) // 1000
    sessions = [d for d in sessions_all if d >= day(first, ET)]
    closes, carried = {}, defaultdict(int)
    for name in NAMES:
        bars = sorted((int(r[5]), float(r[3])) for r in raw[name])
        out, last, i = [], None, 0
        for d in sessions:
            close_et = datetime.fromisoformat(d + "T16:00").replace(tzinfo=ET)
            limit_ms = int(close_et.timestamp() * 1000)
            today = False
            while i < len(bars) and bars[i][0] + 3_600_000 <= limit_ms:
                last = bars[i][1]
                today = day(bars[i][0] // 1000, ET) == d
                i += 1
            carried[name] += not today
            out.append(last)
        closes[name] = out
    return sessions, closes, dict(carried)


def trend_states(closes, n):
    """State after each close: UP/DOWN with a +-1% band on I / mean(last 5 I) - 1, starting UP."""
    index, states, state = [1.0], [], "UP"
    for t in range(n):
        if t:
            rets = [closes[k][t] / closes[k][t - 1] - 1 for k in NAMES]
            index.append(index[-1] * (1 + sum(rets) / len(rets)))
        if len(index) >= 5:
            r = index[-1] / mean(index[-5:]) - 1
            state = "UP" if r > 0.01 else "DOWN" if r < -0.01 else state
        states.append(state)
    return states


def s1_weights(closes, s):
    sig = {}
    for k in NAMES:
        px = closes[k][max(0, s - 61):s]
        rets = [math.log(b / a) for a, b in zip(px, px[1:])]
        sig[k] = pstdev(rets) if len(rets) >= 20 else None
    known = [v for v in sig.values() if v is not None]
    sig = {k: v if v is not None else median(known) for k, v in sig.items()}
    w = {k: 1 / max(v, 1e-12) for k, v in sig.items()}
    total = sum(w.values())
    w = {k: v / total for k, v in w.items()}
    for _ in range(len(NAMES)):  # cap 0.30, excess pro rata over uncapped names
        over = {k for k, v in w.items() if v > 0.30 + 1e-12}
        if not over:
            break
        excess = sum(w[k] - 0.30 for k in over)
        free = {k: v for k, v in w.items() if v < 0.30 - 1e-12 and k not in over}
        for k in over:
            w[k] = 0.30
        free_total = sum(free.values())
        for k, v in free.items():
            w[k] = v + excess * v / free_total
    return w


def run_window(closes, s, arm, states, bps):
    """One 10-session window starting at close s; returns (net return, max drawdown)."""
    c = bps / 10_000
    if arm in ("S1", "S1_STATIC"):
        w = s1_weights(closes, s)
        level = (lambda st: 0.95 if st == "UP" else 0.60) if arm == "S1" else (lambda st: 0.95)
        base = {k: w[k] for k in NAMES}
        top_band, name_line = 0.05, 0.35
    else:
        names = EW4 if arm == "EW" else NAMES
        each = 0.20 if arm == "EW" else 0.16
        base = {k: (each / 0.80 if k in names else 0.0) for k in NAMES}
        level = lambda st: 0.80
        top_band, name_line = 0.05, 0.25
    cash, units = START_EQUITY, {k: 0.0 for k in NAMES}
    cut = False
    cur_level = level(states[s - 1])
    gross_cap = lambda: min(cur_level, 0.40) if cut else cur_level
    target = lambda: {k: gross_cap() * base[k] for k in NAMES}
    pending = target()  # opening buys at close s
    peak, prev_eq, max_dd, buy_block_day, buy_block_dd = START_EQUITY, START_EQUITY, 0.0, False, False

    def execute(desired, prices, allow_buys):
        nonlocal cash
        eq = cash + sum(units[k] * prices[k] for k in NAMES)
        for k in sorted(desired, key=lambda k: desired[k] * eq - units[k] * prices[k]):  # sells first
            delta = desired[k] * eq - units[k] * prices[k]
            if abs(delta) < 1e-9 or (delta > 0 and not allow_buys):
                continue
            units[k] += delta / prices[k]
            cash -= delta + abs(delta) * c + GAS

    for t in range(s, s + WINDOW):
        prices = {k: closes[k][t] for k in NAMES}
        if t == s + WINDOW - 1:
            execute({k: 0.0 for k in NAMES}, prices, False)
        elif pending:
            execute(pending, prices, not (buy_block_day or buy_block_dd))
        pending = None
        eq = cash + sum(units[k] * prices[k] for k in NAMES)
        peak = max(peak, eq)
        dd = 1 - eq / peak
        max_dd = max(max_dd, dd)
        if t == s + WINDOW - 1:
            return eq / START_EQUITY - 1, max_dd
        buy_block_day = eq / prev_eq - 1 <= -0.03
        buy_block_dd = dd >= 0.08 or (buy_block_dd and dd >= 0.05)
        prev_eq = eq
        weights = {k: units[k] * prices[k] / eq for k in NAMES}
        gross = sum(weights.values())
        desired = {}
        if dd >= 0.12 and not cut:
            cut = True
            desired = target()
        new_level = level(states[t])
        if new_level != cur_level:
            cur_level = new_level
            desired = target()
        tgt = target()
        if not desired and gross < gross_cap() - top_band and not (buy_block_day or buy_block_dd):
            desired = {k: tgt[k] for k in NAMES if weights[k] < tgt[k]}
        for k in NAMES:
            if weights[k] > name_line:
                desired[k] = tgt[k]
        if arm.startswith("EW") and gross > 0.90 and not desired:
            desired = {k: weights[k] * 0.80 / gross for k in NAMES}
        pending = desired or None


def block_bootstrap(diffs, block=10, n=10_000, seed=8):
    rng = np.random.default_rng(seed)
    d = np.asarray(diffs)
    starts = np.arange(len(d) - block + 1)
    k = math.ceil(len(d) / block)
    means = np.empty(n)
    for i in range(n):
        idx = (rng.choice(starts, k)[:, None] + np.arange(block)).ravel()[:len(d)]
        means[i] = d[idx].mean()
    return float(np.quantile(means, 0.05)), float(np.quantile(means, 0.95))


def evaluate(sessions, closes, bps, first=None):
    n = len(sessions)
    states = trend_states(closes, n)
    first_start = max(21, sessions.index(first) if first in sessions else 21)
    starts = [s for s in range(first_start, n - WINDOW + 1)]
    arms = ("S1", "EW", "S1_STATIC", "EW5")
    res = {a: [run_window(closes, s, a, states, bps) for s in starts] for a in arms}
    out = {"windows": len(starts), "non_overlapping": len(starts) // WINDOW,
           "first_window": sessions[starts[0]], "last_window_end": sessions[starts[-1] + WINDOW - 1]}
    for a in arms:
        r = [x[0] for x in res[a]]
        dd = [x[1] for x in res[a]]
        out[a] = {"mean_ret_pct": 100 * mean(r), "median_ret_pct": 100 * median(r), "sd_ret_pct": 100 * pstdev(r),
                  "p_ret_gt_0": mean(x > 0 for x in r), "mean_maxdd_pct": 100 * mean(dd),
                  "p_dd_ge_8": mean(x >= 0.08 for x in dd)}
    diff = [a[0] - b[0] for a, b in zip(res["S1"], res["EW"])]
    lo, hi = block_bootstrap(diff)
    out["S1_minus_EW"] = {"mean_pct": 100 * mean(diff), "ci90_pct": [100 * lo, 100 * hi],
                          "share_S1_ahead": mean(x > 0 for x in diff)}
    for a, b in (("S1_STATIC", "EW"), ("S1", "S1_STATIC"), ("EW5", "EW")):
        out[f"{a}_minus_{b}_mean_pct"] = 100 * mean(x[0] - y[0] for x, y in zip(res[a], res[b]))
    by_year = defaultdict(list)
    for s, d in zip(starts, diff):
        by_year[sessions[s][:4]].append(d)
    out["S1_minus_EW_by_year_pct"] = {y: round(100 * mean(v), 3) for y, v in sorted(by_year.items())}
    if len(diff) >= 1 and out["windows"]:
        verdict = ("S1 better for profit" if mean(diff) > 0 and lo > 0
                   else "EW better for profit" if hi < 0 else "no detectable difference")
        out["outcome_if_primary"] = verdict
    return out


def main():
    sessions, closes = underlying_series()
    tok_sessions, tok_closes, carried = token_series(sessions)
    report = {}
    for bps in (25, 50):
        report[f"P_{bps}bp"] = evaluate(sessions, closes, bps, FIRST_SESSION)
        report[f"T_{bps}bp"] = evaluate(tok_sessions, tok_closes, bps)
    report["T_sessions"] = [tok_sessions[0], tok_sessions[-1], len(tok_sessions)]
    report["T_carried_forward_closes"] = carried
    print(json.dumps(report, indent=1, default=lambda x: round(x, 4)))


if __name__ == "__main__":
    main()

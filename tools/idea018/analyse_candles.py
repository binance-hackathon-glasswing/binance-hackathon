"""R2 review: print-based statistics from the bStock candle probe (read-only).
Usage: python -I analyse_candles.py <candles_probe.json>
Rows are [open, high, low, close, volume, open_time_ms, trade_count]; bars exist only when trades printed.
"""
import json, sys, math, hashlib
from datetime import datetime, timezone, timedelta
import numpy as np

P = sys.argv[1]
print("sha256", hashlib.sha256(open(P, "rb").read()).hexdigest())
raw = json.load(open(P))["raw"]
TOK = ["NVDAB", "GOOGLB", "SKHYB", "TSLAB", "MSFTB"]
H = 3_600_000

# --- collect series per token: raw blocks follow "<SYM> rwa/underlying-market" markers
blocks, cur = {t: [] for t in TOK}, None
for r in raw:
    if r.get("endpoint") == "rwa/underlying-market":
        cur = r["symbol"]; continue
    if cur and r.get("bar") and isinstance(r["response"].get("data"), list):
        blocks[cur].append(r)

def rows(tok, bar):
    out = {}
    for r in blocks[tok]:
        if r["bar"] == bar:
            for c in r["response"]["data"]:
                out[int(c[5])] = [float(x) for x in c[:5]] + [int(c[6]) if c[6] is not None else -1]
    return dict(sorted(out.items()))

ET_OFF = -4  # EDT throughout Sep 5 - Oct 7 2026
HOLI = {"2026-09-07"}  # Labor Day

def cat(ms):
    """Category of the hour bar starting at ms (UTC)."""
    t = datetime.fromtimestamp(ms / 1000, tz=timezone.utc) + timedelta(hours=ET_OFF)
    if t.weekday() >= 5 or t.strftime("%Y-%m-%d") in HOLI:
        return "weekend/holiday"
    h = t.hour
    if 10 <= h < 16: return "RTH"          # 10:00-16:00 ET fully inside regular hours
    if h == 9: return "open-hour"           # 09:00-10:00 ET, half regular
    if 4 <= h < 9: return "pre-market"
    if 16 <= h < 20: return "after-hours"
    return "overnight"

CATS = ["RTH", "open-hour", "pre-market", "after-hours", "overnight", "weekend/holiday"]

print("\n== 1h coverage: chunks, missing hours (no-trade hours) ==")
res = {}
for tok in TOK:
    d = rows(tok, "1h"); ts = list(d)
    chunks, start = [], ts[0]
    for a, b in zip(ts, ts[1:]):
        if b - a > 48 * H:
            chunks.append((start, a)); start = b
    chunks.append((start, ts[-1]))
    span = sum((b - a) // H + 1 for a, b in chunks)
    miss_by = {c: [0, 0] for c in CATS}   # [present, expected]
    for a, b in chunks:
        for m in range(a, b + H, H):
            miss_by[cat(m)][1] += 1
            if m in d: miss_by[cat(m)][0] += 1
    fmt = lambda m: datetime.fromtimestamp(m / 1000, tz=timezone.utc).strftime("%m-%d %H:%M")
    print(tok, "bars", len(ts), "chunks", [(fmt(a), fmt(b)) for a, b in chunks], "hours spanned", span,
          "no-trade hours", span - len(ts), f"({(span-len(ts))/span:.1%})",
          {c: f"{v[1]-v[0]}/{v[1]}" for c, v in miss_by.items()})
    # returns within chunks; a multi-hour return (after missing bars) counts its k hours
    acc = {c: [0.0, 0, 0] for c in CATS}  # sum r^2, hours, n returns
    rr, gaps1 = [], []
    for a, b in zip(ts, ts[1:]):
        k = (b - a) // H
        if k > 48: continue
        r = math.log(d[b][3] / d[a][3])
        c = cat(b)
        acc[c][0] += r * r; acc[c][1] += k; acc[c][2] += 1
        if k == 1: rr.append((b, r))
    res[tok] = (acc, rr, d)

print("\n== Hourly variance by category (sum r^2 / hours elapsed), relative to RTH; share of total variance and of time ==")
print(f"{'tok':7}" + "".join(f"{c:>18}" for c in CATS) + f"{'offshare var':>14}{'offshare time':>14}{'off/RTH ratio':>15}")
for tok in TOK:
    acc = res[tok][0]
    vr = {c: acc[c][0] / acc[c][1] for c in CATS}
    tot = sum(acc[c][0] for c in CATS); toth = sum(acc[c][1] for c in CATS)
    on = acc["RTH"][0] + acc["open-hour"][0]; onh = acc["RTH"][1] + acc["open-hour"][1]
    off_var = 1 - on / tot; off_time = 1 - onh / toth
    ratio = ((tot - on) / (toth - onh)) / (on / onh)
    print(f"{tok:7}" + "".join(f"{vr[c]/vr['RTH']:>11.2f} ({acc[c][1]:3d}h)" for c in CATS)
          + f"{off_var:>14.1%}{off_time:>14.1%}{ratio:>15.2f}")
    # weekend vs weeknight per-hour, both relative to RTH
    wn = sum(acc[c][0] for c in ["pre-market", "after-hours", "overnight"]) / sum(acc[c][1] for c in ["pre-market", "after-hours", "overnight"])
    print(f"        weeknight(all off-hours weekdays)/RTH = {wn/vr['RTH']:.2f}; weekend/RTH = {vr['weekend/holiday']/vr['RTH']:.2f}; "
          f"RTH hourly sd = {math.sqrt(vr['RTH'])*1e4:.0f} bp")

print("\n== IDEA-017 R9 arithmetic: off/on hourly ratio = (s/(1-s)) / (f/(1-f)), f = off time share ==")
for f in (0.81, 135.5 / 168):
    print(f"f={f:.3f}:", {s: round((s / (1 - s)) / (f / (1 - f)), 2) for s in (0.73, 0.75, 0.77, 0.79, 0.82)})

def roll(r):
    r = np.asarray(r); c = np.cov(r[1:], r[:-1])[0, 1]
    return 2 * math.sqrt(-c) * 1e4 if c < 0 else float("nan"), np.corrcoef(r[1:], r[:-1])[0, 1]

def ar_spread(d):
    """Abdi-Ranaldo (2017) close-high-low estimator on consecutive bars, bp."""
    ts = list(d); v = []
    for a, b in zip(ts, ts[1:]):
        c = math.log(d[a][3]); e0 = (math.log(d[a][1]) + math.log(d[a][2])) / 2; e1 = (math.log(d[b][1]) + math.log(d[b][2])) / 2
        v.append((c - e0) * (c - e1))
    m = 4 * np.mean(v)
    return 2 * 0 + (math.sqrt(m) * 1e4 if m > 0 else float("nan"))

print("\n== Print-based spread proxies (NOT quotes): Roll = 2*sqrt(-cov) of consecutive returns; AR = Abdi-Ranaldo CHL ==")
for tok in TOK:
    acc, rr, d = res[tok]
    r_all = [r for _, r in rr]
    r_rth = [r for b, r in rr if cat(b) in ("RTH",)]
    r_wk = [r for b, r in rr if cat(b) == "weekend/holiday"]
    m = rows(tok, "1m"); mt = list(m)
    r1 = [math.log(m[b][3] / m[a][3]) for a, b in zip(mt, mt[1:]) if b - a == 60_000]
    r1any = [math.log(m[b][3] / m[a][3]) for a, b in zip(mt, mt[1:])]
    span_m = (mt[-1] - mt[0]) // 60_000 + 1
    one_trade = sum(1 for v in m.values() if v[5] == 1) / len(m)
    vol1h = np.median([v[4] for v in res[tok][2].values()])
    print(f"{tok:7} 1h Roll all {roll(r_all)[0]:5.0f} bp (ac {roll(r_all)[1]:+.2f}) | RTH {roll(r_rth)[0]:5.0f} (ac {roll(r_rth)[1]:+.2f}) "
          f"| wkend {roll(r_wk)[0]:5.0f} (ac {roll(r_wk)[1]:+.2f}) | AR1h {ar_spread(res[tok][2]):4.0f} bp || 1m: {len(m)} bars over {span_m} min "
          f"({1-len(m)/span_m:.0%} no-trade min), consecutive Roll {roll(r1)[0]:4.0f} bp (ac {roll(r1)[1]:+.2f}), any-gap Roll {roll(r1any)[0]:4.0f} bp, "
          f"AR1m {ar_spread(m):4.0f} bp, 1-trade bars {one_trade:.0%}, median 1h volume {vol1h:,.0f}")

print("\n== Overnight token move vs next RTH move (prints). CO = prev 20:00 UTC close -> 13:00 UTC close (pre-open); OC = 13:00 -> 20:00 UTC ==")
allco, alloc = [], []
for tok in TOK:
    d = res[tok][2]
    days = sorted({datetime.fromtimestamp(m / 1000, tz=timezone.utc).date() for m in d})
    def px(dt, hour):  # close of last bar starting at or before hour-1 on that date, within 2h
        tgt = int(datetime(dt.year, dt.month, dt.day, hour, tzinfo=timezone.utc).timestamp() * 1000) - H
        for k in range(3):
            if tgt - k * H in d: return d[tgt - k * H][3]
        return None
    co, oc = [], []
    prev = None
    for dt in days:
        s = dt.strftime("%Y-%m-%d")
        if dt.weekday() >= 5 or s in HOLI: continue
        p13, p20 = px(dt, 13), px(dt, 20)
        if prev and p13 and p20 and (dt - prev[0]).days <= 4:
            co.append(math.log(p13 / prev[1])); oc.append(math.log(p20 / p13))
        if p20: prev = (dt, p20)
    co, oc = np.array(co), np.array(oc)
    allco += list(co / co.std()); alloc += list(oc / oc.std())
    b = np.polyfit(co, oc, 1)[0]
    print(f"{tok:7} n={len(co):2d} corr(CO,OC)={np.corrcoef(co, oc)[0,1]:+.2f} slope={b:+.2f} sd CO {co.std()*1e2:.2f}% sd OC {oc.std()*1e2:.2f}% "
          f"var share CO {co.var()/(co.var()+oc.var()):.0%}")
allco, alloc = np.array(allco), np.array(alloc)
n = len(allco); rho = np.corrcoef(allco, alloc)[0, 1]
print(f"pooled (vol-standardised) n={n} corr={rho:+.2f}  approx 95% CI half-width {1.96/math.sqrt(n-3):.2f} (names not independent)")

print("\n== Daily (24/7 calendar) bStock candles: vol, kurtosis, correlations ==")
D = {t: rows(t, "1d") for t in TOK}
common = sorted(set.intersection(*[set(D[t]) for t in TOK]))
print("common days", len(common), datetime.fromtimestamp(common[0]/1000, tz=timezone.utc).date(), "->", datetime.fromtimestamp(common[-1]/1000, tz=timezone.utc).date())
R = np.array([[math.log(D[t][b][3] / D[t][a][3]) for a, b in zip(common, common[1:]) if b - a == 86_400_000] for t in TOK])
for i, t in enumerate(TOK):
    x = R[i]; k = ((x - x.mean())**4).mean() / x.var()**2
    print(f"{t:7} daily sd {x.std()*100:.2f}% (cal-day), excess kurtosis {k-3:+.1f}, n={len(x)}")
C = np.corrcoef(R); print("corr matrix (calendar-day returns):"); print(np.round(C, 2))
US = [0, 1, 3, 4]
print("mean pairwise corr 4 US names:", round(np.mean([C[i, j] for i in US for j in US if i < j]), 2))
# (review copy) daily returns are not written to disk

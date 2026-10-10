"""R2 transparent Monte Carlo of LARP's scored run (illustrative; assumptions stated in IDEA-018 §3.1).
IDEA-018 review script, offline. Usage: python -I mc_run.py [rho] [n_paths] [vol_scale]
Hourly steps, 24/7 token, Thu Oct 29 2026 14:00 UTC (build) -> Tue Nov 10 19:00 UTC (flatten) = 293 h, 9 US sessions.
"""
import sys, itertools
from datetime import datetime, timedelta, timezone
import numpy as np

RHO = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
N = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
VSCALE = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
EQ0 = 200.0
NAMES = ["NVDAB", "GOOGLB", "TSLAB", "MSFTB"]
SIG_CAL = np.array([1.80, 1.59, 2.44, 1.65]) / 100 * VSCALE   # bStock 1d candles, calendar-day sd (Jul 17-Oct 7)
# per-hour variance relative to RTH (10-16 ET), from 1h candles Sep 5-Oct 7 (analyse_candles.py)
#               RTH  open(9-10) pre(4-9) after(16-20) overnight weekend
PROF = np.array([[1, 3.45, 0.87, 0.60, 0.66, 0.33],    # NVDAB
                 [1, 2.98, 1.15, 1.24, 0.71, 0.19],    # GOOGLB
                 [1, 9.26, 0.49, 0.26, 0.23, 0.24],    # TSLAB
                 [1, 6.63, 0.84, 0.93, 0.78, 0.57]])   # MSFTB
WEEK_H = np.array([30, 5, 25, 20, 40, 48])             # hours per week in each category
W_E1 = np.array([11.5, 13.15, 8.8, 14.25]) / 100        # mid of IDEA-009 D.1 full-history / EWMA rows (47.7% gross)
W_CAP = np.full(4, 0.20)
BETA, DF = 1.3, 5                                        # beta to equity premium (IDEA-009 [A]); daily t mixing df
T0 = datetime(2026, 10, 29, 14, tzinfo=timezone.utc)
HRS = 293

def calendar():
    cats, sched, monday, utcday, opens = [], [], [], [], []
    for h in range(HRS):
        u = T0 + timedelta(hours=h)
        et = u - timedelta(hours=4 if u < datetime(2026, 11, 1, 6, tzinfo=timezone.utc) else 5)
        hh = et.hour
        c = 5 if et.weekday() >= 5 else (0 if 10 <= hh < 16 else 1 if hh == 9 else 2 if 4 <= hh < 9 else 3 if 16 <= hh < 20 else 4)
        cats.append(c)
        sched.append(et.weekday() < 5 and hh in (10, 15))       # scheduled rounds ~open+30 / close-60 (hourly grid)
        monday.append(et.weekday() == 0 and hh == 15)
        opens.append(et.weekday() < 5 and hh == 10)
        utcday.append(u.date())
    newday = [False] + [utcday[i] != utcday[i - 1] for i in range(1, HRS)]
    return np.array(cats), np.array(sched), np.array(monday), np.array(newday), np.array(opens)

CATS, SCHED, MONDAY, NEWDAY, OPENS = calendar()

def simulate(rng):
    """Hourly log-return shocks, (N, HRS, 4): Gaussian x per-UTC-day common variance mixing (t-like daily tails)."""
    unit = (PROF * WEEK_H).sum(1) / (7 * 24)              # mean per-hour multiplier
    sig_h = SIG_CAL[None, :] / np.sqrt(24 * unit)[None, :] * np.sqrt(PROF.T[CATS])  # (HRS,4)
    C = RHO * np.ones((4, 4)) + (1 - RHO) * np.eye(4)
    z = rng.standard_normal((N, HRS, 4)) @ np.linalg.cholesky(C).T
    day_id = np.cumsum(NEWDAY)
    mix = np.sqrt((DF - 2) / rng.chisquare(DF, (N, day_id[-1] + 1)))[:, day_id]   # common across names
    x = z * sig_h[None] * mix[..., None]
    return x - 0.5 * (sig_h[None] * mix[..., None]) ** 2   # zero-premium => E[price relative] = 1 (no convexity drift)

def run(shock, prem, gas, spr, pol):
    """Returns per-path terminal profit, max drawdown, legs, volume, ladder flags."""
    mu = prem * BETA / 8760
    h = np.zeros((N, 4)); cash = np.full(N, EQ0)
    legs = np.zeros(N); vol = np.zeros(N); peak = np.full(N, EQ0); mdd = np.zeros(N)
    halt_day = np.zeros(N, bool); halt8 = np.zeros(N, bool); cut12 = np.zeros(N, bool); locked = np.zeros(N, bool)
    f3 = np.zeros(N, bool); f8 = np.zeros(N, bool); f12 = np.zeros(N, bool)
    day_eq = np.full(N, EQ0)
    tw = W_CAP if pol.get("cap") else W_E1

    def trade(delta, mask):
        nonlocal h, cash, legs, vol
        d = np.where(mask[:, None], delta, 0.0)
        d = np.where(np.abs(d) >= pol.get("min", 1e-9), d, 0.0)
        if pol.get("ladder"):
            d = np.where((halt_day | halt8)[:, None] & (d > 0), 0.0, d)
        if pol.get("ladder"):
            d = np.where(cut12[:, None] & (d > 0), 0.0, d)
        n = (d != 0).sum(1)
        h += d; cash -= d.sum(1) + np.abs(d).sum(1) * spr + n * gas
        legs += n; vol += np.abs(d).sum(1)

    def equity():
        return cash + h.sum(1) * (1 - spr)               # executable (bid) marks

    trade(np.outer(np.ones(N), tw) * EQ0 / (1 + spr), np.ones(N, bool))   # build at t0
    for t in range(HRS):
        if NEWDAY[t]:
            # NEWDAY labels interval START: anchor before its first return.
            day_eq = equity().copy(); halt_day[:] = False
        h *= np.exp(shock[:, t] + mu)
        E = equity()
        # risk checks every hour
        dd = 1 - E / np.maximum(peak, E)
        dl = 1 - E / day_eq
        f3 |= dl >= 0.03; f8 |= dd >= 0.08; f12 |= dd >= 0.12
        if pol.get("ladder"):
            halt_day |= dl >= 0.03; halt8 |= dd >= 0.08
            newcut = (dd >= 0.12) & ~cut12; cut12 |= newcut
            g = h.sum(1) / E
            sc = np.where(cut12 & (g > 0.40), 0.40 / np.maximum(g, 1e-9), 1.0)
            trade(h * (sc[:, None] - 1), sc < 1)
        if pol.get("lock") is not None:
            hit = (E / EQ0 - 1 >= pol["lock"]) & ~locked
            trade(-h, hit); locked |= hit
        if pol.get("trim") is not None:                  # hard-cap safety trims every hour (R4)
            E = equity(); w = h / E[:, None]
            over = w > 0.20
            trade(np.where(over, (pol["trim"] - w) * E[:, None], 0.0), over.any(1))
        E = equity()
        live = ~locked
        if pol.get("band") is not None and SCHED[t]:
            w = h / E[:, None]
            off = np.abs(w - tw) > pol["band"]
            trade(np.where(off, (tw - w) * E[:, None], 0.0), live & off.any(1))
        if pol.get("weekly") and MONDAY[t]:
            trade(tw * E[:, None] - h, live)
        if pol.get("rotate") and OPENS[t]:              # zero-edge churn: sell and re-buy at the open+30 round
            k = t % 4 if pol["rotate"] == "one" else slice(None)
            m = np.zeros((N, 4)); m[:, k] = 1
            sold = h * m
            trade(-sold, live); trade(sold * (1 - spr) / (1 + spr), live)
        E = equity()
        peak = np.maximum(peak, E); mdd = np.maximum(mdd, 1 - E / peak)
    trade(-h, np.ones(N, bool))                         # final flatten
    E = equity()
    peak = np.maximum(peak, E)
    mdd = np.maximum(mdd, 1 - E / peak)                 # include terminal gas
    pnl = cash - EQ0
    return pnl, mdd, legs, vol, f3, f8, f12

POL = {"P0 cash": None,
       "P1 E1 build+hold": {},
       "P2 80% (4x20%) hold": {"cap": 1},
       "P2a 80% + exact-cap trims": {"cap": 1, "trim": 0.20},
       "P2b 80% + trims to 18%": {"cap": 1, "trim": 0.18},
       "P3 E1 + weekly rebal": {"weekly": 1},
       "P4a E1 + band 1pp": {"band": 0.01},
       "P4b E1 + band 2pp": {"band": 0.02},
       "P4c E1 + band 4pp": {"band": 0.04},
       "P5 E1 + flatten at +6%": {"lock": 0.06},
       "P6 E1 + band2 + 3/8/12 ladder": {"band": 0.02, "ladder": 1},
       "P6b 80% + ladder": {"cap": 1, "ladder": 1},
       "P7a E1 + 1 name RT/session": {"rotate": "one"},
       "P7b E1 + whole book RT/session": {"rotate": "all"}}

if __name__ == "__main__":
    rng = np.random.default_rng(20261010)
    shock = simulate(rng)
    print(f"rho={RHO} N={N} volscale={VSCALE}; sessions with open rounds={OPENS.sum()} sched rounds={SCHED.sum()} "
          f"hours={HRS}; E1 gross={W_E1.sum():.3f}")
    basket = (shock @ (W_E1 / W_E1.sum())).sum(1)
    print(f"E1 basket run-horizon log-return sd (unlevered) {basket.std()*100:.2f}%")
    grid = list(itertools.product([0.0, 0.05, 0.08], [0.017, 0.035], [5, 15, 30, 50]))
    hdr = f"{'policy':32}{'prem':>5}{'gas':>6}{'spr':>4}{'E[pnl]':>8}{'E%':>7}{'sd%':>6}{'P(loss)':>8}{'E[MDD]%':>8}{'P(MDD>5%)':>10}{'legs':>6}{'vol USDT':>9}{'P3%':>6}{'P8%':>6}{'P12%':>6}"
    print(hdr)
    for (prem, gas, spr), (name, pol) in itertools.product(grid, POL.items()):
        if pol is None:
            print(f"{name:32}{prem:5.2f}{gas:6.3f}{spr:4d}{0:8.2f}{0:7.2f}{0:6.2f}{0:8.1%}{0:8.2f}{0:10.1%}{0:6.0f}{0:9.0f}"); continue
        pnl, mdd, legs, vol, f3, f8, f12 = run(shock, prem, gas, spr / 1e4, pol)
        print(f"{name:32}{prem:5.2f}{gas:6.3f}{spr:4d}{pnl.mean():8.3f}{pnl.mean()/2:7.3f}{pnl.std()/2:6.2f}{(pnl<0).mean():8.1%}"
              f"{mdd.mean()*100:8.2f}{(mdd>0.05).mean():10.1%}{legs.mean():6.1f}{vol.mean():9.0f}{f3.mean():6.1%}{f8.mean():6.1%}{f12.mean():6.2%}")

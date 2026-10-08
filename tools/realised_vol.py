"""Realised volatility of the five bStocks and their Ondo counterparts, from saved kit-source probe files.

Read-only: no network, no signing, no ai-seeds logging. Inputs are the raw probe captures in data/probe/
(git-ignored); this script only reads them.

Usage:
  python tools/realised_vol.py data/probe/candles_probe_<ts>.json data/probe/kit_sources_<ts>.json

Sources (both kit-provided or kit-named, IDEA-001 §11):
  - bStock daily candles: Web3 Open API `candles` (bar=1d), raw responses in candles_probe_*.json
  - Ondo daily klines: kit-named Skill `binance-tokenized-securities-info` (bapi dex/market/token/kline/ai),
    raw responses in kit_sources_*.json

Output per series: bars, date range, bars per year (measured), daily-bar volatility, annualised volatility
(sqrt(bars per year)), and the EWMA volatility at the last bar with a 20-bar half-life (Harvey et al. 2018 default).
Ondo daily bars skip most weekends, so a Monday bar's return spans the weekend.
"""
import json
import math
import sys
from datetime import datetime, timezone

TOKENS = ["NVDAB", "GOOGLB", "SKHYB", "TSLAB", "MSFTB"]
HALF_LIFE = 20


def day(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def stats(rows):
    """rows: list of (open_time_ms, close). Returns a dict of volatility statistics."""
    rows = sorted(dict(rows).items())
    closes = [c for _, c in rows]
    rets = [math.log(b / a) for a, b in zip(closes, closes[1:])]
    n = len(rets)
    mean = sum(rets) / n
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / (n - 1))
    span_days = (rows[-1][0] - rows[0][0]) / 86_400_000
    bars_per_year = len(rows) / span_days * 365
    lam = 0.5 ** (1 / HALF_LIFE)
    var = sum(r * r for r in rets[:HALF_LIFE]) / HALF_LIFE  # seed with the first 20 squared returns
    for r in rets[HALF_LIFE:]:
        var = lam * var + (1 - lam) * r * r
    return {
        "bars": len(rows), "first": day(rows[0][0]), "last": day(rows[-1][0]),
        "bars_per_year": bars_per_year, "vol_bar": sd, "vol_ann": sd * math.sqrt(bars_per_year),
        "ewma_ann": math.sqrt(var) * math.sqrt(bars_per_year),
    }


def bstock_series(path):
    raw = json.load(open(path))["raw"]
    daily = [r for r in raw if r.get("bar") == "1d" and isinstance(r["response"].get("data"), list)]
    # Two 1d calls per token (limits 300 and 150), in TOKENS order; keep the first of each pair.
    out = {}
    for tok, r in zip(TOKENS, daily[::2]):
        out[tok] = [(int(c[5]), float(c[3])) for c in r["response"]["data"]]
    return out


def ondo_series(path):
    d = json.load(open(path))
    rep, raw = d["report"]["B_tokenized_securities_info"], d["raw"]
    out = {}
    for tok in TOKENS:
        ondo = rep[tok]["ondo_token"]
        rows = []
        for r in raw:
            if ondo["contract"] in r.get("url", "") and "kline" in r["url"]:
                rows += [(int(k[0]), float(k[4])) for k in r["body"]["data"]["klineInfos"]]
        out[ondo["symbol"]] = rows
    return out


def main(candles_path, kit_path):
    series = {**bstock_series(candles_path), **ondo_series(kit_path)}
    print(f"{'series':8} {'bars':>5} {'first':>10} {'last':>10} {'bars/yr':>7} {'vol/bar':>8} {'ann.vol':>8} {'EWMA20':>8}")
    for name, rows in series.items():
        s = stats(rows)
        print(f"{name:8} {s['bars']:5d} {s['first']:>10} {s['last']:>10} {s['bars_per_year']:7.0f} "
              f"{s['vol_bar']:8.2%} {s['vol_ann']:8.1%} {s['ewma_ann']:8.1%}")


if __name__ == "__main__":
    main(*sys.argv[1:3])

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
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from larp.research.candles import capture_cutoff_ms, closed_bstock_bars

TOKENS = ["NVDAB", "GOOGLB", "SKHYB", "TSLAB", "MSFTB"]
HALF_LIFE = 20


def day(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def stats(rows):
    """rows: list of (open_time_ms, close). Returns a dict of volatility statistics."""
    if len(rows) != len(dict(rows)):
        raise ValueError("Duplicate timestamps require explicit reconciliation")
    rows = sorted(dict(rows).items())
    if len(rows) < HALF_LIFE + 1:
        raise ValueError("At least 21 finite, positive closed bars required for EWMA20")
    if any(not math.isfinite(c) or c <= 0 for _, c in rows):
        raise ValueError("Finite positive prices required")
    closes = [c for _, c in rows]
    rets = [math.log(b / a) for a, b in zip(closes, closes[1:])]
    n = len(rets)
    mean = sum(rets) / n
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / (n - 1))
    span_days = (rows[-1][0] - rows[0][0]) / 86_400_000
    bars_per_year = n / span_days * 365
    lam = 0.5 ** (1 / HALF_LIFE)
    var = sum(r * r for r in rets[:HALF_LIFE]) / HALF_LIFE  # seed with the first 20 squared returns
    for r in rets[HALF_LIFE:]:
        var = lam * var + (1 - lam) * r * r
    return {
        "bars": len(rows), "first": day(rows[0][0]), "last": day(rows[-1][0]),
        "bars_per_year": bars_per_year, "vol_bar": sd, "vol_ann": sd * math.sqrt(bars_per_year),
        "ewma_ann": math.sqrt(var) * math.sqrt(bars_per_year),
    }


def bstock_series(path, *, as_of_ms=None):
    with open(path, encoding="utf-8") as source:
        capture = json.load(source)
    bars = closed_bstock_bars(capture, "1d", 86_400_000, as_of_ms=as_of_ms)
    return {symbol: [(stamp, row[3]) for stamp, row in rows.items()] for symbol, rows in bars.items()}


def ondo_series(path, *, as_of_ms=None):
    d = json.load(open(path))
    cutoff = capture_cutoff_ms(d, as_of_ms)
    rep, raw = d["report"]["B_tokenized_securities_info"], d["raw"]
    out = {}
    for tok in TOKENS:
        ondo = rep.get(tok, {}).get("ondo_token")
        if not ondo:
            continue
        rows = {}
        for r in raw:
            if ondo["contract"] in r.get("url", "") and "kline" in r["url"]:
                body = r.get("body")
                if r.get("status") != 200 or r.get("error") or type(body) is not dict:
                    continue
                if body.get("success") is False or body.get("code") not in (None, 0, "000000", "0"):
                    continue
                for k in (body.get("data") or {}).get("klineInfos") or []:
                    if type(k) is not list or len(k) < 7:
                        raise ValueError("Malformed Ondo candle")
                    times = [k[0], k[6]]
                    for index, value in enumerate(times):
                        if type(value) is str and value.isdigit():
                            times[index] = int(value)
                        elif type(value) is not int:
                            raise ValueError("Ondo timestamps must be integer milliseconds")
                    if type(k[4]) is bool:
                        raise ValueError("Boolean Ondo close is invalid")
                    stamp, closed = times
                    close = float(k[4])
                    if stamp < 0 or closed < stamp or not math.isfinite(close) or close <= 0:
                        raise ValueError("Invalid Ondo candle")
                    if max(stamp + 86_400_000, closed + 1) > cutoff:
                        continue
                    if stamp in rows and rows[stamp] != close:
                        raise ValueError("Conflicting versions of a saved Ondo candle")
                    rows[stamp] = close
        out[ondo["symbol"]] = sorted(rows.items())
    return out


def main(candles_path, kit_path):
    series = {**bstock_series(candles_path), **ondo_series(kit_path)}
    print(f"{'series':8} {'bars':>5} {'first':>10} {'last':>10} {'bars/yr':>7} {'vol/bar':>8} {'ann.vol':>8} {'EWMA20':>8}")
    for name, rows in series.items():
        try:
            s = stats(rows)
        except ValueError as exc:
            print(f"{name}: MISSING/INVALID ({exc})")
            continue
        print(f"{name:8} {s['bars']:5d} {s['first']:>10} {s['last']:>10} {s['bars_per_year']:7.0f} "
              f"{s['vol_bar']:8.2%} {s['vol_ann']:8.1%} {s['ewma_ann']:8.1%}")


if __name__ == "__main__":
    main(*sys.argv[1:3])

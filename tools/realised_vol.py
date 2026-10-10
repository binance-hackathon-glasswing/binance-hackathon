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


def bstock_series(path, *, as_of_ms=None):
    with open(path, encoding="utf-8") as source:
        capture = json.load(source)
    raw = capture["raw"]
    if as_of_ms is None:
        captured = capture.get("report", {}).get("run_utc")
        if not captured:
            raise ValueError("Capture cutoff missing; supply explicit as_of_ms")
        cutoff = datetime.fromisoformat(captured.replace("Z", "+00:00"))
        if cutoff.tzinfo is None:
            raise ValueError("Capture cutoff needs timezone")
        as_of_ms = int(cutoff.timestamp() * 1000)
    # Legacy captures lack symbols on candle responses: use the explicit preceding
    # entity marker, never the position of a successful response in the array.
    out, current = {symbol: {} for symbol in TOKENS}, None
    for r in raw:
        if r.get("endpoint") == "rwa/underlying-market":
            current = r.get("symbol")
            if current not in out:
                raise ValueError("Unknown entity marker")
        if r.get("bar") != "1d":
            continue
        symbol = r.get("symbol", current)
        if symbol not in out:
            raise ValueError("Daily response lacks verified entity context")
        body = r.get("response", {})
        if body.get("code") != 0 or not isinstance(body.get("data"), list):
            continue
        for c in body["data"]:
            timestamp, close = int(c[5]), float(c[3])
            if timestamp + 86_400_000 > as_of_ms:
                continue  # never use the still-open calendar-day bar
            if timestamp in out[symbol] and out[symbol][timestamp] != close:
                raise ValueError("Conflicting versions of a saved candle")
            out[symbol][timestamp] = close
    return {symbol: sorted(rows.items()) for symbol, rows in out.items()}


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
        try:
            s = stats(rows)
        except ValueError as exc:
            print(f"{name}: MISSING/INVALID ({exc})")
            continue
        print(f"{name:8} {s['bars']:5d} {s['first']:>10} {s['last']:>10} {s['bars_per_year']:7.0f} "
              f"{s['vol_bar']:8.2%} {s['vol_ann']:8.1%} {s['ewma_ann']:8.1%}")


if __name__ == "__main__":
    main(*sys.argv[1:3])

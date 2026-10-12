"""Read-only probe: how much candle history does the Web3 Open API return for the five bStocks?

What it does (GET requests only; no signing of transactions, no ai-seeds log() calls):
  1. GET market/rwa/tokens        -> confirms the five tokens, prints underlyingTicker and statusInfo
  2. GET market/rwa/underlying-market (per token) -> prints the response fields, to see whether it
     carries underlying-share prices or only market status
  3. GET market/candles (per token, per bar) at the largest accepted `limit` -> how many rows come back,
     the oldest and newest timestamps, gaps, and whether one call returns the full history
  4. Optional (--try-paging): for a capped bar size, repeats the call with an extra `before`, `after`,
     `endTime` or `startTime` parameter to see whether older bars can be paged in (undocumented)

Credentials: BINANCE_API_KEY / BINANCE_SECRET_KEY from .env (same as binance_test.py). Nothing secret is
printed. Raw responses are saved under data/probe/ (git-ignored).

Usage:  python tools/probe_candles.py [--bars 1d,1h,15m] [--try-paging]
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.probe_http import ProbeStopped, envelope, stop_if_refused  # noqa: E402

BASE_URL = "https://web3.binance.com/build"
CHAIN_ID = "56"
TOKENS = {  # participant-kit.md K3
    "NVDAB": "0x02fca66c1d1afb4e2a7884261eb00f63598a7436",
    "GOOGLB": "0x3f53de71c126bdabae20f9cd64848d317f6c3238",
    "SKHYB": "0xca750ef65f295bbecd685abf54e82caf297bdb61",
    "TSLAB": "0x5b1910eaad6450e50f816082aa078c41f10c292f",
    "MSFTB": "0x80106cb3ead06659a5ad19df39d9b4733863b9b0",
}
MIN_INTERVAL_S = 0.35  # the kit's demo keeps >= 0.3 s between calls (K9)
BAR_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000, "1h": 3_600_000,
          "4h": 14_400_000, "1d": 86_400_000}

API_KEY = None
SECRET = None
RECV_WINDOW = None
_last_call = 0.0


def _ts():
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def get(path, params):
    """Signed GET (K5); stop the probe on authentication/compliance/rate refusal."""
    global _last_call
    query = "&".join(f"{quote(str(k), safe='')}={quote(str(v), safe='')}" for k, v in params.items())
    target = f"{path}?{query}" if query else path
    for attempt in range(4):
        wait = MIN_INTERVAL_S - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        ts = _ts()
        sign = base64.b64encode(hmac.new(SECRET.encode(), (ts + "GET" + "/build" + target).encode(),
                                         hashlib.sha256).digest()).decode()
        headers = {"X-OC-APIKEY": API_KEY, "X-OC-TIMESTAMP": ts, "X-OC-SIGN": sign}
        if RECV_WINDOW:
            headers["X-OC-RECV-WINDOW"] = RECV_WINDOW
        try:
            resp = requests.get(BASE_URL + target, headers=headers, timeout=20, allow_redirects=False)
        except requests.RequestException:
            _last_call = time.monotonic()
            body = {"code": None, "msg": "network error", "data": None}
            time.sleep(2 ** attempt)
            continue
        _last_call = time.monotonic()
        body = envelope(resp, (API_KEY, SECRET, sign))
        stop_if_refused(resp.status_code, body)
        return body
    return body


def iso(ms):
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def summarise(rows, bar, limit):
    if not rows:
        return {"rows": 0}
    try:
        if not isinstance(rows, list) or any(not isinstance(r, list) or len(r) < 6 for r in rows):
            raise ValueError("invalid candle rows")
        stamps = [int(r[5]) for r in rows]
        oldest, newest = iso(stamps[0]), iso(stamps[-1])
    except (TypeError, ValueError, OverflowError, OSError):
        return {"rows": 0, "note": "malformed candle rows"}
    step = BAR_MS.get(bar)
    gaps = sum(1 for a, b in zip(stamps, stamps[1:]) if step and b - a > step)
    return {
        "rows": len(rows),
        "oldest": oldest,
        "newest": newest,
        "span_days": round((stamps[-1] - stamps[0]) / 86_400_000, 1),
        "gaps": gaps,  # missing bars = periods with no trades (kit: only periods with trades are returned)
        "capped_by_limit": len(rows) >= limit,
    }


def candles(addr, bar, limit, raw, **extra):
    params = {"binanceChainId": CHAIN_ID, "tokenContractAddress": addr, "bar": bar, "limit": limit, **extra}
    body = get("/api/v1/dex/market/candles", params)
    raw.append({"bar": bar, "limit": limit, **extra, "response": body})
    return body


def find_max_limit(addr, raw, bar="1h"):
    """The server rejects large limits with 40001 'invalid limit range'; find the largest accepted value."""
    ok = lambda n: candles(addr, bar, n, raw).get("code") == 0
    good = next((n for n in (100, 50, 20, 10) if ok(n)), None)
    if good is None:
        return None
    bad = None
    while bad is None and good < 100_000:
        nxt = good * 2
        if ok(nxt):
            good = nxt
        else:
            bad = nxt
    while bad is not None and bad - good > 1:
        mid = (good + bad) // 2
        good, bad = (mid, bad) if ok(mid) else (good, mid)
    return good


def probe_candles(addr, bar, raw, max_limit):
    """Fetch at max_limit and at half of it: if the oldest bar is the same, the history is complete."""
    full = candles(addr, bar, max_limit, raw)
    if full.get("code") != 0:
        return {"rows": 0, "note": f"code {full.get('code')} {full.get('msg')}"}
    best = summarise(full.get("data") or [], bar, max_limit) | {"limit_used": max_limit}
    if not best["rows"]:
        return best | {"history": "no rows"}
    half = candles(addr, bar, max(1, max_limit // 2), raw)
    h = summarise(half.get("data") or [], bar, max_limit // 2) if half.get("code") == 0 else {}
    if h.get("oldest") == best["oldest"]:
        return best | {"history": "complete (same oldest bar at half the limit)"}
    return best | {"history": f"capped at {max_limit} bars per call - older bars need paging"}


def try_paging(addr, bar, oldest_ms, raw, max_limit):
    out = {}
    for name in ("before", "after", "endTime", "startTime"):
        val = oldest_ms if name in ("before", "endTime") else oldest_ms - 7 * 86_400_000
        body = candles(addr, bar, max_limit, raw, **{name: val})
        rows = (body.get("data") or []) if body.get("code") == 0 else []
        summary = summarise(rows, bar, max_limit)
        if summary.get("note"):
            out[name] = summary["note"]
            continue
        older = [r for r in rows if int(r[5]) < oldest_ms]
        out[name] = (f"code {body.get('code')}" if body.get("code") != 0
                     else f"{len(rows)} rows, {len(older)} older than the oldest seen")
    return out


def _main():
    global API_KEY, SECRET, RECV_WINDOW
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bars", default="1d,4h,1h,15m,1m")
    ap.add_argument("--try-paging", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    API_KEY, SECRET = os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_SECRET_KEY")
    RECV_WINDOW = os.getenv("BINANCE_RECV_WINDOW")
    if not API_KEY or not SECRET:
        sys.exit("BINANCE_API_KEY / BINANCE_SECRET_KEY missing from .env")
    raw, report = [], {"run_utc": _ts(), "tokens": {}}

    toks = get("/api/v1/dex/market/rwa/tokens", {"platformId": "bstock"})
    raw.append({"endpoint": "rwa/tokens", "response": toks})
    listed = {str(t.get("tokenContractAddress", "")).lower(): t for t in toks["data"]
              if isinstance(t, dict)} if toks.get("code") == 0 and isinstance(toks.get("data"), list) else {}
    print(f"rwa/tokens: code {toks.get('code')}, {len(listed)} tokens listed\n")

    max_limit = find_max_limit(TOKENS["NVDAB"], raw)
    report["max_limit"] = max_limit
    print(f"largest accepted candles limit: {max_limit}\n")
    if not max_limit:
        sys.exit("candles rejected even limit=10; see the raw file for the error")

    for sym, addr in TOKENS.items():
        info = listed.get(addr.lower(), {})
        print(f"== {sym} ({addr}) underlying={info.get('underlyingTicker')} "
              f"tokenToShareRatio={info.get('tokenToShareRatio')} tokenPrice={info.get('tokenPrice')} "
              f"referencePrice={info.get('referencePrice')} statusInfo={json.dumps(info.get('statusInfo'))}")
        um = get("/api/v1/dex/market/rwa/underlying-market",
                 {"binanceChainId": CHAIN_ID, "tokenContractAddress": addr})
        raw.append({"symbol": sym, "endpoint": "rwa/underlying-market", "response": um})
        data = um.get("data")
        sample = data[0] if isinstance(data, list) and data else data
        fields = sorted(sample) if isinstance(sample, dict) else type(sample).__name__
        print(f"   underlying-market: code {um.get('code')}; fields: {fields}")
        tok = {"underlying_market_fields": fields, "candles": {}}
        for bar in args.bars.split(","):
            s = probe_candles(addr, bar.strip(), raw, max_limit)
            tok["candles"][bar] = s
            print(f"   {bar:>4}: {s}")
        d1 = tok["candles"].get("1d", {}).get("oldest")
        for bar, summ in tok["candles"].items():  # finer bars that stop short of the daily history are capped
            if bar != "1d" and d1 and summ.get("oldest") and summ["oldest"][:10] > d1[:10]:
                summ["history"] = (f"capped: reaches back only to {summ['oldest']} "
                                   f"({summ['rows']} rows); daily bars go back to {d1}")
                print(f"   {bar:>4}: CAPPED - only back to {summ['oldest']} vs daily {d1}")
        capped = [b for b, v in tok["candles"].items() if str(v.get("history", "")).startswith("capped")]
        if args.try_paging and capped:
            pbar = "1h" if "1h" in capped else capped[0]
            oldest = datetime.strptime(tok["candles"][pbar]["oldest"], "%Y-%m-%d %H:%M")
            oldest_ms = int(oldest.replace(tzinfo=timezone.utc).timestamp() * 1000)
            tok["paging"] = {"bar": pbar} | try_paging(addr, pbar, oldest_ms, raw, max_limit)
            print(f"   paging: {tok['paging']}")
        report["tokens"][sym] = tok
        print()

    out_dir = Path("data/probe")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out_dir / f"candles_probe_{stamp}.json").write_text(json.dumps({"report": report, "raw": raw}, indent=1))
    (out_dir / f"candles_probe_{stamp}_summary.json").write_text(json.dumps(report, indent=1))
    print(f"Saved data/probe/candles_probe_{stamp}.json and _summary.json (git-ignored).")


def main():
    try:
        return _main()
    except ProbeStopped as exc:
        print(f"STOPPED: {exc.outcome}; no further API requests.")
        return 2


if __name__ == "__main__":
    sys.exit(main())

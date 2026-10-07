"""Read-only probe of the other data sources the participant kit names (Guide p.17-18, F-104).

No API keys, no signing, no ai-seeds calls. Public GET requests only.

  A. query-token-info skill:  token search / dynamic info on web3.binance.com, candles on dquery.sintral.io
  B. binance-tokenized-securities-info skill:  www.binance.com bapi rwa endpoints (stock list, dynamic, kline)
  C. binance skill (spot market data):  api.binance.com /api/v3 exchangeInfo + klines for <TICKER>BUSDT,
     and the data.binance.vision bulk files

For each source and each of the five bStocks it records: does it answer, how far back daily candles go
(paging until no older bars come back), and how its daily closes compare with the Web3 Open API candles
saved by tools/probe_candles.py (latest data/probe/candles_probe_*.json, if present).

Every response is saved with its URL, HTTP status, fetch time (UTC) and sha256 under data/probe/
(git-ignored). Run from the team network:   python tools/probe_kit_sources.py
"""
import glob
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from urllib.parse import urlencode

import requests

TOKENS = {  # participant-kit.md K3
    "NVDAB": "0x02fca66c1d1afb4e2a7884261eb00f63598a7436",
    "GOOGLB": "0x3f53de71c126bdabae20f9cd64848d317f6c3238",
    "SKHYB": "0xca750ef65f295bbecd685abf54e82caf297bdb61",
    "TSLAB": "0x5b1910eaad6450e50f816082aa078c41f10c292f",
    "MSFTB": "0x80106cb3ead06659a5ad19df39d9b4733863b9b0",
}
UNDERLYING = {"NVDAB": "NVDA", "GOOGLB": "GOOGL", "SKHYB": "SKHY", "TSLAB": "TSLA", "MSFTB": "MSFT"}
HEADERS = {"Accept-Encoding": "identity", "User-Agent": "binance-web3/2.0 (Skill)"}  # as the skills send
WEB3 = "https://web3.binance.com/bapi/defi"
BAPI = "https://www.binance.com/bapi/defi"
SINTRAL = "https://dquery.sintral.io/u-kline/v1/k-line/candles"
SPOT = "https://api.binance.com/api/v3"
VISION = "https://data.binance.vision/data/spot/monthly/klines"
DAY = 86_400_000
LAUNCH_FLOOR = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)  # paging stop guard

RAW = []
_last = 0.0


def fetch(url, params=None, binary=False):
    """GET with a 0.35 s spacing; never raises. Returns (status, parsed_json_or_bytes_or_None, error)."""
    global _last
    full = url + ("?" + urlencode(params) if params else "")
    wait = 0.35 - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    rec = {"url": full, "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds")}
    try:
        r = requests.get(full, headers=HEADERS, timeout=20)
        _last = time.monotonic()
        rec |= {"status": r.status_code, "sha256": hashlib.sha256(r.content).hexdigest(), "bytes": len(r.content)}
        if binary:
            RAW.append(rec)
            return r.status_code, r.content, None
        try:
            body = r.json()
        except ValueError:
            body = None
            rec["text"] = r.text[:500]
        rec["body"] = body
        RAW.append(rec)
        return r.status_code, body, None
    except requests.RequestException as e:
        _last = time.monotonic()
        rec["error"] = repr(e)[:300]
        RAW.append(rec)
        return None, None, repr(e)[:200]


def day(ms):
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def web3_api_closes():
    """Daily closes per token from the latest tools/probe_candles.py run (Web3 Open API, the kit's own data)."""
    files = sorted(f for f in glob.glob("data/probe/candles_probe_*.json") if not f.endswith("_summary.json"))
    if not files:
        return {}, None
    d = json.load(open(files[-1]))
    out, current = {}, None
    for r in d["raw"]:
        if "symbol" in r:  # the underlying-market call marks the start of each token's block
            current = r["symbol"]
        elif (current and current not in out and r.get("bar") == "1d" and len(r) == 3
              and r.get("response", {}).get("code") == 0):
            out[current] = {day(row[5]): float(row[3]) for row in r["response"]["data"]}
    return out, files[-1]


def compare(ref, other):
    common = sorted(set(ref) & set(other))
    if not common:
        return {"overlap_days": 0}
    diffs = [abs(other[k] / ref[k] - 1) * 1e4 for k in common if ref[k]]
    return {"overlap_days": len(common), "median_abs_diff_bp": round(median(diffs), 1),
            "max_abs_diff_bp": round(max(diffs), 1)}


def page_back(get_rows, ts_index, close_index, end_param_name, limit):
    """Generic paging: repeatedly ask for bars ending before the oldest seen. Returns {day: close}."""
    closes, end, calls = {}, None, 0
    while calls < 20:
        rows, err = get_rows(end)
        calls += 1
        if err or not rows:
            break
        new = {day(r[ts_index]): float(r[close_index]) for r in rows}
        before = len(closes)
        closes.update(new)
        oldest = min(int(r[ts_index]) for r in rows)
        if len(closes) == before or len(rows) < limit or oldest <= LAUNCH_FLOOR:
            break
        end = oldest - 1
    return closes, calls


# ---------------------------------------------------------------- A. query-token-info
def source_a():
    res = {}
    for sym, addr in TOKENS.items():
        r = {}
        st, body, err = fetch(f"{WEB3}/v4/public/wallet-direct/buw/wallet/market/token/dynamic/info/ai",
                              {"chainId": "56", "contractAddress": addr})
        data = (body or {}).get("data") if isinstance(body, dict) else None
        r["dynamic"] = {"status": st, "error": err, "code": (body or {}).get("code") if isinstance(body, dict) else None,
                        "fields": sorted(data)[:40] if isinstance(data, dict) else None,
                        "price": data.get("price") if isinstance(data, dict) else None}

        def rows(end):
            p = {"platform": "bsc", "address": addr, "interval": "1d", "limit": 500}
            if end:
                p["to"] = end
            s, b, e = fetch(SINTRAL, p)
            if e or s != 200 or not isinstance(b, dict):
                return None, e or f"HTTP {s}"
            d = b.get("data")
            if isinstance(d, dict):
                d = d.get("klineInfos") or d.get("candles") or d.get("list")
            return (d if isinstance(d, list) else None), None

        first, err = rows(None)
        if err or not first:
            r["kline"] = {"error": err or "no rows", "sample": str(RAW[-1].get("body"))[:300]}
        else:
            sample = first[-1]
            # rows are [open, high, low, close, volume, timestamp_ms, count] per the skill's docs
            closes, calls = page_back(rows, 5, 3, "to", 500)
            r["kline"] = {"rows_first_call": len(first), "sample_row": sample, "calls": calls,
                          "oldest": min(closes) if closes else None, "newest": max(closes) if closes else None,
                          "days": len(closes)}
            r["_closes"] = closes
        res[sym] = r
    return res


# ---------------------------------------------------------------- B. tokenized-securities-info (bapi)
def source_b():
    res = {"stock_list": {}}
    ondo_items = []
    for label, params in (("all_platforms", None), ("ondo_type1", {"type": 1})):
        st, body, err = fetch(f"{BAPI}/v1/public/wallet-direct/buw/wallet/market/token/rwa/stock/detail/list/ai",
                              params)
        items = body.get("data") if isinstance(body, dict) and isinstance(body.get("data"), list) else []
        ours = [i for i in items if str(i.get("contractAddress", "")).lower() in {a.lower() for a in TOKENS.values()}]
        same = [i for i in items if i.get("ticker") in UNDERLYING.values()]
        if label == "ondo_type1":
            ondo_items = same
        res["stock_list"][label] = {"status": st, "error": err, "items": len(items),
                                    "bstock_contracts_listed": len(ours),
                                    "same_tickers": [(i.get("symbol"), i.get("chainId"), i.get("type"))
                                                     for i in same][:20]}
    ondo_by_ticker = {}
    for it in sorted(ondo_items, key=lambda i: str(i.get("chainId")) != "56"):  # prefer BSC listings
        ondo_by_ticker.setdefault(it.get("ticker"), (it.get("symbol"), str(it.get("chainId")), it.get("contractAddress")))

    def kline_closes(chain, addr):
        def rows(end):
            p = {"chainId": chain, "contractAddress": addr, "interval": "1d", "limit": 300}
            if end:
                p["endTime"] = end
            s, b, e = fetch(f"{BAPI}/v1/public/wallet-direct/buw/wallet/dex/market/token/kline/ai", p)
            if e or s != 200 or not isinstance(b, dict):
                return None, e or f"HTTP {s}"
            d = b.get("data") or {}
            return (d.get("klineInfos") if isinstance(d, dict) else None), None
        # rows are [openTime, open, high, low, close, reserved, closeTime]
        return page_back(rows, 0, 4, "endTime", 300)

    for sym, addr in TOKENS.items():
        r = {}
        st, body, err = fetch(f"{BAPI}/v2/public/wallet-direct/buw/wallet/market/token/rwa/dynamic/ai",
                              {"chainId": "56", "contractAddress": addr})
        data = body.get("data") if isinstance(body, dict) else None
        r["rwa_dynamic_on_bstock"] = {"status": st, "error": err,
                                      "code": body.get("code") if isinstance(body, dict) else None,
                                      "fields": sorted(data)[:40] if isinstance(data, dict) else None}
        closes, calls = kline_closes("56", addr)
        r["kline_on_bstock"] = {"days": len(closes), "calls": calls,
                                "oldest": min(closes) if closes else None, "newest": max(closes) if closes else None}
        r["_closes"] = closes
        if UNDERLYING[sym] in ondo_by_ticker:
            osym, ochain, oaddr = ondo_by_ticker[UNDERLYING[sym]]
            oc, ocalls = kline_closes(str(ochain), oaddr)
            r["ondo_token"] = {"symbol": osym, "chainId": ochain, "contract": oaddr, "days": len(oc),
                               "oldest": min(oc) if oc else None, "newest": max(oc) if oc else None}
        res[sym] = r
    return res


# ---------------------------------------------------------------- C. Binance spot (public market data)
def source_c():
    res = {}
    symbols = [f"{s}USDT" for s in TOKENS]
    st, body, err = fetch(f"{SPOT}/exchangeInfo", {"symbols": json.dumps(symbols, separators=(",", ":"))})
    listed = {s["symbol"]: s.get("status") for s in body.get("symbols", [])} if isinstance(body, dict) else {}
    res["exchangeInfo"] = {"status": st, "error": err, "listed": listed,
                           "msg": body.get("msg") if isinstance(body, dict) else None}
    for sym in TOKENS:
        pair = f"{sym}USDT"
        st, body, err = fetch(f"{SPOT}/klines", {"symbol": pair, "interval": "1d", "startTime": LAUNCH_FLOOR,
                                                "limit": 1000})
        if isinstance(body, list) and body:
            closes = {day(row[0]): float(row[4]) for row in body}
            res[sym] = {"status": st, "days": len(closes), "oldest": min(closes), "newest": max(closes),
                        "_closes": closes}
        else:
            res[sym] = {"status": st, "error": err, "body": str(body)[:200]}
        month = None
        if res[sym].get("oldest"):
            month = res[sym]["oldest"][:7]
        if month:
            st2, content, err2 = fetch(f"{VISION}/{pair}/1d/{pair}-1d-{month}.zip", binary=True)
            res[sym]["data_binance_vision"] = {"month": month, "status": st2, "error": err2,
                                               "bytes": len(content) if content else 0}
    return res


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ref, ref_file = web3_api_closes()
    print(f"Web3 Open API reference closes: {ref_file or 'none found (run tools/probe_candles.py first)'}\n")
    report = {"run_utc": stamp, "reference_file": ref_file}
    for name, fn in (("A_query_token_info", source_a), ("B_tokenized_securities_info", source_b),
                     ("C_binance_spot", source_c)):
        print(f"== {name}")
        try:
            res = fn()
        except Exception as e:  # keep going; record the failure
            res = {"crashed": repr(e)[:300]}
        for sym in TOKENS:
            entry = res.get(sym)
            if isinstance(entry, dict) and entry.get("_closes") is not None and sym in ref:
                entry["vs_web3_api"] = compare(ref[sym], entry["_closes"])
        printable = {k: ({kk: vv for kk, vv in v.items() if kk != "_closes"} if isinstance(v, dict) else v)
                     for k, v in res.items()}
        for k, v in printable.items():
            print(f"   {k}: {json.dumps(v, default=str)[:600]}")
        report[name] = printable
        print()
    out = Path("data/probe")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"kit_sources_{stamp}.json").write_text(json.dumps({"report": report, "raw": RAW}, indent=1, default=str))
    (out / f"kit_sources_{stamp}_summary.json").write_text(json.dumps(report, indent=1, default=str))
    print(f"Saved data/probe/kit_sources_{stamp}.json and _summary.json (git-ignored).")


if __name__ == "__main__":
    main()

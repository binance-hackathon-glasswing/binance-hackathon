"""Read-only quote probe for the run-host test (IDEA-010 §7 action 2) and the first quote-cost sample (GAP-50).

Run it on a candidate host (e.g. a Singapore cloud VM) to check that the Web3 Open API answers signed calls
and returns executable quotes from that host's IP, and to measure the round-trip cost of each bStock.

What it does (GET requests only):
  1. GET aggregator/supported/chain       -> signed-read check; a 40304 "compliance restriction" here means
                                            this host's IP is refused (E-15); stop and do not work around it (G-17)
  2. GET market/rwa/tokens                -> decimals and statusInfo (openState, marketStatus, reasonCode) per token
  3. per token and size: GET aggregator/quote-and-swap
       buy  quote  USDT -> token  for <size> USDT
       sell quote  token -> USDT  for exactly the token amount the buy quote returned
     round-trip cost = 1 - (sell proceeds / buy cost), both from quotes (IDEA-009 §D.5)
  4. clock check: local UTC vs the API envelope's `timestamp`

What it never does: sign or broadcast a transaction, call approve, call ai-seeds `log()`, or read
WALLET_PRIVATE_KEY, WALLET_MNEMONIC or AI_SEEDS_SECRET. "Quotes are free and don't check balances" (Guide p.7),
so any public address works as --address (use the dev wallet's public address). Quote results are simulated
costs, not realised fills (ledger rule 4).

Credentials: BINANCE_API_KEY / BINANCE_SECRET_KEY from .env (same as binance_test.py); ideally a separate
Developer Portal key for probes and loggers (IDEA-010 §7 action 3). Nothing secret is printed or saved.
Raw responses (URL, HTTP status, fetch time, sha256) go to data/probe/ (git-ignored).

Usage:  python tools/probe_quote.py --address 0x<public address> [--sizes 10,25] [--symbols NVDAB,MSFTB]
Exit code: 0 all checks passed; 1 some quote or call failed; 2 the host is refused (40304) or signed reads fail.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import socket
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

BASE_URL = "https://web3.binance.com/build"
CHAIN_ID = "56"
USDT = "0x55d398326f99059fF775485246999027B3197955"  # BSC USDT, 18 decimals (K3)
USDT_DECIMALS = 18
TOKENS = {  # participant-kit.md K3
    "NVDAB": "0x02fca66c1d1afb4e2a7884261eb00f63598a7436",
    "GOOGLB": "0x3f53de71c126bdabae20f9cd64848d317f6c3238",
    "SKHYB": "0xca750ef65f295bbecd685abf54e82caf297bdb61",
    "TSLAB": "0x5b1910eaad6450e50f816082aa078c41f10c292f",
    "MSFTB": "0x80106cb3ead06659a5ad19df39d9b4733863b9b0",
}
COMPLIANCE_CODE = 40304
MIN_INTERVAL_S = 0.35  # the kit's demo keeps >= 0.3 s between calls (K9)

load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
SECRET = os.getenv("BINANCE_SECRET_KEY")
RECV_WINDOW = os.getenv("BINANCE_RECV_WINDOW")
RAW = []
_last_call = 0.0


def _ts():
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def get(path, params):
    """Signed GET (K5). Returns (http_status, envelope, local_ms_at_response); never raises on API errors."""
    global _last_call
    query = "&".join(f"{quote(str(k), safe='')}={quote(str(v), safe='')}" for k, v in params.items())
    target = f"{path}?{query}" if query else path
    status, body, local_ms = None, {"code": None, "msg": "no attempt", "data": None}, None
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
        fetched = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        try:
            resp = requests.get(BASE_URL + target, headers=headers, timeout=20)
        except requests.RequestException as exc:
            status, body = None, {"code": None, "msg": f"network error: {type(exc).__name__}", "data": None}
            RAW.append({"path": path, "params": params, "fetched_utc": fetched, "status": None, "error": body["msg"]})
            _last_call = time.monotonic()
            time.sleep(2 ** attempt)
            continue
        _last_call = time.monotonic()
        local_ms = int(time.time() * 1000)
        status = resp.status_code
        try:
            body = resp.json()
        except ValueError:
            body = {"code": None, "msg": f"HTTP {status}, not JSON", "data": None}
        RAW.append({"path": path, "params": params, "fetched_utc": fetched, "status": status,
                    "sha256": hashlib.sha256(resp.content).hexdigest(), "response": body})
        if status == 429 or body.get("code") == 42900:
            time.sleep(int(resp.headers.get("Retry-After", 2 ** attempt)))
            continue
        return status, body, local_ms
    return status, body, local_ms


def first(data):
    """quote-and-swap and rwa endpoints may wrap the payload in a list."""
    if isinstance(data, list):
        return data[0] if data else {}
    return data or {}


def units(amount_str, decimals):
    return Decimal(str(amount_str)) / (Decimal(10) ** int(decimals))


def quote_swap(amount_smallest, from_addr, to_addr, address, slippage):
    params = {"binanceChainId": CHAIN_ID, "amount": str(amount_smallest), "fromTokenAddress": from_addr,
              "toTokenAddress": to_addr, "userWalletAddress": address, "vendor": "LiquidMesh",
              "slippagePercent": slippage}
    status, body, _ = get("/api/v1/dex/aggregator/quote-and-swap", params)
    if body.get("code") != 0:
        return None, f"code {body.get('code')} {body.get('msg')} (HTTP {status})"
    d = first(body.get("data"))
    rr, tx = d.get("routerResult") or {}, d.get("tx") or {}
    if rr.get("toTokenAmount") in (None, ""):
        return None, "no toTokenAmount in response"
    return {"toTokenAmount": rr.get("toTokenAmount"), "priceImpactPercent": rr.get("priceImpactPercent"),
            "estimateGasFee": rr.get("estimateGasFee"), "vendorName": rr.get("vendorName"),
            "tx_to": tx.get("to"), "tx_gas": tx.get("gas"), "minReceiveAmount": tx.get("minReceiveAmount"),
            "executionMode": d.get("executionMode")}, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--address", required=True, help="public wallet address used as userWalletAddress (no key needed)")
    ap.add_argument("--sizes", default="10", help="buy sizes in USDT, comma-separated (default 10)")
    ap.add_argument("--symbols", default=",".join(TOKENS), help="subset of the five bStocks")
    ap.add_argument("--slippage", default="1", help="slippagePercent sent with each quote (default 1)")
    args = ap.parse_args()

    if not API_KEY or not SECRET:
        sys.exit("BINANCE_API_KEY / BINANCE_SECRET_KEY not found in .env")
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", args.address):
        sys.exit("--address must be a 0x-prefixed 40-hex-character public address")
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    unknown = [s for s in symbols if s not in TOKENS]
    if unknown:
        sys.exit(f"not an eligible bStock: {unknown} (F-91)")
    sizes = [Decimal(s.strip()) for s in args.sizes.split(",") if s.strip()]
    # Presence only, never values: a probe host should not hold wallet or ai-seeds secrets (IDEA-010 §7).
    present = [n for n in ("WALLET_PRIVATE_KEY", "WALLET_MNEMONIC", "AI_SEEDS_SECRET") if os.getenv(n)]
    if present:
        print(f"WARNING: {', '.join(present)} set on this host; a probe host does not need them.")

    started = datetime.now(timezone.utc)
    summary = {"started_utc": started.isoformat(timespec="seconds"), "hostname": socket.gethostname(),
               "address": args.address, "sizes_usdt": [str(s) for s in sizes], "slippage": args.slippage,
               "checks": {}, "quotes": []}
    failures = 0

    # 1. Signed read + compliance check
    status, body, local_ms = get("/api/v1/dex/aggregator/supported/chain", {"binanceChainId": CHAIN_ID})
    code = body.get("code")
    summary["checks"]["signed_read"] = {"http": status, "code": code, "msg": body.get("msg")}
    print(f"Signed read (supported/chain): HTTP {status}, code {code}")
    if code == COMPLIANCE_CODE or status in (401, 403):
        print("REFUSED: this host cannot use the Web3 API. Do not use a VPN or relay (G-17); choose another host.")
        return finish(summary, 2)
    if code != 0:
        print(f"FAILED signed read: {body.get('msg')}")
        return finish(summary, 2)

    # 4. Clock check against the API envelope timestamp (ms)
    if isinstance(body.get("timestamp"), (int, float)) and local_ms:
        skew = local_ms - int(body["timestamp"])
        summary["checks"]["clock_skew_ms_vs_api"] = skew
        print(f"Clock: local - API = {skew} ms (includes network latency; G-05 threshold 500 ms)")

    # 2. Decimals and market state
    status, body, _ = get("/api/v1/dex/market/rwa/tokens", {"platformId": "bstock"})
    info = {}
    if body.get("code") == 0:
        for row in body.get("data") or []:  # a flat list of tokens (probe_candles.py, K6a)
            if not isinstance(row, dict):
                continue
            addr = str(row.get("tokenContractAddress", "")).lower()
            for sym, a in TOKENS.items():
                if a == addr:
                    info[sym] = {"decimals": row.get("decimals"), "statusInfo": row.get("statusInfo")}
    else:
        failures += 1
        print(f"rwa/tokens failed: code {body.get('code')} {body.get('msg')}")
    summary["checks"]["rwa_tokens"] = info

    # 3. Buy and sell quotes
    print(f"\n{'symbol':7} {'size':>6} {'open':>5} {'buy impact%':>11} {'sell impact%':>12} {'round trip bp':>13}")
    for sym in symbols:
        st = (info.get(sym) or {}).get("statusInfo") or {}
        open_state = st.get("openState")
        dec = (info.get(sym) or {}).get("decimals")
        for size in sizes:
            rec = {"symbol": sym, "size_usdt": str(size), "openState": open_state,
                   "marketStatus": st.get("marketStatus"), "reasonCode": st.get("reasonCode"),
                   "quoted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            buy, err = quote_swap(int(size * 10 ** USDT_DECIMALS), USDT, TOKENS[sym], args.address, args.slippage)
            rec["buy"], rec["buy_error"] = buy, err
            sell = None
            if buy:
                sell, err = quote_swap(buy["toTokenAmount"], TOKENS[sym], USDT, args.address, args.slippage)
                rec["sell"], rec["sell_error"] = sell, err
            if buy and sell:
                proceeds = units(sell["toTokenAmount"], USDT_DECIMALS)
                rt_bp = (1 - proceeds / size) * 10_000
                rec["round_trip_cost_bp"] = float(round(rt_bp, 2))
                if dec is not None:
                    qty = units(buy["toTokenAmount"], dec)
                    rec["tokens_bought"] = str(qty)
                    rec["buy_price_usdt"] = str(round(size / qty, 6)) if qty else None
                rt = f"{rt_bp:13.1f}"
            else:
                failures += 1
                rt = f"{'FAILED':>13}"
            summary["quotes"].append(rec)
            print(f"{sym:7} {str(size):>6} {str(open_state):>5} "
                  f"{str((buy or {}).get('priceImpactPercent')):>11} {str((sell or {}).get('priceImpactPercent')):>12} {rt}"
                  + (f"  ({rec.get('buy_error') or rec.get('sell_error')})" if not (buy and sell) else ""))
    if not info:
        print("Note: decimals unknown (rwa/tokens failed); token quantities not reported.")
    return finish(summary, 1 if failures else 0)


def finish(summary, code):
    summary["exit_code"] = code
    out = Path("data/probe")
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out / f"quote_probe_{stamp}.json").write_text(json.dumps(RAW, indent=1, default=str), encoding="utf-8")
    (out / f"quote_probe_{stamp}_summary.json").write_text(json.dumps(summary, indent=1, default=str),
                                                           encoding="utf-8")
    print(f"\nSaved data/probe/quote_probe_{stamp}.json and _summary.json (git-ignored). Exit code {code}.")
    return code


if __name__ == "__main__":
    sys.exit(main())

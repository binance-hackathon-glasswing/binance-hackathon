"""EXP-008 snapshot: underlying daily closes (Yahoo chart API) and kit token 1-hour candles (read-only GETs).

Writes data/exp008/underlying.json and data/exp008/tokens.json (git-ignored) and prints their SHA-256.
Usage:  python tools/exp008/fetch.py [--env PATH_TO_.env]
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import tools.probe_candles as pc  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "data" / "exp008"
UNDERLYING = {"NVDAB": "NVDA", "GOOGLB": "GOOGL", "TSLAB": "TSLA", "MSFTB": "MSFT", "SKHYB": "000660.KS"}
START, END = 1527811200, 1792713600  # 2018-06-01, 2026-10-23 00:00 UTC
CUTOFF_MS = END * 1000


def underlying():
    out = {}
    for token, ticker in UNDERLYING.items():
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                         params={"period1": START, "period2": END, "interval": "1d"},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        closes = res["indicators"]["quote"][0]["close"]
        out[token] = {"ticker": ticker, "currency": res["meta"]["currency"],
                      "tz": res["meta"]["exchangeTimezoneName"],
                      "rows": [[t, c] for t, c in zip(res["timestamp"], closes) if c is not None]}
        time.sleep(1)
    return out


def tokens():
    out = {}
    for sym, addr in pc.TOKENS.items():
        rows, after = {}, None
        while True:
            extra = {"after": after} if after else {}
            body = pc.candles(addr, "1h", 300, [], **extra)
            if body.get("code") != 0:
                raise SystemExit(f"{sym}: code {body.get('code')} {body.get('msg')}")
            page = [r for r in body.get("data") or [] if int(r[5]) + 3_600_000 <= CUTOFF_MS]
            new = [r for r in page if int(r[5]) not in rows]
            for r in page:
                rows[int(r[5])] = r
            if not new:
                break
            after = min(int(r[5]) for r in page) - 1
        out[sym] = [rows[k] for k in sorted(rows)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default=".env")
    args = ap.parse_args()
    load_dotenv(args.env)
    pc.API_KEY, pc.SECRET = os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_SECRET_KEY")
    pc.RECV_WINDOW = os.getenv("BINANCE_RECV_WINDOW")
    if not pc.API_KEY or not pc.SECRET:
        sys.exit("BINANCE_API_KEY / BINANCE_SECRET_KEY missing")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in (("underlying", underlying()), ("tokens", tokens())):
        path = OUT / f"{name}.json"
        path.write_text(json.dumps(data, sort_keys=True))
        print(name, hashlib.sha256(path.read_bytes()).hexdigest(),
              {k: len(v["rows"] if isinstance(v, dict) else v) for k, v in data.items()})


if __name__ == "__main__":
    main()

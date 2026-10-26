"""IDEA-106 snapshot: kit 1-hour token candles (T) and underlying daily closes (P), read-only.

T goes through the production history transport (TH-01, IDEA-105: Web3Client + MarketPort, exact decimals, raw
artifacts) paging `market/candles` with `after=`; P through the Yahoo chart API as in EXP-008. Writes
data/idea106/{tokens,underlying}.json (git-ignored) plus raw/ and prints their SHA-256. GET requests only.
Usage:  python -m tools.idea106.fetch [--env-file .env] [--out DIR]
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import requests

from larp.marketdata.port import TOKENS
from larp.marketdata.web3 import credentials
from tools.th01_candle_timestamps import production_port

OUT = Path(__file__).resolve().parents[2] / 'data' / 'idea106'
UNDERLYING = dict(NVDAB='NVDA', GOOGLB='GOOGL', TSLAB='TSLA', MSFTB='MSFT', SKHYB='000660.KS')
START, END = 1527811200, 1793059200  # 2018-06-01, 2026-10-27 00:00 UTC (covers the Oct 26 close)
CUTOFF_MS = 1793044800000  # 2026-10-26 20:00 UTC = NYSE close (EDT): bars must end by then
MAX_PAGES = 400


def tokens(port):
    out = {}
    for symbol in sorted(TOKENS):
        rows, after = {}, None
        for _ in range(MAX_PAGES):
            page = port.candles(symbol, bar='1h', limit=300, after=after)['rows']
            page = [r for r in page if int(r[5]) + 3_600_000 <= CUTOFF_MS]
            new = [r for r in page if int(r[5]) not in rows]
            for r in page:
                rows[int(r[5])] = r
            if not new:
                break
            after = min(int(r[5]) for r in page) - 1
            time.sleep(0.4)
        else:
            raise SystemExit(f'{symbol}: more than {MAX_PAGES} pages')
        out[symbol] = [rows[k] for k in sorted(rows)]
        print(f'{symbol}: {len(out[symbol])} bars', file=sys.stderr)
    return out


def underlying():
    out = {}
    for token, ticker in UNDERLYING.items():
        r = requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}',
                         params=dict(period1=START, period2=END, interval='1d'),
                         headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        r.raise_for_status()
        res = r.json()['chart']['result'][0]
        closes = res['indicators']['quote'][0]['close']
        out[token] = dict(ticker=ticker, currency=res['meta']['currency'], tz=res['meta']['exchangeTimezoneName'],
                          rows=[[t, c] for t, c in zip(res['timestamp'], closes) if c is not None])
        time.sleep(1)
    return out


def _write(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--env-file', default='.env')
    parser.add_argument('--out', default=str(OUT))
    args = parser.parse_args(argv)
    out = Path(args.out).expanduser()
    out.mkdir(mode=0o700, parents=True)  # a new snapshot only
    port = production_port(credentials(args.env_file if Path(args.env_file).is_file() else None), out / 'raw')
    hashes = dict(tokens=_write(out / 'tokens.json', tokens(port)),
                  underlying=_write(out / 'underlying.json', underlying()))
    print(json.dumps(dict(status='IDEA106_SNAPSHOT_WRITTEN', out=str(out), sha256=hashes), sort_keys=True))


if __name__ == '__main__':
    main()

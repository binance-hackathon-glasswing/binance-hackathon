"""Read-only quote collection at configured sizes. No wallet signing or ai-seeds client."""
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from statistics import median
import subprocess
import time

from .port import MarketPort, TOKENS, integer, units
from .web3 import Artifacts, Unavailable, Web3Client, credentials, single, utc


def cycle(port, sizes, symbols):
    report = dict(schema='QuoteCycle.v1', started_at=utc(), wallet=port.wallet, observations=[])
    for symbol in symbols:
        for size in sizes:
            item = dict(symbol=symbol, size_usdt=str(size))
            try:
                buy = port.observe(dict(schema='MarketRequest.v1', symbol=symbol, side='BUY',
                    amount_kind='EXACT_IN', pay_asset='USDT', pay_units=units(size, 6), pay_decimals=6))
                item.update(token_open=buy['token_open'], underlying_open=buy['underlying_open'], buy=buy)
                amount = buy['quote_measurement']['receive_units']
                decimals = buy['quote_measurement']['receive_decimals']
                sell = port.observe(dict(schema='MarketRequest.v1', symbol=symbol, side='SELL',
                    amount_kind='EXACT_IN', pay_asset=symbol, pay_units=amount, pay_decimals=decimals))
                item['sell'] = sell
                # Quoted net loss includes any fees already reflected in received amounts; gas is separate.
                proceeds = Decimal(sell['quote_measurement']['receive_units']) / 10**18
                item['quoted_roundtrip_bps'] = str((size - proceeds) * 10000 / size)
                item['effective_quoted_spread_bps'] = str(20000 * (size - proceeds) / (size + proceeds))
                item['measurement'] = 'SEQUENTIAL_BUY_AND_SELL_QUOTES; prices can move between calls'
                item['gas_estimates'] = {}
                for side, observation in (('BUY', buy), ('SELL', sell)):
                    tx = observation['quote_measurement']['unsigned_transaction']
                    try:
                        estimate = port.client.request('POST', 'pre-transaction/gas-limit', dict(
                            binanceChainId='56', evmTx={'from': port.wallet, 'to': tx['to'],
                            'data': tx['data'], 'value': str(tx['value'])}))
                        item['gas_estimates'][side] = dict(status='OBSERVED', gas_limit=single(estimate)['gasLimit'],
                                                          artifact_sha256=estimate['artifact_sha256'])
                    except Unavailable as e:
                        item['gas_estimates'][side] = dict(status='UNAVAILABLE', reason=str(e))
                        if str(e) in ('compliance_restriction', 'http_forbidden_unclassified', 'authentication_error', 'rate_limited'):
                            raise
                item['status'] = 'MEASURED_NONEXECUTABLE'
            except Unavailable as e:
                item.update(status='UNAVAILABLE', reason=str(e))
                report['observations'].append(item)
                if str(e) in ('compliance_restriction', 'http_forbidden_unclassified', 'authentication_error', 'rate_limited'):
                    report.update(finished_at=utc(), stopped=str(e))
                    return report
                continue
            report['observations'].append(item)
    report['candles'] = {}
    for symbol in symbols:
        try:
            report['candles'][symbol] = port.candles(symbol, bar='1h', limit=300)
        except Unavailable as e:
            report['candles'][symbol] = dict(status='UNAVAILABLE', reason=str(e))
            if str(e) in ('compliance_restriction', 'http_forbidden_unclassified', 'authentication_error', 'rate_limited'):
                report['stopped'] = str(e)
                break
    report['finished_at'] = utc()
    return report


def summarize(root):
    reports = []
    for path in Path(root).glob('*.json'):
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != path.stem:
            raise Unavailable('artifact summary integrity failure')
        value = json.loads(raw)
        if value.get('schema') == 'QuoteCycle.v1':
            reports.append((path.stem, value))
    result = dict(schema='QuoteSummary.v1', cycle_count=len(reports), artifact_hashes=[h for h, _ in reports], symbols={})
    if reports:
        result.update(first_at=min(r['started_at'] for _, r in reports), last_at=max(r['finished_at'] for _, r in reports))
    for symbol in TOKENS:
        items = [x for _, r in reports for x in r['observations'] if x['symbol'] == symbol]
        costs = [Decimal(x['quoted_roundtrip_bps']) for x in items if 'quoted_roundtrip_bps' in x]
        impacts = [Decimal(x[side]['quote_measurement']['impact_bps']) for x in items
                   for side in ('buy', 'sell') if side in x]
        spreads = [Decimal(x['effective_quoted_spread_bps']) for x in items if 'effective_quoted_spread_bps' in x]
        latencies = [x[side]['quote_measurement']['elapsed_ms'] for x in items for side in ('buy', 'sell')
                     if side in x and type(x[side]['quote_measurement'].get('elapsed_ms')) is int]
        result['symbols'][symbol] = dict(samples=len(items), successful_pairs=len(costs),
            open_samples=sum(x.get('token_open') is True and x.get('underlying_open') is True for x in items),
            roundtrip_bps_median=str(median(costs)) if costs else None,
            roundtrip_bps_min=str(min(costs)) if costs else None,
            roundtrip_bps_max=str(max(costs)) if costs else None,
            impact_bps_median=str(median(impacts)) if impacts else None,
            effective_quoted_spread_bps_median=str(median(spreads)) if spreads else None,
            effective_quoted_spread_bps_min=str(min(spreads)) if spreads else None,
            effective_quoted_spread_bps_max=str(max(spreads)) if spreads else None,
            quote_latency_ms_median=median(latencies) if latencies else None,
            quote_latency_ms_max=max(latencies) if latencies else None,
            spread_convention='SEQUENTIAL_EFFECTIVE_QUOTED_PRICES; includes reflected fees and price movement',
            failures=[x.get('reason') for x in items if x.get('status') == 'UNAVAILABLE'])
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-file', default='.env')
    p.add_argument('--address')
    p.add_argument('--sizes', default='40')
    p.add_argument('--symbols', default=','.join(TOKENS))
    p.add_argument('--artifact-root', required=True)
    p.add_argument('--interval-seconds', type=int, default=3600)
    p.add_argument('--cycles', type=int, default=1, help='0 runs continuously')
    p.add_argument('--balance-only', action='store_true')
    p.add_argument('--summary-only', action='store_true')
    args = p.parse_args(argv)
    if args.summary_only:
        print(json.dumps(summarize(args.artifact_root), sort_keys=True))
        return 0
    if args.interval_seconds < 60 or args.cycles < 0:
        p.error('interval must be >=60 seconds; cycles must be nonnegative')
    sizes = [Decimal(x) for x in args.sizes.split(',')]
    symbols = args.symbols.split(',')
    if not sizes or any(not x.is_finite() or x <= 0 for x in sizes) or any(s not in TOKENS for s in symbols):
        p.error('positive sizes and eligible symbols required')
    env = credentials(args.env_file)
    artifacts = Artifacts(args.artifact_root)
    port = MarketPort(Web3Client(env['BINANCE_API_KEY'], env['BINANCE_SECRET_KEY'], artifacts=artifacts),
                      args.address or env.get('AI_SEEDS_ADDRESS'))
    if args.balance_only:
        result = port.balances()
        print('balance artifact:', result['artifact_sha256'])
        assets = single(result)['tokenAssets']
        native = [x for x in assets if str(x.get('tokenContractAddress', '')).lower() in ('', '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')]
        print('BNB raw balance:', integer(native[0]['rawBalance']) if len(native) == 1 else 'NO_NATIVE_ENTRY')
        return 0
    count = 0
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    while args.cycles == 0 or count < args.cycles:
        start = time.monotonic()
        report = cycle(port, sizes, symbols)
        report['code_revision'] = revision
        sha = artifacts.put(report)
        print(report['finished_at'], 'cycle artifact:', sha, flush=True)
        count += 1
        if report.get('stopped'):
            print('collection stopped:', report['stopped'], flush=True)
            return 1
        if args.cycles == 0 or count < args.cycles:
            time.sleep(max(0, args.interval_seconds - (time.monotonic() - start)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

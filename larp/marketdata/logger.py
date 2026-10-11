"""Read-only quote collection at configured sizes. No wallet signing or ai-seeds client."""
import argparse
from decimal import Decimal
from pathlib import Path
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
                item['gas_estimate_status'] = 'NOT_ESTIMATED_BEFORE_APPROVAL; quoted gas is not an executable estimate'
                item['status'] = 'MEASURED_NONEXECUTABLE'
            except Unavailable as e:
                item.update(status='UNAVAILABLE', reason=str(e))
                report['observations'].append(item)
                if str(e) in ('compliance_restriction', 'authentication_error', 'rate_limited'):
                    report.update(finished_at=utc(), stopped=str(e))
                    return report
                continue
            report['observations'].append(item)
    report['finished_at'] = utc()
    return report


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
    args = p.parse_args(argv)
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
    while args.cycles == 0 or count < args.cycles:
        start = time.monotonic()
        report = cycle(port, sizes, symbols)
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

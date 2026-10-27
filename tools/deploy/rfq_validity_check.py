"""OBS03-B2-RV01 read-only RFQ validity measurement (IDEA-104): how long a fresh quote's calldata stays executable.

    python -m tools.deploy.rfq_validity_check [--env-file .env] [--rounds 6] [--pay-units 15000000]
        [--rpc-url https://bsc-dataseed.bnbchain.org] [--out NEW_DIR] [--packet FILE]

For each round and each of the five bStocks: one BUY quote (USDT -> bStock, dev wallet, LiquidMesh, 0.2 % slippage),
then `eth_estimateGas` of that quote's exact calldata on a public read RPC, with a USDT balance and router-allowance
state override, immediately and at target ages 1, 2, 3, 5, 8, 12, 20 and 30 s after the quote response. Probing
stops after two RFQ failures in a row or after the 30 s probe. Every probe records its actual start age (monotonic).
Each quote also records its route legs' `dexProtocol.dexName` (RFQ makers are named "Rfq ...") and any packed or
word-aligned calldata value that reads as a Unix time within ±1 h, as offsets from the block and response times.

Read-only: the Web3 client allows only `aggregator/quote-and-swap`; the RPC refuses every call shape except the
reads and override simulations listed in `allowed_call`, before any network access. Only the Web3 key pair is
loaded from the env file; there is no signer, wallet key, submit path, AWS or database. Raw quote responses go to a
new private directory outside the checkout. The printed packet holds public values only (calldata as fingerprints)
and is scanned for the credentials, RPC URL and wallet before printing.

Exit 0 for DONE, 2 for NOT_RUN (override not proven), 4 for a tool or input error.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.request import Request, build_opener

from larp.execution import USDT
from larp.marketdata.port import TOKENS
from larp.marketdata.web3 import Artifacts, NoRedirect, Unavailable, Web3Client, credentials, single
from tools.deploy.replay_router_readonly import public_bytes

ROUTER = '0xb44446b0c8e56988c34f7ff73ae904982b5fdda5'
SWAP_SELECTOR = '0xad43f73d'
DEV_WALLET = '0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479'
PUBLIC_RPC = 'https://bsc-dataseed.bnbchain.org'  # BSC_BNBCHAIN_PUBLIC
ALLOWANCE_CALL, BALANCE_OF_CALL = '0xdd62ed3e', '0x70a08231'
USDT_BALANCE_SLOT, USDT_ALLOWANCE_SLOT = 1, 2  # LD02c, proven again before every run (RV-3)
OVERRIDE_BALANCE, OVERRIDE_ALLOWANCE = 10**30, 2**255
TARGETS = (0, 1, 2, 3, 5, 8, 12, 20, 30)
ARRIVED_EXPIRED_AGE_S = 2.0
TIMESTAMP_WINDOW_S = 3600


class QuoteOnlyClient(Web3Client):
    endpoints = frozenset({('GET', 'aggregator/quote-and-swap')})


class RpcRefused(ValueError):
    """A JSON-RPC error from the provider (a revert, for a simulation)."""

    def __init__(self, error):
        super().__init__('RPC_REFUSED')
        self.message = str(error.get('message', '')) if type(error) is dict else ''

    def reason(self):
        found = re.search(r'RFQ_[A-Za-z]+', self.message)
        if found:
            return found.group(0)
        if 'revert' not in self.message.lower():
            return 'RPC_ERROR'
        reason = re.findall(r'Error\(([A-Za-z][A-Za-z0-9_ ]{0,59})', self.message)
        return 'REVERTED:' + reason[-1].strip() if reason else 'REVERTED'


def word(value):
    return format(value, '064x')


def mapping_slot(key, slot):
    from eth_utils import keccak
    position = word(slot if type(slot) is int else int(slot, 16))
    return '0x' + keccak(bytes.fromhex(str(key)[2:].rjust(64, '0') + position)).hex()


def override(wallet):
    return {USDT: {'stateDiff': {
        mapping_slot(wallet, USDT_BALANCE_SLOT): '0x' + word(OVERRIDE_BALANCE),
        mapping_slot(ROUTER, mapping_slot(wallet, USDT_ALLOWANCE_SLOT)): '0x' + word(OVERRIDE_ALLOWANCE)}}}


def allowed_call(method, params, scope):
    """RV-1: the only call shapes this tool may send."""
    if type(params) is not list:
        return False
    if method == 'eth_chainId':
        return params == []
    if method == 'eth_getBlockByNumber':
        return params == ['latest', False]
    tx = params[0] if params and type(params[0]) is dict else None
    if tx is None or len(params) != 3 or params[1] != 'latest' or params[2] != override(scope['wallet']):
        return False
    data = str(tx.get('data', ''))
    padded = scope['wallet'][2:].rjust(64, '0')
    if method == 'eth_call':
        return (set(tx) == {'to', 'data'} and tx['to'] == USDT
                and data in (BALANCE_OF_CALL + padded, ALLOWANCE_CALL + padded + ROUTER[2:].rjust(64, '0')))
    if method == 'eth_estimateGas':
        return (set(tx) == {'from', 'to', 'data', 'value'} and tx['from'] == scope['wallet'] and tx['to'] == ROUTER
                and tx['value'] == '0x0' and data.startswith(SWAP_SELECTOR) and data in scope['calldata'])
    return False


class Rpc:
    def __init__(self, url, scope, *, opener=None, timeout=20):
        if not url.startswith('https://'):
            raise ValueError('RPC_URL_REFUSED')
        self.url, self.scope, self.timeout = url, scope, timeout
        self.opener = opener or build_opener(NoRedirect())

    def __call__(self, method, params):
        if not allowed_call(method, params, self.scope):
            raise ValueError('RPC_CALL_REFUSED')
        body = json.dumps(dict(jsonrpc='2.0', id=1, method=method, params=params)).encode()
        request = Request(self.url, data=body, headers={'Content-Type': 'application/json'})
        with self.opener.open(request, timeout=self.timeout) as response:
            reply = json.loads(response.read(2 * 1024 * 1024))
        if type(reply) is dict and type(reply.get('error')) is dict:
            raise RpcRefused(reply['error'])
        if type(reply) is not dict or 'result' not in reply:
            raise ValueError('RPC_REFUSED')
        return reply['result']


def fingerprint(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def timestamp_offsets(data, chain_ts, response_ts):
    """Packed or word-aligned values in the calldata that read as Unix seconds (4 bytes) or ms (6 bytes) within ±1 h of
    the latest block time; offsets are from that block time and from the quote response's wall-clock time."""
    raw = bytes.fromhex(data[2:] if data.startswith('0x') else data)
    found = []
    for size, unit, scale in ((4, 's', 1), (6, 'ms', 1000)):
        for i in range(4, len(raw) - size + 1):
            value = int.from_bytes(raw[i:i + size], 'big') / scale
            if raw[i] != 0 and abs(value - chain_ts) <= TIMESTAMP_WINDOW_S:
                found.append(dict(byte_offset=i, unit=unit, offset_vs_block_s=round(value - chain_ts, 3),
                                  offset_vs_response_s=round(value - response_ts, 3)))
    return found


def route_names(quote):
    """Each route leg's `dexProtocol.dexName` (an RFQ maker shows as e.g. "Rfq ...") and percentage."""
    names = []
    for leg in ((quote.get('routerResult') or {}).get('dexRouterList') or [])[:8]:
        protocol = leg.get('dexProtocol') if isinstance(leg, dict) else None
        if isinstance(protocol, dict) and isinstance(protocol.get('dexName'), str):
            names.append(dict(dex=re.sub(r'[^ -~]', '?', protocol['dexName'])[:40],
                              percent=re.sub(r'[^0-9.]', '', str(protocol.get('percent', '')))[:8]))
    return names


def is_rfq(quote):
    return any('rfq' in r['dex'].lower() for r in route_names(quote))


def classify(probes):
    """Observed bounds per quote; a probe result is a gas integer or a reason string."""
    ok = [p['age_s'] for p in probes if isinstance(p['result'], int)]
    rfq = [p for p in probes if str(p['result']).startswith('RFQ_')]
    other = [p for p in probes if not isinstance(p['result'], int) and not str(p['result']).startswith('RFQ_')]
    first = probes[0] if probes else None
    return dict(
        rfq_failing=bool(rfq),
        arrived_expired=bool(first and first['result'] == 'RFQ_OrderExpired' and first['age_s'] <= ARRIVED_EXPIRED_AGE_S),
        last_success_age_s=max(ok) if ok else None,
        first_rfq_failure_age_s=min(p['age_s'] for p in rfq) if rfq else None,
        first_rfq_reason=rfq[0]['result'] if rfq else None,
        other_failures=sorted({str(p['result']) for p in other}))


def probe_quote(rpc, wallet, data, t0, *, clock, sleep):
    state = override(wallet)
    probes, rfq_streak = [], 0
    for target in TARGETS:
        wait = t0 + target - clock()
        if wait > 0:
            sleep(wait)
        start = clock()
        try:
            result = int(rpc('eth_estimateGas', [dict(to=ROUTER, data=data, value='0x0', **{'from': wallet}),
                                                 'latest', state]), 16)
        except RpcRefused as error:
            result = error.reason()
        except Exception as error:  # transport failure: recorded, never retried
            result = 'ERROR:' + type(error).__name__
        probes.append(dict(target_s=target, age_s=round(start - t0, 3), rpc_ms=round((clock() - start) * 1000)))
        probes[-1]['result'] = result
        rfq_streak = rfq_streak + 1 if str(result).startswith('RFQ_') else 0
        if rfq_streak >= 2:
            break
    return probes


def prove_override(rpc, wallet):
    """RV-3: the overridden balance and allowance must be what the token reports."""
    padded = wallet[2:].rjust(64, '0')
    state = override(wallet)
    balance = int(rpc('eth_call', [dict(to=USDT, data=BALANCE_OF_CALL + padded), 'latest', state]), 16)
    allowance = int(rpc('eth_call', [dict(to=USDT, data=ALLOWANCE_CALL + padded + ROUTER[2:].rjust(64, '0')),
                                     'latest', state]), 16)
    return dict(balance_override_effective=balance == OVERRIDE_BALANCE,
                allowance_override_effective=allowance == OVERRIDE_ALLOWANCE)


def summarize(quotes):
    by_symbol = {}
    for q in quotes:
        s = by_symbol.setdefault(q['symbol'], dict(quotes=0, rfq_routes=0, rfq_failing=0, arrived_expired=0, bounds=[],
                                                    short_encoded_times_vs_response_s=[],
                                                    max_success_age_s_non_rfq=None))
        s['quotes'] += 1
        if q.get('rfq_route'):
            s['rfq_routes'] += 1
            s['short_encoded_times_vs_response_s'] += [v['offset_vs_response_s'] for v in q['timestamp_values']
                                                       if v['offset_vs_response_s'] < 60]
        c = q.get('classification')
        if not c:
            continue
        if c['rfq_failing']:
            s['rfq_failing'] += 1
            s['arrived_expired'] += int(c['arrived_expired'])
            if not c['arrived_expired']:
                s['bounds'].append([c['last_success_age_s'], c['first_rfq_failure_age_s']])
        elif c['last_success_age_s'] is not None:
            s['max_success_age_s_non_rfq'] = max(s['max_success_age_s_non_rfq'] or 0, c['last_success_age_s'])
    failing = [q for q in quotes if q.get('classification', {}).get('rfq_failing')]
    if not failing:
        verdict = 'INCONCLUSIVE_NO_RFQ_FAILURE_OBSERVED'
    elif all(q['classification']['arrived_expired'] for q in failing):
        verdict = 'ALL_RFQ_FAILURES_ARRIVED_EXPIRED'
    elif not any(q['classification']['arrived_expired'] for q in failing):
        verdict = 'RFQ_VALIDITY_WINDOW_OBSERVED'
    else:
        verdict = 'MIXED'
    return by_symbol, verdict


def utc_iso():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def run(args, *, client=None, rpc_factory=None, credentials_source=credentials, clock=time.monotonic, sleep=time.sleep, wallclock=time.time):
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix='larp-rfq-validity-'))
    wallet = DEV_WALLET
    scope = dict(wallet=wallet, calldata=set())
    selected = credentials_source(args.env_file, environ={})  # the Web3 key pair only; never a wallet key
    keys = (selected['BINANCE_API_KEY'], selected['BINANCE_SECRET_KEY'])
    forbidden = [*keys, args.rpc_url, wallet, wallet[2:]]
    client = client or QuoteOnlyClient(*keys, artifacts=Artifacts(out / 'web3'))
    rpc = (rpc_factory or Rpc)(args.rpc_url, scope)
    if int(rpc('eth_chainId', []), 16) != 56:
        raise ValueError('CHAIN_NOT_56')
    packet = dict(schema='RfqValidityCheck.v1', generated_utc=utc_iso(), signing_enabled=False,
                  claims='Read-only quotes and override simulations; observed outcomes, not a guaranteed TTL.',
                  side='BUY', pay_units=args.pay_units, slippage_percent='0.2', targets_s=list(TARGETS),
                  rpc_fingerprint=fingerprint(args.rpc_url), rounds=args.rounds,
                  enable_rfq='false' if args.disable_rfq else 'default')
    proof = prove_override(rpc, wallet)
    packet['override_proof'] = proof
    if not all(proof.values()):
        packet['status'] = 'NOT_RUN'
        return 2, public_bytes(packet, forbidden)
    quotes = []
    for round_no in range(args.rounds):
        for symbol, token in TOKENS.items():
            row = dict(round=round_no, symbol=symbol, quoted_utc=utc_iso())
            quotes.append(row)
            params = dict(binanceChainId='56', amount=str(args.pay_units * 10**12), fromTokenAddress=USDT,
                          toTokenAddress=token, userWalletAddress=wallet, vendor='LiquidMesh', slippagePercent='0.2')
            try:
                if args.disable_rfq:
                    # RV02-2: an unprobed default quote first, for the route choice and output comparison.
                    default = single(client.request('GET', 'aggregator/quote-and-swap', params))
                    row['default_quote'] = dict(route_names=route_names(default), rfq_route=is_rfq(default),
                                                to_amount=int(default['routerResult']['toTokenAmount']))
                    params = dict(params, enableRFQ='false')
                begin = clock()
                q = single(client.request('GET', 'aggregator/quote-and-swap', params))
                int(q['routerResult']['toTokenAmount'])
            except (Unavailable, KeyError, TypeError, ValueError) as error:
                row['quote_error'] = re.sub(r'[^ -~]', '?', str(error))[:80]
                continue
            t0 = clock()
            row['quote_request_ms'] = round((t0 - begin) * 1000)
            tx = q.get('tx') or {}
            data = str(tx.get('data', ''))
            if str(tx.get('to', '')).lower() != ROUTER or not data.startswith(SWAP_SELECTOR):
                row['quote_error'] = 'NOT_PINNED_ROUTER'
                continue
            scope['calldata'].add(data)
            response_ts = wallclock() - (clock() - t0)
            block = rpc('eth_getBlockByNumber', ['latest', False])
            chain_ts = int(block['timestamp'], 16)
            row.update(calldata=fingerprint(data), calldata_bytes=(len(data) - 2) // 2,
                       execution_mode=q.get('executionMode'), rfq_field_null=q.get('rfq') is None,
                       route_names=route_names(q), quoted_gas=int(tx['gas']) if tx.get('gas') else None,
                       block_age_at_quote_s=round(wallclock() - chain_ts, 3),
                       rfq_route=is_rfq(q), to_amount=int(q['routerResult']['toTokenAmount']),
                       timestamp_values=timestamp_offsets(data, chain_ts, response_ts))
            if 'default_quote' in row:
                base = row['default_quote']['to_amount']
                row['default_minus_no_rfq_bp'] = round((base - row['to_amount']) * 10000 / base, 2) if base else None
            row['probes'] = probe_quote(rpc, wallet, data, t0, clock=clock, sleep=sleep)
            row['classification'] = classify(row['probes'])
            scope['calldata'].discard(data)
    packet['quotes'] = quotes
    packet['by_symbol'], packet['verdict'] = summarize(quotes)
    packet['status'] = 'DONE'
    packet['finished_utc'] = utc_iso()
    return 0, public_bytes(packet, forbidden)


def parse(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--env-file', default='.env')
    parser.add_argument('--rounds', type=int, default=6)
    parser.add_argument('--pay-units', type=int, default=15_000_000, help='USDT in micro units (10^6)')
    parser.add_argument('--rpc-url', default=PUBLIC_RPC)
    parser.add_argument('--out', help='new private directory for raw quote responses')
    parser.add_argument('--packet', help='also write the public packet here')
    parser.add_argument('--disable-rfq', action='store_true',
                        help='RV02: probe quotes requested with enableRFQ=false, each after an unprobed default quote')
    args = parser.parse_args(argv)
    if not 1 <= args.rounds <= 12 or not 1_000_000 <= args.pay_units <= 100_000_000:
        parser.error('rounds must be 1..12 and pay units 1..100 USDT')
    return args


def main(argv=None, **ports):
    try:
        args = parse(argv)
        code, raw = run(args, **ports)
    except SystemExit:
        raise
    except Exception as error:
        own = str(error) if re.fullmatch(r'[A-Z0-9_]+', str(error)) else ''
        print(json.dumps(dict(error='RFQ_VALIDITY_REFUSED', reason=type(error).__name__ + (':' + own if own else ''))))
        return 4
    if args.packet:
        Path(args.packet).write_bytes(raw)
    sys.stdout.write(raw.decode())
    return code


if __name__ == '__main__':
    raise SystemExit(main())

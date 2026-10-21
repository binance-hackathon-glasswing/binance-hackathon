# LD02c read-only check (IDEA-070 LD02c): RFQ order validity and execution-RPC read qualification.
# Run on primary only, never the signer. Prints one sanitized JSON packet and its SHA-256. No file, service, config,
# ledger or AWS change; no transaction or signature. Quotes and RPC answers stay in memory.
set -eu
cd /opt/larp/current
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
from datetime import datetime, timezone
import hashlib
import json
import re
import time

ROUTER = '0xb44446b0c8e56988c34f7ff73ae904982b5fdda5'
SWAP_SELECTOR = '0xad43f73d'
FACET_SLOT = '0x7ddc1c45a5ae31800e181de98e8cb97525e9b89f99e5829d49f25a8ca4bac1d7'
FUNDING_TX = '0x24683de219c18cc78a2d7aeb37c94e733a6a383b1c3a58d3a403f95df7da5c55'  # IDEA-039 FG-01, public
ALLOWANCE_CALL, APPROVE_CALL, BALANCE_OF_CALL = '0xdd62ed3e', '0x095ea7b3', '0x70a08231'
USDT_BALANCE_SLOT, USDT_ALLOWANCE_SLOT, OVERRIDE_ALLOWANCE = 1, 2, 2**255
DELAYS = (0, 3, 6, 10, 15, 20, 30, 45, 60, 90)
READ_METHODS = ('eth_chainId', 'eth_getBlockByNumber', 'eth_getBalance', 'eth_getTransactionCount',
                'eth_getTransactionByHash', 'eth_getTransactionReceipt', 'eth_getCode', 'eth_getStorageAt', 'eth_call')
ROUTE_KEY = re.compile(r'rfq|mode|vendor|expir|valid|deadline|route|dex|source|adapter|type', re.I)
OWN_CODES = frozenset(('RPC_CALL_REFUSED', 'RPC_METHOD_REFUSED', 'RPC_REFUSED', 'SANITIZER_URL',
                       'SANITIZER_FORBIDDEN_VALUE', 'NO_PROVIDERS'))


def fingerprint(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def plain(text):
    """Printable ASCII (others as '?'), at most 160 characters; anything with a URL is 'FILTERED'."""
    text = str(text)
    if '://' in text:
        return 'FILTERED'
    shown = ''.join(c if ' ' <= c <= '~' else '?' for c in text)
    return shown if len(shown) <= 160 else shown[:160] + f'...[{len(shown)} chars]'


def refusal(error):
    text = str(error)
    return dict(error='LD02C_REFUSED', signing_enabled=False,
                reason=type(error).__name__ + (':' + text if text in OWN_CODES else ''))


class RpcRefused(ValueError):
    def __init__(self, error):
        super().__init__('RPC_REFUSED')
        self.error = error

    def reason(self):
        message = str(self.error.get('message', ''))
        found = re.search(r'RFQ_[A-Za-z]+', message)
        return found.group(0) if found else ('reverted' if 'revert' in message.lower() else plain(message)[:60])


def word_hex(value):
    return format(value, '064x')


def mapping_slot(key, slot):
    from eth_utils import keccak
    position = word_hex(slot if type(slot) is int else int(slot, 16))
    return '0x' + keccak(bytes.fromhex(str(key)[2:].rjust(64, '0') + position)).hex()


def allowed_call(method, params, scope):
    """The only call shapes sent: execution's read methods, and swap simulations of exact fresh calldata."""
    tx = params[0] if params and type(params[0]) is dict else {}
    data = str(tx.get('data', ''))

    def override_ok(value):
        return (type(value) is dict and set(value) == {scope['usdt']} and set(value[scope['usdt']]) == {'stateDiff'}
                and len(value[scope['usdt']]['stateDiff']) == 1)
    if method in ('eth_chainId', 'eth_getBlockByNumber', 'eth_getBalance', 'eth_getTransactionCount',
                  'eth_getTransactionByHash', 'eth_getTransactionReceipt', 'eth_getCode', 'eth_getStorageAt'):
        return True
    if method == 'eth_call':
        return (data[:10] in (ALLOWANCE_CALL, BALANCE_OF_CALL) and tx.get('to') in scope['tokens']
                and (len(params) == 2 or (len(params) == 3 and override_ok(params[2]))))
    if method == 'eth_estimateGas':
        return (set(tx) <= {'from', 'to', 'data', 'value'} and tx.get('from') == scope['wallet']
                and tx.get('value', '0x0') == '0x0' and tx.get('to') == ROUTER and data in scope['calldata']
                and len(params) == 3 and override_ok(params[2]))
    return False


def rpc(url, method, params, scope, log=None):
    from urllib.request import Request, build_opener
    from larp.marketdata.web3 import NoRedirect
    if not url.startswith('https://'):
        raise ValueError('RPC_METHOD_REFUSED')
    if not allowed_call(method, params, scope):
        raise ValueError('RPC_CALL_REFUSED')
    body = json.dumps(dict(jsonrpc='2.0', id=1, method=method, params=params)).encode()
    start = time.monotonic()
    with build_opener(NoRedirect()).open(Request(url, data=body, headers={'Content-Type': 'application/json'}),
                                         timeout=20) as response:
        reply = json.loads(response.read(2 * 1024 * 1024))
    if log is not None:
        log.append((method, round((time.monotonic() - start) * 1000)))
    if type(reply) is dict and type(reply.get('error')) is dict:
        raise RpcRefused(reply['error'])
    if type(reply) is not dict or 'result' not in reply:
        raise ValueError('RPC_REFUSED')
    return reply['result']


def route_markers(record):
    """R1: field names of the quote response and short scalar values of routing-like fields."""
    data = record['response']['data']
    q = data[0] if isinstance(data, list) and len(data) == 1 else data
    rr = q.get('routerResult') or {}
    def scalars(d):
        return {k: (v if isinstance(v, (bool, int, float)) or v is None else plain(v)[:80]) for k, v in d.items()
                if ROUTE_KEY.search(k) and (isinstance(v, (bool, int, float, str)) or v is None)}
    lists = {}
    for k, v in rr.items():
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            lists[k] = [{kk: (plain(vv)[:60] if isinstance(vv, str) else vv) for kk, vv in x.items()
                         if ROUTE_KEY.search(kk) and isinstance(vv, (str, int, float, bool))} for x in v[:6]]
    return dict(top_level_keys=sorted(q), router_result_keys=sorted(rr), top_level=scalars(q), router_result=scalars(rr),
                router_result_lists=lists)


def timeline(results):
    """R3: observed bounds only."""
    ok = [d for d, r in results if isinstance(r, int)]
    bad = [d for d, r in results if not isinstance(r, int)]
    return dict(last_success_s=max(ok) if ok else None, first_failure_s=min(bad) if bad else None,
                failures_after_success=bool(ok and bad and min(bad) > min(ok)))


def rfq_check(url, scope, quotes, sleep=time.sleep, clock=time.monotonic):
    """R2: simulate each quote's exact calldata at fixed delays after the quote, all symbols per step."""
    from larp.execution import USDT
    block = rpc(url, 'eth_getBlockByNumber', ['latest', False], scope)['number']
    balance = int(rpc(url, 'eth_getStorageAt', [USDT, mapping_slot(scope['wallet'], USDT_BALANCE_SLOT), block],
                      scope), 16)
    slot = mapping_slot(ROUTER, mapping_slot(scope['wallet'], USDT_ALLOWANCE_SLOT))
    override = {USDT: {'stateDiff': {slot: '0x' + word_hex(OVERRIDE_ALLOWANCE)}}}
    seen = int(rpc(url, 'eth_call', [dict(to=USDT, data=ALLOWANCE_CALL + scope['wallet'][2:].rjust(64, '0')
                                          + ROUTER[2:].rjust(64, '0')), 'latest', override], scope), 16)
    proof = dict(balance_slot_matches=balance == scope['usdt_units'], override_effective=seen == OVERRIDE_ALLOWANCE)
    out = dict(proof=proof, delays_s=list(DELAYS), symbols={})
    if not all(proof.values()):
        return dict(out, status='NOT_RUN', reason='allowance override not proven')
    results = {s: [] for s in quotes}
    for delay in DELAYS:
        for symbol, q in quotes.items():
            wait = q['t0'] + delay - clock()
            if wait > 0:
                sleep(wait)
            try:
                gas = int(rpc(url, 'eth_estimateGas', [{'from': scope['wallet'], 'to': ROUTER, 'data': q['data'],
                                                        'value': '0x0'}, 'latest', override], scope), 16)
                results[symbol].append((delay, gas))
            except RpcRefused as error:
                results[symbol].append((delay, error.reason()))
            except Exception as error:
                results[symbol].append((delay, type(error).__name__))
    for symbol, rows in results.items():
        out['symbols'][symbol] = dict(results={str(d): r for d, r in rows}, **timeline(rows))
    return dict(out, status='DONE')


def rpc_check(providers, scope, wallet):
    """Q1-Q3: every execution read method on each provider, with latency and cross-provider agreement."""
    from larp.execution import USDT
    from eth_utils import keccak
    rows = {}
    for p in providers:
        log, r = [], {}
        def call(name, method, params):
            try:
                r[name] = dict(ok=True, value=rpc(p['url'], method, params, scope, log))
            except RpcRefused as error:
                r[name] = dict(ok=False, error=error.reason())
            except Exception as error:
                r[name] = dict(ok=False, error=type(error).__name__)
        call('chain_id', 'eth_chainId', [])
        call('latest', 'eth_getBlockByNumber', ['latest', False])
        call('finalized', 'eth_getBlockByNumber', ['finalized', False])
        block = r['finalized']['value']['number'] if r['finalized']['ok'] else 'latest'
        call('balance', 'eth_getBalance', [wallet, block])
        call('nonce_latest', 'eth_getTransactionCount', [wallet, 'latest'])
        call('nonce_pending', 'eth_getTransactionCount', [wallet, 'pending'])
        call('tx', 'eth_getTransactionByHash', [FUNDING_TX])
        call('receipt', 'eth_getTransactionReceipt', [FUNDING_TX])
        call('router_code', 'eth_getCode', [ROUTER, block])
        call('facet_slot', 'eth_getStorageAt', [ROUTER, FACET_SLOT, block])
        call('usdt_balance_of', 'eth_call', [dict(to=USDT, data=BALANCE_OF_CALL + wallet[2:].rjust(64, '0')), block])
        call('usdt_allowance', 'eth_call', [dict(to=USDT, data=ALLOWANCE_CALL + wallet[2:].rjust(64, '0')
                                                  + ROUTER[2:].rjust(64, '0')), block])
        v = {k: x.get('value') for k, x in r.items()}
        summary = dict(
            methods_ok={k: x['ok'] for k, x in r.items()},
            errors={k: x['error'] for k, x in r.items() if not x['ok']},
            chain_id=int(v['chain_id'], 16) if r['chain_id']['ok'] else None,
            latest_block=int(v['latest']['number'], 16) if r['latest']['ok'] else None,
            finalized_block=int(v['finalized']['number'], 16) if r['finalized']['ok'] else None,
            nonce=[int(v[k], 16) if r[k]['ok'] else None for k in ('nonce_latest', 'nonce_pending')],
            tx_found=bool(r['tx']['ok'] and v['tx']),
            receipt=None if not (r['receipt']['ok'] and v['receipt']) else dict(
                status=int(v['receipt']['status'], 16), block=int(v['receipt']['blockNumber'], 16),
                gas_used=int(v['receipt']['gasUsed'], 16)),
            router_codehash=('0x' + keccak(bytes.fromhex(v['router_code'][2:])).hex()) if r['router_code']['ok'] else None,
            facet='0x' + v['facet_slot'][-40:] if r['facet_slot']['ok'] else None,
            usdt_units=int(v['usdt_balance_of'], 16) if r['usdt_balance_of']['ok'] else None,
            usdt_allowance=int(v['usdt_allowance'], 16) if r['usdt_allowance']['ok'] else None,
            latency_ms={m: [ms for mm, ms in log if mm == m] for m in READ_METHODS})
        rows[p['source_id']] = summary
    values = list(rows.values())
    concurrent = finalized_pairs(providers, scope)
    agree = dict(
        chain_56=all(s['chain_id'] == 56 for s in values),
        receipt=len({json.dumps(s['receipt'], sort_keys=True) for s in values}) == 1 and values[0]['receipt'] is not None,
        router_codehash=len({s['router_codehash'] for s in values}) == 1 and values[0]['router_codehash'] is not None,
        facet=len({s['facet'] for s in values}) == 1 and values[0]['facet'] is not None,
        finalized_within_10=(None not in [s['finalized_block'] for s in values]
                             and max(s['finalized_block'] for s in values) - min(s['finalized_block'] for s in values) <= 10),
        every_method_ok_everywhere=all(all(s['methods_ok'].values()) for s in values))
    agree_q2b = dict(agree, finalized_within_10=concurrent['within_10'])
    return dict(providers=rows, agreement=agree, status='PASS' if all(agree.values()) else 'FAIL',
                finalized_concurrent=concurrent, status_q2b='PASS' if all(agree_q2b.values()) else 'FAIL')


def finalized_pairs(providers, scope, rounds=3):
    """Q2b: `finalized` from every provider at the same moment (threads started together), `rounds` times."""
    from concurrent.futures import ThreadPoolExecutor
    pairs = []
    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        for _ in range(rounds):
            futures = [pool.submit(rpc, p['url'], 'eth_getBlockByNumber', ['finalized', False], scope) for p in providers]
            try:
                pairs.append([int(f.result()['number'], 16) for f in futures])
            except Exception as error:
                pairs.append(type(error).__name__)
    ok = [p for p in pairs if isinstance(p, list)]
    return dict(pairs=pairs, within_10=bool(ok) and len(ok) == len(pairs) and all(max(p) - min(p) <= 10 for p in ok))


def sanitize(text, forbidden):
    if '://' in text:
        raise ValueError('SANITIZER_URL')
    low = text.lower()
    for value in forbidden:
        if value and len(value) >= 6 and value.lower() in low:
            raise ValueError('SANITIZER_FORBIDDEN_VALUE')
    return text


def collect():
    from urllib.parse import urlsplit
    from larp.execution import USDT
    from larp.marketdata.port import TOKENS, MarketPort
    from larp.marketdata.web3 import Web3Client
    from larp.runtime.credentials import runtime_secrets
    with open('/etc/larp/runtime.json', 'rb') as f:
        config = json.loads(f.read())
    with open('/etc/larp/strategy-profile.json', 'rb') as f:
        profile = json.loads(f.read())
    providers = list(config['driver'].get('balance_rpc_providers') or [])
    if len(providers) < 1:
        raise ValueError('NO_PROVIDERS')
    wallet = config['wallet_address'].lower()
    secrets = runtime_secrets(config)

    class Memory:
        def put(self, observation):
            return hashlib.sha256(json.dumps(observation, sort_keys=True).encode()).hexdigest()
    port = MarketPort(Web3Client(secrets['BINANCE_API_KEY'], secrets['BINANCE_SECRET_KEY'], artifacts=Memory()),
                      wallet, quote_limits=profile)
    pay = profile['minimum_trade_units']
    quotes, markers = {}, {}
    scope = dict(wallet=wallet, usdt=USDT, tokens={USDT, *TOKENS.values()}, calldata=set())
    for symbol in TOKENS:
        record = port.quote(symbol, 'BUY', pay * 10**12, 18)
        data = record['response']['data']
        q = data[0] if isinstance(data, list) and len(data) == 1 else data
        tx = q['tx']
        if str(tx.get('to', '')).lower() != ROUTER or not str(tx.get('data', '')).startswith(SWAP_SELECTOR):
            markers[symbol] = dict(status='NOT_PINNED_ROUTER')
            continue
        quotes[symbol] = dict(t0=time.monotonic(), data=tx['data'])
        scope['calldata'].add(tx['data'])
        markers[symbol] = dict(route_markers(record), quoted_gas=int(tx['gas']) if tx.get('gas') else None,
                               elapsed_ms=record.get('elapsed_ms'), calldata=fingerprint(tx['data']))
    usdt_units = int(rpc(providers[0]['url'], 'eth_call', [dict(to=USDT, data=BALANCE_OF_CALL + wallet[2:].rjust(64, '0')),
                                                           'latest'], scope), 16)
    scope['usdt_units'] = usdt_units
    packet = dict(schema='LD02cCheck.v1', generated_utc=iso(time.time_ns() // 1000000), signing_enabled=False,
                  claims='Simulations and reads only; observed bounds, not guarantees. Not signed-path evidence.',
                  quote_size_units=pay, route_markers=markers,
                  rfq=rfq_check(providers[0]['url'], scope, quotes),
                  rpc=rpc_check(providers, scope, wallet),
                  provider_fingerprints={p['source_id']: fingerprint(p['url']) for p in providers})
    forbidden = [wallet, wallet[2:], config.get('database_host')]
    for p in providers:
        forbidden += [p['url'], urlsplit(p['url']).hostname]
    forbidden += [v for v in secrets.values() if isinstance(v, str)]
    return packet, forbidden


def main():
    packet, forbidden = collect()
    text = sanitize(json.dumps(packet, sort_keys=True, separators=(',', ':')), forbidden)
    print(text)
    print(json.dumps(dict(packet_sha256=hashlib.sha256(text.encode()).hexdigest())))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps(refusal(error)))
        raise SystemExit(2)
PY

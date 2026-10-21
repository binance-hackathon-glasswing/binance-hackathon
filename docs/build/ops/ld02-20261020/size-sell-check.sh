# LD02d read-only check (IDEA-070 LD02d): SELL-side swap gas and BUY/SELL quote-size sweep.
# Run on primary only, never the signer. Prints one sanitized JSON packet and its SHA-256. No file, service, config,
# ledger or AWS change; no transaction or signature. Quotes and RPC answers stay in memory. State overrides apply
# only to proven balance/allowance slots of the pinned tokens, inside eth_call/eth_estimateGas simulations.
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
ALLOWANCE_CALL, BALANCE_OF_CALL = '0xdd62ed3e', '0x70a08231'
USDT_BALANCE_SLOT, USDT_ALLOWANCE_SLOT = 1, 2  # proven again on chain before use (LD02b)
OZ5_ERC20 = 0x52c63247e1f47db19d5ce0460030c497f067ca4cebf71ba98eeadabe20bace00
CANDIDATES = tuple(range(13)) + (OZ5_ERC20,)
SIZES_USDT = (10, 20, 40, 100)
SENTINEL = 10**30 + 7
PLENTY = 10**36
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
    return dict(error='LD02D_REFUSED', signing_enabled=False,
                reason=type(error).__name__ + (':' + text if text in OWN_CODES else ''))


class RpcRefused(ValueError):
    def __init__(self, error):
        super().__init__('RPC_REFUSED')
        self.error = error

    def reason(self):
        message = str(self.error.get('message', ''))
        found = re.search(r'RFQ_[A-Za-z]+', message)
        return found.group(0) if found else plain(message)[:80]


def word_hex(value):
    return format(value, '064x')


def mapping_slot(key, slot):
    from eth_utils import keccak
    position = word_hex(slot if type(slot) is int else int(slot, 16))
    return '0x' + keccak(bytes.fromhex(str(key)[2:].rjust(64, '0') + position)).hex()


def allowance_slot(wallet, base):
    return mapping_slot(ROUTER, mapping_slot(wallet, base))


def allowed_call(method, params, scope):
    """Reads, slot-proof calls and swap simulations of exact fresh calldata; overrides only on permitted slots."""
    tx = params[0] if params and type(params[0]) is dict else {}
    data = str(tx.get('data', ''))

    def override_ok(value):
        if type(value) is not dict or not value or not set(value) <= scope['tokens']:
            return False
        for token, diff in value.items():
            if type(diff) is not dict or set(diff) != {'stateDiff'} or type(diff['stateDiff']) is not dict:
                return False
            if not diff['stateDiff'] or len(diff['stateDiff']) > 2:
                return False
            if not set(diff['stateDiff']) <= scope['slots'].get(token, set()):
                return False
        return True
    if method in ('eth_chainId', 'eth_getBlockByNumber', 'eth_getStorageAt'):
        return True
    if method == 'eth_call':
        return (data[:10] in (ALLOWANCE_CALL, BALANCE_OF_CALL) and tx.get('to') in scope['tokens']
                and (len(params) == 2 or (len(params) == 3 and override_ok(params[2]))))
    if method == 'eth_estimateGas':
        return (set(tx) <= {'from', 'to', 'data', 'value'} and tx.get('from') == scope['wallet']
                and tx.get('value', '0x0') == '0x0' and tx.get('to') == ROUTER and data in scope['calldata']
                and len(params) == 3 and override_ok(params[2]))
    return False


def rpc(url, method, params, scope):
    from urllib.request import Request, build_opener
    from larp.marketdata.web3 import NoRedirect
    if not url.startswith('https://'):
        raise ValueError('RPC_METHOD_REFUSED')
    if not allowed_call(method, params, scope):
        raise ValueError('RPC_CALL_REFUSED')
    body = json.dumps(dict(jsonrpc='2.0', id=1, method=method, params=params)).encode()
    with build_opener(NoRedirect()).open(Request(url, data=body, headers={'Content-Type': 'application/json'}),
                                         timeout=20) as response:
        reply = json.loads(response.read(2 * 1024 * 1024))
    if type(reply) is dict and type(reply.get('error')) is dict:
        raise RpcRefused(reply['error'])
    if type(reply) is not dict or 'result' not in reply:
        raise ValueError('RPC_REFUSED')
    return reply['result']


def permit_slots(scope, token, base):
    scope['slots'].setdefault(token, set()).update({mapping_slot(scope['wallet'], base)}
                                                    | {allowance_slot(scope['wallet'], b) for b in (base, base + 1)})


def read_call(url, scope, token, data, override=None):
    params = [dict(to=token, data=data), 'latest'] + ([override] if override is not None else [])
    return int(rpc(url, 'eth_call', params, scope), 16)


def prove_slots(url, scope, token):
    """S2: the balance base whose one-slot override makes balanceOf(wallet) return the sentinel, then the allowance
    base (base+1 first, then base) whose override makes allowance(wallet, router) return it."""
    wallet = scope['wallet']
    balance_call = BALANCE_OF_CALL + wallet[2:].rjust(64, '0')
    allowance_call = ALLOWANCE_CALL + wallet[2:].rjust(64, '0') + ROUTER[2:].rjust(64, '0')
    for base in CANDIDATES:
        permit_slots(scope, token, base)
        slot = mapping_slot(wallet, base)
        try:
            seen = read_call(url, scope, token, balance_call, {token: {'stateDiff': {slot: '0x' + word_hex(SENTINEL)}}})
        except RpcRefused:
            continue
        if seen != SENTINEL:
            continue
        for allowance_base in (base + 1, base):
            a_slot = allowance_slot(wallet, allowance_base)
            try:
                a_seen = read_call(url, scope, token, allowance_call,
                                   {token: {'stateDiff': {a_slot: '0x' + word_hex(SENTINEL)}}})
            except RpcRefused:
                continue
            if a_seen == SENTINEL:
                return dict(proven=True, balance_base=hex(base), allowance_base=hex(allowance_base),
                            balance_slot=slot, allowance_slot=a_slot)
        return dict(proven=False, balance_base=hex(base), reason='allowance slot not found')
    return dict(proven=False, reason='balance slot not found')


def simulate(url, scope, data, override):
    try:
        return int(rpc(url, 'eth_estimateGas', [{'from': scope['wallet'], 'to': ROUTER, 'data': data, 'value': '0x0'},
                                                'latest', override], scope), 16)
    except RpcRefused as error:
        return error.reason()
    except Exception as error:
        return type(error).__name__


def single(record):
    data = record['response']['data']
    return data[0] if isinstance(data, list) and len(data) == 1 else data


def quote_row(record):
    q = single(record)
    tx, rr = q.get('tx') or {}, q.get('routerResult') or {}
    pinned = str(tx.get('to', '')).lower() == ROUTER and str(tx.get('data', '')).startswith(SWAP_SELECTOR)
    return dict(pinned=pinned, from_amount=int(rr['fromTokenAmount']), to_amount=int(rr['toTokenAmount']),
                quoted_gas=int(tx['gas']) if tx.get('gas') else None, calldata=tx.get('data') if pinned else None)


def round_trip_bp(pay, back):
    return round((pay - back) * 10000 / pay, 2)


def sweep(url, scope, quote, usdt_override, token_overrides, sizes=SIZES_USDT):
    """S1/S3: per symbol and size, BUY then SELL of the BUY output; each pinned calldata simulated at once."""
    from larp.marketdata.port import TOKENS
    out = {}
    for symbol, token in TOKENS.items():
        rows = {}
        for size in sizes:
            pay = size * 10**18
            row = dict()
            try:
                buy = quote_row(quote(symbol, 'BUY', pay))
            except Exception as error:
                rows[str(size)] = dict(buy_error=plain(type(error).__name__ + ':' + str(error))[:80])
                continue
            scope['calldata'].add(buy['calldata'] or '')
            row['buy'] = dict(out_units=buy['to_amount'], quoted_gas=buy['quoted_gas'], pinned=buy['pinned'],
                              calldata=fingerprint(buy['calldata']),
                              gas=simulate(url, scope, buy['calldata'], usdt_override) if buy['pinned'] else None)
            try:
                sell = quote_row(quote(symbol, 'SELL', buy['to_amount']))
            except Exception as error:
                row['sell_error'] = plain(type(error).__name__ + ':' + str(error))[:80]
                rows[str(size)] = row
                continue
            scope['calldata'].add(sell['calldata'] or '')
            override = token_overrides.get(symbol)
            row['sell'] = dict(in_units=sell['from_amount'], usdt_out_units=sell['to_amount'],
                               quoted_gas=sell['quoted_gas'], pinned=sell['pinned'],
                               calldata=fingerprint(sell['calldata']),
                               gas=(simulate(url, scope, sell['calldata'], override) if sell['pinned'] and override
                                    else 'NOT_PROVEN' if sell['pinned'] else None))
            row['round_trip_bp'] = round_trip_bp(pay, sell['to_amount'])
            rows[str(size)] = row
        gas = lambda side: [r[side]['gas'] for r in rows.values() if side in r and isinstance(r[side]['gas'], int)]
        out[symbol] = dict(sizes=rows, max_buy_gas=max(gas('buy'), default=None),
                           max_sell_gas=max(gas('sell'), default=None))
    return out


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
    url = providers[0]['url']
    wallet = config['wallet_address'].lower()
    secrets = runtime_secrets(config)

    class Memory:
        def put(self, observation):
            return hashlib.sha256(json.dumps(observation, sort_keys=True).encode()).hexdigest()
    port = MarketPort(Web3Client(secrets['BINANCE_API_KEY'], secrets['BINANCE_SECRET_KEY'], artifacts=Memory()),
                      wallet, quote_limits=profile)
    scope = dict(wallet=wallet, usdt=USDT, tokens={USDT, *TOKENS.values()}, calldata=set(), slots={})
    # USDT: the LD02b-proven layout, re-proven here with the same sentinel test.
    usdt_proof = prove_slots(url, scope, USDT)
    usdt_ok = (usdt_proof.get('proven') and int(usdt_proof['balance_base'], 16) == USDT_BALANCE_SLOT
               and int(usdt_proof['allowance_base'], 16) == USDT_ALLOWANCE_SLOT)
    usdt_override = {USDT: {'stateDiff': {usdt_proof['balance_slot']: '0x' + word_hex(PLENTY),
                                          usdt_proof['allowance_slot']: '0x' + word_hex(PLENTY)}}} if usdt_ok else None
    proofs, token_overrides = dict(USDT=usdt_proof), {}
    for symbol, token in TOKENS.items():
        proof = proofs[symbol] = prove_slots(url, scope, token)
        if proof.get('proven'):
            token_overrides[symbol] = {token: {'stateDiff': {proof['balance_slot']: '0x' + word_hex(PLENTY),
                                                             proof['allowance_slot']: '0x' + word_hex(PLENTY)}}}
    sweep_out = (sweep(url, scope, lambda s, side, units: port.quote(s, side, units, 18), usdt_override,
                       token_overrides) if usdt_override else 'NOT_RUN: USDT layout not re-proven')
    packet = dict(schema='LD02dCheck.v1', generated_utc=iso(time.time_ns() // 1000000), signing_enabled=False,
                  claims='Quotes and override simulations only; not fills, not signed-path evidence.',
                  minimum_trade_units=profile.get('minimum_trade_units'), sizes_usdt=list(SIZES_USDT),
                  slot_proofs={k: {kk: vv for kk, vv in v.items() if not kk.endswith('_slot')} for k, v in proofs.items()},
                  sweep=sweep_out, provider_fingerprint=fingerprint(url))
    forbidden = [wallet, wallet[2:], config.get('database_host'), url, urlsplit(url).hostname]
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

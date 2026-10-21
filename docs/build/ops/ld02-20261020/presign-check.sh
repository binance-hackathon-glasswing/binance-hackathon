# KG-DEC-01-H read-only check (IDEA-070): the Web3 API exact-payload gas-limit endpoint refuses payloads that revert.
# Run on primary only, never the signer. Prints one sanitized JSON packet and its SHA-256. No transaction, signature,
# file, service, config, ledger or AWS change. Quotes and answers stay in memory.
set -eu
cd /opt/larp/current
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
import hashlib, json, re, time

ROUTER = '0xb44446b0c8e56988c34f7ff73ae904982b5fdda5'
SWAP_SELECTOR = '0xad43f73d'
SYMBOL = 'MSFTB'
OWN = frozenset(('SANITIZER_URL', 'SANITIZER_FORBIDDEN_VALUE', 'NO_PROVIDERS', 'RPC_REFUSED'))
FORBIDDEN = []  # filled before any provider text is handled; scanned on the full text, before any shortening


def plain(text):
    text = str(text)
    low = text.lower()
    if '://' in text or any(f and len(f) >= 6 and f.lower() in low for f in FORBIDDEN):
        return 'FILTERED'
    return ''.join(c if ' ' <= c <= '~' else '?' for c in text)[:120]


def rpc_call(url, to, data):
    from urllib.request import Request, build_opener
    from larp.marketdata.web3 import NoRedirect
    body = json.dumps(dict(jsonrpc='2.0', id=1, method='eth_call', params=[dict(to=to, data=data), 'latest'])).encode()
    with build_opener(NoRedirect()).open(Request(url, data=body, headers={'Content-Type': 'application/json'}),
                                         timeout=20) as response:
        reply = json.loads(response.read(1 << 20))
    if 'result' not in reply:
        raise ValueError('RPC_REFUSED')
    return int(reply['result'], 16)


def estimate(client, sender, to, data):
    """P2/P3: the exact call LiveVenue.estimate_gas makes; the outcome kind and a short reason only."""
    from larp.marketdata.web3 import Unavailable, single
    try:
        r = client.request('POST', 'pre-transaction/gas-limit',
                           dict(binanceChainId='56', evmTx={'from': sender, 'to': to, 'data': data, 'value': '0'}))
        gas = int(single(r)['gasLimit'])
        return dict(outcome='ESTIMATE' if gas > 0 else 'NON_POSITIVE', gas_limit=gas)
    except Unavailable as error:
        return dict(outcome='REFUSED', reason=plain(error)[:80])
    except (KeyError, TypeError, ValueError) as error:
        return dict(outcome='REFUSED_SCHEMA', reason=type(error).__name__)


def quote_tx(port, side, units):
    from larp.marketdata.web3 import single
    q = single(port.quote(SYMBOL, side, units, 18))
    tx = q['tx']
    pinned = str(tx.get('to', '')).lower() == ROUTER and str(tx.get('data', '')).startswith(SWAP_SELECTOR)
    return tx['data'] if pinned else None


def collect():
    from urllib.parse import urlsplit
    from larp.execution import USDT
    from larp.marketdata.port import TOKENS, MarketPort
    from larp.marketdata.web3 import Web3Client, single
    from larp.runtime.credentials import runtime_secrets
    config = json.loads(open('/etc/larp/runtime.json', 'rb').read())
    profile = json.loads(open('/etc/larp/strategy-profile.json', 'rb').read())
    providers = list(config['driver'].get('balance_rpc_providers') or [])
    if not providers:
        raise ValueError('NO_PROVIDERS')
    url, wallet = providers[0]['url'], config['wallet_address'].lower()
    secrets = runtime_secrets(config)
    FORBIDDEN[:] = [wallet, wallet[2:], url, urlsplit(url).hostname, config.get('database_host')] + [
        v for v in secrets.values() if isinstance(v, str)]

    class Memory:
        def put(self, observation):
            return hashlib.sha256(json.dumps(observation, sort_keys=True).encode()).hexdigest()
    client = Web3Client(secrets['BINANCE_API_KEY'], secrets['BINANCE_SECRET_KEY'], artifacts=Memory())
    port = MarketPort(client, wallet, quote_limits=profile)
    word = wallet[2:].rjust(64, '0')
    token = TOKENS[SYMBOL]
    pre = dict(bstock_balance=rpc_call(url, token, '0x70a08231' + word),
               usdt_allowance_to_router=rpc_call(url, USDT, '0xdd62ed3e' + word + ROUTER[2:].rjust(64, '0')))
    packet = dict(schema='PresignCheck.v1', generated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  signing_enabled=False, symbol=SYMBOL, preconditions=pre,
                  claims='Exact-payload gas-limit answers only; no transaction or signature.')
    if any(pre.values()):
        packet['status'] = 'NOT_RUN'
        return packet, [wallet, wallet[2:], url, urlsplit(url).hostname]
    approve = single(client.request('GET', 'aggregator/approve-transaction', dict(
        binanceChainId='56', tokenContractAddress=USDT, approveAmount=str(20 * 10**18), vendor='LiquidMesh')))
    approve_ok = str(approve.get('dexContractAddress', '')).lower() == ROUTER
    packet['control_approve'] = dict(spender_pinned=approve_ok, **(estimate(client, wallet, USDT, approve['data'])
                                                                    if approve_ok else {}))
    for name, side, units in (('sell_without_balance', 'SELL', 10**18), ('buy_without_allowance', 'BUY', 20 * 10**18)):
        data = quote_tx(port, side, units)
        packet[name] = dict(pinned=data is not None, **(estimate(client, wallet, ROUTER, data) if data else {}))
    refused = lambda r: r.get('outcome') in ('REFUSED', 'REFUSED_SCHEMA', 'NON_POSITIVE')
    packet['status'] = ('PASS' if packet['control_approve'].get('outcome') == 'ESTIMATE'
                        and all(refused(packet[k]) for k in ('sell_without_balance', 'buy_without_allowance'))
                        else 'FAIL')
    return packet, list(FORBIDDEN)


def main():
    packet, forbidden = collect()
    text = json.dumps(packet, sort_keys=True, separators=(',', ':'))
    if '://' in text or any(f and len(f) >= 6 and f.lower() in text.lower() for f in forbidden):
        raise ValueError('SANITIZER_FORBIDDEN_VALUE')
    print(text)
    print(json.dumps(dict(packet_sha256=hashlib.sha256(text.encode()).hexdigest())))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps(dict(error='PRESIGN_REFUSED', signing_enabled=False,
                              reason=type(error).__name__ + (':' + str(error) if str(error) in OWN else ''))))
        raise SystemExit(2)
PY

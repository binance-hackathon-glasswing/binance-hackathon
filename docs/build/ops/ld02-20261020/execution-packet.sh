# LD02 read-only execution packet (IDEA-070 LD02): run on primary only, never the signer.
# Prints one sanitized JSON packet and its SHA-256. No file, service, config, ledger or AWS change:
# Web3 and RPC artifacts stay in memory and SQL runs READ ONLY.
set -eu
cd /opt/larp/current
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
import base64
from datetime import datetime, timezone
import hashlib
import json
import re
import statistics
import time
import zlib

# Canonical larp/execution_live/untrusted_router.py at codex/system-testing-20261012 697ff3a. The host release
# predates it, so its exact bytes travel here and are loaded in memory after the hash check.
ROUTER_MODULE_SHA256 = '9934f5372f406ad9b9b62e85da93421128d68fdf2722af234f358d6140b0923a'
ROUTER_MODULE_Z = (
    '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'
    '7kw='
)
CLAIMS = ('LD02 operator packet. Not native-trace, signed-path or #92 evidence; the router draft stays '
          'REVIEW_REQUIRED and nothing is enabled.')
CONFIGS = {'runtime': '/etc/larp/runtime.json', 'release_manifest': '/etc/larp/release.json',
           'strategy_profile': '/etc/larp/strategy-profile.json'}
ALLOWANCE_CALL = '0xdd62ed3e'
RPC_METHODS = frozenset(('eth_chainId', 'eth_getBlockByNumber', 'eth_gasPrice', 'eth_call'))
SIGNER_TIMINGS = ('queue_ms', 'sign_ms', 'broadcast_ms', 'receipt_ms', 'finality_ms')


def fingerprint(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def epoch_s(stamp):
    return datetime.fromisoformat(stamp.replace('Z', '+00:00')).timestamp()


def code(error):
    """An error's type, plus its text only when it is a short code or fixed phrase (no URL, path or value)."""
    text = str(error)
    return type(error).__name__ + (':' + text if re.fullmatch(r'[A-Za-z0-9_ ,.-]{3,100}', text) else '')


def load_router_module():
    import types
    raw = zlib.decompress(base64.b64decode(''.join(ROUTER_MODULE_Z)))
    if hashlib.sha256(raw).hexdigest() != ROUTER_MODULE_SHA256:
        raise ValueError('ROUTER_MODULE_HASH')
    module = types.ModuleType('ld02_untrusted_router')
    exec(compile(raw, 'untrusted_router.py@697ff3a', 'exec'), module.__dict__)
    return module


class MemoryArtifacts:
    """`Artifacts.put` without a disk write: the packet keeps hashes, never the stored bytes."""

    def __init__(self):
        self.records = []

    def put(self, observation):
        raw = json.dumps(observation, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        self.records.append(observation)
        return hashlib.sha256(raw).hexdigest()


class TimedOpener:
    """Wraps the production opener and logs (source, method, ms to response headers)."""

    def __init__(self, inner, log, source_id):
        self.inner, self.log, self.source_id = inner, log, source_id

    def open(self, request, timeout=None):
        method = json.loads(request.data).get('method')
        start = time.monotonic()
        try:
            return self.inner.open(request, timeout=timeout)
        finally:
            self.log.append((self.source_id, method, round((time.monotonic() - start) * 1000)))


def rpc(url, source_id, method, params, log):
    """One read-only JSON-RPC call outside the production client (allowance, gas price, finality)."""
    from urllib.request import Request, urlopen
    if method not in RPC_METHODS or not url.startswith('https://'):
        raise ValueError('RPC_METHOD_REFUSED')
    if method == 'eth_call' and str(params[0].get('data', ''))[:10] != ALLOWANCE_CALL:
        raise ValueError('RPC_CALL_REFUSED')
    body = json.dumps(dict(jsonrpc='2.0', id=1, method=method, params=params)).encode()
    start = time.monotonic()
    with urlopen(Request(url, data=body, headers={'Content-Type': 'application/json'}), timeout=20) as response:
        reply = json.loads(response.read(2 * 1024 * 1024))
    log.append((source_id, method, round((time.monotonic() - start) * 1000)))
    if type(reply) is not dict or 'error' in reply or 'result' not in reply:
        raise ValueError('RPC_REFUSED')
    return reply['result']


def timing_summary(log):
    groups = {}
    for source, method, ms in log:
        groups.setdefault(f'{source}:{method}', []).append(ms)
    return {k: dict(n=len(v), min=min(v), median=statistics.median(v), max=max(v)) for k, v in sorted(groups.items())}


def word(body, index):
    return int.from_bytes(body[32 * index:32 * index + 32], 'big')


def inner_deadline(data, m):
    """The route's inner deadline, read with the canonical layout constants (IDEA-070 B02-U)."""
    if type(data) is not str or not data.startswith(m.SWAP_SELECTOR):
        raise ValueError('CALLDATA_SELECTOR')
    body = bytes.fromhex(data[10:])
    if len(body) < 32 * m.HEAD_WORDS:
        raise ValueError('CALLDATA_LAYOUT')
    start, length = 32 * m.HEAD_WORDS, word(body, m.BLOB_LENGTH)
    inner = body[start:start + length]
    if length < 4 + 32 * m.INNER_WORDS or '0x' + inner[:4].hex() != m.INNER_SELECTOR:
        raise ValueError('CALLDATA_LAYOUT')
    return word(inner[4:], m.INNER_DEADLINE)


def quote_row(symbol, side, pay_units, amount, decimals, record, m, tokens, usdt):
    """A request-bound summary of one quote: binding booleans, timings and the route deadline, no calldata."""
    data = record['response']['data']
    q = data[0] if isinstance(data, list) and len(data) == 1 else data
    rr, tx = q.get('routerResult') or {}, q.get('tx') or {}
    pay, receive = (usdt, tokens[symbol]) if side == 'BUY' else (tokens[symbol], usdt)
    pay_decimals, receive_decimals = (18, decimals) if side == 'BUY' else (decimals, 18)
    bound = (str(rr.get('fromToken', {}).get('tokenContractAddress', '')).lower() == pay
             and str(rr.get('toToken', {}).get('tokenContractAddress', '')).lower() == receive
             and int(rr['fromToken']['decimal']) == pay_decimals and int(rr['toToken']['decimal']) == receive_decimals
             and int(rr['fromTokenAmount']) == amount)
    received, minimum = int(rr['toTokenAmount']), int(tx['minReceiveAmount'])
    row = dict(symbol=symbol, side=side, pay_units=pay_units, status='OK', request_bound=bound,
               router_pinned=str(tx.get('to', '')).lower() == m.ROUTER, native_value_zero=int(tx.get('value', 0)) == 0,
               selector_pinned=str(tx.get('data', ''))[:10] == m.SWAP_SELECTOR, vendor=rr.get('vendorName'),
               elapsed_ms=record.get('elapsed_ms'), quoted_gas=int(tx['gas']) if tx.get('gas') else None,
               receive_units=received, minimum_receive=minimum,
               minimum_below_quote_bps=(received - minimum) * 10000 // received if received else None,
               impact_percent=rr.get('priceImpactPercent'),
               calldata=fingerprint(tx.get('data')), artifact=record['artifact_sha256'][:16])
    try:
        row['deadline_after_request_s'] = round(inner_deadline(tx['data'], m) - epoch_s(record['requested_at']), 1)
    except (ValueError, KeyError, TypeError) as error:
        row['deadline_after_request_s'], row['deadline_error'] = None, code(error)
    return row


def memory_quotes(records):
    """`untrusted_router._quotes` over this run's in-memory quote records (same fields it reads from files)."""
    for value in records:
        if value.get('endpoint') != 'aggregator/quote-and-swap' or value.get('outcome') != 'ok':
            continue
        data = value['response']['data']
        data = data[0] if isinstance(data, list) and len(data) == 1 else data
        tx = data.get('tx') if isinstance(data, dict) else None
        if type(tx) is dict and str(tx.get('data', '')).startswith('0x'):
            raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
            yield hashlib.sha256(raw).hexdigest(), value['params'], tx


def finality(providers, log):
    rows = []
    for p in providers:
        try:
            latest = rpc(p['url'], p['source_id'], 'eth_getBlockByNumber', ['latest', False], log)
            final = rpc(p['url'], p['source_id'], 'eth_getBlockByNumber', ['finalized', False], log)
            rows.append(dict(source_id=p['source_id'], latest=int(latest['number'], 16), finalized=int(final['number'], 16),
                             lag_blocks=int(latest['number'], 16) - int(final['number'], 16),
                             lag_seconds=int(latest['timestamp'], 16) - int(final['timestamp'], 16)))
        except Exception as error:
            rows.append(dict(source_id=p['source_id'], status='REFUSED', error=code(error)))
    return rows


def sanitize(text, forbidden):
    """Refuse the packet if it carries a URL, a secret, the wallet or a database endpoint."""
    if '://' in text:
        raise ValueError('SANITIZER_URL')
    low = text.lower()
    for value in forbidden:
        if value and len(value) >= 6 and value.lower() in low:
            raise ValueError('SANITIZER_FORBIDDEN_VALUE')
    return text


def forbidden_values(config, secrets, providers):
    from urllib.parse import urlsplit
    wallet = str(config.get('wallet_address', '')).lower()
    values = [wallet, wallet[2:], config.get('database_host')]
    for p in providers:
        values += [p.get('url'), urlsplit(p.get('url', '')).hostname]
    return values + [v for v in secrets.values() if isinstance(v, str)]


def read_configs():
    raw = {}
    for name, path in CONFIGS.items():
        with open(path, 'rb') as stream:
            raw[name] = stream.read()
    return raw


def database(config):
    from contextlib import contextmanager
    from larp.runtime.database import IamPostgresStore, rds_client

    class RO(IamPostgresStore):
        @contextmanager
        def transaction(self):
            with super().transaction() as db:
                db.execute('SET TRANSACTION READ ONLY'); yield db

    with RO(config, rds_client(config['region'])).transaction() as db:
        run = db.execute('SELECT wallet_id,version,epoch,quarantined,projection FROM runs WHERE run_id=%s',
                         (config['run_id'],)).fetchone()
        reservations = db.execute('SELECT asset,count(*),sum(units) FROM reservations WHERE run_id=%s GROUP BY asset',
                                  (config['run_id'],)).fetchall()
        commands = db.execute('SELECT status,count(*) FROM commands WHERE run_id=%s GROUP BY status',
                              (config['run_id'],)).fetchall()
        rounds = db.execute('SELECT status,count(*) FROM rounds WHERE run_id=%s GROUP BY status',
                            (config['run_id'],)).fetchall()
    return run, reservations, commands, rounds


def collect():
    from larp.contracts import Document
    from larp.execution import USDT
    from larp.execution_live.balances import BalanceProviders, DecimalsCache
    from larp.execution_live.chain import Rpc
    from larp.marketdata.port import TOKENS, MarketPort
    from larp.marketdata.web3 import NoRedirect, Web3Client
    from larp.risk.reconcile import compare_balances
    from larp.runtime.credentials import runtime_secrets
    from urllib.request import build_opener
    import socket

    module = load_router_module()
    before = read_configs()
    config, profile = json.loads(before['runtime']), json.loads(before['strategy_profile'])
    driver = config['driver']
    providers = list(driver.get('balance_rpc_providers') or [])
    if not providers:
        raise ValueError('NO_BALANCE_PROVIDERS')
    wallet = config['wallet_address'].lower()
    secrets = runtime_secrets(config)
    log, quote_log = [], []
    packet = dict(schema='LD02ExecutionPacket.v1', generated_utc=iso(time.time_ns() // 1000000), claims=CLAIMS,
                  signing_enabled=False, router_module_sha256=ROUTER_MODULE_SHA256)

    run, reservations, commands, rounds = database(config)
    projection = Document(bytes(run[4])).read()
    portfolio, registered = projection.get('portfolio') or {}, projection.get('registered_version') or {}
    hashes = {k: hashlib.sha256(v).hexdigest() for k, v in before.items()}
    packet['identity'] = dict(
        host=socket.gethostname(), run_id=config['run_id'], build_id=config.get('build_id'), mode=config.get('mode'),
        execution=driver.get('execution'), database_name=config.get('database_name'),
        config_sha256=hashes, wallet_fingerprint=fingerprint(wallet),
        wallet_consistent=wallet == str(run[0]).lower() == str(portfolio.get('wallet_id', '')).lower(),
        registered_build_matches=registered.get('build_id') == config.get('build_id'),
        registered_manifest_matches=registered.get('manifest_sha256') == hashes['release_manifest'],
        run=dict(version=run[1], epoch=run[2], quarantined=run[3]))
    packet['in_flight'] = dict(
        reservations={a: dict(count=n, units=int(u)) for a, n, u in reservations},
        commands=dict(commands), rounds=dict(rounds),
        execution_pending=sorted(r for r, rec in (projection.get('round_records') or {}).items()
                                 if rec.get('execution_pending')),
        settled_block=projection.get('settled_block'))
    packet['finality_start'] = finality(providers, log)

    # Holdings: the production ordered-provider reader and reconciliation against the current ledger.
    reader = BalanceProviders(
        [Rpc(p['url'], artifacts=MemoryArtifacts(), source_id=p['source_id'],
             opener=TimedOpener(build_opener(NoRedirect()), log, p['source_id'])) for p in providers],
        wallet=wallet, decimals=DecimalsCache(), min_block=lambda: projection.get('settled_block'))
    observed_ms = time.time_ns() // 1000000
    observation = reader(observed_ms)
    plain = {k: v for k, v in observation.items() if k != 'source_id'}
    check = compare_balances(portfolio, plain, settled_block=projection.get('settled_block'))
    packet['holdings'] = dict(
        observed_utc=iso(observed_ms), served_by=observation['source_id'], block=observation['block_number'],
        block_hash=observation['block_hash'], observation_sha256=Document.from_dict(observation).digest('ChainBalances.v1'),
        status=check['status'], assets={a: dict(cls=r['class'], ledger=r['ledger_units'], chain=r['chain_units'])
                                        for a, r in check['assets'].items()},
        native_wei=observation['native_wei'], latest_nonce=observation['latest_nonce'],
        pending_nonce=observation['pending_nonce'], note='fresh read in this run, not a #92 citation')

    # Request-bound quotes at the profile's planned sizes, with its slippage, through the runtime's own port.
    web3 = MemoryArtifacts()
    port = MarketPort(Web3Client(secrets['BINANCE_API_KEY'], secrets['BINANCE_SECRET_KEY'], artifacts=web3), wallet,
                      quote_limits=profile)
    minimum, cap = profile.get('minimum_trade_units'), profile.get('per_trade_cap_units')
    quotes = []
    for symbol in TOKENS:
        decimals = observation['tokens'][symbol]['decimals']
        sell_units = None
        for side, units in (('BUY', minimum), ('BUY', cap), ('SELL', None)):
            if side == 'SELL':
                units = sell_units
            if type(units) is not int or units <= 0:
                quotes.append(dict(symbol=symbol, side=side, status='NOT_REQUESTED', reason='SIZE_UNAVAILABLE'))
                continue
            amount = units * 10**12 if side == 'BUY' else units
            try:
                record = port.quote(symbol, side, amount, decimals)
                row = quote_row(symbol, side, units, amount, decimals, record, module, TOKENS, USDT)
                if side == 'BUY' and units == minimum:
                    sell_units = row['receive_units']
            except Exception as error:
                row = dict(symbol=symbol, side=side, pay_units=units, status='REFUSED', error=code(error))
            quotes.append(row)
    packet['quotes'] = dict(sizes=dict(minimum_trade_units=minimum, per_trade_cap_units=cap,
                                       slippage_bps=profile.get('slippage_bps')), rows=quotes)

    # Router/facet/code draft from live state and this run's quotes; it stays REVIEW_REQUIRED.
    module._quotes = lambda _directory: memory_quotes(web3.records)
    try:
        draft, block, count = module.observe(providers[0]['url'], None)
        text = json.dumps(draft, indent=2, sort_keys=True) + '\n'
        allowances = {}
        owner, spender = wallet[2:].rjust(64, '0'), module.ROUTER[2:].rjust(64, '0')
        for name, token in (('USDT', USDT), *TOKENS.items()):
            value = rpc(providers[0]['url'], providers[0]['source_id'], 'eth_call',
                        [dict(to=token, data=ALLOWANCE_CALL + owner + spender), block], log)
            allowances[name] = int(value, 16)
        packet['router'] = dict(status='DRAFT_REVIEW_REQUIRED', block=int(block, 16), quotes_used=count,
                                draft_sha256=hashlib.sha256(text.encode()).hexdigest(), draft=draft,
                                allowances_to_router=allowances, served_by=providers[0]['source_id'])
    except Exception as error:
        packet['router'] = dict(status='REFUSED', error=code(error))

    # Funding input for Isaac (LD07: initial gas only). Not a decision: LD09's measured gas is still missing.
    gas_price = int(rpc(providers[0]['url'], providers[0]['source_id'], 'eth_gasPrice', [], log), 16)
    swap_gas = [r['quoted_gas'] for r in quotes if r.get('status') == 'OK' and r.get('quoted_gas')]
    median_gas = int(statistics.median(swap_gas)) if swap_gas else None
    bnb_value = observation['native_wei'] * portfolio['bnb_price_units'] // 10**18 if portfolio.get('bnb_price_units') else None
    reserve = profile.get('exit_gas_reserve_units')
    packet['funding_input'] = dict(
        native_wei=observation['native_wei'], bnb_value_units=bnb_value, gas_price_wei=gas_price,
        median_quoted_swap_gas=median_gas,
        indicative_swaps_affordable=observation['native_wei'] // (median_gas * gas_price) if median_gas and gas_price else None,
        exit_gas_reserve_wei=reserve,  # the planner compares it with ledger bnb_units (wei), not USDT value
        versus_exit_reserve=None if type(reserve) is not int else
        ('BELOW_EXIT_RESERVE' if observation['native_wei'] < reserve else 'AT_OR_ABOVE_EXIT_RESERVE'),
        reserve_multiple=round(observation['native_wei'] / reserve, 2) if type(reserve) is int and reserve > 0 else None,
        approve_gas='UNMEASURED', ld09_measured_gas='UNMEASURED',
        note='Input for Isaac against LD07 (initial gas only); seeding needs LD09 measured gas x planned trades x margin.')

    configured = []
    for path in sorted(__import__('glob').glob('/etc/larp/*.json')):
        try:
            with open(path, 'rb') as stream:
                doc = json.loads(stream.read())
        except ValueError:
            continue
        for key in ('execution_rpc_url', 'rpc_url', 'execution_rpc_providers', 'rpc_providers'):
            if isinstance(doc, dict) and key in doc:
                configured.append(dict(file=path.rsplit('/', 1)[-1], key=key))
    packet['execution_rpc'] = dict(
        configured_on_primary=configured,
        candidates=[dict(source_id=p['source_id'], url_fingerprint=fingerprint(p['url']),
                         approved_for='development balance reads') for p in providers],
        status='AWAITING_KEEGAN_CONFIRMATION')
    packet['signer_timings'] = dict(status='UNMEASURED', fields=list(SIGNER_TIMINGS),
                                    reason='no signer installed; the signer host was not queried')
    packet['finality_end'] = finality(providers, log)
    packet['timings'] = dict(rpc_ms=timing_summary(log), quote_ms=timing_summary(
        [('BINANCE_WEB3', 'quote-and-swap', r['elapsed_ms']) for r in quotes if r.get('elapsed_ms') is not None]))
    after = read_configs()
    packet['configs_unchanged'] = after == before
    return packet, forbidden_values(config, secrets, providers)


def main():
    packet, forbidden = collect()
    text = sanitize(json.dumps(packet, sort_keys=True, separators=(',', ':')), forbidden)
    print(text)
    print(json.dumps(dict(packet_sha256=hashlib.sha256(text.encode()).hexdigest())))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Neither config content nor provider/database text is emitted; only this script's own codes.
        print(json.dumps(dict(error='LD02_PACKET_REFUSED', reason=code(error), signing_enabled=False)))
        raise SystemExit(2)
PY

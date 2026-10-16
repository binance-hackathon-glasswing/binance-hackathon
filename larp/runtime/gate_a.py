"""Gate A input capture and assembly. No signer, broadcaster, uploader or activation call.

Capture public metadata and wallet balances with the existing credential-screened
Web3 transport. Preparation consumes those exact bytes and a separately reviewed
LIVE rehearsal profile. It never invents quote costs or attests hosted readiness.
"""
import hashlib
import json
from pathlib import Path
import re

from larp.contracts import ContractError, Document
from larp.execution import USDT
from larp.integration import contract
from larp.intelligence.config import load_config, load_registry
from larp.marketdata.port import MarketPort, NATIVE, TOKENS, integer
from larp.marketdata.web3 import data, encoded, utc
from larp.runtime.driver import SessionCalendar
from larp.strategy.profiles import validate_live
from larp.strategy.schema import instant

ROOT = Path(__file__).resolve().parents[2]
CADENCE_MS = 900_000
DAY_ROLL_MS = 300_000
HOST_CHECKS = ('REAL_RECEIVER_ACK', '24H_INGESTION', 'HOST_RESTART', 'HOURLY_ANCHOR',
               'IAM_TLS_ROLES', 'NETWORK_ROUTES', 'TIME_SYNC', 'ALARM_RECEIVED')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def wallet_address(value):
    if type(value) is not str or not re.fullmatch(r'0x[0-9a-fA-F]{40}', value):
        raise ContractError('A public wallet address is required')
    return value.lower()


def check_balance_rpc(url, source_id):
    """GA13c: both an HTTPS URL and a source ID, or neither. An empty shell variable arrives as '' and refuses."""
    if (url is None) != (source_id is None) or url is not None and (
            type(url) is not str or not url.startswith('https://') or type(source_id) is not str or not source_id):
        raise ContractError('The balance RPC needs both an HTTPS URL and a source ID, or neither')


def capture_inputs(client, wallet, rpc=None):
    """Exactly two read-only endpoints, never quote-and-swap, signing or audit delivery.

    With `rpc` (the manifested balance RPC, `chain.Rpc`), also the finalized chain balances and nonces (GA11)."""
    wallet = wallet_address(wallet)
    port = MarketPort(client, wallet)
    metadata = port.metadata()
    meta = metadata[next(iter(TOKENS))][1]
    balances = port.balances()
    value = dict(schema='GateAInputs.v1', wallet=wallet, observed_at=utc(),
                 metadata=meta, balances=balances)
    if rpc is not None:
        value['chain'] = chain_capture(rpc, wallet, observed_at=utc())
    # Validate before persisting a purported usable capture.
    issuer_map(value)
    raw_balances(value)
    if rpc is not None:
        check_chain(value)
    return value


def chain_capture(rpc, wallet, *, observed_at):
    """IDEA-055's `read_balances` at the finalized block, plus the wallet nonce at that same block (GA11)."""
    from larp.execution_live.balances import read_balances
    from larp.execution_live.chain import quantity
    value = read_balances(rpc, wallet=wallet_address(wallet), observed_at=observed_at)
    value['finalized_nonce'] = quantity(rpc.call('eth_getTransactionCount',
                                                 [value['wallet'], hex(value['block_number'])]))
    value['source_id'] = rpc.source_id
    return value


def check_chain(capture, now=None):
    """GA11: refuse while a wallet transaction is pending or not yet finalized, or when chain and kit disagree.

    The kit's balances have no block identity. Equal finalized, latest and pending nonces mean nothing the wallet sent
    can still change them; the finalized balances must then equal the kit's, asset by asset."""
    chain = capture['chain']
    if (type(chain) is not dict or chain.get('schema') != 'ChainBalances.v1' or chain.get('chain_id') != 56
            or chain.get('wallet') != wallet_address(capture['wallet'])):
        raise ContractError('The chain balance capture belongs to another wallet or chain')
    if now is not None:
        age = (instant(now) - instant(chain['observed_at'])).total_seconds()
        if not 0 <= age <= 300:
            raise ContractError('The chain balance capture is future-dated or stale')
    nonces = [chain.get(k) for k in ('finalized_nonce', 'latest_nonce', 'pending_nonce')]
    if any(type(n) is not int for n in nonces) or len(set(nonces)) != 1:
        raise ContractError('A wallet transaction is in flight (finalized, latest and pending nonces differ); '
                            'capture again once it is finalized')
    kit = raw_balances(capture)
    observed = {NATIVE: chain['native_wei'], **{row['contract']: row['units'] for row in chain['tokens'].values()}}
    if set(observed) != set(kit) or any(observed[token] != kit[token] for token in kit):
        raise ContractError('Finalized chain balances differ from the kit balances; capture again')


def observation(capture, name, endpoint, method):
    r = capture[name]
    if (r.get('schema') != 'Web3Observation.v1' or r.get('source_id') != 'BINANCE_WEB3'
            or r.get('endpoint') != endpoint or r.get('method') != method or r.get('outcome') != 'ok'
            or r.get('response', {}).get('code') != 0 or not re.fullmatch('[0-9a-f]{64}', r.get('artifact_sha256', ''))):
        raise ContractError('Successful, attributed Web3 observation required')
    instant(r['available_at'])
    if digest(encoded({k: v for k, v in r.items() if k != 'artifact_sha256'})) != r['artifact_sha256']:
        raise ContractError('Web3 capture bytes differ from their artifact hash')
    return data(r)


def issuer_map(capture):
    """Bind observed tickers to SEC issuers; do not assert a share class or conversion ratio."""
    rows = observation(capture, 'metadata', 'market/rwa/tokens', 'GET')
    if type(rows) is not list:
        raise ContractError('Metadata must contain token rows')
    result = {}
    for entry in load_registry().entries:
        found = [r for r in rows if r.get('tokenContractAddress', '').lower() == TOKENS[entry.token]]
        if len(found) != 1:
            raise ContractError('Every eligible contract must appear exactly once')
        row = found[0]
        ticker = row.get('underlyingTicker')
        tickers = {s.security_id.split(':', 1)[1] for s in entry.securities}
        if (row.get('tokenSymbol') != entry.token or str(row.get('binanceChainId')) != '56'
                or ticker not in tickers or integer(row['decimals']) > 30):
            raise ContractError('Metadata identity, ticker or decimals differ from registry')
        # The evidence contract's own rule decides whether real filings for this token are accepted (GA-P1, #25).
        if not contract.issuer_matches(dict(issuer_id=entry.issuer_id, token=entry.token, underlying_id=ticker),
                                       ticker, source_id='BINANCE_WEB3'):
            raise ContractError(f'{entry.token}: the evidence contract refuses issuer {entry.issuer_id} '
                                f'with ticker {ticker!r}')
        result[entry.issuer_id] = dict(token=entry.token, underlying_id=ticker)
    return result


def raw_balances(capture):
    rows = observation(capture, 'balances', 'balance/token-balances-by-address', 'POST')
    # Kit: omitted assets have zero balance; no account row is also a zero response.
    if type(rows) is not list or len(rows) > 1:
        raise ContractError('Expected one wallet balance result')
    assets = [] if not rows else rows[0]['tokenAssets']
    if type(assets) is not list:
        raise ContractError('Balance assets must be a list')
    known = {USDT, NATIVE, *TOKENS.values()}
    result = dict.fromkeys(known, 0)
    seen = set()
    for asset in assets:
        token = asset['tokenContractAddress'].lower()
        if token not in known or token in seen or str(asset.get('binanceChainId', '56')) != '56':
            raise ContractError('Unexpected or duplicate balance asset')
        seen.add(token)
        result[token] = integer(asset['rawBalance'])
    params = capture['balances'].get('params', {})
    requested = params.get('address')
    wallet = wallet_address(capture['wallet'])
    if requested not in (wallet, 'sha256:' + digest(wallet.encode())):
        raise ContractError('Balance capture belongs to another wallet')
    wanted = {(str(r['binanceChainId']), r['tokenContractAddress'].lower())
              for r in params.get('tokenContractAddresses', [])}
    if wanted != {('56', t) for t in ('', USDT, *TOKENS.values())}:
        raise ContractError('Balance request must cover all eligible assets and native BNB')
    return result


def initial_state(capture, profile, run_id):
    """Only a fresh, stock-flat dev wallet can be initialized without cost-basis history.

    USDT is floored from chain 18 decimals into ledger micro-USDT. Exact raw
    balances and the discarded sub-micro remainder stay in the pinned capture.
    Native BNB stays in wei. Existing holdings need reviewed accounting history.
    """
    balances = raw_balances(capture)
    if any(balances[token] for token in TOKENS.values()):
        raise ContractError('Existing stock holdings require reviewed cost-basis history')
    costs = profile['quote_cost_summary']
    if costs['bnb_decimals'] != 18:
        raise ContractError('Native BNB must be accounted in wei')
    cash, bnb = balances[USDT] // 10**12, balances[NATIVE]
    opening = cash + bnb * costs['bnb_price_units'] // 10**18
    if type(run_id) is not str or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,99}', run_id) or opening <= 0:
        raise ContractError('A funded run identity is required')
    rows = observation(capture, 'metadata', 'market/rwa/tokens', 'GET')
    decimals = {s: integer(next(r['decimals'] for r in rows
                               if r.get('tokenContractAddress', '').lower() == token))
                for s, token in TOKENS.items()}
    day = instant(capture['observed_at']).date().isoformat()
    state = dict(schema='PortfolioState.v1', mode='dev', run_id=run_id, wallet_id=wallet_address(capture['wallet']),
                cash_units=cash, bnb_units=bnb, bnb_decimals=18, bnb_price_units=costs['bnb_price_units'],
                opening_equity_units=opening,
                positions={s: dict(units=0, decimals=decimals[s], cost_basis_units=0) for s in sorted(TOKENS)},
                reservations={}, applied_events={},
                accounting=dict(realized_units=0, fees_units=0, gas_value_units=0, service_units=0, turnover_units=0),
                risk=dict(day=day, day_anchor_units=opening, peak_units=opening,
                          daily_halt=False, run_halt=False, deep_cut=False))
    check_initial_state(state, capture)
    return state


def check_initial_state(state, capture):
    """GA-P2: the runtime can build its ledger from the state, and it has gate_b DR-06's shape (ported from PR #89)."""
    from larp.integration.runtime import initial_projection, ledger_from
    units = [state.get('cash_units'), state.get('bnb_units'),
             *[p.get('units') for p in (state.get('positions') or {}).values()]]
    if (state.get('schema') != 'PortfolioState.v1' or state.get('wallet_id') != wallet_address(capture['wallet'])
            or state.get('bnb_decimals') != 18 or state.get('mode') != 'dev'
            or any(type(u) is not int or u < 0 for u in units)):
        raise ContractError('Initial state lacks the DR-06 shape (identity, wei, dev mode, non-negative units)')
    try:
        ledger_from(initial_projection(state), [])
    except (ValueError, KeyError, TypeError) as error:
        raise ContractError('The runtime cannot build its ledger from the initial state: ' + str(error)) from None


def prepare(configs, *, profile_raw, capture_raw, calendar_raw, run_id, build_id, now, sec_contact=None,
            balance_rpc_url=None, balance_rpc_source_id=None):
    """Return filenames -> exact bytes. The caller writes them only to ignored deployment storage."""
    profile, capture = json.loads(profile_raw), json.loads(capture_raw)
    if profile.get('schema') != 'StrategyProfile.v1' or profile.get('mode') != 'LIVE':
        raise ContractError('A separately reviewed LIVE profile is required')
    validate_live(profile)
    if profile.get('environment') != 'REHEARSAL':
        raise ContractError('Gate A requires a dev rehearsal profile')
    if capture.get('schema') != 'GateAInputs.v1' or not re.fullmatch('[0-9a-f]{40}', build_id or ''):
        raise ContractError('Captured inputs and full pushed build SHA required')
    age = (instant(now) - instant(capture['observed_at'])).total_seconds()
    if not 0 <= age <= 300:
        raise ContractError('Starting balance capture is future-dated or older than five minutes')
    for name in ('metadata', 'balances'):
        age = (instant(now) - instant(capture[name]['available_at'])).total_seconds()
        if not 0 <= age <= 300:
            raise ContractError('Underlying capture is future-dated or stale')
    calendar = SessionCalendar(json.loads(calendar_raw))
    calendar(int(instant(now).timestamp() * 1000))
    calendar(int(instant(profile['signing_end']).timestamp() * 1000))
    issuers = issuer_map(capture)
    check_balance_rpc(balance_rpc_url, balance_rpc_source_id)
    if balance_rpc_url is not None and 'chain' not in capture:
        # GA12: with the balance RPC configured, nothing excuses a capture without the chain read.
        raise ContractError('A chain balance capture required: capture with --balance-rpc-url')
    if 'chain' in capture:
        check_chain(capture, now)
        if balance_rpc_url is not None and capture['chain'].get('source_id') != balance_rpc_source_id:
            raise ContractError('The chain balance capture came from another RPC source')
    state = initial_state(capture, profile, run_id)
    state_raw = encoded(state) + b'\n'
    configs = json.loads(json.dumps(configs))
    runtime, uploader, operations = (configs[n] for n in ('runtime.json', 'uploader.json', 'operations.json'))
    wallet = state['wallet_id']
    if any(c.get('wallet_address') != wallet for c in (runtime, uploader)):
        raise ContractError('Infrastructure and captured wallet identities differ')
    runtime.update(run_id=run_id, build_id=build_id, mode='dev', initial_state_sha256=digest(state_raw))
    # IDEA-055 (#84): a dev start needs the manifested BSC RPC for the chain-balance check (GA10). Without it the
    # values stay null, the report names BALANCE_RPC, and the runtime refuses to start.
    runtime['driver'].update(balance_rpc_url=balance_rpc_url, balance_rpc_source_id=balance_rpc_source_id)
    runtime['driver'].update(execution='shadow', assessor='deterministic', intelligence_mode='shadow',
                             cadence_ms=CADENCE_MS, day_roll_window_ms=DAY_ROLL_MS,
                             strategy_profile_sha256=digest(profile_raw),
                             session_calendar_sha256=digest(calendar_raw), issuers=issuers)
    uploader.update(run_id=run_id, build_id=build_id, mode='dev')
    # Explicit bounded dev operations values; no trading-policy parameter changes.
    operations.update(run_id=run_id, archive_prefix='archive/' + run_id, retention_days=82,
                      backup_interval_hours=24, max_attempts=3, retry_seconds=60,
                      max_archive_bytes=64 * 1024 * 1024)
    files = {n: encoded(c) + b'\n' for n, c in
             (('runtime.json', runtime), ('uploader.json', uploader), ('operations.json', operations))}
    files.update({'strategy-profile.json': profile_raw, 'session-calendar.json': calendar_raw,
                  'initial-state.json': state_raw, 'input-capture.json': capture_raw})
    env = 'LARP_ARTIFACT_ROOT=/var/lib/larp-evidence\nLARP_EVIDENCE_CONFIG_MODE=shadow\n'
    if sec_contact:
        from larp.intelligence.config import sec_user_agent
        sec_user_agent({'LARP_SEC_USER_AGENT': sec_contact})
        if any(c in sec_contact for c in '\r\n\x00'):
            raise ContractError('SEC contact must be one line')
        # systemd EnvironmentFile supports a quoted value, with no shell execution.
        env += 'LARP_SEC_USER_AGENT=' + json.dumps(sec_contact) + '\n'
        files['evidence.env'] = env.encode()
    from larp.sources.register import load_register
    register = load_register()[0]
    terms_missing = [s.source_id for s in register.values() if s.enabled and not s.rights.get('terms_evidence_sha256')]
    from larp.sources.register import load_edgar_terms
    if not load_edgar_terms().get('terms_evidence_sha256'):
        terms_missing.append('sec-edgar')
    load_config('shadow')
    report = dict(schema='GateAPreparation.v1', build_id=build_id, run_id=run_id, signing_enabled=False,
                  runtime_mode='dev', execution='shadow', prepared=True, gate_a_passed=False,
                  # No BNB does not stop a shadow run (no gas), but Gate B (DR-06) refuses it (GA-P3, Q-03).
                  missing_inputs=([] if sec_contact else ['SEC_CONTACT']) + ['TERMS_CAPTURE:' + s for s in terms_missing]
                  + ([] if state['bnb_units'] else ['FIRST_BNB (Q-03)'])
                  + ([] if balance_rpc_url else ['BALANCE_RPC'])
                  # GA11: without a chain read, an in-flight transaction cannot be ruled out; Gate B needs it.
                  + ([] if 'chain' in capture else ['CHAIN_BALANCE_CAPTURE']),
                  host_checks={name: 'NOT_RUN' for name in HOST_CHECKS},
                  input_hashes={n: digest(raw) for n, raw in files.items()},
                  notes=['No share ratio or basis verification granted',
                         'Rehearsal window unchanged; pre-Oct21 rounds may HOLD',
                         'Copy retained terms artifacts to the evidence store before startup'])
    files['preparation-report.json'] = encoded(report) + b'\n'
    return files

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
from larp.strategy.execution_bounds import require_open_state_scope
from larp.strategy.profiles import validate_live
from larp.strategy.schema import instant

ROOT = Path(__file__).resolve().parents[2]
CADENCE_MS = 900_000
DAY_ROLL_MS = 300_000
HOST_CHECKS = ('REAL_RECEIVER_ACK', '24H_INGESTION', 'HOST_RESTART', 'HOURLY_ANCHOR',
               'IAM_TLS_ROLES', 'NETWORK_ROUTES', 'TIME_SYNC', 'ALARM_RECEIVED')
MODEL_ROUTING_FILE = '/etc/larp/model-routing.json'
MODEL_BUDGET_ROOT = '/var/lib/larp-runtime/model-budget'
MAX_ROUTING_BYTES = 64 * 1024


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


def rpc_provider_list(url, source_id, providers):
    """GA15 (IDEA-066 PC-RPC01): the ordered balance providers from either the single URL pair or a list, or None.

    The list is checked with the runtime's own `balance_providers`, so prepare never writes a list the runtime refuses."""
    check_balance_rpc(url, source_id)
    if providers is None:
        return None if url is None else [dict(url=url, source_id=source_id)]
    if url is not None:
        raise ContractError('Name the balance RPC list or the single URL pair, not both')
    from larp.runtime.service import balance_providers
    return balance_providers(dict(balance_rpc_providers=providers))


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


CARRY_OVER_SCHEMA = 'HoldingsCarryOver.v1'
CARRY_OVER_FILE = 'holdings-carry-over.json'
CARRY_OVER_KEYS = frozenset(('schema', 'source_run_id', 'wallet_id', 'source_version', 'projection_sha256',
                             'reservations', 'positions', 'exported_at'))


def carried_positions(carry_over, capture, run_id, balances, decimals):
    """IDEA-097 S4: the previous run's exported book, accepted only when it is exactly the captured chain book."""
    c = carry_over
    if (type(c) is not dict or set(c) != CARRY_OVER_KEYS or c['schema'] != CARRY_OVER_SCHEMA
            or type(c['source_run_id']) is not str or not c['source_run_id'] or c['source_run_id'] == run_id
            or type(c['source_version']) is not int or c['source_version'] <= 0
            or type(c['projection_sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', c['projection_sha256'])
            or type(c['exported_at']) is not str or type(c['positions']) is not dict
            or set(c['positions']) != set(TOKENS)):
        raise ContractError('A complete HoldingsCarryOver.v1 export from another run is required')
    if str(c['wallet_id']).lower() != wallet_address(capture['wallet']):
        raise ContractError('The carried-over book belongs to another wallet')
    if c['reservations'] != {}:
        raise ContractError('The carried-over book has reservations in flight')
    instant(c['exported_at'])
    positions = {}
    for symbol, token in sorted(TOKENS.items()):
        row = c['positions'][symbol]
        if type(row) is not dict or set(row) != {'units', 'decimals', 'cost_basis_units'} or any(
                type(row[k]) is not int or row[k] < 0 for k in row):
            raise ContractError('Carried-over positions need non-negative integer units, decimals and cost')
        if row['units'] != balances[token] or row['decimals'] != decimals[symbol]:
            raise ContractError('Carried-over units differ from the captured chain balance: ' + symbol)
        if (row['units'] > 0) != (row['cost_basis_units'] > 0):
            raise ContractError('A carried-over holding needs a positive cost basis, and only a holding has one')
        positions[symbol] = dict(row)
    return positions


def initial_state(capture, profile, run_id, *, mode='dev', carry_over=None):
    """Only a fresh, stock-flat wallet can be initialized without cost-basis history.

    USDT is floored from chain 18 decimals into ledger micro-USDT. Exact raw
    balances and the discarded sub-micro remainder stay in the pinned capture.
    Native BNB stays in wei. Existing holdings need reviewed accounting history:
    an S4 profile (IDEA-097) takes it from the previous run's export, carried at
    that run's cost, so opening equity is cash + BNB value + the carried cost.
    """
    from larp.strategy import carry_over as scope
    balances = raw_balances(capture)
    carried = scope.declared(profile)
    if carried != (carry_over is not None):
        raise ContractError('A holdings carry-over export is required exactly when the profile declares one')
    if not carried and any(balances[token] for token in TOKENS.values()):
        raise ContractError('Existing stock holdings require reviewed cost-basis history')
    costs = profile['quote_cost_summary']
    if costs['bnb_decimals'] != 18:
        raise ContractError('Native BNB must be accounted in wei')
    rows = observation(capture, 'metadata', 'market/rwa/tokens', 'GET')
    decimals = {s: integer(next(r['decimals'] for r in rows
                               if r.get('tokenContractAddress', '').lower() == token))
                for s, token in TOKENS.items()}
    positions = (carried_positions(carry_over, capture, run_id, balances, decimals) if carried else
                 {s: dict(units=0, decimals=decimals[s], cost_basis_units=0) for s in sorted(TOKENS)})
    cash, bnb = balances[USDT] // 10**12, balances[NATIVE]
    opening = (cash + bnb * costs['bnb_price_units'] // 10**18
               + sum(p['cost_basis_units'] for p in positions.values()))
    if type(run_id) is not str or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,99}', run_id) or opening <= 0:
        raise ContractError('A funded run identity is required')
    day = instant(capture['observed_at']).date().isoformat()
    state = dict(schema='PortfolioState.v1', mode=mode, run_id=run_id, wallet_id=wallet_address(capture['wallet']),
                cash_units=cash, bnb_units=bnb, bnb_decimals=18, bnb_price_units=costs['bnb_price_units'],
                opening_equity_units=opening,
                positions=positions,
                reservations={}, applied_events={},
                accounting=dict(realized_units=0, fees_units=0, gas_value_units=0, service_units=0, turnover_units=0),
                risk=dict(day=day, day_anchor_units=opening, peak_units=opening,
                          daily_halt=False, run_halt=False, deep_cut=False))
    check_initial_state(state, capture, mode=mode)
    return state


def check_initial_state(state, capture, *, mode='dev'):
    """GA-P2: the runtime can build its ledger from the state, and it has gate_b DR-06's shape (ported from PR #89)."""
    from larp.integration.runtime import initial_projection, ledger_from
    units = [state.get('cash_units'), state.get('bnb_units'),
             *[p.get('units') for p in (state.get('positions') or {}).values()]]
    if (state.get('schema') != 'PortfolioState.v1' or state.get('wallet_id') != wallet_address(capture['wallet'])
            or state.get('bnb_decimals') != 18 or mode not in ('dev', 'live') or state.get('mode') != mode
            or any(type(u) is not int or u < 0 for u in units)):
        raise ContractError('Initial state lacks the DR-06 shape (identity, wei, matching mode, non-negative units)')
    try:
        ledger_from(initial_projection(state), [])
    except (ValueError, KeyError, TypeError) as error:
        raise ContractError('The runtime cannot build its ledger from the initial state: ' + str(error)) from None


def model_routing(raw, expected_sha256):
    """SG-8: an explicit, reviewed public file; no model, secret or budget construction."""
    from larp.intelligence.common import IntelligenceError
    from larp.intelligence.routing import validate_routing_spec
    try:
        if (type(raw) is not bytes or not 0 < len(raw) <= MAX_ROUTING_BYTES
                or type(expected_sha256) is not str or not re.fullmatch('[0-9a-f]{64}', expected_sha256)
                or digest(raw) != expected_sha256):
            raise ValueError
        spec = json.loads(raw)
        validate_routing_spec(spec)
    except (IntelligenceError, ValueError, TypeError, KeyError, RecursionError):
        raise ContractError('Reviewed model routing bytes or settings refused') from None
    return spec


def model_routing_report(spec, sha256):
    report = dict(sha256=sha256, budget_account=spec['budget_account'],
                routine=spec['routine']['model_id'], reviewer=spec['openai_model'],
                external_reviewers=[e['model_id'] for e in spec['external_reviewers']],
                checks=dict.fromkeys(('AIAND_RUNTIME_SECRET', 'MODEL_BUDGET_INITIALIZATION',
                                      'PROVIDER_IDENTITY', 'SHADOW_TRIAL_EVALUATION'), 'NOT_RUN'))
    if spec['schema'] in ('AIandRouting.v3', 'AIandRouting.v4'):
        report.update(routine=spec['openai_model'], reviewer=spec['external_reviewers'][0]['model_id'],
                      openai_pacing=spec['openai_pacing'], reserve_micro_usd=0)
        if 'openai_trial' in spec:
            report['openai_trial'] = spec['openai_trial']
    if spec['schema'] == 'AIandRouting.v4':
        report['completion_limits'] = dict(openai=spec['openai_max_output_tokens'],
            routine=spec['routine']['max_output_tokens'],
            external_reviewers=[e['max_output_tokens'] for e in spec['external_reviewers']])
    return report


def scoped_rehearsal(profile, mode):
    """LD11-RH01 (equal weight), SJ-11-RH01 (S1): deterministic, model-shadow rehearsal only; never scored adoption."""
    return (mode == 'dev' and profile.get('environment') == 'REHEARSAL'
            and profile.get('baseline') in ('EQUAL_WEIGHT', 'TREND_GUARDED_VOL')
            and profile.get('evidence_mode') == 'SHADOW'
            and profile.get('falsifier_authority') == 'SHADOW' and profile.get('assessment_required') is False)


def prepare(configs, *, profile_raw, capture_raw, calendar_raw, run_id, build_id, now, sec_contact=None,
            balance_rpc_url=None, balance_rpc_source_id=None, balance_rpc_providers=None,
            model_routing_raw=None, model_routing_sha256=None, execution='shadow', runtime_mode='dev',
            adoption_ref=None, untrusted_router_policy_file=None, untrusted_router_policy_sha256=None,
            allowance_recovery=False, carry_over_raw=None):
    """Return filenames -> exact bytes. The caller writes them only to ignored deployment storage.

    The balance RPC is either one `balance_rpc_url` + `balance_rpc_source_id` or an ordered `balance_rpc_providers`
    list (GA15), never both. The untrusted-router policy pair (IDEA-088, IDEA-089 S2-10: the host path of the
    signer's UntrustedRouterPolicy.v1 and its SHA-256) enables the runtime's quote verifier; without it the driver
    block carries no pair and every quote stays CAPABILITY_PROOF_REQUIRED."""
    routing = None
    if model_routing_raw is not None or model_routing_sha256 is not None:
        routing = model_routing(model_routing_raw, model_routing_sha256)
    signed = execution == 'service'
    if routing is not None and routing.get('openai_trial') is not None and (signed or runtime_mode != 'dev'):
        raise ContractError('Unsigned trial routing requires dev/shadow preparation')
    profile, capture = json.loads(profile_raw), json.loads(capture_raw)
    require_open_state_scope(profile, runtime_mode)  # IDEA-089 S2-1 / IDEA-093 FS1
    deterministic_rehearsal = routing is None and scoped_rehearsal(profile, runtime_mode)
    if (execution not in ('shadow', 'service') or runtime_mode not in ('dev', 'live')
            or (not signed and (runtime_mode != 'dev' or adoption_ref is not None))
            or (signed and ((routing is None and not deterministic_rehearsal)
                            or type(adoption_ref) is not str or not adoption_ref.strip()))):
        raise ContractError('Signed preparation needs reviewed routing or scoped deterministic rehearsal and an adoption reference')
    if profile.get('schema') != 'StrategyProfile.v1' or profile.get('mode') != 'LIVE':
        raise ContractError('A separately reviewed LIVE profile is required')
    validate_live(profile)
    if profile.get('environment') != ('FINAL' if runtime_mode == 'live' else 'REHEARSAL'):
        raise ContractError('Profile environment differs from preparation mode')
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
    providers = rpc_provider_list(balance_rpc_url, balance_rpc_source_id, balance_rpc_providers)
    policy = (untrusted_router_policy_file, untrusted_router_policy_sha256)
    if type(allowance_recovery) is not bool or allowance_recovery and policy == (None, None):
        raise ContractError('Allowance recovery needs explicit boolean scope and pinned router policy')
    if policy != (None, None):
        if (type(policy[0]) is not str or not policy[0].startswith('/') or any(c in policy[0] for c in '\r\n\x00')
                or type(policy[1]) is not str or not re.fullmatch('[0-9a-f]{64}', policy[1])):
            raise ContractError('The untrusted-router policy needs an absolute file path and its SHA-256, together')
        if providers is None:
            raise ContractError('The untrusted-router quote verifier needs balance RPC providers')
    if providers is not None and 'chain' not in capture:
        # GA12: with the balance RPC configured, nothing excuses a capture without the chain read.
        raise ContractError('A chain balance capture required: capture with --balance-rpc-url or --balance-rpc-config')
    if 'chain' in capture:
        check_chain(capture, now)
        if providers is not None and capture['chain'].get('source_id') not in {p['source_id'] for p in providers}:
            raise ContractError('The chain balance capture came from another RPC source')
    carry_over = None
    if carry_over_raw is not None:
        # IDEA-097 S4: the previous run's exported book, packaged and hash-pinned with the other inputs.
        if type(carry_over_raw) is not bytes:
            raise ContractError('The holdings carry-over must be the exact export bytes')
        try:
            carry_over = json.loads(carry_over_raw)
        except ValueError:
            raise ContractError('The holdings carry-over must be JSON') from None
    state = initial_state(capture, profile, run_id, mode=runtime_mode, carry_over=carry_over)
    state_raw = encoded(state) + b'\n'
    configs = json.loads(json.dumps(configs))
    runtime, uploader, operations = (configs[n] for n in ('runtime.json', 'uploader.json', 'operations.json'))
    wallet = state['wallet_id']
    if any(c.get('wallet_address') != wallet for c in (runtime, uploader)):
        raise ContractError('Infrastructure and captured wallet identities differ')
    runtime.update(run_id=run_id, build_id=build_id, mode=runtime_mode, initial_state_sha256=digest(state_raw))
    # IDEA-055 (#84): a dev start needs the manifested BSC RPC for the chain-balance check (GA10). Without it the
    # values stay null, the report names BALANCE_RPC, and the runtime refuses to start.
    if 'balance_rpc_providers' in runtime['driver']:
        # IDEA-055 PR 5 (#116): the example lists providers; the runtime refuses a block naming both forms (GA14).
        if providers is not None:
            runtime['driver']['balance_rpc_providers'] = providers
    else:
        if providers is not None and len(providers) > 1:
            raise ContractError('This rendered config uses the single balance_rpc_url form; it cannot hold a backup')
        first = providers[0] if providers else dict(url=None, source_id=None)
        runtime['driver'].update(balance_rpc_url=first['url'], balance_rpc_source_id=first['source_id'])
    runtime['driver'].update(execution=execution, assessor='deterministic', intelligence_mode='live' if signed else 'shadow',
                             cadence_ms=CADENCE_MS, day_roll_window_ms=DAY_ROLL_MS,
                             strategy_profile_sha256=digest(profile_raw),
                             session_calendar_sha256=digest(calendar_raw), issuers=issuers)
    for key in ('model_routing_file', 'model_routing_sha256', 'model_budget_root', 'model_adoption_ref',
                'untrusted_router_policy_file', 'untrusted_router_policy_sha256'):
        runtime['driver'].pop(key, None)
    if policy != (None, None):
        runtime['driver'].update(untrusted_router_policy_file=policy[0], untrusted_router_policy_sha256=policy[1])
    runtime['driver'].pop('allowance_recovery', None)
    if allowance_recovery:
        runtime['driver']['allowance_recovery'] = True
    if routing is not None:
        runtime['driver'].update(assessor='aiand_routed', model_routing_file=MODEL_ROUTING_FILE,
                                 model_routing_sha256=model_routing_sha256, model_budget_root=MODEL_BUDGET_ROOT)
    if signed:
        runtime['driver']['model_adoption_ref'] = adoption_ref
    uploader.update(run_id=run_id, build_id=build_id, mode=runtime_mode)
    # Explicit bounded dev operations values; no trading-policy parameter changes.
    operations.update(run_id=run_id, archive_prefix='archive/' + run_id, retention_days=82,
                      backup_interval_hours=24, max_attempts=3, retry_seconds=60,
                      max_archive_bytes=64 * 1024 * 1024)
    files = {n: encoded(c) + b'\n' for n, c in
             (('runtime.json', runtime), ('uploader.json', uploader), ('operations.json', operations))}
    files.update({'strategy-profile.json': profile_raw, 'session-calendar.json': calendar_raw,
                  'initial-state.json': state_raw, 'input-capture.json': capture_raw})
    if routing is not None:
        files['model-routing.json'] = model_routing_raw
    if carry_over_raw is not None:
        files[CARRY_OVER_FILE] = carry_over_raw
    env = 'LARP_ARTIFACT_ROOT=/var/lib/larp-evidence\nLARP_EVIDENCE_CONFIG_MODE=' + ('live' if signed else 'shadow') + '\n'
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
    if not signed:
        load_config('shadow')
    report = dict(schema='GateAPreparation.v1', build_id=build_id, run_id=run_id, signing_enabled=False,
                  runtime_mode=runtime_mode, execution=execution, prepared=True, gate_a_passed=False,
                  # No BNB does not stop a shadow run (no gas), but Gate B (DR-06) refuses it (GA-P3, Q-03).
                  missing_inputs=([] if sec_contact else ['SEC_CONTACT']) + ['TERMS_CAPTURE:' + s for s in terms_missing]
                  + ([] if state['bnb_units'] else ['FIRST_BNB (Q-03)'])
                  + ([] if providers else ['BALANCE_RPC'])
                  # GA11: without a chain read, an in-flight transaction cannot be ruled out; Gate B needs it.
                  + ([] if 'chain' in capture else ['CHAIN_BALANCE_CAPTURE']),
                  host_checks={name: 'NOT_RUN' for name in HOST_CHECKS},
                  input_hashes={n: digest(raw) for n, raw in files.items()},
                  notes=['No share ratio or basis verification granted',
                         'Rehearsal window unchanged; pre-Oct21 rounds may HOLD',
                         'Copy retained terms artifacts to the evidence store before startup'])
    if carry_over is not None:
        report['holdings_carry_over'] = dict(sha256=digest(carry_over_raw), source_run_id=carry_over['source_run_id'],
                                             source_version=carry_over['source_version'])
        report['notes'].append('Holdings carried over at the previous run\'s cost; Keegan reviews the accounting')
    if allowance_recovery:
        report['allowance_recovery'] = True
        report['missing_inputs'].append('ALLOWANCE_RECOVERY_SIGNER_GAS_AND_HOST_ACCEPTANCE')
    if routing is not None:
        report['model_routing'] = model_routing_report(routing, model_routing_sha256)
        report['notes'].append('OpenAI runtime secret is optional; absent or exhausted OpenAI uses external review')
    if signed:
        report['model_adoption_ref'] = adoption_ref
        report['missing_inputs'].append('LIVE_INTELLIGENCE_SETTINGS_AND_SIGNED_GATE_B_ACCEPTANCE')
        report['notes'].append('Signed scope prepared only; no activation or signing authority granted')
    files['preparation-report.json'] = encoded(report) + b'\n'
    return files

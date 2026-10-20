"""Read-only Gate B observations and offline review inventory. Never enables signing."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from larp.contracts import ContractError
from larp.execution import Blocked, DependencyUnavailable
from larp.marketdata.web3 import Artifacts, utc
from larp.strategy.profiles import quote_summary, validate_live
from larp.strategy.schema import initial_gas_only, instant
from .chain import ChainEvidence, Rpc, evidence_boundary, hash_value, quantity
from .main import BUILD_KEYS, validate_config

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 2 * 1024 * 1024


def address(value):
    if type(value) is not str or not re.fullmatch(r'0x[0-9a-fA-F]{40}', value):
        raise Blocked('public wallet/router address required')
    return value.lower()


@evidence_boundary
def probe_chain(rpc, *, wallet, router, observed_at):
    """Bracket fixed-block public observations with canonical/finalized identity.

    Nonces are separately observed latest/pending snapshots, not an atomic lock.
    Router code presence is not ABI, proxy or route qualification.
    """
    wallet, router = address(wallet), address(router)
    instant(observed_at)
    if type(rpc.source_id) is not str or not rpc.source_id:
        raise Blocked('provider source ID required')
    ChainEvidence(rpc).check_chain()
    finalized = rpc.call('eth_getBlockByNumber', ['finalized', False])
    height, block_hash = quantity(finalized['number']), hash_value(finalized['hash'])

    def canonical():
        block = rpc.call('eth_getBlockByNumber', [hex(height), False])
        if quantity(block['number']) != height or hash_value(block['hash']) != block_hash:
            raise Blocked('finalized block identity changed')

    canonical()
    balance = quantity(rpc.call('eth_getBalance', [wallet, hex(height)]))
    tokens = token_balances(rpc, wallet, height)  # GB-2: USDT and every pinned bStock, same finalized block
    # GB-1: the nonce at the finalized block; a mined but unfinalized transaction makes it lag `latest`.
    finalized_nonce = quantity(rpc.call('eth_getTransactionCount', [wallet, hex(height)]))
    latest = quantity(rpc.call('eth_getTransactionCount', [wallet, 'latest']))
    pending = quantity(rpc.call('eth_getTransactionCount', [wallet, 'pending']))
    code = rpc.call('eth_getCode', [router, hex(height)])
    if type(code) is not str or not re.fullmatch(r'0x(?:[0-9a-fA-F]{2})*', code):
        raise Blocked('invalid router bytecode')
    canonical()
    ChainEvidence(rpc).check_chain()
    code = bytes.fromhex(code[2:])
    blockers = []
    if balance == 0:
        blockers.append('FIRST_BNB_REQUIRED')
    if latest != pending:
        blockers.append('PENDING_NONCE_REQUIRES_RECONCILIATION')
    if finalized_nonce != latest:
        blockers.append('UNFINALIZED_TRANSACTION_REQUIRES_RECONCILIATION')
    if not code:
        blockers.append('ROUTER_CODE_MISSING')
    return dict(schema='GateBChainEvidence.v1', observed_at=observed_at, source_id=rpc.source_id,
        chain_id=56, wallet=wallet, router=router, finalized_block_number=height,
        finalized_block_hash=block_hash, native_balance_wei=balance, native_balance_scope='FINALIZED_BLOCK',
        finalized_nonce=finalized_nonce, tokens=tokens,
        latest_nonce=latest, pending_nonce=pending, router_code_sha256=hashlib.sha256(code).hexdigest(),
        router_code_bytes=len(code), blockers=blockers, signing_enabled=False)


def token_balances(rpc, wallet, height):
    """decimals()/balanceOf(wallet) for USDT and the pinned bStocks at `height`, through Rpc's eth_call allowlist."""
    from .balances import assets, word
    from .chain import BALANCE_OF_CALL, DECIMALS_CALL
    tokens = {}
    for name, contract in assets().items():
        decimals = word(rpc.call('eth_call', [dict(to=contract, data=DECIMALS_CALL), hex(height)]))
        units = word(rpc.call('eth_call', [dict(to=contract, data=BALANCE_OF_CALL + '0' * 24 + wallet[2:]),
                                           hex(height)]))
        if decimals > 77:
            raise Blocked('implausible token decimals')
        tokens[name] = dict(contract=contract, decimals=decimals, units=units)
    return tokens


def starting_balances_match(state, chain):
    """GB-2: the pinned starting cash and every bStock position equal the finalized chain balances.

    Cash is micro-USDT floored from the chain's decimals (Gate A's convention). A position equals its chain units at
    the same decimals; zero equals zero at any scale. A pinned token without a position counts as zero."""
    from .balances import assets
    tokens, pinned = chain['tokens'], assets()
    if type(tokens) is not dict or set(tokens) != set(pinned):
        return False
    for name, row in tokens.items():
        if (type(row) is not dict or row.get('contract') != pinned[name]
                or any(type(row.get(k)) is not int or row[k] < 0 for k in ('decimals', 'units'))):
            return False
    usdt = tokens['USDT']
    if usdt['decimals'] < 6 or state['cash_units'] != usdt['units'] // 10**(usdt['decimals'] - 6):
        return False
    positions = state['positions']
    if type(positions) is not dict or set(positions) - (set(pinned) - {'USDT'}):
        return False
    for name in set(pinned) - {'USDT'}:
        position, row = positions.get(name, dict(units=0)), tokens[name]
        if position['units'] == row['units'] == 0:
            continue
        if position['units'] != row['units'] or position.get('decimals') != row['decimals']:
            return False
    return True


REQUIREMENTS = {
    1: ('Isaac / Keith', 'Three days including weekend of hash-verified five-name captures and measured cost summary'),
    2: ('Isaac / Keegan', 'Verified source/evidence or named-reviewed untrusted policy, applicable recorded-route replay/preflight and logged dev approve/swap'),
    3: ('Isaac / Keegan', 'Isolated signer identity, selected router evidence/policy hash and host tests; provider-qualified nonce/finality evidence'),
    4: ('Isaac / Keegan', 'Pinned dev execution configuration and PostgreSQL crash/fencing acceptance on reviewed build'),
    5: ('Keegan / Keith', 'Real-fill/gas/reservation success, revert and replay acceptance on reviewed build'),
    6: ('Isaac / Keith', 'Initial native funding, exact accounting units and reviewed gas scope'),
    7: ('Keegan', 'Durable receiver per-event/chunk ACK and crash/rejection drills'),
    8: ('Keith / Yao', 'Recorded-real token sessions and total-cost impact inputs'),
    9: ('Keith / Yao', 'Hash-pinned REHEARSAL LIVE profile with sourced, reviewed measurements'),
    10: ('Yao / Keith', 'Live red-flag predicates and recorded verification fixtures'),
    11: ('Yao / Keith', 'Declared assessor fallback or bake-off with round cost and complete I/O'),
    12: ('Yao / Keegan', 'Dated source licences, SEC identity and gap-free 24-hour host ingestion'),
    13: ('Keegan / Isaac', 'Host restart and autonomous HALT incident drills'),
    14: ('Keith / Keegan', 'End-of-run clock boundary acceptance on reviewed build'),
    15: ('Keegan / Yao', 'Hourly write-once anchors and verification evidence'),
    16: ('Keegan / Isaac', 'Applied infrastructure, actual alert delivery and restore drill'),
    18: ('Keegan / all', 'Registered build manifest, version event, deviations and service list'),
    19: ('Keegan / Yao', 'Recorded shadow-day replay reproduces the head'),
    20: ('Keegan / all', 'Green integrated CI and reviewer approval on merged integration commit'),
}


def read_json(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise Blocked('public input exceeds size limit')
    value = json.loads(raw)
    if type(value) is not dict:
        raise Blocked('public input must be a JSON object')
    return raw, value


def pinned(ref, base_dir):
    if type(ref) is not dict or set(ref) != {'path', 'sha256'}:
        raise Blocked('path and SHA-256 pin required')
    if type(ref['path']) is not str or not ref['path']:
        raise Blocked('public evidence path required')
    path = Path(ref['path'])
    path = path if path.is_absolute() else Path(base_dir) / path
    raw, value = read_json(path)
    if hashlib.sha256(raw).hexdigest() != ref['sha256']:
        raise Blocked('public input hash mismatch')
    return value


def readiness_report(inputs, *, now, base_dir):
    """Validate supplied public inputs, leaving acceptance to owners and reviewers.

    VALIDATED means this tool's limited input check, never the whole DR item.
    No arbitrary attestation/ready flags are accepted as execution authority.
    """
    checks = {f'DR-{i:02}': dict(status='BLOCKED', owner=owner, required=requirement,
                               detail='Owner acceptance evidence still required')
              for i, (owner, requirement) in REQUIREMENTS.items()}
    result = dict(schema='GateBReport.v1', observed_at=now, status='BLOCKED', signing_enabled=False,
                  acceptance='OWNER_REVIEW_REQUIRED', router_mode='unconfigured', checks=checks, evidence_hashes={})
    instant(now)
    if inputs is None:
        result['detail'] = 'No GateBInputs.v1 supplied; this is the required evidence inventory'
        return result
    allowed = {'schema', 'build_id', 'run_id', 'wallet', 'chain_max_age_seconds', 'files'}
    if type(inputs) is not dict or set(inputs) != allowed or inputs['schema'] != 'GateBInputs.v1':
        raise Blocked('GateBInputs.v1 exact fields required; no readiness overrides')
    if not re.fullmatch(r'[0-9a-f]{40}', str(inputs['build_id'])):
        raise Blocked('full build commit required')
    if type(inputs['run_id']) is not str or not inputs['run_id']:
        raise Blocked('run identity required')
    wallet = address(inputs['wallet'])
    age = inputs['chain_max_age_seconds']
    if type(age) is not int or age <= 0:
        raise Blocked('explicit positive chain evidence freshness budget required')
    files = inputs['files']
    if type(files) is not dict or set(files) - {'execution_config', 'chain', 'initial_state', 'quote_costs',
                                                'router_check'}:
        raise Blocked('unsupported public evidence input')
    result.update(build_id=inputs['build_id'], run_id=inputs['run_id'], wallet=wallet)
    errors = (Blocked, ContractError, OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError)

    def load(name):
        value = pinned(files[name], base_dir)
        result['evidence_hashes'][name] = files[name]['sha256']
        return value

    config = profile = chain = None
    try:
        value = validate_config(load('execution_config'))
        if (value['build_id'] != inputs['build_id'] or value['run_id'] != inputs['run_id']
                or value['wallet_address'] != wallet or value['mode'] != 'dev'
                or any(value.get(k) in (None, '') for k in BUILD_KEYS)):
            raise Blocked('execution identity or required configuration differs')
        address(value['router'])
        config = value
        checks['DR-04'].update(status='VALIDATED', detail='Configuration only; crash/fencing CI and review still required')
    except errors:
        checks['DR-04']['detail'] = 'Execution configuration absent, invalid, mismatched or hash changed'
    try:
        from .config import untrusted_router_settings
        from .router import PinnedRouterDecoder, evidence_settings, validate_route_report
        settings = None if config is None else evidence_settings(config)
        untrusted = None if config is None else untrusted_router_settings(config)
        if untrusted is not None:
            result['router_mode'] = 'untrusted'
            checks['DR-02']['required'] = ('Named-reviewed untrusted router/code/facet/allowance policy and hash; '
                'fresh recorded-quote replay/live preflight, residual-risk acceptance and logged dev approve/swap')
            # IDEA-070 B02-U: no source guarantees; DEV-23 records the residual risk owners must accept.
            from .untrusted_router import UntrustedRouterDecoder
            decoder = UntrustedRouterDecoder(pinned(dict(path=untrusted[0], sha256=untrusted[1]), base_dir),
                                             policy_sha256=untrusted[1])
            if decoder.router != address(config['router']):
                raise Blocked('untrusted-router policy is for another router')
            value = load('router_check')
            if (type(value) is not dict or value.get('schema') != 'UntrustedRouteCheck.v1'
                    or value.get('status') != 'PASS' or value.get('policy_sha256') != untrusted[1]
                    or type(value.get('quotes')) is not int or value['quotes'] < 1):
                raise Blocked('passing untrusted-route check for this policy required')
            result['evidence_hashes']['untrusted_router_policy'] = untrusted[1]
            checks['DR-02'].update(status='VALIDATED', detail='UNTRUSTED router policy and a passing recorded-quote '
                                   'check only (DEV-23); no source guarantees. Owner acceptance of the residual risk, '
                                   'live preflight and a logged dev approve + swap still required')
        else:
            if settings is None:
                raise Blocked('router evidence not configured')
            result['router_mode'] = 'verified'
            checks['DR-02']['required'] = ('Verified router/proxy/nested ABI and deadline evidence; '
                'independent source review, recorded-real responses and logged dev approve/swap')
            decoder = PinnedRouterDecoder(pinned(dict(path=settings[0], sha256=settings[1]), base_dir),
                                          evidence_sha256=settings[1])
            if decoder.router != address(config['router']):
                raise Blocked('router evidence is for another router')
            value = load('router_check')
            validate_route_report(value, decoder, wallet=wallet)
            result['evidence_hashes']['router_evidence'] = settings[1]
            checks['DR-02'].update(status='VALIDATED', detail='Pinned router evidence and a passing recorded-route check '
                                   'only; owner review of the verified source and a logged dev approve + swap still required')
    except errors:
        if result['router_mode'] == 'untrusted':
            checks['DR-02']['detail'] = ('Pinned named-reviewed untrusted policy or matching recorded-quote check '
                'absent, invalid or mismatched; live preflight and owner acceptance remain required')
        elif result['router_mode'] == 'verified':
            checks['DR-02']['detail'] = ('Pinned router evidence or a passing recorded-route check absent or '
                'mismatched; independent source review remains required')
        else:
            checks['DR-02']['detail'] = ('Select exactly one complete pinned router evidence or untrusted policy '
                'pair in a valid execution configuration; applicable review/replay remains required')
    try:
        if config is None:
            raise Blocked('valid execution config required')
        value = pinned(dict(path=config['strategy_profile_file'], sha256=config['strategy_profile_sha256']), base_dir)
        validate_live(value)
        if value.get('schema') != 'StrategyProfile.v1' or value.get('mode') != 'LIVE' or value['environment'] != 'REHEARSAL':
            raise Blocked('REHEARSAL LIVE profile required')
        profile = value
        result['evidence_hashes']['strategy_profile'] = config['strategy_profile_sha256']
        checks['DR-09'].update(status='VALIDATED', detail='Profile shape/provenance only; real capture attribution and owner review still required')
    except errors:
        checks['DR-09']['detail'] = 'Pinned REHEARSAL LIVE profile absent or rejected by existing validator'
    try:
        value = load('chain')
        elapsed = (instant(now) - instant(value['observed_at'])).total_seconds()
        if (config is None or value['schema'] != 'GateBChainEvidence.v1' or type(value['chain_id']) is not int
                or value['chain_id'] != 56 or value['wallet'] != wallet or value['router'] != address(config['router'])
                or not 0 <= elapsed <= age or value['signing_enabled'] is not False
                or type(value['source_id']) is not str or value['source_id'] != config['rpc_source_id']
                or value['native_balance_scope'] != 'FINALIZED_BLOCK'):
            raise Blocked('chain capture identity/freshness differs')
        hash_value(value['finalized_block_hash'])
        for k in ('finalized_block_number', 'native_balance_wei', 'finalized_nonce', 'latest_nonce', 'pending_nonce',
                  'router_code_bytes'):
            if type(value[k]) is not int or not 0 <= value[k] < 2**256:
                raise Blocked('invalid chain capture quantity')
        if (value['native_balance_wei'] == 0 or value['latest_nonce'] != value['pending_nonce']
                or value['finalized_nonce'] != value['latest_nonce']
                or value['router_code_bytes'] == 0 or value['blockers'] != []
                or not re.fullmatch(r'[0-9a-f]{64}', value['router_code_sha256'])):
            raise Blocked('chain capture has unresolved blockers')
        chain = value
        checks['DR-03']['detail'] = 'Public chain snapshot checked; isolated signer identity and provider/host qualification still required'
    except errors:
        checks['DR-03']['detail'] = 'Public chain capture missing, blocked, stale or mismatched; signer/host acceptance also required'
    try:
        from larp.integration.runtime import initial_projection, ledger_from
        value = load('initial_state')
        if (value['schema'] != 'PortfolioState.v1' or value['wallet_id'] != wallet
                or value['run_id'] != inputs['run_id'] or type(value['bnb_decimals']) is not int
                or value['bnb_decimals'] != 18 or value.get('mode') not in ('dev', 'LIVE')):
            raise Blocked('native ledger identity or exact wei scale differs')
        for units in [value['cash_units'], value['bnb_units'], *[p['units'] for p in value['positions'].values()]]:
            if type(units) is not int or units < 0:
                raise Blocked('invalid starting balance units')
        ledger_from(initial_projection(value), [])
        if chain is None or value['bnb_units'] != chain['native_balance_wei'] or value['bnb_units'] == 0:
            raise Blocked('initial native funding differs from chain capture')
        if not starting_balances_match(value, chain):
            raise Blocked('initial cash or positions differ from chain capture')
        if profile is not None and initial_gas_only(profile):
            checks['DR-06']['detail'] = ('Initial-only funding/18-decimal ledger checked; measured whole-run seeding, '
                'full-exit reserve, low-gas incident/alarm and full balance reconciliation acceptance still required; '
                'native top-ups are excluded')
        else:
            checks['DR-06']['detail'] = 'Initial native funding/18-decimal ledger checked; C1, full balance reconciliation and logged top-up still required'
    except errors:
        if profile is not None and initial_gas_only(profile):
            checks['DR-06']['detail'] = ('Pinned initial-only portfolio/funded native chain evidence absent or '
                'mismatched; measured seeding/reserve and low-gas acceptance still required')
        else:
            checks['DR-06']['detail'] = 'Pinned initial portfolio/funded native chain evidence absent or mismatched; top-up rehearsal still required'
    try:
        value = quote_summary(load('quote_costs'))
        if profile is None or value != profile['quote_cost_summary']:
            raise Blocked('cost summary differs from profile')
        checks['DR-01']['detail'] = 'Consumer cost-summary shape/profile match checked; raw capture attribution and three-day/weekend coverage still required'
    except errors:
        checks['DR-01']['detail'] = 'Pinned measured cost summary absent/invalid; logger QuoteSummary.v1 cannot substitute for QuoteCostSummary.v1'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    probe = commands.add_parser('probe-chain')
    for name in ('rpc-url', 'source-id', 'wallet', 'router', 'artifact-root'):
        probe.add_argument('--' + name, required=True)
    report = commands.add_parser('report')
    report.add_argument('--inputs')
    report.add_argument('--artifact-root', required=True)
    args = parser.parse_args(argv)
    try:
        root = Path(args.artifact_root).resolve()
        if root == ROOT or ROOT in root.parents:
            raise Blocked('external artifact root required')
        artifacts = Artifacts(root)
        if args.command == 'probe-chain':
            rpc = Rpc(args.rpc_url, artifacts=artifacts, source_id=args.source_id)
            result = probe_chain(rpc, wallet=args.wallet, router=args.router, observed_at=utc())
        else:
            path = Path(args.inputs).resolve() if args.inputs else None
            inputs = read_json(path)[1] if path else None
            result = readiness_report(inputs, now=utc(), base_dir=path.parent if path else root)
        sha = artifacts.put(result)
        summary = dict(schema=result['schema'], artifact_sha256=sha, signing_enabled=False,
                       status=result.get('status', 'OBSERVED'), blockers=result.get('blockers', []))
        if args.command == 'report':
            summary['blocked_checks'] = sorted(name for name, check in result['checks'].items()
                                               if check['status'] == 'BLOCKED')
            summary['acceptance'] = result['acceptance']
        print(json.dumps(summary))
        return 2 if result.get('status') == 'BLOCKED' or result.get('blockers') else 0
    except (Blocked, DependencyUnavailable, ContractError, OSError, ValueError, TypeError, KeyError):
        print(json.dumps(dict(status='REFUSED', signing_enabled=False, reason='PUBLIC_EVIDENCE_UNAVAILABLE_OR_INVALID')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

"""LD10-Q01: private numeric coverage inputs and report.

Without --bindings it never assembles signer.json. With --bindings (SJ-04) it pins the
exact hosted IAM database and untrusted-router settings, rebinds the reconciled wallet
holdings to the selected signed run, and assembles a key-free candidate at the review's
own timestamp, so the 300 s quote limit is checked once for both.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zlib

from larp.contracts import ContractError, Document
from larp.execution_live.caps_review import ERRORS, review

ROOT = Path(__file__).resolve().parents[2]
# The reviewed equal-weight rehearsal profile e95d5842 (LD10-P03); an S1 run names its own with --profile (SJ-11-RH01).
DEFAULT_PROFILE = ROOT / 'docs/build/evidence/rehearsal-exit-split-20261021/rehearsal-deterministic.json'
# SJ-04: the hosted execution role and the exact private binding fields, nothing else.
BINDING_KEYS = {'schema', 'run_id', 'build_id', 'database_host', 'database_name', 'database_ca_file',
                'database_ca_sha256', 'region', 'untrusted_router_policy_file', 'untrusted_router_policy_sha256'}
SHA256 = re.compile(r'[0-9a-f]{64}')


def require(ok):
    """An explicit check: unlike assert, it still refuses under python -O."""
    if not ok:
        raise AssertionError('Rehearsal packet check failed')


def outside_checkout(path):
    """Hosted outputs carry the private bindings, so refuse checkout paths before writing anything."""
    path = Path(path).resolve()
    if path == ROOT or ROOT in path.parents:
        raise ContractError('Hosted private outputs must remain outside the checkout')


def read_packet(raw):
    """The decoded packet: either its JSON, or the probe's two stdout lines with a matching packet_sha256."""
    text = raw.decode().strip()
    if text.startswith('{'):
        return json.loads(text)
    lines = text.splitlines()
    if len(lines) != 2:
        raise ContractError('Capture output must be exactly the packet and its hash')
    body = zlib.decompress(base64.b64decode(lines[0], validate=True))
    if hashlib.sha256(body).hexdigest() != json.loads(lines[1])['packet_sha256']:
        raise ContractError('Capture packet differs from its packet_sha256')
    return json.loads(body)


def hosted(bindings):
    """Exact private hosted settings (SJ-04); paths must also exist locally at the same absolute paths."""
    if type(bindings) is not dict or set(bindings) != BINDING_KEYS or bindings['schema'] != 'RehearsalSignerBindings.v1':
        raise ContractError('RehearsalSignerBindings.v1 exact fields required')
    if (any(type(v) is not str or not v.strip() for v in bindings.values())
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', bindings['run_id'])
            or not re.fullmatch(r'[0-9a-f]{40}', bindings['build_id'])
            or not all(SHA256.fullmatch(bindings[k]) for k in ('database_ca_sha256', 'untrusted_router_policy_sha256'))
            or not all(Path(bindings[k]).is_absolute() for k in ('database_ca_file', 'untrusted_router_policy_file'))):
        raise ContractError('Hosted signer bindings are malformed')
    connection = {k: v for k, v in bindings.items() if k not in ('schema', 'run_id', 'build_id')}
    return dict(connection, database_user='larp_execution')


def held(reservations):
    """True while any reservation holds units. The LD02 probe groups the reservations table by asset as
    {asset: {count, units}}; released rows stay with zero units, so a source run that has traded still lists them
    (IDEA-097: run 4). Only positive units are in flight, as X1 reads them (PR284-RV01-1)."""
    if type(reservations) is dict:
        return any(type(r) is not dict or type(r.get('units')) is not int or r['units'] != 0
                   for r in reservations.values())
    return bool(reservations)


def chain_start(holdings, portfolio, usdt_deficit, usdt_surplus=0):
    """SJ-04-A1: a new run's holdings are the finalized chain values. Stocks must match the source ledger;
    USDT may fall short by exactly the declared seed debit, or exceed it by exactly a declared top-up (IDEA-104
    S5R2-8), never both; BNB may only exceed it."""
    assets = holdings['assets']
    require(set(assets) == {'USDT', 'BNB', *portfolio['positions']})
    require(all(assets[s]['cls'] == 'MATCH' and assets[s]['chain'] == portfolio['positions'][s]['units']
                for s in portfolio['positions']))
    usdt, bnb = assets['USDT'], assets['BNB']
    require(usdt['ledger'] == portfolio['cash_units'] and bnb['ledger'] == portfolio['bnb_units'])
    require(not (usdt_deficit and usdt_surplus))
    require(usdt['chain'] - usdt['ledger'] == usdt_surplus - usdt_deficit
            and usdt['cls'] == ('DEFICIT' if usdt_deficit else 'SURPLUS' if usdt_surplus else 'MATCH'))
    require(bnb['chain'] >= bnb['ledger'] and bnb['cls'] in ('MATCH', 'SURPLUS'))
    # compare_balances' overall status must agree with these classes (never SKIPPED).
    require(holdings['status'] == ('DEFICIT' if usdt_deficit else 'SURPLUS_ONLY'
                                   if usdt_surplus or bnb['cls'] == 'SURPLUS' else 'MATCH'))
    return dict(portfolio, cash_units=usdt['chain'], bnb_units=bnb['chain'])


def collect(packet, output, build_id, *, bindings=None, now=None, usdt_deficit=0, usdt_surplus=0, profile=DEFAULT_PROFILE,
            allowance_recovery=False):
    if bindings is not None:
        outside_checkout(output)
    # The profile must be the one the probe carried (selected_profile_sha256), checked before any output exists.
    profile_raw = Path(profile).read_bytes()
    require(hashlib.sha256(profile_raw).hexdigest() == packet['selected_profile_sha256'])
    selected = json.loads(profile_raw)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    private = packet['private_caps_inputs']
    require(packet['configs_unchanged'])
    require(packet['holdings']['status'] == 'MATCH' or bindings is not None)
    require(type(usdt_deficit) is int and usdt_deficit >= 0 and (bindings is not None or usdt_deficit == 0))
    require(type(usdt_surplus) is int and usdt_surplus >= 0 and (bindings is not None or usdt_surplus == 0))
    require(packet['holdings']['latest_nonce'] == packet['holdings']['pending_nonce'])
    require(not held(packet['in_flight']['reservations']) and not packet['in_flight']['execution_pending'])
    # IDEA-097 S4: with IDEA-096 allowance recovery opted in, the new run clears a leftover allowance itself.
    require(type(allowance_recovery) is bool)
    require(allowance_recovery or not any(packet['router']['allowances_to_router'].values()))
    decision = json.loads((ROOT / 'docs/build/evidence/signer-numeric-ceilings-20261021.json').read_bytes())
    policy = decision['policies']['development']['signing_policy']
    portfolio = private['portfolio']
    run_id = packet['identity']['run_id']
    if bindings is not None:
        connection = hosted(bindings)
        if bindings['build_id'] != build_id:
            raise ContractError('Hosted bindings name another build')
        # The new signed run has no ledger yet: it starts from the finalized chain holdings, checked
        # against the source ledger (chain_start), nonce, allowances and nothing in flight. The source stays recorded.
        run_id = bindings['run_id']
        portfolio = dict(chain_start(packet['holdings'], portfolio, usdt_deficit, usdt_surplus), run_id=run_id)
    config = dict(schema='ExecutionService.v1', run_id=run_id, build_id=build_id,
        mode='dev', wallet_address=private['wallet'], interval_seconds=1, database_dsn_file='/etc/larp/execution-dsn',
        router=policy['allowed_spenders'][0], token_decimals=private['token_decimals'],
        max_gas=decision['execution_ceiling']['max_gas'],
        max_gas_price=decision['execution_ceiling']['max_gas_price_wei'],
        gas_budget=selected['gas_action_budget_units'], allowance_recovery=allowance_recovery,
        strategy_profile_file='/etc/larp/strategy-profile.json',
        strategy_profile_sha256=packet['selected_profile_sha256'])
    if bindings is not None:
        del config['database_dsn_file']
        config.update(connection)
    # Without bindings: proposed numeric execution scope only; actual DB/RPC/CA/run/release
    # configuration is a separate LD16/17 binding. This file is never installed by this tool.
    def pin(name, value, raw=None):
        raw = raw or json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n'
        with (output / name).open('xb') as stream:
            stream.write(raw)
        (output / name).chmod(0o600)
        return dict(path=name, sha256=hashlib.sha256(raw).hexdigest())
    base = json.dumps(policy, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    require(hashlib.sha256(base).hexdigest() == decision['policies']['development']['sha256_canonical_json_lf'])
    # The reviewed development policy, with only the zero-only recovery scope switched on when opted in (IDEA-096).
    policy_ref = pin('signing-policy.json', dict(policy, allowance_recovery=True) if allowance_recovery else policy)
    # The exact selected bytes: an S1 profile's provenance is UTF-8 (e.g. "IDEA-075 §4"), which the ASCII encoder
    # above would escape, so re-encoding would no longer match selected_profile_sha256 (SJ-11-RH01).
    profile_ref = pin('profile.json', selected, profile_raw)
    require(profile_ref['sha256'] == config['strategy_profile_sha256'])
    inputs = dict(schema='GateBCapsInputs.v1', wallet=private['wallet'], run_id=config['run_id'],
        build_id=build_id, environment='REHEARSAL', max_age_seconds=300,
        files=dict(profile=profile_ref, signing_policy=policy_ref,
            execution_config=pin('execution-config.json' if bindings else 'execution-numeric-scope.json', config),
            initial_state=pin('current-holdings.json', portfolio)),
        quote_artifacts=[pin('quote-%02d.json' % n, r) for n, r in enumerate(private['quote_artifacts'])])
    now = now or datetime.now(timezone.utc).isoformat()
    result = review(inputs, now=now, base_dir=output)
    pin('inputs.json', inputs)
    pin('review.json', result)
    if bindings is not None:
        holdings = packet['holdings']
        pin('portfolio-rebinding.json', dict(source_run_id=packet['identity']['run_id'], run_id=run_id,
            source_portfolio_sha256=Document.from_dict(private['portfolio']).digest('PortfolioState.v1'),
            accepted_usdt_deficit_units=usdt_deficit, accepted_usdt_surplus_units=usdt_surplus,
            status=holdings['status'], assets=holdings['assets'],
            block=holdings['block'], observation_sha256=holdings['observation_sha256']))
    return inputs, result, now


def assemble_hosted(packet, output, bindings, signer_out, *, now=None, usdt_deficit=0, usdt_surplus=0,
                    profile=DEFAULT_PROFILE, allowance_recovery=False):
    """SJ-04: review and assemble on one clock; a refusal writes no candidate and echoes nothing private."""
    from larp.signer.assembly import assemble, write_new
    outside_checkout(signer_out)
    inputs, result, now = collect(packet, output, bindings['build_id'], bindings=bindings, now=now,
                                  usdt_deficit=usdt_deficit, usdt_surplus=usdt_surplus, profile=profile,
                                  allowance_recovery=allowance_recovery)
    if result['numeric_status'] != 'COVERED':
        return result, now, None
    files = assemble(inputs, now=now, base_dir=output)
    write_new(signer_out, files)
    return result, now, hashlib.sha256(files['signer.json']).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True,
                        help='decoded packet JSON, or the capture stdout (packet line + packet_sha256 line)')
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--build-id', help='numeric-only review; hosted mode takes the build from --bindings')
    parser.add_argument('--bindings', type=Path, help='private RehearsalSignerBindings.v1 (SJ-04)')
    parser.add_argument('--signer-out', type=Path, help='new private directory outside the checkout')
    parser.add_argument('--accept-usdt-deficit-units', type=int, default=0,
                        help='hosted only: exact micro-USDT the chain may hold below the source ledger (SJ-04-A1)')
    parser.add_argument('--accept-usdt-surplus-units', type=int, default=0,
                        help='hosted only: exact micro-USDT the chain may hold above the source ledger, a declared '
                             'dev-wallet top-up (IDEA-104 S5R2-8); never together with a deficit')
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE,
                        help='the selected profile the probe carried; its SHA-256 must equal selected_profile_sha256 '
                             '(default: the reviewed equal-weight profile)')
    parser.add_argument('--allowance-recovery', action='store_true',
                        help='IDEA-096/097: opt execution and signer policy into zero-only allowance recovery; '
                             'a leftover router allowance is then accepted for the new run to clear')
    args = parser.parse_args(argv)
    if args.bindings is None:
        if (args.build_id is None or args.signer_out is not None or args.accept_usdt_deficit_units
                or args.accept_usdt_surplus_units):
            parser.error('--build-id is required; --signer-out and a USDT deficit or surplus need --bindings')
        _, result, now = collect(read_packet(args.packet.read_bytes()), args.output_dir, args.build_id,
                                 profile=args.profile, allowance_recovery=args.allowance_recovery)
        print(json.dumps(dict(numeric_status=result['numeric_status'], blockers=result['blockers'],
                             reviewed_at=now, missing=result['missing_quote_coverage'])))
        return 0
    if args.signer_out is None or args.build_id is not None:
        parser.error('hosted mode needs --signer-out and takes the build from --bindings')
    try:
        packet = read_packet(args.packet.read_bytes())
        result, now, signer_sha256 = assemble_hosted(packet, args.output_dir, json.loads(args.bindings.read_bytes()),
                                                     args.signer_out, usdt_deficit=args.accept_usdt_deficit_units,
                                                     usdt_surplus=args.accept_usdt_surplus_units,
                                                     profile=args.profile,
                                                     allowance_recovery=args.allowance_recovery)
    except (*ERRORS, AssertionError, zlib.error):
        # Never echo hostnames, paths, DSNs, raw input or exception messages.
        print(json.dumps(dict(status='SIGNER_ASSEMBLY_REFUSED', ready_to_install=False,
                              signing_enabled=False, gate_b_accepted=False)))
        return 4
    print(json.dumps(dict(status='ASSEMBLED_REQUIRES_APPROVAL' if signer_sha256 else 'NUMERIC_NOT_COVERED',
                          numeric_status=result['numeric_status'], blockers=result['blockers'],
                          reviewed_at=now, missing=result['missing_quote_coverage'],
                          signer_config_sha256=signer_sha256, ready_to_install=False,
                          signing_enabled=False, gate_b_accepted=False)))
    return 0 if signer_sha256 else 3


if __name__ == '__main__':
    raise SystemExit(main())

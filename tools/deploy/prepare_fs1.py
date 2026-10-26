"""Offline, standalone FS1 FINAL preparation from fresh final-wallet inputs.

No previous run, development wallet, rehearsal signer, database connection or credentials are read.
Outputs are candidates: exact owner approval, release binding and host checks remain required.
Run with `python -m tools.deploy.prepare_fs1 --help` from the reviewed release checkout.
"""
import argparse
import json
from pathlib import Path
import re

from larp.contracts import ContractError
from larp.execution import Blocked
from larp.runtime import gate_a
from larp.marketdata.web3 import utc

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / 'docs/build/evidence/fs1-final-20261025/fs1-final-recovery.json'
PROFILE_SHA = 'b8ba06e248b48b6406d77c1bda4110001324382e91bb63c71a27ce514731892f'
ROUTING = ROOT / 'config/intelligence/aiand-routing.fs1.json'
ROUTING_SHA = '9b86c7327eddca76e0739f6639211f9b609f18c027bc4e61bf83dc804dfcf1f4'
POLICY = ROOT / 'docs/build/evidence/untrusted-router-policy-ld03-20261020.json'
POLICY_SHA = '05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5'


def prepare_final(configs, *, wallet, database_name, capture_raw, calendar_raw, token_history_raw,
                  run_id, build_id, now, adoption_ref, sec_contact=None,
                  balance_rpc_url=None, balance_rpc_source_id=None, balance_rpc_providers=None):
    """Fresh, flat FINAL wallet only. Qualified input semantics and adoption remain owner assertions."""
    if not re.fullmatch(r'larp_final(?:_[a-z0-9_]+)?', database_name or '') or len(database_name) > 63:
        raise ContractError('Use a dedicated larp_final database, never an existing rehearsal database')
    if gate_a.wallet_address(wallet) != json.loads(capture_raw).get('wallet'):
        raise ContractError('Capture differs from the explicitly selected final wallet')
    profile_raw, routing_raw = PROFILE.read_bytes(), ROUTING.read_bytes()
    if gate_a.digest(profile_raw) != PROFILE_SHA or gate_a.digest(routing_raw) != ROUTING_SHA:
        raise ContractError('FS1 profile or routing differs from the reviewed pins')
    if gate_a.digest(POLICY.read_bytes()) != POLICY_SHA:
        raise ContractError('FS1 router policy differs from the reviewed pin')
    configs = json.loads(json.dumps(configs))
    for config in configs.values():
        if 'database_name' in config:
            config['database_name'] = database_name
    # Wallet ownership markers must not reuse the development wallet's directories.
    directory = '/var/lib/larp-runtime/final-' + gate_a.wallet_address(wallet)[2:]
    configs['runtime.json'].update(ai_seeds_dir=directory + '/ai-seeds', nonce_dir=directory + '/nonce')
    return gate_a.prepare(configs, profile_raw=profile_raw, capture_raw=capture_raw, calendar_raw=calendar_raw,
        token_history_raw=token_history_raw, run_id=run_id, build_id=build_id, now=now,
        sec_contact=sec_contact, balance_rpc_url=balance_rpc_url, balance_rpc_source_id=balance_rpc_source_id,
        balance_rpc_providers=balance_rpc_providers, model_routing_raw=routing_raw,
        model_routing_sha256=ROUTING_SHA, execution='service', runtime_mode='live', adoption_ref=adoption_ref,
        untrusted_router_policy_file='/etc/larp/untrusted-router-policy.json',
        untrusted_router_policy_sha256=POLICY_SHA, allowance_recovery=True)


def final_services(files, inputs, *, now, base_dir):
    """Independently review/assemble explicit FINAL caps inputs; never rebind a rehearsal ledger.

    Keep these service files separate until gate_a_check has checked the original prepared directory.
    The caller then binds all services to one release manifest with the existing preflight command.
    """
    from larp.execution_live.gate_b import pinned
    from larp.execution_live.main import BUILD_KEYS
    from larp.signer.assembly import assemble
    runtime, initial = (json.loads(files[n]) for n in ('runtime.json', 'initial-state.json'))
    if inputs.get('environment') != 'FINAL' or runtime['mode'] != 'live':
        raise ContractError('Standalone FS1 assembly requires FINAL/live inputs')
    refs = inputs['files']
    if refs['profile']['sha256'] != gate_a.digest(files['strategy-profile.json']):
        raise ContractError('Caps review must pin the prepared FS1 profile')
    execution = pinned(refs['execution_config'], base_dir)
    if any(execution.get(k) in (None, '') for k in (*BUILD_KEYS, 'runtime_secret_id')):
        raise ContractError('Final caps inputs require a complete execution service configuration')
    holdings = pinned(refs['initial_state'], base_dir)
    if holdings != initial:
        raise ContractError('Caps holdings must equal the fresh FINAL initial state')
    for field in ('run_id', 'build_id', 'mode', 'wallet_address', 'database_host', 'database_name',
                  'database_ca_file', 'database_ca_sha256', 'region'):
        if execution.get(field) != runtime.get(field):
            raise ContractError('Final execution and prepared runtime identities differ')
    if (execution.get('allowance_recovery') is not True
            or (execution.get('untrusted_router_policy_file'), execution.get('untrusted_router_policy_sha256'))
            != (runtime['driver'].get('untrusted_router_policy_file'), POLICY_SHA)):
        raise ContractError('Final execution requires the reviewed recovery and router scope')
    driver = runtime['driver']
    providers = driver.get('balance_rpc_providers') or [dict(url=driver.get('balance_rpc_url'),
        source_id=driver.get('balance_rpc_source_id'))]
    if (execution['strategy_profile_file'] != driver['strategy_profile_file']
            or execution['runtime_secret_id'] != runtime['runtime_secret_id']
            or not any((execution['rpc_url'], execution['rpc_source_id']) == (p['url'], p['source_id'])
                       for p in providers)):
        raise ContractError('Final execution profile, secret or qualified RPC differs from runtime')
    return dict(assemble(inputs, now=now, base_dir=base_dir),
                **{'execution.json': (json.dumps(execution, sort_keys=True, indent=2) + '\n').encode(),
                   'untrusted-router-policy.json': POLICY.read_bytes()})


def main(argv=None):
    # Reuse the renderer and private RPC reader, not a run-specific wrapper or historical config.
    import sys
    sys.path.insert(0, str(ROOT / 'tools/deploy'))
    import prepare_shadow
    import render_host_configs as renderer
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('terraform-output', 'capture', 'token-history-config', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name in ('wallet', 'build-id', 'rds-ca-sha256', 'model-adoption-ref'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--run-id', default='larp-final-fs1')
    parser.add_argument('--database-name', default='larp_final')
    parser.add_argument('--sec-contact')
    parser.add_argument('--balance-rpc-config', type=Path, required=True)
    parser.add_argument('--calendar', type=Path, default=ROOT / 'config/runtime/session-calendar.2026.json')
    parser.add_argument('--caps-inputs', type=Path, help='Fresh FINAL GateBCapsInputs.v1, with exact initial-state pin')
    parser.add_argument('--services-out', type=Path, help='New private directory outside the checkout; with --caps-inputs')
    args = parser.parse_args(argv)
    if (args.caps_inputs is None) != (args.services_out is None):
        parser.error('--caps-inputs and --services-out are required together')
    try:
        now = utc()
        configs = renderer.render(renderer.outputs(json.loads(args.terraform_output.read_bytes())),
                                  args.wallet, args.rds_ca_sha256)
        files = prepare_final(configs, wallet=args.wallet, database_name=args.database_name,
            capture_raw=args.capture.read_bytes(), calendar_raw=args.calendar.read_bytes(),
            token_history_raw=args.token_history_config.read_bytes(), run_id=args.run_id,
            build_id=args.build_id, now=now, adoption_ref=args.model_adoption_ref, sec_contact=args.sec_contact,
            balance_rpc_providers=prepare_shadow.rpc_providers(args.balance_rpc_config))
        services = None if args.caps_inputs is None else final_services(files, json.loads(args.caps_inputs.read_bytes()),
            now=now, base_dir=args.caps_inputs.resolve().parent)
        prepare_shadow.write_new(args.out, files)
        if services is not None:
            from larp.signer.assembly import write_new
            write_new(args.services_out, services)
    except (ContractError, Blocked, OSError, ValueError, TypeError, KeyError, AttributeError, renderer.Refused):
        print(json.dumps(dict(status='FS1_PREPARATION_REFUSED', signing_enabled=False, ready_to_install=False)))
        return 4
    print(json.dumps(dict(status='FS1_PREPARED_REQUIRES_APPROVAL', signing_enabled=False, ready_to_install=False,
                          profile_sha256=PROFILE_SHA, routing_sha256=ROUTING_SHA,
                          services_assembled=services is not None)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

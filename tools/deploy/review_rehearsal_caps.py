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
# SJ-04: the hosted execution role and the exact private binding fields, nothing else.
BINDING_KEYS = {'schema', 'run_id', 'build_id', 'database_host', 'database_name', 'database_ca_file',
                'database_ca_sha256', 'region', 'untrusted_router_policy_file', 'untrusted_router_policy_sha256'}
SHA256 = re.compile(r'[0-9a-f]{64}')


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


def collect(packet, output, build_id, *, bindings=None, now=None):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    private = packet['private_caps_inputs']
    profile_path = ROOT / 'docs/build/evidence/rehearsal-exit-split-20261021/rehearsal-deterministic.json'
    profile = json.loads(profile_path.read_bytes())
    assert hashlib.sha256(profile_path.read_bytes()).hexdigest() == packet['selected_profile_sha256']
    assert packet['holdings']['status'] == 'MATCH' and packet['configs_unchanged']
    assert packet['holdings']['latest_nonce'] == packet['holdings']['pending_nonce']
    assert not packet['in_flight']['reservations'] and not packet['in_flight']['execution_pending']
    assert not any(packet['router']['allowances_to_router'].values())
    decision = json.loads((ROOT / 'docs/build/evidence/signer-numeric-ceilings-20261021.json').read_bytes())
    policy = decision['policies']['development']['signing_policy']
    portfolio = private['portfolio']
    run_id = packet['identity']['run_id']
    if bindings is not None:
        connection = hosted(bindings)
        if bindings['build_id'] != build_id:
            raise ContractError('Hosted bindings name another build')
        # The new signed run has no ledger yet: it starts from these reconciled wallet holdings,
        # checked above (MATCH, nonce, allowances, nothing in flight). The source run stays recorded.
        run_id = bindings['run_id']
        portfolio = dict(portfolio, run_id=run_id)
    config = dict(schema='ExecutionService.v1', run_id=run_id, build_id=build_id,
        mode='dev', wallet_address=private['wallet'], interval_seconds=1, database_dsn_file='/etc/larp/execution-dsn',
        router=policy['allowed_spenders'][0], token_decimals=private['token_decimals'],
        max_gas=decision['execution_ceiling']['max_gas'],
        max_gas_price=decision['execution_ceiling']['max_gas_price_wei'],
        gas_budget=profile['gas_action_budget_units'], allowance_recovery=False,
        strategy_profile_file='/etc/larp/strategy-profile.json',
        strategy_profile_sha256=packet['selected_profile_sha256'])
    if bindings is not None:
        del config['database_dsn_file']
        config.update(connection)
    # Without bindings: proposed numeric execution scope only; actual DB/RPC/CA/run/release
    # configuration is a separate LD16/17 binding. This file is never installed by this tool.
    def pin(name, value):
        raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n'
        with (output / name).open('xb') as stream:
            stream.write(raw)
        (output / name).chmod(0o600)
        return dict(path=name, sha256=hashlib.sha256(raw).hexdigest())
    policy_ref = pin('signing-policy.json', policy)
    assert policy_ref['sha256'] == decision['policies']['development']['sha256_canonical_json_lf']
    profile_ref = pin('profile.json', profile)
    # The canonical JSON encoder above is byte-identical to this profile's file format.
    assert profile_ref['sha256'] == config['strategy_profile_sha256']
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
        pin('portfolio-rebinding.json', dict(source_run_id=packet['identity']['run_id'], run_id=run_id,
            source_portfolio_sha256=Document.from_dict(private['portfolio']).digest('PortfolioState.v1')))
    return inputs, result, now


def assemble_hosted(packet, output, bindings, signer_out, *, now=None):
    """SJ-04: review and assemble on one clock; a refusal writes no candidate and echoes nothing private."""
    from larp.signer.assembly import assemble, write_new
    inputs, result, now = collect(packet, output, bindings['build_id'], bindings=bindings, now=now)
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
    args = parser.parse_args(argv)
    packet = read_packet(args.packet.read_bytes())
    if args.bindings is None:
        if args.build_id is None or args.signer_out is not None:
            parser.error('--build-id is required, and --signer-out needs --bindings')
        _, result, now = collect(packet, args.output_dir, args.build_id)
        print(json.dumps(dict(numeric_status=result['numeric_status'], blockers=result['blockers'],
                             reviewed_at=now, missing=result['missing_quote_coverage'])))
        return 0
    if args.signer_out is None or args.build_id is not None:
        parser.error('hosted mode needs --signer-out and takes the build from --bindings')
    try:
        result, now, signer_sha256 = assemble_hosted(packet, args.output_dir, json.loads(args.bindings.read_bytes()),
                                                     args.signer_out)
    except (*ERRORS, AssertionError):
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

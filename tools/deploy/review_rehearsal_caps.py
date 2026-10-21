"""LD10-Q01: private numeric coverage inputs and report; never assembles signer.json."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from larp.execution_live.caps_review import review

ROOT = Path(__file__).resolve().parents[2]


def collect(packet, output, build_id):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    private = packet['private_caps_inputs']
    profile_path = ROOT / 'docs/build/evidence/rehearsal-qualified-inputs-20261021/rehearsal-live.json'
    profile = json.loads(profile_path.read_bytes())
    assert hashlib.sha256(profile_path.read_bytes()).hexdigest() == packet['selected_profile_sha256']
    assert packet['holdings']['status'] == 'MATCH' and packet['configs_unchanged']
    assert packet['holdings']['latest_nonce'] == packet['holdings']['pending_nonce']
    assert not packet['in_flight']['reservations'] and not packet['in_flight']['execution_pending']
    assert not any(packet['router']['allowances_to_router'].values())
    decision = json.loads((ROOT / 'docs/build/evidence/signer-numeric-ceilings-20261021.json').read_bytes())
    policy = decision['policies']['development']['signing_policy']
    config = dict(schema='ExecutionService.v1', run_id=packet['identity']['run_id'], build_id=build_id,
        mode='dev', wallet_address=private['wallet'], interval_seconds=1, database_dsn_file='/etc/larp/execution-dsn',
        router=policy['allowed_spenders'][0], token_decimals=private['token_decimals'],
        max_gas=decision['execution_ceiling']['max_gas'],
        max_gas_price=decision['execution_ceiling']['max_gas_price_wei'],
        gas_budget=profile['gas_action_budget_units'], allowance_recovery=False,
        strategy_profile_file='/etc/larp/strategy-profile.json',
        strategy_profile_sha256=packet['selected_profile_sha256'])
    # Proposed numeric execution scope only; actual DB/RPC/CA/run/release configuration
    # is a separate LD16/17 binding. This file is never installed by this tool.
    def pin(name, value):
        raw = (json.dumps(value, sort_keys=True, indent=2).encode() if name == 'signing-policy.json'
               else json.dumps(value, sort_keys=True, separators=(',', ':')).encode()) + b'\n'
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
            execution_config=pin('execution-numeric-scope.json', config),
            initial_state=pin('current-holdings.json', private['portfolio'])),
        quote_artifacts=[pin('quote-%02d.json' % n, r) for n, r in enumerate(private['quote_artifacts'])])
    now = datetime.now(timezone.utc).isoformat()
    result = review(inputs, now=now, base_dir=output)
    pin('inputs.json', inputs)
    pin('review.json', result)
    return inputs, result, now


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--build-id', required=True)
    args = parser.parse_args()
    _, result, now = collect(json.loads(args.packet.read_bytes()), args.output_dir, args.build_id)
    print(json.dumps(dict(numeric_status=result['numeric_status'], blockers=result['blockers'],
                         reviewed_at=now, missing=result['missing_quote_coverage'])))


if __name__ == '__main__':
    main()

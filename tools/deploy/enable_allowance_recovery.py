"""IDEA-096 AL7: produce a recovery candidate from reviewed inputs. No install, approval or network calls."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from larp.contracts import ContractError, Document
from larp.execution_live.main import validate_config
from larp.marketdata.port import TOKENS
from larp.risk.planner import exit_parts
from larp.signer.policy import SigningPolicy
from larp.strategy.profiles import validate_live
from larp.strategy.schema import ceil, fraction, initial_gas_only


def candidate(profile, execution, signing_policy, runtime, *, decision_id):
    p, e, s, r = map(deepcopy, (profile, execution, signing_policy, runtime))
    validate_live(p)
    validate_config(e)
    SigningPolicy.from_config(s)
    if not initial_gas_only(p) or not decision_id.strip():
        raise ContractError('Recovery candidate needs initial-only gas scope and a review reference')
    if (e.get('untrusted_router_policy_file') is None or
            e.get('untrusted_router_policy_sha256') is None):
        raise ContractError('Recovery needs the pinned untrusted router policy')
    driver = r['driver']
    for field in ('untrusted_router_policy_file', 'untrusted_router_policy_sha256'):
        if driver.get(field) != e[field]:
            raise ContractError('Runtime and execution must pin the same router policy')
    if (r['run_id'] != e['run_id'] or r['build_id'] != e['build_id']
            or r['wallet_address'] != e['wallet_address'] or r['mode'] != e['mode']):
        raise ContractError('Runtime and execution identities differ')
    evidence = hashlib.sha256(Document.from_dict(dict(profile=p, execution=e, policy=s)).payload).hexdigest()
    action = 8 * e['max_gas'] * e['max_gas_price']
    # Clean-pair sizing stays measured. The verifier adds the observed cleanup count at expected price;
    # charging every clean entry for five hypothetical revokes can make the smallest position infeasible.
    sizing = p.get('gas_sizing_budget_units', p['gas_action_budget_units'])
    if sizing > action:
        raise ContractError('Measured recovery sizing exceeds the eight-child signed envelope')
    if p['baseline'] == 'TREND_GUARDED_VOL':
        from larp.strategy.s1 import config
        positions, hard = len(TOKENS), config(p)['hard']
    else:
        positions, hard = 4, fraction(p['hard_name_weight'])
    children = exit_parts(ceil(hard * p['expected_equity_units']), p['per_trade_cap_units'])
    p.update(gas_action_budget_units=action, gas_sizing_budget_units=sizing,
             exit_gas_reserve_units=positions * children * action)
    for name, formula in dict(
            gas_action_budget_units='8 children*max_gas*max_gas_price; <=5 other-token revokes + approve + swap '
                                    'or abort pay-token revoke; original authority only',
            gas_sizing_budget_units='clean-pair expected gas; verifier adds observed other-token revokes '
                                   '*ceil(max measured approve gas*5/4); action reserves signed maxima',
            exit_gas_reserve_units=f'{positions} positions*{children} balanced exit children*gas_action_budget_units').items():
        p['provenance'][name] = dict(decision_id=decision_id, data_hash=evidence, formula=formula)
    raw = Document.from_dict(p).payload + b'\n'
    sha = hashlib.sha256(raw).hexdigest()
    e.update(allowance_recovery=True, gas_budget=action, strategy_profile_sha256=sha)
    s['allowance_recovery'] = True
    driver.update(allowance_recovery=True, strategy_profile_sha256=sha)
    validate_live(p)
    validate_config(e)
    SigningPolicy.from_config(s)
    return {'profile.json': raw, 'execution-config.json': Document.from_dict(e).payload + b'\n',
            'signing-policy.json': Document.from_dict(s).payload + b'\n',
            'runtime.json': Document.from_dict(r).payload + b'\n',
            'allowance-recovery-review.json': Document.from_dict(dict(
                schema='AllowanceRecoveryCandidate.v1', decision_id=decision_id, ready_to_install=False,
                signing_enabled=False, gas_action_budget_units=action, gas_sizing_budget_units=sizing,
                exit_gas_reserve_units=p['exit_gas_reserve_units'], profile_sha256=sha,
                remaining_gates=['FRESH_CAPS_REVIEW', 'GATE_A_CHECK', 'ISAAC_SIGNER_APPROVAL',
                                 'KEEGAN_GAS_TIMING_ACCEPTANCE', 'AL9_LIVE_HOST_ACCEPTANCE'])).payload + b'\n'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('profile', 'execution-config', 'signing-policy', 'runtime'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--decision-id', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    files = candidate(*(json.loads(p.read_bytes()) for p in
                        (args.profile, args.execution_config, args.signing_policy, args.runtime)),
                      decision_id=args.decision_id)
    args.output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name, raw in files.items():
        path = args.output_dir / name
        with path.open('xb') as stream:
            stream.write(raw)
        path.chmod(0o600)


if __name__ == '__main__':
    main()

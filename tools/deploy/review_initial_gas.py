"""GC01 offline bounded gas candidates. No credentials, network, funding or installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from larp.contracts import ContractError, Document
from larp.execution import REVOKE_TOKENS
from larp.strategy.profiles import build_live_profiles, validate_live

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/build/evidence'


def positive(value):
    if type(value) is not int or not 0 < value < 2**256:
        raise ContractError('Positive uint256 integer required')
    return value


def envelope(max_gas, max_price, fee_cap, *, cleanup):
    if type(cleanup) is not bool:
        raise ContractError('Explicit cleanup scope required')
    child = positive(max_gas) * positive(max_price)
    if child > positive(fee_cap):
        raise ContractError('Execution ceiling exceeds independent signer fee cap')
    children = 2 + (len(REVOKE_TOKENS) if cleanup else 0)
    return positive(children * child)


def seeding(nonterminal_actions, action_budget, exit_actions, margin_numerator, margin_denominator):
    if type(nonterminal_actions) is not int or nonterminal_actions < 0:
        raise ContractError('Non-terminal action count required')
    for value in (action_budget, exit_actions, margin_numerator, margin_denominator):
        positive(value)
    if margin_numerator < margin_denominator:
        raise ContractError('Seeding margin cannot reduce the action count')
    # N excludes terminal exits; exits are reserved exactly once, outside the margin.
    return positive(-(-(nonterminal_actions * action_budget * margin_numerator) // margin_denominator)
                    + exit_actions * action_budget)


def build():
    decision_path = EVIDENCE / 'signer-numeric-ceilings-20261021.json'
    decision_raw = decision_path.read_bytes()
    decision = json.loads(decision_raw)
    c = decision['execution_ceiling']
    assert all(not row['signing_policy']['allowance_recovery'] for row in decision['policies'].values())
    caps = [int(row['signing_policy']['max_fee_wei']) for row in decision['policies'].values()]
    action = envelope(c['max_gas'], c['max_gas_price_wei'], min(caps), cleanup=False)
    cleanup_action = envelope(c['max_gas'], c['max_gas_price_wei'], min(caps), cleanup=True)
    def doc(path):
        return Document.from_dict(json.loads(path.read_bytes()))
    authority_path = EVIDENCE / 'ld02-execution-packet-20261020.json'
    authority = dict(seconds=660, margin=30, decision_id='IDEA-049-C LD04-V01 (Keegan, 2026-10-20)',
                     data_hash=hashlib.sha256(authority_path.read_bytes()).hexdigest())
    budget = dict(action_units=action, sizing_units=80004560000000,
                  decision_id='IDEA-061 LD08-GC01: bounded candidate, adoption pending',
                  data_hash=hashlib.sha256(decision_raw).hexdigest())
    profiles = build_live_profiles(doc(EVIDENCE / 'quotes-complete-20261020/quote-cost-summary.json'),
                                  doc(ROOT / 'config/intelligence/red_flags.v1.json'),
                                  initial_gas_only=True, authority=authority, gas_budget=budget)
    files, rows = {}, {}
    for env, document in profiles.items():
        p = document.read()
        validate_live(p)
        assert p['gas_action_budget_units'] == action
        assert p['exit_gas_reserve_units'] == 4 * action
        raw = document.payload + b'\n'
        filename = env.lower() + '-live.json'
        files[filename] = raw
        rows[env] = dict(file_sha256=hashlib.sha256(raw).hexdigest(),
                         document_sha256=document.digest('StrategyProfile.v1'),
                         gas_action_budget_units=action, exit_gas_reserve_units=p['exit_gas_reserve_units'],
                         gas_sizing_budget_units=p['gas_sizing_budget_units'],
                         minimum_trade_units=p['minimum_trade_units'], baseline=p['baseline'])
    report = dict(schema='InitialGasBoundedCandidateReview.v1', decision_id='IDEA-061 LD08-GC01',
                  status='OFFLINE_BOUND_CANDIDATES_NOT_DEPLOYMENT_ACCEPTANCE',
                  policy_evidence_sha256=hashlib.sha256(decision_raw).hexdigest(),
                  execution_ceilings=c, normal_children=2, normal_action_wei=action,
                  cleanup_children=2 + len(REVOKE_TOKENS), cleanup_action_wei=cleanup_action,
                  cleanup_enabled=False, cleanup_policy_approved=False,
                  ew_exit_reserve_wei=4 * action, s1_five_exit_bound_wei=5 * action,
                  rounded_observed_20_percent_pair_wei=((55243 * 6 + 4) // 5
                                                        + (944814 * 6 + 4) // 5) * c['max_gas_price_wei'],
                  rounded_observed_25_percent_pair_wei=((55243 * 5 + 3) // 4
                                                        + (944814 * 5 + 3) // 4) * c['max_gas_price_wei'],
                  seeding_count_definition='N excludes terminal exits; margin applies to N; exit reserve added once',
                  seeding_sensitivity_not_approved={str(n): seeding(n, action, 4, 5, 4)
                                                   for n in (0, 5, 10, 15, 30)},
                  profiles=rows, ready_to_install=False, signing_enabled=False,
                  remaining=['Keith selected-profile/whole-run count and fee acceptance',
                             'current execution gas_budget <= funded action budget; actual per-action reservations',
                             'fresh full holdings and one-exit-per-position cap coverage',
                             'cleanup disabled unless separately approved and covered',
                             'final PF-04 calendar; actual qualified release/config/alarm/host acceptance'])
    files['review.json'] = (json.dumps(report, sort_keys=True, indent=2) + '\n').encode()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    target = args.out.absolute()
    if ROOT == target.resolve() or ROOT in target.resolve().parents:
        parser.error('Output must be outside the checkout')
    files = build()
    target.mkdir(mode=0o700)  # existing output/symlinks refuse; no overwrite
    for name, raw in files.items():
        fd = os.open(target / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
    print(json.dumps(dict(status='CANDIDATES_WRITTEN', ready_to_install=False, signing_enabled=False)))


if __name__ == '__main__':
    main()

"""LD10-P01: reproduce public candidates; no current-wallet coverage is inferred.

From the repository root: PYTHONPATH=. python3 <this file>
Only committed public files are read. JSON goes to stdout; no ports or keys are used.
The actual private packet must separately use larp.execution_live.caps_review.
"""
import hashlib
import json
from pathlib import Path

from larp.contracts import Document
from larp.execution import USDT
from larp.signer.policy import SigningPolicy
from larp.strategy.profiles import build_live_profiles, validate_live

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / 'docs/build/evidence'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def verify():
    summary_path = EVIDENCE / 'quotes-complete-20261020/quote-cost-summary.json'
    registry_path = ROOT / 'config/intelligence/red_flags.v1.json'
    authority_path = EVIDENCE / 'ld02-execution-packet-20261020.json'
    gas_path = EVIDENCE / 'ld02d-size-sell-20261021.json'
    decision_path = EVIDENCE / 'signer-numeric-ceilings-20261021.json'
    selected_policy_path = ROOT / 'docs/ledger/IDEA-084.md'
    report_path = EVIDENCE / 'quotes-complete-20261020/quote-cost-summary.report.json'
    decision = load(decision_path)
    for name, digest in decision['evidence'].items():
        assert sha((EVIDENCE / name).read_bytes()) == digest, name
    generated = build_live_profiles(
        Document.from_dict(load(summary_path)), Document.from_dict(load(registry_path)),
        initial_gas_only=True,
        authority=dict(seconds=660, margin=30,
                       decision_id='IDEA-049-C LD04-V01 (Keegan, 2026-10-20)',
                       data_hash=sha(authority_path.read_bytes())),
        gas_budget=dict(action_units=200011400000000, sizing_units=80004560000000,
                        decision_id='IDEA-061 LD09-B (Keegan, 2026-10-21)',
                        data_hash=sha(gas_path.read_bytes())))
    expected_hashes = {
        'REHEARSAL': ('d76b640866250a2963618d093eadc8fb0b48e26cfca8f98151d693d3e392740f',
                      'df58529756c715282c567e39b013163cd1428d347c5d5bef196a273b152f5d6e'),
        'FINAL': ('0497a820821524cbcbd5234c937aa211b8b94da9409b6b8e787f49b33cde5f40',
                  '07e8e8c90b06440993052a0ce67ce6f24b103edac4dc7b168ba457a75267a542')}
    final_windows = dict(trade_after='2026-10-29T14:00:00Z', new_risk_end='2026-11-09T21:00:00Z',
                         flatten_start='2026-11-10T19:00:00Z', signing_end='2026-11-11T14:45:00Z')
    policy_text = selected_policy_path.read_text()
    for row in ('| First final buy eligibility | Oct 29 14:00 |',
                '| New risk ends | Nov 9 21:00 |', '| Flatten starts | Nov 10 19:00 |'):
        assert row in policy_text, 'Selected PF-04 calendar changed; review required'
    profiles = {}
    for env, document in generated.items():
        path = EVIDENCE / 'rv120-profiles-20261021' / (env.lower() + '-live.json')
        raw = path.read_bytes()
        assert raw == document.payload + b'\n', 'Candidate reproduction: ' + env
        assert (sha(raw), document.digest('StrategyProfile.v1')) == expected_hashes[env]
        p = document.read()
        validate_live(p)
        mode = 'development' if env == 'REHEARSAL' else 'final'
        policy_raw = decision['policies'][mode]['signing_policy']
        policy_bytes = (json.dumps(policy_raw, sort_keys=True, separators=(',', ':')) + '\n').encode()
        assert sha(policy_bytes) == decision['policies'][mode]['sha256_canonical_json_lf']
        policy = SigningPolicy.from_config(policy_raw)
        cash = p['per_trade_cap_units'] * 10**12
        ceiling = decision['execution_ceiling']
        fee = ceiling['max_gas'] * ceiling['max_gas_price_wei']
        assert cash <= policy.max_input_units[USDT]
        assert fee <= policy.max_fee_wei
        assert p['initial_gas_only'] is True and policy.allowance_recovery is False
        windows = {key: p[key] for key in final_windows}
        profiles[env] = dict(
            file_sha256=sha(raw), document_sha256=document.digest('StrategyProfile.v1'),
            reproduced=True, production_live_validation='PASS', baseline=p['baseline'],
            policy_sha256=sha(policy_bytes), cash_required_raw=str(cash),
            cash_cap_raw=str(policy.max_input_units[USDT]), cash_covered=True,
            configured_fee_ceiling_wei=str(fee), independent_fee_cap_wei=str(policy.max_fee_wei),
            fee_ceiling_covered=True, windows=windows,
            final_pf04_mismatches=({k: dict(candidate=v, selected=final_windows[k])
                                    for k, v in windows.items() if v != final_windows[k]}
                                   if env == 'FINAL' else {}),
            deployment_accepted=False)
    report = load(report_path)
    assert report['parameters']['fee_netting_status'] == 'UNVERIFIED'
    source_paths = [summary_path, registry_path, authority_path, gas_path,
                    decision_path, selected_policy_path, report_path]
    return dict(
        schema='LD10ProfileCoverageInventory.v1', decision_id='IDEA-049-C LD10-P01',
        canonical_base='f10d9ad', status='BLOCKED_MISSING_ACTUAL_INPUTS',
        offline_candidate_checks='PASS', actual_caps_review='NOT_RUN_MISSING_INPUTS',
        profiles=profiles,
        historical_public_report=dict(coverage=report['coverage'],
                                      fee_netting_status='UNVERIFIED',
                                      raw_capture_independently_replayed=False),
        missing_actual_packet=['selected profile and Keith/Isaac #120 confirmation',
                               'current complete reconciled PortfolioState.v1 and metadata',
                               'intended execution.json with exact run/build/environment/CA bindings',
                               'fresh original request-bound BUY/SELL artifacts for all five names',
                               'reviewed freshness budget and four-file GateBCapsInputs.v1 manifest'],
        separate_remaining_gates=['signed-child/cleanup/full-exit/whole-run gas coverage (priority 2)',
                                  'fresh router replay/live preflight (priority 3)',
                                  'qualified release and private signer assembly (priority 4)',
                                  'fee netting #119; receipt confirmation at LD19/LD20'],
        ready_to_install=False, signing_enabled=False, gate_b_accepted=False,
        source_hashes={str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in source_paths})


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True, indent=2) + '\n', end='')

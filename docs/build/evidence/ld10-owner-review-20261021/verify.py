"""P02: verify published Q01 arithmetic and runtime compatibility, no ports/private originals.

Run from repository root with PYTHONPATH=.; JSON output is a dated public review,
not GateBCapsInputs.v1, a fresh caps run, owner installation approval or signer config.
"""
import hashlib
import json
from pathlib import Path

from larp.contracts import Document
from larp.execution import USDT
from larp.execution_live.untrusted_router import load_policy
from larp.integration.contract import authority
from larp.marketdata.port import TOKENS
from larp.signer.policy import SigningPolicy
from larp.strategy.profiles import validate_live
from larp.strategy.schema import execution_authority
from tools.deploy.build_rehearsal_candidate import build

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = ROOT / 'docs/build/evidence'
PACKET = EVIDENCE / 'rehearsal-qualified-inputs-20261021'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    rc_path = EVIDENCE / 'ab-rel-rc2-20261021.json'
    rc = read(rc_path)
    for name, digest in rc['selected_inputs'].items():
        assert sha(PACKET / name) == digest, name
    profile_path = PACKET / 'rehearsal-deterministic.json'
    coverage_path = PACKET / 'coverage-decision-deterministic.json'
    scope_path = PACKET / 'rehearsal-deterministic-scope.json'
    p, c, scope = read(profile_path), read(coverage_path), read(scope_path)
    document = build()
    assert document.payload + b'\n' == profile_path.read_bytes()
    validate_live(p)
    assert document.digest('StrategyProfile.v1') == c['profile_document_sha256'] == rc['profile_document_sha256']
    assert sha(profile_path) == c['profile_file_sha256'] == scope['profile_file_sha256']
    assert authority(p)['falsifier'] == p['evidence_mode'] == scope['effective_falsifier_authority'] == 'SHADOW'
    assert scope['driver_overrides']['assessor'] == 'deterministic' and not scope['hosted_model_calls']
    assert p['environment'] == scope['environment'] == 'REHEARSAL'
    assert execution_authority(p) == (660, 30)
    caps_path = EVIDENCE / 'signer-numeric-ceilings-20261021.json'
    caps = read(caps_path)
    pv = caps['policies']['development']['signing_policy']
    policy = SigningPolicy.from_config(pv)
    policy_sha = hashlib.sha256((json.dumps(pv, sort_keys=True, separators=(',', ':')) + '\n').encode()).hexdigest()
    assert policy_sha == c['signer_policy_sha256'] == rc['signing_policy_sha256']
    assert not policy.allowance_recovery and not c['cleanup_enabled'] and p['initial_gas_only']
    assert policy.allowed_tokens == {USDT, *TOKENS.values()}
    router_path = EVIDENCE / 'untrusted-router-policy-ld03-20261020.json'
    router = load_policy(router_path, rc['router_policy_sha256'])
    assert policy.allowed_spenders == {router.router}
    assert c['policy_check']['status'] == 'PASS' and c['policy_check']['quotes'] == 15
    assert c['policy_check']['policy_sha256'] == rc['router_policy_sha256']
    assert all(r['status'] == 'PASS' and r['matches_quote'] and r['tampered_refused']
               for r in c['policy_check']['rows'])
    holdings = c['holdings']
    assert holdings['status'] == 'MATCH' and holdings['latest_nonce'] == holdings['pending_nonce']
    assert set(holdings['assets']) == {*TOKENS, 'BNB', 'USDT'}
    assert all(r['cls'] == 'MATCH' and r['chain'] == r['ledger'] for r in holdings['assets'].values())
    assert not c['in_flight']['reservations'] and not c['in_flight']['execution_pending']
    assert not any(c['in_flight']['commands'].values()) and not any(c['allowances_to_router'].values())
    assert c['token_decimals'] == {symbol: 18 for symbol in TOKENS}
    fee = c['max_signed_child_gas'] * c['max_gas_price_wei']
    action = 2 * fee
    assert action == p['gas_action_budget_units'] == c['aggregate_pair_budget_wei']
    assert p['exit_gas_reserve_units'] == c['exit_reserve_wei'] == 4 * action
    assert holdings['native_wei'] >= p['exit_gas_reserve_units']
    assert (c['planned_pairs'] + 4) * action == c['conservative_seed_target_wei']
    assert c['conservative_seed_target_wei'] - holdings['native_wei'] == c['additional_bnb_wei']
    assert p['gas_sizing_budget_units'] == c['sizing_budget_wei'] == 1_250_072 * 64_000_000
    published = {r['check']: r for r in c['numeric_checks']}
    assert len(published) == len(c['numeric_checks']) == 50
    expected = {
        'FULL_POSITION_USDT': (p['per_trade_cap_units'] * 10**12, policy.max_input_units[USDT]),
        'INITIAL_BNB_EXIT_RESERVE': (p['exit_gas_reserve_units'], holdings['native_wei']),
        'CONFIGURED_FEE_ENVELOPE_WEI': (fee, policy.max_fee_wei),
        'INITIAL_SIGNED_CHILD_GAS_ENVELOPE': (action, c['aggregate_pair_budget_wei']),
        'INITIAL_PROFILE_ACTION_BUDGET': (c['aggregate_pair_budget_wei'], p['gas_action_budget_units'])}
    for symbol, token in TOKENS.items():
        expected['FULL_HOLDING_' + symbol] = (holdings['assets'][symbol]['ledger'], policy.max_input_units[token])
        for step in ('APPROVE', 'SWAP'):
            value = p['quote_cost_summary']['symbols'][symbol][step.lower() + '_gas_bnb_units']
            expected['MEASURED_' + step + '_FEE_' + symbol] = (value, policy.max_fee_wei)
    rows, hashes = c['quote_rows'], c['quote_artifact_hashes']
    assert len(rows) == len(hashes) == len(set(hashes)) == 15
    compatibility = []
    for symbol, token in TOKENS.items():
        selected = [r for r in rows if r['symbol'] == symbol]
        buys = [r for r in selected if r['side'] == 'BUY']
        sells = [r for r in selected if r['side'] == 'SELL']
        assert len(buys) == 2 and len(sells) == 1
        assert sorted(r['pay_units'] for r in buys) == [p['minimum_trade_units'], p['per_trade_cap_units']]
        assert sells[0]['pay_units'] == max(buys, key=lambda r: r['pay_units'])['receive_units']
    for row, digest in zip(rows, hashes):
        assert row['status'] == 'OK' and all(row[k] for k in ('request_bound', 'router_pinned', 'selector_pinned', 'native_value_zero'))
        assert row['vendor'] == 'LiquidMesh'
        assert 0 < row['minimum_receive'] <= row['receive_units']
        assert row['minimum_receive'] >= row['receive_units'] * (10000 - p['slippage_bps']) // 10000
        amount = row['pay_units'] * (10**12 if row['side'] == 'BUY' else 1)
        pay = USDT if row['side'] == 'BUY' else TOKENS[row['symbol']]
        expected['QUOTE_INPUT_' + digest] = (amount, policy.max_input_units[pay])
        # Public packet omits upstream gasPrice; verify the reported fee ceiling
        # and integrality, without claiming an independent raw-response replay.
        reported_fee = int(published['QUOTE_FEE_' + digest]['required'])
        assert reported_fee % row['quoted_gas'] == 0
        assert reported_fee // row['quoted_gas'] <= c['max_gas_price_wei']
        expected['QUOTE_FEE_' + digest] = (reported_fee, policy.max_fee_wei)
        cash = amount if row['side'] == 'BUY' else row['receive_units']
        cap = p['per_trade_cap_units'] * 10**12
        compatibility.append(dict(symbol=row['symbol'], side=row['side'], quote_projection_sha256=digest,
                                  cash_raw=str(cash), execution_cash_cap_raw=str(cap), covered=cash <= cap))
    assert set(published) == set(expected)
    for name, (required, cap) in expected.items():
        old = published[name]
        assert (int(old['required']), int(old['cap']), old['covered']) == (required, cap, required <= cap), name
    failures = [r for r in compatibility if not r['covered']]
    return dict(schema='LD10OwnerPacketReview.v1', decision_id='IDEA-049-C LD10-P02',
                status='BLOCKED_EXECUTION_CASH_CAP' if failures else 'RECORDED_SCOPE_REVIEW_PASS',
                selected_profile_reproduced=True, scope_and_hash_checks='PASS',
                recorded_numeric_rows_consistent=len(expected),
                execution_cash_checks=compatibility, execution_cash_failures=failures,
                private_originals_replayed=False, new_current_clock_caps_review_run=False,
                recorded_snapshot_at=c['observed_at'], canonical_release_source=rc['source_commit'],
                numeric_scope_build=c['numeric_scope_build_id'], actual_config_binding_accepted=False,
                full_exit_reserve_accepted=False, full_ld10_owner_acceptance=False,
                signing_enabled=False, ready_to_install=False,
                seeding_target_funded=False, seed_target_wei=c['conservative_seed_target_wei'],
                seeding_scope='reported planning count plus four exits; not a proven maximum strategy count',
                source_hashes={str(x.relative_to(ROOT)): sha(x) for x in
                    (profile_path, coverage_path, scope_path, caps_path, router_path, rc_path)},
                remaining=['Keith/Keegan resolve full-size exit cash-cap/requote and complete exit-child reserve coverage',
                           'operator recollect applicable quotes/state against the reviewed exit plan',
                           'Isaac finish deployment review against corrected evidence',
                           'LD16 actual release/run/DB/RPC/CA/config/reservation binding',
                           'funding disposition, LD17 host/session and later #119 receipt verification'])


if __name__ == '__main__':
    print(json.dumps(verify(), sort_keys=True, indent=2))

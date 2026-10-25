"""IDEA-097 S4-1..S4-6: a REHEARSAL-only flatten test that starts run 5 from run 4's carried-over book, with allowance
recovery gas (IDEA-096 AL-IMPL01). Synthetic ports; no keys or network."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from larp.contracts import ContractError, Document
from larp.marketdata.port import TOKENS
from larp.runtime import gate_a, gate_a_check
from larp.strategy import carry_over
from larp.strategy.profiles import validate_live
from tests.strategy import test_s1_rehearsal as rh
from tests.strategy.test_execution_bounds import at, run
from tests.strategy.test_s1_plan import AT_95
from tests.strategy.test_s2_weekend import AFTER_CLOSE, BLOCK, POLICY, PROFILE as S2_PROFILE, S2, build_runtime, \
    s2_shadow

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/build/evidence/s4-rehearsal-profile-20261025'
PROFILE = EVIDENCE / 'rehearsal-s4-deterministic.json'
DECIDED = {'trade_after', 'new_risk_end', 'flatten_start', 'signing_end', 'policy_id', 'holdings_carry_over',
           'gas_action_budget_units', 'exit_gas_reserve_units'}
# Run 4's book at 2026-10-25T10:17Z (IDEA-096 evidence); cost bases are synthetic round numbers near what it paid.
HELD = dict(GOOGLB=58963981213780645, NVDAB=89437333956570829, SKHYB=137879758388310745, TSLAB=50963873012289550)
COST = dict(GOOGLB=18_917_895, NVDAB=18_924_816, SKHYB=18_951_721, TSLAB=18_931_246)


def s4_shadow():
    p = s2_shadow()
    p['holdings_carry_over'] = carry_over.VALUE
    p['provenance'] = dict(p['provenance'], holdings_carry_over=dict(decision_id='synthetic', formula='synthetic'))
    return p


def export(**changes):
    positions = {s: dict(units=HELD.get(s, 0), decimals=18, cost_basis_units=COST.get(s, 0)) for s in sorted(TOKENS)}
    value = dict(schema=gate_a.CARRY_OVER_SCHEMA, source_run_id='larp-dev-rehearsal-20261024-s2',
                 wallet_id='0x' + '1' * 40, source_version=203, projection_sha256='e' * 64, reservations={},
                 positions=positions, exported_at='2026-10-19T11:59:00Z')
    value.update(changes)
    return value


def held_capture(held=HELD):
    from tests.runtime.test_gate_a import Node, captured, rehash, WALLET, NOW
    c = captured()
    c['balances']['response']['data'][0]['tokenAssets'] += [
        dict(tokenContractAddress=TOKENS[s], rawBalance=str(u)) for s, u in held.items()]
    rehash(c)
    c['chain'] = gate_a.chain_capture(Node(tokens={TOKENS[s]: u for s, u in held.items()}), WALLET, observed_at=NOW)
    return c


def refusal(call):
    with pytest.raises(ContractError) as info:
        call()
    return str(info.value)


# --- S4-1: the committed S4 profile ----------------------------------------------------------------------------------

def test_s4_1_profile_rebuilds_and_differs_from_s2_only_where_decided():
    from tools.deploy.build_rehearsal_candidate import S4_POLICY_ID, S4_WINDOW, build
    raw = PROFILE.read_bytes()
    p, s2 = json.loads(raw), json.loads(S2_PROFILE.read_bytes())
    rebuilt = build(2, s1_raw=BLOCK.read_bytes(), s1_decision=s2['provenance']['s1']['decision_id'], carry_over=True)
    assert rebuilt.payload + b'\n' == raw
    validate_live(p)
    assert {k for k in set(p) | set(s2) if p.get(k) != s2.get(k)} == DECIDED | {'provenance'}
    assert {k for k in set(p['provenance']) | set(s2['provenance'])
            if p['provenance'].get(k) != s2['provenance'].get(k)} == DECIDED
    assert (p['policy_id'], p['holdings_carry_over']) == (S4_POLICY_ID, 'RUN_EXPORT')
    assert {k: p[k] for k in S4_WINDOW} == S4_WINDOW
    # No BUY window after install: new risk ends when the flatten starts, both before run 5 can be installed.
    assert p['new_risk_end'] == p['flatten_start'] < '2026-10-25T11:00:00Z' < p['signing_end'] < '2026-10-29'
    assert 's1' in p and p['s1'] == json.loads(BLOCK.read_bytes()) and 'scheduled_flatten_at' not in p
    readme = (EVIDENCE / 'README.md').read_text()
    assert hashlib.sha256(raw).hexdigest() in readme
    assert Document.from_dict(p).digest('StrategyProfile.v1') in readme


def test_s4_1_recovery_gas_equals_the_pr282_candidate_formula():
    from tools.deploy.build_rehearsal_candidate import RECOVERY_CHILDREN, RECOVERY_MAX_GAS, RECOVERY_MAX_GAS_PRICE
    p = json.loads(PROFILE.read_bytes())
    action = RECOVERY_CHILDREN * RECOVERY_MAX_GAS * RECOVERY_MAX_GAS_PRICE
    assert (p['gas_action_budget_units'], p['exit_gas_reserve_units']) == (action, 5 * 2 * action)
    assert p['gas_sizing_budget_units'] == json.loads(S2_PROFILE.read_bytes())['gas_sizing_budget_units']
    # The same envelope tools/deploy/enable_allowance_recovery.py computes from the execution config's maxima.
    assert action == 1_536_000_000_000_000 and p['exit_gas_reserve_units'] == 15_360_000_000_000_000


def test_s4_1_builder_refuses_s4_without_s2_hours_with_s3_or_one_child():
    from tools.deploy.build_rehearsal_candidate import build
    decision = 'synthetic'
    with pytest.raises(ContractError):
        build(2, carry_over=True)
    with pytest.raises(ContractError):
        build(1, s1_raw=BLOCK.read_bytes(), s1_decision=decision, carry_over=True)
    with pytest.raises(ContractError):
        build(2, s1_raw=BLOCK.read_bytes(), s1_decision=decision, carry_over=True,
              scheduled_flatten_at='2026-10-25T04:00:00Z')


# --- S4-2: profile scope -------------------------------------------------------------------------------------------

def test_s4_2_carry_over_only_in_an_s2_rehearsal_without_s3():
    validate_live(s4_shadow())
    validate_live(s2_shadow())  # unchanged without the key
    assert rh.refusal(lambda: validate_live(dict(s4_shadow(), holdings_carry_over='YES'))) \
        == 'holdings_carry_over must be "RUN_EXPORT"'
    no_hours = rh.shadow(execution=dict(open_delay_seconds=1800, close_buffer_seconds=900,
                                        max_attempts_per_leg_session=5))
    no_hours['holdings_carry_over'] = carry_over.VALUE
    no_hours['provenance'] = dict(no_hours['provenance'], holdings_carry_over=dict(decision_id='s', formula='s'))
    assert rh.refusal(lambda: validate_live(no_hours)) == carry_over.SCOPE
    s3 = s4_shadow()
    s3['scheduled_flatten_at'] = '2026-10-24T12:00:00Z'
    s3['provenance']['scheduled_flatten_at'] = dict(decision_id='s', formula='s')
    with pytest.raises(ContractError):
        validate_live(s3)
    with pytest.raises(ContractError):
        validate_live(dict(s4_shadow(), environment='FINAL'))


# --- S4-3 / S4-4: initial_state with a carried-over book -----------------------------------------------------------

def test_s4_3_initial_state_takes_chain_units_and_exported_cost():
    p = s4_shadow()
    state = gate_a.initial_state(held_capture(), p, 'larp-dev-rehearsal-20261025-s4', carry_over=export())
    assert {s: pos['units'] for s, pos in state['positions'].items()} == dict.fromkeys(TOKENS, 0) | HELD
    assert {s: pos['cost_basis_units'] for s, pos in state['positions'].items()} == dict.fromkeys(TOKENS, 0) | COST
    bnb_value = 10**15 * p['quote_cost_summary']['bnb_price_units'] // 10**18
    assert state['opening_equity_units'] == 100_000_000 + bnb_value + sum(COST.values())
    assert state['risk']['day_anchor_units'] == state['risk']['peak_units'] == state['opening_equity_units']
    assert state['reservations'] == {}


def test_s4_4_initial_state_refuses_every_mismatch():
    p, run_id, capture = s4_shadow(), 'larp-dev-rehearsal-20261025-s4', held_capture()
    exact = 'A holdings carry-over export is required exactly when the profile declares one'
    assert refusal(lambda: gate_a.initial_state(capture, p, run_id)) == exact
    assert refusal(lambda: gate_a.initial_state(capture, s2_shadow(), run_id, carry_over=export())) == exact
    # Without the key, holdings are still refused as before.
    assert refusal(lambda: gate_a.initial_state(capture, s2_shadow(), run_id)) == \
        'Existing stock holdings require reviewed cost-basis history'
    off_by_one = export()
    off_by_one['positions']['SKHYB']['units'] += 1
    assert 'differ from the captured chain balance: SKHYB' in refusal(
        lambda: gate_a.initial_state(capture, p, run_id, carry_over=off_by_one))
    zero_cost = export()
    zero_cost['positions']['TSLAB']['cost_basis_units'] = 0
    cost_without_units = export()
    cost_without_units['positions']['MSFTB']['cost_basis_units'] = 5
    negative, fractional = export(), export()
    negative['positions']['NVDAB']['cost_basis_units'] = -1
    fractional['positions']['NVDAB']['cost_basis_units'] = 1.5
    for bad in (export(wallet_id='0x' + '2' * 40), export(source_run_id=run_id), export(reservations={'r': {}}),
                zero_cost, cost_without_units, negative, fractional, export(schema='Other'),
                {k: v for k, v in export().items() if k != 'projection_sha256'},
                export(positions={s: v for s, v in export()['positions'].items() if s != 'MSFTB'})):
        with pytest.raises(ContractError):
            gate_a.initial_state(capture, p, run_id, carry_over=bad)


# --- S4-5: signed dev preparation and gate_a_check --------------------------------------------------------------------

def test_s4_5_preparation_packages_and_pins_the_export_and_the_checker_rebuilds_the_state():
    p = json.loads(PROFILE.read_bytes())
    raw = json.dumps(export()).encode()
    files = rh.prepared(p, capture_raw=json.dumps(held_capture()).encode(), carry_over_raw=raw,
                        allowance_recovery=True, **POLICY)
    assert files[gate_a.CARRY_OVER_FILE] == raw
    values = {n: json.loads(v) for n, v in files.items() if n.endswith('.json')}
    report = values['preparation-report.json']
    assert report['holdings_carry_over'] == dict(sha256=gate_a.digest(raw),
                                                 source_run_id='larp-dev-rehearsal-20261024-s2', source_version=203)
    assert report['input_hashes'][gate_a.CARRY_OVER_FILE] == gate_a.digest(raw)
    assert values['runtime.json']['driver']['allowance_recovery'] is True
    assert {s: v['units'] for s, v in values['initial-state.json']['positions'].items()} == \
        dict.fromkeys(TOKENS, 0) | HELD
    gate_a_check.check_scope(values, report)
    gate_a_check.check_inputs(files, values, report)
    # The checker refuses a package whose export, pin or state was changed after preparation.
    tampered = deepcopy(values)
    tampered[gate_a.CARRY_OVER_FILE]['positions']['GOOGLB']['cost_basis_units'] += 1
    with pytest.raises(ContractError):
        gate_a_check.check_inputs(files, tampered, report)
    with pytest.raises(ContractError):
        gate_a_check.check_inputs(files, values, dict(report, holdings_carry_over=None))
    without = {k: v for k, v in values.items() if k != gate_a.CARRY_OVER_FILE}
    with pytest.raises(ContractError):
        gate_a_check.check_inputs(files, without, report)
    build_runtime(PROFILE.read_bytes())


def test_s4_5_package_files_accepts_the_export_as_an_optional_file(tmp_path):
    p = json.loads(PROFILE.read_bytes())
    files = rh.prepared(p, capture_raw=json.dumps(held_capture()).encode(),
                        carry_over_raw=json.dumps(export()).encode(), **POLICY)
    for name, raw in files.items():
        (tmp_path / name).write_bytes(raw)
    package, report = gate_a_check.package_files(tmp_path)
    assert gate_a.CARRY_OVER_FILE in package and 'holdings_carry_over' in report


def test_s4_5_without_the_profile_key_preparation_still_refuses_held_stocks():
    with pytest.raises(ContractError):
        rh.prepared(s2_shadow(), capture_raw=json.dumps(held_capture()).encode(), **POLICY)
    with pytest.raises(ContractError):
        rh.prepared(s2_shadow(), capture_raw=json.dumps(held_capture()).encode(),
                    carry_over_raw=json.dumps(export()).encode(), **POLICY)


# --- S4-6: the first round of run 5 sells and never buys ---------------------------------------------------------------

def test_s4_6_first_round_from_the_carried_book_exits_every_name_and_buys_nothing():
    terminal = dict(S2, new_risk_end='2026-10-10T21:00:00Z', flatten_start='2026-10-10T21:00:00Z',
                    signing_end='2026-10-11T12:00:00Z')
    result = run(at(AFTER_CLOSE, profile_changes=terminal, held=dict(NVDAB=AT_95, SKHYB=AT_95 // 2)))
    assert {r['symbol']: r['reasons'] for r in result['requirements']} == {
        'NVDAB': ['TERMINAL_FLATTEN'], 'SKHYB': ['TERMINAL_FLATTEN']}
    asked = [(q['side'], q['mandatory']) for q in result['quote_requests']] + [
        (i['side'], i['mandatory']) for i in result['intents']]
    assert asked and set(asked) == {('SELL', True)}

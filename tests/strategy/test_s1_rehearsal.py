"""IDEA-049-C SJ-11-RH01: a deterministic, SHADOW-evidence S1 rehearsal (run 3). Fixture S1 block; no ports or keys.

The fixture block (tests/strategy/test_s1_core.py) stands in for Keith's block, so no profile here is a run-3 profile.
"""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
from unittest.mock import patch

import pytest

from larp.contracts import ContractError, Document
from larp.runtime import gate_a, gate_a_check
from larp.strategy.profiles import build_live_profiles, validate_live
from tests.strategy.test_s1_core import NAMES, block

ROOT = Path(__file__).resolve().parents[2]
EV = ROOT / 'docs/build/evidence'
DECISION = 'SJ-11-RH01 fixture'
SCOPE = 'Live profile differs from decided v1 scope'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def document(path):
    return Document.from_dict(json.loads(path.read_bytes()))


# The RC4 rehearsal gas and authority inputs (tools/deploy/build_rehearsal_candidate.py).
AUTHORITY = dict(seconds=660, margin=30, decision_id='IDEA-049-C LD04-V01 (Keegan, 2026-10-20)',
                 data_hash=sha(EV / 'ld02-execution-packet-20261020.json'))
BUDGET = dict(action_units=384000000000000, sizing_units=80004608000000,
              decision_id='IDEA-049-C LD10-Q01 (Keegan delegation, 2026-10-21)',
              data_hash=sha(EV / 'signer-numeric-ceilings-20261021.json'))


def inputs():
    return document(EV / 'quotes-complete-20261020/quote-cost-summary.json'), document(
        ROOT / 'config/intelligence/red_flags.v1.json')


def s1_raw(**changes):
    return json.dumps(block(**changes), sort_keys=True).encode()


def candidate(exit_children=2, **changes):
    from tools.deploy.build_rehearsal_candidate import build
    return build(exit_children, s1_raw=s1_raw(**changes), s1_decision=DECISION).read()


def shadow(**changes):
    """The S1 REHEARSAL profile with LD11-RH01's SHADOW scope and a two-child reserve, without the candidate tool."""
    p = build_live_profiles(*inputs(), s1=block(**changes), s1_decision=DECISION, initial_gas_only=True,
                            authority=AUTHORITY, gas_budget=BUDGET)['REHEARSAL'].read()
    p.update(evidence_mode='SHADOW', falsifier_authority='SHADOW', exit_gas_reserve_units=10 * BUDGET['action_units'])
    return p


def refusal(call):
    with pytest.raises(ContractError) as info:
        call()
    return str(info.value)


# --- RH1/RH2/RH5: validate_live ----------------------------------------------------------------------------------

def test_rh1_s1_shadow_rehearsal_passes_validate_live():
    p = shadow()
    assert (p['baseline'], p['environment']) == ('TREND_GUARDED_VOL', 'REHEARSAL')
    assert (p['evidence_mode'], p['falsifier_authority'], p['assessment_required']) == ('SHADOW', 'SHADOW', False)
    validate_live(p)


def test_rh2_rh5_s1_shadow_outside_the_rehearsal_scope_is_refused_with_its_reason():
    p = shadow()
    cases = dict(final=dict(environment='FINAL'), assessment=dict(assessment_required=True),
                 falsifier_only=dict(falsifier_authority='NONE'))
    for name, change in cases.items():
        changed = dict(p, **change)
        assert refusal(lambda: validate_live(changed)) == SCOPE, name


def test_rh5_specific_refusals_are_not_rewrapped():
    p = shadow()
    assert refusal(lambda: validate_live(dict(p, exit_gas_reserve_units=1))) == \
        'Insufficient exit gas reserve for every position'
    assert refusal(lambda: validate_live(dict(p, statement_authority='DISCRETIONARY_EXIT'))) == SCOPE
    # Errors that are not ContractErrors keep the generic message.
    assert refusal(lambda: validate_live(dict(p, impact_median_bps=5))) == 'Malformed or incomplete live profile'


# --- RH1/RH2: signed dev preparation without model routing ---------------------------------------------------------

def prepared(p, **changes):
    from tests.runtime.test_gate_a import assembled
    with patch('socket.create_connection', side_effect=AssertionError('no model/network')):
        return assembled(profile_raw=json.dumps(p).encode(), execution='service',
                         adoption_ref='SYNTHETIC SJ-11-RH01', **changes)


def test_rh1_signed_dev_preparation_with_the_deterministic_assessor():
    p = shadow()
    files = prepared(p)
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    report = values['preparation-report.json']
    driver = values['runtime.json']['driver']
    assert (driver['assessor'], driver['execution'], values['runtime.json']['mode']) == (
        'deterministic', 'service', 'dev')
    assert driver['strategy_profile_sha256'] == gate_a.digest(files['strategy-profile.json'])
    assert 'model-routing.json' not in files and 'model_routing_sha256' not in driver
    assert report['model_adoption_ref'] == 'SYNTHETIC SJ-11-RH01'
    gate_a_check.check_scope(values, report)
    gate_a_check.check_inputs(files, values)


def test_rh2_live_mode_final_or_bounded_evidence_is_still_refused():
    p = shadow()
    signed = 'Signed preparation needs reviewed routing or scoped deterministic rehearsal and an adoption reference'
    assert refusal(lambda: prepared(p, runtime_mode='live')) == signed
    assert refusal(lambda: prepared(dict(p, environment='FINAL'), runtime_mode='live')) == signed
    assert refusal(lambda: prepared(dict(p, environment='FINAL'))) == signed
    bounded = dict(p, evidence_mode='BOUNDED_FALSIFIER', falsifier_authority='DISCRETIONARY_EXIT')
    validate_live(bounded)
    assert refusal(lambda: prepared(bounded)) == signed
    # The checker refuses the same escapes in an already prepared package.
    files = prepared(p)
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    for env, evidence in [('FINAL', 'SHADOW'), ('REHEARSAL', 'BOUNDED_FALSIFIER')]:
        modified = deepcopy(values)
        modified['strategy-profile.json'].update(environment=env, evidence_mode=evidence)
        with pytest.raises(ContractError):
            gate_a_check.check_scope(modified, values['preparation-report.json'])


def test_rh1_scope_is_dev_rehearsal_only():
    p = shadow()
    assert gate_a.scoped_rehearsal(p, 'dev')
    assert not gate_a.scoped_rehearsal(p, 'live')
    for change in (dict(environment='FINAL'), dict(evidence_mode='BOUNDED_FALSIFIER'),
                   dict(falsifier_authority='DISCRETIONARY_EXIT'), dict(assessment_required=True),
                   dict(baseline='PRICE_MOMENTUM')):
        assert not gate_a.scoped_rehearsal(dict(p, **change), 'dev'), change


def test_rh1_signed_s1_rehearsal_runtime_builds_with_the_real_live_settings():
    """LV4-style: the prepared S1 profile composes a dev/service runtime without models or network."""
    build_runtime(json.dumps(shadow()).encode())


def build_runtime(raw):
    from tests.runtime.test_driver import Composition, Store
    from larp.runtime.service import build_driver
    from larp.runtime.driver import ServiceExecution
    fixture = Composition(); fixture.setUp()
    try:
        cfg = fixture.config(execution='service', intelligence_mode='live', expiry_grace_ms=5000)
        base = json.loads((gate_a.ROOT / 'config/runtime/runtime.example.json').read_bytes())['driver']
        for key in ('balance_check_interval_ms', 'balance_check_max_age_ms', 'price_jump_check_bps'):
            cfg['driver'][key] = base[key]
        cfg['driver']['balance_rpc_providers'] = [dict(url='https://rpc.invalid/', source_id='synthetic-rpc')]
        (fixture.root / 'profile.json').write_bytes(raw)
        cfg['driver']['strategy_profile_sha256'] = gate_a.digest(raw)
        cfg['mode'] = 'dev'
        with patch('socket.create_connection', side_effect=AssertionError('No network during construction')):
            runtime = build_driver(cfg, Store(), fixture.secrets)
        try:
            assert isinstance(runtime.execution, ServiceExecution)
            assert not runtime.signing
        finally:
            runtime.ports['evidence'].close()
    finally:
        fixture.doCleanups()


# --- RH4: the two-child S1 rehearsal candidate --------------------------------------------------------------------

def one_child(**options):
    return build_live_profiles(*inputs(), s1=block(), s1_decision=DECISION, **options)


def test_rh4_two_child_reserve_and_only_the_scoped_fields_differ_from_the_one_child_build():
    p = candidate()
    action = p['gas_action_budget_units']
    assert action == BUDGET['action_units']
    assert p['exit_gas_reserve_units'] == 5 * 2 * action == 3_840_000_000_000_000
    assert 'LD10-P03' in p['provenance']['exit_gas_reserve_units']['decision_id']
    assert p['provenance']['exit_gas_reserve_units']['formula'].startswith('5 positions*2 balanced exit children')
    assert p['provenance']['s1']['data_hash'] == hashlib.sha256(s1_raw()).hexdigest()
    assert p['provenance']['s1']['decision_id'] == DECISION
    assert 'SJ-11' in p['provenance']['evidence_mode']['decision_id']
    base = one_child(initial_gas_only=True, authority=AUTHORITY, gas_budget=BUDGET)['REHEARSAL'].read()
    assert {k for k in set(p) | set(base) if p.get(k) != base.get(k)} == {
        'exit_gas_reserve_units', 'evidence_mode', 'falsifier_authority', 'provenance'}
    assert {k for k in p if p[k] != shadow()[k]} == {'provenance'}
    validate_live(p)


def test_rh4_one_child_s1_builds_are_unchanged_and_the_validation_minimum_is_kept():
    pinned = {('rc4', 'REHEARSAL'): 'fbecead883e7e906fca61736ba0aef959c58fadf9a301858c8ae11a2b7ec4b4c',
              ('rc4', 'FINAL'): '5425acf46529908f486fae5c18e1f7c754d9180d7cffbedd2c0e6e8c95fbec80',
              ('plain', 'REHEARSAL'): 'e724657b0ba4b02cd9b4def34ede18afdf5f90c8a75f830516cf315a766bed4e',
              ('plain', 'FINAL'): '28b7de106af7f399dab8c56768ee5d2000a0ba0bcf529f9184239285f3a20e0e'}
    builds = dict(rc4=one_child(initial_gas_only=True, authority=AUTHORITY, gas_budget=BUDGET), plain=one_child())
    for (kind, env), digest in pinned.items():
        doc = builds[kind][env]
        assert hashlib.sha256(doc.payload).hexdigest() == digest, (kind, env)
    p = builds['rc4']['REHEARSAL'].read()
    assert p['exit_gas_reserve_units'] == 5 * p['gas_action_budget_units']
    two = candidate()
    validate_live(dict(two, exit_gas_reserve_units=5 * two['gas_action_budget_units']))
    assert refusal(lambda: validate_live(dict(two, exit_gas_reserve_units=5 * two['gas_action_budget_units'] - 1))) \
        == 'Insufficient exit gas reserve for every position'


def test_rh4_rehearsal_weights_must_be_one_fifth_each():
    # 0.198..0.202 fits the measured minimum at 100 USDT (C5: every weight >= 0.1962), so only the 1/5 rule refuses.
    near = {s: [1, 5] for s in NAMES}
    near.update({NAMES[0]: [101, 500], NAMES[1]: [99, 500]})
    validate_live(build_live_profiles(*inputs(), s1=block(weights=near), s1_decision=DECISION, initial_gas_only=True,
                                      authority=AUTHORITY, gas_budget=BUDGET)['REHEARSAL'].read())
    assert re.search('1/5', refusal(lambda: candidate(weights=near)))


def test_rh4_hard_line_needing_more_exit_children_than_reserved_is_refused():
    # Hard line 35% of 100 USDT against a 19.1 USDT cap: two balanced children (LD10-P03 D1).
    assert re.search('exit children', refusal(lambda: candidate(exit_children=1)))
    with pytest.raises(ValueError):
        candidate(exit_children=3)


def test_rh4_s1_config_and_decision_go_together(tmp_path):
    from tools.deploy.build_rehearsal_candidate import build, main
    with pytest.raises(ContractError):
        build(2, s1_raw=s1_raw())
    with pytest.raises(ContractError):
        build(2, s1_decision=DECISION)
    config = tmp_path / 's1.json'
    config.write_bytes(s1_raw())
    out, stdout = tmp_path / 'profile.json', io.StringIO()
    with redirect_stdout(stdout):
        main(['--output', str(out), '--exit-children', '2', '--s1-config', str(config), '--s1-decision', DECISION])
    p = json.loads(out.read_bytes())
    assert p == candidate()
    assert stdout.getvalue().strip() == Document.from_dict(p).digest('StrategyProfile.v1')
    with pytest.raises(SystemExit):
        main(['--output', str(tmp_path / 'other.json'), '--exit-children', '2', '--s1-config', str(config)])
    with pytest.raises(FileExistsError):
        main(['--output', str(out), '--exit-children', '2', '--s1-config', str(config), '--s1-decision', DECISION])


def test_l1_s1_rehearsal_requires_the_deterministic_limiter(tmp_path):
    """SJ-11-RH01-L1: no hosted models in this scope, and nothing sets exposure_assessment, so MODEL would never move."""
    from tools.deploy.build_rehearsal_candidate import main
    assert re.search('limiter_mode', refusal(lambda: candidate(limiter_mode='MODEL')))
    config, out = tmp_path / 's1.json', tmp_path / 'profile.json'
    config.write_bytes(s1_raw(limiter_mode='MODEL'))
    with pytest.raises(ContractError):
        main(['--output', str(out), '--exit-children', '2', '--s1-config', str(config), '--s1-decision', DECISION])
    assert not out.exists()
    # L2: the DETERMINISTIC fixture block builds the same bytes as before the guard (2e8a633).
    assert hashlib.sha256(Document.from_dict(candidate()).payload).hexdigest() == \
        'cbdda7df294bce307d57fd4d126e639d21a1d7fae4a6f78628a169ce16ab978a'


# --- M3 probe: only the embedded profile differs ------------------------------------------------------------------

def test_probe_for_an_s1_profile_differs_from_the_reviewed_probe_only_in_the_profile_line():
    from tools.deploy.ld10_readonly_packet import script
    ew = (EV / 'rehearsal-exit-split-20261021/rehearsal-deterministic.json').read_bytes()
    reviewed = script(ew)
    assert hashlib.sha256(reviewed.encode()).hexdigest() == \
        '692787e49a55c37fec5af9082a0247e202e86f4aaf8e083e939c55c6d59b69b3'
    s1 = Document.from_dict(candidate()).payload + b'\n'
    changed = [(a, b) for a, b in zip(reviewed.splitlines(), script(s1).splitlines()) if a != b]
    assert len(reviewed.splitlines()) == len(script(s1).splitlines())
    assert len(changed) == 1 and all(line.startswith('SELECTED_PROFILE_B64 = ') for line in changed[0])

"""IDEA-089 S2I-1..S2I-7: KIT_OPEN_STATE hours for the weekend REHEARSAL (run 4). Synthetic ports; no keys or network."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from larp.contracts import ContractError, Document
from larp.execution import USDT
from larp.marketdata.port import TOKENS
from larp.research.fixtures import changed, with_quotes
from larp.runtime import gate_a, gate_a_check
from larp.strategy import execution_bounds as bounds, s1
from larp.strategy.profiles import validate_live
from tests.execution_fixtures import intent
from tests.strategy import test_s1_rehearsal as rh
from tests.strategy.test_execution_bounds import at, milliseconds, run
from tests.strategy.test_s1_core import block

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/build/evidence/s2-rehearsal-profile-20261024'
BLOCK, PROFILE = EVIDENCE / 's2-block.json', EVIDENCE / 'rehearsal-s2-deterministic.json'
RUN3 = ROOT / 'docs/build/evidence/s1-rehearsal-profile-20261023'
PROFILE_SHA256 = 'eb55d76a36b9fb931f551752da9266c379072611d789ab85d9cb1fc2291d8e68'
PROFILE_DIGEST = '120fcd1275d217ca07d3bbca40dd8e4e9484b9de579f7964023a84867fbb8e69'
PROBE_SHA256 = '8e8d6c89bf4f16e69465b2fc46db4414b4b623d2d6909b2a3c9325d5930ce97a'
RUN3_SHA256 = '6bcf1dfbd7f0c29893dd62bf67d9bcf7a04299b1d24a29d7310b6d769f8c1526'
EXECUTION = dict(open_delay_seconds=1800, close_buffer_seconds=900, max_attempts_per_leg_session=5)
S2 = dict(s1=block(execution=dict(EXECUTION, hours='KIT_OPEN_STATE')))
NYSE = dict(s1=block(execution=EXECUTION))
# The synthetic session (tests/strategy/test_s1_plan.py snap): open 13:30Z, close 20:00Z, next open 13:30Z next day.
AFTER_CLOSE, NEXT_OPEN = '2026-10-10T23:00:00Z', '2026-10-11T13:30:00Z'
POLICY = dict(untrusted_router_policy_file='/etc/larp/untrusted-router-policy.json',
              untrusted_router_policy_sha256='05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5')


def s2_shadow():
    """The fixture S1 rehearsal profile in SHADOW scope, with S2's hours set once the scope is (as the builder does)."""
    p = rh.shadow(execution=EXECUTION)
    p['s1'] = deepcopy(S2['s1'])
    return p


def weekend_round(profile_changes=S2):
    snapshot = with_quotes(at(AFTER_CLOSE, profile_changes=profile_changes))
    return snapshot, run(snapshot)


# --- S2I-1 / S2I-2 (S2-2, S2-8): both callers of `interval` --------------------------------------------------------

def test_s2i1_planner_reserves_a_discretionary_buy_after_the_close_only_with_open_state_hours():
    snapshot, result = weekend_round()
    assert result['intents'], result
    item = result['intents'][0]
    assert (item['side'], item['mandatory']) == ('BUY', False)
    session = snapshot.context.read()['execution_session']
    assert item['execution_bounds'] == dict(schema=bounds.SCHEMA, session_index=session['index'],
        leg='DISCRETIONARY:BUY:' + item['symbol'], ordinal=1,
        valid_from_ms=session['open_ms'], valid_until_ms=session['next_open_ms'])
    for unchanged in (NYSE, dict(s1=block(execution=dict(EXECUTION, hours='NYSE_SESSION')))):
        _, refused = weekend_round(unchanged)
        assert not refused['intents'] and not refused['quote_requests']
        assert 'EXECUTION_WINDOW_CLOSED' in {r['reason'] for r in refused['rejections']}


def test_s2i1_openstate_and_the_profile_window_still_apply():
    snapshot = with_quotes(at(AFTER_CLOSE, profile_changes=S2))
    markets = snapshot.context.read()['markets']
    for market in markets:
        market['token_open'] = False
    closed = run(changed(snapshot, markets=markets))
    assert not closed['intents'] and 'MARKET_CLOSED_OR_UNKNOWN' in {r['reason'] for r in closed['rejections']}
    late = run(with_quotes(at(AFTER_CLOSE, profile_changes=dict(S2, new_risk_end='2026-10-10T22:00:00Z'))))
    assert not late['intents'] and not late['quote_requests'] and not late['execution_attempts']


def admitted_case():
    snapshot, result = weekend_round()
    planned = result['intents'][0]
    record = dict(policy_input=dict(context=snapshot.context.read()), plan=result)
    economic = intent(intent_id=planned['intent_id'], pay_token=USDT, receive_token=TOKENS[planned['symbol']],
                      amount=planned['pay_units'] * 10**12, minimum_output=planned['min_receive_units'])
    return dict(round_records={'round': record}), economic, record


def test_s2i2_execution_admits_the_planner_accepted_weekend_buy_until_the_next_open():
    projection, economic, record = admitted_case()
    assert bounds.permitted(projection, economic, milliseconds(AFTER_CLOSE))
    assert bounds.permitted(projection, economic, milliseconds('2026-10-11T13:29:59Z'))
    assert not bounds.permitted(projection, economic, milliseconds(NEXT_OPEN))
    # The same durable record under NYSE hours: the execution side refuses what it would not have planned.
    nyse = deepcopy(record)
    nyse['policy_input']['context']['profile']['s1']['execution'].pop('hours')
    assert not bounds.permitted(dict(round_records={'round': nyse}), economic, milliseconds(AFTER_CLOSE))


# --- S2I-3: parameters, and existing profiles unchanged -----------------------------------------------------------

def test_s2i3_hours_values_and_an_absent_key_keeps_todays_config():
    assert bounds.parameters(dict(EXECUTION)) == EXECUTION
    assert bounds.parameters(dict(EXECUTION, hours='NYSE_SESSION'))['hours'] == 'NYSE_SESSION'
    assert bounds.parameters(dict(EXECUTION, hours='KIT_OPEN_STATE'))['hours'] == 'KIT_OPEN_STATE'
    for bad in ('24_7', None, True, 'kit_open_state'):
        with pytest.raises(ContractError):
            s1.config(dict(s1=block(execution=dict(EXECUTION, hours=bad))))
    with pytest.raises(ContractError):
        s1.config(dict(s1=block(execution=dict(EXECUTION, hours='KIT_OPEN_STATE', extra=1))))
    raw = (RUN3 / 'rehearsal-s1-deterministic.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RUN3_SHA256
    p = json.loads(raw)
    assert 'hours' not in p['s1']['execution'] and not bounds.open_state_hours(p)
    validate_live(p)


# --- S2I-4 (S2-1): five refusal points ----------------------------------------------------------------------------

def test_s2i4_validate_live_scope():
    p = s2_shadow()
    validate_live(p)
    for change in (dict(environment='FINAL'), dict(evidence_mode='BOUNDED_FALSIFIER'),
                   dict(falsifier_authority='DISCRETIONARY_EXIT')):
        assert rh.refusal(lambda: validate_live(dict(p, **change))) in (bounds.SCOPE, rh.SCOPE), change
    # The S2 check itself, separately from the v1 scope check (which allows BOUNDED_FALSIFIER evidence).
    assert rh.refusal(lambda: validate_live(dict(p, evidence_mode='BOUNDED_FALSIFIER',
                                                 falsifier_authority='DISCRETIONARY_EXIT'))) == bounds.SCOPE
    assert rh.refusal(lambda: bounds.require_open_state_scope(dict(p, environment='FINAL'), None)) == bounds.SCOPE
    for mode in ('live', 'offline', None):
        bounds.require_open_state_scope(rh.shadow(), mode)  # S1 without the hours: unaffected


def test_s2i4_preparation_and_gate_check_refuse_live_mode():
    p = s2_shadow()
    assert rh.refusal(lambda: rh.prepared(p, runtime_mode='live')) == bounds.SCOPE
    files = rh.prepared(p)
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    gate_a_check.check_scope(values, values['preparation-report.json'])
    live = deepcopy(values)
    for name in ('runtime.json', 'uploader.json', 'initial-state.json'):
        live[name]['mode'] = 'live'
    report = dict(values['preparation-report.json'], runtime_mode='live')
    assert rh.refusal(lambda: gate_a_check.check_scope(live, report)) == bounds.SCOPE


def test_s2i4_runtime_start_refuses_outside_dev():
    rh.build_runtime(json.dumps(s2_shadow()).encode())
    assert rh.refusal(lambda: build_runtime(json.dumps(s2_shadow()).encode(), mode='live')) == bounds.SCOPE


def test_s2i4_execution_start_refuses_outside_dev():
    from larp.execution_live.main import NotIntegrated, build_execution
    from tests.execution import test_execution_loop as loop_fixtures
    fixture = loop_fixtures.Composition()
    fixture.setUp()
    try:
        raw = json.dumps(s2_shadow()).encode()
        (fixture.root / 'profile.json').write_bytes(raw)
        config = dict(fixture.config, strategy_profile_sha256=hashlib.sha256(raw).hexdigest())
        with pytest.raises(NotIntegrated):  # dev: past the S2 check, to the executor capability gate
            build_execution(config, loop_fixtures.Store(), fixture.secrets)
        for mode in ('live', None):
            changed_config = dict(config, mode=mode) if mode else {k: v for k, v in config.items() if k != 'mode'}
            assert rh.refusal(lambda: build_execution(changed_config, loop_fixtures.Store(), fixture.secrets)) \
                == bounds.SCOPE
    finally:
        fixture.doCleanups()


def build_runtime(raw, *, mode='dev', history=True, **driver):
    """tests/strategy/test_s1_rehearsal.py build_runtime with a run mode and extra driver settings."""
    from tests.runtime.test_driver import Composition, Store
    from larp.runtime.service import build_driver
    fixture = Composition(); fixture.setUp()
    try:
        cfg = fixture.config(execution='service', intelligence_mode='live', expiry_grace_ms=5000)
        base = json.loads((gate_a.ROOT / 'config/runtime/runtime.example.json').read_bytes())['driver']
        for key in ('balance_check_interval_ms', 'balance_check_max_age_ms', 'price_jump_check_bps'):
            cfg['driver'][key] = base[key]
        cfg['driver']['balance_rpc_providers'] = [dict(url='https://rpc.invalid/', source_id='synthetic-rpc')]
        cfg['driver'].update(driver)
        (fixture.root / 'profile.json').write_bytes(raw)
        cfg['driver']['strategy_profile_sha256'] = gate_a.digest(raw)
        from larp.marketdata.history import requires_history
        if history and requires_history(json.loads(raw)):
            from tests.marketdata.test_session_history import SEMANTICS
            from tests.runtime.test_gate_a import captured
            history_raw = json.dumps(SEMANTICS).encode()
            (fixture.root / 'token-history.json').write_bytes(history_raw)
            cfg['driver'].update(token_history_file=str(fixture.root / 'token-history.json'),
                                 token_history_sha256=gate_a.digest(history_raw), issuers=gate_a.issuer_map(captured()))
        cfg['mode'] = mode
        with patch('socket.create_connection', side_effect=AssertionError('No network during construction')):
            runtime = build_driver(cfg, Store(), fixture.secrets)
        runtime.ports['evidence'].close()
        return runtime
    finally:
        fixture.doCleanups()


# --- S2I-5 (S2-10): the router-policy pair in runtime.json ---------------------------------------------------------

def test_s2i5_preparation_writes_the_policy_pair_and_refuses_partial_inputs():
    p = s2_shadow()
    files = rh.prepared(p, **POLICY)
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    driver = values['runtime.json']['driver']
    assert {k: driver[k] for k in POLICY} == POLICY
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)
    without = rh.prepared(p)
    plain = json.loads(without['runtime.json'])['driver']
    assert not any(k in plain for k in POLICY)
    assert {k: v for k, v in driver.items() if k not in POLICY} == plain
    path, sha = POLICY.values()
    for bad in (dict(untrusted_router_policy_file=path), dict(untrusted_router_policy_sha256=sha),
                dict(POLICY, untrusted_router_policy_sha256=sha[:-1]),
                dict(POLICY, untrusted_router_policy_sha256=sha.upper()),
                dict(POLICY, untrusted_router_policy_file='etc/larp/untrusted-router-policy.json')):
        with pytest.raises(ContractError):
            rh.prepared(p, **bad)
    with pytest.raises(ContractError):
        rh.prepared(p, balance_rpc_url=None, balance_rpc_source_id=None, **POLICY)
    half = deepcopy(values)
    del half['runtime.json']['driver']['untrusted_router_policy_sha256']
    with pytest.raises(ContractError):
        gate_a_check.check_scope(half, values['preparation-report.json'])


def test_s2i5_the_pair_is_optional_and_the_runtime_wires_the_verifier_only_with_it():
    # In the examples a null is a placeholder every host must fill (tests/runtime/test_driver.py SG3); the pair is
    # optional, so the examples leave it out and preparation adds it (docs/build/runbook.md).
    for name in ('runtime.example.json', 'runtime.aiand-shadow.example.json'):
        example = json.loads((ROOT / 'config/runtime' / name).read_bytes())['driver']
        assert not any(k in example for k in POLICY), name
    from larp.runtime import service
    seen = []
    with patch.object(service, 'quote_verifier', side_effect=lambda d, *a, **k: seen.append(
            {key: d.get(key) for key in POLICY})):
        build_runtime(json.dumps(s2_shadow()).encode(), **POLICY)
        build_runtime(json.dumps(s2_shadow()).encode())
    assert seen == [POLICY, dict.fromkeys(POLICY)]


# --- S2I-6 (S2-9): five quote rounds per leg over the weekend session ---------------------------------------------

def test_s2i6_five_buy_quote_rounds_then_the_leg_limit():
    snapshot = at(AFTER_CLOSE, profile_changes=S2)
    snapshot = changed(snapshot, markets=[m for m in snapshot.context.read()['markets'] if m['symbol'] == 'NVDAB'])
    snapshot = with_quotes(snapshot, spread_bps=100)  # every quote refused on cost, so each round spends a slot
    for ordinal in range(1, 6):
        result = run(snapshot)
        assert not result['intents'] and result['execution_attempts'], result
        assert {i['authority']['ordinal'] for i in result['execution_attempts']} == {ordinal}
        snapshot = changed(snapshot, execution_attempt_budget=result['execution_attempt_budget'])
    refused = run(snapshot)
    assert not refused['execution_attempts'] and not refused['quote_requests']
    assert 'LEG_ATTEMPT_LIMIT' in {r['reason'] for r in refused['rejections']}


# --- S2I-7 (S2-3, S2-4, S2-9): the committed S2 profile -----------------------------------------------------------

def test_s2i7_profile_rebuilds_byte_for_byte_and_differs_from_run_three_only_where_decided():
    from tools.deploy.build_rehearsal_candidate import build
    raw = PROFILE.read_bytes()
    p = json.loads(raw)
    rebuilt = build(2, s1_raw=BLOCK.read_bytes(), s1_decision=p['provenance']['s1']['decision_id'])
    assert rebuilt.payload + b'\n' == raw
    assert hashlib.sha256(raw).hexdigest() == PROFILE_SHA256
    assert rebuilt.digest('StrategyProfile.v1') == PROFILE_DIGEST == Document.from_dict(p).digest('StrategyProfile.v1')
    assert p['provenance']['s1']['data_hash'] == hashlib.sha256(BLOCK.read_bytes()).hexdigest()
    validate_live(p)
    run3 = json.loads((RUN3 / 'rehearsal-s1-deterministic.json').read_bytes())
    window = ('trade_after', 'new_risk_end', 'flatten_start', 'signing_end')
    assert {k for k in set(p) | set(run3) if p.get(k) != run3.get(k)} == {*window, 'policy_id', 's1', 'provenance'}
    assert [p[k] for k in window] == ['2026-10-24T01:00:00Z', '2026-10-25T08:00:00Z',
                                      '2026-10-25T09:00:00Z', '2026-10-25T15:00:00Z']
    assert p['policy_id'] == 'larp-s2-rehearsal-v1'
    assert {k for k in p['s1'] if p['s1'][k] != run3['s1'][k]} == {'execution'}
    assert p['s1']['execution'] == dict(run3['s1']['execution'], hours='KIT_OPEN_STATE', max_attempts_per_leg_session=5)
    # baseline and s1 share the S1 block's decision; the rest of the provenance is run 3's.
    assert {k for k in p['provenance'] if p['provenance'][k] != run3['provenance'][k]} == {
        *window, 'policy_id', 's1', 'baseline'}
    assert (p['environment'], p['evidence_mode'], p['falsifier_authority']) == ('REHEARSAL', 'SHADOW', 'SHADOW')
    assert bounds.open_state_hours(p)


def test_s2i7_signed_dev_preparation_checks_runtime_build_and_probe():
    p = json.loads(PROFILE.read_bytes())
    files = rh.prepared(p, **POLICY)
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    assert values['runtime.json']['driver']['assessor'] == 'deterministic'
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)
    build_runtime(PROFILE.read_bytes())  # the verifier's own wiring: test_s2i5 and tests/runtime (IDEA-088)
    from tools.deploy.ld10_readonly_packet import script
    assert hashlib.sha256(script(PROFILE.read_bytes()).encode()).hexdigest() == PROBE_SHA256


def test_s2i7_builder_refuses_open_state_hours_without_five_attempts():
    from tools.deploy.build_rehearsal_candidate import build
    value = json.loads(BLOCK.read_bytes())
    value['execution']['max_attempts_per_leg_session'] = 3
    with pytest.raises(ContractError):
        build(2, s1_raw=json.dumps(value).encode(), s1_decision='synthetic')


def test_s2i5_prepare_shadow_cli_passes_the_pair():
    from contextlib import redirect_stdout
    from io import StringIO
    import tempfile
    from larp.marketdata.web3 import encoded
    from tests.runtime.test_deploy_presetup import terraform_output
    from tests.runtime.test_gate_a import NOW, prepare_shadow, with_chain
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name, raw in {'terraform.json': encoded(terraform_output()), 'profile.json': PROFILE.read_bytes(),
                          'capture.json': encoded(with_chain())}.items():
            (root / name).write_bytes(raw)
        args = ['prepare', '--terraform-output', str(root / 'terraform.json'), '--profile', str(root / 'profile.json'),
                '--capture', str(root / 'capture.json'), '--run-id', 's2-test', '--build-id', 'b' * 40,
                '--rds-ca-sha256', 'c' * 64, '--balance-rpc-url', 'https://rpc.invalid/',
                '--balance-rpc-source-id', 'synthetic-rpc']
        with patch.object(prepare_shadow, 'utc', return_value=NOW), \
                patch.object(prepare_shadow.renderer, 'ignored_by_git', return_value=True), \
                patch.object(prepare_shadow, 'credentials', side_effect=AssertionError('No credentials')), \
                patch('socket.create_connection', side_effect=AssertionError('No network')), \
                redirect_stdout(StringIO()):
            assert prepare_shadow.main(args + ['--out', str(root / 'half'), '--untrusted-router-policy-file',
                                               POLICY['untrusted_router_policy_file']]) == 4
            assert not (root / 'half').exists()
            assert prepare_shadow.main(args + ['--out', str(root / 'new'),
                '--untrusted-router-policy-file', POLICY['untrusted_router_policy_file'],
                '--untrusted-router-policy-sha256', POLICY['untrusted_router_policy_sha256']]) == 0
        driver = json.loads((root / 'new' / 'runtime.json').read_bytes())['driver']
        assert {k: driver[k] for k in POLICY} == POLICY

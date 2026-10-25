"""IDEA-093: FS1, the final live solution (S4-1..S4-8, S4R-1..S4R-4, FS1-1..FS1-6). Synthetic ports; no keys or network.

S4 was renamed FS1 (and S4-R FS1-R); the criteria IDs keep their pre-registered names."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from larp.contracts import ContractError, Document
from larp.execution import USDT
from larp.marketdata.port import TOKENS
from larp.research.fixtures import changed, with_quotes
from larp.strategy import execution_bounds as bounds
from larp.strategy.profiles import validate_live
from tests.execution_fixtures import intent
from tests.strategy import test_s1_rehearsal as rh
from tests.strategy import test_s2_weekend as s2
from tests.strategy.test_execution_bounds import at, milliseconds, run
from tests.strategy.test_s1_core import block

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/build/evidence/fs1-final-20261025'
BLOCK, PROFILE = EVIDENCE / 'fs1-block.json', EVIDENCE / 'fs1-final.json'
WINDOW = ('trade_after', 'new_risk_end', 'flatten_start', 'signing_end')
PF04 = ['2026-10-29T14:00:00Z', '2026-11-09T21:00:00Z', '2026-11-10T19:00:00Z', '2026-11-11T14:45:00Z']
FS1 = dict(s1=block(execution=dict(s2.EXECUTION, hours='KIT_OPEN_STATE')))
# A synthetic Friday session (open 13:30Z, close 20:00Z) whose next open is Monday 13:30Z: the weekend is one session.
FRIDAY_OPEN, FRIDAY_CLOSE, MONDAY_OPEN = '2026-10-09T13:30:00Z', '2026-10-09T20:00:00Z', '2026-10-12T13:30:00Z'
SATURDAY, SUNDAY = '2026-10-10T23:00:00Z', '2026-10-11T12:00:00Z'


def profile():
    return json.loads(PROFILE.read_bytes())


def final_scope(p=None):
    """A FINAL with the decided v1 scope and FS1's hours (the committed profile unless given)."""
    return deepcopy(p or profile())


def weekend(value, profile_changes=FS1):
    """A round at `value` in the weekend session. The risk day is `value`'s UTC day, as the runtime's day roll leaves
    it (S2-12: without the roll a Sunday buy is NEW_RISK_HALTED)."""
    session = at(value).context.read()['session_index']
    return with_quotes(at(value, profile_changes=profile_changes, risk=dict(day=value[:10]), execution_session=dict(
        index=session, open_ms=milliseconds(FRIDAY_OPEN), close_ms=milliseconds(FRIDAY_CLOSE),
        next_open_ms=milliseconds(MONDAY_OPEN))))


# --- S4-1: the scope check -----------------------------------------------------------------------------------------

def test_s4_1_final_scope_is_accepted_only_in_live_mode():
    p = final_scope()
    assert (p['environment'], p['evidence_mode'], p['falsifier_authority'], p['statement_authority']) == (
        'FINAL', 'BOUNDED_FALSIFIER', 'DISCRETIONARY_EXIT', 'SHADOW')
    for mode in (None, 'live'):
        bounds.require_open_state_scope(p, mode)
    for mode in ('dev', 'offline', ''):
        assert rh.refusal(lambda: bounds.require_open_state_scope(p, mode)) == bounds.SCOPE, mode


def test_s4_1_final_with_shadow_evidence_or_a_rehearsal_with_final_evidence_is_refused():
    p = final_scope()
    for change in (dict(evidence_mode='SHADOW'), dict(falsifier_authority='SHADOW'),
                   dict(statement_authority='BOUNDED_FALSIFIER'), dict(environment='REHEARSAL'),
                   dict(environment='STAGING')):
        for mode in (None, 'live', 'dev'):
            assert rh.refusal(lambda: bounds.require_open_state_scope(dict(p, **change), mode)) == bounds.SCOPE, \
                (change, mode)
    # S2's rule is unchanged: a SHADOW REHEARSAL is accepted in dev only.
    shadow = s2.s2_shadow()
    bounds.require_open_state_scope(shadow, 'dev')
    assert rh.refusal(lambda: bounds.require_open_state_scope(shadow, 'live')) == bounds.SCOPE
    # Without the hours nothing changes for any profile or mode.
    nyse = deepcopy(p)
    nyse['s1']['execution'].pop('hours')
    for mode in (None, 'live', 'dev', 'offline'):
        bounds.require_open_state_scope(nyse, mode)


def test_s4_1_scheduled_flatten_stays_rehearsal_only():
    from larp.strategy import scheduled_flatten
    p = final_scope()
    p['scheduled_flatten_at'] = '2026-11-02T04:00:00Z'
    p['provenance']['scheduled_flatten_at'] = dict(decision_id='synthetic', formula='synthetic')
    assert rh.refusal(lambda: validate_live(p)) == scheduled_flatten.SCOPE


# --- S4-2 / S4-3: overnight and weekend entries, both callers of `interval` -----------------------------------------

def test_s4_2_planner_buys_overnight_and_at_the_weekend_with_open_state_hours():
    for value in (SATURDAY, SUNDAY):
        snapshot = weekend(value)
        result = run(snapshot)
        assert result['intents'], (value, result)
        item = result['intents'][0]
        assert (item['side'], item['mandatory']) == ('BUY', False)
        session = snapshot.context.read()['execution_session']
        assert item['execution_bounds'] == dict(schema=bounds.SCHEMA, session_index=session['index'],
            leg='DISCRETIONARY:BUY:' + item['symbol'], ordinal=1, valid_from_ms=milliseconds(FRIDAY_OPEN),
            valid_until_ms=milliseconds(MONDAY_OPEN))
        # S1's NYSE hours refuse the same snapshot (the S2-era limit FS1 removes).
        refused = run(weekend(value, s2.NYSE))
        assert not refused['intents'] and 'EXECUTION_WINDOW_CLOSED' in {r['reason'] for r in refused['rejections']}


def test_s4_2_openstate_and_the_profile_window_still_apply():
    snapshot = weekend(SATURDAY)
    for key in ('token_open', 'underlying_open'):
        markets = snapshot.context.read()['markets']
        for market in markets:
            market[key] = False
        closed = run(changed(snapshot, markets=markets))
        assert not closed['intents'] and 'MARKET_CLOSED_OR_UNKNOWN' in {r['reason'] for r in closed['rejections']}, key
    late = run(weekend(SATURDAY, dict(FS1, new_risk_end='2026-10-10T22:00:00Z')))
    assert not late['intents'] and not late['quote_requests'] and not late['execution_attempts']
    early = run(weekend(SATURDAY, dict(FS1, trade_after='2026-10-11T00:00:00Z')))
    assert not early['intents'] and not early['quote_requests'] and not early['execution_attempts']


def test_s4_2_five_quote_rounds_per_leg_over_the_weekend_session_then_the_leg_limit():
    snapshot = weekend(SATURDAY)
    snapshot = changed(snapshot, markets=[m for m in snapshot.context.read()['markets'] if m['symbol'] == 'NVDAB'])
    snapshot = with_quotes(snapshot, spread_bps=100)  # every quote refused on cost, so each round spends a slot
    for ordinal in range(1, 6):
        result = run(snapshot)
        assert {i['authority']['ordinal'] for i in result['execution_attempts']} == {ordinal}, result
        snapshot = changed(snapshot, execution_attempt_budget=result['execution_attempt_budget'])
    refused = run(snapshot)
    assert not refused['execution_attempts'] and 'LEG_ATTEMPT_LIMIT' in {r['reason'] for r in refused['rejections']}


def test_s4_3_execution_admits_the_weekend_buy_until_monday_open():
    snapshot = weekend(SATURDAY)
    result = run(snapshot)
    planned = result['intents'][0]
    record = dict(policy_input=dict(context=snapshot.context.read()), plan=result)
    economic = intent(intent_id=planned['intent_id'], pay_token=USDT, receive_token=TOKENS[planned['symbol']],
                      amount=planned['pay_units'] * 10**12, minimum_output=planned['min_receive_units'])
    projection = dict(round_records={'round': record})
    for value in (SATURDAY, SUNDAY, '2026-10-12T13:29:59Z'):
        assert bounds.permitted(projection, economic, milliseconds(value)), value
    assert not bounds.permitted(projection, economic, milliseconds(MONDAY_OPEN))
    nyse = deepcopy(record)
    nyse['policy_input']['context']['profile']['s1']['execution'].pop('hours')
    assert not bounds.permitted(dict(round_records={'round': nyse}), economic, milliseconds(SATURDAY))


# --- S4-5: the wider slippage limit after S2-F6 ----------------------------------------------------------------------

def test_s4_5_a_12_bp_adverse_requote_prepares_at_20_bp_and_fails_the_minimum_at_8_bp():
    from larp.execution_live.venue import LiveVenue
    from tests.execution.test_requote_at_authorized_minimum import Wire, bps
    from tests.execution_fixtures import FakeDecoder
    planned, fresh = 1_000_000, 998_800  # the swap requote returns 12 bp less than the planning quote
    results = {}
    for limit in (8, 20):
        authorized = planned * (10000 - limit) // 10000
        i = intent(minimum_output=authorized, max_slippage_bps=limit)
        client = Wire(i, [fresh])
        economics = FakeDecoder().decode(LiveVenue(client, None, decoder=FakeDecoder()).quote(i, 0))
        assert all(bps(s) <= limit for s in client.slippages), (limit, client.slippages)
        results[limit] = economics.minimum_output >= authorized
    assert results == {8: False, 20: True}  # 8 bp: validate_payload blocks the swap (run 4); 20 bp: it prepares
    assert profile()['slippage_bps'] == 20


# --- S4-6 / S4-7: the committed profile and the builder --------------------------------------------------------------

def test_s4_6_profile_rebuilds_byte_for_byte_and_carries_the_final_values():
    from tools.deploy.build_final_candidate import build
    raw = PROFILE.read_bytes()
    p = json.loads(raw)
    rebuilt = build(s1_raw=BLOCK.read_bytes(), s1_decision=p['provenance']['s1']['decision_id'])
    assert rebuilt.payload + b'\n' == raw
    assert rebuilt.digest('StrategyProfile.v1') == Document.from_dict(p).digest('StrategyProfile.v1')
    assert p['provenance']['s1']['data_hash'] == hashlib.sha256(BLOCK.read_bytes()).hexdigest()
    validate_live(p)
    assert (p['environment'], p['expected_equity_units'], p['baseline']) == ('FINAL', 200_000_000, 'TREND_GUARDED_VOL')
    assert p['s1']['weights'] == {s: [1, 5] for s in TOKENS}
    assert p['s1']['execution'] == dict(open_delay_seconds=1800, close_buffer_seconds=900,
                                        max_attempts_per_leg_session=5, hours='KIT_OPEN_STATE')
    assert (p['slippage_bps'], p['policy_id']) == (20, 'larp-fs1-final-v1')
    assert [p[k] for k in WINDOW] == PF04
    assert (p['evidence_mode'], p['falsifier_authority']) == ('BOUNDED_FALSIFIER', 'DISCRETIONARY_EXIT')
    assert bounds.open_state_hours(p)


def test_s4_6_differs_from_the_generators_final_s1_profile_only_where_decided():
    from tools.deploy.build_rehearsal_candidate import pinned_profiles
    p = profile()
    value = json.loads(BLOCK.read_bytes())
    base_block = dict(value, execution={k: v for k, v in value['execution'].items() if k != 'hours'})
    generated = pinned_profiles(s1=base_block, s1_decision=p['provenance']['s1']['decision_id'])['FINAL'].read()
    # The generator's FINAL signing_end (Nov 11 14:45) already equals PF-04's; its provenance still differs.
    reviewed = {'entry_cost_basis', 'run_halt_recovery_bps', 's1_reduction_cost_cap_bps', 's1_capital_basis'}
    reviewed |= {'activation_self_check'}  # IDEA-093 SC (GAP-74): FINAL only
    decided = {'trade_after', 'new_risk_end', 'flatten_start', 'slippage_bps', 'policy_id', 's1', 'exit_gas_reserve_units', 'provenance', *reviewed}
    assert {k for k in set(p) | set(generated) if p.get(k) != generated.get(k)} == decided
    assert {k for k in p['s1'] if p['s1'][k] != generated['s1'][k]} == {'execution'}
    assert p['s1']['execution'] == dict(generated['s1']['execution'], hours='KIT_OPEN_STATE')
    # Two balanced exit children per position, as S2 (LD10-P03); the gas formulas as the rehearsal builder writes them.
    assert p['exit_gas_reserve_units'] == 10 * p['gas_action_budget_units'] > generated['exit_gas_reserve_units']
    assert {k for k in p['provenance'] if p['provenance'][k] != generated['provenance'].get(k)} == {
        *WINDOW, 'slippage_bps', 'policy_id', 's1', 'exit_gas_reserve_units',
        'gas_action_budget_units', 'gas_sizing_budget_units', *reviewed}


def test_s4_7_builder_refusals():
    from tools.deploy.build_final_candidate import build
    value = json.loads(BLOCK.read_bytes())

    def refused(**changes):
        changed_block = deepcopy(value)
        for key, item in changes.items():
            if key == 'execution':
                changed_block['execution'] = item
            else:
                changed_block[key] = item
        with pytest.raises(ContractError):
            build(s1_raw=json.dumps(changed_block).encode(), s1_decision='synthetic')

    refused(execution=dict(value['execution'], max_attempts_per_leg_session=3))
    refused(execution={k: v for k, v in value['execution'].items() if k != 'hours'})
    refused(execution=dict(value['execution'], hours='NYSE_SESSION'))
    refused(limiter_mode='MODEL')
    refused(weights=dict(value['weights'], NVDAB=[3, 10], MSFTB=[1, 10]))
    with pytest.raises(ContractError):
        build(s1_raw=BLOCK.read_bytes(), s1_decision=' ')
    with pytest.raises(ContractError):
        build(s1_raw=value, s1_decision='synthetic')


def test_s4_7_cli_writes_once(tmp_path):
    from tools.deploy.build_final_candidate import main
    out = tmp_path / 'final.json'
    args = ['--s1-config', str(BLOCK), '--s1-decision', profile()['provenance']['s1']['decision_id'],
            '--output', str(out)]
    main(args)
    assert out.read_bytes() == PROFILE.read_bytes()
    with pytest.raises(FileExistsError):
        main(args)


# --- S4-8: both service starts in live mode ------------------------------------------------------------------------

def _not_scope(call):
    try:
        call()
    except Exception as error:  # a later live gate may refuse; the open-state scope must not
        assert str(error) != bounds.SCOPE, error
        return error
    return None


def test_s4_8_runtime_start_passes_the_scope_in_live_and_refuses_dev():
    raw = PROFILE.read_bytes()
    _not_scope(lambda: s2.build_runtime(raw, mode='live'))
    assert rh.refusal(lambda: s2.build_runtime(raw, mode='dev')) == bounds.SCOPE


def test_s4_8_execution_start_passes_the_scope_in_live_and_refuses_dev():
    from larp.execution_live.main import build_execution
    from tests.execution import test_execution_loop as loop_fixtures
    fixture = loop_fixtures.Composition()
    fixture.setUp()
    try:
        raw = PROFILE.read_bytes()
        (fixture.root / 'profile.json').write_bytes(raw)
        config = dict(fixture.config, strategy_profile_sha256=hashlib.sha256(raw).hexdigest())
        _not_scope(lambda: build_execution(dict(config, mode='live'), loop_fixtures.Store(), fixture.secrets))
        for mode in ('dev', None):
            changed_config = dict(config, mode=mode) if mode else {k: v for k, v in config.items() if k != 'mode'}
            assert rh.refusal(lambda: build_execution(changed_config, loop_fixtures.Store(), fixture.secrets)) \
                == bounds.SCOPE, mode
    finally:
        fixture.doCleanups()


# --- IDEA-093 S4R-1..S4R-4: FS1-R, the dev REHEARSAL with FS1's settings ---------------------------------------------------

REHEARSAL = ROOT / 'docs/build/evidence/fs1-rehearsal-20261025/fs1-rehearsal.json'
S4R_WINDOW = ['2026-10-25T16:00:00Z', '2026-10-26T06:00:00Z', '2026-10-26T07:00:00Z', '2026-10-26T12:00:00Z']


def rehearsal_build(**options):
    from tools.deploy.build_rehearsal_candidate import build
    p = json.loads(REHEARSAL.read_bytes())
    return build(2, s1_raw=BLOCK.read_bytes(), s1_decision=p['provenance']['s1']['decision_id'], **options)


def test_s4r_1_rehearsal_rebuilds_and_passes_dev_preparation_and_runtime_build():
    raw = REHEARSAL.read_bytes()
    assert rehearsal_build(fs1_rehearsal=True).payload + b'\n' == raw
    p = json.loads(raw)
    validate_live(p)
    from larp.runtime import gate_a_check
    files = rh.prepared(p, **s2.POLICY)
    values = {n: json.loads(item) for n, item in files.items() if n.endswith('.json')}
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)
    s2.build_runtime(raw)


def test_s4r_2_differs_from_s2_only_in_slippage_window_and_policy_and_keeps_the_final_block():
    p = json.loads(REHEARSAL.read_bytes())
    s2p = json.loads(s2.PROFILE.read_bytes())
    changed_keys = {*WINDOW, 'slippage_bps', 'policy_id', 'entry_cost_basis', 'run_halt_recovery_bps', 's1_capital_basis',
                    's1_reduction_cost_cap_bps'}
    assert {k for k in set(p) | set(s2p) if p.get(k) != s2p.get(k)} == changed_keys | {'provenance'}
    # `baseline` and `s1` share the block's decision ID, which names FS1-R; the block bytes are S2's (same data hash).
    assert {k for k in p['provenance'] if p['provenance'][k] != s2p['provenance'].get(k)} == changed_keys | {'s1', 'baseline'}
    for key in ('s1', 'baseline'):
        assert {k for k in p['provenance'][key] if p['provenance'][key][k] != s2p['provenance'][key].get(k)} \
            == {'decision_id'}, key
    assert p['provenance']['s1']['data_hash'] == hashlib.sha256(BLOCK.read_bytes()).hexdigest()
    assert [p[k] for k in WINDOW] == S4R_WINDOW
    assert (p['slippage_bps'], p['policy_id']) == (20, 'larp-fs1-rehearsal-v1')
    assert p['s1'] == profile()['s1']
    assert (p['environment'], p['evidence_mode'], p['falsifier_authority']) == ('REHEARSAL', 'SHADOW', 'SHADOW')


def test_s4r_3_live_mode_and_final_are_refused():
    p = json.loads(REHEARSAL.read_bytes())
    assert rh.refusal(lambda: rh.prepared(p, runtime_mode='live')) == bounds.SCOPE
    assert rh.refusal(lambda: s2.build_runtime(REHEARSAL.read_bytes(), mode='live')) == bounds.SCOPE
    assert rh.refusal(lambda: validate_live(dict(p, environment='FINAL'))) in (bounds.SCOPE, rh.SCOPE)


def test_s4r_4_builder_refusals_and_s2_s3_unchanged():
    from tools.deploy.build_rehearsal_candidate import build
    value = json.loads(BLOCK.read_bytes())
    nyse = dict(value, execution={k: v for k, v in value['execution'].items() if k != 'hours'})
    with pytest.raises(ContractError):
        build(2, s1_raw=json.dumps(nyse).encode(), s1_decision='synthetic', fs1_rehearsal=True)
    with pytest.raises(ContractError):
        build(2, fs1_rehearsal=True)
    with pytest.raises(ContractError):
        rehearsal_build(fs1_rehearsal=True, scheduled_flatten_at='2026-10-26T00:00:00Z')
    s2raw = s2.PROFILE.read_bytes()
    assert build(2, s1_raw=s2.BLOCK.read_bytes(),
                 s1_decision=json.loads(s2raw)['provenance']['s1']['decision_id']).payload + b'\n' == s2raw
    s3 = ROOT / 'docs/build/evidence/s3-rehearsal-profile-20261024/rehearsal-s3-deterministic.json'
    s3raw = s3.read_bytes()
    assert build(2, s1_raw=s2.BLOCK.read_bytes(), s1_decision=json.loads(s3raw)['provenance']['s1']['decision_id'],
                 scheduled_flatten_at=json.loads(s3raw)['scheduled_flatten_at']).payload + b'\n' == s3raw


# --- FS1-2..FS1-6: the final live solution with AIand/ChatGPT routing ----------------------------------------------

ROUTING = ROOT / 'config/intelligence/aiand-routing.fs1.json'
REPAIR = ROOT / 'config/intelligence/aiand-routing.repair.example.json'


def live_prepared(p, routing=ROUTING, **changes):
    from unittest.mock import patch
    from tests.runtime.test_gate_a import assembled
    options = {} if routing is None else dict(model_routing_raw=routing.read_bytes(),
                                              model_routing_sha256=hashlib.sha256(routing.read_bytes()).hexdigest())
    from tests.marketdata.test_session_history import SEMANTICS
    options['token_history_raw'] = json.dumps(SEMANTICS).encode()
    options.update(changes)
    with patch('socket.create_connection', side_effect=AssertionError('no model/network')):
        return assembled(profile_raw=json.dumps(p).encode(), execution='service', runtime_mode='live',
                         adoption_ref='SYNTHETIC IDEA-093 FS1', **options)


def test_fs1_2_routing_is_the_v4_repair_without_the_trial_and_chatgpt_leads():
    from larp.intelligence.routing import validate_routing_spec
    spec = json.loads(ROUTING.read_bytes())
    validate_routing_spec(spec)
    repair = json.loads(REPAIR.read_bytes())
    assert 'openai_trial' in repair and 'openai_trial' not in spec
    assert spec == {k: v for k, v in repair.items() if k != 'openai_trial'}
    assert (spec['schema'], spec['openai_model']) == ('AIandRouting.v4', 'gpt-6.1-sol')
    assert [e['model_id'] for e in spec['external_reviewers']] == ['moonshotai/kimi-k3', 'zai-org/glm-5.3']
    pacing, p = spec['openai_pacing'], profile()
    assert pacing['start_ms'] <= milliseconds(p['trade_after']) and milliseconds(p['signing_end']) < pacing['end_ms']


def test_fs1_3_signed_live_preparation_with_routing_passes_the_gate_check():
    from larp.runtime import gate_a_check
    files = live_prepared(profile())
    values = {n: json.loads(raw) for n, raw in files.items() if n.endswith('.json')}
    runtime, report = values['runtime.json'], values['preparation-report.json']
    assert runtime['mode'] == 'live'
    assert (runtime['driver']['assessor'], runtime['driver']['execution']) == ('aiand_routed', 'service')
    assert runtime['driver']['model_routing_sha256'] == hashlib.sha256(ROUTING.read_bytes()).hexdigest()
    assert files['model-routing.json'] == ROUTING.read_bytes()
    assert report['model_routing']['routine'] == 'gpt-6.1-sol'
    assert values['strategy-profile.json'] == profile()
    gate_a_check.check_scope(values, report)
    gate_a_check.check_inputs(files, values)
    for routing in (None, REPAIR):  # no routing, or the v4 example that still carries the expired trial
        with pytest.raises(ContractError):
            live_prepared(profile(), routing=routing)


def test_fs1_4_runtime_starts_live_with_the_routed_assessor():
    from unittest.mock import patch
    from larp.intelligence.model_budget import ModelBudget
    from larp.intelligence.routing import RoutedAssessor
    from larp.runtime import gate_a
    from larp.runtime.service import build_driver
    from tests.runtime.test_driver import Composition, Store
    fixture = Composition(); fixture.setUp()
    try:
        raw = ROUTING.read_bytes()
        (fixture.root / 'routing.json').write_bytes(raw)
        spec = json.loads(raw)
        pacing = spec['openai_pacing']  # a paced (v3/v4) spec opens its ledger with the pacing total and no reserve
        ModelBudget.initialize(fixture.root / 'openai-budget.sqlite', spec['budget_account'],
                               initial_spent=pacing['prior_spent_micro_usd'], total=pacing['total_micro_usd'],
                               reserve=0, pacing=pacing)
        cfg = fixture.config(execution='service', intelligence_mode='live', expiry_grace_ms=5000,
                             assessor='aiand_routed', model_routing_file=str(fixture.root / 'routing.json'),
                             model_routing_sha256=hashlib.sha256(raw).hexdigest(),
                             model_budget_root=str(fixture.root), model_adoption_ref='SYNTHETIC IDEA-093 FS1')
        base = json.loads((gate_a.ROOT / 'config/runtime/runtime.example.json').read_bytes())['driver']
        for key in ('balance_check_interval_ms', 'balance_check_max_age_ms', 'price_jump_check_bps'):
            cfg['driver'][key] = base[key]
        cfg['driver']['balance_rpc_providers'] = [dict(url='https://rpc.invalid/', source_id='synthetic-rpc')]
        (fixture.root / 'profile.json').write_bytes(PROFILE.read_bytes())
        cfg['driver']['strategy_profile_sha256'] = gate_a.digest(PROFILE.read_bytes())
        from tests.marketdata.test_session_history import SEMANTICS
        history_raw = json.dumps(SEMANTICS).encode()
        (fixture.root / 'token-history.json').write_bytes(history_raw)
        cfg['driver'].update(token_history_file=str(fixture.root / 'token-history.json'),
                             token_history_sha256=hashlib.sha256(history_raw).hexdigest())
        cfg['mode'] = 'live'
        secrets = dict(fixture.secrets, LARP_AIAND_API_KEY='synthetic-aiand-runtime-key')
        with patch('socket.create_connection', side_effect=AssertionError('No network during construction')):
            runtime = build_driver(cfg, Store(), secrets)
        from larp.marketdata.history import SessionHistory
        assert isinstance(runtime.coordinator.context_builder.series, SessionHistory)
        runtime.ports['evidence'].close()
        from larp.runtime.driver import ServiceExecution
        assert isinstance(runtime.coordinator.assessor, RoutedAssessor)
        assert isinstance(runtime.execution, ServiceExecution)  # signing itself starts only at run activation
    finally:
        fixture.doCleanups()


def test_fs1_5_a_verified_model_assessed_4_02_finding_sells_the_name_at_the_weekend():
    """The assessment path FS1 uses (synthetic model in place of AIand): a verified Item 4.02 finding on a held name
    gives an EXIT target, and the planner makes it a mandatory SELL on a Saturday, under FS1's settings."""
    from dataclasses import replace as replaced
    from datetime import datetime, timedelta, timezone
    from larp.contracts import TargetKind
    from larp.integration.contract import build_evidence_context
    from larp.integration.runtime import ContextBuilder, initial_projection
    from larp.intelligence.agent import context_hash
    from larp.intelligence.gate import accept, consume, initial_state
    from larp.intelligence.scenarios import EXSEMI
    from larp.research.fixtures import snapshot
    from larp.risk.planner import plan
    from larp.strategy.policy import decide
    from larp.strategy.schema import instant
    from tests.intelligence.test_red_flags import Run
    p = profile()
    run = Run('RF1-4.02-SUPPORTED')
    original = run.state['context']
    result = run.assess('RF1-4.02-SUPPORTED')
    s = snapshot(held={'NVDAB': 2000}, now=instant('2026-10-10T14:00:00Z'), profile_changes={
        'baseline': p['baseline'], 's1': p['s1'], 'red_flag_policy': p['red_flag_policy'],
        'falsifier_ids': p['falsifier_ids'], 'red_flag_authority': p['red_flag_authority'],
        'evidence_mode': p['evidence_mode'], 'falsifier_authority': p['falsifier_authority']})
    now = datetime.fromtimestamp(result['completed_ms'] / 1000, timezone.utc)
    s = replaced(s, observed_at=now)
    result.update(run_id=s.run_id, policy_profile_hash=s.policy_profile_hash)
    state = dict(initial_state(EXSEMI, s.policy_profile_hash), context=original, context_hash=context_hash(original))
    decision, state = accept(state, Document.from_dict(result), profile_hash=s.policy_profile_hash,
                             now_ms=result['completed_ms'])
    assert decision == 'ACCEPT'
    record = build_evidence_context(consume(state, result['completed_ms']), state, run_id=s.run_id, token='NVDAB',
                                    underlying_id=EXSEMI, policy_profile_hash=s.policy_profile_hash)
    c = s.context.read()
    for m in c['markets']:
        m['observed_at'] = m['available_at'] = m['close_at'] = now.isoformat()
        if m['symbol'] == 'NVDAB':
            m['underlying_id'] = EXSEMI
    friday = (now - timedelta(days=1)).replace(hour=13, minute=30, second=0, microsecond=0)
    session = dict(index=c['session_index'], open_ms=int(friday.timestamp() * 1000),
                   close_ms=int((friday + timedelta(hours=6, minutes=30)).timestamp() * 1000),
                   next_open_ms=int((friday + timedelta(days=3)).timestamp() * 1000))
    assert session['close_ms'] < result['completed_ms'] < session['next_open_ms']  # after Friday's close
    s = changed(s, markets=c['markets'], assessments=[record], execution_session=session)
    proposal = decide(s, s.policy_state)
    assert next(t for t in proposal.targets if t.symbol == 'NVDAB').kind is TargetKind.EXIT
    builder = ContextBuilder(profile=c['profile'], profile_hash=s.policy_profile_hash, run_id=s.run_id, issuers={},
                             market=None, health=None, calendar=None, universe=s.universe)
    current = {'run_id': s.run_id, 'wallet_id': s.wallet_id, 'projection': initial_projection(c['portfolio']),
               'policy_state': s.policy_state.record(), 'reservations': []}
    reductions = builder._reductions([record], current, {'NVDAB': 2000}, c['markets'], result['completed_ms'])
    assert reductions == [{'symbol': 'NVDAB', 'max_units': 0, 'reason': 'CLASS_1_EXIT'}]
    planned = plan(with_quotes(changed(s, reduction_constraints=reductions)), None).read()
    assert (planned['intents'][0]['symbol'], planned['intents'][0]['side'], planned['intents'][0]['mandatory']) == (
        'NVDAB', 'SELL', True)


def test_fs1_6_install_refuses_a_wallet_holding_stock_and_fs1_has_no_scheduled_flatten():
    """S3 lesson 1 (IDEA-092 H1): a new run's install refuses any stock, so the final wallet must be stock-free at install
    and the scored run must stay one run; FS1 sells by rule and in the terminal flatten, never on a schedule."""
    from larp.runtime import gate_a
    from tests.runtime.test_gate_a import captured, rehash
    from larp.marketdata.port import TOKENS as CONTRACTS
    p = profile()
    assert 'scheduled_flatten_at' not in p
    flat = captured()
    state = gate_a.initial_state(flat, p, 'fs1-run')
    assert all(position['units'] == 0 for position in state['positions'].values())
    for symbol in sorted(CONTRACTS):
        held = captured()
        held['balances']['response']['data'][0]['tokenAssets'].append(
            dict(tokenContractAddress=CONTRACTS[symbol], rawBalance='1'))  # dust counts too (H2)
        rehash(held)
        with pytest.raises(ContractError):
            gate_a.initial_state(held, p, 'fs1-run')

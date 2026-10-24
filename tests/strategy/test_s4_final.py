"""IDEA-093 S4-1..S4-8: the final 24/7 profile (KIT_OPEN_STATE hours in a live FINAL). Synthetic ports; no keys or network."""
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
EVIDENCE = ROOT / 'docs/build/evidence/s4-final-profile-20261025'
BLOCK, PROFILE = EVIDENCE / 's4-block.json', EVIDENCE / 'final-s4.json'
WINDOW = ('trade_after', 'new_risk_end', 'flatten_start', 'signing_end')
PF04 = ['2026-10-29T14:00:00Z', '2026-11-09T21:00:00Z', '2026-11-10T19:00:00Z', '2026-11-11T14:45:00Z']
S4 = dict(s1=block(execution=dict(s2.EXECUTION, hours='KIT_OPEN_STATE')))
# A synthetic Friday session (open 13:30Z, close 20:00Z) whose next open is Monday 13:30Z: the weekend is one session.
FRIDAY_OPEN, FRIDAY_CLOSE, MONDAY_OPEN = '2026-10-09T13:30:00Z', '2026-10-09T20:00:00Z', '2026-10-12T13:30:00Z'
SATURDAY, SUNDAY = '2026-10-10T23:00:00Z', '2026-10-11T12:00:00Z'


def profile():
    return json.loads(PROFILE.read_bytes())


def final_scope(p=None):
    """A FINAL with the decided v1 scope and S4's hours (the committed profile unless given)."""
    return deepcopy(p or profile())


def weekend(value, profile_changes=S4):
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
        # S1's NYSE hours refuse the same snapshot (the S2-era limit S4 removes).
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
    late = run(weekend(SATURDAY, dict(S4, new_risk_end='2026-10-10T22:00:00Z')))
    assert not late['intents'] and not late['quote_requests'] and not late['execution_attempts']
    early = run(weekend(SATURDAY, dict(S4, trade_after='2026-10-11T00:00:00Z')))
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
    assert (p['slippage_bps'], p['policy_id']) == (20, 'larp-s4-final-v1')
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
    decided = {'trade_after', 'new_risk_end', 'flatten_start', 'slippage_bps', 'policy_id', 's1', 'exit_gas_reserve_units', 'provenance'}
    assert {k for k in set(p) | set(generated) if p.get(k) != generated.get(k)} == decided
    assert {k for k in p['s1'] if p['s1'][k] != generated['s1'][k]} == {'execution'}
    assert p['s1']['execution'] == dict(generated['s1']['execution'], hours='KIT_OPEN_STATE')
    # Two balanced exit children per position, as S2 (LD10-P03); the gas formulas as the rehearsal builder writes them.
    assert p['exit_gas_reserve_units'] == 10 * p['gas_action_budget_units'] > generated['exit_gas_reserve_units']
    assert {k for k in p['provenance'] if p['provenance'][k] != generated['provenance'][k]} == {
        *WINDOW, 'slippage_bps', 'policy_id', 's1', 'exit_gas_reserve_units',
        'gas_action_budget_units', 'gas_sizing_budget_units'}


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


# --- IDEA-093 S4R-1..S4R-4: the dev REHEARSAL with S4's settings ---------------------------------------------------

REHEARSAL = ROOT / 'docs/build/evidence/s4-rehearsal-profile-20261025/rehearsal-s4-deterministic.json'
S4R_WINDOW = ['2026-10-25T16:00:00Z', '2026-10-26T06:00:00Z', '2026-10-26T07:00:00Z', '2026-10-26T12:00:00Z']


def rehearsal_build(**options):
    from tools.deploy.build_rehearsal_candidate import build
    p = json.loads(REHEARSAL.read_bytes())
    return build(2, s1_raw=BLOCK.read_bytes(), s1_decision=p['provenance']['s1']['decision_id'], **options)


def test_s4r_1_rehearsal_rebuilds_and_passes_dev_preparation_and_runtime_build():
    raw = REHEARSAL.read_bytes()
    assert rehearsal_build(s4_rehearsal=True).payload + b'\n' == raw
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
    changed_keys = {*WINDOW, 'slippage_bps', 'policy_id'}
    assert {k for k in set(p) | set(s2p) if p.get(k) != s2p.get(k)} == changed_keys | {'provenance'}
    assert {k for k in p['provenance'] if p['provenance'][k] != s2p['provenance'][k]} == changed_keys
    assert [p[k] for k in WINDOW] == S4R_WINDOW
    assert (p['slippage_bps'], p['policy_id']) == (20, 'larp-s4-rehearsal-v1')
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
        build(2, s1_raw=json.dumps(nyse).encode(), s1_decision='synthetic', s4_rehearsal=True)
    with pytest.raises(ContractError):
        build(2, s4_rehearsal=True)
    with pytest.raises(ContractError):
        rehearsal_build(s4_rehearsal=True, scheduled_flatten_at='2026-10-26T00:00:00Z')
    s2raw = s2.PROFILE.read_bytes()
    assert build(2, s1_raw=s2.BLOCK.read_bytes(),
                 s1_decision=json.loads(s2raw)['provenance']['s1']['decision_id']).payload + b'\n' == s2raw
    s3 = ROOT / 'docs/build/evidence/s3-rehearsal-profile-20261024/rehearsal-s3-deterministic.json'
    s3raw = s3.read_bytes()
    assert build(2, s1_raw=s2.BLOCK.read_bytes(), s1_decision=json.loads(s3raw)['provenance']['s1']['decision_id'],
                 scheduled_flatten_at=json.loads(s3raw)['scheduled_flatten_at']).payload + b'\n' == s3raw

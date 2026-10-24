"""IDEA-092 S3-1..S3-7: S2 with a scheduled sell-all, then S2 again. Synthetic ports; no keys or network."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from larp.contracts import ContractError, Document
from larp.execution import USDT
from larp.marketdata.port import TOKENS
from larp.research.fixtures import changed, with_quotes
from larp.runtime import gate_a_check
from larp.strategy import execution_bounds as bounds, scheduled_flatten
from larp.strategy.profiles import validate_live
from tests.execution_fixtures import intent
from tests.strategy import test_s1_rehearsal as rh
from tests.strategy.test_execution_bounds import at, milliseconds, run
from tests.strategy.test_s1_plan import AT_95, NAMES
from tests.strategy.test_s2_weekend import (AFTER_CLOSE, BLOCK, EXECUTION, POLICY, PROFILE as S2_PROFILE, S2,
                                            build_runtime, s2_shadow)

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/build/evidence/s3-rehearsal-profile-20261024'
PROFILE = EVIDENCE / 'rehearsal-s3-deterministic.json'
PASSED, LATER = '2026-10-10T22:00:00Z', '2026-10-11T01:00:00Z'  # the synthetic round runs at 23:00Z
S3 = dict(S2, scheduled_flatten_at=PASSED)
HELD = dict(NVDAB=AT_95, SKHYB=AT_95)
EVER_HELD = dict(lifecycle={n: dict(status='CASH_REVIEW', last_review_session=80, ever_held=True,
                                    observed_session=80) for n in NAMES})


def legs(result):
    return sorted((i['symbol'], i['side'], i['mandatory'], i['pay_units']) for i in result['intents']), \
        sorted((q['symbol'], q['side']) for q in result['quote_requests'])


def reasons(result):
    return {r['reason'] for r in result['rejections']}


def round_at(profile_changes, **kwargs):
    return run(with_quotes(at(AFTER_CLOSE, profile_changes=profile_changes, **kwargs)))


def buys(result):
    return [i for i in result['intents'] if i['side'] == 'BUY'] + [
        q for q in result['quote_requests'] if q['side'] == 'BUY']


# --- S3-1: before the time S3 is S2 ----------------------------------------------------------------------------------

@pytest.mark.parametrize('held', [None, HELD])
def test_s3_1_before_the_time_plans_what_s2_plans(held):
    s2, s3 = round_at(S2, held=held), round_at(dict(S2, scheduled_flatten_at=LATER), held=held)
    assert legs(s3) == legs(s2) and reasons(s3) == reasons(s2)
    assert s3['requirements'] == s2['requirements']
    assert 'scheduled_flatten' not in s3['risk_state']
    if held is None:
        assert buys(s3)  # S2 buys before noon


# --- S3-2: from the time, every held name is sold first ---------------------------------------------------------------

def test_s3_2_every_held_name_is_a_mandatory_sell_and_nothing_is_bought():
    result = round_at(S3, held=HELD)
    assert {r['symbol']: r['reasons'] for r in result['requirements']} == {
        'NVDAB': ['SCHEDULED_FLATTEN'], 'SKHYB': ['SCHEDULED_FLATTEN']}
    assert result['intents'] and all((i['side'], i['mandatory']) == ('SELL', True) for i in result['intents'])
    assert not buys(result)
    assert 'scheduled_flatten' not in result['risk_state']
    # Unchanged S2 on the same book holds it.
    assert not round_at(S2, held=HELD)['requirements']


def test_s3_2_execution_admits_the_scheduled_sell_through_the_mandatory_lane():
    snapshot = with_quotes(at(AFTER_CLOSE, profile_changes=S3, held=HELD))
    result = run(snapshot)
    planned = result['intents'][0]
    assert planned['execution_bounds']['leg'] == 'SAFETY:SELL:' + planned['symbol']
    record = dict(policy_input=dict(context=snapshot.context.read()), plan=result)
    economic = intent(intent_id=planned['intent_id'], pay_token=TOKENS[planned['symbol']], receive_token=USDT,
                      amount=planned['pay_units'], minimum_output=planned['min_receive_units'] * 10**12)
    assert bounds.permitted(dict(round_records={'round': record}), economic, milliseconds(AFTER_CLOSE))


# --- S3-3: no buy while pending, even when the held name cannot be sold this round -----------------------------------

def test_s3_3_a_held_name_on_price_jump_hold_still_blocks_every_buy():
    hold = dict(price_jump_hold=dict(NVDAB=100_000_000))
    pending = round_at(S3, held=dict(NVDAB=AT_95), **hold)
    assert not pending['intents'] and not buys(pending)
    assert 'SCHEDULED_FLATTEN_PENDING' in reasons(pending)
    assert buys(round_at(S2, held=dict(NVDAB=AT_95), **hold))  # the S3 block is what stops them


def test_s3_3_reservations_and_balances_above_dust_keep_the_flatten_pending():
    p = dict(scheduled_flatten_at=PASSED, trade_after='2026-10-01T00:00:00Z', new_risk_end='2026-10-20T00:00:00Z')
    now = datetime(2026, 10, 10, 23, tzinfo=timezone.utc)
    flat = dict(positions=dict(NVDAB=dict(units=0)), reservations={})
    assert scheduled_flatten.state(p, {}, flat, now) == 'DONE'
    assert scheduled_flatten.state(p, {}, dict(flat, reservations=dict(r={})), now) == 'PENDING'
    assert scheduled_flatten.state(p, {}, dict(flat, positions=dict(NVDAB=dict(units=1))), now) == 'PENDING'
    assert scheduled_flatten.state(p, {}, flat, datetime(2026, 10, 10, 21, tzinfo=timezone.utc)) == 'BEFORE'
    assert scheduled_flatten.state({}, {}, flat, now) is None
    dusty = dict(flat, positions=dict(NVDAB=dict(units=5)))
    assert scheduled_flatten.state(dict(p, dust_units=5), {}, dusty, now) == 'DONE'
    assert scheduled_flatten.state(dict(p, dust_units=4), {}, dusty, now) == 'PENDING'


# --- S3-4: once flat, DONE is recorded and S2 rebuilds the book ------------------------------------------------------

def test_s3_4_flat_book_records_done_and_rebuys_names_held_before():
    result = round_at(S3, state=EVER_HELD)
    assert result['risk_state']['scheduled_flatten'] == 'DONE'
    assert buys(result) and 'SCHEDULED_FLATTEN_PENDING' not in reasons(result)
    # Without S3, or before its time, S1's re-entry rule keeps a name it held before in cash.
    for profile_changes in (S2, dict(S2, scheduled_flatten_at=LATER)):
        assert not buys(round_at(profile_changes, state=EVER_HELD))


# --- S3-5: DONE persists ----------------------------------------------------------------------------------------------

def test_s3_5_done_is_never_undone():
    result = round_at(S3, held=HELD, risk=dict(scheduled_flatten='DONE'))
    assert not any('SCHEDULED_FLATTEN' in r['reasons'] for r in result['requirements'])
    assert result['risk_state']['scheduled_flatten'] == 'DONE'
    assert legs(result) == legs(round_at(S2, held=HELD))


# --- S3-6: profile validation ----------------------------------------------------------------------------------------

def with_time(p, value):
    return dict(p, scheduled_flatten_at=value, provenance=dict(p['provenance'], scheduled_flatten_at=dict(
        decision_id='synthetic', formula='synthetic')))


def test_s3_6_validate_live_scope_and_time():
    p = s2_shadow()
    validate_live(p)
    window = [datetime.fromisoformat(p[k].replace('Z', '+00:00')) for k in ('trade_after', 'new_risk_end')]
    middle = (window[0] + (window[1] - window[0]) / 2).strftime('%Y-%m-%dT%H:%M:%SZ')
    validate_live(with_time(p, middle))
    for bad in ('noon', 12, p['trade_after'], p['new_risk_end'], p['signing_end']):
        assert rh.refusal(lambda: validate_live(with_time(p, bad))) in (
            'scheduled_flatten_at must be an ISO-8601 UTC instant',
            'scheduled_flatten_at must fall after trade_after and before new_risk_end'), bad
    with pytest.raises(ContractError):
        validate_live(with_time(p, None))  # unset live value
    for change in (dict(environment='FINAL'), dict(s1=rh.shadow(execution=EXECUTION)['s1'])):
        with pytest.raises(ContractError):
            validate_live(dict(with_time(p, middle), **change))
    assert rh.refusal(lambda: validate_live(with_time(rh.shadow(execution=EXECUTION), middle))) \
        == scheduled_flatten.SCOPE


# --- S3-7: the committed S3 profile ---------------------------------------------------------------------------------

def test_s3_7_profile_rebuilds_and_differs_from_s2_only_where_decided():
    from tools.deploy.build_rehearsal_candidate import S3_FLATTEN_AT, S3_POLICY_ID, build
    raw = PROFILE.read_bytes()
    p, s2 = json.loads(raw), json.loads(S2_PROFILE.read_bytes())
    rebuilt = build(2, s1_raw=BLOCK.read_bytes(), s1_decision=s2['provenance']['s1']['decision_id'],
                    scheduled_flatten_at=S3_FLATTEN_AT)
    assert rebuilt.payload + b'\n' == raw
    validate_live(p)
    assert {k for k in set(p) | set(s2) if p.get(k) != s2.get(k)} == {'scheduled_flatten_at', 'policy_id', 'provenance'}
    assert {k for k in set(p['provenance']) | set(s2['provenance'])
            if p['provenance'].get(k) != s2['provenance'].get(k)} == {'scheduled_flatten_at', 'policy_id'}
    assert (p['scheduled_flatten_at'], p['policy_id']) == ('2026-10-25T04:00:00Z', S3_POLICY_ID)
    assert p['trade_after'] < p['scheduled_flatten_at'] < p['new_risk_end']
    files = rh.prepared(p, **POLICY)
    values = {n: json.loads(v) for n, v in files.items() if n.endswith('.json')}
    gate_a_check.check_scope(values, values['preparation-report.json'])
    gate_a_check.check_inputs(files, values)
    build_runtime(raw)
    readme = (EVIDENCE / 'README.md').read_text()
    assert hashlib.sha256(raw).hexdigest() in readme
    assert Document.from_dict(p).digest('StrategyProfile.v1') in readme


def test_s3_7_builder_refuses_a_scheduled_flatten_without_s2_hours():
    from tools.deploy.build_rehearsal_candidate import build
    value = json.loads(BLOCK.read_bytes())
    del value['execution']['hours']
    value['execution']['max_attempts_per_leg_session'] = 3
    with pytest.raises(ContractError):
        build(2, s1_raw=json.dumps(value).encode(), s1_decision='synthetic', scheduled_flatten_at='2026-10-25T04:00:00Z')
    with pytest.raises(ContractError):
        build(2, scheduled_flatten_at='2026-10-25T04:00:00Z')

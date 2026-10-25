"""IDEA-102 MC1–MC6: mandatory retry authority; synthetic prices only."""
from copy import deepcopy
import pytest

from larp.research.fixtures import changed, with_quotes
from larp.strategy import execution_bounds as bounds, s1
from tests.strategy.test_execution_bounds import at, milliseconds, round_record, run

POLICY = 'MANDATORY_CADENCE_V1'
SLOT = 900_000
LEG = 'SAFETY:SELL:NVDAB'


def modern(snapshot):
    return changed(snapshot, execution_attempt_policy=POLICY)


def flatten(stamp='2026-10-10T14:00:00Z', **extra):
    return modern(at(stamp, held={'NVDAB': 2000}, profile_changes={
        'new_risk_end': '2026-10-10T12:00:00Z', 'flatten_start': '2026-10-10T13:00:00Z'}, **extra))


def test_mc1_sixth_mandatory_attempt_in_next_slot_is_planned():
    s = flatten(execution_attempt_budget=dict(session=80, counts={LEG: 5}, closed={LEG: 5},
        last_ms={LEG: milliseconds('2026-10-10T13:45:00Z')}))
    legacy = run(changed(s, execution_attempt_policy=None,
        execution_attempt_budget=dict(session=80, counts={LEG: 5}, closed={LEG: 5})))
    assert 'LEG_ATTEMPT_LIMIT' in {r['reason'] for r in legacy['rejections']}
    result = run(with_quotes(s))
    assert result['intents'], result
    assert result['intents'][0]['execution_bounds']['ordinal'] == 6


def test_mc2_same_slot_blocks_new_attempt_but_quote_child_reuses_parent():
    snapshot = flatten()
    parent_plan = run(snapshot)
    assert parent_plan['quote_requests']
    parent = bounds.parent_authority(dict(round_id='parent', policy_input=dict(context=snapshot.context.read()),
                                         plan=parent_plan))
    child = changed(with_quotes(snapshot), execution_attempt_budget=parent_plan['execution_attempt_budget'],
                    execution_parent=parent)
    result = run(child)
    assert result['intents'][0]['execution_bounds']['ordinal'] == 1
    retry = run(changed(child, execution_parent=None))
    assert not retry['intents'] and not retry['quote_requests']
    assert 'MANDATORY_RETRY_SPACING' in {r['reason'] for r in retry['rejections']}
    # Issuing an intent closes reuse, including an explicit stale-parent reference.
    retry = run(changed(child, execution_attempt_budget=result['execution_attempt_budget']))
    assert not retry['intents']
    assert 'MANDATORY_RETRY_SPACING' in {r['reason'] for r in retry['rejections']}


def test_mc2_spacing_uses_slot_boundaries_and_is_per_leg():
    snapshot = flatten('2026-10-10T14:14:59Z')
    context = snapshot.context.read()
    cfg = s1.config(context['profile'])
    state = bounds.budget(None, 80)
    first, refused = bounds.reserve(context, cfg, state, 'NVDAB', 'SELL', True, milliseconds('2026-10-10T14:14:59Z'))
    assert refused is None
    bounds.close(state, first)
    assert bounds.reserve(context, cfg, state, 'NVDAB', 'SELL', True, milliseconds('2026-10-10T14:14:59Z'))[1] == 'MANDATORY_RETRY_SPACING'
    second, refused = bounds.reserve(context, cfg, state, 'NVDAB', 'SELL', True, milliseconds('2026-10-10T14:15:00Z'))
    assert refused is None and second['ordinal'] == 2
    assert bounds.reserve(context, cfg, state, 'GOOGLB', 'SELL', True, milliseconds('2026-10-10T14:15:00Z'))[1] is None


@pytest.mark.parametrize('side', ['BUY', 'SELL'])
def test_mc3_discretionary_cap_is_unchanged(side):
    context = modern(at('2026-10-10T14:00:00Z')).context.read()
    cfg = s1.config(context['profile'])
    key = bounds.leg_key('NVDAB', side, False)
    state = dict(session=80, counts={key: 3}, closed={key: 3})
    assert bounds.reserve(context, cfg, state, 'NVDAB', side, False, milliseconds('2026-10-10T14:00:00Z'))[1] == 'LEG_ATTEMPT_LIMIT'


def test_mc4_execution_admits_above_cap_only_for_new_mandatory_authority():
    from tests.execution_fixtures import intent
    from larp.execution import USDT
    from larp.marketdata.port import TOKENS
    record = round_record(mandatory=True)
    record['policy_input']['context']['execution_attempt_policy'] = POLICY
    record['plan']['intents'][0]['execution_bounds']['ordinal'] = 6
    record['plan']['execution_attempt_budget'].update(counts={LEG: 6}, closed={LEG: 6})
    economic = intent(pay_token=TOKENS['NVDAB'], receive_token=USDT, minimum_output=90*10**12)
    now = milliseconds('2026-10-10T14:00:00Z')
    assert bounds.permitted(dict(round_records={'round': record}), economic, now)
    legacy = deepcopy(record)
    del legacy['policy_input']['context']['execution_attempt_policy']
    assert not bounds.permitted(dict(round_records={'round': legacy}), economic, now)
    discretionary = deepcopy(record)
    item = discretionary['plan']['intents'][0]
    item['mandatory'] = False
    item['execution_bounds']['leg'] = 'DISCRETIONARY:SELL:NVDAB'
    discretionary['plan']['execution_attempt_budget'].update(counts={'DISCRETIONARY:SELL:NVDAB': 6},
                                                            closed={'DISCRETIONARY:SELL:NVDAB': 6})
    assert not bounds.permitted(dict(round_records={'round': discretionary}), economic, now)
    for key, value in [('ordinal', 7), ('session_index', 81), ('valid_until_ms', now)]:
        bad = deepcopy(record)
        bad['plan']['intents'][0]['execution_bounds'][key] = value
        assert not bounds.permitted(dict(round_records={'round': bad}), economic, now)


def test_mc5_existing_integrity_gas_market_and_window_guards_still_apply():
    snapshot = with_quotes(flatten())
    assert run(snapshot)['intents']
    context = snapshot.context.read()
    cases = []
    for gate in ('integrity_ok', 'journal_ok', 'ownership_ok', 'clock_ok'):
        cases.append(changed(snapshot, health=dict(context['health'], **{gate: False})))
    ledger = deepcopy(context['portfolio'])
    ledger['bnb_units'] = 0
    cases.append(changed(snapshot, portfolio=ledger))
    cases.append(changed(snapshot, markets=[dict(m, token_open=False) for m in context['markets']]))
    cases.append(with_quotes(flatten('2026-10-27T14:00:00Z')))
    for candidate in cases:
        result = run(candidate)
        assert not result['intents'], result
        # New authority does not change the pre-existing blocking reason.
        old = run(changed(candidate, execution_attempt_policy=None))
        assert result['rejections'] == old['rejections']


def test_mc6_optional_last_ms_is_validated_even_when_session_rolls():
    now = milliseconds('2026-10-10T14:00:00Z')
    assert bounds.budget(dict(session=80, counts={}), 80) == dict(session=80, counts={}, closed={})
    base = dict(session=80, counts={}, closed={})  # a refund may remove a count but must keep spacing
    for bad in (None, [], {'invented': now}, {LEG: True}, {LEG: '1.5'}, {LEG: -1}, {LEG: now + 1}):
        snapshot = flatten(execution_attempt_budget=dict(base, last_ms=bad))
        result = run(snapshot)
        assert not result['intents'] and not result['quote_requests']
        assert 'EXECUTION_BOUNDS_INVALID' in {r['reason'] for r in result['rejections']}


def test_refunded_count_does_not_refund_mandatory_spacing():
    from larp.integration.settlement import refund_attempt
    now = milliseconds('2026-10-10T14:00:00Z')
    budget = dict(session=80, counts={LEG: 1}, closed={LEG: 1}, last_ms={LEG: now})
    projection = dict(execution_attempt_budget=budget)
    refund_attempt(projection, dict(execution_bounds=dict(session_index=80, leg=LEG, ordinal=1)))
    result = run(flatten(execution_attempt_budget=projection['execution_attempt_budget']))
    assert not result['quote_requests']
    assert 'MANDATORY_RETRY_SPACING' in {r['reason'] for r in result['rejections']}

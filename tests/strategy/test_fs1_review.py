"""IDEA-093 PR278-RV01: counterexamples and bounded proofs; synthetic inputs only."""
from copy import deepcopy
from itertools import product
import json

import pytest

from larp.contracts import ContractError, Document, TargetKind
from larp.research.fixtures import changed, with_quotes
from larp.risk.accounting import update_risk
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.schema import equity, value
from tests.strategy.test_s1_plan import AT_95, FALLING, NAMES, settled, snap
from tests.strategy.test_fs1_final import BLOCK, profile
from tests.strategy.test_equal_weight import with_state

OPTIONS = dict(run_halt_recovery_bps=500, s1_reduction_cost_cap_bps=50)


def recovered(*, nav=190_000_001, healthy=True, **context):
    s = snap(profile_changes=OPTIONS, risk=dict(run_halt=True, day_anchor_units=nav))
    c = s.context.read()
    c['portfolio']['cash_units'] = nav - 1_000_000
    c['health'].update(new_spending_ok=healthy, balances_ok=healthy)
    c.update(context)
    return changed(s, **c)


@pytest.mark.parametrize('nav,halt', [(183_999_999, True), (184_000_000, True),
    (189_999_999, True), (190_000_000, True), (190_000_001, False), (200_000_001, False)])
def test_recovery_strict_boundary_and_peak(nav, halt):
    s = recovered(nav=nav)
    r = plan(s, None).read()['risk_state']
    assert r['run_halt'] is halt
    assert r['peak_units'] == max(200_000_000, nav)


@pytest.mark.parametrize('gate', ['integrity_ok', 'journal_ok', 'ownership_ok', 'clock_ok',
                                 'new_spending_ok', 'balances_ok'])
def test_recovery_needs_every_health_gate(gate):
    s = recovered()
    c = s.context.read()
    for missing in (False, True):
        health = dict(c['health'])
        if missing:
            health.pop(gate)
        else:
            health[gate] = False
        assert plan(changed(s, health=health), None).read()['risk_state']['run_halt']


def test_recovery_never_clears_other_latches_and_is_profile_opt_in():
    s = recovered()
    c = s.context.read()
    c['portfolio']['risk'].update(daily_halt=True, deep_cut=True)
    r = plan(changed(s, **c), None).read()['risk_state']
    assert not r['run_halt'] and r['daily_halt'] and r['deep_cut']
    p = Document.from_dict(c['portfolio'])
    assert update_risk(p, now=s.observed_at, equity_units=200_000_000).read()['risk']['run_halt']


@pytest.mark.parametrize('defect', ['missing', 'stale', 'jump', 'pending', 'abnormal'])
def test_recovery_requires_complete_reconciled_unencumbered_valuation(defect):
    s = recovered()
    c = s.context.read()
    if defect in ('missing', 'stale', 'jump'):
        c['portfolio']['positions']['NVDAB']['units'] = 100
        c['portfolio']['cash_units'] -= 1_000_000
        if defect == 'missing':
            c['markets'] = [m for m in c['markets'] if m['symbol'] != 'NVDAB']
        elif defect == 'stale':
            next(m for m in c['markets'] if m['symbol'] == 'NVDAB')['observed_at'] = '2020-01-01T00:00:00Z'
        else:
            c['price_jump_hold'] = {'NVDAB': 100_000_000}
    elif defect == 'pending':
        c['portfolio']['reservations']['pending'] = dict(side='BUY', symbol='NVDAB', token_units=1,
                                                       cash_units=10_000, bnb_units=0)
    else:
        c['portfolio']['unreconciled_outcomes'] = {'bad': {}}
    assert plan(changed(s, **c), None).read()['risk_state']['run_halt']


def test_recovery_bounded_paths_preserve_hysteresis_after_serialization():
    """All 6^4 paths across trigger/recovery/peak boundaries against an independent finite-state oracle."""
    start = recovered().context.read()['portfolio']
    start['risk'].update(run_halt=False, daily_halt=False, deep_cut=False)
    now = recovered().observed_at
    for path in product((88, 92, 94, 95, 96, 101), repeat=4):
        state = Document.from_dict(start)
        peak, stopped, deep = 200_000_000, False, False
        for percent in path:
            nav = 2_000_000 * percent
            peak = max(peak, nav)
            if nav * 100 <= peak * 92:
                stopped = True
            elif nav * 100 > peak * 95:
                stopped = False
            deep |= nav * 100 <= peak * 88
            state = update_risk(state, now=now, equity_units=nav, recover_run_halt=True)
            state = Document.from_dict(json.loads(state.payload))  # restart's persisted bytes
            actual = state.read()['risk']
            assert (actual['peak_units'], actual['run_halt'], actual['deep_cut']) == (peak, stopped, deep)


def test_buy_cost_is_bounded_at_authorized_minimum_not_quoted_output():
    s = snap(profile_changes=dict(slippage_bps=20, cost_reserve_units=200_000))
    s = changed(s, markets=[m for m in s.context.read()['markets'] if m['symbol'] == 'NVDAB'])
    # At 30bp quoted spread, the additional 20bp authorized slippage plus gas exceeds 50bp.
    s = with_quotes(s, spread_bps=30)
    r = plan(s, decide(s, s.policy_state)).read()
    assert not r['intents']
    assert {'ENTRY_COST_CAP', 'COST_RESERVE_INSUFFICIENT'} & {v['reason'] for v in r['rejections']}


def test_every_accepted_buy_in_cost_grid_satisfies_exact_minimum_fill_bound():
    """Finite grid of spreads/slippage; cost is recomputed independently with integer rational arithmetic."""
    s = snap(profile_changes=dict(slippage_bps=20, cost_reserve_units=200_000))
    s = changed(s, markets=[m for m in s.context.read()['markets'] if m['symbol'] == 'NVDAB'])
    for spread in range(0, 61, 5):
        quoted = with_quotes(s, spread_bps=spread)
        last_admitted = True
        for slip in range(21):
            c = quoted.context.read()
            m = c['markets'][0]
            q = m['quotes'][0]
            q['min_receive_units'] = q['token_units'] * (10000 - slip) // 10000
            candidate = changed(quoted, markets=c['markets'])
            r = plan(candidate, decide(candidate, candidate.policy_state)).read()
            admitted = bool(r['intents'])
            assert not admitted or last_admitted  # worsening the minimum cannot restore acceptance
            last_admitted = admitted
            if admitted:
                mark = value(q['min_receive_units'], m)
                cost = max(0, q['cash_units'] - mark) + q['fee_units'] + q['gas_bnb_units']
                assert cost <= c['profile']['cost_reserve_units']
                assert cost * 10000 <= mark * 50


def reduced(**options):
    return snap({s: AT_95 for s in NAMES}, state=settled([19, 20]), path=FALLING,
                profile_changes=dict(OPTIONS, minimum_trade_units=18_637_000, cost_reserve_units=200_000,
                                     **options))


def test_small_level_reductions_execute_with_cost_gate_and_remain_pending_on_failure():
    s = reduced()
    proposal = decide(s, s.policy_state)
    assert all(t.kind is TargetKind.TARGET_WEIGHT and t.reason == 'S1_LEVEL_CHANGE' for t in proposal.targets)
    assert set(proposal.next_policy_state.data.read()['s1']['rebalance']) == set(NAMES)
    cheap = with_quotes(s)
    r = plan(cheap, decide(cheap, cheap.policy_state)).read()
    assert len(r['intents']) == 1
    i = r['intents'][0]
    assert i['side'] == 'SELL' and not i['mandatory']
    assert i['cash_units'] < 18_637_000
    costly = with_quotes(s, spread_bps=100)
    rejected = plan(costly, decide(costly, costly.policy_state)).read()
    assert not rejected['intents']
    assert 'S1_REDUCTION_COST_CAP' in {x['reason'] for x in rejected['rejections']}
    restarted = with_state(s, proposal.next_policy_state.data.read())
    again = decide(restarted, restarted.policy_state)
    assert set(again.next_policy_state.data.read()['s1']['rebalance']) == set(NAMES)


def test_reduction_option_does_not_create_drift_sales_or_lower_buy_minimum():
    s = snap({n: AT_95 for n in NAMES}, state=settled([19, 20]), profile_changes=OPTIONS)
    assert all(t.kind is TargetKind.KEEP_QUANTITY for t in decide(s, s.policy_state).targets)
    s = snap({n: 3000 for n in NAMES}, state=settled([19, 20]),
             profile_changes=dict(OPTIONS, minimum_trade_units=18_637_000))
    assert not plan(with_quotes(s), decide(s, s.policy_state)).read()['intents']


def test_final_and_rehearsal_carry_explicit_review_options():
    from tools.deploy.build_final_candidate import build
    from tools.deploy.build_rehearsal_candidate import build as rehearsal
    for p in (build(s1_raw=BLOCK.read_bytes(), s1_decision='synthetic').read(),
              rehearsal(2, s1_raw=BLOCK.read_bytes(), s1_decision='synthetic', fs1_rehearsal=True).read()):
        assert all(p[k] == v for k, v in OPTIONS.items())


@pytest.mark.parametrize('mutation', ['weights', 'limiter', 'attempts', 'reserve'])
def test_rehearsal_refuses_a_different_strategy(mutation):
    from tools.deploy.build_rehearsal_candidate import build
    block = json.loads(BLOCK.read_bytes())
    if mutation == 'weights':
        block['weights'].update(NVDAB=[3, 10], MSFTB=[1, 10])
    elif mutation == 'limiter':
        block['limiter_mode'] = 'MODEL'
    elif mutation == 'attempts':
        block['execution']['max_attempts_per_leg_session'] = 3
    with pytest.raises(ContractError):
        build(1 if mutation == 'reserve' else 2, s1_raw=json.dumps(block).encode(),
              s1_decision='synthetic', fs1_rehearsal=True)


@pytest.mark.parametrize('key,bad', [('run_halt_recovery_bps', 501), ('run_halt_recovery_bps', True),
                                   ('s1_reduction_cost_cap_bps', 51), ('s1_reduction_cost_cap_bps', True)])
def test_profile_options_cannot_loosen_the_decided_values(key, bad):
    from larp.strategy.profiles import validate_live
    p = profile()
    p[key] = bad
    p['provenance'][key] = dict(decision_id='synthetic', formula='synthetic')
    with pytest.raises(ContractError):
        validate_live(p)

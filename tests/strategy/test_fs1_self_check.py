"""IDEA-093 SC-2..SC-7, SC-9: the F-125 activation self-check (GAP-74). Synthetic snapshots; no keys or network.

One minimum-size BUY of one name before `trade_after`, a mandatory SELL of it, DONE once flat, then FS1 as usual in
the same run.
"""
from copy import deepcopy
import json

import pytest

from larp.contracts import ContractError, TargetKind
from larp.research.fixtures import changed, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.profiles import validate_live
from tests.strategy import test_s2_weekend as s2
from tests.strategy.test_execution_bounds import at, run
from tests.strategy.test_s1_core import block
from tests.strategy.test_s1_plan import NAMES

OPTIONS = dict(run_halt_recovery_bps=500, s1_reduction_cost_cap_bps=50, entry_cost_basis='AUTHORIZED_MINIMUM',
               s1_capital_basis='EXCLUDE_GAS')
SC = dict(symbol='SKHYB', buy_after='2026-10-10T00:00:00Z', buy_until='2026-10-10T20:00:00Z',
          flat_by='2026-10-10T23:00:00Z', pay_units=20_000_000)
KIT = dict(s2.EXECUTION, hours='KIT_OPEN_STATE')
BASE = dict(OPTIONS, s1=block(execution=KIT), trade_after='2026-10-11T00:00:00Z')
WITH = dict(BASE, activation_self_check=SC)
DURING, AFTER_FLAT_BY, SCORED = '2026-10-10T15:00:00Z', '2026-10-10T23:30:00Z', '2026-10-11T15:00:00Z'
HELD = {'SKHYB': 2000}  # 20 USDT at 100 USDT per token, 4 decimals


def at_time(value, profile_changes=WITH, **context):
    return at(value, profile_changes=profile_changes, **context)


def buys(result):
    return [i for i in result['intents'] if i['side'] == 'BUY']


def requirement(result, symbol):
    return next((r for r in result['requirements'] if r['symbol'] == symbol), None)


# --- SC-3: one minimum-size BUY of the self-check name before trade_after ------------------------------------------

def test_sc3_one_self_check_buy_before_trade_after_and_nothing_without_the_key():
    result = run(with_quotes(at_time(DURING)))
    [item] = buys(result)
    assert item['symbol'] == 'SKHYB' and not item['mandatory']
    assert 5_000_000 <= item['pay_units'] <= SC['pay_units'] + 100  # at least the minimum, about pay_units
    assert result['risk_state'].get('activation_self_check') is None  # not bought yet
    plain = run(with_quotes(at_time(DURING, BASE)))
    assert not plain['intents'] and not plain['quote_requests']


def test_sc3_nothing_is_bought_outside_the_buy_window_before_trade_after():
    for value in ('2026-10-09T23:00:00Z', '2026-10-10T20:00:00Z', '2026-10-10T22:00:00Z'):
        result = run(with_quotes(at_time(value)))
        assert not buys(result) and not result['quote_requests'], value


# --- SC-4: every other new-risk gate still applies -------------------------------------------------------------------

def test_sc4_other_new_risk_gates_still_stop_the_self_check_buy():
    for name, changes in (('run halt', dict(risk=dict(run_halt=True))),
                          ('daily halt', dict(risk=dict(daily_halt=True)))):
        result = run(with_quotes(at_time(DURING, **changes)))
        assert not buys(result), name
    snapshot = at_time(DURING)
    c = snapshot.context.read()
    c['health']['new_spending_ok'] = False
    assert not buys(run(with_quotes(changed(snapshot, health=c['health']))))
    markets = c['markets']
    for market in markets:
        market['token_open'] = False
    closed = run(with_quotes(changed(snapshot, markets=markets)))
    assert not buys(closed) and 'MARKET_CLOSED_OR_UNKNOWN' in {r['reason'] for r in closed['rejections']}
    costly = run(with_quotes(at_time(DURING), spread_bps=100))
    assert not buys(costly) and {'ENTRY_COST_CAP', 'COST_RESERVE_INSUFFICIENT'} & {r['reason'] for r in costly['rejections']}


# --- SC-5: once held, a mandatory SELL of the whole position ---------------------------------------------------------

def test_sc5_held_self_check_name_is_sold_whole_and_nothing_is_bought():
    result = run(with_quotes(at_time(DURING, held=HELD)))
    req = requirement(result, 'SKHYB')
    assert req is not None and 'ACTIVATION_SELF_CHECK' in req['reasons']
    assert (req['max_units'], req['remaining_sell_units']) == (0, 2000)
    sells = [i for i in result['intents'] if i['side'] == 'SELL']
    assert sells and sells[0]['symbol'] == 'SKHYB' and sells[0]['mandatory']
    assert not buys(result)
    assert result['risk_state']['activation_self_check'] == 'BOUGHT'


# --- SC-6: DONE once flat; FS1 then builds all five names, the self-check name included -----------------------------

def test_sc6_done_when_flat_and_the_scored_run_rebuys_the_self_check_name():
    done = run(with_quotes(at_time(DURING, risk=dict(activation_self_check='BOUGHT'))))
    assert done['risk_state']['activation_self_check'] == 'DONE'
    assert not buys(done)  # before trade_after, DONE buys nothing more
    held_before = {'lifecycle': {'SKHYB': dict(status='UNBUILT', last_review_session=80, ever_held=True,
                                               observed_session=80)}}
    s = at_time(SCORED, risk=dict(activation_self_check='DONE'), state=held_before)
    proposal = decide(s, s.policy_state)
    target = next(t for t in proposal.targets if t.symbol == 'SKHYB')
    assert target.kind is TargetKind.TARGET_WEIGHT, target
    lifecycle = proposal.next_policy_state.data.read()['lifecycle']['SKHYB']
    assert (lifecycle['ever_held'], lifecycle['self_check_cleared']) == (False, True)
    # The clearance is one-time: a later holding and sale of the same name keeps the normal re-entry rule.
    later = {'lifecycle': {'SKHYB': dict(lifecycle, ever_held=True)}}
    s = at_time(SCORED, risk=dict(activation_self_check='DONE'), state=later)
    again = next(t for t in decide(s, s.policy_state).targets if t.symbol == 'SKHYB')
    assert again.kind is TargetKind.KEEP_QUANTITY
    # Without the key the normal rule applies to a previously held name.
    s = at_time(SCORED, BASE, state=held_before)
    plain = next(t for t in decide(s, s.policy_state).targets if t.symbol == 'SKHYB')
    assert plain.kind is TargetKind.KEEP_QUANTITY


# --- SC-7: EXPIRED at flat_by; nothing is forced -----------------------------------------------------------------

def test_sc7_expired_at_flat_by_keeps_a_residual_and_forces_nothing():
    held = run(with_quotes(at_time(AFTER_FLAT_BY, held=HELD, risk=dict(activation_self_check='BOUGHT'))))
    assert held['risk_state']['activation_self_check'] == 'EXPIRED'
    req = requirement(held, 'SKHYB')
    assert req is None or 'ACTIVATION_SELF_CHECK' not in req['reasons']
    never = run(with_quotes(at_time(AFTER_FLAT_BY)))
    assert never['risk_state']['activation_self_check'] == 'EXPIRED' and not buys(never)
    expired = run(with_quotes(at_time(DURING, held=HELD, risk=dict(activation_self_check='EXPIRED'))))
    assert requirement(expired, 'SKHYB') is None or 'ACTIVATION_SELF_CHECK' not in requirement(
        expired, 'SKHYB')['reasons']


# --- SC-2 / SC-9: profile validation and the committed FS1 candidate ------------------------------------------------

def fs1():
    from tests.strategy.test_fs1_final import profile
    return profile()


def test_sc9_fs1_carries_the_self_check_and_validates():
    p = fs1()
    assert p['activation_self_check'] == dict(symbol='SKHYB', buy_after='2026-10-27T00:00:00Z',
        buy_until='2026-10-28T18:00:00Z', flat_by='2026-10-28T23:00:00Z', pay_units=32_000_000)
    assert p['provenance']['activation_self_check']['decision_id'].startswith('IDEA-093 SC')
    validate_live(p)


def test_sc2_validate_live_refuses_out_of_scope_or_malformed_self_checks():
    from larp.strategy import self_check
    p = fs1()
    sc = p['activation_self_check']
    bad = [dict(sc, symbol='AAPLB'), dict(sc, buy_after=sc['buy_until']), dict(sc, flat_by='2026-10-29T14:00:01Z'),
           dict(sc, buy_until=sc['flat_by'], flat_by=sc['buy_until']), dict(sc, pay_units=p['minimum_trade_units'] - 1),
           dict(sc, pay_units=p['per_trade_cap_units']), dict(sc, extra=1), dict(sc, pay_units='19010169'), None]
    for value in bad:
        with pytest.raises(ContractError):
            validate_live(dict(p, activation_self_check=value))
    from tests.strategy import test_fs1_final as final
    rehearsal = json.loads(final.REHEARSAL.read_bytes())
    rehearsal['activation_self_check'] = dict(sc, buy_after='2026-10-25T10:00:00Z', buy_until='2026-10-25T12:00:00Z',
                                              flat_by='2026-10-25T14:00:00Z')
    rehearsal['provenance']['activation_self_check'] = p['provenance']['activation_self_check']
    with pytest.raises(ContractError) as info:
        validate_live(rehearsal)
    assert str(info.value) == self_check.SCOPE

"""S5-COST01: cash cushion and economic cost admission are independent; synthetic ports only."""
from dataclasses import replace
from fractions import Fraction
import json

import pytest

from larp.contracts import ContractError, Document
from larp.research.fixtures import changed, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.profiles import validate_live
from tests.strategy.test_equal_weight import with_state
from tests.strategy.test_s1_plan import settled
from tests.strategy.test_s5_small_wallet import snapshot
from tests.strategy import test_s5_monday_flatten as s5


def reprofile(s, **changes):
    p = dict(s.context.read()['profile'], **changes)
    return replace(changed(s, profile=p), policy_profile_hash=Document.from_dict(p).digest('StrategyProfile.v1'))


def candidate(*, cushion=0, limit=400_000):
    s = with_state(snapshot(), settled([3, 5], trend='DOWN'))
    return reprofile(s, cost_reserve_units=cushion, discretionary_cost_limit_units=limit, initial_gas_only=True)


def quote(s, spread=100, impact=1):
    s = with_quotes(s, spread_bps=spread, gas=75_000_000_000_000)
    markets = s.context.read()['markets']
    for m in markets:
        for q in m['quotes']:
            q['impact_bps'] = impact
    return changed(s, markets=markets)


def result(s):
    return plan(s, decide(s, s.policy_state)).read()


def reasons(r):
    return {v['reason'] for v in r['rejections']}


def test_zero_cushion_admits_cost_above_old_ceiling_without_removing_cost_checks():
    old = quote(with_state(snapshot(), settled([3, 5], trend='DOWN')))
    assert not result(old)['intents']
    assert 'COST_RESERVE_INSUFFICIENT' in reasons(result(old))
    s = quote(candidate())
    r = result(s)
    assert len(r['intents']) == 1
    intent = r['intents'][0]
    # Authorized-minimum value, gas and cash are the same inputs the independent planner costs.
    m = next(m for m in s.context.read()['markets'] if m['symbol'] == intent['symbol'])
    mark = Fraction(intent['min_receive_units'] * m['price_units'], 10**m['decimals'])
    ledger = s.context.read()['portfolio']
    gas = Fraction(75_000_000_000_000 * ledger['bnb_price_units'], 10**ledger['bnb_decimals'])
    cost = max(0, intent['cash_units'] - mark) + intent['fee_units'] + gas
    assert 100_000 < cost < 400_000
    assert cost * 10000 <= mark * 200


def test_independent_absolute_percentage_impact_and_gas_guards_remain():
    tight = result(quote(candidate(limit=100_000)))
    assert not tight['intents'] and 'COST_RESERVE_INSUFFICIENT' in reasons(tight)
    over = result(quote(candidate(), spread=150))
    assert not over['intents'] and 'ENTRY_COST_CAP' in reasons(over)
    impact = result(quote(reprofile(candidate(), impact_bps=2), impact=3))
    assert not impact['intents'] and 'QUOTE_ROUTE_OR_SLIPPAGE' in reasons(impact)
    s = candidate()
    ledger = s.context.read()['portfolio']
    ledger['bnb_units'] = s.context.read()['profile']['exit_gas_reserve_units']
    equity = ledger['cash_units'] + ledger['bnb_units'] * ledger['bnb_price_units'] // 10**ledger['bnb_decimals']
    ledger['opening_equity_units'] = equity
    ledger['risk'].update(day_anchor_units=equity, peak_units=equity)
    low_gas = result(quote(changed(s, portfolio=ledger)))
    assert not low_gas['intents']
    assert reasons(low_gas) & {'INSUFFICIENT_GAS', 'CASH_OR_EXIT_RESERVE'}


def test_changing_cost_ceiling_does_not_change_capital_targets_or_quote_requests():
    low, high = candidate(limit=100_000), candidate(limit=400_000)
    assert decide(low, low.policy_state).targets == decide(high, high.policy_state).targets
    assert result(low)['quote_requests'] == result(high)['quote_requests']
    # The cushion itself still affects proportional stock capital.
    buffered = candidate(cushion=100_000)
    assert result(buffered)['quote_requests'][0]['pay_units'] < result(high)['quote_requests'][0]['pay_units']


def live_candidate():
    p = json.loads(s5.S5.read_bytes())
    p.update(cost_reserve_units=0, discretionary_cost_limit_units=400_000)
    p['provenance']['cost_reserve_units'] = dict(decision_id='S5-COST01 synthetic review example', formula='zero cash cushion')
    p['provenance']['discretionary_cost_limit_units'] = dict(decision_id='S5-COST01 synthetic review example', formula='separate 0.40USDT ceiling')
    return p


def test_live_opt_in_requires_provenance_and_changes_no_gas_parameters():
    p = live_candidate()
    validate_live(p)
    original = json.loads(s5.S5.read_bytes())
    for k in ('gas_action_budget_units', 'exit_gas_reserve_units', 'gas_sizing_budget_units', 'slippage_bps'):
        assert p[k] == original[k]
    del p['provenance']['discretionary_cost_limit_units']
    with pytest.raises(ContractError):
        validate_live(p)


@pytest.mark.parametrize('limit', [0, -1, True, None, '400000', 0.4])
def test_live_limit_must_be_a_positive_integer(limit):
    p = live_candidate()
    p['discretionary_cost_limit_units'] = limit
    with pytest.raises(ContractError):
        validate_live(p)


@pytest.mark.parametrize('changes', [dict(environment='FINAL'), dict(policy_id='larp-fs1-rehearsal-v1'),
    dict(initial_gas_only=False), dict(s5_entry_cost_cap_bps=50), dict(s1_capital_basis='TOTAL'),
    dict(entry_cost_basis='DISPLAYED'), dict(baseline='EQUAL_WEIGHT')])
def test_live_opt_in_cannot_escape_s5_initial_gas_scope(changes):
    p = dict(live_candidate(), **changes)
    with pytest.raises(ContractError):
        validate_live(p)


@pytest.mark.parametrize('spread,impact,expected', [(100, 1, None), (150, 1, 'ENTRY_COST_CAP'),
                                                   (100, 3, 'ENTRY_IMPACT_CAP')])
def test_live_planner_keeps_percentage_and_per_name_impact_checks(spread, impact, expected):
    s = quote(candidate(), spread=spread, impact=impact)
    c = s.context.read()
    p = live_candidate()
    p['impact_bps'] = 50  # exercise the stricter per-name median check independently
    c['health']['new_spending_ok'] = True
    for m in c['markets']:
        m.update(origin='WEB3_OPEN_API', source_id='WEB3')
        for q in m['quotes']:
            q['origin'] = 'WEB3_OPEN_API'
            q.pop('quoted_depth_units', None)
    s = replace(changed(s, profile=p, markets=c['markets'], health=c['health']),
                policy_profile_hash=Document.from_dict(p).digest('StrategyProfile.v1'))
    r = result(s)
    if expected is None:
        assert len(r['intents']) == 1
    else:
        assert not r['intents'] and expected in reasons(r)


def test_discretionary_ceiling_does_not_change_mandatory_exit_sizing():
    s, _ = s5.round_at('2026-10-27T11:00:00Z', held=dict(GOOGLB=1900, NVDAB=1900),
                      cash_units=s5.RUN6_CASH - 38_000_000, bnb_units=s5.RUN6_BNB, sizing=True)
    plans = [result(with_quotes(reprofile(s, cost_reserve_units=0, initial_gas_only=True,
              discretionary_cost_limit_units=limit))) for limit in (1, 400_000)]
    assert plans[0]['intents'] and all(i['mandatory'] for i in plans[0]['intents'])
    # Profile rebinding changes economic identity; quantities/authority remain the same.
    without_id = lambda intent: {k: v for k, v in intent.items() if k != 'intent_id'}
    assert [without_id(i) for i in plans[0]['intents']] == [without_id(i) for i in plans[1]['intents']]
    assert plans[0]['requirements'] == plans[1]['requirements']

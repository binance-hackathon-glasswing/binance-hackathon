"""IDEA-104 S5-SIZE01: small-wallet lots with unchanged measured/exact-quote safety gates.

Synthetic settlements and serialized policy reconstruction; no venue or wallet calls.
"""
from dataclasses import replace
from fractions import Fraction
import json

import pytest

from larp.contracts import ContractError, Document, PolicyState, Target, TargetKind
from larp.research.fixtures import changed, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from larp.strategy.profiles import validate_live
from larp.strategy.rehearsal_sizing import name_target, opening_cash_check
from larp.strategy.s1 import config
from tests.strategy import test_s5_monday_flatten as s5
from tests.strategy.test_equal_weight import with_state
from tests.strategy.test_s1_plan import settled


def profile():
    return json.loads(s5.S5.read_bytes())


def snapshot(cash=s5.RUN6_CASH):
    s, _ = s5.round_at('2026-10-26T16:00:00Z', cash_units=cash, bnb_units=s5.RUN6_BNB, sizing=True)
    markets = s.context.read()['markets']
    ledger = s.context.read()['portfolio']
    for m in markets:
        m['quotes'] = []
        # Production token precision: the legacy fixture's 0.01-USDT quantity ticks can themselves
        # consume the 0.10-USDT cost reserve when exact minimum output and measured gas are combined.
        m['decimals'] = 18
        ledger['positions'][m['symbol']]['decimals'] = 18
    return changed(s, markets=markets, portfolio=ledger)


def test_four_serialized_openings_fit_cash_and_never_sell_back_or_buy_a_fifth():
    s = snapshot()
    names = set()
    for _ in range(4):
        quoted = with_quotes(s, spread_bps=1, gas=75_000_000_000_000)
        proposal = decide(quoted, quoted.policy_state)
        result = plan(quoted, proposal).read()
        assert len(result['intents']) == 1, result['rejections']
        intent = result['intents'][0]
        assert intent['side'] == 'BUY' and intent['cash_units'] == 19_000_000
        assert intent['symbol'] not in names
        names.add(intent['symbol'])
        # Explicit synthetic finalized settlement; account for input cash, fees and native gas.
        ledger = quoted.context.read()['portfolio']
        ledger['cash_units'] -= intent['cash_units'] + intent['fee_units']
        ledger['bnb_units'] -= 75_000_000_000_000
        pos = ledger['positions'][intent['symbol']]
        pos['units'] += intent['token_units']
        pos['cost_basis_units'] += intent['cash_units']
        # Reconstruct immutable policy bytes as a new process would; no shared mutable state.
        record = json.loads(json.dumps(proposal.next_policy_state.record()))
        state = PolicyState(**dict(record, data=Document.from_dict(record['data'])))
        s = replace(changed(s, portfolio=ledger, execution_attempt_budget=result['execution_attempt_budget']),
                    policy_state=state)
        check = plan(s, decide(s, s.policy_state)).read()
        assert not [i for i in check['intents'] if i['side'] == 'SELL']
    final = plan(s, decide(s, s.policy_state)).read()
    assert not final['intents'] and not final['quote_requests']
    assert len(names) == 4 and s.context.read()['portfolio']['cash_units'] >= 5_373_047


def test_floor_preserves_exact_cost_gate_and_independent_name_cap():
    s = snapshot()
    costly = with_quotes(s, spread_bps=100, gas=75_000_000_000_000)
    refused = plan(costly, decide(costly, costly.policy_state)).read()
    assert not refused['intents']
    assert {r['reason'] for r in refused['rejections']} & {'ENTRY_COST_CAP', 'COST_RESERVE_INSUFFICIENT'}
    proposal = decide(s, s.policy_state)
    first = next(t.symbol for t in proposal.targets if t.kind is TargetKind.TARGET_WEIGHT)
    forged = replace(proposal, targets=tuple(
        Target(t.symbol, TargetKind.TARGET_WEIGHT, t.reason, Fraction(1)) if t.symbol == first
        else Target(t.symbol, TargetKind.KEEP_QUANTITY, 'FORGED_TEST_HOLD') for t in proposal.targets))
    bounded = plan(s, forged).read()
    assert bounded['quote_requests'] and all(q['pay_units'] <= 19_000_000 for q in bounded['quote_requests'])


@pytest.mark.parametrize('level,enabled', [(Fraction(3, 5), True), (Fraction(3, 10), True),
                                          (Fraction(19, 20), False)])
def test_floor_cannot_enlarge_reduced_targets(level, enabled):
    p, safe = profile(), 100_000_000
    cfg, scale = config(p), Fraction(4, 5)
    nominal = level * Fraction(1, 5) * scale
    assert name_target(p, cfg, nominal, level=level * scale, capital_scale=scale,
                       safe_equity=safe, enabled=enabled) == nominal


def test_down_level_planning_keeps_ordinary_targets_and_halts_still_refuse_buys():
    s = snapshot()
    down = with_state(s, settled([3, 5], trend='DOWN'))
    assert all(t.kind is TargetKind.KEEP_QUANTITY for t in decide(down, down.policy_state).targets)
    for flag in ('daily_halt', 'run_halt', 'deep_cut'):
        ledger = s.context.read()['portfolio']
        ledger['risk'][flag] = True
        halted = changed(s, portfolio=ledger)
        refused = plan(halted, decide(halted, halted.policy_state)).read()
        assert not refused['intents'] and not refused['quote_requests'], (flag, refused)


@pytest.mark.parametrize('cash', [0, 19_100_000, 60_000_000])
def test_preparation_refuses_unfundable_lots(cash):
    with pytest.raises(ContractError):
        opening_cash_check(profile(), cash)


def test_preparation_check_uses_cash_only_and_allows_recorded_wallet():
    result = opening_cash_check(profile(), s5.RUN6_CASH)
    assert result == dict(stock_capital_units=81_273_047, opening_lot_units=19_000_000,
                          maximum_opening_lots=4)
    baseline = decide(snapshot(), snapshot().policy_state)
    for bnb, price in ((0, 722_150_988), (s5.RUN6_BNB * 2, 722_150_988), (s5.RUN6_BNB, 1_444_301_976)):
        s = snapshot()
        ledger = s.context.read()['portfolio']
        ledger.update(bnb_units=bnb, bnb_price_units=price)
        proposal = decide(changed(s, portfolio=ledger), s.policy_state)
        targets = [t for t in proposal.targets if t.kind is TargetKind.TARGET_WEIGHT]
        assert len(targets) == 4 and sum(t.weight for t in targets) <= 1
        for target in targets:
            if target.kind is TargetKind.TARGET_WEIGHT:
                # E includes marked gas, but the target's cash notional stays exactly 19 USDT.
                E = ledger['cash_units'] + bnb * price // 10**18
                assert target.weight * (E - profile()['cost_reserve_units']) == 19_000_000
    assert baseline.targets


def test_health_and_terminal_requirements_are_not_bypassed():
    s = snapshot()
    health = dict(s.context.read()['health'], new_spending_ok=False)
    # LIVE-only spending health has separate end-to-end coverage; the fixture still checks the integrity halt.
    health['integrity_ok'] = False
    unhealthy = changed(s, health=health)
    result = plan(unhealthy, decide(unhealthy, unhealthy.policy_state)).read()
    assert not result['intents'] and not result['quote_requests']
    _, terminal = s5.round_at('2026-10-27T00:00:00Z', held=dict(GOOGLB=1900, NVDAB=1900),
                            cash_units=s5.RUN6_CASH - 38_000_000, bnb_units=s5.RUN6_BNB, sizing=True)
    assert terminal['requirements']
    assert terminal['intents'] and all(i['side'] == 'SELL' and i['mandatory'] for i in terminal['intents'])


@pytest.mark.parametrize('change', [dict(environment='FINAL'), dict(policy_id='larp-fs1-rehearsal-v1'),
    dict(s1_capital_basis='TOTAL'), dict(s5_entry_lot_units=True), dict(s5_entry_lot_units=20_000_000)])
def test_lot_opt_in_is_rejected_outside_exact_s5_scope(change):
    with pytest.raises(ContractError):
        validate_live(dict(profile(), **change))

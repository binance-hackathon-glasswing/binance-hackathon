"""IDEA-110 TS-1..TS-5: the temporary sub-1-USDT final-wallet self-check. Synthetic snapshots; no keys or network.

One self-check BUY below 1 USDT on its own 1000bp floor, then the mandatory SELL; no other BUY under the temp policy.
"""
from datetime import datetime, timezone
from fractions import Fraction
import json

import pytest

from larp.contracts import ContractError, Proposal, Target, TargetKind
from larp.research.fixtures import with_quotes
from larp.risk.planner import plan
from larp.strategy import self_check
from larp.strategy.policy import decide
from larp.strategy.profiles import validate_live
from tests.strategy import test_fs1_self_check as sc
from tests.strategy.test_execution_bounds import run
from tools.deploy.build_selfcheck_temp import PAY_UNITS, build
from tools.deploy.prepare_fs1 import PROFILE

NOW = datetime(2026, 10, 27, 18, 0, 30, tzinfo=timezone.utc)
FS1 = json.loads(PROFILE.read_bytes())
# The synthetic fixture prices BNB at 1 USDT (6 decimals), so gas units are USDT units: 0.054 USDT is 6% of 0.90.
GAS = 54_000
COSTS = dict(quote_cost_summary=FS1['quote_cost_summary'], gas_sizing_budget_units=FS1['gas_sizing_budget_units'])
TEMP_SC = dict(sc.SC, pay_units=PAY_UNITS)
TEMP = dict(sc.BASE, **COSTS, policy_id=self_check.TEMP_POLICY_ID, activation_self_check=TEMP_SC,
            **{self_check.TEMP_COST_KEY: self_check.TEMP_COST_CAP_BPS})


def temp_at(value, profile_changes=TEMP, **context):
    return sc.at_time(value, profile_changes, **context)


def buys(result):
    return [i for i in result['intents'] if i['side'] == 'BUY']


def reasons(result):
    return {r['reason'] for r in result['rejections']}


# --- TS-1: the generator ---------------------------------------------------------------------------------------------

def test_w2_1_generator_gives_the_fixed_window_whenever_prepared():
    p = build(fs1_raw=PROFILE.read_bytes(), now=NOW).read()
    validate_live(p)
    assert p['activation_self_check'] == dict(symbol='SKHYB', pay_units=900_000, buy_after='2026-10-28T07:00:00Z',
        buy_until='2026-10-28T08:30:00Z', flat_by='2026-10-28T08:45:00Z')
    assert (p['trade_after'], p['new_risk_end'], p['flatten_start'], p['signing_end']) == (
        '2026-10-28T08:45:00Z', '2026-10-28T08:46:00Z', '2026-10-28T08:46:00Z', '2026-10-28T09:30:00Z')
    later = datetime(2026, 10, 28, 8, 29, 59, tzinfo=timezone.utc)
    assert build(fs1_raw=PROFILE.read_bytes(), now=later).payload == build(fs1_raw=PROFILE.read_bytes(), now=NOW).payload
    assert p['policy_id'] == self_check.TEMP_POLICY_ID and p[self_check.TEMP_COST_KEY] == 1000
    assert self_check.temp_floor(p) == 588_951
    changed = {k for k in set(p) | set(FS1) if p.get(k) != FS1.get(k)}
    assert changed == {'activation_self_check', 'policy_id', self_check.TEMP_COST_KEY, 'trade_after', 'new_risk_end',
                       'flatten_start', 'signing_end', 'provenance'}
    assert all(p['provenance'][k]['decision_id'].startswith('IDEA-110') for k in changed - {'provenance'})


def test_w2_1_generator_refuses_other_sources_and_a_closed_window():
    with pytest.raises(ContractError, match='reviewed FS1'):
        build(fs1_raw=PROFILE.read_bytes() + b' ', now=NOW)
    for late in ('2026-10-28T08:30:00Z', '2026-10-28T09:00:00Z'):
        with pytest.raises(ContractError, match='window closed'):
            build(fs1_raw=PROFILE.read_bytes(), now=late)


# --- TS-2: validation scope ------------------------------------------------------------------------------------------

def test_ts2_validate_live_refuses_out_of_scope_temp_profiles():
    p = build(fs1_raw=PROFILE.read_bytes(), now=NOW).read()
    floor = self_check.temp_floor(p)
    check = p['activation_self_check']
    bad = [dict(p, activation_self_check=dict(check, pay_units=1_000_000)),
           dict(p, activation_self_check=dict(check, pay_units=floor - 1)),
           dict(p, signing_end='2026-10-28T10:00:01Z'),
           dict(p, **{self_check.TEMP_COST_KEY: 999}), dict(p, **{self_check.TEMP_COST_KEY: 1500}),
           dict(p, **{self_check.TEMP_COST_KEY: '1000'}),
           dict(p, policy_id='larp-fs1-final-v1'),  # the key on FS1
           dict(p, environment='REHEARSAL'),
           {k: v for k, v in p.items() if k != 'activation_self_check'}]
    for value in bad:
        with pytest.raises(ContractError):
            validate_live(value)
    s5 = json.loads((PROFILE.parents[1] / 's5-rehearsal-profile-20261026/rehearsal-s5.json').read_bytes())
    with pytest.raises(ContractError):
        validate_live(dict(s5, **{self_check.TEMP_COST_KEY: 1000},
                           provenance=dict(s5['provenance'], **{self_check.TEMP_COST_KEY: p['provenance'][
                               self_check.TEMP_COST_KEY]})))
    validate_live(FS1)  # FS1 unchanged


# --- TS-3: one sub-1-USDT BUY on its own floor -----------------------------------------------------------------------

def test_ts3_one_self_check_buy_under_one_usdt_at_six_percent_gas():
    result = run(with_quotes(temp_at(sc.DURING), gas=GAS))
    [item] = buys(result)
    assert item['symbol'] == 'SKHYB' and not item['mandatory'] and item['reasons'] == ['ACTIVATION_SELF_CHECK_BUY']
    assert self_check.temp_floor(dict(TEMP)) <= item['cash_units'] + item['fee_units'] < 1_000_000
    assert len(result['intents']) == 1


def test_ts3_the_same_buy_without_the_temp_policy_is_refused_on_entry_cost():
    plain = dict(sc.WITH, **COSTS, minimum_trade_units=500_000, activation_self_check=TEMP_SC)
    result = run(with_quotes(temp_at(sc.DURING, plain), gas=GAS))
    assert not buys(result) and 'ENTRY_COST_CAP' in reasons(result)


def test_ts3_temp_floor_and_cap_still_refuse_a_costlier_buy():
    result = run(with_quotes(temp_at(sc.DURING), gas=100_000))  # about 11%: above the 1000bp cap
    assert not buys(result) and {'ENTRY_COST_CAP', 'COST_RESERVE_INSUFFICIENT'} & reasons(result)


# --- TS-4: nothing else is ever bought ------------------------------------------------------------------------------

def test_ts4_no_buy_outside_the_buy_phase_or_after_the_self_check():
    for value, risk in (('2026-10-11T00:00:30Z', {}),  # the S1 window after flat_by
                        (sc.SCORED, {}), (sc.DURING, dict(activation_self_check='BOUGHT')),
                        (sc.DURING, dict(activation_self_check='DONE')), ('2026-10-10T20:30:00Z', {})):
        result = run(with_quotes(temp_at(value, risk=risk), gas=GAS))
        assert not buys(result), (value, risk)


def forge(s):
    honest = decide(s, s.policy_state)
    targets = tuple(t for t in honest.targets if t.symbol != 'NVDAB')
    return Proposal(honest.snapshot_id, honest.policy_id, honest.valid_until,
                    targets + (Target('NVDAB', TargetKind.TARGET_WEIGHT, 'S1_TOP_UP', Fraction(1, 5)),),
                    honest.next_policy_state)


@pytest.mark.parametrize('value,risk', [(sc.DURING, {}), ('2026-10-11T00:00:30Z', dict(activation_self_check='DONE'))])
def test_ts4_a_forged_s1_target_on_another_name_is_rejected_by_the_planner(value, risk):
    s = temp_at(value, risk=risk)
    result = plan(s, forge(s)).read()
    assert 'NVDAB' not in {i['symbol'] for i in buys(result)}
    assert {'symbol': 'NVDAB', 'reason': 'TEMP_SELF_CHECK_ONLY'} in result['rejections']
    assert not result['quote_requests'] or {r['symbol'] for r in result['quote_requests']} <= {'SKHYB'}


def test_ts4_policy_never_proposes_s1_risk_in_its_window():
    s = temp_at('2026-10-11T00:00:30Z', risk=dict(activation_self_check='DONE'))
    targets = decide(s, s.policy_state).targets
    assert all(t.kind is not TargetKind.TARGET_WEIGHT or t.weight == 0 for t in targets)


# --- TS-5: the sell -------------------------------------------------------------------------------------------------

def test_ts5_held_position_is_sold_whole_then_terminal_flatten_covers_a_residual():
    result = run(with_quotes(temp_at(sc.DURING, held=sc.HELD), gas=GAS))
    sells = [i for i in result['intents'] if i['side'] == 'SELL']
    assert sells and sells[0]['symbol'] == 'SKHYB' and sells[0]['mandatory'] and not buys(result)
    late = run(with_quotes(temp_at('2026-11-02T00:30:00Z', held=sc.HELD,
                                   risk=dict(activation_self_check='EXPIRED')), gas=GAS))
    req = sc.requirement(late, 'SKHYB')
    assert req is not None and 'TERMINAL_FLATTEN' in req['reasons'] and not buys(late)

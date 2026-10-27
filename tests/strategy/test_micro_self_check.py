"""IDEA-110 MSC-1..MSC-7: the micro activation self-check (a sub-1-USDT BUY, then the mandatory SELL).

Synthetic snapshots; no keys or network. Same fixture as the IDEA-093 SC tests: 100 USDT per token, 4 decimals.
"""
from fractions import Fraction
import json
from pathlib import Path

import pytest

from larp.contracts import ContractError
from larp.research.fixtures import with_quotes
from larp.strategy import self_check
from larp.strategy.profiles import validate_live
from tests.strategy import test_fs1_self_check as sc
from tests.strategy.test_execution_bounds import run

MICRO = dict(sc.SC, pay_units=900_000, max_cost_units=50_000)
WITH = dict(sc.BASE, activation_self_check=MICRO)
SMALL_HELD = {'SKHYB': 90}  # 0.9 USDT at 100 USDT per token


def at_time(value, profile_changes=WITH, **context):
    return sc.at(value, profile_changes=profile_changes, **context)


def reasons(result):
    return {r['reason'] for r in result['rejections']}


def gas_wei_for(snapshot, usdt_units):
    """BNB wei whose value at the snapshot's BNB price is `usdt_units` USDT micro-units."""
    portfolio = snapshot.context.read()['portfolio']
    return int(Fraction(usdt_units) * 10**portfolio['bnb_decimals'] / portfolio['bnb_price_units'])


# --- MSC-3: one sub-1-USDT BUY in the window; nothing outside it ---------------------------------------------------

def test_msc3_one_micro_buy_in_the_window():
    result = run(with_quotes(at_time(sc.DURING)))
    [item] = sc.buys(result)
    assert item['symbol'] == 'SKHYB' and not item['mandatory']
    assert 0 < item['pay_units'] <= MICRO['pay_units'] < 1_000_000
    assert not {'MINIMUM_TRADE', 'DUST_OR_MINIMUM_TRADE', 'ENTRY_COST_CAP'} & reasons(result)


def test_msc3_nothing_is_bought_outside_the_window():
    for value in ('2026-10-09T23:00:00Z', '2026-10-10T20:00:00Z', '2026-10-10T22:00:00Z'):
        result = run(with_quotes(at_time(value)))
        assert not sc.buys(result) and not result['quote_requests'], value


# --- MSC-4: an absolute cost cap; the other gates still stop it ----------------------------------------------------

def test_msc4_cost_above_max_cost_units_is_refused():
    snapshot = at_time(sc.DURING)
    costly = run(with_quotes(snapshot, gas=gas_wei_for(snapshot, MICRO['max_cost_units'] + 10_000)))
    assert not sc.buys(costly) and 'SELF_CHECK_COST_CAP' in reasons(costly)
    cheap = run(with_quotes(snapshot, gas=gas_wei_for(snapshot, MICRO['max_cost_units'] // 2)))
    assert len(sc.buys(cheap)) == 1


def test_msc4_halts_health_and_closed_markets_still_stop_the_micro_buy():
    from larp.research.fixtures import changed
    for changes in (dict(risk=dict(run_halt=True)), dict(risk=dict(daily_halt=True))):
        assert not sc.buys(run(with_quotes(at_time(sc.DURING, **changes)))), changes
    snapshot = at_time(sc.DURING)
    c = snapshot.context.read()
    c['health']['new_spending_ok'] = False
    assert not sc.buys(run(with_quotes(changed(snapshot, health=c['health']))))
    for market in c['markets']:
        market['token_open'] = False
    closed = run(with_quotes(changed(snapshot, markets=c['markets'])))
    assert not sc.buys(closed) and 'MARKET_CLOSED_OR_UNKNOWN' in reasons(closed)


# --- MSC-5: ordinary buys keep the minimum trade and the bps entry cap ---------------------------------------------

def test_msc5_the_exemption_is_only_for_the_self_check_buy():
    from dataclasses import replace
    from larp.risk.planner import plan
    from larp.strategy.policy import decide
    snapshot = with_quotes(at_time(sc.DURING))
    proposal = decide(snapshot, snapshot.policy_state)
    relabelled = replace(proposal, targets=tuple(
        replace(t, reason='S1_TOP_UP') if t.reason == 'ACTIVATION_SELF_CHECK_BUY' else t for t in proposal.targets))
    result = plan(snapshot, relabelled).read()
    assert not sc.buys(result) and {'MINIMUM_TRADE', 'DUST_OR_MINIMUM_TRADE'} & reasons(result)
    # Without max_cost_units the bps entry-cost cap still governs the self-check BUY (IDEA-093 SC-4).
    costly = run(with_quotes(sc.at_time(sc.DURING), spread_bps=100))
    assert not sc.buys(costly) and {'ENTRY_COST_CAP', 'COST_RESERVE_INSUFFICIENT'} & reasons(costly)


# --- MSC-6: the mandatory SELL of the whole position, then DONE ----------------------------------------------------

def test_msc6_held_micro_position_is_sold_whole_then_done():
    result = run(with_quotes(at_time(sc.DURING, held=SMALL_HELD)))
    req = sc.requirement(result, 'SKHYB')
    assert req is not None and 'ACTIVATION_SELF_CHECK' in req['reasons']
    assert (req['max_units'], req['remaining_sell_units']) == (0, 90)
    [sell] = [i for i in result['intents'] if i['side'] == 'SELL']
    assert sell['symbol'] == 'SKHYB' and sell['mandatory'] and not sc.buys(result)
    assert result['risk_state']['activation_self_check'] == 'BOUGHT'
    done = run(with_quotes(at_time(sc.DURING, risk=dict(activation_self_check='BOUGHT'))))
    assert done['risk_state']['activation_self_check'] == 'DONE' and not sc.buys(done)


# --- MSC-1 / MSC-2 / MSC-7: validation and the committed candidates ------------------------------------------------

def test_msc2_validation():
    p = sc.fs1()
    base = dict(p['activation_self_check'], pay_units=900_000)
    with pytest.raises(ContractError):
        validate_live(dict(p, activation_self_check=base))  # below the minimum without max_cost_units
    for bad in (0, -1, 1.5, '100000', True, p['cost_reserve_units'] + 1):
        with pytest.raises(ContractError):
            validate_live(dict(p, activation_self_check=dict(base, max_cost_units=bad)))
    validate_live(dict(p, activation_self_check=dict(base, max_cost_units=p['cost_reserve_units'])))
    assert self_check.config(dict(p, activation_self_check=dict(base, max_cost_units=1)))['max_cost_units'] == 1
    assert 'max_cost_units' not in self_check.config(p)


FS1 = Path('docs/build/evidence/fs1-final-20261025')


def build(**options):
    from tools.deploy.build_final_candidate import build as candidate
    decision = (FS1 / 'README.md').read_text().split('--s1-decision "', 1)[1].split('"', 1)[0]
    return candidate(s1_raw=(FS1 / 'fs1-block.json').read_bytes(), s1_decision=decision, **options)


def test_msc1_msc7_builders_reproduce_and_the_micro_variant_differs_only_in_the_self_check():
    assert build().payload + b'\n' == (FS1 / 'fs1-final.json').read_bytes()
    recovery = build(allowance_recovery=True)
    assert recovery.payload + b'\n' == (FS1 / 'fs1-final-recovery.json').read_bytes()
    micro = build(allowance_recovery=True, micro_self_check=True)
    assert micro.payload == build(allowance_recovery=True, micro_self_check=True).payload
    committed = Path('docs/build/evidence/fs1-micro-self-check-20261028/fs1-final-recovery-micro.json')
    assert micro.payload + b'\n' == committed.read_bytes()
    a, b = json.loads(recovery.payload), json.loads(micro.payload)
    assert {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)} == {'activation_self_check', 'provenance'}
    assert {k for k in a['provenance'] if a['provenance'][k] != b['provenance'][k]} == {'activation_self_check'}
    assert b['activation_self_check'] == dict(symbol='SKHYB', buy_after='2026-10-27T17:00:00Z',
        buy_until='2026-10-28T08:00:00Z', flat_by='2026-10-28T09:30:00Z', pay_units=900_000, max_cost_units=150_000)
    validate_live(b)

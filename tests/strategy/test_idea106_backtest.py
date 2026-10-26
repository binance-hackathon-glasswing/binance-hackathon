"""IDEA-106 S6-B0: the S6 backtest simulator is point in time and charges the hand-computed costs. No network."""
from datetime import date, datetime, timedelta
import math

import pytest

from tools.idea106 import simulate as sim

HOUR = 3_600_000


def weekdays(start, n):
    out, d = [], date.fromisoformat(start)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def tokens(sessions, price):
    """24/7 hourly OPEN-labelled bars from the day before the first session; close = price(name, bar start ms)."""
    first = int(datetime.fromisoformat(sessions[0] + 'T00:00').replace(tzinfo=sim.ET).timestamp() * 1000) - 24 * HOUR
    last = int(datetime.fromisoformat(sessions[-1] + 'T23:00').replace(tzinfo=sim.ET).timestamp() * 1000)
    return {k: [[str(price(k, m)), str(price(k, m)), str(price(k, m)), str(price(k, m)), '1', m, 1]
                for m in range(first, last, HOUR)] for k in sim.NAMES}


def et_ms(day, hm):
    return int(datetime.fromisoformat(f'{day}T{hm}').replace(tzinfo=sim.ET).timestamp() * 1000)


def test_b0_fill_and_close_use_only_bars_ending_by_their_decision_time():
    sessions = weekdays('2026-03-02', 30)  # spans the US DST change on Mar 8
    market = sim.token_market(tokens(sessions, lambda k, m: m / HOUR), sessions)
    for t, d in enumerate(market.sessions):
        fill_ms, fill_px = market.fills[t]
        assert fill_ms == et_ms(d, '11:00')  # the bar starting at open + 30 min closes at 11:00 ET
        assert all(fill_px[k] == et_ms(d, '10:00') / HOUR for k in sim.NAMES)
        assert all(market.closes[t][k] == et_ms(d, '15:00') / HOUR for k in sim.NAMES)  # last bar ending 16:00 ET
        if t:
            assert et_ms(market.sessions[t - 1], '16:00') < fill_ms  # signal at t-1 close trades at fill t
            assert all(ms < fill_ms for ms, _ in market.marks[t])
    assert market.fallbacks == dict(next_bar=0, session_close=0)


def test_b0_scores_never_read_a_later_close():
    sessions = weekdays('2026-03-02', 30)
    market = sim.token_market(tokens(sessions, lambda k, m: 100.0), sessions)
    before = sim.scores(market, 15, 10, sim.NAMES)
    market.closes[16] = {k: 1e9 for k in sim.NAMES}  # a later close changes nothing at t = 15
    assert sim.scores(market, 15, 10, sim.NAMES) == before


def test_b0_flat_prices_give_the_hand_computed_costs():
    sessions = weekdays('2026-03-02', 30)
    market = sim.token_market(tokens(sessions, lambda k, m: 100.0), sessions)
    bps, gas = sim.COSTS['central']
    fs1 = sim.run_window(market, 12, sim.static(sim.NAMES), sim.COSTS['central'])
    expected = sum(2 * (38.0 * bps[k] / 10_000 + gas) for k in sim.NAMES)  # five one-leg buys and five sells
    assert fs1['cost'] == pytest.approx(expected, rel=1e-9)
    assert fs1['ret'] == pytest.approx(-expected / 200, rel=1e-9)
    assert fs1['swaps'] == 0 and fs1['max_dd'] < 0.01
    s6 = sim.run_window(market, 12, sim.s6(), sim.COSTS['central'])
    assert s6['swaps'] == 0  # flat prices: no score gap above the margin
    held = sorted(sim.NAMES)[:3]  # ties broken by name
    position = 200 * 0.95 / 3
    expected = sum(2 * (position * bps[k] / 10_000 + 2 * gas) for k in held)  # two legs each way
    assert s6['cost'] == pytest.approx(expected, rel=1e-6)
    assert s6['min_leg'] == pytest.approx(position / 2)


def test_s6_swaps_into_a_rising_outsider_within_its_budget_and_legs():
    sessions = weekdays('2026-03-02', 40)
    start = et_ms(sessions[15], '16:00')

    def price(k, m):
        if k == 'TSLAB' and m > start:
            return 100.0 * math.exp(0.004 * (m - start) / HOUR)  # strong rally after session 15's close
        return 100.0
    market = sim.token_market(tokens(sessions, price), sessions)
    result = sim.run_window(market, 13, sim.s6(), sim.COSTS['central'])
    assert 1 <= result['swaps'] <= 6
    assert result['min_leg'] >= sim.MIN_TRADE
    assert result['swap_excess']  # each swap is evaluated against its cost + 50 bp


def test_ladder_cut_on_a_crash_blocks_further_buys():
    sessions = weekdays('2026-03-02', 40)
    crash = et_ms(sessions[16], '12:00')
    market = sim.token_market(tokens(sessions, lambda k, m: 100.0 if m < crash else 70.0), sessions)
    result = sim.run_window(market, 13, sim.static(sim.NAMES), sim.COSTS['central'])
    assert result['max_dd'] >= 0.12
    assert result['ret'] < -0.25

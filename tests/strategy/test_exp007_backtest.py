"""EXP-007 simulator: point-in-time inputs, the TRV-04 fill rule, hand-computed costs and the frozen rule. No network."""
from datetime import date, datetime, timedelta

import pytest

from tools.exp007 import simulate as sim

HOUR = 3_600_000


def weekdays(start, n):
    out, d = [], date.fromisoformat(start)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def et_ms(day, hm):
    return int(datetime.fromisoformat(f'{day}T{hm}').replace(tzinfo=sim.ET).timestamp() * 1000)


def market(sessions, price):
    """24/7 OPEN-labelled bars: open = price(name, start), close = price(name, start + 1h)."""
    first, last = et_ms(sessions[0], '00:00') - 24 * HOUR, et_ms(sessions[-1], '23:00')
    tokens = {k: [[str(price(k, m)), '0', '0', str(price(k, m + HOUR)), '1', m, 1] for m in range(first, last, HOUR)]
              for k in sim.NAMES}
    return sim.Market(tokens, sessions)


SESSIONS = weekdays('2026-07-01', 60)


def test_fill_is_the_open_of_the_bar_starting_at_open_plus_30_and_close_is_the_bar_ending_at_16():
    m = market(SESSIONS, lambda k, ms: ms / HOUR)
    for t, d in enumerate(m.sessions):
        assert all(m.fill[k][t] == et_ms(d, '10:00') / HOUR for k in sim.NAMES)
        assert all(m.close[k][t] == et_ms(d, '16:00') / HOUR for k in sim.NAMES)
    assert m.fallbacks == dict(next_bar=0, close=0)


def test_weights_and_trend_never_read_a_later_close():
    m = market(SESSIONS, lambda k, ms: 100 + (ms // HOUR) % 7 * (1 + sim.NAMES.index(k)))
    w = sim.weights(m, 30)
    states = sim.trend_states(m)
    for k in sim.NAMES:
        for t in range(30, len(m.sessions)):
            m.close[k][t] = 1e6
    assert sim.weights(m, 30) == w
    assert sim.trend_states(m)[:30] == states[:30]
    assert sum(w.values()) == pytest.approx(1) and max(w.values()) <= sim.CAP + 1e-12


def test_flat_prices_cost_exactly_the_build_and_flatten_in_both_arms():
    m = market(SESSIONS, lambda k, ms: 100.0)
    states = sim.trend_states(m)
    s = sim.window_starts(m)[0]
    a = sim.run_window(m, s, False, states, 25, 0.03)
    b = sim.run_window(m, s, True, states, 25, 0.03)
    expected = -2 * (190 * 0.0025 + 5 * 0.03) / 200
    assert a[0] == pytest.approx(expected) and b == a and a[2] == 0


def test_a_steady_decline_turns_the_guard_down_and_cuts_drawdown():
    m = market(SESSIONS, lambda k, ms: 100 * 0.998 ** max(0, (ms - et_ms(SESSIONS[30], '16:00')) / HOUR))
    states = sim.trend_states(m)
    s = 29
    a = sim.run_window(m, s, False, states, 25, 0.03)
    b = sim.run_window(m, s, True, states, 25, 0.03)
    assert b[2] >= 1 and b[1] < a[1] and b[0] > a[0]


@pytest.mark.parametrize('a_dd,b_dd,a_ret,b_ret,changes,n,verdict', [
    (5.0, 3.5, 1.0, 0.8, 2, 5, 'SUPPORTED'),
    (5.0, 3.5, 1.0, 0.8, 3, 5, 'INCONCLUSIVE'),
    (5.0, 5.0, 1.0, 1.0, 1, 5, 'NOT SUPPORTED'),
    (5.0, 3.0, 1.0, -0.1, 1, 5, 'NOT SUPPORTED'),
    (5.0, 4.5, 1.0, 0.8, 1, 5, 'INCONCLUSIVE'),
    (5.0, 3.5, 1.0, 0.8, 2, 4, 'INCONCLUSIVE'),
])
def test_frozen_decision_rule(a_dd, b_dd, a_ret, b_ret, changes, n, verdict):
    r = dict(non_overlapping=n, A_static=dict(mean_maxdd_pct=a_dd, mean_ret_pct=a_ret),
             B_trend=dict(mean_maxdd_pct=b_dd, mean_ret_pct=b_ret, median_changes=changes))
    assert sim.outcome(r) == verdict

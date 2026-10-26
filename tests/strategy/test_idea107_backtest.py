"""IDEA-107 S7-G0: the S7 backtest is point in time, charges the hand-computed costs and applies the decision rule.

Offline only (synthetic bars; no snapshot, network or credentials). S7 is experimental and must not be deployed.
"""
from datetime import date, datetime, timedelta
import math
import random
from statistics import stdev

import pytest

from tools.idea106 import simulate as s6sim
from tools.idea107 import simulate as sim

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
    first = int(datetime.fromisoformat(sessions[0] + 'T00:00').replace(tzinfo=s6sim.ET).timestamp() * 1000) - 24 * HOUR
    last = int(datetime.fromisoformat(sessions[-1] + 'T23:00').replace(tzinfo=s6sim.ET).timestamp() * 1000)
    return {k: [[str(price(k, m))] * 4 + ['1', m, 1] for m in range(first, last, HOUR)] for k in sim.NAMES}


def random_walk(seed):
    rng = random.Random(seed)
    level = {k: 100.0 for k in sim.NAMES}
    cache = {}

    def price(k, m):
        if (k, m) not in cache:
            level[k] *= math.exp(rng.gauss(0, 0.006))
            cache[(k, m)] = level[k]
        return cache[(k, m)]
    return price


def flat_market(n=40):
    sessions = weekdays('2026-03-02', n)
    return s6sim.token_market(tokens(sessions, lambda k, m: 100.0), sessions)


def close_market(closes):
    """A P-style market from per-session close dicts (fill at the close, no intraday marks)."""
    n = len(closes)
    return s6sim.Market([f'd{i}' for i in range(n)], [(i, c) for i, c in enumerate(closes)], closes,
                        [{k: False for k in sim.NAMES} for _ in range(n)], [[] for _ in range(n)])


def test_g0_signal_reads_no_close_after_build_minus_one():
    sessions = weekdays('2026-03-02', 40)
    market = s6sim.token_market(tokens(sessions, random_walk(1)), sessions)
    s = 25
    before = sim.s7_targets(market, s)
    assert sorted(before.values()) == [0.0, sim.BASE_W, sim.BASE_W, sim.OVER_W, sim.OVER_W]
    for t in range(s, len(market.sessions)):  # the build's own close and every later close change nothing
        market.closes[t] = {k: 1e9 if k == 'NVDAB' else 1e-3 for k in sim.NAMES}
        market.carried[t] = {k: True for k in sim.NAMES}
    assert sim.s7_targets(market, s) == before
    z = sim.zscores(market, s - 1)
    market.closes[s - 1] = dict(market.closes[s - 1], NVDAB=market.closes[s - 1]['NVDAB'] * 0.5)
    assert sim.zscores(market, s - 1)['NVDAB'] < z['NVDAB']  # close s-1 is the latest input used


def test_g0_fill_bar_ends_after_the_signal_close():
    sessions = weekdays('2026-03-02', 30)
    market = s6sim.token_market(tokens(sessions, lambda k, m: 100.0), sessions)
    for t in range(1, len(market.sessions)):
        close_ms = int(datetime.fromisoformat(market.sessions[t - 1] + 'T16:00').replace(tzinfo=s6sim.ET).timestamp()
                       * 1000)
        assert close_ms < market.fills[t][0]


def test_g0_residual_volatility_scaled_z_is_hand_computed():
    closes = [{k: 100.0 for k in sim.NAMES} for _ in range(22)]
    closes[-1] = dict(closes[-1], NVDAB=90.0)
    market = close_market(closes)
    z = sim.zscores(market, 21)
    a = math.log(0.9)
    e_nvda = [0.0] * 19 + [a - a / 5]
    e_other = [0.0] * 19 + [-a / 5]
    assert z['NVDAB'] == pytest.approx((a - a / 5) / (stdev(e_nvda) * math.sqrt(5)))
    assert z['GOOGLB'] == pytest.approx((-a / 5) / (stdev(e_other) * math.sqrt(5)))
    assert sim.zscores(market, 21, residual=False, scale=False)['NVDAB'] == pytest.approx(a)
    assert sim.zscores(market, 20)['NVDAB'] == 0.0  # flat history before the drop: sd 0 -> z 0


def test_g0_too_short_history_and_carried_closes_make_names_ineligible():
    closes = [{k: 100.0 + i for k in sim.NAMES} for i in range(22)]
    market = close_market(closes)
    assert sim.zscores(market, 19) == {}  # needs closes t-20..t
    for u in (5, 9, 13):
        market.carried[u]['TSLAB'] = True
    z = sim.zscores(market, 21)
    assert 'TSLAB' not in z and len(z) == 4
    market.closes[3] = dict(market.closes[3], MSFTB=None)
    assert set(sim.zscores(market, 21)) == {'GOOGLB', 'NVDAB', 'SKHYB'}


def test_g0_ranking_rule_assigns_the_registered_shape():
    z = dict(GOOGLB=0.1, MSFTB=-2.0, NVDAB=-1.0, SKHYB=0.5, TSLAB=3.0)
    w = sim.targets_from_z(z)
    assert w == dict(GOOGLB=sim.BASE_W, MSFTB=sim.OVER_W, NVDAB=sim.OVER_W, SKHYB=sim.BASE_W, TSLAB=0.0)
    assert sum(w.values()) == pytest.approx(0.95)
    assert sim.OVER_W * 200 == pytest.approx(57.0) and sim.BASE_W * 200 == pytest.approx(38.0)
    m = sim.targets_from_z(z, shape='MIRROR')
    assert m['TSLAB'] == m['SKHYB'] == sim.OVER_W and m['MSFTB'] == 0.0
    t1 = sim.targets_from_z(z, shape='TILT1')
    assert t1['MSFTB'] == sim.OVER_W and t1['TSLAB'] == pytest.approx(0.095) and sum(t1.values()) == pytest.approx(0.95)
    # one name not ranked keeps 19%; fewer than three ranked names -> equal weight
    w4 = sim.targets_from_z({k: v for k, v in z.items() if k != 'MSFTB'})
    assert w4['MSFTB'] == sim.BASE_W and w4['NVDAB'] == w4['GOOGLB'] == sim.OVER_W and w4['TSLAB'] == 0.0
    assert sim.targets_from_z(dict(GOOGLB=1.0, TSLAB=-1.0)) == sim.equal_targets()
    # ties break by name
    assert sim.targets_from_z({k: 0.0 for k in sim.NAMES}) == dict(
        GOOGLB=sim.OVER_W, MSFTB=sim.OVER_W, NVDAB=sim.BASE_W, SKHYB=sim.BASE_W, TSLAB=0.0)
    assert len(sim.tilt_books()) == 30 and all(sum(b.values()) == pytest.approx(0.95) for b in sim.tilt_books())


def test_g0_flat_prices_give_the_hand_computed_costs():
    market = flat_market()
    bps, gas = sim.COSTS['central']
    fs1 = sim.run_book(market, 21, sim.equal_targets(), sim.COSTS['central'])
    expected_fs1 = sum(2 * (38.0 * bps[k] / 10_000 + gas) for k in sim.NAMES)
    assert expected_fs1 == pytest.approx(0.8118)
    assert fs1['cost'] == pytest.approx(expected_fs1) and fs1['ret'] == pytest.approx(-expected_fs1 / 200)
    assert fs1['legs'] == 10 and fs1['min_leg'] == pytest.approx(38.0)
    s7 = sim.run_book(market, 21, sim.s7_targets(market, 21), sim.COSTS['central'])  # flat: z all 0 -> name order
    expected_s7 = 2 * (57.0 * (bps['GOOGLB'] + bps['MSFTB']) / 10_000 + 4 * gas
                       + 38.0 * (bps['NVDAB'] + bps['SKHYB']) / 10_000 + 2 * gas)
    assert s7['cost'] == pytest.approx(expected_s7) and s7['ret'] == pytest.approx(-expected_s7 / 200)
    assert s7['legs'] == 12 and s7['min_leg'] == pytest.approx(28.5)
    assert s7['cost'] - fs1['cost'] == pytest.approx(2 * gas + 2 * (19 * (4.5 + 11.5) - 38 * 5.5) / 10_000)
    team = sim.run_book(market, 21, sim.s7_targets(market, 21), sim.COSTS['team'])
    assert team['cost'] == pytest.approx(2 * (190 * 25 / 10_000 + 6 * 0.03))


def test_g0_equal_weight_path_reproduces_idea106_fs1_static():
    sessions = weekdays('2026-03-02', 45)
    market = s6sim.token_market(tokens(sessions, random_walk(7)), sessions)
    for cost in (sim.COSTS['central'], sim.COSTS['stress']):
        for s in range(sim.FIRST_START, len(market.sessions) - sim.WINDOW + 1):
            a = sim.run_book(market, s, sim.equal_targets(), cost)
            b = s6sim.run_window(market, s, s6sim.static(sim.NAMES), cost)
            assert (a['ret'], a['max_dd'], a['cost']) == (b['ret'], b['max_dd'], b['cost'])


def test_g0_crash_trips_the_12_percent_cut_and_blocks_rebuild():
    closes = [{k: 100.0 for k in sim.NAMES} for _ in range(40)]
    for i in range(24, 40):
        closes[i] = {k: 70.0 for k in sim.NAMES}
    market = close_market(closes)
    r = sim.run_book(market, 21, sim.s7_targets(market, 21), sim.COSTS['central'])
    assert r['max_dd'] >= 0.12 and r['ret'] < -0.25


def _p(mean_pct=0.1, hi=0.2, s_hi=1.0, p1=0.1, p2=0.1, gates=None, dd=True, impl=True):
    g = dict(G1=True, G2=True, G3=True, G4=True, G7=True) if gates is None else gates
    return dict(gates=g, hi=hi, s_hi=s_hi, dd_gate=dd, impl_gate=impl,
                split=dict(P1=dict(mean_pct=p1), P2=dict(mean_pct=p2)))


def test_g0_decision_rule_matches_the_preregistration():
    t_ok = dict(hi=0.5, dd_gate=True, impl_gate=True)
    assert sim.outcome(_p(), t_ok)[0] == 'SUPPORTED'
    assert sim.outcome(_p(gates=dict(G1=False, G2=True, G3=True, G4=True, G7=True)), t_ok)[0] == 'INCONCLUSIVE'
    assert sim.outcome(_p(hi=-0.01), t_ok)[0] == 'NOT SUPPORTED'
    assert sim.outcome(_p(s_hi=-0.01), t_ok)[0] == 'NOT SUPPORTED'
    assert sim.outcome(_p(p1=-0.1, p2=-0.1), t_ok)[0] == 'NOT SUPPORTED'
    assert sim.outcome(_p(p1=-0.1, p2=0.1, gates=dict(G1=True, G2=False, G3=True, G4=True, G7=True)),
                       t_ok)[0] == 'INCONCLUSIVE'
    assert sim.outcome(_p(), dict(t_ok, hi=-0.01))[0] == 'NOT SUPPORTED'
    assert sim.outcome(_p(dd=False), t_ok)[0] == 'NOT SUPPORTED'
    assert sim.outcome(_p(), dict(t_ok, dd_gate=False))[0] == 'NOT SUPPORTED'
    assert sim.outcome(_p(impl=False), t_ok)[0] == 'INCONCLUSIVE'
    assert sim.outcome(_p(), t_ok, g0=False)[0] == 'INCONCLUSIVE'


def test_g0_refuses_a_snapshot_with_another_hash(tmp_path):
    (tmp_path / 'tokens.json').write_text('{}')
    (tmp_path / 'underlying.json').write_text('{}')
    with pytest.raises(SystemExit, match='refusing to run'):
        sim.main(['--data', str(tmp_path)])

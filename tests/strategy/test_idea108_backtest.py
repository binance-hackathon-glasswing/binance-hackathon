"""IDEA-108 S8-G0: the S8 backtest is point in time, charges the hand-computed costs and applies the decision rule.

Offline only (synthetic data; no snapshot, network or credentials). S8 is experimental and must not be deployed.
"""
from datetime import date, datetime, timedelta
import math
import random

import pytest

from tools.idea106 import simulate as s6sim
from tools.idea107 import simulate as s7sim
from tools.idea108 import simulate as sim

HOUR = 3_600_000
NAMES = sim.NAMES


def weekdays(start, n):
    out, d = [], date.fromisoformat(start)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def tokens(sessions, price):
    first = int(datetime.fromisoformat(sessions[0] + 'T00:00').replace(tzinfo=s6sim.ET).timestamp() * 1000) - 24 * HOUR
    last = int(datetime.fromisoformat(sessions[-1] + 'T23:00').replace(tzinfo=s6sim.ET).timestamp() * 1000)
    return {k: [[str(price(k, m))] * 4 + ['1', m, 1] for m in range(first, last, HOUR)] for k in NAMES}


def random_walk(seed):
    rng = random.Random(seed)
    level = {k: 100.0 for k in NAMES}
    cache = {}

    def price(k, m):
        if (k, m) not in cache:
            level[k] *= math.exp(rng.gauss(0, 0.006))
            cache[(k, m)] = level[k]
        return cache[(k, m)]
    return price


def close_market(closes, sessions=None):
    n = len(closes)
    sessions = sessions or [f'd{i}' for i in range(n)]
    return s6sim.Market(sessions, [(i, c) for i, c in enumerate(closes)], closes,
                        [{k: False for k in NAMES} for _ in range(n)], [[] for _ in range(n)])


def spiky_series(sessions, spikes, seed=3):
    """Closes with small noise and one large planted move per (name, day) in spikes."""
    rng = random.Random(seed)
    closes = {k: [] for k in NAMES}
    level = {k: 100.0 for k in NAMES}
    for d in sessions:
        for k in NAMES:
            level[k] *= math.exp(rng.gauss(0, 0.002) + (0.10 if (k, d) in spikes else 0.0))
            closes[k].append(level[k])
    return closes


# --- S8-G0: point in time -------------------------------------------------------------------------------------------

def test_detection_finds_planted_day_per_complete_quarter():
    sessions = weekdays('2024-01-01', 300)
    spikes = {('NVDAB', '2024-02-22'), ('NVDAB', '2024-05-23'), ('GOOGLB', '2024-04-26'), ('MSFTB', '2024-07-31')}
    days = sim.announcement_days(sessions, spiky_series(sessions, spikes))
    nv = dict(days['NVDAB'])
    assert nv['2024-03-31'] == '2024-02-22' and nv['2024-06-30'] == '2024-05-23'
    assert dict(days['GOOGLB'])['2024-06-30'] == '2024-04-26'
    assert dict(days['MSFTB'])['2024-09-30'] == '2024-07-31'
    last_q = sim._quarter(date.fromisoformat(sessions[-1]))[1].isoformat()
    assert all(q != last_q for k in NAMES for q, _ in days[k])  # the incomplete last quarter is never used


def test_signal_ignores_every_close_after_the_decision():
    sessions = weekdays('2024-01-01', 520)
    spikes = {('NVDAB', '2024-11-20'), ('TSLAB', '2024-10-23'), ('GOOGLB', '2025-07-24')}
    closes = spiky_series(sessions, spikes)
    days = sim.announcement_days(sessions, closes)
    s = sessions.index('2025-10-13')
    dec, build, flat = sessions[s - 1], sessions[s], sessions[s + 9]
    before = sim.announcers(days, dec, build, flat)
    assert 'TSLAB' in before  # 2024-10-23 + 364 d = 2025-10-22, inside (build, flatten]
    for k in NAMES:  # change every close from the decision session on: nothing may change
        for u in range(s - 1, len(sessions)):
            closes[k][u] = 1e6 if k == 'GOOGLB' else closes[k][u] * (3.0 if u % 2 else 0.2)
    after_days = sim.announcement_days(sessions, closes)
    assert sim.announcers(after_days, dec, build, flat) == before


def test_quarter_ending_on_or_after_decision_is_not_used():
    days = {k: [] for k in NAMES}
    days['NVDAB'] = [('2025-12-31', '2025-10-28')]
    assert sim.announcers(days, '2025-12-31', '2026-10-26', '2026-11-06') == ()
    assert sim.announcers(days, '2026-01-02', '2026-10-26', '2026-11-06') == ('NVDAB',)


def test_shift_window_is_build_exclusive_flatten_inclusive():
    days = {k: [] for k in NAMES}
    days['GOOGLB'] = [('2025-12-31', '2025-10-30')]  # p = 2026-10-29
    assert sim.announcers(days, '2026-10-27', '2026-10-28', '2026-11-10') == ('GOOGLB',)
    assert sim.announcers(days, '2026-10-28', '2026-10-29', '2026-11-11') == ()          # p == build: not held
    assert sim.announcers(days, '2026-10-14', '2026-10-15', '2026-10-29') == ('GOOGLB',)  # p == flatten: held
    assert sim.announcers(days, '2026-10-14', '2026-10-15', '2026-10-28') == ()
    assert sim.announcers(days, '2026-10-30', '2026-10-31', '2026-11-12', wide=5) == ('GOOGLB',)
    assert sim.announcers(days, '2026-08-01', '2026-08-03', '2026-08-14', shift=364 + 45) == ()


def test_skhyb_is_never_an_announcer_by_default():
    days = {k: [('2025-12-31', '2025-10-29')] for k in NAMES}
    assert 'SKHYB' not in sim.announcers(days, '2026-10-20', '2026-10-21', '2026-11-03')
    assert 'SKHYB' in sim.announcers(days, '2026-10-20', '2026-10-21', '2026-11-03', names=NAMES)


def test_coverage_requires_year_ago_quarters_for_all_predictable_names():
    days = {k: [('2018-09-30', '2018-08-01'), ('2018-12-31', '2018-11-01')] for k in NAMES}
    assert sim.covered(days, '2019-10-01', '2019-10-14')
    assert not sim.covered(days, '2019-06-03', '2019-06-14')  # needs 2018-Q2
    days['TSLAB'] = days['TSLAB'][:1]
    assert not sim.covered(days, '2019-12-20', '2020-01-03')


def test_fill_bar_ends_after_the_signal_close():
    sessions = weekdays('2026-03-02', 30)
    market = s6sim.token_market(tokens(sessions, lambda k, m: 100.0), sessions)
    for t in range(1, len(market.sessions)):
        close_ms = int(datetime.fromisoformat(market.sessions[t - 1] + 'T16:00').replace(tzinfo=s6sim.ET).timestamp()
                       * 1000)
        assert close_ms < market.fills[t][0]


# --- S8-G0: decision rule ---------------------------------------------------------------------------------------------

def test_targets_table():
    assert sim.targets(()) == {k: 0.19 for k in NAMES}
    w1 = sim.targets(('NVDAB',))
    assert w1['NVDAB'] == pytest.approx(0.285) and all(w1[k] == pytest.approx(0.16625) for k in NAMES if k != 'NVDAB')
    w2 = sim.targets(('GOOGLB', 'MSFTB'))
    assert w2['GOOGLB'] == w2['MSFTB'] == pytest.approx(0.285)
    assert all(w2[k] == pytest.approx(0.38 / 3) for k in ('NVDAB', 'SKHYB', 'TSLAB'))
    assert sim.targets(('GOOGLB', 'MSFTB', 'NVDAB')) == {k: 0.19 for k in NAMES}
    assert sim.targets(('GOOGLB', 'MSFTB', 'NVDAB', 'TSLAB')) == {k: 0.19 for k in NAMES}
    w3 = sim.targets(('GOOGLB', 'MSFTB', 'NVDAB'), all_m=True)
    assert w3['GOOGLB'] == pytest.approx(0.25) and w3['SKHYB'] == pytest.approx(0.10)
    w4 = sim.targets(sim.PREDICTABLE, all_m=True)
    assert w4['GOOGLB'] == pytest.approx(0.2125) and w4['SKHYB'] == pytest.approx(0.10)
    for w in (w1, w2, w3, w4):
        assert sum(w.values()) == pytest.approx(0.95) and max(w.values()) <= 0.30
        assert min(v * 200 for v in w.values()) >= sim.MIN_TRADE


# --- S8-G0: costs on flat prices ----------------------------------------------------------------------------------------

def hand_cost(notional, bps, gas):
    """Build + flatten at flat prices: each name's notional once each way, legs = ceil(notional / 38.2)."""
    one_way = sum(n * bps[k] / 10_000 + math.ceil(n / 38.2) * gas for k, n in notional.items())
    return 2 * one_way


@pytest.mark.parametrize('ann', [(), ('NVDAB',), ('MSFTB',), ('GOOGLB', 'MSFTB'), ('NVDAB', 'TSLAB')])
@pytest.mark.parametrize('cost', ['central', 'team', 'stress'])
def test_flat_costs_match_hand_calculation(ann, cost):
    market = close_market([{k: 100.0 for k in NAMES} for _ in range(12)])
    bps, gas = sim.COSTS[cost]
    bps = bps if isinstance(bps, dict) else {k: bps for k in NAMES}
    w = sim.targets(ann)
    r = s7sim.run_book(market, 1, w, sim.COSTS[cost])
    expect = hand_cost({k: w[k] * 200 for k in NAMES}, bps, gas)
    assert r['cost'] == pytest.approx(expect, abs=1e-9)
    assert r['ret'] == pytest.approx(-expect / 200, abs=1e-9)
    assert r['legs'] == 2 * (5 + len(ann))
    assert r['min_leg'] >= sim.MIN_TRADE


def test_flat_central_numbers_in_the_entry():
    market = close_market([{k: 100.0 for k in NAMES} for _ in range(12)])
    fs1 = s7sim.run_book(market, 1, sim.targets(()), sim.COSTS['central'])['cost']
    assert fs1 == pytest.approx(0.8118, abs=1e-4)  # 2 x (38 x 30.5 bp + 5 x 0.058)
    nv = s7sim.run_book(market, 1, sim.targets(('NVDAB',)), sim.COSTS['central'])['cost']
    # NVDAB 57 USDT (2 legs) at 5.0 bp, four names at 33.25 USDT at 4.5+11.5+4.0+5.5 bp, six pairs, both ways
    assert nv == pytest.approx(2 * (57 * 5.0e-4 + 33.25 * 25.5e-4 + 6 * 0.058), abs=1e-9)
    assert 0.108 - 1e-3 <= nv - fs1 <= 0.142 + 1e-3


def test_equal_path_reproduces_idea106_fs1_static():
    sessions = weekdays('2026-03-02', 40)
    market = s6sim.token_market(tokens(sessions, random_walk(7)), sessions)
    for s in (1, 11, 25):
        a = s6sim.run_window(market, s, s6sim.static(NAMES), sim.COSTS['central'])
        b = s7sim.run_book(market, s, sim.targets(()), sim.COSTS['central'])
        assert a['ret'] == pytest.approx(b['ret'], abs=1e-12)
        assert a['max_dd'] == pytest.approx(b['max_dd'], abs=1e-12)


def test_s8_equals_fs1_when_no_announcer():
    sessions = weekdays('2026-03-02', 40)
    market = s6sim.token_market(tokens(sessions, random_walk(9)), sessions)
    setup = sim.Setup(market, {k: [] for k in NAMES}, sim.t_starts(market))
    a, b = sim.run_s8(setup, sim.COSTS['central']), sim.run_fs1(setup, sim.COSTS['central'])
    assert [x['ret'] for x in a] == [x['ret'] for x in b]


# --- outcome rule ---------------------------------------------------------------------------------------------------------

def fake(hi=0.01, s_hi=0.05, dd=True, impl=True, p1=0.1, p2=0.1, gates=None):
    out = dict(hi=hi, s_hi=s_hi, dd_gate=dd, impl_gate=impl, split=dict(P1=dict(mean_pct=p1), P2=dict(mean_pct=p2)))
    out['gates'] = gates if gates is not None else dict(G1=True, G2=True, G3=True, G4=True, G7=True)
    return out


def test_outcome_rule():
    assert sim.outcome(fake(), fake())[0] == 'SUPPORTED'
    assert sim.outcome(fake(gates=dict(G1=False, G2=True, G3=True, G4=True, G7=True)), fake())[0] == 'INCONCLUSIVE'
    assert sim.outcome(fake(), fake(), g0=False)[0] == 'INCONCLUSIVE'
    assert sim.outcome(fake(hi=-0.001), fake())[0] == 'NOT SUPPORTED'
    assert sim.outcome(fake(s_hi=-0.001), fake())[0] == 'NOT SUPPORTED'
    assert sim.outcome(fake(), fake(hi=-0.001))[0] == 'NOT SUPPORTED'
    assert sim.outcome(fake(dd=False), fake())[0] == 'NOT SUPPORTED'
    assert sim.outcome(fake(), fake(dd=False))[0] == 'NOT SUPPORTED'
    assert sim.outcome(fake(p1=-0.1, p2=-0.1), fake())[0] == 'NOT SUPPORTED'
    assert sim.outcome(fake(p1=-0.1, p2=0.1, gates=dict(G1=True, G2=False, G3=True, G4=True, G7=True)),
                       fake())[0] == 'INCONCLUSIVE'
    assert sim.outcome(fake(), fake(impl=False))[0] == 'INCONCLUSIVE'


def test_refuses_to_run_on_a_different_snapshot(tmp_path):
    (tmp_path / 'tokens.json').write_text('{}')
    (tmp_path / 'underlying.json').write_text('{}')
    with pytest.raises(SystemExit, match='refusing to run'):
        sim.check_hashes(tmp_path)

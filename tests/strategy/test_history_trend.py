"""IDEA-103: fetched session history changes actual policy and planner targets; synthetic prices."""
from larp.contracts import Document
from larp.marketdata.port import TOKENS
from larp.research.fixtures import changed, with_quotes
from larp.risk.planner import plan
from larp.strategy.policy import decide
from tests.marketdata.test_session_history import NOW, Port, reader, rows
from tests.strategy.test_execution_bounds import at
from tests.strategy.test_s1_core import block
from tests.strategy.test_s1_plan import AT_60, AT_95, NAMES, settled


def snapshot(*, low=False, terminal=False):
    stamp = '2026-10-23T20:20:00Z'
    s = at(stamp, held={s: AT_60 if low else AT_95 for s in NAMES},
        state=settled([3,5] if low else [19,20], trend='DOWN' if low else 'UP'),
        risk=dict(day='2026-10-23'), session_index=79,
        execution_session=dict(index=79,open_ms=1792762200000,close_ms=1792785600000,next_open_ms=1793021400000),
        profile_changes=dict(s1=block(execution=dict(open_delay_seconds=1800,close_buffer_seconds=900,
            max_attempts_per_leg_session=3,hours='KIT_OPEN_STATE')), new_risk_end='2026-10-23T19:00:00Z' if terminal else '2026-11-01T00:00:00Z',
            flatten_start='2026-10-23T20:00:00Z' if terminal else '2026-11-02T00:00:00Z',
            signing_end='2026-11-03T00:00:00Z'))
    return changed(s, markets=[dict(m, token_id=TOKENS[m['symbol']]) for m in s.context.read()['markets']])


def test_falling_history_causes_actual_reduction_toward_60_percent(tmp_path):
    s = snapshot()
    history = reader(tmp_path,Port(source=rows(prices=(100,99,98,97,90,90))),profile=s.context.read()['profile'])
    s = changed(s,series=history(NOW))
    proposal = decide(s,s.policy_state)
    data = proposal.next_policy_state.data.read()
    assert data['s1']['trend_state'] == 'DOWN' and data['s1']['applied_target'] == [3,5]
    s = with_quotes(s)
    result = plan(s,decide(s,s.policy_state)).read()
    assert result['intents'] and result['intents'][0]['side'] == 'SELL', result
    assert not result['intents'][0]['mandatory']


def test_rising_history_restores_95_percent_and_plans_a_buy(tmp_path):
    s = snapshot(low=True)
    history = reader(tmp_path,Port(source=rows(prices=(90,91,92,93,100,100))),profile=s.context.read()['profile'])
    s = changed(s,series=history(NOW))
    proposal = decide(s,s.policy_state)
    data = proposal.next_policy_state.data.read()
    assert data['s1']['trend_state'] == 'UP' and data['s1']['applied_target'] == [19,20]
    s = with_quotes(s)
    result = plan(s,decide(s,s.policy_state)).read()
    assert result['intents'] and result['intents'][0]['side'] == 'BUY', result


def test_neutral_and_missing_history_keep_previous_state_and_risk_exits_run(tmp_path):
    s = snapshot(low=True)
    history = reader(tmp_path,Port(),profile=s.context.read()['profile'])
    stable = changed(s,series=history(NOW))
    assert decide(stable,stable.policy_state).next_policy_state.data.read()['s1']['trend_state'] == 'DOWN'
    failing = Port(); failing.fail=True
    history = reader(tmp_path/'failed',failing,profile=s.context.read()['profile'])
    missing = changed(s,series=history(NOW))
    assert decide(missing,missing.policy_state).next_policy_state.data.read()['s1']['trend_state'] == 'DOWN'
    terminal = changed(snapshot(terminal=True),series=history(NOW))
    terminal = with_quotes(terminal)
    result = plan(terminal,decide(terminal,terminal.policy_state)).read()
    assert result['intents'] and result['intents'][0]['mandatory'], result

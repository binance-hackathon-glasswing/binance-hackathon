"""S5-SMALL01: actual UP-quote -> DOWN regime and serial small-wallet execution; synthetic only."""
from dataclasses import replace
from fractions import Fraction
import json
import pytest
from larp.contracts import ContractError, Document, PolicyState, TargetKind
from larp.research.fixtures import changed, with_quotes
from larp.strategy.policy import decide
from larp.risk.planner import plan
from larp.strategy.profiles import validate_live
from larp.strategy.rehearsal_sizing import opening_cash_check
from tests.strategy import test_s5_monday_flatten as s5
from tests.strategy.test_s1_plan import token_series, FALLING, settled
from tests.strategy.test_equal_weight import with_state


def snapshot():
    s, _ = s5.round_at('2026-10-27T05:00:00Z', cash_units=s5.RUN6_CASH,
                       bnb_units=s5.RUN6_BNB, sizing=True)
    c = s.context.read()
    for m in c['markets']:
        m.update(quotes=[], decimals=18)
        c['portfolio']['positions'][m['symbol']]['decimals'] = 18
    return changed(s, markets=c['markets'], portfolio=c['portfolio'])


def restored(s, proposal):
    rec = json.loads(json.dumps(proposal.next_policy_state.record()))
    return replace(s, policy_state=PolicyState(**dict(rec, data=Document.from_dict(rec['data']))))


def test_valid_up_quote_then_down_history_requotes_and_executes_smaller_buy():
    up = snapshot()
    quoted = with_quotes(up, spread_bps=1, gas=75_000_000_000_000)
    initial = decide(quoted, quoted.policy_state)
    high = plan(quoted, initial).read()
    assert len(high['intents']) == 1
    assert 15_000_000 < high['intents'][0]['cash_units'] < 16_000_000
    down = restored(quoted, initial)
    down = changed(down, series=token_series(down, FALLING))
    proposal = decide(down, down.policy_state)
    assert proposal.next_policy_state.data.read()['s1']['trend_state'] == 'DOWN'
    resized = plan(down, proposal).read()
    assert not resized['intents']  # high-size quote cannot authorize the new smaller order
    assert resized['quote_requests'] and all(9_700_000 < q['pay_units'] < 9_800_000 for q in resized['quote_requests'])
    executable = with_quotes(down, spread_bps=1, gas=75_000_000_000_000)
    result = plan(executable, decide(executable, executable.policy_state)).read()
    assert len(result['intents']) == 1 and 9_700_000 < result['intents'][0]['cash_units'] < 9_800_000


@pytest.mark.parametrize('trend,limiter,level', [('UP','NORMAL',Fraction(19,20)),
    ('DOWN','NORMAL',Fraction(3,5)), ('UP','SEVERE',Fraction(3,10))])
def test_five_proportional_names_survive_serial_settlement_and_state_reconstruction(trend,limiter,level):
    s = snapshot()
    state = settled([level.numerator,level.denominator], trend=trend)
    state['s1']['limiter'].update(level=limiter, expires_session=1000 if limiter!='NORMAL' else None)
    s = with_state(s, state)
    names=set()
    for _ in range(5):
        s = with_quotes(s, spread_bps=1, gas=75_000_000_000_000)
        proposal=decide(s,s.policy_state)
        result=plan(s,proposal).read()
        assert len(result['intents'])==1, result
        intent=result['intents'][0]
        assert intent['side']=='BUY' and intent['symbol'] not in names
        assert 3_192_045 <= intent['cash_units'] < 19_000_000
        names.add(intent['symbol'])
        ledger=s.context.read()['portfolio']
        ledger['cash_units']-=intent['cash_units']+intent['fee_units']
        ledger['bnb_units']-=75_000_000_000_000
        pos=ledger['positions'][intent['symbol']]
        pos['units']+=intent['token_units'];pos['cost_basis_units']+=intent['cash_units']
        s=restored(changed(s,portfolio=ledger,execution_attempt_budget=result['execution_attempt_budget']),proposal)
        check=plan(s,decide(s,s.policy_state)).read()
        assert not [i for i in check['intents'] if i['side']=='SELL']
    assert len(names)==5 and not plan(s,decide(s,s.policy_state)).read()['intents']
    assert s.context.read()['portfolio']['cash_units']>0


@pytest.mark.parametrize('change', [dict(environment='FINAL'),dict(policy_id='larp-fs1-rehearsal-v1'),
    dict(s5_entry_cost_cap_bps=201),dict(s5_entry_cost_cap_bps=True),dict(s5_entry_cost_cap_bps=50),
    dict(s5_entry_lot_units=19_000_000),dict(entry_cost_basis='DISPLAYED'),dict(s1_capital_basis='TOTAL')])
def test_cost_opt_in_cannot_escape_exact_small_wallet_scope(change):
    p=json.loads(s5.S5.read_bytes())
    with pytest.raises(ContractError): validate_live(dict(p,**change))


def test_cost_limit_and_reserve_still_block_expensive_quotes():
    s=with_state(snapshot(),settled([3,5],trend='DOWN'))
    for spread,gas in ((250,1),(1,200_000_000_000_000)):
        costly=with_quotes(s,spread_bps=spread,gas=gas)
        markets=costly.context.read()['markets']
        for m in markets:
            for q in m['quotes']: q['impact_bps']=1  # isolate total cost from the separate impact guard
        costly=changed(costly,markets=markets)
        r=plan(costly,decide(costly,costly.policy_state)).read()
        assert not r['intents']
        assert {v['reason'] for v in r['rejections']} & {'ENTRY_COST_CAP','COST_RESERVE_INSUFFICIENT'}
    affordable=with_quotes(s,spread_bps=1,gas=75_000_000_000_000)
    assert plan(affordable,decide(affordable,affordable.policy_state)).read()['intents']
    # The same quote fails the historical50bp policy, even when its preliminary minimum is bypassed.
    p=affordable.context.read()['profile'];p.pop('s5_entry_cost_cap_bps')
    legacy=replace(changed(affordable,profile=p),policy_profile_hash=Document.from_dict(p).digest('StrategyProfile.v1'))
    r=plan(legacy,decide(legacy,legacy.policy_state)).read()
    assert not r['intents'] and any(v['reason']=='ENTRY_COST_CAP' for v in r['rejections'])


def test_small_preparation_requires_fundable_low_level_target():
    p=json.loads(s5.S5.read_bytes())
    assert opening_cash_check(p,s5.RUN6_CASH)['opening_lot_units']==4_876_382
    with pytest.raises(ContractError):opening_cash_check(p,20_000_000)

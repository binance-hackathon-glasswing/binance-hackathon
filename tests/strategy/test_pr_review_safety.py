"""Prospective strategy integration regressions from IDEA-043 / IDEA-040."""
from dataclasses import replace
import pytest
from larp.contracts import Document, ContractError
from larp.research.fixtures import changed, with_quotes
from larp.risk.planner import plan
from larp.risk.accounting import advance_accounting
from larp.strategy.policy import decide
from larp.strategy.schema import instant
from tests.strategy.live_fixtures import live_snapshot
from tests.strategy.test_red_flag_classes import evidence, next_session
from tests.risk.test_live_resource_receipts import receipt


def test_low_gas_above_one_sale_budget_never_starves_mandatory_trim():
    s = live_snapshot(held={'NVDAB':6000}, gas_low=True, quoted=True)
    result = plan(s, decide(s, s.policy_state)).read()
    assert result['intents'] and result['intents'][0]['side'] == 'SELL'
    assert result['intents'][0]['mandatory'] is True
    assert not any(q['symbol'] == 'BNB' for q in result['quote_requests'])


def test_class1_exit_precedes_buy_and_bypasses_discretionary_filters():
    s = with_quotes(evidence(live_snapshot(held={'NVDAB':100}), '4.02'))
    c = s.context.read()
    for q in c['markets'][0]['quotes']:
        q['impact_bps'] = 500
        q['origin'] = 'WEB3_OPEN_API'
    s = changed(s, markets=c['markets'], last_discretionary_session=c['session_index'])
    result = plan(s, decide(s, s.policy_state)).read()
    assert result['intents'][0]['symbol'] == 'NVDAB'
    assert result['intents'][0]['mandatory'] is True
    assert 'CLASS_1_EXIT' in result['intents'][0]['reasons']


def test_critical_clearance_preserves_unexpired_timed_block():
    s = evidence(live_snapshot(), '1.05')
    p1 = decide(s, s.policy_state)
    s = next_session(s, p1.next_policy_state, 81, item='4.02', finding_id='critical')
    p2 = decide(s, s.policy_state)
    s = next_session(s, p2.next_policy_state, 82, item=None)
    p3 = decide(s, s.policy_state)
    assert p3.next_policy_state.data.read()['blocked']['NVDAB']['expires_session'] == 85
    s = replace(changed(s, session_index=85, assessments=[]), policy_state=p3.next_policy_state)
    assert 'NVDAB' not in decide(s, s.policy_state).next_policy_state.data.read()['blocked']


def test_missing_entry_ranking_data_does_not_block_terminal_sale():
    s = live_snapshot(held={'NVDAB':1000}, now=instant('2026-11-10T00:00:00Z'), quoted=True)
    c = s.context.read()
    for m in c['markets']: m.pop('measured_roundtrip_bps',None)
    result = plan(changed(s, markets=c['markets']), None).read()
    assert result['intents'][0]['mandatory'] is True


def test_unmarked_ledger_cannot_accept_scripted_receipt():
    s = live_snapshot(held={'NVDAB':1000}, now=instant('2026-11-10T00:00:00Z'), quoted=True)
    ledger, event = receipt(s, plan(s,None))
    data = ledger.read(); data.pop('mode',None)
    event['origin'] = 'SCRIPTED_FAKE'
    with pytest.raises(ContractError):
        advance_accounting(Document.from_dict(data), Document.from_dict(event))


def test_signing_stops_with_confirmation_margin_and_expiry_is_bounded():
    s = live_snapshot(held={'NVDAB':1000}, now=instant('2026-11-11T14:44:50Z'), quoted=True)
    result = plan(s,None).read()
    assert instant(result['intents'][0]['quote_expiry']) <= instant('2026-11-11T14:45:00Z')
    s = live_snapshot(held={'NVDAB':1000}, now=instant('2026-11-11T14:45:00Z'), quoted=True)
    assert not plan(s,None).read()['intents']

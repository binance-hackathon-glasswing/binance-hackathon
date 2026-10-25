"""IDEA-097 S4-F1 ER2/ER4: the refund flag is marked by expire() and accepted only on an unclaimed expiry."""
from larp.contracts import ContractError
from larp.ports import validate_execution_observation
from larp.runtime.driver import EXPIRED_REASON
from tests.integration.test_execution_bounds import unclaimed_fact as fact


def test_er4_the_flag_is_only_valid_on_an_unclaimed_expiry():
    import pytest
    base = fact(dict(intent_id='i'), 'r', 'e', 1792900000000)
    validate_execution_observation(dict(base, reason=EXPIRED_REASON, attempt_refund=True))
    for bad in (dict(reason=EXPIRED_REASON, attempt_refund=1), dict(reason=EXPIRED_REASON, attempt_refund=False),
                dict(reason='QUOTE_EXPIRED', attempt_refund=True), dict(attempt_refund=True)):
        with pytest.raises(ContractError):
            validate_execution_observation(dict(base, **bad))
    approval = dict(base, kind='BROADCAST_ATTEMPTED', step='approve', tx_hash='0x' + 'a' * 64, attempt_refund=True)
    for key in ('settlement', 'origin', 'intent_terminal', 'round_terminal'):
        approval.pop(key)
    with pytest.raises(ContractError):
        validate_execution_observation(approval)


def test_er2_expire_marks_its_fact_for_a_refund():
    from larp.runtime.driver import not_submitted
    current = dict(run_id='run', wallet_id='w')
    assert not_submitted(current, 'r', 'i', 'e', 1792900000000, EXPIRED_REASON, True, refund=True)['attempt_refund'] is True
    assert 'attempt_refund' not in not_submitted(current, 'r', 'i', 'e', 1792900000000, 'OTHER', True)

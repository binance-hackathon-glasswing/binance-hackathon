"""CAP-02: real policy boundaries and retained sample coverage, no keys or external I/O."""
import hashlib
import json
from pathlib import Path

import pytest

from larp.execution import Blocked, NATIVE_BNB, USDT
from larp.marketdata.port import TOKENS
from larp.signer.policy import SigningPolicy
from tests.execution.test_signer_caps_proposal import CapsProposal

EVIDENCE = Path(__file__).resolve().parents[2] / 'docs/build/evidence'
DECISION = json.loads((EVIDENCE / 'signer-numeric-ceilings-20261021.json').read_bytes())


def test_numeric_decision_hashes_and_scope_are_explicit():
    assert DECISION['status'] == 'APPROVED_NUMERIC_CEILINGS_ONLY'
    assert not any(DECISION[k] for k in ('ready_to_install', 'signing_enabled',
                                       'selected_profile_approved', 'current_full_holdings_checked'))
    for path, digest in DECISION['evidence'].items():
        assert hashlib.sha256((EVIDENCE / path).read_bytes()).hexdigest() == digest
    for mode, row in DECISION['policies'].items():
        p = row['signing_policy']
        raw = (json.dumps(p, sort_keys=True, separators=(',', ':')) + '\n').encode()
        assert hashlib.sha256(raw).hexdigest() == row['sha256_canonical_json_lf']
        assert set(p['allowed_tokens']) == {USDT, *TOKENS.values()}
        assert p['allowance_recovery'] is False


@pytest.mark.parametrize('mode', ['development', 'final'])
def test_approved_numeric_policies_enforce_actual_token_fee_and_spender_boundaries(mode):
    policy = SigningPolicy.from_config(DECISION['policies'][mode]['signing_policy'])
    case = CapsProposal()
    for token, cap in policy.max_input_units.items():
        for step in ('APPROVE', 'SWAP'):
            case.check(policy, token, cap, step)
            with pytest.raises(Blocked):
                case.check(policy, token, cap + 1, step)
    for step in ('APPROVE', 'SWAP'):
        case.check(policy, USDT, 1, step, fee=policy.max_fee_wei)
        for bad in (dict(fee=policy.max_fee_wei + 1), dict(spender='0x' + '34' * 20), dict(native_value=1)):
            with pytest.raises(Blocked):
                case.check(policy, USDT, 1, step, **bad)
        with pytest.raises(Blocked):
            case.check(policy, NATIVE_BNB, 1, step)


@pytest.mark.parametrize('mode,env,size', [('development', 'rehearsal', 20), ('final', 'final', 40)])
def test_retained_quote_quantities_and_candidate_cash_fee_ceilings_fit(mode, env, size):
    policy = SigningPolicy.from_config(DECISION['policies'][mode]['signing_policy'])
    packet = json.loads((EVIDENCE / 'ld02d-size-sell-20261021.json').read_bytes())
    p = json.loads((EVIDENCE / f'ld09b-gas-budget-profiles-20261021/{env}-live.json').read_bytes())
    assert p['per_trade_cap_units'] * 10**12 <= policy.max_input_units[USDT]
    assert size * 10**18 <= policy.max_input_units[USDT]  # nominal requested pay; not retained response binding
    for symbol, token in TOKENS.items():
        row = packet['sweep'][symbol]['sizes'][str(size)]
        assert row['buy']['out_units'] == row['sell']['in_units'] <= policy.max_input_units[token]
    ceiling = DECISION['execution_ceiling']
    assert ceiling['max_gas'] * ceiling['max_gas_price_wei'] == ceiling['max_transaction_fee_wei']
    assert ceiling['max_transaction_fee_wei'] <= policy.max_fee_wei
    # Keep the historical refusal: cap coverage does not establish executable route coverage.
    assert packet['sweep']['MSFTB']['sizes']['40']['buy']['gas'] == 'Min return not reached'

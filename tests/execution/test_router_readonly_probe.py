"""RP01 collector boundaries; fake external ports only."""
import json

import pytest

from larp.contracts import ContractError
from larp.execution import Blocked
from larp.marketdata.web3 import Unavailable
from tools.deploy.replay_router_readonly import BoundedRpc, QuoteOnlyClient, public_bytes


def test_quote_collector_cannot_build_approvals_estimate_gas_or_broadcast(tmp_path):
    from larp.marketdata.web3 import Artifacts
    c = QuoteOnlyClient('synthetic-key', 'synthetic-secret', artifacts=Artifacts(tmp_path))
    for method, endpoint in [('GET', 'aggregator/approve-transaction'),
                             ('POST', 'pre-transaction/gas-limit'),
                             ('POST', 'pre-transaction/broadcast-transaction')]:
        with pytest.raises(Unavailable, match='allowlist'):
            c.request(method, endpoint, {})


def test_readonly_rpc_refuses_submission_arbitrary_calls_and_budget_overrun(tmp_path):
    from larp.marketdata.web3 import Artifacts
    rpc = BoundedRpc('https://example.invalid', source_id='synthetic', artifacts=Artifacts(tmp_path))
    for method, params in [('eth_sendRawTransaction', ['0x00']),
                           ('eth_call', [dict(to='0x' + '11' * 20, data='0x1234'), '0x1'])]:
        with pytest.raises(Blocked):
            rpc.call(method, params)
    rpc.read_count = 125
    with pytest.raises(ContractError, match='budget'):
        rpc.call('eth_chainId', [])


@pytest.mark.parametrize('echo', ['private-value', 'PRIVATE-VALUE', 'private\\u002dvalue'])
def test_public_report_refuses_literal_case_changed_and_json_escaped_private_values(echo):
    with pytest.raises(ContractError, match='privacy'):
        public_bytes(dict(error=echo), ['private-value'])


def test_public_summary_never_adds_private_input_fields():
    raw = public_bytes(dict(status='PASS_LOCAL_READONLY', signing_enabled=False), ['synthetic-secret'])
    assert json.loads(raw) == dict(status='PASS_LOCAL_READONLY', signing_enabled=False)

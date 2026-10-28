"""IDEA-110 TEMP-SC M3: FINAL caps inputs from a prepared directory, then FS1's own final_services assembly.
Synthetic quotes through a fake port; no network."""
import hashlib
import json
from unittest.mock import patch

import pytest

from larp.contracts import ContractError
from larp.marketdata.port import TOKENS
from larp.execution import USDT
from tests.runtime import test_fs1_standalone as standalone, test_gate_a
from tests.runtime.test_fs1_standalone import prepare
from tests.runtime.test_gate_a import WALLET
from tools.deploy import final_caps_inputs as tool, prepare_fs1

NOW = '2026-10-27T18:00:30Z'
TEMP = dict(temp_self_check=True, run_id='larp-final-selfcheck-temp', database_name='larp_final_selfcheck')
ROUTER = '0xb44446b0c8e56988c34f7ff73ae904982b5fdda5'


@pytest.fixture(autouse=True)
def activation_time(monkeypatch):
    for module in (standalone, test_gate_a):
        monkeypatch.setattr(module, 'NOW', NOW)


class FakePort:
    """Web3Observation.v1 records at 500 USDT per whole token (inside the CAP-02 token ceilings), 64 Mwei gas price."""

    def __init__(self, artifacts, wallet=WALLET):
        self.artifacts, self.wallet, self.requests = artifacts, wallet, []

    def quote(self, symbol, side, amount, decimals):
        self.requests.append((symbol, side, amount))
        pay, receive = (USDT, TOKENS[symbol]) if side == 'BUY' else (TOKENS[symbol], USDT)
        out = amount * 10**decimals // (500 * 10**18) if side == 'BUY' else amount * 500 * 10**18 // 10**decimals
        scales = {USDT: 18, TOKENS[symbol]: decimals}
        record = dict(schema='Web3Observation.v1', source_id='BINANCE_WEB3', requested_at=NOW, method='GET',
            endpoint='aggregator/quote-and-swap', outcome='ok', http_status=200,
            params=dict(binanceChainId='56', userWalletAddress=self.wallet, fromTokenAddress=pay,
                        toTokenAddress=receive, amount=str(amount)),
            response=dict(code=0, data=[dict(executionMode='SWAP', rfq=None, routerResult=dict(
                fromToken=dict(tokenContractAddress=pay, decimal=str(scales[pay])),
                toToken=dict(tokenContractAddress=receive, decimal=str(scales[receive])),
                fromTokenAmount=str(amount), toTokenAmount=str(out)), tx=dict(
                to=ROUTER, value='0', gas='300000', gasPrice='64000000', minReceiveAmount=str(out * 998 // 1000),
                **{'from': self.wallet, 'chainId': '0x38'}))]))
        self.artifacts.put(record)
        return record


def prepared(tmp_path):
    files = prepare(**TEMP)
    runtime = json.loads(files['runtime.json'])
    # Local public CA/router files stand in for the identical absolute host paths (as test_fs1_standalone).
    ca = tmp_path / 'ca.pem'; ca.write_bytes(b'synthetic-public-CA')
    policy = tmp_path / 'router.json'; policy.write_bytes(prepare_fs1.POLICY.read_bytes())
    runtime.update(database_ca_file=str(ca), database_ca_sha256=hashlib.sha256(ca.read_bytes()).hexdigest())
    runtime['driver']['untrusted_router_policy_file'] = str(policy)
    files['runtime.json'] = json.dumps(runtime).encode()
    directory = tmp_path / 'prepared'; directory.mkdir()
    for name, raw in files.items():
        (directory / name).write_bytes(raw)
    return files, directory, runtime


def rendered():
    return dict(market_artifact_root='/var/lib/larp-execution/market', chain_artifact_root='/var/lib/larp-execution/chain',
                signer_timeout_seconds=20)


def test_temp_caps_inputs_cover_and_assemble_through_final_services(tmp_path):
    files, directory, runtime = prepared(tmp_path)
    providers = runtime['driver']['balance_rpc_providers']
    ports = []
    with patch('socket.socket', side_effect=AssertionError('Offline only')):
        inputs, result, _ = tool.build(directory, rendered(), providers, {}, tmp_path / 'caps', now=NOW,
                                       port_factory=lambda a: ports.append(FakePort(a)) or ports[-1])
        assert result['numeric_status'] == 'COVERED', result['blockers']
        services = prepare_fs1.final_services(files, inputs, now=NOW, base_dir=tmp_path / 'caps')
    signer = json.loads(services['signer.json'])
    assert signer['mode'] == 'live' and signer['run_id'] == 'larp-final-selfcheck-temp'
    assert signer['database_name'] == 'larp_final_selfcheck' and signer['signing_policy']['allowance_recovery'] is True
    execution = json.loads(services['execution.json'])
    assert execution['rpc_source_id'] == providers[0]['source_id'] and execution['mode'] == 'live'
    # The self-check BUY of 0.90 USDT is quoted beside the profile sizes.
    profile = json.loads(files['strategy-profile.json'])
    check = profile['activation_self_check']
    assert (check['symbol'], 'BUY', check['pay_units'] * 10**12) in ports[0].requests
    assert all(p.stat().st_mode & 0o077 == 0 for p in (tmp_path / 'caps').iterdir())


def test_refuses_rehearsal_or_changed_prepared_bytes_and_existing_output(tmp_path):
    files, directory, runtime = prepared(tmp_path)
    providers = runtime['driver']['balance_rpc_providers']
    factory = lambda a: FakePort(a)
    (directory / 'initial-state.json').write_bytes(files['initial-state.json'] + b' ')
    with pytest.raises(ContractError, match='initial state'):
        tool.build(directory, rendered(), providers, {}, tmp_path / 'a', now=NOW, port_factory=factory)
    (directory / 'initial-state.json').write_bytes(files['initial-state.json'])
    (tmp_path / 'b').mkdir()
    with pytest.raises(FileExistsError):
        tool.build(directory, rendered(), providers, {}, tmp_path / 'b', now=NOW, port_factory=factory)
    with pytest.raises(ContractError, match='not a runtime provider'):
        tool.build(directory, rendered(), [dict(url='https://other.invalid/', source_id='x')], {}, tmp_path / 'c',
                   now=NOW, port_factory=factory)


def test_quotes_from_another_wallet_are_not_covered(tmp_path):
    _, directory, runtime = prepared(tmp_path)
    _, result, _ = tool.build(directory, rendered(), runtime['driver']['balance_rpc_providers'], {}, tmp_path / 'caps',
                              now=NOW, port_factory=lambda a: FakePort(a, wallet='0x' + '2' * 40))
    assert result['numeric_status'] == 'BLOCKED' and 'QUOTE_ARTIFACT_REFUSED' in result['blockers']

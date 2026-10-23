"""IDEA-088 QV10: the live read-only quote check, offline. Recorded quotes and fake RPC state only; no network."""
from copy import deepcopy
import hashlib
import json
import uuid

import pytest

from larp.execution_live import untrusted_router as u
from larp.marketdata.web3 import Artifacts, Unavailable
from tests.execution.test_untrusted_router import FakeRpc, policy
from tests.marketdata.test_live_port import Client
from tests.marketdata.test_untrusted_quote_verifier import changed, profile, recorded, side_of
from tools.deploy import quote_check as qc

KEY, SECRET = 'synthetic-web3-key-0123456789', 'synthetic-web3-secret-9876543210'
URL = 'https://rpc.invalid/private-path'
WALLET = '0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479'
TSLAB = '0x5b1910eaad6450e50f816082aa078c41f10c292f'


def tslab():
    """The recorded TSLAB pair: a 40 USDT BUY and the SELL of exactly its output (the tool's default SELL)."""
    rows = [r for r in recorded() if TSLAB in (r['params']['fromTokenAddress'], r['params']['toTokenAddress'])]
    buy = next(r for r in rows if side_of(r) == 'BUY')
    received = buy['response']['data']['routerResult']['toTokenAmount']
    sell = next(r for r in rows if side_of(r) == 'SELL' and r['params']['amount'] == received)
    return buy, sell


class FakeClient(Client):
    def __init__(self, buy, sell):
        self.buy, self.sell, self.endpoints = buy, sell, []

    def request(self, method, endpoint, params):
        self.endpoints.append(endpoint)
        if endpoint != 'aggregator/quote-and-swap':
            return super().request(method, endpoint, params)
        return deepcopy(self.buy if params['fromTokenAddress'] == qc.USDT else self.sell)


class ChainRpc(FakeRpc):
    source_id = 'synthetic'

    def call(self, method, params):
        if method == 'eth_chainId':
            return '0x38'
        return super().call(method, params)


@pytest.fixture
def pinned(tmp_path, monkeypatch):
    """The run-3 profile at the recorded quotes' 40 USDT / 0.5 % and the test router policy, pinned by hash."""
    files = dict(profile=json.dumps(profile(per_trade_cap_units=40_100_000, cost_reserve_units=100_000)).encode(),
                 policy=json.dumps(policy()).encode())
    for name, raw in files.items():
        (tmp_path / name).write_bytes(raw)
        monkeypatch.setattr(qc, name.upper(), tmp_path / name)
        monkeypatch.setattr(qc, name.upper() + '_SHA', hashlib.sha256(raw).hexdigest())
    (tmp_path / '.env').write_text(f'BINANCE_API_KEY={KEY}\nBINANCE_SECRET_KEY={SECRET}\n')
    return tmp_path


def check(pinned, capsys, *argv, buy=None, sell=None, rpc_state=None):
    pair = tslab()
    buy, sell = buy or pair[0], sell or pair[1]
    decoder = u.UntrustedRouterDecoder(policy())
    pay = qc.USDT if '--side' not in argv else qc.TOKENS['TSLAB']
    rpc = ChainRpc(decoder, WALLET, pay, 0, **(rpc_state or {}))
    client = FakeClient(buy, sell)
    code = qc.main(['--symbol', 'TSLAB', '--env-file', str(pinned / '.env'), '--rpc-url', URL,
                    '--out', str(pinned / ('artifacts-' + uuid.uuid4().hex)), *argv],
                   client=client, rpcs=[rpc], now=lambda: max(buy['available_at'], sell['available_at']))
    out = capsys.readouterr().out
    return code, out, client


def private(out, buy):
    return [v for v in (KEY, SECRET, URL, WALLET, WALLET[2:], buy['response']['data']['tx']['data'][10:74])
            if v.lower() in out.lower()]


def test_qv10_a_recorded_buy_is_verified_executable_and_prints_only_public_values(pinned, capsys):
    buy, _ = tslab()
    code, out, client = check(pinned, capsys)
    report = json.loads(out)
    assert (code, report['status'], report['quote_status']) == (0, 'VERIFIED_EXECUTABLE', 'VERIFIED_EXECUTABLE')
    e = report['economics']
    assert (e['pay_token'], e['receive_token'], e['amount']) == (qc.USDT, TSLAB, str(40 * 10**18))
    assert e['minimum_output'] == buy['response']['data']['tx']['minReceiveAmount']
    assert (e['recipient'], report['quote_at_cap']['accepted']) == ('UNVERIFIED_UNTRUSTED_LAYOUT', True)
    assert (report['gas_basis'], report['fee_units'], report['slippage_bps']) == ('EXECUTION_FEE_AUTHORITY', 0, 50)
    assert report['signing_enabled'] is False and private(out, buy) == []
    assert set(client.endpoints) <= {e for _, e in qc.ReadOnlyClient.endpoints}


def test_qv10_the_default_sell_is_the_buy_output_and_is_verified(pinned, capsys):
    buy, sell = tslab()
    code, out, _ = check(pinned, capsys, '--side', 'SELL', '--mandatory')
    report = json.loads(out)
    assert (code, report['status']) == (0, 'VERIFIED_EXECUTABLE')
    assert report['economics']['amount'] == buy['response']['data']['routerResult']['toTokenAmount']
    assert report['sell_amount_basis'] == 'HYPOTHETICAL_BUY_OUTPUT'


def test_qv10_tampered_and_mismatched_quotes_exit_2_with_the_exact_reason(pinned, capsys):
    buy, _ = tslab()
    tampered = changed(buy, data=u.mutations(buy['response']['data']['tx']['data'])['inner_amount'])
    code, out, _ = check(pinned, capsys, buy=tampered)
    report = json.loads(out)
    assert (code, report['status']) == (2, 'REFUSED')
    assert report['reason'] == 'quote proof refused: outer and inner swap economics disagree'
    assert private(out, buy) == []
    code, out, _ = check(pinned, capsys, buy=changed(buy, minReceiveAmount='1'))
    assert (code, json.loads(out)['reason']) == (2, 'decoded route does not bind quote economics')
    code, out, _ = check(pinned, capsys, rpc_state=dict(storage='0x' + '0' * 24 + '2' * 40))
    assert json.loads(out)['reason'] == 'quote proof refused: router dispatches the swap selector to another facet'


def test_qv10_a_reflected_credential_is_refused_and_never_printed(pinned, capsys):
    buy, _ = tslab()

    class Leaky(FakeClient):
        def request(self, method, endpoint, params):
            if endpoint == 'aggregator/quote-and-swap':
                raise Unavailable('provider said ' + KEY)
            return super().request(method, endpoint, params)
    code = qc.main(['--symbol', 'TSLAB', '--env-file', str(pinned / '.env'), '--rpc-url', URL,
                    '--out', str(pinned / 'artifacts')],
                   client=Leaky(*tslab()), rpcs=[ChainRpc(u.UntrustedRouterDecoder(policy()), WALLET, qc.USDT, 0)],
                   now=lambda: buy['available_at'])
    out = capsys.readouterr().out
    assert code == 4 and KEY not in out and json.loads(out)['status'] == 'CHECK_REFUSED'


def test_qv10_pinned_profile_and_policy_hashes_are_enforced(pinned, capsys, monkeypatch):
    for name in ('PROFILE_SHA', 'POLICY_SHA'):
        with monkeypatch.context() as m:
            m.setattr(qc, name, '0' * 64)
            code, out, _ = check(pinned, capsys)
            assert code == 4 and json.loads(out)['status'] == 'CHECK_REFUSED'


def test_qv10_the_shipped_pins_are_the_run_3_profile_and_the_ld03_policy():
    assert hashlib.sha256(qc.PROFILE.read_bytes()).hexdigest() == qc.PROFILE_SHA
    assert qc.PROFILE_SHA.startswith('6bcf1dfb') and qc.POLICY_SHA.startswith('05759e90')
    assert hashlib.sha256(qc.POLICY.read_bytes()).hexdigest() == qc.POLICY_SHA
    assert qc.DEV_WALLET == WALLET


def test_qv10_the_client_cannot_approve_estimate_gas_or_broadcast(tmp_path):
    client = qc.ReadOnlyClient('synthetic-key', 'synthetic-secret', artifacts=Artifacts(tmp_path))
    for method, endpoint in (('GET', 'aggregator/approve-transaction'), ('POST', 'pre-transaction/gas-limit'),
                             ('POST', 'pre-transaction/broadcast-transaction')):
        with pytest.raises(Unavailable, match='allowlist'):
            client.request(method, endpoint, {})


def test_qv10_artifacts_stay_outside_the_checkout(pinned, capsys):
    code = qc.main(['--symbol', 'TSLAB', '--env-file', str(pinned / '.env'), '--rpc-url', URL,
                    '--out', str(qc.ROOT / 'quote-check-artifacts')])
    out = capsys.readouterr().out
    assert code == 4 and json.loads(out)['status'] == 'CHECK_REFUSED'
    assert not (qc.ROOT / 'quote-check-artifacts').exists()


class ClosedClient(FakeClient):
    """Token and underlying both report openState false (a weekend or holiday)."""

    def request(self, method, endpoint, params):
        r = super().request(method, endpoint, params)
        if endpoint in ('market/rwa/tokens', 'market/rwa/underlying-market'):
            for row in r['response']['data']:
                row['statusInfo'] = {'openState': False}
        return r


def closed_check(pinned, capsys, buy):
    _, sell = tslab()
    rpc = ChainRpc(u.UntrustedRouterDecoder(policy()), WALLET, qc.USDT, 0)
    code = qc.main(['--symbol', 'TSLAB', '--env-file', str(pinned / '.env'), '--rpc-url', URL,
                    '--out', str(pinned / ('artifacts-' + uuid.uuid4().hex))],
                   client=ClosedClient(buy, sell), rpcs=[rpc], now=lambda: buy['available_at'])
    return code, json.loads(capsys.readouterr().out)


def test_qv12_closed_markets_are_reported_and_do_not_decide_the_verdict(pinned, capsys):
    buy, _ = tslab()
    code, report = closed_check(pinned, capsys, buy)
    assert (code, report['status']) == (0, 'VERIFIED_EXECUTABLE')
    assert (report['token_open'], report['underlying_open']) == (False, False)


def test_qv12_a_refused_quote_still_reports_both_open_states(pinned, capsys):
    buy, _ = tslab()
    code, report = closed_check(pinned, capsys, changed(buy, minReceiveAmount='1'))
    assert (code, report['status']) == (2, 'REFUSED')
    assert (report['token_open'], report['underlying_open']) == (False, False)
    code, out, _ = check(pinned, capsys, buy=changed(buy, minReceiveAmount='1'))
    assert (json.loads(out)['token_open'], json.loads(out)['underlying_open']) == (True, True)

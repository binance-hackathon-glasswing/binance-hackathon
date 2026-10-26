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


def test_blocked_preflight_report_has_nonzero_cli_exit(monkeypatch):
    import sys
    from tools.deploy import replay_router_readonly as probe
    monkeypatch.setattr(sys, 'argv', ['probe', '--out', '/unused', '--profile', '/unused',
                                    '--providers', '/unused', '--env-file', '/unused'])
    monkeypatch.setattr(probe, 'run', lambda args: False)
    assert probe.main() == 2


@pytest.mark.parametrize('outcome', ['pass', 'refused', 'stale', 'tampered'])
def test_probe_cli_reports_actual_measurement_failures_without_public_private_values(tmp_path, monkeypatch, capsys, outcome):
    import itertools
    import sys
    from types import SimpleNamespace
    from tools.deploy import replay_router_readonly as probe

    wallet = '0x' + '12' * 20
    secrets = {'BINANCE_API_KEY': 'synthetic-private-key',
               'BINANCE_SECRET_KEY': 'synthetic-private-secret', 'AI_SEEDS_ADDRESS': wallet}
    providers = [{'source_id': source, 'url': 'https://private-' + source.lower() + '.invalid'}
                 for source in probe.SOURCES]
    settings = tmp_path / 'providers.json'
    settings.write_text(json.dumps({'balance_rpc_providers': providers}))
    profile = probe.ROOT / 'docs/build/evidence/gc01-bounded-profiles-20261021/rehearsal-live.json'
    target = tmp_path / 'capture'
    economics = {}

    class QuoteClient:
        def __init__(self, key, secret, *, artifacts):
            self.artifacts = artifacts

    class Market:
        def __init__(self, client, wallet, *, quote_limits):
            self.client = client

        def metadata(self):
            return {s: ({'statusInfo': {'openState': True}, 'decimals': 18}, None) for s in probe.TOKENS}

        def quote(self, symbol, side, amount, decimals):
            data = '0x' + format(len(economics), '064x')
            pay, receive = ((probe.USDT, probe.TOKENS[symbol]) if side == 'BUY'
                            else (probe.TOKENS[symbol], probe.USDT))
            economics[data] = SimpleNamespace(pay_token=pay, receive_token=receive, amount=amount, minimum_output=1)
            row = {'available_at': '2026-10-21T00:00:00Z', 'response': {'data': {
                'tx': {'to': '0x' + '34' * 20, 'value': '0', 'gas': '1', 'gasPrice': '1',
                       'data': data, 'minReceiveAmount': '1'}, 'routerResult': {'toTokenAmount': '2'}}}}
            row['artifact_sha256'] = self.client.artifacts.put(row)
            return row

    class ReadRpc:
        def __init__(self, url, *, source_id, artifacts):
            self.source_id, self.read_count = source_id, 0

        def call(self, method, params):
            self.read_count += 1
            return '0x38'

    class Decoder:
        router = '0x' + '34' * 20

        def decode(self, payload):
            return economics[payload.data]

        def bind(self, rpc):
            self.rpc = rpc
            return self

        def preflight(self, intent, payload, *, approved):
            if outcome == 'refused' and self.rpc.source_id == probe.SOURCES[1]:
                raise Blocked('synthetic-private-secret')

    def replay(decoder, directory):
        assert len(list(directory.glob('*.json'))) == 10
        return {'status': 'FAIL' if outcome == 'tampered' else 'PASS', 'quotes': 10}

    monkeypatch.setattr(probe, 'credentials', lambda *a, **kw: secrets)
    monkeypatch.setattr(probe, 'QuoteOnlyClient', QuoteClient)
    monkeypatch.setattr(probe, 'MarketPort', Market)
    monkeypatch.setattr(probe, 'BoundedRpc', ReadRpc)
    monkeypatch.setattr(probe, 'load_policy', lambda *a: Decoder())
    monkeypatch.setattr(probe, 'check', replay)
    monkeypatch.setattr(probe.time, 'monotonic', itertools.count(step=31 if outcome == 'stale' else 0.5).__next__)
    monkeypatch.setattr(sys, 'argv', ['probe', '--out', str(target), '--profile', str(profile),
                                    '--providers', str(settings), '--env-file', str(tmp_path / 'unused')])
    assert probe.main() == (0 if outcome == 'pass' else 2)
    report = json.loads((target / 'report.json').read_bytes())
    assert report['status'] == ('PASS_LOCAL_READONLY' if outcome == 'pass' else 'BLOCKED_LOCAL_READONLY')
    assert len(report['rows']) == 10
    assert not report['signing_enabled'] and not report['host_binding_accepted']
    if outcome == 'refused':
        assert all(row['preflight'][probe.SOURCES[1]] == {'status': 'REFUSED', 'error_type': 'Blocked'}
                   for row in report['rows'])
    if outcome == 'stale':
        assert all(not row['within_profile_quote_age'] for row in report['rows'])
    public = (target / 'report.json').read_text() + capsys.readouterr().out
    assert not any(value.lower() in public.lower() for value in [*secrets.values(), *[p['url'] for p in providers]])

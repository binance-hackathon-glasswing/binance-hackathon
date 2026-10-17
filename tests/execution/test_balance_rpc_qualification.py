"""IDEA-055 RPC-Q01: real transport/consumer, synthetic node; no public credentials or transactions."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from larp.execution_live.chain import Rpc
from larp.marketdata.web3 import NoRedirect, encoded
from tests.runtime.test_gate_a import Node
from tests.marketdata.test_transport import Response
from tools.deploy import qualify_balance_rpc as tool

PROVIDERS = [dict(url='https://rpc.invalid/path/PRIVATE_KEY', source_id='BSC_FIXTURE_PRIMARY'),
             dict(url='https://backup.invalid/?key=PRIVATE_KEY', source_id='BSC_FIXTURE_BACKUP')]


class NodeTransport:
    def __init__(self, node=None, defect=None):
        self.node, self.defect, self.calls = node or Node(), defect, []

    def open(self, request, timeout):
        self.asserted_timeout = timeout
        call = json.loads(request.data)
        method, params = call['method'], call['params']
        self.calls.append((method, params))
        if self.defect == 'unavailable':
            raise URLError('PRIVATE_KEY')
        if self.defect == 'redirect':
            raise HTTPError(request.full_url, 302, 'PRIVATE_KEY', {}, None)
        result = self.node.call(method, params)
        if self.defect == 'chain' and method == 'eth_chainId':
            result = '0x1'
        if self.defect == 'finalized' and method == 'eth_getBlockByNumber' and params[0] == 'finalized':
            return Response(encoded(dict(jsonrpc='2.0', id=call['id'], error=dict(message='PRIVATE_KEY'))))
        if self.defect == 'canonical' and method == 'eth_getBlockByNumber' and params[0] != 'finalized':
            result = dict(result, hash='0x' + 'e' * 64)
        if self.defect == 'word' and method == 'eth_call':
            result = '0x1'
        if self.defect == 'scale' and method == 'eth_call' and params[0]['data'] == '0x313ce567':
            result = '0x' + format(78, '064x')
        return Response(encoded(dict(jsonrpc='2.0', id=call['id'], result=result)))


class BalanceRpcQualification(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='larp-rpc-qualification-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.config = self.root / 'providers.json'
        self.config.write_bytes(encoded(dict(balance_rpc_providers=PROVIDERS)))
        self.out = self.root / 'probe'
        self.state = dict(commit='a' * 40, dirty=False, pushed=True)

    def run_cli(self, defects=None, **changes):
        transports = {p['source_id']: NodeTransport(defect=(defects or {}).get(p['source_id'])) for p in PROVIDERS}
        def factory(url, *, artifacts, source_id):
            return Rpc(url, artifacts=artifacts, source_id=source_id, opener=transports[source_id])
        stdout = io.StringIO()
        with redirect_stdout(stdout), patch('subprocess.run', side_effect=AssertionError('unexpected subprocess')):
            code = tool.main(['--config', str(self.config), '--out', str(self.out)],
                             state=changes.get('state', self.state), rpc_factory=factory)
        text = stdout.getvalue()
        for private in ('PRIVATE_KEY', 'rpc.invalid', 'backup.invalid', tool.PROBE_WALLET):
            self.assertNotIn(private, text)
        return code, json.loads(text), transports

    def test_exact_runtime_read_contract_with_separate_canonical_observations(self):
        code, report, transports = self.run_cli()
        self.assertEqual(code, 0)
        self.assertTrue(report['all_passed'])
        self.assertFalse(report['providers_adopted'])
        self.assertFalse(report['signing_enabled'])
        self.assertFalse(report['round_logs_uploaded'])
        self.assertEqual(report['hosted_check'], 'NOT_RUN')
        self.assertEqual(report['native_trace'], 'NOT_RUN')
        for row in report['results']:
            self.assertEqual(row['status'], 'PASS')
            self.assertEqual(row['observation_count'], 19)
            files = self.out / row['source_id']
            raw = (files / 'chain-capture.json').read_bytes()
            self.assertEqual(tool.digest(raw), row['capture_sha256'])
            capture = json.loads(raw)
            self.assertEqual(capture['wallet'], tool.PROBE_WALLET)
            self.assertEqual(set(capture['tokens']), {'USDT', 'NVDAB', 'GOOGLB', 'SKHYB', 'TSLAB', 'MSFTB'})
            calls = transports[row['source_id']].calls
            self.assertEqual(len([m for m, _ in calls if m == 'eth_call']), 12)
            self.assertTrue(all(p[1] == '0x1f4' for m, p in calls if m == 'eth_call'))
            self.assertEqual({p[1] for m, p in calls if m == 'eth_getTransactionCount'},
                             {'latest', 'pending', '0x1f4'})
            self.assertEqual(transports[row['source_id']].asserted_timeout, 20)
            self.assertTrue(all(m != 'eth_sendRawTransaction' for m, _ in calls))
            for sha in row['observation_hashes']:
                self.assertEqual(tool.digest((files / (sha + '.json')).read_bytes()), sha)

    def test_bad_provider_is_recorded_and_not_hidden_by_good_backup(self):
        for defect in ('chain', 'finalized', 'canonical', 'word', 'scale', 'unavailable', 'redirect'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as root:
                self.out = Path(root) / 'probe'
                code, report, _ = self.run_cli({PROVIDERS[0]['source_id']: defect})
                self.assertEqual(code, 1)
                self.assertFalse(report['all_passed'])
                first, second = report['results']
                self.assertEqual(first['status'], 'UNAVAILABLE' if defect in ('unavailable', 'redirect') else 'REFUSED')
                self.assertIsNone(first['capture_sha256'])
                self.assertEqual(second['status'], 'PASS')
                self.assertFalse((self.out / first['source_id'] / 'chain-capture.json').exists())

    def test_provider_config_refuses_duplicates_bad_urls_source_ids_and_excess_providers(self):
        cases = [dict(balance_rpc_providers=[]), dict(balance_rpc_providers=PROVIDERS * 3),
                 dict(balance_rpc_providers=[PROVIDERS[0], PROVIDERS[0]]),
                 dict(balance_rpc_providers=[dict(PROVIDERS[0], url='http://rpc.invalid')]),
                 dict(balance_rpc_providers=[dict(PROVIDERS[0], url='https://user:PRIVATE_KEY@rpc.invalid')]),
                 dict(balance_rpc_providers=[dict(PROVIDERS[0], url='https://rpc.invalid:444')]),
                 dict(balance_rpc_providers=[dict(PROVIDERS[0], url='https://rpc.invalid/#fragment')]),
                 dict(balance_rpc_providers=[dict(PROVIDERS[0], source_id='../PRIVATE_KEY')]),
                 dict(balance_rpc_providers=PROVIDERS, unexpected='PRIVATE_KEY')]
        for value in cases:
            with self.subTest(value=value):
                self.config.write_bytes(encoded(value))
                code, report, _ = self.run_cli()
                self.assertEqual(code, 4)
                self.assertEqual(report['reason'], 'PROBE_INPUTS_REFUSED')
                self.assertFalse(self.out.exists())

    def test_dirty_unpushed_or_existing_output_refuses_before_network(self):
        for state in (dict(self.state, dirty=True), dict(self.state, pushed=False)):
            code, report, transports = self.run_cli(state=state)
            self.assertEqual(code, 4)
            self.assertTrue(all(not t.calls for t in transports.values()))
            self.assertFalse(self.out.exists())
        self.out.mkdir()
        marker = self.out / 'keep'
        marker.write_bytes(b'original')
        code, _, transports = self.run_cli()
        self.assertEqual(code, 4)
        self.assertEqual(marker.read_bytes(), b'original')
        self.assertTrue(all(not t.calls for t in transports.values()))

    def test_outputs_inside_repository_and_symlink_destinations_refuse(self):
        for path in (tool.ROOT / 'deploy/activation/forbidden-probe', tool.ROOT / 'data/forbidden-probe'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                tool.new_output(path)
            self.assertFalse(path.exists())
        linked = self.root / 'linked'
        linked.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            tool.new_output(linked)

    def test_config_symlink_and_tracked_config_are_refused(self):
        link = self.root / 'link.json'
        link.symlink_to(self.config)
        with self.assertRaises(ValueError):
            tool.private_config(link)
        self.assertIsNone(NoRedirect().redirect_request(None, None, None, None, None, None))
        with self.assertRaises(ValueError):
            tool.private_config(tool.ROOT / 'config/runtime/runtime.example.json')


if __name__ == '__main__':
    unittest.main()

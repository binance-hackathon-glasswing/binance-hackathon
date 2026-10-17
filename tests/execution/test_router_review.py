"""RV-130 R11-R14 regressions. Synthetic ABI/artifacts only; no real router qualification."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from larp.contracts import ContractError
from larp.execution import USDT
from larp.execution_live.router import PinnedRouterDecoder, check_routes, selector, mutations
from tests.execution.test_router_decoder import evidence, quote, artifact, calldata, payload, TOKEN, ROUTER
from tests.execution.test_router_wiring import GateBReport as _GateBReport


class EvidenceReview(unittest.TestCase):
    def test_wallet_debit_guarantee_is_required(self):
        for value in (None, False, 1):
            candidate = deepcopy(evidence())
            if value is None:
                candidate['guarantees'].pop('wallet_debits_limited_to_pay_token_and_amount', None)
            else:
                candidate['guarantees']['wallet_debits_limited_to_pay_token_and_amount'] = value
            with self.subTest(value=value), self.assertRaises(ContractError):
                PinnedRouterDecoder(candidate)

    def test_invalid_types_even_in_unreferenced_arguments_refuse_evidence(self):
        for suffix in ('uint7', 'uint264', 'bytes33', 'uint256[0]', 'notAnAbiType'):
            signature = 'swap((address,address,uint256,uint256,address,uint256),' + suffix + ')'
            candidate = evidence(function=dict(signature=signature, selector=selector(signature)))
            with self.subTest(suffix=suffix), self.assertRaises(ContractError):
                PinnedRouterDecoder(candidate)


class RouteReview(unittest.TestCase):
    def setUp(self):
        self.decoder = PinnedRouterDecoder(evidence(), evidence_sha256='e' * 64)

    def report_changed(self, change):
        with tempfile.TemporaryDirectory() as directory:
            quote(directory, USDT, TOKEN, 100, 90)
            quote(directory, TOKEN, USDT, 50, 40)
            for path in Path(directory).glob('*.json'):
                row = json.loads(path.read_bytes())
                if row['params']['fromTokenAddress'] == USDT:
                    change(row)
                    path.write_text(json.dumps(row))
            return check_routes(self.decoder, directory)

    def test_chain_mode_and_execution_numbers_are_not_assumed(self):
        cases = {
            'wrong chain': lambda row: row['params'].update(binanceChainId='1'),
            'chain absent': lambda row: row['params'].pop('binanceChainId'),
            'RFQ': lambda row: row['response']['data'].update(executionMode='RFQ'),
            'RFQ payload': lambda row: row['response']['data'].update(rfq={}),
            'zero gas': lambda row: row['response']['data']['tx'].update(gas='0'),
            'negative gas price': lambda row: row['response']['data']['tx'].update(gasPrice='-1'),
            'boolean gas': lambda row: row['response']['data']['tx'].update(gas=True),
            'failed API response': lambda row: row['response'].update(code=1),
        }
        for name, change in cases.items():
            with self.subTest(name):
                self.assertEqual(self.report_changed(change)['status'], 'FAIL')

    def test_zero_economics_or_unsupported_pair_cannot_be_extra_passing_routes(self):
        for pay, receive, amount, minimum, data in (
                (USDT, TOKEN, 0, 90, calldata(amount=0)),
                (USDT, TOKEN, 100, 0, calldata(minimum=0)),
                (USDT, TOKEN, 100, 90, calldata(deadline=0)),
                (USDT, '0x' + '44' * 20, 100, 90, calldata(receive='0x' + '44' * 20))):
            with self.subTest(pay=pay, receive=receive, amount=amount, minimum=minimum), tempfile.TemporaryDirectory() as directory:
                quote(directory, USDT, TOKEN, 100, 90)
                quote(directory, TOKEN, USDT, 50, 40)
                quote(directory, pay, receive, amount, minimum, data=data)
                self.assertEqual(check_routes(self.decoder, directory)['status'], 'FAIL')

    def test_malformed_approval_or_json_produces_fail_instead_of_crash_or_omission(self):
        for broken_json in (False, True):
            with self.subTest(broken_json=broken_json), tempfile.TemporaryDirectory() as directory:
                quote(directory, USDT, TOKEN, 100, 90)
                quote(directory, TOKEN, USDT, 50, 40)
                if broken_json:
                    (Path(directory) / 'broken.json').write_text('{')
                else:
                    artifact(directory, 'aggregator/approve-transaction', {}, {})
                self.assertEqual(check_routes(self.decoder, directory)['status'], 'FAIL')

    def test_uint_boundary_mutations_remain_encodable_and_change_economics(self):
        original = payload(calldata(amount=2**256-1, deadline=2**256-1))
        economics = self.decoder.decode(original)
        changed = mutations(self.decoder, original)
        for field in ('amount', 'deadline'):
            self.assertNotEqual(self.decoder.decode(replace(original, data=changed[field][0])), economics)


class ReportReview(unittest.TestCase):
    setUp = _GateBReport.setUp
    report = _GateBReport.report
    with_router = _GateBReport.with_router

    def test_header_only_pass_is_not_route_evidence(self):
        inputs = self.with_router()
        path = Path(inputs['files']['router_check']['path'])
        check = json.loads(path.read_bytes())
        check = {key: check[key] for key in ('schema', 'status', 'router', 'selector', 'evidence_sha256')}
        raw = json.dumps(check).encode()
        path.write_bytes(raw)
        inputs['files']['router_check']['sha256'] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(self.report(inputs)['checks']['DR-02']['status'], 'BLOCKED')

    def test_report_contents_are_bound_to_wallet_routes_and_artifact_hashes(self):
        changes = {
            'no routes': lambda check: check.update(routes=[]),
            'wrong chain': lambda check: check.update(chain_id=1),
            'only buy': lambda check: check.update(directions=['BUY']),
            'no artifact hashes': lambda check: check.update(artifacts_read=[]),
            'unread route hash': lambda check: check['routes'][0].update(artifact_sha256='0'*64),
            'route problem': lambda check: check['routes'][0].update(problems=['mismatch']),
            'wrong wallet': lambda check: check['routes'][0]['decoded'].update(recipient='0x'+'99'*20),
            'zero amount': lambda check: check['routes'][0]['decoded'].update(amount='0'),
        }
        for name, change in changes.items():
            with self.subTest(name):
                inputs = self.with_router()
                path = Path(inputs['files']['router_check']['path'])
                check = json.loads(path.read_bytes())
                change(check)
                raw = json.dumps(check).encode()
                path.write_bytes(raw)
                inputs['files']['router_check']['sha256'] = hashlib.sha256(raw).hexdigest()
                result = self.report(inputs)
                self.assertEqual(result['checks']['DR-02']['status'], 'BLOCKED')
                self.assertFalse(result['signing_enabled'])


class OfflineDependencyReview(unittest.TestCase):
    def test_fake_executor_and_config_check_do_not_import_signing_packages(self):
        import subprocess
        import sys
        script = '''
import importlib.abc
import sys
from types import SimpleNamespace
class RefuseSigningPackages(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'eth_abi', 'eth_utils', 'eth_account'}:
            raise ModuleNotFoundError('signing dependency forbidden: ' + fullname)
sys.meta_path.insert(0, RefuseSigningPackages())
from larp.execution import Executor, Blocked
from larp.execution_live.main import validate_config
fake = SimpleNamespace(mode='fake')
Executor(None, fake, fake, fake, fake)
try:
    Executor(None, SimpleNamespace(mode='live'), fake, fake, fake)
except Blocked:
    pass
else:
    raise AssertionError('mixed capability bundle accepted')
validate_config(dict(schema='ExecutionService.v1', run_id='synthetic', build_id='a'*40,
                     mode='dev', wallet_address='0x'+'1'*40, interval_seconds=1,
                     database_dsn_file='/synthetic'))
'''
        result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

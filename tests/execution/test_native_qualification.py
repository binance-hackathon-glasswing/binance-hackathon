"""NT-Q1: use the actual receipt/trace path, prove refusals and keep private URLs out of output."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from larp.execution import Blocked
from tests.execution import test_gate_b_native as native_fixtures
from tests.execution_fixtures import WALLET, ROUTER
from tests.execution import test_settlement as fixtures
from tools.deploy import qualify_native_rpc as q


class NativeQualification(unittest.TestCase):
    def inputs(self):
        return dict(schema='NativeRpcQualificationInputs.v1', wallet=WALLET, tx_hash=fixtures.HASH,
                    providers=[dict(source_id='TEST_NATIVE', url='https://rpc.invalid/private-secret')])

    def factory(self, *, bad=None, calls=None):
        def factory(url, **kwargs):
            rpc, seen = native_fixtures.NativeRPC().rpc(bad=bad)
            rpc.source_id = kwargs['source_id']
            rpc.opener = object()  # synthetic call implementation never opens a socket
            if calls is not None:
                calls.append(seen)
            return rpc
        return factory

    def run_probe(self, value=None, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            return q.probe(q.validate_inputs(value or self.inputs()), Path(tmp), build_id='a'*40, **kwargs)

    def test_actual_chain_proof_is_rechecked_and_no_runtime_or_host_authority_is_implied(self):
        calls = []
        report = self.run_probe(rpc_factory=self.factory(calls=calls))
        self.assertTrue(report['all_transaction_proofs_passed'], report)
        row = report['results'][0]
        self.assertEqual(row['rpc_calls'], 15)
        self.assertEqual(sum(m == 'eth_getTransactionReceipt' for m, _ in calls[0]), 2)
        self.assertEqual(row['net_native_inflow_excluding_gas_wei'], str(2*10**15))
        for field in ('signing_enabled', 'runtime_enabled', 'providers_selected'):
            self.assertFalse(report[field])
        self.assertEqual(report['hosted_check'], 'NOT_RUN')
        self.assertNotIn('private-secret', json.dumps(report))

    def test_reorg_missing_wallet_and_trace_nonce_mismatch_cannot_pass(self):
        for bad in ('reorg', 'missing', 'nonce'):
            with self.subTest(bad=bad):
                report = self.run_probe(rpc_factory=self.factory(bad=bad))
                self.assertFalse(report['all_transaction_proofs_passed'])
                self.assertEqual(report['results'][0]['status'], 'INCONCLUSIVE')

    def test_foreign_wallet_and_no_positive_credit_cannot_pass(self):
        value = self.inputs();value['wallet'] = ROUTER
        self.assertFalse(self.run_probe(value, rpc_factory=self.factory())['all_transaction_proofs_passed'])
        rpc, _ = native_fixtures.NativeRPC().rpc()
        from larp.execution_live.chain import ChainEvidence
        proof = ChainEvidence(rpc).native_receipt(fixtures.HASH)
        proof['native_balance']['after_wei'] = proof['native_balance']['before_wei'] - 500000
        with self.assertRaises(Blocked):
            q.native_credit(proof, q.validate_inputs(self.inputs()))

    def test_wrong_chain_and_reverted_receipt_cannot_qualify_native_credit(self):
        for bad in ('chain', 'revert'):
            def factory(url, **kwargs):
                rpc = self.factory()(url, **kwargs)
                original = rpc.call
                def call(method, params):
                    value = original(method, params)
                    if bad == 'chain' and method == 'eth_chainId':return '0x1'
                    if bad == 'revert' and method == 'eth_getTransactionReceipt':
                        return dict(value, status='0x0')
                    return value
                rpc.call = call
                return rpc
            with self.subTest(bad=bad):
                self.assertFalse(self.run_probe(rpc_factory=factory)['all_transaction_proofs_passed'])

    def test_effective_receipt_gas_price_does_not_require_legacy_transaction_field(self):
        rpc, _ = native_fixtures.NativeRPC().rpc()
        from larp.execution_live.chain import ChainEvidence
        proof = ChainEvidence(rpc).native_receipt(fixtures.HASH)
        proof['receipt']['effectiveGasPrice'] = '0x2'
        proof['tx'].pop('gasPrice', None)
        flow, gas = q.native_credit(proof, q.validate_inputs(self.inputs()))
        self.assertEqual(gas, int(proof['receipt']['gasUsed'], 16) * 2)
        self.assertGreater(flow, 0)

    def test_read_budget_stops_before_extra_transport(self):
        class RPC:
            source_id = 'TEST_NATIVE'
            def call(self, method, params):return '0x38'
        rpc = q.BudgetRpc(RPC())
        for _ in range(q.CALL_LIMIT):rpc.call('eth_chainId', [])
        with self.assertRaises(Blocked):rpc.call('eth_chainId', [])
        self.assertEqual(rpc.calls, q.CALL_LIMIT)

    def test_invalid_inputs_and_private_output_refusals_happen_without_provider_use(self):
        for update in (dict(wallet=True), dict(tx_hash='bad'), dict(schema='wrong'), dict(providers=[])):
            with self.subTest(update=update), self.assertRaises((ValueError, Blocked)):
                q.validate_inputs(self.inputs() | update)
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp)/'inputs.json';config.write_text(json.dumps(self.inputs()));config.chmod(0o600)
            args = ['--inputs', str(config), '--out', str(Path(tmp)/'out')]
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(q.main(args, state=dict(commit='a'*40, dirty=True, pushed=True)), 4)
            self.assertNotIn('private-secret', stream.getvalue())
            self.assertFalse((Path(tmp)/'out').exists())
            target = q.new_output(Path(tmp)/'out')
            with self.assertRaises(FileExistsError):q.new_output(target)
            with self.assertRaises(ValueError):q.new_output(q.ROOT/'native-output')

    def test_unsupported_provider_error_is_sanitized(self):
        def factory(url, **kwargs):raise Blocked('echo https://rpc.invalid/private-secret')
        report = self.run_probe(rpc_factory=factory)
        self.assertFalse(report['all_transaction_proofs_passed'])
        self.assertNotIn('private-secret', json.dumps(report))

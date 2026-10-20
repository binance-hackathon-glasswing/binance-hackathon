"""Offline checks for the LD02c RFQ/RPC script (IDEA-070 LD02c R1-R4, Q1-Q4); no host or network calls."""
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'docs/build/ops/ld02-20261020/rfq-rpc-check.sh'
USDT = '0x55d398326f99059ff775485246999027b3197955'
WALLET = '0x' + 'ab' * 20


class Ld02cScriptTests(unittest.TestCase):
    def setUp(self):
        source = SCRIPT.read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        self.ns = {'__name__': 'offline_ld02c'}
        exec(compile(source, str(SCRIPT), 'exec'), self.ns)
        self.scope = dict(wallet=WALLET, usdt=USDT, tokens={USDT, '0x' + '1' * 40}, calldata={'0xad43f73d00'},
                          usdt_units=10**12)

    def test_q1_only_reads_and_exact_simulations_are_allowed(self):
        ok, s = self.ns['allowed_call'], self.scope
        override = {USDT: {'stateDiff': {'0x1': '0x2'}}}
        sim = {'from': WALLET, 'to': self.ns['ROUTER'], 'data': '0xad43f73d00', 'value': '0x0'}
        self.assertTrue(ok('eth_estimateGas', [sim, 'latest', override], s))
        self.assertTrue(ok('eth_getTransactionReceipt', ['0x' + '2' * 64], s))
        self.assertTrue(ok('eth_call', [dict(to=USDT, data='0x70a08231' + '0' * 64), 'latest'], s))
        for method, params in [
                ('eth_sendRawTransaction', ['0x00']),
                ('eth_estimateGas', [sim, 'latest']),                                    # no override
                ('eth_estimateGas', [dict(sim, data='0xad43f73d01'), 'latest', override]),  # not a fresh quote
                ('eth_estimateGas', [dict(sim, value='0x1'), 'latest', override]),
                ('eth_estimateGas', [dict(sim, **{'from': '0x' + 'cd' * 20}), 'latest', override]),
                ('eth_call', [dict(to=USDT, data='0xa9059cbb' + '0' * 128), 'latest']),   # transfer
                ('eth_call', [dict(to='0x' + '9' * 40, data='0x70a08231' + '0' * 64), 'latest']),
                ('eth_call', [dict(to=USDT, data='0xdd62ed3e' + '0' * 128), 'latest', {'0x' + '9' * 40: {}}])]:
            with self.subTest(method=method, params=str(params)[:50]):
                self.assertFalse(ok(method, params, s))
                with self.assertRaisesRegex(ValueError, 'RPC_(CALL|METHOD)_REFUSED'):
                    self.ns['rpc']('https://a.b', method, params, s)

    def test_r2_r3_schedule_and_observed_bounds(self):
        clock = {'t': 100.0}
        calls = []

        def rpc(url, method, params, scope, log=None):
            if method == 'eth_getBlockByNumber':
                return dict(number='0x10')
            if method == 'eth_getStorageAt':
                return hex(10**12)
            if method == 'eth_call':
                return hex(2**255)
            elapsed = clock['t'] - 100.0
            calls.append(round(elapsed))
            if params[0]['data'] == '0xrfq' and elapsed >= 10:
                raise self.ns['RpcRefused'](dict(code=3, message='execution reverted: adapter:0x1:Error(RFQ_OrderExpired x)'))
            return hex(500_000)
        self.ns['rpc'] = rpc
        quotes = {'MSFTB': dict(t0=100.0, data='0xrfq'), 'NVDAB': dict(t0=100.0, data='0xamm')}
        out = self.ns['rfq_check']('https://p', self.scope, quotes, sleep=lambda s: clock.__setitem__('t', clock['t'] + s),
                                   clock=lambda: clock['t'])
        self.assertEqual(out['status'], 'DONE')
        msft, nvda = out['symbols']['MSFTB'], out['symbols']['NVDAB']
        self.assertEqual((msft['last_success_s'], msft['first_failure_s']), (6, 10))
        self.assertEqual(msft['results']['10'], 'RFQ_OrderExpired')
        self.assertEqual((nvda['last_success_s'], nvda['first_failure_s']), (90, None))
        self.assertEqual(sorted(set(calls)), list(self.ns['DELAYS']))

    def test_r2_no_simulation_without_the_override_proof(self):
        self.ns['rpc'] = lambda url, method, params, scope, log=None: (
            dict(number='0x10') if method == 'eth_getBlockByNumber' else hex(1) if method == 'eth_getStorageAt' else hex(2**255))
        out = self.ns['rfq_check']('https://p', self.scope, {'MSFTB': dict(t0=0, data='0xrfq')})
        self.assertEqual((out['status'], out['symbols']), ('NOT_RUN', {}))

    def test_r1_route_markers_keep_names_and_short_routing_scalars_only(self):
        record = dict(response=dict(data=dict(executionMode='SWAP', rfq=None, tx=dict(data='0x' + 'ff' * 400),
            routerResult=dict(vendorName='LiquidMesh', toTokenAmount='5', dexRouterList=[dict(dexName='RFQ-MM', ratio='1')]))))
        m = self.ns['route_markers'](record)
        self.assertIn('tx', m['top_level_keys'])
        self.assertEqual(m['top_level'], dict(executionMode='SWAP', rfq=None))
        self.assertEqual(m['router_result'], dict(vendorName='LiquidMesh'))
        self.assertEqual(m['router_result_lists'], dict(dexRouterList=[dict(dexName='RFQ-MM')]))
        self.assertNotIn('ff' * 20, json.dumps(m))

    def test_q2_agreement_across_providers(self):
        def rpc(url, method, params, scope, log=None):
            if log is not None:
                log.append((method, 400))
            answers = {'eth_chainId': '0x38', 'eth_getBalance': '0x1', 'eth_getTransactionCount': '0x2',
                       'eth_getTransactionByHash': {'hash': '0x1'}, 'eth_getCode': '0x6001',
                       'eth_getStorageAt': '0x' + '0' * 24 + 'a' * 40, 'eth_call': '0x0',
                       'eth_getTransactionReceipt': dict(status='0x1', blockNumber='0x5', gasUsed='0x10')}
            if method == 'eth_getBlockByNumber':
                return dict(number='0x64' if url.endswith('a') else '0x60')
            return answers[method]
        self.ns['rpc'] = rpc
        out = self.ns['rpc_check']([dict(source_id='A', url='https://a'), dict(source_id='B', url='https://b')],
                                   self.scope, WALLET)
        self.assertEqual(out['status'], 'PASS')
        self.assertEqual(out['providers']['A']['receipt'], dict(status=1, block=5, gas_used=16))
        self.assertTrue(all(out['providers']['B']['methods_ok'].values()))
        self.assertEqual(out['finalized_concurrent']['pairs'], [[100, 96]] * 3)
        self.assertEqual(out['status_q2b'], 'PASS')

    def test_refusal_and_sanitizer(self):
        self.assertEqual(self.ns['refusal'](RuntimeError('rpc.example.org')),
                         dict(error='LD02C_REFUSED', signing_enabled=False, reason='RuntimeError'))
        with self.assertRaises(ValueError):
            self.ns['sanitize'](json.dumps(dict(x=WALLET)), [WALLET])
        with self.assertRaises(ValueError):
            self.ns['sanitize']('see https://x', [])


if __name__ == '__main__':
    unittest.main()

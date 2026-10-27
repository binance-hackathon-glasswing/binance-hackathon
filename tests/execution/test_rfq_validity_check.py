"""Offline checks for the OBS03-B2-RV01 RFQ validity collector (IDEA-104 RV-1..RV-5); no network calls."""
import io
import json
import unittest

from larp.execution import USDT
from larp.marketdata.port import TOKENS
from larp.marketdata.web3 import Unavailable
from tools.deploy import rfq_validity_check as rv

WALLET = rv.DEV_WALLET
PADDED = WALLET[2:].rjust(64, '0')
KEY, SECRET = 'fixture-api-key-0001', 'fixture-secret-0002'


def calldata(n):
    # second word: the outer deadline 500 s ahead; then a packed 4-byte time 1 s ahead (an RFQ order expiry)
    return rv.SWAP_SELECTOR + '%064x' % n + '%064x' % 1_800_000_500 + 'abcd' + '%08x' % 1_800_000_001 + 'ef'


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


class FakeClient:
    """Quotes in TOKENS order; `routes` gives each symbol's behaviour."""

    def __init__(self, clock, *, fail=()):
        self.clock, self.fail, self.calls, self.n = clock, set(fail), [], 0

    def request(self, method, endpoint, params):
        self.calls.append((method, endpoint, params))
        symbol = next(s for s, t in TOKENS.items() if t == params['toTokenAddress'])
        if symbol in self.fail:
            raise Unavailable('quote_unavailable')
        self.clock.t += 0.4
        self.n += 1
        return dict(response=dict(data=dict(executionMode='SWAP', rfq=None, tx=dict(
            to=rv.ROUTER, data=calldata(self.n), gas='450000'), routerResult=dict(
            vendorName='LiquidMesh', dexRouterList=[dict(dexProtocol=dict(
            dexName=('Rfq Maker' if symbol == 'NVDAB' else 'Pool-' + symbol), percent='100.00'))]))))


class FakeRpc:
    """Expiry per calldata: None = AMM (never expires); a number = RFQ order valid that long after the quote."""

    def __init__(self, clock, scope, expiry, *, proof=True):
        self.clock, self.scope, self.expiry, self.proof = clock, scope, expiry, proof
        self.calls, self.quote_t = [], {}

    def __call__(self, method, params):
        if not rv.allowed_call(method, params, self.scope):
            raise ValueError('RPC_CALL_REFUSED')
        self.calls.append(method)
        self.clock.t += 0.05
        if method == 'eth_chainId':
            return '0x38'
        if method == 'eth_getBlockByNumber':
            return dict(number='0x10', timestamp=hex(1_800_000_000))
        if method == 'eth_call':
            if not self.proof:
                return '0x1'
            return hex(rv.OVERRIDE_BALANCE if params[0]['data'].startswith(rv.BALANCE_OF_CALL) else rv.OVERRIDE_ALLOWANCE)
        data = params[0]['data']
        n = int(data[10:74], 16)
        self.quote_t.setdefault(data, self.clock.t)
        expiry = self.expiry(n)
        if expiry is not None and self.clock.t - self.quote_t[data] >= expiry:
            raise rv.RpcRefused(dict(code=3, message='execution reverted: adapter:0x1:Error(RFQ_OrderExpired x)'))
        return hex(550_000)


def fixture_credentials(path, environ):
    return dict(BINANCE_API_KEY=KEY, BINANCE_SECRET_KEY=SECRET)


class Args:
    env_file = None
    rounds = 1
    pay_units = 15_000_000
    rpc_url = 'https://rpc.fixture.example'
    out = None
    packet = None


class RfqValidityTests(unittest.TestCase):
    def setUp(self):
        self.scope = dict(wallet=WALLET, calldata={calldata(1)})
        self.state = rv.override(WALLET)

    def run_tool(self, expiry, *, proof=True, fail=(), rounds=1):
        clock = Clock()
        client = FakeClient(clock, fail=fail)
        holder = {}

        def rpc_factory(url, scope):
            holder['rpc'] = FakeRpc(clock, scope, expiry, proof=proof)
            return holder['rpc']
        args = Args()
        args.rounds = rounds
        code, raw = rv.run(args, client=client, rpc_factory=rpc_factory, credentials_source=fixture_credentials,
                           clock=clock, sleep=clock.sleep, wallclock=lambda: 1_800_000_001.5)
        return code, json.loads(raw), client, holder['rpc'], raw

    def test_rv1_only_reads_and_exact_override_simulations_are_allowed(self):
        ok, s, st = rv.allowed_call, self.scope, self.state
        sim = {'from': WALLET, 'to': rv.ROUTER, 'data': calldata(1), 'value': '0x0'}
        allowance = dict(to=USDT, data=rv.ALLOWANCE_CALL + PADDED + rv.ROUTER[2:].rjust(64, '0'))
        self.assertTrue(ok('eth_chainId', [], s))
        self.assertTrue(ok('eth_getBlockByNumber', ['latest', False], s))
        self.assertTrue(ok('eth_call', [dict(to=USDT, data=rv.BALANCE_OF_CALL + PADDED), 'latest', st], s))
        self.assertTrue(ok('eth_call', [allowance, 'latest', st], s))
        self.assertTrue(ok('eth_estimateGas', [sim, 'latest', st], s))
        refused = [
            ('eth_sendRawTransaction', ['0x00']),
            ('eth_sendTransaction', [sim]),
            ('eth_getBlockByNumber', ['finalized', True]),
            ('eth_estimateGas', [sim, 'latest']),                                             # no override
            ('eth_estimateGas', [sim, 'latest', {USDT: {'stateDiff': {}}}]),                  # other override
            ('eth_estimateGas', [dict(sim, data=calldata(2)), 'latest', st]),                 # not the live quote
            ('eth_estimateGas', [dict(sim, value='0x1'), 'latest', st]),
            ('eth_estimateGas', [dict(sim, to='0x' + '9' * 40), 'latest', st]),
            ('eth_estimateGas', [dict(sim, **{'from': '0x' + 'cd' * 20}), 'latest', st]),
            ('eth_estimateGas', [dict(sim, gas='0x1'), 'latest', st]),
            ('eth_call', [dict(to=USDT, data='0xa9059cbb' + '0' * 128), 'latest', st]),        # transfer
            ('eth_call', [dict(to='0x' + '9' * 40, data=rv.BALANCE_OF_CALL + PADDED), 'latest', st]),
            ('eth_call', [dict(to=USDT, data=rv.BALANCE_OF_CALL + PADDED), 'pending', st]),
        ]
        rpc = rv.Rpc('https://a.b', s, opener=self)  # opener must never be reached
        for method, params in refused:
            with self.subTest(method=method, params=str(params)[:60]):
                self.assertFalse(ok(method, params, s))
                with self.assertRaisesRegex(ValueError, 'RPC_CALL_REFUSED'):
                    rpc(method, params)
        with self.assertRaisesRegex(ValueError, 'RPC_URL_REFUSED'):
            rv.Rpc('http://a.b', s)

    def open(self, *args, **kwargs):
        raise AssertionError('network reached for a refused call')

    def test_rv1_client_allows_only_the_quote_endpoint(self):
        client = rv.QuoteOnlyClient(KEY, SECRET, artifacts=None, opener=self)
        for method, endpoint in [('POST', 'pre-transaction/broadcast-transaction'), ('GET', 'aggregator/approve-transaction'),
                                 ('POST', 'pre-transaction/gas-limit'), ('GET', 'market/rwa/tokens')]:
            with self.subTest(endpoint=endpoint), self.assertRaisesRegex(Unavailable, 'allowlist'):
                client.request(method, endpoint, {})

    def test_rv2_actual_ages_bounds_and_stop_rule(self):
        # NVDAB (n=1) RFQ order valid 4 s; GOOGLB (n=2) arrives expired; others AMM.
        code, p, client, rpc, _ = self.run_tool(lambda n: {1: 4.0, 2: 0.0}.get(n))
        self.assertEqual((code, p['status']), (0, 'DONE'))
        q = {r['symbol']: r for r in p['quotes']}
        nv, go, ts = q['NVDAB'], q['GOOGLB'], q['TSLAB']
        self.assertTrue(all(r['age_s'] >= r['target_s'] for r in nv['probes']))
        self.assertLess(nv['probes'][0]['age_s'], 0.5)  # first probe immediately after the response
        self.assertEqual(nv['classification']['last_success_age_s'], 3.0)
        self.assertEqual(nv['classification']['first_rfq_failure_age_s'], 5.0)
        self.assertFalse(nv['classification']['arrived_expired'])
        self.assertEqual([r['target_s'] for r in nv['probes']], [0, 1, 2, 3, 5, 8])  # two RFQ failures -> stop
        self.assertTrue(go['classification']['arrived_expired'])
        self.assertEqual(len(go['probes']), 2)
        self.assertEqual([r['target_s'] for r in ts['probes']], list(rv.TARGETS))
        self.assertFalse(ts['classification']['rfq_failing'])
        self.assertEqual(p['verdict'], 'MIXED')
        self.assertEqual(p['by_symbol']['NVDAB']['bounds'], [[3.0, 5.0]])
        self.assertEqual(p['by_symbol']['TSLAB']['max_success_age_s_non_rfq'], ts['probes'][-1]['age_s'])
        # the response wall time is the fixture wallclock 1_800_000_001.5 (read before the block call)
        self.assertEqual(nv['timestamp_values'], [
            dict(byte_offset=64, unit='s', offset_vs_block_s=500, offset_vs_response_s=498.5),
            dict(byte_offset=70, unit='s', offset_vs_block_s=1, offset_vs_response_s=-0.5)])
        self.assertEqual(nv['route_names'], [dict(dex='Rfq Maker', percent='100.00')])
        self.assertEqual((nv['rfq_route'], ts['rfq_route']), (True, False))
        self.assertEqual(p['by_symbol']['NVDAB']['short_encoded_times_vs_response_s'], [-0.5])
        self.assertEqual(p['by_symbol']['TSLAB']['short_encoded_times_vs_response_s'], [])
        self.assertEqual(client.calls[0][2]['slippagePercent'], '0.2')
        self.assertEqual(client.calls[0][2]['amount'], str(15 * 10**18))

    def test_verdicts(self):
        self.assertEqual(self.run_tool(lambda n: None)[1]['verdict'], 'INCONCLUSIVE_NO_RFQ_FAILURE_OBSERVED')
        self.assertEqual(self.run_tool(lambda n: 0.0 if n == 3 else None)[1]['verdict'], 'ALL_RFQ_FAILURES_ARRIVED_EXPIRED')
        self.assertEqual(self.run_tool(lambda n: 6.0 if n == 3 else None)[1]['verdict'], 'RFQ_VALIDITY_WINDOW_OBSERVED')

    def test_non_rfq_reverts_are_not_rfq_expiry(self):
        probes = [dict(target_s=0, age_s=0.1, result='REVERTED'), dict(target_s=1, age_s=1.0, result=500_000)]
        c = rv.classify(probes)
        self.assertEqual((c['rfq_failing'], c['other_failures']), (False, ['REVERTED']))
        self.assertEqual(rv.RpcRefused(dict(message='execution reverted: Min return not reached')).reason(), 'REVERTED')
        self.assertEqual(rv.RpcRefused(dict(message='execution reverted: adapter:0x1:Error(Expired order x)')).reason(),
                         'REVERTED:Expired order x')
        self.assertEqual(rv.RpcRefused(dict(message='header not found')).reason(), 'RPC_ERROR')

    def test_rv3_no_simulation_without_the_override_proof(self):
        code, p, client, rpc, _ = self.run_tool(lambda n: None, proof=False)
        self.assertEqual((code, p['status']), (2, 'NOT_RUN'))
        self.assertNotIn('eth_estimateGas', rpc.calls)
        self.assertEqual(client.calls, [])

    def test_quote_failure_is_recorded_and_others_continue(self):
        code, p, *_ = self.run_tool(lambda n: None, fail={'MSFTB'})
        q = {r['symbol']: r for r in p['quotes']}
        self.assertEqual(q['MSFTB']['quote_error'], 'quote_unavailable')
        self.assertIn('probes', q['SKHYB'])

    def test_rv4_packet_is_public(self):
        code, p, client, rpc, raw = self.run_tool(lambda n: 4.0 if n == 1 else None)
        text = raw.decode().lower()
        for private in (KEY, SECRET, Args.rpc_url, WALLET[2:], calldata(1)[10:]):
            self.assertNotIn(private.lower(), text)
        self.assertEqual(len(p['quotes'][0]['calldata']), 16)
        with self.assertRaises(Exception):
            rv.public_bytes(dict(leak=WALLET), [WALLET, WALLET[2:]])

    def test_main_refuses_with_code(self):
        stdout = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(stdout):
            code = rv.main(['--rounds', '1'], rpc_factory=lambda url, scope: lambda m, p: '0x1',
                           client=object(), credentials_source=fixture_credentials)
        self.assertEqual(code, 4)
        self.assertEqual(json.loads(stdout.getvalue())['reason'], 'ValueError:CHAIN_NOT_56')


if __name__ == '__main__':
    unittest.main()

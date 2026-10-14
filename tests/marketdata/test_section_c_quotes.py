"""IDEA-049-C requirement-derived quotes; synthetic external responses only."""
from dataclasses import replace
import base64
import hashlib
import hmac
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from larp.execution import Blocked, NATIVE_BNB, Payload, SwapEconomics, USDT
from larp.execution_live.service import map_command
from larp.execution_live.venue import LiveVenue
from larp.marketdata.port import MarketPort, TOKENS, slippage_percent
from larp.marketdata.web3 import Artifacts, Unavailable, Web3Client
from larp.research.fixtures import changed
from larp.risk.planner import plan
from tests.strategy.live_fixtures import live_snapshot
from tests.marketdata.test_quote_contract import QuoteClient, proof, WALLET, ROUTER, STAMP
from tests.execution import test_live_boundaries as command_fixtures
from tests.execution_fixtures import intent
from tests.marketdata.test_transport import Opener


class BoundQuotes(QuoteClient):
    def __init__(self):
        self.requests = []
        self.minimum_bps = None
    def request(self, method, endpoint, params):
        self.requests.append((endpoint, params))
        raw = super().request(method, endpoint, params)
        if endpoint == 'aggregator/quote-and-swap':
            q = raw['response']['data'][0]
            q['executionMode'] = 'SWAP'
            received = int(q['routerResult']['toTokenAmount'])
            bps = self.minimum_bps if self.minimum_bps is not None else int(float(params['slippagePercent']) * 100)
            q['tx']['minReceiveAmount'] = str(received * (10000 - bps) // 10000)
        return raw


def strict_proof(*args):
    return dict(proof(*args), slippage_bps=20)


class SlippageRequirements(unittest.TestCase):
    limits = dict(mode='LIVE', quote_age_seconds=30, slippage_bps=20,
                  impact_bps=50, per_trade_cap_units=50000000)
    request = dict(schema='MarketRequest.v1', symbol='NVDAB', side='BUY', amount_kind='EXACT_IN',
                   pay_asset='USDT', pay_units=40000000, pay_decimals=6)

    def test_c_req_014_percent_conversion_preserves_integral_percent_zeros(self):
        for bps, expected in ((0, '0'), (1, '0.01'), (20, '0.2'), (50, '0.5'),
                              (100, '1'), (1000, '10'), (9999, '99.99')):
            with self.subTest(bps=bps):
                self.assertEqual(slippage_percent(bps), expected)

    def test_c_req_007_get_signature_binds_escaped_query_and_fixed_timestamp(self):
        params = {'binanceChainId': '56', 'tokenContractAddresses': '0xabc,0xdef', 'note': 'a+b c'}
        target = '/api/v1/dex/market/rwa/price?' + urlencode(params)
        timestamp = '2026-10-14T12:00:00.123Z'
        expected = base64.b64encode(hmac.new(b'fixture-secret',
            (timestamp + 'GET/build' + target).encode(), hashlib.sha256).digest()).decode()
        with tempfile.TemporaryDirectory() as root, patch('larp.marketdata.web3.utc', return_value=timestamp):
            opener = Opener(b'{"code":0,"data":[]}')
            client = Web3Client('fixture-api-key', 'fixture-secret', artifacts=Artifacts(root), opener=opener)
            client.request('GET', 'market/rwa/price', params)
        sent = opener.calls[0]
        self.assertEqual(sent.full_url, 'https://web3.binance.com/build' + target)
        self.assertEqual(sent.get_header('X-oc-sign'), expected)
        self.assertIsNone(sent.data)

    def test_c_req_006_nondefault_bstock_decimals_reach_mapping_without_rescaling(self):
        class EightDecimals(BoundQuotes):
            def request(self, method, endpoint, params):
                raw = super().request(method, endpoint, params)
                if endpoint == 'market/rwa/tokens':
                    raw['response']['data'][0]['decimals'] = '8'
                elif endpoint == 'aggregator/quote-and-swap':
                    q = raw['response']['data'][0]
                    q['routerResult']['toToken']['decimal'] = '8'
                    q['routerResult']['toTokenAmount'] = str(4 * 10**7)
                    q['tx']['minReceiveAmount'] = str(4 * 10**7 * 998 // 1000)
                return raw
        row = MarketPort(EightDecimals(), WALLET, quote_limits=self.limits,
                         cost_observation=lambda _: None).observe(self.request)
        self.assertEqual(row['decimals'], 8)
        self.assertEqual(row['quote_measurement']['receive_decimals'], 8)
        command = command_fixtures.LiveBoundaries().command()
        minimum = row['quote_measurement']['minimum_receive_raw']
        command['payload'].update(receive_decimals=8, min_receive_units=int(minimum))
        economic = map_command(command, run_id='run', wallet=WALLET, version_id='v', router=ROUTER,
            token_decimals={'NVDAB':row['decimals']}, now_ms=100, limits=dict(self.limits,
                max_gas=1000000, max_gas_price=10, gas_budget=20000000))
        self.assertEqual(economic.minimum_output, int(minimum))
        command['payload']['receive_decimals'] = 18
        with self.assertRaises(Blocked):
            map_command(command, run_id='run', wallet=WALLET, version_id='v', router=ROUTER,
                token_decimals={'NVDAB':8}, now_ms=100, limits=dict(self.limits,
                    max_gas=1000000, max_gas_price=10, gas_budget=20000000))

    def test_c_req_014_initial_quote_uses_independent_20bp_profile(self):
        client = BoundQuotes()
        row = MarketPort(client, WALLET, quote_limits=self.limits,
                         quote_verifier=strict_proof, cost_observation=lambda _: None).observe(self.request)
        self.assertEqual(client.last_params['slippagePercent'], '0.2')
        self.assertEqual(row['quote_status'], 'VERIFIED_EXECUTABLE')

    def test_c_req_014_minimum_output_cannot_borrow_a_lower_proof_slippage(self):
        client = BoundQuotes(); client.minimum_bps = 50
        with self.assertRaises(Unavailable):
            MarketPort(client, WALLET, quote_limits=self.limits,
                       quote_verifier=strict_proof, cost_observation=lambda _: None).observe(self.request)

    def test_c_req_014_invalid_profile_limit_refused_before_quote_io(self):
        for limit in (-1, True, 10000, '20', None):
            client = BoundQuotes()
            with self.subTest(limit=limit), self.assertRaises(Unavailable):
                MarketPort(client, WALLET, quote_limits=dict(self.limits, slippage_bps=limit)).quote(
                    'NVDAB', 'BUY', 40 * 10**18, 18)
            self.assertFalse(client.requests)

    def test_c_req_014_explicit_quote_cannot_widen_profile_limit(self):
        client = BoundQuotes()
        with self.assertRaises(Unavailable):
            MarketPort(client, WALLET, quote_limits=self.limits).quote(
                'NVDAB', 'BUY', 40 * 10**18, 18, slippage='0.5')
        self.assertFalse(client.requests)

    def test_c_req_014_execution_quote_uses_immutable_intent_limit(self):
        client = BoundQuotes()
        class Decoder:
            def decode(self, payload):
                return SwapEconomics(USDT, TOKENS['NVDAB'], 40 * 10**18, WALLET, 1, 1000, 0)
        # Initial and post-approval calls use the same immutable intent.
        economic = replace(intent(), amount=40 * 10**18, max_slippage_bps=20)
        for nonce in (0, 1):
            LiveVenue(client, None, decoder=Decoder()).quote(economic, nonce)
            self.assertEqual(client.last_params['slippagePercent'], '0.2')

    def test_c_req_014_mapper_binds_accepted_profile_limit(self):
        command = command_fixtures.LiveBoundaries().command()
        economic = map_command(command, run_id='run', wallet=WALLET, version_id='v', router=ROUTER,
            token_decimals={'NVDAB':18}, now_ms=100, limits=dict(self.limits,
                max_gas=1000000, max_gas_price=10, gas_budget=20000000))
        self.assertEqual(economic.max_slippage_bps, 20)

    def test_c_req_014_post_approval_quote_cannot_weaken_its_minimum_output(self):
        client = BoundQuotes(); client.minimum_bps = 50
        class Decoder:
            def decode(self, payload):
                return SwapEconomics(USDT, TOKENS['NVDAB'], 40 * 10**18, WALLET, 1, 1000, 0)
        with self.assertRaises(Blocked):
            LiveVenue(client, None, decoder=Decoder()).quote(
                replace(intent(), amount=40 * 10**18, max_slippage_bps=20), 1)

    def test_c_req_014_fresh_minimum_matches_consumer_integer_floor(self):
        class Rounded(BoundQuotes):
            def request(self, *args):
                raw = super().request(*args)
                if args[1] == 'aggregator/quote-and-swap':
                    q = raw['response']['data'][0]
                    received = 4 * 10**17 + 1
                    q['routerResult']['toTokenAmount'] = str(received)
                    q['tx']['minReceiveAmount'] = str(received * 9980 // 10000)
                return raw
        class Decoder:
            def decode(self, payload):
                return SwapEconomics(USDT, TOKENS['NVDAB'], 40 * 10**18, WALLET, 1, 1000, 0)
        client = Rounded()
        self.assertIsInstance(LiveVenue(client, None, decoder=Decoder()).quote(
            replace(intent(), amount=40 * 10**18, max_slippage_bps=20), 1), Payload)

    def test_c_req_014_floor_minus_one_native_unit_still_fails(self):
        class TooWeak(BoundQuotes):
            def request(self, *args):
                raw = super().request(*args)
                if args[1] == 'aggregator/quote-and-swap':
                    q = raw['response']['data'][0]
                    received = int(q['routerResult']['toTokenAmount'])
                    q['tx']['minReceiveAmount'] = str(received * 9980 // 10000 - 1)
                return raw
        with self.assertRaises(Blocked):
            LiveVenue(TooWeak(), None, decoder=None).quote(
                replace(intent(), amount=40 * 10**18, max_slippage_bps=20), 1)


class GasClient:
    def __init__(self, *, scale=6):
        self.scale = scale; self.params = None; self.mutation = lambda q: None
    def request(self, method, endpoint, params):
        self.params = params
        q = dict(executionMode='SWAP', routerResult=dict(
            fromToken=dict(tokenContractAddress=USDT, decimal='18'),
            toToken=dict(tokenContractAddress=NATIVE_BNB, decimal='18'),
            fromTokenAmount=params['amount'], toTokenAmount=str(241000 * 10**12),
            vendorName='LiquidMesh', priceImpactPercent='0.1'),
            tx=dict(to=ROUTER, data='0xdeadbeef', value='0', gas='200000', gasPrice='1',
                    minReceiveAmount=str(241000 * 10**12 * 998 // 1000)))
        self.mutation(q)
        return dict(response={'data':[q]}, available_at='2026-10-29T14:00:00+00:00',
                    artifact_sha256='a' * 64)


def gas_proof(raw, request):
    q = raw['response']['data'][0]; tx = q['tx']; rr = q['routerResult']
    return dict(source_hash=raw['artifact_sha256'], route_valid=True, exact_gas_verified=True,
        payload=Payload(56, WALLET, ROUTER, 0, 0, 200000, 1, tx['data']),
        economics=SwapEconomics(USDT, NATIVE_BNB, int(rr['fromTokenAmount']), WALLET,
        int(tx['minReceiveAmount']), 1793282430, 0), fee_units=0,
        gas_bnb_units=max(10000, (200000 + 10**(18-request.get('receive_decimals', 6))-1)
                           // 10**(18-request.get('receive_decimals', 6))))


class GasQuoteRequirements(unittest.TestCase):
    def port(self, client, *, verifier=gas_proof, scale=6):
        from larp.marketdata.port import NativeGasQuotePort
        snapshot = live_snapshot(gas_low=True)
        limits = snapshot.context.read()['profile']
        return NativeGasQuotePort(client, WALLET, quote_limits=limits,
            pay_units=limits['gas_top_up_cash_units'], receive_decimals=scale, quote_verifier=verifier)

    def test_c_req_047_native_quote_passes_real_resource_planner(self):
        snapshot = live_snapshot(gas_low=True); client = GasClient()
        quotes = self.port(client)(int(snapshot.observed_at.timestamp() * 1000))
        result = plan(changed(snapshot, gas_quotes=quotes), None).read()
        self.assertEqual(len(result['intents']), 1)
        self.assertEqual(result['intents'][0]['kind'], 'GAS_TOP_UP')
        self.assertEqual(client.params['toTokenAddress'], NATIVE_BNB)
        self.assertEqual(client.params['slippagePercent'], '0.2')
        self.assertEqual(quotes[0]['receive_decimals'], 6)
        self.assertEqual(quotes[0]['token_units'], 241000)

    def test_c_req_047_no_verified_proof_means_no_executable_quote(self):
        self.assertEqual(self.port(GasClient(), verifier=None)(0), [])

    def test_c_req_047_native_quote_tampering_is_refused(self):
        mutations = [lambda q: q['routerResult']['toToken'].update(tokenContractAddress=TOKENS['NVDAB']),
            lambda q: q['routerResult'].update(fromTokenAmount='1'),
            lambda q: q['tx'].update(value='1'),
            lambda q: q['tx'].update(minReceiveAmount=str(241000 * 10**12 * 995 // 1000)),
            lambda q: q['routerResult'].update(vendorName='Unknown')]
        for mutation in mutations:
            client = GasClient(); client.mutation = mutation
            with self.subTest(mutation=mutation), self.assertRaises(Unavailable):
                self.port(client)(0)

    def test_c_req_047_wrong_recipient_deadline_or_proof_hash_is_refused(self):
        for change in (dict(source_hash='b'*64), dict(exact_gas_verified=False),
                       dict(gas_bnb_units=0), dict(fee_units=1),
                       dict(economics=SwapEconomics(USDT, NATIVE_BNB, 1, ROUTER, 1, 1, 0))):
            with self.subTest(change=change), self.assertRaises(Unavailable):
                self.port(GasClient(), verifier=lambda *a: dict(gas_proof(*a), **change))(0)

    def test_c_req_048_native_chain_scale_is_not_accounting_scale(self):
        quote = self.port(GasClient(), scale=18)(0)[0]
        self.assertEqual(quote['token_units'], 241000 * 10**12)
        self.assertEqual(quote['receive_decimals'], 18)

    def test_c_req_015_gas_quote_retains_retrieval_time_even_after_cutoff(self):
        quote = self.port(GasClient())(0)[0]
        self.assertEqual(quote['available_at'], '2026-10-29T14:00:00+00:00')

    def test_c_req_018_native_gas_proof_cannot_underreserve_signed_payload(self):
        with self.assertRaises(Unavailable):
            self.port(GasClient(), scale=18,
                verifier=lambda *a: dict(gas_proof(*a), gas_bnb_units=1))(0)

    def test_c_req_049_native_proof_rejects_invalid_payload_fields(self):
        for field, value in (('gas', 0), ('gas_price', True), ('nonce', -1), ('to', 'invalid'),
                             ('data', 'not-calldata')):
            def invalid(raw, request):
                value_proof = gas_proof(raw, request)
                value_proof['payload'] = replace(value_proof['payload'], **{field:value})
                # The HTTP fixture can echo the same invalid bytes; equality alone is insufficient.
                if field == 'data':
                    raw['response']['data'][0]['tx']['data'] = value
                return value_proof
            with self.subTest(field=field), self.assertRaises(Unavailable):
                self.port(GasClient(), verifier=invalid)(0)

    def test_c_req_047_each_decoded_economic_field_is_independently_bound(self):
        for field, value in (('pay_token', TOKENS['NVDAB']), ('receive_token', TOKENS['NVDAB']),
                             ('amount', 1), ('recipient', ROUTER), ('minimum_output', 1),
                             ('deadline', 1793282399), ('native_value', 1)):
            def invalid(raw, request):
                value_proof = gas_proof(raw, request)
                value_proof['economics'] = replace(value_proof['economics'], **{field:value})
                return value_proof
            with self.subTest(field=field), self.assertRaises(Unavailable):
                self.port(GasClient(), verifier=invalid)(0)

    def test_c_req_048_native_minimum_is_not_weakened_by_accounting_rounding(self):
        client = GasClient()
        client.mutation = lambda q: q['tx'].update(
            minReceiveAmount=str(241000 * 10**12 * 998 // 1000 + 1))
        with self.assertRaises(Unavailable):
            self.port(client)(0)

    def test_c_req_047_native_minimum_matches_consumer_integer_floor(self):
        client = GasClient()
        def rounded(q):
            received = int(q['routerResult']['toTokenAmount']) + 1
            q['routerResult']['toTokenAmount'] = str(received)
            q['tx']['minReceiveAmount'] = str(received * 9980 // 10000)
        client.mutation = rounded
        self.assertTrue(self.port(client, scale=18)(0))

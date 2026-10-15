import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone
from larp.marketdata.web3 import Artifacts, Unavailable, credentials, encoded
from larp.marketdata.port import MarketPort, TOKENS, units
from larp.strategy.schema import market_view

class Client:
    def request(self, method, endpoint, params):
        stamp='2026-10-11T16:00:00Z'
        if endpoint=='market/rwa/tokens':
            rows=[dict(tokenContractAddress=t, tokenSymbol=s, binanceChainId='56', decimals='18',
                       tokenPrice='100', underlyingTicker=s[:-1], statusInfo={'openState':True}) for s,t in TOKENS.items()]
        elif endpoint=='market/rwa/underlying-market':
            rows=[dict(tokenContractAddress=params['tokenContractAddress'],statusInfo={'openState':True})]
        elif endpoint=='market/rwa/price':
            rows=[dict(tokenContractAddress=params['tokenContractAddresses'],tokenPrice='100')]
        elif endpoint=='aggregator/quote-and-swap':
            from larp.execution import USDT
            amount=int(params['amount']);buy=params['fromTokenAddress']==USDT
            receive=amount//100 if buy else amount*100*999//1000
            rows=[dict(routerResult=dict(fromToken=dict(tokenContractAddress=params['fromTokenAddress'],decimal='18'),
                 toToken=dict(tokenContractAddress=params['toTokenAddress'],decimal='18'),
                 fromTokenAmount=str(amount),toTokenAmount=str(receive)))]
        else:
            raise AssertionError(endpoint)
        return dict(response={'data':rows},available_at=stamp, artifact_sha256=hashlib.sha256(encoded(rows)).hexdigest())

class LiveMarket(unittest.TestCase):
    def test_market_output_passes_consumer_validator_and_does_not_invent_basis(self):
        port=MarketPort(Client(),'0x'+'1'*40)
        rows=port(0)
        validated=market_view(rows,tuple(TOKENS),datetime(2026,10,11,16,tzinfo=timezone.utc),{'quote_age_seconds':30})
        self.assertEqual(set(validated),set(TOKENS))
        self.assertTrue(all(m['decimals']==18 and not m['basis_verified'] and not m['quotes'] for m in validated.values()))
    def test_credentials_are_selected_and_alias_conflicts_block(self):
        with self.assertRaises(Unavailable):
            credentials(environ={'BINANCE_API_KEY':'a','BN_WEB3_API_KEY':'b','BINANCE_SECRET_KEY':'c'})
        v=credentials(environ={'BN_WEB3_API_KEY':'a','BN_WEB3_SECRET_KEY':'b','WALLET_PRIVATE_KEY':'unused'})
        self.assertNotIn('WALLET_PRIVATE_KEY',v)
        self.assertEqual(v['BINANCE_API_KEY'],'a')
    def test_artifacts_are_immutable_and_hashed(self):
        with tempfile.TemporaryDirectory() as d:
            a=Artifacts(d); h=a.put({'test':1})
            self.assertEqual(h,a.put({'test':1}))
            self.assertEqual((Path(d)/(h+'.json')).read_bytes(),encoded({'test':1}))
            self.assertEqual((Path(d)/(h+'.json')).stat().st_mode & 0o777,0o600)
    def test_exact_scaling_rejects_dust_and_invalid_numeric_data(self):
        self.assertEqual(units('40',18),40*10**18)
        for val in ('NaN','Infinity','-1','0.0000001'):
            with self.subTest(val=val),self.assertRaises(Unavailable):units(val,6)

    def test_optional_cost_access_failures_stop_before_later_market_requests(self):
        for failure in ('authentication_error', 'compliance_restriction',
                        'http_forbidden_unclassified', 'rate_limited'):
            class RefusedCostClient(Client):
                def __init__(self): self.endpoints = []
                def request(self, method, endpoint, params):
                    self.endpoints.append(endpoint)
                    if endpoint == 'aggregator/quote-and-swap':
                        raise Unavailable(failure)
                    return super().request(method, endpoint, params)
            client = RefusedCostClient()
            with self.subTest(failure=failure), self.assertRaisesRegex(Unavailable, failure):
                MarketPort(client, '0x' + '1' * 40)(0)
            self.assertEqual(client.endpoints, ['market/rwa/tokens', 'market/rwa/underlying-market',
                                               'market/rwa/price', 'aggregator/quote-and-swap'])

    def test_temporary_cost_outage_retains_explicit_unavailable_cost(self):
        def missing_cost(symbol):
            raise Unavailable('transport_error')
        rows = MarketPort(Client(), '0x' + '1' * 40, cost_observation=missing_cost)(0)
        self.assertEqual(len(rows), len(TOKENS))
        self.assertTrue(all(row['cost_status'] == 'UNAVAILABLE' and
                            row['measured_roundtrip_bps'] is None for row in rows))

    def test_malformed_remote_schemas_raise_sanitized_unavailable(self):
        for endpoint, body in (('market/rwa/tokens', ['PRIVATE_MARKER']),
                               ('market/rwa/underlying-market', [dict(tokenContractAddress=TOKENS['NVDAB'],
                                                                      statusInfo=None)]),
                               ('market/rwa/price', [dict(tokenContractAddress=TOKENS['NVDAB'])])):
            class MalformedClient(Client):
                def request(self, method, current, params):
                    r = super().request(method, current, params)
                    if current == endpoint: r['response']['data'] = body
                    return r
            with self.subTest(endpoint=endpoint), self.assertRaisesRegex(Unavailable, 'market response schema rejected'):
                MarketPort(MalformedClient(), '0x' + '1' * 40)(0)

    def test_out_of_range_candle_timestamp_is_typed_unavailable(self):
        class InvalidCandleClient(Client):
            def request(self, *args):
                return dict(response={'data': [['1', '1', '1', '1', '1', 2**255, 1]]},
                            artifact_sha256='a' * 64, available_at='2026-10-11T16:00:00Z')
        with self.assertRaisesRegex(Unavailable, 'market response schema rejected'):
            MarketPort(InvalidCandleClient(), '0x' + '1' * 40).candles('NVDAB')

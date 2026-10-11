from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import unittest

from larp.execution import Payload, SwapEconomics, USDT
from larp.marketdata.port import MarketPort, TOKENS
from larp.marketdata.web3 import Unavailable, encoded
from larp.risk.planner import _quote_at_cap
from larp.strategy.schema import market_view
from tests.marketdata.test_live_port import Client

WALLET = '0x' + '1' * 40
ROUTER = '0x' + '2' * 40
STAMP = '2026-10-11T16:00:00Z'


class QuoteClient(Client):
    def request(self, method, endpoint, params):
        if endpoint != 'aggregator/quote-and-swap':
            return super().request(method, endpoint, params)
        self.last_params = params
        q = dict(routerResult=dict(fromToken=dict(tokenContractAddress=USDT, decimal='18'),
                  toToken=dict(tokenContractAddress=TOKENS['NVDAB'], decimal='18'),
                  fromTokenAmount=str(40 * 10**18), toTokenAmount=str(4 * 10**17),
                  priceImpactPercent='0.0123', vendorName='LiquidMesh'),
                 tx=dict(to=ROUTER, data='0xdeadbeef', value='0', gas='200000', gasPrice='1',
                         minReceiveAmount=str(39 * 10**16)))
        return dict(response={'data':[q]}, available_at=STAMP, artifact_sha256=hashlib.sha256(encoded(q)).hexdigest())


def proof(raw, request, observation):
    tx = raw['response']['data'][0]['tx']
    return dict(source_hash=raw['artifact_sha256'], route_valid=True, exact_gas_verified=True,
                payload=Payload(56, WALLET, ROUTER, 0, 0, 200000, 1, tx['data']),
                economics=SwapEconomics(USDT, TOKENS['NVDAB'], 40 * 10**18, WALLET,
                                       int(tx['minReceiveAmount']), 1791734430, 0),
                fee_units=0, gas_bnb_units=200000, slippage_bps=50)


class QuoteContractTests(unittest.TestCase):
    request = dict(schema='MarketRequest.v1', symbol='NVDAB', side='BUY', amount_kind='EXACT_IN',
                   pay_asset='USDT', pay_units=40000000, pay_decimals=6)

    def test_verified_fixture_passes_real_consumers(self):
        c = QuoteClient()
        row = MarketPort(c, WALLET, quote_verifier=proof).observe(self.request)
        now = datetime(2026, 10, 11, 16, tzinfo=timezone.utc)
        self.assertIsNotNone(market_view([row], ('NVDAB',), now, {'quote_age_seconds':30})['NVDAB'])
        accepted = _quote_at_cap(row, 'BUY', 40000000,
                                 dict(quote_age_seconds=30, slippage_bps=50, impact_bps=50,
                                      per_trade_cap_units=50000000), now, 4 * 10**17)
        self.assertIsNotNone(accepted[0])
        self.assertEqual(accepted[0]['impact_bps'], 2)
        self.assertEqual(c.last_params['amount'], str(40 * 10**18))

    def test_missing_or_unbound_proof_is_not_executable(self):
        row = MarketPort(QuoteClient(), WALLET).observe(self.request)
        self.assertFalse(row['quotes'])
        for change in (dict(source_hash='wrong'), dict(exact_gas_verified=False), dict(gas_bnb_units=0)):
            with self.subTest(change=change), self.assertRaises(Unavailable):
                MarketPort(QuoteClient(), WALLET,
                           quote_verifier=lambda *args: {**proof(*args), **change}).observe(self.request)

    def test_fresh_quote_does_not_refresh_old_metadata(self):
        class OldMetadata(QuoteClient):
            def request(self, method, endpoint, params):
                r = super().request(method, endpoint, params)
                if endpoint == 'market/rwa/tokens':
                    r['available_at'] = '2026-10-11T15:00:00Z'
                return r
        row = MarketPort(OldMetadata(), WALLET).observe(self.request)
        now = datetime(2026, 10, 11, 16, tzinfo=timezone.utc)
        self.assertIsNone(market_view([row], ('NVDAB',), now, {'quote_age_seconds':30})['NVDAB'])

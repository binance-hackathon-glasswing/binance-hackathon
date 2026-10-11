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

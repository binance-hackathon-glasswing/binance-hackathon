"""Opt-in consumer validation of hash-addressed real responses kept outside Git."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from datetime import datetime
from larp.marketdata.port import MarketPort, TOKENS
from larp.marketdata.web3 import Unavailable
from larp.strategy.schema import market_view
from larp.risk.planner import _quote_at_cap

class Recorded:
    def __init__(self,root):
        self.rows=[]
        for p in Path(root).glob('*.json'):
            raw=p.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=p.stem:raise Unavailable('recorded artifact hash mismatch')
            r=json.loads(raw)
            if r.get('schema')=='Web3Observation.v1' and r.get('outcome')=='ok':
                self.rows.append(dict(r,artifact_sha256=p.stem))
    def request(self,method,endpoint,params):
        matches=[r for r in self.rows if r['method']==method and r['endpoint']==endpoint and r['params']==params]
        if not matches:raise Unavailable('no matching recorded response')
        return max(matches,key=lambda r:r['available_at'])

@unittest.skipUnless(os.getenv('LARP_RECORDED_MARKET_ROOT'),'real response artifacts are external; opt-in only')
class RecordedConsumers(unittest.TestCase):
    def test_real_outputs_pass_market_validator_and_unknown_routes_remain_nonexecutable(self):
        port=MarketPort(Recorded(os.environ['LARP_RECORDED_MARKET_ROOT']),
                        '0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479')
        rows=port(0)
        cutoff=max(datetime.fromisoformat(r['available_at'].replace('Z','+00:00')) for r in rows)
        # Recorded samples span several cycles; use a broad fixture age solely for schema validation.
        view=market_view(rows,tuple(TOKENS),cutoff,{'quote_age_seconds':3600})
        self.assertTrue(all(view.values()))
        r=port.observe(dict(schema='MarketRequest.v1',symbol='NVDAB',side='BUY',amount_kind='EXACT_IN',
                            pay_asset='USDT',pay_units=40000000,pay_decimals=6))
        self.assertEqual(r['quote_status'],'CAPABILITY_PROOF_REQUIRED')
        self.assertFalse(r['quotes'])
        result=_quote_at_cap(r,'BUY',40000000,{},cutoff,10**18)
        self.assertEqual(result[3],'PENDING')

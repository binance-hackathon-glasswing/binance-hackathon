"""Producer/consumer checks also run on the isolated strategy integration branch."""
from datetime import datetime, timezone
import importlib.util
import unittest

from larp.contracts import Document
from larp.marketdata.port import MarketPort, TOKENS
from larp.strategy.schema import market_view
from tests.marketdata.test_live_port import Client


class LiveConsumerTests(unittest.TestCase):
    def test_market_has_live_origin_and_measured_cost_provenance(self):
        rows=MarketPort(Client(),'0x'+'1'*40)(0)
        result=market_view(rows,tuple(TOKENS),datetime(2026,10,11,16,tzinfo=timezone.utc),
                           {'mode':'LIVE','quote_age_seconds':30})
        self.assertTrue(all(result.values()))
        for row in rows:
            self.assertEqual(row['origin'],'WEB3_OPEN_API')
            self.assertGreater(row['measured_roundtrip_bps'],0)
            self.assertEqual(row['cost_status'],'MEASURED')
            self.assertEqual(len(row['cost_observation']['content_hash']),64)

    @unittest.skipUnless(importlib.util.find_spec('larp.strategy.sessions'),'actual session consumer lives on strategy branch')
    def test_normalized_capture_passes_actual_session_builder(self):
        from larp.strategy.sessions import token_sessions
        class CandleClient(Client):
            def request(self,method,endpoint,params):
                if endpoint=='market/candles':
                    return dict(response={'data':[['100','100','100','100','1',
                        int(datetime(2026,10,9,13+i,tzinfo=timezone.utc).timestamp()*1000),1] for i in range(7)]},
                        available_at='2026-10-09T20:01:00Z',artifact_sha256='a'*64)
                return super().request(method,endpoint,params)
        raw=MarketPort(CandleClient(),'0x'+'1'*40).session_candles('NVDAB',entity_id='NVDA',
            timestamp_kind='OPEN',timestamp_evidence_hash='b'*64,token_adjustment_version='SYNTHETIC-v1')
        calendar=Document.from_dict(dict(schema='USRegularSessions.v1',calendar_id='SYNTHETIC',content_hash='c'*64,
            sessions=[dict(session_index=0,open_at='2026-10-09T13:30:00Z',close_at='2026-10-09T20:00:00Z')]))
        result=token_sessions(Document.from_dict(raw),calendar,cutoff=datetime(2026,10,9,20,1,tzinfo=timezone.utc)).read()
        self.assertEqual(len(result['bars']),1)
        self.assertFalse(result['missing_sessions'])

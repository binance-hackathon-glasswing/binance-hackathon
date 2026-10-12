import tempfile
import unittest
from unittest.mock import patch

from larp.marketdata.logger import summarize
from larp.marketdata.web3 import Artifacts, credentials
from larp.marketdata.port import MarketPort
from tests.marketdata.test_live_port import Client


class LoggerTests(unittest.TestCase):
    def test_summary_uses_immutable_report_pairs_and_keeps_negative_samples(self):
        with tempfile.TemporaryDirectory() as root:
            a = Artifacts(root)
            for amount in ('-3', '5'):
                a.put(dict(schema='QuoteCycle.v1', started_at='2026-10-11T16:00:00Z', finished_at='2026-10-11T16:01:00Z',
                           observations=[dict(symbol='NVDAB', status='MEASURED_NONEXECUTABLE', token_open=True,
                           underlying_open=True, quoted_roundtrip_bps=amount,effective_quoted_spread_bps=amount,
                           buy={'quote_measurement':{'impact_bps':'1','elapsed_ms':100}},
                           sell={'quote_measurement':{'impact_bps':'3','elapsed_ms':200}})]))
            report = summarize(root)
            self.assertEqual(report['cycle_count'], 2)
            self.assertEqual(report['symbols']['NVDAB']['roundtrip_bps_median'], '1')
            self.assertEqual(report['symbols']['NVDAB']['impact_bps_median'], '2')
            self.assertEqual(report['symbols']['NVDAB']['open_samples'], 2)
            self.assertEqual(report['symbols']['NVDAB']['effective_quoted_spread_bps_median'],'1')
            self.assertEqual(report['symbols']['NVDAB']['quote_latency_ms_median'],150)

    def test_official_secret_alias_and_conflicts(self):
        selected = credentials(environ={'BN_WEB3_API_KEY':'fixture-key','BN_WEB3_API_SECRET':'fixture-secret'})
        self.assertEqual(selected['BINANCE_SECRET_KEY'], 'fixture-secret')
        from larp.marketdata.web3 import Unavailable
        with self.assertRaises(Unavailable):
            credentials(environ={'BN_WEB3_API_KEY':'fixture-key','BN_WEB3_API_SECRET':'a','BN_WEB3_SECRET_KEY':'b'})

    def test_candles_preserve_raw_times_without_guessing_session_boundaries(self):
        class CandleClient(Client):
            def request(self, method, endpoint, params):
                if endpoint == 'market/candles':
                    return dict(response={'data':[['1','2','1','2','4',1791734400000,'1']]},
                                artifact_sha256='a'*64, available_at='2026-10-11T17:00:00Z')
                return super().request(method, endpoint, params)
        row = MarketPort(CandleClient(), '0x'+'1'*40).candles('NVDAB', bar='1h')
        self.assertEqual(row['rows'][0][5], 1791734400000)
        self.assertIsNone(row['timestamps'][0]['open_at'])
        self.assertEqual(row['content_hash'], 'a'*64)
        port=MarketPort(CandleClient(), '0x'+'1'*40)
        normalized=port.session_candles('NVDAB',entity_id='NVDA',timestamp_kind='OPEN',
                                       timestamp_evidence_hash='b'*64,token_adjustment_version='fixture-v1')
        self.assertEqual(normalized['schema'],'TokenCandles.v1')
        self.assertEqual(normalized['bar_seconds'],3600)
        self.assertEqual(normalized['candles'],row['rows'])

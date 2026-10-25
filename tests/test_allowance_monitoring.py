"""IDEA-096 AL8: public allowance exports and bounded, sanitized dirty reasons."""
import json
from pathlib import Path
import unittest

from larp.marketdata.allowances import observe, from_config
from larp.marketdata.port import TOKENS
from larp.execution import USDT
from larp.runtime.driver import quote_drop_reason
from larp.marketdata.web3 import Unavailable
from tests.execution.test_untrusted_router import FakeRpc, policy
from larp.execution_live.untrusted_router import UntrustedRouterDecoder
from tests.test_dashboard_decisions import load_export


class AllowanceMonitoring(unittest.TestCase):
    def test_public_status_has_exact_raw_amounts_and_no_provider_details(self):
        d = UntrustedRouterDecoder(policy())
        rpc = FakeRpc(d, '0x' + '1' * 40, USDT, 0)
        d.bind(rpc)
        rpc.allowances[TOKENS['SKHYB']] = 68939879194155372
        value = observe(d, '0x' + '1' * 40)
        self.assertEqual(value['reason'], 'DIRTY_ROUTER_ALLOWANCE')
        self.assertEqual(value['symbols'], ['SKHYB'])
        self.assertEqual(value['allowances']['SKHYB'], '68939879194155372')
        self.assertEqual(len(value['allowances']), 6)
        self.assertNotIn('0x', json.dumps(value))
        self.assertEqual(from_config({'rpc_url': 'secret'})['reason'], 'ALLOWANCE_READ_UNAVAILABLE')

    def test_dirty_quote_refusal_survives_allowlisted_decisions_export(self):
        reason = quote_drop_reason(Unavailable('quote proof refused: DIRTY_ROUTER_ALLOWANCE:SKHYB'))
        x = load_export()
        events = [(1, dict(kind='INCIDENT', incident=dict(type='QUOTE_NOT_EXECUTABLE',
                    requests=[dict(reason=reason, symbol='NVDAB')])))]
        summary = json.loads(x['emit'](events, 30, 'synthetic')[-1])
        self.assertEqual(summary['allowance_incidents'], [dict(reason='DIRTY_ROUTER_ALLOWANCE', symbols=['SKHYB'])])
        events *= 1000
        self.assertLess(len('\n'.join(x['emit'](events, 30, 'synthetic')).encode()), 22000)
        self.assertEqual(len(json.loads(x['emit'](events, 30, 'synthetic')[-1])['allowance_incidents']), 3)

    def test_current_operational_entrypoints_include_allowances(self):
        root = Path(__file__).resolve().parents[1]
        ops = root / 'docs/build/ops/rehearsal-install-rc7-20261024'
        for p in (ops / 'checks/trading-status.sh', root / 'tools/dashboard/decisions-export.sh'):
            self.assertIn('from_config(c)', p.read_text())
        self.assertIn('router_allowances=', (ops / 'mac/chain-monitor.py').read_text())

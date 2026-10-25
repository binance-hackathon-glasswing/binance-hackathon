"""IDEA-096 AL7/F4: gate preparation scope and durable quiet-boundary diagnostics."""
import json
from types import SimpleNamespace
import unittest

from larp.contracts import ContractError
from larp.execution import USDT
from larp.marketdata.port import TOKENS
from larp.execution_live.untrusted_router import UntrustedRouterDecoder
from larp.runtime.allowances import RouterAllowanceCheck
from larp.runtime import gate_a_check
from tests.execution.test_untrusted_router import FakeRpc, policy
from tests.runtime.test_gate_a import assembled
from tests.support import DatabaseCase


class Preparation(unittest.TestCase):
    def test_recovery_flag_is_explicit_and_bound_to_preparation_report(self):
        files = assembled(allowance_recovery=True, untrusted_router_policy_file='/synthetic/policy.json',
                          untrusted_router_policy_sha256='a' * 64)
        values = {k: json.loads(v) for k, v in files.items() if k.endswith('.json')}
        report = values['preparation-report.json']
        self.assertTrue(values['runtime.json']['driver']['allowance_recovery'])
        gate_a_check.check_scope(values, report)
        report['allowance_recovery'] = False
        with self.assertRaises(ContractError):
            gate_a_check.check_scope(values, report)
        with self.assertRaises(ContractError):
            assembled(allowance_recovery=True)


class QuietAllowanceIncident(DatabaseCase):
    def test_nonzero_allowance_is_low_severity_durable_once_per_quiet_decision(self):
        d = UntrustedRouterDecoder(policy())
        rpc = FakeRpc(d, '0x' + '1' * 40, USDT, 0)
        rpc.allowances[TOKENS['SKHYB']] = 12
        d.bind(rpc)
        c = SimpleNamespace(store=self.store, run_id='run')
        check = RouterAllowanceCheck(c, d, '0x' + '1' * 40)
        self.assertEqual(check(1000), 'DIRTY_ROUTER_ALLOWANCE')
        event = self.store.event('run', 'allowance:0')
        self.assertEqual(event['incident']['severity'], 'LOW')
        self.assertEqual(event['incident']['allowances']['SKHYB'], '12')
        version = self.store.load('run').read()['version']
        self.assertEqual(RouterAllowanceCheck(c, d, '0x' + '1' * 40)(2000), 'CHECKED')
        self.assertEqual(self.store.load('run').read()['version'], version)

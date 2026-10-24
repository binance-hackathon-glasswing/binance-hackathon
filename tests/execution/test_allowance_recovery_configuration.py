"""LD06: matching explicit opt-ins, assembler refusal and untrusted-only scope."""
from copy import deepcopy
import json
import unittest

from larp.contracts import ContractError
from larp.execution import Blocked
from larp.execution_live.main import validate_config
from larp.signer.service import router_decoder
from larp.signer.policy import SigningPolicy
from tests.execution import test_mode_readiness as modes


class CleanupConfiguration(unittest.TestCase):
    def setUp(self):
        self.mode = modes.ModeReadiness('test_assembly_untrusted_path_copies_only_policy_pair_and_retains_gates')
        self.mode.setUp()
        self.addCleanup(self.mode.doCleanups)
        self.mode.select_untrusted()
        self.case = self.mode.case

    def test_explicit_matching_optins_assemble_with_gas_and_host_gates_open(self):
        f = self.case.fixture
        f.config['allowance_recovery'] = f.policy['allowance_recovery'] = True
        f.save_inputs()
        report = json.loads(self.case.build()['signer-assembly-report.json'])
        self.assertTrue(report['allowance_recovery'])
        self.assertIn('ALLOWANCE_RECOVERY_GAS_AND_HOST_ACCEPTANCE', report['remaining_gates'])
        for flag in ('ready_to_install', 'signing_enabled', 'gate_b_accepted'):
            self.assertIs(report[flag], False)
        for primary, signer in ((True, False), (False, True)):
            f.config['allowance_recovery'], f.policy['allowance_recovery'] = primary, signer
            f.save_inputs()
            self.assertIn('ALLOWANCE_RECOVERY_SCOPE_MISMATCH', f.report()['blockers'])
            with self.assertRaises(ContractError):self.case.build()

    def test_primary_refuses_nonboolean_or_absent_untrusted_policy(self):
        config = self.case.fixture.config
        for value in (1, None, 'true'):
            with self.subTest(value=value), self.assertRaises(ContractError):
                validate_config(dict(config, allowance_recovery=value))
        bare = deepcopy(config)
        bare.pop('untrusted_router_policy_file')
        bare.pop('untrusted_router_policy_sha256')
        with self.assertRaises(ContractError):validate_config(dict(bare, allowance_recovery=True))

    def test_signer_loader_refuses_recovery_with_verified_source_mode(self):
        config = self.case.fixture.config
        config.pop('untrusted_router_policy_file')
        config.pop('untrusted_router_policy_sha256')
        import hashlib
        config.update(router_evidence_file=str(self.case.router),
                      router_evidence_sha256=hashlib.sha256(self.case.router.read_bytes()).hexdigest())
        policy = SigningPolicy.from_config(dict(self.case.fixture.policy, allowance_recovery=True))
        with self.assertRaises(ContractError):router_decoder(config, policy)

"""LD01: offline reports distinguish router paths without granting authority."""
from copy import deepcopy
import hashlib
import json
import unittest

from larp.contracts import ContractError
from larp.execution import Blocked
from larp.execution_live.gate_b import readiness_report
from tests.execution import test_signer_caps_proposal as proposals
from tests.execution import test_untrusted_router as untrusted
from tests.signer import test_assembly as assembly
from tools.deploy.propose_signer_caps import build


class ModeReadiness(unittest.TestCase):
    def setUp(self):
        self.case = assembly.SignerAssembly(
            'test_candidate_reports_exact_hashes_and_keeps_approval_and_release_gates_open')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def select_untrusted(self, value=None):
        config = self.case.fixture.config
        config.pop('router_evidence_file')
        config.pop('router_evidence_sha256')
        self.policy_path = self.case.root / 'untrusted.json'
        self.policy_path.write_text(json.dumps(untrusted.policy() if value is None else value))
        config.update(untrusted_router_policy_file=str(self.policy_path),
                      untrusted_router_policy_sha256=hashlib.sha256(self.policy_path.read_bytes()).hexdigest())
        self.case.fixture.save_inputs()

    def report(self):
        return json.loads(self.case.build()['signer-assembly-report.json'])

    def test_assembly_verified_path_still_requires_source_review(self):
        report = self.report()
        self.assertEqual(report['router_mode'], 'verified')
        self.assertIn('ROUTER_SOURCE_REVIEW_AND_REAL_ROUTE_REPLAY', report['remaining_gates'])
        self.assertNotIn('UNTRUSTED_POLICY_REVIEW_REPLAY_AND_LIVE_PREFLIGHT', report['remaining_gates'])

    def test_assembly_untrusted_path_copies_only_policy_pair_and_retains_gates(self):
        self.select_untrusted()
        files = self.case.build()
        config = json.loads(files['signer.json'])
        report = json.loads(files['signer-assembly-report.json'])
        self.assertEqual(report['router_mode'], 'untrusted')
        self.assertIn('UNTRUSTED_POLICY_REVIEW_REPLAY_AND_LIVE_PREFLIGHT', report['remaining_gates'])
        self.assertNotIn('ROUTER_SOURCE_REVIEW_AND_REAL_ROUTE_REPLAY', report['remaining_gates'])
        for field in ('untrusted_router_policy_file', 'untrusted_router_policy_sha256'):
            self.assertEqual(config[field], self.case.fixture.config[field])
        self.assertNotIn('router_evidence_file', config)
        self.assertNotIn('router_evidence_sha256', config)
        self.assertEqual(report['untrusted_router_policy_sha256'],
                         self.case.fixture.config['untrusted_router_policy_sha256'])
        for gate in ('EXACT_POLICY_OWNER_APPROVAL', 'SIGNING_LIFETIME_27',
                     'REGISTERED_RELEASE_AND_HOST_ACCEPTANCE', 'APPROVED_SIGNER_SESSION_AND_KEY_PLACEMENT'):
            self.assertIn(gate, report['remaining_gates'])
        for flag in ('ready_to_install', 'signing_enabled', 'gate_b_accepted'):
            self.assertIs(report[flag], False)

    def test_untrusted_assembly_refuses_unreviewed_changed_missing_or_mixed_policy(self):
        self.select_untrusted()
        original = deepcopy(self.case.fixture.config)
        raw = self.policy_path.read_bytes()
        for change in ('unreviewed', 'changed', 'missing', 'mixed'):
            with self.subTest(change=change):
                self.case.fixture.config = deepcopy(original)
                self.policy_path.write_bytes(raw)
                if change == 'unreviewed':
                    value = untrusted.policy(review=dict(reviewed_by='REVIEW_REQUIRED', review_ref='REVIEW_REQUIRED'))
                    self.policy_path.write_text(json.dumps(value))
                    self.case.fixture.config['untrusted_router_policy_sha256'] = hashlib.sha256(
                        self.policy_path.read_bytes()).hexdigest()
                elif change == 'changed':
                    self.policy_path.write_bytes(raw + b' ')
                elif change == 'missing':
                    self.policy_path.unlink()
                else:
                    self.case.fixture.config.update(router_evidence_file=str(self.case.router),
                        router_evidence_sha256=hashlib.sha256(self.case.router.read_bytes()).hexdigest())
                self.case.fixture.save_inputs()
                with self.assertRaises((ContractError, Blocked, OSError)):
                    self.case.build()

    def test_proposal_mode_changes_only_router_limitations_and_never_approves(self):
        verified = build(proposals.inputs())
        other = build(proposals.inputs(), router_mode='untrusted')
        self.assertEqual(verified['router_mode'], 'verified')
        self.assertEqual(other['router_mode'], 'untrusted')
        self.assertEqual(verified['candidates'], other['candidates'])
        self.assertIn('ROUTER_SOURCE_REVIEW_AND_REAL_ROUTE_REPLAY', verified['limitations'])
        self.assertIn('UNTRUSTED_POLICY_REVIEW_REPLAY_AND_LIVE_PREFLIGHT', other['limitations'])
        self.assertNotIn('ROUTER_SOURCE_REVIEW_AND_REAL_ROUTE_REPLAY', other['limitations'])
        self.assertIn('EXACT_POLICY_OWNER_APPROVAL', other['limitations'])
        self.assertFalse(other['ready_to_install'])
        for mode in ('UNKNOWN', '', None):
            with self.subTest(mode=mode), self.assertRaises(ContractError):
                build(proposals.inputs(), router_mode=mode)

    def test_gate_b_inventory_and_untrusted_failure_name_applicable_requirements(self):
        inventory = readiness_report(None, now=assembly.NOW, base_dir=self.case.root)
        self.assertIn('untrusted', inventory['checks']['DR-02']['required'].lower())
        self.assertIn('policy', inventory['checks']['DR-03']['required'].lower())
        case = untrusted.GateB('test_dr02_untrusted_policy_and_passing_check')
        case.setUp()
        self.addCleanup(case.doCleanups)
        result = case.report()
        self.assertEqual(result['router_mode'], 'untrusted')
        self.assertEqual(result['checks']['DR-02']['status'], 'BLOCKED')
        self.assertIn('untrusted', result['checks']['DR-02']['detail'].lower())
        self.assertIn('policy', result['checks']['DR-02']['required'].lower())
        self.assertFalse(result['signing_enabled'])

"""SA-01: synthetic, key-free installation candidates; never Gate B acceptance."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import stat
import unittest
from unittest.mock import patch

from larp.contracts import ContractError
from larp.execution import Blocked
from larp.signer.assembly import assemble, main
from tests.execution import test_caps_review as numeric_fixtures
from tests.execution.test_router_decoder import evidence
from tools.deploy.propose_signer_caps import ROUTER

NOW = numeric_fixtures.NOW


class SignerAssembly(unittest.TestCase):
    def setUp(self):
        fixture = numeric_fixtures.CapsReview('test_covered_candidate_still_needs_owners_and_never_enables_signing')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.root = fixture.root
        self.ca = self.root / 'ca.pem'
        self.ca.write_bytes(b'synthetic public CA bytes')
        self.router = self.root / 'router.json'
        self.router.write_text(json.dumps(evidence(router=ROUTER)))
        fixture.policy['cap_basis'] = 'SYNTHETIC_DECISION_NOT_REAL_APPROVAL'
        del fixture.config['database_dsn_file']
        fixture.config.update(database_host='synthetic.example', database_name='signed_test',
                              database_user='larp_execution', region='ap-southeast-2',
                              database_ca_file=str(self.ca),
                              database_ca_sha256=hashlib.sha256(self.ca.read_bytes()).hexdigest(),
                              router_evidence_file=str(self.router),
                              router_evidence_sha256=hashlib.sha256(self.router.read_bytes()).hexdigest())
        fixture.save_inputs()

    def build(self):
        return assemble(self.fixture.inputs, now=NOW, base_dir=self.root)

    def test_uses_exact_execution_identity_and_signer_role_without_loading_keys_or_services(self):
        with patch('larp.runtime.database.open_service_store') as db, \
                patch('larp.runtime.database.rds_client') as aws, \
                patch('larp.signer.service.load_key_file') as key, patch('socket.socket') as network:
            files = self.build()
        for boundary in (db, aws, key, network):
            boundary.assert_not_called()
        config = json.loads(files['signer.json'])
        for field in ('run_id', 'build_id', 'mode', 'wallet_address', 'database_host', 'database_name',
                      'region', 'database_ca_file', 'database_ca_sha256',
                      'router_evidence_file', 'router_evidence_sha256'):
            self.assertEqual(config[field], self.fixture.config[field])
        self.assertEqual(config['database_user'], 'larp_signer')
        self.assertEqual(config['key_credential'], 'wallet.key')
        self.assertEqual(config['signing_policy'], self.fixture.policy)
        self.assertNotIn('rpc_url', config)
        self.assertNotIn('runtime_secret_id', config)

    def test_candidate_reports_exact_hashes_and_keeps_approval_and_release_gates_open(self):
        files = self.build()
        report = json.loads(files['signer-assembly-report.json'])
        self.assertEqual(report['schema'], 'SignerAssemblyReport.v1')
        self.assertEqual(report['status'], 'ASSEMBLED_REQUIRES_APPROVAL')
        self.assertEqual(report['signer_config_sha256'], hashlib.sha256(files['signer.json']).hexdigest())
        self.assertEqual(report['input_hashes'],
                         {k: v['sha256'] for k, v in self.fixture.inputs['files'].items()})
        self.assertEqual(report['numeric_review']['numeric_status'], 'COVERED')
        for flag in ('ready_to_install', 'signing_enabled', 'gate_b_accepted'):
            self.assertIs(report[flag], False)
        self.assertIn('EXACT_POLICY_OWNER_APPROVAL', report['remaining_gates'])
        self.assertIn('SIGNING_LIFETIME_27', report['remaining_gates'])
        self.assertIn('REGISTERED_RELEASE_AND_HOST_ACCEPTANCE', report['remaining_gates'])

    def test_undecided_caps_and_missing_or_changed_input_pins_refuse(self):
        original = deepcopy(self.fixture.policy)
        self.fixture.policy['cap_basis'] = ' EXAMPLE_PENDING_TEAM_DECISION\n'
        self.fixture.save_inputs()
        with self.assertRaises((ContractError, Blocked)):
            self.build()
        self.fixture.policy = original
        self.fixture.save_inputs()
        (self.root / 'signing_policy.json').write_bytes(b'{}')
        with self.assertRaises((ContractError, Blocked)):
            self.build()

    def test_full_holding_gas_and_quote_freshness_checks_cannot_be_skipped(self):
        for change in ('holding', 'gas', 'age', 'coverage'):
            with self.subTest(change=change):
                config, ledger, inputs = deepcopy(self.fixture.config), deepcopy(self.fixture.ledger), deepcopy(self.fixture.inputs)
                if change == 'holding':
                    self.fixture.ledger['positions']['NVDAB']['units'] = 2**255
                elif change == 'gas':
                    self.fixture.config['max_gas'] *= 2
                elif change == 'age':
                    self.fixture.inputs['quote_artifacts'][0] = self.fixture.pin('expired.json',
                        {**json.loads((self.root / 'NVDABBUY.json').read_bytes()),
                         'requested_at': '2026-10-20T00:00:00Z'})
                else:
                    self.fixture.inputs['quote_artifacts'] = []
                self.fixture.save_inputs()
                with self.assertRaises(ContractError):
                    self.build()
                self.fixture.config, self.fixture.ledger, self.fixture.inputs = config, ledger, inputs
                self.fixture.save_inputs()

    def test_missing_changed_and_wrong_router_evidence_refuse(self):
        for value in (None, evidence(router='0x' + 'cd' * 20), {'schema': 'invalid'}):
            with self.subTest(value=value):
                if value is None:
                    self.fixture.config.update(router_evidence_file=None, router_evidence_sha256=None)
                else:
                    raw = json.dumps(value).encode()
                    self.router.write_bytes(raw)
                    self.fixture.config.update(router_evidence_file=str(self.router),
                                               router_evidence_sha256=hashlib.sha256(raw).hexdigest())
                self.fixture.save_inputs()
                with self.assertRaises(ContractError):
                    self.build()

    def test_unpinned_ca_and_local_dsn_refuse(self):
        original = deepcopy(self.fixture.config)
        self.ca.write_bytes(b'changed CA')
        with self.assertRaises(ContractError):
            self.build()
        self.fixture.config = original
        for field in ('database_host', 'database_name', 'database_user', 'database_ca_file', 'database_ca_sha256'):
            del self.fixture.config[field]
        self.fixture.config['database_dsn_file'] = '/must-not-read'
        self.fixture.save_inputs()
        with self.assertRaises(ContractError):
            self.build()

    def test_router_hash_change_and_unsafe_run_identity_refuse(self):
        self.router.write_bytes(self.router.read_bytes() + b' ')
        with self.assertRaises(ContractError):
            self.build()
        self.fixture.config['router_evidence_sha256'] = hashlib.sha256(self.router.read_bytes()).hexdigest()
        self.fixture.inputs['run_id'] = '../unsafe-run'
        self.fixture.config['run_id'] = '../unsafe-run'
        self.fixture.ledger['run_id'] = '../unsafe-run'
        self.fixture.save_inputs()
        with self.assertRaises(ContractError):
            self.build()

    def invoke(self, output):
        inputs = self.root / 'inputs.json'
        inputs.write_text(json.dumps(self.fixture.inputs))
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(['--inputs', str(inputs), '--now', NOW, '--out', str(output)])
        return code, json.loads(stdout.getvalue())

    def test_cli_writes_private_new_candidate_and_never_overwrites(self):
        output = self.root / 'candidate'
        code, result = self.invoke(output)
        self.assertEqual(code, 0)
        self.assertFalse(result['ready_to_install'])
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
        originals = {p.name: p.read_bytes() for p in output.iterdir()}
        for path in output.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(self.invoke(output)[0], 4)
        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, originals)
        link = self.root / 'link'
        link.symlink_to(output, target_is_directory=True)
        self.assertEqual(self.invoke(link)[0], 4)

    def test_refusal_creates_no_candidate_and_does_not_echo_private_inputs(self):
        self.fixture.config['database_host'] = 'DO_NOT_ECHO_PRIVATE_HOST'
        self.fixture.config['max_gas'] *= 2
        self.fixture.save_inputs()
        output = self.root / 'candidate'
        code, result = self.invoke(output)
        self.assertEqual(code, 4)
        self.assertFalse(output.exists())
        self.assertNotIn('DO_NOT_ECHO_PRIVATE_HOST', json.dumps(result))
        self.assertFalse(result['signing_enabled'])

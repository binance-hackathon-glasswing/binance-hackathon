"""SR-01: production startup refuses unfinished caps/source before DB or key access.

All source evidence and releases here are synthetic. A successful local check
does not establish real source provenance, approval, host or Gate B acceptance.
"""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.signer.policy import EXAMPLE_CAP_BASIS
from larp.signer.service import main
from tests.execution.test_router_decoder import evidence
from tests.execution_fixtures import ROUTER
from tests.host_support import BUILD, synthetic_release
from tests.signer.test_service import policy_config


class StartupPrerequisites(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.evidence_path = self.root / 'router.json'
        raw = json.dumps(evidence(router=ROUTER)).encode()
        self.evidence_path.write_bytes(raw)
        self.config = dict(schema='SignerService.v1', run_id='synthetic-readiness', build_id=BUILD,
                           mode='dev', wallet_address='0x' + '1' * 40, interval_seconds=1,
                           key_file='/no-key-read', database_dsn_file='/no-database-read',
                           signing_policy=policy_config(), router_evidence_file=str(self.evidence_path),
                           router_evidence_sha256=hashlib.sha256(raw).hexdigest())

    def invoke(self, command, config):
        raw = json.dumps(config).encode()
        path = self.root / 'signer.json'
        path.write_bytes(raw)
        root, manifest = synthetic_release(self.root, {'signer': raw})
        output = io.StringIO()
        with patch('larp.runtime.database.open_service_store') as db, \
                patch('larp.signer.service.load_key_file') as key, redirect_stdout(output):
            code = main([command, '--config', str(path), '--manifest', str(manifest),
                         '--root', str(root)], max_cycles=1)
        db.assert_not_called()
        key.assert_not_called()
        return code, json.loads(output.getvalue())

    def test_unapproved_caps_refuse_check_and_run_in_both_environments(self):
        for mode in ('dev', 'live'):
            for basis in (EXAMPLE_CAP_BASIS, ' ' + EXAMPLE_CAP_BASIS + '\n'):
                for command in ('check', 'run'):
                    with self.subTest(mode=mode, basis=basis, command=command):
                        config = deepcopy(self.config)
                        config['mode'] = mode
                        config['signing_policy']['cap_basis'] = basis
                        code, result = self.invoke(command, config)
                        self.assertEqual((code, result['reason']), (4, 'START_REFUSED'))
                        self.assertFalse(result['signing_enabled'])

    def test_missing_corrupt_or_untrusted_evidence_refuses_before_db_and_key(self):
        cases = {
            'absent': dict(router_evidence_file=None, router_evidence_sha256=None),
            'missing file': dict(router_evidence_file=str(self.root / 'missing.json')),
            'changed hash': dict(router_evidence_sha256='0' * 64),
        }
        for name, changes in cases.items():
            for command in ('check', 'run'):
                with self.subTest(name=name, command=command):
                    code, result = self.invoke(command, {**self.config, **changes})
                    self.assertEqual((code, result['reason']), (4, 'START_REFUSED'))
        for name, value in (
                ('wrong router', evidence(router='0x' + 'cd' * 20)),
                ('invalid JSON', None),
                ('missing debit guarantee', {**evidence(router=ROUTER), 'guarantees': {}})):
            raw = b'{' if value is None else json.dumps(value).encode()
            self.evidence_path.write_bytes(raw)
            config = {**self.config, 'router_evidence_sha256': hashlib.sha256(raw).hexdigest()}
            for command in ('check', 'run'):
                with self.subTest(name=name, command=command):
                    code, result = self.invoke(command, config)
                    self.assertEqual((code, result['reason']), (4, 'START_REFUSED'))

    def test_check_reports_local_scope_and_exact_evidence_without_loading_a_key(self):
        code, result = self.invoke('check', self.config)
        self.assertEqual(code, 0)
        self.assertTrue(result['configuration_valid'])
        self.assertEqual(result['swap_decoder'], 'VERIFIED')
        self.assertEqual(result['router_evidence_sha256'], self.config['router_evidence_sha256'])
        self.assertEqual(result['scope'], 'LOCAL_CONFIG_AND_ROUTER_EVIDENCE_ONLY')
        self.assertFalse(result['signing_enabled'])
        self.assertFalse(result['gate_b_accepted'])

    def test_evidence_edit_after_successful_check_is_refused(self):
        self.assertEqual(self.invoke('check', self.config)[0], 0)
        self.evidence_path.write_bytes(self.evidence_path.read_bytes() + b' ')
        for command in ('check', 'run'):
            with self.subTest(command=command):
                self.assertEqual(self.invoke(command, self.config)[0], 4)

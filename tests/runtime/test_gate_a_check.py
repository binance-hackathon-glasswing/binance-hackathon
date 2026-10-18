"""IDEA-066 PC01–07: real consumers, synthetic captures/terms/CI bytes; no host authority."""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from larp.marketdata.web3 import encoded
from larp.runtime import gate_a, gate_a_check as checker
from larp.runtime.preflight import release_files
from tests.runtime.test_gate_a import assembled
from tools.build_release_bundle import release_manifest


class GateAPackageCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='larp-gate-a-local-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = self.root / 'prepared'
        self.package.mkdir()
        self.release = self.root / 'release'
        self.release.mkdir()
        for name in release_files(gate_a.ROOT) | {'docs/INCOMPLETE_WORK.md', 'docs/skill/SKILL.md',
                                                 'docs/skill/larp/plan.md'}:
            target = self.release / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(gate_a.ROOT / name, target)
        # The consumer resolves ledger references by file presence; these are only temporary fixture stubs.
        ledger = self.release / 'docs/ledger'
        ledger.mkdir()
        for path in (gate_a.ROOT / 'docs/ledger').glob('*.md'):
            (ledger / path.name).write_text('Synthetic reference fixture.\n')
        self.artifacts = self.root / 'terms'
        self.artifacts.mkdir()
        register_path = self.release / 'config/sources/sources.v1.json'
        register = json.loads(register_path.read_bytes())
        for source in [*register['sources'], register['edgar']]:
            raw = ('Synthetic terms bytes: ' + source['source_id']).encode()
            digest = gate_a.digest(raw)
            source['rights']['terms_evidence_sha256'] = digest
            path = self.artifacts / 'artifacts' / digest[:2] / digest
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        register_path.write_bytes(encoded(register))
        self.ca = self.root / 'rds-ca.pem'
        self.ca.write_bytes(b'Synthetic CA bytes; not a real trust root.\n')
        self.files = assembled(sec_contact='LARP Test test-contact@larp.test')
        for name in ('runtime.json', 'uploader.json', 'operations.json'):
            value = json.loads(self.files[name])
            value['database_ca_sha256'] = gate_a.digest(self.ca.read_bytes())
            self.files[name] = encoded(value)
        self.write_package()
        self.manifest = self.root / 'release-manifest.json'
        self.write_manifest()
        self.options = dict(rds_ca=self.ca, ci_manifest=self.manifest, release_root=self.release,
                            artifact_root=self.artifacts)

    def write_manifest(self):
        repository = json.loads((self.release / 'config/release/repository.v1.json').read_bytes())['repository']
        self.manifest.write_bytes(release_manifest(self.release, release_files(self.release), 'b' * 40,
                                                  repository, repository))

    def write_package(self):
        report = json.loads(self.files['preparation-report.json'])
        report['input_hashes'] = {n: gate_a.digest(raw) for n, raw in self.files.items()
                                 if n != 'preparation-report.json'}
        self.files['preparation-report.json'] = encoded(report)
        for p in self.package.iterdir():
            p.unlink()
        for name, raw in self.files.items():
            (self.package / name).write_bytes(raw)

    def alter(self, name, change):
        value = json.loads(self.files[name])
        change(value)
        self.files[name] = encoded(value)
        self.write_package()

    def qualify(self, **overrides):
        return checker.qualify(self.package, **dict(self.options, **overrides))

    def test_valid_real_assembly_passes_local_checks_with_no_side_effects(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with ExitStack() as stack:
            for target in ('socket.create_connection', 'urllib.request.urlopen', 'subprocess.run',
                           'larp.storage.postgres.PostgresStore.transaction', 'larp.runtime.gate_a.capture_inputs'):
                stack.enter_context(patch(target, side_effect=AssertionError('Remote or mutable operation')))
            report = self.qualify()
        self.assertTrue(report['local_ready'], report)
        self.assertEqual(set(report['checks'].values()), {'PASS'})
        self.assertFalse(report['gate_a_passed'])
        self.assertFalse(report['signing_enabled'])
        self.assertFalse(report['remote_ci_verified'])
        self.assertEqual(set(report['host_checks'].values()), {'NOT_RUN'})
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_missing_prerequisites_never_pass(self):
        for argument, check in (('rds_ca', 'SERVICE_CONFIGS'), ('ci_manifest', 'CI_RELEASE_BYTES'),
                                ('release_root', 'CI_RELEASE_BYTES'), ('artifact_root', 'SOURCE_TERMS')):
            with self.subTest(argument=argument):
                report = self.qualify(**{argument: None})
                self.assertFalse(report['local_ready'])
                self.assertEqual(report['checks'][check], 'NOT_RUN')

    def test_package_missing_changed_extra_and_symlinked_files_refuse(self):
        name = 'runtime.json'
        path = self.package / name
        for defect in ('missing', 'changed', 'extra', 'symlink'):
            with self.subTest(defect=defect):
                self.write_package()
                if defect == 'missing':
                    path.unlink()
                elif defect == 'changed':
                    path.write_bytes(path.read_bytes() + b' ')
                elif defect == 'extra':
                    (self.package / 'signer.json').write_text('{}')
                else:
                    path.unlink()
                    path.symlink_to(self.ca)
                report = self.qualify()
                self.assertEqual(report['checks']['PACKAGE_INTEGRITY'], 'FAIL')
                self.assertFalse(report['local_ready'])

    def test_resealed_identity_and_unsigned_scope_changes_still_refuse(self):
        originals = dict(self.files)
        cases = [('runtime.json', lambda c: c.update(mode='live')),
                 ('runtime.json', lambda c: c.update(run_id='other-run')),
                 ('uploader.json', lambda c: c.update(build_id='d' * 40)),
                 ('uploader.json', lambda c: c.update(wallet_address='0x' + '2' * 40)),
                 ('operations.json', lambda c: c.update(database_name='other-database')),
                 ('runtime.json', lambda c: c['driver'].update(execution='service')),
                 ('runtime.json', lambda c: c['driver'].update(intelligence_mode='development')),
                 ('runtime.json', lambda c: c['driver'].update(assessor='aiand_routed')),
                 ('runtime.json', lambda c: c['driver'].update(cadence_ms=1))]
        for index, (name, change) in enumerate(cases):
            with self.subTest(file=name, case=index):
                self.files = dict(originals)
                self.alter(name, change)
                report = self.qualify()
                self.assertEqual(report['checks']['UNSIGNED_IDENTITIES'], 'FAIL')
                self.assertFalse(report['local_ready'])

    def test_resealed_pins_state_issuers_and_rpc_changes_refuse(self):
        originals = dict(self.files)
        cases = [('runtime.json', lambda c: c.update(initial_state_sha256='0' * 64)),
                 ('runtime.json', lambda c: c['driver'].update(issuers={})),
                 ('runtime.json', lambda c: c['driver'].update(strategy_profile_sha256='0' * 64)),
                 ('runtime.json', lambda c: c['driver'].update(balance_rpc_providers=[])),
                 ('initial-state.json', lambda c: c.update(cash_units=1)),
                 ('input-capture.json', lambda c: c['chain'].update(pending_nonce=99)),
                 ('input-capture.json', lambda c: c['chain'].update(source_id='other-rpc'))]
        for index, (name, change) in enumerate(cases):
            with self.subTest(case=index):
                self.files = dict(originals)
                self.alter(name, change)
                report = self.qualify()
                self.assertEqual(report['checks']['PINNED_INPUTS'], 'FAIL')

    def test_configuration_validators_and_pinned_ca_are_enforced(self):
        self.alter('uploader.json', lambda c: c.update(database_user='larp_runtime'))
        self.assertEqual(self.qualify()['checks']['SERVICE_CONFIGS'], 'FAIL')
        self.ca.write_bytes(b'Wrong CA')
        self.assertEqual(self.qualify()['checks']['SERVICE_CONFIGS'], 'FAIL')

    def test_manifest_other_build_mirror_bound_or_changed_release_refuses(self):
        original = self.manifest.read_bytes()
        for field, value in (('build_id', 'd' * 40), ('build_origin', 'https://github.com/synthetic/mirror'),
                             ('runtime_config_sha256', '0' * 64), ('remote_verified', False)):
            with self.subTest(field=field):
                manifest = json.loads(original)
                manifest[field] = value
                self.manifest.write_bytes(encoded(manifest))
                self.assertEqual(self.qualify()['checks']['CI_RELEASE_BYTES'], 'FAIL')
        self.manifest.write_bytes(original)
        (self.release / 'larp/runtime/operations.py').write_text('# changed\n')
        self.assertEqual(self.qualify()['checks']['CI_RELEASE_BYTES'], 'FAIL')

    def test_pc_mirror01_exact_approved_origin_passes_without_side_effects(self):
        original = json.loads(self.manifest.read_bytes())
        for suffix in ('', '.git'):
            with self.subTest(suffix=suffix):
                value = dict(original, build_origin='https://github.com/Keegan4/Keegan4-larp-ci-mirror' + suffix)
                self.manifest.write_bytes(encoded(value))
                before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
                with ExitStack() as stack:
                    for target in ('socket.create_connection', 'urllib.request.urlopen', 'subprocess.run',
                                   'larp.storage.postgres.PostgresStore.transaction',
                                   'larp.runtime.gate_a.capture_inputs'):
                        stack.enter_context(patch(target, side_effect=AssertionError('Remote or mutable operation')))
                    report = self.qualify()
                self.assertEqual(report['checks']['CI_RELEASE_BYTES'], 'PASS', report)
                self.assertTrue(report['local_ready'], report)
                self.assertFalse(report['gate_a_passed'])
                self.assertFalse(report['remote_ci_verified'])
                self.assertFalse(report['signing_enabled'])
                self.assertEqual(set(report['host_checks'].values()), {'NOT_RUN'})
                self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_pc_mirror01_origin_approval_is_exact_and_repository_scoped(self):
        original = json.loads(self.manifest.read_bytes())
        approved = 'https://github.com/Keegan4/Keegan4-larp-ci-mirror'
        origins = ('https://github.com/synthetic/mirror', approved + '-other', approved + '/',
                   approved + '/extra', approved + '?approved=true', approved + '#approved',
                   approved.replace('https:', 'http:'), approved.replace('github.com', 'github.com.invalid'),
                   approved.replace('github.com', 'user@github.com'),
                   approved.replace('github.com', 'github.com@evil.invalid'),
                   approved.replace('/Keegan4/', '/another-owner/'), None)
        for origin in origins:
            with self.subTest(origin=origin):
                self.manifest.write_bytes(encoded(dict(original, build_origin=origin)))
                self.assertEqual(self.qualify()['checks']['CI_RELEASE_BYTES'], 'FAIL')
        # A self-consistent foreign register/manifest cannot borrow this team's mirror approval.
        path = self.release / 'config/release/repository.v1.json'
        register = json.loads(path.read_bytes())
        register['repository'] = 'https://github.com/synthetic/another-registered-repository'
        path.write_bytes(encoded(register))
        self.manifest.write_bytes(release_manifest(self.release, release_files(self.release), 'b' * 40,
                                                   register['repository'], approved))
        self.assertEqual(self.qualify()['checks']['CI_RELEASE_BYTES'], 'FAIL')

    def test_pc_mirror01_approved_origin_preserves_every_release_check(self):
        approved = dict(json.loads(self.manifest.read_bytes()),
                        build_origin='https://github.com/Keegan4/Keegan4-larp-ci-mirror')
        defects = (('build_id', 'd' * 40), ('repository', 'https://github.com/synthetic/another-repository'),
                   ('remote_verified', False), ('runtime_config_sha256', '0' * 64),
                   ('operations_config_sha256', '0' * 64), ('registration_evidence', {'already': 'bound'}),
                   ('service_configs_sha256', {'uploader': '0' * 64}),
                   ('release_register', {'changed': True}))
        for field, value in defects:
            with self.subTest(field=field):
                self.manifest.write_bytes(encoded(dict(approved, **{field: value})))
                self.assertEqual(self.qualify()['checks']['CI_RELEASE_BYTES'], 'FAIL')
        self.manifest.write_bytes(encoded(approved))
        path = self.release / 'larp/runtime/operations.py'
        path.write_bytes(path.read_bytes() + b'\n# tampered after CI\n')
        self.assertEqual(self.qualify()['checks']['CI_RELEASE_BYTES'], 'FAIL')
        # Even self-consistent listed hashes must cover every executable release file.
        self.write_manifest()
        value = json.loads(self.manifest.read_bytes())
        value['build_origin'] = approved['build_origin']
        del value['files']['larp/runtime/operations.py']
        self.manifest.write_bytes(encoded(value))
        self.assertEqual(self.qualify()['checks']['CI_RELEASE_BYTES'], 'FAIL')

    def test_terms_metadata_does_not_replace_actual_retained_bytes(self):
        register = json.loads((self.release / 'config/sources/sources.v1.json').read_bytes())
        digest = register['edgar']['rights']['terms_evidence_sha256']
        artifact = self.artifacts / 'artifacts' / digest[:2] / digest
        original = artifact.read_bytes()
        for raw in (b'', b'Altered terms'):
            artifact.write_bytes(raw)
            self.assertEqual(self.qualify()['checks']['SOURCE_TERMS'], 'FAIL')
        artifact.write_bytes(original)
        artifact.unlink()
        self.assertEqual(self.qualify()['checks']['SOURCE_TERMS'], 'FAIL')

    def test_evidence_environment_is_parsed_without_shell_evaluation(self):
        self.files['evidence.env'] += b'UNEXPECTED=$(touch should-never-exist)\n'
        self.write_package()
        self.assertEqual(self.qualify()['checks']['SOURCE_TERMS'], 'FAIL')
        self.assertFalse((self.root / 'should-never-exist').exists())

    def test_no_first_bnb_is_valid_for_unsigned_gate_a(self):
        # Exercise the real preparation path with a truly zero native balance on both captures.
        from tests.runtime.test_gate_a import rehash, with_chain
        capture = with_chain()
        capture['chain']['native_wei'] = 0
        rows = capture['balances']['response']['data'][0]['tokenAssets']
        next(r for r in rows if r['tokenContractAddress'] == gate_a.NATIVE)['rawBalance'] = '0'
        from tests.runtime.test_gate_a import assembled as assemble
        self.files = assemble(capture_raw=encoded(rehash(capture)), sec_contact='LARP Test test-contact@larp.test')
        for name in ('runtime.json', 'uploader.json', 'operations.json'):
            value = json.loads(self.files[name])
            value['database_ca_sha256'] = gate_a.digest(self.ca.read_bytes())
            self.files[name] = encoded(value)
        self.write_package()
        self.assertIn('FIRST_BNB (Q-03)', json.loads(self.files['preparation-report.json'])['missing_inputs'])
        self.assertTrue(self.qualify()['local_ready'])

    def test_cli_exit_codes_and_errors_never_reflect_values(self):
        arguments = ['--prepared', str(self.package), '--rds-ca', str(self.ca), '--ci-manifest', str(self.manifest),
                     '--release-root', str(self.release), '--artifact-root', str(self.artifacts)]
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(checker.main(arguments), 0)
        self.assertTrue(json.loads(stdout.getvalue())['local_ready'])
        stdout = io.StringIO()
        with redirect_stdout(stdout), patch.object(checker, 'read_file', side_effect=OSError('PRIVATE_VALUE')):
            self.assertEqual(checker.main(arguments), 4)
        text = stdout.getvalue()
        self.assertNotIn('PRIVATE_VALUE', text)
        self.assertNotIn('test-contact', text)
        self.assertNotIn('rpc.invalid', text)
        self.assertFalse(json.loads(text)['gate_a_passed'])


if __name__ == '__main__':
    unittest.main()

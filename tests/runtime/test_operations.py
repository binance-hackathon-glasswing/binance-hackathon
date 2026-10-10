import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from larp.contracts import ContractError, Document
from larp.runtime.operations import validate_config, main
from larp.runtime.preflight import release_files, verify_release


class OperationsTests(unittest.TestCase):
    def test_prepare_failure_still_drains_delivery_and_reports_unhealthy(self):
        from unittest.mock import patch,MagicMock
        worker=MagicMock()
        worker.prepare.side_effect=ContractError('Synthetic oversized backup')
        worker.once.side_effect=[True,False]
        worker.health.return_value=Document.from_dict(dict(healthy=True,reasons=[]))
        c=dict(run_id='run',deployment='fixture',archive_bucket='fixture',account_id='123456789012',
               kms_key='synthetic',archive_prefix='archive/dev',retention_days=7,max_archive_bytes=1,
               backup_interval_hours=24,max_attempts=2,retry_seconds=60)
        clients={key:MagicMock() for key in ('s3','rds','cloudwatch')}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'config.json'; path.write_text('{}')
            with patch('larp.runtime.operations.validate_config',return_value=c), \
                    patch('larp.runtime.operations.cloud_clients',return_value=clients), \
                    patch('larp.runtime.operations.S3Archive'), \
                    patch('larp.runtime.operations.Maintenance',return_value=worker), \
                    patch('builtins.print') as output:
                self.assertEqual(1,main(['once','--config',str(path)]))
            self.assertEqual(2,worker.once.call_count)
            health=json.loads(output.call_args.args[0])
            self.assertIn('ARCHIVE_PREPARATION_FAILED',health['reasons'])
            self.assertFalse(health['healthy'])

    def test_example_config_cannot_start_or_contact_cloud(self):
        example = Path('config/runtime/operations.example.json')
        with self.assertRaises(ContractError): validate_config(json.loads(example.read_text()))
        self.assertEqual(1, main(['check', '--config', str(example)]))

    def test_manifest_rejects_unlisted_code_and_missing_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'larp/runtime/operations.py'
            path.parent.mkdir(parents=True)
            path.write_text('# fixture', encoding='utf-8')
            files = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in release_files(root)}
            base = dict(schema='ReleaseManifest.v1', build_id='a'*40, repository='synthetic',
                        remote_verified=True, services=['synthetic'], files=files)
            with self.assertRaises(ContractError): verify_release(Document.from_dict(base), root)
            base['registration_evidence'] = dict(schema='RegistrationEvidence.v1', evidence_ref='synthetic-only',
                                                 build_id='a'*40, repository='synthetic')
            verify_release(Document.from_dict(base), root)
            (path.parent/'unexpected.py').write_text('# unlisted', encoding='utf-8')
            with self.assertRaises(ContractError): verify_release(Document.from_dict(base), root)

    def test_database_certificate_is_pinned_and_admin_role_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            certificate = Path(directory)/'ca.pem'
            certificate.write_bytes(b'synthetic certificate')
            config = dict(schema='OperationsConfiguration.v1', deployment='fixture', region='us-east-1',
                          account_id='123456789012', run_id='run', archive_bucket='fixture',
                          archive_prefix='archive/development', kms_key='synthetic', retention_days=7,
                          backup_interval_hours=24, database_host='synthetic', database_user='larp_archive',
                          database_name='larp', database_ca_file=str(certificate),
                          database_ca_sha256=hashlib.sha256(certificate.read_bytes()).hexdigest(),
                          max_attempts=2, retry_seconds=60, max_archive_bytes=1024)
            validate_config(config)
            with self.assertRaises(ContractError): validate_config(dict(config, database_user='larp_admin'))
            certificate.write_bytes(b'changed')
            with self.assertRaises(ContractError): validate_config(config)

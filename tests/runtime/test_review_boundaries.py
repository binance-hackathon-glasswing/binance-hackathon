"""IDEA-044 C07/C08: actual archive adapter and configuration release boundary."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from larp.contracts import ContractError
from larp.runtime.maintenance import HOUR_MS, Maintenance
from larp.runtime.operations import IamPostgresStore
from larp.runtime.service import EXIT_REFUSED, StartRefused, main, validate_config, verify_registered_manifest
from larp.storage.archive import S3Archive
from larp.storage.postgres import IntegrityError, doc
from tests.storage.test_archive import FakeS3
from tests.support import DatabaseCase


class ArchiveAdapter(DatabaseCase):
    def test_replaced_manifest_same_build_cannot_override_journaled_config(self):
        from larp.runtime.coordinator import batch_for
        manifest = doc(dict(build_id='a' * 40, runtime_config_sha256='b' * 64))
        current = self.store.load('run')
        projection = current.read()['projection']
        projection['registered_version'] = dict(build_id='a' * 40,
            manifest_sha256=hashlib.sha256(manifest.payload).hexdigest())
        self.store.commit(batch_for(current, 'registered', dict(kind='VERSION_REGISTERED'), projection=projection))
        config = dict(run_id='run', build_id='a' * 40, mode='offline')
        verify_registered_manifest(self.store, config, manifest)
        with self.assertRaises(StartRefused):
            verify_registered_manifest(self.store, config,
                doc(dict(build_id='a' * 40, runtime_config_sha256='c' * 64)))
        with self.assertRaises(StartRefused):
            verify_registered_manifest(self.store, dict(config, mode='live'), manifest)

    def test_unregistered_live_run_cannot_start_or_downgrade_to_offline(self):
        self.store.initialize('live-run', 'fixture-wallet', 56, doc({}), mode='live')
        for mode in ('live', 'offline'):
            with self.subTest(mode=mode), self.assertRaises(StartRefused):
                verify_registered_manifest(self.store, dict(run_id='live-run', build_id='a' * 40, mode=mode), doc({}))

    def test_iam_adapter_verifies_and_prepares_real_postgres_archive(self):
        import psycopg
        connect = psycopg.connect
        rds = Mock()
        rds.generate_db_auth_token.side_effect = lambda **kw: 'synthetic-token'
        config = dict(database_host='synthetic', database_user='larp_archive', region='synthetic',
                      database_name='larp_test', database_ca_file='/synthetic/ca')
        store = IamPostgresStore(config, rds)
        # Preserve the real IAM connection path, replacing only its transport
        # destination with this test's isolated PostgreSQL schema.
        with patch('psycopg.connect', side_effect=lambda *a, **kw: connect(self.store._dsn)) as transport:
            self.assertEqual(store.verify('run'), self.store.verify('run'))
            worker = Maintenance(store, S3Archive(FakeS3(), bucket='fixture', account_id='123456789012',
                                 kms_key='synthetic', prefix='archive/test', retention_days=7),
                                 backup_interval_ms=24 * HOUR_MS)
            worker.prepare('run', 100)
            worker.once('run', 100)
            worker.once('run', 100)
            self.assertTrue(worker.health('run', 100).read()['healthy'])
            self.assertEqual(rds.generate_db_auth_token.call_count, transport.call_count - 1)
            self.assertGreater(rds.generate_db_auth_token.call_count, 5)

    def test_genesis_policy_and_execution_tampering_refuses_full_verification(self):
        self.assertEqual(self.store.verify('run'), '0' * 64)
        for field in ('policy_state', 'execution_state'):
            with self.subTest(field=field):
                with self.store.transaction() as db:
                    db.execute(f"UPDATE runs SET {field}=%s WHERE run_id='run'", (doc({'injected': True}).payload,))
                with self.assertRaises(IntegrityError):
                    self.store.verify('run')
                with self.store.transaction() as db:
                    db.execute(f"UPDATE runs SET {field}=%s WHERE run_id='run'", (doc({}).payload,))
        self.assertEqual(self.store.verify('run'), '0' * 64)


class RuntimeConfiguration(unittest.TestCase):
    def config(self):
        return dict(schema='RuntimeService.v1', run_id='run', build_id='a' * 40, database_dsn_file='/synthetic',
                    max_failures=3, clear_after=2, interval_seconds=5, mode='offline')

    def test_service_refuses_missing_or_tampered_config_binding_before_driver_or_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = json.dumps(self.config()).encode()
            (root / 'runtime.json').write_bytes(raw)
            (root / 'manifest.json').write_bytes(b'{}')
            options = ['--config', str(root / 'runtime.json'), '--manifest', str(root / 'manifest.json'),
                       '--root', str(root)]
            for expected in (None, 'f' * 64, hashlib.sha256(raw).hexdigest()):
                manifest = dict(build_id='a' * 40, runtime_config_sha256=expected)
                with self.subTest(expected=expected), patch('larp.runtime.preflight.verify_release', return_value=manifest), \
                        patch('larp.runtime.credentials.runtime_secrets') as secrets, \
                        patch('larp.runtime.service.build_driver') as driver, patch('builtins.print'):
                    self.assertEqual(main(['check'] + options), 0 if expected == hashlib.sha256(raw).hexdigest()
                                     else EXIT_REFUSED)
                    if expected != hashlib.sha256(raw).hexdigest():
                        self.assertEqual(main(['run'] + options), EXIT_REFUSED)
                    secrets.assert_not_called()
                    driver.assert_not_called()

    def test_malformed_runtime_settings_are_start_refusals(self):
        for key, values in (('max_failures', [True, 0, '3']), ('clear_after', [False, -1, '2']),
                            ('interval_seconds', [True, 0, -1, float('nan'), float('inf')]),
                            ('mode', ['unknown'])):
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ContractError):
                    validate_config(dict(self.config(), **{key: value}))
        for value in ([], None, 'configuration'):
            with self.assertRaises(ContractError):
                validate_config(value)

"""C-REQ-059: real PostgreSQL, real composition, synthetic credentials/releases."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from larp.contracts import Document
from larp.execution_live.loop import RunAuthorization
from larp.execution_live.main import main
from larp.marketdata.port import TOKENS
from larp.research.fixtures import synthetic_profile
from larp.storage.postgres import doc
from tests.execution_fixtures import intent
from tests.host_support import BUILD, synthetic_release
from tests.support import DatabaseCase


class ExecutionStartup(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        directory = Path(self.tmp.name)
        dsn = directory / 'dsn'
        dsn.write_text(self.store._dsn)
        profile = json.dumps(dict(synthetic_profile(), mode='LIVE')).encode()
        (directory / 'profile.json').write_bytes(profile)
        config = dict(schema='ExecutionService.v1', run_id='c-execution', build_id=BUILD, mode='dev',
                      wallet_address='0x' + 'a' * 40, interval_seconds=1, database_dsn_file=str(dsn),
                      market_artifact_root=str(directory / 'market'), chain_artifact_root=str(directory / 'chain'),
                      rpc_url='https://rpc.invalid/', rpc_source_id='fixture', router='0x' + '2' * 40,
                      token_decimals={s: 18 for s in TOKENS}, max_gas=500000, max_gas_price=10**10,
                      gas_budget=10**16, strategy_profile_file=str(directory / 'profile.json'),
                      strategy_profile_sha256=hashlib.sha256(profile).hexdigest())
        raw = json.dumps(config).encode()
        path = directory / 'execution.json'
        path.write_bytes(raw)
        root, manifest = synthetic_release(self.tmp.name, {'execution': raw})
        self.manifest_hash = hashlib.sha256(Document(manifest.read_bytes()).payload).hexdigest()
        self.argv = ['run', '--config', str(path), '--manifest', str(manifest), '--root', str(root)]
        self.store.initialize('c-execution', config['wallet_address'], 56, doc(dict(balances=dict(USDT=1))), mode='dev')
        self.registration(dict(build_id=BUILD, manifest_sha256=self.manifest_hash))

    def registration(self, version):
        projection = dict(balances=dict(USDT=1))
        if version is not None:
            projection['registered_version'] = version
        with self.store.transaction() as db:
            db.execute('UPDATE runs SET projection=%s,initial=%s,quarantined=false WHERE run_id=%s',
                       (doc(projection).payload, doc(projection).payload, 'c-execution'))

    def run_main(self, *, refused):
        output = io.StringIO()
        with patch('larp.runtime.credentials.runtime_secrets', return_value=dict(
                BINANCE_API_KEY='fixture-key', BINANCE_SECRET_KEY='fixture-secret')) as credentials, \
                redirect_stdout(output):
            code = main(self.argv)
        if refused:
            self.assertEqual(code, 4, output.getvalue())
            self.assertIn('START_REFUSED', output.getvalue())
            credentials.assert_not_called()
        else:
            self.assertEqual(code, 2, output.getvalue())
            self.assertIn('EXECUTOR_CAPABILITY_GATE', output.getvalue())

    def test_c_req_059_unregistered_startup_refuses_before_credentials(self):
        self.registration(None)
        self.run_main(refused=True)

    def test_c_req_059_wrong_build_refuses_before_credentials(self):
        self.registration(dict(build_id='c' * 40, manifest_sha256=self.manifest_hash))
        self.run_main(refused=True)

    def test_c_req_059_same_build_wrong_manifest_refuses_before_credentials(self):
        self.registration(dict(build_id=BUILD, manifest_sha256='0' * 64))
        self.run_main(refused=True)

    def test_c_req_059_matching_release_retains_executor_capability_refusal(self):
        self.run_main(refused=False)


class ExecutionAuthorization(DatabaseCase):
    def setUp(self):
        super().setUp()
        projection = self.store.load('run').read()['projection']
        projection['registered_version'] = dict(build_id='version', manifest_sha256='a' * 64)
        self.store.commit(self.batch(projection=projection))
        with self.store.transaction() as db:
            db.execute("UPDATE runs SET mode='dev' WHERE run_id='run'")

    def facts(self, manifest, version='version'):
        authority = RunAuthorization(self.store, run_id='run', build_id='version')
        authority.manifest_sha256 = manifest
        return authority.facts(intent(version_id=version), 12)

    def test_c_req_059_wrong_manifest_cannot_authorize(self):
        self.assertFalse(self.facts('b' * 64)['version_valid'])

    def test_c_req_059_missing_production_manifest_cannot_authorize(self):
        self.assertFalse(self.facts(None)['version_valid'])

    def test_c_req_059_stale_immutable_intent_version_cannot_authorize(self):
        self.assertFalse(self.facts('a' * 64, version='another-build')['version_valid'])

    def test_c_req_059_matching_production_manifest_is_version_valid(self):
        self.assertTrue(self.facts('a' * 64)['version_valid'])

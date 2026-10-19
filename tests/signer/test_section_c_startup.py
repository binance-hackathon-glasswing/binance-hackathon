"""C-REQ-058: registered signer startup, real PostgreSQL and synthetic releases."""
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from larp.contracts import Document
from larp.signer.service import main
from larp.storage.postgres import doc
from tests.host_support import BUILD, synthetic_release
from tests.signer import test_service as fixtures


class RegisteredStartup(fixtures.SigningCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        directory = Path(self.tmp.name)
        keys = directory / 'keys'
        keys.mkdir(mode=0o700)
        key = keys / 'wallet.key'
        key.write_text(self.account.key.hex())
        os.chmod(key, 0o600)
        dsn = directory / 'dsn'
        dsn.write_text(self.store._dsn)
        config = dict(schema='SignerService.v1', run_id='c-startup', build_id=BUILD, mode='dev',
                      wallet_address=self.wallet, key_file=str(key), interval_seconds=1,
                      database_dsn_file=str(dsn), signing_policy=fixtures.policy_config(),
                      **fixtures.pinned_router_settings(directory))
        raw = json.dumps(config).encode()
        path = directory / 'signer.json'
        path.write_bytes(raw)
        root, manifest = synthetic_release(self.tmp.name, {'signer': raw})
        self.manifest_hash = hashlib.sha256(Document(manifest.read_bytes()).payload).hexdigest()
        self.argv = ['run', '--config', str(path), '--manifest', str(manifest), '--root', str(root)]
        self.store.initialize('c-startup', self.wallet, 56, doc(dict(balances=dict(USDT=1))), mode='dev')
        self.registration(dict(build_id=BUILD, manifest_sha256=self.manifest_hash))

    def registration(self, version):
        # Synthetic genesis authority; no signature or economic command is seeded.
        projection = dict(balances=dict(USDT=1))
        if version is not None:
            projection['registered_version'] = version
        with self.store.transaction() as db:
            db.execute('UPDATE runs SET projection=%s,initial=%s,quarantined=false WHERE run_id=%s',
                       (doc(projection).payload, doc(projection).payload, 'c-startup'))

    def run_main(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = main(self.argv, max_cycles=1, sleep=lambda seconds: None)
        return code, stream.getvalue()

    def refused_without_key(self):
        with patch('larp.signer.service.load_key_file') as key:
            code, output = self.run_main()
        self.assertEqual(code, 4, output)
        self.assertIn('START_REFUSED', output)
        key.assert_not_called()

    def test_c_req_058_unregistered_startup_refuses_before_key_loading(self):
        self.registration(None)
        self.refused_without_key()

    def test_c_req_058_wrong_registered_build_refuses_before_key_loading(self):
        self.registration(dict(build_id='c' * 40, manifest_sha256=self.manifest_hash))
        self.refused_without_key()

    def test_c_req_058_wrong_registered_manifest_refuses_before_key_loading(self):
        self.registration(dict(build_id=BUILD, manifest_sha256='0' * 64))
        self.refused_without_key()

    def test_c_req_058_matching_registered_release_starts(self):
        code, output = self.run_main()
        self.assertEqual(code, 0, output)
        self.assertIn('"signing_enabled": true', output)

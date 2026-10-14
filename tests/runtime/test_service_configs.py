"""IDEA-047 M01: host service configurations are pinned in the release manifest (G-03)."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.runtime import preflight
from larp.runtime.preflight import (build_manifest, release_files, service_config_arguments, verify_environment,
                                    verify_service_config)
from tests.host_support import ROOT, synthetic_release

COMMIT = 'd' * 40


def fake_git(root):
    names = '\0'.join(sorted(release_files(root)))

    def run(command, **kwargs):
        args = command[3:]  # git -C <root> ...
        out = {('status', '--porcelain'): '', ('rev-parse', 'HEAD'): COMMIT, ('branch', '--show-current'): 'main',
               ('remote', 'get-url', 'origin'): 'https://github.com/example/larp',
               ('ls-files', '-z'): names}.get(tuple(args))
        if args[:1] == ['ls-remote']:
            out = COMMIT + '\trefs/heads/main'
        return subprocess.CompletedProcess(command, 0, out, '')
    return run


class ServiceConfigs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.root, _ = synthetic_release(self.tmp.name)

    def test_m01_build_records_each_service_config(self):
        with patch.object(preflight.subprocess, 'run', fake_git(self.root)):
            plain = build_manifest(self.root, ['synthetic']).read()
            pinned = build_manifest(self.root, ['synthetic'], service_configs={'signer': b'{"a":1}',
                                                                               'uploader': b'{}'}).read()
        self.assertNotIn('service_configs_sha256', plain)  # earlier manifests keep their exact shape
        verify_service_config(pinned, 'signer', b'{"a":1}')
        verify_service_config(pinned, 'uploader', b'{}')
        for name, raw in (('signer', b'{"a":2}'), ('execution', b'{}')):
            with self.subTest(name=name), self.assertRaises(ContractError):
                verify_service_config(pinned, name, raw)
        with self.assertRaises(ContractError):
            verify_service_config(plain, 'signer', b'{"a":1}')

    def test_m01_arguments(self):
        config = self.dir / 'signer.json'
        config.write_bytes(b'{}')
        self.assertEqual(service_config_arguments(['signer=' + str(config)]), {'signer': b'{}'})
        self.assertEqual(service_config_arguments(None), {})
        for values in (['signer'], ['=x'], ['signer='], ['signer=' + str(config)] * 2):
            with self.subTest(values=values), self.assertRaises(ContractError):
                service_config_arguments(values)

    def test_m01_cli_verify_with_service_config_and_host_profile(self):
        config = self.dir / 'signer.json'
        config.write_bytes(b'{"schema":"SignerService.v1"}')
        _, manifest = synthetic_release(self.tmp.name, {'signer': config.read_bytes()})
        (self.root / 'deploy').mkdir(exist_ok=True)
        for lock in ('requirements-runtime.lock', 'requirements-aws.lock', 'requirements-signer.lock'):
            (self.root / 'deploy' / lock).write_bytes((ROOT / 'deploy' / lock).read_bytes())
        _, manifest = synthetic_release(self.tmp.name, {'signer': config.read_bytes()})

        def check(*extra):
            out = io.StringIO()
            with redirect_stdout(out):
                code = preflight.main(['--manifest', str(manifest), '--root', str(self.root), *extra])
            return code, json.loads(out.getvalue())['release_verified']
        self.assertEqual(check('--profile', 'host', '--service-config', 'signer=' + str(config)), (0, True))
        config.write_bytes(b'{"schema":"SignerService.v1","changed":true}')
        self.assertEqual(check('--service-config', 'signer=' + str(config)), (1, False))
        self.assertEqual(check('--service-config', 'execution=' + str(config)), (1, False))

    def test_m01_host_profile_checks_the_signer_lock(self):
        (self.root / 'deploy').mkdir(exist_ok=True)
        for lock in ('requirements-runtime.lock', 'requirements-aws.lock'):
            (self.root / 'deploy' / lock).write_bytes((ROOT / 'deploy' / lock).read_bytes())
        (self.root / 'deploy/requirements-signer.lock').write_text('eth-account==0.0.1\n')
        verify_environment(self.root)  # the operations profile does not read the signer lock
        with self.assertRaises(ContractError):
            verify_environment(self.root, 'host')


if __name__ == '__main__':
    unittest.main()

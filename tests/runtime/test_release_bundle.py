"""IDEA-047 H01: the host release bundle (tools/build_release_bundle.py), with a throwaway repository."""
import hashlib
import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from larp.contracts import ContractError, Document
from larp.runtime.preflight import release_files, verify_release
from larp.runtime.register import load_register

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import build_release_bundle as bundle  # noqa: E402

PYTHON = b'synthetic python archive'
CA = b'-----BEGIN CERTIFICATE-----\nsynthetic\n-----END CERTIFICATE-----\n'


def run(*args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


@unittest.skipIf(shutil.which('git') is None, 'git not installed')
class ReleaseBundle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo, remote, self.out = base / 'repo', base / 'remote.git', base / 'out'
        run('git', 'init', '-q', '--bare', str(remote), cwd=base)
        self.repo.mkdir()
        run('git', 'init', '-q', '-b', 'main', cwd=self.repo)
        for name in ('larp/runtime/operations.py', 'larp/__init__.py', 'deploy/requirements-runtime.lock',
                     'deploy/requirements-aws.lock', 'deploy/requirements-signer.lock', 'deploy/host/provision.sh',
                     'deploy/systemd/larp-signer.service', 'config/release/services.v1.json',
                     'config/release/deviations.v1.json', 'docs/proposal/proposal_answers.md',
                     'larp/runtime/preflight.py', 'larp/runtime/register.py', 'larp/runtime/release.py',
                     'larp/contracts.py'):
            (self.repo / name).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / name).write_bytes((ROOT / name).read_bytes())
        (self.repo / 'deploy/requirements-runtime.lock').write_text('psycopg==3.3.6\n')
        (self.repo / 'deploy/requirements-aws.lock').write_text('-r requirements-runtime.lock\nboto3==1.43.111\n')
        (self.repo / 'deploy/requirements-signer.lock').write_text('-r requirements-runtime.lock\nrlp==5.0.0\n')
        self.pin(hashlib.sha256(PYTHON).hexdigest())
        run('git', 'add', '-A', cwd=self.repo)
        self.commit('initial')
        run('git', 'remote', 'add', 'origin', str(remote), cwd=self.repo)
        run('git', 'push', '-q', '-u', 'origin', 'main', cwd=self.repo)
        self.python = PYTHON

    def pin(self, sha, arch='x86_64'):
        (self.repo / 'deploy/host').mkdir(parents=True, exist_ok=True)
        (self.repo / 'deploy/host/python.lock').write_text(f'# test\ntag=20261001\nversion=3.12.15\n{arch}={sha}\n')

    def commit(self, message):
        run('git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-q', '-m', message,
            cwd=self.repo)

    def fetch(self, url, path):
        Path(path).write_bytes(self.python if url.endswith('.tar.gz') else CA)

    def wheels(self, names=('psycopg-3.3.6', 'boto3-1.43.111', 'rlp-5.0.0')):
        def download(release, arch, directory):
            for name in names:
                (directory / f'{name}-py3-none-any.whl').write_bytes(name.encode())
        return download

    def build(self, **kwargs):
        return bundle.build(self.repo, kwargs.pop('arch', 'x86_64'), self.out, fetch=self.fetch,
                            wheels=kwargs.pop('wheels', self.wheels()), **kwargs)

    def test_h01_bundle_contents_and_checksums(self):
        result = self.build()
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.repo, capture_output=True,
                                text=True).stdout.strip()
        self.assertEqual(result['build_id'], commit)
        archive = Path(result['bundle'])
        self.assertEqual(archive.name, f'larp-{commit[:12]}-x86_64.tar.gz')
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), result['sha256'])
        self.assertIn(result['sha256'], (self.out / (archive.name + '.sha256')).read_text())
        with tarfile.open(archive) as tar:
            members = {m.name: m for m in tar.getmembers()}
            top = f'larp-{commit[:12]}-x86_64/'
            for member in members.values():
                self.assertTrue(member.isfile() or member.isdir())
                self.assertEqual((member.uid, member.gid), (0, 0))
            read = lambda name: tar.extractfile(members[top + name]).read()
            sums = dict(reversed(line.split('  ', 1)) for line in read('SHA256SUMS').decode().splitlines())
            files = {n[len(top):] for n, m in members.items() if m.isfile()} - {'SHA256SUMS'}
            self.assertEqual(set(sums), files)
            for name, digest in sums.items():
                self.assertEqual(hashlib.sha256(read(name)).hexdigest(), digest, name)
            self.assertEqual(read('release/larp/runtime/operations.py'),
                             (ROOT / 'larp/runtime/operations.py').read_bytes())
            self.assertEqual(read('provision.sh'), (ROOT / 'deploy/host/provision.sh').read_bytes())
            self.assertEqual(members[top + 'provision.sh'].mode, 0o755)
            env = dict(line.split('=', 1) for line in read('BUNDLE.env').decode().splitlines())
            self.assertEqual((env['arch'], env['python_version'], env['python_sha256']),
                             ('x86_64', '3.12.15', hashlib.sha256(PYTHON).hexdigest()))
            self.assertEqual(env['rds_ca_sha256'], hashlib.sha256(CA).hexdigest())
            self.assertEqual(read('release/docs/proposal/proposal_answers.md'),
                             (ROOT / 'docs/proposal/proposal_answers.md').read_bytes())

    def test_r8_extracted_release_verifies_and_binds_the_proposal(self):
        result = self.build()
        extracted = Path(self.tmp.name) / 'extracted'
        with tarfile.open(result['bundle']) as tar:
            tar.extractall(extracted, filter='data')
        root = next(extracted.glob('larp-*')) / 'release'
        build = result['build_id']
        manifest = Document.from_dict(dict(
            schema='ReleaseManifest.v1', build_id=build, repository='synthetic', remote_verified=True,
            services=['synthetic'], registration_evidence=dict(schema='RegistrationEvidence.v1',
                evidence_ref='synthetic-only', build_id=build, repository='synthetic'),
            files={name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in release_files(root)},
            release_register=load_register(root)))
        self.assertEqual(verify_release(manifest, root)['build_id'], build)
        proposal = root / 'docs/proposal/proposal_answers.md'
        proposal.write_text(proposal.read_text() + '\nchanged after packaging\n')
        with self.assertRaisesRegex(ContractError, 'hash mismatch'):
            verify_release(manifest, root)

    def test_wr_d3_the_bundle_carries_the_ci_release_manifest(self):
        """IDEA-049-D WR-D3a (#62 item 3): the release manifest is built with the bundle, never on a host."""
        import json
        result = self.build()
        commit = result['build_id']
        beside = self.out / f'larp-{commit[:12]}-x86_64.release.json'
        self.assertEqual(Path(result['manifest']).resolve(), beside.resolve())
        self.assertEqual(result['manifest_sha256'], hashlib.sha256(beside.read_bytes()).hexdigest())
        extracted = Path(self.tmp.name) / 'extracted'
        with tarfile.open(result['bundle']) as tar:
            tar.extractall(extracted, filter='data')
        top = next(extracted.glob('larp-*'))
        inside = top / 'release-manifest.json'
        self.assertEqual(inside.read_bytes(), beside.read_bytes())
        self.assertIn('  release-manifest.json', (top / 'SHA256SUMS').read_text())
        root = top / 'release'
        m = Document(inside.read_bytes()).read()
        remote = subprocess.run(['git', 'config', '--get', 'remote.origin.url'], cwd=self.repo, capture_output=True,
                                text=True).stdout.strip()
        self.assertEqual((m['schema'], m['build_id'], m['repository'], m['remote_verified']),
                         ('ReleaseManifest.v1', commit, remote, True))
        self.assertEqual(m['services'], json.loads((ROOT / 'config/release/services.v1.json').read_text()))
        self.assertEqual(m['files'], {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                      for name in release_files(root)})
        self.assertEqual(m['release_register'], load_register(root))
        self.assertIsNone(m.get('registration_evidence'))
        for binding in ('operations_config_sha256', 'runtime_config_sha256', 'service_configs_sha256'):
            self.assertIsNone(m.get(binding), binding)
        # A remote URL carrying credentials is never recorded (git still reaches the same bare repository).
        secret = 'https://x-access-token:synthetic@github.com/example/larp.git'
        run('git', 'remote', 'set-url', 'origin', secret, cwd=self.repo)
        run('git', 'config', f'url.{self.repo.parent / "remote.git"}.insteadOf', secret, cwd=self.repo)
        with self.assertRaisesRegex(bundle.BundleError, 'credential'):
            self.build()

    def test_h01_committed_bytes_not_the_working_tree(self):
        (self.repo / 'scratch.txt').write_text('untracked files are not released')
        result = self.build()
        with tarfile.open(result['bundle']) as tar:
            self.assertFalse(any(m.name.endswith('scratch.txt') for m in tar.getmembers()))

    def test_h01_refusals(self):
        (self.repo / 'larp/runtime/operations.py').write_text('# changed\n')
        with self.assertRaisesRegex(bundle.BundleError, 'uncommitted'):
            self.build()
        run('git', 'add', '-A', cwd=self.repo)
        self.commit('not pushed')
        with self.assertRaisesRegex(bundle.BundleError, 'pushed'):
            self.build()
        run('git', 'push', '-q', cwd=self.repo)
        with self.assertRaisesRegex(bundle.BundleError, 'No pinned Python'):
            self.build(arch='aarch64')
        self.python = b'tampered'
        with self.assertRaisesRegex(bundle.BundleError, 'checksum'):
            self.build()
        self.python = PYTHON
        with self.assertRaisesRegex(bundle.BundleError, 'rlp==5.0.0'):
            self.build(wheels=self.wheels(('psycopg-3.3.6', 'boto3-1.43.111')))
        with self.assertRaisesRegex(bundle.BundleError, 'Unsupported'):
            self.build(arch='riscv64')
        self.assertEqual(list(self.out.glob('*.tar.gz')) if self.out.exists() else [], [])

    def test_h01_python_pin_parsing(self):
        pin = bundle.python_pin('tag=20261001\nversion=3.12.15\nx86_64=' + 'a' * 64 + '\n', 'x86_64')
        self.assertEqual(pin['file'], 'cpython-3.12.15+20261001-x86_64-unknown-linux-gnu-install_only.tar.gz')
        self.assertTrue(pin['url'].startswith('https://github.com/astral-sh/python-build-standalone/releases/'))
        for source in ('tag=1\nversion=3\nx86_64=short', 'version=3\nx86_64=' + 'a' * 64, ''):
            with self.subTest(source=source), self.assertRaises(bundle.BundleError):
                bundle.python_pin(source, 'x86_64')
        real = bundle.python_pin((ROOT / 'deploy/host/python.lock').read_text(), 'x86_64')
        self.assertEqual(real['version'], '3.12.15')


if __name__ == '__main__':
    unittest.main()

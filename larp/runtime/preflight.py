"""Build/verify a local release manifest, never register or activate a wallet."""

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess

from larp.contracts import ContractError, Document
from larp.runtime.register import load_register
from larp.runtime.release import verify_manifest


def release_files(root):
    root = Path(root).resolve()
    files = set()
    patterns = [('larp', '*.py'), ('migrations', '*.sql'), ('deploy', '*.lock'),
                ('deploy', '*.tf'), ('deploy/systemd', '*'), ('deploy/postgres', '*.sql'),
                ('deploy', 'Dockerfile'), ('config', '*.json'), ('config', '*.txt')]
    for directory, pattern in patterns:
        for path in (root / directory).rglob(pattern):
            # Host-local configuration and downloaded Terraform modules are not release code.
            if path.name.endswith('.local.json') or '.terraform' in path.relative_to(root).parts:
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ContractError('Release files must not escape through symlinks')
            files.add(path.relative_to(root).as_posix())
    if not files or 'larp/runtime/operations.py' not in files:
        raise ContractError('Incomplete release directory')
    return files


def verify_environment(root):
    """The operations service checks its own small installed dependency profile."""
    directory = Path(root) / 'deploy'
    for filename in ('requirements-runtime.lock', 'requirements-aws.lock'):
        for line in (directory / filename).read_text(encoding='utf-8').splitlines():
            value = line.split('#', 1)[0].strip()
            if not value or value.startswith('-r '):
                continue
            name, expected = value.split('==')
            if version(name) != expected:
                raise ContractError('Installed operations dependency differs from manifest lock')


def verify_release(manifest, root):
    m = verify_manifest(manifest, root)
    if not release_files(root).issubset(m['files']):
        raise ContractError('Executable files are missing from the manifest')
    evidence = m.get('registration_evidence', {})
    if (not isinstance(evidence, dict) or evidence.get('schema') != 'RegistrationEvidence.v1'
            or not evidence.get('evidence_ref') or evidence.get('build_id') != m.get('build_id')
            or evidence.get('repository') != m.get('repository') or not m.get('services')
            or not m.get('remote_verified')):
        raise ContractError('Recorded registration/build/services evidence is incomplete')
    # Services list and deviations register (F-61, GAP-62; IDEA-042 item 8): valid and exactly as manifested.
    if m.get('release_register') != load_register(root):
        raise ContractError('Release register is missing, invalid or changed since the manifest')
    return m


def tracked_release_files(root, git):
    """release_files(root), refusing any that git does not track (an ignored file
    would put its hash into release provenance and be missing on the deploy host)."""
    names = release_files(root)
    untracked = names - set(git('ls-files', '-z').split('\0'))
    if untracked:
        raise ContractError('Release files are not tracked by git: ' + ', '.join(sorted(untracked)[:5]))
    return names


def verify_runtime_config(manifest, raw):
    if manifest.get('runtime_config_sha256') != hashlib.sha256(raw).hexdigest():
        raise ContractError('Runtime configuration differs from the registered manifest')


def build_manifest(root, services, registration_evidence=None, operations_config=None, runtime_config=None):
    root = Path(root).resolve()
    def git(*args):
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                                text=True, timeout=30, check=True)
        return result.stdout.strip()
    if git('status', '--porcelain'):
        raise ContractError('Build requires a clean checkout')
    commit = git('rev-parse', 'HEAD')
    branch = git('branch', '--show-current')
    remote = git('remote', 'get-url', 'origin')
    if not remote.startswith('https://github.com/') or '@' in remote:
        raise ContractError('Expected credential-free registered repository URL')
    remote_row = git('ls-remote', '--exit-code', 'origin', 'refs/heads/' + branch).split()
    if not remote_row or remote_row[0] != commit:
        raise ContractError('Build commit is not the pushed branch head')
    names = tracked_release_files(root, git)
    files = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sorted(names)}
    return Document.from_dict(dict(schema='ReleaseManifest.v1', build_id=commit,
        repository=remote, remote_verified=True, services=services,
        registration_evidence=registration_evidence, files=files, release_register=load_register(root),
        operations_config_sha256=hashlib.sha256(operations_config).hexdigest() if operations_config else None,
        runtime_config_sha256=hashlib.sha256(runtime_config).hexdigest() if runtime_config is not None else None))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest')
    parser.add_argument('--root', required=True)
    parser.add_argument('--build-output')
    parser.add_argument('--services')
    parser.add_argument('--registration-evidence')
    parser.add_argument('--config')
    parser.add_argument('--runtime-config')
    args = parser.parse_args(argv)
    try:
        if args.build_output:
            if not args.services:
                raise ContractError('Explicit services document is required')
            services = json.loads(Path(args.services).read_text(encoding='utf-8'))
            evidence = (json.loads(Path(args.registration_evidence).read_text(encoding='utf-8'))
                        if args.registration_evidence else None)
            config = Path(args.config).read_bytes() if args.config else None
            runtime_config = Path(args.runtime_config).read_bytes() if args.runtime_config else None
            manifest = build_manifest(args.root, services, evidence, config, runtime_config)
            # Exclusive creation avoids replacing a release's provenance.
            with Path(args.build_output).open('xb') as stream:
                stream.write(manifest.payload)
            print(json.dumps(dict(manifest_created=True, registration_evidence_supplied=evidence is not None, signing_enabled=False)))
        else:
            m = verify_release(Document(Path(args.manifest).read_bytes()), args.root)
            verify_environment(args.root)
            if args.config and hashlib.sha256(Path(args.config).read_bytes()).hexdigest() != m.get('operations_config_sha256'):
                raise ContractError('Operations configuration differs from the registered manifest')
            if args.runtime_config:
                verify_runtime_config(m, Path(args.runtime_config).read_bytes())
            print(json.dumps(dict(release_verified=True, signing_enabled=False)))
        return 0
    except Exception:
        print(json.dumps(dict(release_verified=False, reason='RELEASE_CHECK_FAILED', signing_enabled=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

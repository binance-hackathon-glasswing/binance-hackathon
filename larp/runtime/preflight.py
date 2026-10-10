"""Build/verify a local release manifest, never register or activate a wallet."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from larp.contracts import ContractError, Document
from larp.runtime.release import verify_manifest


def release_files(root):
    root = Path(root).resolve()
    files = set()
    for directory, pattern in (('larp', '*.py'), ('migrations', '*.sql'), ('deploy', '*.lock')):
        for path in (root / directory).rglob(pattern):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ContractError('Release files must not escape through symlinks')
            files.add(path.relative_to(root).as_posix())
    if not files or 'larp/runtime/operations.py' not in files:
        raise ContractError('Incomplete release directory')
    return files


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
    return m


def build_manifest(root, services, registration_evidence=None):
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
    files = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
             for name in sorted(release_files(root))}
    return Document.from_dict(dict(schema='ReleaseManifest.v1', build_id=commit,
        repository=remote, remote_verified=True, services=services,
        registration_evidence=registration_evidence, files=files))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest')
    parser.add_argument('--root', required=True)
    parser.add_argument('--build-output')
    parser.add_argument('--services')
    parser.add_argument('--registration-evidence')
    args = parser.parse_args(argv)
    try:
        if args.build_output:
            if not args.services:
                raise ContractError('Explicit services document is required')
            services = json.loads(Path(args.services).read_text(encoding='utf-8'))
            evidence = (json.loads(Path(args.registration_evidence).read_text(encoding='utf-8'))
                        if args.registration_evidence else None)
            manifest = build_manifest(args.root, services, evidence)
            # Exclusive creation avoids replacing a release's provenance.
            with Path(args.build_output).open('xb') as stream:
                stream.write(manifest.payload)
            print(json.dumps(dict(manifest_created=True, registered=evidence is not None, signing_enabled=False)))
        else:
            verify_release(Document(Path(args.manifest).read_bytes()), args.root)
            print(json.dumps(dict(release_verified=True, signing_enabled=False)))
        return 0
    except Exception:
        print(json.dumps(dict(release_verified=False, reason='RELEASE_CHECK_FAILED', signing_enabled=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

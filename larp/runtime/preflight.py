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
                ('deploy', 'Dockerfile'), ('config', '*.json'), ('config', '*.txt'),
                # Routed-assessor stage prompts are pinned by the routing spec and read at startup (IDEA-081).
                ('config/intelligence/prompts', '*.md'),
                # The deviations register validates verbatim quotes against this file at every host startup.
                ('docs/proposal', 'proposal_answers.md')]
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


PROFILES = {
    'operations': ('requirements-runtime.lock', 'requirements-aws.lock'),
    # Both hosts run the signer lock too: the signer signs, and the execution service verifies signed bytes.
    'host': ('requirements-runtime.lock', 'requirements-aws.lock', 'requirements-signer.lock'),
}


def verify_environment(root, profile='operations'):
    """Each service checks its installed dependency profile against the release locks."""
    directory = Path(root) / 'deploy'
    for filename in PROFILES[profile]:
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


def verify_service_config(manifest, name, raw):
    """A host service's configuration is part of the registered version (G-03), as the runtime's is."""
    recorded = manifest.get('service_configs_sha256')
    if type(recorded) is not dict or recorded.get(name) != hashlib.sha256(raw).hexdigest():
        raise ContractError('Service configuration differs from the registered manifest')


def service_config_arguments(values):
    """`NAME=PATH` arguments -> {name: bytes}; names are unique."""
    configs = {}
    for value in values or ():
        name, separator, path = value.partition('=')
        if not separator or not name or not path or name in configs:
            raise ContractError('Service configs are NAME=PATH, each name once')
        configs[name] = Path(path).read_bytes()
    return configs


def build_manifest(root, services, registration_evidence=None, operations_config=None, runtime_config=None,
                   service_configs=None):
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
    value = dict(schema='ReleaseManifest.v1', build_id=commit,
        repository=remote, remote_verified=True, services=services,
        registration_evidence=registration_evidence, files=files, release_register=load_register(root),
        operations_config_sha256=hashlib.sha256(operations_config).hexdigest() if operations_config else None,
        runtime_config_sha256=hashlib.sha256(runtime_config).hexdigest() if runtime_config is not None else None)
    if service_configs:
        value['service_configs_sha256'] = {name: hashlib.sha256(raw).hexdigest()
                                           for name, raw in sorted(service_configs.items())}
    return Document.from_dict(value)


HOST_BINDINGS = ('registration_evidence', 'operations_config_sha256', 'runtime_config_sha256', 'service_configs_sha256')


def bind_manifest(ci_manifest, root, registration_evidence=None, operations_config=None, runtime_config=None,
                  service_configs=None):
    """A host's release manifest from the one CI built with the bundle (IDEA-049-D WR-D3, #62 item 3).

    Code identity is never recomputed here: every file, the services list and the register must be exactly as CI
    recorded them, and are copied unchanged. The host adds only what CI cannot know: the registration evidence and
    the hashes of its own configuration files (account-specific, never committed; IDEA-051). Needs no git."""
    ci = ci_manifest.read()
    if any(ci.get(key) is not None for key in HOST_BINDINGS):
        raise ContractError('CI manifest already carries host bindings')
    if not ci.get('build_id') or not ci.get('repository') or not ci.get('services') or not ci.get('remote_verified'):
        raise ContractError('CI manifest lacks its build identity')
    verify_manifest(ci_manifest, root)
    if not release_files(root).issubset(ci['files']):
        raise ContractError('Executable files are missing from the manifest')
    if ci.get('release_register') != load_register(root):
        raise ContractError('Release register differs from the CI manifest')
    if registration_evidence is not None and (
            type(registration_evidence) is not dict
            or registration_evidence.get('schema') != 'RegistrationEvidence.v1'
            or not registration_evidence.get('evidence_ref') or registration_evidence.get('build_id') != ci['build_id']
            or registration_evidence.get('repository') != ci['repository']):
        raise ContractError('Registration evidence is for another build or repository')
    value = dict(ci, registration_evidence=registration_evidence,
                 ci_manifest_sha256=hashlib.sha256(ci_manifest.payload).hexdigest(),
                 operations_config_sha256=hashlib.sha256(operations_config).hexdigest() if operations_config else None,
                 runtime_config_sha256=(hashlib.sha256(runtime_config).hexdigest() if runtime_config is not None
                                        else None))
    if service_configs:
        value['service_configs_sha256'] = {name: hashlib.sha256(raw).hexdigest()
                                           for name, raw in sorted(service_configs.items())}
    return Document.from_dict(value)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest')
    parser.add_argument('--root', required=True)
    parser.add_argument('--build-output')
    # The CI-built release-manifest.json, verified here and written bound to this host at --output (#62 item 3).
    parser.add_argument('--bind', metavar='CI_MANIFEST')
    parser.add_argument('--output')
    parser.add_argument('--services')
    parser.add_argument('--registration-evidence')
    parser.add_argument('--config')
    parser.add_argument('--runtime-config')
    parser.add_argument('--service-config', action='append', metavar='NAME=PATH')
    parser.add_argument('--profile', choices=tuple(PROFILES), default='operations')
    args = parser.parse_args(argv)
    try:
        if args.bind:
            if not args.output or args.build_output:
                raise ContractError('--bind writes to --output and never builds a manifest')
            ci = Document(Path(args.bind).read_bytes())
            evidence = (json.loads(Path(args.registration_evidence).read_text(encoding='utf-8'))
                        if args.registration_evidence else None)
            config = Path(args.config).read_bytes() if args.config else None
            runtime_config = Path(args.runtime_config).read_bytes() if args.runtime_config else None
            manifest = bind_manifest(ci, args.root, evidence, config, runtime_config,
                                     service_config_arguments(args.service_config))
            with Path(args.output).open('xb') as stream:
                stream.write(manifest.payload)
            print(json.dumps(dict(manifest_bound=True, ci_manifest_sha256=manifest.read()['ci_manifest_sha256'],
                                  registration_evidence_supplied=evidence is not None, signing_enabled=False)))
        elif args.build_output:
            if not args.services:
                raise ContractError('Explicit services document is required')
            services = json.loads(Path(args.services).read_text(encoding='utf-8'))
            evidence = (json.loads(Path(args.registration_evidence).read_text(encoding='utf-8'))
                        if args.registration_evidence else None)
            config = Path(args.config).read_bytes() if args.config else None
            runtime_config = Path(args.runtime_config).read_bytes() if args.runtime_config else None
            manifest = build_manifest(args.root, services, evidence, config, runtime_config,
                                      service_config_arguments(args.service_config))
            # Exclusive creation avoids replacing a release's provenance.
            with Path(args.build_output).open('xb') as stream:
                stream.write(manifest.payload)
            print(json.dumps(dict(manifest_created=True, registration_evidence_supplied=evidence is not None, signing_enabled=False)))
        else:
            m = verify_release(Document(Path(args.manifest).read_bytes()), args.root)
            verify_environment(args.root, args.profile)
            if args.config and hashlib.sha256(Path(args.config).read_bytes()).hexdigest() != m.get('operations_config_sha256'):
                raise ContractError('Operations configuration differs from the registered manifest')
            if args.runtime_config:
                verify_runtime_config(m, Path(args.runtime_config).read_bytes())
            for name, raw in service_config_arguments(args.service_config).items():
                verify_service_config(m, name, raw)
            print(json.dumps(dict(release_verified=True, signing_enabled=False)))
        return 0
    except Exception:
        print(json.dumps(dict(release_verified=False, reason='RELEASE_CHECK_FAILED', signing_enabled=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Build the host release bundle (IDEA-047 H01). Run on a development machine with internet access.

    python tools/build_release_bundle.py --arch x86_64 --out <dir> [--rds-region ap-southeast-2]

The bundle carries everything a host installs, so the signer (no internet route, IDEA-046 B2) installs it offline:

    larp-<build12>-<arch>/
      BUNDLE.env      build, architecture, pinned Python and RDS CA identity (key=value)
      SHA256SUMS      every other file in the bundle
      provision.sh    deploy/host/provision.sh at the same commit
      python/         CPython 3.12.15 from python-build-standalone, checksum-pinned in deploy/host/python.lock
      wheels/         Linux CPython 3.12 wheels for every pin in the signer and AWS locks (the signer lock includes
                      the runtime lock)
      rds-ca.pem      the region's RDS certificate bundle; its SHA-256 goes into each service config
      release/        the commit's tracked release files (larp.runtime.preflight.release_files), from `git archive`

It refuses a tracked file with uncommitted changes, a commit that is not the pushed branch head, an architecture
without a pinned Python checksum, a Python download whose checksum differs, and any pinned package without a wheel.
Upload the `.tar.gz` and its `.sha256` to the artifact bucket under `releases/` (deploy/aws/hosts.tf grants hosts
read access there through the S3 gateway endpoint). Nothing here contacts AWS.
"""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ARCHES = ('x86_64', 'aarch64')
# Amazon Linux 2023 has glibc 2.34.
PLATFORMS = ('manylinux2014_{arch}', 'manylinux_2_17_{arch}', 'manylinux_2_28_{arch}', 'manylinux_2_34_{arch}')
LOCKS = ('deploy/requirements-signer.lock', 'deploy/requirements-aws.lock')
PROVISION = 'deploy/host/provision.sh'
PYTHON_LOCK = 'deploy/host/python.lock'
PBS_URL = ('https://github.com/astral-sh/python-build-standalone/releases/download/{tag}/'
           'cpython-{version}+{tag}-{arch}-unknown-linux-gnu-install_only.tar.gz')
RDS_CA_URL = 'https://truststore.pki.rds.amazonaws.com/{region}/{region}-bundle.pem'


class BundleError(Exception):
    pass


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=120,
                          check=True).stdout


def text(output):
    return output.decode('utf-8').strip()


def source_commit(root, git=git):
    """The pushed branch head; uncommitted changes to tracked files refuse (untracked files are not released)."""
    if text(git(root, 'status', '--porcelain', '--untracked-files=no')):
        raise BundleError('Tracked files have uncommitted changes')
    commit, branch = text(git(root, 'rev-parse', 'HEAD')), text(git(root, 'branch', '--show-current'))
    if not branch:
        raise BundleError('Build from a branch, not a detached HEAD')
    try:
        row = text(git(root, 'ls-remote', '--exit-code', 'origin', 'refs/heads/' + branch)).split()
    except subprocess.CalledProcessError:
        row = []
    if not row or row[0] != commit:
        raise BundleError('HEAD is not the pushed branch head')
    return commit


def python_pin(source, arch):
    values = dict(line.split('=', 1) for line in source.splitlines() if '=' in line and not line.startswith('#'))
    sha = values.get(arch, '')
    if not re.fullmatch(r'[0-9a-f]{64}', sha) or not values.get('tag') or not values.get('version'):
        raise BundleError('No pinned Python build for ' + arch)
    url = PBS_URL.format(tag=values['tag'], version=values['version'], arch=arch)
    return dict(tag=values['tag'], version=values['version'], sha256=sha, url=url, file=url.rsplit('/', 1)[1])


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def fetch(url, path):
    with urllib.request.urlopen(url, timeout=120) as response, open(path, 'wb') as out:
        shutil.copyfileobj(response, out)


def committed_files(root, commit, names, git=git):
    """{name: bytes} for `names` exactly as committed; symlinks and missing names refuse."""
    archive = tarfile.open(fileobj=io.BytesIO(git(root, 'archive', '--format=tar', commit)))
    found = {}
    for member in archive.getmembers():
        if member.name in names:
            if not member.isfile():
                raise BundleError('Release path is not a regular file: ' + member.name)
            found[member.name] = (archive.extractfile(member).read(), member.mode)
    missing = sorted(set(names) - set(found))
    if missing:
        raise BundleError('Not in the commit: ' + ', '.join(missing[:5]))
    return found


def release_names(root, git=git):
    sys.path.insert(0, str(root))
    from larp.runtime.preflight import tracked_release_files
    return tracked_release_files(root, lambda *args: text(git(root, *args)))


def lock_pins(release):
    pins = []
    for lock in LOCKS:
        for line in (release / lock).read_text(encoding='utf-8').splitlines():
            value = line.split('#', 1)[0].strip()
            if value and not value.startswith('-r '):
                name, version = value.split('==')
                pins.append((name, version))
    return sorted(set(pins))


def normalized(name):
    return re.sub(r'[-_.]+', '_', name).lower()


def download_wheels(release, arch, wheels):
    command = [sys.executable, '-m', 'pip', 'download', '--quiet', '--no-deps', '--only-binary=:all:',
               '--implementation', 'cp', '--python-version', '3.12', '--abi', 'cp312', '--dest', str(wheels)]
    for platform in PLATFORMS:
        command += ['--platform', platform.format(arch=arch)]
    for lock in LOCKS:
        command += ['-r', str(release / lock)]
    subprocess.run(command, check=True, timeout=900)


def check_wheels(release, wheels):
    present = {normalized('-'.join(p.name.split('-')[:2])) for p in wheels.glob('*.whl')}
    missing = [f'{n}=={v}' for n, v in lock_pins(release) if normalized(f'{n}-{v}') not in present]
    if missing:
        raise BundleError('No Linux wheel for: ' + ', '.join(missing))


def write_checksums(directory):
    lines = []
    for path in sorted(p for p in directory.rglob('*') if p.is_file()):
        lines.append(f'{sha256_file(path)}  {path.relative_to(directory).as_posix()}')
    (directory / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def reset(info):
    info.uid = info.gid = 0
    info.uname = info.gname = 'root'
    info.mtime = 0
    return info


def build(root, arch, out, *, region='ap-southeast-2', git=git, fetch=fetch, wheels=download_wheels):
    root, out = Path(root).resolve(), Path(out).resolve()
    if arch not in ARCHES:
        raise BundleError('Unsupported architecture')
    commit = source_commit(root, git)
    names = release_names(root, git)
    files = committed_files(root, commit, names | {PROVISION, PYTHON_LOCK}, git)
    pin = python_pin(files[PYTHON_LOCK][0].decode('utf-8'), arch)
    name = f'larp-{commit[:12]}-{arch}'
    with tempfile.TemporaryDirectory() as temporary:
        bundle = Path(temporary) / name
        for path, (data, mode) in files.items():
            target = bundle / 'release' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (bundle / 'provision.sh').write_bytes(files[PROVISION][0])
        (bundle / 'python').mkdir()
        python = bundle / 'python' / pin['file']
        fetch(pin['url'], python)
        if sha256_file(python) != pin['sha256']:
            raise BundleError('Python download differs from its pinned checksum')
        fetch(RDS_CA_URL.format(region=region), bundle / 'rds-ca.pem')
        if b'BEGIN CERTIFICATE' not in (bundle / 'rds-ca.pem').read_bytes():
            raise BundleError('RDS certificate bundle download is not PEM')
        (bundle / 'wheels').mkdir()
        wheels(bundle / 'release', arch, bundle / 'wheels')
        check_wheels(bundle / 'release', bundle / 'wheels')
        identity = dict(build_id=commit, arch=arch, python_version=pin['version'], python_tag=pin['tag'],
                        python_file=pin['file'], python_sha256=pin['sha256'], rds_region=region,
                        rds_ca_sha256=sha256_file(bundle / 'rds-ca.pem'))
        (bundle / 'BUNDLE.env').write_text(''.join(f'{k}={v}\n' for k, v in identity.items()), encoding='utf-8')
        write_checksums(bundle)
        out.mkdir(parents=True, exist_ok=True)
        archive = out / (name + '.tar.gz')
        with tarfile.open(archive, 'w:gz', format=tarfile.PAX_FORMAT) as tar:
            for path in [bundle] + sorted(bundle.rglob('*')):
                info = reset(tar.gettarinfo(str(path), arcname=path.relative_to(bundle.parent).as_posix()))
                info.mode = 0o755 if path.is_dir() or path.name == 'provision.sh' else 0o644
                if path.is_file():
                    with open(path, 'rb') as stream:
                        tar.addfile(info, stream)
                else:
                    tar.addfile(info)
    digest = sha256_file(archive)
    (out / (name + '.tar.gz.sha256')).write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    return dict(bundle=str(archive), sha256=digest, **identity)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--arch', choices=ARCHES, default='x86_64')
    parser.add_argument('--out', required=True)
    parser.add_argument('--rds-region', default='ap-southeast-2')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(ROOT, args.arch, args.out, region=args.rds_region), indent=1))
        return 0
    except (BundleError, subprocess.CalledProcessError, OSError) as error:
        print(json.dumps(dict(built=False, reason=type(error).__name__, detail=str(error))), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

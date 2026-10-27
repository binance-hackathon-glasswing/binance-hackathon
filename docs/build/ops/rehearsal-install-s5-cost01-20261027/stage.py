"""Verify the exact delivered bundle and create its detached source checkout. No AWS calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
from datetime import datetime, timezone


def require(ok, reason):
    if not ok:
        raise SystemExit('Stage refused: ' + reason)


def verify_bundle(path, package):
    pins = package['pins']
    require(hashlib.sha256(path.read_bytes()).hexdigest() == pins['BUNDLE_SHA256'], 'bundle digest')
    prefix = pins['BUNDLE'] + '/'
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        require(len({m.name for m in members}) == len(members), 'duplicate archive member')
        require(all((m.name.startswith(prefix) or m.name == pins['BUNDLE']) and '..' not in Path(m.name).parts
                    and not Path(m.name).is_absolute() and (m.isfile() or m.isdir()) for m in members),
                'unsafe archive member')
        def raw(name):
            return archive.extractfile(prefix + name).read()
        require(hashlib.sha256(raw('release-manifest.json')).hexdigest() == pins['MANIFEST_SHA256'], 'manifest digest')
        require(hashlib.sha256(raw('provision.sh')).hexdigest() == pins['PROVISION_SHA256'], 'provision digest')
        require(hashlib.sha256(raw('rds-ca.pem')).hexdigest() == pins['CA_SHA256'], 'CA digest')
        require(json.loads(raw('release-manifest.json'))['build_id'] == package['build_id'], 'manifest build')
        count = 0
        for line in raw('SHA256SUMS').decode().splitlines():
            expected, name = line.split(maxsplit=1)
            name = name.lstrip('*')
            require('..' not in Path(name).parts and not Path(name).is_absolute(), 'unsafe checksum path')
            require(hashlib.sha256(raw(name)).hexdigest() == expected, 'member checksum: ' + name)
            count += 1
    return count


def main():
    os.umask(0o077)
    here = Path(__file__).resolve().parent
    package = json.loads((here / 'package.json').read_text())
    require(datetime.now(timezone.utc) < datetime.fromisoformat('2026-10-27T14:00:00+00:00'),
            'buy window expired; obtain new profile and signer acceptance')
    repo = Path(os.environ['LARP_REPO']).resolve()
    require(not here.is_relative_to(repo) or here.is_relative_to(repo / 'deploy/activation'),
            'copy operator package outside tracked source first')
    profile = here / 'inputs/rehearsal-s5-next.json'
    require(hashlib.sha256(profile.read_bytes()).hexdigest() == package['profile_sha256'], 'profile digest')
    history = here / 'inputs/token-history.json'
    require(hashlib.sha256(history.read_bytes()).hexdigest() == package['history_sha256'], 'history digest')
    bundle = here / 'bundle' / (package['pins']['BUNDLE'] + '.tar.gz')
    count = verify_bundle(bundle, package)
    destination = here / 'bundle/x'
    if not destination.exists():
        destination.mkdir()
        with tarfile.open(bundle) as archive:
            archive.extractall(destination, filter='data')
    require(not destination.is_symlink(), 'extraction directory is a link')
    extracted = destination / package['pins']['BUNDLE']
    with tarfile.open(bundle) as archive:
        for member in archive.getmembers():
            if member.isfile():
                path = destination / member.name
                require(path.is_file() and not path.is_symlink()
                        and path.resolve().is_relative_to(extracted.resolve()), 'unsafe extracted file')
                require(hashlib.sha256(path.read_bytes()).digest()
                        == hashlib.sha256(archive.extractfile(member).read()).digest(), 'extracted file differs')
    source = repo / '.claude/worktrees' / ('release-' + package['build_id'][:7])
    if not source.exists():
        subprocess.run(['git', '-C', str(repo), 'fetch', 'origin', package['build_id']], check=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '--detach', str(source), package['build_id']], check=True)
    require(subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            == package['build_id'], 'release checkout build')
    require(not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip(),
            'release checkout dirty')
    # Input capture independently requires HEAD at a pushed branch, not a detached checkout.
    branch = package['source_branch']
    subprocess.run(['git', 'check-ref-format', '--branch', branch], check=True, capture_output=True)
    remote = subprocess.check_output(['git', '-C', str(source), 'ls-remote', '--exit-code',
                                     'origin', 'refs/heads/' + branch], text=True).split()
    require(remote and remote[0] == package['build_id'], 'release branch moved')
    subprocess.run(['git', '-C', str(source), 'fetch', 'origin',
                    'refs/heads/' + branch + ':refs/remotes/origin/' + branch], check=True)
    exists = subprocess.run(['git', '-C', str(source), 'show-ref', '--verify', '--quiet',
                             'refs/heads/' + branch]).returncode == 0
    if exists:
        require(subprocess.check_output(['git', '-C', str(source), 'rev-parse', branch], text=True).strip()
                == package['build_id'], 'local release branch moved')
        subprocess.run(['git', '-C', str(source), 'switch', branch], check=True)
    else:
        subprocess.run(['git', '-C', str(source), 'switch', '-c', branch, '--track', 'origin/' + branch], check=True)
    for number, commit in package['included_pr_merge_commits'].items():
        require(subprocess.run(['git', '-C', str(source), 'merge-base', '--is-ancestor',
                                commit, package['build_id']], capture_output=True).returncode == 0,
                'missing FS1 fix PR' + number)
    for name in ('private', 'results'):
        (here / name).mkdir(mode=0o700, exist_ok=True)
        (here / name).chmod(0o700)
    print(json.dumps(dict(stage='PASS', build=package['build_id'], verified_files=count,
                          next='Set private input paths; follow README. No AWS change performed.')))


if __name__ == '__main__':
    main()

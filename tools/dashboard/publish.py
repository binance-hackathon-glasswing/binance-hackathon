"""Build the wallet dashboard and push it to a GitHub Pages branch (IDEA-087).

  python -m tools.dashboard.publish --monitor-dir deploy/activation/rehearsal-monitor --repo OWNER/NAME \
      [--branch gh-pages] [--loop 600] [--full]

Each run builds the site (tools/dashboard/build.py) straight into a local clone of the Pages repository (default
deploy/activation/dashboard-pages/OWNER__NAME, git-ignored). It commits and pushes only when a file changed: one
commit per run, fast-forward only. It never force-pushes, and if the remote branch has diverged from the clone it stops
without writing anything. Git uses your usual credentials (for example `gh auth setup-git`); nothing is stored here.

The Pages repository holds only the built site. It must never be the main repository, which has to stay private
(F-24); that is refused. On the Free plan the Pages site is public, so keep the default redaction unless the site is
private.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from tools.dashboard.build import OUTPUTS, build

ROOT = Path(__file__).resolve().parents[2]
REPO = re.compile(r'^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$')
BRANCH = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$')
MIN_LOOP = 360  # GitHub's soft limit is 10 branch-based Pages builds per hour


class PublishError(RuntimeError):
    pass


def git(*args, cwd, check=True):
    done = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if check and done.returncode:
        raise PublishError('git %s failed: %s' % (args[0], (done.stderr or done.stdout).strip()[:300]))
    return done


def slug(url):
    """owner/name of a GitHub remote URL, lower-case, or None."""
    m = re.search(r'github\.com[:/]+([^/\s]+/[^/\s]+?)(?:\.git)?/?$', url or '')
    return m.group(1).lower() if m else None


def refuse_main_repository(repo, remote_url):
    origin = git('remote', 'get-url', 'origin', cwd=ROOT, check=False).stdout.strip()
    target = slug(remote_url) or repo.lower()
    if slug(origin) and target == slug(origin):
        raise PublishError('Refusing to publish into %s: that is the private main repository (F-24)' % repo)
    local = Path(remote_url)
    if local.exists() and local.resolve() == ROOT:
        raise PublishError('Refusing to publish into this checkout')


def prepare(remote_url, branch, clone):
    """A clone of the Pages repository with `branch` checked out and level with (or ahead of) the remote."""
    if not (clone / '.git').is_dir():
        if clone.exists() and any(clone.iterdir()):
            raise PublishError('%s exists and is not a git clone' % clone)
        clone.parent.mkdir(parents=True, exist_ok=True)
        git('clone', '--quiet', '--no-tags', remote_url, str(clone), cwd=clone.parent)
    if git('remote', 'get-url', 'origin', cwd=clone).stdout.strip() != remote_url:
        raise PublishError('%s is a clone of a different repository' % clone)
    git('fetch', '--quiet', '--prune', 'origin', cwd=clone)
    remote = git('rev-parse', '--verify', '--quiet', 'refs/remotes/origin/' + branch, cwd=clone, check=False).returncode == 0
    local = git('rev-parse', '--verify', '--quiet', 'refs/heads/' + branch, cwd=clone, check=False).returncode == 0
    if local:
        git('switch', '--quiet', branch, cwd=clone)
    elif remote:
        git('switch', '--quiet', '--create', branch, 'origin/' + branch, cwd=clone)
    else:
        git('switch', '--quiet', '--orphan', branch, cwd=clone)
    if remote and git('merge', '--ff-only', '--quiet', 'origin/' + branch, cwd=clone, check=False).returncode:
        raise PublishError('origin/%s has diverged from the local clone %s; nothing was written. Inspect it by hand.'
                           % (branch, clone))


def unpushed(clone, branch):
    """True when an earlier run committed but its push failed."""
    if git('rev-parse', '--verify', '--quiet', 'HEAD', cwd=clone, check=False).returncode:
        return False
    if git('rev-parse', '--verify', '--quiet', 'refs/remotes/origin/' + branch, cwd=clone, check=False).returncode:
        return True
    return git('rev-list', '--count', 'origin/%s..HEAD' % branch, cwd=clone).stdout.strip() != '0'


def publish_once(monitor_dir, repo, *, branch='gh-pages', clone=None, remote_url=None, redact=True):
    if not REPO.match(repo):
        raise PublishError('--repo must look like OWNER/NAME')
    if not BRANCH.match(branch) or '..' in branch:
        raise PublishError('Unsafe branch name')
    remote_url = remote_url or 'https://github.com/%s.git' % repo
    clone = Path(clone) if clone else ROOT / 'deploy/activation/dashboard-pages' / repo.replace('/', '__')
    refuse_main_repository(repo, remote_url)
    prepare(remote_url, branch, clone)
    summary = build(monitor_dir, clone, redact=redact)['summary']
    git('add', '--', *OUTPUTS, cwd=clone)
    result = dict(repo=repo, branch=branch, as_of_utc=summary['as_of_utc'], redacted=redact, changed=False)
    if git('diff', '--cached', '--quiet', cwd=clone, check=False).returncode == 0:
        if not unpushed(clone, branch):
            return result
    else:
        git('commit', '--quiet', '-m', 'dashboard: data as of %s' % (summary['as_of_utc'] or 'no data'), cwd=clone)
        result['changed'] = True
    git('push', '--quiet', 'origin', 'HEAD:refs/heads/' + branch, cwd=clone)
    result['commit'] = git('rev-parse', 'HEAD', cwd=clone).stdout.strip()
    return result


def pages_url(repo):
    owner, name = repo.split('/')
    user_site = name.lower() == owner.lower() + '.github.io'
    return 'https://%s.github.io/%s' % (owner.lower(), '' if user_site else name + '/')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--monitor-dir', required=True, help='chain-monitor output folder (LARP_MONITOR_DIR)')
    ap.add_argument('--repo', required=True, help='OWNER/NAME of the repository that serves the Pages site')
    ap.add_argument('--branch', default='gh-pages', help='Pages source branch (default gh-pages)')
    ap.add_argument('--clone', help='local clone to use (default deploy/activation/dashboard-pages/OWNER__NAME)')
    ap.add_argument('--remote-url', help='push URL if not https://github.com/OWNER/NAME.git')
    ap.add_argument('--loop', type=int, metavar='SECONDS', help='keep publishing every SECONDS (minimum %d)' % MIN_LOOP)
    ap.add_argument('--full', action='store_true',
                    help='keep transaction hashes, blocks, nonces and alert details (only for a private site)')
    args = ap.parse_args()
    if args.loop is not None and args.loop < MIN_LOOP:
        ap.error('--loop must be at least %d s (GitHub allows about 10 Pages builds an hour)' % MIN_LOOP)
    if shutil.which('git') is None:
        ap.error('git is not installed')
    print(json.dumps(dict(pages_url=pages_url(args.repo))), flush=True)
    while True:
        try:
            out = publish_once(args.monitor_dir, args.repo, branch=args.branch, clone=args.clone,
                               remote_url=args.remote_url, redact=not args.full)
        except (PublishError, OSError, ValueError) as e:
            out = dict(publish_error=type(e).__name__, detail=str(e)[:300])
            if args.loop is None:
                print(json.dumps(out, sort_keys=True), flush=True)
                sys.exit(1)
        print(json.dumps(out, sort_keys=True), flush=True)
        if args.loop is None:
            return
        time.sleep(args.loop)


if __name__ == '__main__':
    main()

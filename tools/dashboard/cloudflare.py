"""Refresh the dashboard and post it to Cloudflare Pages (IDEA-091, Keith's always-on computer).

  CLOUDFLARE_API_TOKEN=... CLOUDFLARE_ACCOUNT_ID=... AWS_PROFILE=larp \\
      python -m tools.dashboard.cloudflare --work ~/larp-dashboard --project larp-dashboard

One run: `tools.dashboard.refresh` (chain-monitor poll, incremental read-only decisions export over SSM, redacted
build), then `wrangler pages deploy` of exactly index.html, data.json and _headers to the project's production branch.
Cloudflare Access must protect the project's hostnames before the first deploy (docs/build/DASHBOARD.md). Run it from
cron or launchd every hour; an overlapping run exits without doing anything. A failed refresh deploys nothing, so the
last good page stays. The Cloudflare token comes only from the environment and is never printed.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from tools.dashboard import refresh

WRANGLER = ('npx', '--yes', 'wrangler@4.145.0')  # exact version, published 2026-09-30
PROJECT = re.compile(r'^[a-z0-9][a-z0-9-]{0,57}$')
HEADERS = '/*\n  Cache-Control: no-store\n  X-Robots-Tag: noindex, nofollow\n  Referrer-Policy: no-referrer\n'
PAGE_FILES = ('index.html', 'data.json')
CREDENTIALS = ('CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ACCOUNT_ID')


class Busy(Exception):
    pass


def lock(work):
    """A non-blocking lock on <work>/.lock, held for the run; another run gets Busy."""
    work.mkdir(parents=True, exist_ok=True)
    handle = open(work / '.lock', 'w')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise Busy() from None
    return handle


def stage(work):
    """<work>/deploy holds only what is published: the redacted page, its data and the headers file."""
    deploy = work / 'deploy'
    shutil.rmtree(deploy, ignore_errors=True)
    deploy.mkdir()
    for name in PAGE_FILES:
        shutil.copyfile(work / 'site' / name, deploy / name)
    (deploy / '_headers').write_text(HEADERS)
    return deploy


def deploy(folder, project, wrangler=WRANGLER):
    command = [*wrangler, 'pages', 'deploy', str(folder), '--project-name', project, '--branch', 'main',
               '--commit-dirty=true']
    done = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if done.returncode:
        token = os.environ.get('CLOUDFLARE_API_TOKEN') or '\0'
        raise RuntimeError('wrangler pages deploy failed: ' + done.stderr.replace(token, '<token>').strip()[-300:])
    return done.stdout.strip().splitlines()[-1:] or ['']


def run(work, project, *, settings=None, wrangler=WRANGLER, refresher=refresh.refresh):
    missing = [k for k in CREDENTIALS if not os.environ.get(k)]
    if missing:
        raise SystemExit('Set ' + ' and '.join(missing) + ' (a Cloudflare API token limited to Pages edit)')
    if not PROJECT.match(project):
        raise SystemExit('--project must be a Cloudflare Pages project name')
    work = Path(work).expanduser()
    try:
        held = lock(work)
    except Busy:
        return dict(skipped='another run is in progress')
    try:
        summary = refresher(work, settings=settings)  # raises on failure: nothing is deployed
        result = deploy(stage(work), project, wrangler)
        return dict(as_of_utc=summary['as_of_utc'], rounds=summary['rounds'], export_error=summary.get('export_error'),
                    chain=summary['chain'], deployed=result[0])
    finally:
        held.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--work', required=True, help='working folder (monitor state, site); keep it on this machine')
    ap.add_argument('--project', required=True, help='Cloudflare Pages project name')
    ap.add_argument('--wallet', help='wallet to watch (default: the dev rehearsal wallet in the RC7 monitor)')
    ap.add_argument('--start-nonce', type=int, help="the wallet's nonce at the run's start")
    ap.add_argument('--start-usdt', type=float, help='opening equity in USDT, excluding BNB')
    args = ap.parse_args()
    if args.wallet and not re.fullmatch(r'0x[0-9a-fA-F]{40}', args.wallet):
        ap.error('--wallet must be a 0x address')
    settings = {k: v for k, v in dict(wallet=args.wallet, start_nonce=args.start_nonce, start_usdt=args.start_usdt).items()
                if v is not None}
    print(json.dumps(run(args.work, args.project, settings=settings), sort_keys=True), flush=True)


if __name__ == '__main__':
    sys.exit(main())

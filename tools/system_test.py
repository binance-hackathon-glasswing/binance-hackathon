#!/usr/bin/env python3
"""IDEA-043: reproducible credential-free system checks on a pushed testing branch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SYSTEM_CASES = [
    'tests/integration/test_cross_component.py',
    'tests/integration/test_acceptance.py',
    'tests/integration/test_service_system.py',
    'tests/integration/test_published_red_flag_policy.py',
    'tests/integration/test_live_replay.py',
    'tests/integration/test_settlement.py',
    'tests/integration/test_cadence.py',
    'tests/integration/test_evidence_pipeline.py',
    'tests/execution/test_postgres_execution.py',
    'tests/execution/test_runtime_consumer.py',
    'tests/audit/test_round_logging.py',
    'tests/runtime/test_supervision.py',
    'tests/runtime/test_anchors_roles.py',
    'tests/runtime/test_manifest_prompts.py',
    'tests/runtime/test_review_boundaries.py',
]
GUARD = '''import socket
_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
def _check(address):
    if isinstance(address, tuple) and address[0] not in ('127.0.0.1', 'localhost', '::1'):
        raise OSError('System tests permit local fixture network only')
def _connect(self, address):
    _check(address)
    return _original_connect(self, address)
def _connect_ex(self, address):
    _check(address)
    return _original_connect_ex(self, address)
socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex
'''


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--system-only', action='store_true')
    parser.add_argument('--output-dir')
    parser.add_argument('--linux-ci-run', help='Successful runtime CI run for platforms without bubblewrap')
    args = parser.parse_args()
    branch, commit = git('branch', '--show-current'), git('rev-parse', 'HEAD')
    allowed_branch = (branch.startswith('codex/system-testing-')
                      or re.fullmatch(r'review/final-[a-d]-[0-9]{8}', branch) is not None)
    if not allowed_branch or git('status', '--porcelain'):
        parser.error('Use a clean codex/system-testing-* or review/final-[a-d]-<yyyymmdd> branch')
    if git('rev-parse', '--verify', 'origin/' + branch) != commit:
        parser.error('Commit and push the tested head first')
    dsn = os.environ.get('LARP_TEST_DATABASE_URL', '')
    db = urlsplit(dsn)
    if (db.scheme not in ('postgresql', 'postgres') or db.hostname not in ('127.0.0.1', 'localhost', '::1')
            or not db.path.lstrip('/').startswith('larp_test')
            or os.environ.get('LARP_SYSTEM_TEST_DISPOSABLE') != '1'):
        parser.error('Set a disposable local larp_test database URL and LARP_SYSTEM_TEST_DISPOSABLE=1')
    output = Path(args.output_dir).resolve() if args.output_dir else Path(tempfile.mkdtemp(prefix='larp-system-'))
    if output == ROOT or ROOT in output.parents:
        parser.error('Write raw test artifacts outside the repository')
    output.mkdir(parents=True, exist_ok=True)
    guard = output / 'guard'; guard.mkdir(exist_ok=True)
    (guard / 'sitecustomize.py').write_text(GUARD)
    env = {k: v for k, v in os.environ.items() if k in (
        'PATH', 'HOME', 'TMPDIR', 'LANG', 'LC_ALL', 'SYSTEMROOT', 'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH')}
    env.update(LARP_TEST_DATABASE_URL=dsn, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               PYTHONPATH=str(guard) + os.pathsep + str(ROOT), AWS_EC2_METADATA_DISABLED='true')
    pytest = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider']
    phases = [('system', pytest + SYSTEM_CASES)]
    if not args.system_only:
        phases.append(('full_suite', pytest))
    linux_evidence = None
    if sys.platform == 'linux' and shutil.which('bwrap'):
        phases.append(('offline_demo', [sys.executable, '-m', 'larp.runtime.demo']))
    elif args.linux_ci_run:
        if not args.linux_ci_run.isdigit():
            parser.error('Linux CI run ID must be numeric')
        ci = json.loads(subprocess.check_output(['gh', 'run', 'view', args.linux_ci_run,
            '--repo', 'binance-hackathon-glasswing/binance-hackathon',
            '--json', 'headSha,status,conclusion,jobs,url'], text=True))
        runtime = next((j for j in ci['jobs'] if j['name'] == 'runtime'), {})
        demo = next((s for s in runtime.get('steps', []) if 'python -m larp.runtime.demo' in s['name']), {})
        paths = ['larp', 'config', 'deploy', 'migrations', '.github', 'requirements.lock', 'requirements.in']
        same_runtime = subprocess.run(['git', 'diff', '--quiet', ci['headSha'], commit, '--', *paths], cwd=ROOT).returncode == 0
        if (ci['status'] != 'completed' or ci['conclusion'] != 'success' or runtime.get('conclusion') != 'success'
                or demo.get('conclusion') != 'success' or not same_runtime):
            parser.error('CI evidence must prove this exact runtime tree and its Linux demo passed')
        linux_evidence = dict(name='offline_demo', status='PASS', execution='GITHUB_ACTIONS_LINUX',
                              ci_run=args.linux_ci_run, tested_commit=ci['headSha'], url=ci['url'],
                              proof='Successful runtime/demo steps and identical runtime/config/deploy/migration tree')
    else:
        parser.error('Linux bubblewrap unavailable; supply --linux-ci-run for a verified equivalent runtime tree')
    report = dict(schema='SystemTestReport.v1', branch=branch, commit=commit, synthetic=True,
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Disposable PostgreSQL; local fake HTTP/EDGAR/venue/chain/signing; no production credentials',
                  checks=[])
    for name, command in phases:
        log = output / (name + '.log')
        started=time.monotonic()
        with log.open('wb') as stream:
            run = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        raw = log.read_bytes(); tail = raw.decode('utf-8', 'replace')[-6000:]
        counts = {key: int(match.group(1)) for key, pattern in (
            ('passed', r'(\d+) passed'), ('skipped', r'(\d+) skipped'),
            ('subtests_passed', r'(\d+) subtests passed')) if (match := re.search(pattern, tail))}
        check = dict(name=name, status='PASS' if run.returncode == 0 else 'FAIL', exit_code=run.returncode,
                     elapsed_seconds=round(time.monotonic()-started,3),
                     log_sha256=hashlib.sha256(raw).hexdigest(), **counts)
        report['checks'].append(check)
        print(json.dumps(check), flush=True)
    if linux_evidence is not None:
        report['checks'].append(linux_evidence)
        print(json.dumps(linux_evidence), flush=True)
    report['status'] = 'PASS' if all(c['status'] == 'PASS' for c in report['checks']) else 'FAIL'
    report['completed_utc']=datetime.now(timezone.utc).isoformat()
    (output / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print('Report: ' + str(output / 'report.json'))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

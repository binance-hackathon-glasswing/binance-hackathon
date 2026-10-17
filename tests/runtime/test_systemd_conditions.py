"""IDEA-047 R13: actual systemd startup/refusal/restart semantics, enabled on the disposable Linux CI runner."""
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

from larp.contracts import Document
from larp.runtime.preflight import release_files
from tests.host_support import ROOT, synthetic_release
from tests.runtime.test_host_units import directives, value


@unittest.skipUnless(os.environ.get('LARP_TEST_SYSTEMD') == '1', 'Disposable systemd test runner not enabled')
class UnitConditions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root, self.manifest = synthetic_release(self.base, {s: b'{}' for s in ('signer', 'execution', 'uploader')})
        for name in ('requirements-runtime.lock', 'requirements-aws.lock', 'requirements-signer.lock'):
            target = self.root / 'deploy' / name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes((ROOT / 'deploy' / name).read_bytes())
        manifest = Document(self.manifest.read_bytes()).read()
        manifest['files'] = {p: hashlib.sha256((self.root / p).read_bytes()).hexdigest()
                             for p in release_files(self.root)}
        manifest['runtime_config_sha256'] = hashlib.sha256(b'{}').hexdigest()
        self.manifest.write_bytes(Document.from_dict(manifest).payload)
        for service in ('runtime', 'signer', 'execution', 'uploader'):
            (self.base / (service + '.json')).write_bytes(b'{}')

    def command(self, *args, input=None):
        return subprocess.run(['sudo', '-n', *args], input=input, capture_output=True, text=True,
                              timeout=15, check=True).stdout

    def launch_command(self, unit, marker, exit_code):
        argv = shlex.split(value(directives(unit), 'ExecStart')[0])
        argv[0] = sys.executable
        replacements = {'/etc/larp/release.json': str(self.manifest), '/opt/larp/current': str(self.root)}
        for service in ('runtime', 'signer', 'execution', 'uploader'):
            path = '/etc/larp/' + service + '.json'
            replacements[path] = str(self.base / (service + '.json'))
            replacements[service + '=' + path] = service + '=' + replacements[path]
        # Use the real launch/preflight command, replacing only the actual service with an inert Python fixture.
        argv = argv[:argv.index('--') + 1]
        argv += ['-c', 'from pathlib import Path; Path(' + repr(str(marker))
                 + ').touch(); raise SystemExit(' + str(exit_code) + ')']
        return ' '.join(shlex.quote(replacements.get(arg, arg)) for arg in argv)

    def start(self, unit, exit_code=1):
        name = 'larp-review-' + uuid.uuid4().hex
        path = '/run/systemd/system/' + name + '.service'
        marker = self.base / (name + '.started')
        def cleanup():
            subprocess.run(['sudo', '-n', 'systemctl', 'stop', name], capture_output=True, timeout=15)
            subprocess.run(['sudo', '-n', 'rm', '-f', path], capture_output=True, timeout=15)
            subprocess.run(['sudo', '-n', 'systemctl', 'daemon-reload'], capture_output=True, timeout=15)
            subprocess.run(['sudo', '-n', 'systemctl', 'reset-failed', name], capture_output=True, timeout=15)
        self.addCleanup(cleanup)
        fixture = ('[Unit]\nStartLimitIntervalSec=0\n[Service]\nType=simple\nWorkingDirectory=' + str(ROOT)
                   + '\nExecStart=' + self.launch_command(unit, marker, exit_code)
                   + '\nRestartPreventExitStatus=' + value(directives(unit), 'RestartPreventExitStatus')[0]
                   + '\nRestart=always\nRestartSec=100ms\n')
        # Keep a named fixture unit until cleanup, so inspection never depends on transient-unit collection.
        self.command('tee', path, input=fixture)
        self.command('systemctl', 'daemon-reload')
        self.command('systemctl', 'start', '--no-block', name)
        return name, marker

    def state(self, name):
        output = self.command('systemctl', 'show', name, '--property=ActiveState', '--property=NRestarts',
                              '--property=Result', '--property=ExecMainStatus')
        return dict(line.split('=', 1) for line in output.splitlines())

    def test_r13_changed_release_never_runs_or_restarts_the_main_process(self):
        (self.root / 'docs/proposal/proposal_answers.md').write_text('changed after manifesting')
        for unit in ('larp-runtime', 'larp-evidence', 'larp-signer', 'larp-execution', 'larp-uploader'):
            with self.subTest(unit=unit):
                name, marker = self.start(unit)
                deadline = time.monotonic() + 8
                state = self.state(name)
                while state['ActiveState'] != 'failed' and time.monotonic() < deadline:
                    time.sleep(0.05)
                    state = self.state(name)
                self.assertEqual(state['ActiveState'], 'failed', state)
                self.assertEqual(state['ExecMainStatus'], '4')
                time.sleep(0.3)
                self.assertEqual(self.state(name)['NRestarts'], '0')
                self.assertFalse(marker.exists())

    def test_r13_valid_condition_keeps_main_process_failure_recovery(self):
        name, marker = self.start('larp-evidence')
        deadline = time.monotonic() + 8
        state = self.state(name)
        while int(state['NRestarts']) == 0 and time.monotonic() < deadline:
            time.sleep(0.05)
            state = self.state(name)
        self.assertTrue(marker.exists(), state)
        self.assertGreater(int(state['NRestarts']), 0, state)

    def test_r13_clean_evidence_cycle_still_restarts(self):
        name, marker = self.start('larp-evidence', exit_code=0)
        deadline = time.monotonic() + 8
        state = self.state(name)
        while int(state['NRestarts']) == 0 and time.monotonic() < deadline:
            time.sleep(0.05)
            state = self.state(name)
        self.assertTrue(marker.exists(), state)
        self.assertGreater(int(state['NRestarts']), 0, state)


@unittest.skipUnless(os.environ.get('LARP_TEST_SYSTEMD') == '1' and os.environ.get('LARP_TEST_DATABASE_URL'),
                     'Disposable systemd runner and PostgreSQL required (WR-T7/8 NOT RUN)')
class RuntimeUnit(unittest.TestCase):
    """WR-T7/8: preserve every production sandbox directive, with real preflight and service lifecycle."""
    command = UnitConditions.command
    state = UnitConditions.state

    def setUp(self):
        import json
        import shutil
        import psycopg
        from psycopg.conninfo import make_conninfo
        from larp.runtime.service import activate_run, init_run
        from larp.storage.postgres import PostgresStore
        from tests.integration.test_evidence_pipeline import pipeline_ledger

        self.state_dir = Path('/var/lib/larp-runtime')
        if self.state_dir.exists() or self.state_dir.is_symlink():
            self.skipTest('/var/lib/larp-runtime already exists; this is not a disposable runner')
        self.name = 'larp-wrt-' + uuid.uuid4().hex
        # /tmp is hidden by PrivateTmp, and /home by ProtectHome. Real service paths stay unchanged.
        self.base = Path('/var/lib') / self.name
        self.command('install', '-d', '-m', '0755', '-o', str(os.getuid()), '-g', str(os.getgid()), str(self.base))
        self.addCleanup(lambda: self.command('rm', '-rf', str(self.base)))
        for group in ('larp-runtime', 'larp-evidence'):
            if subprocess.run(['getent', 'group', group], capture_output=True).returncode:
                self.command('groupadd', '--system', group)
                def remove_group(g=group):
                    if subprocess.run(['getent', 'group', g], capture_output=True).returncode == 0:
                        self.command('groupdel', g)
                self.addCleanup(remove_group)
        if subprocess.run(['id', '-u', 'larp-runtime'], capture_output=True).returncode:
            self.command('useradd', '--system', '--gid', 'larp-runtime', '--no-create-home',
                         '--shell', '/usr/sbin/nologin', 'larp-runtime')
            self.addCleanup(lambda: self.command('userdel', 'larp-runtime'))
        self.addCleanup(lambda: self.command('rm', '-rf', str(self.state_dir)))

        self.root, self.manifest = synthetic_release(self.base)
        for relative in release_files(ROOT):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        fixture = self.base / 'runtime_fixture.py'
        shutil.copyfile(ROOT / 'tests/runtime/fixtures/systemd_runtime.py', fixture)
        self.fixture = fixture
        ca = self.base / 'rds-ca.pem'
        ca.write_bytes(b'Synthetic TLS pin; open_store uses the disposable PostgreSQL instead of IAM.\n')
        self.config = json.loads((ROOT / 'config/runtime/runtime.example.json').read_text())
        self.config.update(run_id=self.name, build_id='b' * 40, wallet_address='0x' + '4' * 40,
                           database_host='synthetic.invalid', database_ca_file=str(ca),
                           database_ca_sha256=hashlib.sha256(ca.read_bytes()).hexdigest())
        self.config['driver'].update(cadence_ms=3_600_000, day_roll_window_ms=15 * 60 * 1000,
                                     strategy_profile_sha256='0' * 64)
        initial = self.base / 'initial-state.json'
        ledger = dict(pipeline_ledger(), run_id=self.name, wallet_id=self.config['wallet_address'], mode='LIVE')
        initial.write_bytes(Document.from_dict(ledger).payload)
        self.config.update(initial_state_file=str(initial), initial_state_sha256=hashlib.sha256(initial.read_bytes()).hexdigest())
        self.config_path = self.base / 'runtime.json'
        self.config_path.write_bytes(Document.from_dict(self.config).payload)
        manifest = Document(self.manifest.read_bytes()).read()
        manifest['files'] = {p: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for p in release_files(self.root)}
        manifest['runtime_config_sha256'] = hashlib.sha256(self.config_path.read_bytes()).hexdigest()
        self.manifest.write_bytes(Document.from_dict(manifest).payload)
        # Traverse/read permissions for the non-root runtime account, regardless of the invoking user's umask.
        for path in self.base.rglob('*'):
            path.chmod(0o755 if path.is_dir() else 0o644)

        dsn = os.environ['LARP_TEST_DATABASE_URL']
        self.schema = 'wrt_' + uuid.uuid4().hex
        with psycopg.connect(dsn) as db:
            db.execute('CREATE SCHEMA ' + self.schema)
        def drop_schema():
            with psycopg.connect(dsn) as db:
                db.execute('DROP SCHEMA ' + self.schema + ' CASCADE')
        self.addCleanup(drop_schema)
        connection = self.base / 'connection.txt'
        connection.write_text(make_conninfo(dsn, options='-c search_path=' + self.schema))
        connection.chmod(0o644)  # disposable test DB only; no hosted credentials
        self.connection = connection
        self.store = PostgresStore(connection.read_text())
        self.store.migrate()
        init_run(self.config, self.store)
        activate_run(self.config, self.store, Document(self.manifest.read_bytes()), reviewer='synthetic WR-T7/8',
                     review_ref='IDEA-049-D WR-T', now_ms=time.time_ns() // 1_000_000)

    def start(self, *, state_directory=True):
        path = '/run/systemd/system/' + self.name + '.service'
        def cleanup():
            subprocess.run(['sudo', '-n', 'systemctl', 'stop', self.name], capture_output=True, timeout=15)
            self.command('rm', '-f', path)
            self.command('systemctl', 'daemon-reload')
            subprocess.run(['sudo', '-n', 'systemctl', 'reset-failed', self.name], capture_output=True, timeout=15)
        self.addCleanup(cleanup)
        text = (ROOT / 'deploy/systemd/larp-runtime.service').read_text()
        argv = shlex.split(value(directives('larp-runtime'), 'ExecStart')[0])
        argv[0] = sys.executable
        argv = argv[:argv.index('--') + 1] + [str(self.fixture), str(self.connection), str(self.config_path),
                                              str(self.manifest), str(self.root)]
        replacements = {'/etc/larp/release.json': str(self.manifest), '/etc/larp/runtime.json': str(self.config_path),
                        '/opt/larp/current': str(self.root)}
        lines = []
        for line in text.splitlines():
            if not state_directory and line.startswith(('StateDirectory=', 'StateDirectoryMode=')):
                continue
            if line.startswith('ExecStart='):
                line = 'ExecStart=' + ' '.join(shlex.quote(replacements.get(a, a)) for a in argv)
            else:
                for old, new in replacements.items():
                    line = line.replace(old, new)
            lines.append(line)
        self.command('tee', path, input='\n'.join(lines) + '\n')
        self.command('systemctl', 'daemon-reload')
        self.command('systemctl', 'start', '--no-block', self.name)

    def sessions(self):
        with self.store.transaction() as db:
            return db.execute('SELECT build_id,ended_ms FROM process_sessions WHERE run_id=%s', (self.name,)).fetchall()

    def wait_until(self, predicate):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.1)
        self.fail(str(self.state(self.name)) + '\n' + self.command('journalctl', '-u', self.name, '--no-pager', '-n', '30'))

    def test_wr_t7_the_runtime_unit_gets_past_directory_binding(self):
        import pwd
        self.start()
        cycle = self.state_dir / 'cycle'
        self.wait_until(lambda: subprocess.run(['sudo', '-n', 'test', '-f', str(cycle)],
                                              capture_output=True).returncode == 0)
        uid = pwd.getpwnam('larp-runtime').pw_uid
        for directory in ('ai-seeds', 'nonce'):
            marker = self.state_dir / directory / '.larp-wallet'
            self.assertEqual(self.command('cat', str(marker)).strip(), self.config['wallet_address'])
            self.assertEqual(int(self.command('stat', '-c', '%u', str(marker)).strip()), uid)
        self.assertEqual(self.sessions(), [(self.config['build_id'], None)])
        self.assertEqual(self.state(self.name)['ActiveState'], 'active')
        self.assertEqual(self.state(self.name)['NRestarts'], '0')
        self.command('systemctl', 'stop', self.name)
        self.assertEqual(self.state(self.name)['ExecMainStatus'], '0')
        self.assertIsNotNone(self.sessions()[0][1])

    def test_wr_t8_without_its_state_directory_the_start_is_refused(self):
        self.start(state_directory=False)
        self.wait_until(lambda: self.state(self.name)['ActiveState'] == 'failed')
        state = self.state(self.name)
        self.assertEqual((state['ExecMainStatus'], state['NRestarts']), ('4', '0'))
        self.assertFalse(self.state_dir.exists())
        self.assertEqual(self.sessions(), [])
        self.assertIn('LIVE_START_REFUSED', self.command('journalctl', '-u', self.name, '--no-pager'))

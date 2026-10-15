"""IDEA-047 R13 and IDEA-049 WR-59 (#59): actual systemd semantics, enabled on the disposable Linux CI runner."""
import hashlib
import json
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
from tests.runtime.test_host_units import UNITS, directives, value


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


ADDRESS = '0x' + '5' * 40  # synthetic; no wallet, key or secret is involved
STATE = Path('/var/lib/larp-runtime')
# The fixture runs once and reports through its exit status; everything else in [Service] is the real unit's.
NOT_COPIED = ('ExecStart', 'Type', 'Restart', 'RestartSec', 'RestartPreventExitStatus')
BIND = """import json
from pathlib import Path
from larp.runtime.live import LiveStartRefused, check_live_start
c = json.loads(Path('/opt/larp/current/config/runtime/runtime.example.json').read_text(encoding='utf-8'))
try:
    check_live_start(mode=c['mode'], ports={'market': object(), 'chain': object()},
                     secrets={'AI_SEEDS_ADDRESS': ADDRESS, 'BINANCE_API_KEY': 'synthetic',
                              'BINANCE_SECRET_KEY': 'synthetic'},
                     wallet_address=ADDRESS, run_wallet=ADDRESS, ai_seeds_dir=c['ai_seeds_dir'],
                     nonce_dir=c['nonce_dir'])
except LiveStartRefused as refused:
    print('LIVE_START_REFUSED', refused, flush=True)
    raise SystemExit(4)
print('BOUND', flush=True)
"""


def service_directives(unit, drop=()):
    """The unit's [Service] lines, without NOT_COPIED and `drop`."""
    section, lines = None, []
    for line in (UNITS / (unit + '.service')).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('['):
            section = line
        elif section == '[Service]' and line.split('=', 1)[0] not in NOT_COPIED + tuple(drop):
            lines.append(line)
    return lines


@unittest.skipUnless(os.environ.get('LARP_TEST_SYSTEMD') == '1', 'Disposable systemd test runner not enabled')
class RuntimeStateDirectories(unittest.TestCase):
    """WR-59: the runtime unit's own sandbox binds the example config's ai-seeds and nonce directories (#59)."""

    def setUp(self):
        if any(Path(sys.executable).resolve().is_relative_to(p) for p in ('/home', '/root', '/tmp', '/var/tmp')):
            self.skipTest('The interpreter must be outside the paths the unit hides (ProtectHome, PrivateTmp)')
        if subprocess.run(['sudo', '-n', 'test', '-e', str(STATE)], timeout=15).returncode == 0:
            self.skipTest(str(STATE) + ' exists: not a disposable runner')
        self.addCleanup(self.sudo, 'rm', '-rf', str(STATE))
        for user in ('larp-runtime', 'larp-evidence'):  # as deploy/host/provision.sh creates them
            if subprocess.run(['id', '-u', user], capture_output=True, timeout=15).returncode:
                self.sudo('useradd', '--system', '--user-group', '--no-create-home', '--home-dir', '/nonexistent',
                          '--shell', '/usr/sbin/nologin', user)
                self.addCleanup(self.sudo, 'userdel', user)
        self.stage = Path('/run/larp-review-' + uuid.uuid4().hex)
        self.addCleanup(self.sudo, 'rm', '-rf', str(self.stage))
        current = self.stage / 'current'
        self.sudo('mkdir', '-p', str(current / 'config'))
        self.sudo('cp', '-r', str(ROOT / 'larp'), str(current / 'larp'))
        self.sudo('cp', '-r', str(ROOT / 'config' / 'runtime'), str(current / 'config' / 'runtime'))
        self.sudo('tee', str(current / 'larp_review_bind.py'), input='ADDRESS = ' + repr(ADDRESS) + '\n' + BIND)
        self.sudo('chmod', '-R', 'a+rX', str(self.stage))

    def sudo(self, *args, input=None):
        return subprocess.run(['sudo', '-n', *args], input=input, capture_output=True, text=True, timeout=15,
                              check=True).stdout

    def run_unit(self, drop=()):
        name = 'larp-review-' + uuid.uuid4().hex
        path = '/run/systemd/system/' + name + '.service'
        def cleanup():
            subprocess.run(['sudo', '-n', 'systemctl', 'stop', name], capture_output=True, timeout=15)
            subprocess.run(['sudo', '-n', 'rm', '-f', path], capture_output=True, timeout=15)
            subprocess.run(['sudo', '-n', 'systemctl', 'daemon-reload'], capture_output=True, timeout=15)
            subprocess.run(['sudo', '-n', 'systemctl', 'reset-failed', name], capture_output=True, timeout=15)
        self.addCleanup(cleanup)
        config = self.stage / 'current' / 'config' / 'runtime' / 'runtime.example.json'
        fixture = ('[Unit]\nStartLimitIntervalSec=0\nConditionPathExists=' + str(config) + '\n[Service]\n'
                   + '\n'.join(service_directives('larp-runtime', drop))
                   # RemainAfterExit keeps a finished unit's status: otherwise systemd unloads it, and `show`
                   # reports defaults (ConditionResult=no, ExecMainStatus=0) instead of what ran.
                   + '\nType=oneshot\nRemainAfterExit=yes\n'
                   # Production installs the release at /opt/larp/current; this is the same path, read-only.
                   + 'BindReadOnlyPaths=' + str(self.stage / 'current') + ':/opt/larp/current\n'
                   + 'ExecStart=' + sys.executable + ' /opt/larp/current/larp_review_bind.py\n')
        self.sudo('tee', path, input=fixture)
        self.sudo('systemctl', 'daemon-reload')
        subprocess.run(['sudo', '-n', 'systemctl', 'start', name], capture_output=True, timeout=60)
        output = self.sudo('systemctl', 'show', name, '--property=Result', '--property=ExecMainStatus',
                           '--property=ConditionResult', '--property=ActiveState', '--property=SubState')
        return dict(line.split('=', 1) for line in output.splitlines())

    def test_wr59_the_unit_binds_the_example_directories_in_its_state_directory(self):
        config = json.loads((ROOT / 'config' / 'runtime' / 'runtime.example.json').read_text(encoding='utf-8'))
        state = self.run_unit()
        self.assertEqual((state['ConditionResult'], state['ExecMainStatus'], state['Result'], state['ActiveState'],
                          state['SubState']), ('yes', '0', 'success', 'active', 'exited'), state)
        self.assertEqual(self.sudo('stat', '-c', '%U %a', str(STATE)).split(), ['larp-runtime', '700'])
        for key in ('ai_seeds_dir', 'nonce_dir'):
            with self.subTest(directory=key):
                directory = Path(config[key])
                self.assertTrue(directory.is_relative_to(STATE))
                self.assertEqual(self.sudo('stat', '-c', '%U', str(directory)).strip(), 'larp-runtime')
                self.assertEqual(self.sudo('cat', str(directory / '.larp-wallet')), ADDRESS + '\n')

    def test_wr59_without_the_state_directory_the_start_is_refused(self):
        # The #59 defect: ProtectSystem=strict leaves /var/lib read-only, so binding fails (exit 4, no restart).
        state = self.run_unit(drop=('StateDirectory', 'StateDirectoryMode'))
        self.assertEqual((state['ConditionResult'], state['ExecMainStatus'], state['ActiveState']),
                         ('yes', '4', 'failed'), state)
        self.assertNotEqual(subprocess.run(['sudo', '-n', 'test', '-e', str(STATE)], timeout=15).returncode, 0)

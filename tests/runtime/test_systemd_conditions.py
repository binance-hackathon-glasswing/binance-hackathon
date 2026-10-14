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

    def condition(self, unit):
        argv = shlex.split(value(directives(unit), 'ExecCondition')[0])
        argv[0] = sys.executable
        replacements = {'/etc/larp/release.json': str(self.manifest), '/opt/larp/current': str(self.root)}
        for service in ('runtime', 'signer', 'execution', 'uploader'):
            path = '/etc/larp/' + service + '.json'
            replacements[path] = str(self.base / (service + '.json'))
            replacements[service + '=' + path] = service + '=' + replacements[path]
        return ' '.join(shlex.quote(replacements.get(arg, arg)) for arg in argv)

    def start(self, unit):
        name = 'larp-review-' + uuid.uuid4().hex
        path = '/run/systemd/system/' + name + '.service'
        marker = self.base / (name + '.started')
        def cleanup():
            subprocess.run(['sudo', '-n', 'systemctl', 'stop', name], capture_output=True, timeout=15)
            subprocess.run(['sudo', '-n', 'rm', '-f', path], capture_output=True, timeout=15)
            subprocess.run(['sudo', '-n', 'systemctl', 'daemon-reload'], capture_output=True, timeout=15)
            subprocess.run(['sudo', '-n', 'systemctl', 'reset-failed', name], capture_output=True, timeout=15)
        self.addCleanup(cleanup)
        command = 'touch ' + shlex.quote(str(marker)) + '; exit 1'
        fixture = ('[Unit]\nStartLimitIntervalSec=0\n[Service]\nType=simple\nWorkingDirectory=' + str(ROOT)
                   + '\nExecCondition=' + self.condition(unit) + '\nExecStart=/bin/sh -c '
                   + shlex.quote(command) + '\nRestart=always\nRestartSec=100ms\n')
        # Keep a named fixture unit until cleanup, so systemd cannot garbage-collect a skipped transient unit
        # before we inspect the exit status and restart counter.
        self.command('tee', path, input=fixture)
        self.command('systemctl', 'daemon-reload')
        self.command('systemctl', 'start', '--no-block', name)
        return name, marker

    def state(self, name):
        output = self.command('systemctl', 'show', name, '--property=ActiveState', '--property=NRestarts',
                              '--property=Result', '--property=ExecCondition')
        return dict(line.split('=', 1) for line in output.splitlines())

    def test_r13_changed_release_never_runs_or_restarts_the_main_process(self):
        (self.root / 'docs/proposal/proposal_answers.md').write_text('changed after manifesting')
        for unit in ('larp-runtime', 'larp-evidence', 'larp-signer', 'larp-execution', 'larp-uploader'):
            with self.subTest(unit=unit):
                name, marker = self.start(unit)
                deadline = time.monotonic() + 8
                state = self.state(name)
                while state['ActiveState'] != 'inactive' and time.monotonic() < deadline:
                    time.sleep(0.05)
                    state = self.state(name)
                self.assertEqual(state['ActiveState'], 'inactive', state)
                self.assertIn('status=4', state['ExecCondition'])
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

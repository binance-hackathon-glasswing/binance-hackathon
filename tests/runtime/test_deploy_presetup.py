"""IDEA-051: deployment pre-setup tools (tools/deploy/), on synthetic Terraform outputs and a fake `aws`."""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from larp.audit.service import validate_config as validate_uploader

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'deploy'))
import render_host_configs as render  # noqa: E402

ACCOUNT = '000000000000'
WALLET = '0xAbCdEf0123456789aBcDeF0123456789AbCdEf01'


def terraform_output(account=ACCOUNT, name='larp-dev', services=('runtime', 'uploader', 'evidence')):
    arn = 'arn:aws:secretsmanager:ap-southeast-2:{}:secret:{}/{}-AbC123'
    values = {
        'archive_bucket': f'larp-{account}-dev-archive',
        'archive_kms_key': f'arn:aws:kms:ap-southeast-2:{account}:key/synthetic',
        'artifact_bucket': f'larp-{account}-dev-artifacts',
        'database_host': 'larp-dev.synthetic.ap-southeast-2.rds.amazonaws.com',
        'database_name': 'larp',
        'host_ids': {},
        'service_secret_arns': {s: arn.format(account, name, s) for s in services},
        'signing_enabled': False,
    }
    return {k: {'sensitive': False, 'type': 'string', 'value': v} for k, v in values.items()}


class RenderHostConfigs(unittest.TestCase):
    def test_only_infrastructure_values_are_filled(self):
        configs = render.render(render.outputs(terraform_output()), WALLET, 'a' * 64)
        self.assertEqual(set(configs), set(render.EXAMPLES))
        for name, config in configs.items():
            example = json.loads((ROOT / render.EXAMPLES[name]).read_text())
            self.assertEqual(set(config), set(example), name)  # no key added or dropped
            if 'wallet_address' in config:
                self.assertEqual(config['wallet_address'], WALLET.lower())
            self.assertEqual(config['database_host'], 'larp-dev.synthetic.ap-southeast-2.rds.amazonaws.com')
            self.assertEqual(config['database_ca_sha256'], 'a' * 64)
            self.assertEqual(config['database_ca_file'], '/etc/larp/rds-ca.pem')
        self.assertEqual(configs['runtime.json']['runtime_secret_id'], 'larp-dev/runtime')
        self.assertEqual(configs['execution.json']['runtime_secret_id'], 'larp-dev/runtime')
        self.assertEqual(configs['uploader.json']['uploader_secret_id'], 'larp-dev/uploader')
        operations = configs['operations.json']
        self.assertEqual((operations['deployment'], operations['account_id'], operations['region']),
                         ('larp-dev', ACCOUNT, 'ap-southeast-2'))
        self.assertEqual(operations['archive_bucket'], f'larp-{ACCOUNT}-dev-archive')
        # Decided elsewhere, never guessed: run/build IDs, profile and calendar hashes, policy values.
        self.assertIn('run_id', render.unset(configs['runtime.json']))
        self.assertIn('driver.strategy_profile_sha256', render.unset(configs['runtime.json']))
        self.assertIn('rpc_url', render.unset(configs['execution.json']))
        self.assertIn('max_attempts', render.unset(operations))

    def test_a_filled_uploader_config_passes_its_validator(self):
        ca = b'-----BEGIN CERTIFICATE-----\nsynthetic\n-----END CERTIFICATE-----\n'
        with tempfile.NamedTemporaryFile(suffix='.pem') as pem:
            pem.write(ca)
            pem.flush()
            uploader = render.render(render.outputs(terraform_output()), WALLET,
                                     hashlib.sha256(ca).hexdigest())['uploader.json']
            # On the host the file is /etc/larp/rds-ca.pem; here the same bytes sit in a temporary file.
            validate_uploader(dict(uploader, run_id='run', build_id='b' * 40, database_ca_file=pem.name))

    def test_without_the_evidence_secret_still_renders(self):
        tf = render.outputs(terraform_output(services=('runtime', 'uploader')))
        self.assertEqual(tf['secret_ids'], {'runtime': 'larp-dev/runtime', 'uploader': 'larp-dev/uploader'})

    def test_refusals(self):
        tf = render.outputs(terraform_output())
        for wallet in ('', '0x123', 'AbCdEf0123456789aBcDeF0123456789AbCdEf0123'):
            with self.subTest(wallet=wallet), self.assertRaises(render.Refused):
                render.render(tf, wallet)
        with self.assertRaises(render.Refused):
            render.render(tf, WALLET, 'not-a-hash')
        mixed = terraform_output()
        mixed['service_secret_arns']['value']['uploader'] = terraform_output(account='111111111111')[
            'service_secret_arns']['value']['uploader']
        with self.assertRaises(render.Refused):
            render.outputs(mixed)
        with self.assertRaises(render.Refused):
            render.outputs(terraform_output(services=('runtime',)))
        broken = terraform_output()
        del broken['database_host']
        with self.assertRaises(render.Refused):
            render.outputs(broken)

    def test_main_writes_private_files_only_into_an_ignored_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'tf.json'
            source.write_text(json.dumps(terraform_output()))
            outside = Path(tmp) / 'out'
            self.assertEqual(render.main(['--terraform-output', str(source), '--wallet', WALLET,
                                          '--out', str(outside)]), 2)  # not inside the repository's ignored path
            self.assertFalse(outside.exists())
            out = ROOT / 'deploy' / 'activation' / ('test-' + str(os.getpid()))
            try:
                args = ['--terraform-output', str(source), '--wallet', WALLET, '--out', str(out)]
                self.assertEqual(render.main(args), 0)
                for name in render.EXAMPLES:
                    self.assertEqual(stat.S_IMODE((out / name).stat().st_mode), 0o600, name)
                self.assertEqual(render.main(args), 2)  # no silent overwrite
                self.assertEqual(render.main(args + ['--force']), 0)
            finally:
                shutil.rmtree(out, ignore_errors=True)


FAKE_AWS = """#!/usr/bin/env bash
printf '%s\\n' "$@" >> "$FAKE_AWS_DIR/argv"
cat > "$FAKE_AWS_DIR/stdin.$(ls "$FAKE_AWS_DIR" | grep -c stdin)"
echo synthetic-version
"""


@unittest.skipIf(shutil.which('bash') is None or shutil.which('python3') is None, 'bash and python3 required')
class PutServiceSecrets(unittest.TestCase):
    SCRIPT = ROOT / 'tools' / 'deploy' / 'put_service_secrets.sh'
    API, API_SECRET, AUDIT = 'synthetic-api-key', 'synthetic-api-secret', 'ab' * 32

    def run_script(self, answers, *args):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        bin_dir = Path(tmp.name) / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'aws').write_text(FAKE_AWS)
        (bin_dir / 'aws').chmod(0o755)
        record = Path(tmp.name) / 'record'
        record.mkdir()
        env = dict(os.environ, PATH=f'{bin_dir}:{os.environ["PATH"]}', FAKE_AWS_DIR=str(record))
        done = subprocess.run(['bash', str(self.SCRIPT), *args], input='\n'.join(answers) + '\n', text=True,
                              capture_output=True, env=env, timeout=30)
        stored = [json.loads(p.read_text()) for p in sorted(record.glob('stdin.*'))]
        argv = (record / 'argv').read_text() if (record / 'argv').exists() else ''
        return done, stored, argv

    def test_writes_exactly_each_hosts_names_with_values_on_stdin_only(self):
        done, stored, argv = self.run_script(
            [WALLET, self.API, self.API_SECRET, '', '', 'y', self.AUDIT, 'y'], '--name', 'larp-dev')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(stored, [
            {'AI_SEEDS_ADDRESS': WALLET, 'BINANCE_API_KEY': self.API, 'BINANCE_SECRET_KEY': self.API_SECRET},
            {'AI_SEEDS_ADDRESS': WALLET, 'AI_SEEDS_SECRET': self.AUDIT}])
        self.assertIn('larp-dev/runtime', argv)
        self.assertIn('larp-dev/uploader', argv)
        self.assertIn('file:///dev/stdin', argv)
        for value in (self.API, self.API_SECRET, self.AUDIT):
            self.assertNotIn(value, argv)
            self.assertNotIn(value, done.stdout + done.stderr)

    def test_sg4_optional_model_keys_join_the_runtime_secret_on_stdin_only(self):
        aiand, openai = 'synthetic-aiand-key', 'synthetic-openai-key'
        done, stored, argv = self.run_script([WALLET, self.API, self.API_SECRET, aiand, openai, 'y'],
                                             '--name', 'larp-dev', '--only', 'runtime')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(stored, [{'AI_SEEDS_ADDRESS': WALLET, 'BINANCE_API_KEY': self.API,
                                   'BINANCE_SECRET_KEY': self.API_SECRET, 'LARP_AIAND_API_KEY': aiand,
                                   'LARP_MODEL_API_KEY': openai}])
        for value in (aiand, openai):
            self.assertNotIn(value, argv)
            self.assertNotIn(value, done.stdout + done.stderr)
        self.assertIn('LARP_AIAND_API_KEY', done.stderr)  # prompted by name (hidden input)
        done, stored, _ = self.run_script([WALLET, self.API, self.API_SECRET, aiand, '', 'y'],
                                          '--name', 'larp-dev', '--only', 'runtime')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(stored, [{'AI_SEEDS_ADDRESS': WALLET, 'BINANCE_API_KEY': self.API,
                                   'BINANCE_SECRET_KEY': self.API_SECRET, 'LARP_AIAND_API_KEY': aiand}])

    def test_sg4_the_script_writes_the_names_the_runtime_loads(self):
        from larp.runtime.credentials import OPTIONAL_MODEL_SECRETS
        from larp.runtime.live import RUNTIME_SECRETS
        text = self.SCRIPT.read_text()
        for name in RUNTIME_SECRETS + OPTIONAL_MODEL_SECRETS:
            self.assertIn(name, text)

    def test_declining_writes_nothing(self):
        done, stored, _ = self.run_script([WALLET, self.API, self.API_SECRET, '', '', 'n'], '--name', 'larp-dev',
                                          '--only', 'runtime')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(stored, [])

    def test_refusals(self):
        cases = {
            'bad address': ([('0x1234'), self.API], ['--name', 'larp-dev']),
            'bad audit secret': ([WALLET, 'not-hex'], ['--name', 'larp-dev', '--only', 'uploader']),
            'bad name': ([WALLET], ['--name', 'Larp Dev']),
            'empty key': ([WALLET, ''], ['--name', 'larp-dev', '--only', 'runtime']),
        }
        for label, (answers, args) in cases.items():
            with self.subTest(label):
                done, stored, _ = self.run_script(answers, *args)
                self.assertNotEqual(done.returncode, 0)
                self.assertEqual(stored, [])
                self.assertNotIn('not-hex', done.stdout + done.stderr)


if __name__ == '__main__':
    unittest.main()

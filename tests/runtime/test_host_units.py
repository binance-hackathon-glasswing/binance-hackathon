"""IDEA-047 D01: systemd units of the host services."""
from pathlib import Path
import re
import unittest

UNITS = Path(__file__).resolve().parents[2] / 'deploy/systemd'
HARDENING = ('NoNewPrivileges=true', 'ProtectSystem=strict', 'ProtectHome=true', 'PrivateTmp=true',
             'PrivateDevices=true', 'ProtectKernelTunables=true', 'ProtectKernelModules=true',
             'ProtectControlGroups=true', 'RestrictSUIDSGID=true', 'LockPersonality=true',
             'RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6', 'CapabilityBoundingSet=', 'UMask=0077')
SERVICES = {  # unit -> (host role, module, pinned config name or None)
    'larp-signer': ('signer', 'larp.signer.service', 'signer'),
    'larp-execution': ('primary', 'larp.execution_live.main', 'execution'),
    'larp-uploader': ('primary', 'larp.audit.service', 'uploader'),
    'larp-evidence': ('primary', 'larp.sources.live', None),
}


def directives(name):
    lines = (UNITS / (name + '.service')).read_text(encoding='utf-8').splitlines()
    return [line.strip() for line in lines if '=' in line and not line.lstrip().startswith('#')]


def value(lines, key):
    return [line.split('=', 1)[1] for line in lines if line.split('=', 1)[0] == key]


class HostUnits(unittest.TestCase):
    def test_d01_each_service_has_its_own_user_hardening_and_preflight(self):
        users = set()
        for unit, (role, module, config) in SERVICES.items():
            with self.subTest(unit=unit):
                d = directives(unit)
                users.add(value(d, 'User')[0])
                self.assertEqual(value(d, 'User'), [unit])
                self.assertEqual(value(d, 'Group'), [unit])
                for line in HARDENING:
                    self.assertIn(line, d)
                self.assertIn('Restart=always', d)
                self.assertIn('StartLimitIntervalSec=0', d)
                self.assertIn(f'ConditionPathExists=/etc/larp/role-{role}', d)
                pre, start = value(d, 'ExecStartPre'), value(d, 'ExecStart')
                self.assertEqual(len(pre), 1)
                self.assertEqual(len(start), 1)
                self.assertIn('-m larp.runtime.preflight --manifest /etc/larp/release.json --root /opt/larp/current '
                              '--profile host', pre[0])
                self.assertIn(f'-m {module} run', start[0])
                if config:
                    path = f'/etc/larp/{config}.json'
                    self.assertIn(f'--service-config {config}={path}', pre[0])
                    self.assertIn(f'--config {path}', start[0])
                    self.assertIn(f'ConditionPathExists={path}', d)
                    self.assertIn('RestartPreventExitStatus=2 3 4', d)
                # Settings never carry a secret: no Environment= value names a key, secret or token.
                for line in value(d, 'Environment'):
                    self.assertNotRegex(line.upper(), r'KEY|SECRET|TOKEN|MNEMONIC|PASSWORD')
        self.assertEqual(len(users), len(SERVICES))
        self.assertTrue(users.isdisjoint({'larp-runtime', 'larp-archive', 'root'}))

    def test_d01_only_the_signer_loads_the_key_and_only_as_a_credential(self):
        for unit in SERVICES:
            d = directives(unit)
            with self.subTest(unit=unit):
                if unit == 'larp-signer':
                    self.assertEqual(value(d, 'LoadCredential'), ['wallet.key:/etc/larp/signer/wallet.key'])
                    self.assertNotIn('ConditionPathExists=/etc/larp/role-primary', d)
                else:
                    self.assertEqual(value(d, 'LoadCredential'), [])
                    self.assertFalse(any('signer/wallet.key' in line for line in d))
        for unit in ('larp-runtime', 'larp-archive'):
            self.assertFalse(any('LoadCredential' in line or 'wallet.key' in line for line in directives(unit)))

    def test_d01_evidence_reads_only_a_non_secret_settings_file(self):
        d = directives('larp-evidence')
        self.assertEqual(value(d, 'EnvironmentFile'), ['/etc/larp/evidence.env'])
        self.assertEqual(value(d, 'StateDirectory'), ['larp-evidence'])
        self.assertIn('--release-manifest /etc/larp/release.json --release-root /opt/larp/current',
                      value(d, 'ExecStart')[0])

    def test_d01_example_configs_match_the_units(self):
        import json
        examples = Path(__file__).resolve().parents[2] / 'config/hosts'
        for name, schema in (('signer', 'SignerService.v1'), ('execution', 'ExecutionService.v1'),
                             ('uploader', 'UploaderService.v1')):
            with self.subTest(name=name):
                config = json.loads((examples / f'{name}.example.json').read_text(encoding='utf-8'))
                self.assertEqual(config['schema'], schema)
                self.assertFalse(any(re.search('private_key|mnemonic', k) for k in config))
        self.assertEqual(json.loads((examples / 'signer.example.json').read_text())['key_credential'], 'wallet.key')
        env = (examples / 'evidence.example.env').read_text(encoding='utf-8')
        self.assertIn('LARP_ARTIFACT_ROOT=/var/lib/larp-evidence', env)
        names = [line.split('=', 1)[0] for line in env.splitlines() if '=' in line and not line.startswith('#')]
        self.assertEqual(names, ['LARP_SEC_USER_AGENT', 'LARP_ARTIFACT_ROOT'])  # no key or secret setting


if __name__ == '__main__':
    unittest.main()

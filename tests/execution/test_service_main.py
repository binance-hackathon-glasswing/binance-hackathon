"""IDEA-047 E01, IDEA-050 E9: the execution entry point holds no key, refuses an unactivated run and stops at the
Executor's capability gate."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile

from unittest.mock import patch

from larp.execution_live.main import EXIT_NOT_INTEGRATED, EXIT_QUARANTINED, EXIT_REFUSED, main
from larp.marketdata.port import TOKENS
from larp.research.fixtures import synthetic_profile
from larp.storage.postgres import doc
from tests.host_support import BUILD, synthetic_release
from tests.support import DatabaseCase

WALLET = '0x' + 'a' * 40


class ExecutionCommand(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        dsn = Path(self.tmp.name) / 'dsn'
        dsn.write_text(self.store._dsn)
        self.store.initialize('live-run', WALLET, 56, doc(dict(balances=dict(USDT=1))), mode='dev')
        self.config = dict(schema='ExecutionService.v1', run_id='live-run', build_id=BUILD, mode='dev',
                           wallet_address=WALLET, interval_seconds=1, database_dsn_file=str(dsn))

    def run_main(self, command, config=None, pin=True):
        raw = json.dumps(config or self.config).encode()
        path = Path(self.tmp.name) / 'execution.json'
        path.write_bytes(raw)
        root, manifest = synthetic_release(self.tmp.name, {'execution': raw} if pin else {})
        out = io.StringIO()
        with redirect_stdout(out):
            code = main([command, '--config', str(path), '--manifest', str(manifest), '--root', str(root)])
        return code, json.loads(out.getvalue())

    def test_e01_check_then_not_integrated(self):
        self.assertEqual(self.run_main('check'), (0, dict(configuration_valid=True, signing_enabled=False)))
        code, out = self.run_main('run')  # a new run is quarantined until `service activate` (IDEA-050)
        self.assertEqual((code, out['reason'], out['signing_enabled']), (EXIT_QUARANTINED, 'QUARANTINED', False))
        self.store.activate('live-run', self.store.load('live-run').read()['epoch'])
        profile = json.dumps(dict(synthetic_profile(), mode='LIVE')).encode()
        (Path(self.tmp.name) / 'profile.json').write_bytes(profile)
        full = dict(self.config, market_artifact_root=str(Path(self.tmp.name) / 'market'),
                    chain_artifact_root=str(Path(self.tmp.name) / 'chain'), rpc_url='https://rpc.invalid/',
                    rpc_source_id='fixture', broadcast_rpc_url='https://submit.invalid/', router='0x' + '2' * 40,
                    token_decimals={s: 18 for s in TOKENS}, max_gas=500000, max_gas_price=10**10, gas_budget=10**16,
                    strategy_profile_file=str(Path(self.tmp.name) / 'profile.json'),
                    strategy_profile_sha256=hashlib.sha256(profile).hexdigest())
        secrets = dict(BINANCE_API_KEY='synthetic-key', BINANCE_SECRET_KEY='synthetic-secret')
        with patch('larp.runtime.credentials.runtime_secrets', return_value=secrets):
            code, out = self.run_main('run', full)
            self.assertEqual((code, out['reason'], out['detail'], out['signing_enabled']),
                             (EXIT_NOT_INTEGRATED, 'NOT_INTEGRATED', 'EXECUTOR_CAPABILITY_GATE', False))
            code, out = self.run_main('run')  # an active run without the build settings never starts
            self.assertEqual((code, out['reason']), (EXIT_REFUSED, 'START_REFUSED'))

    def test_e01_refusals(self):
        cases = {
            'unpinned config': (self.config, False),
            'wallet key file': ({**self.config, 'key_file': '/k'}, True),
            'wallet key value': ({**self.config, 'wallet_private_key': '0x' + '1' * 64}, True),
            'mnemonic': ({**self.config, 'wallet_mnemonic': 'w'}, True),
            'paper mode': ({**self.config, 'mode': 'paper'}, True),
            'other build': ({**self.config, 'build_id': 'c' * 40}, True),
            'runtime database role': ({k: v for k, v in self.config.items() if k != 'database_dsn_file'} | dict(
                database_host='h', database_user='larp_runtime', database_name='larp', database_ca_file='/x',
                database_ca_sha256='0', region='ap-southeast-2'), True),
            'wallet differs from the run': ({**self.config, 'wallet_address': '0x' + 'b' * 40}, True),
            'mode differs from the run': ({**self.config, 'mode': 'live'}, True),
        }
        for name, (config, pin) in cases.items():
            with self.subTest(name=name):
                code, out = self.run_main('run', config, pin)
                self.assertEqual((code, out['reason']), (EXIT_REFUSED, 'START_REFUSED'))

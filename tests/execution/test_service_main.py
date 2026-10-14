"""IDEA-047 E01: the execution service entry point holds no key and stops NOT_INTEGRATED until the round driver."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile

from larp.execution_live.main import EXIT_NOT_INTEGRATED, EXIT_REFUSED, main
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
        code, out = self.run_main('run')
        self.assertEqual((code, out['reason'], out['signing_enabled']), (EXIT_NOT_INTEGRATED, 'NOT_INTEGRATED', False))

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

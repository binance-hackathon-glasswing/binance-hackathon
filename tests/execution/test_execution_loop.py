"""IDEA-050 E9: the execution entry point composes live ports and stops at the Executor's capability gate.

No network: the composed clients are constructed, never called. The broadcast boundary is exercised with fakes.
"""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import ContractError
from larp.execution import Blocked, Signed
from larp.execution_live.loop import FencedRelease, RawTransactionSubmitter
from larp.execution_live.main import EXIT_NOT_INTEGRATED, EXIT_REFUSED, NotIntegrated, build_execution, main
from larp.marketdata.port import TOKENS
from larp.research.fixtures import synthetic_profile
from larp.storage.postgres import doc

WALLET = '0x' + '5' * 40


class Store:
    def load(self, run_id):
        return doc(dict(epoch=3, version=7, wallet_id=WALLET))


class Composition(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        profile = json.dumps(dict(synthetic_profile(), mode='LIVE')).encode()
        (self.root / 'profile.json').write_bytes(profile)
        self.secrets = dict(BINANCE_API_KEY='synthetic-key', BINANCE_SECRET_KEY='synthetic-secret')
        self.config = dict(schema='ExecutionService.v1', run_id='run', build_id='a' * 40, mode='dev',
                           wallet_address=WALLET, interval_seconds=1, database_dsn_file='/synthetic',
                           market_artifact_root=str(self.root / 'market'), chain_artifact_root=str(self.root / 'chain'),
                           rpc_url='https://rpc.invalid/', rpc_source_id='fixture-rpc',
                           broadcast_rpc_url='https://submit.invalid/', router='0x' + '2' * 40,
                           token_decimals={s: 18 for s in TOKENS}, max_gas=500_000, max_gas_price=10**10,
                           gas_budget=10**16, strategy_profile_file=str(self.root / 'profile.json'),
                           strategy_profile_sha256=hashlib.sha256(profile).hexdigest())

    def test_e9_a_valid_configuration_stops_at_the_executor_capability_gate(self):
        with self.assertRaises(NotIntegrated) as gate:
            build_execution(self.config, Store(), self.secrets)
        self.assertEqual(str(gate.exception), 'EXECUTOR_CAPABILITY_GATE')

    def test_e9_inconsistent_inputs_are_refused(self):
        for change in (dict(router='0xnot'), dict(token_decimals={'NVDAB': 18}), dict(max_gas=0),
                       dict(strategy_profile_sha256='0' * 64), dict(rpc_url='http://rpc.invalid/'),
                       dict(broadcast_rpc_url=None)):
            with self.subTest(change), self.assertRaises((ContractError, Blocked)):
                build_execution(dict(self.config, **change), Store(), self.secrets)
        with self.assertRaises(ContractError):
            build_execution(self.config, Store(), {})

    def test_e9_main_exits_2_at_the_gate_and_4_on_a_refusal(self):
        raw = json.dumps(self.config).encode()
        (self.root / 'execution.json').write_bytes(raw)
        argv = ['run', '--config', str(self.root / 'execution.json'), '--manifest', str(self.root / 'm.json'),
                '--root', str(self.root)]
        (self.root / 'm.json').write_bytes(b'{}')

        class Db:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        class Opened:
            def transaction(self):
                return Db()

        run = dict(mode='dev', wallet_id=WALLET, quarantined=False)
        for error, code in ((NotIntegrated('EXECUTOR_CAPABILITY_GATE'), EXIT_NOT_INTEGRATED),
                            (ContractError('refused'), EXIT_REFUSED)):
            with self.subTest(code=code), \
                    patch('larp.runtime.preflight.verify_release', return_value=dict(build_id='a' * 40)), \
                    patch('larp.runtime.preflight.verify_service_config'), \
                    patch('larp.runtime.database.open_service_store', return_value=Opened()), \
                    patch('larp.storage.postgres.PostgresStore._run', return_value=run), \
                    patch('larp.runtime.credentials.runtime_secrets', return_value=self.secrets), \
                    patch('larp.execution_live.main.build_execution', side_effect=error), patch('builtins.print'):
                self.assertEqual(main(argv), code)
        named = dict(self.config, key_file='/etc/larp/signer/wallet.key')
        (self.root / 'execution.json').write_bytes(json.dumps(named).encode())
        with patch('builtins.print'):
            self.assertEqual(main(argv), EXIT_REFUSED)  # a configuration naming a key never starts


class Release(unittest.TestCase):
    def test_e9_the_release_rechecks_the_possible_send_and_the_returned_hash(self):
        signed = Signed('0xabcd', '0x' + 'a' * 64)

        class Registry:
            def __init__(self, ok):
                self.ok, self.checked = ok, []

            def check_broadcast(self, s, epoch, version):
                self.checked.append((s, epoch, version))
                if not self.ok:
                    from larp.execution import Conflict
                    raise Conflict('no possible-send authority')

        class Submitter:
            def __init__(self, answer):
                self.answer, self.sent = answer, []

            def send(self, raw):
                self.sent.append(raw)
                return self.answer

        good = Submitter(signed.tx_hash)
        self.assertEqual(FencedRelease(Registry(True), good)(signed, 3, 3), signed.tx_hash)
        refused = Submitter(signed.tx_hash)
        with self.assertRaises(Blocked):
            FencedRelease(Registry(False), refused)(signed, 3, 3)
        self.assertEqual(refused.sent, [])  # nothing leaves without the durable possible-send record
        with self.assertRaises(Blocked):
            FencedRelease(Registry(True), Submitter('0x' + 'b' * 64))(signed, 3, 3)

    def test_e9_the_submitter_speaks_only_eth_send_raw_transaction_over_https(self):
        for url in ('http://rpc.invalid/', 'https://user:pw@rpc.invalid/', 'ftp://rpc.invalid/'):
            with self.subTest(url), self.assertRaises(Blocked):
                RawTransactionSubmitter(url)
        sent = []

        class Response:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n):
                return self.body

        class Opener:
            def open(self, request, timeout):
                sent.append(json.loads(request.data))
                return Response(json.dumps(dict(jsonrpc='2.0', id=1, result='0x' + 'c' * 64)).encode())

        self.assertEqual(RawTransactionSubmitter('https://rpc.invalid/', opener=Opener()).send('0xabcd'),
                         '0x' + 'c' * 64)
        self.assertEqual([(s['method'], s['params']) for s in sent], [('eth_sendRawTransaction', ['0xabcd'])])


if __name__ == '__main__':
    unittest.main()

"""LD21-H RG6 harness: the read-only preflight agrees with switch_wallet and writes nothing (PostgreSQL)."""
import importlib.util
import json
from pathlib import Path
import tempfile

from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePlanner, FakePolicy
from larp.runtime.live import LiveStartRefused, bind_directory, switch_wallet
from larp.storage.postgres import doc
from tests.support import DatabaseCase, request

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('drill_wallet_switch', ROOT / 'tools/deploy/drill_wallet_switch.py')
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)

NEW = '0x' + 'a' * 40
OLD = '0x' + 'c' * 40
NOW = 1791590400000


class WalletSwitchHarness(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old_dirs = [str(bind_directory(self.root / 'dev/.ai-seeds', OLD)), str(bind_directory(self.root / 'dev/nonces', OLD))]
        self.new_dirs = [str(self.root / 'final/.ai-seeds'), str(self.root / 'final/nonces')]

    def report(self, run='run', **changes):
        options = dict(old_run=run, new_wallet=NEW, old_dirs=self.old_dirs, new_dirs=self.new_dirs)
        options.update(changes)
        return harness.preflight(harness.read_only(self.store), **options)

    def accepted(self, run='run', **changes):
        options = dict(old_run=run, new_run='final-' + run, new_wallet=NEW, chain_id=56,
                       initial_projection=dict(balances=dict(USDT=200, BNB=0)), old_dirs=self.old_dirs,
                       new_dirs=self.new_dirs)
        options.update(changes)
        try:
            switch_wallet(self.store, **options)
            return True
        except LiveStartRefused:
            return False

    def assert_agrees(self, blocker, run='run', **changes):
        report = self.report(run, **changes)
        self.assertIn(blocker, report['blockers'])
        self.assertFalse(report['ready'])
        self.assertFalse(self.accepted(run, **changes))

    def test_clean_flat_run_is_ready_and_preflight_creates_nothing(self):
        report = self.report()
        self.assertEqual((report['ready'], report['blockers']), (True, []))
        self.assertEqual(set(report['new_directories'].values()), {'WILL_CREATE'})
        self.assertFalse((self.root / 'final').exists())  # nothing created or marked
        self.assertEqual(self.store.load('run').read()['version'], report['old_version'])
        self.assertTrue(self.accepted())

    def test_open_round_reservations_and_unfinished_execution_block_both(self):
        c = Coordinator(self.store, FakeAssessor(), FakePolicy(), FakePlanner(), execution=FakeExecution(),
                        run_id='run', version_id='synthetic', profile_hash='a' * 64, address='0x' + '1' * 40,
                        clock_ms=lambda: NOW)
        c.start('r', request('BUY'), NOW)
        report = self.report()
        self.assertTrue({'OPEN_ROUNDS', 'RESERVATIONS'} <= set(report['blockers']))
        self.assertFalse(self.accepted())
        with self.store.transaction() as db:
            db.execute("INSERT INTO execution_records VALUES('key-r','run','0xw',56,false,1,'{}','s')")
        self.assertIn('UNFINISHED_EXECUTIONS', self.report()['blockers'])

    def test_held_token_blocks_both(self):
        self.store.initialize('held', OLD, 56, doc(dict(balances=dict(USDT=1, BNB=1, NVDAB=5))))
        self.assert_agrees('NOT_FLAT', run='held')
        self.assertEqual(self.report('held')['held_tokens'], ['NVDAB'])

    def test_wallet_and_directory_refusals_block_both(self):
        self.assert_agrees('NEW_WALLET_INVALID_OR_SAME', new_wallet='wallet')
        self.assert_agrees('NEW_WALLET_INVALID_OR_SAME', new_wallet='not-an-address')
        self.assert_agrees('DIRECTORIES_NOT_SEPARATE', new_dirs=[self.old_dirs[0], self.new_dirs[1]])
        bind_directory(self.root / 'other', '0x' + 'd' * 40)
        self.assert_agrees('DIRECTORY_UNUSABLE', new_dirs=[str(self.root / 'other'), self.new_dirs[1]])
        (self.root / 'unmarked').mkdir()
        (self.root / 'unmarked' / 'spool.jsonl').write_text('{}')
        self.assert_agrees('DIRECTORY_UNUSABLE', new_dirs=[str(self.root / 'unmarked'), self.new_dirs[1]])

    def test_preflight_transactions_are_read_only_and_the_original_store_is_untouched(self):
        store = harness.read_only(self.store)
        with self.assertRaises(Exception):
            with store.transaction() as db:
                db.execute("INSERT INTO execution_records VALUES('key-x','run','0xw',56,false,1,'{}','s')")
        with self.store.transaction() as db:  # the original still writes, and the refused row is absent
            self.assertEqual(db.execute("SELECT count(*) FROM execution_records WHERE economic_key='key-x'").fetchone()[0], 0)
            db.execute("INSERT INTO execution_records VALUES('key-y','run','0xw',56,true,1,'{}','s')")

    def test_cli_switch_needs_confirmation_and_a_new_record_file(self):
        config = self.root / 'runtime.json'
        config.write_text(json.dumps(dict(run_id='run', ai_seeds_dir=self.old_dirs[0], nonce_dir=self.old_dirs[1])))
        projection = self.root / 'opening.json'
        projection.write_text(json.dumps(dict(balances=dict(USDT=200, BNB=0))))
        base = ['--config', str(config), '--new-wallet', NEW, '--new-ai-seeds-dir', self.new_dirs[0],
                '--new-nonce-dir', self.new_dirs[1]]
        stores = lambda _config: self.store  # noqa: E731
        self.assertEqual(harness.main(['preflight', *base], open_store=stores), 0)
        switch = ['switch', *base, '--new-run', 'final', '--initial-projection', str(projection),
                  '--record-out', str(self.root / 'record.json')]
        self.assertEqual(harness.main([*switch, '--confirm-old-run', 'wrong'], open_store=stores), 2)
        self.assertFalse((self.root / 'final').exists())
        self.assertEqual(harness.main([*switch, '--confirm-old-run', 'run'], open_store=stores), 0)
        record = json.loads((self.root / 'record.json').read_text())
        self.assertEqual((record['old_run'], record['new_run'], record['new_wallet']), ('run', 'final', NEW))
        self.assertEqual(self.store.load('final').read()['wallet_id'], NEW)

"""Live-mode refusals and the final-wallet switch (IDEA-042 W1-W4; DR-17)."""

import os
from pathlib import Path
import tempfile
import unittest

from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakeMarket, FakePlanner, FakePolicy, settle
from larp.runtime.live import LiveStartRefused, bind_directory, check_live_start, switch_wallet
from larp.runtime.service import Service
from larp.runtime.supervision import Guard
from larp.storage.postgres import doc
from tests.support import DatabaseCase, request

WALLET = '0x' + 'a' * 40
OTHER = '0x' + 'b' * 40
NOW = 1791590400000


class Real:
    """Stands in for a production port: no fixture marker, not from a fixtures module."""


# The runtime host's secrets only (IDEA-042 S3): no audit secret, no wallet key.
SECRETS = dict(AI_SEEDS_ADDRESS=WALLET, BINANCE_API_KEY='k', BINANCE_SECRET_KEY='s3cret-value')


class Refusals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dirs = dict(ai_seeds_dir=Path(self.tmp.name) / 'dev' / '.ai-seeds',
                         nonce_dir=Path(self.tmp.name) / 'dev' / 'nonces')

    def check(self, mode='live', ports=None, secrets=SECRETS, wallet=WALLET, run_wallet=WALLET, **dirs):
        check_live_start(mode=mode, ports=ports if ports is not None else dict(market=Real(), assessor=Real()),
                         secrets=secrets, wallet_address=wallet, run_wallet=run_wallet, **{**self.dirs, **dirs})

    def refused(self, fragment, **kwargs):
        with self.assertRaises(LiveStartRefused) as caught:
            self.check(**kwargs)
        self.assertIn(fragment, str(caught.exception))
        self.assertNotIn('s3cret-value', str(caught.exception))  # never a secret value
        return caught.exception

    def test_w1_valid_live_start_passes_and_binds_directories(self):
        self.check()
        self.assertEqual((self.dirs['ai_seeds_dir'] / '.larp-wallet').read_text().strip(), WALLET)

    def test_w1_each_refusal(self):
        self.refused('market', ports=dict(market=FakeMarket(), assessor=Real()))
        self.refused('assessor', ports=dict(market=Real(), assessor=FakeAssessor()))
        self.refused('assessor', ports=dict(market=Real(), assessor=None))
        self.refused('BINANCE_SECRET_KEY', secrets={**SECRETS, 'BINANCE_SECRET_KEY': ''})
        self.refused('uploader host only', secrets={**SECRETS, 'AI_SEEDS_SECRET': 'audit-secret'})  # S3
        self.refused('BINANCE_API_KEY', secrets={k: v for k, v in SECRETS.items() if k != 'BINANCE_API_KEY'})
        self.refused('WALLET_PRIVATE_KEY', secrets={**SECRETS, 'WALLET_PRIVATE_KEY': 'never-here'})
        self.refused('mismatch', wallet=OTHER)
        self.refused('mismatch', run_wallet=OTHER)
        self.refused('mismatch', secrets={**SECRETS, 'AI_SEEDS_ADDRESS': OTHER})
        self.refused('separate directories', nonce_dir=self.dirs['ai_seeds_dir'])

    def test_w1_offline_and_paper_are_not_checked(self):
        for mode in ('offline', 'paper'):
            self.check(mode=mode, ports=dict(market=FakeMarket()), secrets={})

    def test_w2_a_directory_marked_for_another_wallet_is_refused(self):
        bind_directory(self.dirs['ai_seeds_dir'], OTHER)
        self.refused('another wallet')
        unmarked = Path(self.tmp.name) / 'old'
        unmarked.mkdir()
        (unmarked / 'spool.jsonl').write_text('{}')
        self.refused('unmarked records', ai_seeds_dir=unmarked)

    def test_w2_an_unbindable_directory_is_a_refused_start_not_a_crash(self):
        # #59 (WR17): an OSError must refuse the start (exit 4), or Restart=always loops on it.
        blocker = Path(self.tmp.name) / 'blocker'
        blocker.write_text('not a directory')
        refusal = self.refused('cannot be bound', ai_seeds_dir=blocker / '.ai-seeds')
        self.assertIn('NotADirectoryError', str(refusal))

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0, 'root ignores the directory mode')
    def test_w2_a_read_only_directory_is_a_refused_start(self):
        read_only = Path(self.tmp.name) / 'read-only'
        read_only.mkdir(mode=0o500)
        self.addCleanup(read_only.chmod, 0o700)
        refusal = self.refused('cannot be bound', nonce_dir=read_only)
        self.assertIn('PermissionError', str(refusal))


class Switch(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.old_dirs = [bind_directory(root / 'dev/.ai-seeds', '0x' + 'c' * 40),
                         bind_directory(root / 'dev/nonces', '0x' + 'c' * 40)]
        self.new_dirs = [root / 'final/.ai-seeds', root / 'final/nonces']

    def switch(self, **changes):
        options = dict(old_run='run', new_run='final', new_wallet=WALLET, chain_id=56,
                       initial_projection=dict(balances=dict(USDT=200, BNB=0)), old_dirs=self.old_dirs,
                       new_dirs=self.new_dirs)
        return switch_wallet(self.store, **{**options, **changes})

    def coordinator(self):
        return Coordinator(self.store, FakeAssessor(), FakePolicy(), FakePlanner(), execution=FakeExecution(),
                           run_id='run', version_id='synthetic', profile_hash='a' * 64, address='0x' + '1' * 40,
                           clock_ms=lambda: NOW)

    def test_w3_refused_until_the_old_run_is_closed_and_flat(self):
        c = self.coordinator()
        c.start('r', request('BUY'), NOW)  # open round, reservations and a pending command
        with self.assertRaises(LiveStartRefused):
            self.switch()
        with self.store.transaction() as db:  # the execution service's record of that intent, not yet terminal
            db.execute("INSERT INTO execution_records VALUES('key-r','run','0xw',56,false,1,'{}','s')")
        tx = '0x' + 'b' * 64
        c.observe('b', doc(dict(kind='BROADCAST_ATTEMPTED', observation_id='b', round_id='r', tx_hash=tx,
                                simulated=True)), settle)
        c.observe('f', doc(dict(kind='FINAL_SUCCESS', observation_id='f', round_id='r', tx_hash=tx,
                                simulated=True)), settle)
        c.recover(NOW + 1)
        with self.assertRaises(LiveStartRefused) as caught:  # rounds closed, but the execution is unfinished
            self.switch()
        self.assertIn('unfinished executions', str(caught.exception))
        with self.store.transaction() as db:  # the execution service finishes it (IDEA-042 V6; grant tested in G2)
            db.execute("UPDATE execution_records SET terminal=true WHERE economic_key='key-r'")
        with self.assertRaises(LiveStartRefused) as caught:  # holds NVDAB after the fill
            self.switch()
        self.assertIn('not flat', str(caught.exception))

    def test_w3_rehearsal_with_a_throwaway_configuration(self):
        with self.assertRaises(LiveStartRefused):
            self.switch(new_wallet='wallet')  # same as the old run's wallet ID / not an address
        with self.assertRaises(LiveStartRefused):
            self.switch(new_dirs=[self.old_dirs[0], self.new_dirs[1]])  # shared .ai-seeds directory
        record = self.switch()
        self.assertEqual((record['old_run'], record['new_run'], record['new_wallet']), ('run', 'final', WALLET))
        self.assertEqual(record['old_head'], self.store.verify('run'))
        new = self.store.load('final').read()
        self.assertEqual((new['wallet_id'], new['mode'], new['quarantined']), (WALLET, 'live', True))
        self.assertEqual((self.new_dirs[0] / '.larp-wallet').read_text().strip(), WALLET)

    def test_w4_service_refuses_before_opening_a_session(self):
        def start_check():
            check_live_start(mode='live', ports=dict(market=FakeMarket()), secrets=SECRETS, wallet_address=WALLET,
                             run_wallet=WALLET, ai_seeds_dir=self.new_dirs[0], nonce_dir=self.new_dirs[1])
        service = Service(self.store, 'run', 'build-1', guard=Guard(self.store, 'run', max_failures=3, clear_after=2),
                          driver=None, clock_ms=lambda: NOW, start_check=start_check, session_id='s1')
        with self.assertRaises(LiveStartRefused):
            service.run(max_cycles=1)
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM process_sessions').fetchone()[0], 0)

"""PR #69 regressions; criteria: IDEA-049-D D-RV-01/02. Disposable PostgreSQL, synthetic execution/receivers only."""

import json

from larp.audit.delivery import DeliveryWorker
from larp.contracts import Document
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePlanner, FakePolicy, FakeReceiver, settle
from larp.runtime.maintenance import HOUR_MS, Maintenance
from larp.storage.archive import S3Archive
from larp.storage.postgres import Conflict, doc
from tests.storage.test_archive import FakeS3
from tests.support import DatabaseCase, request

NOW = 1791590400000
DAY_MS = 86_400_000
WALLET = '0x' + '5' * 40


class Review(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.store.initialize('dev', WALLET, 56, doc(dict(balances=dict(USDT=100, BNB=10, NVDAB=0))), mode='dev')
        self.dev_epoch = self.store.activate('dev', 1)
        self.coordinator = Coordinator(self.store, FakeAssessor(), FakePolicy(), FakePlanner(),
                                       execution=FakeExecution(), run_id='dev', version_id='synthetic',
                                       profile_hash='a' * 64, address=WALLET, clock_ms=lambda: NOW)
        self.coordinator.start('r', doc(dict(request('BUY').read(), run_id='dev')), NOW)

    def broadcast(self):
        self.coordinator.observe('b', doc(dict(kind='BROADCAST_ATTEMPTED', observation_id='b', round_id='r',
                                              tx_hash='0x' + 'b' * 64, simulated=True)), settle)

    def test_logged_round_remains_open_until_settlement_and_recovery(self):
        self.broadcast()
        self.coordinator.log_round('r', NOW + 1)
        self.assertEqual(list(dict(self.store.open_rounds('dev'))), ['r'])
        self.assertEqual(self.store.metrics('dev').read()['open_rounds'], 1)
        self.coordinator.observe('f', doc(dict(kind='FINAL_SUCCESS', observation_id='f', round_id='r',
                                              tx_hash='0x' + 'b' * 64, simulated=True)), settle)
        # Even settled work must reach the journaled ROUND_CLOSED transition before it disappears.
        self.assertEqual(self.store.metrics('dev').read()['open_rounds'], 1)
        self.coordinator.recover(NOW + 2)
        self.assertEqual(self.store.open_rounds('dev'), [])
        self.assertEqual(self.store.metrics('dev').read()['open_rounds'], 0)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM audit_events WHERE run_id='dev'").fetchone()[0], 1)
        self.store.verify('dev')

    def test_activation_refuses_a_logged_round_awaiting_runtime_settlement(self):
        self.broadcast()
        self.coordinator.log_round('r', NOW + 1)
        self.store.quarantine('dev')
        # There is no unfinished execution record to protect this window: the runtime's outstanding round must.
        with self.assertRaisesRegex(Conflict, 'round is still open'):
            self.store.activate('dev', self.dev_epoch)
        run = self.store.load('dev').read()
        self.assertTrue(run['quarantined'])
        self.assertEqual(run['epoch'], self.dev_epoch)

    def test_archive_health_counts_overdue_unlogged_rounds_and_clears_after_ack(self):
        archive = S3Archive(FakeS3(), bucket='fixture', account_id='123456789012', kms_key='k',
                            prefix='archive/dev', retention_days=90)
        worker = Maintenance(self.store, archive, backup_interval_ms=DAY_MS)
        late = (NOW // DAY_MS + 1) * DAY_MS + 2 * HOUR_MS + 1
        worker.prepare('dev', late)
        for _ in range(4):
            worker.once('dev', late)
        health = worker.health('dev', late).read()
        self.assertEqual(health['reasons'], ['AUDIT_DELIVERY_BLOCKED'])
        self.assertEqual(health['audit_deadline_breaches'], 1)
        self.assertEqual(worker.service_health('dev', late).read()['audit_overdue'], 1)
        self.broadcast()
        self.coordinator.log_round('r', late)
        receiver = FakeReceiver()
        uploader = DeliveryWorker(self.store, receiver, retry_ms=1)
        for _ in range(20):
            if not uploader.once('dev', self.dev_epoch, late):
                break
        self.assertTrue(receiver.stored)
        self.assertTrue(worker.health('dev', late).read()['healthy'])
        with self.store.transaction() as db:
            [raw] = db.execute("SELECT document FROM audit_events WHERE run_id='dev'").fetchone()
        self.assertEqual(json.loads(Document(bytes(raw)).read()['log'])['data']['orders'][0]['tx_hash'], '0x' + 'b' * 64)

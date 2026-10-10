from larp.contracts import ContractError, Document
from larp.runtime.maintenance import Maintenance, HOUR_MS
from larp.storage.archive import S3Archive
from larp.storage.backup import export, restore
from larp.storage.postgres import Conflict, Unavailable, digest
from tests.storage.test_archive import FakeS3
from tests.support import DatabaseCase


class MaintenanceTests(DatabaseCase):
    def worker(self, client=None, **kwargs):
        self.client = client or FakeS3()
        archive = S3Archive(self.client, bucket='fixture', account_id='123456789012',
                            kms_key='arn:synthetic:key', prefix='archive/development', retention_days=7)
        return Maintenance(self.store, archive, backup_interval_ms=24*HOUR_MS, retry_ms=1000, **kwargs)

    def test_hourly_anchor_with_unchanged_head_and_daily_backup(self):
        worker = self.worker()
        worker.prepare('run', 100)
        worker.prepare('run', 100)
        for _ in range(2): worker.once('run', 100)
        self.assertTrue(worker.health('run', 100).read()['healthy'])
        self.assertEqual(2, len(self.client.objects))
        worker.prepare('run', HOUR_MS+100)
        worker.once('run', HOUR_MS+100)
        self.assertEqual(3, len(self.client.objects))
        with self.assertRaises(Conflict): worker.prepare('run', 0)
        self.assertIn('ANCHOR_STALE', worker.health('run', 4*HOUR_MS).read()['reasons'])

    def test_lost_ack_and_restart_keep_payload_and_budget(self):
        worker = self.worker(max_attempts=2)
        worker.prepare('run', 100)
        self.client.lost_ack = True
        worker.once('run', 100)
        restarted = self.worker(self.client, max_attempts=2)
        restarted.once('run', 1100)
        with self.store.transaction() as db:
            status, attempts = db.execute("SELECT status,attempts FROM archive_outbox WHERE kind='anchor'").fetchone()
        self.assertEqual(('ACK', 2), (status, attempts))
        self.assertEqual(1, len(self.client.objects))

    def test_persistent_failures_exhaust_without_hiding_health(self):
        class Fails:
            def put(self, *args, **kwargs): raise Unavailable('synthetic failure')
        worker = Maintenance(self.store, Fails(), backup_interval_ms=24*HOUR_MS, max_attempts=1, retry_ms=1000)
        worker.prepare('run', 100)
        for _ in range(10): worker.once('run', 10000)
        health = worker.health('run', 10000).read()
        self.assertEqual(2, health['counts']['EXHAUSTED'])
        self.assertIn('ARCHIVE_DELIVERY_BLOCKED', health['reasons'])

    def test_backups_do_not_recursively_embed_previous_backups(self):
        worker = self.worker()
        worker.prepare('run', 100)
        size = len(export(self.store).payload)
        worker.prepare('run', 24*HOUR_MS+100)
        self.assertEqual(size, len(export(self.store).payload))
        self.store.quarantine('run')
        with self.assertRaises(Conflict): worker.prepare('run', 25*HOUR_MS)
        with self.assertRaises(Conflict): worker.once('run', 25*HOUR_MS)

    def test_archive_restore_preserves_quarantine_and_rejects_corruption(self):
        worker = self.worker()
        self.store.commit(self.batch())
        worker.prepare('run', 100)
        for _ in range(2): worker.once('run', 100)
        with self.store.transaction() as db:
            receipt = Document(bytes(db.execute("SELECT acknowledgement FROM archive_outbox WHERE kind='backup'").fetchone()[0]))
        backup = Document(worker.archive.fetch(receipt))
        with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
        restore(self.store, backup)
        self.assertTrue(self.store.load('run').read()['quarantined'])
        self.store.verify('run', minimum_version=1)

    def test_corrupted_outbox_blocks_remote_send(self):
        worker = self.worker()
        worker.prepare('run', 100)
        with self.store.transaction() as db: db.execute("UPDATE archive_outbox SET sha256='bad'")
        worker.once('run', 100)
        self.assertFalse(self.client.objects)
        self.assertIn('ARCHIVE_DELIVERY_BLOCKED', worker.health('run', 100).read()['reasons'])

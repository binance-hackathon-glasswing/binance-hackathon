from larp.contracts import ContractError, Document
from larp.runtime.maintenance import Maintenance, HOUR_MS
from larp.storage.archive import S3Archive
from larp.storage.backup import export, restore, restore_chain
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
        self.assertTrue(worker.once('run', 25*HOUR_MS))
        self.assertTrue(self.store.load('run').read()['quarantined'])

    def test_oversized_backup_does_not_prevent_queued_anchor_delivery(self):
        worker=self.worker(max_payload_bytes=1)
        with self.assertRaises(ContractError): worker.prepare('run',100)
        self.assertTrue(worker.once('run',100))
        self.assertEqual(1,len(self.client.objects))
        self.assertEqual(1,worker.health('run',100).read()['counts']['ACK'])

    def test_slow_archive_verification_does_not_lock_out_primary_commit(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from unittest.mock import patch
        from larp.storage.postgres import PostgresStore
        entered,release=Event(),Event()
        verify=self.store._verify
        def slow(db,run_id,run,*rest):
            if not entered.is_set():
                entered.set()
                if not release.wait(4): raise AssertionError('Verification not released')
            return verify(db,run_id,run,*rest)
        batch=self.batch('concurrent')
        primary=PostgresStore(self.store._dsn)
        worker=self.worker()
        with patch.object(self.store,'_verify',side_effect=slow), ThreadPoolExecutor(2) as pool:
            preparation=pool.submit(worker.prepare,'run',100)
            try:
                self.assertTrue(entered.wait(2))
                receipt=pool.submit(primary.commit,batch).result(timeout=2)
                self.assertEqual(1,receipt.read()['version'])
            finally:
                release.set()
            preparation.result(timeout=4)
        self.store.verify('run')

    def test_archive_restore_preserves_quarantine_and_rejects_corruption(self):
        worker = self.worker()
        self.store.commit(self.batch())
        worker.prepare('run', 100)
        for _ in range(2): worker.once('run', 100)
        with self.store.transaction() as db:
            receipt = Document(bytes(db.execute("SELECT acknowledgement FROM archive_outbox WHERE kind='backup'").fetchone()[0]))
        backup = worker.archive.fetch(receipt)  # a Backup.v2 segment (IDEA-094)
        with self.store.transaction() as db: db.execute('TRUNCATE runs CASCADE')
        restore_chain(self.store, [backup])
        self.assertTrue(self.store.load('run').read()['quarantined'])
        self.store.verify('run', minimum_version=1)

    def test_corrupted_outbox_blocks_remote_send(self):
        worker = self.worker()
        worker.prepare('run', 100)
        with self.store.transaction() as db: db.execute("UPDATE archive_outbox SET sha256='bad'")
        worker.once('run', 100)
        self.assertFalse(self.client.objects)
        self.assertIn('ARCHIVE_DELIVERY_BLOCKED', worker.health('run', 100).read()['reasons'])

    def test_audit_deadline_failure_remains_visible_to_monitoring(self):
        from tests.audit.test_protocol import event
        worker = self.worker()
        self.store.commit(self.batch(audit=[event()]))
        health = worker.health('run', 1791676800000+7200000).read()
        self.assertEqual(1, health['audit_deadline_breaches'])
        self.assertIn('AUDIT_DELIVERY_BLOCKED', health['reasons'])

    def test_archive_role_can_operate_without_mutating_financial_state(self):
        # Apply the production grants inside a rolled-back PG transaction, using
        # existing fixture roles and schema. No global roles survive the test.
        from pathlib import Path
        from larp.storage.backup import TABLES, select_sql
        script = Path('deploy/postgres/roles.sql').read_text()
        import psycopg
        with psycopg.connect(self.store._dsn) as db:
            if not db.execute("SELECT 1 FROM pg_roles WHERE rolname='rds_iam'").fetchone():
                db.execute('CREATE ROLE rds_iam')
            database = db.execute('SELECT current_database()').fetchone()[0]
            script = script.replace('ON DATABASE larp ', 'ON DATABASE '+database+' ')
            script = script.replace('SCHEMA public ', 'SCHEMA '+self.schema+' ')
            db.execute(script)
            # Prove upgrades revoke a pre-existing blanket uploader grant.
            db.execute('GRANT UPDATE ON audit_chunks TO larp_uploader')
            db.execute(script)
            db.execute("INSERT INTO audit_events VALUES('run','role-event','role-round','{}'::bytea,0)")
            db.execute("INSERT INTO audit_chunks(run_id,event_id,chunk_index,body) VALUES('run','role-event',0,'original'::bytea)")
            db.execute('SET LOCAL ROLE larp_uploader')
            db.execute("UPDATE audit_chunks SET attempts=1,status='ACK',next_ms=2,last_code='200',acknowledgement='{}'::bytea")
            for sql in ("UPDATE audit_chunks SET body='changed'::bytea",
                        "UPDATE audit_chunks SET event_id='changed'",
                        'UPDATE audit_chunks SET chunk_index=1'):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with db.transaction(): db.execute(sql)
            db.execute('RESET ROLE')
            db.execute("DELETE FROM audit_chunks WHERE event_id='role-event'")
            db.execute("DELETE FROM audit_events WHERE event_id='role-event'")
            db.execute('SET LOCAL ROLE larp_archive')
            run = self.store._run(db, 'run')
            self.store._verify(db, 'run', run)
            for table in TABLES:
                db.execute(*select_sql(db,table)).fetchall()  # the backup's own queries (signed bytes redacted)
            db.execute("INSERT INTO archive_clock VALUES('run',100)")
            db.execute("INSERT INTO archive_outbox(run_id,kind,slot_ms,payload,sha256) "
                       "VALUES('run','anchor',0,'{}'::bytea,'synthetic')")
            db.execute("UPDATE archive_outbox SET attempts=1 WHERE run_id='run'")
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with db.transaction(): db.execute("UPDATE runs SET projection='changed'::bytea")
            db.rollback()

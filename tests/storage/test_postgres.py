from concurrent.futures import ThreadPoolExecutor

from larp.contracts import Document
from larp.storage.postgres import Conflict,IntegrityError,Unavailable,doc
from larp.storage.backup import export,restore
from tests.support import DatabaseCase,job


class Transactions(DatabaseCase):
    def test_migrations_and_immutable_retry(self):
        self.store.migrate()
        batch=self.batch(); first=self.store.commit(batch)
        self.assertEqual(first,self.store.commit(batch))
        changed=batch.read(); changed['event']['changed']=True
        with self.assertRaises(IntegrityError):
            self.store.commit(doc(changed))
        self.assertEqual(1,self.store.load('run').read()['version'])

    def test_concurrent_reservations_only_one_wins(self):
        a=self.batch('a',reservation_deltas=[dict(intent_id='a',asset='USDT',units=80)])
        b=self.batch('b',reservation_deltas=[dict(intent_id='b',asset='USDT',units=80)])
        def attempt(batch):
            try:
                self.store.commit(batch); return 'ok'
            except Conflict:
                return 'conflict'
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(attempt,(a,b)))
        self.assertCountEqual(['ok','conflict'],results)
        with self.assertRaises(Conflict):
            self.store.commit(self.batch('c',reservation_deltas=[dict(intent_id='c',asset='USDT',units=21)]))

    def test_atomic_rollback_of_every_component(self):
        command=dict(command_id='c',expires_ms=999,kind='FAKE')
        batch=self.batch(jobs=[job()],commands=[command,dict(command,kind='CHANGED')],
                         reservation_deltas=[dict(intent_id='i',asset='USDT',units=20)])
        with self.assertRaises(IntegrityError):
            self.store.commit(batch)
        self.assertEqual(0,self.store.load('run').read()['version'])
        self.assertEqual([],self.store.load('run').read()['reservations'])
        self.assertEqual(0,self.store.metrics('run').read()['jobs_pending'])

    def test_zombie_and_quarantine_reject_commands(self):
        self.store.commit(self.batch(commands=[dict(command_id='c',expires_ms=999,kind='FAKE')]))
        self.assertEqual('c',self.store.command('run','c',self.epoch,100).read()['command_id'])
        old=self.batch('stale')
        self.store.takeover('run',self.epoch,offline=True)
        with self.assertRaises(Conflict): self.store.commit(old)
        with self.assertRaises(Conflict): self.store.command('run','c',self.epoch,100)
        self.store.quarantine('run')
        with self.assertRaises(Conflict): self.store.commit(self.batch('q'))

    def test_corrupt_tail_and_projection_fail_closed(self):
        self.store.commit(self.batch())
        with self.store.transaction() as db:
            db.execute("UPDATE events SET head=%s",('f'*64,))
        with self.assertRaises(IntegrityError): self.store.verify('run')
        with self.assertRaises(IntegrityError): self.store.takeover('run',self.epoch,offline=True)

    def test_corrupt_reservations_fail_before_new_commit(self):
        self.store.commit(self.batch(reservation_deltas=[dict(intent_id='i',asset='USDT',units=20)]))
        with self.store.transaction() as db:
            db.execute('UPDATE reservations SET units=0')
        with self.assertRaises(IntegrityError): self.store.commit(self.batch('next'))

    def test_changed_applied_migration_is_rejected(self):
        with self.store.transaction() as db:
            db.execute("UPDATE schema_migrations SET sha256='bad'")
        with self.assertRaises(IntegrityError): self.store.migrate()

    def test_database_write_failure_cannot_authorize(self):
        # Real PostgreSQL read-only transaction stands in for a failing durable write.
        from psycopg.conninfo import make_conninfo
        broken=type(self.store)(make_conninfo(self.store._dsn,options='-c search_path='+self.schema+' -c default_transaction_read_only=on'))
        with self.assertRaises(Unavailable): broken.commit(self.batch())
        self.assertEqual(0,self.store.load('run').read()['version'])

    def test_backup_checksum_and_stale_external_watermark(self):
        self.store.commit(self.batch())
        backup=export(self.store)
        with self.assertRaises(IntegrityError): restore(self.store,backup)
        with self.assertRaises(IntegrityError): self.store.verify('run',minimum_version=2)
        changed=backup.read(); changed['sha256']='0'*64
        with self.assertRaises(IntegrityError): restore(self.store,doc(changed))

    def test_restore_into_empty_schema_quarantines_and_preserves_outboxes(self):
        self.store.commit(self.batch(jobs=[job()],commands=[dict(command_id='c',expires_ms=999,kind='FAKE')]))
        backup=export(self.store)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        restore(self.store,backup)
        value=self.store.load('run').read()
        self.assertTrue(value['quarantined'])
        self.assertEqual(1,value['version'])
        self.assertEqual(self.epoch+1,value['epoch'])
        self.store.verify('run')
        with self.assertRaises(Conflict): self.store.command('run','c',value['epoch'],100)

from larp.audit.delivery import DeliveryWorker
from larp.runtime.fixtures import FakeReceiver
from larp.storage.postgres import IntegrityError,doc
from tests.support import DatabaseCase
from tests.audit.test_protocol import event


class Delivery(DatabaseCase):
    def test_non_object_receiver_bodies_retry_then_ack_without_crashing(self):
        self.store.commit(self.batch(audit=[event()]))
        class Receiver(FakeReceiver):
            body=[]
            def deliver(self,value): return doc(dict(status_code=200,body=self.body))
        receiver=Receiver()
        worker=DeliveryWorker(self.store,receiver,retry_ms=1,max_backoff_ms=1)
        for tick,body in enumerate(([], 'ok', None, 12)):
            receiver.body=body
            self.assertTrue(worker.once('run',self.epoch,tick))
        DeliveryWorker(self.store,FakeReceiver(),retry_ms=1).once('run',self.epoch,5)
        with self.store.transaction() as db:
            self.assertEqual(('ACK',5),db.execute('SELECT status,attempts FROM audit_chunks').fetchone())

    def test_lost_ack_restart_has_one_immutable_event(self):
        e=event(text='🙂'*40000)
        self.store.commit(self.batch(audit=[e]))
        receiver=FakeReceiver(lose_ack=True)
        worker=DeliveryWorker(self.store,receiver,retry_ms=1)
        worker.once('run',self.epoch,100)
        restarted=DeliveryWorker(type(self.store)(self.store._dsn),receiver,retry_ms=1)
        for tick in range(101,120):
            restarted.once('run',self.epoch,tick)
        self.assertEqual(len(e.read()['chunks']),len(receiver.stored))
        self.assertEqual(0,self.store.metrics('run').read()['audit_pending'])

    def test_permanent_and_transient_errors_remain_visible(self):
        for code in (400,401,413,429,500,503,0):
            identity='e'+str(code)
            self.store.commit(self.batch(identity,audit=[event(identity,identity)]))
        receiver=FakeReceiver()
        worker=DeliveryWorker(self.store,receiver,retry_ms=1000)
        for index,code in enumerate((0,400,401,413,429,500,503)):
            receiver.code=code
            worker.once('run',self.epoch,100+index)
        with self.store.transaction() as db:
            statuses=dict(db.execute('SELECT event_id,status FROM audit_chunks'))
        self.assertEqual('PERMANENT',statuses['e400'])
        self.assertEqual('PERMANENT',statuses['e401'])
        self.assertEqual('PERMANENT',statuses['e413'])
        self.assertEqual('PENDING',statuses['e429'])
        self.assertEqual(7,len(worker.deadline_breaches('run',1791676800000+7200000)))

    def test_r1_transient_failures_never_exhaust_and_deliver_once_the_receiver_recovers(self):
        """IDEA-047 R1: replaces the old exhaustion test; a chunk given up on would latch a delivery HALT."""
        self.store.commit(self.batch(audit=[event()]))
        receiver=FakeReceiver(code=503)
        worker=DeliveryWorker(self.store,receiver,retry_ms=1,max_backoff_ms=4)
        for tick in range(20):
            self.assertTrue(worker.once('run',self.epoch,tick*10))
        with self.store.transaction() as db:
            self.assertEqual(('PENDING',20),db.execute('SELECT status,attempts FROM audit_chunks').fetchone())
        receiver.code=200
        self.assertTrue(worker.once('run',self.epoch,1000))
        with self.store.transaction() as db:
            self.assertEqual(('ACK',21),db.execute('SELECT status,attempts FROM audit_chunks').fetchone())
        self.assertEqual(worker.status('run')['delivered'],[event().read()['event_id']])

    def test_r1_backoff_doubles_up_to_its_cap(self):
        worker=DeliveryWorker(self.store,FakeReceiver(code=503),retry_ms=1000,max_backoff_ms=5000)
        self.assertEqual([worker.backoff_ms(n) for n in (1,2,3,4,5,50,10**6)],[1000,2000,4000,5000,5000,5000,5000])
        self.store.commit(self.batch(audit=[event()]))
        for now in (100,1100,3100):
            worker.once('run',self.epoch,now)
            with self.store.transaction() as db:
                attempts,next_ms=db.execute('SELECT attempts,next_ms FROM audit_chunks').fetchone()
            self.assertEqual(next_ms,now+worker.backoff_ms(attempts))
        self.assertFalse(worker.once('run',self.epoch,3100+3999))  # not due before its backoff ends
        for invalid in (dict(retry_ms=0),dict(retry_ms=2,max_backoff_ms=1),dict(retry_ms=1.5),dict(max_attempts=8)):
            with self.subTest(invalid=invalid),self.assertRaises((ValueError,TypeError)):
                DeliveryWorker(self.store,FakeReceiver(),**invalid)

    def test_same_audit_id_different_bytes_rolls_back(self):
        self.store.commit(self.batch(audit=[event()]))
        with self.assertRaises(IntegrityError):
            self.store.commit(self.batch('other',audit=[event(text='changed')]))
        self.assertEqual(1,self.store.load('run').read()['version'])

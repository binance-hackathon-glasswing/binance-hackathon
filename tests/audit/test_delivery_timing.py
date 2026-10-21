"""LD14-I01: per-attempt delivery timing for the rehearsal ACK measurement; it never changes delivery."""
from larp.audit.delivery import DeliveryWorker
from larp.runtime.fixtures import FakeReceiver
from tests.audit.test_protocol import event
from tests.support import DatabaseCase


class DeliveryTiming(DatabaseCase):
    def status(self):
        with self.store.transaction() as db:
            return db.execute('SELECT status,attempts FROM audit_chunks').fetchone()

    def test_each_attempt_reports_outcome_and_duration_without_payload(self):
        self.store.commit(self.batch(audit=[event()]))
        seen = []
        receiver = FakeReceiver(code=503)
        worker = DeliveryWorker(self.store, receiver, retry_ms=1, max_backoff_ms=1, observe=seen.append)
        worker.once('run', self.epoch, 10)
        receiver.code = 200
        worker.once('run', self.epoch, 20)
        self.assertEqual([(s['attempt'], s['code'], s['status']) for s in seen], [(1, 503, 'PENDING'), (2, 200, 'ACK')])
        for s in seen:
            self.assertEqual(set(s), {'event_id', 'chunk_index', 'attempt', 'code', 'status', 'duration_ms',
                                      'attempt_clock_ms', 'wall_ms'})
            self.assertGreaterEqual(s['duration_ms'], 0)
        self.assertEqual([s['attempt_clock_ms'] for s in seen], [10, 20])
        self.assertEqual(self.status(), ('ACK', 2))

    def test_a_failing_observer_cannot_change_delivery(self):
        self.store.commit(self.batch(audit=[event()]))

        def broken(attempt):
            raise RuntimeError('observer down')
        self.assertTrue(DeliveryWorker(self.store, FakeReceiver(), retry_ms=1, observe=broken).once('run', self.epoch, 10))
        self.assertEqual(self.status(), ('ACK', 1))

    def test_transport_exception_reports_code_zero(self):
        self.store.commit(self.batch(audit=[event()]))
        seen = []

        class Down(FakeReceiver):
            def deliver(self, value):
                raise ConnectionError('down')
        DeliveryWorker(self.store, Down(), retry_ms=1, observe=seen.append).once('run', self.epoch, 10)
        self.assertEqual((seen[0]['code'], seen[0]['status']), (0, 'PENDING'))

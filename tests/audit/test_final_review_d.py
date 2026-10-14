"""IDEA-049 final review D: round-log delivery after non-transient 4xx responses (D-REQ-014, 015, 075; #50).

Criteria pre-registered in docs/ledger/IDEA-049-D.md §4.2 before these tests ran.
"""

from larp.audit.delivery import DeliveryWorker
from larp.runtime.coordinator import halt_reasons
from larp.runtime.fixtures import FakeReceiver
from larp.runtime.supervision import Guard
from tests.audit.test_protocol import event
from tests.support import DatabaseCase

DAY_MS = 86_400_000


class Responses(FakeReceiver):
    """Answers each delivery with the next scripted status code, then 200 STORED."""

    def __init__(self, *codes):
        super().__init__()
        self.codes, self.bodies = list(codes), []

    def deliver(self, value):
        self.bodies.append(value.read()['body'])
        self.code = self.codes.pop(0) if self.codes else 200
        return super().deliver(value)


class NonTransientRejections(DatabaseCase):
    def chunk(self):
        with self.store.transaction() as db:
            return db.execute('SELECT status,attempts,next_ms,acknowledgement IS NOT NULL FROM audit_chunks').fetchone()

    def test_d_req_014_a_401_then_recovery_acks_and_clears_the_halt(self):
        logged = event()
        self.store.commit(self.batch(audit=[logged]))
        timestamp = logged.read()['timestamp_ms']
        after_deadline = timestamp + 2 * DAY_MS
        receiver = Responses(401)  # e.g. TIMESTAMP_SKEW while the host clock was off
        worker = DeliveryWorker(self.store, receiver, retry_ms=1000, max_backoff_ms=4000)
        guard = Guard(self.store, 'run', max_failures=3, clear_after=1)
        self.assertTrue(worker.once('run', self.epoch, after_deadline))
        self.assertEqual(guard.evaluate(after_deadline), ['HALT:DELIVERY_DEADLINE'])
        # The clock is fixed and the receiver accepts the same bytes on a later cycle, with nobody acting.
        later = after_deadline + 60_000
        self.assertTrue(worker.once('run', self.epoch, later))
        status, attempts, _, acknowledged = self.chunk()
        self.assertEqual((status, attempts, acknowledged), ('ACK', 2, True))
        self.assertEqual(receiver.bodies[0], receiver.bodies[1])  # identical bytes resent
        self.assertEqual(worker.status('run')['delivered'], [logged.read()['event_id']])
        self.assertEqual(guard.evaluate(later), ['CLEAR:DELIVERY_DEADLINE'])
        self.assertEqual(halt_reasons(self.store.load('run').read()['projection']), [])

    def chunks(self):
        with self.store.transaction() as db:
            return {r[0]: r[1:] for r in db.execute('SELECT event_id,status,attempts,next_ms FROM audit_chunks')}

    def test_d_req_014_auth_and_conflict_4xx_retry_with_backoff_and_stay_visible(self):
        codes = {f'e{code}': code for code in (401, 403, 408, 409)}
        for identity in codes:
            self.store.commit(self.batch(identity, audit=[event(identity, identity)]))
        receiver = ByEvent(codes)
        worker = DeliveryWorker(self.store, receiver, retry_ms=1000, max_backoff_ms=4000)
        delays = {identity: [] for identity in codes}
        now = 0
        for _ in range(4):
            due = {identity: row[2] for identity, row in self.chunks().items()}
            now = max(due.values()) if any(due.values()) else 0
            for _ in codes:
                self.assertTrue(worker.once('run', self.epoch, now))
            for identity, (status, attempts, next_ms) in self.chunks().items():
                with self.subTest(code=codes[identity], attempts=attempts):
                    self.assertEqual(status, 'PENDING')
                delays[identity].append(next_ms - now)
        for identity, values in delays.items():
            with self.subTest(code=codes[identity]):
                self.assertEqual(values, [1000, 2000, 4000, 4000])  # grows, then capped
        status = worker.status('run')
        self.assertEqual(status['delivered'], [])
        self.assertEqual(set(status['events'].values()), {'PENDING'})

    def test_d_req_015_payload_rejections_stay_failed_and_are_not_resent(self):
        codes = {'e400': 400, 'e413': 413}
        for identity in codes:
            self.store.commit(self.batch(identity, audit=[event(identity, identity)]))
        receiver = ByEvent(codes)
        worker = DeliveryWorker(self.store, receiver, retry_ms=1, max_backoff_ms=1)
        self.assertTrue(worker.once('run', self.epoch, 0))
        self.assertTrue(worker.once('run', self.epoch, 0))
        for now in (10, 10_000, DAY_MS):
            self.assertFalse(worker.once('run', self.epoch, now))
        self.assertEqual(sorted(receiver.sent), ['e400', 'e413'])  # each sent once, never again
        self.assertEqual({k: v[:2] for k, v in self.chunks().items()},
                         {'e400': ('PERMANENT', 1), 'e413': ('PERMANENT', 1)})
        self.assertEqual(worker.status('run')['failed'], ['e400', 'e413'])


class ByEvent(FakeReceiver):
    """Answers every delivery of an event with that event's scripted status code."""

    def __init__(self, codes):
        super().__init__()
        self.codes, self.sent = codes, []

    def deliver(self, value):
        identity = value.read()['event_id']
        self.sent.append(identity)
        self.code = self.codes[identity]
        return super().deliver(value)

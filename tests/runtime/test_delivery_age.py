"""D-DN-04 delivery-age guard (IDEA-049-D LD13, criteria G1-G9) on real PostgreSQL.

B values here are test values; the adopted bound waits for measured dispatch/ACK delays (Isaac, LD14).
"""
import unittest
from unittest.mock import patch

from larp.audit.delivery import DeliveryWorker
from larp.contracts import ContractError
from larp.runtime.fixtures import FakeReceiver
from larp.runtime.service import runtime_guard, validate_config
from larp.storage.postgres import Conflict, doc
from tests.runtime import test_supervision as sv
from tests.support import request

B = 1000
NOW = sv.NOW


class EmptyOk:
    """A receiver that answers 200 without STORED: never a positive acknowledgement."""

    def deliver(self, event):
        return doc(dict(status_code=200, body={}))


class DeliveryAge(sv.Supervision):
    def age_guard(self, bound=B):
        return self.guard(delivery_age_ms=bound)

    def logged(self, round_id, at):
        self.coordinator(clock=at).start(round_id, request('HOLD', job='job-' + round_id), at)

    def pending(self):
        with self.store.transaction() as db:
            return db.execute("SELECT count(*) FROM audit_chunks WHERE run_id='run' AND status<>'ACK'").fetchone()[0]

    def test_g1_off_without_a_bound(self):
        self.logged('r1', NOW)
        self.assertEqual(self.guard().evaluate(NOW + 10 * B), [])
        self.assertNotIn('halt', self.projection())

    def test_g2_g6_exact_boundary_and_restart(self):
        self.logged('r1', NOW)
        self.assertEqual(self.age_guard().evaluate(NOW + B - 1), [])
        self.assertEqual(self.age_guard().evaluate(NOW + B), ['HALT:DELIVERY_AGE'])  # a fresh Guard: a restart
        self.assertEqual(self.age_guard().evaluate(NOW + B + 1), [])  # still halted, not re-raised

    def test_g3_the_halt_blocks_signing(self):
        c = self.coordinator()
        c.start('r1', request('BUY'), NOW)  # an open round with a pending command and no log yet (G8 too)
        command_id = self.projection()['round_records']['r1']['plan']['intents'][0]['intent_id']
        self.assertEqual(self.age_guard().evaluate(NOW + B), ['HALT:DELIVERY_AGE'])
        with self.assertRaises(Conflict):
            self.store.command('run', command_id, self.epoch, NOW + B)

    def test_g4_a_200_without_stored_is_not_an_ack(self):
        self.logged('r1', NOW)
        DeliveryWorker(self.store, EmptyOk(), retry_ms=1).once('run', self.epoch, NOW + 1)
        self.assertGreater(self.pending(), 0)
        self.assertEqual(self.age_guard().evaluate(NOW + B), ['HALT:DELIVERY_AGE'])

    def test_g5_clears_only_when_every_overdue_log_is_acked(self):
        self.logged('r1', NOW)
        self.logged('r2', NOW + 1)
        self.assertEqual(self.age_guard().evaluate(NOW + B + 5), ['HALT:DELIVERY_AGE'])
        worker = DeliveryWorker(self.store, FakeReceiver(), retry_ms=1)
        worker.once('run', self.epoch, NOW + B + 6)  # one chunk delivered; one overdue log remains
        self.assertGreater(self.pending(), 0)
        self.assertEqual(self.age_guard().evaluate(NOW + B + 7), [])
        while worker.once('run', self.epoch, NOW + B + 8):
            pass
        self.assertEqual(self.pending(), 0)
        self.assertEqual(self.age_guard().evaluate(NOW + B + 9), ['CLEAR:DELIVERY_AGE'])
        self.assertNotIn('halt', self.projection())

    def test_g7_a_future_timestamp_fails_closed(self):
        # Rewriting a stored log would trip the journal integrity check (QUARANTINED), and a log made under a later
        # clock trips the CLOCK HALT first. So the guard's own branch is exercised with the query patched.
        self.logged('r1', NOW)
        for k, times in enumerate(([NOW + 10 * B], [None])):
            at = NOW + 10 * k + 1
            with self.subTest(times=times), patch('larp.runtime.supervision.pending_log_times', return_value=times):
                self.assertEqual(self.age_guard().evaluate(at), ['HALT:DELIVERY_AGE'])
                self.assertEqual(self.age_guard().evaluate(at + 1), [])  # does not clear while it remains
            with patch('larp.runtime.supervision.pending_log_times', return_value=[]):
                self.assertEqual(self.age_guard().evaluate(at + 2), ['CLEAR:DELIVERY_AGE'])

    def test_g8_an_open_round_counts_from_its_start(self):
        self.coordinator().start('r1', request('BUY'), NOW)
        self.assertFalse(self.projection()['round_records']['r1'].get('logged'))
        self.assertEqual(self.age_guard().evaluate(NOW + B - 1), [])
        self.assertEqual(self.age_guard().evaluate(NOW + B), ['HALT:DELIVERY_AGE'])

    def test_clock_rollback_after_restart_cannot_clear_an_overdue_log(self):
        self.logged('r1', NOW)
        self.assertEqual(self.age_guard().evaluate(NOW + B), ['HALT:DELIVERY_AGE'])
        self.assertGreater(self.pending(), 0)
        self.assertEqual(self.age_guard().evaluate(NOW + B - 1), ['HALT:CLOCK'])
        self.assertIn('DELIVERY_AGE', self.projection()['halt']['reasons'])
        self.assertIn('CLOCK', self.projection()['halt']['reasons'])
        self.assertEqual(self.age_guard().evaluate(NOW + B), [])
        self.assertIn('DELIVERY_AGE', self.projection()['halt']['reasons'])

    def test_multipart_out_of_order_acks_keep_the_original_pending_age(self):
        from tests.audit.test_protocol import event
        audit = event(text='x' * 160000)
        self.assertGreater(len(audit.read()['chunks']), 1)
        self.store.commit(self.batch(audit=[audit]))
        self.assertEqual(self.age_guard().evaluate(NOW + B), ['HALT:DELIVERY_AGE'])

        class DelayFirst(FakeReceiver):
            first = True

            def deliver(self, value):
                if self.first:
                    self.first = False
                    return doc(dict(status_code=0, body={}))
                return super().deliver(value)

        worker = DeliveryWorker(self.store, DelayFirst(), retry_ms=100, max_backoff_ms=100)
        while worker.once('run', self.epoch, NOW + B + 1):
            pass
        self.assertEqual(self.pending(), 1)  # later chunks ACKed, first chunk's retry is still waiting
        self.assertEqual(self.age_guard().evaluate(NOW + B + 2), [])
        self.assertTrue(worker.once('run', self.epoch, NOW + B + 101))
        self.assertEqual(self.pending(), 0)
        self.assertEqual(self.age_guard().evaluate(NOW + B + 102), ['CLEAR:DELIVERY_AGE'])

    def test_g9_config_and_service_wiring(self):
        base = dict(schema='RuntimeService.v1', run_id='run', build_id='b', max_failures=3, clear_after=2,
                    interval_seconds=1, database_dsn_file='/dev/null')
        validate_config(dict(base))
        validate_config(dict(base, delivery_age_halt_seconds=7200))
        for bad in (0, -1, 1.5, '7200'):
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                validate_config(dict(base, delivery_age_halt_seconds=bad))
        self.assertEqual(runtime_guard(self.store, dict(base, delivery_age_halt_seconds=7)).delivery_age_ms, 7000)
        self.assertIsNone(runtime_guard(self.store, base).delivery_age_ms)


for name in [n for n in vars(sv.Supervision) if n.startswith('test_')]:
    setattr(DeliveryAge, name, None)  # Supervision's own tests run in their module


if __name__ == '__main__':
    unittest.main()

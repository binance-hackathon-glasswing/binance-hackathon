"""S5-COST03: preparation may persist only with fresh guards after slow venue I/O."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from larp.execution import Blocked, Conflict, Executor
from tests.execution_fixtures import SQLiteFixture, FakeGuards, FakeVenue, FakeSigner, FakeDecoder, intent


class FreshPreparationFence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SQLiteFixture(str(Path(self.temp.name) / 'state.sqlite'))
        self.addCleanup(self.store.close)
        self.guards = FakeGuards(self.store)
        self.signer = FakeSigner(self.store)
        self.callback = lambda: None
        outer = self
        class Venue(FakeVenue):
            def estimate_gas(self, payload):
                result = super().estimate_gas(payload)
                outer.callback()
                return result
        self.venue = Venue(self.store)
        self.executor = Executor(self.store, self.guards, self.venue, self.signer, FakeDecoder())
        self.intent = intent(max_prepare_probes=8)
        self.executor.create(self.intent, 10)

    def test_harmless_journal_write_during_io_preserves_one_probe_and_prepares(self):
        self.callback = self.store.advance_authority
        state = self.executor.prepare(self.intent.key, 11)
        self.assertEqual(state.attempts[-1].state, 'PREPARED')
        self.assertEqual(state.prepare_probes, 1)
        self.assertEqual(self.signer.calls, 0)
        self.assertFalse(self.venue.broadcasts)

    def test_changed_risk_reservation_version_clock_and_health_refuse(self):
        for fact in ('risk_valid', 'reservation_valid', 'version_valid', 'clock_trusted', 'health_valid'):
            with self.subTest(fact=fact):
                self.guards.changes.clear()
                self.callback = lambda: self.guards.change(**{fact: False})
                state = self.executor.prepare(self.intent.key, 11)
                self.assertFalse(state.attempts)
                self.assertIsNotNone(state.blocked_reason)
        self.assertEqual(self.signer.calls, 0)

    def test_changed_owner_is_never_silently_adopted(self):
        self.callback = lambda: self.store.advance_authority(epoch=True)
        with self.assertRaises(Conflict):
            self.executor.prepare(self.intent.key, 11)
        self.assertFalse(self.store.load(self.intent.key).attempts)

    def test_changed_nonce_cannot_prepare_the_old_payload(self):
        def change_nonce():
            self.guards.nonce += 1
        self.callback = change_nonce
        state = self.executor.prepare(self.intent.key, 11)
        self.assertFalse(state.attempts)
        self.assertIn('nonce', state.blocked_reason)

    def test_completion_clock_cannot_revive_expired_authority(self):
        self.executor = Executor(self.store, self.guards, self.venue, self.signer, FakeDecoder(), clock_s=lambda: 2000)
        state = self.executor.prepare(self.intent.key, 11)
        self.assertFalse(state.attempts)
        self.assertEqual(state.last_observed_at, 2000)

    def test_race_after_refresh_still_fails_compare_and_swap(self):
        original = self.store.commit
        def racing(previous, current, event, epoch, version):
            if event['type'] == 'PREPARED':
                self.store.advance_authority()
            return original(previous, current, event, epoch, version)
        self.store.commit = racing
        with self.assertRaises(Conflict):
            self.executor.prepare(self.intent.key, 11)
        self.assertFalse(self.store.load(self.intent.key).attempts)

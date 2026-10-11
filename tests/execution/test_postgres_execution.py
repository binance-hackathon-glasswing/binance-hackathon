"""Disposable PostgreSQL W04 faults. No Ethereum signatures or networking."""
from dataclasses import replace

from larp.execution import Conflict, Executor
from larp.execution_live.store import ExecutionStore
from tests.support import DatabaseCase
from tests.execution_fixtures import (FakeDecoder, FakeGuards, FakeSigner, FakeVenue,
                                      WALLET, finalized, intent)


class RegistrySigner:
    mode = 'fake'
    def __init__(self, store):
        self.store = store
    def sign(self, attempt_id, payload, epoch, version):
        prior = self.lookup(attempt_id, payload.hash)
        return prior or self.store.put_if_absent(attempt_id, payload.hash, FakeSigner.expected(payload), epoch, version)
    def verify(self, payload, signed):
        return signed == FakeSigner.expected(payload)
    def lookup(self, attempt_id, payload_hash):
        return self.store.lookup(attempt_id, payload_hash)


class PostgresExecutionTests(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.execution_store = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.execution_store.install_test_schema()
        self.guards = FakeGuards(self.execution_store)
        self.venue = FakeVenue(self.execution_store)
        self.signer = RegistrySigner(self.execution_store)
        self.restart()

    def restart(self):
        adapter = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.executor = Executor(adapter, self.guards, self.venue, RegistrySigner(adapter), FakeDecoder())

    def prepared(self):
        i = intent()
        self.executor.create(i, 10)
        self.executor.prepare(i.key, 11)
        self.executor.authorize(i.key, 12)
        return i.key

    def test_crash_before_sign_and_after_sign(self):
        key = self.prepared()
        self.restart()
        signed = self.executor.sign(key, 13)
        self.restart()
        self.assertEqual(self.executor.sign(key, 14).attempts, signed.attempts)
        self.assertFalse(self.venue.broadcasts)

    def test_crash_after_broadcast_and_after_receipt(self):
        key = self.prepared()
        self.executor.sign(key, 13)
        sent = self.executor.broadcast(key, 14)
        self.restart()
        self.executor.broadcast(key, 15)
        self.assertEqual(len(self.venue.broadcasts), 1)
        a = sent.attempts[-1]
        self.venue.outcomes[a.tx_hash] = finalized(a)
        final = self.executor.reconcile(key, 17)
        self.assertEqual(final.attempts[-1].state, 'FINAL_SUCCESS')
        self.restart()
        self.assertEqual(self.executor.reconcile(key, 20), final)
        self.assertEqual(len(self.venue.broadcasts), 1)

    def test_wallet_barrier_and_stale_cas(self):
        state = self.executor.create(intent(), 10)
        with self.assertRaises(Conflict):
            self.executor.create(intent(intent_id='other'), 11)
        e, v = self.execution_store.authority()
        self.execution_store.commit(state, replace(state, blocked_reason='probe'), {'type':'PROBE'}, e, v)
        with self.assertRaises(Conflict):
            self.execution_store.commit(state, state, {'type':'STALE'}, e, v)

    def test_registry_survives_restart_and_rejects_changed_payload(self):
        key = self.prepared()
        state = self.executor.sign(key, 13)
        attempt = state.attempts[-1]
        self.restart()
        self.assertEqual(self.executor.signer.lookup(attempt.attempt_id, attempt.payload.hash).tx_hash, attempt.tx_hash)
        with self.assertRaises(Conflict):
            self.executor.signer.lookup(attempt.attempt_id, 'changed')

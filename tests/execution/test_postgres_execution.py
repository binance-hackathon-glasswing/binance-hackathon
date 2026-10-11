"""Disposable PostgreSQL W04 faults. No Ethereum signatures or networking."""
from dataclasses import replace
import os
import subprocess
import sys

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

    def crash(self, stage, key):
        result = subprocess.run([sys.executable, '-m', 'tests.execution.crash_worker', stage, key],
                                env={'LARP_TEST_DATABASE_URL': self.store._dsn},
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 77, 'Crash fixture did not reach its intended boundary')
        self.restart()

    def test_process_death_recovers_signature_and_possible_broadcast(self):
        key = self.prepared()
        self.crash('BEFORE_SIGN', key)
        self.assertEqual(self.execution_store.load(key).attempts[-1].state, 'AUTHORIZED')
        self.crash('AFTER_SIGN', key)
        self.assertEqual(self.execution_store.load(key).attempts[-1].state, 'AUTHORIZED')
        signed = self.executor.recover_signature(key, 25)
        self.assertEqual(signed.attempts[-1].state, 'SIGNED_DURABLE')
        self.crash('AFTER_BROADCAST', key)
        sent = self.execution_store.load(key)
        self.assertEqual(sent.attempts[-1].state, 'BROADCAST_ATTEMPTED')
        self.executor.broadcast(key, 31)
        self.assertFalse(self.venue.broadcasts)
        self.crash('AFTER_RECEIPT', key)
        self.assertEqual(self.execution_store.load(key).attempts[-1].state, 'BROADCAST_ATTEMPTED')
        self.venue.outcomes[sent.attempts[-1].tx_hash] = finalized(sent.attempts[-1])
        final = self.executor.reconcile(key, 40)
        self.assertEqual(final.attempts[-1].state, 'FINAL_SUCCESS')
        self.assertEqual(final.attempts[-1].finalized_at, 40)
        self.assertFalse(self.venue.broadcasts)

    def test_swap_process_death_never_reissues_or_rebroadcasts(self):
        key = self.prepared()
        self.executor.sign(key, 13)
        state = self.executor.broadcast(key, 14)
        self.venue.outcomes[state.attempts[-1].tx_hash] = finalized(state.attempts[-1])
        self.executor.reconcile(key, 17)
        self.guards.nonce = 1
        self.executor.prepare(key, 20)
        self.executor.authorize(key, 21)
        self.crash('AFTER_SIGN', key)
        recovered = self.executor.recover_signature(key, 25)
        self.assertEqual(recovered.attempts[-1].step, 'SWAP')
        self.crash('AFTER_BROADCAST', key)
        sent = self.execution_store.load(key)
        self.executor.broadcast(key, 31)
        self.assertEqual(len(self.venue.broadcasts), 1)  # Only the parent's earlier approval.
        self.crash('AFTER_RECEIPT', key)
        self.venue.outcomes[sent.attempts[-1].tx_hash] = finalized(sent.attempts[-1])
        final = self.executor.reconcile(key, 40)
        self.assertEqual(final.status, 'COMPLETED')
        self.assertEqual(len(self.venue.broadcasts), 1)

    def test_final_observation_is_immutable_across_restart(self):
        e, v = self.execution_store.authority()
        fact = dict(event_id='fact', run_id='run', kind='APPROVAL', settlement='FINAL')
        self.execution_store.put_observation(fact, e, v)
        self.restart()
        self.assertEqual(self.executor.store.lookup_observation('fact'), fact)
        with self.assertRaises(Conflict):
            self.execution_store.put_observation(dict(fact, finalized_height=999), e, v)

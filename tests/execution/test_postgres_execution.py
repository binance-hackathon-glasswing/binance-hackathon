"""Disposable PostgreSQL W04 faults. No Ethereum signatures or networking."""
from dataclasses import replace
import os
import subprocess
import sys
import importlib.util
import unittest

from larp.execution import Conflict, Executor
from larp.execution_live.store import ExecutionStore
from larp.execution_live.service import ExecutionService
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


class ExecutionGuards(FakeGuards):
    def snapshot(self, economic_intent, now):
        return replace(super().snapshot(economic_intent, now),
                       execution_version=self.store.execution_authority()[1])


class PostgresExecutionTests(DatabaseCase):
    def setUp(self):
        super().setUp()
        self.execution_store = ExecutionStore(self.store, run_id='run', wallet=WALLET)
        self.execution_store.install_test_schema()
        self.guards = ExecutionGuards(self.execution_store)
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
        e, v = self.execution_store.execution_authority()
        fact = dict(event_id='fact', run_id='run', kind='APPROVAL', settlement='FINAL')
        self.execution_store.put_observation(fact, e, v)
        self.restart()
        self.assertEqual(self.executor.store.lookup_observation('fact'), fact)
        with self.assertRaises(Conflict):
            self.execution_store.put_observation(dict(fact, finalized_height=999), e, v)

    def service(self, publish=None):
        epoch, version = self.execution_store.execution_authority()
        return ExecutionService(store=self.store,executor=self.executor,mapping={},
                                observe=publish or (lambda _:None),wallet_id='wallet',
                                epoch=epoch,authority_version=version)

    def test_runtime_commit_does_not_invalidate_authorized_attempt(self):
        key=self.prepared()
        self.store.commit(self.batch('ordinary-runtime-commit'))
        result=self.service().advance(key,13)
        self.assertEqual(result.attempts[-1].state,'SIGNED_DURABLE')

    def test_service_recovers_signature_after_takeover_without_reissuing(self):
        key=self.prepared();signed=self.executor.sign(key,13)
        stale=self.service()
        self.store.takeover('run',self.epoch,offline=True)
        from larp.storage.postgres import Conflict as StorageConflict
        with self.assertRaises(StorageConflict):stale.advance(key,14)
        service=self.service()
        recovered=service.advance(key,15)
        self.assertEqual(recovered.attempts[-1].tx_hash,signed.attempts[-1].tx_hash)
        self.assertEqual(recovered.attempts[-1].epoch,self.epoch+1)
        service.advance(key,16)
        self.assertEqual(len(self.venue.broadcasts),1)

    def test_service_recovers_registry_commit_and_publication_crash(self):
        key=self.prepared()
        state=self.execution_store.load(key);a=state.attempts[-1]
        self.signer.sign(a.attempt_id,a.payload,a.epoch,a.guard_version)
        self.assertEqual(self.service().advance(key,13).attempts[-1].state,'SIGNED_DURABLE')
        publications=[]
        def lost_ack(fact):
            publications.append(fact)
            raise ConnectionError('synthetic publication crash')
        with self.assertRaises(ConnectionError):self.service(lost_ack).advance(key,14)
        self.service(publications.append).advance(key,15)
        self.assertEqual(publications[0],publications[1])
        self.assertEqual(len(self.venue.broadcasts),1)

    def test_expired_unbroadcast_signature_is_revoked_but_possible_send_cannot_abort(self):
        key=self.prepared();signed=self.executor.sign(key,13)
        self.store.takeover('run',self.epoch,offline=True)
        result=self.service().advance(key,1001)
        self.assertEqual(result.status,'ABORTED')
        a=signed.attempts[-1]
        with self.assertRaises(Conflict):self.execution_store.lookup(a.attempt_id,a.payload.hash)
        from larp.execution import Signed
        e,v=self.execution_store.execution_authority()
        with self.assertRaises(Conflict):self.execution_store.check_broadcast(Signed(a.raw_hex,a.tx_hash),e,v)
        facts=[]
        service=self.service(facts.append)
        service.advance(key,1002)
        service.round_terminal=lambda _:True
        service.advance(key,1003)
        self.assertEqual(facts[0],facts[1])
        self.assertEqual(facts[0]['kind'],'NOT_SUBMITTED')

    def test_expired_prepared_command_releases_barrier_and_publishes_stable_abort(self):
        i = intent()
        self.executor.create(i, 10)
        self.executor.prepare(i.key, 11)
        self.restart()
        facts = []
        service = self.service(facts.append)
        state = service.advance(i.key, i.valid_until)
        self.assertEqual(state.status, 'ABORTED')
        self.assertEqual(state.attempts[-1].state, 'ABORTED')
        self.assertEqual(state.last_observed_at, i.valid_until)
        self.assertIsNone(state.attempts[-1].tx_hash)
        self.assertFalse(self.venue.broadcasts)
        service.advance(i.key, i.valid_until + 1)
        service.advance(i.key, i.valid_until + 2)
        self.assertEqual(facts[0], facts[1])
        self.assertEqual(facts[0]['kind'], 'NOT_SUBMITTED')
        self.assertEqual(facts[0]['observed_at'], '1970-01-01T00:16:40+00:00')
        second = intent(intent_id='second', valid_until=2000)
        self.assertEqual(self.executor.create(second, 1003).status, 'ACTIVE')

    def test_expired_possible_send_keeps_wallet_barrier(self):
        key = self.prepared()
        self.executor.sign(key, 13)
        self.executor.broadcast(key, 14)
        state = self.service().advance(key, 1001)
        self.assertEqual(state.status, 'ACTIVE')
        self.assertIsNotNone(state.attempts[-1].broadcast_at)
        with self.assertRaises(Conflict):
            self.executor.create(intent(intent_id='other', valid_until=2000), 1002)
        self.assertEqual(len(self.venue.broadcasts), 1)

    @unittest.skipUnless(importlib.util.find_spec('eth_account'),'signer dependency supplied by integration CI lock')
    def test_real_ephemeral_signer_uses_postgres_registry(self):
        from eth_account import Account
        from larp.signer.local import LocalSigner,verify
        account=Account.create()
        adapter=ExecutionStore(self.store,run_id='run',wallet=account.address.lower())
        guards=ExecutionGuards(adapter)
        executor=Executor(adapter,guards,FakeVenue(adapter),RegistrySigner(adapter),FakeDecoder())
        i=intent(wallet=account.address.lower())
        executor.create(i,10);executor.prepare(i.key,11);state=executor.authorize(i.key,12)
        a=state.attempts[-1]
        signer=LocalSigner(account=account,expected_address=i.wallet,registry=adapter,signer_host=True,
            authorization=lambda *_:(i,'APPROVE',guards.snapshot(i,13),13,None))
        signed=signer.sign(a.attempt_id,a.payload,a.epoch,a.guard_version)
        self.assertTrue(verify(a.payload,signed))
        self.assertEqual(signed,signer.lookup(a.attempt_id,a.payload.hash))


class AbnormalSigningFenceTests(PostgresExecutionTests):
    def test_durable_abnormal_outbox_fences_signer_before_runtime_ingestion_and_after_restart(self):
        key = self.prepared()
        epoch, version = self.execution_store.execution_authority()
        self.execution_store.put_observation(dict(event_id='abnormal-final', run_id='run',
            kind='ABNORMAL', disposition='SUSTAINED_QUARANTINE'), epoch, version)
        self.restart()
        with self.assertRaisesRegex(Conflict, 'quarantined'):
            self.executor.sign(key, 13)
        with self.store.transaction() as db:
            run = self.execution_store._release_authority(db, epoch, version)
            self.assertTrue(run['abnormal_outcome'])
            with self.assertRaisesRegex(Conflict, 'quarantined'):
                self.execution_store.check_signing_run(run, self.executor._load(key).intent)
        # Receipt publication is still possible; quarantine never hides chain facts.
        self.execution_store.put_observation(dict(event_id='later-receipt', run_id='run',
            kind='REVERT'), epoch, version)
        self.assertIsNotNone(self.execution_store.lookup_observation('later-receipt'))

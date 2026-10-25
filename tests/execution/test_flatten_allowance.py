"""IDEA-096 AL2–AL6: synthetic external chain, durable executor and real PostgreSQL registry."""
from dataclasses import replace
import unittest

from larp.execution import Blocked, Conflict, REVOKE_TOKENS, USDT, possible_swap_hashes
from larp.marketdata.port import TOKENS
from tests import execution_fixtures as f
from tests.execution.test_allowance_recovery import AllowanceRecovery, PostgresRecovery, step


class AbortCleanup(AllowanceRecovery):
    def test_expiry_does_not_extend_cleanup_authority_and_pending_revoke_keeps_barrier(self):
        h = self.harness(); i = h.intent()
        h.executor.create(i, h.now); h.finish_step(i)
        state = h.executor.abort_unsigned(i.key, i.valid_until)
        self.assertEqual(state.status, 'ABORTED')
        self.assertEqual(h.rpc.allowances[USDT], i.amount)
        self.assertEqual(len(h.venue.broadcasts), 1)

    def test_rejected_swap_proved_not_submitted_gets_cleanup_without_reusing_nonce_authority(self):
        from larp.execution import Rejected
        h = self.harness(); i = h.intent()
        h.executor.create(i, h.now); h.finish_step(i)
        for method in ('prepare', 'authorize', 'sign'):
            h.now += 1; getattr(h.executor, method)(i.key, h.now)
        h.venue.broadcast_fault = Rejected('INSUFFICIENT_FUNDS')
        h.now += 1; state = h.executor.broadcast(i.key, h.now)
        from larp.execution import Outcome
        a = state.attempts[-1]
        h.venue.outcomes[a.tx_hash] = Outcome(a.tx_hash, None, None, 'UNKNOWN')
        h.now += i.timeout
        state = h.executor.reconcile(i.key, h.now)
        self.assertTrue(state.abort_pending)
        self.assertEqual(state.status, 'ACTIVE')
        h.venue.broadcast_fault = None
        h.finish_step(i)
        self.assertFalse(h.rpc.allowances[USDT])

    def test_abort_after_approve_cleans_inside_original_gas_and_releases_only_after_zero_read(self):
        h = self.harness(); i = h.intent()
        h.executor.create(i, h.now)
        h.finish_step(i)
        state = h.executor.abort_unsigned(i.key, h.now + 1)
        self.assertTrue(state.abort_pending)
        self.assertEqual(state.status, 'ACTIVE')
        with self.assertRaises(Conflict):
            h.executor.create(h.intent('other'), h.now + 1)
        h.restart()
        state = h.finish_step(i)
        self.assertEqual(state.attempts[-1].step, step(USDT))
        self.assertFalse(h.rpc.allowances[USDT])
        self.assertEqual(state.status, 'ACTIVE')
        state = h.executor.prepare(i.key, h.now + 1)
        self.assertEqual(state.status, 'ABORTED')
        self.assertFalse(possible_swap_hashes(state))
        self.assertLessEqual(sum(a.payload.gas * a.payload.gas_price for a in state.attempts), i.gas_budget)

    def test_failed_requote_durably_requests_abort_cleanup_without_another_quote(self):
        h = self.harness(); i = h.intent()
        h.executor.create(i, h.now); h.finish_step(i)
        def refused(*args):
            raise Blocked('encoded swap economics mismatch/expired')
        h.venue.quote = refused
        state = h.executor.prepare(i.key, h.now + 1)
        self.assertTrue(state.abort_pending)
        h.restart()
        state = h.finish_step(i)  # revoke works even though the quote endpoint still refuses
        self.assertEqual(state.attempts[-1].step, step(USDT))

    def test_exhausted_swap_quote_probes_leave_one_bounded_cleanup_stage(self):
        h = self.harness(); i = h.intent()
        h.executor.create(i, h.now); h.finish_step(i)
        def unavailable(*args):
            raise TimeoutError()
        h.venue.quote = unavailable
        for _ in range(i.max_prepare_probes):
            h.now += 1; h.executor.prepare(i.key, h.now)
        h.now += 1; state = h.executor.abort_unsigned(i.key, h.now)
        self.assertTrue(state.abort_pending)
        self.assertEqual(state.prepare_probes, 0)
        h.finish_step(i)
        self.assertFalse(h.rpc.allowances[USDT])

    def test_all_five_exits_clear_dirty_skhyb_or_usdt_before_any_swap(self):
        from tests.execution import test_untrusted_router as u
        for dirty in (TOKENS['SKHYB'], USDT):
            h = self.harness()
            h.rpc.allowances[dirty] = 123
            for n, token in enumerate(TOKENS.values()):
                _, params, tx = next(row for row in u.quotes() if row[1]['fromTokenAddress'].lower() == token)
                i = replace(u.swap_intent(params, tx, h.decoder), wallet=f.WALLET, intent_id=str(n),
                            reservation_id=str(n), valid_until=2000, gas_budget=10**7)
                h.executor.create(i, h.now)
                while h.executor._load(i.key).status == 'ACTIVE':
                    state = h.finish_step(i)
                    if state.attempts[-1].step == 'SWAP':
                        self.assertTrue(all(not a for t, a in h.rpc.allowances.items() if t != token))
                self.assertEqual(state.status, 'COMPLETED')
            self.assertFalse(any(h.rpc.allowances.values()))

    def test_swap_authorize_and_broadcast_recheck_other_token_contamination(self):
        for stage in ('authorize', 'broadcast'):
            h = self.harness(); i = h.intent()
            h.executor.create(i, h.now); h.finish_step(i)
            h.now += 1; h.executor.prepare(i.key, h.now)
            if stage == 'broadcast':
                h.now += 1; h.executor.authorize(i.key, h.now)
                h.now += 1; h.executor.sign(i.key, h.now)
            h.rpc.allowances[TOKENS['SKHYB']] = 1
            with self.assertRaisesRegex(Blocked, 'router allowance'):
                getattr(h.executor, stage)(i.key, h.now + 1)
            self.assertEqual(len(h.venue.broadcasts), 1)


class AbortPostgres(PostgresRecovery):
    def test_preexisting_execution_without_abort_field_keeps_its_original_hash_chain(self):
        import json
        from dataclasses import asdict
        from larp.execution import canonical, digest
        h = self.h; i = h.intent()
        state = h.executor.create(i, h.now)
        legacy = asdict(state)
        legacy.pop('abort_pending')
        checksum = digest(legacy)
        with self.case.store.transaction() as db:
            event, previous = db.execute('SELECT event,previous_hash FROM execution_journal '
                                        'WHERE economic_key=%s', (i.key,)).fetchone()
            db.execute('UPDATE execution_records SET state=%s,state_hash=%s WHERE economic_key=%s',
                       (canonical(legacy).encode(), checksum, i.key))
            db.execute('UPDATE execution_journal SET state_hash=%s,head=%s WHERE economic_key=%s',
                       (checksum, digest([previous, json.loads(bytes(event)), checksum]), i.key))
        self.restart()
        self.assertEqual(h.executor._load(i.key), state)
        self.assertEqual(h.executor.abort_unsigned(i.key, h.now + 1).status, 'ABORTED')

    def test_restart_every_abort_cleanup_stage_preserves_unique_signature_and_barrier(self):
        h = self.h; i = h.intent()
        h.executor.create(i, h.now); h.finish_step(i)
        self.restart()  # after successful approve
        h.now += 1; state = h.executor.prepare(i.key, h.now)
        h.now += 1; h.executor.authorize(i.key, h.now)
        h.now += 1; signed = h.executor.sign(i.key, h.now)
        swap = signed.attempts[-1]
        h.now += 1; state = h.executor.abort_unbroadcast(i.key, h.now)
        self.restart()  # after abort, issued swap revoked atomically
        self.assertEqual(h.executor._load(i.key), state)
        with self.assertRaises(Conflict):
            h.store.lookup(swap.attempt_id, swap.payload.hash)
        with self.assertRaises(Conflict):
            h.executor.create(h.intent('other'), h.now)
        for method in ('prepare', 'authorize', 'sign', 'broadcast'):
            h.now += 1; state = getattr(h.executor, method)(i.key, h.now)
            self.restart()
            self.assertEqual(h.executor._load(i.key), state)
        a = state.attempts[-1]
        self.assertEqual(a.step, step(USDT))
        h.executor.broadcast(i.key, h.now + 1)
        self.assertEqual(len(h.venue.broadcasts), 2)  # approve + cleanup, never aborted swap
        h.venue.outcomes[a.tx_hash] = f.finalized(a, 'SUCCESS')
        h.now += 3; h.executor.reconcile(i.key, h.now); h.guards.nonce += 1
        h.rpc.allowances[USDT] = 0
        self.restart()
        h.now += 1; state = h.executor.prepare(i.key, h.now)
        self.assertEqual(state.status, 'ABORTED')
        self.assertFalse(possible_swap_hashes(state))
        with self.case.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_signatures').fetchone()[0], 3)

from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.execution import (Blocked, Conflict, Executor, Gates, Outcome, Signed,
                            canonical, possible_swap_hashes, validate_payload)
from execution_fixtures import (BLOCK, ROUTER, TOKEN, WALLET, FakeDecoder, FakeGuards,
                                FakeSigner, FakeVenue, SQLiteFixture, finalized, intent)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "fixture.sqlite"
        self.attach()
        self.economic = intent()
        self.key = self.economic.key

    def attach(self):
        self.store = SQLiteFixture(self.path)
        self.guards = FakeGuards(self.store)
        self.signer = FakeSigner(self.store)
        self.venue = FakeVenue(self.store)
        self.decoder = FakeDecoder()
        self.engine = Executor(self.store, self.guards, self.venue, self.signer, self.decoder)

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def restart(self):
        self.store.close()
        self.attach()

    def signed_approve(self):
        self.engine.create(self.economic, 10)
        self.engine.prepare(self.key, 10)
        self.engine.authorize(self.key, 10)
        return self.engine.sign(self.key, 10)

    def final_approve(self):
        self.signed_approve()
        state = self.engine.broadcast(self.key, 11)
        self.venue.outcomes[state.attempts[-1].tx_hash] = finalized(state.attempts[-1])
        state = self.engine.reconcile(self.key, 12)
        self.guards.nonce = 1  # Positive adapter observation, not engine increment.
        return state

    def test_complete_flow_requotes_and_never_repeats_fill_or_broadcast(self):
        self.final_approve()
        state = self.engine.prepare(self.key, 13)
        self.assertEqual(self.venue.quote_calls, 2)
        self.assertEqual(state.attempts[-1].payload.nonce, 1)
        self.engine.authorize(self.key, 13)
        self.engine.sign(self.key, 13)
        state = self.engine.broadcast(self.key, 14)
        self.venue.outcomes[state.attempts[-1].tx_hash] = finalized(state.attempts[-1])
        done = self.engine.reconcile(self.key, 15)
        count = len(self.store.events())
        for _ in range(2):
            self.assertEqual(self.engine.broadcast(self.key, 16), done)
            self.assertEqual(self.engine.reconcile(self.key, 16), done)
            self.assertEqual(self.engine.create(self.economic, 16), done)
        self.assertEqual(done.status, "COMPLETED")
        self.assertEqual(len(self.venue.broadcasts), 2)
        self.assertEqual(len(self.store.events()), count)
        self.assertEqual(possible_swap_hashes(done), (done.attempts[-1].tx_hash,))

    def test_approval_needs_no_swap_deadline_field(self):
        state = self.signed_approve()
        self.assertEqual(state.attempts[-1].step, "APPROVE")
        self.assertEqual(state.attempts[-1].state, "SIGNED_DURABLE")

    def test_revert_consumes_outcome_but_does_not_authorize_swap(self):
        state = self.signed_approve()
        self.engine.broadcast(self.key, 11)
        self.venue.outcomes[state.attempts[-1].tx_hash] = finalized(state.attempts[-1], "REVERT")
        state = self.engine.reconcile(self.key, 12)
        self.assertEqual(state.status, "FAILED")
        self.assertEqual(self.engine.prepare(self.key, 13), state)
        self.assertEqual(len(state.attempts), 1)

    def test_expired_or_closed_after_approval_blocks_swap(self):
        self.final_approve()
        self.guards.change(underlying_market_open=False)
        state = self.engine.prepare(self.key, 13)
        self.assertIsNotNone(state.blocked_reason)
        self.assertEqual(len(state.attempts), 1)
        self.guards.changes.clear()
        state = self.engine.prepare(self.key, 1001)
        self.assertIsNotNone(state.blocked_reason)
        self.assertEqual(len(self.venue.broadcasts), 1)

    def test_approval_cannot_advance_without_verified_next_nonce(self):
        self.final_approve()
        self.guards.nonce = 7
        state = self.engine.prepare(self.key, 13)
        self.assertIn("nonce consumption", state.blocked_reason)
        self.assertEqual(len(state.attempts), 1)

    def test_swap_economic_mutations(self):
        economic = self.economic
        gates = self.guards.snapshot(economic, 10)
        payload = self.venue.quote(economic, 0)
        fields = json.loads(bytes.fromhex(payload.data[10:]))
        changes = {"pay_token": TOKEN, "receive_token": economic.pay_token,
                   "amount": 101, "recipient": ROUTER, "minimum_output": 89,
                   "deadline": 10, "native_value": 1}
        for field, value in changes.items():
            with self.subTest(field=field):
                mutated = replace(payload, data="0xfafafafa" + canonical({**fields, field: value}).encode().hex())
                with self.assertRaises(Blocked):
                    validate_payload(economic, "SWAP", mutated, gates, 10, self.decoder)
        for field, value in {"chain_id": 1, "sender": ROUTER, "to": TOKEN, "value": 1,
                             "nonce": 1, "gas": 200001, "gas_price": 11,
                             "data": "0xdeadbeef"}.items():
            with self.subTest(field=field), self.assertRaises(Blocked):
                validate_payload(economic, "SWAP", replace(payload, **{field: value}), gates, 10, self.decoder)

    def test_approve_tampering(self):
        payload = self.venue.approve(self.economic, 0)
        gates = self.guards.snapshot(self.economic, 10)
        mutations = [replace(payload, to=TOKEN), replace(payload, value=1),
                     replace(payload, data=payload.data + "00"),
                     replace(payload, data="0xdeadbeef" + payload.data[10:]),
                     replace(payload, data=payload.data[:-64] + format(101, "064x")),
                     replace(payload, data="0x095ea7b3" + "0" * 24 + WALLET[2:] + payload.data[74:])]
        for mutated in mutations:
            with self.assertRaises(Blocked):
                validate_payload(self.economic, "APPROVE", mutated, gates, 10, self.decoder)

    def test_every_guard_failure_blocks_prepare(self):
        self.engine.create(self.economic, 10)
        gates = self.guards.snapshot(self.economic, 10)
        for field in ("audit_durable", "reservation_valid", "version_valid", "risk_valid",
                      "health_valid", "token_market_open", "underlying_market_open", "clock_trusted"):
            for bad in (False, "false"):
                with self.subTest(field=field, bad=bad), self.assertRaises(Blocked):
                    replace(gates, **{field: bad}).check(self.economic, 10)
        with self.assertRaises(Blocked):
            replace(gates, nonce=None).check(self.economic, 10)

    def test_guard_change_before_sign_and_broadcast(self):
        self.engine.create(self.economic, 10)
        self.engine.prepare(self.key, 10)
        self.engine.authorize(self.key, 10)
        self.guards.change(risk_valid=False)
        with self.assertRaises(Conflict):
            self.engine.sign(self.key, 11)
        self.assertEqual(self.signer.calls, 0)

    def test_guard_change_after_signature_preserves_reservation_and_hash(self):
        state = self.signed_approve()
        self.guards.change(token_market_open=False)
        with self.assertRaises(Conflict):
            self.engine.broadcast(self.key, 11)
        self.assertEqual(self.venue.broadcasts, [])
        self.assertEqual(self.store.load(self.key).attempts[-1].tx_hash, state.attempts[-1].tx_hash)
        with self.assertRaises(Blocked):
            self.engine.abort_unsigned(self.key, 12)

    def test_ownership_loss_in_signer_release_boundary(self):
        self.engine.create(self.economic, 10)
        self.engine.prepare(self.key, 10)
        self.engine.authorize(self.key, 10)
        original = self.signer.sign
        def fenced(*args):
            self.store.advance_authority(epoch=True)
            return original(*args)
        with patch.object(self.signer, "sign", side_effect=fenced), self.assertRaises(Conflict):
            self.engine.sign(self.key, 10)
        self.assertEqual(self.signer.calls, 0)

    def test_lost_broadcast_response_never_blindly_resends(self):
        self.signed_approve()
        self.venue.broadcast_fault = TimeoutError()
        state = self.engine.broadcast(self.key, 11)
        self.assertEqual(state.attempts[-1].state, "UNKNOWN")
        self.engine.broadcast(self.key, 12)
        self.assertEqual(len(self.venue.broadcasts), 1)
        self.assertEqual(possible_swap_hashes(state), ())

    def test_crash_after_broadcast_before_result_save(self):
        self.signed_approve()
        original = self.venue.broadcast
        def sent(*args):
            result = original(*args)
            self.store.fail_next = True
            return result
        with patch.object(self.venue, "broadcast", side_effect=sent), self.assertRaises(OSError):
            self.engine.broadcast(self.key, 11)
        self.restart()
        state = self.store.load(self.key)
        self.assertEqual(state.attempts[-1].state, "BROADCAST_ATTEMPTED")
        self.engine.broadcast(self.key, 12)
        self.assertEqual(self.venue.broadcasts, [])
        self.venue.outcomes[state.attempts[-1].tx_hash] = finalized(state.attempts[-1])
        self.assertEqual(self.engine.reconcile(self.key, 13).attempts[-1].state, "FINAL_SUCCESS")

    def test_storage_failure_before_broadcast_makes_no_submission(self):
        self.signed_approve()
        self.store.fail_next = True
        with self.assertRaises(OSError):
            self.engine.broadcast(self.key, 11)
        self.assertEqual(self.venue.broadcasts, [])
        self.assertEqual(self.store.load(self.key).attempts[-1].state, "SIGNED_DURABLE")

    def test_signature_persist_failure_recovers_registry_after_takeover(self):
        self.engine.create(self.economic, 10)
        self.engine.prepare(self.key, 10)
        self.engine.authorize(self.key, 10)
        self.store.fail_next = True
        with self.assertRaises(OSError):
            self.engine.sign(self.key, 10)
        self.assertEqual(self.store.load(self.key).attempts[-1].state, "AUTHORIZED")
        self.restart()
        self.store.advance_authority(epoch=True)
        state = self.engine.recover_signature(self.key, 11)
        self.assertIsNotNone(state.attempts[-1].tx_hash)
        with self.assertRaises(Conflict):
            self.engine.broadcast(self.key, 11)

    def test_idempotent_signing_rejects_changed_attempt_bytes(self):
        state = self.signed_approve()
        attempt = state.attempts[-1]
        signed = self.signer.sign(attempt.attempt_id, attempt.payload, attempt.epoch, attempt.guard_version)
        self.assertEqual(signed.tx_hash, attempt.tx_hash)
        self.assertEqual(self.signer.calls, 1)
        with self.assertRaises(Conflict):
            self.signer.sign(attempt.attempt_id, replace(attempt.payload, value=1), attempt.epoch, attempt.guard_version)

    def test_provisional_inclusion_reorg_and_late_finality(self):
        state = self.signed_approve()
        self.engine.broadcast(self.key, 11)
        attempt = state.attempts[-1]
        self.venue.outcomes[attempt.tx_hash] = finalized(attempt, finality_verified=False)
        state = self.engine.reconcile(self.key, 12)
        self.assertEqual(state.attempts[-1].state, "INCLUDED_SUCCESS")
        self.assertEqual(len(self.engine.prepare(self.key, 13).attempts), 1)
        self.venue.outcomes[attempt.tx_hash] = Outcome(attempt.tx_hash, WALLET, 0, "UNKNOWN")
        self.assertEqual(self.engine.reconcile(self.key, 16).attempts[-1].state, "UNKNOWN")
        self.venue.outcomes[attempt.tx_hash] = finalized(attempt)
        self.assertEqual(self.engine.reconcile(self.key, 20).attempts[-1].state, "FINAL_SUCCESS")

    def test_wrong_sender_nonce_hash_or_canonical_block_cannot_finalize(self):
        state = self.signed_approve()
        self.engine.broadcast(self.key, 11)
        attempt = state.attempts[-1]
        for n, changes in enumerate(({"sender": ROUTER}, {"nonce": 7}, {"tx_hash": BLOCK},
                                      {"canonical_block_hash": "0x" + "4" * 64}, {"finalized_height": 9})):
            self.venue.outcomes[attempt.tx_hash] = finalized(attempt, **changes)
            state = self.engine.reconcile(self.key, 12 + n * 4)
            self.assertNotEqual(state.attempts[-1].state, "FINAL_SUCCESS")
            self.assertEqual(state.status, "ACTIVE")

    def test_timeout_probe_budget_and_restart_never_release_wallet_barrier(self):
        state = self.signed_approve()
        self.engine.broadcast(self.key, 11)
        for now in range(200, 240, 4):
            state = self.engine.reconcile(self.key, now)
        self.assertEqual(state.attempts[-1].probes, 8)
        self.restart()
        count = len(self.store.events())
        self.engine.reconcile(self.key, 300)
        self.assertEqual(len(self.store.events()), count)
        self.engine.broadcast(self.key, 301)
        self.assertEqual(self.store.load(self.key).attempts[-1].probes, 8)
        self.assertEqual(self.venue.broadcasts, [])
        with self.assertRaises(Conflict):
            self.engine.create(intent(intent_id="economic-2", pay_token=TOKEN, receive_token=self.economic.pay_token), 300)
        self.assertEqual(self.store.load(self.key).status, "ACTIVE")

    def test_wallet_barrier_spans_run_ids_and_changed_parent_cannot_duplicate(self):
        state = self.engine.create(self.economic, 10)
        for changed in (intent(run_id="other-run", intent_id="other"), intent(round_id="another-round")):
            with self.assertRaises(Conflict):
                self.engine.create(changed, 10)
        self.assertEqual(self.store.load(self.key), state)

    def test_stale_commit_rolls_back_event_and_state(self):
        state = self.engine.create(self.economic, 10)
        gates = self.guards.snapshot(self.economic, 10)
        current = self.engine.prepare(self.key, 10)
        count = len(self.store.events())
        with self.assertRaises(Conflict):
            self.store.commit(state, state, {}, gates.epoch, gates.state_version)
        self.assertEqual(self.store.load(self.key), current)
        self.assertEqual(len(self.store.events()), count)

    def test_missing_gas_and_prepare_budget_survive_restart(self):
        self.engine.create(self.economic, 10)
        self.venue.estimate = None
        for _ in range(3):
            state = self.engine.prepare(self.key, 10)
            self.assertEqual(state.attempts, ())
        self.restart()
        with self.assertRaises(Blocked):
            self.engine.prepare(self.key, 11)
        self.assertEqual(self.signer.calls, 0)

    def test_parent_gas_budget_counts_approval_cost(self):
        self.economic = intent(gas_budget=150000)
        self.key = self.economic.key
        self.final_approve()
        state = self.engine.prepare(self.key, 13)
        self.assertEqual(len(state.attempts), 1)
        self.assertIn("parent gas budget", state.blocked_reason)

    def test_events_never_expose_signed_bytes(self):
        state = self.signed_approve()
        self.assertNotIn(state.attempts[-1].raw_hex, canonical(self.store.events()))
        self.assertNotIn("raw_hex", canonical(self.store.events()))

    def test_unsigned_abort_is_distinct_from_issued_uncertainty(self):
        self.engine.create(self.economic, 10)
        self.engine.prepare(self.key, 10)
        state = self.engine.abort_unsigned(self.key, 11)
        self.assertEqual(state.status, "ABORTED")
        self.assertEqual(state.attempts[-1].state, "ABORTED")

    def test_live_bundle_and_replacement_disabled(self):
        with self.assertRaises(Blocked):
            self.engine.replace_transaction()
        self.venue.mode = "live"
        with self.assertRaises(Blocked):
            Executor(self.store, self.guards, self.venue, self.signer, self.decoder)

    def test_invalid_intent_values_and_topups_rejected(self):
        for changes in ({"amount": True}, {"amount": 0}, {"chain_id": 1},
                        {"wallet": WALLET.upper()}, {"receive_token": ROUTER},
                        {"intent_id": ""}, {"max_prepare_probes": 0}):
            with self.subTest(changes=changes), self.assertRaises(Blocked):
                intent(**changes).validate()

    def test_unspecified_guard_facts_fail_closed(self):
        with self.assertRaises(Blocked):
            Gates(1, 1, 0, 10, 40).check(self.economic, 10)

    def test_backward_clock_cannot_broadcast_emitted_signature(self):
        self.signed_approve()
        with self.assertRaises(Blocked):
            self.engine.broadcast(self.key, 9)
        self.assertEqual(self.venue.broadcasts, [])

    def test_backward_clock_initial_prepare_preserves_saved_timestamp(self):
        state = self.engine.create(self.economic, 100)
        with self.assertRaisesRegex(Blocked, "clock regression"):
            self.engine.prepare(self.key, 90)
        self.assertEqual(self.store.load(self.key), state)
        self.assertEqual(state.last_observed_at, 100)
        self.assertEqual(self.venue.quote_calls, 0)
        self.assertEqual(self.signer.calls, 0)
        self.assertEqual(self.venue.broadcasts, [])

    def test_backward_clock_after_approval_cannot_prepare_swap(self):
        state = self.final_approve()
        with self.assertRaisesRegex(Blocked, "clock regression"):
            self.engine.prepare(self.key, 11)
        self.assertEqual(self.store.load(self.key), state)
        self.assertEqual(self.venue.quote_calls, 1)
        self.assertEqual(len(self.venue.broadcasts), 1)
        self.assertEqual(self.engine.prepare(self.key, 13).attempts[-1].step, "SWAP")

    def test_unbroadcast_approval_survives_restart_reconcile_then_first_send(self):
        signed = self.signed_approve()
        self.restart()
        state = self.engine.reconcile(self.key, 11)
        attempt = state.attempts[-1]
        self.assertEqual(attempt.state, "SIGNED_DURABLE")
        self.assertIsNone(attempt.broadcast_at)
        self.assertEqual(attempt.tx_hash, signed.attempts[-1].tx_hash)
        self.assertEqual(attempt.raw_hex, signed.attempts[-1].raw_hex)
        self.assertEqual(state.intent.reservation_id, signed.intent.reservation_id)
        self.assertEqual(self.engine.broadcast(self.key, 12).attempts[-1].state, "PENDING")
        self.engine.broadcast(self.key, 13)
        self.assertEqual(self.venue.broadcasts, [attempt.tx_hash])
        self.assertEqual(self.signer.calls, 0)

    def test_unbroadcast_swap_preserves_guarded_first_send_after_absent_outcome(self):
        self.final_approve()
        self.engine.prepare(self.key, 13)
        self.engine.authorize(self.key, 13)
        state = self.engine.sign(self.key, 13)
        self.restart()
        self.guards.nonce = 1
        attempt = state.attempts[-1]
        self.venue.outcomes[attempt.tx_hash] = Outcome(attempt.tx_hash, WALLET, 1, "UNKNOWN")
        recovered = self.engine.reconcile(self.key, 14)
        self.assertEqual(recovered.attempts[-1].state, "SIGNED_DURABLE")
        self.engine.broadcast(self.key, 15)
        self.assertEqual(self.venue.broadcasts, [attempt.tx_hash])

    def test_unbroadcast_reconciliation_does_not_bypass_changed_authority(self):
        self.signed_approve()
        self.restart()
        self.guards.change(risk_valid=False)
        self.assertEqual(self.engine.reconcile(self.key, 11).attempts[-1].state, "SIGNED_DURABLE")
        with self.assertRaises(Conflict):
            self.engine.broadcast(self.key, 12)
        self.assertEqual(self.venue.broadcasts, [])

    def exhaust_unbroadcast_probes(self, state, start):
        attempt = state.attempts[-1]
        self.venue.outcomes[attempt.tx_hash] = Outcome(attempt.tx_hash, WALLET, attempt.payload.nonce, "UNKNOWN")
        for index in range(self.economic.max_recovery_probes):
            state = self.engine.reconcile(self.key, start + index * self.economic.probe_interval)
        self.assertEqual(state.attempts[-1].state, "SIGNED_DURABLE")
        self.assertEqual(state.attempts[-1].probes, self.economic.max_recovery_probes)
        self.assertIsNone(state.attempts[-1].broadcast_at)
        return state

    def test_exhausted_prebroadcast_approval_budget_can_process_finality_after_restart(self):
        state = self.exhaust_unbroadcast_probes(self.signed_approve(), 11)
        self.restart()
        self.assertEqual(self.store.load(self.key).attempts[-1].probes, 8)
        state = self.engine.broadcast(self.key, 33)
        self.assertEqual(state.attempts[-1].probes, 0)
        self.assertEqual(state.attempts[-1].next_probe, 33)
        self.assertEqual(self.venue.broadcasts, [state.attempts[-1].tx_hash])
        self.restart()
        attempt = self.store.load(self.key).attempts[-1]
        self.assertEqual(attempt.probes, 0)
        self.venue.outcomes[attempt.tx_hash] = finalized(attempt)
        state = self.engine.reconcile(self.key, 34)
        self.assertEqual(state.attempts[-1].state, "FINAL_SUCCESS")
        self.assertEqual(state.attempts[-1].probes, 1)

    def test_exhausted_prebroadcast_swap_budget_can_complete_after_restart(self):
        self.final_approve()
        self.engine.prepare(self.key, 13)
        self.engine.authorize(self.key, 13)
        state = self.engine.sign(self.key, 13)
        self.exhaust_unbroadcast_probes(state, 14)
        state = self.engine.broadcast(self.key, 36)
        self.assertEqual(state.attempts[-1].probes, 0)
        self.assertEqual(len(self.venue.broadcasts), 2)
        self.restart()
        attempt = self.store.load(self.key).attempts[-1]
        self.venue.outcomes[attempt.tx_hash] = finalized(attempt)
        self.assertEqual(self.engine.reconcile(self.key, 37).status, "COMPLETED")

    def test_first_broadcast_storage_failure_keeps_prebroadcast_counter(self):
        state = self.exhaust_unbroadcast_probes(self.signed_approve(), 11)
        self.store.fail_next = True
        with self.assertRaises(OSError):
            self.engine.broadcast(self.key, 33)
        self.assertEqual(self.store.load(self.key), state)
        self.assertEqual(self.venue.broadcasts, [])
        self.restart()
        state = self.engine.broadcast(self.key, 34)
        self.assertEqual(state.attempts[-1].probes, 0)
        self.assertEqual(self.venue.broadcasts, [state.attempts[-1].tx_hash])

    def test_lost_first_broadcast_response_retains_fresh_budget_after_restart(self):
        self.exhaust_unbroadcast_probes(self.signed_approve(), 11)
        self.venue.broadcast_fault = TimeoutError()
        state = self.engine.broadcast(self.key, 33)
        self.assertEqual(state.attempts[-1].state, "UNKNOWN")
        self.assertEqual(state.attempts[-1].probes, 0)
        self.restart()
        self.engine.broadcast(self.key, 34)
        self.assertEqual(self.venue.broadcasts, [])
        attempt = self.store.load(self.key).attempts[-1]
        self.venue.outcomes[attempt.tx_hash] = finalized(attempt)
        self.assertEqual(self.engine.reconcile(self.key, 34).attempts[-1].state, "FINAL_SUCCESS")

    def test_missing_receipt_gas_retains_allowance_and_blocks_tight_parent_budget(self):
        self.economic = intent(gas_budget=150000)
        self.key = self.economic.key
        state = self.signed_approve()
        attempt = state.attempts[-1]
        self.engine.broadcast(self.key, 11)
        # Construct the outcome with gas_used OMITTED, matching the review report.
        self.venue.outcomes[attempt.tx_hash] = Outcome(attempt.tx_hash, WALLET, 0, "SUCCESS",
                                                     BLOCK, BLOCK, 10, 12, True)
        state = self.engine.reconcile(self.key, 12)
        self.assertEqual(state.attempts[-1].state, "FINAL_SUCCESS")
        self.assertIsNone(state.attempts[-1].gas_used)
        self.assertIn("gas allowance retained", state.blocked_reason)
        self.restart()
        self.guards.nonce = 1
        state = self.engine.prepare(self.key, 13)
        self.assertEqual(len(state.attempts), 1)
        self.assertIn("parent gas budget", state.blocked_reason)

    def test_missing_receipt_gas_allows_only_affordable_worst_case_swap(self):
        state = self.signed_approve()
        attempt = state.attempts[-1]
        self.engine.broadcast(self.key, 11)
        self.venue.outcomes[attempt.tx_hash] = finalized(attempt, gas_used=None)
        self.engine.reconcile(self.key, 12)
        self.guards.nonce = 1
        self.assertEqual(self.engine.prepare(self.key, 13).attempts[-1].step, "SWAP")

    def test_invalid_receipt_gas_cannot_finalize_or_release_budget(self):
        state = self.signed_approve()
        attempt = state.attempts[-1]
        self.engine.broadcast(self.key, 11)
        for index, gas in enumerate((0, -1, True, attempt.payload.gas + 1)):
            self.venue.outcomes[attempt.tx_hash] = finalized(attempt, gas_used=gas)
            with self.subTest(gas=gas), self.assertRaises(Blocked):
                self.engine.reconcile(self.key, 12 + index * 4)
            self.assertEqual(self.store.load(self.key).attempts[-1].state, "PENDING")

    def test_ownership_loss_at_broadcast_release_keeps_possible_send(self):
        self.signed_approve()
        original = self.venue.broadcast
        def fenced(*args):
            self.store.advance_authority(epoch=True)
            return original(*args)
        with patch.object(self.venue, "broadcast", side_effect=fenced), self.assertRaises(Conflict):
            self.engine.broadcast(self.key, 11)
        self.assertEqual(self.venue.broadcasts, [])
        self.assertEqual(self.store.load(self.key).attempts[-1].state, "BROADCAST_ATTEMPTED")

    def test_cold_restart_after_each_successful_durable_transition(self):
        self.engine.create(self.economic, 10)
        self.restart()
        self.engine.prepare(self.key, 10)
        self.restart()
        self.engine.authorize(self.key, 10)
        self.restart()
        signed = self.engine.sign(self.key, 10)
        self.restart()
        self.assertEqual(self.store.load(self.key).attempts[-1].tx_hash, signed.attempts[-1].tx_hash)
        self.engine.broadcast(self.key, 11)
        self.restart()
        attempt = self.store.load(self.key).attempts[-1]
        self.venue.outcomes[attempt.tx_hash] = finalized(attempt)
        self.engine.reconcile(self.key, 12)
        self.restart()
        self.guards.nonce = 1
        self.engine.prepare(self.key, 13)
        self.restart()
        self.guards.nonce = 1
        self.engine.authorize(self.key, 13)
        self.restart()
        self.guards.nonce = 1
        self.engine.sign(self.key, 13)
        self.restart()
        self.guards.nonce = 1
        self.engine.broadcast(self.key, 14)
        self.restart()
        self.guards.nonce = 1
        attempt = self.store.load(self.key).attempts[-1]
        self.venue.outcomes[attempt.tx_hash] = finalized(attempt)
        self.engine.reconcile(self.key, 15)
        self.restart()
        state = self.store.load(self.key)
        self.assertEqual(state.status, "COMPLETED")
        self.assertEqual(len(state.attempts), 2)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM signatures").fetchone()[0], 2)
        self.assertEqual([event["step"] for event in self.store.events() if event["type"] == "FINAL_SUCCESS"], ["APPROVE", "SWAP"])


if __name__ == "__main__":
    unittest.main()

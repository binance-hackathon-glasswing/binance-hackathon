# Runtime development documents v1

All examples are synthetic. Common ports are in `larp/ports.py`. Existing
DecisionSnapshot/PolicyState/Proposal/Target retain their original Python API.
Documents use integer base units, exact rational weights and UTC epoch milliseconds.
Concrete successful and rejected example payloads, committed batches and exact
audit chunks are retained in `evidence/runtime-offline-trace.json`; provenance and
the file checksum are recorded in IDEA-028. All its prices/balances/identities are
synthetic fixtures, not production configuration.

| Schema | Required vocabulary |
|---|---|
| AssessmentRequest.v1 | job_id, run_id, issuer_id, cutoff_ms, evidence_refs, context_hash, policy_profile_hash, allowed_tools, budget |
| AssessmentResult.v1 | same identities/hashes, model_hash, prompt_hash, claims, novelty, conflicts, missingness, confidence, falsifiers, expiry_ms, review_requests, rationale, model_io |
| MarketRequest.v1 | request_id, run_id, token, underlying, cutoff_ms |
| MarketObservation.v1 | observation_id, token, underlying, decimals, token_market_state, underlying_market_state, source, observed_ms, available_ms, content_hash, quality |
| PlanResult.v1 | snapshot_id, reasons, intents, reservation_deltas, proposed_state, jobs |
| ExecutionState.v1 | intent_id, step, state, attempts |
| ExecutionTransition.v1 | next_state, commands, observation_ids |
| CommitBatch.v1 | run_id, wallet_id, chain_id, event_id, expected_version, owner_epoch, event, projection, policy_state, execution_state, reservation_deltas, jobs, commands, audit |
| AuditEvent.v1 | event_id, round_id, version_id, decision_ids, address, timestamp_ms, log, chunks, log_sha256 |

CommitBatch event_hash is computed from canonical `event`; batch_hash covers all
bytes. Reusing a batch ID requires identical bytes (including expected_version).
The store owns sequence, version and head hash. Reservation deltas name intent_id,
asset and signed integer units; balances in the proposed projection are settled
units. Projection changes must come through the owner-supplied reducer, not policy.

Jobs carry job_id, lane (safety/reconcile/audit/evidence/policy), due_ms,
valid_until_ms, max_attempts, payload, calendar_id, tzdata_version and missed policy
(catch_up/expire). Attempts/status/next_due are store-owned; scheduling the same
ID with different content is an error. Reassessment jobs carry no trade command.

Commands carry command_id, kind, payload, expires_ms, round_id and decision_id.
Commands are requests until committed; the external executor must recheck current
owner epoch, version, health and action-specific authorization at each boundary.
No live executor is included here. Audit hashes have unique primary round ownership.

Schemas are additive development contracts; matching a schema name alone never
establishes field validity, approved evidence, monetary correctness or live readiness.

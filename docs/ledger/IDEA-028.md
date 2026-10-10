# IDEA-028 — Runtime, audit and platform build

- Date: 2026-10-10 SGT. Owner Keegan; required reviewer Isaac.
- User request: implement docs/build/04-runtime-audit.prompt.txt completely.
- Baseline: e10eae2, shared kickoff on origin/codex/engine-foundation.
- Branch: codex/runtime-audit-platform. No main merge or live activation authorized.
- Status: implementation in progress; tests NOT RUN at this initial record.
- Scope: shared additive ports, PostgreSQL atomic durability, coordinator, bounded
  workers/scheduler, protocol 2.0 audit outbox, release gates and offline integration.
- Production database/backup/anchor/hosting destinations are not selected. User
  requests recommendations after this implementation; production remains blocked.

## Decisions

RT01: Preserve IDEA-023 contracts and all 13 tests. Publish Protocol interfaces;
cross-owner examples are synthetic and versioned, never production policy.

RT02: Implement first-party protocol 2.0 delivery, preserving the vendored SDK.
Store immutable event bytes and character-aligned chunks before sending. Retries
reuse event/chunk identity with fresh authentication headers. SDK log() is not
used to recreate events. Source: verbatim PROTOCOL.md §§1–6 and SDK README.

RT03: PostgreSQL is authoritative. Serialize commits on the run row, compare
expected version and wallet owner epoch, and atomically persist the journal,
projection, policy/execution state, reservations, jobs and outboxes. Local storage
failure never grants authority; remote upload failure retains durable records.

RT04: Restore is quarantined by default. A backup is not fresh wallet authority;
external fencing and reconciliation evidence must precede promotion. No runtime
live signer is supplied by this branch. Isaac owns its enforcement.

## Prospective acceptance criteria (before execution)

1. Existing 13 tests pass; import/collection needs no secrets or network.
2. Real disposable PostgreSQL: migration repeatability; identical commit retry is
   idempotent, changed bytes fail; concurrent/stale writers cannot double-reserve;
   atomic rollback leaves no event, job, command or audit fragment.
3. Journal replay and restart match canonical hashes; corrupt history/checkpoints
   fail validation; stale/zombie ownership and quarantined restores block commands.
4. Audit official PUT and POST signature vectors pass; Unicode chunking is exact;
   lost ACK, mid-chunk crash and restart yield one logical event. 400/401/413 remain
   explicit permanent failures; 429/5xx/network retry is bounded and durable.
5. Every started fixture round, including worker failures/HOLD/restart, closes once
   with truthful I/O and all possibly broadcast swap hashes; approvals never become
   swap orders; later observations do not mutate the original audit event.
6. Scheduler deduplicates ticks, persists attempts and UTC high-water marks, expires
   stale trades and services safety/reconciliation/audit despite evidence overload.
   DST fallback, UTC midnight, missed ticks and backward clocks do not duplicate work.
7. Isolated worker hangs/errors/oversized outputs cannot mutate the controller or
   stall independently scheduled safety. Offline/paper have no signing capability;
   unset live settings and manifest mismatches fail closed.
8. One durable offline integration trace covers observation, assessment, proposal,
   independent planning, reservation, fake outcomes, settlement, audit ACK and replay.
   Fakes remain explicit; no financial/venue semantics claim replaces owner review.
9. Verify Python 3.12 dependencies, Linux execution, backup/restore and release
   artifacts. Record exact commands/results and unresolved AT01–20 capabilities.

These are engineering checks, not market/model experiments. Commit and push new
code/criteria before tests. Unit tests cannot establish the submitted five-plus-day
full-pipeline rehearsal including a weekend, actual registration or live capability.

## Open items

Keegan: complete implementation and evidence for RT01–09. Isaac: independent review
and signer/venue integration. Keith: financial reducer/planner integration. Yao Zhu:
assessment semantics and real evidence integration. Team: production destinations,
registration, policy, window, measured limits, funding/gas and rehearsal. GAP-28,
GAP-30–36/45/46/48/52/65 remain open until verified in their complete scope.

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

## RT05–09 — implementation and verification, 2026-10-10

RT05: Offline implementation is delivered on `codex/runtime-audit-platform`;
required independent review by Isaac is pending. Preserve the initial NOT RUN
record above as history. Tested code head is
`4207d925a6640f0e41524f17665b42351446e07c`. Each code/criteria increment was committed
and pushed before execution. No other owner branch or main was merged; no real
signer, registered uploader or live wallet was used.

RT06: Bounded Linux workers use bubblewrap, JSON communication and resource limits.
The controller injects ports; the offline demo supplies sandboxed assessment/policy
and explicitly synthetic market/planner/execution/accounting adapters. Real owner
modules remain required. Worker/queue values are development limits, not measured
production service guarantees. No alternate production engine was implemented.

RT07: A complete round audit is preflighted before commands/reservations. Unsupported
size causes `AUDIT_CONTENT_UNSUPPORTED`, no commands, and an explicit small failure
audit referencing the retained full local record's hash. The original received I/O
remains local; there is no claim that a summary satisfies a full remote I/O requirement.
Production provider/storage bounds and this failure path require owner review.
Late execution observations remain separate journal events after immutable closure.

RT08: Exact replay now reruns deterministic policy, planning, execution transitions
and the injected accounting reducer using captured assessment results; it compares
each reconstructed canonical batch hash. It does not just recommit saved projections
or silently invoke a new model. Unknown journal event kinds require an owner adapter.

RT09: No deployment destinations have been selected (user confirmed). The proposed
AWS stack in `docs/build/runtime-infrastructure.md` is a recommendation only. The
declared hourly anchor remains configured as 3600 seconds; deployment scheduling,
write-once storage policy, retention and external authority are still open. No shorter
retention or rehearsal is adopted. `capabilities()` refuses dev/live even if all
example settings are filled, until the reviewed live bundle is integrated.

### Execution evidence

| Check | Result and scope |
|---|---|
| Original compatibility | Original `larp/contracts.py` and 13 tests unchanged; passing within the full suite |
| Fresh Linux Python/dependencies | Python 3.12.15 on Ubuntu 22.04 WSL; fresh full `requirements.lock` installation and `pip check` passed; minimal runtime/test profile also passes in CI |
| Full Linux suite at `4207d92` | **55 passed, 44 subtests passed**, 13.71 seconds; real disposable PostgreSQL 14.24 plus Linux isolation tests; no skips |
| Windows compatibility | Python 3.12.14 existing conda environment repaired with pinned pytest; `pip check` passed; **21 passed, 34 skipped, 44 subtests passed**; skips are PostgreSQL/Linux-only cases without the corresponding Windows environment |
| CI at tested code head | [Run 38022535118](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38022535118) succeeded: tests, restart demo, digest-pinned Docker build and no-network/read-only container smoke |
| Failed CI and repair | `b698192` run 38021766973 exposed the remapped Python shared-library path; `656524c` added explicit sandbox `LD_LIBRARY_PATH=/python/lib`; subsequent runs 38022300045, 38022405190 and 38022535118 passed |
| Real process deaths | `tests/storage/test_process_crash.py`: process exit before commit rolls back; after commit retains state/outbox; after receiver fsync/before local ACK resends identical ID/bytes to one logical fake receiver event |
| Migration/restore | Repeated migration and changed-checksum rejection; full backup/empty-target restore preserves journal/jobs/outbox, increments epoch and quarantines; corrupt hash/tail/reservations and stale external minimum version fail |
| Local write failure | Real PostgreSQL read-only transactions block commit AND command release; SQLSTATE 53100 disk-full fault injection rolls back reservations. Physical media exhaustion, power failure and hosted failover have NOT been tested |
| Integrated trace | `docs/build/evidence/runtime-offline-trace.json`: sandboxed model/policy, reserved fake buy, broadcast observation, controller restart, unresolved-round audit, late settled receipt, rejected model round and lost-ACK retry; final version 6, zero open rounds/pending uploads, balances USDT=90/BNB=9/NVDAB=2 in synthetic units |
| Exact replay | `tests/integration/test_runtime.py::IntegratedRuntime::test_restartable_round_settlement_audit_backup_and_exact_replay`: re-executed port path matches canonical journal head and projection; restored backup matches head and preserves ACK |

The stored trace is entirely synthetic. File SHA256:
`b68ac3704cb18cbe8171c3ee42dd0f31ee7292d551176c449185f7a3787cac04`.
Trace journal head: `5ca09700686487cc9b8b6e83af7ed76d1b6863c8ff2c39c3767c3cd0d56d309e`.
The trace schema name is disposable and unique, not a deployment destination.
Exact environment/reproducer commands and recovery procedure are in
`docs/build/runtime-operations.md`; versioned payload vocabulary is in
`docs/build/runtime-contracts.md`. CI pins Python/image/action revisions; apt OS
packages and the external provider are not claimed fully reproducible or immutable.

### AT01–20 evidence and remaining capabilities

These statuses describe runtime contribution, not full acceptance. No row implies
the other owners' semantics or real venue behavior have passed. Names below follow
the revised four-person build allocation.

| Case | Evidence in this branch | Remaining capability / owner |
|---|---|---|
| AT01 | Immutable original contracts; bounded sandbox; exact fake-policy replay | Stateful owner policies, feature registry and hidden-I/O adversaries — Keith/Yao Zhu |
| AT02 | Planner runs when assessment fails; proposals cannot settle holdings | Financial cap/loss/exit precedence and profile enforcement — Keith |
| AT03 | Original invalid-target/expiry/state tests; stale assessment/context/budget checks; truthful no-action audits | Full production policy/profile variants — Keith/Yao Zhu |
| AT04 | Real PG concurrent reserve conflict, atomic rollback, idempotent settlement and restart | Both 100/200 USDT financial/gas fixtures, pending-sell semantics — Keith with Keegan |
| AT05 | Reservation/plan-rejection is durable without partial mutation | Combined mandatory reductions, child splitting/dust — Keith |
| AT06 | Current version/epoch/expiry and durable write required for command release | Approve wait, market/deadline recheck and transaction payload validation — Isaac |
| AT07 | Real process crash before/after DB commit; duplicate synthetic observations | Every real transaction step, nonce/fee/finality and lost broadcast response — Isaac |
| AT08 | Zombie epoch rejection; corrupt/stale restore detection; quarantine; dev/live cannot use offline takeover | External signer fencing, unknown nonce consumers and already-issued payload reconciliation — Isaac/Keegan |
| AT09 | No replacement/signer capability supplied; dev/live blocked | Replacement remains disabled; any future implementation needs Isaac's full adversarial cases |
| AT10 | Official POST/PUT vectors; immutable Unicode chunks; restart mid-delivery; real death after fake receiver fsync; round/version/decision swap mapping; approval rejected | Actual registered receiver compatibility, real swap/gas coverage — Keegan/Isaac |
| AT11 | 400/401/413/429/500/503/network statuses, bounded retry/exhaustion, deadline breach, corrupt tail, read-only and SQLSTATE disk-full, oversized-I/O no-command fallback | Physical disk/power faults, measured upload slack across UTC rollover and real receiver outage drain — Keegan |
| AT12 | Timeout/exception and stale/future/context-mismatched assessment rejection; independent planner still runs | Real source outage, filing catch-up and dependency/thesis invalidation — Yao Zhu/Keith |
| AT13 | Captured assessment replay through policy/planner/execution/reducer matches every batch hash, projection and audit payload | Production latches/owner adapters — Keith/Isaac/Yao Zhu with Keegan |
| AT14 | Separate bounded lanes and job queues; evidence overload leaves safety service; durable lease/attempt budget and outbox recovery | Host partition/long outage, production service objectives and operator alerts/escalation — Keegan with owners |
| AT15 | DST ambiguity/nonexistent time, midnight, duplicate/missed/stale jobs, backward UTC and persisted retry budget tests | Real exchange weekends/half-days, risk latches/gas budgets and reboot-wide clock policy — Keith/Isaac/Keegan |
| AT16 | Acquisition/observation identities and captured results retained; future evidence rejected | Real point-in-time datasets, source revisions, future-bar perturbation and comparable simulations — Yao Zhu/Keith/Isaac |
| AT17 | Real OS/PG checks; fake execution port; offline/paper capability denial | Real approve/requote/sign/reconcile machine parity and labelled paper fills — Isaac |
| AT18 | Integer atomic reservation boundary; fake settled-only reducer | Actual fees, gas floor/top-up, marks/equity, unsolicited balances and terminal costs — Keith/Isaac |
| AT19 | No inherited credentials/home/network; hang/error/input/output limits; independent service lanes; audit size rejection | Provider-specific tools/network isolation, malicious filing corpus and measured worst-case storage budgets — Yao Zhu/Keegan |
| AT20 | Fresh Linux install, secret-free collection, manifest mismatch denial, consistent backup/restore, local epoch fencing, synthetic complete export | Registered wallet/build binding, hosted cold standby/external fencing and full 5+ day rehearsal including weekend — team |

### Review and handoff scope

All session implementation/evidence is intended for a draft PR against
`codex/engine-foundation`; Isaac is the designated reviewer, with review not yet
performed. Keegan owns integrating the reviewed branches and the deployment work;
Keith owns the financial reducer/planner; Isaac owns execution/signing; Yao Zhu owns
real evidence/model semantics. Team-owned choices are enumerated in the operations
guide and infrastructure recommendation. Shared backlog partial progress is recorded;
no incompletely verified GAP was removed. No main merge, live activation, credential
provisioning, organizer message, market experiment or rehearsal completion is claimed.

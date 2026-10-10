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

## RT10 — architecture implementation follow-up, prospective criteria

2026-10-10: user asks for everything needed to create the recommended architecture
and implementation of everything possible. Scope extends this branch/PR with AWS
infrastructure definitions, immutable S3 archive delivery, durable hourly maintenance,
monitoring, host service definitions and deployment/readiness instructions. Cloud
account/region/budget/retention/AMI are not supplied; no AWS resources or notifications
will be created. Signer/execution and financial/evidence semantics retain their owners.

Before running new code: commit and push. Acceptance criteria: (1) Terraform formats,
validates and passes mocked-provider plan assertions without AWS credentials; private
database, protected archives, per-host IAM and no live startup defaults; (2) conditional
S3 writes verify bytes/version/retention, retries preserve identity, conflicting bytes
fail and no credentials enter output; (3) real PG maintenance outbox survives lost ACK,
restart, exhausted attempts and backward clocks, schedules hourly anchors and bounded
backups, reports failures; (4) restored application state remains quarantined; (5) service
and configuration checks fail closed on missing settings; (6) existing suite and CI
remain green. Mocked AWS tests are not hosted disaster-recovery evidence. Record all
unresolved deployment inputs, ownership and exact commands after verification.

### RT11 — architecture choices implemented (not provisioned)

The AWS definitions now cover state bootstrap, private two-AZ networking, RDS
TLS/IAM/managed admin credentials, KMS, separate Object Lock archive/release buckets,
six separate host identities, optional private EC2 hosts, optional restricted-role
HTTPS/NAT access and CloudWatch alarms. AWS provider 6.61.0 and Terraform 1.13.5 are
pinned. Cloud service availability/quotas, costs and chosen input values are not verified.
The host AMI is required before enabling hosts; none starts application code in user-data.
The selected Linux EC2 pattern remains an unprovisioned recommendation, not a claim
that D-05 or the wider infrastructure decision has been adopted by the team.

### RT12 — durable archive and operational boundary

Hourly anchors now have an immutable UTC slot and captured time, including hours
with an unchanged journal head. New migration 005 persists archive payloads, digest,
attempts, next retry, explicit terminal failures and ACK, plus a monotonic maintenance
clock. No historic state is fabricated after downtime. The S3 adapter uses conditional
creation and verifies the exact object version's bytes, KMS key and COMPLIANCE
retention. A lost acknowledgement retries the identical slot/payload; conflicting
bytes fail. Stored receipts select immutable backup versions for quarantined restore.

Backup.v1 excludes archive delivery tables to prevent recursive backup growth. A
restored deployment must use a new archive namespace after reconciliation; the old
remote history is retained. The archive process never promotes a run or signer.
Its database role can read snapshots and update archive state but cannot mutate the
financial projection. Runtime IAM tokens are generated for each TLS connection.
CloudWatch health includes archive failures/staleness and official-outbox failures/
deadline breaches; notification destinations are empty until explicitly selected.

The archive systemd timer is supplied, not installed or enabled. Startup verifies
the root-controlled manifest, code/config hashes, installed dependency pins, the
actual operations configuration, recorded registration evidence and pinned RDS CA.
A supplied registration reference is not proof of organiser acceptance; no proof is
invented. Independent signer fencing, app-to-app authentication, actual provider /
venue channels, selected image provisioning and live service startup remain owner
integration work. The Terraform templates expose no inbound application ports yet.

RT13 evidence will follow the final pushed code checks. The complete ordered work
list, required inputs, owner responsibilities and no-cloud/cloud commands are in
`docs/build/architecture-deployment.md`. No AWS resources, secrets, alarms to people,
registered uploads or real transactions were created by this follow-up.

### RT13 — follow-up verification results, 2026-10-10

Pushed implementation `5f3ecc3edd6bab9fee628175279b3d6a6b0231ed`: **70 tests passed,
44 subtests passed**, 13.06 seconds, real PostgreSQL 14.24 / Linux Python 3.12.15.
The original restart demo also passes; dependencies report no broken requirements.
New tests cover SDK-validated S3 request parameters, same-key lost ACK, changed
bytes/retention, corrupted restore downloads, hourly unchanged-head anchors, restart
budgets, backward time, backup recursion avoidance, quarantine, corrupt outbox,
audit deadline monitoring, real SQL grants denying financial-state mutation, missing
configuration, pinned CA and release-manifest tampering.

Terraform 1.13.5 / AWS provider 6.61.0: both modules validate; main infrastructure
has **3 passing mocked plan scenarios**, bootstrap **1**. No AWS credential or apply
was used. The initial `5c20936` validation caught heterogeneous conditional IAM/S3
statement types; `9ac4ab8` replaced them with filtered statement lists and the checks
pass. CI at `887f961` passes both infrastructure modules plus Python/demo/container:
[run 38029124199](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38029124199).
The final code head also runs the same CI workflow; GitHub PR #3 carries its checks.

Changes continue in [draft PR #3](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/3)
against `codex/engine-foundation`, designated reviewer Isaac. The AWS profile adds
only boto3/botocore/jmespath/s3transfer to the full lock; existing compatible urllib3,
dateutil and six pins are retained. No new Mac validation is claimed. Updated README,
ledger index and partial backlog records point to the architecture guide; no unresolved
GAP was removed. All source increments were committed and pushed before execution.

Remaining owners: Keegan/team for selections, hosted provisioning/monitoring/restore
and deployment acceptance; Isaac for independent review, signer fencing and real
execution; Keith for financial semantics; Yao Zhu for evidence/provider integration;
team for registration, final policy/window/funding evidence and declared rehearsal.
The supplied systemd unit has not been installed or exercised on a selected cloud
AMI. Local recovery and mocked cloud checks do not establish production readiness.

### RT14 — PR #3 review amendments and prospective criteria, 2026-10-10

Source: Cookiemunchrr review 5477961701 on `4718eb5`, eleven inline comments
4236713043–4236713066. All eleven are accepted implementation issues; no live
authorization or financial-policy change follows. This section and the fixes/tests
must be committed and pushed before executing affected code. Results: **NOT RUN**
at this criteria commit; append actual results separately.

| Review topic | Amendment and required regression result |
|---|---|
| Rejected/command-less round restart | A durable rejection never reruns assessment/planning; crash after HOLD plan closes COMPLETE, with no new commands. Both replay exactly even when closure occurs later. |
| In-flight audit sealing | Recovery and direct close cannot seal unresolved execution. The execution owner supplies `terminal_rounds` only after all attempts/mappings/settlement are reconciled. Restart before/after broadcast stays open; final success/revert closes once with the swap hash and ownership mapping. |
| Projection growth | Closed round records are removed from projection; complete I/O remains in journal/audit events. Eight completed HOLD rounds leave constant-size projection, with original records still retrievable and replayable. |
| Uploader permissions | Revoke the former broad UPDATE grant on re-provisioning; allow only delivery status/attempt/ACK columns. Real PostgreSQL must reject body/identity/index updates while allowing delivery updates. |
| Verification lock contention | Verify full coherent MVCC snapshots outside wallet row locks; commits/command reads compare verified authority under a short lock and reject a changed head/state. Slow maintenance verification must allow another primary commit; integrity corruption tests must still fail closed. Skip archive verification when that slot is already prepared. |
| Preparation failures and quarantine | Delivery of immutable queued archive payloads proceeds even when preparation fails or the run is quarantined. Health remains unhealthy with the preparation failure; no signing authority changes. |
| Receiver response type | JSON arrays/scalars/null cannot crash ACK handling; attempts persist, a later correct ACK succeeds, retry budgets remain bounded. |
| Nullable transaction hash | Null means absent; other invalid types raise ContractError; non-null hashes still require unique swap ownership. |
| Replay rejection/fallback | Replay recorded rejection without retrying the rejected economic plan. Closure has a durable request when no plan exists; oversize fallback replay uses the full local journal record. |
| Timezone provenance | Load pinned tzdata resources directly with one ZoneInfo instance for both directions, without changing global TZPATH/cache. DST gap/fold tests continue passing with a prepopulated host cache. |
| Zero retry timestamp | Persist explicit retry_at_ms=0 without replacing it with the original due time. |

Commands after push: Linux Python 3.12 `python -m pytest -q` against disposable
PostgreSQL, the isolated restart demo, `pip check`, and `git diff --check`; current
head CI also checks container and unchanged infrastructure plans. No live network
service, credential, wallet, or production database is involved. Retain all 13
foundation tests. Add regression tests rather than relax acceptance assertions.

Remaining limits: full integrity scans are still O(journal size), but run without
the trading row lock; this is not a constant-time verifier or a rehearsal capacity
claim. The real execution owner must implement terminal-round attestation. Final
deployment role provisioning must reapply `roles.sql` to revoke the old grant.
Existing cloud, provider, independent-review and rehearsal gates remain open.

RT14 follow-up criteria before a second run: remove synthetic completed-execution
history from fixture state and expose only nonzero reservations to new decision
contexts. Four settled synthetic swaps must leave no copied observation/completed
intent history or inactive reservations in the next snapshot; journal replay must
remain exact. This prevents the smaller fixture histories from recreating quadratic
batch growth after the large round records have been pruned. Owner production
state retention remains an explicit integration responsibility.

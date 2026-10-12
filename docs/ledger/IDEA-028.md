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

### RT15 — review-amendment verification, 2026-10-10

Pushed `4ecfaa0`: **85 tests and 49 subtests passed** against the disposable Linux
PostgreSQL database (21.49 s). Both CI triggers passed, including container/demo
and both infrastructure modules: run 38032038917 and 38032042361. No failed test
was suppressed or acceptance threshold relaxed.

Pushed final implementation `79d5ba38dd860517aa250debf721fce6dd1786d4`:
**86 tests and 49 subtests passed** (23.69 s), Linux Python 3.12.15 / PostgreSQL
14.24; all 13 foundation tests retained. `pip check` reports no broken requirements.
CI for `79d5ba3` also passes runtime/tests/demo/container and both infrastructure
modules: [run 38032177234](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38032177234).
The restart demo passes and its refreshed `docs/build/evidence/runtime-offline-trace.json`
has SHA-256 `eb713e04152fa44120d7c76c86c479f4e7298a2717057da63d0342c434a2cfc0`.
It records the broadcast, terminal success, then the COMPLETE audit with the exact
synthetic hash and decision/round mapping. Final metrics: 0 open rounds, 0 pending
audit chunks. The failed-assessment example is still labeled by its error rather
than inventing model reasoning. Older RT05–13 trace descriptions/checksums refer
to their historical commits; this file supersedes that earlier trace.

All eleven reviewer topics now have amendments and regression evidence under RT14.
The live backlog was checked: these fixes do not complete any entire remaining
GAP, so none is removed. No production roles, infrastructure or live services were
changed. PR #3 remains for re-review; integration owners and deployment/rehearsal
limits in RT14 remain open. Full snapshot verification remains linear in journal
size and must still be capacity-tested during rehearsal.

### RT16 — PR routing and next-chat handoff, 2026-10-10

Read-only GitHub checks after RT15: PR #3 remains OPEN, mergeable, targeting
`codex/engine-foundation`, at `3ee7eb5ba1bff86b3813fbebfcb9c7c7f1b482a4`.
All six checks from its push/PR triggers passed, including
[run 38032311100](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38032311100)
and run 38032314701. Cookiemunchrr's review is COMMENTED; independent acceptance
of the amended code is still pending. These results precede this documentation-only
handoff commit; do not describe them as checks of a later SHA.

[PR #4](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/4)
remains OPEN, mergeable, targeting `main`, now at
`572332fc4adb2049e7be04d6e959cf5589bff8d7`. Yao Zhu has replied to all eleven
findings from Keegan's review of `33c2f40`. Fixes are in `35c60b4`, fixtures/results
in `5ba3e88`, and the updated record in `572332f` (IDEA-025 §9.2 on that branch).
The author reports 139 tests and 514 subtests passing, plus an autocrlf checkout
check on macOS; these amended results have NOT been independently verified here.
GitHub returned no CI checks for PR #4. Actual Windows verification and the locked
environment are not established by the author's report. The replies describe a
remaining limitation: a permanently blocked evidence-store read can leave a daemon
thread waiting after the caller's assessment deadline.

Branch ancestry checked via GitHub: `codex/engine-foundation` is three commits
ahead of `main`, zero behind. PR #4 includes those foundation commits (5a6f4d7,
510dfa3, e10eae2) as well as the evidence changes, but does not include PR #3's
runtime changes. Merging #3 alone leaves main unchanged. No foundation-to-main
PR is currently open. Recommendation ONLY, not an adopted team decision: target
both component PRs at `codex/engine-foundation`, independently re-review them,
then combine them through a tested integration PR to main. No PR was approved,
retargeted, merged, or newly commented on during this routing discussion.

Next chat: re-check remote heads; independently review PR #4's amended diff and
regressions against Downloads/01-evidence-agent.prompt.txt and the common build
brief; obtain PR #3 peer re-review; agree the integration route before changing
targets or merging. Preserve the no-history-rewrite rule. Commit and push any
decision/trade/logging changes and prospective acceptance criteria BEFORE running
them. The user asked for advice and a handoff, not approval or merge execution.

Open owners: Yao Zhu for evidence fixes/provider inputs; Keith is PR #4's named
reviewer; Isaac is PR #3's designated reviewer and owns real execution, terminal-round
attestation and signer fencing; Keegan owns cross-module integration and the combined
checks. Keegan/team still own cloud selections/provisioning, final configuration,
monitoring/restore acceptance and rehearsal (RT14/15, GAP-65 and related backlog).
The user has not selected database, backup/anchor storage or hosting destinations
and asked for recommendations after the build prompt; no production activation is
authorized by this handoff. Full-journal verification capacity remains unproved.

Before this handoff-only edit, the runtime worktree was clean and fully pushed;
local main and origin/main matched. Runtime code/test evidence remains RT14/15.
Future work must distinguish component acceptance from live-trading readiness.

### RT17 — second PR #3 review: amendments and prospective criteria, 2026-10-10

Source: Cookiemunchrr's second review of `34bcde3` (2026-10-10 07:15 UTC), ten inline
comments 4236833312–4236833347. Keegan checked all ten against the code: all are
valid. This section covers the five that could stall rounds or audit delivery (#1–#5).
The five cleanups (#6 duplicated deadline formula, #7 read-only `load()`/`metrics()`
row locks, #8 request/assessment serialized twice, #9 dead `backup.anchor()`, #10
manifest built from the working tree rather than `git ls-files`) remain open for a
later change. Note for #7: the uploader's epoch check still locks `runs`, and
PostgreSQL requires UPDATE privilege for any row lock, so the `UPDATE(clock_ms)`
grant cannot simply be dropped. This section, the fixes and their tests are committed
and pushed before any affected code runs. Results: **NOT RUN** at this criteria commit;
results are appended separately.

| # | Finding | Amendment | Required regression result |
|---|---|---|---|
| 1 | Fallback audit can never succeed when the pre-execution failure came from orders or the round ID; the round stays OPEN and `recover()` stops at it | (a) Planner intents are checked against the audit order rules (`protocol.check_orders`: one of the five symbols, BUY/SELL, non-blank string amount) before anything is committed; an invalid plan becomes an empty plan with error `PLAN_INVALID`, no commands or reservations. (b) In the AUDIT_CONTENT_UNSUPPORTED fallback, and for a durably rejected plan, no order is placed, so the record's `orders` is `[]` (kit K11: orders are those the code finally decided to place). A non-string or empty round ID is refused before anything is written. (c) The event ID no longer embeds the round ID (#5). (d) `recover()` closes every closable round; a round that fails is reported in `RecoveryIncomplete` (raised after the loop, listing round IDs and error types) instead of blocking later rounds. | A numeric amount, a non-eligible symbol (USDT→BNB) and a round ID outside the protocol character set each close the round with an accepted audit, no commands, and replay exactly. A fallback round and a rejected round with planned intents each close with `orders: []`. A round whose close fails does not stop a later round from closing, and the failure is reported. |
| 2 | Every write re-verifies the whole journal and outbox (O(N) per commit, O(N²) per run) | `verified_snapshot(run_id, full=False)` on the write paths (`commit`, `command`) verifies only events after this process's last verified checkpoint (sequence, head, field digests, reservation totals, outbox ID sets and chunk count). It checks the new events' hash chain, the new outbox rows byte for byte, the full reservations table and the row counts of every outbox table. The checkpoint is in process memory: a new process, `verify()`, `takeover`, restore, journal export and maintenance anchoring all run the full verification, and any checkpoint that no longer matches the database (rewound version, changed head at the checkpoint, changed initial projection) falls back to a full verification. | After one full verification, eight commits never call the full path. Each commit reads only the events after the checkpoint. Still fail closed on the incremental path: changed run projection, changed reservations, an extra or deleted audit chunk/event/command/job row, and a changed new outbox row. `verify()` still detects a changed old event or old chunk body. All existing corruption and replay tests still pass unchanged. |
| 3 | Post-send status update has no attempt guard, so an older in-flight attempt can overwrite a newer one | A non-ACK result is written only if `attempts` still equals the attempt that sent it. An ACK is always recorded (unless the row is already ACK), because the server stored those exact bytes. | Overlapping attempts: newer 400 then older 503 stays PERMANENT; newer 503 then older 400 stays PENDING (not a false PERMANENT); newer 503 then older ACK becomes ACK. |
| 4 | Every psycopg error becomes `Unavailable` (treated as transient), including permanent constraint violations | Integrity-constraint errors (SQLSTATE class 23) raise `IntegrityError` with the SQLSTATE and constraint name (no DSN or server message). Every other database error stays `Unavailable`, including lock and statement timeouts, so plan-rejection behaviour is unchanged. | Two rounds recording the same `tx_hash` raise `IntegrityError` naming `swap_owners_pkey`, not `Unavailable`; the synthetic disk-full fault still raises `Unavailable`. |
| 5 | The ai-seeds event ID `round:<round_id>` is not scoped to the run; the server de-duplicates by event ID (kit K11: "unique per log", the resend de-dup key) | Event ID = `evt-<close timestamp ms>-<12 hex>`, the kit SDK's format, where the hex is the SHA-256 prefix of (run ID, wallet address, round ID, journal head before the close). It is deterministic, so retries resend the same ID and replay reproduces it. | The ID depends on each of run ID, wallet address (case-insensitively), round ID, head and timestamp. A run re-initialised with the same run ID and wallet that reuses round ID `entry` gets a new event ID; replay reproduces the event ID and journal head exactly; every ID matches the protocol pattern. |

Commands after push: Linux Python 3.12.15 `python -m pytest -q -p no:cacheprovider`
against disposable PostgreSQL 14.24 (CI `runtime` job), `pip check`, the offline demo,
the container build, both infrastructure modules, and `git diff --check`. All 13
foundation tests and all existing runtime tests are retained; no assertion is relaxed.
No live service, credential, wallet or production database is involved.

Known limits after these fixes: between full verifications, a change to an *old*
journal row or an old audit chunk body is detected only at the next full verification
(new process, takeover, restore, maintenance anchoring), not on every write. Full
verification remains linear in journal size and must still be capacity-tested in the
rehearsal. The committed `docs/build/evidence/runtime-offline-trace.json` still shows
the old `round:` event IDs until it is regenerated on Linux. Cleanups #6–#10 stay open.

### RT18 — second PR #3 review cleanups #6–#10: amendments and prospective criteria, 2026-10-10

Source: the same review as RT17 (comments 4236833330–4236833347). Auto-fix on PR #3
is the standing authorization for these follow-ups. As in RT17, this section, the
fixes and their tests are committed and pushed before any affected code runs.
Results: **NOT RUN** at this criteria commit.

| # | Finding | Amendment | Required regression result |
|---|---|---|---|
| 6 | Deadline formula duplicated in `maintenance.health` and `DeliveryWorker.deadline_breaches`; both load every unacknowledged audit document to read one timestamp | One helper (`protocol.breach_cutoff_ms`): an event is late iff its `timestamp_ms` is before the start of the UTC day that began 2 h before now, i.e. now ≥ next UTC midnight + 2 h, as before. Migration 006 adds `audit_events.timestamp_ms`, filled from each existing document, NOT NULL; `_audit` writes it; `_verify` checks it against the document (full and incremental). One SQL query in `delivery.deadline_breaches(db, …)` serves both callers without loading documents. | The cutoff agrees with the old formula across day boundaries. Health and the worker report the same breaches as before (existing tests unchanged). A changed `timestamp_ms` fails verification. |
| 7 | Read-only `load()`/`metrics()` take `FOR UPDATE` | Both read without a row lock. Writers still compare versions under their own lock, so a stale read can only cause a `Conflict`. The `UPDATE(clock_ms)` grant stays: the uploader's epoch check still locks `runs`, and PostgreSQL requires UPDATE privilege for any row lock. | `load()` and `metrics()` return while another connection holds `FOR UPDATE` on the run row. |
| 8 | Request and assessment serialized twice (top level and inside `policy_input`) | `policy_input` keeps the projection and reservations plus `includes: ["request","assessment"]`, naming the top-level fields that complete the policy context. The policy still receives the full context; only the stored and audited copy changes. | The audit input has the request and assessment once each. Existing oversize-fallback tests keep their purpose with a larger synthetic input (4.5 MB instead of 2.2 MB, since the duplicate no longer doubles it). Replay stays exact. |
| 9 | `backup.anchor()` (Anchor.v1) is dead; the live anchor is `Maintenance.prepare` (Anchor.v2) | Remove `anchor()`. Migration 006 drops the unused `anchors` table; it is removed from backups and from `roles.sql`. | After migration there is no `anchors` table, backup/restore round-trips and the role grants apply. |
| 10 | Manifest can hash git-ignored files | `release_files` skips host-local files (`*.local.json`, anything under `.terraform/`) on both the build and the host side. `build_manifest` refuses any release file that git does not track. | A temporary tree with `config/x/deployment.local.json` and `deploy/aws/.terraform/m/main.tf` lists neither. In a temporary git repository, an ignored `larp/extra.py` makes the tracked-file check fail. |

Commands after push: as RT17. Cleanups change the shape of the audit input (#8) and
add migration 006 (#6, #9); the demo trace is regenerated with RT17's.

### RT19 — RT17/RT18 verification results, 2026-10-10

All runs below are of pushed commits; RT17 and RT18 criteria were pushed with
their fixes before any run.

1. `0da6c24` (RT17 fixes): CI run 38035209654 **failed**, 97 passed, 3 failed, 1
   error. All three were test defects, none in the fixes: an existing maintenance
   test's `_verify` stand-in took three arguments (the same signature-only change
   had been made in `test_postgres` but missed there); the new checkpoint test
   expected versions 1–9 where each write continues from 0–8; the new fail-closed
   test re-ran `setUp` and dropped schemas twice. Fixed in `9a7f1bb`; no assertion
   was relaxed.
2. `9a7f1bb`: CI run 38035409760 **failed**, 100 passed, 7 subtests failed: the
   per-case runs shared wallet `wallet`, violating `runs_wallet_id_chain_id_key`.
   The error surfaced as `IntegrityError: 23505 runs_wallet_id_chain_id_key`,
   not `Unavailable`, which is RT17 #4 working. Fixed in `8fd6ebc` (one wallet
   per case).
3. `c40bb39` (RT18 cleanups on top): CI runs 38035762563 (push) and 38035765202
   (pull request) **passed**: **108 tests and 65 subtests passed** (48.68 s),
   Linux Python 3.12.15 / PostgreSQL 14.24; `pip check` clean; offline demo,
   container build and both infrastructure modules pass. All 13 foundation tests
   and every earlier runtime test are retained. Test-data changes only: two
   oversize fixtures grew from 2.2 MB to 4.5 MB (RT18 #8) and one raw
   `audit_events` insert gained the new `timestamp_ms` value (RT18 #6).

**Outcome: RT17 #1–#5 and RT18 #6–#10 PASS.** All 21 review threads on PR #3
(eleven from the first review, ten from the second) have replies naming the fix
commit and are resolved; the first eleven were resolved on RT15's evidence, the
second ten after run 38035762563.

Still open: `docs/build/evidence/runtime-offline-trace.json` still shows the
pre-RT17 `round:` event IDs and RT15's SHA-256; CI runs the demo but does not
commit its output, so the trace must be regenerated on a Linux host with
PostgreSQL. Between full verifications, a change to an old journal row or old
audit chunk is found only at the next full verification (RT17 known limit);
full-verification capacity is still unproved until the rehearsal. Migration 006
was run only on fresh test schemas (no pre-existing audit rows). Peer
acceptance of PR #3 (Isaac) and the integration route remain as in RT16.

### RT20 — cross-component integration: first criteria and gap inventory, 2026-10-10

Context: PRs #3 (runtime), #4 (evidence) and #6 (execution) plus `main` were merged
onto `codex/engine-foundation` (which already held PR #5, strategy) through
integration PR #8 (`codex/integration`); PR #7 is excluded by the user's
instruction. Main's IDEA-023 was renumbered IDEA-032 there. These tests are
committed and pushed before they run. Results: **NOT RUN** at this commit.

**Boundary inventory (read from the merged code):**

| Boundary | State | Gap / owner |
|---|---|---|
| Runtime → evidence: `AssessmentRequest.v1` / `AssessmentResult.v1` | Yao's `build_request` and result match `larp.runtime.schema` validators field for field | none known; C1 checks it |
| Evidence → strategy: `consume()` | Keith's adapter reads Yao's real output (captured from the golden trace at `544df90`) | fixture drift if the evidence output changes; C2 detects it |
| Coordinator → strategy policy/planner (G1) | The coordinator builds context `{projection, reservations, request, assessment}`; Keith's `decide`/`plan` need `StrategyContext.v1` (profile, `PortfolioState.v1`, markets, price series, `assessments`, `assessment_requests`, sessions, health) | G1, Keegan: a context provider port in `larp/ports.py`, then the coordinator uses it |
| Strategy plan → coordinator commit (G2) | Coordinator expects intents with `decision_id`, string `amount`, `expires_ms` and deltas `{intent_id, asset, units}`; Keith's intents carry `pay_units`/`min_receive_units`/quote fields and deltas `{cash_units, bnb_units, token_units}` | G2, Keegan with Keith: one PlanResult/reservation schema or an adapter |
| Coordinator → execution (G3) | `ports.Execution.advance(state, observation)` vs Isaac's `Executor` (`create/prepare/authorize/sign/broadcast/reconcile`) with its own `Intent` and `Store` | G3, Keegan with Isaac: adapter from command to `Executor`, and `terminal_rounds` attestation from its outcomes |
| Execution observations → accounting (G4) | The coordinator reducer updates a `balances` projection; Keith's `advance_accounting` reduces `PortfolioState.v1` | G4, Keegan with Keith: make Keith's reducer the projection reducer |
| Issuer evidence context (G5) | `consume()` needs `PolicyState.data.evidence_contexts` kept in step with Yao's issuer state; nothing updates it | G5, Keegan with Yao and Keith: decide where the context lives (PR #5 re-review note 1) |

**Prospective criteria for this commit** (`python -m pytest -q -p no:cacheprovider`, CI Linux/PostgreSQL; unittest locally):

1. C1: the evidence golden-trace request and result pass `assessment_request` and `assessment_result` at the result's completion time.
2. C2: Keith's `assessment-producer.json` request/result equal the current evidence golden trace. A failure means re-capture, not a code bug.
3. C3: the current golden-trace result, bound only to the strategy fixture's run/profile, reaches `decide()` with diagnostic `ASSESSMENT_ACCEPTED`.
4. C4: marked `expectedFailure`: a BUY round through the real coordinator, PostgreSQL store, Keith's `decide` and `plan` commits at least one execution command. It is expected to fail on G1/G2 today (no StrategyContext provider, no PlanResult adapter); an unexpected success means remove the marker and re-check.
5. Every existing test still passes (CI on PR #8 is the baseline).

Next (not in this commit): adapters for G1–G4 and the full thin path from PARALLEL_BUILD (filing → assessment → proposal → mandatory risk/planning → atomic commit → execution observations → settled accounting → durable audit → restart replay), each with its own prospective criteria.

- 2026-10-11 note (Keegan, drafted with Claude; [IDEA-042](IDEA-042.md) item 1 B2): `codex/engine-foundation` (`e8658ba`, PR #7 and main `a21d034` included) merged into this branch by a merge commit. C1 passes. C3 is rewritten for the current path (PR #7): the golden `AssessmentResult.v2` is accepted into `IssuerEvidenceState.v2`, consumed into `EvidenceContext.v1` and accepted by `decide()` with no `evidence_rejections`; the old check read `assessment_diagnostics`, which PR #7 removed. C2 is unchanged and fails until Keith re-captures `tests/strategy/fixtures/assessment-producer.json` (prompt 07 item 8), so this PR must not merge before then. C4 stays an expected failure with an updated reason (raw wiring without `ContextBuilder`, superseded by PR #7's adapters; a real BUY is blocked by entry inputs until DR-08); the deployment acceptance suite replaces it.

## 2026-10-12 RT21 — PR #9 remediation (IDEA-043), prospective criteria

C2 must use an exact capture of the reviewed producer golden request/result. C4 must use ContextBuilder, StrategyPolicy and RuntimePlanner against disposable PostgreSQL and commit a BUY execution command with resource reservations; remove the obsolete expected-failure raw wiring. C1/C3 remain real producer/consumer validation. Commit/push before execution. Whole-system/host acceptance stays separate.

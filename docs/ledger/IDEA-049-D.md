# IDEA-049-D — Final review D: accountability and operations

- Date / reviewer: 2026-10-14 / Yao Zhu, with Claude.
- Branch: `review/final-d-20261014`, cut from `codex/system-testing-20261012` at **`c1b6daf`** (merge of PR #66).
- Catalogue: [`docs/build/final-review/D-catalogue.md`](../build/final-review/D-catalogue.md).
- Protocol: [`00-common-protocol.md`](../build/final-review/00-common-protocol.md) and [the D prompt](../build/final-review/D-accountability-operations.prompt.md).
- Status: **partial review; deployment blocked.** Phase 1 frozen at `3ab45dc`; phase 2–3 fixes pushed through `e11654d`; WR-D (2026-10-15, last section) fixes #25's scheduler, #23's export/restore side and #62 item 3, and records #64 item 4 as not reproduced; team decisions (§5) and hosted gates remain open; integration not started (§9).

## 0. Preconditions (protocol §0.1), checked 2026-10-14 before section work

| Input | Disposition | Evidence |
|---|---|---|
| PR #20 merged into `codex/system-testing-20261012` | **Merged** 2026-10-14T11:27:54Z, merge commit `faf9adc` | `gh pr view 20 --json state,baseRefName,mergedAt,mergeCommit` |
| PR #21 (review prompts and runner change) integrated | **Merged** 2026-10-14T11:41:42Z, merge commit `c829fae` | `gh pr view 21 …` |
| Round driver (IDEA-048) | **Merged** through PR #66 (`claude/round-driver-20261014` → `codex/system-testing-20261012`) 2026-10-14T15:09:51Z, merge commit **`c1b6daf`**; PR head `6085347`, tested base `c829fae`. It merges the IDEA-048 branch `claude/pre-deployment-review-4zxz7p` with history kept, and PR #41 (C's profile-bound quotes / native gas quote port). | `gh pr view 66 --json mergeCommit,baseRefOid,headRefOid,body` |
| Driver's accepted scope | **Signed-execution path wired, live signing still gated** (per the PR description): `execution: "shadow" \| "service"`; the service path drives I3 → execution service → `RemoteSigner` → `SignerService` → `FencedRelease` → I4 → settlement → close, tested with a throwaway key and synthetic ports. Live signing stays blocked by C's capability gates: fake-only `Executor` (`EXECUTOR_CAPABILITY_GATE`, `larp-execution` exits 2 `NOT_INTEGRATED`), unverified router decoder (GAP-29), native top-up receipts refused (C-OPEN-005). | PR #66 description; to be verified against the code in phase 2 |
| Consequence for D | The driver is on the review base, so no §0.1 exclusion is needed. Requirements that depend on the live signer path (Gate B) stay `NOT-OFFLINE`/blocked until C's gates lift; a shadow or gated path is not proof of the live `ExecutionService`/signer path. | — |

No AWS action, wallet key, `AI_SEEDS_SECRET`, ai-seeds `log()`, signing, broadcast or organiser contact is part of this review (§0.6).

## 1. Environment (protocol §0.4)

- macOS (darwin), Python **3.12.14** venv in the session scratch directory from `deploy/requirements-test.lock` (installed as CI does, `pip install -r`; `pip check` clean).
  - Observation (setup only): `pip install --require-hashes -r deploy/requirements-test.lock` fails because `psycopg==3.3.6` has no hash line; recorded as D-ASM-020, to be checked in phase 2.
- PostgreSQL **14.24** from `deploy/compose.test.yml` (pinned digest), project `larpd`, loopback port 55432, database `larp_test`.
- Docker 29.4.3 (Docker Desktop started for this review).
- Terraform 1.13.5: **not installed on this machine**. Phase 2 will use the official `hashicorp/terraform:1.13.5` image or report the Terraform tests as NOT RUN locally and rely on Linux CI.

## 2. Phase 1

Catalogue frozen in the commit that adds this file: 92 requirements, 30 assumptions, 69 use cases, 13 conflicts, coverage of every item in D's scope inventory. Input gap: the kit's demo code and SDK `examples/` are not preserved in the repo, so F-106/F-111 cannot be re-checked against verbatim text (D-ASM-029).

## 3. Baseline (protocol §0.5)

Run after the freeze was pushed, before any phase-2 change, on `3ab45dc` (base `c1b6daf` plus the two phase-1 docs; no code change): `LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/larp_test python -m pytest -q -p no:cacheprovider -rs`.

**1229 passed, 7 skipped, 1561 subtests passed** (129 s). Skips: 1 opt-in external recorded-market artifacts (`tests/marketdata/test_recorded.py:29`), 3 disposable systemd runner not enabled (`tests/runtime/test_systemd_conditions.py`), 3 Linux bubblewrap (`tests/runtime/test_worker_release.py`). All environmental; Linux CI runs the bubblewrap and systemd cases.

## 4. Phase 2: pre-registered criteria and suspected defects

Written 2026-10-14 after reading the code (trace: catalogue §8), and committed before any of these tests is written or run. Prior issues read only after the freeze (protocol §2.1): tracker #22 (#23–#40) and the later tracker #42 (#43–#64), re-fetched 2026-10-14.

### 4.1 Suspected defects (D-owned unless stated)

| ID | Sev | Requirement | Suspected defect | Issue |
|---|---|---|---|---|
| D-FND-001 | P0 | D-REQ-014, 075 | `DeliveryWorker` marks every 4xx except 429 PERMANENT and never resends it. A single 401 `TIMESTAMP_SKEW` (or a 401 before the final wallet's secret is registered) leaves the log undelivered and the `DELIVERY_DEADLINE` HALT latched for the rest of the run: a lost/late log and an unrecoverable HALT. | #50 (P2 → P0 under §3), #29 remnant |
| D-FND-002 | P0 | D-REQ-001, 003, 018, 026 | The round log is built only when the round closes, which needs every intent to be final. A broadcast swap that stays unconfirmed keeps its round open with no audit event, so its `tx_hash` reaches no log and the deadline check cannot see it. | #28 |
| D-FND-003 | P1 | D-REQ-070 | `load_runtime_secrets` turns any Secrets Manager exception (throttle, timeout, network) into `LiveStartRefused` → exit 4, which systemd never restarts. A reboot with a slow network leaves the runtime down until a person acts. (The uploader side is already restartable: `SecretUnavailable`, exit 1.) | #43 |
| D-FND-004 | P1 | D-REQ-076 | No watchdog: a `driver.once` that blocks keeps the process alive, so no restart; rounds and heartbeats stop; only an alarm fires. | #35 (P2 → P1: no autonomous recovery) |
| D-FND-005 | P1 | D-REQ-023 | Signed bytes (`raw_hex`) are stored in `execution_records.state` and exported unredacted in backups. Fix owner: C (execution state), with D (export). | #23 |
| D-FND-008 | P1 | D-REQ-035 | No journal upload after an incident (declared "uploaded daily, and after any incident"). | — |
| D-FND-009 | P2 | D-REQ-036, 085 | Archive outbox rows become EXHAUSTED after 8 tries and are never retried; `health()` reports `ARCHIVE_DELIVERY_BLOCKED` for the rest of the run. A missed anchor slot leaves no incident record. | #64 item 1 |
| D-FND-010 | P1 | D-REQ-059 | A `live` run can be activated while deviation rows are OPEN or DRAFT (G-11; plan.md §6.5 "Final at the Oct 26 freeze"). | — |
| D-FND-011 | P1 | D-REQ-055 | The host bundle is not byte-reproducible (gzip header time); CI keeps no bundle artifact; CI `push` runs only on an obsolete branch, not on `main`, `codex/system-testing-*` or `review/final-*`. | #49 |
| D-FND-013 | P1 | D-REQ-062 | No secret scan runs in CI (G-41 "CI scan on every push [TEST]"). | — |
| D-FND-014 | P2 | D-REQ-072 | A deterministic exception in `driver.once` (e.g. `RecoveryIncomplete`) crash-loops every 10 s with a RESTART incident each time. Recorded for a team decision. | — |
| D-FND-015 | P2 | D-REQ-089 | No host-disk metric or alarm; no growth estimate. | — |
| D-FND-016 | P2 | D-REQ-103 | Budget is monthly and cannot track the one-off $100 credit. | #63 |
| D-FND-017 | P1 | D-REQ-105 | Only system-status failures recover a host; an instance-status failure (kernel panic, OOM) has no automatic reboot. | #60 part 2 |
| D-FND-018 | P2 | D-REQ-135 | The internet-facing evidence poller can reach the instance metadata service and so read every secret through the shared role. | #61 |
| D-FND-019 | P3 | D-REQ-111 | `larp-runtime.service` is not ordered after `time-sync.target`. | — |

### 4.2 Pass criteria for new tests (written before the tests)

All run against real PostgreSQL 14.24 (`LARP_TEST_DATABASE_URL`) with fakes only at the receiver, S3, Secrets Manager and chain boundaries. A test that fails before its fix is the finding's evidence; it is pushed before the fix.

| Test | Requirement | Pass criterion |
|---|---|---|
| `tests/audit/test_final_review_d.py::test_d_req_014_a_401_then_recovery_acks_and_clears_the_halt` | 014, 075 | A chunk answered first with HTTP 401 (`TIMESTAMP_SKEW`) and later with 200 `STORED` ends `ACK` with its stored acknowledgement and the same bytes; after the deadline the guard HALTs, and once ACKed the `DELIVERY_DEADLINE` HALT clears through a journaled clear, with no manual step. |
| `…::test_d_req_014_auth_and_conflict_4xx_retry_with_backoff_and_stay_visible` | 014 | 401, 403, 408 and 409 leave the chunk retryable (not PERMANENT) with growing, capped backoff; while unacknowledged the event is reported undelivered (never DELIVERED). |
| `…::test_d_req_015_payload_rejections_stay_failed_and_are_not_resent` | 014, 015 | 400 and 413 remain `PERMANENT` (visible as FAILED) and are not resent on later cycles. |
| `tests/runtime/test_final_review_d.py::test_d_req_003_a_broadcast_swap_is_logged_before_finality` | 001, 003, 018, 026 | Service execution: once a swap's `BROADCAST_ATTEMPTED` fact is journaled and every planned intent is broadcast or terminal, the next driver cycle commits exactly one audit event for the round carrying that swap's `tx_hash`, while no final receipt exists. The later FILL is settled into the journal, the round then closes **without** a second audit event, and replay of the journal reaches the same head. |
| `…::test_d_req_018_an_unlogged_open_round_past_the_deadline_is_overdue` | 018 | An open round with a planned intent that has no disposition by the next 02:00 UTC is counted overdue by the guard (DELIVERY_DEADLINE HALT), even though no audit event exists yet. |
| `…::test_d_req_070_transient_secret_errors_restart_and_definite_ones_refuse` | 070 | Throttling / 5xx `ClientError`, connection or read timeout and an unclassified exception raise a restartable error (service exit 1); `ResourceNotFoundException`, `AccessDeniedException` and malformed content remain start refusals (exit 4). No error text contains the secret value. |
| `…::test_d_req_076_a_hung_cycle_exits_for_a_supervised_restart` | 076 | `Service` with a cycle timeout: a `driver.once` that blocks longer than the timeout triggers the watchdog's exit hook with exit status 1 and leaves the session open (counted as a crash on the next start). A cycle that finishes in time never triggers it. `validate_config` requires `cycle_timeout_seconds` for `dev`/`live` modes. |
| `tests/runtime/test_final_review_d.py::test_d_req_035_an_incident_triggers_an_extra_journal_upload` | 035 | After a RESTART incident or HALT committed since the last archived backup, `Maintenance.prepare` enqueues one extra backup inside the same backup interval; a second `prepare` for the same incident enqueues nothing more. |
| `…::test_d_req_085_backups_keep_retrying_and_a_newer_ack_clears_archive_health` | 036, 085 | A backup row is retried after more than `max_attempts` failures and ACKs when the archive recovers; an anchor slot that could not be delivered within its hour is reported once as missed and stops blocking `health()` after a later anchor is ACKed. |
| `…::test_d_req_059_live_activation_refuses_open_or_draft_deviations` | 059 | `activate_run` for a `live` run refuses (exit-4 refusal) while the manifest's register has OPEN or DRAFT rows; a `dev` run may still be activated. |
| `tests/runtime/test_final_review_d.py::test_d_req_055_bundle_archive_is_byte_reproducible` | 055 | Two `build()` calls with identical fetch/wheel fakes produce archives with identical SHA-256. |
| `…::test_d_req_055_ci_keeps_the_bundle_and_runs_on_the_branches_that_ship` | 055 | The workflow uploads the built bundle and its `.sha256` as an artifact and its `push` trigger covers `main`, `codex/system-testing-*` and `review/final-*`. |
| `…::test_d_req_062_no_credentials_are_tracked` | 062 | A scanner over `git ls-files` finds no private-key block, AWS access key ID, populated `*_SECRET`/`*_PRIVATE_KEY`/`MNEMONIC` assignment or tracked `.env`/`*.tfvars`/`*.tfstate`; the same scanner flags a planted example of each. Runs in the CI pytest job on every push. |
| `…::test_d_req_023_backups_carry_no_usable_signed_bytes` | 023 | Exporting an execution record whose state holds a SIGNED_DURABLE attempt with `raw_hex` yields a backup in which the raw hex appears nowhere. (Expected red until C changes the execution state; recorded under "For other sections".) |
| `…::test_d_req_105_instance_status_failure_reboots_the_host` | 105 | Terraform declares, per host, a `StatusCheckFailed_Instance` alarm whose actions include `arn:aws:automate:<region>:ec2:reboot`. (Static test on the Terraform source, plus a `terraform test` run in CI.) |
| `…::test_d_req_135_evidence_poller_cannot_reach_instance_metadata` | 135 | `larp-evidence.service` sets `IPAddressDeny=169.254.169.254/32`. |
| `…::test_d_req_111_runtime_starts_after_time_sync` | 111 | `larp-runtime.service` has `After=` including `time-sync.target`. |
| `…::test_d_req_103_a_budget_covers_the_whole_credit_period` | 103 | Terraform declares a COST budget with a custom period from the deployment start to at least 2027-01-01 with the $100 credit as its limit, besides the monthly pace budget. |

**Amendment A1 (2026-10-14, before any fix; disclosed ordering).** The criterion for `test_d_req_085_…` is replaced by `test_d_req_085_a_newer_ack_supersedes_an_exhausted_slot_in_archive_health`: an archive slot that exhausted its attempts stays EXHAUSTED (the existing `test_persistent_failures_exhaust_without_hiding_health` keeps per-cycle work bounded, and IDEA-036 #2 forbids writing a past anchor slot late), `health()` lists every exhausted slot under `missed` (the logged record of a missed anchor/backup), keeps `ARCHIVE_DELIVERY_BLOCKED` while no newer slot of that kind is ACKed, and drops it once a newer anchor and backup are ACKed. Reason: a later full backup and a later anchor supersede the missed ones, so retrying a past anchor would break the no-late-write rule. Disclosure: this test was run once locally (red, `KeyError: 'missed'`) a few minutes before this amendment was committed; no fix existed at that time.

The deliverable test for #23 (`test_d_req_023_…`) is committed with `unittest.expectedFailure`: the fix belongs to C's execution-state code (D-FND-005, §7). The marker must be removed in the same change that fixes it; an unexpected pass fails the suite.

**Amendment A2 (2026-10-14, after the first fix round, before its test is written).** D-FND-020, P2, D-REQ-030/032 (#51): when a plan commit is rejected (`Conflict`), `record_rejection` reloads the projection and drops the evidence updates the context builder accepted that round, so the next round re-processes them against old evidence versions. Criterion for `tests/runtime/test_final_review_d.py::test_d_req_032_a_rejected_plan_keeps_the_rounds_evidence_updates`: after a round whose plan commit is rejected, the stored projection holds the builder's updates exactly as an accepted round would, the round still has one log with `COMMIT_REJECTED`, and replay of the journal reaches the same head. Disclosure: the criterion was written to the file before the test ran, but the single local red run (`evidence: None`) happened before this commit was pushed.

**Amendment A3 (2026-10-15, before its test is written).** D-FND-021, P1, D-REQ-089/035 (found in my own D-FND-008 fix during the adversarial pass): a crash loop journals a RESTART incident every ~10 s, so `prepare` (every minute) would queue a full database export each minute, and every ACKed archive row keeps its payload in `archive_outbox` for good. The database could fill during the run. Criterion for `tests/runtime/test_final_review_d.py::test_d_req_089_incident_backups_are_rate_limited_and_acked_payloads_released`: many incidents within one hour produce at most one incident backup per hour beyond the scheduled ones; once a row is ACKed its stored payload is released (length 0) while its slot, SHA-256 and receipt stay; a lost ACK still resends the identical bytes (existing test).

Every round of fixes is followed by the full suite, `tools/system_test.py` on this pushed branch, and Linux CI (Terraform and host-bundle jobs included).

### 4.3 Findings: fixes and retests

Commits (each pushed before it ran): criteria `c609dc5`; failing tests `b5b0f23`; fixes `bb8fb3d`; D-FND-020 test `6a15214`, fix `b1450fa`; D-FND-021 test `620a83e`, fix `e11654d`. Retest counts are in §10.

| ID | Sev | Status | Evidence (red before fix) | Fix | Retest |
|---|---|---|---|---|---|
| D-FND-001 | P0 | **Fixed** | `tests/audit/test_final_review_d.py::test_d_req_014_*` red at `b5b0f23` (chunk PERMANENT after 401) | `bb8fb3d` `larp/audit/delivery.py`: only 400/413/422 are permanent; every other refusal keeps the capped backoff | green; `test_delivery.py::test_permanent_and_transient_errors_remain_visible` now expects 401 PENDING (that line asserted the defect; 400/413 stay PERMANENT) |
| D-FND-002 | P0 | **Fixed** | `test_d_req_003_*` (0 logs while the swap was unconfirmed), `test_d_req_018_*` (no HALT) red at `b5b0f23` | `bb8fb3d`: `Coordinator.disposed/log_round`, `ServiceExecution.log_disposed`; `close` of a logged round writes no second log; `recover` closes logged rounds once final; replay of `ROUND_LOGGED` and log-less `ROUND_CLOSED`; `unlogged_rounds` in the guard and `OverdueLogs` | green; E1–E10, settlement, live replay unchanged and green |
| D-FND-003 | P1 | **Fixed** | `test_d_req_070_*` red at `b5b0f23` (exit 4) | `bb8fb3d` `larp/runtime/credentials.py`: `DEFINITE_SECRET_ERRORS` refuse; anything else raises `SecretsUnavailable` → exit 1 → restart | green; `test_credentials.py` fake now raises a definite `AccessDeniedException` (an unclassified error is now restartable by design, covered by the new test) |
| D-FND-004 | P1 | **Fixed** | `test_d_req_076_*` red at `b5b0f23` | `bb8fb3d` new `larp/runtime/watchdog.py`; `Service(cycle_timeout_s=…)`; `cycle_timeout_seconds` required for dev/live; example 600 s (D-ASM-031) | green |
| D-FND-005 | P1 | **Open (C)** | `test_d_req_023_*` red; committed as `expectedFailure` | Owner C: keep `raw_hex` only in `execution_signatures` (§7) | xfail |
| D-FND-008 | P1 | **Fixed** | `test_d_req_035_*` red at `b5b0f23` | `bb8fb3d` `Maintenance.prepare` + `migrations/010_incident_backups.sql` (`covers_sequence`) | green |
| D-FND-009 | P2 | **Fixed** | `test_d_req_085_*` red at `b5b0f23` | `bb8fb3d` `Maintenance.health`: `missed` slots listed; blocked only until a newer slot of the kind is ACKed (amendment A1) | green; existing exhaustion test unchanged and green |
| D-FND-010 | P1 | **Fixed** | `test_d_req_059_*` red at `b5b0f23` | `bb8fb3d` `register.load_register` reports `draft_deviations`; `activate_run` refuses a `live` run with OPEN/DRAFT rows | green. **Consequence:** the final activation is blocked until the team makes every deviation row FINAL (D-DN-01..03). |
| D-FND-011 | P1 | **Fixed (repo side)** | `test_d_req_055_*` red at `b5b0f23` | `bb8fb3d`: gzip header without time or name; CI `push` on `main`, `codex/system-testing-*`, `review/final-*`; bundle + `.sha256` uploaded (`actions/upload-artifact` pinned `ea165f8…`, v4.6.2, 90 days) | green; CI run 38593987008 `host-bundle` uploaded the artifact. Remaining procedure items under #62 (manifest built in CI, runbook text). |
| D-FND-013 | P1 | **Fixed** | — (the scan is the test) | `b5b0f23` `tests/runtime/test_final_review_d.py::CredentialScan` runs in the CI pytest job on every push/PR | green: no credential file or populated secret tracked |
| D-FND-014 | P2 | **Open (decision)** | — | D-DN-07 | — |
| D-FND-015 | P2 | **Open** | — | Host-disk metric/alarm not built; growth estimate in §6 R-09 | — |
| D-FND-016 | P2 | **Fixed** | `test_d_req_103_*` red at `b5b0f23` | `bb8fb3d` `aws_budgets_budget.credit` (2026-10-01 → 2027-04-12, $100, ACTUAL 50/75/90 + FORECASTED 100) | green; TF `budget_alerts_with_recipient` asserts it |
| D-FND-017 | P1 | **Fixed** | `test_d_req_105_*` red at `b5b0f23` | `bb8fb3d` `aws_cloudwatch_metric_alarm.reboot` per host | green; TF `host_isolation` asserts it |
| D-FND-018 | P2 | **Fixed** | `test_d_req_135_*` red | `bb8fb3d` `IPAddressDeny=169.254.169.254/32` in `larp-evidence.service` | green. The unused `evidence` secret in `hosts.tf` stays (Terraform change for Keegan/team; harmless). |
| D-FND-019 | P3 | **Fixed** | `test_d_req_111_*` red | `bb8fb3d` `After=… time-sync.target` | green |
| D-FND-020 | P2 | **Fixed** | `test_d_req_032_*` red at `6a15214` | `b1450fa` `record_rejection(…, updates)`; `PLAN_REJECTED` carries `updates`; replay re-applies them | green |
| D-FND-021 | P1 | **Fixed** | `test_d_req_089_*` red at `620a83e` (30 backups in an hour) | `e11654d` one incident backup per hour; ACKed payloads released | green |

Test changes beyond new tests, disclosed: two existing assertions encoded behaviour this review found contradicted (`test_delivery.py` e401, `test_credentials.py` fake error), changed with comments, never weakened; in my own new test file the CI-trigger regex now tolerates a comment line and the planted private-key fixture is split so the scanner does not flag its own source. Terraform: `fmt`, `init -backend=false -lockfile=readonly`, `validate`, `test` run locally in `hashicorp/terraform:1.13.5` (linux/amd64, copy of the tracked files, no credentials): `deploy/aws` 15/15, `deploy/bootstrap` 1/1.

### 4.4 Prior issues reconciled on this tree (protocol §2.1; trackers #22 and #42 re-fetched 2026-10-14)

Mapped severity per protocol §3. "Resolved here" means verified on `review/final-d-20261014`; closing the GitHub issue is the team's step after merge.

| Issue | Primary | Mapped sev | Disposition on this tree |
|---|---|---|---|
| #23 R01 signed bytes in backups | D (code in C) | P1 | **Open.** D-FND-005; failing test in tree (xfail). Needs C's state change (§7). |
| #24 R02 market after cutoff | C | P1 | Runtime side verified: `test_e7_the_decision_time_is_never_before_the_market_observations` (PR #66). Producer side with C. |
| #25 R03 issuer IDs | A | P1 | Not D. Open with A. |
| #26 R04 stranded command | D | P1 | **Resolved here** by PR #66: `ServiceExecution.reauthorize` (restart moved the version), `expire` (HALT-refused or unclaimed commands end NOT_SUBMITTED and release reservations); tests `test_r3_*`, `test_e4_*` green on real PostgreSQL. |
| #27 R05 swap deadline | C | P1 | Not D. Open with C. |
| #28 R06 pending broadcast unlogged | D | **P0** | **Resolved here** (D-FND-002). |
| #29 R07 audit outage | D | P1 | **Resolved here**: transient part by IDEA-047 R1; 4xx by D-FND-001; archive side by D-FND-009. Old `EXHAUSTED` audit rows: no hosted run exists yet, so none to migrate. |
| #30 R08 gas top-up path | C | P1 | D side (round kind, BNB order, mapping) covered by `test_l3_l4_gas_topup_round`; native receipts refused (C-OPEN-005). Open with C. |
| #31 R09 daily anchor | B | P1 | D side (journaled `DAY_ROLLED`, replay) verified by `test_e8_*`, `test_r2_*`. Policy with B. |
| #32 R10 deployment routes | D | P1 | Two-host layout: execution and evidence on `primary` (HTTPS egress when enabled), signer through the database; TF `internet_reaches_primary_only`. **Open as a hosted check** (Gate A, AWS_RUNBOOK): reach Web3/RPC/SEC/ai-seeds from `primary`. |
| #33 R11 blocked application | D (+C) | P1 | Driver integrated (PR #66). **Open blocking dependency:** C's capability gates (fake-only Executor, GAP-29 decoder, C-OPEN-005), live profile/calendar/issuers, terms hashes, hosted assessor (DR-11). |
| #34 R12 HALT vs mandatory planning | B | P1 | Team decision (D-DN-09). D runtime acceptance: `test_e5_*` show current semantics (HALT stops every signature, reconciliation continues). |
| #35 R13 hang supervision | D | **P1** | **Resolved here** (D-FND-004) + heartbeat alarm (IDEA-047 R5). |
| #36 R14 balance reconciliation | B | P1 | Not built (D-REQ-039 MISSING). Open with B; D provides scheduling once it exists. |
| #37–#39 | B/A | P2 | Not D. |
| #40 R18 slippage | C | P1 | Fixed by PR #41 (C). |
| #43 WR01 secrets at boot | D | P1 | **Resolved here** (D-FND-003); uploader side already restartable (IDEA-047 R14). |
| #44–#48, #53–#58 | A/B/C | — | Not D. |
| #49 WR07 release integrity | D | P1 | **Resolved here, repo side** (D-FND-011). Remaining: manifest produced in CI and only verified on hosts (#62 item 3, runbook procedure). |
| #50 WR08 4xx permanent | D | **P0** | **Resolved here** (D-FND-001). |
| #51 WR09 rejected plan drops evidence | D | P2 | **Resolved here** (D-FND-020). |
| #52 WR10 HALT and in-flight signing | C/D | P2 | PR #66 `RunAuthorization` reads HALT; `test_e5_a_halt_after_the_approval_stops_the_swap_signature`. Final semantics with #34 (D-DN-09). |
| #59 WR17 runtime unit paths | D | P2 | **Resolved** by PR #66 (`StateDirectory=larp-runtime`, `config/runtime/runtime.example.json`, `test_e9_*`). |
| #60 WR18 memory / instance check | D | P1 / P2 | Instance-status reboot **resolved here** (D-FND-017). Memory limits vs `t3.small`: D-DN-08. |
| #61 WR19 IMDS from evidence | D | P2 | **Resolved here** (D-FND-018). |
| #62 WR20 runbooks vs code | D | P2 | Shared-doc edits at integration (§8). |
| #63 WR21 budget | D | P2 | **Resolved here** (D-FND-016). |
| #64 WR22 item 1 archive retries | D | P3 | **Resolved here** (D-FND-009). Items 2–4: C/B/A. |

**Review-record collision:** tracker #22 still names the trading review "IDEA-046 / GAP-68"; `docs/ledger/IDEA-046.md` stays the hosting record. No published original record under a new ID was found on the integration, B or C branches (checked 2026-10-15). Input gap, owner Keith, before full completion.

## 5. DECISION-NEEDED (team)

| ID | Question | Options | Recommendation |
|---|---|---|---|
| D-DN-01 | Standby (D-CON-03): declared "one primary runtime plus a fenced cold standby"; IDEA-046 B1 built two hosts and no standby; DEV-18 is OPEN. | (a) Decide DEV-18 as a deviation: no standby; recovery = supervisor restart + EC2 recover/reboot + RDS; record reason (budget, B1) and evidence. (b) Build a fenced cold standby (third host, cost). | (a), with the RTO/RPO in §6 stated in the register. Final activation is refused until DEV-18 is decided (D-FND-010). |
| D-DN-02 | Rehearsal (D-CON-04): declared 5+ days incl. a weekend at minimum size, signer on; signing is still gated (C) and Gate B (Oct 20) is at risk. | (a) Keep: signed rehearsal Oct 21–26 covering Oct 24–25. (b) Shadow rehearsal + shorter signed window, recorded as a deviation. | Decide by Oct 19; if C's gates are not lifted by Oct 20, take (b) and record it the same day (GAP-04). |
| D-DN-03 | Every DEV row is DRAFT; DEV-19 (assessor) and DEV-20 (event planner) are OPEN. | Finalize each row by Oct 26. | Required: the live activation now refuses otherwise. |
| D-DN-04 | Delivery bound before the 02:00 UTC deadline (D-REQ-025): today signing continues while round logs are undelivered until the deadline passes. | (a) Add a guard HALT when the oldest unacknowledged log is older than B (e.g. 2 h). (b) Accept the risk. | (a) with B = 2 h: it limits how many fills can become "fill without log" during a receiver outage. Needs B's view on HALT semantics (#34). |
| D-DN-05 | Routes for migrations/roles on RDS and for provisioning the signer (D-REQ-108): no host can read the RDS admin secret; the signer has no internet. | (a) One-off development SSM session on `primary` to run migrations with the admin secret, before Gate A; signer bundle from the S3 gateway endpoint (artifact bucket) with the key copied over SSM. (b) Temporary bastion. | (a); never during the scored run; record each step in the AWS runbook. |
| D-DN-06 | Watchdog timeout (`cycle_timeout_seconds`, example 600 s). | Value per measured cycle length. | Keep 600 s unless rehearsal shows cycles above 300 s (D-ASM-031). |
| D-DN-07 | Crash loop on a deterministic error (D-FND-014): restarts every 10 s forever, one RESTART incident each. | (a) Accept (the agent fails closed; incidents are rate-limited for backups). (b) Escalate to a HALT after N restarts per hour. | (a) for v1.0 unless rehearsal shows a loop; incident volume is bounded by D-FND-021. |
| D-DN-08 | Memory (#60): unit `MemoryMax` sum 3 GiB on a 2 GiB `t3.small`. | (a) `t3.medium` (cost vs credit). (b) Tighter limits + `MemoryHigh` + swap. | Measure RSS in the hosted shadow run (Gate A), then choose; instance-status reboot now covers an OOM hang. |
| D-DN-09 | HALT semantics (#34, #52; B owns): HALT now blocks every signature including mandatory sells; reconciliation continues. | B's options. | B decides; D's guard and tests follow. |
| D-DN-10 | Clock HALT (D-CON-09) is latched for the run: one backward clock step stops trading until the end. | (a) Keep latched. (b) Autonomous clear after the clock is monotonic and NTP-synchronised for N minutes; integrity quarantine stays latched. | (b) with N = 30 min, because F-114 forbids a person clearing it; needs B's agreement with D-DN-09. |
| D-DN-11 | Restore during the scored run: a restored run is quarantined and needs `activate` by a person (F-114 forbids it). | (a) Accept: losing the database ends trading for the run (single-AZ RDS, 1-day PITR, daily + incident backups). (b) Pre-registered automatic re-activation after anchor-verified restore. | (a), stated as a deployment risk; (b) is too much new code after the cut line. |

## 6. Deployment risks

| ID | Risk | Owner | Validation step | Deadline | Blocking? |
|---|---|---|---|---|---|
| R-01 | Hosted round logs never tested against the real receiver (401/413 behaviour, clock, address registration). | Keegan + Yao Zhu | Gate A: one dev-wallet shadow round, committed code, ACK stored | Gate A | yes (Gate A) |
| R-02 | Final wallet's `AI_SEEDS_SECRET` (Q-35/D-ASM-018). | Team | Confirm with organisers' Telegram contact; uploader `check` with the new secret | Oct 26 | yes (Gate C) |
| R-03 | AWS credit exhaustion closes the account (D-ASM-008/009). | Team | Credit budget alerts (D-FND-016) applied; spend projection at Gates B/C | Gate B | yes |
| R-04 | EC2 recover/reboot behaviour and service restart after it (D-ASM-010/011). | Keegan + Isaac | Host drill: stop the runtime, reboot `primary`, check RESTART incident and resumed delivery | Gate B | no (drill) |
| R-05 | Single-AZ RDS failure or maintenance; 1-day PITR; restore needs a person (D-DN-11). | Team | Restore drill into an empty DB with anchors (IDEA-036 #5) | Gate B | no (accepted risk if D-DN-11 = a) |
| R-06 | Signer journald and primary journald are not shipped; collected by EBS snapshot at teardown (AWS_RUNBOOK "Journald log shipping"). | Keegan | Snapshot procedure in teardown checklist; test once | Before teardown | no |
| R-07 | Hosted network routes (#32): Web3, RPC, SEC, ai-seeds from `primary`; signer via DB only. | Keegan + Isaac | Gate A read-only reachability check | Gate A | yes |
| R-08 | Clock: no in-process absolute drift check; relies on chrony/Amazon Time Sync (D-REQ-111). | Keegan (A/B for G-05) | `chronyc tracking` on both hosts at Gate A; alarm on drift | Gate A | no |
| R-09 | Database growth over 18 days (D-FND-015): journal + model I/O + backups. ACKed backups no longer stay in the DB (D-FND-021); measured bytes/round needed. | Keegan | Measure bytes per round in the hosted shadow run; extrapolate × 18 days vs 20→30 GiB | Gate B | no |
| R-10 | Host disk (journald, evidence artifacts) has no alarm (D-FND-015). | Keegan | Add a disk metric or size journald limits | Gate B | no |
| R-11 | Week-one checkpoint commit and progress note (F-13) not yet recorded. | Team | Commit + note | Oct 19 | yes (deliverable) |
| R-12 | On-call rota (GAP-37): during the run people observe only (F-114). | Team | Dated rota in the activation pack | Oct 26 | no |
| R-13 | Restart and coded HALT are team positions (Q-40, C5), not organiser answers (D-ASM-016). | Team | Ask with the open questions (wording in D-CON-01) | Before Oct 27 | no |
| R-14 | Bundle reproducibility depends on the live RDS CA download and on PyPI serving the same wheels (D-ASM-021). | Keegan | Rebuild the CI bundle locally from the activation commit and compare hashes | Gate C | no |

## 7. For other sections

| To | Item | Evidence |
|---|---|---|
| C (Isaac) | **#23 / D-FND-005 (P1):** keep signed bytes only in `execution_signatures`; remove `raw_hex` from `execution_records.state` (`larp/execution.py` Attempt, `execution_live/store.py`), broadcasting by registry lookup. Then remove `expectedFailure` from `tests/runtime/test_final_review_d.py::SignedBytesInBackups`. | Failing test in tree; C's record assigns #23 to D but the code is C's. |
| C (Isaac) | Signed rehearsal depends on lifting the capability gates (#33): fake-only `Executor`, GAP-29 decoder, C-OPEN-005. | §4.4 |
| B (Keegan) | #34/#52 HALT semantics (D-DN-09), clock HALT clearing (D-DN-10), delivery bound (D-DN-04), #36 reconciliation (D-REQ-039 MISSING; D adds scheduling). | §5 |
| A (Keith) | Publish the trading review under an unused ledger ID with its evidence (tracker #22 collision); G-05 absolute clock check (R-08). | §4.4 |
| All | New migration `010_incident_backups.sql` is taken; coordinate any further number with D. | `migrations/` |

## 8. Requested shared edits (D applies at integration)

- `docs/INCOMPLETE_WORK.md`: GAP-35 — add "missed anchor/backup slots are listed by `health().missed`, superseded by later ACKs (D-FND-009); incident uploads (D-FND-008/021)". GAP-46 — "round logs are committed when orders are disposed, before finality (D-FND-002); only payload refusals are permanent (D-FND-001)". GAP-62 — "final activation refuses OPEN/DRAFT rows (D-FND-010)". Add the deployment risks R-01..R-14 not already listed.
- `docs/build/AWS_RUNBOOK.md` and `docs/build/runbook.md` (#62): wallet key is `/etc/larp/signer/wallet.key` on the signer host (no Secrets Manager entry); uploader secret ID is `${name}/uploader`; the release manifest is built in CI with the bundle and only verified on hosts; take the bundle and its `.sha256` from the CI artifact `larp-bundle-x86_64`; `cycle_timeout_seconds` in `runtime.json`; migrations route per D-DN-05.
- `docs/LEDGER.md`: add rows IDEA-049-D (this record) and, once published, Keith's trading review under its new ID.
- `docs/skill/SKILL.md`: none required by D (no summary found unfaithful; F-106/F-111 could not be re-checked, input gap D-ASM-029).

## 9. Integration status (protocol: D runs it last)

Checked 2026-10-15: A has no branch or PR; B's PR #65 is open and green (head `4711ce6`, 15 commits behind the base); C's PR #41 merged, and `review/final-c-20261014` has 27 newer commits with no open PR. Integration step 1 needs all three PRs, so **integration has not started**. D's own PR is opened for review. Overall: **partial review; deployment blocked** (open P1 #23 and the blocking dependencies above).

## 10. Final counts and CI

| Run | Commit | Result |
|---|---|---|
| Local baseline (§3) | `3ab45dc` | 1229 passed, 7 skipped, 1561 subtests |
| Local full suite after fixes | `b1450fa` | 1252 passed, 7 skipped, 1 xfailed (#23), 1593 subtests |
| Linux CI [38593987008](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38593987008) | `bb8fb3d` | all four jobs PASS; pytest 1254 passed, 4 skipped, 1 xfailed, 1593 subtests |
| Linux CI [38594705007](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38594705007) | `e11654d` (last code change) | all four jobs PASS; pytest **1256 passed, 4 skipped, 1 xfailed, 1593 subtests**; systemd conditions 3/3; Terraform `deploy/aws` 15/15, `deploy/bootstrap` 1/1; host bundle provisioned and uploaded as artifact `larp-bundle-x86_64` |
| `tools/system_test.py` (full mode, fresh clone of the pushed head, disposable PostgreSQL 14.24, macOS + Linux CI for the demo) | `a56eb25` | **PASS**: system 112 passed, 70 subtests (log sha256 `03b629e0…2729`); full suite 1253 passed, 7 skipped, 1593 subtests (log sha256 `d12932c0…1979`); offline demo PASS on CI 38594705007 at `e11654d` with an identical runtime/config/deploy/migration tree. SystemTestReport.v1 kept outside Git (synthetic data only). |
| Terraform, local | working tree = `bb8fb3d` | `hashicorp/terraform:1.13.5` (linux/amd64): fmt, init (readonly lock), validate, test: 15/15 and 1/1 |

The seven local skips are the baseline's environmental ones; Linux CI runs the bubblewrap cases and the systemd cases separately.

**Not established offline:** delivery to the real ai-seeds receiver; hosted routes, IAM and secrets; EC2 recover/reboot; RDS failover and the restore drill; cycle durations under real load; the 14-day unattended run; any signed transaction (C's gates stay closed).

## 11. After merge (2026-10-14, Yao Zhu with Claude Code)

- **Merge.** PR #67 merged into `codex/system-testing-20261012` at `0820b0d` (merge commit; tree identical to `25b9116`) before any teammate reviewed it. The post-merge review happens on the follow-up PR, which links back to #67 and its diff.
- **Merged-tree retest.** Local, macOS, Python 3.12.15 with `deploy/requirements-test.lock`, disposable PostgreSQL 14.24 (CI image): **1253 passed, 7 skipped, 1 xfailed (#23), 1593 subtests**. Same seven environment skips as §10.
- **Issues closed** with per-criterion evidence comments: #28, #29, #35, #43, #50, #51, #63. Status comments: #49, #60, #61, #64, trackers #22 and #42. #24, #26 and #40 had already been closed by Keegan after #41/#66.
- **Shared edits applied (§8) on the follow-up branch `review/final-d-open-20261014`:** GAP-35, GAP-46 and GAP-62 notes plus the R-01..R-14 summary in `docs/INCOMPLETE_WORK.md`; the IDEA-049-D row in `docs/LEDGER.md`; runbook corrections for #62 items 1–2 (the wallet key is the file `/etc/larp/signer/wallet.key`, not a `<name>/signer` secret; secret IDs are `${name}/…`, so `config/hosts/uploader.example.json` now uses `larp-dev/uploader`); the bundle comes from the CI artifact `larp-bundle-x86_64` with its hash checked against the job summary; `cycle_timeout_seconds`; the migrations route marked as D-DN-05.
- **Correction to §8.** §8 asked the runbooks to say "the release manifest is built in CI with the bundle and only verified on hosts". That is not what the code does: CI uploads the bundle and its `.sha256`, but `/etc/larp/release.json` is still built on each host with `preflight --build-output` (it hashes the host's service configs). The runbooks now say this plainly and keep **#62 item 3 open** (a code and procedure change, owner Keegan).
- **Still open from D:** D-FND-005 (#23, C's code), D-FND-014 (D-DN-07), D-FND-015 (R-09/R-10); decisions D-DN-01..11; risks R-01..R-14; #62 item 3; Keith's trading-review record under a new ledger ID (§4.4). Integration of the A/B/C requested shared edits (B's are listed in `IDEA-049-B.md`) waits for A's PR and for B's PR #65 to merge (§9).

## 12. PR #69 independent review (2026-10-15, Keith with Codex)

Reviewed head `bfe1f6c`, including the code merged by #67 (`c1b6daf..0820b0d`) as requested in #69. Both PRs had no inline review comments when fetched. Existing deployment decisions and hosted gates remain open.

Pass criteria recorded before new tests or changed runtime code execute:

| ID | Severity | Finding and acceptance criterion |
|---|---|---|
| D-RV-01 | P1 | `_audit` marks a round's SQL row CLOSED at early log creation, before runtime settlement. `open_rounds`, metrics and `activate` consult only that SQL status. Once the execution service has finished but before the runtime ingests its final fact, activation can change ownership despite an unsettled projection. Keep the round logically open until `Coordinator.close` removes its projection record; activation must refuse it even when no execution record is unfinished. After settlement/recovery, open-round checks clear, exactly one audit event remains, and downstream replay reproduces the head. |
| D-RV-02 | P2 | `Maintenance.health` omits `unlogged_rounds`, unlike the guard and service health, and can report healthy with a missed round-log deadline. With current ACKed archives and an overdue unlogged round, health must include `AUDIT_DELIVERY_BLOCKED` and count the round; after its log is committed and ACKed the condition must clear. |

Validation status: NOT RUN. Changes affecting decisions or logging must be committed and pushed before execution (AGENTS.md); push approval is required by the user's standing preference.

### D-RV-03 — PR69 review correction (2026-10-15 SGT, Isaac / Codex)

User requests the PR69 review fixes, including updating its existing branch/PR. Reviewed head `dd94ed881c07dd9683217e850f8dd0627bb5ab3c`; latest target `5c1c9c854b66a9d0c6eddba39c2be91cc3742483` contains A/B reviews and PR73's calendar. Independent Python3.12/PostgreSQL14.24 review run of `test_pr69_review.py` plus `test_final_review_d.py`: **1 failed, 23 passed, 1 known expected failure, 12 subtests**. External log `/private/tmp/larp-review-pr69-20261015-tests.log`, SHA-256 `0415626574084cfce7bae492337a2531e93a1b2b77c87c7e4cc58016a9ae6585`. The new activation test passes the pre-quarantine epoch even though quarantine increments it, so it fails at `Stale ownership` before checking the pending-round barrier. The implementation barrier is not shown broken by that failure.

Prospective acceptance before repairs or new runs: use the current persisted epoch after quarantine, retain the exact pending-round refusal assertion, and assert that refused activation preserves quarantine and the post-quarantine epoch. Preserve the other D-RV-01/02 tests, existing known #23 expected failure and all live/host acceptance items. Merge the latest target normally, retaining A's ledger row and PR73's calendar notes alongside D's backlog/index additions. Resolve only the conflicting shared documentation, without rewriting history, removing incomplete whole-GAP items or making owner decisions. Commit and push before tests. Verify the focused D tests and full Python3.12 / disposable PostgreSQL14.24 suite; rerun exact-head Linux CI, recording an account-limit refusal as NOT RUN rather than PASS. Update PR69's description to cover its runtime/storage changes and actual verification; leave the PR open for review. No secrets, signing, broadcasts or AWS activity.

D-RV-03 results (supersede §12's initial NOT RUN status): criteria pushed at `af4469d`; normal target merge `c53f084` preserves both sides of the backlog/index conflicts; test repair pushed at **`741c34af1e245a8e705410f44496c6e396138711`** before execution. The test reads the persisted post-quarantine epoch, verifies its increment, requires the exact `round is still open` refusal and checks both quarantine and epoch are preserved. No runtime guard was loosened and no assertion or known expected failure was removed.

- **PASS — focused D:** `tests/runtime/test_pr69_review.py` and `tests/runtime/test_final_review_d.py`, **24 passed, 1 xfailed, 12 subtests**, 13.00s. External log `/private/tmp/larp-pr69-fixes-20261015-results/focused.log`, SHA-256 `60afbc9b2d6a1076472609007b7892f3fd3b1faca1485201159197727bded0d6`.
- **PASS — full suite:** Python **3.12.14**, CI test lock, disposable PostgreSQL **14.24** at loopback port55469, **1330 passed, 7 skipped, 1 xfailed, 1608 subtests**, 160.55s. External log `/private/tmp/larp-pr69-fixes-20261015-results/full.log`, SHA-256 `f5cb1c480eb8838113ee38dff710afcc8d20e4f53cfabc93d0fcadd442de76e3`. Environment sanitized; `tools/system_test.py`'s network guard permits local fixtures only. Existing environment/external-artifact skips and #23's legacy signed-state backup expected failure remain; this does not close that issue. These counts include the upstream A/B/calendar integration, not only the test correction. `pip check` and `git diff --check` pass.
- **NOT RUN — Linux CI:** [exact-head dispatch 38707865791](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38707865791) targets `741c34a`. All jobs have zero executed steps; the runtime annotation says recent account payments failed or the spending limit needs increasing. A GitHub account owner must resolve this, then D/Keegan reruns exact-head and merged-branch Linux/systemd/host-bundle checks. Do not treat the earlier green D baseline as this PR's CI evidence.
- **Review state:** update PR69's title/body for the actual early-logged-round barriers, archive health, repaired activation test, merged target and runbook/config changes. PR remains open for review; no merge or deployment is performed here. Subsequent completion changes affect documentation only. Remove the task's disposable database after verification; retain the separate read-only quote collector.

Remaining owners: D/Keegan for shared-document reconciliation, #62 item3, archive/restore/host and integrated acceptance; C and D for the separately tracked #23 signed-state/legacy-backup closure; B/team for D-DN-01..11 and the existing risk decisions; account owner for CI availability. No whole incomplete-work item was completed in this correction: the backlog is retained and its D review status narrowed to local verification complete, CI and deployment acceptance pending.

### 12.1 Local CI checks (2026-10-15)

The user requested local execution after hosted CI was unavailable and approved publication of the results. **Historical revision boundary:** these checks ran before the A/B/calendar integration now present at `b99a876`; they do not establish native-Linux verification of that newer tree. The later macOS integration results in D-RV-03 above are preserved separately. Tested source: `2db6538`; runtime, config, deploy, migrations, tools and dependency locks are identical to pushed `dd94ed8` (`git diff --exit-code dd94ed8 2db6538 -- larp config deploy migrations tools requirements.in requirements.lock`). A disposable clone is mounted read-only into local Linux containers. PostgreSQL 14.24 is disposable; Python tests block external connections and use fixture receivers/venues. Docker and package installation use public dependency downloads only. No AWS resource, real wallet or organiser service is used.

| Check | Result |
|---|---|
| Corrected regressions on original `bfe1f6c` | **3 fail**, reproducing both findings; activation succeeds when it should refuse. |
| Corrected regressions on `2db6538`, macOS Python 3.12.14 | **3 pass**. |
| Earlier macOS broader suite, excluding the then-unpushed corrected test module | **1253 passed, 7 environment skips, 1 expected failure (#23), 1593 subtests**. |
| Full native ARM64 Linux suite, Python 3.12.15, pinned test lock, real systemd tests enabled | **1262 passed, 1 skipped, 1 expected failure (#23), 1598 subtests**. The sole skip is the opt-in external recorded-market dataset. Bubblewrap isolation and all three real systemd checks run. |
| x86_64 Linux under Rosetta, full suite | **1257 passed, 2 failed, 4 skipped, 1 expected failure, 1593 subtests**. The two sandbox failures are the emulator crashing under the unchanged 256 MB address-space cap: direct isolated-child reproduction prints `rosetta error: mmap_anonymous_rw mmap failed`. Native Linux passes with the same cap and sandbox; it is not weakened. This is not proof of the full suite on a native x86_64 host. |
| Separate x86_64 systemd checks | **3 passed, 5 subtests** in the disposable systemd container. |
| Terraform 1.13.5, fmt/init/validate/mock-provider tests | **deploy/aws 15/15; deploy/bootstrap 1/1**. No credentials or real cloud plan/apply. |
| Runtime Dockerfile build and restricted smoke run | **PASS**, x86_64 image, network disabled, read-only root filesystem, all capabilities dropped. |
| Offline sandboxed demo, native ARM64 Linux | **PASS**, `simulated=true`, zero pending audit chunks and zero open rounds. |
| Actual x86_64 release bundle, pushed `dd94ed8` | **PASS**: built with the remote-head guard intact, then primary and signer provisioning each run twice in disposable Amazon Linux 2023 containers with provisioning network disabled; packaged preflight, identities, permissions and entry points pass. |

Bundle SHA-256: `8eaa5d59b3bff45bb9dd791e6805765d4cbfb065b8ffffc472afee5c9df85aa5`. Raw logs, bundle, demo and summary are outside Git under `/private/tmp/larp-pr69-artifacts/`; `local-ci-report.json` indexes the retained logs and their hashes. The Linux test containers use Debian bookworm and Docker's Linux VM, rather than GitHub's Ubuntu 22.04 runner; the native full-suite run is ARM64. Hosted CI remains blocked, not reported green.

**Disposition:** D-RV-01 and D-RV-02 are fixed and verified offline. No whole deployment GAP closes. The equivalent test-only correction is already upstream at `741c34a`, with an additional epoch-increment assertion, and is retained unchanged. Original local commits `2db6538` and `e2c46de` are superseded for publication by this documentation-only reconciliation on `b99a876`; their history is retained locally. Still pending: resolving hosted Actions billing (repository/account administrator); existing #23 (Isaac + Keegan), #62 item 3 (Keegan), and D's previously recorded policy decisions and hosted gates. The repository API also reported private forking disabled and no admin access for the authenticated account; automatic approval review rejected the attempted private-fork creation before it reached GitHub. No fork was created.

## WR-D — review fixes #25 #23 #62.3 #64.4 (2026-10-15)

Yao Zhu with Claude Code, branch `claude/wr-d-runtime-fixes-58d34b` from `codex/system-testing-20261012` at `7b7acd2`. Section D's open GitHub items after the A/B/C/D merges. B (`larp/strategy`, `larp/risk`) and C (`larp/execution.py`, `larp/execution_live/`, `larp/signer/`) are being edited by other sessions and are not touched here. Out of scope: D-DN-08/09 decisions and the hosted Gate A checks (#32, #33, #59's runner test).

### Pre-registered pass criteria (written and pushed before any test or fix is written)

Environment: Python 3.12 from `deploy/requirements-test.lock`, PostgreSQL 14.24 (`postgres:14.24-bookworm@sha256:5a05f61a…1ac2`, trust auth, `larp_test`), `LARP_TEST_DATABASE_URL` set. Each new test is pushed failing before its fix; a failing test is the finding's evidence.

| ID | Issue | Test | Pass criterion |
|---|---|---|---|
| WR-D1a | #25 (A-FND-012, A-ASM-014, A-T15; P1) | `tests/integration/test_review_issuer_identity.py::…test_a_t15_policy_review_from_real_market_metadata_schedules_the_sec_issuer` | Built as A's proof (`tests/intelligence/proofs/issue25_runtime_review.py`): actual `MarketPort` output (ticker `NVDA`), real policy and a default `RuntimePlanner`. The `HORIZON_REASSESSMENT` job's `issuer_id` is `load_registry().by_token('NVDAB').issuer_id` (`SEC-CIK-0001045810`), never the ticker. The proof script itself exits 0. |
| WR-D1b | #25 | `…test_the_scheduled_job_passes_the_evidence_consumer` | Producer to consumer: the planner's review job is accepted by the evidence agent's `check_job` for `SEC-CIK-0001045810` and refused for `NVDA`; the real fixture keeps the market ticker `NVDA` (namespaces not collapsed). |
| WR-D1c | #25 | `…test_an_explicit_mapping_keeps_synthetic_identities_and_job_ids` | `RuntimePlanner(issuers=…)` with the ContextBuilder's mapping (`{issuer_id: {token, underlying_id}}`) uses that mapping: a synthetic `{EXSEMI: NVDAB}` fixture still schedules `EXSEMI`, and the job ID equals `_job` of the unchanged payload shape `{kind, issuer_id, reason, session}` (exact job identity). |
| WR-D1d | #25 | `…test_unresolvable_identity_fails_closed` | A review for a token with no registered issuer creates no job and never one naming the market ticker; a mapping that gives one token two issuers, or a registry that cannot be loaded, refuses construction (`ContractError` / `IntelligenceError`). |
| WR-D1e | #25 | `…test_the_service_planner_uses_the_driver_issuers` | `build_driver` gives `RuntimePlanner` the same registry-validated driver `issuers` as `ContextBuilder`: with the test config `{SEC-CIK-0001045810: NVDAB/NVDA}` the planner maps `NVDAB` to `SEC-CIK-0001045810`. |
| WR-D2a | #23 (D-FND-005 remainder, C-OPEN-008; P0/P1) | `tests/runtime/test_final_review_d.py::SignedBytesInBackups::test_d_req_023_backups_carry_no_usable_signed_bytes` | `expectedFailure` removed in the fix commit. Strengthened: every base64 cell of every exported table is decoded, and the raw hex (either case, with or without `0x`) and the raw bytes appear in no cell and not in the payload. |
| WR-D2b | #23 | `…test_d_req_023_a_legacy_signed_state_is_redacted_and_restores_closed` | A real signed execution (C's `Executor` path) rewritten to a pre-C-FND-010 legacy row: `raw_hex` in `execution_records.state` with a valid `state_hash` and journal chain (it loads before export). Export carries no usable bytes in any cell; the row's `state_hash` and every `execution_journal` row are exported unchanged. Restore into an empty schema succeeds, the run is quarantined with `epoch+1`, the restored state holds no raw bytes, and `ExecutionStore.load` of that key and the registry `lookup` raise `Conflict` (fail closed). |
| WR-D2c | #23 | `…test_d_req_023_forged_rows_carry_no_signed_bytes` | Forged variants exported with no usable bytes: `signedTransaction` instead of `raw_hex`, bytes nested deeper in the state, bytes in an `execution_journal.event`, and a state blob that is not JSON. |
| WR-D2d | #23 | `…test_d_req_023_restoring_an_old_backup_drops_signed_bytes` | A `Backup.v1` made before this fix (raw bytes in a state, valid checksum) restores with no raw bytes in the target database; run quarantined; that record fails closed. |
| WR-D2e | #23 | existing `tests/execution/test_section_c_signed_state.py` | C's legitimate byte-free state still exports byte-identically and its restored record still loads (`test_c_req_012_*`, `test_c_req_037_*` stay green unchanged). |
| WR-D3a | #62 item 3 (with #49 remainder; P2) | `tests/runtime/test_release_bundle.py::…test_wr_d3_the_bundle_carries_the_ci_release_manifest` | `build()` writes `release-manifest.json` inside the bundle (listed in `SHA256SUMS`) and byte-identical `larp-<build12>-<arch>.release.json` beside the archive. It is a `ReleaseManifest.v1` with `build_id` = commit, `repository` = the credential-free origin URL, `services` = the commit's `config/release/services.v1.json`, `files` = SHA-256 of every `release_files()` path in the bundle's `release/`, `release_register` = `load_register` of that tree, and no host bindings (no registration evidence, no config hashes). A remote URL with credentials refuses. |
| WR-D3b | #62.3 | `tests/runtime/test_operations.py` or `test_final_review_d.py::…test_wr_d3_hosts_only_verify_and_bind_the_ci_manifest` | `preflight --bind <CI manifest> --root R --build-output OUT [--registration-evidence F] [--config F] [--runtime-config F] [--service-config NAME=PATH]`: needs no git; refuses a changed or missing manifested file, an unmanifested release file, a changed register, a CI manifest that already carries host bindings, and registration evidence for another build or repository; writes OUT (exclusive create) with every CI field unchanged plus `ci_manifest_sha256` and the host bindings; OUT passes `verify_release` and the existing runtime/service config checks. |
| WR-D3c | #62.3 | `deploy/host/provision.sh`, `tools/test_host_bundle.sh` (CI `host-bundle` job) | `provision.sh` installs the bundle's manifest read-only as `<release>/release-manifest.json` and refuses a bundle without one or whose `build_id` differs from `BUNDLE.env`. The packaged-release check binds and verifies that CI manifest instead of a synthetic one. |
| WR-D3d | #62.3 | `…test_wr_d3_ci_uploads_the_manifest_with_the_bundle` | The `host-bundle` job uploads the `.release.json` in the same artifact as the bundle and its `.sha256`, and lists its SHA-256 in the step summary; every `uses:` in the workflow is pinned by a 40-hex commit SHA. |
| WR-D3e | #62.3 | `…test_wr_d3_runbooks_never_build_the_manifest_on_a_host` | `docs/build/AWS_RUNBOOK.md`, `docs/build/runbook.md` and `docs/build/DEPLOYMENT_DAY.md` name the CI manifest and `preflight --bind`, and contain no host step running `preflight --build-output`. |
| WR-D4 | #64 item 4 (P3, plausible) | Two-OS-user reproduction in a Linux container (`python:3.12.15-bookworm`, users `larp-evidence` and `larp-runtime` in group `larp-evidence`, directory `0770`, reader umask `0077`, writer umask `0007`) | **Reproduce first.** At the issue's baseline `9bfffcd` store, the reader opening first is expected to create `-shm` owned by `larp-runtime` and lock the writer out. At this base: (i) reader first after a clean writer close, (ii) the same with the directory group-writable (no systemd sandbox), (iii) a writer killed mid-transaction leaving a hot journal. Pass (no code change) if the current tree creates no file owned by `larp-runtime` and the writer reopens and commits in all three; otherwise a failing test and a fix. |

Overall: the full suite on PostgreSQL 14.24 shows no new failures against this base and **0 xfailed** (#23's expected failure gone). The `host-bundle` job's change is checked in mirror CI (`Cookiemunchrr/larp-ci-mirror`), which Yao Zhu dispatches.

### Results (2026-10-15)

Commits, each pushed before it ran: criteria `405b743`; #25 test `6cf0102`, fix `007b9d9`; #23 tests `3af7aef`, fix `70ebb42` (removes the `expectedFailure`), test-helper repair `fb53bea`; #62.3 tests `79e20b0`, fix `fa4c768`, test repairs and amendment `715a042`, flag fix `8d396bd`; #64.4 proof `05e3a1e`.

**Amendment A-WR1 (disclosed; after the first #62.3 fix run, before its retest).** WR-D3b named `preflight --bind … --build-output OUT`, which contradicts WR-D3e (no `--build-output` in a host runbook step). The bind output flag is `--output` instead; `--bind` refuses `--build-output`. Same commit: three test bugs, assertions unchanged: the field-by-field copy check now skips exactly the host-binding fields CI leaves empty (`HOST_BINDINGS`), the summary check reads the summary block rather than one line, and macOS temp paths are compared resolved. The #23 helper repair (`fb53bea`) encodes compared journal rows as the export does (`{'bytes': …}`).

| ID | Status | Red before the fix | Fix | Retest |
|---|---|---|---|---|
| WR-D1 (#25) | **Fixed (D scheduler side)** | `6cf0102`: 5 failed (the job named `NVDA`; no `issuers` argument) | `007b9d9` `larp/integration/runtime.py`: `RuntimePlanner(issuers=…)` maps each review's token to its issuer through the ContextBuilder's registry-validated map (`build_driver` passes the same map) or, by default, the canonical registry. No issuer → no job (never the ticker); a duplicate token or an unreadable registry refuses construction. Payload shape and job ID unchanged. | 5/5 green; A's proof prints required and actual `SEC-CIK-0001045810` and exits 0; integration/intelligence/driver/redteam suites 528 passed. |
| WR-D2 (#23) | **Fixed (D export/restore side)** | `3af7aef`: 3 failed + the existing xfail | `70ebb42` `larp/storage/backup.py`: export and restore replace any signed-bytes field (`raw_hex`, `signedTransaction` and aliases) and any whole RLP-encoded signed transaction (legacy or typed, nonzero r/s) in an exported JSON value with a marker; an unparseable execution state or journal event is replaced whole. Stored hashes are kept, so the restored record fails its state/journal check (closed) and the run is quarantined. Clean values export byte-identical. | 4/4 green with no `expectedFailure`; C's `test_section_c_signed_state.py` 7/7 unchanged; D, execution, storage, maintenance, signer suites green. |
| WR-D3 (#62.3) | **Fixed (repo side)** | `79e20b0`: 7 failures | `fa4c768`, `8d396bd`: `tools/build_release_bundle.py` writes the code-only `ReleaseManifest.v1` as `release-manifest.json` (in `SHA256SUMS`) and `<name>.release.json`; credentialed origin refuses. `preflight --bind CI --output OUT` verifies it against the installed release (no git) and adds only registration evidence and config hashes plus `ci_manifest_sha256`. `provision.sh` installs it `0444` and refuses a bundle without it or for another build. The `host-bundle` job uploads it with the bundle and lists its hash. `AWS_RUNBOOK.md`, `runbook.md`, `DEPLOYMENT_DAY.md`, `architecture-deployment.md` use `--bind`. | 5 tests green. Local host check: aarch64 bundle from pushed head `8d396bd` (bundle `019eda11…f22b`, manifest `f6112f80…2946`), `tools/test_host_bundle.sh … linux/arm64` **PASS** for `primary` and `signer` (manifest `0444 root`, bind then host-profile preflight on the packaged release, R15 two-user check). x86_64 `host-bundle` job: mirror CI, not yet run. |
| WR-D4 (#64.4) | **Not reproduced on this tree; no code change** | — | Already fixed by IDEA-047 R15 (`c34e8ad`): DELETE-journal shared writer, read-only reader that refuses a WAL header, runtime unit without `ReadWritePaths` | `tests/runtime/proofs/issue64_sqlite_sidecars.py` (two OS users, `python:3.12.15-bookworm`, no systemd sandbox). At `9bfffcd`: **reproduces**: `-shm`/`-wal` owned by `larp-runtime`, writer `unable to open database file` while the reader is open and after it closes (exit 1; report SHA-256 `8799b276…614d`). This tree: no file owned by `larp-runtime` in (i)–(iii); the writer reopens and commits; after a writer killed mid-transaction the reader creates nothing and the writer rolls the transaction back (exit 0; report `233269a3…635a`). CI's `test_host_bundle.sh` keeps the two-user R15 check. |

Full suite (macOS, Python 3.12.14 from the CI test lock, PostgreSQL 14.24 on loopback, head `05e3a1e`): **1433 passed, 7 skipped, 0 xfailed, 2071 subtests** (202 s; log SHA-256 `af0f5a85…2ede`). Baseline on the same machine at `7b7acd2`: 1419 passed, 7 skipped, 1 xfailed, 2059 subtests. +14 tests (13 new, the #23 xfail now passes), no new failure; the seven skips are the usual environment ones (bubblewrap, systemd runner, external artifacts), which Linux CI runs.

**Still open after WR-D.**
- #23: the archive role can still `SELECT execution_records` directly. No database has ever held signed state (signing is gated; C's new state is byte-free since C-FND-010), so no legacy row exists to scrub; an in-place redaction migration is a C+D follow-up only if one ever does. Known limit: bytes hidden in another encoding (for example base64 inside JSON) or in a non-JSON value outside the two execution columns are not detected.
- #25: A's contract side (A-T01/A-T16) and this scheduler fix together cover the issue's three criteria; A (Keith) to confirm A-T15 on the merged tree before closing.
- #62.3: mirror CI must show the `host-bundle` job uploading the `.release.json`. The manifest records the CI checkout's origin URL, so the activation bundle must come from the registered repository's CI run, not the mirror's (the registration evidence must name the same repository). Host configs stay out of Git (IDEA-051), so a host still adds their hashes; it never recomputes code identity.
- #64.4: nothing for D; the first-host legacy-sidecar step in INCOMPLETE_WORK (IDEA-047 item 3) applies only if a host ever ran the WAL build, and none has.

### Added criterion WR-D3f (2026-10-15, after the integrator's review of PR #78; written and pushed before its test)

Finding (integrator review): the CI manifest's `repository` was the checkout's `remote.origin.url`. With org Actions out of quota, CI bundles are built on the private mirror, so the manifest would name `Cookiemunchrr/larp-ci-mirror` instead of the registered repository (F-61, F-47), and `--bind` would refuse registration evidence for the real repository. The `'@'` check also refused an SSH origin (`git@github.com:…`).

| ID | Test | Pass criterion |
|---|---|---|
| WR-D3f | `tests/runtime/test_release_bundle.py::…test_wr_d3f_the_manifest_names_the_registered_repository_from_any_origin` | The manifest's `repository` comes from a committed file in `config/release/` (covered by the manifest's `files`), equal to `https://github.com/binance-hackathon-glasswing/binance-hackathon`, whatever the origin: with origin set to the mirror URL and with an SSH-form origin, the bundle builds and `repository` is the registered URL; the origin is kept separately as provenance (`build_origin`). An origin URL carrying credentials (`https://user:token@…`) still refuses, and a registered-repository file that is missing, has another schema or is not a credential-free `https://github.com/<owner>/<repo>` URL refuses. |

Note (integrator, no change): the #23 redaction catches the known signed-bytes keys and whole hex-encoded signed transactions, not a base64-encoded transaction under an unknown key (already listed under "Still open"); C's PR70 handles base64 reflections on the response side.

# IDEA-049-D — Final review D: accountability and operations

- Date / reviewer: 2026-10-14 / Yao Zhu, with Claude.
- Branch: `review/final-d-20261014`, cut from `codex/system-testing-20261012` at **`c1b6daf`** (merge of PR #66).
- Catalogue: [`docs/build/final-review/D-catalogue.md`](../build/final-review/D-catalogue.md).
- Protocol: [`00-common-protocol.md`](../build/final-review/00-common-protocol.md) and [the D prompt](../build/final-review/D-accountability-operations.prompt.md).
- Status: phase 1 frozen at `3ab45dc`. Phase 2: trace and pre-registration below.

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

## 5. DECISION-NEEDED

Candidates from phase 1 (to be confirmed in phase 2): D-CON-03 (standby vs two hosts), D-CON-04 (rehearsal length), D-CON-09 (latched HALTs vs autonomous recovery).

## 6. Deployment risks

To be filled.

## 7. For other sections

To be filled.

## 8. Requested shared edits

To be filled at integration.

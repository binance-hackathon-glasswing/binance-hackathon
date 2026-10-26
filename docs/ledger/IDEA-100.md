# IDEA-100 — RDS `db.t4g.micro` stall on 2026-10-25: cause, and keeping a 14-day run inside 1 GB and a 10 % CPU baseline

- Date / author: 2026-10-26 (SGT) / Claude Code, at Yao's request ("whats the issue with the 1gb database instance
  crashing and is there a way to better optimise our code so we wont crash in the 14 day run since we are using the
  free trial and cant upgrade to 2gb database"). Owner for review: Keegan (runtime/storage). Host steps: Yao.
- Status: **open — incident analysed from logs and metrics; recommendations R1–R6 drafted, none implemented.**
- Related: IDEA-094 (archive OOM loop, PR280), IDEA-095 (incremental anchors), ARCH-01 (payload growth), ARCH-02,
  IDEA-085 (connection reuse), IDEA-097 (run 5, which ran on the fixed build).

## What happened (2026-10-25, instance `larp-dev`, db.t4g.micro, PostgreSQL 14.24, 20 GB)

Read-only sources: the RDS PostgreSQL log `error/postgresql.log.2026-10-25-13`, RDS events, CloudWatch AWS/RDS
metrics, and two read-only queries on run 5 (`checks/db-sizes.sh` and a column-size query).

| Time (UTC) | Evidence |
|---|---|
| 00:00 onwards | Run 4 (RC7 `2d16007`, without PR280) runs the IDEA-094 archive loop: every `larp-archive` run is OOM-killed while exporting the whole database, and the 60 s timer restarts it. RDS outbound rose from ~0.56 to ~7 MB/s (IDEA-094). |
| 10:00 → 13:45 | `CPUCreditBalance` falls steadily, 15.7 → 0. `CPUUtilization` averages 11–21 % against the micro's 10 % baseline. `FreeableMemory` sits at ~95–110 MB and `SwapUsage` at ~400 MB all day (chronic, unchanged at the stall). |
| 13:28 | The uploader's `SELECT … FOR UPDATE` on the single `runs` row ends in `canceling statement due to lock timeout`. |
| 13:30 | Execution's `SELECT … FROM execution_records … FOR UPDATE` ends in `canceling statement due to statement timeout`; clients begin dropping TLS handshakes (`could not accept SSL connection: EOF detected`). |
| 13:33 | Every service's login fails (`canceling authentication due to timeout`); RDS's own WAL archive command fails. |
| 13:40:25 | RDS: "Recovery of the DB instance has started"; `shutdown immediate` at 13:41:18. |
| 13:43:34 | "Recovery of the DB instance is complete"; restarted 13:43:46. No data lost: run 4 reloaded unchanged. |

**Cause (best supported reading).** The instance is burstable: it runs at a 10 % CPU baseline and spends saved
credits to go above it. Run 4's archive loop (the IDEA-094 bug, fixed in PR280 and absent from RC7) re-exported the
whole database about once a minute for 13 hours. That drained the credits by about 13:30. From then the database was
too slow to finish transactions on the hot `runs` row, every client queued behind the row lock, logins timed out, and
RDS restarted it.
- Since then the instance runs in unlimited mode: `CPUSurplusCreditBalance` 2.6–3.4, `CPUSurplusCreditsCharged` 0.
- The exact trigger minute is not provable without Performance Insights or `pg_stat_statements`, both off.
- Memory was tight all day but unchanged at the stall, so it is a contributing factor, not the trigger.

**Not the cause:**
- **WAL volume.** It is a constant 64 MB per 5 minutes both with run 4 and with run 5. That is RDS switching
  segments on a timer, not our writes.
- **Database size.** Run 5's database is 21 MB.

## What a run costs the database now (run 5, build `7fc9f601`, which includes PR280/IDEA-095)

- **CPU averages ≈ 9.5–10 %, right at the 10 % baseline**, with 4–5 connections and an almost empty database. Any
  extra steady load spends credits.
- **The `runs` row is small:** projection 9.5 KB raw (6.2 KB stored), `policy_state` 2 KB, `execution_state` 43 B.
- **Events are large:** 80 events average **202 KB raw / 87 KB stored**, and the largest is **1.56 MB**. Each
  `events` row stores the whole `CommitBatch`, with full state copies and the round's context (IDEA-094's
  `row(n) ≈ 100 KB + 4 KB × n`).
- **Polling.**
  - The runtime ticks every 5 s. Each tick does about 5–6 full `store.load` reads of the `runs` row (`recover`,
    `balance_check.due`, `allowance_check`, `day_roll.due`, then the round): about 100,000 reads a day.
  - Execution and the signer poll every 1 s. During an active intent, execution also runs
    `verified_snapshot(full=False)` plus a full load every second.
- **14-day projection at run 5's rate (~640 events a day):** about 9,000 events, roughly 1.8 GB raw and 0.8 GB stored.
  That fits the 20 GB volume. Each daily backup reads all of it, so its CPU and I/O grow every day.

## Recommendations (cheapest first; none needs a bigger instance)

| # | Change | Why | Effort |
|---|---|---|---|
| R1 | **Alarms**: CloudWatch alarms on `CPUCreditBalance` < 20 (standard) and `CPUSurplusCreditBalance` > 10, plus `FreeableMemory` < 60 MB, `SwapUsage` > 600 MB, `DatabaseConnections` > 15. | The stall gave 3.5 hours of visible credit drain and nothing alerted. | Terraform only |
| R2 | **Turn on query visibility**: `pg_stat_statements` and `log_min_duration_statement = 1000` in the parameter group (free). | The next diagnosis can name the query instead of inferring it. | Parameter group, one reboot |
| R3 | **Read the hot row once per tick.** Have `RoundDriver.once` (and execution's `facts`) reuse one loaded snapshot per tick, or check `version` first and reload only when it changed. | Turns ~100,000 full-row reads a day into roughly one per commit. Today the row is small; it grows with evidence (IDEA-094). | Small code change + tests |
| R4 | **Back off idle polling**: execution and signer at 2–3 s when nothing is claimable, 1 s only while an intent is active. | About halves idle transactions; trading latency is unchanged. | Small code change |
| R5 | **Slim `events` rows (ARCH-01)**: store the batch delta, not full copies of projection/policy/execution state. Keep large immutable round context (market rows, quotes, assessments) once by hash. | Event rows drop from ~200 KB to a few KB. That cuts TOAST compress/decompress CPU, backup size and time, archive memory and storage. This is the change that keeps day 14 as cheap as day 1. | Larger; touches replay and verification; Keegan review |
| R6 | **Guard the archive job**: exponential backoff, and a cap on full exports per day, on top of PR280. | A future archive regression can no longer re-run a full export every 60 s. | Small |

**For the final run, with no instance upgrade:** R1, R2 and R6 now. R3 and R4 before the final build if they fit,
since they are low risk with tests. R5 only behind its own review (ARCH-01's trigger, PR281). Without R5, check
credits and archive duration daily (R1 alarms) during the scored run.
- If the instance stays in unlimited mode, sustained load above the baseline is charged as surplus credits, not
  throttled. At ≈ 5 % above baseline for 14 days that is on the order of a few dollars [ESTIMATE]. That is cheaper
  than a stall. The billing check below shows how it is paid.

## Billing check (2026-10-26, read-only Cost Explorer and CloudWatch; Yao asked "are those credits from the free trial or did aws just try and bill me")

- **Two different "credits".**
  - *CPU credits* are a burstable-instance performance allowance, not money.
  - *Account credits* are the trial/promotional dollars.
- **No surplus CPU credit has been charged.**
  - `CPUSurplusCreditsCharged` sums to 0 from 2026-10-24 to 2026-10-25T16:30Z.
  - Cost Explorer's `APS2-CPUCredits:db.t4g` usage type is $0.00.
- **October to 2026-10-26:** $18.44 usage and −$18.44 account credits (record type `Credit`), so **$0 net**. Any
  surplus CPU charge would draw on the same account credits first.
- **Remaining account credit: about US$141** (Yao, 2026-10-26). Expiry not recorded.
- **Decision (Yao, 2026-10-26): "we dont need to be that stringent with our use".**
  - With about $141 left, surplus CPU charges of a few dollars over 14 days are acceptable.
  - In unlimited mode the instance borrows rather than throttles, so CPU cost alone is not a stall risk.
  - The remaining risks are a pathological loop like run 4's archive bug, and missing visibility. DB1, DB2 and DB5
    are therefore required before final activation. DB3, DB4 and DB6 become optional efficiency work.
  - DB7's CPU target is relaxed to "credits or surplus stable, no alarm".

## Implementation spec for R1–R6 (2026-10-26; pass criteria pre-registered before any implementation)

For teammates to implement, one PR per row or grouped, each based on canonical. Defaults and the strict
safety checks (swap preflight, signer policy, Gate A/B) do not change. Each PR records its results here.

| # | Where | Change | Pass when (pre-registered) |
|---|---|---|---|
| DB1 (R1) | `deploy/aws/monitoring.tf` (next to `database_storage`) | Alarms on `AWS/RDS` for the instance, all with `local.alarm_actions` and the footer. `CPUCreditBalance` < 20 for 15 min (missing data breaching). `CPUSurplusCreditBalance` > 10 for 15 min. `FreeableMemory` < 60 MB for 10 min. `SwapUsage` > 600 MB for 15 min. `DatabaseConnections` > 15 for 5 min. | `terraform plan` adds exactly 5 alarms and changes nothing else. A `tftest` asserts the metric names, thresholds and actions. Each alarm reaches the existing email topic (SNS test publish). |
| DB2 (R2) | `deploy/aws/storage.tf` `aws_db_parameter_group.larp` | Add `shared_preload_libraries = pg_stat_statements` (`apply_method = pending-reboot`), `pg_stat_statements.track = top`, `log_min_duration_statement = 1000` and `log_lock_waits = 1`. Then a read-only `checks/db-top-queries.sh` that prints the top 15 statements by total time (query text truncated, no parameters). | Plan changes only the parameter group. After one planned reboot, outside a run, `CREATE EXTENSION pg_stat_statements` succeeds as admin. The check prints rows. Slow (≥ 1 s) statements and lock waits appear in `postgresql.log`. |
| DB3 (R3) | `larp/runtime/driver.py` `RoundDriver.once`; `larp/execution_live/loop.py` `facts` | Load the `runs` row once per tick and pass that snapshot to `recover`, `balance_check.due`, `allowance_check`, `day_roll.due` and the round. Reload only after a commit in the same tick, or when a cheap `SELECT version` differs. Writers keep their own `FOR UPDATE` re-check. | A counting store wrapper shows ≤ 2 full `runs` loads per idle tick (today 5–6). The full runtime, coordinator and replay suites pass unchanged. A concurrent-writer test proves a stale snapshot never commits (the version conflict is still raised). |
| DB4 (R4) | `larp/execution_live/main.py` loop; `larp/signer/service.py` loop; configs | Idle backoff: when a tick claims, advances and signs nothing, sleep `idle_interval_seconds` (new, default 3, bounded 1–5). Use `interval_seconds` (1) while any intent or signing request is active. | Tests show 1 s spacing while work is open and 3 s when idle. No claim, sign or broadcast is delayed past its authority margin (`submission_margin_seconds`). Config validators refuse values out of range. |
| DB5 (R6) | `deploy/systemd/larp-archive.timer`; `larp/runtime/operations.py` | After a failed run, the next archive attempt waits 60 s, 120 s, 240 s … up to 1 h. At most 3 full exports per UTC day, recorded durably, so a restart cannot reset the count. A healthy hourly anchor run is unaffected. | Tests: N consecutive failures produce the backoff schedule; a 4th full export in a day is refused with a fixed status line; anchors and health still run hourly; ARCH-02 checks still pass. |
| DB6 (R5) | `larp/storage/postgres.py` commit and `events`; replay and verification | Store each `CommitBatch` as a delta: the changed keys of projection, policy and execution state, plus round context by content hash in a separate table. Checkpoint the full state every K events. Verification and replay rebuild from the checkpoint plus deltas. | Event rows average ≤ 20 KB on the run-5 fixture (today 202 KB raw). Replay of every recorded fixture run is byte-identical to before. Hash-chain verification covers the deltas and the content table. A migration test loads existing journals unchanged. Keegan reviews (ARCH-01; PR281 trigger). |
| DB7 (live) | next dev run | Run for ≥ 24 h with DB1–DB5 installed. | Average RDS CPU ≤ 8 %, and `CPUCreditBalance` not falling over the 24 h. No alarm except planned tests. `db-top-queries` lists no single statement above 30 % of total time. |

**Priority (after Yao's 2026-10-26 decision):**
- **Required before final activation:** DB1 (alarms, with the `CPUSurplusCreditBalance` alarm kept as cost
  visibility), DB2 (query visibility) and DB5 (archive backoff and daily cap).
- **Optional:** DB3 and DB4 (fewer reads, idle backoff), if they fit the final build. DB6 only after its own review.
- **DB7:** 24 h with no alarm, credit or surplus balance stable (not steadily climbing), and no single statement
  above 30 % of total time. The 8 % CPU target is dropped.

## DB1, DB2, DB5 implementation: design choices (2026-10-26, Claude Code; written before any test or code)

Asked by the user ("Can you implement PR 288?"). This implements the three required rows; DB3, DB4 and DB6 stay
optional and are not part of it. The pass criteria are the ones pre-registered above. Choices the spec leaves open:

- **DB1.** One `aws_cloudwatch_metric_alarm.database_health` map of five alarms beside `database_storage`, using
  `local.alarm_actions` and `local.alarm_footer`. Thresholds in bytes: 60 MiB free memory, 600 MiB swap. Only the
  credit-balance alarm treats missing data as breaching, as the spec says; the other four use `notBreaching`.
  Evidence offline: `terraform test` with the mock provider (no AWS access here). `terraform plan` against the real
  account and the SNS test publish are host checks for Yao.
- **DB2.** The four parameters go into `aws_db_parameter_group.larp` (`pending-reboot` for
  `shared_preload_libraries`). The read-only check is `checks/db-top-queries.sh` in the run-5 sheet folder and in the
  FS1 run sheet folder, in the same shape as `checks/db-sizes.sh`. It reads `pg_stat_statements` in one READ ONLY
  transaction and prints the top 15 statements by total time, query text cut to 160 characters. Query texts are
  already normalised by the extension (constants as `$n`), so no parameter values are printed.
- **DB5.** Two parts:
  - **Daily cap.** `Maintenance(max_exports_per_day=…)`: `prepare_backup` counts this run's backup rows whose slot falls
    in the current UTC day, in any status, from `archive_outbox`. That count is durable and survives restarts. At the
    cap it prepares nothing and returns None, and `health()` reports `BACKUP_DAILY_CAP`. The default `None` keeps
    current behaviour. `operations once` passes 3, or the optional config key `max_exports_per_day`.
  - **Backoff.** It lives in `operations once`, not in the timer, so the cheap steps keep their one-minute cadence:
    anchor, delivery and health, as the spec's "anchors and health still run hourly" requires. After a run with any
    failure, a backoff file in `StateDirectory` records the count and the next allowed time: 60 s, then 120 s, 240 s …
    up to 3600 s. Until that time the run skips the two heavy steps, the backup export and the daily full verification,
    and reports `ARCHIVE_BACKOFF`. A run without failures clears the file. Without a state directory there is no
    backoff, as with IDEA-095. `larp-archive.timer` is unchanged (`OnUnitInactiveSec=60s`); only a comment is added.

## DB1, DB2, DB5 results (2026-10-26; Python 3.12 from the pinned lock, PostgreSQL 16 — not the pinned 14.24 image; Terraform 1.13.5, AWS provider 6.61.0, mock provider)

Commits: `6689bf8d` (design choices), `52a26321` (tests, red on canonical `1ed5a248`: the alarms are undeclared; 12
failures counting subtests in the archive/check file, whose 3 guard tests pass on base by design), `8d2d731e`
(implementation).

| # | Result |
|---|---|
| DB1 | **PASS offline.** `deploy/aws` `terraform test`: 21 passed (19 before + 2 new). `database_health.tftest.hcl` asserts exactly 5 `database_health` alarms with the IDEA-100 metrics, comparisons, thresholds (60 MiB, 600 MiB in bytes) and windows; the alarm topics, the instance dimension and the F-114 footer on each; only the credit-balance alarm treats missing data as breaching. `fmt -check` and `validate` pass. **Not run here:** `terraform plan` against the account ("adds exactly 5 alarms, changes nothing else" — this change set also changes the parameter group, DB2) and the SNS test publish: host steps for Yao (FS1 run sheet row F0d). |
| DB2 | **PASS offline.** The tftest asserts the parameter group holds `rds.force_ssl` plus exactly the four new parameters, with `shared_preload_libraries` at `pending-reboot`. `checks/db-top-queries.sh` (run-5 sheet) parses, is one READ ONLY transaction with a 30 s statement timeout, `LIMIT 15`, query text cut to 160 characters, and has no write or reset statement (test). Deviation: the spec named both sheets; the FS1 sheet has no `checks/` folder yet (F0p), so it is in the run-5 sheet and F0p copies it. **Not run here:** reboot, `CREATE EXTENSION`, rows printed, slow statements and lock waits in `postgresql.log` (F0d, outside a run). |
| DB5 | **PASS.** `tests/runtime/test_archive_backoff.py` (11 tests, 5 subtests): a fourth backup export in a UTC day is refused and named `BACKUP_DAILY_CAP`; the count survives a new process; the next day exports again; no cap keeps the old behaviour; `operations once` uses 3; invalid caps are refused. Backoff: repeated failures give pauses of 60, 120, 240, 480, 960, 1920, 3600, 3600 s; during a pause the export and full check do not run, health says `ARCHIVE_BACKOFF`, and the new hour's anchor and the health metrics still go out; a clean run clears it; without a state directory nothing changes. The existing archive, growth, maintenance, operations and host-unit tests pass unchanged (ARCH-02's offline checks). Deviation: the timer itself is unchanged (comment only); the backoff is in `operations once` so the cheap steps keep their 60 s cadence. |
| Suite | Same container: branch **2851 passed, 11 skipped, 4060 subtests, 0 failed**; base `1ed5a248` **2840 passed, 11 skipped, 4055 subtests, 0 failed**. The difference is the 11 new tests. `deploy/bootstrap` `terraform test` 1/1. GitHub Actions cannot run (billing). |

**Still to do:** Keegan reviews; Yao applies DB1/DB2 outside any run (F0d: apply, SNS test, one reboot, extension) and
installs a build containing DB5; DB7's 24 h check on the next run. DB3, DB4 and DB6 stay optional and are not built.

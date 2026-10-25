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
  than a stall, but it still needs to be allowed under the trial (Yao to confirm).

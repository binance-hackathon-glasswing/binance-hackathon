# IDEA-095 — 14-day journal: incremental hourly anchors and no full journal re-read inside a trading cycle

- Date / author: 2026-10-25 / Claude Code (review of PR280, asked by the user: "ensure our agent is able to trade
  smoothly for 14 days"). Owner for review: Keegan (runtime/storage). Host steps: Yao.
- Status: **open — pre-registered (criteria SD1–SD7 below committed before any criterion test was run).**
- Related: IDEA-094 (PR280; ARCH-01 item 1), IDEA-036 (hourly anchors), IDEA-055 (balance adoption, `_quiet_since`),
  IDEA-085 (connection reuse), F-114/F-117/F-124 (no human action during the scored run; automatic restarts only).

## Problem (read from the code at PR280 head `67d2abfb`)

Both paths below read the **whole** journal from RDS, and each one costs more as the run gets longer. IDEA-094
projects 8–18 GB of raw journal by day 14, against a db.t4g.micro network baseline of ≈8 MB/s [ESTIMATE].

1. **Hourly anchor.** `operations once` runs as a new process every time, so it has no in-memory checkpoint.
   `Maintenance.prepare_anchor` therefore calls `verified_snapshot(run_id)` (`full=True`), which re-reads and re-hashes
   every journal row. IDEA-094 projects this at ≈1000 s on day 14 in the constant-row case, and past
   `TimeoutStartSec=1200` around day 10 in the growth case. Past that point, each run is killed inside the anchor
   step. That run then sends no anchor, no health metric and no backup, and the timer restarts the read about 60 s
   later, so RDS network is saturated nearly all the time. Trading shares that RDS: every commit writes and reads
   rows of a few MB. Before the cutoff, the hourly re-read already takes a growing share of every hour
   (≈500 s/h by day 7 in the constant case).
2. **Trading cycle.** Balance adoption (`BalanceCheck._confirm` → `_quiet_since` in `larp/runtime/driver.py`) calls
   `store.journal(after_version=…, through_version=…)`. `journal()` calls `verify()`, a **full** verification, inside a
   runtime cycle under the 600 s hung-cycle watchdog (`cycle_timeout_seconds`). This path runs whenever a
   chain/ledger mismatch candidate (for example a dust transfer into the wallet) meets a version that moved between
   the two reads. Once a full read takes longer than the watchdog, the cycle is killed, the runtime restarts, the
   startup verification re-reads the journal, and the next confirmation repeats the loop. Even before that point,
   every confirmation stalls the cycle for minutes.

## Decision (proposed; Keegan to accept)

1. **Archive verification checkpoint on the archive host.** When systemd provides `$STATE_DIRECTORY`
   (`StateDirectory=larp-archive`, mode 0700, owned by `larp-archive`), `operations once` keeps the last verification
   checkpoint (the same dict `PostgresStore._verify` returns) in a JSON file there, written atomically.
   - The anchor continues from it: `verified_snapshot(full=False)` re-hashes only the events after it and still checks
     the run row, the reservations table and every outbox count in full.
   - A missing, unreadable, malformed or other-run file, or one the database no longer extends (`_continues`), means a
     full verification (the current behaviour).
   - The file sits outside the database's trust domain: a database credential cannot change it. This is the same trust
     model the trading runtime already uses for its own in-memory checkpoint.
2. **Daily full check, last.** Once per backup interval, after the anchor, health and backup steps, `once` runs one
   full verification.
   - Its start is recorded in the state file *before* it runs, so a run killed by `TimeoutStartSec` is not retried until
     the next interval (no retry storm).
   - Success records its time and refreshes the checkpoint. An `IntegrityError` discards the checkpoint, so the next
     anchor verifies in full and refuses, and the run reports `ARCHIVE_PREPARATION_FAILED`.
   - Health adds `FULL_VERIFICATION_OVERDUE` (Healthy=0) when no full check has completed within 2 backup intervals.
3. **No full verification in the trading cycle.** `PostgresStore.journal(..., full=False)` continues from this
   process's checkpoint instead of re-reading the whole journal. In the same read transaction it checks the hash chain
   of the rows it returns: each row's batch hash, previous hash, head and sequence, from the head stored at
   `after_version`. `_quiet_since` passes `full=False`. The default (`full=True`) is unchanged for every other caller.
4. Not changed: the per-event payload (ARCH-01 rows), `TimeoutStartSec`, `MemoryMax`, the Backup.v2 format, the
   runtime's startup verification (still full; see residual risks).

Tradeoff: between two daily full checks, the anchor no longer re-hashes rows older than its checkpoint. An older row
changed in the database is caught by the next daily full check, a runtime restart, a restore, or `verify_anchors`
against the Object-Locked anchors. Each anchor's head still extends the previous verified head, so the anchors stay a
hash commitment to the history.

## Pass criteria (pre-registered)

Base for "red on base": PR280 head `67d2abfb`. Real PostgreSQL. Tests in `tests/runtime/test_journal_growth.py`.

| ID | Criterion |
|---|---|
| SD1 | With a state directory, the second and later `once`-style runs (a new store and a new `Maintenance` each, like new processes) verify for the anchor from the saved checkpoint: `_verify` gets a base whose version is the previous run's verified version, and the anchor head and sequence equal those of a full verification. Base: every anchor verifies from genesis. |
| SD2 | A missing, corrupt, wrong-schema, other-run or non-continuing (rewound or replaced head) checkpoint falls back to a full verification. An event changed after the checkpoint is still refused by the anchor (IntegrityError, no anchor queued). |
| SD3 | The full check runs at most once per backup interval. Its attempt is durable before it starts (a `BaseException` inside it leaves no retry within the interval). A row changed *before* the checkpoint is found by the full check: IntegrityError, the checkpoint is discarded, and the next anchor refuses. `FULL_VERIFICATION_OVERDUE` is reported only after 2 intervals without a completed full check. |
| SD4 | Without a state directory, behaviour is unchanged: every anchor verifies in full and existing maintenance/operations tests pass unmodified. |
| SD5 | `journal(..., full=False)` does not verify from genesis when this process holds a continuing checkpoint (`_verify` gets a base). It returns the same documents as `full=True`, and refuses (IntegrityError) a returned row whose batch bytes, batch hash or head chain were changed. `_quiet_since` uses it. Base: `_quiet_since` verifies from genesis. |
| SD6 | `larp-archive.service` declares `StateDirectory=larp-archive` and `StateDirectoryMode=0700`; host unit tests pass. |
| SD7 | Full suite: no new failures against PR280 head `67d2abfb` in the same environment; exact counts reported. |

Result states: `supported` if SD1–SD7 pass; `not supported` if any SD1–SD5 fails after the fix; `inconclusive` if the
environment prevents a run (stated).

## Residual 14-day risks not fixed here (recorded for Keegan/Yao)

- **Restart pause.** A new runtime or execution process verifies the full journal once: at startup for the runtime
  (`verify_registered_manifest`, outside the watchdog), and at the first intent's `facts()` for the execution service.
  At ≈8 MB/s that is ≈17 min on day 14 in the constant-row case, during which that process makes no decisions and
  signs nothing. Each automatic restart (F-124) costs this once.
- **Per-event payload (ARCH-01).** Rows still copy the whole projection, which is what makes the items above
  expensive. The 4 MiB pre-execution round-record budget (`Coordinator`) is not reached in 14 days. The record embeds
  `EvidenceContext.v1` summaries, not the evidence state. Their only part that grows with run length is the
  unresolved adverse findings, about 1.6 KB per latch in the IDEA-094 fixture: ≈2,600 latches before 4 MiB, against
  the fixture's synthetic one per round.

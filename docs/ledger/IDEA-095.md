# IDEA-095 — 14-day journal: incremental hourly anchors and no full journal re-read inside a trading cycle

- Date / author: 2026-10-25 / Claude Code (review of PR280, asked by the user: "ensure our agent is able to trade
  smoothly for 14 days"). Owner for review: Keegan (runtime/storage). Host steps: Yao.
- Status: **open — pre-registered (criteria SD1–SD7 below committed before any criterion test was run).**
- 2026-10-25 status (Claude Code): **supported offline** (results below); Keegan review and host acceptance open.
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

## Results (2026-10-25, Claude Code; PostgreSQL 16.15 and Python 3.12.3 on Linux x86_64 — not the pinned 14.24 Docker image, which this container cannot run)

- 2026-10-25 note (Claude Code): after the red commit `d772ef23`, the tests' `anchors()` helper was changed to read the
  delivered S3 objects (the outbox payload is emptied after delivery). The red result is unaffected: on base, SD1 fails
  at the `_verify` base assertion before the helper runs. Three tests were added with the fix: incident backup later
  in the hour (fails without the seeding line), a full check that never completes, and an unwritable state directory.

Implementation: `larp/runtime/maintenance.py` (`VerificationState`, `_verified`, `full_check`, `verification_reasons`,
incident-backup seeding), `larp/runtime/operations.py` (state directory, full check last, overdue health),
`larp/storage/postgres.py` (`journal(full=False)`, `export_checkpoint`, `adopt_checkpoint`),
`larp/runtime/driver.py` (`_quiet_since`), `deploy/systemd/larp-archive.service` (`StateDirectory`).

| ID | Result | Evidence |
|---|---|---|
| SD1 | PASS | Fresh store per run: the second and third anchors verify from versions 4 and 7 (`_verify` bases `[4]`, `[7]`). The anchor's sequence and head equal the database's. An incident backup in a run with no anchor to prepare continues from the saved checkpoint (no genesis verification). |
| SD2 | PASS | Missing, corrupt, wrong-schema, other-run, replaced-head and malformed checkpoints all verify from genesis, and the anchor head is correct. An event changed after the checkpoint is refused (IntegrityError, no anchor for that hour). An unwritable state directory still delivers the anchor, and the full check reports `FileNotFoundError`. |
| SD3 | PASS | One full verification per interval, last in the run. A killed full check is not retried in runs 2–4 of that interval and runs again the next interval. A row changed before the checkpoint passes the incremental anchor (the documented tradeoff) and is found by the next daily full check: IntegrityError, checkpoint discarded, and the next anchor verifies in full and refuses (`ARCHIVE_PREPARATION_FAILED`). `FULL_VERIFICATION_OVERDUE` appears at 2 intervals + 1 min, not at 2 intervals − 1 min. When no full check ever completes, the count starts at the first attempt. |
| SD4 | PASS | Without `STATE_DIRECTORY`, every anchor verifies from genesis and nothing is written. Without a state directory the new Maintenance methods are not called at all. This was found by the full suite: `test_service_health` R5 mocks `Maintenance`, and has passed unmodified since the fix. |
| SD5 | PASS | `journal(full=False)` continues from the process checkpoint (no genesis verification) and returns the same bytes as `full=True`. It refuses a changed row and a row whose batch hash was recomputed off the head chain. `_quiet_since` passes `full=False`. |
| SD6 | PASS | `StateDirectory=larp-archive`, `StateDirectoryMode=0700`; `tests/runtime` (host unit tests included) 653 passed, 9 skipped. |
| SD7 | PASS | Full suite, same container and database: branch `605d7438` **2687 passed, 11 skipped, 4016 subtests, 0 failed**; PR280 head `67d2abfb` **2671 passed, 11 skipped, 4008 subtests, 0 failed**. The difference is the 16 new tests. |

Result state: **supported** offline (SD1–SD7). Not run: the pinned PostgreSQL 14.24 image, mirror CI, the host.

Review of PR280 itself (same session): no blocking defect found. The Backup.v2 delta/restore round trip, streaming
`_verify`, the PREPARING latch and the `once` ordering were read against their tests, and its 70 archive,
maintenance, operations and storage tests pass here. One precondition is recorded in ARCH-02: incremental segments need
a database that holds the final run only.

Host acceptance (Yao, with ARCH-02): after install, `/var/lib/larp-archive` exists (0700, `larp-archive`) and holds one
checkpoint file after the first run. Later hourly runs finish in seconds, and one run per day takes the full check.

## PR280-RV01 — SD5 range gap (Isaac, 2026-10-25; fix pre-registered before tests or code)

**Finding (Isaac, PR280-RV01 at `ecc4e0d8`; confirmed by reading the code).** `journal(full=False)` checks the returned
rows' hash chain from the head stored at `after_version` but never links its end to a trusted head. When
`through_version` is before the process checkpoint, a consistently rewritten subchain (rows 3–5 re-hashed, row 6 and the
run row untouched) is returned without error; full `verify` refuses it. The verification and the row read also run in
two transactions, so they need not see the same snapshot. `_quiet_since` relies on the returned rows as evidence that
intervening commits were wallet-neutral, and reads up to `current['version']`, which is at or just before the
checkpoint, so the bridge to a trusted head is short.

**Fix (proposed).** One REPEATABLE READ, READ ONLY transaction verifies from the checkpoint (as `verified_snapshot`)
and reads every row after `after_version` up to the verified snapshot's version. Their chain from the head at
`after_version` must end exactly at the verified `(head, version)`, so it passes through the checkpoint row and the
newly verified rows. Only rows up to `through_version` are returned. `full=True` is unchanged.

| ID | Criterion |
|---|---|
| SD8 | With this process's checkpoint at version 6: rows 3–5 rewritten as a self-consistent chain (batch bytes, batch hash, event hash, previous hash and head recomputed; row 6 and the run row unchanged) make `journal('run', after_version=2, through_version=5, full=False)` raise `IntegrityError` (red on `ecc4e0d8`). The same call on an untampered journal returns the same bytes as `full=True`, still without a genesis verification. The existing SD1–SD5 tests pass unchanged. |
| SD9 | Full suite on the fixed head: no new failures against `ecc4e0d8` in the same environment; exact counts reported. |

Result states: `supported` if SD8–SD9 pass; `not supported` if SD8 fails after the fix.

### PR280-RV01 results (2026-10-25; Python 3.12 from the pinned lock, PostgreSQL 16 — not the pinned 14.24 image)

| # | Result |
|---|---|
| SD8 | **PASS.** Test committed red on `ecc4e0d8` (`385efde5`: the rewritten range was returned). With the fix (`eac6e923`) it raises `IntegrityError`, as full `verify` does. SD1–SD5 tests pass unchanged, including the untampered `through_version=5` read with the checkpoint at 6, still without a genesis verification. Journal, archive and storage tests: 73 passed |
| SD9 | **PASS.** Same container and database server: fixed head **2688 passed, 11 skipped, 4016 subtests, 0 failed**; `ecc4e0d8` **2687 passed, 11 skipped, 4016 subtests, 0 failed**. The difference is the SD8 test. The 11 skips are environment-only (systemd runner, bubblewrap, root, opt-in fixtures) |

Result state: **supported** offline. The `full=True` path still verifies and reads in two transactions, as before
PR280; it is not changed here.

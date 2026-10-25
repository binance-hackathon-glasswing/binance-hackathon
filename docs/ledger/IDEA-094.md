# IDEA-094 — Archive job survives a 14-day journal: anchors and health never wait on the backup

- Date / author: 2026-10-25 / Claude Code session started from the run-4 incident session (design, implementation,
  record). Owner for review: Keegan (runtime/storage). Host steps: Yao.
- Status: **open — pre-registered (criteria AR1–AR9 below committed before any criterion test was run).**
- Related: IDEA-036 (hourly anchors), IDEA-049 D-FND-008/-021 (daily and incident backups), IDEA-089 (run 4),
  GAP-35, F-114/F-117 (no host changes during the scored run).

## Incident (run 4, dev rehearsal, 2026-10-25; evidence relayed by the starting session)

- From 00:00Z every `larp-archive.service` run ends `Result=oom-kill` (`MemoryMax=512M`).
- `Maintenance.prepare` ran the first daily backup slot since install (2026-10-25T00:00Z). `export()` loads every
  table of every run into memory and serialises one JSON payload.
- The database is 60 MB, but `events` is 160 rows / 64.66 MB (≈400 KB per row on disk, rising). Each `events` row
  stores the whole `CommitBatch`, which carries full copies of `projection`, `policy_state` and `execution_state`.
- The process is killed before `publish_health`, so no metric is sent (8 CloudWatch alarms on missing data). Because
  `prepare` runs before delivery, the hour's anchor is queued but never sent; the last anchor is 23:00Z.
- RDS outbound traffic rose from ~0.56 to ~7 MB/s: the timer (`OnUnitInactiveSec=60s`) re-runs the export every
  ~60 s, because a killed export leaves no record for its slot.
- Trading does not depend on the archive.

## Offline measurement (exploratory, before this entry; pinned Python 3.12.15 / PostgreSQL 14.24 in Docker)

Fixture: `tests/runtime/test_driver.py` `DriverHarness`, one issuer, an hourly cadence round per tick (2 journal
events per round). Numbers are from fixtures, not from the host.

| Rounds | Events | `events` raw bytes | `events` on disk | Export (v1) | Export peak Python memory | zlib(export) |
|---|---|---|---|---|---|---|
| 24 | 48 | 9.4 MB | 2.1 MB | 20.1 MB | 121 MB | 2.9 MB |
| 48 | 96 | 28.2 MB | 5.1 MB | 58.2 MB | 350 MB | 6.9 MB |
| 72 | 144 | 56.2 MB | 9.0 MB | 114.3 MB | 686 MB | 11.9 MB |
| 96 | 192 | 93.5 MB | 13.9 MB | 188.4 MB | 1131 MB | 18.0 MB |

- Row size fits `row(n) ≈ 100 KB + 4.0 KB × n` (from the 96- and 192-event totals). The growth is the evidence
  state in `projection['evidence']` (fixture: `unresolved_adverse` +1.6 KB per round) copied into every row, and
  the round record and round log, which embed the evidence context. Open round records sit in the projection and are
  copied into every event of their round.
- PostgreSQL stores these rows ~6.7× smaller than their raw bytes (TOAST compression), so "64.66 MB on disk" is not
  the export size. The v1 export is ~2× raw `events` (base64 and the other tables); its peak memory is ~6× its own
  size (`doc()` encodes, re-parses and re-encodes the whole payload twice).
- Run 4 by the same ratios (an estimate, to be checked on the host): ~430 MB raw `events`, a ~0.9 GB v1 payload and
  several GB of peak memory. This is consistent with the OOM at 512 MB.

## Projection for the scored run (14 days, unattended)

Model: `row(n) = a + b·n`, total `T(N) = a·N + b·N²/2`, one daily backup. Rates are taken from run 4: 160 events in
~18 h (≈9 events/h, ≈214 per day, ≈3,000 in 14 days). Two bounds bracket the unknown real `a`/`b`:

- Constant rows (`b = 0`, `a` ≈ 2.7 MB raw, the run-4 estimate): `T(3000)` ≈ 8 GB raw, ≈1.2 GB on disk.
- Fixture growth (`a` = 100 KB, `b` = 4 KB per event, one issuer): `T(3000)` ≈ 18 GB raw.

Consequences:
1. **No single full backup fits** any memory budget on this host by day 14, compressed or not. A compressed full
   copy (≈5× smaller than raw `events`) would still be 1.6–3.6 GB.
2. **One day's events do fit, if compressed and streamed.** Day-14 volume in the constant-row case: 214 × 2.7 MB ≈
   580 MB raw ≈ 60–120 MB compressed before excluding re-derivable copies. Measured on the fixture, a daily
   segment without the re-derivable copies and with state deltas is several times smaller again (AR6 records the
   measured ratio).
3. **Full journal verification** (every hourly anchor; `export()`) must stream. Today it fetches the whole `events`
   result into client memory and keeps every outbox payload of the journal, so anchors alone pass 512 MB once raw
   `events` passes a few hundred MB: within the first days of a scored run at run-4 rates.
4. **The per-event payload itself is the long-run risk** and is out of scope here (it changes trading-path journals
   and replay). Left alone, it threatens RDS storage (20 GiB, autoscaling to 30 GiB) under the growth case, the CPU
   time of hourly full verification, and the 4 MiB pre-execution round-record budget in `Coordinator`. Recorded as
   an open item for Keegan/Keith (INCOMPLETE_WORK ARCH-01).

## Decision (proposed; Keegan to accept)

1. **Decouple.** `operations once` prepares and delivers the hour's anchor, then attempts the backup, then always
   computes and publishes health. A backup that fails, is refused or is still marked as preparing from an earlier
   killed run makes health `Healthy=0` with a named reason; it never stops the anchor or the metric.
2. **Durable attempt record.** Before an export starts, its slot is written to `archive_outbox` as `PREPARING` in its
   own committed transaction. Success turns it `PENDING` with the payload; a refusal or error turns it `PERMANENT`
   with the error class. A `PREPARING` row left by a killed process is closed as `PERMANENT`
   (`PreparationInterrupted`) by the next run. A slot is attempted once: no 60-second retry storm against RDS.
   No migration is needed (`archive_outbox.status` has no CHECK; the archive role already has INSERT/UPDATE).
3. **Backup.v2: incremental, streamed, compressed, bounded.**
   - Each backup carries the `events` rows after the newest *acknowledged* backup of the run (its base: sequence,
     head and slot) and a full copy of every other table. A chain from a base-less backup restores the journal.
   - Re-derivable copies are left out: an outbox value column (`audit_events.document`, `audit_chunks.body`,
     `commands`, `jobs` values listed in `OUTBOXES`) equal to the bytes its journal event holds is replaced by a
     reference, and rebuilt from the journal on restore. Each row's `projection`/`policy_state`/`execution_state`
     is stored as a delta against the previous row of the segment. Restore rebuilds the exact bytes; the existing
     hash-chain and outbox verification (`_verify`) is the check, so any reconstruction error fails closed.
   - Rows are read with server-side cursors and written through a deterministic gzip stream. The compressed size is
     checked as it grows; passing `max_payload_bytes` stops the export at once (`BackupOverBound`), so memory stays
     near the bound whatever the journal size. Signed-bytes redaction is unchanged.
   - Backup.v1 objects still restore.
4. **Streaming verification.** `_verify` reads `events` through a server-side cursor and keeps SHA-256 digests of
   journal outbox values instead of the values. Same checks, same results; memory no longer grows with the journal.
5. **Limits.** `MemoryMax`, `TimeoutStartSec` and `max_archive_bytes` are set from AR7/AR8 measurements and the
   projection above, and justified in the results section.

Tradeoffs: a restore needs every segment of the chain (each is Object-Locked for 82 days, so all 14 days' segments
exist); a lost segment breaks restores past it until the next acknowledged backup that bases on an older segment.
Bases are always acknowledged backups, so an unacknowledged segment is never a base. The `events` table, the
journal format, the hash chain, replay and the runtime's write path are unchanged.

## Pass criteria (pre-registered)

Each AR test must fail on the base `4b164649` (where it can run there) and pass on the branch. Real PostgreSQL 14.24.

| ID | Criterion |
|---|---|
| AR1 | A process killed inside the backup export (simulated by a `BaseException` raised in `export`) has already delivered the hour's anchor and published health. Base: anchor queued, not delivered; no metric. |
| AR2 | After a killed or refused export for slot S, later `once` runs in S do not export again (one export call over 5 runs), still deliver anchors, and publish `Healthy=0` with reason `BACKUP_PREPARATION_FAILED` and the error class. Base: one export per run. |
| AR3 | A backup whose compressed stream would exceed `max_payload_bytes` is refused (`BackupOverBound`) with traced peak memory ≤ 2 × bound + 16 MiB; nothing is queued for delivery. Base: the full payload is built first. |
| AR4 | Export peak traced memory on the 96-round fixture journal is ≤ 25 % of the v1 export's peak, and does not grow more than 2× from 48 to 96 rounds for a constant daily segment. |
| AR5 | A Backup.v2 chain (≥3 segments, with an incident backup) restores into an empty database to the exact journal head; `verify_anchors` passes against delivered anchors; the restored run is quarantined. Backup.v1 still restores. A tampered segment, a missing or reordered segment, or a segment of another chain is refused. |
| AR6 | A segment holds only the events after its acknowledged base; an unacknowledged backup is never a base. The measured segment-to-v1 size ratio on the fixture is recorded. |
| AR7 | Full `verified_snapshot` on the 96-round fixture keeps traced peak memory ≤ 2 × the largest single row + 16 MiB (base: grows with the journal). Existing tamper/truncation tests still pass. |
| AR8 | Unit limits are justified: export and verify throughput measured on the fixture, projected to the 14-day bound, and `TimeoutStartSec`/`MemoryMax`/`max_archive_bytes` set with headroom ≥ 2×. Host unit tests pass. |
| AR9 | Full pinned suite: no new failures against the base; exact counts reported. |

Result states: `supported` if AR1–AR9 pass; `not supported` if any AR1–AR7 fails after the fix; `inconclusive` if
the environment prevents a run (stated).

## Not covered here (owner/host acceptance)

- Keegan: review and accept the decision, especially the Backup.v2 format, the streaming `_verify` and ARCH-01.
- Yao: install the build; afterwards check, read-only, one `once` run on the host (anchor delivered, health
  published, backup segment ACK), and run the calibration query in the results section to replace the run-4
  estimate (`a`, `b`, raw/on-disk ratio).
- The per-event payload growth (ARCH-01) stays open.

- 2026-10-25 clarification (Claude Code, before any fix was written): AR7 is measured as peak RSS growth of a
  fresh process (`tests/runtime/memory_probe.py`, `/proc/self/clear_refs` reset, then `VmHWM`), not with
  tracemalloc, because tracemalloc cannot see libpq's result buffer, which is where the base holds the journal. AR3
  and AR4 stay tracemalloc as written. The AR tests live in `tests/runtime/test_archive_budget.py`.

## Red on base (`18d10036`, code identical to `4b164649`; pinned Docker Python 3.12.15 / PostgreSQL 14.24)

9 failed, 2 passed. AR1: anchor not delivered (0 objects) and `Killed` escapes before any metric. AR2: the export
runs on every one of 5 runs (5 calls, not 1). AR3: traced peak 351.7 MB against an 18 MiB bound (1 MiB backup
bound). AR7: RSS growth 90.1 MB verifying a 42.5 MB journal whose largest row is 0.6 MB (bound 18.0 MB). AR4, AR5
chain/tamper/foreign and AR6: `export_segment` / `restore_chain` / `segment_header` do not exist. Passing on base,
as expected: the AR5 v1 round trip (compatibility check) and nothing else.
- 2026-10-25 correction (Claude Code): the recorded base run at `21420648` is **10 failed, 1 passed**; AR7 fails on
  base (RSS growth 90.2 MB) and only the AR5 v1 round trip passes. "9 failed, 2 passed" above was an earlier run whose
  AR7 probe inherited the parent's peak-RSS mark.

## Results (2026-10-25, Claude Code; pinned Docker Python 3.12.15 / PostgreSQL 14.24 on Apple-silicon Linux)

Implementation (files): `larp/storage/backup.py` (Backup.v2 `export_segment`, `restore_chain`, `segment_header`),
`larp/storage/postgres.py` (streaming `_verify`), `larp/runtime/maintenance.py` (`prepare_anchor`,
`prepare_backup`, PREPARING latch, `BACKUP_PREPARATION_FAILED`), `larp/runtime/operations.py` (order; restore
takes one `--receipt` per segment), `larp/storage/archive.py` (`.json.gz` keys), `deploy/systemd/larp-archive.service`.

| ID | Result | Evidence |
|---|---|---|
| AR1 | PASS | Killed export: the hour's anchor object exists and health was published before the kill. |
| AR2 | PASS | Killed export: 1 export over 5 runs; after 30 min `BACKUP_PREPARATION_FAILED`, `PreparationInterrupted`, Healthy=0. Refused export: 1 call over 5 runs, error class `ContractError`; the next day's slot ACKs and health returns to healthy. |
| AR3 | PASS | 41 MB journal, 64 KiB bound: refused as `BackupOverBound` within 2 × bound + 16 MiB traced; slot `PERMANENT`, nothing delivered. |
| AR4 | PASS | 96-round fixture: full v2 segment traced peak 11.5 MB vs v1 1,131 MB (1.0 %); 24-round daily segment 4.8 MB at round 48 vs 7.8 MB at round 96 (1.63×). |
| AR5 | PASS | Daily → incident → daily chain restores (any order) to the exact head; `verify_anchors` passes 3 anchors; run quarantined. Missing base, duplicate, tampered, foreign-chain and non-backup inputs refused with nothing restored. v1 restores. |
| AR6 | PASS | Segments hold exactly the events after their acknowledged base; an unacknowledged (PENDING) backup is not a base. Fixture sizes: full segment 4.9 MB vs v1 188.4 MB (39×) for a 93.5 MB raw journal; daily segment of 48 events (37.3 MB raw) 1.7 MB (22×). |
| AR7 | PASS | Full verification RSS growth 4.4 MB for a 42.5 MB journal (largest row 0.6 MB; bound 18 MB). Base 90.2 MB. One row per fetch (4 rows: 16.9 MB; 16: 46.5 MB) and binary transfer (text-format bytea is hex). |
| AR8 | PASS | See limits below; `Limits` test ties `TimeoutStartSec` < `PREPARING_STALE_MS` and `MemoryMax` ≥ 2 × measured peak. |
| AR9 | PASS | Full suite: branch **2668 passed, 9 skipped, 4008 subtests, 5 failed**; base `4b164649` **2656 passed, 9 skipped, 4004 subtests, 5 failed** — the same 5 on both, all environment-only in this container: 3 need `git` metadata the worktree mount lacks (`test_deploy_presetup` ignored-directory check, `test_final_review_d` credential scan via `git ls-files`, `test_gate_a` GA15b ignored-path check) and 2 need nested bubblewrap (`test_worker_release` Sandbox). Org CI unavailable; mirror CI not run (user pushes it). |

Limits (AR8):
- **`max_archive_bytes` = 64 MiB (unchanged).** Projected day-14 daily segment: constant-row case 214 × 2.7 MB
  ≈ 580 MB raw ≈ 26–29 MB compressed at the measured 20–22× → fits with ≥2× headroom. Fixture-growth case
  (compressed cost per event ≈ 12.6 KB + 0.13 KB × n, fitted from the full and daily fixture segments) ≈ 83 MB on
  day 14: segments are refused from about day 11 (`BackupOverBound`, Healthy=0, anchors continue; earlier segments
  stay restorable). Raising the bound needs more memory than primary has spare (`MemoryMax` totals 3 GB already);
  the real lever is ARCH-01.
- **`MemoryMax=512M` (unchanged).** Measured peak RSS for prepare plus delivery of a 62.8 MB segment in one process:
  234 MB (230 MB with binary cursors; 40 MB baseline; prepare and delivery each ≈3× the segment, memory released in
  between). 2.2× headroom. Rows of ~12 MB (growth case, day 14) add roughly 60–100 MB of parsed state.
- **`TimeoutStartSec` 240 → 1200.** The hourly anchor's full verification ran at 50–57 MB/s of raw journal here
  (CPU-bound); on the host it is network-bound: db.t4g.micro's baseline is ≈8 MB/s [ESTIMATE from the EC2 t4g.micro
  baseline], and the incident plateaued at ≈7 MB/s. Day-14 journals of 8 GB (constant case) take ≈1000 s at that
  rate; 1200 s covers it. In the growth case the hourly verify passes 1200 s around day 10 → ARCH-01. Kept below
  `PREPARING_STALE_MS` = 30 min.

Decision: implemented as proposed. Result state: **supported** offline (AR1–AR9); host acceptance and ARCH-01 open.

Calibration query for Yao (read-only, replaces the run-4 estimate; output stays in the ignored activation folder):
`SELECT sequence, octet_length(batch), pg_column_size(batch) FROM events WHERE run_id=<run> ORDER BY sequence;`
— fit `a`, `b` and the raw/on-disk ratio, then re-run the projection above.

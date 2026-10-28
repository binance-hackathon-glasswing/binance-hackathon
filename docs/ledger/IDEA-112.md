# IDEA-112 — Throttle idle signed safety rounds (ARCH-01 / DB-01 volume fix before the F-127 freeze)

- Date / author: 2026-10-28 SGT / Claude Code at Yao Zhu's request ("fix everything before code freeze at 6pm")
- Status: open (criteria registered before code)
- What: in signed mode `RoundDriver._signed_cycle` starts a `safety:` round on **every** runtime tick
  (`interval_seconds` 5; about every 13 s in run 7). Each round journals the whole projection plus audit rows,
  even when nothing changed. Run 7 (IDEA-104 S5-OBS02) grew `events` by about 1.7 GB/day from these hold-only
  rounds. Its first daily backup was refused (`BackupOverBound`, 64 MiB gzip, about 12 h in, so about 20 KB
  compressed per idle round), and the 1 GB database stalled twice. FS1 runs the same loop for 14 days, so
  ARCH-01's pre-registered trigger (b) requires a fix before final activation.
- Fix: an optional driver setting `safety_round_interval_ms`. When it is set, an idle safety round is skipped
  unless one of these holds:
  - no safety round has been started by this process yet (so every restart plans at once);
  - the run journal's version changed since the end of the last safety round, so another writer committed
    (settlement, assessment round, balance adoption, day roll, recovery);
  - the UTC day changed;
  - the interval has elapsed.
  Everything else in the cycle is unchanged: assessment completion, settlement, queueing and the day roll.
  `runtime.example.json` (the base for `prepare_fs1`) sets 120000. Without the key, behaviour is unchanged.
- Why 120 s: about 720 idle rounds/day × about 20 KB ≈ 14 MB/day compressed against the 64 MiB bound (≈4.5×
  margin), and about 9× less raw `events` volume than run 7 (≈190 MB/day). The cost: a purely price-driven
  mandatory reaction (loss ladder, hard name line) waits at most 120 s more. Settlements, red-flag assessments
  and the day roll still trigger at once. All FS1 windows are hours long.
- Not changed: per-event payload size (ARCH-01 item 1), restart re-verification, instance size (IDEA-109 S-07)
  and DB1/DB2 apply. Those stay with DB-01/ARCH-01.
- Links: ARCH-01, DB-01, IDEA-094, IDEA-095, IDEA-100, IDEA-104 S5-OBS02, IDEA-109.

## Pass criteria (registered before code)

- **ST-1.** With the setting absent, a signed driver starts a safety round on every idle cycle (current tests
  unchanged).
- **ST-2.** With 120000: the first idle cycle starts a safety round; further idle cycles within 120 s with an
  unchanged journal version start none and make no quote request; the cycle at +120 s starts one.
- **ST-3.** A commit by another writer (version change) before 120 s makes the next cycle start a safety round.
  So does a UTC day change.
- **ST-4.** A skipped cycle still settles open execution, completes ready assessments and queues new work.
- **ST-5.** Validation: negative or non-integer values are refused; `runtime.example.json` carries 120000, and
  the FS1 standalone preparation passes it through.
- **ST-6.** Full suite with PostgreSQL: no new failures compared with canonical.

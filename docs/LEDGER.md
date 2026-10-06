# Experiment & Idea Ledger — index

One row per idea (IDEA-) or experiment (EXP-). Full records are in `ledger/<ID>.md`; rules and templates are in [`ledger/README.md`](ledger/README.md). Add new rows at the bottom.

**Reading rule:** read this table; open an entry file only when the task names that ID or touches its topic.

| ID | Title | Status | Result (one line) | Updated | File |
|---|---|---|---|---|---|
| EXP-001 | Verified evidence vs no-evidence baseline | draft (blocked on D-07, D-08; final block = post-cutoff Tier B, five names as a slice, per D-10 (a)) | — | 2026-10-06 | [ledger/EXP-001.md](ledger/EXP-001.md) |
| EXP-002 | Do off-hours bStocks quotes lag verified news? | draft (thresholds not frozen; viability depends on off-hours `openState`, Q-32) | — | 2026-10-05 | [ledger/EXP-002.md](ledger/EXP-002.md) |
| EXP-003 | Rule-based regime gating vs a simple volatility cap | draft | — | 2026-10-03 | [ledger/EXP-003.md](ledger/EXP-003.md) |
| IDEA-001 | Decision-model training set: sources, size and build workflow | open | data plan decided 2026-10-06: train/tune/test on Tier B time blocks, five names as a slice; D-09, D-10 (b) and Q-31 pending | 2026-10-06 | [ledger/IDEA-001.md](ledger/IDEA-001.md) |
| IDEA-002 | Event-driven news ingestion with local sentiment screening | open | Research supports investigating fast screening; immediate trading benefit unvalidated | 2026-10-05 | [ledger/IDEA-002.md](ledger/IDEA-002.md) |
| IDEA-003 | Red team of data, labels and evaluation; "well captured" gates M1–M7 | open (all fixes recommended, not decided) | 29 findings (6 critical): filing-only rows, timezone/merge leaks, vol-blind absolute labels, no clean block for V1, under-powered test | 2026-10-06 | [ledger/IDEA-003.md](ledger/IDEA-003.md) |
| IDEA-004 | Method v2 from literature: C1 base book + veto/exit overlay; walk-forward test; "well captured" v2 (T1–T10, D1–D5) | open (recommended, not decided; supersedes IDEA-003 where they conflict) | literature: catalyst drift ≈ 0 after costs in large caps; more names barely add power, more weeks do | 2026-10-06 | [ledger/IDEA-004.md](ledger/IDEA-004.md) |

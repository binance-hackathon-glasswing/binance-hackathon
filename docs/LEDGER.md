# Experiment & Idea Ledger — index

One row per idea (IDEA-) or experiment (EXP-). Full records are in `ledger/<ID>.md`; rules and templates are in [`ledger/README.md`](ledger/README.md). Add new rows at the bottom.

**Reading rule:** read this table; open an entry file only when the task names that ID or touches its topic.

| ID | Title | Status | Result (one line) | Updated | File |
|---|---|---|---|---|---|
| EXP-001 | Verified evidence vs no-evidence baseline | draft (blocked on D-07, D-08; final block = post-cutoff Tier B, five names as a slice, per D-10 (a)) | — | 2026-10-06 | [ledger/EXP-001.md](ledger/EXP-001.md) |
| EXP-002 | Do off-hours bStocks quotes lag verified news? | draft (thresholds not frozen; viability depends on off-hours `openState`, Q-32) | — | 2026-10-05 | [ledger/EXP-002.md](ledger/EXP-002.md) |
| EXP-003 | Rule-based regime gating vs a simple volatility cap | draft | — | 2026-10-03 | [ledger/EXP-003.md](ledger/EXP-003.md) |
| IDEA-001 | Decision-model training set: sources, size and build workflow | open | kit-first scope retained; external sources on hold; source-rights review and FRED/ALFRED correction in section 13; GAP-56/57 pending | 2026-10-08 | [ledger/IDEA-001.md](ledger/IDEA-001.md) |
| IDEA-002 | Event-driven news ingestion with local sentiment screening | open | Research supports investigating fast screening; immediate trading benefit unvalidated | 2026-10-05 | [ledger/IDEA-002.md](ledger/IDEA-002.md) |
| IDEA-003 | Red team of data, labels and evaluation; "well captured" gates M1–M7 | open (all fixes recommended, not decided) | 29 findings (6 critical): filing-only rows, timezone/merge leaks, vol-blind absolute labels, no clean block for V1, under-powered test | 2026-10-06 | [ledger/IDEA-003.md](ledger/IDEA-003.md) |
| IDEA-004 | Method v2 from literature: C1 base book + veto/exit overlay; walk-forward test; "well captured" v2 (T1–T10, D1–D5) | open (recommended, not decided; supersedes IDEA-003 where they conflict) | literature: catalyst drift ≈ 0 after costs in large caps; slope gate withdrawn after IDEA-005/EXP-004; C1 must be a rule-based trading book given organiser scoring statement (F-115) | 2026-10-06 | [ledger/IDEA-004.md](ledger/IDEA-004.md) |
| EXP-004 | Analytical falsification of IDEA-004's slope gate | not supported (sufficiency hypothesis) | positive slope can harm C1; broad-panel slope can hide negative eligible slope; synthetic analytical checks only | 2026-10-06 | [ledger/EXP-004.md](ledger/EXP-004.md) |
| IDEA-005 | Independent review of pulled change 0489dcf | open (recommendations only) | keep data hygiene; strategy adoption blocked by policy metric, population transfer and untested veto; nine findings R1–R9 | 2026-10-06 | [ledger/IDEA-005.md](ledger/IDEA-005.md) |
| IDEA-006 | Risk-constrained Kelly sizing for the C1 book (Busseti, Ryu & Boyd 2016) | open (recommended, not decided) | helps sizing, not edge; infinite-horizon bound too conservative for 10 sessions → finite-horizon drawdown constraint; synthetic illustration: efficient gross ≈ 0.4–0.6 | 2026-10-06 | [ledger/IDEA-006.md](ledger/IDEA-006.md) |
| IDEA-007 | Training data when real data is short: web catalysts vs synthetic data; three tracks; distillation spec | open (recommended, not decided) | both ideas as stated rejected (chart-site terms, look-ahead, no new information; Anthropic AUP bans training on Claude outputs); recommend A real-text veto classifier distilled from an open-weight/DeepSeek-API teacher (§7), B scenario lab + planted-signal test, C forward data + gated Databento; FRED replaced (Board H.10 fetched, kit realised vol); Binance spot via the kit skill OK, data.binance.vision not | 2026-10-08 | [ledger/IDEA-007.md](ledger/IDEA-007.md) |

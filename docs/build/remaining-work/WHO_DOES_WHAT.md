# Who does what: moved to the pre-trading checklist (IDEA-064)

The per-person split that was here (written 2026-10-16) is retired. As of 2026-10-17 it lives in [`docs/build/PRE_TRADING_CHECKLIST.md`](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/133) (PR #133; on branch `claude/pre-trading-checklist-20261017` until it merges). Read your own tasks and dates there.

Why it moved:

- **One owner per line.** The checklist gives every line exactly one owner. Work that needs more than one person is split into pieces (one person proposes or does it, another reviews or decides), and a piece that depends on another says "after …". The old tables here had shared "with …" tasks and owners that no longer match.
- **AWS and host steps need the approved coordinator/operator handoff.** Yao stepped down as coordinator on Oct19; the next coordinator/operator must obtain access and private files from the account owner/Yao. Do not infer that anyone else has access. Isaac's key placement remains restricted to the approved signer session. Decisions, reviews, merges, code and write-ups retain the checklist's named owners.
- **Facts moved since Oct 16.** For example, the quote capture runs on Keith's server (#132), terms are captured for all sources (#129), and the trading plan is IDEA-075 (#123).

This page keeps no owner tables, so the repository holds only one owner list. The four agent briefs in this folder ([README.md](README.md)) take their owners from the checklist too.

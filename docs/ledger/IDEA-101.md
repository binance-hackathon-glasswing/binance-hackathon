# IDEA-101 — Branch cleanup, issue reconciliation and parallel-assessment verification

Date: 2026-10-26 SGT. Owner: Yao Zhu / Codex, requested repository maintenance.
Baseline: canonical `1ed5a248cb` (PR287 integrated); main remains separate.

## CL-01 prospective acceptance

Recorded before tests and mutations.

1. Inventory all origin branches, local branches/worktrees, open issues and PRs.
   Delete only branch heads proven ancestors of the canonical integration or main;
   preserve main, canonical, every open-PR head (including PR133), the original
   current branch, and branches with unique commits. Preserve checked-out local
   branches/worktrees and user files. Record exact deleted names/SHAs and retained
   branches so the commit graph remains recoverable. Recheck the current remote
   head before deletion and use an expected-head lease.
2. Close issues only when every acceptance criterion has recorded completion or
   an explicit accepted disposition. Read all eight open issues and relevant
   current ledger/backlog evidence. Keep partial policy, economic, provider and
   hosted qualification issues open; record why. Do not equate a source merge
   with real-host acceptance.
3. Locate PR278's PL implementation in canonical and run the existing parallel
   queue, real-PostgreSQL signed-driver, continuation, restart/replay, shared
   budget and runtime-composition tests. Run adjacent driver, signed-model,
   cadence, settlement/replay and wallet-barrier regressions. A passing run
   requires no unexplained failures/skips and evidence that assessments overlap,
   same-company duplication is refused, a hung job does not block other slots,
   admission stays within budget, continuation waits for settlement, and wallet
   trades remain serial. Review implementation for uncovered contradictions.
4. Use synthetic providers and a disposable local PostgreSQL database only.
   No AWS, real wallet/key, model calls, deployment or live trading. Report
   real-provider concurrency/latency as unmeasured. If a defect is reproduced,
   preregister its test/repair here and push decision/trading/logging code before
   executing it, as required by AGENTS.md.
5. Preserve results under this ID, update canonical current status and narrow
   relevant backlog wording only where completion is verified. Deliver a PR
   based on canonical; PR133 remains noticeboard-only.

## Results

Results will be appended after the checks; this section is intentionally pending.

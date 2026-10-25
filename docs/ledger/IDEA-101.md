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
   head before deletion and rely on the ordinary Git push old-ref comparison (no force option).
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

### Branch cleanup — completed

Deleted **137 origin branches and 23 unused local branches**. Exact pre-deletion
names/SHAs, retained refs/reasons and completion counts are in
[the machine record](../build/evidence/repo-cleanup-20261026.json), committed and
pushed before deletion at `22e11026`. All candidates were ancestors of canonical;
a fresh origin listing and open-PR listing were checked immediately before an
ordinary atomic push deletion. No force option, reset or history rewrite.
Kept the original checkout branch, main, canonical and every open-PR head,
including PR133; kept all local branches attached to worktrees and all unique
histories. User files and historical worktree contents are untouched. After
cleanup: 32 origin heads (including this audit branch), 34 local branches.
Local main equals origin/main (`cf67c5d722`).

### Issue audit — no whole issue is complete

Reviewed all eight open issue bodies, their available comments, canonical
backlog/current status and the topical records. **Zero issues closed**: every
remaining issue has unmet acceptance. This is not an assertion that their
original implementation findings are all still present.

| Issue | Completed evidence / remaining acceptance | Owners / authoritative record |
|---|---|---|
| #127 hosted Gate A | KG-REV01 accepts historical unsigned host evidence and PR178. The fixed24h ingestion report remains raw FAIL; no post-fix combined explained PASS is recorded. Current-build host qualification remains separate. | Yao/Keegan, IDEA-066 PC-GAP02/RV1 and KG-REV01; GAP-70/72, PC-SRC01 |
| #120 measured profile review | Keith reproduced distributions and supported17bp MSFTB; review corrections merged. Exact current profile/gas/config adoption is still not supplied by that COMMENTED review, and #119 remains open. | Keith/Isaac, IDEA-063 RV120-RV01; GAP-69/KMP-QUOTE01 |
| #119 route-fee netting | PR157 preserved fee fields and corrected network-fee interpretation. No attributable route-fee semantics or transaction-bound quote-versus-wallet-transfer comparison completes FN3. Real swaps alone are not that comparison. | Isaac/Keith, IDEA-063 FN-01/FN-02 |
| #97 model adoption | Signed/live capability and routed workers exist. Provider/private-label quality, affordability/ledger recovery, account terms and exact adoption/release evidence remain. | Yao/Keith/Keegan/team, IDEA-057; KMP-BUD01 and FS1 adoption gates |
| #60 memory capacity | Automatic instance reboot exists; defaults still primary t3.small and 3GiB combined MemoryMax against2GiB RAM. LD14 retained limits without swap; current measurements/accepted capacity disposition remain. | Keegan/Isaac/operator, IDEA-049-D D-DN-08/LD14-I01 |
| #38 portfolio/cost conventions | FS1 repairs authorized-minimum costs and demonstrates serial all-five construction with restart/replay; PL removes a whole-session wait on the cadence path. Actual-size measured costs, stressed liquidation/correlated-loss validation and exact adoption remain. | Keith/Isaac/team, IDEA-093 PR278-RV01; GAP-10/14 and PF-04 |
| #37 economic edge | Research and EXP008 do not establish predictive FS1 edge; current review explicitly says NOT_ESTABLISHED. | Keith/Isaac/team, IDEA-093 and fs1-review-20261025; PF-04 |
| #22 review tracker | Sixteen children closed; #37/#38 remain, along with independent hosted/recovery qualification and ledger reconciliation. | Keith/Isaac/Keegan/team, tracker #22 and prior-issues.md |

### Parallel verification — PASS offline

PR278 introduced IDEA-093 PL. Checked current canonical application/test bytes
at `1ed5a248cb` from the isolated audit branch (documentation changes only).
Linux container, Python3.12.15, PostgreSQL14.24, synthetic providers, no external
network: existing parallel-assessment, signed-model, driver and service-driver
modules **85 passed /54 subtests /zero skips**, 29.79s.

Five assessor slots use independent routed instances and a shared atomically
reserved spend ledger. One company has at most one unacknowledged job; the main
thread commits at most one eligible result per tick. A hung company does not
block other completed jobs or safety planning. **Order clarification:** ready()
selects the first completed eligible result in in-process submission order,
skipping running jobs; restart recovery scans hash-named journals, so it does
not promise global submission order across restarts. This is consistent with
the PL-4 nonblocking test; older unqualified “submission order” wording should
be read with this scope.

Wallet execution remains serial through the existing wallet barrier and
one-intent-per-round planner. Cadence continuations start only after all
reservations/open rounds/execution-pending facts clear, stop at the configured
bound or a no-intent round, and preserve restart/replay identity. Signed/routed
execution already plans safety each tick; continuations apply to the cadence
path. Prepared FS1 runtimes select five workers/four continuations. Real
provider rate limits/latency, deployed configuration and final-wallet acceptance
are unmeasured by this offline check.

Full-suite first run: **2835 passed /4 failed /12 skipped /4053 subtests**,
289.56s. All four failures were test-environment artifacts: the read-only mount
prevented creation of ignored `deploy/activation` files, and the worktree `.git`
pointer referenced host metadata absent from the container. The corrected
writable disposable copy had a local Git index and the registered origin;
all four failures plus neighboring tests passed: **20 passed /23 subtests**,
0.93s. The dashboard registered-repository refusal that skipped for missing
origin also passed separately (1/1, 0.06s).

**Combined unique test coverage: 2840 passing tests, zero unresolved failures;
11 unrun environment/fixture cases:** five opt-in systemd, three bubblewrap,
root-only directory permission behavior, optional private-source fixture and
external recorded-market artifacts. These are not a single all-green full-run
count: the initial full run plus targeted environment-corrected reruns supply
the result. No application/configuration/test repair was necessary. The 85
focused tests have zero skips. Runtime: Linux aarch64, Python3.12.15,
pytest9.1.1, psycopg3.3.6, disposable PostgreSQL14.24.

The complete application/configuration/test tree is unchanged from canonical
`1ed5a248cb`; verification commands/counts and remaining limits are in
[the receipt](../build/evidence/parallel-verification-20261026.json).
No deployment, actual provider concurrency, signing or final-wallet acceptance
is inferred. Existing FS1 owner gates remain with the owners in IDEA-093 and
INCOMPLETE_WORK.md. Issue-body maintenance adds the current CL-01 remaining
acceptance summary to all eight issues; no issue closure is justified.

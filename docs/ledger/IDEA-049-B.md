# IDEA-049-B — Final review B: decisions, strategy, risk and accounting

## B-PRE-01 — authority and setup (2026-10-14 SGT)

Owner: Keegan/Codex. Separate managed worktree; branch
`review/final-b-20261014`, base `c829fae038a0589085d13552b1123802babbde4c`.
PR20/21 are MERGED into the testing branch. The user revoked the earlier wait
and requested execution of B. This is a limited B start disposition: driver
integration remains blocked for Keegan+Isaac/D before overall completion.
No new deadline, driver acceptance, profile value or activation was approved.

## B-FRZ-01 — source-first catalogue

The catalogue is `docs/build/final-review/B-catalogue.md`. Earlier conversation
edited PR21 and saw quoted findings; independence is source-first in this task,
not a claim of no previous exposure. No B implementation/test files have been
opened in this task before the catalogue freeze. Read only authoritative text
and the exact decision/readiness passages allowed by the protocol.

Prospective baseline: after pushing the freeze, run the unchanged full suite
using Python 3.12 test lock and disposable local PostgreSQL 14.24. Record exact
passed/skipped/subtest counts and environment. Then trace B code/tests; register
criteria and push failing regressions before each fix. Synthetic engineering
checks never establish live data, economic edge or host readiness.

No keys, real signing/broadcast, ai-seeds log calls, AWS operations or organiser
contact. Source/PDF reads are not execution experiments.

## Results

Requirements freeze pushed at `d2ed620` before opening B code/tests.

### B-BASE-01 — baseline (2026-10-14)

Fresh Python3.12.15 venv from deploy/requirements-test.lock; PostgreSQL14.24
dedicated cluster/database at loopback55434, no production credentials. Raw
logs outside Git under `/home/theruin08/.local/share/larp-final-b-20261014/`.
The first attempt incorrectly began after a database-start failure (unwritable
default Unix socket directory): 208 failed,955 passed,4 skipped,1383 subtests,
67.47s. These environmental failures are retained in baseline.log, not declared
implementation defects. The process had completed when interruption was attempted.

After a task-owned writable socket directory and verified PostgreSQL14.24 startup,
unchanged baseline at d2ed620: **1163 passed,4 skipped,1491 subtests**,141.86s.
The four skips are three opt-in real-systemd tests and recorded external-market
data; Linux bubblewrap is installed and its ordinary isolation tests ran.
The clean baseline log is baseline-db-ready.log. No test threshold was relaxed.

### B-REG-01 — prospective first regression pass

Write and push tests before their first run; then fixes must be separately pushed.
These tests are requirement checks, not an economic experiment:

- B-REQ010/012–016/028/050: LIVE EQUAL_WEIGHT must reject changing decided
  operating20%/80%, hard25%/90% or top-up75% thresholds without a new recorded
  team decision. Equivalent rational representations are accepted; stress regime
  budget may tighten separately. Suspected defect: validate_live checks upper
  bounds, not equality to these adopted values; provenance strings alone are not
  an adopted change. B-FND-001, P1 if reproduced.
- B-REQ018: update_risk must evaluate the UTC date, including an equivalent
  timezone-offset datetime; reject naive time. Same UTC-day loss must latch even
  if the input's local date differs. Suspected helper defect, B-FND-002, P2.
- B-REQ022/026/040/044: null/scalar/mixed/duplicate quote collections must return
  a blocked quote outcome with reductions retained, never a planner exception
  or an arbitrary first competing quote. Include stock and gas collections and
  controls showing valid quotes still work. Suspected B-FND-003, P2.
- B-REQ017–020/030–033/039–040/045/047: add requirement-named boundaries and a
  synthetic14-day policy/risk/accounting replay across UTC days, DST, timed
  blocks, halt and terminal costs. External observations synthetic; no real
  profit/source capability claim. Existing accounting/idempotence components used.

Focused tests, full suite and system_test must run against the dedicated database
after the criteria/tests/fixes are pushed. Use CI for real-systemd/host bundle;
Docker is unavailable locally. No deploy files/locks are edited by B.

### B-INPUT-01 — prior finding reconciliation (phase2)

GitHub #31 maps REQ018: roll_day exists but runtime has no production caller.
Keep P1 open; B verifies the reducer, D owns trusted journaled midnight hook.
#34 maps REQ021: B plan(None) retains mandatory reductions but coordinator/store
HALT gating suppresses the integrated path; classify as blocking P0 where safety
or unrecoverable-halt definitions apply, never hide it as a benign deliberate gate.
D owns coordinator/command correction and the team decides allowed HALT semantics.
#36 maps REQ005/038: no production balance-only reconciliation or BNB-mark
freshness contract; P1 open. C owns trusted chain facts, D startup/periodic hook;
B owns financial consumer validation after the interface is agreed.
#37 maps REQ046/ASM011, P2: after-cost support evaluator exists, real economic
comparison and default-policy acceptance remain NOT RUN/DECISION-NEEDED.
#38 maps REQ005/011/024/042 and ASM004/013: token mark vs executable liquidation,
actual-size all-in cost ranking, concentration and staggered4-session build need
explicit policy/measurement decisions. No silent restoration of volatility sizing.
#27/#30/#40 are C's expiry/native-gas/slippage interfaces; B's final tests verify
consumer constraints, without merging unreviewed C code. #39 is A's SKHYB evidence
coverage, with B policy-risk acceptance still needed. Original tracker #22
review record/ID collision remains a D/Keith input; findings are not authority.

Section completion remains blocked while these owned/cross-section dependencies
or unaccepted P2 decisions remain open; passing baseline is not review acceptance.

### B-FIX-01 — fail-first evidence

Tests and criteria pushed at fc1334e before execution. Focused run at that head:
18 failed,3 passed,2.29s (regressions-red.log). B-FND-001 P1 reproduced for four
threshold mutations; lowering gross alone already fails the existing top-up
consistency guard. B-FND-002 P2 reproduced for offset dates and naive acceptance.
B-FND-003 P2 reproduced for malformed/ambiguous stock and gas collections;
valid stock/gas and equivalent-rational/stress controls pass. Fixes require exact
decided fraction equality, aware UTC normalization and explicit blocked quote
collection outcomes. No decided value, threshold or test assertion is relaxed.

Focused retest at d1c7c77:21 passed,1.53s. Full suite at d1c7c77:
1184 passed,4 skipped,1491 subtests,138.40s. Relative to baseline:+21 tests,
unchanged skips/subtests. Full system runner follows after the replay additions.

### B-REG-02 — fourteen-day consumer replay criteria

Before first execution: Oct29–Nov11 inclusive, real coordinator, context builder,
policy, risk, settlement, PostgreSQL reservations and recorded-port replay.
Synthetic external marks/RFQs/model outage/final chain facts only; no signer.
Journal explicit UTC boundary observations before intraday shocks. Assert name
drift trim,3/8/12 loss latches, daily-only reset, closed-market retention, no
buys under spending block, terminal revert retains inventory and spends gas,
subsequent flat final ledger before deadline, duplicate final facts idempotent,
reservations released once and exact replay head/projection equality. Exact
loss-boundary tests distinguish one unit above from equality and recovery latches.
Midnight inputs are test INCIDENT facts, not evidence of D's absent production
hook; replay recomputes policy/planner/settlement, not that missing scheduler.
Published Class1/2 evidence is separately exercised by existing real-producer
tests; this replay does not fabricate an evidence producer or economic edge.

First replay run at b26dff8:1 failed,1 passed,2.43s. Test setup used unsupported
profile mode OFFLINE rather than OFFLINE_FIXTURE, so risk output was absent;
not an application finding. Correct the synthetic mode and explicitly assert
real policy output before the day4 external-model outage. Loss assertions remain.

Second replay run at3150cdd:1 failed,1 passed,5.85s. Its final observation was
15:00 UTC, after the candidate14:45 signing stop. The planner correctly refused
another sale and retained holdings. Move the retry stimulus to14:40 (market open,
before the cutoff) to exercise recovery; retain flat/gas assertions unchanged.

Third replay run at750f2bc:1 failed,1 passed,5.63s. Terminal recovery/flat/gas
assertions passed, but weekend marks triggered no reduction obligation, so the
blocked-requirement assertion was not exercised. Increase the weekend NVDAB
shock above25% while closed, retaining the required blocked-trim assertion.

Fourth replay run at80c912c:2 passed,9.65s. Real PostgreSQL risk/terminal/replay
criteria pass. This does not exercise Class1/2/3 in the14-day chain; their
consumer/producers remain separate passing regressions and live coverage gates.

### B-REG-03 — prohibited-position and fresh-wallet criteria

Before execution:100 deterministic synthetic portfolios spanning zero cash,
five held slots, dust, exact/over cap quantities; real policy/planner and external
RFQs. All targets eligible and ≤20%; every sell ≤holdings, every buy paid by cash,
no more than four held slots for an accepted buy, one child only. This finite
exploration supplements schema/validator proof, not a claim of exhaustive state
enumeration. Fresh200-USDT zero-BNB ledger must produce FIRST_BNB_REQUIRED and
no spend/holding; external bootstrap remains C/team's blocked activation input.

Initial B-REG-03 run at023acb6:1 failed,7 passed,1.12s. Incorrect positional
call to five_names keyword-only fixture; fix setup to five_names(), keeping
all prohibition/capacity assertions unchanged. Zero-BNB control passed.

B-REG-03 retest at98a65bd:8 passed,5.44s.

### B-REG-04 — adversarial required-input collections

Before execution: B-REQ022/044 malformed market/portfolio collections must return
INVALID_REQUIRED_INPUT, no intent and retain any valid known holding; never
escape with AttributeError in market_view or its error-recovery branch. Null,
scalar,string,mixed rows and malformed position maps are covered. Suspected
B-FND-004 P2: top-level market/portfolio shape checks absent and fallback itself
assumes valid dictionaries. Runtime catches failures but B's typed safety outcome
and known holding requirement must remain available. Tests pushed before fix/run.

B-FND-004 P2 reproduced at a9d6c03:8 failed,18 passed,2.47s, input-shapes-red.log.
Wrong market rows escaped with AttributeError; the portfolio fallback crashed
on malformed maps/rows. Fix validates required collection shapes up front and
retains only factual positive integer holdings in the rejection outcome.

Focused retest at e3aafaf:36 passed,16.85s. System-runner first invocation failed
before testing: Linux git cannot parse the managed worktree's Windows gitdir.
Read-only GIT_DIR/GIT_COMMON_DIR/GIT_WORK_TREE mapping plus process-local
core.autocrlf=true proves the actual clean pushed tree; no runner guard removed.

### B-REG-05 — exact cap trigger coverage

Before execution: isolate decided strict25%/90% triggers with synthetic zero
cost reserve, assert exact equality creates no reduction and one token unit over
creates durable20%/80% targets. This is a mathematical fixture, not a LIVE
cost-reserve change; post-cost convention still needs ASM004 team acceptance.

## For other sections

C/D own driver, signer, first-BNB and authoritative chain-fact integration.
A owns evidence production; B owns its policy/latch/session consumer effects.
D applies shared edits after dispositions and evidence are verified.

## Requested shared edits

IDEA-049 prerequisite entry: "2026-10-14: Keegan revoked the earlier wait and
requested section B execution. B proceeds with source-derived requirements;
driver-dependent integrated checks remain blocked for Keegan+Isaac/D before
overall completion. No driver or activation was authorized."

LEDGER: add IDEA-049-B, Final review B: decisions/strategy/risk/accounting,
IN PROGRESS, linked to this record. Baseline/results and backlog/runbook text
will be supplied after verification; no whole GAP is removed in this phase.

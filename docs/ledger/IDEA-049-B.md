# IDEA-049-B — Final review B: decisions, strategy, risk and accounting

## B-PRE-01 — authority and setup (2026-10-14 SGT)

Owner: Keegan/Codex. Separate managed worktree; branch
`review/final-b-20261014`, base `c829fae038a0589085d13552b1123802babbde4c`.
PRs #20/#21 are MERGED into the testing branch. The user revoked the earlier wait
and requested execution of B. This is a limited B start disposition: driver
integration remains blocked for Keegan+Isaac/D before overall completion.
No new deadline, driver acceptance, profile value or activation was approved.

## B-FRZ-01 — source-first catalogue

The catalogue is `docs/build/final-review/B-catalogue.md`. Earlier conversation
edited PR #21 and saw quoted findings; independence is source-first in this task,
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

Fresh Python 3.12.15 venv from deploy/requirements-test.lock; PostgreSQL 14.24
dedicated cluster/database at loopback 55434, no production credentials. Raw
logs outside Git under `/home/theruin08/.local/share/larp-final-b-20261014/`.
The first attempt incorrectly began after a database-start failure (unwritable
default Unix socket directory): 208 failed, 955 passed, 4 skipped, 1383 subtests,
67.47s. These environmental failures are retained in baseline.log, not declared
implementation defects. The process had completed when interruption was attempted.

After a task-owned writable socket directory and verified PostgreSQL 14.24 startup,
unchanged baseline at d2ed620: **1163 passed, 4 skipped, 1491 subtests**, 141.86s.
The four skips are three opt-in real-systemd tests and recorded external-market
data; Linux bubblewrap is installed and its ordinary isolation tests ran.
The clean baseline log is baseline-db-ready.log. No test threshold was relaxed.

### B-REG-01 — prospective first regression pass

Write and push tests before their first run; then fixes must be separately pushed.
These tests are requirement checks, not an economic experiment:

- B-REQ010/012–016/028/050: LIVE EQUAL_WEIGHT must reject changing decided
  operating 20%/80%, hard 25%/90% or top-up 75% thresholds without a new recorded
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
  synthetic 14-day policy/risk/accounting replay across UTC days, DST, timed
  blocks, halt and terminal costs. External observations synthetic; no real
  profit/source capability claim. Existing accounting/idempotence components used.

Focused tests, full suite and system_test must run against the dedicated database
after the criteria/tests/fixes are pushed. Use CI for real-systemd/host bundle;
Docker is unavailable locally. No deploy files/locks are edited by B.

### B-INPUT-01 — prior finding reconciliation (phase 2)

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
actual-size all-in cost ranking, concentration and staggered 4-session build need
explicit policy/measurement decisions. No silent restoration of volatility sizing.
#27/#30/#40 are C's expiry/native-gas/slippage interfaces; B's final tests verify
consumer constraints, without merging unreviewed C code. #39 is A's SKHYB evidence
coverage, with B policy-risk acceptance still needed. Original tracker #22
review record/ID collision remains a D/Keith input; findings are not authority.

Section completion remains blocked while these owned/cross-section dependencies
or unaccepted P2 decisions remain open; passing baseline is not review acceptance.

### B-FIX-01 — fail-first evidence

Tests and criteria pushed at fc1334e before execution. Focused run at that head:
18 failed, 3 passed, 2.29s (regressions-red.log). B-FND-001 P1 reproduced for four
threshold mutations; lowering gross alone already fails the existing top-up
consistency guard. B-FND-002 P2 reproduced for offset dates and naive acceptance.
B-FND-003 P2 reproduced for malformed/ambiguous stock and gas collections;
valid stock/gas and equivalent-rational/stress controls pass. Fixes require exact
decided fraction equality, aware UTC normalization and explicit blocked quote
collection outcomes. No decided value, threshold or test assertion is relaxed.

Focused retest at d1c7c77:21 passed, 1.53s. Full suite at d1c7c77:
1184 passed, 4 skipped, 1491 subtests, 138.40s. Relative to baseline:+21 tests,
unchanged skips/subtests. Full system runner follows after the replay additions.

### B-REG-02 — fourteen-day consumer replay criteria

Before first execution: Oct 29–Nov 11 inclusive, real coordinator, context builder,
policy, risk, settlement, PostgreSQL reservations and recorded-port replay.
Synthetic external marks/RFQs/model outage/final chain facts only; no signer.
Journal explicit UTC boundary observations before intraday shocks. Assert name
drift trim, 3/8/12 loss latches, daily-only reset, closed-market retention, no
buys under spending block, terminal revert retains inventory and spends gas,
subsequent flat final ledger before deadline, duplicate final facts idempotent,
reservations released once and exact replay head/projection equality. Exact
loss-boundary tests distinguish one unit above from equality and recovery latches.
Midnight inputs are test INCIDENT facts, not evidence of D's absent production
hook; replay recomputes policy/planner/settlement, not that missing scheduler.
Published Class 1/2 evidence is separately exercised by existing real-producer
tests; this replay does not fabricate an evidence producer or economic edge.

First replay run at b26dff8:1 failed, 1 passed, 2.43s. Test setup used unsupported
profile mode OFFLINE rather than OFFLINE_FIXTURE, so risk output was absent;
not an application finding. Correct the synthetic mode and explicitly assert
real policy output before the day 4 external-model outage. Loss assertions remain.

Second replay run at 3150cdd:1 failed, 1 passed, 5.85s. Its final observation was
15:00 UTC, after the candidate 14:45 signing stop. The planner correctly refused
another sale and retained holdings. Move the retry stimulus to 14:40 (market open,
before the cutoff) to exercise recovery; retain flat/gas assertions unchanged.

Third replay run at 750f2bc:1 failed, 1 passed, 5.63s. Terminal recovery/flat/gas
assertions passed, but weekend marks triggered no reduction obligation, so the
blocked-requirement assertion was not exercised. Increase the weekend NVDAB
shock above 25% while closed, retaining the required blocked-trim assertion.

Fourth replay run at 80c912c:2 passed, 9.65s. Real PostgreSQL risk/terminal/replay
criteria pass. This does not exercise Class 1/2/3 in the 14-day chain; their
consumer/producers remain separate passing regressions and live coverage gates.

### B-REG-03 — prohibited-position and fresh-wallet criteria

Before execution:100 deterministic synthetic portfolios spanning zero cash,
five held slots, dust, exact/over cap quantities; real policy/planner and external
RFQs. All targets eligible and ≤20%; every sell ≤holdings, every buy paid by cash,
no more than four held slots for an accepted buy, one child only. This finite
exploration supplements schema/validator proof, not a claim of exhaustive state
enumeration. Fresh 200-USDT zero-BNB ledger must produce FIRST_BNB_REQUIRED and
no spend/holding; external bootstrap remains C/team's blocked activation input.

Initial B-REG-03 run at 023acb6:1 failed, 7 passed, 1.12s. Incorrect positional
call to five_names keyword-only fixture; fix setup to five_names(), keeping
all prohibition/capacity assertions unchanged. Zero-BNB control passed.

B-REG-03 retest at 98a65bd:8 passed, 5.44s.

### B-REG-04 — adversarial required-input collections

Before execution: B-REQ022/044 malformed market/portfolio collections must return
INVALID_REQUIRED_INPUT, no intent and retain any valid known holding; never
escape with AttributeError in market_view or its error-recovery branch. Null,
scalar,string,mixed rows and malformed position maps are covered. Suspected
B-FND-004 P2: top-level market/portfolio shape checks absent and fallback itself
assumes valid dictionaries. Runtime catches failures but B's typed safety outcome
and known holding requirement must remain available. Tests pushed before fix/run.

B-FND-004 P2 reproduced at a9d6c03:8 failed, 18 passed, 2.47s, input-shapes-red.log.
Wrong market rows escaped with AttributeError; the portfolio fallback crashed
on malformed maps/rows. Fix validates required collection shapes up front and
retains only factual positive integer holdings in the rejection outcome.

Focused retest at e3aafaf:36 passed, 16.85s. System-runner first invocation failed
before testing: Linux git cannot parse the managed worktree's Windows gitdir.
Read-only GIT_DIR/GIT_COMMON_DIR/GIT_WORK_TREE mapping plus process-local
core.autocrlf=true proves the actual clean pushed tree; no runner guard removed.

### B-REG-05 — exact cap trigger coverage

Before execution: isolate decided strict 25%/90% triggers with synthetic zero
cost reserve, assert exact equality creates no reduction and one token unit over
creates durable 20%/80% targets. This is a mathematical fixture, not a LIVE
cost-reserve change; post-cost convention still needs ASM004 team acceptance.

B-REG-05 retest at 6105a69:9 passed, 5.37s. The interim system run started at
e3aafaf reported 112 system tests/70 subtests, 1199 full/4 skipped/1491 subtests,
and demo PASS. Its full phase overlapped the later test addition: **superseded,
not final fixed-head evidence**. Repeat after all source/trace changes are pushed.

### B-REG-06 — native gas planner/mapping scale contract

Before execution: generate profiles from synthetic quote-cost inputs with
6/8/18 BNB decimals; real GAS planner→RuntimePlanner→map_command must preserve
the ledger receive scale, native minimum output 18-decimal conversion and USDT
pay conversion exactly. This specifically guards 9bfffcd at the producer/consumer
boundary rather than testing a manually constructed command alone. No gas
profile is adopted and no signer runs. Push these tests before execution.

B-REG-06 at 75df4e9:29 risk regression tests passed, 1.91s, including all three
planner→native mapping scales. The 9bfffcd fix holds at this consumer boundary.

### B-REG-07 — final replay obligation-strength check

Before execution: after day 1 real settled children NVDAB must be≤20% of safe
equity; after the day 4 deep cut settled gross must be≤40%. A later terminal
flatten cannot mask failed intraday reduction completion. Add these assertions
to the 14-day run without relaxing existing replay/terminal/latch assertions.

## B-FND — disposition register

| ID / severity | Requirement and committed failing evidence or code proof | Fix / disposition |
|---|---|---|
| 001 P1 | REQ010/012–016/050. fc1334e LIVE threshold mutation tests, four improper acceptances. | d1c7c77 exact decided rational values; focused 21 passed and full 1184/1491 at that head. Equivalent fractions/stress tightening still allowed. FIXED offline. |
| 002 P2 | REQ018. fc1334e offset-date mismatch and naive-time acceptance. Snapshot already normalizes UTC, containing main-path exposure. | d1c7c77 UTC-normalize aware observations/reject naive; same focused/full evidence. FIXED offline. |
| 003 P2 | REQ022/026/040/044. fc1334e malformed/duplicate stock and gas collection failures. Coordinator contains exceptions but lost typed consumer outcomes. | d1c7c77 rejects invalid/ambiguous collections, retains reductions; valid controls pass. FIXED offline. |
| 004 P2 | REQ022/044. a9d6c03 eight malformed-market/portfolio regressions failed; fallback itself raised AttributeError. | e3aafaf guards shapes and fallback factual holdings; focused 36 passed including downstream 14-day replay. FIXED offline. |
| 005 P1, #31 | REQ018. ACC roll_day has no production runtime caller (only research/test); B14 explicitly injects boundary facts. | OPEN D/Keegan runtime hook; C supplies trusted mark. Commit trusted UTC boundary before new-day returns, persist/replay once, outage/restart/duplicate/missed-day checks. Do not anchor from post-loss equity. |
| 006 P0 where HALT is unrecoverable/safety-disabled; at least P1, #34 | REQ021. Coordinator.start skips planning under non-probe HALT and discards probe plan; PostgresStore command gates all HALT. B spending-only tests pass, exposing integration mismatch. | OPEN D/Yao Zhu + team/B acceptance. Keep integrity/ownership failures closed; allow agreed logged mandatory reductions under remote-delivery/new-spending HALT. Test actual coordinator/store, terminal holdings and recovery. |
| 007 P1, #36 | REQ005/038. No balance-only reducer; ACC supports final execution/service-cost facts only; ContextBuilder compares ledger to its projection, not authoritative chain. BNB mark has no fresh timestamp contract. | OPEN C/Isaac producer + D/Yao Zhu startup/periodic hook + B/Keegan financial consumer after agreed ABI. Unknown assets never swapped, unexplained changes journaled and spending blocked until reconciled. |
| 008 P1 | REQ042. POL/PLAN consume static regime_gross_weight; no dynamic volatility/stress governor or adopted omission found. Existing tighter-budget control cannot prove stress detection. | DECISION-NEEDED team+B/Keegan: preregister mathematical governor and rights-cleared point-in-time inputs or approve a justified declared deviation. No invented threshold. |
| 009 P1 pending source/deviation disposition | REQ025. Exit gas reserve/actual terminal costs exist, but no sourced future exit-spread allowance is recorded in live entry economics. PROP explicitly requires an allowance. | DECISION-NEEDED team+B/C: explicit measured/stressed exit allowance with derivation and trace fields, or documented adopted change tied to equal-weight fallback. Synthetic 50 bp entry-cap success is not the allowance or edge. |
| 010 P1 priority-adoption input | REQ030, B-CON007. DEC35 §10.1 explicitly DISCRETIONARY_EXIT; current published directive consumer creates mandatory reductions. Earlier synthetic consumer tests prove behavior, not its adoption. | DECISION-NEEDED team+A/B. Preserve current safety implementation pending explicit priority/gate disposition; no review-time policy switch. |
| COR001 summary correction | REQ034; SKILL Q08 says logging convention undecided, contradicting DEC35 B11. | Q08 corrected here under protocol §1.2 exception; organiser confirmation and bootstrap still open. No new policy. |

All proposed severities above retain the protocol's blocking treatment of existing
tracker P1s. No issue was closed solely because B unit tests pass. #37 is P2 and
needs actual economic evaluation or written team acceptance; #38's missing live
cost/valuation conventions remain blocking inputs. #27/#30/#40 await C acceptance
on its merged quote/deadline/native/slippage tree; A #39 SKHYB source coverage also
requires policy-risk acceptance. Tracker 22's original evidence/ID collision remains
Keith+D input, not evidence silently substituted by hosting IDEA-046.

## DECISION-NEEDED — reviewable proposals, no adoption

| ID | Options and recommendation | Owner / deadline / blocking |
|---|---|---|
| B-DEC-01 | LIVE profile: adopt mathematically generated candidates after five-name C capture review, or revise only with sourced decision. Recommend reviewing every value, not accepting generic provenance strings as approval. Cost minimum = max ceil(10000*pair gas value/(50-spread-min(50,2*median impact)-fee)); reject nonpositive budget or minimum>20% wallet. Per-trade cap=20% opening equity+cost reserve. Proposed cost reserve=0.1% equity, exit reserve 4G, floor 6G, receive 12G; all remain candidates. | Team+B/C, Oct 22 freeze; YES |
| B-DEC-02 | Fresh executable risk mark: liquidation quote/bid proceeds with timestamp vs kit tokenPrice plus conservative execution haircut. Recommend exact-size executable liquidation marks and fresh timestamped native-BNB value; retain disclosed lower-bound blocking when unavailable. Avoid fee/gas double charging after settlement. Cost ranking should use actual planned/rehearsal size and include both legs/gas; C must supply measurements. | Team+B/C, Oct 22; YES (#38) |
| B-DEC-03 | Concentration/default policy: quantify correlated-tech stress and staggered four-session build under preregistered costs/data, or explicitly accept unvalidated economic risk. Recommend no profitability/premium claim from historical illustrative MC. Equal-weight and 20/80/25/90/75 decisions stay unchanged. | Team+B/Keith, Oct 22; YES (#37/#38), P2 needs written acceptance |
| B-DEC-04 | Declared regime governor: implement a preregistered stress detector and source series, or approve a justified omission/deviation. Recommend documenting rights-cleared inputs and mathematical triggers before implementation; static lower budget is only the consumer gate. | Team+B, Oct 22; YES |
| B-DEC-05 | Event classes: preregister source/calendar and hold/reduce/flatten actions, or adopt reasoned DEV20 omission. Recommend explicit class rules if reliable inputs exist; no ad-hoc operator decisions during run. | Team+B/A/D, Oct 22; YES |
| B-DEC-06 | Exit costs/slippage: add measured/stressed exit-spread allowance and explicitly approve exit slippage, or adopt a sourced fallback deviation. Recommend pessimistic measured round-trip allowance including approve+swap on both legs; no fabricated bp value. | Team+B/C, Oct 22; YES |
| B-DEC-07 | Class 1 priority: confirm mandatory bypass of minimum/profit/cadence or retain DEC35's discretionary qualifier. Recommend an explicit mandatory risk-exit decision if intended, with market/integrity/slippage/expiry/gas/cap gates intact. Existing code is not the adoption record. | Team+A/B, Oct 22; YES |
| B-DEC-08 | Gas reservation margin (#46). (a) Keep reserving the quote's `gas_bnb_units` and rely on the WR-B accounting (overage charged against the real balance and recorded in `gas_over_reserve_bnb_units`). (b) Reserve approve + swap gas from the profile's QuoteCostSummary (`approve_gas_bnb_units + swap_gas_bnb_units`) times a margin factor recorded in the profile and manifest. Recommend (b), with the factor derived from C's measured receipt-vs-quote gas on both legs; no value is chosen here. Until decided, (a) holds: receipts are no longer rejected for overage, and `exit_gas_reserve_units` plus the planner's `INSUFFICIENT_GAS` check are the only protection against BNB running short between rounds. | Team+B/C, Oct 22 profile freeze; not blocking correctness (overage is now accounted), blocking the LIVE profile freeze |

Profile windows in LIVE.md (Oct 29 start; Nov 9 new-risk cut; Nov 10 flatten; Nov 11
14:45 signing stop) are candidates, not all adopted: the decided requirement is
flat by Nov 11 15:00 UTC. The 15-minute margin cannot guarantee receipt finality;
team must approve/rehearse earlier gates. Rehearsal begins from a 100-USDT wallet,
final from fresh 200-USDT facts; no measured artifact was supplied in this review.

## Deployment risks and later checks

| Risk | Assumptions / gate | Owner; exact validation step; deadline; blocks |
|---|---|---|
| B-RISK-01 | ASM001/002/003/010; final rules, valuation, scored timestamps, first BNB | Team+Isaac verifies official final parameters and registered-wallet balances/funding without adding own capital; first gas path tested only through authorised committed/logged code. Before Oct 22/final activation respectively; YES. No organiser contact performed. |
| B-RISK-02 | ASM006/015/017/020; measured approved LIVE values | Isaac/C supplies dated/hash-bound five-name RFQs, approve+swap gas/fees/slippage/TTL at both wallet/order sizes. Team+B approves every formula/value and freezes profile hash in manifest. Oct 22; YES. Synthetic summary is not real data. |
| B-RISK-03 | ASM008/009/019; midnight/chain reconciliation/BNB freshness | D/Yao Zhu implements journaled boundary and startup/periodic reconciliation hooks, C/Isaac supplies trusted facts, B validates agreed financial ABI; merge driver and run exact merged-tree restart/duplicate/missed-boundary/unknown-asset cases. Before final-review integration; YES. Calendar integration date not yet supplied by team. |
| B-RISK-04 | ASM004/011/013/018/021; executable valuation, costs, concentration, economics | Team+B/C adopts actual-size all-in cost/mark conventions; Keith preregisters rights-cleared complete-window comparison or team records unvalidated-default acceptance. Historical research MC coefficients remain illustrative; a new dated/hash-bound run is required before reuse. Oct 22/before evidence reuse; YES for activation/claims. |
| B-RISK-05 | ASM005/022; regime/event/exit/Class 1 semantics | Team+A/B/C adopts B-DEC04–07, then tests exact adopted behavior and registers deviations/reasons. Oct 22; YES. No numeric default selected to make review pass. |
| B-RISK-06 | ASM007/012; final fresh wallet, calendar/SKHYB coverage, no human action | A/Yao Zhu verifies all-five evidence coverage; C/Isaac supplies timestamp/calendar/session facts incl DST/holidays/early close; D runs merged-driver zero-human same-build 5+day weekend rehearsal and complete 14-day synthetic schedule with evidence classes, loss/caps, gas, failures and terminal receipt path. Before DR08/10/17/21 and final activation; YES. |
| B-RISK-07 | Missing driver and prior review evidence | Keegan+Isaac open/review/merge IDEA-048 driver with accepted shadow/signed scope recorded; Keith publishes tracker 22 original review under unused ID and GAP68 text, D reconciles. Before final integration; YES; calendar deadline needs team entry. Exclusion/start override never means ready. |

## Final acceptance status

**PARTIAL REVIEW; DEPLOYMENT BLOCKED.** B's owned defects are fixed and tested;
the trace deliberately keeps WEAK/MISSING/CONTRADICTED requirements where evidence
or adoption/integration is absent. Therefore common protocol §4's all-MUST,
no-open-P0/P1 and combined 14-day exit gates are not met. Do not approve this
record as complete solely from full-suite/system/CI counts. No GAP line removed.

The final clean pushed-head runner/CI evidence is recorded in B-VERIFY-01 below.
Local raw artifacts stay outside Git; results never establish
real-market execution, economic edge, AWS readiness or driver coverage.

## B-VERIFY-01 — final verified consumer tree

Tested clean, pushed head: `c3e58d11cb46add5c2e6ee78a26187ab08db41f9`.
No files or HEAD changed during this final runner. B-REG07 strengthened replay:
2 passed at that head, 11.88s. Tests/fixes were committed and pushed before each
run; initial fixture/environment failures and the superseded interim runner are
retained above rather than hidden. No tests were weakened, skipped or removed
to make these fixes pass.

`tools/system_test.py` on Python 3.12.15/PostgreSQL 14.24/WSL Linux bubblewrap:
started `2026-10-14T13:50:43.635630+00:00`, completed
`2026-10-14T13:54:31.295588+00:00`, status PASS.

| Check | Result | Raw-log SHA256 |
|---|---|---|
| system | 112 passed, 70 subtests; no skips; 51.373s | 67112927250222495b66ec7eb9fd1137f9390cf5b519e4a9afab04851d3f342f |
| full_suite | 1203 passed, 4 skipped, 1491 subtests; 174.971s | fa56afe3325e1e8595bfb1849c7a05e26984c2eabd3ba148966dc5f9f5b23eea |
| isolated offline_demo | PASS;1.316s | b66a849e816f6c6ab9871945c283863b18d8500a0d6fb9df0698769f955bb480 |

Report outside Git:
`/home/theruin08/.local/share/larp-final-b-20261014/system-clean-c3e58d1/report.json`,
SHA256 `41e113ca0d9dc9a6fead1ff730fa2a85c5dbdb7805caec8d7f0397be3d6c77d3`.
The process-local Git path/CRLF mapping described above resolved the Windows
worktree in WSL; clean/exact pushed-head/local-disposable/loopback guards stayed
enabled. The synthetic demo uses fake external transports, never registered keys.

Against unchanged valid baseline d2ed620 (1163/4/1491): **+40 tests**, unchanged
skips/subtests. Three skips are opt-in actual-systemd tests, one needs external
recorded market data. Local Docker unavailable; Linux CI supplies host/Docker
evidence. No deploy/host/lock file changed in B.

[Linux CI 38575163069](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38575163069)
on PR #65 head c3e58d1: all four jobs SUCCESS. Runtime full suite:
**1203 passed, 4 skipped, 1491 subtests**, 164.20s; separate opt-in systemd:
**3 passed, 5 subtests**, 6.36s. Isolated demo and Docker build/smoke succeeded.
Host-bundle build/provision test succeeded. Terraform mock tests:
deploy/aws **15 passed, 0 failed**; deploy/bootstrap **1 passed, 0 failed**.
These CI Terraform tests make no AWS login/plan/apply call and do not establish
deployment readiness.

[Draft PR #65](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/65)
targets codex/system-testing-20261012. It is attached to this task. The record
and shared-edit requests are a documentation follow-up to the tested consumer
tree; no new executable change is made in the result commit.

Source adversarial sweep rechecked PAGE, scoped Guide pages 3–8/10/17, verbatim
trading/OpenAPI/amount conventions, F/G/Q and K3/K6, every proposal risk/control/
reproducibility sentence, decided plan/IDEA-035/037 passages, IDEA-040 adoption
limits, B deviation rows and DR/AT gates. It added COR001 and CON007, then
rechecked their exact sources; no additional owned implementation defect was
found in the final consumer pass. This is **not** the protocol §4 no-open-findings
exit: production/adoption MUSTs and the complete integrated 14-day run remain
blocked, as the trace/dispositions state.

Final external-state recheck 2026-10-14: integration branch still c829fae;
no driver PR exists for claude/pre-deployment-review-4zxz7p; C PR #41 remains open;
#31/#34/#36 remain OPEN. Primary checkout clean; local main/origin/main and
read-only remote main all 5e945e148314b395a09ffe3e8a1461467b617114. D's shared index,
backlog and runbook integration remains requested, so no full session/review
handoff-readiness claim is made solely from Git cleanliness.

## B-VERIFY-02 — merged-base recheck before merge (2026-10-15)

The 2026-10-14 status above is out of date. After B's last push, #66 merged the
IDEA-048 driver (with IDEA-050) into `codex/system-testing-20261012` at
2026-10-14 15:09 UTC (`c1b6daf`), and C PR #41 merged at the same time. #67
(D) and #68 (A) then moved the base to `421205b`. So "no driver PR exists" and
"C PR #41 remains open" no longer hold. B-RISK-07's driver item is now "merged;
review of the merged driver and the combined runs are still open". #66 does not
touch `larp/risk` or `larp/strategy`. #31, #34, #36, #37, #38 and #39 are still
OPEN.

PR #65 head `4711ce6` merged with base `421205b` (local merge, no conflicts),
macOS, Python 3.14.6, disposable `postgres:16` container on loopback:
- B tests (3 files): **40 passed**, including the 14-day PostgreSQL replay.
- Full suite with PostgreSQL: merged tree **1286 passed**, base alone **1246
  passed** (+40 = B's tests); both 39 skipped, 1 xfailed, 1566 subtests and the
  same 3 failures. The 3 failures need the Linux host setup (two) or `boto3`
  (one), so they are local-environment failures, not B regressions.

Linux CI has not run on the merged tree (Actions quota is used up). This
recheck does not change the PARTIAL REVIEW / DEPLOYMENT BLOCKED status, the
open P0/P1 items or the team decisions listed above. D's shared ledger and
backlog edits for B are tracked in PR #69.

## For other sections

C/D own driver, signer, first-BNB and authoritative chain-fact integration.
A owns evidence production; B owns its policy/latch/session consumer effects.
D applies shared edits after dispositions and evidence are verified.

- D: #31/B-FND005 midnight hook and #34/B-FND006 HALT integration are open.
  The B tests and code proofs above are ready for the owning PR; use actual
  PostgreSQL/coordinator path, preserve local integrity fail-closed behavior.
- C+D+B: #36/B-FND007 needs an agreed balance/mark observation ABI before B
  can implement financial reconciliation. C PR #41 was unmerged when read; no
  implementation from it was silently incorporated. Accept #27/#30/#40 on the
  merged tree with B's native 6/8/18 scale test and planner deadline/cost controls.
- A+B: #39 SKHYB source coverage and B-CON007 Class 1 priority require explicit
  cross-section acceptance; passing synthetic RF1 fixtures does not prove coverage.
- Keith+D: tracker 22 original review record/GAP68 missing; retain ID collision
  and unavailable evidence, do not overwrite hosting IDEA-046 or pretend reviewed.

## Requested shared edits

IDEA-049 prerequisite entry: "2026-10-14: Keegan revoked the earlier wait and
requested section B execution. B proceeds with source-derived requirements;
driver-dependent integrated checks remain blocked for Keegan+Isaac/D before
overall completion. No driver or activation was authorized."

LEDGER: add IDEA-049-B, Final review B: decisions/strategy/risk/accounting,
IN PROGRESS, linked to this record. Baseline/results and backlog/runbook text
will be supplied after verification; no whole GAP is removed in this phase.

Exact shared text for D to apply at integration (add to existing items; do not
delete whole multi-part GAPs until every subpart is verified):

**docs/LEDGER.md row:**

`| IDEA-049-B | 2026-10-14 | Final review B: decisions, strategy, risk and accounting | PARTIAL; DEPLOYMENT BLOCKED | [record](ledger/IDEA-049-B.md) |`

Use the existing table's column arrangement while retaining this exact content.

**docs/INCOMPLETE_WORK.md addition to GAP12/32/64/65:**

> 2026-10-14, IDEA-049-B: B's allocation-profile/UTC/malformed-input defects
> are fixed offline with fail-first evidence. Remaining blocking integration:
> trusted journaled UTC daily anchor (#31, D/Yao Zhu with C mark), mandatory
> risk/terminal planning under spending/delivery HALT (#34, D/Yao Zhu with team
> semantics), authoritative chain-balance reconciliation and fresh BNB marks
> (#36, C/Isaac producer + D/Yao Zhu hook + B/Keegan agreed consumer). Validate
> restart, duplicate/missed boundary, unexplained/unknown assets, final receipts
> and exact replay on the merged IDEA-048 driver before final-review completion.

**docs/INCOMPLETE_WORK.md addition to GAP09/10/13/50/51/53/54/64:**

> 2026-10-14, IDEA-049-B: approval remains blocked on actual dated/hash-bound
> five-name quote costs and team-adopted LIVE values (Isaac+C, team+B; Oct 22),
> executable mark/all-in actual-size cost and concentration conventions (#38),
> positive after-cost default evaluation or explicit unvalidated-policy acceptance
> (#37, P2), declared regime/event/exit allowance dispositions and Class 1
> discretionary-vs-mandatory priority (team+A/B/C; Oct 22). Candidate profiles and
> synthetic tests are not adoption, measured evidence or profitability. Keep
> H02/EXP001 NOT RUN unless new preregistered real evidence exists.

**docs/INCOMPLETE_WORK.md addition to GAP06/08/11/14/15/66:**

> 2026-10-14, IDEA-049-B: adopted equal-weight/top-up/trim/loss/session consumers
> have offline regression coverage, including 14-day downstream PostgreSQL replay
> with terminal revert/gas and native 6/8/18 mapping. Source/calendar/SKHYB coverage,
> first BNB, official final valuation/window and unchanged-build integrated
> rehearsal remain with A/C/D/team before final activation. Research gap,
> adjacency, midnight and terminal-gas corrections pass deterministic tests;
> historical illustrative coefficients/statistics need a new preregistered,
> dated/hash-bound rerun before reuse (Keith). Do not close whole GAPs from this
> consumer evidence.

**docs/skill/SKILL.md:** Q08 summary correction already applied in this PR under
protocol §1.2; preserve it at merge. No further summary/rule edit requested and
no requirement should be labelled tested/settled merely from this partial review.

**README.md and docs/build/AWS_RUNBOOK.md / docs/build/runbook.md addition:**

> Final review B (IDEA-049-B) is partial; deployment remains blocked. Before
> activation, merge/review the IDEA-048 driver; verify journaled UTC anchors,
> mandatory HALT exits, authoritative chain reconciliation/fresh marks, actual
> measured and adopted profile values, policy/deviation dispositions and source/
> calendar coverage. Run the complete 14-day synthetic rule schedule and 5+day
> same-build weekend rehearsal on the final merged tree, then fresh-final-wallet
> integrity checks. Synthetic downstream replay and green CI do not authorize
> signing, AWS deployment or a profitability claim. Owners and deadlines are
> listed in docs/ledger/IDEA-049-B.md B-RISK01–07.

## WR-B — review fixes #45 #46 #57 #64.3 (2026-10-15)

Owner: Claude Code session for Yao Zhu (section D integrator), on branch
`claude/wr-b-risk-fixes-0f380b` from base `7b7acd2` on
`codex/system-testing-20261012`. Scope is B's code only (`larp/strategy`,
`larp/risk`, the runtime market-view call site for #45) and B's tests. Team
decisions #34, #36, #37, #38, #55 and #56 are out of scope and not decided here.
No LIVE profile value changes. Synthetic tests only: no keys, signing, chain,
ai-seeds or AWS calls.

### Pass criteria (registered before any test or code change)

All four issues still reproduce on `7b7acd2` (triage by the starting session).
Each fix lands as failing tests pushed first, then the fix. The suite must pass
with no existing test weakened, skipped or removed; any existing test whose
expectation encodes the reported defect is named here with the reason before it
is changed.

**WRB-45 (#45, WR03, P1): one bad market row must not block other names.**
- WRB-45-1. `market_view` is per row. A row with a row-level defect (wrong
  schema; missing `token_id` or `underlying_id`; currency other than USDT;
  `money_scale` other than 1,000,000; `decimals` missing, not an int or above 30;
  `price_units` missing or below 1; malformed `measured_roundtrip_bps`) maps its
  symbol to `None` and records the reason in a caller-supplied dict. It does not
  raise.
- WRB-45-2. Set-level problems still raise `ContractError`: the collection is not
  a list, a row is not an object, a symbol is missing, unknown or outside the
  universe, a symbol appears twice, or (LIVE) a row has a fake or unidentified
  origin. The B-REG-04 tests (`test_b_req_022_*`) still pass unchanged.
- WRB-45-3. Flatten window (LIVE FINAL profile, `2026-11-10T14:00Z`), NVDAB and
  GOOGLB held and quoted, one bad row for unheld TSLAB (each defect in
  WRB-45-1): the plan has no `INVALID_REQUIRED_INPUT`, has `TERMINAL_FLATTEN`
  requirements for both held names, plans one mandatory SELL of a held name, and
  records `{"reason": "INVALID_MARKET_ROW", "symbol": "TSLAB"}`.
- WRB-45-4. Same, but the bad row is held NVDAB: NVDAB's requirement keeps its
  full `remaining_sell_units` with status `BLOCKED_INPUT`; GOOGLB's mandatory
  SELL is planned; the `INVALID_MARKET_ROW` rejection names NVDAB; new risk stays
  blocked (`unvalued_symbols` includes NVDAB).
- WRB-45-5. Non-terminal POSITION_CAP trim of a held name still plans its
  mandatory SELL with a bad unheld row; `decide()` still returns a proposal with
  a bad unheld row.
- WRB-45-6. Runtime evidence path: `ContextBuilder._reductions` with a bad
  unheld row still returns the `CLASS_1_EXIT` reduction for held NVDAB (real
  RF1 producer fixture), instead of `[]`.

**WRB-46 (#46, WR04, P1): gas above the reservation is charged, not rejected.**
- WRB-46-1. A final reconciler FILL whose `gas_bnb_units` exceeds the
  reservation's `bnb_units` but not the wallet's BNB balance is applied: BNB
  falls by the actual gas, `gas_value_units` rises by the actual gas value, the
  terminal fill deletes the reservation, and the overage is recorded in
  `accounting.gas_over_reserve_bnb_units`.
- WRB-46-2. Approve plus swap above the quote: reservation 10,000; approve
  receipt 8,000 gas (non-terminal, reservation left at 2,000); swap receipt
  15,000 gas is applied; total charged 23,000; no reservation remains. The same
  sequence through `integration.settlement.settle` leaves no BNB reservation row
  for the intent.
- WRB-46-3. Gas above the actual BNB balance still raises `ContractError` and
  changes nothing.
- WRB-46-4. No LIVE profile value or validator changes (`larp/strategy/profiles.py`
  untouched). The reservation margin over the quoted gas is a team/B decision,
  recorded as B-DEC-08 below, not adopted.

**WRB-57 (#57, WR15, P2): a Class 1 latch reaches the planner on its own.**
- WRB-57-1. The planner reads `CLASS_1_EXIT` latches from the persisted policy
  state (`snapshot.policy_state`, the state committed by the last round). With
  an NVDAB latch, NVDAB partly sold and still held, GOOGLB held with a stale
  mark, no proposal and no reduction constraints, the planner emits an NVDAB
  requirement with `max_units` 0 and reason `CLASS_1_EXIT`, and plans a mandatory
  NVDAB SELL when a quote exists. The scenario check: `decide()` raises on that
  snapshot (so the old path had no target).
- WRB-57-2. A latch on a name with zero units adds no requirement.
- WRB-57-3. The latch clears only by the IDEA-035 rule: a later round with no
  evidence keeps it (requirement still emitted from the next persisted state);
  after `decide()` resolves it on a complete review with no Class 1 finding (A8),
  the planner emits no `CLASS_1_EXIT` requirement from that persisted state. The
  planner never clears or writes the latch itself. A resolution decided in the
  current round takes effect from the next round (one-round lag, conservative).
- WRB-57-4. A malformed `blocked` map in the persisted state fails closed as
  `INVALID_REQUIRED_INPUT` with the held names kept.

**WRB-64.3 (#64 item 3, P3): mandatory sells ordered by reason class, then value.**
- WRB-64-1. Mandatory requirements are ordered by class first: any requirement
  with `CLASS_1_EXIT` or `TERMINAL_FLATTEN` before all others; then by
  descending notional value of `remaining_sell_units` at the current mark; then
  by symbol. A requirement without a usable mark sorts after valued ones in its
  class.
- WRB-64-2. Two non-terminal requirements where the name with more token units
  has the smaller notional: the larger-notional name gets the one intent.
- WRB-64-3. A small Class 1 requirement is planned before a larger POSITION_CAP
  trim.

**Full suite.** Python 3.12 from `deploy/requirements-test.lock`, pinned
`postgres:14.24-bookworm@sha256:5a05f61a…` with `LARP_TEST_DATABASE_URL`. Pass =
the base's counts plus the new tests, with failures only in the same
environment-only tests as the base run on this machine.

### Results (2026-10-15)

Criteria pushed at `69caadd` before any test or code. Failing tests pushed at
`179d156` (55 tests in `tests/risk/test_wr_b_review_fixes.py`, code still at
`7b7acd2`): **53 failed, 2 passed**. The two passes are the registered controls
WRB-46-3 (gas above balance already raised) and WRB-57-2 (no latch requirement
on a flat name). Each failure was for the reported reason: whole-plan
`INVALID_REQUIRED_INPUT` / `decide()` raising on one bad row (#45),
`Gas exceeds committed reserve/actual balance` (#46), no NVDAB requirement or
no fail-closed on malformed latches (#57), and the token-unit order (#64.3).
`ContextBuilder._reductions` returned `[]` with one bad unheld row.

| Issue | Fix commit | What changed |
|---|---|---|
| #45 WR03 | `d9b87d4` | `market_view` per row (`_row_defect`); reason in an optional `invalid` dict; planner records `INVALID_MARKET_ROW` and a held bad-row name stays `BLOCKED_INPUT`. Set-level checks unchanged. No runtime code change: `_reductions` now returns `[]` only for set-level problems. |
| #46 WR04 | `1a339a0` | `advance_accounting` rejects only gas above the actual BNB balance; overage charged and recorded in `accounting.gas_over_reserve_bnb_units`; terminal receipt releases the reservation. No profile change. |
| #57 WR15 | `2de511c` | Planner reads `CLASS_1_EXIT` latches from `snapshot.policy_state`; cap 0 until the position is zero; malformed latch map fails closed. The planner never writes latches. |
| #64.3 | `ba81aa2` | Mandatory requirements sorted by (Class 1 / terminal first, unmarked last, descending notional, symbol). |

After each fix the focused B/strategy/integration/research/redteam(/runtime)
suites were green except the not-yet-fixed WR-B tests. No existing test was
changed, skipped or removed; no existing expectation encoded the defects.

Side effects checked and accepted:
- `larp/runtime/driver.py` (D, unchanged code) also calls `market_view` for the
  daily anchor. A bad row for an unheld name no longer blocks the anchor; a bad
  row for a held name still gives `MARK_UNAVAILABLE` (equity has no mark).
- Under a global execution block every requirement still becomes `BLOCKED`, as
  `BLOCKED_MARK` did before; `BLOCKED_INPUT` is shown only on unblocked rounds.
- A latch resolved by this round's proposal still forces the exit for that one
  round (WRB-57-3, registered as conservative).

Full suite at fix head `ba81aa2` (clean pushed tree; macOS, Python 3.12.14 from
`deploy/requirements-test.lock`, pinned `postgres:14.24-bookworm@sha256:5a05f61a…`
container on loopback): **1474 passed, 7 skipped, 1 xfailed (#23), 2059 subtests,
0 failed**, 204.87s. Base `7b7acd2` on the same machine and setup: 1419 passed,
7 skipped, 1 xfailed, 2059 subtests, 0 failed. The difference is exactly the 55
new tests. Synthetic checks only: no live data, signing or chain.

Linux mirror CI on PR #77 head `a853528` (pushed to the mirror and started by
Yao Zhu): [run 38750352994](https://github.com/Cookiemunchrr/larp-ci-mirror/actions/runs/38750352994),
all four jobs SUCCESS. Runtime full suite **1477 passed, 4 skipped, 1 xfailed,
2059 subtests**, 306.37s: the mirror base on `e5db681` (1422 passed, 4 skipped,
1 xfailed, 2059 subtests) plus the 55 new tests. Opt-in systemd 3 passed,
5 subtests; offline demo and Docker build/smoke passed (job success).
Terraform mock tests: deploy/aws 15 passed, 0 failed; deploy/bootstrap 1 passed,
0 failed. Host-bundle build/provision succeeded. These do not establish
deployment readiness.

B-DEC-08 (gas reservation margin) is added to the DECISION-NEEDED table above.
WR-B does not change the PARTIAL REVIEW / DEPLOYMENT BLOCKED status.

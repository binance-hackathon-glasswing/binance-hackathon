# Section B catalogue — IDEA-049

## B-FRZ-01 — independent freeze (2026-10-14 SGT)

Base `c829fae038a0589085d13552b1123802babbde4c`, branch `review/final-b-20261014`.
Derived before opening B implementation/tests in this task. Earlier conversation
included PR #21 editing and quoted prior findings; prior exposure is disclosed,
but neither code nor prior findings is a requirement source. Frozen rows change
only by dated amendments. User revoked the earlier wait; B may proceed, with
driver-dependent integration remaining blocked for Keegan+Isaac/D (B-PRE-01).

## Sources (short names used below)

- PAGE: verbatim `docs/official/source_page.md`, full page, especially Challenge,
  Scoring and Rules. F summaries checked against it.
- KIT: participant Guide PDF pp3–8,10,17; `bstocks-trading-guide.md` market,
  quote, error, security and limitations sections; `web3-open-api.md`. K3/K6 and
  F91/93/95/105 checked against verbatim text. Demo constants/nonce retries are
  observations/examples, not binding policy values.
- ORG: SKILL F107/F114/F115/F117, relayed answers/team statements, not issued
  competition rules. Q03/04/06/39/40 retain the unsettled official details.
- PROP: exact submitted `docs/proposal/proposal_answers.md`, Your Proposal,
  market/execution sources, Position & risk management, validation,
  reproducibility and delivery statements; plan Declared values checked against it.
- DEC35: IDEA-035 adopted A8/B2–6/B11/C1–5/C8/§10.1 (SYZ, Oct 11).
- DEC37: IDEA-037 §1 and held-name top-up addendum (SYZ, Oct 11). The addendum
  supersedes unheld-only top-up; Class 2 five-session block supersedes earlier
  three-item forced-exit recommendations. §§5/6 of DEC35 bind only as adopted
  by §10.1, never by the earlier recommendation label alone.
- DR/AT: allowed DEPLOYMENT_BUILD DR list and IDEA-021 AT01–20, adopted as this
  user-invoked review's engineering gates, not organiser rules.
- DEV: release deviation register/plan §6.5. DRAFT or OPEN rows are not adoption
  evidence; exact later decided source governs. IDEA-040 metadata establishes
  build scope only; no independent adopted trading value was found there.

## Requirements

Numbers below expand to B-REQ-NNN. Every row is one observable obligation.
Source labels: PAGE/KIT=RULE; ORG=relayed organiser; PROP=DECLARED;
DEC35/37=DECIDED; DR/AT=review-adopted acceptance. Every row is MUST unless
explicitly stated otherwise. UC sets and offline limits are defined after the table.

| ID | Testable statement: when X, system must Y | Source / short quote | Acceptance | UC set / offline |
|---|---|---|---|---|
| 001 | When producing stock intents, permit only long spot holdings in the five eligible bStocks against USDT. | PAGE Rules/F64 “Leverage, shorting, derivatives”; KIT p17 “only trades the five eligible bStocks” | Reject unknown/substitute symbols, negative holdings and prohibited targets. | instruments / yes |
| 002 | When converting amounts, use supplied token decimals and integer smallest units. | KIT p17 “takes decimals from the API response”; K3 | Non-default cash/token/BNB scales preserve economic values exactly. | numeric / yes |
| 003 | When a bStock is closed/halted, place no bStock order. | KIT p6/F95 “don't place orders” | False openState blocks BUY/SELL; obligations remain visible. | market / yes |
| 004 | When consuming data, reject any information unavailable at decision cutoff. | PAGE Challenge/F20 “information available ... at each decision point”; PROP filter | Future/retrieved-after-cutoff bars/assessments cannot influence earlier decisions. | data / yes |
| 005 | When valuing decision risk, use fresh executable token marks, not derived share reference. | PROP “equity measured on executable quotes”; KIT p6 “not an official stock market quote” | Missing/stale marks block new risk without deleting holdings or declaring fake flatness. | valuation / yes |
| 006 | When computing equity/return/drawdown, include actual fees and BNB gas. | PAGE F44 “Trading fees and gas reduce what remains”; F45 previous peak | Approval/fill/revert/terminal costs affect ledger and drawdown once. | accounting / yes |
| 007 | When reporting performance, retain the complete scored window. | PAGE F46 “No best-week selection, no dropped days” | Include losses and final liquidation expenses in replay/report. | replay / yes |
| 008 | When describing score, preserve proposed equity formula and unresolved official terms. | PAGE F43 “Proposed FinalScore”; F52 final rules; ORG F115 | No invented score weights/trade quota; Q39/conflict stays visible. | economic / docs/live |
| 009 | During scored operation, prevent human trade choices or policy/version changes. | PAGE F60; ORG F114 “no changes allowed”; F117 paraphrase | Immutable profile/version and autonomous controls; D's zero-human rehearsal. | profile / yes+rehearsal |
| 010 | When equal-weight allocation is eligible, target four names at 20%, total 80%. | DEC35 §10.1 “equal weight, four names at 20%” | ≤4 settled/pending slots and post-cost capacities at 100/200 USDT. | allocation / yes |
| 011 | When selecting names, exclude blocked names and prefer lower measured costs. | DEC35 §10.1 “unresolved red flag ... most expensive” | Deterministic feasible ranking, no fabricated cost/edge evidence. | allocation / yes |
| 012 | When gross≥75%, forbid top-ups; below 75%, eligible held gaps and unheld names may top up. | DEC37 §1 “gross<75%”; addendum “held ... also bought” | Exact trigger; all entry gates apply; no incidental sell above target. | allocation / yes |
| 013 | When accepting buys, retain ≤20% name and ≤80% gross ceilings including commitments/costs. | DEC37 buy ceilings | Pending/concurrent intents cannot breach caps or spend reserved funds. | reservations / yes |
| 014 | When only operating caps are exceeded by price drift, do not sell solely for drift. | DEC37 “Never sell because prices moved” | 20–25% name/80–90% gross alone yields KEEP. | caps / yes |
| 015 | When a name exceeds 25%, retain mandatory reductions back to 20%. | DEC37 “above 25% ... back to 20%” | Strict boundary; child caps/fills/restarts preserve residual target. | caps / yes |
| 016 | When gross exceeds 90%, retain proportional reductions back to 80%. | DEC37 “above 90% ... proportional ...80%” | Collision/multiple-name reductions do not oversell or rebuy. | caps / yes |
| 017 | When UTC daily loss reaches 3%, block new risk for the remainder of that day. | PROP “Daily loss≥3% ... rest of the UTC day” | Inclusive threshold; same-day rebound/restart cannot clear latch. | loss / yes |
| 018 | At UTC rollover, anchor before the first new-day return interval without post-loss reset. | PROP UTC-day convention; AT15 | Consecutive/missed/duplicate midnight and backward clock; preserve run latches. | time / yes+D integration |
| 019 | When drawdown reaches 8%, block new risk while permitting valid exits. | PROP “new-risk halt, not a liquidation” | Exact peak-to-low threshold; daily reset cannot clear run-wide latch. | loss / yes |
| 020 | When drawdown reaches 12%, retain immediate reductions to gross≤40%. | PROP “automatically reduced to≤40%, using fresh quotes” | No 90% hard-line delay; quote failure retains obligation. | loss / yes |
| 021 | Under new-spending HALT with intact authority, preserve independent mandatory risk/terminal planning. | PROP risk exits; AT02 “invalid policy never disables mandatory controls” | Policy errors/HALT cannot suppress valid reductions; integrity failure stays fail-closed. | failure / yes+D integration |
| 022 | When data/model/tool/schema fails, take no new policy risk and record the failure truthfully. | PROP “HOLD, no new risk”; G20/G27 | No timeout-to-BUY; independent valid mandatory controls persist. | failure / yes |
| 023 | For new stock entries, enforce impact≤min(50bp, twice measured median). | DEC35 B4 | Inclusive boundaries; missing per-name measured median refuses entry. | cost / yes |
| 024 | For new entries, enforce total spread/impact/fee/gas cost≤50bp without double counting. | PROP cost; DEC35 B4 “total entry cost ...≤50bp” | Dimensionally correct quote/reference algebra and exact thresholds. | cost / yes |
| 025 | When estimating round-trip costs, include and label an explicit future exit allowance. | PROP “explicit allowance for the cost of exiting later” | Estimated/realized costs distinguished; comparisons include both legs. | cost / yes |
| 026 | For mandatory risk exits, entry profitability/minimum thresholds must not veto reductions. | PROP “Entry-cost thresholds never block ... risk-reducing exit” | Small/high-cost exit eligible under its own slippage/integrity/order cap. | exit / yes |
| 027 | When an order exceeds its amount/slippage cap, refuse or safely split under that cap. | KIT p17 “orders above it are refused”; PROP slippage | Both directions/scales; reduction residual persists through safe child caps. | numeric / yes |
| 028 | When LIVE profile lacks a required value/provenance, refuse startup/planning. | DR09 “every value set and sourced”; DEC35 B6 | Null/malformed/unmeasured profiles refused; proposals not silently adopted. | profile / yes |
| 029 | When setting live parameters, derive from approved measurements/sources, never dev P&L. | DEC35 B6 “never from P&L”; PROP fixed strategy | C DR01 cost summary and team approval required before active profile. | profile / docs/live |
| 030 | On verified Class 1 Item 4.02, sell held position and block unresolved-latch buys. | DEC35 §6/§10.1 | Critical exit despite Class 2 collision; no LLM trade authority. | evidence / yes |
| 031 | On Class 2 Item 1.05/2.06, block buys/adds for five sessions without forced sale. | DEC35 §10.1 | Session-based holiday/DST expiry, no duplicate-trigger extension. | evidence / yes |
| 032 | On Class 3 statements, retain SHADOW without trading effect. | DEC35 B2/§10.1 | Unverified/general/hypothetical statements cannot command trades/blocks. | evidence / yes |
| 033 | On source correction/withdrawal, re-entry may occur only after remaining gates pass. | DEC35 A8 | Clear critical latch without losing independent Class 2 block; incomplete newer revision cannot clear. | evidence / yes |
| 034 | Below available BNB reserve, replenish only through authorized USDT→nativeBNB resource intent. | KIT p5; DEC35 C1/B11; DR06 | No magic zero-gas bootstrap; reserve protects exits; BNB is not a stock slot. | gas / yes+live bootstrap |
| 035 | When gas fill settles, account actual cash paid/nativeBNB received/fees/gas using correct scales. | PAGE F44; KIT rawBalance; AT18 | Native-resource fill needs no nonexistent bStock quote; outcomes charged once. | gas / yes |
| 036 | When intents compete, reserve cash/holdings/gas/incoming claims/capacity atomically. | AT04; DEC35 A9 | Real PostgreSQL races/restarts cannot overspend; pending sells cannot fund buys. | reservations / yes |
| 037 | On FINAL success/revert, release matching reservations once; unconfirmed attempts do not change balances. | DEC35 A9; AT04/07/18 | Replay/duplicate idempotence; approval gas; C's finality facts required. | accounting / yes+C/D |
| 038 | On unexplained chain balances, reconcile before new risk without touching unsolicited assets. | PAGE unexplained transfers; PROP “every transaction and balance change”; AT18 | Recorded discrepancy/obligations; no invented fill or external funding. | accounting / yes+C/D |
| 039 | At new-risk cutoff, forbid new positions and reinvestment. | DEC35 C4; DEC37 “no reinvestment” | Exact boundary; gas/stock distinction; post-approval expired buy refused. | terminal / yes |
| 040 | At terminal flatten, retain reductions until factual flatness or explicit block, aiming for Nov 11 15:00UTC. | DEC35 C4 “finish flattening by Nov 11 15:00UTC” | Failed/reverted/closed/dust paths never fake completion; report lateness. | terminal / yes+rehearsal |
| 041 | On final-wallet activation, initialize truthful fresh balances/risk anchors. | PAGE F14; DR17 | Old run/wallet/nonce/risk state cannot silently initialize final run. | activation / yes+C/D host |
| 042 | Under regime stress, lower the allowed exposure budget and veto new risk as declared. | PROP “regime governor lowers the exposure budget” | Missing series/stress cannot increase permitted exposure; forced-trim distinction explicit. | regime / yes+decision |
| 043 | For scheduled macro/earnings events, use a preregistered class rule or expose the unresolved deviation. | PROP “pre-registered rule per event class”; DEV20 OPEN | No ad-hoc human choice; team disposition required before activation. | event / decision+yes |
| 044 | For malformed/stale/nonfinite/unknown/duplicate policy outputs, independent risk still applies. | AT02/03 | Precision/version/NaN/Inf/negative targets refused without disabling safety. | hostile / yes |
| 045 | On identical recorded-input replay, reproduce policy/latches/plans/accounting deterministically. | PROP rerun; AT01/13/16 | No hidden clock/live I/O; matching hashes; future edits cannot alter past. | replay / yes |
| 046 | In economic/default-policy review, report unrun evaluation and positive after-cost support criterion honestly. | PROP “make no return promise”; DEC35 A5; F50 | Synthetic checks never imply profit; default H02/EXP001 NOT RUN preserved. | economic / docs/live |
| 047 | For candle session inputs, use only completed regular sessions closing 16:00 ET, correctly in UTC. | DEC35 B3 “closing 16:00 ET, fixed in UTC” | DST/holiday/short-history/early-close/identity tested; no fabricated or Ondo-extended series. | sessions / yes+real data |
| 048 | While signed attempt is unresolved, reserve the worst authorized financial outcome. | AT04/08/09 | Expiry/index absence cannot free funds; unsupported replacements disabled. | reservations / yes+C |
| 049 | On colliding safety targets, retain all constraints and forbid same-round rebuy. | AT05 | Name/gross/deep/terminal/evidence collisions and child costs conserve ledger. | collision / yes |
| 050 | When changing limits in development, version/explain them and never loosen for losses. | PROP governance; PAGE F60/61; ORG F117 | Policy cannot mutate risk hash; no unapproved/in-run profile switching. | profile / yes+D |

## Use cases — B-UC-001–036

| UC | Trigger/state → expected outcome | REQ |
|---|---|---|
| 001 | 100/200USDT, zeroBNB → no magical spending/bootstrap; factual ledger. | 010,013,034–038 |
| 002 | Four eligible low-cost names, fifth costly/blocked → deterministic ≤4 equal targets. | 001,010–013 |
| 003 | Gross just below/at/above 75%, held below/at 20% → exact top-up threshold, no sell. | 012–014 |
| 004 | Name at/above 25%, gross at/above 90% → strict trigger, persistent reductions. | 015–016,049 |
| 005 | Loss just below/at/above 3%, then rebounds → same-day halt persists. | 017–019 |
| 006 | Two days, crash/missing/duplicate midnight → trusted anchor before interval, no post-loss reset. | 018,045 |
| 007 | Clock backward/skewed/reboot → no future/expired buy or cleared run latch. | 004,018,039,045 |
| 008 | Drawdown at 8%, rebound, at 12% → no buys, exits available, immediate deep trim. | 019–022 |
| 009 | HALT with holdings → valid mandatory planning persists; integrity loss refuses unsafe actions. | 021–022,040 |
| 010 | Impact/cost at/over limits → exact inequalities and no double counting. | 023–027 |
| 011 | All names expensive → logged HOLD/cash, no quota or fabricated edge. | 008,011,024,046 |
| 012 | Nondefault scales, huge/small/zero/negative/nonfinite amounts → exact math or refusal. | 001–002,027,035,044 |
| 013 | Market closed for days → no stock orders; obligations persist; gas eligibility separate. | 003,034,040 |
| 014 | Future/shuffled/duplicate/missing/early-close candles → no leakage/entity mix/fictional bars. | 004,047 |
| 015 | Model/evidence/context timeout/malformed/outage → no new risk, valid safety retained. | 021–022,044 |
| 016 | Missing/stale token quote, misleading share reference → refuse unsafe mark, preserve holdings. | 005,026,040 |
| 017 | Fill differs from quote, fees/revert/approval gas → actual final facts once. | 006,035,037 |
| 018 | Duplicate/reordered final facts or reserve/settle crash → same ledger and correct release. | 036–038,045,048 |
| 019 | Concurrent buy/sell/top-up compete → reserve assets/capacity atomically. | 013,034,036,048 |
| 020 | Class 1 exit plus Class 2 block → critical sell; independent block survives resolution. | 030–033,049 |
| 021 | Five-session Class 2 across weekend/holiday/DST → no forced sale/duplicate extension. | 031,047 |
| 022 | Source correction then incomplete newer revision → no premature re-entry. | 004,030–033 |
| 023 | Class 3 hostile/hypothetical statement → SHADOW, no trading/secret/config authority. | 032,044,050 |
| 024 | Small mandatory SELL vs cap/minimum/slippage → safe chunks and explicit residual/dust. | 015–016,026–027,049 |
| 025 | Colliding risk/terminal/cap obligations, failed then good quote → tightest targets retained, no rebuy. | 020,040,049 |
| 026 | Exact start/cut/flatten/end, approve confirms late → no new-risk swap; exit obligation retained. | 039–040,048 |
| 027 | Terminal fill/revert gas crosses loss threshold → final costs included, no fake flatness. | 006,020,037,040 |
| 028 | Fresh final wallet with old run state → truthful initialization/mismatch refusal. | 009,041,050 |
| 029 | Stress lowers budget, missing series/correlated book → preserve decided gates; flag undefined concentration policy. | 010,013,042 |
| 030 | Scheduled event without adopted rule → decision gap, no human override. | 043,050 |
| 031 | Synthetic 14 days incl.DST/weekend/rollover/loss/outage/terminal → all decided rules/replay hold. | 007,009,017–022,039–045 |
| 032 | Chain discrepancy/unsolicited asset → record gap; no prohibited transfer/swap or invented fill. | 001,038 |
| 033 | DB/disk/upload/credit outage incl.02:00UTC → local obligations/facts preserved; D integration named. | 021–022,036–038,048 |
| 034 | Tampered profile/release, stale owner/wrong wallet/malicious target → independent safe refusal. | 001,009,044,048,050 |
| 035 | Auditor samples decision/fee/balance change → complete full-window recorded trace/replay. | 006–009,037–038,045 |
| 036 | Missing measured costs or official score/BNB convention → no invented profile/answers. | 008,023–029,034,046 |

UC sets: instruments=001/002/012/032/034; numeric=012/024; market=013/016/026;
data=007/014/015/022; valuation=010/016/017/027; accounting=001/017–019/027/032/035;
allocation=001–003/011/029; reservations=018/019/026/034; caps=004/024/025;
loss=005–009/025/027/031; time=006/007/021/026/031; failure=009/013/015/033/034;
cost=010–012/024/036; exit=009/020/024–027; profile=028/034/036;
evidence=020–023; gas=001/013/017/019/036; terminal=013/024–028/031;
activation=028; regime=029; event=030; hostile=012/023/034;
replay=006/018/031/035; economic=011/031/035/036; sessions=014/021/031.
Protocol matrix axes: phase 001/028/031/035; time 005–007/013/021/026/031/033;
dependencies 013/015/016/033; data 012/014/017/022/023; process 006/018/019/031/034;
resources 001/013/019/024/033; security 023/028/034; audit 017/018/031/035.

## Assumptions — B-ASM

Only evidence checked in this review can validate an assumption. Tests to be
performed are prospective; documentary observations do not qualify live behavior.

| ID | Assumption / status and checked evidence | Validation, failure consequence, owner/deadline |
|---|---|---|
| 001 | Internal BNB equity convention equals official scoring; UNVALIDATED, Q03/Q39. | Team confirms official valuation before Oct 22. Internal risk convention must be explicit; official score claim blocked. |
| 002 | Tokens trade 24/7; PARTIAL team C8, no measured hours here. | C DR01 ≥3days/weekend; openState gates orders regardless; before LIVE profile. |
| 003 | Kit gas amounts/30s expiry remain accurate; PARTIAL, documentary observations only. | C dated quote/gas/expiry artifacts; configurable conservative limits before DR09. |
| 004 | Quote/reference components permit correct spread+impact/fee decomposition; UNVALIDATED live. | B/C dimensional tests and measured executable quotes; refuse missing references/fees; before Oct 22. |
| 005 | Declared event planner may be omitted; UNVALIDATED, DEV20 OPEN. | Team decides implemented class rule or justified deviation before Oct 22; blocks activation. |
| 006 | LIVE freshness/minimum/slippage/reserve/dates are usable; UNVALIDATED until measured/adopted. | B derives, C supplies DR01, team approves before Oct 22; no automatic adoption. |
| 007 | Calendar/source coverage handles all five incl.SKHYB and half-days; PARTIAL. | A/C coverage and B identity/timestamp/short-history tests before DR08/10; conservative missing-data refusal. |
| 008 | Trusted UTC-midnight mark survives outages/restarts; UNVALIDATED integration. | B accounting contract+D merged-driver test before closure; missing boundary blocks new risk. |
| 009 | Chain/receipt facts are authoritative and idempotent; UNVALIDATED live. | C adapter+D durability+B accounting invariants before GateB; no premature financial release. |
| 010 | Proposed final/opening equity is final score; PARTIAL, conflicting F115. | Team Q39 before freeze; retain realized-PnL/full-equity reports, no invented score weights/quota. |
| 011 | Default equal weight has economic edge; UNVALIDATED, no return promise. | Rights-cleared costs/data and preregistered evaluation or explicit team acceptance of unvalidated default before activation. |
| 012 | Same-build autonomous restart is organiser-accepted; PARTIAL team C5 only. | Team Q40; D same-build no-human rehearsal before activation. |
| 013 | Correlated-tech book needs no additional aggregate limit; UNVALIDATED policy. | Team settles GAP10 before Oct 22; max-position count alone does not settle concentration. |
| 014 | AT matrix is this review's adopted engineering gate. | VALIDATED by user-invoked common protocol §1.1/§4, not official rules; unsupported deployment capabilities stay disabled. |
| 015 | Turnover/order-count/minimum/clock/reserve numeric defaults are adopted. | UNVALIDATED unless exact decision supplies each value; B decision register before Oct 22, never infer from implementation. |

## Conflicts — B-CON

- 001: PAGE F43 equity ranking/F45 tie-break/F50 no trade-count score vs ORG
  F115 completed trades/PnL/drawdown/logs/repo and not-trading warning. Preserve
  both; DEC35 C2/C4 maximizes net equity and flattens without artificial churn.
  Q39: ask actual score weights, open-position and BNB treatment; no contact here.
- 002: PAGE improve-in-run vs F114/F117 freeze. Stricter one-build/no-human reading
  and DEV13/14 govern. Q40 automatic same-build restart remains separate from the
  already-settled prohibition on version releases.
- 003: PROP sizing/caps vs DEC35/37 equal weight/75% top-up/25%-90% hard lines.
  Decided source wins with recorded declared deviation; DRAFT rows are not authority.
- 004: Old G25 depth cap has no kit depth input. DEC35 B4 replaces it with impact,
  not permission to discard liquidity protection.
- 005: Declared event rule vs OPEN DEV20 needs a team decision.
- 006: Fixed 16:00 ET session convention vs half-day data needs explicit behavior;
  don't fabricate a close or silently substitute another series.

## Scope coverage

Every number below is a B-REQ ID; splitting ownership by aspect does not waive
cross-section acceptance. Unadopted opinions and build results are not requirements.

| Inventory item | Requirement / owner / disposition |
|---|---|
| F20 decision aspect | 004,010–050; acquisition A, execution C |
| F35,F42,F43,F44,F45,F46,F50,F52,F73 | 006–008,046; ASM001/010 retain unissued official parameters; hosting D |
| F64 holdings aspect | 001,034,038; prohibited transfers/signer C |
| F91,F93,F95,F105,F107 | 001–003,005–006,027,034–038; funding is a team statement, actual wallet/venue C/logs D |
| K3,K6 | 001–006,027,034–038,047; HTTP/auth/signing C |
| F114,F115,F117 | 008–009,039–041,046,050; releases/operations D |
| Never-do 1,4 | 001,009,034,050; humans/signing C/D |
| G02,G11,G13 | 001,009,023–029,034,038,046,050 |
| G15 | No adopted numeric depth/turnover manipulation rule inferred; no material misrepresentation/churn quota under 008/046; unsupported numeric policy ASM015 |
| G20,G21,G22,G23,G24,G25 | 010–027,039–043; G23 unresolved declared event rule ASM005 |
| G26,G27,G28,G29,G30,G46 | 002–005,009,022,028–029,034,042,047,050; old sizing superseded by decided equal weight; freshness values require adoption |
| PROP Your Proposal selective/abstain/verification/thesis/model/default sentences | 001,004,010–012,022,030–033,044–046; source/model loop A, training omitted under recorded default |
| PROP Control three layers/LLM never sizes or sets limits/write-ahead | 010–029,042–044,049–050; model authority A, signing C, write-ahead D |
| PROP Position actions/sizing/caps/example | 001–002,010–016; 9% worked example is not a limit; sizing deviation needs reason |
| PROP entry bullets 1–6 | 023–029,046; probability thresholds replaced by adopted default; depth by B4 |
| PROP exits three triggers and entry-cost bypass/cap | 019–022,026–027,030–033,039–040; model DOWN replaced by adopted class map |
| PROP drawdown four bullets | 017–022,042–043; unresolved event rule retained |
| PROP failure four bullets | 004–005,021–022,034,038,044 |
| PROP governance three bullets | 009,028–029,050; human HALT superseded stricter F114/117 |
| PROP market data/BSC/valuation and fixed-strategy validation sentences | 004–008,028–029,038,045–047; data rights/training A |
| PROP reproducibility policy/risk trace/rerun/reconciliation/nontrade balances | 006,036–038,044–045,048–050; durable release/logs D/signing C |
| Plan Declared values every parameter | Horizon/sizing/cost/caps/loss/depth 004,010–029,046–047; evidence budget A; threshold adoption blocked |
| Plan D05,D06,D07,D08,D09,D10,D11,D12 | D05 D hosting; D06/07/08 028–029,046; D09/10 004,047+A/C; D11 030–033; D12 010–020,039–040 |
| DEC35 A8,B4,B5,B6,B11,C1,C8,§5,§10.1,§10.2 | 010–040,046–047; §10.2 synthetic calculations are not adopted policy or profit evidence |
| DEC37 §1/addendum/durable trim requirement | 012–020,024–027,036,049; implementation/results not read before freeze |
| IDEA-040 decided parts | Metadata uses DEC35/37; no independent adopted trading value found; build/results deferred phase 2 |
| DEV all 21 rows | B aspects 01–07/13–14/20–21 map 009–050; A08–12/19; C16; D15/17/18 and register publication |
| DR06,DR08,DR09,DR10,DR14 | 028–035,039–040,047; firstBNB C/team, live measurement C, policy approval team |
| DR01,DR05,DR13,DR19 split aspects | Cost summary 023–029; financial facts 037–038; HALT021; replay 045; primary C/D |
| Other DR02,03,04,07,11,12,15,16,17,18,20,21,22 | C02–04/17; A11/12; D07/13/15/16/18–22; B041/045 activation/replay interfaces |
| AT01,02,03,04,05,06,12,13,15,16,18 | 004,006,013,017–022,026–027,030–049;06 authorization C,04/05/13 durability D |
| AT07,08,09,10,11,14,17,19,20 | C07–09/17; D10–11/14/20; A19; B financial/mandatory interfaces 006,021,036–038,044–048 |
| GAP06,08,09,10,11,12,13,14,15,32,50,51,53,54,64,66 | Corresponding 001–050; no whole item assumed complete. D applies verified dispositions only. |

Baseline, trace and code-derived amendments are appended only after this catalogue
is committed and pushed. No section completion or activation claim follows freeze.

## B-TRC-01 — Trace (2026-10-14, after freeze d2ed620)

This is a partial review, not a green deployment checklist. COVERED means the
named deterministic acceptance is exercised; synthetic passing evidence does
not validate external transports, policy adoption or profitability. Split rows
retain the weaker whole-requirement verdict when integration is absent.
Names after `::` are test functions (class prefixes omitted where unique).

Code keys: **POL** `larp/strategy/policy.py:decide`; **SCH**
`larp/strategy/schema.py:profile/market_view/equity`; **PRO**
`larp/strategy/profiles.py:validate_live/build_live_profiles`; **PLAN**
`larp/risk/planner.py:plan/_quote_at_cap`; **ACC**
`larp/risk/accounting.py:advance_accounting/update_risk/roll_day`; **GAS**
`larp/risk/gas.py:plan_top_up`; **PRED**
`larp/strategy/predicates.py:update_directive_blocks/update_blocks`.

Test keys are exact files:

- **BR** `tests/risk/test_b_regressions.py`; **BQ** `tests/strategy/test_b_requirements.py`.
- **B14** `tests/risk/test_b_fourteen_day_run.py`.
- **EW** `tests/strategy/test_equal_weight.py`; **TRIM** `tests/strategy/test_trim_replanning.py`.
- **MECH** `tests/risk/test_mechanics.py`; **LP** `tests/strategy/test_live_profiles.py`.
- **LT** `tests/risk/test_live_terminal.py`; **RR** `tests/risk/test_live_resource_receipts.py`.
- **RB** `tests/strategy/test_review_boundaries.py`; **PS** `tests/strategy/test_pr_review_safety.py`.
- **RF** `tests/strategy/test_red_flag_classes.py`; **SES** `tests/strategy/test_token_sessions.py`.
- **POLT** `tests/strategy/test_policy.py`; **CON** `tests/test_contracts.py`.
- **PUB** `tests/integration/test_published_red_flag_policy.py`.
- **PG** `tests/storage/test_postgres.py`; **SYS** `tests/integration/test_service_system.py`.
- **SET** `tests/integration/test_settlement.py`; **EX** `tests/test_w04_execution.py`.
- **RES** `tests/research/test_research.py`; **ABS** `tests/research/test_absolute_return.py`.
- **REC** `tests/research/test_recorded_candles.py`.

| REQ | Implementation | Passing acceptance / exact later check | Verdict |
|---|---|---|---|
| 001 | POL,SCH,PLAN; contracts.Target/validate_proposal | BQ::test_b_req_001_generated_portfolios_cannot_create_short_leveraged_or_ineligible_positions; CON::test_invalid_weights_and_instruction_shapes / test_duplicate_unknown_and_excess_total_rejected. Structural authority: eligible market whitelist, nonnegative integer settled holdings, bounded targets, sell≤held, buy≤cash; C validates transaction identities. | COVERED consumer; C live transport separate |
| 002 | SCH:value/integer; ACC; GAS; larp.ports:decimal_string | MECH::test_exact_input_buy_records_variable_received_quantity; SYS::test_command_to_actual_service_receipt_audit_restart_and_replay (18-decimal BNB); BR::test_b_req_002_035_planned_native_gas_scale_agrees_with_execution_mapping (6/8/18); RR::test_actual_sell_proceeds_fee_and_basis_are_used. Internal micro-USDT is deliberate; C owns exact 18-decimal transport conversion. | COVERED arithmetic; C transport acceptance required |
| 003 | PLAN executable gates; POL window | MECH::test_mandatory_bypasses_minimum_and_cadence_but_market_blocks; LT::test_terminal_retains_unfilled_position_when_execution_gate_blocks; B14 closed weekend. | COVERED |
| 004 | SCH:usable; strategy.features; integration.contract:accept_for_strategy | POLT::test_future_perturbation_does_not_change_decisions_or_features; SES::test_duplicate_future_capture_wrong_timestamp_and_bad_calendar_reject; CON::test_expiry_boundary_and_clock_reversal. | COVERED |
| 005 | SCH:equity; PLAN partial lower-bound valuation | TRIM::test_partial_valuation_defers_allocation_until_all_marks_recover; MECH::test_stale_name_does_not_block_healthy_terminal_or_cap_exit. Production tokenPrice vs liquidation mark and BNB freshness do not meet the full declared executable-quote contract (#36/#38). | WEAK; B-RISK-03/04 |
| 006 | ACC; economic_views; research evaluation | MECH::test_approvals_reverts_gas_service_and_terminal_equity; RR::test_approval_and_revert_spend_gas_only; B14 terminal gas once; RES::test_mc_midnight_and_terminal_gas_counterexamples. Actual costs change balances once, not a second equity subtraction. | COVERED consumer |
| 007 | research.evaluation:evaluate; research.replay | RES::test_outcome_provenance_windows_purge_and_incomplete; B14 full Oct 29–Nov 11 decision/settlement journal plus final wallet. Full official scored timestamps/valuation remain unavailable. | NOT-OFFLINE; team official-window acceptance then D full-window rehearsal/report |
| 008 | B-CON001, ASM010; no invented score implementation | PAGE/ORG conflict rechecked; Q39 owner team must record final scoring/open-position/BNB treatment before Oct 22. No trade-count threshold introduced. | NOT-OFFLINE; B-RISK-01 |
| 009 | SCH hash identity; D release/version gates | CON::test_hash_binds_every_snapshot_version / test_wrong_policy_and_state_ownership_rejected; D must run unchanged-build zero-human scored-duration rehearsal and release checks, driver merged first. | NOT-OFFLINE; B-RISK-06 |
| 010 | POL equal-weight branch; PRO exact decided fractions | EW::test_p01_initial_build_takes_four_cheapest; LP::test_profiles_are_distinct_complete_and_full_position_capable; BQ::test_b_req_010_equivalent_fractions_and_separate_stress_budget_are_valid. One discretionary child/session implies staggered build, not instant 80% claim. | COVERED targets; ASM013 economic/concentration decision open |
| 011 | POL:_cost_rank; PLAN intent ordering | EW::test_p02_red_flagged_name_is_replaced_by_the_next_cheapest; RB::test_cheapest_selected_name_receives_the_first_execution_slot / test_equal_cost_execution_priority_is_stable_by_symbol. C cost currently fixed-size/excludes route gas; actual-size all-in rank convention needed (#38). | WEAK; B-RISK-04 |
| 012 | POL equal-weight top-up branch | EW::test_p03_no_buy_at_or_above_threshold / test_p14_p15_tops_up_held_names_and_skips_small_gaps / test_p16_no_top_up_at_or_above_threshold. | COVERED |
| 013 | PLAN capacities; RuntimePlanner incoming; PostgresStore reserve | MECH::test_post_cost_caps_at_both_wallet_sizes / test_pending_buy_and_sell_block_allocation_and_retain_requirement; PG::test_concurrent_reservations_only_one_wins; BQ generated portfolios. | COVERED consumer/store |
| 014 | POL KEEP; PLAN hard lines | EW::test_p05_no_sell_on_drift; TRIM::test_no_trim_for_drift_without_a_prior_trigger. | COVERED |
| 015 | PLAN durable name cap_trims | BQ::test_b_req_015_016_hard_lines_are_strict_at_exact_fraction_boundaries; TRIM::test_capped_name_trim_continues_below_trigger_until_target; EW::test_p06_hard_per_name_line. | COVERED under documented post-cost convention; ASM004 team review |
| 016 | PLAN durable gross_shares | Same BQ exact test; TRIM::test_gross_trim_continues_below_trigger_until_target_after_reload / test_costly_gross_trim_keeps_dust_residual_explicit. | COVERED under documented post-cost convention |
| 017 | ACC:update_risk; PLAN new-risk gates | B14::test_b_req_017_019_020_exact_loss_boundaries_and_utc_reset; EW::test_p17_loss_stop_blocks_top_ups. | COVERED |
| 018 | ACC:roll_day/update_risk; production hook absent | BR::test_b_req_018_offset_loss_observation_uses_utc_day / test_b_req_018_naive_loss_observation_is_rejected; B14 explicitly supplies midnight facts. Search found roll_day called only in research/test paths, no runtime producer (#31). | MISSING production; B-FND-005/D |
| 019 | ACC run_halt; PLAN exits | B14 exact loss test/replay; MECH::test_strictest_reduction_and_no_discretionary_buy; EW::test_p17_loss_stop_blocks_top_ups. | COVERED |
| 020 | ACC deep_cut; PLAN gross≤40% obligations | EW::test_p08_deep_drawdown_trims_at_forty_percent; B14 threshold/replay; TRIM residual tests. | COVERED consumer |
| 021 | PLAN spending gate; D coordinator/store HALT | RB::test_spending_block_preserves_mandatory_sales_and_healthy_buy_control passes B. Coordinator.start discards HALT plans; PostgresStore command gates all HALT (#34). | CONTRADICTED integrated; B-FND-006/D |
| 022 | PLAN input/policy rejection; B-FND003/004 fixes | BR::test_b_req_022_bad_market_collection_is_explicit_and_preserves_holdings / test_b_req_022_bad_portfolio_cannot_escape_the_input_rejection_path; MECH::test_invalid_and_absent_policy_still_reduce; B14 day 4 model outage. | COVERED B; integrated HALT remains 021 |
| 023 | PLAN quote impact / median; PRO sourced medians | LP::test_live_entry_without_depth_passes_cost_and_impact_and_rejects_high_impact / test_live_per_name_median_rule_cannot_use_larger_global_limit. Real medians need C capture/adoption 029. | COVERED inequality; NOT-OFFLINE measurements 029 |
| 024 | PLAN economic quote difference + fee + gas | LP::test_live_cost_cap_still_blocks_without_double_counting_impact; MECH::test_costly_opportunity_rejected. Quote/reference convention and actual marks require ASM004. | COVERED algebra; live inputs B-RISK-04 |
| 025 | PRO exit gas reserve; research terminal legs | MECH::test_exit_may_spend_exit_gas_reserve_but_zero_gas_blocks and RES paired-cost tests cover gas/terminal charges. No adopted explicit future exit-spread allowance in live entry record; tests would not catch omission. | MISSING complete declared allowance; B-FND-009/team |
| 026 | PLAN mandatory branch | LT::test_mandatory_sale_bypasses_impact_cost_minimum_and_cadence; PS::test_class1_exit_precedes_buy_and_bypasses_discretionary_filters. | COVERED B |
| 027 | PLAN:_quote_at_cap cap/requote; GAS | MECH::test_split_parent_replanned_after_actual_fill_and_fee / test_better_sell_price_requests_smaller_quote_and_can_progress; LT mandatory-slippage tests. C fresh post-approval deadline/slippage proof still required. | COVERED B; C #27/#40 |
| 028 | PRO validate_live; SCH profile hash | LP::test_missing_unsourced_and_unset_live_fields_reject / test_bad_measurements_and_impossible_cost_budget_reject; BQ cap-mutation rejection. Validation of fields cannot certify the source/adopter actually approved them; release acceptance 029. | COVERED schema; adoption 029 |
| 029 | PRO mathematical candidates; config/strategy/LIVE.md | LP impossible-budget/source checks. No actual five-name cost artifact or approved live profile supplied. Team reviews all formulas/values and manifest hash at Oct 22 freeze after C DR01. | NOT-OFFLINE; B-RISK-02 |
| 030 | POL,PRED; independent ContextBuilder reduction | PUB::test_real_rf1_producer_is_mandatory_even_without_policy; PS::test_class1_exit_precedes_buy_and_bypasses_discretionary_filters. Real ingestion/verifier producer, synthetic external filing. Sell action covered, but DEC35 §10.1's DISCRETIONARY_EXIT qualifier conflicts with mandatory precedence; B-CON007 requires disposition. | WEAK priority adoption; B-FND-010/team; A SKHYB coverage 039 separate |
| 031 | POL,PRED session expiry/history | RF::test_class2_never_sells_expires_after_five_sessions_and_replay_cannot_renew; PUB::test_resolved_critical_latch_does_not_survive_only_timed_adverse_evidence. Calendar index quality is C/D check; SES tests DST, not holiday producer. | COVERED session-index consumer; ASM007 calendar risk |
| 032 | POL shadow authority | RF::test_class3_statement_does_not_veto_and_bad_registry_rejects; POLT::test_shadow_and_explicit_bounded_variant; actual published predicate tests in A. | COVERED B |
| 033 | POL,PRED fresh re-entry/critical+timed | RF::test_class1_exits_latches_without_context_and_clears_on_verified_resolution; PS::test_critical_clearance_preserves_unexpired_timed_block; POLT::test_stale_assessment_cannot_clear_reentry. | COVERED B |
| 034 | GAS; PLAN mandatory affordability precedence | BQ::test_b_req_034_opening_200_usdt_without_bnb_needs_bootstrap_and_cannot_spend; RR::test_top_up_own_round_does_not_occupy_stock_slot_or_gross; PS::test_low_gas_above_one_sale_budget_never_starves_mandatory_trim. First BNB needs authorised source before GateB. | COVERED consumer; NOT-OFFLINE bootstrap B-RISK-01 |
| 035 | GAS decimals; ACC resource settlement | RR::test_top_up_requires_actual_quote_then_accounts_actual_bnb_separately / test_real_fill_uses_variable_actual_output_not_estimated_output; SYS integrated real receipt/replay; existing 9bfffcd fix retained. C full native quote producer in unmerged PR #41 not claimed tested here. | COVERED B; C producer pending |
| 036 | PLAN incoming/cash/gas; RuntimePlanner; PostgresStore | PG::test_concurrent_reservations_only_one_wins / test_atomic_rollback_of_every_component; B14 real store/settlement; SET::test_b5_2_buy_fill_releases_usdt_bnb_and_incoming. | COVERED arithmetic/store; C/D production reconciliation remains |
| 037 | ACC; ExecutionBridge/settle | RR::test_duplicate_approval_receipt_cannot_spend_gas_again_with_new_event_id; SET::test_b5_1_sell_broadcast_then_fill; B14 duplicate facts and exact replay; EX finality/reorg tests. | COVERED synthetic final-fact consumer |
| 038 | No chain-balance-only reducer/production hook | #36 proof: ACC accepts only ExecutionObservation/ServiceCostObservation; ContextBuilder checks ledger-vs-projection, not authoritative chain-only changes. C/D agree facts + B validated reducer before startup/periodic new-risk clearance. | MISSING; B-FND-007/C+D+B |
| 039 | POL/PLAN temporal gates; GAS spending cutoff | LT::test_no_buys_before_start_or_after_new_risk_cut; RR::test_top_up_respects_all_spending_and_wallet_barriers; EX::test_expired_or_closed_after_approval_blocks_swap. C #27 encoded deadline acceptance required. | COVERED B; candidate cut values 029 |
| 040 | PLAN terminal obligations; ACC final holdings | LT::test_terminal_survives_absent_policy_and_blocked_rounds_until_final_receipt; B14 revert→retry→flat 14:40; PS::test_signing_stops_with_confirmation_margin_and_expiry_is_bounded; TRIM dust residual. Real closure before 15:00 needs rehearsal and driver. | COVERED consumer; NOT-OFFLINE integrated terminal rehearsal |
| 041 | initial_projection; store run/wallet binding; ACC identity | CON::test_wrong_policy_and_state_ownership_rejected; RR wrong-round/fake receipt rejection; BQ zero-BNB fresh ledger. Team/C verifies actual final wallet balances/nonce/secret; D fresh activation manifest. | NOT-OFFLINE; B-RISK-06 |
| 042 | POL/PLAN consume static regime_gross_weight | BQ stress-budget control validates tighter static budget; no runtime high-volatility/stress producer found. Declared dynamic governor is not satisfied by a static field or a passing clamp. | MISSING; B-FND-008/team+B |
| 043 | DEV20 OPEN; no adopted event-class rule | Team chooses preregistered hold/reduce/flatten classes or records justified declared deviation. No numeric trigger invented. Implementation/test follows adopted ABI/calendar. | MISSING decision; B-RISK-05 |
| 044 | validate_proposal; PLAN independence/rejections | CON invalid/unknown/duplicate/expiry/ownership tests; MECH::test_invalid_and_absent_policy_still_reduce; BR malformed collections; BQ unknown shape contracts. | COVERED B; finite tests are not exhaustive enumeration |
| 045 | pure POL/PLAN/ACC; replay_live | B14 exact head and final-state replay; RES::test_exact_replay_and_policy_failure_fallback_hashes / test_accounting_replay_matches_direct_settlement_and_duplicate_hashes; SYS service replay. Midnight INCIDENT facts are replayed inputs, not a scheduler proof. | COVERED downstream; driver/D hook blocked |
| 046 | research.evaluation absolute+paired gates; records | ABS::test_losing_but_better_is_never_supported / test_profitable_and_better_is_supported; RES invalid-registration checks. H02/EXP001 and actual default economic evaluation NOT RUN; team accepts risk or preregisters real evaluation. | NOT-OFFLINE real edge; B-RISK-04/P2 #37 |
| 047 | strategy.sessions:token_sessions; strategy.features | SES::test_fixed_us_close_utc_dst_and_first_date / test_missing_trade_interval_remains_missing_session / test_short_session_and_bar_crossing_close_cannot_supply_1600_close / test_token_history_is_explicit_optional_and_not_underlying_share_history; REC capture validation. C real timestamp/calendar metadata still required. | COVERED consumer; ASM007 live evidence |
| 048 | PLAN reservations; C Executor/store | MECH pending-intent test; EX::test_guard_change_after_signature_preserves_reservation_and_hash / test_timeout_probe_budget_and_restart_never_release_wallet_barrier / test_wallet_barrier_spans_run_ids_and_changed_parent_cannot_duplicate; PG fences. | COVERED synthetic financial guard; C live proof |
| 049 | PLAN strictest bounds/cap_trims; serial replanning | MECH::test_strictest_reduction_and_no_discretionary_buy / test_rejected_cost_overrun_does_not_rescale_other_requirements; TRIM stable proportional residual; PS critical+timed collision; B14 post-settlement children. | COVERED B |
| 050 | SCH hash; PRO exact decided fractions; D manifests | BQ::test_b_req_050_live_profile_cannot_change_adopted_caps; CON snapshot hashes/ownership; policy never updates profile hash. D final manifest/deviations and unchanged-build rehearsal required. | COVERED B; D release check NOT-OFFLINE |

## B-AMD-01 — code-derived assumptions (2026-10-14)

Frozen requirements above are unchanged. Reasons: phase 2 exposed implementation
defaults requiring source/adoption checks. These are not new permissions.

| ASM | Observed dependency | Status / disposition |
|---|---|---|
| 016 | Internal USDT scale 1e6, native transport 18; integer conversion must be exact, sub-micro cash refused rather than rounded. | VALIDATED internal design by SCH/ports and RR/SYS arithmetic; live transport producer acceptance C before GateB. |
| 017 | Candidate profiles use 6G gas floor, 4G exit reserve, 12G top-up, 15s proposal, 30s quote, 4d features, zero dust and Nov 9/10/11 cuts. | UNVALIDATED as adopted values. Mathematical derivations checked in PRO/LIVE.md; no actual C measurements. Team+B review all at Oct 22, blocking. |
| 018 | Fixed-size 40-USDT measured_roundtrip_bps excludes gas and ranks entries of different actual/rehearsal sizes. | PARTIAL schema/cost-rank tests; #38 all-in rank convention and size-dependent observations still open. Isaac+C+B/team before Oct 22, blocking. |
| 019 | Journaled INCIDENT boundary facts in B14 model a trusted external midnight observation. | VALIDATED test distinction only; not production capability. D owner midnight/replay hook plus driver before integration, blocking. |
| 020 | Candidate same-slippage cap protects buys and mandatory sells. | PARTIAL B validators pass; declared separate exit allowance/cap adoption not documented. Team/C/B approves exit convention before Oct 22, blocking. |
| 021 | Research variance tools' EDT constants describe Sep 5–Oct 7 captures, not a general session calendar; MC coefficients are historical illustrative inputs. | PARTIAL: inspected date comments, gap/terminal/adjacency regressions pass; no fresh real-data rerun. Keith owns dated/hash-bound rerun before reuse; blocking if statistics promoted to live/economic evidence. |
| 022 | Class 1 DISCRETIONARY_EXIT may be upgraded to mandatory independently of cost/minimum/cadence. | UNVALIDATED adoption: DEC35 §10.1 explicitly says DISCRETIONARY_EXIT; published producer/consumer tests show mandatory. Team+A+B must resolve B-CON007 before Oct 22, blocking. |

ASM001–015 keep their frozen evidence/status; tested subsets do not silently
validate whole live assumptions. All PARTIAL/UNVALIDATED items map to the
owner/deadline/blocking deployment-risk text requested in IDEA-049-B.

## B-AMD-02 — source recheck amendments (2026-10-14)

- **B-COR-001:** SKILL Q08 still called the gas logging convention undecided,
  although DEC35 B11 explicitly adopted it. Corrected the summary in this PR
  under common protocol §1.2's shared-SKILL exception. No organiser confirmation
  invented; first-BNB bootstrap Q03 remains unresolved.
- **B-CON007:** DEC35 §10.1 says Class 1 sell `(DISCRETIONARY_EXIT)`, while the
  current published consumer makes it mandatory. The sell requirement 030 is
  unchanged; its priority/gate semantics require a team disposition. Conservative
  action: retain the existing safety path while activation stays blocked, rather
  than silently strengthening the source or changing the policy in review.
  Team wording to resolve: "Should a verified Class 1 finding bypass the minimum
  size, profitability and cadence gates as a mandatory reduction, or retain the
  adopted discretionary exit controls?" This is an internal policy decision,
  not a question for organisers.
- The synthetic 14-day test covers risk/cap/closed/terminal/replay consumers,
  with Class 1/2/3 tested separately. It is not the prompt's complete integrated
 14-day proof of every decided rule; that combined driver/evidence/calendar run
  remains required after D/C/A integration. No done claim is made.

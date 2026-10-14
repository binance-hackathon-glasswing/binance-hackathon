# Section B catalogue — IDEA-049

## B-FRZ-01 — independent freeze (2026-10-14 SGT)

Base `c829fae038a0589085d13552b1123802babbde4c`, branch `review/final-b-20261014`.
Derived before opening B implementation/tests in this task. Earlier conversation
included PR21 editing and quoted prior findings; prior exposure is disclosed,
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
- DEC35: IDEA-035 adopted A8/B2–6/B11/C1–5/C8/§10.1 (SYZ, Oct11).
- DEC37: IDEA-037 §1 and held-name top-up addendum (SYZ, Oct11). The addendum
  supersedes unheld-only top-up; Class2 five-session block supersedes earlier
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
| 010 | When equal-weight allocation is eligible, target four names at20%, total80%. | DEC35 §10.1 “equal weight, four names at20%” | ≤4 settled/pending slots and post-cost capacities at100/200 USDT. | allocation / yes |
| 011 | When selecting names, exclude blocked names and prefer lower measured costs. | DEC35 §10.1 “unresolved red flag ... most expensive” | Deterministic feasible ranking, no fabricated cost/edge evidence. | allocation / yes |
| 012 | When gross≥75%, forbid top-ups; below75%, eligible held gaps and unheld names may top up. | DEC37 §1 “gross<75%”; addendum “held ... also bought” | Exact trigger; all entry gates apply; no incidental sell above target. | allocation / yes |
| 013 | When accepting buys, retain ≤20% name and ≤80% gross ceilings including commitments/costs. | DEC37 buy ceilings | Pending/concurrent intents cannot breach caps or spend reserved funds. | reservations / yes |
| 014 | When only operating caps are exceeded by price drift, do not sell solely for drift. | DEC37 “Never sell because prices moved” | 20–25% name/80–90% gross alone yields KEEP. | caps / yes |
| 015 | When a name exceeds25%, retain mandatory reductions back to20%. | DEC37 “above25% ... back to20%” | Strict boundary; child caps/fills/restarts preserve residual target. | caps / yes |
| 016 | When gross exceeds90%, retain proportional reductions back to80%. | DEC37 “above90% ... proportional ...80%” | Collision/multiple-name reductions do not oversell or rebuy. | caps / yes |
| 017 | When UTC daily loss reaches3%, block new risk for the remainder of that day. | PROP “Daily loss≥3% ... rest of the UTC day” | Inclusive threshold; same-day rebound/restart cannot clear latch. | loss / yes |
| 018 | At UTC rollover, anchor before the first new-day return interval without post-loss reset. | PROP UTC-day convention; AT15 | Consecutive/missed/duplicate midnight and backward clock; preserve run latches. | time / yes+D integration |
| 019 | When drawdown reaches8%, block new risk while permitting valid exits. | PROP “new-risk halt, not a liquidation” | Exact peak-to-low threshold; daily reset cannot clear run-wide latch. | loss / yes |
| 020 | When drawdown reaches12%, retain immediate reductions to gross≤40%. | PROP “automatically reduced to≤40%, using fresh quotes” | No90% hard-line delay; quote failure retains obligation. | loss / yes |
| 021 | Under new-spending HALT with intact authority, preserve independent mandatory risk/terminal planning. | PROP risk exits; AT02 “invalid policy never disables mandatory controls” | Policy errors/HALT cannot suppress valid reductions; integrity failure stays fail-closed. | failure / yes+D integration |
| 022 | When data/model/tool/schema fails, take no new policy risk and record the failure truthfully. | PROP “HOLD, no new risk”; G20/G27 | No timeout-to-BUY; independent valid mandatory controls persist. | failure / yes |
| 023 | For new stock entries, enforce impact≤min(50bp, twice measured median). | DEC35 B4 | Inclusive boundaries; missing per-name measured median refuses entry. | cost / yes |
| 024 | For new entries, enforce total spread/impact/fee/gas cost≤50bp without double counting. | PROP cost; DEC35 B4 “total entry cost ...≤50bp” | Dimensionally correct quote/reference algebra and exact thresholds. | cost / yes |
| 025 | When estimating round-trip costs, include and label an explicit future exit allowance. | PROP “explicit allowance for the cost of exiting later” | Estimated/realized costs distinguished; comparisons include both legs. | cost / yes |
| 026 | For mandatory risk exits, entry profitability/minimum thresholds must not veto reductions. | PROP “Entry-cost thresholds never block ... risk-reducing exit” | Small/high-cost exit eligible under its own slippage/integrity/order cap. | exit / yes |
| 027 | When an order exceeds its amount/slippage cap, refuse or safely split under that cap. | KIT p17 “orders above it are refused”; PROP slippage | Both directions/scales; reduction residual persists through safe child caps. | numeric / yes |
| 028 | When LIVE profile lacks a required value/provenance, refuse startup/planning. | DR09 “every value set and sourced”; DEC35 B6 | Null/malformed/unmeasured profiles refused; proposals not silently adopted. | profile / yes |
| 029 | When setting live parameters, derive from approved measurements/sources, never dev P&L. | DEC35 B6 “never from P&L”; PROP fixed strategy | C DR01 cost summary and team approval required before active profile. | profile / docs/live |
| 030 | On verified Class1 Item4.02, sell held position and block unresolved-latch buys. | DEC35 §6/§10.1 | Critical exit despite Class2 collision; no LLM trade authority. | evidence / yes |
| 031 | On Class2 Item1.05/2.06, block buys/adds for five sessions without forced sale. | DEC35 §10.1 | Session-based holiday/DST expiry, no duplicate-trigger extension. | evidence / yes |
| 032 | On Class3 statements, retain SHADOW without trading effect. | DEC35 B2/§10.1 | Unverified/general/hypothetical statements cannot command trades/blocks. | evidence / yes |
| 033 | On source correction/withdrawal, re-entry may occur only after remaining gates pass. | DEC35 A8 | Clear critical latch without losing independent Class2 block; incomplete newer revision cannot clear. | evidence / yes |
| 034 | Below available BNB reserve, replenish only through authorized USDT→nativeBNB resource intent. | KIT p5; DEC35 C1/B11; DR06 | No magic zero-gas bootstrap; reserve protects exits; BNB is not a stock slot. | gas / yes+live bootstrap |
| 035 | When gas fill settles, account actual cash paid/nativeBNB received/fees/gas using correct scales. | PAGE F44; KIT rawBalance; AT18 | Native-resource fill needs no nonexistent bStock quote; outcomes charged once. | gas / yes |
| 036 | When intents compete, reserve cash/holdings/gas/incoming claims/capacity atomically. | AT04; DEC35 A9 | Real PostgreSQL races/restarts cannot overspend; pending sells cannot fund buys. | reservations / yes |
| 037 | On FINAL success/revert, release matching reservations once; unconfirmed attempts do not change balances. | DEC35 A9; AT04/07/18 | Replay/duplicate idempotence; approval gas; C's finality facts required. | accounting / yes+C/D |
| 038 | On unexplained chain balances, reconcile before new risk without touching unsolicited assets. | PAGE unexplained transfers; PROP “every transaction and balance change”; AT18 | Recorded discrepancy/obligations; no invented fill or external funding. | accounting / yes+C/D |
| 039 | At new-risk cutoff, forbid new positions and reinvestment. | DEC35 C4; DEC37 “no reinvestment” | Exact boundary; gas/stock distinction; post-approval expired buy refused. | terminal / yes |
| 040 | At terminal flatten, retain reductions until factual flatness or explicit block, aiming for Nov11 15:00UTC. | DEC35 C4 “finish flattening by Nov11 15:00UTC” | Failed/reverted/closed/dust paths never fake completion; report lateness. | terminal / yes+rehearsal |
| 041 | On final-wallet activation, initialize truthful fresh balances/risk anchors. | PAGE F14; DR17 | Old run/wallet/nonce/risk state cannot silently initialize final run. | activation / yes+C/D host |
| 042 | Under regime stress, lower the allowed exposure budget and veto new risk as declared. | PROP “regime governor lowers the exposure budget” | Missing series/stress cannot increase permitted exposure; forced-trim distinction explicit. | regime / yes+decision |
| 043 | For scheduled macro/earnings events, use a preregistered class rule or expose the unresolved deviation. | PROP “pre-registered rule per event class”; DEV20 OPEN | No ad-hoc human choice; team disposition required before activation. | event / decision+yes |
| 044 | For malformed/stale/nonfinite/unknown/duplicate policy outputs, independent risk still applies. | AT02/03 | Precision/version/NaN/Inf/negative targets refused without disabling safety. | hostile / yes |
| 045 | On identical recorded-input replay, reproduce policy/latches/plans/accounting deterministically. | PROP rerun; AT01/13/16 | No hidden clock/live I/O; matching hashes; future edits cannot alter past. | replay / yes |
| 046 | In economic/default-policy review, report unrun evaluation and positive after-cost support criterion honestly. | PROP “make no return promise”; DEC35 A5; F50 | Synthetic checks never imply profit; default H02/EXP001 NOT RUN preserved. | economic / docs/live |
| 047 | For candle session inputs, use only completed regular sessions closing16:00ET, correctly in UTC. | DEC35 B3 “closing16:00ET, fixed in UTC” | DST/holiday/short-history/early-close/identity tested; no fabricated or Ondo-extended series. | sessions / yes+real data |
| 048 | While signed attempt is unresolved, reserve the worst authorized financial outcome. | AT04/08/09 | Expiry/index absence cannot free funds; unsupported replacements disabled. | reservations / yes+C |
| 049 | On colliding safety targets, retain all constraints and forbid same-round rebuy. | AT05 | Name/gross/deep/terminal/evidence collisions and child costs conserve ledger. | collision / yes |
| 050 | When changing limits in development, version/explain them and never loosen for losses. | PROP governance; PAGE F60/61; ORG F117 | Policy cannot mutate risk hash; no unapproved/in-run profile switching. | profile / yes+D |

## Use cases — B-UC-001–036

| UC | Trigger/state → expected outcome | REQ |
|---|---|---|
| 001 | 100/200USDT, zeroBNB → no magical spending/bootstrap; factual ledger. | 010,013,034–038 |
| 002 | Four eligible low-cost names, fifth costly/blocked → deterministic ≤4 equal targets. | 001,010–013 |
| 003 | Gross just below/at/above75%, held below/at20% → exact top-up threshold, no sell. | 012–014 |
| 004 | Name at/above25%, gross at/above90% → strict trigger, persistent reductions. | 015–016,049 |
| 005 | Loss just below/at/above3%, then rebounds → same-day halt persists. | 017–019 |
| 006 | Two days, crash/missing/duplicate midnight → trusted anchor before interval, no post-loss reset. | 018,045 |
| 007 | Clock backward/skewed/reboot → no future/expired buy or cleared run latch. | 004,018,039,045 |
| 008 | Drawdown at8%, rebound, at12% → no buys, exits available, immediate deep trim. | 019–022 |
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
| 020 | Class1 exit plus Class2 block → critical sell; independent block survives resolution. | 030–033,049 |
| 021 | Five-session Class2 across weekend/holiday/DST → no forced sale/duplicate extension. | 031,047 |
| 022 | Source correction then incomplete newer revision → no premature re-entry. | 004,030–033 |
| 023 | Class3 hostile/hypothetical statement → SHADOW, no trading/secret/config authority. | 032,044,050 |
| 024 | Small mandatory SELL vs cap/minimum/slippage → safe chunks and explicit residual/dust. | 015–016,026–027,049 |
| 025 | Colliding risk/terminal/cap obligations, failed then good quote → tightest targets retained, no rebuy. | 020,040,049 |
| 026 | Exact start/cut/flatten/end, approve confirms late → no new-risk swap; exit obligation retained. | 039–040,048 |
| 027 | Terminal fill/revert gas crosses loss threshold → final costs included, no fake flatness. | 006,020,037,040 |
| 028 | Fresh final wallet with old run state → truthful initialization/mismatch refusal. | 009,041,050 |
| 029 | Stress lowers budget, missing series/correlated book → preserve decided gates; flag undefined concentration policy. | 010,013,042 |
| 030 | Scheduled event without adopted rule → decision gap, no human override. | 043,050 |
| 031 | Synthetic14days incl.DST/weekend/rollover/loss/outage/terminal → all decided rules/replay hold. | 007,009,017–022,039–045 |
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
Protocol matrix axes: phase001/028/031/035; time005–007/013/021/026/031/033;
dependencies013/015/016/033; data012/014/017/022/023; process006/018/019/031/034;
resources001/013/019/024/033; security023/028/034; audit017/018/031/035.

## Assumptions — B-ASM

Only evidence checked in this review can validate an assumption. Tests to be
performed are prospective; documentary observations do not qualify live behavior.

| ID | Assumption / status and checked evidence | Validation, failure consequence, owner/deadline |
|---|---|---|
| 001 | Internal BNB equity convention equals official scoring; UNVALIDATED, Q03/Q39. | Team confirms official valuation before Oct22. Internal risk convention must be explicit; official score claim blocked. |
| 002 | Tokens trade24/7; PARTIAL team C8, no measured hours here. | C DR01 ≥3days/weekend; openState gates orders regardless; before LIVE profile. |
| 003 | Kit gas amounts/30s expiry remain accurate; PARTIAL, documentary observations only. | C dated quote/gas/expiry artifacts; configurable conservative limits before DR09. |
| 004 | Quote/reference components permit correct spread+impact/fee decomposition; UNVALIDATED live. | B/C dimensional tests and measured executable quotes; refuse missing references/fees; before Oct22. |
| 005 | Declared event planner may be omitted; UNVALIDATED, DEV20 OPEN. | Team decides implemented class rule or justified deviation before Oct22; blocks activation. |
| 006 | LIVE freshness/minimum/slippage/reserve/dates are usable; UNVALIDATED until measured/adopted. | B derives, C supplies DR01, team approves before Oct22; no automatic adoption. |
| 007 | Calendar/source coverage handles all five incl.SKHYB and half-days; PARTIAL. | A/C coverage and B identity/timestamp/short-history tests before DR08/10; conservative missing-data refusal. |
| 008 | Trusted UTC-midnight mark survives outages/restarts; UNVALIDATED integration. | B accounting contract+D merged-driver test before closure; missing boundary blocks new risk. |
| 009 | Chain/receipt facts are authoritative and idempotent; UNVALIDATED live. | C adapter+D durability+B accounting invariants before GateB; no premature financial release. |
| 010 | Proposed final/opening equity is final score; PARTIAL, conflicting F115. | Team Q39 before freeze; retain realized-PnL/full-equity reports, no invented score weights/quota. |
| 011 | Default equal weight has economic edge; UNVALIDATED, no return promise. | Rights-cleared costs/data and preregistered evaluation or explicit team acceptance of unvalidated default before activation. |
| 012 | Same-build autonomous restart is organiser-accepted; PARTIAL team C5 only. | Team Q40; D same-build no-human rehearsal before activation. |
| 013 | Correlated-tech book needs no additional aggregate limit; UNVALIDATED policy. | Team settles GAP10 before Oct22; max-position count alone does not settle concentration. |
| 014 | AT matrix is this review's adopted engineering gate. | VALIDATED by user-invoked common protocol §1.1/§4, not official rules; unsupported deployment capabilities stay disabled. |
| 015 | Turnover/order-count/minimum/clock/reserve numeric defaults are adopted. | UNVALIDATED unless exact decision supplies each value; B decision register before Oct22, never infer from implementation. |

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
- 006: Fixed16:00ET session convention vs half-day data needs explicit behavior;
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
| Never-do1,4 | 001,009,034,050; humans/signing C/D |
| G02,G11,G13 | 001,009,023–029,034,038,046,050 |
| G15 | No adopted numeric depth/turnover manipulation rule inferred; no material misrepresentation/churn quota under008/046; unsupported numeric policy ASM015 |
| G20,G21,G22,G23,G24,G25 | 010–027,039–043; G23 unresolved declared event rule ASM005 |
| G26,G27,G28,G29,G30,G46 | 002–005,009,022,028–029,034,042,047,050; old sizing superseded by decided equal weight; freshness values require adoption |
| PROP Your Proposal selective/abstain/verification/thesis/model/default sentences | 001,004,010–012,022,030–033,044–046; source/model loop A, training omitted under recorded default |
| PROP Control three layers/LLM never sizes or sets limits/write-ahead | 010–029,042–044,049–050; model authority A, signing C, write-ahead D |
| PROP Position actions/sizing/caps/example | 001–002,010–016; 9% worked example is not a limit; sizing deviation needs reason |
| PROP entry bullets1–6 | 023–029,046; probability thresholds replaced by adopted default; depth by B4 |
| PROP exits three triggers and entry-cost bypass/cap | 019–022,026–027,030–033,039–040; model DOWN replaced by adopted class map |
| PROP drawdown four bullets | 017–022,042–043; unresolved event rule retained |
| PROP failure four bullets | 004–005,021–022,034,038,044 |
| PROP governance three bullets | 009,028–029,050; human HALT superseded stricter F114/117 |
| PROP market data/BSC/valuation and fixed-strategy validation sentences | 004–008,028–029,038,045–047; data rights/training A |
| PROP reproducibility policy/risk trace/rerun/reconciliation/nontrade balances | 006,036–038,044–045,048–050; durable release/logs D/signing C |
| Plan Declared values every parameter | Horizon/sizing/cost/caps/loss/depth004,010–029,046–047; evidence budget A; threshold adoption blocked |
| Plan D05,D06,D07,D08,D09,D10,D11,D12 | D05 D hosting; D06/07/08 028–029,046; D09/10 004,047+A/C; D11 030–033; D12 010–020,039–040 |
| DEC35 A8,B4,B5,B6,B11,C1,C8,§5,§10.1,§10.2 | 010–040,046–047; §10.2 synthetic calculations are not adopted policy or profit evidence |
| DEC37 §1/addendum/durable trim requirement | 012–020,024–027,036,049; implementation/results not read before freeze |
| IDEA040 decided parts | Metadata uses DEC35/37; no independent adopted trading value found; build/results deferred phase2 |
| DEV all21 rows | B aspects01–07/13–14/20–21 map009–050; A08–12/19; C16; D15/17/18 and register publication |
| DR06,DR08,DR09,DR10,DR14 | 028–035,039–040,047; firstBNB C/team, live measurement C, policy approval team |
| DR01,DR05,DR13,DR19 split aspects | Cost summary023–029; financial facts037–038; HALT021; replay045; primary C/D |
| Other DR02,03,04,07,11,12,15,16,17,18,20,21,22 | C02–04/17; A11/12; D07/13/15/16/18–22; B041/045 activation/replay interfaces |
| AT01,02,03,04,05,06,12,13,15,16,18 | 004,006,013,017–022,026–027,030–049;06 authorization C,04/05/13 durability D |
| AT07,08,09,10,11,14,17,19,20 | C07–09/17; D10–11/14/20; A19; B financial/mandatory interfaces006,021,036–038,044–048 |
| GAP06,08,09,10,11,12,13,14,15,32,50,51,53,54,64,66 | Corresponding001–050; no whole item assumed complete. D applies verified dispositions only. |

Baseline, trace and code-derived amendments are appended only after this catalogue
is committed and pushed. No section completion or activation claim follows freeze.

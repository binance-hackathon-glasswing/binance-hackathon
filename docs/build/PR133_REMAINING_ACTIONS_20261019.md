# PR133 remaining actions — PC-COORD01 (2026-10-19 UTC)

This plan is based on the reviewed PR133 state at `cc4e715`. It supersedes older
pending-review/release summaries, including the dated remaining-work audit
comment. Owners below identify the existing workstreams; an unassigned operator
is not assumed to have access or to have accepted the handoff. All times are UTC.

Completed: reviews/merges176/177/171/173/179–184; PR126 briefs aligned and included
in PR133; original candidate `c5be269` qualified/published; combined preparation
source `9a0b80e` all four CI jobs PASS (2109 tests/3340 subtests,6 expected skips;
separate systemd5/5). PR126 merged into integration at `eb430b8`; PR133 remains open. Release availability does not establish installation or trading.

Use the [live checklist](PRE_TRADING_CHECKLIST.md),
[coordinator handoff](COORDINATOR_HANDOFF_20261019.md),
[release handoff](releases/idea083-c5be269/README.md), and
[signer preparation](SIGNER_INSTALLATION_PREPARATION.md) for commands and evidence.

## Isaac can start now

Isaac delivered **IQ01 activation-blocker matrix** in
[DEPLOYMENT_BUILD.md](DEPLOYMENT_BUILD.md#iq01-activation-blocker-matrix-2026-10-19);
IQ01-RV01 accepts the repository matrix; GAP-05 is closed. **IQ02 declaration consistency audit** is delivered in
[plan.md §6.5](../skill/larp/plan.md#iq02-declaration-consistency-audit-2026-10-19);
IQ02-RV01 accepts the corrected audit; remaining GAP-02/GAP-62 decisions/evidence are pending. Both use committed
repository inputs without the blocked execution prerequisites. Exact scope, deliverables
and Keegan review requirements are in the [ready queue](PRE_TRADING_CHECKLIST.md#isaac--ready-work-first-pc-isaac-queue01-2026-10-19).
They are preparation slices of GAP-05 and GAP-02/GAP-62; final acceptance remains
with Keegan. Missing external facts are recorded, not prerequisites to finishing
the audit. Blocked execution tasks resume independently when inputs arrive.

## Execution order — PC-ORDER01

Dependencies cannot be removed by changing the task list. This order prevents
assigning work before its inputs exist. It supersedes the earlier implication
that every item under “Start now” or “In parallel” is immediately executable.
Only ready tasks enter a person's queue; a missing input stays with its supplier.
Owner assignments below are requests, not recorded acceptance or access grants.

| Order | Work that becomes ready | Responsible person and required handoff |
|---|---|---|
| 1 — unblock access and inputs | Name the coordinator/operator (A01); obtain source export (B01 supply); provide approved tracing config (B04); verify account rights/funding (A03). These requests can proceed independently. | Account owner coordinates suppliers and a confirmed Binance/Web3/LiquidMesh contact for the complete #139 export. Do not send Isaac another source-acquisition task while he lacks the contact/export. Transfer RPC credentials privately. No new paid account is authorized by this plan. |
| 1 — repository preparation | Database procedure (A04), O2 decision and operations proposals (A06), B4/B5 code (A07). Keith can finish existing capture/provenance/quote-only analysis within A08. | Keegan prepares code/decisions now; Keith reports actual available coverage and missing measurements. Values requiring host/source evidence remain pending. This work need not wait for Isaac. |
| 2 — inspect delivered prerequisites | After A01, actual host/wallet/signing/account/ledger snapshot and timing (A02), pre-funding reconciliation (B06-pre), unsigned exports (C01). After the complete source export, independent source review (B02). | Approved operator supplies fresh sanitized evidence; Keegan supplies attributable source review. Neither requires Isaac to finish route checks or funding first. No circular request for a signed trade as a prerequisite to approving that first trade. |
| 3 — Isaac's first ready tasks, independently | B03 after complete B01+B02 source review and recorded routes; B05 local qualification after B04 private config and a suitable canonical transaction; B07 only after B06-pre confirms eligibility and remaining need; C05 after complete A06 proposals and required A02 measurements. | Give Isaac each complete input packet as soon as it arrives. Do not wait for all four lanes. If no suitable native-credit transaction exists, keep B05 blocked explicitly; an approved B07 transaction may supply it when applicable. B07 can be resolved by reconciliation showing no further seed is needed. |
| 4 — finish measurements and policies | Operator takes B06-post after B07 disposition. Keith completes A08/B08 from the actual profile, B03 fee/source evidence, fresh B06-post holdings and sufficient approve/swap gas evidence; A05 follows A02/A03. Keegan finalizes B10 after B02 and actual A02 timing. | Keith hands Isaac the exact measured #44 policy/coverage packet. Missing receipt gas stays missing; do not assume a fallback estimate or first signed trade establishes pre-signing coverage. Source-qualified estimates/other attributable evidence must meet the existing review standard. |
| 5 — Isaac's policy decisions | B09 after B08 and source-qualified spender/evidence. C05 can complete independently when its own proposal/measurement packet is ready. | Isaac approves or rejects the supplied exact policy hashes; preparation is not approval. No further upstream implementation is assigned to him to manufacture these inputs. |
| 6 — release, then signer session | C06 after B02/B03/B05/B09/B10 and applicable strategy inputs; C07 after that exact qualified release and all required real inputs/approvals. | Keegan delivers the reviewed bundle; approved operator assembles/provisions/isolates it and supplies the approved session plus exact identity/config bindings. Local B05 proof and operator provider acceptance must both be present before signing; operator provider qualification can happen earlier once access/config exist. |
| 7 — key placement and rehearsal | C08 after C07 and all execution gates; C09 after the qualified first logged agent round. | Isaac places the key only in the approved session. The agent generates the approve/swap; the operator completes drills. Hand the evidence back to Keegan for Gate A/B review. |
| 8 — final acceptance | C10 after required Gate A/B, strategy/model, rehearsal and DR evidence; C11 before the final wallet's first agent trade and activation. C12 closes only its actually evidenced items. | Keegan completes the activation pack/signoffs; Isaac handles the authorized final-wallet steps with the approved operator. No date or ordering change waives a gate. |

The strategy/model lane runs alongside this sequence: A06/O2 and A08 → C03;
A02/A03 → A05, and A01/A02 → C01; C01+A05 → C02;
C02+C03+A07 → C04. Each arrow requires the actual output, not just a task being
assigned. Signed adoption and final acceptance wait for the selected lane's
required evidence. C12 billing/administrative preparation can start independently;
actual closure/signoffs wait for their evidence. The fixed trial cutoff remains.

B06 is split into **B06-pre** (eligibility and current funding need) and
**B06-post** (opening capture after B07's funding/no-additional-funding disposition).
The sequence is B06-pre → B07 → B06-post → B08 → B09. This removes the old
B06/B07 circular wording while preserving both checks.

A ready handoff names the accepted owner, exact task ID, input paths/artifact
hashes, measured UTC/validity and required acceptance result. Missing or stale
inputs return the task to its supplier. Isaac can therefore remain idle until a
packet is ready without blocking the independent preparation lanes. This is a
planned order; no supplier delivery, reassignment acceptance or work completion
is inferred.

## Start now: unblock people, inputs and code

| ID | Owner | Required next output | Dependency / completion evidence |
|---|---|---|---|
| A01 | Account owner | Name the successor coordinator and approved AWS operator; have them accept the handoff. Transfer approved access and private Terraform/provider/runtime/profile/terms/SEC-contact files privately. | Record names, scope and handoff acknowledgment. Give this workspace only approved profile names or private local paths; never credentials in GitHub/chat. Yao's former ownership is not reassigned by assumption. |
| A02 | Approved operator, once named | Fresh read-only host/run/build/DB/service snapshot; preserved budget-ledger backup/export, actual spend/UNKNOWN/reservations/latches, unit memory, ACK/anchor/backup/source-gap state, and available queue/signer/finality timing. | After A01. Supply sanitized UTC reports and artifact hashes; distinguish unknown timing from measured bounds. Oct 18 observations are historical. |
| A03 | Account owner | Verify AIand balance units, expiry/funding, actual usage and account-specific rights; reconcile the retained UNKNOWN 84,764 micro-USD through the reviewed process. | Owner evidence/status/export and decision reference. Catalogue authentication and reported 140+ are insufficient. Preserve every charge/reservation/latch; no direct ledger edits/reset. |
| A04 | Keegan | **Repository deliverable DONE:** fresh trial DB procedure selected in [PC-DBPLAN01](NEXT_TRIAL_DATABASE_20261019.md). Operator creation/prepare/bind remains NOT_RUN. | Preserve old DBs and the same ledger/cutoff; verify new name is absent. Version switching is separate future work. |
| A05 | Keith | Review IDEA083 protocol/reporting, measured latency/cost and affordable parallel-review usage; finish provider-rights/financial-policy review with Keegan. | A02/A03 exports; dated review and measured evidence. Prior unsigned protocol approval stands; signed/scored adoption remains separate. |
| A06 | Keegan | **O2 and DEV20 decided 2026-10-19 (Keegan).** O2: RETAIN_DECLARED_TREND_GUARD on inconclusive, accepted before any run (EXP007 PC-O2-ACCEPT-20261019). DEV20: omit the planner as a declared deviation (`decided` 2026-10-19, still DRAFT). Operations proposals D-DN-01/04/06/07/08/11 are delivered in [PC-OPS01](OPERATIONS_DECISIONS_20261019.md). | Keegan's A06 decisions DONE. Remaining: Keith pins EXP007 code/config/snapshot hashes before running; DEV20 final wording/FINAL at C10; Isaac decides the operations proposals; numeric measurements stay open. No illustrative value adopted. |
| A07 | Keegan | PC-S1WIRE01 supplies Class2 evidence production/audit/expiry, frozen close-trigger jobs and recorded-calendar replay; [implementation scope](PR133_REPOSITORY_COMPLETION_20261019.md). PR review pending. | Remaining: verified official-event producer contracts/full issuer coverage, selected inputs/profile and actual S1 acceptance. B6 already merged; no MODEL call or live qualification. |
| A08 | Keith | Finish real quote coverage/summary and fee/gas evidence; review recovered interim provenance (YP-01); prepare the selected measured Oct 20 profile and exact hashes. | Yao's original export is complete: [originals/verifier](evidence/interim-provenance-20261019/README.md), exact516-record snapshot prefixes and summary reproduction. Final capture was interrupted/resumed: demonstrate actual coverage. Supply all raw token scales, full-position/top-up amounts and approve/swap measurements; fallback gas and40-USDT captures do not establish cap coverage. |

## In parallel: source, provider, funding and signing policy

| ID | Owner | Required next output | Dependency / completion evidence |
|---|---|---|---|
| B01 | Account owner coordinates source supplier; Isaac receives ready packet | Obtain complete verified router/facet/helper source, imports/ABI/compiler/settings and chain56 deployed-code/dispatch binding using draft139's request packet through a confirmed team contact. Source delivery must not depend on blocked Isaac acquiring unavailable access. | Original export and hashes. Source access is still missing; do not manufacture an ABI or treat an access error as a verification verdict. |
| B02 | Keegan | Independently review source guarantees, including nested-call wallet debit bounds, minimum receipt and enforced deadlines. | After B01. Attributable review/guarantees and supported economic paths. |
| B03 | Isaac | Build the real pinned router evidence and replay the existing recorded routes in both directions. Resolve attributable route-fee netting (#119), with source/quote/receipt evidence as applicable. | After B02. Reviewed evidence/hash and router-check PASS; reporting fix157 alone does not prove fee inclusion. |
| B04 | Account owner | Supply an approved BSC native-tracing account/config privately, including required prestateTracer diffMode capabilities and canonical/finalized history. | Existing approved service/config and private path; no new signup/spend is inferred. Public balance reads are insufficient. |
| B05 | Isaac | Run merged PR173's real native-proof qualifier and review the sanitized proof; operator then qualifies the same provider on the host. | B04. Exact proof/input/provider hashes and host acceptance; native_trace stays unqualified until then. |
| B06 | Approved operator | Confirm from actual wallet/run/signing state that no first agent trade or in-flight work prevents remaining manual funding. This is B06-pre. Separately, B06-post captures fresh reconciled full holdings/opening state after B07 funding or no-additional-funding disposition. | Actual reconciliation, not nonce equality alone. Retain the final capture/hash and exact matching execution settings. |
| B07 | Isaac | Only after B06-pre's confirmation, finish the remaining MetaMask gas-funding plan if needed; retain public transaction hash, amount and UTC. | Draft172 procedure; operator takes the post-last-funding capture. No seed/key is shared with the assistant. |
| B08 | Keith | Check exact measured profile, full fresh holdings, top-up amounts and approve/swap fee envelope against per-token/per-request caps and aggregate gas budget. | A08, B03 and B06-post inputs. Produce pinned coverage inputs/report; historical prices or nominal headroom are insufficient. |
| B09 | Isaac | Decide/approve exact #44 development/final policies and hashes after the measured review; review the exact summary/profile (#120). | B08 and source-qualified spender/evidence. Pending/example cap labels must not be installed. |
| B10 | Keegan | Adopt and implement #27's finite authority model, duration/margins and per-action windows; preserve original authority through quote refresh/restart and uncertain-send reconciliation. | B02 and A02 timing inputs. Deliver dated C-OPEN-003 decision, reviewed code and expiry/requote/restart tests.60s remains illustrative; kit quote TTL is not verified router expiry. |

Unsigned deployment can proceed when its own profile/account/source/host gates
are accepted; it does not enable execution. Operator uses the exact qualified
candidate, fresh capture/prepare/bind and approved database plan, preserving the
shared ledger and fixed cutoff. Record actual stage timings, charges, restart,
source checks and receiver ACK. Keep the original source-gap FAIL and historical
backup failure. Complete the benign-link/injection-defense qualification on the
exact routed configuration. These are actual host tasks, not new code-review tasks.

## Rehearsal, adoption and final activation

| ID | Owner | Required next output | Dependency / completion evidence |
|---|---|---|---|
| C01 | Approved operator | Export immutable actual unsigned job/source/usage populations and qualified-start identity; maintain spend/headroom, memory, ACK/anchors/backups and source monitoring. Remove the two private-RPC-bearing S3 transfer copies after the approved handoff and resolve earlier trial-DB creation history. | A01/A02; hashed exports and sanitized observed reports. Preserve the fixed cutoff and accounting state. |
| C02 | Keith | Apply the approved population draw/blind rubric, obtain independent labels and M9/route coverage, then produce separate unsigned verdict and signed-rehearsal reports with actual costs/hours. | C01/A05. Fewer than 72 qualified unsigned hours or missing labels/coverage cannot establish SUPPORTED; signed hours and small AI-labelled diagnostics do not fill the gap. |
| C03 | Keith | After O2, run/report EXP-007; finish S1 weights/parameters/candle/trend inputs and O1/O3–O6 proposals; complete live evidence settings, SKHYB protection/deviation, #55/#56/#107 and #37/#38 evaluations. Check T4 behavior and confirm A-T15/#25. | A06/A08 and the existing frozen experiment/weight cutoffs. Exact profile/hash adoption remains required; do not infer a result from a schedule. |
| C04 | Keegan | Confirm the bounded rehearsal/model/strategy choices from the measured reports; confirm S1 values or retain the already conditional measured EQUAL_WEIGHT fallback when S1 remains unqualified. Write T4/rehearsal evidence. | C02/C03/A07. Keep assessor adoption distinct from DETERMINISTIC limiter mode; preserve failed/inconclusive results and record exceptions/deviations explicitly. |
| C05 | Isaac | **Ready now:** review D-DN-01/07/11 risk proposals and D-DN-04 guard requirements in [PC-OPS01](OPERATIONS_DECISIONS_20261019.md). Final numeric/source/caps/host acceptance remains blocked. | A06 proposal packet delivered; A02 still required for measurement-based settings. Record decisions separately; no adoption is inferred. |
| C06 | Keegan | Supply the exact reviewed Gate B release/bundle/manifest with adopted #27 and other required changes; qualify original bytes and required tests. | B02/B03/B05/B09/B10; C03/A07 if S1 is chosen. Publishedc5be269 is the unsigned candidate, not proof of later signed changes. |
| C07 | Approved operator | Run PR184 assembly on real approved pinned inputs, provision/isolate the signer, verify run/build/DB/CA/router/manifest/config bindings, time/IAM/TLS/routes and temporary-access plan. Open the approved signer session. | C06 and policy/source/input approvals. Report exact candidate hashes; assembler success itself keeps installation/signing/Gate B false. No reuse of unsigned identities by assumption. |
| C08 | Isaac | Place the key only in the approved signer session; verify the agent-generated minimum-size approve/swap on chain with acknowledged round logs inside the adopted window. | C07 and all execution gates. People do not select a trade to manufacture acceptance. Operator removes temporary endpoints after the session. |
| C09 | Approved operator | Perform signed crash/reservation/recovery, automatic HALT, anchors, restore and throwaway final-wallet-switch drills; record actual acceptance evidence. | C07/C08 and approved drill procedure. |
| C10 | Keegan | Review Gate A/B item by item, perform deterministic journal replay, keep daily rehearsal/T4 evidence and record any shortened rehearsal deviation. Finalize DEV-18/19/20/22 and all other services/deviations, agentic-system acceptance and activation pack/Gate C. | Host/rehearsal evidence and dated owner decisions; every required DR signoff and final declaration must exist. |
| C11 | Isaac | Confirm final-wallet credential issuance and obtain applicable secret privately; perform final first-gas funding before the final wallet's first agent trade and scheduled activation. | Account/registration confirmation and approved funding procedure; operator installs secrets privately while preserving model keys/ledger and takes the final opening capture. |
| C12 | Keegan | Reconcile #22/#42/#98 with actual evidence, coordinate owner disposition of retained branches and current unanswered organiser questions; collect final DR signoffs. 2026-10-19: states, options and the organiser draft are in [C12 reconciliation](C12_RECONCILIATION_20261019.md); Keegan's dispositions and sending remain. | Org billing remains broken; approved mirror acceptance is separate. No branch deletion, organiser outreach or final activation is performed by writing this plan. |

## Targets and completion protocol

- **Before the Oct 20 change:** accepted coordinator/operator handoff, database
  procedure, profile/fee inputs and exact-release selection; record missing gates.
- **Oct 21 00:00–Oct 22 00:00:** existing conditional first-trade/rehearsal buy
  window. Trading requires all Gate B prerequisites; no date overrides a refusal.
- **Oct 22 00:00:** fixed unsigned trial cutoff. Preserve it and the spending stops.
  Oct 22 remains the parameter/model decision cut; record insufficient evidence.
- **By Oct 26:** final declarations/services, final-wallet credential disposition,
  approved release/config registration, completed DR/agentic-system acceptance
  and activation pack. Final activation follows the existing Oct 27–29 process.

Each owner should update PR133 with: task ID, accepted owner, delivered commit or
artifact hashes, verification result/UTC and remaining blocker. If blocked,
name the exact missing input and its supplier; provide an ETA only when the owner
can support it. A task is checked off only after its output and required review
are recorded. No new host access, spending, policy approval, signer session or
trading authorization is created by this coordination document.

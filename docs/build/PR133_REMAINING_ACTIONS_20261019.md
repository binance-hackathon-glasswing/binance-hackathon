# PR133 remaining actions — PC-COORD01 (2026-10-19 UTC)

This is the current coordination plan for PR133 at cc4e715. It supersedes older
pending-review/release summaries, including the dated remaining-work audit
comment. Owners below identify the existing workstreams; an unassigned operator
is not assumed to have access or to have accepted the handoff. All times are UTC.

Completed: reviews/merges176/177/171/173/179–184; PR126 briefs aligned and included
in PR133; original candidatec5be269 qualified/published; combined preparation
source9a0b80e all4 CI jobs PASS (2109 tests/3340 subtests,6 expected skips;
separate systemd5/5). PR126's separate integration promotion and PR133 itself
remain open. Release availability does not establish installation or trading.

Use the [live checklist](PRE_TRADING_CHECKLIST.md),
[coordinator handoff](COORDINATOR_HANDOFF_20261019.md),
[release handoff](releases/idea083-c5be269/README.md), and
[signer preparation](SIGNER_INSTALLATION_PREPARATION.md) for commands and evidence.

## Start now: unblock people, inputs and code

| ID | Owner | Required next output | Dependency / completion evidence |
|---|---|---|---|
| A01 | Account owner / team | Name the successor coordinator and approved AWS operator; have them accept the handoff. Transfer approved access and private Terraform/provider/runtime/profile/terms/SEC-contact files privately. | Record names, scope and handoff acknowledgment. Give this workspace only approved profile names or private local paths; never credentials in GitHub/chat. Yao's former ownership is not reassigned by assumption. |
| A02 | Approved operator, once named | Fresh read-only host/run/build/DB/service snapshot; preserved budget-ledger backup/export, actual spend/UNKNOWN/reservations/latches, unit memory, ACK/anchor/backup/source-gap state, and available queue/signer/finality timing. | After A01. Supply sanitized UTC reports and artifact hashes; distinguish unknown timing from measured bounds. Oct18 observations are historical. |
| A03 | Account/provider owner | Verify AIand balance units, expiry/funding, actual usage and account-specific rights; reconcile the retained UNKNOWN84,764 micro-USD through the reviewed process. | Owner evidence/status/export and decision reference. Catalogue authentication and reported140+ are insufficient. Preserve every charge/reservation/latch; no direct ledger edits/reset. |
| A04 | Keegan | Record the Oct20 build/database plan: use another trial DB under the current one-run-per-wallet constraint, unless reviewed version-switch support lands first. | Record the selected procedure before the profile/release change. A new DB never authorizes a new empty shared model-budget ledger or trial window. |
| A05 | Keith | Review IDEA083 protocol/reporting, measured latency/cost and affordable parallel-review usage; finish provider-rights/financial-policy review with Keegan. | A02/A03 exports; dated review and measured evidence. Prior unsigned protocol approval stands; signed/scored adoption remains separate. |
| A06 | Keegan | Settle O2 before Keith runs EXP007; record the default and decision rule. Prepare outstanding D-DN01/04/06/07/08/11 proposals and DEV20 planner disposition. | Written decision/proposals, measured gaps and implementation/deviation requirements; no illustrative lifetime or operations value silently adopted. Isaac decides the outstanding operations proposals. |
| A07 | Keegan | Build B4 exposure-evidence production/audit/expiry and B5 session-close/log wiring; document the exact trusted input contract and test recovery/outage behavior. | Reviewed, pushed code and tests. Only verified evidence gains authority. B6 code is already merged; MODEL exposure calls are not selected. S1 use waits for this wiring and its other inputs. |
| A08 | Keith | Finish real quote coverage/summary and fee/gas evidence; recover missing interim provenance; prepare the selected measured Oct20 profile and exact hashes. | Capture was interrupted/resumed: demonstrate actual coverage. Supply all raw token scales, full-position/top-up amounts and approve/swap measurements; fallback gas and40-USDT captures do not establish cap coverage. |

## In parallel: source, provider, funding and signing policy

| ID | Owner | Required next output | Dependency / completion evidence |
|---|---|---|---|
| B01 | Isaac | Obtain complete verified router/facet/helper source, imports/ABI/compiler/settings and chain56 deployed-code/dispatch binding using draft139's request packet through a confirmed team contact. | Original export and hashes. Source access is still missing; do not manufacture an ABI or treat an access error as a verification verdict. |
| B02 | Keegan | Independently review source guarantees, including nested-call wallet debit bounds, minimum receipt and enforced deadlines. | After B01. Attributable review/guarantees and supported economic paths. |
| B03 | Isaac | Build the real pinned router evidence and replay the existing recorded routes in both directions. Resolve attributable route-fee netting (#119), with source/quote/receipt evidence as applicable. | After B02. Reviewed evidence/hash and router-check PASS; reporting fix157 alone does not prove fee inclusion. |
| B04 | Account owner / approved operator | Supply an approved BSC native-tracing account/config privately, including required prestateTracer diffMode capabilities and canonical/finalized history. | Existing approved service/config and private path; no new signup/spend is inferred. Public balance reads are insufficient. |
| B05 | Isaac | Run merged PR173's real native-proof qualifier and review the sanitized proof; operator then qualifies the same provider on the host. | B04. Exact proof/input/provider hashes and host acceptance; native_trace stays unqualified until then. |
| B06 | Approved operator | Confirm from actual wallet/run/signing state that no first agent trade or in-flight work prevents remaining manual funding. After the last funding action, capture fresh reconciled full holdings/opening state. | Actual reconciliation, not nonce equality alone. Retain the final capture/hash and exact matching execution settings. |
| B07 | Isaac | Only after B06's confirmation, finish the remaining MetaMask gas-funding plan if needed; retain public transaction hash, amount and UTC. | Draft172 procedure; operator takes the post-last-funding capture. No seed/key is shared with the assistant. |
| B08 | Keith | Check exact measured profile, full fresh holdings, top-up amounts and approve/swap fee envelope against per-token/per-request caps and aggregate gas budget. | A08, B03 and post-funding B06 inputs. Produce pinned coverage inputs/report; historical prices or nominal headroom are insufficient. |
| B09 | Isaac | Decide/approve exact #44 development/final policies and hashes after the measured review; review the exact summary/profile (#120). | B08 and source-qualified spender/evidence. Pending/example cap labels must not be installed. |
| B10 | Keegan | Adopt and implement #27's finite authority model, duration/margins and per-action windows; preserve original authority through quote refresh/restart and uncertain-send reconciliation. | B02 and A02 timing inputs. Deliver dated C-OPEN003 decision, reviewed code and expiry/requote/restart tests.60s remains illustrative; kit quote TTL is not verified router expiry. |

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
| C02 | Keith | Apply the approved population draw/blind rubric, obtain independent labels and M9/route coverage, then produce separate unsigned verdict and signed-rehearsal reports with actual costs/hours. | C01/A05. Fewer than72 qualified unsigned hours or missing labels/coverage cannot establish SUPPORTED; signed hours and small AI-labelled diagnostics do not fill the gap. |
| C03 | Keith | After O2, run/report EXP007; finish S1 weights/parameters/candle/trend inputs and O1/O3–O6 proposals; complete live evidence settings, SKHYB protection/deviation, #55/#56/#107 and #37/#38 evaluations. Check T4 behavior. | A06/A08 and the existing frozen experiment/weight cutoffs. Exact profile/hash adoption remains required; do not infer a result from a schedule. |
| C04 | Keegan | Confirm the bounded rehearsal/model/strategy choices from the measured reports; confirm S1 values or retain the already conditional measured EQUAL_WEIGHT fallback when S1 remains unqualified. Write T4/rehearsal evidence. | C02/C03/A07. Keep assessor adoption distinct from DETERMINISTIC limiter mode; preserve failed/inconclusive results and record exceptions/deviations explicitly. |
| C05 | Isaac | Decide Keegan's operations proposals, including memory from measured routed-service RSS; review actual source/caps and execution acceptance. | A02/A06 and measured evidence. No new operations policy is adopted by this plan. |
| C06 | Keegan | Supply the exact reviewed Gate B release/bundle/manifest with adopted #27 and other required changes; qualify original bytes and required tests. | B02/B03/B05/B09/B10; C03/A07 if S1 is chosen. Publishedc5be269 is the unsigned candidate, not proof of later signed changes. |
| C07 | Approved operator | Run PR184 assembly on real approved pinned inputs, provision/isolate the signer, verify run/build/DB/CA/router/manifest/config bindings, time/IAM/TLS/routes and temporary-access plan. Open the approved signer session. | C06 and policy/source/input approvals. Report exact candidate hashes; assembler success itself keeps installation/signing/Gate B false. No reuse of unsigned identities by assumption. |
| C08 | Isaac | Place the key only in the approved signer session; verify the agent-generated minimum-size approve/swap on chain with acknowledged round logs inside the adopted window. | C07 and all execution gates. People do not select a trade to manufacture acceptance. Operator removes temporary endpoints after the session. |
| C09 | Approved operator | Perform signed crash/reservation/recovery, automatic HALT, anchors, restore and throwaway final-wallet-switch drills; record actual acceptance evidence. | C07/C08 and approved drill procedure. |
| C10 | Keegan | Review Gate A/B item by item, perform deterministic journal replay, keep daily rehearsal/T4 evidence and record any shortened rehearsal deviation. Finalize DEV18/19/20/22 and all other services/deviations, agentic-system acceptance and activation pack/Gate C. | Host/rehearsal evidence and dated owner decisions; every required DR signoff and final declaration must exist. |
| C11 | Isaac | Confirm final-wallet credential issuance and obtain applicable secret privately; perform final first-gas funding before the final wallet's first agent trade and scheduled activation. | Account/registration confirmation and approved funding procedure; operator installs secrets privately while preserving model keys/ledger and takes the final opening capture. |
| C12 | Keegan | Reconcile #22/#42/#98 with actual evidence, coordinate owner disposition of retained branches and current unanswered organiser questions; collect final DR signoffs. Keith confirms A-T15/#25. | Org billing remains broken; approved mirror acceptance is separate. No branch deletion, organiser outreach or final activation is performed by writing this plan. |

## Targets and completion protocol

- **Before the Oct20 change:** accepted coordinator/operator handoff, database
  procedure, profile/fee inputs and exact-release selection; record missing gates.
- **Oct21 00:00–Oct22 00:00:** existing conditional first-trade/rehearsal buy
  window. Trading requires all Gate B prerequisites; no date overrides a refusal.
- **Oct22 00:00:** fixed unsigned trial cutoff. Preserve it and the spending stops.
  Oct22 remains the parameter/model decision cut; record insufficient evidence.
- **By Oct26:** final declarations/services, final-wallet credential disposition,
  approved release/config registration, completed DR/agentic-system acceptance
  and activation pack. Final activation follows the existing Oct27–29 process.

Each owner should update PR133 with: task ID, accepted owner, delivered commit or
artifact hashes, verification result/UTC and remaining blocker. If blocked,
name the exact missing input and its supplier; provide an ETA only when the owner
can support it. A task is checked off only after its output and required review
are recorded. No new host access, spending, policy approval, signer session or
trading authorization is created by this coordination document.

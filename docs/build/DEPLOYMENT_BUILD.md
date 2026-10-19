# Four-person deployment build brief — IDEA-038

This is the common instruction sheet for prompts 06–09 beside this file. Read it with your own prompt; it is part of that prompt. Its goal: **when the four PRs are integrated, the repository contains everything needed to deploy LARP for the development rehearsal and for final activation** (F-13, F-14). It does not authorize live trading, organiser messages, or merges to `main`.

The previous brief, [PARALLEL_BUILD.md](PARALLEL_BUILD.md) (IDEA-024), built the offline components. Its rules still apply unless this file changes them.

## Where we start (2026-10-11)

- **Base:** `origin/codex/engine-foundation` at the commit that adds this brief. It contains the foundation (IDEA-023), runtime/audit/AWS definitions (IDEA-028), evidence agent and hardening (IDEA-025, IDEA-031), strategy/risk with the decided equal-weight policy (IDEA-026, IDEA-037), execution machine W04/W08 (EXP-005/006) and the runtime adapters `larp/integration/runtime.py` (`ContextBuilder`, `RuntimePlanner`, `StrategyPolicy`).
- **Decided and binding for this build:** IDEA-035 (team decisions 2026-10-11: 80% invested, equal weight 4 × 20%, red-flag classes, flatten by Nov 11 15:00 UTC, automatic restart, hourly anchoring, gas top-up rounds) and IDEA-037 (equal-weight policy, 75% top-up, 25%/90% hard trim lines). Where `main`'s `a21d034` (2026-10-10) differs, IDEA-035/037 govern; Keegan merges `a21d034` and annotates the differences (IDEA-035 A11).
- **Team statements 2026-10-10/11:** the development wallet's `AI_SEEDS_SECRET` is held and the USDT deposit arrived. Whether the wallet holds any BNB is **unknown**; EXP-005 saw none. If it holds none, no transaction can be paid for (Q-03, IDEA-035 §8.1), and only the team may ask the organisers.
- **What is missing:** IDEA-035 §7 lists 16 features still needed before live trading. Every one is assigned below.

## Branches, owners and files

Each owner starts a new branch from the base above, in a separate clone or worktree, and opens one PR into `codex/engine-foundation`. Keegan integrates.

| Owner | Prompt | Branch | Exclusive paths | Reviewer |
|---|---|---|---|---|
| Isaac | [06-execution-live](06-execution-live.prompt.txt) | `codex/deploy-execution` | `larp/execution.py`, new `larp/execution_live/`, `larp/marketdata/`, `larp/signer/`, `tests/test_w04_execution.py`, `tests/test_w08_capabilities.py`, `tests/execution_fixtures.py`, new `tests/execution/`, `tests/marketdata/`, `tests/signer/`, `config/execution/`, `tools/w08_capabilities.py`, `tools/probe_quote.py` | Keegan |
| Keith | [07-strategy-live](07-strategy-live.prompt.txt) | `codex/deploy-strategy` | `larp/strategy/`, `larp/risk/`, `larp/research/`, `config/strategy/`, `tests/strategy/`, `tests/risk/`, `tests/research/`, `tools/realised_vol.py`, `tools/idea018/` | Yao Zhu |
| Yao Zhu | [08-evidence-live](08-evidence-live.prompt.txt) | `codex/deploy-evidence` | `larp/intelligence/`, `larp/sources/`, `larp/integration/contract.py`, `config/intelligence/`, `config/sources/`, `tests/intelligence/`, `tests/sources/`, `tests/redteam/`, `tools/edgar_fetch.py`, `tools/probe_free_sources.py` | Keith |
| Keegan | [09-runtime-deployment](09-runtime-deployment.prompt.txt) | `codex/deploy-runtime` | `larp/runtime/`, `larp/storage/`, `larp/audit/`, `larp/contracts.py`, `larp/ports.py`, `larp/integration/` (except `contract.py`), `migrations/`, `deploy/`, `.github/`, `config/runtime/`, `tests/runtime/`, `tests/storage/`, `tests/audit/`, `tests/integration/`, shared docs (README, LEDGER, INCOMPLETE_WORK, plan.md, SKILL.md), dependency locks | Isaac |

Rules carried over: Keegan alone edits shared docs, locks, the ledger index and the backlog; everyone else records in their own build record and lists requested shared edits there. Build records: **IDEA-039 Isaac, IDEA-040 Keith, IDEA-041 Yao Zhu, IDEA-042 Keegan** (reserved; create the file on first use). Experiment IDs are coordinated through Keegan before any run.

**Scoped review handoff (IDEA-049 / PR #21, 2026-10-14):** for final-review
integration only, section D (Yao Zhu) temporarily applies shared-doc, ledger-index
and backlog edits requested by A/B/C, per
[`final-review/00-common-protocol.md`](final-review/00-common-protocol.md) §0/§6.
This exception is limited to that review; lock stewardship and AGENTS.md hard
rules remain unchanged. Keegan's earlier shared-doc role resumes outside it.

## Frozen interfaces (agreed on day 1, Oct 12)

These are the boundaries where this week's integration broke (RT20 G1–G6). For each one the **consumer's validator is the contract**: the producer's tests must call the consumer's real validator on a real output, not a hand-written copy. A change to any interface needs both owners' agreement, recorded in both build records, before code depends on it.

| ID | Interface | Producer → consumer | Contract (validator that must pass) |
|---|---|---|---|
| **I1** | Live `MarketObservation.v1` with executable `EXACT_IN` quotes (side, `pay_asset`, `pay_units`, `token_units`, `min_receive_units`, `cash_units`, `fee_units`, `gas_bnb_units`, `impact_bps` from `priceImpactPercent`, `slippage_bps`, `route_valid`, times, `quote_id`) | Isaac → Keith's planner via Keegan's `ContextBuilder` market port | `larp.strategy.schema.market_view` and `larp.risk.planner._quote_at_cap`; `MarketRequest.v1` as `larp.risk.planner._request` emits it |
| **I2** | Raw token candles (Web3 `candles`, bar, open/close times, source hash) | Isaac → Keith | Keith's new session builder (B3: one bar per US regular session closing 16:00 ET, fixed in UTC) |
| **I3** | `EXECUTION_REQUEST` command payload | Keegan's `RuntimePlanner` (Keith's intent inside) → Isaac's execution service | Isaac's `Intent.validate` after the mapping Isaac publishes; gas top-up intents included (I7) |
| **I4** | `ExecutionObservation.v1`, each with `run_id`, `wallet_id`, `round_id`, `intent_id`, `event_id`, `tx_hash`. **Two boundaries:** `BROADCAST_ATTEMPTED` updates execution and audit state only (attempt state, the swap's tx-hash mapping to its order and decision); it never changes balances, reservations or gas accounting. Only **final receipt facts**, `APPROVAL`, `FILL` and `REVERT` with `settlement: FINAL` and receipt evidence (block hash, canonical/finality flag), change balances and gas: actual `token_units`/`cash_units`/`fee_units` for fills, `gas_bnb_units` and `gas_value_units` for all three | Isaac → Keegan's settlement reducer (both kinds) and Keith's accounting (final facts only) | Final facts: `larp.risk.accounting.advance_accounting`, which rejects every other kind; broadcast attempts: Keegan's execution-state and audit-mapping tests |
| **I5** | `AssessmentResult.v1` incl. `model_io` (exact request/response records, reasoning summary) and `rationale` | Yao → coordinator, Keith's `consume`, ai-seeds `cot` | `larp.runtime.schema.assessment_result`, `larp.strategy.assessments.consume`, Keegan's round-log builder |
| **I6** | `StrategyProfile.v1` in a new `LIVE` mode, every value with provenance, loaded and hashed by the runtime | Keith → Keegan (config, manifest) | `larp.strategy.schema.profile` (extended by Keith) and Keegan's release preflight |
| **I7** | Gas top-up: a planned USDT→BNB intent when BNB < floor, executed as its own round, logged as `{symbol: "BNB", side: "BUY", amount: <USDT spent>, tx_hash}` with a `cot` saying it is a gas top-up (B11) | Keith plans, Isaac executes, Keegan logs | Keith's planner tests, Isaac's `Intent.validate` (must allow USDT→BNB **only** for this kind), Keegan's `check_orders` (must allow `BNB` **only** for this kind) |
| **I8** | Red-flag predicate records (versioned: item, class, action, block length, fixtures) | Yao → Keith's policy | Keith's policy tests on Yao's real records |

## Deployment-readiness checklist (DR)

**Current cut-line and acceptance audit:** [IQ01 activation-blocker matrix](#iq01-activation-blocker-matrix-2026-10-19)
maps every DR item below to current controls, evidence and missing acceptance.
The Oct11 allocation, defaults and milestones elsewhere in this brief remain
dated history; use [PR133's live owner/dependency plan](PR133_REMAINING_ACTIONS_20261019.md)
for current suppliers and the accepted coordinator/operator. In particular,
first-BNB is answered by F-120, and the source export is supplied through the
account owner rather than assigned to Isaac without access. IQ02 separately
audits other declaration drift; IQ01 does not adopt replacement policies.

Readiness is checked at **three gates**, in order. Each gate needs every DR item marked for it (and for earlier gates) to have evidence: a pushed commit, the test or drill that shows it, and where it is recorded. "Built" without evidence does not count. Items that can only be shown on a deployed host or during the rehearsal are evidenced at the later gate, not demanded before deployment. Items map to IDEA-035 §7 (numbers in brackets).

| Gate | What it allows | Target |
|---|---|---|
| **A · Hosted shadow** | Deploy to the hosted dev environment and run real read-only data, real assessments and official round logs from a manifested build, with **no signing** | Oct 14–16 |
| **B · Signed rehearsal** | Turn the signer on for the dev wallet at minimum size; start the declared 5+ day rehearsal | Oct 20 (rehearsal from Oct 21) |
| **C · Final activation** | Freeze the build, register the final wallet and hand over the activation pack | Oct 26 (activation Oct 27–29) |

| DR | Gate | Item | Owner (reviewer) | Evidence required |
|---|---|---|---|---|
| DR-01 | A (logger running) · B (summary) | Live market port and quote logger running; measured spread/impact data for the five names [§7.2, GAP-44/50] | Isaac (Keegan) | Logger output ≥ 3 days incl. a weekend, hashed outside Git; summary in IDEA-039 |
| DR-02 | B | Live venue adapter: quote-and-swap, approve, gas estimate after approval, broadcast, receipt [§7.1–7.2] | Isaac (Keegan) | Tests against recorded real responses; one approve + swap on the dev wallet from committed code with a logged round |
| DR-03 | B | Isolated signer; refuses to start unless key address = `AI_SEEDS_ADDRESS`; nonce and finality evidence that does not rely on the kit history (which omits approvals) [§7.2, GAP-31/47] | Isaac (Keegan) | Signer tests; documented nonce/finality method with its EXP-005 capability verdicts updated |
| DR-04 | B | Execution service consuming `EXECUTION_REQUEST` commands with fencing, and recovery after a crash at each step [§7.1] | Isaac + Keegan | PostgreSQL crash tests (before sign, after sign, after broadcast, after receipt) |
| DR-05 | B | Settlement reducer: real fills/fees/gas through Keith's accounting; release of USDT, BNB and `INCOMING:` reservations on success, revert and replay [§7.1, A9] | Keegan + Keith | PostgreSQL regression: no reservation row left after either outcome or after replaying the same observation |
| DR-06 | B | First BNB solved and automatic top-ups with a two-transaction BNB floor [§7.3, GAP-49, I7] | Isaac + Keith (+ team for Q-03) | The C1 test result recorded; top-up round logged correctly |
| DR-07 | A | Official ai-seeds round logging: one log per round on every path (incl. hold, failure, gas top-up), stable logical event IDs, **delivery proven only by a durable per-event/chunk acknowledgement** from the receiver (an empty spool or outbox is a health check, not delivery proof: participant-kit.md K14 engineering caveat, IDEA-021 R06), size limits, test rounds marked [§7.4, GAP-46] | Keegan (Isaac) | Every round's event ACKed and the ACK stored durably; a crash after send and before ACK resends the same event ID and bytes; a rejected (4xx) request stays visible as a delivery failure; no "fill without log" |
| DR-08 | B | Entry inputs: token-candle sessions (B3) and price-impact rule (B4) replace `INSUFFICIENT_60_SESSION_HISTORY`/`DECLARED_DEPTH_INPUT_UNAVAILABLE` blockers [§7.5] | Keith (Yao) | Tests on recorded real candles and quotes; first candle dates for GOOGLB/SKHYB recorded |
| DR-09 | B (rehearsal profile) · C (final profile) | Live strategy profile with every value set and sourced (B6/GAP-13: per-trade cap ≥ one 20% position, minimum trade, slippage, freshness, gas floor, dates) [§7.6] | Keith (Yao) | Profile file with provenance per value; startup refuses any unset value |
| DR-10 | B | Red-flag classes live: Class 1 (4.02) sells, Class 2 (1.05/2.06) blocks buys for 5 sessions then expires, Class 3 statements SHADOW [§7.7, B1] | Yao + Keith | Versioned predicate records + verification fixtures; policy tests on them |
| DR-11 | A (deterministic fallback) · C (final choice) | Assessor model connected with budget and fallback (B8), or the deterministic assessor declared as v1.0 [§7.8] | Yao (Keith) | Model bake-off result or fallback decision recorded; cost per round measured; model I/O complete in records |
| DR-12 | A | Live sources on: SEC User-Agent, dated terms captures with hashes, artifact store outside Git, polling cadence [§7.9, GAP-23/24] | Yao (Keegan) | Licence-register rows; a 24 h live ingestion run with no gaps |
| DR-13 | A (restart) · B (HALT drill) | Automatic supervisor restart of the same version and an autonomous HALT, each logged as an incident [§7.10, C5] | Keegan (Isaac) | Kill-and-restart drill on the host; HALT drill |
| DR-14 | B (tests) · C (final dates) | End-of-run schedule: no new risk after the cut, flatten finished by Nov 11 15:00 UTC, no reinvestment in the window [§7.11, C4] | Keith (Keegan) | Clock-driven tests across the window boundaries |
| DR-15 | A (schedule running) · C (criteria 1–6 drill) | Hourly anchoring to write-once storage, verified [§7.12, IDEA-036] | Keegan (Yao) | IDEA-036 criteria 1–6 with results |
| DR-16 | A (provisioned, alerts) · B (restore drill) | Hosting: AWS account/region, database, backups, Object Lock archive, monitoring with real alert destinations, host image [§7.13, architecture-deployment.md 1–7] | Keegan (Isaac) | Applied Terraform plan; restore drill; alarm test reaching a person |
| DR-17 | C | Final-wallet switch: new wallet + new secret, separate `.ai-seeds/` and nonce records, refusal on address mismatch [§7.14, GAP-52] | Keegan + Isaac | Switch rehearsed on the dev host with a throwaway config |
| DR-18 | A (each build) · C (final register) | Version manifest, version event, deviations register and services list [§7.15, GAP-62] | Keegan (all) | Manifest of the rehearsal build; deviations block complete |
| DR-19 | B (replay a shadow day) · C (replay a rehearsal day) | Live replay: recorded-port adapter so live rounds replay exactly [§7.16, GAP-65, A2] | Keegan (Yao) | Replay of a rehearsal day reproduces the head |
| DR-20 | A | Integrated acceptance suite green in CI on the merged branch, incl. the end-to-end path with real component code and fake external services | Keegan (all) | CI run link on the integration commit |
| DR-21 | C | Rehearsal: full pipeline on the hosted dev environment, signer on, ≥ 5 days including the Oct 24–25 weekend, at minimum size (declared; GAP-04) | Team (Keegan runs) | Daily rehearsal log; incidents and their fixes recorded |
| DR-22 | C | Activation pack ready by Oct 26: frozen commit, manifest, final-wallet config with secret slot, runbook, on-call rota (GAP-37) | Keegan (team) | Checklist signed off by each owner in IDEA-042 |

## IQ01 activation-blocker matrix (2026-10-19)

**IQ01 / GAP-05, repository audit at PR133 source2b7ed42. Prepared by Isaac's
delegated assistant; Keegan review outstanding. This matrix is complete as a
repository deliverable; the missing acceptance evidence below is not complete.**

### Gate scope, evidence meaning and the Oct22 cut line

DR-01–DR-22 and the cut line are **team acceptance policy**, not a new list of
organiser rules. Source check: the captured [official page](../official/source_page.md)
(traceability, repository integrity, logging, autonomy and rights), verbatim kit
[trading flow](../official/kit/web3-open-api.md), [logging](../official/kit/logging.md)
and [protocol](../official/kit/PROTOCOL.md); [SKILL.md](../skill/SKILL.md) F-60–F-66,
F-90–F-112, relayed F-114/F-117/F-119–F-124, G-01/G-03/G-04/G-18/G-19 and Q-08/
Q-16/Q-33–Q-40; [participant-kit K13–K15](../skill/reference/participant-kit.md#k13-retry-spool-delivery-check-batch-mode-manual-push).
Later recorded answers, including automatic restart and first gas, are retained.
No new organiser enquiry or external rule verification was performed.

- **IMPLEMENTED** names a code/config control; **OFFLINE-TESTED** means retained
  repository/fixture evidence. Neither means real venue or host qualification.
- **RECORDED-HOST** means a dated observation on the named old build/run, only
  for the behavior actually observed. It does not transfer to a new deployment.
- **MISSING** names absent evidence, adoption or review. **QUALIFIED** may be
  recorded only for the specific build/config, gate, owner review and proof.
  No complete Gate A/B/C qualification is asserted by this audit.
- All rows are mandatory **at their specified gate/phase**, including earlier
  gates still applicable to the selected build. The A-stage portion of a B/C
  row does not demand a future signed transaction before hosted shadow can run.
  Controlled host start and first signing follow their approved prerequisites;
  the resulting observations complete the applicable acceptance afterward.
- At Oct22, remove only optional scope, or use an already permitted alternative
  with its actual adoption, profile and declarations. A required safety, logging,
  verification, reconciliation or recovery failure stops progression at the
  affected gate. A deviation cannot waive organiser restrictions or make a
  disabled/broken integrity control acceptable. A signed-window date never
  overrides a refusal. A shortened rehearsal requires its real disposition and
  evidence; do not mark a future shortfall as already observed.

There is **no automatic all22-DR approval check**. The concrete controls below
refuse their own invalid inputs; remaining gate/drill reviews are manual acceptance
recorded by Keegan and the named owners in [IDEA-042](../ledger/IDEA-042.md).
[`activate_run`](../../larp/runtime/service.py) checks identity, a nonempty reviewer/
reference, registered build and, for live mode, no OPEN/DRAFT deviations; it does
not verify the content of all DR reviews. A reviewer string is not gate evidence.
[`gate_a_check`](../../larp/runtime/gate_a_check.py) is local preparation only;
[`readiness_report`](../../larp/execution_live/gate_b.py) stays BLOCKED with signing
disabled even when some input checks say VALIDATED. [Signer assembly](SIGNER_INSTALLATION_PREPARATION.md)
never grants installation, signing or Gate B acceptance.

### Retained evidence used in this audit

| Ref | Retained proof and precise scope |
|---|---|
| E-CI | [Combined preparation verification](evidence/pr133-continuation-20261019.json), source9a0b80e: recorded all4 approved-mirror jobs PASS,2109 tests/3340 subtests/6 expected skips; separate real-systemd5/5. Source/control links below identify existing tests, not tests newly run by IQ01. No new original bundle is independently downloaded/published in that receipt. |
| E-REL | [Unsigned original release verification](evidence/idea083-release-20261019.json), c5be269: Linux/PG and original bundle/manifest/198 source files/237 checksums/CA verified and published. This is an unsigned candidate, not the later signed release or a deployed signer. Org billing #98 is separate from approved-mirror acceptance. |
| E-HOST | [Oct18 deployment record](evidence/llm-trial-deployment-20261018.json), PC-DEPLOY01/02: old builds86b1476/ea25b52, unsigned shadow, preserved ledger, served model identities/charges and receiver STORED. [Coordinator handoff](COORDINATOR_HANDOFF_20261019.md) and [IDEA-066](../ledger/IDEA-066.md) PC-AWS03–08 retain prior primary setup/routes/IAM/TLS/alarm/restart/anchor results. No fresh host observation or signed acceptance in IQ01. |
| E-SOURCE | [Source/gap and harness audit](HARNESS_READINESS_AUDIT_20261018.md) and IDEA-066 PC-GAP02: original fixed24h report FAIL retained; unsigned historical exceptions do not establish full-source or signed acceptance. Post-fix current-window qualification remains missing. |
| E-QUOTE | [Signed prerequisite evidence](SIGNED_PREREQUISITES_20261018.md), [IDEA-063](../ledger/IDEA-063.md) KMP-QUOTE01 and [fee review](QUOTE_FEE_REVIEW_20261017.md): interrupted/resumed interim captures and 29 checked handoff hashes, not final measured coverage, wallet-net fee proof or adequate measured gas. |
| E-SIGN | [Gate B remaining evidence](GATE_B_REMAINING.md), [IDEA-039](../ledger/IDEA-039.md) GB-RW1, [IDEA-070](../ledger/IDEA-070.md) SR-01 and [signer preparation](SIGNER_INSTALLATION_PREPARATION.md): real-local-PostgreSQL/fixture authority, decoder, reservation, startup and assembly tests; real source/replay, native provider, #27, #44 and signed host acceptance remain missing. |
| E-OPS | [Current action plan](PR133_REMAINING_ACTIONS_20261019.md) PC-ORDER01 and [operations proposal packet](OPERATIONS_DECISIONS_20261019.md): named suppliers/dependencies and proposals only. Former Yao-owned host work needs an accepted successor operator; no reassignment, access, risk acceptance or numeric adoption is inferred. |

### DR controls, evidence and remaining acceptance

Each row is an activation blocker at its indicated phase until its actual proof
and required review are recorded. The owner column in the original table remains
historical allocation; the **missing acceptance** column names current workstreams
and [A/B/C task IDs](PR133_REMAINING_ACTIONS_20261019.md). Operator means an accepted,
approved operator after A01, not assumed AWS access for Isaac or this assistant.

| DR | Gate/phase | Mandatory requirement | Existing guard or manual acceptance check | Evidence state / reference | Exact missing acceptance and current owner |
|---|---|---|---|---|---|
| DR-01 | A logger; B measured summary | Five-name real quote capture, attributable spread/impact/cost coverage | [`cost_summary`](../../larp/marketdata/cost_summary.py) and [`validate_live`](../../larp/strategy/profiles.py) reject insufficient/invalid measured inputs; manual raw-hash, three-day/weekend and gap review | IMPLEMENTED/OFFLINE-TESTED: [summary tests](../../tests/marketdata/test_cost_summary.py), E-CI. Partial real capture E-QUOTE; no final coverage PASS | **MISSING:** Keith A08 recovers provenance, proves actual coverage and delivers selected summary/profile; Isaac B03/B09 resolves fee inclusion #119 and reviews #120. Interrupted capture and fallback gas do not satisfy measurements. |
| DR-02 | B controlled first-round acceptance | Source-qualified quote/approve/requote/gas/broadcast/receipt path and one logged dev approve+swap | [`Executor`/`validate_payload`](../../larp/execution.py), [`PinnedRouterDecoder`](../../larp/execution_live/router.py); manual independent full source/debit/deadline review and recorded-route check, then bounded agent round | IMPLEMENTED/OFFLINE-TESTED: [router tests](../../tests/execution/test_router_review.py), E-SIGN/E-CI. Real route replay NOT_RUN | **MISSING:** account-owner/source supplier B01 export; Keegan B02 guarantees review; Isaac B03 route/fee proof. Keegan B10 adopts/implements #27; Keith/Isaac B08/B09 settle #44. After C06/C07, Isaac/operator C08 retains exact on-chain swap and durable round ACK. |
| DR-03 | B pre-signing and signer-host proof | Isolated wallet key, identity, own caps, source decoder, nonce/canonical-finality qualification | [`validate_config`/`router_decoder`/SignerService](../../larp/signer/service.py), [`load_key_file`](../../larp/signer/keyfile.py), [`SigningPolicy`](../../larp/signer/policy.py), [`ChainEvidence`](../../larp/execution_live/chain.py); manual isolation/IAM/routes/time check | IMPLEMENTED/OFFLINE-TESTED: [startup](../../tests/signer/test_readiness.py), [malicious-intent policy tests](../../tests/signer/test_wr_c_policy.py), E-SIGN. Signer host/key NOT_RUN | **MISSING:** B01–B05 source/provider inputs/proof and B09/B10 policy; release owner C06 exact signed bundle; operator C07 isolation/config/manifest/IAM/time evidence and approved session. Isaac C08 places key only then; balance-RPC success is not native tracing or signer qualification. |
| DR-04 | B execution and crash acceptance | Durable commands, original economic authority, fenced signer/broadcaster and crash reconciliation | [`ExecutionService`](../../larp/execution_live/service.py), [`ExecutionStore`](../../larp/execution_live/store.py), [`ExecutionLoop`](../../larp/execution_live/loop.py), [`validate_sequence`](../../larp/execution.py); manual signed-host crash drills | IMPLEMENTED/OFFLINE-TESTED: [execution bounds](../../tests/integration/test_execution_bounds.py), [crash tests](../../tests/execution/test_postgres_execution.py), E-SIGN/E-CI. #27 integration unresolved | **MISSING:** Keegan B10 finite original lifetime/margins/expiry/restart implementation and operator timing; C06 signed release. Operator/Isaac C08/C09 crashes before/after sign, broadcast and receipt must preserve exact nonce/payload, reservations and audit state. |
| DR-05 | B financial settlement/replay | Final receipt facts alone update balances/gas; release exact resources once; retain unresolved barriers | [`settle`](../../larp/integration/settlement.py), [`advance_accounting`](../../larp/risk/accounting.py), [`ReceiptFacts`](../../larp/execution_live/settlement.py); manual finalized-chain-to-ledger comparison | IMPLEMENTED/OFFLINE-TESTED: [PostgreSQL settlement](../../tests/integration/test_settlement.py), E-SIGN/E-CI; no actual signed success/revert/replay acceptance | **MISSING:** operator/Isaac C08/C09 actual receipt-bound approval/fill/revert/replay and reservation evidence; Keith/Keegan review resource/accounting outcomes. Timeout, absent receipt or deadline expiry alone never establishes NOT_SUBMITTED or releases uncertain state. |
| DR-06 | B funding, floor and top-up acceptance | Reconciled first gas and bounded, exactly accounted native top-up with logged gas round | [`map_command`](../../larp/execution_live/service.py) refuses top-ups without native settlement; [`native proof`](../../larp/execution_live/chain.py), planner/profile floor and [`check_orders`](../../larp/audit/protocol.py); manual funding/C1 review | IMPLEMENTED/OFFLINE-TESTED: [gas round](../../tests/integration/test_gas_top_up_round.py), [native tests](../../tests/execution/test_gate_b_native.py), E-SIGN. Historical funding is not current need/reconciliation | **MISSING:** account owner B04 tracing config, Isaac B05 canonical native proof, operator same-provider acceptance. Operator B06-pre → Isaac B07 funding/no-extra-funding disposition → B06-post opening capture. Keith B08 measured floor/top-up/two-tx fees; later operator/Isaac retain C1/logged agent top-up proof. |
| DR-07 | A every round; B/C signed-log continuity | Durable write-ahead IDs/bytes and per-event/chunk receiver ACK; no unmapped swap, no secret in logs | [`Coordinator`](../../larp/runtime/coordinator.py), [`delivery`](../../larp/audit/delivery.py), [`protocol`](../../larp/audit/protocol.py), [`supervision.Guard`](../../larp/runtime/supervision.py); manual on-chain/order/decision/ACK reconciliation | IMPLEMENTED/OFFLINE-TESTED: [delivery](../../tests/audit/test_delivery.py), [round logging](../../tests/audit/test_round_logging.py), E-CI; RECORDED-HOST E-HOST STORED for old unsigned rounds | **MISSING:** operator A02/C01 actual selected-build ACK/rejection/outage/retry and source/model records; C08/C09 signed swap mapping and crash-after-send-before-ACK proof. Keegan reviews. Empty spool, HTTP200 without positive stored ACK, or a finality timeout never proves delivery. |
| DR-08 | B selected strategy inputs | Real token sessions, metadata/scales and total-cost/impact checks for the selected policy | [`sessions`](../../larp/strategy/sessions.py), [`planner`](../../larp/risk/planner.py), measured profile validation; manual recorded candle/quote coverage review | IMPLEMENTED/OFFLINE-TESTED: [token sessions](../../tests/strategy/test_token_sessions.py), E-CI; input/profile adoption incomplete | **MISSING:** Keith A08/C03 recorded real candles/first dates and adopted cost/impact inputs. If S1 is selected, Keegan A07 B4/B5 trusted producer/session/log wiring and Keith trend/weight/EXP007 inputs are required. Conditional measured EQUAL_WEIGHT needs its own exact adoption/profile; it does not qualify S1. |
| DR-09 | B rehearsal profile; C final profile | Complete sourced LIVE profile, risk/cost/freshness/size/gas/windows, exact hash | [`validate_live`/`build_live_profiles`](../../larp/strategy/profiles.py), [`preflight`](../../larp/runtime/preflight.py), [`gate_a.prepare`](../../larp/runtime/gate_a.py); manual provenance and full-position/holding/fee review | IMPLEMENTED/OFFLINE-TESTED: [profile tests](../../tests/strategy/test_live_profiles.py), E-CI. Interim host profile E-HOST is not final acceptance | **MISSING:** Keith A08/B08 selected measured profile and full holdings/top-up/fee packet; Isaac B09 #120/#44 exact hashes; Keegan C04 strategy and applicable window adoption; operator final manifest/config binding. No proposal/example/default value is adopted by this matrix. |
| DR-10 | B verified red-flag lifecycle | Verified predicates, Class1 sells, Class2 entry blocks/expiry, Class3 shadow, supported held-name falsifiers | [`gate`](../../larp/intelligence/gate.py), [`predicates`](../../larp/strategy/predicates.py), [`consume`](../../larp/strategy/assessments.py), policy/risk precedence; manual real-document/provider qualification | IMPLEMENTED/OFFLINE-TESTED: [published predicate integration](../../tests/integration/test_published_red_flag_policy.py), [class tests](../../tests/strategy/test_red_flag_classes.py), E-CI | **MISSING:** evidence/strategy workstreams Keith/Keegan C03 real live settings, supported SKHYB protection or accepted declaration disposition, independent verifier/evaluation proof and hosted positive/expiry/restart behavior. Synthetic predicates or a tiny AI-labelled diagnostic do not qualify T01/M9. |
| DR-11 | A scoped assessor; C final model choice | Bounded verified assessment, budget/fallback/worker ownership, full provider I/O; no model trade authority | [`EvidenceAssessor`](../../larp/intelligence/agent.py), [`routing`](../../larp/intelligence/routing.py), [`time_budget`](../../larp/intelligence/time_budget.py), [`model_budget`](../../larp/intelligence/model_budget.py); manual account/rights/adoption review | IMPLEMENTED/OFFLINE-TESTED E-CI/E-REL, IDEA083; RECORDED-HOST E-HOST OpenAI served/I/O/settled charges on old60s trial, combined assessment UNAVAILABLE | **MISSING:** account owner A03 account rights/balance/expiry/usage and retained UNKNOWN reconciliation; Keith A05/C02 measured180s parallel cost/latency, actual population/labels/M9 and unsigned verdict; operator current-build full stage/charge/ACK proof; Keegan C04 final signed/scored model adoption. Prior unsigned protocol approval is complete, not a new dependency. |
| DR-12 | A sources/rights; B/C live scope | Authorised point-in-time source/issuer identity, terms hashes, poll coverage and artifact integrity | [`LiveRunner`/`preflight`](../../larp/sources/live.py), [`source rights`](../../larp/sources/rights.py), [`integration contract`](../../larp/integration/contract.py); manual dated rights/24h gap review | IMPLEMENTED/OFFLINE-TESTED E-CI; RECORDED-HOST terms/source startup E-HOST. E-SOURCE original fixed24h **FAIL**, no full qualification | **MISSING:** accepted operator A02/C01 post-fix current-window polls/restart/gap evidence; Keith C03 issuer/live-evidence settings and independent evaluation; Keegan source exception/rights review in applicable scope. Keep historical DOJ failure and BIS distinction; runtime health=true is not source coverage PASS. |
| DR-13 | A automatic restart; B autonomous HALT | Same-build automatic restart, fenced identity and logged HALT/clear without losing reconciliation | [`Sessions`/`Guard`](../../larp/runtime/supervision.py), [`halts`](../../larp/runtime/halts.py), [runtime systemd unit](../../deploy/systemd/larp-runtime.service); manual restart/HALT host drill | IMPLEMENTED/OFFLINE-TESTED: [supervision](../../tests/runtime/test_supervision.py), [HALT split](../../tests/runtime/test_halt_split.py), E-CI systemd. RECORDED-HOST old runtime restart E-HOST | **MISSING:** operator C09 current signed-release restart/HALT/clear with incidents and in-flight reconciliation; Isaac C05/Keegan operations dispositions with required measurements. D-DN-07 crash-loop recommendation is not approval or bounded incident-growth evidence. No manual restart during scored operation is inferred. |
| DR-14 | B boundary tests; C final dates | Adopted no-new-risk/flatten/no-reinvestment boundaries, no stale or extended execution authority | [`execution_bounds`](../../larp/strategy/execution_bounds.py), [`policy`](../../larp/strategy/policy.py), [`RunAuthorization`](../../larp/execution_live/loop.py), signer independent bound checks; manual exact-profile date adoption | IMPLEMENTED/OFFLINE-TESTED: [bounds](../../tests/execution/test_execution_bounds.py), [strategy bounds](../../tests/strategy/test_execution_bounds.py), E-CI. No newly adopted dates here | **MISSING:** Keith C03 #107/final-window decision and exact profile; Keegan B10 #27 finite authority/margins; Isaac/operator C08/C09 actual window/mandatory-exit behavior. Mandatory obligations persist when a quote/integrity guard refuses; a cutoff cannot excuse extending authority. |
| DR-15 | A anchor schedule; C full verification drill | Hourly write-once anchors tied to journal head, retention and stale-restore protection | [`maintenance`](../../larp/runtime/maintenance.py), [`archive`](../../larp/storage/archive.py), [`verify_anchors`](../../larp/runtime/maintenance.py); manual IDEA036 criteria1–6 | IMPLEMENTED/OFFLINE-TESTED: [anchor/role tests](../../tests/runtime/test_anchors_roles.py), E-CI; RECORDED-HOST old hourly ACKs E-HOST | **MISSING:** operator C01/C09 selected-build uninterrupted cadence, actual Object Lock/retention/head verification and stale-restore refusal; Keegan reviews all [IDEA036 criteria](../ledger/IDEA-036.md). Neither an ACK count nor old anchors proves the new run is protected. |
| DR-16 | A provision/alerts; B restore | Actual isolation, IAM/TLS/time/routes, monitored storage/backups, delivered alerts and safe restore | [Infrastructure](../../deploy/aws/hosts.tf), [`database`](../../larp/runtime/database.py), [`backup`](../../larp/storage/backup.py), [`operations`](../../larp/runtime/operations.py); manual applied-plan/route/alarm/restore checks | IMPLEMENTED/OFFLINE-TESTED E-CI Terraform/bundle/systemd. RECORDED-HOST primary migration/IAM/TLS/routes/alerts E-HOST; signer/restore unqualified | **MISSING:** account owner A01 accepted operator/access handoff; operator A02/C07 signer plan/provision/isolation/time/IAM/TLS/routes/SA teardown, C09 empty-target restore/checksum/head/quarantine drills. Isaac C05 numeric memory/watchdog/delivery decisions need real measurements; E-OPS proposals do not establish RTO/RPO or capacity. |
| DR-17 | C final-wallet switch | Fresh registered final wallet, isolated records/nonce namespaces, no old open executions/reservations | [`check_live_start`/`switch_wallet`](../../larp/runtime/live.py), signer key/address check; manual throwaway host switch then real credential/registration check | IMPLEMENTED/OFFLINE-TESTED: [wallet/live-start tests](../../tests/runtime/test_live_start.py), E-CI; real switch rehearsal NOT_RUN | **MISSING:** operator C09 throwaway final-wallet switch; Isaac C11/account owner confirms actual applicable final credential issuance/registration privately; final opening capture after last eligible first-gas funding, exact bound configs and mismatched-wallet refusal. Do not assume the dev secret is the final secret. |
| DR-18 | A each build; C final register | Pushed registered code/config identity, manifest/version event, complete services/deviations | [`verify_release`/`verify_service_config`](../../larp/runtime/preflight.py), [`load_register`](../../larp/runtime/register.py), [`activate_run`](../../larp/runtime/service.py); live mode refuses OPEN/DRAFT rows | IMPLEMENTED/OFFLINE-TESTED: [register tests](../../tests/runtime/test_release_register.py), E-CI. E-REL unsigned original bytes; RECORDED-HOST E-HOST old registered build | **MISSING:** Keegan C06 exact signed release with adopted #27/source/caps and C10 all final declarations including DEV18/19/20/22; operator exact run/config/manifest binding and version evidence. IQ02 declaration audit is separate; a draft decision/reference never finalizes a row. |
| DR-19 | B shadow-day replay; C rehearsal-day replay | Recorded inputs reproduce journal head; financial/nonce/ACK state survives replay | [`replay_live`](../../larp/integration/replay.py), [`replay`](../../larp/runtime/replay.py), storage journal verification; manual actual-day comparison | IMPLEMENTED/OFFLINE-TESTED: [live replay](../../tests/integration/test_live_replay.py), E-CI; real selected-build day/head proof MISSING | **MISSING:** operator C01 exports complete immutable actual inputs/state; Keegan C10 replays the required shadow/rehearsal day with original build/config and compares head. Synthetic exact replay and hand-edited/backfilled records do not satisfy this row. |
| DR-20 | A merged-source CI; B/C release changes | Integrated real components/fake externals plus exact required release/platform checks and review | [Runtime CI](../../.github/workflows/runtime.yml), [`verify_manifest`](../../larp/runtime/release.py), bundle checks; manual exact source/job/artifact/reviewer comparison | **QUALIFIED-CI, scoped only:** E-CI records all4 jobs at9a0b80e; E-REL originalc5be269 acceptance. IQ01 ran no runtime suite/CI and does not transfer PASS to new application bytes | Current tree's application/config/deploy/tests match9a0b80e; later changes are docs. **MISSING for signed/final changes:** Keegan C06/C10 exact future source/release reviews, required Linux/PG/systemd/worker/bundle evidence and original bytes. Org Actions billing #98 still needs truthful separate disposition. |
| DR-21 | C observed rehearsal | Full minimum-size signed pipeline/day logs, including declared5+days/weekend or real reviewed shortfall disposition | Manual [Gate B procedure](GATE_B.md), [rehearsal plan](REHEARSAL_PROFILE_REVIEW_20261018.md), daily records/incidents and model/strategy reports; no single runtime flag certifies duration | IMPLEMENTED components E-CI; RECORDED-HOST unsigned E-HOST is not signed rehearsal or72 qualified unsigned hours. Declared rehearsal evidence MISSING | Team with Keegan C04/C10 and operator C08/C09 supplies actual signed days/weekend, recovery/replay and incidents; Keith C02/C03 separate unsigned/signed reports and adopted strategy. Record a missed requirement when applicable (GAP04); do not manufacture duration, labels, positive performance or a deviation acceptance. |
| DR-22 | C final activation pack | Frozen registered build/final wallet, all applicable reviews, runbook, accepted owners and final DR signoffs | Manual [IDEA042](../ledger/IDEA-042.md) gate-by-gate approval, [runbook](runbook.md), final register/service/identity checks in `activate_run`; accepted [owner handoff](COORDINATOR_HANDOFF_20261019.md) | Repository procedures/unsigned release E-CI/E-REL and E-OPS exist. **MISSING:** complete signed/final acceptance pack and accountable final signoffs | Keegan C10/C12 collects every required DR approval, final deviations/services, agentic-system acceptance and frozen exact manifest/config; account owner A01 resolves accepted operator/team roles; Isaac C11/account owner supplies final-wallet disposition. Dates, this matrix or a nonempty review_ref cannot substitute for the pack. |

### Mandatory controls that cannot be cut

The DR rows include code and manual checks; required manual proof is a blocker
even when there is no automatic guard for it. In particular:

- **Economic action and risk integrity:** DR02–06/08–10/14 retain G-01/G-02/G-18,
  independent signer token/spender/input/fee limits, fresh verified evidence and
  quotes, intended recipient/debit/minimum/deadline, finite original authority,
  current market/risk/health/build/epoch, canonical nonce/finality and confirmed
  balances. A mandatory sale may bypass an entry-only pause, not an integrity
  refusal; unsettled approvals/uncertain sends retain their reconciliation barriers.
- **Version and trace integrity:** DR07/15/18–20 retain G-03/G-04/G-07/G-19,
  write-ahead order/decision/build mapping, exact recorded model/tool I/O,
  stable retry IDs/bytes, positive durable per-chunk ACK, hash-chain verification,
  write-once anchors/backups and replay. Buffering/retries do not authorize missing
  swaps or retrospective log fabrication; required delivery bounds still apply.
- **Verified agentic behavior:** DR10–12/18/22 retain plan §6.2 G-50 bounded tool
  use, G-53 claim verification and G-51 verified thesis/falsifier behavior.
  Existing evidence/assessment code is implemented/offline-tested; actual selected
  provider/rights/trust/label coverage and hosted I/O/falsifier/recovery acceptance
  remain with Keith/Keegan/operator. Failed verification never grants model trade
  authority. A newly chosen assessor or omission requires actual adoption and
  truthful declaration, not relabelling all deterministic operation as agentic proof.
- **Unattended recovery and isolation:** DR03–05/13/15–17/19/22 retain signer-only
  key access, fenced ownership, logged same-build automatic restart, autonomous
  HALT/quarantine and restore integrity. Provenance, role grants, time sync and
  actual recovery/retention/capacity checks cannot be removed as optional polish.
  Current proposals about standby/crash loops/restores do not certify availability
  or permit human intervention during the scored run.

### Optional scope and decisions that are not free cuts

| Scope | Existing permitted disposition | What remains mandatory / who records it |
|---|---|---|
| G-51 post-mortem enrichment | plan §6.2 explicitly makes post-mortems optional | Verified thesis/falsifier checks and audit remain required. Keegan records any actual declaration impact; do not remove evidence verification or open-position safety. |
| More elaborate G-52 planning | plan §6.2 permits a static calendar | The implemented end schedule is not an event-calendar planner. Keegan A06/C10 must implement the accepted minimum or obtain/finalize the actual DEV20 omission disposition; current OPEN/DRAFT is not optionality approval. |
| S1 and its additional limiter/model path | SP-D2 permits a **measured EQUAL_WEIGHT rehearsal fallback** conditionally if S1 remains unqualified | Keith/Keegan adopt the exact rehearsal profile and Isaac reviews caps. A final S1 omission needs its own strategy/deviation decision. Choosing S1 keeps B4/B5/weight/trend/EXP007 requirements; DETERMINISTIC limiter does not select a deterministic assessor or require an extra MODEL call. |
| Additional research/challenger experiments, training or speculative off-hours logic | Omit work not selected for the frozen system; retain NOT_RUN/inconclusive results truthfully | Do not omit required real-document/provider/rights/model evaluation while claiming that model is qualified, or treat an experiment as evidence of profit. Keith/Keegan record selected scope and final declarations. |
| Standby, shortened rehearsal, routing/model changes | **Decision required**, not an already optional feature. E-OPS contains proposals; GAP04 and DEV18/19/22 retain their acceptance requirements | Isaac/Keegan record actual applicable risk/adoption/deviation decisions with evidence. No new standby omission, shortened rehearsal acceptance, model adoption, numeric cap or lifetime is decided by IQ01. |

### Completing IQ01 versus accepting a gate

The matrix supplies the missing mandatory-component/cut-line inventory and all22
DR mappings. Keegan reviews this deliverable before GAP-05 closes. IQ02 remains
separate. Every MISSING row stays open with its named supplier; this does not
prevent finishing the repository audit.

For first signing, follow PC-ORDER01: B01/B02 source → independent B03 route/fee,
B04/B05 provider, B06-pre/B07/B06-post reconciliation/funding, B08/B09 measured
caps and B10 finite authority → C06 exact signed release → C07 operator/session.
Only then can the controlled C08 agent approve/swap supply observed DR02/03/07
proof; C09 completes the required crash/accounting/recovery drills and C10 records
Gate B/rehearsal acceptance. It would be circular to require the first signed
receipt before approving its pre-signing numeric/source/provider safeguards.
Missing receipt gas must instead have the attributable pre-signing evidence
required by B08; a guessed fallback estimate or this sequencing text is no waiver.

Each final acceptance record needs DR ID and phase, accepted owner/reviewer,
exact build/config/profile/policy/evidence hashes, UTC/validity, actual test/drill
result and any remaining blocker. Keegan reconciles the record in IDEA-042 and
PR133. Reuse valid historical scoped proof; require new proof when changed code,
config, provider, wallet or deployment makes it inapplicable. Do not repeat old
host setup merely because this Oct11 brief contains stale instructions.

## Milestones (organiser dates are fixed: development ends Oct 26, activation Oct 27–29, F-13/F-14, F-117)

| Date | Milestone | Who |
|---|---|---|
| Oct 12 | Interfaces I1–I8 agreed; each owner's PR open as a draft | All |
| Oct 13 | Keegan's reconciled baseline on the base branch: PR #9 fixed, PR #10 closed and its execution/settlement parts ported, `main` synced (A11) | Keegan |
| Oct 14 | Hosting inputs decided (B9/D-05); dev environment provisioned; first logged **shadow** round from the host (**Gate A**) | Keegan + team |
| Oct 16 | First integration of all four branches; shadow rehearsal running continuously with real data and logs | All |
| Oct 19–20 | Signing proven on the dev wallet (DR-02/03/04/06); first small trades; **Gate B** review | Isaac + Keegan |
| **Oct 21** | **Signed rehearsal starts** (5+ days incl. the Oct 24–25 weekend) | Team |
| Oct 22 | Cut line: parameters frozen (B6), B7/B8/B9 answered, anything not working is cut and recorded as a deviation | Team |
| Oct 26 | Build freeze, manifest, activation pack (DR-22); **Gate C** review | Keegan + all |

If Oct 20 slips, the signed rehearsal cannot cover 5 days before the freeze; Keegan records the shortfall as a deviation (GAP-04) the same day.

## Rules for every owner

- Read AGENTS.md, SKILL.md (§0 reading rules and never-do list), the LEDGER table, IDEA-035, IDEA-037 and your prompt's listed records first.
- **Commit and push before running** any decision, trade or logging code, and its acceptance criteria. Write criteria in your build record first.
- **Every run with the development wallet's ai-seeds credentials uploads logs auditors see.** Only committed, manifested code may run with them; mark test rounds (never-do #13, F-103). Every transaction needs a decision record and a logged round, including failures (never-do #2, #12).
- Never commit secrets, populated `.env` files or private data. Wallet keys live only on the isolated signer host. Never ask anyone to paste a secret into a chat.
- No history rewriting, no force-push, no self-merge into `main`, no organiser messages. Ask the team for anything that needs a decision you do not own.
- Fake adapters must never reach live mode: live mode refuses to start if any port is a fake.
- Report results as PASS, FAIL, NOT RUN or INCONCLUSIVE with the commit SHA. Synthetic results are not market evidence.

## Integration procedure (Keegan)

1. Each owner's PR must pass CI and its reviewer before integration. Keegan merges them into `codex/deploy-integration` with merge commits (never squash), runs the full suite and the DR-20 acceptance suite, and opens one integration PR into `codex/engine-foundation`.
2. A failure caused by an interface mismatch is fixed by the producer against the consumer's validator, not by loosening the validator.
3. Each gate is reviewed item by item in IDEA-042 before what it allows is turned on: Gate A before the hosted shadow run, Gate B before the signer is enabled, Gate C before activation. The foundation → `main` PR is opened only after Gate C, with team authorization.

## Details the team must provide

| Setting | Who | Needed by |
|---|---|---|
| Whether the dev wallet holds BNB; if not, the team asks the organisers (Q-03) | Team (Isaac checks) | Oct 13 |
| AWS account, region, budget, Object Lock retention (≥ Dec 31 2026), alert recipients (B9, D-05) | Team + Keegan | Oct 14 |
| Model provider, exact model ID, API key and budget, or the deterministic fallback (B8) | Team + Yao Zhu | Oct 19 (bake-off), Oct 22 (final) |
| SEC contact identity for the User-Agent (`LARP_SEC_USER_AGENT`) | Yao Zhu | Oct 13 |
| Wallet key for the signer host (one of `WALLET_PRIVATE_KEY` / `WALLET_MNEMONIC`), `BINANCE_API_KEY`/`BINANCE_SECRET_KEY`, `AI_SEEDS_ADDRESS`/`AI_SEEDS_SECRET` | Team, into the runtime secret store only | Oct 14 (dev), Oct 27 (final) |
| On-call rota for the rehearsal and the scored run (GAP-37) | Team | Oct 20 |

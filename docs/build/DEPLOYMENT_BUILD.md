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

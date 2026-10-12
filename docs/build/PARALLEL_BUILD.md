# Four-person build brief — IDEA-024

This is the common instruction sheet for the four prompts beside this file. Read it with the assigned prompt. It assigns development work, not live trading or strategy promotion. Optimize credible after-cost performance and useful autonomous reasoning; no design can ensure high PnL.

## Starting point and branches

All four branches must start from the SAME kickoff commit containing this brief, on `origin/codex/engine-foundation`. The tested code underneath it is `5a6f4d7`, with evidence in `510dfa3` / IDEA-023. The kickoff commit hash is supplied in the accompanying handoff. Do not start from an older `main`, cherry-pick only the contracts, or independently recreate the foundation.

| Owner | Branch | Exclusive implementation paths | Review partner |
|---|---|---|---|
| Yao Zhu | `codex/evidence-agent` | `larp/intelligence/`, `tests/intelligence/`, `config/intelligence/`, `tools/edgar_fetch.py` | Keith |
| Keith | `codex/strategy-risk-research` | `larp/strategy/`, `larp/risk/`, `larp/research/`, `tests/strategy/`, `tests/risk/`, `tests/research/`, `config/strategy/`, `tools/realised_vol.py`, `tools/idea018/` | Yao Zhu |
| Isaac | `codex/execution-recovery` | `larp/execution/`, `larp/marketdata/`, `tests/execution/`, `tests/marketdata/`, `config/execution/`, `tools/probe_quote.py` | Keegan |
| Keegan | `codex/runtime-audit-platform` | `larp/runtime/`, `larp/storage/`, `larp/audit/`, `larp/contracts.py`, new `larp/ports.py`, `tests/contracts/`, `tests/runtime/`, `tests/storage/`, `tests/audit/`, `tests/integration/`, `config/runtime/`, migrations, deployment and CI files | Isaac |

This deliberately moves the thin coordinator, scheduler and shared-contract stewardship from Yao Zhu's IDEA-021 engine-only allocation to Keegan, so Yao Zhu can build the actual evidence/model path. Keith owns the deterministic policy and risk mechanics; Yao Zhu's models never emit orders. It supersedes only those delivery boundaries, not the engine safety contracts or trading declarations. The previous 14–18-day estimate excludes this additional model work and must not be reused as a new promise.

Each owner can edit their corresponding prompt's progress appendix and their own ledger entry below. Keegan integrates shared README, dependency/lock, ledger-index and backlog edits to avoid four conflicting edits. All owners still read the shared backlog, report completed items with verification evidence, and retain unresolved ones. Keegan removes completed backlog lines in the integrating change, not before evidence exists.

Reserve IDEA-025 (Yao Zhu), IDEA-026 (Keith), IDEA-027 (Isaac), IDEA-028 (Keegan) for build records. They are reserved, not started or adopted. Experimental IDs must be coordinated in the shared index before any run; do not independently allocate the same EXP number on four branches. Module-local dependency requests go into the owner's record; Keegan alone updates the common lock after a fresh install check.

Use separate clones or worktrees, never four agents switching branches in one shared checkout. Git fetch and new ordinary branch creation are fine; no history rewriting. Commit and push all decision/trade/logging code and test criteria before executing it. Preserve private data outside Git. No changes to verbatim kit copies or vendored SDK. These prompts do not authorize messages to organisers, live transactions or automatic main-branch merges.

## Development assumptions

1. Start with Python 3.12, standard-library fixture tests and the existing immutable contracts. The 13 original tests must continue passing. Add `__init__.py` to nested test directories so unittest discovery can recurse. The project environment currently lacks its pinned pytest package; Keegan fixes that and verifies the full environment instead of silently changing pins.
2. Build the low-turnover, declared-volatility-sized baseline plus a bounded evidence-assessment path first. Evidence influence starts in shadow in the DEVELOPMENT profile; this is a reversible engineering assumption, not resolution of D-08/D-11 or the competing live-falsifier recommendations. Production activation requires an explicitly selected, manifested policy and all gates.
3. Preserve declared sizing, max 4 positions / 20% per name / 80% gross and the UTC-day 3%, run-drawdown 8%, deeper 12%→40% ladder. These are team declarations, not claims about organiser-mandated numeric limits. Operating targets should leave room for costs and rounding; do not invent calibrated headroom, slippage, minimum trade or daily budgets. Keep values in validated configuration with provenance and require unset live parameters to fail startup.
4. `KEEP_QUANTITY` is the missing-target default. No entry or re-entry on evidence timeout, no blanket mandatory round trips, no unsupported +6% profit lock, no automatic maximum exposure, and no same-nonce replacement by default. Shorting, leverage, derivatives and external hedging are outside the allowed universe; cash and bounded exposure remain the available controls.
5. Use kit-authorized market sources and EDGAR under existing source decisions. Do not silently reopen held external data or confuse the underlying share with its token. Laya/other training and the IDEA-008 fusion stack remain optional gated experiments, not prerequisites for a working agent. No provider, checkpoint, teacher-output rights or dataset license is assumed approved merely because it is named in an old idea.
6. Default mode is offline. Paper mode has no signing capability. Real read-only adapters are opt-in and need valid source/configuration credentials; real execution additionally requires the integrated readiness gates. Only the isolated signer host receives a wallet key. Never ask anyone to paste secrets into a chat or commit a populated environment file.

## Shared boundaries: develop independently, integrate through ports

Keep IDEA-023's `Document`, `DecisionSnapshot`, `PolicyState`, `Proposal`, `Target` and `validate_proposal` backward compatible. All cross-module payloads are canonical versioned `Document` values; quantities are integers in explicitly named asset units, weights exact fractions, UTC timestamps explicit and money/price scales identified. Every fact records source identity, observation/availability time, content hash and quality state. Missing, stale, zero and unknown are distinct.

The following is the agreed development-port vocabulary. Local fakes may implement these interfaces without importing another owner's unfinished modules. Keegan publishes the shared Protocol definitions and fixture schema in `larp/ports.py` early; additive detail is resolved through adapters, not competing copies of a production store or engine. Until then, test doubles remain owner-local and explicitly temporary. No branch may ship a fake adapter into live mode.

| Port | Input → output | Owner / critical semantics |
|---|---|---|
| `assess(request: Document) -> Document` | `AssessmentRequest.v1` → `AssessmentResult.v1` | Yao Zhu. Request: job/run/issuer IDs, cutoff, evidence references, prior-thesis/context hash, policy-profile hash, allowed tools and budget. Result: same IDs/hashes, model/prompt hashes, claims with supporting spans, novelty/conflicts/missingness, bounded confidence or unknown, falsifier findings, expiry, structured review requests and public rationale. No BUY/SELL fields. |
| `observe(request: Document) -> Document` | `MarketRequest.v1` → `MarketObservation.v1` | Isaac. Token/underlying identities, decimals, both market states, source timestamps; executable quotes additionally bind side, units, size, gas/fees, expiry and route. Acquisition events are immutable; a changing response is a new observation. |
| `decide(snapshot, state) -> Proposal` | Existing snapshot/state → existing proposal | Keith. Deterministic baseline/candidate policy; verified assessment fields may influence a separately enabled research variant. Identity/state/expiry checks are mandatory. |
| `plan(snapshot, proposal_or_none) -> Document` | Existing snapshot plus optional validated proposal → `PlanResult.v1` | Keith. Independent reduction requirements, clamps/rejections, concrete economic intents, resource reservation deltas, proposed state and reason codes. `None` still evaluates mandatory risk. Reservation deltas are requests, never proof of a committed reservation. |
| `advance(state: Document, observation: Document) -> Document` | `ExecutionState.v1` + observation → `ExecutionTransition.v1` | Isaac. Pure step transition emits next state, attempt/intent IDs and required commands; it does not broadcast. A separate command consumer checks durable authorization and fencing at each sign/broadcast boundary. |
| `commit(batch: Document) -> Document` | `CommitBatch.v1` → durable receipt or conflict | Keegan. Run/wallet/chain, event ID/hash, expected state version, owner epoch, new projection, policy state, reservation deltas, execution state, jobs and command/audit outboxes commit atomically. Repeated ID/same bytes is idempotent; different bytes is an integrity failure; stale versions/epochs fail. |
| `deliver(event: Document) -> Document` | Immutable audit ID/bytes/chunks → delivery observation | Keegan. Durable command outbox first; stable retries after lost ACK. Remote failures cannot be confused with local durability health or a successful empty spool. |

Only Keegan's store owns persistent ordering, state versions, resource reservations and owner epochs. Keith owns their economic arithmetic. Isaac returns observed fills/reverts/fees; those are the only inputs that can settle holdings through the common reducer. A proposed order, signature, API response or quote is not a confirmed fill. Yao Zhu owns evidence/job semantics; Keegan owns their durable scheduling and priority. Do not implement four independent portfolios or schedulers.

## Profit and agentic-depth evidence

Use IDEA-014's costs-first approach and IDEA-017's opportunity-driven objective. Compare paired NET portfolio outcomes against the same baseline/exposure constraints after gas, spread, slippage, failed-attempt costs, model/service costs (reported separately from wallet PnL where appropriate), detection delay and missed opportunities. Show uncertainty, drawdown, turnover, coverage and sample counts. A high-volatility book or more trades is not evidence of alpha.

Pre-register every market/model experiment: hypothesis, data rights/hash, chronological split, purging/embargo as needed, fixed thresholds, primary metric, uncertainty method, pass/kill/inconclusive criteria and fallback. Compare baseline, evidence-only, price-only and fusion only where the inputs and budget support the comparison. Use out-of-fold upstream predictions for a trained fusion model. Do not tune from development-wallet or scored-run PnL. Keep NOT RUN, NOT SUPPORTED and INCONCLUSIVE distinct. Do not claim a profitable example proves the strategy.

Agentic depth means the system detects a missing fact, selects an allowed tool, retrieves and verifies evidence, updates an explicitly versioned thesis, schedules reassessment, abstains when uncertain, monitors outcomes and recovers autonomously. Test these behaviors with adversarial and delayed-input fixtures. Respect the declared evidence-loop budget (at most six tool calls and 60 seconds per decision unless a documented declaration change is adopted); record actual model inputs/outputs and concise decision rationales, never fabricate hidden reasoning or five-model consensus.

## Integration and definition of done

First milestone: each owner delivers one runnable offline scenario plus failure cases, exact commands and versioned example input/output documents. Keegan wires a single end-to-end fixture: observed filing and market → assessment → proposal → mandatory risk/planning → atomic commit → fake execution observations → settled accounting → durable audit → crash/restart replay. Iterate this thin path before broad training or live adapters; independent unit tests do not replace integration.

Each owner opens a reviewable branch/PR, lists files changed and unfilled settings, records tests against pushed commits, and provides one successful and one rejected/blocked trace. Reviewers follow the allocation above. Merge compatible contracts first, then owner modules and adapters through reviewed additive changes. Keegan coordinates integration; both state-machine parity and real storage/adapter capabilities need evidence. Attach created PRs to the working chat when supported. Do not self-merge into main without team authorization.

Full activation still requires IDEA-021 AT01–20 as applicable, actual registered-wallet binding, known market/route/finality/logging capabilities, confirmed funding/gas, a selected policy, declared services, release manifest and the submitted five-plus-day rehearsal including a weekend. Quote-only operation and fake fills do not count as that rehearsal. The prompts contain no deadline guarantee.

## Details the team must provide

Existing names are taken from the repo README and verbatim kit; names marked NEW are proposed configuration conventions for this build, not organiser-defined variables.

| Setting / information | Who supplies it; where it is needed |
|---|---|
| `BINANCE_API_KEY`, `BINANCE_SECRET_KEY` | Web3 Developer Portal values, provisioned to approved read/execution hosts. Isaac maps these to the kit aliases `BN_WEB3_API_KEY`, `BN_WEB3_API_SECRET`; reject conflicting values. |
| `AI_SEEDS_ADDRESS` | Organiser-registered development wallet, later separately registered final wallet. Nonsecret but must match configuration and signer address. |
| `AI_SEEDS_SECRET` | Organiser-issued log-upload signing secret; audit service host only. This is NOT an `AI_SEED_KEY` variable and NOT the wallet private key. Leave `AI_SEEDS_URL` unset unless an approved endpoint is supplied. |
| `WALLET_PRIVATE_KEY` OR `WALLET_MNEMONIC` | Exactly one, provisioned only to the isolated signer host. Mnemonic path must be explicitly consistent with registration; kit default `m/44'/60'/0'/0/0`. Never distribute it to all four developers. |
| Model provider, exact model/checkpoint revision, terms and budget | Yao Zhu + team. NEW adapter conventions: `LARP_MODEL_PROVIDER`, `LARP_MODEL_ID`, `LARP_MODEL_API_KEY` for hosted inference or `LARP_MODEL_PATH` for local weights. Map to the selected provider's actual auth; these are not ai-seeds variables. A deterministic stub runs before these are filled. |
| EDGAR contact identity | Yao Zhu supplies a real name/contact for a descriptive User-Agent; NEW `LARP_SEC_USER_AGENT`. No fabricated contact and no secret required for synthetic fixtures. |
| Database, retention and deployment destinations | Keegan. NEW `LARP_DATABASE_URL`, `LARP_ARTIFACT_ROOT`, backup/anchor destination and retention policy; real credentials only in the runtime secret store. Tests use disposable local resources. |
| Registered repository/version procedure, dev/final wallet identity, actual balances and first usable BNB | Keegan + Isaac confirm; expected funding is not a balance observation. Record organiser answers already received before asking anything again. |
| Scored UTC window, valuation/scoring source, per-trade cap, gas/exit reserves, slippage/impact bounds, minimum viable order, freshness/retry limits, final baseline and evidence policy | Named decision owners in GAP-13/39/49–51/64; derive from official answers, declarations and measured costs. Offline fixtures can supply clearly labeled synthetic values; missing live settings must stop activation. |

No one needs a real wallet key, paid LLM credential or another teammate's finished module to begin unit development.

## How earlier ideas are incorporated

| Ideas | Treatment in this build |
|---|---|
| IDEA-001/002 | Licensed, point-in-time source ingestion, relevance screening and provenance; held sources stay held. |
| IDEA-003/004/005 and EXP-004 | Baseline/overlay hypotheses, novelty and paired evaluation; retain the reviews' gate corrections, not the refuted slope-only sufficiency claim. |
| IDEA-006 and EXP-003 | Exposure/regime controls as bounded research/configuration; no unsupported Kelly sizing or automatic exposure increase. |
| IDEA-007/008 | Evidence/severity model is the first model path; time-series/fusion are optional, rights-cleared, out-of-fold experiments with explicit ablations and kill gates. |
| IDEA-009/010/011/012 | Low-turnover baseline, lifecycle, source triggers and terminal planning, subject to later corrections; no vote-to-trade or variance-as-profit shortcut. |
| IDEA-013 | Owners repair source/text/hash, auth/retry, signer-integrity and payload-validation defects before promotion. |
| IDEA-014/015/016 | Measure executable costs, assessment-only evidence, durable ingestion, declared ladder and mandatory-action precedence. |
| IDEA-017/018/019 | Complete lifecycle, cost-aware justified activity, baseline/falsifier candidates and capacity constraints; disagreements stay explicit research/configuration choices. |
| IDEA-020/021 | Use the corrected contracts, atomic durability, independent risk, wallet-wide nonce/finality recovery, stable audit and acceptance cases. Superseded generic clearing/timeouts are excluded. |
| IDEA-022/023 | Fix midnight/gap/spread research defects before reuse; build on the existing tested immutable contracts. |
| EXP-001/002 | Preserve as prospective evidence-overlay and tradable-lag investigations, not proof of returns. |

Sources checked: AGENTS.md; SKILL.md and LEDGER index; relevant IDEA-014/021/022/023, model-track and backlog passages; plan.md declared values; official source_page.md repository/funding/prohibited-actions text; verbatim bstocks-trading-guide.md credentials, eligible tokens, market-state and logging sections. No new market measurement, external research, model training, runtime test or live capability verification is claimed by this brief.

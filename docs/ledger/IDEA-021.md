# IDEA-021 — Engine-only review of IDEA-020: contracts, recovery and verification

- Date / author: 2026-10-10 SGT / SYZ requested; Codex with three independent sub-agents (literature, execution/audit red team, architecture/code red team).
- Status: open — **RECOMMENDED, NOT ADOPTED OR IMPLEMENTED.** This review corrects the IDEA-020 candidate; it does not select a trading policy, change declared limits, or authorize wallet activity.
- U1 — Scope: review the complete available codebase and IDEA-020 for an engine that can support profitable, competitive trading, interchangeable policies, replay/simulation and unattended recovery. Aggressive versus conservative exposure, entry signals, evidence trading rules and policy selection are deliberately deferred.
- Baseline: `7f43a6632f1351fadb1ab2e370c774956e7d2796`; `main` matched freshly fetched `origin/main`. All 10 tracked first-party Python files (1,918 lines), dependency/configuration files and relevant integration sources were read. Two untracked `Claude outputs/` scripts were byte-identical to the tracked IDEA-018 scripts; preserved untouched.
- Method: independent literature and two adversarial reviews, parent source verification and synthesis, then a second adversarial pass over the corrected design. Static review only: no policy experiment, simulation, API probe, signer, model or ai-seeds run. The acceptance matrix below is prospective, **NOT RUN**.
- Related: IDEA-020; G-01..G-19, G-21..G-30, G-43..G-47; GAP-05, GAP-24, GAP-27..38, GAP-45..52, GAP-62..65.
- Labels: **[V]** source/code observation; **[I]** inference; **[R]** proposed engineering requirement; **[OPEN]** unresolved implementation/operational parameter. All R/ENG/AT items remain recommendations until adopted. External systems literature supports mechanisms, not profitability or competition permission.

## 1. Verdict and objective check

**V1 [I] — Keep IDEA-020's direction; do not adopt it unchanged.** A deterministic core, isolated policy, injected adapters, scoped health and autonomous recovery are appropriate. The present proposal is neither policy-neutral nor complete enough to establish safety or liveness. There is no production engine in this checkout to certify. A review can expose errors; only implemented contracts plus evidence can establish readiness.

**V2 [V] — Project specification was checked again.** Read `official/source_page.md` (the Sep 27 capture re-verified Sep 30), `official/kit/bstocks-trading-guide.md`, `logging.md`, `ai-seeds-sdk-README.md`, `PROTOCOL.md`, relevant F/K/Q items including answered-in-practice notes, the submitted proposal answers and all three architecture-PDF pages. The live DoraHacks page was attempted on Oct 10 and returned HTTP 405; no fresh page verification is claimed.

- F-20/F-30 require an autonomous agentic system; F-34/F-47..49 require traceable decisions and complete audit/model artifacts. A reliable execution shell alone is not the completed entry.
- The page's F-43 equity-return formula is explicitly proposed. F-115's relayed organiser answer discusses completed-trade PnL, drawdown, logs and repo together. Exact weights and valuation remain Q-39/Q-04; scored timestamps remain Q-06. Neither the engine nor this review invents a winning-score formula.
- F-44 makes fees and gas economically relevant; F-48 makes integrity essential to retaining a result. Engine quality therefore means preserving valid opportunities, avoiding accidental/duplicate orders and avoidable costs, maintaining accounting, and making decisions auditable. It cannot manufacture trading edge or guarantee a prize.
- F-117/G-46 govern the working freeze assumption: policy replacement is a development/research capability, **not a manual in-run switch**. All autonomous fallback/recovery paths must be inside the registered build. Same-version automatic restart remains the Q-40 working assumption, not a newly settled organiser answer.
- Both market-state endpoints must permit a bStock order, including sells (F-95). The engine must preserve the current declared limits until an explicit pre-freeze change/deviation is recorded (G-11/GAP-62). Moving a number into a profile does not loosen it.

**V3 [R] — Separate three claims.** Architectural adequacy, operational correctness and economic merit require separate evidence. This review addresses the first and specifies tests for the second. Policy merit and the competition outcome remain unestablished.

## 2. Prioritized review findings

Line references below identify the reviewed baseline; append-only notes do not change those lines.

| ID | Priority | Concrete defect or omission | Required correction / acceptance |
|---|---|---|---|
| R01 | P1 | IDEA-020 §3.3–3.5 fixes sigma60, cheapest-first ranking, five-session thesis semantics, permanent filing-item blocks and one rebalance/session inside the engine. Its line 124 disallows policy exits despite §3.2 allowing them. A different compliant signal policy cannot be installed without engine edits. | ENG-01/02: distinguish immutable execution invariants, separately manifested risk commitments and replaceable policy logic/state; preserve current declarations. AT01/02. |
| R02 | P1 | IDEA-020 §3.1 lacks policy state, accepted/rejected/fill feedback, proposal expiry, snapshot identity and target semantics. `frozen=True` does not freeze nested dictionaries/lists; NaN/Infinity/unknown symbols and aggregate target feasibility are unspecified. | Immutable, versioned value objects; finite exact numeric types; pure explicit state transition; full output validation; no hidden state or I/O. AT01/03. |
| R03 | P1 | IDEA-020 §5.3/§8.3 claim other-token sells can continue if a missing nonce cannot clear. A wallet-wide nonce gap prevents higher-nonce transactions from executing. A timeout or absent history row cannot establish that a signed transaction is dead. | ENG-05/06 wallet-level nonce ownership and evidence-based resolution; state what liveness depends on. AT07/08. |
| R04 | P1 | The same-nonce procedure (§5.3, lines 232–241) signs the “next intended action,” treats 1.2× gas as sufficient, and marks the original DEAD on replacement confirmation. Old and new alternatives may have different economics; delayed indexing or reorg can invalidate the conclusion. Approve has no quote deadline. | No generic replacement by a different action. Optional replacement requires bounded authorization, all hash alternatives, canonical outcome/finality evidence and tested API support. Default disabled until proved. AT07–09. |
| R05 | P1 | G-18's one-signature-per-decision wording cannot literally support approve plus swap plus any replacement. IDEA-020 provides no durable identity, reservation or transactional persistence contract (GAP-30/32/34 remain open). | ENG-03/05 define round → decision → intent → step → authorized attempt → hash; idempotent signing per attempt; atomic cash/holdings/gas reservations and one economic action. AT04–09. |
| R06 | P1 | G-19's exactly-one `log()` call does not make crash-safe exactly-one logical logs. SDK `log()` generates a random event ID; crash after server store before local acknowledgement creates a duplicate if called again, or loss if skipped. Empty spool does not prove a particular round arrived. | ENG-07 durable immutable event ID/bytes and acknowledgement outbox; reuse event ID on retry, as PROTOCOL §1 requires. Preserve vendor. AT10/11. |
| R07 | P1 | IDEA-020 §6 allows buys after EDGAR has failed for 24h and §3.3 permits `reassess_timeout_action=allow`. An unseen adverse event can exist precisely because the source is down; elapsed outage time supplies no evidence of safety. | ENG-08 dependency-based invalidation. Timeouts produce explicit unavailable outcomes; no timeout-to-buy conversion. Any independently operable fallback needs its own declared dependencies, state transitions and pre-freeze validation. AT12. |
| R08 | P1 | IDEA-020 line 220 allows sells after an unexplained outgoing transaction if balances reconcile. That proves neither exclusive key control nor that a competing signer has stopped. Local journal/disk failure is missing from its halt table. | ENG-06: unknown signer/nonce ownership or unwriteable durable journal blocks all signing; remote upload outage is a different fault. AT08/11/14. |
| R09 | P1 | A frozen round can authorize an entry before an approve wait but sign the swap after market closure, an adverse event, new-risk deadline or lost ownership. The diagram does not specify checks at the final side-effect boundary. | ENG-04/05: revalidate at every signature and before broadcast against current health/risk/ownership epoch; invalidate stale proposals. AT06/09. |
| R10 | P1 | The proposed Sim path advances by round and creates abstract fills; Paper assumes a current quote fills. Neither exercises approve, re-quote, nonce, timeout, outbox or concurrent-worker races. One-hour traded candles are not executable mid quotes. | ENG-09: exact recorded replay, event-driven fault simulation and approximate market simulation are separate contracts sharing the real core. AT13–17. |
| R11 | P1 | IDEA-020 lacks accounting/valuation definitions, and a common gas floor can prevent the very exits it protects. Mandatory-order splitting, dust, cost remeasurement and infeasible cap repairs are unspecified. | ENG-04/10: atomic-unit ledger, distinct marks/PnL, net-of-cost feasibility, spendable exit reserve and bounded residual plans. AT04/05/18. |
| R12 | P1 | Assessor outputs are keyed only by accession (§2); no input/model/schema identity, knowledge cutoff, stale-result handling or causal link to round I/O. A live/shadow switch does not produce causal counterfactual PnL “for free” (§3.5). | ENG-08/09: immutable assessments keyed by complete context; replay recorded results; shadow outcomes need separate portfolio/execution paths. AT12/13/16. |
| R13 | P1 | Hourly merged rounds lack a durable scheduler, trigger identity, missed-tick policy, priority/service guarantees, queue backpressure and retry budgets. An unbounded “retry hourly” or a restart loop can exhaust gas, quotas or time. | ENG-06/11: durable timers, separate control-plane polling, bounded attempts and periodic recovery probes; explicit no-progress deadlines. AT14/15/19. |
| R14 | P2 | IDEA-020 estimates 6–9 net new person-days by assuming must-have infrastructure and policy-rule savings. No core, tests or deployment exist here; savings are not demonstrated. `BuildHold` is not “always shippable” without its inputs and gates. | ENG-12: build/accept a thin end-to-end engine slice first, then re-estimate from actual delivery. Do not remove the only paper/dry-run path to preserve speculative features. AT20. |

No P0 live incident is asserted: this is a design candidate and research checkout, not a deployed trading system.

## 3. Corrected engine contract

### ENG-01 — Boundaries and minimum architecture [R]

Use one logical wallet controller and one authoritative durable transactional store, with separate capabilities for signing, evidence work and uploads. A modular Python service plus isolated signer is sufficient; this is not a recommendation for a distributed microservice platform. The submitted PostgreSQL and fenced cold-standby design remains the starting commitment; a different storage/deployment choice needs GAP-62, not a silent substitution.

```text
Adapters / timers / assessor completions
                  |
        validated, sequenced events
                  v
   durable inbox -> deterministic state reducer -> immutable decision snapshot
                                                    |
                                  isolated policy + explicit policy state
                                                    |
                          independent risk constraints / required reductions
                                                    |
                       order planner -> fresh quote & feasibility validation
                                                    |
              atomic intent + reservation + audit state + command outbox
                                                    |
                           fenced signer -> Web3 broadcaster -> reconciler
                                                    |
                     observed outcome events feed the same reducer

   immutable round outbox -> ai-seeds delivery worker -> durable acknowledgements
```

The deterministic reducer, policy invocation contract, guards, planner, transaction state machines, accounting and audit serialization are shared in live and test modes. Only the external ports change. Workers cannot mutate portfolio/policy state outside the ordered event path. A network call never runs while holding the database transaction that owns wallet state.

| Boundary | Owns | Cannot be bypassed by a policy |
|---|---|---|
| Competition/execution invariants | Registered wallet/version; allowed assets/calls; local signing; durable decisions; trace completeness; no leverage; exclusive nonce ownership; integer amounts; fresh required market states | Always enforced, including emergency exits |
| Manifested risk profile | Currently declared caps/cash floor/loss controls, sizing obligations, cost and slippage limits, budgets and terminal restrictions | Enforced independently of the policy; values remain declared until changed through governance |
| Replaceable policy profile | Ranking, forecasts, target construction, economic entry/exit/re-entry, thesis/block meaning, review cadence and any selected evidence overlay | Cannot relax either layer above; any declared behavior remains a profile constraint |
| Operational machinery | Jobs, deadlines, retry/fault state, reservations, execution settlement, logging, checkpoints | Never interprets a missing input as favorable market evidence |

The engine enforces a declared one-rebalance/session limit if adopted; it does not make that number an architectural constant. The same distinction applies to sigma60, permanent evidence blocks and evidence-exit switches. Regime logic and loss-control values live in the versioned risk profile; the core enforces their outputs, not a chosen aggressive/conservative stance.

### ENG-02 — Policy ABI and explicit state [R]

Conceptual interface (not executable implementation):

```text
PolicySpec = identity + code_hash + schema_version + parameter_hash
           + required_feature_ids + required_assessment_ids + state_schema
decide(DecisionSnapshot, PolicyState) -> Proposal
Proposal = snapshot_id + policy_id + valid_until + targets + reasons
         + next_policy_state + bounded_review_requests
```

- `DecisionSnapshot` carries wallet/run/version IDs, event sequence, observation cutoff, UTC/session/calendar IDs, settled and reserved balances, pending actions, valuation provenance, verified feature/assessment references and health, risk latches, last outcomes and current policy state version. Every nested value is immutable/canonicalized; the policy gets no credential, network client, mutable global, wall-clock handle or signer.
- Target instructions are explicit `KEEP_QUANTITY`, `TARGET_WEIGHT` or `EXIT`, using decimal/rational weights and integer token units after planning. Missing symbol means `KEEP_QUANTITY`, never an accidental flatten or rebalance. Reject duplicate/unknown symbols, NaN/Infinity, negative weights and out-of-range totals before planning. An invalid/slow policy causes a recorded no-policy-action result; mandatory valid risk controls can still operate.
- State belongs to `(run_id, policy_id, state_schema)`. Persist `next_policy_state` in the same transaction as the proposal result; future fill/reject/abort events are separate inputs. A proposed order is not a fill and must not increment holdings, clear a block, consume a completed-trade counter or mark an exit complete.
- Give decisions/attempts separate counters. Define whether a selected profile's activity budget counts intent, broadcast, fill or economic turnover. Retries cannot reset or multiply a budget silently.
- Policies may deterministically request bounded assessment/review jobs, not invoke tools themselves. The scheduler enforces supported job types, resource limits, deduplication and priority. Evidence workers remain outside the synchronous trading critical path and cannot emit trade commands.
- Isolate policy execution with a time/memory budget so a hang cannot stop the reconciler, safety checks or uploader. Record duration/outcome. Purity is a contract with conformance tests and capability isolation, not a guarantee supplied by Python type hints.
- Development policy replacement requires a new manifested identity, resolved/inherited pending ownership and explicit state initialization/migration. Never reuse stale targets from the old policy. During the scored run, no manual change of code, parameters, enabled policy or capability set.

### ENG-03 — Durable facts, state and side effects [R]

An ACID transaction commits each accepted event, monotonic sequence, canonical bytes/hash, projection/state version, proposal result, resource reservations and resulting command/outbox rows. Commit uses the expected state version; stale worker/proposal completions must be revalidated instead of overwriting newer state. Unique keys reject repeated immutable events/commands. Bind mutating-command idempotency keys and immutable event IDs to payload hashes; the same such ID with different content is an integrity error. Polling responses and source revisions instead get distinct observation/attempt IDs linked to their request/source: pending→success is a valid new observation, not payload tampering. Required raw input blobs must be durably stored and hash-verified before any action depends on them.

Commit precedes an external side effect. On restart reconstruct from a verified checkpoint plus journal tail; latches, balances, pending hashes, reserved gas/cash, policy state, timers and upload backlog survive. Record crashes and incomplete rounds truthfully; never rewrite the original event time or fabricate missing model output. Exact downstream replay compares canonical state/proposal/intent hashes; environment-specific delivery acknowledgements remain recorded external events.

Backups are not authority to rewind a wallet. A restored state older than signed transactions is quarantined for full reconciliation; unavailable evidence prevents signing. Hash chains expose alteration relative to an anchored head but do not recover missing data by themselves. Preserve hourly anchoring and retention commitments until an explicit deviation is adopted.

### ENG-04 — Planning, reservations and fresh authorization [R]

The first snapshot contains indicative market/feature data; a policy does not need to predict its exact quote size before it chooses a target. Resolve policy targets against risk constraints, derive concrete amounts, request size-specific quotes, then run a bounded feasibility pass. If any essential inputs changed, invalidate or re-plan; never iterate quotes/targets without a budget.

Compute **all** independent reduction constraints, even when trading is temporarily blocked. Combine compatible upper bounds deterministically, record all triggering reasons and retain a pending requirement. A priority list is not permission to ignore a stricter simultaneous constraint. Integrity/market failures gate execution, not observation of a new risk breach. Entry-profitability, discretionary cadence and discretionary minimum-size rules cannot veto mandatory reductions; recipient/allowlist, current market state, exit slippage, actual holdings, per-transaction limits and affordability always apply.

Reserve cash, token quantities, BNB gas and portfolio capacity atomically for pending actions. Use worst-case outstanding buys for exposure/position counts; subtract pending sells from available holdings; do not fund new buys from unconfirmed sell proceeds. Recheck post-cost cash and exposure constraints as each transaction settles. Market moves may breach a cap despite correct control; record a repair obligation rather than falsely promise continuous cap compliance.

An exit exceeding the per-trade cap is a bounded parent plan with sequential child intents; remeasure residual holdings and costs after each confirmed fill. Tiny residuals receive a dust/unexecutable status with amount and reason, never an endless retry or a fabricated zero balance. Where gas/slippage/caps make all actions infeasible, retain an explicit blocked requirement.

### ENG-05 — Execution and identity state machines [R]

Use the hierarchy `run → round → decision → economic_intent → tx_step(approve/swap) → authorized_attempt → tx_hash`. Wallet and chain are part of every uniqueness key. One round can contain multiple decisions/intents; one intent can require both steps. One economic intent must not execute twice. A signer may reproduce the same stored signature for the same immutable authorized attempt; it must reject the same attempt ID with different bytes. This refines G-18's ambiguous per-decision signing language; it does not authorize blind re-signing.

Step states: `PREPARED → AUTHORIZED → SIGNED_DURABLE → BROADCAST_ATTEMPTED → PENDING/UNKNOWN → INCLUDED_SUCCESS/INCLUDED_REVERT → FINAL_SUCCESS/FINAL_REVERT`; additional explicit states cover pre-sign abort, superseded alternatives and unresolved ownership. `BROADCAST_ATTEMPTED` is durable before the request; a crash at that boundary is treated as possibly sent. Persist the locally calculated hash and signed bytes securely before transmission, with a hash-bound authorization, nonce, gas budget and owner epoch. Signed bytes are executable capabilities; keep them out of general logs.

Validation is action-specific. An approve must encode the permitted pay-token contract, exact amount, permitted spender, zero value, chain/wallet/nonce and gas bounds; it has no swap minimum-output or quote-deadline field. A bStock swap must match the approved token pair/amount, recipient, router/selector, value, encoded minimum receive and deadline, chain/wallet/nonce and gas ceilings. A permitted USDT→BNB gas top-up has its own gas-purpose budget and route checks, with the native-asset convention from F-93; it does not require a nonexistent BNB underlying-stock market status. Do not trust a convenience JSON `minReceiveAmount` without checking the encoded swap. If the router ABI/route cannot be validated, refuse that route. Failed gas estimation does not silently use the kit's known-insufficient 450000 fallback.

At **each** sign and broadcast boundary recheck ownership/fencing, durable audit availability, current required health and risk authorization, plus action-specific terminal, market and expiry conditions. The parent bStock action requires both market states before spending approval gas and again before its swap; a gas top-up uses its separately defined infrastructure conditions. Waiting for approve may invalidate an entry. A signature already emitted cannot be revoked by a later gate; record and reconcile that exposure instead of claiming prevention. Swaps follow approve-success → fresh re-quote → gas estimate → validate → sign/broadcast. Observe and account actual fills and gas; quote amounts are estimates.

Define the local authorization point: a durable compare-and-set against current state/risk/ownership versions atomically accepts each side-effect authorization. All relevant observations sequenced before that point must affect the decision; later observations trigger invalidation of unused authorizations where possible, reconciliation of emitted capabilities and subsequent controls. Freshness bounds limit observation age; the engine cannot know an external change before observing it. Do not hold the database transaction across signing/network I/O; the fenced signer/broadcaster checks the accepted authorization and current epoch at its own release boundary.

### ENG-06 — Autonomous recovery and honest liveness [R]

Track token-level conflicts **and** the wallet-wide nonce pipeline. For this small universe, one unresolved outgoing step at a time is a reasonable implementation simplification; this is an operational choice, not a trading frequency limit. Neither `highest local nonce + 1` nor a missing history row is sufficient evidence to advance after a crash.

Recovery first inspects all stored attempt hashes, transaction details/history, balances and the adapter's verified canonicality/finality evidence. The kit lacks a nonce endpoint and omits approves from history; prove how the permitted read adapters establish nonce consumption and finality. If they cannot, mark that capability unsupported and block affected progression. A new read-only chain service must be registered and manifested; transaction submission stays on the Web3 API. Do not assume RPC access is already available.

**No generic same-nonce clear is adopted.** An optional replacement facility is disabled until protocol behavior and invariant tests pass. If enabled before freeze, it preserves the same approved economic intent and step, obtains a fresh bounded authorization, retains every alternative hash and reservation, respects current guards and a total gas/attempt budget, and resolves the winning canonical outcome before later action. Re-quoting changes bytes and therefore requires revalidation. Do not replace an uncertain approve with a swap; do not send unrelated transfers/cancellations. An old swap may have succeeded before expiry but become visible later. Expiry, mempool absence, a fixed gas multiplier or one confirmation is not proof of impossibility. Approve expiry cannot be inferred from a swap quote.

Every blocked condition has `scope, cause, first_seen, last_progress, next_probe, retry_budget, clear_predicate, deadline, escalation, incident_id`. Clear only on positive evidence; retain active symptoms and latch history. Suggested taxonomy:

| Condition | Signing behavior | Autonomous clear / terminal behavior |
|---|---|---|
| Transient quote/market-data/API fault | Block affected dependency/action; preserve unrelated work only if its prerequisites are valid | Bounded backoff with jitter and health probes; require fresh validated observations, not one arbitrary successful API call |
| Unresolved outgoing transaction or nonce gap | No conflicting action or higher-nonce execution promise; keep reservations | Proven canonical outcome or tested authorized replacement; otherwise explicit persistent UNRESOLVED |
| Unknown outgoing transaction, unexplained nonce, split-brain or suspected key compromise | All signing blocked | Resume only after exclusive ownership and complete state are provable under a pre-registered recovery path; otherwise latched-all for the run |
| Local journal/storage corrupt, full or unwriteable | All signing blocked | Autonomous repair/restore only if durable signed history can be reconciled; never trade without write-ahead evidence |
| Remote audit outage with durable local records intact | Block new risk before upload grace/retention margin is endangered; reductions require a durably loggable permitted path | Drain outbox and verify acknowledgements; persistent bad credentials/config are not labelled self-clearing |
| Clock untrustworthy | All timestamp-dependent signing blocked; continue safe observation/reconciliation | Verified synchronization plus hysteresis; UTC clock for timestamps, monotonic time for elapsed deadlines |
| New-risk halt in declared risk profile | Buys blocked; independently valid reductions permitted | Only the declared reset predicate; restart or midnight must not clear a run-wide latch |
| Closed venue / no route / insufficient gas | Affected execution blocked; requirement remains pending | Bounded periodic rechecks, reserve/top-up path if valid, deadline incident if still impossible |

“Stuck-state exit” means every recoverable fault has a tested automatic recovery path and every unrecoverable one is visible and safely bounded. It cannot mean guaranteed liquidation through a closed market, zero gas, missing nonce evidence or a compromised signer. Separate avoidable software deadlocks from externally blocked states and quantify time spent in each.

Persist UTC first-seen/expiry times, boot identity and attempt/gas counters. Monotonic timers are only valid within their clock/boot epoch; do not reuse raw monotonic values across reboot. Reconstruct overdue work only after validating clock trust/continuity. Restart or backward UTC correction cannot grant fresh retry/gas budgets or make an expired proposal current again.

### ENG-07 — Crash-safe audit and round closure [R]

One logical immutable ai-seeds event per decision round, with stable event ID, finalized event bytes/hash and chunk boundaries stored durably **before first transmission**. Retry those bytes with the same event ID; acknowledge every chunk/file durably. A lost response is an idempotent resend, not another `Client.log()` call with a new random ID. Schema validation/size checks occur before the trading path relies on an eventual record.

The unmodified SDK's public `log()` is insufficient for this contract by itself (R06). Implement a first-party durable adapter using the documented PROTOCOL 2.0 idempotency/transport contract and the pinned SDK's applicable validation, or demonstrate an equally durable integration. Record this integration choice and its relationship to G-19's SDK wording before adoption; pass official protocol vectors and mocked receiver tests. Do not edit `vendor/` or rely on undocumented monkey-patches without an explicit versioned compatibility contract.

Separate **local durability**, **upload pending**, **server acknowledgement** and **audit reconciliation**. Spool emptiness is a useful SDK health signal only after accounting for in-flight work, errors and all round outboxes; it is not per-round proof. A 4xx may leave no spool at all. Bad credentials, validation errors and oversized payloads have distinct remediation; retries do not repair permanent errors.

Round closure is bounded and never waits indefinitely for a pending transaction. It includes broadcast hashes even on failure/timeout, never approve hashes in `orders`. Persist the intent/hash before broadcast so a crash can recover an ambiguous attempt honestly. If later recovery creates a new authorized swap attempt, it belongs to a new linked recovery round with its own record; do not edit an already uploaded event. Define unique primary ownership of each hash, with links to the originating economic intent; factual reconciliation events may reference it without claiming another order.

The assessor runs asynchronously but every consumed assessment has complete saved model/tool input/output, reasoning summary, schema/version and source references. Include the required material and causal references in the round log; references alone must not silently omit fields required by the kit. Bound evidence/model budgets to the 8 MB log limit and retain full local artifacts for F-49; unsupported oversize behavior blocks activation. A fallback valid error log must retain every possibly broadcast hash and the actual failure, not invent successful reasoning.

### ENG-08 — Availability, evidence and failure scope [R]

Every input has source identity, entity/contract/currency/unit, event/publication time, first observed/ingested time, version/hash, availability evidence, expiry and health. Record revision/corporate-action changes. Live decisions use information observed by their cutoff; historical availability must be justified separately and never substituted for today's retrieval timestamp (GAP-24). Closed versus unknown market state are distinct; neither permits an order.

Persist filing discovery, cursor/watermark and deduplication atomically with queued jobs. A watermark advances only after the work is durable, not after fetching only the newest N rows. Define retry/dead-letter outcomes and backfill after outage. Each assessment key includes source version, complete input/context hash, model/prompt/tool/verifier versions and schema. An accession is not a unique assessment context. Late/stale/out-of-order results cannot overwrite newer verified state; newly ingested adverse evidence invalidates any dependent outstanding buy authorization.

A declared dependency graph decides fault scope. A missing feature blocks actions that require it; global balance/ownership/audit faults have global scope. Missing data remains missing as an outage grows. Reassessment expiry produces `UNAVAILABLE` plus a new bounded job/probe, not permission to buy. If a policy can operate without a particular source, that independence must be explicit before activation and consistent with declarations; it cannot be inferred from an empty queue during ingestion failure.

Keep raw retrieved instructions untrusted. Retrieval workers get approved destinations and resource budgets; verification controls which claims reach memory; policies/LLMs receive no signing or uploader secrets. Logs use redaction at credential boundaries while retaining all non-secret evidence needed for audit. Fake “system” text in a filing must not alter destinations, thresholds or authority.

### ENG-09 — Four distinct validation modes [R]

| Mode | Inputs and execution | What it establishes | What it does not establish |
|---|---|---|---|
| Exact audit replay | Recorded ordered events, model/tool results, clocks, version/profile/state; external writes disabled | Same downstream state, decisions and intended commands from identical recorded facts | Provider determinism or alternate-policy profits |
| Deterministic fault simulation | Real reducer/planner/execution/audit state machines; virtual network, storage, signer and chain; seeded discrete-event clock | Reproducible crashes, duplicate/out-of-order responses, delays, partitions, reorgs and recovery | Actual venue/OS behavior or performance |
| Market/counterfactual simulation | Historical or synthetic paths and explicit fill/cost/latency model; separate portfolio per policy | Sensitivity/feasibility, later pre-registered policy research | Guaranteed fill at a candle/quote, independent statistical samples or live edge |
| Paper/dry run and dev rehearsal | Live read-only adapters and fake signer/receiver first; then separately authorized manifested dev integration | Real response shapes, clock/calendar, latency, protocol compatibility and recovery integration | Scored-run profit or permission to tune on dev PnL |

Advance simulation to the next **event**, not just the next hourly decision. Inject quote expiry during approve, API latency, gas depletion, partial multi-order plan completion, success with lost response, delayed indexing, crashes around each durable boundary and upload acknowledgement. A swap is fill-all-or-revert under F-97; a portfolio plan can be partially complete across swaps.

Use independent reproducible random streams for market, venue, model latency and infrastructure faults, keyed by scenario/time/entity where appropriate; different policies' call counts must not silently change the exogenous market path. Store seeds, generator version, scenario parameters, initial state and dataset hashes. For exact replay use recorded outputs rather than calling a stochastic LLM again. Counterfactual reuse of an assessment is valid only if its complete inputs are unchanged and independent of that alternative policy's holdings/thesis; otherwise simulate/recompute it under a declared assumption and label the result approximate.

Candles are trade aggregates, not executable midpoints. Never use a bar's close/high/low before the bar has closed and become available. Missing bars do not imply a zero return, an open venue or a fill. Preserve gaps; do not stitch separated windows into invented continuous portfolios. Jun/Jul to Oct supplies only roughly 6–9 non-overlapping calendar two-week windows even with complete coverage, not IDEA-020's 10–14; usable windows must be counted from actual jointly covered timestamps. Synthetic repetitions and correlated names do not increase historical independence.

Quote simulations include both approval and swap gas, gas price variability, failed attempts, bid/ask/route costs without double counting, size effects, market closure and latency. Sample correlated outages/stress, not only independent failures. A quote for another time, route or size cannot be replayed as guaranteed fill. Preserve unavailability and rejected proposals in reports. The existing IDEA-018 Monte Carlo can be a labelled path generator after review; it is not the execution engine or conformance oracle.

Report operational invariant failures, recovery latency, unknown-state duration, feasible-but-missed proposals, block causes, timing/cost attribution and audit completeness independently of policy PnL. Report equity/realized PnL/fees/gas separately while Q-39 is open. Later policy comparisons require their own committed EXP criteria, holdout windows and selection rule; this review chooses none.

### ENG-10 — Accounting and gas [R]

Maintain an event-derived asset ledger in integer base units: USDT cash, each eligible token, native BNB, reserved amounts and pending alternatives. Fill receipts and reconciled actual balance deltas establish holdings; quoted amounts never do. Reverts change gas/PnL but not acquired holdings. Duplicate observations cannot apply a fill twice. Reorg observations produce explicit reversals/provisional states, not edits to immutable history.

Separate cost basis/realized round-trip PnL, unrealized PnL, fees, BNB consumption/revaluation, mark-to-market equity and estimated executable liquidation equity. Declare the cost-basis convention before implementation. Internal marks are not asserted to be the unknown official valuation source. Equity peaks/day anchors persist across restart and carry quality/age; missing or stale marks must not reset drawdown. Record unsolicited assets or balance changes without approving/trading them; reconcile corporate actions rather than silently treating them as fills.

The gas controller distinguishes gas available, gas reserved for the in-flight step, planned liquidation costs, top-up costs and a discretionary-entry reserve. A protective reserve blocks new discretionary spending; a validated exit is allowed to spend its allocated reserve. Requiring the entire pre-entry reserve to remain after every exit would deadlock liquidation. Every step must still afford its actual worst-case gas. Gas top-ups are explicit infrastructure intents through the permitted USDT→BNB route, with their own bounds, audit and dependencies; Q-08's log convention and Q-03's first-gas availability remain open. No external funding or arbitrary gas swaps are introduced.

### ENG-11 — Scheduler, lifecycle and observability [R]

Durable scheduled-trigger keys prevent duplicate rounds after restart. Store due time, valid-through, priority, missed-tick disposition and next wakeup. Catch up observation/reconciliation, but never blindly execute an old timed trade after recovery. A merged round retains all trigger IDs and consumes each once. Use UTC instants plus a pinned exchange-calendar/timezone version; test DST, holidays, half-days and UTC loss resets. Scored start/new-risk/end gates are explicit validated configuration with source/provenance; do not hard-code speculative dates.

Confirmation polling, upload retries, health checks, position safety monitoring and policy decisions are separate jobs with separate intervals. Routine evidence work cannot starve held-position servicing, nonce recovery or audit uploads. Limit queue length, retries, response sizes, tool budgets, model concurrency and total gas expenditure. Use backoff/circuit breakers with bounded recovery probes; classify permanent versus transient errors. Exhausted trading retries stop further economic attempts, while cheap health observation can continue.

Persist execution lifecycle separately from policy thesis state. A thesis review is a request, not automatically a trade or an automatic re-entry. Pending exits remain until the residual is reconciled or explicitly impossible; terminal-flatten completion means actual reconciled residuals meet the declared dust rule. Recovery cannot clear hard/run-wide latches as a side effect of a daily reset.

Observable metrics include last durable event/decision, event-loop and job lag, oldest pending transaction/assessment/upload, heartbeat gaps, balance discrepancies, gas budget, input ages, policy rejection/clamp counts, feasible proposals lost to engine latency, retry/revert costs, disk/retention margin and deadline slack. Every state has a reason and next action; distinguish legitimate policy HOLD, risk HOLD, unavailable venue and a stalled process. Health endpoints reveal no credentials and trigger no wallet actions.

### ENG-12 — Deployment and release gates [R]

Bundle and verify code, lockfile/image, policy and risk schemas/config, prompts/tools, model artifacts, calendars, source registry, migrations and registered-version evidence. Keep mutable journals/data outside code-integrity hashes but retain their own provenance/durability checks. Pre-start registration proof should survive a GitHub outage (GAP-33); never treat a failed remote request as permission to bypass version checks. Pinning code does not pin an external provider's behavior: schema/model failures still need tested handling.

No trade-capable object or wallet key exists in replay/paper processes. Modes require distinct capability bundles and explicit startup validation, not only `if mode == live`. Replay must succeed offline with all secrets absent and networking disabled. Final and dev wallets have distinct run IDs, secrets, nonce stores, journals and uploader ownership.

Start one active signer; enforce a durable ownership epoch at the signer and broadcaster, not just a process heartbeat or database leader lock. A cold standby gains authority only after fencing the old controller from new authorizations/signatures and from the controlled broadcast path. Previously emitted signed bytes may still be submitted or mined; fencing cannot revoke them. Reconcile every issued capability on takeover and preserve its reservations. Automatic restart has bounded attempts/backoff and returns through reconciliation. Corrupt credentials/manifests must not create an infinite restart loop.

Build in this order: (1) typed event/state/policy ABI plus deterministic replay; (2) durable journal/reservations/signer and fake execution/audit ports; (3) real read/quote/transaction/log adapters with crash tests; (4) paper soak, then registered dev rehearsal and recovery; (5) final activation evidence. Policy fixtures should exercise HOLD, entry, reduction, exit and stateful re-entry without selecting a profitable policy. Re-estimate staffing after this vertical slice; no revised person-day promise is made here.

## 4. Prospective acceptance matrix — NOT RUN

All invariants must hold in every applicable scenario, not merely on average. For generated fault cases, save failing seeds and minimal event histories as regression fixtures. Run deterministic tests against committed/pushed decision/trading/logging code per F-61; register any experiment before running it. These tests do not require another policy comparison.

| ID | Test and pass criterion | Covers |
|---|---|---|
| AT01 | Install stateless and stateful fixture policies with different feature needs using only registry/profile changes. Replay each with identical input/state to identical output hashes. Nested mutation, hidden time/I/O and over-budget execution cannot affect engine state. | R01/02, ENG-01/02 |
| AT02 | Policy requests over-cap/blocked/late buys and discretionary exits. Independent risk controls always win; valid discretionary exits are possible; invalid policy never disables mandatory controls. Risk/profile hash cannot be changed by policy. | R01/07 |
| AT03 | Reject NaN, Infinity, negative/duplicate/unknown targets, bad precision, stale snapshot/profile/state versions and expired proposals. Missing targets keep quantities. Invalid outputs produce a no-policy-action/incident record, with any independently valid mandatory actions also recorded. | R02/09 |
| AT04 | Simultaneous proposals cannot double-reserve cash/holdings/gas or fund buys from pending sells. Restart before/after reserve/settle produces the same ledger; fills/fees apply once. Check both 100 and 200 USDT fixtures. | R05/11 |
| AT05 | Simultaneous cap/loss/terminal/evidence reductions retain all required constraints; no rebuy in the same round. Quote failure preserves pending obligation. Child sells obey per-trade caps and terminate as filled residual, dust or explicitly blocked. | R11/13 |
| AT06 | Approve confirms after a buy deadline or an observed market-state change; the old buy swap is not authorized. Guard changes immediately before/after the durable authorization point obey the specified ordering; later observations do not imply revocation of emitted signatures. Applicable recipient/token/value/min-out/deadline/selector/amount/router tampering always fails authorization. | R09 |
| AT07 | For every transaction step inject crash before/after each durable transition, lost broadcast response, delayed success/revert, nonce errors and duplicate result. No duplicate economic fill, nonce skipping, lost hash or premature resource release. | R03–05 |
| AT08 | Unknown nonce consumer, zombie primary, lease loss and stale restored checkpoint cannot obtain new valid signing authority. Race ownership loss before/after authorization acceptance; old issued payloads remain reserved/reconciled. A missing nonce blocks wallet progression honestly; another token is not claimed as an escape. | R03/08 |
| AT09 | If replacements are proposed, cover original-success-before-expiry but late visibility, unresolved approve, rejected/underpriced replacement, competing hashes and reorg where the apparent winner disappears and the original becomes canonical. Reserve the worst mutually exclusive outcome without booking both as spent; apply only the accepted canonical result. Unsupported capability remains disabled. | R04/09 |
| AT10 | Crash after receiver STORED but before local ack; replay exactly the same event ID/bytes/chunks and obtain one logical event. Also crash before send, mid-chunk and after local enqueue. Official protocol vectors pass; all broadcast swaps map to their version/decision/round. | R06 |
| AT11 | Inject 400/401/413/429/5xx, disk full, corrupt tail, oversized model I/O and UTC upload rollover. No error disappears because spool is empty; local durability loss blocks signing. Recovery with sufficient measured delivery slack drains the outbox before its deadline; later recovery preserves every record and reports the deadline breach without backdating it. | R06/08 |
| AT12 | Source outage hides an adverse filing; 24h elapsed and reassessment timeout do not permit a dependency-invalid buy. Catch-up processes all filings once; stale/context-mismatched assessments never overwrite newer state. | R07/12 |
| AT13 | Exact replay uses captured model/adapter results offline and matches state, latches, proposals, intended actions and audit payload hashes. Recomputed LLM output is never silently substituted. | R10/12 |
| AT14 | Under restart/partition/queue overload, safety/reconciliation/uploader work retains service. No unlimited economic retry or restart loop. Each blocked state exposes reason, last progress, bounded next action and escalation. | R08/13 |
| AT15 | DST Nov 1, UTC midnight, weekends/half-days, clock jumps, reboot plus backward UTC correction, missed/duplicate timers and merged triggers produce no duplicate round or execution of expired trades. Run-wide latches, timeout age and retry/gas budgets survive day reset/restart; boot-local monotonic values are not reused. | R13 |
| AT16 | Perturb future bars and delayed assessments: earlier decisions remain unchanged. Missing/shuffled/duplicate source blocks preserve entity identity; early bar-close use fails. Status pending→success and source revisions are new observations, not duplicate-ID violations. Shared exogenous paths remain comparable across policy call counts. | R10/12 |
| AT17 | Fake venue drives the same approve/requote/sign/broadcast/reconcile machine as live. Paper has no key/broadcast capability; its fills remain labelled simulated. OS/storage/real-adapter contract tests supplement simulation. | R10 |
| AT18 | Zero gas, reserved exit gas, top-up failure, fees/reverts, stale marks, unsolicited balance changes and terminal liquidation costs have correct ledger/equity effects. Approvals need no nonexistent swap-deadline field; bStock closure alone does not invent a market-state gate for an otherwise permitted gas-maintenance intent. Applicable terminal/route/budget restrictions still hold. Final liquidation costs are included in drawdown; no fake flat state or overselling. | R11 |
| AT19 | Malicious filing/tool output cannot change rules, signer destinations or secrets. A policy/assessor hang cannot starve recovery or upload; response and storage budgets hold under worst-case input. | R12/13 |
| AT20 | Fresh Linux install/secret-free test collection, manifest mismatch rejection, backup/restore, registered-wallet binding, cold-standby fencing and complete audit export pass. Attach actual rehearsal evidence for the declared 5+ days including weekend; resolve GAP-04 before claiming a shorter substitute. | R14, ENG-12 |

Activation requires all applicable tests passed, required capability/parameter choices settled and recorded, no unexplained transaction/ledger/log gaps, and live adapter/recovery rehearsal evidence. Optional capabilities may be omitted only explicitly, with their limitation and declaration impact recorded; failing a mandatory guarantee is not a reason to disable its test.

## 5. Full-codebase inventory and implementation findings [V]

| Files reviewed | Role / finding | Follow-up |
|---|---|---|
| `binance_test.py` | Signed-read smoke probe, no wallet executor. Loads and validates secrets at import (17–26); name matches pytest's default `*_test.py` pattern, so secret-free collection can fail before tests run. | C01: move credential lookup into invoked probe path or exclude/rename intentionally; AT20. |
| `tools/probe_candles.py` | History/API-shape probe, with undocumented paging experiments. Candle blocks lack explicit entity identity; error first-call path skips paired call; `Retry-After` assumes integer (78–79). | C02/C03; promote neither raw ordering nor probe retries into runtime contracts. |
| `tools/probe_kit_sources.py` | Public-source coverage probe, not a source registry/runtime ingester. Default source C still probes `data.binance.vision` (247–249) despite current research-source exclusion; snapshots/partial paging are not complete historical availability evidence. | C04: isolate historical probe scope and enforce approved-source profile before reuse; no source-rights change here. |
| `tools/probe_quote.py` | Quote-only cost probe. Existing GAP-63 authentication-vs-compliance diagnosis and Retry-After problems remain. It checks token-list state but not underlying-market state; hard-codes USDT decimals; quote round-trip excludes actual approval/swap gas and timing risk. | C03: do not treat probe success/cost as order permission or realized cost. Gate promotion on typed errors, both states, metadata and cost provenance. |
| `tools/edgar_fetch.py` | Newest-N research fetcher, not durable ingestion. Existing GAP-63 table/encoding/provenance issues remain; first EX-99 selection can omit relevant primary filing sections; no durable watermark/job/assessment cache. | C05: retain research label; runtime contract is ENG-08, with raw bytes and portable saved-text hashes. |
| `tools/realised_vol.py` | Positional `daily[::2]` zipped to fixed token order (54–58) can silently label another token's volatility after a failed daily request. `stats` (35–43) lacks finite/positive/minimum-history checks and divides an underfilled EWMA seed by 20. | C02: identity-keyed records plus minimum-history/closed-bar validation; AT16. Static counterexample: NVDAB fails, GOOGLB succeeds → GOOGLB daily block is labelled NVDAB. |
| `tools/fetch_h10_krw.py` | Standalone H.10 parser/fetcher; its existence does not lift current source hold or supply a runtime vintage/availability contract. | C04/ENG-08 source registry; no new use authorized. |
| `tools/idea018/analyse_candles.py`, `variants.py` | Descriptive candle analyses with sample-specific EDT/calendar/coverage assumptions, positional block context and top-level execution. | C06: keep research-only; runtime feature/calendars require validated identities and coverage. |
| `tools/idea018/mc_run.py` | Illustrative policy simulator, no reservations/nonce/real execution state. Final `trade(-h, …)` after the last drawdown update (118–121) means reported drawdown omits terminal liquidation gas. A zero-move four-name example loses another 4×gas at flatten with no MDD update. | C07: correct before any future use of that metric; no rerun/result revision is claimed here. Not engine conformance evidence. |
| `requirements.in`, `requirements.lock`, `environment.yml`, `README.md`, `.gitignore`, `.env.example`, `CLAUDE.md`, `AGENTS.md` | Dependencies/procedures exist. Lock records macOS arm64; fresh/Linux validation remains GAP-45. `.env.example` contains placeholders, not credentials. No deployment manifest, runtime package, test suite or CI configuration found. | C08: platform/release evidence and secret-free tests; no library-vulnerability or exhaustive secret-history audit claimed. |
| `vendor/ai-seeds-sdk-0.3.0/` and kit integration docs | Vendored client/protocol inspected read-only by execution reviewer. `client.py` 145–159 makes a new random event ID and uploads before fallback spool; 220–225 appends without an explicit fsync. | R06/ENG-07, K13 review note; vendor remains unchanged. |

These are static findings, not newly executed tests. C01–C08 must be resolved before affected research tools become runtime components; the review does not imply every exploratory script must become production code. No implementation backlog item is completed by documentation alone.

## 6. Literature register and limits

All sources below were accessed 2026-10-10 by the literature or execution reviewer; the parent independently opened LIT01–04. “Read” identifies the relevant sections checked, not a claim that every cited system was reproduced. These are primary papers or the system/vendor's own documentation.

| ID | Primary source / what was checked | Applicable finding and limit |
|---|---|---|
| LIT01 | Parnas, *On the Criteria To Be Used in Decomposing Systems into Modules*, CMU-CS-71-101 (1971 original report): modularization examples, criteria, conclusion. [Original report](https://prl.khoury.northeastern.edu/img/p-tr-1971.pdf). | Hide decisions likely to change behind interfaces. Applying this to policy/risk/core separation is our engineering inference, not a prescription for this competition. ENG-01/02. |
| LIT02 | Zhou et al., *FoundationDB: A Distributed Unbundled Transactional Key Value Store*, SIGMOD 2021, §2.1 and §4 including test limitations. [Paper](https://www.foundationdb.org/files/fdb-paper.pdf); [project testing documentation](https://apple.github.io/foundationdb/testing.html). | Simulate network, disk, clock and randomness around real state machines; complement with OS/dependency/performance checks. No recommendation to introduce FoundationDB; no simulator proves every environment assumption. ENG-03/09, AT07–17. |
| LIT03 | Temporal, workflow definition: deterministic command history, intrinsic nondeterminism and versioning sections. [Documentation](https://docs.temporal.io/workflow-definition). | Record external/model results and replay ordered history. Temporal is an architectural reference, not a required dependency; exactly reproducible downstream code is not deterministic hosted inference. ENG-02/09. |
| LIT04 | AWS Builders' Library, *Making retries safe with idempotent APIs*: request-token identity, atomicity, late arrivals and parameter mismatch. [Article](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/). | Durable identity bound to immutable intent; reject same-ID/different-content. Local ACID does not make a blockchain transaction and a local journal atomic. ENG-03/05/07. |
| LIT05 | Microsoft Research, *Uncovering Bugs in Distributed Storage Systems using P#*: introduction and §§2.3–2.5, safety/liveness monitors. [Paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/04/paper-1.pdf). | Specify both forbidden effects and eventual progress under stated conditions. Bounded exploration finds failures but is not proof over all executions; no requirement to adopt P#. ENG-06, AT14. |
| LIT06 | AWS Builders' Library, *Timeouts, retries, and backoff with jitter*: retry multiplication, idempotency, throttling, backoff and jitter. [Article PDF](https://d1.awsstatic.com/builderslibrary/pdfs/timeouts-retries-and-backoff-with-jitter.pdf). | Assign retry budgets once per operation/dependency; protect capacity and avoid coordinated storms. Values must come from our measurements and deadlines. ENG-11. |
| LIT07 | Ethereum transaction documentation (nonce semantics) and Geth monitoring documentation (queued versus executable transactions). [Ethereum](https://ethereum.org/developers/docs/transactions); [Geth](https://geth.ethereum.org/docs/monitoring/understanding-dashboards). | Account-wide nonces explain why a gap blocks unrelated-token exits. General EVM behavior is not evidence that the competition's Web3 endpoint supports fee replacements. ENG-05/06. |
| LIT08 | BNB Chain, BSC JSON-RPC API list: latest/safe/finalized and finality methods. [Official documentation](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/bsc-api-list/). | Explicitly distinguish inclusion and accepted final settlement. Do not import latency examples or assume the supplied Web3 API exposes equivalent fields. Prove permitted read-source capability before depending on it. ENG-05/06/10. |

No source here establishes profitable trading, independent samples in sparse bStock history, or the organisers' final score. Those claims remain outside this review. The literature supports a compact deterministic core plus fault-injected boundaries; it does not justify adding infrastructure merely because a successful system used it.

### Cross-review record

CR1 — Independent first passes agreed on the policy/core boundary, insufficient replay fidelity, missing persistence/reservations, audit identity ambiguity and unjustified timeout-to-buy transitions. The execution reviewer additionally checked the vendored SDK and nonce/finality assumptions; the architecture reviewer checked every first-party source file and all three submitted PDF pages.

CR2 — Parent synthesis added explicit staged quoting, policy state/feedback, action identities, accounting/gas, capability-separated modes, deployment/freeze and 20 prospective acceptance cases. All three reviewers then independently attacked this corrected document. Accepted corrections: transaction-specific guards for approve/bStock/gas paths; durable authorization ordering against racing risk/ownership events; fencing future authority without claiming to revoke old signed bytes; upload deadlines conditional on sufficient recovery slack; immutable event IDs distinguished from evolving observations; reboot-safe elapsed deadlines; explicit replacement-reorg alternatives; invalid-policy logging that still permits valid mandatory controls; two source-line corrections.

CR3 — Each reviewer reported no additional foundational/blocking architectural defect after those corrections, subject to the stated unproved integration capabilities and implementation tests. This is agreement on a proposed design basis, not unanimity about profitability, a formal proof, an adopted design or readiness certification. Parent checked each accepted correction in the saved document and preserved the NOT RUN status of every acceptance case.

## 7. Remaining ownership and decision register [OPEN]

Suggested functional owners follow the repo; assignment is still GAP-37. This review does not choose strategy values.

| Work | Suggested owner | Where recorded / completion evidence |
|---|---|---|
| Adopt corrected engine contracts and reconcile G-18/G-19 language/declarations | Team; Keith + Keegan | GAP-65, GAP-30/34/46, GAP-62; adopted spec and versioned implementation |
| Nonce/finality/route decode/replacement capability, reservations and gas controller | Keith | GAP-29..32/47/49; AT04–09/18, dev adapter evidence; replacement disabled until proven |
| Journal, stable log outbox, fencing, storage, restart, release/restore | Keegan | GAP-33..38/45/46/52; AT10/11/14/20 |
| Policy ABI, deterministic state and evidence-job contracts | Yao Zhu | GAP-24/27/28/63/65; AT01–03/12/13/16/19 |
| Valuation/cost model, calendars and simulation assumptions | Isaac with Keith/Keegan | GAP-13..15/50/51/65; AT05/15–18; no policy ranking in this task |
| Source/probe promotion defects C01–C08 | Yao Zhu + Keegan; Isaac for analytics | GAP-63/65; fixes and targeted fixtures before promotion |
| Organiser-dependent activation inputs | Team | Existing GAP-41/42: Q-03 usable first gas, Q-04/Q-06 valuation/window, Q-08 gas-swap logging, Q-14 incident grace, Q-33 procedures, Q-35 final secret, Q-39 scoring, Q-40 automatic restart. Q-32 hours measured through market-state behavior; Q-38 quotas from portal. Do not re-ask already settled Q-16/34/36/37. |
| Frozen operational values | Respective component owners | GAP-13/28/36/65: input/quote ages, replay schemas, timeouts, retry/gas budgets, queue/service limits, confirmation/finality rule, mark/dust rules, retention/recovery targets and terminal UTC gates. Activation config must reject missing values; no unflagged placeholders. |

Policy decisions stay in GAP-64/D-08/D-11/D-12 for a separate task. No exposure/cadence/evidence-exit variant is selected here. Handoff requires the repo's clean/pushed check; the pre-existing untracked `Claude outputs/` copies are user-owned and left untouched.

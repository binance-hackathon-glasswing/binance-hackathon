# IDEA-020 — Engine architecture: policy interface, replay harness, autonomous clears and failure scope

- Date / author: 2026-10-10 / SYZ (requested); drafted by Claude (Cowork).
- Status: open — **⚠ RECOMMENDED — NOT DECIDED.** An architecture spec for the team to adopt on Oct 11. It does not choose a trading policy, change a declared value or authorise trading.
- What: (1) a quick review of [IDEA-019](IDEA-019.md) and what this spec adopts from it; (2) the engine that every candidate policy runs on, filling the four architecture gaps named after [IDEA-018](IDEA-018.md):
  - G1 a policy interface, so policies are swappable configuration;
  - G2 a replay and paper harness, so policies can be compared without dev-wallet P&L;
  - G3 autonomous clears for stuck states;
  - G4 a scoped failure model.
- Why: the trading-policy debate (IDEA-012..019) keeps moving because scoring (Q-39) and the spread (GAP-50) are unknown. Every candidate uses the same building blocks: build, hold, mandatory reductions, evidence exit or block, flatten. Fix the engine now; choose policy *parameters* by Oct 19 from replay, the Monte Carlo and measured costs.
- Cost / risk: desk design only. No code, API, wallet or ai-seeds calls.
- Links:
  - entries: IDEA-010 §4–§5, IDEA-011, IDEA-013 R1–R4, IDEA-015 A.1–A.2, IDEA-016 §3.1, IDEA-017, IDEA-018 §4, IDEA-019;
  - guardrails and facts: G-01, G-03, G-04, G-09, G-18, G-19, G-22, G-25, G-27, G-28, G-30, G-46; F-95..F-101, F-105, F-114, F-117;
  - decisions: D-05, D-08, D-11, D-12;
  - backlog: GAP-08..15, GAP-29..34, GAP-46..47, GAP-63, GAP-64.

Labels: [V] checked here (file and quote); [E] estimate with stated inputs; [O] opinion; [I] inference; [C] changes or interprets a declaration (needs a GAP-62 row).

## 1. Quick review of IDEA-019, and what this spec adopts

IDEA-019 (Isaac, drafted by Codex) consolidates IDEA-012–017 (§1–4). Its §5 adds a candidate policy aimed at prize placement. It is careful and consistent with the sources. Most of its policy content overlaps IDEA-018 §4. **What it adds that this spec adopts:**

| IDEA-019 item | Adopted as |
|---|---|
| §5 "Admit only names with sufficient trustworthy inputs, … executable routes and affordable entry/exit. If more than four pass, prefer … lower measured round-trip cost under a frozen ranking rule; do not rank by volatility alone." | Engine **eligibility gate** (§3.4), run at activation and each scheduled round. It is more general than IDEA-018 §4.1's MSFTB/SKHYB swap rule, which it replaces |
| §5 "Missing inputs do not justify silently substituting an unregistered sizing method." | **Failure model** (§6): a name with no valid σ₆₀ is ineligible, never sized by a fallback |
| §5 "Horizon expiry triggers review, not an automatic sell and rebuy." | **Lifecycle** (§3.3): thesis renewal is a logged state change, never a trade |
| §5 "At most one discretionary portfolio rebalance per defined session … not a quota." | **Engine rate limit** (§3.2): it applies to policy-originated trades only; mandatory reductions are exempt |
| §5 "No order when either required market-state check reports closed." | **Adopted, and corrects IDEA-018 §4.3**, which let sells check only `rwa/tokens`. The kit's verbatim text: "When `openState` is `False` (here or in `rwa/underlying-market`), the market is closed or trading is halted: don't place orders." (`docs/official/kit/bstocks-trading-guide.md` line 102) [V]. It applies to sells too. See §5.1 |
| §2 R2 "Distinguish NOT RUN, INCONCLUSIVE and NOT SUPPORTED. None automatically authorizes a variant." | Result labels in the replay reports (§4.5) |
| §3 [V] IDEA-013 R5–R8 still present in the tools | Confirms GAP-63; the engine's EDGAR and quote adapters must not reuse those code paths unfixed |

**Where IDEA-019 and IDEA-018 disagree**, the engine supports both as configuration, so the build does not wait on the decision (§3.5):
- **Evidence exit:** IDEA-019 R2 keeps it in shadow; IDEA-018 §1 R3 runs a narrow live falsifier exit. Config switch: `evidence_exit = shadow | live`.
- **Re-entry:** IDEA-019 §5 needs a fresh reassessment; IDEA-018 §4.2 lets code re-enable after a soft-block expiry. Config switch: `reentry = code | reassess`. The `reassess` mode is made safe by an engine-scheduled reassessment job with a timeout (§3.3), which removes IDEA-018's stuck-in-cash objection.
- **Objective and exposure:** IDEA-019 §5 targets prize placement; IDEA-018 targets net profit. This is a policy parameter (`gross_multiplier`, bounded by the declared caps), chosen by Oct 19 under D-12.

## 2. Shape of the engine

```
                    ┌────────────── Clock (UTC; session calendar; gates) ──────────────┐
 Adapters ──► Snapshot builder ──► Health/failure model (§6) ──► Mandatory layer (§5)
 (quotes, state,     │  (frozen, journaled                 │            │
  balances, EDGAR    │   RoundInput)                       ▼            ▼
  queue, assessor)   │                         Policy.decide (pure, §3)  forced targets
                     ▼                                     │            │
               Journal (WAL) ◄── Precedence resolver (§5.2): integrity ▸ market ▸ mandatory ▸
                     ▲             evidence ▸ policy; clamps (caps, halts, blocks, MinTrade, cost)
                     │                                     ▼
               ai-seeds round log ◄── Order planner ──► Executor (Live | Paper | Sim) ──► Reconciler
```

- **One round = one cycle of the loop and one ai-seeds log (G-19).** Rounds are either *scheduled* (US-session open+30 and close−60) or *monitor* (hourly, 24/7). A monitor round in the same hour as a scheduled round is merged into it.
- **The LLM is never inside a round.** The assessor runs as a separate worker on the durable EDGAR queue (IDEA-015 A.2). It writes assessments keyed by accession; rounds only read them.
- **Swappable implementations.** Every adapter and the executor sit behind an interface with three implementations, `Live`, `Paper` and `Sim` (§4). The round loop, precedence resolver and policy code are identical in all three modes.

## 3. G1 — The policy interface

### 3.1 Contract
A policy is a **pure, deterministic function** of a frozen snapshot. It does no I/O, uses no clock read other than the snapshot's, makes no network call and uses no randomness. Its parameters are part of the manifest hash (G-03).

```python
@dataclass(frozen=True)
class RoundInput:                      # built by the engine, journaled before decide()
    round_id: str; kind: Literal["scheduled", "monitor"]
    now_utc: datetime; session: SessionInfo          # open/close, open+30/close-60, US holiday, DST-safe
    gates: TerminalGates                             # trade_after, new_risk_end, flatten_start/by (absolute UTC)
    portfolio: Portfolio                             # cash, holdings (on-chain), equity marks, peak, day_start_equity
    market: dict[Symbol, MarketView]                 # both openState flags, executable quote(s) per intended size,
                                                     # reference mark (tokenPrice), quote age, cost estimate incl. gas
    features: dict[Symbol, Features]                 # sigma60 (or None), regime inputs; computed by the engine
    evidence: dict[Symbol, EvidenceView]             # queue status, latest verified assessment, hard/soft block state
    lifecycle: dict[Symbol, LifecycleState]          # §3.3
    risk: RiskState                                  # ladder latches, regime R, health flags (§6)
    params: PolicyParams                             # frozen config, hashed in the manifest

@dataclass(frozen=True)
class PolicyOutput:
    targets: dict[Symbol, float]                     # desired weight of equity, ≥ 0; absent = keep current
    reasons: dict[Symbol, str]                       # reason code per name (feeds cot/output and metrics)
    candidates: list[CandidateNote]                  # every name considered, incl. "not chosen because …"
    review_note: str | None                          # optional human-readable round summary for cot

class Policy(Protocol):
    name: str; version: str
    def decide(self, x: RoundInput) -> PolicyOutput: ...
```

### 3.2 What the policy may and may not do
- **May:** set target weights for eligible names, i.e. build, hold, re-size, or reduce to zero for its own reasons. It may also choose among eligible names, and log candidates and reasons.
- **May not**, because the engine clamps it regardless (§5.2):
  - exceed a hard cap or the operating ceiling;
  - buy during a halt, a block, or after `new_risk_end`;
  - trade below MinTrade, above the entry-cost cap, or outside both `openState` flags;
  - make more than one discretionary rebalance per session (IDEA-019 §5, adopted).

  Every clamp is logged as `CLAMPED:<rule>` beside the policy's raw target, so replay can show how much each policy was constrained.
- **Cannot see or call:** the signer, the executor or the assessor. Evidence reaches the policy only as `EvidenceView`. The LLM therefore never holds trade authority (architecture PDF), whichever policy runs.
- **Mandatory reductions** (§5.1) are computed by the engine *before* the policy and override it. The policy cannot add risk back in the same round.

### 3.3 Lifecycle and reassessment: engine-owned, policy-visible
Per-name states, from IDEA-018 §4.2:
- `UNBUILT`, `HELD`, `EXIT_PENDING`, `CLOSED_HARD`, `CASH_RISK`, `SKIPPED`, `FLAT_TERMINAL`;
- plus a soft-block flag and a thesis object.

The engine owns the transitions. The policy sees the state and can only target names whose state allows buying.

Additions to IDEA-018:
- **Thesis expiry** at the declared 5-session horizon is a logged `THESIS_REVIEW` state change, never a trade (IDEA-019 §5).
- **Reassessment job** (needed for `reentry = reassess`, §3.5). When a soft block expires, or a thesis reaches its horizon, the engine enqueues a reassessment for that name with deadline `T_reassess` = [next scheduled round + 1].
  - **On time:** the result updates `EvidenceView`.
  - **Not on time** (LLM down, schema failures): the failure model (§6) decides. The name never waits indefinitely: if no pending adverse accession exists, the name's buy eligibility follows `reassess_timeout_action` = [`allow` | `block_until_next_round`], a frozen parameter.
  - This is the fix for IDEA-018's stuck-in-cash objection to IDEA-019's re-entry rule.
- **Hard blocks** (verified {4.02, 1.05, 2.06}) are permanent for the run in both modes (IDEA-011 X7).

### 3.4 Eligibility gate (adopted from IDEA-019 §5)
At activation, and at each scheduled round, a name is eligible to *buy* only if all of these hold:
- valid σ₆₀ (no fallback sizing);
- quotes returned at the intended size within the last [N] scheduled rounds;
- measured round-trip cost at intended size ≤ [cap];
- declared target weight × equity ≥ MinTrade.

If more than four names pass, the frozen ranking is lowest measured round-trip cost first, then lowest σ as the tie-break (not highest). Ineligibility never forces a sell; held names leave only through mandatory or evidence paths.

### 3.5 Policy registry and the configuration that resolves today's disagreements
`policies/` holds named policies. The manifest records `policy.name`, `policy.version` and `params_hash`. Candidates expressible from day one:

| Policy | What it does | Main parameters |
|---|---|---|
| `BuildHold` (default, always shippable) | Builds the declared vol-sized book once, holds, and leaves exits to the engine | `gross_multiplier` (1.0 = declared formula), `universe_max` |
| `BuildHoldRebalance` | Adds a capped, pre-registered re-size toward the vol target | `rebalance_days`, `min_delta`, `activity_budget_bp`, `no_reversal_hours` |
| `CapLevel` (only if D-12 picks it) | Targets the operating ceiling per name | `ceiling`, `cost_condition_bp` |

Engine switches (not policies), frozen in config:
- `evidence_exit ∈ {live, shadow}`;
- `reentry ∈ {code, reassess}`;
- `reassess_timeout_action`;
- `soft_block_budget`.

In `shadow` mode the map M still runs and logs what it *would* have done next to what the engine did. That keeps IDEA-005 R4's counterfactual and gives the post-run evaluation for free.

## 4. G2 — Replay, paper and simulation harness

### 4.1 Three modes, one code path
| Mode | Data in | Executor | Signs? | ai-seeds | Used for |
|---|---|---|---|---|---|
| `Sim` | recorded candles and quote logs, or Monte Carlo paths; fixture filings | `SimExecutor` (cost and fill model, §4.2) | no | never | policy comparison; fault-injection tests; regression |
| `Paper` | live APIs, quotes only | `PaperExecutor`: fills simulated at the *real* quote just taken | no | **off** by default; if ever on, committed code with the test marker only (F-103, F-106 (c), never-do #13) | soak of everything but signing; cost-data collection; DST and calendar checks |
| `Live` | live | `LiveExecutor` (G-01, G-18) | yes | on (realtime, G-19) | dev rehearsal, scored run |

- **Clock and adapters are injected.** `SimClock` advances by round; `WallClock` is real time. The round loop never calls `datetime.now()` directly, so any two-week window can be replayed in seconds.

### 4.2 Sim cost and fill model (frozen before use, stated in each report)
- **Price path:** a token mid from 1h candles, or a Monte Carlo path (re-use `tools/idea018/mc_run.py`'s generator: per-hour variance profile, fat tails, ρ).
- **Cost per leg** = spread(name, hour category, size) + impact(size) + gas (USDT, frozen G).
  - Before quote logs exist: the grid {5, 15, 30, 50} bp/side.
  - After Oct 19: the empirical distribution from the quote logger at intended sizes, sampled by name and hour category.
- **Fill outcomes, each with a frozen probability:**
  - quote failure;
  - revert (gas spent, no fill);
  - confirmation timeout → UNRESOLVED (then resolves per §5.3);
  - `openState` false (from the logger's observed schedule once GAP-44 has data).
- **EDGAR and assessor:** a fixture filing stream (IDEA-018 §4.4 sets) with planted adverse items and an assessor stub returning labelled outputs, including timeouts and schema failures.

### 4.3 What replay is allowed to decide (G-46, ledger README rule 5)
- **Allowed:** ranking policies on *historical and simulated* paths; checking that no policy gets stuck; counting trades, costs and clamp frequencies; checking feasibility at 100 and 200 USDT.
- **Not allowed:** using dev-wallet or Paper P&L to choose or tune anything. Paper/Live outputs feed only non-P&L checks: costs, failures, latency and calendar behaviour.
- **Freeze before running:** the windows, paths, cost model and selection rule go in a committed EXP entry *before* any comparison is run. Suggested selection rule [O]: maximise mean net equity over the frozen window set, subject to P(DD ≥ 8%) ≤ [x]% and zero stuck-state events; ties go to fewer swaps.

### 4.4 Windows available for replay [I]
- bStock token candles exist since roughly Jun/Jul 2026, so about 10–14 non-overlapping two-week windows can be stitched from 1h candles. Note the probe's 7-day hole (IDEA-018 §2.1).
- Ondo daily history (~16 months) can supply longer stress paths at daily resolution.
- Monte Carlo paths cover what history lacks.
- Reports must say which source each number comes from.

### 4.5 Report (per policy × cost scenario)
- **Profit and risk:** mean and percentiles of net equity; max drawdown; P(each ladder step).
- **Trading:** swaps; executed USDT volume (IDEA-017 §4); per-swap cost split (gas, spread, impact).
- **Engine behaviour:** clamp counts by rule; skip reasons; stuck-state events (must be 0); counterfactual evidence-exit P&L (shadow).
- **Result label:** one of SUPPORTED, NOT SUPPORTED, INCONCLUSIVE, NOT RUN (IDEA-019 R2).

### 4.6 Doubles as the test matrix
The IDEA-010 §5 must-have tests (fault at each step, crash at each of 9 steps, `openState` false, 0 BNB, wrong secret, DST days, clock-shifted terminal gates) run as `Sim` scenarios with injected faults. One harness serves policy research, regression and activation evidence (GAP-05/GAP-38).

## 5. G3 — Precedence and autonomous clears for stuck states

### 5.1 Mandatory layer (engine, before policy)
Order, highest first:
1. terminal flatten;
2. regime R = 0 (sell all);
3. 12% delever (two marks ≥ 5 min apart; latched);
4. hard-cap trim to the operating ceiling;
5. regime R = 0.5 cut;
6. live evidence EXIT (`evidence_exit = live`).

Every mandatory sell still requires both `openState` flags true (§1 correction) and a fresh valid quote, and respects the declared exit slippage cap, the per-trade cap (F-105) and the gas floor. When markets are closed, the sell becomes `EXIT_PENDING` and retries hourly.

### 5.2 Precedence resolver (one target per name per round)
Layer order (IDEA-018 §4.3, with the §1 correction):
1. 0 Integrity
2. 0b Wallet pending
3. 1 Market (both flags) and quote
4. 2 Mandatory
5. 3 Evidence blocks
6. 4 Policy targets

Sells that serve two layers count once. "Any buy is new risk" (declared).

### 5.3 Halt taxonomy: every halt has an owner and an exit
A permanent halt is acceptable only where trading on would be worse than stopping. Everything else must clear itself, because no human may act during the run (F-114, F-117).

| Halt | Blocks | Clears when | Class |
|---|---|---|---|
| Clock offset > 500 ms (G-05) | all signing | offset < 500 ms on 2 consecutive checks | self-clearing |
| API error, 429, quote failure | the affected action | next successful call; bounded backoff (F-105) | self-clearing |
| ai-seeds spool > 30 min | buys | spool empty (F-109) | self-clearing |
| ai-seeds spool > 2 h or `UploadError` (e.g. bad secret) | buys | own retry queue empties | self-clearing; sells continue |
| **UNRESOLVED tx** (timeout, no receipt) | conflicting actions on that token; new nonces | **same-nonce clear**, below | self-clearing |
| **Unknown outgoing tx / nonce consumed by a hash not in our journal** | buys, permanently | never (possible key compromise or a second instance) | latched-buys. Sells continue only if on-chain balances reconcile with the journal plus that tx |
| Version or manifest hash mismatch, signer ≠ `AI_SEEDS_ADDRESS` | all signing | never at runtime; the process refuses to start (G-03, G-09) | latched-all. To keep this from firing on runtime files, the hash covers tracked code and config only, never `data/`, `.ai-seeds/` or the journal |
| 8% drawdown | buys | never (latched for the run) | latched-buys |
| 12% drawdown | buys; gross capped | never | latched-buys |
| Daily 3% loss | buys | next 00:00 UTC (declared) | self-clearing |

**Same-nonce clear for UNRESOLVED** [O; Keith to verify against G-18 (g)–(j) and the kit before adoption]:
- **Facts it rests on** [V, `bstocks-trading-guide.md`]:
  - there is no nonce endpoint, and the history omits approves (line 154);
  - "after 120 s … the transaction may still be mined" (line 156);
  - an expired quote reverts with `DeadlinePassed` (line 277).
- **Procedure:**
  1. **Wait.** Hold the intent UNRESOLVED, polling `transaction-detail-by-txhash`, until the original swap's quote deadline + [10] min. For an approve, which has no deadline, wait [10] min.
  2. **Re-sign the next intended action at the same nonce N,** with gas price ≥ 1.2 × the original. Never N + 1, and never the old signed payload (G-18 (j), F-108).
     - Because at most one transaction per nonce can be mined, this can never create two economic actions.
     - A late-mined old swap reverts with `DeadlinePassed`.
     - Re-sending an approve is idempotent: approve *sets* the allowance to the exact amount.
  3. **If the broadcast is rejected as "nonce too low",** nonce N was consumed:
     - look up the original hash's status;
     - if it is found, resolve the intent to success or fail;
     - if it is not found, raise **Unknown outgoing tx** (latched-buys).
  4. **If the original is still unresolved after the replacement confirms,** mark it `DEAD` and journal both hashes.
- **Why it matters.** It removes IDEA-018's highest stuck-state risk: one dropped transaction freezing the Nov 10 flatten.
- **Must be shown in dev** on the dev wallet with a deliberately low gas price, from committed test-mode code. That needs the broadcast endpoint to accept a same-nonce replacement, which is unverified (Q to log in GAP-63).

## 6. G4 — Failure scope: the declared rule, made precise

- **Declared** [V, `proposal_answers.md` "Failure modes"]: "A data, model, tool or schema failure means HOLD, no new risk, and an incident record. A timeout never becomes a trade."
- **Recommended interpretation** [C — needs a GAP-62 interpretation row]: "no new risk" applies to **every decision that depends on the failed input**, not book-wide. Each input has a scope:

| Input fails | Blocks | Still allowed | Incident |
|---|---|---|---|
| Quote for name X | buys and sells of X (no executable price) | others | yes |
| `openState` read for X (error ≠ false) | all orders on X | others | yes |
| Balances or reconciliation mismatch | all buys; sells only of confirmed holdings (G-18 (g)) | logging, retries | yes; degraded mode G-27 |
| Equity mark (all quotes fail) | buys book-wide | sells of names with fresh quotes; ladder uses the declared fallback mark (IDEA-010 S.3) | yes |
| σ₆₀ for X | buys of X (no fallback sizing, IDEA-019 §5) | holding X | yes |
| EDGAR poll < [24] h | buys book-wide (an adverse filing may be unseen) | sells; mandatory path | health state, logged as "EDGAR unreachable", never "no filings" |
| EDGAR poll ≥ [24] h | buys of names with no assessed filing in the last [5] sessions are allowed with `DEGRADED_EVIDENCE` | — | yes [C] |
| Assessor (LLM) timeout or schema failure on accession A for X | buys of X while A is pending (soft block, counts toward the budget) | others; all sells | yes |
| Assessor down ≥ [24] h | as the row above, per pending accession; reassessment jobs time out per §3.3 | base-book buys of names with nothing pending | yes |
| ai-seeds upload | per §5.3 | — | yes |

- **Why the per-input scope** [I]: under F-117 a book-wide reading turns any EDGAR, LLM or API outage before Nov 4 into a zero-trade run, which conflicts with F-115. The per-input reading still guarantees that no decision uses a missing or failed input. "A timeout never becomes a trade" holds in every row.
- **Health record:** every round logs a health line (each input: ok, degraded or failed, plus age) in `input` and a rule-statement `cot` (F-106 (a)). A judge sees why a round did not trade.

## 7. Build plan and owners (suggested; GAP-37)
Estimates are [E]. "Incremental" means beyond IDEA-010 §5 must-haves already planned.

| Component | Incremental pd | Suggested owner | By |
|---|---|---|---|
| `RoundInput`/`PolicyOutput` types, `Policy` protocol, registry, `BuildHold` | 1.5 | Yao Zhu | Oct 13 |
| Precedence resolver + mandatory layer + clamp logging | 1 (shares G-22/G-27 work) | Isaac | Oct 15 |
| Lifecycle state machine + reassessment job | 1.5 | Yao Zhu | Oct 16 |
| Clock / adapter / executor interfaces; `SimExecutor`, cost and fill model, fault injection | 3–4 | Keegan (harness) + Keith (executor contract) | Oct 16 |
| `PaperExecutor` | 0.5 | Keith | Oct 17 |
| Replay data loader (candles, quote logs, fixtures) + report | 1.5 | Isaac | Oct 18 |
| Same-nonce clear + halt taxonomy | 1–1.5 | Keith | Oct 15 (dev test once gas is available) |
| Failure-scope matrix + health line | 1 | Keegan | Oct 16 |
| **Total incremental** | **≈ 11–13 pd** | | |

- **Partial offset:** the fault-matrix tests that IDEA-010 §5 needs anyway become Sim scenarios. IDEA-018 §4 also dropped about 2–3 pd of policy rules. Net new is ≈ 6–9 pd [E].
- **Capacity:** still the binding constraint (IDEA-011 X1). If hours are short, cut in this order: `PaperExecutor` → Monte Carlo mode in Sim (keep candle replay) → the reassessment job (fix `reentry = code`). **Do not cut** the policy interface, §5.3 or §6.

## 8. Decisions (Oct 11) and follow-ups
1. Adopt §3 (policy contract), §5.3 (halt taxonomy) and §6 (failure scope) as engine invariants. Owner: team. Record the §6 interpretation row in GAP-62 (Keegan).
2. Adopt the both-endpoint `openState` rule for all orders (§1 correction; kit line 102). Owner: Keith.
3. Keith verifies the same-nonce clear against G-18 and the broadcast endpoint by Oct 15. If the endpoint rejects replacements, the fallback is: keep UNRESOLVED; block conflicting actions only on that token; continue sells of other confirmed holdings; log an incident.
4. Pre-register the replay comparison (windows, cost model, selection rule) as an EXP entry before running it. Owners: Isaac + Yao Zhu, by Oct 17. Choose policy parameters and engine switches by Oct 19 (D-08/D-11/D-12).
5. Unchanged blockers: Q-03 (first gas), Q-06 (window end), Q-32 (off-hours `openState`), Q-39 (scoring), Q-40 (automatic restart).

## 9. Sources and limits
- **Read for this entry:** IDEA-019 in full; IDEA-018; IDEA-010 §4–§5; IDEA-011; IDEA-013 R1; IDEA-015 A.1–A.2; SKILL.md G-03, G-05, G-09, G-18, G-19, F-95..F-110, F-114..F-117; plan.md G-22, G-25, G-27, G-28, G-46; `proposal_answers.md` "Failure modes"; `bstocks-trading-guide.md` lines 97–102, 154–156, 277–292.
- **Not tested:** that the Web3 API's broadcast endpoint accepts a same-nonce replacement; real `openState` schedules; real quote costs.
- **Status:** this is an architecture recommendation, not an implementation, and no readiness or profitability claim follows from it.

## 10. 2026-10-10 correction — engine-only independent review (SYZ requested; Codex)

[IDEA-021](IDEA-021.md) records a full first-party code review, primary systems literature, two independent red teams and a second adversarial pass over the corrected contracts. It is the **corrected architecture candidate** for this entry; both remain recommendations, not an adopted policy or implementation. The original text above is retained under the append-only ledger rule.

Do not adopt §§3–6 unchanged. In particular:
- §§3.3–3.5 embed policy choices in the engine; move them into separately manifested policy/risk profiles without loosening current declarations. Add explicit policy state, input requirements, proposal expiry, precise numeric/target semantics and outcome feedback.
- §5.3's generic same-nonce clear is unproved, and §8.3's other-token sell fallback cannot bypass a wallet-wide nonce gap. Replacement remains disabled until its authorization, competing hashes, finality, reservations and endpoint behavior are verified. Unknown signing ownership blocks all new signing.
- §6's 24-hour EDGAR relaxation and §3.3's reassessment-timeout `allow` do not establish valid inputs. Use declared dependencies and positive recovery evidence; outage age is not favorable evidence.
- The journal needs atomic reservations and durable command/audit outboxes. Exactly one `log()` call or an empty SDK spool does not establish one durable logical log across crashes; retain immutable event IDs and bytes per PROTOCOL 2.0.
- §4 needs separate exact audit replay, shared-state-machine fault simulation, approximate market simulation and real-adapter/paper/dev verification. Trade candles are not executable midpoints; synthetic fills do not prove live recovery. Jun/Jul to Oct does not supply 10–14 independent two-week historical windows; count actual joint coverage and retain gaps.
- “Always shippable,” “counterfactual … for free,” guaranteed self-clearing and the net-new 6–9 pd estimate are not established. Read IDEA-021 ENG-01–12 and AT01–20 for the corrected contracts, conditional liveness and prospective activation evidence.

No trading policy was selected, no experiment or wallet/model/logging code was run, and no implementation backlog item is closed by this review. Follow-up remains GAP-65; policy selection is separate in GAP-64.

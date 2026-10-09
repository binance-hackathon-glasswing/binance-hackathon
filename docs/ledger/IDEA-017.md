# IDEA-017 — Review of IDEA-012–016 against profit and opportunity-driven trading

- Date / author: 2026-10-10 / Codex, requested by SYZ.
- Status: open — **recommendations, not strategy adoption or trading authorization**. U1 below records the user's objective; the proposed implementation remains undecided.
- What: full project-specification review, followed by a review of IDEA-012–016 as an evolving design, including their dated corrections rather than treating withdrawn proposals as current.
- Cost / risk: document and source review only. No credential files read, wallet/API probes run, model evaluations run, transactions signed or audit logs uploaded. Existing market measurements and simulations were not independently reproduced.
- Links: D-08/D-11/D-12; H-02; G-01/G-03/G-11/G-18/G-22/G-25/G-46/G-53; GAP-08–15/24/26/28/37/44/50/54/62/63/64.

Labels: **[U]** user instruction; **[V]** source checked; **[A]** illustrative arithmetic, not a measured result; **[I]** inference; **[R]** recommendation.

## 1. Objective and specification understood

**U1 [U].** SYZ asks for maximum profit with consistent trading volume, clarified in this review as **“Regular trading when opportunities justify costs.”** Interpret this as maximizing expected net terminal portfolio profit within the declared risk and operating constraints, with reliable execution of qualifying opportunities. There is no user-requested daily trade count or turnover quota. HOLD logs demonstrate operation; they are not executed trading volume.

**V1 [V].** LARP is an autonomous, long/cash bStocks agent using the Binance Web3 Open API on BSC. Only NVDAB, GOOGLB, SKHYB, TSLAB and MSFTB are eligible; USDT funds trades and BNB pays gas. Funding is recorded as 100 USDT development / 200 USDT final (F-107, team statement). The submitted design assigns evidence authority to the LLM, calibrated prediction to a separate decision model, and action selection/sizing/execution to deterministic code. It includes bounded retrieval, claim verification, thesis memory, event planning, logging and recovery.

Declared values include a five-US-session forecast horizon, trailing 60-session volatility sizing, at most four positions, 20% per name and 80% gross, a 50 bp one-way entry-cost ceiling, and validation against round-trip costs plus a 50 bp buffer. The portfolio loss ladder is 3% daily loss → no new positions for the UTC day; 8% peak drawdown → no new positions; 12% → gross at most 40%. These are declared team commitments, not exchange-prescribed optimal parameters. The submitted full-pipeline rehearsal is five-plus days including a weekend; the shorter signer-on schedule remains unreconciled (GAP-04).

**V2 [V].** The captured challenge page proposes final equity return, drawdown as a tie-break, and no scoring points for trade count (F-43/F-45/F-50). The later organiser chat includes completed-trade PnL, drawdown, logs and repository, and rejects no trading (F-115). No numerical minimum activity or scoring weights have been supplied; Q-39 remains open. Do not reduce this to “volume does not matter” or invent a trades/day requirement. F-117 settles no new versions after development; exact scored-window instants and same-version restart policy remain Q-06/Q-40. First-gas readiness is not established by the reported funding expectation (GAP-41/Q-03).

**V3 [V].** This checkout contains probes/fetchers and specifications, not a production trading agent, signer/journal/recovery implementation or automated test suite. All non-vendored Python source was inspected. External or unmerged implementation was not inspected. “Adopted” in the plan is distinct from implemented or tested. Reading the specification cannot establish current profitability or readiness.

## 2. Verdict by idea

| Idea | Keep | Change / conclusion |
|---|---|---|
| **012** | Slow evidence assessment separated from deterministic execution; cost awareness; new-evidence discipline | Useful design candidate, not a complete trading policy. Top-three probability under guessed rivals is a different objective from net profit. Do not adopt high-volatility selection, cap-level targets or the +6% conditional flatten on this evidence. The −15% floor, LLM action schema and round-based filing watermark were already corrected by 015/016. |
| **013** | R1–R8: signing integrity, economic payload verification, durable ingestion, authority boundary and tool defects | Strongest immediate engineering review. R3/R4 are accepted in draft, not implemented. Static inspection confirms R5–R8 remain in the tools. Preserve R1/R2 as activation requirements. |
| **014** | Costs first; one frozen baseline; evaluate the entire paired portfolio, including blocked trades, cash and missed upside; test novel evidence after detection latency | Best research framework for U1. Specify its inconclusive default and baseline lifecycle. A maximum of two variants is a ceiling, not an obligation to build both. |
| **015** | Assessment-only schema, durable queue, fixture checks, honest novelty limits and prioritizing the baseline | Reject automatic deployment of an unvalidated exit-only overlay merely because the result is inconclusive. A fixed median-cost waiting rule is still a timing policy with opportunity cost. Sparse events warrant counting/power analysis, not a categorical impossibility claim. |
| **016** | Independent mandatory-risk path; declared 3/8/12% ladder; exposure decision separated; corrected cost accounting; cautious interpretation of candle statistics | Necessary corrections, but the cap-trim and minimum-size rules still need an economically workable portfolio policy. “Band ≥ minimum/equity” is a feasibility condition, not an optimal rebalancing rule. |

## 3. Findings that matter for profit and regular justified activity

### R1 [P1] Complete the entry and re-entry policy before implementing the overlay

**Locations:** IDEA-012 §8.1/§9; IDEA-015 A.1/B1; GAP-08/GAP-11.

The suggested map sends adverse held names to EXIT, adverse unheld names to ENTRY_BLOCK and everything else to HOLD. ENTER after EXIT is explicitly unresolved. Combined with the new-event restriction and sparse filings, the book can sell down and never rebuild despite later eligible opportunities. Conversely, IDEA-009's next-round re-entry can buy back immediately unless “still current” evidence has a precise meaning. Neither is a complete lifecycle. [V/I]

**Recommendation [R]:** specify initial entry, incremental buys, candidate ranking, expiry/renewal at the horizon, exits, and re-entry in one state machine. An adverse state must persist until its predefined invalidation or expiry rule; a verified adverse fact must not disappear just because a timer expires. Expiry makes a name eligible for reassessment, not automatically eligible to buy. Re-entry requires the baseline entry conditions, fresh valid evidence where required, remaining holding time, affordable execution, risk capacity, and no active block. Repeated evidence must not cause repeated exits or automatic sell/buy oscillation. A new favorable statement is not by itself proof of a profitable entry.

### R2 [P1] Separate expected profit from tournament variance

**Locations:** IDEA-012 §3/§4.3; IDEA-016 §3.2; D-12.

IDEA-012's toy tournament expressly leaves expected return approximately unchanged while changing top-three probability through variance. It cannot establish a profit-maximizing allocation. Selecting the four most volatile names is not evidence of higher expected net return, and four correlated technology holdings are not four independent bets. IDEA-016 correctly defers that decision. [V/I]

**Recommendation [R]:** retain declared sizing as the provisional constraint set, not as a claimed optimum. Compare prospective policies after costs at comparable exposure/risk, and disclose when gains come from more market exposure. Do not replace return evidence with the uncommitted tournament simulation. If tournament prize probability becomes the objective, record that as a separate user/team decision; it is not U1.

### R3 [P1] An exit-only overlay is not automatically a safe economic fallback

**Locations:** IDEA-015 B1/B4; plan H-02; IDEA-005 R4; GAP-54.

Correctly extracting bad news does not establish that selling after detection improves the remaining return. Selling after a repricing can pay costs, miss a recovery, and leave cash idle. An entry veto can miss gains. Smaller exposure after an exit does not prove lower realized drawdown across all paths. EDGAR latency makes this question harder; it does not establish the value of exit-only use. [I]

H-02 requires each variant, including the veto variant, to be evaluated on its own criterion. The proposal says evidence-assisted trading depends on passing held-out validation. Declaring an overlay “not validated for edge” is honest reporting but does not itself satisfy those commitments. [V]

**Recommendation [R]:** pre-register one default before evaluation. If an optional predictive overlay is inconclusive, retain the specified baseline and keep its new assessments in shadow unless a separately justified and explicitly adopted risk policy governs them. A narrow factual-risk rule still needs evidence-correctness and operational tests, a stated economic tradeoff, and any required deviation record. Do not ship a sentiment-driven rule simply to make LLM output cause trades. The baseline itself also needs an explicit return premise, costs and acceptance decision; a buy-and-hold comparator is not automatically a validated profit strategy. If no defensible policy is ready, flag that before activation rather than manufacture volume.

### R4 [P1] Cap-level targets plus unrestricted cap trims can create expensive micro-trades

**Locations:** IDEA-012 §8.2 H5; IDEA-016 §3.1/§3.4; GAP-10/13/50.

**Example [A]:** with 200 USDT equity, a 40 USDT holding is exactly at 20%. A 1% rise in that name, all else unchanged, produces 40.4 / 200.4 = 20.16%. A trim back to exactly 20% is about 0.32 USDT before execution costs. At the kit's historical 0.02–0.035 USDT approve-plus-swap gas example, gas alone is approximately 6.3–10.9% of the trim. Those gas numbers are illustrative, not current measurements. Repeated small rises can repeat the trade because safety trims bypass the band, minimum and daily cap. Gas/spread also reduce equity, so sizing from pre-cost equity can leave a cap breached after the trade. [I]

**Recommendation [R]:** distinguish hard maximum weights from lower operating targets; reserve room for costs and plausible drift. When reducing a breach, target a defined interior weight using conservative post-cost equity rather than repeatedly returning to the exact boundary. Do not solve this by ignoring a hard-cap breach. Venue minimums, unavailable routes and closed markets still constrain execution: queue and report the unresolved breach with bounded retries, never assert a guaranteed fill.

IDEA-016's 7.5–12.5 percentage-point band follows from 15–25 USDT / 200 USDT, but is very wide relative to a 10–20% position. It can suppress most discretionary adjustments. Choose minimum order, target sizes and band jointly from actual quote costs and the policy's economic benefit. Check both development and final funding sizes; a fixed 25-USDT minimum can prevent the declared base book from being built at all (IDEA-010/011).

### R5 [P2] Remove arbitrary profit lock-in and make the clock part of state

**Locations:** IDEA-012 §4.6/§8.1 N2–N3/§8.2 H8; D-04/D-12.

No supplied evaluation supports flattening at +6% by Nov 10 while keeping exposure otherwise. Accumulated profit alone does not establish the value of the next holding interval. [V/I] **Recommendation [R]:** use a precommitted terminal liquidation schedule and last-entry horizon based on Q-06 or the documented conservative window assumption; apply the declared drawdown controls separately. Keep an additional profit-lock rule only as an explicit, separately justified risk preference.

Also resolve state transitions independent of fresh news: initial build, thesis expiry, a matured re-entry condition, a cost gate reopening and approaching the terminal window. A “no new event” HOLD must not silently prevent these code-defined transitions. For N2, resetting the price anchor every LLM round can miss a cumulative move made through sub-threshold steps; define a durable reference and reset condition. N3's calendar time only signals that a release is due: it is not the released evidence. Missing release data must remain missing.

### R6 [P2] Keep voting optional and verify meaning, not just quoted text

**Locations:** IDEA-012 §8.4; IDEA-015 A.1/A.3; IDEA-016 §2; G-53.

Five samples from one model share failure modes. A 4/5 tally is repeatability, not an 80% probability of being correct or profitable. IDEA-015/016's fixture checks are the right correction. A quoted span can exist without supporting “material adverse” or “thesis broken”; those fields remain judgments unless tied to a predefined falsifier and checked semantic/numerical interpretation. [I/R]

Compare a single assessment with voting on frozen human-labelled fixtures: unsupported claim acceptance, missed material evidence, factual/numerical correctness, latency and failure rate. Add voting only if it earns its extra complexity. Scheduled thesis reviews may be useful, but more calls or longer reasoning logs do not create financial edge. Retain the declared evidence loop and record scope changes honestly.

### R7 [P2] Cost-based waiting needs a complete execution policy

**Locations:** IDEA-014 §1–2; IDEA-015 B2/B3; tools/probe_quote.py.

Trading at the first quote below a historical median can miss an opportunity while price moves, wait through an unavailable route, or reach a deadline with costs still above the hard entry ceiling. Lower quoted cost alone is not higher portfolio profit. [I]

**Recommendation [R]:** prioritize cost/availability measurement. If timing research is cut, use a simple frozen execution rule with a bounded deadline and explicit skip behavior when entry requirements remain unmet. The median cannot override the entry cap, freshness or integrity. Compare waiting with immediate eligible execution including missed trades and price movement; absent that evidence, label the rule an engineering heuristic, not alpha. Mandatory risk exits do not wait for a cheaper discretionary slot.

R7 diagnostics need not block otherwise successful read-only collection, but all authentication errors must fail visibly without suggesting a restriction bypass. R8's backoff parsing, durable result capture and rate-limit budgeting matter before unattended collection. Quotes for 10/25/40 USDT are a useful start, not a substitute for samples at the actual intended portfolio sizes or for realized fills. Capture both market-state endpoints and failures.

### R8 [P2] Consolidate risk precedence and reset rules into one executable specification

**Locations:** IDEA-013 R1/R2; IDEA-016 §3.1; GAP-12/15/63/64.

Recommended precedence [R]: **signing identity/version/payload/reconciliation and executable-market requirements → mandatory portfolio-risk/terminal reductions → evaluated discretionary evidence actions → baseline entries/re-entry/rebalancing**. The risk monitor must not wait on an LLM vote or its timeout. Mandatory reductions may bypass strategy cost/size/cadence filters; they cannot bypass signing integrity, market closure, valid quotes or reconciled holdings. Evidence-driven exits are not automatically “safety” actions just because they sell.

Specify whether adding to a held position counts as new risk (recommend yes), daily versus peak-drawdown resets, recovery conditions, exit retry bounds, and what wins when events coincide. “No new positions” must not become a loophole for adding risk to existing ones. D-11/D-12 still contain older recommendations alongside corrections; implement only from a single reconciled spec, with explicit version/deviation decisions.

### R9 [P2] Preserve uncertainty and reproducibility in the research claims

**Locations:** IDEA-012 §1–2/§4.3/§4.7; IDEA-015 B1; IDEA-016 §3.3.

The cited candle file and calculation/tournament scripts were not reproduced here. Record a snapshot hash and commit calculation code before using their results for D-12. Off-hours variance share must be normalized by actual sampled hours and missing-bar rules. A share of 73–82% versus approximately 81% of time does not prove identical hourly variance: using those approximate denominators gives an off/on hourly ratio of roughly 0.63–1.07 [A]. Negative autocorrelation is consistent with bounce, not proof of a taker-tradable reversal or a complete explanation of it.

IDEA-015's “cannot be met” validation claim is too strong without the selected model's cutoff, eligible event count, effect size and dependence assumptions. An execution-timing MDE cannot simply be transferred to a different event-overlay test. Plan for an inconclusive result; distinguish NOT RUN from inconclusive. Neither implies permission to deploy the untested variant.

## 4. What to measure for U1

Freeze definitions before evaluating a policy; these are recommended metrics, not a registered experiment:

| Measure | Definition / use |
|---|---|
| Primary profit | Terminal portfolio equity minus opening equity, with realized and remaining-position value, gas, fees, reverts and liquidation costs reconciled. Report BNB treatment separately until Q-39 resolves it. |
| Risk | Peak-to-trough portfolio drawdown, gross/name exposure and correlated exposure; distinguish measured paths from scenario assumptions. |
| Executed volume | Successful bStock buy USDT spent and sell USDT proceeds per tradable session, reported separately and together. Gas top-ups, approvals, reverts and HOLD logs are not successful bStock trading volume, though their costs still count. |
| Opportunity capture | Qualifying opportunities under the frozen policy versus executions; classify misses as no route/market closed, cost, evidence block, risk capacity, lateness or system failure. Log candidates before downstream rejection so the denominator cannot hide failures. |
| Lifecycle | Completed round trips, open positions, time in cash, time since last eligible trade, and how blocks expire or are resolved. A no-trade session is not automatically a failure. |
| Policy comparison | Paired net portfolio result versus the frozen baseline and a cash reference; hold constraints comparable and include missed upside. A cash benchmark does not by itself meet F-115. |

Do not lower the cost hurdle to hit a volume target. If valid opportunities are rare, improve or broaden the tested opportunity policy within the eligible universe; report scarcity honestly. Consistent scanning and reliable execution are controllable; profitable opportunities and daily fills are not guaranteed.

## 5. Order of work and remaining owners

Individual assignments remain subject to GAP-37; the following follow the proposed functional leads.

1. **Isaac + Yao Zhu; team adoption by D-11/D-12:** freeze the objective, baseline, complete lifecycle, risk precedence, exposure and inconclusive default. Record disagreements and proposal deviations; GAP-08–13/54/62/64. Keep the existing Oct 11 direction / Oct 19 baseline / Oct 22 parameter deadlines visible; dates are plans, not proof of capacity.
2. **Keegan + Isaac + Keith:** repair unattended quote collection, record both open-state endpoints and costs at intended sizes, then establish realized execution evidence through the versioned test path once funding/gas and signing prerequisites are satisfied; GAP-41/44/47/49/50/63.
3. **Yao Zhu + Keegan:** durable evidence queue, text/byte correctness, falsifier-linked assessment/verifier fixtures; optional voting only after the comparison; GAP-24/26/28/63.
4. **Keith + Keegan:** payload validation, single-wallet transaction state, WAL/reconciliation, every-path round logging, restart and failure tests; GAP-29–36/46–48. No strategy finding substitutes for these activation requirements.
5. **Team:** preregister research before running it; evaluate only feasible variants; preserve the full declared rehearsal or record an explicit change, then freeze; GAP-04/05/16–22/38/62. No tuning on development-wallet PnL.

## 6. Sources, checks and limits

**Project coverage [V]:** read the core skill, plan and all reference files; the proposal answers and all three architecture-PDF pages; the ledger's IDEA-001–016 and EXP-001–004 histories; the backlog and repository instructions/READMEs; the verbatim captured challenge page and participant-kit documents, including all 18 guide-PDF pages; non-vendored Python tools and dependency declarations. Binary dependency internals and private datasets were not exhaustively audited. This was a full specification review, not a full security audit or replication.

**Rule check [V]:** compared the captured page's Stage 2/rules text and kit's trading/logging/preflight text with SKILL.md F/K/Q, including the settled organiser replies and answered-in-practice notes. The live DoraHacks page returned HTTP 405 to the browser check; no newer official scoring text is claimed. Current rule conclusions rely on the repository's captured sources and recorded replies.

**Primary literature checked 2026-10-10:** [Lopez-Lira and Tang, arXiv v6](https://arxiv.org/html/2304.07619v6), abstract/introduction and transaction-cost appendix: the initial-reaction hit rate is non-tradable; later drift is stronger in small stocks and negative news. Their overnight-news strategy becomes unprofitable at 20 bp round-trip costs; that result does not describe every strategy in the paper or establish returns for these five long-only tokens. Header/manuscript dates differ, so pin a source version for replication. [Wang et al., self-consistency](https://arxiv.org/abs/2203.11171), abstract: arithmetic/commonsense reasoning benchmarks, not calibrated financial confidence. The remaining IDEA-012 literature summaries were not individually re-verified and are not promoted to established facts here.

**Documentation checks, specified before execution:** require `git diff --check` to pass, new local Markdown links to resolve, the new IDEA ID to be unique, only intended documentation to be staged, and no secrets/data/code changes. This is documentation validation, not a trading experiment. No existing backlog item is completed merely by recording this review.

**Verification results (2026-10-10):** `git diff --check` passed; local Markdown links in all four changed documents resolve; IDEA-017 and GAP-64 each appear once in their indexes; the changed/untracked file set is exactly this review, `docs/LEDGER.md`, `docs/INCOMPLETE_WORK.md` and `docs/skill/larp/plan.md`. Only documentation changed; no secrets, data or application code were added. Final staging is restricted to these four paths. No runtime-readiness or profitability claim follows from these checks.

# IDEA-019 — Consolidated recommendations from the review of IDEA-012–017

- Date / author: 2026-10-10 (SGT) / Codex, requested by Isaac.
- Status: open — **recommendations, not adopted policy or trading authorization**.
- What: record the session's review of IDEA-012–017 and the decisions needed to turn their evolving design into one implementable specification.
- Why it might help: separate engineering readiness, evidence quality and financial benefit; resolve contradictory rules before building the frozen agent.
- Cost / risk: documentation and source review only. No credentials read, probes executed, models evaluated, transactions signed or audit logs uploaded. Existing market measurements and tournament simulations were not reproduced.
- Links: [IDEA-012](IDEA-012.md), [IDEA-013](IDEA-013.md), [IDEA-014](IDEA-014.md), [IDEA-015](IDEA-015.md), [IDEA-016](IDEA-016.md), [IDEA-017](IDEA-017.md); [plan](../skill/larp/plan.md) D-08/D-11/D-12, H-02; [backlog](../INCOMPLETE_WORK.md) GAP-08–15/24/26/28/44/50/54/62/63/64.
- Scope boundary: IDEA-018 is reserved for the partner's work, per Isaac's instruction. It was not reviewed, created or edited here. This entry records the prior review; it does not replace the source entries or adopt their recommendations.

Labels: **[V]** source checked; **[A]** illustrative arithmetic, not a measured result; **[R]** recommendation.

## 1. Overall assessment

[R] IDEA-012 provides a useful architectural direction, IDEA-013 identifies urgent engineering defects, and IDEA-014 supplies the strongest evaluation framework. IDEA-015/016 repair important mistakes; IDEA-017 is the best basis for consolidating them. Together, they still do not define a complete, validated trading policy. Accepted review findings are not implemented fixes.

| Idea | Keep | Change / conclusion |
|---|---|---|
| 012 | Evidence assessment separated from deterministic execution; cost awareness; reaction to newly available evidence | Do not implement the original rules wholesale. Its LLM action schema, filing watermark and −15% floor were subsequently corrected. High-volatility selection and the +6% profit lock lack supporting evaluation. |
| 013 | Signing integrity, economic payload validation, durable ingestion and the eight concrete findings | Implement and verify the findings before using affected paths. Funding or credential access does not establish readiness. |
| 014 | Costs first; one frozen baseline; paired portfolio evaluation including missed upside, latency and cash | Specify the baseline and inconclusive default. Research variants must fit actual build and evaluation capacity. |
| 015 | Assessment-only output, durable filing queue, labelled fixtures and explicit novelty limits | Reject automatic deployment of an unvalidated exit overlay. Median-cost waiting needs bounded waiting and opportunity-cost accounting. |
| 016 | Independent safety path, declared loss ladder, corrected costs and cautious measurement interpretation | Resolve operating targets and cap trims. Safety exemptions from minimum size can otherwise create repeated expensive tiny sells. |
| 017 | Complete lifecycle, justified trading activity, conservative evidence interpretation and consolidated precedence | Turn recommendations into specific decisions. It identifies gaps but does not supply the missing entry strategy or demonstrate profitability. |

## 2. Policy recommendations

### R1 — Specify the return premise and complete entry lifecycle first

[V/R] The corrected architecture can assess evidence, block entries and exit positions, but still needs initial selection and entry, incremental-buy semantics, candidate ranking, position expiry and thesis renewal, re-entry, and adverse-block clearing rules. Explain why the expected remaining return justifies costs; neither a favourable assessment nor a simple baseline establishes that premise.

Without rebuilding rules, the book can sell into cash and never recover exposure. Clearing blocks too easily can instead cause repeated sell/buy cycles. An expired block should trigger reassessment, not automatically a buy; a still-valid adverse fact must remain represented. Resolve this under D-08/D-11/D-12 and GAP-08/11/28/64 before implementing the overlay.

### R2 — Pre-register the inconclusive default; do not automatically ship an exit overlay

[R] Disagree with IDEA-015 B1's automatic bounded exit-only fallback. Verified adverse evidence does not establish that selling after detection improves remaining returns: the price may already reflect the news, and selling can incur costs and miss a recovery. Describing the overlay as not validated for edge reports uncertainty but does not justify deployment.

Pre-register the baseline and fallback before evaluation. Keep an optional predictive overlay in shadow if its evaluation is inconclusive, subject to the baseline's own acceptance decision. A separately adopted factual-risk policy needs explicit triggers, economic tradeoffs, evidence-correctness and operational tests, and proposal-deviation records where required. Do not manufacture trades to make the LLM visibly influential.

[R] IDEA-015's categorical claim that validation cannot finish before the freeze needs event counts and power analysis. Distinguish **NOT RUN**, **INCONCLUSIVE** and **NOT SUPPORTED**. None automatically authorizes a variant. Sources: H-02, IDEA-017 R3/R9, GAP-54/64.

### R3 — Design position targets, costs, bands and minimum sizes together

[A] At 200 USDT, a five-percentage-point adjustment is 10 USDT, below the proposed 15–25 USDT minimum. IDEA-017 R4 also shows that a 40 USDT holding rising 1%, with other holdings unchanged, becomes 40.4 / 200.4 = 20.16% of equity; returning to exactly 20% requires about a 0.32 USDT trim before costs. Repeating those trims can consume substantial gas relative to their size.

[R] Use operating targets below hard caps and a defined interior trim target based on conservative post-cost equity. Choose position sizes, minimum orders and discretionary bands jointly for both development and final wallet sizes. Hard breaches still need a reduction policy with executable-market checks, bounded retries and explicit unresolved status when execution is unavailable. A feasibility inequality is not an optimal rebalancing rule. Sources: IDEA-016 §3.4, IDEA-017 R4, GAP-10/13/50/64.

### R4 — Keep voting optional and test semantic support

[R] Five samples from one model share failure modes. Four agreeing samples show consistency, not financial correctness or an 80% calibrated success probability. Compare single assessments and voting on frozen labelled fixtures covering factual/numerical correctness, unsupported claims, missed material evidence, semantic support, latency and failures. Add voting only if the comparison justifies its complexity.

Checking that a quotation exists does not establish that it supports a material adverse impact or a broken thesis. Tie those judgments to predefined falsifiers and verify their interpretation. The cited [self-consistency paper](https://arxiv.org/abs/2203.11171) evaluates arithmetic and commonsense reasoning benchmarks; it does not validate financial confidence. Sources: IDEA-015 A.3, IDEA-016 §2, IDEA-017 R6, GAP-26/63/64.

### R5 — Consolidate action precedence and terminal policy

[R] Mandatory portfolio reductions must bypass discretionary voting, cadence, bands and profitability filters while satisfying signing identity, version, payload validation, reconciliation and executable-market requirements. The risk monitor must operate independently of LLM latency or failure. An evidence-driven sell is not automatically a mandatory safety action.

Keep the declared 3% daily-loss / 8% drawdown / 12% drawdown ladder as the current commitment unless explicitly changed; the −15% replacement was withdrawn in IDEA-016. Specify reset conditions and whether adding to existing holdings counts as new risk (recommend yes). Use a precommitted terminal schedule and last-entry horizon; the +6% conditional profit lock lacks supporting evaluation. Exact scored-window instants remain Q-06, so any conservative timestamp must be labelled an assumption. Sources: IDEA-013 R1/R2, IDEA-016 §3.1–3.2, IDEA-017 R5/R8, GAP-12/15/64.

### R6 — Separate exposure choices from evidence of profit

[R] More exposure or higher-volatility selection can change outcome variance without demonstrating higher expected net profit. Do not use the uncommitted tournament simulation to justify D-12. Retain the declared sizing as the provisional constraint set, not a claimed optimum; compare prospective policies at comparable exposure/risk and disclose exposure-driven differences.

Use IDEA-017 U1's objective: net profit within declared constraints, with regular trading when opportunities justify costs. HOLD logs demonstrate operation, not executed volume. Measure qualifying opportunities and missed executions as well as successful trades; no guaranteed daily fill quota follows. Sources: IDEA-017 R2/§4, F-115/Q-39, GAP-64.

## 3. Engineering and research order

[V] Static inspection during this review confirmed that IDEA-013 R5–R8 remain in the current tools: EDGAR table cells lack separators; saved text uses default encoding while its hash uses UTF-8; quote-probe 401/403 responses are classified as host refusal; and Retry-After is parsed only as an integer. No runtime reproduction is claimed. GAP-63 already tracks these findings.

[R] Recommended sequence:

1. **Isaac + Yao Zhu, team adoption:** resolve D-08/D-11/D-12 into one specification covering objective, baseline lifecycle, evidence authority, exposure, fallback and terminal policy. Suggested roles only; individual assignments remain GAP-37.
2. **Keegan + Isaac + Keith:** fix affected GAP-63 paths and collect repeated quote/state evidence at intended position sizes, including both market-state endpoints, failures, latency and gas. Simulated quotes are not realised fills.
3. **Keith + Keegan, with Yao Zhu on evidence:** implement and verify payload validation, durable ingestion, execution state, reconciliation, every-path round logging and independent risk monitoring. Required exits never wait for a cheaper discretionary slot.
4. **Isaac + Yao Zhu:** pre-register and evaluate one narrow evidence variant against the frozen baseline. Include blocked allocations, cash, missed upside, detection latency and all costs. Add voting only if fixture evidence justifies it. Never tune on development-wallet PnL.

If discretionary timing research is cut, a frozen cost-based execution rule still needs a deadline, explicit skip behaviour and the hard entry ceiling. Lower quoted cost alone is not higher portfolio profit. These recommendations narrow existing work; they do not register an experiment or complete GAP-63/64.

## 4. Sources and limits

[V] Reviewed IDEA-012–017, including IDEA-012's appended corrections, the ledger index, relevant backlog and plan decisions, submitted proposal text, current EDGAR/quote-probe source, and relevant captured official page and participant-kit trading/logging text alongside SKILL.md F/K/Q records. Rule conclusions use repository captures and recorded organiser replies; no newer organiser announcement was verified.

Primary literature checked during the session: [Wang et al., self-consistency](https://arxiv.org/abs/2203.11171), abstract; [Lopez-Lira and Tang, arXiv v6](https://arxiv.org/html/2304.07619v6), relevant initial-reaction, drift and transaction-cost passages. Neither source establishes profitability for this five-token policy. Other IDEA-012 literature claims, private candle captures and tournament simulations were not independently reproduced.

Documentation checks specified before execution: require `git diff --check` to pass, local links in the new entry to resolve, IDEA-019 to have exactly one ledger row, and only the intended documentation files to change. No checklist item is completed by recording this review. Verification evidence is appended after the checks.

- Verification results (2026-10-10): `git diff --check` passed; all local links in this entry resolve; the index contains exactly one IDEA-019 row. The changed file set is this entry, `docs/LEDGER.md` and `docs/INCOMPLETE_WORK.md` (GAP-64 cross-reference). No code, credentials, datasets or IDEA-018 files changed. These are documentation checks, not evidence of runtime readiness or profitability.

## 5. Candidate trading policy for the winning objective (2026-10-10 follow-up)

**[U] Isaac's follow-up:** recommend a trading policy to maximize chances of winning; IDEA-018 does not exist and its absence is fine. This changes the recommendation's objective from net-profit-first to prize placement subject to eligibility and audit. No policy, experiment or parameter is adopted by this request.

**[R] Recommendation:** a low-turnover, volatility-sized long/cash base portfolio, with meaningful market participation, bounded evidence assessment and independent deterministic risk/execution controls. This is a defensible starting candidate under uncertain scoring, not a demonstrated optimizer of top-three probability. Scoring weights, competitors' policies and conditional market returns are not known. In particular, retaining declared sizing is justified by current commitments and lack of evidence for changing it, not proof it maximizes prize probability.

| Policy area | Candidate recommendation |
|---|---|
| Objective | Complete an eligible, fully auditable scored run with competitive net returns and controlled drawdown. Revisit exposure before the freeze when Q-39 is answered; never adapt it to development PnL. |
| Base portfolio | Up to four eligible bStocks. Admit only names with sufficient trustworthy inputs, functioning evidence coverage, executable routes and affordable entry/exit. If more than four pass, prefer reliable availability and lower measured round-trip cost under a frozen ranking rule; do not rank by volatility alone. Correlation remains a portfolio risk. Exact ranking and missing-data rules need adoption. |
| Sizing | Retain the declared weight formula: `1% / (2 × sigma_5session)`, where `sigma_5session = trailing 60-session daily volatility × sqrt(5)`. Enforce four-position, 20%-per-name and 80%-gross caps, with operating headroom below hard caps and gas/cost reserves. The existing 42–54% gross estimate is illustrative; actual weights depend on trustworthy current data and cost feasibility. Missing inputs do not justify silently substituting an unregistered sizing method. |
| Initial entry | Build the adopted base portfolio autonomously only after integrity, market-state, freshness, reserves, cost and risk gates pass. This is a proposed market-participation default, not a validated catalyst signal. Its return premise and acceptance, plus any departure from the submitted calibrated-model approach, must be explicit under D-08/D-11/D-12 and GAP-62 before activation. |
| Holding and review | Multi-session holds; reassess at the declared five-US-session horizon and on material new evidence. Horizon expiry triggers review, not an automatic sell and rebuy. Maintain the position while its adopted baseline conditions remain valid and no mandatory reduction applies. |
| Discretionary trading | At most one discretionary portfolio rebalance per defined session as a provisional engineering limit, not a quota. Execute only when the frozen economic rule justifies all incremental costs; derive minimum size from measured gas/spread/impact at actual intended sizes. No intraday price-bounce trading or routine daily churn. Define the session clock before adoption. |
| LLM role | Retrieve and verify evidence, maintain thesis/falsifier memory and emit assessments with supporting spans and uncertainty. Code owns actions and sizing. Keep optional predictive entry/veto/exit effects in shadow if their evaluation is not run or inconclusive. A separately adopted factual-risk rule needs explicit falsifiers, tradeoffs and tests; adverse tone alone is insufficient. The agentic evidence harness remains substantive even when optional predictions are shadowed. |
| Re-entry | Require a fresh reassessment, explicit resolution of any adverse block, baseline eligibility, risk capacity, affordable execution and enough remaining holding time before the terminal cutoff. Neither a timer nor an LLM change of mind alone clears a block. No immediate automatic buyback after an evidence exit. |
| Risk | Retain the declared 3% UTC-day loss / 8% peak drawdown entry halts and 12% drawdown reduction to at most 40% gross. Treat additions to held positions as new risk. Specify reset conditions before implementation. Mandatory reductions run independently of the model and discretionary cadence/size filters but never bypass integrity or market-state checks. |
| Caps and trim costs | Operate below hard caps; reduce breaches to an adopted interior target using conservative post-cost equity. Avoid repeated tiny boundary trims without ignoring the breach. Bounded retries and unresolved-state reporting apply when execution is unavailable. Exact headroom is a cost/stress-based parameter decision, not supplied as a guessed optimum here. |
| Terminal policy | Precommit a last-entry cutoff and autonomous liquidation schedule inside the confirmed scored window or an explicitly conservative assumption, with retry time reserved. No unsupported +6% profit-lock rule. Flattening aims to make completed-trade and terminal-equity readings more comparable; exact valuation/scoring treatment remains Q-04/Q-06/Q-39. |
| Execution/audit | One wallet transaction in flight; durable intent before signing; approve/confirm/requote flow; decoded economic-payload validation; nonce/receipt reconciliation; every-path round logging and swap hashes. No order when either required market-state check reports closed. Funding/gas and production readiness remain separate activation gates. |

**[R] Exposure escalation is conditional.** If confirmed rules principally rank terminal equity with drawdown only a tie-break, stronger exposure can be considered as an explicit tournament choice within declared caps. If drawdown materially affects score, the incentive differs. Neither branch establishes that maximum gross or selecting the four most volatile names is best; preregister assumptions and compare scenario sensitivity, costs and drawdown before deciding. Do not claim the unavailable IDEA-012 tournament script validates escalation.

**[R] Source of potential return:** the base candidate mainly takes equity-market risk through eligible tokens; its success depends heavily on the realized market path. Reliable execution and reduced costs protect the outcome but do not establish predictive alpha. A separate evidence overlay must demonstrate incremental value after detection latency and costs before receiving discretionary trade authority through the registered code map. The [Lopez-Lira and Tang paper](https://arxiv.org/html/2304.07619v6) supports caution: its initial-reaction accuracy is non-tradable and its subsequent drift results are particularly associated with small stocks and negative news, rather than establishing this five-token long-only strategy.

**[V] Checks for this follow-up:** re-read the declared parameters, proposal validation commitment, captured page scoring/rules, kit market-state/logging text, recorded organiser scoring/freeze answers and relevant backlog. Attempted a live DoraHacks fetch; it returned HTTP 405, so no new scoring confirmation is claimed. IDEA-018 is not indexed in this checkout. No balances, live quotes, private datasets or forecasts were checked. The candidate remains incomplete until the named parameter/lifecycle/acceptance decisions and activation tests are recorded; GAP-64 remains open.

Documentation validation for this addition: require `git diff --check`, resolving local links, one IDEA-019 ledger row, and changes restricted to this entry and its existing ledger row. No experiment is executed or checklist item completed by this addition.

- Follow-up verification results (2026-10-10): whitespace and local-link checks passed; exactly one IDEA-019 ledger row remains. Only `docs/ledger/IDEA-019.md` and `docs/LEDGER.md` changed. The addition is uncommitted; no policy was adopted or run.

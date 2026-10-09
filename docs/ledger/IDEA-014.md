# IDEA-014 — Improving edge: costs first, then a narrow evidence overlay

- Date / author: 2026-10-09 / Codex, requested by Keegan.
- Status: open — recommendations only; no strategy adoption, experiment execution or trading authorization.
- What: prioritize a small research program that separates lower execution costs, incremental prediction and increased market exposure.
- Why: the current expected-return arithmetic is a scenario estimate, not demonstrated alpha; adding model complexity or gross exposure alone does not validate an edge.
- Cost / risk: desk research only; no credentials accessed, probes run, models trained or trades placed. Historical-data rights, model hindsight, small samples and measurement latency can invalidate results.
- Links: IDEA-005 R1-R9; IDEA-010; IDEA-012; IDEA-013 R1-R8; EXP-001/002; GAP-16/17/21/24/26/44/50/54/63; D-08/D-11/D-12; G-46.

## 1. Recommended order

1. **Measure execution costs and availability.** After fixing IDEA-013 R7/R8, collect repeated buy and matching-quantity sell quotes for all five names at representative sizes (e.g. 10, 25, 40 USDT), together with both market-state endpoints, timestamps, latency, failures and gas estimates. Use fixed sampling across sessions and weekends; event-triggered observations require a recorded sampling rule and rate-limit budget. Report median and adverse-tail costs per name/size/time, including missing quotes. Quotes are simulated, not fills. Lower estimated cost does not justify delaying mandatory risk exits. Suggested leads: Isaac + Keith; GAP-44/GAP-50.

2. **Freeze one baseline and at most two research variants.** Baseline: a fully specified low-turnover portfolio inside declared limits, including entry, exit, sizing and risk rules. Variant A changes discretionary execution timing only; variant B adds verified evidence-based entry blocks/exits. Hold exposure/risk constraints comparable and record differences. Evaluate each against the baseline, not against zero or the traded subset alone. Retain vetoed allocations as cash and charge missed upside, liquidation and re-entry costs. Freeze thresholds, source snapshots, eligible-population metric, dependence treatment and inconclusive fallback in a committed EXP record before evaluating. Suggested leads: Isaac + Yao Zhu; EXP-001/002 and GAP-54. This entry does not itself pre-register those experiments.

3. **Test economic novelty, not generic sentiment.** Use the LLM to extract a structured change from primary evidence: what is new relative to information previously available, relevant numerical comparisons, affected issuer, supporting spans and uncertainty. Missing prior guidance must remain missing; do not invent a consensus expectation. Fix the EDGAR ingestion/table/encoding problems first (IDEA-013 R3/R5/R6). Code verifies the evidence and maps it to bounded actions. Research question: does an action taken after actual detection and processing latency improve the paired net result? Price movement before detection cannot be counted as obtainable profit. A negative headline or correct explanation is not enough. Suggested lead: Yao Zhu; GAP-24/GAP-26/D-11.

4. **Keep token repricing lag as a gated hypothesis.** EXP-002 may investigate whether token quotes remain favorable after genuinely new evidence. Require actual tradability and executable-size quotes; test the subsequent token return, not the underlying share's already-realized move. Without sufficient independent events and rights-cleared comparison data, report inconclusive. Do not infer arbitrage from cross-venue closing prices. Suggested leads: Isaac + Yao Zhu; GAP-44/EXP-002.

## 2. Proposed evidence gates

- Data quality: source and retrieval timestamps, exact text versions, durable accession deduplication, quote availability and all costs accounted for; corrected extractor fixtures pass before financial testing.
- Operational improvement: compare costs, latency, failures and reproducibility using the pre-specified sampling design; account for opportunity cost in any claim about delaying entry. Lower quote cost alone is not proof of higher total returns.
- Predictive overlay: paired net portfolio return versus the frozen baseline on untouched, rights-cleared data; uncertainty must account for common market shocks and overlapping horizons. A proposed promotion standard is a positive lower confidence bound plus the pre-registered risk limits, with an explicit inconclusive outcome for insufficient evidence. Confidence level, sample requirement and thresholds remain to be specified in EXP-001, not selected after results.
- Historical LLM replay: preserve model-cutoff and memorization checks; a present-day model explaining an old crash does not establish foresight. Broader-company training does not replace an eligible-name evaluation.
- Live development: collect forward data and measure non-P&L operational quality; **do not tune rules, prompts or exposure to development-wallet P&L** (G-46). Forward financial comparisons are descriptive unless the pre-registered governance permits their use; they are not a loophole for refitting. A short profitable streak is not sufficient promotion evidence.
- Voting: five agreeing samples are not five independent confirmations or an 80% calibrated success probability. Compare evidence correctness, robustness and latency on fixed labeled fixtures before adding five-call voting.

## 3. Priorities before the freeze

First fix the integrity/ingestion defects and start the quote/state dataset; next lock baseline, schemas and evaluation criteria. Build only one narrow evidence overlay in parallel with the required execution/logging/recovery path. Avoid spending the remaining window on the unvalidated three-model pipeline, frequent intraday rotation or simulated tournament gains as a substitute for net-return evidence. Exposure and concentration remain separate D-12 decisions.

Illustrative cost arithmetic, not an observed result: reducing per-side cost by 10 bp on four 25-USDT positions bought and sold once saves `4 * 25 * 2 * 0.001 = 0.20 USDT`, or 0.10% of 200-USDT equity, before any timing opportunity cost. This is comparable to the small assumed expected return in IDEA-010; the achievable saving is unmeasured.

## 4. External evidence checked 2026-10-09

- [PRIMARY] Lopez-Lira and Tang, [arXiv v6](https://arxiv.org/html/2304.07619v6), abstract and introduction: distinguishes the non-tradable initial reaction from subsequent drift; effects stronger in small stocks and negative news, with transaction costs limiting practical exploitation. This supports testing an economically narrow hypothesis, not an expected-return claim for five long-only bStocks. The page has inconsistent header/manuscript dates; pin the actual source for any replication (already noted by IDEA-005).
- [PRIMARY] [SEC EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces): opened as the primary ingestion reference. Availability of an API is not evidence of a tradable speed advantage.

No new return experiment or measurement was run. This is a prioritization of existing research threads with proposed gates; individual assignments and strategy choices remain open. Record actual experiment criteria and outcomes separately. Existing backlog items above track the work; none is completed by this note.

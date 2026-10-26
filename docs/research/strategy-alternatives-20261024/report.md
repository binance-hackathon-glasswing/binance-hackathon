# Strategy alternatives: verified gaps and conditional candidates

IDEA-091 / PR276-RV01, reviewed 2026-10-24 SGT against canonical `59c878c0`.
This is research for an owner decision. No strategy, parameter, gas allocation or runtime change is adopted here.
The useful result is a readiness assessment; the available evidence does not establish a profit ranking for the
scored run. Review criteria and findings are in [IDEA-091](../../ledger/IDEA-091.md).

## What the implementation establishes

The service builds `ContextBuilder` without a price-series producer. An S1 instance initialized UP therefore keeps
that trend state when `evaluate_trend` reports `TREND_INPUT_UNAVAILABLE`; it does not receive a fresh trend signal.
Persisted state may differ. A target is not a filled portfolio: evidence, quotes, cash, gas, minimum size and execution
still gate buys. “S1 runs a static 95% book” overstates this finding.

The current live exposure producer supplies Class 2 red-flag evidence and explicitly marks the other limiter inputs
unsupported. It cannot newly produce the inputs needed for SEVERE. This does not prove every persisted limiter state
is NORMAL. The 8% buy stop remains latched by the accounting implementation; PF-02's recovery below 5% is outstanding.
See the [baseline note](notes/current_strategy_baseline.md) for code and policy references.

Minimum size can suppress a requested exposure reduction. For a fully built, equally weighted five-name book at
200 USDT, ignoring reserves and drift, a 95% to 60% target change requests `0.35 × 0.2 × 200 = 14 USDT` per name.
That is below the selected S1 rehearsal candidate's `18.637420 USDT` minimum. This is a conditional example, not a
statement about all profiles, frozen weights or wallet states. Hard name limits, mandatory deep-cut controls and
other exit paths must be evaluated separately; the planner has no ordinary S1 gross-trim line that automatically
repairs every such small target change.

FINAL readiness also requires reconciling the generator with the adopted PF-04 calendar, obtaining actual S1 inputs
and approving exact profile/config/release bindings. These remain in [INCOMPLETE_WORK](../../INCOMPLETE_WORK.md).
Missing series is an implementation gap, not an intentional static-mode decision or an EXP-007 result.

## Execution evidence is dated and incomplete

IDEA-090 records four BUY execution records in run 4: one completed approve-plus-swap, two approval-only aborts and
one abort without a prepared signed attempt. They are not four signed swaps. The generic “encoded swap economics
mismatch/expired” error covers both output and deadline checks; it alone cannot identify a unique price-movement
cause. This review read the retained record and source, without querying the wallet or running another cycle.

PR274's merged source repairs keep the original authorized minimum and permit a bounded follow-up quote. Their
offline source acceptance does not establish later hosted fills, sells or flatten success. The later dev-run F7 and
post-approve checks still need the existing owners and gates. See the [execution note](notes/tokenized_stock_execution.md).

The dated quote summaries supersede neither current exact-size quotes nor fill/fee checks. Historical Roll estimates
from trade prints are not executable spreads, and quote-pair differences are not guaranteed one-way all-in costs.
A single low-gas fill cannot justify reducing the whole-run reserve. The original proposals to change slippage from
8 to 20 bp, attempts from 3 to 5, or the final gas seed from roughly 6 to 4 USDT have no demonstrated joint cost,
latency, loss-bound and qualification case. They remain candidates, with no selected replacement value here.

## Historical and external research does not decide the final strategy

EXP-008's pre-registered underlying-proxy comparison favoured EW over S1 by 0.58 percentage points per 10-session
window at its 25 bp per-side cost assumption. Retain that recorded outcome. It compares different exposure levels,
name sets, weights and a trend rule; it does not isolate equal weighting. Its exploratory decomposition and short
token sample do not establish a future gain from retiring the guard. Token history supplied only four non-overlapping
windows, and static S1 versus EW had the opposite sign from the underlying proxy. Nothing here reruns or supersedes
EXP-008, EXP-007, or the team's S1 decision. See the [portfolio note](notes/portfolio_construction_and_risk.md).

Volatility management, stop/re-entry rules, equal weights, event timing and LLM signals depend on assumptions,
implementation and costs. “Every overlay lowers expected return,” “all timing signals lose after costs,” and
“every code option changes profit by at most 0.1 pp” are unsupported universal or numerical claims. The reviewed
literature supplies conditional mechanisms and leads, not executable forecasts for this five-token basket.
The [timing note](notes/timing_signals_and_events.md) separates verified event schedules from directional hypotheses;
the [competition/LLM note](notes/competition_and_llm_agents.md) separates model results from tournament advice.

Two original notes claimed 200000-draw simulations without committed scripts, seeds, inputs or result receipts.
Those claims are unreproduced and are not accepted ledger experiments. Their probability, drawdown and CPPI tables
are removed from this synthesis and the reviewed notes. The immutable original remains linked below. This review
performed documentation/source checks and deterministic arithmetic only; it ran no strategy simulation or backtest.

## Decisions and qualification work, in dependency order

This order reflects readiness dependencies, not estimated profit or prize probability.

| Work | Owner / gate | What remains uncertain |
|---|---|---|
| Validate merged execution repairs in a later dev cycle, including sells and flatten | Yao/Isaac operations; Keith/Keegan acceptance under IDEA-089/090 | Hosted execution and complete round/transaction reconciliation |
| Reconcile S1 series/limiter semantics, stop recovery and target/minimum feasibility | Keith; Keegan review; PF-IMPL01 and unchanged EXP-007 criteria | Chosen intentional behaviour, actual inputs, cost and full-exit feasibility |
| Reconcile FINAL calendar and build exact profile/config | Keith/Keegan; PF-04; Isaac approval | Session/date boundaries, fresh inputs and signed-child coverage |
| Compare equal weights, inverse volatility or an explicit static alternative if reopened | Yao strategy choice; Keith analysis; team decision ID | Net return and drawdown; no weighting dominance or forecast established |
| Review fixed slippage, attempt budget and gas seed if reopened | Isaac/Keith; recorded exception, coverage and run pins | Adverse movement, expiry, gas/fee ceilings, retry spend and exit headroom |
| Consider signal overlays or architecture changes | Separate registered hypothesis and rights/compliance review | Point-in-time availability, incremental benefit, costs and qualification time |

PF-04's first buy `2026-10-29 14:00`, new-risk end `2026-11-09 21:00`, flatten start `2026-11-10 19:00`, signing end
`2026-11-11 14:45` and flat-by `2026-11-11 15:00` are team POLICY (all UTC), not organiser-imposed deadlines.
The team's Oct 22 parameter cut line and the organiser's final-activation build freeze are different constraints.
A profile-only change still changes a hash and needs decision/deviation, coverage, approval and release work.

## Rules and scoring scope checked

Checked [verbatim challenge page](../../official/source_page.md), [participant trading guide](../../official/kit/bstocks-trading-guide.md),
[participant-kit reference](../../skill/reference/participant-kit.md) and [SKILL](../../skill/SKILL.md) F/K/Q items,
including F-43/115/117/119/120/121 and Q-03/06/39. The page's equity-return formula is proposed; the later organiser
statement considers completed-trade PnL, drawdown, logs and repo together, with weights unresolved. Do not assume
drawdown is only a tie-break in the final assessment, or infer a minimum trade count. Top-three awards do not prove
95% exposure or high-volatility concentration maximizes prize probability without a model of returns, rivals and costs.

F-119 permits 24/7 orders while the `openState` guard remains. S2's implementation is limited to dev rehearsal;
it does not authorize FINAL 24/7 activation. F-120 already settles first-BNB bootstrap before trading/scoring; BNB
valuation remains open. No funding change or new organiser question about bootstrap follows from this report.
Preserve exact-amount approvals, local signing, Web3 API broadcast, authorized minima and qualified gas/cap limits.

Owners retain the existing backlog. This research closes no implementation, experiment, live-run or release gate.

## Provenance and original source leads

The [original research text](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/5d5b5e284fd0e70586ba83767a2d22b0fd726d1e/docs/research/strategy-alternatives-20261024/report.md) is retained immutably.
PR276-RV01 replaces unsupported conclusions and repairs local references. The register preserves the original
external URLs for follow-up; inclusion does not verify availability, quality, rights or any claimed result. Only
sources explicitly assessed above have been rechecked; all other entries remain unverified leads.

- Lead 01: [BscScan](<https://bscscan.com/gastracker>)
- Lead 02: [thetrading.tools](<https://www.thetrading.tools/nvda-options>)
- Lead 03: [MarketChameleon](<https://marketchameleon.com/Overview/TSLA/OptionChain/>)
- Lead 04: [Spark](<https://www.spark.money/glossary/request-for-quote>)
- Lead 05: [DeMiguel, Garlappi & Uppal 2009](<https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html>)
- Lead 06: [Kirby & Ostdiek 2012](<https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/its-all-in-the-timing-simple-active-portfolio-strategies-that-outperform-naive-diversification/05D18E04B226C6E9B8441482CC92F943>)
- Lead 07: [Cederburg et al. 2020](<https://www.lehigh.edu/~xuy219/research/COWY.pdf>)
- Lead 08: [Harvey et al. 2018](<https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf>)
- Lead 09: [Kaminski & Lo 2014](<https://swopec.hhs.se/sifrwp/abs/sifrwp0063.htm>)
- Lead 10: [Lo & Remorov via CXO](<https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth>)
- Lead 11: [farmdoc on Sullivan–Timmermann–White](<https://farmdoc.illinois.edu/assets/meetings/nccc134/conf_2004/pdf/confp23-04.pdf>)
- Lead 12: [Lewellen](<https://faculty.tuck.dartmouth.edu/images/uploads/faculty/jonathan-lewellen/Autocorrelations.pdf>)
- Lead 13: [de Groot, Huij & Zhou](<https://efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2011-Braga/papers/0259_update.pdf>)
- Lead 14: [Medhat & Schmeling](<https://repec.cepr.org/repec/cpr/ceprdp/DP15857.pdf>)
- Lead 15: [Federal Reserve](<https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm>)
- Lead 16: [Kurov et al.](<https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html>)
- Lead 17: [SK hynix](<https://news.skhynix.com/en/?p=13734>)
- Lead 18: [Microsoft](<https://news.microsoft.com/source/2026/10/07/microsoft-announces-quarterly-earnings-release-date-69/>)
- Lead 19: [PrimeXBT on Alphabet](<https://primexbt.com/for-traders/alphabet-earnings-date/>)
- Lead 20: [days.to](<https://days.to/nvidia-earnings>)
- Lead 21: [Martineau 2022](<https://cfr.ivo-welch.info/published/papers/martineau2021rest.pdf>)
- Lead 22: [Lopez-Lira & Tang](<https://arxiv.org/html/2304.07619v6>)
- Lead 23: [CoinPaprika](<https://coinpaprika.com/education/tokenized-stocks-price-tracking/>)
- Lead 24: [Blockworks Research](<https://blockworks-research.beehiiv.com/p/when-markets-sleep>)
- Lead 25: [Frazzini & Pedersen 2014](<https://research-api.cbs.dk/ws/portalfiles/portal/60082899/lasse_heje_pedersen_et_al_betting_against_beta_publishersversion.pdf>)
- Lead 26: [BNB Chain](<https://www.bnbchain.org/en/blog/how-the-goodwill-alliance-slashed-sandwich-attacks-by-95>)
- Lead 27: [BLS](<https://www.bls.gov/schedule/2026/11_sched_list.htm>)
- Lead 28: [The Block](<https://www.theblock.co/post/341215/bnb-chain-will-prioritize-memecoin-transactions-as-gas-fees-surge-400>)
- Lead 29: [Grossman & Zhou 1993](<https://ideas.repec.org/a/bla/mathfi/v3y1993i3p241-276.html>)
- Lead 30: [Gaba, Tsetlin & Winkler 2004](<https://pubsonline.informs.org/doi/pdf/10.1287/opre.1030.0098>)
- Lead 31: [Schwarz & Severinov 2010](<https://ideas.repec.org/a/ucp/jlabec/v28y2010i4p893-922.html>)
- Lead 32: [BigGo Finance](<https://finance.biggo.com/news/5BSX_Z0BaoGGrU-ID27J>)
- Lead 33: [FINSABER](<https://arxiv.org/html/2505.07078v5>)
- Lead 34: [Busse 2001](<https://ideas.repec.org/a/cup/jfinqa/v36y2001i01p53-73_00.html>)
- Lead 35: [BEA](<https://www.bea.gov/index.php/news/schedule/full>)
- Lead 36: [ETF Trends](<https://www.etftrends.com/etf-strategist-channel/turn-month-effect/>)
- Lead 37: [Atlanta Fed](<https://fedinprint.org/item/fedawp/13394/original>)
- Lead 38: [Time Out](<https://www.timeout.com/usa/news/when-do-the-clocks-go-back-in-2026-heres-when-daylight-saving-time-officially-ends-100626>)

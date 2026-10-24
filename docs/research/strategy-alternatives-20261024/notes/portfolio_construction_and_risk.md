# Portfolio construction and risk — conditional comparisons

PR276-RV01, reviewed 2026-10-24 SGT. No weights, risk rule or exposure change is adopted.

## What can be inferred

For fixed weights and one holding interval, expected gross portfolio return is `sum(w_i × E[r_i])`. Equal weighting
versus inverse volatility therefore depends on expected returns and their relation to weights. Rebalancing, cash,
execution and path-dependent constraints add terms. There is no general inequality proving that unlevered inverse
volatility, stop/re-entry or volatility management always reduces expected return. Equal weighting is a simple
candidate with less estimation work; that does not establish higher future return for these five names.

Moreira and Muir's [NBER working-paper abstract](https://www.nber.org/papers/w22208) was checked (primary indexed abstract; direct re-fetch later returned 403,
not full-text verification or replication). It reports benefits for volatility-managed factor portfolios under its study design.
Those portfolios and scaling assumptions do not establish performance for a bounded, long-only, fee-paying
five-token book over this scored window. They also do not support the original blanket claim that volatility
management cannot raise expected return without leverage.

The DeMiguel/Garlappi/Uppal [publisher listing](https://academic.oup.com/rfs/article-abstract/22/5/1915/1592901)
was located (metadata only; full text inaccessible). This literature is relevant to estimation error and naive diversification, but the original
linked full text was not available to this review. Its abstract/index lead is not evidence that 1/N maximizes raw
expected return for LARP. Minimum variance, risk parity and return optimization address different objectives and
require defensible estimates. Keep them as alternatives requiring an explicit objective and prospective evaluation.

## Existing experiment, with its limits

[EXP-008](../../../ledger/EXP-008.md) records the pre-registered result “EW better for profit” on the 2019–2026
underlying-proxy sample at 25 bp per side: S1 minus EW averaged −0.58 pp per 10-session window. That is a historical
comparison, not a final-run forecast. EW drops MSFT, targets 80% gross and uses equal weights; S1 holds five names,
targets up to 95% and includes a trend rule. The primary contrast cannot isolate weighting or guard quality.

Reported exploratory decomposition: static S1 minus EW was −0.24 pp on the underlying proxy, but +0.48 pp on the
short token sample; guard contributions were −0.33 and −0.50 pp respectively. The token sample has four
non-overlapping windows. Selection of recent successful underlying names, token/proxy basis, KRW/FX treatment,
close-price fills, overlapping windows, cost assumptions and minimum-trade differences limit transfer. These
figures are retained from the experiment record, not independently rerun here. Its later diagnostics are exploratory.
The experiment does not replace [EXP-007](../../../ledger/EXP-007.md)'s registered trend-guard decision rule.

## Risk and cost trade-offs

A stop can reduce exposure before a continuing decline, miss a rebound, or cause whipsaw and additional fees.
Re-entry and reset semantics matter. The PF-02 recovery gap is a correctness/readiness issue against adopted policy;
its incremental profit cannot be bounded to ±0.1 pp from the evidence here. CPPI/drawdown-cushion methods likewise
need a declared model, discrete execution/gap risks and transaction-cost treatment. A continuous-time theoretical
optimum is not an implementation guarantee with minimum trades and market closures.

Increasing exposure from 95% to 100% adds a marginal risky sleeve and consumes cash/reserve headroom. Its expected
net benefit is that sleeve's unknown return minus incremental costs and operational effects. Similarly, dropping
MSFT or tilting to high-volatility names trades diversification and costs against unknown expected returns and
correlations. None has a measured positive profit effect or prize-probability improvement for the final run.

The original note claimed a 200000-draw simulation and numerical CPPI/exposure comparisons without committed code,
seed, inputs or receipts. Those are unreproduced claims, not accepted experiments. Their tables are withdrawn from
this reviewed note; the original text remains in immutable history below. No new simulation was run for this review.

## Decision use

Yao/team own any reopening of the chosen strategy; Keith owns prospective analysis and actual-size feasibility;
Keegan reviews; Isaac accepts exact profile/caps. Keep PF-01, PF-02 and EXP-007 gates. A fair alternative comparison
must declare return/drawdown objectives, common exposure/name sets or explicit ablations, authorized point-in-time
data, fees/gas/minimums, entry/exit calendars and decision criteria before running. Nothing here grants runtime use
of Yahoo data or changes the declared data plan.

## Provenance and original source leads

The [original research text](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/5d5b5e284fd0e70586ba83767a2d22b0fd726d1e/docs/research/strategy-alternatives-20261024/notes/portfolio_construction_and_risk.md) is retained immutably.
PR276-RV01 replaces unsupported conclusions and repairs local references. The register preserves the original
external URLs for follow-up; inclusion does not verify availability, quality, rights or any claimed result. Only
sources explicitly assessed above have been rechecked; all other entries remain unverified leads.

- Lead 01: [IDEAS/RePEc](<https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html>)
- Lead 02: [London Business School](<https://london.edu/faculty-and-research/academic-research/o/optimal-versus-naive-diversification-how-inefficient-is-the-1n-portfolio-strategy-p7805>)
- Lead 03: [Malformed original NBER path; unverified](<https://conference.nber.org/confer/2006/si2006/ap\uppal.pdf>)
- Lead 04: [summary of DP5142](<https://causalclaims.trfetzer.com/paper/DP5142.html>)
- Lead 05: [R-bloggers](<https://www.r-bloggers.com/2013/06/the-fallacy-of-1n-and-static-weight-allocation/>)
- Lead 06: [Cambridge Core](<https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/its-all-in-the-timing-simple-active-portfolio-strategies-that-outperform-naive-diversification/05D18E04B226C6E9B8441482CC92F943>)
- Lead 07: [IDEAS](<https://ideas.repec.org/a/cup/jfinqa/v47y2012i02p437-467_00.html>)
- Lead 08: [MSCI](<https://www.msci.com/documents/10199/36c8ed57-cfad-4d77-8d40-6cbcc107a778>)
- Lead 09: [CBS publisher version](<https://research-api.cbs.dk/ws/portalfiles/portal/60082899/lasse_heje_pedersen_et_al_betting_against_beta_publishersversion.pdf>)
- Lead 10: [EDHEC](<https://climateinstitute.edhec.edu/publications/why-does-equal-weighted-portfolio-outperform-value-and-price-weighted-portfolios>)
- Lead 11: [NBER w22208](<https://www.nber.org/papers/22208>)
- Lead 12: [PDF](<https://www.lehigh.edu/~xuy219/research/COWY.pdf>)
- Lead 13: [HKU seminar page](<https://hkubs.hku.hk/event/a-multifactor-perspective-on-volatility-managed-portfolios>)
- Lead 14: [Duke PDF](<https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf>)
- Lead 15: [Alpha Architect](<https://alphaarchitect.com/volatility-targeting-improves-risk-adjusted-returns/>)
- Lead 16: [Quantpedia](<https://quantpedia.com/the-impact-of-volatility-targeting-on-equities-bonds-commodities-and-currencies>)
- Lead 17: [SWoPEc abstract](<https://swopec.hhs.se/sifrwp/abs/sifrwp0063.htm>)
- Lead 18: [MIT DSpace](<https://dspace.mit.edu/handle/1721.1/114876>)
- Lead 19: [CXO Advisory](<https://www.cxoadvisory.com/?p=1809>)
- Lead 20: [MIT PDF](<https://dspace.mit.edu/bitstream/handle/1721.1/114876/Lo_When%20Do%20Stop-Loss.pdf>)
- Lead 21: [MIT DSpace](<https://dspace.mit.edu/handle/1721.1/107017>)
- Lead 22: [CXO Advisory](<https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth>)
- Lead 23: [IDEAS](<https://ideas.repec.org/a/bla/mathfi/v3y1993i3p241-276.html>)
- Lead 24: [Lund University](<https://lup.lub.lu.se/record/223851>)
- Lead 25: [Banque de France/ACPR paper](<https://acpr.banque-france.fr/system/files/import/acpr/medias/documents/brinkerlv_optimaldrawdowns.pdf>)
- Lead 26: [CFA Institute](<https://rpc.cfainstitute.org/research/financial-analysts-journal/1988/dynamic-strategies-for-asset-allocation>)
- Lead 27: [Baltic Journal of Economic Studies](<https://cyberleninka.ru/article/n/perold-sharpe-rebalancing-strategies-in-practice>)
- Lead 28: [IDEAS](<https://ideas.repec.org/a/cup/jfinqa/v48y2013i05p1433-1461_00.html>)
- Lead 29: [Vanguard, "Rational rebalancing"](<https://corporate.vanguard.com/content/dam/corp/research/pdf/rational_rebalancing_analytical_approach_to_multiasset_portfolio_rebalancing.pdf>)
- Lead 30: [Vanguard, "The rebalancing edge"](<https://corporate.vanguard.com/content/dam/corp/research/pdf/the_rebalancing_edge_optimizing_target_date_fund_rebalancing_through_threshold_based_strategies.pdf>)
- Lead 31: [Advisor.ca](<https://www.advisor.ca/investments/market-insights/with-rebalancing-less-is-more/>)
- Lead 32: [Alpha Architect](<https://alphaarchitect.com/quantitative-momentum-research-short-term-return-reversal/>)
- Lead 33: [Columbia Business School](<https://business.columbia.edu/sites/default/files-efs/pubfiles/11568/str1.pdf>)
- Lead 34: [CiteDrive record](<https://www.citedrive.com/en/discovery/short-term-reversals-and-longer-term-momentum-around-the-world-theory-and-evidence/>)
- Lead 35: [Berkeley copy](<https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf>)
- Lead 36: [Davis & Lleo chapter](<https://him-application.uni-bonn.de/uploads/media/DavisLleoKellyChapter.pdf>)
- Lead 37: [Gothenburg, "Winning ways"](<https://gupea.ub.gu.se/items/0ca5fa01-6afb-423a-b952-36aabc34106c>)
- Lead 38: [AEA 2018 session](<https://benny.aeaweb.org/conference/2018/preliminary/2044>)

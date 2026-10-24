# Portfolio construction, exposure and drawdown control for a 5-name, long-only, 10-session basket (LARP)

Scope: weighting, gross exposure, volatility management, stop-loss/drawdown rules, rebalancing and concentration for a long-only, unlevered basket of NVIDIA, Alphabet, SK hynix, Tesla and Microsoft (tokenized), about 200 USDT, about 10 trading sessions (UTC Oct 29 to Nov 12, 2026), with costs of about 15–25 bp per side plus gas. Score is % change in equity; the tie-break is lower max drawdown. This is design research for a competition agent, not investment advice, and it makes no price forecasts.

Evidence-quality legend used below: **[P]** primary source text read in this session (full text or official abstract); **[A]** abstract or publisher page only; **[S]** secondary summary (blog, aggregator, thesis), not checked against the paper; **[I]** my own derivation or synthetic illustration, not empirical evidence.

Internal context (not external evidence): the team's backtest (2019–2026 daily closes) found equal weight (80% gross, four names) beat S1 by about 0.58 pp per 10-session window, and S1 hit an 8% drawdown in 3.5% of windows vs 9.7% for equal weight (figures from the task brief). Related ledger rows: IDEA-006 (risk-constrained Kelly; synthetic "efficient gross ≈ 0.4–0.6"), IDEA-016 (build plus liquidate costs 0.24–0.68% of equity; a ±5 pp band, about 10 USDT, is below the minimum order, so the band must be at least 7.5–12.5 pp), IDEA-035/IDEA-037 (decided 2026-10-11: equal weight, four names at 20%, 80% invested, top-up rebalancing, no sales on drift) — [docs/LEDGER.md](../../docs/LEDGER.md).

---

## 1. Equal weight (1/N) vs inverse volatility vs risk parity vs minimum variance vs mean-variance, out of sample: which wins on return, and why, for 5 correlated assets?

### Takeaway
Out of sample, no optimised rule reliably beats 1/N on Sharpe or certainty-equivalent return, because expected returns cannot be estimated from short samples. Inverse-vol, risk parity and min-variance mainly lower volatility, not raise return. When an unlevered investor scores on raw return and expected return rises with volatility (even only proportionally), inverse-vol weights mechanically lower expected return relative to 1/N. They are Sharpe-optimal at best, never return-optimal. The team's −0.58 pp/window gap for inverse-vol plus trend guard fits this, and the size of the gap is inflated by in-sample selection: the high-vol names were the big winners of 2019–2026.

### Cited Findings
- DeMiguel, Garlappi & Uppal (2009, *RFS* 22(5):1915–1953): of 14 models across seven datasets, none is consistently better than 1/N on Sharpe ratio, certainty-equivalent return or turnover. The authors attribute this to estimation error offsetting the gains from optimisation [A] — [IDEAS/RePEc](https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html)
- Same paper: with parameters calibrated to US equities, the sample-based mean-variance rule needs an estimation window of about 3,000 months for 25 assets and about 6,000 months for 50 assets to beat 1/N [A] — [London Business School](https://london.edu/faculty-and-research/academic-research/o/optimal-versus-naive-diversification-how-inefficient-is-the-1n-portfolio-strategy-p7805); [NBER draft](https://conference.nber.org/confer/2006/si2006/ap\uppal.pdf)
- Working-paper version (CEPR DP5142): even with only four assets (20% average idiosyncratic volatility), the classical policy needs about 50 years of data to beat 1/N [S] — [summary of DP5142](https://causalclaims.trfetzer.com/paper/DP5142.html)
- Critique: the result rests on a short monthly history, and the paper does not test whether Sharpe differences are statistically significant [S, blog] — [R-bloggers](https://www.r-bloggers.com/2013/06/the-fallacy-of-1n-and-static-weight-allocation/)
- Kirby & Ostdiek (2012, *JFQA* 47(2):437–467): DGU's result is "largely due to their research design", which focuses on high-estimation-risk, extreme-turnover portfolios. Mean-variance often beats 1/N, but turnover erodes its edge after costs. Their low-turnover "volatility timing" (weights from conditional volatilities only) and "reward-to-risk timing" rules beat 1/N "even in the presence of high transaction costs" [A] — [Cambridge Core](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/its-all-in-the-timing-simple-active-portfolio-strategies-that-outperform-naive-diversification/05D18E04B226C6E9B8441482CC92F943); [IDEAS](https://ideas.repec.org/a/cup/jfinqa/v47y2012i02p437-467_00.html). Note that the evaluation criteria are Sharpe and CER, not raw return.
- Maillard, Roncalli & Teiletche (2010): the equal-risk-contribution (ERC/risk-parity) portfolio's volatility lies between that of minimum variance and 1/N, both theoretically and empirically [S, MSCI citing the paper] — [MSCI](https://www.msci.com/documents/10199/36c8ed57-cfad-4d77-8d40-6cbcc107a778)
- Frazzini & Pedersen (2014, *JFE*, "Betting Against Beta"): investors who cannot use leverage overweight high-beta assets, which flattens the security market line. High-beta assets have lower alphas in US equities, 20 international equity markets, Treasuries, corporate bonds and futures [A] — [CBS publisher version](https://research-api.cbs.dk/ws/portalfiles/portal/60082899/lasse_heje_pedersen_et_al_betting_against_beta_publishersversion.pdf)
- Plyakha, Uppal & Vilkov: monthly-rebalanced equal weight beat value weight on mean return, four-factor alpha and Sharpe ratio over about four decades of US index stocks. About 42% of the outperformance comes from alpha that the authors attribute to contrarian rebalancing (reversal plus idiosyncratic volatility). Equal weight also had higher volatility and kurtosis [A] — [EDHEC](https://climateinstitute.edhec.edu/publications/why-does-equal-weighted-portfolio-outperform-value-and-price-weighted-portfolios)

### Inferences
- [I] **Theory, raw-return objective.** With no leverage, the expected return of any long-only fully invested portfolio is Σwᵢμᵢ. It is maximised by putting everything in the single highest-μ name; diversification only buys lower variance. Any rule that shifts weight from high-μ to low-μ names lowers expected return.
- [I] **Equal-Sharpe case.** If μᵢ = S·σᵢ (equal Sharpe ratios) and correlations are constant, the tangency weights Σ⁻¹μ are proportional to 1/σᵢ. Inverse-vol is then exactly Sharpe-optimal, and it is the ERC portfolio. Its expected return relative to 1/N equals harmonic-mean(σ)/arithmetic-mean(σ). With assumed daily vols (NVDA 3.2%, GOOGL 2.0%, SK hynix 3.0%, TSLA 3.8%, MSFT 1.7%; my assumptions, not measured), that ratio is **0.914**: inverse-vol gives up about 9% of the basket's drift. The resulting inverse-vol weights are 15.6/25.0/16.7/13.2/29.5%, so the 30% cap barely binds on MSFT. At a 10-session drift of 0.5–1.0%, that is only about 0.05–0.09 pp per window.
- [I] **Why the measured gap is larger.** The team's 0.58 pp gap is several times what equal-Sharpe theory predicts. Part comes from the trend guard and the ladder lowering average exposure. The rest implies that in 2019–2026 the high-vol names (NVDA, SK hynix, TSLA) earned *more* than proportional return per unit of vol. That is an in-sample, selection-biased fact (the organisers picked these names after rallies), not a structural one. The BAB evidence points the other way in broad samples: high-beta and high-vol stocks earn *less* per unit of risk. Do not extrapolate "high-vol names win" forward. The defensible claim is only that inverse-vol cannot raise expected return when no leverage is allowed.
- [I] **With 5 correlated names, the rules converge.** At a pairwise correlation of about 0.5, ERC ≈ inverse-vol. Min-variance concentrates in the lowest-vol names (MSFT, GOOGL). Mean-variance from 60 sessions is noise, per DGU: windows of decades are needed even for 4 assets. Kirby–Ostdiek volatility timing is the defensible "optimised" choice, but its benefit is measured in Sharpe and CER, not return.
- [I] Under the stated objective (raw % return, with drawdown only as a tie-break or soft consideration), 1/N is the best-supported default. Inverse-vol is a deliberate trade of about 9% of the drift for about 9–10% lower basket volatility. With the assumed vols, EW daily vol is 2.14% and IV is 1.94% at ρ = 0.5.

### Gaps
- I could not read Maillard–Roncalli–Teiletche's full text to confirm the exact optimality conditions; the equal-Sharpe/constant-correlation result above is my derivation.
- I could not verify Kirby–Ostdiek's exact tuning parameter values or cost levels from the full text (abstract only).
- I found no study specific to 5-asset, single-sector, 2-week horizons. All the evidence uses monthly rebalancing over years.
- The per-name volatilities and correlations above are assumptions. The team should replace them with measured 60-session values from its own data.

---

## 2. Volatility-managed or volatility-targeted exposure: does it raise returns or only Sharpe, at what turnover cost, and does it help over 2 weeks?

### Takeaway
Volatility management raises Sharpe ratios in-sample for equities and thins the left tail. It does so by cutting exposure in high-vol periods and **levering up in calm ones**. Real-time, out-of-sample versions do not systematically beat buy-and-hold (Cederburg et al. 2020). Long-only and unlevered, LARP can only implement the "cut" half, and because equity mean returns are about flat across volatility regimes, that half lowers expected return. Over 10 sessions there is at most one meaningful scaling decision, so any benefit is mostly drawdown and tail reduction, not return.

### Cited Findings
- Moreira & Muir (2017, *JF* 72(4):1611–1644): portfolios that take less risk when volatility is high produce large alphas, higher factor Sharpe ratios and large utility gains for mean-variance investors. Their explanation is that volatility changes are not matched by proportional changes in expected returns [A] — [NBER w22208](https://www.nber.org/papers/22208)
- Cederburg, O'Doherty, Wang & Yan (2020, *JFE* 138:95–117), read in full [P] — [PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf):
  - Across 103 equity strategies (9 factors plus 94 anomalies), the volatility-managed versions beat the unmanaged ones on Sharpe in **53 cases vs 50**, with few differences significant.
  - In spanning regressions, 77 of 103 have positive alphas, 23 significantly positive. The market factor's spanning alpha is 4.63%/year. These regression-implied strategies "are not implementable in real time".
  - The real-time combination of managed and unmanaged earns a lower CER than the unmanaged portfolio in **72 of 103** cases. For the market, the out-of-sample Sharpe is **0.42 vs 0.46** for unmanaged.
  - The median position is about 1×, but the 99th percentile of required leverage exceeds **400%** for each factor, reaching 864% for momentum.
  - They attribute the failure to "structural instability in the underlying spanning regressions".
- Barroso & Detzel (2020) reportedly show that volatility-managed portfolio gains do not survive transaction costs [S, seminar abstract only] — [HKU seminar page](https://hkubs.hku.hk/event/a-multifactor-perspective-on-volatility-managed-portfolios)
- Harvey, Hoyle, Korgaonkar, Rattray, Sargaison & Van Hemert (2018, *JPM*, "The Impact of Volatility Targeting"), with text partly read [P] — [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf):
  - Sharpe gains are confined to "risk assets" (equity, credit) and are negligible for bonds, currencies and commodities.
  - For US equities sorted by the previous month's volatility, "the mean return shows no clear pattern across different quintiles".
  - The equity Sharpe ratio improves in all subsamples except 1957–1987.
  - The mechanism is the leverage effect, so vol scaling "effectively introduces some time-series momentum". Momentumness explains 45% (20-day half-life) to 60% (90-day half-life) of the cross-asset variation in Sharpe improvement.
  - Volatility targeting reduces max drawdowns for balanced and risk-parity portfolios.
  - The baseline volatility estimate uses EWMA with a 20-day half-life. Scaled and unscaled series are compared at the same 10% full-sample volatility, which implies leverage in calm periods.
- Secondary figures for the same paper, not verified against its tables [S]: equity Sharpe of about 0.40 unscaled vs 0.48–0.51 scaled, and US equity vol-of-vol of 4.6% vs 1.8% — [Alpha Architect](https://alphaarchitect.com/volatility-targeting-improves-risk-adjusted-returns/); [Quantpedia](https://quantpedia.com/the-impact-of-volatility-targeting-on-equities-bonds-commodities-and-currencies)

### Inferences
- [I] **Return vs Sharpe.** If equity mean returns are about flat across vol regimes (Harvey et al.), cutting exposure in high-vol regimes cuts expected return roughly in proportion to the cut, while cutting variance by more. The Sharpe gain in the literature is realised as higher return only by re-levering in calm periods. LARP cannot lever, and S1's cap is 95%. For LARP, then, vol-targeting is a pure de-risking overlay: it may lower drawdown, and it lowers expected return unless high vol forecasts low returns, which the quintile evidence does not show.
- [I] **Horizon.** Moreira–Muir rebalance monthly on the prior month's realised variance, and Harvey et al. use a 20-day half-life. A 10-session contest gets about half of one decision. Volatility clustering makes a 20–60-session vol estimate a reasonable forecast of the next two weeks' risk, but there is no evidence that it forecasts the next two weeks' return.
- [I] **Turnover cost.** S1's inverse-vol weights use a 60-session window, so they barely move within 10 sessions; turnover is negligible. The cost lies in the level shift: holding less risk on average. Any vol-targeted *gross* rule that trades on daily vol changes pays 15–25 bp per side on each adjustment. A 35 pp exposure change costs about 5–9 bp of equity each way.
- [I] Harvey et al.'s finding that vol scaling works *through* a momentum overlay suggests a vol-gross rule and a trend guard are partly redundant. Both cut exposure after falls. The team backtest found both cost return.

### Gaps
- I could not extract the S&P 500 exhibit numbers (Sharpe, max drawdown) from the Harvey et al. PDF; their tables are rendered as graphics.
- I did not read Liu, Tang & Zhou (2019) on look-ahead bias in Moreira–Muir, or Barroso & Detzel (2020) directly.
- I found no study of unlevered, cap-at-100% volatility targeting on a concentrated single-sector basket over horizons under a month.

---

## 3. Stop-loss and drawdown-control rules: when do they add or subtract expected return, and how do re-entry rules matter?

### Takeaway
Under a random walk, stop-loss rules **always** lower expected return (Kaminski & Lo 2014). They add value only when returns show momentum or regime persistence, and for individual US stocks in recent decades, short-horizon autocorrelation has been negative, so tight stops lose, mostly to costs (Lo & Remorov 2017). Wide stops measured over about 10 days roughly match buy-and-hold on a risk-adjusted basis while reducing max drawdown and improving skew. Drawdown-constrained optimisation (Grossman & Zhou 1993) gives a CPPI-like rule: risky exposure proportional to the cushion above a floor set relative to peak equity. It reliably cuts drawdown tails, but it is a convex, buy-high/sell-low strategy that loses in choppy markets and to trading costs. Fast re-entry helps tight stops; a stop with no re-entry is a permanent exposure cut.

### Cited Findings
- Kaminski & Lo (2014, *J. Financial Markets* 18:234–254):
  - Under the Random Walk Hypothesis, simple 0/1 stop-loss rules always decrease expected return; with momentum they can add value [A].
  - Their test uses US equities with long-term Treasuries as the stop asset, monthly, January 1950 to December 2004. Certain rules add 50–100 bp/month **during stop-out periods** [A].
  - They propose a regime-switching "flight-to-quality" process as an explanation [A].
  - Sources: [SWoPEc abstract](https://swopec.hhs.se/sifrwp/abs/sifrwp0063.htm); [MIT DSpace](https://dspace.mit.edu/handle/1721.1/114876)
- Same paper: the outperformance excludes trading frictions, and the rule's gains come from picking out periods when bonds beat equities [S] — [CXO Advisory](https://www.cxoadvisory.com/?p=1809)
- Same paper: the stopping premium can be positive and is "directly proportional to the magnitude of return persistence". For mean-reverting processes, stopping out "often leads to missing the subsequent reversion" [S, search snippet of the paper text] — [MIT PDF](https://dspace.mit.edu/bitstream/handle/1721.1/114876/Lo_When%20Do%20Stop-Loss.pdf)
- Lo & Remorov (2017, *J. Financial Markets* 34:1–15): they derive closed forms for serially correlated, regime-switching returns with costs. Tight stops generally underperform buy-and-hold for individual stocks, mainly because of costs, unless serial correlation is high. Downside-risk reduction is only modest [A] — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/107017)
- Same paper, details from a secondary summary [S] — [CXO Advisory](https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth):
  - Sample: US common stocks, daily, 1964–2014. Stops tested from 0 to −6% daily and 0 to −14% over 10 days, with the stopped money going to T-bills.
  - Costs: 0.2% half-spread.
  - Wide 10-day stops performed about as well as buy-and-hold on a risk-adjusted basis, reduced max drawdown and raised skewness. Tight stops significantly lowered returns.
  - Stock autocorrelation was positive in the first half of the sample and significantly negative in the second half.
  - One-day-delayed execution did better, because of reversion during the delay.
  - Quick re-entry usually helped tight stops.
  - Large spreads often accompany crashes.
  - Summary verdict: individual US stocks in recent decades are "not conducive to use of tight stop-losses".
- Grossman & Zhou (1993, *Mathematical Finance* 3(3):241–276): with a constraint W_t ≥ α·M_t (M_t = running maximum of wealth), the optimal risky investment is proportional to the surplus W_t − α·M_t [A] — [IDEAS](https://ideas.repec.org/a/bla/mathfi/v3y1993i3p241-276.html)
- Klass & Nowicki (2005): the Grossman–Zhou strategy does not keep its optimal-growth property in discrete time [A] — [Lund University](https://lup.lub.lu.se/record/223851). Practitioner work notes it is hard to implement near the limit when there are transaction costs [S] — [Banque de France/ACPR paper](https://acpr.banque-france.fr/system/files/import/acpr/medias/documents/brinkerlv_optimaldrawdowns.pdf)
- Perold & Sharpe (1988, *FAJ*, "Dynamic Strategies for Asset Allocation"): compares buy-and-hold (linear payoff), constant mix (concave: sells winners, buys losers) and CPPI (convex: buys as markets rise, sells as they fall) [A] — [CFA Institute](https://rpc.cfainstitute.org/research/financial-analysts-journal/1988/dynamic-strategies-for-asset-allocation). Constant mix is commonly summarised as better in trendless, volatile markets and CPPI as better in trending ones, but a later empirical paper found "no definite link" [S] — [Baltic Journal of Economic Studies](https://cyberleninka.ru/article/n/perold-sharpe-rebalancing-strategies-in-practice)
- Han, Yang & Zhou (2013, *JFQA* 48(5):1433–1461): a 10-day moving-average timing rule applied to *high-volatility decile portfolios* (stock vs T-bills, 1963–2009) earns abnormal returns above momentum's, surviving costs [A] — [IDEAS](https://ideas.repec.org/a/cup/jfinqa/v48y2013i05p1433-1461_00.html)

### Inferences
- [I] **S1's ladder and trend guard map onto this literature.** The trend guard (EW index 1% below its 5-session mean → 60% gross) is a short-horizon trend stop with automatic re-entry. Over a 10-session random-walk-like window it has a negative stopping premium (Kaminski–Lo). Each whipsaw pays about 35 pp × 20 bp × 2 ≈ 14 bp of equity, plus the missed rebound if large-cap returns mean-revert over days (Lo–Remorov). This matches the team finding that the guard costs return. Han–Yang–Zhou is the strongest pro-MA evidence, but it applies to diversified high-vol portfolios over decades, not a 5-name basket over 2 weeks.
- [I] **Synthetic illustration (not evidence).** I simulated 200,000 iid paths of 10 daily steps for an equal-weight basket: μ = 0.05%/day, σ = 2.3%/day (normal; Student-t(4) gave similar results). Costs are 20 bp per side on entry, every rebalance and the final liquidation. The baseline holds 95% gross.

  | Rule | Mean 10-session return | Median | P(maxDD ≥ 8%) | P(maxDD ≥ 12%) | Mean maxDD |
  |---|---|---|---|---|---|
  | Buy and hold | +0.09% | −0.14% | 24.2% | 5.8% | 5.98% |
  | S1-style 12% cut to 40%, no re-entry | +0.09% | −0.14% | 24.0% | 5.9% | 5.94% |
  | CPPI: gross = min(95%, 5 × (20% − DD)), traded only on > 5 pp change | +0.01% | −0.61% | 19.0% | 1.3% | 5.54% |

  Reading the table:
  - Entry plus exit costs (about 0.38%) eat most of the 0.475% expected 10-session drift at 95% gross.
  - The 12% rung barely matters within 10 sessions: it truncates only the tail beyond 12%.
  - A smooth CPPI cushion cuts the chance of a 12% drawdown by about 4–5× and of an 8% drawdown by about 5 pp. It costs about 0.08 pp of mean and about 0.5 pp of median, consistent with Kaminski–Lo's negative stopping premium under iid returns.
  - Daily marks miss intraday and 24/7 path lows, so real drawdowns would be deeper.
- [I] **Re-entry design.** A cut with no re-entry, like S1's 12% rung, locks in lower exposure for the rest of the contest, so it is a pure expected-return cost under iid returns. Rules that re-enter on recovery (CPPI, the trend guard) can whipsaw. The literature favours **wide** thresholds, roughly −10% to −14% cumulative over about 10 days, delayed execution, and quick re-entry, over tight daily stops.
- [I] **A tie-break argument exists.** Because the tie-break is lower max drawdown and the organisers "consider" drawdown, a CPPI-style cushion is the efficient way to buy drawdown reduction. S1's ladder is a coarse approximation of it: floor 20% below peak, multiplier 5 → 60% at 8% DD and 40% at 12% DD. The cost is real but small in expectation: about 0.1 pp of mean in the illustration.

### Gaps
- I could not access the full Kaminski–Lo text (HTTP 429), so the exact stopping-premium formula and its parameter grid are not quoted.
- The Lo–Remorov numbers come from a secondary summary. Mean, volatility and drawdown figures were not available.
- I found no study of stop rules on 24/7 tokenized equities, or of stop-outs within a 2-week contest.

---

## 4. Rebalancing over short horizons: bands vs calendar vs none; cost vs drift; letting winners run

### Takeaway
Over 10 sessions, rebalancing is almost irrelevant to expected return: weight drift is small, and the "rebalancing bonus" is second order. Each rebalance costs 15–25 bp on the traded amount and is constrained by minimum order size. The evidence favours wide threshold bands over calendar rebalancing, and "no sales on drift" (S1 and IDEA-037) is consistent with it. Stock-level evidence shows short-term (1-week to 1-month) *reversal*, not momentum, so "letting winners run" over 2 weeks has no support at the single-stock level. It also has no strong evidence against it in mega-caps.

### Cited Findings
- Vanguard: optimal rebalancing is neither too frequent (monthly or quarterly calendar) nor too infrequent (every two years). Annual, or threshold-based with drift tolerance, is generally preferred [A] — [Vanguard, "Rational rebalancing"](https://corporate.vanguard.com/content/dam/corp/research/pdf/rational_rebalancing_analytical_approach_to_multiasset_portfolio_rebalancing.pdf)
- Vanguard (2024, target-date funds): threshold rebalancing beats quarterly calendar rebalancing by only 5–8 bp/year (accumulation) and 6–10 bp/year (decumulation), mainly through lower transaction costs [A] — [Vanguard, "The rebalancing edge"](https://corporate.vanguard.com/content/dam/corp/research/pdf/the_rebalancing_edge_optimizing_target_date_fund_rebalancing_through_threshold_based_strategies.pdf)
- 1926–2009 study, not clearly attributed: annual monitoring with a 10% threshold gave 15 rebalancing events and 1.4% annual turnover, vs 389 events and 2.3% turnover for monthly monitoring with a 1% threshold. Gross returns were minimally affected [S] — [Advisor.ca](https://www.advisor.ca/investments/market-insights/with-rebalancing-less-is-more/)
- Plyakha–Uppal–Vilkov: the alpha of equal weight comes from *monthly* contrarian rebalancing that exploits reversal (see §1) [A] — [EDHEC](https://climateinstitute.edhec.edu/publications/why-does-equal-weighted-portfolio-outperform-value-and-price-weighted-portfolios)
- Lehmann (1990) and Jegadeesh (1990): prior-week losers beat prior-week winners. Jegadeesh's monthly reversal strategy earned about 2% per month of abnormal return (1965–1989). One summary reports prior-week winners averaging −0.35% to −0.55% the next week and losers +0.86% to +1.24% [S] — [Alpha Architect](https://alphaarchitect.com/quantitative-momentum-research-short-term-return-reversal/)
- Short-term reversals reflect incomplete liquidity provision, and within-industry (residual) reversals have a much higher Sharpe ratio [A, working paper] — [Columbia Business School](https://business.columbia.edu/sites/default/files-efs/pubfiles/11568/str1.pdf)
- Jegadeesh, Luo, Subrahmanyam & Titman (2025, *RFS*): stock returns reverse at short horizons and move slowly to momentum at longer horizons [A] — [CiteDrive record](https://www.citedrive.com/en/discovery/short-term-reversals-and-longer-term-momentum-around-the-world-theory-and-evidence/)
- Internal: build plus liquidate costs 0.24–0.68% of equity, and a ±5 pp band (about 10 USDT) is below the minimum order, so the band must be at least 7.5–12.5 pp — [IDEA-016 in docs/LEDGER.md](../../docs/LEDGER.md)

### Inferences
- [I] **Drift is small.** Over 10 sessions, with name vols of about 2–4%/day and correlation around 0.5, the cross-sectional dispersion of 10-session returns is a few percent to about 10%. Starting from 19% weights (95%/5), a name rarely drifts more than ±2–3 pp. Rebalancing everything back would trade only a few percent of equity, about 1 bp of cost. The expected benefit (diversification return, reversal capture) is of the same tiny order, and with about 200 USDT it is blocked by the minimum order anyway.
- [I] **Top-ups.** "Top-ups only when gross falls 5 points below target" and "no sales on drift" are consistent with the threshold evidence. Given IDEA-016's minimum-order finding, the effective band is wider than 5 pp, so for practical purposes the strategy is buy-and-hold for 10 sessions. That is close to optimal on cost grounds.
- [I] **Momentum vs reversal.** Weekly reversal evidence is strongest in small and illiquid stocks (the liquidity-provision explanation). Mega-cap tokenized stocks are liquid in the underlying, but the token venues may not be. Neither "let winners run" nor "rebalance into losers" has reliable expected-return support at 2 weeks for these names, so the cheapest option (do nothing) dominates.

### Gaps
- I did not find a source quantifying weekly reversal specifically for US mega-caps after costs. I found no direct one-month industry-momentum figures in this session.
- I found no study on rebalancing tokenized equities or 24/7 venues.

---

## 5. Gross exposure: 95% vs 100% vs lower over 10 sessions; Kelly and fractional Kelly over a 2-week horizon

### Takeaway
Going from 95% to 100% gross changes expected 10-session return by only about 0.015–0.05 pp at historical equity drifts. That is below the cost of the extra trade's round trip, and it raises max drawdown about proportionally (+5%). Kelly reasoning gives a full-Kelly fraction of roughly 0.6–1.9× for this basket depending on the assumed drift, which cannot be estimated reliably. Half-Kelly is 0.3–0.95. Kelly targets long-run log growth, though, not the score of a single, ranked, 2-week contest. A rank-based contest can rationally call for more variance, not less. Gross level is a variance and drawdown dial with almost no expected-return content at this horizon.

### Cited Findings
- MacLean, Thorp & Ziemba (2010, *Quantitative Finance*, "Good and bad properties of the Kelly and fractional Kelly capital growth criteria"):
  - Kelly (max E[log W]) maximises the long-run growth rate. Other good properties include minimising the time to large goals and maximising the median.
  - It is "very risky in the short term" because its Arrow–Pratt risk aversion is small.
  - Fractional Kelly (blending with cash) cuts risk while keeping much of the upside, at the cost of lower expected final wealth.
  - [A] — [Berkeley copy](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf)
- Fractional Kelly corresponds to the optimal policy of a power-utility investor in Merton's continuous-time model [S] — [Davis & Lleo chapter](https://him-application.uni-bonn.de/uploads/media/DavisLleoKellyChapter.pdf)
- Tournament and rank-based incentives [mostly S/A, working papers]:
  - Theory predicts more risk-taking than under linear pay.
  - Convex prize schedules induce positively skewed, riskier choices, and trailing agents increase risk.
  - Rewarding several top performers instead of only the best reduces risk-taking.
  - Sources: [Gothenburg, "Winning ways"](https://gupea.ub.gu.se/items/0ca5fa01-6afb-423a-b952-36aabc34106c); [AEA 2018 session](https://benny.aeaweb.org/conference/2018/preliminary/2044)
- Internal: IDEA-006's risk-constrained Kelly (Busseti, Ryu & Boyd 2016) synthetic illustration gave efficient gross of about 0.4–0.6 — [docs/LEDGER.md](../../docs/LEDGER.md)

### Inferences
- [I] **Arithmetic.** With an equal-weight basket σ ≈ 2.3%/day (my assumption: ρ ≈ 0.5–0.6):

  | Drift (μ/day) | 10-session mean at 100% gross | 10-session sd | 95% vs 100% gap | Full-Kelly f* = μ/σ² |
  |---|---|---|---|---|
  | 0.03% | 0.30% | 7.3% | 0.015 pp | 0.57 |
  | 0.05% | 0.50% | 7.3% | 0.025 pp | 0.95 |
  | 0.10% | 1.00% | 7.3% | 0.050 pp | 1.89 |

  The extra 5 pp costs about 1 bp to buy and 1 bp to sell. Signal-to-noise over one window is about 0.04–0.14 sd, so the realised outcome is almost all noise.
- [I] **Round-trip cost vs drift.** Round-trip build plus liquidate costs (IDEA-016: 0.24–0.68% of equity) are of the **same size as the whole expected 10-session drift** at 95% gross. Whether the score needs an end-of-contest flatten matters more for expected score than any weighting choice. That rule question belongs to the team's rules work, not this note.
- [I] **Kelly is the wrong objective here.** Kelly is defined for repeated bets and long horizons; a 14-day, single-shot contest is not that. Kelly's f* is also extremely sensitive to μ, which DGU show cannot be estimated. A 2× error in μ doubles f*. At realistic drifts, full Kelly sits at or above 95% gross and half-Kelly around 30–50%, so Kelly gives no sharp guidance between 80% and 100%.
- [I] **Objective under ranking.** If prizes go to the top few by % return, the score is convex in return, and the tournament literature says to *raise* variance. A higher gross raises it in a way that is roughly neutral in expected return. Lower max drawdown matters only as a tie-break, or as an undefined "consideration". The optimal gross therefore depends on the prize structure and how drawdown is weighed, which is a question for the team's rules work.
- [I] **Practical range.** For a contest scored on return, 90–100% gross is all about the same in expectation. The real choice is between (a) about 95% plus a drawdown cushion and (b) a lower gross (80%, as in IDEA-037) bought for drawdown. The team backtest's 8%-drawdown frequencies (3.5% vs 9.7%) are the measured price of that choice.

### Gaps
- I found no peer-reviewed study of optimal exposure in short, rank-scored trading competitions with drawdown tie-breaks. The tournament evidence is mostly experimental or from mutual funds over a year.
- I did not verify Brown, Harlow & Starks (1996, *JF*) on mid-year fund-manager risk shifting in this session.
- The basket σ and μ values are assumptions; they should be measured from the team's data, including off-hours variance (IDEA-016 notes off-hours variance share ≈ off-hours time share).

---

## 6. Concentration: is holding fewer names (dropping the costliest or lowest-beta) better for expected return in a 5-name basket?

### Takeaway
With five highly correlated names, diversification buys little: dropping one name raises basket vol by only about 2% (relative). So dropping the **costliest** name is a near-free cost saving. Dropping the **lowest-beta or lowest-vol** name raises variance and beta, but broad-sample evidence (flat security market line, BAB) gives no reliable reason to expect higher return per unit of risk from high-beta names. In this sample, the opposite in-sample pattern is a selection artefact. Concentration is mainly a variance lever, useful only if the prize structure rewards variance.

### Cited Findings
- Frazzini & Pedersen (2014): leverage-constrained investors bid up high-beta assets, so high-beta assets carry lower alphas across 20+ markets and asset classes [A] — [CBS publisher version](https://research-api.cbs.dk/ws/portalfiles/portal/60082899/lasse_heje_pedersen_et_al_betting_against_beta_publishersversion.pdf)
- DGU (2009): with few assets, estimated means are too noisy to justify tilting away from 1/N [A] — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html)
- Equal weight's measured edge over cap or price weighting is partly factor exposure and partly rebalancing alpha (42%), not a result of holding fewer names [A] — [EDHEC](https://climateinstitute.edhec.edu/publications/why-does-equal-weighted-portfolio-outperform-value-and-price-weighted-portfolios)
- Internal: IDEA-037 already orders purchases "cheapest round trip first" and holds four names at 20% — [docs/LEDGER.md](../../docs/LEDGER.md)

### Inferences
- [I] **Diversification arithmetic.** For equal weights, portfolio variance relative to average single-name variance is ρ + (1 − ρ)/N. At ρ = 0.5 that is 0.60 for N = 5, 0.625 for N = 4 and 0.667 for N = 3. In volatility terms, 4 names are about 2% riskier than 5, and 3 names about 5% riskier. Assumed-vol figures: EW-5 at 2.14%/day vs an average single name at 2.74%.
- [I] **Dropping the costliest name.** If one name's round trip costs, say, 10–20 bp more than the others, dropping it saves about 2–4 bp of equity (20% weight × the cost gap) at about +2% relative vol. That is a reasonable trade, consistent with the team's 4-name choice.
- [I] **Dropping the lowest-beta or lowest-vol name (e.g. MSFT).** Under equal Sharpe this adds return in proportion to the added vol. Under BAB it adds less than proportionally. The 2019–2026 backtest probably favours it because NVDA and SK hynix dominated, but that is look-ahead and selection.
- [I] **Correlation of the tilts.** Because the five names are highly correlated, choosing which 3–5 to hold mostly changes idiosyncratic dispersion (single-name events, earnings), not basket direction. Earnings dates inside Oct 29 – Nov 12 add event variance per name, which is a separate topic.

### Gaps
- I did not retrieve Bessembinder (2018) or other evidence on the skewness of single-stock returns relevant to concentration.
- I found no source on the actual per-name token spreads or venue costs. They should come from the team's measured profiles (IDEA-040 notes measured profiles are still open).

---

## 7. Candidate alternatives to S1, with expected effects and trade-offs (synthesis)

### Takeaway
The evidence favours dropping return-negative overlays (the trend guard, and inverse-vol if return is the objective). Drawdown control should be **one** explicit, wide, cushion-based rule. Buy once near the start, avoid trading on drift, and treat gross and concentration as variance dials set by the prize structure. Each candidate below states what it is expected to buy and what it costs. The magnitudes are from §§1–6, mostly [I], and need confirmation on the team's own data before any change. Per AGENTS.md, a ledger entry with pass criteria must be written first.

### Cited Findings
- 1/N is hard to beat out of sample (DeMiguel et al. 2009) [A] — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html)
- Real-time volatility management does not systematically beat unmanaged portfolios: 53 vs 50 on Sharpe, and lower CER in 72 of 103 (Cederburg et al. 2020) [P] — [PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf)
- Stops lower expected return under a random walk (Kaminski & Lo 2014) [A] — [SWoPEc](https://swopec.hhs.se/sifrwp/abs/sifrwp0063.htm). Wide 10-day stops are about neutral on Sharpe and cut max drawdown, while tight stops lose (Lo & Remorov 2017) [S] — [CXO Advisory](https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth)
- Drawdown-constrained optimum: exposure proportional to the cushion above α·peak (Grossman & Zhou 1993) [A] — [IDEAS](https://ideas.repec.org/a/bla/mathfi/v3y1993i3p241-276.html)
- Threshold rebalancing beats calendar rebalancing, by a little, through costs (Vanguard) [A] — [Vanguard](https://corporate.vanguard.com/content/dam/corp/research/pdf/the_rebalancing_edge_optimizing_target_date_fund_rebalancing_through_threshold_based_strategies.pdf)

### Inferences
Candidates, relative to S1 (95% cap, inverse-vol 60-session weights with a 30% cap, 5-session trend guard → 60%, ladder at 3%/8%/12%, 5 pp top-ups, no drift sales):

- **C-A "EW-hold-95" (return-maximising baseline).**
  - Rules: equal weight across the 4–5 cheapest names, built once at the start to about 95% gross. No trend guard, no inverse-vol, no drift trades. Keep only the 12% cut, or replace it with C-B.
  - Expected effect: recovers the inverse-vol drift give-up (about 9% of drift, or about 0.05–0.1 pp per window under equal Sharpe; more in-sample). Removes trend-guard whipsaw costs (about 14 bp per whipsaw) and the missed-rebound drag.
  - Cost: about 10% higher basket vol than inverse-vol, and more windows breaching 8% drawdown (team backtest: about 9.7% vs 3.5%, though that was at 80% gross).
  - Best if the score is pure return and drawdown matters only for exact ties.
- **C-B "EW-95 + CPPI cushion" (efficient drawdown control).**
  - Rules: C-A plus target gross = min(95%, m × (F − DD_from_peak)), e.g. F = 20%, m = 5. That gives 95% down to about 1% drawdown, 60% at 8% and 40% at 12%, so it contains S1's 12% rung as a special case. Trade only when the target moves more than the minimum-order band (≥ 7.5–12.5 pp per IDEA-016). Re-entry follows automatically as drawdown recovers.
  - Expected effect (synthetic): P(maxDD ≥ 12%) drops from about 5.8% to about 1.3%, and P(≥ 8%) from about 24% to about 19%.
  - Cost: about 0.08 pp of mean and about 0.5 pp of median per window under iid returns. Larger in choppy, mean-reverting markets (convex strategy; Perold–Sharpe), smaller in trending selloffs.
  - Best if drawdown carries real weight in judging.
- **C-C "EW-95 + one wide 10-session stop".**
  - Rules: C-A plus a single rule. If the basket's cumulative 10-session (or contest-to-date) return falls below about −10% to −12%, cut to about 40–50%. Re-enter to 95% if it recovers above the trigger by a margin, with delayed (next-session) execution.
  - Expected effect: this is the Lo–Remorov "wide 10-day stop" region, about Sharpe-neutral with lower max drawdown and better skew. It costs less than CPPI because it trades at most about twice.
  - Cost: a negative stopping premium under a random walk, plus about 10–15 bp per stop-and-re-entry cycle.
- **C-D "IV-95, no trend guard" (Sharpe and tie-break oriented).**
  - Rules: keep inverse-vol (or Kirby–Ostdiek volatility timing, w ∝ 1/σ²) for lower basket vol, but drop the trend guard.
  - Expected effect: keeps most of S1's drawdown advantage that comes from weighting, and recovers the trend guard's return cost.
  - Cost: still gives up about 9% of drift relative to EW under equal Sharpe.
  - Best if drawdown is judged materially but a smooth cushion (C-B) is not wanted.
- **C-E "100% gross" variants of A–C.**
  - Expected effect: +0.015–0.05 pp of expected return per window, which is about cancelled by the extra 5 pp round-trip cost (about 2 bp) and possible gas/minimum-order cash needs. Max drawdown is about +5% relative.
  - Verdict: essentially neutral. Choose by operational cash needs (gas, minimum orders), not by expected return.
- **C-F "Concentrated 3 high-vol names" (variance-seeking).**
  - Expected effect: about +5% relative basket vol vs 5 names, plus higher beta and idiosyncratic dispersion. Expected return is about unchanged to modestly higher only under an equal-Sharpe-or-better assumption; BAB evidence argues against.
  - Cost: much higher drawdown tail.
  - Use only if the prize structure is strongly convex (winner-take-most) and drawdown is only a tie-break. Even then, the edge comes from variance, not expected return.
- **C-G "Drop the costliest name" (4 names, any of A–D).**
  - Expected effect: saves about 2–4 bp per window at about +2% relative vol. This is consistent with IDEA-037's 4-name choice.

**Cross-cutting [I] points**
1. Cost per round trip (0.24–0.68% of equity) is about the size of the whole expected 10-session drift. Minimising the number of trades, and settling whether an end-of-contest flatten is needed, matters more than the weighting rule.
2. Every 2019–2026 backtest of these five names is selection-biased toward high-vol winners. Rules that look better because they overweight NVDA or SK hynix should be discounted. Rules that look worse because they underweight them (inverse-vol) are worse partly for structural reasons (§1) and partly for in-sample ones.
3. Pass criteria for any switch should be written in the ledger before testing. Examples: mean and median 10-session return net of measured costs, P(maxDD ≥ 8%/12%) on rolling windows, and robustness when NVDA and SK hynix are excluded or their drift is demeaned.

### Gaps
- No source evaluates these specific rule combinations on tokenized-equity venues or 14-day contests. All magnitudes above are either broad-literature results at longer horizons or my synthetic illustrations under iid assumptions.
- The prize structure (top-N vs ranked payouts) and how much "drawdown is considered" were not in my scope. Both change which candidate is optimal and should be checked against `docs/skill/SKILL.md` F/K/Q items before choosing.
- The illustrative volatilities and correlations need replacing with measured values, including weekend and off-hours variance on the token venues.

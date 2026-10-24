# Competition strategy under rank-based payoffs, and what LLM trading agents have achieved (for LARP)

*Research date 2026-10-24. Evidence dates are marked on each item. This is design research for a competition agent, not investment advice, and contains no price forecasts. Unless marked "primary", web figures come from abstracts or secondary reports and were not checked against full texts. Local rule citations point to the repo's verbatim copies.*

## 1. Tournament theory and evidence: how a top-3-of-~25, 14-day, rank-based payoff changes optimal risk-taking (variance, concentration, correlation with rivals, drawdown tie-break)

### Takeaway
Only 3 of about 25 teams win prizes (12% of the field). Contest theory says that in this regime a team should pick a riskier return distribution, and one less correlated with the rest of the field, than a team trying to maximise its absolute or risk-adjusted return would. Under illustrative assumptions, a half-invested diversified basket is close to the worst choice for P(top 3), while a concentrated position gives the most robust P(top 3), at the cost of a higher chance of a large loss. Empirical evidence that funds shift risk in tournaments exists but is contested. Most of it concerns trailing managers gambling late in the period, which LARP cannot act on: there is no live leaderboard and the build is frozen.

### Cited Findings
**Contest theory (variance and correlation choice)**
- Gaba, Tsetlin & Winkler (2004, *Operations Research* 52(3):384–396) model contestants in a multinormal setting who can change the variability of their performance and its correlation with rivals. When fewer than half the contestants win, a riskier distribution is preferred; when more than half win, a less risky one. With few winners it pays to "take chances and distance oneself from other contestants" (lower correlation); herding suits contests with many winners. When every contestant can make these changes, the same rule is the dominant best response. — [INFORMS](https://pubsonline.informs.org/doi/pdf/10.1287/opre.1030.0098); [INSEAD listing](https://www.insead.edu/faculty-research/publications/journal-articles/modifying-variability-and-correlations-winner-take) (abstract)
- In a companion paper on multi-round contests and contests with handicaps (Gaba, Tsetlin & Winkler 2004, *Journal of Risk and Uncertainty* 29(2):143–158), a contestant should maximise variability from a weak position and minimise it from a strong one. — [IDEAS/RePEc](https://ideas.repec.org/a/kap/jrisku/v29y2004i2p143-158.html) (abstract)
- Schwarz & Severinov, "Investment Tournaments: When Should a Rational Agent Put All Eggs in One Basket?" (NBER w15136, 2009; *Journal of Labor Economics* 28(4):893–922, 2010): when the payoff weights are convex in final values, it is optimal "in a broad range of cases" to put all resources into the most promising alternative. — [IDEAS/RePEc](https://ideas.repec.org/a/ucp/jlabec/v28y2010i4p893-922.html); [NBER](https://www.nber.org/papers/w15136)
- Forecasting contests show the same pattern. Lichtendahl & Winkler (2007, *Management Science* 53(11):1745–1755) find that forecasters who care about beating rivals should report more extreme probabilities. — [IDEAS/RePEc](https://ideas.repec.org/a/inm/ormnsc/v53y2007i11p1745-1755.html). Witkowski, Freeman, Wortman Vaughan, Pennock & Krause ("Incentive-Compatible Forecasting Competitions", AAAI 2018) show that when only the top scorer wins, forecasters can raise their chance of winning by reporting extreme beliefs, so the prize does not reliably go to the most accurate forecaster. — [arXiv 2101.01816](https://arxiv.org/pdf/2101.01816)
- Poker tournament evidence (IZA DP 1345): players adjust their risk to the prize structure, and players far behind have reason to take high-risk actions late, because when prizes are fixed by rank a bigger loss costs them nothing extra. — [IZA](https://docs.iza.org/dp1345.pdf)
- In experiments, Kirchler, Lindner & Weitzel (2018, *Journal of Finance* 73(5):2271–2302) found that rankings and tournament incentives raised risk-taking among underperforming finance professionals (657 professionals, 432 students). The students did not respond to rankings. — [Utrecht research portal](https://research-portal.uu.nl/en/publications/rankings-and-risk-taking-in-the-finance-industry/) (abstract)

**Fund-tournament evidence (risk-shifting)**
- Brown, Harlow & Starks (1996, *JF* 51(1):85–110) studied 334 growth funds over 1976–1991. Mid-year "losers" raised fund volatility in the second part of the year more than mid-year "winners" did, and the effect grew as investors paid more attention to performance. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v51y1996i1p85-110.html). (One literature summary gives the period as 1980–1991; IDEAS gives 1976–1991.)
- Chevalier & Ellison (1997, *JPE* 105(6):1167–1200) estimated the flow–performance relationship for 1982–1992. Its shape gives managers an incentive to change risk depending on year-to-date return, and September-to-December holdings show that funds did change risk in line with those incentives. — [NBER w5234](https://nber.org/papers/w5234); [JPE](https://www.journals.uchicago.edu/doi/10.1086/516389)
- **Contradicting evidence:** Busse (2001, *JFQA* 36(1):53–73) re-ran the test on daily returns, and the monthly-data result that underperformers raise risk "disappears". He attributes the monthly result to bias in monthly volatility estimates caused by autocorrelation in daily returns. — [IDEAS/RePEc](https://ideas.repec.org/a/cup/jfinqa/v36y2001i01p53-73_00.html); [Cambridge](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/another-look-at-mutual-fund-tournaments/CD3356D7C7EDDC18D960CEF90CA7D84F)
- Taylor (2003, *JEBO* 50(3):373–383) adds strategic interaction. When managers are judged against an exogenous benchmark, losers gamble; when the benchmark is endogenous (beating rivals), winners gamble. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jeborg/v50y2003i3p373-383.html). A UK study of 422 funds found no consistent tournament behaviour over 1989–2003, but did find Taylor-style strategic behaviour in the 1997–2003 sub-period. — [Maastricht CRIS](https://cris.maastrichtuniversity.nl/en/publications/tournaments-in-the-uk-mutual-fund-industry/); [Emerald](https://www.emerald.com/insight/content/doi/10.1108/03074350810900514/full/html)
- Chen, Hughson & Stoughton argue that a leader should lock in its advantage by cutting risk if and only if its lead is large enough. A 2012 paper concludes that "no clear consensus has emerged" on whether tournament behaviour exists. — [CFR Cologne PDF](https://www.cfr-cologne.de/download/kolloquium/2012/Chen_etal.pdf)

**This contest's rules (local verbatim copies)**
- There is no public real-time leaderboard; the full 14-day window decides the ranking. The proposed FinalScore is the % change in wallet equity. The tie-break is lower maximum drawdown; if still tied, the rank is shared. Fees and gas reduce the score. "Not scored" includes "number of trades" and "call volume". — [docs/official/source_page.md](../../docs/official/source_page.md) (lines 84, 102–107, 121–122)
- Organiser statement F-115: "we'll look at your completed trades' PnL, drawdown, logs, and code repo all together", and not trading "is definitely not what this competition is about". The weights are open (Q-39). — [docs/skill/SKILL.md](../../docs/skill/SKILL.md) (F-115, Q-17)

### Inferences
- With 3 winners out of ~25 (12%, well below one half), the contest is in the Gaba–Tsetlin–Winkler regime that favours **more variance and lower correlation with the field**. Adding teams while keeping 3 prizes pushes further in that direction.
- **Short horizon:** over 14 days, outcomes are dominated by noise (the common move shared by the five names plus each name's own move) rather than by skill. That makes the choice of payoff *distribution* matter more than a small forecasting edge does.
- **Illustrative Monte Carlo (my own calculation, uncalibrated assumptions; not data):**
  - **Setup:** 25 teams; 5 names. Each name's 14-day return = a common factor M ~ N(0, 7%) + its own idiosyncratic part ~ N(0, 8%). These sizes are assumed, not estimated from tokenized-stock data.
  - **24 rivals:** each holds a random exposure x with random Dirichlet weights across the five names, plus noise for active trading and fees ~ N(−0.5%, 3%). Three rival fields:
    - *cautious:* x ~ U(0, 0.6), diversified (α = 3)
    - *mixed:* x ~ U(0, 1), α = 1
    - *aggressive:* x ~ U(0.7, 1), concentrated (α = 0.3)
  - **Run:** 200k draws per field. Pure luck gives P(top 3) = 3/25 = 12%.

  P(top 3) by strategy and field:

  | LARP choice | cautious field | mixed field | aggressive field |
  |---|---|---|---|
  | All cash | 6.1% | 12.3% | 21.6% |
  | 50% equal basket | 1.4% | ~0.0% | 4.8% |
  | 95% equal basket | 25.1% | 8.4% | 0.1% |
  | 95% in two names | 29.9% | 21.5% | 10.6% |
  | 95% in one name | 33.9% | 28.7% | 23.0% |

  - The median rank was about 11–12 for every choice, so concentrating did not change the *expected* rank, only the tails.
  - In the mixed field, the outcome for a 95% basket depends on direction: P(top 3) was 16.5% when the common factor rose and 0.3% when it fell. All cash got 0.5% and 23.9% in the same two cases.
  - Chance of losing more than 10% over 14 days: 9.1% for the basket, 12.1% for two names, 16.1% for one name.
  - Giving LARP's holdings an assumed +1% edge over 14 days moved the basket's P(top 3) only from 8.4% to 15.6%, and one name's from 28.7% to 33.2%.

  **Reading:** being "in the middle" (half-invested and diversified) is worst for a top-3 payoff. A fully invested equal basket is a bet that the field is under-invested and the common factor rises. Concentration gives the most field-robust P(top 3) but a heavier left tail.
- **Kelly is the wrong objective for this payoff (reasoning, no source retrieved):** Kelly maximises long-run growth across repeated bets, and with no reliable edge the Kelly fraction tends to zero (hold cash). A one-shot top-3 prize instead rewards variance. Any risk-constrained Kelly rule in the repo (L-37/IDEA-006 per SKILL.md v0.7.1) is better read as a *cap* on risk than as the thing being optimised.
- **No live leaderboard plus a frozen build** means the dynamic tournament rules (losers gamble late, leaders lock in, from Brown–Harlow–Starks, Taylor, and Chen–Hughson–Stoughton) cannot be conditioned on rank. Own P&L is a poor stand-in for rank, because the common factor moves every team. Any path-dependent rule has to be coded and committed before the freeze.
- **The drawdown tie-break almost never binds for a top-3 contender.** Exact ties in % return are realistic only for teams that never trade (0.00%) or hold identical portfolios. Drawdown matters mainly through the F-115 "all together" assessment and the winner audit, not the tie-break itself.
- **Rivals:** Kirchler et al. suggest teams that see themselves losing will gamble more. In this contest they can only see their own P&L, so expect some late, high-variance behaviour from teams that are down. That widens the right tail of the field and raises the bar for top 3.

### Gaps
- I found no primary paper titled or framed as "how to win a trading competition" with top-k prizes under long-only, no-leverage constraints, and no empirical study of what wins short retail or exchange trading competitions.
- I retrieved no primary source on Kelly versus rank maximisation (e.g. maximising the probability of beating rivals by a deadline). The Kelly point above is reasoning only.
- I read only abstracts and secondary summaries for Brown–Harlow–Starks, Chevalier–Ellison, Taylor and Busse. The full texts are paywalled, and an EFMA literature-review PDF could not be parsed.
- Both the composition of the field and the volatility parameters of the Monte Carlo are unknown. The 7% and 8% 14-day sizes are placeholders and should be calibrated on the team's own tokenized-stock data before anyone relies on the numbers.

## 2. Live LLM trading competitions and benchmarks: results by model, drivers of wins and losses, fees and overtrading, and whether LLM agents beat buy-and-hold

### Takeaway
Across the 2025–26 live contests and bias-controlled benchmarks, LLMs acting as the main trader rarely beat buy-and-hold reliably. Results depend more on the agent framework, prompt and risk style than on the base model, and general-capability rankings do not predict trading results. Alpha Arena's large losses came from behaviour: overtrading, leverage and position sizing. Under long-horizon, bias-controlled tests (FINSABER), LLM timing strategies show no significant alpha and are "too cautious when risk is rewarded and too aggressive when it is penalised".

### Cited Findings
**nof1 Alpha Arena, Season 1 (crypto perpetuals on Hyperliquid, Oct 18 – Nov 3, 2025; $10k per model; six models; identical prompts and data according to the organiser)**
- Reported final returns: Qwen3 Max +22.3%, DeepSeek V3.1 +4.89%, Claude Sonnet 4.5 −30.81%, Grok 4 −45.3%, Gemini 2.5 Pro −56.71%, GPT-5 −62.66%. The official Season 1 pages are no longer available. Secondary sources disagree on figures (Claude about −30.8% or −42.0%; Grok −45.3% or −57.9%) but not on the order. — [iWeaver recap](https://www.iweaver.ai/blog/alpha-arena-ai-trading-season-1-results/); [SCMP](https://www.scmp.com/tech/tech-trends/article/3331425/alibabas-ai-model-outperforms-us-rivals-crypto-trading-showdown)
- Trade counts and fees (secondary sources, conflicting): Qwen made about 43 trades (under 3 a day). Gemini 2.5 Pro is reported at 238 trades with $1,331 in fees, or at 165 trades and more than $1,000 in fees by Oct 27. Reports of leverage conflict, from under 1× to 10–15× for GPT-5. — [Forklog](https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/); [Aurpay](https://aurpay.net/aurspace/ai-trading-battle-chinese-models-crush-western-ai/); [iWeaver](https://www.iweaver.ai/blog/alpha-arena-ai-trader-showdown/)
- The path mattered: DeepSeek reportedly peaked well above its starting balance before finishing at about +4.9%. — [iWeaver recap](https://www.iweaver.ai/blog/alpha-arena-ai-trading-season-1-results/)

**Alpha Arena, Season 1.5 (US equities; started Nov 19, 2025; ended Dec 3, or announced ended Dec 5; 8 models; $10k each)**
- The assets were TSLA, NVDA, MSFT, AMZN and the Nasdaq-100 per [GNcrypto](https://www.gncrypto.news/news/mystery-model-alpha-arena-season-1-5-winner/). [One Day Advisor](https://www.onedayadvisor.com/2025/12/nof1ai-alpha-arena-review-season-15.html) adds GOOGL and PLTR. Either way the list overlaps LARP's NVDA, MSFT, TSLA and possibly GOOGL.
- Four parallel contests ran:
  - **New Baseline:** extra data, including news, macro sentiment, fundamentals and order book.
  - **Monk Mode:** prompt about 50% shorter, optional guardrails, and "do nothing" allowed.
  - **Situational Awareness:** models saw live rankings of themselves and rivals.
  - **Max Leverage:** 20× leverage required on every position.

  — [GNcrypto](https://www.gncrypto.news/news/mystery-model-alpha-arena-season-1-5-winner/)
- The winner, "Mystery Model", was later revealed as Grok 4.20. It returned +12.11% in aggregate over two weeks and made money in all four contests. Qwen, the Season 1 winner, dropped to sixth on day 1 and never recovered. — [GNcrypto](https://www.gncrypto.news/news/mystery-model-alpha-arena-season-1-5-winner/); [Yahoo Finance](https://finance.yahoo.com/news/elon-musks-grok-4-20-123855766.html)
- Field outcome (secondary): the combined portfolio lost about a third of its value, and only 6 of 32 model-contest sessions were profitable. In one round under identical prompts, Qwen made 1,418 trades and Grok 4.20 made 158. Founder Jay Azhang is reported as saying LLMs are prone to overtrading, timing errors and position-sizing errors, and that handing money directly to an LLM "doesn't work yet". — [BigGo Finance](https://finance.biggo.com/news/5BSX_Z0BaoGGrU-ID27J)
- The leaderboard reportedly lists 32 Season 1.5 entries, from +34.59% to −96.15%. — [TradeRank](https://www.traderank.ai/blog/alpha-arena-alternatives-2026) (secondary)
- Jim Moran (Flat Circle) found at least one profitable model in each of 11 tracked arenas, but the median model was profitable in only 2 of them, and he calls the experiments too short and noisy to be conclusive. — [BigGo Finance](https://finance.biggo.com/news/5BSX_Z0BaoGGrU-ID27J)

**Benchmarks**
- **StockBench** (arXiv 2510.02209, Oct 2025; primary HTML):
  - **Setup:** Mar 3 – Jun 30, 2025 (82 trading days), the top 20 DJIA stocks, $100k starting cash.
  - **Baseline vs models:** the passive baseline returned +0.4% with max drawdown −15.2%. The best LLM agents returned +1.9% to +2.5% with drawdowns of −11.2% to −14.9% (Kimi-K2 +1.9%, Qwen3-235B-Ins +2.4%). GPT-5 returned +0.3% and GPT-OSS-20B −2.8%.
  - **No frictions:** trading costs and slippage are not modelled.
  - **Regimes:** in a Jan–Apr 2025 downturn window, *all* LLM agents failed to beat the passive baseline; in a May–Aug 2025 upturn, most did.
  - **News ablation:** Kimi-K2's return fell from 1.9% to 1.4% without news, and to 0.6% without news and fundamentals.

  — [arXiv HTML](https://arxiv.org/html/2510.02209v1)
- **LiveTradeBench** (arXiv 2511.03628, Nov 2025; primary HTML):
  - **Setup:** a live run of 50 trading days (Aug 18 – Oct 24, 2025) on 15 US large caps plus cash, with 21 LLMs.
  - **Returns:** cumulative returns ranged from +1.78% to +6.25% (GPT-4.1 +6.25%, o3 +6.04%, Gemini-2.5-Pro +1.95%). No passive baseline is reported.
  - **Capability vs results:** the Spearman correlation between LMArena score and stock return was only 0.054 (−0.38 on Polymarket), and reasoning models did not do better.
  - **Styles:** GPT-4o concentrated on AAPL, MSFT and NVDA; GPT-5 diversified and held under 10% cash.

  — [arXiv HTML](https://arxiv.org/html/2511.03628v1)
- **Agent Market Arena** (arXiv 2510.11695, v2 Oct 30, 2025): a live benchmark across crypto and stocks with four agent frameworks on five base models. Agent frameworks showed "markedly distinct behavioral patterns", and base models contributed less to the variation in outcomes. — [arXiv](https://arxiv.org/abs/2510.11695). In an interview, the authors said most agents still struggle to beat buy-and-hold, that no real money is used, and that costs are not included. — [AI Street](https://aistreet.beehiiv.com/p/benchmarking-ai-agents-in-live-markets)
- **FINSABER** (arXiv 2505.07078 v5, Feb 12, 2026; KDD '26; primary HTML):
  - **Replication:** FinMem's reported TSLA result (cumulative return 61.8%, Sharpe 2.68) replicated at 19.9% and Sharpe 0.93.
  - **Bias-mitigated 2004–2024 composite:**
    - buy-and-hold Sharpe 0.315 to 0.703
    - FinMem −0.29 to 0.03
    - FinAgent −0.08 to 0.24
    - alpha not significant (FinAgent's best was +6.57%, p = 0.345)
  - **Regimes (average Sharpe):**

    | Strategy | Bull years | Bear years |
    |---|---|---|
    | Buy-and-hold | 0.61 | −0.28 |
    | FinAgent | 0.12 | −0.38 |
    | FinMem | −0.19 | −0.97 |

  - **Turnover:** FinMem's commission ratio was 5–9× FinAgent's (overtrading).
  - **Authors' advice:** better trend detection and regime-aware risk controls; the main barrier is "a lack of domain-aware financial logic", not model scale.

  — [arXiv HTML](https://arxiv.org/html/2505.07078v5)
- **InvestorBench** (ACL 2025): thirteen base models across stocks, crypto and ETFs. Larger and proprietary models generally did better, but all models struggle in highly volatile markets. — [arXiv 2412.18174](https://arxiv.org/abs/2412.18174v1)
- **FinRL contests:** the 2025 Task 1 (FinRL-DeepSeek) feeds LLM-derived sentiment scores and risk levels from news into an RL trader. Team counts were 46, 21 and 85 for 2023–2025. — [FinRL contests paper](https://arxiv.org/html/2504.02281v3); [Task 1 docs](https://finrl-contest.readthedocs.io/en/latest/finrl2025/task1.html)

### Inferences
- The consistent lesson is that the money was lost through behaviour: turnover, leverage and sizing. General model capability does not predict results. That supports LARP's frozen, rule-based, low-turnover core, with the LLM kept off the "add exposure" path.
- The typical failure in the bias-controlled evidence is being *under-invested in rising markets* (FINSABER). For LARP, the main risk of a reduce-only LLM is a false-positive cut during a rally that is never re-entered. In an up market that loses rank directly.
- Season 1.5 is the closest analogue: two weeks, overlapping US tech names, ranked on return. Most of the field lost money (6 of 32 sessions profitable). That suggests many of LARP's ~25 rivals may lose to fees and churn, so a low-turnover invested agent has a fair chance of beating the median. Reaching the top 3 still means being on the right side of the tails (see §1).
- The benchmark windows are short (50–82 days) and cover a single regime, and the gaps between models (1–4 points) are within one-regime noise. None of them shows durable skill.

### Gaps
- nof1's official results pages were unavailable (nof1.ai/blog returned 404), so the Season 1 and 1.5 figures come from secondary sources, which conflict on trade counts, fees, leverage, asset lists and end dates. Per-model, per-contest Season 1.5 results were not retrieved.
- LiveTradeBench reports no passive baseline, so I could not say whether its models beat buy-and-hold.
- I did not retrieve AMA's quantitative leaderboard, InvestorBench's numbers, or the FinRL 2025 final standings and LLM-signal effect sizes.
- No benchmark found tests a "reduce-only LLM risk veto on a rule-based core" design directly.

## 3. Evidence on LLM-derived news/sentiment signals for large-cap returns at 1-day to 2-week horizons, look-ahead/memorisation bias, and LLMs as risk filters or event detectors

### Takeaway
LLM news scores do predict drift, but the documented edge is concentrated in **small stocks and negative news**. It lasts about **1–2 trading days**, is eliminated by **about 20 bps of round-trip cost**, and its Sharpe ratio fell from **6.54 in late 2021 to 1.22 in early 2024**. Memorisation can inflate backtests. For five heavily covered mega-caps at 1–14 day horizons, there is little support for using an LLM to generate signals. Support is better for LLMs as **risk and event classifiers**, and the asymmetry towards negative news fits a downside-only role.

### Cited Findings
- **Lopez-Lira & Tang** (arXiv 2304.07619 v6, Oct 28, 2025; primary HTML):
  - **Sample:** Oct 2021 – May 2024, after GPT-4's training cutoff.
  - **Initial reaction:** about a 90% hit rate, but that reaction cannot be traded.
  - **Drift:** lasts "for the next one to two trading days". The overnight-news long-short earns 0.34% a day, Sharpe 2.97 before costs.
  - **Costs:** at 10 bps round trip the Sharpe ratio is 1.29; at 20 bps the strategy is unprofitable.
  - **Firm size and direction:** the small-firm interaction is 0.404 against a base coefficient of 0.087. The short leg earns 26 bps a day (Sharpe 2.01) against the long leg's 8 bps (Sharpe 0.78).
  - **Decline:** annual Sharpe ratio fell from 6.54 (2021Q4) to 3.68 (2022), 2.33 (2023) and 1.22 (Jan–May 2024), which the authors call "suggestive" of rising LLM adoption.

  — [arXiv HTML](https://arxiv.org/html/2304.07619v6)
- **Chen, Kelly & Xiu, "Expected Returns and Large Language Models":** LLM embeddings of news improve return forecasts over technical signals and simpler NLP methods. Prices respond slowly to news, consistent with limits to arbitrage. The study covers 16 equity markets in 13 languages, and a strategy trading on fresh news alerts gets higher Sharpe ratios. — [Univ. of Sydney seminar abstract](https://business.sydney.edu.au/events/research/2024/finance/dacheng-xiu); [Tsinghua PBCSF notice](https://www.pbcsf.tsinghua.edu.cn/info/1504/7668.htm)
- **Kirtac & Germano** (*Finance Research Letters* 62, 2024, 105227): 965,375 US news articles over 2010–2023. OPT reached 74.4% accuracy, and an OPT-based long-short strategy had a Sharpe ratio of 3.05 after 10 bps costs, against 1.23 for a dictionary method. This is a daily, cross-sectional long-short result, not a long-only result on five names. — [arXiv 2412.19245](https://arxiv.org/html/2412.19245v1)
- **Look-ahead and memorisation:**
  - Glasserman & Lin (2023) separate look-ahead bias from a "distraction" effect. In-sample, headlines with the company anonymised did better, suggesting distraction matters more. Out of sample, look-ahead is not a concern. — [arXiv 2309.17322](https://arxiv.org/abs/2309.17322)
  - "Detecting Lookahead Bias in LLM Forecasts" (arXiv 2512.23847, Dec 2025) replicates the Lopez-Lira–Tang setup with Llama-3.3 and finds that memorisation substantially amplifies apparent predictive power (about +37% of the baseline effect). Per a community summary, the effect is insignificant in true out-of-sample tests. Masking company identifiers leaves subtler memorisation channels intact. — [arXiv HTML](https://arxiv.org/html/2512.23847v1)
- **LLMs as risk detectors:** Kim, Muhn & Nikolaev, "From Transcripts to Insights" (arXiv 2310.17721, v2 Mar 2025), scored political, climate and AI risk from earnings calls with GPT-3.5. The scores beat existing risk measures at predicting abnormal firm-level volatility, held up on transcripts after the model's training cutoff (Jan 2022 – Mar 2023), and caught emerging risks. — [arXiv](https://arxiv.org/abs/2310.17721v2); [Harvard Law School Forum](https://corpgov.law.harvard.edu/2023/11/01/from-transcripts-to-insights-uncovering-corporate-risks-using-generative-ai/)
- **LLM risk signals inside a trader:** FinRL-DeepSeek (arXiv 2502.07393) feeds LLM risk assessments from news into a CVaR-PPO trader, backtested on the Nasdaq-100 over 2019–2023. — [arXiv](https://arxiv.org/pdf/2502.07393). A May 2026 follow-up preprint (not peer reviewed) reports that its constraints cut max drawdown only from −58.37% to −56.09%. — [Cambridge Open Engage](https://www.cambridge.org/engage/coe/article-details/6a071d88d1922e37d57d1470)
- In LiveTradeBench, news was the factor agents cited most, but stock agents put more weight on price trends than Polymarket agents did. — [arXiv HTML](https://arxiv.org/html/2511.03628v1). In StockBench, removing news cut returns only modestly (see §2). — [arXiv HTML](https://arxiv.org/html/2510.02209v1)

### Inferences
- The documented LLM news edge is in small caps, over 1–2 days, mostly before 2023, and sensitive to costs. It is unlikely to carry over to NVDA, GOOGL, MSFT, TSLA and SK hynix tokens in Oct–Nov 2026 after tokenized-stock fees and gas. That argues against widening the LLM's role to generating signals or adding exposure.
- Three findings support the current **downside-only, event-gated** role: the asymmetry towards negative news (short leg about 3× long leg), slow price response under limits to arbitrage, and evidence that LLMs extract risk well. The role suits rare, verifiable, high-impact events such as trading suspensions and issuer filings, where a miss is costly and events are infrequent.
- The main failure mode of such a filter is **false positives during rallies** (see FINSABER, §2). The design should favour precision (verified sources, a closed list of event types), and an exposure cut should have an explicit, rule-based path back in. Otherwise one spurious cut in an up market can take the team out of the top 3.
- Any backtest of the veto on 2023–2025 news using a model trained through 2025 is contaminated by memorisation. Its precision should be judged only on events after the model's training cutoff, or on synthetic or replayed cases.

### Gaps
- I found no study of LLM vetoes or risk filters on long-only mega-cap portfolios at 1–14 day horizons, and none on how tokenized stocks react to news (for example, news arriving while the underlying exchange is closed).
- I did not retrieve Chen–Kelly–Xiu's results for large caps or how quickly their signal decays.
- I did not retrieve the effect sizes in Kim–Muhn–Nikolaev.
- Lopez-Lira–Tang report no separate large-cap coefficient. They report only that the cumulative return before costs stays above 300% after dropping stocks priced at $5 or less and stocks below the 20th NYSE size percentile.

## 4. Implications for LARP: target exposure, concentration vs diversification across the five names, the LLM's role, and how much activity is needed

### Takeaway
Keep the invested, low-turnover, rule-based core and the LLM's reduce-only, event-gated role. The evidence supports both, and it argues against making the LLM a signal generator. But an equal-weight basket up to 95% is essentially a bet on the factor common to all five names, and its chance of a top-3 finish depends on how invested the rest of the field is. For a top-3-of-25 payoff, theory supports more idiosyncratic or concentrated exposure than a diversification-first design gives, limited by the organisers' scrutiny of drawdown and logs. A small number of deliberate, logged trades is enough activity; turnover is the documented failure mode.

### Cited Findings
- Ranking is by % equity change; fees and gas reduce the score; "number of trades" and "call volume" are not scored; the tie-break is lower max drawdown; there is no live leaderboard. — [docs/official/source_page.md](../../docs/official/source_page.md)
- The entry "must be genuinely agentic", and "larger spend and higher call volume earn nothing on their own". — [docs/official/source_page.md](../../docs/official/source_page.md) (line 61)
- Organisers look at "completed trades' PnL, drawdown, logs, and code repo all together", and not trading is "definitely not what this competition is about". The working assumption is that a mostly-cash default is penalised, and it is open whether open positions count or only completed round trips (Q-39). — [docs/skill/SKILL.md](../../docs/skill/SKILL.md) (F-115, Q-17)
- With few winners, choose more variance and lower correlation with rivals. — [Gaba, Tsetlin & Winkler 2004](https://pubsonline.informs.org/doi/pdf/10.1287/opre.1030.0098). Convex payoffs favour putting everything in the most promising alternative. — [Schwarz & Severinov 2010](https://ideas.repec.org/a/ucp/jlabec/v28y2010i4p893-922.html)
- The large losses among LLM traders were driven by overtrading and leverage. — [BigGo Finance](https://finance.biggo.com/news/5BSX_Z0BaoGGrU-ID27J); [Forklog](https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/). LLM strategies tend to be under-invested in bull markets. — [FINSABER](https://arxiv.org/html/2505.07078v5)

### Inferences
- **Target exposure:**
  - Under the rank payoff, staying near fully invested (the existing 95% cap) is preferable to sitting half-invested. In the illustrative Monte Carlo, a 50% diversified basket had about 0–5% P(top 3) in every field.
  - The trend guard's move to cash in a falling market is, by accident, also a contrarian rank strategy: being in cash while an invested field falls gave about 24% P(top 3) in the mixed field. Its value depends on firing early and on how often it whipsaws; that needs calibration against the team's own data before the freeze.
- **Concentration (a design choice for the team; not a price view):**
  - **(a) Status quo, an equal-weight basket.** Good if most rivals are cautious; poor if most are invested or concentrated. It is highly correlated with any field that also holds the basket.
  - **(b) Tilt towards one or two names with the highest volatility or idiosyncratic risk, chosen on volatility rather than a forecast.** This gives the most field-robust P(top 3) in the Monte Carlo, but a heavier left tail (P(loss > 10%) about 16% vs 9%) and more exposure to the F-115 drawdown review.
  - **(c) Core plus satellite:** an equal-weight core with one overweight name. This sits in between.

  Which name the field crowds into (NVDA is a plausible candidate) is unknown. Choosing different weights from the likely consensus is the "distance yourself" lever. Any change must be recorded as a ledger idea with pass criteria first (AGENTS.md), committed before the freeze (Oct 27–29 activation; SKILL.md Q-40 notes a plan to freeze on Oct 26), and cannot be changed during the run.
- **The LLM's role:**
  - *Keep* it reduce-only and event-gated.
  - *Strengthen* precision: verified primary sources, a closed list of event types, cuts sized by severity, and an explicit rule-based re-entry.
  - *Log* every veto and non-veto with its reasoning, so the "genuinely agentic" claim and the F-115 log review rest on traceable decisions rather than on call volume.
  - *Do not loosen* it into generating buy signals or adding exposure: the evidence on mega-cap, multi-day, after-cost edge is weak and decaying, and benchmarks show LLM traders underperform passive exposure in rising markets.
  - A shadow mode, in which the LLM's signals are logged but never traded, could show agentic depth without affecting trades. Whether judges reward this is unknown.
- **Activity:**
  - The number of trades earns nothing, and fees and gas reduce the score. But F-115 penalises not trading and refers to "completed trades' PnL".
  - The evidence-consistent minimum is a deterministic, low-frequency schedule: an initial entry, then a few scheduled rebalances or partial trims (for example, weekly) that close some positions and record realised PnL.
  - This avoids the Alpha Arena overtrading pattern (hundreds to over a thousand trades) while making sure the record is not empty if only round trips count (Q-39 open).
- **Drawdown:** the tie-break is close to irrelevant for a top-3 finish, but drawdown counts in the organisers' combined assessment. The loss ladder is the right tool to cap the left tail that a concentrated tilt would add.

### Gaps
- The field's composition and level of investment are unknown, and there is no leaderboard during the run, so the choice between (a), (b) and (c) cannot be tuned to rivals.
- The F-115 weights (Q-39) are unknown, as is whether "completed trades" means round trips.
- Fee, gas and volatility levels for each tokenized stock (especially SK hynix's liquidity and trading hours against the underlying) were not researched here and are needed to calibrate both the Monte Carlo and the rebalance schedule.
- I found no external evidence on how judges weigh a reduce-only LLM against an LLM that sends orders when assessing "genuinely agentic". The official text names harness-layer guardrails and verification as legitimate innovation (source_page line 61), but how judges will weigh that is unconfirmed.

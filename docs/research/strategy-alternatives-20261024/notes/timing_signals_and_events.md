# Short-horizon timing signals and scheduled events for a long-only 5-stock basket (window Oct 29 – Nov 12, 2026)

Scope: NVDA, GOOGL, 000660.KS (SK hynix), TSLA, MSFT or USDT; long-only, unleveraged; ~10 US regular sessions; 15–25 bp per side; rules frozen before Oct 29, 2026. Research compiled Oct 24, 2026. This is design research for a competition agent, not investment advice, and contains no price forecasts.

Window mechanics used throughout (computed from the calendar, not from a source): Oct 29 is a Thursday. US daylight saving time ends Sunday Nov 1, 2026 ([Time Out](https://www.timeout.com/usa/news/when-do-the-clocks-go-back-in-2026-heres-when-daylight-saving-time-officially-ends-100626); [Almanac](https://www.almanac.com/daylight-saving-time-ends)), so the NYSE core session (9:30–16:00 ET per [NYSE](https://www.nyse.com/markets/hours-calendars)) is 13:30–20:00 UTC on Oct 29–30 and 14:30–21:00 UTC from Mon Nov 2. "No new buys after Nov 9 21:00 UTC" therefore equals the Nov 9 16:00 EST close (last buying session = Mon Nov 9). "Flat by Nov 11 15:00 UTC" equals 10:00 EST, i.e. only the first 30 minutes of the Nov 11 session. Sessions in the window: Oct 29, Oct 30, Nov 2, 3, 4, 5, 6, 9, 10, and a 30-minute stub on Nov 11.

## 1. Short-horizon time-series momentum and moving-average trend filters (1–10 day lookbacks), whipsaw and cost drag

### Takeaway
There is no credible evidence that a 1–10 day trend filter on large-cap US equities adds return after costs in recent decades; the best-documented short-MA effects are concentrated in high-volatility/small portfolios and pre-1987 data, and the published TSMOM evidence is for 1–12 *month* lookbacks (and is itself contested). At a 10-session horizon the guard is insurance with a measurable premium (~0.33–0.50 pp per 10 sessions in LARP's own backtest), and slower or wider-band variants mainly reduce that premium by flipping less.

### Cited Findings
- Moskowitz, Ooi & Pedersen (2012) document time-series momentum as return persistence for 1 to 12 *months* that partially reverses over longer horizons; the standard construction is a 12-month lookback with a 1-month hold, robust across lookback/holding periods — [SSRN abstract](https://papers.ssrn.com/abstract=2089463); [AQR dataset description](https://www.aqr.com/insights/datasets/time-series-momentum-original-paper-data).
- The original TSMOM abnormal-return results do not account for strategy execution costs — [CBS thesis](https://research-api.cbs.dk/ws/portalfiles/portal/60699508/815971_Masters_thesis_final_Magnus_Bojesen.pdf).
- Huang, Li, Wang & Zhou (JFE 2020, "Time series momentum: Is it there?"): asset-by-asset regressions show little evidence of TSMOM in or out of sample; the pooled t-statistic is below bootstrap critical values; TSMOM's investment performance is "virtually the same" as a strategy based on the historical sample mean that needs no predictability; "the evidence on TSM is weak" — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html); [Alpha Architect summary](https://alphaarchitect.com/an-empirical-challenge-for-trend-following/).
- Han, Yang & Zhou (JFQA 2013): a 10-day moving-average timing rule (hold portfolio when above its MA, T-bills otherwise; also tested 20/50/100/200 days) applied to volatility-decile portfolios of US stocks, 1963–2009, produces CAPM/FF3 abnormal returns that are economically large for *high-volatility* portfolios and larger than standard momentum — [IDEAS](https://ideas.repec.org/a/cup/jfinqa/v48y2013i05p1433-1461_00.html); [CXO Advisory](https://www.cxoadvisory.com/volatility-effects/combining-realized-volatility-and-simple-moving-averages).
- Secondary summaries disagree on the decile pattern: the CFA Institute digest says MA-timing returns rise with volatility decile (excluding the top decile) from 8.42% to 18.70% a year; CXO says the highest alphas are in the most volatile stocks — [CFA Institute digest](https://rpc.cfainstitute.org/research/cfa-digest/2014/08/a-new-anomaly-the-cross-sectional-profitability-of-technical-analysis-digest-summary); [CXO Advisory](https://www.cxoadvisory.com/volatility-effects/combining-realized-volatility-and-simple-moving-averages).
- Zakamulin (S&P Composite monthly, 1860–2009, 0.25% one-way friction): all MA-type timing rules generate many false signals in both bull and bear trends; they tend to outperform in bear states; there is no statistically significant outperformance in the second half of the sample; outperformance is more likely for long horizons, equal weighting of past returns and a dynamic (rolling-window) lookback; the simple momentum rule was best out of sample — [Zakamulin working paper](https://c.mql5.com/forextsd/forum/214/Market%20Timing%20with%20Moving%20Averages%20-%20Anatomy%20and%20Performance%20of%20Trading%20Rules.pdf); [SSRN 2677212](https://papers.ssrn.com/abstract=2677212).
- Reported "too good to be true" MA results are attributed to look-ahead bias in the simulated trading; without it the MA strategy is statistically indistinguishable from buy-and-hold — [Alpha Architect on Zakamulin](https://alphaarchitect.com/2016/04/the-moving-average-research-king-valeriy-zakamulin/).
- Sullivan, Timmermann & White (JF 1999) applied White's Reality Check to the Brock-Lakonishok-LeBaron universe of daily technical rules on 100 years of DJIA data — [FMG discussion paper](https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf). On the 1987–1996 out-of-sample decade the best rule earned a statistically insignificant 8.63% a year *before* costs (secondary report) — [farmdoc/NCCC-134 paper](https://farmdoc.illinois.edu/assets/meetings/nccc134/conf_2004/pdf/confp23-04.pdf). Later work cites STW/White as finding no significantly profitable rule for DJIA, S&P 500 or S&P 500 futures — [Re-examining technical analysis (SPA test)](https://c.mql5.com/forextsd/forum/211/Re-Examining%20the%20Profitability%20of%20Technical%20Analysis%20with%20Whitets%20Reality%20Check%20and%20Hansen9s%20SPA%20Tes.pdf).
- Individual US stocks show significant *negative* daily autocorrelation over 1960–2019, strongest in the 1990s and weaker but still significant after 2000 — [Lewellen, Dartmouth](https://faculty.tuck.dartmouth.edu/images/uploads/faculty/jonathan-lewellen/Autocorrelations.pdf).
- A 2026 arXiv preprint reports SPY lag-1 daily autocorrelation of about −0.081, stable across decades, while finding no statistical support for a simple fade-yesterday strategy (preprint; figures not independently verified) — [arXiv 2606.29591](https://arxiv.org/pdf/2606.29591).
- Rolling 60-month autocorrelation of *monthly* SPY returns through Oct 2020 switched sign over time with no persistent trend — [CXO Advisory](https://cxoadvisory.com/?p=34705).

### Inferences
- The two literatures that support short MA rules (Han-Yang-Zhou; pre-1987 BLL-type daily rules) do not describe this basket: these are mega-caps in a 5-name equal-weight index, and STW show daily rules failing out of sample after 1987. Mild negative daily autocorrelation (Lewellen; arXiv) is the opposite of what a 5-day trend rule needs; a 5-session mean with ±1% bands is plausibly *selling into short-term dips that tend to partly reverse*, which is consistent with LARP's measured whipsaw.
- Cost arithmetic for the current guard (my calculation from the brief's numbers): ~35 flips/year ≈ 1.4 flips per 10 sessions; each flip trades 35% of NAV; at 15–25 bp/side that is ≈5–9 bp per flip, ≈7–12 bp per 10 sessions in explicit costs. The rest of the measured 0.33–0.50 pp per 10 sessions is therefore mostly *path* loss (de-risking ≥1% below the mean and re-risking ≥1% above it costs roughly 2% × 35% ≈ 0.7 pp of NAV per full whipsaw round-trip, before mean drift). Widening the band reduces flips but raises the path loss per round-trip; lengthening the mean reduces flips. Neither is supported as alpha; both just change the insurance premium.
- With only ~10 sessions, a slow filter (e.g. 20–50 session mean) will rarely flip inside the window, so it behaves like near-constant 95% exposure plus a tail-risk switch. The literature (Zakamulin: rules "tend to outperform in bear states") supports the guard only as crash insurance, not as a return source.
- Pre-registrable variants that the evidence does not contradict (to be backtested on LARP's own 2019–2026 data with costs before freezing; pass criteria first per AGENTS.md): (a) slower mean (10 or 20 sessions) with the same ±1% band; (b) asymmetric hysteresis (e.g. exit at −2%/−3% below mean, re-enter at +1%); (c) confirmation requirement (two consecutive closes beyond band); (d) a one-way ratchet for the final days (allowed to de-risk, never re-risk after a fixed date, consistent with the Nov 9 no-new-buys rule). Evaluate them on flips/year, cost per 10 sessions and worst 10-session drawdown, not on mean return alone, because a 10-session sample cannot distinguish their means.
- Look-ahead trap to avoid: computing the signal on a close and trading at that same close. The basket's SK hynix component closes at 06:30 UTC on KRX while US names close 20:00/21:00 UTC, so an "equal-weight basket close" mixes stale and fresh prices; a rule should fix which timestamp each constituent uses.

### Gaps
- I did not obtain the MOP (2012) tables for 1-week or 1-month lookbacks on equity index futures specifically; whether TSMOM at ≤1-month lookback is positive for equity indices was not verified.
- No peer-reviewed study found that directly compares 5-day/±1% vs wider/slower filters on mega-cap baskets after 2010; the comparison must come from LARP's own backtest.
- Han-Yang-Zhou's exact per-decile numbers were only available via conflicting secondary summaries.

## 2. Short-term reversal and cross-sectional momentum among a handful of names (1–2 week horizon, net of costs)

### Takeaway
Classic 1-week/1-month reversal (Jegadeesh 1990; Lehmann 1990) is much weaker in large caps, is largely consumed by costs in broad universes, and flips sign to short-term *momentum* among high-turnover, heavily covered stocks (Medhat & Schmeling 2022). With five names, 15–25 bp per side and ~10 sessions, a reversal or momentum tilt has an ambiguous sign for these specific stocks and an expected edge that is unlikely to clear costs; the evidence supports no tilt.

### Cited Findings
- De Groot, Huij & Zhou (2011): transaction costs consume most short-term reversal profit, mainly because of small-cap trading; restricting to large caps significantly reduces costs, and turnover-reducing portfolio construction lowers them further — [EFMA 2011 paper](https://efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2011-Braga/papers/0259_update.pdf).
- Medhat & Schmeling (RFS 2022, "Short-term Momentum"; NYSE/AMEX/Nasdaq nonfinancial stocks, July 1963–Dec 2018): sorting on prior-month return and share turnover shows reversal among low-turnover stocks but short-term *momentum* among high-turnover stocks; short-term momentum is as profitable and persistent as conventional momentum, survives transaction costs, and is strongest among the largest, most liquid, most covered stocks — [CEPR DP15857](https://repec.cepr.org/repec/cpr/ceprdp/DP15857.pdf); [City Research Online](https://openaccess.city.ac.uk/id/eprint/31278/).
- Per a summary of Medhat & Schmeling: the reversal premium is 0.84%/month among large caps (t = 5.45) vs 1.41%/month among small caps, and for the full universe the average monthly transaction cost of 1.94% subsumes the average gross reversal return — [Alpha Architect](https://alphaarchitect.com/short-term-momentum/).
- Blitz, Huij, Lansdorp & Verbeek (J. Financial Markets 2013): reversal on *residual* returns (vs a rolling 36-month FF3 model, standardized) is significant net of trading costs even restricted to large caps after 1990 — [Erasmus repository](https://repub.eur.nl/pub/40707); [Robeco summary](https://www.robeco.com/en-int/insights/2011/11/short-term-residual-reversal). A secondary summary of the 1926–2008 sample (stocks above NYSE median size) gives 1.34% vs 0.97% monthly gross for residual vs conventional reversal — [CXO Advisory](https://www.cxoadvisory.com/technical-trading/purified-short-term-stock-reversal/).
- Da & Schaumburg find reversal within S&P 500 stocks linked to stock-specific liquidity events, consistent with a premium for supplying immediacy — [Kellogg research page](https://www.kellogg.northwestern.edu/academics-research/research/detail/2008/short-run-reversal-in-the-market-for-large-stocks/?p=1).
- Lou, Polk & Skouras (JFE 2019) test 14 strategies: momentum profits accrue entirely overnight, while reversal and many other strategies earn their profits intraday — [LSE PDF](https://personal.lse.ac.uk/polk/research/TugOfWar.pdf); [LSE Research Online](https://researchonline.lse.ac.uk/id/eprint/87481).

### Inferences
- The published large-cap reversal premia are long-short decile spreads across hundreds of stocks. A long-only tilt among five correlated tech/semis names captures a small fraction of that spread with very high idiosyncratic noise; over ~2 weekly rebalances the expected gross gain is plausibly a few bp, against 30–50 bp round-trip on every unit of NAV moved.
- Medhat & Schmeling make the *sign* ambiguous for this basket: TSLA and NVDA are among the highest-turnover, most covered stocks, where the evidence points to continuation, not reversal. A pre-registered rule cannot pick a sign with confidence.
- Residual reversal (Blitz et al.) needs a 36-month factor model per stock and is designed for broad cross-sections; with five names and 10 sessions it is not a credible pre-registered rule.
- Lou-Polk-Skouras suggests that if any reversal edge exists, it is intraday (consistent with a regular-session-only agent), while momentum is overnight; this does not rescue the cost problem.
- Implication: keep the basket weight rule (equal-weight or whatever is already frozen) and avoid return-based tilts; if a tilt is tested, require it to beat equal weight net of 20 bp/side in LARP's own 2019–2026 backtest across rolling 10-session windows before freezing.

### Gaps
- No study found on 1–2 week reversal or momentum within a 5-stock mega-cap universe after 2015.
- Turnover figures for the five names relative to the Medhat-Schmeling breakpoints were not checked.
- Original Jegadeesh (1990) and Lehmann (1990) effect sizes were not retrieved; they are older full-universe results and were not re-verified here.

## 3. Calendar effects in this exact window (Halloween, turn-of-month, pre-holiday, day-of-week, US midterm, overnight vs intraday)

### Takeaway
Turn-of-the-month (Oct 30, Nov 2, 3, 4) and the midterm-election seasonal (Election Day Nov 3, Q4 of a midterm year) are the only calendar effects with reasonably persistent, if contested, recent support that fall inside the window; both argue *against* being de-risked in early November rather than for leverage. The Halloween effect is a half-year effect too diffuse to matter over 10 sessions; the weekend/day-of-week effect has disappeared; there is no NYSE holiday in the window (so no pre-holiday effect); the overnight-return premium is persistent but is captured automatically by holding.

### Cited Findings
**Halloween / "Sell in May"**
- Bouman & Jacobsen (AER 2002) found the effect in 36 of 37 countries, strongest in Europe — [LGT](https://www.lgt.com/at-en/insights/investment-strategies/how-much-truth-is-there-in-sayings-about-stock-markets--85452).
- Zhang & Jacobsen, "The Halloween indicator, 'Sell in May and Go Away': Everywhere and all the time" — [University of Nottingham Ningbo record](https://research.nottingham.edu.cn/en/publications/the-halloween-indicator-sell-in-may-and-go-away-everywhere-and-al/fingerprints/); it covers all 114 stock market indices with data, with UK data back to 1693 — [LGT](https://www.lgt.com/at-en/insights/investment-strategies/how-much-truth-is-there-in-sayings-about-stock-markets--85452).
- Arendas, Malacka & Schwarzova (IJFS 2018): among DJIA blue chips 1980–2017 most stocks had higher Nov–Apr than May–Oct average returns, but the effect was significant in only 18 of 35 stocks — [IDEAS](https://ideas.repec.org/a/gam/jijfss/v6y2018i2p42-d140703.html).

**Turn of the month (TOM)**
- McConnell & Xu: using CRSP daily returns, the TOM effect persisted in 1987–2005, and all of the market's positive excess return came in the four-day TOM window — [Purdue CIBER working paper](https://docs.lib.purdue.edu/ciberwp/43).
- Contrary: an Atlanta Fed working paper (2000) found the TOM effect in S&P 500 futures disappeared after 1990, carrying over to the spot index — [Fed in Print](https://fedinprint.org/item/fedawp/13394/original).
- 401(k) evidence (AEA 2022 paper): the TOM effect is still present, but stocks held by retirement funds with month-end inflows do not show a stronger effect, challenging the payroll-flow explanation — [AEA 2022 preliminary paper](https://aeaweb.org/conference/2022/preliminary/paper/iQikdBKZ).
- Practitioner backtest 1980–Q3 2024 (window: close before month-end through 3rd trading day): holding stocks only on those few days per month earned an annual return only 0.89% below being invested on all other days, with ~20% max drawdown — [ETF Trends](https://www.etftrends.com/etf-strategist-channel/turn-month-effect/).
- A J.P. Morgan structured-note index document backtests a turn-of-month index (first four and last two trading days vs mid-month, 1987–2024) and warns the effect may not persist — [SEC 424B3](https://www.sec.gov/Archives/edgar/data/19617/000121390025039323/ea0240777-01_424b3.htm).

**Pre-holiday / holidays**
- NYSE 2026 holidays are Jan 1, Jan 19, Feb 16, Apr 3, May 25, Jun 19, Jul 3, Sep 7, Nov 26 and Dec 25; early closes Nov 27 and Dec 24. Election Day (Nov 3) and Veterans Day (Nov 11) are not NYSE holidays — [NYSE hours & calendars](https://www.nyse.com/markets/hours-calendars).

**Day of week / weekend**
- Robins & Smith (2016, ~1,000 stocks 1926–2014): a structural break; since 1975 the Monday drop is insignificant (≈−0.05%) — [Fronteras Desk (ASU)](https://fronterasdesk.org/node/429504).
- Boston Fed (Fortune 1998): large significant negative weekend returns before 1987, no weekend drift after 1987, though weekend volatility stayed higher — [Boston Fed WP 98-6](https://www.bostonfed.org/-/media/Documents/Workingpapers/PDF/wp98_6.pdf).
- Industry portfolios 1926–2017: broad absence of weekend effects in most portfolios — [Emerald, JFEP](https://www.emerald.com/insight/content/doi/10.1108/JFEP-04-2019-0066/full/html); index data Jan 2010–May 2015: the weekend effect no longer exists in the USA — [Eunomia](https://ojs.akademiarac.edu.pl/index.php/eunomia/en/article/view/268).

**US midterm election (Tuesday Nov 3, 2026)**
- Date: the 2026 general election is Tuesday, November 3, 2026 — [Mecklenburg County elections](https://vote.mecknc.gov/upcoming-elections); [Washington Examiner](https://www.washingtonexaminer.com/news/4462055/dates-to-know-2026-midterm-elections/).
- Day after midterm elections: average S&P 500 gain 0.57%, positive 76.5% of the time (2018 analysis) — [Schaeffer's Research](https://www.schaeffersresearch.com/content/analysis/2018/10/31/what-midterm-elections-could-mean-for-stocks).
- Q4 of midterm years: S&P 500 average gain 6.6% since 1950, followed by 7.4% and 4.8% in the next two quarters (Carson Investment Research, as reported) — [WealthManagement.com](https://www.wealthmanagement.com/equities/wall-street-hopes-history-repeats-with-a-post-election-comeback); "over 6.5%" — [Esquire Bank](https://signature.esquirebank.com/wealth-management/midterm-year-seasonality-swings-favorable-for-stocks/). A Zacks piece attributes the 7.4% figure to Q1 of year 3, so quarter attributions conflict across sources — [Zacks](https://www.zacks.com/stock/news/2014377/).
- Capital Group: midterm years averaged 4.7% vs 9.5% for other years (back to 1930); the average one-year return after a midterm since 1950 was 15.4% — [Capital Group](https://www.capitalgroup.com/apac/capitalideas/en/articles/how-us-midterm-elections-affect-the-markets.html).
- Bank of America (via InvestingLive): the S&P 500 has risen in every 6- and 12-month period after a midterm since WWII; the index was up ~13% in 2026 vs a ~3% midterm-year average — [InvestingLive](https://investinglive.com/stock-market-update/s-p-500-defies-midterm-slump-as-bank-of-america-says-history-favours-post-election-gains/).
- The index climbed in the year after 32 of the last 38 midterms (since 1874) — [Motley Fool research](https://www.fool.com/research/midterm-election-year-stock-market-history/).

**Overnight vs intraday**
- Cliff, Cooper & Gulen ("Return differences between trading and non-trading hours: Like night and day"; published 2011 as "...The difference is day and night"), 1993–2006: overnight (16:00–09:30) returns strongly positive while trading-hour returns near zero or negative; for S&P 500 stocks average overnight ≈0.028%–0.048% vs daytime ≈−0.028% to 0.002% per day; holds for ETFs, index futures and stocks — [CXO Advisory](https://www.cxoadvisory.com/?p=1377); [IDEAS citation record](https://ideas.repec.org/r/pal/assmgt/v12y2011i2d10.1057_jam.2011.2.html).
- NY Fed (Boyarchenko, Larsen, Whelan) document an "overnight drift" in S&P 500 futures with the largest returns around 2–3 a.m. ET near the European open — [Liberty Street Economics](https://libertystreeteconomics.newyorkfed.org/tag/paul-whelan/).
- Lou, Polk & Skouras (2019): momentum profits accrue overnight, reversal and other strategies intraday; institutional rebalancing shifts the overnight-intraday spread by roughly 2% per month — [LSE PDF](https://personal.lse.ac.uk/polk/research/TugOfWar.pdf); [Alpha Architect](https://alphaarchitect.com/2015/02/overnight-momentum-vs-intraday-momentum/).
- For markets that trade around the clock there is no natural open/close, so the split depends on how sessions are defined — [CXO Advisory](https://www.cxoadvisory.com/?p=1377).

### Inferences
- TOM dates in window (Lakonishok-Smidt-style: last trading day + first three): Fri Oct 30, Mon Nov 2, Tue Nov 3, Wed Nov 4. Using the ETF Trends figure, ~4 TOM days/month earned nearly as much per year as the ~17 other days, implying several-times-higher average daily returns on TOM days (rough ratio, assumes the two halves have similar totals). A frozen rule can cheaply exploit this *defensively*: e.g. suppress trend-guard de-risking (or require a wider band) on Oct 30–Nov 4. It should not be used to raise exposure above 95% (no leverage permitted anyway).
- Election Day (Nov 3) sits inside the TOM window, and the day-after statistic (+0.57%, 76.5% positive) implies ~17 observations (13/17 = 76.5%), i.e. low statistical power and overlap with TOM and Q4 seasonality. Treat as "do not be underweight around Nov 3–4" rather than as a standalone signal.
- Midterm Q4 seasonality is ~19 observations since 1950 with overlapping causes; it supports a neutral-to-long prior for the whole window but cannot be quantified per session with any confidence.
- Halloween: the window straddles Oct 31/Nov 1, but the effect is defined over six-month halves; every 1 pp of half-year winter-minus-summer difference is only ~0.08 pp per 10 sessions (1/126 × 10), far below cost and noise. No rule should key off it.
- Day-of-week rules: no support; do not use.
- Overnight premium: because the tokens trade 24/7 and the agent holds through US nights, it collects whatever overnight premium exists simply by being invested. The practical implication is execution timing: re-risking trades placed near the US close and de-risking placed near the open would, under Cliff-Cooper-Gulen, forgo less of the overnight return than the reverse. This is a mild execution preference, not a signal, and its transfer to 24/7 on-chain token prices is unverified.
- SK hynix's KRX session (09:00–15:30 KST = 00:00–06:30 UTC) is the US "overnight", so for that component the "overnight vs intraday" split is reversed relative to the US names.

### Gaps
- No post-2010 peer-reviewed TOM study for US large caps was retrieved; the 1980–2024 figure is from a practitioner source (ETF Trends) and the 1987–2024 index from a structured-note document.
- A claim that the S&P 500 rose in 64% of midterm-year Novembers appeared in search output but could not be tied to a specific source; excluded.
- Exact winter-minus-summer magnitudes from Bouman-Jacobsen and Zhang-Jacobsen were not retrieved.
- Whether overnight/intraday patterns apply to tokenized stocks trading 24/7 on BNB Chain (which may track after-hours venues or be stale) was not researched.

## 4. Macro events in/near the window: FOMC dates and the pre-FOMC drift; CPI and jobs report dates

### Takeaway
No FOMC decision falls inside the window: the Oct 27–28 decision (18:00 UTC Oct 28) precedes it and the next meeting is Dec 8–9, so the pre-FOMC drift (which largely vanished after 2015 anyway) cannot be used. The scheduled macro shocks inside the window are Q3 GDP/September PCE (Oct 29), ECI (Oct 30), the October jobs report (Fri Nov 6, 13:30 UTC) and October CPI (Tue Nov 10, 13:30 UTC) — the CPI print lands on the last full session before the forced flat deadline.

### Cited Findings
- FOMC 2026: Jan 27–28, Mar 17–18*, Apr 28–29, Jun 16–17*, Jul 28–29, Sep 15–16*, **Oct 27–28**, **Dec 8–9*** (* = Summary of Economic Projections). September minutes were released Oct 7; minutes are released three weeks after the decision. 2027 tentative: Jan 26–27, Mar 16–17, Apr 27–28, Jun 8–9, Jul 27–28, Sep 14–15, Oct 26–27, Dec 7–8 — [Federal Reserve FOMC calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) (confirmed).
- The Oct 28 rate decision is scheduled for 2:00 p.m. ET — [PrimeXBT, citing Fed timing](https://primexbt.com/for-traders/alphabet-earnings-date/) (the standard 2:00 p.m. ET release time; 18:00 UTC under EDT).
- Lucca & Moench (NY Fed SR 512; JF 2015): the 24 hours before scheduled FOMC announcements account for more than 80% of the US equity premium over ~1994–2011; similar pre-announcement returns appear in other major equity indices but not in Treasuries — [EconPapers SR 512](https://econpapers.repec.org/RePEc:fip:fednsr:512); [NY Fed staff report PDF](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.pdf). Returns rose on average 49 bp in the 24 hours before announcements, Sept 1994–March 2011 (as restated in the Kurov et al. introduction) — [Kurov, Wolfe & Gilbert working paper](https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf).
- A 2018 NY Fed follow-up found continued pre-FOMC excess returns only at meetings with a Chair press conference — [Liberty Street Economics 2018](https://libertystreeteconomics.newyorkfed.org/2018/11/the-pre-fomc-announcement-drift-more-recent-evidence.html).
- Kurov, Wolfe & Gilbert (Finance Research Letters 2021, sample to Dec 2019): the drift "essentially disappeared after 2015", both with and without press conferences; reduced uncertainty is the suggested cause — [IDEAS/RePEc](https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html).
- Practitioner research argues the drift is much stronger in periods of high uncertainty/risk premium — [Quantpedia](https://vvv.quantpedia.com/tag/volatility-premium/page/2/).
- BLS October 2026 (ET): Employment Situation (Sep) Oct 2; CPI (Sep) Oct 14; PPI (Sep) Oct 15; **Employment Cost Index Q3: Fri Oct 30, 08:30**; Consumer Expenditures (annual 2025) Oct 29 10:00 — [BLS Oct 2026 schedule](https://www.bls.gov/schedule/2026/10_sched_list.htm) (confirmed; page last modified Feb 18, 2026 and "updated as needed").
- BLS November 2026 (ET): **JOLTS (Sep) Tue Nov 3, 10:00**; **Productivity & Costs Q3 (P) Thu Nov 5, 08:30**; **Employment Situation (Oct) Fri Nov 6, 08:30**; **CPI (Oct) and Real Earnings Tue Nov 10, 08:30**; Veterans Day Nov 11 (no release); PPI (Oct) Fri Nov 13, 08:30; Import/Export Prices Nov 17 — [BLS Nov 2026 schedule](https://www.bls.gov/schedule/2026/11_sched_list.htm) (confirmed, same caveat).
- BLS December 2026: CPI (Nov) Thu Dec 10, 08:30 ET — [BLS Dec 2026 schedule](https://www.bls.gov/schedule/2026/12_sched_list.htm).
- BEA: **GDP Q3 advance estimate + Personal Income & Outlays (Sep, incl. PCE prices) Thu Oct 29, 08:30 ET**; GDP second estimate + Personal Income (Oct) Nov 25; third estimate Dec 23 — [BEA release schedule](https://www.bea.gov/index.php/news/schedule/full). BEA rescheduled releases after the 2025 shutdown, so dates can shift — [BEA blog Jan 7, 2026](https://bea.gov/news/blog/2026-01-07/economic-release-schedule-updates-gdp-personal-income-and-outlays).

### Inferences
- UTC times (my conversions): Oct 28 FOMC decision 18:00 UTC; Oct 29 GDP/PCE 12:30 UTC (EDT); Oct 30 ECI 12:30 UTC; Nov 3 JOLTS 15:00 UTC (EST); Nov 6 jobs 13:30 UTC; Nov 10 CPI 13:30 UTC — all 8:30 ET releases land one hour before the US open, so a regular-session-only agent always trades *after* the print, at the open.
- Minutes of the Oct 27–28 meeting would be due ~Nov 18 under the three-week rule (inference; not yet listed by the Fed), i.e. after the window.
- Pre-FOMC drift: unusable in-window and decayed; no rule should reference it. If LARP were live on Oct 28, the post-2015 evidence still would not support a pre-FOMC overweight.
- The Nov 10 CPI print is the last big scheduled macro shock before the forced liquidation (Nov 11 by 15:00 UTC). A frozen rule could pre-decide whether to hold or reduce exposure into Nov 10's open (e.g. begin the wind-down at the Nov 9 close or Nov 10 open) so the exit is not forced into a 30-minute Nov 11 stub after a CPI move. This is risk management, not an expected-return signal.
- Veterans Day (Nov 11) is not an NYSE holiday; US bond markets commonly close (SIFMA recommendation not verified here), which may thin cross-asset liquidity on the exit morning.

### Gaps
- Fed Chair press conference schedule and any 2026-specific policy context were not researched.
- ISM Manufacturing (conventionally first business day, Nov 2), ISM Services (~Nov 4), ADP, the Treasury quarterly refunding (conventionally early November) and the SIFMA Veterans Day bond-market recommendation were not verified; treat as unconfirmed.
- Bank of Korea November 2026 meeting date and Korean data releases (relevant to 000660.KS) were not researched.
- Effect sizes of CPI/jobs announcement-day returns for mega caps after 2015 were not retrieved (e.g. Savor & Wilson 2013 on macro announcement days was not checked).

## 5. Company events: Q3 2026 earnings dates, PEAD for mega-caps, earnings-day volatility, holding through earnings

### Takeaway
Every constituent except NVIDIA reports *before* the window: TSLA reported Oct 21; SK hynix, MSFT and GOOGL report on Oct 28 (SK hynix before the Seoul open; MSFT and GOOGL after the US close). Oct 29, day 1 of the challenge, is therefore the US reaction session for MSFT and GOOGL. NVIDIA's Q3 FY2027 report is expected ~Nov 18 (unconfirmed), after the window. Large-cap PEAD has largely disappeared since ~2006 (contested), and the earnings-announcement premium is unavailable because no constituent announces inside the window, so earnings mainly matter as a source of day-1 noise for any trend signal.

### Cited Findings
**Dates**
- **SK hynix (000660.KS) Q3 2026: Wed Oct 28, 2026, press release before 09:00 KST, conference call 09:00 KST** (= Oct 28 00:00 UTC) — **confirmed**, [SK hynix newsroom](https://news.skhynix.com/en/?p=13734); SK hynix files 6-Ks with the SEC — [SEC 6-K](https://www.sec.gov/Archives/edgar/data/0002120882/000119312526420934/d413172d6k.htm). US calendars list it as Oct 27 after close for the US-listed SKHY line, i.e. the same release on US time — [TipRanks](https://www.tipranks.com/stocks/skhy/earnings).
- **Microsoft FY27 Q1: Wed Oct 28, 2026 after market close; webcast 2:30 p.m. PT (5:30 p.m. ET)** — **confirmed** per Microsoft's Oct 7, 2026 release as reported by [Finviz headline "Microsoft Announces Quarterly Earnings Release Date"](https://finviz.com/news/400058/microsoft-announces-quarterly-earnings-release-date) (page returned HTTP 403 to my fetch; date/time taken from the search summary of that release) and [CM Elite Group](https://www.cmelitegroup.com/knowledge-hub/microsoft-earnings-date-fiscal-q1-2027-report-time-estimates-and-expected-move/). Cross-check on Microsoft IR before freezing.
- **Alphabet Q3 2026: Wed Oct 28, 2026 after close; call 4:30 p.m. ET (1:30 p.m. PT)** — reported as confirmed by an Alphabet IR announcement on Oct 6, 2026 by [PrimeXBT](https://primexbt.com/for-traders/alphabet-earnings-date/); listed as not yet officially confirmed by [days.to](https://days.to/alphabet-earnings); I could not verify on abc.xyz (page content did not render). Treat as **expected / likely confirmed**. Prior-year pattern: Q3 2025 call was Oct 29, 2025 at 2:30 p.m. PT — [Alphabet IR 2025](https://abc.xyz/investor/news/news-details/2025/Alphabet-Announces-Date-of-Third-Quarter-2025-Financial-Results-Conference-Call-2025--ZwUcLWeND/default.aspx).
- **Tesla Q3 2026: reported Wed Oct 21, 2026 after market close** — **confirmed (already happened)**, [Electrek](https://electrek.co/2026/10/21/tesla-tsla-q3-2026-financial-results/).
- Tesla 2026 annual shareholder meeting: Thu Dec 3, 2026, 3:00 p.m. CT (after window); record date Oct 13 — **confirmed**, [SEC DEF 14A](https://www.sec.gov/Archives/edgar/data/0001318605/000110465926116700/tm267596-1_def14a.htm); [Drive Tesla Canada](https://driveteslacanada.ca/news/tesla-2026-annual-shareholder-meeting-december-3/).
- **NVIDIA Q3 FY2027: expected Wed Nov 18, 2026, after close (5:00 p.m. ET)** — **expected / unconfirmed**, [days.to](https://days.to/nvidia-earnings); also a prediction-market listing — [Manifold](https://manifold.markets/Terminator2/what-will-nvidias-q3-fiscal-2027-re). Pattern: the Q2 FY27 call (Aug 26, 2026, 2 p.m. PT) was announced Jul 29, 2026 — [NVIDIA IR](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Sets-Conference-Call-for-Second-Quarter-Financial-Results/default.aspx); last year's Q3 call (Nov 19, 2025) was announced Oct 29, 2025 — [NVIDIA IR 2025](https://investor.nvidia.com/news/press-release-details/2025/NVIDIA-Sets-Conference-Call-for-Third-Quarter-Financial-Results/). Q2 FY27 results release — [SEC 8-K exhibit](https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000073/q2fy27pr.htm).
- NVIDIA GTC Washington, D.C. 2026: Nov 30–Dec 3, keynote Tue Dec 1, 2 p.m. ET (after window) — [NVIDIA GTC DC](https://www.nvidia.com/en-us/gtc/dc/).
- Read-through peers: AMD Q3 expected ~Tue Nov 3, 2026 after close (**unconfirmed**) — [days.to AMD](https://days.to/amd-earnings); Meta Q3 2026 reported Oct 21 after close per a single source (**unverified**) — [Pluang](https://pluang.com/en/news-feed/meta-umumkan-hasil-kuartal-tiga-2026).

**PEAD and the earnings-announcement premium**
- Martineau (Critical Finance Review 2022, "Rest in Peace Post-Earnings Announcement Drift"): prices fully reflect earnings surprises on the announcement date; for large stocks the drift has been absent since 2006 — [CFR PDF](https://cfr.ivo-welch.info/published/papers/martineau2021rest.pdf); [IDEAS](https://ideas.repec.org/a/now/jnlcfr/104.00000122.html).
- Contrary: two papers accepted in 2025 claim PEAD is "alive and well"; the disagreement largely reflects research-design choices — [UCLA Anderson Review](https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/).
- Earnings-announcement premium: Savor & Wilson report an annualized abnormal return of 9.9% for firms scheduled to report — [Wharton working draft](https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Draft20111215p_edited.pdf); Barber et al. (46 countries) estimate 66.8 bp in announcement months (8.02% annualized), attribute it to idiosyncratic volatility, and note arbitrage transaction costs are very high due to turnover — [Barber et al. PDF](https://en-coller.tau.ac.il/sites/nihul_en.tau.ac.il/files/media_server/Recanati/management/seminars/account/barber.pdf). A 2020 paper titled "The Disappearing Earnings Announcement Premium" exists (content not reviewed) — [IIMB ARC 2020](https://www.iimb.ac.in/ARC2020/Papers/The_Disappearing_Earnings_Announcement_Premium.pdf).

### Inferences
- Timeline (UTC): SK hynix results ~Oct 28 00:00 UTC (KRX reaction Oct 28 00:00–06:30 UTC); FOMC 18:00 UTC Oct 28; MSFT and GOOGL results after 20:00 UTC Oct 28; first US reaction session Oct 29 13:30–20:00 UTC = challenge day 1. If LARP starts in USDT at Oct 29 00:00 UTC and only trades in the US session, it will buy *after* the MSFT/GOOGL gap is priced, so it neither earns nor risks the announcement jump; with large-cap PEAD likely absent, the post-gap entry is fair-priced on average.
- Day-1 trend-guard contamination: the 5-session basket mean at the Oct 29 close will include Oct 28–29 earnings gaps for three of five names. A ±1% band can be triggered purely by an earnings gap. A frozen rule can neutralize this (e.g. no trend-guard state change on the first session after a constituent's earnings, or initialize the guard at "risk-on" for the first N sessions); this is a design choice to test, not an evidence-backed edge.
- NVDA: if the Nov 18 estimate holds, no constituent reports inside the window; any pre-earnings run-up for NVDA would fall after the Nov 9 no-new-buys cutoff and the Nov 11 flat deadline, so the earnings-announcement premium is not harvestable. If NVIDIA's date-announcement (expected ~late Oct) unexpectedly sets a date on or before Nov 11, the rule should treat it as a pre-registered "earnings inside window" case (decide in advance whether to hold through or cap that name).
- Peer read-throughs inside the window (e.g. AMD ~Nov 3, unconfirmed) are unscheduled-for-our-names shocks; no evidence supports trading them.

### Gaps
- Implied/historical earnings-day moves for MSFT, GOOGL, SK hynix were not retrieved, so day-1 volatility cannot be quantified here.
- Apple and Amazon Q3 2026 dates (likely late Oct, AI-capex read-through) were not found.
- Samsung Electronics' Q3 2026 final results date (memory read-through for SK hynix) was not verified.
- Whether the BNB Chain tokens reprice continuously during US after-hours (Oct 28 20:00–24:00 UTC) was not researched.

## 6. Scheduled-event calendar inside and just before the window (UTC, with confirmation status)

### Takeaway
Pre-window cluster: Oct 27–28 FOMC and Oct 28 SK hynix/MSFT/GOOGL earnings. Inside the window: macro prints (Oct 29, Oct 30, Nov 6, Nov 10), the TOM window (Oct 30–Nov 4), US Election Day (Nov 3), the DST switch (Nov 1), the last-buy session (Nov 9) and the forced exit on Nov 11 (Veterans Day, NYSE open). After the window: NVDA earnings (~Nov 18, expected), FOMC minutes (~Nov 18, inferred), Dec 8–9 FOMC.

### Cited Findings
| Date (2026) | Time | Event | Status / source |
|---|---|---|---|
| Wed Oct 21 | after US close | Tesla Q3 results | Confirmed (past) — [Electrek](https://electrek.co/2026/10/21/tesla-tsla-q3-2026-financial-results/) |
| Tue–Wed Oct 27–28 | decision 2:00 p.m. ET Oct 28 (18:00 UTC) | FOMC meeting (no SEP) | Confirmed — [Fed](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) |
| Wed Oct 28 | before 09:00 KST (≈00:00 UTC) | SK hynix Q3 results + call | Confirmed — [SK hynix](https://news.skhynix.com/en/?p=13734) |
| Wed Oct 28 | after close; call 5:30 p.m. ET (21:30 UTC) | Microsoft FY27 Q1 | Confirmed per Oct 7 release (fetch blocked) — [Finviz](https://finviz.com/news/400058/microsoft-announces-quarterly-earnings-release-date) |
| Wed Oct 28 | after close; call 4:30 p.m. ET (20:30 UTC) | Alphabet Q3 | Expected/likely confirmed — [PrimeXBT](https://primexbt.com/for-traders/alphabet-earnings-date/); unconfirmed per [days.to](https://days.to/alphabet-earnings) |
| Thu Oct 29 | 08:30 ET (12:30 UTC) | GDP Q3 advance; Personal Income & Outlays (Sep) | Scheduled — [BEA](https://www.bea.gov/index.php/news/schedule/full) |
| Thu Oct 29 | 13:30–20:00 UTC | Challenge day 1 = US reaction session to MSFT/GOOGL | Derived |
| Fri Oct 30 | 08:30 ET (12:30 UTC) | Employment Cost Index Q3 | Scheduled — [BLS](https://www.bls.gov/schedule/2026/10_sched_list.htm) |
| Fri Oct 30 – Wed Nov 4 | sessions | Turn-of-month window (last day of Oct + first 3 of Nov) | Derived from calendar; effect evidence in §3 |
| Sun Nov 1 | 02:00 local | US DST ends; US session shifts to 14:30–21:00 UTC | Confirmed — [Time Out](https://www.timeout.com/usa/news/when-do-the-clocks-go-back-in-2026-heres-when-daylight-saving-time-officially-ends-100626) |
| Tue Nov 3 | all day; results overnight into Nov 4 | US midterm general election (NYSE open) | Confirmed — [Mecklenburg County](https://vote.mecknc.gov/upcoming-elections); [NYSE](https://www.nyse.com/markets/hours-calendars) |
| Tue Nov 3 | 10:00 ET (15:00 UTC) | JOLTS (Sep) | Scheduled — [BLS](https://www.bls.gov/schedule/2026/11_sched_list.htm) |
| Tue Nov 3 | after close | AMD Q3 (peer read-through) | Expected/unconfirmed — [days.to](https://days.to/amd-earnings) |
| Thu Nov 5 | 08:30 ET (13:30 UTC) | Productivity & Costs Q3 (P) | Scheduled — [BLS](https://www.bls.gov/schedule/2026/11_sched_list.htm) |
| Fri Nov 6 | 08:30 ET (13:30 UTC) | Employment Situation (Oct) | Scheduled — [BLS](https://www.bls.gov/schedule/2026/11_sched_list.htm) |
| Mon Nov 9 | 21:00 UTC (= 16:00 EST close) | LARP no-new-buys cutoff | Challenge rule (brief) |
| Tue Nov 10 | 08:30 ET (13:30 UTC) | CPI (Oct) + Real Earnings | Scheduled — [BLS](https://www.bls.gov/schedule/2026/11_sched_list.htm) |
| Wed Nov 11 | NYSE opens 14:30 UTC | Veterans Day: NYSE open, no BLS releases; LARP must be flat by 15:00 UTC | [NYSE](https://www.nyse.com/markets/hours-calendars); [BLS](https://www.bls.gov/schedule/2026/11_sched_list.htm) |
| Fri Nov 13 | 08:30 ET | PPI (Oct) | Scheduled (after window) — [BLS](https://www.bls.gov/schedule/2026/11_sched_list.htm) |
| Wed Nov 18 | after close (5 p.m. ET est.) | NVIDIA Q3 FY2027 | Expected/unconfirmed — [days.to](https://days.to/nvidia-earnings) |
| ~Wed Nov 18 | 2:00 p.m. ET | FOMC minutes (Oct meeting) | Inferred from three-week rule — [Fed](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) |
| Thu Nov 26 / Fri Nov 27 | — | Thanksgiving closure / 1 p.m. early close | Confirmed (after window) — [NYSE](https://www.nyse.com/markets/hours-calendars) |
| Nov 30–Dec 3 | keynote Dec 1, 2 p.m. ET | NVIDIA GTC DC | Confirmed (after window) — [NVIDIA](https://www.nvidia.com/en-us/gtc/dc/) |
| Thu Dec 3 | 3 p.m. CT | Tesla annual meeting | Confirmed (after window) — [SEC DEF 14A](https://www.sec.gov/Archives/edgar/data/0001318605/000110465926116700/tm267596-1_def14a.htm) |
| Tue–Wed Dec 8–9 | — | FOMC with SEP | Confirmed (after window) — [Fed](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) |

### Inferences
- Any time-of-day logic in the agent written in UTC must handle the Nov 1 DST shift (open 13:30 UTC → 14:30 UTC; close 20:00 → 21:00 UTC); a hard-coded 13:30/20:00 UTC session would trade an hour early/late for 8 of the ~10 sessions.
- The Nov 11 exit stub is only 30 minutes long; a pre-registered wind-down that completes on Nov 10 (after the CPI open) or starts at the Nov 9 close would avoid concentrating exit costs and opening-auction volatility into that stub.
- Dates sourced from BLS/BEA pages are "scheduled" and could move (BEA moved releases after the 2025 shutdown); the frozen rule should key off the actual release (or avoid release-specific logic) rather than hard-coded dates where possible.

### Gaps
- MSCI November 2026 index review announcement/effective dates, monthly options expiry interactions (Nov 20 is after the window), Korean CSAT-day KRX late open, and BoK dates were not verified.
- Fed speaker schedule after the Oct 28 blackout ends was not researched.

## 7. Candidate scorecard: effect size, evidence quality, decay since publication, implementability as a fixed rule

### Takeaway
None of the candidates offers a credible positive expected edge large enough to justify extra trading at 15–25 bp per side over 10 sessions. The evidence-consistent uses are defensive: reduce whipsaw (slower/wider or event-aware trend guard), avoid de-risking during TOM/Election-week, and pre-plan the CPI-to-exit sequence. All are implementable without look-ahead because they depend only on calendar dates known before Oct 29 and on past prices.

### Cited Findings
| Candidate | Reported effect size (source) | Evidence quality | Decay since publication | Fixed-rule implementable? |
|---|---|---|---|---|
| 5-day MA / ±1% guard (current) | Short MA rules: best daily rule insignificant 8.63%/yr pre-cost OOS 1987–96 ([farmdoc](https://farmdoc.illinois.edu/assets/meetings/nccc134/conf_2004/pdf/confp23-04.pdf)); MA(10) alpha concentrated in high-vol portfolios ([CXO](https://www.cxoadvisory.com/volatility-effects/combining-realized-volatility-and-simple-moving-averages)) | Moderate (large literature, heavy data-snooping) | Strong decay after 1987 ([FMG DP303](https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf)) | Yes |
| Slower/long-horizon MA filter | Outperformance more likely at long horizons, mainly in bear states; not significant in 2nd half of 1860–2009 ([Zakamulin](https://c.mql5.com/forextsd/forum/214/Market%20Timing%20with%20Moving%20Averages%20-%20Anatomy%20and%20Performance%20of%20Trading%20Rules.pdf)) | Moderate | Weak post-1935 significance | Yes |
| TSMOM (1–12 m) | Persistence 1–12 months ([MOP SSRN](https://papers.ssrn.com/abstract=2089463)); weak asset-by-asset ([Huang et al.](https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html)) | Contested | n/a at 10-day horizon | Yes, but lookback ≫ window |
| Short-term reversal (1 w/1 m) | Large-cap 0.84%/mo long-short gross; costs 1.94%/mo full universe ([Alpha Architect](https://alphaarchitect.com/short-term-momentum/)) | High (old), but sign flips for high-turnover stocks ([CEPR](https://repec.cepr.org/repec/cpr/ceprdp/DP15857.pdf)) | Weaker after 2000 ([Lewellen](https://faculty.tuck.dartmouth.edu/images/uploads/faculty/jonathan-lewellen/Autocorrelations.pdf)) | Yes, but 5 names too few |
| Turn of month (Oct 30–Nov 4) | TOM days earned within 0.89%/yr of all other days combined, 1980–2024 ([ETF Trends](https://www.etftrends.com/etf-strategist-channel/turn-month-effect/)) | Moderate; mixed (gone post-1990 in futures per [Atlanta Fed](https://fedinprint.org/item/fedawp/13394/original)) | Contested | Yes (calendar) |
| Midterm Election Day / Q4 | Day after +0.57%, 76.5% positive ([Schaeffer's](https://www.schaeffersresearch.com/content/analysis/2018/10/31/what-midterm-elections-could-mean-for-stocks)); Q4 midterm +6.6% avg since 1950 ([WealthManagement](https://www.wealthmanagement.com/equities/wall-street-hopes-history-repeats-with-a-post-election-comeback)) | Low (≈17–19 obs, practitioner sources) | Unknown | Yes (calendar) |
| Halloween | 36/37 countries ([LGT](https://www.lgt.com/at-en/insights/investment-strategies/how-much-truth-is-there-in-sayings-about-stock-markets--85452)); 18/35 DJIA stocks significant ([IDEAS](https://ideas.repec.org/a/gam/jijfss/v6y2018i2p42-d140703.html)) | Moderate-high (long history) | Authors report persistence | Yes, but too diffuse for 10 sessions |
| Day-of-week / weekend | ≈0 since 1975/1987 ([Boston Fed](https://www.bostonfed.org/-/media/Documents/Workingpapers/PDF/wp98_6.pdf); [Fronteras](https://fronterasdesk.org/node/429504)) | High | Disappeared | Not worth it |
| Pre-holiday | No NYSE holiday in window ([NYSE](https://www.nyse.com/markets/hours-calendars)) | n/a | n/a | n/a |
| Pre-FOMC drift | 49 bp/24h, >80% of premium 1994–2011 ([EconPapers](https://econpapers.repec.org/RePEc:fip:fednsr:512)) | High (original) | Disappeared after 2015 ([IDEAS](https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html)) | No FOMC in window |
| PEAD (mega-caps) | Absent for large stocks since 2006 ([Martineau](https://cfr.ivo-welch.info/published/papers/martineau2021rest.pdf)); disputed ([UCLA Anderson](https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/)) | Contested | Strong decay | Yes, but no edge |
| Earnings-announcement premium | 9.9% annualized ([Savor & Wilson](https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Draft20111215p_edited.pdf)) | Moderate | Possibly disappearing ([IIMB title](https://www.iimb.ac.in/ARC2020/Papers/The_Disappearing_Earnings_Announcement_Premium.pdf)) | No constituent reports in window (NVDA expected Nov 18) |
| Overnight premium | S&P 500 stocks overnight ≈0.03–0.05%/day vs daytime ≈0, 1993–2006 ([CXO](https://www.cxoadvisory.com/?p=1377)) | High, persistent ([NY Fed](https://libertystreeteconomics.newyorkfed.org/tag/paul-whelan/)) | Persistent | Captured by holding; execution-timing preference only |

### Inferences
- Ranking for pre-registration (my judgment from the above): (1) reduce whipsaw cost of the existing guard via slower mean/wider or asymmetric band/confirmation, chosen on LARP's own backtest with costs; (2) calendar overrides that block de-risking on Oct 29 (earnings-gap day), Oct 30–Nov 4 (TOM + Election Day) — cheap, look-ahead-free, and aligned with the only calendar effects that plausibly survive; (3) a fixed wind-down schedule that exits across Nov 9 close/Nov 10 session rather than in the Nov 11 30-minute stub; (4) no cross-sectional reversal/momentum tilt and no PEAD/pre-FOMC logic.
- Statistical honesty: across ~10 sessions, none of these effects can be detected in realized performance; the rules should be judged ex ante on cost, turnover and drawdown control, and pass criteria written before any backtest (per repo rules).

### Gaps
- No direct evidence on how these effects behave in 24/7 tokenized-stock markets on BNB Smart Chain, or how token premiums/discounts to the underlying move around events.
- The scoring metric of the challenge (return vs risk-adjusted) determines whether an insurance-type guard is worth its premium; not covered here.

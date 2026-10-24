# Timing signals and events — verified schedules, unproven trading edges

PR276-RV01, checked 2026-10-24 SGT. Events are context and execution-risk inputs; their dates do not establish a
profitable directional rule. No timing overlay or scheduled-event limiter is activated by this research.

## Source checks and UTC conversion

| Event | Checked source / access | Schedule as published | UTC |
|---|---|---|---|
| FOMC | [Federal Reserve calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm), primary schedule | 2026 Oct 27–28; next scheduled meeting Dec 8–9 | No scheduled meeting inside Oct 29–Nov 12; unscheduled policy news remains possible |
| Microsoft FY27 Q1 | [Microsoft Oct 7 release](https://news.microsoft.com/source/2026/10/07/microsoft-announces-quarterly-earnings-release-date-69/), issuer full text | Oct 28 after close; webcast 14:30 Pacific | Webcast Oct 28 21:30 |
| Q3 GDP advance / September personal income and outlays | [BEA schedule](https://www.bea.gov/news/schedule/full), primary schedule | Oct 29 08:30 Eastern | Oct 29 12:30 |
| Employment Situation | [BLS November calendar](https://www.bls.gov/schedule/2026/11_sched_list.htm), primary schedule | Nov 6 08:30 Eastern | Nov 6 13:30 |
| CPI / real earnings | [BLS November calendar](https://www.bls.gov/schedule/2026/11_sched_list.htm), primary schedule | Nov 10 08:30 Eastern | Nov 10 13:30 |

Schedules can change; these are dated checks, not future confirmations. Pacific/Eastern UTC conversions use
`zoneinfo` with `America/Los_Angeles` / `America/New_York`. US daylight saving ends Nov 1: 08:30 Eastern becomes
13:30 UTC, versus 12:30 before the transition. The review receipt records deterministic conversion checks.
Microsoft's webcast time is not the exact publication instant of every earnings item.

Alphabet's earnings date was found in a syndicated release, not independently checked on its issuer site here.
The SK hynix primary link was unavailable; NVIDIA and Tesla dates in original leads were not reverified. They remain
leads and must not be promoted to confirmed events or operational scheduler inputs. Event identity and the rights,
publication/availability times and instrument mapping still matter before ingestion.

PF-04's Oct 29 14:00 first buy and Nov 10 19:00 flatten are team POLICY. Under the checked schedule they occur after
the respective GDP/PCE and CPI release times. That ordering does not establish favourable returns, quantify a gain
from changing the generator, or remove event risk. See [IDEA-084](../../../ledger/IDEA-084.md) and
[INCOMPLETE_WORK](../../../INCOMPLETE_WORK.md) for the calendar implementation gap.

## Signal evidence and transfer limits

Momentum/trend, short-term reversal, cross-sectional ranking, post-earnings drift, turn-of-month, election and
pre-FOMC effects study different universes and holding intervals. A published gross effect is not an executable
net edge in five correlated bStocks. Conversely, this review has not established that every such signal is negative
after costs. Treat each as a hypothesis with its original population, sample, portfolio construction and costs.

[EXP-008](../../../ledger/EXP-008.md)'s guard result is specific to its historical proxy and implementation; it does
not prove every 1–10-day filter loses, or justify silently disabling the adopted guard. [EXP-007](../../../ledger/EXP-007.md)
retains its own unchanged criteria. Original event-driven profit estimates and categorical “all signals fail”
scorecards are withdrawn because there is no common prospective, point-in-time LARP evaluation supporting them.

Underlying share prices and token quotes also have different availability, session and basis risks. A token premium,
weekend price move or stale underlying close is not a validated reversal signal; rights and freshness must be
satisfied and basis/cost inputs measured before any intended trade. RFQ expiry and `openState` cannot be bypassed.

## Qualification if reopened

Keith would specify a fixed rule, horizon, costs and kill criteria; Yao supplies authorized point-in-time source
inputs; Keegan reviews timestamps and lifecycle; Isaac accepts execution/gas/size coverage. Source rights and any
new principal service need their existing approvals. Freeze-compatible integration time and the cost of added
failure modes belong in the decision. Keeping a source lead is not authorization to ingest it or to tune on dev PnL.

## Provenance and original source leads

The [original research text](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/5d5b5e284fd0e70586ba83767a2d22b0fd726d1e/docs/research/strategy-alternatives-20261024/notes/timing_signals_and_events.md) is retained immutably.
PR276-RV01 replaces unsupported conclusions and repairs local references. The register preserves the original
external URLs for follow-up; inclusion does not verify availability, quality, rights or any claimed result. Only
sources explicitly assessed above have been rechecked; all other entries remain unverified leads.

- Lead 01: [Time Out](<https://www.timeout.com/usa/news/when-do-the-clocks-go-back-in-2026-heres-when-daylight-saving-time-officially-ends-100626>)
- Lead 02: [Almanac](<https://www.almanac.com/daylight-saving-time-ends>)
- Lead 03: [NYSE](<https://www.nyse.com/markets/hours-calendars>)
- Lead 04: [SSRN abstract](<https://papers.ssrn.com/abstract=2089463>)
- Lead 05: [AQR dataset description](<https://www.aqr.com/insights/datasets/time-series-momentum-original-paper-data>)
- Lead 06: [CBS thesis](<https://research-api.cbs.dk/ws/portalfiles/portal/60699508/815971_Masters_thesis_final_Magnus_Bojesen.pdf>)
- Lead 07: [IDEAS/RePEc](<https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html>)
- Lead 08: [Alpha Architect summary](<https://alphaarchitect.com/an-empirical-challenge-for-trend-following/>)
- Lead 09: [IDEAS](<https://ideas.repec.org/a/cup/jfinqa/v48y2013i05p1433-1461_00.html>)
- Lead 10: [CXO Advisory](<https://www.cxoadvisory.com/volatility-effects/combining-realized-volatility-and-simple-moving-averages>)
- Lead 11: [CFA Institute digest](<https://rpc.cfainstitute.org/research/cfa-digest/2014/08/a-new-anomaly-the-cross-sectional-profitability-of-technical-analysis-digest-summary>)
- Lead 12: [Zakamulin working paper](<https://c.mql5.com/forextsd/forum/214/Market%20Timing%20with%20Moving%20Averages%20-%20Anatomy%20and%20Performance%20of%20Trading%20Rules.pdf>)
- Lead 13: [SSRN 2677212](<https://papers.ssrn.com/abstract=2677212>)
- Lead 14: [Alpha Architect on Zakamulin](<https://alphaarchitect.com/2016/04/the-moving-average-research-king-valeriy-zakamulin/>)
- Lead 15: [FMG discussion paper](<https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf>)
- Lead 16: [farmdoc/NCCC-134 paper](<https://farmdoc.illinois.edu/assets/meetings/nccc134/conf_2004/pdf/confp23-04.pdf>)
- Lead 17: [Re-examining technical analysis (SPA test)](<https://c.mql5.com/forextsd/forum/211/Re-Examining%20the%20Profitability%20of%20Technical%20Analysis%20with%20Whitets%20Reality%20Check%20and%20Hansen9s%20SPA%20Tes.pdf>)
- Lead 18: [Lewellen, Dartmouth](<https://faculty.tuck.dartmouth.edu/images/uploads/faculty/jonathan-lewellen/Autocorrelations.pdf>)
- Lead 19: [arXiv 2606.29591](<https://arxiv.org/pdf/2606.29591>)
- Lead 20: [CXO Advisory](<https://cxoadvisory.com/?p=34705>)
- Lead 21: [EFMA 2011 paper](<https://efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2011-Braga/papers/0259_update.pdf>)
- Lead 22: [CEPR DP15857](<https://repec.cepr.org/repec/cpr/ceprdp/DP15857.pdf>)
- Lead 23: [City Research Online](<https://openaccess.city.ac.uk/id/eprint/31278/>)
- Lead 24: [Alpha Architect](<https://alphaarchitect.com/short-term-momentum/>)
- Lead 25: [Erasmus repository](<https://repub.eur.nl/pub/40707>)
- Lead 26: [Robeco summary](<https://www.robeco.com/en-int/insights/2011/11/short-term-residual-reversal>)
- Lead 27: [CXO Advisory](<https://www.cxoadvisory.com/technical-trading/purified-short-term-stock-reversal/>)
- Lead 28: [Kellogg research page](<https://www.kellogg.northwestern.edu/academics-research/research/detail/2008/short-run-reversal-in-the-market-for-large-stocks/?p=1>)
- Lead 29: [LSE PDF](<https://personal.lse.ac.uk/polk/research/TugOfWar.pdf>)
- Lead 30: [LSE Research Online](<https://researchonline.lse.ac.uk/id/eprint/87481>)
- Lead 31: [LGT](<https://www.lgt.com/at-en/insights/investment-strategies/how-much-truth-is-there-in-sayings-about-stock-markets--85452>)
- Lead 32: [University of Nottingham Ningbo record](<https://research.nottingham.edu.cn/en/publications/the-halloween-indicator-sell-in-may-and-go-away-everywhere-and-al/fingerprints/>)
- Lead 33: [IDEAS](<https://ideas.repec.org/a/gam/jijfss/v6y2018i2p42-d140703.html>)
- Lead 34: [Purdue CIBER working paper](<https://docs.lib.purdue.edu/ciberwp/43>)
- Lead 35: [Fed in Print](<https://fedinprint.org/item/fedawp/13394/original>)
- Lead 36: [AEA 2022 preliminary paper](<https://aeaweb.org/conference/2022/preliminary/paper/iQikdBKZ>)
- Lead 37: [ETF Trends](<https://www.etftrends.com/etf-strategist-channel/turn-month-effect/>)
- Lead 38: [SEC 424B3](<https://www.sec.gov/Archives/edgar/data/19617/000121390025039323/ea0240777-01_424b3.htm>)
- Lead 39: [Fronteras Desk (ASU)](<https://fronterasdesk.org/node/429504>)
- Lead 40: [Boston Fed WP 98-6](<https://www.bostonfed.org/-/media/Documents/Workingpapers/PDF/wp98_6.pdf>)
- Lead 41: [Emerald, JFEP](<https://www.emerald.com/insight/content/doi/10.1108/JFEP-04-2019-0066/full/html>)
- Lead 42: [Eunomia](<https://ojs.akademiarac.edu.pl/index.php/eunomia/en/article/view/268>)
- Lead 43: [Mecklenburg County elections](<https://vote.mecknc.gov/upcoming-elections>)
- Lead 44: [Washington Examiner](<https://www.washingtonexaminer.com/news/4462055/dates-to-know-2026-midterm-elections/>)
- Lead 45: [Schaeffer's Research](<https://www.schaeffersresearch.com/content/analysis/2018/10/31/what-midterm-elections-could-mean-for-stocks>)
- Lead 46: [WealthManagement.com](<https://www.wealthmanagement.com/equities/wall-street-hopes-history-repeats-with-a-post-election-comeback>)
- Lead 47: [Esquire Bank](<https://signature.esquirebank.com/wealth-management/midterm-year-seasonality-swings-favorable-for-stocks/>)
- Lead 48: [Zacks](<https://www.zacks.com/stock/news/2014377/>)
- Lead 49: [Capital Group](<https://www.capitalgroup.com/apac/capitalideas/en/articles/how-us-midterm-elections-affect-the-markets.html>)
- Lead 50: [InvestingLive](<https://investinglive.com/stock-market-update/s-p-500-defies-midterm-slump-as-bank-of-america-says-history-favours-post-election-gains/>)
- Lead 51: [Motley Fool research](<https://www.fool.com/research/midterm-election-year-stock-market-history/>)
- Lead 52: [CXO Advisory](<https://www.cxoadvisory.com/?p=1377>)
- Lead 53: [IDEAS citation record](<https://ideas.repec.org/r/pal/assmgt/v12y2011i2d10.1057_jam.2011.2.html>)
- Lead 54: [Liberty Street Economics](<https://libertystreeteconomics.newyorkfed.org/tag/paul-whelan/>)
- Lead 55: [Alpha Architect](<https://alphaarchitect.com/2015/02/overnight-momentum-vs-intraday-momentum/>)
- Lead 56: [Federal Reserve FOMC calendar](<https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm>)
- Lead 57: [PrimeXBT, citing Fed timing](<https://primexbt.com/for-traders/alphabet-earnings-date/>)
- Lead 58: [EconPapers SR 512](<https://econpapers.repec.org/RePEc:fip:fednsr:512>)
- Lead 59: [NY Fed staff report PDF](<https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.pdf>)
- Lead 60: [Kurov, Wolfe & Gilbert working paper](<https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf>)
- Lead 61: [Liberty Street Economics 2018](<https://libertystreeteconomics.newyorkfed.org/2018/11/the-pre-fomc-announcement-drift-more-recent-evidence.html>)
- Lead 62: [IDEAS/RePEc](<https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html>)
- Lead 63: [Quantpedia](<https://vvv.quantpedia.com/tag/volatility-premium/page/2/>)
- Lead 64: [BLS Oct 2026 schedule](<https://www.bls.gov/schedule/2026/10_sched_list.htm>)
- Lead 65: [BLS Nov 2026 schedule](<https://www.bls.gov/schedule/2026/11_sched_list.htm>)
- Lead 66: [BLS Dec 2026 schedule](<https://www.bls.gov/schedule/2026/12_sched_list.htm>)
- Lead 67: [BEA release schedule](<https://www.bea.gov/index.php/news/schedule/full>)
- Lead 68: [BEA blog Jan 7, 2026](<https://bea.gov/news/blog/2026-01-07/economic-release-schedule-updates-gdp-personal-income-and-outlays>)
- Lead 69: [SK hynix newsroom](<https://news.skhynix.com/en/?p=13734>)
- Lead 70: [SEC 6-K](<https://www.sec.gov/Archives/edgar/data/0002120882/000119312526420934/d413172d6k.htm>)
- Lead 71: [TipRanks](<https://www.tipranks.com/stocks/skhy/earnings>)
- Lead 72: [Finviz headline "Microsoft Announces Quarterly Earnings Release Date"](<https://finviz.com/news/400058/microsoft-announces-quarterly-earnings-release-date>)
- Lead 73: [CM Elite Group](<https://www.cmelitegroup.com/knowledge-hub/microsoft-earnings-date-fiscal-q1-2027-report-time-estimates-and-expected-move/>)
- Lead 74: [days.to](<https://days.to/alphabet-earnings>)
- Lead 75: [Alphabet IR 2025](<https://abc.xyz/investor/news/news-details/2025/Alphabet-Announces-Date-of-Third-Quarter-2025-Financial-Results-Conference-Call-2025--ZwUcLWeND/default.aspx>)
- Lead 76: [Electrek](<https://electrek.co/2026/10/21/tesla-tsla-q3-2026-financial-results/>)
- Lead 77: [SEC DEF 14A](<https://www.sec.gov/Archives/edgar/data/0001318605/000110465926116700/tm267596-1_def14a.htm>)
- Lead 78: [Drive Tesla Canada](<https://driveteslacanada.ca/news/tesla-2026-annual-shareholder-meeting-december-3/>)
- Lead 79: [days.to](<https://days.to/nvidia-earnings>)
- Lead 80: [Manifold](<https://manifold.markets/Terminator2/what-will-nvidias-q3-fiscal-2027-re>)
- Lead 81: [NVIDIA IR](<https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Sets-Conference-Call-for-Second-Quarter-Financial-Results/default.aspx>)
- Lead 82: [NVIDIA IR 2025](<https://investor.nvidia.com/news/press-release-details/2025/NVIDIA-Sets-Conference-Call-for-Third-Quarter-Financial-Results/>)
- Lead 83: [SEC 8-K exhibit](<https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000073/q2fy27pr.htm>)
- Lead 84: [NVIDIA GTC DC](<https://www.nvidia.com/en-us/gtc/dc/>)
- Lead 85: [days.to AMD](<https://days.to/amd-earnings>)
- Lead 86: [Pluang](<https://pluang.com/en/news-feed/meta-umumkan-hasil-kuartal-tiga-2026>)
- Lead 87: [CFR PDF](<https://cfr.ivo-welch.info/published/papers/martineau2021rest.pdf>)
- Lead 88: [IDEAS](<https://ideas.repec.org/a/now/jnlcfr/104.00000122.html>)
- Lead 89: [UCLA Anderson Review](<https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/>)
- Lead 90: [Wharton working draft](<https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Draft20111215p_edited.pdf>)
- Lead 91: [Barber et al. PDF](<https://en-coller.tau.ac.il/sites/nihul_en.tau.ac.il/files/media_server/Recanati/management/seminars/account/barber.pdf>)
- Lead 92: [IIMB ARC 2020](<https://www.iimb.ac.in/ARC2020/Papers/The_Disappearing_Earnings_Announcement_Premium.pdf>)

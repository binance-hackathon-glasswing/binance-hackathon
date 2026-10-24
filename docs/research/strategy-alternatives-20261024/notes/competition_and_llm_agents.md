# Competition strategy and LLM agents — evidence with model limits

PR276-RV01, reviewed 2026-10-24 SGT. Neither higher variance nor any LLM overlay is adopted.

## Scoring is not a fully specified tournament model

Checked the [verbatim challenge page](../../../official/source_page.md), [trading guide](../../../official/kit/bstocks-trading-guide.md),
[kit reference](../../../skill/reference/participant-kit.md) and [SKILL](../../../skill/SKILL.md) F/K/Q entries,
including F-43/115/117/119/120 and Q-03/06/39. The page proposes percentage wallet-equity return and a drawdown
tie-break; F-115 later describes completed-trade PnL, drawdown, logs and repo together. Weights and open-position/BNB
valuation remain unresolved. It is unsafe to treat drawdown as irrelevant except for exact ties or to infer a
numeric minimum activity requirement. First-gas bootstrap is already settled by F-120, not a new open question.

Top-three awards among fewer than 25 teams and no live leaderboard do not reveal the rival return distribution,
our expected alpha, correlations, trading costs or the assessment function. “95% beats 80% for prize probability,”
“cash places us in the worst part of the field” and “tilt to the highest-volatility names” do not follow without
those inputs. Higher variance can increase or decrease the chance of crossing a rank threshold.

The checked [Gaba/Tsetlin/Winkler working paper](https://flora.insead.edu/fichiersti_wp/inseadwp2003/2003-27.pdf)
(primary full-text model/result sections, 2003 working-paper version) studies variability and correlations under specified contest models,
including symmetric performance distributions and choices without a cost of changing variability. Its conditional
comparative statics are not a theorem selecting financial leverage, exposure or weights for LARP. The original
Schwarz/Severinov concentration lead was inaccessible in this review; no claimed optimum is accepted from it.

The original note claimed a 200000-draw rival simulation without committed code, seed, calibrated inputs or receipts.
Its top-three probabilities are unreproduced and withdrawn from the reviewed note. No such simulation was run here.
The immutable original and source leads remain below for provenance, not as accepted experiment evidence.

## LLM evidence: checked paper versus leads

The [Lopez-Lira/Tang paper](https://arxiv.org/html/2304.07619v6) was checked in its primary full-text result sections (version 6).
Its daily-rebalanced, equal-weighted long-short headline strategy became unprofitable at 20 bp round-trip costs;
10 bp retained a positive result. These are
sample/strategy-specific findings, not a bound on every LLM strategy. Long-only and short-only size results differ:
the large-cap short leg's weakness does not establish that a negative-news exit filter works for this long-only book.
The paper's declining later-period performance does not by itself identify adoption as the cause or forecast 2026.

Live-agent competition press summaries, vendor demonstrations and benchmark papers in the original bibliography
were not independently replicated or fully verified here. Their universes, allowed shorts/leverage, execution,
benchmarks, costs, sample sizes, model cutoffs and look-ahead controls need checking. A reported count of profitable
sessions cannot estimate this field's return distribution, prove overtrading caused losses or establish that
LARP's invested basket will beat the median rival.

## Implications that survive review

Reliability, traceability, costs and a declared objective are prerequisites; they do not establish a profitable
strategy. An LLM signal must show incremental value beyond an equivalent deterministic baseline using authorized,
point-in-time inputs, complete request/response provenance and costs. A model's training cutoff, potential news
memorization and source availability can undermine a retrospective test. Evidence extraction, event detection,
negative-news exits and buy authority are different tasks and need separate criteria.

The adopted architecture's LLM role and verified adverse-evidence lifecycle remain in the existing plan and records.
This note does not expand trade authority, authorize a new service, waive label/rights requirements or adopt a
numerical exposure/turnover target. Yao/team own strategic adoption; Keith owns portfolio analysis; Keegan reviews
lifecycle/release bindings; Isaac approves exact signer/profile limits. Any new experiment needs criteria and pushed
code before running, and any final change needs the existing freeze and qualification process.

## Provenance and original source leads

The [original research text](https://github.com/binance-hackathon-glasswing/binance-hackathon/blob/5d5b5e284fd0e70586ba83767a2d22b0fd726d1e/docs/research/strategy-alternatives-20261024/notes/competition_and_llm_agents.md) is retained immutably.
PR276-RV01 replaces unsupported conclusions and repairs local references. The register preserves the original
external URLs for follow-up; inclusion does not verify availability, quality, rights or any claimed result. Only
sources explicitly assessed above have been rechecked; all other entries remain unverified leads.

- Lead 01: [INFORMS](<https://pubsonline.informs.org/doi/pdf/10.1287/opre.1030.0098>)
- Lead 02: [INSEAD listing](<https://www.insead.edu/faculty-research/publications/journal-articles/modifying-variability-and-correlations-winner-take>)
- Lead 03: [IDEAS/RePEc](<https://ideas.repec.org/a/kap/jrisku/v29y2004i2p143-158.html>)
- Lead 04: [IDEAS/RePEc](<https://ideas.repec.org/a/ucp/jlabec/v28y2010i4p893-922.html>)
- Lead 05: [NBER](<https://www.nber.org/papers/w15136>)
- Lead 06: [IDEAS/RePEc](<https://ideas.repec.org/a/inm/ormnsc/v53y2007i11p1745-1755.html>)
- Lead 07: [arXiv 2101.01816](<https://arxiv.org/pdf/2101.01816>)
- Lead 08: [IZA](<https://docs.iza.org/dp1345.pdf>)
- Lead 09: [Utrecht research portal](<https://research-portal.uu.nl/en/publications/rankings-and-risk-taking-in-the-finance-industry/>)
- Lead 10: [IDEAS/RePEc](<https://ideas.repec.org/a/bla/jfinan/v51y1996i1p85-110.html>)
- Lead 11: [NBER w5234](<https://nber.org/papers/w5234>)
- Lead 12: [JPE](<https://www.journals.uchicago.edu/doi/10.1086/516389>)
- Lead 13: [IDEAS/RePEc](<https://ideas.repec.org/a/cup/jfinqa/v36y2001i01p53-73_00.html>)
- Lead 14: [Cambridge](<https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/another-look-at-mutual-fund-tournaments/CD3356D7C7EDDC18D960CEF90CA7D84F>)
- Lead 15: [IDEAS/RePEc](<https://ideas.repec.org/a/eee/jeborg/v50y2003i3p373-383.html>)
- Lead 16: [Maastricht CRIS](<https://cris.maastrichtuniversity.nl/en/publications/tournaments-in-the-uk-mutual-fund-industry/>)
- Lead 17: [Emerald](<https://www.emerald.com/insight/content/doi/10.1108/03074350810900514/full/html>)
- Lead 18: [CFR Cologne PDF](<https://www.cfr-cologne.de/download/kolloquium/2012/Chen_etal.pdf>)
- Lead 19: [iWeaver recap](<https://www.iweaver.ai/blog/alpha-arena-ai-trading-season-1-results/>)
- Lead 20: [SCMP](<https://www.scmp.com/tech/tech-trends/article/3331425/alibabas-ai-model-outperforms-us-rivals-crypto-trading-showdown>)
- Lead 21: [Forklog](<https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/>)
- Lead 22: [Aurpay](<https://aurpay.net/aurspace/ai-trading-battle-chinese-models-crush-western-ai/>)
- Lead 23: [iWeaver](<https://www.iweaver.ai/blog/alpha-arena-ai-trader-showdown/>)
- Lead 24: [GNcrypto](<https://www.gncrypto.news/news/mystery-model-alpha-arena-season-1-5-winner/>)
- Lead 25: [One Day Advisor](<https://www.onedayadvisor.com/2025/12/nof1ai-alpha-arena-review-season-15.html>)
- Lead 26: [Yahoo Finance](<https://finance.yahoo.com/news/elon-musks-grok-4-20-123855766.html>)
- Lead 27: [BigGo Finance](<https://finance.biggo.com/news/5BSX_Z0BaoGGrU-ID27J>)
- Lead 28: [TradeRank](<https://www.traderank.ai/blog/alpha-arena-alternatives-2026>)
- Lead 29: [arXiv HTML](<https://arxiv.org/html/2510.02209v1>)
- Lead 30: [arXiv HTML](<https://arxiv.org/html/2511.03628v1>)
- Lead 31: [arXiv](<https://arxiv.org/abs/2510.11695>)
- Lead 32: [AI Street](<https://aistreet.beehiiv.com/p/benchmarking-ai-agents-in-live-markets>)
- Lead 33: [arXiv HTML](<https://arxiv.org/html/2505.07078v5>)
- Lead 34: [arXiv 2412.18174](<https://arxiv.org/abs/2412.18174v1>)
- Lead 35: [FinRL contests paper](<https://arxiv.org/html/2504.02281v3>)
- Lead 36: [Task 1 docs](<https://finrl-contest.readthedocs.io/en/latest/finrl2025/task1.html>)
- Lead 37: [arXiv HTML](<https://arxiv.org/html/2304.07619v6>)
- Lead 38: [Univ. of Sydney seminar abstract](<https://business.sydney.edu.au/events/research/2024/finance/dacheng-xiu>)
- Lead 39: [Tsinghua PBCSF notice](<https://www.pbcsf.tsinghua.edu.cn/info/1504/7668.htm>)
- Lead 40: [arXiv 2412.19245](<https://arxiv.org/html/2412.19245v1>)
- Lead 41: [arXiv 2309.17322](<https://arxiv.org/abs/2309.17322>)
- Lead 42: [arXiv HTML](<https://arxiv.org/html/2512.23847v1>)
- Lead 43: [arXiv](<https://arxiv.org/abs/2310.17721v2>)
- Lead 44: [Harvard Law School Forum](<https://corpgov.law.harvard.edu/2023/11/01/from-transcripts-to-insights-uncovering-corporate-risks-using-generative-ai/>)
- Lead 45: [arXiv](<https://arxiv.org/pdf/2502.07393>)
- Lead 46: [Cambridge Open Engage](<https://www.cambridge.org/engage/coe/article-details/6a071d88d1922e37d57d1470>)

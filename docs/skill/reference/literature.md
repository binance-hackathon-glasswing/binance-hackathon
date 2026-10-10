# Binance Agentic AI Challenge — Literature (L)

> Research evidence with citations and grades (§12 of the v0.3 skill file, in full). Justifies P/G items; tournament papers (§12.5) are used only in larp/strategy-opinions.md.
> IDs are stable; see `SKILL.md` for the reading contract and label meanings.
> Split out of SKILL.md v0.3 on 2026-09-30 (v0.4 restructure); item wording unchanged except the v0.4 fixes listed in SKILL.md Appendix B.

## 12. LITERATURE (L)

Grades as in §0.1. [PRIMARY] here means the paper itself was checked at abstract/HTML level (2026-09-27/29) unless noted.

### 12.1 LLM trading agents (architectures; backtest-only evidence)
- L-01 FinMem (Yu et al., 2023, arXiv:2311.13743) — layered memory. Backtest only. [PRIMARY, existence]
- L-02 FinAgent (Zhang et al., KDD 2024, arXiv:2402.18485) — multimodal, dual-level reflection. Backtest only. [PRIMARY, existence]
- L-03 FinCon (Yu et al., NeurIPS 2024, arXiv:2407.06567) — manager–analyst hierarchy, self-critique as risk control. Backtest only. [PRIMARY, existence]
- L-04 TradingAgents (Xiao et al., 2024, arXiv:2412.20138) — Sharpe 8.21 (AAPL), 6.39 (GOOGL), 5.60 (AMZN) over Jan 1–Mar 29, 2024; the authors note the high Sharpe came from a period with few pullbacks; costs not mentioned. [PRIMARY]
- L-05 Trading-R1 (arXiv:2509.11420) — SFT + RL curriculum; backtest only. [PRIMARY, abstract]
- L-06 Survey (Xia et al., 2026, arXiv:2605.19337) — of a 19-study primary empirical subset, only 2 report extractable time-consistent split protocols and 1 an explicit transaction-cost model; none reaches the top reproducibility tier. [PRIMARY]
- L-07 Li et al. (EMNLP 2023 Industry, arXiv:2305.05862) — GPT-4 "can outperform" domain-pretrained and fine-tuned models "on many tasks"; fine-tuned models still lead on structured prediction. [PRIMARY]
- So what: borrow structure (roles, memory, reflection); do not cite their returns.

### 12.2 Live / forward evaluations
- L-10 nof1 Alpha Arena Season 1 (Oct 18 – Nov 3, 2025; $10k each; crypto perps): final balances $12,231 / $10,489 / $5,799 / $5,445 / $4,208 / $4,126 (Qwen3-Max, DeepSeek-V3.1, Claude Sonnet 4.5, Gemini 2.5 Pro, Grok 4, GPT-5). [SECONDARY: ForkLog; nof1.ai blocked] Behavioural details [UNCONFIRMED].
- L-11 Alpha Arena Season 1.5 (~Nov 19 – Dec 3, 2025; US stock tokens on Hyperliquid; reported tickers incl. TSLA, NVDA, MSFT, AMZN, Nasdaq-100): Grok 4.20 "up 12% on avg" across four modes. [SECONDARY]
- L-12 LiveTradeBench (arXiv:2511.03628) — 21 LLMs, 50 days live; "high LMArena scores do not imply superior trading outcomes"; performance on one market "does not generalize to another". [PRIMARY]
- L-13 Agent Market Arena (arXiv:2510.11695) — "model backbones contribute less to outcome variation" than agent frameworks. [PRIMARY]
- L-14 StockBench (arXiv:2510.02209) — "most models struggle to outperform the simple buy-and-hold baseline"; "all LLM agents underperform the passive baseline during the downturn"; thinking models make fewer arithmetic but more schema errors. [PRIMARY]
- L-15 DeepFund (arXiv:2505.11065) — DeepSeek-V3 and Claude-3.7-Sonnet "incur net trading losses". [PRIMARY]
- L-16 AI-Trader (arXiv:2512.10971) — "risk control capability determines cross-market robustness". KTD-Fin (arXiv:2605.28359, CSI300) — returns "largely explained by passive market and style exposure". [PRIMARY]
- L-17 FinSearchComp (Hu et al., arXiv:2509.13160) — search/finance tools "substantially" improve time-sensitive retrieval. [PRIMARY]
- So what: base rate is losing money or matching beta; harness matters more than backbone; deterministic quantities/schemas are mandatory. These support design choices; they are not claims about LARP's results.

### 12.3 Look-ahead bias and leakage
- L-20 Profit Mirage (arXiv:2510.07920) — backtest gains fade after the model's knowledge window. [PRIMARY]
- L-21 Glasserman & Lin (arXiv:2309.17322) — anonymised headlines outperform; "distraction effect". [PRIMARY]
- L-22 Lopez-Lira & Tang (arXiv:2304.07619) — headline predictability "especially for small stocks and negative news"; "strategy returns decline as LLM adoption rises". [PRIMARY]
- L-23 Lopez-Lira, Tang & Zhu (arXiv:2504.14765) — LLMs memorise past market values. [PRIMARY]
- L-24 Gao, Jiang & Yan, "Detecting Lookahead Bias in LLM Forecasts" (arXiv:2512.23847); Benhenda, Look-Ahead-Bench (arXiv:2601.13770). [PRIMARY]

### 12.4 Short-horizon predictability and costs
- L-30 Tetlock (2007, J. Finance) — media pessimism → temporary pressure then reversal. [PRIMARY, standard]
- L-31 Chan (2003, JFE) — drift after news, reversal after no-news moves, mainly small stocks; Chen, Kelly & Xiu (SSRN 4416687) — LLM news embeddings predict returns across markets. [PRIMARY, not re-checked]
- L-32 Martineau (CFR 2022) — PEAD largely gone in large caps; Barber et al. (2013, JFE) — earnings-announcement premium; Lou, Polk & Skouras (2019, JFE) — overnight vs intraday returns differ. [PRIMARY, not re-checked]
- L-34 Novy-Marx & Velikov (2016, RFS) — high-turnover strategies rarely survive costs; a buy/hold spread is an effective mitigation. [PRIMARY, not re-checked]

### 12.5 Tournament incentives (used only in Appendix A)
- L-40 Brown, Harlow & Starks (1996) — mid-year losers raise risk; Busse (2001) — effect weakens with daily data. [PRIMARY, standard]
- L-41 Gaba, Tsetlin & Winkler (INSEAD WP 2003/27) — with proportion of winners p < 0.5, choose riskier distributions and lower correlation; at p = 0.1 and zero correlation, doubling σ raises P(win) about 2.7×. [PRIMARY]
- L-42 Seel & Strack (2013, JET) — winner-take-all contestants gamble. [PRIMARY, standard]
- L-43 Fang et al., "Winning ways" (SSRN 4856341) — convex prizes favour positive skew; equilibrium bounded. [PRIMARY, existence only]

### 12.6 Risk management
- L-31b Harvey et al. (2018, JPM) — volatility targeting improves equity Sharpe and trims tails; gains fragile out of sample (Cederburg et al., 2020). [PRIMARY, not re-checked]
- L-33 Kaminski & Lo (2014) — stop-losses add value only under momentum/regime-switching; Lo & Remorov (2017) — tight stops lose to costs. [PRIMARY, not re-checked]
- L-35 Grossman & Zhou (1993) — drawdown-constrained exposure ∝ equity − floor. [PRIMARY, standard]
- L-36 MacLean, Thorp & Ziemba (2010) — fractional Kelly and estimation error. [PRIMARY, standard] Not adopted (P-07).
- L-37 Busseti, Ryu & Boyd (2016), "Risk-Constrained Kelly Gambling" (https://web.stanford.edu/~boyd/papers/pdf/kelly.pdf) — maximise E log wealth subject to a convex sufficient condition for Prob(W_min < α) < β: E (rᵀb)^(−λ) ≤ 1 with λ = log β / log α; beats fractional Kelly at equal drawdown risk in the paper's examples. Assumes iid returns, a known distribution and an infinite horizon. [PRIMARY, read 2026-10-06] Assessed in IDEA-006 (recommended for C1 sizing with a finite-horizon constraint; not decided).

### 12.7 Agent reliability
- L-50 Huang et al. (ICLR 2024, arXiv:2310.01798) — no reliable self-correction without external feedback. [PRIMARY]
- L-51 Self-consistency (Wang et al., ICLR 2023). [PRIMARY, standard]
- L-52 MAST (arXiv:2503.13657) — 14 multi-agent failure modes; τ-bench (arXiv:2406.12045) — pass^8 < 25% in retail. [PRIMARY]
- L-53 Chen et al. (Anthropic, arXiv:2505.05410) — reasoning models reveal hint use often below 20% of the time. [PRIMARY]
- L-54 LoRA; DPO. No live evidence found that fine-tuned/RL traders beat a well-harnessed frontier model. [PRIMARY, standard]

### 12.9 Independent uncertain-event review (2026-10-10, IDEA-030)

This qualifies L-60–65/§12.8 added on the evidence owner branch at `544df90`; those historical entries are not yet in this main-branch version. [IDEA-030 R09](../../ledger/IDEA-030.md) retains the primary links, reading depth and ten source IDs L030-01–10.

- L-60 supports studying filing changes, but slow long-short returns do not validate a five-session lexical novelty flag or long-only exit policy.
- L-61 supports risk-perception/volatility associations. The prior blanket boilerplate discount is too broad, including the author abstract's firm-versus-industry comparison.
- L-62 concerns informativeness, not an executable trading rule. L-63's primary abstract and manuscript introduction/conclusion support rising boilerplate/stickiness, not that most of this implementation's hypothetical statements are boilerplate.
- L-64 remains secondary. Pre-impairment underperformance does not show that a hypothetical disclosure caused or forecast the return.
- L-65 is upgraded to publisher abstract checked; forecast explanation/price-response associations do not establish universal immediate reactions or returns available after assessment.
- L030-06 separates initial headline reaction from subsequent returns; size, short exposure and costs limit transfer. L030-07 motivates staleness controls; L030-08 examines specialised takeover rumors; L030-09 cautions against assuming large-cap earnings drift; L030-10 motivates leakage diagnostics.

Retain attributed uncertain information, but test semantic correctness, novelty, usable latency and complete after-cost portfolio value separately. Neither volatility prediction nor sentiment establishes a return advantage. H-04 remains NOT RUN; its endpoint, horizon, comparison design and inconclusive fallback require preregistration. The main-branch publication carries the review corrections without merging the owner implementations.
### 12.8 Disclosure text and statements about possible events (added 2026-10-10, IDEA-025 §9.5)
Checked 2026-10-10. The grade says what was read.
- L-60 Cohen, Malloy & Nguyen, "Lazy Prices" (J. Finance 75(3), 2020; NBER w25084) — changes in the language of 10-K/10-Q filings (1995–2014) predict future earnings, profitability, news and bankruptcies; a short-changers/long-non-changers portfolio earns up to 188 bp a month; changes about the executive team, litigation and risk factors are especially informative; **no announcement effect** — returns accrue only when the information is later revealed. [PRIMARY, abstract]
- L-61 Kravet & Muslu, "Textual risk disclosures and investors' risk perceptions" (Rev. Accounting Studies 18(4), 2013, 1088–1122) — annual increases in 10-K risk disclosure go with higher return volatility and trading volume around and after the filing and more dispersed analyst revisions: risk text "increase[s] investors' risk perceptions"; effects are weaker for disclosures that look boilerplate. [PRIMARY, abstract]
- L-62 Campbell, Chen, Dhaliwal, Lu & Steele, "The information content of mandatory risk factor disclosures in corporate filings" (Rev. Accounting Studies 19(1), 2014, 396–455) — firms facing more risk disclose more; the disclosures are reflected in systematic risk, idiosyncratic risk, information asymmetry and firm value. [PRIMARY, abstract]
- L-63 Dyer, Lang & Stice-Lawrence, "The evolution of 10-K textual disclosure" (J. Accounting & Economics 64(2–3), 2017, 221–245) — 1996–2013: 10-Ks grow longer, more boilerplate and stickier; risk factors are one of three topics behind nearly all of the growth. [SECONDARY: abstract as summarised by search results; paper not opened]
- L-64 FEI / Duff & Phelps goodwill impairment study (reported by FM Magazine, 2012-10-09) — 1,259 US impairment events 2005–2009; the companies trailed the S&P 500 by 4.9% in the 7–12 months before the impairment versus 1.2% in the 6 months after: the market prices impairments before they are recorded. Other studies find announcement reactions, so the evidence is mixed. [SECONDARY: practitioner study via trade press, not peer reviewed]
- L-65 Baginski, Hassell & Kimbrough (J. Accounting Research, 2004) — management forecasts move prices at once; explained bad-news forecasts move them more. [UNCONFIRMED: search-result summary only]
- So what: statements about possible events carry information before the event (L-61, L-62, L-64), but mostly when they are **new**; repeated boilerplate carries little (L-60, L-61, L-63). Timing differs by source: changed filing text pays off over months (L-60), forecasts at once (L-65). All samples are broad US equities; nothing here measures our five names or a 5-session horizon (H-04).

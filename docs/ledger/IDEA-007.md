# IDEA-007 — Training data when real data is short: web catalysts vs synthetic data; three recommended tracks

- Date / author: 2026-10-08 / SYZ (requested); 5 research subagents, 3 red-team subagents, load-bearing terms re-fetched by Claude; merged by Claude
- Status: open — **⚠ RECOMMENDED — NOT DECIDED.** Feeds GAP-56 and the Oct 10 declarations (F-12).
- What: SYZ proposed (1) read the stock charts and collect every catalyst from the web, or (2) have Claude construct synthetic training data that closely matches the real data. This entry tests both, plus 7 alternatives, and recommends three tracks.
- Why it might help: kit data gives ≈ 16 months (Ondo) / 3–4 months (bStocks) of token prices only (IDEA-001 §10–12), too little to train or validate a return model.
- Cost / risk: Track A ≈ 5–6 person-days (pd), Track B ≈ 4–5 pd, Track C ≈ 1–2 pd plus logging already planned. Main risks: data and model terms (§1), hindsight in labels, time before the Oct 18 model freeze.
- Links: GAP-56, GAP-21, GAP-22, GAP-23, GAP-44, D-03, D-09, D-10, I-37, I-67, F-30, F-31, F-32, F-49, F-61, F-63, F-71, F-114, F-115, IDEA-001, IDEA-004, IDEA-006

## 0. Answer in one paragraph
No collection or synthesis method adds information about future returns that the real data does not hold. Charts and web catalysts give ≈ 400–600 events for the five names over 2018–2026, and their minimum detectable 5-session effect (≈ 0.75–1.0%) is about the size of the ≈ 100 bp round trip. Synthetic prices fitted to a single bull path reproduce that path and add nothing. Synthetic catalyst→outcome pairs written by an LLM carry its memory of what happened (look-ahead). So neither idea can train the proposal's P(UP/FLAT/DOWN) model. **Recommendation:** re-target the model layer to labels that can be checked without returns: event type, severity and veto from real, rights-clear text. Use synthetic data only to stress-test the risk layer and the pipeline. Treat forward data from Oct 12 as the only clean evaluation set. This agrees with IDEA-004 (C1 base book + veto/exit overlay).

## 1. Rights findings that change current plans (re-fetched 2026-10-08)
| Source | Finding (quoted) | Effect |
|---|---|---|
| Anthropic Usage Policy (effective 2025-09-15, anthropic.com/legal/aup) | prohibits "Utilization of inputs and outputs to train an AI model (e.g., "model scraping" or "model distillation")" "without prior authorization from Anthropic" | **Claude must not generate or label any data used to train a model** (C1 teacher, C2 synthetic text, C4 trajectories, SYZ's idea 2 as stated). Claude stays fine for runtime inference, writing code, and evaluation-only sets. Applies to every Claude surface, not only consumer plans |
| FRED terms (fred.stlouisfed.org/legal, no date shown) | prohibits use "in connection with the development or training of any software program or system or machine learning ... or any other program or process commonly known as artificial intelligence"; same in API item (k) | Plans name FRED `DEXKOUS` (plan.md D-10 (b)) and `VIXCLS` (IDEA-004 §3). Don't take these from FRED; get KRW/USD from the Fed H.10 release directly (check its terms) and drop VIXCLS or find a licensed source |
| Binance Vision Dataset Terms v1.0 (last updated 2026-08-26) | CC BY-NC-SA 4.0; covers data.binance.vision "and associated endpoints"; §4.1 permits only non-commercial uses incl. "algorithmic historical backtesting for purely personal non-production research"; §4.2 "You shall not use the Datasets for live proprietary trading execution, automated commercial order generation" | Don't use data.binance.vision files to fit or tune anything that trades. Whether api.binance.com klines (the kit-named `binance` skill) fall under "associated endpoints" is unclear → ask the organisers (they are Binance) |
| Chart and price websites (red team + research, fetched) | Google Finance: not to "copy ... store ... reprocess"; TradingView: "display-only", no "algorithmic decision-making"; Nasdaq.com: no extraction for ML "including ... any automated or manual process"; Yahoo, Macrotrends, Investing.com similar | Idea 1's "read the graph" fails F-71 even by hand |
| Price vendors | Twelve Data free tier: no "Free Tier data for commercial purposes", no storage beyond documented timeframes, no credential sharing; Tiingo, Massive, FMP, Alpha Vantage, Alpaca, WRDS, Cboe: personal/academic only; Pyth/Douro Labs: no ML training. Databento: own T&C not readable (JS-only); its blog's "no licence needed for historical (T+1)" is about exchange licensing only | Only Databento (written OK needed) remains for licensed share prices; see Track C |
| Clear sources | EDGAR ("public information ... may be copied or further distributed"); GDELT fields ("unlimited and unrestricted use ... commercial", cite; no article text); Wikimedia pageviews (CC0); BLS calendars (public domain) | Usable for Track A |

Not re-verified by Claude (from subagents, treat as leads): ChronoBERT (MIT, vintages to 2024-12-31, ~0.1B); DeepSeek-V3.1 (MIT) and Qwen3 (Apache-2.0) as possible open teachers, and the terms of any host serving them; Chronos-Bolt and TimesFM-2.5 (Apache-2.0); Kronos (MIT, data provenance undisclosed); OpenDART terms silent on training.

## 2. Candidates and verdicts
Scores from the red teams, 1–5: value to score / value to F-30 and audit / compliance / leakage safety / feasibility by Oct 18 / evidence.

| ID | Candidate | Verdict | Scores | Main reason |
|---|---|---|---|---|
| X1 | Idea 1 literal: chart-read prices + web catalysts → return labels | **Reject** | 1/2/1/1/3/1 | Chart sites forbid it (§1); web explainers are written after the move (label leaks into text); sampling from big moves selects on the outcome; n too small |
| X2 | Idea 2 literal: Claude writes price series and catalyst→outcome pairs | **Reject** | 1/1/2/1/3/1 | No new information (Cetingoz & Lehalle 2025); Claude remembers 2025–26 prices (Lopez-Lira, Tang & Zhu 2025) → F-63 risk; AUP bans training on Claude outputs; F-49 hands the prompts to auditors |
| C1 | Rights-clear catalyst corpus + teacher→student distillation | **Adopt modified → Track A** | 1/4/4*/3–4/3/3 | *Only with a non-Claude teacher or no teacher |
| C2 | Counterfactual synthetic catalysts (fictional firms) | Fold into A | 1/3/4*/3/3/2 | Entity neutering fails on event structure (an "export licence for data-centre GPUs" is still NVDA); keep as verifier test cases and an optional ablation |
| C3 | Synthetic market scenarios for the risk layer | **Adopt modified → Track B** | 2/3/4/4/4/3 | As a parameter optimiser it is ceremony; as a stress and harness test it is standard practice |
| C4 | Synthetic agent trajectories to fine-tune a small model | Fold into A as an eval suite | 2/4/3/4/2–3/3 | No evidence a 2-week 1.5–4B model beats a hosted frontier model; serving risk under F-114 |
| C5 | Licensed independent share prices (Databento) | Gated part of Track C | 3/2/2→4/4/3/3 | Gives real 2020 and 2022 stress, the token-vs-share check (GAP-22) — only after a written OK |
| C6 | Zero-shot time-series foundation model as a vol feature | **Reject** (optional shelf test) | 1/1/4/5/4/2 | Better vol forecasts move the score by basis points; F-31 |
| C7 | Forward data from Oct 12 (quotes, fills, openState, shadow agent) | **Adopt → Track C** | 4/3/5/5/5/4 | The only data after every model's cutoff; calibrates costs, premium, latency, veto counts |

## 3. Recommended tracks (top 3)

### Track A — Real-text event and veto classifier, labels without returns (replaces the return-labelled encoder)
- **Data:** EDGAR 8-Ks with `acceptanceDateTime` and Ex. 99.1 text, 2022–2026, for the 4 US eligible names + ~50 large US filers (labels describe text, so the universe can be wide). Events defined mechanically, never from price moves. SK Hynix (Korean DART) stays out of the text task; GDELT fields stay runtime features. Corpus stays outside the repo; commit a manifest (accession numbers + sha256) (F-61).
- **Labels, in order of preference:**
  1. 8-K item codes as free event-type labels (filer-assigned, no LLM).
  2. Rule-based labelling functions (Snorkel style): impairment amount, guidance raised/cut phrases, regulator named, executive departure, restatement (4.02).
  3. Gold set: ~400 items labelled by the team, stratified by item code (adverse classes over-sampled), blind to date and price, 100 double-labelled.
  4. Optional teacher for the remainder: **an open-weight model whose licence and host terms allow training on its outputs** (to verify). Never Claude (§1).
- **Model:** ModernBERT-large head (or ChronoBERT) → severity (1–3) and veto yes/no; a declared deterministic rule layer decides; the zero-shot hosted LLM + item-code rules is the fallback. This is the F-30 "domain fine-tuning / distillation" claim.
- **Eval:** real held-out items only; post-cutoff events (Jul–Oct 2026 8-Ks) + Track C shadow vetoes. Claude may write adversarial test cases for the claim verifier (planted unsupported claims, stale timestamps, number mismatches) because they are never trained on.
- **Kill criteria (pre-register by Oct 12):** no documented teacher rights by Oct 13 → no teacher (gold + rules only); gold κ < 0.6 on veto → drop the veto label, item-code rules only; student veto F1 > 0.05 below the zero-shot LLM, or higher false-veto rate, on post-cutoff items → ship zero-shot + rules; hindsight probe fails (Spearman ρ between teacher-minus-gold severity and |5-session return| > 0.10, p < 0.05) → relabel on masked text or drop severity; not trained and evaluated by Oct 17 → freeze without the student.
- **Effort:** MVP ≈ 5–6 pd (EDGAR pull 2–3, taxonomy 0.5, gold set 2–3, train + eval 1.5–2). Run EDGAR locally (cloud IPs are blocked; declared User-Agent).
- **Score value ≈ 0** (overlay ≈ 0.09% of equity, IDEA-004 §1); its value is the model-layer claim, determinism, and no API dependency during the run.

### Track B — Scenario lab: generator code + declared stress grid + planted-signal test
- **Generators (Claude may write the code; the data comes from code + declared parameters + seed):** demeaned and raw block bootstrap of joint hourly kit returns (bStock candles, Ondo; not data.binance.vision), plus a cited stress grid: single-name gaps −8/−15/−25% (anchor to documented days, e.g. NVDA 2025-01-27), market shock with correlation → 0.9, vol ×2/×3 for 3–5 days, weekend gaps, token de-peg vs reference; optional GJR-GARCH-t / t-copula with assumed parameters.
- **Uses:** report P(MDD > x), whipsaw count, cost drag and worst single-name loss for C1 with literature-default parameters (EWMA ~20-day half-life, Harvey et al. 2018); replay the full quote → decide → order → `log()` chain as harness fixtures; **planted-signal test** — inject a known 10/20 bp-per-day edge and pure noise, run the training/evaluation pipeline, and measure power and false positives with the data length we have.
- **Not for:** choosing exposure (that is an objective decision: a 4% E[MDD] cap means w ≈ 0.46 at 35% vol, costing ≈ 2.5 pp of rank in a +5% market; drawdown tie-break almost never binds), or fitting return means. Run PBO/CSCV on real data only.
- **Kill criteria:** rule rankings flip between raw and demeaned bootstraps or between bootstrap and GARCH paths → use defaults, report only; a tuned setting beats the default by < 0.5 pp expected 10-session return or < 1 pp p95 MDD → default; planted 20 bp/day edge not recovered at ≥ 80% power → no fitted alpha component ships (the pre-registered default runs, as the proposal promised).
- **Effort:** ≈ 3–4 pd + 1 pd for the planted-signal test.

### Track C — Real forward data from Oct 12, plus gated licensed share prices
- **Forward capture (extends T10, GAP-44):** quote logger, `openState` logger, `rwa/*` snapshots, a shadow run of the exact final configuration (pinned LLM snapshot, no signing) logging veto decisions, and ≥ 10 real minimum-size round trips on the dev wallet (realised fills, not quotes). Cover late-October Q3 earnings windows (check dates) and the Oct 24–25 weekend.
- **Calibrates:** cost model, fill/revert rates, token premium vs `referencePrice`, trading hours (Q-32), latency, veto false-positive counts. **Cannot** validate alpha (≈ 4,900 stock-days needed for 10 bp/day).
- **Gated add-on (C5):** email Databento today for a written OK (team of 4, prize contest, offline model building and risk calibration). If OK by Oct 16: XNAS `ohlcv-1d` 2018-05 → for NVDA, GOOGL, TSLA, MSFT, SPY, QQQ, SMH (+ SKHY ADR since 2026-07-10); check cost first; apply splits from EDGAR; check closes vs the consolidated summary. Feeds real 2020/2022 stress into Track B and the token-vs-share check (GAP-22). Offline only; never in runtime model inputs.
- **Pass criteria:** ≥ 5 days continuous logging incl. a weekend; ≥ 10 real round trips; cost-model error ≤ 25 bp; zero unmapped log items; false vetoes > half of all vetoes → veto ships disabled.

## 4. Decisions needed (by Oct 10)
1. Adopt Tracks A–C or not; accept re-targeting the decision model from P(UP/FLAT/DOWN) to severity/veto (changes the declared model stack, F-12; proposal wording "fine-tune on our own point-in-time labels" still holds).
2. Teacher for Track A: none (gold + rules), or a named open-weight model after its licence and host terms are read. Record that Claude is not a teacher (AUP).
3. Remove FRED from the plan (D-10 (b) `DEXKOUS`, IDEA-004 `VIXCLS`) and from the proposal's FRED/ALFRED line; choose replacements.
4. Ask the organisers: does the kit-named `binance` skill (api.binance.com, data.binance.vision) permit use by a live trading agent and for model building, given Vision §4.2? Same question for the Ondo `bapi` candles.
5. Send the Databento question (or drop C5).

## 5. Key sources (fetched 2026-10-08 unless noted)
- Rights: anthropic.com/legal/aup; anthropic.com/legal/commercial-terms; fred.stlouisfed.org/legal; data.binance.vision/Binance_Vision-Terms_of_Use.pdf; sec.gov/about/privacy-information; gdeltproject.org/about.html; google.com/intl/en/googlefinance/disclaimer; tradingview.com/policies; nasdaq.com/legal; twelvedata.com/terms; databento.com/blog/introduction-market-data-licensing
- Synthetic data: Cetingoz & Lehalle 2025 (arXiv 2501.03993); Wiese et al. 2020 Quant GANs (1907.06673); Bühler et al. 2020 (2006.14498); Rahimikia, Ni & Wang 2025 (2511.18578); Bailey et al. 2015 PBO (SSRN 2326253); Magdon-Ismail et al. 2004 (E[MDD]); Harvey et al. 2018 vol targeting; Cederburg et al. 2020
- LLM data and leakage: Meng et al. 2022 SuperGen (2202.04538); Gerstgrasser et al. 2024 (2404.01413); Lopez-Lira, Tang & Zhu 2025 (2504.14765); Sarkar & Vafa 2024; Li et al. 2025 "Profit Mirage" (2510.07920); He, Lv, Manela & Wu 2025 ChronoBERT (2502.21206); Glasserman & Lin 2023 (2309.17322); Trade-R1 2026 (2601.03948); StockBench (2510.02209); APIGen (2406.18518); Ratner et al. 2017 Snorkel (1711.10160)
- Catalysts: Boudoukh, Feldman, Kogan & Richardson (NBER w18725); Baker, Bloom, Davis & Sammon (NBER w28687); Massive 8-K taxonomy (2607.08346)

## 6. Updates
- 2026-10-08 correction (SYZ, drafted with Claude): **kit check of §1's Binance Vision row.** The Participant Guide (p.17, "Binance Skills") lists the `binance` skill as "Binance spot market data through binance-cli: candles, tickers, order book, recent trades", notes "Public market data, no key needed. Its trading functions must not be used in this competition", and lists `trading-signal` as "can inform decisions". So the kit sanctions Binance spot market data (api.binance.com via the skill) as an agent data source; only its trading functions are banned. The kit never mentions data.binance.vision. Revised position: use the `binance` skill / api.binance.com klines freely (the bStock pairs only start 2026-06-11, so the klines API covers their full history); do not use data.binance.vision bulk files (separate product, own CC BY-NC-SA terms, not named by the kit, adds nothing for these pairs). §4 item 4 drops to an optional confirmation. The probe tool (`tools/probe_kit_sources.py`) touched data.binance.vision once for an access check; no training data came from it.
- 2026-10-08 update (SYZ, drafted with Claude): **FRED replacements tried.**
  - KRW/USD: the Board's own H.10 page (federalreserve.gov/releases/h10/hist/dat00_ko.htm, won per dollar, from 2000-01-03, release of 2026-10-05) is the same series as FRED `DEXKOUS`; the Board's site says its information "is in the public domain and may be copied and distributed without permission" (cite the Board; no AI/ML clause). Claude's sandboxes cannot reach federalreserve.gov, so `tools/fetch_h10_krw.py` downloads and parses it from the team network (parser tested on a synthetic snippet only; it exits if no rows parse).
  - VIX: replaced by realised volatility from kit data, `tools/realised_vol.py` (read-only, reads `data/probe/`). Annualised daily-bar volatility, full history / EWMA 20-bar half-life: NVDAB 35% / 29%, GOOGLB 34% / 30%, SKHYB 96% / 75%, TSLAB 47% / 40%, MSFTB 30% / 26%; Ondo (from Jun 2025) NVDA 38% / 26%, GOOGL 31% / 24%, TSLA 46% / 36%, MSFT 27% / 23%. SK Hynix tokens are ~3× the others on both venues (largest daily moves +20% / −15% in late July 2026), which matters for C1 caps and IDEA-006 sizing. Ondo daily bars skip most weekends (≈ 296 bars/year), so their volatility is per trading bar.

- 2026-10-08 update (SYZ): `tools/fetch_h10_krw.py` run from the team network: 6,980 rows, 2000-01-03 → 2026-10-02, 272 ND (holidays), raw page sha256 `ba5aace919baf6c143fc693d8406c39a7f73e52d4f337092df2b082491a417d0`. Checked: dates sorted, no duplicates, ~261 rows/year, range 903–1,570 KRW per USD. Stored in `data/raw/fed_h10/` (git-ignored). FRED `DEXKOUS` is no longer needed.

## 7. Track A build spec: distilling an open-weight teacher into a small classifier (2026-10-08, SYZ, drafted with Claude)
⚠ RECOMMENDED — NOT DECIDED (GAP-57). Written so the pipeline can be built from this section alone. Labels describe text only; no return labels anywhere.

**Teacher terms (checked 2026-10-08).** Not every Chinese model is fine: what matters is the terms of the service you pay for, plus the model licence.

| Teacher route | Terms on training other models with outputs | Verdict |
|---|---|---|
| DeepSeek Open Platform API (ToS released 2026-04-22, effective 2026-04-29) | §4.2: rights in Outputs assigned to you; permitted uses include "training other models (such as model distillation)" | **Clear.** Preferred paid route |
| Kimi / Moonshot OpenPlatform API (ToS updated 2026-07-30) | §3.2(5) restricts developing models "that have potential competitive possibilities with the Services without authorization"; Moonshot may use your content to improve its services by default | Ambiguous: a veto classifier hardly competes, but the clause is broad. Ask in writing or skip |
| Qwen via Alibaba Cloud Model Studio | Service-specific terms (modified 2026-09-28) say nothing on distillation; **free-trial outputs "may only be used to evaluate the model's performance"**, not for any commercial purpose or third parties. Paid-use general terms not read | Do not use free trial quota. Paid route: read the general terms first |
| Qwen3 open weights (e.g. Qwen3-30B-A3B-Instruct-2507, card: apache-2.0) run locally | Apache-2.0; no output restriction | Clear. Note Qwen3.8-Max (Aug 2026) has its own licence (revenue threshold for large firms) — check each model's card |
| gpt-oss-20b open weights run locally (card: apache-2.0; < 16 GB) | Apache-2.0 | Clear |
| GLM (Z.ai), MiniMax, others | Not checked | Read the API terms before use |
| Any third-party host (OpenRouter, Together, …) | Host terms apply on top of the model licence | Read before use |
| Claude (any surface) | Anthropic AUP: no "model distillation" without authorization | **Never a teacher** |

**Pipeline (code in `tools/` or a `pipeline/` package; all data under `data/`, git-ignored; commit manifests and hashes only, F-61).**
1. **Universe and pull.** EDGAR submissions for the 4 US eligible names + ~50 large US filers (frozen list, committed), 2022-01 → 2026-10. 8-Ks only for the MVP: items, `acceptanceDateTime`, accession number, Ex. 99.1 text (HTML → text). Run from the team network with a declared User-Agent, ≤ 10 req/s. Store raw responses with fetch time and sha256.
2. **Documents.** One row per 8-K: accession, CIK, acceptance time, item codes, cleaned text truncated by a fixed rule (headline + first N paragraphs + any guidance table; N frozen on day 1). Masked copy: company names, tickers, products and dates replaced by placeholders.
3. **Taxonomy v1 (frozen on day 1, versioned).** Event type from item codes (2.02, 1.01, 1.05, 2.05, 2.06, 4.02, 5.02, 7.01, 8.01, …) collapsed to ~12 classes; severity 1–3 and veto yes/no with written definitions and examples; guidance direction (raised / cut / maintained / none).
4. **Gold set (humans only).** ~400 items stratified by item code (adverse items over-sampled, weights recorded), labelled blind on masked text by the team; 100 double-labelled; Cohen's κ per label. Claude may draft the guideline text but must not pre-fill any label.
5. **Teacher pass.** Masked text + rubric → JSON: labels, one quoted supporting span per label, confidence. Code checks: valid JSON, span is a substring of the input, numbers in the span match. Two teachers (or one teacher × 3 samples); keep agreements, send disagreements to human review. Log every request/response with model ID, date and hash (F-49 provenance). If run locally, keep per-class probabilities as soft labels.
6. **Student.** ModernBERT-large (or ChronoBERT; check its card first), shared encoder + heads for event type, severity, veto; trained on soft labels where available; class weights for rare adverse classes; 3 seeds; temperature calibration on a held-out split. Pin and hash the weights.
7. **Evaluation (real data only).** Teacher vs gold, student vs gold, student vs teacher, student vs the zero-shot runtime LLM; macro-F1, veto recall/precision with CIs, ECE. Post-cutoff slice: 8-Ks accepted after the teachers' knowledge cutoffs (Jul–Oct 2026 at least). Hindsight probe: Spearman ρ between (teacher − gold severity) and |5-session return| on kit prices. Kill criteria: §3 Track A.
8. **Runtime.** Student on CPU; its output feeds the declared rule layer (veto/exit); the zero-shot LLM + item-code rules is the fallback. Every runtime input/output is logged (F-49).
9. **Optional second student** (only if 1–8 finish early): LoRA on Qwen3-1.7B/4B as a claim verifier ("does this span support this claim?") trained on teacher rationales + answers.

**Timeline.** Oct 9–10 declare teacher(s) and student base (F-12); freeze universe, taxonomy, truncation rule. Oct 10–12 EDGAR pull; gold set. Oct 12–13 teacher pass. Oct 14–16 train and evaluate. Oct 17 ship or drop (kill criteria). Weights frozen by Oct 18.

**Cost [ESTIMATE].** MVP ≈ 3k docs × ~2.5k input + ~0.3k output tokens ≈ 7.5M in / 1M out per teacher pass: small at DeepSeek API rates (check the current price list), or one overnight run per laptop for gpt-oss-20b / Qwen3-30B-A3B locally. Student training: under an hour on one GPU, a few hours on an M-series Mac. If NUS SoC compute is used, first confirm its acceptable-use policy allows a personal-capacity contest.

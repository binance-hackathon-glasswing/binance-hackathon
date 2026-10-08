# IDEA-001 — Decision-model training set: sources, size and build workflow

- Date / author: 2026-10-03 / SYZ (drafted with Claude)
- Status: open
- What: build the point-in-time, labelled event dataset that trains, calibrates and evaluates the decision model (P(UP), P(FLAT), P(DOWN) over the next [5] US sessions; I-63), and the matched no-evidence panel for the H-02 baseline (EXP-001, D-07).
- Why it might help: the decision model is near chance zero-shot and ships over-confident (E-51), so fine-tuning, calibration and thresholds all depend on this dataset. EXP-001 cannot be pre-registered until the data, periods and sample size are fixed.
- Cost / risk: about 1 week of data work for one person plus an LLM batch pass. Main risks: LLM memorisation leaking into training inputs (I-37), price-data rights (F-71), and too few post-cutoff events for a conclusive test (H-02).
- Links: I-37, I-38, I-63, H-02, D-03, D-06, D-07, D-08, G-05, G-41, G-42, Q-19, Q-30, EXP-001

## 1. What one training example is
- **Unit:** one catalyst event for one underlying at decision time `t` = source acceptance time + [15] min of processing latency.
- **Input (state):** only items with `source_ts ≤ t` and `fetched_ts` recorded (the same G-05 filter code as live): the structured evidence assessment after claim verification, point-in-time price/volatility features, the regime state and the macro calendar context.
- **Label:** the underlying share's return from the entry reference to the close [5] sessions later. Entry reference = the next regular-session open after `t`, or that day's close if `t` falls inside the session (conservative: never earlier than `t`). Classes: UP if r > c + b, DOWN if r < −(c + b), FLAT otherwise; c = round-trip cost assumption, b = buffer (D-06). Store both absolute and index-relative (minus QQQ) returns, and pick one in D-06.
- **The declared values are not calibrated** (`skill/larp/plan.md`, "Declared values"). Three of them shape this dataset:
  - h = 5 sessions: choose or confirm it on the train and calibration blocks only.
  - The 50 bp cost / 50 bp buffer: keep c + b a parameter in the label code until Web3 quote costs are measured (from Oct 12).
  - The 6-call / 60 s evidence budget: the historical evidence pass uses the same budget.
- **No-evidence panel (V0):** the same names sampled every 5th session, without the evidence fields, so labels do not overlap.

## 2. Sources and access check (run 2026-10-03 from the team's Singapore network; no VPN)

| Need | Source | Reachable? | Rights / notes | Use |
|---|---|---|---|---|
| Catalyst events + timestamps | SEC EDGAR `data.sec.gov` submissions API | Yes. `acceptanceDateTime` and 8-K item codes are present; filing documents (e.g. the earnings press-release exhibit) download | US government data; fair-access rules: declared User-Agent, ≤ 10 req/s | Primary event source |
| Fundamentals as reported | EDGAR XBRL `companyfacts` | Yes | As above | Optional features |
| Filing full-text search | `efts.sec.gov` | Yes | As above | Optional |
| Second independent source | GDELT 2.0 raw 15-min files (events, mentions, GKG) since 2015-02 | Yes (files; 2025 sample downloaded) | Open use with citation | Second source and news events |
| — | GDELT DOC API | Timed out; it covers only ~3 months anyway | — | Not used for history |
| Macro values | FRED `fredgraph.csv` | Yes (no key) | FRED terms; some series are third-party copyright, so use BLS/BEA/Fed series only | Features |
| Macro vintages | ALFRED API | **Needs a free API key** (returns 400 without one) | FRED API terms | Point-in-time macro. **⚠ RECOMMENDED — NOT DECIDED:** not needed if macro *values* stay out of v1.0 model inputs; macro events enter as dates from BLS/BEA/Fed calendars. The Web3 API has no macro data |
| Underlying daily OHLC, adjusted, with corporate actions | **Licensed vendor (not chosen)** | Not tested: Tiingo needs a key (403); Alpha Vantage demo key works only for IBM | Proposal declares "licensed historical daily prices"; the vendor is to be declared at onboarding (F-12) | **Labels** |
| — | Yahoo chart endpoint | Reachable (NVDA from 1999) | **No licence; unofficial endpoint. Do not use for labels or features (F-71, G-42).** | None |
| — | Stooq CSV | Blocked by a JavaScript bot check | — | None |
| — | Nasdaq earnings-calendar API | Reachable | Unofficial endpoint, no licence | None; earnings timing comes from 8-K item 2.02 acceptance times |
| Token vs share history | Binance spot public klines (`api.binance.com`, `data.binance.vision`) | **Yes.** bStocks are listed on Binance spot as `<TICKER>BUSDT`; NVDABUSDT has daily bars from 2026-06-11 and 1-minute bars | Public market data, not Binance-internal (F-63). **Open question:** Binance.com does not serve Singapore users (E-16), so ask organisers before relying on it (proposed Q-31) | Basis-risk check only |
| — | BNB Smart Chain public RPC | Yes | Public chain data | Fallback for token prices (swap logs) |
| Live executable quotes | Binance Web3 API | **Yes (2026-10-03 15:42 UTC, team key, Singapore network, no VPN):** signed GET `/api/v1/dex/aggregator/supported/chain?binanceChainId=56` → HTTP 200, `code 0`, chain 56 = BNB Smart Chain. Without credentials it returns 401. This shows read access from Singapore only; trading bStocks from Singapore is still open (Q-12) | Whoever holds the Developer Portal keys runs `binance_test.py` | Not training; H-01 forward logging from Oct 12 |
| Decision model base | Hugging Face `convaiinnovations/laya` | Yes. Not gated, apache-2.0, revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` (2026-09-24) | The repo ships `.py` files (`rl_agent_api.py`, `rl_common.py`, `email_utils.py`). Reviewed 2026-10-04 at the pinned revision: imports only torch, transformers, safetensors, numpy and the standard library; no network, exec or subprocess calls. Base-model choice: see Q-30 (⚠ recommended: ModernBERT-large) | Pin this revision |

## 3. Universe and event counts (measured 2026-10-03)
- Binance spot lists **86** `…BUSDT` bStock pairs. This is a candidate list only; the official eligible list arrives at onboarding (Q-19).
  - 6 leveraged or inverse pairs are excluded (G-02): SOXLB, SOXSB, TQQQB, SQQQB, MUUB, KORUB.
  - 5 ETFs: QQQB, SPYB, SMHB, EWYB, DRAMB.
  - 72 single names map to an SEC CIK by ticker (unverified: some, e.g. CBRS, QNT, SHAZ, CYPH, AGPU, FWDI, SPCX, may be mis-mapped). 3 do not map: INTW, MVLL, SNXX. 8 are foreign filers that file 6-K/20-F rather than 8-K: ARM, ASML, BABA, NBIS, NOK, PDD, SKHY, TSM.
- Catalyst filings by the 72 names, by acceptance year:

| Form | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 (to Oct 3) | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| 8-K | 518 | 583 | 620 | 671 | 614 | 639 | 712 | 958 | 830 | 6,145 |
| 10-Q | 112 | 130 | 132 | 149 | 161 | 162 | 167 | 178 | 135 | 1,326 |
| 10-K | 37 | 41 | 44 | 47 | 54 | 53 | 53 | 59 | 52 | 440 |
| 6-K | 135 | 141 | 140 | 149 | 196 | 194 | 259 | 265 | 183 | 1,662 |
| 20-F | 6 | 6 | 6 | 6 | 7 | 7 | 8 | 7 | 7 | 60 |

- [ESTIMATE] Keeping material 8-K items (2.02, 1.01, 2.01, 2.05, 2.06, 4.02, 5.02, 7.01, 8.01) and merging events for the same name within 5 sessions leaves roughly 50–65% of these, i.e. about **500–800 usable events a year**: ~4.5–6k for 2018–2025 and ~400–600 for 2026.

## 4. How much data
- [ESTIMATE] **Tier A (bStock underlyings only):** ~5–6.5k events. Split by anchored walk-forward with a [5]-session embargo between blocks:

| Block | Period | Events (approx.) | Purpose |
|---|---|---|---|
| Train | 2018-01 → 2023-12 | 3–4k | fit |
| Calibration | 2024 | ~0.7k | temperature scaling |
| Threshold selection | 2025-01 → [evidence-LLM cutoff] | ~0.6–0.8k | θ, m (G-25) |
| Final evaluation (used once) | [cutoff] → 2026-09 | ~0.3–0.6k, depending on the cutoff | EXP-001 |

- **Why that is thin:** returns over 5 sessions are mostly noise. At 10–20% coverage the threshold block yields ~60–160 traded cases and the final block ~30–120. A reliability estimate for the traded bin needs ≥ ~100 cases, so EXP-001 is likely to come out inconclusive (H-02 already expects this).
- **Tier B (recommended lever):** the training universe does not have to equal the trading universe. Adding ~400–500 large US filers gives ~10× the events (~40–50k). Labels stay in the same domain (US shares). Cost: survivorship bias unless membership is point-in-time. A free proxy is the XBRL `dei:EntityPublicFloat` as filed before `t`. Use Tier B for train/calibration only; thresholds and final evaluation stay on Tier A names.
- **Model size versus data:** fully fine-tuning 395M parameters on 3–4k noisy labels will overfit. Freeze the backbone, or fine-tune the head plus the top layers (or LoRA). Always fit a logistic-regression/GBM baseline on the same structured fields; if the encoder does not beat it on the calibration block, ship the simpler model (F-31 allows classical ML).
- **No-evidence panel (V0):** 72 names × ~250 sessions × 8 years ÷ 5 ≈ 29k non-overlapping rows (Tier A).

## 5. The memorisation problem in training inputs (now I-67 in skill/larp/plan.md)
- I-37 covers evaluation. It also bites in **training**: if the evidence LLM writes the assessment for a 2021 event and already knows the outcome, judgement fields (durability, novelty, strength) carry future information into the inputs, and the decision model learns to over-trust them.
- Proposed rule: in pre-cutoff training data, feed the decision model only **extractive fields** (catalyst type and 8-K item, reported figure vs prior figure, guidance direction, source agreement) plus anonymised text. Judgement fields enter the model only if they help on post-cutoff data. Run the "name the firm" probe on a sample of each block (G-39).
- The evidence LLM (D-03) must be chosen before the evidence pass, because its training cutoff sets the threshold/final split.

## 6. Build workflow
| Step | What | Output | Owner (proposed) | By |
|---|---|---|---|---|
| 0 | Freeze D-06 target items (h, c + b, absolute vs index-relative); choose price vendor and evidence LLM (D-03); pre-register EXP-001 periods and n | Ledger commit | Yao Zhu + Isaac | Oct 10 |
| 1 | Universe table: bStock → ticker → CIK, verified by hand; replace with the official list at onboarding | `universe` table + hash | Isaac | Oct 6 |
| 2 | Raw ingest, append-only, each item stamped with `source_ts`, `fetched_ts`, URI, sha256: EDGAR submissions + primary docs/exhibits; GDELT files filtered to universe names; ALFRED vintages (only if macro values are used, see §2); release calendars; vendor prices; bStock klines (if Q-31 allows) | Raw store **outside the repo** | Isaac | Oct 10 |
| 3 | Event table: filter items, merge within 5 sessions, set `t` | `events` | Isaac | Oct 11 |
| 4 | State builder = the live G-05 point-in-time code path, run in historical mode | `states` | Yao Zhu | Oct 13 |
| 5 | Evidence + verification pass on anonymised inputs, batch API, full I/O logged (G-06) | `assessments` | Yao Zhu | Oct 15 |
| 6 | Labels from vendor prices; corporate-action check; token-vs-share basis report on bStock history | `labels`, basis report | Isaac | Oct 12 |
| 7 | Splits + embargo; snapshot hash recorded in EXP-001 | frozen snapshot | Isaac | Oct 15 |
| 8 | Train baseline vs encoder; calibrate; pick thresholds | checkpoints + hashes (G-47) | Yao Zhu | Oct 18 |
| 9 | Final evaluation once → EXP-001 result; D-07/D-08 | ledger result | Yao Zhu | Oct 19–22 |

- [ESTIMATE] Evidence-pass volume for Tier A: ~6k events × ~10k input tokens (filing excerpt + second source) ≈ 60M input and ~6M output tokens. Tier B under the same pass is ~10× that, so for Tier B use a smaller model or extractive fields only. Price it against the chosen provider's current batch rates.
- Code that builds the dataset or trains the model goes in the repo (F-61). The data itself stays out (F-61, G-41): add `data/` to `.gitignore` and reference snapshots by hash only.

## 7. Open items raised here
- Proposed **Q-31**: may we use Binance spot public market data (bStock klines) from Singapore, given that Binance.com does not serve SG users (E-16)? Until answered, use BSC on-chain swap logs for the basis check.
- **D-09** (now in skill/larp/plan.md §6.4, with a ⚠ RECOMMENDED — NOT DECIDED test plan): price vendor for labels. Aim to decide by Oct 6 so labels can be built in onboarding week.
- ALFRED API key: only if the team keeps macro values as model features (⚠ recommended: leave them out of v1.0; team to discuss).
- Web3 API: the team has a Developer Portal key pair. Each member holds the secret in their own local `.env` (gitignored; template in `.env.example`); it is never shared with Claude or written in the repo. Any member runs `binance_test.py` on the Singapore network. First run on 2026-10-03 returned 200 (see §2), so read access works from Singapore; E-15's 40304 report did not reproduce for this endpoint. Wait for the official endpoint docs before trying token-list or quote endpoints.
- Participant kit expected Oct 5 (team statement; the official onboarding documents per F-18). Before step 2 ingest, check it for: the eligible list (Q-19, replaces §3's candidate universe); data rules (F-73); the valuation source (Q-04, which may affect the label price series); historical-data endpoints in the Web3 API docs; and whether the current key is the challenge's development credential or needs re-issuing (G-09).
- Promote this idea to an EXP entry once step 0 is frozen.

## 8. Updates
- 2026-10-05 update (SYZ, drafted with Claude): **participant kit received** (SKILL.md F-90..F-105). Effects on this idea:
  - **Universe:** only five bStocks are eligible: NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB (F-91). §3's 86 pairs / 72 single names are now background only. Tier A = four US 8-K filers (NVDA, GOOGL, TSLA, MSFT) + SK Hynix (`SKHY`, a 6-K/20-F filer per §3; its main disclosures are Korean).
  - **Event counts:** [ESTIMATE, scaled from §3's 500–800 usable events/year for 72 names ≈ 7–11 per name] about 30–45 usable events a year for the four US names, ~220–360 for 2018–2025, and a final-evaluation block of perhaps 10–40 cases. Recount from EDGAR for the four names before relying on this. §4's Tier A block sizes no longer hold; Tier B (a wider US large-cap training universe) becomes the only way to get a usable training set, and EXP-001 is very likely inconclusive (D-08 decides what v1.0 runs). Decision: D-10 in skill/larp/plan.md.
  - **§7 checklist against the kit:** eligible list — answered (F-91); data rules (F-73) — not in the kit; valuation source (Q-04) — not in the kit; historical-data endpoints — the Web3 API has `candles` for bStock token history (F-95), no underlying-share history; key re-issue (G-09) — the kit does not re-issue the Web3 key; the separate `AI_SEEDS_SECRET` is issued per registered wallet (F-92).
  - **Q-31:** the Guide lists the `binance` skill (public spot market data) for use (F-104); the Singapore question is still open. The Web3 `candles` endpoint is an alternative source for the token-vs-share check.
  - **D-09 (price vendor):** coverage now needed for NVDA, GOOGL, TSLA, MSFT, SKHY (or the Korean line) and any Tier B names; not ETFs.
  - **Workflow §6:** step 1 (universe table) shrinks to the five kit addresses plus the Tier B list; steps 0–1 wait on D-10.
  - 2026-10-05 note (SYZ, drafted with Claude): two §7 lines are superseded — "Wait for the official endpoint docs before trying token-list or quote endpoints" and "Participant kit expected Oct 5". The kit arrived on Oct 5 and is now captured in the repo: compact facts in SKILL.md §1.9 (F-90..F-112), every endpoint with its parameters in skill/reference/participant-kit.md K6, verbatim copies in docs/official/kit/. The five eligible addresses for step 1 are F-91 / K3.
- 2026-10-06 update (SYZ, drafted with Claude): **data plan decided** (D-10 (a) in skill/larp/plan.md). This supersedes §4's rule "thresholds and final evaluation stay on Tier A names":

| Job | Fit | Data | Period |
|---|---|---|---|
| Parameters | weights (GBM/logistic baseline; encoder only if it beats it on calibration) | broad Tier B, ~400–500 US large caps, point-in-time membership via `dei:EntityPublicFloat` filed before `t`; sector + size features | 2018-01 → 2023-12 |
| Hyperparameters | model HPs; confirm h = 5 | purged walk-forward CV inside train, [5]-session embargo | 2018-01 → 2023-12 |
| Calibration | temperature | Tier B | 2024 |
| Thresholds | θ, m (G-25) | Tier B; five-name slice reported, not optimised on | 2025-01 → [evidence-LLM cutoff] |
| Generalisation (used once) | nothing | all Tier B names (primary) + five-name slice with CI; token-vs-share basis gate on bStock `candles` before live (GAP-22) | [cutoff] → 2026-09 |

  - **Features:** pre-cutoff rows get extractive fields only (8-K item, reported vs prior figures, guidance direction, source agreement, price/vol, calendar); the full LLM evidence pass runs only on post-cutoff events, and judgement fields enter the model only if they help there (I-67). This also removes §6's "Tier B evidence pass is ~10× the cost" problem.
  - Still open: SKHYB handling (D-10 (b)); price vendor with Tier B coverage including delisted names (D-09); the evidence LLM, whose cutoff sets the threshold/final boundary (D-03); the EDGAR recount (GAP-43). sec.gov was blocked by the egress policy in the 2026-10-06 session, so run the recount from a normal network.
  - 2026-10-06 note (SYZ, drafted with Claude): red-teamed in [IDEA-003](IDEA-003.md); its fixes (RT-01..RT-29) and dataset gates (M1–M7) are recommendations, not decisions.
  - 2026-10-06 note (SYZ, drafted with Claude): [IDEA-004](IDEA-004.md) proposes replacing the block map with pilot 2018–19 + a frozen 2020-01 → 2026-09 walk-forward, and a single primary metric (recommended, not decided).

## 9. Data acquisition plan (2026-10-07, SYZ, drafted with Claude)
Decided by SYZ on 2026-10-07: GDELT history via a one-pass BigQuery extract; full Korean data for SK Hynix (plan.md D-10 (b)). Recommended, awaiting SYZ's confirmation: "prices wide, events narrow". Price vendor still open (D-09). Rows, labels and model are not covered here (IDEA-004, IDEA-005).

| Need | Source and access | Scope | Rights / notes | Status |
|---|---|---|---|---|
| Daily OHLCV, adjusted + raw, splits/dividends, delisted names | Licensed vendor (D-09): leaning EODHD, Tiingo as backup | All Tier B names (~450, point-in-time membership) + ETFs (SPY, QQQ, SMH, sector ETFs) + `SKHY` ADR + KRX 000660, 2017-01 → | Personal licences forbid group sharing; contest use not addressed → written answer first (draft below) | **Open** |
| Filings, events, XBRL as filed | SEC EDGAR bulk `submissions.zip` and `companyfacts.zip` (nightly), plus filing documents and exhibits | Membership and size for all Tier B; events and exhibits only for the 4 US eligible names + ~40 neighbours | US government data; declared User-Agent, ≤ 10 req/s. Run from the team's network (Claude's sandboxes cannot reach sec.gov) | Ready |
| News context | GDELT 2.0 GKG via the BigQuery sandbox (free, no card: 1 TiB of queries/month, 10 GiB storage, tables expire after 60 days) | Per-firm 15-minute and daily counts, unique domains and mean tone for the 4 + ~40 names, plus market-wide totals for normalisation, 2018-01 → 2026-09 | Open use with citation. The same GKG data as the live 15-minute files (train/serve parity) | **Decided.** Run a dry run first: one pass over DATE, V2Organizations, V2Tone and DocumentIdentifier is [ESTIMATE] 0.3–0.6 TB. If it exceeds ~0.8 TiB, split the years across two months |
| Macro calendar | federalreserve.gov FOMC calendars; BLS (CPI, Employment Situation) and BEA (GDP, PCE) release schedules | Dates and times only, 2018 → 2026 | Public | Ready |
| Market context | Vendor ETF prices; realised volatility computed from them | — | FRED `VIXCLS` is CBOE-sourced (third-party); keep FRED to government series (§2) | Follows D-09 |
| SK Hynix | KRX 000660 prices (vendor); `SKHY` ADR (vendor) and SKHYB token (Web3 `candles`) for the basis check; KRW/USD from FRED `DEXKOUS` (Fed H.10); OpenDART disclosure list and documents (free API key) | 2018 → | DART is mostly Korean and gives a receipt date only → t = next KRX session (`exchange_calendars` XKRX). Korean text goes through the same verbatim-span extractor (I-67, IDEA-004 T6) | **Decided** (D-10 (b)) |
| Token history | Web3 `candles` for the five bStocks (F-95); Binance spot klines only if Q-31 allows | Jun 2026 → | Public market data | Ready once the API key is set |
| Live costs and trading hours | Our own quote logger (IDEA-004 T10) and `openState` logger (GAP-44) | From now on | Read-only, no signing, no `log()` | **Start now**: GAP-44 needs 7+ days including a weekend |

**Neighbour rule (frozen; point in time; IDEA-005 R5).** At each yearly refit date D, take US-listed common stocks whose EDGAR SIC code is in the eligible names' industries and adjacent ones (357x computers, 367x electronic components including 3674 semiconductors, 737x software and internet services, 371x motor vehicles). Rank them by market cap at D − 1 (unadjusted close × `dei:EntityCommonStockSharesOutstanding` from the latest filing before D) and keep the top 40, excluding the eligible names. SIC codes are current-only: record this as a known look-ahead. No hand-picking after the rule is frozen.

**Storage.** `data/` is already git-ignored. Layout: `data/raw/<source>/…` (append-only; every file stamped with source URI, `fetched_ts` and sha256) → `data/snapshots/<name>-<sha256>.parquet`. The ledger references snapshots by hash only (F-61, G-41).

**Order of work.** 1) Vendor emails today, plus a trial key restricted to our own names to build the loader. 2) EDGAR bulk files and the Tier B membership table. 3) GDELT dry run, then extract. 4) Calendars. 5) Korean data. 6) Snapshot and hash. Logging (GAP-44, T10) runs in parallel from now on. Suggested leads, not assignments (GAP-37): Markets/Data for 1–3 and 5; Agent/Model for 4 and 6.

**Draft vendor question (send to EODHD and Tiingo):** "We are a team of four university students in a prize competition run by Binance (Oct–Nov 2026). We want end-of-day US prices (including delisted names), and for EODHD Korean prices, for 2017 to the present, for about 500 symbols. We would store the data privately, use it to train and evaluate a trading model, and share it only within our four-person team. Nothing would be redistributed or published, except aggregate statistics in our competition report. Which plan and licence permit this? Is a student or personal plan enough, or do we need a commercial licence? Please confirm in writing."

**Sources (checked 2026-10-07):**
- EODHD: [pricing](https://eodhd.com/pricing), [delisted data](https://eodhd.com/financial-apis/delisted-stock-companies-data-2), [terms](https://eodhd.com/financial-apis/terms-conditions), [SKHY.US](https://eodhd.com/financial-summary/SKHY.US), [KO exchange](https://eodhd.com/exchange/KO)
- [Tiingo pricing](https://www.tiingo.com/about/pricing)
- [Massive pricing](https://massive.com/pricing)
- [Sharadar via QuantRocket](https://www.quantrocket.com/pricing/data/sharadar)
- [NUS BIZ Financial Database](https://bizfaculty.nus.edu.sg/financial-database/), [WRDS terms of use](https://wrds-www.wharton.upenn.edu/users/tou/)
- [BigQuery sandbox](https://docs.cloud.google.com/bigquery/docs/sandbox), [GDELT size (2021)](https://blog.gdeltproject.org/?p=13324)

## 10. Kit-provided data for the five names (2026-10-07, SYZ, drafted with Claude)
SYZ's direction: build the verifiable training set from what the participant kit provides or names first; other sources (§9) come after. Measured by the read-only probe (participant-kit.md K6a).

| Kit source | What it gives for the five names | History | Verifiable? |
|---|---|---|---|
| Web3 `candles` | Token OHLCV + trade count, 24/7 | Daily: complete since launch in one call (NVDAB/TSLAB 2026-06-12, MSFTB 07-01, SKHYB 07-14, GOOGLB 07-15): 495 token-days. Intraday: 300 bars per call, paged back with `after` → ≈ 2,000–2,800 hourly bars per token (≈ 12k in all) | Yes: contest-provided; store raw responses with fetch time and sha256 |
| `rwa/tokens`, `rwa/price` | tokenPrice, referencePrice (derived from the token price), tokenToShareRatio, statusInfo, 24h volume, market cap, P/E | Snapshot only | From now on, by logging snapshots |
| `rwa/underlying-market` | statusInfo + fundamentals snapshot (52-week high/low, 24h share volume, market cap, dividend, P/E, P/B) | Snapshot only | From now on, by logging |
| `quote-and-swap` (quote only) | Executable price, price impact, route | None stored by the API | From now on: our quote logger (IDEA-004 T10) |
| Skills named in the Guide (F-104) | `binance` spot data for `<TICKER>BUSDT`; `query-token-info` on-chain candles; `binance-tokenized-securities-info` (Ondo tokens only, not bStocks) | Not yet probed | `binance` spot data still waits on Q-31 |

**What kit data can support:** volatility, correlation and sizing of the actual tokens (C1, IDEA-006); 24/7 and weekend behaviour (H-01; about 17 weekends for NVDAB/TSLAB, 12 for GOOGLB/SKHYB); liquidity by hour; and, with forward logging, costs (T10), trading hours (GAP-44) and the ratio and fundamentals snapshots.

**What it cannot support on its own:** training or validating a return model (≈ 16 non-overlapping 5-session windows per name in one market period, about one earnings report each); and the token-vs-share basis check (T9), because `referencePrice` is derived from the token price and the kit has no independent share price. Both need data from outside the kit (§9).

Next: a collector that pages the full candle history with `after` and stores raw responses with hashes, plus a snapshot logger for `rwa/tokens`, `rwa/price` and `rwa/underlying-market`. The quote logger and GAP-44 run alongside it.

## 11. Data-source priority: kit sources first (2026-10-07, SYZ, drafted with Claude)
**Decided by SYZ:** for now the training and validation data comes only from what the participant kit provides or names, so every dataset can be traced to a contest-sanctioned source. External sources from §9 (licensed price vendor, EDGAR, GDELT, Korean data) are on hold, not dropped.

All four kit sources were probed read-only from the team network on 2026-10-07 (participant-kit.md K6a, K6b; raw responses with sha256 in `data/probe/`):

| Kit source | Status | What it adds for the five names |
|---|---|---|
| Web3 Open API (`candles`, `rwa/*`, quotes) | Works | Primary: the traded instrument. Daily history since launch; intraday paged with `after`; snapshots and quotes logged from now on |
| `query-token-info` | Works | Mirror of the Web3 candles (identical closes); adds on-chain trading-activity snapshots. Candles are served by `dquery.sintral.io` |
| `binance-tokenized-securities-info` | Works | Fundamentals snapshot (`stockInfo`); **Ondo tokens for NVDA, GOOGL, TSLA, MSFT back to Jun 2025** (≈ 16 months; SKHY only since Jul 2026), plus xStocks; Ondo vs bStock daily-return correlation 0.91–0.99 |
| `binance` skill (Binance spot `…BUSDT`) | Works from Singapore (Q-31 annotated) | A second venue for the same tokens (CEX vs on-chain), one day more history; differs from on-chain by a median 10–20 bp |

**What this changes:**
- The longest kit-sourced price history for the four US names is now the Ondo series: about 16 months of 24/7 tokenized-stock prices. Still far from the 2018–2026 panel in §4/§9, and still token prices, not share prices.
- No kit source gives an independent share price, so the token-vs-share check (GAP-22, IDEA-004 T9) can only be done across venues and issuers for now.
- Everything the earlier plans built on long share-price history (Tier B training, the 2020–2026 walk-forward, IDEA-004's block map) cannot be built from kit data alone. These plans stay recorded but wait until the team decides on external data.

Next: a collector for the four kit sources (raw responses, fetch time, sha256; intraday paging), plus forward logging of snapshots, quotes and `openState`.

## 12. For team discussion: limits of kit-only data and the options (2026-10-07, SYZ, drafted with Claude)
Raised by SYZ for the team. No option below is decided.

**Issue 1 — no independent share price.** Every kit source prices a *token* (bStock on-chain, Binance spot, Ondo, xStocks); `referencePrice` is derived from the token price. So we cannot measure the token's premium or discount to the share. This matters most off-hours and at weekends (H-01), if the final valuation uses a share-based reference (Q-04), and when learning how the company reacts to news (the share is the clean signal; the token adds noise). Cross-venue agreement is only a partial check: all these tokens are hedged against the same share and can drift together.

| Option | What it takes | Trade-off |
|---|---|---|
| 1A Token-only: treat the token as the instrument; check venues against each other (bStock, Binance spot, Ondo, xStocks) and flag divergence | Nothing new | Cannot see a common drift away from the share |
| 1B Ask the organisers for the valuation source (Q-04) and whether they provide or approve share-price data | One message | Depends on their answer and its timing |
| 1C Share prices for only the five names + a few ETFs from a free vendor tier, with the vendor's written OK (IDEA-001 §9) | One email; small download | Leaves the kit-only scope; licence is personal |
| 1D Paid licence for one month (EODHD or Tiingo) | ~$20–50 | Leaves the kit-only scope; the team has said it does not plan to pay |

**Issue 2 — no long history.** Kit data reaches back ≈ 16 months for NVDA, GOOGL, TSLA, MSFT (Ondo tokens, from Jun 2025) and 3–4 months for the bStocks themselves (SK Hynix: ≈ 3 months either way). That is ≈ 66 non-overlapping 5-session windows per name, largely one market path; it starts after the Jan 2025 DeepSeek drop and the Apr 2025 tariff sell-off, so it contains no crash or bear market; about 5 earnings reports per name. It is too little to train and validate a return model, to tune and still hold back a clean test, or to stress-test the drawdown rules.

| Option | What it takes | Trade-off |
|---|---|---|
| 2A Rules first, no trained return model: the C1 book with parameters from published research; volatility and costs from kit data; the catalyst/LLM loop as a fixed-rule veto/exit reported descriptively | Version event for the entry rule (proposal's "pre-registered default"); declarations by Oct 10 | Little to validate; the declared calibrated decision model does not ship as a return predictor |
| 2B Train a small model on the Ondo history (≈ 16 months) and report it as exploratory | A collector for Ondo candles | Single regime, low power; easy to overfit; must not be presented as validated |
| 2C Add outside long history (licensed prices, EDGAR, GDELT): re-open §9 and IDEA-004's 2020–2026 walk-forward | Licence answers or payment; 8–10 person-days (IDEA-004 §7) | Leaves the kit-only scope; tight before the Oct 18 freeze |
| 2D Simulated stress tests for the risk rules (resampled and scaled-tail scenarios, as in IDEA-006) | ≈ 1 day; no new data | Only as realistic as its assumptions |
| 2E Combination: 2A + 2D now, 2C later only if a licence answer arrives in time | As above | Two tracks to manage |

Deadlines that bear on the choice: onboarding declarations by Oct 10 (F-12: principal data and model services); model freeze Oct 18; v1.0 freeze Oct 27–29. Tracked as GAP-56.
- 2026-10-08 note (SYZ, drafted with Claude): FRED's terms prohibit use "in connection with the development or training of any ... machine learning" (fred.stlouisfed.org/legal). §2's FRED/ALFRED rows and §9's `DEXKOUS` are superseded: KRW/USD now comes from the Board's H.10 page (public domain; `tools/fetch_h10_krw.py`), market volatility from kit data (`tools/realised_vol.py`). Also: data.binance.vision has its own terms (CC BY-NC-SA, §4.2 no live-trading use); use Binance spot data only via the kit-named `binance` skill / api.binance.com. See [IDEA-007](IDEA-007.md) §1, §6.

## 13. Source-rights review and reconciliation (2026-10-08, Codex)

- Scope: provider-documentation research only; no dataset ingestion, training, credentials or trading runs. This note was reconciled against remote main f41c00c before publication. The earlier local checkout ended at 71d25da and lacked sections 9-12 and IDEA-007; recommendations made against it are superseded where noted below. No team decision is changed.
- Current scope: section 11's kit-first decision governs; EDGAR, GDELT, licensed prices and Korean external data remain on hold. D-10 (a)/(b) were decided in the newer history, with their external-data implementation on hold; they must not be described as wholly undecided. IDEA-007's proposed text-classification/distillation track remains a recommendation, not an adopted replacement for the return model. Source suitability below is conditional on reopening external acquisition and clearing applicable rights.
- Correction to the earlier ALFRED suggestion: do not use FRED/ALFRED for this model. Independently checked https://fred.stlouisfed.org/legal/ on 2026-10-08: its prohibited-use clause covers AI/ML development and training, and its applicability section includes ALFRED. Series-level permission and historical vintages do not override that restriction. Preserve IDEA-007 section 6's direct Fed H.10 replacement and kit-derived volatility.
- [PRIMARY, provider pages checked 2026-10-08] SEC EDGAR remains the preferred US catalyst source: submissions and XBRL APIs plus original filings/exhibits. SEC's dissemination policy allows copying/distribution of information on sec.gov without SEC permission; cite the source. Follow declared User-Agent and <=10 requests/second fair access. Do not generalise this to all linked third-party material. Sources: https://www.sec.gov/search-filings/edgar-application-programming-interfaces ; https://www.sec.gov/about/privacy-information#dissemination ; https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data . Historical inputs must select filings by acceptance/availability time, not fiscal period; later amendments/restatements must not replace earlier inputs.
- [PRIMARY] GDELT allows academic/commercial/government use and redistribution of its datasets, with attribution and a link. Use its own metadata/features for discovery and supporting inputs. This does not establish a licence to scrape/train on every linked publisher's article. A syndicated story is not independent corroboration (GAP-25). Sources: https://gdeltproject.org/about.html (Terms of Use); https://gdeltproject.org/data.html .
- [PRIMARY; correction to the earlier trial recommendation] Tiingo terms, updated 2026-10-06, prohibit persistent storage of data AND derived products on Starter/Trial plans. Eligible paid plans allow storage while active; termination requires data deletion, including compliance stores. Some non-reconstructable derived outputs are permitted; API redistribution needs separate permission. Starter/trial is therefore unsuitable for our retained dataset. Any paid choice needs team-use, training, audit disclosure and retention compatibility checked before adoption. Source: https://app.tiingo.com/tos/ sections 1.6 and 7.3.
- [PRIMARY] EODHD personal use is limited to an individual's own investment activities; group use falls under professional use and personal redistribution is prohibited. Treat it as a commercial-licence candidate, not an approved personal-plan fallback. Obtain terms covering team training, retained snapshots and organiser access; test corporate actions and exact instrument coverage separately. Source: https://eodhd.com/financial-apis/terms-conditions .
- [PRIMARY, conditional candidate] OpenDART provides Korean disclosures/financial data, useful for investigating SK Hynix. Its terms require an approved application/key, impose usage limits, prohibit third-party credential use and leave content rights subject to copyright/public-data law. No blanket ML/audit permission was established here. Verify issuer identity, original language/publication time, translation availability and exact underlying/price mapping before SKHYB training; do not assume the earlier SKHY/EDGAR mapping is validated. Sources: https://engopendart.fss.or.kr/intro/main.do ; https://engopendart.fss.or.kr/intro/terms.do .
- Kit-source position: use Web3 data and the kit-named public-data skills under section 11 and IDEA-007 section 6. The latter records the team's api.binance.com research-use position; do not reinstate the old blanket Q-31 hold. Keep data.binance.vision bulk files excluded under their separate terms. Token prices and cross-venue comparisons do not provide an independent underlying-share price (GAP-22).
- If external data is reopened, EDGAR evidence plus GDELT metadata and explicitly licensed prices remain candidates for the return-labelled plan; this is not authority to start acquisition or train. For IDEA-007 Track A, event-type labels can instead come from filing item codes, rules and a human gold set; return labels are not that task. Teacher/provider rights must be checked separately.
- Retain the temporal safeguards: use acceptance/availability time rather than fiscal period, preserve actual collection time separately from demonstrated historical availability (GAP-24), keep future returns only as matured labels, purge overlapping outcomes across chronological splits, and check every input-generating model's cutoff/memorisation risk (I-67). GDELT syndication is not independent corroboration (GAP-25).
- Audit/licence questions for any price vendor must explicitly include four-person team access, prize-competition model training, retained raw snapshots, and organiser access to required inputs/outputs. The earlier section 9 draft's aggregate-only disclosure assumption does not establish rights for the F-49 audit. No vendor is approved by this review.
- Open ownership (suggested leads, not assignments; GAP-37): Markets/Data/Risk (Isaac) handles source rights and coverage (GAP-23); Agent/Model (Yao Zhu) handles labels/leakage and track choice (GAP-06/07/21/56/57); Platform/Audit (Keegan) handles retention and audit compatibility (GAP-23/34). No backlog item was fully completed, so none is removed. The live DoraHacks page was unavailable in this review; no claim is made that unpublished or later official rules were independently verified.

## 14. Free training-source register and three-model follow-up (2026-10-08, Codex)

- Scope / status: records the source research from this conversation and the user's new [IDEA-008](IDEA-008.md). Free sources may cover only some of NVDAB, GOOGLB, SKHYB, TSLAB and MSFTB. Published licences and selected article relevance were checked; no corpus download, per-stock completeness audit, training run or trading result is claimed. Section 11's kit-first decision is unchanged; external candidates remain on hold pending a team decision and the outstanding rights/quality checks.
- User proposal: one model analyses past news article text plus timestamps; a second analyses historical price/volume series to generate trading signals; their aligned outputs feed a third, trained decision model. See IDEA-008 for schemas, leakage safeguards, labels, evaluation and source examples. This is an open idea, not an adopted replacement for IDEA-007 or the runtime stack.

| Source / training role | Relevant coverage / archive | Published terms and remaining checks |
|---|---|---|
| [Larxel S&P 500 stocks, Kaggle](https://www.kaggle.com/datasets/andrewmvd/sp-500-stocks): candidate underlying-share OHLCV/adjusted-close series for the time-series model and outcome labels | NVDA, GOOGL, TSLA, MSFT; card/preview range 2010-01-04–2024-12-20, per-stock availability varies; observed version 1023, last update 2024-12-23 SGT. No verified SKHY coverage | Card: CC0 1.0. Source description: FRED and yfinance. CC0 permits commercial reuse/training of rights the uploader holds, but cannot clear upstream Yahoo/yfinance/FRED restrictions. **Not rights-cleared.** Inspect exact columns/provenance and exclude restricted features; verify splits, adjusted values and missing rows |
| [Sinan tech stocks, Kaggle](https://www.kaggle.com/datasets/sinankr/tech-stocks-dataset): candidate daily prices/volume/features | 2010–2024; NVDA, TSLA, MSFT plus **GOOG**, not GOOGL; no verified SKHY | Card: CC0 1.0; README cites Yahoo Finance API. **Upstream rights unresolved.** Review precomputed indicators/macro provenance and inconsistent forward-fill/interpolation descriptions before using any feature |
| [English Wikinews](https://en.wikinews.org/wiki/Wikinews:Copyright): original article text for semantic/event features | [Google](https://en.wikinews.org/wiki/Category:Google), [Microsoft](https://en.wikinews.org/wiki/Category:Microsoft), [Tesla](https://en.wikinews.org/wiki/Category:Tesla_Motors) archives; examples in IDEA-008 §3.2 | CC BY 2.5 for 2005-09-25–2024-12-15; CC BY 4.0 from 2024-12-16; earlier material public domain per policy. Commercial sharing/adaptation permits text analysis/training within licensed rights; preserve attribution/licence/changes and check article-specific notices and non-original quotations/media |
| [EFF Deeplinks](https://www.eff.org/deeplinks): original analysis of software, advertising, privacy and regulation | Google and Microsoft examples in IDEA-008 §3.2; editorial/sector evidence, not earnings coverage | [Copyright policy](https://www.eff.org/copyright): original EFF material CC BY 4.0 unless otherwise noted. Commercial reuse/adaptation permitted with attribution/licence/changes; third-party material is separately excluded or cleared |
| [FTC announcements](https://www.ftc.gov/news-events/news/press-releases): regulator text on Nvidia/Arm and AI/cloud partnerships | NVIDIA, Alphabet/Google, Microsoft; archived examples in IDEA-008 §3.2 | [Website policy](https://www.ftc.gov/policy-notices/website-policy): original US-government material generally public domain under US law. **International scope for Singapore use unresolved**; third-party attachments/media and protected marks not blanket-cleared |
| [DOJ announcements](https://www.justice.gov/news): original antitrust/regulatory text | Google advertising/search; example in IDEA-008 §3.2 | [Legal policies](https://www.justice.gov/legalpolicies): public-domain basis unless otherwise indicated; exclude third-party material. **International scope unresolved.** Current versions can contain later updates and must not substitute for earlier historical inputs |
| [GDELT historical datasets](https://www.gdeltproject.org/data.html): organisation mentions, themes, tone, source URLs and processing times | Historical GKG/mention archives; exact eligible-company coverage and sample counts not audited | [Terms](https://www.gdeltproject.org/about.html) permit free academic/commercial/government dataset use; retain attribution/link. **Metadata permission does not license linked publishers' article text.** Processing time is not automatically original publication time |
| Kit Web3 `candles` and kit-named public market-data skills: actual-token series, forward quote/cost snapshots | All five eligible tokens; Web3 history since launch; longer Ondo history for four US names (section 11), still token prices | Existing kit-first source position, F-95/F-104 and section 13, applies. Record exact endpoint/source manifest; use Binance spot data through the kit-named skill/api.binance.com, exclude data.binance.vision under IDEA-007 §6. Limited history and no independent share prices remain GAP-22/56 |

- Licence basis: [CC0 legal code](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en), [CC BY 2.5](https://creativecommons.org/licenses/by/2.5/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and [Creative Commons' AI guidance](https://creativecommons.org/faq/#artificial-intelligence-and-cc-licenses). The CC licences need not mention AI by name for their existing permissions to apply; third-party rights and access terms remain separate. A dataset card is not proof that the uploader holds every underlying right. No blanket declaration that all these sources are cleared is made.
- Exclusions retained: FRED/ALFRED and data.binance.vision under sections 12–13/IDEA-007; unlicensed publisher full text obtained through GDELT; non-commercial datasets without separate permission for this use. Commercial/contest suitability must not be inferred just from a free download or an uploader's licence label.
- Remaining work: GAP-58 source rights/coverage and attribution register; GAP-59 historical availability, article versions and price quality; GAP-60 architecture choice, chronological out-of-fold fusion and pre-registration. Suggested functional leads remain unassigned under GAP-37. Source research/documentation is completed; these acquisition, validation and model decisions are not.
- 2026-10-08 review note (SYZ, drafted with Claude) on §§13–14: full findings in [IDEA-008 §7](IDEA-008.md#7-review-of-this-entry-and-idea-001-1314-2026-10-08-syz-drafted-with-claude) (R1–R7). Agreed: the FRED/ALFRED correction matches IDEA-007 §6, so the ALFRED row in §2 is superseded; the Tiingo Starter/Trial finding also removes the "trial key" route in §9 and plan.md D-09. Points for these sections: §13 rates EDGAR the preferred US catalyst source, yet §14/IDEA-008 build Model A on Wikinews/EFF/FTC/DOJ text (R3); neither section reconciles §14 with D-10 (a)'s Tier B training universe (R4); §§13–14 cite session context ("this conversation", "the earlier ALFRED suggestion", "earlier local checkout") instead of repo IDs or commits (R6). No decision changed.

## 15. SEC EDGAR taken off hold (2026-10-08, SYZ decision; drafted with Claude)
**Decided by SYZ (Agent/Model lead):** SEC EDGAR is usable — for the runtime evidence loop, for validation and evaluation sets, and for any later training — and is no longer on hold under §11. The other §11 holds (licensed price vendor D-09, GDELT, Korean data) are unchanged.
- **Why the hold could be lifted:** §11 was a scope choice (kit sources first), not a rights problem. EDGAR's terms are clear: "Information presented on sec.gov is considered public information and may be copied or further distributed" (https://www.sec.gov/privacy, checked 2026-10-08; also IDEA-007 §1). It is the only runtime text source in the 2026-10-08 comparison that is licensed, timestamped to the second (`acceptanceDateTime`, true UTC on the 6-K checked) and loggable for the audit ([IDEA-009](IDEA-009.md) §C.2). It covers all five names: NVIDIA CIK 1045810, Alphabet 1652044, Tesla 1318605, Microsoft 789019, SK hynix 2120882 (Nasdaq SKHY, files 6-K).
- **Conditions of use:** (1) the SEC's fair-access rules: a declared User-Agent with contact details and ≤ 10 requests/second (https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data); (2) run from the team network (cloud IPs have been blocked before; IDEA-007 §3); (3) record EDGAR in the licence register (GAP-23) and in every version manifest's services list (F-61); (4) keep raw documents under `data/` (git-ignored) and commit only accession numbers and hashes (F-61); (5) validation of an LLM uses filings accepted after that model's training cutoff (I-37, I-67); (6) Claude never labels anything that is trained on (Anthropic AUP; IDEA-007 §1) — EDGAR's terms do not change that.
- **Test pipeline:** `tools/edgar_fetch.py` (read-only): the filing list from the submissions JSON, the newest 8-K/6-K per issuer, the Ex. 99.x press release (or primary document) as plain text, with `acceptanceDateTime`, retrieval time, URL and sha256, and an optional filing count over a date window. Run: `python tools/edgar_fetch.py --user-agent "Glasswing research <contact email>" [--per-company 3] [--window 2025-10-29:2025-11-12]`. Tested only against mocked responses; a test run from the linked computer's sandbox could not reach sec.gov (proxy), so the first live run is from a team member's own terminal.


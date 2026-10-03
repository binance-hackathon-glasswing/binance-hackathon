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
| Decision model base | Hugging Face `convaiinnovations/laya` | Yes. Not gated, apache-2.0, revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851` (2026-09-24) | The repo ships `.py` files (`rl_agent_api.py`, `rl_common.py`, `email_utils.py`). Review them before loading; never use `trust_remote_code` without review. Q-30 is still open | Pin this revision |

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

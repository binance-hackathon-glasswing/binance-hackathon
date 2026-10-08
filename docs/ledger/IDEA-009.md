# IDEA-009 — Direction review: what v1.0 decides, with which data, and how changes from the proposal are recorded

- Date / author: 2026-10-08 / SYZ (requested); drafted with Claude (Cowork) and four research subagents (Skills-hub source read; literature re-check; runtime text-source terms; calendar and cost facts); merged and checked by Claude
- Status: open — **⚠ RECOMMENDED — NOT DECIDED.** Team decisions are listed in §8 with owners and deadlines.
- What: answers questions A–G of the temporary handoff note of 2026-10-08 (added in commit `a0507da`, deleted in the same change as this entry): the scoring readings, the LLM's role, runtime data, exposure and frequency, model-layer work, how deviations from the proposal are recorded, and the Oct 9–29 build plan.
- Why it might help: the team starts building on Oct 12 and needs one direction. Several earlier statements were estimates or opinions presented as findings; this entry re-checks them.
- Cost / risk: desk research, source reading and arithmetic only. No Binance API call from the cloud, no wallet transaction, no ai-seeds call. The research subagents fetched public web pages from the cloud, including sec.gov / data.sec.gov pages and one GDELT API call (HTTP 429).
- Links: F-08, F-12, F-15, F-20, F-30, F-31, F-40, F-42..F-50, F-52, F-60..F-66, F-93, F-95, F-96, F-99, F-102, F-104, F-106, F-107, F-114..F-117, K6, K6a, K6b, K14, K16, Q-03, Q-04, Q-06, Q-32, Q-33, Q-38..Q-40, D-03..D-10, G-05, G-11, G-21..G-25, G-46, G-50..G-53, H-01, H-02, I-61, I-63, I-66, I-68, IDEA-001, IDEA-004..IDEA-008, EXP-001, GAP-02..GAP-05, GAP-23, GAP-37, GAP-41..GAP-44, GAP-50, GAP-53, GAP-54, GAP-56, GAP-57

**Labels.** [V: source] checked in this review (file and quote, or a fetched page with its date). [V2: source] checked by a research subagent from a fetched page on 2026-10-08; the fetch tool returns a summarised page, so spot-check a quote before it goes into anything external. [R: file] taken from a repo file without re-checking. [E] estimate; its inputs are stated. [O] opinion. [A] assumption, unchecked. [T] team statement. [P] probe pending.

## 0. Summary
**⚠ RECOMMENDED — NOT DECIDED.** Keep the proposal's harness (bounded evidence loop, claim verification, thesis memory with falsifiers, deterministic governors). Make the proposal's own fallback explicit: v1.0 runs a pre-registered rule-based **base book** as the "pre-registered default" (four US names, the declared volatility-scaled sizing, a regime gate, a no-trade band, flat at the end). Every round, the **LLM decides per name from a fixed, risk-reducing menu**: CONFIRM, VETO_ENTRY or EXIT. EXIT needs a verified claim or a fired falsifier. The evidence comes from **SEC EDGAR**, fetched by our own tools. Code does all sizing and limits and has the final say on orders. **No model training on the critical path.** (Option B5 in §B.)

Why [O, from the evidence in §A–§G]:
1. Being flat at the end makes the page formula and the organisers' "completed trades' PnL" reading give the same number.
2. Under the freeze (F-117), an LLM that misbehaves can only remove exposure. It cannot add losses the code did not allow.
3. The literature re-check supports using an LLM on negative text evidence. It argues against letting an LLM judge price paths.
4. EDGAR is the only runtime text source that is clearly licensed, timestamped and loggable for the audit.
5. The critical path (adapter, logging, recovery, five-day soak) leaves no slack for a training track.

Largest unknowns: the bStock spread (never measured), trading hours outside the US session (`openState`), how the run is scored (Q-39), and whether an automatic restart is allowed during the run (Q-40).

## 1. What was read
- **Repo.** AGENTS.md; the handoff note; SKILL.md v0.7.4 in full; LEDGER.md; INCOMPLETE_WORK.md; `docs/official/source_page.md`; `docs/proposal/proposal_answers.md`; `docs/skill/larp/plan.md` in full; participant-kit.md K2, K6, K6a, K6b and K14–K18; Participant Guide pp.12–18 (pdftotext); IDEA-004..IDEA-008; EXP-001..EXP-004; literature.md; strategy-opinions.md; `tools/probe_kit_sources.py`; `tools/realised_vol.py`.
- **External, via subagents (2026-10-08):**
  - github.com/binance/binance-skills-hub at commit `9960c675387bd27f8866645b83693c1fa87242f6` (2026-09-11);
  - the papers in §2.1;
  - the terms pages in §C.2;
  - the company and agency calendars in §D.4.
- **Not reachable:** the DoraHacks page (HTTP 405 to automated fetches; the 2026-09-27/30 capture stands); nof1 primary pages; a live BscScan gas reading.

## 2. Re-check of the handoff note's claims
| Handoff item | Verdict | Evidence |
|---|---|---|
| §5.1 "a news/skill overlay is worth ≈ 0.09% of equity" | Arithmetic right for its inputs (4 trades × 18 USDT × 25 bp ÷ 200 USDT); the inputs are assumptions, and the average-edge framing misses where an exit overlay's value lies | §D.3: one avoided 5–10% gap on a 40 USDT position is worth 1–2% of equity before costs; whether such an exit is possible depends on `openState` outside the US session (Q-32) |
| §5.2 "no model trained on kit data can show an edge" | Holds for showing an edge (validation), not for training | Detecting 10 bp/day at σ = 2.5%/day needs n ≈ (1.96 + 0.84)² σ²/μ² ≈ 4,900 stock-days (two-sided 5%, 80% power, independent days) [E]. Kit data: ≈ 500 bStock token-days (5 names × 85–118 daily bars, K6a); ≈ 1,500 Ondo bar-days (4 × ~380, K6b) [V] |
| §5.3 literature claims | Supported, with corrections | §2.1 |
| §5.5 "C1 = the proposal's pre-registered default" | Not so | The proposal says "Otherwise the agent runs a pre-registered default and records that in its version manifest" and never defines the default [V: proposal_answers.md]. D-08 is undecided [V: plan.md]. C1 is a candidate for the default |
| §5.6 a menu "conflicts with the proposal ('schema forbids trade actions')" | Mis-sourced | "Its schema forbids trade actions" is in T-12, the team drafts as of 2026-09-28, not in the submitted text [V: plan.md T-12; proposal_answers.md]. The submitted text says "The LLM never signs, sizes or sets limits" and "a policy that maps the model's output to LONG, HOLD or EXIT", where "the model" is the calibrated decision model [V]. An LLM choosing from a menu does not breach "never signs, sizes or sets limits". Replacing the decision model is a deviation (§F) |
| §5.7 four Skills "of little use" | Desk read done; coverage still unknown | §C.1; probe pending [P] |
| §5.8 EDGAR as the runtime text source | Confirmed after comparing the alternatives | §C.2 |
| §5.9 distillation; Claude never a teacher | AUP point stands [R: IDEA-007 §1, re-fetched there 2026-10-08] | §E |
| §5.10 every fallback must be in v1.0 | Agreed | §G.2 |
| §5.11 "dedicated trading agent = statistical models + risk rules" | Dropped; no decision depends on it | — |
| §2.2 no declaration requested | Recorded as a team statement [T] | SKILL.md Q-33 |
| §4 BNB price and gas unchecked | BNB ≈ $769–771 (CoinGecko $768.88, CoinMarketCap $771.40, about 04:00 UTC). The BSC minimum gas price is still 0.05 gwei: no 2026 change found, but there is no live reading [V2] | https://www.coingecko.com/en/coins/bnb ; https://docs.bnbchain.org/announce/mendel-bsc/ |

### 2.1 Literature re-check [V2]
| Claim as used in the repo | Verdict | What the source says | Fair use for us |
|---|---|---|---|
| Martineau: PEAD gone since ~2006 except microcaps; 2016–19 coefficient −0.002 | Supported | "For large stocks, PEAD have been non-existent since 2006"; −0.002 is the BHAR[2,60] coefficient for all-but-microcap stocks (Table 3B). The day 0–1 reaction is still positive (0.012) | No drift left after day 1 in large caps. Gross of costs; sample ends 2019 |
| Lopez-Lira & Tang v6: Sharpe 6.54 → 1.22; stronger after negative news; small stocks; 20 bp kills the overnight strategy | Supported, except "concentrated in small stocks" | 6.54 is 2021Q4 only. "predictability is substantially stronger among smaller stocks", but "not limited to small stocks". "A transaction cost of 20 bps round-trip makes the strategy unprofitable" | All results are long-short and daily. A long-only agent can only use the negative-news side, by avoiding or exiting |
| Chen, Green, Gulen & Zhou (AEA 2026), "What Does ChatGPT Make of Historical Stock Returns?": LLMs over-extrapolate price history and are miscalibrated | Supported (Dec 2025 version) | Forecasts "overextrapolate trends", with confidence intervals "too narrow"; the biases "resist correction through prompt engineering" | Monthly horizon, GPT-4o. The arXiv v1 abstract says the opposite on calibration; cite the 2025 version |
| Ke, Kelly & Xiu: news is priced on day 0–1, ~4× stronger in small stocks | Mostly supported | Large stocks move ~11 bp on day 1 and finish within a day; small stocks ~5× more, over three days | Large caps finish fastest |
| Cong et al. 2026: 1% off-hours token move → +0.28% close-to-open | Supported (slides only) | t = 3.09, N = 23,931; Backed xStocks and Ondo tokens | Not bStocks. It predicts the underlying's open, not a tradable token gain |
| Chen & Velikov 8 bp/month; McLean & Pontiff −26% / −58% | Supported | 120 and 97 long-short anomalies | Not catalyst studies |
| Ai, Bansal & Guo: 10.68 vs 0.93 bp/day | Supported | Aggregate US market on macro announcement days | Favours being invested on macro days |

**Live and forward LLM-trading evidence [V2].**
- *LiveTradeBench* (2511.03628): the LLM sets long-only weights directly. Underperformance comes from "overreactive allocation changes".
- *StockBench* (2510.02209 v2): its abstract and §3.2 contradict each other on buy-and-hold. It reports schema and arithmetic errors. All agents underperform in the downturn.
- *Agent Market Arena* (2510.11695): the framework matters more than the backbone model. No agent beat TSLA buy-and-hold.
- *AlphaForgeBench* (2602.18481): runs disagree at temperature 0. Gemini-3-pro's pairwise action agreement is 0.36–0.48; Grok-4.1-fast disagreed on 88.4% of steps.
- None of these models fees.
- No controlled study of "LLM decides" vs "LLM informs a rule-based policy" was found.
- Alpha Arena results are from secondary sources only.

**So what [O].** The evidence supports bounding the LLM's authority, adding hysteresis, and using text, especially negative news, rather than price judgement. It does not show that an LLM veto adds value (IDEA-005 R4 still applies).

## A. Scoring: what each reading rewards, and a design robust to both
**Readings.**
- **R1, the page.** "Proposed FinalScore (%) = (Final Wallet Equity − Opening Wallet Equity) / Opening Wallet Equity × 100". Tie-break: "lower maximum drawdown". "Not scored: … number of trades". "The audit adds no points" [V: source_page.md].
- **R2, the organiser chat.** "completed trades' PnL, drawdown, logs, and code repo all together" (F-115). Two sub-readings:
  - **R2a:** only completed round trips count;
  - **R2b:** PnL is marked to market.
- **Status.** Neither reading is in issued rules (F-52, K18). The live page could not be re-checked on 2026-10-08.

| What moves the score | R1 | R2a | R2b |
|---|---|---|---|
| Exposure × market path | Yes, through end equity | Only on closed trades | Yes |
| Open positions at the end | Marked at the valuation source (Q-04) | Not counted (or unknown) | Counted |
| Drawdown | Tie-break only | Weighted (weight unknown) | Weighted |
| Logs and code repo | Audit only (pass/fail) | Scored (how is unknown) | Scored |
| Number of trades | "Not scored" | Zero trading penalised ("definitely not what this competition is about") | Same |
| Gas and fees | Reduce equity (F-44) | Reduce trade PnL | Same |

**Design robust to both [O].**
1. **Flat at the end.** Close every position before the end of the scored window. Then R2a's completed-trade PnL and R1's equity change are the same number, apart from BNB.
   - Cost: ≈ 0.06–0.47% of equity [E]: 4 positions × 25–40 USDT; one approve + swap at $0.017–0.035; spread 5–50 bp per side, unmeasured.
   - Timing: the window end is unknown (Q-06: "Oct 29 – Nov 12" vs "14 days"), and the earliest plausible end is Nov 12 00:00 UTC [A]. So be flat by the close of the Nov 11 US session (21:00 UTC under EST) unless Q-06 is answered first. That gives up at most one session of exposure.
2. **Little BNB.** Hold only the G-28 gas floor, because whether BNB counts as equity is unknown (Q-03).
3. **Moderate, pre-registered exposure.** Drawdown is weighted under R2 (§D).
4. **Readable logs every round.** Each round logs an LLM reasoning summary or a rule statement in `cot`, and the repo shows the harness. This matters only under R2 and costs little.
5. **No churn to manufacture round trips.** Trade count is "Not scored" under R1. Under R2a the end-of-run flatten completes every trade anyway.

Questions still worth sending (GAP-42, in the organisers' words, without our IDs): Q-39 scoring composition; Q-06 window timestamps; Q-32 trading hours; Q-40 automatic restart. The design does not wait for the answers.

## B. The LLM's role in the decision
Options, each in its strongest form:
- **B1 — proposal as submitted.** The LLM reads evidence only. A self-hosted calibrated decision model (P(UP/FLAT/DOWN)) feeds a deterministic policy. Strongest form: IDEA-008's fused model, or IDEA-007 Track A's severity/veto model.
- **B2 — full menu.** The LLM chooses LONG, HOLD or EXIT per name. Code sizes, caps and can veto.
- **B3 — kit pattern.** As in `strategy_agent.py`: an Anthropic tool loop with `place_order(side, symbol, amount)`; code enforces amount caps and the arming switch (K16).
- **B4 — rules with an LLM veto.** Rules decide. The LLM can only veto entries and trigger exits (IDEA-004 minimal tier).
- **B5 — recommended hybrid.** Rules propose a target book. Every round, the LLM decides per name from {CONFIRM, VETO_ENTRY, EXIT}. EXIT needs a verified claim (G-53) or a fired falsifier (G-51). VETO_ENTRY may rest on an unverified flag, matching the proposal's "If the core claim fails, the agent takes no new risk". With no new evidence since the last round, code forces CONFIRM. Code sizes and has the final say.

**Page wording** ("Build an LLM-powered Agentic AI system that gathers information, reasons, decides, manages its own risk"; "Rules and classical ML may support the system") [V]:
- B1: fits on paper, but the model cannot be validated in time (§E), so in practice it runs the default.
- B2: fits.
- B3: closest to the wording.
- B4: weakest, since rules decide.
- B5: the LLM makes each round's decision, with rules supplying the starting point.

**Kit reference and log format** (`orders` = "the orders your code finally decided to place this round (after risk checks and other adjustments; not necessarily what the model output)" [V: Guide p.13]; "The organizers use these logs to audit whether each on-chain transaction was decided autonomously by the agent" [V: Guide p.12]; rule-only demos put the rule statement in `cot`, F-106 (a)):
- All five options can be logged.
- B3 copies the reference agent.
- B4 has rounds with no LLM call, so `cot` holds the rule statement.
- B5 logs one LLM call per round.

**Audit and the F-117 freeze** (no patches during the run):
- B1: deterministic once the model is frozen.
- B2: the LLM can add risk.
- B3: the LLM sizes within the caps; a misbehaviour cannot be fixed.
- B4 and B5: the worst case is less exposure.

**Reliability:**
- B2 and B3 inherit run-to-run disagreement (AlphaForgeBench) and over-adjustment (LiveTradeBench), so expect churn.
- In B5, LLM noise matters only when new verified evidence arrives.
- B1 needs a model that does not exist.

**Cost:**
- Tokens are small in every option [E]: ~6 rounds/day × 14 days × 20–40k tokens ≈ 2–3.5M input tokens, a few USD at current list prices (check the chosen provider). Spend is not scored (F-50) and is ours (F-32).
- Trading costs are highest for B2 and B3 (turnover).

**Fit with the proposal:**
- B1: as declared.
- B2: replaces the calibrated model.
- B3: breaks "The LLM never signs, sizes or sets limits".
- B4 and B5: use the proposal's own fallback ("pre-registered default"), but change its character from "selective … abstains when the evidence or its confidence is not good enough" to invested by default. The reason is F-115 and must be recorded (§F).

**Buildable by Oct 19:**
- B1: no (training data on hold, IDEA-001 §11).
- B2, B4, B5: yes.
- B3: fastest to start (kit code), but needs the most safety work (K16 N1–N12).

**Recommendation: B5 [O].** It keeps the LLM as the per-round decider that the page and the kit describe, and keeps "never signs, sizes or sets limits". It bounds an unpatchable failure to lost exposure, and puts the LLM on the evidence type the literature supports. Its weakness: outside earnings the evidence loop will mostly CONFIRM (§C.3), so the LLM's visible role in the logs is modest. That is honest and should be described as such.

## C. Runtime data
### C.1 The four unprobed Skills — desk read of the Skills hub (commit `9960c67`) [V2]; probe pending [P]
| Skill | Endpoint the Skill calls | Filter by bStock contract? | History? | Per-item timestamps |
|---|---|---|---|---|
| trading-signal | POST `web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money/ai` `{chainId:"56", page, pageSize ≤ 100, smartSignalType}` | No; match `contractAddress` client-side | Paged list of recent signals; no time-range parameter | `signalTriggerTime`, `highestPriceTime` (ms) |
| crypto-market-rank | token-rank (POST, `rankType` 40 = "Stock"), smart-money inflow (POST), social-hype (GET), meme-rank, address-pnl-rank (GET) | No; token-rank `keywords` matches symbols | Snapshots over `period` windows | `launchTime`; address-pnl `dailyPNL[].dt` |
| query-address-info | GET `…/v3/…/address/pnl/active-position-list/ai?address&chainId&offset` (headers `clienttype: web`, `clientversion: 1.2.0`) | By wallet only | Snapshot | None |
| query-token-audit | POST `…/v1/public/wallet-direct/security/token/audit` `{binanceChainId:"56", contractAddress, requestId}` (header `source: agent`) | Yes | Snapshot ("Audit results are point-in-time snapshots") | None |

- **Text in the hub.** No news skill exists. The only text is crypto-market-rank's social-hype summaries and academy-skill's "Binance Announcement" search; academy-skill is not on the kit's list. Neither is equity news.
- **Reading [O].** None of the four gives usable history apart from signal trigger times. If any of them covers bStocks, it can only be live context, and its history would have to be logged by us from Oct 12. query-token-audit is a one-off sanity check.
- **Probe.** `tools/probe_kit_sources.py` gained section D on 2026-10-08. Run `python tools/probe_kit_sources.py --skills-only [--wallet 0x<public address>]` from the team network; it takes about 2 minutes, including a 60 s wait. It was tested only against mocked responses in the cloud and made no real calls. Record the results in participant-kit.md K6b.

### C.2 Text source for the evidence loop [V2 unless marked]
| Source | Automated use | Store and show auditors | Timestamps | Verdict |
|---|---|---|---|---|
| SEC EDGAR (submissions JSON, Archives) | Yes, with a declared User-Agent, ≤ 10 req/s (sec.gov "Accessing EDGAR Data") | "public information and may be copied or further distributed" (sec.gov/privacy) | `acceptanceDateTime` to the second. One 6-K checked: true UTC vs the index page's ET. Submissions API "typical processing delay of less than a second" | **Use.** Covers all five; SK hynix is CIK 2120882 (Nasdaq SKHY, files 6-K) |
| Issuer IR / newsrooms | NVIDIA: no "robot, spider, scraper"; Microsoft: "personal and non-commercial use"; SK hynix newsroom: no "robot, spider"; Alphabet: robots.txt allows (10 s delay); Tesla: terms not found | No for NVIDIA, Microsoft, SK hynix | RSS or none | **Exclude.** The releases reach EDGAR as 8-K / 6-K exhibits |
| Newswires | PR Newswire: no robots; Business Wire: no "store, aggregate"; GlobeNewswire: terms page 404 | No | — | Exclude |
| GDELT DOC 2.0 | "unlimited and unrestricted use … commercial", with citation | Its own metadata only; article text "if you have the necessary subscriptions or authorizations" | Every 15 min; `seendate` meaning unverified | Optional discovery flag (URL, title, time); may only block entries |
| Hosted LLM web search | Anthropic `web_search`: page text returned as `encrypted_content`, `cited_text` "Up to 150 characters", no date filter. OpenAI: URLs and titles. Gemini grounding: must not "cache … analyze … Grounded Results". DeepSeek: unclear | Not audit-grade (F-49 (c) asks for complete records) | `page_age` = "When the site was last updated" | Exclude. Anthropic `web_fetch` (full text plus `retrieved_at`) is acceptable only as a fetcher for EDGAR URLs |
| OpenDART | API key; Copyright Act and Public Data Act apply; contest use not addressed | Not stated | `rcept_dt` is date-only | Optional SK hynix cross-check |
| Binance Skills / feeds | No news skill (§C.1) | — | — | Not a text source |

- **Point-in-time.** Live use: each item carries `acceptanceDateTime` and our retrieval time, and G-05 rejects anything later than the decision time.
- **Rights.** IDEA-001 §11's kit-first rule covers training and validation data. EDGAR at runtime still needs a licence-register entry (GAP-23) and a line in the manifest's services list.

### C.3 How often the evidence loop will have something to read
Scheduled company events [V2]:
- Tesla reports Oct 21 (dev phase).
- Alphabet and Microsoft report Oct 28 after the close, during activation; Oct 28 is also the FOMC statement.
- SK hynix: not announced; estimated Oct 22–29 KST.
- NVIDIA: estimated Nov 17–18, after the run.

Inside the run [V2]: GDP/PCE Oct 29, NFP Nov 6, CPI Nov 10, and the US DST change on Nov 1 (the US open moves from 21:30 to 22:30 SGT).

Outside earnings, large caps file roughly 0–2 8-Ks in a two-week window [E, from memory; unchecked]. So most rounds will CONFIRM. Check by counting 8-K / 6-K filings for the five CIKs over Oct 29 – Nov 12, 2025, from the team network.

## D. Exposure level and trading frequency
### D.1 What the declared sizing gives (1% of equity ÷ (2 × daily σ × √5); caps 20% per name, 80% gross) [E]
Vols from `tools/realised_vol.py` (IDEA-007 §6), Ondo history; per-session σ = annual ÷ √252:

| Vol estimate | NVDA | GOOGL | TSLA | MSFT | Gross (4 US names) | At 200 USDT |
|---|---|---|---|---|---|---|
| Full history | σ 2.39% → 9.3% | 1.95% → 11.5% | 2.90% → 7.7% | 1.70% → 13.1% | 41.7% | ≈ 83 USDT |
| EWMA (20-bar half-life) | 1.64% → 13.7% | 1.51% → 14.8% | 2.27% → 9.9% | 1.45% → 15.4% | 53.7% | ≈ 107 USDT |

- SKHYB: σ ≈ 5–6% per session → 3.7–4.5% weight.
- The declared formula uses a trailing 60-session σ, which lies between the two rows.
- I-61's "≈ 36%" assumed 2.5% daily vol. Measured vols give 42–54%, i.e. positions of ≈ 15–31 USDT.

### D.2 Costs [E]
- **Gas** per approve + swap: 0.000022–0.000046 BNB (Guide p.5) × ≈ $770 = $0.017–0.035.
- Gas per leg in bp:

  | Trade size | Gas per leg |
  |---|---|
  | 10 USDT | 17–35 bp |
  | 18 USDT | 9–20 bp |
  | 25 USDT | 7–14 bp |
  | 40 USDT | 4–9 bp |

- **Spread and price impact: never measured.** The cross-venue close differences in K6b are not spreads.
- **Whole-run cost** ≈ N × (2 × gas + 2 × spread × size) ÷ equity:

  | Round trips × size | Spread 5 bp/side | 20 bp/side | 50 bp/side |
  |---|---|---|---|
  | 4 × 25 USDT | 0.12–0.19% | 0.27–0.34% | 0.57–0.64% |
  | 8 × 25 USDT | 0.24–0.38% | 0.54–0.68% | 1.14–1.28% |
  | 16 × 40 USDT | 0.59–0.89% | 1.55–1.85% | 3.47–3.77% |

- The "≈ 100 bp round trip" in IDEA-004 is the declared 50 bp cost cap plus a 50 bp buffer: a hurdle, not a measurement (IDEA-005 R9 is right).

### D.3 What this means [E/O]
- **Expected market gain over 10 sessions.** At gross 0.4 / 0.55 / 0.8: ≈ 0.17 / 0.23 / 0.33% of equity [A: 8%/yr premium, β ≈ 1.3].
- **Spread of outcomes.** The standard deviation of the 10-session result is ≈ 2.3 / 3.2 / 4.6% [A: ρ = 0.55, full-history vols].
- **Three consequences:**
  1. Rank is driven by exposure × market path.
  2. Each unnecessary round trip costs about as much as the whole expected premium.
  3. **The bStock spread is the most valuable number to measure now.**
- **Exit overlay.** Its value is dominated by rare large moves: one avoided −5% / −10% move on a 40 USDT position = 1.0 / 2.0% of equity before costs. That requires a verified adverse filing while `openState` is true and before the token reprices. If bStocks cannot be traded outside the US session (Q-32, GAP-44), after-hours filings can only be acted on at the next open, after the gap.

### D.4 Options
**Exposure:**
- **E1 — keep the declared formula** (≈ 42–54% gross). No declared value changes.
- **E2 — risk-constrained Kelly with a finite-horizon drawdown target** (IDEA-006; 0.4–0.6 in its synthetic illustration). A version event with a stated reason if the formula changes (G-11).
- **E3 — up to the 80% cap.** Needs a new sizing rule and a stated reason; the tournament argument is S-01, not for documents.
- **Recommended: E1 [O].** Mid-range risk, no declaration change, and its inputs are measured.

**Frequency** (expected round trips):
- F1 — buy at the start, flatten at the end: ≈ 4.
- F2 — F1 + no-trade-band rebalancing + evidence exits and re-entries: ≈ 4–8.
- F3 — scheduled weekly close and re-open: ≈ 8–12.
- F4 — LLM-driven trading: unbounded.
- **Recommended: F2 [O].** Minimum trade size so that gas is ≤ ~15 bp per leg (≥ ~25 USDT at the high gas figure) [E]. The band is set from the measured spread.

### D.5 What can be measured before Oct 26
Basis [V: Guide p.7 "Quotes are free and don't check balances"; K6 "a read-only address can get quotes"].

1. **Quote logger (cost probe).** No signing, no ai-seeds.
   - Coverage: five names × {buy USDT → token, sell token → USDT} × {10, 25, 40 USDT} every 15–30 min, with `userWalletAddress` = the dev wallet's public address.
   - Record `toTokenAmount`, `priceImpactPercent`, `minReceiveAmount`, `estimateGasFee`, the `openState` at the time, and the UTC time.
   - Round-trip spread = 1 − (sell proceeds ÷ buy cost) at equal size.
   - Can start **now**: it needs only the Web3 API key, which worked on 2026-10-07 (K6a).
   - Rate limits: check the Developer Portal quotas first (Q-38).
2. **`openState` logger.** `rwa/tokens` `statusInfo` hourly (GAP-44), across the weekends of Oct 10–11, 17–18 and 24–25.
3. **Realised gas, fills and reverts.** From the dev wallet's own test trades, once gas is solved (Q-03), around Oct 15.

**Audit trace of plain API calls.** The kit's audit chain is ai-seeds logs plus on-chain fills (Guide p.2, p.12), and quote calls produce neither. Binance can see the API key's traffic [A]. Never-do #13 concerns the ai-seeds credentials only.

## E. Model-layer work
| Option | Person-days | Score value | Fit with the page / audit | Risk under the freeze | Verdict [O] |
|---|---|---|---|---|---|
| E0 none: hosted LLM + rules, declared honestly | 0 | — | F-30 asks for innovation "at the model layer … and at the harness layer"; Stage 1 is over (F-40); the repo may be assessed under R2 [A] | Lowest | **Recommended for v1.0** |
| IDEA-007 Track A: EDGAR 8-K event / severity / veto classifier, open-weight or DeepSeek-API teacher (never Claude), human gold set | 5–6 [R: IDEA-007 §3] | ≈ 0 [R: IDEA-007] | Gives a real "domain fine-tuning / distillation" claim; deterministic at runtime | Low once frozen; must pass its kill criteria by Oct 17 | Optional, off the critical path, only if someone is free after the Oct 15 milestone; replaces only the item-code rules, not the LLM |
| IDEA-008 (Keith): news model + time-series model → trained decision model | Not estimated [R: IDEA-008 §7 R1] | Cannot be validated (§2, 5.2) | Strongest model-layer story; matches the proposal's "calibrated decision model" | High: three pipelines, out-of-fold fusion, sparse aligned events (R2); Wikinews has been read-only since May 2026 (archive still readable) [V2] | Not for v1.0. R1–R4 are still open and there is no dated plan |

Capacity: about 4 people × 4–5 effective person-days per week [A: ask the team]; the critical path is about 20–24 person-days [E, §G].

## F. Recording deviations from the proposal
- **No declaration form was requested** [T] (SKILL.md Q-33). So the record is:
  1. a **deviations register** in plan.md;
  2. a `deviations` block plus a **services list** in every version manifest (F-61: "Third-party services are declared in your manifest").
- **Each row records:** the declared text (quote), what v1.0 does, the reason with evidence IDs, the date, and the version that introduces it.
- **H-02 / EXP-001:** record "not run: training and evaluation data on hold (IDEA-001 §11, GAP-56); inconclusive by construction". The D-08 default then applies, as the proposal itself says.
- **D-08:** pre-register the base book (§H) as the default before Oct 19, which is plan.md's deadline for D-07/D-08.

| # | Declared (proposal_answers.md) | v1.0 (recommended) | Reason |
|---|---|---|---|
| 1 | "self-hosted calibrated decision model … fine-tune on our own point-in-time labels" | Not shipped; the pre-registered default (base book) runs | H-02 not runnable (IDEA-001 §11); IDEA-004/007 power arithmetic |
| 2 | "selective … abstains"; entry needs P(UP) and margin thresholds | Invested by default in the base book; the LLM can veto and exit | F-115 ("if you don't trade at all? That's definitely not what this competition is about") |
| 3 | "Licensed historical daily prices … vendor will be declared"; GDELT "second independent source"; FRED/ALFRED; issuer IR/RSS | Kit data + EDGAR; GDELT metadata optional; no FRED, no issuer IR scraping | IDEA-001 §11 and §13; IDEA-007 §1 (FRED terms); §C.2 (issuer terms) |
| 4 | Tools `fetch_filing_section`, `fetch_issuer_release`, `search_second_source`, feature lookup | EDGAR fetch / list tools; issuer-release tool dropped | §C.2; GAP-03 (≤ 3 tool types) |
| 5 | "Improvements are versioned releases, at most one a day" during the run | No releases during the run | F-117; G-46 |
| 6 | "registered safe-mode build"; "Humans can halt the agent" | Autonomous safe mode inside v1.0; no human action | F-114, F-117; Q-40 |
| 7 | "The order is ≤ 10% of the quoted depth" | Price-impact cap | No depth in the quote (I-68 (c), GAP-51) |
| 8 | "anchored hourly" write-once store | Team decision (keep or drop) | I-68 (d), GAP-35 |
| 9 | "quote/build/simulate", "order hash" | Quote → approve → re-quote → gas estimate → swap; nonce and tx hash | I-68 (a), (b) |
| 10 | "Small self-hosted finance sentiment/relevance model" for triage | Not shipped unless a model-layer track passes | §E |
| 11 | "full pipeline for 5+ days including a weekend, at minimum size" | Kept: Oct 19/20–26 incl. Oct 24–25 | GAP-04 |
| 12 | "one primary runtime plus a fenced cold standby" | Primary + automatic supervisor restart; standby per D-05 | Q-40; D-05 |
| 13 | Exits: confident DOWN signal, falsifier, risk limit | Falsifier, verified adverse evidence, risk limit, end-of-run flatten | No decision model; §A |
| 14 | Sizing, caps, drawdown halts (3%, 8%, 12% → 40%) | Unchanged (E1) | — |

## G. What four people can build and soak, Oct 9–29
### G.1 Schedule [O; dates are SGT]
| Dates | Agent/Model (Yao Zhu) | Markets/Data/Risk (Isaac) | Execution/Security (Keith) | Platform/Audit (Keegan) | Exit criterion |
|---|---|---|---|---|---|
| Oct 9–11 | §8 direction decisions; run the Skills probe | Start the quote and `openState` loggers | Begin the adapter port (quote-only) | ai-seeds logging contract (GAP-46); hosting choice | Direction decided Oct 11; loggers running |
| Oct 12–15 | EDGAR poller and fetch tools; LLM bake-off on ~20 recent 8-K / 6-Ks (D-03) | Base-book rules, risk governor, cost model from the logs | Approve → re-quote → swap, nonce reconciliation, signer allow-list; **first minimum-size buy and sell from versioned test-mode code by Oct 15** (needs Q-03) | Write-ahead journal, version gate and manifest, one log per round on every path (G-19) | Real round trip logged and reconciled |
| Oct 16–18 | Claim verifier, thesis memory with falsifiers, menu output and `cot` capture | Regime gate, end-of-run flatten, no-trade band | Gas top-up, UNRESOLVED handling, 120 s timeouts | Supervisor restart, heartbeat, spool monitor, daily reconciliation | Week-one checkpoint commit and progress note (Oct 18) |
| Oct 19–21 | Integration | Cost readout from the logger → band and minimum trade size | Fault injection (test matrix, plan.md §9) | Deploy to the run host; soak starts with the signer on at minimum size | Full pipeline live by Oct 20 |
| Oct 22 | **Cut line**: anything not green is cut (G.3) | | | | |
| Oct 23–26 | Soak including the Oct 24–25 weekend; recovery drills; deviations register and manifest | | | | Self-check evidence; v1.0 candidate frozen Oct 26 |
| Oct 27–29 | Fresh final wallet, its secret (Q-35), v1.0 manifest, integrity check; v1.0 starts and is never changed (F-117) | | | | v1.0 registered |

### G.2 Must be in v1.0 (failure blocks activation)
- G-01 signer allow-list; G-03 version gate; G-04 write-ahead record; G-18 at-most-once signing and reconciliation; G-19 one log per round;
- the `openState` gate (G-30); the gas floor and top-up (G-28); the risk governor and drawdown halts (G-22);
- the end-of-run flatten (§A); degraded mode (G-27); automatic supervisor restart of the same version (Q-40 assumption);
- spool and delivery monitoring (F-109); DST-safe scheduling (UTC internally; Nov 1).

### G.3 Cut order if behind [O]
1. GDELT flag.
2. Thesis post-mortems.
3. Social and rank context from the Skills.
4. LLM menu → B4 (rules with an LLM veto only; the LLM runs only when new evidence arrives).
5. Evidence loop entirely → base book + risk rules only, recorded as a deviation.

Never cut anything in G.2.

## H. Recommended v1.0 direction (⚠ RECOMMENDED — NOT DECIDED)
**Base book** (the pre-registered default; D-08). Parameters in [brackets] are frozen by Oct 22 from logged data, never from P&L.
- **Universe:** the 4 names with the lowest trailing σ; this excludes SKHYB today.
- **Sizing:** declared weights, inside the caps (≤ 4 positions, ≤ 20% per name, ≤ 80% gross).
- **Regime multiplier:** 1.0 normally, [0.5] when the basket's 5-session realised vol is > [2]× its 60-session vol, [0] in stress (I-66).
- **Schedule:** decision rounds at [US open + 30 min] and [close − 60 min] on US sessions, plus event-triggered rounds (new EDGAR filing for a held or candidate name).
- **Trading:** only if |current − target| > [band] and the trade is ≥ [25] USDT. Build the book on the first session of the run.
- **Re-entry:** after an LLM EXIT, the name re-enters at the next scheduled round, unless the triggering evidence is still current or a falsifier is still firing.
- **End of run:** flat by the close of the Nov 11 US session unless Q-06 says otherwise.

**LLM** (D-03 picks the model via the bake-off):
- **Input:** one call per round with positions, base-book targets, the regime, measured costs, new EDGAR items (full text, `acceptanceDateTime`, retrieval time) and thesis memory.
- **Output:** a schema-checked menu choice per name, with cited evidence IDs.
- **Verification and limits:** claims are checked by G-53. Code applies EXIT only with a verified claim or a fired falsifier, applies VETO_ENTRY freely, and forces CONFIRM when there is no new evidence. Schema failure → CONFIRM held positions and no new entries.
- **Thesis object per holding:** catalyst = "base-book holding"; falsifiers = verified adverse classes:
  - 8-K items 4.02, 2.06, unplanned 5.02, 1.05;
  - a guidance cut in 2.02 / 7.01;
  - the regime turning to stress;
  - G-22 drawdown triggers.

  The list is fixed by Oct 22.
- **Logging:** `input` = the full model request; `cot` = the provider's reasoning summary; `output` = the menu choice; `orders` = what code decided.

## 8. Decisions for the team
Owners follow the proposal's roles. Named individual assignment is still GAP-37; SYZ to confirm.

| # | Decision | Owner | Deadline (SGT) | Input |
|---|---|---|---|---|
| 1 | Direction: LLM role (B1–B5), base book as the D-08 default, EDGAR as the runtime source | SYZ, with all four | Sun Oct 11, 23:00 | §B, §C, §H |
| 2 | Model-layer track: none / Track A / IDEA-008 (GAP-57) | SYZ with Keith | Sun Oct 11, 23:00; Track A ship-or-kill Oct 17 | §E |
| 3 | Send the remaining organiser questions (Q-39, Q-06, Q-32, Q-40; Q-04, Q-35) | SYZ (Telegram) | Fri Oct 9 | §A |
| 4 | Start the quote logger and the `openState` logger (GAP-44, GAP-50) | Isaac | Fri Oct 9 (readout Oct 19) | §D.5 |
| 5 | Run the extended Skills probe; record the results in K6b | SYZ | Sat Oct 10 | §C.1 |
| 6 | Run host for 14 unattended days; supervisor restart (D-05, Q-40) | Keegan | Wed Oct 14 | §G |
| 7 | Evidence LLM and snapshot (D-03) from the bake-off | Yao Zhu | Thu Oct 15 | §B |
| 8 | Pre-register D-08 (base-book spec v0) and record H-02 as not run | Isaac + Yao Zhu | Mon Oct 19 | §F, §H |
| 9 | Exposure level (E1–E3) and cadence parameters (band, minimum trade size, rounds per day) | Isaac proposes, team decides | Mon Oct 19 (frozen Oct 22) | §D |
| 10 | End-of-run policy (G-24, D-04) | Isaac | Thu Oct 22 (or when Q-06 is answered) | §A |
| 11 | Deviations register and manifest services list | Keegan | Draft Oct 19; final Mon Oct 26 | §F |
| 12 | Confirm individual owners and backups (GAP-37) | SYZ | Sun Oct 11 | — |

## 9. Updates this entry implies
**Applied in the same change as this entry:**
- SKILL.md: Q-33 (team statement: no declaration or repo-registration form requested); Q-40 (assumptions behind F-117); §0.4 priority by deadline; change log.
- INCOMPLETE_WORK.md: the Oct 10 heading and the GAP-41/53/56/57 deadlines re-dated to §8.
- plan.md: D-03, D-09 and D-10 headings re-dated (no declaration requested).
- LEDGER.md: this row, a "Direction for v1.0" thread, and the thread deadlines moved from Oct 10 to Oct 11.
- `tools/probe_kit_sources.py`: section D and `--skills-only` / `--wallet` (§C.1).

**Applied as pointers only (SYZ's choice, 2026-10-08):** one-line notes marked ⚠ RECOMMENDED — NOT DECIDED on plan.md D-03, D-04, D-05, D-08, G-24, §9 and "Funding implications"; new stub items D-11 and D-12; an empty plan.md §6.5 deviations register; SKILL.md Q-32 and Q-39; INCOMPLETE_WORK GAP-03, GAP-44, GAP-50, GAP-53, GAP-54; new GAP-61 (Skills probe) and GAP-62 (deviations register); the K6b desk read; a dated IDEA-008 note. Nothing was rewritten.

**Full text to write once the team decides (Oct 11):**
- **plan.md:**
  - D-03: bake-off scope and EDGAR tools;
  - D-05: unattended host and supervisor;
  - D-08: the old ladder ("run V1 at half the risk budget") assumes a V1 that will not exist; replace it with §H;
  - new **D-11** (LLM role) and **D-12** (exposure, cadence, end of run);
  - G-24: flat by Nov 11 close unless Q-06 is answered;
  - §9 rows Oct 12–29 per §G;
  - "Funding implications": measured vols, BNB ≈ $770;
  - new section "Deviations from the submitted proposal" (§F table).
- **SKILL.md:** Q-39 (point to §A's robust design); Q-32 (raise in rank: decides the exit overlay's value, §D.3).
- **INCOMPLETE_WORK.md:**
  - GAP-44 and GAP-50 (start now; needs only the Web3 API key);
  - new items for the Skills probe (§C.1) and the deviations register (§F);
  - GAP-03 (tool list per §F row 4);
  - GAP-53 and GAP-54 (IDEA-004's C1 now enters as the D-08 default; R1–R4 evaluation is replaced by "not runnable before the run; report as such").
- **participant-kit.md K6b:** add the §C.1 desk read, labelled as not probed.
- **IDEA-008:** note that Wikinews has been read-only since May 2026.

## 10. Updates
- 2026-10-08 (SYZ): SEC EDGAR recorded as usable (IDEA-001 §15), settling the EDGAR part of §8 decision 1; the LLM-role and base-book parts are still open. Test pipeline `tools/edgar_fetch.py` added for the §C.3 filing count and the D-03 bake-off.
- 2026-10-08 (SYZ runs; results recorded by Claude): **Skills probe** (participant-kit.md K6b): only crypto-market-rank's token-rank (all five) and social-hype (TSLAB, NVDAB, MSFTB) cover our names, as live snapshots; trading-signal, smart-money inflow, address-pnl-rank and token-audit do not. One `ondoStatusInfo.openState: true` reading for NVDAB at 00:51 ET hints at trading outside US regular hours (Q-32; GAP-44 decides). **EDGAR** (IDEA-001 §15): in last year's run window (Oct 29 – Nov 12, 2025) the five issuers filed 4 8-Ks, two of them earnings that this year fall on Oct 28, before the run; this supports §C.3's estimate that the evidence loop will mostly CONFIRM.

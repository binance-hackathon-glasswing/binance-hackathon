# IDEA-004 — Literature-grounded method v2: what to test when the edge is too small to detect, and "well captured" v2

- Date / author: 2026-10-06 / SYZ (requested); literature review (3 subagents), second red team of IDEA-003 (1 subagent) and a final red team of this draft (1 subagent), merged by Claude
- Status: open — **⚠ RECOMMENDED — NOT DECIDED.** Supersedes IDEA-003 where they conflict (§6 lists the corrections to IDEA-003).
- What: (1) what to do when the planned final test cannot detect a realistic edge; (2) what the literature says the model should target; (3) method v2 (book structure, rows, labels, decision rule, block map, primary metric); (4) "well captured" v2: correctness tests, informativeness diagnostics and anti-overfitting rules; (5) what the pivot means for our declarations.
- Why it might help: aligns the build with effects that survived publication and costs, gives a test that can say something, and keeps the dataset checks from becoming a tuning loop.
- Cost / risk: minimal set 8–10 person-days [E] and blocked on D-09 (price vendor); it competes with the Oct 12–18 adapter work (F-13). Main risks: keeping catalyst drift as the return engine against the evidence; changing behaviour without a version event (I-35, G-11).
- Links: H-01, H-02, H-03, D-02, D-03, D-06..D-10, I-35, I-37, I-61, I-63, I-66, I-67, G-11, G-21, G-24, G-25, G-46, F-02, F-12, F-40, F-42, F-45, F-48, IDEA-001, IDEA-002, IDEA-003, EXP-001, EXP-002, GAP-44, GAP-50, GAP-53

Tags: [E] = reviewer estimate. Sources fetched 2026-10-06; none blocked except one arXiv HTML page (HTTP 429), which is not cited.

## 1. Why the test cannot detect the edge, and what helps
- **The binding term is time, not names.** With weekly common shocks, Var ≈ σc²/W + σi²/N (W weeks, N cases). More names only shrink the second term: 9-month block, relative labels, MDE 79 bp → 68 bp at 2× names, 62 bp at 4×, 55 bp at infinitely many [E]. A broader universe also adds domain shift: news, LLM and lead-lag edges concentrate in small, less-covered firms (Lopez-Lira & Tang, https://arxiv.org/abs/2304.07619; Hou 2007, https://ideas.repec.org/a/oup/rfinst/v20y2007i4p1113-1138.html; Menzly & Ozbas 2010, https://ideas.repec.org/a/bla/jfinan/v65y2010i4p1555-1580.html). **Verdict:** do not broaden the *test* universe; use related firms as features and event sources for the five (e.g. TSM monthly revenue for NVDA; MU and Samsung for SK Hynix), knowing post-publication customer momentum is insignificant (https://arxiv.org/abs/2301.11394).
- **What helps** [E for every MDE]:
  1. **More weeks.** Freeze one configuration on the pilot block and make the whole 2020-01 → 2026-09 walk-forward (yearly refits) the confirmatory test (Arnott, Harvey & Markowitz 2019, https://papers.ssrn.com/abstract=3275654). On a 44-name panel (4 US eligible + ~40 neighbours) the IC MDE is ≈ 0.023–0.032; on the 4 eligible names alone ≈ 0.17–0.24.
  2. **Use all rows, not the traded tail,** and vol-standardised, market-residualised targets (control variates, CUPED: https://exp-platform.com/cuped/; ×1.4–2.7 effective n).
  3. **Decide with a fixed rule, not a significance gate** (§3). Literature prior for information: post-publication anomalies earn ≈ 8 bp *per month* long-short net of costs (Chen & Velikov, https://www.federalreserve.gov/econres/feds/zeroing-in-on-the-expected-returns-of-anomalies.htm), i.e. ≈ 2 bp per 5 days; out-of-sample returns fall 26% and post-publication 58% (McLean & Pontiff 2016, https://counterpointfunds.com/wp-content/uploads/2017/07/PredictabilityMcleanPontiff.pdf).
  4. **Sequential tests (e-values, https://arxiv.org/abs/2210.01948) only as kill switches** on calibration, cost and basis during shadow and live runs.
- **The overlay barely moves the score anyway:** ~4 trades × 18 USDT × 25 bp ≈ 0.09% of equity [E]; the score is mostly exposure × market path.

## 2. What the literature says to target (1–10 days, US large caps, post-2010)
| Effect | Status in large caps, recent | Size vs our round trip (~100 bp incl. 22–39 bp gas on 18 USDT) | Use here |
|---|---|---|---|
| Post-earnings drift | Gone since ~2006 for all but microcaps; 2016–19 coefficient −0.002 (Martineau, "Rest in Peace PEAD", https://cfr.ivo-welch.org/forthcoming/papers/martineau2021rest.pdf) | ≤ 0 | No |
| Earnings-announcement premium | US value-weighted 8.7 bp (n.s.) in 2005–16 (https://www.iimb.ac.in/ARC2020/Papers/The_Disappearing_Earnings_Announcement_Premium.pdf) | ≈ 0 | No |
| Pre-FOMC drift | 49 bp (1994–2011) → ~9 bp (2016–19) (Kurov, Wolfe & Gilbert) | ≤ 10 bp | No; FOMC is Oct 28, before the run |
| Macro-announcement-day premium | 10.68 vs 0.93 bp/day, 1961–2023, includes FOMC days (Ai, Bansal & Guo, https://www.nber.org/system/files/working_papers/w31923/w31923.pdf); a beta premium | ≈ 20 bp of equity over ~4 run days at ~38% gross [E] | Stay invested on CPI/NFP days; value is small |
| Analyst-revision drift | Gone after 2003 (Altinkilic, Hansen & Ye 2016) | ≈ 0 | No |
| News text / LLM scores | Mostly day 0–1, ~4× stronger in small stocks (Ke, Kelly & Xiu, https://www.nber.org/papers/w26186); LLM long-short Sharpe decayed 6.54 → 1.22 by Jan–May 2024, strongest after negative news (Lopez-Lira & Tang v6, https://arxiv.org/html/2304.07619v6) | ≈ 0 long-only after costs in large caps [E] | Negative-news veto/exit only |
| LLM reading price history | Over-extrapolates, miscalibrated (AEA 2026, https://www.aeaweb.org/conference/2026/program/paper/zNrQ4Yn6) | negative | The LLM never judges direction |
| Short-term reversal | ~0 in low VIX, ~10 bp/day in high VIX (Nagel 2012) | small | Feature: don't chase moves |
| Short-term momentum (high turnover) | 500 largest: 0.42%/month (Medhat & Schmeling) | ~0.2% / 2 weeks gross [E] | Weak tilt at most |
| Volatility-managed exposure | Real time, 45 of 103 strategies beat unmanaged (Cederburg et al. 2020, https://www.lehigh.edu/~xuy219/research/COWY.pdf) | drawdown control, not return | Risk cap (I-61) |
| Tokenised-stock off-hours moves | Top-100 xStocks/Ondo tokens, Jul 2025 – May 2026 (no bStocks): a 1% off-hours token move predicts +0.28% in the *stock's* close-to-open (pooled, t = 3.09); overnight token moves reverse ("noise"), weekend moves show "genuine anticipation" (Cong, Landsman, Rabetti, Zhang & Zhao 2026, slide deck: https://www.suomenpankki.fi/globalassets/bof/fi/ajankohtaista/tapahtumat/kalenteri/rabetti_sra2026.pdf) | Predicts the stock, not the token return a long-only trader earns; no exploitable size shown | H-01 stays a hypothesis; test on bStock candles only (~17 weekends since June → expect inconclusive) |

**Implication.** The literature does not support "catalyst → 5-session drift" as the return engine for these names: a catalyst read 15 min after acceptance with next-open entry has missed the reaction, and what remains is far below a ~100 bp hurdle. This is a literature prior, not our result: H-02 is still run and reported (expected null). The catalyst pipeline stays for **risk, abstention and exits** (negative-news veto, scheduled-event flags) and for the audit trail.

## 3. Method v2
- **Book structure.** Base book **C1** = the proposal's pre-registered default, made concrete: regime-gated (I-66), vol-scaled (I-61) long exposure to the **four US names** (≤ 4 positions, G-21; SKHYB not held by C1 and handled by the risk governor only). Overlay = deviations from C1 only:
  - **Veto** a C1 entry (no trading cost) iff E[ẑ] < 0, or the fixed-rule negative-news veto fires (H-02 V2; LLM evidence + verification; no fitting).
  - **Exit/reduce** a held name iff E[ẑ]·σ₅ < −(c_exit + c_re-entry), or a falsifier or risk rule fires.
  - No overlay-driven entries beyond C1.
  - **Minimal tier (ship by default):** C1 + fixed-rule veto + risk exits; fitted-overlay budget 0. **Full tier:** add the fitted E[ẑ] veto/exit rule if the §3 primary metric passes.
- **Rows.** Price-only name × session panel (5 offset sub-panels, or uniqueness weights ≈ 1/5) for the 4 US names + ~40 neighbours (top tech/semis by size; hand list); event rows remain the H-02 unit. The LLM never touches panel rows.
- **Labels.** Store r_abs, r_rel (r − β̂·r_SPY, β from 250 pre-t sessions), sector-relative, r_gap, r₁/r₃/r₅/r₁₀, MAE. Target z = r_rel / σ₅ (σ₅ known at t).
- **Features.** Per-date rank-normalised to [−1, 1] with missing flags (Gu, Kelly & Xiu 2020, https://www.nber.org/papers/w25398); no price levels; SPY/QQQ/SMH context, VIX (FRED VIXCLS), macro calendar dates, own and peer event recency.
- **Model.** One pre-declared configuration: equal-weight ridge + shallow GBM (depth ≤ 4, large minimum leaf, literature-default hyperparameters, early stopping on purged folds), h = 5, fixed on the pilot block. Deep models' edge largely vanishes outside microcaps (Avramov, Cheng & Metzker 2023, https://papers.ssrn.com/abstract=3450322).
- **Block map** (replaces IDEA-001 §8's blocks and IDEA-003 RT-21/RT-24):

| Block | Period | Use |
|---|---|---|
| Pilot | 2018-01 → 2019-12 | Every outcome-based choice (event-type list, horizon check, configuration). Training only, never evaluation |
| Confirmatory walk-forward | 2020-01 → 2026-09 | Frozen configuration, yearly refits, h-session purge at every refit boundary. Opened once, after the manifest is committed and pushed. 2025-01 → 2026-09 reported as a separate slice |
| Post-LLM-cutoff events | cutoff → 2026-09 | Fixed-rule veto, descriptive only |
| Shadow / live | Oct 19 → Nov 12 | Kill switches only (e-values on calibration, cost, basis); no tuning (G-46) |

  Leak note: the team lived through 2025–26 (DeepSeek drop, Apr 2025 tariffs). Record which I-66 regime parameters were fixed before any 2025 data was looked at; C1's rules are designed on pre-2025 episodes only.
- **Primary metric (= the decision quantity).** Per-name, non-demeaned slope of realised z_rel on ẑ over the 44-name panel, week-clustered (2-week block bootstrap), 2020-01 → 2026-09. **Rule:** the full tier ships iff the point estimate > 0; otherwise the minimal tier. Prior mean fixed at 0, so no separate Bayesian step is needed (posterior mean > 0 ⇔ estimate > 0 under linear loss). Report n_eff and MDE. "t ≥ 3" applies only to claims of an edge written in documents, not to shipping.
- **Reported, not decision-making:** week-demeaned rank IC (diagnostic D3); after-cost overlay − C1 P&L on the 4 US names; C1 vs C0 (cash) vs buy-and-hold on 2025–26.
- **Dropped:** PBO and deflated Sharpe (with one configuration they add nothing; CSCV also ignores time order), the ±10 pp top-bin reliability gate (unresolvable at n_eff ≈ 30 and undefined for a z-regression), forced top-k% coverage.
- **Exposure level is a separate team decision.** Scoring is top 3 of < 25 finalists by % return, tie-break on lower max drawdown (F-02, F-04, F-45). C1 at ≈ 38% gross on the same names most teams hold is near the field's consensus, so the exposure level (within declared limits) matters far more than the overlay.

## 4. "Well captured" v2
Principle: **correctness tests** are hard pass/fail and never computed from returns; **informativeness diagnostics** are reported against a literature benchmark or a placebo and are never tuned. This replaces IDEA-003's M1–M7.

### 4.1 Correctness tests (all pass before the confirmatory block opens)
| # | Test | Pass condition |
|---|---|---|
| T1 | Timestamp order | source_ts ≤ t < entry_ts < label_end on 100% of rows; features ≤ t. Unit tests on one EDT and one EST 8-K comparing the submissions JSON `acceptanceDateTime` with the index page's "Accepted" time (settles whether the `Z` is real UTC), plus a half-day case; expected values generated with tz tooling |
| T2 | Session calendar | Entries and label ends on valid sessions per `exchange_calendars`; early closes handled |
| T3 | Corporate actions | Every |r₁d| > 40% matches a known action or is reviewed; NVDA 4:1 (2021), 10:1 (2024), TSLA 5:1 (2020), 3:1 (2022), GOOGL 20:1 (2022) reproduce |
| T4 | Price integrity | No duplicate (name, session); a random 1% sample matches a second source **on the licence register** within that source's documented rounding; join match rate reported for active and dead CIKs (survivorship documented + sensitivity run if delisted coverage is missing) |
| T5 | Filing hygiene | Accession dedupe; 8-K/A as own events; merged rows only include items with source_ts ≤ t; XBRL facts as filed before t (no `frames`) |
| T6 | Extractor parity | One code path pre-cutoff, post-cutoff and live; every extracted value cites a verbatim span; missing rate reported by block, and a dev-vs-live difference outside its sampling CI is a failure (by-design missingness flagged and exempt) |
| T7 | Leak canaries | Labels permuted within dates → IC within its null CI; a planted future feature is caught; a date/row-ID-only model shows no skill; if lagging features one extra session changes IC by > 2 SE in either direction, run a T1 timing audit (only a T1 finding may change data) |
| T8 | Reproducibility | Deterministic rebuild gives identical hashes; a 30-row hand-checked golden set matches |
| T9 | Basis (per name, live gate) | Daily close-aligned token vs share since 2026-06 (~80 obs): CI upper bound of mean |premium| at decision times ≤ measured one-way quote cost. A failing name is risk-governor-only |
| T10 | Cost model | c(size) vs logged Web3 quotes (from Oct 12), by size, `openState` and time of day; the c used in the decision rule lies within the quotes' CI |

### 4.2 Informativeness diagnostics (reported with CIs; never a reason to rebuild after the pilot)
| # | Diagnostic | Benchmark / null |
|---|---|---|
| D1 | Move recall **lift over placebo**: share of large |z| moves preceded by a dataset signal vs the same signals shifted ±20 sessions at random; plus precision | Placebo (raw recall is ≈ 0.69 by chance [E]: macro dates alone cover ~47% of 2-session windows) |
| D2 | News-day vs non-news-day contrast: variance ratio per event type (day 0/1 and entry → t + 5) and market-model R² | Median variance ratio ≈ 2.2; R² ≈ 16% news days vs ≈ 33% no-news days (Boudoukh et al., https://www.nber.org/papers/w18725) |
| D3 | Week-demeaned rank IC, its decay at h = 1/3/5/10, and its sign by year and regime cell (distinct weeks) | IC 0.05–0.10 is "stellar"; 5-day IC > 0.10 or OOS R² > ~1% in large caps → hunt for a leak first [E]; expect a 26–58% drop from in-sample (McLean & Pontiff) |
| D4 | Breadth and turnover: independent bets per week; turnover × measured cost | Gas ≈ 11–19 bp per 18-USDT trade each way |
| D5 | Covariate drift: adversarial AUC vs a permutation null; top drifting features | Flags normalisation needs; no gate |

### 4.3 Rules that stop the checks being overfitted
1. Freeze and hash every definition, threshold and the one configuration before the confirmatory block opens.
2. Outcome-based choices happen on the pilot block only.
3. Only correctness failures may change the dataset, and the justification may never cite returns.
4. Every rebuild evaluated against diagnostics is a logged trial (at most 2); none after the confirmatory block opens.
5. Gate only where the available n can resolve pass vs fail; otherwise report.
6. Keep the set small: 10 tests, 5 diagnostics, 1 primary metric.
7. Checks are two-sided: "too good" fails until explained.
8. Thresholds are derived (from measured cost, source documentation, sampling CIs) or come from the literature or a placebo; no invented pass lines.

## 5. Declarations and framing (the pivot)
- **Scoring cost: none.** "Agentic depth" was a Stage 1 criterion (F-40) and we were selected on Oct 2; Stage 2 is pure % return (F-42); Stage 3 is a pass/fail audit. **The real risk is the audit:** misrepresentation or false declarations (F-48, F-66) and the "spirit of selection" point (I-35).
- **Conflicts with what we declared, to fix through declarations and version events:**
  1. Entry rule: the declared entry needs P(UP)/margin thresholds and validation-beating cases; C1 entries meet neither → a version event changing the entry rule before the v1.0 freeze (G-11).
  2. Position cap: C1 holds the four US names only (≤ 4 positions); raising the cap would be a loosening.
  3. Principal model: the onboarding declaration (F-12, Oct 5–10) is open now: declare what will actually run (ridge/GBM ensemble + hosted LLM evidence step), not a fine-tuned encoder.
  4. Exposure: declared sizing caps C1 at ≈ 38% gross; any tournament-driven raise is a declared-limit change.
- **Honest framing:** the proposal already says "The evidence-assisted model trades only if it passes on held-out data. Otherwise the agent runs a pre-registered default and records that in its version manifest" (proposal_answers.md). Present C1 as that default, fixed before the test is opened. The agentic loop (evidence, verification, thesis memory, falsifiers) now governs abstention, vetoes and exits, which the proposal already stressed. Do not write "catalyst drift is zero for our names"; write that the literature prior is near zero and our H-02 test is reported as run.

## 6. Corrections to IDEA-003 (append-only; IDEA-003 is not edited)
- Citation: the 49.6% overnight / 12.4% intraday figures are from Boudoukh, Feldman, Kogan & Richardson, RFS 32(3) 2019, not NBER w18725.
- RT-06: the NVDA example (2026-09-18, EDT) is consistent, but the JSON `Z` semantics are unverified for an EST filing (T1 tests both).
- RT-15: arithmetic correct, but vol alone cannot push P(UP) above 0.5; the bias bites under top-k coverage. With fat tails the |z| ≥ 0.5 split is ≈ 26/48/26.
- RT-21: replaced by the fixed-rule veto (halving the post-cutoff window pushes the paired MDE to ~80 bp).
- RT-22: the paired MDE ≈ 56 bp assumed ~50% overlap of selected cases; at a 4% idiosyncratic sd the MDEs are 122/69 bp.
- RT-24: its window overlapped the calibration and threshold blocks; replaced by the §3 block map. A 20-questions-per-month cutoff probe has 25–42% power and understates the cutoff; prefer an LLM with an older documented cutoff, or no fitted V1.
- RT-25: realistic noise ≈ 1.1% at ~18% average gross; C1 over 2018–2026 is not possible for SKHY.
- RT-26: expected best-of-216 null z ≈ 2.8 (simulated), not 3.3; forced top-k% coverage withdrawn.
- RT-28: the β band [0.9, 1.1] is narrower than its CI at ~18 windows; T9 uses daily close-aligned data.
- RT-29: the top-bin check cannot be measured before the run (labels resolve ~Oct 26).
- Effort: the full IDEA-003 set is 2–3 person-weeks, not 1–2 days.
- M1–M7 replaced by §4.

## 7. Feasibility and cut order
- Minimal tier: 8–10 person-days [E], starting only once D-09 is chosen.
- Cut first: (1) the ~40-name neighbour panel and any fitted overlay (ship the minimal tier); (2) the GBM (ridge only); (3) full T3/T4 automation (keep the split cases).
- Never cut: T1/T2, T10 (cost from measured quotes), T9 basis, the C1 historical check (pre-2025 design, reported on 2025–26), the hashed manifest.

## 8. Decisions needed (feed GAP-53)
1. Adopt C1 + overlay/veto with minimal and full tiers; stop treating catalyst drift as the return engine (D-02 scope note, D-08).
2. Adopt the §3 labels, decision rule, block map and primary metric (D-06, EXP-001 / H-02, IDEA-001 §8).
3. Adopt "well captured" v2 (§4) in place of IDEA-003 M1–M7.
4. Onboarding declarations now: actual model stack; C1 as the default with ≤ 4 positions; plan the entry-rule version event (§5).
5. Exposure level within declared limits, given tournament scoring (team strategy call).
6. H-01/EXP-002: keep as a hypothesis on bStock data; GAP-44 still decides whether off-hours orders are possible.

## 9. Independent review (append-only)

- 2026-10-06 (Codex, requested by Keith): [IDEA-005](IDEA-005.md) independently reviews this proposal and its research. [EXP-004](EXP-004.md), pre-registered and pushed before execution, refutes the sufficiency of §3's positive-slope gate with deterministic counterexamples: slope +1 can accompany harmful vetoes; pooled +0.818182 can hide eligible-name slope −1. These are analytical examples, not market-performance results. Resolve IDEA-005 R1–R9 / GAP-54 before adoption; all original recommendations remain undecided.
- 2026-10-06 response from the author (SYZ, drafted with Claude) to IDEA-005 and EXP-004:
  - **Accepted:** R1–R9. In particular the §3 slope gate is withdrawn as a shipping rule (R1, EXP-004 A); the veto rule acted on the residual alone and ignored beta (R3); the default news veto had not been evaluated (R4); eligible-name performance needs its own comparison, with "inconclusive → declared default" if underpowered (R2); "scoring cost: none" is withdrawn (R8, and now contradicted by F-115).
  - **New organiser information (SKILL.md §1.10, F-113..F-116) changes the pivot:**
    - Scoring per the organisers looks at "completed trades' PnL, drawdown, logs, and code repo all together", and not trading "is definitely not what this competition is about" (F-115; open details in Q-39). A passive buy-once C1 that rarely completes a trade is therefore a poor default, and log and repo quality count.
    - "Once the competition starts, no changes allowed — period" (F-114): every safety action must be autonomous (Q-40).
  - **What survives:** do not rely on catalyst drift for returns; keep the hygiene work (§4 T1–T10). **What changes:** C1 must become a rule-based *trading* book with completed round trips on a fixed, pre-registered cadence, with drawdown as an objective rather than a tie-break; the catalyst/evidence loop gates entries and exits, each evaluated as its own variant (R4). Recommended, not decided; to be specified under GAP-53/GAP-54 once Q-39 is answered.
- 2026-10-08 note (SYZ, drafted with Claude): §3's "VIX (FRED VIXCLS)" feature is withdrawn: FRED's terms prohibit ML use and VIX is CBOE data. Use realised volatility from kit data instead (`tools/realised_vol.py`; [IDEA-007](IDEA-007.md) §6).

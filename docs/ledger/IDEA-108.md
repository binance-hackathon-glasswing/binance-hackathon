# IDEA-108 — S8 (EXPERIMENTAL, DO NOT DEPLOY): an earnings-calendar build tilt (announcement premium) inside FS1's book

> **Docs-only merge (2026-10-27).** This record was merged into canonical without its code at the user's request. The simulator, tests and any config it names are still in [PR 302](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/302) (`tools/idea108/`, `tests/strategy/test_idea108_backtest.py`; it builds on PRs 301 and 299), which is not merged; commit SHAs cited below are on that PR's branch.

> ## DO NOT DEPLOY
>
> S8 is an **experimental research design**. It is not FS1, not a candidate for the scored run, and not approved for
> anything except the offline backtest pre-registered below. It **must not** be installed, activated, used to build a
> FINAL or REHEARSAL `StrategyProfile.v1`, prepared through `gate_a`, started by the runtime or execution service, or
> run on any wallet (dev or final) or in `dev` or `live` mode, until every step in
> [What must happen before any deployment](#what-must-happen-before-any-deployment) is done **and** an explicit written
> team approval naming the exact profile hash, build, wallet and mode is recorded in this entry. A chat message, a
> review comment or a merged PR is not that approval. FS1 (IDEA-093) stays the final candidate; nothing here changes
> FS1, S5, S6, S7, EXP-007 or any profile or runtime code.

- Date / author: 2026-10-26 SGT / requested in a Claude Code session on Keith's machine; design, arithmetic, code and
  record by Claude Code (subagent). Strategy owner for review: Keith.
- Status: **backtest run 2026-10-26: INCONCLUSIVE** (P: S8 − FS1-STATIC +0.004 pp/window, 90% CI −0.037..+0.047;
  P1 +0.040, P2 −0.022; T +0.40 pp, −0.15..+0.80; G1, G2, G3, G7 fail; drawdown and cost gates pass). S8 is not
  adopted; FS1 is unchanged. No profile, runtime, wallet, host or deploy action was taken. Predictive edge:
  NOT_ESTABLISHED.
- Base: `d0f242cb` (has the IDEA-106/IDEA-107 simulators), branch `claude/s8-experimental-strategy-20261026`; not
  pushed.
- Related: IDEA-093 (FS1), IDEA-106 (S6), IDEA-107 (S7), EXP-007, EXP-008, IDEA-001 §15 (EDGAR off hold for runtime),
  IDEA-034 (a losing arm is never SUPPORTED), larp/plan.md D-09, D-11, DEV-06..DEV-08, G-21.

## Request (in chat, 2026-10-26 SGT)

Propose one new experimental strategy, S8, aiming for higher net profit than an FS1-like static five-name 95% book at
200 USDT after realistic costs; parameters from literature or structure, not tuned on the data; pre-register and run an
offline backtest on the token (T) and proxy (P) snapshots; record it; do not deploy.

## What was read before this criteria commit (independence disclosure)

The request barred reading the result/outcome/variant sections of IDEA-106, IDEA-107, EXP-007 and EXP-008, their
LEDGER rows' status text and any `~/larp-idea106/*report*.json` before this commit. What was actually read:

- AGENTS.md; SKILL.md frontmatter, §0 and §1.1–§1.7, and F-90..F-126 lines (grep); larp/plan.md lines for D-09, D-11,
  DEV-06..DEV-08 and the EDGAR data-priority note (grep); `docs/official/source_page.md` lines 67, 111, 127, 133, 140
  and kit `web3-open-api.md` l.66, `bstocks-trading-guide.md` l.29, `logging.md` l.3 and l.41 (grep).
- `docs/LEDGER.md`: the header, the threads table, rows EXP-001..IDEA-018 and the IDEA-105 row; the ID column only
  (grep) for the rest. The IDEA-106/107 and EXP-007/008 rows were not printed.
- `docs/ledger/IDEA-106.md` lines 1–248 (header, rules check, design, economics, rules table, criteria);
  `docs/ledger/IDEA-107.md` lines 85–238 (why-not table, design, economics, criteria, deployment steps);
  `docs/ledger/EXP-008.md` lines 32–111 (Data, Costs, Metrics, Pass criterion, Decision use, Caveats); the section
  headings of all four files and EXP-007 line 83; `docs/ledger/IDEA-093.md` lines 1–60; `docs/ledger/README.md`
  lines 1–20; `docs/INCOMPLETE_WORK.md` headings and the first ~160 characters of each line.
- Code: `tools/idea106/simulate.py`, `tools/idea107/simulate.py` (both in full), `tests/strategy/test_idea107_backtest.py`
  lines 1–80. The snapshot files' keys, first two rows and row counts (no returns computed).

**Prior results seen despite the rule (incidental, disclosed in full):**
1. IDEA-106's header Status line and the section headings of IDEA-106 and IDEA-107 say "NOT SUPPORTED"; the IDEA-106
   status line adds that S6 trails FS1-STATIC on T with the 90% interval below zero and that S6-B4 (drawdown) fails.
2. The worktree's `git log` (printed when it was created) shows the IDEA-107 commit subject "S7 backtest NOT SUPPORTED
   (P −0.16 pp/window vs FS1-STATIC; both halves negative)".
3. IDEA-107's design text (allowed section) says REV3 was the best of IDEA-106's seven T arms and cites EXP-008's
   inverse-σ result (−0.24 pp on P) and IDEA-106's text cites the trend guard's −0.33 to −0.50 pp.
4. EXP-008's "Caveats" section (read because Caveats is a design section) contains EXP-008's full result block: on P
   S1 − EW −0.58 pp (EW better), the trend guard −0.33 pp, inverse-σ weights −0.24 pp, and a diagnostic that the
   most volatile names had the highest mean 10-session returns on P (NVDAB 2.30%, TSLAB 2.06%, SKHYB 1.84%, GOOGLB
   1.00%, MSFTB 0.88%).

**How this influenced S8.** It ruled out, as data-snooped, any design based on volatility or beta (a high-vol tilt
would be selection on item 4), on 5–10-session momentum or reversal (items 1–3), or on trend timing. S8's signal is a
calendar date, one per name per quarter, so every predictable name is overweighted about equally often; it is not a
function of the names' level, trend or volatility. One known bias runs *against* S8: SKHYB (third-highest mean return
in item 4) is never overweighted, so S8 underweights it in tilt windows. The structure control (TILT-AVG, below) has the
same SKHYB underweight and isolates the timing.

## What the rules allow (checked, SKILL.md §0.2)

Checked: the verbatim page lines above, the kit lines above, SKILL.md never-do 1–13, F-44, F-50, F-63, F-64, F-91,
F-95, F-99, F-100, F-114, F-115, F-117, F-119, F-123, F-124, F-126, and plan.md D-09, D-11, DEV-06..DEV-08.

- **Settled:** only NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB against USDT, bStock ↔ USDT only (F-91, F-123; kit
  `web3-open-api.md` l.66); long-only, no leverage/shorting/derivatives (F-64, page l.140); no manual trading or
  intervention (F-48, F-60; page l.111, l.127); one ai-seeds log per round including hold-only rounds, every broadcast
  swap's `tx_hash`, never an approve's (F-99, F-100; kit `logging.md` l.3, l.41); no order while `openState` is false
  (F-95); orders 24/7 otherwise (F-119); clean, authorised, non-future data (F-63, page l.133); fees and gas reduce the
  score (F-44); the registered build runs unchanged (F-114, F-117); development testing to Oct 28, then FS1 is frozen
  (F-126, relayed).
- **Open; S8 must work either way:** the scoring formula (Q-39: F-43 vs F-115), BNB in equity (Q-03), exact window
  instants (Q-06).
- **Team policy, not rules** (never-do 11): the 3%/8%/12% ladder, 30%/35% per-name lines, 95% gross, minimum trade,
  cost gates, end flatten.

**Consequence.** As for S6/S7: S8 cannot replace FS1 in the Oct 29 – Nov 12 run (F-114, F-117, F-126). It is a research
record and at most a future REHEARSAL candidate after the gates below.

## Why not the obvious alternatives

| Option | Why rejected |
|---|---|
| Any volatility, beta or inverse-σ weighting (incl. Black 1972 / Frazzini–Pedersen "leverage-constrained investors tilt to high beta") | Item 4 above shows which way it went on P: choosing it now is selection on a seen result |
| 5–20-session momentum or reversal, rotation or build tilt | Already pre-registered as S6 and S7; their outcomes were seen (items 1–3) |
| Trend or volatility timing of gross (EXP-007 guard; Moreira–Muir) | Long-only at a 95% cap, timing can only remove exposure; it gains only if the removed periods' return is below the ≈ 0.3% switching cost. Guard already measured |
| Turn-of-month, pre-holiday, pre-FOMC timing | Same: removes exposure in periods whose expected return is ≈ 0, not negative; pays switches |
| Raise gross to 100% | 5 × 40 USDT exceeds the 38.2 USDT leg cap → 10 legs; +5 pairs each way ≈ 0.29% of equity per window to gain 5% × E[10-session return] ≈ 0.05 pp. Also a G-21 deviation. 95% at five 38 USDT legs is cost-optimal |
| Threshold rebalancing / "diversification return" | Drift trades are mostly below the 18.637 USDT minimum (9.3% of equity); the continuous-rebalancing gain is ≈ ½(mean σ² − σp²) ≈ 0.1% per 10 sessions, below one extra pair each way |
| Cross-sectional seasonality (Heston–Sadka 2008) | Needs years of history: tokens start Jun–Jul 2026 and the underlying proxy may not be used at runtime (D-09, F-63) |
| NVDA → SK hynix lead-lag | KRX closes at 02:30 ET, so the catch-up is already in SKHYB's price at the open+30 fill on T and at the KRX close on P |
| Post-earnings drift | Evidence that it has largely gone in large caps (Martineau 2022; Chordia et al. 2009); it is also a momentum-type signal (item 1) |
| Model-driven directional view | D-11: models never size or place orders; a model's view cannot be backtested honestly on history it may have memorised (L-23, I-67) |

## The S8 design

**One sentence.** At the opening build, overweight the eligible US-listed names whose quarterly earnings announcement is
predicted to fall inside the hold, using the date four quarters earlier plus 364 days (Frazzini & Lamont's
prediction method), then hold exactly like FS1; with no predicted announcer, or three or more, S8 is FS1.

**Why this mechanism.**
1. *Published prior at the right horizon.* Stocks earn higher returns around and in the month of scheduled earnings
   announcements (Beaver 1968; Chari, Jagannathan & Ofer 1988; Frazzini & Lamont 2007; Barber, De George, Lehavy &
   Trueman 2013, international; Savor & Wilson 2016, who find it in large firms and read it as compensation for
   announcement risk). Reported magnitudes are of the order of 0.5–0.8% per announcement month for announcers over
   non-announcers. These are cited from memory and were **not re-read in this session; no L-ID is assigned**.
2. *Independent of the price signals already tested.* The signal is a calendar date, not a function of returns,
   trend or volatility in the hold or before it (disclosure above).
3. *Deterministic and point-in-time at runtime.* The predicted date comes from public, dated SEC filings (8-K
   Item 2.02 "Results of Operations", filed on the release day; EDGAR is approved for runtime, IDEA-001 §15) four
   quarters earlier. SK hynix does not file with the SEC (Korean DART is on hold), so **SKHYB is never predicted**.
4. *Cheapest structure.* FS1 already pays the build and flatten; S8 re-weights the build only (as S7 did), adding one
   or two approve + swap pairs each way.
5. *Nothing fitted.* 364 days (same weekday a year later), 1.5× overweight (28.5%, the largest weight that splits into
   two legs under the 38.2 USDT cap and stays under FS1's 30% cap), proportional underweight, and "no tilt for 3+
   announcers" (cost per unit of tilt rises; arithmetic below) are structural.

**Rules (all deterministic).**

| Item | S8 value | FS1 value |
|---|---|---|
| Universe | GOOGLB, MSFTB, NVDAB, SKHYB, TSLAB vs USDT | same |
| Predictable names | GOOGLB, MSFTB, NVDAB, TSLAB (SEC filers). SKHYB: never an announcer | — |
| Announcement days (backtest) | per name and calendar quarter, the session with the largest absolute basket-residual daily log return, eᵢ,ᵤ = rᵢ,ᵤ − mean over the five names of r·,ᵤ, from underlying closes (P series). Only quarters that are complete in the data and end before the decision close are used. Ties → earliest | — |
| Announcement days (runtime, if ever built) | the reaction session after each Item 2.02 8-K filing date (EDGAR, point-in-time) | — |
| Prediction | p = a + 364 calendar days for each announcement day a. Name i is an announcer for the window if some p satisfies date(build) < p ≤ date(flatten) | — |
| m = number of announcers | m ∈ {1, 2}: announcers 28.5% each; the other 5 − m names share 95% − 28.5%·m equally (m = 1: 16.625%; m = 2: 12.667%). m ∈ {0, 3, 4}: all five at 19% | 19% each |
| Legs | 57 USDT target = two 28.5 USDT legs; 33.25 and 25.33 USDT one leg; all ≥ 18.637 | five 38 USDT legs |
| After the build | hold; top-up when gross < 90% (names below target back to target); a name above the 35% hard line goes back to target; no re-ranking, no trade when the announcement passes | same |
| Ladder | 3% daily (UTC day) and 8% drawdown block buys, 8% clears below 5%; 12% cuts gross to ≤ 40%, no rebuild | same |
| Model role (D-11) | none added; FS1's SHADOW view unchanged. Dates come from EDGAR metadata by code, not from a model | — |

**Scored-run applicability (honest note).** With 2025's filing dates plus 364 days, GOOGL/MSFT (Oct 29, 2025 filings)
predict reactions on or before the Oct 29, 2026 build, TSLA (Oct 22) before it and NVDA (Nov 19) after Nov 12. So S8
would most likely hold FS1's exact book in the Oct 29 – Nov 12, 2026 run. The backtest tests the mechanism over all
10-session windows; it is not a claim that S8 would differ from FS1 in this particular run.

## Economics at 200 USDT (estimate, not a fill result)

Inputs as IDEA-106/107: round-trip spread GOOGLB 3, MSFTB 17, NVDAB 4, SKHYB 2, TSLAB 5 bp; central per side =
spread ÷ 2 + 3 bp = GOOGLB 4.5, MSFTB 11.5, NVDAB 5.0, SKHYB 4.0, TSLAB 5.5 bp; gas 0.058 USDT per approve + swap;
team convention 25 bp + 0.03 USDT; stress 50 bp + 0.03; gas at the cap price 0.277. Notional traded is 190 USDT each
way in both arms, so a per-side bp level changes S8 − FS1 only through the per-name spread mix.

| | FS1-STATIC (build + flatten) | S8, m = 1 | S8, m = 2 |
|---|---|---|---|
| Legs each way | 5 | 6 | 7 |
| Central cost | 2 × (38 × 30.5 bp + 5 × 0.058) = **0.812 USDT (0.41%)** | +0.116 gas ± spread mix (−0.008..+0.026) = **+0.108..0.142 USDT (+0.054..0.071%)** | +0.232 gas ± mix = **≈ +0.21..0.26 USDT (+0.11..0.13%)** |
| Tilt (equity moved to announcers) | — | 9.5% | 19% |
| Gain | — | 19 USDT × (r_ann − mean r_non) | 38 USDT × (mean r_ann − mean r_non) |
| **Break-even announcer excess over the hold, central** | — | **0.61%** (0.57–0.75% with the mix) | **0.61%** |
| Team convention / stress (+0.03 per pair) | 1.25 / 2.20 USDT | +0.06 USDT → 0.32% | +0.12 USDT → 0.32% |
| Gas at cap price (0.277) | 3.00 USDT | +0.55 USDT → 2.9% | +1.11 USDT → 2.9% |

m = 3 would move only 18% for +3 pairs (break-even ≈ 0.97%) and m = 4 only 9% for +4 pairs (≈ 2.6%), hence no tilt.

**Break-even, plainly.** S8 matches FS1 at central cost when a predicted announcer beats the non-announcers by about
**0.6% over the hold**. The literature's 0.5–0.8% is
for a whole month and for broad samples; a 10-session hold around one announcement in mega-caps, with dates detected
from prices rather than known, should capture less. **Expected outcome: a difference near zero, likely slightly
negative at central cost and slightly positive at the team convention; INCONCLUSIVE.** S8 is not claimed to be
profitable.

## Pre-registered backtest criteria (written 2026-10-26 before any S8 code or run)

**Hypothesis.** Over 10-session windows, S8 earns a higher mean net return than FS1-STATIC after central costs, and the
gain comes from announcement timing, not from the tilt structure.

**Data (offline only; hashes verified before use by the simulator; files never modified).**
- `~/larp-idea106/snapshot-20261026/tokens.json` SHA-256
  `61f24e23abf70b7b8110cd460d1a3069d3d052b9e1b2ab17d01ce1c555ccc05c` (kit `market/candles` 1-hour bars,
  OPEN-labelled) and `underlying.json` SHA-256 `19dd7f70814a3156a685c7b5d6373bc6fce57c9202f23394eca5896e9933dbe3`
  (Yahoo daily closes, research-only proxy, D-09). Completed sessions only, through the **2026-10-23** close.
- **P (decisive):** underlying closes, IDEA-106 `proxy_market` (signal at close s − 1, fills and marks at closes).
  Announcement days from all underlying closes (from 2018-06-01). Windows: every overlapping window whose build session
  is ≥ 2019-01-02 **and** at which every predictable name's year-ago quarters are complete in the data (structural;
  expected first build ≈ 2019-07-01 because the data start mid-2018). **P1** = windows whose flatten session is
  ≤ 2022-12-30; **P2** = windows whose build session is ≥ 2023-01-03; straddling windows count only in full P.
- **T (confirmatory):** token 1-hour bars, IDEA-106 `token_market` (fill = close of the 1-hour bar starting at open +
  30 min, fallbacks as IDEA-106; marks hourly); every window with build index s ≥ 1. **Deviation by design:** T's
  announcement days come from the underlying series a year earlier (a research stand-in for the public filing date;
  tokens have no year-old history).
- No network, credentials, `.env`, wallet, host, deploy, AWS, model or API calls.

**Simulation.** 200 USDT start; build at fill s, hold through fills s + 1..s + 8, flatten at fill s + 9 (IDEA-107
`run_book`, whose equal-weight path reproduces IDEA-106 FS1-STATIC). Legs ≤ 38.2 and ≥ 18.637 USDT; a target change
below the minimum is skipped. 3%/8%/12% ladder in every arm. No red flags or model views replayed.

**Arms.**
- **S8** as specified.
- **FS1-STATIC** (comparator): five names at 19%, same mechanics.
- **TILT-AVG** (structure control): per window with the same m, the mean over all C(4, m) assignments of the S8 shape
  to the four predictable names (SKHYB always on the non-announcer side, as in S8); windows with m ∈ {0, 3, 4} equal
  FS1-STATIC.
- **PLACEBO** (timing control): S8 with every predicted day moved by +45 calendar days (half a quarter: same names,
  same frequency of overweights, wrong timing).
- Reported only, cannot change the outcome: WITH_SKHY (SKHYB predictable too), WIDE (p within ±5 calendar days of the
  window), ALL_M (tilt also for m = 3: 25%/10%, m = 4: 21.25%/10%), and a mechanism diagnostic: in tilt windows, mean
  price return over the hold of announcers minus non-announcers (compare with the 0.61% break-even).

**Costs.** Central (per name), team convention, stress, gas at the cap price, as above. **Break-even cost:** the gas
per approve + swap (central bps) at which mean(S8 − FS1-STATIC) on P = 0, bisection on [0, 5] USDT; also stated, the
tilt-window announcer excess needed (the 0.61% above). A uniform per-side bp level is not a useful break-even here:
both arms trade the same notional, so it cancels.

**Metrics.** Per window: net return, maximum drawdown on marks, DD ≥ 8% / ≥ 12%, legs, cost, smallest discretionary
leg, m. Means, medians, SD, share > 0 (all windows and tilt windows). Differences with a moving-block bootstrap 90%
interval (block = 10 windows, 10,000 resamples, **seed 108**, IDEA-106 `block_bootstrap`). Calendar years by build
session.

| # | Pass when |
|---|---|
| S8-G0 | Point in time and costs: simulator and tests committed before the run; tests prove that no announcement day from a quarter ending on or after the decision close is used and that changing any close after the decision changes nothing; the fill bar ends after the signal close; flat prices give the hand-computed costs for S8 (m = 1, 2) and FS1-STATIC; the target rule matches the table for m = 0..4; the equal path reproduces IDEA-106 FS1-STATIC |
| S8-G1 | Profit vs FS1 on P (central): mean(S8 − FS1-STATIC) > 0 **and** its 90% lower bound > 0, **and** S8's own mean net return has a 90% lower bound > 0 (IDEA-034) |
| S8-G2 | Chronological split: mean(S8 − FS1-STATIC) > 0 in **P1 and in P2** separately |
| S8-G3 | Timing, not structure: on P, mean(S8 − TILT-AVG) > 0 with 90% lower bound > 0, **and** mean(S8 − PLACEBO) > 0 |
| S8-G4 | Cost robustness on P: mean(S8 − FS1-STATIC) > 0 under the team convention **and** under stress, **and** break-even gas ≥ 0.116 USDT per pair (2 × central) |
| S8-G5 | Drawdown limits on **P and T** (central): share of windows with DD ≥ 8% ≤ FS1-STATIC's + 3 pp; DD ≥ 12% ≤ FS1-STATIC's + 2 pp; median maximum drawdown ≤ 1.25 × FS1-STATIC's |
| S8-G6 | T does not contradict: T's 90% upper bound of mean(S8 − FS1-STATIC) ≥ 0 |
| S8-G7 | Breadth on P: mean(S8 − FS1-STATIC) > 0 in at least 5 of the 8 calendar years 2019–2026 |
| S8-G8 | Implementation bound (P and T): no discretionary leg below 18.637 USDT; mean legs per window ≤ FS1-STATIC's + 4; mean incremental cost ≤ 0.15% of equity |

**Outcome states (ledger rule 3).**
- **SUPPORTED** only if S8-G0..G8 all pass. Even then it is evidence for a team review, not a deployment approval.
- **NOT SUPPORTED** if any of: P's 90% upper bound of mean(S8 − FS1-STATIC) < 0; S8's own P 90% upper bound < 0; the
  P1 and P2 means are both < 0; T's 90% upper bound < 0; S8-G5 fails.
- **INCONCLUSIVE** otherwise (the expected result). S8 then stays experimental and is not adopted; FS1 is unchanged.
- No parameter may change after this commit. A changed design is a new pre-registration. A later code fix that changes
  a number is recorded as a deviation with both results. No dev-wallet or scored-run P&L is used (ledger rule 5).

## Rules and guardrail check

| Item | S8 | Status |
|---|---|---|
| Never-do 1 / F-48, F-60, G-08 | targets computed by code at the build; no human action | complies by design |
| F-114, F-117, F-126 | not the registered build; cannot replace FS1 mid-run | **blocks scored-run use** |
| Never-do 2, 12 / F-34, F-99, F-100, G-04, G-19 | same round loop as FS1: one write-ahead decision record per order, one round log per round with every broadcast swap's `tx_hash`; the reason summary names the predicted filing | complies if implemented in the existing loop |
| Never-do 3, 4 / F-64, F-91, F-123, G-02, G-13 | five bStocks vs USDT only, long-only, gross 95% | complies |
| F-95 | unchanged `openState` guard | complies |
| Never-do 8 / F-63, G-05 | runtime dates from public SEC filings filed ≥ 9 months earlier; backtest dates from year-old closes only | complies; S8-G0 tests it |
| D-09 | the Yahoo proxy is research-only; it is never a runtime input | complies |
| D-11 | no model signs, sizes, ranks or places orders; no new model role | complies |
| G-21 (declared ≤ 20% per name; FS1 deviated to 30%) | 28.5% ≤ 30% cap | inside FS1's deviation; review needed |
| Never-do 5, 7, 9, 13 | nothing installed; offline backtest; no credentials; snapshots outside Git | complies |

## What must happen before any deployment

In order; each step recorded here with its evidence:
1. The backtest run as pre-registered with result **SUPPORTED** (INCONCLUSIVE or NOT SUPPORTED ends it).
2. Independent review of the simulator, tests and result against the recorded hashes (not the author); Keith as
   strategy owner.
3. A backtest with true Item 2.02 filing dates (EDGAR) instead of price-detected days, pre-registered first.
4. A prospective, forward-only test on sessions after 2026-10-23, pre-registered first.
5. Runtime implementation (an EDGAR date fetcher with point-in-time checks, a build-time weight rule in the FS1 planner
   and its validator; the builder now refuses weights other than 1/5) with pre-registered acceptance criteria and the
   full pinned suite passing.
6. Caps, gas and `signer.json` review (Isaac); G-21 review (Keegan).
7. A dev-wallet REHEARSAL showing the tilted build and a restart that keeps the targets, balance check MATCH.
8. **Explicit written approval from the team (Keith, Keegan, Isaac, Yao) recorded in this entry**, naming the exact
   build SHA, profile hash, wallet, mode and window. Not possible for the Oct 29 – Nov 12 run once FS1 is frozen.

### Backtest run record (2026-10-26 SGT, recorded before the run)

- **Criteria** committed at `df6b8df6`, before any S8 code existed.
- **Simulator** `tools/idea108/simulate.py` (SHA-256 `ddeed657fd3bfbb527efe7037efc70ccedf2d6925c8640641efeb044590876d8`)
  and tests `tests/strategy/test_idea108_backtest.py` (SHA-256
  `7efa06573667ed01e6bf85d5f1e1fdcdd48ee3e720705e8c5613d5b7fd5d9097`) committed at `40fe1373`, before any S8 run.
  Reused, unchanged: `tools/idea106/simulate.py` (`3155b9da…e99f`) and `tools/idea107/simulate.py` (`f1d54b6b…459bd`).
- **Tests (S8-G0):** 28 pass (Python 3.14.6, numpy 2.4.6, pytest 9.0.3, `~/anaconda3/bin/python`, offline): a planted
  move is detected as the quarter's announcement day and the incomplete last quarter is never used; the announcer set
  is unchanged when every close from the decision session on is changed; a quarter ending on or after the decision is
  not used; the shift window is build-exclusive and flatten-inclusive (WIDE and PLACEBO shifts too); SKHYB is never an
  announcer unless WITH_SKHY; coverage needs every predictable name's year-ago quarters; each T fill bar ends after the
  signal close; the target table for m = 0..4 (and ALL_M) sums to 95%, stays ≤ 30% and has no leg below 18.637 USDT;
  flat prices give the hand-computed cost and leg count for FS1-STATIC and four S8 announcer sets under central, team
  and stress costs (FS1 central 0.8118 USDT; NVDAB m = 1 adds 0.108–0.142 USDT as in Economics); the equal path
  reproduces IDEA-106's FS1-STATIC; S8 with no announcer is FS1 exactly; the decision rule maps every state; a
  snapshot with another hash is refused. IDEA-106 and IDEA-107 tests: 15 pass. Whole `tests/strategy`: 452 passed,
  1 failed for an environment reason (`eth_abi` not installed; `larp/execution_live/router.py`), as recorded in
  IDEA-107, unrelated to this change.
- **Snapshot** `~/larp-idea106/snapshot-20261026/`, hashes re-verified 2026-10-26 before use and checked again by the
  simulator at start: `tokens.json` `61f24e23abf70b7b8110cd460d1a3069d3d052b9e1b2ab17d01ce1c555ccc05c`,
  `underlying.json` `19dd7f70814a3156a685c7b5d6373bc6fce57c9202f23394eca5896e9933dbe3`. Not modified. Cutoff 2026-10-23
  (`LAST_SESSION`).
- **Command:** `~/anaconda3/bin/python -m tools.idea108.simulate --data ~/larp-idea106/snapshot-20261026 --out
  ~/larp-idea108/report-40fe1373.json` (report outside Git).
- **Implementation choices fixed here before the run** (details the criteria leave open): bootstrap = IDEA-106
  `block_bootstrap` (blocks of 10 consecutive windows, 10,000 resamples), seed 108, also for the P1/P2, tilt-window and
  mechanism intervals (reported); calendar year = build session's year; legs and cost count every leg including ladder
  cuts and the flatten; "discretionary leg" = build, top-up and hard-line legs (IDEA-106/107); break-even gas by 20
  bisection steps; residuals use all five names' returns and skip a day on which any close is missing; the
  aligned-closes reader is IDEA-106's `proxy_market` alignment started at the first data row (2018-06-01); P window
  starts are s ≥ 1 with build ≥ 2019-01-02 and coverage; T window starts are every s ≥ 1; PLACEBO uses whatever
  announcement days exist at the +409-day shift (no extra coverage filter); costs, controls, variants, years and the
  mechanism diagnostic are reported for P and T, gates use P except G5, G6 and G8 (as pre-registered).
- **Deviations:** none.

## Backtest result (2026-10-26 SGT): INCONCLUSIVE

Run at `16ba8aa3` (code `40fe1373`), offline, command as in the run record; report
`~/larp-idea108/report-40fe1373.json` (SHA-256 `a656f091f23337804333a1392bf302bf612b93d980eb959855b2951f0b534163`,
outside Git). Simulated fills at bar or daily closes, not realised fills (ledger rule 4). Differences are per
10-session window in percentage points of the 200 USDT start; intervals are moving-block bootstrap 90% (block 10,
10,000 resamples, seed 108).

**Main table (central costs).**

| Data | Windows (non-overlapping) | S8 mean net | FS1-STATIC mean net | S8 − FS1-STATIC (90% CI) | S8 own 90% CI |
|---|---|---|---|---|---|
| **P** 2019-07-01 → 2026-10-23 | 1,831 (184); tilt windows 606 (m = 1: 414, m = 2: 192; m = 0: 1,147, m = 3: 65, m = 4: 13) | +1.083% | +1.080% | **+0.004 pp (−0.037, +0.047)** | (+0.54, +1.63) |
| P1 2019-07 → 2022-12 | 875 | +0.765% | +0.725% | +0.040 pp (−0.005, +0.090) | (−0.03, +1.66) |
| P2 2023-01 → 2026-10 | 947 | +1.396% | +1.418% | **−0.022 pp** (−0.090, +0.044) | (+0.71, +2.09) |
| P, tilt windows only | 606 | — | — | +0.011 pp (−0.123, +0.139), ahead in 49.7% | — |
| **T** 2026-07-16 → 2026-10-23 | 62 (7); tilt 28 (m = 1: 24, m = 2: 4) | +1.024% | +0.626% | **+0.40 pp (−0.15, +0.80)** | (+0.12, +3.73) |
| T, tilt windows only | 28 | — | — | +0.88 pp (−0.35, +1.79) | — |

**Controls and mechanism.**

| | P | T |
|---|---|---|
| S8 − TILT-AVG (structure) | +0.001 pp (−0.036, +0.039) | +0.16 pp (−0.12, +0.43) |
| S8 − PLACEBO (+45 days) | +0.048 pp (−0.011, +0.110) | +0.47 pp (−0.09, +0.86) |
| Announcer minus non-announcer price return over the hold, tilt windows (break-even 0.61%) | **+0.09%** (−1.02, +1.14) | +2.88% (−3.86, +9.05) |
| Overweight counts | GOOGLB 187, MSFTB 195, NVDAB 221, TSLAB 195, SKHYB 0 | TSLAB 14, GOOGLB 9, MSFTB 9, NVDAB 0 |

**Costs and drawdown (P unless stated).**

| | S8 − FS1-STATIC | S8 | FS1-STATIC |
|---|---|---|---|
| Central | +0.004 pp | +1.083% | +1.080% |
| Team convention (25 bp + 0.03) | +0.005 pp | +0.899% | +0.894% |
| Stress (50 bp + 0.03) | +0.005 pp | +0.420% | +0.414% |
| Gas at the cap price (0.277) | −0.003 pp | −0.337% | −0.334% |
| **Break-even gas per pair** | **≥ 5 USDT (the search cap; see the correction below)** | | |
| Mean legs / cost per window | +0.03 legs, +0.003 USDT (0.0016% of equity) | 12.88 / 0.982 USDT | 12.85 / 0.979 USDT |
| P: DD ≥ 8% / ≥ 12% / median max DD | | 10.9% / 2.8% / 3.28% | 11.3% / 2.7% / 3.23% |
| T: DD ≥ 8% / ≥ 12% / median max DD | | 17.7% / 1.6% / 3.55% | 17.7% / 6.5% / 3.59% |
| Smallest discretionary leg | | 25.33 USDT | 38.0 USDT |

P by build year (S8 − FS1-STATIC, pp): 2019 +0.02, 2020 +0.08, 2021 +0.09, 2022 −0.07, 2023 −0.09, 2024 +0.14,
2025 −0.04, 2026 −0.10 (4 of 8 positive). Reported-only variants (P / T, pp vs FS1-STATIC): WITH_SKHY −0.006 / +0.09;
WIDE +0.011 / +0.34; ALL_M −0.002 / +0.40. T fill fallbacks: next bar 5, session close 3.

**Gate by gate.**

| Gate | Result | Why |
|---|---|---|
| S8-G0 point in time, costs | PASS | 28 tests, run record |
| S8-G1 profit vs FS1 on P | **FAIL** | mean +0.004 pp but the 90% lower bound −0.037 < 0 (S8's own lower bound +0.54% > 0) |
| S8-G2 P1 and P2 both > 0 | **FAIL** | P1 +0.040, P2 −0.022 |
| S8-G3 timing, not structure | **FAIL** | S8 − TILT-AVG +0.001 pp, lower bound −0.036 < 0 (S8 − PLACEBO +0.048 > 0 passes its part) |
| S8-G4 cost robustness | PASS | team +0.005, stress +0.005 pp > 0; break-even gas ≥ 5 USDT ≥ 0.116 |
| S8-G5 drawdown (P and T) | PASS | DD ≥ 8%: P 10.9% vs 11.3%, T 17.7% vs 17.7%; DD ≥ 12%: P 2.8% vs 2.7% (+0.2 pp ≤ +2), T 1.6% vs 6.5%; median max DD ratio P 1.02, T 0.99 |
| S8-G6 T does not contradict | PASS | T upper bound +0.80 ≥ 0 |
| S8-G7 breadth (≥ 5 of 8 years) | **FAIL** | 4 of 8 |
| S8-G8 implementation bound | PASS | smallest leg 25.33 USDT; +0.03 legs; +0.0016% of equity (P), −0.009% (T) |

**Outcome (pre-registered rule): INCONCLUSIVE.** No NOT SUPPORTED trigger fired (P upper bound +0.047 ≥ 0, S8's own
P upper bound > 0, T upper bound ≥ 0, G5 passes, P2 negative but P1 positive), and G1, G2, G3 and G7 fail. On P the
difference is indistinguishable from zero (+0.004 pp per window, about 0.007 USDT), the announcers did not beat the
other names by anything near the 0.61% break-even (+0.09%), and the structure control explains the whole difference.
T is positive (+0.40 pp) but it is 62 overlapping windows (7 independent), driven by TSLAB and the late-July GOOGLB/
MSFTB predictions, and cannot decide anything. **S8 is not adopted; FS1 is unchanged; the announcement-premium edge in
this basket is NOT_ESTABLISHED.**

**Caveats.**
1. *The signal is a noisy stand-in for real dates.* Announcement days are price-detected (largest basket-residual move
   of the quarter), not true filing dates. Recent detected days include several that, from memory and unverified here
   (no network), were not earnings reactions (e.g. NVDAB 2025-01-27 and 2025-04-09, GOOGLB 2025-09-03, MSFTB
   2026-06-26), while others match the usual late-January/April/July/October reports. The test is therefore biased
   toward zero; the deployment step 3 backtest with EDGAR Item 2.02 dates is the proper test and was not run.
2. *Cost economics differ from the pre-registered estimate.* The arithmetic assumed S8 pays one or two extra pairs
   each way. In simulation FS1-STATIC's 38 USDT positions usually exceed the 38.2 USDT leg cap after any gain, so its
   flatten takes two legs per name, while S8's 33.25 and 25.33 USDT underweights still flatten in one. Net, S8 used only
   +0.03 legs per window on P (+0.0016% of equity) and fewer on T. This is why the break-even gas reached the 5 USDT
   search cap and S8-G4 passed. It depends on how the runtime splits a position slightly above 38.2 USDT (two legs in
   the simulator), which was not checked against FS1's sell path.
3. P is a proxy (Yahoo, research-only, D-09), with SKHYB at the KRX close; T is short and its "announcement days" come
   from the proxy a year earlier.
4. The overlapping windows are not independent; the block bootstrap only partly allows for it. 606 of 1,831 P windows
   carry any tilt, so whole-sample differences are diluted by construction (the tilt-only row shows the same answer).
5. The independence of the design is limited: prior S6/S7/EXP-008 results were partly seen before the criteria (see the
   disclosure). S8's signal avoids those signals, but the choice of a non-price mechanism was informed by them.
6. Even if it had passed, S8 would most likely hold FS1's exact book in the Oct 29 – Nov 12, 2026 run (scored-run note
   above) and cannot be used there anyway (F-114, F-117, F-126).

- 2026-10-26 note (Claude Code, with the results): the Economics table's "+0.108..0.142 USDT" for m = 1 is correct for
  a flat market (tested); in moving markets the flatten-leg effect in caveat 2 offsets it. The criteria are unchanged.

## Provenance (2026-10-26)

The work was done on a local branch stacked on `d0f242cb` (IDEA-106, EXP-007 and IDEA-107 originals). For its own PR
it was moved by cherry-pick (`-x`, author dates and order preserved) onto PR 301's head `37bff3c3`, because S8's
simulator and tests import `tools/idea106` and `tools/idea107`; it does not need EXP-007. Original → new commits:
criteria `df6b8df6` → `8154702c`; simulator + tests `40fe1373` → `8d5a1f2b`; run record `16ba8aa3` → `0416335d`;
results `dd36599d` → `511ec802`. `tools/idea108/simulate.py` and `tests/strategy/test_idea108_backtest.py` are
byte-identical to the originals, and an independent rerun reproduced `report-40fe1373.json` byte for byte.

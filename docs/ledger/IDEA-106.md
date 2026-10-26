# IDEA-106 — S6 (EXPERIMENTAL, DO NOT DEPLOY): a concentrated rank-rotation book with a model veto, as an alternative to FS1

> ## DO NOT DEPLOY
>
> S6 is an **experimental research design**. It is not FS1, not a candidate for the scored run, and not approved for
> anything except the offline backtest pre-registered below. It **must not** be installed, activated, used to build a
> FINAL (or REHEARSAL) `StrategyProfile.v1`, prepared through `gate_a`, started by the runtime or execution service, or
> run on any wallet (dev or final) or in `dev` or `live` mode, until every step in
> [What must happen before any deployment](#what-must-happen-before-any-deployment) is done **and** an explicit written
> team approval naming the exact profile hash, build, wallet and mode is recorded in this entry. A chat message, a
> review comment or a merged PR is not that approval. FS1 (IDEA-093) stays the final candidate; nothing here changes it.

- Date / author: 2026-10-26 SGT / requested in a Claude Code session on Keith's machine; design, arithmetic and record by
  Claude Code. Strategy owner for review: Keith.
- Status: **open — design and pre-registered backtest criteria only.** No backtest, data fetch, model call, profile,
  runtime change, wallet, host or deploy action was taken. Predictive edge: **NOT_ESTABLISHED** (as for FS1).
- Base: canonical `codex/system-testing-20261012` at `c997df2c` (PR298 merged).
- Related: IDEA-093 (FS1), IDEA-104 (S5), IDEA-105/IDEA-103 (TH-01 token history), IDEA-091 (strategy alternatives
  research), EXP-007, EXP-008, IDEA-063 (quote costs), IDEA-084 PF-01/PF-02/PF-04, IDEA-034 (a losing arm is never
  SUPPORTED), IDEA-012 (hourly autocorrelation), larp/plan.md D-11, G-21, G-22, T-11, T-14, DEV-02..DEV-04, DEV-21;
  strategy-opinions.md S-01, S-04, S-06.

## Request (in chat, 2026-10-26 SGT)

Design an experimental strategy, S6: more active and higher-volatility than FS1, agentic, aiming to maximise profit,
inside the challenge rules and the project's guardrails, and not deployed. Record the design, the rule check, an
honest cost estimate, pre-registered backtest criteria, an implementation plan and a do-not-deploy section.

## What the rules allow (checked, SKILL.md §0.2)

Checked: `docs/official/source_page.md` (verbatim page), the kit copies in `docs/official/kit/` (Guide p.3, p.6,
p.13), SKILL.md §0.3 never-do 1–13, §1.9–§1.10 (F-90..F-126), §7.1 (G-01..G-19), §11 (Q-03, Q-06, Q-09, Q-17, Q-32,
Q-36, Q-39, Q-40 including the "answered" and team-position notes), larp/plan.md declared values, G-21/G-22,
D-11, DEV-02..DEV-07, DEV-21.

- **Settled by the rules or organiser answers** (not open): orders 24/7 (F-119) but none while `openState` is false
  (F-95); only the five bStocks against USDT, bStock ↔ USDT only (F-91, F-123); long-only, no leverage/shorting
  (F-64); no manual trading or intervention (F-48, F-60); no changes once the run starts and the build registered at
  final activation runs unchanged (F-114, F-117); automatic restarts allowed, manual not (F-124); one ai-seeds log per
  round with every broadcast swap's `tx_hash` (F-99, F-100); development testing until Oct 28, then FS1 is frozen and
  installed (F-126, relayed); fees and gas reduce the score (F-44); number of trades is not scored (F-50), but "if you
  don't trade at all? That's definitely not what this competition is about" (F-115).
- **Open, and S6 must work either way:** how the run is scored (Q-39: F-43 % equity vs F-115's PnL/drawdown/logs/repo
  mix), whether BNB counts in equity (Q-03), the exact window instants (Q-06), whether a corrected version can be
  registered during Oct 27–29 (Q-40).
- **Team policy, not rules** (never-do 11): the 3%/8%/12% ladder, the per-name and gross caps, the minimum trade,
  the cost gates, the PF-04 calendar and the end flatten.

**Consequence for S6.** Under F-114/F-117/F-126 the scored run uses the build registered at final activation, and the
team will freeze and install FS1 after Oct 28. S6 cannot be swapped in during the scored run, and it cannot be
designed, backtested, implemented, reviewed and qualified before that freeze. S6 is therefore a research record and,
at most, a candidate for a dev-wallet REHEARSAL after the gates below; it is **not a scored-run option**.

## Why not the other "more active" designs (reasoned from repo evidence)

| Option | Why not chosen |
|---|---|
| Intraday mean reversion on hourly candles | IDEA-012 measured lag-1 hourly autocorrelation −0.08..−0.34 on on-chain prints and read it as bid-ask bounce, not tradable reversion. A round trip at the 18.637 USDT minimum costs about 27–74 bp of the leg (measured spread + impact + gas, table below). With hourly moves of the order of tens of bp, the expected reversal is well below that hurdle; and the large-cap literature (IDEA-012 §2: daily reversal ≈ 0 for large caps, half bounce; Nagel 2012) gives no edge to pay it |
| Profit-taking and re-entry | Stops/take-profits lower mean return under IID returns and more under costs (L-33 Kaminski & Lo; Lo & Remorov); each cycle pays two legs plus gas |
| Daily forced round trips | Already rejected for FS1 on cost (about 0.3–1.5% over the run, IDEA-093 request) |
| Model-driven directional buys | No producer for `exposure_assessment` exists (IDEA-093 FS1 section); LLM news long-leg edges are small and "unprofitable at 20 bps round-trip" (IDEA-012 §2, Lopez-Lira & Tang); and a model's view cannot be backtested honestly on history it may have memorised (L-23, I-67) |
| Static high-volatility tilt | Profile-level and cheap, but not "more active"; it is kept below as the concentration control (CONC3) |

## The S6 design

**One sentence.** Hold the **three** eligible names with the strongest trailing 10-session token return at about
31.7% each (95% gross), swap at most one name per US session and only when the best outsider beats the weakest
holding by a fixed margin, within a run budget of six swaps; a model may **veto** a swap-in on verified adverse
evidence, and every size, order and risk decision stays in deterministic code.

**Why this one.** It is the design whose costs can be bounded in advance and whose claim can be tested offline:
1. *Larger swings by construction.* Three names at ~31.7% instead of five at 19% raise idiosyncratic variance at the
   same gross. That is the honest source of S6's "higher volatility"; it is a variance choice, not an edge. The
   tournament argument for variance (top 3 of ≤ 25 paid, raw return) is a strategy opinion (S-01, S-04, S-06) and stays
   out of the proposal; under F-115 and the F-45 tie-break, more drawdown can also cost rank.
2. *Selection rule with a published prior.* Cross-sectional and time-series momentum are the most replicated price
   effects (Jegadeesh & Titman 1993; Moskowitz, Ooi & Pedersen 2012), but at 3–12-month horizons; at 1–4 weeks single
   stocks show reversal (Jegadeesh 1990; Lehmann 1990), weaker in large caps. So the sign at a 10-session horizon in five
   correlated mega-caps is **not known**; the backtest reports the reversal mirror (bottom-3) as a falsification arm.
   10 sessions is chosen because it matches the scored-run length (about 10 US sessions) and leaves enough decision days
   on the short token history; it is not fitted.
3. *Turnover is capped, not emergent.* A margin, one swap per session and a six-swap budget bound the extra cost at
   about 0.5–1.1% of equity (central), whatever the signal does.
4. *It reuses FS1's machinery.* Same five names, red-flag classes, ladder, cost/impact gates, PF-04 window, `openState`
   guard, signer, gas scope and logging. The new parts are a ranking, a rotation rule and a veto.

**Rules (all deterministic; values fixed here and in `config/strategy/experimental/s6-design.v0.json`).**

| Item | S6 value | FS1 value |
|---|---|---|
| Universe | GOOGLB, MSFTB, NVDAB, SKHYB, TSLAB vs USDT | same |
| Held names K | 3 (reported variant: 2) | 5 |
| Target per held name | 95% ÷ 3 ≈ 31.67% of equity; weight cap 1/3; hard name line 40% → trim to target | 19%; cap 30%; hard line 35% |
| Gross target | 95%; top-up when below target − 5 pp | same |
| Score | sᵢ = ln(Cᵢ,t ÷ Cᵢ,t−10), C = session close = close of the last 1-hour token bar ending at or before the NYSE close (16:00 ET) of session t (FS1/EXP-008 convention) | — |
| Missing data | a missing session close carries the last close forward; a name with more than 2 carried closes in the lookback is not eligible that day | — |
| Initial build | at `trade_after`, buy the top 3 by score (Class 2 blocked or vetoed names skipped; next name takes the slot) | buy all five |
| Swap rule | at the first round ≥ open + 30 min of each US regular session, if best unheld score − worst held score > **150 bp**: sell the worst held name, then buy the best unheld name | none |
| Swap limits | ≤ 1 swap per US session; ≤ **6 swaps per run**; swaps only between `trade_after` and `new_risk_end`; after the budget is used S6 holds like FS1 | — |
| Swap legs' hours | US regular session only (lower measured spread: MSFTB 7 vs 17 bp off-session, IDEA-063 C3); mandatory sells keep 24/7 `KIT_OPEN_STATE` | 24/7 for every leg |
| Ladder | 3% daily (UTC day) and 8% drawdown block buys; 8% clears strictly below 5% (PF-02); 12% cuts gross to ≤ 40%. **A swap starts only if its buy is permitted at that moment; no rotation sells while buys are blocked** | same ladder |
| Failed buy after the sell | retry in later slots of the same session within the existing attempt limits; cash still idle at the next session is bought by the normal top-up into the best eligible unheld name | — |
| Red flags | unchanged: verified Class 1 (Item 4.02) forces a sale; verified Class 2 (1.05, 2.06) blocks buys 5 sessions | same |
| Window | PF-04: `trade_after` Oct 29 14:00Z, `new_risk_end` Nov 9 21:00Z, `flatten_start` Nov 10 19:00Z, `signing_end` Nov 11 14:45Z — for the record only; S6 is not a scored-run option | same |
| Leg sizes | minimum trade 18.637 USDT; a ~63 USDT position is two legs under the 38.2 USDT per-trade cap (see implementation item 6) | one leg per name |

**Agentic layer (inside D-11).** Models assess; deterministic code decides. Models never sign, size, rank or place
orders, and their output schema has no trade fields (D-11, IDEA-093 "What AIand/ChatGPT in its decisions means").
- *Live-capable after approval — veto only.* A new per-candidate stage asks the routed assessor (AIand/ChatGPT, FS1's
  routing) whether verified evidence since the last session contradicts holding the name. Output
  `{view: ADVERSE | NONE, evidence_ids[], falsifier}`. A claim counts only after the existing deterministic verifier
  matches it to a source span. A verified ADVERSE result removes that name from **swap-in** eligibility for the
  session. It never forces a sale (that remains Class 1 only), never adds a buy and never changes a size. Failure,
  timeout or an unverified claim = NONE (the swap proceeds on the rule alone), so a model outage cannot stop exits or
  create trades.
- *SHADOW only — directional view.* The same stage also returns `view: POSITIVE | NEGATIVE | NEUTRAL` per name with
  cited evidence. It is logged with its inputs and reasoning (F-49, G-06) and has **no authority** in S6 v0. Giving it
  any (e.g. a one-rank tie-break inside the margin) needs its own prospective, forward-only experiment, because a
  historical backtest of a model's view is contaminated by memorisation and look-ahead (L-23, I-67).
- Every round still logs `input`/`cot`/`output`/`orders` (F-99); deterministic rounds write the rule path as `cot`
  (F-106 (a), Q-36).

## Economics at 200 USDT (estimate, not a fill result)

Inputs, all from the repo: FS1 profile `docs/build/evidence/fs1-final-20261025/fs1-final.json` (SHA-256
`19176e6c…`): quote round-trip spread GOOGLB 3, MSFTB 17, NVDAB 4, SKHYB 2, TSLAB 5 bp (mean 6.2), median impact
1 bp per side, `fee_bps` 0 (netting **unverified**, #119, IDEA-063 C6), BNB 722.15 USDT, minimum trade 18.637 USDT,
per-trade cap 38.2 USDT, slippage limit 20 bp, gas sizing budget 0.0000800 BNB per approve + swap (≈ 0.058 USDT, the
"29 bp of a 20 USDT trade" of IDEA-063 C4), cap-price action budget 0.000384 BNB (≈ 0.277 USDT), measured live gas
0.0000242 BNB (≈ 0.0175 USDT, IDEA-091). The team's backtest convention is 25 bp per side plus 0.03 USDT gas per swap
(EXP-007/EXP-008). Arithmetic: `[ESTIMATE]`, scratch script, not committed.

**One swap** = sell a ~63.3 USDT position (two legs) and buy ~63.3 USDT (two legs): 126.7 USDT traded, four
approve + swap pairs.

| Cost case | Per side | Gas per pair | Per swap | % of equity | Hurdle on the swapped position | 3 swaps | 6 swaps |
|---|---|---|---|---|---|---|---|
| Low (live gas, mean spread) | 4.1 bp | 0.0175 | 0.12 USDT | 0.06% | 19 bp | 0.18% | 0.37% |
| **Central** (sizing gas, mean spread, +2 bp slippage) | 6.1 bp | 0.058 | **0.31 USDT** | **0.15%** | **49 bp** | **0.46%** | **0.93%** |
| MSFTB legs, central | 11.5 bp | 0.058 | 0.38 USDT | 0.19% | 59 bp | 0.57% | 1.13% |
| Team convention | 25 bp | 0.03 | 0.44 USDT | 0.22% | 69 bp | 0.66% | 1.31% |
| Stress | 50 bp | 0.03 | 0.75 USDT | 0.38% | 119 bp | 1.13% | 2.26% |
| Gas at the cap price | 6.1 bp | 0.277 | 1.19 USDT | 0.59% | 187 bp | 1.78% | 3.56% |

Building and flattening are paid by FS1 too (central ≈ 0.81 USDT, 0.40%); S6's three-name book needs about two more
pairs (≈ +0.06 pp). Minimum-trade check: every S6 leg is ≥ 25 USDT (63.3 ÷ 2 or more), above 18.637; at the minimum
size a round trip would cost 27–74 bp of the leg, which is why S6 never trades minimum-size legs for rotation.

**Break-even, plainly.** Concentration alone adds variance, not expected return. To merely match FS1 net of costs, S6's
selection must make its three held names beat the equal-weight five by about **0.5–1.0 pp over the run** at the central
cost (3–6 swaps; 0.2–2.3 pp across the cases), which is **≈ 5–10 bp per session**; each swap must earn ≥ **≈ 49 bp**
(19–187 bp) of relative return on the swapped position over its holding period, and ≥ **≈ 99 bp** to meet the
proposal's "round-trip cost + 50 bp" entry rule. The large-cap literature puts short-horizon long-leg edges at
≤ ~10 bp/day for whole strategies (IDEA-012 §2), selection among five correlated names has less room than that, and
EXP-008 found that the one active element tested so far (the trend guard) cost −0.33 to −0.50 pp. **The expected
outcome is that S6 earns less than FS1 by roughly its costs, with wider dispersion and more drawdown.** S6 is not
claimed to be profitable; without the backtest below passing, its edge is NOT_ESTABLISHED.

## Rules and guardrail check

| Item | S6 | Status |
|---|---|---|
| Never-do 1 / F-48, F-60, G-08: no manual trading or intervention | every rotation decided by code from the profile; no human action once running | complies by design |
| F-114, F-117, F-126: no changes during the run | S6 is not the registered build; it cannot replace FS1 mid-run | **blocks scored-run use** |
| F-124: automatic restarts only | held set, swap count, last swap session and pending sell→buy pair must be persisted in the journal and restored by the supervisor restart of the same run (FS1's one-run rule) | needs new code |
| Never-do 2 / F-34, G-04: one decision record per order with a reason summary | rotation sell and buy each get their own write-ahead record and reason (IDEA-099), linked by a rotation ID | needs new code |
| Never-do 12 / F-99, F-100, G-19: one round log per round; every broadcast swap's `tx_hash` | unchanged round loop; a rotation spans two or more rounds, each logged | complies if implemented in the existing loop |
| Never-do 3, 4 / F-64, F-91, F-123, G-02, G-13 | five bStocks vs USDT only; sell to USDT then buy; long-only; gross ≤ 95% | complies |
| F-95: no order while `openState` is false | unchanged guard on every leg | complies |
| Never-do 5 / F-60, F-61, G-03: committed, pushed, manifested before it trades | not met; nothing is installed | gate below |
| Never-do 8 / F-63, G-05: point-in-time data | score uses closed candles only; the backtest must lag every input; no future bars | backtest criterion S6-B0 |
| Never-do 7, 9, 13 / F-61, F-62, F-103 | no credentials here; the backtest is offline and uploads nothing; data snapshots stay out of Git (as EXP-008) | complies |
| F-49 (c), G-06: complete model I/O | veto/view stage records full requests and responses | needs new code |
| G-01, G-18: signer allow-list, at-most-once signing | unchanged; more swaps = more exact-amount approvals | unchanged code; new caps review |
| G-11: enforce what is declared; limits not loosened in a drawdown | ladder kept; rotation pauses while buys are blocked | complies |
| G-21 declared ≤ 20% per name, ≤ 80% gross (already deviated by FS1 to 30% / 95%, DEV-03/DEV-04) | 33.3% cap, 40% hard line | **new deviation row needed** |
| T-11 "not to trade often"; proposal entry rule "selected cases returned more than round-trip cost + 50 bp" | more trading; the entry rule is checked by S6-B7 | **deviation row needed**; B7 |
| DEV-21 initial gas only | 6 swaps × 4 pairs ≈ 24 extra pairs ≈ 0.4–1.4 USDT at expected prices, far inside the F-125 30 USDT seed; cap-price reserve 6.7 USDT | review by Isaac |
| G-15: no manipulation | ~63 USDT orders | complies |
| F-45 tie-break / F-115 drawdown | concentration raises drawdown; S6-B4 bounds it | accepted risk, measured |

## Pre-registered backtest criteria (written 2026-10-26 before any code, data fetch or run)

**Hypothesis.** Over 10-session windows of bStock token history, S6 (K = 3, L = 10, margin 150 bp, ≤ 1 swap per
session, ≤ 6 per window) earns a higher mean net return than the FS1-like static book, after costs, and the gain comes
from selection rather than from concentration.

**Data.**
- **T (primary):** kit `candles` 1-hour bars for the five bStocks (`after=` paging, participant-kit.md K6a), fetched
  read-only through the TH-01 transport (IDEA-105, `TokenHistoryConfig.v1` convention
  `BINANCE_WEB3_RAW_TOKEN_NO_LOCAL_ADJUSTMENT_V1`), from each token's first bar to the 2026-10-26 NYSE close. Fetched
  by a team member with the dev Web3 key, never with the registered wallet's ai-seeds credentials (never-do 13).
  Snapshot kept outside Git; its SHA-256 is recorded in this entry **before** the run.
- **P (secondary, veto only):** EXP-008's underlying daily snapshot `data/exp008/underlying.json` (SHA-256
  `f061394d…`, research-only, D-09), with daily fills at the next close. It can make the result NOT SUPPORTED; it
  cannot make it SUPPORTED.

**Simulation.**
- Every overlapping 10-session window with at least 10 earlier sessions for the score. Session calendar for T: the
  pinned 2026 NYSE calendar (IDEA-054); P uses its own session dates (EXP-008).
- Fill price: the close of the first full 1-hour bar starting at or after the open + 30 min (EDT 15:00Z, EST 16:00Z).
  Signal at session t's close trades at session t + 1's fill bar. Marks: hourly closes. Start 200 USDT; both arms flat
  at the last session's fill bar.
- Legs ≤ 38.2 USDT and ≥ 18.637 USDT; a target change smaller than the minimum is skipped (FS1 rule).
- Ladder in both arms on hourly marks: 3% daily (UTC day) → no buys that UTC day; 8% drawdown from the window peak →
  no buys until < 5%; 12% → gross cut to ≤ 40%, no rebuild in that window. No red flags or model veto (cannot be
  replayed honestly).

**Arms.**
- **S6** as specified above.
- **FS1-STATIC** (comparator): five names at 19% (95% gross), built at session 1, held, top-up band 5%, same ladder.
- **CONC3** (control for concentration): the mean over all ten static three-name books at 31.67%, same ladder.
- Reported only, cannot change the outcome: S6 with K = 2; L = 5 and L = 20; REV3 (the bottom three, the reversal
  mirror); margin 0; no swap budget.

**Costs.** Central: per side = spread/2 + 1 bp impact + 2 bp slippage, per-name spreads from the FS1 quote summary;
gas 0.058 USDT per approve + swap. Sensitivities: team convention (25 bp per side + 0.03 USDT per pair), stress
(50 bp per side + 0.03), gas at the cap price (0.277 USDT per pair). Break-even: the per-side bp (gas central) at which
mean S6 − FS1-STATIC = 0, by bisection.

**Metrics.** Per window: net return, maximum drawdown on hourly marks, whether it reached 8% and 12%, swaps, traded
notional, cost. Means, medians, SD, share > 0. Differences with a moving-block bootstrap 90% interval (block = 10
sessions, 10,000 resamples, seed 106).

| # | Pass when |
|---|---|
| S6-B0 | Point-in-time check: the simulator is committed before the data snapshot hash; a test proves no fill or score uses a bar that ends after its decision time; synthetic flat/up/down prices give the hand-computed costs |
| S6-B1 | Profit vs FS1, central costs, T: mean(S6 − FS1-STATIC) > 0 **and** its 90% lower bound > 0, **and** S6's own mean net return has a 90% lower bound > 0 (IDEA-034: a losing arm is never SUPPORTED) |
| S6-B2 | Selection, not concentration: mean(S6 − CONC3) > 0 with 90% lower bound > 0 (T, central) |
| S6-B3 | Cost robustness: mean(S6 − FS1-STATIC) > 0 under the team convention (25 bp + 0.03), and the break-even per-side cost is ≥ 2 × the central per-side cost (≥ 12.2 bp) |
| S6-B4 | Drawdown limits (T, central): share of windows reaching 8% ≤ FS1-STATIC's + 5 pp **and** ≤ 15%; reaching 12% ≤ 5%; median maximum drawdown ≤ 1.5 × FS1-STATIC's |
| S6-B5 | Turnover bound: mean swaps per window ≤ 6 (structural), mean incremental cost vs FS1-STATIC ≤ 1.5% of equity, no leg below 18.637 USDT |
| S6-B6 | Breadth: S6 − FS1-STATIC > 0 in ≥ 60% of non-overlapping windows, and the mean stays > 0 when any one name is removed from the universe (K = 3 of the other four) in at least 4 of the 5 cases |
| S6-B7 | Proposal entry rule: across all swaps, the mean realised return of the swapped-in name minus the swapped-out name over the holding period exceeds that swap's round-trip cost + 50 bp |
| S6-B8 | P does not contradict: on P, the 90% upper bound of mean(S6 − FS1-STATIC) is ≥ 0 |

**Outcome states (ledger rule 3).**
- **SUPPORTED** only if S6-B0..B8 all pass. Even then the result is evidence for a team review, not a deployment
  approval.
- **NOT SUPPORTED** if the 90% upper bound of mean(S6 − FS1-STATIC) on T or P is < 0, or S6's own 90% upper bound is
  < 0, or S6-B4 fails.
- **INCONCLUSIVE** otherwise. This is the expected result: the bStock token history is short (EXP-008 T had 41
  overlapping, 4 non-overlapping windows to Oct 22), so the T interval will be wide. INCONCLUSIVE means S6 stays
  experimental and is not adopted; FS1 is unchanged.
- No parameter may be changed after the data hash is recorded; a changed design is a new pre-registration. No dev-wallet
  or scored-run P&L may be used (ledger rule 5).

### Backtest run record (2026-10-26 SGT, recorded before the run)

- **Simulator** `tools/idea106/simulate.py`, committed at `dc8e33ac` before the snapshot existed (S6-B0), with
  `tools/idea106/fetch.py` and `tests/strategy/test_idea106_backtest.py` (5 tests: fill and close bars end by their
  decision time across the DST change, a later close never changes an earlier score, flat prices give the
  hand-computed central costs for FS1-STATIC and S6, a rising outsider triggers a budgeted swap with legs
  ≥ 18.637 USDT, a 30% crash trips the 12% cut).
- **Snapshot**, fetched 2026-10-26 ~13:50Z by Keith's session with the dev Web3 key from `.env` (read-only GET
  `market/candles` through the TH-01 transport; Yahoo chart API for P). Kept outside Git at
  `~/larp-idea106/snapshot-20261026/` with 52 raw Web3 artifacts:
  - `tokens.json` SHA-256 `61f24e23abf70b7b8110cd460d1a3069d3d052b9e1b2ab17d01ce1c555ccc05c`. First bars: NVDAB
    2026-06-12, TSLAB 2026-06-12, MSFTB 2026-07-01, SKHYB 2026-07-14, GOOGLB 2026-07-15 (so T starts mid-July);
    hourly gaps (hours with no bar) 5–152 per name, handled by the carry rule.
  - `underlying.json` SHA-256 `19dd7f70814a3156a685c7b5d6373bc6fce57c9202f23394eca5896e9933dbe3`.
- **Deviation BT-D1 (data availability, not a parameter):** the snapshot was taken while the Oct 26 US session was
  still open, so the last completed session, **2026-10-23**, ends both T and P instead of the Oct 26 close.
- **Implementation choices fixed here before the run** (where the criteria above leave a detail open):
  all of a session's trades execute at its fill time, using each name's fill price (fallbacks counted);
  swaps and swap-ins need the score of both names (a name with > 2 carried closes is skipped on both sides);
  after the 12% cut S6 makes no swaps for the rest of the window; NYSE early closes are not modelled (16:00 ET
  throughout); session dates come from the underlying NYSE trading days; K = 2 uses a 56% name line.

## Implementation plan (if, and only if, the gates allow)

Profile settings alone cannot express S6: FS1/S1 never sells on drift or rank, has no ranking input and holds all five
names. A profile-only approximation is a static concentrated tilt through `s1.weights`, but the FS1 builder refuses
weights other than 1/5 and that is CONC3, not S6. New runtime code is needed:

1. `larp/strategy/s6.py` (new, pure): score from session closes, eligibility, the margin swap rule, budgets; the
   `s6` profile block and its validator.
2. `larp/strategy/policy.py` and the planner: targets from `s6`; a new discretionary `ROTATION_EXIT` SELL linked to its
   `ROTATION_ENTRY` BUY by a rotation ID; the "no rotation sell while buys are blocked" precedence below the ladder,
   red-flag and flatten paths.
3. `larp/marketdata/history.py` / `token_sessions`: reuse FS1's TH-01 history (IDEA-103) with a lookback of ≥ 11
   session closes; a separate pinned `TokenHistoryConfig.v1`.
4. `larp/strategy/execution_bounds.py`: per-reason hours (rotation legs US-session, mandatory legs `KIT_OPEN_STATE`);
   today `hours` is per profile.
5. `larp/strategy/profiles.py` `validate_live`, `gate_a.prepare`, `gate_a_check`, `service.build_driver`,
   `execution_live/main.py`: keep refusing S6 in FINAL/live; a REHEARSAL scope only after approval, like S2/S5.
   `validate_live` already refuses any baseline other than EQUAL_WEIGHT / TREND_GUARDED_VOL and any environment other
   than REHEARSAL / FINAL (tests below).
6. Signer and caps (`larp/execution_live/caps_review.py`, `tools/deploy/propose_signer_caps.py`,
   `review_rehearsal_caps.py`): either raise the per-trade cap to cover a 63.3 USDT position (`validate_live` requires
   cap ≥ top position + reserve) or allow multi-leg top positions in the validator; gas action budget and exit reserve
   for 3 × 2 exit children; per-run swap count.
7. `larp/risk/accounting.py`: unchanged ladder; expose "buys permitted now" to the rotation rule.
8. `larp/intelligence`: the veto/view stage prompt, schema (no trade fields), verifier mapping and routing stage;
   audit capture; SHADOW flag for the view.
9. Journal/replay (`larp/research/replay.py`): persist and replay rotation state across restarts.
10. Backtest: `tools/s6/backtest.py` (new, modelled on `tools/exp008/simulate.py`), committed before the data hash.

## What must happen before any deployment

In order; each step recorded in this entry with its evidence:
1. Snapshot hash recorded, backtest run as pre-registered, result **SUPPORTED** (INCONCLUSIVE or NOT SUPPORTED ends it).
2. Independent review of the backtest code and result (not the author), Keith as strategy owner.
3. If the view layer is to have any authority: a separate prospective, forward-only experiment, pre-registered and run.
4. Runtime implementation with pre-registered acceptance criteria, red-on-base tests and the full pinned suite
   (Python 3.12.15 / PostgreSQL 14.24) passing.
5. Deviation rows for G-21 caps, T-11 activity and the proposal entry rule finalised in the GAP-62 review (Keegan).
6. A REHEARSAL profile and coverage review; Isaac approves the exact profile hash, caps, gas and `signer.json`.
7. A dev-wallet REHEARSAL run that shows rotations (sell then buy), a failed-buy retry and a restart that resumes
   rotation state, with balance check MATCH.
8. **Explicit written approval from the team (Keith, Keegan, Isaac, Yao) recorded in this entry**, naming the exact
   build SHA, profile hash, wallet, mode and window.
9. For the scored run in addition: registration at final activation (F-125) before any trade. Under F-114/F-117/F-126
   this is not possible for the Oct 29 – Nov 12 run once FS1 is frozen; S6 cannot be used there.

## Repository artefacts in this entry

- `config/strategy/experimental/s6-design.v0.json`: the design values above as an `S6ExperimentDesign.v0` document,
  `mode` `EXPERIMENTAL_DO_NOT_DEPLOY`, `environment` `EXPERIMENTAL`. It is not a `StrategyProfile.v1`.
- `tests/strategy/test_s6_experimental.py`: offline tests that `validate_live` refuses the design document and every
  FS1 profile grafted with S6 (baseline, block, environment), that FS1 itself still validates, and that the design
  values are internally consistent. No FS1, S5 or other profile bytes and no runtime behaviour change.

## Open questions and risks

- Q-39: if scoring weighs drawdown (F-115), S6's higher drawdown may cost more than any extra return.
- #119: if quotes do not net route fees, every cost above is understated.
- The short token history makes the backtest low-powered; P is a long proxy but uses underlying stocks, not tokens.
- Rotation doubles the number of approvals and swaps, so the S2-F6 post-approve requote risk and allowance recovery
  (IDEA-096/098) apply more often.
- Concentration in three names raises single-name event risk (earnings in the window); the veto acts only on verified
  filings, not on price gaps.

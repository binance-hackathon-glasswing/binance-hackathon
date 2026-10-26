# IDEA-107 — S7 (EXPERIMENTAL, DO NOT DEPLOY): a build-time residual-reversal tilt that trades no more than FS1

> ## DO NOT DEPLOY
>
> S7 is an **experimental research design**. It is not FS1, not a candidate for the scored run, and not approved for
> anything except the offline backtest pre-registered below. It **must not** be installed, activated, used to build a
> FINAL or REHEARSAL `StrategyProfile.v1`, prepared through `gate_a`, started by the runtime or execution service, or
> run on any wallet (dev or final) or in `dev` or `live` mode. Under F-114, F-117 and F-126 the build frozen after
> Oct 28 and registered at final activation (FS1, IDEA-093) runs unchanged through the scored run, so S7 **cannot** be
> used there whatever its backtest says. Before any other use, every step in
> [What must happen before any deployment](#what-must-happen-before-any-deployment) must be done **and** an explicit
> written team approval naming the exact profile hash, build, wallet and mode must be recorded in this entry. A chat
> message, a review comment, a merged PR or a SUPPORTED backtest is not that approval. Nothing here changes FS1, S5,
> S6, EXP-007 or any profile or runtime code.

- Date / author: 2026-10-26 SGT / requested in a Claude Code session on Keith's machine; design, arithmetic, code and
  record by Claude Code. Strategy owner for review: Keith.
- Status: **pre-registered 2026-10-26** (criteria committed before any simulator code exists and before the snapshot
  is read for this idea). Not adopted, not implemented in the runtime, not approved. Predictive edge:
  **NOT_ESTABLISHED**.
- Base: `744430e5` (tip of `claude/s6-experimental-active-strategy-20261026`: IDEA-106 S6 and EXP-007 with their
  simulators). Branch `claude/s7-experimental-strategy-20261026`.
- Related: IDEA-093 (FS1), IDEA-106 (S6, its simulator and snapshot), EXP-007, EXP-008, IDEA-063 (quote costs),
  IDEA-012 (hourly autocorrelation), IDEA-034 (a losing arm is never SUPPORTED), larp/plan.md D-09, D-11, G-21, G-22,
  T-11, DEV-03/DEV-04.

## Request (in chat, 2026-10-26 SGT)

Propose one new experimental strategy (S7), pre-register its backtest, run it offline on the existing IDEA-106
snapshot, evaluate it honestly and record everything; it must not be deployed. Aim to improve net profit versus FS1
inside the rules, be explicit about the cost hurdle at 200 USDT, and compare against an FS1-like static five-name 95%
book under the same simulator, costs and 10-session windows.

## Prior results read before designing, and how they influenced S7 (snooping disclosure)

The token snapshot (T) and the underlying proxy (P) have both been used before. Read before S7 was designed:

| Source | What I read | Influence on S7 |
|---|---|---|
| IDEA-106 (S6) | Economics table (≈ 49 bp hurdle per rotation swap, 27–74 bp per minimum-size round trip); T result S6 − FS1-STATIC −1.49 pp; CONC3 ≈ FS1; P result +0.03 pp; reported-only variants including **REV3 (hold the three weakest) +0.76 pp on T**, K = 2, L = 5/20, margin 0 | **Yes.** (1) The cost arithmetic (known before S6's run) drove S7's main choice: no rotation trades at all, selection only where FS1 already trades. (2) S7 is in the **same contrarian family as REV3**. REV3's T result was seen, so **T cannot support S7**: it is confirmatory-only and can only contradict (gate S7-G6). (3) P was also used by S6 (top-3 by 10-session raw return ≈ FS1 on P). A 10-session raw-return mirror on P is therefore partly predictable (≈ 0); S7's signal (5-session, basket-residual, volatility-scaled) is different but correlated with it. P is the decisive test, but it is not virgin data. |
| EXP-007 | trend guard B − A −0.88 pp on T, drawdown −0.21 pp | Indirect: S7 adds no exposure timing; the comparator has no trend guard (as IDEA-106's FS1-STATIC) |
| EXP-008 | on P, S1 − EW −0.58 pp, inverse-σ weights −0.24 pp, trend guard −0.33 pp | Indirect: S7's base is FS1's actual equal weights (1/5, IDEA-093 S4-7), not inverse-σ |
| IDEA-093 (FS1) | five names at 19% (95% gross), cap 30%, hard line 35%, top-up band 5 pp, the 3%/8%/12% ladder | S7 keeps all of this and stays inside FS1's 30% name cap |

Guards against fitting to these results: every parameter below is fixed from the literature's standard horizon or
from the leg/minimum-trade geometry, none is chosen by looking at a result; there is **no threshold** to tune; the
pass rule rests on P with a pre-registered chronological split (2019–2022 vs 2023–2026) plus calendar-year breadth;
the reversal-mirror and parameter variants are reported only and cannot change the outcome; and no backtest code
exists or has been run for S7 at the commit that records these criteria.

## What the rules allow (checked, SKILL.md §0.2)

Checked: `docs/official/source_page.md` (Autonomous operation line 127, prohibited list lines 139–140, "Real costs are
reflected" line 105, audit line 111); kit copies `docs/official/kit/web3-open-api.md` line 66 and
`bstocks-trading-guide.md` line 29 ("Only these five bStocks are eligible"); SKILL.md §0.3 never-do 1–13, F-43..F-48,
F-60..F-64, F-91, F-93, F-95, F-99, F-100, F-114, F-115, F-117, F-119..F-126; larp/plan.md D-09, D-11, G-21, G-22,
T-11, DEV-03/DEV-04; the IDEA-106 rules section.

- **Settled (not open):** only NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB against USDT, bStock ↔ USDT only (F-91, F-123);
  long-only, no leverage, shorting or derivatives (F-64); every scored trade from the registered agent, no manual
  trading or intervention (F-48, F-60); no changes once the run starts, the build registered at final activation runs
  unchanged (F-114, F-117), and FS1 is frozen after Oct 28 (F-126, relayed); automatic restarts allowed, manual not
  (F-124); one ai-seeds log per round with every broadcast swap's `tx_hash` (F-99, F-100); no order while `openState`
  is false (F-95), otherwise 24/7 (F-119); fees and gas reduce the score (F-44); "if you don't trade at all? That's
  definitely not what this competition is about" (F-115).
- **Open, S7 must work either way:** how the run is scored (Q-39: F-43 % equity vs F-115's PnL/drawdown mix), whether
  BNB counts in equity (Q-03), the exact window instants (Q-06), whether a corrected version may be registered during
  Oct 27–29 (Q-40). None of these is asked about here.
- **Team policy, not rules** (never-do 11): the ladder, the caps, the minimum trade, the cost gates, the end flatten.

| Item | S7 | Status |
|---|---|---|
| Never-do 1 / F-48, F-60, G-08 | the tilt is computed by code from the profile at the build; no human action | complies by design |
| F-114, F-117, F-126 | S7 is not the registered build and cannot replace FS1 | **blocks scored-run use** |
| Never-do 3, 4 / F-64, F-91, F-123, G-02, G-13 | five bStocks vs USDT only; one name may be held at 0%; long-only; gross 95% | complies |
| Never-do 2, 12 / F-34, F-99, F-100, G-04, G-19 | same round loop and write-ahead records as FS1; no new order types | complies if implemented in the existing loop |
| F-95 | unchanged `openState` guard on every leg | complies |
| **D-11**: models never sign, size or place orders | the ranking and weights are deterministic code; a model may only write a SHADOW per-name view (logged with inputs and reasoning, F-49, G-06) with **no authority**; FS1's deterministic red-flag verifier is unchanged | complies by design |
| Never-do 8 / F-63, G-05, D-09 | the runtime signal uses only kit token candles (TH-01 history, IDEA-103/105); the Yahoo proxy P is a research-only offline check and never a runtime input (D-09: Yahoo is unlicensed for labels) | complies |
| G-21 (declared ≤ 20% per name, ≤ 80% gross; FS1 already deviates to 30%/95%, DEV-03/DEV-04) | two names at 28.5%, inside FS1's 30% cap and 35% hard line | inside FS1's deviation; a G-21 row would still be needed |
| T-11 "not to trade often" | the same build and flatten as FS1 plus two approve + swap pairs per run | complies |
| F-45 tie-break / F-115 drawdown | slightly more concentration than FS1; bounded by S7-G5 | accepted risk, measured |

## Why not the obvious alternatives

| Option | Why rejected |
|---|---|
| Momentum rotation (S6) | Pre-registered and NOT SUPPORTED (IDEA-106); not repeated |
| REV3 as it stands (bottom-3 rotation) | It is the best of seven arms already seen on T; adopting it would be selection on the result (IDEA-106 says so). It also rotates, paying the ≈ 49 bp per-swap hurdle |
| Intraday or overnight-return capture with 24/7 tokens | A daily round trip of the book costs ≥ 10 pairs × 0.058 USDT ≈ 0.29% of equity per day in gas alone |
| Threshold rebalancing to equal weight | Drift trades are mostly below the 18.637 USDT minimum (9.3% of equity); a minimum-size round trip costs ≈ 74 bp of the lot (IDEA-106) |
| Calendar exposure timing (turn of month, pre-holiday) or volatility-managed gross | In a long-only book already at 95%, timing can only remove exposure; it pays only if off-window returns are below the ≈ 0.3% switching cost per cycle. EXP-007/008 already measured the related trend guard |
| Long-horizon momentum, 52-week high | Needs ≥ 12 months of token history; tokens start Jun–Jul 2026 and the underlying proxy may not be used at runtime (D-09, F-63) |
| Earnings-announcement premium, customer–supplier lead-lag (e.g. NVDA → SK hynix) | Needs dated event or link data not in the offline snapshot and not replayable; on P the KRX close precedes the US close by ~13 h, which would contaminate a lead-lag test |
| Inverse-σ or low-volatility tilt | Measured on P by EXP-008 (−0.24 pp); not a new idea |

## The S7 design

**One sentence.** At the one moment FS1 already trades (the opening build), tilt the five-name 95% book away from the
name with the strongest recent basket-relative move and toward the two weakest, then hold exactly like FS1; no
selection trade is ever made after the build.

**Why this one.**
1. *It spends selection where trading is already paid for.* FS1 buys all five names at the build and sells them at
   the flatten anyway. Re-weighting those same buys costs only the extra legs (two approve + swap pairs per run),
   not a rotation. The hurdle falls from ≈ 49 bp per swapped position (S6) to ≈ 0.31% relative return on a 38 USDT
   tilt over the whole hold (table below).
2. *Published prior at the right horizon.* Weekly and monthly reversal in single stocks (Lehmann 1990; Jegadeesh
   1990) is stronger and more persistent in large caps when measured on residual, volatility-scaled returns (Blitz,
   Huij, Lansdorp & Verbeek 2013, "Short-term residual reversal"; Da, Liu & Schaumburg 2014). These are cited from
   memory and were not re-read in this session; no L-ID is assigned. Large-cap reversal is weak (IDEA-106; Nagel 2012),
   so the expected effect is small.
3. *Nothing is fitted.* Formation 5 sessions (Lehmann's week), volatility 20 sessions (about one month, the
   literature's common choice), tilt size fixed by the 38.2 USDT leg and 18.637 USDT minimum (below), no entry
   threshold.
4. *It keeps FS1's machinery and caps.* Same names, ladder, top-up band, 30% cap and 35% hard line; no new order type.

**Rules (all deterministic).**

| Item | S7 value | FS1 value |
|---|---|---|
| Universe | GOOGLB, MSFTB, NVDAB, SKHYB, TSLAB vs USDT | same |
| Signal (after close t = the session before the build) | daily log returns rᵢ,ᵤ = ln(Cᵢ,ᵤ ÷ Cᵢ,ᵤ₋₁); basket bᵤ = mean over eligible names; residual eᵢ,ᵤ = rᵢ,ᵤ − bᵤ; formation Eᵢ = Σ eᵢ,ᵤ over the last **5** returns; σᵢ = sample SD of eᵢ,ᵤ over the last **20** returns; zᵢ = Eᵢ ÷ (σᵢ √5), zᵢ = 0 when σᵢ = 0. C = session close (last 1-hour token bar ending at or before 16:00 ET) | — |
| Eligibility | a name needs all 21 closes and at most 2 carried (no bar that session) closes among the last 20; ineligible names keep 19% and are not ranked | — |
| Targets at the build | rank eligible names by (z, name). The two lowest → **28.5%** each; the highest → **0%**; every other name → **19%**. Gross 95%. Fewer than 3 eligible names → all five at 19% | 19% each |
| After the build | hold; top-up when gross < 90% (names below target back to target, a 0% name is never bought); a name above the 35% hard line goes back to target; **no selection trade, no re-ranking** | same hold rules |
| Ladder | 3% daily (UTC day) and 8% drawdown block buys, 8% clears below 5%; 12% cuts gross to ≤ 40%, no rebuild | same |
| Legs | ≤ 38.2 USDT and ≥ 18.637 USDT; a 57 USDT target is two 28.5 USDT legs | one 38 USDT leg per name |
| Model role (D-11) | SHADOW per-name view only, logged, no authority; not replayed | as FS1 |
| Window | at most one tilt per run, decided at the first build | — |

**Why 28.5 / 28.5 / 19 / 19 / 0.** At 200 USDT and 95% gross the book is 190 USDT. FS1 uses the minimum possible five
legs (5 × 38 ≤ 38.2). Moving the strongest name's whole 38 USDT into the two weakest gives 57 + 57 + 38 + 38 + 0:
six legs at the build (one more than FS1) and six at the flatten, a 19%-of-equity tilt, both overweights inside FS1's
30% cap, and no leg below the minimum (smallest 28.5 USDT). The one-name alternative (28.5/9.5) costs the same extra
legs for half the tilt and puts a 19 USDT leg at the minimum; it is reported only.

## Economics at 200 USDT (estimate, not a fill result)

Inputs as IDEA-106 (FS1 profile quote summary): round-trip spread GOOGLB 3, MSFTB 17, NVDAB 4, SKHYB 2, TSLAB 5 bp;
central per side = spread ÷ 2 + 3 bp (1 bp impact + 2 bp slippage) = GOOGLB 4.5, MSFTB 11.5, NVDAB 5.0, SKHYB 4.0,
TSLAB 5.5 bp (mean 6.1); gas 0.058 USDT per approve + swap (sizing budget); team convention 25 bp per side + 0.03 USDT;
cap-price gas 0.277 USDT. Fee netting is unverified (#119).

| Cost case | FS1-STATIC build + flatten | S7 extra per run | S7 extra, % of equity | Break-even: relative return the 38 USDT tilt must earn over the hold |
|---|---|---|---|---|
| **Central** | 2 × (38 × 30.5 bp + 5 × 0.058) = **0.812 USDT (0.41%)** | 2 extra pairs 0.116 + spread mix −0.055..+0.034 = **0.061–0.150 USDT** | **0.03–0.075%** | **0.16–0.39%** (0.31% at the gas term alone) |
| Team convention (25 bp + 0.03) | 2 × (190 × 25 bp + 5 × 0.03) = 1.25 USDT | 0.06 USDT (same notional) | 0.03% | 0.16% |
| Stress (50 bp + 0.03) | 2.20 USDT | 0.06 USDT | 0.03% | 0.16% |
| Gas at the cap price (0.277) | 2 × (0.116 + 5 × 0.277) = 3.00 USDT | 0.50–0.59 USDT | 0.25–0.29% | 1.3–1.6% |

The spread mix term is 2 × [19 × (bps of the two overweights) − 38 × bps of the zeroed name]: worst when MSFTB is
overweighted (+0.034), best when MSFTB is zeroed (−0.055). **Break-even, plainly:** with gain = 38 USDT × [(r₁ + r₂) ÷ 2
− r_top] over the hold, S7 matches FS1 net when the two weakest names beat the strongest by about **0.3%** over nine
sessions (≈ 3.4 bp per session; 1.5% at cap-price gas). In equity terms the hurdle is **≈ 0.06 pp per 10-session
window** (central), versus S6's 0.5–1.0 pp over a run. That is the cheapest selection bet available inside FS1's
caps, but large-cap short-term reversal is weak, so **the expected outcome is a difference near zero (≤ ~0.1 pp per
window either way) and INCONCLUSIVE**. S7 is not claimed to be profitable.

## Pre-registered backtest criteria (written 2026-10-26 before any S7 code or run)

**Hypothesis.** Over 10-session windows, S7 earns a higher mean net return than FS1-STATIC after costs, and the gain
comes from the residual-reversal ranking, not from the tilted structure.

**Data (offline only; hashes verified before use; files never modified).**
- Snapshot `~/larp-idea106/snapshot-20261026/` (IDEA-106 run record, outside Git):
  `tokens.json` SHA-256 `61f24e23abf70b7b8110cd460d1a3069d3d052b9e1b2ab17d01ce1c555ccc05c` (kit `market/candles`
  1-hour bars, OPEN-labelled per TH-01) and `underlying.json` SHA-256
  `19dd7f70814a3156a685c7b5d6373bc6fce57c9202f23394eca5896e9933dbe3` (Yahoo daily closes, research-only proxy).
  The simulator refuses to run if either hash differs.
- Completed sessions only, up to the **2026-10-23** close (IDEA-106 BT-D1).
- **P (decisive):** underlying daily closes from 2019-01-02; signal at close t − 1, fills at close t (IDEA-106 `proxy_market`).
  **P1** = windows whose flatten session is ≤ 2022-12-30; **P2** = windows whose build session is ≥ 2023-01-03;
  windows straddling the boundary count only in full P.
- **T (confirmatory-only, contaminated by REV3):** token 1-hour bars (IDEA-106 `token_market`), sessions from
  2026-07-15 (all five names).
- No network, credentials, `.env`, wallet, host, deploy, AWS, model or API calls.

**Simulation (IDEA-106 conventions, reused from `tools/idea106/simulate.py`).** 200 USDT start; window = build at
fill s, hold through fills s + 1..s + 8, flatten at fill s + 9; every overlapping window with s ≥ 21 (21 closes
before the build); T fills at the close of the 1-hour bar starting at open + 30 min (fallbacks as IDEA-106), marks
hourly; P fills and marks at closes. Legs ≤ 38.2 and ≥ 18.637 USDT; a target change below the minimum is skipped.
Ladder in all arms as IDEA-106. No red flags or model views replayed.

**Arms.**
- **S7** as specified.
- **FS1-STATIC** (comparator): five names at 19%, same hold rules and ladder (identical to IDEA-106's FS1-STATIC; a
  test proves it).
- **TILT-AVG** (control for structure): per window, the mean over all 30 assignments of the 28.5/28.5/19/19/0 shape
  to the five names.
- Reported only, cannot change the outcome: MIRROR (two strongest at 28.5%, weakest at 0%); RAW (5-session raw
  return, no residual, no σ scaling); F10 and F20 (formation 10 and 20 sessions); TILT1 (weakest 28.5%, strongest
  9.5%); on P, NO-SKHY-SIGNAL (SKHYB kept at 19% and not ranked, because its KRX close is ~13 h older than the US closes).

**Costs.** Central (per-name, above); team convention (25 bp + 0.03); stress (50 bp + 0.03); gas at the cap price
(central bps + 0.277). Break-even gas: the gas per approve + swap (central bps) at which mean(S7 − FS1-STATIC) on P
= 0, by bisection on [0, 5] USDT.

**Metrics.** Per window: net return, maximum drawdown on marks, DD ≥ 8% / ≥ 12%, legs, cost, smallest discretionary
leg. Means, medians, SD, share > 0. Differences with a moving-block bootstrap 90% interval (block = 10 windows,
10,000 resamples, seed 107), IDEA-106's `block_bootstrap`. "Non-overlapping" = every 10th window from the first.

| # | Pass when |
|---|---|
| S7-G0 | Point in time and costs: simulator and tests committed before the run; tests prove the signal at the build reads no close after s − 1, flat prices give the hand-computed costs for S7 and FS1-STATIC, the ranking rule assigns 28.5/28.5/19/19/0 as specified, and the equal-weight path reproduces IDEA-106's FS1-STATIC |
| S7-G1 | Profit vs FS1 on P (central): mean(S7 − FS1-STATIC) > 0 **and** its 90% lower bound > 0, **and** S7's own mean net return has a 90% lower bound > 0 (IDEA-034) |
| S7-G2 | Chronological split: mean(S7 − FS1-STATIC) > 0 in **P1 and in P2** separately |
| S7-G3 | Selection, not structure: on P, mean(S7 − TILT-AVG) > 0 with 90% lower bound > 0 |
| S7-G4 | Cost robustness on P: mean(S7 − FS1-STATIC) > 0 under the team convention **and** under stress, **and** break-even gas ≥ 0.116 USDT per pair (2 × central) |
| S7-G5 | Drawdown limits on **P and T** (central): share of windows with DD ≥ 8% ≤ FS1-STATIC's + 3 pp; DD ≥ 12% ≤ FS1-STATIC's + 2 pp; median maximum drawdown ≤ 1.25 × FS1-STATIC's |
| S7-G6 | T does not contradict (confirmatory-only): T's 90% upper bound of mean(S7 − FS1-STATIC) ≥ 0. A positive T result is **not** evidence for S7 (REV3 was seen) |
| S7-G7 | Breadth on P: mean(S7 − FS1-STATIC) > 0 in at least 5 of the 8 calendar years 2019–2026 (by build session) |
| S7-G8 | Implementation bound (P and T): no discretionary leg below 18.637 USDT; mean legs per window ≤ FS1-STATIC's + 2; mean incremental cost ≤ 0.15% of equity |

**Outcome states (ledger rule 3).**
- **SUPPORTED** only if S7-G0..G8 all pass. Even then it is evidence for a team review, not a deployment approval,
  and S7 still cannot be used in the scored run (F-114, F-117, F-126).
- **NOT SUPPORTED** if any of: P's 90% upper bound of mean(S7 − FS1-STATIC) < 0; S7's own P 90% upper bound < 0; the
  P1 and P2 means are both < 0; T's 90% upper bound < 0; S7-G5 fails.
- **INCONCLUSIVE** otherwise (the expected result). S7 then stays experimental and is not adopted; FS1 is unchanged.
- No parameter may change after this commit. A changed design is a new pre-registration. Any later code fix that
  changes a number is recorded as a deviation with both results. No dev-wallet or scored-run P&L is used (ledger rule 5).

## What must happen before any deployment

In order; each step recorded here with its evidence:
1. The backtest run as pre-registered with result **SUPPORTED** (INCONCLUSIVE or NOT SUPPORTED ends it).
2. Independent review of the simulator, tests and result against the recorded hashes (not the author); Keith as
   strategy owner.
3. A prospective, forward-only test on sessions after 2026-10-23 that no one has seen, pre-registered first.
4. Runtime implementation (a build-time weight rule in the FS1 planner and its validator; the builder now refuses
   weights other than 1/5) with pre-registered acceptance criteria and the full pinned suite passing.
5. A G-21 deviation row (two names at 28.5%) in the GAP-62 review (Keegan); caps, gas and `signer.json` review (Isaac).
6. A dev-wallet REHEARSAL showing the tilted build and a restart that keeps the targets, balance check MATCH.
7. **Explicit written approval from the team (Keith, Keegan, Isaac, Yao) recorded in this entry**, naming the exact
   build SHA, profile hash, wallet, mode and window. Not possible for the Oct 29 – Nov 12 run once FS1 is frozen.

### Backtest run record (2026-10-26 SGT, recorded before the run)

- **Criteria** committed at `084444fe`, before any S7 code existed.
- **Simulator** `tools/idea107/simulate.py` (SHA-256 `f1d54b6b…459bd`) and tests
  `tests/strategy/test_idea107_backtest.py` (SHA-256 `ff1ffcb3…94443`) committed at `6ceb91f1`, before any S7 run.
  10 tests pass (Python 3.14.6, numpy 2.4.4, offline): the build's signal is unchanged when its own and every later close
  change and moves when close s − 1 changes; each fill bar ends after the signal close; the residual σ-scaled z is
  hand-computed; short history and carried closes make names ineligible; the ranking assigns 28.5/28.5/19/19/0 (ties by
  name, one unranked name at 19%, < 3 ranked → equal weight), MIRROR and TILT1 shapes, 30 TILT-AVG books; flat prices
  give the hand-computed central and team-convention costs for S7 (12 legs, smallest 28.5 USDT) and FS1-STATIC (10 legs,
  0.8118 USDT); the equal-weight path reproduces IDEA-106's FS1-STATIC bit for bit (central and stress); a 30% crash
  trips the 12% cut; the decision rule maps every NOT SUPPORTED trigger; a snapshot with another hash is refused.
  The same session ran IDEA-106's 5 and EXP-007's 10 tests (pass). The whole `tests/strategy` folder: 424 passed,
  1 failed for an environment reason (`eth_abi` not installed in this interpreter; `larp/execution_live/router.py`),
  unrelated to this change.
- **Snapshot** `~/larp-idea106/snapshot-20261026/`, hashes re-verified 2026-10-26 before use and checked again by the
  simulator at start: `tokens.json` `61f24e23abf70b7b8110cd460d1a3069d3d052b9e1b2ab17d01ce1c555ccc05c`,
  `underlying.json` `19dd7f70814a3156a685c7b5d6373bc6fce57c9202f23394eca5896e9933dbe3`. Not modified. Cutoff 2026-10-23
  (IDEA-106 BT-D1, `LAST_SESSION`).
- **Command:** `python -m tools.idea107.simulate --data ~/larp-idea106/snapshot-20261026`; report kept outside Git at
  `~/larp-idea106/idea107-report-6ceb91f1.json`.
- **Implementation choices fixed here before the run** (details the criteria leave open): bootstrap = IDEA-106
  `block_bootstrap` (blocks of 10 consecutive windows, 10,000 resamples) with seed 107, also used for the P1/P2
  intervals (reported); calendar year = the build session's year; legs and cost per window count every leg including
  ladder cuts and the flatten; "discretionary leg" = build, top-up and hard-line legs (not the flatten or the 12% cut),
  as IDEA-106; break-even gas by 20 bisection steps; the cost cases, TILT-AVG, the split and the years are computed on
  P only (their gates are P gates); T reports central costs and the T variants; NO-SKHY-SIGNAL runs on P only.
- **Deviations:** none.

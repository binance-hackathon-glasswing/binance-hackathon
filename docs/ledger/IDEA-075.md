# IDEA-075 — Trading plan v1: S1 core book at 95% with trend guard and LLM exposure limiter

> First drafted as IDEA-058 in PR #123; renumbered to IDEA-075 on 2026-10-17 because IDEA-058 is the Gate A configuration assembly record.

- Date / author: 2026-10-16 / team decision (strategy S1 at 95% exposure), relayed in session; plan drafted with Claude
- Status: open (strategy choice decided by the team 2026-10-16; parameters in §12 proposed, not frozen; B2/B3/B4 core implemented and reviewed offline in PR #131 / IDEA-076 RV-131; live inputs, B5/B6/B7 and rehearsal remain; the trend-guard test is pre-registered in [EXP-007](EXP-007.md) and not run)
- What: the complete trading plan for v1.0. A volatility-weighted long-only book of the five eligible bStocks. Its exposure is the lowest of three levels: a basket trend level (95% / 60%), an LLM exposure limiter that can only lower exposure on verified evidence (95% / 60% / 30%), and the declared risk ladder. Flat by the end of the run.
- Why: over a 14-day run in five correlated tech names, return comes mostly from how much market exposure the book holds (S-05; IDEA-035 §10.2). The trend guard and the limiter are there to cut drawdown in a falling market, which the organisers say they look at (F-115). Neither is a source of edge.
- Cost / risk: at 95% the book takes almost the full market move. In the synthetic simulation (IDEA-035 §10.2, not market data), 90–100% gross gives a mean of +0.16% to +0.19% over 10 sessions, SD 5.2–5.8%, and P(hit the 8% stop) 8.9–12.4%, about double the 80% plan. The trend guard is untested (EXP-007), and five-session momentum is not supported as a return predictor for large caps (IDEA-035 §10.3); here it is a drawdown control only. The plan deviates from the submitted proposal's caps (≤ 4 positions, ≤ 20% per name, ≤ 80% gross) and from D-11's LLM role; §14 lists every change for the deviations register.
- Links: D-12, D-04, D-11, G-21, G-22, G-25, GAP-10, GAP-12, GAP-13, GAP-50, GAP-62, GAP-64; IDEA-016, IDEA-018 §4, IDEA-035, IDEA-037, IDEA-054, IDEA-057; EXP-007; F-15, F-34, F-43, F-44, F-48, F-99, F-115, F-117; S-01, S-05.

## 1. Decision (team, 2026-10-16)

The team chose strategy **S1** from the session ranking, with **95%** as the top exposure level:

- a volatility-weighted core book (rank 1 in the ranking; S2 was its fallback);
- a basket trend guard (#4);
- an LLM exposure limiter (#9) that can only lower exposure;
- combined by taking the **lowest** of the three levels, with the declared safety controls always winning.

This settles the exposure part of D-12 and supersedes the 80% equal-weight target of IDEA-035 B5 and IDEA-037 (§14). Everything below the strategy choice (every value in §12, the open decisions in §16) is a proposal for the team to confirm before the **Oct 22** parameter freeze.

## 2. The plan in one paragraph

At the start of the run the agent buys all five eligible bStocks, weighted so that calmer names get more money, until 95% of the wallet is invested. Once a day, after the US close, it checks two things. First, is the basket of the five names more than 1% below its 5-session average? If so, it cuts to 60%. Second, does the LLM, citing evidence that code has verified, judge the outlook CAUTION or SEVERE? If so, it cuts to 60% or 30%. It holds whichever level is lowest, and it never sells just because prices moved. The declared loss controls override everything: no new buys after a 3% daily loss or 8% drawdown, and a cut to 40% at 12% drawdown. It sells everything by Nov 11 15:00 UTC.

## 3. Universe and book

- **Instruments:** NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB against BSC USDT; BNB for gas only (F-91, F-93). Long-only, no leverage (never-do #3, #4).
- **Positions:** all five names. A name is left out only if it has an unresolved Class 1 red flag, is blocked by a Class 2 red flag, or fails the entry-cost gate at the time of the buy (DEV-05: impact ≤ min(50 bp, 2 × logged median) and total entry cost ≤ 50 bp). Its weight then stays in cash until it is eligible again. It is **not** spread over the other names, so no name ever goes above its own target.
- **Gross:** invested value ÷ equity. Equity counts USDT, BNB and tokens at the valuation the runtime already uses. The uninvested 5% covers the BNB gas floor (DEV-21) and rounding.

## 4. Exposure level

Every round, the **target gross** is:

> target = min(trend level, LLM level, risk cap)

and each name's target is target × wᵢ (§5).

### 4.1 Trend level

- **Series:** one session bar per name per US regular session, closing 16:00 ET, fixed in UTC (B3, D-09; calendar IDEA-054). DST ends Sun Nov 1, 2026, so the close is 20:00 UTC up to Oct 30 and 21:00 UTC from Nov 2.
- **Basket index:** Iₜ = Iₜ₋₁ × (1 + the equal-weight average of the five names' session returns). Equal weight here, not the book weights, so that the signal does not depend on the sizing.
- **Signal:** r = Iₜ ÷ (mean of the last 5 session values of I, today included) − 1.
- **State, with a dead band:**
  - r > +1% → **UP** → trend level 95%;
  - r < −1% → **DOWN** → trend level 60%;
  - otherwise the state does not change.
- **Start:** the state on the first run day is computed from the 5 sessions before Oct 29; inside the band, it starts **UP**.
- **Timing:** evaluated once per session, 15 minutes after the close bar is final. So at most one trend change per session. The new target applies from the next US session (§7).
- **Basket, not per name:** the five names are highly correlated (pairwise ≈ 0.55 in IDEA-035 §10.2's simulation inputs), so per-name signals would add trades without much information.

### 4.2 LLM level (exposure limiter)

- **Cadence:** one assessment per session after the trend evaluation, plus one when a new verified filing or official event flag for an eligible issuer arrives (the existing filing trigger).
- **Inputs:** only verified evidence already produced by the evidence pipeline (EDGAR filings for the five issuers; official event flags such as Federal Register rules and SEC trading suspensions, IDEA-029/031), plus a declared calendar of scheduled events in the window (the US midterm elections on Tue Nov 3; CPI and Fed dates to be checked and frozen with the parameters).
- **Output schema:** `{level: NORMAL | CAUTION | SEVERE, evidence_ids: [...], reason, falsifier}`. The model's reasoning is logged as `cot` (F-102).
- **Code accepts the output only if** every cited `evidence_id` exists in the evidence store, is verified and is inside the window, and the evidence class allows the level (table below). Otherwise the result is rejected and logged, and the previous accepted level stands.

| Verified evidence class | Highest cut it allows |
|---|---|
| Class 2 red flag (8-K 1.05 or 2.06) on two or more eligible names in the same 5 sessions | CAUTION (60%) |
| Official government action restricting semiconductor or technology trade that names two or more eligible issuers or their products (e.g. a Federal Register export-control rule) | CAUTION (60%) |
| SEC or exchange trading suspension of an eligible issuer's shares | SEVERE (30%) |
| Scheduled event on the calendar, with no new verified evidence | None: may be mentioned in `reason`, cannot lower the level |

- **Expiry:** an accepted CAUTION or SEVERE expires after 3 **healthy** sessions unless a new accepted assessment renews it with new evidence. Then the level returns to NORMAL (95%). A session is healthy when its assessment could be evaluated: well-formed and citing only verified, in-window evidence. An assessment that renews nothing, such as NORMAL, still counts. A session with no assessment (failure, timeout), a malformed one, or one citing unverified evidence does not count. So the last accepted cut stands for as long as the assessor is unhealthy, and an outage can never raise exposure. With the deterministic assessor, a session is healthy when the evidence input was available. (Review TRV-01, 2026-10-17: the earlier wording let three sessions of failures expire a cut and re-risk to 95%.)
- **Reduce-only:** NORMAL equals the top level, so the limiter can never raise exposure above the trend level or the risk cap.
- **No model (DEV-19 still open):** if the team declares the deterministic assessor for v1.0, the table above maps evidence to levels directly, with no model call. The schema, logging and expiry are the same.
- **Routing:** the model calls use the routing and budget of IDEA-057 if it is adopted.

### 4.3 Risk cap (declared ladder, G-22)

| Trigger | Effect |
|---|---|
| Daily loss ≥ 3% (UTC day) | No buys for the rest of the UTC day; the target may not rise above current gross; sells continue |
| Drawdown ≥ 8% from the run's equity peak | No buys; sells continue. Reset: §16 O1 |
| Drawdown ≥ 12% | Risk cap 40%: sell at once to ≤ 40% gross, skipping the minimum trade and the cadence (IDEA-016) |
| End of run | §8: no buys after `new_risk_end`, flat by `flatten_by` |

## 5. Weights and rebalancing

### 5.1 Weights

- wᵢ = (1/σᵢ) ÷ Σⱼ(1/σⱼ), where σᵢ is the standard deviation of name i's session log returns over the last 60 sessions up to the Oct 21 close (at least 20 sessions; with fewer, use the median σ of the other names).
- Cap: wᵢ ≤ 0.30. Any excess is spread over the uncapped names in proportion to their weights.
- **Computed once and frozen** in the profile at the Oct 22 parameter freeze. No re-estimation during the run (F-117), and no tuning on development P&L (ledger rule 5).
- At 95%, each name's target is 0.95 × wᵢ of equity: about 19% on average, at most 28.5%.

### 5.2 When the agent trades

These six triggers are the complete list. Nothing else causes a trade.

1. **Level change** (trend, LLM or 12% cap): move every eligible name to its new target. Sells first, then buys. Skip any leg below the minimum trade.
2. **Top-up:** if gross < target − 5 pp, and no loss control blocks buys, buy the names below their targets, largest gap first.
3. **Hard name line:** a name above **35%** of equity is sold back to its target (latch kept across settlement, as in IDEA-037 R01).
4. **Class 1 red flag** (8-K 4.02): sell that name, with no buys until the finding is corrected or withdrawn (IDEA-035).
5. **Deep cut** at 12% drawdown (§4.3).
6. **End-of-run flatten** (§8).

**No sale on drift.** A name above its target, or gross above the target, is left alone unless trigger 1, 3, 4, 5 or 6 applies. At 95% invested, price moves alone can push gross only to about 96–97%, so no gross trim line is needed.

## 6. Precedence

When rules conflict, the higher row wins:

1. Integrity and execution barriers: wallet, nonce, signer checks, `openState` false, audit delivery (unchanged; never bypassed).
2. End-of-run flatten.
3. 12% deep cut.
4. Class 1 red-flag sell.
5. Loss-control buy blocks (3% daily, 8% drawdown).
6. Class 2 buy block (5 sessions).
7. Target gross = min(trend, LLM, risk cap).
8. Top-up.

Safety actions (rows 2–4) skip the minimum trade and the one-change-per-session cadence, as in IDEA-016, but not the integrity checks.

## 7. Execution

- **When:** planned trades run in the US regular session, from open + 30 minutes to close − 15 minutes, while `openState` is true (F-95). That is when RFQ spreads are expected to be tightest; it should be checked against logged quote costs (GAP-50). Safety actions (rows 2–4 of §6) run in the next round where `openState` is true, at any hour.
- **Flow:** the kit flow, unchanged: quote → approve exactly the amount → re-quote → gas estimate → swap (DEV-16).
- **Price check:** the DEV-05 gates decide *entry* eligibility, so they apply to discretionary legs only, as the planner does today. The entry-cost cap and its impact cap apply to non-mandatory buys. The price-impact threshold applies to every non-mandatory leg: buys, top-ups and level-change sells. Mandatory actions (end-of-run flatten, 12% deep cut, Class 1 sell, and every other recorded sale requirement) bypass both, as `larp/risk/planner.py` does (`_quote_at_cap`, `ENTRY_COST_CAP`/`ENTRY_IMPACT_CAP`), so a safety sell is never stopped by an entry-style cost. Every leg, mandatory or not, still needs a valid, unexpired quote within the slippage limit, and passes the integrity checks (§6 row 1). A rejected leg is retried in a later round, at most 3 attempts per leg per session, never in a loop (F-105). (Review TRV-02, 2026-10-17: the earlier wording applied the entry gates to every leg.)
- **Order size:** one leg per name per round. The per-trade cap is at least one full position (≈ 57 USDT at 200 USDT equity × 28.5%), so most legs complete in one trade (GAP-13).
- **Minimum trade:** the gas-based minimum (IDEA-010, GAP-50). Legs below it are skipped, except safety actions.
- **Gas:** BNB top-up rounds as in DEV-21.
- **Expected count:** 5 opening buys, about 5 legs per level change, and 5 closing sells. With 0–4 level changes, about 10–30 swaps in the run. Gas ≈ 30 × $0.03 ≈ $0.9 (≈ 0.45% of 200 USDT) at the upper end (F-93). One down-and-back-up trend cycle moves 35% of equity twice, so it costs ≈ 0.1–0.4% of equity in spread at 13–56 bp per side (IDEA-012).

## 8. Run calendar (UTC)

| When | What | Source |
|---|---|---|
| Oct 22 | Parameter freeze: weights, σ inputs, thresholds, calendar of scheduled events | D-12, IDEA-009 |
| Oct 27–29 | Final activation: fresh final wallet, manifest, build frozen | F-14, F-117 |
| Oct 29 14:00 | `trade_after`: opening buys at the trend level computed from the 5 sessions before Oct 29 | IDEA-018 §4 |
| Each session close + 15 min | Trend evaluation, then LLM assessment; new target from the next session | §4 |
| Tue Nov 3 | US midterm elections: calendar entry only; cannot lower the level by itself | §4.2 |
| Nov 9 21:00 | `new_risk_end`: no buys, top-ups or level increases after this (§16 O4) | proposed here |
| Nov 10 19:00 | `flatten_start`: begin selling everything | IDEA-018 §4 |
| Nov 11 15:00 | `flatten_by`: flat. If a leg still fails, keep retrying within the rules until it fills | IDEA-035 C4 |

The run window covers 10 US sessions before the flatten: Oct 29, 30, Nov 2, 3, 4, 5, 6, 9, 10 and 11 (IDEA-054 calendar).

## 9. Logging and audit

- One ai-seeds round log per round, including hold-only and failed rounds; every broadcast swap's `tx_hash` in its round's log; approves never logged as orders (F-99, F-100, never-do #12).
- Each round's `input` holds the trend inputs (the 5 basket values, mean, r, state), the accepted LLM level with its evidence IDs, the risk-cap state and the final target.
- `cot` holds the LLM reasoning (F-102) or, in rounds without a model call, a plain statement of the rule and its inputs (F-106 (a)).
- Each order carries a one-line reason (F-34), for example: "Trend level 60%: basket 1.4% below its 5-session average; selling NVDAB to its 60% target."
- The profile, weights and calendar are hashed into the version manifest (F-61).

## 10. Failure behaviour

| Failure | Behaviour |
|---|---|
| A name's session bar is missing or stale | Trend state unchanged this session; logged |
| LLM call fails, times out, or cites unverified evidence | Previous accepted LLM level stands, and the session does not count toward its expiry (§4.2), so the level cannot rise during an outage; logged. Never raises exposure |
| `openState` false for a name | No order for that name; retried in a later round; the level change completes when it opens |
| Leg fails the price check, or the quote expires | Skipped; at most 3 attempts per leg per session |
| Swap reverts | Logged with `tx_hash`; no immediate re-send; the next round re-plans from chain state |
| BNB below the gas floor | Gas top-up round (DEV-21) |
| Process crash | Supervisor restarts the same build, which reconciles from chain before trading (DEV-14) |

## 11. Expected outcome (honest)

- Return ≈ 0.95 × the five names' move over the run, minus about 0.5–1% for costs (gas, spreads, the closing flatten), minus any whipsaw from the trend guard.
- Synthetic reference (IDEA-035 §10.2; 8%/yr premium, β 1.3, 5 bp per side; not market data, no trend guard): mean +0.16% to +0.19%, SD 5.2–5.8%, P(< −5%) 15–17%, P(> +5%) 16–19%, P(hit 8% stop) 9–12%. At 20 bp per side the mean is about −0.12% at every exposure level.
- The trend guard should cut the left tail in a falling market and costs a little in a choppy one; EXP-007 measures this on past token data before the freeze.
- The LLM limiter is expected to act rarely, only on verified adverse evidence. Its value is protection against a rare large event and auditable agentic reasoning, not expected return.
- Ranking: in a rising market this plan ranks with the invested field; in a falling one it should lose less than a static invested book. It cannot be shown before the run to make money.

## 12. Parameters (proposed; freeze by Oct 22)

| Parameter | Proposed value | Owner | How it is set |
|---|---|---|---|
| Levels (high / mid / low) | 95% / 60% / 30% | Keith | Team decision (95%); 60/30 proposed |
| Trend window and band | 5 sessions, ±1% | Keith | Declared; EXP-007 reports sensitivity but does not tune |
| Trend evaluation time | Session close + 15 min | Keegan | IDEA-054 calendar |
| σ window | 60 sessions (min 20) to Oct 21 close | Keith | Token session bars |
| Per-name weight cap | 0.30 | Keith | Proposed |
| Hard name line | 35% of equity | Keith | Proposed |
| Top-up band | target − 5 pp | Keith | Proposed |
| LLM expiry | 3 healthy sessions (§4.2) | Yao Zhu | Proposed |
| Evidence-class map | §4.2 table | Yao Zhu | Versioned predicate records and fixtures |
| Loss controls | 3% daily / 8% / 12% → 40% | — | Declared (unchanged) |
| Execution window | Open + 30 min to close − 15 min | Isaac | Proposed; check against logged quote costs |
| Attempts per leg per session | 3 | Isaac | Proposed |
| Minimum trade, per-trade cap | Gas-based minimum; cap ≥ one full position | Isaac / Keith | GAP-13, GAP-50 |
| `trade_after` / `new_risk_end` / `flatten_start` / `flatten_by` | Oct 29 14:00 / Nov 9 21:00 / Nov 10 19:00 / Nov 11 15:00 UTC | Keegan | IDEA-018, IDEA-035 C4, §16 O4 |

## 13. Tests (criteria written before any run)

- **T1 Trend-guard replay:** pre-registered in [EXP-007](EXP-007.md).
- **T2 Limiter acceptance** (synthetic fixtures; Yao Zhu):
  - L01 a cited evidence ID that is missing or unverified → output rejected, previous level stands;
  - L02 an accepted CAUTION → target = min(trend, 60%);
  - L03 NORMAL never raises the target above the trend level or the risk cap;
  - L04 CAUTION expires after 3 healthy sessions without renewal (§4.2);
  - L05 model outage → previous level stands, and the outage sessions do not count toward expiry;
  - L09 an accepted CAUTION (and, separately, SEVERE) followed by more than 3 sessions of timeouts or rejected evidence → the level stays, and the policy plans no BUY above the cut's target; after 3 healthy sessions without renewal → NORMAL;
  - L06 SEVERE on evidence that allows only CAUTION → capped at 60%;
  - L07 a scheduled calendar event alone cannot lower the level.
- **T3 Policy acceptance** (synthetic fixtures; Keith; IDEA-037 style):
  - Q01 a flat book at 95% UP builds five names to 0.95 × wᵢ;
  - Q02 UP → DOWN sells pro rata to 60%;
  - Q03 the dead band holds the state;
  - Q04 no sale on drift;
  - Q05 top-up only below target − 5 pp;
  - Q06 the 35% hard line trims to target and holds the latch;
  - Q07 the 12% deep cut beats every level;
  - Q08 the 8% stop blocks a DOWN → UP rebuy;
  - Q09 no buys after `new_risk_end`;
  - Q10 flat by `flatten_by`;
  - Q11 a Class 1 name's weight stays in cash;
  - Q12 frozen weights sum to 1 with every wᵢ ≤ 0.30;
  - Q13 every existing test passes unchanged (Q14, per-name cadence, is defined in IDEA-076);
  - Q15 a mandatory safety sell whose quote exceeds the DEV-05 impact and entry-cost limits is still planned, while its quote validity, slippage and integrity checks still apply.
- **T4 Development-wallet run:** at least one full live session on the development wallet with the frozen profile (small real trades, F-13), checked for a complete round log per round and every fill reconciled to its log. Engineering evidence only; never used to tune parameters (ledger rule 5).

## 14. Changes to existing decisions (for the deviations register, GAP-62)

| Item | Was | Now | Register |
|---|---|---|---|
| IDEA-035 B5, IDEA-037 | 80% invested, four names at 20% equal weight, top-up below 75%, hard lines 25% / 90% | Up to 95% invested, five names volatility-weighted (cap 0.30), top-up band 5 pp, hard name line 35%, no gross line. `EQUAL_WEIGHT` stays in code as the fallback profile | Update DEV-02, DEV-03 |
| G-21 (proposal: "≤ 80% gross exposure, so at least 20% stays in cash"; ≤ 4 positions; ≤ 20% per name) | Buy-time ceiling of 80% (DEV-04) | Up to 95% gross; 5 positions; up to 28.5% per name | Update DEV-04; new row for positions and per-name cap |
| D-11 (LLM assesses; only verified 8-K 4.02/1.05/2.06 may force an exit) | LLM has no exposure authority | The LLM may lower market-wide exposure on verified evidence, through the code map in §4.2; reduce-only | New DEV row |
| No trend rule in the proposal | — | Basket trend guard, 95% / 60% | New DEV row |
| IDEA-018 `new_risk_end` candidate Nov 4 21:00 UTC | — | Nov 9 21:00 UTC (§16 O4) | Terminal gates note |
| DEV-20 (event planner, OPEN) | Not built | Scheduled events are calendar context only; they cannot lower exposure without verified evidence | Update DEV-20 |

The register source is `config/release/deviations.v1.json`, rendered into plan.md §6.5 by `tools/render_deviations.py --write`. It must be updated before the Oct 26 freeze; a stale register risks the audit's "no material misrepresentation" check (F-48). Tracked in `INCOMPLETE_WORK.md`.

## 15. Build work and owners (owners as in IDEA-024)

| # | Work | Owner | By |
|---|---|---|---|
| B1 | Run EXP-007 on token bars to the Oct 16 close, after O2 is settled; record the result | Keith | Oct 19 |
| B2 | Strategy profile `TREND_GUARDED_VOL`: frozen weights, three levels, trend state machine, top-up band, 5 positions, 35% hard name line; schema bounds; T3 | Keith | Oct 24 |
| B3 | Planner: target = min(trend, LLM, risk cap); precedence as in §6; reuse the IDEA-037 R01 trim latch | Keith | Oct 24 |
| B4 | LLM limiter: output schema, evidence-class map with versioned predicate records, expiry, rejection logging; T2 | Yao Zhu | Oct 24 |
| B5 | Session-close evaluation job, execution window, `cot` / `input` fields of §9, profile and calendar in the manifest | Keegan | Oct 24 |
| B6 | Per-leg attempt limit and execution-window checks against logged quote costs | Isaac | Oct 24 |
| B7 | Deviations register rows of §14 | Keegan | Oct 26 |
| B8 | T4 development-wallet run | All | Oct 24–26 |

## 16. Open decisions for the team (before Oct 22)

- **O1 Reset of the 8% stop.** The declared ladder does not say when the buy block ends (GAP-12). With 95% exposure it fires in about 1 run in 10 (synthetic), and a DOWN → UP rebuy would then be blocked for the rest of the run. **Recommended:** lift the block when drawdown recovers below 5%. **Default if not decided:** no reset.
- **O2 Default if EXP-007 is inconclusive.** Must be settled **before** EXP-007 runs, because it is part of the pre-registered decision rule. **Recommended:** ship the trend guard as declared, since the team chose S1 for drawdown protection and its cost is bounded by one change per session. Alternative: drop it and run at 95% with the limiter and ladder only. **Decided 2026-10-19 (Keegan), before any EXP-007 run:** ship the trend guard as declared (EXP-007 PC-O2-ACCEPT-20261019).
- **O3 Five names or four.** SKHYB is the most expensive route (F-93). **Recommended:** five, since the entry-cost gate already skips a name whose buy is too expensive.
- **O4 `new_risk_end`.** **Recommended:** Nov 9 21:00 UTC, so that a trend recovery after Nov 4 can still be rebought. IDEA-018's Nov 4 candidate would freeze the book for the last four sessions.
- **O5 Scheduled events.** **Recommended:** no cut on a scheduled event alone (§4.2). Alternative: a declared CAUTION over the Nov 3 elections, at a cost of two level changes.
- **O6 Assessor.** Model or deterministic assessor for v1.0 (DEV-19). The plan works either way (§4.2).

## SP-D2 / SP-D3 — rehearsal selection and limiter mode (2026-10-18)

User-delegated decision on KMP-SIGN01: use measured EQUAL_WEIGHT on Oct20
if S1's actual inputs/frozen weights/parameters/EXP007/B4 are unqualified;
otherwise use explicitly adopted exact TREND_GUARDED_VOL profile. Profile/hash
adoption awaits real final coverage. For adopted S1 choose DETERMINISTIC limiter,
which maps verified LLM evidence to exposure levels; B4 producer remains required.
This does not settle original O6 model-vs-deterministic ASSESSOR adoption: that
retains team/trial/rights/declaration gates. No final strategy or values frozen.

Full criteria, evidence, limits and remaining owners: [SP-01](../build/SIGNED_PREREQUISITES_20261018.md).

## PC-O2-20261019 — candidate inconclusive default delivered for review

PR187, under the user's remaining-task instruction, records the concrete O2
choice RETAIN_DECLARED_TREND_GUARD if EXP007 is INCONCLUSIVE. It follows the
existing recommendation; it does not change EXP007's supported/not-supported
rules or adopt S1 parameters. Acceptance/pinning must precede the real experiment;
Keith's actual run/result, all frozen profile inputs and live acceptance remain
open. See EXP007 PC-O2-20261019. This entry records the PR candidate and does not
impersonate an owner signoff or manufacture a retrospective pre-registration.

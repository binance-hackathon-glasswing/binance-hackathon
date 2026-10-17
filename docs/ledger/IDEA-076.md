# IDEA-076 — Build the S1 trading plan (trend-guarded volatility-weighted book)

- Date / author: 2026-10-16 / Claude Code session, at the user's request ("Build the S1 trading plan"). Owners of the plan: Keith (B2, B3) and Yao Zhu (B4); reviewer Isaac.
- Status: open (criteria pre-registered; implementation follows on `claude/s1-trading-plan`).
- What: the code for the team's 2026-10-16 strategy choice, S1 at 95%. The plan is in PR #123 (`claude/sweet-tesla-dx49h0`). It was first numbered IDEA-058 and has been renumbered to IDEA-075 (PR #123), because IDEA-058 is already the Gate A record. This record builds:
  - **B2:** a profile baseline, `TREND_GUARDED_VOL`, with its own `s1` block and bounds.
  - **B3:** the policy and planner: target gross = min(trend level, LLM level), with the planner's risk ladder on top; precedence as in IDEA-075 §6; reuse of the IDEA-037 trim latch.
  - **B4 core:** the reduce-only exposure limiter. That covers its output schema, the evidence-class map, expiry and rejection, plus the deterministic path for when no model is used.
  It also adds a **per-name, per-session leg cadence** in place of the one-discretionary-swap-per-session rule, for this baseline only. A level change moves every name in one session, so the old rule would spread the five opening buys over five sessions.
- Values: every IDEA-075 §12 value is a **proposal until the Oct 22 freeze** (Keith, Yao Zhu). The code takes them from the profile; nothing here freezes them. The weights are computed by a freeze tool from token session bars at the freeze, never tuned on development P&L (ledger rule 5).
- Not in this record:
  - EXP-007, the trend-guard replay. It is NOT RUN, because this session can't reach any price history (network policy).
  - Wiring live session bars into the runtime driver. Today the driver passes no `series`, and the candle reader needs timestamp-convention evidence (DR-08). Until then the live trend guard keeps its starting state (UP), and every round says so.
  - The execution window and the per-leg attempt limit at execution level (B6, Isaac).
  - The session-close job and the round-log `input`/`cot` fields (B5, Keegan).
  - The deviations-register rows (B7).
  - Any LLM call. The limiter accepts a model's output only through the evidence check; producing that output is B4's model half.
- Links: IDEA-075 (PR #123; §4–§8, §12–§14, §16), IDEA-035, IDEA-037, IDEA-016 (cadence), IDEA-054 (calendar), IDEA-057 (routing), GAP-10, GAP-12, GAP-13, GAP-62, D-12, #55, #56.

## Pass criteria (written before any code exists)

All offline, on synthetic fixtures. A synthetic pass is not market evidence.

**Profile (B2)**
- **S01:** `TREND_GUARDED_VOL` needs a complete `s1` block, and the refusal of each defect is tested:
  - levels high > mid > low > 0, with high ≤ 95%;
  - weights for exactly the five symbols, summing to 1, each ≤ `weight_cap` ≤ 0.30;
  - `hard_name_weight` from high × cap up to 35%;
  - a top-up band in (0, 10%];
  - trend window 2–20 sessions and band 1–1000 bp;
  - LLM expiry 1–10 sessions; legs per name per session 1–5.
  The proposal's declared 80% / 20% caps still bind every other baseline unchanged.
- **S02 Weight freeze:** wᵢ ∝ 1/σᵢ over the last 60 session log returns (at least 20; with fewer, the median σ of the others); capped at `weight_cap`, with the excess spread in proportion over the uncapped names. The result sums exactly to 1 and is reproducible from the same series.

**Trend (IDEA-075 §4.1)**
- **S03:** the basket index uses equal-weight average returns; r = I_t ÷ mean(last 5 I) − 1.
  - r > +band gives UP; r < −band gives DOWN; inside the band the state holds.
  - A first evaluation inside the band starts UP.
  - A missing or stale bar for any name, or a non-consecutive session, leaves the state unchanged and is reported.
  - Each completed session is evaluated at most once.
- **S04:** without series (today's live driver), the state stays at its start (UP) and the round reports `TREND_INPUT_UNAVAILABLE`.

**Limiter (IDEA-075 §4.2, T2)**
- **L01** A cited evidence ID that is missing or unverified: the output is rejected and the previous level stands.
- **L02** An accepted CAUTION: target = min(trend, 60%).
- **L03** NORMAL never raises the target above the trend level.
- **L04** CAUTION expires after the expiry sessions without renewal.
- **L05** A model outage (no output): the previous level stands until expiry.
- **L06** SEVERE on evidence that allows only CAUTION is capped at 60%.
- **L07** A scheduled-event entry alone cannot lower the level.
- **L08** In deterministic mode, the evidence-class map alone sets the level: Class 2 on two or more names within 5 sessions gives CAUTION; a verified suspension gives SEVERE.

**Policy and planner (IDEA-075 §5–§6, T3)**
- **Q01** A flat book at 95% UP builds the five names to 0.95 × wᵢ, at most one leg per name per round, sells before buys.
- **Q02** UP → DOWN sells every name toward 0.60 × wᵢ.
- **Q03** The dead band holds the state.
- **Q04** No sale on drift: a name above its target with no trigger is kept.
- **Q05** A top-up happens only when gross < target − band, buying the largest gaps first.
- **Q06** The 35% hard name line trims to target and holds the latch across settlement.
- **Q07** The 12% deep cut sells to ≤ 40% gross ahead of every level.
- **Q08** The 8% stop blocks a DOWN → UP rebuy (no reset by default, IDEA-075 §16 O1).
- **Q09** No buys or level increases after `new_risk_end`; level decreases still sell.
- **Q10** Exits only from `flatten_start`.
- **Q11** A Class 1 name's weight stays in cash (no redistribution).
- **Q12** The cash floor is 1 − high level (5%), not 20%; five positions allowed.
- **Q13** Every existing test passes unchanged, which covers EQUAL_WEIGHT and the other baselines.
- **Q14 Cadence.** For this baseline, at most `max_legs_per_symbol_session` discretionary swaps per name per session. The count comes from the settlement record and survives replay. The other baselines keep one discretionary swap per session.

**Live profile (DR-09)**
- **S05:** `build_live_profiles(..., s1=...)` produces REHEARSAL and FINAL `TREND_GUARDED_VOL` profiles that pass `validate_live`:
  - the per-trade cap covers one full top-level position;
  - the exit gas reserve covers five positions;
  - provenance marks the §12 values as proposals, pending the Oct 22 freeze.
  The EQUAL_WEIGHT profiles are unchanged.

**No regressions**
- **R:** full suite green against the baseline at `eda2ed2`: 1751 passed, 10 skipped (Python 3.13.16, PostgreSQL 16.15, this session).

## Results
- 2026-10-16: criteria pushed at `504c266` before any code. Code at `c430b6e` (core), `d34f003` (policy, planner, cadence) and `b5c8683` (LIVE profiles).
- Environment: Python 3.13.16, the locked subset without ML packages, PostgreSQL 16.15. CI (Python 3.12, PostgreSQL 14.24) has not run on this branch.
- **S01 PASS:** a valid block is accepted, and 18 defect cases are refused (`tests/strategy/test_s1_core.py` ProfileBlock). The other baselines still pass the proposal's declared caps (the existing tests are unchanged and green).
- **S02 PASS:** inverse volatility; the calmest name is capped at 30% and the excess spread over the rest; the sum is exactly 1; reproducible; median sigma substituted for short history; refused with no history.
- **S03 PASS:** rising gives UP; falling gives DOWN; the exact signal on a known path; the dead band holds; the first evaluation starts UP (or the configured start); each session is evaluated once; a bar counts only after the delay; a missing session, a stale input, a missing name or a bad bar each hold the state.
- **S04 PASS:** without series the state starts UP and the round reports `TREND_INPUT_UNAVAILABLE` (Q01 also checks this through the policy).
- **L01–L08 PASS** (`Limiter`), plus a malformed assessment being rejected. The renewal rule only accepts new evidence of a class that can give the cut, so a new calendar entry cannot renew one (L07).
- **Q01–Q12 PASS** (`tests/strategy/test_s1_plan.py`).
  - Q01: build at 19% per name.
  - Q02: UP → DOWN sells to 12%.
  - Q03: dead band.
  - Q04: no sale on drift; Q05: top-up below 90% only, largest gap first.
  - Q06: the 35% line trims to 19% and holds the latch at 30%.
  - Q07: deep cut to 40%; no gross trim at 97%.
  - Q08: the stop blocks a rebuy.
  - Q09: after `new_risk_end`, no buys but cuts still sell.
  - Q10: terminal exit.
  - Q11: a Class 1 name's weight stays in cash.
  - Q12: fifth position allowed with a 5% floor.
  - Also: a limiter CAUTION lowers every target, and a rebalance ends once every name is at target.
- **Q13 PASS:** existing tests unchanged; EQUAL_WEIGHT keeps one discretionary swap per session.
- **Q14 PASS:** the per-name leg budget ignores the old session rule and refuses the fourth leg; settlement counts legs per name and resets them each session, for S1 only; the runtime context reads only the current session.
- **S05 PASS:** REHEARSAL and FINAL S1 profiles pass `validate_live`, with a per-trade cap of one full top position plus reserve and an exit reserve for five positions; provenance says "proposed"; S1 defects are refused; EQUAL_WEIGHT profiles are unchanged.
- **R PASS:** full suite 1797 passed, 10 skipped, 0 failed, 2577 subtests (532.9 s), against 1751 / 10 at `eda2ed2`. The difference is the 46 new tests.
- **Differences from the plan:**
  - The rebalance completes per name once within one minimum trade of target, so legs smaller than the minimum are skipped, as IDEA-075 §5.2 says.
  - Hard-line trims go to min(top level × w, the current target).
  - The S1 LIVE profiles keep the builder's existing windows (FINAL: new risk ends Nov 9 00:00, flatten Nov 10 00:00, signing ends Nov 11 14:45 UTC) rather than IDEA-075 §8's proposed Nov 9 21:00 / Nov 10 19:00. That is IDEA-075 §16 O4, for the team.
- **Still open, with owners:**
  - Keith + Yao Zhu: freeze the IDEA-075 §12 values and §16 O1–O6 by Oct 22; run `python -m larp.strategy.s1 freeze-weights` on token session bars to Oct 21; build the profiles with `s1=` and the decision ID.
  - Keith: EXP-007 (NOT RUN here; no price data reachable).
  - DR-08: wire live session bars into the runtime driver; until then the live trend guard stays UP.
  - Yao Zhu: produce `exposure_evidence` and `exposure_assessment` from the evidence pipeline (B4's model half); until then the limiter sees no evidence and stays NORMAL.
  - Isaac: execution window and attempt limit (B6).
  - Keegan: round-log fields (B5) and the deviations-register rows (B7).

## Review fixes (2026-10-17, PR #131 review)

- **R1 (criterion written before the fix):** a level change ends per name. A name leaves the rebalance once a round finds it within one minimum trade of its target (or its buy gates closed), and after that it is only topped up, never sold on drift, even while another name's leg is still open. The failure it prevents: one name whose buy the planner keeps refusing (for example the entry-cost gate on SKHYB, IDEA-075 §16 O3) kept the whole book in rebalance mode, so every other name was sold back whenever it drifted one minimum trade above target. Pass: `test_a_name_whose_rebalance_completed_is_not_sold_on_drift` (NVDAB at 25% is held while SKHYB still rebalances) passes, it fails on the code before the fix, and every other test passes unchanged.
- **R1 PASS:** the test failed at `133575e` (NVDAB got an `S1_LEVEL_CHANGE` sell) and passes with the fix at `45445f8`. The policy state's `rebalance` is now the sorted list of names still rebalancing (a stored `true` from the old flag means the whole book). Names a round does not reach (blocked, unmarked) keep their place, so a cut still reaches them once they return. A name that has completed can be topped up while another is still rebalancing; before the fix no top-up ran during a rebalance.
- Full suite at `45445f8` (after merging `codex/system-testing-20261012` at `02f02ee`): **1811 passed, 10 skipped, 0 failed**, 2622 subtests (Python 3.13.16, PostgreSQL 16.15 local, ML packages left out, `deploy/requirements-{signer,runtime,aws}.lock` installed). Before the fix, at `dbab2e0`, the same environment gave 1810 passed, 10 skipped. The difference from 1797 / 10 is the merged base's tests plus the R1 test. `test_service_configs` M01 fails if the deploy locks are not installed; it fails the same way on the base branch.
- Checked in the review with no change needed: the weight freeze (20,000 random sigma sets and caps: every result sums to exactly 1, with each weight in (0, cap]); the trend dead band and the handling of stale, missing and already-evaluated inputs; limiter expiry and renewal; leg counting (one swap attempt per intent, observations deduplicated by event ID, the count comes back from the journal on replay); the 5% cash floor; the 35% line and its latch; sells before buys; EQUAL_WEIGHT and the other baselines unchanged.
- Noted, not fixed (no realistic path today, or a bounded effect):
  - A swap planned in session k but broadcast in session k+1 counts against session k, so k+1 can allow one extra leg for that name. Unlike `last_discretionary_session`, the count does not use the broadcast time.
  - `_verified` catches only `ContractError` and `KeyError`. An evidence item with unhashable `symbols` raises `TypeError` and fails the round closed. Nothing produces `exposure_evidence` yet (B4's model half, Yao Zhu), so the producer should validate.
  - The research fixture context has no `discretionary_legs`, so the planner does not enforce the leg budget there. Research only.
  - A held name under a Class 2 entry block takes the blocked branch (`KEEP_QUANTITY`), so a level cut does not reach it while the block lasts. With R1 it stays in the rebalance and is cut once the block ends.

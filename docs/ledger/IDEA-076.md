# IDEA-076 — Build the S1 trading plan (trend-guarded volatility-weighted book)

- Date / author: 2026-10-16 / Claude Code session, at the user's request ("Build the S1 trading plan"). Owners of the plan: Keith (B2, B3) and Yao Zhu (B4); reviewer Isaac.
- Status: open (criteria pre-registered; implementation follows on `claude/s1-trading-plan`).
- What: the code for the team's 2026-10-16 strategy choice, S1 at 95%. The plan is in PR #123 (`claude/sweet-tesla-dx49h0`), where it is numbered IDEA-058 and is proposed for renumbering to IDEA-075, because IDEA-058 is already the Gate A record. This record builds:
  - **B2:** a profile baseline, `TREND_GUARDED_VOL`, with its own `s1` block and bounds.
  - **B3:** the policy and planner: target gross = min(trend level, LLM level), with the planner's risk ladder on top; precedence as in the plan's §6; reuse of the IDEA-037 trim latch.
  - **B4 core:** the reduce-only exposure limiter. That covers its output schema, the evidence-class map, expiry and rejection, plus the deterministic path for when no model is used.
  It also adds a **per-name, per-session leg cadence** in place of the one-discretionary-swap-per-session rule, for this baseline only. A level change moves every name in one session, so the old rule would spread the five opening buys over five sessions.
- Values: every §12 value is a **proposal until the Oct 22 freeze** (Keith, Yao Zhu). The code takes them from the profile; nothing here freezes them. The weights are computed by a freeze tool from token session bars at the freeze, never tuned on development P&L (ledger rule 5).
- Not in this record:
  - EXP-007, the trend-guard replay. It is NOT RUN, because this session can't reach any price history (network policy).
  - Wiring live session bars into the runtime driver. Today the driver passes no `series`, and the candle reader needs timestamp-convention evidence (DR-08). Until then the live trend guard keeps its starting state (UP), and every round says so.
  - The execution window and the per-leg attempt limit at execution level (B6, Isaac).
  - The session-close job and the round-log `input`/`cot` fields (B5, Keegan).
  - The deviations-register rows (B7).
  - Any LLM call. The limiter accepts a model's output only through the evidence check; producing that output is B4's model half.
- Links: PR #123 (plan §4–§8, §12–§14, §16), IDEA-035, IDEA-037, IDEA-016 (cadence), IDEA-054 (calendar), IDEA-057 (routing), GAP-10, GAP-12, GAP-13, GAP-62, D-12, #55, #56.

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

**Trend (plan §4.1)**
- **S03:** the basket index uses equal-weight average returns; r = I_t ÷ mean(last 5 I) − 1.
  - r > +band gives UP; r < −band gives DOWN; inside the band the state holds.
  - A first evaluation inside the band starts UP.
  - A missing or stale bar for any name, or a non-consecutive session, leaves the state unchanged and is reported.
  - Each completed session is evaluated at most once.
- **S04:** without series (today's live driver), the state stays at its start (UP) and the round reports `TREND_INPUT_UNAVAILABLE`.

**Limiter (plan §4.2, T2)**
- **L01** A cited evidence ID that is missing or unverified: the output is rejected and the previous level stands.
- **L02** An accepted CAUTION: target = min(trend, 60%).
- **L03** NORMAL never raises the target above the trend level.
- **L04** CAUTION expires after the expiry sessions without renewal.
- **L05** A model outage (no output): the previous level stands until expiry.
- **L06** SEVERE on evidence that allows only CAUTION is capped at 60%.
- **L07** A scheduled-event entry alone cannot lower the level.
- **L08** In deterministic mode, the evidence-class map alone sets the level: Class 2 on two or more names within 5 sessions gives CAUTION; a verified suspension gives SEVERE.

**Policy and planner (plan §5–§6, T3)**
- **Q01** A flat book at 95% UP builds the five names to 0.95 × wᵢ, at most one leg per name per round, sells before buys.
- **Q02** UP → DOWN sells every name toward 0.60 × wᵢ.
- **Q03** The dead band holds the state.
- **Q04** No sale on drift: a name above its target with no trigger is kept.
- **Q05** A top-up happens only when gross < target − band, buying the largest gaps first.
- **Q06** The 35% hard name line trims to target and holds the latch across settlement.
- **Q07** The 12% deep cut sells to ≤ 40% gross ahead of every level.
- **Q08** The 8% stop blocks a DOWN → UP rebuy (no reset by default, plan §16 O1).
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

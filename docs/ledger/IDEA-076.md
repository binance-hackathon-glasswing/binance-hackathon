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
- **L04** CAUTION expires after the expiry sessions without renewal. *(2026-10-17: counted in healthy sessions since R2; see L09.)*
- **L05** A model outage (no output): the previous level stands until expiry. *(Superseded 2026-10-17 by L09 / R2: an outage does not count toward expiry, so the level stands for as long as the outage lasts.)*
- **L06** SEVERE on evidence that allows only CAUTION is capped at 60%.
- **L07** A scheduled-event entry alone cannot lower the level.
- **L08** In deterministic mode, the evidence-class map alone sets the level: Class 2 on two or more names within 5 sessions gives CAUTION; a verified suspension gives SEVERE.
- **L09** (added 2026-10-17, R2, review TRV-01) An accepted cut expires after `llm_expiry_sessions` *healthy* sessions without renewal. A session with no assessment, a malformed one or one citing unverified evidence does not count (DETERMINISTIC: one without an evidence input). An assessor outage never raises exposure. Criterion and tests under Review fixes.

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
- **Q15** (added 2026-10-17, R3, review TRV-02) Under the S1 profile a mandatory safety sell is exempt from the impact threshold and the DEV-05 cost limits; its quote validity, slippage, expiry and LIVE-origin checks still apply. Criterion and test under Review fixes.

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
- **L01–L08 PASS** (`Limiter`), plus a malformed assessment being rejected. The renewal rule only accepts new evidence of a class that can give the cut, so a new calendar entry cannot renew one (L07). *(2026-10-17: the expiry rule changed to healthy sessions in R2; L04, L05 and L07 were updated with it, and L09 was added.)*
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
- Checked in the review with no change needed: the weight freeze (20,000 random sigma sets and caps: every result sums to exactly 1, with each weight in (0, cap]); the trend dead band and the handling of stale, missing and already-evaluated inputs; limiter expiry and renewal (expiry later changed by R2, review TRV-01); leg counting (one swap attempt per intent, observations deduplicated by event ID, the count comes back from the journal on replay); the 5% cash floor; the 35% line and its latch; sells before buys; EQUAL_WEIGHT and the other baselines unchanged.
- Noted, not fixed (no realistic path today, or a bounded effect):
  - A swap planned in session k but broadcast in session k+1 counts against session k, so k+1 can allow one extra leg for that name. Unlike `last_discretionary_session`, the count does not use the broadcast time.
  - `_verified` catches only `ContractError` and `KeyError`. An evidence item with unhashable `symbols` raises `TypeError` and fails the round closed. Nothing produces `exposure_evidence` yet (B4's model half, Yao Zhu), so the producer should validate.
  - The research fixture context has no `discretionary_legs`, so the planner does not enforce the leg budget there. Research only.
  - A held name under a Class 2 entry block takes the blocked branch (`KEEP_QUANTITY`), so a level cut does not reach it while the block lasts. With R1 it stays in the rebalance and is cut once the block ends.

### PR #123 review: TRV-01, TRV-02 (2026-10-17, wtvlol)

The plan text changes in PR #123 (IDEA-075 §4.2 and §13: L09, Q15). These are the matching code criteria, written and pushed before the fixed code runs.

- **R2 (TRV-01, P1; criterion L09): an assessor outage never raises exposure.**
  - Rule (IDEA-075 §4.2 as rewritten): an accepted cut expires after `llm_expiry_sessions` *healthy* sessions without renewal. A session is healthy when its assessment was accepted for evaluation: well-formed and citing only verified in-window evidence. An assessment that renews nothing, such as NORMAL, still counts. Sessions with no assessment (`NO_ASSESSMENT`), a malformed one (`MALFORMED_ASSESSMENT`) or one citing unverified evidence (`UNVERIFIED_OR_OUT_OF_WINDOW_EVIDENCE`) do not count, so the last accepted cut stands for as long as the assessor is unhealthy. In DETERMINISTIC mode a session is healthy when the evidence input was present (not None).
  - The failure it prevents: today an accepted CAUTION (60%) or SEVERE (30%) lapses at `session + expiry` even if every assessment in between failed. A continuous outage then takes the target back to 95%, and the level-change trigger buys. Run against the code before the fix, the synthetic policy chain in `test_l09_an_assessor_outage_never_rebuys_above_the_cut` plans `S1_LEVEL_CHANGE` BUYs (first GOOGLB) at session 83, three sessions after a CAUTION accepted at 80 with no usable output since.
  - Constraints: each session is counted at most once (`limiter_step` can run more than once per session), and the acceptance session does not count. The reduce-only and renewal rules are unchanged. The count lives in the persisted policy state (`s1.limiter`), like the current state. A state stored before the rule (only `expires_session`) still loads.
  - Pass: these tests fail on the code before the fix and pass after it, and every other test passes (L04, L05 and L07 are updated to the healthy-session count):
    - `tests/strategy/test_s1_core.py` `Limiter`:
      - `test_l09_an_outage_never_expires_a_caution` (3 × expiry sessions of timeouts, malformed and unverified outputs: still CAUTION);
      - `test_l09_caution_expires_after_expiry_healthy_sessions` (then exactly `expiry` healthy, non-renewing sessions: NORMAL, and not one session earlier);
      - `test_l09_severe_holds_through_an_outage_and_expires_when_healthy`;
      - `test_l09_deterministic_mode_counts_only_sessions_with_an_evidence_input`;
      - `test_l09_a_session_is_counted_once` (repeated calls in one session, and in the acceptance session);
      - `test_l09_a_state_stored_before_the_rule_still_loads`.
    - `tests/strategy/test_s1_plan.py` `test_l09_an_assessor_outage_never_rebuys_above_the_cut`: through the policy and planner, nine outage sessions after an accepted CAUTION leave the applied target at 60%, plan no target above 0.60 × w and no BUY intent or BUY quote request.
  - Found while writing these tests, and in R2's scope: `allowed_severity` read its input twice, and in MODEL mode that input is a generator. Only the Class 2 rule saw the evidence, so a cited suspension (SEVERE) or two-name restriction (CAUTION) was never accepted. DETERMINISTIC mode passes a re-readable view and was not affected. Pass: `test_l09_model_mode_accepts_suspension_and_restriction_evidence` fails before the fix and passes after it.
- **R3 (TRV-02, P1; criterion Q15): mandatory safety sells keep their exemptions under S1.**
  - Rule: mandatory actions (planner `requirements`: flatten, 12% deep cut, Class 1, reduction constraints, hard-line trims) are exempt from the impact threshold (`_quote_at_cap`: `mandatory or impact <= impact_bps`), from the cost-reserve veto, and from `ENTRY_COST_CAP` / `ENTRY_IMPACT_CAP` (non-mandatory BUY only). These are the DEV-05 limits. Quote validity (route, quote ID, availability, age), slippage, minimum receive, expiry and the LIVE `WEB3_OPEN_API` origin check still apply.
  - Check: the S1 changes to `larp/risk/planner.py` (the diff against `codex/system-testing-20261012`) do not touch `_quote_at_cap`, the cost-reserve veto or the entry caps. S1 changes only the limits, the leg budget, the sell-first order and the cash floor.
  - Pass: `tests/strategy/test_s1_plan.py` `Planner.test_q15_a_mandatory_safety_sell_ignores_impact_and_cost_limits_but_not_quote_checks` passes. On a LIVE FINAL S1 profile, a Class 1 exit whose quote has impact above `impact_bps` and a cost above both the 50 bp entry cap and the cost reserve is planned as a mandatory SELL. In each of six subtests (slippage over the limit, expired, stale, invalid route, non-Web3 origin, minimum receive below the slippage floor) the same sell is not sent, and the requirement stays `BLOCKED_QUOTE` with `max_units` 0. As a check that the test can fail: removing the `mandatory` exemption from the impact check, or from the cost-reserve veto, makes it fail. If S1 had broken the bypass, the fix would be the minimal one that restores it.
- **Results (2026-10-17):** the criteria and tests were pushed at `4f32319` (after merging `codex/system-testing-20261012` at `b547646`), before the fix. The fix is at `eadb72b`.
  - **R2 PASS.** Before the fix, at `4f32319`, six of the seven new `Limiter` L09 tests and the policy chain test failed. In the policy chain, the CAUTION accepted at session 80 lapsed at 83, and the round planned `S1_LEVEL_CHANGE` BUYs, the first for GOOGLB. `test_l09_a_session_is_counted_once` passed on the old code as well, because a clock expiry also counts each session once. It now pins the count. After the fix all eight pass, and so do the updated L04, L05 and L07 tests.
  - What changed: `limiter_step` keeps `healthy_sessions` (healthy sessions counted since the cut was accepted or renewed) and `counted_session` (the last session counted, or the acceptance session) in `s1.limiter`, in place of `expires_session`. The state is persisted and replayed with the policy state as before. A session counts toward expiry when it is healthy and later than `counted_session`. The cut lapses when the count reaches `llm_expiry_sessions`, which is checked before acceptance, so that session can still accept a new cut as before. An acceptance or renewal resets the count to 0 at that session. The round record (`s1_round.limiter`) now carries `healthy` and `healthy_sessions` in place of `expires_session`.
  - State compatibility: a stored state with only `expires_session` E loads as a cut accepted at E − `llm_expiry_sessions` with no healthy session counted. It now lapses only after that many healthy sessions, never on the clock alone. A cut without a usable E needs a full `llm_expiry_sessions` healthy sessions. A stored NORMAL state is unaffected. The test fixture `settled()` still writes the old shape, so the policy path loads it on every S1 plan test.
  - The policy now passes an absent `exposure_evidence` as None rather than `[]`, so in DETERMINISTIC mode a round without the evidence input is not healthy. Nothing produces the input yet (B4's model half, Yao Zhu), and until something does the limiter stays NORMAL.
  - `allowed_severity` now reads its input into a list.
- **R3 PASS.** No code change was needed: S1 did not change the mandatory bypass. `test_q15_a_mandatory_safety_sell_ignores_impact_and_cost_limits_but_not_quote_checks` passes, with its 6 subtests. It fails when the `mandatory` exemption is removed from the impact check, or from the cost-reserve veto (each change was tried locally and reverted).
- Full suite at `eadb72b`: **1820 passed, 10 skipped, 0 failed**, 2628 subtests, 259.9 s. The environment was Python 3.13.16 and a throwaway PostgreSQL 16.15 cluster under /tmp. `deploy/requirements-{signer,runtime,aws,test}.lock` were installed and the ML packages left out. Against the previous 1811 passed / 10 skipped, the difference is the 9 new tests (7 in `Limiter`, the L09 policy chain and Q15). `git diff --check` is clean.


## RV-131 — Isaac-requested review and merge (2026-10-17, prospective)

Review head `4b87036` against current integration `5f16784` (includes PR130); ordinary merge retains current IDEA080, IDEA070, IDEA075, EXP007 and IDEA076 rows. This reviews S1 B2/B3/B4 core only; all §12 choices remain proposed, EXP007 is not run, live series/model evidence, B5/B6/B7 and host/rehearsal gates remain open. No new market experiment or activation is authorized.

Criteria before running regressions:
- **R4:** Class2 is an entry-only block. S1 must still emit a SELL toward a reduced target for a held Class2-blocked name; it must never buy that name. Other baselines and Class1/reduction/terminal precedence remain unchanged. Rebalance tracking must retain any unfilled cut.
- **R5:** the independent planner bounds each symbol by `high * its frozen weight`, not `high * the maximum permitted weight`. A proposal above its own frozen allocation cannot produce an oversized buy even when below the global 30% weight cap.
- **R6:** malformed deterministic evidence (non-list, malformed/unhashable items, duplicate/conflicting IDs) is not a healthy session and cannot expire a prior cut. A valid empty input can count as healthy; valid new adverse evidence still lowers exposure. MODEL invalid evidence fails closed without crashing.
- **R7:** the offline profile CLI must support explicitly selecting a supplied S1 block plus a named decision, hash-bind that block in provenance and keep EQUAL_WEIGHT as the default. Invalid/missing paired arguments or bad block fail without generating a profile; no overwrite of existing profiles.
- **R8:** weight freeze validates `2 <= minimum <= window`, a positive integer scale and a dict series input. Invalid arguments raise ContractError, not decimal division errors or zero weights. Returned weights must be strictly positive, sum to1 and respect the cap. Missing-history substitution is kept and reported; real candle/timestamp/source qualification remains DR08.
- **R9:** push criteria/tests before RED, fixes before GREEN. Focused S1/strategy/risk/integration and full synthetic disposable-PostgreSQL regression must pass; report skips/environment and current Actions billing limitation honestly. No .env/keys, API/model calls, real prices, transactions, AWS or receiver use.

R8 clarification before the freeze fix: “last window sessions” is a session-index horizon, not the last window observed adjacent pairs drawn across arbitrary gaps. A name with 26 old bars and only6 recent bars separated by75 missing sessions cannot borrow the old returns to meet a20-return minimum. Its sigma must be substituted and reported. Add that regression before execution. RED at pushed8dc60d3 already reproduces R4/R5/R6/R7 and invalid R8 arguments (14 failed /7 passed /2 subtests passed).

RV-131 history RED at pushedf63ef4a: old pre-gap returns incorrectly avoided median substitution (1 failed). R4 also retains blocked/unfilled buys in the rebalance set; allowing a held entry-blocked name to reach S1 processing must not drop its pending buy. R6 treats a deterministic input as healthy only when the entire list resolves to unique verified in-window items; malformed symbols are caught without crashing. This is conservative failure handling, not a new exposure choice.

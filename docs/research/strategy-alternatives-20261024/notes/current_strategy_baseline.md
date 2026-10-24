# LARP current trading strategy baseline: S1 (TREND_GUARDED_VOL), EQUAL_WEIGHT fallback, S2 weekend test — parameters, evidence, cost handling and what can change before the freeze

_Source: the team repository only, branch `codex/system-testing-20261012` at commit `59c878c0` (2026-10-24 18:32 +08:00), read-only. Every link below is a repo-relative path at that commit, with line numbers as `path:line`. Labels follow `docs/skill/SKILL.md` §0.1: F = official/organiser fact, G[RULE]/G[RULE-DERIVED]/G[POLICY] = guardrail tags, POLICY = team choice. "Offline" = synthetic tests, simulations or quote captures; "live" = signed dev-wallet transactions on BSC mainnet._

---

## 1. Which strategies can the agent run, and which one is planned for the scored run?

### Takeaway
The code knows four baselines, but a LIVE profile can only be `EQUAL_WEIGHT` or `TREND_GUARDED_VOL` (S1). The team's decided scored-run strategy is S1 at up to 95% gross (IDEA-084 PF-01). EQUAL_WEIGHT is the declared fallback if S1 fails qualification. S2 is a dev-only weekend test profile and is barred from FINAL. Yao is due to re-decide "S1 or another version" on Monday Oct 26 (IDEA-089). At 59c878c0, S1's trend guard gets no live price series, so it stays at its start state (UP). The limiter can only see Class 2 filings. The decided 8%-stop recovery is not implemented. No FINAL S1 profile or frozen weights exist yet.

### Cited Findings

**Strategy inventory and status**
- Baselines accepted by profile validation: `DECLARED_EXPOSURE`, `PRICE_MOMENTUM`, `EQUAL_WEIGHT`, `TREND_GUARDED_VOL` — [larp/strategy/schema.py:79-80](larp/strategy/schema.py). `validate_live` refuses any LIVE profile whose baseline is not `EQUAL_WEIGHT` or `TREND_GUARDED_VOL`, or whose `series_kind` is not TOKEN — [larp/strategy/profiles.py:109-116](larp/strategy/profiles.py).
- Decision for the final: "Choose **TREND_GUARDED_VOL / S1**, up to **95% gross** … Prefer qualified S1; preserve SP-D2's measured EQUAL_WEIGHT rehearsal fallback if S1 inputs/wiring fail qualification. That fallback is not five-name 95% S1." These are delegated team POLICY choices by Isaac (2026-10-21), not organiser rules — [docs/ledger/IDEA-084.md:40-58](docs/ledger/IDEA-084.md), [docs/ledger/IDEA-084.md:4-9](docs/ledger/IDEA-084.md).
- The S1 family choice came from a team decision on 2026-10-16 (strategy S1 at 95%) — [docs/ledger/IDEA-075.md:12-21](docs/ledger/IDEA-075.md).
- Pending re-decision: "After the test (Monday) Yao chooses the strategy for the next run and the final: S1 or another version (EXP-008 questions the trend guard)… S2 is never used for the final run." — [docs/ledger/IDEA-089.md:85-89](docs/ledger/IDEA-089.md).
- S1 is described as a drawdown control, not a source of edge: "The trend guard and the limiter are there to cut drawdown in a falling market… Neither is a source of edge." — [docs/ledger/IDEA-075.md:8](docs/ledger/IDEA-075.md).

**S1 rules (code)**
- *Target:* target gross = min(trend level, limiter level). NORMAL equals the high level, so the limiter can only lower exposure — [larp/strategy/s1.py:6-7](larp/strategy/s1.py), [larp/strategy/s1.py:89-93](larp/strategy/s1.py). Each name's target is `level × w_i × (E − cost_reserve)` — [larp/strategy/policy.py:193-194](larp/strategy/policy.py).
- *Weights:* w ∝ 1/σ of session log returns over the last `window`=60 sessions with at least `minimum`=20 returns. A name with too little history takes the median σ of the others. Weights are capped at `weight_cap`, with the excess spread pro rata by iteration. They are rounded to 1/1,000,000 and sum exactly to 1. They are frozen once into the profile, not re-estimated in the run — [larp/strategy/s1.py:269-330](larp/strategy/s1.py), [docs/ledger/IDEA-075.md:84-89](docs/ledger/IDEA-075.md). The profile block requires positive weights for all five symbols, each ≤ cap, summing to exactly 1 — [larp/strategy/s1.py:61-66](larp/strategy/s1.py).
- *Trend guard:* an equal-weight basket index I_t = I_{t−1} × (1 + mean of the five session returns). The signal is r = I_t ÷ mean(last `trend_window_sessions` values of I) − 1. r > +band → UP (high level); r < −band → DOWN (mid level); inside the band the state is unchanged. A first evaluation inside the band takes `trend_start_state` — [larp/strategy/s1.py:142-158](larp/strategy/s1.py). Missing, stale or already-evaluated input leaves the state unchanged (`TREND_INPUT_UNAVAILABLE`/`STALE`/`MISSING`/`ALREADY_EVALUATED`) — [larp/strategy/s1.py:127-144](larp/strategy/s1.py). A bar counts only `trend_delay_seconds` after its close — [larp/strategy/s1.py:115](larp/strategy/s1.py). The plan's setting: 5 sessions, ±1%, 95%/60%, evaluated at close + 15 min — [docs/ledger/IDEA-075.md:41-52](docs/ledger/IDEA-075.md).
- *Limiter (reduce-only):* verified evidence counts only inside a 5-session window (`EVIDENCE_WINDOW_SESSIONS = 5`) — [larp/strategy/s1.py:32](larp/strategy/s1.py), [larp/strategy/s1.py:163-177](larp/strategy/s1.py). Class map: Class 2 red flag on ≥2 eligible names → CAUTION (mid); a TRADE_RESTRICTION naming ≥2 names → CAUTION; a TRADING_SUSPENSION → SEVERE (low); a SCHEDULED_EVENT can never cut — [larp/strategy/s1.py:180-195](larp/strategy/s1.py), [docs/ledger/IDEA-075.md:61-66](docs/ledger/IDEA-075.md). An accepted cut lapses only after `llm_expiry_sessions` *healthy* sessions without renewal, so an assessor outage never re-risks — [larp/strategy/s1.py:211-264](larp/strategy/s1.py), [docs/ledger/IDEA-076.md:176-199](docs/ledger/IDEA-076.md). In DETERMINISTIC mode the class map alone sets the level, with no model call — [larp/strategy/s1.py:223-225](larp/strategy/s1.py).
- *Trade triggers (policy):* a level change moves every eligible name in the rebalance set to level × w. It sells when gap ≤ −minimum trade and buys when gap ≥ minimum trade and the entry gates pass. Otherwise a name is topped up only when gross < level − `top_up_band` and its gap ≥ minimum trade. Nothing is sold on drift — [larp/strategy/policy.py:186-215](larp/strategy/policy.py), [docs/ledger/IDEA-075.md:91-102](docs/ledger/IDEA-075.md). The rebalance ends per name (review fix R1) — [docs/ledger/IDEA-076.md:162-163](docs/ledger/IDEA-076.md).
- *Planner:* S1 uses gross limit = high level, five positions, the S1 hard name line and no gross trim line except the 12% deep cut — [larp/risk/planner.py:181-203](larp/risk/planner.py). A name over the hard line is sold back to min(applied level, current target) × w — [larp/risk/planner.py:244-262](larp/risk/planner.py). Discretionary per-name cap = high × w_i — [larp/risk/planner.py:351-353](larp/risk/planner.py). Sells go first, then the parent-requested leg, then the largest whole-unit notional — [larp/risk/planner.py:384-390](larp/risk/planner.py). One wallet leg (one intent or one quote request) is planned per round — [larp/risk/planner.py:452-455](larp/risk/planner.py), [larp/risk/planner.py:544](larp/risk/planner.py). The cash floor is (1 − high) of safe equity and counts free BNB — [larp/risk/planner.py:490-500](larp/risk/planner.py). A per-name, per-session discretionary leg budget (`max_legs_per_symbol_session`) replaces EQUAL_WEIGHT's one-swap-per-session rule — [larp/risk/planner.py:370-380](larp/risk/planner.py).
- *Loss ladder (declared in the proposal; enforced in code):* `run_halt` latches at equity ≤ 92% of peak (8% drawdown); `deep_cut` latches at ≤ 88% (12%); `daily_halt` at ≤ 97% of the UTC-day anchor (3%) — [larp/risk/accounting.py:26-38](larp/risk/accounting.py). `daily_halt` resets only at the next midnight anchor — [larp/risk/accounting.py:12-23](larp/risk/accounting.py). The deep cut sets the gross limit to 40% — [larp/risk/planner.py:194-195](larp/risk/planner.py). Any halt blocks BUYs (`NEW_RISK_HALTED`) — [larp/risk/planner.py:357-363](larp/risk/planner.py). Declared values (3%/8%/12%→40%) — [docs/skill/larp/plan.md:51](docs/skill/larp/plan.md).
- *Execution windows and attempts (B6):* discretionary legs only in [session open + `open_delay_seconds`, close − `close_buffer_seconds`). Mandatory sells use open → next open — [larp/strategy/execution_bounds.py:99-105](larp/strategy/execution_bounds.py). The attempt budget per (lane, side, symbol) per session is capped at `max_attempts_per_leg_session` — [larp/strategy/execution_bounds.py:156-170](larp/strategy/execution_bounds.py). The bounds are re-checked at execution and in the signer — [larp/strategy/execution_bounds.py:182-223](larp/strategy/execution_bounds.py), [docs/build/S1_EXECUTION_BOUNDS.md:27-37](docs/build/S1_EXECUTION_BOUNDS.md). Every order also requires kit `openState` true for both token and underlying (`MARKET_CLOSED_OR_UNKNOWN`) — [larp/risk/planner.py:426-430](larp/risk/planner.py).
- *Terminal calendar:* `trade_after < new_risk_end ≤ flatten_start < signing_end`. A FINAL profile must have `signing_end` ≤ 2026-11-11T15:00Z — [larp/strategy/schema.py:135-142](larp/strategy/schema.py). From `flatten_start` every name gets an EXIT target, and mandatory TERMINAL_FLATTEN sells follow — [larp/strategy/policy.py:54](larp/strategy/policy.py), [larp/strategy/policy.py:140-142](larp/strategy/policy.py), [larp/risk/planner.py:281-283](larp/risk/planner.py).
- *Calendar mismatch:* the generator constant `WINDOWS["FINAL"]` is still Oct 29 00:00 / Nov 9 00:00 / Nov 10 00:00 / Nov 11 14:45 UTC — [larp/strategy/profiles.py:17-22](larp/strategy/profiles.py). The decided PF-04 calendar is first buy Oct 29 14:00, new risk ends Nov 9 21:00, flatten starts Nov 10 19:00, signing ends Nov 11 14:45, flat-by Nov 11 15:00 UTC — [docs/ledger/IDEA-084.md:80-99](docs/ledger/IDEA-084.md). This is an open backlog item: [docs/INCOMPLETE_WORK.md:102](docs/INCOMPLETE_WORK.md).

**Live-wiring status at 59c878c0 (what S1 does on a host today)**
- The production service builds `ContextBuilder` without `series=` — [larp/runtime/service.py:330-333](larp/runtime/service.py). The context's `series` is then `{}` — [larp/integration/runtime.py:196](larp/integration/runtime.py). `evaluate_trend` returns `TREND_INPUT_UNAVAILABLE` and keeps the start state — [larp/strategy/s1.py:127-130](larp/strategy/s1.py). IDEA-076 records this: "Today the driver passes no `series`… Until then the live trend guard keeps its starting state (UP)" — [docs/ledger/IDEA-076.md:55](docs/ledger/IDEA-076.md), [docs/ledger/IDEA-076.md:83](docs/ledger/IDEA-076.md).
- The live limiter input producer emits only `CLASS_2_RED_FLAG` items. Its scope is `ENABLED_CLASS2_FILINGS_ONLY`, and `TRADE_RESTRICTION`, `TRADING_SUSPENSION` and `SCHEDULED_EVENT` are listed as unsupported — [larp/integration/exposure.py:50-56](larp/integration/exposure.py).
- PF-02 decided that the 8% buy stop clears when drawdown is strictly below 5% — [docs/ledger/IDEA-084.md:60-68](docs/ledger/IDEA-084.md). The code still latches `run_halt` with no reset (`|=`) — [larp/risk/accounting.py:33](larp/risk/accounting.py). This is open as PF-IMPL01/GAP-12 — [docs/INCOMPLETE_WORK.md:53](docs/INCOMPLETE_WORK.md), [docs/INCOMPLETE_WORK.md:61](docs/INCOMPLETE_WORK.md).
- Weight freeze is unchecked: "[ ] Keith: freeze the S1 weights from token session bars up to the Oct 21 close" — [docs/build/PRE_TRADING_CHECKLIST.md:366](docs/build/PRE_TRADING_CHECKLIST.md). The only S1 profiles in the repo are REHEARSAL profiles with weights 1/5 each. The committed FINAL candidate profiles are all EQUAL_WEIGHT (e.g. `docs/build/evidence/ld09b-gas-budget-profiles-20261021/final-live.json`, `…/gc01-bounded-profiles-20261021/final-live.json`, `…/rv120-profiles-20261021/final-live.json`; inspected values: baseline EQUAL_WEIGHT, midnight windows).
- Run 3 (RC6, S1 profile `6bcf1dfb`, weights 1/5) "is installed and healthy but has never placed an order", because the service had no quote verifier — [docs/ledger/IDEA-089.md:19-25](docs/ledger/IDEA-089.md).

**EQUAL_WEIGHT fallback (IDEA-037), and how it differs from S1**
- Four names at 20% each (80% gross), cheapest measured round trip first; red-flagged names are skipped. New buys only while gross < 75%; held names below 20% are topped up while gross < 75%. Nothing is sold on drift. Hard lines: a name > 25% is trimmed back to 20%; gross > 90% is trimmed back to 80%. The 12% deep cut is unchanged — [docs/ledger/IDEA-037.md:10-23](docs/ledger/IDEA-037.md), [larp/strategy/policy.py:156-185](larp/strategy/policy.py), [larp/strategy/policy.py:260-270](larp/strategy/policy.py), [larp/risk/planner.py:192-203](larp/risk/planner.py).
- LIVE EW allocations are hard-pinned to the IDEA-035/037 decisions: 1/5, 4/5, 1/4, 9/10, 3/4 — [larp/strategy/profiles.py:119-137](larp/strategy/profiles.py).
- EW allows one discretionary swap per calendar session (`DISCRETIONARY_CADENCE`) — [larp/risk/planner.py:378-380](larp/risk/planner.py). Its build is therefore staggered over four sessions ("staggered 4-session build") — [docs/ledger/IDEA-049-B.md:90](docs/ledger/IDEA-049-B.md), [docs/ledger/IDEA-049-B.md:247](docs/ledger/IDEA-049-B.md). S1 can build all five names in one session — [docs/ledger/IDEA-076.md:51](docs/ledger/IDEA-076.md).
- EW has no NYSE-hours execution bounds (the B6 bounds apply to S1 only) — [larp/risk/planner.py:397-406](larp/risk/planner.py). Its exit gas reserve is 4 × pair, against 5 × pair for S1 — [larp/strategy/profiles.py:166-167](larp/strategy/profiles.py).

**S2 weekend test (IDEA-089/090)**
- S2 is "a REHEARSAL-only test profile for the dev wallet, not a contest strategy". It uses S1's five-name book at 19% per name (weights 1/5), with trend and limiter left at UP/NORMAL. Trading is allowed whenever kit `openState` is true (`s1.execution.hours = KIT_OPEN_STATE`), with 5 attempts per leg. The window ran Sat Oct 24 01:00Z – Sun Oct 25 15:00Z — [docs/ledger/IDEA-089.md:42-60](docs/ledger/IDEA-089.md), [docs/build/evidence/s2-rehearsal-profile-20261024/rehearsal-s2-deterministic.json](docs/build/evidence/s2-rehearsal-profile-20261024/rehearsal-s2-deterministic.json).
- `KIT_OPEN_STATE` is refused unless the profile is a REHEARSAL with SHADOW evidence and falsifiers and the run mode is dev. The check is enforced in five places — [larp/strategy/execution_bounds.py:44-51](larp/strategy/execution_bounds.py), [larp/strategy/profiles.py:117-118](larp/strategy/profiles.py), [docs/ledger/IDEA-089.md:184](docs/ledger/IDEA-089.md).
- IDEA-090 source fixes are on canonical but not yet exercised live (F7 open): a planning round every 15-min slot (S2-F2), the child round plans its parent's leg (S2-F3), `max_quote_rounds` 1→2 (S2-F4), a replay fix (S2-F5), and the post-approve requote at the authorized minimum (S2-F6) — [docs/ledger/IDEA-090.md:118-157](docs/ledger/IDEA-090.md), [docs/ledger/IDEA-090.md:229-242](docs/ledger/IDEA-090.md), [docs/INCOMPLETE_WORK.md:107](docs/INCOMPLETE_WORK.md).

### Inferences
- With no live `series`, the deployed S1 is in practice a static book at `high × w_i` (95% × weights). It has the deterministic Class 2 CAUTION cut, the Class 1 exit, the Class 2 entry block, the declared ladder (8% latched for the run) and the terminal flatten. The trend guard is code-complete and tested offline only. Setting `trend_start_state` to DOWN would, by the same mechanism, give a static book at the mid level. (Derived from service.py:330-333, s1.py:127-130 and policy.py:193.)
- Even if series were wired, at 200 USDT most S1 trend and CAUTION cuts would fall below the profile minimum trade. See §2 and §4: the cut per name is ≈ 0.35 × w × 199.8 USDT (≈ 14.0 USDT at w = 0.20), against a minimum of 18.637 USDT, so only names with w ≥ ≈ 0.267 could be trimmed. The run-3 rehearsal documents the same effect at 100 USDT (SJ-09-PC01 C6).
- What is actually "planned" for Oct 29 is therefore unsettled in three ways: the strategy choice (Monday re-decision), the exact profile (no frozen weights or FINAL S1 profile), and the calendar (generator vs PF-04).

### Gaps
- No record at 59c878c0 of Monday's (Oct 26) strategy decision, of frozen S1 weights or σ inputs, or of a FINAL S1 profile hash.
- Not found: any plan to wire live token session bars into `ContextBuilder` before the freeze. IDEA-076 lists DR-08 as open, but no current backlog line names it explicitly beyond IDEA-075/PF-IMPL01.

---

## 2. Every numeric parameter: value and where it is set

### Takeaway
S1's tunables live in the profile's `s1` block and top-level profile keys, validated by `s1.config`, `schema.profile` and `profiles.validate_live`. Hard limits and the ladder are code constants. The concrete S1 values used so far are the run-3/S2 rehearsal values, sized for about 100 USDT. The FINAL values follow the formulas in `build_live_profiles` at 200 USDT expected equity.

### Cited Findings

**S1 `s1` block (profile; rehearsal value → PF-01 final target)**
- `levels` high/mid/low = 19/20, 3/5, 3/10 (95/60/30%). Bound: 0 < low < mid < high ≤ 95% — [larp/strategy/s1.py:52-57](larp/strategy/s1.py), S2 profile JSON, [docs/ledger/IDEA-084.md:46](docs/ledger/IDEA-084.md).
- `weights`: rehearsal 1/5 each. The rehearsal deviation reads: "At about 100 USDT the measured minimum trade (18.637420 USDT) needs every weight ≥ 0.1962" — [docs/build/evidence/s1-rehearsal-profile-20261023/README.md:24](docs/build/evidence/s1-rehearsal-profile-20261023/README.md). Final: inverse-σ, 60 sessions (min 20) to the Oct 21 close, frozen once — [docs/ledger/IDEA-084.md:48](docs/ledger/IDEA-084.md). Freeze-tool defaults: window 60, minimum 20, cap 3/10 — [larp/strategy/s1.py:286](larp/strategy/s1.py), [larp/strategy/s1.py:343-345](larp/strategy/s1.py).
- `weight_cap` 3/10. Bound: (0, 30%] — [larp/strategy/s1.py:58-60](larp/strategy/s1.py).
- `hard_name_weight` 7/20 (35%). Bound: [high × cap, 35%] — [larp/strategy/s1.py:67-69](larp/strategy/s1.py).
- `top_up_band` 1/20 (5 pp). Bound: (0, 10%] — [larp/strategy/s1.py:70-72](larp/strategy/s1.py).
- `trend_window_sessions` 5 (bound 2–20); `trend_band_bps` 100 (1–1000); `trend_delay_seconds` 900 (0–86400); `trend_start_state` UP (UP/DOWN); `llm_expiry_sessions` 3 (1–10); `max_legs_per_symbol_session` 3 (1–5); `limiter_mode` DETERMINISTIC (or MODEL) — [larp/strategy/s1.py:73-86](larp/strategy/s1.py), S2/run-3 profile JSON, [docs/build/evidence/s1-rehearsal-profile-20261023/README.md](docs/build/evidence/s1-rehearsal-profile-20261023/README.md).
- `execution`: `open_delay_seconds` 1800, `close_buffer_seconds` 900, `max_attempts_per_leg_session` 3 (S2: 5, plus `hours` KIT_OPEN_STATE). Bounds: delay and buffer ≤ 14,400 s; attempts 1–5 — [larp/strategy/execution_bounds.py:22-34](larp/strategy/execution_bounds.py), [docs/ledger/IDEA-084.md:51](docs/ledger/IDEA-084.md).

**Top-level profile keys (rehearsal S2 value; FINAL formula/value)**
- `expected_equity_units` 100 USDT (rehearsal) / 200 USDT (final) — [larp/strategy/profiles.py:271](larp/strategy/profiles.py).
- `cost_reserve_units` = ceil(E/1000): 0.1 / 0.2 USDT — [larp/strategy/profiles.py:272](larp/strategy/profiles.py), [larp/strategy/profiles.py:299](larp/strategy/profiles.py).
- `per_trade_cap_units` = ceil(E × high × max w) + reserve: 19.1 USDT (rehearsal, w = 1/5); final 38.2 USDT at w = 1/5, up to 57.2 USDT at w = 0.30. Validation requires the cap to cover a full top position — [larp/strategy/profiles.py:273-276](larp/strategy/profiles.py), [larp/strategy/profiles.py:126-133](larp/strategy/profiles.py).
- `minimum_trade_units` 18.637420 USDT in the rehearsal and in every committed FINAL (EW) candidate. Formula: max over symbols of ceil(10000 × sizing-gas value ÷ (50 − spread − min(50, 2 × impact) − fee)). It must lie between that formula and the smallest top-level position — [larp/strategy/profiles.py:147-165](larp/strategy/profiles.py), [larp/strategy/profiles.py:226-228](larp/strategy/profiles.py).
- `slippage_bps` 8 = min(50, max measured p90 15 s requote drift). Validation allows 0 < s ≤ 50 — [larp/strategy/profiles.py:245](larp/strategy/profiles.py), [larp/strategy/profiles.py:138-139](larp/strategy/profiles.py), [docs/build/QUOTE_COST_REVIEW_120_20261021.md:77](docs/build/QUOTE_COST_REVIEW_120_20261021.md).
- `impact_bps` 2 = min(50, 2 × max median impact). `impact_median_bps` is 1 for all five and must equal the summary — [larp/strategy/profiles.py:246](larp/strategy/profiles.py), [larp/strategy/profiles.py:140-144](larp/strategy/profiles.py).
- `quote_age_seconds` 30 (≤ 30); `proposal_seconds` 15 = min(15, quote age); `feature_age_seconds` 345,600 (4 days); `review_sessions` 5 (must equal 5); `dust_units` 0; `price_threshold_bps` 0; `minimum_remaining_sessions` 0 — [larp/strategy/profiles.py:243-247](larp/strategy/profiles.py), [larp/strategy/schema.py:81-87](larp/strategy/schema.py).
- Execution authority L = 660 s, margin m = 30 s (≤ 3600 s, both or neither) — [larp/strategy/schema.py:116-132](larp/strategy/schema.py), S2 profile JSON, [docs/ledger/IDEA-084.md:149](docs/ledger/IDEA-084.md).
- Gas, initial-only scope: `gas_action_budget_units` 384,000,000,000,000 wei (0.000384 BNB per approve+swap pair, at the cap gas price); `gas_sizing_budget_units` 80,004,608,000,000 wei (≈ 0.00008 BNB, expected price); `exit_gas_reserve_units` 3,840,000,000,000,000 wei = 5 positions × 2 children × action budget. Validation requires exit reserve ≥ 5 × pair for S1 — S2 profile JSON, [docs/build/evidence/s1-rehearsal-profile-20261023/README.md:30](docs/build/evidence/s1-rehearsal-profile-20261023/README.md), [larp/strategy/profiles.py:147-167](larp/strategy/profiles.py), [larp/strategy/profiles.py:320-322](larp/strategy/profiles.py).
- Windows: REHEARSAL Oct 23 00:00 / Oct 25 00:00 / Oct 26 00:00 / Oct 26 14:45Z; FINAL generator Oct 29 00:00 / Nov 9 00:00 / Nov 10 00:00 / Nov 11 14:45Z — [larp/strategy/profiles.py:17-22](larp/strategy/profiles.py). PF-04 target: Oct 29 14:00 / Nov 9 21:00 / Nov 10 19:00 / Nov 11 14:45 (flat-by 15:00) — [docs/ledger/IDEA-084.md:82-90](docs/ledger/IDEA-084.md).
- Evidence scope: `falsifier_ids` F-ITEM-4.02/1.05/2.06; `evidence_max_age_ms` 3,600,000; FINAL requires `falsifier_authority` DISCRETIONARY_EXIT (SHADOW only in a REHEARSAL); `statement_authority` SHADOW; `assessment_required` false — [larp/strategy/profiles.py:109-116](larp/strategy/profiles.py), [larp/strategy/profiles.py:234-238](larp/strategy/profiles.py).
- Quote-cost summary embedded in the profile (capture `407a08e7…`, observed 2026-10-19T23:57Z): BNB price 722.150988 USDT. Spreads: GOOGLB 3, MSFTB 17, NVDAB 4, SKHYB 2, TSLAB 5 bp. Median impact 1 bp each; fee 0. Slippage p90: 4/8/6/8/6 bp. Approve gas ≈ 4.52–4.56e12 wei; swap gas ≈ 7.06–7.17e13 wei — S2 profile JSON `quote_cost_summary`.

**Code constants (not reachable by profile)**
- `MAX_GROSS` 19/20, `MAX_WEIGHT_CAP` 3/10, `MAX_HARD_NAME` 7/20, `EVIDENCE_WINDOW_SESSIONS` 5 — [larp/strategy/s1.py:32-38](larp/strategy/s1.py).
- Ladder thresholds 92/88/97 (8/12/3%) — [larp/risk/accounting.py:33-36](larp/risk/accounting.py). Deep-cut gross 2/5 — [larp/risk/planner.py:194-195](larp/risk/planner.py).
- `ENTRY_COST_CAP` 50 bp (`cost * 10000 > mark * 50`) — [larp/risk/planner.py:472](larp/risk/planner.py). Entry impact cap min(50, 2 × median) — [larp/risk/planner.py:476-477](larp/risk/planner.py). `EXIT_SPLIT_HEADROOM_BPS` 100 — [larp/risk/planner.py:26](larp/risk/planner.py).
- Summary feasibility: spread + min(50, 2i) + fee < 50 bp — [larp/strategy/profiles.py:63-64](larp/strategy/profiles.py). FINAL `signing_end` ≤ Nov 11 15:00Z — [larp/strategy/schema.py:140-141](larp/strategy/schema.py). Execution-authority maximum 3600 s — [larp/strategy/schema.py:117](larp/strategy/schema.py).
- EW-only: 4 positions; one discretionary swap per session — [larp/risk/planner.py:192](larp/risk/planner.py), [larp/risk/planner.py:378-380](larp/risk/planner.py).
- In-run cost probe: `measured_roundtrip_bps` comes from a fresh 40 USDT buy+sell quote pair per market observation, with no negative-cost credit — [larp/marketdata/port.py:135-189](larp/marketdata/port.py).
- Runtime: `max_quote_rounds` 2 (example config); `price_jump_check_bps` 3000; `cadence_ms` set per run (15-min slots in runs 2–4) — [config/runtime/runtime.example.json:28-39](config/runtime/runtime.example.json), [docs/ledger/IDEA-090.md:18-31](docs/ledger/IDEA-090.md).

### Inferences
- At the final's 200 USDT with weights 1/5: per-name target ≈ 37.96 USDT, per-trade cap 38.2 USDT, so one buy per name. With inverse-σ weights capped at 0.30, the largest target is ≈ 56.9 USDT and the cap 57.2 USDT. The minimum weight allowed by `validate_live` is then 18.637 ÷ 190 ≈ 0.098 (profiles.py:163-165). Arithmetic from the formulas cited above.
- The minimum trade of 18.64 USDT is driven entirely by MSFTB's 17 bp off-session spread: its gas budget is 50 − 17 − 2 = 31 bp. The other four names would give 12.6–13.4 USDT minimums. Recomputed from the summary values: gas value 0.057776 USDT ÷ 0.0031 = 18.637 USDT.

### Gaps
- The exact FINAL S1 values (frozen weights, σ inputs and data hashes, final windows, final gas budgets, signer caps) are not in the repo. No FINAL S1 profile has been built.
- The repo does not record whether the FINAL `minimum_trade_units` will stay at the formula floor (18.64) or be set higher.

---

## 3. Evidence for and against each component (what was proposed, adopted or rejected, and why)

### Takeaway
No component of S1 has positive out-of-sample profit evidence. The pre-registered trend-guard test (EXP-007) has never been run. The one completed comparison (EXP-008, historical underlying proxies) favoured equal weight for profit by −0.58 pp per 10 sessions, and attributes both inverse-σ weighting and the trend guard as drags. S1 halved the 8%-drawdown frequency in that test. The team kept S1 for drawdown and to avoid requalification, and recorded that this decision goes against the pre-registered outcome. Measured quote costs are low (2–5 bp round trip except MSFTB at 17 bp). Live execution so far completed 1 of 4 buys. Earlier reviews consistently said returns come from exposure × market path, not prediction. They recommended low turnover and lower gross (≈ 42–54%) than the 95% that was adopted.

### Cited Findings

**EXP-007 (trend guard vs static 95%): criteria frozen, not run**
- Hypothesis: on bStock token candles, over 10-session windows, the guard lowers mean max drawdown by ≥ 1 pp versus static 95% while costing ≤ 0.5 pp of return. Outcomes: supported / not supported (no drawdown gain, or return worse by > 1 pp) / inconclusive (also if fewer than 5 non-overlapping windows). Costs 25 bp per side + $0.03 gas — [docs/ledger/EXP-007.md:6-18](docs/ledger/EXP-007.md).
- Decision rule fixed before any run (Keegan, 2026-10-19): an INCONCLUSIVE result ships the guard as declared; NOT_SUPPORTED fixes trend at 95% — [docs/ledger/EXP-007.md:20](docs/ledger/EXP-007.md), [docs/ledger/EXP-007.md:46-59](docs/ledger/EXP-007.md). Status: "criteria frozen… not yet run". "Code / config" and "Result" are unfilled — [docs/ledger/EXP-007.md:4](docs/ledger/EXP-007.md), [docs/ledger/EXP-007.md:23-24](docs/ledger/EXP-007.md), [docs/LEDGER.md:94](docs/LEDGER.md).

**EXP-008 (S1 vs EW over 10 sessions): run 2026-10-23, "EW better for profit"**
- Primary data: Yahoo Finance split-adjusted daily closes, 2019-01-02 → 2026-10-22 (SK hynix in KRW). Token check: kit 1h candles. Both arms start at 200 USDT and end flat. The EW arm drops MSFTB as the highest-cost name. Costs 25 bp per side + 0.03 USDT gas. The test has no limiter, no red flags and no minimum trade, and models the 8% stop as lifting below 5% — [docs/ledger/EXP-008.md:13-45](docs/ledger/EXP-008.md), [docs/ledger/EXP-008.md:131](docs/ledger/EXP-008.md).
- Results (simulated at closes, not fills). On 1,954 windows (195 non-overlapping), mean net return was S1 +0.34% (SD 4.1%, P(DD ≥ 8%) 3.5%) against EW +0.92% (SD 5.2%, 9.7%). S1 − EW = −0.58 pp (90% CI −0.77, −0.41); S1 was ahead in 36% of windows and negative in every calendar year. At 50 bp the gap was −0.68 pp. On tokens (41 windows, 4 non-overlapping) it was −0.02 pp (CI −1.36, +0.61) — [docs/ledger/EXP-008.md:84-95](docs/ledger/EXP-008.md).
- Decomposition (reported only). S1-STATIC − EW = −0.24 pp (weights and name set, net of +15 pp gross); S1 − S1-STATIC = −0.33 pp (trend guard). On tokens, static S1 led EW by +0.48 pp and the guard cost −0.50 pp. In the post-hoc diagnostics, inverse-σ moved weight from the highest-return names (NVDAB, TSLAB, SKHYB) to the lowest (GOOGLB, MSFTB). The trend state was DOWN on 37% of sessions with "about 35 flips a year: the guard mostly whipsaws" — [docs/ledger/EXP-008.md:97-105](docs/ledger/EXP-008.md).
- Review caveats: the recommendation to keep S1 is "a judgement against the pre-registered outcome". The simulator existed before the criteria commit (3.5 min apart). The Yahoo snapshot is not reproducible from Git — [docs/ledger/EXP-008.md:112-126](docs/ledger/EXP-008.md). Status: "Input for team discussion, no profile change" — [docs/LEDGER.md:105](docs/LEDGER.md).
- Source-rights tension, flagged: plan.md D-09 states "Yahoo is unlicensed and must not be used" (for training labels) — [docs/skill/larp/plan.md:134](docs/skill/larp/plan.md). EXP-008's primary data is Yahoo — [docs/ledger/EXP-008.md:34-37](docs/ledger/EXP-008.md). The relevant rules are F-63 ("no source you aren't authorized to use") and F-71 — [docs/skill/SKILL.md:157](docs/skill/SKILL.md), [docs/skill/SKILL.md:164](docs/skill/SKILL.md).

**Quote-cost measurements (IDEA-063 DC-01; RV120-01/RV01; FN-01/02) — offline quote captures, not fills**
- Coverage: 1,924 bStock samples and 385 BNB quotes, Oct 16–19 UTC including the weekend, all at 40 USDT. `openState` was true on every sample. All 3,848 gas estimates were FALLBACK ("no usable gas") — [docs/build/QUOTE_COST_REVIEW_120_20261021.md:14-29](docs/build/QUOTE_COST_REVIEW_120_20261021.md).
- Spreads, round-trip minus impacts, worse-of-regime (off-session) medians: GOOGLB 3, MSFTB 17, NVDAB 4, SKHYB 2, TSLAB 5 bp. US-session median round trips are lower: 0.68 / 6.99 / 1.11 / 1.13 / 0.68 bp. MSFTB's US p90 is 32.7 bp, maximum 50.3 bp. Impact ≈ 0 (floored at 1 bp) — [docs/build/QUOTE_COST_REVIEW_120_20261021.md:31-50](docs/build/QUOTE_COST_REVIEW_120_20261021.md).
- Entry cost at the 0.064 gwei sizing price: 18.4–33.4 bp at 40 USDT and 32.9–47.9 bp at 20 USDT. MSFTB sits at exactly 50.0 bp at the 18.64 USDT minimum. At the 0.16 gwei cap, 20 USDT entries are refused — [docs/build/QUOTE_COST_REVIEW_120_20261021.md:52-73](docs/build/QUOTE_COST_REVIEW_120_20261021.md).
- Slippage: 8 bp is the worst token/regime p90 of two-sided 15 s requote drift. Adverse exceedances: SKHYB 2/43 in US hours, 10/342 off-session; MSFTB 1/42 US. These are counterfactual quote comparisons, not revert frequencies — [docs/build/QUOTE_COST_REVIEW_120_20261021.md:75-100](docs/build/QUOTE_COST_REVIEW_120_20261021.md).
- Fee: `fee_bps = 0` "only if fees are netted (UNVERIFIED)". `tradeFee` (0.0092–0.0168 USD) is documented as network-fee metadata; #119 is open — [docs/build/QUOTE_COST_REVIEW_120_20261021.md:101-104](docs/build/QUOTE_COST_REVIEW_120_20261021.md), [docs/build/QUOTE_FEE_REVIEW_20261017.md:9-23](docs/build/QUOTE_FEE_REVIEW_20261017.md).
- Earlier estimates were superseded. IDEA-012's print-based Roll spreads of 13–56 bp are not quotes — [docs/ledger/IDEA-012.md:12-20](docs/ledger/IDEA-012.md) — and its numbers "remain historical" after the IDEA-022 defects — [docs/ledger/IDEA-012.md:95](docs/ledger/IDEA-012.md). IDEA-035's synthetic break-even for being invested was ≈ 20 bp per side — [docs/INCOMPLETE_WORK.md:164](docs/INCOMPLETE_WORK.md).

**Run-4 live execution (S2 on the dev wallet, Oct 24): signed mainnet evidence**
- Quote check Saturday 03:39Z and 05:20Z: all five names `VERIFIED_EXECUTABLE` at 19 USDT, BUY and SELL, with `openState` true for token and underlying. Impact 0–1 bp; quoted slippage 8 bp; fee 0 — [docs/ledger/IDEA-089.md:97-119](docs/ledger/IDEA-089.md), [docs/ledger/IDEA-089.md:256-258](docs/ledger/IDEA-089.md).
- First signed fill: BUY SKHYB 18.951721 USDT → 137,879,758,388,310,745 units (consistent with the quote). Approve used 46,218 gas at 51.46 Mwei; swap used 434,540 gas at 50.29 Mwei. "Gas per approve + swap: 0.0000242 BNB, against the 0.000384 BNB reservation and the 0.00008 expected." The round log was delivered — [docs/ledger/IDEA-089.md:369-384](docs/ledger/IDEA-089.md).
- Outcome over four BUY intents: 1 COMPLETED (06:00Z) and 3 ABORTED with "encoded swap economics mismatch/expired" (07:15Z, 08:00Z, 08:30Z). `max_slippage_bps` was 8 on every intent; signer refusals 0. Two approves confirmed with no swap, leaving open router allowances — [docs/ledger/IDEA-090.md:169-227](docs/ledger/IDEA-090.md). Root cause (S2-F6): the post-approve requote had to return at least the planning quote's minimum at the same 8 bp slippage. The fix is in source, not yet live-tested — [docs/ledger/IDEA-090.md:191-242](docs/ledger/IDEA-090.md).
- Other live findings. Rounds ran only in 2 of 5 slots because cadence followed the evidence-issuer rotation (S2-F2). Child rounds re-ordered near-equal legs (S2-F3); SKHYB filled only on its third round. The first post-activation intent expired unclaimed because the run sheet starts execution after P4 — [docs/ledger/IDEA-089.md:363-368](docs/ledger/IDEA-089.md), [docs/ledger/IDEA-089.md:423-466](docs/ledger/IDEA-089.md).

**Off-hours pricing and regime gating**
- EXP-002 (do off-hours quotes lag verified news?): "draft (thresholds in brackets not frozen)"; no code or result. Its decision: "v1.0 uses off-hours logic as an execution guard only unless the result is supported" — [docs/ledger/EXP-002.md:1-14](docs/ledger/EXP-002.md). Off-hours `openState` has since been observed true: on all DC-01 samples, including the weekend, and in the Saturday Oct 24 sample — [docs/INCOMPLETE_WORK.md:158](docs/INCOMPLETE_WORK.md).
- EXP-003 (regime gating vs a volatility cap): "draft"; episodes unlisted; no result — [docs/ledger/EXP-003.md:1-14](docs/ledger/EXP-003.md). PF-05 chose "no additional unbuilt regime/covariance governor beyond S1's trend, limiter and declared ladder" — [docs/ledger/IDEA-084.md:122-124](docs/ledger/IDEA-084.md).

**Kelly sizing (IDEA-006): recommended, not decided**
- Risk-constrained Kelly "helps sizing, not edge". The infinite-horizon bound is too conservative for 10 sessions, so the entry proposes a finite-horizon drawdown constraint. Synthetic: efficient gross ≈ 0.4–0.6; expected log growth flattens above that while drawdown risk keeps rising; "≈ 10 bp of expected log growth at a 6% premium" is at stake — [docs/ledger/IDEA-006.md:15-35](docs/ledger/IDEA-006.md), [docs/LEDGER.md:28](docs/LEDGER.md). Never adopted; superseded in practice by S1 at 95% (IDEA-075).

**Profit-focused direction reviews (all marked recommended / not decided unless stated)**
- IDEA-009: proposed a rule-based base book with LLM CONFIRM/VETO/EXIT, declared sizing (≈ 42–54% gross), flat at the end and low frequency. "Rank is driven by exposure × market path"; "each unnecessary round trip costs about as much as the whole expected premium" — [docs/ledger/IDEA-009.md:12-22](docs/ledger/IDEA-009.md), [docs/ledger/IDEA-009.md:221-242](docs/ledger/IDEA-009.md). The base-book default was adopted on 2026-10-10 (D-08) — [docs/skill/larp/plan.md:133](docs/skill/larp/plan.md). Flat-at-end was adopted (IDEA-035 C4, Q-06). The exposure part was superseded by S1 at 95%.
- IDEA-012: harness = execution + guardrails only, with no intraday heuristics. It proposed "exposure to declared caps in 4 high-vol names" (toy P(top 3) 0.07–0.27). Its −15% floor and its variance headline were later withdrawn — [docs/ledger/IDEA-012.md:29-44](docs/ledger/IDEA-012.md), [docs/ledger/IDEA-012.md:93](docs/ledger/IDEA-012.md).
- IDEA-014: measure costs first; one frozen baseline plus ≤ 2 variants; "do not tune rules, prompts or exposure to development-wallet P&L" — [docs/ledger/IDEA-014.md:10-31](docs/ledger/IDEA-014.md).
- IDEA-017: reject variance as profit evidence; require a complete entry/re-entry lifecycle; reject automatic deployment of an unvalidated overlay; prevent cap-trim micro-trades — [docs/ledger/IDEA-017.md:28-60](docs/ledger/IDEA-017.md).
- IDEA-018: base-book expected net −0.61% to +0.06% at 200 USDT. Gas for 8 swaps ≈ the whole expected premium. A discretionary round trip needs 45–135 bp of edge. The break-even spread for adding exposure is 10.9–17.4 bp per side; above it more exposure lowers expected profit, below it the gain is ≤ 0.1 pp. Recommendations: keep the declared formula; "8% halt latched for the run" — [docs/ledger/IDEA-018.md:20-30](docs/ledger/IDEA-018.md), [docs/ledger/IDEA-018.md:96-138](docs/ledger/IDEA-018.md), [docs/ledger/IDEA-018.md:164-184](docs/ledger/IDEA-018.md).
- IDEA-019: a low-turnover, volatility-sized base book with conditional exposure escalation: "If confirmed rules principally rank terminal equity… stronger exposure can be considered as an explicit tournament choice" — [docs/ledger/IDEA-019.md:89-110](docs/ledger/IDEA-019.md).
- IDEA-075's own expected outcome (synthetic, IDEA-035 §10.2, no trend guard): at 90–100% gross, mean +0.16 to +0.19% over 10 sessions, SD 5.2–5.8%, P(8% stop) 9–12% (about double the 80% plan). At 20 bp per side the mean is ≈ −0.12%. "It cannot be shown before the run to make money." — [docs/ledger/IDEA-075.md:9](docs/ledger/IDEA-075.md), [docs/ledger/IDEA-075.md:164-170](docs/ledger/IDEA-075.md).
- PF-00 states the objective and its evidence base: "There is no calibrated distribution or held-out result proving an optimum for this 14-day window… not a claim that 95% exposure has a higher probability of profit than every lower-exposure policy." — [docs/ledger/IDEA-084.md:13-23](docs/ledger/IDEA-084.md).

### Inferences
- If the live trend guard stays inert (no series, and cuts below the minimum trade), the deployed S1 resembles EXP-008's S1-STATIC arm. That arm trailed EW by −0.24 pp on the underlying proxy, led it by +0.48 pp on the short token sample, and was not separately reported for drawdown. The guard's measured −0.33 to −0.50 pp cost would then not be paid, and neither would its drawdown benefit.
- EXP-008 does not model three code behaviours. (a) EW's one-swap-per-session staggered 4-session build. (b) The minimum-trade filter that blocks small S1 trims. (c) The latched 8% stop: EXP-008 used a <5% reset that the code lacks. Each could shift the S1 − EW gap in either direction.
- Measured spreads per side (≈ 1–2.5 bp; ≈ 8.5 bp for MSFTB, since spread_bps is a round-trip figure) are below IDEA-018's 10.9–17.4 bp/side break-even for adding exposure. Under IDEA-018's own model, higher gross therefore has a slightly positive expected cost-adjusted premium, at the price of higher variance and drawdown.
- The live failure mode that matters most for any strategy is execution completion (1/4 buys, with abandoned approvals). The S2-F6 fix exists only in source, and S1's 3 attempts per leg per session can be used up in about 45 minutes once rounds run every slot ([docs/ledger/IDEA-090.md:160-162](docs/ledger/IDEA-090.md)).

### Gaps
- No EXP-007 result. No S1-STATIC drawdown statistics in EXP-008. No quote-vs-fill fee evidence (#119). No revert-frequency measurement (LD19/LD20). No live sell/flatten evidence yet: run 4's Sunday flatten is after this commit.
- Not found: any rights review covering EXP-008's use of Yahoo data.

---

## 4. Cost handling: fees, spread, impact, gas, slippage, gas reservation and seeding

### Takeaway
Costs enter at four points.
1. **Profile build.** A measured `QuoteCostSummary` sets the minimum trade, slippage and impact limits. The rule is gas ÷ (50 bp − spread − 2 × impact − fee) for the worst symbol.
2. **Planning.** Every discretionary BUY must cost ≤ 50 bp of mark (premium + fee + expected gas), stay within the impact cap and the cost reserve, and keep the exit gas reserve.
3. **Execution.** The quote's minimum output must respect `slippage_bps` (8).
4. **Gas.** Initial-gas-only reservation at a capped gas price, with no agent top-ups (POLICY); the whole run's BNB comes from a pre-run MetaMask seed of about 6 USDT.

Live gas used is about 16× below the per-pair reservation.

### Cited Findings
- *Quote validity, every leg:* route valid, fresh (≤ `quote_age_seconds`) and unexpired; quoted slippage ≤ `slippage_bps`; impact ≤ `impact_bps` unless mandatory; LIVE origin WEB3_OPEN_API; minimum receive ≥ output × (1 − slippage_bps) — [larp/risk/planner.py:56-73](larp/risk/planner.py).
- *Cost:* for a BUY, max(0, cash − mark) + fee + gas value, where gas uses the quote's `expected_gas_bnb_units` if present (IDEA-088) and the reservation keeps full `gas` — [larp/risk/planner.py:463-467](larp/risk/planner.py), [docs/LEDGER.md:106](docs/LEDGER.md).
- *Discretionary gates:* cost > `cost_reserve_units` → `COST_RESERVE_INSUFFICIENT` (any non-mandatory leg). A BUY with cost > 50 bp of mark → `ENTRY_COST_CAP`. LIVE impact > min(50, 2 × median) → `ENTRY_IMPACT_CAP`. Mandatory sells bypass these but not quote validity or slippage — [larp/risk/planner.py:468-479](larp/risk/planner.py), [docs/ledger/IDEA-076.md:190-200](docs/ledger/IDEA-076.md). The entry cost cap is declared ("≤ 50 bp one-way") and recorded as DEV-05 (FINAL) — [docs/skill/larp/plan.md:47](docs/skill/larp/plan.md), `config/release/deviations.v1.json` DEV-05.
- *Minimum trade:* discretionary legs below `minimum_trade_units` are rejected (`MINIMUM_TRADE`) — [larp/risk/planner.py:418-425](larp/risk/planner.py), [larp/risk/planner.py:458-462](larp/risk/planner.py). The policy uses the same value as its rebalance step — [larp/strategy/policy.py:199-206](larp/strategy/policy.py). The formula and the "largest across all five names" rule are documented in [config/strategy/LIVE.md:19-29](config/strategy/LIVE.md).
- *Cost ranking:* EW ranks entries by in-run `measured_roundtrip_bps`, a fresh 40 USDT quote round trip — [larp/strategy/policy.py:20-23](larp/strategy/policy.py), [larp/risk/planner.py:391-396](larp/risk/planner.py), [larp/marketdata/port.py:156-189](larp/marketdata/port.py). S1 does not rank by cost; it sorts sells first, then by notional. In LIVE it only requires that a measured cost exists for a buy — [larp/strategy/policy.py:195](larp/strategy/policy.py), [larp/risk/planner.py:384-390](larp/risk/planner.py). PF-05 asks for ranking by "current intended size's all-in round-trip cost" — [docs/ledger/IDEA-084.md:104-107](docs/ledger/IDEA-084.md).
- *Slippage derivation:* `slippage_bps` = min(50, max symbol p90 of 15 s requote drift) = 8 — [larp/strategy/profiles.py:245](larp/strategy/profiles.py), [docs/ledger/IDEA-063.md:28-40](docs/ledger/IDEA-063.md). PF-06: "finite slippage ≤ 50 bp; do not widen slippage automatically on retry" — [docs/ledger/IDEA-084.md:128-129](docs/ledger/IDEA-084.md). S2-F6's bounded second requote never goes wider than the intent's limit — [docs/ledger/IDEA-090.md:193-197](docs/ledger/IDEA-090.md).
- *Gas reservation:* a BUY needs quote gas ≤ free BNB and must leave BNB − reserved − gas ≥ `exit_gas_reserve_units` — [larp/risk/planner.py:485-500](larp/risk/planner.py). PF-06 defines the reservation: "attributable qualified step estimate/observed bound with 20% gas-limit headroom, multiplied by the selected gas-price cap… FALLBACK gas is ineligible" — [docs/ledger/IDEA-084.md:134-144](docs/ledger/IDEA-084.md). The action budget formula is ceil(max pair gas × 5/4 × cap gas price) — [larp/strategy/profiles.py:320](larp/strategy/profiles.py). The S1 exit reserve covers 5 positions × 2 balanced children × 0.000384 BNB = 0.00384 BNB — [docs/build/evidence/s1-rehearsal-profile-20261023/README.md:30](docs/build/evidence/s1-rehearsal-profile-20261023/README.md), [docs/build/evidence/rehearsal-exit-split-20261021/README.md:21-45](docs/build/evidence/rehearsal-exit-split-20261021/README.md). Mandatory exits are split into k = ceil(V × 1.01 / cap) children — [larp/risk/planner.py:26-37](larp/risk/planner.py). The coverage review checks positions × children × action ≤ reserve — [larp/execution_live/caps_review.py:130-137](larp/execution_live/caps_review.py).
- *Initial gas only (DEV-21, FINAL):* "v1 plans no gas top-up rounds. The only BNB is the F-120 first-gas swap…" — `config/release/deviations.v1.json` DEV-21. `plan_top_up` returns False under `initial_gas_only` — [larp/risk/gas.py:13-16](larp/risk/gas.py). A passive monitor raises `PAIR_UNAFFORDABLE` / `BELOW_EXIT_RESERVE` incidents — [larp/runtime/gas.py:39-44](larp/runtime/gas.py).
- *Seed sizing:* "about 4 USDT in total for the dev wallet, about 6 USDT for the final wallet… No BNB is swapped back to USDT at the end (G-13); leftover BNB is accepted." This is POLICY (Yao, 2026-10-16) — [docs/build/DEPLOYMENT_DAY.md:77-81](docs/build/DEPLOYMENT_DAY.md), [docs/skill/SKILL.md:208](docs/skill/SKILL.md). Planning estimate for the final: N ≈ 30 pairs → ≈ 0.0083 BNB ≈ 6 USDT, plus ≈ 5 pairs if LD06 cleanup is enabled — [docs/build/QUOTE_COST_REVIEW_120_20261021.md:124-129](docs/build/QUOTE_COST_REVIEW_120_20261021.md). The final funding note is still blank ("Isaac, after funding and before Oct 29 00:00 UTC") — [docs/build/DEPLOYMENT_DAY.md:89](docs/build/DEPLOYMENT_DAY.md).
- *Equity accounting:* equity includes BNB at the ledger BNB price — [larp/strategy/schema.py:210-223](larp/strategy/schema.py). Gas above a reservation is still charged as a chain fact — [larp/risk/accounting.py:76-87](larp/risk/accounting.py).
- *Live gas:* 0.0000242 BNB per approve+swap pair (≈ 0.0175 USDT at 722 USDT/BNB), against 0.000384 reserved and 0.00008 expected — [docs/ledger/IDEA-089.md:380](docs/ledger/IDEA-089.md). The kit's figure is 0.000022–0.000046 BNB per trade — [docs/skill/SKILL.md:176](docs/skill/SKILL.md).

### Inferences
- The minimum trade is computed from the *sizing* gas budget (≈ 0.00008 BNB per pair), not from the ≈ 0.0000242 BNB seen live, and from MSFTB's worst-regime 17 bp spread. A cheaper minimum, which would let the trend guard or CAUTION trim at 200 USDT, needs a new measured `QuoteCostSummary` and sizing budget (profiles.py:155-165 requires sizing ≥ the summary's measured pair), or a per-symbol minimum (a code change).
- The `spread_bps` that feeds the 50 bp entry-budget formula is a round-trip measure, so the build-time feasibility check is conservative compared with the planner's actual one-way cost check.
- With about 30 live-cost pairs ≈ 0.0007 BNB (≈ 0.5 USDT), most of a 6 USDT seed (≈ 3% of 200 USDT) would still be BNB at the end. It is never sold back (G-13), and whether it counts in equity is open (Q-03/Q-39). A smaller seed is an operational, non-code choice but must clear the buy gate. Arithmetic: S1 needs BNB ≥ exit reserve 0.00384 + one action budget 0.000384 = 0.004224 BNB (≈ 3.05 USDT) before the first buy (planner.py:498), plus margin for the actual gas of every pair.

### Gaps
- Fee netting (#119) and actual quote-vs-fill slippage on sells are unverified. The FINAL gas budgets, signer caps (CAP-02 for the final) and final seed amount are not recorded.

---

## 5. Configurability: what a new profile can change without code, what needs code, and what requalification follows

### Takeaway
Inside S1, a new StrategyProfile can change levels (≤ 95%), weights (positive, ≤ 30%, sum 1), the hard line (≤ 35%), the top-up band (≤ 10%), the trend window, band, delay and start state, limiter expiry and mode, leg and attempt counts, execution delay and buffer, slippage (≤ 50 bp), windows (signing end ≤ Nov 11 15:00Z) and minimum trade (≥ the measured formula). Any such change creates a new profile hash. That needs a fresh coverage review, Isaac's approval of the profile and `signer.json`, new run pins, and FINAL deviation rows. Anything outside these bounds needs code: live trend series, the 8%-stop reset, a different ladder, more than 95% gross, a 4-name S1, per-symbol minimums, cost ranking for S1, other evidence classes, or EW parameters other than 20/80/25/90/75. A code change also needs a new release build and qualification before final activation (Oct 27–29).

### Cited Findings

**Reachable by profile alone (within validator bounds)**
- `s1` block bounds — [larp/strategy/s1.py:52-86](larp/strategy/s1.py):

  | Key | Allowed range |
  |---|---|
  | `levels` | 0 < low < mid < high ≤ 19/20 |
  | `weight_cap` | ≤ 3/10 |
  | `weights` | > 0 each, ≤ cap, Σ = 1, exactly five symbols |
  | `hard_name_weight` | [high × cap, 7/20] |
  | `top_up_band` | (0, 1/10] |
  | `trend_window_sessions` | 2–20 |
  | `trend_band_bps` | 1–1000 |
  | `trend_delay_seconds` | 0–86400 |
  | `trend_start_state` | UP or DOWN |
  | `llm_expiry_sessions` | 1–10 |
  | `max_legs_per_symbol_session` | 1–5 |
  | `limiter_mode` | DETERMINISTIC or MODEL |

- `execution` bounds: delay and buffer ≤ 14,400 s; attempts 1–5; `hours` NYSE_SESSION (KIT_OPEN_STATE is REHEARSAL/SHADOW/dev only) — [larp/strategy/execution_bounds.py:22-51](larp/strategy/execution_bounds.py).
- Top-level LIVE bounds — [larp/strategy/profiles.py:126-167](larp/strategy/profiles.py):

  | Key | Constraint |
  |---|---|
  | `slippage_bps` | 0 < s ≤ 50 |
  | `quote_age_seconds` | ≤ 30 |
  | `impact_bps` | ≤ 50 |
  | `impact_median_bps` | must equal the summary |
  | `minimum_trade_units` | ≥ measured formula and ≤ int(E × high × min w) |
  | `per_trade_cap_units` | ≥ full top position + reserve |
  | `exit_gas_reserve_units` | ≥ 5 × pair |
  | provenance | every value needs a decision ID plus a formula or data hash (profiles.py:78-90) |

- Windows: only order and the FINAL `signing_end` ≤ 2026-11-11T15:00Z are validated — [larp/strategy/schema.py:135-142](larp/strategy/schema.py). `validate_live` checks that `environment` ∈ {REHEARSAL, FINAL} but does not require the WINDOWS constant's dates — [larp/strategy/profiles.py:76-77](larp/strategy/profiles.py). The S2 builder path set custom windows this way — [docs/ledger/IDEA-089.md:190-192](docs/ledger/IDEA-089.md). The generator constant itself is code and is still unreconciled with PF-04 — [docs/INCOMPLETE_WORK.md:102](docs/INCOMPLETE_WORK.md).
- Profile CLI for S1: `--s1-config <block.json> --s1-decision <ID>`; the block's SHA-256 goes into provenance — [docs/ledger/IDEA-076.md:224](docs/ledger/IDEA-076.md), [larp/strategy/profiles.py:340-403](larp/strategy/profiles.py).

**Hard-coded (code change required)**
- S1 ceilings 95% gross / 30% weight / 35% hard line; 5-session evidence window; evidence-class map; equal-weight basket index — [larp/strategy/s1.py:32-38](larp/strategy/s1.py), [larp/strategy/s1.py:145-149](larp/strategy/s1.py), [larp/strategy/s1.py:180-195](larp/strategy/s1.py).
- Every weight must be > 0, so a 4-name S1 cannot be configured — [larp/strategy/s1.py:65](larp/strategy/s1.py).
- Ladder 3/8/12 and deep cut 40%; the 8% latch has no reset — [larp/risk/accounting.py:33-36](larp/risk/accounting.py), [larp/risk/planner.py:194-195](larp/risk/planner.py).
- 50 bp entry-cost cap and 2 × median impact cap; one wallet leg per round; S1 sort order; single global minimum across symbols — [larp/risk/planner.py:384-390](larp/risk/planner.py), [larp/risk/planner.py:452-455](larp/risk/planner.py), [larp/risk/planner.py:472-479](larp/risk/planner.py), [larp/strategy/profiles.py:160-162](larp/strategy/profiles.py).
- `review_sessions` == 5 — [larp/strategy/schema.py:86-87](larp/strategy/schema.py).
- EW LIVE allocations pinned to 1/5, 4/5, 1/4, 9/10, 3/4; EW 4 positions and one swap per session — [larp/strategy/profiles.py:121-137](larp/strategy/profiles.py), [larp/risk/planner.py:192](larp/risk/planner.py), [larp/risk/planner.py:378-380](larp/risk/planner.py).
- FINAL evidence scope (DISCRETIONARY_EXIT falsifiers, statement authority SHADOW, `assessment_required` false) — [larp/strategy/profiles.py:109-116](larp/strategy/profiles.py).
- Live trend series not wired; limiter producer limited to Class 2 — [larp/runtime/service.py:330-333](larp/runtime/service.py), [larp/integration/exposure.py:50-56](larp/integration/exposure.py).
- Rule-derived ceiling: the FINAL signing end — [larp/strategy/schema.py:140-141](larp/strategy/schema.py).

**Requalification a profile change triggers**
- The new profile hash is pinned in `runtime.json` and `execution.json`; the execution service refuses an unpinned profile — [larp/execution_live/main.py:77](larp/execution_live/main.py), [larp/execution_live/main.py:152](larp/execution_live/main.py), [docs/build/LD15_SIGNED_RELEASE_CHECKLIST.md:80](docs/build/LD15_SIGNED_RELEASE_CHECKLIST.md).
- A fresh M3 capture and numeric coverage review against the new sizes is required: full-position USDT within the signer `max_input_units`, the full-book exit reserve, per-child SELL quotes, and the initial BNB ≥ exit reserve. The tool always reports `OWNER_REVIEW_REQUIRED` — [larp/execution_live/caps_review.py:99-137](larp/execution_live/caps_review.py), [larp/execution_live/caps_review.py:202-221](larp/execution_live/caps_review.py).
- Isaac's approval of the exact profile hash and the reassembled `signer.json` is required (run-4 precedent) — [docs/ledger/IDEA-089.md:263-286](docs/ledger/IDEA-089.md).
- LD15: "A rebuilt profile or any further release-code change makes a new candidate that needs its own run; a PASS doesn't carry over." — [docs/build/LD15_SIGNED_RELEASE_CHECKLIST.md:52](docs/build/LD15_SIGNED_RELEASE_CHECKLIST.md).
- Live activation refuses any DRAFT or OPEN deviation row: "Final activation needs a final deviations register" — [larp/runtime/service.py:452-457](larp/runtime/service.py). DEV-02/03/04 (entry rule, sizing, cash floor) are DRAFT "until the S1 entry profile is frozen" — `config/release/deviations.v1.json` (DEV-02/03/04); [docs/build/LD15_SIGNED_RELEASE_CHECKLIST.md:50](docs/build/LD15_SIGNED_RELEASE_CHECKLIST.md) lists 9 DRAFT rows.
- A code change additionally needs a new release bundle, CI qualification and an LD15 receipt. Org GitHub Actions is billing-blocked and the mirror hit its artifact quota, so recent candidates used local bundles under explicit gate exceptions — [docs/ledger/IDEA-090.md:321-324](docs/ledger/IDEA-090.md), [docs/ledger/IDEA-089.md:205-218](docs/ledger/IDEA-089.md), [docs/ledger/IDEA-089.md:222-243](docs/ledger/IDEA-089.md).
- Timeline (team schedule, not organiser): "parameters frozen at the Oct 22 cut line; code frozen at final activation, Oct 27–29 (F-117)" — [docs/skill/SKILL.md:82](docs/skill/SKILL.md). "Plan to freeze the v1.0 candidate on Oct 26 so both readings hold" — [docs/skill/SKILL.md:291](docs/skill/SKILL.md). Ledger rule 5 forbids tuning on dev-phase or scored-run P&L — [docs/ledger/README.md:16](docs/ledger/README.md).

### Inferences
- These alternatives are reachable by profile only, each still needing coverage review, approval and deviation rows:
  - a static book at any gross ≤ 95% (set `high` and keep start UP, given no live series);
  - equal or re-tilted weights, e.g. 1/5 each, or down-weighting MSFTB to ≥ ≈ 0.098, which is the minimum weight allowed at 200 USDT;
  - a "static mid" book (start DOWN);
  - different limiter expiry;
  - a narrower or wider execution window and more attempts (up to 5);
  - a later new-risk end or earlier flatten (within signing end ≤ Nov 11 15:00Z);
  - slippage up to 50 bp. PF-06 says not to widen it automatically; a deliberate, documented change would be a new POLICY decision.
- These need code before final activation:
  - a working trend guard (series wiring);
  - the PF-02 reset;
  - per-symbol minimums or cost-ranked S1 entries;
  - a 4-name S1;
  - EW at other weights;
  - a regime/vol governor;
  - KIT_OPEN_STATE (24/7) hours for FINAL;
  - the PF-04 calendar in the generator (or hand-assembled windows).
- The cheapest change in requalification terms is to keep S1's code and only swap the `s1` block values and windows. Even that changes the FINAL profile hash, and the hash has to be produced anyway, because no FINAL S1 profile exists.

### Gaps
- No document states whether the organisers require any declaration update for a profile change (Q-13 says "[Yes.]" as an assumption that prompt/config-only changes need a full version event — [docs/skill/SKILL.md:273](docs/skill/SKILL.md)).
- The CAP-02 signer caps for the final wallet and any FINAL `signer.json` are not in the repo.

---

## 6. Rules that bound any alternative (verbatim where it matters)

### Takeaway
The official text constrains *what* may be traded and *how changes are made*, not how to size or time trades. Only five bStocks against USDT, long-only, no unrelated swaps, no human action during the run, and no build change after final activation. The proposed score is % change in wallet equity with fees and gas included; max drawdown breaks ties. The organisers also said they look at completed-trade PnL, drawdown, logs and repo together, and that not trading is penalised. Exact start/end instants, BNB in equity and scoring weights are still open. Everything numeric in §2 is team POLICY, except where tagged.

### Cited Findings
- F-43 (official page, verbatim): "Proposed FinalScore (%) = (Final Wallet Equity - Opening Wallet Equity) / Opening Wallet Equity x 100. The final rules will confirm the valuation method and treatment of transfers before onboarding." — [docs/official/source_page.md:104](docs/official/source_page.md), [docs/skill/SKILL.md:142](docs/skill/SKILL.md).
- F-44: "Real costs are reflected. Trading fees and gas reduce what remains in the wallet, and therefore reduce your final figure" — [docs/official/source_page.md:105](docs/official/source_page.md).
- F-45: "Tie-break: lower maximum drawdown — the largest percentage fall from a previous equity peak to a later low during the run. Still tied → shared rank" — [docs/official/source_page.md:106](docs/official/source_page.md).
- F-64: "Dedicated wallets — prohibited in both phases:" own or external funds; withdrawals, wallet-to-wallet transfers, bridging; "Unrelated swaps or arbitrary contract calls"; manual trading; "Leverage, shorting, derivatives" — [docs/official/source_page.md:135-140](docs/official/source_page.md), [docs/skill/SKILL.md:158](docs/skill/SKILL.md).
- F-91 (kit): "Only these five bStocks are eligible: NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB." — [docs/skill/SKILL.md:174](docs/skill/SKILL.md).
- F-95 (kit): "When `openState` is False (here or in `rwa/underlying-market`), the market is closed or trading is halted: don't place orders." — [docs/official/kit/bstocks-trading-guide.md:102](docs/official/kit/bstocks-trading-guide.md).
- F-114 (organiser chat): "Once the competition starts, no changes allowed — period." — [docs/skill/SKILL.md:200](docs/skill/SKILL.md).
- F-115 (organiser chat): "We want you to keep a stable, reliable trading state. When it comes to scoring, we'll look at your completed trades' PnL, drawdown, logs, and code repo all together to come up with a final score. And if you don't trade at all? That's definitely not what this competition is about." — [docs/skill/SKILL.md:201](docs/skill/SKILL.md).
- F-117 (paraphrase): "we can keep improving in the development period, but must halt once this period is over". Reading: the build registered at final activation runs unchanged; "no releases, hotfixes or switches to another build during the run" — [docs/skill/SKILL.md:203](docs/skill/SKILL.md).
- F-119: "Orders can be placed 24/7. The strategy in the guide is just my personal approach in a trading demo — treat it as a reference, not a requirement." (the `openState` guard is kept) — [docs/skill/SKILL.md:207](docs/skill/SKILL.md).
- F-120: first gas comes from USDT → BNB swaps in MetaMask (gas paid in USDT), "only before that wallet's first agent trade and never after the scored run starts". Sizing about 6 USDT for the final is [POLICY]; no BNB → USDT sell-back is [RULE-DERIVED: F-64] — [docs/skill/SKILL.md:208](docs/skill/SKILL.md).
- F-121: "All times are UTC+0." The exact start and end instants are still not stated — [docs/skill/SKILL.md:209](docs/skill/SKILL.md). F-122: only the final wallet counts — [docs/skill/SKILL.md:210](docs/skill/SKILL.md). F-123: "Swap between bStocks via USDT only" — [docs/skill/SKILL.md:211](docs/skill/SKILL.md). F-124: "Automatic restarts (engineering issues) — allowed. Manual restarts — not allowed." — [docs/skill/SKILL.md:212](docs/skill/SKILL.md).
- G-11 [RULE-DERIVED: F-48, F-66]: "Every limit in the current proposal/manifest is enforced by the risk governor. Changes go through a version event [RULE: F-60]; a logged reason for each change [POLICY]; limits are not loosened in response to a drawdown [POLICY]." — [docs/skill/SKILL.md:234](docs/skill/SKILL.md). Declared proposal values (≤ 4 positions, ≤ 20%/name, ≤ 80% gross; ladder 3/8/12→40; 50 bp entry cost) bind until changed by version event — [docs/skill/larp/plan.md:41-52](docs/skill/larp/plan.md). S1's departures are recorded as DRAFT deviations — `config/release/deviations.v1.json` DEV-02/03/04; [docs/ledger/IDEA-075.md:220-231](docs/ledger/IDEA-075.md).
- G-13 [RULE-DERIVED: F-64, F-48]: tokens only within {eligible bStocks, USDT}, "except USDT → native BNB swaps… for gas only… Gas is never swapped back: no BNB → USDT sale, at the end or otherwise" — [docs/skill/SKILL.md:236](docs/skill/SKILL.md).
- Q-03: the first-BNB part is answered by F-120; "whether BNB held counts in equity is still open (Q-39)" — [docs/skill/SKILL.md:255](docs/skill/SKILL.md).
- Q-06: "[UNRESOLVED — the stated dates span 15 calendar days vs '14 days' (I-08).]" Team position: flatten by Nov 11 15:00 UTC; "relaxing it is a strategy decision (Keith, DR-14)" — [docs/skill/SKILL.md:258](docs/skill/SKILL.md).
- Q-39: "How exactly is the run scored: weights of completed-trade PnL, drawdown, logs and code repo; are open positions at the end marked to market or only completed (round-trip) trades counted; is the F-43 % equity formula still the ranking; is BNB held counted? [UNRESOLVED; high priority…]". Team position: "maximise profit as the competition page defines it (final vs opening wallet equity, F-43)… being flat at the end (Q-06) makes the open-position reading moot." — [docs/skill/SKILL.md:290](docs/skill/SKILL.md).
- Q-40 / F-124: automatic same-build supervisor restarts only; a human HALT is treated as not allowed — [docs/skill/SKILL.md:291](docs/skill/SKILL.md).
- Never-do #1: no human trading or wallet actions during the run, apart from the pre-trade F-120 seeding — [docs/skill/SKILL.md:64](docs/skill/SKILL.md).

### Inferences
- No rule limits exposure level, weighting, trend logic or the number of trades. These are POLICY and are constrained only by G-11 (declared values need recorded deviations) and by F-115's "don't not trade".
- Because the run cannot be changed after activation (F-114/F-117/F-124), any fallback has to be pre-coded and pre-qualified in the activated build, for example the profile's own rules for drawdown, a missing trend input or execution failure.
- Flat by Nov 11 15:00 UTC gives up roughly the Nov 11 and Nov 12 US sessions of exposure (Q-06), which is a deliberate POLICY choice. Leftover BNB from the seed is a scoring unknown (Q-03/Q-39) that every strategy shares.

### Gaps
- Official scoring rules, valuation source and instant (Q-04), exact window instants (Q-06), BNB-in-equity treatment and the F-115 weighting (Q-39) remain unanswered in the repo. No official-rules document has been issued (F-52, SKILL.md §0.4).

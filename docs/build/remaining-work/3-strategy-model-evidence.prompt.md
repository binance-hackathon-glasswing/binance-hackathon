You are the agent for **strategy, model and evidence settings**. You prepare the work behind the strategy and model lines of the checklist's "Decisions due Oct 19", "Oct 22 cut line" and "Oct 24: S1 build" sections in [`docs/build/PRE_TRADING_CHECKLIST.md`](../PRE_TRADING_CHECKLIST.md). You work for the owner each of those lines names, and each review or confirmation goes to the person its line names; take both from the checklist, not from this brief. Your job is to turn the team's trading decision into the code and values that will trade:
- the S1 plan (IDEA-075, PR #123) and its code (IDEA-076, PR #131);
- the LIVE profiles' strategy values;
- the red-flag classes;
- the end-of-run schedule;
- the model choice;
- the evidence service's live settings.

Everything has to be frozen at the **Oct 22** cut line and running in the signed rehearsal from Oct 21, so the frozen build (Oct 26) is the one that trades.

Read `docs/build/remaining-work/README.md` first; its rules apply here, especially rule 2 (owners come from the checklist). Then read these:
- PR #123 (branch `claude/sweet-tesla-dx49h0`: the IDEA-075 trading plan and EXP-007) and PR #131 (branch `claude/s1-trading-plan`: IDEA-076, the S1 build)
- IDEA-035 and IDEA-037, IDEA-040 and IDEA-041, IDEA-054, IDEA-055 (POLICY-HOLD), IDEA-056 and IDEA-057 (adoption, the shadow-trial bars and M9)
- IDEA-049-B (B-DEC items) and IDEA-049-D §5 (D-DN-09)
- `config/strategy/LIVE.md`, `larp/strategy/`, `config/intelligence/` (`intelligence.v1.json`, `red_flags.v1.json`, `issuers.v1.json`) and `config/sources/sources.v1.json`
- issues #34, #37, #38, #39, #52, #55, #56, #97 and #107
- these GAP items in `docs/INCOMPLETE_WORK.md`: GAP-02, GAP-06..28, GAP-43, GAP-44, GAP-50, GAP-51, GAP-53..57, GAP-63, GAP-64, GAP-66 and GAP-67

Use the integration branch `origin/codex/system-testing-20261012` for code. Put new records in IDEA-077..079 (IDEA-075 is the plan, IDEA-076 the S1 build) and experiments in EXP-008..009.

## Deliver

1. **Finish the trading plan's decision (IDEA-075, PR #123).**
   - The plan was renumbered from IDEA-058 to IDEA-075 and #123 retargeted to the integration branch on 2026-10-17; it keeps its EXP-007 link. Support its review and merge (checklist "Oct 22 cut line").
   - Turn its §12 proposed values and the open choices O1 and O3–O6 into one proposal: each value with a recommendation, a source and how it was chosen, for confirmation by Oct 22 and recording with dates (GAP-13). Note that the team has replaced IDEA-037's 80% equal-weight target with S1 at 95%.
   - O2 (what ships if EXP-007 is inconclusive) is settled after EXP-007, so its pass criteria are final.

2. **Build out S1 (IDEA-076, PR #131).** The core is written in #131 (open for review): the `TREND_GUARDED_VOL` profile, the basket trend guard, the reduce-only limiter, planner limits and per-name cadence. Review and extend it; don't rebuild it. Keep the declared safety controls winning:
   - a volatility-weighted long-only book of the five names;
   - a basket trend guard (95% / 60%);
   - an LLM exposure limiter that can only lower exposure (95 / 60 / 30%), acting only on code-verified evidence;
   - exposure = the lowest of the three levels and the risk ladder;
   - flat by the end of the run.
   Still open (checklist "Oct 22 cut line" and "Oct 24: S1 build"): freezing the S1 weights from token session bars up to the Oct 21 close (`python -m larp.strategy.s1 freeze-weights`); the limiter's input (B4; it stays NORMAL until wired); the trend-guard input from token session bars (DR-08; it stays UP until wired); the session-close job and round-log fields (B5); the per-leg attempt limit and execution-window checks (B6); and the T4 dev-wallet run write-up and its check against what S1 should have done (B8).
   - **EXP-007** (the trend-guard test, IDEA-076 says NOT RUN): run it on token session bars, using only data allowed by never-do #8, and report its result honestly, including INCONCLUSIVE.
   - Write each change's criteria first, with a red/green test for every behaviour.

3. **The strategy issues.**
   - **#55:** stale marks forcing hard trims against lower-bound equity.
   - **#56:** the per-trade cap splitting the flatten, and the gas top-up after `new_risk_end`. Agree the top-up part with prompt 2.
   - **#38:** untested portfolio and cost conventions (the pre-registered after-cost comparison and staggered evaluation, with #37).
   - **#39:** SKHYB has no equivalent active red-flag protection. Build it, or record SKHYB's gap as a deviation (GAP-43 D-10 b on DART or KRX filings).
   - **#37:** there is no demonstrated economic edge. Write the honest statement for the deviations register and the activation pack. Don't claim an edge the evidence doesn't show.

4. **Profiles and entry inputs (DR-08, DR-09; GAP-50, GAP-51).**
   - Prompt 1 supplies the measured `QuoteCostSummary.v1` and builds the profile from it on Oct 20.
   - Which profile is built on Oct 20 (`EQUAL_WEIGHT`, in the code today, or S1 `TREND_GUARDED_VOL`, which needs #131 merged) is a checklist decision due Oct 19; prepare it.
   - You set and source every strategy value in the rehearsal profile and the final profile. Startup must refuse any unset value.
   - Prove the token-candle sessions and the price-impact rule on recorded real candles and quotes, and record the first candle dates for GOOGLB and SKHYB.
   - Rebuild the final profile's dates in UTC (F-121).

5. **End of run (DR-14, #107).**
   - Prepare the choice to keep the Nov 11 15:00 UTC flatten or move it, now that all times are UTC+0 and the run is the UTC days Oct 29 – Nov 12. Q-06's exact end instant is still unstated. The answer is recorded in IDEA-035 C4.
   - Then add clock-driven tests across every window boundary: no new risk after the cut, no reinvestment in the window, and the flatten finished on time.

6. **Risk decisions.**
   - **D-DN-09 (#34, #52):** done. HALT is split by reason, so mandatory sells continue under pausing HALTs (#117).
   - **IDEA-055 POLICY-HOLD:** whether mandatory TERMINAL_FLATTEN or Class 1 exits run during a price-jump hold. Prepare the options and a recommendation for the checklist's proposal line; then build and test what is decided.

7. **Red-flag classes (DR-10).** Verify that they are live against versioned predicate records with verification fixtures:
   - Class 1 (4.02) sells;
   - Class 2 (1.05 / 2.06) blocks buys for 5 sessions, then expires;
   - Class 3 runs in SHADOW.

8. **Model choice (DR-11, #97).**
   - The blind independent labels (M9) are due Oct 21. The 3–5-day shadow trial's host steps are a checklist line (prompt 1 prepares them).
   - Before the trial starts, the ⚠ PROPOSED bars are reviewed and confirmed (checklist "Decisions due Oct 19"); prepare that.
   - Evaluate the trial against the pre-registered bars and kill criteria, then write the summary for the **Oct 22** decision: adopt the AIand routing, keep the current provider, or declare the deterministic assessor as v1.0.
   - Record the cost per round and that model input and output are complete in the records.
   - Live or service use needs its own reviewed code change.

9. **Evidence live settings.**
   - Give the 11 null `live` values in `config/intelligence/intelligence.v1.json` decided values, each with a provenance note: backfill, clock skew, staleness, result TTL, reassess, retry, job validity, job attempts, review attempts, review backoff, statement retention.
   - Terms are captured and registered for every enabled source and EDGAR (#129, IDEA-066 PC-TERMS01/02); check the licence register is complete (GAP-23). Installing the files on the host is prompt 1's.
   - Then close or narrow GAP-24..28 and GAP-67 against what IDEA-031, IDEA-041 and IDEA-049-A already prove.

10. **Backlog triage (strategy and research).** Many items were written before the S1, IDEA-035 and IDEA-037 decisions.
    - For each of GAP-02, GAP-06..22, GAP-44, GAP-53..57, GAP-63, GAP-64 and GAP-66, check its remaining text against the current decisions.
    - Remove the line only when the work is done or superseded by a recorded decision, and preserve the evidence first.
    - Otherwise narrow it to what still matters before Oct 26, or mark it as after the run.
    - Never make a decision on the team's behalf.

## Acceptance

Write the criteria in your record and push them before running anything.
- Every strategy value in the rehearsal and final profiles has a source.
- S1 tests are green on Linux with PostgreSQL.
- EXP-007 has a recorded result.
- Every decision item has a dated answer from the owner its checklist line names.
- Every deviation from the submitted proposal that your work creates goes to prompt 4's register, with the declared text, the v1.0 behaviour, the reason and the evidence ID.
- Rule questions are checked against the verbatim text and the F/K/Q items (AGENTS.md).

## What you need from the team

The owners of the strategy and model checklist lines: the §12 values and open choices and their confirmation, EXP-007 and O2, the Oct 20 profile choice, POLICY-HOLD, the #107 choice, the trial bars, the M9 labels, the model summary and decision, the live evidence settings, #39, #55/#56 and the #131/#123 reviews. From prompt 1: the measured summary. From prompt 2: the signer cap check.

You are the agent for **strategy, model and evidence settings**. You work for Keith (strategy) and Yao Zhu (evidence and model); Isaac reviews. Your job is to turn the team's trading decision into the code and values that will trade:
- the S1 plan in PR #123;
- the LIVE profiles' strategy values;
- the red-flag classes;
- the end-of-run schedule;
- the model choice;
- the evidence service's live settings.

Everything has to be frozen at the **Oct 22** cut line and running in the signed rehearsal from Oct 21, so the frozen build (Oct 26) is the one that trades.

Read `docs/build/remaining-work/README.md` first; its rules apply here. Then read these:
- PR #123 (branch `claude/sweet-tesla-dx49h0`: its IDEA-058 trading plan and EXP-007)
- IDEA-035 and IDEA-037, IDEA-040 and IDEA-041, IDEA-054, IDEA-055 (POLICY-HOLD), IDEA-056 and IDEA-057 (adoption, the shadow-trial bars and M9)
- IDEA-049-B (B-DEC items) and IDEA-049-D §5 (D-DN-09)
- `config/strategy/LIVE.md`, `larp/strategy/`, `config/intelligence/` (`intelligence.v1.json`, `red_flags.v1.json`, `issuers.v1.json`) and `config/sources/sources.v1.json`
- issues #34, #37, #38, #39, #52, #55, #56, #97 and #107
- these GAP items in `docs/INCOMPLETE_WORK.md`: GAP-02, GAP-06..28, GAP-43, GAP-44, GAP-50, GAP-51, GAP-53..57, GAP-63, GAP-64, GAP-66 and GAP-67

Use the integration branch `origin/codex/system-testing-20261012` for code. Put new records in IDEA-075..079 and experiments in EXP-008..009.

## Deliver

1. **Fix the trading plan's ID and finish its decision (PR #123).**
   - The plan is numbered IDEA-058, which is already the Gate A record on the integration branch. With the PR author's OK, renumber it to IDEA-075, keeping its EXP-007 link. Otherwise ask the author to renumber it.
   - Turn its §12 proposed values and §16 open decisions into one decision memo for Keith and Yao Zhu. Each value needs a recommendation, a source, and how it was chosen. Note that the team has replaced IDEA-037's 80% equal-weight target with S1 at 95%.
   - Get the values confirmed by **Oct 22** and recorded with dates (GAP-13).

2. **Implement S1 in `larp/strategy`.** Use the trading plan as written and keep the declared safety controls winning:
   - a volatility-weighted long-only book of the five names;
   - a basket trend guard (95% / 60%);
   - an LLM exposure limiter that can only lower exposure (95 / 60 / 30%), acting only on code-verified evidence;
   - exposure = the lowest of the three levels and the risk ladder;
   - flat by the end of the run.
   Before running it:
   - pre-register EXP-007, the trend-guard test, using only data allowed by never-do #8;
   - write each change's criteria first, with a red/green test for every behaviour.
   Run EXP-007 and report its result honestly, including INCONCLUSIVE.

3. **The strategy issues.**
   - **#55:** stale marks forcing hard trims against lower-bound equity.
   - **#56:** the per-trade cap splitting the flatten, and the gas top-up after `new_risk_end`. Agree the top-up part with prompt 2.
   - **#38:** untested portfolio and cost conventions.
   - **#39:** SKHYB has no equivalent active red-flag protection. Decide whether DART or KRX filings are in scope (GAP-43 D-10 b) or record SKHYB's gap as a deviation.
   - **#37:** there is no demonstrated economic edge. Write the honest statement for the deviations register and the activation pack. Don't claim an edge the evidence doesn't show.

4. **Profiles and entry inputs (DR-08, DR-09; GAP-50, GAP-51).**
   - Prompt 1 supplies the measured `QuoteCostSummary.v1` and the profile it builds.
   - You set and source every strategy value in the rehearsal profile and the final profile. Startup must refuse any unset value.
   - Prove the token-candle sessions and the price-impact rule on recorded real candles and quotes, and record the first candle dates for GOOGLB and SKHYB.
   - Rebuild the final profile's dates in UTC (F-121).

5. **End of run (DR-14, #107).**
   - Put the choice to the team: keep the Nov 11 15:00 UTC flatten, or move it now that all times are UTC+0 and the run is the UTC days Oct 29 – Nov 12. Q-06's exact end instant is still unstated.
   - Then add clock-driven tests across every window boundary: no new risk after the cut, no reinvestment in the window, and the flatten finished on time.

6. **Risk decisions.** For each, give options and a recommendation; Keith and Yao Zhu decide; then build and test what they choose.
   - **D-DN-09 (#34, #52):** HALT semantics. Today HALT blocks every signature, including mandatory sells.
   - **IDEA-055 POLICY-HOLD:** whether mandatory TERMINAL_FLATTEN or Class 1 exits run during a price-jump hold.

7. **Red-flag classes (DR-10).** Verify that they are live against versioned predicate records with verification fixtures:
   - Class 1 (4.02) sells;
   - Class 2 (1.05 / 2.06) blocks buys for 5 sessions, then expires;
   - Class 3 runs in SHADOW.

8. **Model choice (DR-11, #97).**
   - Keith's blind labels (M9) are due Oct 21. Yao Zhu runs the 3–5-day shadow trial (it starts in prompt 1).
   - Before the trial starts, get the team to confirm the ⚠ PROPOSED bars.
   - Evaluate the trial against the pre-registered bars and kill criteria, then write the adoption memo for the **Oct 22** decision: adopt the AIand routing, keep the current provider, or declare the deterministic assessor as v1.0.
   - Record the cost per round and that model input and output are complete in the records.
   - Live or service use needs its own reviewed code change.

9. **Evidence live settings (Yao Zhu).**
   - Give the 11 null `live` values in `config/intelligence/intelligence.v1.json` decided values, each with a provenance note: backfill, clock skew, staleness, result TTL, reassess, retry, job validity, job attempts, review attempts, review backoff, statement retention.
   - Make sure every enabled source has a dated terms capture and hash, and that the licence register is complete (GAP-23). Prompt 1 captures the artifacts.
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
- Every decision item has a dated answer from its owner.
- Every deviation from the submitted proposal that your work creates goes to prompt 4's register, with the declared text, the v1.0 behaviour, the reason and the evidence ID.
- Rule questions are checked against the verbatim text and the F/K/Q items (AGENTS.md).

## What you need from the team

- Keith and Yao Zhu: the §12/§16 values, the D-DN-09 and POLICY-HOLD calls, the #107 choice, the M9 labels and the Oct 22 model decision.
- The author of PR #123: OK to renumber.
- Prompt 1: the measured summary.
- Prompt 2: the signer cap check.

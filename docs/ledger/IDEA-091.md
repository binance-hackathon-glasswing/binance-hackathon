> **PR276-RV01 reviewed status (2026-10-24):** the original proposal below is retained as authored. Its universal
> return claims, profit-effect rankings, static-book characterization, gas/slippage recommendations and claimed
> simulations are superseded by the [reviewed report](../research/strategy-alternatives-20261024/report.md) and
> [review results](#pr276-rv01-results--pass-for-documentation-merge-2026-10-24-sgt). No strategy change is adopted.

# IDEA-091 — Strategy alternatives research: execution first, equal 1/5 weights, retire the inert trend guard

- Date / author: 2026-10-24 / requested in a Claude Code session; research, report and record by Claude Code
- Status: **open — research and recommendations only.** Nothing here is decided, adopted or implemented. No
  backtest, live run, profile, config, code, wallet, host or model action was taken.
- Base: canonical `codex/system-testing-20261012` at `59c878c0` (PR274 merged).
- Files: report [`../research/strategy-alternatives-20261024/report.md`](../research/strategy-alternatives-20261024/report.md);
  the five research notes behind it in [`../research/strategy-alternatives-20261024/notes/`](../research/strategy-alternatives-20261024/notes/)
  (current strategy baseline, portfolio construction and risk, timing signals and events, tokenized-stock
  execution, competition strategy and LLM agents).
- Related: IDEA-075/076 (S1), IDEA-084 PF-01/02/04/06, IDEA-037 (EQUAL_WEIGHT), EXP-007, EXP-008, IDEA-089/090
  (S2, run 4), IDEA-063 (quote costs); SKILL.md F-43, F-115, F-117, F-119, F-120, Q-03, Q-06, Q-39.

## What

A review of the current strategies (S1 `TREND_GUARDED_VOL` as planned for the final, the EQUAL_WEIGHT fallback and the
S2 weekend test), how they behave as built, and which alternatives could raise expected profit in the scored run
(Oct 29 – Nov 12, 2026) inside the rules and the build freeze at final activation (Oct 27–29, F-117). Ranked by
evidence, expected effect and what each costs to qualify before the freeze.

## Findings (as built at `59c878c0`)

- **S1 runs as a static ~95% book.** `larp/runtime/service.py:330-333` builds `ContextBuilder` without `series`, so
  the context carries `series: {}` (`larp/integration/runtime.py:119,196`) and `evaluate_trend` returns
  `TREND_INPUT_UNAVAILABLE`, keeping the UP start state (`larp/strategy/s1.py:127-130`). Checked from source by the
  coordinating session, not only by the notes.
- The live limiter producer emits Class 2 evidence only (`larp/integration/exposure.py:50-56`), so SEVERE (30%) is
  unreachable.
- A 95% → 60% cut at 1/5 weights is about 14 USDT per name, below the 18.637 USDT minimum trade, so neither a trend
  nor a CAUTION cut would trade at 200 USDT. The 12% deep cut (mandatory) is the one loss control that acts at full size.
- The 8% buy stop is latched for the run (`larp/risk/accounting.py:33`); PF-02's below-5% reset is not built.
- No FINAL S1 profile exists, the inverse-σ weights are not frozen, and the generator's FINAL windows still differ
  from the PF-04 calendar.
- Run 4 (S2, dev wallet): 1 of 4 signed buys completed; 3 aborted at the requote under the 8 bp slippage limit
  (S2-F6). The S2-F2..F6 fixes are merged but have not run live. No live sell or flatten evidence yet.
- Costs are lower than older figures: quote round trips 2–5 bp (MSFTB 17 bp); live gas 0.0000242 BNB per
  approve + swap against a 0.000384 BNB reservation.
- External evidence: 1/N is hard to beat out of sample; unlevered volatility management and stop rules lower
  expected return; no short-horizon timing signal (trend, reversal, calendar, FOMC, earnings drift, LLM news,
  weekend token prices) clears costs over this window. EXP-008 (EW better for profit) points the same way.

## Ranked recommendations (for the owners to decide)

| Rank | Change | What it takes | Expected profit effect |
|---|---|---|---|
| 1 | Get the book built: run the merged S2 fixes live including a sell; `slippage_bps` 8 → about 20 (≤ 50) as a recorded decision; `max_attempts_per_leg_session` 3 → 5 | Profile values + one live dev cycle | First-order: decides whether ~95% of equity is invested at all |
| 2 | Equal 1/5 weights in the S1 block instead of frozen inverse-σ | Profile only (the run-3/S2 configuration) | Small positive; removes the unrun weight freeze |
| 3 | Retire the trend guard for v1.0 (declare it static; do not wire series) | Profile or deviation note | Avoids the −0.33 to −0.50 pp a working guard cost in EXP-008; no change from today's inert build |
| 4 | Build the FINAL profile on the PF-04 calendar | Profile | ~+0.05 pp; flatten starts in session |
| 5 | Size the MetaMask gas seed to the buy gate plus measured spend (~4 instead of ~6 USDT) | Operational, before the first trade | 0 to ~+1 pp, depending on whether BNB counts in equity (Q-03/Q-39) |
| 6 | Tilt toward high-volatility names within the 30% cap | Profile | ~0, sign unknown; more variance |
| 7 | Code options (PF-02 reset, CPPI cushion, wired guard, 100% gross, later flatten, per-name minimums, 24/7 FINAL hours) | New code, bundle, LD15 run | ≤ ~±0.1 pp each or drawdown only; not worth requalifying before the freeze |
| 8 | Signal overlays (LLM buy signals, reversal/momentum tilts, weekend fades, earnings/FOMC rules) | Code | Negative after costs |

Highest-value items outside the strategy code: one live buy-and-sell cycle with the S2 fixes before the freeze, and an
organiser answer on whether BNB held counts in final equity and whether only completed trades count (Q-03/Q-39; only
the team may ask).

## Before any of this changes live behaviour

- Ledger rule 2: each adopted change needs its own decision ID and pass criteria committed before any run. Nothing
  here is pre-registered.
- Ledger rule 5: no recommendation is tuned on dev-wallet or scored P&L. Run 4 is used only for fill/abort mechanics;
  EXP-008 is historical proxy data.
- Any profile change is past the team's Oct 22 parameter cut line (SKILL.md §0.4), produces a new profile hash and
  needs a fresh coverage review, Isaac's profile and `signer.json` approval, new run pins and final deviation rows.
- Owners per existing records: next-run and final strategy choice, Yao (IDEA-089 "After the test"); S1 profile and
  planner, Keith (IDEA-090, PF-IMPL01); profile and `signer.json` approval, Isaac; review, Keegan.

## Caveats

- Several 2026 sources are company-reported or secondary (crypto press, aggregators); the notes flag each. Earnings
  dates for Alphabet and the NVIDIA date are expected, not all confirmed.
- The report omits the notes' synthetic simulations (top-3 probabilities, CPPI numbers) except qualitatively; they use
  assumed volatilities, not measured ones.
- EXP-008's Yahoo data is research-only (plan D-09 forbids it as a data source); nothing here proposes it for runtime.
- The notes were not re-verified line by line by the coordinating session beyond the `series` finding above.

## PR276-RV01 — independent documentation review (Isaac/Codex, 2026-10-24 SGT)

Original research head `5d5b5e28`; base canonical `59c878c0`. Review criteria before numerical or documentation
validation: (1) each operational claim matches source at this immutable base; (2) no team policy becomes an organiser
rule; (3) literature findings retain their population/model assumptions and access grades; (4) no unregistered,
unreproducible simulation or stale cost statistic becomes a measured result; (5) proposed parameter, gas and strategy
changes remain unadopted with named owners and existing qualification gates; (6) preserve original source leads and
immutable original text, repair local links, and verify a docs-only diff. No new strategy experiment is authorized.

Findings to repair:
- R1: unsupported universal return/ranking claims, deterministic small profit-effect forecasts, and a concentration
  recommendation inferred from assumed rival distributions; replace with conditional comparisons and uncertainty.
- R2: code wiring findings need scope: an UP-initialized trend state with missing series is not a guarantee that a
  fully invested95% book runs; min-trade arithmetic is conditional on equity, weights, gaps and the selected profile.
- R3: final trade/flat gates are PF-04/IDEA-035 policy, not challenge deadlines. F-43 is proposed and F-115/Q-39 leave
  scoring interpretation unresolved. First-BNB bootstrap is already answered by F-120; only valuation remains open.
- R4: two notes assert200000-draw simulations without committed criteria/code/seed/receipts. These are unreproduced
  claims, not experiments accepted by this ledger, and cannot support probability/CPPI/effect-size tables.
- R5: the execution note mixes old13–56bp proxy estimates with current quote evidence, gives unsupported numeric
  slippage/gas advice, suggests standing allowances/direct RPC submission, and infers too much from3/4 generic
  mismatch errors. Preserve exact-amount approvals, authorized minima, the Web3 broadcast path, gas/cap qualification
  and distinguish planned/approved/swap-signed/completed states.
- R6: event confirmations and research results must come from checked primary sources; unavailable or secondary-only
  sources remain leads, not confirmed event dates or deployable signals. Preserve every original external source URL
  in the corresponding reviewed note's lead register; original prose is retained at immutable head `5d5b5e28`.

Method: checked source/official captures and primary web sources; rewrite the synthesis and scope the notes to what
this review can support. This is a research-document acceptance, not approval of a strategy, parameter exception,
private-data evaluation, runtime change, live run, funding change, service use or release.

## PR276-RV01 results — PASS for documentation merge (2026-10-24 SGT)

Acceptance is for the corrected research documents only. R1–R6 above are repaired in the report and five notes:
- R1/R4: unsupported numerical profit/rank forecasts, universal return claims and two unregistered simulation
  tables withdrawn. No new simulation, market-data fetch, model call or backtest was run. Original prose remains
  immutable at `5d5b5e28`; unreproduced claims there are not accepted experiment evidence.
- R2: missing series preserves previous/start state, not guaranteed holdings; limiter reachability is scoped to the
  current producer. The 14 USDT reduction example names its equity/weight/reserve assumptions and selected minimum.
  Other mandatory controls and incomplete PF-02/PF-04 work remain explicit.
- R3: checked the verbatim page, trading guide, kit reference and SKILL F/K/Q entries. PF-04 is team policy;
  F-43 is proposed and F-115/Q-39 still qualify scoring. First-gas bootstrap is settled by F-120; BNB valuation remains
  open. Hours permission retains `openState` and does not remove S2's dev scope.
- R5: corrected four execution records versus signed swaps; generic mismatch/expiry is not a unique diagnosis.
  Retained authorized minima, exact-amount approvals and Web3/local-signing path. Dated proxy quotes/gas are not
  current all-in fill costs, a selected replacement slippage value, spike tolerance or a smaller FINAL seed approval.
- R6: primary-source checks distinguish full-text result sections, indexed abstracts, metadata, unavailable links
  and unverified leads. Event schedules are dated, with independently checked UTC conversions; no directional edge
  is inferred from a calendar. All 282 original non-repository URL entries (counted per file) remain in lead registers;
  immutable originals and source hashes preserve provenance. Unverified links are not availability or rights claims.

Validation (prospective criteria committed/pushed at `0d666b79` before checks): Python3.12.14 standard-library
assertions PASS for original-source URL retention, 54 research relative-file links, conditional sizing/reserve
arithmetic and six UTC conversions including the DST boundary. Final added-line file/fragment checks: 65 PASS.
`git diff --check` PASS; diff is docs-only.
Full application tests were not rerun for these documentation changes; no CI pass is claimed.
[Review receipt](../build/evidence/pr276-review-20261024.json) /
[original provenance](../build/evidence/pr276-original-sources-20261024.json).

Open items retain their existing owners and records: Keith/Keegan PF-IMPL01 and PF-04; Yao/Isaac later dev execution,
sell/flatten and reconciliation under IDEA-089/090/S2-F2; Yao/team any strategy reopening; Isaac exact
profile/signer/gas/caps acceptance. Any new hypothesis requires prospective criteria and pushed code; any adopted
change needs the existing parameter exception, decision/deviation, coverage, run-pin and release gates. No backlog
line is closed, runtime/profile changed, deployment/funding authorized or organiser message sent by this review.

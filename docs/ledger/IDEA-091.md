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

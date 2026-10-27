# IDEA-110 — Micro activation self-check: a sub-1-USDT FS1 self-check buy, then the mandatory sell

- Date / author: 2026-10-28 SGT (2026-10-27 UTC) / drafted with Claude Code at the user's request
- Status: open (criteria registered before implementation and tests; candidate profile not approved, installed or bound)
- What: an opt-in variant of the IDEA-093 SC activation self-check (GAP-74, F-125) whose BUY pays less than 1 USDT,
  so the final-wallet end-to-end check costs cents instead of a 32 USDT round trip. The same pipeline runs: the
  runtime gathers market/quote/evidence data each round, the policy decides the self-check BUY, the independent
  planner admits it, execution requests and validates the exact quote, signs through the signer, waits for
  settlement, then the next round's mandatory SELL flattens the whole position and the round logs are delivered.
  Only two entry gates change for that one BUY (below). Everything else, including the scored FS1 run that follows
  in the same run, is FS1's.
- Why it matters: FS1's self-check BUY must be an ordinary FS1 entry (≥ the 18.64 USDT minimum, about 32 USDT)
  because a smaller leg fails the 50 bp entry-cost gate: approve+swap gas alone is about 0.054 USDT (summary
  `quotes-complete-20261020`: SKHYB approve + swap ≈ 7.52e-5 BNB × 722.15 USDT/BNB), about 6 % of a 0.9 USDT leg.
- Cost / risk: the round trip costs about 0.11–0.15 USDT (two legs of gas plus 20 bp authorized slippage and spread),
  about 12–17 % of the traded amount but < 0.1 % of the 200 USDT wallet. The variant changes the profile hash, so
  it needs the same owner approval as any FS1 profile (Isaac: profile/signer; Keegan: code/release; Yao: install).
  Open risk: the Web3 Open API's minimum order size for a sub-1-USDT bStock buy has not been measured; if the API
  refuses the quote, the check stays WAIT/EXPIRED and nothing is bought (no fallback to a bigger trade).
- Links: F-120, F-125, F-127; GAP-73, GAP-74; IDEA-093 SC; IDEA-109; [FS1 profile](../build/evidence/fs1-final-20261025/README.md).

## 1. Design (registered before implementation)

1. `activation_self_check` gains one optional key, `max_cost_units` (USDT micro-units). Without it the block, its
   validation and planner behaviour are unchanged, so every existing profile (FS1, FS1 recovery, S-series) keeps its
   exact bytes and hash.
2. With `max_cost_units`: `0 < max_cost_units <= cost_reserve_units`, and `pay_units` may lie below
   `minimum_trade_units` (still `1 <= pay_units <= per_trade_cap_units - cost_reserve_units`).
3. For the self-check BUY only (reason `ACTIVATION_SELF_CHECK_BUY`, phase BUY, the self-check symbol), the planner
   replaces the minimum-trade-value check and the bps `ENTRY_COST_CAP` with an absolute cap: refused as
   `SELF_CHECK_COST_CAP` when the authorized-minimum cost (spread/slippage + fee + expected gas) exceeds
   `max_cost_units`. All other gates still apply: the buy window, run/daily halts, health `new_spending_ok`, market
   open state, measured round trip, quote validity/age/route/slippage/impact, `ENTRY_IMPACT_CAP`, cost reserve,
   gas/BNB, cash and exit-gas reserve, execution attempt budget and the signer's own checks.
4. The SELL is the existing mandatory self-check SELL (unchanged).
5. Builder: `tools/deploy/build_final_candidate.py --micro-self-check` builds the variant from the same FS1 inputs:
   `pay_units` 900,000 (0.9 USDT), `max_cost_units` 150,000 (0.15 USDT; expected ≈ 0.056 USDT), symbol SKHYB (the
   existing cheapest-round-trip rule), and the window below.
6. Window (F-127: code cutoff and pause 2026-10-28T10:00Z; handoff target flat with logs by 17:30 SGT):
   `buy_after` 2026-10-27T17:00Z (01:00 SGT Oct 28, after the server components and signer are installed),
   `buy_until` 2026-10-28T08:00Z (16:00 SGT), `flat_by` 2026-10-28T09:30Z (17:30 SGT). FS1's own window
   (flat by Oct 28 23:00Z) extends past the pause; the micro variant does not.

## 2. Pass criteria (registered before running any test)

- MSC-1: profiles without `max_cost_units` validate and plan exactly as before; the FS1 and FS1-recovery builders
  still reproduce `fs1-final.json` / `fs1-final-recovery.json` byte for byte; the existing SC tests pass unchanged.
- MSC-2: validation refuses `max_cost_units` that is zero, negative, non-integer or above `cost_reserve_units`, and
  still refuses `pay_units` below the minimum when `max_cost_units` is absent.
- MSC-3: with the micro block in its window, the planner emits one non-mandatory SKHYB BUY of about 0.9 USDT (not
  above `pay_units`); outside the window, nothing.
- MSC-4: a self-check BUY whose cost exceeds `max_cost_units` is refused as `SELF_CHECK_COST_CAP` and no intent is
  emitted; run/daily halt, `new_spending_ok` false and closed markets still stop it.
- MSC-5: an ordinary (non-self-check) discretionary BUY below `minimum_trade_units` is still refused, and one above
  the 50 bp entry cap is still `ENTRY_COST_CAP`, in a profile carrying the micro block.
- MSC-6: after the BUY settles, the SELL is mandatory for the whole position; once flat the phase is DONE and the
  scored FS1 run follows (no new buy before `trade_after` except the self-check).
- MSC-7: the micro builder output passes `validate_live`, differs from `fs1-final-recovery.json` only in
  `activation_self_check` and its provenance, and is reproducible byte for byte.
- MSC-8: the full strategy and risk test directories pass.

## 3. Results

(not run yet)

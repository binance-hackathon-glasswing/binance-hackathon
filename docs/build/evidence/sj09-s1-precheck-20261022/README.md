# SJ-09-PC01: can the installed build run the planned S1 swap? (2026-10-22)

**Short answer: not as planned.** The SJ-09 plan (IDEA-049-C SJ-09, PR249) swaps the equal-weight dev rehearsal for an
S1 `TREND_GUARDED_VOL` run on Oct 24. In the installed build RC4 `d03bbb1` (larp/ and config/ are byte-identical on
canonical `f56bcf6`), three code checks refuse that swap. Even with them fixed, S1 at about 100 USDT behaves almost
like equal weight, so the swap would test little that the current run does not.

This is an offline code check by the assistant. It is not a pre-registered experiment and not an owner decision.
No port, key, AWS or live call was used. Reproduce with:

    python3.12 -I docs/build/evidence/sj09-s1-precheck-20261022/verify.py   # exit 0 = every check as recorded

`result.json` is the output at `ad208e2` (this branch after merging canonical with PR249, PR253 and PR257; the first run at `f56bcf6` gave the same results). The S1 block is the test fixture (`tests/strategy/test_s1_core.py`, equal
weights 1/5), not Keith's frozen weights. The gas, authority and cost inputs are the RC4 rehearsal ones
(`tools/deploy/build_rehearsal_candidate.py`).

## Findings

| Check | Result | Where |
|---|---|---|
| C1 | An S1 REHEARSAL profile builds and passes `validate_live`, but only with `evidence_mode` BOUNDED_FALSIFIER and `falsifier_authority` DISCRETIONARY_EXIT. | `larp/strategy/profiles.py` |
| C2 | **S1 with SHADOW evidence and falsifiers (the LD11-RH01 scope) is refused:** "Live profile differs from decided v1 scope". The SHADOW exception covers only REHEARSAL + EQUAL_WEIGHT. | `profiles.py` `validate_live` |
| C3 | **Signed preparation without reviewed model routing is refused for any S1 profile**, SHADOW or not: `gate_a.scoped_rehearsal` requires EQUAL_WEIGHT. The equal-weight profile `e95d5842…` passes the same check (control). | `larp/runtime/gate_a.py` `prepare` |
| C4 | **A new run cannot start from a wallet that holds stocks:** `gate_a.initial_state` refuses with "Existing stock holdings require reviewed cost-basis history", and `gate_a_check` recomputes the initial state the same way. On Oct 24 the wallet will hold the equal-weight positions (flattening starts Oct 26 00:00Z), so the swap's "chain start including positions" has no code path. | `gate_a.py` `initial_state` |
| C5 | At 100 USDT expected equity the measured minimum trade is 18.637420 USDT. **Every frozen weight must be at least 0.1962**, so the five weights must be almost exactly 1/5. Inverse-volatility weights such as 15/17/20/22/26% are refused at build: "Measured minimum cannot fit a full position at REHEARSAL". | `build_live_profiles` |
| C6 | Using the S1 planner fixture scaled to the rehearsal's minimum-to-equity ratio (0.1867): a flat book buys, but **an UP→DOWN trend change holds every name** (`LOW_TURNOVER_HOLD`, no intent). With a minimum of 1 unit the same state sells toward 60% (control). The trend guard and limiter cuts are smaller than one minimum trade, so they cannot act at this size. S1 buys stop altogether if equity falls below 98.191685 USDT (start equity 99.845905 USDT including BNB at the pinned price). | `larp/strategy/policy.py`, `larp/risk/planner.py` |
| C7 | The S1 builder sets the exit reserve to 5 × action = 0.00192 BNB, one child per position (open item LD10-P03-R1). Two children per position need 0.00384 BNB, which leaves 0.001486 BNB of the 0.005326 BNB held at install for every other action, before day 1's gas. | `build_live_profiles` |

A side finding: `validate_live` turns every specific refusal into "Malformed or incomplete live profile",
because `ContractError` is a `ValueError` and its `except (KeyError, TypeError, ValueError)` re-wraps it. Anyone
building the S1 profile on Oct 23 sees only that message. `verify.py` reads the inner cause. A fix (re-raise
`ContractError` unchanged) is a runtime change, so it belongs in the next release, not RC4.

## What this means for SJ-09 (options for Yao, Keegan, Isaac and Keith)

1. **Keep the equal-weight run through the rehearsal window.** No new build, database, `signer.json` or approval.
   It already tests the signed path, costs, receipts and the flatten. Test S1 offline or in shadow instead. This
   has the least risk before the Oct 27 cutoff.
2. **Swap as planned, with a new release (RC5).** It needs at least: (a) a reviewed chain-start rule that carries
   positions with cost basis from the retired run's ledger (C4); (b) a decision to allow a scoped deterministic S1
   rehearsal in `validate_live` and `gate_a.scoped_rehearsal` (C2, C3), or adopted hosted models; (c) the
   two-child exit reserve in the S1 builder (C7). Then mirror CI, a new LD15 receipt, a new `signer.json`, Isaac's
   approval and the P3–P5 install, all by Oct 24. The S1 weights would still have to be about 1/5 (C5), and the
   trend guard could not trim (C6).
3. **Swap with hosted models adopted** (routing file, budget, `model_adoption_ref`). This removes C2 and C3 but
   not C4, so it still needs RC5 or a flat wallet, and the agent cannot flatten before Oct 26.

None of these is decided here. Adding capital to make S1 meaningful is not proposed: wallet funding is the owners' decision.

## Update 2026-10-23: the J8 incident removes C4 as a blocker

The equal-weight run never traded: from about 20:45Z on Oct 22 its database logins timed out and every service
restart-looped (IDEA-049-C SJ-06 J8 incident). The wallet is still 96 USDT and BNB at nonce 4, with no stocks. So the
next run starts stock-flat, and C4's refusal does not apply to it. The SJ-09 path is now also the install path for
RC5, which adds IDEA-085's connection pooling (PR257, merged). C2, C3, C5, C6 and C7 are unchanged: an S1 run still
needs reviewed model routing or a scoped deterministic S1 rehearsal decision, weights of about 1/5, the
two-child exit reserve, and its trend guard cannot trim at this size. C0 now compares only the runtime files these
checks exercise, since canonical's `larp/storage` and `larp/runtime/database.py` changed with IDEA-085.

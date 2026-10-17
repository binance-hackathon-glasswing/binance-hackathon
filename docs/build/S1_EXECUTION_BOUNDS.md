# S1 execution bounds — IDEA-076 EB-01 / Isaac B6

The `TREND_GUARDED_VOL` profile now requires an explicit `execution` object inside
its `s1` block. Other baselines keep their existing behavior. Existing S1 profile
inputs must be rebuilt with this object; missing fields are refused rather than
filled from defaults.

This is an example of IDEA-075 §12's **proposed**, not frozen, values:

```json
{
  "execution": {
    "open_delay_seconds": 1800,
    "close_buffer_seconds": 900,
    "max_attempts_per_leg_session": 3
  }
}
```

Pass the complete S1 block through the existing `--s1-config` and `--s1-decision`
profile-builder options. The supplied bytes and decision reference remain pinned
by profile provenance and the release manifest. No live parameters or profiles
are installed by this change. Delay/buffer support 0–14,400 seconds each; attempts
support 1–5. A short session whose resulting window is empty permits no
discretionary trade.

## Session window

The runtime takes open, close and next-open timestamps from its hash-pinned
`USRegularSessions.v1` calendar. Discretionary BUY and SELL legs are eligible only
in `[open + delay, close - buffer)`. This follows the calendar across early
closes, holidays, weekends and daylight-saving changes. `openState`, slippage,
exact-input quote economics and the existing cost/impact gates still apply.

Mandatory stock sales bypass this window. Their session runs from the latest
regular open until the next actual regular open; there is no midnight/weekend
reset. Gas top-ups retain their separate controls.

Every S1 intent records `S1ExecutionBounds.v1` with its session, leg, attempt
ordinal and validity interval. Command expiry is clamped to that interval. The
execution guards, signer service and final broadcast release independently check
the durable round's bounds against current time. Unbroadcast authority is revoked
when it expires; receipt reconciliation continues for every possible submission.
An approval already sent can finish reconciliation after the window, but cannot
authorize a new swap outside it.

## Attempts and quote follow-ups

An attempt is a bounded quote/economic-action chain for one
`(symbol, BUY/SELL, discretionary/safety)` leg. Separate safety and discretionary
lanes prevent failed entries or discretionary sales from consuming a mandatory
exit's allowance. Both lanes have the explicit configured maximum. Exhausted
mandatory requirements remain outstanding with `LEG_ATTEMPT_LIMIT`; they are not
treated as completed. The owner must confirm these proposed values and this retry
scope against measured costs before activation.

The planner consumes a slot when it evaluates a leg's quote or requests its
missing exact-input quote. Cost, route and quote refusals keep the spent slot.
It requests one S1 wallet leg at a time, so names whose quotes are never requested
do not lose their allowance. Existing driver quote-round limits still bound
refinement. A quote child can share its parent's slot only through a committed
parent-round reference, matching profile/session/leg/interval/ordinal and an
exact-input quote the parent requested. Ordinary fresh rounds cannot reuse it.

`execution_attempt_budget` is committed in the same PostgreSQL transaction as the
round plan. It survives closure, failed execution, restarts and settlement, and
resets at the next regular-session open. No new database migration is needed.
Counters, bounds, parent provenance, quote requests and rejection/cost evidence
are included in normal round logs. Recorded-port replay reconstructs them from
the journal, including parent/child relationships, without network calls.

## Remaining acceptance

Isaac and Keith still review real quote-cost coverage and approve the execution
parameters/profile hashes. Keegan retains B5 scheduling and release integration;
Yao Zhu retains host setup; all owners retain the signed rehearsal and Gate B/C
checks. Verified router evidence, #27 lifetimes, #44 signer policy, native tracing
and first-wallet acceptance are separate gates. Offline tests authorize none of
those actions.

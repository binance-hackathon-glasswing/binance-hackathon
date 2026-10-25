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
exit's allowance. IDEA-102 removes the configured session maximum from mandatory
SELL legs in new runtime rounds. They receive at most one new attempt per leg
per UTC 15-minute slot, refused with `MANDATORY_RETRY_SPACING` within that slot.
Discretionary BUY/SELL legs retain `max_attempts_per_leg_session` and
`LEG_ATTEMPT_LIMIT`. Ordinals continue increasing for audit. All existing gas,
window, health, HALT, allowance-recovery and strict preflight guards still apply.
The exit reserve continues to protect buys; an affordable mandatory sale may
consume it. Profile hashes and configured discretionary ceilings do not change.

New rounds record runtime-owned `execution_attempt_policy: MANDATORY_CADENCE_V1`.
Historical journals without it retain their original configured maximum for both
lanes and replay with their original plan bytes.

The planner consumes a slot when it evaluates a leg's quote or requests its
missing exact-input quote. Cost, route and quote refusals keep the spent slot.
It requests one S1 wallet leg at a time, so names whose quotes are never requested
do not lose their allowance. Existing driver quote-round limits still bound
refinement. A quote child can share its parent's slot only through a committed
parent-round reference, matching profile/session/leg/interval/ordinal and an
exact-input quote the parent requested. Ordinary fresh rounds cannot reuse it.
An issued intent or terminal quote refusal closes that slot. Even if execution
later ends NOT_SUBMITTED, an old parent cannot reopen it. IDEA-097 S4-F1 refunds
only an explicitly tagged never-claimed expiry of the latest attempt in the same
session; any recorded broadcast prevents the refund. Ordinary aborts retain their
spent ordinal. A refund retains the mandatory leg's last-slot timestamp, so it
cannot admit another new attempt in the same slot. The signer also binds window authority to the actual planned
tokens, exact input and minimum output, so a BUY cannot borrow a safety SELL's
after-hours exception.

`execution_attempt_budget` is committed in the same PostgreSQL transaction as the
round plan. It survives closure, failed execution, restarts and settlement, and
resets counts at the next regular-session open. Optional `last_ms` timestamps
survive a count refund and session rollover; unknown legs, invalid integers and
future timestamps are refused. No new database migration is needed.
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

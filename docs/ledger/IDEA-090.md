# IDEA-090 — S2-F2/S2-F3 fix: a planner decision round every slot, and the child plans its parent's leg (handoff)

- Date / author: 2026-10-24 / Yao Zhu (decision), Claude Code (record and design notes)
- Status: **open, not implemented.** This entry is the handoff for Yao's team: the problem, the evidence, a proposed
  design, and pass criteria written before any code. Implementation and review are the team's.
- Owners: Keegan (driver, `larp/runtime/driver.py`), Keith (S1 timing and planner). Review: the other of the two.
- Related: IDEA-089 finding S2-F2 and the S2-F2 backlog line (PR272), IDEA-076 / IDEA-084 PF-01 (S1), IDEA-088 (quote
  verifier), IDEA-050 (round driver).

## Decision (Yao, in chat, 2026-10-24)

"yes update that we want to fix our final strategy as well" and "dont implement the fix, write a docs pr for my friends
to finish the implementation and review". S2-F2 is fixed before the final run, not accepted as a limit.

## Problem

The planner can only trade inside a round, and outside evidence jobs (filings, reviews) the driver makes one cadence
round per 15-minute slot. `larp/runtime/driver.py` `EvidenceWork._cadence`:

```python
slot = now_ms // self.cadence
...
issuer = self.issuers[slot % len(self.issuers)]
records = self._latest(issuer, now_ms)
if not records:
    return None  # nothing to assess for this slot's issuer
```

So a slot whose rotating issuer has no evidence records produces **no round at all**, and the planner gets no chance to
act in it. `EvidenceWork.next` is `_review or _ingested or _cadence`; there is no other path.

## Evidence (runs 2, 3 and 4)

Every cadence round seen in the signed dev rehearsals sits in a slot with `slot % 5` in {2, 4}:

| Run | Cadence rounds (slot, UTC) |
|---|---|
| 2 (RC5) | 1991922 (04:30), 1991924 (05:00), 1991927 (05:45), 1991929 (06:15) |
| 3 (RC6) | 1991969 (16:15), 1991972 (17:00) |
| 4 (RC7) | 1992024 (06:00, the first signed BUY, SKHYB) |

So only two of the five issuers have records, and the planner can trade in 2 of every 5 slots. In run 4 the SKHYB
buy filled in the 06:00Z round; no round ran at 06:15Z or 06:30Z (read-only check: no stuck state, no errors, no
reservations), and the remaining buys can only come at 06:45, 07:15, 08:00 and 08:30Z.

**Why it matters for the final:** S1's entries, rebalances, trend-guard and limiter trims, and any mandatory exit
outside the flatten window can be delayed by 30–45 minutes, or indefinitely if no issuer has records (for example
early in a run, or if the evidence poller stops). Trade timing should not depend on which issuer happens to have a
filing.

**Side effect found at the same time:** after the 06:00Z round, `execution_attempt_budget` showed
`DISCRETIONARY:BUY:GOOGLB: 1` although no GOOGLB quote was requested. The S1 planner (`larp/risk/planner.py`, the loop
over `actions` with `execution_bounds.reserve`) reserves the next leg's attempt and adds its quote request in the same
plan that already carries the SKHYB intent; the driver's `_quotes` then returns because `plan['intents']` is set. Each
such plan spends one of the next name's attempts for nothing (`max_attempts_per_leg_session` is 3 in S1, 5 in S2).

## Proposed design (for the implementers to confirm or change)

1. **A decision round every slot.** Keep `_review` and `_ingested` first. In `_cadence`, when the slot's issuer has
   no records, do not return None:
   - **Option A (smaller):** pick the next issuer, in the fixed `issuers` order starting at `slot % n`, that has
     records, so a round runs whenever any issuer has records.
   - **Option B (complete):** when no issuer has records, still start a planning-only round for the slot, with the
     prior accepted evidence (the `_signed_cycle` "safety" round already does this with `use_accepted_evidence=True`
     and a `SAFETY_TICK` job).
   - Recommended: A plus B, so a slot always plans. The round ID stays `cadence:{slot}#{attempt}`, one per slot, and
     the job payload records the issuer actually used (replay reads it from the journal, not from the store).
2. **One wallet leg at a time, for real.** In the S1 branch of the planner, stop after the first leg that produced an
   intent or a quote request: do not call `execution_bounds.reserve` for a further leg in that plan. The comment there
   already states the intent ("Do not spend attempts for quotes the driver never requests").
3. **The child plans its parent's leg (S2-F3).** In a quote follow-up round (`execution_parent` present), put the
   parent's requested leg (`execution_parent.quote_requests`) first, so the executable quote it fetched is the one
   used; and give near-equal legs a stable order (for example compare notionals rounded to the money scale before
   the symbol tie-break) so a fresh price inside the child cannot re-order them. Evidence: run 4 at 06:45Z, TSLAB
   quote executable, child requested NVDAB instead and planned nothing (IDEA-089 S2-F3).
4. **No change** to evidence review rounds, quote follow-ups, the kit `openState` guard, caps, signer, execution
   admission or the S2 rehearsal profile.

## Pre-registered pass criteria (before any code)

| # | Pass when | How |
|---|---|---|
| F1 | With evidence records for only two of five issuers, a cadence planning round runs in every 15-minute slot | driver test with a fake evidence store, 10 consecutive slots |
| F2 | With records for every issuer, round IDs, chosen issuers and plans are byte-identical to today's (no regression) | existing driver tests plus a slot-by-slot comparison |
| F3 | With no records for any issuer (Option B), each slot still plans with prior accepted evidence, and a mandatory sell due in that slot is planned in that slot | driver + planner test |
| F4 | One round per slot: a restart inside a slot, or a recovered interrupted round, does not create a second cadence round for it; replay reproduces the journal | existing recover/replay tests extended |
| F5 | An S1 plan that carries an intent reserves no attempt for another leg (`execution_attempt_budget` unchanged for other names) | planner test reproducing the run-4 SKHYB/GOOGLB case |
| F8 | A quote follow-up whose parent requested leg X plans X when X's quote is executable, even if another leg's notional is marginally larger at the child's prices | planner test reproducing run 4's TSLAB/NVDAB case |
| F6 | Full suite on Python 3.12 with PostgreSQL 14.24, test commit red on base first | as in IDEA-088 |
| F7 | Rehearsal check before the final: in a dev run, rounds appear in consecutive slots in `checks/trading-status.sh` | operator, next dev run |

Fail or partial: record it here; do not loosen the evidence, `openState` or execution guards to make rounds appear.

## Not covered

- Run 4 (`larp-dev-rehearsal-20261024-s2`, RC7 `2d160073`) keeps running as it is; a run cannot change build.
- The final strategy choice (S1 or another version, Monday) and its profile hash are separate decisions; this fix
  goes into whichever build the final uses, with its own release, run and approval.

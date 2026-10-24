# IDEA-092 — S3: S2 with a scheduled sell-all at 12:00 SGT Sunday, then S2 resumes

- Date / author: 2026-10-24 (~13:00Z; Saturday evening in Singapore) / team request in a Claude Code session (record
  and implementation: Claude Code)
- Status: **requested; design and pass criteria pre-registered below, before code or tests.** Not approved,
  built into a release, or installed.
- Related: IDEA-089 (S2, run 4), IDEA-090 (S2-F2..F6), IDEA-076 (S1), SKILL.md §0.3 #1 (no manual trading), F-95.

## Request (in chat, 2026-10-24)

1. "Create a new strategy S3 that initially sells all the stocks, then proceeds with S2 as per normal"
2. "Make it automatically sell at 12 noon"

**Reading (assistant; the requester can change it).** At a fixed time the agent itself sells every held bStock. It
buys nothing new until the book is flat, then S2 runs as usual for the rest of its window. The sell is agent code
(mandatory SELL legs, round-logged), not a manual action (§0.3 #1).
- **"12 noon" means 12:00 SGT on Sun Oct 25, which is 2026-10-25T04:00:00Z.** The request came at Sat 20:5x SGT. This
  is the only coming noon inside S2's buy window (`new_risk_end` Sun 08:00Z).
- 12:00 UTC Sunday was not chosen because it falls inside S2's own terminal flatten (09:00–15:00Z), where S3 would
  add nothing.
- The time is a builder argument, so another time needs only a rebuilt profile, not new code.

## Design

- **Profile key `scheduled_flatten_at`** (an ISO-8601 UTC instant) on top of the S2 profile. Every other value is S2's
  (window, sizes, caps, the S1 block with `KIT_OPEN_STATE` and 5 attempts per leg). `policy_id` is
  `larp-s3-rehearsal-v1`.
- **Scope:** `validate_live` accepts the key only when all of these hold:
  - the profile is a REHEARSAL carrying S2's `KIT_OPEN_STATE` hours (so S2-1's SHADOW/`dev` scope applies);
  - `trade_after < scheduled_flatten_at < new_risk_end`.
  - Profiles without the key are unchanged byte for byte.
- **Phases (one helper, `larp/strategy/scheduled_flatten.py`, used by both the policy and the planner):**
  - **Before the time:** plain S2.
  - **From the time until flat (PENDING):**
    - every held name gets a mandatory SELL requirement, reason `SCHEDULED_FLATTEN`, sold through the mandatory lane
      exactly like the terminal flatten (balanced exit children, `openState` check kept);
    - no BUY is planned (`SCHEDULED_FLATTEN_PENDING`), even when a held name cannot be sold this round (price-jump
      hold, closed market, missing mark).
  - **DONE:** the first round at or after the time that sees no stock units and no reservations records
    `scheduled_flatten: DONE` in the persisted risk state. DONE is never undone.
- **After DONE: S2 as normal, from a fresh book.**
  - S1's policy blocks re-entry into a name it has ever held unless a fresh review exists. That rule is why S2's book
    is "built once and then held" (IDEA-089 S2-4).
  - After DONE, S3 lifts that block so S2 can rebuild its five-name book. Red-flag blocks, the window,
    `openState`, caps, the per-name leg budget and the attempt budget are unchanged.
- **Unchanged:** the terminal flatten (`flatten_start`, `signing_end`), the signer, execution admission, caps, gas,
  logging.
- **Failure mode:** if a name cannot be sold (unexecutable residual, repeated refusals), DONE never comes and S3 stays
  in cash for the rest of the window, then the terminal flatten runs as usual. That is a finding, not a reason to
  bypass a guard.

## Known limits (recorded before testing)

- **Install needs a stock-flat wallet.** `gate_a.initial_state` refuses a wallet that holds stocks ("Existing stock
  holdings require reviewed cost-basis history").
  - Run 4 (S2) holds stocks now and flattens only from Sun 09:00Z, after S3's noon. So S3 cannot be installed this
    weekend unless run 4 is retired flat first; a new run cannot "sell run 4's stocks".
  - S3's noon sell only sells what S3 itself bought. Whether to retire run 4 early, or rebuild S3 with a later time
    and window, is the team's decision (Yao; approval Isaac).
- **Attempt budget.** The whole weekend is one S1 session, so the 5 BUY attempts per name (S2-9) and the 3
  discretionary legs per name are shared by the buys before and after noon. The mandatory noon sells use their own
  SAFETY lane. If the morning buys used most attempts, some rebuys may end in `LEG_ATTEMPT_LIMIT`.
- **Not for the final.** Like S2, S3 is a dev REHEARSAL profile only.

## Pre-registered pass criteria (written before code or tests)

| # | Pass when | Evidence |
|---|---|---|
| S3-1 | Before `scheduled_flatten_at`, an S3 round plans exactly what the same round plans under S2 | synthetic planner test |
| S3-2 | At/after the time with stocks held, every held name gets a mandatory SELL requirement with reason `SCHEDULED_FLATTEN`, a mandatory SELL intent/quote request is planned, and no BUY is planned | synthetic planner test |
| S3-3 | While PENDING, a BUY stays refused (`SCHEDULED_FLATTEN_PENDING`) even when the held name is not sellable this round | synthetic planner test |
| S3-4 | Once flat with no reservations, the round records `scheduled_flatten: DONE` in `risk_state` and the policy proposes S2 re-entry buys for names held before (the S1 `ever_held` block is lifted only after DONE) | synthetic policy/planner tests |
| S3-5 | DONE persists: a later round with stocks held again plans no `SCHEDULED_FLATTEN` sell | synthetic planner test |
| S3-6 | `validate_live` refuses a malformed time, a time outside `trade_after`..`new_risk_end`, a FINAL profile and a profile without S2's hours; S2's committed profile still validates and rebuilds byte for byte | profile tests |
| S3-7 | The committed S3 profile rebuilds byte for byte, differs from S2's only in `scheduled_flatten_at`, `policy_id` and their provenance, and passes `validate_live` and a signed dev `gate_a.prepare` with `gate_a_check` | profile tests |
| S3-8 | Strategy, risk, integration and runtime test suites pass with no new failures | pytest output |
| S3-L1 (live, team) | In an installed S3 run: the first round at/after the time sells every position, round-logged with `tx_hash`; the balance check is MATCH when flat; S2 buys resume after DONE; then IDEA-089 P2–P6 | chain monitor, `checks/trading-status.sh`, BscScan |

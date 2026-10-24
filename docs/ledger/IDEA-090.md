# IDEA-090 — S2-F2/S2-F3 fix: a planner decision round every slot, and the child plans its parent's leg (handoff)

- Date / author: 2026-10-24 / Yao Zhu (decision), Claude Code (record and design notes)
- Status: **implemented 2026-10-24, review pending** (branch `claude/zen-meitner-luu8xj`; results below). This entry
  began as the handoff for Yao's team (problem, evidence, proposed design, criteria before any code). A Claude Code
  session then implemented it on request; Keegan and Keith still review it as owners, and F7 needs the next dev run.
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

### Added 2026-10-24 (implementation, before the F9 test was written)

**Finding S2-F4 — a better-than-mark BUY quote is dropped with one follow-up round.** When the follow-up's quote would
receive more tokens than the target (the quote is about 2 bps or more better than the mark), the planner asks for a
smaller quote (`BUY_RECEIVE_TARGET_REQUOTE`). With `max_quote_rounds: 1` (`config/runtime/runtime.example.json`, which
`gate_a.prepare` turns into every run's `runtime.json`), the driver stops there, the round plans nothing and the next
round reserves a new attempt. An exploratory check in the S1 planner fixture (not a pass test) showed: at −10 bps the
child requests 37950023 instead of 37980000, and a second follow-up with that quote plans the intent on attempt 1.

| # | Pass when | How |
|---|---|---|
| F9 | A parent → follow-up → second follow-up chain with a better-than-mark quote plans the parent's leg on the parent's attempt (ordinal 1, no other leg's count), and the example runtime config allows two follow-up rounds | planner chain test; config test |

**Finding S2-F5 (found while checking replay for S2-F2) — a signed-path round with an assessment does not replay.**
`_signed_cycle` starts its ready-assessment rounds with `use_accepted_evidence=True`, which adds
`assessment_available` to the policy context, but the round record does not say so and `larp/runtime/replay.py` starts
every round without it, so replay of such a round diverges (`Deterministic replay diverged`). No existing test replays
a signed-path journal. Affects audit replay (DR-19) of a signed final, not trading.

| # | Pass when | How |
|---|---|---|
| F10 | A round started with this round's assessment and `use_accepted_evidence=True` (the signed path's ready round) replays to the same head, as do planning-only rounds (F4) | driver-harness replay test, red on base first |

Fail or partial: record it here; do not loosen the evidence, `openState` or execution guards to make rounds appear.

## Implementation and results (2026-10-24)

Code commits on `claude/zen-meitner-luu8xj`, each test commit red on base first: `6c67a6ee` (F1–F5 tests), `fc07f23e`
(S2-F2), `2a353e8e` (F8 tests), `ec7b3b85` (S2-F3), `b2dc560b` (F9 tests), `9d74d91b` and `a403143a` (S2-F4 config),
`5e121da2` (F10 test), `7ee4fef1` (S2-F5).

**What changed, and the design choices against the proposal above:**
1. **S2-F2, Option B only** (`larp/runtime/driver.py`). A slot whose issuer has no records runs a planning-only round,
   `cadence:{slot}#n`, job reason `SCHEDULED_DECISION`, started with `assessment_override=None,
   use_accepted_evidence=True` (the same mode as the signed path's safety round). A slot whose issuer has records is
   unchanged (F2). **Option A was not built:** taking the next issuer with records would reassess the issuers that have
   records two to three times as often, adding model calls on the signed path and changing the evidence review cadence
   that the S2-F2 backlog line says to keep. Option B alone gives a round every slot. On the signed path,
   planning-only items are ignored (it already plans on every tick).
2. **Design item 2 (stop after the first leg) was not needed.** F5 passes on base: the S1 loop already ends after an
   intent (`break`) and after a quote request. The run-4 `GOOGLB 1` count matches S2-F3 instead: a follow-up that
   sorted another leg first spends that leg's attempt (the F8 reproduction leaves exactly the parent's leg plus the
   re-sorted leg in the budget).
3. **S2-F3** (`larp/risk/planner.py`, `larp/strategy/execution_bounds.py requested_legs`). S1 actions sort as
   (sell first, the parent's requested leg first, notional in whole cash units descending, symbol). The parent
   preference applies only when `execution_parent` is from the same session; whether its attempt may be reused is
   still `_reuse`'s decision.
4. **S2-F4** (`config/runtime/runtime.example.json` and the AIand shadow example, which must mirror it):
   `max_quote_rounds` 1 → 2, so a smaller requote after a better-than-mark quote can complete in the same round.
5. **S2-F5** (`larp/runtime/coordinator.py`, `larp/runtime/replay.py`). A round started on accepted evidence records
   `accepted_evidence`: `ONLY` (no assessment attempted) or `WITH_ASSESSMENT` (the signed path's ready result). Replay
   starts it the same way. The key is absent from every other round, so their bytes do not change.

| # | Result | Evidence |
|---|---|---|
| F1 | **pass** | `test_f1_…`: 10 consecutive slots with records for 2 of 5 issuers give 10 rounds; the 6 slots without records are planning-only (`accepted_evidence` `ONLY`, no assessment, no `ASSESSMENT_UNAVAILABLE`, the policy ran). Red on base in those 6 slots. |
| F2 | **pass** | `test_f2_…`: job IDs equal the old payload digest, assessment present, no new key; all 21 existing `test_driver.py` tests pass, with D3 updated because it asserted the old skip. |
| F3 | **pass** | `test_f3_…`: after a 4.02 filing makes the reduction mandatory, the next slot of an issuer without records plans the mandatory SELL in that slot. Red on base (no round). The "no issuer has records" case is the same code path (the slot's issuer has none). |
| F4 | **pass** | `test_f4_…`: one round per slot across ticks and a restarted driver; an interrupted planning-only round retries as `#2`; the journal replays to the same head. Without the replay change the replay diverges (checked by reverting it). |
| F5 | **pass on base** (regression guard) | `test_f5_…`: a plan with an intent reserves only that leg's attempt. See design note 2. |
| F6 | **partial** | Linux, PostgreSQL **16.15** (14.24 not available here). Python 3.13.17: 2632 passed, 11 skipped, 1 failed (`test_m01_cli_verify_with_service_config_and_host_profile`: the host profile compares installed packages with the release locks; this venv is not the lock set). Python 3.12.3: the same, 2632 passed, 11 skipped, 1 failed (the same host-profile test). Before the changes, the same setup failed only that test plus 25 tests that needed boto3/botocore/numpy, which were installed for the later runs. |
| F7 | open | Operator, next dev run: rounds in consecutive slots in `checks/trading-status.sh`. |
| F8 | **pass** | `tests/strategy/test_child_keeps_parent_leg.py`: a one-unit price move on other names, or a whole-unit larger notional, no longer re-sorts the follow-up; it plans the parent's leg on attempt 1 and spends no other leg. A fresh round is not re-ordered by a sub-unit move; a parent from another session does not steer. Red on base. |
| F9 | **pass** | `tests/strategy/test_requote_follow_up.py`: parent → follow-up (smaller requote) → second follow-up plans the leg on attempt 1; the example config allows two follow-ups (red on base). |
| F10 | **pass** | `test_f10_…`: a round started with its assessment and `use_accepted_evidence=True` replays to the same head. Red on base (`Deterministic replay diverged`). |

**Consequences for review (Keith, Keegan):**
- **Attempts are spent faster.** Planning every slot means up to four quote rounds an hour per leg instead of about
  1.6. With S1's 3 attempts per leg per session, a quote that keeps failing (verifier or venue outage) can exhaust a
  leg's attempts in about 45 minutes. The limits themselves are unchanged (parameters are frozen).
- **More rounds are logged.** Every round is logged, hold-only rounds included (never-do #12): up to 96 cadence rounds
  a day at 15 minutes, plus follow-ups, instead of about 38.
- **Quote requests.** Up to two follow-up rounds a round (one extra quote request when a requote is needed).
- **Not changed here:** the run-sheet order that let the first post-P4 intent expire before P5 (IDEA-089) is a sheet
  matter for the final install.

### Suspected finding S2-F6 — run 4, 07:15Z: approve confirmed, swap never sent (2026-10-24 08:2xZ, unconfirmed)

Chain facts (public RPC, 08:17Z): at 07:15:42Z (block 129472187) the dev wallet approved 18.940509 USDT to the router
(nonce 6, status 1, tx `0x865ada0e…957d`). No swap followed: nonce 7 both `latest` and `pending`, USDT unchanged at
77.048279, and the 18.940509 USDT allowance to the router is still open. No transaction at the 08:00Z round either.

**Most likely cause (code reading, not yet confirmed from the database):** after the approve is final, the execution
service re-quotes the swap (`larp/execution_live/venue.py quote`, same `slippage_bps` 8 as the planning quote,
`larp/execution_live/main.py` line 92) and `validate_payload` (`larp/execution.py`) requires the fresh quote's encoded
`minimum_output >= intent.minimum_output`, the planning quote's minimum. With the same slippage on both sides that means
**the fresh quote must return at least as many tokens as the planning quote**: any adverse move between planning and
the post-approve requote blocks the swap ("encoded swap economics mismatch/expired"). After `max_prepare_probes` (3)
blocked probes, or at `valid_until`, the intent aborts unsigned (`NOT_SUBMITTED`, `ABORTED_BEFORE_SWAP_BROADCAST`),
leaving the approval open. The 06:00Z buy passed because its requote was not worse. Other possible causes: the
untrusted-router preflight refusing, gas above the authorized limit, or the authority expiring.

**To confirm (SSM operator, primary):** `checks/trading-status.sh` for the 07:15Z round's execution record: its
`blocked_reason` and the NOT_SUBMITTED reason. If confirmed, this applies to the final as well (same code). A fix would
re-request the post-approve quote with a slippage that makes its minimum equal the intent's authorized minimum (never
wider than the profile's limit), so the swap goes through whenever the fresh output is still above the authorized
minimum; it needs its own pass criteria and Isaac/Keegan review (execution and signer path).

### S2-F6 fix: pass criteria (written 2026-10-24 before any S2-F6 test was run)

Fix (`larp/execution_live/venue.py LiveVenue.quote`): when the fresh quote's minimum is below the intent's authorized
minimum but its output is still above it, request the quote once more with the largest whole-bps slippage `s'` with
`output × (10000 − s') / 10000 ≥ intent.minimum_output`, only when `1 ≤ s' < intent.max_slippage_bps`. Every existing
check applies to the second quote unchanged, and `validate_payload` still requires `minimum_output ≥
intent.minimum_output`. Nothing is ever requested wider than the intent's slippage limit.

| # | Pass when | How |
|---|---|---|
| F11 | A post-approve requote whose output moved against the plan by less than the slippage limit prepares the SWAP (minimum ≥ the authorized minimum), where the current code blocks it | executor test: approve → final → swap prepare with a fake Web3 client applying the requested slippage; red on base |
| F12 | The second request's slippage is a whole number of bps with `1 ≤ s' <` the intent's limit; no request is ever wider than the limit | venue test recording every request's `slippagePercent` |
| F13 | No second request when the first quote already meets the minimum (one request, unchanged bytes), when the output is below the authorized minimum, or when `s'` would be 0; those cases behave as before | venue tests |
| F14 | The second quote goes through every existing check (vendor, mode, minimum ≤ output, slippage bound, cash cap, decode); one that still misses the minimum blocks the probe as before | venue and executor tests |
| F15 | Full suite: no new failures against the F6 runs above | as F6 |
| F16 | Operator: confirm from run 4's 07:15Z execution record that S2-F6 is this cause (`blocked_reason`, `NOT_SUBMITTED` reason) | `checks/trading-status.sh` |

### F16 — S2-F6 confirmed from run 4's database (2026-10-24 ~09:00Z)

Read-only `checks/trading-status.sh` on the primary over SSM (command `636400b6-bbf7-445c-9dad-eaae346e45b5`, run from a
Claude Code session as IAM user `larp-claude-session`; one READ ONLY transaction, public values only). All units
active with 0 restarts, no HALT, run not quarantined; 15 rounds, all closed. Execution records (all terminal):

| Round | Intent amount (USDT) | Attempts | Status | `blocked_reason` |
|---|---|---|---|---|
| `cadence:1992024#1/quote1` (06:00Z) | 18.951721 | approve nonce 4, swap nonce 5 | COMPLETED | — |
| `cadence:1992029#1/quote1` (07:15Z) | 18.940509 | approve nonce 6 only | ABORTED | `encoded swap economics mismatch/expired` |
| `cadence:1992032#1/quote1` (08:00Z) | 18.928356 | none (blocked at the pre-approve requote) | ABORTED | `encoded swap economics mismatch/expired` |
| `cadence:1992034#1/quote1` (08:30Z) | 18.932548 | approve nonce 7 only | ABORTED | `encoded swap economics mismatch/expired` |

Events: 3 × `ABORTED_BEFORE_SWAP_BROADCAST`; signing requests 4, signatures 4, **refusals 0** (the signer and its
policy are not the cause). `max_slippage_bps` 8 on every intent. **F16 passes:** the swaps were blocked by
`validate_payload`'s economics check on the execution service's requote, in 3 of 4 buys; at 08:00Z already at the
pre-approve requote, seconds after the planning quote. That message also covers a swap deadline outside the
authority, but the same path passed at 06:00Z and fails intermittently, which fits the minimum-output comparison under
price noise, not a fixed deadline mismatch. The S2-F6 fix (F11–F14) covers both requotes. Run 4 keeps RC7 and stays
exposed, including the Sunday flatten's SELL swaps.

### S2-F6 fix: results (2026-10-24)

Commits: `05f0687e` (criteria), `b2da84f8` (tests, red on base), `de86fd0b` (fix), `bf1e6a31` (F16).

| # | Result | Evidence |
|---|---|---|
| F11 | **pass** | `tests/execution/test_requote_at_authorized_minimum.py`: the executor prepares and sends the approve, finalizes it, and the swap requote after a 5 bps adverse move is `PREPARED` with a minimum ≥ the authorized one (requests at 8, 8, then 3 bps). On base the same test reproduces run 4's `encoded swap economics mismatch/expired`. |
| F12 | **pass** | Four adverse moves inside the limit: the second request is whole bps, 1 ≤ s' < 8; no request is wider than 8. |
| F13 | **pass** | One request when the first quote meets the minimum (bytes unchanged); no second request at or below the authorized minimum or when s' would be 0. |
| F14 | **pass** | A second quote that fell again is returned and then blocked by `validate_payload` as before; a second response from another vendor or with a minimum wider than the limit is refused by the existing checks. |
| F15 | **pass** | Python 3.12.3, PostgreSQL 16.15: 2638 passed, 11 skipped, 1 failed, the same host-profile lock test as in F6; no new failures. `tests/execution`, `tests/marketdata`, `tests/signer`: 576 passed, 1 skipped. |
| F16 | **pass** | See above: 3 of run 4's 4 buys were blocked by this check. |

Review: Isaac (execution and signer path) and Keegan. Next dev run: buys go through after the approve.

## Not covered

- Run 4 (`larp-dev-rehearsal-20261024-s2`, RC7 `2d160073`) keeps running as it is; a run cannot change build.
- The final strategy choice (S1 or another version, Monday) and its profile hash are separate decisions; this fix
  goes into whichever build the final uses, with its own release, run and approval.

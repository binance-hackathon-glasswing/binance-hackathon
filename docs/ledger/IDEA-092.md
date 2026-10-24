# IDEA-092 — S3: S2 with a scheduled sell-all at 12:00 SGT Sunday, then S2 resumes

- Date / author: 2026-10-24 (~13:00Z; Saturday evening in Singapore) / team request in a Claude Code session (record
  and implementation: Claude Code)
- Status: **implemented and tested offline 2026-10-24 (S3-1..S3-8 PASS; see the end of this entry).** Not approved,
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
  - **DONE:** the first round at or after the time that sees every stock at or below `dust_units` and no
    reservations records `scheduled_flatten: DONE` in the persisted risk state. DONE is never undone. (The dust
    tolerance was added after H2 below, before the full-suite run.)
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

## Handoff notes from the requester (2026-10-24, "pass these on so the S3 install doesn't fail halfway")

| # | Note | Status in this change |
|---|---|---|
| H1 | The wallet must hold no stocks before run 5 starts: `gate_a.initial_state` (`larp/runtime/gate_a.py:185`, called by `gate_a.prepare`) refuses any non-zero stock balance. If S3 is meant to start while run 4's stocks are still in the wallet, that check needs a REHEARSAL-only change that carries over run 4's holdings and their purchase costs. | **Open, not implemented.** A carry-over changes accounting (cost basis, opening equity, P&L) and needs Isaac's and Keegan's review. Until then, start run 5 only once the wallet is flat. |
| H2 | Dust counts: Sunday's flatten can leave balances at or below `dust_units`, and the same check rejects those too. | **Inside S3: handled.** The switch treats balances at or below `dust_units` as flat (`scheduled_flatten.state`). **At install: open.** `gate_a.initial_state` still rejects any non-zero balance, dust included (the S2/S3 profiles have `dust_units` 0, so the planner sells every positive balance). A dust tolerance there belongs with H1. |
| H3 | The sell-everything has to happen once: a one-time switch that turns off once the wallet is flat, with buys blocked until then; otherwise it also sells what S3 buys afterwards. | **Implemented.** `scheduled_flatten: DONE` is committed in the risk state on the first flat round and never undone. While PENDING every BUY is refused (`SCHEDULED_FLATTEN_PENDING`). Tests: S3-3, S3-4, S3-5. |

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

## Implementation and results (2026-10-24, assistant; branch `claude/vigilant-carson-krj1sw` from `codex/system-testing-20261012` `a0409d19`)

**Code.**
- `larp/strategy/scheduled_flatten.py` (new): the `scheduled_flatten_at` check, the scope check, and the one-time
  switch `state()` (None/BEFORE/PENDING/DONE).
- `larp/risk/planner.py`: from the time, every held name is capped at 0 with reason `SCHEDULED_FLATTEN` (urgency equal
  to the terminal flatten). While PENDING a BUY is refused (`SCHEDULED_FLATTEN_PENDING`). DONE is written to `risk_state`.
- `larp/strategy/policy.py`: after DONE, S1's re-entry gate also passes for names held before (`fresh_book`).
- `larp/strategy/profiles.py`: `validate_live` calls the S3 scope check.
- `tools/deploy/build_rehearsal_candidate.py`: `--scheduled-flatten-at` (bare = `2026-10-25T04:00:00Z`) builds S3 from an
  S2 block. It refuses the option without S2's hours.

**Profile.** `docs/build/evidence/s3-rehearsal-profile-20261024/`:
- file SHA-256 `2fb32b8e9ba342192ad57b61059654409ffbe3fad04e900c1887053a263f1526`;
- `StrategyProfile.v1` digest `127ce7968c19c8bc27ffa12c92341d2ce33a5aa71d7243c1952a32eb30157eb9`;
- M3 probe `142e1b06eb59b985f7680cbf96a0f7ae9a58ad3089b8bcd812e99c3bcce8085e`.

S2's profile still rebuilds byte for byte (`eb55d76a…`).

**Results** (`tests/strategy/test_s3_scheduled_flatten.py`, 11 tests):

| # | Result |
|---|---|
| S3-1 | PASS: before the time, intents, quote requests, rejections and requirements equal S2's (flat and held books) |
| S3-2 | PASS: both held names get `SCHEDULED_FLATTEN` mandatory SELLs, no BUY; execution admission (`permitted`) admits the SELL through the SAFETY lane |
| S3-3 | PASS: a held name on price-jump hold still blocks every BUY (`SCHEDULED_FLATTEN_PENDING`; S2 on the same snapshot buys); reservations or a balance above `dust_units` keep it PENDING, dust counts as flat |
| S3-4 | PASS: a flat book records DONE and rebuys names held before; S2, or S3 before its time, keeps them in cash |
| S3-5 | PASS: with DONE recorded, held names get no scheduled sell and the plan equals S2's |
| S3-6 | PASS: malformed time, a time at/after the window edges, unset value, FINAL and a profile without S2's hours are refused |
| S3-7 | PASS: profile rebuilds byte for byte; differs from S2 only in `scheduled_flatten_at`, `policy_id` and their provenance; `validate_live`, signed dev `gate_a.prepare` + `gate_a_check`, dev runtime build pass; builder refusals |
| S3-8 | PASS (qualified): full `tests/` on this branch **2139 passed, 526 skipped, 3654 subtests, 0 failed**. The unchanged base gives 2128 passed and the same 526 skipped (+11 = the new tests). Run on Python 3.13.17 without PostgreSQL, not the pinned Python 3.12.14 / PostgreSQL 14.24, so the PostgreSQL-backed tests are among the skips. The pinned PG run is still owed before release. |

Red on base: the S3 tests cannot run on base (no `scheduled_flatten` module or committed S3 profile).

**Open:**
- H1: install with run 4's holdings needs a reviewed carry-over, or a flat wallet.
- H2 at install: `gate_a` rejects dust.
- The run decision and window (Yao), Isaac's approval, the pinned PG suite, and S3-L1.

## PR277-RV01 — independent merge review (Isaac/Codex, 2026-10-24 SGT)

Original PR head `08dd9a84`; canonical base `a0409d19`. User authorizes source review, repairs and merge;
installation, wallet operations, carry-over accounting and profile/signer approval remain outside this review.

R1 (source finding): the planner blocks new BUYs while the scheduled flatten is pending, but a BUY authorized just
before the time retains its ordinary S2 execution window and finite command lifetime across that boundary. Neither
`RuntimePlanner` nor `execution_bounds.permitted` applies the S3 cutoff to this in-flight authority. The fix must
bound both the runtime command and independent execution/signer admission; settlement/reconciliation must continue
for transactions already submitted. First flat/DONE rounds must still permit S2 rebuilding.

Prospective pass criteria, recorded before review tests or changed runtime code run:
- RV1: a pre-cut BUY's command authority expires no later than the scheduled instant; independent admission accepts
  before and refuses at/after the boundary. Post-DONE BUYs retain their ordinary bounds, mandatory SELLs remain
  admitted, and S2/profile bytes and other execution guards remain unchanged. Cover quote refinement/retry as needed.
- RV2: real PostgreSQL coordinator commits, reloads and replays DONE, with a later re-held book not sold again by the
  schedule; pending reservations prevent early DONE. Exercise risk-state persistence with the actual runtime adapter.
- RV3: safety/discretionary attempt counts are not reset by the scheduled cycle. Scheduled and terminal sells share
  SAFETY counts; exhausted SAFETY capacity can also prevent terminal exits. Record this remaining operational risk
  alongside the existing BUY/leg/gas/install constraints, without granting more attempts or carrying holdings over.
- RV4: validate/rebuild S3 and unchanged S2 candidates, review scope refusals, and run focused and full tests with
  PostgreSQL14.24 and repository-pinned dependencies. Current workflow/Docker pin is Python3.12.15; the original
  claim that3.12.14 is the repository pin is historical wording to correct. Document actual environment/skips.

GitHub Actions run40098610551 did not start jobs: runtime annotation says failed account payments/spending limit.
No code/CI pass is inferred from that run. No runtime release or live trading test is authorized by this source review.

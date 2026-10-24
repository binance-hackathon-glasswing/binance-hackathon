# IDEA-093 — S4: the final strategy, 24/7 with every S2 fix

- Date / author: 2026-10-25 SGT (2026-10-24 ~16:30Z) / team request in a Claude Code session on Keith's machine (request and the
  hours choice below); Claude Code (design, implementation, record). Strategy owner for review: Keith
- Status: **open — design and pass criteria pre-registered before any test or code.** Results are added below.
  Not approved, built into a release or installed.
- Base: canonical `codex/system-testing-20261012` at `4b164649` (PR277 merged).
- Related: IDEA-076 / IDEA-084 PF-01, PF-04 (S1 and the final calendar), IDEA-089 (S2, run 4), IDEA-090 (S2-F2..F6),
  IDEA-091 (strategy research), IDEA-092 (S3), SKILL.md F-95, F-115, F-117, F-119, F-121, F-124.

## Request (in chat, 2026-10-25 SGT)

"Can you develop the final trading strategy, make sure it does not have the same errors that happened in S2 and it can
trade everyday 24/7." Asked what "trade everyday 24/7" means, the requester chose **24/7 capability**: the agent may buy, top up
and exit at any hour on any day while the kit reports `openState` true, with a decision round every 15-minute slot. It
builds the five-name book as soon as it can and holds it; it trades when the book needs it (entry, top-up, red-flag
exit, loss cut, final flatten). No forced daily round trips (rejected options: a daily one-name rotation, about 0.3%
cost over the run; a daily sell-all and rebuy, about 1–1.5% and a risk of idle cash after a failed rebuy).

## What the rules allow (checked, SKILL.md §0.2)

- **F-119:** "Orders can be placed 24/7." There is no organiser trading-hours restriction.
- **F-95:** no order while `openState` is false in `rwa/tokens` or `rwa/underlying-market`. S4 keeps the planner's
  `MARKET_CLOSED_OR_UNKNOWN` check unchanged.
- **F-117 / F-114:** the build registered at final activation runs unchanged for the scored run, so S4 must be complete
  in that build: no hours, slippage or attempt value can be changed during the run.
- **F-124:** automatic restarts are allowed, so the runtime's UTC day roll (S2-12) and every slot's round run without a
  person.
- **Proposal** (`docs/proposal/proposal_answers.md` line 28): "Unless the test supports it, off-hours logic is used only
  as an execution guard." S4 adds no off-hours signal: off-hours trading uses the same entry, cost, impact and
  `openState` guards as in-session trading. No new deviation row is proposed; the GAP-62 final review (Keegan) decides.

## The S2 errors and what S4 does about each

| S2 finding | What happened (run 4, IDEA-089/090) | S4 |
|---|---|---|
| NYSE-only entries | S1 enters only from 30 min after the XNYS open to 15 min before the close; S2's `KIT_OPEN_STATE` was refused outside a dev SHADOW REHEARSAL (S2-1) | `KIT_OPEN_STATE` hours allowed for the FINAL profile with the decided v1 scope, in `live` mode only (S4-1) |
| S2-F2 | rounds only in slots whose rotating issuer had evidence (2 of 5) | fixed in source (IDEA-090, PR274): a planning round every slot; regression-tested here (S4-4) |
| S2-F3 | a quote follow-up re-sorted near-equal legs and dropped the executable quote | fixed in source (IDEA-090); regression (S4-4) |
| S2-F4 | a better-than-mark quote was dropped with one follow-up round | `max_quote_rounds` 2 in the example runtime configs (IDEA-090); regression (S4-4) |
| S2-F5 | signed-path rounds with an assessment did not replay | fixed in source (IDEA-090, PR274-RV01 R2); regression (S4-4) |
| S2-F6 | 3 of 4 buys aborted at the post-approve requote: any adverse move above the 8 bp limit blocked the swap | IDEA-090 requotes at the authorized minimum; S4 also widens `slippage_bps` 8 → 20 (inside the 50 bp validator bound), so the swap goes through after an adverse move of up to 20 bp (S4-5). The worst-case fill is 12 bp lower, about 0.05 USDT on a 38 USDT leg; the entry-cost cap (50 bp all-in) and impact cap are unchanged |
| S2-9 | one session spans a weekend; 3 attempts per leg would not last | 5 attempts per leg per session (the validator's maximum), as S2 (S4-2) |
| First intent expired unclaimed | the runtime planned before the execution service started (run-sheet order P4 → P5) | the final installs before `trade_after` (Oct 29 14:00Z), so both services run before the first buy; noted for the final run sheet, not code |
| Approve without swap | an aborted swap left an exact-amount allowance open | unchanged: the next approve for that token replaces it (exact-amount approvals, G-01); LD06 cleanup stays disabled |

## Design

- **Scope (`larp/strategy/execution_bounds.require_open_state_scope`).** `KIT_OPEN_STATE` is accepted in exactly two
  scopes:
  1. S2's (unchanged): REHEARSAL, evidence and falsifiers SHADOW, mode `dev` (or `None` for `validate_live`);
  2. **S4's (new):** FINAL, `evidence_mode` BOUNDED_FALSIFIER, `falsifier_authority` DISCRETIONARY_EXIT,
     `statement_authority` SHADOW (the decided v1 FINAL scope that `validate_live` already requires), mode `live` (or
     `None`).
  Everything else is refused as today: a FINAL profile in `dev`, `offline` or with no mode at a service start; a FINAL
  profile with SHADOW evidence; a REHEARSAL with BOUNDED_FALSIFIER evidence. The same function is called at all five
  points (`validate_live`, `gate_a.prepare`, `gate_a_check`, the runtime start and the execution start). The scheduled
  flatten (S3) stays REHEARSAL-only.
- **Hours.** Unchanged code: `execution_bounds.interval` gives a `KIT_OPEN_STATE` discretionary leg the session's open to
  the next session's open, for both the planner (`reserve`) and execution admission (`permitted`, which the execution
  service, the loop, the store and the signer all call). The profile window still bounds new risk and the flatten.
- **Profile (`tools/deploy/build_final_candidate.py`, new).** Built from the same pinned inputs as S2 (quote summary
  `quotes-complete-20261020`, red-flag registry, L = 660 s / m = 30 s, initial-only gas budgets, two exit children per
  position) through `build_live_profiles`' FINAL profile, then:
  - `s1` block `docs/build/evidence/s4-final-profile-20261025/s4-block.json`: S2's block (levels 95/60/30%, weights 1/5,
    cap 30%, hard name line 35%, top-up band 5%, deterministic limiter, legs 3, expiry 3, trend start UP) with
    `execution.hours` KIT_OPEN_STATE and 5 attempts per leg;
  - window PF-04 (IDEA-084, adopted): `trade_after` 2026-10-29T14:00:00Z, `new_risk_end` 2026-11-09T21:00:00Z,
    `flatten_start` 2026-11-10T19:00:00Z, `signing_end` 2026-11-11T14:45:00Z (flat-by target Nov 11 15:00Z);
  - `slippage_bps` 20; `policy_id` `larp-s4-final-v1`; each changed key's provenance names this entry.
  - FINAL sizes from `build_live_profiles`: expected equity 200 USDT, per-trade cap 38.2 USDT, cost reserve 0.2 USDT,
    minimum trade 18.637 USDT (one leg per name builds the 38 USDT position).
  - The generator's `WINDOWS["FINAL"]` stays as it is, so earlier evidence profiles still rebuild; the S4 builder sets
    PF-04's windows itself (as the rehearsal builder does for S2).
- **Not changed:** the planner, trend guard (inert without series, IDEA-091; start UP), limiter, loss ladder (3% daily
  and 8% drawdown block buys, 12% cuts), red-flag exits, entry-cost and impact caps, CAP-02, router policy, signer caps,
  gas scope, quarantine, nonce barrier, logging and uploads.

## Known limits (recorded before testing)

- **Weekend attempts.** A `KIT_OPEN_STATE` session runs from one NYSE open to the next, so Friday's session covers the
  weekend (and Monday Nov 2 opens at 14:30Z after the US DST change). Each leg gets 5 quote rounds in it; with a round
  every slot, a quote that keeps failing exhausts them in about 75 minutes and the leg waits for Monday. This protects
  against quote/venue outages; it is not relaxed.
- **Holding is the default.** Once the book is built, S4 trades only when a rule requires it. Daily activity is not
  forced (the requester's choice above). F-115 says not trading at all is not the point of the competition; S4 trades at entry,
  on red flags and loss cuts, and in the final flatten.
- **Live evidence still owed.** No S2-fixed build has run live; a dev run with these fixes (IDEA-090 F7, a post-approve
  swap, a sell) is still the highest-value check before the freeze. S4 is a FINAL profile and cannot run on the dev
  wallet; an S2-style REHEARSAL with this block (hours, attempts, slippage) can.
- **Approvals.** Isaac approves the exact profile hash and `signer.json`; Keegan reviews code, release and GAP-62; Yao
  installs. This entry adopts no installation or signing authority.

## Pre-registered pass criteria (written before any test or code)

| # | Pass when | Evidence |
|---|---|---|
| S4-1 | `require_open_state_scope` accepts `KIT_OPEN_STATE` for a FINAL profile with BOUNDED_FALSIFIER / DISCRETIONARY_EXIT / statement SHADOW in mode `live` and `None`, and refuses it in `dev`, `offline` and a missing service mode; refuses FINAL with SHADOW evidence or falsifiers; S2's REHEARSAL rule is unchanged (every IDEA-089 S2I-4 test passes unchanged) | `tests/strategy/test_s4_final.py`, `tests/strategy/test_s2_weekend.py` |
| S4-2 | With the S4 profile on a synthetic snapshot after the session close (overnight) and on a weekend time, the planner reserves a discretionary BUY and forms an intent, authority open → next open; with `openState` false it is `MARKET_CLOSED_OR_UNKNOWN`; before `trade_after` or after `new_risk_end` no entry; 5 BUY quote rounds per leg per session, then `LEG_ATTEMPT_LIMIT` | `test_s4_final.py` |
| S4-3 | Execution admission (`permitted`) admits the planner-accepted overnight S4 BUY until the next open and refuses it at the next open | `test_s4_final.py` |
| S4-4 | The S2-F2..F6 and S3 regression tests pass unchanged (`tests/runtime/test_driver.py`, `tests/strategy/test_child_keeps_parent_leg.py`, `tests/strategy/test_requote_follow_up.py`, `tests/execution/test_requote_at_authorized_minimum.py`, `tests/strategy/test_s3_scheduled_flatten.py`) | pytest |
| S4-5 | At S4's 20 bp limit, a post-approve swap requote 12 bp below the planning output prepares with a minimum ≥ the authorized minimum, where the same move at 8 bp is blocked; no request is wider than 20 bp | `test_s4_final.py` (venue, synthetic Web3) |
| S4-6 | The committed S4 profile rebuilds byte for byte from its README command; passes `validate_live`; is FINAL, 200 USDT, weights 1/5, `KIT_OPEN_STATE`, 5 attempts, 20 bp, PF-04 windows, BOUNDED_FALSIFIER / DISCRETIONARY_EXIT; and differs from the generator's FINAL S1 profile built from the same inputs only in `s1.execution`, the four window keys, `slippage_bps`, `policy_id` and their provenance | `test_s4_final.py` |
| S4-7 | The builder refuses `KIT_OPEN_STATE` without 5 attempts, weights other than 1/5, a MODEL limiter, and a block without `KIT_OPEN_STATE` | `test_s4_final.py` |
| S4-8 | The runtime start (`service.build_driver`) and the execution start (`build_execution`) in `live` mode get past the open-state scope check with the S4 profile (any refusal is a later gate, not `SCOPE`), and refuse it in `dev` with `SCOPE` | `test_s4_final.py` |
| S4-9 | Local CI replica, because GitHub Actions cannot start (account billing): the `runtime` job's steps on Python 3.12.15 with PostgreSQL 14.24 and `deploy/requirements-test.lock` (`pip check`, full `pytest`, offline demo, Docker image build and run); the infrastructure job's Terraform `fmt`/`validate`/`test` if a pinned Terraform runs locally; the host-bundle build and its test if they run locally. Each failure is reported with its cause; only environment-only failures already recorded (nested bubblewrap in Docker, systemd) may remain | command output and a receipt in `docs/build/evidence/` |

Fail or partial: record it here; do not loosen the `openState`, cost, impact, attempt or signer guards to pass.

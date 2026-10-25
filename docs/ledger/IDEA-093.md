# IDEA-093 — FS1 (first built as S4): the final live solution, 24/7 with every S2 fix and AIand/ChatGPT routing

> PR278-RV01 is an independent review requested by Yao on 2026-10-25 SGT. The original results below describe
> earlier commits. The review's criteria/results at the end govern its changes; no profitability or deployment
> approval follows from offline tests. PR278 must remain open for teammate review.

- Date / author: 2026-10-25 SGT (2026-10-24 ~16:30Z) / team request in a Claude Code session on Keith's machine (request and the
  hours choice below); Claude Code (design, implementation, record). Strategy owner for review: Keith
- Status: **open — implemented and tested offline 2026-10-25 (S4-1..S4-9, S4R-1..S4R-5 and FS1-1..FS1-7 PASS, local
  CI replica; see the results sections).** Not approved, built into a release or installed. S4 was renamed FS1.
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

## Implementation and results (2026-10-25 SGT; branch `claude/final-strategy-20261025`)

Commits: `6f0141d1` (criteria, before any test or code), `4fffd75e` (tests, red on base), `d9db07c9` (code and
profile), `d1260bc4` (evidence README, backlog). Red on base: with the code change removed, 8 of the 14 new tests fail
(every scope, builder and service-start test); the 6 that pass on base are the refusal guards, the planner/admission
tests (the hours already worked for any profile the scope let through) and the venue test (IDEA-090 F11 existed).

**Code.**
- `larp/strategy/execution_bounds.py`: `require_open_state_scope` accepts `KIT_OPEN_STATE` in S2's scope or S4's (live
  FINAL, decided v1 scope); the five call sites are unchanged.
- `tools/deploy/build_final_candidate.py` (new) builds the S4 profile; `build_rehearsal_candidate.py` now shares its
  pinned inputs through `pinned_profiles` / `gas_formulas` (S2 and S3 profiles still rebuild byte for byte).

**Profile** `docs/build/evidence/s4-final-profile-20261025/final-s4.json`: file `bb59b190…`, digest `429b7025…`,
probe `14257e77…` (full hashes in the README).

| # | Result | Evidence |
|---|---|---|
| S4-1 | **PASS.** FINAL with the v1 scope accepted in `live` and `None`, refused in `dev`, `offline` and `''`; SHADOW evidence/falsifiers/BOUNDED statements, REHEARSAL or another environment refused; S2's rule unchanged (all `test_s2_weekend.py` tests pass); the S3 scheduled flatten is still refused for FINAL | `test_s4_1_*` |
| S4-2 | **PASS.** Saturday 23:00Z and Sunday 12:00Z in a Friday-to-Monday session: discretionary BUY intent with authority Friday open → Monday open; NYSE hours refuse the same snapshot; `token_open` or `underlying_open` false → `MARKET_CLOSED_OR_UNKNOWN`; before `trade_after` / after `new_risk_end` no attempt; 5 quote rounds then `LEG_ATTEMPT_LIMIT`. The Sunday round needs the risk day rolled to Sunday (the runtime's UTC day roll, S2-12); without it the planner says `NEW_RISK_HALTED`, as designed | `test_s4_2_*` |
| S4-3 | **PASS.** `permitted` admits the weekend BUY on Saturday, Sunday and Monday 13:29:59Z, refuses it at Monday's open and under NYSE hours | `test_s4_3_*` |
| S4-4 | **PASS.** Every listed regression file passes unchanged in the full run below | full suite |
| S4-5 | **PASS.** A requote 12 bp below the planning output: at 20 bp the minimum reaches the authorized one; at 8 bp it does not (run 4's block); no request wider than the limit | `test_s4_5_*` |
| S4-6 | **PASS, with one correction to the criterion's wording.** Rebuilds byte for byte; values as designed. Against the generator's FINAL S1 profile it differs in `s1.execution`, `trade_after`, `new_risk_end`, `flatten_start`, `slippage_bps`, `policy_id`, **and `exit_gas_reserve_units`** (two exit children, as S2; the criterion omitted it), plus the provenance of those keys and of the two gas-budget formulas. `signing_end` is equal (both 14:45) | `test_s4_6_*` |
| S4-7 | **PASS.** Refusals: 3 attempts, no hours, NYSE hours, MODEL limiter, non-1/5 weights, blank decision, non-bytes block; the CLI writes once | `test_s4_7_*` |
| S4-8 | **PASS.** Runtime and execution starts in `live` get past the scope check; `dev` (and a missing execution mode) refuse with the scope message | `test_s4_8_*` |
| S4-9 | **PASS (local replica, not GitHub CI).** Full suite on Python 3.12.15 / PostgreSQL 14.24 / pinned lock, clean clone of `d1260bc4`: **2675 passed, 9 skipped, 4004 subtests, 0 failed**, `pip check` clean, no deselection (bubblewrap ran in a privileged container); offline demo PASS; Docker image build and run PASS; Terraform 1.13.5 (amd64) `deploy/aws` 19/19 and `deploy/bootstrap` 1/1 with fmt/validate; x86_64 host bundle built and `test_host_bundle.sh` PASS for primary and signer. Not run: `LARP_TEST_SYSTEMD=1` systemd conditions (needs a disposable systemd runner) | [receipt](../build/evidence/idea093-local-ci-20261025.json) |

**Open (owners as in the backlog line "IDEA-093 S4"):** Keith accepts the values (20 bp, 24/7 hours, PF-04 kept);
Keegan reviews code, release and GAP-62; a dev REHEARSAL with this block and 20 bp shows a post-approve swap,
consecutive-slot rounds (IDEA-090 F7) and a sell before the freeze; Isaac approves the exact profile, final
`signer.json` and caps/gas coverage; Yao builds and installs the final release before `trade_after`.

## S4-R: a dev REHEARSAL with the S4 settings (requested 2026-10-25 SGT, pre-registered before tests or code)

**Request (in chat):** "Yes, build a dev REHEARSAL profile with the S4 block and 20 bp slippage so we can run it live
before the freeze." S4 itself is FINAL and cannot run on the dev wallet, so S4-R carries S4's strategy settings into
S2's dev SHADOW scope (S2-1).

**Design.**
- Built by `tools/deploy/build_rehearsal_candidate.py --s4-rehearsal` from the S4 block (`s4-block.json`, the same
  bytes as S2's block), so the strategy block is exactly the final one: `KIT_OPEN_STATE`, 5 attempts, weights 1/5.
- `slippage_bps` 20 (S4's value); `policy_id` `larp-s4-rehearsal-v1`.
- Everything else is S2's: REHEARSAL sizes at 100 USDT, SHADOW evidence and falsifiers, `dev` mode only, gas, caps,
  L/m, exit reserve.
- **Window (proposed; Yao decides the run and may rebuild it with other times):**
  - `trade_after` 2026-10-25T16:00:00Z (Mon 00:00 SGT), one hour after run 4's `signing_end`, so run 4 can retire flat
    first (IDEA-092 H1: a new run needs a stock-flat wallet);
  - `new_risk_end` 2026-10-26T06:00:00Z;
  - `flatten_start` 2026-10-26T07:00:00Z;
  - `signing_end` 2026-10-26T12:00:00Z (Mon 20:00 SGT), before Monday's NYSE open, inside the Oct 26 freeze day.
  - The whole window is outside the NYSE session, so every buy and sell it makes is an off-hours trade: the case S4 adds.
- The builder refuses `--s4-rehearsal` without a `KIT_OPEN_STATE` block and together with `--scheduled-flatten-at`.

**Live checks this run is for** (evaluated by the operator on the run, as IDEA-089 P1–P6): a BUY whose swap completes
after its approve (S2-F6 with 20 bp); rounds in consecutive slots (IDEA-090 F7); the flatten sells every position
before `signing_end`; balance check MATCH; no HALT or quarantine.

| # | Pass when (offline) |
|---|---|
| S4R-1 | The committed S4-R profile rebuilds byte for byte from its README command and passes `validate_live`, signed dev `gate_a.prepare` with the router-policy pair, `gate_a_check` scope and inputs, and the dev runtime build |
| S4R-2 | It differs from S2's profile `eb55d76a…` only in `slippage_bps`, the four window keys, `policy_id` and their provenance; its `s1` block equals S4's FINAL block |
| S4R-3 | `live` mode is refused at preparation and at the runtime start (S2-1 scope); FINAL is refused for it |
| S4R-4 | The builder refuses `--s4-rehearsal` with an NYSE-hours block and with a scheduled flatten; S2 and S3 profiles still rebuild byte for byte |
| S4R-5 | Full local CI replica as S4-9, no new failures |

### S4-R results (2026-10-25 SGT)

Commits: `76260ae8` (criteria), `31945fb0` tests red on base (all 4 S4R tests failed before the builder change), `db048e0d`
(builder option and profile). Profile `docs/build/evidence/s4-rehearsal-profile-20261025/rehearsal-s4-deterministic.json`:
file `9dbe6f4d…`, digest `b09c88e8…`, probe `a56f5307…`.

| # | Result |
|---|---|
| S4R-1 | **PASS.** Rebuilds byte for byte; `validate_live`, signed dev `gate_a.prepare` with the router-policy pair, `gate_a_check` scope and inputs, and the dev runtime build pass |
| S4R-2 | **PASS, with one correction to the criterion's wording.** Differs from S2's `eb55d76a…` in `slippage_bps`, the four window keys and `policy_id` with their provenance, **and in the decision ID on `s1`/`baseline` provenance** (they carry the block's decision text, which names S4-R; the block bytes and data hash equal S2's). The `s1` block equals S4's FINAL block |
| S4R-3 | **PASS.** `live` refused at preparation and at the runtime start; FINAL refused |
| S4R-4 | **PASS.** NYSE-hours block, no block, and a scheduled flatten are refused; S2 and S3 still rebuild byte for byte |
| S4R-5 | **PASS (local replica).** Clean clone of `db048e0d`, Python 3.12.15 / PostgreSQL 14.24 / pinned lock: **2679 passed, 9 skipped, 4004 subtests, 0 failed**; `pip check`, offline demo, Docker image build and run PASS; x86_64 bundle (`8b95a5ef…`) built and `test_host_bundle.sh` PASS for primary and signer. Terraform not rerun: no `deploy/` file changed since S4-9. Systemd conditions not run |

**To run it (Yao, Isaac):** retire run 4 flat after its Sun 15:00Z `signing_end`; new run ID and database; RC8 build from
this branch (or its merge); M3 coverage review against `9dbe6f4d…`; Isaac's approval of that hash and the new
`signer.json`; install with execution running before `trade_after` (2026-10-25T16:00:00Z). If install is later, the
window can be rebuilt with other times (one-line change in `S4R_WINDOW`, new hash, new approval).

## FS1: the final live solution (requested 2026-10-25 SGT; pre-registered before tests or code)

**Requests (in chat):** "make sure the PR creates a final live solution, name it FS1", and for the live preparation gate,
"have it use AIand/ChatGPT in its decisions". The same message asked to take into account why S3 sells nothing today
(pasted note, IDEA-092 H1/H2): (1) a new run's install (`gate_a.initial_state`) refuses a wallet that holds any stock;
(2) S3's sell-all is at a fixed time, not on start; (3) a run only sells what its own books hold, and carrying another
run's holdings over (H1) is not built.

**Naming.** S4 is renamed **FS1** (final) and S4-R **FS1-R** (its dev rehearsal). The criteria IDs above (S4-n, S4R-n)
keep their pre-registered names; the profile bytes change only in `policy_id` and its provenance text.

**What "AIand/ChatGPT in its decisions" means in the code (checked, not changed).**
- Signed live preparation (`gate_a.prepare`, `runtime_mode='live'`) already requires a reviewed AIand routing file;
  deterministic signing is only allowed for dev rehearsals. With it the runtime's assessor is `aiand_routed`.
- Models act on decisions through the red-flag path that FS1's FINAL scope enables (BOUNDED_FALSIFIER evidence,
  DISCRETIONARY_EXIT falsifiers, `red_flag_authority` RF1 4.02 / RF2 1.05, 2.06): the model assesses EDGAR evidence;
  a claim counts only after the deterministic verifier matches it to the source span; a verified Class 1 finding forces
  an exit (mandatory SELL), a verified Class 2 finding blocks buys for five sessions. Models never sign, size or place
  orders (D-11, services.v1.json).
- The S1 exposure limiter stays DETERMINISTIC: the runtime has no producer for `exposure_assessment` (IDEA-057
  routing guide: "This does not implement B4's exposure-evidence producer or the optional MODEL-mode exposure call"),
  so a MODEL limiter would never move. Wiring that is new runtime code and is not part of FS1.

**FS1 routing: `config/intelligence/aiand-routing.fs1.json`.** The v4 repair candidate
(`aiand-routing.repair.example.json`, IDEA-057 PR204: per-stage output caps, `review.v2.md`) **without `openai_trial`**:
the trial window is historical/expired, and `gate_a.prepare` refuses a trial in a signed preparation. ChatGPT
(`gpt-6.1-sol`, medium) leads; Kimi K3 and GLM-5.3 (high) review and take over when OpenAI fails or its budget refuses.
`openai_pacing` keeps the example's values (US$50 total, US$2 prior spend, Oct 18 11:00Z – Nov 13 00:00Z, daily
release), which cover the PF-04 window. **These budget values are not reconciled** with the shared ledger (KMP-BUD01:
about US$2.88 settled plus US$0.34 unknown); the account owners must confirm or change them before install, and any
change makes a new routing hash.

**The S3 install limits, applied.**
- **FS1 (final wallet).** The final wallet is fresh and funded with USDT only (F-14, F-107); its first BNB comes from a
  MetaMask USDT → BNB swap before the first agent trade (F-120). So it holds no stock at install and (1) does not
  block. FS1 has no scheduled sell-all (the S3 key is refused for FINAL); it sells by rule (red-flag exits, loss cuts)
  and in the terminal flatten from Nov 10 19:00Z, so (2) does not apply. Every position is bought by the FS1 run
  itself, so the flatten can sell all of it (3). **Consequence:** the scored run must be **one run** from start to end:
  automatic restarts (F-124) resume the same run and database; a new run cannot be started mid-run, because its install
  would refuse the held stocks and its books would not own them.
- **FS1-R (dev wallet).** It can only be installed once run 4 has sold out. Run 4 is RC7, which predates the S2-F6
  fix, so its Sunday flatten SELLs can abort the same way its buys did; if SKHYB (or any dust, H2) is still in the dev
  wallet after 15:00Z, FS1-R cannot be installed, and nothing in this PR sells run 4's stocks. The run sheet's first
  step is a read-only wallet check for zero stock units. If the check fails, the options are a reviewed H1 carry-over
  (Isaac/Keegan) or skipping FS1-R; neither is built here.

**Final live package (this PR).** FS1 profile, FS1 routing, the gate scope already added for S4, tests, and a run sheet
`docs/build/ops/final-fs1/README.md` that lists the final install steps and inputs for the owners (no host, wallet,
key, secret or paid-model action is taken here).

| # | Pass when |
|---|---|
| FS1-1 | FS1 and FS1-R profiles rebuild byte for byte; each differs from its S4 / S4-R predecessor only in `policy_id` (`larp-fs1-final-v1`, `larp-fs1-rehearsal-v1`) and provenance text |
| FS1-2 | `aiand-routing.fs1.json` passes `validate_routing_spec`, equals the v4 repair example minus `openai_trial`, names `gpt-6.1-sol` as the OpenAI model with Kimi K3 and GLM-5.3 reviewers, and its pacing window covers FS1's `trade_after`..`signing_end` |
| FS1-3 | Signed live `gate_a.prepare` with FS1 + FS1 routing + an adoption reference writes `assessor` `aiand_routed` and the routing file; `gate_a_check` scope and inputs pass; the same preparation without routing, or with the v4 example that still carries the trial, is refused |
| FS1-4 | The runtime start in `live` mode builds with FS1 and the FS1 routing pair, with no network |
| FS1-5 | With FS1's settings, a verified model-assessed Item 4.02 finding gives an EXIT target and a mandatory SELL intent from the planner (the model's verified output changes the decision); at a weekend time too |
| FS1-6 | Live preparation of FS1 refuses a capture whose wallet holds any stock (S3 lesson 1), and FS1 refuses a scheduled flatten |
| FS1-7 | Full local CI replica as S4-9, no new failures |

### FS1 results (2026-10-25 SGT)

Commit `c7242513` (rename, routing file, FS1 tests, run sheet). The FS1 tests were written in the same commit as the
routing file; a separate red check removed `aiand-routing.fs1.json` and FS1-2, FS1-3 and FS1-4 failed; FS1-5 and FS1-6
pass without it (they are guards on behaviour that already existed for this profile).

| # | Result |
|---|---|
| FS1-1 | **PASS.** Against the S4 / S4-R builds at `db048e0d`, both profiles differ only in `policy_id` and provenance (`decision_id` text on the keys this entry set; formula text on the FS1-R window and policy). FS1 `75767d3e…` (digest `9249bf11…`, probe `fcd18d03…`); FS1-R `62b38000…` (digest `c0ba0637…`, probe `15cce45b…`); both rebuild byte for byte |
| FS1-2 | **PASS.** Routing `9b86c732…` validates, equals the v4 repair example minus `openai_trial`, `gpt-6.1-sol` primary, Kimi K3 / GLM-5.3 reviewers; pacing Oct 18 11:00Z – Nov 13 00:00Z covers FS1's window |
| FS1-3 | **PASS.** Signed live preparation writes `mode` `live`, `assessor` `aiand_routed`, `execution` `service`, the routing file and pin; `gate_a_check` scope and inputs pass; without routing, or with the v4 example (trial), preparation is refused. Missing inputs reported by preparation: `SEC_CONTACT` (installer supplies) and `LIVE_INTELLIGENCE_SETTINGS_AND_SIGNED_GATE_B_ACCEPTANCE` (always for signed) |
| FS1-4 | **PASS.** The live runtime builds with the routed assessor and service execution, no network; signing itself starts only at run activation. The synthetic budget ledger is opened with the routing's pacing (total, prior spend, no reserve) |
| FS1-5 | **PASS.** With FS1's settings on a Saturday after Friday's close, a verified Item 4.02 assessment (the repository's synthetic rule model in place of AIand, through the same gate and verifier) gives an EXIT target, a `CLASS_1_EXIT` reduction and a mandatory SELL intent |
| FS1-6 | **PASS.** A stock-free capture initializes; one unit of any of the five stocks is refused at install; FS1 has no scheduled flatten |
| FS1-7 | **PASS (local replica).** Clean clone of `c7242513`: **2684 passed, 9 skipped, 4004 subtests, 0 failed**; `pip check`, offline demo, Docker build and run PASS; x86_64 bundle `7304b7ba…` and `test_host_bundle.sh` PASS for primary and signer. Terraform not rerun: no `deploy/` or workflow file changed in this entry. Systemd conditions not run |

## PR278-RV01 — prospective review criteria (2026-10-25 SGT)

User request: thorough final-strategy review with formal methods and primary online literature on price prediction
and crowd behavior; implement necessary fixes, keep PR278 open. Reviewed original head `da5af854`, based on current
canonical `4b164649`. No host, wallet, credentials, paid model calls or market-data collection is part of this review.
Implementation/tests are committed and pushed before execution (SKILL F-61). Synthetic checks establish code
properties, never an economic edge. Literature and the existing EXP008 report cannot establish FS1's future profit.

### Findings and acceptance criteria, before implementation or tests

| ID | Finding / proposed repair | Pass criterion |
|---|---|---|
| RV01-1 | PF02 recovery is absent: the 8% stop is permanently OR-latched. Add an explicit profile opt-in `run_halt_recovery_bps=500` to FS1/FS1-R, leaving historical profiles unchanged. | Stop at drawdown >=8%; clear only strictly below5% with complete fresh valuation, all health gates including reconciled balances true and no reservations/abnormal accounting. Persist the original peak, daily halt and deep cut; boundaries, restart serialization, repeated paths and unhealthy inputs checked. |
| RV01-2 | Entry cost checks use quoted output, overlooking the weaker authorized minimum (20bp in FS1). | Evaluate BUY cost/reserve/50bp cap against `min_receive_units` at the current mark, plus explicit fee and expected gas. Acceptable quoted price but unacceptable authorized fill is refused. Exact-rational boundary and monotonicity checks; full gas reservations stay unchanged; mandatory exits keep their bypass. This bounds modeled cost, not realized gas or future prices. |
| RV01-3 | At200USDT a95%->60% equal-weight cut is about14USDT/name, below the18.637USDT entry minimum, and policy silently drops its rebalance. Introduce opt-in `s1_reduction_cost_cap_bps=50` for FS1/FS1-R. | A pending S1 level decrease may quote/sell below the entry minimum only if its actual authorized-minimum SELL proceeds, fee and expected gas satisfy both50bp and the cash cost reserve. Rejected/blocked reductions remain pending through restart; no drift sale or mandatory classification is introduced; entry minimum, attempt/cadence/openState/signing gates unchanged. |
| RV01-4 | `--fs1-rehearsal` accepts non-FS1 weights, a MODEL limiter or different attempt limits, so the claimed final-settings rehearsal can test another strategy. | Apply the same block validator as FINAL and require the two-child reserve. Refuse changed weights/mode/attempts; rebuild both candidates byte-for-byte with new profile pins; S2/S3 historical candidates remain byte-identical. |
| RV01-5 | Missing live trend series, limited limiter inputs, no licensed crowd/return prediction input or held-out alpha evidence. | Record exact effective behavior, distinguish empirical vs synthetic evidence, and deliver an after-cost decision criterion and chronological validation design. No fabricated alpha, silent signal activation, tuning on dev PnL or replacement of frozen EXP007. Explicit owner decisions remain in the backlog. |
| RV01-6 | Research and integration acceptance | Check primary sources for momentum/underreaction, attention/herding/disagreement, estimation risk and overfitting; record access level and applicability. Run focused counterexamples, finite state/exact arithmetic checks and full pinned Python3.12/PostgreSQL14 suite; report skips/environment limits. Verify candidate hashes, preparation, replay and existing execution regressions. Keep PR open/unmerged. |

Formal scope: algebraic invariants plus bounded exhaustive state/path checks in ordinary Python using integers and
fractions, not a machine-checked proof of all runtime behavior or market profitability. Prospective economic test:
same point-in-time feasible five-name book and all-in execution model, chronological fit/calibration/held-out blocks,
purge overlapping forward labels, all ablations/trials recorded, block confidence intervals on both absolute net
return and improvement, and prospective shadow evidence before any new predictive/crowd overlay is eligible. No
market experiment is run here because the necessary cleared point-in-time inputs and untouched evaluation block
have not been supplied; classify economic acceptance as NOT_ESTABLISHED.

### Initial counterexamples (pushed test commit `342b9f53`)

Network-disabled, read-only checkout in the existing Python3.12.15 test image: **12 failed,20 passed**. Failures
confirm RV01-1/2/3 and the absent new profile options/validation. RV01-4's hypothesized defect is **withdrawn**:
all four refusal tests pass on the original implementation because `s1_block` and the existing reserve check
already enforce these conditions. Retain those regression tests; no validator rewrite is needed. This correction
supersedes the provisional finding above. Candidate generation will add only RV01-1/3's explicit profile opt-ins.

First repair `111200b0`: all32 focused cases pass. The broader strategy/risk suite exposed25 failures because
historical synthetic profiles/cadence tests reserve only quoted cost. Scope the new entry-cost semantics to an
explicit hashed `entry_cost_basis=AUTHORIZED_MINIMUM` on FS1/FS1-R, alongside the other two opt-ins. Historical
profiles retain their old cost semantics and bytes; this is a compatibility correction, not an increase in FS1's
50bp cost or cash reserve. Existing profile tests are updated to expect these three deliberate new fields.

## PR278-RV02 — second review (2026-10-25, separate from Yao's PR278-RV01)

Review of PR278 requested in a Claude Code session; it ran alongside PR278-RV01 and reached the branch after RV01's
commits up to `c4d10c91`. It does not review or accept RV01's changes and leaves RV01's "keep PR278 open" note in place.

**Checked at `da5af854` (before RV01):** both profiles then pinned rebuilt byte for byte; `aiand-routing.fs1.json`
`9b86c732…` equals the v4 repair example minus `openai_trial`, and its three prompt hashes match
`config/intelligence/prompts/routing/`; the scope check refuses `KIT_OPEN_STATE` for a FINAL in any mode but `live` and
for a REHEARSAL in any mode but `dev`. Full suite on Python 3.12 (pinned lock) with PostgreSQL 16 (not the pinned 14.24):
2682 passed, 11 skipped, 4004 subtests, 0 failed. The two extra skips against FS1-7 come from the environment only (no
bubblewrap; root ignores directory modes).

**Fixed (no profile or routing bytes change):** `build_final_candidate.s4_block` renamed `fs1_block`; the scope-check
comments in `gate_a`, `gate_a_check` and `execution_live.main` name FS1 as well as S2-1. With RV01's commits, both
candidates still rebuild byte for byte (`fs1-final.json` `f5ac59de…`, `fs1-rehearsal.json` `ce0dcde4…`), and the full suite on
the combined head passes: 2715 passed, 11 skipped (same environment skips), 4004 subtests, 0 failed.

**Finding recorded, not built (PR278-RV02-F1):** the run sheet reuses the RC7 scripts, but M1, D1, M3, M4 and P4 are
pinned to run 4 (S2 profile `eb55d76a…`, `--runtime-mode dev`, assessor `deterministic`, `larp_rehearsal4`). The
final install needs reviewed FS1 copies. Added as run-sheet row F0p and to the IDEA-093 line in `INCOMPLETE_WORK.md`
(owner Yao, review Keegan).

## PL: per-stock parallel assessments and trade continuation (requested 2026-10-25 SGT; pre-registered before tests or code)

**Request (in chat):** "can you implement this change for each stock to be evaluated separately so they can be
parallelised?, continue in this PR". Asked which part, the requester chose **assessments + faster trades**: assess
every company with new evidence in parallel, start the next decision round as soon as a trade settles, and keep
trades one at a time on the wallet.

**What the code does today (checked at `6bb2f648`).**
- Every round evaluates all five stocks in one pass (`policy.decide` loops over the universe) and the planner ranks the
  needed legs together. That part is already per stock.
- **Trades are serial on purpose.** One intent per round (`planner.py`), and the execution store's unique index
  `execution_wallet_barrier` allows one non-terminal execution per wallet: nonces are wallet-wide (G-18). Unchanged.
- **FS1's live path is the signed, AIand-routed one** (`service.build_driver`: `signed_model` → `DeferredAssessments`
  → `RoundDriver._signed_cycle`). It already plans a safety round every runtime tick (`interval_seconds` 5), so a new
  leg is planned seconds after the previous one settles. The earlier "about 75 minutes to build the book" in this
  session's chat applies only to the cadence path (deterministic assessor: FS1-R and other unrouted runs), which plans
  once per 15-minute slot.
- **Assessments are serial.** `DeferredAssessments` runs one background job (`submit` refuses while `busy`), and the
  routed assessor itself refuses a second concurrent call on one instance (`ROUTING_GROUP_BUSY`). Filings and reviews
  for different companies queue behind each other.

**Design.**
- **PA (parallel assessments, signed path).** New driver setting `assessment_workers` (integer 1..5; absent = 1 =
  today's behaviour and bytes).
  - `service.build_driver` builds that many independent routed-assessor instances. They share only the OpenAI budget
    ledger (one SQLite `BEGIN IMMEDIATE` transaction per admission, so concurrent workers cannot over-reserve), the
    content-addressed artifact store (atomic `link`) and the evidence store (lock-guarded methods). Each keeps its own
    worker ownership, so a hung provider call holds only its own slot.
  - `DeferredAssessments` takes the list of assessors: one thread per job, at most one pending job per company,
    `busy` when every slot is taken. Results are committed on the main thread one per tick, in submission order, with
    their original audit (replay unchanged).
  - `_signed_cycle` fills every free slot in a tick: it asks `EvidenceWork.next` repeatedly, skipping companies that
    already have a pending job, and submits each item that has records. A cadence slot with no records still only
    plans (no assessment), as today.
  - Cost: up to five concurrent assessments only when several companies have new work; OpenAI pacing still caps
    OpenAI spend (excess goes to the AIand reviewers); provider rate limits under concurrency are not measured.
- **CR (continuation rounds, cadence path).** New driver setting `continuation_rounds` (integer 0..10; absent = 0 =
  today). In a slot whose latest round chain planned at least one intent, once nothing is in flight (no reservation,
  open round or pending execution), the driver starts a planning-only round `cadence:{slot}:next{k}` on the next tick,
  up to `k = continuation_rounds`. A continuation that plans no intent ends the chain until the next slot. Trades stay
  one at a time; every round is still logged.
- **Configuration.** `runtime.example.json` and the AIand shadow example carry `assessment_workers` 5 and
  `continuation_rounds` 4, so `gate_a.prepare` writes them into every new `runtime.json` (FS1 and FS1-R).
- **Not changed:** planner, one-intent-per-round, wallet barrier, signer, caps, quote follow-ups, openState guard.

| # | Pass when |
|---|---|
| PL-1 | With `assessment_workers` 1 (or absent) and `continuation_rounds` 0 (or absent), every existing driver, deferred-assessment and replay test passes unchanged |
| PL-2 | With 5 workers and new filings for three companies, one signed-cycle tick submits three jobs, one per company, each on a distinct assessor instance; a second filing for a company with a pending job is not submitted until that job is acknowledged |
| PL-3 | Finished results are committed one per tick in submission order with their audit; the journal replays to the same head |
| PL-4 | A hung job holds only its own slot: other companies are still assessed, and safety rounds still plan every tick |
| PL-5 | A restart with several pending model journals recovers each (COMPLETE or INTERRUPTED) and acknowledges each once; no round is duplicated |
| PL-6 | `service.build_driver` builds N distinct routed assessors for `assessment_workers` N; 0, 6, a boolean or a string is refused; concurrent budget admissions from N threads never reserve more than the released allowance |
| PL-7 | Cadence path with `continuation_rounds` 4: a five-name book that needs five buys plans them in consecutive ticks inside one slot as each settles; no continuation starts while an intent is in flight; a continuation that plans nothing ends the chain; a mandatory sell uses the same path |
| PL-8 | Continuation rounds replay to the same head, and a restart inside a slot does not create a duplicate continuation |
| PL-9 | The examples carry both settings (mirrored); `gate_a.prepare` writes them; FS1's live runtime builds with five routed assessors |
| PL-10 | Full local CI replica as before, no new failures |

## PR278-RV01-GAS — F-125 follow-up (2026-10-25; criteria before execution)

PR279 is merged; F-125 instructs a 30 USDT final-wallet gas swap unless organisers explicitly permit less.
Reviewed F-120/F-125, verbatim source page and kit gas conventions, IDEA-055 D6/B7, and the actual startup,
policy and planner code. The current 95% target treats non-saleable BNB as stock-buying capital: at 170 USDT cash
and 30 USDT BNB, four roughly 38 USDT names can consume the funds and starve the fifth. This is an allocation
defect, independent of whether BNB counts in the eventual score. Also, BNB is marked at a fixed profile price:
market moves do **not** directly trigger our stops; the problem is unobserved valuation error. B7 only tests
floor plus one top-up, not the actual seeded balance. Its old <=5% materiality argument no longer covers F-125.

Review candidate: explicit `s1_capital_basis=EXCLUDE_GAS` on FS1 and FS1-R. Apply the nominal 95/60/30% levels
to cash plus marked eligible stocks minus the existing cost reserve; keep the frozen equal fifths. Convert this
budget to weights in total-equity units for the existing proposal contract. The independent planner must clamp
to the same fundable cap. Keep nominal trend/limiter state separate so changes in valuation do not trigger drift
sales. Loss triggers, peak, opening equity and the fixed BNB accounting price remain unchanged pending D6 owner
resolution and score valuation. At 170 cash, the high target is about 161.5 USDT total /32.3 per name before costs.
This leaves the existing 5% uninvested share of deployable assets, rather than treating gas as spendable USDT.

Pass criteria GAS-1: 30-USDT synthetic gas wallet builds all five names through sequential settled buys with
nonnegative cash and unchanged gas reserve checks; equal target notionals and independent planner clamp.
GAS-2: target stock notional is invariant to BNB price for fixed cash/stocks; nominal-level changes still reduce
positions, while gas mark changes alone cause no discretionary sell. GAS-3: old profiles keep their exact behavior;
new option is S1-only and exact-valued, generated profiles/provenance/hashes rebuild. GAS-4: real PostgreSQL
commit/restart/exact replay preserves recovery and all-five construction using synthetic ports. GAS-5: affected
tests and full merged suite pass (concurrent PL work is independently owned and must be complete for a green head).
Economic/live acceptance stays open: no funding, signing, upload or host activation is authorized by these tests.

### PR278-RV01 results — source review complete; keep PR278 open (2026-10-25 SGT)

Four explicit profile refinements are implemented: PF02 run-stop recovery; authorized-minimum BUY cost;
cost-gated pending small level SELLs; and F-125 gas-excluded stock capital. The original suspected FS1-R builder
defect was disproved and withdrawn. Relevant commits: tests `342b9f53`, repairs `111200b0`/`a82a70d2`, first
profile pins `c4d10c91`, F-125 capital sizing/tests `92df8662`, current candidate pins/run sheet `37f674c3`.
Current FINAL file `0401e966…` / digest `ac5de572…` / probe `518b1e76…`; REHEARSAL `54802665…` /
digest `22a9ad90…` / probe `7d5a5602…`. Full pins: candidate READMEs and the receipt below.

Validation on pushed combined head **`d7741f916681c1f1d48b7e11c1d26d41d795baa6`**, including current canonical
`5b5f0c89` (PR279/280) and the separate PL implementation:

- Full clean-clone suite: **2766 passed, 9 skipped, 4027 subtests, 0 failures**, no deselection, 255.92 s;
  pinned Python 3.12.15, PostgreSQL 14.24, offline/synthetic ports on an internal Docker network.
- Five actual-systemd checks run separately: **5 passed /5 subtests** (release refusal and automatic restart).
  Two further environment skips resolved separately: non-root directory permission and GitHub-origin refusal
  **2 passed**. Across these runs, **2773 unique tests pass**; only the two external/private-fixture tests remain
  unrun. No GitHub Actions or exact new host-release qualification is claimed.
- GAS-1..4 focused run: **63 tests /9 subtests pass**. Real PostgreSQL commits five settled synthetic buys,
  restarts the coordinator between every leg, retains healthy recovery, and replays the exact journal without
  external ports. Other bounded checks enumerate 1296 recovery paths and a 273-case cost grid.
- Both candidate profiles rebuild byte for byte. Offline demo PASS, 67652-byte valid simulated trace.
- Earlier environment failures and the superseded incomplete run are retained truthfully in the receipt.

Evidence: [receipt](../build/evidence/pr278-review-20261025.json) and
[research/formal review](../research/fs1-review-20261025.md), including eight primary literature sources with
access grades, RV-H1 crowd/news hypothesis and RV-E1 prospective evaluation design. No new market experiment
was run and no predictive alpha, return forecast or maximum-profit claim is supported. The exact FS1 policy
was not what EXP008 tested; EXP007 remains frozen/unrun. Literature supports testable conditional mechanisms,
not a universal instruction to chase attention or follow a crowd.

**Remaining, explicitly owned:** Keith/Keegan reconcile missing live trend series versus a declared static
baseline, accept the four new fields and finish actual-size round-trip cost ranking; Keith/Isaac/Keegan resolve
material fixed-price BNB risk valuation under the 30 USDT seed (GAP-73) and accept fresh profile/gas/cap evidence;
Keith/Keegan/Yao implement the registered final-wallet self-check/handover (GAP-74) and FS1 install scripts/new
release qualification; Yao confirms funding (GAP-75); team/Yao complete model adoption, independent quality
evidence, budget and secret bindings. The run sheet now states these gaps rather than treating a dev 8 bp quote
as FINAL qualification or the final wallet as still holding 200 USDT cash after gas funding. No full backlog
item is closed, no release installed, and no wallet/model/upload action performed by this review.

### Base sync (2026-10-25 SGT, "pull from latest")

Merged canonical `codex/system-testing-20261012` at `5b5f0c89` (PR279 F-125 Final Activation facts, PR280 14-day archive
and anchor fixes) into this branch as `6bb2f648`; one LEDGER row conflict (IDEA-093 vs IDEA-094/095 appended at the same
place) resolved by keeping all three rows. Local replica on a clean clone of `6bb2f648`: **2746 passed, 9 skipped, 4016
subtests, 0 failed**, `pip check`, offline demo, Docker build/run and x86_64 host bundle (`0eefb9d9…`, primary and
signer) PASS. F-125 (30 USDT final-wallet gas) and its GAP-73/74 consequences for FS1 sizing and the pre-Oct 29
self-check were then addressed on this branch by the PR278 reviewer (commits `a4706dc1`..`37f674c3`).

### PL results (2026-10-25 SGT)

Commits: `0ea5a0ca` (criteria), `6938d2bc` (tests, 20 red on base), `cf528047` (implementation), `d7741f91` (PL-9
FS1 runtime test); merged with the reviewer's F-125 commits as `b0d9cd6c` and `e7a0b3cf`. The test file's own
fixture defects found while running it (thread names instead of identities; a shared audit hook; jobs released after
their temporary directory closed) were fixed in the test only.

| # | Result |
|---|---|
| PL-1 | **PASS.** One assessor keeps the single slot (`test_pl1_*`); every existing driver, signed-model, cadence and replay test passes unchanged in the full run below. With one assessor the signed cycle still makes one work lookup per tick |
| PL-2 | **PASS.** Five slots: three companies submitted in one call each and in flight together on three distinct assessor instances and threads; a second job for a company with a pending job is refused until acknowledged. In the driver, one signed-cycle tick submits `filing:A/B/C` with the `busy` set growing A → A,B |
| PL-3 | **PASS.** Finished results come back in submission order; the driver commits one per tick (A, B, C on three ticks). Replay of committed rounds is unchanged code (one commit per tick on the main thread with its audit); PL-8 replays the continuation journal |
| PL-4 | **PASS.** A hung job keeps only its slot; another company's job finishes, is acknowledged, and a third company is assessed in the freed slot while the first still hangs; acknowledging a running job is refused |
| PL-5 | **PASS.** After a restart, a finished and an interrupted journal are both returned once (COMPLETE, INTERRUPTED) and acknowledged once; a further restart has none pending |
| PL-6 | **PASS.** `assessment_workers` 1 and 5 build that many distinct routed assessors with their own budget objects on one ledger file; 0, 6, a boolean and a string are refused. Ten threads admitting 0.3 against a 1.0 allowance admit exactly three |
| PL-7 | **PASS, with one correction to the criterion's wording.** The cadence-path test demonstrates the chain with a held name whose mandatory SELL stays due (shadow execution never fills): `cadence:{slot}#1` then `:next1..4` on consecutive ticks, then nothing until the next slot; 0 continuations keeps today's single round; a round that plans nothing ends the chain; no continuation while the trade is unsettled, then `:next1` once it settles. A five-name BUY book was not used: the synthetic driver profile is equal weight (one discretionary swap per session) and shadow execution never fills |
| PL-8 | **PASS.** A restarted driver continues with `:next2` (no duplicate), and the journal with continuation rounds replays to the same head with every live port disabled |
| PL-9 | **PASS.** Both examples carry `assessment_workers` 5 and `continuation_rounds` 4; FS1's signed live preparation writes them; FS1's live runtime built from them has five routed assessors and four continuations |
| PL-10 | **PASS (local replica).** Clean clone of `d7741f91`: **2766 passed, 9 skipped, 4027 subtests, 0 failed**; `pip check`, offline demo, Docker build and run PASS; x86_64 bundle `b9b2cb66…`, `test_host_bundle.sh` PASS for primary and signer. Terraform not rerun (no `deploy/` change). Systemd conditions not run |

**Not measured:** AIand/OpenAI rate limits and latency under five concurrent assessments; budget-ledger lock waits
under load (each admission is one short transaction with a 1 s SQLite timeout; a timeout surfaces as budget
unavailable and that stage falls back to the AIand reviewers). Signed-path trading was already per tick before this
change; continuation rounds affect only the cadence path (FS1-R and other unrouted runs).

## SC: the F-125 activation self-check on the final wallet (GAP-74; requested 2026-10-25 SGT; pre-registered before tests or code)

**Request (in chat):** "Yes, design and build the GAP-74 pre-Oct-29 final-wallet self-check and handover for FS1 in
this PR, with pre-registered criteria."

**What F-125 asks (checked, SKILL.md §1.10 F-125):** before Oct 29, on the final wallet, by the registered version:
"Run your system through the full chain once": the agent gathers data, reasons and decides; a trade executes on the
final wallet (after the 30 USDT → BNB MetaMask swap); a decision record with a reason summary is generated; trace
uploads work. Registration (commit, manifest, version event) comes before any trading.

**Decision: one run spans the self-check and the scored run (GAP-74's second option).**
- A separate self-check run would have to end with zero stock, dust included, before a second install
  (`gate_a.initial_state`, IDEA-092 H1/H2), and would need a second install inside Oct 27–29. A run never sells
  another run's holdings, so a stuck sell would block the scored-run install.
- With one run, the build and profile registered at final activation make the self-check trade and then trade the
  scored run unchanged (F-117, F-114). No second version event or install is needed; automatic restarts (F-124) resume
  the same run.

**Design.**
- New FINAL-only profile key `activation_self_check` = {`symbol`, `buy_after`, `buy_until`, `flat_by`, `pay_units`},
  checked by `validate_live` (S1 baseline; `buy_after < buy_until < flat_by <= trade_after`; symbol eligible;
  `minimum_trade_units <= pay_units <= per_trade_cap_units - cost_reserve_units`). Profiles without the key are
  unchanged byte for byte.
- One helper, `larp/strategy/self_check.py`, gives the phase from the profile, the persisted risk state, the ledger
  and the time, for both the policy and the independent planner:
  - **WAIT** before `buy_after`, or while a self-check reservation is in flight;
  - **BUY** in `[buy_after, buy_until)` with the symbol unheld and the check not yet bought: the policy proposes one
    BUY of about `pay_units` of `symbol`; the planner admits that one BUY although `trade_after` has not come
    (every other new-risk halt still applies: loss latches, health, gas, terminal, caps, cost and impact gates);
  - **SELL** once the symbol is held: a mandatory SELL of the whole position, reason `ACTIVATION_SELF_CHECK`; no BUY
    of any name while it is pending; the planner records `activation_self_check: BOUGHT` in the risk state;
  - **DONE** when it was bought and the position and reservations are zero: recorded once, never undone;
  - **EXPIRED** at `flat_by` if not DONE: recorded; nothing is forced; any residual position simply becomes part of
    FS1's book from `trade_after` (the same run owns it).
- **Re-entry.** S1 does not re-buy a name it has held without a fresh review. On DONE, the policy clears the self-check
  symbol's `ever_held` once (marker `self_check_cleared`), so FS1 can buy it in the scored run. Every other name, and
  any later holding of the same name, keeps today's rule.
- **FS1 values (proposed; Keith/Keegan accept):** symbol **SKHYB**, the cheapest measured round trip in the pinned
  quote summary (spread 2 bp + 2 × impact 1 bp); `pay_units` = `ceil(minimum_trade_units × 1.02)` = 19.010169 USDT;
  `buy_after` 2026-10-27T00:00:00Z (install can be later: the buy then comes at the first round after install);
  `buy_until` 2026-10-28T18:00:00Z; `flat_by` 2026-10-28T23:00:00Z, before Oct 29 in UTC (F-121) and before FS1's
  first ordinary buy (Oct 29 14:00Z).
- **Not changed:** FS1-R (its window cannot hold a pre-`trade_after` check), the signer, caps, wallet barrier, logging.
  Every self-check round is an ordinary round log with the swap's `tx_hash`, so the decision-record and trace-upload
  parts of F-125 are checked on the same rounds; the run sheet adds that check.

| # | Pass when |
|---|---|
| SC-1 | Without the key, every existing profile, policy and planner test passes unchanged, and the committed FS1-R profile is byte-identical |
| SC-2 | `validate_live` refuses the key on a REHEARSAL or non-S1 profile, with a window outside `buy_after < buy_until < flat_by <= trade_after`, an ineligible symbol, or `pay_units` below the minimum or above the cap minus the reserve |
| SC-3 | In BUY phase, before `trade_after`, the plan has exactly one BUY intent: `symbol`, worth at least `minimum_trade_units`, at most `pay_units` plus rounding; no other name is bought; outside `[buy_after, buy_until)` nothing is bought before `trade_after` |
| SC-4 | The other new-risk gates still apply in BUY phase: a run halt, daily halt, unhealthy health input, closed market or a cost-capped quote stops the self-check BUY |
| SC-5 | Once held, the plan is a mandatory SELL of the whole position with reason `ACTIVATION_SELF_CHECK`; no BUY of any name while it is pending; the risk state records BOUGHT |
| SC-6 | When flat with no reservations after BOUGHT, the risk state records DONE, and from `trade_after` FS1 builds all five names including the self-check symbol (the one-time re-entry clearance); a later sale of that name keeps the normal re-entry rule |
| SC-7 | At `flat_by` without DONE the state is EXPIRED and nothing is forced; a residual position is kept into FS1's book |
| SC-8 | Real PostgreSQL: a run commits the self-check BUY and SELL with settled synthetic fills, restarts between them, reaches DONE, and the journal replays to the same head with every live port disabled |
| SC-9 | The rebuilt FS1 profile carries the key with the values above, rebuilds byte for byte, passes `validate_live`, signed live preparation and `gate_a_check`; it differs from the previous FS1 candidate only in the key and its provenance |
| SC-10 | Full local CI replica as before, no new failures |

### SC results (2026-10-25 SGT)

Commits: `36c9f753` (criteria), `11337ba3` (tests, red on base: 7 of 8 strategy cases and SC-8), `0a65e19e`
(implementation, FS1 profile, run sheet).

**Deviation from the pre-registered value (recorded before the results below):** `pay_units` is **32 USDT**, not
`ceil(minimum_trade_units × 1.02)` = 19.01 USDT. With RV01's `entry_cost_basis=AUTHORIZED_MINIMUM`, a BUY's cost is
the full 20 bp slippage allowance plus spread, impact and expected gas: at 19.01 USDT that is about 54 bp (gas alone
about 30 bp) against the 50 bp entry-cost cap, so the self-check BUY would be refused live. 32 USDT (an ordinary
FS1 entry, `floor(0.19 × (200 − 30 − 0.2))` rounded down to whole USDT) is about 42 bp, the same gate the scored-run
entries pass. Found when the first SC-3 run on a 5.1 USDT fixture leg was refused `ENTRY_COST_CAP`; the fixture leg
is now 20 USDT. Three test-only defects were also fixed: a malformed timestamp in an SC-2 case, a cost assertion
that named only one of the two cost gates, and the S4-6 list of deliberate FS1 keys.

| # | Result |
|---|---|
| SC-1 | **PASS.** All existing tests pass in the full run; FS1-R still rebuilds byte for byte (unchanged `54802665…`) |
| SC-2 | **PASS.** Refused: a REHEARSAL profile (`SCOPE`), an ineligible symbol, `buy_after >= buy_until`, `flat_by` after `trade_after`, reversed times, `pay_units` below the minimum or at the cap, an extra field, a string amount, a null |
| SC-3 | **PASS.** In BUY phase before `trade_after`, one SKHYB BUY (20 USDT fixture leg); without the key nothing; before `buy_after`, at `buy_until` and between `buy_until` and `flat_by`, nothing |
| SC-4 | **PASS.** Run halt, daily halt, `new_spending_ok` false, closed market and a cost-refused quote each stop the self-check BUY |
| SC-5 | **PASS.** Once held: mandatory SELL of all 2000 units, reason `ACTIVATION_SELF_CHECK`, no BUY, risk state BOUGHT |
| SC-6 | **PASS.** BOUGHT and flat → DONE (no further buy before `trade_after`); in the scored window the self-check name gets a TARGET_WEIGHT despite `ever_held`, with `self_check_cleared`; a later holding keeps the normal re-entry block; without the key the block stands |
| SC-7 | **PASS.** At `flat_by`: EXPIRED with or without a residual position, nothing forced; EXPIRED stays |
| SC-8 | **PASS.** Real PostgreSQL: BUY leg, new coordinator, mandatory SELL leg (BOUGHT), new coordinator, DONE with no intents; flat, no reservations; exact journal replay with every live port disabled |
| SC-9 | **PASS.** FS1 `19176e6c…` (digest `969532f5…`, probe `5b642bd3…`) carries SKHYB, 32 USDT, Oct 27 00:00Z / Oct 28 18:00Z / Oct 28 23:00Z; rebuilds byte for byte; differs from `0401e966…` only in `activation_self_check` and its provenance; `validate_live`, signed live preparation and `gate_a_check` pass |
| SC-10 | **PASS (local replica).** Clean clone of `0a65e19e`: **2775 passed, 9 skipped, 4027 subtests, 0 failed**; `pip check`, demo, Docker build/run PASS; x86_64 bundle `e2b394b5…`, `test_host_bundle.sh` PASS for primary and signer. Systemd conditions not run here (passed in the reviewer's separate run at `d7741f91`; no unit file changed since) |

**Live, not testable offline:** the actual final-wallet trade, its `tx_hash` in delivered round logs, and the
uploader ack (run sheet J-SC). The install must finish before 2026-10-28T18:00Z for the buy to happen.

## PR278-RV03 — merge into canonical (2026-10-25)

Merged at the user's request ("Can you fix and merge 278"), in a Claude Code session. Earlier notes in this entry
and in the PR body asked to keep PR278 open for teammate review; this request supersedes them. Isaac's PR283
(IDEA-098) and canonical PR282 (IDEA-096 allowance recovery) were already in the branch.

**Checked on the merged head** (PR278 `2003c04e` + canonical `7fc9f601`, merge `c5c6213c`, no conflicts):
- all four FS1 profiles rebuild byte for byte: FINAL recovery `b8ba06e2…` (the one the run sheet installs), FINAL
  cleanup-off `19176e6c…`, FS1-R recovery `17ab891d…`, FS1-R `54802665…`;
- full suite on Python 3.12 (pinned lock) with PostgreSQL 16, not the pinned 14.24: **2819 passed, 11 skipped,
  4033 subtests, 0 failed**. All skips are environment-only (systemd runner, bubblewrap, root, opt-in fixtures);
- `git diff --check` clean; no placeholders or secret-like files in the diff;
- GitHub Actions did not run: every job ended within 3 s with no runner assigned (account billing limit).

**Not a review of the whole diff** (4,355 lines across RV01, PL, SC, PR283). It relies on those recorded reviews.
**Not approval:** merging to canonical installs or approves nothing. Every owner gate in the run sheet and in the
IDEA-093 / FLAT-01 lines of `INCOMPLETE_WORK.md` remains open.

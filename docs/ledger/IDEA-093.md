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

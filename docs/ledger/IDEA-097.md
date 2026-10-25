# IDEA-097 — S4: REHEARSAL-only flatten test that carries over run 4's holdings

- Date / author: 2026-10-25 (~10:40Z) / Yao's request in a Claude Code session (record and implementation: Claude
  Code). Approvals: Isaac (profile hash, `signer.json`), Keegan (carry-over accounting, runtime review). Host steps:
  Yao.
- Status: **open — pre-registered. Criteria S4-1..S4-9 and S4-L1 below were committed before any S4 code or test.**
- 2026-10-25 status: **supported offline** (S4-1..S4-6, S4-7′, S4-8′, S4-9 PASS; results below). Approval, B0 BNB top-up,
  build and install (S4-L1) open.
- Related: IDEA-089 (S2, run 4), IDEA-092 H1/H2 (install needs a stock-flat wallet), IDEA-096 (the leftover-allowance
  block on run 4's flatten), IDEA-090 S2-F6 (post-approve requote; on canonical, not in run 4's RC7), IDEA-093 (FS1,
  delayed; the scored run starts Oct 29), SKILL.md §0.3 #1 (no manual trading).

## Request (in chat, 2026-10-25)

> "we can always delay the FS1 since official trading begins 29 oct, so we have time to implement the new rehearsal
> profile, make this s4 strictly for rehearsal, do the carry over match what s2 does ignore s3 … then lets see if we
> can retire this run and load the new profile in to continue the process note this profile is meant strictly to test
> the flattening process so set the flatten to a time very close to now so when we load the new profile in it
> immediately can begin selling"

**Reading (assistant; the requester can change it).**
- S4 is S2's profile with three changes: a carry-over, a window whose flatten has already begun, and its own
  `policy_id`. It is for the dev wallet only and is never installed for the final run.
- Run 5 starts from run 4's exact on-chain holdings and run 4's recorded cost basis, instead of refusing them.
- Run 5's first round is already inside the terminal flatten. It sells; it never buys.
- S3's `scheduled_flatten_at` is not used.

## Design

1. **Profile S4** (`larp-s4-rehearsal-v1`), built by `tools/deploy/build_rehearsal_candidate.py --carry-over`:
   - the S2 block unchanged (`KIT_OPEN_STATE`, 5 attempts per leg), S2's sizes, caps, gas, slippage and SHADOW scope;
   - window: `trade_after` 2026-10-25T10:00Z, `new_risk_end` = `flatten_start` 2026-10-25T10:30Z (already passed, so
     no BUY is possible and every round of run 5 is a terminal-flatten round), `signing_end` 2026-10-26T12:00Z
     (Mon 20:00 SGT; about a day of rounds for 4 names × 2 balanced children);
   - a new key `holdings_carry_over: "RUN_EXPORT"`, which declares that the run must start from a reviewed export of
     the previous run's book.
   - Scope: `holdings_carry_over` is accepted only in a REHEARSAL with S2's `KIT_OPEN_STATE` block and without
     `scheduled_flatten_at`. Profiles without the key are unchanged byte for byte.
2. **Carry-over file** `HoldingsCarryOver.v1`, exported read-only from run 4's database after run 4 is retired:
   - source `run_id`, `wallet_id`, the run's `version`, a SHA-256 of its portfolio projection, `reservations` (must be
     empty), and per stock `units`, `decimals`, `cost_basis_units`.
3. **`gate_a.initial_state`** with a carry-over profile:
   - requires the file;
   - refuses it unless its wallet matches, its source run differs from the new run, and it has no reservations;
   - refuses unless every stock's `units` equals the captured raw chain balance exactly, including zero and dust;
   - refuses any `cost_basis_units` that is not a non-negative integer, and any positive balance with zero cost.
   It then sets positions to those units and cost bases. Opening equity is cash + BNB value + Σ `cost_basis_units`
   (holdings are carried at cost, so run 5's P&L is measured against what run 4 paid). The day anchor and peak
   start at that value.
   - Without the profile key the file is refused, and the stock-flat rule is unchanged.
   - `gate_a.prepare` writes the file into the package as `holdings-carry-over.json` and pins its hash in the
     report. `gate_a_check` rebuilds the same initial state from it.
4. **IDEA-096 F1 for this run (sell the token that already has an allowance first).**
   - `MarketPort` attaches `router_allowance_units` to each stock's market row. It reads them through the quote
     verifier's own pinned decoder at one block; if the read fails, the field is omitted.
   - Among mandatory sells, the planner puts names whose router allowance is non-zero first. That name's own
     approve replaces the leftover allowance and its swap uses it up, which unblocks the other names.
   - Records without the field replay unchanged.
   - S4 never buys, so USDT, the one case F1 cannot repair, cannot pick up a leftover allowance. F2/F3/F4 stay open
     in IDEA-096.

## Known limits (recorded before testing)

- **Retiring run 4 ends its flatten window early.** Run 4 still holds GOOGLB, NVDAB, SKHYB and TSLAB, and the SKHYB
  router allowance is still open. Run 5 inherits both.
- **The post-approve requote abort (S2-F6) still applies.** The canonical build includes PR274's narrower
  requote; run 4's RC7 did not. A second adverse move can still abort a swap safely. Each name has 5 mandatory
  attempts in the session.
- **The carry-over is an accounting decision.** Cost basis comes from run 4's own ledger, not from a new
  calculation. Keegan reviews it; Isaac approves the profile hash and `signer.json`.
- **Not for the final.** FS1 starts from a fresh, stock-flat final wallet.

## Pre-registered pass criteria (written before code or tests)

| # | Pass when | Evidence |
|---|---|---|
| S4-1 | The S4 profile rebuilds byte for byte. It differs from S2's only in the window, `policy_id`, `holdings_carry_over` and their provenance, and passes `validate_live` | profile test |
| S4-2 | `holdings_carry_over` is refused in a FINAL profile, without `KIT_OPEN_STATE` hours, together with `scheduled_flatten_at`, or with any other value | profile test |
| S4-3 | `initial_state` with S4 and a matching export gives positions equal to the chain units and the export's cost bases, opening equity = cash + BNB value + Σ cost, and `check_initial_state` passes | gate_a test |
| S4-4 | `initial_state` refuses: S4 without an export; an export under a non-carry-over profile; units differing from chain by one unit; another wallet; the same run ID; reservations present; a negative or non-integer cost; a positive balance with zero cost | gate_a tests |
| S4-5 | A signed dev `gate_a.prepare` with S4 and the export packages `holdings-carry-over.json`, pins its hash, and `gate_a_check` passes on the package; without the profile key, the stock-flat refusal is unchanged | gate_a / gate_a_check test |
| S4-6 | With run 4's carried book and `now` after `flatten_start`, the first planned round has an EXIT target for every held name, at least one mandatory `TERMINAL_FLATTEN` SELL quote request or intent, and no BUY | planner test |
| S4-7 | **Red on base.** On canonical, with a non-zero SKHYB `router_allowance_units` and NVDAB worth more, the first mandatory request is NVDAB. After the fix it is SKHYB. With no allowance field, the order equals canonical's | planner test |
| S4-8 | `MarketPort` attaches `router_allowance_units` per stock from the verifier's single-block read, and omits them if the read fails, without failing the observation | market port test |
| S4-9 | The full pinned suite passes with no new failures against canonical | full suite |
| S4-L1 (live, team) | Run 5 installs from the export. Its first round sells SKHYB, the name with the allowance, then the other names; every position reaches dust before `signing_end`; balance check `MATCH`; all router allowances end at 0 | trading-status, chain monitor, BscScan |

## Revision before the S4 tests (2026-10-25 ~11:30Z; recorded before S4-1..S4-6 were run)

Yao, mid-session: "pr 282 should have the new updated logic to fix this kind of errors inside, do take a look there
as well when u build s4, we can always add more gas reserve as needed".

- **IDEA-096 F1 is dropped; PR282's F2/F3/F4 recovery is used instead.**
  - PR282 (teammates, AL-IMPL01, 2705 tests PASS offline) clears a leftover allowance with a zero-only approve
    before the trade approve, and clears an aborted swap's own approve. That covers USDT too, which F1 could not.
  - My F1 draft (planner ordering, `router_allowance_units` on market rows) touched the same quote-verifier/port code.
    It was an uncommitted working copy: its red-on-base test failed on canonical as expected (NVDAB first) and passed
    after the change, and it was discarded before the merge.
  - This branch merges `claude/flatten-allowance-deadlock-20261025` at `5cac4ca4`, the PR282 head.
- **Criteria S4-7 and S4-8 are replaced** by:
  - **S4-7′:** the S4 profile carries PR282's recovery gas (`gas_action_budget_units` = 8 × 1200000 × 160000000,
    exit reserve 5 × 2 × that) and passes `validate_live`;
  - **S4-8′:** M3's caps review (`review_rehearsal_caps --allowance-recovery`) refuses a leftover allowance without
    the flag, and with it opts both execution and the signer policy into recovery and changes nothing else.
- **`signing_end` is 2026-10-27T12:00Z** (Tue 20:00 SGT), not Mon 12:00Z. That allows a slower approval/install and
  stays before FS1 (Oct 29).
- **Gas.** Recovery's exit reserve is 0.01536 BNB, against about 0.00518 BNB in the wallet. Yao accepted adding BNB;
  this is run-sheet step B0.

## Results (2026-10-25, offline; tested source `a2a5ab81`)

| # | Result |
|---|---|
| S4-1 | **PASS.** Profile `e79a92fc…` (digest `6164039c…`, M3 probe `9397c0cf…`) rebuilds byte for byte. It differs from S2's `eb55d76a…` only in the window, `policy_id`, `holdings_carry_over`, the two recovery gas keys and their provenance; `validate_live` passes. The builder refuses S4 without S2 hours, with one exit child, or with S3. |
| S4-2 | **PASS.** The key is refused in FINAL, without `KIT_OPEN_STATE`, with `scheduled_flatten_at`, and with any value other than `RUN_EXPORT`. Profiles without it are unchanged. |
| S4-3 | **PASS.** Run 4's units (GOOGLB 0.05896, NVDAB 0.08944, SKHYB 0.13788, TSLAB 0.05096) plus the exported cost; opening equity = cash + BNB value + Σ cost; day anchor and peak equal it. |
| S4-4 | **PASS.** Refused: S4 without an export; an export under S2; one unit off (names the symbol); another wallet; the same run ID; reservations; negative or fractional cost; a holding with zero cost; cost without a holding; another schema; a missing key; a missing symbol. The stock-flat refusal is unchanged without the key. |
| S4-5 | **PASS.** Signed dev `prepare` with the real S4 profile, carry-over and recovery packages `holdings-carry-over.json`, pins its hash in `input_hashes` and `holdings_carry_over`, and sets `driver.allowance_recovery`. `check_scope`/`check_inputs` pass. A tampered export, a dropped pin or a missing file is refused. `package_files` accepts the optional file, and the dev runtime builds without network. |
| S4-6 | **PASS.** With `now` after `flatten_start`, every held name is `TERMINAL_FLATTEN` and every request is a mandatory SELL. |
| S4-7′ | **PASS.** Action budget 1536000000000000 = 8 × 1200000 × 160000000; exit reserve 15360000000000000 = 5 × 2 × action; sizing budget unchanged from S2. |
| S4-8′ | **PASS.** Hosted assembly refuses run 4's SKHYB allowance without `--allowance-recovery`. With it, execution `allowance_recovery: true`, the signing policy is the reviewed development policy plus `allowance_recovery: true`, and `signer.json` carries it. A non-boolean opt-in is refused. |
| Sheet | **PASS.** `tests/runtime/test_run5_sheet.py`: one run and database; run 4 retired; probe/profile pins; recovery and carry-over flags in M3/M4; signer diff base `56e029af…`; all scripts parse; a synthetic X1 output saves 0600 without overwrite and rebuilds the S4 state; a truncated or in-flight export is refused. |
| S4-9 | **PASS.** Full suite in the team's Linux image `larp-test:pr282` (Python 3.12.15) against a disposable PostgreSQL 14.24 container: **2717 passed, 12 skipped, 4018 subtests passed; 3 failed, all git-only**. The suite ran on a `git archive` copy without `.git`. Those three files (`test_deploy_presetup`, `test_final_review_d`, `test_gate_a`) pass when rerun in a git checkout: 82 passed, 107 subtests. The 12 skips are 5 systemd, 3 bubblewrap, 2 opt-in fixtures, 1 root directory-mode case and 1 no-GitHub-origin case. The same suite on macOS with PostgreSQL gave 2721 passed and 1 failure, the Linux-only `/proc` memory probe of IDEA-094 AR7. Not GitHub CI (billing-blocked); no host, systemd or release acceptance. |
| S4-9 (merged head) | **PASS.** After merging canonical (PR282 merged with PR282-RV01's fixes), tested source `04c8997b` from a git clone in the same Linux image and PostgreSQL 14.24: **2722 passed, 0 failed, 12 skipped (as above), 4018 subtests passed**, 306 s. Focused S4/recovery suites: 36 passed. |
| S4-L1 | **NOT RUN.** It needs B0 (BNB top-up), the build, Isaac's approval and the install (run sheet `build/ops/rehearsal-install-s4-20261025/`). |

Remaining: Keegan reviews the carry-over accounting (opening equity at cost) and the recovery gas. Isaac approves the
profile, probe and `signer.json`. Yao: B0, then the sheet. PR282's own review gates (FLAT-01) still apply, because
S4 runs on its code.

## PR284-RV01 review (2026-10-25, Claude Code; asked by the user to review and merge if there are no issues)

Checked:
- the carry-over acceptance in `gate_a.initial_state`/`prepare`/`check_inputs`;
- `carry_over.require_scope`;
- the caps-review recovery opt-in (`review_rehearsal_caps`);
- the S4 profile's recovery gas;
- the X1 export;
- the run-5 sheet against SKILL.md §0.3, F-120 and F-125.

**The code paths are sound:**
- the export must equal the captured chain units;
- a FINAL profile, missing `KIT_OPEN_STATE` hours and S3 are all refused;
- a missing or extra export file is refused;
- the report pins the export hash, and `gate_a_check` rebuilds the starting state from it.

**Fixed in this review:**
- **RV01-1 (bug, X1).** `x1-export-holdings.sh` took `reservations` from `projection['portfolio']`. That copy is never
  updated, because `ledger_from` rebuilds reservations from the `reservations` table. The "no reservations in flight"
  check therefore always passed. X1 now reads non-zero rows of the `reservations` table and counts unfinished
  `execution_records`; either one makes the export's `reservations` non-empty, which X1-save and `gate_a` refuse.
  `larp_execution` already has SELECT on both tables. Regression test:
  `test_x1_reads_live_reservations_and_the_execution_barrier_not_the_projection_copy`.

**Open, team decisions needed before run 5 (not changed here):**
- **RV01-2 (rule).** Step B0 tops up the dev wallet's BNB by hand. The team's confirmed F-120 reading (SKILL.md §0.3 #1,
  Yao Zhu 2026-10-16) allows manual USDT → BNB swaps only *before* a wallet's first agent trade. After that, only the
  agent's own logged top-ups are allowed (G-13). The dev wallet's first agent trade was 2026-10-24 06:00Z (run 4), and
  a transfer from another wallet is never-do #3. B0 therefore needs either:
  - an explicit, recorded team decision that amends §0.3 for the dev phase; or
  - a smaller reviewed S4 gas envelope that the wallet's current ≈0.00518 BNB covers. The four small run-4 positions
    each need one exit child; the actual gas is about 0.0000242 BNB per approve and swap.
- **RV01-3 (schedule).** `signing_end` is 2026-10-27T12:00Z, but F-125 says the development phase ends Mon Oct 26
  (UTC, F-121). Final activation (install, F-125 self-check from Oct 27 00:00Z) needs the same primary and signer
  hosts, which run 5 occupies until it is retired. Proposed: end run 5 by about 2026-10-26T20:00Z, and retire it as soon
  as it is flat.
- PR284-RV01 validation (Claude Code, PostgreSQL 16.15 / Python 3.12.3, not the pinned 14.24 image): full suite at
  `ef88ba11` **2724 passed, 11 skipped, 4018 subtests, 0 failed**; base `51b846f8` **2707 passed, 11 skipped, 4018
  subtests, 0 failed** (+17 = this PR's tests and the RV01-1 regression). Not merged: RV01-2 and RV01-3 are open.
- 2026-10-25 correction (Claude Code, PR284-RV01-3 fixed on the user's instruction "fix and merge it"):
  - **Window moved.** `signing_end` is now **2026-10-26T20:00Z** (Tue 04:00 SGT), inside the development phase, which
    ends Oct 26 (F-125), and before final activation needs the hosts.
  - **New pins.** These supersede the `e79a92fc…`, `6164039c…` and `9397c0cf…` recorded in the results above:
    - S4 profile `58b3180678a01d46b114dad6fadd296cc8a68677f7ab4260892aee5bd33c3b55`;
    - digest `28aa420a89916a06fe234f990fdeb0d89835dd49e0ded621425f7e7beb94aa0c`;
    - M3 probe `379c476b90c24e6ba60e1e1839e53e892b16cb2b852187263a65b471505ab8fa`.

    The new profile differs from `e79a92fc…` only in `signing_end` and the window provenance text. The sheet, scripts
    (M1, M3, M4, P4), README, status and backlog are updated. The probe method reproduces the old pins from the old bytes.
  - **RV01-2 is not changed by this merge.** B0 stays blocked in the run sheet. Before B0, either:
    - the team records an amendment to SKILL.md §0.3 #1 / F-120 for a dev-wallet top-up after its first agent trade; or
    - Isaac and Keegan review a smaller S4 gas envelope that the wallet's current BNB covers.

    Merging is not activation; nothing here is approved, installed or run.
- PR284-RV01-3 validation (Claude Code, PostgreSQL 16.15 / Python 3.12.3): full suite at `477ac4f1` **2724 passed,
  11 skipped, 4018 subtests, 0 failed**; S4/run-5/Gate A/S2/S3/hosted-assembly suites 103 passed. Merged on the user's
  instruction; B0 (RV01-2) remains a blocked run-sheet step.

## M3-R1 — M3 treats released reservations as in flight (2026-10-25 ~13:55Z; pre-registered before the fix was tested)

- **Finding.** All three M3 attempts (13:21Z, and 13:45–13:49Z with run 4 idle) refused with
  `SIGNER_ASSEMBLY_REFUSED`. In every one, only "nothing in flight" failed; assets MATCH, nonce settled, no allowance
  open.
  - The LD02 probe reports `in_flight.reservations` as `SELECT asset, count(*), sum(units) FROM reservations GROUP BY
    asset`, which gives run 4's released rows: 8 assets, all with `units: 0`.
  - `review_rehearsal_caps.collect` required that dict to be empty. A source run that has traded can therefore never
    pass M3. Run 3, M3's previous source, never traded.
- **Fix.** Only positive units are in flight, as X1 already reads them (PR284-RV01-1).
- **Pass when (M3-R1):**
  - a packet listing released rows with zero units assembles;
  - positive units, a missing `units`, a boolean `units` and the old list form are still refused, with no candidate
    written;
  - the new test fails on canonical `9fe5fb07` and passes after the fix;
  - the hosted-assembly suite passes.
- **M3-R1 result: PASS.**
  - The new test fails on canonical `9fe5fb07` (the old check refuses run 4's released rows).
  - After the fix it passes, as do the hosted-assembly, S1 caps, S4 and run-5 sheet suites (39 passed).
  - Full suite without PostgreSQL: 2178 passed, 0 failed. The change touches no database code.

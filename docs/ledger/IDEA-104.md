# IDEA-104 — S5: FS1's settings on the dev wallet, selling everything on Monday night (SGT)

- Date / author: 2026-10-26 SGT / Claude Code, asked by the user: "Can you create S5 that is fs1 but it sells all on
  monday night, leave FS1 as our final trading strategy". Owners: Yao (install, run), Isaac (profile/signer
  approval), Keegan (review); Keith (strategy values: unchanged from FS1).
- Status: **open. R1 (Monday-night window) superseded by R2 (to Tue Oct 27 12:00 SGT, FS1 token history), supported
  offline 2026-10-26 (results at the end). Top-up (B0), the qualified history input, approval and install remain.**
- Related: IDEA-093 (FS1, FS1-R), IDEA-098 (FS1 recovery profiles), IDEA-096 (allowance recovery), IDEA-097 (S4 run 5/6,
  dev wallet flat after run 6), IDEA-102 (mandatory sell spacing), F-125 (development ends Mon Oct 26 UTC).

## Design

- S5 is the FS1-R recovery profile (`fs1-rehearsal-recovery.json` `17ab891d…`) with a new window and `policy_id`
  `larp-s5-rehearsal-v1`. Everything else is unchanged and comes from the same builder path:
  - FS1's `s1` block (weights 1/5, 24/7 `KIT_OPEN_STATE` hours, 5 attempts per discretionary leg);
  - 20 bp slippage and the four FS1 review refinements;
  - IDEA-096 allowance-recovery gas;
  - the deterministic SHADOW dev scope of every signed rehearsal.
- Window (reading "Monday night" as Singapore time; one constant to change otherwise):
  - `trade_after` 2026-10-25T20:00Z (Mon 04:00 SGT);
  - `new_risk_end` 2026-10-26T12:00Z (Mon 20:00 SGT);
  - `flatten_start` 2026-10-26T13:00Z (Mon 21:00 SGT): every holding becomes a mandatory sell;
  - `signing_end` 2026-10-26T20:00Z (Tue 04:00 SGT), inside the development phase, as S4 (PR284-RV01-3).
- FS1 (FINAL) is not touched. Its four profiles must rebuild byte for byte.
- Dev wallet: flat after run 6 (IDEA-097 S4-L1), so S5 installs as a fresh run (no carry-over). With about 90 USDT and
  an 18.64 USDT minimum trade, the book may hold four names, not five [ESTIMATE].

## Pre-registered pass criteria (written before any test or code)

| # | Pass when |
|---|---|
| S5-1 | `build_rehearsal_candidate --exit-children 2 --fs1-rehearsal --allowance-recovery --s5 …` builds `validate_live`-valid S5. It differs from `fs1-rehearsal-recovery.json` only in `trade_after`, `new_risk_end`, `flatten_start`, `signing_end`, `policy_id` and those keys' provenance. |
| S5-2 | The S5 window is the four instants above, ordered `trade_after < new_risk_end < flatten_start < signing_end`, and `signing_end` is before 2026-10-27T00:00Z. |
| S5-3 | `--s5` is refused without `--fs1-rehearsal` and `--allowance-recovery`, and with `--carry-over` or `--scheduled-flatten-at`. |
| S5-4 | The committed S5 file rebuilds byte for byte. All four FS1 profiles and the S4 profile rebuild byte for byte (unchanged). |
| S5-5 | A planner check on the S5 profile: at 13:00Z on Mon Oct 26 with a held name, the planner plans a mandatory SELL (`TERMINAL_FLATTEN`); at 11:59Z a BUY is still admitted; at 12:00Z new buys are refused. |
| S5-6 | Full suite: no new failures against canonical in the same environment; exact counts reported. |

## Results (2026-10-26; Python 3.12 from the pinned lock, PostgreSQL 16 — not the pinned 14.24 image)

Commits: `8ee6420a` (criteria), `2642ab94` (tests, red on canonical `ecdbc1aa`: 7 failed, 1 passed — the S5-5 planner
check exercises the planner on the S5 window and needs no builder change), `0eb588d9` (builder `--s5`, profile, README).

| # | Result |
|---|---|
| S5-1 | **PASS.** `rehearsal-s5.json` `c7938dae…` (digest `cb7f8e1c…`) passes `validate_live`. It differs from `fs1-rehearsal-recovery.json` only in the four window keys and `policy_id`. In provenance it differs in those keys and in the `decision_id` text of `s1` and `baseline`; the `s1` block bytes and `data_hash` are identical. Signed dev preparation, `gate_a_check` scope and inputs, and the runtime build pass. |
| S5-2 | **PASS.** Window 2026-10-25T20:00Z / 2026-10-26T12:00Z / 13:00Z / 20:00Z, strictly ordered, ends before 2026-10-27T00:00Z. |
| S5-3 | **PASS.** `--s5` is refused without `--fs1-rehearsal` or `--allowance-recovery`, and with `--carry-over` or `--scheduled-flatten-at`. |
| S5-4 | **PASS.** S5 rebuilds byte for byte. The four FS1 profiles keep their SHA-256 (`19176e6c…`, `b8ba06e2…`, `54802665…`, `17ab891d…`), and the S4 tests pass unchanged. |
| S5-5 | **PASS.** At 11:59Z one discretionary BUY is planned; at 12:00Z no BUY intent or BUY quote request; at 13:00Z every held name (NVDAB, SKHYB) has a `TERMINAL_FLATTEN` requirement and the intents are mandatory SELLs only. |
| S5-6 | **PASS.** Full suite on the branch: **2878 passed, 11 skipped, 4060 subtests, 0 failed**. Canonical `ecdbc1aa` in the same container: 2869 / 11 / 4060 / 0. The difference is the 9 new tests. The skips are environment-only. |

Result state: **supported** offline. M3 probe for the profile: `9f2dde00…`. Not done: an S5 run sheet, Isaac's
approval of the profile and `signer.json`, the install (Yao), and the live run.

## R2: S5 runs until Tue Oct 27 12:00 SGT and takes FS1's token-history input (2026-10-26 SGT, pre-registered before tests or code)

**Request (in chat, 2026-10-26 11:45 SGT):** "we are now going to deply s5, check the profile and make sure it runs until
tuesday 1200 sgt in addition make sure that all the new fs1 details are reflected in s5, s5 is our fs1 mirror run as
reherasl since we are given extra time to test and refine our pipeline until the 28th and then we have to freeze and
deploy our fs1". The development time is extended to Oct 28 (F-126, relayed by the user); S5-2's "before
2026-10-27T00:00Z" bound came from F-125's Oct 26 end and is replaced below.

**Check of the R1 profile.** Its `trade_after` (Mon 04:00 SGT) has passed, and its flatten (Mon 21:00 SGT) and
`signing_end` (Tue 04:00 SGT) end the run eight hours before Tue 12:00 SGT. Since R1 was built, canonical gained one FS1
change: PR295 / IDEA-103 makes FS1 FINAL and FS1-R preparation and startup require a pinned `TokenHistoryConfig.v1`
(`larp/marketdata/history.py` `requires_history`, keyed on their two `policy_id`s). S5's `policy_id`
`larp-s5-rehearsal-v1` is not in that list, so the R1 S5 would start **without** the live trend-history callback:
not an FS1 mirror. FS1's four profiles and the S4 profile did not change.

**Design.**
- New window (one constant in `tools/deploy/build_rehearsal_candidate.py`):

  | Key | UTC | Singapore |
  |---|---|---|
  | `trade_after` | Mon Oct 26 06:00 | Mon Oct 26 14:00 |
  | `new_risk_end` | Mon Oct 26 23:00 | Tue Oct 27 07:00 |
  | `flatten_start` | Tue Oct 27 00:00 | Tue Oct 27 08:00 |
  | `signing_end` | Tue Oct 27 04:00 | **Tue Oct 27 12:00** |

  Four hours of flatten is 16 mandatory-sell slots per name at IDEA-102's 15-minute spacing. An install after
  `trade_after` simply starts buying at install (execution P5 before runtime P4, as every run sheet).
- `requires_history` also covers `larp-s5-rehearsal-v1`, so S5 needs the same pinned `token-history.json` as FS1.
  No other profile's behaviour changes.
- Everything else in S5 stays FS1-R with recovery (`17ab891d…`): FS1's `s1` block, 20 bp, the four PR278-RV01 fields,
  recovery gas, deterministic SHADOW dev scope.

| # | Pass when |
|---|---|
| S5R2-1 | The rebuilt S5 passes `validate_live` and differs from `fs1-rehearsal-recovery.json` only in the four window keys, `policy_id` and those keys' provenance (S5-1, unchanged). |
| S5R2-2 | The window is the four instants above, strictly ordered; `signing_end` is 2026-10-27T04:00Z (Tue 12:00 SGT) and before 2026-10-28T00:00Z. |
| S5R2-3 | S5 requires token history: signed dev preparation without `token_history_raw` is refused; with it, `token-history.json` is packaged, `driver.token_history_sha256` pins it, `gate_a_check` scope/inputs pass, and the built runtime's `series` is a `SessionHistory`. A runtime config without the history pair is refused at startup. |
| S5R2-4 | FS1 FINAL and FS1-R still require history; the S2, S4 and other existing profiles still do not. The four FS1 profiles and the S4 profile rebuild byte for byte; the committed S5 file rebuilds byte for byte. |
| S5R2-5 | Planner on the S5 profile: at Mon 22:59Z a discretionary BUY is planned; at Mon 23:00Z no BUY intent or BUY quote request; at Tue 00:00Z every held name has `TERMINAL_FLATTEN` and the intents are mandatory SELLs only. |
| S5R2-6 | Full suite: no new failures against canonical `5e3f33df` in the same environment; exact counts reported. |

**R2 addendum: opening-cash check (added 2026-10-26 SGT before the check was run).** Hand arithmetic on the S5
profile suggests the dev wallet's run-6 closing balance (USDT 81.373047, BNB 0.024973; IDEA-097) is too small for any
S5 buy. FS1's `s1_capital_basis` `EXCLUDE_GAS` leaves stock capital `cash − cost_reserve` ≈ 81.27 USDT, so each name's
95 % × 1/5 target is ≈ 15.44 USDT, below `minimum_trade_units` 18.637420 USDT, and neither `S1_LEVEL_CHANGE` nor
`S1_TOP_UP` fires. The break-even is cash ≈ 98.19 USDT (0.19 × (cash − 0.1) ≥ 18.637420). R1's "four names at about
90 USDT" estimate is wrong for this profile.

| # | Pass when |
|---|---|
| S5R2-7 | Planner on the S5 profile's sizing keys with a flat book inside the buy window: at cash 81.373047 USDT and BNB 0.024973 (profile BNB price) no BUY intent or BUY quote request is planned; at cash 101.373047 USDT with the same BNB, five BUY targets are planned and the first BUY quote request is at least `minimum_trade_units`. |

**R2 addendum: declared USDT top-up in the M3 caps review (added 2026-10-26 SGT before tests or code).** If the dev
wallet is topped up to meet S5R2-7, M3 must accept it. `tools/deploy/review_rehearsal_caps.py` `chain_start` accepts
USDT equal to the source ledger or short by an exactly declared seed debit (`--accept-usdt-deficit-units`), and refuses
any USDT surplus. Add the mirror image: `--accept-usdt-surplus-units N`, an exact declared top-up.

| # | Pass when |
|---|---|
| S5R2-8 | Hosted review with `usdt_surplus=N`: accepted only when chain USDT − ledger USDT is exactly N, USDT is classed `SURPLUS` and the packet status is `SURPLUS_ONLY`; the new run starts from the chain cash; `portfolio-rebinding.json` records `accepted_usdt_surplus_units` N. Refused: an undeclared surplus, a surplus off by one unit, a declared surplus with a matching chain, a negative or non-integer value, a surplus and a deficit together, and numeric-only mode with a surplus. Every existing deficit/BNB/stock test passes unchanged. |

## R2 results (2026-10-26; Python 3.12 from the pinned lock, macOS for focused runs; full suite in `larp-test:pr282` /
PostgreSQL 14.24)

Commits: `a4a822df` (S5R2-1..6 criteria), `c480667e` (tests, red on the merged base: 4 failed), `e5426786` (window,
`requires_history`, profile), `dbbbd2d3` / `d7b629e8` (S5R2-7 criterion, test), `68e082c9` / `ece4c2f7` / `5751a449`
(S5R2-8 criterion, red tests, code), `6b9cadb8` (run-7 sheet and its static tests).

| # | Result |
|---|---|
| S5R2-1 | **PASS.** `rehearsal-s5.json` `5a5a200a…` (digest `64918e6a…`, M3 probe `8ba1328f…`) passes `validate_live` and differs from `fs1-rehearsal-recovery.json` only in the window keys, `policy_id` and their provenance (S5-1 unchanged). The `--s1-decision` text now says "from Tuesday Oct 27 08:00 SGT". The R1 profile still reproduces probe `9f2dde00…`, so the probe method is unchanged. |
| S5R2-2 | **PASS.** 2026-10-26T06:00Z / 23:00Z / 2026-10-27T00:00Z / 04:00Z, strictly ordered; `signing_end` Tue 12:00 SGT, before Oct 28. |
| S5R2-3 | **PASS.** Signed dev preparation packages `token-history.json` and pins it at `/etc/larp/token-history.json`; `gate_a_check` scope and inputs pass; the runtime's `series` is a `SessionHistory`. Without the input, preparation and startup refuse. |
| S5R2-4 | **PASS.** FS1 FINAL (both) and FS1-R (both) still require history; S1, S2, S3, S4 and the equal-weight rehearsal do not. FS1 profiles keep `19176e6c…`, `b8ba06e2…`, `54802665…`, `17ab891d…`; S5 rebuilds byte for byte. The rehearsal test helpers now key on `requires_history`, not one `policy_id`. |
| S5R2-5 | **PASS.** Mon 22:59Z one discretionary BUY; Mon 23:00Z no BUY intent or request; Tue 00:00Z NVDAB/SKHYB `TERMINAL_FLATTEN`, mandatory SELLs only. |
| S5R2-6 | **PASS.** Full suite in `larp-test:pr282` (Python 3.12.15) with PostgreSQL 14.24: branch **2919 passed, 12 skipped, 4069 subtests, 3 failed**; canonical `5e3f33df` in the same setup: 2897 passed, 12 skipped, 4060 subtests, the same 3 failed. The 3 (`test_deploy_presetup` ignored-directory, `test_final_review_d` credential scan, `test_gate_a` GA15b) call `git check-ignore`/`git ls-files`, which cannot read the worktree's git metadata inside the container: environment-only. +22 tests are the new S5, top-up and run-7 sheet tests. |
| S5R2-7 | **PASS (finding confirmed).** At 81.373047 USDT / BNB 0.024973, no BUY target, intent or request. At 101.373047 USDT, five BUY targets and one 19.0 USDT BUY intent (serial). Bisection: the first buy needs about **98.31 USDT** of cash (98 310 912 units at 1 000-unit resolution). R1's "four names at about 90 USDT" was wrong. With quotes supplied, the planner returns the first buy as an intent, so the test checks the intent rather than a quote request. |
| S5R2-8 | **PASS.** `--accept-usdt-surplus-units N` accepts exactly N with USDT `SURPLUS` and status `SURPLUS_ONLY`, starts the run from chain cash and records `accepted_usdt_surplus_units`. It refuses an undeclared surplus, ±1 unit, a declared surplus on a matching chain, negative, float and boolean values, a surplus together with a deficit, a status mismatch, and numeric-only mode. All existing hosted-assembly tests pass unchanged. |

**Run-7 sheet:** `build/ops/rehearsal-install-s5-20261026/`, adapted from the run-5 sheet. It retires run 6; has no X1
step; M4 takes the qualified `TOKEN_HISTORY`, refuses synthetic history, held stock and cash below 98.32 USDT, and
expects a signer diff of exactly `build_id`/`database_name`/`run_id` against run 6's `1e052e26…`; P3 installs and
checks `token-history.json`; M3 declares the B0 top-up. `tests/runtime/test_run7_sheet.py` pins it statically.
Not run against any host.

**Not mirrored (by design or out of scope):** S5 keeps the deterministic assessor in the SHADOW dev scope (S2-1
`KIT_OPEN_STATE` rule), so the AIand/ChatGPT routing, `model_budget` and parallel model assessments of FS1 FINAL are not
exercised; FS1's `activation_self_check` is FINAL-only; sizes are 1/5 of about 100 USDT, not 170 USDT.

**Remaining:** Yao: B0 top-up (≥ 98.32 USDT, about +20 USDT recommended) and the TH input with Keith's actual
timestamp-evidence hash; team: merge PR294 so the build contains R2; Isaac: A1 (profile, probe, signer hash);
Keegan: review S5R2-8, the sheet and the input; Yao: install; then the live checks in the sheet's J section.

## R3: FS1's model calls and authority, and the dev wallet as it is (2026-10-26 SGT, pre-registered before tests or code)

**Requests (in chat, 2026-10-26):** "well i cant add more usdt so use whatever is inside" and "yes turn on the FS1's
aland/chatgpt model calls like FS1, s5 is meant to mirror FS1".

**Design.**
- **Models as in FS1.** S5 takes FS1 FINAL's evidence authority: `evidence_mode` `BOUNDED_FALSIFIER`,
  `falsifier_authority` `DISCRETIONARY_EXIT` (statements stay `SHADOW`, `red_flag_authority` RF1 4.02 / RF2 1.05, 2.06
  as before). A verified Class 1 finding then forces a mandatory SELL, and a verified Class 2 finding blocks buys, as in
  FS1. Signed preparation then needs the reviewed routing, because the deterministic-rehearsal path covers SHADOW
  profiles only. M4 passes `config/intelligence/aiand-routing.fs1.json` (`9b86c732…`); the runtime assessor is
  `aiand_routed` with FS1's five assessment workers. `require_open_state_scope` gains a third, narrow scope: a
  REHEARSAL with `policy_id` `larp-s5-rehearsal-v1`, FS1's v1 authority, in a `dev` run. S2's and FS1's scopes are
  unchanged.
- **Wallet as it is (no top-up).** S5 counts BNB in stock capital (no `s1_capital_basis` key; FS1 keeps
  `EXCLUDE_GAS`). At run 6's closing balance (81.373047 USDT, BNB 0.024973 at the profile's 722.15 USDT/BNB), equity is
  about 99.4 USDT, so each 1/5 target at 95 % is about 18.87 USDT, just above the 18.637 USDT minimum. Cash allows at
  most four buys of about 19 USDT.
- The R2 top-up guard in M4 is replaced with an equity guard; `--accept-usdt-surplus-units` stays available but
  unused (`TOPUP` 0).

| # | Pass when |
|---|---|
| S5R3-1 | The rebuilt S5 passes `validate_live`. Against `fs1-final-recovery.json` (`b8ba06e2…`) its non-provenance keys differ only in `environment`, `cost_reserve_units`, `expected_equity_units`, `per_trade_cap_units`, the four window keys, `policy_id`, `activation_self_check` (absent) and `s1_capital_basis` (absent). Its `s1` block equals FS1's. |
| S5R3-2 | `require_open_state_scope` accepts S5 in `dev` and `None`; refuses it in `live`, `offline` and `''`; refuses a REHEARSAL with another `policy_id` (FS1-R, S2) and FS1's authority; refuses S5 with SHADOW statements changed. Every existing S2-1/FS1 scope test passes unchanged. |
| S5R3-3 | Signed dev preparation of S5 without routing is refused. With the FS1 routing file and an adoption reference it packages `model-routing.json`, pins `9b86c732…`, sets assessor `aiand_routed` and keeps the token-history pin; `gate_a_check` scope and inputs pass; the built runtime has five `RoutedAssessor`s and a `SessionHistory`. |
| S5R3-4 | Planner on the S5 profile at run 6's closing balance in the buy window: the first round plans one BUY intent of at least `minimum_trade_units`; with three names already held at about 19 USDT each and the matching remaining cash, a fourth BUY is still planned. |
| S5R3-5 | Planner at Mon 22:59Z BUY, Mon 23:00Z no BUY, Tue 00:00Z `TERMINAL_FLATTEN` mandatory SELLs only (S5R2-5 on the R3 profile). The FS1 profiles and S4 still rebuild byte for byte. |
| S5R3-6 | Full suite: no new failures against canonical `81ee30a1` in the same environment; exact counts reported. |

**R3 amendment (2026-10-26 SGT, before any R3 test ran).** User, in chat: "s5 should not count BNB as capital and i
think the real token history file is already in FS1 just take from there and finally all approvals from all parties
are given so just ahead". So S5 keeps FS1's `s1_capital_basis` `EXCLUDE_GAS`; the BNB-counting design above is
withdrawn. Replacements:
- S5R3-1: the allowed differences from FS1 FINAL lose `s1_capital_basis` (S5 keeps `EXCLUDE_GAS`).
- S5R3-4: at run 6's closing balance S5 plans no BUY (S5R2-7 still holds); at 101.373047 USDT it plans one.
- Token history: no `TokenHistoryConfig.v1` with real evidence exists in the repository, the private
  `deploy/activation/` folder or any local checkout (searched 2026-10-26). FS1 has none either; TH-01 is open. M4
  keeps refusing a synthetic file.
- Approvals: recorded as relayed by the user ("all approvals from all parties are given"); no named record or hash
  was given.

## R3 results (2026-10-26)

Commits: `ca253e7b` (criteria), the R3 amendment, red tests (3 failed on base), `3af0f670` (builder, scope, profile,
sheet). Profile `rehearsal-s5.json` `f371b18d…` (digest `63c35391…`, M3 probe `90344caa…`).

| # | Result |
|---|---|
| S5R3-1 | **PASS.** `validate_live` passes; against FS1 FINAL `b8ba06e2…` the non-provenance differences are exactly `environment`, `cost_reserve_units`, `expected_equity_units`, `per_trade_cap_units`, the four window keys, `policy_id` and the absent `activation_self_check`. `s1`, red-flag authority and `EXCLUDE_GAS` equal FS1's. |
| S5R3-2 | **PASS.** S5 accepted in `dev`/`None`; refused in `live`, `offline`, `''`; FS1-R and S2 with FS1's authority, S5 with other statement authority, SHADOW evidence or FINAL environment refused. S2-1/FS1 tests unchanged. |
| S5R3-3 | **PASS.** Deterministic signed preparation refused; with FS1 routing: `model-routing.json` packaged, `9b86c732…` pinned, `aiand_routed`, token history pinned, `gate_a_check` PASS; the dev runtime has five `RoutedAssessor`s and a `SessionHistory`; startup without history refused. |
| S5R3-4 | **PASS (amended).** Run 6's closing balance: no BUY; +20 USDT: one BUY ≥ minimum. |
| S5R3-5 | **PASS.** Window behaviour unchanged; FS1 and S4 profiles byte for byte. |
| S5R3-6 | **PASS.** `larp-test:pr282` / PostgreSQL 14.24: branch 2924 passed / 12 skipped / 4069 subtests / 3 failed; canonical `81ee30a1` 2919 / 12 / 4069 / the same 3 (git metadata unavailable in the container). |

**Blocked before install (2026-10-26):** (1) at 81.37 USDT with gas excluded S5 buys nothing; the user cannot add
USDT, so either S5 runs as a no-trade pipeline rehearsal or its sizing changes (decision open). (2) No real
`TokenHistoryConfig.v1` exists (TH-01); M4 refuses a synthetic one. Approvals relayed as given.

## PR296-RV01 — review and independent FS1 preparation (2026-10-26, criteria before execution)

Review head: `f89ec87389d0e20b5725e1a4c67961d602db5704`; base: `81ee30a1696c54ff22deed9ced3ce6aa26538b07`.
User requested review/fixes and comparison with FS1, including standalone FS1 operation. No push, merge,
installation, provider calls, wallet operations or strategy-value changes are authorized by this review.

Pass criteria (synthetic inputs, no registered credentials):
- RV1: direct runtime startup rejects deterministic signed FS1/S5 configurations as preparation already does;
  historical scoped deterministic rehearsals continue to pass.
- RV2: S5 initializes/activates before signer/execution startup, then starts runtime only after execution is
  healthy. The runtime-start step never disables execution; a missing/restarting executor refuses runtime startup.
- RV3: a dedicated offline FS1 preparer accepts an explicitly named final wallet, fresh chain capture, database,
  adoption record and pinned history/routing, producing live FINAL inputs with no previous run/signing config.
  Wrong wallet, missing history/adoption and a rehearsal profile refuse; profile/routing bytes stay unchanged.
- RV4: FS1 constructs five routed assessors and session history from a clean evidence/budget directory and
  independent initial state; no S5 files or state are read. Existing self-check, five-buy/restart/replay and
  terminal-flatten regressions pass. Quote/assembly coverage uses fresh FINAL inputs, never a dev-run rebinding.
- RV5: compare every non-provenance S5/FS1 profile field; run focused regressions then the full offline suite
  in the available Python 3.12.15/PostgreSQL 14.24 environment, recording skips and any environment failures.

Implementation/validation results follow below after execution. Real history semantics, final funding/gas,
model-budget reconciliation, exact signer/profile/release approvals and host qualification remain owner gates.

### PR296-RV01 findings and S5/FS1 comparison

- **RV-F1 (P1):** `build_driver` accepted deterministic signed FS1 FINAL and S5 directly, although preparation
  and package qualification refused that scope. Two direct-start regressions both failed on the reviewed head
  (no ContractError). Runtime now applies the same scoped deterministic-rehearsal restriction as preparation.
- **RV-F2 (P1):** the run-7 P4 script started runtime while execution was disabled; run 4 already demonstrated
  that this can expire the first intent. P4 now initializes/activates and starts evidence/delivery only. After S2
  and P5, P6 checks execution is active with zero restarts before starting runtime. Initialization refuses active
  or transitioning services. The FINAL scripts use the same ordering and independent FINAL identities.
- **RV-F3 (P2):** the run-7 sheet still instructed a USDT transfer despite the R3 amendment saying the user
  cannot top up. The transfer recommendation is withdrawn; current sizing/capital/minimums and the cash refusal
  remain unchanged. B0 records the remaining sizing/no-trade decision. This review does not adopt either option.
- **RV-G1 (standalone gap):** the FINAL folder contained only a plan relying on run-4-pinned preparation/start
  scripts; the rehearsal caps tool selects a development policy and rebinds a source ledger. `prepare_fs1.py`
  now prepares fresh FINAL inputs with explicit wallet/database/adoption and exact profile/routing/history pins,
  and independently assembles fresh FINAL caps inputs. Wallet-specific ai-seeds/nonce directories avoid reusing
  development ownership markers. No S5 state, old signer, run-6 bindings or completed rehearsal is needed.

The committed S5 `f371b18d…` and FS1 FINAL recovery `b8ba06e2…` differ in **exactly ten non-provenance fields**:

| Field | S5 | FS1 FINAL |
|---|---|---|
| `environment` | REHEARSAL (`dev` run) | FINAL (`live` run) |
| `policy_id` | `larp-s5-rehearsal-v1` | `larp-fs1-final-v1` |
| `expected_equity_units` | 100 USDT | 200 USDT |
| `per_trade_cap_units` | 19.10 USDT | 38.20 USDT |
| `cost_reserve_units` | 0.10 USDT | 0.20 USDT |
| `trade_after` | Oct 26 06:00Z | Oct 29 14:00Z |
| `new_risk_end` | Oct 26 23:00Z | Nov 9 21:00Z |
| `flatten_start` | Oct 27 00:00Z | Nov 10 19:00Z |
| `signing_end` | Oct 27 04:00Z | Nov 11 14:45Z |
| `activation_self_check` | absent | 32 USDT SKHYB, Oct 27–28, same run as scored trading |

Every other non-provenance profile field matches: S1 block, equal fifth weights, 20 bp slippage, discretionary
attempt cap, evidence/falsifier authority, gas-excluded stock capital and recovery gas/reserve. Routing is the
same `9b86c732…`; both use five assessment workers and pinned session history. With 170 USDT cash and the 0.20
reserve, FS1's nominal high target is 32.262 USDT/name before fills/costs. The S5 81.37 USDT cash shortfall does
not propagate into the fresh FINAL wallet. All four existing FS1 profile files and the routing file remain unchanged.

### PR296-RV01 compatibility correction after the first full run

The first pinned Python3.12.15/PG14.24 full run completed: 2958 passed, 8 skipped, 4069 subtests passed,
4 failed (504.08 s). Two review regressions were corrected: the startup restriction now applies only to
history-required FS1/S5 profiles, preserving the pre-existing LV-01 equal-weight deterministic path, and the
FINAL run sheet again explains generic `--allowance-recovery`. Two worker-isolation failures required Docker
namespace permissions for nested bubblewrap; they do not concern FS1 decisions or numeric assembly. Final
validation below supersedes this intermediate run; no single green full-suite result is claimed from it.

### PR296-RV01 final results (2026-10-26)

**PASS, local synthetic source validation.** Final full run on Python 3.12.15 / PostgreSQL 14.24:
**2962 passed, 8 skipped, 4069 subtests passed, 0 failures**, 492.96 s. Nested bubblewrap ran with container-local
SYS_ADMIN, unconfined seccomp and unmasked system paths; a direct diagnostic established that Docker's masked
`/proc` caused the earlier worker failures. No production worker code was changed. Network was isolated in the
disposable database's namespace, with no external credentials supplied. The database/container were removed.

| Criterion | Evidence |
|---|---|
| RV1 | Both direct deterministic FS1/S5 startup regressions pass; existing LV-01 equal-weight and scoped historical deterministic rehearsals pass. |
| RV2 | Actual S5 and FINAL shell steps execute against synthetic service stubs: P4 initializes/activates without planning, active/transitioning states refuse initialization, P6 refuses missing/restarting execution and starts runtime only after a healthy executor. Shell syntax passes. |
| RV3 | Standalone CLI and API prepare fresh FINAL inputs and wallet-specific ownership directories. Wrong wallet/database, missing history/adoption and substituting the S5 profile refuse. Package scope/input checks pass with exact unchanged profile/routing bytes. |
| RV4 | Fresh FINAL numeric coverage is COVERED and the real signer assembler succeeds without a previous run; mismatched holdings and stale quotes refuse. Clean runtime builds five RoutedAssessors and SessionHistory. Real PostgreSQL self-check BUY → restart → SELL → DONE, all-five construction across restarts, exact replay and allowance-recovery flatten tests pass. |
| RV5 | Exactly ten non-provenance differences recorded above; all six existing FS1/S5 profile/routing file hashes unchanged. Full suite green as reported. |

Eight explicit skips: two external/private source/response fixtures; one directory-mode test because root ignores
permissions; five real-systemd tests because that runner was not enabled. No hosted systemd/host or live-provider
qualification is claimed. The final source/test files all predate the full run's startup and are pinned by hashes
in [the receipt](../build/evidence/pr296-review-20261026.json).

PR296 was refreshed after verification: still OPEN at the reviewed head `f89ec873…`, base `81ee30a1…`.
No workflow runs existed for that head at the API check. Fixes remain **local and uncommitted** on
`codex/pr296-fs1-standalone-review-20261026`; nothing was pushed, merged, posted, installed or run live. The unrelated
untracked `.idea/` and Conda requirements file were preserved. This is not a completed Git handoff.

Remaining owners: Keith supplies actual qualified history and the S5 sizing/no-trade decision; Keith/Keegan accept
final profile/model decisions and reconcile the shared account budget; Isaac accepts exact final signer/gas/caps;
Yao supplies final-wallet captures/quotes, exact bundle/database/release binding and host qualification. The
existing TH-01, GAP-73/74/75, IDEA-093, IDEA-098 and IDEA-104 backlog entries retain those live gates. No S5 run is
a prerequisite of the new standalone FS1 source path.

### PR296-RV01 publication authorization (2026-10-26)

User requested "push to the latest PR" after reviewing the local result. PR296 remains the latest PR, OPEN at
`f89ec87389d0e20b5725e1a4c67961d602db5704`; the fetched canonical base remains `81ee30a1…`.
Commit the verified source/tests/docs and push by ordinary fast-forward to
`claude/s5-r3-fs1-models-20261026`. Preserve unrelated untracked files. No merge, host installation or live execution
is requested. The source hashes and prior test results in the receipt are unchanged; only publication metadata
and current-status wording changed after validation.

## S5-SIZE01 — cash-funded rehearsal opening lots (2026-10-26; criteria before implementation/execution)

User request: "ok resolve the sizing mismatch" after the S5 evaluation. No funding transfer, BNB inclusion,
FS1 change, merge or installation is requested. This work prepares a reviewable local change; publication of
the new decision code requires permission before execution (AGENTS.md and SKILL.md §0.3).

The 18.637420 USDT entry minimum is derived from measured costs and stays unchanged. S5 alone opts into
`s5_entry_lot_units=19000000`. At the high exposure level, each target is the larger of its ordinary equal-fifth
target and 19 USDT, provided the lot fits the existing 30% allocation-weight cap times the high level, the hard
name line and gas-excluded stock capital. At lower exposure levels the ordinary targets apply. This is a
rehearsal sizing exception, not an exact equal-weight portfolio: the existing deterministic planner chooses
among all five names, with total stock exposure/cash/gas and exact quote costs still limiting fills. At recorded
cash 81.373047, stock capital after the 0.10 reserve is 81.273047 and its 95% ceiling is 77.209394 USDT;
four 19 USDT lots fit, five do not. Existing 19.10 USDT per-trade cap and 0.10 cost reserve stay unchanged.
Targets for held names retain the same floor at the high level so a filled opening lot cannot immediately
produce a sell back to the unfundable equal-fifth target. Trend/limiter reductions and all mandatory sales retain
priority. No performance/P&L input is used to choose the lot.

Acceptance criteria:
- SZ1: validate/rebuild S5 with exactly one additional non-provenance difference from R3: the 19 USDT lot.
  FS1's four profiles, S4 and model routing retain their exact bytes; other profiles reject the opt-in.
- SZ2: on the recorded cash/BNB balances, policy and independent planner admit a 19 USDT opening BUY with
  executable synthetic quotes. Settle four serialized buys, preserving policy state across reconstruction;
  there is no immediate discretionary sell-back and no fifth BUY beyond the 95% stock-capital ceiling.
- SZ3: BNB price/balance changes cannot enlarge the stock target. Insufficient stock capital, bad quote costs,
  lower trend/limiter levels, loss/health halts and the terminal window cannot be bypassed by the lot.
  A forged oversized policy target is independently clamped to the bounded lot/ordinary name cap.
- SZ4: M4 replaces the stale 98.32-USDT constant with a check derived from the exact selected profile and fresh
  flat-book cash. Profile/probe pins and run-7 instructions agree; history and model gates remain required.
- SZ5: run focused sizing/policy/planner/preparation/shell regressions and the full pinned offline suite after
  the changed code has been committed and pushed. Record actual results, skips and limitations; no live claim.

Implementation prepared locally: `s5_entry_lot_units`, bounded policy/planner targets, aggregate opening-capacity
selection (largest gap then symbol, independent of BNB valuation), fresh-cash preparation check and regression
tests. Profile `6dadc1961a54374f51415e2168ff8d4a917b28f90e58c9493a1b9fbd8731e80d`, digest
`d80045d446af6297e5e0c5df2f1aeb6f0467e4a402728a1a222361b8b2ae4248`, probe
`68e49922432f8a8e8081fbaa32b3d8bb3b5614a5ca2982b6ed5ee671262f8e17`. Exactly one new
non-provenance profile key versus R3. Static syntax/pin/diff checks pass; FS1/S4/routing bytes match HEAD.
The changed production code has not been executed: permission to commit/push and then run SZ1–SZ5 is pending.
The original R3 no-entry result and prior full-suite receipt remain historical evidence, not validation of this change.

Publication authorization (2026-10-26): user answered "yes" to committing/pushing this prepared S5 change to
PR296 and running focused/full offline validation. Ordinary fast-forward publication only; no merge or installation.

First focused run after publication (`338beeb7`, native Python 3.12.14): 109 passed, 39 subtests passed,
one new serial-settlement test failed. Its legacy four-decimal token fixture rounded a 19-USDT minimum output
by whole cents, exceeding the unchanged cost reserve with measured gas. The test now uses production-style
18-decimal token quantities; no cost gate or decision code was loosened. Rerun follows publication of this correction.

### S5-SIZE01 final validation (2026-10-26)

**Supported offline.** Source `2f9e886c25b4ceba0eb35bd23dd5543952d23865` was committed/pushed before execution.
Native Python 3.12.14 focused run: **110 passed, 39 subtests passed, zero failures/skips** (9.47 s).
Full Linux/aarch64 run on Python **3.12.15** and PostgreSQL **14.24**: **2978 passed, 8 skipped, 4069 subtests
passed, zero failures** (677.99 s). The eight skips are two external/private fixtures, one root-permission test and
five opt-in systemd tests. Receipt: [S5-SIZE01](../build/evidence/s5-size01-review-20261026.json).

| Criterion | Result |
|---|---|
| SZ1 | PASS: committed profile rebuilds byte for byte; only new non-provenance key versus R3 is `s5_entry_lot_units`. Existing FS1/S4 profiles and routing retain their exact bytes; other scopes/bad values refuse. |
| SZ2 | PASS: four serialized 19-USDT synthetic BUYs with policy reconstruction fit the recorded cash; filled names do not immediately sell back; no fifth BUY/quote is planned. These are synthetic finalized settlements, not real fills. |
| SZ3 | PASS: BNB changes, including zero marked BNB, do not change cash targets or invalidate aggregate proposal weights; bad costs, insufficient cash, lower levels, loss/health gates and mandatory terminal sales retain their checks. Forged overweight policy input is independently bounded. |
| SZ4 | PASS: M4 uses the profile-derived fresh-cash check, which reports four possible opening lots at recorded cash; profile/probe pins and shell tests agree. Routing and history remain required. |
| SZ5 | PASS: focused and full pinned offline runs above; final receipt pins every changed source/test/script hash. |

The runner had external networking disabled and shared only the disposable PostgreSQL namespace; the repository
`.env` was hidden. Nested bubblewrap tests used container-local SYS_ADMIN with unconfined seccomp/system paths,
as in PR296-RV01. The runner and database were removed. No production credentials, provider/model calls, wallet
operations, host install or merge were performed.

GitHub run `40287198787` did not start jobs: its runtime annotation says recent account payments failed or the
spending limit needs increasing. Hosted CI is **unavailable**, not a tested code failure. Real TH-01 history,
fresh hosted inputs and exact profile/probe/signer/release acceptance, host qualification and installation remain
with the existing owners. The cash sizing implementation is complete; no funding transfer or FS1 change is needed.

## S5-DEPLOY01 — authorized run-7 deployment (2026-10-26 SGT)

User request: "ok can merge and lets deploy s5" after TH-CONFIG01. PR298 merged at `c997df2c`.
Selected build: canonical `c997df2c19cf1c0d17b18b83b5bb0d38015879fc`; S5-SIZE01 profile `6dadc196…`,
probe `68e49922…`, history input `5e572570…`, routing `9b86c732…`. Use the existing S5 sheet and its
local-bundle route, as requested in the S2 comparison; record actual source/checks without claiming hosted CI.
The user authorizes operator deployment of this selected S5 scope; do not attribute any new statement to Isaac
or Keegan. No profile/window changes, funding transfers, manual wallet transactions or FINAL activation.

Before execution, acceptance: preserve run6 history/accounting and verify current state before retirement;
new run `larp-dev-rehearsal-20261026-s5` / DB `larp_rehearsal7`; local bundle integrity/reference comparison;
fresh M3 numeric COVERED/chain reconciliation and exact signer identity-only difference; explicit selected
history/routing/profile pins and valid model-budget/credential-name checks; both-role preflight and signer-key
match; initialize before signer/execution/runtime (P4/S2/P5/P6); verify active units, five-token history/status,
reason summaries and trace delivery. Record live J checks honestly, with no inferred fill or profitability PASS.
Readiness flags remain tied to actual results. Keep signer provisioning temporary and remove uploaded config
packages after installation. Stop at an actual refusal and preserve its evidence; do not bypass safety checks.

Initial AWS identity check refused because the `larp` login expired. User asked to run `aws login --profile larp`;
local preparation continues while authentication is pending. No host change has occurred at this point.

### S5-DEPLOY01 preparation / authorization binding

User subsequently confirmed login and "full permission to complete deployment including using my terminal".
AWS authentication works. Initial read-only run6 checks: all four primary services active/zero restarts,
archive healthy (19 anchors/four backups ACK), no quarantine, all five stock positions zero, cash81.373047USDT,
BNB0.024973109594021811. Both runtime model credential names are populated (values not printed).

M1-local PASS: canonical `c997df2c…`, bundle SHA-256
`590280b653b8946ec4ee57bfc133f143e3e652c2198a8453fb1c9b7f4b9bc218`, manifest
`f842043ebee74dfe01a1983ad4ff50e7052a5793c7eafa0e204a81e9ac308fa8`;
file comparison against original CI RC4 passed, pinned Python3.12.15/CA/provisioner unchanged.
D1 PASS: new empty `larp_rehearsal7`,21 tables,13 matching migrations, all five roles/connect and privilege checks.
M2 PASS: verified bundle uploaded (98,468,977bytes, SSE-KMS).

M3 `20261026T114558Z`:98 checks, numeric COVERED, no missing coverage. Signer
`1b2bca7f7f9ce8694c016c05e48f61dde438e0b90b36dea03cbf8bbcc4d90559`
differs from run6 `1e052e26…` only in build/run/database identity; signing policy and enabled recovery identical.
M4 PASS before retirement: package `package-20261026T114801Z`, all seven local qualification checks PASS,
bound shared manifest `1a57fa73bc7872bd6ef9df9fba841df2b7c869453c8fdcb96c946fa5d4333d00`,
history/profile/routing pins exact, local signer `check` PASS. Fresh stock capital81.273047USDT supports four
19-USDT lots. Preparation readiness flags retain their scoped false values pending actual host acceptance.

Yao's direct deployment authorization above applies to this selected S5 scope and the reviewed identity-only
signer candidate; it is the operator review reference for activation. No new approval statement is attributed
to Isaac/Keegan. The prior approved signing policy/caps are unchanged; no policy refusal is overridden.
B1 read-only PASS: existing account `larp-openai-2026`,50,000,000microUSD total,3,217,536microUSD charges retained.
No ledger reset/init or private invoice reconciliation is claimed. Private results are under
`deploy/activation/rehearsal-install-s5-20261026/` in the original checkout.

### S5-DEPLOY01 startup refusal / preserving transition criteria

P3, P4, signer provisioning/check/routes/S1b/key-match/S2 and execution P5 passed. P6 refused with START_REFUSED;
runtime is stopped, so no new planning/trade was made. Actual read-only diagnosis: the budget's base pacing
matches FS1 exactly, but its trial binding remains `larp-unsigned-v3-20261018`, expired end_ms1792627200000.
Trial stopped=false/reason empty; global account latch=false/reason empty. Historical104 SETTLED/2,880,356microUSD
and three UNKNOWN/337,180microUSD remain. This is the preserving-migration gap previously recorded in IDEA-066.

Before implementing/running a migration: require exact expected ledger/routing hashes, existing private file,
no live trial/model workers, an expired trial, no RESERVED charges, no trial/global safety stop or clock rollback,
unchanged account/total/reserve/initial charge and identical base pacing. Refuse any mismatch atomically.
Make an exact private pre-migration backup, archive rather than discard trial policy/dispatch attribution, preserve
every charge/state/amount/request identity, account/switch/clock row, and record source/target hashes. Only retire
the expired trial binding for the explicitly selected non-trial S5 routing. Old trial-aware workers must refuse
afterward; current ModelBudget must load without replenishing spent credit or clearing UNKNOWN.
Code/tests must be committed/pushed before execution. Verify negative cases and atomic preservation against
synthetic ledgers, plus existing budget/trial/routing checks, before applying to the stopped host runtime.
No runtime release/profile/routing bytes are changed by this administrative transition.

Transition verification:84 tests/288 subtests PASS offline (migration preservation/refusals plus existing
trial caps, assessment budget and routing). The operation requires an expired unlatched trial and no reserved
requests, rejects changed pacing/account/hash/attribution or safety/clock stops, saves the exact original bytes,
retains all trial rows under archived table names, and preserves every charge/switch/account/clock field.
The deployed release remains byte-identical to `c997df2c`; only an explicitly versioned administrative helper
will perform this configuration-state transition. Host wrapper must refuse any other runtime-user process.

## S5-OBS01 — run 7 makes no entries while the trend guard is DOWN (2026-10-26, live observation)

Read-only observation, not an experiment: no code, profile, host or wallet change. Sources: the team's SSM
`primary-status`/`trading-status`/`signer-status` outputs of 12:10–12:17Z (read back with `ssm:GetCommandInvocation`)
and read-only Session Manager queries run by the user (in a Claude session) on the primary between about 12:40Z and 13:00Z
(`SET TRANSACTION READ ONLY`, as `larp-execution`). Code citations are to the deployed build `c997df2c`.

Observed state of `larp-dev-rehearsal-20261026-s5` (mode `dev`, build `c997df2c`):
- `larp-execution` active since 11:58:16Z, `larp-runtime` since 12:09:02Z, both `NRestarts=0`; evidence/uploader
  active; run not quarantined; archive health `healthy: true`. The journal holds only start-up JSON lines.
- 205 rounds planned and closed by about 13:00Z, all `safety:` ticks about every 13 s; last decision 9 s before the
  query. Event kinds: only VERSION_REGISTERED, RUN_ACTIVATED, BALANCE_CHECKED, ROUND_PLANNED, ROUND_CLOSED (no model
  assessment events). Jobs: five `evidence` jobs, all `EXPIRED`.
- 0 intents, 0 planner rejections, 0 execution records, 0 signing requests, 0 signatures, router allowances 0.
- Every policy target in the last 40 rounds: `KEEP_QUANTITY / LOW_TURNOVER_HOLD` for all five names.
- Policy state: `s1.trend_state` **DOWN** (`trend_evaluated_session` 203), limiter `NORMAL`.
- Markets: all five `basis_verified`, `token_open` and `underlying_open` true; measured round trip 2–9 bp.
- Signer at 12:10Z: `larp-signer` active, `signing_enabled: true`, `swap_decoder: "UNTRUSTED"` (DEV-23). SSM shows
  the signer `ConnectionLost` since 12:10Z; its health after that was not checked.

**Cause (from code; consistent with every observation above).** With trend DOWN the S1 level is
min(mid 60%, limiter high 95%) = 60% (`s1.level_fraction`). Each name's target is 60% × 1/5 × stock capital
81.273047 ≈ **9.75 USDT**, below `minimum_trade_units` **18.637420 USDT**. So the gap never reaches one step,
and the policy emits `LOW_TURNOVER_HOLD` (a hold, not a rejection; `policy.py` S1 branch). The S5-SIZE01 lot
does not apply: `rehearsal_sizing.name_target` returns the ordinary target unless the level is the high level,
as S5-SIZE01 specified ("At lower exposure levels the ordinary targets apply"). The S5-SIZE01 cash check
(`opening_cash_check`) and SZ2 tested the high level only. So **S5 cannot enter at the mid or low level on
this wallet.** The trend signal is the five-name equal-weight basket's last close over its 5-session mean, minus
one; below −100 bp is DOWN (`s1.evaluate_trend`). The two `S1_LEVEL_CHANGE` reasons seen at 12:17Z are probably
the switch from `trend_start_state` UP to the evaluated DOWN [inference; not traced].

Not the cause: market data/basis, quote cost, `trade_after` (06:00Z; KIT_OPEN_STATE hours), `assessment_required`
(false in S5) and `minimum_remaining_sessions` (0). The expired evidence jobs are Friday Oct 23's
`S1_SESSION_CLOSE` reviews (due 20:15Z, valid to Sat 20:15Z, `missed='expire'`): the run started on Monday, after
their validity. That is a start-time effect, not a weekend rule. In a continuous run, Friday's review runs on
Friday evening and covers the weekend (IDEA-093 "Weekend attempts").

Consequence for run 7: the trend is re-evaluated after Monday's close, at about **20:15Z** (04:15 SGT). If it turns
UP, 19-USDT lots are possible until `new_risk_end` 23:00Z, before the 00:00Z flatten. If it stays DOWN, run 7
makes no trade and does not exercise the post-approve swap or sell that S5 was meant to test. No profile or
window change is proposed here; any change needs a new profile hash and the existing owners' approval.

FS1 implication [our arithmetic, not run]: at 170 USDT cash (GAP-73) and a 0.20 reserve, the FINAL mid-level
target is 0.6 × 1/5 × 169.8 ≈ 20.38 USDT. That is above the 18.637 USDT minimum, so FS1 can still enter in a
downtrend, by about 1.7 USDT before costs. Lower funding (fees, the self-check) narrows that margin. At the
limiter `SEVERE` level (30%) the target is about 10.19 USDT, so FS1 makes no new entries there.

S5-OBS01 outcome (team's read-only checks, 2026-10-27 02:51Z): the trend was re-evaluated for session 204 and
stayed **DOWN**; at 02:39Z run 7 still had 0 execution records/signatures. Run 7 made no trade before
`new_risk_end` and did not exercise the swap/sell path. Correction to S5-OBS01: the signer's SSM `ConnectionLost` is expected. The run sheet checks the
signer once (C1, the 12:10Z check), then removes signer SSM access (T2).

## S5-OBS02 — database stalls crash-loop run 7's services; first daily backup over its bound (2026-10-27, live observation)

Read-only diagnosis, requested by the user: `journalctl`/`systemctl` and read-only database connections on the
primary over SSM at 03:56–03:58Z (Claude session), plus the outputs of the team's read-only SSM checks of
02:39–02:57Z. No host, run, profile or wallet change. Run 7 ran build `c997df2c`, which includes PR280
(`Backup.v2`, IDEA-094/095) and IDEA-100 DB5. IDEA-109 fixes 1 and 2 (PR #303) are not in that build.

Observed:
- **Two crash bursts.** Runtime, execution and uploader exited `status=1` together at **23:32–23:59Z**
  (runtime 62, execution 33, uploader 58 restarts) and again from **03:41Z**. At 03:57:49Z the runtime was
  crash-looping at 80 restarts, with execution at 36 and uploader at 60. `larp-evidence` had 0 restarts.
  Every exit logs only the fixed `RUNTIME_FAILED`/`EXECUTION_FAILED`/`UPLOADER_FAILED` line; exception text is
  withheld by design (`larp/runtime/service.py`, broad `except Exception`). No OOM kill or timeout marker;
  host memory 1,909 MB total, 1,106 MB available, no swap (03:56Z).
- **The database accepts TCP but not logins.** At 03:57:28/38/49Z the database port connected in 0.0 s, but each
  login failed with `Unavailable` caused by psycopg `ConnectionTimeout` after 5.34 s (`connect_timeout=5`,
  `larp/storage/postgres.py`), 3 of 3. That means a reachable but starved server: the DB-01 failure mode of 2026-10-25.
- **Size at 02:56Z** (12:09Z start + 14.8 h): database 687,517,019 bytes; `events` 7,437 rows /
  1,044,522,587 raw bytes (largest 4,906,883); `audit_events` 3,709 rows / 512,349,747 raw bytes (largest
  4,895,047). That is about 71 MB of raw `events` per hour, about **1.7 GB per day**, from hold-only safety rounds
  every ~13 s. `pg_stat_statements` is not installed (IDEA-100 DB2 not applied).
- **First daily backup refused.** Archive health `healthy: false`, `backup_failure` `BackupOverBound` for the
  00:00Z and 00:05:35Z slots, `PERMANENT` 2, `ACK` 18; no durable backup since. The run database was new and
  single-run (S5-DEPLOY01 D1), so this is the first segment of a fresh chain, about 12 h into the run.
- Each runtime restart consumed about 1 minute of CPU before exiting.

**Cause (high confidence that it is the database; the starved resource is not yet confirmed).** The 1 GB
`db.t4g.micro` instance cannot serve this journal volume: every database client fails together, and the
server stops completing logins. CPU-credit exhaustion versus memory pressure is unconfirmed:
this session's AWS identity cannot read CloudWatch or RDS. Owner check: RDS Monitoring for 22:30–04:00Z
(`CPUCreditBalance`, `CPUUtilization`, `FreeableMemory`, `DatabaseConnections`, latency) and RDS events.
Likely amplifier [inference, not measured]: ARCH-01 item (1). Each automatic restart re-verifies the whole journal
before deciding, so a crash loop adds reads to a starved database.

**Consequences.**
- Run 7: no trade affected (flat book, no orders), but rounds stopped during each outage; those gaps may be
  published as diagnostics (F-51).
- **ARCH-01's 2026-10-25 trigger (b) is met:** health reported a `BackupOverBound` refusal on a build with the
  PR280 fix. By that pre-registered rule, ARCH-01 (per-event payload) must be implemented before final activation;
  Keegan decides.
- ARCH-01's growth projection is falsified: it put the 64 MiB daily-segment bound around day 11, but run 7 passed
  it on its first segment.
- **FS1 is exposed:** the same instance and the same round cadence would reach this state within its first day of
  the 14-day run. During a stall FS1 cannot plan, log, sell or flatten. Automatic restarts help only after the
  database answers again.
- IDEA-109 S-06/S-07 (DB1/DB2/DB5 applied, RDS reboot, maintenance/backup windows away from 00:00Z, optional
  larger instance) are now required, not optional, before P4.

No fix is implemented here. Options for the owners (Keegan, Yao; Keith for evidence-state content), each needing
its own criteria before code (AGENTS.md): (1) slim per-event payloads (ARCH-01 / DB-01 R5); (2) a larger
instance class or memory (IDEA-109 S-07); (3) apply DB1/DB2 so the next stall names its queries;
(4) re-size the backup bound or the first-segment strategy for a run of this volume; (5) restart pacing so
crash loops do not repeat full verification.

## S5-OBS03 — run 8's first BUY aborts on RFQ expiry after the approve; the zero-amount revoke is rejected (2026-10-27, live observation)

Read-only evidence from the run-7/8 monitoring session (SSM reads of API artifacts, execution records and events on
the primary; public BNB Chain RPC reads of the receipt, allowance and nonce). No host, run, profile or wallet change
by that session apart from the manual runtime stop below. Full timeline and read-only methods:
[handoff](../build/S5_RUN8_FS1_HANDOFF_20261027.md). Run 8 = `larp-dev-rehearsal-20261027-s5-small`, build
`bdd515f8` (S5-SMALL01, includes IDEA-109 PR #303), dev wallet `0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479`.

Observed (UTC):
- 05:01: run 8 starts; trend UP, limiter NORMAL, targets about 15.44 USDT/name (SMALL01 proportional targets work).
- 05:03:47: `aggregator/approve-transaction` ok, `approveAmount` `15441878000000000000`, vendor LiquidMesh.
- 05:04:12: approve confirmed, nonce 38, tx `0x5e67cc065517f252d4cbe97c7b00b0d514e5f65a06edfd2bb19b482597403b74`,
  USDT → `approve(0xb44446b0c8e56988c34f7ff73ae904982b5fdda5, 15.441878)`, status 1.
- 05:04:31, 05:04:39: `pre-transaction/gas-limit` code 40435, `execution reverted … RFQ_OrderExpired`. No swap sent;
  record `0e22df21…` ABORTED.
- 05:04:50, 05:04:58, 05:05:05: the allowance clean-up's `approve-transaction` with `approveAmount: "0"` is rejected,
  code 40001, "invalid approveAmount, must be a positive integer string" (`larp/execution_live/venue.py` `revoke`).
- From 05:05: `DIRTY_ROUTER_ALLOWANCE` (LOW) every ~2 min. Records `e639da05…` and `e813dcea…` got approve payloads
  (05:06–05:12) but were never signed (`signing_requests` = 1 in total) and ended ABORTED. Last plan
  `EXECUTION_BLOCKED`, gate `WALLET_PENDING`; reason summaries `LEG_ATTEMPT_LIMIT (GOOGLB)`,
  `BUY_RECEIVE_TARGET_REQUOTE (NVDAB)`.
- 05:12: manual `systemctl stop larp-runtime` (`PLANNING_PAUSED`). At ~06:35: book flat, cash 81.3730 USDT,
  BNB 0.024971, **on-chain USDT allowance to the router 15.441878 (open)**, next nonce 39 (one transaction sent).

Findings:
- **OBS03-B1 (defect, high confidence):** the zero-amount revoke cannot work against the live API. FS1's recovery
  profile `b8ba06e2…` (IDEA-098/AL9) and the FS1 flatten (all router allowances 0) depend on it. Fixing it needs a
  signer-policy decision (Isaac) before code (Keegan): another revoke route, or accepting a minimal non-zero
  allowance. Criteria must be written before code (AGENTS.md).
- **OBS03-B2 (defect, high confidence in the effect):** the RFQ order had expired by the gas estimate (about 25 s
  from the approve request to its confirmation; the quote time is not recorded), and the leg aborted instead of
  re-quoting. The cause of the expiry is open (see below). Similar to run 4's S2-F6; likely to hit FS1's first
  entries (Keegan, Keith).

Open, not findings (to be confirmed read-only; methods in the handoff, items 9 and 10):
- Whether a fresh quote was fetched between the approve and the reverted gas estimates. If not, the executor
  estimated gas on the stale pre-approve quote, against the kit order approve → confirm → re-quote → gas estimate
  (F-105); if yes, the fresh RFQ order expired again. This decides the B2 fix.
- Why attempts 2 and 3 were never broadcast. Likely, unconfirmed: the open allowance plus the attempt limit.

Run 8 status: no trade, so SMALL-5's live acceptance (autonomous buy/sell) is not met by run 8 so far. Restart,
clean-up or retirement before the FS1 install is Yao's decision.

### OBS03-B1 fix — zero revoke from an API-anchored approve (2026-10-27; criteria before code)

Authorization: Keith (user) asked for the fix on 2026-10-27. Of the two options in S5-OBS03 (build `approve(router, 0)`
locally, or a 1-wei API approve), this takes a hybrid of the first: the API still names the spender and supplies the
gas fields; only the amount word of its calldata is set to 0. **Isaac's signer-policy acceptance is still required
before this build is used for FS1** (OBS03-B1 owner); the signer policy itself is unchanged by this fix.

Design: `LiveVenue.revoke` requests `aggregator/approve-transaction` with `approveAmount: "1"` (the smallest positive
integer string, which the API accepts) and `vendor: LiquidMesh`. It requires `dexContractAddress` == the intent's
router and the returned `data` == the canonical `approve(router, 1)` bytes (selector `0x095ea7b3`, zero-padded
spender, amount word 1), case-insensitive. It returns a payload to the token with value 0 and the same bytes with the
amount word 0. The 1-unit approval is never signed or broadcast. The executor's existing exact-payload gas estimate
(`pre-transaction/gas-limit` on the zero payload, max with the API gas × 1.2) and `validate_payload` /
`SigningPolicy` (amount must be 0) are unchanged.

Pass criteria:
- B1-1: the revoke request sends `approveAmount: "1"`, never `"0"`; the returned payload's calldata is
  `approve(router, 0)` to the token with value 0, nonce and API gas fields carried through.
- B1-2: blocked with no payload when the API spender differs from the router, when the API data is not exactly
  canonical `approve(router, 1)` (other selector, spender, amount, padding or length), or for a non-eligible token.
- B1-3: the produced payload passes `validate_payload` for the `REVOKE:` step and the signer's `SigningPolicy`; a
  payload with a non-zero amount is still refused by both.
- B1-4: the existing allowance-recovery suite (`tests/execution/test_allowance_recovery.py`) passes with the
  1-unit request; full pinned suite passes with exact counts; no other module changes.
- B1-5 (live, not claimed by this change): the next run that needs a clean-up confirms an on-chain allowance of 0.

### OBS03-B1 results (2026-10-27, offline)

Criteria `ef28c2e1`, fix `b59f59c6` (`larp/execution_live/venue.py` only), test follow-up `4a43ddfa`. The new test
fails on the old builder (it sent `"0"`) and passes on the fix.
- B1-1 PASS: request is exactly `{binanceChainId: 56, tokenContractAddress, approveAmount: "1", vendor: LiquidMesh}`;
  the payload is `approve(router, 0)` to the token, value 0, nonce and the API's gas fields carried through (checked
  with values distinct from the fixture defaults), for USDT and all five bStocks. The next exact-payload
  `pre-transaction/gas-limit` request carries the zeroed bytes.
- B1-2 PASS: wrong spender, zero/amount-2 data, extra or missing byte, other selector, non-zero padding, other spender,
  `None` and integer data are all blocked; native BNB is refused before any request.
- B1-3 PASS: the produced payload passes `validate_payload` (`REVOKE:` step) and `SigningPolicy.check`; the existing
  boundary test still refuses a non-zero amount at both.
- B1-4 PASS: `tests/execution/test_allowance_recovery.py` 13 passed / 32 subtests with PostgreSQL (on `4a43ddfa`).
  Full suite on `b59f59c6` (Python 3.12.3, pinned `postgres:14.24-bookworm` image): **3055 passed, 8 skipped,
  4123 subtests, 0 failed** (baseline `7511e7ba`: 3055/8/4114). On `4a43ddfa`: offline demo, Docker build and
  `--network none --read-only --cap-drop ALL` run (proxy CA mounted for `pip` only), host-bundle build and Terraform
  `fmt -check` pass. Not run in this sandbox: Terraform init/validate/test, `test_host_bundle.sh` (registry and
  Amazon Linux mirrors blocked) and the R13 systemd test.
- A subagent review (read-only) found no code defect. Its test nits are fixed in `4a43ddfa`. One audit note: the
  recorded `approve-transaction` artifact shows `approveAmount=1` and amount-1 calldata, while the signed clean-up
  is amount 0. No code compares the two.
- Still open: Isaac's policy acceptance, Keegan's review and merge, the FS1 release built from a commit containing
  the fix, and B1-5 (live 0 allowance).

### S5-NEXT01 — next rehearsal preparation (2026-10-27)

Keegan requested a new run with the fixes integrated, relayed Isaac's acceptance of PR310's API-anchored zero
calldata, and selected new SGT times: buy cutoff Oct27 22:00, flatten Oct27 23:00, signing end Oct28 00:00.
Retain the development wallet and S5-SMALL01 strategy/risk/model/gas limits. This is not a FINAL activation.
PR310 is merged at `05b7aa6d`; independent focused validation: 11 tests / 32 subtests pass, 2 PostgreSQL cases
skipped locally (the PR separately records its PostgreSQL results). Deployment has not occurred.

Fresh primary read-only SSM evidence, command `f3b6d83e-34e2-4fdf-9c6d-4355a1f23851`:
- Build `bdd515f8`, dev run8, not quarantined, all five stock balances zero; cash 81.373047 USDT,
  BNB 0.024970602989216991. USDT router allowance remains 15.441878; other five allowances zero.
- All three execution records are terminal ABORTED. The first has one FINAL_SUCCESS approval; the other two
  have no attempts. Each consumed three prepare probes. Nine reservation rows exist; their active/released
  disposition is not established by a row count.
- Crucially, fresh quote calls DID occur after the approval: 05:04:26.172/.522 before gas failure at
  05:04:31.042, and 05:04:34.158/.508 before gas failure at 05:04:39.072 (UTC). Thus missing post-approval
  re-quoting is disproved. The upstream RFQ still failed within seconds; provider route validity is unresolved.

Pre-implementation criteria for the narrow retry correction (NEXT01-R1):
1. A sanitized DependencyUnavailable during post-approval quote/gas preparation retains the original active
   intent for a fresh next probe instead of immediately initiating allowance cleanup. No new signature or send.
2. Original prepare-probe budget, expiry, authority, nonce and gas bounds remain. Exhaustion/expiry still enters
   existing zero-only cleanup; hard Blocked validation failures still abort immediately.
3. A retry that succeeds may finish the original swap; repeated dependency failures never create unbounded work.
4. Targeted execution/recovery and service tests pass. This does not prove upstream RFQ success live.
5. Generate and validate a separate next-run S5 profile for the selected times; historical run8/FINAL profiles
   remain intact. Retain exact profile hash and source/release identity before any host installation.

Launch prerequisites: qualify the resulting exact release; clear run8's allowance through registered agent recovery,
reconcile reservations and ledger/chain, preserve run8 history, assemble fresh caps and a new run/database/signer
binding, perform the authorized signer provisioning and host acceptance, then start execution before the planner.
Do not reset terminal records or reuse expired intent authority to clear the allowance.

## S5-SMALL01 — proportional small-wallet rehearsal, Oct27 19:00SGT flatten

User instruction, 2026-10-27 SGT: amend S5 to buy now and sell at19:00, to exercise FS1 on a smaller wallet and shorter timeline. This is a development rehearsal only. FS1 FINAL remains unchanged.

Design, registered before implementation/tests: replace the S5-only19-USDT high-level lot with ordinary FS1 proportional targets at every trend/limiter level. For this smaller wallet only, adopt `s5_entry_cost_cap_bps=200` (2%) instead of FS1's50bp. Recompute the measured entry minimum against the same200bp; the exact quote gate also uses200bp. Keep authorized-minimum output,20bp slippage, measured impact,0.10USDT cost reserve, all risk/model/history/gas/recovery and serial-wallet controls. This deliberately changes rehearsal economics; it is pipeline evidence, not an equivalent after-cost FS1 return experiment. No human-selected instrument or order.

Window (UTC): trade_after2026-10-27T04:00Z (12:00SGT, immediate on deployment); new_risk_end10:00Z (18:00SGT); flatten_start11:00Z (19:00SGT); signing_end15:00Z (23:00SGT). Sell starts at19:00; completion depends on autonomous execution and market availability. Install as fresh run8 on a reconciled flat development wallet to preserve run7's journal and avoid its growing cold-start history.

Prospective pass criteria:
- SMALL-1: live validation accepts the exact200bp opt-in only for gas-excluded S5 REHEARSAL; FINAL/other policies, malformed values and simultaneous19-USDT lot are refused. Historical profiles retain50bp behaviour.
- SMALL-2: builder/profile/probe reproduce; measured minimum is computed from200bp, below the ordinary30%/60% targets at recorded wallet size; all four FS1 files and S4 rebuild byte for byte.
- SMALL-3: flat DOWN60% generates ordinary proportional BUYs; five serial synthetic settlements fit cash/gross limits with no immediate sell-back, including process-state reconstruction. High/low/limiter levels preserve proportional targets; risk halts, market closure, gas, quote-cost/impact and total/name caps remain effective.
- SMALL-4: quotes above200bp or the cost reserve are refused; no opt-in keeps50bp. Buys stop18:00SGT; all holdings become mandatory sells19:00SGT; signing ends23:00SGT.
- SMALL-5: appropriate strategy/risk/preparation/execution/ops checks and pinned full-suite pass with exact counts. Publish code before any host execution; fresh capture/caps/signing policy and registered manifest must bind the new profile. Verify actual history/model/log delivery and report observed autonomous orders honestly.

User-requested diagnosis included in SMALL01: the first BUY quote was valid, then completed history changed the trend from UP95% to DOWN60%. Ordinary targets became9.75USDT/name, below18.637420USDT; the old19USDT floor applied only at95%. No execution request reached the signer. DOWN persisted in sampled states. SMALL-3 explicitly covers UP quote followed by DOWN history and proportional requoting.
Infrastructure before install (user request): apply IDEA-100 DB1/DB2/DB5, applicable pending maintenance, one planned RDS reboot and pg_stat_statements; set maintenance/backup windows outside23:30–01:00UTC and flatten; verify both EC2 CPU-credit alarms and primary memory. Preserve all old journals and shared budget.

SMALL-INFRA prospective acceptance: two notifying EC2 CPU-credit alarms (20credits/15minutes); daily backup16:00–16:30UTC and maintenanceSat16:30–17:00UTC avoid23:30–01:00UTC, S5 sells11:00–15:00UTC and FS1's Tue19:00–Wed14:45UTC flatten. Use db.t4g.small (2GiB) for the memory-constrained database; primary/signing EC2 sizes stay unchanged when inspection shows adequate memory/credits. Pending OS maintenance is applied only after stopping all run7 database clients, with no in-flight transaction. Verify parameter preload, extension and monitoring after recovery. These windows constrain scheduled work and cannot prohibit urgent AWS maintenance.

SMALL01 preliminary verification: focused strategy/risk/execution/FS1 preparation/archive checks862 passed,92 environment skips,1157 subtests; all14 new small-wallet regressions pass, including the valid UP quote -> DOWN history -> correctly resized requote -> BUY. Historical SIZE01 tests retain archived input bytes. New run8 and historical run7 pin/scope/static checks28 pass. Terraform validate and22 mock tests pass. Full pinned suite still running; no claim of host acceptance.

Infrastructure constraint: AWS rejected db.t4g.small with FreeTierRestrictionError (free-plan account). No account-plan upgrade is authorized or attempted; retain db.t4g.micro and complete monitoring/windows/maintenance. Two host-credit alarms and query parameters applied before the resize refusal. Database size increase remains an explicit blocked optional improvement.

### SMALL01 source acceptance (2026-10-27)

Application source includes canonical PR303 (e3105689) via normal merge3869f8e1; no history rewrite. Pinned Linux/Python3.12.15/PostgreSQL14.24 suite on integrated runtime: **3038 passed,11 environment skips,4114 subtests,0 failures**. All3 operating-system sandbox cases pass separately in existing bubblewrap-enabled image. Offline demo passes in that image (base image lacks bubblewrap and cannot run the isolated demo). Final separate tests after two test/setup additions: **23 passed** (15 SMALL01 plus8 run8 sheet checks); recovery-focused PostgreSQL set **73 passed/106subtests**. Terraform validate and22 mock tests pass. The earlier three Git-sensitive failures were container metadata access, corrected by read-only Git metadata mounting; no ignored/private files were made tracked.

SMALL-1..4 PASS offline: exact REHEARSAL scope, minimum3192045 microUSDT, unchanged FS1 hashes, DOWN requote/execution, all5 serial settlements at95/60/30 with reconstructed state, independent200bp rejection boundary, prior50bp refusal, risk/gas/market/integrity gates and18:00/19:00/23:00 window checks. SMALL-5 source verification PASS; fresh host/caps/deployment/order acceptance remains in progress. Source and ops are pushed before execution.

### S5-NEXT01 targeted validation

NEXT01-R1 retains DependencyUnavailable during quote/gas preparation inside the original probe budget;
hard validation failures still enter cleanup. Three regressions cover successful fresh retry, exhausted probes,
and hard failure cleanup. Two retry regressions failed before implementation. Python3.12.14 and disposable pinned
PostgreSQL14.24: execution, signer and existing S5 profile suites **503 passed /1279 subtests /zero skips**.
Next profile file SHA `1dbb52b12b6b8e379a1b3996d427b2ab83b520f98ec6275d29f536600f327e4c`,
StrategyProfile.v1 `b4719c230f41a28883d268fac77fe44bdcad23fb36355dbaec4af23a3536e7af`.
Host readback: both x86_64; signer EC2 running but SSM ConnectionLost since04:59:46UTC. Current AWS identity's
IAM GetInstanceProfile read is AccessDenied. T1 restoration needs the authorized operator's reviewed Terraform
plan/apply. No service, key, signer policy, wallet or hosted run state was changed; local SDK/test dependencies and
disposable PostgreSQL were used. Exact release/systemd/host qualification and run8 cleanup remain prerequisites.

### OBS03-B2-RV01 — read-only RFQ validity measurement (2026-10-27; criteria before code)

Authorization: Keith (user) asked on 2026-10-27 for a read-only collector, built off the integration branch and run
locally with the read-only Web3 key pair. Question: how long a fresh quote's swap calldata stays executable, measured
as actual elapsed time since the quote response, and whether RFQ-routed quotes already fail at the first probe
(upstream order arrives expired) or after a measurable window. LD02c could not answer this (nominal delays only, see
the IDEA-070 correction); run 8 saw `RFQ_OrderExpired` about 5 s after fresh post-approval quotes.

Method: `tools/deploy/rfq_validity_check.py`, run on a workstation, never a host. BUY 15 USDT (run 8's per-name
size) USDT → each of the five bStocks, from the public dev wallet address, `slippagePercent` 0.2 (S5's 20 bp). One
quote at a time. Each quote's exact calldata is simulated with `eth_estimateGas` on the public read RPC
(`BSC_BNBCHAIN_PUBLIC`) with a USDT balance and router-allowance state override (LD02c's slots 1 and 2), immediately
after the response and then at target ages 1, 2, 3, 5, 8, 12, 20 and 30 s. Probing stops after an RFQ failure is seen
twice in a row, or after the 30 s probe. Six rounds over the five symbols (30 quotes, about 15 minutes). The calldata's
32-byte words are also scanned for Unix-second values within ±1 h of the latest block time and reported as offsets,
to look for an encoded RFQ expiry. The simulation is the same chain check the API's `pre-transaction/gas-limit`
performs, but not that endpoint itself.

Tool criteria (offline, before the live run):
- RV-1 read-only: the Web3 client allows only `GET aggregator/quote-and-swap`; the RPC allows only `eth_chainId`,
  `eth_getBlockByNumber`, `eth_call` (USDT `balanceOf`/`allowance` only, with exactly the override) and
  `eth_estimateGas` (from the dev wallet, to the pinned router, value 0, exactly a fresh quote's calldata, exactly the
  override). Every other call is refused before any network access. No signer, private key, submit endpoint, AWS or
  database is loaded.
- RV-2 timing: every probe records its actual start age since the quote response was received (monotonic ms) and
  its target; result keys are never nominal-only.
- RV-3 override proof: before any simulation, `eth_call` with the override must return the overridden balance and
  allowance; otherwise the packet is NOT_RUN with no simulation.
- RV-4 output: the committed packet holds no credentials, RPC URL, wallet or calldata (fingerprints only); the
  sanitizer refuses otherwise. Raw quote responses stay in a private directory outside the checkout.
- RV-5 offline tests cover RV-1..RV-4 and the classification below; they and `tests/execution/test_quote_check.py`
  pass.

Interpretation rules (fixed before the live run):
- A quote is RFQ-failing if any probe returns an `RFQ_*` revert. It "arrived expired" if its first probe (actual age
  ≤ 2 s) returns `RFQ_OrderExpired`. Otherwise its validity is bounded by (last success age, first failure age].
- If every RFQ-failing quote arrived expired: the inner order is unusable as quoted; no client latency reduction can
  fix it, and the remedy is to treat it as a route refusal (re-quote or skip the leg within existing bounds) and raise
  it with the provider. If bounds exist: compare the lower bound with run 8's measured ~5 s from re-quote to gas
  estimate, plus the signer and broadcast path.
- If no quote is RFQ-failing: INCONCLUSIVE for RFQ validity (routing is chosen per quote, IDEA-070 LD09), not a fix.
- Results are observed outcomes for this window and size, not a guaranteed TTL. Non-RFQ reverts are reported
  separately and not counted as RFQ expiry.

Criteria amendment after a 1-round smoke run (2026-10-27 13:13Z, tool `d5871635`, recorded before the full run).
The smoke run proved the override (RV-3) and probed all five symbols. MSFTB's quote was executable at 0.37 s, reverted
at 1.0 s and 2.0 s, and returned `RFQ_OrderExpired` at 3.0 s. Inspecting its raw response locally showed two things the
criteria had not anticipated:
- The quote response does mark the route: `routerResult.dexRouterList[].dexProtocol.dexName` = `Rfq Neptunex`
  (100 %). The tool now records each leg's `dexProtocol` name and percentage and flags `rfq_route` for names starting
  "Rfq". This contradicts the LD02c R1 conclusion (IDEA-070) that nothing in the response marks an RFQ route; that
  collector read only top-level scalar fields of each `dexRouterList` item, not the nested `dexProtocol`.
- The calldata carries a packed (not 32-byte-aligned) 4-byte Unix time 1.55 s after the quote response, twice, next
  to the outer deadline at +499.6 s. The scan now covers every byte offset (4-byte seconds and 6-byte ms values with a
  non-zero leading byte, within ±1 h of block time) and reports offsets from both the block time and the response.
- Non-RFQ revert messages now keep the provider's short `Error(...)` reason (letters, digits, underscore and space;
  60 characters at most), still subject to the public-packet scan.
Interpretation rules are unchanged; an encoded short time is evidence about the order's intended lifetime, while the
probe outcomes remain the measurement.

### OBS03-B2-RV01 results (2026-10-27, live read-only)

Tool `cd7cce73`, run 13:15:51–13:29:54Z from a workstation (`BSC_BNBCHAIN_PUBLIC`, 6 rounds × 5 symbols, BUY
15 USDT). Packet: [rfq-validity-rv01-20261027.json](../build/evidence/rfq-validity-rv01-20261027.json), SHA-256
`ea2884c81bc41a9a472e9ff61f5b1a3999a5a32073deb5b8c9ffd8e2cd2954ec`. No signature, approval, broadcast, host, wallet or
profile change; raw quote responses were kept outside the repo.

- RV-1..RV-5 PASS: 9 offline tests plus `test_quote_check.py` (19 passed, 17 subtests); the override proof held;
  the packet holds no credential, RPC URL, wallet or calldata.
- First probes ran 0.32–0.43 s after the quote response; quote requests took 138–247 ms.
- **Verdict `RFQ_VALIDITY_WINDOW_OBSERVED`.** 3 of 30 quotes were RFQ-routed, all MSFTB, all named `Rfq Neptunex`
  (100 %). Each was executable at its first probe (0.33, 0.35 and 0.33 s), reverted at 1.0 s and 2.0 s (no reason
  string), and returned `RFQ_OrderExpired` at 3.0 s and 5.0 s. Observed validity bounds: (0.33, 1.0] s. None arrived
  expired.
- Each RFQ calldata carried a packed Unix time 1.49–1.61 s after the quote response, which matches the observed
  window: the maker's order is built to live about 1.5 s (time resolution is whole seconds).
- The other 27 quotes (all five symbols, including MSFTB three times through Pancakeswap V3 or Uniswap V3) used AMM
  routes (Tessera V, Metric V2, Pancakeswap V3, Uniswap V3/V4, Elfomofi) and simulated successfully at every probe
  through 30 s. The route name matched the failures exactly: every `Rfq` quote failed and no other did.

Conclusions (observations for owners, not adopted decisions):
- The RFQ order lives about 1.5 s from the quote response. Run 8 needed about 5 s from re-quote to gas estimate, and
  the signed path adds signing and broadcast, so no realistic latency reduction makes an RFQ route usable. NEXT01-R1's
  retry of the whole quote/gas step can only help when the next quote happens to be an AMM route.
- RFQ routes are detectable at quote time from `dexProtocol.dexName`, which corrects IDEA-070 LD02c R1/R4. Treating
  an `Rfq` route as a refused quote (re-quote within the existing probe budget, else skip the leg) would avoid the
  approve-then-expire pattern; refusing it before the approve also avoids the open allowance seen in run 8. That is an
  execution change needing its own criteria and Isaac/Keegan's acceptance.
- Scope: one 14-minute window on a Tuesday (US market hours), one size, BUY only. The maker's lifetime and how often
  RFQ is chosen may differ at other times, sizes or for SELL. This is not a guaranteed TTL.

### OBS03-B2-RQ01 — refuse RFQ-maker quotes in execution (2026-10-27; criteria before code)

Authorization: Keith (user) asked on 2026-10-27 for the change, written for Isaac/Keegan's review. **Not adopted until
Isaac (execution/signer policy) and Keegan (execution owner) accept it**; no host, profile, signer policy or release
changes here.

Design: `LiveVenue._quote` (the execution re-quote used before the approve and again before the swap, including
IDEA-090's tighter second request) inspects every `dexName` under the response's `routerResult`. If any name contains
`rfq` (case-insensitive; covers `Rfq Neptunex` from RV01 and `PcsXRfq` from E-12), it raises
`DependencyUnavailable('fresh quote uses an RFQ maker route')`. That reuses the executor's existing semantics: the
probe is already persisted, nothing is prepared or signed, and the next `prepare` re-quotes inside the original probe
budget and authority (NEXT01-R1). If every remaining quote is RFQ, the existing budget-exhaustion and zero-only cleanup
paths apply unchanged. A response with no `dexName` anywhere is not refused by this check; every other quote check,
the decoder and the pre-sign simulation still apply. Planning quotes (`MarketPort`) are unchanged.

Pass criteria:
- RQ-1 venue: a quote with an `rfq` name in any leg (only leg, partial leg, any letter case, nested anywhere under
  `routerResult`) is refused with `DependencyUnavailable` and leaves no vendor recorded, so `approve` stays refused.
  The same applies when the RFQ route first appears on IDEA-090's tighter second request. AMM names (the seven seen in
  RV01) and responses without names pass as before.
- RQ-2 before the approve: an RFQ quote consumes one prepare probe and produces no attempt, payload or signature; the
  intent stays ACTIVE without `abort_pending`. A following AMM quote prepares the APPROVE normally.
- RQ-3 after the approve: an RFQ quote keeps the confirmed approval and the original intent (no cleanup); a following
  AMM quote completes the swap. RFQ quotes on every remaining probe exhaust the budget and the existing
  `abort_unsigned` clean-up starts; no extra probe or authority is created.
- RQ-4 regression: the venue, re-quote, pre-sign simulation, allowance-recovery and execution suites pass, plus
  the pinned full suite where the local environment allows (exact counts and any environment skips recorded).
- RQ-5 (live, not claimed here): the next rehearsal shows an RFQ quote refused before the approve, or reports that
  none occurred.

### OBS03-B2-RQ02 — request quotes without RFQ (`enableRFQ=false`) (2026-10-27; criteria before the run and code)

Keith asked on 2026-10-27 that the change actually fix the RFQ issue; refusal alone only skips RFQ quotes. The
official Web3 trading-API page (the page EXP-005 cites) documents an optional `quote-and-swap` parameter `enableRFQ`,
"true" by default for bStock pairs, and warns that RFQ calldata may embed a short-deadline settlement. It also lists
`excludeDexes`. Neither is in the kit's parameter table or used anywhere in this repo. Using it keeps the same
endpoint, vendor, local signing and router (F-96, F-104); it changes only which liquidity the aggregator may route to.

Live read-only check (RV02), before any code change: the RV01 collector with `--disable-rfq` sends `enableRFQ=false`
on each probed quote, after an unprobed default quote for the same symbol and size for comparison. 6 rounds × 5
symbols, BUY 15 USDT, same probes and override.
- RV02-1 PASS requires: every `enableRFQ=false` quote is answered and routes through no `rfq`-named DEX; no probe
  returns an `RFQ_*` revert; every quote simulates successfully at every probe through 30 s (non-RFQ failures are
  reported and examined, not counted as RFQ).
- RV02-2 (cost, recorded not gated): for each pair, whether the default quote chose RFQ and the output difference in
  bp `(default − no-RFQ) / default`. A material RFQ price advantage goes to the owners as a trade-off.
- If RV02-1 fails (RFQ still chosen or expiries still seen), the parameter is not effective and only RQ01 applies.

Code criteria if RV02-1 passes:
- RQ-6: execution's `LiveVenue` quote and the planner's `MarketPort.quote` both send `enableRFQ="false"` for bStock
  quotes, so the authorized minimum and the execution re-quote come from the same route family (no repeat of the
  IDEA-090 S2-F6 shortfall). RQ01's refusal stays as the backstop. Gas top-up quotes (`enableRFQ` already defaults to
  false for non-bStock pairs) are unchanged.
- RQ-7: request-binding and replay checks (quote verifier, router replay, caps review) accept the parameter; affected
  suites and the pinned full suite pass with exact counts.
- RQ-8 (live, not claimed here): the next rehearsal shows no RFQ route and no `RFQ_OrderExpired`.

### OBS03-B2-RQ01/RQ02 results (2026-10-27)

**RV02 live read-only** (tool `0a863816`, 13:45:40–14:01:11Z, `BSC_BNBCHAIN_PUBLIC`, 6 rounds × 5 symbols, BUY 15 USDT):
[rfq-validity-rv02-20261027.json](../build/evidence/rfq-validity-rv02-20261027.json), SHA-256
`47430483765c0e7f3c2cffd1fee1fe277c2a6eab71490916fd4b12b7a10d29f0`. Override proof held. The packet's `verdict`
label (`INCONCLUSIVE_NO_RFQ_FAILURE_OBSERVED`) is RV01's wording for "no RFQ failure"; RV02 is judged by RV02-1.
- **RV02-1 PASS.** All 30 `enableRFQ=false` quotes were answered; none routed through an `rfq`-named DEX; all 270
  probes simulated successfully, the last at 30.0 s for every quote. MSFTB routed through Pancakeswap V3 every time.
- **RV02-2 (cost).** The paired default quote chose `Rfq Neptunex` for MSFTB in all 6 rounds (3 of 6 in RV01), and
  its quoted output was 30.6–44.2 bp above the no-RFQ quote. That price was not executable (RV01: expired by 1 s). For
  the other four symbols the default and no-RFQ quotes differed by −2.0 to +1.7 bp, with no RFQ route chosen.
- Observation for owners: MSFTB's executable price is the AMM route's. If its cost against the reference price
  exceeds a profile's entry-cost gate (FS1 50 bp; S5 rehearsal 200 bp), the gate refuses MSFTB entries as designed.
  Not measured against the gate here.

**Code** (`f285b859`, `larp/execution_live/venue.py`, `larp/marketdata/port.py`): execution and planning bStock
quotes send `enableRFQ="false"`; any `rfq`-named route that still appears is refused with `DependencyUnavailable`, and a
quote that fails any check clears the recorded vendor, so `approve` needs a passing quote. Gas top-up quotes unchanged.
- RQ-1..RQ-3, RQ-6 PASS: `tests/execution/test_rfq_route_refusal.py` 10 tests / 9 subtests. The 8 RQ-1..RQ-3 tests
  run against the pre-fix venue gave 11 failures and 2 passes, counting subtests.
- RQ-7: no binding or replay check compares exact parameter sets (quote verifier, router replay, caps review read
  named keys). Execution, marketdata and signer suites with PostgreSQL 14.24: **676 passed, 1 skipped,
  1471 subtests**. Full suite on `f285b859` (macOS, Python 3.12.14, PostgreSQL 14.24): **3096 passed, 10 skipped, 4150 subtests, 1 failed**. The failure, `test_archive_budget.py::test_ar7…`, needs Linux `/proc/self/clear_refs` and fails the same way without this change (3093 passed on the RQ01-only tree). Not run here: the pinned Linux image.
- Not claimed: RQ-5/RQ-8 (live rehearsal), Isaac/Keegan acceptance, and a release built from this commit.

## S5-COST01 — separate cash cushion from discretionary cost admission (proposal)

Yao requested a new review PR on 2026-10-27 after confirming gas is already
funded in BNB. The current `cost_reserve_units` both reduces investable USDT
and caps estimated discretionary costs; setting it to zero currently blocks
all positive-cost entries. PR313 retains the coupled 0.10-USDT setting.

Prospective acceptance, recorded before implementation or test execution:
- COST1: an explicit positive `discretionary_cost_limit_units` separates the
  absolute cost ceiling from the USDT cushion `cost_reserve_units`. Absence
  preserves every historical profile's behavior and bytes. Opt-in is limited
  to the existing S5 proportional/200bp REHEARSAL scope with initial-only gas.
- COST2: a zero cash cushion plus a separately sourced cost ceiling permits
  a below-200bp quote costing more than0.10USDT; the old profile refuses it.
  The independent absolute ceiling,200bp entry bound, impact/slippage,
  available cash and BNB/action/exit-reserve checks still reject unsafe work.
- COST3: cash allocation and per-trade notional calculations use only the
  cash cushion. Mandatory exit/post-cost tightening keeps its current
  cash-buffer semantics. Bad/missing scope, zero/negative/noninteger limits,
  missing LIVE provenance and FINAL opt-in are refused.
- COST4: focused strategy/risk/profile tests pass and the unchanged FS1
  profiles rebuild byte for byte. Publish a review PR without host or
  Terraform changes; no existing profile/package hash is replaced.

Suggested review example only: cash cushion0, separate absolute cost limit
0.40USDT, existing S5 200bp cap. This is not an adopted numeric profile.
The per-trade cap must be reviewed because it currently includes the cash
cushion; changing the cushion changes BUY sizing. The release/package owner
must generate fresh profile/probe/config pins and numeric coverage and obtain
exact acceptance before installation. PR313's already-packaged release does
not gain this feature by merging a later PR. Owners: teammate reviewer for
policy/numeric adoption; package owner for bindings/qualification/install.

### S5-COST01 implementation and verification (2026-10-27)

The implementation adds a positive optional `discretionary_cost_limit_units`
to the scoped initial-only-gas S5 REHEARSAL. Only discretionary economic cost
admission reads it; `cost_reserve_units` retains its capital/sizing and
mandatory post-cost-bound roles. Absence falls back to the historical reserve.
No builder defaults, shipped profiles, PR313 package pins, signer policy, BNB
reserves, host services or Terraform settings were changed. The 0/0.40USDT
values appear only as synthetic review examples, not an adopted profile.

Red evidence before implementation: the initial17 synthetic cases gave
7 failures/10 passes, including the positive-cost zero-cushion refusal and
invalid-limit acceptance. Final21 new cases cover the independent absolute
ceiling,200bp and LIVE per-name impact refusals, initial-gas scope, integer
and provenance validation, sizing independence, gas availability/exit reserve
and mandatory exit invariance (economic IDs correctly change on rebinding).

Final affected suites on Linux/Python3.12.15 with disposable PostgreSQL14.24:
`tests/strategy tests/risk` **588 passed,87 subtests passed,zero skips,zero
failures**. Existing FS1/S5 rebuild/hash checks pass in that suite. Earlier
macOS run before the final4 cases:582 passed,2 PostgreSQL skips,87 subtests.
`git diff --check` passes and `config/` plus existing profile/evidence bytes
are unchanged relative to canonical `fd6b6719`. This is affected-suite
qualification, not a full release/systemd/host or live-trading acceptance.

COST1–COST4 implemented/tested for review. Remaining: teammate policy/value
review and adoption, package owner fresh profile/probe/config pins and numeric
coverage/exact signer acceptance, newly qualified release and host acceptance.
The current deployment and temporary T1 access are unaffected by this PR.

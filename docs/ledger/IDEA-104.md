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

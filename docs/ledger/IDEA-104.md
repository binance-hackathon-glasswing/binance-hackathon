# IDEA-104 — S5: FS1's settings on the dev wallet, selling everything on Monday night (SGT)

- Date / author: 2026-10-26 SGT / Claude Code, asked by the user: "Can you create S5 that is fs1 but it sells all on
  monday night, leave FS1 as our final trading strategy". Owners: Yao (install, run), Isaac (profile/signer
  approval), Keegan (review); Keith (strategy values: unchanged from FS1).
- Status: **open — pre-registered (criteria S5-1..S5-6 committed before any test or code, `8ee6420a`); supported offline
  2026-10-26 (results below). Approval, run sheet and install remain.**
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

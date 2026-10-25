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

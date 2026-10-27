# IDEA-110 — Temporary sub-1-USDT final-wallet self-check (TEMP-SC)

- Date / author: 2026-10-28 SGT (2026-10-27 UTC) / drafted with Claude Code at Keith's request
- Status: open (criteria registered before code; not merged, not installed)
- What: a temporary FINAL profile, separate from FS1, that tests the full pipeline on the final wallet:
  - one buy of under 1 USDT of one bStock;
  - an automatic sell of the whole position;
  - nothing else.
  It reuses the IDEA-093 SC self-check (`larp/strategy/self_check.py`) with its own entry-cost floor. The 1-hour buy window is stamped when the operator prepares the install, not when the code is written.
- Why it matters: F-125 asks for an end-to-end self-check with a real trade on the final wallet before Oct 29. Keith asked for the smallest possible value (relayed 2026-10-28 SGT): "we are trading on out final wallet address and the organisers want us to test our pipeline and ensure it is accurate, thats why the value is lwo". Keith also said FS1 must not be installed for this.
- Decisions (Keith, 2026-10-28 SGT, in chat):
  - **Size:** total stock bought under 1 USDT, one name, one buy, then the normal sell.
  - **Cost:** accept the much higher relative cost of a sub-1-USDT trade on its own cost floor.
  - **Window:** a 1-hour buy window starting when the operator prepares the install.
- Cost / risk:
  - At recorded gas (0.000080 BNB at 722.15 USDT/BNB, about 0.058 USDT per buy), a 0.90 USDT buy costs about 6.4% to enter and about 13% for the round trip. The point is the test, not the return.
  - The run is a separate run and version event on the final wallet before FS1. FS1's later preparation requires a flat wallet (dust included) and no leftover allowance. The S5-OBS03 defect (the live API rejects `approveAmount: "0"`) can leave a USDT allowance behind.
  - FS1's own built-in self-check (about 32 USDT of SKHYB) is unchanged and still runs after FS1 is installed, unless the team removes it separately.
  - This change touches the shared planner and policy. All new paths are gated on the new `policy_id`, so FS1, S5 and the other profiles must behave byte-for-byte as before.
- Links: F-125, F-127, GAP-74, IDEA-093 SC, IDEA-104 S5-OBS03, IDEA-109.

## Design (registered before code)

- **New `policy_id` `larp-final-selfcheck-temp-v1`.** It is FINAL, LIVE and TREND_GUARDED_VOL, built from the reviewed FS1 recovery profile `b8ba06e2…` with only these changes:
  - `policy_id`;
  - `activation_self_check` (stamped window, `pay_units`);
  - the four terminal times;
  - a new key `self_check_entry_cost_cap_bps` = 1000.
  The provenance of every changed value names IDEA-110.
- **Self-check floor.** The self-check's own floor = max over symbols of ceil(gas_value × 10000 / (1000 − spread − min(50, 2 × impact) − fee)). It uses the profile's `gas_sizing_budget_units` and quote summary, the same formula as `validate_live` at 1000bp. At the recorded summary this is 588,951 units (0.589 USDT).
  - It replaces `minimum_trade_units` only for the self-check BUY. `minimum_trade_units` (FS1's 18.64 USDT) is unchanged and still governs everything else.
- **Size bound.** `pay_units` must satisfy floor ≤ pay ≤ 999,999 and pay ≤ cap − reserve. The generator uses 900,000 (0.90 USDT).
- **Time bounds.** With T = the preparation time rounded up to the next whole minute:
  - buy_after = T;
  - buy_until = T+1h;
  - flat_by = T+2h = trade_after;
  - new_risk_end = flatten_start = T+2h+1min;
  - signing_end = T+3h.

  Every one must be at or before the F-127 pause, 2026-10-28T10:00:00Z. Otherwise the profile is refused, so a temp run can never reach the scored phase.
- **Only one buy.** No S1 entry or top-up BUY is ever proposed or planned under this policy: only the self-check BUY, and only in its BUY phase. Any planned BUY must have cash + fee ≤ 999,999 units.
- **Sells are unchanged.** The mandatory self-check SELL, the terminal flatten and recovery are unchanged.
- **Preparation.** `prepare_fs1.prepare_final` accepts an explicit temp profile, validated as above. It uses run `larp-final-selfcheck-temp`, database `larp_final_selfcheck`, and its own `ai_seeds_dir`/`nonce_dir` beside FS1's (suffix `-selfcheck-temp`). FS1's pinned path and outputs are unchanged.

## Pass criteria (offline; registered before code)

- **TS-1.** The generator builds a profile that passes `validate_live`. Its window matches T exactly, and two runs with the same T give byte-identical output.
- **TS-2.** `validate_live` refuses each of these:
  - pay ≥ 1,000,000 or pay below the 1000bp floor;
  - any window end after 2026-10-28T10:00Z;
  - `self_check_entry_cost_cap_bps` ≠ 1000;
  - the key on any other `policy_id` or environment (FS1, S5, REHEARSAL);
  - the temp `policy_id` without an `activation_self_check`.
- **TS-3.** In the BUY phase at a synthetic gas cost of about 6% of the trade, the planner emits exactly one non-mandatory BUY of the self-check symbol with cash + fee < 1 USDT. The same snapshot under the unmodified FS1 policy emits no buy (MINIMUM_TRADE/ENTRY_COST_CAP).
- **TS-4.** No other BUY under the temp policy:
  - no BUY in the S1 window after flat_by;
  - no BUY of another name;
  - no second BUY after BOUGHT/DONE.
  A forged S1 target proposal is rejected by the planner.
- **TS-5.** Holding the position triggers a mandatory SELL of the whole of it. After flat_by, the terminal flatten from flatten_start sells any leftover.
- **TS-6.** Standalone preparation with the temp profile produces the temp run, database and directories and the temp profile hash. Preparation without it still produces FS1's exact pins (`b8ba06e2…`) and refuses a non-temp substitute.
- **TS-7.** Regression: the existing FS1 self-check, final, standalone, S5 and planner suites pass unchanged.

Host qualification and owner approval are out of scope here and remain required:
- the signer's CAP-02 policy for sub-1-USDT legs;
- fresh final-wallet quotes and caps;
- registration and version event.

- 2026-10-28 correction (Claude Code): the zero-allowance revoke route (OBS03-B1) was merged in PR310 at `05b7aa6d` but has not been live-qualified. The Cost / risk line above calls the S5-OBS03 defect current; read it as "fixed in source, not yet confirmed live".

## Results (offline, 2026-10-28 SGT; branch `claude/final-selfcheck-temp-20261028`, not pushed or merged)

What changed:

| Area | Change |
|---|---|
| `larp/strategy/self_check.py` | Temp policy scope, the 1000bp floor (`temp_floor`) and the pay bounds |
| `larp/strategy/policy.py` | No S1 risk window under the temp policy |
| `larp/risk/planner.py` | Its only BUY is the self-check, in its BUY phase (`TEMP_SELF_CHECK_ONLY`). The self-check BUY uses the temp floor and the 1000bp entry cap. Cash + fee ≥ 1 USDT is refused (`TEMP_SELF_CHECK_SIZE`) |
| `larp/audit/reasons.py` | Both new rejection reasons |
| `larp/marketdata/history.py` | The temp policy needs the token history, like FS1 |
| `tools/deploy/build_selfcheck_temp.py` | The generator |
| `tools/deploy/prepare_fs1.py` | `--temp-self-check`, plus `--temp-stamp` (at most 30 minutes old) so the caps/services rerun reproduces the same profile bytes |
| `docs/build/ops/final-selfcheck-temp/` | Run sheet and a temp P4 |

Results against the pass criteria:

| Criterion | Result | Evidence |
|---|---|---|
| TS-1 | PASS | Stamping at 2026-10-27T18:00:30Z gives a buy window of 18:01–19:01Z, flat by 20:01Z, a terminal flatten at 20:02Z and signing end at 21:01Z. The output is byte-identical across runs (StrategyProfile.v1 `a1a72380…`, file `1cd2142a…`). The floor is 588,951 units. A stamp after 2026-10-28T07:00Z is refused. |
| TS-2 | PASS | Every out-of-scope variant listed is refused. FS1 `b8ba06e2…` still validates. |
| TS-3 | PASS | At about 6% gas: exactly one non-mandatory SKHYB BUY with cash + fee < 1 USDT. The same buy without the temp policy is refused (`ENTRY_COST_CAP`). About 11% gas is refused. |
| TS-4 | PASS | No BUY in the S1 window, after BOUGHT/DONE, or after the buy window. A forged S1 target is refused with `TEMP_SELF_CHECK_ONLY` both inside and outside the S1 window. |
| TS-5 | PASS | A held position is sold whole by a mandatory SELL. After EXPIRED, the terminal flatten covers what's left. |
| TS-6 | PASS | Preparation produces the temp run, database and directories. FS1 preparation is byte-for-byte unchanged. Mixed identities are refused. The CLI prints the stamp, and reusing it reproduces the profile. |
| TS-7 | PASS with one environment failure | See below. |

How the checks were run:
- **New tests:** 19 in `tests/strategy/test_selfcheck_temp.py` and `tests/runtime/test_selfcheck_temp_prepare.py`.
- **Red checks:** removing the planner or policy guard fails the forged-target and no-S1-risk tests.
- **TS-7 full suite:** local Python 3.12.14 (not the pinned 3.12.15) on macOS, against a disposable PostgreSQL 14.24 container.
  - Result: 3148 passed, 10 skipped, 1 failed, 4172 subtests passed.
  - The one failure is `tests/runtime/test_archive_budget.py::Budget::test_ar7_full_verification_memory_does_not_grow_with_the_journal`. Its memory probe crashes on macOS. It fails identically on unmodified `c1e23729`, so it is not caused by this change.
  - A focused rerun after the `--temp-stamp` change (strategy, risk, audit, FS1/S5 preparation) gave 648 passed and 45 skipped (PostgreSQL tests skipped).
- Linux, pinned-image and hosted CI have not been run.

Remaining, unchanged from the criteria section: review and merge, then release and registration (F-125). Owners also need to decide on this extra version event and on FS1's own 32-USDT self-check. Before install, the signer's CAP-02 must accept a sub-1-USDT leg, and fresh final-wallet quotes/caps are needed. The install must finish inside the stamped hour. Live evidence is then needed: both `tx_hash` values, DONE, and a flat wallet with no allowance before FS1 preparation.

## Amendment W2 — fixed buy window 12:00–14:00 SGT Oct 28 (registered before code, 2026-10-28 01:46 SGT)

Keith asked (2026-10-28 SGT): "can you extend the buy window to 12 to 2pm today and create another release". "Today" means Tue Oct 28 SGT, so the buy window is 2026-10-28T04:00Z to 06:00Z. This replaces the 1-hour window stamped at preparation. Everything else is unchanged: the size, floor, symbol, policy and sell rules.

New fixed times:

| Field | Time (UTC) | SGT |
|---|---|---|
| buy_after | 2026-10-28T04:00:00Z | 12:00 |
| buy_until | 2026-10-28T06:00:00Z | 14:00 |
| flat_by = trade_after | 2026-10-28T07:00:00Z | 15:00 |
| new_risk_end = flatten_start | 2026-10-28T07:01:00Z | 15:01 |
| signing_end | 2026-10-28T08:00:00Z | 16:00 |

Signing ends before the F-127 pause (10:00Z).

Because the profile no longer depends on when it is prepared, `--temp-stamp` is removed. Preparation is refused at or after buy_until.

Pass criteria:
- **W2-1.** The generator gives exactly these times. Its output is byte-identical whatever the preparation time. Preparation at or after 06:00Z is refused.
- **W2-2.** TS-2 to TS-6 still pass with the fixed window. The temp-stamp tests are replaced by a test that preparation at two different times produces identical profile bytes.
- **W2-3.** The full suite has no new failures compared with `47ccf11b`.

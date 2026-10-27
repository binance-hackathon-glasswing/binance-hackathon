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

# IDEA-110 — Temporary sub-1-USDT final-wallet self-check (TEMP-SC)

## TA-01 — temporary activation scope (2026-10-28; criteria before implementation/tests)

User confirms this release is only the temporary pipeline test: one BUY below 1 USDT then an automatic SELL,
with no discretionary strategy. Final FS1 declaration details remain for later review. The current W2 profile
already enforces this trading scope but live activation refuses its nine unfinished FS1 declarations.

Implement an explicit, narrowly pinned pre-scored activation exception, not a blanket removal of the final gate:
- TA1: only live run `larp-final-selfcheck-temp`, database `larp_final_selfcheck`, exact reviewed W2 profile file
  SHA-256 `b2e85827c65d99b709c0d958c2b1bf734e62cc271bba35ac536284dcba1b4187`, and activation before
  2026-10-28T06:00Z on Oct28 may retain the existing nine DRAFT rows. Require the existing exact deviations hash
  `5c38324017313746e08b1ee7c76b721888418a936559c50a7f2ecf02d429b707`, no OPEN rows and the exact draft IDs.
- TA2: verify actual profile bytes against their configured pin, validate the profile, and record the temporary
  activation scope, profile hash and deferred rows in RUN_ACTIVATED. Preserve wallet/build/registration/quarantine
  fencing and operator review reference; no FS1 declaration is finalized or silently omitted.
- TA3: ordinary FS1/live runs, wrong run/database/profile/hash, modified size/windows, missing/bad register,
  OPEN rows, added DRAFT rows and activation at/after cutoff refuse before store activation. No caller-supplied
  generic bypass flag. The standard final gate remains unchanged outside this exact temporary scope.
- TA4: existing sub-1-USDT/one-BUY/mandatory-full-SELL/no-S1-risk tests and standalone preparation tests pass;
  add activation integration regressions with disposable PostgreSQL and targeted guards/register/replay checks.
- TA5: generate and deliver the actual temp profile; commit/push code before building a new exact x86_64 bundle.
  Verify manifest/archive/profile pins, fix inclusion and declarations. Deliver installation/update instructions
  for the existing quarantined run (avoid a second init). No host install, key, signing or wallet action here.

The profile's W2 windows remain buy04:00–06:00Z, flat-by07:00Z, terminal flatten07:01Z, signing-end08:00Z Oct28.
It ends before the10:00Z pause. Model/source/caps and host preflights are retained as pipeline components;
they do not grant discretionary strategy authority. Actual final-wallet quotes/caps and registration remain
deployment inputs, not fabricated by offline preparation.

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

### W2 results (2026-10-28 SGT; PR #322)

| Criterion | Result | Evidence |
|---|---|---|
| W2-1 | PASS | The generator gives exactly the registered times. Output is byte-identical when prepared at 2026-10-27T18:00:30Z and at 2026-10-28T05:59:59Z. Preparation at 06:00Z or 09:00Z is refused ("window closed"). |
| W2-2 | PASS | 19 IDEA-110 tests pass. Preparing at two different times gives identical profile bytes. |
| W2-3 | PASS | Full suite, local macOS, Python 3.12.14, PostgreSQL 14.24: 3149 passed, 10 skipped, 1 failed, 4172 subtests. The failure is the same pre-existing `test_ar7_full_verification_memory_does_not_grow_with_the_journal`, which also fails on `c1e23729`. |

A scratch run (not committed) of the FINAL caps/signer assembly with the W2 profile gave `numeric_status: COVERED`, and the runtime built from the profile.

## Install progress (2026-10-28 SGT, Claude Code with Yao Zhu)

- **W0** (00:50Z, read-only): the final wallet has no stock, no allowance to our router, MetaMask or Permit2, 170 USDT, 0.0400 BNB and nonce 2 (the MetaMask gas swap). PASS.
- **D1**: `larp_final_selfcheck` created; `IDEA-110 D1 PASS`, `D1_DONE` (Yao).
- **M3 gap and fix**: no FINAL caps-inputs path existed. `review_rehearsal_caps.py` is REHEARSAL-only. `tools/deploy/final_caps_inputs.py` (PR #323) builds the inputs from `prepare_fs1` output and live final-wallet quotes. Offline tests: 23 passed.
- **M3** (stamp `20261028T010234Z`): COVERED with 26 quotes. Profile `b2e85827…` matches the release. Signer `9e574c312d66…`, execution `1be4c3034bb7…`. The quoted self-check BUY of 0.90 USDT costs about 1.3e-5 BNB in gas.
- **A1**: Yao Zhu and Isaac approved these exact hashes, the caps, the window and the sub-1-USDT leg (relayed by Yao in chat).
- **M1/M4 local**: Keith's release assets were verified. The bound `release.json` is `9271a5d6…`, and the signer check passes. Host steps follow the run sheet's install package section.
- **Risk** (corrected 2026-10-28, REL-AUD01): this line first said FENCE01 was reverted. It was not. PR317/PR319 (FENCE01/FENCE02) are ancestors of `2aa95617`; the revert commit `69d3e314` sits on an unmerged branch, and the published archive contains the fenced files byte for byte ([audit](../build/RELEASE_DECLARATIONS_AUDIT_20261028.md)).

## TA-01 results and release (2026-10-28 SGT)

Implemented at `e261bcfc7a339a5e28388b843798b4197a9993a6`, pushed before building. TA1–TA3: exact W2 file/run/database/date/register pins qualify; FS1, altered files/pins/size/windows/register/OPEN/extra-DRAFT/cutoff refuse before activation. RUN_ACTIVATED retains temporary purpose/profile/deferred rows. A real disposable-PostgreSQL regression activates the existing quarantined run, registers the build and refuses a repeated activation. No generic bypass, declaration status edit or database reset. TA4: focused79 tests/17subtests; full Linux/Python3.12.15/PG14.24:3165 passed/4172subtests/11skips/0failed; three sandbox skips pass separately,3168 distinct passes/8unrun. TA5: actual public profile generated (b2e85827), new exact x86_64 bundle built; all217 source files/256 checksums match, primary/signer offline provisioning PASS, sandboxed demo PASS. Hosted CI ran no steps due billing. [Published release/receipt and remaining deployment steps](../build/evidence/temp-selfcheck-20261028/README.md). PR324 retains final declaration follow-up; user deploys later. No host/key/wallet/signing action.

## Amendment W3 — re-run on the FS1 build after IDEA-111 (registered before install, 2026-10-28 ~14:50 SGT)

The W2 run (`e261bcfc`) made three approves and three revokes and no swap (IDEA-111). Yao Zhu asked for one more
buy and sell on the final wallet with the fixed build: "set buy window as 3pm" and then chose "16:45 sell".

- Build: release `fs1-4ebf65fe` (contains IDEA-111 and IDEA-112; declarations final, so ordinary live activation, no
  TA-01 exception). The profile is generated by this branch's `prepare_fs1 --temp-self-check` at preparation.
- Fresh run `larp-final-selfcheck-temp2`, database `larp_final_selfcheck2`, directories `-selfcheck-temp2`
  (the W2 run keeps its own registered build and audit trail).
- Window (UTC, Oct 28): buy 07:00–08:30 (15:00–16:30 SGT); flat_by = trade_after 08:45 (16:45 SGT); new risk end =
  flatten 08:46; signing ends 09:30, before the F-127 pause (10:00Z). Size, symbol, floor and policy unchanged.
- Pass criteria: W3-1 generator gives exactly these times and refuses preparation at or after 08:30Z; W3-2 TS/W2 tests
  pass with the new identity; W3-3 live: one SKHYB BUY and one SELL with `tx_hash` in round logs, self-check DONE, flat
  wallet. The TA-01 tests now read the W2 profile from its saved evidence copy.
- Offline result: strategy/runtime/execution 1206 passed, 402 skipped (no local PostgreSQL); full suite on the
  15:00–15:29 draft 2570 passed, 624 skipped, 0 failed.

### W3 install and live BUY (2026-10-28, Claude Code on Yao Zhu's laptop at Yao's instruction)

- 06:43Z: `larp-dev` (db.t4g.micro) ran out of memory (~100 MB free, ~430 MB swap); the W2 run's services
  restart-looped on `Unavailable`. W2 services stopped (X0p/X0s); RDS rebooted at Yao's approval (07:07Z shutdown,
  recovery complete 07:13:43Z).
- Release `fs1-4ebf65fe` (bundle `7b8e504d…`, manifest `e3c190ab…`) uploaded; M3 stamp `20261028T071015Z`: COVERED,
  23 quotes; profile `70cf1bee…`, signer `02e9b9a0…`, execution `068f30d9…` (approved by Yao Zhu in chat).
- D1 `larp_final_selfcheck2` (first attempt hit the pre-reboot timeouts); P2/P3 (routes recheck PASS after reboot),
  P2/S1/S1b (key loader PASS), P4 (first init `RUNTIME_FAILED` on a transient DB error, init retried, activated
  epoch 2), S2, P5, P6: all services active, 0 restarts, at 07:19Z.
- **W3-3 BUY: PASS.** SKHYB BUY 0.899999 USDT. Approve `0x912ec18fbf75cce27e34faacea441400d97af3ce84788949cad3c54bb7a249ad`
  (status 1, block 130240185); swap `0x6470add8492212d95c7f6b006392aaf8874026d3a45e70b87efa033cee3374d0` (status 1,
  block 130240300). No refusal, no revoke: the IDEA-111 live swap check passes. SELL due at 08:45Z.
- **W3-3 SELL: PASS.** The self-check sells as soon as the bought units settle (`self_check.phase`: units held → SELL;
  `flat_by` 08:45Z is the deadline, not the sell time). Full position 5733218145265367 SKHYB units: approve
  `0x988881dc85ca33e499eb90d6ee6e0b401a5fae4a56bf3bbbc7efc6ed925256af` (status 1, block 130241630), swap
  `0x95c1b4cae53c705776bc2c5254f4dc4576cf2efd93eb78eba9294e3c1019fa39` (status 1, block 130241743), ~07:32Z. Both
  execution records COMPLETED, 4 signatures, 0 refusals; router allowances all 0 (CLEAN); services 0 restarts.
  Seen in passing: transient `StateVersionConflict` cycle blocks on the BUY record (recovered, no effect).
  Open: receiver ACKs/empty spool check, final chain flat check, and retiring the run after signing ends (09:30Z).

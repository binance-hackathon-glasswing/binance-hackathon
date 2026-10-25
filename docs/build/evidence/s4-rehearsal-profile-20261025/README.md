# S4 REHEARSAL profile (IDEA-097, 2026-10-25)

The candidate `StrategyProfile.v1` for S4, a flatten-only test on the dev wallet:
- run 5 starts from run 4's carried-over book;
- it is already inside the terminal flatten when installed;
- it sells every held name with IDEA-096 allowance recovery on.

This is a **candidate for review**: not approved, built, installed or bound to a `signer.json`. It is never installed
for the final run.

| File | SHA-256 |
|---|---|
| `../s2-rehearsal-profile-20261024/s2-block.json` (the profile's `s1` block, S2's unchanged) | `35e20c38e23657da6723e31b18f323e5f5ede778de938d73c72ff1a2c1408d03` |
| `rehearsal-s4-deterministic.json` (file bytes; the `PROFILE_SHA` to pin) | `e79a92fc7905107130f368fc95735f6e0dbafa1f41e47e81d8279b0014d3aa25` |
| `StrategyProfile.v1` digest of the same profile | `6164039cf44fb820eda77ea6268ff936495fccc1ef0a07a2db2dbdcb317b92de` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile rehearsal-s4-deterministic.json`; the `PROBE_SHA` to pin) | `9397c0cfdcce2982eaaecab6359eb53464fad64127fa7112f4ed99ae2eecb63f` |

## Against S2's profile `eb55d76a…`

S4 differs from S2's profile only in these keys and their provenance:

| Key | S2 | S4 |
|---|---|---|
| `trade_after` | 2026-10-24T01:00:00Z | 2026-10-25T10:00:00Z |
| `new_risk_end` | 2026-10-25T08:00:00Z | 2026-10-25T10:30:00Z |
| `flatten_start` | 2026-10-25T09:00:00Z | 2026-10-25T10:30:00Z (before run 5 can start) |
| `signing_end` | 2026-10-25T15:00:00Z | 2026-10-27T12:00:00Z (Tue 20:00 SGT, before FS1 on Oct 29) |
| `policy_id` | `larp-s2-rehearsal-v1` | `larp-s4-rehearsal-v1` |
| `holdings_carry_over` | — | `RUN_EXPORT` |
| `gas_action_budget_units` | 384000000000000 (2 children) | 1536000000000000 (8 children, IDEA-096 recovery) |
| `exit_gas_reserve_units` | 3840000000000000 | 15360000000000000 (5 positions × 2 children × action) |

Everything else is S2's:
- the S1 block (`KIT_OPEN_STATE`, 5 attempts per leg);
- sizes, caps, slippage, `gas_sizing_budget_units` and the quote summary;
- the SHADOW scope and the `dev` run mode.

## What the agent does with it

- **No BUY.** `new_risk_end` has passed before the install.
- **Every round is a terminal-flatten round.** Every held name is a mandatory SELL (`TERMINAL_FLATTEN`), split into
  balanced children under the per-trade cap.
- **Allowance recovery** (IDEA-096 F2/F3, PR282): before a SELL's approve, a non-zero allowance on another token is
  cleared with a zero-only approve. A swap aborted after its approve clears its own allowance. The strict swap-time
  preflight is unchanged.
- **Signing ends** Tue 2026-10-27 12:00Z.

## Before install (not done)

- **BNB top-up.** With recovery, the exit gas reserve is **0.01536 BNB**; Gate B and caps review refuse a start
  below it. Run 4 left about 0.00518 BNB. Add BNB to the dev wallet before the capture (about 0.02 BNB in total
  leaves room for the gas spent on cleanups).
- **Export.** Run 4's book is exported with `checks/holdings-export.sh` after run 4 is retired. Its units must equal
  the captured chain balances exactly.
- **Approvals.** Isaac approves this profile hash, the probe and the new `signer.json` (with
  `signing_policy.allowance_recovery: true`). Keegan reviews the carry-over accounting and the recovery gas.
- **The usual RC sheet steps:** release build, Q1 quote check, D1 database, M3 coverage, install.

## Reproduce

```bash
python -m tools.deploy.build_rehearsal_candidate --exit-children 2 --carry-over \
  --s1-config docs/build/evidence/s2-rehearsal-profile-20261024/s2-block.json \
  --s1-decision "IDEA-089 S2-2/S2-9 (Yao, 2026-10-23): run-3 block (IDEA-084 PF-01 values; weights 1/5, SJ-09-PC01 C5; start UP, legs 3, expiry 3, Keith 2026-10-23) with hours KIT_OPEN_STATE and 5 attempts per leg" \
  --output /tmp/s4-profile-check.json
```

It prints the `StrategyProfile.v1` digest above. The output must be byte-identical to
`rehearsal-s4-deterministic.json`.

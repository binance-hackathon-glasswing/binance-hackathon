# S5: FS1 on the dev wallet, with FS1's model calls, running to Tue Oct 27 12:00 SGT (IDEA-104 R3, 2026-10-26)

A candidate `StrategyProfile.v1` for one more signed dev rehearsal. S5-SIZE01 is verified offline (source
`2f9e886c…`: full pinned suite 2978 passed, 8 skipped, 4069 subtests), and is not installed or bound to a
`signer.json`. [Receipt](../s5-size01-review-20261026.json). **FS1 stays the final strategy:** S5 is REHEARSAL-only on the dev wallet and is never installed for the
final run. Record: [IDEA-104](../../../ledger/IDEA-104.md) (S5-SIZE01 replaces R3 `f371b18d…`, R2 `5a5a200a…`, R1 `c7938dae…`).

| File | SHA-256 |
|---|---|
| `rehearsal-s5.json` (file bytes; the `PROFILE_SHA` to pin) | `6dadc1961a54374f51415e2168ff8d4a917b28f90e58c9493a1b9fbd8731e80d` |
| `StrategyProfile.v1` digest of the same profile | `d80045d446af6297e5e0c5df2f1aeb6f0467e4a402728a1a222361b8b2ae4248` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile rehearsal-s5.json`) | `68e49922432f8a8e8081fbaa32b3d8bb3b5614a5ca2982b6ed5ee671262f8e17` |

## What it is

FS1 FINAL with recovery (`b8ba06e2…`) at rehearsal size: it differs only in `environment` REHEARSAL, the 100 USDT
sizes (`expected_equity_units`, `per_trade_cap_units`, `cost_reserve_units`), the window, `policy_id`
`larp-s5-rehearsal-v1`, no FINAL-only `activation_self_check`, and S5-only `s5_entry_lot_units` 19 USDT. So it has FS1's `s1` block, 20 bp slippage, the
PR278-RV01 fields including gas-excluded capital, recovery gas, and **FS1's model authority** (`BOUNDED_FALSIFIER`,
`DISCRETIONARY_EXIT`): it must be prepared with FS1's AIand/ChatGPT routing `9b86c732…`, and verified red flags exit
or block entry as in FS1.

**FS1 token history (IDEA-103, PR295).** Like FS1 FINAL and FS1-R, S5 cannot be prepared or started without a pinned
`TokenHistoryConfig.v1` ([contract](../../FS1_TOKEN_HISTORY.md)): pass it to `prepare_shadow.py prepare
--token-history-config`, install the packaged `token-history.json` at `/etc/larp/token-history.json`. Its
`timestamp_evidence_sha256` must be the hash of the actual hourly OPEN timestamp evidence (Keith), not a synthetic value.

| Window key | UTC | Singapore (UTC+8) |
|---|---|---|
| `trade_after` (buys allowed) | Mon Oct 26 06:00 | Mon Oct 26 14:00 |
| `new_risk_end` (buys stop) | Mon Oct 26 23:00 | Tue Oct 27 07:00 |
| `flatten_start` (every holding is a mandatory sell) | **Tue Oct 27 00:00** | **Tue Oct 27 08:00** |
| `signing_end` (run ends) | Tue Oct 27 04:00 | **Tue Oct 27 12:00** |

`signing_end` is inside the development time, which the user relayed on 2026-10-26 as extended to Oct 28 (F-126).

Notes for the run owner:
- **Fresh run.** The dev wallet is flat after run 6 (IDEA-097 S4-L1), so S5 installs as a fresh run, with no carry-over.
- **Install time.** Installing after `trade_after` is fine: buying starts once both services run (P5 before P4).
- **Cash.** The 19-USDT high-level opening lot replaces R3's unfundable 15.44-USDT target at the recorded 81.37
  USDT cash. Four lots fit the 95% stock-capital ceiling; five do not. BNB remains excluded, exact quote costs
  and all risk/cash limits still apply, and reduced levels keep normal targets. M4 checks fresh cash using the
  selected profile. Actual holdings may differ from FS1's equal-fifth portfolio; FS1's own sizing is unchanged.
- **Selling.** Mandatory sells are spaced one per 15-minute slot per name (IDEA-102), with no per-session cap: four
  hours of flatten is 16 slots per name.
- **Run sheet.** [`docs/build/ops/rehearsal-install-s5-20261026/`](../../ops/rehearsal-install-s5-20261026/README.md).

## Reproduce

```bash
python -m tools.deploy.build_rehearsal_candidate --exit-children 2 --fs1-rehearsal --allowance-recovery --s5 \
  --s1-config docs/build/evidence/fs1-final-20261025/fs1-block.json \
  --s1-decision "IDEA-104 S5 (2026-10-26): the FS1 final block (S2's block: IDEA-084 PF-01 values; weights 1/5, start UP, legs 3, expiry 3, deterministic limiter; hours KIT_OPEN_STATE, 5 attempts per leg) on the dev wallet, selling everything from Tuesday Oct 27 08:00 SGT" \
  --output /tmp/s5-profile-check.json
```

The committed builder reproduces the digest above and `rehearsal-s5.json` byte for byte (SZ1). Exact quotes,
qualified history and the new release/signer/host acceptance are still required before installation.

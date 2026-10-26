# S5: FS1 on the dev wallet, with FS1's model calls, running to Tue Oct 27 12:00 SGT (IDEA-104 R3, 2026-10-26)

A candidate `StrategyProfile.v1` for one more signed dev rehearsal. It is not approved, installed or bound to a
`signer.json`. **FS1 stays the final strategy:** S5 is REHEARSAL-only on the dev wallet and is never installed for the
final run. Record: [IDEA-104](../../../ledger/IDEA-104.md) (R3 replaces R2 `5a5a200a…`, which replaced R1 `c7938dae…`).

| File | SHA-256 |
|---|---|
| `rehearsal-s5.json` (file bytes; the `PROFILE_SHA` to pin) | `f371b18dd44e4da4ab96a86a8c2d491cde6d799168ca53f6ae93d1358be65c5b` |
| `StrategyProfile.v1` digest of the same profile | `63c35391e519b4e3282782dc5f35fcc546bb89230a3761865ca51b16c74533a9` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile rehearsal-s5.json`) | `90344caae70b2c17d7197d75cbf01e2b9e2dfa85885534dae5f4f32b22051e9d` |

## What it is

FS1 FINAL with recovery (`b8ba06e2…`) at rehearsal size: it differs only in `environment` REHEARSAL, the 100 USDT
sizes (`expected_equity_units`, `per_trade_cap_units`, `cost_reserve_units`), the window, `policy_id`
`larp-s5-rehearsal-v1`, and no FINAL-only `activation_self_check`. So it has FS1's `s1` block, 20 bp slippage, the
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
- **Cash.** With gas excluded, S5 buys nothing below about 98.3 USDT of cash (S5R2-7/S5R3-4); the dev wallet holds
  81.37 USDT after run 6.
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

It prints the digest above; the output must be byte-identical to `rehearsal-s5.json`.

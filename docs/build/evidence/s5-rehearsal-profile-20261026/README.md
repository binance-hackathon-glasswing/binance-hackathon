# S5: FS1's settings on the dev wallet, running to Tue Oct 27 12:00 SGT (IDEA-104 R2, 2026-10-26)

A candidate `StrategyProfile.v1` for one more signed dev rehearsal. It is not approved, installed or bound to a
`signer.json`. **FS1 stays the final strategy:** S5 is REHEARSAL-only on the dev wallet and is never installed for the
final run. Record: [IDEA-104](../../../ledger/IDEA-104.md) (R2 replaces the R1 Monday-night window `c7938dae…`).

| File | SHA-256 |
|---|---|
| `rehearsal-s5.json` (file bytes; the `PROFILE_SHA` to pin) | `5a5a200ae26c59dbfc79ba0e269fe909a749892944f16fa3e1583cfb283c8b2b` |
| `StrategyProfile.v1` digest of the same profile | `64918e6a09d540b0d8fe3d5fd88ebc136810b0f1fadf0f87508acf8bff4ebe46` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile rehearsal-s5.json`) | `8ba1328f2423f81a84496d9fa466568b924611202d395e4b9926839f0227b06f` |

## What it is

`fs1-rehearsal-recovery.json` (`17ab891d…`) with a new window and `policy_id` `larp-s5-rehearsal-v1`, nothing else.
That means FS1's `s1` block (weights 1/5, `KIT_OPEN_STATE` hours, 5 attempts per discretionary leg), 20 bp slippage,
the four FS1 review refinements, the IDEA-096 allowance-recovery gas and the deterministic SHADOW dev scope.

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
- **Book size.** With about 90 USDT and an 18.64 USDT minimum trade, the book may hold four names, not five [ESTIMATE].
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

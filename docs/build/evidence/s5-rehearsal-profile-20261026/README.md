# S5: FS1's settings on the dev wallet, selling everything Monday night (IDEA-104, 2026-10-26)

A candidate `StrategyProfile.v1` for one more signed dev rehearsal. It is not approved, installed or bound to a
`signer.json`. **FS1 stays the final strategy:** S5 is REHEARSAL-only on the dev wallet and is never installed for the
final run. Record: [IDEA-104](../../../ledger/IDEA-104.md).

| File | SHA-256 |
|---|---|
| `rehearsal-s5.json` (file bytes; the `PROFILE_SHA` to pin) | `c7938dae9ca21d459f876c7272b25c52d25c3a814e6c26ddff8db0893687a650` |
| `StrategyProfile.v1` digest of the same profile | `cb7f8e1cfb745fad66d49765e5aa02c09a2c9ccf9c4a1d4d7e9b5f0dbb7289ef` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile rehearsal-s5.json`) | `9f2dde0007e70f72414756e105fff871cac85c0fcd0e54f7c07be316a6bd65ce` |

## What it is

`fs1-rehearsal-recovery.json` (`17ab891d…`) with a new window and `policy_id` `larp-s5-rehearsal-v1`, nothing else.
That means FS1's `s1` block (weights 1/5, `KIT_OPEN_STATE` hours, 5 attempts per discretionary leg), 20 bp slippage,
the four FS1 review refinements, the IDEA-096 allowance-recovery gas and the deterministic SHADOW dev scope.

| Window key | UTC | Singapore (UTC+8) |
|---|---|---|
| `trade_after` (buys allowed) | Sun Oct 25 20:00 | Mon Oct 26 04:00 |
| `new_risk_end` (buys stop) | Mon Oct 26 12:00 | Mon Oct 26 20:00 |
| `flatten_start` (every holding is a mandatory sell) | **Mon Oct 26 13:00** | **Mon Oct 26 21:00** |
| `signing_end` | Mon Oct 26 20:00 | Tue Oct 27 04:00 |

`signing_end` is inside the development phase, which ends on Oct 26 UTC (F-125), as S4 did.

Notes for the run owner:
- **Fresh run.** The dev wallet is flat after run 6 (IDEA-097 S4-L1), so S5 installs as a fresh run, with no carry-over.
- **Book size.** With about 90 USDT and an 18.64 USDT minimum trade, the book may hold four names, not five [ESTIMATE].
- **Selling.** Mandatory sells are spaced one per 15-minute slot per name (IDEA-102), with no per-session cap.
- **Run sheet.** No S5 run sheet has been written yet.

## Reproduce

```bash
python -m tools.deploy.build_rehearsal_candidate --exit-children 2 --fs1-rehearsal --allowance-recovery --s5 \
  --s1-config docs/build/evidence/fs1-final-20261025/fs1-block.json \
  --s1-decision "IDEA-104 S5 (2026-10-26): the FS1 final block (S2's block: IDEA-084 PF-01 values; weights 1/5, start UP, legs 3, expiry 3, deterministic limiter; hours KIT_OPEN_STATE, 5 attempts per leg) on the dev wallet, selling everything from Monday 21:00 SGT" \
  --output /tmp/s5-profile-check.json
```

It prints the digest above; the output must be byte-identical to `rehearsal-s5.json`.

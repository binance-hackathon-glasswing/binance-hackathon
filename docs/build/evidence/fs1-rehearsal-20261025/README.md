# FS1-R dev REHEARSAL profile: the final FS1 settings on the dev wallet (IDEA-093, 2026-10-25)

A **candidate for review**, not approved, installed or bound to a `signer.json`. It lets the FS1 final settings trade
live on the dev wallet before the freeze. It is REHEARSAL-only (dev SHADOW scope, S2-1) and is never installed for the
final run.

The fourth PR278-RV01 field, `s1_capital_basis=EXCLUDE_GAS`, applies nominal exposure levels to cash plus marked
stocks minus the cost reserve, excluding BNB from stock allocation. It matches FINAL's F-125 sizing logic using
the dev wallet's actual balances; it does not require a 30 USDT dev-wallet seed. See the
[FINAL candidate](../fs1-final-20261025/README.md) and [review](../../../research/fs1-review-20261025.md).

| File | SHA-256 |
|---|---|
| `../fs1-final-20261025/fs1-block.json` (the `s1` block; same bytes as S2's) | `35e20c38e23657da6723e31b18f323e5f5ede778de938d73c72ff1a2c1408d03` |
| `fs1-rehearsal.json` (file bytes; the `PROFILE_SHA` to pin) | `54802665f3fd28cfcdf4fcb3dd9653db2ce5fab00b4ecfd8a183774d436c4115` |
| `StrategyProfile.v1` digest | `22a9ad90916730bf3c13299aedc4fce54c028abc0f62eb9bc51e6733ac89deb9` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile fs1-rehearsal.json`; the `PROBE_SHA` to pin) | `7d5a5602a2f01f1a789f1bb69a400a4114c2507207d00c695e7220561c2e8693` |

## Against S2's profile `eb55d76a…`

It differs only in:
- `slippage_bps` 8 → 20 (FS1's value; S2-F6);
- the window (proposed; the run owner may rebuild it with other times): `trade_after` 2026-10-25T16:00:00Z (Mon 00:00
  SGT, an hour after run 4's `signing_end`, so run 4 can retire flat first), `new_risk_end` 2026-10-26T06:00:00Z,
  `flatten_start` 2026-10-26T07:00:00Z, `signing_end` 2026-10-26T12:00:00Z (Mon 20:00 SGT, before Monday's NYSE open);
- `policy_id` `larp-fs1-rehearsal-v1`;
- PR278-RV01's `entry_cost_basis=AUTHORIZED_MINIMUM`, `run_halt_recovery_bps=500` and
  `s1_reduction_cost_cap_bps=50`, with the same semantics as FINAL;
- the provenance of those keys, and the decision ID on `s1`/`baseline` (same block bytes and data hash).

The `s1` block equals the FS1 FINAL profile's. Every buy and sell in this window is off-hours, which is the case FS1
adds. Like every signed dev rehearsal so far it uses the deterministic assessor (no hosted models); FS1's AIand routing
is tested offline only (IDEA-093 FS1-3/FS1-4). Earlier S4-R/FS1-R hashes and receipts are historical. The reviewed
candidate needs new exact-profile/caps/gas/signer and release qualification, including sub-entry-minimum reductions.

## Before installing: the wallet must hold no stock

A new run's install (`gate_a.initial_state`) refuses a wallet holding any stock, dust included (IDEA-092 H1/H2), and
this run cannot sell another run's holdings. Run 4 must have sold out in its Sunday flatten. Run 4 is RC7, which
predates the S2-F6 fix, so its SELL swaps can abort as its buys did. First step: a read-only wallet check (chain
monitor `--once`) showing 0 units of all five stocks. If any remain, FS1-R cannot be installed; the options are a
reviewed H1 carry-over (not built) or skipping FS1-R.

## What to check on the run (IDEA-093 FS1-R)

A BUY whose swap completes after its approve; rounds in consecutive 15-minute slots (IDEA-090 F7); the flatten sells
every position before `signing_end`; balance check MATCH; no HALT or quarantine.

## Reproduce

```bash
python -m tools.deploy.build_rehearsal_candidate --exit-children 2 --fs1-rehearsal \
  --s1-config docs/build/evidence/fs1-final-20261025/fs1-block.json \
  --s1-decision "IDEA-093 FS1-R (2026-10-25): the FS1 final block (S2's block: IDEA-084 PF-01 values; weights 1/5, start UP, legs 3, expiry 3, deterministic limiter; hours KIT_OPEN_STATE, 5 attempts per leg) for an off-hours dev rehearsal" \
  --output /tmp/fs1r-profile-check.json
```

It prints the digest above; the output must be byte-identical to `fs1-rehearsal.json`.

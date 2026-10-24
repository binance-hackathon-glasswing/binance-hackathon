# S4-R dev REHEARSAL profile: the final S4 settings on the dev wallet (IDEA-093, 2026-10-25)

A **candidate for review**, not approved, installed or bound to a `signer.json`. It lets the S4 final settings trade
live on the dev wallet before the freeze. It is REHEARSAL-only (dev SHADOW scope, S2-1) and is never installed for the
final run.

| File | SHA-256 |
|---|---|
| `../s4-final-profile-20261025/s4-block.json` (the `s1` block; same bytes as S2's) | `35e20c38e23657da6723e31b18f323e5f5ede778de938d73c72ff1a2c1408d03` |
| `rehearsal-s4-deterministic.json` (file bytes; the `PROFILE_SHA` to pin) | `9dbe6f4d82f79a069b995e3716b8331a505c37a4db3db14f885626825b440abe` |
| `StrategyProfile.v1` digest | `b09c88e82f962182b36f37bbc91c0c0fef89c1c69bb5ea117dd405e92331fb98` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile rehearsal-s4-deterministic.json`; the `PROBE_SHA` to pin) | `a56f53076d8ff50ff0e90f6c23c8189f4432aebc4275f5f9669312f6a8d725b5` |

## Against S2's profile `eb55d76a…`

It differs only in:
- `slippage_bps` 8 → 20 (S4's value; S2-F6);
- the window (proposed; the run owner may rebuild it with other times): `trade_after` 2026-10-25T16:00:00Z (Mon 00:00
  SGT, an hour after run 4's `signing_end`, so run 4 can retire flat first), `new_risk_end` 2026-10-26T06:00:00Z,
  `flatten_start` 2026-10-26T07:00:00Z, `signing_end` 2026-10-26T12:00:00Z (Mon 20:00 SGT, before Monday's NYSE open);
- `policy_id` `larp-s4-rehearsal-v1`;
- the provenance of those keys, and the decision ID on `s1`/`baseline` (same block bytes and data hash).

The `s1` block equals the S4 FINAL profile's. Every buy and sell in this window is off-hours, which is the case S4 adds.

## What to check on the run (IDEA-093 S4-R)

A BUY whose swap completes after its approve; rounds in consecutive 15-minute slots (IDEA-090 F7); the flatten sells
every position before `signing_end`; balance check MATCH; no HALT or quarantine.

## Reproduce

```bash
python -m tools.deploy.build_rehearsal_candidate --exit-children 2 --s4-rehearsal \
  --s1-config docs/build/evidence/s4-final-profile-20261025/s4-block.json \
  --s1-decision "IDEA-093 S4-R (2026-10-25): the S4 final block (S2's block: IDEA-084 PF-01 values; weights 1/5, start UP, legs 3, expiry 3, deterministic limiter; hours KIT_OPEN_STATE, 5 attempts per leg) for an off-hours dev rehearsal" \
  --output /tmp/s4r-profile-check.json
```

It prints the digest above; the output must be byte-identical to `rehearsal-s4-deterministic.json`.

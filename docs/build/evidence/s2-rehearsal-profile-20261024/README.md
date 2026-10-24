# Run-4 S2 REHEARSAL profile (IDEA-089, 2026-10-24)

The candidate `StrategyProfile.v1` for signed dev rehearsal run 4, the weekend trade test S2 (IDEA-089). It is a
**candidate for review**: not approved, installed or bound to a `signer.json`. Isaac's approval of this hash and of the
`signer.json` that the RC7 M3 prints is still required (S2-7). S2 is never installed for the final run.

| File | SHA-256 |
|---|---|
| `s2-block.json` (the profile's `s1` block) | `35e20c38e23657da6723e31b18f323e5f5ede778de938d73c72ff1a2c1408d03` |
| `rehearsal-s2-deterministic.json` (file bytes; the `PROFILE_SHA` to pin) | `eb55d76a36b9fb931f551752da9266c379072611d789ab85d9cb1fc2291d8e68` |
| `StrategyProfile.v1` digest of the same profile | `120fcd1275d217ca07d3bbca40dd8e4e9484b9de579f7964023a84867fbb8e69` |
| M3 probe (`tools/deploy/ld10_readonly_packet.py --profile rehearsal-s2-deterministic.json`; the `PROBE_SHA` to pin) | `8e8d6c89bf4f16e69465b2fc46db4414b4b623d2d6909b2a3c9325d5930ce97a` |

## Against run 3's profile `6bcf1dfb…`

`s2-block.json` is run 3's `s1-block.json` with two changes in `execution`:
- `hours` `KIT_OPEN_STATE` (S2-2, S2-8): discretionary legs may trade from the session open to the next open, the
  interval mandatory sells already use. The kit's `openState` check (F-95) and the profile window still apply.
- `max_attempts_per_leg_session` 3 → 5 (S2-9): the weekend sits in one session (Friday's).

The profile differs from `6bcf1dfb…` only in:
- the `s1` block above;
- the window (S2-4): `trade_after` 2026-10-24T01:00:00Z, `new_risk_end` 2026-10-25T08:00:00Z, `flatten_start`
  2026-10-25T09:00:00Z, `signing_end` 2026-10-25T15:00:00Z;
- `policy_id` `larp-s2-rehearsal-v1`;
- the provenance of those keys and of `baseline` (which shares the S1 block's decision ID).

Sizes, the two-child exit reserve, gas budgets, L/m, slippage, impact, caps, the quote summary and the SHADOW scope are
run 3's (S2-3, S2-5). The scope check (S2-1) refuses this profile outside a REHEARSAL with SHADOW evidence and
falsifiers, and outside a `dev` run.

## Reproduce

```bash
python -m tools.deploy.build_rehearsal_candidate --exit-children 2 \
  --s1-config docs/build/evidence/s2-rehearsal-profile-20261024/s2-block.json \
  --s1-decision "IDEA-089 S2-2/S2-9 (Yao, 2026-10-23): run-3 block (IDEA-084 PF-01 values; weights 1/5, SJ-09-PC01 C5; start UP, legs 3, expiry 3, Keith 2026-10-23) with hours KIT_OPEN_STATE and 5 attempts per leg" \
  --output /tmp/s2-profile-check.json
```

It prints the `StrategyProfile.v1` digest above. The output must be byte-identical to `rehearsal-s2-deterministic.json`.

## Checked offline (`tests/strategy/test_s2_weekend.py`, IDEA-089 S2I-1..S2I-7)

- The profile rebuilds byte for byte, passes `validate_live`, a signed dev `gate_a.prepare` with the router-policy pair,
  `gate_a_check`'s scope and input checks, and builds a dev/service runtime with no network. The probe hash is as above.
- On synthetic snapshots, the planner reserves a weekend discretionary BUY under `KIT_OPEN_STATE` (refused as
  `EXECUTION_WINDOW_CLOSED` without it), and execution admission (`permitted`) admits that intent until the next open.
- Five BUY quote rounds per name over the session, then `LEG_ATTEMPT_LIMIT`.

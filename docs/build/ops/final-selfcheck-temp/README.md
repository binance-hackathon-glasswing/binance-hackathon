# Temporary final-wallet self-check (IDEA-110 TEMP-SC): run sheet

This sheet installs a **temporary** run on the final wallet. It is **not FS1**:
- one buy of 0.90 USDT of SKHYB;
- the automatic sell of the whole position;
- nothing else.

It answers F-125's "end-to-end self-check with a real final-wallet trade" at the smallest size Keith asked for (2026-10-28 SGT). This sheet is a plan: no host, wallet, key or approval action has been taken. Times are UTC (SGT = UTC+8).

TA-01 (Oct28): the user authorizes this temporary pipeline test while FS1's final declarations remain unfinished.
Activation now accepts the existing nine DRAFT rows only for this exact W2 profile hash, temp run/database and
Oct28 activation before06:00Z. It records the temporary purpose and deferred IDs in RUN_ACTIVATED.
No FS1 declaration becomes FINAL; ordinary FS1/live activation still refuses DRAFT rows. Existing signer, caps,
release/registration, wallet, gas, logging and market checks remain. No discretionary strategy BUY is permitted.
The generated public profile is [strategy-profile.json](../../evidence/temp-selfcheck-20261028/strategy-profile.json),
file SHA-256 `b2e85827c65d99b709c0d958c2b1bf734e62cc271bba35ac536284dcba1b4187`.

**Continuing the existing refused P4:** after installing/binding the new bundle and service configs to its new
build_id, use P4 with third argument `existing-quarantined`:
`ssm_run.py host/p4-init-activate-start.sh "<reviewer>" "<IDEA-110 A1 reference>" existing-quarantined`.
This skips only `init` and runs the normal reviewed `activate`; an already active run or a different registered
build still refuses. Do not delete/recreate the database or reset attempt history. With a genuinely new database,
omit that argument to retain init then activate. Then follow S2, P5, P6 and the read-only J checks below.
This document does not execute any of those host steps.

## Timing (read first)

The windows are fixed (IDEA-110 W2, Keith 2026-10-28 SGT). They don't depend on when the install is prepared.

| Window | UTC, Oct 28 | SGT, Oct 28 |
|---|---|---|
| Buy | 04:00 to 06:00 | 12:00 to 14:00 |
| Self-check flat by | 07:00 | 15:00 |
| Terminal flatten | from 07:01 | from 15:01 |
| Signing ends | 08:00 | 16:00 |

- **Finish P6 before 06:00Z (14:00 SGT).** The whole install has to be done by then: caps/services assembly, A1, P2–P3, S1, P4 → S2 → P5 → P6. P6 can finish before 04:00Z; the run then waits and buys at 04:00Z. A start after 06:00Z buys nothing: the self-check becomes `EXPIRED` at 07:00Z, and the run only flattens.
- **Preparation is refused at or after 06:00Z.**
- Everything ends by 08:00Z, before the F-127 pause (10:00Z).

## Pins

| Item | Value |
|---|---|
| Source profile | FS1 recovery `b8ba06e2…`; only the IDEA-110 fields change |
| Policy | `larp-final-selfcheck-temp-v1` (FINAL / live). The profile is the same whenever it is prepared; A1 approves the hash the preparation prints |
| Self-check | SKHYB, `pay_units` 900000 (0.90 USDT). Its own floor is 1000bp: 0.589 USDT at the pinned costs. Any BUY with cash + fee ≥ 1 USDT is refused |
| Run / database | `larp-final-selfcheck-temp` / `larp_final_selfcheck`. FS1's `larp-final-fs1` / `larp_final` are untouched |
| Wallet directories | `/var/lib/larp-runtime/final-<wallet>-selfcheck-temp/{ai-seeds,nonce}`, not FS1's |
| Routing, history, router policy | the same pins as FS1 (`9b86c732…`, the TH-01 history, `05759e90…`) |

## Order

1. **W0 (read-only).** Run the chain monitor on the final wallet. Confirm:
   - zero stock, dust included;
   - no allowance;
   - the BNB from the organiser's 30 USDT → BNB swap;
   - the actual USDT.
2. **D1.** Create the empty `larp_final_selfcheck` database using the existing procedure, with that explicit name.
3. **M1/M2.** Build and upload the bundle from the commit that contains IDEA-110.
4. **M3 (prepare).** From the release checkout:
   ```bash
   python -m tools.deploy.prepare_fs1 --temp-self-check \
     --terraform-output "$TF_OUTPUT" --wallet "$FINAL_WALLET" --capture "$FINAL_CAPTURE" \
     --token-history-config "$TOKEN_HISTORY" --balance-rpc-config "$RPC_CONFIG" \
     --rds-ca-sha256 "$CA_SHA256" --build-id "$BUILD" --model-adoption-ref "$MODEL_ADOPTION_REF" \
     --out deploy/activation/selfcheck-temp-prepared
   ```
   The expected output is `TEMP_SELF_CHECK_PREPARED_REQUIRES_APPROVAL`, together with `profile_sha256`, `run_id` and `activation_self_check` (buy 04:00–06:00Z). Record all of them. Then follow the FS1 sheet's `--caps-inputs`/`--services-out` step, adding `--temp-self-check`: take fresh final-wallet quotes for a 0.90 USDT SKHYB BUY and its full exit, run within the capture's validity, and write to a new `--out`.

   The rerun produces byte-identical profile bytes, so the caps inputs pin the same hash.
5. **A1.** Isaac/Keegan approve, in IDEA-110:
   - the exact profile hash;
   - the signer hash;
   - the caps coverage;
   - the window (buy 04:00–06:00Z Oct 28).

   The approval must also confirm that the signer's CAP-02 policy accepts a sub-1-USDT leg.
6. **M4 / P2 / P3 / S1 / B1 / S1b.** As in the FS1 sheet, with these outputs.
7. **P4 → S2 → P5 → P6.** Use this folder's [P4](host/p4-init-activate-start.sh). It checks the temp run, database and policy. P5 and P6 are FS1's ([P5](../final-fs1/host/p5-start-execution.sh), [P6](../final-fs1/host/p6-start-runtime.sh)).
8. **J (read-only).** Use `checks/trading-status.sh` and the chain monitor. Confirm:
   - one SKHYB BUY (`ACTIVATION_SELF_CHECK_BUY`) with its `tx_hash` in a round log;
   - a mandatory SELL (`ACTIVATION_SELF_CHECK`);
   - risk state `activation_self_check: DONE`;
   - receiver ACKs and an empty uploader spool.
9. **X (retire) after signing ends at 08:00Z.** Stop runtime, then execution and signer. Stop the uploader last, only with an empty spool.
10. **Final checks.** Run the chain monitor again: zero stock, dust included, and no allowance. FS1's preparation refuses anything else. If an allowance remains, record it and never revoke it by hand. The zero-allowance revoke route (OBS03-B1, PR310) is merged but not yet live-qualified, so this run is also its first live final-wallet check.

## Not covered

- The organisers' registration of this build: commit, manifest and version event before any trading (F-125).
- How this extra version event relates to FS1's.
- FS1's own built-in 32-USDT self-check, which is unchanged.

Those are owner decisions, recorded in IDEA-110.

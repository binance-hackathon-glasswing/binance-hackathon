# Temporary final-wallet self-check (IDEA-110 TEMP-SC): run sheet

This sheet installs a **temporary** run on the final wallet. It is **not FS1**:
- one buy of 0.90 USDT of SKHYB;
- the automatic sell of the whole position;
- nothing else.

It answers F-125's "end-to-end self-check with a real final-wallet trade" at the smallest size Keith asked for (2026-10-28 SGT). This sheet is a plan: no host, wallet, key or approval action has been taken. Times are UTC (SGT = UTC+8).

## Timing (read first)

`prepare_fs1 --temp-self-check` stamps the profile at the moment it runs. With T = that time rounded up to the next whole minute:

| Window | Time |
|---|---|
| Buy | T to T+1h |
| Self-check flat by | T+2h |
| Terminal flatten | from T+2h+1min |
| Signing ends | T+3h |

- **The whole install must finish inside the buy window.** That covers the caps/services assembly, A1, P2–P3, S1, P4 → S2 → P5 → P6. A start after T+1h buys nothing: the self-check becomes `EXPIRED` at T+2h, and the run only flattens.
- **Prepare as late as possible**, once everything else is staged.
- **The tool refuses a preparation after 2026-10-28T07:00Z**, because T+3h must be at or before the F-127 pause (10:00Z). Preparing later gives you a refusal, not a shorter window.

## Pins

| Item | Value |
|---|---|
| Source profile | FS1 recovery `b8ba06e2…`; only the IDEA-110 fields change |
| Policy | `larp-final-selfcheck-temp-v1` (FINAL / live). The profile hash is new for each stamp, so the hash printed by the preparation is what A1 approves |
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
4. **M3 (prepare and stamp).** From the release checkout:
   ```bash
   python -m tools.deploy.prepare_fs1 --temp-self-check \
     --terraform-output "$TF_OUTPUT" --wallet "$FINAL_WALLET" --capture "$FINAL_CAPTURE" \
     --token-history-config "$TOKEN_HISTORY" --balance-rpc-config "$RPC_CONFIG" \
     --rds-ca-sha256 "$CA_SHA256" --build-id "$BUILD" --model-adoption-ref "$MODEL_ADOPTION_REF" \
     --out deploy/activation/selfcheck-temp-prepared
   ```
   The expected output is `TEMP_SELF_CHECK_PREPARED_REQUIRES_APPROVAL`, together with `profile_sha256`, `run_id`, `temp_stamp` and the stamped `activation_self_check`. Record all of them. Then follow the FS1 sheet's `--caps-inputs`/`--services-out` step, adding `--temp-self-check --temp-stamp "<printed temp_stamp>"`: take fresh final-wallet quotes for a 0.90 USDT SKHYB BUY and its full exit, run within the capture's validity, and write to a new `--out`.

   **Reuse the stamp.** `--temp-stamp` makes the rerun produce byte-identical profile bytes, so the caps inputs pin the same hash. A stamp more than 30 minutes old is refused. Without `--temp-stamp`, a rerun in a later minute restamps the window and changes the hash.
5. **A1.** Isaac/Keegan approve, in IDEA-110:
   - the exact profile hash;
   - the signer hash;
   - the caps coverage;
   - the stamped window.

   The approval must also confirm that the signer's CAP-02 policy accepts a sub-1-USDT leg.
6. **M4 / P2 / P3 / S1 / B1 / S1b.** As in the FS1 sheet, with these outputs.
7. **P4 → S2 → P5 → P6.** Use this folder's [P4](host/p4-init-activate-start.sh). It checks the temp run, database and policy. P5 and P6 are FS1's ([P5](../final-fs1/host/p5-start-execution.sh), [P6](../final-fs1/host/p6-start-runtime.sh)).
8. **J (read-only).** Use `checks/trading-status.sh` and the chain monitor. Confirm:
   - one SKHYB BUY (`ACTIVATION_SELF_CHECK_BUY`) with its `tx_hash` in a round log;
   - a mandatory SELL (`ACTIVATION_SELF_CHECK`);
   - risk state `activation_self_check: DONE`;
   - receiver ACKs and an empty uploader spool.
9. **X (retire) after signing ends at T+3h.** Stop runtime, then execution and signer. Stop the uploader last, only with an empty spool.
10. **Final checks.** Run the chain monitor again: zero stock, dust included, and no allowance. FS1's preparation refuses anything else. If an allowance remains, record it and never revoke it by hand. The zero-allowance revoke route (OBS03-B1, PR310) is merged but not yet live-qualified, so this run is also its first live final-wallet check.

## Not covered

- The organisers' registration of this build: commit, manifest and version event before any trading (F-125).
- How this extra version event relates to FS1's.
- FS1's own built-in 32-USDT self-check, which is unchanged.

Those are owner decisions, recorded in IDEA-110.

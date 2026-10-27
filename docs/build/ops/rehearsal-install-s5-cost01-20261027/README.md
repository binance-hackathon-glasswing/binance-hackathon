# Yao: run 8 revision 2 deployment package

Prepared for Yao-authorized S5-COST02 deployment; record actual installation and launch separately. This is a fresh S5 small-wallet development rehearsal with the
integrated FS1 fixes listed in **FS1_FIX_AUDIT.md**. It preserves the first run8 and uses a new identity:

| Binding | Pinned value |
|---|---|
| Source release | `3ae830981b9ce1c4b80a46dbeb086825d91ae7ec` |
| New run | `larp-dev-rehearsal-20261027-s5-cost01` |
| New database | `larp_rehearsal8cost01` |
| Source run / database | `larp-dev-rehearsal-20261027-s5-small` / `larp_rehearsal8` |
| Profile file SHA256 | `f26c332aad317631ee7308a6d7669761104e2b4f8d1864300a5d6ff40e487dec` |
| StrategyProfile.v1 | `a40231c8f52e0185d0e45efaf75797b78ca769afc09b977c6b14bd40bccf63fb` |
| Buy cutoff | Oct27 22:00 SGT (14:00 UTC) |
| Flatten starts | Oct27 23:00 SGT (15:00 UTC) |
| Signing ends | Oct28 00:00 SGT (Oct27 16:00 UTC) |

Start when qualified, before the buy cutoff. If the window has expired, STOP: a new profile, coverage and exact
signer approval are required. The package never extends the window automatically. S5 retains its approved
200bp small-wallet entry economics, 3.192045-USDT minimum, 20bp slippage, FS1 model routing/history/authority and
risk/gas limits. This is not equal-cost FS1 performance evidence. No transfer/top-up or manual transaction step.

## Files and private prerequisites

Extract the delivered operator archive outside tracked source, e.g. `$HOME/larp-s5-cost01-20261027`.
It contains this folder plus the original `bundle/larp-3ae830981b9c-x86_64.tar.gz`, checksum and release manifest.
The Git PR contains scripts and public pins only; private inputs must remain on Yao's configured machine.

Use a Python3.12 virtual environment with the release's `deploy/requirements-test.lock`, AWS CLI with
Session Manager plugin, `git`, `bash`, `lsof`, and Terraform1.13.5. Keep AWS profile `larp` in ap-southeast-2.
Use the existing private Terraform backend/input files; never create a replacement stack.

```bash
export LARP_REPO="$HOME/binance-hackathon"       # existing configured repository
export LARP_PY="$HOME/larp-monitor-venv/bin/python"
export LARP_ENV_FILE="$LARP_REPO/.env"           # existing private provider credentials
export TOKEN_HISTORY="$PWD/inputs/token-history.json"
export OLD_BINDINGS="$LARP_REPO/deploy/activation/rehearsal-install-s5-small-20261027/private/bindings-bdd515f.json"
export OLD_SIGNER="$LARP_REPO/deploy/activation/rehearsal-install-s5-small-20261027/private/signer.json"
export SCOPE_CONFIRMATION="IDEA-104 S5-NEXT01 Keegan Oct27"
```

`OLD_BINDINGS` and `OLD_SIGNER` must point to the actual original run8 files, wherever Yao retained them; the
example paths are selectors, not files included in the archive. M3/M4 verify their contents, not their names.
The existing private `deploy/activation/tf-output.json`, `balance-rpc/selected-providers.json` and
`gate-a-prepared-20261017/{runtime.json,evidence.env}` are also needed. They supply the real wallet, database,
RPC, service-secret references and SEC contact without publishing them. Do not paste keys into chat or scripts.
The existing signer wallet key stays in its root-only location; S2 validates it without printing it.

## Operator sequence

Stop at any nonzero exit or missing DONE marker. Keep `results/` and `private/` private. Do not run every line
as one unattended batch. Exact signer/config acceptance follows the fresh M3 assembly, before retirement.

1. **Stage / verify locally.** `"$LARP_PY" stage.py` verifies the delivered archive and all256 member hashes,
   profile/history pins and exact ancestor fixes, extracts the bundle, and creates the exact release checkout and selects its pinned pushed branch (required by input capture).
   It does not rebuild the bundle or contact AWS. Run `source pins.sh` afterward, then
   `"$LARP_PY" -I mac/00-inputs-check.py` to check private input selectors and source-run metadata without printing them.
2. **Operator/environment checks.** `bash mac/signer-reach.sh`; primary and signer must both be SSM Online for
   installation. Restore T1 temporarily using `enable_signer_provisioning=true` in the existing Terraform inputs,
   the refreshing-credential plan/apply sequence in the pinned checkout's `docs/build/AWS_RUNBOOK.md`, and a reviewed
   plan limited to the eight T1 resources. Do not rebuild/reboot trading hosts as an automatic repair.
3. **Source idle / database readiness.** Read `checks/trading-status.sh`, `checks/db-diagnose.sh`,
   `checks/db-top-queries.sh` and `checks/db-sizes.sh` using SSM. The source planner must remain stopped; reconcile
   possible submissions and held reservations. Apply/verify DB1/DB2/alarms/windows and any approved maintenance
   before a new run. The readback, not the Terraform source alone, proves infrastructure readiness.
4. **D1 / new database.** `bash mac/d1-create-db.sh`. Opens a temporary primary-to-RDS tunnel, creates only
   `larp_rehearsal8cost01`, applies pinned migrations/roles and verifies pg_stat_statements. Refuses a database with a run.
5. **M2 / upload release.** `bash mac/m2-upload-bundle.sh`. Uses the delivered pinned bundle, not latest HEAD.
6. **M3 / capture + coverage + signer candidate.** `bash mac/m3-recapture-assemble.sh`. Reads the source run8,
   verifies capture hash `763e2746850cbed5a4a6f608fc235e6ed87a1284265bd6f9d8cfdda1e5c46a8d`, and requires fresh
   holdings/quotes/nonce, no pending execution and zero held reservation units. Released zero-unit rows are fine.
   Records `ASSEMBLED_REQUIRES_APPROVAL` and `numeric_status=COVERED`; retain its printed timestamp and signer hash.
   The recorded 15.441878-USDT allowance may be inherited only under the existing approved zero-only recovery
   scope and reserved eight-child budget. Do not manually revoke it or reactivate expired terminal intents.
7. **A1 / exact acceptance.** Isaac/Keegan accept the selected profile, capture/coverage, new exact signer hash,
   release/config scope and remaining measured risks. Isaac's previously relayed PR310 approach acceptance does
   not substitute for acceptance of fresh exact bindings. No policy/cap widening if M3 refuses.
8. **M4 / package + bind.** `"$LARP_PY" -I mac/m4-prepare.py M3_TIMESTAMP` (use the actual timestamp printed by M3).
   Refuses an M3 review older than300 seconds (rerun M3 if approval/preparation took longer).
   Captures fresh market inputs, prepares new runtime configs, enforces model/history/recovery/router pins,
   checks signer differences against source run8, binds one release.json for both hosts, runs local preflight and
   signer checks, uploads the private transfer package and prints the exact P3/S1 commands. Keep those commands.
9. **Retire source host configs.** `"$LARP_PY" -I ssm_run.py host/r1-retire-primary.sh`, then
   `"$LARP_PY" -I ssm_run.py --signer host/r1-retire-signer.sh`. Both refuse unexpected source-run identities,
   stop/disable services and preserve configs under `/etc/larp-history/bdd515f-<source-run>/`; never delete run8 DB,
   evidence, logs or provider budget ledger. Keep the existing root-only key on the signer.
10. **P2 / install exact release on both hosts.**
    ```bash
    "$LARP_PY" -I ssm_run.py host/p2-provision.sh primary @artifact_bucket "$BUNDLE" "$BUNDLE_SHA256" "$PROVISION_SHA256"
    "$LARP_PY" -I ssm_run.py --signer host/p2-provision.sh signer @artifact_bucket "$BUNDLE" "$BUNDLE_SHA256" "$PROVISION_SHA256"
    ```
11. **P3 / S1.** Run the exact hash-pinned P3 and S1 commands printed by M4. They install the same bound manifest,
    verify routes/time/roles, and check runtime, executor and signer without starting trading.
12. **B1 / S1b.** `"$LARP_PY" -I ssm_run.py host/b1-model-budget-check.sh` and
    `"$LARP_PY" -I ssm_run.py --signer host/s1b-credential-mode-test.sh`. Preserve provider spend; stop on
    missing keys, exhausted budget, changed wallet or credential-mode refusal.
13. **P4 → S2 → P5 → P6** (strict order):
    ```bash
    : "${REVIEWER:?set the actual A1 reviewer}" "${APPROVAL_REF:?set the recorded exact-hash A1 reference}"
    "$LARP_PY" -I ssm_run.py host/p4-init-activate-start.sh "$REVIEWER" "$APPROVAL_REF"
    "$LARP_PY" -I ssm_run.py --signer host/s2-key-check-start-signer.sh
    "$LARP_PY" -I ssm_run.py host/p5-start-execution.sh
    "$LARP_PY" -I ssm_run.py host/p6-start-runtime.sh
    ```
    Substitute the actual recorded A1 reference/reviewer in P4. P4 initializes/activates only the new database,
    starts evidence/delivery; S2 starts signer; P5 starts executor; P6 starts planner. P4/P6 refuse wrong identity,
    profile/build or expired buy windows. Verify every DONE marker, zero restarts and fresh health.
14. **T2 / M9.** After both host checks and healthy startup, set `enable_signer_provisioning=false` and apply the
    reviewed T2 plan. Verify primary SSM remains Online; signer direct SSM loss is then expected. Delete only the
    private transfer prefix printed by M4: `bash mac/m9-cleanup-s3-package.sh EXACT_M4_PREFIX`. The original public
    release bundle remains. Retain private local receipts. Temporary SSM access must not remain enabled for FINAL.

## Live acceptance and failure handling

Use `"$LARP_PY" -I ssm_run.py checks/trading-status.sh` and `checks/primary-status.sh`. Record autonomous BUY/SELL
hashes, quote/approval/retry/signing timings, gas/accounting, reason summaries, real model/history activity, receiver
ACKs, zero residual stock/allowances at completion, and restart/DB metrics. No swap is guaranteed by this package.
A successful cleanup is maintenance, not a trade. A no-trade run does not pass autonomous buy/sell acceptance.

If M3 finds positive reservations or possible submissions, reconcile the existing run using the reviewed runtime
paths; do not edit journals, zero reservation rows manually, reuse a terminal intent, or mask the refusal.
If any post-install check fails, leave the planner stopped, preserve evidence and record the exact failure.
Do not blindly restore old configs or restart source run8 after creating a new version event. No manual wallet
trade, key export or automatic infrastructure replacement is part of this package.

## S5-COST02 adoption

Yao authorized merging PR314 and all package/deployment steps on Oct27. This profile sets the extra USDT cash cushion to0, the independent absolute economic-cost ceiling to0.40USDT, and retains200bp entry,20bp slippage and the existing BNB/action/exit reserves. The19.10USDT per-trade cap is unchanged; without the old0.10USDT cushion its maximum BUY sizing input rises by0.10USDT, subject to fresh exact cash/risk/caps coverage. Normal five-name targets at the observed81.37USDT cash are smaller than that cap. FINAL profiles remain unchanged. All18 earlier audited merge fixes plus PR314 are ancestors of the pinned release.

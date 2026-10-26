# Run 7 run sheet: S5, the FS1 mirror rehearsal on the dev wallet, to Tue Oct 27 12:00 SGT (IDEA-104 R2)

Retire run 6 (`larp-dev-rehearsal-20261026-s4b`, build `7fc9f60`, `larp_rehearsal6`; flat since 2026-10-25 17:21Z) and
install run 7 (`larp-dev-rehearsal-20261026-s5`, database `larp_rehearsal7`) on the **S5 profile `5a5a200a…`** with a
**new build** from canonical that contains FS1's token history (PR295) and S5 R2.

S5 is FS1-R with recovery (`17ab891d…`) on a shorter window. It has FS1's `s1` block (weights 1/5, `KIT_OPEN_STATE`
hours, 5 attempts per discretionary leg), 20 bp slippage, the four PR278-RV01 fields, IDEA-096 recovery gas and FS1's
pinned token history. It runs the deterministic assessor in a SHADOW dev scope, like every signed rehearsal.
**FS1 stays the final strategy;** S5 is never installed for the final run.

**Status: draft for review.** Not approved, built or run. Nothing in this folder has touched a host or the wallet.

| Window (profile) | UTC | SGT |
|---|---|---|
| buys allowed (`trade_after`) | Mon Oct 26 06:00 | Mon 14:00 (already open at install) |
| buys stop (`new_risk_end`) | Mon Oct 26 23:00 | Tue 07:00 |
| sell everything (`flatten_start`) | Tue Oct 27 00:00 | Tue 08:00 |
| signing ends (`signing_end`) | Tue Oct 27 04:00 | **Tue 12:00** |

## What changed against the run-5 sheet (`rehearsal-install-s4-20261025`)

- **Fresh run, no carry-over:** no X1 step; `m4-prepare.py` has no `--carry-over` and refuses any held stock.
- **Token history (FS1, IDEA-103):** M4 needs `TOKEN_HISTORY=<qualified TokenHistoryConfig.v1>`, validates it with the
  release's parser, refuses a synthetic value, passes `--token-history-config` and checks the runtime pin. P3 installs
  `token-history.json` and checks that `larp-runtime` can read it at the pinned hash. Without it, preparation and
  startup refuse (S5R2-3).
- **Opening cash (S5R2-7):** at run 6's closing 81.37 USDT, S5 buys nothing: each 1/5 target (gas excluded) is
  below the 18.64 USDT minimum trade. The first buy needs about 98.31 USDT of cash. B0 tops the wallet up. M3 then
  declares the exact top-up with `--accept-usdt-surplus-units` (S5R2-8), and M4 refuses below 98.32 USDT.
- **M3:** S5 profile and probe `8ba1328f…`; bindings from run 6 (`larp_rehearsal6`) to run 7 (`larp_rehearsal7`).
- **M4:** the signer diff against run 6's `1e052e26…` must be exactly `build_id`, `database_name` and `run_id`.
  Recovery stays on.
- **M1:** requires `larp-s5-rehearsal-v1` in `larp/marketdata/history.py` and the S5 profile `5a5a200a…` at BUILD.
- **R1p/R1s** retire run 6. **D1, P4** and `prepare_rehearsal_db.py` name run 7 and `larp_rehearsal7`. Migrations and
  `roles.sql` are unchanged since RC4 `d03bbb1` (D1 checks).
- **Q1** is supplementary: `quote_check.py` is pinned to run 3's 8 bp (FS1 sheet Q1 note). M3's caps review at the
  S5 profile is the binding check.

**Before starting:** copy this folder to the git-ignored `deploy/activation/` and run everything from there. Host steps
go through `python3.12 -I ssm_run.py [--signer] host/<script> [args]`. Stop at the first step that does not end with
its `*_DONE` line, and keep its `results/` files.

```bash
cp -R docs/build/ops/rehearsal-install-s5-20261026 deploy/activation/ && cd deploy/activation/rehearsal-install-s5-20261026
```

`OLD` below means run 6's folder, `deploy/activation/rehearsal-install-s4b-20261026`.

## Order

| Step | Who / where | Command | Done when |
|---|---|---|---|
| B0 | Yao (wallet owner, dev phase) | Transfer USDT into the dev wallet so it holds **at least 98.32 USDT; about 101.4 USDT (+20) recommended**, for headroom through all five buys. Record the exact amount in micro-USDT as `TOPUP` | chain monitor `--once`: USDT ≥ 98.32, every stock 0, BNB ≥ 0.01536 plus headroom (0.024973 after run 6) |
| TH | Keith (evidence), Yao | write the qualified `TokenHistoryConfig.v1` to `private/token-history.json`: `timestamp_kind` `OPEN`, `timestamp_evidence_sha256` = SHA-256 of the actual hourly OPEN timestamp evidence, and the adjustment version ([contract](../../FS1_TOKEN_HISTORY.md)) | the file parses; no synthetic value (M4 refuses one) |
| — | team | merge PR294 (S5 R2) into canonical, so BUILD contains it | canonical head contains `5a5a200a…` |
| D1 | Yao, Mac | `LARP_PY=<venv> D1_OUT=<repo>/deploy/activation/rehearsal-db-run7 bash mac/d1-create-db.sh` (any time) | `S5-D1` result, `D1_DONE` |
| M1-local | Mac | `PY=<venv>/bin/python RC4=<CI RC4 bundle dir larp-d03bbb16cf51-x86_64> bash mac/m1-local-bundle.sh` (BUILD = canonical after the merge) | S5, history and recovery checks pass; integrity checks pass; `M1_DONE` |
| (M1) | Mac | `[BUILD=<sha>] bash mac/m1-fetch-bundle.sh <run id>`, if a mirror run is made | digest match, `build.env`, `M1_DONE` |
| Q1 | Yao, Mac | `LARP_PY=<venv>/bin/python bash mac/q1-quote-check.sh` (supplementary) | ten lines `VERIFIED_EXECUTABLE`; `Q1_DONE` |
| M2 | Yao, Mac | `bash mac/m2-upload-bundle.sh` | `M2_DONE` |
| M3 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_BINDINGS=$OLD/private/bindings-7fc9f60.json bash mac/m3-recapture-assemble.sh` (run 6 idle, after B0). It passes `--accept-usdt-surplus-units ${TOPUP:-0}` | probe `8ba1328f…`; `ASSEMBLED_REQUIRES_APPROVAL`, `numeric_status: COVERED`; note the stamp and the signer hash |
| A1 | Isaac (relayed); Keegan | Isaac approves profile `5a5a200a…`, probe `8ba1328f…` and the new `signer.json` hash M3 printed. Keegan reviews S5R2-8 and the token-history input | recorded in IDEA-104 |
| R1p | primary | `python3.12 -I ssm_run.py host/r1-retire-primary.sh` (after M3 and A1) | every run-6 unit inactive and disabled, configs in `/etc/larp-history/7fc9f60-larp-dev-rehearsal-20261026-s4b/`, `R1P_DONE` |
| F0d (optional) | Yao (Keegan reviews) | FS1 sheet F0d (IDEA-100 DB1/DB2) here, while no run is active: `terraform apply` of `deploy/aws`, SNS test, one RDS reboot, `CREATE EXTENSION pg_stat_statements`. Only if it can finish well before P4; otherwise leave it to the gap after S5 | `checks/db-top-queries.sh` prints rows |
| P2 | primary | `python3.12 -I ssm_run.py host/p2-provision.sh primary @artifact_bucket $BUNDLE $BUNDLE_SHA256 $PROVISION_SHA256` | `P2_DONE` |
| M4 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_SIGNER=$OLD/private/signer-<run-6 M3 stamp>/signer.json TOKEN_HISTORY=$PWD/private/token-history.json SCOPE_CONFIRMATION="IDEA-104 R2 (<who>, 2026-10-26)" /opt/homebrew/bin/python3.12 -I mac/m4-prepare.py <M3 stamp>` | signer diff is exactly identity; runtime and execution pin `5a5a200a…` with recovery on; runtime pins `token-history.json`; flat book, cash ≥ 98.32 USDT; checks pass; prints P3 and S1 |
| P3 | primary | the P3 command M4 printed | preflight, checks, router policy and token history readable, routes PASS, `P3_DONE` |
| T1 | Yao, Mac | Terraform `enable_signer_provisioning = true` | plan adds only the 8 IDEA-080 resources; signer SSM `Online` (reboot the signer if commands stay `Delayed`) |
| R1s | signer | `python3.12 -I ssm_run.py --signer host/r1-retire-signer.sh` | `larp-signer` inactive and disabled, key file still `600 root:root`, `R1S_DONE` |
| P2s | signer | `python3.12 -I ssm_run.py --signer host/p2-provision.sh signer @artifact_bucket $BUNDLE $BUNDLE_SHA256 $PROVISION_SHA256` | `P2_DONE` |
| S1, S1b | signer | the S1 command M4 printed, with `--signer`; then `--signer host/s1b-credential-mode-test.sh` | signer `check` UNTRUSTED `05759e90…`, routes PASS, `S1_DONE`; `key_loader: PASS`, `S1B_DONE` |
| **P4 → S2 → P5** | primary, signer, primary | **back to back** (buying is already open): `python3.12 -I ssm_run.py host/p4-init-activate-start.sh "<reviewer>" "<IDEA-104 approval ref>"`; `--signer host/s2-key-check-start-signer.sh`; `host/p5-start-execution.sh` | `P4_DONE`; `wallet_matches: true`, `started: true`, `S2_DONE`; `larp-execution active restarts=0`, `P5_DONE` |
| C1 | signer | `python3.12 -I ssm_run.py --signer checks/signer-status.sh` (before T2) | active, 0 restarts, no refusal after the start line |
| T2, M9 | Yao, Mac | Terraform `enable_signer_provisioning = false`; `bash mac/m9-cleanup-s3-package.sh <prefix from M4>` | plan destroys only the 8; `M9_DONE` |
| J | anyone, read-only | `checks/trading-status.sh`, `mac/chain-monitor.py`, `checks/db-top-queries.sh` | see below |

M3's caps review command passes the declared top-up. Before M3, set `TOPUP` to the exact B0 amount in micro-USDT (for
example `TOPUP=20000000`). Leave it unset (0) only if the wallet already matches run 6's ledger, but then S5 cannot buy.

## What run 7 must show (IDEA-104 S5, the FS1 pipeline on the dev wallet)

- **Buys (Mon 14:00 → Tue 07:00 SGT):** the first round after P5 buys. Names are bought one wallet trade at a time
  (serial; IDEA-093 CL-01), up to five, each about 19 USDT at the per-trade cap, with a post-approve swap. Rounds run in
  consecutive 15-minute slots.
- **Token history:** each round journals `PriceSeries.v1` inputs with source hashes, or a bounded
  `history_status`/`quality: UNAVAILABLE`. A cold start may hold the UP default until a complete five-session window
  exists (FS1_TOKEN_HISTORY.md). No provider or exception text appears in decisions.
- **Round logs:** every round log carries `output.reason_summary` and per-order `decision_summaries` (IDEA-099), and
  every swap's `tx_hash`.
- **Flatten (from Tue 08:00 SGT):** every held name becomes a mandatory `TERMINAL_FLATTEN` SELL, spaced one per
  15-minute slot per name (IDEA-102); 16 slots per name before `signing_end`. Every position reaches dust by Tue
  12:00 SGT with balance check `MATCH` and all router allowances 0 (AL9: recovery clears any leftover allowance).
- **Health:** no HALT, quarantine or restarts. On the database, watch CPU credits and the archive backoff (IDEA-100
  DB5 is in this build).

A shortfall is a finding to record in IDEA-104, never a reason to bypass a guard. Stop trading at any time on primary
with `systemctl disable --now larp-execution`, or pause all database clients with `host/pause-primary-db-clients.sh`.
After `signing_end`, retire run 7 with the same R1p/R1s pattern before FS1's final install.

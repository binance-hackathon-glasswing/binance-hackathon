# Signed dev rehearsal, run 2: RC5 install run sheet (IDEA-049-C SJ-10, 2026-10-23)

Run 1 (`larp-dev-rehearsal-20261022`, RC4 `d03bbb1`, database `larp_rehearsal1`) never traded. Its database logins
timed out on `db.t4g.micro` after about 7 hours, and every service restart-looped (SJ-06 J8 incident). RC4 did about
45,000 IAM logins an hour, one per transaction. **RC5** is canonical with IDEA-085 (PR257: pooled connections, one
login per connection, 600 s maximum age; RV1 `eadd5d4`: bounded dead sockets).

A run cannot change build ("Another build is registered for this run"), so RC5 goes in as a **new run**:
- run `larp-dev-rehearsal-20261023`;
- database `larp_rehearsal2`;
- the same dev wallet, key, equal-weight profile `e95d5842…`, CAP-02 policy and router policy `05759e90…`.

Run 1 never traded, so the start is plain USDT and BNB, with no stock positions to carry over.

Between RC4 and RC5 only `larp/runtime/database.py` and `larp/storage/postgres.py` changed. The migrations, `roles.sql`,
the capture probe and the signer assembly are byte-identical.

**Before starting:** copy this folder to the git-ignored `deploy/activation/rehearsal-install-rc5-20261023/` and run
everything from there. Host steps go through `python3.12 -I ssm_run.py [--signer] host/<script> [args]`. Stop at the
first step that does not end with its `*_DONE` line, and keep its `results/` files.

```bash
cp -R docs/build/ops/rehearsal-install-rc5-20261023 deploy/activation/ && cd deploy/activation/rehearsal-install-rc5-20261023
```

`OLD` below means run 1's folder, `deploy/activation/rehearsal-install-20261022`.

## Order

| Step | Who / where | Command | Done when |
|---|---|---|---|
| 0 | — | **skipped (SJ-10-A2, Yao):** no mirror CI for RC5; M1-local replaces M1 | — |
| D1 | Yao, Mac | `bash mac/d1-create-db.sh` (any time; needs no RC5) | `SJ-10-D1 PASS`, `D1_DONE` |
| M1-local | Mac | `PY=<venv>/bin/python RC4=$OLD/bundle/x/larp-d03bbb16cf51-x86_64 bash mac/m1-local-bundle.sh` | integrity checks pass; versus CI RC4 only `release/larp/runtime/database.py` and `release/larp/storage/postgres.py` differ; `BUNDLE.env` differs only in `build_id`; `M1_DONE` |
| (M1) | Mac | `[BUILD=<sha>] bash mac/m1-fetch-bundle.sh <run id>`, only if a mirror run is made later | digest match, `build.env`, `M1_DONE` |
| M2 | Yao, Mac | `bash mac/m2-upload-bundle.sh` | `M2_DONE` |
| M3 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_BINDINGS=$OLD/private/bindings-d03bbb1.json bash mac/m3-recapture-assemble.sh` | `ASSEMBLED_REQUIRES_APPROVAL`, `numeric_status: COVERED`; note the stamp |
| A1 | Isaac (relayed) | confirm the new `signer.json` hash M3 printed | recorded in IDEA-049-C SJ-10-A1 |
| R1p | primary | `python3.12 -I ssm_run.py host/r1-retire-primary.sh` (after M3) | every run-1 unit inactive and disabled, configs in `/etc/larp-history/`, `R1P_DONE` |
| P2 | primary | `python3.12 -I ssm_run.py host/p2-provision.sh primary @artifact_bucket $BUNDLE $BUNDLE_SHA256 $PROVISION_SHA256` | `P2_DONE` |
| M4 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_SIGNER=$OLD/private/signer-20261022T105153Z/signer.json /opt/homebrew/bin/python3.12 -I mac/m4-prepare.py <M3 stamp>` | diff vs `cd0b38b8…` is exactly `build_id`, `database_name`, `run_id`; checks pass; prints P3 and S1 |
| P3 | primary | the P3 command M4 printed | preflight, checks, routes PASS, `P3_DONE` |
| P4 | primary | `python3.12 -I ssm_run.py host/p4-init-activate-start.sh` | run 2 initialized and activated; units active with 0 restarts; `P4_DONE` |
| T1 | Yao, Mac | Terraform `enable_signer_provisioning = true` (run 1 README T1/T2) | plan adds only the 8 IDEA-080 resources; SA9 |
| R1s | signer | `python3.12 -I ssm_run.py --signer host/r1-retire-signer.sh` | `larp-signer` inactive and disabled, key file still `600 root:root`, `R1S_DONE` |
| P2s | signer | `python3.12 -I ssm_run.py --signer host/p2-provision.sh signer @artifact_bucket $BUNDLE $BUNDLE_SHA256 $PROVISION_SHA256` | `P2_DONE` |
| S1 | signer | the S1 command M4 printed, with `--signer` | signer `check` UNTRUSTED `05759e90…`, routes PASS, `S1_DONE` |
| S1b | signer | `python3.12 -I ssm_run.py --signer host/s1b-credential-mode-test.sh` | `key_loader: PASS`, `S1B_DONE` |
| S2 | signer | `python3.12 -I ssm_run.py --signer host/s2-key-check-start-signer.sh` | `wallet_matches: true`, `started: true`, `S2_DONE` |
| P5 | primary | `python3.12 -I ssm_run.py host/p5-start-execution.sh` | `larp-execution active restarts=0`, `P5_DONE` |
| C1 | signer | `python3.12 -I ssm_run.py --signer checks/signer-status.sh` (before T2) | active, 0 restarts, no refusal after the start line |
| T2 | Yao, Mac | Terraform `enable_signer_provisioning = false` | plan destroys only the 8; SA5 (no SSM endpoints); SA9 |
| M9 | Yao, Mac | `bash mac/m9-cleanup-s3-package.sh <prefix from M4>` | `M9_DONE` |
| K | anyone | `bash mac/soak-db-logins.sh 3` at about 1 h and again at 8 h or later | `SOAK_PASS`: under 500 logins per hour, no auth failure |
| J8 | anyone | `checks/trading-status.sh`, `mac/chain-monitor.py` | first agent round: approve, swap, receipts, STORED ACK |

Why this order:
- **D1 has no dependency** on RC5, because the migrations are the same, so it can run while Keegan builds RC5.
- **M3 before R1p.** M3's read-only probe reads run 1's `/etc/larp/runtime.json` on primary.
- **A1 is the approval gate.** M4 enforces the scope mechanically: the candidate may differ from run 1's installed
  `cd0b38b8…` only in `build_id` (RC5), `run_id` and `database_name`, with exactly the new values. Any other difference
  stops M4 and needs a new decision.
- **R1s needs T1.** The signer is reachable only while the IDEA-080 endpoints exist. Until R1s, run 1's signer
  keeps polling `larp_rehearsal1` with RC4's per-transaction logins.
- **The key stays.** R1s moves run 1's configs but leaves `/etc/larp/signer/wallet.key` in place (same dev wallet),
  and `provision.sh` never writes it. S1b and S2 re-check it, so K1 is not repeated.
- **P4, S2 and P5 fail closed**, as in run 1, including the timer exception (SJ-06 P4).

Stop trading at any time on primary with `systemctl disable --now larp-execution` (survives a reboot), or pause all
database clients with `host/pause-primary-db-clients.sh`.

## Live measurement

The chain monitor watches the wallet, not a run, so the one already running keeps working. On the agent side:
`python3.12 -I ssm_run.py checks/trading-status.sh` (it reads `/etc/larp/execution.json`, which is run 2's after P3).

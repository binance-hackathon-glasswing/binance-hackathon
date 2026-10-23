# Signed dev rehearsal, run 3 on S1: RC6 install run sheet (IDEA-049-C SJ-11; drafted 2026-10-23)

**Draft, prepared ahead of the gates. Do not start until all of these hold:**
1. PR262 (IDEA-086 basis check) and PR264 (SJ-11-RH01 S1 rehearsal scope and profile) are merged into canonical.
   M1 refuses a build without both.
2. Yao has confirmed the SJ-11-RH01 scope (deterministic, SHADOW evidence and falsifiers, no hosted models) in a
   record in IDEA-049-C. M4 refuses without `SCOPE_CONFIRMATION` naming that record.
3. Yao has confirmed the run ID. It is proposed here as `larp-dev-rehearsal-20261024`; to change it, edit `RUN` in
   `mac/m3-recapture-assemble.sh`, `mac/m4-prepare.py` and `host/p4-init-activate-start.sh` together. M4 and P4
   cross-check it.
4. Isaac has approved the S1 profile `6bcf1dfb…` and the new `signer.json` that M3 prints (A1).

**Timing.** The REHEARSAL window (RV120-02) allows new risk only until **2026-10-25 00:00Z**. Flattening starts at
Oct 26 00:00Z and signing ends at Oct 26 14:45Z. A run installed after Oct 25 00:00Z can make no entry. Changing the
window would mean a new decision and a new profile hash.

Run 2 (`larp-dev-rehearsal-20261023`, RC5 `d53d1b7`, database `larp_rehearsal2`) cannot enter, because RC5 has no
basis verifier (SJ-10 first trading-status). **RC6** is canonical with IDEA-086 (PR262) and SJ-11-RH01 (PR264). A run
cannot change build, so run 3 is a **new run**:
- run `larp-dev-rehearsal-20261024` (proposed, see above);
- database `larp_rehearsal3`;
- the same dev wallet and key, CAP-02 policy `3241abd3…`, router policy `05759e90…`, untrusted mode and initial gas only;
- **strategy S1**: profile `docs/build/evidence/s1-rehearsal-profile-20261023/rehearsal-s1-deterministic.json`,
  file SHA-256 `6bcf1dfb…`. Its values are IDEA-084 PF-01's, with weights 1/5 (SJ-11-RH01-P1).
- the M3 probe for that profile, `75547c8e…`. It differs from the reviewed equal-weight probe `692787e4…` only in the
  embedded profile line.

Run 2 never entered, so the start is plain USDT and BNB with no stock positions. `gate_a` refuses a wallet that holds
stocks (SJ-09-PC01 C4). `signer.json` carries no profile field, so the candidate differs from run 2's installed
`1a4cda6f…` only in `build_id`, `run_id` and `database_name`. M4 enforces that.

What changed against the RC5 sheet:
- M1 additionally requires PR262 and the pinned S1 profile in BUILD.
- D1 creates `larp_rehearsal3`.
- M3 starts from run 2's bindings and uses the S1 profile, its probe hash, and `review_rehearsal_caps --profile`.
- M4 uses the S1 profile, run 2's signer as the diff base, and the scope confirmation.
- R1p/R1s retire run 2.
- P4 takes the reviewer and the approval record as arguments instead of a pre-written approval.

The other host and check scripts are byte-identical to the RC5 sheet (`tests/runtime/test_run3_sheet.py`).

**Before starting:** copy this folder to the git-ignored `deploy/activation/rehearsal-install-rc6-20261023/` and run
everything from there. Host steps go through `python3.12 -I ssm_run.py [--signer] host/<script> [args]`. Stop at the
first step that does not end with its `*_DONE` line, and keep its `results/` files.

```bash
cp -R docs/build/ops/rehearsal-install-rc6-20261023 deploy/activation/ && cd deploy/activation/rehearsal-install-rc6-20261023
```

`OLD` below means run 2's folder, `deploy/activation/rehearsal-install-rc5-20261023`.

## Order

| Step | Who / where | Command | Done when |
|---|---|---|---|
| D1 | Yao, Mac | `bash mac/d1-create-db.sh` (any time; needs no RC6) | `SJ-11-D1 PASS`, `D1_DONE` |
| M1-local | Mac | `PY=<venv>/bin/python RC4=<CI RC4 bundle dir larp-d03bbb16cf51-x86_64> bash mac/m1-local-bundle.sh` | PR262 and profile checks pass; integrity checks pass; versus CI RC4, only release files changed in `d03bbb1..BUILD` differ; `BUNDLE.env` differs only in `build_id`; `M1_DONE` |
| (M1) | Mac | `[BUILD=<sha>] bash mac/m1-fetch-bundle.sh <run id>`, if a mirror run is made | digest match, `build.env`, `M1_DONE` |
| M2 | Yao, Mac | `bash mac/m2-upload-bundle.sh` | `M2_DONE` |
| M3 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_BINDINGS=$OLD/private/bindings-d53d1b7.json bash mac/m3-recapture-assemble.sh` | probe `75547c8e…`; `ASSEMBLED_REQUIRES_APPROVAL`, `numeric_status: COVERED` against S1's sizes; note the stamp |
| A1 | Isaac (relayed) | approve profile `6bcf1dfb…` and the new `signer.json` hash M3 printed | recorded in IDEA-049-C SJ-11 |
| R1p | primary | `python3.12 -I ssm_run.py host/r1-retire-primary.sh` (after M3) | every run-2 unit inactive and disabled, configs in `/etc/larp-history/`, `R1P_DONE` |
| P2 | primary | `python3.12 -I ssm_run.py host/p2-provision.sh primary @artifact_bucket $BUNDLE $BUNDLE_SHA256 $PROVISION_SHA256` | `P2_DONE` |
| M4 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_SIGNER=$OLD/private/signer-20261023T043528Z/signer.json SCOPE_CONFIRMATION="<record>" /opt/homebrew/bin/python3.12 -I mac/m4-prepare.py <M3 stamp>` | diff vs `1a4cda6f…` is exactly `build_id`, `database_name`, `run_id`; runtime and execution pin `6bcf1dfb…`; checks pass; prints P3 and S1 |
| P3 | primary | the P3 command M4 printed | preflight, checks, routes PASS, `P3_DONE` |
| P4 | primary | `python3.12 -I ssm_run.py host/p4-init-activate-start.sh "<reviewer>" "<run-3 approval record>"` | run 3 initialized and activated; units active with 0 restarts; `P4_DONE` |
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
| K | anyone | `bash mac/soak-db-logins.sh 3` at about 1 h | under 500 logins per hour, no auth failure |
| J | anyone | `checks/trading-status.sh`, `mac/chain-monitor.py` | first S1 entry: a BUY intent, approve, swap, receipts, STORED ACK |

Why this order is the same as the RC5 sheet's:
- **M3 before R1p:** M3's read-only probe reads run 2's `/etc/larp/runtime.json` on primary.
- **A1 is the approval gate.** M4 enforces the scope mechanically.
- **R1s needs T1:** the signer is reachable only while the IDEA-080 endpoints exist. Until R1s, run 2's signer keeps
  polling `larp_rehearsal2`.
- **The key stays:** R1s moves run 2's configs but leaves `/etc/larp/signer/wallet.key` in place (same dev wallet).
  S1b and S2 re-check it.
- **P4, S2 and P5 fail closed**, as in runs 1 and 2.

**What run 3 can show (SJ-09-PC01 C6, accepted):** S1's entries at the 95% level (five buys of about 19 USDT),
sessions, the flatten from Oct 26, and the deterministic limiter. At this size it cannot show a trend-guard trim.

Stop trading at any time on primary with `systemctl disable --now larp-execution` (survives a reboot), or pause all
database clients with `host/pause-primary-db-clients.sh`.

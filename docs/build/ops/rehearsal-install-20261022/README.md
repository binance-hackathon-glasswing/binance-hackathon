# Signed dev rehearsal: install run sheet (IDEA-049-C SJ-06, 2026-10-22)

Installs run `larp-dev-rehearsal-20261022` (database `larp_rehearsal1`, already created in SJ-04-DB01) on the
mirror-CI build of canonical after PR243 (LV-01), and turns signing on for the **dev wallet**. The agent makes
every trade itself: no person picks or submits a trade (never-do #1). The profile allows the first buy from
**2026-10-23 00:00 UTC**; new risk ends Oct 25 00:00, flatten from Oct 26 00:00, signing ends Oct 26 14:45 UTC.

These scripts hold no secrets, database hosts or RPC URLs. Those are read at run time from git-ignored files on
Yao's Mac (`.env`, `deploy/activation/tf-output.json`, `deploy/activation/balance-rpc/selected-providers.json`,
`deploy/activation/gate-a-prepared-20261017/`, the SJ-04 `bindings.json`).

**Before starting:** copy this folder to the git-ignored `deploy/activation/rehearsal-install-20261022/` and run
everything from there. Results, the bundle and `private/` land next to the scripts; host output can name the
database endpoint, so none of it may be committed.

```bash
cp -R docs/build/ops/rehearsal-install-20261022 deploy/activation/ && cd deploy/activation/rehearsal-install-20261022
```

Host steps go through `python3.12 -I ssm_run.py [--signer] host/<script> [args]`. `@artifact_bucket` is resolved
locally and never printed. Re-run `aws login --profile larp --region ap-southeast-2` when the session expires.

## Order

Stop at the first step that does not end with its `*_DONE` line, and keep its `results/` files.

| Step | Who / where | Command | Done when |
|---|---|---|---|
| 0 | Yao, Mac | `gh pr merge 243 --merge`, then `git fetch origin && git push mirror origin/codex/system-testing-20261012:refs/heads/codex/system-testing-20261012` | mirror CI run green on all four jobs |
| M1 | Mac | `bash mac/m1-fetch-bundle.sh <mirror run id>` | `build.env` written, `M1_DONE` |
| M1′ | Mac (instead of 0/M1 when CI is skipped, SJ-06-A1) | `PY=<venv>/bin/python RC3A=<extracted RC3a bundle> bash mac/m1-local-bundle.sh` | differs from RC3a only in files changed since `fa1b6c9`; `M1_DONE` |
| M2 | Yao, Mac | `bash mac/m2-upload-bundle.sh` | `M2_DONE` |
| M3 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_BINDINGS=<SJ-04 bindings.json> bash mac/m3-recapture-assemble.sh` | `ASSEMBLED_REQUIRES_APPROVAL`, `numeric_status: COVERED`; note the stamp |
| P1 | primary | `python3.12 -I ssm_run.py host/p1-preserve-trial.sh` | `P1_DONE` |
| P2 | primary | `python3.12 -I ssm_run.py host/p2-provision.sh primary @artifact_bucket $BUNDLE $BUNDLE_SHA256 $PROVISION_SHA256` (values from `build.env`) | `P2_DONE` |
| M4 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_SIGNER=<SJ-04 signer.json> /opt/homebrew/bin/python3.12 -I mac/m4-prepare.py <M3 stamp>` | signer diff is `build_id` only, bind and signer check pass; it prints the P3 and S1 commands |
| P3 | primary | the P3 command M4 printed | preflight, `service check`, execution `check`, routes PASS, `P3_DONE` |
| P4 | primary | `python3.12 -I ssm_run.py host/p4-init-activate-start.sh` | run initialized and activated; evidence, uploader, runtime active; execution inactive |
| T1 | Yao, Mac | Terraform: `enable_signer_provisioning = true` (below) | apply done; SSM session to `primary` still works (SA9) |
| P2s | signer | `python3.12 -I ssm_run.py --signer host/p2-provision.sh signer @artifact_bucket $BUNDLE $BUNDLE_SHA256 $PROVISION_SHA256` | `P2_DONE` |
| S1 | signer | the S1 command M4 printed, with `--signer` | preflight, signer `check` (UNTRUSTED `05759e90…`), routes PASS (SA4), `S1_DONE` |
| K1 | **Isaac**, interactive SSM | key placement (below) | `/etc/larp/signer/wallet.key` exists, root `0600` |
| S2 | signer | `python3.12 -I ssm_run.py --signer host/s2-key-check-start-signer.sh` | `wallet_matches: true`, signer `started: true`, `swap_decoder: UNTRUSTED` |
| P5 | primary | `python3.12 -I ssm_run.py host/p5-start-execution.sh` | `larp-execution active`, no exit 2/4 |
| T2 | Yao, Mac | Terraform: `enable_signer_provisioning = false` (below) | no signer endpoints left (SA5); signer keeps running (it reaches only the database) |
| M9 | Yao, Mac | `bash mac/m9-cleanup-s3-package.sh <prefix from M4>` | `M9_DONE` |
| C | anyone | `python3.12 -I ssm_run.py checks/primary-status.sh` | after Oct 23 00:00 UTC: the first agent round, approve and swap |

Why this order:
- **M3 runs before P1/P2.** Its read-only probe reads the retired trial's `/etc/larp/runtime.json` and
  `/opt/larp/current` on primary. M3 also re-checks every quote, holding and allowance within 300 s. That is the
  pre-install recapture SJ-04-OA01 requires.
- **M4 needs P2's new build on primary only for P3**; it binds `release.json` on the Mac from the verified bundle.
  Both hosts install the **same** `release.json`. The signer refuses unless its manifest is byte-identical to the
  one the run registered at P4.
- **P4 before S2.** The signer's `run` checks the run's registered version, which P4 records.
- **P5 after S2.** Execution waits for signatures; starting it first would only time requests out.

## T1 / T2: signer provisioning access (IDEA-080)

Set `enable_signer_provisioning = true` (T1) or `false` (T2) in `deploy/aws/development.tfvars`, then plan and
apply with the refreshing-credential subshell from `docs/build/AWS_RUNBOOK.md` (Gate A plan/apply blocks). Review
that the plan only adds (T1) or removes (T2) the three SSM interface endpoints, their security group and its two
rules. Costs about $0.01 per endpoint-hour. After T2, record the time in IDEA-080 (SA5).

## K1: key placement (Isaac only)

Isaac holds the dev wallet key. It goes only to `/etc/larp/signer/wallet.key` (root, `0600`), never to S3, Secrets
Manager, the repo, chat or shell history (SA6). The file holds one line: the `0x…` hex private key.

```bash
aws ssm start-session --profile larp --region ap-southeast-2 --target i-0f8fe5d5fe5ccba36
```

In the session:

```bash
sudo -i
set +o history
umask 077
read -rs K && printf '%s\n' "$K" > /etc/larp/signer/wallet.key && unset K
chown root:root /etc/larp/signer/wallet.key && chmod 0600 /etc/larp/signer/wallet.key
ls -l /etc/larp/signer/wallet.key
exit
```

`read -rs` does not echo the pasted key. Then run S2, which checks the file and the wallet match without printing
the key.

## If something fails

- **Before P4:** nothing is activated. Fix the cause and re-run the step. P3/S1 refuse to overwrite installed
  files: move them to `/root/` first.
- **After P4:** the run exists in `larp_rehearsal1`. `activate` refuses another build for it (never-do #5), so a new
  build needs a new database.
- **Stop trading:** `systemctl stop larp-execution` on primary stops new submissions. The agent's own HALT and
  quarantine paths still apply; an unresolved fill quarantines the run.
- **Gas:** initial gas only (no agent top-ups). F-120 allows the manual MetaMask seed only before a wallet's first
  agent trade, so a mid-run top-up is a human wallet action. If the low-gas alarm fires on this dev wallet: stop
  `larp-execution`, top up, write the funding note, record it as an incident (deviation), take a fresh balance
  read, then restart execution. Never do this on the final wallet during the scored run (F-114).

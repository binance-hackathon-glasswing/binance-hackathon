# Run 5 run sheet: S4 carry-over flatten test (IDEA-097)

Retire run 4 (`larp-dev-rehearsal-20261024-s2`, RC7 `2d16007`, `larp_rehearsal4`) and install run 5
(`larp-dev-rehearsal-20261025-s4`, database `larp_rehearsal5`) on the S4 profile `58b31806…`. Run 5:
- starts from run 4's exact on-chain book, carried at run 4's cost;
- is already inside the terminal flatten, so it never buys;
- sells every held name with IDEA-096 allowance recovery on, clearing run 4's leftover SKHYB router allowance itself.

**Status: draft for review.** Not approved, built or run. Nothing in this folder has touched a host.

## What changed against the RC7 sheet

- **New:** `host/x1-export-holdings.sh` and `mac/x1-save-export.py` (X1) export run 4's book after R1p.
- **M3:** probe `379c476b…`, S4 profile, run-4 bindings, `--allowance-recovery` (the leftover allowance is accepted;
  execution and the signer policy opt in).
- **M4:** S4 profile, X1 export into `prepare` (`--carry-over`), `--allowance-recovery`, and recovery required in
  runtime, execution and signer. The signer diff against run 4's `56e029af…` is exactly `build_id`, `database_name`,
  `run_id`, and `signing_policy.allowance_recovery` switched on.
- **M1:** also requires `larp/strategy/carry_over.py` and recovery in `larp/marketdata/quote_verifier.py`.
- **R1p/R1s** retire run 4. **D1, P4** and `prepare_rehearsal_db.py` name run 5 and `larp_rehearsal5`.
- Everything else is the RC7 sheet's (with PR282's allowance columns in `checks/trading-status.sh` and
  `mac/chain-monitor.py`).

**Before starting:** copy this folder to the git-ignored `deploy/activation/` and run everything from there. Host steps
go through `python3.12 -I ssm_run.py [--signer] host/<script> [args]`. Stop at the first step that does not end with
its `*_DONE` line, and keep its `results/` files.

```bash
cp -R docs/build/ops/rehearsal-install-s4-20261025 deploy/activation/ && cd deploy/activation/rehearsal-install-s4-20261025
```

`OLD` below means run 4's folder, `deploy/activation/rehearsal-install-rc7-20261024`.

## Order

| Step | Who / where | Command | Done when |
|---|---|---|---|
| B0 | Yao (wallet owner) | **Done 2026-10-25 under Yao's dev-phase decision (IDEA-097 RV01-2 resolution, SKILL.md §0.3 #1): the wallet held 0.025178 BNB at 13:17Z.** Add BNB to the dev wallet: at least 0.0102 BNB more, so the wallet holds about 0.02 BNB | the chain monitor shows BNB ≥ 0.01536 plus headroom. Recovery's exit reserve is 0.01536 BNB (5 × 2 × 0.001536); Gate B and caps review refuse below it |
| D1 | Yao, Mac | `bash mac/d1-create-db.sh` (any time) | `S4-D1 PASS`, `D1_DONE` |
| M1-local | Mac | `PY=<venv>/bin/python RC4=<CI RC4 bundle dir larp-d03bbb16cf51-x86_64> bash mac/m1-local-bundle.sh` (BUILD = canonical after this PR merges) | S4, carry-over and recovery checks pass; integrity checks pass; `M1_DONE` |
| (M1) | Mac | `[BUILD=<sha>] bash mac/m1-fetch-bundle.sh <run id>`, if a mirror run is made | digest match, `build.env`, `M1_DONE` |
| Q1 | Yao, Mac | `LARP_PY=<venv>/bin/python bash mac/q1-quote-check.sh` | ten lines `VERIFIED_EXECUTABLE`; `Q1_DONE`. The SELL side is the one S4 uses |
| M2 | Yao, Mac | `bash mac/m2-upload-bundle.sh` | `M2_DONE` |
| M3 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_BINDINGS=$OLD/private/bindings-2d16007.json bash mac/m3-recapture-assemble.sh` (run 4 idle, after B0) | probe `379c476b…`; `ASSEMBLED_REQUIRES_APPROVAL`, `numeric_status: COVERED`; note the stamp |
| A1 | Isaac (relayed); Keegan | Isaac approves profile `58b31806…`, probe `379c476b…` and the new `signer.json` hash M3 printed (recovery on). Keegan reviews the carry-over accounting and the recovery gas | recorded in IDEA-097 |
| R1p | primary | `python3.12 -I ssm_run.py host/r1-retire-primary.sh` (after M3 and A1) | every run-4 unit inactive and disabled, configs in `/etc/larp-history/2d16007-larp-dev-rehearsal-20261024-s2/`, `R1P_DONE` |
| X1 | primary, then Mac | `python3.12 -I ssm_run.py host/x1-export-holdings.sh`, then `/opt/homebrew/bin/python3.12 -I mac/x1-save-export.py` (before P2) | `X1_DONE`. The saved export shows GOOGLB, NVDAB, SKHYB and TSLAB units equal to the chain, positive cost, no reservations |
| P2 | primary | `python3.12 -I ssm_run.py host/p2-provision.sh primary @artifact_bucket $BUNDLE $BUNDLE_SHA256 $PROVISION_SHA256` | `P2_DONE` |
| M4 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_SIGNER=$OLD/private/signer-20261024T052155Z/signer.json SCOPE_CONFIRMATION="IDEA-097 Decision (Yao, 2026-10-25)" /opt/homebrew/bin/python3.12 -I mac/m4-prepare.py <M3 stamp>` | signer diff is exactly identity and `signing_policy` recovery; runtime and execution pin `58b31806…`, with recovery on; the package pins the X1 export; the starting book equals it; checks pass; prints P3 and S1 |
| P3 | primary | the P3 command M4 printed | preflight, checks, router policy readable, routes PASS, `P3_DONE` |
| P4 | primary | `python3.12 -I ssm_run.py host/p4-init-activate-start.sh "<reviewer>" "<run-5 approval record>"` | run 5 initialized and activated; units active with 0 restarts; `P4_DONE` |
| T1 | Yao, Mac | Terraform `enable_signer_provisioning = true` | plan adds only the 8 IDEA-080 resources; SA9 |
| R1s | signer | `python3.12 -I ssm_run.py --signer host/r1-retire-signer.sh` | `larp-signer` inactive and disabled, key file still `600 root:root`, `R1S_DONE` |
| P2s | signer | `python3.12 -I ssm_run.py --signer host/p2-provision.sh signer @artifact_bucket $BUNDLE $BUNDLE_SHA256 $PROVISION_SHA256` | `P2_DONE` |
| S1 | signer | the S1 command M4 printed, with `--signer` | signer `check` UNTRUSTED `05759e90…`, routes PASS, `S1_DONE` |
| S1b | signer | `python3.12 -I ssm_run.py --signer host/s1b-credential-mode-test.sh` | `key_loader: PASS`, `S1B_DONE` |
| S2 | signer | `python3.12 -I ssm_run.py --signer host/s2-key-check-start-signer.sh` | `wallet_matches: true`, `started: true`, `S2_DONE` |
| P5 | primary | `python3.12 -I ssm_run.py host/p5-start-execution.sh` | `larp-execution active restarts=0`, `P5_DONE` |
| C1 | signer | `python3.12 -I ssm_run.py --signer checks/signer-status.sh` (before T2) | active, 0 restarts, no refusal after the start line |
| T2 | Yao, Mac | Terraform `enable_signer_provisioning = false` | plan destroys only the 8; SA5; SA9 |
| M9 | Yao, Mac | `bash mac/m9-cleanup-s3-package.sh <prefix from M4>` | `M9_DONE` |
| J-flat | anyone | `checks/trading-status.sh`, `mac/chain-monitor.py`, every round until flat | S4-L1: first SELL clears or uses the SKHYB allowance (`REVOKE` or SKHYB first); every position sold to dust before Tue 12:00Z; balance check MATCH; all six router allowances 0 at the end |

## Why this order

- **B0 before M3.** The caps review checks the starting BNB against the 0.01536 BNB exit reserve.
- **M3 before R1p.** M3's read-only probe reads run 4's `/etc/larp/runtime.json` and holdings on primary.
- **X1 after R1p and before P2.** Run 4 has stopped, so its book cannot change. Its configs sit in the root-only
  history folder, and `/opt/larp/current` is still run 4's build.
- **R1s needs T1.** Until R1s, run 4's signer keeps polling `larp_rehearsal4`. The key stays in place (same dev wallet).
- **P4, S2 and P5 fail closed**, as in runs 1 to 4.

**What run 5 must show is S4-L1 (IDEA-097):**
- the first round sells;
- run 4's SKHYB allowance is cleared by a zero-only revoke, or used by an SKHYB sell first;
- every position reaches dust before `signing_end` with balance MATCH;
- all router allowances end at 0;
- no HALT, quarantine or restarts.

A shortfall is a finding to record in IDEA-097, never a reason to bypass a guard.

Stop trading at any time on primary with `systemctl disable --now larp-execution`, or pause all database clients with
`host/pause-primary-db-clients.sh`. S4 is never installed for the final run.

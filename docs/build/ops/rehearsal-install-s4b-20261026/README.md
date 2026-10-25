# Run 6 run sheet: S4 rerun to sell run 5's last GOOGLB (IDEA-097)

Retire run 5 (`larp-dev-rehearsal-20261025-s4`, build `7fc9f60`, `larp_rehearsal5`) and install run 6
(`larp-dev-rehearsal-20261026-s4b`, `larp_rehearsal6`) on the **same S4 profile `58b31806…`** and the **same build
`7fc9f601`**, which is already provisioned on both hosts.
- Run 6 carries run 5's book over: 0.029482 GOOGLB plus cash and BNB.
- Its attempt budget starts fresh. Run 5's last GOOGLB was stopped by `LEG_ATTEMPT_LIMIT`; see IDEA-097 S4-F1 and
  IDEA-102.
- Signing ends 2026-10-26T20:00Z, as in the profile.

Differences from the run-5 sheet (`rehearsal-install-s4-20261025`):
- source run 5, target run 6; X1-save expects run 5 as the source;
- M4's signer diff against run 5's `378e7b35…` is exactly `run_id` and `database_name`, with the recovery scope
  unchanged;
- no M1, M2, P2 or P2s: copy `build.env` and `bundle/` from the run-5 folder, because the hosts already run
  `7fc9f601`.

| Step | Command (from `deploy/activation/rehearsal-install-s4b-20261026/`) | Done when |
|---|---|---|
| prep | `cp ../rehearsal-install-s4-20261025/build.env . && cp -R ../rehearsal-install-s4-20261025/bundle .` | `BUILD=7fc9f601…` |
| D1 | `LARP_PY=<venv> D1_OUT=<repo>/deploy/activation/rehearsal-db-run6 bash mac/d1-create-db.sh` | `S4-D1 PASS`, `D1_DONE` |
| Q1 | `LARP_PY=<venv> bash mac/q1-quote-check.sh` | GOOGLB SELL `VERIFIED_EXECUTABLE`; `Q1_DONE` |
| M3 | `LARP_PY=<venv> OLD_BINDINGS=../rehearsal-install-s4-20261025/private/bindings-7fc9f60.json bash mac/m3-recapture-assemble.sh` (run 5 idle) | `ASSEMBLED_REQUIRES_APPROVAL`, `COVERED`; note the stamp and the signer hash |
| A1 | Isaac approves the new `signer.json` hash (profile and probe unchanged: `58b31806…`, `379c476b…`) | recorded in IDEA-097 |
| R1p | `python3.12 -I ssm_run.py host/r1-retire-primary.sh` | `R1P_DONE` |
| X1 | `python3.12 -I ssm_run.py host/x1-export-holdings.sh`, then `/opt/homebrew/bin/python3.12 -I mac/x1-save-export.py` | `X1_DONE`; export holds GOOGLB only |
| M4 | `LARP_PY=<venv> OLD_SIGNER=../rehearsal-install-s4-20261025/private/signer-20261025T135530Z/signer.json SCOPE_CONFIRMATION="IDEA-097 Decision (Yao, 2026-10-25)" /opt/homebrew/bin/python3.12 -I mac/m4-prepare.py <M3 stamp>` | checks pass; prints P3 and S1 |
| P3, P4 | the P3 command M4 printed; `python3.12 -I ssm_run.py host/p4-init-activate-start.sh "<reviewer>" "<short approval ref>"` | `P3_DONE`, `P4_DONE` |
| T1 | Terraform `-var enable_signer_provisioning=true` (plan: exactly 8 to add) | apply complete; signer SSM `Online` (reboot the signer if commands stay `Delayed`) |
| R1s, S1, S1b, S2 | `python3.12 -I ssm_run.py --signer host/r1-retire-signer.sh`; the S1 command M4 printed; `--signer host/s1b-credential-mode-test.sh`; `--signer host/s2-key-check-start-signer.sh` | `R1S_DONE`, `S1_DONE`, `S1B_DONE`, `S2_DONE` |
| P5 | `python3.12 -I ssm_run.py host/p5-start-execution.sh` | `P5_DONE` |
| T2, M9 | Terraform without the var (plan: exactly 8 to destroy); `bash mac/m9-cleanup-s3-package.sh <prefix>` | `M9_DONE` |
| J | `checks/trading-status.sh` | GOOGLB sold to dust; balance MATCH; no allowance open |

Start P4 as late as possible before P5, so few commands expire unclaimed before execution starts (IDEA-097 S4-F1; PR290
fixes the budget effect).

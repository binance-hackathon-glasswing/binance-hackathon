# Signed dev rehearsal, run 4 on S2 (weekend trade test): RC7 install run sheet (IDEA-089; drafted 2026-10-24)

**Draft, prepared ahead of the gates. Do not start until all of these hold:**
1. PR268 (IDEA-088 SJ-11-QV01 quote verifier) and the S2 implementation (IDEA-089 S2-1..S2-12) are merged into
   canonical. M1 refuses a build without the quote verifier, the S2 hours and the S2 profile `eb55d76a…`.
2. Q1 (below) returns `VERIFIED_EXECUTABLE` with `quote_at_cap` accepted for every S2 name, BUY and SELL, shortly
   before install (S2-6, S2-12).
3. Yao has confirmed the run ID. It is proposed here as `larp-dev-rehearsal-20261024-s2`; to change it, edit `RUN` in
   `mac/m3-recapture-assemble.sh`, `mac/m4-prepare.py` and `host/p4-init-activate-start.sh` together. M4 and P4
   cross-check it.
4. Isaac has approved the S2 profile `eb55d76a…` and the new `signer.json` that M3 prints (A1, S2-7).

**What S2 is (IDEA-089).** A REHEARSAL-only test profile for the dev wallet, not a contest strategy: run 3's S1 block
and sizes (five names at 19/100, about 19 USDT per buy) with two changes in `s1.execution`, plus the weekend window.
- `hours: KIT_OPEN_STATE` (S2-2, S2-8): discretionary legs may trade from the session open to the next open. The whole
  weekend sits in Friday's session (next open Monday 13:30Z). The planner (`reserve`) and execution admission
  (`permitted`) both use this interval, in `larp/strategy/execution_bounds.py interval`. The kit's `openState` check
  (F-95, `MARKET_CLOSED_OR_UNKNOWN`) is unchanged.
- `max_attempts_per_leg_session: 5` (S2-9): five quote rounds per name and leg over the whole weekend.
- Window (S2-4): new risk from **Sat 2026-10-24 01:00Z** (09:00 SGT) to **Sun 08:00Z** (16:00 SGT), flatten from
  **Sun 09:00Z** (17:00 SGT), signing until **Sun 15:00Z** (23:00 SGT). A run installed after Sun 08:00Z makes no entry.
- `policy_id` `larp-s2-rehearsal-v1`. Every other value is run 3's `6bcf1dfb…`
  (`tests/strategy/test_s2_weekend.py`).

**Scope (S2-1), enforced in code.** `KIT_OPEN_STATE` is refused unless the profile is REHEARSAL with evidence and
falsifiers in SHADOW and the run mode is `dev`. `validate_live`, `gate_a.prepare`, `gate_a_check`, the runtime start
and the execution start each refuse it.

**Quote verifier on (S2-10).** M4 passes the LD03 router-policy pair (`/etc/larp/untrusted-router-policy.json`,
`05759e90…`) to `prepare` and refuses a `runtime.json` without it. P3 checks the `larp-runtime` user can read the
file and that it matches the pin. Without the pair the runtime has no quote verifier, so run 4 would behave exactly
like run 3: no executable quote.

**The UTC day roll (S2-12).** The risk day rolls at 00:00Z. Keep the runtime up across **Sun 00:00Z** (08:00 SGT):
without the roll, Sunday buys are refused as `NEW_RISK_HALTED`.

Run 3 (`larp-dev-rehearsal-20261024`, RC6 `9dc5edab`, database `larp_rehearsal3`, signer `49cb1a08…`) cannot place
an order (SJ-11-QV01) and runs as a no-trade soak. A run cannot change build, so run 4 is a **new run**:
- run `larp-dev-rehearsal-20261024-s2` (proposed, see above);
- database `larp_rehearsal4`;
- the same dev wallet and key, CAP-02 policy `3241abd3…`, router policy `05759e90…`, untrusted mode and initial gas
  only (S2-5);
- **strategy S2**: profile `docs/build/evidence/s2-rehearsal-profile-20261024/rehearsal-s2-deterministic.json`,
  file SHA-256 `eb55d76a…`;
- the M3 probe for that profile, `8e8d6c89…`. It differs from run 3's probe `75547c8e…` only in the embedded
  profile line.

Run 3 never placed an order, so the start is plain USDT and BNB with no stock positions. `gate_a` refuses a wallet
that holds stocks (SJ-09-PC01 C4). `signer.json` carries no profile field, so the candidate differs from run 3's
installed `49cb1a08…` only in `build_id`, `run_id` and `database_name`. M4 enforces that.

What changed against the RC6 sheet:
- M1 additionally requires PR268's `larp/marketdata/quote_verifier.py`, the S2 hours and the S2 profile in BUILD.
- New **Q1** (`mac/q1-quote-check.sh`): the live read-only quote check, BUY and SELL, for every name.
- D1 creates `larp_rehearsal4`.
- M3 starts from run 3's bindings and uses the S2 profile and its probe hash.
- M4 uses the S2 profile, run 3's signer as the diff base, the S2 scope record, and writes and checks the
  router-policy pair in `runtime.json`.
- P3 checks the runtime user can read the router policy.
- R1p/R1s retire run 3. P4 names run 4 and its database.

The other host and check scripts are byte-identical to the RC6 sheet (`tests/runtime/test_run4_sheet.py`).

**Before starting:** copy this folder to the git-ignored `deploy/activation/rehearsal-install-rc7-20261024/` and run
everything from there. Host steps go through `python3.12 -I ssm_run.py [--signer] host/<script> [args]`. Stop at the
first step that does not end with its `*_DONE` line, and keep its `results/` files.

```bash
cp -R docs/build/ops/rehearsal-install-rc7-20261024 deploy/activation/ && cd deploy/activation/rehearsal-install-rc7-20261024
```

`OLD` below means run 3's folder, `deploy/activation/rehearsal-install-rc6-20261023`.

## Order

| Step | Who / where | Command | Done when |
|---|---|---|---|
| D1 | Yao, Mac | `bash mac/d1-create-db.sh` (any time; needs no RC7) | `S2-D1 PASS`, `D1_DONE` |
| M1-local | Mac | `PY=<venv>/bin/python RC4=<CI RC4 bundle dir larp-d03bbb16cf51-x86_64> bash mac/m1-local-bundle.sh` | PR262, PR268, S2 and profile checks pass; integrity checks pass; versus CI RC4, only release files changed in `d03bbb1..BUILD` differ; `BUNDLE.env` differs only in `build_id`; `M1_DONE` |
| (M1) | Mac | `[BUILD=<sha>] bash mac/m1-fetch-bundle.sh <run id>`, if a mirror run is made | digest match, `build.env`, `M1_DONE` |
| Q1 | Yao, Mac | `LARP_PY=<venv>/bin/python bash mac/q1-quote-check.sh` (again shortly before P4 if more than about an hour passes) | ten lines `VERIFIED_EXECUTABLE`, `quote_at_cap=True`, `exit=0`; `Q1_DONE` |
| M2 | Yao, Mac | `bash mac/m2-upload-bundle.sh` | `M2_DONE` |
| M3 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_BINDINGS=$OLD/private/bindings-9dc5eda.json bash mac/m3-recapture-assemble.sh` | probe `8e8d6c89…`; `ASSEMBLED_REQUIRES_APPROVAL`, `numeric_status: COVERED` against S2's sizes; note the stamp |
| A1 | Isaac (relayed) | approve profile `eb55d76a…` and the new `signer.json` hash M3 printed | recorded in IDEA-089 |
| R1p | primary | `python3.12 -I ssm_run.py host/r1-retire-primary.sh` (after M3) | every run-3 unit inactive and disabled, configs in `/etc/larp-history/`, `R1P_DONE` |
| P2 | primary | `python3.12 -I ssm_run.py host/p2-provision.sh primary @artifact_bucket $BUNDLE $BUNDLE_SHA256 $PROVISION_SHA256` | `P2_DONE` |
| M4 | Yao, Mac | `LARP_PY=<venv>/bin/python OLD_SIGNER=$OLD/private/signer-20261023T161113Z/signer.json SCOPE_CONFIRMATION="IDEA-089 Decision (Yao, 2026-10-23)" /opt/homebrew/bin/python3.12 -I mac/m4-prepare.py <M3 stamp>` | diff vs `49cb1a08…` is exactly `build_id`, `database_name`, `run_id`; runtime and execution pin `eb55d76a…`; runtime carries the router-policy pair; checks pass; prints P3 and S1 |
| P3 | primary | the P3 command M4 printed | preflight, checks, `runtime_router_policy readable_by=larp-runtime sha256=05759e90`, routes PASS, `P3_DONE` |
| P4 | primary | `python3.12 -I ssm_run.py host/p4-init-activate-start.sh "<reviewer>" "<run-4 approval record>"` | run 4 initialized and activated; units active with 0 restarts; `P4_DONE` |
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
| J | anyone | `checks/trading-status.sh`, `mac/chain-monitor.py` | P2: a BUY intent, approve, swap, receipts, STORED ACK, round log with the `tx_hash` |
| J-roll | anyone | `checks/trading-status.sh` after Sun 00:00Z | risk day `2026-10-25`, no `NEW_RISK_HALTED` from a stale day (S2-12) |
| J-flat | anyone | `checks/trading-status.sh`, `mac/chain-monitor.py` from Sun 09:00Z | P4: every position sold to dust before 15:00Z; final balance check MATCH |

Why this order is the same as the RC6 sheet's:
- **M3 before R1p:** M3's read-only probe reads run 3's `/etc/larp/runtime.json` on primary.
- **A1 is the approval gate.** M4 enforces the scope mechanically.
- **R1s needs T1:** the signer is reachable only while the IDEA-080 endpoints exist. Until R1s, run 3's signer keeps
  polling `larp_rehearsal3`.
- **The key stays:** R1s moves run 3's configs but leaves `/etc/larp/signer/wallet.key` in place (same dev wallet).
  S1b and S2 re-check it.
- **P4, S2 and P5 fail closed**, as in runs 1 to 3.

**What run 4 must show** is IDEA-089's P1–P6: executable quotes at install (Q1), at least one BUY end to end, balance
MATCH after the entries, the Sunday flatten to dust before `signing_end`, no HALT, quarantine or restarts, and the
gas, fill, latency and round-trip PnL measurements. A shortfall is a finding to record in IDEA-089, never a reason to
bypass a guard. Record how many of the five attempts per leg were used (S2-9).

Stop trading at any time on primary with `systemctl disable --now larp-execution` (survives a reboot), or pause all
database clients with `host/pause-primary-db-clients.sh`. S2 is never installed for the final run; on Monday the next
run returns to S1 or another version with its own profile hash, build and approval.

IDEA-096 F4 (PR282 source update, 2026-10-25): `checks/trading-status.sh` exports six pinned router allowances
and `mac/chain-monitor.py` includes raw per-token amounts plus LOW severity DIRTY_ROUTER_ALLOWANCE alerts.
These observer changes apply only when this newer checkout is copied; historical RC7 receipts and the running
run-4 build remain bound to their recorded commits. Recovery itself needs the separately reviewed PR282
candidate configuration, gas/caps, signer approval and host acceptance (see `docs/build/ALLOWANCE_RECOVERY.md`).

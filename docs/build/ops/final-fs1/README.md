# FS1 final live install: run sheet (IDEA-093; drafted 2026-10-25)

How to install **FS1**, the final strategy, for the scored run on the **final wallet**, in `live` mode, with
AIand/ChatGPT routing. This is a plan for the owners, not a record: no host, wallet, key, secret, model or budget action
has been taken. PR296-RV01 supplies independent offline preparation and FINAL primary install/start scripts below;
shared bundle provisioning and signer installation still use the generic steps from
[`../rehearsal-install-rc7-20261024/`](../rehearsal-install-rc7-20261024/README.md).
Times are UTC (SGT = UTC+8). Organiser rules that bind every step: no manual trading or human action on
the agent once the run starts (F-114, F-117); automatic restarts only (F-124); one round log per round with every swap's
`tx_hash` (F-99, F-100).

## Pins

| Item | Value |
|---|---|
| Strategy profile | **`docs/build/evidence/fs1-final-20261025/fs1-final-recovery.json`, `PROFILE_SHA` `b8ba06e248b48b6406d77c1bda4110001324382e91bb63c71a27ce514731892f`** (IDEA-098: FS1 with the IDEA-096 allowance-recovery gas; install this one). The cleanup-off `fs1-final.json` `19176e6c…` (M3 probe `5b642bd3…`) has run 4's flatten deadlock: a leftover allowance can block swaps in other tokens until it is consumed or cleared. Rebuild the M3 probe for the recovery profile |
| Model routing | `config/intelligence/aiand-routing.fs1.json` → `/etc/larp/model-routing.json`, `9b86c7327eddca76e0739f6639211f9b609f18c027bc4e61bf83dc804dfcf1f4` (ChatGPT `gpt-6.1-sol` first; Kimi K3 / GLM-5.3 through AIand) |
| Token history | IDEA-103 [qualified history input](../../FS1_TOKEN_HISTORY.md), packaged as `token-history.json` → `/etc/larp/token-history.json`; the prepared runtime pins its exact SHA-256. Required for FS1 startup |
| Router policy, CAP-02 | unchanged from run 4: UNTRUSTED `05759e90…`, CAP-02 `3241abd3…` (re-confirm at A1) |
| Run mode / environment | `live` / FINAL (the profile is refused in any other mode) |
| Window (PF-04) | first buy 2026-10-29T14:00Z; new risk ends 2026-11-09T21:00Z; flatten from 2026-11-10T19:00Z; signing ends 2026-11-11T14:45Z; flat by 15:00Z |
| Build | a new RC from the merge of PR278 (it must contain `tools/deploy/build_final_candidate.py` and `aiand-routing.fs1.json`) |

## Standalone preparation (PR296-RV01)

FS1 does **not** need S5 to have run, bought, flattened or produced a signer. From the reviewed release checkout,
use `python -m tools.deploy.prepare_fs1` with an explicitly selected **final** wallet and a fresh read-only
`prepare_shadow.py capture` on that wallet. No S5 package, run-6 bindings, old signer or development ledger is read.
The fresh wallet must hold zero stock (including dust), have no in-flight nonce, and have reconciled chain/API
balances. Qualified history and the F0m adoption reference are required; neither is invented by this tool.

```bash
python -m tools.deploy.prepare_fs1 \
  --terraform-output "$TF_OUTPUT" --wallet "$FINAL_WALLET" \
  --capture "$FINAL_CAPTURE" --token-history-config "$TOKEN_HISTORY" \
  --balance-rpc-config "$RPC_CONFIG" --rds-ca-sha256 "$CA_SHA256" \
  --sec-contact "$SEC_CONTACT" --build-id "$BUILD" \
  --model-adoption-ref "$MODEL_ADOPTION_REF" --out deploy/activation/fs1-prepared
```

This freezes `live` / FINAL, `larp-final-fs1` / `larp_final`, recovery profile `b8ba06e2…`, routing `9b86c732…`,
router policy `05759e90…`, five assessment workers, history pin, fresh initial state and final-wallet-specific
`ai_seeds_dir`/`nonce_dir` (development ownership markers are not reused). It performs no provider
calls, uploads, signing, service starts or database operations. Create/grant the empty `larp_final` database first
using the existing database provisioning procedure with that explicit target; no existing run is rebound.
Recovery is always enabled here; the equivalent generic preparation requires an explicit `--allowance-recovery`.

For Q1/M3, supply **fresh FINAL** `GateBCapsInputs.v1` (see `larp.execution_live.caps_review`): exact profile bytes,
the prepared `initial-state.json`, explicit final execution/IAM/CA/router bindings, the final CAP-02 signing policy
with recovery enabled, and current final-wallet quote artifacts at the selected sizes. Use the actual final wallet
in every quote. Do not run `review_rehearsal_caps.py` or the installed-dev-run LD10 probe for this path. Re-run the
command above within the capture's five-minute validity, with a new `--out`, plus
`--caps-inputs "$FINAL_CAPS_INPUTS" --services-out "$PRIVATE_FINAL_SERVICES"` (a new private directory outside Git).
`final_services` compares the entire fresh initial state and every run/build/wallet/database/CA binding, then runs
the real numeric reviewer and signer assembler. Missing/expired quotes or insufficient caps/gas refuse assembly.
It writes `execution.json`, `signer.json`, the assembly report and router policy; no approval is granted.

Check the original prepared directory with `larp.runtime.gate_a_check` **before** adding service files. After A1,
use `larp.runtime.preflight --bind` with the CI manifest, release root, registration evidence, prepared operations
and runtime configs, and **all three** service configs (uploader, execution, signer). Both hosts install these
same bound manifest bytes. FINAL scripts are [P3](host/p3-install-primary.sh),
[P4](host/p4-init-activate-start.sh), [P5](host/p5-start-execution.sh), and [P6](host/p6-start-runtime.sh).
P4 initializes/activates and starts evidence/delivery only; then S2 starts the signer, P5 starts execution, and
P6 starts runtime after checking execution is active with zero restarts. Never run the old RC7 P4 here.

Source tests verify independent preparation, fresh FINAL numeric COVERED and signer assembly, clean routed
runtime construction, and the actual shell startup steps against synthetic services. Actual history semantics,
fresh final-wallet quotes, budget reconciliation, owner approvals, bundle/release binding and host qualification
are still required; an offline preparation is not an install receipt.

## Before the install (decisions and inputs; nothing here is done)

| # | Who | What | Why |
|---|---|---|---|
| F0 | Keith + Keegan | accept FS1's values and four PR278-RV01 fields: authorized-minimum cost, PF02 recovery, cost-gated small reductions and gas-excluded stock capital; qualify IDEA-103 hourly OPEN timestamp/adjustment evidence and accept the history-driven runtime; resolve material fixed-price BNB valuation (GAP-73) | IDEA-093; research/fs1-review-20261025.md |
| F0m | team (LD11/LD22) | record the model-adoption decision; its ID is the `--model-adoption-ref` | `gate_a.prepare` refuses signed routing without it; DEV-19/22, GAP-62 |
| F0b | account owners | reconcile the OpenAI budget (KMP-BUD01: about US$2.88 settled + US$0.34 unknown vs the file's US$2 prior spend). If `openai_pacing` changes, rebuild the routing file (new hash) and re-pin | never initialize a ledger with a stale number (AIAND_MODEL_ROUTING.md) |
| F0s | Yao | runtime Secrets Manager entry carries `LARP_AIAND_API_KEY` (required) and `LARP_MODEL_API_KEY` (OpenAI; without it every assessment goes to the AIand reviewers, so ChatGPT is not used) | `larp/intelligence/routing.py` |
| F0w | Isaac + Yao | confirm the already registered final wallet's 200 USDT funding (GAP-75), bind its uploader secret, and record the organiser-required **30 USDT → BNB** MetaMask swap before the first agent trade (now the activation self-check) and before Oct 29; smaller only with explicit organiser permission | F-120/F-125, GAP-73 |
| F0a | Keith + Keegan + Yao | GAP-74 is built into FS1 (IDEA-093 SC): **one run spans the self-check and the scored run**, so no second install or version event. The profile key `activation_self_check` buys about 32 USDT of SKHYB between 2026-10-27T00:00Z and 2026-10-28T18:00Z, sells it whole, and records DONE before 2026-10-28T23:00Z; FS1 then trades as usual from Oct 29 14:00Z. Keith/Keegan accept the values; the install (P4/S2/P5/P6) must finish **before 2026-10-28T18:00Z** or no self-check buy is made (the run then records EXPIRED and still trades the scored run) | IDEA-093 SC, F-125 |
| F0k | Yao | the final wallet's key on the signer (as SJ-06 K1, for the final wallet) | G-09 |
| F0p | Yao (Keegan reviews) | Use the standalone preparer and FINAL P3/P4/P5/P6 above. Select the exact CI bundle and provision the explicit final database; supply fresh FINAL capture/caps inputs and bind the approved services to one registered release. These source paths replace run-4-pinned M4/P3/P4 and S5/old-signer dependencies; current-host and final-input qualification is still required | no hand-editing a dev run's config into FINAL |
| F0d | Yao (Keegan reviews) | IDEA-100 DB1/DB2 on the database, **outside any run**: `terraform apply` of `deploy/aws` (five `database-*` alarms, four parameters); confirm each alarm with an SNS test publish; reboot the RDS instance once so `shared_preload_libraries` loads; as admin, `CREATE EXTENSION pg_stat_statements`; then `checks/db-top-queries.sh` (run-5 sheet; copy it with F0p) prints rows | IDEA-100: the 1 GB instance stalled on 2026-10-25; the reboot must not interrupt a run |

## Order (differences from the RC7 sheet)

| Step | Who / where | FS1 difference | Done when |
|---|---|---|---|
| W0 | anyone, read-only | chain monitor `--once` on the **final** wallet after funding and the 30 USDT gas swap, before install | 0 units of all five stocks (dust included), actual remaining USDT (about 170 before fees/self-check), actual BNB and a fresh profile valuation; reconcile funding notes and opening equity |
| D1 | Yao, Mac | new database (proposed `larp_final`), run ID (proposed `larp-final-fs1`) | `D1_DONE` |
| M1 | Mac or CI | bundle from the PR278 merge; check it contains the FS1 builder and routing file | `M1_DONE` |
| Q1 | Yao + Isaac | obtain FS1-pinned final-wallet quotes at actual gas-excluded opening sizes (about 32.3 USDT/name before fees), full-exit child sizes and small level reductions, using its 20 bp slippage and minimum-output cost checks. The existing `quote_check.py` is pinned to run 3's 8 bp/dev address and is supplementary only; an FS1-pinned path remains to be built/reviewed | exact-profile executable quotes and fee/gas evidence accepted, including cost-refused residuals |
| M2, M3 | Yao, Mac | Standalone preparation and `--caps-inputs` above: fresh final-wallet capture, FINAL quote artifacts, exact prepared initial state and final policy/bindings. No installed dev runtime or retired source ledger is required. The historical `5b642bd3…` probe is comparison evidence only | `numeric_status: COVERED` at FS1 sizes (38.2 USDT cap, two exit children), eight-child action gas and actual BNB; final signer assembly complete before A1 |
| A1 | Isaac | approve `PROFILE_SHA` `b8ba06e2…` (recovery profile, IDEA-098), the final `signer.json` with `signing_policy.allowance_recovery: true` (zero-only revokes, IDEA-096/LD06), and caps/gas coverage: the eight-child envelope 0.001536 BNB per action and the 0.01536 BNB exit reserve against the final wallet's actual BNB (GAP-73) | recorded in IDEA-093 and IDEA-098 |
| M4 | Yao, Mac | Run `tools.deploy.prepare_fs1` as documented above, with fresh FINAL `--caps-inputs` and `--services-out`; check the original prepared package, approve exact service bytes at A1, then bind operations/runtime/uploader/execution/signer and registration evidence to one release. The older `enable_allowance_recovery` tool remains an independent RC3 regression path; no opt-in rewrite is needed here because FS1 recovery is already pinned | `live` / `aiand_routed`, routing `9b86c732…`, recovery true in all three services, profile `b8ba06e2…`; local package checks PASS and both hosts use the same manifest |
| P2–P3 | primary | as RC7; also install the packaged `/etc/larp/model-routing.json` and `/etc/larp/token-history.json` root-owned and readable by `larp-runtime` | preflight and checks PASS |
| B1 | primary | `model_budget init --routing-file /etc/larp/model-routing.json` with the **reconciled** prior spend (F0b), as `larp-runtime` | status shows the frozen pacing and the routing hash |
| S1–S2 | signer | as RC7, with the final wallet key | `wallet_matches: true`, `started: true` |
| P4 → S2 → P5 → P6 | primary, signer, primary | Use this folder's scripts: initialize/activate without planning, start signer, start execution, then start runtime only after execution is healthy. Complete before the self-check buy cutoff 2026-10-28T18:00Z | both active, 0 restarts; `P6_DONE` |
| J | anyone | `checks/trading-status.sh`, chain monitor | rounds in consecutive 15-minute slots; first BUY end to end with `tx_hash` in a round log |
| J-SC | anyone, read-only | `checks/trading-status.sh`, chain monitor, ai-seeds spool | the F-125 self-check: a SKHYB BUY (about 32 USDT) then a mandatory SELL (`ACTIVATION_SELF_CHECK`) on the final wallet, risk state `activation_self_check: DONE` before 2026-10-28T23:00Z, both round logs with their swap `tx_hash`, a non-empty reason summary, and the uploader spool empty (delivered). If the state is EXPIRED, record why; FS1 still starts on Oct 29 14:00Z |

## During the run (no human action)

- One run from start to end. A crash is restarted automatically by systemd (F-124) on the same run and database; never
  start a new run while stocks are held: its install would refuse them and its books would not own them.
- The runtime must be up across every 00:00Z (UTC day roll), including weekends, or new buys stop as
  `NEW_RISK_HALTED` until the next roll.
- Read-only checks only: `checks/trading-status.sh`, `checks/primary-status.sh`, `checks/db-top-queries.sh` (IDEA-100), the chain monitor, the OpenAI budget
  status. No pause, no flatten, no restart by hand (F-114).
- Expected behaviour: the book is built in the first sessions after Oct 29 14:00Z and held; trades after that only on
  verified red flags (AIand/ChatGPT assessment + verifier), qualified basket trend changes, loss-ladder cuts, and the terminal flatten from Nov 10 19:00Z.

PR296-RV01 adds standalone source preparation and FINAL numeric assembly to the PR283-RV01 recovery work.
Fresh Q1 inputs, exact bundle/database/release qualification and host installation remain explicit owner tasks.
A standalone policy file or numeric COVERED result grants no signer approval; the exact assembled signer,
prepared package and manifested outputs must all agree.

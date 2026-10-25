# FS1 final live install: run sheet (IDEA-093; drafted 2026-10-25)

How to install **FS1**, the final strategy, for the scored run on the **final wallet**, in `live` mode, with
AIand/ChatGPT routing. This is a plan for the owners, not a record: no host, wallet, key, secret, model or budget action
has been taken. It reuses the RC7 sheet's scripts and order
([`../rehearsal-install-rc7-20261024/`](../rehearsal-install-rc7-20261024/README.md)); the rows below say only what
differs for FS1. Times are UTC (SGT = UTC+8). Organiser rules that bind every step: no manual trading or human action on
the agent once the run starts (F-114, F-117); automatic restarts only (F-124); one round log per round with every swap's
`tx_hash` (F-99, F-100).

## Pins

| Item | Value |
|---|---|
| Strategy profile | **`docs/build/evidence/fs1-final-20261025/fs1-final-recovery.json`, `PROFILE_SHA` `b8ba06e248b48b6406d77c1bda4110001324382e91bb63c71a27ce514731892f`** (IDEA-098: FS1 with the IDEA-096 allowance-recovery gas; install this one). The cleanup-off `fs1-final.json` `19176e6c…` (M3 probe `5b642bd3…`) has run 4's flatten deadlock: a leftover allowance can block swaps in other tokens until it is consumed or cleared. Rebuild the M3 probe for the recovery profile |
| Model routing | `config/intelligence/aiand-routing.fs1.json` → `/etc/larp/model-routing.json`, `9b86c7327eddca76e0739f6639211f9b609f18c027bc4e61bf83dc804dfcf1f4` (ChatGPT `gpt-6.1-sol` first; Kimi K3 / GLM-5.3 through AIand) |
| Router policy, CAP-02 | unchanged from run 4: UNTRUSTED `05759e90…`, CAP-02 `3241abd3…` (re-confirm at A1) |
| Run mode / environment | `live` / FINAL (the profile is refused in any other mode) |
| Window (PF-04) | first buy 2026-10-29T14:00Z; new risk ends 2026-11-09T21:00Z; flatten from 2026-11-10T19:00Z; signing ends 2026-11-11T14:45Z; flat by 15:00Z |
| Build | a new RC from the merge of PR278 (it must contain `tools/deploy/build_final_candidate.py` and `aiand-routing.fs1.json`) |

## Before the install (decisions and inputs; nothing here is done)

| # | Who | What | Why |
|---|---|---|---|
| F0 | Keith + Keegan | accept FS1's values and four PR278-RV01 fields: authorized-minimum cost, PF02 recovery, cost-gated small reductions and gas-excluded stock capital; resolve missing trend input/static-baseline deviation and material fixed-price BNB valuation (GAP-73) | IDEA-093; research/fs1-review-20261025.md |
| F0m | team (LD11/LD22) | record the model-adoption decision; its ID is the `--model-adoption-ref` | `gate_a.prepare` refuses signed routing without it; DEV-19/22, GAP-62 |
| F0b | account owners | reconcile the OpenAI budget (KMP-BUD01: about US$2.88 settled + US$0.34 unknown vs the file's US$2 prior spend). If `openai_pacing` changes, rebuild the routing file (new hash) and re-pin | never initialize a ledger with a stale number (AIAND_MODEL_ROUTING.md) |
| F0s | Yao | runtime Secrets Manager entry carries `LARP_AIAND_API_KEY` (required) and `LARP_MODEL_API_KEY` (OpenAI; without it every assessment goes to the AIand reviewers, so ChatGPT is not used) | `larp/intelligence/routing.py` |
| F0w | Isaac + Yao | confirm the already registered final wallet's 200 USDT funding (GAP-75), bind its uploader secret, and record the organiser-required **30 USDT → BNB** MetaMask swap before the first agent trade (now the activation self-check) and before Oct 29; smaller only with explicit organiser permission | F-120/F-125, GAP-73 |
| F0a | Keith + Keegan + Yao | GAP-74 is built into FS1 (IDEA-093 SC): **one run spans the self-check and the scored run**, so no second install or version event. The profile key `activation_self_check` buys about 32 USDT of SKHYB between 2026-10-27T00:00Z and 2026-10-28T18:00Z, sells it whole, and records DONE before 2026-10-28T23:00Z; FS1 then trades as usual from Oct 29 14:00Z. Keith/Keegan accept the values; the install (P4/P5) must finish **before 2026-10-28T18:00Z** or no self-check buy is made (the run then records EXPIRED and still trades the scored run) | IDEA-093 SC, F-125 |
| F0k | Yao | the final wallet's key on the signer (as SJ-06 K1, for the final wallet) | G-09 |
| F0p | Yao (Keegan reviews) | **make FS1 copies of the RC7 scripts; not built yet.** The RC7 scripts are pinned to run 4: `mac/m4-prepare.py` (S2 profile `eb55d76a…`, `--runtime-mode dev`, assessor `deterministic`, no routing args, run 4's adoption text), `mac/m3-recapture-assemble.sh`, `mac/d1-create-db.sh`, `mac/setup_rehearsal_db.py`, `mac/prepare_rehearsal_db.py`, `mac/m1-*-bundle.sh` and `host/p4-init-activate-start.sh` (run 4 database/run ID/build). The FS1 copies pin `fs1-final-recovery.json` (the `PROFILE_SHA` above), `live`, `aiand_routed`, the routing pair `9b86c732…`, the F0m adoption reference, the final wallet, database and run ID, and the new RC | the steps below cannot run on the RC7 scripts unchanged; editing them by hand at install time is not a reviewed path |

## Order (differences from the RC7 sheet)

| Step | Who / where | FS1 difference | Done when |
|---|---|---|---|
| W0 | anyone, read-only | chain monitor `--once` on the **final** wallet after funding and the 30 USDT gas swap, before install | 0 units of all five stocks (dust included), actual remaining USDT (about 170 before fees/self-check), actual BNB and a fresh profile valuation; reconcile funding notes and opening equity |
| D1 | Yao, Mac | new database (proposed `larp_final`), run ID (proposed `larp-final-fs1`) | `D1_DONE` |
| M1 | Mac or CI | bundle from the PR278 merge; check it contains the FS1 builder and routing file | `M1_DONE` |
| Q1 | Yao + Isaac | obtain FS1-pinned final-wallet quotes at actual gas-excluded opening sizes (about 32.3 USDT/name before fees), full-exit child sizes and small level reductions, using its 20 bp slippage and minimum-output cost checks. The existing `quote_check.py` is pinned to run 3's 8 bp/dev address and is supplementary only; an FS1-pinned path remains to be built/reviewed | exact-profile executable quotes and fee/gas evidence accepted, including cost-refused residuals |
| M2, M3 | Yao, Mac | Regenerate and hash `ld10_readonly_packet.py --profile fs1-final-recovery.json` for the final wallet; the old `5b642bd3…` probe is cleanup-off comparison evidence only. The F0p FINAL-specific assembly must use `mode=live`, `environment=FINAL`, final-wallet bindings/policy and `allowance_recovery=true` for execution and signer. `review_rehearsal_caps.py` currently hard-codes dev/REHEARSAL and the development policy, so it cannot supply this FINAL packet unchanged | fresh pinned probe and full `numeric_status: COVERED` at FS1 sizes (38.2 USDT cap, two exit children), eight-child action gas and actual BNB; final signer assembly complete before A1 |
| A1 | Isaac | approve `PROFILE_SHA` `b8ba06e2…` (recovery profile, IDEA-098), the final `signer.json` with `signing_policy.allowance_recovery: true` (zero-only revokes, IDEA-096/LD06), and caps/gas coverage: the eight-child envelope 0.001536 BNB per action and the 0.01536 BNB exit reserve against the final wallet's actual BNB (GAP-73) | recorded in IDEA-093 and IDEA-098 |
| M4 | Yao, Mac | `prepare_shadow.py prepare … --execution service --runtime-mode live --profile fs1-final-recovery.json --allowance-recovery --model-routing config/intelligence/aiand-routing.fs1.json --model-routing-sha256 9b86c732… --model-adoption-ref "<F0m>"` plus the RC7 router-policy pair, through the FS1 copy of `m4-prepare.py` (F0p; its identity checks are `live` / `aiand_routed`, not RC7's `dev` / `deterministic`); then `python -m tools.deploy.enable_allowance_recovery --profile fs1-final-recovery.json --execution-config … --signing-policy … --runtime … --decision-id "<A1 ref>" --output-dir …` emits `execution-config.json`, standalone `signing-policy.json`, `runtime.json` and `profile.json`, and must leave the profile bytes unchanged (IDEA-098 RC3). It does not edit or assemble `signer.json`; use the final M3 inputs and emitted signing-policy source to regenerate the signer assembly, then verify it is exactly the A1-approved signer. Rebuild/re-pin any changed prepared-config report and release-manifest hashes before `gate_a_check`; return to A1 for approval if final signer bytes differ | `runtime.json` `mode` `live`, `assessor` `aiand_routed`, routing pin `9b86c732…`, `allowance_recovery` true in all three files; profile SHA still `b8ba06e2…`; `gate_a_check` PASS |
| P2–P3 | primary | as RC7; also install `/etc/larp/model-routing.json` readable by `larp-runtime` | preflight and checks PASS |
| B1 | primary | `model_budget init --routing-file /etc/larp/model-routing.json` with the **reconciled** prior spend (F0b), as `larp-runtime` | status shows the frozen pacing and the routing hash |
| S1–S2 | signer | as RC7, with the final wallet key | `wallet_matches: true`, `started: true` |
| P5 then P4 | primary | **start execution before the runtime plans its first buy** (run 4's first intent expired because P4 ran before P5); all of this before `trade_after` 2026-10-29T14:00Z | both active, 0 restarts |
| J | anyone | `checks/trading-status.sh`, chain monitor | rounds in consecutive 15-minute slots; first BUY end to end with `tx_hash` in a round log |
| J-SC | anyone, read-only | `checks/trading-status.sh`, chain monitor, ai-seeds spool | the F-125 self-check: a SKHYB BUY (about 32 USDT) then a mandatory SELL (`ACTIVATION_SELF_CHECK`) on the final wallet, risk state `activation_self_check: DONE` before 2026-10-28T23:00Z, both round logs with their swap `tx_hash`, a non-empty reason summary, and the uploader spool empty (delivered). If the state is EXPIRED, record why; FS1 still starts on Oct 29 14:00Z |

## During the run (no human action)

- One run from start to end. A crash is restarted automatically by systemd (F-124) on the same run and database; never
  start a new run while stocks are held: its install would refuse them and its books would not own them.
- The runtime must be up across every 00:00Z (UTC day roll), including weekends, or new buys stop as
  `NEW_RISK_HALTED` until the next roll.
- Read-only checks only: `checks/trading-status.sh`, `checks/primary-status.sh`, the chain monitor, the OpenAI budget
  status. No pause, no flatten, no restart by hand (F-114).
- Expected behaviour: the book is built in the first sessions after Oct 29 14:00Z and held; trades after that only on
  verified red flags (AIand/ChatGPT assessment + verifier), loss-ladder cuts, and the terminal flatten from Nov 10 19:00Z.

PR283-RV01: recovery gas/profile selection does not complete F0p, Q1 or FINAL M3 automation. These remain
explicit owner tasks before installation. A standalone policy file or numeric COVERED result grants no signer
approval; the exact assembled signer, prepared package and manifested outputs must all agree.

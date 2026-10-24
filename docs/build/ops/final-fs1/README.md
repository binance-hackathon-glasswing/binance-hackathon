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
| Strategy profile | `docs/build/evidence/fs1-final-20261025/fs1-final.json`, `PROFILE_SHA` `75767d3e4d202d0e25645f7015cde5dcf4b50c07609b9731ae1b6d52b8d62f76`, M3 probe `fcd18d03…` |
| Model routing | `config/intelligence/aiand-routing.fs1.json` → `/etc/larp/model-routing.json`, `9b86c7327eddca76e0739f6639211f9b609f18c027bc4e61bf83dc804dfcf1f4` (ChatGPT `gpt-6.1-sol` first; Kimi K3 / GLM-5.3 through AIand) |
| Router policy, CAP-02 | unchanged from run 4: UNTRUSTED `05759e90…`, CAP-02 `3241abd3…` (re-confirm at A1) |
| Run mode / environment | `live` / FINAL (the profile is refused in any other mode) |
| Window (PF-04) | first buy 2026-10-29T14:00Z; new risk ends 2026-11-09T21:00Z; flatten from 2026-11-10T19:00Z; signing ends 2026-11-11T14:45Z; flat by 15:00Z |
| Build | a new RC from the merge of PR278 (it must contain `tools/deploy/build_final_candidate.py` and `aiand-routing.fs1.json`) |

## Before the install (decisions and inputs; nothing here is done)

| # | Who | What | Why |
|---|---|---|---|
| F0 | Keith | accept FS1's values: 20 bp slippage, 24/7 hours, PF-04 kept, equal weights | IDEA-093 |
| F0m | team (LD11/LD22) | record the model-adoption decision; its ID is the `--model-adoption-ref` | `gate_a.prepare` refuses signed routing without it; DEV-19/22, GAP-62 |
| F0b | account owners | reconcile the OpenAI budget (KMP-BUD01: about US$2.88 settled + US$0.34 unknown vs the file's US$2 prior spend). If `openai_pacing` changes, rebuild the routing file (new hash) and re-pin | never initialize a ledger with a stale number (AIAND_MODEL_ROUTING.md) |
| F0s | Yao | runtime Secrets Manager entry carries `LARP_AIAND_API_KEY` (required) and `LARP_MODEL_API_KEY` (OpenAI; without it every assessment goes to the AIand reviewers, so ChatGPT is not used) | `larp/intelligence/routing.py` |
| F0w | organisers / team | the **final wallet** is registered and funded with 200 USDT; its `AI_SEEDS_SECRET` (Q-35) is in the uploader secret; first BNB from a MetaMask USDT → BNB swap, recorded as a funding note, **before** the first agent trade and before Oct 29 00:00Z | F-14, F-107, F-120 |
| F0k | Yao | the final wallet's key on the signer (as SJ-06 K1, for the final wallet) | G-09 |

## Order (differences from the RC7 sheet)

| Step | Who / where | FS1 difference | Done when |
|---|---|---|---|
| W0 | anyone, read-only | chain monitor `--once` on the **final** wallet | 0 units of all five stocks (dust included: `gate_a.initial_state` refuses any, IDEA-092 H1/H2), USDT about 200, BNB > 0 |
| D1 | Yao, Mac | new database (proposed `larp_final`), run ID (proposed `larp-final-fs1`) | `D1_DONE` |
| M1 | Mac or CI | bundle from the PR278 merge; check it contains the FS1 builder and routing file | `M1_DONE` |
| Q1 | Yao, Mac | `tools/deploy/quote_check.py --pay-units 38000000` BUY, and SELL, for each name. The tool is pinned to run 3's profile (8 bp, dev wallet address; quotes do not check balances), so a pass is at a tighter limit than FS1's 20 bp; no FS1-pinned variant is built | ten `VERIFIED_EXECUTABLE` |
| M2, M3 | Yao, Mac | M3 against `fs1-final.json` (probe `fcd18d03…`) and the final wallet | `numeric_status: COVERED` at FS1's sizes (38.2 USDT cap, two exit children) |
| A1 | Isaac | approve `PROFILE_SHA` `75767d3e…`, the final `signer.json`, caps/gas coverage | recorded in IDEA-093 |
| M4 | Yao, Mac | `prepare_shadow.py prepare … --execution service --runtime-mode live --profile fs1-final.json --model-routing config/intelligence/aiand-routing.fs1.json --model-routing-sha256 9b86c732… --model-adoption-ref "<F0m>"` plus the RC7 router-policy pair; the M4 script's `'dev'` identity checks become `'live'` | `runtime.json` `mode` `live`, `assessor` `aiand_routed`, routing pin `9b86c732…`; `gate_a_check` PASS |
| P2–P3 | primary | as RC7; also install `/etc/larp/model-routing.json` readable by `larp-runtime` | preflight and checks PASS |
| B1 | primary | `model_budget init --routing-file /etc/larp/model-routing.json` with the **reconciled** prior spend (F0b), as `larp-runtime` | status shows the frozen pacing and the routing hash |
| S1–S2 | signer | as RC7, with the final wallet key | `wallet_matches: true`, `started: true` |
| P5 then P4 | primary | **start execution before the runtime plans its first buy** (run 4's first intent expired because P4 ran before P5); all of this before `trade_after` 2026-10-29T14:00Z | both active, 0 restarts |
| J | anyone | `checks/trading-status.sh`, chain monitor | rounds in consecutive 15-minute slots; first BUY end to end with `tx_hash` in a round log |

## During the run (no human action)

- One run from start to end. A crash is restarted automatically by systemd (F-124) on the same run and database; never
  start a new run while stocks are held: its install would refuse them and its books would not own them.
- The runtime must be up across every 00:00Z (UTC day roll), including weekends, or new buys stop as
  `NEW_RISK_HALTED` until the next roll.
- Read-only checks only: `checks/trading-status.sh`, `checks/primary-status.sh`, the chain monitor, the OpenAI budget
  status. No pause, no flatten, no restart by hand (F-114).
- Expected behaviour: the book is built in the first sessions after Oct 29 14:00Z and held; trades after that only on
  verified red flags (AIand/ChatGPT assessment + verifier), loss-ladder cuts, and the terminal flatten from Nov 10 19:00Z.

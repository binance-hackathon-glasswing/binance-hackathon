# IDEA-096 — Flatten blocked by a leftover router allowance from an aborted swap (run 4 incident, fix spec)

- Date / author: 2026-10-25 (~09:40Z) / Claude Code, from read-only host and chain checks requested by Yao
  ("check if our agent is selling the stocks now for the flatten process"). Owners for the fix: Keegan
  (execution/gas caps, LD06/LD10), Isaac (signer policy), Keith (planner order, if F1 is taken). Host checks: Yao.
- Status: **implemented for review in PR282 — F2/F3/F4 source and offline regressions; owner/profile/host acceptance and AL9 remain open.**
- Related: IDEA-088 (quote verifier, PR268), IDEA-089 (S2, run 4), IDEA-090 S2-F6 (post-approve requote aborts),
  IDEA-092 (S3 scheduled flatten), IDEA-093 (FS1 final candidate, PR278), IDEA-049-C LD06 (allowance cleanup),
  LD10 (gas budgets), SKILL.md §0.3 #1 (no manual trading).

## What happened (run 4, `larp-dev-rehearsal-20261024-s2`, RC7 build `2d160073`)

All values are public (wallet balances, allowances, tx hashes, reason codes). Sources: `checks/trading-status.sh`
via SSM at 09:26:52Z and 09:30:20Z (command `29d1369d-d40c-423e-ab48-b5e60af658ae`),
`tools/dashboard/decisions-export.sh 10`, and direct `allowance`/`balanceOf` reads on BSC public RPC at ~09:35Z.
Summary: [`build/evidence/flatten-allowance-20261025.json`](../build/evidence/flatten-allowance-20261025.json).

| Time (UTC) | Round | What the agent did |
|---|---|---|
| ≤ 08:15 | `cadence:1992129#1` and earlier | every name `KEEP_QUANTITY / LOW_TURNOVER_HOLD` |
| 09:00:04 | `cadence:1992132#1` | terminal flatten starts: all five names `EXIT / TERMINAL_REQUIREMENT` (on time) |
| 09:00:21 | `cadence:1992132#1/quote1` | mandatory `SELL` SKHYB 0.068939879194155372 (half the holding; `PER_TRADE_CAP` split), reason `TERMINAL_FLATTEN`. **APPROVE succeeded** (nonce 14, `0x21de2f5e30f0f696fdfa1264aca8d79b7acc6206106ce401ef183c66dfd81bc2`, status 1, gas 54 432). **SWAP aborted before broadcast**: `ABORTED_BEFORE_SWAP_BROADCAST`, "encoded swap economics mismatch/expired" (the S2-F6 class of post-approve requote refusal). |
| 09:30:02 | `cadence:1992134#1` | mandatory `SELL` NVDAB 0.044718666978285414 refused at quote time: **INCIDENT** `Unavailable: quote proof refused: router allowance exceeds what this swap may take`. Nothing sent. |

On-chain at ~09:35Z (wallet `0x62b8…d479`, router `0xb444…fdda5`):

| Token | Router allowance | Wallet balance |
|---|---|---|
| **SKHYB** | **68939879194155372** (the 09:00 approve, unspent) | 137879758388310745 |
| NVDAB / GOOGLB / TSLAB | 0 | 89437333956570829 / 58963981213780645 / 50963873012289550 |
| USDT, MSFTB | 0 | 20.274322 USDT / 0 |

No HALT, quarantine or signer refusal; balance check `MATCH`. `larp-execution`, `larp-evidence`, `larp-uploader`
show `restarts=1` (cause not read; separate from this incident).

## Root cause (read from the code at canonical `5b5f0c89`)

1. `UntrustedRouterDecoder.preflight` (`larp/execution_live/untrusted_router.py:231-244`) refuses a swap when **any
   token other than the pay token** has a non-zero router allowance (`limit = 0` for other tokens). This is a
   deliberate safety rule (LD06: never swap with a dirty other-token allowance).
2. `UntrustedQuoteVerifier._proof` (`larp/marketdata/quote_verifier.py:104-109`, IDEA-088) runs that same preflight
   with `approved=False` **at quote time, in the runtime**, before any execution intent exists. A dirty allowance on
   another token therefore turns into "no executable quote" for every other name.
3. The executor's cleanup step that would clear it (LD06 zero-approve, `larp/execution.py:471-482`, `REVOKE:<token>`)
   only runs inside an intent and only when `allowance_recovery` is true. It defaults to false
   (`larp/execution_live/main.py:53-55`, `larp/signer/policy.py:56`) and every current profile's gas formulas say
   "cleanup disabled". So nothing in the system can clear the allowance.
4. An aborted swap after a successful approve leaves the exact-amount approve open. During BUYs this never showed:
   every BUY pays USDT, and the pay token is exempt before its own approve (the next USDT approve overwrites it, the
   swap consumes it). Three of seven run-4 BUY intents aborted this way without harm. During a flatten each SELL pays
   a **different** token, so one aborted sell blocks every other name.

**Consequence.** Until SKHYB's allowance is consumed, every SELL except SKHYB's is refused, and every BUY too. It is
consumed only if the planner happens to quote SKHYB again *and* that swap completes. If the dirty token were USDT
(a BUY aborted after its approve just before `new_risk_end`), no SELL could run at all, since no BUY is planned during
a flatten. The terminal flatten, the S3 scheduled flatten (IDEA-092) and S1 level reductions all share this path.

**Scope.** The FS1 final candidate (IDEA-093, PR278) keeps cleanup disabled and records "Approve without swap … the
next approve for that token replaces it … LD06 cleanup stays disabled". That holds for one pay token only; this
incident is the cross-token case. **The final run has the same defect** unless it is fixed before final activation.

## Immediate operational questions (team; not decided here)

- **Run 4.** If SKHYB is not re-quoted and swapped before `signing_end` (Sun 15:00Z), run 4 ends holding GOOGLB,
  NVDAB, TSLAB (and part of SKHYB). Recheck after each round with `checks/trading-status.sh`.
- **Next dev run.** `gate_a.initial_state` refuses a wallet holding stocks (IDEA-092 H1/H2). The proposed FS1-R
  rehearsal window opens Sun 16:00Z (PR278) and would need a flat wallet.
- **No manual workaround is proposed.** A wallet-signed zero-approve or sell outside the agent is a manual
  wallet action (SKILL.md §0.3 #1). Whether anything is done for run 4 is for Yao/Isaac.

## Fix spec (draft for implementers)

Recommended: **F2 + F3 + F4** before the final; **F1** optional and cheap. F2/F3 change signer policy and gas caps, so
Isaac and Keegan must accept them.

- **F1 — consume first (planner; no new transaction types).** When a held name with a mandatory SELL has a non-zero
  router allowance, quote and plan that name first. Its own approve overwrites the allowance and the swap consumes it.
  Not enough alone: it fails when the dirty token is USDT or a name that cannot be sold this round, and a second
  abort repeats the problem. Needs an allowance observation in the runtime (the verifier already reads all six).
- **F2 — let the executor clean up instead of refusing at quote time.**
  - Turn `allowance_recovery` on for the execution service and signer policy (`signing_policy.allowance_recovery`).
  - In `UntrustedQuoteVerifier`, when recovery is on, stop refusing *other-token* allowances at quote time. Record
    them in the proof (for example `dirty_allowances: {token: units}`) and refuse only what the executor could not
    clean (non-pinned token, pin or code-hash mismatch).
  - The executor's existing LD06 path then sends `REVOKE:<token>` (zero approve, validated independently by the
    signer) before the APPROVE. **The strict swap-time preflight (`approved=True`) stays unchanged**, so no swap is
    ever broadcast while another token has a non-zero allowance.
  - Recompute the gas and caps that assume "cleanup disabled": `caps_review` children (8 instead of 2 when
    recovery is on), `gas_action_budget_units`, `exit_gas_reserve_units` and their provenance formulas (LD10).
- **F3 — clear on abort.** When an intent ends `ABORTED` after a `FINAL_SUCCESS` APPROVE and no swap, the executor sends
  a zero-approve for that pay token within the same intent's authority and reservation (or one dedicated
  `ALLOWANCE_REVOKE` maintenance intent). This stops the problem from being created. Restart between the abort and
  the revoke must neither lose nor repeat it (`revokes_unbroadcast` store contract).
- **F4 — make it visible.** Give the refusal its own reason code (for example `DIRTY_ROUTER_ALLOWANCE` with the
  token symbol) instead of free text. Show router allowances per token in `checks/trading-status.sh` and
  `mac/chain-monitor.py`, and raise a low-severity incident whenever an allowance is non-zero at round end.

## Pre-registered pass criteria (written before any fix code or test)

| # | Pass when | Evidence |
|---|---|---|
| AL1 | **Red on base.** At canonical `5b5f0c89`, a synthetic state with SKHYB router allowance > 0 and a mandatory NVDAB SELL makes the quote proof refuse with "router allowance exceeds what this swap may take"; the test fails on base and passes after the fix | synthetic verifier/planner test |
| AL2 | After the fix, the AL1 state flattens all five names to `dust_units` within the window. The SKHYB allowance is cleared (revoke) or consumed (its own sell) before any other swap | coordinator test with fake chain |
| AL3 | A USDT allowance left by a BUY aborted just before `new_risk_end` does not block the flatten | coordinator test |
| AL4 | No swap is ever signed or broadcast while a non-pay token has a non-zero allowance; the swap-time `preflight(approved=True)` is byte-for-byte unchanged | unit test + diff |
| AL5 | An intent aborted after a successful APPROVE ends with that token's allowance at 0 (F3); gas stays inside the intent's `gas_budget` and the aggregate reservation | executor test |
| AL6 | Restart at each step (after approve, after abort, after revoke signed, after revoke broadcast) neither repeats nor loses the revoke; replay is exact | restart/replay tests |
| AL7 | With `allowance_recovery` off, behaviour is unchanged and the signer still refuses `REVOKE:*`; with it on, `caps_review`, `validate_live` and `gate_a_check` pass with the recomputed gas/caps and their provenance | profile/caps tests |
| AL8 | The refusal is exported as `DIRTY_ROUTER_ALLOWANCE` (with symbol) by `decisions-export.sh` and `trading-status.sh`; router allowances appear in both and in `chain-monitor.py` | export tests |
| AL9 (live, team) | In the next dev run: after every round all six router allowances are 0 or consumed by the next swap; any aborted post-approve swap is followed by a confirmed zero-approve; the terminal flatten reaches dust with balance check `MATCH` | chain monitor, `trading-status.sh`, BscScan |

## Results

### AL-IMPL01 — implementation contract (2026-10-25, before execution)

Implement F2/F3/F4 on this PR; F1 is unnecessary for correctness and deferred. Defaults remain disabled;
candidate assembly must explicitly opt runtime, execution and signer into the same recovery scope and budget.
Use at most five pre-trade revokes (other tokens), one exact trade approve, and either swap or pay-token
abort revoke. The existing eight-child envelope remains conservative. The pay allowance is overwritten by
the exact trade approve, reserving its unique revoke identity for abort cleanup. No swap preflight changes.

Persist abort intent before cleanup, revoke any unbroadcast swap capability atomically, hold the wallet barrier
and reservation until cleanup terminates, and publish ordinary gas-only approval facts plus NOT_SUBMITTED.
Never renew expiry/window/margin or bypass HALT/health/signer guards for cleanup. Consequently AL5/AL6 are
bounded by original authority: expiry, dependency/pin failure, exhausted gas or a reverted revoke can leave
an explicitly reported dirty allowance for the next independently authorized intent (F2), not an unauthorized
late wallet action. AL9 and actual owner/host acceptance remain live gates.

Prospective checks: AL1 red verifier regression on the PR's unchanged base; AL2/AL3 five-name synthetic exits
with dirty stock/USDT; AL4 strict signing/broadcast refusal after fresh contamination; AL5 gas accounting;
AL6 durable PostgreSQL restart at each abort/cleanup stage, revoked signature and exact observation replay;
AL7 explicit opt-in config/caps/profile candidate coverage and disabled compatibility; AL8 sanitized exports.
Run focused suites, then the pinned Linux Python 3.12.15 / PostgreSQL 14.24 suite. Nested bubblewrap and
host/systemd acceptance require their supported environments. Commit/push all changed executable code before tests.


AL1 evidence: regression commit `60b0d3a8` was pushed before its initial failing run (the new opt-in was absent).
A separate synthetic probe loaded the unchanged quote-verifier source at canonical `5b5f0c89` and confirmed the
exact original refusal `quote proof refused: router allowance exceeds what this swap may take` for SKHYB dirty /
NVDAB SELL. The fixed regression checks explicit disabled refusal plus enabled executable proof and amounts.

Implementation: F2/F3/F4, candidate generator and operational monitoring; no planner reorder (F1). The strict
`untrusted_router.py` preflight file is unchanged. Stored execution bytes are hash-verified before defaulting the
new `abort_pending` field, so pre-existing records remain loadable without rewriting historical journals.
Abort cleanup gets its own bounded prepare-probe budget once; restart cannot reset it. Original time/gas and
health/market guards still govern; no post-expiry authority or automatic install is implied.

Final validation is recorded below; the receipt binds the tested source and exact local environment. Initial red integration fixture
runs were corrected to model explicit tx absence, terminal-round attestation, and fresh per-token quote bindings;
no live RPC/host/wallet action was taken. All executable revisions were committed and pushed before execution.


### AL-IMPL01 validation — 2026-10-25

Tested pushed source `1210a9f039799b8fe4120cb01b894d107620680e` on Linux aarch64, Python 3.12.15,
PostgreSQL 14.24; all 45 applicable recursively pinned test dependencies matched. Full suite:
**2705 passed, 0 failed, 8 skipped, 3 deselected, 4018 subtests passed**, 248.53 s.
[Machine-readable receipt](../build/evidence/pr282-allowance-recovery-validation-20261025.json) includes hashes,
command, images, exclusions and the initial full-run corrections. No source, code or tests changed after that run.
Shell syntax checks and `git diff --check` pass. `untrusted_router.py` is byte-identical to base.

| Criterion | Offline evidence / remaining boundary |
|---|---|
| AL1 | Exact canonical refusal probe, then enabled verifier accepts and records dirty SKHYB; disabled refusal remains explicit. |
| AL2 / AL3 | Real PostgreSQL coordinator/ContextBuilder/planner/execution registry/settlement sells five held names to dust with dirty USDT or all five stock allowances; no reservations/allowances remain. Synthetic venue/chain; strict real decoder/preflight. Separate executor cases cover a prior BUY's abandoned/expired approval. |
| AL4 | Contamination between prepare/authorize or signing/broadcast refuses; existing strict router tests pass. Signer retains independent zero-only opt-in/scope, payload/sequence/fee checks. |
| AL5 | Authorized post-approve abort clears the pay allowance with gas-only accounting inside the parent budget. Original expiry/health/window limits are intentionally preserved; out-of-authority cases leave an observable allowance for F2. |
| AL6 | PostgreSQL restart after approve, after signed swap abort, and every cleanup prepare/authorize/sign/broadcast/final stage; revoked swap bytes cannot recover, cleanup never sends twice, unknown sends retain barrier. Existing maintenance observation accounting/exact replay suite passes. Legacy records without the new field preserve their hash chain. |
| AL7 | Recomputed eight-child candidate is numerically COVERED by caps_review and validate_live; Gate A preparation/check_scope binds explicit opt-in and router pins. Full existing Gate A checker suites pass with synthetic inputs. Actual private candidate/release/Gate A/host qualification and owner approval remain open. |
| AL8 | Public pinned allowance amounts and sanitized refusal symbols pass export tests; runtime low-severity incident is durable/idempotent at quiet boundaries. Current RC7 observer scripts updated, older copies preserved. |
| AL9 | NOT RUN — next authorized dev run and live owner acceptance required. |

Eight skips: optional private public-source fixture, external recorded market artifacts, root directory-mode
semantics, and five systemd runner checks. Three unchanged nested-bubblewrap cases were explicitly deselected
because this Docker host cannot supply their namespaces/proc mounts. This is not a host/systemd/sandbox release
acceptance. GitHub runtime check `121141195890` / run `40184126677` did not start due account payment/spending
limits (annotation captured); no GitHub CI PASS is claimed.

Remaining ownership: **Keegan** — fresh quote/caps packet, actual BNB coverage, gas/timing/token behavior and AL9;
**Isaac** — exact signer exception/configuration and manifested candidate acceptance; **Yao/host owners** — authorized
next-run installation and live evidence. Existing run 4 and final candidate are not silently changed. FLAT-01 stays
open for these acceptance items; F1 is optional/deferred. PR282 stays OPEN for teammate review, unmerged.

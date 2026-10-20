# LD06 — bounded allowance recovery

Owner: Isaac. Independent review: Keegan. Record and pre-registered criteria:
[IDEA-070 LD06](../ledger/IDEA-070.md#ld06--bounded-leftover-allowance-recovery-2026-10-20-prospective).
Build from canonical `codex/system-testing-20261012`; PR133 is the noticeboard.

An approve can finalize without its swap, and a reverted swap can leave the same
allowance outstanding. The untrusted-router preflight correctly blocks a later
swap while any other eligible token has a nonzero allowance. That includes a
final exit paying a different token. Re-approving the old token for an unwanted
trade is not recovery. LD06 adds zero-only supporting approvals before the next
independently valid stock intent's normal approve/requote/swap.

## Scope and configuration

This is an opt-in capability. Existing configuration files are unchanged and
remain disabled. Enabling requires both:

- execution.json: `"allowance_recovery": true`;
- signer.json's root-owned, release-pinned `signing_policy` object:
  `"allowance_recovery": true`.

Only literal JSON booleans are accepted. Both default false. Execution requires
its pinned untrusted-router policy; signer loading refuses recovery in verified
mode. Numeric review refuses unequal execution/policy settings. Assembly retains
false installation/signing/Gate B flags and adds
`ALLOWANCE_RECOVERY_GAS_AND_HOST_ACCEPTANCE` to the remaining gates.
A database request cannot enable the signer's setting. Neither an example cap
label nor a successful local assembly supplies actual policy acceptance.

The scope is `approve(pinned_router, 0)` on USDT or one of the five eligible
bStock token contracts, with zero native value, under an already planned
`BSTOCK_TRADE` parent. Gas top-ups, other tokens/spenders/selectors, nonzero
maintenance approvals and a router different from the selected decoder refuse.
Normal trade approvals remain exactly the parent's pay token and positive amount.
No transfer, new economic intent, manual wallet operation or RPC broadcast is
introduced; builders and submission use the existing Web3 Open API boundary.

The verbatim kit specifies exact trade approvals, not a cleanup protocol. This
zero-only supporting scope is a proposed team policy under G-01, requiring
independent review and exact installed policy acceptance; it is not an organiser
rule or a proof of router enforcement. The source check is recorded in LD06.

## State machine

| State / observation | Action and durable boundary |
|---|---|
| Fresh valid parent | Keep the original decision/version/reservation, expiry, action window and gas budget. Get a fresh quote and validate its economic fields. |
| Before trade approval | Read all six allowances with the router dispatch/facet/code pins at one numeric block. Select the first nonzero token in address order. |
| Dirty token, never revoked by this parent | Build an API approval of exactly zero. Name the step `REVOKE:<lowercase token address>`; its immutable attempt ID is derived from parent economic key plus step. |
| PREPARED → AUTHORIZED → SIGNED_DURABLE | Recheck current gates, original expiry/window, nonce and aggregate gas. Primary rechecks code/facet pins. The offline signer independently checks zero-only scope, own opt-in and fee cap, prior step finality/order, nonce and aggregate gas. |
| BROADCAST_ATTEMPTED / PENDING / UNKNOWN | Retain the wallet barrier and original signed bytes. Reconcile; never advance another step, change nonce, re-sign or release uncertainty on timeout/expiry. |
| Canonical FINAL_SUCCESS | Publish the maintenance broadcast and final approval fact, charge actual gas once and retain the remaining parent reservation. Read allowances again; a success receipt alone does not assert zero allowance. |
| Same token still nonzero after confirmed cleanup | Refuse. Each token gets at most one cleanup attempt per parent; the persisted prepare budget prevents endless retry. |
| Canonical FINAL_REVERT | Publish a gas-only REVERT for that cleanup step and fail the parent. No swap hash or fill is invented. |
| All six allowances zero | Normal exact trade approve → confirm → fresh re-quote → strict swap preflight → swap. Cleanup never relaxes the other-token allowance check. |
| Parent expires or another prerequisite fails | Stop. Abort only positively unbroadcast work through existing revocation/expiry paths. Preserve gas facts from already finalized cleanup. A later fresh, independently valid parent can try the remaining cleanup. |

There are at most six cleanup transactions plus one trade approval and one swap
per parent. Prior finalized gas and the next signed gas allowance must fit the
same aggregate parent budget. Existing `RunAuthorization.resources_reserved`
also requires the remaining gas cap to be covered by the current BNB reservation;
cleanup does not borrow another intent's or the exit reserve's funds.

## Audit and accounting

Each cleanup has its own step, attempt, payload hash, nonce and transaction hash
in the execution journal and broadcast/final observations. Its metadata names
`maintenance=ALLOWANCE_REVOKE`, token contract, spender and `approved_amount="0"`.
The observation validator rejects malformed maintenance or a maintenance fill.
The signed transaction and canonical receipt must match exactly. Unexpected
eligible-token movements cause settlement refusal and the existing quarantine;
they are never hidden in a gas-only observation.

Successful cleanup uses `kind=APPROVAL`, `intent_terminal=false`. It charges only
actual gas, preserves token/cash positions and the parent's remaining resources,
and is idempotent by event/receipt identity. A reverted cleanup uses REVERT and
terminates the parent. Supporting approval hashes never enter `orders[].tx_hash`
or `swap_mappings`/`swap_owners`. A parent aborted before swap still closes with
an unbroadcast order disposition, including the real cleanup/gas audit history.
Journal replay recomputes these transitions and the exact final log/head.

## Acceptance still required before installation

- Keegan reviews the zero-only policy exception, implementation and tests.
- Isaac/Keith accept measured cleanup gas, parent reservation/budget and final-exit
  reserve coverage, per-step signer fee limits, and relevant token/API behavior.
  Existing two-transaction gas estimates do not qualify up to eight transactions.
- LD04/LD02 qualify finite authority and real queue/signing/finality timing. Cleanup
  does not lengthen a quote or parent lifetime; short authority may safely refuse.
- LD02/03 supply the actual policy/hash, fresh complete holdings/allowances and
  replay/preflight. LD15–21 qualify exact release, host/session and agent round,
  then cleanup/restart/revert/expiry/final-exit drills without manual trades.
- LD05 abnormal-outcome disposition and LD07/08 supported gas scope remain separate.

Cleanup runs only when a fresh permitted stock action exists. It does not promise
immediate revocation after every failure, or progress while gates/markets are
closed, gas/time is insufficient, the API refuses a zero approval, or a send is
unresolved. Residual allowance remains during such a hold. No maximum-loss bound,
source guarantee or recovery of lost assets is established. No host, wallet/key,
paid provider, signing, receiver or installation operation is part of this PR.

## Offline verification

Source913b400: Linux/Python3.12.15/PostgreSQL14.24 full suite **2190 passed /
3660 subtests /zero failures /eight skips**. The root-sensitive permission skip
was exercised in a separate unprivileged startup run; five real-systemd and two
external-fixture cases remain unrun. Twenty-three new tests cover this feature,
including actual PostgreSQL restart/registry and exact journal replay. Dependency
check, sandbox checks, offline demo and declaration/documentation checks pass.
[Exact-source receipt](evidence/ld06-allowance-recovery-20261020.json) /
[criteria and results](../ledger/IDEA-070.md#ld06-results--source-913b400-2026-10-20).
No full CI, release bundle, real systemd or host qualification is claimed.

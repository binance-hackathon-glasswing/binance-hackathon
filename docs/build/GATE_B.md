# Gate B: first signed trades on the dev wallet (IDEA-070)

Written 2026-10-16. Gate B turns the signer on for the **dev wallet** at minimum size. It starts the signed rehearsal, and is planned for review on **Oct 20** with the rehearsal from Oct 21 (DEPLOYMENT_BUILD.md). The dev wallet is not scored (F-122). This page is the order of work.

Updated for LD01, 2026-10-20: use canonical `codex/system-testing-20261012`.
Isaac selected API-provided router behavior in B09-TRUST01 ([PR196](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/196)).
The selected path is UNTRUSTED; verified source is required only for the separate
source-verified path. Actual policy/hash review, numeric #44 acceptance and
release/host acceptance remain open. This procedure grants no installation or
wallet-operation authority. Current owners/order are on [PR133](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/133).

Current PR reconciliation, lifecycle evidence and the offline current-input
signer-cap checker are in [Gate B remaining work](GATE_B_REMAINING.md)
(IDEA-039 GB-RW1). Source acquisition PR139 and the proposal/host dependencies
remain explicit; numeric cap coverage never enables signing.

## What changed in the code (IDEA-070)

- `larp/execution_live/router.py`: `RouterEvidence.v1`, `PinnedRouterDecoder` and the `selector` / `check` command line.
- The `Executor` accepts live ports with a pinned `PinnedRouterDecoder` or a qualified, RPC-bound `UntrustedRouterDecoder`. Without an applicable decoder:
  - `larp-execution` exits 2 `EXECUTOR_CAPABILITY_GATE`;
  - the signer refuses `check` and `run` before database/key access (SR-01); it cannot start an approval-only path without its pinned decoder.
- Select exactly one complete pair in both `execution.json` and `signer.json`: `router_evidence_file` / `router_evidence_sha256` for verified mode, or `untrusted_router_policy_file` / `untrusted_router_policy_sha256` for untrusted mode. Partial or mixed pairs refuse; the production signer requires a pinned decoder before check/run can pass.
  - The execution service refuses evidence for another router than its `router`.
  - The signer refuses evidence for a router outside its own `signing_policy.allowed_spenders`.
- The Gate B report (`python -m larp.execution_live.gate_b report`) accepts a pinned `router_check` file. DR-02 distinguishes source evidence/review from named-reviewed untrusted policy/replay/live preflight. VALIDATED is a limited local input check; both modes still require owner acceptance and a logged dev approve + swap. DR-03 retains selected policy/evidence identity and isolated-host/provider qualification.

## Two blockers besides the evidence

1. **#27 (C-OPEN-003): choose measured finite authority values.** PR200 implements and reviews Option A: short proposal admission followed by immutable A, with final-release authority and decoded-deadline margins. Keegan chooses L/m from operator timings with Isaac/Keith review and profile provenance. Without the settings, the prior short-authority refusals remain. Recorded routes carry roughly 500-second deadlines; neither the kit's approximate quote TTL nor the illustrative 60s value selects L. Keep `now+m < route_deadline <= A` and uncertain-send reconciliation. See [OG-01](POST_REVIEW_GATES_20261020.md).
2. **A profile window that allows a buy before Oct 21.** The rehearsal profile opens new risk on Oct 21 00:00 UTC, so a Gate B trade on Oct 19–20 needs a team-approved dev window, registered as a version event. Otherwise Gate B proof moves to Oct 21. The trade must still be the agent's own decision: people never choose trades (never-do #1).

## Source-verified path and shared steps

Steps 1–5 and the evidence template apply only to verified mode. For the selected
untrusted path, use U-a–U-d below, then shared steps 6–12 with that policy pair
and the UNTRUSTED startup label. The signer remains offline from RPC. Neither
mode removes #27/#44, fresh full holdings, fee/gas, host or ACK requirements.
LD06 adds [opt-in zero-only allowance recovery](ALLOWANCE_RECOVERY.md) across
tokens/final exits, with policy/gas/timing/host acceptance still required. LD05
must disposition anomalous fills. LD07/PR199 chooses initial gas only. LD08-OG01 adds explicit initial-only
profile/mapping/signer candidates and stock-only cap/assembly coverage for review.
Measured whole-run seeding/full-exit reserve, low-gas incident/alarm and actual
profile/host acceptance remain open. Legacy top-up profiles still require native
qualification. Setting `native_trace=false` alone does not select initial-only scope.

| # | Who | Step | Done when |
|---|---|---|---|
| 1 | Isaac (own machine, browser) | Open BscScan for router `0xb44446b0c8e56988c34f7ff73ae904982b5fdda5`, the quote's `tx.to` (EXP-005). If it is a proxy, follow "Read as Proxy" to the implementation. Save the verified source and ABI **outside Git** and record their SHA-256. **If the source is not verified, stop:** GAP-29 cannot close from evidence; take it to the team. | Source and ABI hashes recorded |
| 2 | Isaac | Find the swap function whose selector is `0xad43f73d`. Write its canonical signature, with structs as tuples (`(address,uint256,...)`) and canonical types (`uint256`, not `uint`), then check it with `python -m larp.execution_live.router selector --signature '<signature>'`. | Selector matches |
| 3 | Isaac, Keegan reviews | Read the complete router/implementation/nested-call source and confirm four things: the minimum output is checked on the **recipient's** balance; the deadline is enforced; the input is pulled only from `msg.sender`; and **all wallet token debits are limited to the decoded pay token and at most its decoded amount**, including nested calls and any existing approval authority. Sender-only pulling does not prove that amount bound. Note the address the router uses for native BNB. If any of these four is false, stop and record why. | Both have read it; IDEA-070 records the finding |
| 4 | Isaac | Fill in `config/execution/router-evidence.v1.json` (template below; public data only) and commit it through a reviewed PR. | Merged; file SHA-256 noted |
| 5 | Isaac | Run the recorded-route check on the IDEA-063 capture artifacts (prompt 1): `python -m larp.execution_live.router check --evidence config/execution/router-evidence.v1.json --sha256 <file sha256> --artifacts <capture>/artifacts --out <outside repo>/router-check.json`. It must report `PASS`, which needs both directions. Add the report's hash to IDEA-070. | `PASS` |
| 6 | Team | Decide #27 (above), and the signer's per-token caps and fee cap (#44 WR-C). Use the approved policy and exact hash; do not install the unapproved example caps. `allowed_spenders` must name the router. | Decisions recorded with dates |
| 7 | Isaac / approved operator | Reconcile current wallet/in-flight state and funding/no-further-funding disposition (#106) before any eligible remaining first-gas step under the existing F-120 procedure. Retain funding notes and capture full holdings after the last funding. An old 4-USDT target or historical receipt does not authorize another seed. | Fresh funded balance and disposition retained |
| 8 | Yao Zhu | Configs on the hosts: `router`, `router_evidence_file` (`/etc/larp/router-evidence.json`) and `router_evidence_sha256` in both `execution.json` and `signer.json`; `allowed_spenders` and the decided caps in `signer.json`. Rebind the manifest (`preflight --bind ... --service-config`). | `check` passes for both services; signer check reports local config/evidence scope only, signing disabled and no Gate B acceptance |
| 9 | Isaac / approved operator | Only after release/config/host acceptance and the separately approved signer session, place the protected key through the existing loader procedure. Expect `"swap_decoder": "VERIFIED"` with evidence hash, or `"swap_decoder": "UNTRUSTED"` with policy hash and DEV-23. | Exact mode/hash and loader ownership/release identity checked |
| 10 | Yao Zhu | Start `larp-execution`. Expect no exit 2. | Service running |
| 11 | Agent, watched by all | The first approve and swap come from the agent's own round, at minimum size, each with its decision record and an ACKed round log. Then run the crash tests at each execution step on the host (DR-04), the reservation checks (DR-05), and a shadow-day replay (DR-19). | DR-02..06 and DR-19 evidence in IDEA-039/042 |
| 12 | Keegan | Run `gate_b report` with inputs including `router_check`. Review Gate B item by item in IDEA-042. Apply the existing D-DN-02 conditional Oct21 rehearsal decision; record any actual shorter signed rehearsal as a deviation (GAP-04). | Gate B reviewed |

## Selected untrusted-router path replacing steps 1–5 (IDEA-070 B02-U, DEV-23)

The retained acquisition packet has no verified source for the router or swap
facet. This path replaces source steps 1–5 and the `router_evidence_*` pair in
step 8. B09-TRUST01 accepts the trust direction; actual reviewed policy/hash and
measured #44 limits remain open. PR200 provides finite authority; until measured L/m are set, the observed long
encoded deadline still conflicts with short authority (#27). Trusted deadline behavior is an assumption,
and timeout never releases a possibly sent transaction's uncertainty.

| # | Who | Step | Done when |
|---|---|---|---|
| U-a | Operator, on primary | `python -m larp.execution_live.untrusted_router observe --rpc-url <approved balance RPC> --artifacts <fresh IDEA-063 quote capture> --out <outside repo>/untrusted-router.json`. It records the facet the swap selector dispatches to, both code hashes, and the head words all quotes share. | Draft written; facet is `0xa9fa1b56…` or the change is investigated |
| U-b | Named reviewer (not the operator) | Check the draft against IDEA-070 B02-U, then replace both `REVIEW_REQUIRED` values with their name and a dated review reference. The policy refuses to load until they do. | Reviewed policy and its SHA-256 recorded in IDEA-070 |
| U-c | Operator | `python -m larp.execution_live.untrusted_router check --policy <file> --sha256 <hash> --artifacts <capture>` must report `PASS` (every quote decodes to its own values, and every tampered copy is refused). Keep the report for `gate_b report` as `router_check`. | `PASS` |
| U-d | Operator | Put `untrusted_router_policy_file` and `_sha256` (never together with `router_evidence_*`) in both `execution.json` and `signer.json`, then rebind. The signer's start line shows `"swap_decoder": "UNTRUSTED"` and `"deviation": "DEV-23"`. | Both `check`s pass |

Before every swap step, primary re-checks at the latest block that the facet slot and code hashes are unchanged, and
that the router's allowance is zero for every other token (and at most the amount for the pay token, after the approve).
Any change refuses the swap. A fill whose settlement is refused (paying anything but the exact amount, or receiving
less than the minimum) withholds all further signing until it is resolved.
These controls do not establish a maximum loss or recover funds. Recipient,
nested-call debit and actual on-chain deadline enforcement remain unverified;
DEV-23 remains DRAFT until its scoped acceptance is complete.

## Source-verified evidence template

The values in angle brackets are placeholders, and the validator refuses them as written. Every value must come from the verified source; none may be guessed.

```json
{
  "schema": "RouterEvidence.v1",
  "chain_id": 56,
  "router": "0xb44446b0c8e56988c34f7ff73ae904982b5fdda5",
  "implementation": "<lowercase implementation address, or null if not a proxy>",
  "function": {
    "signature": "<canonical signature of the 0xad43f73d function>",
    "selector": "0xad43f73d"
  },
  "fields": {
    "pay_token": ["<argument index>", "<tuple index>"],
    "receive_token": ["..."],
    "amount": ["..."],
    "minimum_output": ["..."],
    "recipient": ["..."],
    "deadline": ["..."]
  },
  "native_sentinels": ["<address the router uses for native BNB>"],
  "source": {
    "verified_on": "bscscan.com",
    "url": "https://bscscan.com/address/0xb44446b0c8e56988c34f7ff73ae904982b5fdda5#code",
    "contract_name": "<as shown>",
    "compiler": "<as shown>",
    "source_sha256": "<sha256 of the saved source>",
    "abi_sha256": "<sha256 of the saved ABI JSON>",
    "retrieved_at": "<UTC time>"
  },
  "guarantees": {
    "minimum_output_checked_on_recipient_balance": true,
    "deadline_enforced": true,
    "input_pulled_only_from_sender": true,
    "wallet_debits_limited_to_pay_token_and_amount": true
  },
  "review": {"reviewed_by": "<Isaac + Keegan>", "review_ref": "<IDEA-070 entry or PR link>"}
}
```

Field paths count from 0. For example, `[0, 3]` is the 4th field of the tuple that is the 1st argument. A path may pass only through tuples, never into an array. Every ABI type, including unreferenced route arguments, must be valid and supported. The economic fields must sit in the top-level order struct, not inside the route steps.

RV-130: `router check` requires recorded chain 56, supported SWAP mode and token pairs, positive economics, every mutation check and both directions. Invalid JSON/approval evidence gives FAIL. DR-02 validates the full pinned report and every route recipient against the configured wallet; a standalone PASS flag is insufficient. These are synthetic-tested framework checks, not real source or host qualification.

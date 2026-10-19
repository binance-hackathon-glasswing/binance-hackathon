# Gate B: first signed trades on the dev wallet (IDEA-070)

Written 2026-10-16. Gate B turns the signer on for the **dev wallet** at minimum size. It starts the signed rehearsal, and is planned for review on **Oct 20** with the rehearsal from Oct 21 (DEPLOYMENT_BUILD.md). The dev wallet is not scored (F-122). This page is the order of work.

The repository side of the swap decoder is built (IDEA-070). Everything below needs a person, a host, the router's verified source, or a team decision.

Current PR reconciliation, lifecycle evidence and the offline current-input
signer-cap checker are in [Gate B remaining work](GATE_B_REMAINING.md)
(IDEA-039 GB-RW1). Source acquisition PR139 and the proposal/host dependencies
remain explicit; numeric cap coverage never enables signing.

## What changed in the code (IDEA-070)

- `larp/execution_live/router.py`: `RouterEvidence.v1`, `PinnedRouterDecoder` and the `selector` / `check` command line.
- The `Executor` now accepts live ports only together with a `PinnedRouterDecoder` built from hash-pinned evidence. Without it, nothing changes:
  - `larp-execution` exits 2 `EXECUTOR_CAPABILITY_GATE`;
  - the signer refuses `check` and `run` before database/key access (SR-01); it cannot start an approval-only path without its pinned decoder.
- New settings in `execution.json` and `signer.json`: `router_evidence_file` and `router_evidence_sha256`. The execution configuration accepts both or neither; the production signer requires both before check/run can pass.
  - The execution service refuses evidence for another router than its `router`.
  - The signer refuses evidence for a router outside its own `signing_policy.allowed_spenders`.
- The Gate B report (`python -m larp.execution_live.gate_b report`) accepts a pinned `router_check` file. DR-02 shows VALIDATED only for pinned evidence plus a passing recorded-route check, and still says the source review and a logged dev approve + swap are required.

## Two blockers besides the evidence

1. **#27 (team decision, C-OPEN-003). Resolve the signing-authority/deadline relationship and qualify real timing.** The planner caps an intent's life at the profile's 15 s; the kit states an approximate 30 s quote lifetime, but the real router's encoded deadline is not yet independently verified. `validate_payload` requires deadline ≤ intent expiry and refuses anything later (`encoded swap economics mismatch/expired`). Any encoded deadline beyond the parent expiry remains refused; the actual router timing still needs qualification. Options recorded in IDEA-049-C: (a) a measured, bounded signing lifetime; (b) a shorter, independently qualified router deadline. Keep the deadline check; don't remove it.
2. **A profile window that allows a buy before Oct 21.** The rehearsal profile opens new risk on Oct 21 00:00 UTC, so a Gate B trade on Oct 19–20 needs a team-approved dev window, registered as a version event. Otherwise Gate B proof moves to Oct 21. The trade must still be the agent's own decision: people never choose trades (never-do #1).

## Order of work

| # | Who | Step | Done when |
|---|---|---|---|
| 1 | Isaac (own machine, browser) | Open BscScan for router `0xb44446b0c8e56988c34f7ff73ae904982b5fdda5`, the quote's `tx.to` (EXP-005). If it is a proxy, follow "Read as Proxy" to the implementation. Save the verified source and ABI **outside Git** and record their SHA-256. **If the source is not verified, stop:** GAP-29 cannot close from evidence; take it to the team. | Source and ABI hashes recorded |
| 2 | Isaac | Find the swap function whose selector is `0xad43f73d`. Write its canonical signature, with structs as tuples (`(address,uint256,...)`) and canonical types (`uint256`, not `uint`), then check it with `python -m larp.execution_live.router selector --signature '<signature>'`. | Selector matches |
| 3 | Isaac, Keegan reviews | Read the complete router/implementation/nested-call source and confirm four things: the minimum output is checked on the **recipient's** balance; the deadline is enforced; the input is pulled only from `msg.sender`; and **all wallet token debits are limited to the decoded pay token and at most its decoded amount**, including nested calls and any existing approval authority. Sender-only pulling does not prove that amount bound. Note the address the router uses for native BNB. If any of these four is false, stop and record why. | Both have read it; IDEA-070 records the finding |
| 4 | Isaac | Fill in `config/execution/router-evidence.v1.json` (template below; public data only) and commit it through a reviewed PR. | Merged; file SHA-256 noted |
| 5 | Isaac | Run the recorded-route check on the IDEA-063 capture artifacts (prompt 1): `python -m larp.execution_live.router check --evidence config/execution/router-evidence.v1.json --sha256 <file sha256> --artifacts <capture>/artifacts --out <outside repo>/router-check.json`. It must report `PASS`, which needs both directions. Add the report's hash to IDEA-070. | `PASS` |
| 6 | Team | Decide #27 (above), and the signer's per-token caps and fee cap (#44 WR-C). Use the approved policy and exact hash; do not install the unapproved example caps. `allowed_spenders` must name the router. | Decisions recorded with dates |
| 7 | Isaac | MetaMask USDT → BNB first-gas swap on the **dev** wallet: about 4 USDT **total**, gas paid in USDT, before any agent trade (#106, F-120). Record each funding note. Yao Zhu then re-takes the opening balance capture (GATE_A.md) and `gate_b probe-chain` with the `finalized` RPC (#92) on the host. | Funded native balance in the chain capture |
| 8 | Yao Zhu | Configs on the hosts: `router`, `router_evidence_file` (`/etc/larp/router-evidence.json`) and `router_evidence_sha256` in both `execution.json` and `signer.json`; `allowed_spenders` and the decided caps in `signer.json`. Rebind the manifest (`preflight --bind ... --service-config`). | `check` passes for both services; signer check reports local config/evidence scope only, signing disabled and no Gate B acceptance |
| 9 | Isaac | Put the key at `/etc/larp/signer/wallet.key` (root, `0600`) on the signer host only. Start the signer. Expect `"swap_decoder": "VERIFIED"` with the evidence hash. | Start line shows VERIFIED |
| 10 | Yao Zhu | Start `larp-execution`. Expect no exit 2. | Service running |
| 11 | Agent, watched by all | The first approve and swap come from the agent's own round, at minimum size, each with its decision record and an ACKed round log. Then run the crash tests at each execution step on the host (DR-04), the reservation checks (DR-05), and a shadow-day replay (DR-19). | DR-02..06 and DR-19 evidence in IDEA-039/042 |
| 12 | Keegan | Run `gate_b report` with inputs including `router_check`. Review Gate B item by item in IDEA-042. **If Oct 20 slips, record the rehearsal shortfall as a deviation that day (GAP-04).** | Gate B reviewed |

## Untrusted-router alternative to steps 1–5 (IDEA-070 B02-U, DEV-23)

Step 1 stopped on 2026-10-19: neither the router nor its swap facet `0xa9fa1b56…e603` has verified source on BscScan
or Etherscan. Keegan chose to treat the router as untrusted rather than wait. This replaces steps 1–5 and the
`router_evidence_*` settings in step 8. It does **not** replace step 6 (#27, caps): adoption is Isaac's, together
with the #44 caps, and #27 is still required, because the swap's deadline is about 8 minutes after the quote.

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

## Evidence template

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

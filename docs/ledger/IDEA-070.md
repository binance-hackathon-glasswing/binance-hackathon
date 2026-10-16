# IDEA-070 — Gate B: a swap decoder pinned to router evidence (GAP-29, C-OPEN-004)

- Date / author: 2026-10-16 / Claude Code session, at the user's request ("fully work on creating Gate B"). Owner of the record it serves: Isaac (IDEA-039, GAP-29); reviewer Keegan.
- Status: open (criteria pre-registered; implementation follows in the same branch).
- What: the repository side of the last code blocker in front of Gate B. Today every swap is refused, because no decoder can prove what a swap's calldata does (`UnverifiedRouter`; `Executor` accepts fake bundles only; `larp-execution` exits 2 `EXECUTOR_CAPABILITY_GATE`). This change adds:
  1. `RouterEvidence.v1`, a document Isaac fills in from the router's **verified source on BscScan**: router and implementation address, the swap function's canonical signature and selector, where each economic field sits in the arguments, the router's native-BNB sentinel, the source and ABI hashes, and a named reviewer's confirmation of three properties read in the source.
     - The three properties: the minimum output is checked on the recipient's balance; the deadline is enforced; the input is pulled only from the sender.
  2. `PinnedRouterDecoder`. It decodes a swap only from that evidence, and binds the decoded fields to the bytes by requiring the calldata to re-encode to exactly the same bytes.
  3. A check tool. It replays every recorded `quote-and-swap` response (IDEA-063 capture artifacts) through the decoder, compares the decoded fields with what was asked for and quoted, and checks that tampered copies of each real route are refused.
  4. Wiring. The `Executor`, the execution service and the signer service accept a live bundle only with a verified decoder built from hash-pinned evidence. Without it, everything stays exactly as today: exit 2, and the signer refuses every swap.
- Why: C-OPEN-004 / GAP-29 is the one Gate B code item that needs no team decision. The evidence itself (the ABI) cannot be fetched from this session: BscScan, BSC RPC endpoints, 4byte, openchain and Sourcify are all blocked by its network policy, and no package on PyPI or npm carries the ABI. So the repository work is done here, and the evidence is left as an explicit input for Isaac. **Nothing here invents the router's ABI**: all decoder tests use a synthetic ABI and say so.
- Out of scope: #27 (a recorded team decision, C-OPEN-003); signer caps (#44 WR-C decision); first gas (#106); the signer key; hosted crash/HALT/restore drills; and the dev-wallet approve + swap. These need people, a host or money (see `docs/build/GATE_B.md`).
- Links: GAP-29, GAP-65, C-OPEN-004, EXP-005 (router `0xb44446b0c8e56988c34f7ff73ae904982b5fdda5`, selector `0xad43f73d`, calldata 1636–3172 bytes), IDEA-039, IDEA-049-C, IDEA-063, #33, #44.

## Pass criteria (written before any code exists)

All of these run offline on synthetic fixtures. No network, credentials or signing are involved. A synthetic fixture can never mark the real router as qualified.

- **R1 Evidence validation.** `RouterEvidence.v1` refuses each of the following:
  - wrong schema or chain;
  - an address that isn't lowercase 0x + 40 hex, or a router that is also a token;
  - a selector that differs from keccak-256 of the signature's first 4 bytes, or a signature that isn't canonical (for example `uint` instead of `uint256`) or doesn't parse;
  - a field path that is missing, out of range, passes through anything but a tuple, or ends on the wrong type (address for tokens and recipient; `uintN` for amount, minimum output and deadline);
  - any of the three guarantees not exactly `true`;
  - a missing reviewer, review reference or source/ABI hash;
  - an unknown or missing key.
- **R2 Selector hash.** Selector computation matches known vectors: `transfer(address,uint256)` = `0xa9059cbb`, `approve(address,uint256)` = `0x095ea7b3`.
- **R3 Byte binding.** On a synthetic ABI with a dynamic route array, a canonical encoding decodes to the encoded values. Each of these is refused:
  - another selector;
  - one trailing byte, or truncated data;
  - dirty high bytes in an address word;
  - a non-canonical dynamic offset;
  - `payload.to` that isn't the router.
  Changing the recipient, amount, minimum output, tokens or deadline in the bytes produces different economics, which `validate_payload` refuses against the intent.
- **R4 Native sentinel.** The evidence's native sentinel decodes as `NATIVE_BNB` (gas top-up route). An address not listed as a sentinel is never treated as native.
- **R5 Executor gate.**
  - Still refuses: live ports with `UnverifiedRouter`; a mix of fake and live ports; a "verified" decoder that isn't a `PinnedRouterDecoder`.
  - Accepts: all-live guards, venue and signer with a `PinnedRouterDecoder`.
  - All-fake bundles still work as before.
- **R6 Execution service.**
  - Without `router_evidence_file`/`router_evidence_sha256`: `build_execution` still raises `NotIntegrated('EXECUTOR_CAPABILITY_GATE')` (exit 2).
  - Start is refused when: the evidence hash differs; the evidence is invalid; the evidence router differs from the configured `router`; or only one of the two settings is given.
  - With valid evidence: the capability gate passes, and the venue and `Executor` use the same pinned decoder.
- **R7 Signer.**
  - Without evidence settings: swaps are refused as today.
  - With valid evidence: swaps decode through the signer's own pinned copy.
  - Start is refused when the evidence router isn't in `signing_policy.allowed_spenders`, or the evidence hash differs.
  - The start line reports `swap_decoder` as `VERIFIED` with the evidence hash, or `UNVERIFIED`.
- **R8 Check tool.** Over a directory of `Web3Observation.v1` artifacts:
  - every ok `aggregator/quote-and-swap` record is decoded;
  - the decoded pay token, receive token, amount and recipient are compared with the request's `fromTokenAddress`, `toTokenAddress`, `amount` and `userWalletAddress`, and the decoded minimum output with the response's `tx.minReceiveAmount`;
  - `tx.to` must equal the evidence router and any approve's `dexContractAddress`;
  - the per-route mutation set (selector, trailing byte, recipient, amount, minimum output) must all be refused.
  The report is `PASS` only if every recorded route passes and both directions (USDT → bStock and bStock → USDT) are present. It is otherwise `FAIL`, or `NO_ROUTES` when there are none. The report carries the evidence hash and the hashes of the artifacts it read.
- **R9 No regressions.** The full suite stays green against the baseline at integration head `eda2ed2`: Python 3.13.16 with PostgreSQL 16.15 in this session gave 1751 passed, 10 skipped, 0 failed.

## Results

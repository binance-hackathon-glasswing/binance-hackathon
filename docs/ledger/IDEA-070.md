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
- 2026-10-16: criteria committed at `fd3e4cc`, before any code existed. The code and tests were committed at `3df41a8`. Both commits were local until pushed with this record; the tests are offline and synthetic, so nothing ran live.
- Environment: Python 3.13.16; the locked subset of `requirements.lock` without the ML packages (eth_abi 6.0.0, eth-utils 6.0.0); local PostgreSQL 16.15. CI is Linux with PostgreSQL 14.24 and Python 3.12. This record does not include a CI run of this branch.
- **R1 PASS:**
  - `EvidenceValidation.test_each_defect_is_refused` refuses 25 defect cases (subtests);
  - the file-hash pin and the both-or-neither settings rule are tested.
- **R2 PASS:** `test_known_selectors` (`transfer` = `0xa9059cbb`, `approve` = `0x095ea7b3`).
- **R3 PASS:** `ByteBinding` refuses all 8 malformed variants and a wrong `to`:
  - another selector, a trailing byte, a trailing word, truncated data;
  - dirty address padding, a non-canonical dynamic offset;
  - odd-length hex, non-hex.
  `validate_payload` refuses 7 field changes against the intent: recipient, amount, minimum output, either token, deadline after the intent, and an expired deadline.
- **R4 PASS:** the native sentinel decodes to `NATIVE_BNB`; an address not listed as a sentinel stays as it is; a sentinel recipient is refused.
- **R5 PASS:** `ExecutorGate`.
  - Accepted: all-fake; all-live with `PinnedRouterDecoder`.
  - Refused: live with `UnverifiedRouter`; an imposter "verified" decoder; a fake decoder with live ports; mixed ports; fake ports with a pinned decoder; an unknown mode.
- **R6 PASS:** `ExecutionService`.
  - No evidence: `NotIntegrated`.
  - Pinned evidence: the gate opens, and the venue and Executor share one decoder.
  - Refused: hash differs; only one setting; another router configured; invalid evidence.
- **R7 PASS:**
  - `Signer`: no evidence means swaps are refused; pinned evidence decodes the swap inside the signer's own policy check, which now catches a wrong recipient; a router outside `allowed_spenders` or changed evidence is refused.
  - `SignerStartup`, on real PostgreSQL: the start line shows `UNVERIFIED`, then `VERIFIED` with the evidence hash; another router or a changed hash gives exit 4 `START_REFUSED`.
- **R8 PASS:** `RecordedRouteCheck`.
  - Both directions give `PASS`; a gas route with a router-side native sentinel gives `PASS` with `BUY`/`GAS`/`SELL`.
  - One direction gives `FAIL`. So do an amount, minimum-output or recipient mismatch, undecodable calldata, and an approve to another spender. No routes gives `NO_ROUTES`.
  - CLI exit codes: 0 PASS, 4 evidence refused.
  - The Gate B report shows DR-02 VALIDATED only with pinned evidence and a `PASS` check (`GateBReport` tests); the run stays BLOCKED and `signing_enabled` stays false.
- **R9 PASS:** full suite 1789 passed, 10 skipped, 0 failed, 2617 subtests (585.7 s), against the baseline 1751 / 10 / 0 at `eda2ed2` in the same environment. The difference is the 38 new tests.
- **Finding (#27):** a verified decoder does not by itself make a real swap signable. The planner caps an intent's life at the profile's 15 s, while a quote encodes a deadline of about 30 s, and `validate_payload` refuses a deadline after the intent's expiry. #27 (C-OPEN-003) is therefore a Gate B blocker as well, and `docs/build/GATE_B.md` says so.
- **Still open, with owners:**
  - Isaac: the real `RouterEvidence.v1` from the verified source, read together with Keegan; then `router check` = `PASS` on the IDEA-063 captures.
  - Team: the #27 decision; the #44 caps; a dev profile window before Oct 21 (or Gate B proof from Oct 21).
  - Isaac: first gas (#106) and the signer key.
  - Keegan: host configs and manifest rebind; the Gate B review in IDEA-042.
  - Everyone: DR-02..06 and DR-19 evidence on the dev wallet.
  The full order is in `docs/build/GATE_B.md`. GAP-29 stays open, narrowed.

## Review fix R10 (PR #130 review, 2026-10-17)

- Found while reviewing PR #130 after merging integration head `1ab47ae` into the branch (merge `42a934c`). The signer's `validate_config` enforces the both-or-neither rule for `router_evidence_file` / `router_evidence_sha256`, but the execution service's does not. So `larp-execution check` reports `configuration_valid` for an `execution.json` that sets only one of the two, and the service then refuses at `run` (exit 4, detail only `ContractError`). GATE_B.md step 8 uses "`check` passes for both services" as its done-criterion, so that check would pass a configuration the service cannot start with. Fail-closed either way: nothing signs.
- **R10 pass criterion (written before the fix runs):** `larp.execution_live.main.validate_config` raises `ContractError` when only `router_evidence_file` or only `router_evidence_sha256` is set, and still accepts a configuration with both or neither. A new test in `tests/execution/test_router_wiring.py` fails on `42a934c` and passes with the fix. The full suite stays at 0 failed.
- **R10 PASS** (fix `cfe015c`): `ExecutionService.test_check_refuses_half_set_evidence` failed on `42a934c` (both subtests) and passes with the fix; `validate_config` still accepts both and neither. Full suite at `cfe015c`: 1803 passed, 10 skipped, 0 failed, 2664 subtests (Python 3.12 from `deploy/requirements-test.lock`, local PostgreSQL 16.15). The merge `42a934c` alone gave 1802 / 10 / 0; the 13 tests over the PR's 1789 come from the integration branch (IDEA-066), the 1 more is R10's. `git diff --check` and `tools/render_deviations.py --check` clean.
- Review notes, not changed (judged not worth a fix): `router check` crashes rather than reporting `FAIL` when an ok `approve-transaction` artifact lacks `dexContractAddress`, or when a mutation overflows its uint type (no `PASS` either way); a real router that appends bytes after the ABI-encoded arguments would be refused on every route (by design; `router check` would show it as `FAIL` before any signing).


## RV-130 — Isaac-requested review and merge (2026-10-17, prospective)

Review original head `3c4b430` against integration `bb46234`; ordinary merge keeps IDEA-070, IDEA-075 and EXP-007 rows. Scope is repository framework only: real verified router/facet source remains unavailable (Isaac task3/#138/#139), and #33/GAP29, #27, #44, provider qualification, host provisioning and dev-wallet proof remain open. No live evidence is fabricated or installed.

Pass criteria before regression execution:
- **R11 / wallet debit authority:** the existing three guarantees do not constrain how much `msg.sender` can be charged or whether nested calls can use other token approvals. Require an explicit source-reviewed guarantee that wallet token debits are limited to the decoded pay token and amount across all nested route calls. Missing, false or truthy substitutes must refuse evidence; docs/template must explain the extra obligation. Synthetic fixtures assert only synthetic semantics.
- **R12 / valid ABI types:** reject signatures with invalid widths, zero-sized arrays or unsupported basic types anywhere in the arguments, including unreferenced route components, as ContractError at evidence load. Preserve supported canonical dynamic tuple/array routes.
- **R13 / recorded-route integrity:** chain56, SWAP execution mode/no RFQ, valid wallet, allowed USDT↔bStock or USDT→BNB pairs, positive amount/minimum/deadline/gas and matching decode are required for PASS. Malformed ok approval artifacts or invalid artifact JSON produce a non-passing report, not a crash or silent omission. Mutation values must stay encodable at uint boundaries.
- **R14 / report binding:** Gate B DR02 must require the actual successful report structure, nonempty route/artifact hashes, both BUY and SELL directions, no route problems, supported positive economics and the configured wallet on every route, in addition to the existing evidence/router/selector pins. A header-only PASS, another-wallet report, omitted directions/routes, changed pin or per-route error remains BLOCKED. Gate B overall/signing remain BLOCKED/false.
- **R15 / regression:** run pushed offline synthetic regressions first against the pre-fix code to reproduce these findings, then push fixes before rerunning. Run the focused decoder/wiring/execution/signer suite and the full suite with disposable PostgreSQL where available. No credentials, .env, provider/API, real key, wallet transaction, AWS or receiver access. Record exact environment/skips/CI limitations; local synthetic acceptance is not router or host qualification.

RV-130 RED at pushed `8381556`: targeted review regressions reported 29 failed / 8 passed / 3 subtests passed, including invalid ABI widths/types, absent debit guarantee, wrong chain/mode, zero/boolean gas, failed API response, malformed approval/JSON, uint overflow and header-only/wrong-wallet reports. Exact output retained outside Git at `/private/tmp/larp-pr130-review-red.log`. The earlier R10 note's tolerated malformed-approval/mutation crashes are addressed by R13. The new debit guarantee is a source-review obligation, not a claim about the unverified real router.

### RV-130 R16 — preserve the dependency-free offline boundary (prospective)

Packaging review finds an unconditional import of the ABI decoder in `Executor.__init__`, including all-fake bundles, and in execution config validation with no evidence. This introduces eth_abi/eth_utils into paths that previously needed no signing packages. R16: in fresh subprocesses whose import finder refuses eth_abi, eth_utils and eth_account, an all-fake Executor and execution config check without evidence still work; mixed/live-unverified bundles still refuse. Keep real ABI imports only on the live decoder path, and share the settings-pair check without importing the decoder. Stop the in-progress full run before changing code; rerun after the fix. The interrupted run is not a full-suite pass.

RV-130 R16 RED at `b6f0eb4`: fresh-process regression fails with `ModuleNotFoundError: signing dependency forbidden: eth_abi`. Fixed at `2628603`: ABI import only for all-live Executor validation; the settings-pair helper now lives in dependency-free execution config and is re-exported by router for compatibility. Pushed code before execution. Decoder/wiring/review group with PostgreSQL: 50 passed, 0 skipped, 93 subtests passed. Earlier full run was deliberately interrupted for this new packaging finding (327 passed so far); it is not reported as a complete pass. Final full run follows.

### RV-130 final review acceptance (2026-10-17)

R11–R16 PASS at pushed `91cfc7e` (implementation `2628603`): full offline suite **1840 passed, 9 skipped, 2736 subtests passed**, 262.94 s. Environment: macOS, Python 3.12.14, eth_abi 6.0.0, disposable PostgreSQL 14.24 (loopback-only Docker; no hosted database). Final focused decoder/wiring/review group: 50 passed, 0 skipped, 93 subtests, including PostgreSQL signer startup and the ABI-free fresh-process regression. Before the packaging fix, the broader execution/signer group passed 316 tests / 753 subtests. Logs retained outside Git as `/private/tmp/larp-pr130-review-{red,dependency-red,final-focused,full-final}.log`; the deliberately interrupted earlier full run is not a pass. `git diff --check` and `tools/render_deviations.py --check` pass. No .env/credentials, real key/signature/transaction, Web3/RPC/API, AWS or ai-seeds receiver action occurred.

GitHub Actions run [39017535732](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/39017535732), head `91cfc7e`, runtime job117352623646 annotation confirms the job was not started because recent account payments failed or spending limit needs increasing (#98). No org-CI pass, Linux/systemd acceptance, official host bundle or hosted/live qualification is claimed.

[Issue #152](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/152) tracks these completed repository review fixes and is the closing issue for PR #130. Parent #33 and source task #138 remain open; no entire GAP29 item is removed. Required next work: Isaac obtains real verified router/facet source and ABI, deployed implementation/bytecode attribution and all four source guarantees, with Keegan's independent review; Isaac runs the recorded-real route check. Actual on-chain deadline/authorization timing (#27), caps approval (#44), provider qualification, funding/key/host setup and logged dev approve/swap/rehearsal remain separate and blocked as previously recorded. The new debit guarantee is mandatory for future evidence; existing three-guarantee templates must be updated, never assumed true. This review supersedes the earlier record's inference of an actual approximately30s encoded deadline: only the kit's approximate quote lifetime was known.

## SP-01 — signed-prerequisite follow-through (2026-10-18, prospective)

User-authorized scope and pass criteria are recorded in
[the SP-01 contract](../build/SIGNED_PREREQUISITES_20261018.md). Source acquisition
gets bounded public rechecks; route replay remains conditional on truthful
RouterEvidence and independent review. Keith's interim artifacts are now present
in PR133; their delivery alone does not clear source, fees, current caps or gas.
No AWS, signer session or key operation is authorized in this workstream.

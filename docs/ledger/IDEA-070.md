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

### SP-01 R1 — acquisition stays blocked

Candidate facet BscScan403/Cloudflare, Sourcify404/no match at07:44:34UTC.
No verified source/ABI or independent four-guarantee review exists; router check
NOT_RUN. Exact handoff hashes verify; routes are available when source is ready.
Details and hash-pinned evidence: [SP-01](../build/SIGNED_PREREQUISITES_20261018.md).
No vendor message, synthetic ABI, source hash substitution or signing approval.

## SR-01 — signer startup prerequisites (2026-10-18, prospective)

Isaac requested implementation of the remaining signer preparation, preserving
separate PRs, no AWS changes and key placement only in Yao's approved session.
Baseline integration1306bbb still lets a dev signer use the explicitly undecided
example cap label. Its `check` command returns configuration_valid before loading
router evidence; `run` can start with UnverifiedRouter and sign approvals.
This is not a reproduced caps bypass: independent per-request policy checks
remain implemented. It is a premature-start/qualification gap.

Pass criteria written before execution:
1. Both production CLI modes (`dev`, `live`) refuse the example cap marker,
   including surrounding whitespace, for check and run before DB or key access.
   An arbitrary different label is not independent evidence of owner approval;
   exact numeric approval/profile/holdings and policy hashes remain #44.
2. Check and run require loadable hash-pinned RouterEvidence.v1 for a spender in
   the signer's own policy. Missing/changed/malformed evidence, invalid guarantees
   and another router refuse with exit4 before DB access or key loading.
3. A positive offline check uses the real decoder/manifest/config validation,
   reports the exact evidence hash and local scope with signing_enabled=false
   and gate_b_accepted=false. It does not touch DB/key/network or claim actual
   source provenance, independent review, registered-run/host/receipt acceptance.
4. Run retains registration/quarantine/build/wallet/key/authority checks; existing
   PostgreSQL command tests use explicit synthetic pinned evidence. A source edit
   between check and run refuses. No fabricated real source or adopted cap/L is
   introduced. Direct all-fake unit fixtures remain usable.
5. Push the regression tests/criteria before RED, then implementation before
   GREEN. Run focused startup/policy/router/authority regressions with a throwaway
   local PostgreSQL; record exact counts/skips. No wallet credentials, RPC,
   provider account, AWS, key placement, broadcast or official receiver access.

Remaining prerequisites are unchanged: real source and Keegan review (#139/#138),
recorded-real router check, Keegan's #27 lifetime decision/implementation and
real timing, measured #44 acceptance, native/provider/route-fee evidence,
funding reconciliation, exact signed bundle and Yao's provisioning/approved
signer session/hosted rehearsal. SR-01 does not claim the signer is ready.

SR-01 RED at pushed c7deec2: **21 failed,3 passed,2 subtests passed**
(including subtest failures; pytest's displayed counts),0.89s, macOS/Python3.12.14.
Check accepted missing/changed evidence and lacked local-scope/hash reporting;
run reached DB access first; dev and whitespace-wrapped pending cap labels were
accepted. Mock DB/key adapters proved ordering without network or real key use.
Log: `/private/tmp/larp-signer-readiness-red.log`.

SR-01 GREEN at pushed f9d0917: **139 passed,0 skipped,219 subtests passed**,
24.35s, macOS/Python3.12.14 with disposable PostgreSQL14.24. Command: pytest
`tests/signer tests/execution/test_router_wiring.py tests/execution/test_router_decoder.py tests/execution/test_router_review.py tests/execution/test_section_c_signed_state.py tests/execution/test_signing_request.py tests/runtime/test_service_configs.py`.
Log: `/private/tmp/larp-signer-readiness-green.log`. Existing PostgreSQL
registration/quarantine/key/wallet, immutable authority and malicious-intent
checks pass with explicit synthetic pinned evidence. Four new readiness tests
exercise both environments/commands, whitespace markers, absent/missing/changed/
malformed/other-router evidence and the local-only positive check. Evidence is
re-read on every invocation, so an edit after check is refused by run.

Implementation refuses the undecided marker rather than proving approval: a
non-example cap_basis string is still an operator assertion, not independent
owner approval. No cap number, proposal freshness, signing lifetime, router
semantics or runtime policy was adopted or weakened. Direct fake-unit signers
retain their existing UnverifiedRouter swap refusal for isolated tests; the
production CLI now requires pinned evidence before DB/key access. The shared
check/run precheck does not inspect registered-run state or host permissions;
run still applies its existing registration/quarantine/release gates afterward.
No new Linux/systemd/bundle or hosted acceptance is claimed from this local
suite. A reviewed signed release including this change is still required.

SR-01 delivery: [PR176](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/176)
is a separate open, non-draft PR targeting integration; implementation507d82b
contains tested sourcef9d0917 plus results only. No merge/installation is claimed.
GitHub run39133862711 runtime job117694306416 ran **zero steps**: its annotation
confirms recent failed account payments/spending limit (#98). This is not a
runtime-test failure or a CI pass; Linux/systemd/original signed bundle remain
open. The local disposable PostgreSQL container was stopped/disposed after the
139-test run. PR133 separately tracks SR-01 and the remaining source/lifetime/
measured-policy/provider/host inputs; no complete Gate B backlog item closes.

## B02-U — untrusted-router swap mode (2026-10-19, prospective)

**Why.** B02 (Keegan's source review) cannot be done: on 2026-10-19 Keegan
checked BscScan and Etherscan, and neither the router `0xb44446b0…fdda5` nor
the swap facet `0xa9fa1b56…e603` has published source. Findings recorded first,
all from public data:

- The router is a minimal diamond proxy (solc 0.8.23). It loads
  `facet = sload(keccak256(selector ‖ 0x5e12654f…a35c5)) & (2^160-1)`, then
  `DELEGATECALL`s with the full calldata. Unknown selectors revert with
  `FunctionDoesNotExist()`; empty calldata stops.
- On BSC the slot for `0xad43f73d` is
  `0x7ddc1c45a5ae31800e181de98e8cb97525e9b89f99e5829d49f25a8ca4bac1d7`. Keegan's
  CloudShell read returned `0x…02a9fa1b56f4d7bd25375c2d40b4c8e36a9509e603`, so
  the swap goes to facet `0xa9fa1b56…`. The router and the facet have identical
  code on BSC and Ethereum (Keegan's CloudShell `eth_getCode` hashes).
- On Ethereum the diamond has ownership write functions
  (`transferOwnership`/`confirmOwnershipTransfer`), so an owner can replace facets.
- All 15 recorded swap quotes in `quotes-interim-20261018/selected-raw` share one
  calldata layout. Words 1 = 0, 2 = `0x3d90f66b…6be9`, 7 = `0xd2a27f8f…a271`,
  3/4/5/6/8 = pay token/amount/receive token/minimum output/quoted output, and
  word 9 = offset 0x140 to a bytes blob. The blob is an inner call `0x47ee97ff`
  whose words 6/7/8/9/10 are pay token/receive token/amount/minimum (equal to
  or one more than the outer value)/a deadline (quote time + about 500 s).
  **The wallet address appears nowhere in the calldata.**

Keegan decided on 2026-10-19 to treat the router as untrusted, accepting that a
misbehaving router or inner call can cost up to one capped trade's input. This
work implements that decision. **Adoption is Isaac's (B09 signing policy); this
entry and its PR do not enable signing.**

**Design.** An `UntrustedRouterDecoder` from a pinned `UntrustedRouterPolicy.v1`
file. The guarantees it does not have are replaced as follows:

| Source guarantee (RouterEvidence) | Untrusted-mode replacement |
|---|---|
| input pulled only from sender; wallet debits limited to pay token and amount | exact approve (existing) + before each swap step, on chain: allowance(wallet, router) ≤ amount for the pay token and = 0 for every other pinned token; no native value |
| minimum output checked on recipient balance | NOT replaced: layout check only (outer and inner minimum ≥ intent minimum); settlement already refuses a below-minimum fill, and B02-U blocks further signing while one is unsettled |
| deadline enforced | NOT replaced: layout check only (inner deadline in (now, valid_until]) |
| code cannot change silently | before each swap step: facet slot holds the pinned facet, and router/facet code hashes equal the pinned values |

**Pass criteria, written before any implementation:**

- U1. On the 15 recorded swap quotes, the decoder returns exactly the quote's
  pay token, receive token, amount and minimum output (the `minReceiveAmount`
  field), with recipient unverified (`None`).
- U2. It refuses each tampered copy: another selector, a trailing or missing
  byte, any fixed word changed, a non-canonical address word, the inner selector,
  a mismatch between inner and outer amount/pay/receive, an inner minimum below
  the outer one, non-zero padding, a wrong blob offset or length, and a token
  outside USDT/bStocks (including native BNB).
- U3. With a fake RPC, `preflight` refuses: a facet slot pointing elsewhere; a
  changed router or facet code hash; a non-zero allowance for any other pinned
  token; a pay-token allowance above the amount; and any RPC error (as
  DependencyUnavailable). It passes the all-correct case. It reads only at a
  numeric block, using only allowlisted methods.
- U4. The `Executor` accepts a live bundle with an untrusted decoder only when it
  is bound to an RPC, and it runs `preflight` on every swap validation (prepare,
  authorize, sign, broadcast). `validate_payload` and `SigningPolicy.check` accept
  an unverified recipient only from an untrusted-mode decoder; a verified decoder
  that returns no recipient is still refused.
- U5. The signer and execution configs take `untrusted_router_policy_file` +
  `_sha256` (both or neither), never together with router evidence. The signer
  refuses a policy router outside `allowed_spenders`.
- U6. In untrusted mode, run authorization withholds `risk_valid` while any
  terminal swap of this run has no stored final fact (an unsettleable fill).
- U7. A DEV-23 deviation row (DRAFT) states the residual risk. The register
  renders, and the release-register tests pass.
- U8. Existing suites still pass with disposable PostgreSQL: execution, signer,
  router, settlement, Gate B and the release register.

Out of scope: booking a below-minimum fill (needs Keith's accounting), native-BNB
swaps (gas top-ups) in untrusted mode, the real policy file's code hashes (to
be taken by the operator with the new `observe` command), and adoption.

### B02-U results at `b800794` (2026-10-19)

Criteria were pushed first, at `3a179fa`. Python 3.12 on Linux with a
disposable PostgreSQL 16.

- **U1 PASS.** All 15 recorded quotes decode to their own pay token, receive
  token, amount and `minReceiveAmount`, with the recipient unverified.
- **U2 PASS.** All 15 tampered variants of every quote are refused (225 cases).
  One gap was found and fixed before commit: a blob length one byte longer,
  borrowing padding, had passed. Inner calls must now be a selector plus whole
  words.
- **U3 PASS.** All six refusal cases plus an RPC error are refused, and the
  correct case passes. Every read is at a numeric block and accepted by the
  production allowlist. Fixed during self-review: before this execution's own
  approve, the pay token's allowance is not limited, because our approve
  overwrites it. Without that, a leftover allowance after a reverted swap would
  block every later swap of the same token. A leftover on any other token still
  refuses, so after a reverted swap, sells of other tokens (including the final
  flatten) wait until an intent re-approves the reverted token. A revoke intent
  is a recorded follow-up.
- **U4 PASS.** The `Executor` refuses an unbound untrusted decoder, and preflight
  runs on swap validation. A verified-mode decoder returning no recipient is
  refused by both `validate_payload` and `SigningPolicy`.
- **U5 PASS.** Settings must be set as a pair (both or neither), and router
  evidence plus a policy together is refused. The signer refuses a router
  outside `allowed_spenders` and a policy whose hash differs, and loads the
  policy unbound.
- **U6 PASS.** On the halt-split service harness with real PostgreSQL,
  `risk_valid` stays true with no hold and turns false with a hold. The hold
  covers any terminal execution without its stored fact, which is broader than
  only swaps.
- **U7 PASS.** DEV-23 is DRAFT. The register renders and `--check` passes.
- **U8 PASS.** New tests: 13 passed, 255 subtests, including Gate B DR-02
  (VALIDATED only with a passing check for this policy, and labelled
  UNTRUSTED). Full suite at `b800794`: **2130 passed, 10 skipped (environment),
  3597 subtests**, 422.9 s.

Not done here: the real policy file (operator `observe` on primary, then a
named reviewer), a `check` on fresh quotes, a live preflight, Isaac's adoption
with #44 (B09) and B10/#27. The swap's own deadline is about 8 minutes after
the quote, so it still conflicts with short intent expiries. Signing stays
disabled; nothing here accepts Gate B.

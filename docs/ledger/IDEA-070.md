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

## RE-01 — Isaac checklist task 3: verified router evidence (2026-10-17, prospective)

Issue #138, separate branch `codex/isaac-03-router-evidence-20261017`, based on decoder PR130 head e5bd552. Task2's section C approval was explicitly given and recorded separately in PR137 / IDEA-062 NC-01 D1. This branch is stacked on PR130 for an evidence-only review diff; Keegan owns independent review and decoder merge. No production activation, AWS, credential/key access, quote capture, signing, broadcast or official-log upload. Existing captures belong to task4 after review/merge.

Criteria recorded before public source acquisition or covered-code execution:

- **RE1 provenance:** retrieve the BscScan verified source and ABI for `0xb44446b0c8e56988c34f7ff73ae904982b5fdda5`; determine proxy/implementation status from attributable evidence. Preserve exact downloaded bytes, UTC time and SHA-256 outside Git, under `/private/tmp/larp-isaac-router-20261017`. A block/challenge/unverified contract is INCONCLUSIVE and does not justify guessing an ABI or bypassing access controls. Public canonical explorer/API and attributable vendor sources may be read; do not send credentials to third-party services.
- **RE2 ABI:** derive the full canonical signature and economic field paths from the actual ABI/source; selector must be 0xad43f73d. Verify address/uint leaf types and source-native BNB sentinel. An unrelated selector registry or decoded quote layout alone cannot pass.
- **RE3 semantics:** cite concrete source functions/lines establishing recipient-balance minimum output, enforced deadline and sender-only input. Follow the relevant proxy/route/helper code. A false/unsupported guarantee prevents a truthful RouterEvidence.v1; record the finding and ask the team for a design decision rather than setting it true.
- **RE4 review/validation:** only commit factual public evidence, hashes and source-review notes; never claim Keegan has reviewed before confirmation. After code/evidence is pushed, validate evidence loading and selector with PR130's existing tool/tests if RE1–RE3 pass. Recorded-route checks, host configuration and enabling the signer remain later tasks. No deployable evidence is manufactured if acquisition fails.
- **RE5 completion:** separate PR references `Closes #138` only when this slice is satisfied; otherwise use `Refs #138` and explicit incomplete criteria. Narrow the live backlog, preserving #33/GAP-29 until source review, recorded-route proof and hosted execution requirements actually pass. No experiment or safety guarantee is declared verified from synthetic fixtures alone.

### RE-01 acquisition results (2026-10-17)

Criteria commit `455cb29` was pushed before acquisition. No covered code/test or runtime was executed. BscScan browsing and certificate-verified direct HTTPS GET returned HTTP403; retained HTML is a Cloudflare JavaScript/cookie challenge, not contract source. No challenge bypass or repeated automated retries were attempted. The documented Sourcify v2 lookup returned HTTP404 with `match`, `creationMatch` and `runtimeMatch` all null for chain56/address. This establishes only that no Sourcify match was returned, not that BscScan source is unverified or that on-chain code is absent. Search results for the address/selector did not supply attributable chain56 verified source; other-chain same-address listings are not source proof.

Raw response bytes/headers retained outside Git in `/private/tmp/larp-isaac-router-20261017`; safe response hashes/times and non-deployable status are in `docs/build/evidence/router-source-acquisition-20261017.json`. BscScan response saved 2026-10-17T05:38:48.829862Z, SHA256 f748132683130c90dd3abf03a9f9bafc360438c0a8eeaaa641d024b7e40d0126; Sourcify response saved 05:39:01.693527Z, SHA256 2f330bdf9094896e44b7944263122c48cc1ef34adfb4f99168a0a5dfce1a7a8b. These are response-body hashes, **not source or ABI hashes**.

Primary docs checked: [Sourcify API](https://docs.sourcify.dev/docs/api/) documents `/v2/contract/{chainId}/{address}?fields=all`; [Etherscan getsourcecode](https://docs.etherscan.io/api-reference/endpoint/getsourcecode) requires an API key and describes source/ABI/compiler/proxy fields. No API key was read, supplied or requested in chat; the authenticated API was not called.

**RE1–RE3 INCONCLUSIVE; RE4 blocked on actual source and Keegan review.** No canonical signature, economic path, sentinel, implementation or guarantee was invented, and no deployable RouterEvidence.v1 was added. Isaac was asked to open the explorer in a normal browser and provide a local folder containing public source + ABI (including any proxy implementation), or report that it is unverified/also inaccessible. `docs/build/ROUTER_SOURCE_REVIEW.md` is the concrete handoff. #138/#33/GAP-29 stay open. Task4 cannot run without truthful reviewed evidence and Keegan's PR130 merge; later checklist tasks are not bundled into this branch.

### RE-01 draft PR / input handoff (2026-10-17)

[Draft PR139](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/139) is separate and based on PR130's branch. It references #138 without closing it because source acquisition/review remains incomplete (RE5). On completion, add the closing reference before making the PR ready; do not merge this partial documentation handoff to close the task. #138 records the same missing input and ownership. Task2's explicit approval is pushed in separate PR137 at bced620. No user response to the source-folder request has arrived; dependent evidence/route work remains pending. All task3 work is committed/pushed; no app code was executed and no source/ABI or Keegan review is claimed.

### RE-01 B1 — Isaac browser screenshot (2026-10-17)

Isaac can open the exact router page in a normal browser and supplied its Contract/Code screenshot. The screenshot displays “Are you the contract creator? Verify and Publish your contract source code today!”, an “Add Custom ABI” button, and raw hexadecimal bytecode, without a published source viewer/ABI. This is direct user-provided visual evidence that **this router Code page is unverified**, superseding the prior unknown browser-page status. It does not establish that all delegated implementation/facet source is unavailable. The creation-code-address and exact-bytecode-match links are not proof of swap semantics.

The same screenshot exposes `Read Facets` / `Write Facets` tabs. Next read-only input: inspect `Read Facets` for actual facet addresses / selector mapping, especially selector 0xad43f73d, then inspect the relevant facet's source verification. A facet-based routing structure is a lead, not established source or guarantee evidence. No runtime code, ABI import, decompiler or transaction was used. Do not ask Isaac to verify/publish a contract they do not own or to add a guessed custom ABI. #138/PR139 remain incomplete/draft; the source/ABI guarantees and independent review remain outstanding.

Primary specification checked for the next investigation: [ERC-2535 inspecting facets/functions](https://eips.ethereum.org/EIPS/eip-2535#inspecting-facets--functions) defines read-only `facets`, `facetAddresses` and `facetAddress(bytes4)` selector lookup. This explains the investigation lead; the screenshot alone does not prove this router conforms or identify any particular facet.

### RE-01 B2 / RQ2 — facet UI failure and read-only fallback criteria (2026-10-17, prospective)

Isaac reports Read Facets says “unable to retrieve a valid contract ABI”. This is an explorer-UI failure, not proof that no facet/implementation exists on-chain. No further browser export is requested from that view.

Before manual public RPC diagnostics: at most ten requests across the already selected BNB Chain / NodeReal public development providers, no credentials/wallet/from field/signing/submission, no redirects, no access-control bypass, bounded HTTPS timeouts. Only `eth_chainId`, `eth_getBlockByNumber`, `eth_getCode` and the standard ERC-2535 read-only `facetAddress(bytes4)` lookup are considered here. Pin the lookup/code reads to the numeric finalized block returned by chain56; a missing/wrong chain/header or provider error cannot qualify a result. Preserve exact requests/responses and UTC times outside Git under the existing acquisition folder. The standard loupe signature is documented by ERC-2535; computing its selector does not guess the swap ABI. Production `Rpc`'s token-only eth_call allowlist is unchanged; these manual HTTP research requests cannot be wired into the agent.

**RQ2 pass:** a standard loupe lookup for selector0xad43f73d returns a nonzero, ABI-canonical address and nonempty code at the same pinned block; this is only a candidate implementation identity to follow for verified source, never a swap-ABI/safety/immutability proof. Any revert, transport/chain/header error, empty/malformed answer is INCONCLUSIVE. Do not infer missing selector support from transport error, and do not brute-force signatures/slots or broaden runtime permissions. If inconclusive, retain the blocker and prepare a vendor/team source request for Isaac to send; do not send messages externally.

Primary specifications checked: ERC-2535 `facetAddress(bytes4)` and Ethereum JSON-RPC `eth_call`/`eth_getCode`/block reads. No code/decompiler can replace the three required source guarantees. Source/evidence review and issue138 remain incomplete regardless of a successful lookup.

### RE-01 RQ2 results — candidate swap facet found (2026-10-17)

At pushed criteria b75f481, manual certificate-verified HTTPS requests to the selected public BNB provider returned chain56 and a finalized header at **0x7a2eb81**, hash **0xed600646f050ef598e02be50d553f6d9a75aae3b92c922fc9f72dd15c17dfbce**. Six JSON-RPC methods in three HTTP batches: chainId + finalized header; router code + standard facetAddress lookup; candidate code + the same numeric header. The final header hash agrees. No retries, wallet/from field, signing, submission, official logs, AWS or runtime adapter/config changes. `facetAddress(bytes4)` selector0xcdffacc6 was derived with Keccak-256 (disposable pycryptodome3.23.0 under `/private/tmp/larp-router-keccak-deps`; no global/project dependency change), with argument0xad43f73d left-aligned as ABI bytes4. This standard introspection signature is not a guessed swap ABI.

The canonical 32-byte lookup result is address **0xa9fa1b56f4d7bd25375c2d40b4c8e36a9509e603**. The router has180 code bytes; the candidate has8622 code bytes at that same height, code-bytes SHA256 **924e9da536e78a9ce92f633058a62907ee5834738947432d186e02b212a0d574**. **RQ2 identity lookup supported**, not source/swap/safety proof: this is a provider-observed, point-in-time candidate facet; no independent execution/storage proof, source verification or future mapping immutability is established. Code SHA256 is not a source/ABI hash.

The candidate's BscScan page is inaccessible to the browsing tool; its Sourcify v2 lookup returns404/null match, with no source/ABI. No indexed exact-address result was found. Isaac was asked to open the candidate's distinct BscScan Code page and report verified source versus Verify and Publish/bytecode. RE1–RE4 remain incomplete pending actual verified source and review; no deployable RouterEvidence.v1 or live capability change. Safe pinned lookup metadata is committed in `docs/build/evidence/router-facet-lookup-20261017.json`; raw requests/responses/headers are retained outside Git in the acquisition folder. JSON parsing and diff checks pass; no application test/runtime was executed for these documentation/status artifacts.

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


## RV139 — source-handoff PR conflict review (2026-10-17 SGT)

The user requests all-PR fixes. Decoder PR130 is merged, so this handoff now
merges current integration `a428bab` normally and targets that integration branch.
Resolved the backlog/ledger conflicts by retaining the current RV-130 four-source-
guarantee requirement and all RE-01 acquisition/lookup history; newer integration
rows are preserved. The old three-guarantee acquisition checklist is superseded
by RV-130's fourth, nested wallet-debit guarantee. No historical lookup output or
raw artifact hash was changed.

The PR remains DRAFT. Candidate code/selector attribution is not verified source,
ABI, spender approval or upgrade/semantic proof. No attributable source files or
actual capture corpus were supplied in this environment, so task138 and parent33
remain open. Updated the source-review handoff to use current merged code rather
than waiting for PR130. Validation: evidence JSON parses, ledger IDs are unique,
no conflict markers, and `git diff --check` passes. Documentation-only review;
no application, provider, wallet, host or AWS action is required or performed.

## SP-01 — source acquisition recheck (2026-10-18)

PR133 criteria946edfc precede public requests. Candidate Code403/Cloudflare and
Sourcify404/no verified match at07:44UTC; exact UTC/status/response hashes in
../build/evidence/router-source-recheck-20261018.json. No source/ABI obtained or
independent review invented. Keith handoff file hashes verify; route check
NOT_RUN until source/review. PR139 remains draft; #138/#33/signing remain blocked.
No AWS, key access, transaction, model/receiver call or vendor message.

## RE-02 — separate source-point follow-through (prospective, 2026-10-18)

User requests each immediate point in its own PR and reports no source export
available. Keep this source-only PR139 as that point's dedicated PR rather than
open a duplicate. Make at most three new public GETs with system curl/TLS,
20s/no redirects/retries: candidate Code page, public BscScan source API and
Etherscan v2 source API without account credentials. They are supported retrieval
alternatives, not Cloudflare/VPN/auth bypass. API authentication/deprecation
errors establish access blockers only, never verification status. Retain UTC,
status/error/response hashes; no complete source/ABI means no RouterEvidence,
source guarantee, review or route-check PASS. No vendor message or paid account.
Prepare the minimal export/vendor-request checklist, keep #138/#33 open and
PR139 draft. Validate JSON/hashes and diff only for this evidence/doc slice.

### RE-02 results / point2 dedicated PR

At10:59:10–11UTC: candidate Code403/Cloudflare; legacy source API301 (not
followed); v2 chain56 exact-facet source API reports Missing/Invalid API Key.
Source/ABI still absent and no user export/account access is available.
Report SHA2563d04c7186a398794f53b0818bd891ee3b09a80a8e8de541f261f3b00a85495e4. Request/body hashes never become source/ABI hashes.
Current intake/vendor packet is updated in ROUTER_SOURCE_REVIEW.md; no message
sent. PR139 stays draft; source guarantees/review/route check remain NOT_RUN.
JSON/source-byte hash/diff checks pass; no application test/runtime, key, signing,
wallet, official-log or AWS operation. No whole source/readiness item closes.

RE-02 final integration: normal merge of current integration preserves its
completed GAP30 removal and updated GAP31/32 qualification wording; retains the
exact source blocker under GAP29. Source PR139 remains draft, now synchronized
for review with no application-source delta from integration. JSON/response
hashes, no conflict markers and diff checks pass; no runtime test needed for
the documentation/evidence-only delta. No source/adoption/host gate closes.

## RE-03 — additional public source intake for signer readiness (prospective)

The current signer implementation request still provides no export/account.
Browser-tool BscScan router open returns403; facet open is inaccessible. Search
and Ethereum/Polygon pages identify the same address on other chains but do not
establish BSC source or facet/helper semantics. The Ethereum page is cached and
has no verified source listing; do not use its displayed runtime bytecode as
BSC deployment evidence. The browser tool cannot open the public Routescan
source API; that is a tool-access failure, not a contract verification verdict.

Try exactly two direct public Routescan Etherscan-compatible source GETs for
chain56 router and candidate facet. System curl, normal TLS,20s cap, no retry,
redirect following, credentials, paid service or access bypass. Record status,
response hashes and UTC outside Git, then summarize public responses. Pass only
on complete source/imports/ABI/compiler/settings with a verifiable deployed-code
binding; independent review and all four guarantees remain separate. Empty,
unsupported-chain or access-error responses retain source/review/check NOT_RUN.
No repeated blind probing after these two requests. No wallet/key/AWS operation.

RE-03 result: both bounded direct GETs returned HTTP200/status0,
`chain not supported` at13:59:09–10UTC. Source intake failed at provider
chain coverage, not verification status. Public report SHA256 `f7b24db6572f2c43e314dcc4daa99d83af588a5cb0a6cc93fa14424193f39047`;
body/length/JSON/hash checks PASS, no runtime test needed for this doc/evidence
change. No source guarantee/reviewer/ABI/code match was invented. PR139 stays
draft; real review and quote replay remain NOT_RUN. Source export/account
contact remains the next external input; no AWS/key/signing/vendor action.

## RV139-20261019 — independent review follow-through

Criteria before verification: preserve original reports and hashes, retain every historical ledger section, resolve integration conflicts, validate JSON/address identities/report hashes/false readiness flags and relative links, and add no application/config/tool changes.

Fixed the forwardable source request: the Oct17 browser finding is now dated and attributed; HTTP403 does not establish current verification status. Merged current integration and preserved SR-01 plus RE acquisition history. No actual source export or independent source review exists; #138/#33 remain open and PR139 remains draft until those acceptance inputs and the recorded-real route check exist. No new provider probe, vendor message, wallet or host action.

RV139 verification: nine documentation files only against merged integrationeb430b8; all relative Markdown links exist and whitespace checks pass. Five original JSON reports parse and are byte-identical to the pre-review head395f2c6; chain56 and all stored readiness/safety flags remain false. Alternatives SHA2563d04c7186a398794f53b0818bd891ee3b09a80a8e8de541f261f3b00a85495e4 and Routescan SHA256f7b24db6572f2c43e314dcc4daa99d83af588a5cb0a6cc93fa14424193f39047 match the handoff. No new source/provenance or current external observation is claimed.

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

## LD01 — mode-aware readiness and handoffs (2026-10-20; prospective)

Isaac-owned repository lane from PR133's current checklist, based on canonical
`2a997f4`. B09-TRUST01 and LIVE-PLAN01 are proposed in PR196; this change
references that existing direction without merging its branch or accepting a
real policy. No operator/provider/quote/private-key inputs are needed for this
reporting slice. Follow-on LD06 covers allowance recovery separately.

Pass criteria, before execution:

1. Signer assembly reports the selected verified/untrusted mode and only its
   applicable router review/replay gate; exact caps, hashes, named policy review,
   CA/run/DB binding and installation/signing/Gate B refusals remain intact.
2. Historical cap proposals can explicitly name either mode, retain all numeric
   values and pending policy labels, reject unknown modes, and require the
   applicable source review or untrusted policy review/replay/preflight.
3. Gate B DR-02/03 inventories and failure details name both supported paths
   accurately. Valid untrusted replay is never source verification or activation;
   missing/review-required/altered policy still refuses.
4. Current Gate B/signer handoffs distinguish the two mutually exclusive file/hash
   pairs and retain lifetime, caps, gas scope, allowance, abnormal-fill and host
   gates. Remove unconditional loss-bound claims, leaving DEV-23 DRAFT.
5. Record #138 as incomplete source-path work, optional for the selected path;
   #160's delivered technical handoff is distinct from actual approved assembly.
   Preserve historical artifacts and keep parent #33/#44/GAP-29/47 open.
6. Run focused offline signer/caps/Gate B/router regressions and documentation /
   deviation-render checks after committing and pushing code. No AWS, provider,
   model, wallet, signing, receiver or installation operation.

Results: pending. Review owner: Keegan; real policy/caps/host acceptance stays
with the owners in PR133. No entire deployment backlog item is completed here.

### LD01 results — source `22039ba` (2026-10-20)

Criteria pushed at `7a3e39b`; regressions pushed at `812b363` before execution.
RED: four reporting failures and one policy-refusal PASS (four subtests) on
canonical behavior. Implementation pushed at `baee1ee`; compatibility regression
and synchronized declaration table pushed at `22039ba` before the final tests.

- **Criteria 1–3 PASS:** focused signer, assembly, cap proposal/review, Gate B
  chain/native inventory, verified decoder and untrusted decoder suites passed
  **167 tests / 555 subtests / zero failures / zero skips** on Linux,
  Python3.12.15 and disposable PostgreSQL14.24. Source was mounted read-only;
  PostgreSQL had no external network and no persistent storage. Includes
  review-required, missing, altered and mixed-pair policy refusals; existing
  signing/accounting/recovery tests exercise the unchanged controls.
- Initial macOS/Python3.13 run: **116 passed / 517 subtests / 51 skipped** for
  missing PostgreSQL or signer dependencies. Those checks ran in the Linux
  result above; this is not a full-suite/systemd/CI or host-release claim.
- **Criteria 4–5 PASS (repository slice):** current GATE_B, GATE_B_REMAINING,
  SIGNER_CAPS_PROPOSAL and SIGNER_INSTALLATION_PREPARATION now distinguish both
  modes. Module/DEV-23 reason no longer assert a guaranteed loss bound; DEV-23
  stays DRAFT. #138 and #160 dispositions are recorded in the signer handoff;
  issue states were read, not changed. Historical proposal/draft/evidence bytes
  and pending numeric labels remain unchanged. Generated proposal wrappers now
  include mode-specific limitations; historical numeric candidates reproduce.
- **Criterion 6 PASS:** deviation renderer `--check`, whitespace, added local
  link targets, conflict-marker check, preserved backlog/index IDs and unchanged
  official-kit/vendor/env/historical evidence checks pass. All reports keep
  installation/signing/Gate B false. Disposable test DB is removed after use.

Independent Keegan review and canonical merge remain pending. LD06 remains
Isaac's next independent repository lane. Actual policy/holdings/timing/profile
inputs, gas-scope decision, measured #44 acceptance and release/host/session
qualification retain PR133's named owners. No real network/provider/model,
AWS, wallet/key, signing, receiver or installation action was performed.

Delivery: [PR198](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/198)
targets canonical `codex/system-testing-20261012`. PR133 was read and retained
unchanged as the noticeboard. All LD01 work is pushed; independent review/merge
and the open inputs/LD06 ownership above remain explicit handoff items.


### LD01-RV01 — PR198 independent review (2026-10-20; prospective)

Review requested with authority to fix findings and merge PR198 into canonical
`codex/system-testing-20261012`; reviewed source starts at `52c2349`. PR196 is
still OPEN; its B09-TRUST01 direction is independently confirmed in PR133's
current noticeboard. This review does not approve real policy/caps or installation.

Finding (P2): the active WR-C/#44 backlog entry still requires verified source
evidence for every production signer startup. That contradicts the dual-mode
loader and LD01's updated signer handoff, and sends the selected untrusted lane
back to the unavailable-source prerequisite. Correct the live entry to require
the selected pinned evidence/policy and applicable review/replay/preflight,
retaining numeric, host and key-session gates. No entire GAP is complete.

Acceptance criteria, before this review's test execution:

1. Rerun all signer tests plus mode-readiness, cap proposal/review, Gate B
   chain/native evidence, verified decoder/wiring/review and untrusted-router
   suites on Linux/Python3.12.15 with disposable PostgreSQL14.24. Both modes must
   retain policy/hash/refusal checks and false readiness/signing/acceptance flags.
2. Check deviation rendering, whitespace and changed documentation links; verify
   historical evidence, kit/vendor/env and runtime policy/config bytes are untouched
   by this review fix. Confirm remaining deployment owners/gates stay open.
3. Refresh head/base, reviews and mergeability before normal merge. Hosted run
   `39377020450` executed no steps: GitHub's annotation reports failed payments
   or spending limits. Local test results do not establish hosted CI or readiness.

Results pending. No AWS/provider/model/wallet/key/signing/receiver/installation
operation is part of this review. Existing user workspace files are preserved.


#### LD01-RV01 results — reviewed source `8cea019`

- **Finding fixed:** `8cea019` corrects both unconditional-source sentences in
  WR-C/#44; the selected pinned evidence/policy and applicable review/replay/
  preflight are required. The remaining numeric, release, host, session and
  deployment work stays open with its existing owners. No application code or
  numeric/config policy changed during this review.
- **Criterion 1 PASS:** independent focused Linux/Python3.12.15 test run with
  disposable PostgreSQL14.24: **200 passed / 600 subtests / zero skips**, 16.23s;
  `pip check` PASS. Suites: all `tests/signer`, plus execution mode_readiness,
  signer_caps_proposal, caps_review, gate_b_evidence, gate_b_native, router_decoder,
  router_wiring, router_review and untrusted_router. Source mounted read-only;
  the database had no external network or persistent storage, and the runner
  shared only its isolated network namespace. No production credentials supplied.
- **Criterion 2 PASS:** deviation renderer `--check`, diff whitespace and all
  eight added local documentation link targets pass. Historical evidence and
  signer drafts, official kit and vendor files are unchanged. Review fix changes
  only the live backlog and this record.
- **Criterion 3:** exact-head review and normal merge follow this results-only
  commit. The runtime/config/test/tool tree remains identical to `8cea019`.
  Hosted Actions are still unavailable due billing; this focused run does not
  claim full-suite/systemd/bundle, signed-release, host or Gate B acceptance.

Assistant review is complete for LD01's repository reporting slice under the
user's review/fix/merge instruction. Actual Keegan LD03 policy/hash acceptance,
Isaac LD06 allowance work, LD05 abnormal fills, LD07/08 gas scope, #27/#44 and
release/host/session/real-round acceptance remain with the owners recorded
above and in the live backlog. PR196 remains a separate OPEN documentation PR;
PR133 remains the noticeboard. This session does not qualify real router behavior.

## LD06 — bounded leftover-allowance recovery (2026-10-20; prospective)

Owner Isaac; independent review Keegan. Canonical base `06a93f9` includes reviewed
LD01. Scope: repository code/tests/documentation only, no wallet/provider/host
operation. LD07/08 gas scope and LD04 authority implementation remain separate.

Design proposed for review: optional pre-approval zero-allowance steps under the
next valid, risk-approved parent stock intent. Each step targets only USDT or one
of the five eligible bStocks and only the same pinned router; ERC20 approve amount
is exactly zero, native value zero. Maximum one step per token per parent, six
steps total. Every step has immutable identity, normal fresh gates/expiry/nonce,
fee cap and aggregate parent gas budget, durable signing/send/reconciliation and
receipt/gas/audit facts. No independent trade or authority extending the expired
parent is invented. Possible sends retain the wallet barrier. After cleanup,
re-read allowances, approve the actual pay token exactly, re-quote and swap.

Explicit execution configuration and signer-policy opt-ins default false. Old
configuration behavior remains fail-closed. A repeated nonzero allowance after a
confirmed revoke blocks, never loops. If time, gas, market, health, audit or risk
checks fail, stop/abort only positively unbroadcast work; a later independently
valid intent may recover the allowance. Cleanup failure does not fabricate a
fill or remove ordinary settlement quarantine. Actual reserve/gas sizing and
activation acceptance remain required; this change enables no production flags.

Source check: read `official/source_page.md` Rules & Restrictions and the
verbatim `official/kit/bstocks-trading-guide.md` approval/logging flow, core
F-96/99/100/105, G-01/04/18/19 and Q-07/09, plus participant-kit K8. The kit
specifies exact positive trade approval, not a revoke protocol. The zero-only
maintenance scope is a proposed team implementation policy supporting that
flow, not an organiser rule or a source-enforcement guarantee; it needs explicit
review and exact installed policy acceptance. No arbitrary token/spender/call,
manual approval or direct-RPC broadcast is introduced.

Pass criteria before execution:

1. Reproduce other-token/final-exit blockage from allowance left by approval
   without swap, reverted swap, and expired authority; fresh parent cleanup
   reaches approve/requote/swap with immutable identities across restart.
2. Both execution and signer independently refuse disabled cleanup, nonzero
   approval, unknown token/spender/selector/value, duplicate or misplaced cleanup,
   stale authority/nonces and excess per-step/aggregate gas. Six-token bound and
   at-most-once signing/send survive failures and uncertain outcomes.
3. Keep router/facet/code/layout and strict allowance preflight checks; RPC or
   receipt/reorg uncertainty blocks. Zero/nonzero allowance rechecks determine
   progress; no timeout or old parent's expiry clears possible-send uncertainty.
4. Canonical successful cleanup is an approval maintenance fact, not a fill or
   swap order/hash. Gas is accounted once, reservation retained except spent
   gas; reverted cleanup accounts gas and terminates the parent. Aborting after
   cleanup releases unsent swap reservations without pretending allowances reset.
   Actual PostgreSQL store/remote-signer/outbox/replay tests cover these paths.
5. Update current state machine/runbooks/backlog and ledger results truthfully;
   retain other GAP gates, no historical evidence/kit/vendor/secrets changes.
   Commit/push code before tests; run focused Linux/PostgreSQL and full runtime
   regressions appropriate to this execution/signing/accounting change.

Results pending; all implementation/configuration acceptance remains unclaimed.

### LD06 results — source `913b400` (2026-10-20)

Criteria pushed at `d732a2e`; implementation/tests pushed at `9a95363` before
execution. `8ee1b90` corrects an aggregate-gas fixture that originally hit the
earlier quote-gas admission guard; no gas limit was widened in product code.
`fad55e5` adds PostgreSQL recovery/configuration/exact-replay coverage.
`8a69f84` independently restricts cleanup to a stock parent and its exact selected
router. `913b400` adds malformed-step refusal and labels a confirmed cleanup
transaction without claiming its allowance has already been observed at zero.

**Criteria 1–4 PASS (offline implementation):** 23 new tests cover the original
other-token/final-exit blockage and recovery after no swap/revert/expiry; six-token
bounds and no repeat authority; original gas/nonce/expiry barriers; changed-code
and RPC refusal; PostgreSQL journal/registry restart; ephemeral-key isolated
signer policy/nonce/nonzero refusals; accurate canonical gas-only facts; audit
order/hash exclusion, reservation release and exact empty-target journal replay.
A final zero receipt is followed by a fresh allowance read; residual allowance
never causes repeated cleanup within the same parent. Defaults remain false.

**Criterion 5 PASS:** final full Linux/Python3.12.15/PostgreSQL14.24 run at
`913b400f7b0e2a9d5a6abfc97f6338d8a462c987`: **2190 passed / 3660 subtests /
zero failures / eight skips**, 138.73 seconds. Five skips are real-systemd tests
not enabled, two external fixtures unavailable, and one permission case skipped
under root. A separate unprivileged startup module run passed six checks,
including that permission case; its three PostgreSQL skips were covered in the
full run. No systemd or host-release qualification is inferred.

The initial full run had six environment failures (missing Git metadata, ignored
writable scratch output and bubblewrap namespace/proc permissions). Corrected
container mounts/permissions resolved them; no product bypass or test exclusion
was added. Source and Git metadata were read-only; test output used a separate
ignored scratch mount. PostgreSQL was disposable tmpfs with no external network.
Dependency check, sandbox tests, offline runtime demo (six journal batches/two
audit chunks), deviation rendering, whitespace, links/anchors, preserved backlog/
index IDs and unchanged historical evidence/default configs/kit/vendor/env pass.
Full machine receipt: [LD06 verification](../build/evidence/ld06-allowance-recovery-20261020.json).

**Not accepted here:** Keegan independent review of the zero-only supporting
policy/code; Isaac/Keith actual token/API behavior, measured cleanup/parent/exit
reserve and fee caps; LD02/04 timing/authority; LD15–21 release/host/session/real
agent-round and recovery acceptance. See [state machine and handoff](../build/ALLOWANCE_RECOVERY.md).
The core G-01 note is explicitly a proposed implementation exception, not an
organiser fact; DEV-23 remains DRAFT. All installation/signing/Gate B flags stay
false, no existing configuration opts in, and no real AWS/provider/model/wallet/
key/signing/receiver/installation operation was performed. PR133 remains a
noticeboard; parent GAP-29/47/#33/#44 and LD05/07/08 retain their remaining work.

Delivery: [PR202](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/202)
targets canonical. While it was being prepared, PR199's reviewed LD07 initial-gas-
only decision merged into canonical at db506bd; ordinary merge1f4b072 retains
both histories without conflict. Execution/signer/test/tool bytes are identical
to full-suite source913b400. The combined declarations pass renderer --check
and five release-register tests/three subtests; actual initial-gas/cleanup reserve
acceptance and LD08 implementation remain open. No extra full-suite result is
inferred from this documentation/register merge.

Org Actions [run39387215745](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/39387215745)
on581a70c ran zero steps in all four jobs; the runtime annotation explicitly
says account payments failed or the spending limit must be increased. Local
verification is not called hosted CI. Independent Keegan review/merge and the
actual acceptance owners listed above remain the explicit handoff. All LD06
changes are committed/pushed; no production operation is authorized by delivery.

## LD02 — operator execution packet from `primary` (2026-10-20; prospective)

Requested by Keegan to unblock LD03 (policy/hash review) and the #27 L/m choice
(IDEA-049-C LD04). One read-only script, `docs/build/ops/ld02-20261020/execution-packet.sh`,
runs on `primary` only (never the signer) and prints one sanitized JSON packet.
The host release is `ea25b52`, which predates `untrusted_router`, so the script
carries the canonical module's exact bytes (zlib + base64) and refuses to run if
their SHA-256 differs from the pinned value; the module is loaded in memory only.

**Pass criteria, written before the script is run (P1–P11):**

- P1. **Sanitized:** the packet contains no `://`, no Web3 key or secret, no
  wallet address, no DSN or IAM token, and no provider URL. Providers appear only
  as source ID plus a 16-hex SHA-256 fingerprint of the URL. If the final scan
  finds any of these, the script prints only a refusal and exits 2.
- P2. **No host writes:** Web3 and RPC artifacts are kept in memory; SQL runs
  `READ ONLY`; no file, service, config, ledger or AWS change. Hashes of
  `runtime.json`, `release.json` and the strategy profile are equal before and after.
- P3. **Identity:** host, run, build, release-manifest SHA, profile SHA, DB name,
  run version/epoch/quarantine, and one wallet fingerprint that is consistent
  across runtime config, `runs.wallet_id` and the ledger.
- P4. **Holdings:** a fresh finalized ChainBalances.v1 from the approved ordered
  balance providers, reconciled with the production `compare_balances` against
  the current ledger; reservations, pending commands, open rounds and the
  latest/pending nonces. Not a repeat of #92: no earlier check is cited as current.
- P5. **Router draft:** the canonical `observe()` drafts the policy from live chain
  state and this run's fresh quotes; the draft keeps `review = REVIEW_REQUIRED`,
  `signing_enabled=false`. Six-token router allowances are read at one numeric block.
- P6. **Quotes:** for each of the five bStocks, BUY at the profile's
  `minimum_trade_units` and `per_trade_cap_units`, and SELL at the minimum
  BUY's receive size, through the production `MarketPort.quote` with the
  profile's slippage. Each records request binding (tokens, amount, decimals),
  router, value, selector, round-trip ms, quoted gas, minimum vs quoted output,
  and the inner route deadline minus request time. Failures keep their outcome code.
- P7. **Timings:** RPC round trips per method and provider, quote round trips,
  and latest-vs-finalized lag (blocks, seconds) at start and end. Signer
  queue/sign/broadcast timings are recorded as `UNMEASURED` (no signer installed).
- P8. **Funding input for Isaac:** BNB holdings, gas price, quoted swap gas,
  indicative swap-only coverage and the exit-reserve comparison. Labelled an
  input pending LD09's measured approve/swap gas, not a funding decision.
- P9. **Execution RPC:** what `primary` configures for execution (expected:
  none) and the candidate source IDs with fingerprints, status
  `AWAITING_KEEGAN_CONFIRMATION`.
- P10. **Claims:** the packet states it is not native-trace, signed-path or #92
  evidence, and enables nothing.
- P11. **Local:** offline tests cover the sanitizer, the embedded-module hash,
  deadline extraction, quote binding and refusal paths; focused and full
  suites pass.

### LD02 results — script `2106d6c`, SSM `70965d91-0b91-4436-86f6-c33d8ffc2236` (2026-10-20 12:54 UTC)

Run by a Claude Code session for Keegan, through SSM `AWS-RunShellScript` on `primary` (a root shell; the script
itself is read-only)
(IAM user `larp-claude-session`). Packet SHA-256 as printed on the host:
`f0c7274d11121598fd40d20f12592d593006abc12ad6a465c627a234296dcaa4`. Committed copy
[ld02-execution-packet-20261020.json](../build/evidence/ld02-execution-packet-20261020.json)
is the same packet pretty-printed (indent 1) with the private hostname redacted (SHA-256 `ad43b634…c4ced4`),
so it cannot be re-hashed to the host value; the host bytes are retained privately.

**Superseded first run:** SSM `c89ef2c8-129a-4b46-818a-0a1e7bada96f` at `b70d623`
(packet `6ebf85a5…71bd3`) compared `exit_gas_reserve_units` with the BNB's USDT
value and reported `BELOW_EXIT_RESERVE`. The planner compares it with
`ledger.bnb_units` (wei). Fixed in `2106d6c` with a test that fails on the old
comparison; the rerun above is the packet of record. All other fields agreed.

- **P1 PASS.** No `://`, wallet, secret, provider URL/host or database host (final
  scan passed; independently re-checked: the only addresses are the public router and facet
  and fixed words 2 and 7, which also appear in the committed Oct 18 quotes). Providers appear as source ID plus fingerprint.
- **P2 PASS.** `configs_unchanged=true`; artifacts in memory; SQL `READ ONLY`; the script writes no
  file. (The SSM agent itself stores the command and its sanitized output under
  `/var/lib/amazon/ssm/`, as for every SSM run.)
- **P3 PASS.** Build `ea25b52`, run `larp-dev-llm-trial-20261018t170339z` (version 188,
  epoch 2, not quarantined), DB `larp_trial2`, mode dev, execution shadow. Runtime
  `8cb8fc74…`, release manifest `e592a13e…`, profile `d951207f…`. Wallet fingerprint
  `72afa2ee745685ab`, consistent across config, run and ledger; registered build and
  manifest match.
- **P4 PASS.** Fresh finalized read at block 128749659 by `BSC_BNBCHAIN_PUBLIC`:
  all seven assets MATCH (USDT 98.000000; BNB 2,694,498,869,362,886 wei; five bStocks 0).
  Nonce latest = pending = 2. No reservations, commands, pending executions or open
  rounds (70 rounds CLOSED); `settled_block` null.
- **P5 PASS.** Draft `346fa80d6bfcca605da2698b5b766eac26495cbcab2a6e27bd2344a991347ee1`
  at block 128749690 from 15 fresh quotes: router `0xb44446…fdda5`, slot
  `0x7ddc1c45…c1d7`, facet `0xa9fa1b56…e603`, router codehash `0xb6f35276…96a0`,
  facet codehash `0x5ae2caa1…8ba0`, fixed words {1: 0, 2: `0x3d90f66b…6be9`,
  7: `0xd2a27f8f…a271`, 9: `0x140`}, DEV-23, review `REVIEW_REQUIRED`. All six router
  allowances are 0.
- **P6 PASS.** 15/15 quotes OK, request-bound, pinned router and selector, zero
  native value, LiquidMesh. Binding is checked on `routerResult` (tokens, decimals,
  amount) plus router, selector and value; the fresh calldata itself was not run through
  `decode`/tamper checks (only the 15 Oct 18 quotes were, in LD03). Profile sizes: minimum 19.443104 USDT, cap 20.100000 USDT,
  slippage 16 bp (minimum output 16 bp below quoted in every row). Quoted swap gas
  250,000 everywhere. **Route deadline after request: 499.1–500.1 s** (both runs, 30 quotes).
- **P7 PASS.** Quote round trip 135–253 ms (median 143). RPC round trip to response
  headers 412–489 ms per call (medians 415–476) on both providers. Latest-to-finalized
  lag 0–1 block (0–1 s) at start and end on both; the two reads are about 0.45 s apart and
  timestamps are whole seconds, so the true lag can be up to about one block more. Signer timings `UNMEASURED`.
- **P8 PASS (input only).** 0.002694 BNB = 8.63 × the profile's exit reserve
  (312,320,854,920,000 wei); gas price 0.05 gwei; indicative 215 swaps at the quoted
  250,000 gas. Approve gas and LD09 measured gas `UNMEASURED`. This is Isaac's input
  against LD07, not a funding decision.
- **P9 PASS.** No execution RPC configured on `primary`. Candidates:
  `BSC_BNBCHAIN_PUBLIC` (`2e478f4aa0413423`), `BSC_NODEREAL_PUBLIC` (`e644968b15032fec`),
  both approved for development balance reads only. Status `AWAITING_KEEGAN_CONFIRMATION`.
- **P10 PASS.** The packet states it is not native-trace, signed-path or #92 evidence.
- **P11:** offline tests 11 passed / 11 subtests; a mutation of the sanitizer's URL
  refusal and the old reserve comparison each fail a test. Full suite: see below.
- **P11 full suite** (disposable PostgreSQL 16, Python 3.12): 2225 passed, 11 skipped,
  3692 subtests on the pre-fix tree, and the same again (442.7 s) at `2106d6c`. After the
  docs-only LD03/LD04-V01 edits, the 190 tests that read docs, ledger or evidence files pass.

## LD03 — Keegan's review of the observed router policy (2026-10-20)

Keegan **accepts** the LD02 draft as the reviewed untrusted-router policy (DEV-23).
Review checks, from the LD02 packet and the repository record:

| Check | Result |
|---|---|
| Router | `0xb44446…fdda5`, the kit router (module constant, B02-U) |
| Selector slot | `0x7ddc1c45…c1d7`, as computed in B02-U; it dispatches to facet `0xa9fa1b56…e603`, the same facet B02-U recorded on 2026-10-19 |
| Code hashes | router `0xb6f35276cf3608595df59a3cfa5fb06a3309e64e387b0ea4f60875fdc4c696a0`, facet `0x5ae2caa18a9d1d2dc528e6a1e9edf284883c023a617cc269b96620e4712d8ba0`, first pinned here (B02-U noted identical BSC/Ethereum code but recorded no hash) |
| Fixed words | {1: 0, 2: `0x3d90f66b…6be9`, 7: `0xd2a27f8f…a271`, 9: `0x140`}: identical to all 15 Oct 18 recorded quotes and to the test fixture; no economic word pinned |
| Fresh quotes | 15/15 bound at `routerResult` level to the request, pinned router and selector, zero native value; route deadline 499.1–500.1 s after request. Fresh calldata not decode/tamper-checked |
| Allowances | all six router allowances 0 at block 128749690 |
| Wallet | absent from calldata (B02-U), and the packet's sanitizer confirms the fixed words are not the wallet |

Reviewed file: [untrusted-router-policy-ld03-20261020.json](../build/evidence/untrusted-router-policy-ld03-20261020.json),
the draft with `review = {reviewed_by: Keegan (Weixuan Keegan Gan), review_ref: IDEA-070 LD03 (2026-10-20)}`,
written in `observe`'s own format. **SHA-256 `05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5`.**
`validate_policy` accepts it, and `untrusted_router check` against the 15 recorded quotes in
`quotes-interim-20261018/selected-raw` returns PASS (each quote decoded, each tampered copy refused),
`signing_enabled=false`. That local check is a sanity check, not Isaac's replay or live preflight.

Not claimed: source guarantees, recipient or nested-debit enforcement, on-chain deadline enforcement
(assumed, B09-TRUST01), or any maximum loss. The diamond owner can replace facets; the live preflight
re-checks the facet slot and both code hashes before every swap. **Execution RPC: not confirmed.**
Keegan's reply re-stated the Oct 19 approval of development balance reads only, which the host already
uses; no RPC is approved for execution. Next: Isaac pins the hash in `execution.json`/`signer.json`,
replays and runs the live preflight.

### LD02-RV01 — PR205 reviews and fixes (2026-10-20)

Two reviews of `215fc1f`: Keegan's (35 tests / 273 subtests with PostgreSQL; policy hash
and 15 historical replays confirmed; no host queried) and an independent subagent review
(23 passed / 1 skipped / 266 subtests; `ea25b52` signatures, embed hash, units and evidence
re-derived by hand).

Fixed before merge:

- **P2 (both reviews): the refusal output bypassed the final scan.** `code()` accepted
  hostnames, wallet hex and alphanumeric secrets. The refusal now emits only the exception
  type, plus one of the script's own codes from an explicit allowlist (`refusal()`). A new
  test feeds a hostname, the wallet (with and without `0x`), a secret-like value and a URL
  and checks none survives, and that the allowlist equals exactly the codes the script raises;
  putting the old `code(error)` back fails 5 cases.
- **P3 (both): wrong block.** The P5 router read and the LD03 allowance row cited 128749480,
  from the superseded first run; the packet of record says **128749690**.
- **Timing ranges:** RPC 412–489 ms (was 413–478); quote 135–253 ms and the 15 deadlines of
  record (LD04-V01 had cited the uncommitted first run's figures).
- **Wording:** "bound at `routerResult` level" for the fresh quotes, whose calldata was not
  decode/tamper-checked; the SSM agent's own files under `/var/lib/amazon/ssm/`; the evidence
  copy is reformatted as well as redacted; fixed words 2 and 7 are public addresses too;
  finality lag is biased low by up to about one block.
- The script's own RPC helper now uses the production `NoRedirect` opener.

The packet of record was produced by `2106d6c`. These fixes change only the refusal output
and redirect handling, neither of which affects a successful packet, so it is not rerun.
Offered as a follow-up, not done: decode-and-tamper checks of fresh calldata under the
reviewed policy in a new packet.

## LD02b — fresh calldata under the reviewed policy, and gas estimates (2026-10-20; prospective)

Follow-up from LD02-RV01 (the fresh quotes' calldata was not decode/tamper-checked) and
input for Keith's LD09 (all 3,848 DC-01 swap-gas figures are fallback). Same script and
safety contract as LD02 (P1–P2, P10 still apply), run read-only on `primary` only.

**Pass criteria, written before the script is changed or run (G1–G7):**

- G1. **Policy pinned:** the script carries the reviewed policy's exact bytes, refuses to
  run unless they hash to `05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5`,
  and reports whether this run's live `observe()` draft equals the reviewed policy apart
  from `review`.
- G2. **Fresh calldata:** the canonical `check()` runs on this run's 15 fresh quotes under
  that policy; each row reports `matches_quote` and `tampered_refused`, with an overall
  PASS/FAIL. A FAIL is reported, not hidden.
- G3. **Approve gas:** `eth_estimateGas` from the wallet for `approve(router, amount)` on
  each of the six tokens at the planned size. Only simulations: no transaction, signature
  or nonce use.
- G4. **Swap gas:** a USDT allowance state override is used only after the slot layout is
  proven on chain: the balance slot read at a numeric block equals the observed USDT units,
  and `allowance()` under the override returns the override value. Then `eth_estimateGas`
  on each minimum-size BUY's exact fresh calldata under the override. If the provider
  refuses overrides or the proof fails, the packet says so and no swap gas is reported.
  SELL swaps are not estimated (no bStocks held).
- G5. **Allowlist:** new RPC calls are limited to `eth_estimateGas` (from the wallet, value 0;
  to a pinned token with `approve(router, …)`, or to the router with exactly a fresh quote's
  calldata), `eth_getStorageAt` on USDT only, and `eth_call` for `allowance` only.
  Offline tests prove every other shape is refused.
- G6. **Reporting:** estimates are labelled simulated under the stated override at one
  block, not measured fills. They are LD09 inputs, not cap or seeding decisions.
- G7. **Local:** offline tests for G1, G2, G4 and G5 pass; the full suite passes.

### LD02b results — script `663cdf2`, SSM `8cdfb2b6-93d0-44a4-a3cc-70e6fe9943c8` (2026-10-20)

Packet SHA-256 as printed on the host: `18b68438f3ac0b75e7bb2c7dfbeee6c2cada800d47e6738640657c71444c9eec`.
Committed copy [ld02b-execution-packet-20261020.json](../build/evidence/ld02b-execution-packet-20261020.json)
is pretty-printed with the private hostname redacted (SHA-256 `f8e6e46b…9400`).

- **G1 PASS.** Embedded policy hash `05759e90…7957c5` verified; this run's live draft
  (`346fa80d…`, unchanged) equals the reviewed policy apart from `review`.
- **G2 PASS.** `check()` on this run's 15 fresh quotes under the reviewed policy: 15/15 PASS,
  each decoded to the quoted pay/receive/amount/minimum and every tampered copy refused.
  This closes LD02-RV01's open point: the fresh calldata is now decode/tamper-checked.
- **G3 PASS.** Approve gas (simulated, block 128777572, `BSC_BNBCHAIN_PUBLIC`): USDT 46,588;
  GOOGLB, MSFTB and TSLAB 55,231; NVDAB and SKHYB 55,243.
- **G4 PASS.** Slot layout proven: the USDT balance slot read equals the observed 98 USDT,
  and `allowance()` under the override returns the override. Minimum-size (19.443104 USDT)
  BUY swap gas under the override: GOOGLB 731,144; NVDAB 731,150; SKHYB 731,134; TSLAB
  731,976. **MSFTB: the provider refused the simulation** (`RPC_REFUSED`, most likely a
  revert); its quote itself was OK and request-bound. Not investigated further here.
- **Finding for LD09/#44:** simulated swap gas is about **731k, nearly 3× the quote API's
  `tx.gas` of 250,000** (and below the DC-01 fallback limit of 1,116,000). Approve plus
  swap is about 786k gas per pair. At the observed 0.05 gwei that is about 3.9e13 wei per
  pair; caps and reserves still need the cap gas price, not today's price.
- **G5 PASS.** Offline: 12 refused shapes plus the four allowed ones; a mutation that
  allows any `eth_estimateGas` fails 3 cases. **G6:** the packet labels these as
  simulations at one block, not fills. **G7:** 15 tests / 36 subtests; full suite in the PR.
- Unchanged from LD02: holdings MATCH (block 128777532), 15/15 quotes request-bound,
  deadlines 499.1–499.9 s, RPC 410–488 ms, exit reserve 8.63×, `configs_unchanged=true`.

### LD02b-F1 — why MSFTB's swap simulation was refused (2026-10-20; prospective)

LD02b's MSFTB minimum BUY simulation returned `RPC_REFUSED` while its quote was OK. Same script, safety contract
and allowlist; the only change is that a refused simulation keeps the provider's error, sanitized.

**Pass criteria, written before the change (F1–F3):**

- F1. A refused `eth_estimateGas` reports the JSON-RPC error code, the error message filtered to a short plain-text
  phrase, the 4-byte revert selector if the provider returns revert data, and the decoded text when that selector is
  `Error(string)` (`0x08c379a0`), also filtered. No other revert bytes are emitted; the final scan still applies.
- F2. A read-only rerun on `primary` reports the MSFTB result with that detail, plus the other four symbols again
  for comparison. Offline tests cover decoding, filtering and a refusal that carries a URL or value.
- F3. The finding is recorded as observed. No cause is asserted beyond what the provider returned.

### LD02b-F1 results (2026-10-20)

Three read-only runs on `primary` while the filter was corrected: SSM `3f4360e1…` (`bf69a13`) and `9ff2869a…`
(`4cde56a`) still filtered the reason; SSM `5f92fd74-844a-4602-9a14-69c811e9b963` at `877a4cc` (packet
`615e6e79…c240`; committed copy [ld02b-f1-execution-packet-20261020.json](../build/evidence/ld02b-f1-execution-packet-20261020.json),
hostname redacted) shows it. F1 and F2 PASS (17 offline tests; a URL or wallet in a reason is still dropped or
refuses the packet).

- **F3, MSFTB:** in all four runs the minimum BUY simulation reverted (`rpc_code` 3, `Error(string)`). The provider
  message: `execution reverted: adapter:0x7977f3e8e063a4ee95b5f396d63485dbdea4515d:Error(RFQ_OrderExpired …)`.
  MSFTB's route goes through an **RFQ adapter**, and the signed market-maker order inside it had expired by the time
  of the simulation, tens of seconds after the quote. Its quotes were OK and request-bound, and the outer route
  deadline was still about 500 s away.
- **Implication (observation, not a decision):** for RFQ-routed tokens the outer deadline does not bound execution;
  the inner RFQ order's validity is much shorter. The quote-to-sign path after the approve's finality must be fast,
  or the swap reverts and costs gas. That affects LD09 (MSFTB coverage), LD10 (gas budget for reverts) and the
  #27 margin, which assumed the 500 s deadline. Not yet known: the RFQ order's actual validity, and whether the
  quote response marks RFQ routes (to be read from the quote record). The untrusted decoder's checks are unchanged.
- **Swap gas varies by route:** over the four runs, minimum BUY simulations ranged GOOGLB 554k–731k, NVDAB 423k–731k,
  SKHYB 732k–749k, TSLAB about 731k. The 731k figure in LD02b is an upper observation, not a constant.

### B09-TRUST01 — Isaac selects the API-trusted behavior path (2026-10-19)

**Decision source:** Isaac, in the project conversation after the existing
checks, recovery behavior and unverified-contract risks were explained:
"Its ok, we will trust that the contract that binance API retrieves for us is
what the program requests for".

**Adopted scope:** use the existing B02-U / DEV-23 untrusted-router capability
as the deployment direction, accepting API-provided router behavior without
requiring verified router/facet source first. This is the router-behavior trust
decision, not completed B09/#44 numeric signing-policy acceptance. In code and
release records the mode remains UNTRUSTED; trust does not establish verified
recipient, minimum-output or deadline enforcement. Post-transaction detection
cannot reverse a loss. No unconditional loss bound is established.

Retain the existing pinned router/facet/code and calldata checks, exact approvals,
independent signer input/fee caps, allowance checks, durable attempts, canonical
receipt reconciliation and signing hold for an unsettleable fill. An unexpected
router/code change still needs policy review; this decision does not remove those
checks or automatically authorize every future API destination.

**Remaining before installation:** operator-observed, named-reviewed real policy
and its hash; fresh quote replay/preflight; measured profile/holdings and #44
caps; adopted/implemented #27 authority timing; qualified chain/native tracing
or explicitly reviewed supported scope; allowance/abnormal-fill disposition;
exact release/run/wallet/DB/CA bindings and approved host/session rehearsal.
Native-BNB swaps remain unsupported by this decoder. DEV-23 remains DRAFT until
its complete release acceptance. No config, readiness flag, wallet key, AWS
resource or live transaction is changed by this documentation decision.

**Verification:** documentation consistency and whitespace checks only; no
execution/provider/chain experiment is performed.


### LIVE-PLAN01 — API-trusted deployment continuation (2026-10-20 SGT)

Isaac requested a system-adjustment/deployment plan and a replacement checklist
on PR133 following B09-TRUST01. [The plan](../build/LIVE_DEPLOYMENT_PLAN_20261020.md)
maps LD01–LD24 to existing GAP/issues/DR gates with one accountable owner,
dependencies and completion evidence. It separates existing dual-mode capability
from source-only reporting, #27 authority, abnormal-fill accounting, allowance
liveness and the gas-scope decision; caps_review still requires BNB:BUY despite
the untrusted decoder rejecting native routes. No native omission, numeric
setting, changed readiness flag or deployment is adopted by planning.

PR133's current body/comments and open issues were checked, including the
retained Oct19 host report (#92 process health, partial snapshot, two UNKNOWN
charges, no native trace config). This session made no fresh host/chain/provider
observation. Required owners keep actual policy/profile/caps/source/model/host
evidence and final acceptance. PR196 carries this documentation continuation;
PR133 remains noticeboard-only. Validation: exact checklist-ID parity, local
link/anchor consistency and whitespace checks; no runtime tests or live action.

## LD02b-RV02 — Isaac review of PR211 (2026-10-21 SGT; prospective)

Isaac requests review and merge if possible. Review exact PR head `15fcc3f`
against canonical `e65f827` in an isolated prospective merge tree. Criteria:
RV1 inspect the complete diff/callers, reviewed policy/module byte pins and
state-override/size/block semantics; RV2 prove offline refusal/filter behavior
for malformed or out-of-scope RPC calls and provider error text, without network,
AWS, secrets or wallet calls; RV3 preserve observed packets and distinguish
provider-reported RFQ expiry/simulated gas from actual validity/receipt/cap proof;
RV4 run focused script/decoder/profile/document checks and record actual skips;
RV5 merge only an exact reviewed, pushed head with no blocking findings, retain
all LD09/10/host gates, and update PR133 with source/results. No live packet rerun
or trading operation is part of this review.

LD02b-RV02 reproduced findings at `15fcc3f`: RV-P2-01, an error with a known
credential beginning at character145 leaks its first15 characters because
`plain()` truncates before `sanitize()` sees the complete forbidden value. ASCII
replacement creates the same gap for Unicode values. RV-P2-02, `override_ok`
accepts any one USDT storage slot/value, not the declared wallet/router allowance.
Prospective fixes: scan full message/decoded reason against private forbidden
values before transformation, retain final scan; bind override to exact allowance
slot/value and reject malformed containers. New offline regressions precede fixes.
Original host packets stay unchanged; no live rerun is required for filter/guard
repairs, and historical results remain tied to their original source.

### LD02b-RV02 results — review fixes and merge qualification

Both findings fixed at pushed executable/test source `7fb82b1`. The regression
commit `99221e6` fails for the intended defects (five secret cases and two
arbitrary-override subcases); both pass with the fix. Full raw RPC messages and
decoded revert text are checked against the runtime's forbidden values before
truncation/ASCII replacement; final scanning and code-only refusal remain.
Override equality now binds the exact nested wallet/router USDT allowance slot
and fixed value, rejecting other storage/value/code/malformed containers.

Focused offline/integration verification on macOS arm64/Python3.12.14 with
**disposable PostgreSQL14.24: 96 passed /444 subtests /zero skips/failures**.
Includes19 packet tests, embedded policy/module byte identity,15 historical
recorded-quote decode/tamper checks, override proof failures, error filtering,
router decoder/review and real-PostgreSQL settlement/signer startup refusals.
Initial no-DB run was93 PASS/3 DB skips; all three subsequently passed against
the disposable database. This is local focused evidence, not a full-suite,
hosted-CI, fresh-provider or signed-host result.

Bash syntax, deviations rendering, whitespace and both archived packet
byte-identity/report-consistency checks PASS. Original packet digests remain
`f8e6e46b…9400` and `3ea88ee8…8fa5`; neither is regenerated or reclassified.
Provider-reported `RFQ_OrderExpired` supports an expiry failure observation;
the actual inner validity interval is unmeasured. Current backlog wording now
makes that distinction rather than treating quote-to-simulation delay as the
order's proven lifetime. Existing API-trust, LD09/10/#27 coverage, execution
provider/preflight, numeric policy and actual release/host gates remain open.

[Machine receipt](../build/evidence/pr211-review-20261021.json). Later changes
are documentation only; no new market/model/chain/AWS/key/wallet operation.
Merge/delivery receipt follows after checking the exact final PR head.

# IDEA-049-C — Isaac: actions review and fixes

## C-PREP-001 — prospective scope and preparation (2026-10-14)

User requests section C first, leaving the unclear Keegan/Isaac driver work untouched. Base is integration target `faf9adc`, carrying PR21 `5968b19` by ordinary merge. PR21 is open, so this is preparatory partial section work, not a completed common-protocol review. Driver orchestration and entry-point integration are excluded. No new runtime policy, live authority, secret access or host action is adopted.

Catalogue: `docs/build/final-review/C-catalogue.md`. Historical prior review context is disclosed there. The catalogue is derived from the named authoritative sources, without reading section C code in this turn before freezing. No section reviews or measurements are claimed complete.

## C-VERIFY-001 — prospective criteria

1. Commit and push the source catalogue before opening application code for phase 2.
2. Run unchanged pinned Python 3.12 full-suite baseline with secret-free discovery, artifacts outside Git. PostgreSQL/Linux/recorded-data limitations remain explicit; Linux CI provides independent complete engineering checks.
3. Map every requirement to actual code/test/verdict; map current prior C issues only after freeze. Add requirement-derived fail-first regressions for valid independent C defects, push before run, then push fixes before run. Do not edit driver, B policy, D runtime/audit/infra or applied migrations.
4. Focused C suite, full suite and section-branch system runner pass where available; obtain current-head Linux CI. Use real PostgreSQL for durable proof, not modeled dictionaries.
5. A second source/implementation pass finds no additional independent C defect. Unverified decoder/real native settlement, measured cost/funding/finality and excluded driver remain named open gates; no synthetic PASS as live proof.

Results: NOT RUN at criteria/catalogue freeze.

## For other sections

- D: apply shared ledger/backlog/runbook updates at integration; assign driver integration deadline with Keegan+Isaac. Formal package prerequisite pending PR21 integration.
- B: accept supported profile slippage/min-output/expiry constraints; C enforces them without selecting policy values.

## Requested shared edits

Add an IDEA-049-C row linking this record after results are published. Retain existing whole GAP items until their complete host/live evidence is verified. Specific remaining checks/results will be supplied as dated additions.

## C-BASE-001 — unchanged local baseline

Catalogue/criteria published at `5763c86`. Python 3.12.14 pinned environment, no credential file loaded. Initial sandbox run: 950 passed, 215 skipped, 1383 subtests, two loopback transport failures. Unchanged rerun with loopback permitted: **952 passed, 215 skipped, 1383 subtests** (13.74s). Logs are outside Git under `/private/tmp/larp-final-c-baseline*.log`; hashes will be recorded with final results. Skips include PostgreSQL, Linux isolation/systemd and external recorded-market evidence. This does not qualify hosted execution.

## C-FND-001 / C-REQ-014 — prospective slippage repair (#40)

P1: MarketPort/LiveVenue request fixed 50bp despite independently supplied lower profile limits. Add tests proving 20bp maps to `slippagePercent=0.2` in initial and post-approval quote adapters; mapping binds the independent limit into immutable Intent; invalid limits fail before I/O; strict LIVE consumer accepts byte-bound 20bp output and continues rejecting weaker minimum output. Preserve legacy 50bp default for unconfigured measurement/fixture callers only; production mapping must be supplied the accepted profile limit by its later owner integration. No profile value is selected or weakened.

## C-FND-002 / C-REQ-047/048 — prospective native quote producer (#30, quote side)

P1 dependency: no dedicated native quote producer. Implement an independently injectable native quote port in C, bound to USDT exact-in and native BNB output, explicit accounting scale, profile slippage, response hash and decoded payload/economics. Without verified route/gas/fee proof it exposes measurements but no executable quote. Test with the actual B gas planner, plus token/amount/recipient/min-output/deadline/proof tampering and non-default BNB scales. No native settlement contract is invented: transaction-bound native receipt proof and its B/D acceptance remain blocked. This does not close #30.

## C-FND-003/004 — owner dependencies, no silent policy repair

#24 maps to C-REQ-015: MarketPort preserves actual retrieval completion; Coordinator/ContextBuilder cutoff belongs to D. Request final cutoff after acquisitions with freshness/session/evidence revalidation and exact replay. Never backdate C output.

#27 maps to C-REQ-027: 15s proposal vs approximately 30s router deadline remains DECISION-NEEDED (B/C/D). Keep strict encoded deadline bound. Request measured router TTL/approval latency and explicitly frozen relationship between proposal freshness, signing lifetime and chain deadline. Do not weaken the validator or extend proposals in this section.

GAP29: no primary ABI/recorded route provenance currently qualifies a production decoder; keep UnverifiedRouter and signer swap refusal. Real first-gas, DR01 multi-day/weekend measurements, native finality/receipt capability and wallet switch remain NOT-OFFLINE. Excluded driver/entry-point work is untouched.

### C-RED-001 and follow-up criteria

At published fail-first tests `6072ce7`: **20 failed, 9 passed** including unittest subcases (native producer absent, fixed slippage/mapping). At implementation `89c6c53`: two top-level fixture failures remain (stock quote omitted required executionMode; native quoted output below the existing profile's minimum). Correct these synthetic external fixtures to satisfy unchanged contracts: SWAP mode and 241000 accounting native units, exceeding the profile's 240000 minimum. No consumer gate or production policy changes.

Additional prospective regression: integer percent conversion must preserve 1000bp as 10%, not strip the significant trailing zero. Initial/post-approval LiveVenue must reject a fresh minimum allowing 50bp when the immutable intent cap is 20bp, even if the initial intent minimum happens to be looser. Add/push these tests before running or fixing.

### C-VERIFY-002 — new native producer adversarial criteria

Focused C suite at `19dad67`: **167 passed, 41 skipped, 143 subtests**. Review of the new producer identifies missing independent checks on the verifier's payload primitives and gas scale. Before implementation: add tests rejecting malformed decoded transaction gas/price/nonce/destination/calldata even when echoed by the external fixture; native quote gas reservation must cover at least decoded payload gas × gasPrice in the declared accounting scale. Proof input must explicitly carry receive_decimals. Add tests before run/fix; 18-decimal valid synthetic proof must use chain gas units rather than the 6-decimal fixture allowance. Preserve all prior tampering assertions.

### C-INTEGRATION-001 — package prerequisite resolved

PR21 merged into the declared integration target while this preparation ran, at `c829fae` (2026-10-14 11:41:42 UTC). Ordinary synchronization merge `937da71` brings that target merge into C; executable/test tree is identical to `7cb113f`. Draft PR41 targets `codex/system-testing-20261012` and now contains C files only. Driver scope remains excluded per user. D must record the remaining driver deadline before overall completion.

### C-VERIFY-003 — coverage refinement criteria

The new test module imported a unittest fixture class, causing six existing tests to be collected again. Import its module instead; all sixteen C tests and original assertions remain. This is duplicate-collection cleanup after green checks, not removal of defect coverage. Add independent mutation subcases for each decoded native economic field and an exact-scale minimum-output regression; expired deadline and wrong recipient must each fail independently rather than relying on a compound invalid fixture. Publish before execution. Update final counts to exclude the accidental duplicate collection.

### C-VERIFY-004 — transport coverage criterion

The final trace pass finds POST signature assertions but no independent escaped-GET vector in C's transport tests. Add a fixed UTC timestamp vector containing comma, plus and space query characters; independently compute Base64 raw HMAC over exactly the sent URL bytes including `/build`, and assert GET has no body. This adds requirement C-REQ-007 coverage without changing transport implementation. Publish before run.

### C-VERIFY-005 — close independent decimal trace gap

Before execution, add an API-metadata fixture with eight bStock decimals and prove the declared receive scale reaches command mapping without hard-coded 18 or extra rescaling; mismatched declared scale must remain refused. C-REQ-006's trace gap is independently testable, so add actual proof rather than mark it host-only. Shared backup traversal (#23) and full balance reconciliation (#36) remain D/B dependency rows, with C diagnostic/receipt acceptance supplied. No new native receipt handshake or driver code.

## C-SOURCE-001 — decoder qualification remains inconclusive (2026-10-14)

Reviewed EXP-005's recorded router/selector verdict and IDEA-039's explicit next steps only after catalogue freeze. Read-only public recheck: the observed chain-56 router's [BscScan source page](https://bscscan.com/address/0xB44446b0c8E56988c34f7Ff73Ae904982b5FdDA5#code) was inaccessible through browsing. The vendor's [Quote API introduction](https://docs.liquidmesh.io/docs/quote-api) was read; it describes quote/swap endpoints and generated calldata, but that page supplies no attributable ABI/proxy/nested-route proof for the observed router. No verified decoder was obtained or invented. This is an inconclusive retrieval, not proof that no ABI exists. Other-chain address matches and selector databases are not chain-56 implementation evidence. C owns obtaining attributable implementation/ABI plus recorded response fixtures before any swap decoder is enabled.

## C-RESULT-001 — independent offline implementation verified; partial review

Final local tested code/tests/docs at pushed `5562cae`:
- New independent C regressions: **20 passed, 34 subtests**, 0.17s; all assertions retained. Includes profile-bound initial/re-quotes, fresh minimum output, percent conversion, exact escaped GET HMAC, non-default bStock/native scales, real resource-planner acceptance, independent native economics/payload/deadline/proof tampering, and gas allowance.
- Full Python 3.12.14 suite: **972 passed, 215 skipped, 1417 subtests**, 14.18s; +20 tests/+34 subtests versus published `5763c86` baseline. PostgreSQL/Linux/systemd/external recorded-data opt-ins explain local skips; no database crash proof is inferred from them.
- Focused C suite before the final GET/decimal additions (`c44ac2e`): **165 passed, 41 skipped, 155 subtests**. This count is not presented as the final focused tree.
- Linux CI at `531ce88`, [run 38560527713](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38560527713): all four jobs PASS; real PostgreSQL full suite **1182 passed, 4 skipped, 1525 subtests**; separate real-systemd **3 passed, 5 subtests**; mocked Terraform **15 + 1 passed**; pip check, offline demo, Docker smoke and offline AL2023 host bundle PASS. This preceding test revision lacks the final added decimal test; current-head CI remains required and is checked on PR41. No source-code fix has changed since `7cb113f`.
- `git diff --check` PASS. C diff touches eight allowed C files only. No applied migration, runtime/driver, B policy, D infra/audit, secret file or vendored/official file is edited. Nothing has been merged by this task.
- `tools/system_test.py` NOT RUN locally: no disposable PostgreSQL server and Docker daemon unavailable. Its cases are included in the Linux full suite, but that is not an invocation of the guarded CLI. D runs it on the final merged review tree with real disposable PostgreSQL.

Whole section/overall review **NOT COMPLETE; deployment blocked**. C independent quote repairs and boundary evidence are available for review in draft [PR41](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/41). The source catalogue has a trace for every row; WEAK and NOT-OFFLINE items remain explicit. A second pass over kit/declared conditions found no additional independent C implementation defect in the modified paths. This is not a proof that all driver, host, route or market assumptions are validated.

## C-OPEN-001..008 — remaining owners and acceptance (not implemented here)

| ID | Remaining work | Owner / later acceptance | Blocking |
|---|---|---|---|
| C-OPEN-001 | Excluded driver orchestration, build_driver and execution entry-point wiring; supply accepted profile slippage to mapping/market constructors | Keegan + Isaac, primary assignment/deadline still to be recorded by D; reviewed merged-driver PostgreSQL crash/command/round checks before whole-review completion | yes |
| C-OPEN-002 | #24 final cutoff after all acquisition; revalidate evidence, quote/session clocks and exact replay | D with C boundary acceptance; C preserves true retrieval completion; resolve before combined review closure Oct20 target | yes |
| C-OPEN-003 | #27 proposal freshness vs signing lifetime vs encoded router deadline | B/C/D team DECISION-NEEDED before Oct22 cut; qualify measured approval latency/TTL, preserve strict existing bound; no unilateral lifetime extension | yes |
| C-OPEN-004 | GAP29 attributable verified router/proxy/nested RFQ ABI/implementation and recorded response mutations | Isaac; chain-56 code/ABI hashes, payload variants, tokens/recipient/min-output/expiry tampering; before any signed-execution qualification | yes |
| C-OPEN-005 | #30 native transaction-bound balance/trace proof, accounting/receipt acceptance and dedicated round settlement; first BNB evidence Q03 | C with B/D; no invented receipt contract; separately qualified provider/actual receipt shape before execution; team owns first-gas resolution | yes |
| C-OPEN-006 | DR01 measured quote costs across all five names, ≥3 days including weekend, dated hashed artifacts and cost summary for B | Isaac; no live collection started here; before profile approval/Oct22 cut, record schedule slip if data cannot qualify | yes |
| C-OPEN-007 | Actual signer provisioning/LoadCredential, clock, RDS/role/finality/wallet-switch/registered rehearsal and signer version trust boundary | C+D; existing first-host/runbook checks, team-approved hosting and registered version; Keegan owns signer version binding decision; prior to host/rehearsal/live claims | yes |
| C-OPEN-008 | #23 backup traversal secrecy, #26 command durability, #28 pending-broadcast audit and #36 balance reconciliation | D owns #23/#26/#28, B owns #36 with C/D; C supplies signed-attempt/receipt/hash/scale acceptance; integrated final tree before live activation | yes |

No tracker issue or whole GAP is closed. #40 adapter boundary is repaired; accepted limits still need later production wiring/cross-section verification under C-OPEN-001. #30 quote-side component is supplied; native settlement and first gas remain open. The explicit user instruction to leave the unclear part untouched governs all these deferrals.

## Requested shared edits — exact text for D integration

LEDGER row:
`| IDEA-049-C | Final review C: profile-bound quotes and native gas quote producer | partial (independent offline changes verified; driver/live gates open) | 56 source-derived requirements; 20 new regressions; local 972 passed / 215 skipped / 1417 subtests; latest Linux evidence and C-OPEN-001..008 in record; PR41 | 2026-10-14 | [ledger/IDEA-049-C.md](ledger/IDEA-049-C.md) |`

Backlog addition (retain existing GAP lines and pending issue ownership):
`IDEA-049-C / PR41 supplies profile-bound initial/re-quotes, strict fresh minimum-output checks and an injectable byte-bound native-gas quote producer. C-OPEN-001..008 remain blocking: driver/entry-point/profile wiring, final acquisition cutoff, lifetime decision, verified decoder, native receipt/first gas, measured costs, real-host/final-wallet/rehearsal and D/B shared audit/reconciliation acceptance. Owners and evidence are in docs/ledger/IDEA-049-C.md. No whole GAP is closed.`

Runbook addition:
`Before signed execution, verify C-OPEN-004/005/007 on the registered reviewed build: attributable router/proxy/nested ABI and actual unsigned response hashes; chain-56 nonce/canonical-finality/transaction-bound native proof; first-gas evidence; signer credential permissions and clock; accepted profile limit propagation; final wallet namespace and manifest binding. Require C/D acceptance and real logged rehearsal before live readiness. Native quote fixtures alone are not production capability evidence.`

Shared index/backlog/runbook files are not edited by C. D applies these additions and records closure only after combined verification. There are no unpushed C commits at the final push; main promotion and PR merge remain separate team decisions, so full repository handoff readiness is not claimed.

### C-ARTIFACT-001 — external verification artifact hashes

| External artifact | SHA-256 |
|---|---|
| `/private/tmp/larp-final-c-baseline-allowed.log` | `760430601b84f91162fecf51bf642ec74499828c54fe2d3afc0e1d991c13a3c5` |
| `/private/tmp/larp-final-c-red.log` | `f5dc53c29f49babd946b0abbd04719698b9fbe3a18f0f2f94cfd0f7da0de6390` |
| `/private/tmp/larp-final-c-red2.log` | `ea3672e2e9559e865b79aa759895fd4e03765cde1b115e1dfed8cc395d26203c` |
| `/private/tmp/larp-final-c-red3.log` | `eb81d0a26ecfcd34774bad1040a7d041ea8d12d391e39310abe600615d224375` |
| `/private/tmp/larp-final-c-20-regressions.log` | `856ceef055ed048f15d863483456360f62de0e69a1f3071c16c470f8e89e86ca` |
| `/private/tmp/larp-final-c-full-complete.log` | `15c1df0c03e0dbf72361b0a4bf949d0ecd93c4d5272b299bc3c98cfcd6eafa64` |
| `/private/tmp/larp-final-c-ci-531ce88.log` | `b7579a17c900b38cafc628634bf3bfec2578538c7d9b789c05cfbaf034b3c395` |

## C-RESULT-002 — final executable/test-tree Linux CI PASS

At `5562cae`, [CI 38561158742](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38561158742) passes all four jobs: **1183 passed, 4 skipped, 1525 subtests** with disposable PostgreSQL; separate real-systemd **3 passed, 5 subtests**; mock Terraform **15 + 1 passed**; pip check, isolated demo, Docker smoke and AL2023 host bundle PASS. This includes all twenty new C regressions and the final non-default bStock decimal check. Local baseline/full evidence and all remaining C-OPEN items remain as above. Subsequent C commits only document these results; application/config/test/deployment/tool trees are identical. Current-head CI is visible on PR41 and checked separately; no host, driver or live capability is implied by it.

C-ARTIFACT-002: `/private/tmp/larp-final-c-ci-5562cae.log` SHA-256 `dff2d96fa3b47931302bc8a3f4c46fcb2c3b63d052de8f631799566f614a2866`.

## C-VERIFY-006 — final consumer quantization compatibility

Second integration inspection finds that the existing B consumer explicitly uses `floor(output*(10000-slippage_bps)/10000)` in native chain units, while new C raw quote checks required the exact rational bound. For non-divisible output this can reject a valid API minimum by one indivisible unit. Before the fix, add/push tests accepting the exact consumer floor and rejecting floor-minus-one; apply the same existing convention in stock re-quotes and native quotes. No profile cap or consumer gate changes. Native conversion to an accounting scale remains exact: this does not permit rounding a chain minimum down to a coarser accounting scale.

## C-RESULT-003 — final rounding revision, superseding earlier counts

C-VERIFY-006 red tests at pushed `2ec3ae8`: **2 failed, 21 passed, 34 subtests**; both failures are exact-consumer-floor minima. Fix `a47056d` changes only the two raw quote minimum comparisons to the existing B integer-floor convention. Floor-minus-one is still refused, and coarser native accounting conversion still requires exact representation. No profile value or existing consumer validator changes.

At pushed `a47056d`: **23 independent C regressions passed, 34 subtests**, 0.15s; complete local suite **975 passed, 215 skipped, 1417 subtests**. This is +23 tests/+34 subtests over `5763c86`, with unchanged environmental skips. Earlier C-RESULT-001/002 are dated evidence for their exact revisions, not proof of the rounding change. Current PR41 Linux CI is required for this last code/test tree and checked before finishing; subsequent commits only document this evidence and preserve the exact application/config/test/deployment/tool trees. Latest CI status and final counts are attached to PR41. Full review/deployment remains blocked by C-OPEN-001..008; no driver or live action is added.

Replace the earlier requested ledger/backlog counts with **23 new regressions; local 975 passed / 215 skipped / 1417 subtests**, and retain the partial status. All earlier ownership and exact requested runbook text stays valid.

C-ARTIFACT-003 (rounding revision):

| External artifact | SHA-256 |
|---|---|
| `/private/tmp/larp-final-c-rounding-red.log` | `889c1fd7f790d0e80761812507bca34e54e9aed06fe2d33c5700a40d10f57c0e` |
| `/private/tmp/larp-final-c-regressions-last.log` | `2d5e3a752a3e499ae9a9b5047da44bbe49d95e783e44ef58948a1a19bcc2a2f2` |
| `/private/tmp/larp-final-c-full-last.log` | `d5d223af9ef43d9414cb92364ce67abb63497ad92f14d5fd25d6d8050c3675ab` |

## C-RESUME-001 — merged-tree completion review (2026-10-15 SGT)

User now requests verification and fulfillment of section C requirements using the common protocol and C prompt. Worktree `/private/tmp/larp-final-c-20261015`, branch `review/final-c-20261015`, base `c1b6dafd62f8df7ea894a5177138da2726452696`. The existing independent catalogue was frozen and pushed at `5763c86`; its rows remain unchanged. This continuation uses dated amendments. Historical code exposure is disclosed, including the PR66 review.

Prerequisites checked through GitHub: PR20 merged into `codex/system-testing-20261012` at `faf9adc37e49daafbc2490a77b9871462c7c066e`; PR21 at `c829fae038a0589085d13552b1123802babbde4c`; PR66 at this base, `c1b6daf`. PR66 incorporates PR41 and completes the service-mode command/observation/round path over synthetic external ports. The production fake-only Executor, unverified swap decoder and native receipt gates remain; no signed live coverage is claimed. C-OPEN-001's former branch exclusion is superseded for integrated offline execution-side verification; D owns overall driver acceptance. PR66 includes R1/R2/R3 fixes of the previously posted review; validate these on the merged tree rather than reporting obsolete findings.

## C-VERIFY-007 — prospective resumed-review criteria

1. Before application/test changes, publish this amendment and run the unchanged full suite on the base runtime tree with pinned Python 3.12 and disposable PostgreSQL 14.24 if available. Record exact counts, environment skips, external log hashes and commit. No `.env`, registered wallet credentials, network probes, real signing/broadcast, uploads or AWS actions.
2. Reconcile tracker22 and current C-owned #24/#27/#30/#40 plus cross-section #23/#26/#36 against the frozen requirements. Verify actual assertions and current merged-driver boundaries; no issue closure alone establishes acceptance.
3. Recheck Web3 submission secrecy, response/failure contracts and endpoint/HMAC isolation; signer version/intent/resource binding, wrong wallet/hostile payload, durable single-sign recovery; canonical nonce/finality and settlement, including native gas. Add failing requirement-derived tests, commit and push before execution, then commit/push fixes before execution. Preserve live capability refusals pending attributable evidence.
4. Full suite, focused C tests, guarded `tools/system_test.py` and exact-tree Linux CI must pass for offline completion. Map each still-open MUST, assumption and decision to a named owner/deadline/check; request shared backlog/runbook edits from D. No new migration without D numbering coordination and no edits outside exclusive C paths.
5. Re-read all scoped authoritative sources and repeat adversarial boundary checks after repairs. Record new findings; do not claim whole section/deployment PASS while required live/host/measurement/decision evidence remains unavailable.

Baseline and resumed checks: NOT RUN at this pre-registration commit.

## C-BASE-002 — unchanged merged-tree baseline

At pushed `9733b21` (application/config/test/deployment/tool trees identical to base `c1b6daf`), Python 3.12.14 and pinned Docker PostgreSQL **14.24**: **1229 passed, 7 skipped, 1561 subtests**, 130.46 seconds. Skips: three Linux bubblewrap, three opt-in systemd and one external recorded-market artifact. Log `/private/tmp/larp-final-c-20261015-baseline.log`, SHA-256 `d97ab02fc059e31c833340f38eea57e3e8c0e8586cb733c4c5cee4cfe8c0135b`. Credentials excluded through a subprocess environment whitelist. Docker container `larp-final-c-postgres-20261015` binds loopback port 55466 only and is disposable.

## C-FND-005 — prospective reflected signed-byte secrecy repair

P0 under protocol severity, C-REQ-012/042, cross-section #23 acceptance: Web3Client hashes private request parameters but excludes their values from response reflection screening/redaction. A broadcast response can echo signedTransaction (including an escaped or overwritten duplicate-key value) into the parsed artifact or reversible response_body_base64. No real signature is used to reproduce this.

Pass criteria: broadcast success, business rejection and transport failures preserve their original outcomes and never retry submission; literal, prefixless, JSON-escaped, nested/key and duplicate-key echoes of the submitted synthetic bytes do not appear in returned/persisted diagnostic records or reversible raw-body exports. Untainted public response bytes retain exact evidence. Independently recompute POST HMAC over the captured body, and retain read/build vs submit-only endpoint separation. Publish tests and run red before fixing.

## C-FND-006 — prospective independent signer authority checks

P0 for version mapping; P1 for the existing HALT rule, C-REQ-037/043/049 and C-OPEN-007 (version aspect): the signer reads run epoch/quarantine but trusts version_valid/risk_valid in the primary's request. It does not compare the intent version with the authoritative registered build and its own release build, or reread a HALT raised after request creation. The signer role already has SELECT on runs; no added database privilege or decided policy is required for those comparisons.

Pass criteria with real PostgreSQL and throwaway keys: a queued request with true request gates is refused without invoking key signing if the run is now halted; a production run with missing registration, another registered build, another signer build, missing signer build, or wrong run wallet is refused. Matching production identities sign once and recover existing signatures. Repeat the authoritative HALT/version check under the signature-registry commit's run lock so a change after the service precheck cannot release new bytes. Receipt reconciliation/observation publication and retrieval of already-durable signatures remain available under HALT. Main passes its verified configuration build into the signer service. Offline synthetic fixtures may omit registration; an explicit mismatch or HALT is still refused there. No live gate is lifted, and complete journal/risk/resource trust remains cross-section acceptance, not implied by build comparison.

## For other sections — resumed scope

D applies shared index/backlog/runbook changes at integration, including removal of stale PR66-unmerged/driver-excluded statements only after verifying the merged-tree evidence. C fixes its own signer and venue paths. B/C/D still decide #27 lifetimes; native transaction-bound proof (#30), trusted chain balances (#36), backup traversal (#23), host access and measured costs retain the owners/deadlines in C-OPEN-003..008. No shared file or applied migration is edited here.

### C-RED-002 — first resumed red run and fixture correction

At pushed `670dbb2`, the new regressions report **16 failures, 5 passed, 5 subtests passed** (failure count includes six reflected-response subcases). Signed-byte reflection and signer gate/build/wallet bypasses reproduce. The matching-production positive test also fails later because the fixture changed the genesis wallet after journaling its registration; that intentionally violates journal identity and is not an application defect. Bind the throwaway wallet in setup before the first journal event, preserving all assertions and the independent wrong-wallet mutation. Re-publish and rerun red before application fixes. First log `/private/tmp/larp-final-c-20261015-red.log`, SHA-256 `2567ed34b492b17449712628613447ddd751eda9a4e68c9c20ad605137c3c253`.

Corrected red at pushed `9b15163`: **16 failures, 5 passed, 5 subtests passed**, 2.90 seconds. The positive matching-build/recovery test now passes; the late registry version-change test now reproduces actual release, rather than an invalid fixture journal. Log `/private/tmp/larp-final-c-20261015-red-corrected.log`, SHA-256 `25c6546ec0aee5de4356d12c1261486736e92234064bf8aadd5d223e354c50fd`.

### C-RETEST-004 — first repair run

At pushed `9d59556`, focused C plus integrated driver: **256 passed, 1 failed, 1 skipped, 223 subtests passed**, 51.80 seconds. All new requirement regressions pass. An existing stale-request test detects a changed refusal reason: the new run check executes before the immutable attempt/request authority comparison. Preserve its original `stale signing authority` disposition by doing that comparison first; keep all independent run/build/HALT checks before key use. No test assertion is changed. Log `/private/tmp/larp-final-c-20261015-focused.log`, SHA-256 `f4502ffb7a3325a10c6c80661f68ede08350b5d043f30a3559d3c9411d548705`.

### C-RETEST-005 — full repair pass and next adversarial criterion

At pushed `bc8d645`, full Python 3.12 / PostgreSQL 14.24 suite: **1244 passed, 7 skipped, 1572 subtests**, 134.42 seconds, +15 tests/+11 subtests against C-BASE-002. Log `/private/tmp/larp-final-c-20261015-full.log`, SHA-256 `34739d227d230e1863d12e150eb4a3e1cf9bb59ff9ab970d10e3097e7189e427`.

The final adversarial pass asks whether a reflected private value remains reconstructable after mixed hex case or Base64 encoding, including an escaped overwritten key. Extend C-FND-005's tests for mixed-case hex, Base64 of the hex string, Base64 of decoded bytes, and duplicate-key mixed-case JSON. Publish and run those assertions before any refinement. Preserve exact untainted public response evidence and existing credential redaction; no broadcast retry or result-contract change.

Encoding red at pushed `c5d8a72`: **4 failing reflection subcases, 5 passed, 11 subtests passed**, 0.06 seconds. Log `/private/tmp/larp-final-c-20261015-encoding-red.log`, SHA-256 `3cbf92f84eaad6499134d35779b1f13596a8c64011b930fd36f249d45fc9f9e2`. Refine private-value screening to retain overwritten pairs, cover mixed hex case and both Base64 representations, and redact before serialization; ordinary public response and credential contracts remain unchanged.

Refinement `1adfed5` focused run: **257 passed, 4 failing reflection subcases, 1 skipped, 223 subtests passed**, 52.70 seconds. Base64 cases pass; case-insensitive raw-body screening fails because `object_pairs_hook=list` retains tuple pairs, which the JSON redactor intentionally does not traverse. Convert each pair to a list in the parser hook, keeping all assertions and representations. Log `/private/tmp/larp-final-c-20261015-focused-final.log`, SHA-256 `6f997d8f500cb485b54dbaa7c5fd36385398701c2fb231dcd9d88720949444de`. The wrapper stopped before its full-suite phase on failure; no full result is claimed for this revision.

## C-MEASURE-001 — prospective read-only evidence (2026-10-15 SGT)

User supplies `.env` as the credential location. Only the committed Web3 credential selector's BINANCE/BN_WEB3 fields and public wallet address may be used. AI_SEEDS_SECRET and wallet key fields are not used or exported. Any temporary API-only copy is mode 0600 outside Git and removed after use.

If Web3 credentials are present, run committed `python -m larp.marketdata.logger` once for all five names, with artifacts outside Git, and its `--balance-only` check for first-gas availability. Criteria: authentication/compliance/rate failures stop without bypass; record UTC time, pushed SHA, exact secret-free command, artifacts and hashes; quotes are unsigned measurements and never fills or profitability evidence. A one-cycle sample cannot satisfy DR01's three days/weekend. No continuous process is started without recording its schedule/lifetime. If credentials or access are unavailable, record the reason without secret values. No audit upload, transaction signing/broadcast or cloud operation.

## C-FND-007 / C-ASM-009 — optional credential fields (prospective)

P2, contained read-only startup defect: user-provided `.env` has literal Web3 key/secret fields but an empty public AI_SEEDS_ADDRESS. The committed credential selector raises `credentials must be literal values` on that optional blank field, preventing API-only selection even when an explicit public quote address would be supplied. No credential value was printed; only names and empty/literal dispositions were inspected. No registered key or audit secret is used.

Assumption C-ASM-009: empty optional fields are equivalent to omission; validate this interface assumption independently, never treat a config default as an organiser rule. Pass criteria: blank, quoted-empty and comment-only public-address/alias fields preserve an existing API pair; a truly missing pair, conflicting nonempty aliases and nonliteral interpolation remain refused. Write and push a fixture-only test, run red, then skip optional empties without relaxing literal/alias checks. Measurements use an API-only private copy and a public address; first-gas evidence remains unavailable until the registered public address is supplied.

Credential-selector red at pushed `8612fc9`: **4 failing blank-field subcases, 2 passed, 3 subtests passed**, 0.05 seconds. Log `/private/tmp/larp-final-c-20261015-credentials-red.log`, SHA-256 `bcbe78e37666c4546c856fc0fc7abc32007d11555e31046537e2a24e4816518f`. Ignore empty optional file entries; missing required pairs and conflicting/nonliteral nonempty entries still fail closed. No change to the user's `.env`.

## C-RESULT-004 — resumed offline repairs and integrated coverage

At pushed `c5cb1455471e2de2d696661b697a40b1bddd7022`:

- Focused C plus merged driver: **259 passed, 1 skipped, 234 subtests**, 54.33 seconds. Skip is the opt-in external recorded-artifact test. Log `/private/tmp/larp-final-c-20261015-focused-complete.log`, SHA-256 `2f417a5886da15338745aee02400d2b753ca9555b0339c150c4c7456e39b6c49`.
- Full Python 3.12.14 / PostgreSQL 14.24 suite: **1246 passed, 7 skipped, 1583 subtests**, 140.61 seconds. This is **+17 tests / +22 subtests** against unchanged C-BASE-002; the same seven Linux/systemd/external-artifact skips. Log `/private/tmp/larp-final-c-20261015-full-complete.log`, SHA-256 `6a19e44f2417d64d564bd451eac075243c7bf5d16090c78cedc97788e036e786`.
- [Linux CI 38604152158](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38604152158) at this exact SHA: all four jobs SUCCESS (runtime, host-bundle and both infrastructure jobs). Exact Linux counts and guarded system-runner results are recorded separately below after log inspection/execution.
- C-FND-005 fixed by `9d59556`, refined by `1adfed5`/`0286a4e`; C-FND-006 fixed by `9d59556` with refusal-order compatibility at `bc8d645`; C-FND-007 fixed by `c5cb145`. Their fail-first published proofs and retests are above. No independent contained P2 remains from these three repairs.
- Integrated PR66 R1/R2/R3 and Y1/Y2 checks now pass in the local real-PostgreSQL suite: Web3 channel, rollover clock, actual Service restart/reauthorization, multi-intent seal and interrupted quote resume. Historical C-OPEN-001 driver exclusion is resolved for offline execution-side coverage; D still accepts the complete final merged tree.

Source/adversarial recheck: reread scoped verbatim page/Guide/API/trading-flow text, exact submitted execution/reproducibility commitments, F/K/Q settled notes and the adopted execution decisions/DR/AT acceptance. No F/K summary correction is needed. Frozen statements and decided values are unchanged. The private-response representation pass found the encoded/duplicate-pair refinement and the real credential-selection check found the optional-field defect; both were added as dated, pushed red proofs before repairs. Following those repairs, the final pass over the modified C boundaries found no additional independent implementation defect. This is **partial review; deployment blocked**, not the protocol §4 whole-section exit gate: the dependencies below remain unfulfilled.

## C-MEASURE-002 — real unsigned quote and balance observations

All calls use committed code at `c5cb145`, with only a Web3 API pair in an isolated subprocess/private API-only file. The temporary credential files were removed. No AI_SEEDS_SECRET, wallet key, real transaction signing/broadcast, upload or AWS call. These are genuine API observations, not canonical chain proof or economic validation.

Command: `/private/tmp/larp-pr20-venv/bin/python -m larp.marketdata.logger --env-file <temporary API-only file> --address 0x1111111111111111111111111111111111111111 --sizes 10,40 --symbols NVDAB,GOOGLB,SKHYB,TSLAB,MSFTB --artifact-root /private/tmp/larp-final-c-20261015-quotes --cycles 1`.

- Time **2026-10-15 01:09:49–01:10:40 SGT** (artifact UTC `2026-10-14T17:09:49.536Z`–`17:10:40.677Z`). The public fixture address was used because the user had not yet populated AI_SEEDS_ADDRESS; quotes do not require funds. It is not represented as the registered wallet.
- One cycle: **10 successful buy/sell quote pairs**, two sizes for each of five names; all ten observed markets open. Read-only pre-approval gas estimates all return `api_or_http_error`; no executable gas allowance is inferred.
- External cycle artifact SHA-256 `d610aa8722fc9aedc702e1449b1d3ec118c7bdd339ff3d95a0faf5f4d0ec3232` under `/private/tmp/larp-final-c-20261015-quotes/`. Individual request artifacts are content-addressed there; `summarize` verifies every filename/hash. Measurement log SHA-256 `df3889806bd56c80cb5d92cbecc5afed0cb9c8131ae16c10bd700ad06c1df293`.

| Name | Pairs | Median sequential effective quoted spread (bp) | Median quoted impact (bp) |
|---|---|---|---|
| NVDAB | 2 | 0.913 | 0 |
| GOOGLB | 2 | -0.441 | 0.00383723 |
| SKHYB | 2 | -0.240 | 0 |
| TSLAB | 2 | -1.964 | 0 |
| MSFTB | 2 | 40.190 | 0.27657756 |

Sequential quote differences include market movement and reflected fees; negative values are not profit/edge evidence. These are two-size snapshot medians, not profile inputs. DR01 still needs at least three days including a weekend, independently hashed retention and B's cost/profile acceptance.

After the user populated the public AI_SEEDS_ADDRESS, command: `/private/tmp/larp-pr20-venv/bin/python -m larp.marketdata.logger --env-file <temporary API-only file with the user-provided public address> --artifact-root /private/tmp/larp-final-c-20261015-balances --balance-only`.

- Time **2026-10-15 01:14:54 SGT** (artifact requested `2026-10-14T17:14:54.738Z`, available `17:14:54.949Z`); successful API envelope.
- API reports **NO_NATIVE_ENTRY**, not canonical proof of zero balance or of first-gas funding. First-gas readiness remains unverified. Never solve it by adding personal BNB.
- Observation SHA-256 `19609b6fa8d8ba6cde7b235a7bdbed55ef13f98f87bdc59c3e54cf02a9bb3737` under the balance artifact directory. Log SHA-256 `491de86f17fc063bd53c489c130a4cd0b68730e6be2b75ab5cf966159c0f3a13`.

## Current blocking requirements, owners and decisions

| Gate | Remaining requirement / classification | Owner, exact validation and deadline |
|---|---|---|
| C-OPEN-003 / #27 | P1; DECISION-NEEDED: proposal freshness, signing lifetime and encoded router expiry | B/C/D before Oct22 cut. Options: measured bounded signing lifetime; or shorter independently qualified router deadline. Recommend measure approval latency/TTL, then explicitly freeze the relationship; preserve strict existing expiry now. |
| C-OPEN-004 / GAP29 / DR02–03 | P1 dependency: attributable chain-56 router/proxy/nested ABI, recorded route mutations and verified quote/decoder evidence | Isaac before Gate B / Oct20 target. Obtain primary implementation/ABI and bytecode hashes, recorded unsigned shapes, and mutation acceptance. Executor fake-only and signer swap refusals stay enforced. |
| C-OPEN-005 / #30 / DR06 | P1 dependency: transaction-bound native receipt/trace proof and first gas | C with B/D before Gate B / Oct20 target. Native proof must exclude unrelated changes and include USDT debit, BNB receipt/gas, reservations and dedicated round settlement. The API balance observation above does not prove a funded first transaction. Team addresses organiser funding if canonical evidence shows no BNB. |
| C-OPEN-006 / DR01 | NOT-OFFLINE: three-day/weekend measured five-name costs | Isaac before Oct22 profile cut; propose collection Oct16–19 spanning Oct17–18 weekend, API-only process, hourly cycles, retained hashes, dated summary passed to B. Schedule is proposed, not an unattended process started here. Record slip if unavailable. |
| C-OPEN-007 / DR03/17 | NOT-OFFLINE: real host access, credentials/clock, RDS grants, nonce/finality and fresh-wallet switch/rehearsal | C/D before Gate B / Oct20 (dev host), final switch reminder by Oct26 and activation Oct27–29. Follow named AWS_RUNBOOK host checks; no AWS or registered-wallet transactions in this review. Signer registered-build/HALT comparisons are now implemented offline; the other host/trust checks remain. |
| C-OPEN-008 / #23 | P0 shared secrecy dependency: legacy/forged raw rows and archive/export/restore acceptance | C owns new-state serialization/release (C-FND-010); D owns export/legacy/forged-row refusal and restore/grants acceptance, before combined Oct20 closure. New C state retains no bytes; D's direct-SQL raw-row test remains expected-red. Preserve old hashes, refuse unsafe exports and verify quarantine/registry-marker refusal. Do not close the whole issue yet. |
| C-OPEN-008 / #36 | P1 shared accounting dependency: canonical balance-to-ledger reconciliation | B with C/D before combined review closure / Oct20. Bind block/finality and BNB mark freshness; startup/periodic unsolicited-adjustment/restore-divergence cases; no fabricated fills. |
| C-OPEN-008 / #28 and final driver acceptance | Shared audit/delivery and final merged-tree coverage | PR67 / D-FND-002 supplies pre-final broadcast audit/deadline repair on merged target 0820b0d. C's integrated full suite includes D's regressions; D still owns acceptance of the complete A/B/C/D final tree before combined Oct20 closure. |

Tracker reconciliation on this base: #40 CLOSED and adapter/profile/merged composition regressions pass; #26 CLOSED and actual Service restart/immutable command reauthorization/claim/replay tests pass; #24 remains OPEN but C acquisition and merged cutoff/day-roll acceptance pass, with D final tree acceptance required. #27 and #30 remain OPEN, as do shared #23/#36. No tracker issue is closed by this task, and closing status alone is not used as evidence. The prior inventory's original trading-review ID collision remains D's shared-document reconciliation item, not hosting IDEA-046.

## Requested shared edits — resumed exact text for D

Replace the earlier C ledger suggestion with:
`| IDEA-049-C | Final review C: execution, signing and wallet boundaries | partial; offline fixes verified, deployment gates remain | 59 source requirements; merged-driver/PG14.24 verification; 43 additional regressions; local 1272 passed / 7 skipped / 1583 subtests; broadcast reflection, signer authority, exact startup manifests and per-asset reserves fixed; unsigned five-name snapshot/balance evidence and finite weekend collection; PR70; remaining owners/checks in record | 2026-10-15 | [ledger/IDEA-049-C.md](ledger/IDEA-049-C.md) |`

Replace the stale C/driver-unmerged paragraphs in INCOMPLETE_WORK with:
`IDEA-049-C / PR70 continues the frozen catalogue on merged base c1b6daf. PR20/21/41/66 integration and offline driver/profile/cutoff/command-restart coverage are verified. C fixes reflected signed bytes in broadcast artifacts, independently checks signer registered build/wallet/HALT before key use and registry release, binds both C entry points to the exact registered manifest before credentials, checks separate pay-token/remaining gas reserves, and accepts blank optional credential fields. Local PG14.24 full suite: 1272 passed / 7 skipped / 1583 subtests; exact-source Linux CI 38615929458 green. No whole GAP is closed: C-OPEN-003..008 retain deadline/decoder/native-proof/first-gas/host-wallet-rehearsal, signer primary-facts trust acceptance and D/B backup/audit/reconciliation checks. DR01 finite 73-hour API-only collection started Oct15 02:35 SGT, targets Oct18 02:35 SGT; owner Isaac verifies actual retained three-day/weekend coverage and passes the dated summary to B before Oct22. D also resolves C-CI-001 actual checkout provenance before Oct20. Unsigned snapshots and NO_NATIVE_ENTRY API balance evidence do not prove live readiness.`

Runbook/README readiness addition:
`Section C's merged offline tests and unsigned API samples do not enable live execution. Before Gate B, verify attributable router/proxy/nested decoding, canonical nonce/finality and transaction-bound native receipts, first-gas funding, accepted lifetimes, real signer host credential/clock/RDS checks, explicit acceptance of the primary-facts trust boundary, and backup/balance/audit acceptance. Verify both C entry points match the registered build and exact manifest before accessing credentials; the signer rejects HALT and changed registration for queued/new requests. Qualify the cumulative intent gas budget against typed remaining BNB reserves. Before profile approval, require all five names' retained cost evidence across at least three days including a weekend; before final activation, rehearse separate fresh-wallet namespaces and confirm its audit secret by Oct26. Use actual checkout provenance, rather than PR API headSha alone, for exact-source Linux evidence.`

D alone applies shared index/backlog/README/runbook edits. Completed portions must be removed from the live backlog once integrated and verified; keep remaining checks with their owners/deadlines. No SKILL F/K summary correction was found, so no shared summary edit is requested. Do not delete whole GAP lines while the host/live/cross-section evidence above remains outstanding.

## C-FND-008 — startup and exact manifest binding (prospective source amendment)

P1, C-REQ-043 and new C-REQ-058: the exact submitted proposal's Reproducibility/Versions says every component checks its hash against the active registered version before running, including the signer at startup. Build-id-only request comparisons do not satisfy startup refusal or a different manifest for the same build. Before claiming the final source pass is closed, add tests requiring refusal before key loading for missing/wrong registration and same-build/wrong manifest; require main to retain its verified manifest bytes and pass the computed hash into the service. Check that hash again at request authorization and under the signature-registry commit's run lock. Quarantine remains exit 3; matching registered release starts; unrelated key-file refusal tests keep all assertions but must seed proper registered-release metadata in their synthetic fixture. No additional signer role privilege is needed (runs is already readable). Publish failing tests before fixes.

## C-CI-001 — distinguish PR merge CI from exact branch evidence

Raw CI log inspection corrects C-RESULT-004's initial shorthand: pull_request run 38604152158 reports head c5cb145 but runtime/infrastructure checked out merge `f316575657eacaf0949603ba20a0e03bbec24ae7` into newer integration base `0820b0dd87219cb6b96f2ede34051129fab9f49c`; host-bundle checked out the head branch. Its Linux merged suite is **1273 passed, 4 skipped, 1 xfailed, 1615 subtests**, with separate systemd **3 passed/5 subtests**. Do not compare those merged counts as a pure C increment or claim exact-branch demo proof. External CI log SHA-256 `8caf389d0c40119f1323a29ad7605f54d4e09b5319296ba0735508b1beb149a4`.

The guarded runner at pushed `1efcda5` executes local system cases correctly (**112 passed, 70 subtests**, 32.937s; system log SHA-256 `79f9045c80be0e61f01bb60df1e01b032bb326cacf6cf5025f0b6f32efc42baa`) but accepts the PR API head as its Linux demo tree. The local system result is valid; its claimed matched-tree demo proof is withheld. Initial report SHA-256 `30fe4149d80c40a03e0b66b9225e2cdbdadf3904564dd13a5288180fc7ca8d5d`.

For D: P1 verification gap, before combined Oct20 closure. `tools/system_test.py` must inspect the actual CI checkout (PR merge vs branch) or require workflow_dispatch evidence when using API headSha. Proof is the committed run/checkout mismatch above, not an invented failure count. C cannot edit D's runner. C dispatched exact-branch run 38606430103 at 1efcda5; after the final source fix, dispatch and use a new exact-runtime run and repeat the guarded runner. No test is weakened to accept a different tree.

C-FND-008 red at pushed `6240f85`: **5 failed, 11 passed**, 4.17 seconds (three startup refusals, queued same-build manifest mismatch, late registry manifest change). Log `/private/tmp/larp-final-c-20261015-manifest-red.log`, SHA-256 `dfe600fa2610c61818bff435572f7a9d2b2192f0ab24fa532819f56096dfcbbc`. Fix retains the already verified manifest document, rejects mismatched registration before loading a key, passes its hash into signer authorization and registry release. Existing CLI/key-file fixtures seed valid synthetic registered genesis metadata; every prior assertion stays intact and separate negative tests prove registration is required. No applied schema/grant/other-section file changes.

### C-FND-008 execution-side extension — prospective

The same declared startup obligation covers C's execution entry point and its RunAuthorization. Add C-REQ-059 before tests: wrong/missing registered build or manifest must refuse before Web3 credential access/composition, even while the Executor capability gate is still closed. A matching registered release must still reach exit 2 EXECUTOR_CAPABILITY_GATE; check-only remains offline config validation. RunAuthorization must compare immutable intent version and its own verified manifest, and fail closed without a manifest for production runs. Preserve offline synthetic harnesses, quarantine exit 3 and every existing assertion; seed matching synthetic registration in CLI fixtures rather than bypass checks. Publish real-PostgreSQL startup/authorization tests before fixing.

### C-RETEST-006 — signer exact-manifest repair

At pushed `910afd9`: focused C/driver **265 passed, 1 skipped, 234 subtests**, 52.35s; full suite **1252 passed, 7 skipped, 1583 subtests**, 135.24s (+23 tests/+22 subtests against C-BASE-002). Logs `/private/tmp/larp-final-c-20261015-focused-release.log` SHA-256 `eca384b49168212e5e83fad6cc72946061743b2689651b6a16254a015e3f5dd9`; `/private/tmp/larp-final-c-20261015-full-release.log` SHA-256 `dc700b485b3f449c7936c475df7e74da1faa3c84047f483308b176419df51a42`. Exact-branch CI 38607877362 dispatched at this SHA; execution-side extension still requires its own final verification.

Execution extension red at pushed `d7491ae`: **6 failed, 2 passed**, 1.23s (startup missing/build/hash; authorization missing manifest/stale intent/hash). Log `/private/tmp/larp-final-c-20261015-execution-manifest-red.log`, SHA-256 `d7a218a980edf1270d30acbc92de3a8483495c3313a73eee534fa26abcefc9ee`. Fix retains the execution entry point's verified manifest, refuses before credentials/composition, and binds its hash and immutable intent version into RunAuthorization. Existing CLI fixtures seed matching synthetic registration; assertions and capability refusal remain unchanged.

## C-FND-009 — independent resource reservations (prospective)

P1, C-REQ-017/018/028: RunAuthorization currently sums heterogeneous reservation units and accepts any positive total. A planned intent with pay-token funds but no BNB, BNB alone, an unrelated asset, or insufficient amounts can therefore report reservation_valid. The original trace overstates coverage: intent-local caps and planner tests do not prove this execution-side boundary. No live execution is enabled, so this remains contained behind the existing capability/decoder gates.

Pass criteria, before new tests: use real PostgreSQL and journaled per-asset reservations. Both the exact pay-token amount and remaining cumulative gas budget must be covered separately for this intent; another intent's or an incoming asset's reserve cannot substitute. Convert only with the existing explicit chain/accounting scales (USDT 18/6, bStock same validated token units, BNB using durable portfolio.bnb_decimals). Missing or invalid BNB scale fails closed in production. Preserve historical untyped offline fixtures' unit convention only in offline mode, with separate positive pay and BNB reservations. Cover zero/missing BNB, missing pay token, insufficient pay/gas, wrong asset/intent, non-18 BNB accounting scale, unknown production scale, and already verified cumulative gas expenditure so approval settlement does not incorrectly block a covered remaining budget. Publish tests and run red before the C-only fix. No decided thresholds, B accounting code, D grants/schema or capability gate changes.

The signer independently verifies payload/run/build/wallet/HALT, but primary-supplied resource/risk/market/nonce facts remain the adopted two-host trust boundary. Independent cross-host risk/reservation attestation needs B/C/D acceptance under C-OPEN-007 before activation; this resource fix does not claim to close that architectural gate.

Published red at `d9f5fb4`: **8 failed, 4 passed**, 1.69s, log SHA-256 `b2087d886fbe46b77556af431ebc4813b327b96ada3c5e8bed7e2e141a3e06af`. The approval payload fixture used positional fields incorrectly; changed to explicit keyword fields without changing any assertion, published as `010346c`, and reran: **8 failed, 4 passed**, 1.78s, `/private/tmp/larp-final-c-20261015-resources-red-corrected.log`, SHA-256 `c3162ae8680ea86e7bee04ff0f3378b78ae9aa0b5d5eb63a9ffb80b09caac0e1`. Thus the negative reserve cases independently reproduce before the fix. The repair checks pay and BNB separately, preserves only the explicit untyped offline fixture convention, and verifies execution journal state before crediting finalized gas expenditure. Typed production scales cannot be guessed.

Execution-manifest repair `d70e00e` verified before the resource amendment: focused **273 passed, 1 skipped, 234 subtests**, 55.27s; full **1260 passed, 7 skipped, 1583 subtests**, 136.95s (+31 tests/+22 subtests against baseline). Logs `*-focused-execution-release.log` and `*-full-execution-release.log` under `/private/tmp/larp-final-c-20261015-`. An initial sandboxed attempt could not reach the loopback database (Operation not permitted); it is an environmental refusal, not an application result. The successful run used the same sanitized environment with loopback access.

## C-MEASURE-003 — prospective finite weekend collection

DR01 cannot be satisfied by the two-size snapshot. Start the already committed logger from this pushed branch for **73 hourly cycles**, all five names, sizes 10/40 USDT-equivalent, from Oct15 SGT to approximately Oct18 SGT (72 hours, including the Oct17–18 weekend). The process makes only unsigned read/build API calls, retains content-addressed artifacts outside Git at `/private/tmp/larp-final-c-20261015-weekend`, and writes an external summary at completion. Use a mode-0600 API-only file in a private external directory, containing only the Web3 key/secret and public address, never wallet keys or AI_SEEDS_SECRET; a detached supervisor deletes this copy on normal completion/failure. Record start/end target, PID, pushed revision and first cycle hash after launch. No cloud, audit upload, transaction signing or broadcast.

Acceptance remains pending: verify hashes, actual sample times spanning at least 72 hours and a weekend, all five names and market-state/failure coverage, then publish a dated cost/impact summary for B. The logger stops on its existing authentication/compliance/rate refusal; never bypass it or fabricate missing cycles. Sleep, reboot or process failure may interrupt collection, requiring a recorded schedule slip. Do not call DR01 PASS merely because collection was started; only retain/delete the task's own files/process. No power-management change is made.

### C-MEASURE-003 launch evidence

Started at pushed `44ff2ef970d148b53edd76d20a47dae9f757218b`, **2026-10-15 02:35:47 SGT** (`2026-10-14T18:35:47.004905Z`); target last cycle **2026-10-18 02:35:47 SGT**. Supervisor PID **58913**, alive after first cycle, no traceback. Command: `/private/tmp/larp-pr20-venv/bin/python -m larp.marketdata.logger --env-file <private API-only copy> --artifact-root /private/tmp/larp-final-c-20261015-weekend --sizes 10,40 --symbols NVDAB,GOOGLB,SKHYB,TSLAB,MSFTB --cycles 73 --interval-seconds 3600`. First cycle finished `2026-10-14T18:36:38.886Z`, SHA-256 **`b95c8c800dbca2b2485bcb7ca4420f9e4696482bd284a1d0c4597ed7b28e95d3`**; all underlying request artifacts are retained by hash alongside it. The user's registered public address is used; it is not a credential.

Launch metadata, log, final summary and completion status are siblings `*-weekend-launch.json`, `*-weekend-process.log`, `*-weekend-summary.json`, `*-weekend-completion.json` outside the content-addressed artifact directory. The latter two are written only after exit. The private API copy is removed by the supervisor on normal exit/failure or handled SIGTERM/SIGINT. Isaac owns verifying completion/cleanup and actual times/hashes; if the machine reboots or the supervisor is forcibly killed, use the launch metadata to remove only that API copy. Neither its values nor path is committed. Collection is **IN PROGRESS**, DR01 acceptance **NOT RUN**. This supersedes the earlier proposed Oct16–19 schedule.

## C-RESULT-005 — final C application tree

Application/test tree **`a4e133468801760dc1681709a8be41a99898de46`**, subsequent edits docs only:

- Focused C plus real merged driver: **285 passed, 1 skipped, 234 subtests**, 57.95s; `/private/tmp/larp-final-c-20261015-focused-final.log`, SHA-256 `8cb260d851fba0b0af0f04b26bfd9117de0f61cf65a9b30f0086c8c7b699e38a`.
- Full Python 3.12.14 / PostgreSQL 14.24: **1272 passed, 7 skipped, 1583 subtests**, 140.65s. Against C-BASE-002: **+43 tests / +22 subtests**, unchanged seven environment/external-artifact skips. `/private/tmp/larp-final-c-20261015-full-final.log`, SHA-256 `04a60374a38fd3e190e298d4704d5764eb1b57cc183e002dbc73e1b8f3f91e2a`.
- Exact-branch **workflow_dispatch**, [CI 38615929458](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38615929458): all four jobs SUCCESS. Actual runtime checkout log `git log -1 --format=%H` confirms **a4e133468801760dc1681709a8be41a99898de46**, rather than a PR merge. Linux Python 3.12.15 full suite **1275 passed, 4 skipped, 1583 subtests**, 240.23s; real systemd **3 passed / 5 subtests**, 8.27s. Mock Terraform **15+1 passed**, pip check/demo/Docker smoke/AL2023 host-bundle checks pass. External complete CI log SHA-256 `b89686301283eadce12d03c7b0154fef69a796066c70faeb5d2ce856f9266c81`.
- C-FND-008 repaired by `910afd9` (signer) and `d70e00e` (execution); C-FND-009 repaired by `a4e1334`. C-FND-005..009 are fixed and retested; no new independent contained P2 remains. Baseline/red/green provenance is retained above. Earlier d70 logs: focused SHA-256 `40b13a2928825b1f0c4a9e8bd193c4d8958f274eb480d6245ccec4edc5744bb7`, full `36debb5ba32d3ce522ff4d026488a36d62811d33c231ffe774e2b91567fe3261`.

Final source/adversarial pass after C-FND-009 rechecks the verbatim official page, Guide C pages/checklist/channel, Web3 and trading-flow documents, submitted execution/reproducibility/recovery sentences, settled F/K/Q notes, adopted host/execution decisions and scoped DR/AT acceptance. No further independent implementation defect or F/K summary correction was found in C's modified boundaries. Full section exit is **NOT MET; partial review, deployment blocked** by the current C-OPEN table, shared P0 backup secrecy, cross-host trust decision and C-CI-001. Per-asset reserves do not prove canonical wallet balances, nonce/finality or funding. The fake-only Executor, unverified decoder and native-receipt refusal stay enforced. No registered key, AI_SEEDS_SECRET, audit call, real signing/broadcast, cloud operation, merge or deployment occurred.

Guarded system runner is executed next on the clean pushed docs revision with this exact-source dispatch evidence; its result is recorded separately. D alone applies the exact shared-doc edits above and accepts the final merged integration tree. C's changed code/tests stay in the exclusive paths; no existing assertion was removed, weakened or skipped to pass.

## C-RESULT-006 — guarded system acceptance and handoff

At clean pushed **`1f08521650411b2066bde1e1089a09150ef2b6da`**: `/private/tmp/larp-pr20-venv/bin/python tools/system_test.py --system-only --linux-ci-run 38615929458 --output-dir /private/tmp/larp-final-c-20261015-system-final`, sanitized environment, disposable loopback PostgreSQL, `LARP_SYSTEM_TEST_DISPOSABLE=1`. **PASS: 112 system tests / 70 subtests**, 32.15s. Linux demo evidence is the separately inspected actual a4e1334 workflow_dispatch checkout; runtime/config/deploy/migration trees are identical. This supersedes the earlier withheld PR-merge demo provenance. Report SHA-256 `6c32384eeee4f5cd1d0d3e706d11616a21eebe1d311996124c5eb953dbaec0b5`; system log `5c220c1b4fd77eea3f10aad5eae92974cbfa967ebe9e0eef1f71b77b464d327b`; command log `950e42b7716bd34b684292d03c7553d9c37279c0fc3c6fa118fa78e7786edcc0`. All raw artifacts remain outside Git.

Final fetch confirms target advanced independently from tested base c1b6daf to **0820b0dd87219cb6b96f2ede34051129fab9f49c**. PR70 supplies merge compatibility checks against it; C's pure-branch baseline/CI counts above remain separate, and D owns acceptance of the combined final tree. User main and origin/main both **5e945e148314b395a09ffe3e8a1461467b617114**. Original checkout is returned to latest detached origin/codex/system-testing-20261012; all C changes are isolated in `/private/tmp/larp-final-c-20261015`, published on `review/final-c-20261015` / draft PR70. No main history or user .env is changed.

Offline work can hand off after the final documentation push and clean-status check. Remaining work is explicitly flagged: Isaac verifies the in-progress finite collector and its cleanup, decoder evidence and first-gas/nonce/native proof; B/C/D resolve deadline and signer primary-facts trust acceptance; D handles shared backup P0, audit/final integration, actual CI-tree verification and requested shared docs; B with C/D handles canonical balance reconciliation. Exact acceptance and Oct20/22/26/27–29 deadlines are in the current gates table. The disposable task PostgreSQL container is removed after verification; the read-only collector is intentionally retained until its finite exit. No section/live-ready declaration is made.

## C-FND-010 — signed state / #23 ownership correction (prospective)

Final fetch/read of merged [PR67](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/67), author-linked IDEA-049-D §7: D explicitly requests **C** to keep raw bytes only in execution_signatures and broadcast by registry lookup. The earlier assignment of the entire #23 repair to D was incorrect. C owns state serialization and release; D owns archive/export/legacy restore acceptance. P0 under this protocol because archived unsubmitted bytes are reusable transaction capability; C-REQ-012/036/037. Ordinary merge brings target 0820b0d into this branch, with no history rewriting or D implementation edits. Record pure-C results separately from the new integrated tree.

Pass criteria, before tests: sign using real Executor/ExecutionStore/registry with synthetic non-EVM bytes on PostgreSQL; signed bytes exist only in the restricted registry, not execution_records.state/journal or a logical backup of legitimately produced state. Restart retrieves identical bytes from that registry for the original fenced first broadcast, never signs again or blindly resends a possible send. Missing/corrupt/mismatched registry bytes refuse before possible-send recording/network I/O; changing raw bytes while reusing a hash cannot pass FencedRelease authority. Existing SQLite offline assertions retain their fixture-only representation; production state strips bytes before hashing/commit. Hash-compatible backup/restore stays quarantined and cannot invent missing signature authority. Publish requirement tests before the fix and run red.

D's current expected-failure test directly SQL-inserts legacy raw bytes with an invalid state hash, bypassing C's serialization. Removing its marker cannot establish this fix: the legacy export remains red independently. Do not weaken/delete it or edit D's test. Ask D to add a legitimate C-state positive backup case and separately refuse/quarantine legacy signed state before archive/export, preserving old hash-chain evidence; obtain owner approval before any D change. #23 whole-issue closure remains blocked by that legacy/export acceptance even after new C state is repaired. Existing archive grants/applied migrations are untouched.

Red proofs: `8402d99` **6 failed/1 passed**, SHA-256 `8abd3d3b867023c0d44d47782e6e5df9f572e302b467b5a0a3a64553a81d6499`. Two fixture assumptions were incorrect: backups retain registry metadata with redacted bytes (restore rejects its digest), and release authority exists during BROADCAST_ATTEMPTED, not after a fake send has moved to PENDING. Corrected fixtures published before application repair as `6aa68b8` (**5 failed/2 passed**, SHA-256 `aa1a7001939693be96ca81b20836844475f83abe207e70126c1993e1d087cb6f`) and `cfb684a` (**4 failed/3 passed**, 2.01s, `/private/tmp/larp-final-c-20261015-signed-state-red-boundary.log`, SHA-256 `998f1dc447d8d4311efe1f7762884f5fbd346b3025c0dddf1110de5f16802bc3`). No required refusal or secrecy assertion is dropped; registry-check timing is now exercised by the actual external fake venue.

Repair: PostgreSQL strips raw_hex from every attempt before state hashing/commit; the general offline SQLite fixture representation stays compatible. Executor looks up and verifies original registry bytes before recording possible submission; FencedRelease checks them against the restricted registry in its existing transaction. Missing/corrupt/restored marker evidence refuses with no network call. Historical state hashes are not rewritten; legacy raw state needs D's explicit export/restore handling. The finite collector remains on its original loaded logger/web3 code at 44ff2ef; these execution/D changes do not alter that read-only process.

At `47fe98e`, focused **291 passed / 1 failed / 1 skipped / 234 subtests**, 60.03s, SHA-256 `9937fece268590012a9be4d9e12cca76cc61779763eefeafb584e5664fe37259`. All seven new security/restart/restore cases pass. One original signer test asserted that archive-readable execution state retained raw bytes, the exact defect being fixed. Preserve its exact byte/hash equality, crypto verification and all duplicate/restart assertions, but obtain the byte side from the real RemoteSigner port (the restricted registry), and add an assertion that the returned execution state has raw_hex=None. This changes the byte source to the intended private boundary, not the expected bytes or at-most-once requirement; no assertion/test is removed, skipped or weakened. D's legacy export test remains untouched and expected-red.

## C-RESULT-007 — integrated signed-state repair / tomorrow handoff

Final application/test tree **`1d4d948a6e35e76aff49ff4bbb0205b2109d77af`** (application repair `47fe98e`), including ordinary merge of D's target **0820b0d**. No D file is edited by C; diff against the current target has only the 18 allowed C files. Results:

- Focused C/driver: **292 passed, 1 skipped, 234 subtests**, 61.55s. Log `/private/tmp/larp-final-c-20261015-focused-integrated-release.log`, SHA-256 `2fafea2183b7aee32ab5f325ba247262e48d78b095b0711d72a511da616c6b09`.
- Full Python 3.12.14 / PostgreSQL 14.24: **1303 passed, 7 skipped, 1 xfailed, 1615 subtests**, 153.49s. Log `/private/tmp/larp-final-c-20261015-full-integrated-release.log`, SHA-256 `353ea3abaac50ea95541234769f24ec4d48943c981578ebb451443c9de10ddca`. Against C-BASE-002, +74 passing tests/+54 subtests: **50 C regressions/+22 C subtests**, **24 D tests/+32 D subtests** from the merge, plus D's retained #23 expected failure. Seven environmental skips unchanged. Suite exit 0 does not mean #23 passed.
- Exact-source [workflow_dispatch CI 38619337154](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38619337154) and a renewed guarded system run supply the final Linux/system evidence below. Earlier C-RESULT-005/006 remain valid for their pre-signed-state tree, not this final repair.

C-FND-010 new-state/release repair passes; legacy/forged raw-row export acceptance is **still missing with D**, explicitly P0 under the common protocol. Preserve D's expected-failure assertion; neither removing its marker nor presenting a fresh-state positive as legacy proof is allowed. #28's D-FND-002 repair is now merged and exercised by the integrated suite. The source/secret/restart/release pass finds no further independent C defect in the modified boundaries; all previously named decoder/native/first-gas/host/trust/deadline/measurement/shared gates remain. Section review **partial; deployment blocked**.

Requested shared text above is superseded for counts/ownership by this exact final backlog wording:
`IDEA-049-C / PR70: 59 source requirements, 50 C regressions; C fixes broadcast reflection, authoritative signer build/wallet/HALT, both exact-manifest startup gates, per-asset remaining pay/gas reserves, optional empty credentials, and private-registry-only signed state with fenced restart release. Integrated local suite: 1303 passed / 7 skipped / 1 expected failure / 1615 subtests. #23 remains P0 for D's legacy/forged-row archive/export refusal and restore/grant acceptance; new legitimate C state is byte-free and restores quarantined without usable signature authority. #28 repaired by merged D PR67. Keep C-OPEN-003..008 and C-CI-001 with their named owners/checks/deadlines; finite API-only DR01 collection remains in progress until Oct18 02:35 SGT, with actual coverage/summary acceptance pending. No whole GAP or live readiness is established.`

Final LEDGER replacement row:
`| IDEA-049-C | Final review C: execution, signing and wallet boundaries | partial; offline fixes verified, shared/live gates remain | 59 source requirements; 50 C regressions; integrated PG14.24 suite 1303 passed / 7 skipped / 1 expected failure / 1615 subtests; exact CI/system evidence in record; private signed state repaired; legacy export P0 retained; finite weekend collection; PR70 | 2026-10-15 | [ledger/IDEA-049-C.md](ledger/IDEA-049-C.md) |`

Tomorrow's starting points: PR70 and this record; verify collector PID58913 and new cycle hashes, continue attributable decoder/native/nonce/first-gas evidence within separately authorized scope, and have D resolve legacy/forged raw-row exports, actual CI-checkout validation and apply shared docs. B/C/D still decide lifetimes and signer primary-facts trust; B owns canonical balances, D owns full final-tree/host acceptance. Do not load wallet keys or AI_SEEDS_SECRET, call ai-seeds, operate AWS or enable capability gates under this review. Every action/finding above is kept outside the conversation.

### Final Linux/system acceptance and clean close

[Exact-source CI 38619337154](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38619337154) **all four jobs SUCCESS**. Actual runtime checkout is `1d4d948a6e35e76aff49ff4bbb0205b2109d77af`; Linux **1306 passed / 4 skipped / 1 xfailed / 1615 subtests**, 244.42s; real systemd **3 passed / 5 subtests**, 7.80s; mocked Terraform **15+1**; host bundle, demo, Docker smoke and credential scan pass. Complete external CI log SHA-256 `c30ca1768c46d2a5aee56a64c739419fddc3ea72ee2f389a09774a28b9104ee2`.

Guarded command at clean pushed **14f9b19c2bc8df93133b6da7f37d25b245881014**: `/private/tmp/larp-pr20-venv/bin/python tools/system_test.py --system-only --linux-ci-run 38619337154 --output-dir /private/tmp/larp-final-c-20261015-system-integrated`. **112 passed / 70 subtests**, 31.433s; successful Linux demo from the independently inspected actual checkout, identical final runtime and test trees. Report SHA-256 `53cb0a42247e141b4ebcc3f8017081572a833b51f2c7721901181237b9375cb6`; system log `e3ad443947576609a9f002bd34dadcadacee3ad34be92360a7aba1e886371c10`; command log `9a59d9c2bbbb62e83179faf28ed601c2e310c1d8dbd160171d7d61078b0f95d9`. Later changes are documentation only; source/test/config/deploy/tool trees match the verified revision. Final docs pushes may trigger fresh CI, which is not substituted for the verified exact-source result.

User requested a clean close for tomorrow. All changes/results are committed and pushed on PR70's branch; original checkout stays clean at origin/codex/system-testing-20261012=0820b0d, main=origin/main=5e945e1. No unpushed commits, repo-local temporary files, unflagged new placeholders, secret/.env commits or history rewrites. Only the task's disposable PostgreSQL container was removed after final tests. API-only collector PID58913 remains intentionally running, targets Oct18 02:35 SGT, with first-cycle hash and cleanup metadata in C-MEASURE-003. Its live backlog/owners/deadlines and every incomplete requirement are explicit above. PR70 remains draft/unmerged; section review remains partial and deployment blocked. This record supports a new session without relying on chat history.

## C-FND-011 — PR70 encoded-reflection follow-up (prospective, 2026-10-15)

Source: [review comment 4280232976](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/70#discussion_r4280232976), C-REQ-012. At reviewed head `9a14d6e4fc30387feb82be7923d479f71deb1f46`, synthetic success and rejection responses can retain signed bytes as URL-safe Base64, unpadded Base64, or Base64 of prefixless hex in both parsed diagnostics and reversible raw-response evidence. The review independently ran the unchanged full suite: 1303 passed, 7 skipped, 1 expected failure, 1615 subtests; those passes do not cover these encodings.

Pass criteria recorded before implementation/testing:

1. Screen standard and URL-safe Base64 with or without padding by decoding response string tokens before checking for private request bytes. Cover raw binary transaction bytes and ASCII hex with a prefix, without a prefix, and with mixed/upper hex case.
2. Redact equivalent encodings in response values, dictionary keys, nested values and error messages. An escaped overwritten duplicate JSON key/value must prevent retention of the raw response, even when the final parsed value is public.
3. Exercise success and API rejection paths through the real Web3Broadcaster/Web3Client with a fake HTTP opener and arbitrary unbroadcastable fixture bytes. Retain response hashes, request-parameter hashes, one-call/no-retry behavior and exact untainted public response evidence, including unrelated Base64.
4. Run the focused broadcast/market-data tests, then the offline execution/signer suite with disposable PostgreSQL. Keep the existing legacy/forged-row archive/export expected failure and all live capability gates. No registered credentials, live signing/broadcast or AWS use.

Owner: Codex implementing Keith's request on isolated `review/final-c-20261015`. Status: implementation and three regression methods prepared (28 encodings across success/rejection and escaped top-level/nested duplicate values, plus unrelated public Base64); new code/tests NOT RUN. The response scan normalizes Base64 tokens to bytes, compares binary transactions exactly and hex text without case sensitivity, and uses the same screening for parsed redaction and duplicate-preserving raw-body omission. Syntax-only AST parsing and `git diff --check` pass. AGENTS.md requires logging changes committed and pushed before execution; push approval is pending. No whole GAP is completed by this repair.

## C-RESULT-008 — normalized Base64 repair and CI blocker (2026-10-15)

Keith authorized the push and a merge if verification is satisfactory. Ordinary push publishes regression/criteria commit `58a5f78` and application commit `7d4d8438129df9c521ddb098ff2f2931984961ae` on PR70, without rewriting history. The preceding C-FND-011 preparation status is historical; the new code is now pushed and its focused tests have run.

- At pushed tests-only `58a5f78`, the broadcast file fails in **92 subtest cases** against the original application (pytest also reports 8 passed / 35 passing subtests). The new cases reproduce the reported leak; unrelated public Base64 remains accepted.
- At pushed fixed `7d4d843`, `env -i PATH=/usr/bin:/bin:/usr/local/bin /private/tmp/larp-final-a-test-env/bin/python -m pytest -q tests/execution/test_section_c_broadcast.py tests/marketdata`: **57 passed, 1 skipped, 189 subtests passed**, 0.48s. The three new methods exercise 112 encoding/path subtests and one untainted public-evidence case. These are synthetic fixture observations, not live signed transactions.
- Complete offline Python 3.12.14 / disposable PostgreSQL 14.24 suite at pushed `7d4d843`: **1306 passed, 7 skipped, 1 xfailed, 1727 subtests passed**, 340.64s. Command: `env -i PATH=/usr/bin:/bin:/usr/local/bin LARP_TEST_DATABASE_URL=<disposable-loopback-DSN> /private/tmp/larp-final-a-test-env/bin/python -m pytest -q`. Compared with the independently reviewed `9a14d6e` baseline, +3 passing tests and +112 subtests; the same seven environmental skips and legacy export expected failure remain. Production credentials were absent. Only this task's disposable PostgreSQL container is removed after verification; no user service or collector is touched.
- [Push CI 38700961269](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38700961269) and [PR CI 38700968781](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38700968781) failed before executing any steps. Runtime and host-bundle annotations say: "The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings". No application-test failure was reported by these unstarted jobs. Billing was not modified, and the checks were not bypassed.

Merge remains pending CI acceptance. Account billing/spending-limit remediation belongs to a repository/account administrator; Codex owns rerunning verification on the then-current PR head and completing the authorized ordinary merge into `codex/system-testing-20261012` once checks are satisfactory. The separate legacy/forged-row archive/export expected failure, production decoder/native/host/rehearsal gates and prior open owners remain. No whole GAP is closed and no production capability is enabled.

The result-record follow-up changes documentation only; application and test trees remain identical to verified `7d4d843`. PR70 remains draft/unmerged, with no approval or check bypass. C-FND-011's application repair is locally verified; its checklist item is narrowed to the remaining CI/merge work.

## C-VERIFY-009 — current target integration and literal compatibility amendment (2026-10-15)

The integration target advanced through PR65/PR68 to `ba4ff9068ff70abe9e920d3c3aa5677949845a14`. Ordinary merge `5c42d590c1d3cb4b3f3b856e0230e9793828b970` brings it into PR70 without conflicts or rewriting. This supersedes C-RESULT-008's application/test-tree identity for the current head. Full local Python 3.12.14 / PostgreSQL 14.24 verification at pushed `5c42d59`: **1374 passed, 7 skipped, 1 xfailed, 1740 subtests passed**, 395.40s. [CI 38701933234](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38701933234) still executes zero steps because of the same billing/spending-limit refusal.

An additional synthetic check after that run exposes a compatibility regression in the new normalization: `msg='signed_' + Base64(raw_transaction_bytes)` is treated as a single token whose prefix changes decoded alignment. Removing the earlier exact-encoding list therefore loses its existing embedded-substring protection. This was independently reproduced on `5c42d59` with fake HTTP and arbitrary unbroadcastable bytes; both parsed `msg` and raw-body evidence retain the encoded value. Do not treat the preceding green suite as final acceptance of this case.

Prospective amendment before repair/testing: preserve the original exact standard-Base64 representations alongside normalization, and add a regression for a directly attached `signed_` prefix. Cover Base64 of full hex text and decoded binary bytes on success and API rejection, with no reflected bytes or reversible raw body, one HTTP call, and unchanged public hash/evidence checks. Re-run the focused broadcast/market-data suite, then the complete combined offline suite from the committed/pushed fixed head. This is the same C-FND-011 secrecy repair, not a new trading policy or capability. CI acceptance and the conditional merge remain pending the administrator's billing fix.

## C-RESULT-010 — final combined-tree repair verification (2026-10-15)

Final tested application/test revision: **`d868e6401c70ef1ce1999c0a5869d005031bb5dd`**, pushed before execution. It includes the ordinary merge of current target **`ba4ff9068ff70abe9e920d3c3aa5677949845a14`** (PR65/PR68) and restores literal encoded-substring protection alongside normalized screening. The target remained at that hash at final verification. New security coverage comprises four methods, 116 encoding/path subtests and an unrelated public-Base64 positive case.

- Focused broadcast and complete market-data suite: **58 passed, 1 skipped, 193 subtests passed**, 1.01s. Command as C-RESULT-008, using the final pushed revision.
- Complete combined offline Python 3.12.14 / PostgreSQL 14.24 suite: **1375 passed, 7 skipped, 1 xfailed, 1744 subtests passed**, 392.30s. Same credential-free environment and disposable loopback database command as C-RESULT-008. The retained expected failure is the separate legacy/forged-row archive/export case, not a pass. This supersedes C-RESULT-008 / C-VERIFY-009 for current application/test acceptance.
- [Final-code PR CI 38702802805](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38702802805) and [push CI 38702795300](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38702795300) still do not execute any job steps because of GitHub's account payment/spending-limit restriction. No green CI result is claimed for the new code.

Only the result/index/backlog documentation changes after this verified revision. All prepared changes are committed/pushed to PR70's branch, the user's main checkout stays clean, and only this task's disposable PostgreSQL is removed. **Not merged:** Keith's conditional merge remains pending current-head CI acceptance after an account/repository administrator resolves billing; Codex owns refreshing head/target, rerunning checks and the ordinary merge into `codex/system-testing-20261012`. No check bypass, approval, deployment, real wallet credential, live signing/broadcast or AWS action occurred. Existing production/shared gates remain with their prior owners. The active checklist records the CI/merge work explicitly.

## C-LOCAL-CI-011 — prospective local reproduction of Runtime acceptance (2026-10-15)

Keith asks to run GitHub CI locally after the hosted billing refusal. Reference: `.github/workflows/runtime.yml` at PR70. Pass criteria recorded before the new runs:

1. Use the current clean pushed PR head, record its exact SHA, and keep generated images, databases, bundles and logs outside the repository. No registered credentials or AWS apply; the Terraform tests explicitly use mock providers and plan commands.
2. Infrastructure: checksum-verify Terraform 1.13.5 Linux amd64 as the workflow does; run fmt, backend-disabled/lockfile-readonly init, validate and test for both `deploy/aws` and `deploy/bootstrap`. Preserve pins and locks.
3. Runtime: Linux x86_64, Python 3.12.15, the exact test lock, pip check, PostgreSQL 14.24, pytest with plugin autoload disabled, actual bubblewrap isolation and the offline demo. Prefer the workflow's Ubuntu 22.04 environment; report any distribution/kernel/container differences explicitly. The existing expected-failure legacy export test remains an expected failure, never a pass.
4. Run the separate real-systemd tests in a disposable Linux systemd instance with synthetic fixture units. Any required container privilege is limited to this instance, with no Docker socket, host services, registered credentials or live resources exposed. If kernel/container support prevents the check, record the precise failure rather than substituting unit-file inspection.
5. Build the workflow's runtime Dockerfile and run its network-disabled, read-only, capability-dropped smoke command. Build the x86_64 release bundle from the exact pushed commit; verify its hashes and run the existing AL2023 offline primary/signer provisioning script. Keep raw artifacts and hashes for review. No hosted GitHub artifact upload or green hosted check is implied by a local reproduction.

Status: preregistered; execution not yet started. Codex owns local reproduction and evidence; an account administrator still owns the GitHub billing restriction. Any remaining platform gap stays explicit before applying Keith's previously authorized conditional merge.

## C-LOCAL-CI-012 — local workflow reproduction results (2026-10-15)

Exact tested PR source: **`65e768c04f6ce6e7996e8da2c41147a5a4a024ba`**, clean/pushed, containing target `ba4ff90`. Runtime/test/deploy/tool trees match the preceding repaired source; the new source commit only preregistered these checks. All local jobs use the existing workflow/scripts and dependency locks without weakening application guards. Ubuntu **22.04.5**, Python **3.12.15** from the repository's checksum-pinned python-build-standalone 20261001, PostgreSQL **14.24**, and plugin autoload disabled. Runners are disposable Linux containers on an Apple ARM64 Docker Desktop host (LinuxKit 7.0.14), not GitHub's native x86_64 VM. No production credentials, live wallet or AWS apply.

| Workflow step | Local result |
|---|---|
| Infrastructure, Linux amd64 | Terraform 1.13.5 ZIP checksum matches the workflow; fmt, backend-disabled/lockfile-readonly init, validate pass for both roots; mocked tests **15+1 passed** |
| Runtime Docker, amd64 | Exact `deploy/Dockerfile` builds; network-none/read-only/all-capabilities-dropped smoke passes |
| Host bundle, x86_64 | Exact-source bundle builds; unchanged AL2023 script passes offline primary and signer provisioning/idempotency, hashes, refusal, credential permissions and packaged preflight |
| Real systemd, amd64 | **3 passed / 5 subtests**, 11.35s; actual disposable units, not unit-file inspection |
| Full runtime, amd64 under Rosetta | **1376 passed / 2 failed / 4 skipped / 1 xfailed / 1744 passing subtests**, 204.48s; the two failures are `Sandbox.test_no_home_network_or_inherited_credentials` and `Sandbox.test_valid_assessment` |
| amd64 offline demo | Fails after the guarded worker fails; direct subprocess observation captures exit 133 and `rosetta error: mmap_anonymous_rw mmap failed, size=1000` |
| Native Linux ARM64 worker/demo | All **5 worker tests pass**, including network/home/credential denial and valid assessment; unchanged offline PostgreSQL/bubblewrap demo passes with simulated=true and verified journal |
| Native Linux ARM64 full runtime | **1378 passed / 4 skipped / 1 xfailed / 1744 subtests passed**, 140.20s, with the same limits and dependency pins |
| Native Linux ARM64 real systemd | **3 passed / 5 subtests**, 3.29s |

The native result supports the diagnosis that the positive sandbox failures arise under Rosetta's memory mapping when the worker enforces its existing resource limits. It does **not** establish a passing native x86_64 full run here. Memory/CPU/process limits, sandbox mounts, credential clearing, network denial and tests are unchanged. The separate legacy/forged-row archive/export case remains expected-red. Hosted Actions did not start because of billing; neither hosted green status nor the whole four-section/deployment acceptance is claimed.

Artifacts: `/private/tmp/larp-pr70-local-ci/results/summary.json`, SHA-256 **`c62921bc0536cc3ee309d16e5c643a25cd7740be03c85f484b9305297f395754`**, contains environment, commands/check dispositions and per-file log hashes. Raw logs, exact Dockerfiles/harness, source clone, native/amd64 runner image identities and traces are under `/private/tmp/larp-pr70-local-ci/`. x86_64 host bundle SHA-256 **`571ba36bed2fd9e9a48864bbb4dd245c855a6ffdf7c1d65acf3b06de010025e6`**; additional aarch64 bundle SHA-256 **`6f394f45dd208f634bb4a1ccfa1a359688c68b015bce8769fc74e5e30b6629d1`**. Generated material stays outside Git. Initial local harness issues (GitHub helper PATH and overlaid pip files) were corrected without changing repository code before the reported runs.

During execution the target independently advanced to **`5c1c9c854b66a9d0c6eddba39c2be91cc3742483`** through PR73's calendar/tool/tests. Those new target changes are not in this exact-source run. PR70 itself remained at `65e768c` throughout. **Still not merged:** Codex must refresh/integrate the then-current target and validate that candidate; native x86_64 runtime/hosted acceptance remains outstanding, with an account administrator owning the billing fix. Existing shared/deployment gates retain their owners. Only this task's two systemd containers, two PostgreSQL containers and internal network are cleaned up; other local tasks/services are left alone. Result-record commits after this entry change documentation only.

## C-FND-012 — attached-text bypass of the encoded-reflection screen (prospective, 2026-10-15)

Source: final-C merge review by Yao Zhu with Claude Code, C-REQ-012, same class as [review comment 4280232976](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/70#discussion_r4280232976) and PR74 thread r4280736991. At head `150bf9d` merged with target `67df600` (ordinary merge `14492cc`), a synthetic probe with fake HTTP and the arbitrary fixture bytes from `tests/execution/test_section_c_broadcast.py` attached Base64-alphabet text before and/or after each of the 28 encodings from `encoded_echoes()` (prefixes `signed_`, `tx-`, `a`, `ab`, `abc`, none; suffixes `_end`, `Z`, none; API rejection path). **353 of 504** combinations kept the encoded echo in the stored artifact and kept `response_body_base64`. Cause: `BASE64_TOKEN` absorbs the attached text into one token, so decoding starts at the wrong 4-character alignment, and the literal fallback covers only the padded standard encodings. Example: `msg='signed_' + urlsafe_b64encode(raw)` on a rejected broadcast.

Pass criteria, written before the repair:

1. New regression `test_c_req_012_attached_alphabet_text_does_not_hide_encoded_reflections`: all 28 encodings × 5 prefix/suffix pairs × success and API rejection (280 subtests) through the real `Web3Broadcaster`/`Web3Client` with the fake opener. Each run makes one HTTP call, keeps the response hash, omits `response_body_base64` with reason `private_parameter_reflection`, and the artifact text does not contain the echo.
2. The regression fails on the unrepaired application and passes after the repair. Every earlier C-REQ-012 case still passes, including the unrelated public Base64 one, which must keep its exact raw-body evidence.
3. Then the focused broadcast + market-data suite and the complete offline suite with disposable PostgreSQL. The legacy/forged-row archive/export expected failure is unchanged and all live capability gates stay.
4. Hosted CI for the final head runs on the CI mirror (IDEA-053 rules: same SHAs, same branch name), because org Actions are blocked by billing. The PR70 merge into `codex/system-testing-20261012` follows only if that run is green on all four jobs.

Known limit, not covered by this repair: an echo split by whitespace or line breaks (MIME-style wrapping) is not reassembled.

Status: regression committed with these criteria in `6f364bb`; application repair NOT YET COMMITTED; nothing run from this commit yet. (The probe above and one local red run of the uncommitted regression came before this commit; the red run is repeated from the pushed commit in C-RESULT-013.)

## C-RESULT-013 — C-FND-012 repair, mirror CI and merge (2026-10-15)

Yao Zhu with Claude Code, at Yao's request to fix final review C, run CI on the mirror and merge.

- Target `67df600` (PR69) is in PR70 through ordinary merge `14492cc`. The only conflict was the LEDGER row order; the IDEA-049-C, IDEA-054 and IDEA-049-D rows are all kept. Nothing was rewritten or force-pushed.
- Red at pushed regression `6f364bb`: `tests/execution/test_section_c_broadcast.py` gives **188 failed subtests**, 10 passed tests, 223 passing subtests. Every earlier C-REQ-012 method still passes.
- Repair `fc7a653` (`larp/marketdata/web3.py`): the Base64 token screen now tries all four start offsets, so attached text cannot shift the alignment, and it decodes the final partial group instead of discarding the token. A suffix only adds trailing bytes after the exact echo bytes, so no trimming is needed. Literal matching, hex case folding, duplicate-key screening and the public-evidence path are unchanged.
- Green at `fc7a653`: focused broadcast + market-data **59 passed, 1 skipped, 473 subtests**. The scratch probe (504 combinations) finds **0** leaks.
- Complete local suite at `fc7a653` (Python 3.13.16 / PostgreSQL 16, not the CI pins): **1385 passed, 7 skipped, 1 xfailed, 2026 subtests**. The expected failure is still the separate legacy/forged-row archive/export case.
- **Mirror CI**, commit `fc7a653`: [larp-ci-mirror run 38712281044](https://github.com/Cookiemunchrr/larp-ci-mirror/actions/runs/38712281044) (pull_request into the identical base `67df600`, mirror PR #2) is **green on all four jobs**. Terraform aws and bootstrap pass. Runtime on Python 3.12.15 / PostgreSQL 14.24 gives **1388 passed, 4 skipped, 1 xfailed, 2026 subtests**, real systemd **3 passed / 5 subtests**, and the offline demo and Docker build/run pass. The x86_64 host bundle passes. Push runs [38712261021](https://github.com/Cookiemunchrr/larp-ci-mirror/actions/runs/38712261021) (this head) and [38712261945](https://github.com/Cookiemunchrr/larp-ci-mirror/actions/runs/38712261945) (base `67df600`) are also green. This is mirror evidence on native x86_64 GitHub runners, not org-repo CI, which stays blocked by billing.

This closes C-FND-011's remaining CI and merge item: PR70 is merged into `codex/system-testing-20261012` after this documentation commit. Still open with their owners: the legacy/forged-row archive/export expected failure (#23, D), MIME-style wrapped echoes (the known limit above), proposal/signing/router lifetimes, the signer's trust in primary-supplied facts, the router/decoder/native-receipt/first-BNB capability gates, canonical balance reconciliation and the real host/wallet rehearsal. No deployment, real credential, signing, broadcast or AWS action took place.

## WR-C — review fixes #44 #54 #53 (2026-10-15)

Yao Zhu with Claude Code, at Yao's request to fix the open C-area issues from the whole-repo review (tracker #42): [#44](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/44) (WR02, P1), [#54](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/54) (WR12, P2) and [#53](https://github.com/binance-hackathon-glasswing/binance-hackathon/issues/53) (WR11, P2). Base `codex/system-testing-20261012` at `7b7acd2`; branch `claude/wr-c-execution-fixes-5c3ee3`; one PR into the base. All three reproduce on `7b7acd2` (code inspection; the red tests below prove it). Order: these criteria are committed and pushed first; each fix's failing tests are pushed before its repair. Nothing runs live: no key, signing, broadcast, ai-seeds call or AWS change. Signing stays gated (UnverifiedRouter, fake-only Executor).

Pass criteria, written before any test or code:

**#44 signer-pinned signing policy.**
1. The signer config (`SignerService.v1`, root-owned `/etc/larp/signer.json`, already pinned by the release manifest through `verify_service_config`) gains a required `signing_policy`: allowed spender/router addresses (non-empty), allowed token contracts (a subset of USDT, the five bStocks and native BNB), a per-token input cap in base units (applies to every approve amount and every swap input), a per-transaction fee cap in wei (`gas × gas_price`), and a `cap_basis` label. Invalid or missing policy → `check`/`run` refuse to start (exit 4). The example config carries clearly marked example values (`cap_basis` = `EXAMPLE_PENDING_TEAM_DECISION`) and a `live` run refuses to start while the caps are still the example.
2. `SignerService` requires a policy and checks it on every request before the key is used, independently of the intent: approve token and spender in its lists, amount ≤ cap, any amount ≥ 2^255 refused as unlimited, fee ≤ cap; swap target in the spender list, decoded tokens in the token list, decoded input ≤ cap, recipient = the signer's wallet, no native value. The intent's own tokens and router must also be in the lists.
3. New PostgreSQL test (real `larp_execution`/`larp_signer` roles from `deploy/postgres/roles.sql`): an intent registered as `larp_execution` with `router` = attacker and `amount` = 2^256−1 passes the primary's checks, is authorized, and the signer refuses it without touching the key (`sign_transaction` not called, no signature row). Further subtests: allowed spender with an unlimited amount, an amount one unit above the cap, a fee above the cap, and a token outside the list are each refused; the same attempt within policy is signed. A test shows no database role can change the policy (the signer never reads it from the database; it comes only from the pinned file).
4. Every existing signer barrier still holds: the GAP-29 swap refusal (UnverifiedRouter), manifest/build binding, run fencing, HALT, clock checks, and all current `tests/signer` tests pass with the policy added to their fixtures.
5. Cap VALUES are a team decision, recorded here and in the PR as a decision request (owner: Isaac with Keith); the code ships only the example.

**#54 definite broadcast rejection.**
6. `Web3Broadcaster` classifies a definite node rejection (API error whose message says insufficient funds, nonce too low, intrinsic gas too low, exceeds block gas limit or invalid sender) as `Rejected` with a fixed reason code, never the response text. A timeout, transport error, lost/undecodable response, rate limit, `already known`, or any unrecognised error stays "outcome unknown" exactly as now. Signed-byte secrecy is unchanged: no new storage of bytes or response text, and the existing C-REQ-012 broadcast tests pass.
7. `Executor.broadcast` records a `Rejected` send as attempt state `REJECTED` (non-terminal, keeps `broadcast_at`, keeps the wallet barrier). In `reconcile`, after `broadcast_at + timeout`, when the transaction is absent from the chain and the wallet's chain nonce (latest = pending) equals the attempt's nonce, the attempt becomes `NOT_SUBMITTED` and the execution `ABORTED` (terminal), which frees `execution_wallet_barrier`; the store accepts that transition only from a `REJECTED` attempt. The execution service publishes a `NOT_SUBMITTED` fact (reason `BROADCAST_REJECTED`) so the runtime releases the intent's reservations, and it never publishes `BROADCAST_ATTEMPTED` for a `REJECTED`/`NOT_SUBMITTED` attempt.
8. Tests (red first): an "insufficient funds" rejection through the real broadcaster with a fake HTTP opener ends terminal after the nonce check and a new execution for the wallet can start (PostgreSQL barrier). The record stays non-terminal before the timeout, when the nonce moved, when the nonce is unknown, and when the hash is found on chain. A timeout/lost response still stays `UNKNOWN` and holds the barrier after the timeout.

**#53 guard request budget.**
9. `LiveGuards` stops using the full market observation: no price request and no cost quotes. It reads open state only (token `openState` from the bStock list, underlying `openState`), caches the bStock list per round, and reuses one open-state observation across the steps of an attempt while it is fresher than a freshness window (default 10 s, configurable 1–30 s). Facts older than the window are refetched, so a market close is seen within the window. The nonce stays fresh at every step. Facts still never default true.
10. New test: one approve→swap driven through `ExecutionService.advance` with `LiveGuards`, `LiveVenue` and the real `Web3Client` (real 0.35 s spacing on a virtual clock, fake HTTP opener). It records the number of Web3 requests and the forced spacing. Pass: at most 12 Web3 requests and at most 7.5 s of spacing (half the 15 s intent expiry), against about 80 requests / 28 s on the base. Separate tests: no cost quote or price request from the guards; one bStock-list fetch per round; refetch after the window; a stale or failed observation blocks signing.

**Whole PR.** Full offline suite on Python 3.12 / PostgreSQL 14.24 (pinned image): no new failures against the base baseline (1417 passed, 1 xfailed #23, plus environment-only failures). Mirror CI run on the head (Yao Zhu pushes to `Cookiemunchrr/larp-ci-mirror` and dispatches `runtime.yml`). Issues get one status comment each; none is closed and nothing is merged in this task.

Status: criteria committed before any test or code. Results follow in WR-C results.

## WR-C results — #44 #54 #53 (2026-10-15)

Branch `claude/wr-c-execution-fixes-5c3ee3`, all commits ordinary and pushed before each run: criteria `27f5eec`; #44 red `1feb530`, fix `65cc297`; #54 red `09a5fd8`, fix `ced04ae`; #53 red `09e4a09`, fix `81e0d22`. Local runs: macOS, Python 3.12.14 from `deploy/requirements-test.lock`, pinned `postgres:14.24-bookworm@sha256:5a05f61a…`, plugin autoload disabled. No key, signing, broadcast, ai-seeds call or AWS change.

| Issue | Red (pushed tests, unfixed code) | Green (fix) |
|---|---|---|
| #44 WR02 | `tests/signer/test_wr_c_policy.py`: 24 failed. Scratch probe on `7b7acd2`: approve(attacker, 2^256−1) registered as `larp_execution` → 1 signature, 0 refusals | all `tests/signer` 71 passed / 92 subtests; the malicious intent is refused before `sign_transaction` is called |
| #54 WR12 | `tests/execution/test_wr_c_rejection.py`: 10 failed, 2 passed (every rejection was "broadcast outcome unknown"; record held the barrier) | 12 passed; insufficient-funds rejection → `REJECTED` → after 120 s, hash absent, chain nonce = attempt nonce → `NOT_SUBMITTED`/`ABORTED`, barrier freed, `NOT_SUBMITTED` fact (reason `BROADCAST_REJECTED`) |
| #53 WR11 | `tests/execution/test_wr_c_guard_budget.py`: 10 failed, 3 passed. Base: **50 Web3 requests, 16.80 s spacing**, intent expired before the swap | 8 passed / 5 subtests. **9 requests, 2.10 s spacing** (criterion ≤ 12 / ≤ 7.5 s); with a 10 s approve confirmation 11 requests, 2.45 s; 47 unpaced RPC calls (fresh nonce at each step) |

What changed:
- **#44.** New `larp/signer/policy.py` (`SigningPolicy`). `SignerService` now requires a policy and checks every request against it before the key is used. The policy is read only from `signing_policy` in the signer's pinned config (`config/hosts/signer.example.json` carries example values marked `cap_basis: EXAMPLE_PENDING_TEAM_DECISION` and `allowed_spenders: null`), and a `live` signer refuses to start with the example caps. GAP-29 swap refusal, manifest binding, fencing, HALT and clock checks are unchanged. No `deploy/` change was needed: the config file is already pinned by `verify_service_config`; only its contents grow. Doc: `docs/build/architecture-deployment.md` signer trust boundary paragraph updated.
- **#54.** `larp.execution.Rejected` (fixed reason codes). `Web3Broadcaster` classifies from its in-memory, already-redacted artifact record (`_Recorded` wrapper; nothing new persisted). `already known`, `known transaction`, `replacement`, timeouts, transport errors, non-JSON, rate limits and unknown errors stay `DependencyUnavailable`. `Executor.broadcast`/`reconcile`, `ExecutionStore.commit` (NOT_SUBMITTED only from a rejected possible send), `ExecutionService.advance` and `ExecutionLoop._unpublished_terminal` use the new `possibly_submitted`. The C-REQ-012 secrecy tests still pass.
- **#53.** `LiveGuards` reads open state only (bStock list + underlying market), cached per round and reused while fresher than `market_freshness_s` (default 10 s). No price request, no cost quotes from guards.

Test corrections after the red commits (test bugs, not weakened criteria): #44 a distinct signing request per swap subtest and a DSN file in the example-config test; #54 nonce evidence restored before the barrier check; #53 the confirmation wait applies to the approve only. One test-only refactor: `tests/signer/test_service.py` fixtures split into `RolesCase`/`CommandCase` bases. One-line fixture change outside C's tests: `tests/runtime/test_round_driver_service.py` passes the test policy to `SignerService`.

**Full suite** (sequential; an earlier parallel attempt crashed on shared-server faults and is discarded): head `81e0d22` **1449 passed, 7 skipped, 1 xfailed, 2105 subtests**, 203.5 s; base `7b7acd2` on the same machine and server **1419 passed, 7 skipped, 1 xfailed, 2059 subtests**. Identical (empty) failure lists; the xfail is still #23. +30 tests, +46 subtests. Mirror CI on Linux is pending (Yao Zhu runs it).

**Decisions and residual limits (owners):**
1. **Signer cap values** (Isaac with Keith; Keegan provisions): per-token input caps, the fee cap and `allowed_spenders` (from Gate B router evidence). The example (50 USDT, 1 token per bStock, 0.005 BNB fee) is not a decision. Tracked in `docs/INCOMPLETE_WORK.md`.
2. **Rejected-then-landed residual** (Isaac): a swap released as NOT_SUBMITTED has no `tx_hash` in its round log. If the rejected bytes later landed anyway (they were absent from our RPC and the nonce unused after 120 s), the next execution's reconciliation sees unexplained nonce use and holds the barrier, but that hash would not be in a round log. Accepted as very unlikely; Isaac to confirm or require logging the hash.
3. The rejection message list is matched on text the Web3 Open API passes through from the node; the kit documents only "nonce" messages, so the list needs a recorded-real check at Gate B (Isaac).
4. The guard freshness window (10 s) is a default, not a reviewed value (Isaac).

**Mirror CI (2026-10-15):** [larp-ci-mirror run 38752161594](https://github.com/Cookiemunchrr/larp-ci-mirror/actions/runs/38752161594) (workflow_dispatch, head `64fd5c6`) is **green on all four jobs**. Runtime on Linux, Python 3.12.15 / PostgreSQL 14.24: **1452 passed, 4 skipped, 1 xfailed (#23), 2105 subtests**. Real systemd: 3 passed / 5 subtests. Terraform aws 15 passed, bootstrap 1 passed. Host bundle passes. The org-repo CI did not start (billing). The PR is not merged.

## CP-01 — Isaac checklist task6: signer-cap candidates (2026-10-17, prospective)

Separate branch `codex/isaac-06-signer-caps-20261017`, base integration2306583; parent44. No signer/runtime/default config change, AWS, keys, signing, API call or new quote capture. Use only retained public unsigned W08 reference data and repository contracts; never commit raw wallet/API evidence. Keith reviews the candidate against the actual measured profile; Isaac confirms the final policy; Yao installs/binds only after approval. This slice is preparing a proposal, not selecting or activating it.

Prospective criteria before extraction/builder/test execution:
- **CP1:** explicit finite candidate input budgets35USDT development /70USDT final; these exceed current equal-weight20.10/40.20USDT and S1’s proposed largest28.60/57.20USDT at100/200 equity, without changing the strategy’s smaller limits. Propose per-token raw input caps from each reference token price at a50% reference-price floor, rounded upward with exact rational arithmetic; label historical/conditional coverage and require current profile/holdings/adjustment review before approval. A price reference is not a forecast or guaranteed floor.
- **CP2:** propose max fee0.0002BNB =200000000000000wei per transaction as a separate bounded budget, explicitly not a measured safe fee value; compare actual gas/price maxima during Keith’s review. Allowed spender is only observed router0xb44446b0c8e56988c34f7ff73ae904982b5fdda5, pending verified router evidence. Five pinned bStocks +USDT allowed payable inputs; nativeBNB receive-only, no sell/input cap. Output wrapper is a non-deployable proposal, with signing_policy.cap_basis kept EXAMPLE_PENDING_TEAM_DECISION until real approval.
- **CP3:** implement an offline deterministic builder using strict public reference schema/provenance, explicit token decimals and source hashes, integer/rational arithmetic, finite caps <2**128 and actual SigningPolicy validation. Never accept floats, wrong token/chain, missing/extra public fields, invalid hashes, nonpositive prices/scales or oversized quantities. No wallet/secret/network/service startup. Exclusive output file, no silent overwrite.
- **CP4:** meaningful tests against the actual SigningPolicy checker: each proposed token cap passes exactly and refuses +1; fee equality passes and above-cap refuses; only router spender and allowed tokens, native receive-only; unit conversion/rounding at non18 decimals; malformed source/provenance rejected; CLI cannot overwrite. Existing original signer policy stays unchanged. Push code/tests before running; report precise SHA/count/skips and no live qualification.
- **CP5:** retain private raw reference files outside Git, publish only safe public prices/decimals and exact artifact hashes. The current reference may be stale and cannot be called measured Oct20-profile approval. Document per-request caps do not enforce a cumulative daily/wallet spending limit, reference-price/split/price-jump limitations, USDT raw18 vs money6, one full sell-position coverage check and pending reviewers/install gates. Close only the proposal slice; whole parent44/host readiness remain open.

### CP-01 candidates and local verification (2026-10-17)

Criteria ff1fd6f; tool/tests/public reference ebe8b74 were pushed before execution. `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.execution.test_signer_caps_proposal -v`: **7 passed,0skipped**, Python3.13/macOS. These use actual SigningPolicy consumer checks for six tokens xapprove/swap, equality/+1 at the candidate amount and fee boundaries, wrong spender/native input/native value, rounding at8decimals, bad/private fields, output determinism/0600/exclusive creation and refusal non-echo. No key/DB/network/runtime service. A final extra out-of-universe token assertion is added under CP4 and will be pushed before rerunning this same small suite.

The pushed tool generated `docs/build/evidence/signer-caps-proposal-20261017.json`, SHA256 **2ca75fd48a65ae6b494be310e97f08c8ea443f5854ff5a38ee4bc351ec7d900a**, without networking. Concrete candidate USDT ceilings35/70, fee200000000000000wei, historical50%mark-floor stock caps and router-only spender are shown in `docs/build/SIGNER_CAPS_PROPOSAL.md`; exact integer caps and provenance in the JSON. The public reference extracts only the five pinned tokens' marks/decimals from retained W08 artifactc55871f9379ea589b2f1a7dffb5422953941e7772201c8274cfd78b858f78669, response754d3733058edb2b99a15676308e838b17f3d50080b9ffc001d747ea81297a7e, observed2026-10-10T11:38:00.565Z. Raw wallet/API context stays ignored; prices use the project's USDT mark convention, not executable-quote guarantees.

The candidates cover nominal current equal-weight20.10/40.20 and proposed S1(max95%gross x30%name +reserve)28.60/57.20 budgets. Current quantities/profile, gas price/limit, historical floor and corporate adjustments still need review. At original reference prices, stock caps permit approximately70/140USDT of stock input; the35/70cash cap applies to USDT inputs only. Existing caps are per-request, not cumulative wallet/daily limits. No per-leg split or adjustment solution is assumed. Both generated cap_basis labels stay EXAMPLE_PENDING_TEAM_DECISION and the root wrapper is not SignerService.v1, ready_to_install=false; no approval/activation or real-service/live readiness.

Keith reviews actual profile/raw input/holdings/fees; Isaac confirms chosen policy hash and each environment; Yao owns approvedconfig/manifest binding and IDEA080 provisioning, followed by Isaac key placement. Parent44 stays open. This separate slice closes146 only after proposal/tool PR review/merge. Router source/task3, recorded-route task4, lifetime#27/PR144 and live first gas/host validation remain separate.

### CP-01 final focused verification (2026-10-17)

At pushed317d22e, reran `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.execution.test_signer_caps_proposal -v` after adding the explicit out-of-universe token check: **7passed,0skipped**. The added unknown token is refused for both approve and swap by the actual policy. Candidate bytes/hash unchanged; no production-policy or runtime behavior changed. `git diff --check` passes. No broader repetition is needed for this isolated offline tool; full Linux/CI/host readiness is not inferred. The proposal stays unapproved pending owners and fresh profile/holding/fee checks.

### CP-01 PR / owner-decision handoff (2026-10-17)

[PR148](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/148) is open/mergeable on the separate task6 branch into integration, with `Closes #146`. Parent44 links the concrete proposal and keeps actual numeric approval/config/install/qualification outstanding. Isaac's confirmation-for-review question is pending:35/70USDT-input budgets,0.0002BNB fee ceiling and50%historical-mark stock floor (about70/140USDT stock inputs at reference prices); no silence is treated as approval. Keith still checks current full-position/raw-quantity/top-up/fee/adjustment coverage, Isaac confirms the exact final policy/environment hashes and Yao installs after approval. No service config/default/validator/key/permission change or activation occurs here.

Org CI [39015435747](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/39015435747) at6c92638 did not start runtime tests: check annotation confirms failed account payments/spending limit (#98). Local focused source at317d22e remains7passed,0skipped; no new CI/host/live acceptance is claimed. Changes are committed/pushed, with clean tree and no unpushed commits; whole-project handoff readiness, owner approval and PR merge remain pending.

### CP-01 D1 — Isaac confirms candidates for review (2026-10-17)

Isaac explicitly selected **“Confirm proposed candidates for review (Recommended)”**: USDT-input limits35 development /70 final, fee ceiling0.0002BNB per transaction, historical50%mark-floor stock caps (approximately70/140USDT stock input at the reference prices). This supersedes the pending confirmation question in the dated handoff above. It confirms the existing candidates for Keith's review, **not numeric approval for installation**, current-price/profile qualification or final-wallet readiness.

The candidate JSON SHA256 remains2ca75fd48a65ae6b494be310e97f08c8ea443f5854ff5a38ee4bc351ec7d900a; ready_to_install=false and EXAMPLE_PENDING_TEAM_DECISION labels remain appropriate and unchanged. Keith must check current holdings/raw trade and gas-top-up quantities, selected profile, metadata/adjustments and fee coverage. Isaac then confirms the exact approved policy hashes per environment; Yao installs/binds only after that approval and IDEA080 checks. Parent44 stays open. PR148 retains Closes146 for the proposal/tool slice.

Documentation/status changes only: focused tool/consumer source remains the tested317d22e (7passed,0skipped); no application rerun, signing, key/config/host change or activation. Next independent record task is #106's prior2USDT dev first-gas swap: DEPLOYMENT_DAY§5 has flagged hash/time/BNB placeholders. Isaac was asked for its public tx hash/link; no transaction details or completion are invented while that input is pending.

### CP-01 R1 — PR148 output-byte portability review (2026-10-17)

**Finding (P2):** the builder writes through a text stream with the platform's
default newline conversion and encoding. On Windows, each LF becomes CRLF,
so the same public reference cannot reproduce the committed proposal hash.
This contradicts CP3's deterministic output and the reproduction procedure.
The existing mode-0600 assertion also assumes POSIX permissions on Windows.

Prospective acceptance, before running the new regression:

- **CP-R1-1:** generate from the committed public reference into a temporary
  file on Windows. Exact output bytes equal the committed proposal's UTF-8/LF
  representation; reproduce the regression before changing the writer.
- **CP-R1-2:** after the fix, the same check passes on Windows and Linux;
  run all signer-cap proposal/policy boundary tests on both platforms.
- **CP-R1-3:** preserve exclusive creation/non-overwrite and POSIX mode 0600;
  enforce that mode assertion only on POSIX. Candidate values, canonical
  artifact/hash, unapproved status and all installation gates stay unchanged.

This is part of the requested PR143–151 review. Other dispositions and the
separate merged-PR147 timeout fix are recorded in IDEA-058 GA15c / PR153.
No whole backlog item closes, and no host, wallet or live action is authorized.

#### CP-01 R1 results (2026-10-17)

Criteria/regression `49aa6a5` and fix `4e4e74a` were pushed before execution.
The new exact-byte regression fails on Windows before the fix (CRLF differs
from the committed LF artifact) and passes after the binary UTF-8 writer fix.
All eight proposal/policy tests pass on Windows/Python 3.14 and on Linux/Python
3.10.12 with exact Git blobs; zero skips on either platform. Linux still
verifies mode 0600. Exclusive creation, non-overwrite, cap/fee boundaries and
unapproved labels remain covered. The committed candidate bytes and their
SHA256 `2ca75fd48a65ae6b494be310e97f08c8ea443f5854ff5a38ee4bc351ec7d900a`
are unchanged. `git diff --check` passes. No full-suite, org CI or hosted/live
acceptance is inferred. PR148 contains the fix; PR153 carries GA15c-R1.

## SL-01 — Isaac checklist task 5: signing-lifetime proposal (2026-10-17, prospective)

Issue142, separate branch `codex/isaac-05-signing-lifetime-20261017` from integration352446b. Isaac confirms the private RPC handoff to Yao is sent; record RPC-Q01 H1 in IDEA-055 and parent92. PR135 and PR137 are now merged into integration. Router source task3/#138 and recorded-route task4 remain blocked and separate; this is the next independent checklist deliverable.

This is **a proposal, not adoption or a runtime change**. Keith reviews the quote-age/proposal implications; Keegan decides C-OPEN-003/#27 and owns the code change. Existing profile/expiry/deadline/signer gates stay in place. No API, AWS, wallet/key, signing, capture or runtime action is required.

Acceptance criteria before any experiment or covered-code execution:
- **SL1:** trace current proposal/profile, risk/RuntimePlanner expiry, exact-byte executor/signer checks, post-approve re-quote and recovery; cite source paths and exact reviewed heads. Distinguish kit-stated ~30s quote TTL, unverified real encoded deadline, and #53's fake-transport/virtual-clock spacing evidence.
- **SL2:** specify both options: a finite immutable authorization admitted while the proposal is fresh, or a source-qualified router deadline no later than the existing proposal/intent expiry. Show illustrative timeline arithmetic and the exact constraints each preserves/changes; do not suggest editing arbitrary returned calldata.
- **SL3:** recommend an option with bounded conditions, required real latency/deadline evidence and implementation acceptance cases. Keep quote/data freshness, economic limits, fencing/HALT/window checks, parent expiry, uncertain-send reconciliation and no-replacement/no-restart-extension invariants explicit. Any numerical lifetime is only a candidate for owner decision, not a measured safe value.
- **SL4:** supply a reviewable proposal document and separate PR closing only issue142's writing slice, leave parent27 open for Keith's review, Keegan's decision/code and real qualification; narrow live backlog without removing whole incomplete items. Static references/arithmetic/diff checks suffice for this docs-only change; do not claim new application, host or on-chain tests.

### SL-01 written proposal / static validation (2026-10-17)

Prospective criteria were pushed at9eb9934. `docs/build/SIGNING_LIFETIME_PROPOSAL.md` supplies both requested options, a conditional recommendation for separate finite authority (A), worked15/30/60s illustrations, the deliberate policy change and its cross-component scope, required source/timing evidence, expiry/restart/uncertain-send invariants, and ten prospective implementation acceptance cases. **No option or60s lifetime is adopted.** Keith reviews; Keegan decides C-OPEN-003/#27 and owns the code change. Source qualification/task3 and recorded-route task4 are still separate blockers.

SL1 static trace at integration352446b: profiles/policy/proposal validation → risk quote expiry → RuntimePlanner discretionary clamp → persisted command expiry → executor before approval/requote → signer and reconciliation. The kit's Trading flow step3 says approximate30s quote lifetime; cost_summary labels the default KIT_STATED, not measured encoded expiry. EXP-005 confirms encoded expiry remains unverified. #53 is CLOSED after merged PR79; its9requests/2.10s (11/2.45s with simulated10s approval wait) are fake-HTTP/virtual-clock spacing, not real latency or #27 proof. SL2/SL3 specify both alternatives, A's immutable t0/A and bounded candidate/margins, B's currently unqualified shorter-deadline mechanism, conservative window/expiry semantics for all action kinds, and the difference between approval/chain reconciliation and permission to sign anew. SL4 publishes the writing slice with no runtime/config/default/validation change; parent27 remains open for review, decision, implementation and qualification.

Validation for this docs-only change: checked referenced repository files and existing source/fixture descriptions, illustrative arithmetic (10<40<=60;40>15;65>60), unresolved statuses and owner split; `git diff --check` passes. No application tests/runtime/probes, API, wallet/key, signing, broadcast, AWS or receiver action was run. The old application behavior remains unchanged; no Linux/CI/host/live acceptance is claimed. RPC-Q01 H1 records the user's confirmed private handoff without endpoint values.

### SL-01 PR handoff (2026-10-17)

[PR144](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/144) contains the separate task5 writing deliverable and `Closes #142`, targeting the integration branch. Proposal source atb484d95, criteria9eb9934, docs/diff/source/arithmetic checks only. Parent27 links the proposal and retains Keith's review / Keegan's decision, implementation and qualification; no runtime setting is approved or changed. RPC private handoff is recorded in IDEA-055 H1 and parent92. All task5 changes are committed/pushed; no unpushed commit or dirty working tree. PR review/merge and owner decisions remain outstanding; this is not whole-project handoff readiness.

### SH-01 — delegated development signer handoff (#160, 2026-10-17; prospective)

Isaac explicitly asks the assistant to take over Keith's technical cap review and Isaac's preparation work, for a file Isaac can pass to Yao Zhu. This authorizes the technical work; it does not establish that Keith personally reviewed anything or supply missing live inputs. No deployment, wallet key, signing or AWS work is requested.

- **SH1:** from integration `0672fb8`, retain the exact CP-01 development cap candidate and known public development wallet in a concrete `SignerService.v1` handoff. Leave run/build/database/router-evidence fields unset if their correct signed-run values are unknown, name every such field in the handoff notes and do not label the result installable. Preserve the example cap basis until the missing acceptance evidence exists.
- **SH2:** use the real `SigningPolicy` parser and existing proposal/policy boundary suite to check the handed-off exact bytes: six payable tokens, router-only spender, receive-only native BNB, 35-USDT input and 200000000000000-wei fee ceilings; unlimited, cap+1, fee+1, foreign-token/spender and native-input refusals remain effective. Verify that the handoff policy exactly equals the retained CP-01 development candidate. Do not alter enforcement or cap values.
- **SH3:** the real signer config validator must refuse the deliberately unfinished handoff, without network, DB or key access; this confirms it is an assembly input rather than a qualified service configuration. Validate full JSON parsing and diff hygiene. No new test file is needed for this static config/document handoff.
- **SH4:** write exact rational nominal coverage for EQUAL_WEIGHT and proposed S1 at the known 100-USDT development funding envelope, distinguish that arithmetic from the unavailable selected profile/current holdings, and state the gas-envelope inequality rather than asserting the fee ceiling is adequate. No inference of current holdings or verified router semantics from old quote/funding records.
- **SH5:** record missing external inputs, the run/profile/hash rebinding and exact Yao assembly steps. Keep #44 and the partially complete backlog item open. Open a separate PR closing #160's handoff slice only; preserve all existing source/lifetime/provider/host gates. No new API calls, model calls, deployment or transaction in this slice.

### SH-01 results — 2026-10-17

SH1/SH2/SH3/SH4/SH5's bounded handoff deliverable is prepared in [signer-handoff-20261017](../build/signer-handoff-20261017/README.md), not an approved service configuration. It takes over the available technical review on Isaac's explicit request without attributing Keith's personal endorsement. Exact policy bytes match CP-01. At pushed `7f5e5ac`: **8 proposal tests PASS, 0 skips**; actual handed-off policy accepts **14 valid boundary cases** and refuses **34 invalid cases** (cap+1, unlimited, fee+1, foreign spender/token, native pay/value). Real signer config validation refuses the missing run/build IDs. Exact rational checks confirm 20.10/28.60-USDT nominal positions fit 35, and the 1116000-gas illustration's upper price is 179211469 wei. No selected profile, current holding, measured fee adequacy or router-source verification is inferred.

Draft config SHA256 `339c42025c9771f7d06eb16b5cf4b3ae165556f68d071f977abbe44e6fa31442`; canonical policy SHA256 `254f5c31b2b1bb22f706acfb95343f9e885097786d22918747eb6951c5a42033` (UTF-8 sorted compact JSON + LF). Neither is an approved installed-policy/config hash. The machine-readable review names missing facts and every null host field. No decision/trading/enforcement code changed; no new API/network, key, signing, model, AWS or deployment action occurred. Full suite and hosted acceptance not run for this static handoff. Parent44 remains open, backlog narrowed rather than removed. Actual profile/holdings/top-up/gas files remain the technical-review dependencies; Yao owns host/run/manifest assembly and source/lifetime/host gates remain separate.

SH-01 delivery: [PR #161](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/161), `codex/isaac-10-signer-handoff-20261017` → integration, includes `Closes #160`; open for review, not merged. Parent #44 updated with the delegated review, exact draft hash and remaining external facts. Isaac can pass the entire handoff folder to Yao for assembly, explicitly as an unfinished draft. No direct message to another person was sent.


## KMP-SIGN01 — Keith's #27/profile/limiter review (2026-10-18 UTC)

[Review/proposal](../build/REHEARSAL_PROFILE_REVIEW_20261018.md), criteria1536af8. Confirms SL-01 option A conditionally: keep measured quote age and fresh≤15s proposal admission, persist original t0/P and finite A=min(t0+L,signing_end,applicable action-window end), require every fresh decoded route now<deadline≤A with margin. Re-quote/restart/claim cannot extend A or economic limits; mandatory/gas bounds remain finite and action-specific. Expired authority never releases an uncertain approval's nonce/allowance/reconciliation barrier. OptionB needs a source-qualified caller-controlled deadline within the same original expiry, not calldata patching.60s and kit~30s are unqualified examples, #53 synthetic spacing is not host/finality timing. No runtime/profile/lifetime change; #27 remains open for Keegan's C-OPEN-003 decision/code and Isaac/Yao qualification.

Recommends first signed trade inside existing Oct21 00:00–Oct22 00:00UTC window after gates. Earlier dev window requires separate reviewed version. Proposes measured EQUAL_WEIGHT fallback if S1 inputs/weights/EXP-007/B4 remain unqualified; otherwise explicitly frozen/adopted S1. For S1 proposes DETERMINISTIC limiter (maps LLM-verified evidence, no separate exposure call), B4 producer still needed; this is not a deterministic assessor. MODEL remains unqualified until separate pinned call/audit/budget/expiry tests. POLICY-HOLD recommendation retains existing mandatory-sale HALT pending a reviewed bounded alternative. Isaac confirms profile/window/O6/POLICY-HOLD, Keegan owns B4/finite-authority implementation; no adoption inferred. Keith's #27 comment supplies the review; final Oct20 measured profile/cap proof remains open.

## SP-CAPS / SP-D1..5 — supplied proposal decisions and draft gas (2026-10-18)

SP-01 records Oct21 existing-window choice, conditional measured EQUAL_WEIGHT
rehearsal fallback, DETERMINISTIC S1 limiter and bounded per-symbol POLICY-HOLD.
Original IDEA075 O6 assessor adoption remains separate; no deterministic assessor
is adopted by selecting that limiter. Support conditional #27 OptionA; finite
L/margins/implementation remain Keegan's, with real router/Yao latency evidence.
Execution example ceilings1,200,000 gas×160,000,000wei=192,000,000,000,000wei
(<candidate200,000,000,000,000wei per tx). Actual gas remains unmeasured; aggregate
action budget/final measured profile/fresh full holdings/native quote and exact
policy approval hashes remain unavailable. #44 stays open; no install approval.

Full criteria, evidence, limits and remaining owners: [SP-01](../build/SIGNED_PREREQUISITES_20261018.md).

### SA-01 — offline signer installation-candidate assembly (2026-10-19; prospective)

Isaac requests the remaining feasible preparation after model/review branches
merged. PR133 now includes integration8c1e6df through normal merge cabc159; two
documentation conflicts preserve current evidence and the merged IDEA083 status.
Live #27/#44 remain undecided/unqualified; no new source/profile/host inputs were
supplied. The existing signer draft remains intentionally unusable.

Implement a separate offline assembler using the existing GateBCapsInputs.v1
numeric reviewer, rather than asking an operator to transcribe six fields and
policy amounts by hand. Pass criteria, before execution:

1. Re-run numeric coverage against hash-pinned profile, holdings, execution and
   policy bytes plus fresh quotes for all five buy/sell pairs and native top-up.
   Missing/changed pins, uncovered holdings/fees or stale/incomplete quotes refuse.
2. Refuse the pending cap marker including surrounding whitespace; load actual
   pinned router evidence through the production decoder and require matching
   router/spender. Missing/changed/invalid/wrong-router evidence refuses.
3. Copy exact execution run/build/wallet/mode and IAM DB/CA/evidence bindings;
   change only the dedicated DB role to larp_signer and use wallet.key credential
   delivery. Require the pinned local CA. Refuse local DSN or incomplete identity;
   never read a wallet key, DSN, AWS client, database or network.
4. Validate the generated candidate with production signer config/decoder code;
   record exact config/input hashes. Local assembly success never establishes
   owner/source approval, #27 resolution, manifest/host or Gate B acceptance:
   ready_to_install/signing_enabled/gate_b_accepted remain false.
5. Write only a new external directory, mode0700/files0600, without overwrites or
   symlink replacement. Refusal emits no config and no private input/error values.
6. Push tests/criteria before RED, implementation before GREEN. Run focused
   assembly/numeric/startup/policy/router tests. All external evidence in tests is
   synthetic. No AWS action, wallet key placement, signing or real provider call.

Actual preparation remains blocked on the real source-reviewed evidence,
selected measured profile/fresh holdings/quotes, exact #44 acceptance, #27
policy/code/timing and coordinator/operator run/release/DB/CA/session inputs.
An arbitrary decided cap_basis string is an operator assertion, not proof of
Isaac's approval. The tool must never manufacture approval or replace these gates.

SA-01 results at pushed runtime **a324fb71bb26fcf863315a4dfb5e9ee7202f530e**:

- Initial RED17bd49e: collection refuses the absent assembly module, as expected.
  No candidate assembler existed. Log: /private/tmp/larp-signer-assembly-red-20261019.log.
- Initial GREEN8fe5175:192 tests/349 subtests PASS,0 skips,22.15s with PostgreSQL.
  Additional filesystem REDa34ccab:1 failed/10 passed/7 subtests; dangling output
  symlinks were followed before resolution. Fixed before delivery by checking
  symlink identity before resolving. No runtime signer behavior was changed.
- Final: **194 passed,349 subtests,0 skipped**,21.66s. Pinned Python3.12.14 and
  PostgreSQL14.24 disposable loopback container. Suite: tests/signer plus
  execution tests caps_review, signer_caps_proposal, router_decoder/router_review/
  router_wiring, section_c_signed_state, signing_request; runtime tests
  service_configs, signed_models and model_routing_preparation.
  Log: /private/tmp/larp-signer-assembly-final-20261019.log.
- Eleven new assembler tests exercise exact bindings/hashes, independent signer
  role and local validation, numeric/refreshed quote refusals, pending caps,
  changed CA/router/pins, incomplete source evidence, local DSN and unsafe run
  refusal, private non-overwrite/symlink/checkout boundaries, partial-write cleanup
  and private-error redaction. Boundary mocks assert no DB/AWS/key/network calls.
  Existing policy malicious-intent, epoch/release authority and startup tests pass.

Real candidate assembly **NOT_RUN_MISSING_INPUTS**. No numeric cap approval,
source provenance/replay, #27 decision/code, host/release or Gate B claim follows
from these synthetic tests. No AWS, external RPC/model/receiver, wallet-key,
funding or broadcast operation. The original draft is unchanged; the new command
and precise owner dependencies are in SIGNER_INSTALLATION_PREPARATION.md.

Delivery: [PR184](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/184),
stacked on PR133, open for review. CI39210809471 runtime job117923526599 ran zero
steps; its annotation confirms account payments/spending limit (#98), so no
remote CI PASS is claimed. PR183 separately qualifies the merged IDEA083 release
and explicitly leaves signer gates open. PR133 records current owner requests
under IDEA-066 PC-SIGNER-ASSEMBLY01. No installation or real assembly is claimed.

### SA-RV01 — independent PR184 review criteria (2026-10-19)

Continue the user-requested PR133 work by reviewing the delivered offline
assembler before merging it. Source review checks exact numeric/config pins,
independent signer role and decoder/CA validation, private exclusive outputs,
redacted failures, no key/DB/network boundary calls and permanently false
installation/signing/Gate B flags. No new source, numeric approval or #27 timing
is inferred. Pass criteria: assembly, numeric coverage, signer policy/startup,
router and signed-model preparation regressions pass with disposable PostgreSQL;
then reconcile the tracker with qualified release183 and require full combined
Linux/mirror acceptance. Keep real assembly NOT_RUN_MISSING_INPUTS.

SA-RV01 independent source review and focused verification **PASS** at468d8e1
(application/tests identical to PR184c97d651). No code defect or weakened gate
was found. Exact pinned Python3.12.14 / disposable PostgreSQL14.24 suite:
**194 passed,349 subtests,0 skips**,49.19s. Tested assembly, numeric coverage,
all signer tests, router decoder/review/wiring, signed state/requests, service
configuration and signed/model-routing preparation. Log retained in this
workspace at /tmp/pr184-review.log. Real assembly remains NOT_RUN_MISSING_INPUTS;
no owner approval, source/provider/host qualification, key or signing action.
The result-only follow-up changes no application or test bytes.


### SA-02 — current signer input-readiness handoff (2026-10-19, prospective)

User asks for all available work toward installation. C05 review is separately
submitted in PR192, not merged/independently accepted. Prepare a current exact
input/owner handoff using the existing SA-01 assembler, never another template
or fabricated final signer.json. Base75e5d7f includes current PR133 e169fa1 and
C05; actual source/native/#27/#44/host inputs are still not supplied here.

Pass criteria before verification: preserve historical draft/review bytes; pin
its hash and all six null fields; check current blocker issues and local input
contract; show distinct remaining inputs/owners and production assembly/check
commands. Run the already pushed production validate_config against the actual
historical draft, expecting refusal without DB/key/network access. Verify the
readiness JSON, local links/anchors, old draft hash, changed-file scope and
renderer. No candidate generated without current approved inputs; all ready/
signing/GateB/installation flags remain false. Publish a separate stacked PR
and update PR133, with actual missing owner deliverables rather than repeated
public source/RPC probes or requests for secrets. No runtime implementation or
host/provider/trading acceptance is claimed by this handoff.


SA-02 results at pushed3a4727a: production `validate_config` refuses the actual
historical draft for missing run_id/build_id before database/key access. This is
an expected refusal, not a signer-ready PASS. Static inventory confirms exactly
six null bindings, unchanged config SHA339c42025c9771f7d06eb16b5cf4b3ae165556f68d071f977abbe44e6fa31442,
pending caps, and installation/signing/GateB/candidate flags false. Six added
local links/anchors, JSON, renderer and whitespace PASS; application/registers/
old draft/review unchanged. No new runtime tests were needed for this doc/report
slice; C05's38-test check is separate at1769b30, not new SA-02 qualification.
No actual caps-input packet was supplied; assembly/release check NOT_RUN.

Fresh GitHub issue inspection: #27/#44/#30/#119/#138 remain OPEN; #27's latest
comment is still the conditional OptionA proposal with60s illustrative, #44
still needs actual team cap values, and no source/RPC packet was supplied here.
No repeated failed public probes, new account, funding, paid call or AWS/key
operation was performed. Required inputs and actor sequence are in SA-02;
private credentials must not be posted as a response. No policy, source review,
provider right or exact-release acceptance can be replaced by numeric coverage.


SA-02 delivery: [PR193](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/193),
branch codex/isaac-signer-input-handoff-20261019, stacked on C05 PR192
(head75e5d7f; parent PR133 e169fa1). Keegan independently reviews both; no merge
or final config approval is claimed. PR133's description now links both slices,
marks the review/handoff delivered and retains the input/installation blockers.

Org CI39261664104 runtime job118090596312 atf6628e9 has zero steps and its
annotation explicitly reports failed account payments/spending limit. This is
not a runtime test failure or qualification PASS; no billing/AWS setting was
changed. Static checks6 added local links/anchors, JSON/hash/status flags,
renderer and whitespace PASS. No synthetic installable candidate was created.
All changes are committed/pushed in the two review branches; no unpushed work,
wallet/key/provider/receiver access or new artifacts in the IDE checkout.

## C-OPEN-003 / #27 — decision and LD04 criteria (Keegan, 2026-10-20, prospective)

**Decision: Option A** (SL-01, with Keith's conditional review KMP-02). Short
proposal admission stays. An admitted decision gets a separate, finite,
immutable execution authority:

    A = min(t0 + L, signing_end, S1 execution-window end if any, new_risk_end for a discretionary BUY)

`t0` is the decision snapshot time; `P` is the proposal expiry. A is computed
once, when the round is planned. It is journaled in the plan record and carried
as the command's `expires_ms`, so a re-quote, claim, restart or replay cannot
extend it. Each swap payload must satisfy `now + m < route_deadline <= A`, and
no step starts unless `now + m < A`.

**Values are not decided here.** `L` (`execution_authority_seconds`) and `m`
(`submission_margin_seconds`) are optional profile settings, set together or
not at all, with no defaults. Without them the planner keeps today's bound
(proposal and quote expiry), and #27's current refusals stay. A LIVE profile
that sets them needs per-value provenance like every other live value. The
numeric choice waits for LD02 host timings. New evidence: in all 15 recorded
quotes the route's own deadline is about 500 s after the quote (IDEA-070
B02-U), so a usable L is at least about 9–10 minutes plus the approve and
re-quote time. 60 s would refuse every swap. API-trust assumption (B09-TRUST01):
the route deadline is assumed to be enforced on chain. It is never used to
release an uncertain send.

**Pass criteria, written before any code (A1–A9):**

- A1. Without the two settings, the plan's `expires_ms` is byte-identical to
  today's: a discretionary intent never outlives its proposal (existing R03).
- A2. With them, `expires_ms` = A exactly, for a discretionary buy, a mandatory
  sell and an S1-bounded intent. It is not limited by `P` or the planning
  quote's expiry. A discretionary buy is capped at `new_risk_end`; a mandatory
  sell is not.
- A3. The plan intent records `authority` = {decision_ms, proposal_expires_ms,
  authority_ms, authority_seconds, margin_seconds}, with `authority_ms ==
  expires_ms`. Replanning the same snapshot is byte-identical.
- A4. The command schema refuses an `authority` record whose `authority_ms`
  differs from `expires_ms`, or whose fields are malformed. `map_command` sets
  `Intent.valid_until = expires_ms // 1000` and `authority_margin = m`. A
  restart from the same stored command gives the same Intent.
- A5. `validate_payload` with margin m refuses a step when `now + m >=
  valid_until`, and a swap when `now + m >= deadline` or `deadline >
  valid_until`. With m = 0 every existing check is unchanged.
- A6. The executor runs, with fake ports and a virtual clock, a 15 s
  proposal, a decoded deadline 30 s after each quote, and an approval delay.
  With L = 60, m = 5 the approve → finality → re-quote → sign succeeds. A
  re-quote whose deadline lands after A is refused. A restart at t = 35
  keeps A = t0 + 60. A late approval leaving no margin refuses the swap.
- A7. The signer's own `validate_payload` uses the stored intent's margin, so
  the signer refuses what the executor refuses.
- A8. Profile validation refuses: only one setting; m ≥ L; L below
  `proposal_seconds`; L above 3600; non-integers.
- A9. Full suite passes with disposable PostgreSQL.

Out of scope: choosing L/m (after LD02), an UNKNOWN-send release rule (unchanged:
reconciliation continues and reservations are kept), and gas top-ups (v1 is
initial-gas-only, LD07).

### LD04 results at `884021f` (2026-10-20)

Criteria were pushed first, at `b72448b`. Python 3.12 on Linux with a
disposable PostgreSQL 16.

- **A1 PASS.** Without the settings, plans carry no `authority`, and a
  discretionary intent stays within its proposal. The existing redteam R03
  still passes.
- **A2 PASS.** With L=120 and m=10 (test values), `expires_ms` = t0 + 120 s,
  beyond both the proposal and the planning quote. A discretionary buy 60 s
  before `new_risk_end` is capped at `new_risk_end`; a mandatory sell after
  it gets t0 + 120 s.
- **A3 PASS.** The authority record matches, and replanning is byte-identical.
- **A4 PASS.** Five malformed or mismatched records are refused. Mapping the
  same stored command twice gives an identical Intent with the planned end
  and margin.
- **A5 PASS.** The margin refuses a deadline inside the margin, a deadline
  after A and a step with no margin left. With m = 0 the existing rule is
  unchanged.
- **A6 PASS.** Approve → finality at +10 s → re-quote (deadline +40 s) → sign
  succeeds. A finality at +35 s, then a restart, keeps A = t0 + 60; the
  re-quote with deadline +65 is refused, and at +56 the margin refuses.
- **A7 PASS.** The signer runs the same `validate_payload` on the stored
  intent, covered by the A5 cases.
- **A8 PASS.** Five profile-setting refusals; the full profile validator
  refuses a lone setting.
- **A9 PASS.** Full suite: **2168 passed, 11 skipped (environment), 3641
  subtests**, 411.2 s.

A mutation check confirmed the margin test fails when the margin is removed
from the deadline comparison. Not done: choosing L and m (LD02 timings),
review/merge, and release qualification (LD15). No live or signed path is
enabled by this change.

### LD04-RV01 — PR 200 review criteria (2026-10-20)

Before running added checks: prove A is capped by `signing_end` and the S1
execution-window end even when L would extend beyond either; exercise
`LocalSigner.sign` with its independent clock and prove an exhausted authority
margin or route-deadline margin calls no transaction signing and stores no
signature. Run the authority, S1 execution and signer regressions, then the
full Linux suite with disposable PostgreSQL on the current integration base.
No numeric L/m or host qualification is adopted by these synthetic checks.

LD04-RV01 finding: the executor checks its supplied tick before the durable
`BROADCAST_ATTEMPTED` write, but `FencedRelease` checks only the S1 window with
its fresh clock. A database/scheduling delay can therefore submit bytes after
the new margin is exhausted. Before the fix, require a regression to refuse
that send (and any finite-authority release with no current clock), call no
submitter, and retain possible-send state for reconciliation. The fix must
also recheck the decoded swap deadline at that boundary with the pinned decoder.

LD04-RV01 results: both late-release/no-clock regressions failed at `1a3102b`
because the submitter was reached. Fixed at `49c6bb0`: the final release checks
the stored authority margin against a fresh clock, refuses clock regression or
absence, and decodes a swap again using the production-pinned decoder to check
its route margin. An exhausted margin never reaches the submitter. The durable
possible-send state/signature remain for reconciliation; no uncertain send is
released or retried. Positive coverage proves an in-margin swap sends exactly
the registry's bytes. Added signing-end, S1-window and independent local-signer
boundary checks pass too.

At `4b121a2`, native Linux Python 3.12.15 / disposable PostgreSQL 14.24:
**376 passed, 1150 subtests**, covering all execution tests, signer tests and
strategy/integration execution-window tests. Deviation rendering and whitespace
checks PASS. The first positive-send assertion incorrectly expected public
state to contain signed bytes; corrected to read the private signature registry.
Final combined full-suite verification follows with PR 201. Actions billing
prevents jobs from starting; no hosted CI or host/signing qualification claimed.
L/m selection and release qualification remain open.

### LD04-V01 — Keegan's L and m choice from LD02 timings (2026-10-20)

**Decision (Keegan): `execution_authority_seconds` L = 660, `submission_margin_seconds` m = 30.**

Inputs, all from the LD02 packet (IDEA-070 LD02, SSM `70965d91…`):

- Route deadline after the request: **499.1–500.1 s** in the 15 fresh quotes of record
  (the superseded first run agreed; consistent with B02-U's 15). A swap needs `now + m < deadline ≤ A`, so the
  re-quote must happen no later than `A − 500 s`.
- Quote round trip 135–253 ms; RPC round trip 412–489 ms per call on both
  providers; latest-to-finalized lag 0–1 block as measured (biased low by up to
  about one block).
- Signer, approve inclusion and executor pickup: **UNMEASURED** (no signer installed).

Why 660: it leaves 160 s from the decision snapshot to the swap's re-quote. The
measured parts plus a nominal estimate for the unmeasured ones (pickup within a
5 s cycle, about six RPC calls for the approve, signing, inclusion and finality)
come to roughly 30–35 s, so 160 s also absorbs one 20 s RPC timeout with
failover and a slow signer. 600 s would leave only 100 s; 720 s would let a
decision execute up to 12 minutes after its snapshot without a measured need.

Why 30: no step starts, and no swap is signed, unless 30 s remain before A and
before the route deadline. That is about 40 BSC blocks for sign, broadcast and
inclusion. The margin barely affects the usable window, because the deadline is
about 500 s after the re-quote.

Validity under A8: both integers, m < L, L ≥ `proposal_seconds` (15 in the
candidate profiles), L ≤ 3600. Not yet in any profile: the LIVE profile entry
needs this provenance, and both values are re-checked against measured
signer/approve timings in the signed rehearsal before the Oct 22 cut line. An
approve that ends after `A − 500 s` still leaves a refused swap and an allowance
for LD06 recovery; the window is chosen to make that rare, not impossible.

### LD04-P — L/m in the LIVE profile candidates (2026-10-20; prospective)

Puts Keegan's LD04-V01 values into the profile builder so the LIVE candidates can
carry them with per-value provenance. Keith owns the profiles (#120) and reviews.

**Pass criteria, written before code (Q1–Q5):**

- Q1. Without the new input, `build_live_profiles` output is byte-identical to the
  committed `quotes-complete-20261020` rehearsal/final candidates (YP-01 unaffected).
- Q2. With L = 660, m = 30, each candidate gains exactly `execution_authority_seconds`
  and `submission_margin_seconds`; every other key is unchanged. Provenance for both:
  `decision_id` = IDEA-049-C LD04-V01 and `data_hash` = SHA-256 of the committed LD02
  evidence file. `validate_live` and the schema validator accept them, and
  `execution_authority()` returns (660, 30).
- Q3. The builder and CLI refuse partial input (any of the four authority inputs
  missing), m ≥ L, L above 3600 or below `proposal_seconds`, non-integers, and a blank
  decision ID.
- Q4. New candidate files go to a new evidence directory with file and
  StrategyProfile.v1 hashes; no runtime config, manifest pin or readiness flag changes.
- Q5. Focused strategy tests and the full suite pass.

### LD04-P results (2026-10-20)

- **Q1 PASS.** Without the input, both candidates reproduce byte-for-byte from the
  committed DC-01 summary and `config/intelligence/red_flags.v1.json`.
- **Q2 PASS.** With L = 660, m = 30, each candidate gains exactly the two keys; every other
  key and its provenance are identical; `validate_live` passes and `execution_authority()`
  = (660, 30). Provenance: decision "IDEA-049-C LD04-V01 (Keegan, 2026-10-20)", data hash
  `ad43b634…c4ced4` (committed LD02 packet).
- **Q3 PASS.** Eight builder refusals (m = L, L > 3600, L < `proposal_seconds`, string L,
  m = 0, blank decision, bad hash, missing margin) and the CLI's all-or-nothing flags.
- **Q4 PASS.** Candidates in `docs/build/evidence/ld04-authority-profiles-20261020/`:
  rehearsal file `bb27cbf8…eb5b` / StrategyProfile.v1 `24858d24…10fa`; final file
  `054ca468…0bc7` / StrategyProfile.v1 `ac764577…50d2`. No runtime config, pin or flag changed.
- **Q5 PASS.** Strategy tests 183 passed / 80 subtests; full suite 2237 passed, 11 skipped, 3698 subtests.

Keith reviews and adopts (#120). These candidates still carry the DC-01 top-up fields,
which LD08's initial-gas-only alignment will change.

### LD04-P after PR207 (2026-10-20)

After PR207 (LD08 initial-only gas) merged into canonical (`91d4b0a`), canonical was merged into PR210. The
`profiles.py` conflict was resolved by keeping both features: `build_live_profiles(..., initial_gas_only=..., authority=...)`
and the CLI's `--initial-gas-only` with the four authority flags. A new test checks that the authority keys are the
only difference between initial-only candidates with and without L/m. The candidates were regenerated with
`--initial-gas-only` plus L/m: rehearsal file `07130775…a729` / StrategyProfile.v1 `58cb1be9…bdd4`; final file
`3393ce67…34fd` / StrategyProfile.v1 `70cb0d4f…d862`. No top-up keys; the action budget is still the FALLBACK-based
DC-01 pair (76,177,634,176,000 wei), pending LD09 measured gas. The earlier non-initial-only candidate hashes in
LD04-P are superseded.

### LD04-P-RV01 — Isaac review of PR210 (2026-10-21 SGT; prospective)

Isaac requests review, fixes as needed and merge. Review head `1a66bf9` against
canonical `ffe6210` (including merged PR207/211). Criteria: AP1 inspect complete
builder/CLI diff and validator/caller behavior; AP2 reproduce legacy DC01 and
initial-only+authority candidates byte-for-byte, verify decision/evidence hashes
and preserve missing-real-gas/S1/window/host limits; AP3 verify invalid/partial
L/m/provenance refusals and unchanged output without authority; AP4 verify S1,
initial-only gas and finite-authority planner/executor/signer integration with
focused tests, explain all skips and retain CI limits; AP5 merge only a pushed
exact reviewed head with no blocking defect and reconcile PR133/current records.
No live profile pin, runtime startup, host/provider, model, key or wallet action.

LD04-P-RV01 P2 finding at `1a66bf9`: the builder validates L/m through
`execution_authority()`, but public `validate_live()` does not. A valid generated
profile edited to L=1/3601/bool/string, m=0/L, or a missing authority field passes
that validator. Gate A/B, cap review and runtime startup call it directly; schema
planning checks later are not an equivalent early refusal. Prospective fix: use
the same existing authority contract in LIVE validation, preserving both-absent
legacy profiles and unchanged valid candidates. Regressions precede the fix.

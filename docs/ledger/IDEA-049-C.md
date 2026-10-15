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

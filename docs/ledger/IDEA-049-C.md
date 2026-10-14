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
| C-OPEN-008 / #23 | P0 shared secrecy dependency: nested backup/restore and archive-visible execution raw bytes | D primary with C, before combined review closure / Oct20. C broadcast-response leak fixed; this does not repair restricted signature separation in execution_records/backup. Verify SIGNED_DURABLE export traversal, archive grants, hash-compatible restore and quarantine. |
| C-OPEN-008 / #36 | P1 shared accounting dependency: canonical balance-to-ledger reconciliation | B with C/D before combined review closure / Oct20. Bind block/finality and BNB mark freshness; startup/periodic unsolicited-adjustment/restore-divergence cases; no fabricated fills. |
| C-OPEN-008 / #28 and final driver acceptance | Shared audit/delivery and final merged-tree coverage | D with C before combined review closure / Oct20. C supplies stable broadcast/receipt identities and restart evidence; D proves pre-final broadcast audit/deadline and full-tree integration. |

Tracker reconciliation on this base: #40 CLOSED and adapter/profile/merged composition regressions pass; #26 CLOSED and actual Service restart/immutable command reauthorization/claim/replay tests pass; #24 remains OPEN but C acquisition and merged cutoff/day-roll acceptance pass, with D final tree acceptance required. #27 and #30 remain OPEN, as do shared #23/#36. No tracker issue is closed by this task, and closing status alone is not used as evidence. The prior inventory's original trading-review ID collision remains D's shared-document reconciliation item, not hosting IDEA-046.

## Requested shared edits — resumed exact text for D

Replace the earlier C ledger suggestion with:
`| IDEA-049-C | Final review C: execution, signing and wallet boundaries | partial; offline fixes verified, deployment gates remain | 57 source requirements; merged-driver/PG14.24 verification; 17 additional regressions; local 1246 passed / 7 skipped / 1583 subtests; broadcast reflection and independent signer authority fixed; real unsigned five-name snapshot and API balance evidence; PR70; remaining owners/checks in record | 2026-10-15 | [ledger/IDEA-049-C.md](ledger/IDEA-049-C.md) |`

Replace the stale C/driver-unmerged paragraphs in INCOMPLETE_WORK with:
`IDEA-049-C / PR70 continues the frozen catalogue on merged base c1b6daf. PR20/21/41/66 integration and offline driver/profile/cutoff/command-restart coverage are verified. C fixes reflected signed bytes in broadcast artifacts, independently checks signer registered build/wallet/HALT before key use and registry release, and accepts blank optional credential fields. Local PG14.24 full suite: 1246 passed / 7 skipped / 1583 subtests. No whole GAP is closed: C-OPEN-003..008 retain deadline/decoder/native-proof/first-gas/three-day-weekend/host-wallet-rehearsal and D/B backup/audit/reconciliation owners and named checks. Actual unsigned snapshot and NO_NATIVE_ENTRY API balance evidence are recorded in IDEA-049-C; neither proves live readiness.`

Runbook/README readiness addition:
`Section C's merged offline tests and unsigned API sample do not enable live execution. Before Gate B, verify attributable router/proxy/nested decoding, canonical nonce/finality and transaction-bound native receipts, first-gas funding, accepted lifetimes, real signer host credential/clock/RDS checks, and backup/balance/audit acceptance. Before profile approval, require all five names' three-day/weekend retained cost evidence; before final activation, rehearse separate fresh-wallet namespaces and confirm its audit secret by Oct26. The signer must match its verified build to the authoritative registered run build and reject HALT, even for a previously queued request.`

D alone applies shared index/backlog/README/runbook edits. Completed portions must be removed from the live backlog once integrated and verified; keep remaining checks with their owners/deadlines. No SKILL F/K summary correction was found, so no shared summary edit is requested. Do not delete whole GAP lines while the host/live/cross-section evidence above remains outstanding.

## C-FND-008 — startup and exact manifest binding (prospective source amendment)

P1, C-REQ-043 and new C-REQ-058: the exact submitted proposal's Reproducibility/Versions says every component checks its hash against the active registered version before running, including the signer at startup. Build-id-only request comparisons do not satisfy startup refusal or a different manifest for the same build. Before claiming the final source pass is closed, add tests requiring refusal before key loading for missing/wrong registration and same-build/wrong manifest; require main to retain its verified manifest bytes and pass the computed hash into the service. Check that hash again at request authorization and under the signature-registry commit's run lock. Quarantine remains exit 3; matching registered release starts; unrelated key-file refusal tests keep all assertions but must seed proper registered-release metadata in their synthetic fixture. No additional signer role privilege is needed (runs is already readable). Publish failing tests before fixes.

## C-CI-001 — distinguish PR merge CI from exact branch evidence

Raw CI log inspection corrects C-RESULT-004's initial shorthand: pull_request run 38604152158 reports head c5cb145 but runtime/infrastructure checked out merge `f316575657eacaf0949603ba20a0e03bbec24ae7` into newer integration base `0820b0dd87219cb6b96f2ede34051129fab9f49c`; host-bundle checked out the head branch. Its Linux merged suite is **1273 passed, 4 skipped, 1 xfailed, 1615 subtests**, with separate systemd **3 passed/5 subtests**. Do not compare those merged counts as a pure C increment or claim exact-branch demo proof. External CI log SHA-256 `8caf389d0c40119f1323a29ad7605f54d4e09b5319296ba0735508b1beb149a4`.

The guarded runner at pushed `1efcda5` executes local system cases correctly (**112 passed, 70 subtests**, 32.937s; system log SHA-256 `79f9045c80be0e61f01bb60df1e01b032bb326cacf6cf5025f0b6f32efc42baa`) but accepts the PR API head as its Linux demo tree. The local system result is valid; its claimed matched-tree demo proof is withheld. Initial report SHA-256 `30fe4149d80c40a03e0b66b9225e2cdbdadf3904564dd13a5288180fc7ca8d5d`.

For D: P1 verification gap, before combined Oct20 closure. `tools/system_test.py` must inspect the actual CI checkout (PR merge vs branch) or require workflow_dispatch evidence when using API headSha. Proof is the committed run/checkout mismatch above, not an invented failure count. C cannot edit D's runner. C dispatched exact-branch run 38606430103 at 1efcda5; after the final source fix, dispatch and use a new exact-runtime run and repeat the guarded runner. No test is weakened to accept a different tree.

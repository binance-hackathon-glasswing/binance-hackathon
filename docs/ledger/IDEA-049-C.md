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

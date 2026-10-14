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

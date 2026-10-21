# LD08-GC01 / LD03-RP01 — gas coverage and router replay

Owner: Isaac. Base: canonical `f10d9ad`. Isaac requested priority2, then priority3;
the prior priority1 result remains in PR230. This document records criteria
before verification or new read-only network calls. Exact current profile,
holdings/configuration, strategy action count and host acceptance are not assumed.

## LD08-GC01 — priority2 criteria

1. Audit production per-transaction and aggregate-parent gas limits and current
   initial-only profile/reserve consumers. Sum integer child limits before
   multiplication; do not round the total instead of individual limits.
2. Compute a conservative stock-action envelope from CAP-02 execution ceilings:
   two ordinary transactions, or eight with all six optional zero-only cleanup
   steps. Keep the approved cleanup-disabled policy unchanged; the enabled
   calculation is a separate non-adopted scenario. Include no native top-up.
3. Generate new, explicitly non-adopted EQUAL_WEIGHT candidates with the existing
   production builder using the two-transaction bounded envelope and the retained
   independent sizing budget. Preserve all historical candidates and terminal
   gates; final PF-04 reconciliation remains Keith/Keegan's task from PR230.
   Validate and pin exact bytes. Confirm expected-cost sizing does not lower
   funded action/exit reserves or the independent fee ceiling.
4. Express seeding as reviewed non-terminal action count plus a separately
   counted terminal-exit reserve and rational margin. Do not silently equate
   historical N including exits with non-terminal N, or approve funding without
   Keith's counts/fresh reconciled holdings. Missing data remains explicit.
5. Run focused existing profile/initial-only/allowance/sequence tests; add tests
   only for any new arithmetic code. Record actual source and environment, never
   claim a full suite, live gas, seeding or installed alarm from offline results.

## LD03-RP01 — priority3 criteria

1. Load only the already named-reviewed LD03 policy with SHA-256
   `05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5`.
2. Use the production read/build Web3 client with only its API credentials and
   registered public wallet; never load a signing key or logging secret. Keep
   original observations and RPC URLs in a new private external directory.
3. If the retained approved read-side provider settings and credentials are
   available, collect fresh rehearsal-size BUY/SELL quotes for all five stocks,
   run the canonical decoder replay and every built-in tamper mutation, then
   run production preflight against live code/facet/dispatch/allowances. Only
   read-only RPC and quote endpoints are in scope. No AWS/SSM/session/host write,
   gas simulation override, approval submission, signing, broadcast or paid call.
4. Distinguish decode/tamper PASS from live preflight PASS, API refusal, stale
   quote and missing provider/credentials. Record chain56, observation times,
   requested candidate sizes/profile/policy hashes, and only sanitized public
   summaries. Do not infer router enforcement, RFQ executability, full-position
   coverage, source verification, production host binding or GateB acceptance.
5. Run focused decoder/preflight/privacy/read-only boundary tests; commit and
   push any new probe code before running. Missing real prerequisites are
   reported BLOCKED rather than supplied by synthetic fixtures.

Results will be recorded with the relevant ledger IDs and exact artifact hashes.

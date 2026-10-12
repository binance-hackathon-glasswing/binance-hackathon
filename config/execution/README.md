# Isaac's execution deployment configuration

Only API read/build access is enabled by the market-data tools. Run from a committed, pushed revision:

```
python -m larp.marketdata.logger --env-file .env --artifact-root data/execution-live --balance-only
python -m larp.marketdata.logger --env-file .env --artifact-root data/execution-live --sizes 40 --cycles 1
python -m larp.marketdata.logger --env-file .env --artifact-root data/execution-live --sizes 40 --cycles 0 --interval-seconds 3600
```

`BINANCE_API_KEY` / `BINANCE_SECRET_KEY` and aliases `BN_WEB3_API_KEY` / `BN_WEB3_API_SECRET` (also legacy `BN_WEB3_SECRET_KEY`) must agree. `AI_SEEDS_ADDRESS` is public; an explicit `--address` also works. No wallet key, ai-seeds secret or ai-seeds SDK is read. API authentication is separate from signing a transaction. Permission/compliance/rate failures stop continuous collection; no alternative route is tried.

Artifacts are immutable content-addressed JSON, mode 0600, in the chosen directory **outside Git tracking**. Response hashes cover original received bytes; artifact hashes cover the structured record after defensive credential redaction. Preserve the directory securely for recorded-response validation. `data/` is ignored by the repository. Prefer a dedicated external artifact root on deployed hosts.

Quoted round-trip loss includes fees already reflected in quote output. Gas is reported separately as unavailable before allowance/route capability proof; quoted `tx.gas` is never substituted for exact-payload estimation. Token/share basis, decoded route/expiry and ambiguous fee denominations do not receive invented values. Such observations are useful for measurement, but expose no executable planner quotes until verified integration supplies the missing facts.

Read a summary without loading credentials:

```
python -m larp.marketdata.logger --artifact-root data/execution-live --summary-only
```

Each logger cycle records its committed code revision and all five names’ raw hourly candles (limit 300, the measured API maximum). The kit does not establish whether its timestamp is bar-open or bar-close; open/close fields remain explicitly unverified until the session builder establishes that contract.

`larp.execution_live.store.ExecutionStore` uses the runtime PostgreSQL transaction boundary. Its schema is a proposed extension awaiting Keegan’s migration/role/backup integration; `install_test_schema` is restricted to offline runs. Live startup never installs tables. `ReceiptFacts` requires a persisted attempt-specific BNB price and durable finalization time. The runtime must atomically persist immutable final observations, release reservations and publish audit events before enabling signing.

PR14 review interfaces: `LiveGuards` reads current authorization facts, Web3 market status and chain nonce; missing facts never grant authority. Set `Gates.execution_version` separately from projection CAS `state_version`. The current PostgreSQL adapter derives execution authority from ownership epoch. Service and ReceiptFacts constructors require the controller's pinned `epoch` and `authority_version`; never read a newer lease on behalf of a stale process. HALT/revocation must quarantine or advance authority. The actual broadcaster must use `check_broadcast` plus fresh runtime release checks; generic epoch checks alone do not grant submission.

Command mapping requires `limits.per_trade_cap_units` in six-decimal money units, payload `cash_units`, and explicit receive decimals. BNB minimums convert from declared planner scale to chain scale. Markets provide origin and paired-quote cost provenance; unavailable costs are explicit. Supply `quote_limits` from the independent policy, not from a quote. `session_candles` requires timestamp convention/evidence and adjustment provenance; it does not invent OPEN semantics. Final receipt facts use the agreed `receipt` object and pinned round-completion attestation. Aborted work publishes an immutable NOT_SUBMITTED fact for the runtime's reservation reducer; it never invents a REVERT or gas charge.

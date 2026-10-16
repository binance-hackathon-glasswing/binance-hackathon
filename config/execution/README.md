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

## IDEA-049-C quote limits and native resource quotes

Supply `MarketPort(..., quote_limits=accepted_profile)` with the independent
profile's integer `slippage_bps`. Initial buy/sell quotes then use that cap;
an explicit override cannot widen it. Unconfigured read-only measurements retain
the previous 50bp sampling setting, which is not a production policy decision.

Command mapping accepts the same limit in `limits['slippage_bps']`, binding it
into immutable `Intent.max_slippage_bps`. `LiveVenue` uses this value for every
initial and post-approval re-quote, and refuses a minimum output permitting a
larger loss. The 50bp compatibility default exists for old fixtures/callers;
the eventual driver must explicitly provide the frozen profile value. That
wiring and the proposal-versus-router lifetime decision are separate owner work.

`NativeGasQuotePort(client, wallet, quote_limits=accepted_profile,
pay_units=accepted_profile['gas_top_up_cash_units'], receive_decimals=ledger_scale,
quote_verifier=verified_native_quote)` is an injectable quote producer for the
existing `gas_quotes(now_ms)` boundary. It only reads/builds USDT -> native BNB.
It retains retrieval completion time and never backdates to `now_ms`.

The injected verifier receives `(raw_response, request)` and must return the
response's `source_hash`, decoded `Payload` and `SwapEconomics`, `route_valid`,
`exact_gas_verified`, `fee_units` in six-decimal USDT units and `gas_bnb_units`
in the explicit `request['receive_decimals']` accounting scale. Nonzero fees also
require `fee_asset='USDT'` and `fee_decimals=6`. Gas must cover at least the decoded
swap allowance; the verifier must qualify the complete approve-plus-swap budget.
The producer independently checks route identity/economics, validity at retrieval,
minimum output, policy caps and exact conversion of native 18-decimal amounts.
It refuses incompatible scales rather than rounding down a minimum.

With no qualified verifier it returns an empty quote list. No verified production
router decoder is supplied by this change. Gate B now implements transaction-local
native receipt settlement as described below; provider qualification, first gas
and native quote verifier/driver acceptance remain blocked under #30/GAP-29/GAP-49.
Quote-only fixtures do not authorize production signing or claim those capabilities passed.

## GB-20261015: Gate B evidence and native settlement

From a committed, pushed checkout, capture public chain evidence without loading
`.env`, an API credential, a signer key or the ai-seeds secret:

```sh
python -m larp.execution_live.gate_b probe-chain \
  --rpc-url https://bsc-dataseed.bnbchain.org --source-id bnb-public-mainnet \
  --wallet PUBLIC_DEV_WALLET --router OBSERVED_CHAIN56_ROUTER \
  --artifact-root /absolute/external/gate-b-chain
python -m larp.execution_live.gate_b report --artifact-root /absolute/external/gate-b-reports
python -m larp.execution_live.gate_b report --inputs /absolute/external/gate-b-inputs.json \
  --artifact-root /absolute/external/gate-b-reports
```

Replace the public-address placeholders before use. The public endpoint is listed
in the [BNB endpoint documentation](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/json-rpc-endpoint/).
It is an optional observation provider, not an approved production dependency.
The probe verifies chain56 and the canonical identity of a finalized block before
and after reading its wallet balance and router code. Latest/pending nonces are
separate snapshots requiring fresh reconciliation before any signing. Zero BNB,
pending nonce differences or missing router code are explicit blockers. Presence
and SHA-256 of bytecode do not qualify ABI, proxy implementation or route safety.
The command saves each raw structured RPC observation and a hash-addressed
`GateBChainEvidence.v1` file externally. Exit 0 means observations collected with
no snapshot blocker; it grants no execution authority. Failure/blockers return 2.

The offline report accepts exactly this public input shape:

```json
{
  "schema": "GateBInputs.v1",
  "build_id": "FULL_40_HEX_COMMIT",
  "run_id": "DEV_RUN_ID",
  "wallet": "PUBLIC_DEV_WALLET",
  "chain_max_age_seconds": 300,
  "files": {
    "execution_config": {"path": "execution.json", "sha256": "RAW_FILE_SHA256"},
    "chain": {"path": "chain.json", "sha256": "RAW_FILE_SHA256"},
    "initial_state": {"path": "portfolio.json", "sha256": "RAW_FILE_SHA256"},
    "quote_costs": {"path": "quote-costs.json", "sha256": "RAW_FILE_SHA256"}
  }
}
```

Paths resolve relative to the input file; absolute paths work. All values above
are illustrative placeholders. The freshness budget is an explicit owner choice,
not an execution policy introduced by this tool. Each input is limited to 2 MiB;
hashes cover exact file bytes. Profile path/hash come from the pinned execution
configuration. Missing optional evidence remains BLOCKED. Do not supply secret
files; this tool reads only the public JSON paths supplied and the pinned profile,
and never resolves DSN/key credential references or starts a service.

`GateBReport.v1` inventories DR01–16,18–20, including Gate A dependencies.
`VALIDATED` on DR04/09 describes configuration/profile checks only. The existing
LIVE profile validator is used; a shape-valid synthetic profile cannot establish
real measurement attribution. Initial portfolio checks use the actual integration
projection/ledger adapters, run/wallet identity and exact native funding units;
they do not prove all balances or complete accounting acceptance. `QuoteSummary.v1`
from the logger is not the strategy's `QuoteCostSummary.v1`: no fees, gas or TTLs
are invented to bridge them. Raw multi-day/weekend coverage needs separate owner
review. The report always remains BLOCKED, `signing_enabled=false`, exit 2 until
the external acceptance workflow is implemented and reviewed. It has no override
or acceptance/activation command. No report is a substitute for the item-by-item
IDEA-042 gate review, merged-branch CI, host drills or logged signed dev rehearsal.

Native settlement uses a transaction-specific Geth `prestateTracer` diff,
bracketed by matching canonical/finalized receipt evidence. Provider support and
semantics must be independently qualified. Execution config `native_trace` is
boolean and defaults to false. Enabling it permits only a fixed read-only trace
request; it does not qualify the provider or lift the Executor/router gates.
With `native_trace` false or absent, the service refuses every `GAS_TOP_UP`
command before signing (`map_command`, IDEA-061): a top-up fill can settle only
through the native trace, so it is never started without one.
The trace is trusted-provider evidence, not a cryptographic state proof. Its
`trace_sha256` hashes the canonical encoded trace result; the enclosing raw RPC
observation has its own artifact hash. Whole-block balance differences cannot
be used. Native output equals transaction-local balance change plus actual gas
paid. Exact USDT debit and minimum output are enforced before I4 publication.
Approval/revert receipts remain gas-only.

The execution service reads BNB valuation and accounting decimals from the
durable plan. Use 18-decimal BNB ledgers for Gate B: gas and native output must be
exactly representable; other scales fail on any remainder, without rounding.
Durably stored observations retain their first bytes across retries. The existing
native quote verifier, router qualification, first BNB, accepted profile, full
funding reconciliation and host/audit acceptance still need their named owners.
See [IDEA-039 GB-20261015](../../docs/ledger/IDEA-039.md#gb-20261015--gate-b-implementation-prospective)
for tests, evidence and remaining acceptance.

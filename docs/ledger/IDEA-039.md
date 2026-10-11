# IDEA-039 — Isaac's live market and execution deployment track

- Owner: Isaac; implementation Codex; reviewer Keegan.
- Started: 2026-10-11. Base: PR #12 `e4ebff6` (contains the deployment brief and PR #7 fixes); PR #12 is still open, so this branch starts at its published head rather than the older foundation without prompts.
- Branch: `codex/deploy-execution`. Scope: prompt 06, I1–I4/I7, DR-01–06 and DR-17; no signing activation, paid service activation, organiser messages or main merge.

## Prospective acceptance

1. Signed Web3 transport: fixed origin and endpoint allowlist; exact GET/POST authentication bytes; redirects refused; bounded responses; explicit auth/compliance/rate/business/transport failures; conflicting credential aliases rejected; credentials never enter artifacts or errors.
2. Immutable observations and quote logger: hash-addressed artifacts outside Git; availability at response completion; exact integer decimal conversions; API-supplied token decimals; original status and candle timestamps retained; all five names measured at configured sizes; failed gas estimates remain unavailable, never invented. Real responses remain outside Git; secret-free synthetic tests plus opt-in recorded-response tests.
3. Market output calls the real `market_view` and quote/planner validators. Unknown router ABI, fee or positive gas proof prevents executable quotes; measurement can continue without granting authority. No fake depth, basis verification, receipt, finality or expiry.
4. Chain adapter: configured chain-56 HTTPS JSON-RPC, chain identity, canonical/pending nonce, transaction/receipt/canonical block/finalized head binding, reorg/absent evidence stays uncertain. Endpoint/provider must be supplied and manifested before live use.
5. Venue/signing components: approval calldata bound to exact spender/input; fresh re-quote and exact-payload gas estimate; verified decoder required; transaction sender/hash/nonce/bytes verified; durable immutable signer registry plus current authorization checks at release; no replacement or automatic nonce increment. No wallet key on development tools.
6. Runtime command mapping and observations: six-decimal planner USDT converts exactly to API asset units; identity/reservation/expiry and token pair checked; attempted broadcasts change execution/audit state only; final receipt facts carry actual transfers/gas and pass accounting validation. Production registry, command fencing and settlement schemas require Keegan's integration.
7. Full existing W04/W08 tests and new module tests pass; Linux CI passes. Commit and push changed decision/trade/logging code before running it. Live wallet balance/read-only probe uses only committed code and stores hashed evidence outside Git. Real signing tests remain NOT RUN until integrated release/logging/BNB/router/nonce/finality gates pass.
8. DR-01 multi-day quote logging and signed rehearsal are time-dependent acceptance, not implied by unit tests; record actual coverage and outstanding owners.

## Integration requests and current dependencies

- Keegan: integrate this branch after PR #12, add/update the IDEA-039 index row and relevant GAP entries; preserve all partially complete backlog items.
- Keegan: supply the production atomic execution CAS/store and isolated signed-byte registry boundary, including current fencing checks; publish command/settlement I3/I4 schemas. This track will publish mapping/contracts in this record, without changing shared storage/migrations.
- Keith: publish candle-session consumer, live cost/gas/profile settings and GAS_TOP_UP command schema (I2/I7); no guessed calibration.
- Team/Keegan: supply and manifest the chain RPC endpoint and signer-host provisioning. Verified router ABI and encoded expiry remain W08 blockers; unsigned API JSON is insufficient proof.
- Multi-owner interface agreement remains required by the brief before production integration. Existing consumer schemas are used directly where available; proposed extensions stay unactivated pending owner agreement.

## Results

NOT RUN at preregistration. Implementation and test evidence follow in dated entries.

## 2026-10-12 — first published increment and interface proposal

- `2ff74d8`: read-only Web3 transport, artifact storage, market metadata/status/raw candles, exact-size quote measurements and hourly logger. 77 offline tests pass (W04/W08/shared contract tests and 4 new market tests).
- Development-wallet API balance check at `2ff74d8`: artifact `c88e759e44800843ba503a1f1b631eae8bd84576bca67c5f36bf4bc894b6636c`, no native BNB entry. This is API/indexer evidence only, not canonical balance proof. DR-06 first-gas remains blocked; no signing/funding attempted.
- First live 40-USDT five-name cycle: artifact `7d6ee118d1fd26c8af2386aede40768bf80981ade4cc86b50a3431e804b333b1`, completed 2026-10-11 15:56:51 UTC. All five buy/sell measurements returned. Sequential quoted round-trip bps: NVDAB 1.6805, GOOGLB -3.7185, SKHYB -1.0974, TSLAB 5.6398, MSFTB 21.1993. Negative observations may reflect price movement between requests, not arbitrage/negative spreads. One sample is not a median/calibration or profitability result. Gas not established; unknown route/fee/expiry prevents executable quotes.
- Public BscScan router source retrieval is still unavailable; no attributable ABI established. `UnverifiedRouter` deliberately blocks route decode and approval/signing. No fabricated alternative decoder.
- Chain proof design uses the economic `finalized` tag from BNB Chain's primary API documentation, not a confirmation-count guess: https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/bsc-api-list/ (checked 2026-10-12). Read-only RPC identity/nonce/receipt evidence can be tested independently; team RPC selection remains pending.

**I3/I7 proposal for Keith and Keegan (not production agreement):** Runtime command envelope carries `command_id`, `round_id`, `decision_id`, `expires_ms`, `kind=EXECUTION_REQUEST`; payload must match the IDs/expiry and use existing EXACT_IN asset/min-receive fields. BUY USDT quantities convert planner 10^6 units to chain 10^18; SELL tokens retain API decimals and USDT minimum receive converts 10^6 to 10^18. Intent `kind` defaults BSTOCK_TRADE; only explicit GAS_TOP_UP permits USDT→native BNB. Router and gas ceilings come from externally verified configuration/authorization, never quote defaults. No runtime/strategy shared schema is changed here.

**Signer registry proposal for Keegan:** `lookup(attempt_id,payload_hash)`, `check_authority(epoch,state_version)`, `put_if_absent(attempt_id,payload_hash,signed,epoch,state_version)`; latter must atomically fence/check authority and commit immutable restricted bytes before release. Authorization callback returns actual intent/step/current gates/trusted clock/verified decoder for independent `validate_payload`. Production DB/grants/CAS implementation remains Keegan's path; no SQLite/file fallback. Existing W04 Executor rejects live bundles until capability and runtime integration are proved.

Second increment acceptance adds synthetic nonce/finality/reorg tests, exact signed HTTP bytes/reflection/redirect tests, explicit narrow GAS_TOP_UP validation, and EVM signer tests with freshly generated in-memory fixture keys (no real wallet). Chain provider is not activated. The market logger now records exact-payload simulation failures explicitly instead of substituting quoted gas. Local eth-account exists, but the runtime CI lock does not include it; request Keegan add the already project-pinned signer dependency and fresh lock verification. Cryptographic tests skip visibly in environments without that dependency.

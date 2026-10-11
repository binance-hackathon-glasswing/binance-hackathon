# IDEA-039 — Isaac: live market and execution integration

- Owner Isaac; reviewer Keegan. Prompt `docs/build/06-execution-live.prompt.txt` and IDEA-038 govern scope.
- Baseline: foundation `bd3f69a`, merged into `codex/deploy-execution` by `4d1fde2`. PR12 is merged. Earlier implementation commits were reverted; they provide reusable source, not current acceptance evidence.
- Status: implementation in progress. No live signing, broadcast or official round logging is enabled by this record.

## Preregistered acceptance

Commit and push this record and code before execution. Record PASS / FAIL / NOT RUN / INCONCLUSIVE and commit SHA for each run.

1. Existing foundation, W04 and W08 suites remain passing; network-free component fixtures exercise malformed quantities, credential conflicts, immutable artifacts and exact API signing.
2. I1/I2: recorded real responses, hashed outside Git, pass the actual consumer `market_view`; executable quote evidence must pass `_quote_at_cap`. Missing router decode, expiry, fee or exact gas proof exposes measurements only. Never invent these fields or backdate observations. USDT planner units (6 decimals) map exactly to BSC units (18 decimals).
3. Quote collection: five names, about 40 USDT, hourly or faster; retain availability, impact, round-trip quoted cost, latency, errors and exact simulation failures. Stop on auth/compliance/rate-limit failures. Summary by Oct 19; three days including a weekend remains a time-dependent requirement.
4. Signer: isolated-host configuration, one secret source, matching wallet; immutable signed-byte registry and current fencing/authorization before release. Mutation and restart tests prove exact transaction bytes and hash/sender binding with ephemeral test keys only.
5. Nonce/finality: chain 56, latest/pending counts, transaction/receipt identity, canonical blocks and verified finalized head. Missing or inconsistent evidence keeps the barrier. Replacement disabled.
6. I3/I4: consume commands via `PostgresStore.command`; enforce identity, expiry and exact input/receive scales. Broadcast facts never reach accounting. Final receipt facts contain actual transfer/gas evidence and pass `advance_accounting`; repeated observations are idempotent.
7. Production execution and signer-registry storage require Keegan's fenced atomic PostgreSQL boundary. Crash tests before sign, after sign, after broadcast and after receipt must pass in CI before live activation; SQLite is not production evidence.
8. Check BNB read-only first. A missing/zero balance blocks transactions. USDT→native BNB is allowed only for explicit GAS_TOP_UP intents; final-wallet run identity, nonce and audit directories stay separate.
9. One minimum-size approve/swap with durable decision and official round logs is NOT RUN until router/chain, first gas, production storage, manifest and audit gates pass.

## I3 mapping and integration requests

`command_id = payload.intent_id`; command/payload `decision_id` and `expires_ms` must agree. External run, wallet and registered version come from the trusted store/run configuration. Reservation identity is the intent ID. BUY pays USDT and converts planner `pay_units × 10^12`; SELL pays token units unchanged and converts USDT minimum receive `× 10^12`. `receive_decimals` must match the consumer convention. Router and gas caps are current risk-authorized inputs, never API defaults. Explicit GAS_TOP_UP buys native BNB only.

Keegan owns shared docs/locks/index/backlog/migrations: retain the existing IDEA-039 index reservation; record requested PostgreSQL execution CAS/event storage, restricted immutable signer registry and fenced release/settlement integration. Coordinate I1/I2/I7 with Keith; no owner agreement is assumed from local fixtures. EXP-005 verdict updates are requested through the shared-document owner; no capability is promoted by synthetic tests.

## Open dependencies

- Isaac: verified router ABI/implementation, nested RFQ expiry/economics and decoder; EXP-005 currently inconclusive.
- Team/Keegan: permitted RPC endpoint and manifest entry, signer host runtime secrets, first BNB, production storage/release/audit gates.
- Keith: session-builder I2 validator, live profile/impact/gas values, gas-top-up accounting contract.
- Isaac: start quote measurements and record summaries and coverage; an initial cycle cannot satisfy multi-day acceptance.

## 2026-10-12 SGT implementation and evidence

Implementation `fc0b3ef` was pushed before all runs. [Draft PR14](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/14) targets `codex/engine-foundation`; no merge to main or live activation.

- PASS: targeted 98 tests, including foundation/W04/W08, actual market/planner validators on synthetic proof fixtures and real recorded Binance responses, receipt facts through actual accounting, and real EVM cryptography using ephemeral test keys.
- PASS: full local pytest in a temporary environment using the CI lock: 534 tests, 764 subtests; 90 skips because disposable PostgreSQL and Linux isolation are unavailable locally. Earlier full runs in base/Conda Python failed due missing numpy/AWS test dependencies; no code defect was inferred from those environment failures.
- PASS: [CI on fc0b3ef](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38156124100), all three checks. PostgreSQL-backed run: 621 tests, 780 subtests, 3 skips (external recorded responses and signer dependency). The four new PostgreSQL tests cover pre-sign/post-sign restart, post-broadcast/post-receipt restart, wallet barrier/stale CAS, and registry restart/identity. These are restart simulations over real PostgreSQL and fake venue/signatures; they do not establish power-loss, multi-host or actual chain recovery.
- INCONCLUSIVE: balance artifact `2b75d769b93396aeb8a091dadf65d35d793259f87dfbf7d28af51ee8d5abe683` in ignored `data/execution-live/`: no native BNB entry returned. Per the captured kit zero balances are omitted. No canonical chain balance was collected; first gas remains unresolved and transactions are blocked.
- PASS for read-only collection, not readiness: 40-USDT cycle `ef42ceccbf9963d45f71169adaa871aab1103062e880052e3b5bc368aaa47749`, 2026-10-11 16:33:30.512–16:33:47.993 UTC. All five token/underlying states open; every exact swap gas simulation unavailable. Raw response bytes are retained in private hash-addressed artifacts unless credentials are reflected, in which case only redacted parsed data and the response hash are stored.

| Name | Sequential quoted round-trip bp | Buy impact bp | Sell impact bp |
|---|---:|---:|---:|
| NVDAB | 2.0609 | 0.1763 | 0 |
| GOOGLB | 8.1549 | 0.0408 | 0.0408 |
| SKHYB | -3.3239 | 0.1697 | 0 |
| TSLAB | 7.7633 | 0.0579 | 0.0507 |
| MSFTB | 22.8609 | 0 | 0 |

One pair per name is not a median, spread estimate or opportunity/profit signal: the prices can move between the two calls. Gas is separate and unavailable; these numbers do not satisfy B4's total-cost criterion.

Router search for the exact observed address did not produce a verified ABI. Official [BNB RPC documentation](https://docs.bnbchain.org/bnb-smart-chain/developers/json_rpc/bsc-api-list/) and [BNB node RPC reference](https://github.com/bnb-chain/bsc/blob/master/rpc/json-rpc-api.md) describe finality methods; provider availability and this wallet's nonce/finality evidence remain NOT RUN pending service configuration. Same-nonce replacement stays disabled.

## Integration handoff details and remaining acceptance

- PostgreSQL extension: `larp/execution_live/store.py:SCHEMA` proposes `execution_records` (restricted state/CAS), `execution_journal` (public events/hash chain) and `execution_signatures` (restricted immutable attempt bytes). Atomic commits lock W02's run and compare epoch/state version. The wallet barrier is across economic intents; production startup does not install tables. Keegan must adopt migrations, role grants, backup/restore coverage and atomic command/reservation/observation/outbox wiring. Local tests cannot count as agreement from Keegan.
- Signer requires current authorization and checks fencing before returning persisted bytes. Keegan must add eth-account and its pinned transitives to the deployment/CI signer dependency set; existing full-project requirements already pin eth-account. Local signer tests pass, CI presently skips them.
- I4 broadcasts are stable audit-only events. `ReceiptFacts` uses a durable W04 finalization timestamp and a persisted attempt-specific BNB valuation; the runtime must persist/publicize identical bytes on retry before advancing. Settlement reads actual ERC20 Transfer logs and receipt gas, rejects quantities unrepresentable in the accounting money scale, and includes all USDT transfers in net cash without double-booking an assumed quote fee.
- Native BNB top-up intent validation exists, but actual native receipt/balance-delta settlement and Keith's gas accounting are still needed. No gas conversion is run while first BNB is unresolved.
- I2 supplies raw candle rows and UTC reported timestamps with hashes. Open/close semantics remain explicitly unverified; Keith must establish those semantics in the real session-builder validator. Null open/close values are flagged unresolved fields, not assumed data.
- Live Executor bundles remain rejected until route/expiry and production release gates are evidenced. Development approve/swap acceptance remains NOT RUN. No real wallet transaction signing, broadcasts, official ai-seeds logs, paid services or organiser messages occurred.
- Logger long-running operation and multi-day/weekend summary remain pending; subsequent dated results below record them. The default balance/one-cycle CLI does not start a background logger.

### Follow-up preregistration: actual process death

Additional PostgreSQL acceptance: child processes exit immediately before signing, after restricted signer-registry persistence but before W04 persistence, after a possible fake broadcast but before response persistence, and after receipt reading but before final-state persistence. Restart must recover the same signature/attempt, retain possible-send state, never retransmit, and finalize only from subsequent positive evidence. Both approve and swap paths are covered. The child only uses the disposable CI database and unbroadcastable fake signatures. This strengthens restart evidence; it is not a power-loss or chain test. Commit/push before running.

### Collector operation / follow-up verification

The read-only hourly collector was launched locally on pushed `cbf4440`, PID 96699, at about 2026-10-11 16:45 UTC. Its private PID/log files are ignored under `data/execution-live/`; it has no signer or ai-seeds client. This laptop must stay awake and connected for coverage; Keegan must move/supervise collection on the deployment host for reliable multi-day evidence. Multi-day/weekend acceptance remains open.

Local `cbf4440` full pytest: PASS, 538 tests, 767 subtests, 90 skips; raw recorded-response validation and ephemeral cryptographic tests enabled. CI/result hashes for the latest revision are recorded after completion.

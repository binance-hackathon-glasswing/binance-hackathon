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

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

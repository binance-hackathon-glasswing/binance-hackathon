# IDEA-088 — Quote verifier for the UNTRUSTED router path (SJ-11-QV01)

- Date / author: 2026-10-24 / Claude Code (session started from the SJ-11 coordination session)
- Status: open (pre-registered below; branch `claude/sj11-qv01-quote-verifier`, base `codex/system-testing-20261012`
  at `9dc5edab`, RC6)
- Owners: Isaac (GAP-29 signing and router decisions), Keegan (runtime review). Keith reviews the planner gas split
  (QV6) because it touches how the S1 profile's gas values are used.
- Links: IDEA-049-C SJ-11-QV01 (finding: run 3 on RC6 decided S1 targets 19 % ×5 but formed 0 intents),
  IDEA-050 "Still open" item 1 (quote verifier capability gate), IDEA-070 B02-U / LD03 (UNTRUSTED router policy
  `05759e90…`, DEV-23), IDEA-070 KG-DEC-01-H P3 (BUY swap gas estimate refused before approval), IDEA-061 LD09-B
  (decoupled gas action and sizing budgets), CAP-02, GAP-29, GAP-50.

## What and why

`larp/runtime/service.py` builds `MarketPort` without a `quote_verifier`. `MarketPort.observe` then always returns
`quotes=[]` with `quote_status='CAPABILITY_PROOF_REQUIRED'`, and `RoundDriver._quotes` clears the result and returns
without a child round or any journaled reason. No BUY or SELL intent can be formed on the signed path, for S1 or equal
weight. This entry adds the verifier `MarketPort._executable_quote` asks for, wires it, and journals every dropped
quote.

## Design (recorded before implementation)

`larp/marketdata/quote_verifier.py` `UntrustedQuoteVerifier(decoder, profile, wallet, bnb_decimals)`, called by
`MarketPort.observe` as `verifier(raw, request, observation)`. It returns the proof or raises `Unavailable`; it never
returns a partial proof.

1. **Response bytes.** `source_hash` is the response's own `artifact_sha256` (`Web3Client` hashes the received bytes).
   `executionMode == 'SWAP'`, `rfq is None`, `vendorName == 'LiquidMesh'` (as `LiveVenue.quote`), `tx.from`, when
   present, is the wallet, and `tx.slippagePercent`, when present, equals the requested limit.
2. **Decoded economics.** The payload is `Payload(56, wallet, tx.to, tx.value, 0, tx.gas, tx.gasPrice, tx.data)`
   (the nonce is assigned by execution). `SwapEconomics` comes from the signer's own `UntrustedRouterDecoder.decode`
   (`larp/execution_live/untrusted_router.py`, loaded with `load_policy(path, sha256)`), not a second decoder. The
   port then binds pay/receive token, amount, minimum output (`tx.minReceiveAmount`), native value 0 and the payload
   to the quote, as today.
3. **Recipient.** The UNTRUSTED layout does not carry the recipient, so the decoder returns `None`. The port accepts
   `None` only when its verifier's decoder has `mode == 'untrusted'` (the same rule as `validate_payload` and
   `SigningPolicy.check`); every other proof still needs `recipient == wallet`.
4. **Live route state.** Before any proof, the decoder's own `preflight(intent, payload, approved=False)` runs on the
   runtime's read RPC (the balance providers): at one numeric block the router dispatches the swap selector to the
   pinned facet, both code hashes equal the pinned ones, and no other pinned token has an allowance to the router.
   `route_valid` is true only after this passes. This is the same check the execution service runs before its swap.
5. **Gas.** A swap's gas cannot be estimated before its approve: `/pre-transaction/gas-limit` refuses an unapproved
   BUY or SELL (KG-DEC-01-H P3), and every allowance is zero between trades by policy. So an exact estimate is not
   available when the plan is made. The execution service already enforces the bound that matters: every payload's
   `gas × gas_price` and their sum stay within the configured `gas_budget`, and `RunAuthorization.resources_reserved`
   refuses an intent whose BNB reservation is below that budget. CAP-02's `INITIAL_PROFILE_ACTION_BUDGET` check
   requires `gas_budget ≤ gas_action_budget_units`. The proof therefore sets:
   - `gas_bnb_units` = the profile's `gas_action_budget_units` at the ledger's BNB scale (rounded up): the reservation,
     enough for every gas cost execution can authorize for the intent;
   - `expected_gas_bnb_units` = the profile's `gas_sizing_budget_units` (LD09-B: the same gas at the expected price,
     the value the minimum trade is sized on), at most `gas_bnb_units`;
   - `gas_basis = 'EXECUTION_FEE_AUTHORITY'` instead of `exact_gas_verified`. The port accepts either an exact-gas
     proof (`exact_gas_verified is True`, unchanged) or this basis with `0 < expected ≤ gas`. Nothing is labelled
     exact that is not.
   The verifier refuses a profile that is not initial-gas-only or lacks either budget, and a profile whose
   `quote_cost_summary.bnb_decimals` differs from the ledger's.
6. **Fee.** `fee_units = 0` with `fee_basis = 'ROUTE_FEES_IN_QUOTED_AMOUNTS'`, as the profile's `fee_bps = 0` assumes
   (#119). A response with a non-null, non-zero `feeAmount` is refused, because its denomination is unproved.
7. **Slippage and deadline.** `slippage_bps` = the profile limit, which `MarketPort.quote` requested.
   `tx.minReceiveAmount` must be at least the quoted output × (10000 − slippage) / 10000. The inner deadline must be
   after the response's `available_at`; it becomes `expires_at`. `_quote_at_cap` then runs as today.
8. **Planner (QV6).** Today one field, `gas_bnb_units`, is both the BNB reservation and the gas in the entry-cost
   check. At the action budget (run-3 profile: 3.84e14 wei ≈ 0.277 USDT) a 19 USDT entry fails the 50 bp
   `ENTRY_COST_CAP` (≈ 0.095 USDT) and the 0.1 USDT cost reserve. At an expected fee, execution refuses the
   reservation. So `_quote_at_cap` accepts an optional `expected_gas_bnb_units` (an integer, `0 < e ≤ gas`), and
   `plan` uses it only for the gas value in `cost`. The reservation delta, `INSUFFICIENT_GAS`, the free-BNB floor and
   the exit gas reserve keep `gas_bnb_units`. A quote without the field behaves exactly as before.
9. **Wiring.** The driver block gains the optional pair `untrusted_router_policy_file` /
   `untrusted_router_policy_sha256` (both or neither, as the execution config). With the pair, `build_driver` loads
   the policy by its hash, binds it to the balance RPC providers (tried in order) and passes the verifier to
   `MarketPort`. The pair needs `balance_rpc_providers` and an initial-gas-only profile. Without the pair nothing
   changes, except QV8.
10. **Journaled drop (QV8).** When a quote follow-up returns no executable quote, `_quotes` commits one
    `INCIDENT` (`type = 'QUOTE_NOT_EXECUTABLE'`) with the round ID and, per request, symbol, side, pay units and the
    reason: the port's `quote_status` or the refusal's class and message (at most 200 characters). `INCIDENT` is
    already a recorded fact for replay and is wallet-neutral for the balance check's quiet-period proof. A commit
    conflict is reported in the summary and not raised.

Not done here: installing, signing, AWS, the wallet; any network call in tests; a release, run or REHEARSAL window
decision.

## Pass criteria (written before any test is run)

Offline only. Fixtures: the 15 recorded quotes in `docs/build/evidence/quotes-interim-20261018/selected-raw`,
`tests/execution/test_untrusted_router.py`'s `policy()` and `FakeRpc`, and the S1 REHEARSAL profile
`docs/build/evidence/s1-rehearsal-profile-20261023/rehearsal-s1-deterministic.json`.

- **QV1 executable:** a recorded BUY quote through `MarketPort.observe` with the verifier gives `quote_status =
  VERIFIED_EXECUTABLE` and one quote with `gas_bnb_units` = action budget, `expected_gas_bnb_units` = sizing
  budget, `fee_units` 0, `slippage_bps` = profile, `expires_at` = inner deadline, `route_valid` true; `_quote_at_cap`
  accepts it. The same holds for a recorded SELL quote, if one exists among the 15. Red on base (no module).
- **QV2 bytes and economics:** every `untrusted_router.mutations` copy of `tx.data`, another router, a non-zero
  `tx.value`, `executionMode` ≠ SWAP, a non-null `rfq`, another vendor, `tx.from` ≠ wallet, a lower or mismatched
  `minReceiveAmount`, a different `tx.slippagePercent`, a non-zero `feeAmount`, a deadline at or before
  `available_at`, and changed response bytes each give `Unavailable` and no quote.
- **QV3 live state:** another facet, another router or facet code hash, a non-zero allowance on another pinned token,
  and an unavailable RPC each give `Unavailable`. The reads use one numeric block.
- **QV4 gas:** the reservation equals the action budget at the ledger's scale; a non-initial-only profile, a missing
  budget or a BNB scale mismatch refuses construction (`ContractError`). A proof with `expected_gas_bnb_units` above
  `gas_bnb_units`, zero or absent under `EXECUTION_FEE_AUTHORITY` gives `Unavailable`.
- **QV5 recipient:** a proof with `recipient = None` passes only through a verifier whose decoder mode is
  `untrusted`. The existing `tests/marketdata/test_quote_contract.py` cases pass unchanged.
- **QV6 planner:** with the run-3 S1 profile's budgets, a quote whose reserved gas fails `ENTRY_COST_CAP` forms a BUY
  intent when the expected gas fits; its reservation delta's `bnb_units` is the reserved gas. An expected value above
  the reservation rejects the quote. A quote without the field gives the same plan as before (existing planner
  tests unchanged). Red on base.
- **QV7 wiring:** `build_driver` with the policy pair builds a `MarketPort` whose verifier holds the pinned decoder
  bound to the balance providers; a hash mismatch, one key of the pair, or the pair without balance providers is a
  `ContractError`. Without the pair the port has no verifier. Red on base.
- **QV8 journal:** a non-executable follow-up commits exactly one `INCIDENT` `QUOTE_NOT_EXECUTABLE` naming the round,
  the request and its reason; an executable one commits none; replay of the journal reproduces it. Red on base.
- **QV9 suite:** the full suite on Python 3.12 and disposable PostgreSQL 14.24 has no failure that the base
  `9dc5edab` does not have. Exact counts and skips recorded.

A criterion that fails stays failed in the results; the design is changed only by a new dated amendment here.

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

## Results (2026-10-24, Claude Code; offline only)

Commits on `claude/sj11-qv01-quote-verifier`: pre-registration `a13ad897`; tests `fbd4fa86` (red on base: the QV1–QV5 module did not import, and the QV6–QV8
selection reported 13 failed / 5 passed, the passes being the unchanged-behaviour checks); implementation in the following commit. 20 new tests: `tests/marketdata/test_untrusted_quote_verifier.py`
(11), `tests/risk/test_expected_gas.py` (4), `tests/runtime/test_driver.py` (2) and
`tests/runtime/test_round_driver_service.py` (3).

| ID | Result | Evidence |
|---|---|---|
| QV1 | PASS | Recorded BUY (TSLAB, `0626c8a8…`) and SELL (MSFTB, `1a422811…`) quotes become `VERIFIED_EXECUTABLE`: reservation 384,000,000,000,000 wei (action budget), expected 80,004,608,000,000 wei (sizing budget), fee 0, slippage 50 bp, `expires_at` = inner deadline; `_quote_at_cap` accepts both. The fixture limits are 50 bp / 50 USDT because the recorded quotes are 40 USDT at 0.5 %; the gas budgets and BNB scale are the run-3 profile's. |
| QV2 | PASS | All 15 calldata mutations, other router, native value, other wallet, minimum ±1, slippage echo, RFQ, execution mode, vendor, explicit fee, expired deadline and a proof bound to other bytes are refused. Each refusal was checked to come from the intended check (decoder, preflight, verifier or port binding), not an incidental one. |
| QV3 | PASS | Other facet, router code, facet code, a dirty other-token allowance and an unavailable RPC are refused; every read after `eth_getBlockByNumber` names block `0x10`. |
| QV4 | PASS | Top-up profile, missing sizing or action budget, sizing above action, ledger BNB scale 9 and an unbound decoder refuse construction; a fee-authority proof with no, zero or above-reservation expected gas, or an unknown basis, is refused. |
| QV5 | PASS | `recipient = None` passes only through a verifier whose decoder mode is `untrusted`; a verifier with no decoder or a `pinned` one is refused. `tests/marketdata/test_quote_contract.py` unchanged and passing. |
| QV6 | PASS | At the run-3 budgets valued at its BNB price (reservation ≈ 0.277 USDT, expected ≈ 0.058 USDT) the reservation alone gives `ENTRY_COST_CAP`; with the expected gas the BUY intent forms and both the intent's `gas_bnb_units` and the reservation delta's `bnb_units` are the full reservation. Expected above the reservation, 0, negative or a string rejects the quote (`QUOTE_ROUTE_OR_SLIPPAGE`); expected = reservation gives the same plan as no field. |
| QV7 | PASS | With the pair, the port's verifier holds the pinned decoder (`mode` untrusted, `policy_sha256` = the file's) bound to a `ProviderRpc` over both balance providers in order; hash mismatch, file only, hash only, no balance providers, and a top-up profile each refuse the start; without the pair the port has no verifier. |
| QV8 | PASS | A non-executable follow-up commits one `INCIDENT` `QUOTE_NOT_EXECUTABLE` with round ID, symbol, side, pay units and reason `CAPABILITY_PROOF_REQUIRED`; a refusal journals `Unavailable: <message>`; any other exception is journaled by class name only; an executable follow-up journals none; replay of the journal reaches the same verified head. |
| QV9 | PASS | Python 3.12.14, Docker `postgres:14.24` on loopback, credential-free environment (`env -i`). Base `9dc5edab`: **2555 passed, 10 skipped, 0 failed**, 3931 subtests, 399 s (log SHA-256 `8f8ff8f9fcf1a8cf…`). This branch: **2575 passed, 10 skipped, 0 failed**, 3980 subtests, 396 s (log `be354d74349fa867…`), i.e. +20 tests. The skips are the same 10 environmental ones: 1 optional private source fixture, 1 opt-in recorded-market artifact, 5 opt-in systemd and 3 Linux bubblewrap. No hosted CI was run. |

### What this does and does not establish

- The runtime can now form BUY and SELL intents on the UNTRUSTED path offline, from real recorded quote bytes, with the
  signer's own decoder and preflight. Nothing was installed, signed or sent; no AWS, wallet or network call was made.
- **Finding (QV6, for Keith and Isaac):** before this change, no entry at the run-3 size could pass both the planner
  and execution. Execution requires a reservation of at least `gas_budget` (3.84e14 wei); the planner priced that
  same figure into the 50 bp entry-cost cap and the 0.1 USDT cost reserve. The split (expected fee for cost, full
  authority for reservation) follows LD09-B's stated intent, but it is a planner semantics change and needs their
  review.
- Gas is a reserved bound, not a measurement: an exact swap estimate before approval is refused by the venue
  (KG-DEC-01-H). Execution still estimates each payload after its approve (C8) inside `gas_budget`.
- Fees rest on `fee_bps = 0` (#119, unverified until LD19/20 receipts); an explicit `feeAmount` is refused.

### Open items

| Item | Owner | Where |
|---|---|---|
| Review the verifier, port and planner changes; merge | Isaac (GAP-29), Keegan; Keith for QV6 | this PR |
| Runtime config: add `untrusted_router_policy_file` / `_sha256` (LD03 policy `05759e90…`, readable by the runtime user) | Yao (host), Isaac (approval) | run sheet for the next run |
| Release, new run/database and REHEARSAL window decision (a run cannot change build) | Yao, Isaac, Keegan | IDEA-049-C SJ-11 / SJ-11-QV01 |
| Reword the SJ-11-QV01 backlog line (on the unmerged docs branch `claude/sj11-a2-local-rc6-20261024`) to the remaining release/run work once both merge | whoever merges second | `docs/INCOMPLETE_WORK.md` |
| `config/runtime/runtime.example.json` does not yet name the new optional pair | Keegan | follow-up |

## Amendment A1 — live read-only acceptance check (pre-registered 2026-10-24, before any A1 code or test)

Scope added by Yao through the coordinating session ("yes pls", 2026-10-24). The A1 results are recorded below; the
QV1–QV9 results above do not change.

**What.** `tools/deploy/quote_check.py`: one symbol and one side per run, which Yao runs on his Mac with the read-only
Web3 key in `.env`. It gets a real quote through `MarketPort.observe`, with the verifier built by
`larp.runtime.service.quote_verifier` (the service's own wiring) from:
- the run-3 S1 profile `rehearsal-s1-deterministic.json` (`6bcf1dfb…`) as `quote_limits`;
- the LD03 policy `05759e90…`;
- the dev wallet `0x62b8…d479`;
- a public read RPC.

A BUY defaults to 19 USDT (the profile's `per_trade_cap_units − cost_reserve_units`, the largest BUY the planner
requests). A SELL defaults to the token units a fresh BUY quote of that size would return; that amount is
hypothetical, not holdings.

The tool:
- prints only public values: status and exact refusal reason, decoded economics, recipient rule, gas and fee units,
  slippage and impact, open states, and `_quote_at_cap` at print time;
- never prints URLs, keys, the wallet address or calldata, and a privacy scan refuses any reflection of them;
- uses a Web3 client limited to the four read endpoints the quote path uses, and a read-only RPC;
- has no signer, AWS, database or submit path;
- exits 0 only for `VERIFIED_EXECUTABLE`, 2 for a refused quote and 4 for a tool or input error.

**Pass criteria.**
- **QV10 (offline):** with recorded quotes, fake RPC state and pinned files substituted, the tool behaves as follows.
  1. A BUY and a default SELL give `VERIFIED_EXECUTABLE` and exit 0, with decoded economics matching the request.
  2. A tampered calldata copy and a mismatched quote each give exit 2 with the port's exact `Unavailable` reason.
  3. The output never contains a credential, the RPC URL, the wallet address or calldata, and a reflected credential
     is refused.
  4. A profile or policy hash mismatch exits 4.
  5. The client refuses the approve, gas-limit and broadcast endpoints.
- **QV11 (live, Yao):** all five names return `VERIFIED_EXECUTABLE` with `_quote_at_cap` accepted, for a BUY of about
  19 USDT, while the US session is open (token and underlying `openState` true).
  - The result depends on the time of day. Off-hours a refusal can be legitimate, and that run is not evidence either
    way.
  - A refusal while the session is open is recorded as a QV11 FAIL with its reason, even if a later rerun passes.

### A1 results (2026-10-24, Claude Code)

| ID | Result | Evidence |
|---|---|---|
| QV10 | PASS (offline) | Commit `e8e76460`, `tests/execution/test_quote_check.py`, 8 tests. Red first: with the tool module moved aside, collection failed with an import error. The tests and the tool were then committed together. Results: (1) the recorded TSLAB BUY (40 USDT, profile cap/reserve scaled to it) and the default SELL of exactly its output both exit 0 `VERIFIED_EXECUTABLE`, with matching economics and `quote_at_cap` accepted; (2) inner-amount tampering, `minReceiveAmount` mismatch and another facet each exit 2 with the port's exact reason; (3) no key, RPC URL, wallet or calldata appears in the output, and a credential reflected in a refusal exits 4 without printing it; (4) a profile or policy hash mismatch exits 4, and the shipped pins are `6bcf1dfb…` / `05759e90…` with dev wallet `0x62b8…d479`; (5) the client refuses the approve, gas-limit and broadcast endpoints, and an artifact directory inside the checkout is refused. Full suite (PG 14.24): **2583 passed, 10 skipped, 0 failed** (log SHA-256 `90a7d8ad…`), with the same 10 environmental skips. |
| QV11 | NOT RUN | Live check owned by Yao during the US session; the command and pass shape are in the PR description. |

## Amendment A2 — the live check reports openState and assumes no trading hours (pre-registered 2026-10-24, before the A2 change)

Requested through the coordinating session. IDEA-089 S2 (PR269, decision only; first numbered IDEA-088 S2 there, renumbered 2026-10-24) plans a signed end-to-end dev-wallet
test outside NYSE hours, which F-119 allows; the runtime's `openState` guard stays. Its IDEA-089 S2-6 step needs this check to
return `VERIFIED_EXECUTABLE` for all five names at about 19 USDT shortly before install.

**Change.** The tool reads token and underlying `openState` from the same market observation path before quoting.
It prints `token_open` and `underlying_open` on every outcome: verified, refused, or a quote error after the market
read. It never refuses or passes because of the clock or the open state. The verdict stays the verifier's.
`openState` is reported next to the verdict; the planner, not this tool, enforces it.

**Pass criteria.**
- **QV12 (offline):** with token and/or underlying `openState` false, a valid recorded quote still exits 0
  `VERIFIED_EXECUTABLE` and reports the false states. A refused quote (exit 2) reports both states. No code path reads
  the clock to decide the verdict.
- **QV11 is restated.** Before: all five names at about 19 USDT while the US session is open. Now: all five names at
  about 19 USDT return `VERIFIED_EXECUTABLE` with `quote_at_cap` accepted, at the time the run needs it, with both
  `openState` values recorded per name.
  - An S2-style off-hours run counts toward QV11 only for the verifier.
  - Whether a closed `openState` blocks the trade is the planner's guard. That guard is out of scope here.

### A2 results (2026-10-24, Claude Code)

| ID | Result | Evidence |
|---|---|---|
| QV12 | PASS (offline) | Commit `dc89654b`. Red first: the refused-quote case had no `token_open` (KeyError). The closed-market pass already held, because the port does not gate on `openState`. After the change, with both states false, a valid recorded quote exits 0 `VERIFIED_EXECUTABLE` and reports `false/false`; a refused quote (exit 2) reports both states, closed or open. The clock is used only for the `started_at` stamp and quote freshness in `_quote_at_cap` (profile age 30 s, before the deadline), never for trading hours. Full suite (PG 14.24): **2585 passed, 10 skipped, 0 failed** (log `a7327bad…`). |

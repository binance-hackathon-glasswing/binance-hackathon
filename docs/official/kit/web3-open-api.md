# Calling the Binance Web3 Open API

For runnable code, see `examples/web3_auth.py` (a minimal implementation with comments) and `openapi.py` (the version used in the project, which adds retries, timeouts and request pacing).

## Requests

- Base URL: `https://web3.binance.com/build`; endpoint paths look like `/api/v1/dex/...`
- Headers:

| Header | Value |
|---|---|
| `X-OC-APIKEY` | API Key |
| `X-OC-TIMESTAMP` | UTC time, ISO-8601 with millisecond precision, e.g. `2026-09-26T07:41:35.841Z` |
| `X-OC-SIGN` | Signature, see below |
| `X-OC-RECV-WINDOW` | Optional; allowed clock skew in milliseconds. This project uses `15000` |
| `Content-Type` | Must be `application/json` for POST |

## Signing

```text
X-OC-SIGN = Base64( HMAC-SHA256( secret, timestamp + METHOD + "/build" + path + ["?" + query] + body ) )
```

- GET: `body` is an empty string; parameters go in the query string. Example:

```text
2026-09-26T07:41:35.841ZGET/build/api/v1/dex/market/rwa/price?binanceChainId=56&tokenContractAddresses=0x02fc...
```

- POST: parameters go in the JSON body, and `body` is the raw JSON actually sent (signing and sending must use the same bytes).
- Encode the query string yourself and use the same string for the signature and the URL; don't let the HTTP library re-encode it.
- The path must be prefixed with `/build`; leaving it out is the most common cause of signature errors.

## Responses

```json
{"code": 0, "msg": "success", "data": ..., "timestamp": 1790408497118, "success": true}
```

Only `code == 0` means success; **HTTP 200 can still be a failure**. Errors observed in testing:

| Error | HTTP | Common causes |
|---|---|---|
| `40001` | 200 | Bad parameters: POST parameters not in the JSON body, missing `binanceChainId`, invalid `bar` |
| `40102` | 401 | Signature error: wrong Secret, `/build` missing from the path, clock skew too large |
| `50000` | 200 | Server error, e.g. when a form-encoded request body is used |
| `42900` | 429 | Rate limited (too many calls in a short time). `openapi.py` keeps at least `WEB3_MIN_INTERVAL_S` (default 0.3 s) between calls and retries up to 3 times (after 1 s, 2 s, 4 s, or `Retry-After`) |
| 404 | 404 | Path does not exist; the response is in the gateway format `{path, status, message, error}`, with no `code` field |

## Endpoints used by this project

| Endpoint | Purpose | Key parameters | Key response fields |
|---|---|---|---|
| `GET /api/v1/dex/market/rwa/price` | bStocks prices (batch) | `binanceChainId=56`, `tokenContractAddresses` (comma-separated, ≤100) | `tokenPrice` |
| `GET /api/v1/dex/market/candles` | Candles | `tokenContractAddress`, `bar` (`1m` `5m` `15m` `1h` `4h` `1d`, etc.), `limit` | Each row is `[open, high, low, close, volume, timestamp ms, trade count]`, in ascending time order; only periods with trades are included |
| `GET /api/v1/dex/aggregator/quote-and-swap` | Quote and build an unsigned swap transaction | `amount` (smallest unit), `fromTokenAddress`, `toTokenAddress`, `userWalletAddress`, `vendor=LiquidMesh` (required), `slippagePercent` | `routerResult` (expected amount received, etc.), `tx` (`to` `data` `value` `gas` `gasPrice` `minReceiveAmount`) |
| `POST /api/v1/dex/balance/token-balances-by-address` | Balances (including native BNB) | `{"address", "tokenContractAddresses": [{"binanceChainId": "56", "tokenContractAddress"}]}`, ≤20 entries; pass `""` for native BNB | `data[0].tokenAssets[]`: `balance`, `rawBalance`; for BNB the returned address is `0xeeee…eeee` |
| `GET /api/v1/dex/aggregator/approve-transaction` | Build an unsigned approval transaction | `binanceChainId=56`, `tokenContractAddress` (the token being paid), `approveAmount` (smallest unit, = this order's `amount`), `vendor` (required for bStocks; pass the quote's `routerResult.vendorName`) | `data[0]`: `data` (approve calldata), `dexContractAddress` (the spender), `gasLimit`, `gasPrice`; the transaction's `to` is the token contract and `value` is 0 |
| `POST /api/v1/dex/pre-transaction/gas-limit` | Estimate the gas limit of the swap transaction | `{"binanceChainId": "56", "evmTx": {"from": <wallet address>, "to": tx.to, "data": tx.data, "value": "<tx.value as decimal string>"}}` | `gasLimit` (e.g. `"780552"`) |
| `POST /api/v1/dex/pre-transaction/broadcast-transaction` | Broadcast a signed transaction | `{"binanceChainId": "56", "signedTransaction": "0x<RLP hex>", "address": <wallet address>}` | `txHash`, `orderId` |
| `GET /api/v1/dex/post-transaction/transaction-detail-by-txhash` | Query the transaction result | `binanceChainId=56`, `txHash` | `data[0].txStatus` (`success` / `fail` / `pending`; may not be found right after broadcasting), `gasUsed`, `nonce` |
| `GET /api/v1/dex/post-transaction/transactions-by-address` | Transaction history (used to derive the nonce) | `address`, `chains=56`, `limit=100` | `data[0].transactionList[]`: `nonce`, `from` (`[{address, amount}]`); lists only transactions with token transfers, **approves are not included** |

Constants: BSC USDT `0x55d398326f99059fF775485246999027B3197955` (18 decimals); native BNB in quotes is `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`.

Only these five bStocks are eligible: NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB (addresses in the table). Other tokenized versions of the same stocks (e.g. Ondo, xStocks) are not eligible. All have 18 decimals.

| Symbol | Company | Contract |
|---|---|---|
| NVDAB | Nvidia | `0x02fca66c1d1afb4e2a7884261eb00f63598a7436` |
| GOOGLB | Alphabet (Google) | `0x3f53de71c126bdabae20f9cd64848d317f6c3238` |
| SKHYB | SK Hynix | `0xca750ef65f295bbecd685abf54e82caf297bdb61` |
| TSLAB | Tesla | `0x5b1910eaad6450e50f816082aa078c41f10c292f` |
| MSFTB | Microsoft | `0x80106cb3ead06659a5ad19df39d9b4733863b9b0` |

## Trading flow

1. Quote: `quote-and-swap` returns an unsigned transaction. **Quotes do not check balances**; before placing an order, check the pay token and BNB (for gas) with the balance endpoint. Gas is paid only in BNB; one trade (approve + swap) costs about 0.000022–0.000046 BNB (about $0.02–0.035; SKHYB is the most expensive route). If you run low on BNB, swap a little USDT for BNB through the same quote-and-swap endpoint (toTokenAddress `0xEeee…EEeE`); this swap itself also needs a little BNB for gas.
2. Approve: the Open API cannot query allowances, so **every order is approved first** for its own amount. Call `approve-transaction` (`vendor` = the quote's `vendorName`), sign locally (`to` = token contract, `value` = 0, gas from the returned `gasLimit` / `gasPrice`, nonce = N), broadcast, and poll the result until `success`; on failure, stop and do not send the swap.
3. After approving, **quote again** (quotes expire after about 30 seconds); if the new quote's `tx.to` differs from the spender `dexContractAddress`, stop. **Set the swap gas limit**: the quote's `tx.gas` is a fixed 450000, and routes for NVDAB, GOOGLB, SKHYB and MSFTB need about 450k–930k gas, so a swap sent with `tx.gas` reverts out of gas. Call `POST /api/v1/dex/pre-transaction/gas-limit` for this tx and use `gas = max(tx.gas, gasLimit × 1.2)`; unused gas is not charged. If the estimate fails, fall back to `tx.gas` and log a warning. Then sign the new quote's `tx` with that gas locally (nonce = N+1) and broadcast it with `broadcast-transaction`. If the swap reverts with `gasUsed` close to the gas limit, the gas limit was too low.
4. Query the result: query `transaction-detail-by-txhash` every 3 seconds for up to about 120 seconds; only `success` counts as filled, and not found is treated as not yet confirmed.
5. Write the swap's `tx_hash` into this round's log (see `logging.md`).

nonce: `N = max(highest nonce sent by this wallet in the transaction history + 1, local record logs/.last_nonce + 1)`, or 0 if neither exists. The transaction history does not include approves, so the local record fills the gap; it is written only after a transaction is confirmed (success and failure both consume a nonce; nothing is written on timeout). If a broadcast is rejected with an error message containing `nonce`, re-sign with nonce + 1 and resend, up to 3 times. Limitation: the nonce is derived, so it goes out of sync if another program or a manual transaction uses the same wallet. That is why the competition wallet is for the agent only, and each wallet runs only one agent.

For the implementation, see `trade()` and `_swap_gas_limit()` in `trade.py`, and `wallet.py`.

## About the official SDK

This project does not use the official Python SDK `binance-web3-wallet` at all; every endpoint is signed and called directly by `openapi.py`. The reason: its POST endpoints (6.x–7.0.0) put the parameters in the URL and send an empty request body, so the server returns `40001`, and the SDK does not report an error.

# bStocks Trading Guide

> Technical reference only, not investment advice; the official competition rules prevail. Last updated: 2026-10-01.

This guide shows how to trade bStocks (tokenized US stocks on BNB Smart Chain) **using only the Binance Web3 Open API**: no official SDK, no BSC RPC node, and the private key stays on your machine. The Python code comes from the demo projects (see Attachments), which also come in Java and Node.js.

## Overview

```text
Read market data and balances → Agent decides → Quote via quote-and-swap
   ├─ Quote-only (default): stop here
   └─ Live trading (TRADING_LIVE=1): check token and BNB balances
        → Build the approve transaction via approve-transaction (approve the pay token)
        → Sign locally + broadcast via broadcast-transaction (nonce = N)
        → Wait for confirmation via transaction-detail-by-txhash (on failure, stop; no swap is sent)
        → Re-quote (quotes expire after about 30 s)
        → Estimate the swap gas via pre-transaction/gas-limit (+20%)
        → Sign locally + broadcast the swap (nonce = N+1), wait for confirmation
→ Upload the decision log (ai-seeds log(); once the swap is broadcast, orders carries its tx_hash; when only holding, orders = [])
```

| Item | Convention |
|---|---|
| Chain | BNB Smart Chain, `binanceChainId = "56"`. Mainnet only, no testnet: every broadcast spends real funds and gas and cannot be undone |
| Base URL | `https://web3.binance.com/build` |
| Amounts | Integer strings in the smallest unit. USDT on BSC has **18 decimals**, not 6 as on Ethereum; bStocks also have 18, but always take `decimals` from the API |
| Responses | Only `code == 0` means success; **HTTP 200 can still mean failure** |
| Signing | API requests: HMAC-SHA256 with your API Secret, identifies the caller only. Transactions: signed locally with the wallet's private key, as legacy (`gasPrice`) transactions with `chainId = 56`; the Open API only returns unsigned transactions |
| Tokens | bStocks symbols end in `B`. Only these five bStocks are eligible: NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB (addresses in the table below). Other tokenized versions of the same stocks (e.g. Ondo, xStocks) are not eligible. The examples use NVDAB |

Eligible bStocks (BSC, 18 decimals, `platformId=bstock`):

| Symbol | Company | Contract |
|---|---|---|
| NVDAB | Nvidia | `0x02fca66c1d1afb4e2a7884261eb00f63598a7436` |
| GOOGLB | Alphabet (Google) | `0x3f53de71c126bdabae20f9cd64848d317f6c3238` |
| SKHYB | SK Hynix | `0xca750ef65f295bbecd685abf54e82caf297bdb61` |
| TSLAB | Tesla | `0x5b1910eaad6450e50f816082aa078c41f10c292f` |
| MSFTB | Microsoft | `0x80106cb3ead06659a5ad19df39d9b4733863b9b0` |

## Prerequisites

| Item | Details |
|---|---|
| API Key / Secret | In the [Binance Web3 Developer Portal](https://web3.binance.com/en/dev-portal/project), create a project, complete email and phone verification, and generate an API Key and Secret Key (HMAC-SHA256 only, see the [authentication docs](https://web3.binance.com/en/dev-docs/authentication)). The key cannot move funds, but anyone who has it can use up your quota: keep both secret. Env `BN_WEB3_API_KEY`, `BN_WEB3_API_SECRET` |
| Wallet | A new BSC wallet used only by your agent (one agent per wallet). It must be your registered `AI_SEEDS_ADDRESS` wallet, and `WALLET_PRIVATE_KEY` must be its key: the example in section 4 and the Node.js / Java demos exit otherwise. Env `AI_SEEDS_ADDRESS`, `WALLET_PRIVATE_KEY` (the demos also accept `WALLET_MNEMONIC`) |
| Funds | USDT to trade, BNB for gas (gas is paid only in BNB). In our tests one trade (approve + swap) cost 0.000022–0.000046 BNB (about $0.02–0.035 at BNB ≈ $756); SKHYB is the most expensive route. The example and the demos refuse to trade below **0.002 BNB**. If you run low on BNB, swap a little USDT for BNB through the same quote-and-swap endpoint (`toTokenAddress` `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`, approve USDT as usual); this swap itself also needs a little BNB for gas |
| Python | `pip install requests eth-account` |

## 1. Signing requests

| Header | Value |
|---|---|
| `X-OC-APIKEY` | API Key |
| `X-OC-TIMESTAMP` | UTC ISO-8601 with milliseconds, e.g. `2026-09-26T07:41:35.841Z` |
| `X-OC-SIGN` | `Base64(HMAC-SHA256(secret, timestamp + METHOD + "/build" + path + ["?" + query] + body))`. GET: parameters in the query string, `body` empty. POST: parameters in a JSON body, and the signed `body` is exactly the JSON sent. Sign and send the same encoded query string |
| `X-OC-RECV-WINDOW` | Optional; allowed clock skew in ms (default 5000, max 60000) |
| `Content-Type` | `application/json` for POST |

The code blocks in sections 1–4 build on each other: put them in one file, in order.

```python
import base64, datetime, hashlib, hmac, json, os, time, urllib.parse
import requests
from eth_account import Account
from eth_utils import to_checksum_address

BASE = "https://web3.binance.com/build"
KEY, SECRET = os.environ["BN_WEB3_API_KEY"], os.environ["BN_WEB3_API_SECRET"]
WALLET = os.environ["AI_SEEDS_ADDRESS"]      # registered wallet: quotes, balances and trades all use it

def call(method, path, params=None, body=None):
    """GET parameters go in params; POST parameters go in body (JSON request body). Returns the response data; raises if code != 0."""
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    query = urllib.parse.urlencode(params or {})
    raw = json.dumps(body, separators=(",", ":")) if body is not None else ""
    target = path + (f"?{query}" if query else "")
    pre_hash = ts + method + "/build" + target + raw
    sign = base64.b64encode(hmac.new(SECRET.encode(), pre_hash.encode(), hashlib.sha256).digest()).decode()
    headers = {"X-OC-APIKEY": KEY, "X-OC-TIMESTAMP": ts, "X-OC-SIGN": sign}
    if raw:
        headers["Content-Type"] = "application/json"
    r = requests.request(method, BASE + target, data=raw or None, headers=headers, timeout=20).json()
    if r.get("code") != 0:
        raise RuntimeError(f"{r.get('code')}: {r.get('msg')}")
    return r["data"]
```

## 2. Market data and account state

Every call passes the chain as `binanceChainId=56` (for balances, in each token entry); the transaction history takes `chains=56` instead.

| Purpose | Endpoint | Key parameters |
|---|---|---|
| bStocks list | `GET /api/v1/dex/market/rwa/tokens` | `platformId=bstock` |
| Prices | `GET /api/v1/dex/market/rwa/price` | `tokenContractAddresses`: up to 100, comma-separated |
| Underlying stock market and status | `GET /api/v1/dex/market/rwa/underlying-market` | `tokenContractAddress` |
| Candles | `GET /api/v1/dex/market/candles` | `tokenContractAddress`, `bar` (e.g. `1h`), `limit` |
| Balances | `POST /api/v1/dex/balance/token-balances-by-address` | JSON body, up to 20 tokens; `""` = native BNB |
| Transaction history | `GET /api/v1/dex/post-transaction/transactions-by-address` | `address`, `limit`; last 6 months, cursor pagination |

- `rwa/tokens`: `tokenContractAddress`, `tokenSymbol`, `decimals`, `underlyingTicker`, `tokenPrice`, and `statusInfo` (`openState`, `marketStatus`, `reasonCode`, `nextOpenTime`). When `openState` is `False` (here or in `rwa/underlying-market`), the market is closed or trading is halted: don't place orders.
- `rwa/price`: `tokenPrice` is the on-chain price in USD; `referencePrice` is a derived per-share reference price, not an official stock market quote.
- `candles`: each row is `[open, high, low, close, volume, timestamp_ms, tradeCount]`, oldest first; only periods with trades are included.
- Balances: in `data[0].tokenAssets[]`, `balance` is adjusted for decimals and `rawBalance` is in the smallest unit; zero balances are omitted, and native BNB comes back as `0xeeee…eeee`.

```python
NVDAB = "0x02fca66c1d1afb4e2a7884261eb00f63598a7436"   # example bStock (Nvidia)
USDT = "0x55d398326f99059fF775485246999027B3197955"    # BSC USDT
BNB_KEY = "0x" + "e" * 40                               # native BNB in balance responses

def balances(addrs):
    """addrs: token addresses, "" for native BNB. Returns {lowercase address: amount in smallest unit}."""
    data = call("POST", "/api/v1/dex/balance/token-balances-by-address", body={
        "address": WALLET,
        "tokenContractAddresses": [{"binanceChainId": "56", "tokenContractAddress": t} for t in addrs],
    })
    return {a["tokenContractAddress"].lower(): int(a["rawBalance"]) for a in (data[0]["tokenAssets"] if data else [])}
```

## 3. Quotes

`GET /api/v1/dex/aggregator/quote-and-swap` returns a quote and an unsigned swap transaction. Quotes are free and **don't check balances**: a transaction built without enough balance fails on-chain, and still costs gas.

| Parameter | Description |
|---|---|
| `binanceChainId` | `"56"` |
| `amount` | Pay token amount (smallest unit) |
| `fromTokenAddress` / `toTokenAddress` | Buy: USDT → bStock; sell: bStock → USDT |
| `userWalletAddress` | Wallet address |
| `vendor` | `"LiquidMesh"`: required and case-sensitive, any other value returns `40001` |
| `slippagePercent` | Percentage string, `"1"` = 1%. Pass it or `autoSlippage=true`; passing neither is a parameter error |
| `priceImpactProtectionPercent` | Optional; defaults to 90, lower it to reject shallow pools |

The response has `routerResult` (`toTokenAmount` expected amount received, `priceImpactPercent`, `vendorName` used when approving) and `tx` (`to` router contract, `data`, `value`, `gas` (a fixed 450000, often too low: see Swap gas in section 4), `gasPrice`, and `minReceiveAmount`, the minimum received under slippage protection).

```python
def quote(pay_token, recv_token, amount_wei):
    return call("GET", "/api/v1/dex/aggregator/quote-and-swap", {
        "binanceChainId": "56", "amount": str(amount_wei),
        "fromTokenAddress": pay_token, "toTokenAddress": recv_token,
        "userWalletAddress": WALLET, "vendor": "LiquidMesh", "slippagePercent": "1",
    })
```

## 4. Placing orders

Orders follow the flow in the Overview: check balances, approve, confirm, re-quote, estimate the swap gas, swap, confirm.

**Approve**: the Open API can't read allowances, so every trade first approves the **pay token** (USDT to buy, the bStock to sell) for exactly its amount. `approve-transaction` takes the quote's `vendorName` as `vendor` (required for bStocks) and returns `data`, `gasLimit`, `gasPrice` and the spender `dexContractAddress`, which must equal the re-quote's `tx.to`. The approve goes to the token contract with `value` 0 and costs gas. Wait for its `success`, then re-quote: bStock quotes use RFQ liquidity and expire after about 30 s.

**Swap gas**: the quote's `tx.gas` is a fixed 450000, but the routes for NVDAB, GOOGLB, SKHYB and MSFTB need about 450k–930k gas, so a swap signed with `tx.gas` can revert out of gas. Before signing the swap, `swap_gas()` calls `POST /api/v1/dex/pre-transaction/gas-limit` with the swap's `from`, `to`, `data` and `value` (decimal string) and uses `max(tx.gas, gasLimit × 1.2)`. Unused gas is not charged, so the headroom costs nothing when the swap succeeds. If the estimate fails, it falls back to `tx.gas` and logs a warning. The approve keeps the `gasLimit` from `approve-transaction`.

**Nonce**: the Open API has no nonce endpoint, so take the highest nonce this wallet has sent + 1 from the transaction history. The history **doesn't include approves**, so also keep the last nonce you used and take the larger; if a broadcast is still rejected over its nonce, `sign_and_send` re-signs with nonce + 1, up to 3 times.

**Confirmation**: only `txStatus == "success"` means success; `fail` means reverted (gas is still spent); `pending` or no result yet means unconfirmed. After 120 s `wait()` returns `"timeout"`: the transaction may still be mined, so check BscScan before sending another.

```python
def next_nonce(last_used=None):
    data = call("GET", "/api/v1/dex/post-transaction/transactions-by-address",
                {"address": WALLET, "chains": "56", "limit": 100})
    me = WALLET.lower()
    sent = [int(t["nonce"]) for page in data or [] for t in page.get("transactionList") or []
            if str(t.get("nonce", "")).isdigit() and any(f["address"].lower() == me for f in t.get("from") or [])]
    n = max(sent) + 1 if sent else 0
    return n if last_used is None else max(n, last_used + 1)

last_used = None    # last nonce used; persist it to a local file in practice so it survives a restart

def sign_and_send(tx, nonce):
    """Sign locally and broadcast. On a nonce rejection, retry with nonce + 1, at most 3 times. Returns (txHash, nonce used)."""
    tx = {**tx, "to": to_checksum_address(tx["to"]), "nonce": nonce, "chainId": 56}
    for _ in range(4):
        signed = acct.sign_transaction(tx)
        try:
            call("POST", "/api/v1/dex/pre-transaction/broadcast-transaction", body={
                "binanceChainId": "56", "signedTransaction": "0x" + bytes(signed.raw_transaction).hex(), "address": WALLET})
            return "0x" + bytes(signed.hash).hex(), tx["nonce"]
        except RuntimeError as e:
            if "nonce" not in str(e).lower():
                raise
            tx["nonce"] += 1
    raise RuntimeError("nonce retries exhausted")

def swap_gas(t):
    """Gas limit for the swap t (the quote's tx): max(tx.gas, estimate x 1.2). Falls back to tx.gas if the estimate fails."""
    try:
        est = call("POST", "/api/v1/dex/pre-transaction/gas-limit", body={"binanceChainId": "56", "evmTx": {
            "from": WALLET, "to": t["to"], "data": t["data"], "value": str(int(t["value"] or 0))}})
        return max(int(t["gas"]), int(int(est["gasLimit"]) * 1.2))
    except (RuntimeError, requests.RequestException, KeyError, TypeError, ValueError) as e:
        print(f"warning: gas-limit estimate failed ({e}); using the quote's tx.gas")
        return int(t["gas"])

def wait(tx_hash, timeout=120):
    """Poll the transaction result every 3 s. Returns "success", "fail", or "timeout" if still unconfirmed."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            d = call("GET", "/api/v1/dex/post-transaction/transaction-detail-by-txhash",
                     {"binanceChainId": "56", "txHash": tx_hash})
            st = ((d[0] if isinstance(d, list) and d else d) or {}).get("txStatus")
            if st in ("success", "fail"):
                return st
        except (RuntimeError, requests.RequestException):
            pass                                        # not indexed yet: keep waiting
        time.sleep(3)
    return "timeout"
```

### Full example: buy and sell

By default it only quotes and signs nothing; `TRADING_LIVE=1` (the same switch as the demos) makes it trade. Before sending anything it checks that `WALLET_PRIVATE_KEY` belongs to `AI_SEEDS_ADDRESS` and that the pay token and BNB balances are enough. To sell, use the commented line instead.

```python
# Buy: pay USDT for NVDAB; amount is the USDT spent
pay, recv, amount = USDT, NVDAB, 150_000_000_000_000_000      # 0.15 USDT
# Sell: pay NVDAB for USDT; amount is the NVDAB quantity sold
# pay, recv, amount = NVDAB, USDT, 500_000_000_000_000        # 0.0005 NVDAB (about $0.12)

q = quote(pay, recv, amount)
print("expected", int(q["routerResult"]["toTokenAmount"]) / 1e18, "min", int(q["tx"]["minReceiveAmount"]) / 1e18)
if os.getenv("TRADING_LIVE") != "1":                          # default: quote only
    raise SystemExit("quote only: nothing signed or sent (set TRADING_LIVE=1 to trade)")

acct = Account.from_key(os.environ["WALLET_PRIVATE_KEY"])    # never print or log it
if acct.address.lower() != WALLET.lower():
    raise SystemExit("WALLET_PRIVATE_KEY is not the key of AI_SEEDS_ADDRESS; nothing sent")
bal = balances([pay, ""])
if bal.get(pay.lower(), 0) < amount or bal.get(BNB_KEY, 0) < 2 * 10**15:
    raise SystemExit("need the pay amount and at least 0.002 BNB for gas; nothing sent")

# 1) Approve the pay token (this trade's amount only)
a = call("GET", "/api/v1/dex/aggregator/approve-transaction", {"binanceChainId": "56", "tokenContractAddress": pay,
         "approveAmount": str(amount), "vendor": q["routerResult"]["vendorName"]})[0]
h, n = sign_and_send({"to": pay, "data": a["data"], "value": 0,
                      "gas": int(a["gasLimit"]), "gasPrice": int(a["gasPrice"])}, next_nonce(last_used))
if wait(h) != "success":
    raise SystemExit(f"approve {h} not confirmed; swap not sent")
last_used = n                                           # approves are not in the transaction history, so record it

# 2) Re-quote, estimate the gas, then sign and broadcast the swap
t = quote(pay, recv, amount)["tx"]
if t["to"].lower() != a["dexContractAddress"].lower():
    raise SystemExit("router address does not match the approved spender; swap not sent")
swap_hash, n = sign_and_send({"to": t["to"], "data": t["data"], "value": int(t["value"] or 0),
                              "gas": swap_gas(t), "gasPrice": int(t["gasPrice"])}, n + 1)   # not t["gas"]: too low for some routes
last_used = n
print(wait(swap_hash), f"https://bscscan.com/tx/{swap_hash}")   # log swap_hash whatever the result (section 5)
```

## 5. Decision logs

Upload one log per decision round with the ai-seeds SDK, including rounds that only hold (`orders=[]`):

```python
seeds = Client()        # from ai_seeds_sdk import Client; reads AI_SEEDS_ADDRESS / AI_SEEDS_SECRET
seeds.log(input=prompt_and_market_data, cot=reasoning, output=final_output,
          orders=[{"symbol": "NVDAB", "side": "BUY", "amount": "0.15", "tx_hash": swap_hash}])
```

- Once a swap is broadcast, log its `tx_hash` whatever the confirmation outcome (success, fail or timeout); only the swap's, never the approve's. Orders that never went on-chain are listed without `tx_hash`.
- Part 2 of the participant guide (logging) and the SDK docs in `ai-seeds-sdk-0.3.0.zip` cover the rest.

## 6. Errors and pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `code 40102` (HTTP 401) | Invalid signature | Check the Secret; sign exactly the query and body you send, with `/build` in the path |
| `code 40103` (HTTP 401) | Timestamp expired or request replayed | Sync the clock (NTP); use a new timestamp for every request |
| `code 40104` | API Key lacks the permission | Check the project and key permissions in the Developer Portal |
| `code 40001` (HTTP 200) | Parameter error | Put POST parameters in the JSON body; check required parameters (`binanceChainId`, `vendor`, `slippagePercent`) and values (e.g. `bar`) |
| `code 42900` (HTTP 429) | Rate limited | Back off exponentially; cache market data and poll at fixed intervals, never quote in a tight loop |
| `code 50000` | Server error, or a non-JSON body (e.g. form-encoded) | Send `Content-Type: application/json`; retry later |
| HTTP 404 without `code` | Wrong endpoint path | Check the path |
| Quote fails | No route, or amount too small | Catch it; change the token or amount (0.15 USDT buys worked in our tests) |
| Swap reverts with `DeadlinePassed` | Quote expired | Re-quote after the approve, then sign and broadcast at once |
| Swap reverts with `gasUsed` close to the gas limit | The quote's `tx.gas` (450000) is too low for this route | Estimate with `/pre-transaction/gas-limit` and add 20% headroom (`swap_gas` does) |
| Swap reverts otherwise | Approve missing or unconfirmed, price moved beyond slippage, or low balance | Wait for the approve's `success` and check balances first; re-quote and sign a new transaction, never resend an old signed one unchanged |
| Broadcast error mentioning `nonce` | Nonce too low: an approve missing from the history, or the wallet was used elsewhere | `sign_and_send` retries with nonce + 1, up to 3 times; use the wallet for one agent only |
| No transaction can be sent | No BNB for gas | Keep at least 0.002 BNB |
| Hash without `0x` | `.hex()` from `hexbytes` (used by `eth-account`) may drop the prefix | Add `0x` before broadcasting or logging (the helpers do) |

## 7. Security

- Keep API secrets, private keys and seed phrases only in environment variables, a local `.env` listed in `.gitignore`, or a secrets manager. Never commit, print or log them.
- Keep live trading behind `TRADING_LIVE=1` (the Python demo also requires a one-time arm file), and reject orders above a per-trade cap (the Python demo allows 0.1–0.2 USDT by default).
- Handle quote failures, reverts, rejected broadcasts and timeouts without endless retries or repeated orders.

## 8. Known limitations

- **No allowance or nonce query**: every trade approves its own amount first (extra gas), and the nonce is derived, so transactions sent from elsewhere cause retries.
- **No cancel**: a swap either fills in full or reverts, and a revert still costs gas. To change an order, re-quote and send a new transaction.
- **Official SDK**: `binance-web3-wallet` (6.x–7.0.0) puts POST parameters in the URL and fails silently with `40001`, so this guide calls the HTTP endpoints directly.

## Attachments

- `bstocks-trading-demo.zip`: Python, full-featured (minimal examples, trading service, demo agent); trading code in `openapi.py`, `trade.py`, `wallet.py`. Each demo's `README.md` explains how to run it.
- `bstocks-trading-demo-nodejs.zip`: Node.js, the same flow in one file (`index.mjs`).
- `bstocks-trading-demo-java.zip`: Java, the same flow in one class (`BstocksDemo.java`).
- The ai-seeds SDK (`ai-seeds-sdk-0.3.0.zip`) is not inside the demo zips; download it as well.

API docs: [Authentication](https://web3.binance.com/en/dev-docs/authentication) · [Trading API](https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/trading-api) · [Transaction API](https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/transaction-api) · [Wallet API](https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/wallet-api) · [General Data](https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/general-data) · [RWA Data](https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/rwa-data)

Verified live on 2026-10-01 with the Python demo's trade path, all logs received by ai-seeds: one 0.2 USDT buy of each eligible bStock, swaps NVDAB [0x3f01ade8…2eff](https://bscscan.com/tx/0x3f01ade83d60498f6bea8a2675d7c733b03cfecd1c242bb061a4285d36bf2eff), GOOGLB [0x05c8d8c0…f760](https://bscscan.com/tx/0x05c8d8c0a2a3842262d8bb71452ac27f2891d9f33e4af740d6677476dc98f760), SKHYB [0x2665ca89…6fdf](https://bscscan.com/tx/0x2665ca89d718d0137c6455705e1df6d613b9a375e530350615fd065246f26fdf), TSLAB [0x0e00a546…33b7](https://bscscan.com/tx/0x0e00a546aa9b48769971cdf17555afff51e2860fd6d30459cd1c34662cd133b7), MSFTB [0x12d67bb6…b4e0](https://bscscan.com/tx/0x12d67bb6c5e7901a1083a60de892b37c9268f42f9313530645acc0d60494b4e0).

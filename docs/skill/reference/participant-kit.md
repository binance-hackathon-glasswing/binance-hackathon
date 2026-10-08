---
name: participant-kit-reference
description: Complete operational reference for the organiser-issued AI Seeds Participant Kit (Participant Guide PDF, ai-seeds SDK 0.3.0 + PROTOCOL 2.0, bStocks trading demos in Python/Node.js/Java). Load it for any question on trading bStocks through the Binance Web3 Open API, signing, endpoints, error codes, nonce/gas/approve flow, ai-seeds decision logging, upload modes, or what the kit demos do and do not do. SKILL.md §1.9 (F-90..F-112) is the compact authoritative summary; this file is the detail.
version: 1.0.0
revised: 2026-10-05 (SGT, UTC+8)
source_verification:
  - every kit file read in full 2026-10-05, including the SDK wheel and npm tgz sources; all 18 Guide pages checked visually (text, tables and code only; no figures)
  - PROTOCOL §2 test vectors reproduced locally 2026-10-05 (both signatures match)
  - verbatim copies in docs/official/kit/ (sha256 in its README.md); vendored SDK wheel + manual_push.sh in vendor/ai-seeds-sdk-0.3.0/
primary_source: AI Seeds Participant Kit (organiser-issued; Guide PDF created 2026-10-01; SDK 0.3.0; trading guide "Last updated: 2026-10-01")
---

# Binance Agentic AI Challenge — Participant kit reference (K)

> Operational reference distilled from the whole participant kit. Section anchors K1..K18 are stable; cite as "participant-kit.md K8".
> Citations: **PG p.N** = `docs/official/kit/AI_Seeds_Participant_Guide.pdf` page N; **TG** = `docs/official/kit/bstocks-trading-guide.md` (Markdown of PG Part 1); **OA** = `docs/official/kit/web3-open-api.md`; **LG** = `docs/official/kit/logging.md`; **SR** = `docs/official/kit/ai-seeds-sdk-README.md`; **PR §N** = `docs/official/kit/PROTOCOL.md`; kit-only files are cited by kit path (`SDK/<path>` = `ai-seeds-sdk-0.3.0/<path>`, `PY/<path>` = `bstocks-trading-demo/<path>`, `NJ/<path>` = `bstocks-trading-demo-nodejs/<path>`, `JV/<path>` = `bstocks-trading-demo-java/<path>`).

**Status and precedence.** The official competition rules outrank the kit: "This guide covers technical integration only and is not investment advice. If anything here conflicts with the official competition rules, the official rules prevail." (PG p.2). The kit contains **no event logistics** — no dates, trading window, scoring, prizes, eligibility, deliverables, disqualification rules or contacts (K18). SKILL.md §1.9 (F-90..F-112) is the compact authoritative summary used for decisions; this file holds the detail behind it. Where this file and §1.9 disagree, §1.9 wins until reconciled. Facts here are organiser text unless marked **[demo behaviour]** (what reference code does, not a rule) or **[our note]**.

---

## K1. Participant Guide page map

| Page | Part / section | Content |
|---|---|---|
| p.1 | Downloads | The 4 zips: `ai-seeds-sdk.zip`, `bstocks-trading-demo.zip` (Python, full-featured), `bstocks-trading-demo-nodejs.zip` (single file), `bstocks-trading-demo-java.zip` (single class) |
| p.2 | Start here | Precedence disclaimer; one-paragraph challenge description; "What you need" table; Quickstart steps 1–4 |
| p.3 | Start here (cont.) | Quickstart run commands; step 5 (plug in own agent, go live); "Don't miss" bullet list |
| p.4 | Part 1 · Trading bStocks | Overview flow diagram (text); conventions table (chain, base URL, amounts, responses, signing, tokens); eligible bStocks table |
| p.5 | Part 1 | Prerequisites table (API key, wallet, funds, Python deps); §1 Signing requests (header table, start of `call()`) |
| p.6 | Part 1 | End of `call()`; §2 Market data and account state (endpoint table, field notes, `balances()`) |
| p.7 | Part 1 | §3 Quotes (parameter table, response fields, `quote()`); §4 Placing orders: Approve, Swap gas, Nonce |
| p.8 | Part 1 | §4 Confirmation; `next_nonce()`, `sign_and_send()`, `swap_gas()`, `wait()` |
| p.9 | Part 1 | Full example: buy and sell; §5 Decision logs |
| p.10 | Part 1 | §6 Errors and pitfalls table; §7 Security; §8 Known limitations (start) |
| p.11 | Part 1 | §8 (end); Attachments; API doc links; verified-live note with 5 tx hashes |
| p.12 | Part 2 · Logging (ai-seeds SDK) | Purpose; Install (3 languages); Quick start (env vars, endpoint, `log()` in Python/Node/Java) |
| p.13 | Part 2 | One Client per process; What to log (field table + rules); Two modes (diagram + table) |
| p.14 | Part 2 | How to enable batch; Errors and automatic re-sending; delivery warning; Signing; More |
| p.15 | Part 2 | Filling input/cot/output per model provider (table); Running the examples; Several model calls in one round |
| p.16 | Part 2 | Multi-call code (end) |
| p.17 | Part 3 · Before going live and FAQ | Pre-launch checklist; Binance Skills table |
| p.18 | Part 3 | Skills table (end); "Important" trading-channel box; FAQ (testnet, other languages, fill without log, batch push, slippage, rate limits) |

Hyperlinks in the PDF (PG p.5, p.11, p.17): `https://web3.binance.com/en/dev-portal/project`, `https://web3.binance.com/en/dev-docs/authentication`, `https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/trading-api`, `https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/transaction-api`, `https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/wallet-api`, `https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/general-data`, `https://web3.binance.com/en/dev-docs/catalog/web3-wallet/api/rest-api/rwa-data`, `https://www.binance.com/en/skills`, and the five bscscan links in K8.

---

## K2. Rules stated in the kit; allowed and forbidden channels

| # | Rule (organiser text) | Source |
|---|---|---|
| R1 | Your team "builds an AI agent that trades bStocks (tokenized US stocks, BEP-20 tokens on BNB Smart Chain) through the Binance Web3 Open API, and uploads one decision log per round with the ai-seeds SDK" | PG p.2 |
| R2 | Audit chain: `tx_hash` → the round log that recorded it → that round's input, chain of thought and output. "A fill without a log cannot be shown to come from your agent." | PG p.2 |
| R3 | One log per decision round, including hold-only rounds (`orders=[]`) | PG p.3, p.13 |
| R4 | Every broadcast swap goes into `orders` with its `tx_hash` (succeeded, failed or unconfirmed); orders never on-chain are listed without `tx_hash` | PG p.3, p.13 |
| R5 | "Approvals are not orders: never log an approve transaction." | PG p.3 |
| R6 | Clock in sync (NTP, within ±5 minutes) | PG p.3, p.14 |
| R7 | Batch mode: "a day's logs must arrive before 02:00 UTC the next day. If they arrive later, the related fills are first flagged as 'fill without log'." | PG p.3 |
| R8 | "Trade only from the registered `AI_SEEDS_ADDRESS`; your private key or mnemonic must belong to that wallet." | PG p.3 |
| R9 | Never put API secrets, private keys, the mnemonic or `AI_SEEDS_SECRET` into logs; never commit them | PG p.3, p.10, p.17 |
| R10 | "Demo and example runs upload real logs under your wallet, even in quote-only mode." | PG p.3, p.15 |
| R11 | Only five bStocks are eligible: NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB. "Other tokenized versions of the same stocks (e.g. Ondo, xStocks) are not eligible." | PG p.4, p.17 |
| R12 | Wallet: new, dedicated, "used only by your agent (one agent per wallet)"; registered with the organisers | PG p.2, p.5, p.17 |
| R13 | "Place orders only through the Web3 Open API with local signing (Part 1)." | PG p.18 |
| R14 | Daily check: "Every day, all fills from the previous day are checked. A fill whose `tx_hash` is in no log is flagged for manual review" | PG p.18 |
| R15 | Other languages / frameworks allowed "as long as you keep the chain 'market data → decide → order → `log()`'"; other languages write their own client from PROTOCOL.md | PG p.18 |

**Pre-launch checklist** (PG p.17, "Before going live"; SKILL.md F-105):

| # | Check |
|---|---|
| C1 | API Key/Secret, `AI_SEEDS_SECRET` and the private key or mnemonic only in a local `.env` or a secrets manager: not in the repository, not in any log |
| C2 | The agent trades from the registered wallet (`AI_SEEDS_ADDRESS`), and only this one agent uses that wallet |
| C3 | The wallet holds USDT to trade and enough BNB for gas |
| C4 | Only the five eligible bStocks are traded; decimals are taken from the API response |
| C5 | Quotes pass `vendor=LiquidMesh` and an explicit `slippagePercent` |
| C6 | A full round has run in quote-only mode (without `TRADING_LIVE=1`), and the expected amount, `minReceiveAmount` and price impact look reasonable |
| C7 | Each trade has an amount cap, and orders above it are refused |
| C8 | Before each swap: pay token approved, approve confirmed, swap quoted again, swap gas limit estimated with `/pre-transaction/gas-limit` (+20%), not taken from the quote's `tx.gas` |
| C9 | Quote failures, reverts, rejected broadcasts and confirmation timeouts are handled, "and never lead to endless retries or repeated orders" |
| C10 | `log()` runs every round, including hold-only rounds, and every broadcast swap's `tx_hash` is in `orders` |
| C11 | `UploadError` and `ValidationError` from `log()` are caught. In batch mode the process keeps running past 00:00 UTC until the push succeeds (00:02–00:10 UTC, then a retry every 30 minutes) |
| C12 | The clock is synced (NTP) |

**Forbidden as the competition trading channel** (PG p.18 "Important"): `binance-agentic-wallet` ("places orders from a Binance custodial wallet") and the trading functions of the `binance` skill ("trade on the exchange spot market").

**Binance Skills listed** (PG p.17–18; hub `https://www.binance.com/en/skills`):

| Skill | What it does | Kit note |
|---|---|---|
| `binance` | Spot market data through `binance-cli`: candles, tickers, order book, recent trades | Public, no key. "Its trading functions must not be used in this competition" |
| `query-token-info` | On-chain token search, metadata, live prices, candles | Public, no key |
| `crypto-market-rank` | Rankings by trending, smart-money inflow, trader PnL, etc. | Public |
| `trading-signal` | On-chain smart-money signals | Public; "can inform decisions" |
| `query-address-info` | Token holdings, prices and balances of an address | Public |
| `query-token-audit` | Token security audit: risk score, honeypot detection | Public |
| `binance-tokenized-securities-info` | Tokenized US stock prices, market status, candles | "Covers Ondo only and does not include bStocks; for bStocks use the Open API `rwa/tokens` and `rwa/price` endpoints" |

---

## K3. Chain, assets and tokens

| Item | Value | Source |
|---|---|---|
| Chain | BNB Smart Chain mainnet; `binanceChainId = "56"`; transaction `chainId = 56`. "Mainnet only, no testnet: every broadcast spends real funds and gas and cannot be undone" | PG p.4, p.18 |
| Token standard | BEP-20; bStocks symbols end in `B`; `platformId=bstock` | PG p.2, p.4 |
| Decimals | USDT on BSC **18** (not 6 as on Ethereum); bStocks 18, "but always take `decimals` from the API" | PG p.4 |
| Amount format | Integer strings in the smallest unit | PG p.4 |

| Symbol | Company | Contract (BSC, 18 decimals) | Underlying ticker (PY/config.py) |
|---|---|---|---|
| NVDAB | Nvidia | `0x02fca66c1d1afb4e2a7884261eb00f63598a7436` | NVDA |
| GOOGLB | Alphabet (Google) | `0x3f53de71c126bdabae20f9cd64848d317f6c3238` | GOOGL |
| SKHYB | SK Hynix | `0xca750ef65f295bbecd685abf54e82caf297bdb61` | SKHY |
| TSLAB | Tesla | `0x5b1910eaad6450e50f816082aa078c41f10c292f` | TSLA |
| MSFTB | Microsoft | `0x80106cb3ead06659a5ad19df39d9b4733863b9b0` | MSFT |

(PG p.4; OA; PY/config.py `BSTOCKS_WATCHLIST`)

| Asset form | Value | Where used | Source |
|---|---|---|---|
| BSC USDT (pay/quote token) | `0x55d398326f99059fF775485246999027B3197955` | quote-and-swap from/to, approve, balances | PG p.6; OA |
| Native BNB in quotes | `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` | `toTokenAddress` for USDT → BNB gas top-up | PG p.5; OA |
| Native BNB in balance **requests** | `""` (empty string) as `tokenContractAddress` | token-balances-by-address | PG p.6 |
| Native BNB in balance **responses** | `0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee` (`"0x" + "e"*40`) | `tokenAssets[].tokenContractAddress` | PG p.6; PY/wallet.py `NATIVE_RETURNED` |

Address verification **[demo behaviour]**: `PY/tokenlist.py` checks the five addresses and decimals against the public token list `https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/rwa/stock/detail/list/ai` (no auth; headers `Accept-Encoding: identity`, `User-Agent: binance-web3/1.1 (Skill)`; success `code == "000000"`; match on `symbol` + `chainId == 56` + `type == 3`; fields `contractAddress`, `d` = decimals) (PY/config.py, PY/tokenlist.py).

---

## K4. Credentials, wallet, funding and gas

| Item | Detail | Source |
|---|---|---|
| Web3 API Key + Secret | Developer Portal (`https://web3.binance.com/en/dev-portal/project`): create a project, complete email and phone verification, generate API Key and Secret Key (HMAC-SHA256 only). "The key cannot move funds, but anyone who has it can use up your quota." Env `BN_WEB3_API_KEY`, `BN_WEB3_API_SECRET` | PG p.2, p.5 |
| Wallet | New BSC wallet used only by your agent, registered with the organisers; address = `AI_SEEDS_ADDRESS`; `WALLET_PRIVATE_KEY` (demos also accept `WALLET_MNEMONIC`, derivation path `m/44'/60'/0'/0/0`) signs locally; "the example in section 4 and the Node.js / Java demos exit otherwise" if the key does not match | PG p.2, p.5; JV/.env.example; PY/wallet.py |
| `AI_SEEDS_SECRET` | "Issued by the organizers for that wallet. The SDK signs every log upload with it"; a 64-character hex string; HMAC key = its UTF-8 bytes | PG p.2; PR §2 |
| Funds | "USDT to trade, BNB for gas (gas is paid only in BNB)" | PG p.2, p.5 |
| Gas cost observed | One trade (approve + swap) cost 0.000022–0.000046 BNB (about $0.02–0.035 at BNB ≈ $756); SKHYB is the most expensive route | PG p.5 |
| Gas floor | "The example and the demos refuse to trade below **0.002 BNB**" (a demo threshold; checklist says "enough BNB for gas") | PG p.5, p.17 |
| BNB top-up | Swap a little USDT for BNB through quote-and-swap (`toTokenAddress 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`, approve USDT as usual); "this swap itself also needs a little BNB for gas" | PG p.2, p.5 |
| Clock | NTP on; log uploads fail with `401 TIMESTAMP_SKEW` beyond ±5 min | PG p.2 |
| Runtimes | Demos: Python ≥ 3.10, Node.js ≥ 20.6, JDK ≥ 17 + Maven. SDK alone: Python ≥ 3.9, Node.js ≥ 18, Java ≥ 17 | PG p.2 |
| Python deps (guide example) | `pip install requests eth-account` | PG p.5 |
| Who funds the wallet / how much | **Not in the kit** (team statement in SKILL.md F-107) | — |

---

## K5. Web3 Open API authentication

Base URL `https://web3.binance.com/build`; endpoint paths `/api/v1/dex/...` (PG p.4; OA).

| Header | Value | Source |
|---|---|---|
| `X-OC-APIKEY` | API Key | PG p.5 |
| `X-OC-TIMESTAMP` | UTC ISO-8601 with milliseconds, e.g. `2026-09-26T07:41:35.841Z` | PG p.5 |
| `X-OC-SIGN` | `Base64(HMAC-SHA256(secret, timestamp + METHOD + "/build" + path + ["?" + query] + body))` | PG p.5 |
| `X-OC-RECV-WINDOW` | Optional; allowed clock skew in ms, default 5000, max 60000. PY demo sends `15000`; NJ/JV send none | PG p.5; PY/openapi.py |
| `Content-Type` | `application/json` for POST | PG p.5 |

Rules (PG p.5; OA; PY/examples/web3_auth.py):
- Signature is Base64 of the **raw** HMAC digest (not hex). The secret's UTF-8 bytes are the key. HMAC-SHA256 is the only scheme ("no Ed25519 / RSA", PY/openapi.py).
- `"/build"` must be in the signed path — omitting it is "the most common cause of signature errors" (`40102`).
- GET: parameters in the query string; `body` = `""`. Encode the query yourself and use the **same string** for the signature and the URL (don't let the HTTP library re-encode it). Commas in `tokenContractAddresses` become `%2C`, which the server accepts.
- POST: parameters in a JSON body; the signed `body` is exactly the JSON bytes sent (compact `separators=(",", ":")`). Form-encoded bodies fail (`50000`).
- New timestamp per request; replays → `40103`.
- Example pre-hash (OA): `2026-09-26T07:41:35.841ZGET/build/api/v1/dex/market/rwa/price?binanceChainId=56&tokenContractAddresses=0x02fc...` (truncated in the source itself).

Minimal Python, matching the kit's `call()` (PG p.5–6; TG §1):

```python
import base64, datetime, hashlib, hmac, json, os, urllib.parse, requests
BASE = "https://web3.binance.com/build"
KEY, SECRET = os.environ["BN_WEB3_API_KEY"], os.environ["BN_WEB3_API_SECRET"]

def call(method, path, params=None, body=None):
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    query = urllib.parse.urlencode(params or {})
    raw = json.dumps(body, separators=(",", ":")) if body is not None else ""
    target = path + (f"?{query}" if query else "")
    sign = base64.b64encode(hmac.new(SECRET.encode(), (ts + method + "/build" + target + raw).encode(),
                                     hashlib.sha256).digest()).decode()
    headers = {"X-OC-APIKEY": KEY, "X-OC-TIMESTAMP": ts, "X-OC-SIGN": sign}
    if raw:
        headers["Content-Type"] = "application/json"
    r = requests.request(method, BASE + target, data=raw or None, headers=headers, timeout=20).json()
    if r.get("code") != 0:
        raise RuntimeError(f"{r.get('code')}: {r.get('msg')}")
    return r["data"]
```

Do not use the official Python SDK `binance-web3-wallet` (6.x–7.0.0): it "puts POST parameters in the URL and fails silently with `40001`" and returns inconsistent types (PG p.11; PY/openapi.py docstring; PY/requirements.txt).

---

## K6. Endpoint reference

Every call passes `binanceChainId=56` (for balances, inside each token entry); the transaction history takes `chains=56` instead (PG p.6).

| Method + path | Purpose | Parameters | Response fields | Source |
|---|---|---|---|---|
| GET `/api/v1/dex/market/rwa/tokens` | bStocks list + market state | `platformId=bstock` | `tokenContractAddress`, `tokenSymbol`, `decimals`, `underlyingTicker`, `tokenPrice`, `statusInfo{openState, marketStatus, reasonCode, nextOpenTime}` | PG p.6 |
| GET `/api/v1/dex/market/rwa/price` | Prices (batch) | `binanceChainId=56`, `tokenContractAddresses` (≤ 100, comma-separated) | `tokenContractAddress`, `tokenPrice` (on-chain USD price), `referencePrice` ("a derived per-share reference price, not an official stock market quote"), `tokenPriceUpdatedAt` (ms; PY/examples/01_signed_get.py) | PG p.6; OA |
| GET `/api/v1/dex/market/rwa/underlying-market` | Underlying stock market and status | `tokenContractAddress` | market status incl. `openState` | PG p.6 |
| GET `/api/v1/dex/market/candles` | Candles | `binanceChainId=56`, `tokenContractAddress`, `bar`, `limit` | rows `[open, high, low, close, volume, timestamp_ms, tradeCount]`, oldest first; only periods with trades; `tradeCount` may be null for illiquid tokens (PY/openapi.py) | PG p.6; OA |
| POST `/api/v1/dex/balance/token-balances-by-address` | Balances incl. native BNB | `{"address": <wallet>, "tokenContractAddresses": [{"binanceChainId": "56", "tokenContractAddress": <addr or "">}]}`, ≤ 20 entries | `data[0].tokenAssets[]{tokenContractAddress, balance (decimal-adjusted), rawBalance (smallest unit)}`; zero balances omitted; BNB returned as `0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee` | PG p.6; OA |
| GET `/api/v1/dex/post-transaction/transactions-by-address` | Tx history (nonce derivation) | `address`, `chains=56`, `limit=100` | `data[].transactionList[]{nonce, from[{address, amount}]}`; last 6 months; cursor pagination; **only txs with token transfers — approves are not included** | PG p.6; OA |
| GET `/api/v1/dex/aggregator/quote-and-swap` | Quote + unsigned swap tx | see below | see below | PG p.7; OA |
| GET `/api/v1/dex/aggregator/approve-transaction` | Unsigned approve | `binanceChainId=56`, `tokenContractAddress` (the pay token), `approveAmount` (smallest unit, = this order's `amount`), `vendor` (= quote's `routerResult.vendorName`; required for bStocks) | `data[0]{data (approve calldata), dexContractAddress (spender), gasLimit, gasPrice}`; tx `to` = token contract, `value` = 0 | PG p.7; OA |
| POST `/api/v1/dex/pre-transaction/gas-limit` | Gas estimate for the swap | `{"binanceChainId": "56", "evmTx": {"from": <wallet>, "to": tx.to, "data": tx.data, "value": "<tx.value decimal string>"}}` | `gasLimit` (e.g. `"780552"`) | PG p.7; OA |
| POST `/api/v1/dex/pre-transaction/broadcast-transaction` | Broadcast signed tx | `{"binanceChainId": "56", "signedTransaction": "0x<RLP hex>", "address": <wallet>}` | `txHash`, `orderId` | PG p.8; OA |
| GET `/api/v1/dex/post-transaction/transaction-detail-by-txhash` | Tx result | `binanceChainId=56`, `txHash` | `data[0]{txStatus (success / fail / pending), gasUsed, nonce}`; may be not-found right after broadcast | PG p.8; OA |

**quote-and-swap parameters** (PG p.7):

| Parameter | Value / rule |
|---|---|
| `binanceChainId` | `"56"` |
| `amount` | Pay-token amount, smallest unit |
| `fromTokenAddress` / `toTokenAddress` | Buy: USDT → bStock; sell: bStock → USDT |
| `userWalletAddress` | Wallet address (a read-only address can get quotes) |
| `vendor` | `"LiquidMesh"` — required, case-sensitive; any other value returns `40001` |
| `slippagePercent` | Percentage string, `"1"` = 1%. Pass it **or** `autoSlippage=true`; neither = parameter error. Demos use `"1"` |
| `priceImpactProtectionPercent` | Optional; default 90; lower it to reject shallow pools |

**quote-and-swap response** (PG p.7; PY/examples/03_quote_swap.py; PY/swap_probe.py): top-level `executionMode`, `routerResult`, `tx`.
- `routerResult`: `toTokenAmount` (expected received), `priceImpactPercent`, `vendorName` (pass to approve), `dexRouterList[].dexProtocol{dexName, percent}`, `estimateGasFee`, `router`.
- `tx`: `to` (router contract; example seen `0xB44446b0c8E56988c34f7Ff73Ae904982b5FdDA5`, PY/examples/README.md), `data`, `value`, `gas` (fixed `450000`, often too low), `gasPrice`, `minReceiveAmount` (minimum received under slippage protection), `slippagePercent`.
- "Quotes are free and don't check balances: a transaction built without enough balance fails on-chain, and still costs gas." (PG p.7)

Candle `bar` values accepted (PY/market.py `CANDLE_BARS`; PY/examples/01_signed_get.py): `1s 5s 30s 1m 3m 5m 15m 30m 1h 2h 4h 6h 8h 12h 1d 3d 1w 1M`; other values → `40001`.

Market state (PG p.6): "When `openState` is `False` (here or in `rwa/underlying-market`), the market is closed or trading is halted: don't place orders." No trading hours are given.

---

### K6a. Observed behaviour (read-only probe, 2026-10-07; not in the kit's documents)
Source: `tools/probe_candles.py`, run by SYZ on the team network at 2026-10-07 14:22 UTC; raw responses in `data/probe/` (git-ignored, not committed). Observations, not documented guarantees; re-check if behaviour changes.
- **`candles` `limit` range:** 300 is the largest accepted value; 301 or more → `40001 invalid limit range`.
- **Paging:** the undocumented parameter `after=<ms>` returns bars up to and including that time (`after` = 2026-09-18 03:00 returned 1h bars 2026-09-05 16:00 … 2026-09-18 03:00). `before`, `startTime` and `endTime` returned the latest bars (no paging effect). The full intraday history can therefore be paged back in steps of 300 bars.
- **Daily bars are calendar days (UTC 00:00), weekends included.** Earliest daily bar per token (one call, complete history): NVDAB and TSLAB 2026-06-12 (118 bars), MSFTB 2026-07-01 (88, one gap), SKHYB 2026-07-14 (86), GOOGLB 2026-07-15 (85). Rows are numbers, e.g. NVDAB `[open, high, low, close, volume, timestamp_ms, tradeCount]` = `[239.03, 243.49, 235.45, 239.43, 6815588.56, 1791244800000, 10518]`; the unit of `volume` is not documented.
- **`rwa/underlying-market` requires `binanceChainId=56`** (without it: `40001 Parameter binanceChainId is required`). It returns `statusInfo` plus a `marketData` snapshot: `high52W`, `low52W`, `volumeShares24H`, `marketCap`, `dividendYield`, `latestDividend`, `peRatioTTM`, `pbRatio` (and null `referencePrice`, `avgDailyVolume1Y`, `totalShares`, `turnoverRate`, `amplitude`). No price history.
- **`rwa/tokens`** returned 46 bStocks with `tokenToShareRatio`, `tokenPrice`, `referencePrice` (= tokenPrice ÷ ratio), `volume24H`, `marketCap`, `peRatioTTM`, `tags`, `underlyingName`. Ratios on 2026-10-07: NVDAB 1.00078, GOOGLB 1.00048, MSFTB 1.00131, TSLAB and SKHYB 1.0 (dividends reinvested through the ratio, E-05). All five had `openState: true`, `reasonCode: "TRADING"` at 14:20 UTC (10:20 ET, US session open).

### K6b. Kit-named Skills sources, probed (read-only, 2026-10-07; not in the kit's documents)
Source: `tools/probe_kit_sources.py`, run by SYZ on the team network at 2026-10-07 14:40 UTC; raw responses with URL, status, fetch time and sha256 in `data/probe/kit_sources_*.json` (git-ignored). Endpoints are the ones the Skills call (github.com/binance/binance-skills-hub, read 2026-10-07; MIT); no keys used.
- **`query-token-info`:** `web3.binance.com/bapi/defi/v4/.../market/token/dynamic/info/ai` answers for all five bStock contracts (price plus on-chain trading stats: trade counts by window, holders, Binance-user share). Its candles come from **`dquery.sintral.io/u-kline/v1/k-line/candles`** (a third-party host the Skill calls; params `platform=bsc`, `address`, `interval`, `limit`, `to`). Daily candles: same start dates as the Web3 API and identical closes (median difference 0 bp; max 0.3–26.5 bp, on the still-open current day) — a mirror, not extra history.
- **`binance-tokenized-securities-info`** (`www.binance.com/bapi/defi/...`): the stock list without `type` returns 1,938 items, including our five bStock contracts and, for the same tickers, Ondo (`…on`, type 1) and xStocks (`…x`, type 2) tokens on BSC, Ethereum and Solana. `rwa/dynamic` (v2) answers for bStocks with `stockInfo` (fundamentals snapshot: 52-week range, volume, 30-day average volume, market cap, P/E, P/B, EPS, EV/EBITDA, dividend; `price` null), `tokenInfo` (incl. `sharesMultiplier`, holders) and `statusInfo`. The candle endpoint (`dex/market/token/kline/ai`, `limit` ≤ 300, `startTime`/`endTime` paging) answers for bStocks with the same data as the Web3 API, and for the **Ondo tokens back to 2025-06** (BSC: TSLAon 2025-06-17, NVDAon and GOOGLon 2025-06-24, MSFTon 2025-06-30; SKHYon only 2026-07-10). Ondo daily bars have gaps (NVDAon: 381 bars over ≈ 470 days). Ondo vs bStock daily returns on the overlap: correlation 0.91–0.99, median |difference| 15–29 bp (p95 87–111 bp).
- **`binance` skill (Binance spot, public endpoints, no key):** reachable from the team's Singapore network (HTTP 200, no geo-block). `NVDABUSDT`, `GOOGLBUSDT`, `TSLABUSDT`, `MSFTBUSDT`, `SKHYBUSDT` are all `TRADING`. Daily klines start one day before the on-chain series (NVDAB/TSLAB 2026-06-11, MSFTB 06-30, GOOGLB 07-07, SKHYB 07-13). `data.binance.vision` monthly files download. Closes differ from the on-chain series (a different venue): median 10–20 bp, max 133–434 bp.

- **Desk read of the other four kit-named Skills (2026-10-08; source only, not probed; IDEA-009 §C.1).** From github.com/binance/binance-skills-hub at commit `9960c675387bd27f8866645b83693c1fa87242f6` (2026-09-11), read by a research subagent. `trading-signal`: POST `web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money/ai` with `{chainId: "56", page, pageSize ≤ 100, smartSignalType}`; no contract filter; paged recent signals with `signalTriggerTime` (ms). `crypto-market-rank`: token-rank (POST `…/market/token/pulse/unified/rank/list/ai`, `rankType` 40 = "Stock"), smart-money inflow (POST `…/tracker/wallet/token/inflow/rank/query/ai`), social-hype (GET, text summaries), meme-rank, address-pnl-rank; snapshots over `period` windows; no contract filter. `query-address-info`: GET `…/v3/…/address/pnl/active-position-list/ai?address&chainId=56&offset=0`, by wallet only, snapshot. `query-token-audit`: POST `…/v1/public/wallet-direct/security/token/audit` `{binanceChainId: "56", contractAddress, requestId}`, header `source: agent`; a point-in-time snapshot. No Skill in the hub provides equity news. Probe results below.
- **Four more Skills probed (read-only, 2026-10-08 04:51 UTC = 00:51 ET, US market closed; `tools/probe_kit_sources.py --skills-only`, run by SYZ on the team network; raw in `data/probe/kit_skills_20261008T045132Z*.json`, git-ignored).**
  - `trading-signal`: 56 signals, all trigger times Oct 1–7 (one page; no deeper history), all meme/on-chain tokens; **none of the five bStocks**. Body `contractAddress` returned 0 items (no signals for NVDAB or a filter; either way nothing for us). `pageSize` 150 → `000002 illegal parameter` (not clamped). Not useful for the five names.
  - `crypto-market-rank` token-rank, `rankType` 40 ("Stock"): **all five bStocks listed** on the 24 h board (488 stock tokens, bStocks and Ondo); `keywords: ["NVDAB"]` (or `["NVDA"]`) narrows to NVDAon + NVDAB. Snapshot fields include `price`, `percentChange*`, `volume*` (NVDAB `volume24h` 16,538,999,386; unit not documented), `holders`, `smartMoneyHoldingPercent`, `multiplier` and `ondoStatusInfo` — which for NVDAB read `openState: true, reasonCode: "TRADING"` at 00:51 ET, outside the US regular session (one observation, field name says Ondo; GAP-44 still decides Q-32). The 1 h and 1 m boards' first 200 rows held none of the five. No history: snapshot only.
  - `crypto-market-rank` smart-money inflow (5 m, 1 h, 4 h, 24 h): none of the five. social-hype (24 h): TSLAB, NVDAB and MSFTB appear among 20 tokens, with Binance-generated text summaries (e.g. "Bitcoin Volatility Causes Liquidations, …"); a snapshot, no per-item time. address-pnl-rank: no bStocks among top earners.
  - `query-address-info`: answers by wallet (kit router address: 21 positions; a bStock contract used as an address: 12); fields include `price`, `percentChange24h`, `remainQty`, `lastTxTime`. Team wallet not tested. Snapshot.
  - `query-token-audit`: `hasResult: false`, `isSupported: false` for all five bStocks; identical output a minute later. No coverage.
  - **So:** of the four, only token-rank and social-hype cover our names, both as live snapshots; any history must be logged by us. None is a news source for verified claims (IDEA-009 §C.1).

## K7. Response envelope and error codes

Envelope (OA): `{"code": 0, "msg": "success", "data": ..., "timestamp": 1790408497118, "success": true}`. "Only `code == 0` means success; HTTP 200 can still mean failure" (PG p.4). HTTP 404 has gateway format `{path, status, message, error}` with no `code` (OA).

| Code | HTTP | Cause | Fix | Source |
|---|---|---|---|---|
| `40102` | 401 | Invalid signature (wrong Secret, `/build` missing, clock far off) | Sign exactly the query and body sent, with `/build` | PG p.10; OA |
| `40103` | 401 | Timestamp expired or request replayed | NTP; new timestamp per request | PG p.10 |
| `40104` | — | API Key lacks the permission | Check project/key permissions in the Developer Portal | PG p.10 |
| `40001` | 200 | Parameter error (POST params in URL, missing `binanceChainId`/`vendor`/`slippagePercent`, bad `bar`) | POST params in JSON body; check required params | PG p.10; OA |
| `42900` | 429 | Rate limited | Exponential backoff; cache; fixed-interval polling; never quote in a tight loop | PG p.10, p.18 |
| `50000` | 200 per OA; not stated in PG | Server error, or a non-JSON body (e.g. form-encoded) | `Content-Type: application/json`; retry later | PG p.10; OA |
| (none) | 404 | Wrong endpoint path | Check path | PG p.10; OA |

On-chain / flow failures (PG p.10):

| Symptom | Cause | Fix |
|---|---|---|
| Quote fails | No route, or amount too small | Catch; change token or amount ("0.15 USDT buys worked in our tests") |
| Swap reverts `DeadlinePassed` | Quote expired | Re-quote after the approve, sign and broadcast at once |
| Swap reverts with `gasUsed` close to the limit | Quote `tx.gas` (450000) too low | `/pre-transaction/gas-limit` + 20% |
| Swap reverts otherwise | Approve missing/unconfirmed, price moved beyond slippage, low balance | Wait for approve `success`, check balances; re-quote and sign a new tx, "never resend an old signed one unchanged" |
| Broadcast error mentioning `nonce` | Nonce too low (approve missing from history, or wallet used elsewhere) | nonce + 1 retry, up to 3 times; one agent per wallet |
| No transaction can be sent | No BNB for gas | Keep ≥ 0.002 BNB |
| Hash without `0x` | `.hex()` from `hexbytes` (eth-account) may drop the prefix | Add `0x` before broadcasting or logging |

---

## K8. Trading flow, nonce, gas, confirmation

Flow (PG p.4, p.7–9; OA "Trading flow"):

| Step | Action | Rule |
|---|---|---|
| 1 | Read market data and balances; agent decides | Check `openState` (K6) |
| 2 | Quote via `quote-and-swap` | Quote-only mode (default) stops here |
| 3 | Check pay-token balance ≥ amount and BNB ≥ 0.002 | Quotes don't check balances |
| 4 | `approve-transaction` for the **pay token** (USDT to buy, the bStock to sell), `approveAmount` = exactly this order's amount, `vendor` = quote `vendorName` | API can't read allowances, so approve every trade |
| 5 | Sign locally (`to` = token contract, `value` 0, `gas` = returned `gasLimit`, `gasPrice` = returned `gasPrice`, nonce N), broadcast | Approve keeps the API's `gasLimit` |
| 6 | Wait for confirmation | On failure stop; no swap sent |
| 7 | **Re-quote** | "bStock quotes use RFQ liquidity and expire after about 30 s" |
| 8 | Check re-quote `tx.to` == approve's `dexContractAddress` | Else stop, swap not sent |
| 9 | Swap gas = `max(tx.gas, int(gasLimit × 1.2))` from `POST /pre-transaction/gas-limit`; on estimate failure fall back to `tx.gas` and log a warning | Routes for NVDAB, GOOGLB, SKHYB, MSFTB need about 450k–930k gas vs the fixed 450000; "Unused gas is not charged" |
| 10 | Sign swap locally (legacy `gasPrice`, `chainId` 56, nonce N+1), broadcast | Swap `value` = `int(tx.value or 0)` |
| 11 | Wait for confirmation | See below |
| 12 | `log()` the round; `orders` carries the swap `tx_hash` whatever the outcome | K14 |

**Nonce** (PG p.7–8; OA): "the Open API has no nonce endpoint". N = max(highest `nonce` in `transactions-by-address` where any `from[].address` == wallet, + 1; last locally used nonce + 1); 0 if neither. The history excludes approves, so persist the last used nonce locally ("persist it to a local file in practice so it survives a restart"). On a broadcast error whose message contains `nonce`, re-sign with nonce + 1, at most 3 retries (4 attempts), then fail. Derived nonces desync if anything else sends from the wallet → one agent per wallet. (SKILL.md G-18(j) restricts blind nonce + 1 re-signing for our build.)

**Confirmation** (PG p.8): poll `transaction-detail-by-txhash` every 3 s for up to 120 s. `txStatus == "success"` = success; `fail` = reverted (gas still spent); `pending` or no result = unconfirmed; API errors while polling = not indexed yet. After 120 s the guide's `wait()` returns `"timeout"`: "the transaction may still be mined, so check BscScan before sending another."

**Other limits** (PG p.10–11): no allowance or nonce query (every trade pays for its own approve); **no cancel** — "a swap either fills in full or reverts, and a revert still costs gas. To change an order, re-quote and send a new transaction."

**Signing** (PG p.4): transactions are legacy (`gasPrice`) with `chainId = 56`, signed locally; "the Open API only returns unsigned transactions". Tx hash = keccak256 of the signed raw tx (`"0x" + signed.hash.hex()`); NJ/JV compute it the same way and cross-check the API's `txHash` (NJ/index.mjs, JV/BstocksDemo.java).

**Guide full example amounts** (PG p.9): buy `150_000_000_000_000_000` (0.15 USDT); sell `500_000_000_000_000` NVDAB (0.0005, about $0.12). BNB check `bal.get(BNB_KEY, 0) < 2 * 10**15`.

**Verified live 2026-10-01** with the Python demo's trade path, "all logs received by ai-seeds": one 0.2 USDT buy of each eligible bStock (PG p.11; TG Attachments):

| Symbol | Swap tx |
|---|---|
| NVDAB | `0x3f01ade83d60498f6bea8a2675d7c733b03cfecd1c242bb061a4285d36bf2eff` |
| GOOGLB | `0x05c8d8c0a2a3842262d8bb71452ac27f2891d9f33e4af740d6677476dc98f760` |
| SKHYB | `0x2665ca89d718d0137c6455705e1df6d613b9a375e530350615fd065246f26fdf` |
| TSLAB | `0x0e00a546aa9b48769971cdf17555afff51e2860fd6d30459cd1c34662cd133b7` |
| MSFTB | `0x12d67bb6c5e7901a1083a60de892b37c9268f42f9313530645acc0d60494b4e0` |

View: `https://bscscan.com/tx/<hash>`.

---

## K9. Rate limits

- Exist; the API returns HTTP 429 / code `42900`. "See the Developer Portal or the official documentation for exact quotas." **No numbers in the kit.** (PG p.18)
- Guidance: cache market data, poll at fixed intervals, back off exponentially on 429, never request quotes in a tight loop (PG p.10, p.18).
- **[demo behaviour]** PY/openapi.py: minimum 0.3 s between calls process-wide (`WEB3_MIN_INTERVAL_S`, default `0.3`) — "bursts (e.g. klines for every bStock) trigger 429"; on 429/42900 retries up to 3 times after `Retry-After` or 1 s, 2 s, 4 s (safe for any method: "the request was not processed"); GET retried up to 2 times on network errors/timeouts (re-signed); POST never auto-retried on network errors ("the outcome is unknown"). NJ/JV: no retries at all.

---

## K10. ai-seeds SDK 0.3.0

Purpose: "Your trading agent calls `log()` once at the end of each decision round. The SDK validates, signs and uploads that log, and re-sends it automatically if the upload fails. The organizers use these logs to audit whether each on-chain transaction was decided autonomously by the agent." Python / Node.js / Java, all 0.3.0, "behave the same", no third-party dependencies (PG p.12; SR).

| Item | Value | Source |
|---|---|---|
| Service URL (built in) | `https://api.commonservice.io/ai-seeds-event-log` | PG p.12; SDK client `DEFAULT_BASE_URL` |
| Env `AI_SEEDS_ADDRESS` | Registered wallet; must match `^0x[0-9a-fA-F]{40}$` | SR; SDK validation |
| Env `AI_SEEDS_SECRET` | Organiser-issued signing secret (required) | SR |
| Env `AI_SEEDS_URL` | Optional override of the service URL ("e.g. for a test environment"); also honoured by `manual_push.sh`. Not mentioned in the user READMEs | SDK `client.py`; `manual_push.sh` |
| Install (Python) | `pip install vendor/ai-seeds-sdk-0.3.0/ai_seeds_sdk-0.3.0-py3-none-any.whl` (kit path `ai-seeds-sdk-0.3.0/python/ai_seeds_sdk-0.3.0-py3-none-any.whl`); not on PyPI | PG p.12; PY/requirements.txt |
| Install (Node) | `npm install ./ai-seeds-sdk-0.3.0/nodejs/ai-seeds-sdk-0.3.0.tgz` (not vendored) | PG p.12 |
| Install (Java) | `mvn install:install-file -Dfile=ai-seeds-sdk-0.3.0/java/ai-seeds-sdk-0.3.0.jar -DgroupId=com.aiseeds -DartifactId=ai-seeds-sdk -Dversion=0.3.0 -Dpackaging=jar` (not vendored) | PG p.12 |
| Local files | `.ai-seeds/` under the current directory; one data dir per process | PG p.13 |

**Python API** (`SDK/python/README.md`; wheel source `ai_seeds_sdk/client.py`, `errors.py`, `validation.py`, `wire.py`):

```python
from ai_seeds_sdk import Client, UploadError, ValidationError   # also __version__ == "0.3.0"
client = Client(address=None, mode="realtime", data_dir=".ai-seeds", secret=None,
                *, base_url=None, timeout=15.0, retries=3, backoff=0.5)   # + test-only knobs: sleep, flush_interval, now, wait
client.log(input=..., cot=..., output=..., orders=[...])   # returns None (no event ID exposed)
client.close(timeout=10.0)                                   # optional; background thread is a daemon
```

| Argument | Default | Meaning |
|---|---|---|
| `address` | env `AI_SEEDS_ADDRESS` | Registered wallet; malformed → `ValidationError` at construction; missing → `ValueError` |
| `secret` | env `AI_SEEDS_SECRET` | Required; missing → `ValueError`; never logged |
| `mode` | `"realtime"` | `"realtime"` or `"batch"`; else `ValueError` |
| `data_dir` | `".ai-seeds"` (made absolute) | Holds `spool.jsonl`, `spool.jsonl.uploading`, `batch/` |
| `base_url` | env `AI_SEEDS_URL`, else default URL | Must start `http://` or `https://` |
| `timeout` | 15.0 s | Per realtime request (file uploads use 120 s internally) |
| `retries` | 3 | Retries after the first attempt, transient errors only |
| `backoff` | 0.5 s | Retry n waits `backoff * 2**n` → 0.5, 1, 2 s |

- One `Client` per process; thread-safe, share between threads. Constructor starts a daemon thread `ai-seeds-realtime` (spool flush at start, then every 30 s) or `ai-seeds-batch` (SDK client.py).
- Logger: `logging.getLogger("ai_seeds_sdk")` (warnings on spooling / batch give-up; info on retries).
- Object conversion for `input`/`cot`/`output`/`orders`: `tuple`/`set`/`frozenset` → list; `datetime`/`date`/`time` → ISO 8601; `Decimal`, `UUID` → string; pydantic/`model_dump(mode="json")`, `dict()`, `to_dict()`, dataclass, in that order; `Enum` → member name (int/str-subclass enums give their value per README); dict keys must be `str`/`int`. Rejected (`ValidationError` naming the path): `bytes`, NaN/Infinity, other objects, nesting > 200 levels (SDK/python/README.md; validation.py).

| Exception | When | Attributes / action |
|---|---|---|
| `ValidationError(ValueError)` | Log breaks a rule or exceeds ~8 MB (> 128 chunks of 64 KB); malformed address at construction | `.errors` (list of messages); nothing sent or written |
| `UploadError` | Realtime only: server refused (4xx other than 429) | `.status`, `.code` (server code, or `NETWORK_ERROR` / `HTTP_<status>`), `.message`, `.line_errors`, `.retryable`; not retried, not saved |
| `ValueError` | Construction: address or secret missing, bad `mode`, `retries < 0`, bad URL scheme | Fix config |
| `OSError` | Local file write fails | Check `data_dir` |

Network errors, 5xx and 429 are **never raised** by `log()`: retried, then spooled (K13).

**Node.js** (`SDK/nodejs/README.md`; tgz `index.d.ts`, `lib/client.js`): `import { Client, UploadError, ValidationError, VERSION } from 'ai-seeds-sdk'` (CommonJS `require` also works; ships TS types `LogFields`, `Order`). `new Client({ address, secret, mode: 'realtime'|'batch', dataDir: '.ai-seeds', baseUrl, timeout: 15000, retries: 3, backoff: 500, logger })` (ms units; `logger` = `{warn, info, error}`, default console with info dropped). `await client.log({ input, cot, output, orders })` — the argument may hold **only** these four keys (otherwise `TypeError`); constructor throws `TypeError` for missing address/secret or bad mode. `await client.close(timeout = 10000)` optional; timers and sockets are unref'd so they never keep the process alive. Conversion: `toJSON()`, `Date` → ISO, `BigInt` → decimal string, `Map` (string keys) → object, `Set` → array, class instances → own enumerable props, `undefined` props dropped; rejected: functions, `Symbol`, `Buffer`/`TypedArray`, `Promise` (missing `await`), circular refs, NaN/Infinity, `undefined` in arrays.

**Java** (`SDK/java/README.md`): package `com.aiseeds.sdk`; `Client client = Client.builder().address(..).secret(..).mode(Mode.REALTIME|Mode.BATCH).dataDir(Path).timeout(Duration).retries(int).backoff(Duration).build();` (defaults 15 s, 3, 500 ms); `client.log(input, cot, output, List<Order>)`; `Order.buy(symbol, usdt[, txHash])`, `Order.sell(symbol, qty[, txHash])`, or a `Map` with keys `symbol`, `side`, `amount`, `tx_hash`. Thread-safe, `AutoCloseable`. Unchecked exceptions `ValidationException` (`errors()`), `UploadException` (`status()`, `code()`, `message()`), `IllegalArgumentException`, `UncheckedIOException`. Logger: `System.Logger` `com.aiseeds.sdk`. Maven dependency `<groupId>com.aiseeds</groupId><artifactId>ai-seeds-sdk</artifactId><version>0.3.0</version>`; Gradle `implementation files("libs/ai-seeds-sdk-0.3.0.jar")`.

---

## K11. Log schema and validation rules

Log text = compact JSON (separators `,` `:`, non-ASCII not escaped), UTF-8; stored byte for byte (PR §1):

```json
{"timestamp": 1790242207430,
 "data": {"input": "...", "cot": "...", "output": "...",
          "orders": [{"symbol": "NVDAB", "side": "BUY", "amount": "0.15", "tx_hash": "0x<64 hex>"},
                     {"symbol": "TSLAB", "side": "SELL", "amount": "0.01"}]}}
```

| Field | Rule | Source |
|---|---|---|
| `timestamp` | Filled by the SDK at `log()` call time; integer epoch ms within int64 (`1.0`, `1e12` rejected) | PR §1 |
| `data.input` | Everything given to the agent this round (system prompt, tool definitions, market and position context); required, non-empty; string or JSON | PR §1; PG p.13 |
| `data.cot` | Chain of thought; with several model calls, all reasoning in order; required, non-empty | PR §1 |
| `data.output` | Final output of the round; required, non-empty | PR §1 |
| `data.orders` | Orders the code finally decided to place (after risk checks); required list; `[]` when only holding (empty list allowed only here) | PR §1 |
| `orders[].symbol` | Required non-blank string. **The SDK/server do not check it is one of the five** | PR §1; validation.py |
| `orders[].side` | `BUY` or `SELL` (uppercase; lowercase rejected) | PR §1; LG |
| `orders[].amount` | USDT spent (buy) / shares sold (sell); non-blank string or finite number | PR §1 |
| `orders[].tx_hash` | `^0x[0-9a-fA-F]{64}$`; required once the swap is broadcast; never for approves or unbroadcast orders; missing and `null` both mean "not filled" | PR §1 |

- "Required / non-empty": present and not null; strings not blank (whitespace-only rejected); objects and lists (except `orders`) not empty (PR §1).
- Extra keys inside an order object are not rejected by the Python or Node validators (validation.py; lib/validation.js) **[our note: don't rely on it]**.
- Event ID: unique per log, `^[A-Za-z0-9._:-]{1,128}$`; SDK generates `evt-<ms timestamp>-<12 hex>`; every resend must reuse it (de-dup key) (PR §1).
- Size: ≤ 128 chunks of 65536 bytes (~8 MB) per log; a stored record ≤ 256 KB (PR §6).
- Spool/batch/file line format: `{"eventId":"evt-<ms>-<12 hex>","event":<log text>}` (SDK/examples/README.md; PR §4).

---

## K12. PROTOCOL 2.0 — signing and transport

Base `{base}` = `https://api.commonservice.io/ai-seeds-event-log`. Endpoints (PR intro):
- `PUT {base}/v1/events/{eventId}/chunks/{chunkIndex}` — realtime chunk upload
- `POST {base}/v1/files` — JSONL file upload

**Headers** (PR §2):

| Header | Value |
|---|---|
| `X-AI-Seeds-Timestamp` | Current epoch ms (decimal integer); > ±5 min off → `401 TIMESTAMP_SKEW` |
| `X-AI-Seeds-Nonce` | Fresh per request, 1–128 chars of `[A-Za-z0-9-]`; SDKs use uuid4 hex (32 hex) |
| `X-AI-Seeds-Signature` | HMAC-SHA256, 64 lowercase hex |

SDK also sends `Content-Type`, `Accept: application/json`, `User-Agent: ai-seeds-sdk-python/0.3.0` (or `ai-seeds-sdk-nodejs/0.3.0`) (client.py; client.js).

**String to sign** (PR §2), joined by `\n`, no trailing newline:

```text
METHOD            PUT / POST, uppercase
PATH              starts at /v1/, without /ai-seeds-event-log and without the query string
TIMESTAMP         value of X-AI-Seeds-Timestamp
NONCE             value of X-AI-Seeds-Nonce
lower(ADDRESS)    wallet address, lowercase
sha256_hex(CONTENT)   realtime: raw request body bytes (the whole JSON envelope); file: the file part content only (not the multipart body)
signature = hex(HMAC-SHA256(UTF-8 bytes of the secret string, string_to_sign))   # key is NOT hex-decoded
```

Every retry gets a new timestamp + nonce and is re-signed. Server order of checks (first failure returned): parse (malformed JSON/multipart, oversize → 400/413) → address format (400) → registered (401 `INVALID_CREDENTIAL`) → (file: missing `file` part, 400) → signature (401 `INVALID_SIGNATURE`) → timestamp (401 `TIMESTAMP_SKEW`) → content (400/413) → write (503). So `TIMESTAMP_SKEW` means the signature was correct (PR §2).

**Test vectors** (PR §2; both reproduced locally 2026-10-05):

| Shared input | Value |
|---|---|
| Secret | `5f3a0123456789abcdef0123456789abcdef0123456789abcdef9b2c7e1d4a6f` |
| Timestamp | `1790242207500` |
| Nonce | `0f8e2a9c4b7d4e1f9a3c5b6d7e8f9012` |
| Address (lowercased) | `0xb843d56afc902e37a6433eed534feadc91be71b8` |

*Realtime vector*: `PUT /v1/events/evt-1790242207430-3fa6651c2d4b/chunks/0` with exactly these body bytes (no trailing newline; the `{}` payload is for signature checking only, not a valid log):

```json
{"protocolVersion":"2.0","address":"0xb843d56AfC902e37a6433eEd534Feadc91BE71b8","chunkCount":1,"totalBytes":2,"contentSha256":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a","encoding":"plain","payload":"{}"}
```

- Content sha256 = `ab6216a66effdfc88a6beba78829bff9ee9326767f6acaeaf5fc63f8433c929f`
- Signature = `451191a2b2f2f87eb60a6725fef648e7f3f6ef6efd2a1b8fe2c3cf2ec994ac27`
- (`44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` is sha256 of the 2-byte payload `{}`.)

*File vector*: `POST /v1/files`, file content = this one line followed by one LF:

```json
{"eventId":"evt-1","event":{"timestamp":1790242207430,"data":{"input":"i","cot":"c","output":"o","orders":[]}}}
```

- Content sha256 = `ed9852cbe75ea02d3d44addc87879bd85798fcdf72dc7a7987444b27c8fdb480`
- Signature = `997222a8ba50a845cfb99e479f6f4e38abdf5796a3b0bf2480ae07c4d982c3fc`

**Realtime upload** (PR §3): `PUT {base}/v1/events/{eventId}/chunks/{i}`, `Content-Type: application/json`, body `{"protocolVersion":"2.0","address":<as registered, case kept>,"chunkCount":N,"totalBytes":<bytes of whole log text>,"contentSha256":<sha256 of whole log text, 64 lowercase hex>,"encoding":"plain","payload":<log text or one chunk>}`. Chunking: log text > 65536 bytes split on character boundaries into ≤ 65536-byte UTF-8 chunks; `chunkIndex` from 0; ≤ 128 chunks; `chunkCount`/`totalBytes`/`contentSha256` identical in every chunk. Retry only network errors, 5xx, 429, reusing `eventId` and `chunkIndex`. Success 200 `{"eventId","chunkIndex","status":"STORED","message"}`.

**File upload** (PR §4): `POST {base}/v1/files`, `multipart/form-data`, fields `address` (text) and `file` (JSONL, UTF-8; BOM ignored; LF or CRLF). Each non-empty line `{"eventId":"evt-1790242207430-3fa6651c2d4b","event":{"timestamp":1790242207430,"data":{"input":"...","cot":"...","output":"...","orders":[]}}}`. Whole file validated first; duplicate `eventId` within a file is an error; any invalid line → `400 {"code":"VALIDATION_FAILED","error":"<N> invalid lines","lineErrors":[{"line":3,"error":"..."}]}` (≤ 100 listed; physical line numbers from 1) and nothing stored. Missing `file`, empty file, no logs, invalid UTF-8 → `400 VALIDATION_FAILED` without `lineErrors`. Success 200 `{"lines","events","records","status":"STORED"}`. `503` mid-write → re-upload the whole file. De-duplicated by event ID + chunk index, so re-uploading is harmless. SDK sends the file part as `application/x-ndjson` (wire.py).

**Server error codes** (PR §5); failure body `{"code","error"}` (+ `lineErrors` for files):

| HTTP | `code` | When | Client action |
|---|---|---|---|
| 400 | `VALIDATION_FAILED` | Validation failed, incl. malformed JSON or address | Fix; do not retry |
| 401 | `INVALID_CREDENTIAL` | Address not registered | Register with the organisers |
| 401 | `INVALID_SIGNATURE` | Signing header missing/malformed, signature mismatch, or **no secret registered for the address** | Check secret and string to sign |
| 401 | `TIMESTAMP_SKEW` | > ±5 min off server time | Fix clock |
| 413 | `PAYLOAD_TOO_LARGE` | Stored record > 256 KB; file > 10 MB or > 100000 lines | Split, resend |
| 503 | `WRITE_UNCONFIRMED` | Write not confirmed | Retry (same `eventId`/`chunkIndex`; or whole file) |
| 429, other 5xx, network | — | Transient; body may not match | Back off, retry |

**Limits and server checks** (PR §6):

| Item | Rule | Realtime | File |
|---|---|---|---|
| `address` | `^0x[0-9a-fA-F]{40}$` (400) and registered (401) | yes | yes |
| Event ID | `^[A-Za-z0-9._:-]{1,128}$` | yes | yes |
| Chunk fields | `chunkCount` 1..128, `0 ≤ chunkIndex < chunkCount`, `totalBytes > 0`, `contentSha256` 64 lowercase hex, `encoding == "plain"`, `payload` non-empty | yes | — |
| Integrity | Byte count and sha256 match declared | single-chunk logs | — |
| Log content | K11 rules | single-chunk logs | yes |

Multi-chunk content is validated by the client before sending and by the organisers once all chunks arrive. Limits: chunk ≤ 65536 bytes; log ≤ 128 chunks (~8 MB; realtime 400, file: line error); stored record (chunk + metadata after JSON escaping) ≤ 256 KB → 413; file ≤ 10 MB (10485760 bytes) and ≤ 100000 lines → 413.

---

## K13. Retry, spool, delivery check, batch mode, manual push

**Realtime (default)** (PG p.13–14; SR; client.py):
- `log()` validates, then uploads inside the call (chunked above 64 KB).
- 4xx except 429 → `UploadError`, not retried, not saved.
- Network errors (incl. the 15 s timeout), 5xx, 429 → 3 retries after 0.5, 1, 2 s ("log() can take up to about a minute"); still failing → line appended to `<data_dir>/spool.jsonl`, warning logged, **`log()` returns normally**. If a later chunk of a multi-chunk log fails transiently, the whole log is spooled.
- Background thread: flushes the spool at client start and about every 30 s, including logs left from previous runs; flush renames `spool.jsonl` → `spool.jsonl.uploading`, de-duplicates by eventId, uploads via `POST /v1/files` in ≤ 10 MB / 100000-line parts, puts unsent parts back.
- **Delivery check**: "A normal return from `log()` does not mean the log was delivered." If the data dir has `spool.jsonl` or `spool.jsonl.uploading`, logs are still pending; if neither, everything was delivered (PG p.14).

**Batch** (`mode="batch"` / `mode: 'batch'` / `.mode(Mode.BATCH)`) (PG p.13–14, p.17–18; client.py):
- `log()` validates and appends to `<data_dir>/batch/<UTC date>.jsonl`; no network.
- Push: daily, a random 120–600 s (2–10 min) after 00:00 UTC, the previous UTC day's file is split into `<date>.partN.jsonl` (≤ 10 MB / 100000 lines, de-duplicated) and uploaded; each part deleted on success.
- Any failure (4xx included) retried every 30 min; if still failing at the next 00:00 UTC, retrying stops and a warning prints the manual push command; files stay in `.ai-seeds/batch/`.
- **Deadline**: logs must arrive before **02:00 UTC** the next day, else fills are flagged "fill without log" (PG p.3). The give-up warning "only comes about 22 hours after the deadline" — don't wait for it (PG p.18).
- **Pitfalls**: "a day's file is pushed only by a process that was running that day and is still running at push time" (PG p.13). The push loop starts at the UTC day the `Client` was constructed, so **files from days before the process started are never auto-pushed** (client.py `_batch_loop`). The process must stay alive past 00:00 UTC until the push succeeds (00:02–00:10 UTC, then every 30 min) (PG p.17).

**Manual push** (PG p.14, p.18; `vendor/ai-seeds-sdk-0.3.0/manual_push.sh`): needs `openssl` + `curl`; reads `AI_SEEDS_ADDRESS`, `AI_SEEDS_SECRET`, optional `AI_SEEDS_URL`; splits files over 10,000,000 bytes or 100,000 lines on line boundaries; several files allowed; re-upload harmless. Use it for: batch files after give-up, a process that exited before the push or restarted while retrying, any day not pushed by 02:00 UTC.

```bash
(set -a; . ./.env; set +a; sh vendor/ai-seeds-sdk-0.3.0/manual_push.sh .ai-seeds/batch/2026-09-25.part1.jsonl)
```

Raw curl equivalent: PR §4 (in `docs/official/kit/PROTOCOL.md`). The SDK's warning prints the kit path `ai-seeds-sdk-0.3.0/examples/manual_push.sh`; in this repo use the vendored path.

---

## K14. Logging requirements (what must be logged)

| # | Requirement | Source |
|---|---|---|
| L1 | A **round** = "one complete agent run, from receiving its input to producing a strategy, however many model calls it makes". Log once per round | PG p.13 |
| L2 | Log every round, including hold-only rounds (`orders=[]`) | PG p.3, p.9, p.17 |
| L3 | `orders` = orders the code **finally decided to place** after risk checks and adjustments, "not necessarily what the model output" | PG p.13 |
| L4 | Once a swap is broadcast, its `tx_hash` goes in `orders` whatever the outcome (success, revert, unconfirmed/timeout). "every broadcast swap must appear in some log" | PG p.9, p.13 |
| L5 | Never the approve's hash; approves are not orders | PG p.3, p.9 |
| L6 | Orders never broadcast (failed, blocked by risk controls, quote-only) are listed **without** `tx_hash` | PG p.13; LG |
| L7 | Multi-call round (tool loop): `input` = agent input before the loop (not modified inside it); `cot` = reasoning of every call joined in order; `output` = output of the last call; one log | PG p.15–16 |
| L8 | `output` = everything except reasoning (text and tool calls); don't pass encrypted reasoning blobs (Anthropic `redacted_thinking`, OpenAI `encrypted_content`) | PG p.15 |
| L9 | Never log API secrets, private keys, mnemonic, `AI_SEEDS_SECRET` | PG p.3, p.17 |
| L10 | Catch `UploadError` and `ValidationError` from `log()` | PG p.17 |
| L11 | Timestamp and event ID are generated by the SDK; don't pass them | PG p.13 |
| L12 | Model/framework objects may be passed directly (converted to JSON) | PG p.13 |
| L13 | Consequence of a missing log: fills from the previous day are checked daily; a fill whose `tx_hash` is in no log is "flagged for manual review, because it cannot be shown to come from your agent". Late batch logs → fills "first flagged as 'fill without log'". No further penalty stated | PG p.3, p.18 |
| L14 | Demo, example, `--offline` and quote-only runs **upload real logs** under the wallet, visible to the auditors | PG p.3, p.15; SDK/examples/README.md |

Conventions in organiser reference code (not stated rules; SKILL.md F-106): rule-based demos put a plain statement of the rule and its inputs in `cot`; aborted live rounds log the order without `tx_hash` with the reason in `output` (`"<label> aborted: <reason>"`); example logs carry `"example": true` or an `example-java-` prefix in `input`; placeholder `tx_hash` values are never uploaded; for LLM rounds `input` is the full model request (`SDK/examples/events.jsonl`). `SDK/examples/events.jsonl` has 4 sample rounds: buy on-chain; hold; buy + sell both on-chain; risk-corrected sell 0.0004 → 0.00013 that failed (no `tx_hash`).

---

## K15. Model providers: where `cot` comes from

Common pattern in `SDK/examples/models/*.py`: `build_request()` → call → `extract()` returns `(input, cot, output, decision)` → `execute(decision)` (risk control; `_shared.py` caps buys at `MAX_BUY_USDT = 0.20`) → `client.log(...)`. `--offline` builds two sample responses with the provider SDK types and **really uploads two demo logs**. Install only the provider used: `pip install anthropic openai google-genai` (DeepSeek uses the `openai` package). Env: `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` / `GEMINI_API_KEY` (PG p.15; `SDK/examples/models/README.md`). Docs links "checked 2026-09".

| Provider (file) | Request settings in the example | `cot` source | Must set | Source |
|---|---|---|---|---|
| Anthropic Messages (`anthropic_example.py`) | `model "claude-sonnet-5"`, `max_tokens 16000`, `thinking={"type":"adaptive","display":"summarized"}` | `thinking` of `type="thinking"` blocks (a summary) | Claude 4.7+: adaptive + `display:"summarized"` (else empty text; `{"type":"enabled","budget_tokens":N}` returns 400). Claude 4.6: `{"type":"adaptive"}` (budget form still works). ≤ 4.5: `{"type":"enabled","budget_tokens":N}` | PG p.15; file |
| OpenAI Responses (`openai_example.py`) | `model "gpt-6-astra"`, `instructions`, `input`, `tools` (function, `strict: True`), `reasoning={"effort":"medium","summary":"auto"}` | `summary[].text` of `type="reasoning"` output items | `reasoning={"summary":"auto"}`; Chat Completions returns no reasoning; org verification may be needed | PG p.15; file |
| DeepSeek, OpenAI-compatible (`deepseek_example.py`) | `base_url "https://api.deepseek.com"`, `model "deepseek-flash"`, `reasoning_effort "high"`, `extra_body={"thinking":{"type":"enabled"}}` | `choices[0].message.reasoning_content` (full chain, not a summary) | Thinking on by default for `deepseek-flash` / `deepseek-v4-pro`; read via `getattr`; in tool loops send `reasoning_content` back unchanged; `temperature` ignored in thinking mode | PG p.15; file |
| Gemini `generateContent` (`gemini_example.py`) | `model "gemini-3.8-flash"`, `GenerateContentConfig(system_instruction, tools, thinking_config=ThinkingConfig(include_thoughts=True))` | `text` of parts with `thought=True` (summary) | `include_thoughts=True`; `thought_signature` bytes become base64 via `model_dump(mode="json")`; Interactions API extraction differs | PG p.15; file |

Minimal extraction (from the example files):

```python
# Anthropic
cot = "\n\n".join(b.thinking for b in resp.content if b.type == "thinking")
output = [b for b in resp.content if b.type not in ("thinking", "redacted_thinking")]
# OpenAI Responses
cot = "\n\n".join(s.text for it in resp.output if it.type == "reasoning" for s in it.summary)
output = [it for it in resp.output if it.type != "reasoning"]          # never the whole response (encrypted_content)
# DeepSeek
msg = resp.choices[0].message
cot = getattr(msg, "reasoning_content", None)
output = {"content": msg.content, "tool_calls": msg.tool_calls}       # not the whole message (duplicates cot)
# Gemini
parts = resp.candidates[0].content.parts or []
cot = "\n\n".join(p.text for p in parts if p.thought and p.text)
output = [p.model_dump(mode="json", exclude_none=True) for p in parts if not p.thought]
```

Tool loop (one round, Anthropic; PG p.15–16): keep `agent_input` unchanged, append `{"role":"assistant","content":response.content}` and the tool_result message each turn, collect `thoughts` per call, break when `stop_reason != "tool_use"`, then `client.log(input=agent_input, cot="\n\n".join(thoughts), output=<last call minus thinking>, orders=orders)`; the order tool appends the orders the code finally decided to `orders`. Node model SDKs return plain objects that can be passed as-is.

---

## K16. Demo code map and behaviours we must NOT copy

**Python demo `PY/`** (full-featured; Python ≥ 3.10; deps `eth-account>=0.13.1`, `requests>=2.31.0`, `python-dotenv>=1.0.0`, `anthropic>=1.6.0`, `fastapi>=0.110.0`, `uvicorn>=0.29.0`; ai-seeds wheel installed separately) (PY/README.md, PY/requirements.txt):

| File | Role |
|---|---|
| `config.py` | Loads `.env` from the project dir (existing env wins); constants below |
| `openapi.py` | Signed GET/POST; `RECV_WINDOW "15000"`; `TIMEOUT (5, 20)`; retries per K9; `OpenAPIError` on HTTP ≥ 400 or `code != 0` |
| `market.py` | `prices`, `price`, `klines` (bar validated), `market_data` (24h change/high/low from 30 × 1h klines), `indicators` (ma6, ma12, ma_all, pct_from_high/low, momentum_pct), `balances` (BNB, USDT, held bStocks), `position` (avg cost from `trades.json`), `rich_snapshot` (all 5 assets + focus klines + indicators + last 10 ledger trades + wallet; data errors reported, not fatal) |
| `trade.py` | `quote`; `trade(side, symbol, amount|"all", broadcast)`: amount × 10^config decimals; live: balance check → quote → arm-file check → BNB ≥ 0.002 → disarm → approve → wait → re-quote → spender check → gas ×1.2 → swap → wait; returns `status` `success` / `reverted` / `unconfirmed/timeout`; on success appends to `trades.json` (quoted expected amount, not the fill); `check_range` notional within [MIN, MAX] (sell = shares × current price); `check_armed` / `disarm` |
| `wallet.py` | `Wallet` (mnemonic > private key > read-only address); `balances_raw` (20 per call); `ensure_approve`; `send_swap_tx`; `next_nonce` (history + `logs/.last_nonce` JSON `{address: nonce}`, written only after confirmation); `_sign_and_send` (nonce + 1 up to 3 retries; hash from API `txHash` else signed hash, `0x` ensured); `wait_receipt` (3 s poll, 120 s, raises `TimeoutError`) |
| `server.py` | FastAPI: `GET /health`, `/balance`, `/price?symbol`, `/market?symbol`, `/position?symbol`, `/klines?symbol&interval&limit`, `/analysis?focus&interval&limit`; `POST /quote` and `POST /trade` (`{side, symbol, amount, reason, confirm}`; defaults symbol `NVDAB`, amount `"all"`; `/trade` needs `confirm=true`); notional out of range → 422 |
| `strategy_agent.py` | Prefetch `/analysis` → Anthropic `client.beta.messages.tool_runner` with tool `place_order` → `/quote` (60 s) or `/trade` (300 s) → write `logs/YYYYMMDD-HHMMSS.log` → `log_upload.push_with_retry`. Thinking: models < 4.7 use `budget_tokens` + beta `interleaved-thinking-2025-05-14`; newer use adaptive + summarized, `max_tokens 16000`. CLI `--interval`, `--max-trades` (auto-arms each round when LIVE; stops after max_trades × 3 rounds) |
| `log_upload.py` | Parses the demo's text log into input/cot/output/orders; SDK `data_dir` `logs/.ai-seeds`; `--dry`, `--jsonl` (deterministic event IDs), re-send named files |
| `swap_probe.py` | Quote-only CLI `--symbol --address --amount`; verifies token list; writes `logs/swap_probe_last.md` |
| `tokenlist.py` | Address/decimals check vs the official token list (K3) |
| `examples/01..04`, `web3_auth.py` | Signed GET walkthrough; signed POST + `--show-errors`; quote only (`--side --symbol --amount --address`); log upload (`--dry`; real run uploads one order without hash, `"example": true`, data dir `logs/.ai-seeds-example`) |

`config.py` defaults: `BSC_CHAIN_ID 56`; `AGENT_MODEL "claude-sonnet-5"`; `THINKING_BUDGET 1024`; `TRADING_LIVE "0"`; `TRADE_MIN_USDT 0.1`; `TRADE_MAX_USDT 0.2`; `ARM_FILE .live_armed`; `ARM_WINDOW_SECONDS 300`; `SERVICE_URL http://127.0.0.1:8000`; `AI_SEEDS_UPLOAD "1"`; `LOG_DIR logs/`; `LEDGER_FILE trades.json`; `DEFAULT_TARGET_SYMBOL NVDAB`; `DEFAULT_PAY_AMOUNT "0.15"`; `DEFAULT_SLIPPAGE_PERCENT "1"`; `DEFAULT_VENDOR "LiquidMesh"`; `MIN_BNB_FOR_GAS 0.002`; env also `LLM_API_KEY`, `LLM_BASE_URL`, `WALLET_ADDRESS`, `WEB3_MIN_INTERVAL_S`. Live run: `touch .live_armed && TRADING_LIVE=1 .venv/bin/python strategy_agent.py` (arm file valid 5 min, single use) (PG p.3; PY/config.py).

**Node.js demo `NJ/index.mjs`** (Node ≥ 20.6, `npm start` = `node --env-file=.env index.mjs`; deps `ai-seeds-sdk` (file: tgz) + `ethers ^6.17.0`): one round, no LLM, no service. Rule: buy 0.15 USDT NVDAB if last 1h close < mean of 24 × 1h closes, else HOLD (dry run) / **SELL 0.0005 NVDAB (live — every live run trades)**. Constants `BUY_WEI 150000000000000000`, sell `500000000000000`, `MIN_BNB_WEI 2000000000000000n`, 3 nonce retries, 3 s poll, 120 s wait, 15 s request timeout. Enforces signer == `AI_SEEDS_ADDRESS`. No `X-OC-RECV-WINDOW`, no retries. Nonce file `.last_nonce` (JSON map). Reusable helpers: `openApi`, `quote`, `loadSigner`, `balances`, `nextNonce`, `approveTx`, `swapTx`, `signAndSend`, `waitTx`.

**Java demo `JV/BstocksDemo.java`** (JDK ≥ 17, Maven; `jackson-databind 2.19.4`, `org.web3j:crypto 4.14.0`, `exec-maven-plugin 3.6.4`; run `(set -a; . ./.env; set +a; mvn -q compile exec:java)`): same rule and amounts as NJ; wallet check before sending; `.last_nonce` is a **plain integer** (not per address); `nextNonce` checks only `from[0]`; timeout returns the string `"not confirmed within 120 s"`; no RECV window, no retries; HTTP connect 5 s, request 15 s.

**Behaviours we must NOT copy** [our note]:

| # | Behaviour | Where | Why |
|---|---|---|---|
| N1 | Rounds that end without a log: `SnapshotError` aborts the round with no log; any exception in `run_once` after `place_order` broadcast a swap (LLM/tool-runner error) skips both the log file and the upload | PY/strategy_agent.py | Breaks L2/L4 → "fill without log" |
| N2 | Market-data or dry-run-quote failure throws before `client.log()` | NJ/index.mjs | Breaks L2 |
| N3 | No check that the signing wallet == `AI_SEEDS_ADDRESS`; `AI_SEEDS_ADDRESS` silently falls back to the wallet address | PY/wallet.py, PY/log_upload.py | Breaks R8 |
| N4 | Decimals hard-coded to 18 | all demos | PG p.4: take decimals from the API |
| N5 | `openState` / `rwa/tokens` / `underlying-market` never called | all demos | PG p.6: don't order when closed/halted |
| N6 | Log timestamps parsed as fixed UTC+8 ("Beijing time") | PY/log_upload.py `CST` | Wrong outside UTC+8; use UTC |
| N7 | Incompatible nonce files (PY `logs/.last_nonce` JSON map; NJ `.last_nonce` JSON map; JV `.last_nonce` integer) | all demos | Desyncs if tools mix |
| N8 | Live mode always trades (HOLD becomes SELL) | NJ, JV | Not a strategy |
| N9 | Ledger records quoted expected amount, not the actual fill | PY/trade.py `_log_trade` | Wrong cost basis |
| N10 | `--max-trades` auto-creates the arm file each round | PY/strategy_agent.py | Defeats the manual arm |
| N11 | Blind nonce + 1 re-sign on any error containing "nonce" | all demos, PG p.8 | SKILL.md G-18(j) |
| N12 | Text-log parsing to build ai-seeds fields after the fact | PY/log_upload.py ("only understands the demo agent's log format") | Log structured fields directly in-process |

---

## K17. Kit defects and ambiguities

| # | Issue | Evidence |
|---|---|---|
| D1 | **Stale `SHA256SUMS`**: 27 hash lines for 20 files; only 3 of the 20 files verify (`PROTOCOL.md`, `examples/models/README.md`, `java/ai-seeds-sdk-0.3.0.jar`); `PROTOCOL.md`, `README.md`, `examples/README.md`, `examples/models/README.md`, `java/README.md`, `nodejs/README.md`, `python/README.md` each have two different hash lines; wheel, tgz, all examples and READMEs fail. The unpacked kit folder is byte-identical to `ai-seeds-sdk.zip` → organiser packaging error. Our reference hashes: `vendor/ai-seeds-sdk-0.3.0/README.md`, `docs/official/kit/README.md` | `sha256sum -c SHA256SUMS`, 2026-10-05 |
| D2 | **NJ `package-lock.json` integrity mismatch** for the SDK tgz: lock `sha512-3wktx3XKMobfIiRKNlAVCVr1twfMOLkR9fkBL2wO0Rcd0eBo6SZC2mWYdIpZs7KPzLZ1MOGM9keFRHZSiibGIw==`, shipped tgz `sha512-+OFqelF/EnhzRFhVbFMJwLjj4+JqbcEH+djDHw8Em9pXUDTwR1GP6LoiLS11YFgUe6WM60Yq8QyuKJPdvvvSVg==` → `npm ci` fails `EINTEGRITY`; workaround (NJ README) `npm install ./ai-seeds-sdk-0.3.0/nodejs/ai-seeds-sdk-0.3.0.tgz` | computed 2026-10-05 |
| D3 | **Zip name**: SDK README, demo READMEs, TG and code comments say `ai-seeds-sdk-0.3.0.zip`; the shipped file is `ai-seeds-sdk.zip` (PG p.1 uses the shipped name). The three demo zips equal their folders (no extra files) | kit listing |
| D4 | `50000` HTTP status: OA says 200; PG gives none. `40103`, `40104` only in PG/TG | PG p.10; OA |
| D5 | PG p.5 says "the Node.js / Java demos exit otherwise" (wallet mismatch) — true; the Python demo does not check (N3) | PY/wallet.py |
| D6 | PG says check `openState` and take decimals from the API; no demo does either (N4, N5) | — |
| D7 | Timeout semantics differ: PG `wait()` returns `"timeout"`; PY raises `TimeoutError`; JV returns `"not confirmed within 120 s"`; NJ returns `'timeout'` | code |
| D8 | PG p.6 endpoint table lists history params as `address`, `limit`, while the text above it says `chains=56` is also passed (all code passes `chains=56`) | PG p.6 |
| D9 | PG p.5 "Python: `pip install requests eth-account`" but the guide code also imports `eth_utils` (installed with eth-account) | PG p.5 |
| D10 | Relative links in the official docs point into the kit layout and do not resolve in `docs/official/kit/` | copies |
| D11 | No licence is stated for the SDK; no confidentiality or no-redistribution statement anywhere in the kit (checked 2026-10-05); demo READMEs allow "modify and reuse" | all files |
| D12 | SDK accepts any non-blank `symbol` and extra order keys; enforcement of the five symbols is our job | validation.py |

---

## K18. What the kit does NOT cover

- Event organisers' identity, contacts, communication channels.
- Timeline: dates, onboarding, development vs final phases, trading window, finals period, submission deadlines (only the daily 02:00 UTC batch-log deadline exists).
- Scoring / judging criteria and weights, valuation source and instant, prizes, eligibility, deliverables, disqualification conditions, incident policy.
- Registration procedure, version-event / repo-registration / declaration procedures.
- Wallet funding source and amounts, BNB provision (team statement in SKILL.md F-107; open as Q-03).
- Rate-limit quotas (Developer Portal), trading hours (only `openState`/`nextOpenTime`), minimum order size, fees beyond gas, maximum order size (0.1–0.2 USDT is a demo default).
- Whether the final wallet gets a new `AI_SEEDS_SECRET` (SKILL.md Q-35).
- How a gas top-up swap (USDT → native BNB) should appear in `orders`: BNB is not a bStock and the kit gives no convention (SKILL.md Q-08).
- How a wallet that starts with 0 BNB pays for its first transaction (the top-up swap itself needs BNB for gas, PG p.5; SKILL.md Q-03), and whether BNB held counts in equity.
- Whether the eligible list is frozen for the run, and how an instrument is valued if it becomes ineligible (Q-19); corporate actions (dividends, splits), unsolicited tokens and balance-only changes (Q-20).
- Minimum-activity requirements or the ranking of zero/low-activity teams (Q-17).
- What counts as manual intervention (operator HALT/restart), and the upload deadline after a material incident (Q-09, Q-14).
- KYC and jurisdiction: nothing on identity verification or which countries may use the API (Q-12, Q-26).
- How logs are reviewed beyond the `tx_hash` match (what makes a decision "autonomous").

Verbatim originals: `docs/official/kit/` (Guide PDF, `bstocks-trading-guide.md`, `web3-open-api.md`, `logging.md`, `ai-seeds-sdk-README.md`, `PROTOCOL.md`). Vendored SDK: `vendor/ai-seeds-sdk-0.3.0/`.

# ai-seeds SDK

Your trading agent calls `log()` once at the end of each decision round. The SDK validates, signs and uploads that log, and re-sends it automatically if the upload fails. The organizers use these logs to audit whether each on-chain transaction was decided autonomously by the agent.

Available for Python (≥ 3.9), Node.js (≥ 18) and Java (≥ 17). All three are version 0.3.0, behave the same, and have no third-party dependencies.

## Install

The organizers distribute `ai-seeds-sdk-0.3.0.zip`. Unzip it, then run the command for your language from the directory where you unzipped it:

```bash
# Python
pip install ai-seeds-sdk-0.3.0/python/ai_seeds_sdk-0.3.0-py3-none-any.whl

# Node.js
npm install ./ai-seeds-sdk-0.3.0/nodejs/ai-seeds-sdk-0.3.0.tgz

# Java: installs into your local Maven repository as com.aiseeds:ai-seeds-sdk:0.3.0
mvn install:install-file -Dfile=ai-seeds-sdk-0.3.0/java/ai-seeds-sdk-0.3.0.jar \
    -DgroupId=com.aiseeds -DartifactId=ai-seeds-sdk -Dversion=0.3.0 -Dpackaging=jar
```

For Java with Gradle, or without a build tool, reference the jar directly; see [java/README.md](java/README.md).

## Quick start

Set two environment variables:

```bash
export AI_SEEDS_ADDRESS=0x<your wallet address>                # your registered wallet address
export AI_SEEDS_SECRET=<secret issued at registration>         # never commit it to a repository or write it to logs
```

Logs are uploaded to the service address `https://api.commonservice.io/ai-seeds-event-log`, which is built into the SDK.

Call `log()` once at the end of each decision round:

```python
from ai_seeds_sdk import Client

client = Client()                              # reads the two variables above
client.log(input=request, cot=thinking, output=answer,
           orders=[{"symbol": "NVDAB", "side": "BUY", "amount": "0.15", "tx_hash": swap_hash}])
```

```js
import { Client } from 'ai-seeds-sdk';         // CommonJS: const { Client } = require('ai-seeds-sdk')

const client = new Client();                   // reads the two variables above
await client.log({ input: request, cot: thinking, output: answer,
                   orders: [{ symbol: 'NVDAB', side: 'BUY', amount: '0.15', tx_hash: swapHash }] });
```

```java
Client client = Client.builder().build();      // reads the two variables above
client.log(request, thinking, answer, List.of(Order.buy("NVDAB", "0.15", swapHash)));
```

Create only one `Client` per process. Local files go under `.ai-seeds/` in the current directory; do not share this directory between processes.

## What to log

A round is one complete agent run, from receiving its input to producing a strategy, however many model calls it makes. Log once per round.

| Field | Contents |
|---|---|
| `input` | Everything given to the agent this round, e.g. system prompt, tool definitions, market and position context |
| `cot` | The chain of thought; with several model calls, all the reasoning in order |
| `output` | The final output of this round |
| `orders` | The orders your code **finally decided to place** this round (after risk checks and other adjustments; not necessarily what the model output); an empty list when only holding |
| `orders[].symbol` | Stock symbol, e.g. `NVDAB` |
| `orders[].side` | `BUY` or `SELL` |
| `orders[].amount` | USDT spent for a buy, number of shares sold for a sell; string or number |
| `orders[].tx_hash` | The swap's transaction hash, `0x` + 64 hex digits |

- Everything except `tx_hash` is required. `input` / `cot` / `output` must not be empty and may be a string or JSON. The SDK generates the timestamp and event ID.
- Objects returned by model providers and agent frameworks can be passed as they are; the SDK converts them to JSON. The supported types are in each language's docs.
- **`tx_hash`**: required once the swap has been broadcast, whether it then succeeds, reverts or is still unconfirmed; never used for approve transactions or for orders that never went on-chain. The audit matches `tx_hash` against on-chain transactions, so every broadcast swap must appear in some log.
- Orders that were never broadcast (the order failed, or risk controls blocked it) still go in `orders`, just without `tx_hash`.

## Two modes

```text
log()  validates locally; raises ValidationError if invalid
 ├─ realtime (default) ─▶ upload now ──fails──▶ .ai-seeds/spool.jsonl ──▶ re-sent in the background
 └─ batch ──────────────▶ .ai-seeds/batch/<UTC date>.jsonl ──▶ pushed after the next 00:00 UTC
```

| | `realtime` (default) | `batch` |
|---|---|---|
| When data is sent | Uploaded inside `log()`; logs over 64 KB are chunked automatically | Every day, a random 2–10 minutes after 00:00 UTC, the previous day's file is pushed |
| On failure | Retried, then saved locally and re-sent in the background; some errors raise `UploadError` (see below) | Any failure (4xx included) is retried every 30 minutes; if it still fails at the next 00:00 UTC, retrying stops and the files stay on disk |
| Process | No requirement | Must keep running: a day's file is pushed only by a process that was running that day and is still running at push time |
| How to enable | Default | Python `mode="batch"`, Node.js `mode: 'batch'`, Java `.mode(Mode.BATCH)` |

## Errors and automatic re-sending

- **Validation errors**: `log()` raises `ValidationError` immediately; nothing is sent or written.
- **4xx (except 429)**: in realtime mode, not retried and not saved; `log()` raises `UploadError`. The usual ones are 401: `INVALID_CREDENTIAL` (address not registered; register with the organizers), `INVALID_SIGNATURE` (check `AI_SEEDS_SECRET`; if it is right, the organizers may not have set up a secret for your address yet), `TIMESTAMP_SKEW` (your clock is more than ±5 minutes off).
- **Network errors (including the 15-second timeout), 5xx, 429**: 3 retries (after 0.5, 1 and 2 seconds, so `log()` can take up to about a minute); if still failing, the log is saved to `.ai-seeds/spool.jsonl` and `log()` returns normally. In the background the SDK re-sends it at startup and about every 30 seconds after that, including logs left over from a previous run.
- **After batch mode gives up**: the SDK prints a warning with the push command, and the files stay in `.ai-seeds/batch/`. Push them with [examples/manual_push.sh](examples/manual_push.sh) (it uses the two variables above and also uploads to `https://api.commonservice.io/ai-seeds-event-log`; you can pass several files, and uploading again is harmless):

  ```bash
  sh ai-seeds-sdk-0.3.0/examples/manual_push.sh .ai-seeds/batch/2026-09-25.part1.jsonl
  ```

  Push the files this way too if the process exits before the push or restarts while retrying; the script splits files that exceed the limits, so a whole-day `<date>.jsonl` can be passed directly. Without the script, upload directly with curl as shown in section 4 of [PROTOCOL.md](PROTOCOL.md).

> ⚠️ **A normal return from `log()` does not mean the log was delivered**: it may be waiting in the spool. If the data directory (default `.ai-seeds/`) has `spool.jsonl` or `spool.jsonl.uploading`, some logs are still to be re-sent; if it has neither, everything was delivered.

In Java the two exceptions are `ValidationException` and `UploadException`.

## Signing

The SDK signs every request with HMAC-SHA256 using `AI_SEEDS_SECRET`; you do not need to do anything. Enable time sync: your clock must be within ±5 minutes of the server's. The SDK never needs your wallet's private key or seed phrase; guard the signing secret like a password. Rules and test vectors are in [PROTOCOL.md](PROTOCOL.md).

## More

- [python/](python/README.md), [nodejs/](nodejs/README.md), [java/](java/README.md): constructor options, `log()` usage, the types converted automatically
- [PROTOCOL.md](PROTOCOL.md): the protocol for writing your own client: log format, signing, endpoints, validation rules
- [examples/](examples/README.md): sample logs, upload examples in three languages, the manual push script
- [examples/models/](examples/models/README.md): how to get `input` / `cot` / `output` from each model provider (Anthropic, OpenAI, DeepSeek, Gemini)

# ai-seeds log upload

Competition requirement: **the agent uploads one log for every round it runs**, including rounds where it only holds and places no order. The audit traces each on-chain transaction's `tx_hash` back to the log of the corresponding round; fills with no matching log are flagged.

## Installation and configuration

```bash
.venv/bin/pip install ai-seeds-sdk-0.3.0/python/ai_seeds_sdk-0.3.0-py3-none-any.whl   # in the zip distributed by the organizers
```

| Variable | Description |
|---|---|
| `AI_SEEDS_ADDRESS` | Registered team wallet address |
| `AI_SEEDS_SECRET` | Signing secret, issued by the organizers at registration; do not commit it or write it to logs |

The SDK also comes in Node.js and Java versions, in the same zip.

## Usage

```python
from ai_seeds_sdk import Client

seeds = Client()        # reads the environment variables above; one per process

# call once at the end of each round
seeds.log(
    input=...,          # all input of this round: prompts, market data, positions, etc.
    cot=...,            # the reasoning of this round (with several model calls, concatenated in order)
    output=...,         # the final output of this round
    orders=[            # the orders finally executed; [] when holding
        {"symbol": "NVDAB", "side": "BUY", "amount": "0.15", "tx_hash": "0x..."}, # on-chain: the swap hash
        {"symbol": "TSLAB", "side": "SELL", "amount": "0.0003"},                  # not on-chain: no tx_hash
    ],
)
```

Rules:

- `input` / `cot` / `output` are required and must not be empty; you can pass strings, dicts or the objects your model SDK returns directly.
- `orders` holds the orders your code finally executed, not the model's raw output. `side` is `BUY` / `SELL`; `amount` is the USDT spent for a buy, or the quantity sold for a sell.
- Once a swap is broadcast, include its `tx_hash`, whether it succeeded, failed or is still unconfirmed; never the approve's. The format is `0x` + 64 hex digits (some libraries return the hash without `0x`; add it).
- The SDK generates the timestamp and event ID.
- Realtime upload by default: network errors, 5xx and rate limiting are retried automatically; if it still fails, the log is saved locally and resent in the background every 30 seconds, without interrupting the agent. Data format errors raise an exception immediately.

Full example: `examples/04_log_upload.py` (`--dry` only validates locally and sends nothing).

## How this project does it

- At the end of each round, `strategy_agent.py` writes the run log to `logs/`, then uploads it by calling `log()` through `log_upload.py`. Set `AI_SEEDS_UPLOAD=0` to turn off automatic upload.
- **`log_upload.py` only understands the demo agent's log format.** Once you switch to your own agent, just call `log()` in each round; you won't need it.
- Resend: `.venv/bin/python log_upload.py <logfile>`; validate only, without uploading: `--dry`.

## Common errors

| Error | Fix |
|---|---|
| 401 `INVALID_SIGNATURE` | `AI_SEEDS_SECRET` and `AI_SEEDS_ADDRESS` do not match |
| 401 `TIMESTAMP_SKEW` | Local clock is off by more than ±5 minutes; enable time sync |
| `ValidationError` | Invalid field; fix it according to the error message (e.g. `side` written in lowercase, `tx_hash` missing `0x`) |

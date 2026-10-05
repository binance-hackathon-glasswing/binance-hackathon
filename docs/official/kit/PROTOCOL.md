# ai-seeds Log Upload Protocol 2.0

The SDK already implements everything here; read on if you are writing your own client or debugging signatures. The service address is `https://api.commonservice.io/ai-seeds-event-log`; `{base}` below stands for it, and the endpoint paths are appended to it. Every request must be signed (Section 2); the signed path starts at `/v1/` and excludes the `/ai-seeds-event-log` prefix.

- `PUT {base}/v1/events/{eventId}/chunks/{chunkIndex}`: realtime upload of one chunk of a log (Section 3)
- `POST {base}/v1/files`: upload a JSONL file, one log per line (Section 4)

## 1. Log format

One log = one decision round: one complete agent run, from receiving its input to producing a strategy, however many model calls it makes. The log text is the JSON of the object below, encoded as UTF-8; the SDK produces compact JSON (separators `,` and `:`, non-ASCII characters not escaped). The service stores the text byte for byte and does not modify it.

```json
{"timestamp": 1790242207430,
 "data": {"input": "...", "cot": "...", "output": "...",
          "orders": [{"symbol": "NVDAB", "side": "BUY",  "amount": "0.15", "tx_hash": "0x9906…(64 hex digits)"},
                     {"symbol": "TSLAB", "side": "SELL", "amount": "0.01"}]}}
```

| Field | Meaning and rules |
|---|---|
| `timestamp` | Time of the `log()` call, filled by the SDK; integer milliseconds within 64-bit range (`1.0` and `1e12` count as decimals and are rejected) |
| `data.input` | Everything given to the agent this round, e.g. system prompt, tool definitions, market and position context; required, non-empty, string or JSON |
| `data.cot` | The chain of thought; with several model calls, all the reasoning in order; required, non-empty, string or JSON |
| `data.output` | The final output of this round; required, non-empty, string or JSON |
| `data.orders` | The orders your code finally decided to place this round (after risk checks and other adjustments); required, a list, empty when only holding |
| `orders[].symbol` | Stock symbol; required, non-empty string |
| `orders[].side` | Required, `BUY` or `SELL` |
| `orders[].amount` | USDT spent for a buy, number of shares sold for a sell; required, non-empty string or number |
| `orders[].tx_hash` | The swap's transaction hash, `^0x[0-9a-fA-F]{64}$`; required once the swap has been broadcast, never for approve transactions or orders never broadcast (a missing field and null both count as not filled) |

"Required / non-empty" means: the field is present and not null; strings are not blank; objects and lists (except `orders`) are not empty.

**Event ID**: a unique ID per log; it must match `^[A-Za-z0-9._:-]{1,128}$`. The SDK generates `evt-<ms timestamp>-<12 hex digits>`. It is used to reassemble chunks and to de-duplicate, so every resend must reuse the same event ID.

## 2. Headers and signing

| Header | Value |
|---|---|
| `X-AI-Seeds-Timestamp` | Current time, epoch milliseconds (decimal integer); more than ±5 minutes off the server's time → `401 TIMESTAMP_SKEW` |
| `X-AI-Seeds-Nonce` | A fresh random string for each request, 1 to 128 characters of `[A-Za-z0-9-]`; the SDKs use a uuid4 hex (32 hex digits) |
| `X-AI-Seeds-Signature` | HMAC-SHA256 signature, 64 lowercase hex digits |

The **secret** is a 64-character hex string the organizers issue to each team. The HMAC key is the UTF-8 bytes of that string, not the hex-decoded bytes.

```text
string_to_sign = METHOD + "\n"           PUT / POST, uppercase
               + PATH + "\n"             starts at /v1/, without the /ai-seeds-event-log prefix or the query string
               + TIMESTAMP + "\n"        value of X-AI-Seeds-Timestamp
               + NONCE + "\n"            value of X-AI-Seeds-Nonce
               + lower(ADDRESS) + "\n"   wallet address, lowercase
               + sha256_hex(CONTENT)     realtime: raw request body bytes; file: the file field content (the JSONL file itself, not the whole multipart body)

signature      = hex(HMAC-SHA256(UTF-8 bytes of the secret, string_to_sign))
```

- No trailing newline after the string to sign; the sha256 and the signature are 64 lowercase hex digits.
- Every retry generates a new timestamp and nonce and is signed again.
- The server first parses the request (malformed JSON or multipart, or an oversize body get 400 / 413 straight away), then checks in this order and returns the first failure: address format (400) → registered (401 `INVALID_CREDENTIAL`) → (file upload: missing `file` part, 400) → signature (401 `INVALID_SIGNATURE`) → timestamp (401 `TIMESTAMP_SKEW`) → content (400 / 413) → write (503). So `TIMESTAMP_SKEW` means the signature was correct and only the clock is off.

**Test vectors** (every implementation must pass these). Shared by both vectors:

- Secret `5f3a0123456789abcdef0123456789abcdef0123456789abcdef9b2c7e1d4a6f`
- Timestamp `1790242207500`, nonce `0f8e2a9c4b7d4e1f9a3c5b6d7e8f9012`
- Wallet address (lowercased) `0xb843d56afc902e37a6433eed534feadc91be71b8`

*Realtime*: `PUT /v1/events/evt-1790242207430-3fa6651c2d4b/chunks/0` with exactly these body bytes (no trailing newline; the `{}` payload is only for checking signatures and is not a valid log):

```json
{"protocolVersion":"2.0","address":"0xb843d56AfC902e37a6433eEd534Feadc91BE71b8","chunkCount":1,"totalBytes":2,"contentSha256":"44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a","encoding":"plain","payload":"{}"}
```

Content sha256 `ab6216a66effdfc88a6beba78829bff9ee9326767f6acaeaf5fc63f8433c929f`, signature `451191a2b2f2f87eb60a6725fef648e7f3f6ef6efd2a1b8fe2c3cf2ec994ac27`.

*File*: `POST /v1/files` with file content of this one line followed by one newline (LF):

```json
{"eventId":"evt-1","event":{"timestamp":1790242207430,"data":{"input":"i","cot":"c","output":"o","orders":[]}}}
```

Content sha256 `ed9852cbe75ea02d3d44addc87879bd85798fcdf72dc7a7987444b27c8fdb480`, signature `997222a8ba50a845cfb99e479f6f4e38abdf5796a3b0bf2480ae07c4d982c3fc`.

## 3. Realtime upload

`PUT {base}/v1/events/{eventId}/chunks/{chunkIndex}`, `Content-Type: application/json`:

```json
{"protocolVersion": "2.0", "address": "0xb843d56AfC902e37a6433eEd534Feadc91BE71b8",
 "chunkCount": 1, "totalBytes": 5130, "contentSha256": "<sha256 of the log text's UTF-8 bytes, 64 lowercase hex digits>",
 "encoding": "plain", "payload": "<the log text, or one chunk of it>"}
```

- Chunking: a log text over 65536 bytes is split on character boundaries into chunks of ≤ 65536 UTF-8 bytes each, never cutting a character; concatenating them in `chunkIndex` order (starting at 0) gives back the log text. A log has at most 128 chunks (about 8 MB). `chunkCount`, `totalBytes` and `contentSha256` describe the whole log text and are the same in every chunk.
- Retry only on network errors, 5xx and 429, reusing the same `eventId` and `chunkIndex`. Do not retry other 4xx.
- Success `200`: `{"eventId","chunkIndex","status":"STORED","message"}`.

## 4. File upload

`POST {base}/v1/files`, `multipart/form-data` with fields `address` (text) and `file` (JSONL, UTF-8; a leading BOM is ignored; LF and CRLF both work). Each non-empty line is one log:

```json
{"eventId":"evt-1790242207430-3fa6651c2d4b","event":{"timestamp":1790242207430,"data":{"input":"...","cot":"...","output":"...","orders":[]}}}
```

- The whole file is validated line by line first; a duplicate `eventId` within the file is also an error. If any line is invalid → `400` and nothing is stored: `{"code":"VALIDATION_FAILED","error":"<N> invalid lines","lineErrors":[{"line":3,"error":"..."}]}` (at most 100 lines listed; line numbers start at 1 and count physical lines, including empty ones).
- Missing `file`, an empty file, a file with no logs, or invalid UTF-8 → `400 VALIDATION_FAILED` (without `lineErrors`).
- Logs are stored only if every line is valid. The original text of each line's `event` is stored byte for byte, the same as realtime.
- Success `200`: `{"lines","events","records","status":"STORED"}` (`lines` = physical lines including empty ones, `events` = number of logs, `records` = number of records stored).
- If writing fails midway you get `503`; just re-upload the whole file. Logs are de-duplicated by event ID + chunk index, so uploading again is harmless.

curl example (without the SDK, e.g. to push files left over from batch mode; needs openssl and curl):

```bash
FILE=.ai-seeds/batch/2026-09-25.part1.jsonl                 # the JSONL file to upload
ts="$(date +%s)000"                                         # timestamp in milliseconds
nonce=$(openssl rand -hex 16)                               # new for every request
address=$(printf '%s' "$AI_SEEDS_ADDRESS" | tr 'A-F' 'a-f')  # wallet address, lowercase
content=$(openssl dgst -sha256 -r "$FILE" | cut -d' ' -f1)   # sha256 of the file content
sig=$(printf 'POST\n/v1/files\n%s\n%s\n%s\n%s' "$ts" "$nonce" "$address" "$content" \
  | openssl dgst -sha256 -hmac "$AI_SEEDS_SECRET" -r | cut -d' ' -f1)
curl -sS -X POST https://api.commonservice.io/ai-seeds-event-log/v1/files \
  -H "X-AI-Seeds-Timestamp: $ts" \
  -H "X-AI-Seeds-Nonce: $nonce" \
  -H "X-AI-Seeds-Signature: $sig" \
  -F "address=$AI_SEEDS_ADDRESS" \
  -F "file=@$FILE"
```

- The signed path is `/v1/files`, without `/ai-seeds-event-log`; `content` is the sha256 of the file content itself, not of the whole multipart body.
- A file may have at most 10 MB and 100000 lines; split larger files on line boundaries and upload the parts one by one (the SDK's `examples/manual_push.sh` splits them automatically).

## 5. Error codes

A failure response body is `{"code","error"}`; a rejected file also carries `lineErrors`.

| HTTP | `code` | When | Client action |
|---|---|---|---|
| 400 | `VALIDATION_FAILED` | Validation failed, incl. malformed JSON and malformed address | Fix it and send again; do not retry |
| 401 | `INVALID_CREDENTIAL` | Address not registered | Register with the organizers |
| 401 | `INVALID_SIGNATURE` | A signing header is missing or malformed, the signature does not match, or no secret is registered for the address | Check the secret and the string to sign |
| 401 | `TIMESTAMP_SKEW` | The timestamp is more than ±5 minutes off the server's time | Check your clock |
| 413 | `PAYLOAD_TOO_LARGE` | A single stored record exceeds 256 KB; a file exceeds 10 MB or 100000 lines | Split it and send again |
| 503 | `WRITE_UNCONFIRMED` | The service could not confirm the write | Retry: realtime with the same `eventId` and `chunkIndex`, file by re-uploading the whole file |
| 429, other 5xx, network errors | — | Transient failure; the body may not have the format above | Back off and retry |

## 6. Validation rules and limits

The SDK checks the same rules before sending. The server checks:

| Item | Rule | Realtime | File |
|---|---|---|---|
| `address` | `^0x[0-9a-fA-F]{40}$` (else 400), and registered (else 401) | ✅ | ✅ |
| Event ID | `^[A-Za-z0-9._:-]{1,128}$` | ✅ | ✅ |
| Chunk fields | `chunkCount` 1..128, `0 ≤ chunkIndex < chunkCount`, `totalBytes > 0`, `contentSha256` is 64 lowercase hex digits, `encoding == "plain"`, `payload` non-empty | ✅ | — |
| Integrity | Actual byte count and sha256 match the declared values | Single-chunk logs | — |
| Log content | All rules in Section 1 | Single-chunk logs | ✅ |

The content of multi-chunk logs is validated by the client before sending, and by the organizers once all chunks have arrived.

| Limit | Value | When exceeded |
|---|---|---|
| Per chunk | ≤ 65536 UTF-8 bytes | Guaranteed by the client's chunking |
| Per log | ≤ 128 chunks (about 8 MB) | Realtime 400; file: that line is an error |
| Per stored record (a chunk plus its metadata, after JSON escaping) | ≤ 256 KB | 413 |
| Per file | ≤ 10 MB, ≤ 100000 lines | 413 |

# Vendored ai-seeds SDK 0.3.0 (organiser-issued)

Copied verbatim 2026-10-05 from the AI Seeds Participant Kit (`ai-seeds-sdk.zip` → `ai-seeds-sdk-0.3.0/`). Do not edit these files. Full reference: `docs/skill/reference/participant-kit.md` (K10–K13); protocol: `docs/official/kit/PROTOCOL.md`.

| File | Kit source path | sha256 (computed 2026-10-05) |
|---|---|---|
| `ai_seeds_sdk-0.3.0-py3-none-any.whl` | `ai-seeds-sdk-0.3.0/python/ai_seeds_sdk-0.3.0-py3-none-any.whl` | `2bd16fec5681f47d3c1f1f81a58b630df818d8b53a673683da1b59d868b4e3bb` |
| `manual_push.sh` (executable bit set) | `ai-seeds-sdk-0.3.0/examples/manual_push.sh` | `24795c09469c7a72aa38f1581af1abe563bef55cb7745a6410ccf3063004c61b` |

**The kit's own `SHA256SUMS` is stale**: it has 27 hash lines for 20 files, only 3 files verify (`PROTOCOL.md`, `examples/models/README.md`, the Java jar), 7 files have two different hash lines, and both files vendored here fail it. The unpacked kit folder is byte-identical to `ai-seeds-sdk.zip`, so this is an organiser packaging error. **The hashes in the table above are our reference.** Verify with:

```bash
sha256sum vendor/ai-seeds-sdk-0.3.0/*.whl vendor/ai-seeds-sdk-0.3.0/manual_push.sh
```

## Install (Python ≥ 3.9, no third-party dependencies)

```bash
pip install vendor/ai-seeds-sdk-0.3.0/ai_seeds_sdk-0.3.0-py3-none-any.whl
python -c "import ai_seeds_sdk; print(ai_seeds_sdk.__version__)"   # 0.3.0
```

Env: `AI_SEEDS_ADDRESS` (registered wallet), `AI_SEEDS_SECRET` (organiser-issued, 64 hex chars; never commit or log). Optional `AI_SEEDS_URL` overrides the built-in `https://api.commonservice.io/ai-seeds-event-log` (tests only).

## Manual push (batch files the SDK gave up on, or after a crash/restart)

Needs `openssl` and `curl`. Uploads each JSONL file to `POST https://api.commonservice.io/ai-seeds-event-log/v1/files`, signed per PROTOCOL §2; splits files over 10,000,000 bytes / 100,000 lines; re-uploading is harmless (de-duplicated by event ID). Batch-mode logs must arrive **before 02:00 UTC** the next day.

```bash
(set -a; . ./.env; set +a; sh vendor/ai-seeds-sdk-0.3.0/manual_push.sh .ai-seeds/batch/2026-09-25.part1.jsonl [more files ...])
```

Success prints `{"lines":…,"events":…,"records":…,"status":"STORED"}`. `401 TIMESTAMP_SKEW` → fix the clock (±5 min).

Note: the SDK's own give-up warning prints the path `ai-seeds-sdk-0.3.0/examples/manual_push.sh`; in this repo use `vendor/ai-seeds-sdk-0.3.0/manual_push.sh`.

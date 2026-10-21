# LD12-M01 review correction — LD12-M01-RV01

Original `packet.jsonl` and `summary.json` are immutable historical evidence at
PR217 head a9062da. The original summary reproduces semantically from its
original analyzer, excluding `_receipt` and `collection_errors_explained`
annotations. Their exact hashes are in [the review receipt](../pr217-review-20261021.json).

Use `reviewed-summary.json` for current interpretation. Reproduce with:

```sh
PYTHONDONTWRITEBYTECODE=1 python docs/build/ops/ld12-20261021/analyse.py docs/build/evidence/ld12-ops-measure-20261021/packet.jsonl
```

The recorded5.387s maximum is log timestamp to latest persisted uploader attempt
clock, not a measured send or positive-ACK latency. The former20.4s bound is
withdrawn: socket timeout15s is not a whole-request deadline, and no ACK timestamps
were captured. Legacy chunk grouping uses timestamps; future collection adds
event ordinals. Existing ACK chunk rows alone do not prove every document's
expected chunk count. Time-of-hour offsets cannot establish anchor slot lag.

Unsigned cycle maximum76.309s and other retained values remain historical
observations. Per-unit RSS, signed execution/finality/drain/stall behavior and
actual recovery remain missing. No LD14 number, signed host or release is accepted.
Operator ownership moves to Keegan's team; host writes and signer access retain
the separately recorded Keegan approval requirements. The reviewer ran only
offline/mocked checks and disposable local PostgreSQL, not this collector on a host.

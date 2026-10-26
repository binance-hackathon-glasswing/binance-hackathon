# FS1 token history — IDEA-103 TH-01

FS1 now connects `MarketPort.candles` and `token_sessions` to the production
`ContextBuilder.series` callback through `SessionHistory`. The existing trend
rule,95%/60% targets, five-session window, dead band and profile hashes do not
change. This is runtime integration, not an economic validation of the guard.

## Required pinned input

Both FS1 FINAL and FS1-R preparation/start require a `TokenHistoryConfig.v1`
document. Other historical profiles keep their prior behavior unless explicitly
configured with the new history input.

| Field | Required value / meaning |
|---|---|
| `schema` | `TokenHistoryConfig.v1` |
| `timestamp_kind` | `OPEN`; establish that the source's hourly timestamp labels the start of its interval |
| `timestamp_evidence_sha256` | Lowercase64-hex SHA-256 of the actual timestamp-qualification evidence |
| `token_adjustment_version` | Nonempty version of the qualified raw-token adjustment convention; at most128 characters |

No additional fields are accepted. The file is at most4096 bytes. These are
operator qualification inputs, not proof supplied by a synthetic fixture or a
new organiser requirement. Keith owns the actual candle/session/adjustment
qualification; Keegan reviews its release/runtime binding. Existing private
captures are not copied into Git by this work.

TH-01 timestamp evidence is now available in the
[committed live packet](evidence/th01-live-20261026/): PR297-RV01 independently
reproduces the five-name PASS and verifies all442 raw artifacts. Its evidence
SHA-256 is `cc8371bd235eb4db284367fbf0267890d3c6a87bafca60ca2573f0b9d64b3fa6`.
TH-CONFIG01 generates [the actual config](evidence/th01-live-20261026/token-history.json),
SHA-256 `5e572570bc24fb2ca7b692dccf71f67a37c5fac3d75330e4558634cf45417be9`.
Its label `BINANCE_WEB3_RAW_TOKEN_NO_LOCAL_ADJUSTMENT_V1` names existing processing:
raw provider token prices, exactly scaled, without local split/dividend or token/share
adjustment. The label is copied into series/bar provenance and the cache binding;
it does not select a price transformation or certify the provider's corporate-action
treatment. No additional naming decision from Keith is needed. Copy these exact bytes
for deployment, or reproduce into a new path with:

```bash
python -m tools.th01_candle_timestamps config \
  --evidence docs/build/evidence/th01-live-20261026/timestamp-evidence.json \
  --adjustment-version BINANCE_WEB3_RAW_TOKEN_NO_LOCAL_ADJUSTMENT_V1 \
  --out-file "$TOKEN_HISTORY_OUTPUT"
```

Keep `raw/` beside the evidence file: config generation now verifies its hashes,
request identities, parsed rows and availability before writing anything.
Record the printed config hash and obtain its release binding acceptance; a
placeholder adjustment version is not qualification. This establishes timestamp
semantics, not corporate-action behavior or current-host trend availability.

Pass that file's actual path through `prepare_shadow.py prepare`'s
`--token-history-config` option, alongside the existing FS1 profile, routing,
router policy, balance providers and adoption reference. Preparation packages
its exact bytes as `token-history.json` and pins their SHA-256 in
`driver.token_history_sha256`, with `driver.token_history_file` set to
`/etc/larp/token-history.json`. `gate_a_check` verifies the packet, schema, pin
and destination path. Half/missing/tampered inputs fail preparation or startup.

The operator installs the packaged file at that path, root-owned and readable
by `larp-runtime`, in the same reviewed FS1 transfer as its other pinned inputs.
Manifest the resulting runtime config and re-run the existing release/host
checks. A profile alone cannot silently start FS1 without the history callback.
No build, installation, provider access or activation is performed by this PR.

## Data path and bounds

- Five eligible token contracts only, through the existing credential-screened
  Web3 `market/candles` endpoint; hourly bars,300 rows/page, at most two pages per
  token. The inclusive `after` cursor is the previously observed K6a behavior;
  ignored/non-progressing cursors, conflicting overlap and malformed data fail
  explicitly instead of looping. Raw responses remain in hashed private artifacts.
- A separate history transport has a five-second request timeout. At most ten
  requests occur in a refresh; valid results are reused until a new eligible
  session close, and failed/incomplete attempts retry at most once per15-minute
  slot. Request/timeout bounds do not constitute measured production latency.
- Only the profile's consecutive trend-window sessions are converted, after the
  configured close delay, against the pinned calendar. Normal16:00 and explicit
  early13:00 Eastern closes follow that calendar, including DST and holidays.
  UTC-day candles and underlying share prices are never substituted.
- Missing/no-trade intervals remain missing. No forward fill, gap bridging or
  guessed close. All five series must have the required window; a stale older
  window cannot masquerade as the latest expected session.
- The history transport parses numeric JSON prices directly as decimal strings,
  preserving the source lexeme before any binary-float conversion. Session closes
  use exact rational scaling and integer truncation, independent of Decimal context
  precision; legacy transport/converter callers retain their defaults. Inconsistent
  OHLC ranges are rejected. Trade counts, hourly alignment, identity, source hashes and source
  availability are checked. A capture cannot predate the closes it contains.
- Raw fetches finishing after a round's fixed cutoff are cached but not supplied
  to that decision. They become eligible on a later decision once all source
  bytes are available. Out-of-range future capture timestamps are refused.

## State, failures and replay

The small atomic cache is under the runtime's existing market artifact root,
`history/session-history-cache.json`. It is bound to the full profile, pinned
calendar, five issuer/token identities and semantics input. Its bytes have an
integrity hash. It retains failed-attempt backoff across a restart; corrupted,
misbound or future entries are not trusted. New adjustments/configuration need
a new qualified binding, rather than silently reusing previous results.

Each round records the complete compact `PriceSeries.v1` inputs, source artifact
hashes and availability times in its existing journal. Recorded-port replay uses
those recorded series, without the provider or cache, so old journals remain
replayable and new trend-driven plans reproduce exactly.

Unavailable history is recorded with a bounded `history_status` and
`quality: UNAVAILABLE`; raw exception/provider text is not copied into decisions.
The existing trend rule preserves its previous/default state and mandatory risk
planning continues. This PR does not add an entry halt for missing history:
a cold start may retain the configured UP default until a complete window is
available. It does not establish that the guard improves returns or drawdown;
EXP-007 and exact provider/release/host qualification remain separate.

PR295-RV01 source review (2026-10-26 SGT): pinned Python3.12.15/PG14.24,
2901 tests/4060 subtests PASS; 8 skips/3 nested-sandbox exclusions. Full rerun
deferred in TH-RV02 is complete. [Receipt](evidence/pr295-review-20261026.json).

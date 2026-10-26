# IDEA-105 — TH-01 hourly candle timestamp probe

Date: 2026-10-26 SGT. Owner of the qualification decision: Keith (TH-01). Tool and criteria: Claude session, at the
user's request ("Yes" to writing a probe Keith can run). Related: IDEA-103 (TokenHistoryConfig.v1), IDEA-104
(S5 needs the same input), participant-kit.md K6a, `docs/build/FS1_TOKEN_HISTORY.md`.

## Why

FS1, FS1-R and S5 cannot be prepared or started without a `TokenHistoryConfig.v1` whose `timestamp_evidence_sha256`
is the hash of real evidence that the Web3 `market/candles` hourly timestamp labels the **start** of its hour
(`timestamp_kind` `OPEN`). The kit says only that each row is `[open, high, low, close, volume, timestamp ms, trade
count]`, ascending, with periods without trades left out (`docs/official/kit/web3-open-api.md`). K6a's daily bars at
UTC 00:00 fit OPEN but do not prove it, and its raw responses were never committed. The `capture` branch holds the
IDEA-063 quote capture only (no candles; checked 2026-10-26). `SessionHistory` uses an hourly row stamped T as the
completed hour [T, T+1h) (`stamp + HOUR_MS <= close`), so that is the claim to establish.

## Design

`tools/th01_candle_timestamps.py probe` reads public candles through the production history transport
(`Web3Client(..., timeout=5, exact_decimals=True)` behind `MarketPort`, the same construction as `build_driver`), so
the evidence passes the same credential screening and decimal parsing as the runtime. Read-only: only
`market/rwa/tokens` (at the start and the end, for `tokenToShareRatio`/`statusInfo` context) and `market/candles`.
No quotes, swaps, signing, model or ai-seeds calls.

Every 60 s it fetches, per name, the latest 3 hourly bars and the latest 150 one-minute bars. It runs from start until
15 minutes after the first whole UTC hour B that is at least 8 minutes away (H = B − 1 h is the hour in progress
before B). **Duration: 23–83 minutes; about 35–40 minutes if started between :40 and :45 past the hour.** Trades are
densest in the US session (13:30–20:00 UTC until Nov 1, i.e. 21:30–04:00 SGT); off-hours runs may come back
INCONCLUSIVE and can simply be repeated.

## Pre-registered pass criteria (written before any test or code)

Per name, with grace G = 5 minutes:
- **TS1 no future or misaligned labels.** No hourly or minute row in any successful response is stamped after that
  response's `available_at`; every hourly stamp is a whole UTC hour. A violation is a contradiction of OPEN.
- **TS2 live bar labelled by its start.** At least two successful polls at times in [H + 5 min, B) whose newest hourly
  row is stamped H, and the row stamped H differs between at least two of them (it is accumulating during H).
- **TS3 frozen after its hour.** At least three successful polls at or after B + G contain the row stamped H, and all
  of them are identical. A change after B + G is a contradiction.
- **TS4 one-minute corroboration (reported; contradiction only).** On the last successful poll at or after B + G,
  aggregate the minute rows in the OPEN window [H, B) and in the end-labelled window [H − 59 min, H] (each only if the
  minute response reaches back to its start): first open, max high, min low, last close and summed trade count, each
  compared exactly (decimal) with the hourly row stamped H. Matching the end-labelled window but not the OPEN window
  is a contradiction. Neither matching is reported, not a contradiction (the provider may aggregate differently).

Verdict:
- **FAIL** if any name has a contradiction (TS1, TS3 or TS4).
- **PASS** if there is no contradiction and at least **three of the five** names satisfy TS2 and TS3.
- **INCONCLUSIVE** otherwise (too few trades, transport errors); rerun, preferably in the US session.

Tool criteria:
- **TS5** the output directory must be new; raw responses go to `raw/` through the production `Artifacts` store; the
  single evidence file `timestamp-evidence.json` binds the polls, the artifact hashes, the token metadata and the
  assessment, and its SHA-256 is what the config pins.
- **TS6** `token-history.json` is written only for a PASS evidence file, only with an explicitly supplied
  `--adjustment-version` (Keith's decision, see below), and only after `larp.marketdata.history.configuration`
  accepts it. FAIL/INCONCLUSIVE evidence never yields a config.
- **TS7** offline tests with a synthetic port: start-labelled live bars PASS; end-labelled bars with the in-progress
  bar included FAIL (TS1); end-labelled completed-only bars FAIL (TS4); no trades INCONCLUSIVE; schedule bounds;
  no config on non-PASS; directory refusal. The full suite shows no new failures.

## Not decided here

`token_adjustment_version` names the raw-token corporate-action convention (recorded as `corporate_action_version`
in each `PriceSeries.v1`). The probe records `tokenToShareRatio` at start and end as context only; choosing the
version string stays with Keith. The probe establishes the label convention only; it does not validate the trend
guard's economics (EXP-007) or approve any release, host or profile.

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

## Amendment TS-A1 (2026-10-26, before any live run; offline tests only)

Writing the tool against the real transport showed two cases the synthetic market did not produce:
- `available_at` is the probe host's clock. A host a few seconds behind the provider would see the current minute's
  row "in the future" and fail TS1 falsely. TS1 now allows **30 s** of clock lead. An end-labelled hourly bar in
  progress still leads by 5–55 minutes in every TS2 poll, so TS1 still catches it. The host clock must be
  NTP-synchronised; a clock that is minutes off yields FAIL, not PASS.
- A row with a null trade count would have been treated as malformed (FAIL). TS4 now compares prices only when
  either side has no trade count; it never guesses a count.

No threshold, window or verdict rule changed. Offline: 20 focused tests (`tests/marketdata/test_th01_candle_timestamps.py`),
including one through the real `Web3Client`/`MarketPort` with a fake HTTP opener (exact decimal strings, raw artifacts,
only `market/candles` and `market/rwa/tokens` requested).

## How to run (Keith)

From an up-to-date checkout of canonical containing this tool, on a machine with the Web3 key in `.env`
(`BINANCE_API_KEY`, `BINANCE_SECRET_KEY`) and a synchronised clock:

```bash
python -m tools.th01_candle_timestamps probe --out ~/larp-th01/run-$(date -u +%Y%m%dT%H%MZ)
```

Start at about :40 past the hour, preferably in the US session (21:30–04:00 SGT until Nov 1). It prints its end time
and stops by itself: 0 PASS, 3 INCONCLUSIVE (rerun), 4 FAIL. It never writes into an existing directory. On PASS,
choose the `token_adjustment_version` and write the config (or pass `--adjustment-version` to the probe):

```bash
python -m tools.th01_candle_timestamps config --evidence ~/larp-th01/<run>/timestamp-evidence.json \
  --adjustment-version '<Keith's version>' --out-file ~/larp-th01/<run>/token-history.json
```

The `config` step re-assesses the stored polls, refuses anything that does not re-assess as the stored PASS, and
validates with the runtime's own `configuration()`. Record here the verdict, `timestamp_evidence_sha256`, the config
hash and where the evidence is kept. Then Keegan reviews the binding (TH-01) and the file goes to
`prepare_shadow.py prepare --token-history-config` / `prepare_fs1.py --token-history-config`.
The evidence holds public market data and artifact hashes only; credentials never enter it.

## Offline results (2026-10-26)

**TS5–TS7 PASS offline; TS1–TS4 untested on the real provider (Keith's run).** Source `5abbba6f` (pushed before
execution). Focused: 20 passed. Full suite on Python 3.12 / PostgreSQL 16 (not the pinned 14.24 image):
**2995 passed, 11 skipped, 4069 subtests passed, 0 failed** (850.84 s), against 2975 passed / 11 skipped on canonical
`d4f7a6e0` in the same environment: the difference is exactly the 20 new tests. No live provider was called and no
credentials were used. GitHub CI is billing-blocked. Remaining: Keith's live run and verdict (TH-01), his adjustment
version, Keegan's review of the binding.

## Live run 1 (2026-10-26, Keith's machine)

**PASS: OPEN labels supported on the real provider, 5 of 5 names, no contradiction.** Source `1ea20471` (PR 297
head, containing canonical `d4f7a6e0`), run with Keith's `.env` from an isolated checkout. Polled 09:31–10:15 UTC
across the 10:00 UTC boundary (H = 09:00), in the Asian session rather than the preferred US session. Exit 0.

- Verdict: **PASS**, `names_ok` GOOGLB, MSFTB, NVDAB, SKHYB, TSLAB. TS1, TS2 and TS3 true on all five; no
  contradictions.
- `timestamp_evidence_sha256` = `cc8371bd235eb4db284367fbf0267890d3c6a87bafca60ca2573f0b9d64b3fa6`.
- Evidence: Keith's machine, `~/larp-th01/run-20261026T0931Z/` (`timestamp-evidence.json` plus 442 raw artifacts,
  14 MB). Not committed: it is a run artifact, it holds public market data and artifact hashes only, and neither
  credential value appears anywhere in it (checked).
- TS4 (reported only): `open_match` true on MSFTB only; `end_match` false on all five. Post-run diagnosis (not a
  criteria change): for **all five** names the first open, max high, min low, last close **and summed volume** of the
  OPEN-window minute rows equal the hourly row exactly. Only the trade count differs: the hourly count is below the
  sum of minute counts (GOOGLB 48 vs 74, NVDAB 186 vs 215, SKHYB 186 vs 293, TSLAB 303 vs 463; MSFTB 5 vs 5), so
  the provider's trade count is not additive across bars. That is the "aggregates differently" case the pre-registered
  rule reports without failing; it supports OPEN rather than weakening it. The TS4 code is deliberately unchanged:
  `config` requires the stored assessment to re-assess identically, so changing it would invalidate this evidence.
  If a future rerun is needed, a criteria amendment written before that run could drop trade count from TS4.
- `config` dry run on this evidence with a placeholder version accepted it (re-assessed as the stored PASS, validated
  by `configuration()`); the placeholder file was deleted. No `token-history.json` exists yet.
- Tool fix found by this run: the documented `--out ~/larp-th01/run-…` failed on a first run
  (`TH01_PROBE_REFUSED` / `FileNotFoundError`) because only the leaf directory was created. The probe now creates
  missing parents; the run directory itself must still be new (TS5). Regression test
  `test_ts5_missing_parent_directory_is_created` fails on `1ea20471` and passes with the fix (21 focused passed,
  Python 3.12).

Remaining (TH-01): Keith chooses `token_adjustment_version` and runs the `config` step above on this evidence;
Keegan reviews the binding before the file goes to `prepare_shadow.py` / `prepare_fs1.py --token-history-config`.

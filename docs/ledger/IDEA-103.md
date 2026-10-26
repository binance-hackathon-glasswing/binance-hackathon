# IDEA-103 — FS1 live token history for the basket trend guard

Date: 2026-10-26 SGT. Owner: Yao Zhu / Codex. User request: wire the existing historical-price source into FS1 and deliver a PR. Base: canonical ecdbc1aa. Related: IDEA-075/076 DR-08, IDEA-093 FS1; EXP-007 economic evaluation remains separate.

## TH-01 prospective contract and acceptance (before implementation/tests)

1. Production FS1 preparation/start binds an explicit, hashed TokenHistoryConfig.v1 input: Web3 hourly candle OPEN timestamp convention, its qualification evidence SHA-256 and token adjustment version. Do not invent source qualification or copy private captures into Git. Missing/half/tampered configuration cannot silently ship an inert FS1 trend guard. Older non-FS1 configurations keep existing behavior.
2. Read the five eligible tokens through the existing credential-screened Web3 candle client, using bounded inclusive-after pagination (at most two 300-hour pages per token, five-second transport timeout). Stop on non-progress, conflicting overlap, malformed rows, identity/provenance/future errors. No swap/model/log-upload calls. Preserve source artifacts and request timing.
3. Convert to PriceSeries.v1 against the pinned US calendar; use the exact configured trend window and post-close delay, never UTC-day closes. Missing trades/sessions stay missing; do not bridge gaps or mix token/share prices. Use only bars available at the decision cutoff; a fetch completing later becomes eligible on a later decision. No future leakage.
4. Cache compact, hash-bound derived series under runtime-owned market storage. Refresh after a new eligible session close; retry incomplete/failed capture no more than once per15-minute slot; reuse valid cache after restart. Bind cache to profile, calendar, identities and semantics. Reject corrupted/future cache. Preserve prior/default trend state on unavailable history and keep mandatory risk planning available; do not change strategy thresholds or missing-input policy.
5. Test rising/falling/neutral five-name windows and actual policy/planner transitions between95%/60%, partial/future/stale history, after-hours/weekend/DST/early-close timing, pagination overlaps/non-progress, transport failure, per-session caching/restart and bounded calls. Existing legacy session-consumer behavior remains unchanged unless explicitly opted into the live producer's calendar-close support.
6. Wire preparation CLI, package integrity/host checks and build_driver; test missing/tampered config and prove production composition has a series callback. Full original/new PostgreSQL recorded-port replay must never fetch live history.
7. Commit and push any decision/trading/logging code before executing it. Run focused checks then full pinned Linux/Python3.12/PostgreSQL14 suite, with skips reported. No deployment, credentials, live providers, spending or economic-performance experiment. Existing release/host/qualification and EXP-007 owner gates remain; source integration does not establish profitability.

A pinned timestamp/adjustment qualification input is an installation prerequisite, not an organiser requirement or a claim that current private evidence has been independently qualified. The completed PR must document its exact schema and transfer path; it must not substitute a synthetic example for real qualification.

## TH-RV01 — implementation review and initial checks

The first focused pass exposed failure backoff not surviving restart; failed attempts now persist through the same atomic cache as successful history. Required FS1 synthetic preparations/composition fixtures now supply explicit synthetic semantics and all five identities. Late captures are deferred and captures predating their claimed closes are refused.

At d8e95f02:55 focused tests PASS, including actual strategy/planner SELL/BUY and real PostgreSQL replay. The first full run had2893 passed/1 failed/11 skipped/4060 subtests; the sole failure was the parallel-FS1 composition fixture omitting the new pinned input. Update that fixture without relaxing startup requirements. Prospective additional boundary: refuse extreme decimal exponents before expanding them; reject stale capture metadata. Repeat focused and full pinned checks.

## TH-RV02 — saved handoff; full rerun deferred at user request (2026-10-26 SGT)

PR: https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/295

Source `93ea0e1fd3822fbfbbe55f1c9f6e08273bdedec8`: **73 focused tests /11 subtests /0 skips PASS**,6.13s, on Linux aarch64/Python3.12.15/PostgreSQL14.24. This includes the previously failing five-worker FS1 composition, bounded decimal inputs, actual policy/planner reductions and buys, missing-history mandatory exits, package pins, cache/backoff and exact PostgreSQL replay.

The user asked to stop the suite and defer the rerun until tomorrow. The running full-suite container was stopped before completion (exit137 due requested stop); no full-suite PASS is claimed for this source. Its disposable PostgreSQL container was also stopped/removed. No test process remains from this session. The earlier d8e95f02 full result and its one fixed composition-fixture failure remain recorded in TH-RV01.

**Next work, explicitly deferred:** Codex/reviewer reruns the full pinned suite on the current PR source after the user resumes; then records results and reviews PR295. Keith qualifies actual hourly OPEN timestamp and adjustment evidence; Keegan binds/reviews the exact release/runtime; Yao supplies that input, transfers the pinned file and verifies current-host history. These are tracked in INCOMPLETE_WORK TH-01 / IDEA-093 FS1. No deployment, real provider/credential access, model spend, wallet operation or economic evaluation occurred. EXP-007 remains separate.

Implementation/input/transfer contract: [FS1_TOKEN_HISTORY.md](../build/FS1_TOKEN_HISTORY.md). Machine receipt: [fs1-history-20261026.json](../build/evidence/fs1-history-20261026.json).

## PR295-RV01 — independent review criteria (2026-10-26 SGT)

Incoming head `1a2bd8f0`, canonical base `ecdbc1aa`. Review scope is source integration and offline checks;
actual provider qualification, deployment, owner acceptance and EXP-007 remain separate.

Static findings: the production Web3 transport parses JSON decimal numbers as binary floats before history
normalization, so converting those floats to strings cannot recover the original decimal. The session
converter also multiplies Decimal prices under the ambient precision (normally 28 digits), which can round
a close across a whole price unit. Finally, positive but inconsistent OHLC ranges are accepted as history.

Prospective pass criteria, before new implementation/test execution:
- RV1: the history-only Web3 client preserves exact JSON decimal numbers through credential-screened raw
  artifacts and history conversion. Other transport clients keep their existing default behavior.
- RV2: the producer's scaled closes truncate the exact decimal rational, independent of ambient Decimal
  precision. Legacy session conversion remains the default so historical recorded-port behavior is preserved.
- RV3: reject inconsistent high/low/open/close values; malformed or unavailable input remains bounded,
  sanitized UNAVAILABLE data and cannot fabricate a trend window. Existing cache/pagination/cutoff cases pass.
- RV4: actual production composition, trend-driven BUY/SELL and exact PostgreSQL replay pass; existing
  profile hashes, strategy thresholds, risk authority and legacy preparation remain unchanged.
- RV5: complete the deferred full suite on pinned Python3.12.15/PostgreSQL14.24 with recursive dependency
  locks verified, exact exclusions/skips and GitHub CI availability recorded. Push code/tests before execution.

### PR295-RV01 results and merge decision

**RV1–RV5 PASS offline**, pushed source `ba6f0d94`. The history client alone now parses JSON decimal
numbers as their original decimal strings, retaining credential-screened raw response evidence. Its session
conversion uses exact rational scaling, so even a price just below a whole scaled unit cannot round up under
the ambient Decimal context. Default Web3 clients and legacy converter callers keep their prior behavior.
History also rejects positive but inconsistent OHLC ranges. The redundant scope check was removed without
changing profile hashes, strategy thresholds, trading authority or the stated missing-history policy.

Focused transport/history/cache/session/preparation/composition/strategy/PostgreSQL replay checks:
**112 tests /20 subtests PASS, zero skips**, 8.21s. The exact-price regression uses mocked HTTP JSON,
screened raw artifacts, the real MarketPort and SessionHistory, and Decimal precision six; all five series
retain the correct integer close. Actual trend-driven SELL/BUY and recorded-port replay remain covered.

Deferred full verification is now complete: **2901 passed, 4060 subtests passed, 8 skipped, 3 deselected,
0 failed**, 307.97s, pinned Linux aarch64/Python **3.12.15**, PostgreSQL **14.24**. All53 applicable recursive
requirement lines (44 unique distributions) match their locks; `pip check` passes. The eight skips are the
optional private source fixture, external market artifacts, root directory-mode behavior and five systemd
cases. Three unchanged nested-bubblewrap tests are explicitly excluded because this Docker host cannot
supply their namespace/proc mounts. No Linux sandbox/systemd/host qualification is claimed.
GitHub check `121379203073` did not start because account payments/spending limits block jobs.
[Review receipt](../build/evidence/pr295-review-20261026.json).

Merge PR295 into canonical under the user's review/fix/merge authorization. This completes the deferred
source verification, not deployment or economic evaluation. TH-01 stays open: Keith qualifies actual hourly
OPEN timestamp/adjustment evidence; Keegan reviews and binds the real input and exact release; Yao transfers
the pinned file and records current-host five-name history/trend qualification. EXP-007 remains separate.

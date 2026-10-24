# IDEA-054 — Frozen US regular-session calendar for the runtime (Gate A input 2)

- Date / owner: 2026-10-15 SGT / built with Claude Code at the user's request ("build Gate A"); calendar owner Keith (DEPLOYMENT_DAY.md input 2), runtime pin Keegan. Needs Keith's review.
- Status: open (criteria written before any code; results below once run)
- Links: DEPLOYMENT_BUILD.md Gate A; DEPLOYMENT_DAY.md (PR #72) "Inputs the shadow run still needs" item 2; IDEA-048/IDEA-050 (`SessionCalendar`); IDEA-040 B3 (`larp/strategy/sessions.py`); IDEA-049-D; G-52 (plan.md: "may be a static calendar").

## What and why

`larp.runtime.service` refuses a run without a `USRegularSessions.v1` file pinned by SHA-256 in `runtime.json` (`driver.session_calendar_file` / `session_calendar_sha256`). `SessionCalendar` (`larp/runtime/driver.py`) also refuses any decision time before the first session's open or after the last session's close, so the file must cover the whole run. No calendar file exists in the repo, so Gate A cannot start even with every other input in place.

This entry builds that file and the tool that regenerates it. It is a fixed public schedule, not a parameter, a measurement or a trading choice.

## Scope of "Gate A" in this entry

Gate A (DEPLOYMENT_BUILD.md) needs host work, secrets and team decisions that cannot be done from a code change. Of the six inputs DEPLOYMENT_DAY.md lists as blocking the shadow run, this entry does input 2 only. The others stay open with their owners:

| Input | Why not here |
|---|---|
| 1. LIVE strategy profile | Needs a measured `QuoteCostSummary.v1` from real Web3 quotes. `larp/marketdata/port.py` itself marks fee denomination and post-approval gas as unproved (capability proof, GAP-29), so a summary built now would invent values. Isaac + Keith. |
| 3. Issuers map | Blocked by #25 (issuer ID vs ticker); PR #68 (review A) is changing that code. Yao Zhu + Isaac + Keegan. |
| 4. Evidence live settings and source terms captures | Team decision with provenance (11 `live: null` parameters); dated terms captures. Yao Zhu. |
| 5. Initial state file | Needs a real balance read of the dev wallet. Team. |
| 6. `cadence_ms`, `day_roll_window_ms` | Team decision (IDEA-050 "Still open"). |

## Design

- **Range:** every NYSE regular session in calendar year 2026, 2026-01-02 → 2026-12-31. This covers the first shadow day, the rehearsal (Oct 21–26) and final (Oct 29 → Nov 11) windows in `larp/strategy/profiles.py`, and any run that keeps going after the scored window, so `SessionCalendar` never refuses a 2026 decision time. It also gives more than 60 earlier sessions for the B3 token-candle builder.
- **Sessions:** 09:30–16:00 America/New_York, converted to UTC with `zoneinfo` (DST: Mar 8 and Nov 1, 2026). `session_index` starts at 0 on Jan 2 and increases by 1 per session.
- **Holidays (no session):** Jan 1, Jan 19, Feb 16, Apr 3, May 25, Jun 19, Jul 3 (Independence Day observed), Sep 7, Nov 26, Dec 25.
- **Early closes (13:00 ET):** Nov 27 and Dec 24, marked `"early_close": true`. Under B3 (`sessions.py`) these stay missing sessions. Neither date is inside the rehearsal or final windows.
- **Source:** NYSE Group, "NYSE Group Announces 2026, 2027 and 2028 Holiday and Early Closings Calendar" (press release, Business Wire, 2025-12-23) and the NYSE "Holidays & Trading Hours" page. Both hosts are refused by this container's network policy, so no dated capture or hash of the official text is stored yet: **a team member must capture one and add its SHA-256** (open item below). Independent cross-check: `exchange_calendars` 4.13.2, calendar `XNYS` (third-party library; used once in a scratch environment, not a dependency).
- **Hash:** `content_hash` = `Document.from_dict(<file without content_hash>).digest("USRegularSessions.v1")`. The runtime pins the SHA-256 of the file bytes separately.
- **Files:** `tools/build_session_calendar.py` (holiday lists and source as constants; `--check` verifies the committed file byte for byte); output `config/runtime/session-calendar.2026.json`; `config/runtime/runtime.example.json` gets the file's SHA-256 in `driver.session_calendar_sha256`. The host still copies the file to `/etc/larp/session-calendar.json` (DEPLOYMENT_DAY step 7).

## Pass criteria (written before the code exists)

1. **Sessions:** 251 sessions, Jan 2 → Dec 31, indices 0..250 consecutive; none on a weekend or a listed holiday; every weekday that is not a listed holiday is present.
2. **Times:** every open is 09:30 ET; every close is 16:00 ET except Nov 27 and Dec 24 at 13:00 ET, which (and only which) are marked `early_close`. UTC spot checks: Mar 6 opens 14:30Z, Mar 9 opens 13:30Z, Oct 30 opens 13:30Z, Nov 2 opens 14:30Z, Nov 27 closes 18:00Z.
3. **Cross-check:** the (open, close) pairs equal `exchange_calendars` 4.13.2 `XNYS` for 2026 exactly (run once in a scratch venv; recorded here, not a test).
4. **Runtime and strategy accept it:** `SessionCalendar` loads the committed file and returns an index for every 15-minute step from 2026-10-15T00:00Z to 2026-11-11T16:00Z (no refusal); spot checks of `index`/`remaining` on a weekday, a weekend and across the DST change. `token_sessions` accepts it, keeps a complete Oct 30 session and reports Nov 27 as missing.
5. **Reproducible and pinned:** `content_hash` matches the rule above; `build_session_calendar.py --check` passes on the committed file and fails on a one-byte change; `runtime.example.json`'s `session_calendar_sha256` equals the file's SHA-256, and `build_driver`'s pin check accepts the file with that hash.
6. **No regressions:** the full suite passes locally, and Linux CI is green on the PR.

## Results

- 2026-10-15: criteria committed and pushed at `b4d9ce2`, before any code. Tool, file, tests and the example pin committed and pushed at `a005040`, before the suite ran.
- **Criterion 1: PASS.** 251 sessions, 2026-01-02 → 2026-12-31, indices 0..250; the session dates equal every 2026 weekday minus the ten listed holidays (`tests/runtime/test_session_calendar.py` C1).
- **Criterion 2: PASS.** Every open is 09:30 ET; every close is 16:00 ET except Nov 27 and Dec 24 (13:00 ET, the only `early_close` rows). Spot checks pass: Mar 6 14:30Z, Mar 9 13:30Z, Oct 30 13:30Z, Nov 2 14:30Z, Nov 27 close 18:00Z (C2).
- **Criterion 3: PASS.** `exchange_calendars` 4.13.2 `XNYS` 2026 schedule: 251 sessions, (open, close) pairs **identical** to the file. Run once in a scratch venv with `python -I`; not a repo dependency. The official NYSE pages could not be fetched (hosts refused by this container's network policy), so the holiday list matches the NYSE Group release as reported by search results and this library, not a stored capture (open item below).
- **Criterion 4: PASS.** `SessionCalendar` accepts the file and answers every 15-minute step from 2026-10-15T00:00Z to 2026-11-11T16:00Z; Friday's index holds through the DST weekend and Nov 2 is the next index at 14:30Z; times before Jan 2's open and at Dec 31's close are refused. `token_sessions` keeps a complete Oct 30 session (close 20:00Z) and lists Nov 27 as missing.
- **Criterion 5: PASS.** `content_hash` = `7cd4101d…1a9b` equals the rule; `--check` passes on the committed file and fails on a one-minute change; file SHA-256 `bf4c2eca967195cdbd7d0ab56cbffdfb54352389e6fbca1057d372ac003b769c` equals `runtime.example.json`'s `driver.session_calendar_sha256`; `_pinned_json` (the pin check `build_driver` uses) accepts a host copy and refuses a changed one.
- **Criterion 6: PASS locally, CI pending.** Full suite at `a005040` with a disposable PostgreSQL 16: 1259 passed, 7 skipped, 1 xfailed, 1595 subtests (Python 3.13.16; CI uses 3.12.15). Linux CI runs on the PR.
- Synthetic test inputs only; no market data, credentials or logs were used.

## Open items

- 2026-10-16 update (IDEA-058): the source-capture task below is now verified. The exact NYSE calendar page was retained outside Git, SHA-256 `79602f7be5a8f1d39c2b1cac4dd02c4c07f18cf9f92d70602834069154719bad`; URL, date and artifact location are in IDEA-058 GA-V01. It matches the ten holidays and two early closes. Calendar bytes/pin unchanged; Keith's review remains open. The following capture request is historical.

- Capture the NYSE source (press release or Holidays & Trading Hours page) with a date and SHA-256 and record both here. The calendar file cites the source but holds no capture hash, so recording it does not change the pinned file. Calendar owner (Keith) or any team member with access; the content does not change unless NYSE amends its schedule.
- Keith's review of the file and of B3's handling of early closes.

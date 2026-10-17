# IDEA-063 — QuoteCostSummary.v1 producer: measure quote costs read-only, then summarise (Gate A input 1)

- 2026-10-16 renumbered (Claude Code session, at Keegan's request, PR #88 review): this entry was first written as IDEA-057, which #85 (merged to `main`) uses for AIand evidence routing. The quote record and its references are now IDEA-063 so both records survive the merge. Commit messages before the rename still say IDEA-057.

- Date / owner: 2026-10-15 SGT / built with Claude Code at the user's request ("create the summary tool"). Runs with real quotes belong to Isaac or Keith (dev-wallet Web3 API key); the summary and profiles need Isaac's and Keith's review before they are pinned.
- Status: real capture running (started 2026-10-16 18:19:07 UTC on Keith's Linux server; first round: 5 samples, 1 BNB price quote, 0 failures; summary, fee-netting check and owner review open)
- Links: DEPLOYMENT_DAY.md "Inputs the shadow run still needs" item 1; `larp/strategy/profiles.py` (`quote_summary`, `build_live_profiles`); `config/strategy/LIVE.md`; `larp/execution_live/gate_b.py` DR-01 ("raw capture attribution and three-day/weekend coverage still required"); participant-kit.md K4, K8 (quote-and-swap, approve-transaction, gas-limit); ledger rule 4.

## What and why

A `dev` or `live` run needs a LIVE strategy profile. `build_live_profiles(summary, registry)` builds one, but its input, a `QuoteCostSummary.v1` measured from real Web3 Open API quotes, has no producer. Without it, Gate A cannot start. This entry adds the producer. It measures; it decides nothing. The profile algebra and its thresholds stay as IDEA-035/037/040 fixed them.

All results are quoted costs, not realised fills (ledger rule 4).

## Design

`larp/marketdata/cost_summary.py`, two subcommands.

**`capture`** (needs the Web3 key pair; read-only). Each round, for each of the five bStocks, at a configurable size (default 40 USDT, a full 20 % position of the final 200 USDT):
1. Buy quote USDT → token (`aggregator/quote-and-swap`, through `MarketPort.quote`, so production's vendor and slippage parameters apply).
2. Sell quote for exactly the token units the buy quote returned.
3. A re-quote of the same buy after `--requote-seconds` (default 15 s, the profile's proposal lifetime): drift between quotes.
4. `aggregator/approve-transaction` for USDT and for the token, with that sample's amounts: approve `gasLimit × gasPrice`.
5. `pre-transaction/gas-limit` for the buy and the sell transaction: swap gas = `max(tx.gas, ceil(1.2 × gasLimit)) × tx.gasPrice` (the kit's rule). An estimate that fails is recorded, and the sample then uses `--fallback-gas-limit` (default 1 116 000 = 1.2 × the kit's largest observed route, 930 k gas).

It also takes one USDT → native-BNB quote per round for the BNB price. Each sample is appended to a JSON-lines capture file with the raw response artifact hashes (`Web3Client` stores every response, with credentials redacted). A failed quote is recorded as a failure, never as a value. The tool never signs, approves or broadcasts, and never reads a wallet key or `AI_SEEDS_SECRET` (never-do #13 does not apply: nothing is logged to ai-seeds).

**`summarize`** (offline). It reads every capture file and writes the summary and a report beside it.

| Field | Rule |
|---|---|
| `samples` | successful samples for the token |
| `median_impact_bps` | median of all buy and sell `priceImpactPercent × 100`, ceiled, at least 1 |
| `spread_bps` | median of (round trip − buy impact − sell impact), ceiled, at least 0. Round trip = (USDT paid − USDT from the sell quote) / USDT paid. |
| `fee_bps` | 0. Fees are netted in the quoted amounts, which the round trip already measures; settlement nets all USDT transfers the same way (`ALL_USDT_TRANSFERS_INCLUDED_IN_NET_CASH`). The report keeps any `tradeFee` the API returns. |
| `approve_gas_bnb_units` | 90th percentile (nearest rank) of the sample's larger approve gas, in wei |
| `swap_gas_bnb_units` | 90th percentile of buy and sell swap gas, in wei |
| `slippage_bps` | 90th percentile of the re-quote drift, ceiled, between 1 and 50 |
| `quote_ttl_seconds` | `--quote-ttl-seconds` (default 30, the kit's "expire after about 30 s"); recorded as kit-stated, since the API returns no expiry |
| `bnb_price_units` / `bnb_decimals` | median USDT money units per BNB from the BNB quotes / 18 (wei) |
| `observed_at` | the latest sample's `available_at` |
| `capture_hash` | SHA-256 of the canonical sorted sample records (each names its raw artifacts) |

**Refusals.** Fewer than `--min-samples` (default 10) per token; fewer than `--min-days` (default 3) distinct UTC days; no weekend sample when `--require-weekend` is on (the default; DR-01 asks for weekend coverage); any token that fails the consumer's own check (`quote_summary`). The report lists coverage, failures, fallback-gas counts and every parameter, so a reviewer can see how each number arose.

## Pass criteria (recorded before any test is written)

Synthetic Web3 responses only; no credentials or network.

| ID | Check |
|---|---|
| Q1 | `capture`, against a fake client: per token one buy, one sell (for exactly the bought units), one re-quote, approves for USDT and the token, two gas estimates; one BNB quote per round. Sample records carry the artifact hashes and no credential. No endpoint outside the read allowlist is called (the real `Web3Client` refuses broadcast). |
| Q2 | A failed quote becomes a failure record, never a value; a failed gas estimate uses the fallback and is marked. |
| Q3 | `summarize` computes each field exactly as in the table, from synthetic samples with known values (median, ceiling, p90 nearest rank, clamps). |
| Q4 | Refusals: too few samples, too few days, no weekend, a token whose costs fail `quote_summary`, a capture file with a malformed record. |
| Q5 | End to end: synthetic captures → `summarize` → the summary passes `quote_summary`, and `build_live_profiles` with the repo's predicate set builds both profiles. `capture_hash` changes when any sample changes. |
| Q6 | CLI: `capture` without the key pair exits 2 without a call; `summarize` refuses to overwrite an existing summary. |
| Q7 | Full suite: the base count plus only these tests, no new failure or skip. |

Not in scope: running real captures (owners, with the dev wallet's key), choosing the size or coverage for the frozen profile (owners' review), and pinning the summary or profiles.

## Capture runner (2026-10-15, criteria recorded before the tests)

Reason: `summarize` refuses without a weekend sample, so captures have to run through **Sat Oct 17 – Sun Oct 18 UTC**. The next weekend (Oct 24–25) falls after the rehearsal window opens (Oct 21). The owners need a runner they can start once and leave.

| ID | Check |
|---|---|
| Q8 | `capture --until <UTC time> --interval-seconds S` keeps capturing until that time: one round, then a wait, repeated. It writes one capture file per UTC day (`capture-YYYY-MM-DD.jsonl`), appending each round as it finishes, so a stop loses at most the round in progress. |
| Q9 | An unexpected error in one round is written as a `FAILURE` record with stage `ROUND`, and the loop continues. `--rounds` keeps working; `--until` in the past runs no round; `--until` and `--rounds` together are refused. |
| Q10 | `tools/run_quote_capture.sh` reads the key pair from the environment or a `.env` file without printing it, refuses to start without it, and runs `capture --until` in the background with a log file, keeping a Mac awake (`caffeinate`) when available. Its usage line names the weekend deadline. |

## Results (2026-10-15)

Synthetic Web3 responses only; no credentials, network or real quotes.

**Order of commits**
- Criteria: `6fd23a8`.
- Red tests: `57b7ff0`. 9 test methods, failing for the predicted reason (no module); the broadcast-refusal control passed.
- Build: `aa429e4`.
- Runner criteria: `8ddb7c8`; runner red tests: `aae5b2d` (3 failing); runner build: `54e673b`.

**Mutations.** Each was reverted, and each was caught by at least one test: gas median instead of p90; spread ignoring impacts; no weekend check; sell quoted for the pay amount; fallback gas not marked; no consumer check; no 1.2 factor; summary overwrite allowed; a round error ending the loop; a single capture file; `--until` and `--rounds` both allowed.
- Disclosure: a first mutation pass ran before the module was committed. `git checkout` could not revert an untracked file, so those mutations stacked, and only the first result was valid. The file was restored by hand, checked line by line, committed, and the mutation pass was repeated properly. The results above are from the repeat.

**Full suite.** Python 3.12.3 venv from `deploy/requirements-test.lock`, PostgreSQL 14.24 (the CI image's digest), bubblewrap installed.
- Base `02e2be9`: 1528 passed, 7 skipped (the same setup; 1525 passed / 10 skipped without bubblewrap).
- This branch at `54e673b`: **1540 passed, 7 skipped, 2133 subtests** (+12 tests: this change only).
- The same tree in the pinned `python:3.12.15-slim-bookworm` image: 1520 passed, 7 failed. Every failure is `git` missing from that image, an environmental cause.

**Mirror CI** (`Keegan4/keegan4-larp-ci-mirror`; workflow unchanged; mirror evidence, not org CI):
- `aa429e4`, the producer before the runner: [run 38772183332](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/38772183332). All four jobs passed, every step (Terraform both roots; pytest on Python 3.12.15 / PostgreSQL 14.24; real systemd; demo; Docker; host bundle).
- `54e673b` (runner): not yet run on the mirror.

| ID | Result | Evidence |
|---|---|---|
| Q1 | PASS | `Capture.test_q1_*` |
| Q2 | PASS | `Capture.test_q2_*` |
| Q3 | PASS | `Summary.test_q3_*` |
| Q4 | PASS | `Summary.test_q4_*` |
| Q5 | PASS | `EndToEnd.test_q5_*`: synthetic captures → summary → both LIVE profiles built with the repo's predicate set |
| Q6 | PASS | `Cli.test_q6_*` |
| Q7 | PASS | full suite above |
| Q8–Q10 | PASS | `Runner.test_q8_*`, `test_q9_*`, `test_q10_*` |

**Still open**
- Real capture is running on Keith's Linux server (see the dated run record below); finish coverage and summarize after the capture stops, without weakening coverage refusals.
- The owners' review of the size and coverage before a summary is pinned.
- Whether quoted amounts already net route fees (`fee_bps` 0 assumes so; the report keeps any `tradeFee`).

## Review fixes (PR 88, 2026-10-16)

Found in review; each new test failed against `717b6aa` and passes after the fix (`ReviewFixes` in the test file; R1's transient-error test is a control that passes on both).

| ID | Defect at `717b6aa` | Fix |
|---|---|---|
| R1 | A rejected key or region (`authentication_error`, `compliance_restriction`) or invalid parameters made every call fail, and the backgrounded capture recorded failures until `--until`. Nobody would have known until `summarize`, after the weekend had passed. | These outcomes are recorded as a `ROUND` failure, then raised; `capture` exits 2. Transient errors (`rate_limited`, HTTP errors) are still failures and the loop goes on (Q9 unchanged). |
| R2 | Day and weekend coverage was checked over all tokens together, so a token with weekday-only samples passed on another token's weekend. | Each token needs its own `--min-days` UTC days and its own weekend sample; the report lists each token's days. |
| R3 | A `--until` without an offset was read as the host's local time (in SGT, 8 h early), and a malformed one raised a traceback. | Both are refused before any round. |
| R4 | An error while building the sample record was labelled `GAS_ESTIMATE`. | Stage `RECORD`. |
| R5 | `run_quote_capture.sh` printed "running" even when the capture died at once. | It waits `STARTUP_CHECK_SECONDS` (default 10), and exits 1 with the log tail if the process has gone. |

Also: the test file's `unittest.main()` guard sat above the runner tests and now ends the file. Branch merged with `codex/system-testing-20261012` at `7a8a246` (the conflict was in `docs/LEDGER.md` only; both rows kept). Local: `tests/marketdata` + `tests/strategy` 153 passed, 1 skipped (Python 3.14, no PostgreSQL). The full suite and mirror CI were not rerun.

Not changed, for the owners: a gas estimate for a swap from a wallet with no allowance or balance will likely revert, so expect mostly `FALLBACK` swap gas (1 116 000 × gasPrice). The report counts them. A negative `priceImpactPercent` is refused by `number()`, as in `MarketPort.observe`, so such a quote becomes a failure, not a sample.

## 24/7 trading (2026-10-16)

The team position is that the tokens trade 24/7 (SKILL.md Q-32, IDEA-035 C8), so the agent can trade when the underlying US market is closed. A single median over all samples would let the capture schedule decide how much off-hours costs count. Changes:

| ID | Change |
|---|---|
| T1 | Each sample falls in a regime: `US_SESSION` inside a session of the frozen calendar (`config/runtime/session-calendar.2026.json`, IDEA-054; SHA-256 recorded in the report), otherwise `OFF_SESSION` (nights, weekends, holidays). Each cost field (impact, spread, both gases, slippage) is computed per regime and the summary takes the worse. The report keeps both regimes' values. |
| T2 | Each token needs `--min-samples` (default 10) in **each** regime, as well as its 3 UTC days and weekend sample. A sample outside the calendar's range is refused. `--session-calendar` selects another frozen calendar. |
| T3 | Each round reads the tokens' `openState` once (`market/rwa/tokens`) and records it per sample (`token_open`). The report counts open / closed / unknown per token and regime; nothing is filtered. This also measures how often the F-95 guard would fire (GAP-44). A failed status read is a `TOKEN_STATUS` failure and the samples carry `null`. |

Capture timing: Friday Oct 16's session is 13:30–20:00 UTC. If the capture misses it, the next session is Monday Oct 19, 13:30–20:00 UTC. The suggested `--until` is now `2026-10-20T00:00:00Z`; `summarize` can run earlier on the files so far.

Tests: `AroundTheClock.test_t1_*`–`test_t3_*`. The fixtures now place samples inside and outside the session (`complete()` gives 10 per token, day and hour block). Q3's NVDAB samples repeat in both regimes, so its expected values are unchanged. Local: `tests/marketdata` + `tests/strategy` pass (see the commit). The full suite and mirror CI were not rerun.

## Review fix: quoted `.env` values (PR 88 RV-88-01, 2026-10-16; criteria recorded before the tests)

Defect at `f0e5835`: `run_quote_capture.sh` copied each `.env` value literally, so `BINANCE_API_KEY="k"` exported the
quotes too. The capture would send the wrong key and sign with the wrong secret.

| ID | Check |
|---|---|
| Q11a | Double-quoted, single-quoted and unquoted values in `.env` reach the capture without their quote characters. |
| Q11b | `.env` is parsed by the pinned `python-dotenv` (`requirements.lock`) with interpolation off: a value holding `${OTHER}` or `$(cmd)` arrives literally; the file is never sourced or evaluated. |
| Q11c | A name already set in the environment keeps its value; `.env` fills only the names that are unset. |
| Q11d | No key or secret value appears on stdout or stderr in any of these cases. |
| Q11e | Each new test fails against `f0e5835` (Q11a, Q11c) or is a control that passes on both (Q11b, Q11d); the existing Q10 and R5 tests still pass. |

**Q11 results (2026-10-16): PASS.**
- Red first: against the old wrapper, Q11a failed for double-quoted, single-quoted and CRLF values (unquoted passed),
  and Q11c failed (a `.env` value replaced the environment's key). Deviation from Q11e: Q11b also failed on the
  old wrapper, not as a control, because its single-quoted value kept the quotes. The old wrapper never evaluated
  values either; Q11b now pins that the dotenv parse keeps `${...}` and `$(...)` literal.
- Fix `594ad07`: `.env` is parsed by `python-dotenv` 1.2.4 (`dotenv_values(".env", interpolate=False)`, run as
  `python -I`) and handed to bash as NUL-separated pairs on a pipe, so values never reach the terminal or a file.
  The environment keeps any name it already sets.
- Mutations, each caught by a Q11 test: export without the per-name precedence check; `interpolate=True`.
- Full suite, Python 3.13.16 venv from `deploy/requirements-test.lock`, local PostgreSQL 16.15 (not the CI image's
  14.24): head `594ad07` **1614 passed, 10 skipped, 2213 subtests, 0 failed**; base `e84083c` 1590 passed,
  10 skipped, 2201 subtests. The +24 tests are this PR's test file. The skips are the same in both (no bubblewrap,
  no disposable systemd runner, root ignores directory modes, opt-in recorded-market data).
- Not run: mirror CI on this head; real captures (still Isaac or Keith, with the dev wallet's key); the fee-netting
  check and profile approval stay with the owners.

## Real capture run — 2026-10-17 SGT (2026-10-16 UTC)

- Owner: Keith. Machine: Keith's Linux server (`linuxpc`, Ubuntu 24.04.5, Python 3.12.3), launched from tmux session `1`.
- Source: `codex/system-testing-20261012`, commit `eda2ed2ab1ab4b72f220eb6b92e882737d950825`. `git fetch origin`, branch checkout and `git pull --ff-only` succeeded on the server at this SHA. Working tree clean; no code changes.
- Start: **2026-10-16T18:19:07Z** (2026-10-17 02:19:07 SGT), before both Friday's 20:00 UTC session close and Saturday's 00:00 UTC weekend deadline. Stop: **2026-10-20T00:00:00Z** (Tue 08:00 SGT).
- Settings: interval **600 s** (the tool waits between completed rounds); default quote size **40 USDT**; default re-quote delay 15 s. The unchanged `tools/run_quote_capture.sh` dry run passed, then reported capture PID `91310` running until the stop time.
- Storage: `~/larp-captures`, **outside the repo**. Capture files, response artifacts, logs and credentials are not committed. Credentials are in the server checkout's Git-excluded `.env`, mode 0600; no wallet key or ai-seeds secret is used.
- First completed round: `capture-2026-10-16.jsonl` contains **5 SAMPLE records** (one each for NVDAB, GOOGLB, SKHYB, TSLAB and MSFTB), **1 BNB_PRICE record**, **0 FAILURE records** (failure counts by stage: none), and **10 FALLBACK swap-gas estimates**. Sample/price timestamps span `2026-10-16T18:19:09.205Z`–`2026-10-16T18:20:55.662Z`. The gas-estimate API errors became the expected fallback estimates, not failed samples. These are quotes, not realised fills.
- Twelve-minute health check: **2026-10-16T18:31:17Z** (02:31:17 SGT), 12 min 10 s after startup. PID `91310` alive; the daily file still has the first round's 5 samples, 1 BNB price and 0 failures; 44 raw response artifacts show the next round is underway. No capture restart or gap observed. The 600 s wait starts after a round completes, so the second round need not be written at the twelve-minute mark. Server time reports `NTPSynchronized=yes`. Restart, health-check and post-run commands are saved outside the repo in `~/larp-captures/RUN_NOTES.txt`.
- Server GitHub access: fetch and fast-forward pull succeeded; at 18:31 UTC a `git push --dry-run` for a new branch also succeeded. This verifies push authentication/transport without creating a remote branch; an actual server push and branch-specific protection checks were not performed.
- Host continuity: a separate `systemd-inhibit` process blocks idle/sleep through the capture stop time. Keep the Linux server powered, online and awake; tmux/nohup preserve the process when SSH disconnects. A reboot, power loss or forced sleep still interrupts it.
- Remaining: Keith monitors capture health and records any gaps here. After Oct 20 00:00 UTC, run `cost_summary summarize`, then the LIVE-profile builder; report coverage refusals without loosening flags. Isaac and Keith review the fee-netting assumption, summary and profiles before pinning (#118/#119/#120, GAP-69). This startup record does not close #118 or GAP-69, and no summary/profile is generated or pinned by this change.

## FN-01 — Isaac quote fee-netting check (#119, 2026-10-17, prospective)

Task: determine whether the quoted wallet input/output already include route fees, so `fee_bps = 0` is justified as an additional cost component. Existing summary code assumes netting; receipt settlement's net-transfer accounting alone does not prove quote semantics. This task is separate from the manual MetaMask first-gas record, which used a different route, and from #120 profile adoption.

Criteria before evidence analysis:
- **FN1:** use only existing public quote artifacts under `data/w08`, `data/execution-live` and any existing local quote-capture directory; inspect at most1000 JSON/JSONL files with no credential/env reads. Print/export only allowlisted public economic fields, source/endpoint/time, artifact hashes and counts. Raw responses stay outside Git. No Web3/RPC/API/model requests, new capture, signing, wallet/transaction, AWS or receiver action.
- **FN2:** bind each successful quote to chain56, the requested pair/amount and returned token addresses/decimals; retain exact fromTokenAmount/toTokenAmount/tradeFee/route and minimum output fields, distinguishing missing fee, numeric zero and nonzero fee. Inspect both directions and all available tokens/amounts/timestamps. Inspect source documentation already in the verbatim kit; optional public issuer documentation may be browsed, with exact provenance and no access bypass.
- **FN3:** do not infer fee asset, units, deduction side or inclusion from an unlabeled number or a plausible arithmetic match. The presence of tradeFee, a quoted round trip, minimum output or settlement netting alone does not prove net fee semantics. Require attributable vendor/source semantics or transaction-bound quoted-vs-wallet transfers, separately controlling gas/slippage/price movement, for a definitive netting conclusion. An unrelated manual swap is not a Binance quote-route fill check.
- **FN4:** record verified observations, competing interpretations and missing inputs with hashes in this entry and a reviewable document. If still uncertain, keep #119 and #120 open and label the zero-fee assumption honestly; do not invent a fee rate or claim live-profile acceptance. Any necessary code correction is preregistered here and committed/pushed before it runs, with meaningful offline tests. Independent PR closes only the investigation/tool or correction slice that is genuinely complete.

### FN-02 — bounded reporting correction (#156, prospective)

The FN-01 review found that Binance's dated Trading API describes `tradeFee` as a network-fee estimate in USD; it does not establish route-fee netting. Correct reporting and preserve evidence without changing cost arithmetic:

- **FN5:** future SAMPLE records retain `tradeFee`, `feeAmount`, `feeToken` and `actualSwapAmount` separately for BUY, SELL and REQUOTE, copying only present fields without conversion. Preserve absent vs null vs zero, and keep the legacy buy `trade_fee` unchanged. Verify distinct nonzero values on all legs and missing/null/zero cases with a synthetic client, without network calls.
- **FN6:** reports explicitly identify fee netting as UNVERIFIED (#119), explain the zero additional-fee assumption and identify legacy `trade_fees` as buy-only network estimates with the dated primary-source URL. Nonzero `tradeFee` must not be interpreted as a route-fee rate or added on top of existing gas estimates. Existing captures without the new fields must still summarize and produce the same numeric costs. Verify with meaningful offline capture/summary regressions and the existing marketdata/strategy tests.
- **FN7:** record observations and source limits in a review document, including exact examples and hashes; narrow GAP-50 to the remaining #119/#120 owner checks. Open a PR closing #156 only, referring to #119/#120. No host capture restart, new quotes, policy adoption, signing or broadcast is part of this correction.

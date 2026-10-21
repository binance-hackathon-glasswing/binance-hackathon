# IDEA-063 — QuoteCostSummary.v1 producer: measure quote costs read-only, then summarise (Gate A input 1)

- 2026-10-16 renumbered (Claude Code session, at Keegan's request, PR #88 review): this entry was first written as IDEA-057, which #85 (merged to `main`) uses for AIand evidence routing. The quote record and its references are now IDEA-063 so both records survive the merge. Commit messages before the rename still say IDEA-057.

- Date / owner: 2026-10-15 SGT / built with Claude Code at the user's request ("create the summary tool"). Runs with real quotes belong to Isaac or Keith (dev-wallet Web3 API key); the summary and profiles need Isaac's and Keith's review before they are pinned.
- Status (2026-10-20): completed capture/export independently verified; default summary and candidate profiles reproduced (DC-01). Selected-profile, fee-netting and measured signer-cap acceptance remain open.
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

### FN-01/FN-02 results — 2026-10-17

- **FN1/FN2 completed:** inspected 1,000 existing JSON files within the preregistered limit; 391 successful, request-bound chain-56 LiquidMesh quotes, all five bStocks in both directions, 40-USDT buys, Oct 15–16. Exact amounts/times, sample-selection limits, example hashes and the quote-set hash are in [the dated review](../build/QUOTE_FEE_REVIEW_20261017.md). No credential read, new quote, RPC, host action or trade.
- **FN3 netting verdict: inconclusive.** The primary Binance Trading API, Flash API response fields (checked 2026-10-17), defines `tradeFee` as estimated network fees in USD. All inspected quotes have nonzero `tradeFee` but null custom-fee fields and no custom-fee request parameters. This does not demonstrate an additional trading fee, nor prove all route fees netted. **Correction to the historical Design table:** its unconditional netting statement was an assumption; settlement's net-transfer accounting is not proof of quote semantics. No fee rate is inferred or added to gas.
- **FN4/FN7:** #156 contains the independently completable evidence/reporting correction; #119 stays open for Isaac's route-fee inclusion evidence or bound quote/fill comparison. #118 capture completion remains Keith's; #120 summary/profile review remains Isaac's and Keith's. GAP-50 narrowed, not removed. No profile pinned.
- **FN5/FN6:** regression commit `585512c` failed on the old producer as expected: missing fee-observation records and missing UNVERIFIED report metadata (7 failures including five stock subtests, 1 passed test). Fix `61cb527` retains the four raw fee fields on all three legs and labels the assumption and legacy buy-only network estimates. Missing/null/zero distinctions preserved; original captures still summarize; numeric costs unchanged. This changes evidence recording/reporting, not trading-cost arithmetic or profile validation. Existing server capture need not be restarted.
- **Verification at pushed application/test head `61cb527`:** Python 3.12.14, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /private/tmp/larp-pr20-venv/bin/python -m pytest -q -p no:cacheprovider tests/marketdata tests/strategy`: **235 passed, 1 skipped, 131 subtests passed**, 18.34 s. The recorded-market integration test is opt-in (external artifacts), so was skipped. Local log: `/private/tmp/larp-fee-netting-20261017-tests.log`. Full suite, hosted capture, live fill and CI acceptance not run for this change.
- **Delivery:** [PR #157](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/157), branch `codex/isaac-09-quote-fees-20261017`, targets the integration branch and includes `Closes #156`; #119's body now records the findings and remaining acceptance without closing it. PR is open for review, not merged. GitHub Actions run `39033396981`, runtime check `117398314355`, did not start: annotation says recent account payments failed or the spending limit must be increased (#98). This is not a CI test failure; no hosted acceptance is claimed.

## FN-RV157 — refreshed merge review (2026-10-18, prospective)

Yao Zhu requests review/fix/merge of PR157. Review head 9d8f168 and merge the
current integration base (including PR155) without rewriting history. Preserve
FN5/FN6: raw BUY/SELL/REQUOTE fields keep absent/null/zero distinctions, old
captures remain readable, numeric costs remain unchanged, and fee netting stays
explicitly UNVERIFIED with #119/#120 owner acceptance outstanding. Require the
marketdata/strategy subset and the PR155 cap/report subset to pass on the pushed
combined head; report platform/external-data skips honestly. Re-check the primary
Binance Flash API field definitions as a dated source check, not a quote/fill
comparison. No new quotes, wallet/host actions, profile approval or fee-rate
assumption is authorized by this review.

### FN-RV157 results — 2026-10-18

Pushed combined head `a3918e0` includes integration `2f10b9d` (PR155) by ordinary
merge. Full changed producer/tests and historical evidence reviewed; no further
code defect found. Primary Binance Trading API / Flash API response definitions
rechecked on 2026-10-18: `tradeFee` is still described as an estimated network fee
in USD. This supports the reporting label, not route-fee inclusion or actual fills.

First focused run: 267 passed, 1 failed, 1 external-corpus skip, 236 subtests.
The shell-wrapper test selected system `python3` without dotenv, while pytest
used the pinned temporary venv. Set the wrapper's supported `PYTHON` variable to
the same venv interpreter (no source/assertion change), then the complete same
subset passed: **268 passed, 1 skipped, 236 subtests**, 13.96s, macOS arm64 /
Python3.12. Subset: marketdata, strategy, caps, cap proposal and Gate B evidence.
Only skip: opt-in external recorded-market corpus. `git diff --check` passes.
No new Linux/release/host acceptance claimed. #119 fee-netting proof and #120
Isaac/Keith profile acceptance remain open; merging PR157 completes #156's
reporting/evidence correction only. The ongoing capture is not interrupted.


## KMP-QUOTE01 — verified interim handoff and capture recovery (2026-10-18 UTC)

Criteria: KMP-01/1536af8, before snapshot/summary work. [Handoff and caveats](../build/evidence/quotes-interim-20261018/README.md); [coverage](../build/evidence/quotes-interim-20261018/coverage.json).

The user clarifies earlier captures were interim data, not continuous operation. Checked actual tmux1:0.0: bash/sudo/systemd-inhibit/sleep kept the host awake, no collector. Historical capture exited on fatal authentication_error; underlying HTTP401/40103 says timestamp outside recv_window, request02:42:13.154Z versus server02:42:18.219Z (~5.1s). NTP synchronized. Fresh read-only token-list preflight with the same privately stored Web3 pair succeededHTTP200/552ms. No new keys needed; no timestamp/security window was relaxed.

Unchanged pushed capture implementation eda2ed2ab1ab4b72f220eb6b92e882737d950825 resumed at Oct18 06:54:40Z, PID106610, configured through Oct20 00:00Z at600s sleep after each round/40USDT/15s re-quote. Two completed resumed rounds verified,5 samples/zero failures each. This is health at inspection, not a future uptime guarantee. Existing files/logs preserved; no signing/approval/broadcast/ai-seeds credentials used.

Snapshot first/last observations Oct16 18:19:09.205Z–Oct18 06:56:06.986Z:1,021 complete JSONL records (850SAMPLE/170BNB_PRICE/1FAILURE), each token170 samples across3 UTC days including weekend,9US_SESSION/161OFF_SESSION. All1,700 swap-gas estimates FALLBACK; no measured final gas/cap claim. Largest inter-success gap per token about4h24m, explicitly retained. The snapshot includes26 exact referenced raw artifacts for the latest successful sample/token; older raw references remain in the private original store, so this is not an exhaustive raw export. Stored credential values screened remotely before export, no values disclosed.

Transport archive SHA d2127481bd8835a1f6f12abcaae5a39ed961c521c07ad1a49567c3de729e9520; manifest b6db3560fdbfd2e7f6b2fba70ddd6c99927567642b2edf95e95a7ba6b4e5a1b4; coverage1aac4be95d68dbc2e2c16bdfa902cb28beec9f4559a24b261e7650ae3a8a23df. Each transferred file's SHA/length verified. User-authorized sanitized data PR and #118 handoff supply Isaac's interim router inputs.

Default offline summarize, unchanged10samples/token/regime/3days/weekend, REFUSED every token's9US_SESSION<10. No weakened flags, final summary/profile or pin produced. Continue capture into Monday's session through Oct20, then final measurement/review #120. Old PC-AWS07 interim settings2days/9samples and owner-reported profile SHA d951207f432879eda6b349ae334104e47803f809eb5e94aef422c2e31cab4542 are recorded; original capture hash/full summary bytes still missing here (summary prefix41e17b4d only), need Yao's export. This later snapshot does not replace that provenance. Route-fee inclusion #119, actual router/deadline, final signer caps and final profile owner review remain open;40USDT quote size exceeds candidate35USDT signer input cap and is not a proposed trade.

## SP-FEE — current quote handoff and fee-evidence disposition (2026-10-18)

Verified all29 handoff hashes/lengths:850 samples,1,700 FALLBACK swap-gas
estimates,15 successful latest buy/sell/requote artifacts covering all five names.
Input quantities match request/response. Nonzero tradeFee is network-fee metadata;
null custom-fee fields do not prove wallet-net vendor/pool fees. Applicable
source/semantics and transaction-bound agent-quote/receipt evidence are absent.
#119/#120 stay open; collect the first planned agent swap only after gates.
Default final coverage remains refused (9 US-session samples,10 required);
40USDT quote size exceeds35USDT development signer input cap. No profile pin.

Full criteria, evidence, limits and remaining owners: [SP-01](../build/SIGNED_PREREQUISITES_20261018.md).

## YP-01 — recovered original interim-summary provenance (2026-10-19 SGT)

Criteria: IDEA-066 PC-YAO-NB01 (`47fa8f9`, pushed before verification). The user
requests remaining non-blocked Yao work from PR133. The old PC-AWS07/KMP-QUOTE01
summary/report/metadata originals were retained in Yao's download and deployment
copies. They are now supplied in
[`interim-provenance-20261019`](../build/evidence/interim-provenance-20261019/README.md).

At pushed verifier `6833462`: four transfer checksums PASS; summary SHA
`41e17b4d14322d79b0231544d81d058b128c039b6abb707de5f2c7a5f183be2b`, report
`0195e57623b6aa1bf6fdb9f02cbd6aa83f1dbe6d5c7ef763d42ddcfaba824f89`, capture
`2ec51d514bff738a1b09a5c0be694d69a0e1334dc3bc2990b9c7d57354dde7da`.
The metadata's two original capture byte prefixes in the later committed export
verify against their pre-existing hashes/counts:180+336 records,516 total. The
current summarizer reproduces the complete summary object and report coverage/
symbol details. Actual retained profile SHA `d951207f…4542` matches the previously
reported SHA; its embedded summary equals the original. No profile regenerated.

This completes Yao's missing-original handoff, not Keith's independent review.
Historical originals retain the unverified fee-netting statement; FN3/#119
supersedes that assumption. Coverage is still2days/9US-session samples/token,
all860 swap-gas estimates FALLBACK; final defaults correctly refuse. Raw API
responses were not reverified. Final capture/profile, #119/#120/#44 acceptance
and full-holdings/gas inputs remain open with Keith/Isaac. Results and reproducible
verifier are in the linked directory; no new market/host/wallet operation.

## DC-01 — completed Desktop capture analysis (2026-10-20, prospective)

Keith requests continued development using the completed Desktop capture and a
completion update on PR133. Use canonical `codex/system-testing-20261012` at
`928b8a8`; PR133 remains an open noticeboard. Scope is the independently
completable LD09 capture-analysis/profile-construction slice, not installation
or acceptance of the whole measured execution packet.

Pass criteria, committed before analysis:

1. Verify every payload against the export's SHA256SUMS, all JSONL records and
   their raw-artifact references; retain the manifest/daily-file hashes and
   capture-source identity. Do not commit raw captures, API responses or logs.
2. Run the existing offline summary with unchanged defaults: three UTC dates,
   weekend coverage and ten samples per token per regime. Preserve failures,
   interruptions, fallback gas and UNVERIFIED fee-netting labels. Any refusal
   remains a refusal; do not tune thresholds or remove observations.
3. Reproduce the delivered YP-01 interim provenance independently. Keep its
   original two-day/nine-sample provenance separate from this completed export.
4. Run existing profile construction against the completed summary and the
   published predicate set. Generated EQUAL_WEIGHT profiles are review candidates
   only. Do not invent S1 weights, adopt example parameters/windows, approve
   fallback gas, or enable signing. Record exact file and document-domain hashes,
   minimum size, amounts/reserves and comparison to the draft 35-USDT dev cap.
5. Retain a reproducible verification receipt, complete summary/report and
   candidate profiles with explicit limits. Enumerate unsupported sizes/full
   exits, gas/fee evidence and remaining owner reviews. Run the existing
   marketdata/strategy tests; distinguish local verification from hosted CI.
6. Update the canonical backlog to remove only completed work and link a focused
   PR. On PR133, check off this completed analysis slice and keep LD09's missing
   current measurements and #119/#120/#44 acceptance open. No host, provider,
   model, wallet, signing, spending or deployment operation is in scope.

### DC-01 results — 2026-10-20

**Capture/summary/candidate-construction slice complete; acceptance remains
open.** Detailed findings, exact hashes, commands, owner handoffs and the
reproducible verifier/receipts are in
[quotes-complete-20261020](../build/evidence/quotes-complete-20261020/README.md).

- Criteria pushed at `4035d93`; unchanged canonical producer/builder exercised
  at `4a496a0`. Final verifier pushed at `85adb01` before execution. Verified
  all14,268 export payload checksums/14,258 artifact addresses;14,257 reversible
  HTTP bodies rehash exactly. One unreferenced non-JSON HTTP502 has no retained
  body; only its transport hash exists. Every successful sample/BNB record's
  referenced artifacts and request/response amounts, chain, tokens and vendor
  bind; approve/fallback gas products and openState metadata reproduce.
- Unchanged defaults PASS:1,924 samples,385BNB quotes,four UTC dates/both weekend
  dates,42–43 US-session and342 off-session samples/token. Two failures and
  largest BNB success gap4h24m44.160s retained. All3,848 swap-gas estimates are
  FALLBACK. All successful token-open observations are true; no continuity or
  future-open guarantee follows. Fee inclusion remains UNVERIFIED (#119).
- Summary capture hash
  `407a08e744aaaaf95e30f006deb56a59b220a2bb2fe1f8b9b21b4fc118986ecd`;
  summary file `9d4479e3b02e0aceb2c739e7292b8ca80043972b5c258734c7439a979ef1946a`.
  Rehearsal candidate file
  `401739f5dfdcbbd38e26a58c66fa76855e5377427234ca60fb0b7a8395d4060f`;
  final file `7151a55d145d64d17c9cec880442027a947bb05f58c7af11cf1426eab3f61bae`.
  Both summary/report objects and both candidate file bytes reproduce exactly.
  Existing EQUAL_WEIGHT policy/windows preserved, no S1 values invented/adopted.
- Minimum17.745807USDT; rehearsal/final cash caps20.10/40.20USDT; top-up
  cash0.663460USDT. These cash amounts fit the respective draft35/70 caps.
  Historical buys are all40USDT (all exceed the dev35 input cap); sampled sells
  fit draft stock-quantity caps but are not actual full holdings. One NVDAB BUY
  fallback gas product202,073,877,828,000wei exceeds draft200,000,000,000,000wei.
  This exception is identified by exact timestamp/quote hash in the receipt;
  p90 values below the cap do not establish worst-case coverage. No cap changed.
- Keith independently replays YP-01: original interim summary object, report
  coverage/symbols and original516-record byte prefixes match. Its original
  two-day/nine-US-session coverage still refuses final defaults. That older
  provenance remains distinct and is no longer waiting on Keith's replay.
- Local macOS arm64/Python3.12.14 regression: marketdata+strategy **249 passed,
  1 external-corpus skip,161 subtests**,16.96s. No application module/config
  changed. No full suite, Linux/host/release or hosted-CI acceptance claimed.
- Remaining owners: Isaac/Keith #120 exact selected profile/size/hash review;
  Isaac #119 attributable fee evidence; approved operator/Isaac fresh holdings,
  requested-size/full-exit quotes and actual usable gas; Keegan/Isaac LD07/08
  gas-scope decision/qualification; Keith/Keegan LD11 selected strategy values;
  Isaac LD10/#44 final measured caps decision. No live pin/readiness flag,
  signing, provider, spending, host or deployment action. LD09 stays partial.

### DC-01 delivery — 2026-10-20

[PR197](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/197)
targets canonical `codex/system-testing-20261012`; review/merge remain pending.
PR133's noticeboard now checks **LD09-DC01** complete and links this delivery;
LD09 retains its current-data/#119/#120/#44 prerequisites. PR197 identifies
#118's completed construction deliverable for closure on merge, without closing
the separate review gates. Final audit replay is byte-identical to the retained
receipt and all eight derived-file checksums pass. Original user checkout and
Desktop export remain untouched; no deployment or readiness change.

## DC-01-R1 — independent reproduction from the raw daily files (2026-10-21, Keegan session)

Keegan uploaded the DC-01 raw export subset to the root of `main` (`8c393d3`, "Add files via upload"): the four
daily JSONL files, `SHA256SUMS`, export metadata, run notes and logs. The API-response artifacts aren't included.
Its `SHA256SUMS` hashes to `b17002b0…ffc01`, the DC-01 manifest, so this is the same capture as Keith's archived
ZIP on the `capture` branch (ZIP-01), not a new one.

Check, written before running it: canonical `9c1cb84` `cost_summary summarize` with default settings, run on the
four uploaded daily files, must reproduce the committed `quote-cost-summary.json` and `.report.json` byte for byte.

Result: **PASS.** Both files are identical; the summary is `QuoteCostSummary.v1` `407a08e7…6ecd`. No network was
used. A secret scan of the uploaded text files (credential, key and authorization patterns, URLs, long tokens) found
nothing. The only address is the public development wallet, which is already in canonical docs. The upload isn't on
canonical, and no history was rewritten. Whether to keep those root files on `main` or remove them with a normal
revert commit is Keegan's choice; the ZIP on `capture` is the archival copy.

## RV120-01 — #120 owners' review of the DC-01 quote-cost summary (2026-10-21; prospective)

This review was prepared in Keegan's session under his delegation ("follow the recommended option"), from the
DC-01 capture contents: the four daily JSONL files, manifest `b17002b0…ffc01`, the same capture as ZIP-01 and
DC-01-R1. **Isaac and Keith remain the #120 owners and confirm or amend.** Criteria, written before the analysis
(C1–C7):

- C1. Coverage from the raw files: samples per token and regime, UTC days, weekend days, failures, fallback gas
  estimates and `openState` counts per regime. These must match the committed report.
- C2. Quote size against the per-trade caps: the 40 USDT quote compared with the final (40.2 USDT) and rehearsal
  (20.1 USDT) caps, with LD02d's size sweep as the evidence for using the 40 USDT figures at other sizes.
- C3. Distributions behind each rounded summary value, per token and regime: round trip, spread residual, impact
  and 15 s requote drift (p10/median/p90/max). Each worse-of-regime value must be explained, MSFTB's 17 bp included.
- C4. The 50 bp entry-cost cap checked per token with the profile formula
  (`spread + min(50, 2 × impact) + fee + gas/size`). This uses the LD09-B sizing gas (0.064 gwei) and the cap gas
  (0.16 gwei), at 18.64, 20 and 40 USDT, plus a tail check with the off-session p90 round trip.
- C5. Slippage: the 8 bp setting compared with the drift distribution, and the expected revert rate stated.
- C6. Fee (#119) and gas: state what the capture can and can't show; the gas figures come from LD02b–d via LD09-B.
- C7. Recommendations as proposals for the owners: profile choice for the rehearsal, rehearsal window dates and
  seeding N, each with its derivation. Nothing is pinned, released or approved by this record.

### RV120-01 results (2026-10-21)

Review: [QUOTE_COST_REVIEW_120_20261021.md](../build/QUOTE_COST_REVIEW_120_20261021.md); analysis and output in
`docs/build/evidence/rv120-quote-review-20261021/`. Disclosure: an exploratory run of the same distribution
script came before C1–C7 were written. It showed the MSFTB regime split, so C3 was written knowing that one fact.

- **C1 PASS.** The raw files match the committed report: 1,924 samples and 385 BNB quotes; 42–43 US-session and 342
  off-session samples per token; 4 UTC days including both weekend days; 2 failures; 3,848 FALLBACK gas estimates;
  `openState=true` on every sample.
- **C2 PASS.** Every sample is 40 USDT, the final full position (cap 40.2 USDT). LD02d shows no size dependence from
  10 to 100 USDT, so the figures apply to the 20 USDT rehearsal size.
- **C3 PASS.** Every worse-of-regime spread is the off-session median. **MSFTB's 17 bp is its off-session median
  (16.99)**, against 6.99 in US hours, which is where LD02d's 6.7 bp was measured. The LD09-G1 "refresh MSFTB to
  about 7 bp" suggestion is withdrawn. MSFTB's tails are fat: US p90 32.7 bp, maximum 50.3 bp. Impact is ≈ 0 bp at
  40 USDT.
- **C4 PASS at the sizing price.**
  - At 0.064 gwei: 33–48 bp at 20 USDT and 18–33 bp at 40 USDT. MSFTB is exactly 50.0 bp at the 18.64 USDT minimum,
    by construction.
  - Pair gas is about 29 bp of a 20 USDT trade. This corrects an earlier session estimate of 2.9 bp.
  - At the 0.16 gwei cap, 20 USDT entries cost 76–91 bp and the gate refuses them, which is the intended outcome.
- **C5.** The 8 bp slippage is exceeded by 0–9.5 % of 15 s requotes per token and regime (worst: MSFTB US 9.5 %,
  SKHYB US 9.3 %), as the p90 design implies. Recommendation: keep it, and measure the revert rate at LD19/LD20.
- **C6.** Fee: the netting assumption remains UNVERIFIED (#119, LD19/LD20). Gas: FALLBACK is not used; LD09-B
  supplies the budgets.
- **C7 proposals for Keith and Isaac:**
  1. accept DC-01 as the input;
  2. use the measured EQUAL_WEIGHT fallback for the rehearsal unless S1 weights are frozen (they need price series,
     which the capture doesn't have);
  3. set a new rehearsal window: trade from 2026-10-23T00:00Z, new risk until 2026-10-25T00:00Z, flatten from
     2026-10-26T00:00Z, signing end 2026-10-26T14:45Z;
  4. seeding N ≈ 15 for the rehearsal (≈ 0.0046 BNB; the dev wallet holds about 0.0027) and N ≈ 30 for the final
     run (≈ 0.0083 BNB).

**#120 is not closed by this record:** Isaac and Keith confirm or amend.


## RV120-02 — delegated rehearsal window and profile rebuild (2026-10-21)

Authority: Keegan's session requests the remaining mechanical part of step 1 and recommended
choices for decisions; Keith retains the profile confirmation. Issue #120 had only RV120-01
when checked; this record does not impersonate Keith or Isaac or close their sign-off.

Selected for this rebuild: DC-01 summary, measured EQUAL_WEIGHT rehearsal fallback, MSFTB
spread 17 bp, impact 2 bp, slippage 8 bp, quote age 30 s, fee 0 conditional on #119,
LD09-B action/sizing budgets unchanged. Recommended seeding plans: N=15 rehearsal and
N=30 final (approximately 0.0046/0.0083 BNB); funding remains a separate owner action.
Rehearsal UTC window: trade_after October 23 00:00; new_risk_end October 25 00:00;
flatten_start October 26 00:00; signing_end October 26 14:45. Final dates remain unchanged.
This selects candidate inputs only: LD10 signed-child/holdings envelope acceptance remains
open, including independently rounded pair gas exceeding the historical nominal budget.

Prospective pass criteria (before running the changed builder or tests):
- P1: generate both profiles offline from the exact LD09-B command into a new evidence directory;
  repeated builds must match byte for byte and validate as StrategyProfile.v1.
- P2: rehearsal has the four UTC dates above and RV120-02 window provenance; all other values
  match LD09-B. Final candidate is byte-identical to LD09-B. Retain historical artifacts.
- P3: strategy tests pass, including historical artifact reproduction under historical windows;
  mirror runtime.yml passes infrastructure aws/bootstrap, runtime and host-bundle.
- P4: record exact file and document hashes; narrow GAP-50/GAP-69/KMP-QUOTE01 to remaining
  acceptance/measurement work without claiming fee, caps, signer, deployment or trade readiness.

Results: pending execution after this pre-registration and implementation are committed and pushed.

### RV120-02 local verification (2026-10-21)

P1/P2 PASS at pushed source `839658d`: repeated construction matches every byte; both
StrategyProfile.v1 documents validate; rehearsal differs from LD09-B only in the four
window values/provenance; final is byte-identical. Exact hashes and reproduction command:
[RV120-02 packet](../build/evidence/rv120-profiles-20261021/README.md).
Strategy suite: 205 passed / 80 subtests passed (6.41 s). Add the new packet to the existing
artifact-reproduction parametrization before mirror qualification. P3 mirror result pending.
P4 backlog updated; owner confirmation, fee netting and LD10 coverage retained.

### RV120-02 qualification result (2026-10-21)

P3 PASS: implementation/candidate head `b0da2ca7e8886ac159a564f2b0e1bb16c9324857`,
[mirror run 39606912446](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39606912446),
all four jobs SUCCESS: infrastructure deploy/aws, infrastructure deploy/bootstrap,
runtime, host-bundle. Runtime: 2408 passed / 7 skipped / 3801 subtests; separate
real-systemd check: 5 passed / 5 subtests; offline demo and Docker build/run PASS.
Updated local strategy suite: 206 passed / 80 subtests. P4 PASS: exact file/document
hashes and outstanding acceptance are in the packet and backlog. PR #229 targets the
canonical integration branch. This qualification covers this profile rebuild only;
it is not the later LD15 release candidate or permission for host writes/trading.
The following result-record commit changes documentation only.


## RV120-RV01 — Keith inline-review corrections (2026-10-21; prospective)

Source: Keith (wtvlol), PR226 review5602037122 and inline findings
[4338622249](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/226#discussion_r4338622249) /
[4338622255](https://github.com/binance-hackathon-glasswing/binance-hackathon/pull/226#discussion_r4338622255),
submitted2026-10-21T15:23:22Z, anchored to3bd8a388a66ab74d5ff8f1a003ee859c0c98dcc6.
Keith confirms original raw distributions reproduce and supports the17bp MSFTB
off-session spread. Review state COMMENTED; it requests two corrections, without
an explicit acceptance of the current exact profile/gas/model/funding bindings.

Pass criteria before new analysis: R1 preserve original distributions/script and
raw ZIP bytes; verify original capture archive/daily/calendar hashes; R2 report
two-sided absolute, adverse BUY-output and favourable exceedances of8bp separately
using exact integer comparisons, retaining sample denominators; R3 independently
match Keith's adverse counts1/42 MSFTB US,2/43 SKHYB US and10/342 SKHYB off-session;
R4 remove unsupported fill/minimum-output guarantees and simulated/actual revert
frequency claims, while retaining the observed LD02d simulation as dated evidence;
R5 selected profile/policy/runtime bytes stay unchanged, actual fee/owner/config/
host/revert acceptance remains open. No live call, host, key, funding or trade.

### RV120-RV01 results — both inline findings addressed

Pushed analysis source2efffcf,1924 samples from the original capture branch ZIP
2dcb92c67c4e041019aeba759518e1aeb699182a59e4cb5016db2937be6f4755.
Original payload manifest b17002b0…ffc01 and all four daily-file hashes verify.
Original analyse.py reproduces distributions.json byte-for-byte. New directional
report a1d98b74c2a78e479de999d5de9ca84e107163899ee82a313616e1220f2d4ed5
partitions all10 token/regime absolute counts into adverse/favourable subsets.
Keith's adverse counts match exactly: MSFTB US1/42(2.4%), SKHYB US2/43(4.7%),
SKHYB off-session10/342(2.9%). Those are counterfactual quote-output movements,
not an actual or simulated transaction revert frequency. RV120-01 C5's old
revert-frequency interpretation is withdrawn; its absolute-drift values remain.

QUOTE_COST_REVIEW_120 now removes the unsupported fill-safety guarantee and states
accepted unverified minimum-output/recipient enforcement, possible abnormal fills,
prepare-time simulation mitigation and post-execution LD05 detection/quarantine.
Actual LD19/20 outcomes/reverts remain unmeasured. Historical distributions, raw
source and selected profile/policies are unchanged; all205 runtime release files
are unchanged. This is analysis/documentation validation, no new full-suite/CI.
Raw four-file extraction remains private at /workspace/scratch/rv120-inline-raw.

Keith's COMMENTED review confirms reproducibility and supports the17bp spread;
it is not an exact current-profile/gas/model/configuration adoption attestation.
Fee netting, final scored adoption and actual LD16/17/19/20 owner/configuration/
host/fill acceptance remain separate. No live/host/key/funding/trading operation.

RV120-RV01 canonical sync: PR230 merged while this correction was being prepared
(canonical57af68a). Preserve LD10-P02's new BLOCKED_EXECUTION_CASH_CAP finding:
the hypothetical maximum NVDAB SELL returns20.106983099120719276USDT above20.10.
Actual stock holdings in the dated packet are zero; this is a full-exit coverage
gap requiring a reviewed complete-position disposition/count/reserve and fresh
evidence, not a trapped actual position or a reason to loosen limits silently.
Keith's data review does not settle that gate. PR230 changes coverage-check code;
the older b22207e artifact does not qualify that new source. This review's own
delta remains analysis/documentation only with no runtime/profile/policy change.

# IDEA-087 — Wallet dashboard published as a static GitHub Pages site

- Date / author: 2026-10-23 / Keith (request), Claude Code (build)
- Status: open (pre-registered below; built on branch `claude/idea087-pages-dashboard-20261023`); DX (decisions) built on branch `claude/zen-meitner-luu8xj`
- What: two tools under `tools/dashboard/`.
  - `build` turns the SJ-08 chain monitor's output folder
    (`docs/build/ops/rehearsal-install-20261022/mac/chain-monitor.py`: `snapshots.jsonl`, `transactions.jsonl`,
    `alerts.jsonl`) into one self-contained `index.html`, a `data.json` and a `.nojekyll` file. The page shows equity,
    return and drawdown charts, holdings, swaps and alerts.
  - `publish` builds the site and pushes it as a new commit to the Pages branch of a GitHub repository, once or in a
    loop.
- Why it might help: today the team watches the rehearsal with one terminal line per poll on whichever Mac runs the
  monitor, plus BscScan. A page that rebuilds every few minutes lets all four of us follow equity, drawdown (the
  tie-break metric, F-45), gas and alerts from a phone during the dev rehearsal and the scored run. Nobody needs AWS
  access or a checkout.
- Cost / risk:
  - **Outside the agent.** It reads only the monitor's files: public chain data plus Web3 prices from the read-only
    key, which the monitor already fetches. It never touches the hosts, database, signer, credentials or the
    registered build. It is not a version event and is not a human action on the agent (SKILL.md §0.3 items 1 and 5;
    F-114, F-117), any more than reading BscScan is.
  - **Visibility.** The org is on GitHub Free (checked 2026-10-23: `plan.name = free`). Pages there are available only
    for public repositories, and a Pages site is reachable by anyone with the URL. The main repo must stay private
    (F-24), so publishing needs a separate repository that holds only the built site, never source code. Redaction is
    therefore the default: no wallet address, transaction hash, contract or spender address, block number or nonce
    leaves the build unless `--full` is given. Holdings, swaps and timing are still visible on a public page. Whether
    and where to publish is the team's decision.
  - **Not the official score.** Equity excludes BNB and uses Web3 `rwa/price`, as computed by the monitor. The
    official valuation source is not published (F-42, F-43).
  - **GitHub limits.** Branch-based Pages builds have a soft limit of 10 per hour, so the loop defaults to 600 s and
    commits only when the data changed. Org Actions are blocked by billing (2026-10-23 runs: "recent account payments
    have failed or your spending limit needs to be increased"). Public-repository Pages builds may still run; that is
    unverified.
- Links: IDEA-049-C SJ-08 (chain monitor), `docs/build/ops/rehearsal-install-20261022/README.md` "Live measurement";
  SKILL.md F-24, F-42..F-46, F-114, F-117; G-06 (no secrets in logs or repo).

## Pass criteria (written before any test is run)

Offline, with synthetic monitor files only (no real wallet data, no network):

- **D1 numbers:** from a synthetic monitor folder, `data.json` reports the hand-computed values to within 1e-9:
  latest equity, start equity, return vs start (USDT and %), maximum drawdown (%, peak and trough times), current
  drawdown, realized and unrealized PnL, gas spent, swap and failed-transaction counts, and holdings weights.
- **D2 redaction:** with the default (redacted) build, no file in the site contains the wallet address, any
  transaction hash, the router or any spender address, a block number or a nonce. No `0x` followed by 8 or more hex
  digits appears anywhere in the output. Redaction works by allow-listing output fields, not by deleting known ones.
- **D3 determinism:** two builds from the same input are byte-identical, and the output contains no build-time clock.
  The page works out staleness in the browser from the last snapshot's time.
- **D4 robustness:** the build succeeds and reports what it skipped (no crash) for:
  - a missing or empty monitor folder;
  - a truncated last JSONL line (the monitor mid-write);
  - a malformed line in the middle of a file;
  - snapshots with `price_error` set and no equity.
- **D5 isolation:** the build opens no network connection (sockets blocked in the test) and reads only the three
  monitor files. In particular it reads no `.env`.
- **D6 publisher**, against a local bare git repository:
  - the first publish creates the Pages branch with `index.html`, `data.json` and `.nojekyll`;
  - republishing identical data makes no commit;
  - changed data makes exactly one new commit that fast-forwards the branch;
  - the publisher never force-pushes;
  - a remote branch that diverged from the local clone stops the publish with an error instead of overwriting it.
- **D7 page renders:** the fixture site opened in a browser shows the KPI tiles, both charts with hover, holdings,
  swaps and alerts, with no console errors. This holds in light and dark mode and at 375 px wide with no horizontal
  scroll.

Not claimed by these criteria: a live GitHub Pages site (needs a repository and a visibility decision), real monitor
data, or hosted CI.

## Results (2026-10-23, code commit `46ac41be`)

All seven criteria are **supported offline**, on synthetic data only. Setup: macOS, Python 3.12.14, git 2.55.0.
`pytest tests/test_dashboard.py tests/test_contracts.py` gives 30 passed with 44 subtests. Full collection finds 2,513
tests with no errors.

| Criterion | Result | Evidence |
|---|---|---|
| D1 numbers | supported | `test_d1_numbers_match_hand_computation`, `test_d1_transactions_and_alerts`. Equity 94.9, start 96, return −1.1 USDT, max drawdown 2.5/97 (peak 00:02, trough 00:04), current drawdown 2.1/97, holdings weights and fills all match to 1e-9. |
| D2 redaction | supported | `test_d2_redacted_site_has_no_identifiers` checks that no `0x…` of 8 or more hex digits or identifier key is in any output, while `--full` keeps them. `test_d2_redaction_is_an_allow_list` puts addresses and hashes into kinds, symbols, unit keys and `price_error`; every one becomes `OTHER`. |
| D3 determinism | supported | `test_d3_build_is_deterministic`: byte-identical output, still identical with the clock patched to fail, and the embedded data equals `data.json`. |
| D4 robustness | supported | Four tests: a missing or empty folder; one malformed line plus a truncated last line, both counted and reported; the latest poll without prices (equity taken from the last priced poll, values blank); and 5,000 polls downsampled to at most 2,402 points with the trough kept. |
| D5 isolation | supported | `test_d5_no_network_and_reads_only_monitor_files`: sockets blocked, and the build reads only the three monitor files and its template. A planted `.env` is not read. |
| D6 publisher | supported | Five tests against a local bare repository: the first publish creates `gh-pages` with the three files; an unchanged rerun makes no commit; changed data gives one fast-forward commit; no force flag or `+` refspec appears in any git call; other files on the branch are kept; a diverged remote raises and leaves both sides untouched; a failed push is retried on the next run; the main repository is refused by name and by URL. |
| D7 page renders | supported | Built-in browser on a synthetic two-day run (2,881 polls, 17 transactions, 5 alerts). Redacted dark mode at about 830 px and full light mode at 375 px both show every section with no console messages, and `scrollWidth` equals `clientWidth`. The crosshair and tooltip stay in sync across both charts. BscScan links appear only in the full build. One fix came from this check: the opening-value line was nearly invisible in dark mode and now uses the muted ink at 70%. |

- Release bundle unaffected: `tools/` and `tests/` are outside `release_files` (`larp/runtime/preflight.py`). No
  existing source file changed.
- Not run: the full suite, which needs disposable PostgreSQL and Linux worker isolation. This change touches none of
  its code. Hosted CI is unavailable (org billing).
- Not done: no Pages repository exists, nothing was published, and no real monitor data was used (none is on this
  machine). Whether to publish, and where, is `INCOMPLETE_WORK.md` IDEA-087 PAGES01. Usage: `docs/build/DASHBOARD.md`.

## Review RV1 (2026-10-23, assistant review of PR263)

- **Finding (medium), fixed:** `refuse_main_repository` compared the target only with `origin`'s slug, and `slug()`
  recognises only `github.com` URLs. On a checkout whose `origin` is an SSH host alias, a proxy or a mirror,
  `slug(origin)` is `None` and the private registered repository was not refused. The existing test skipped itself in
  exactly that case. Now the repository named in `config/release/repository.v1.json` is always refused, as well as
  `origin`, for both `--repo` and `--remote-url`.
- New test `test_d6_refuses_the_registered_repository_without_a_github_origin` fakes a proxy `origin`. It fails
  without the fix and passes with it. `tests/test_dashboard.py` and `tests/test_contracts.py`: 31 passed, 0 skipped
  (Linux, Python 3.12).
- Checked, no change: the template writes data only through text and attributes (no `innerHTML`); the embedded JSON
  escapes `<`, `>` and `&`; redaction is an allow-list; publishing pushes fast-forward only and stops on divergence.

## Extension DX: the agent's decisions on the same page (2026-10-24, pre-registered)

- Request: Cookiemunchrr (on PR 272, run 4 live), "a gh pages dashboard for us to take a look at the trades and the
  decisions for the bot". The page above shows only what the chain monitor sees (trades). The decisions (each round's
  policy targets, planner orders, rejections and close status) exist only in the run's database on the primary.
- What: three parts. **None of them runs on the agent's path or changes the registered build.**
  - `tools/dashboard/decisions-export.sh` (first written under the RC7 run folder's `checks/`, moved out 2026-10-24
    because the run-4 sheet test pins that folder's file list): a read-only primary check, run over SSM
    like `trading-status.sh`. It runs one READ ONLY transaction and prints one allow-listed JSON line per round (the
    latest N, default 30; PR274-RV01 additionally bounds complete output to22,000 UTF-8 bytes below SSM's24,000-character inline limit and reports rows omitted for size).
  - `python -m tools.dashboard.decisions merge <ssm stdout> --monitor-dir <dir>`: merges an export into
    `<monitor dir>/decisions.jsonl` (git-ignored), keyed by round ID, so repeated exports build up the whole run.
  - `tools/dashboard/build.py` reads `decisions.jsonl` when present and the page gains a "Decisions" section.
- Fields, allow-listed both on the host and in the build: round time (decision, else start), close status, round kind,
  error codes, orders (symbol, side, amount), intents (symbol, side, mandatory, reason codes), policy targets (symbol,
  kind, reason code, weight), planner rejections and clamps (symbol and reason code), evidence assessment (issuer,
  status, reason codes). Never: free-text `detail`, model text or reasoning, request or quote bodies, intent or quote
  IDs, hashes, addresses, config, DSN or URLs.
- Visibility: on a public Pages site the decisions show the strategy's targets and reasons as well as its trades. The
  round ID (which can name a filing job) is shown only with `--full`. Whether to publish stays PAGES01.

### Pass criteria (written before any test is run)

Offline, synthetic data only (no database, no network):

- **DX1 export allow-list:** the export's shaping code, run on synthetic `ROUND_PLANNED`, `PLAN_REJECTED` and
  `ROUND_CLOSED` events that plant free text, `0x` addresses, hashes, intent and quote IDs and a model reasoning text,
  emits only the allow-listed fields. No planted value appears in its output. A code-shaped field holding anything else
  becomes `OTHER`. The script's database part reads in a READ ONLY transaction and writes nothing (checked by reading
  the script: `SET TRANSACTION READ ONLY`, SELECT only).
- **DX2 merge:** merging an export creates `decisions.jsonl`; merging the same export again leaves it byte-identical;
  a later export in which an open round has closed updates that round; non-decision lines (the summary, other
  sections, garbage) are ignored and counted; the result is sorted and deterministic.
- **DX3 numbers:** with a synthetic `decisions.jsonl`, `data.json` reports the hand-computed counts: rounds, rounds
  by close status, rounds that placed orders, orders by side, and the top rejection reason codes. Rows are newest
  first and capped.
- **DX4 redaction:** the redacted build contains no round ID and no `0x` with 8 or more hex digits, and none of the
  planted values from DX1/DX2 reaches any output file. The full build keeps the round ID. D2, D3 and D5 still pass with
  a decisions file present (D5's allowed reads gain `decisions.jsonl` and nothing else).
- **DX5 page:** in headless Chromium, the fixture site shows the Decisions section with its rows, in light and dark,
  and at 375 px wide without horizontal scroll, with no console errors. Without a decisions file the section says no
  decisions have been exported yet and the rest of the page is unchanged.
- **DX6 regression:** every existing `tests/test_dashboard.py` and `tests/test_contracts.py` test still passes.

Not claimed by these criteria: a run of the export on the live primary (needs an SSM operator), real decision data,
or a published site.

### Results DX (2026-10-24)

All six criteria are **supported offline**, on synthetic data only. Setup: Linux, Python 3.13 venv with pytest,
headless Chromium (Playwright). `pytest tests/test_dashboard.py tests/test_dashboard_decisions.py tests/test_contracts.py`
gives 40 passed with 44 subtests: 18 existing dashboard tests, 9 new, 13 contract tests.

| Criterion | Result | Evidence |
|---|---|---|
| DX1 export allow-list | supported | `test_dx1_export_is_allow_listed` runs the script's own shaping code, taken from its heredoc up to the database part, on three rounds plus noise. Every planted value is absent from the output: addresses, hashes, intent and quote IDs, model text, a DSN and a URL. Non-codes become `OTHER`, a round ID carrying a hash is dropped, and the output keys are a subset of the allow-list. `test_dx1_export_limit` checks the latest-N cut. `test_dx1_database_part_is_read_only` finds `SET TRANSACTION READ ONLY`, only SET and SELECT statements, and no write keyword anywhere in the script. |
| DX2 merge | supported | `test_dx2_merge_is_idempotent_and_updates_closed_rounds`: 4 noise lines skipped and counted; a re-merge is byte-identical; a later export closes the open round; an older export never reopens it; two merge orders give the same bytes. |
| DX3 numbers | supported | `test_dx3_numbers`: 3 rounds (1 open, 1 complete, 1 rejected), 1 with orders, 1 buy, 0 sells, `NEW_RISK_HALTED` ×2 first of 8 top codes, target weight 19.00%, newest first. `test_dx3_rows_are_capped`: 305 rounds give 300 rows, newest first. |
| DX4 redaction | supported | `test_dx4_redacted_build_has_no_round_ids_or_planted_values` checks the redacted site for round IDs, `0x…` and the planted values; the full build keeps the round IDs. `test_dx4_build_does_not_trust_the_file`: a hand-written hostile `decisions.jsonl` is reduced to `OTHER`/None in both builds. D2, D3 and D5 pass; D5's allowed reads gained only `decisions.jsonl`. |
| DX5 page | supported | Headless Chromium on the fixture site: redacted light and dark at 1100 px, full light and redacted dark at 375 px, and a site without decisions at 900 px. Every page has `scrollWidth` = `clientWidth` and no console messages, and shows 3 decision rows, 11 chips and the "Decision rounds" tile. "Only rounds that placed orders" leaves 1 row. Without decisions there is one "No decisions exported yet" row and no tile. The browser check led to one fix: cells now align to the top. |
| DX6 regression | supported | The existing 18 dashboard tests and 13 contract tests pass unchanged, apart from D5's allowed set. |

- Release bundle unaffected: `tools/`, `tests/` and `docs/build/ops/` are outside `release_files`. No `larp/` file
  changed.
- Not done: the export has not been run on the live primary. Its database part copies `trading-status.sh`'s
  read-only pattern but is untested against a real database, so the first SSM run is its check. No real decisions
  have been seen, and nothing was published (PAGES01).


### PR274-RV01 — decision export output bound (2026-10-24)

The default30 rows did not guarantee SSM's inline output limit:30 copies of the existing synthetic DX fixture give
24336 bytes (regression with distinct round IDs). The exporter now removes oldest complete rows until the entire
output, including its summary and every newline, fits22000 UTF-8 bytes. Small exports keep their existing bytes;
size-limited exports add `omitted_for_size`, retained in the merge report. Even a single over-budget row leaves a
complete summary. The SQL/privacy allow-lists are unchanged. This is source/offline validation only; the first
read-only host export and PAGES01 publishing decision remain open. Full review evidence: IDEA-090 PR274-RV01.

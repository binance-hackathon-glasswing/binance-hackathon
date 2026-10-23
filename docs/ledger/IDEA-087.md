# IDEA-087 — Wallet dashboard published as a static GitHub Pages site

- Date / author: 2026-10-23 / Keith (request), Claude Code (build)
- Status: open (pre-registered below; built on branch `claude/idea087-pages-dashboard-20261023`)
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

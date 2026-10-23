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

# Wallet dashboard on GitHub Pages (IDEA-087)

A static page that shows the agent wallet's equity, return, drawdown, holdings, swaps, gas and monitor alerts. It is
rebuilt from the SJ-08 chain monitor's files and pushed to a GitHub Pages branch every 10 minutes. Record and test
results: [IDEA-087](../ledger/IDEA-087.md). Open decision: `INCOMPLETE_WORK.md` IDEA-087 PAGES01.

```
chain-monitor.py ──► deploy/activation/rehearsal-monitor/*.jsonl ──► tools.dashboard.publish ──► <repo>@gh-pages ──► Pages
   (public chain data +                (git-ignored)                  (build, commit if changed,
    read-only Web3 prices)                                             fast-forward push)
```

## What it is and is not

- **An off-host observer.** It reads only the monitor's three files. It never touches the hosts, the database, the
  signer, credentials or the registered build. `tools/` is outside `release_files` (`larp/runtime/preflight.py`), so
  the release bundle does not change. It is not a version event and not a human action on the agent.
- **Not the official score.** Equity excludes BNB and uses the monitor's Web3 `rwa/price`. The official valuation
  source is not published.
- **Public, if hosted on Pages.** The org is on GitHub Free: Pages work only from a public repository, and the site
  is reachable by anyone with the URL. The main repository must stay private (F-24), and the publisher refuses to
  push into it. Use a separate repository that holds only the built page.
- **Redacted by default.** No wallet address, transaction hash, contract or spender address, block number or nonce
  appears unless you pass `--full`. Holdings, swap sizes and times are still shown. Only use `--full` for a local
  file or a site that is not public.

## Preview locally

From the repository root, with the venv from `requirements.lock` (only the standard library is needed):

```bash
python -m tools.dashboard.build --monitor-dir deploy/activation/rehearsal-monitor --out deploy/activation/dashboard-site
```

Open `deploy/activation/dashboard-site/index.html` in a browser. Add `--full` for BscScan links and alert details.

## Publish (after the team decides, IDEA-087 PAGES01)

1. Create the Pages repository once. It must be a new, empty repository, never the main one:

   ```bash
   gh repo create binance-hackathon-glasswing/larp-dashboard --public --description "LARP wallet dashboard (built page only)"
   ```

2. Run the publisher on the machine that runs the chain monitor, next to it:

   ```bash
   python -m tools.dashboard.publish --monitor-dir deploy/activation/rehearsal-monitor --repo binance-hackathon-glasswing/larp-dashboard --loop 600
   ```

   Each run builds the page into `deploy/activation/dashboard-pages/<owner>__<name>/` (a git-ignored clone). It commits
   only when the data changed and pushes one fast-forward commit to `gh-pages`. It never force-pushes. If the remote
   branch diverged from the clone, it stops without writing anything. Git uses your normal credentials
   (`gh auth setup-git`).

3. After the first push, turn on Pages from the `gh-pages` branch:

   ```bash
   gh api -X POST repos/binance-hackathon-glasswing/larp-dashboard/pages -f "source[branch]=gh-pages" -f "source[path]=/"
   ```

   The site is then at `https://binance-hackathon-glasswing.github.io/larp-dashboard/`. An open page fetches
   `data.json` every 5 minutes, and the status pill turns to Delayed after 10 minutes without a new poll and to Stale
   after an hour.

## Decisions (IDEA-087 DX)

The page also has a **Decisions** section: one row per round, with its time, source (cadence, filing, review,
safety), outcome, the planner's orders, the policy's targets, the planner's rejection and error codes ("Why not") and
the evidence assessment's status. The chain monitor cannot see decisions; they live in the run's database on the
primary. So an SSM operator exports them, read-only, and the export is merged into the monitor folder:

```
primary DB ──► tools/dashboard/decisions-export.sh (SSM, READ ONLY) ──► results/decisions-export-stdout.txt
           ──► tools.dashboard.decisions merge ──► <monitor dir>/decisions.jsonl ──► build / publish (as above)
```

From the copied run folder `deploy/activation/rehearsal-install-rc7-20261024/` (the script stays in `tools/dashboard/`;
`ssm_run.py` sends any script path), then from the repository root:

```bash
python3.12 -I ssm_run.py ../../../tools/dashboard/decisions-export.sh 30     # the latest 30 rounds (about 7.5 h at 15-minute rounds)
python -m tools.dashboard.decisions merge deploy/activation/rehearsal-install-rc7-20261024/results/decisions-export-stdout.txt --monitor-dir deploy/activation/rehearsal-monitor
```

- Run the export at least every 7 hours, or pass a larger N. Each merge adds the rounds it has not seen and updates
  rounds that have since closed. About 30 rounds fit SSM's 24,000-character inline output; if the summary line is
  missing from the stdout, the output was cut, so use a smaller N.
- The next build or publisher loop picks the file up. Without it the section says no decisions have been exported.
- The export prints codes, symbols, amounts and times only: no free-text detail, model text, IDs, hashes, config or
  URLs. The build allow-lists the file again. The redacted page also leaves out round IDs, because a filing round's ID
  names its job.
- **On a public page, the decisions show the strategy**: its targets, sizes and reasons, as well as its trades.
  Decide on that before publishing it for the scored run (PAGES01).

## Limits

- GitHub's soft limit is 10 branch-based Pages builds an hour, so `--loop` must be at least 360 s (600 s is the
  default suggestion). A run with unchanged data makes no commit.
- Org Actions are currently blocked by billing. Whether Pages builds for a public repository still run under that
  block has not been checked.
- Each commit adds about 100 KB before compression, so a 14-day run at 600 s adds at most about 2,000 commits.
- The chain monitor hard-codes the dev rehearsal wallet and its opening balances (`WALLET`, `START`). For the scored
  run, a monitor copy needs the final wallet's address and opening balances. The dashboard takes the opening equity
  from the monitor's own `pnl_vs_start` and has no wallet setting.

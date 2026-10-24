# IDEA-091 — Automated private dashboard on AWS (proposal)

- Date / author: 2026-10-24 / requested in the Claude Code session that runs the hourly dashboard refresh ("draft
  option A"); drafted by Claude Code. Owners for review and apply: Isaac and Keegan (AWS, Terraform), Keith (PAGES01).
- Status: **open, proposal.** Drafted and tested offline only; nothing is applied in AWS.
- Related: IDEA-087 (dashboard, DX decisions, DR hourly refresh), PAGES01, F-24, F-114, F-117.

## Why

The private dashboard is a claude.ai page refreshed by an hourly Claude session (IDEA-087 DR). That needs a live
Claude session and this environment's credentials every hour. GitHub Pages is public on our plan and org Actions are
blocked by billing. For the 14-day final the dashboard should update on its own, privately, with no laptop and no
Claude session.

## Design

All files under `tools/dashboard/aws/`: outside `release_files` (`larp/runtime/preflight.py`) and in their own
Terraform state, so the agent's release, manifest and `deploy/aws` stack do not change. It never touches the agent's
hosts except the two read-only SSM documents below.

- **Lambda** (`handler.py`, Python 3.12), run hourly by EventBridge Scheduler, reserved concurrency 1. Each run: load
  the chain monitor's state from a private S3 bucket, one monitor poll (seeded from the primary on the first run),
  the decisions export, the redacted build, then upload the page and the new monitor state. A failed run uploads
  nothing, so the last good page stays.
- **Least-privilege SSM.** Two SSM Command documents hold the fixed read-only scripts (`decisions-export.sh`,
  `tx-export.sh`). The Lambda may run only those two documents, only on the configured primary; it has no
  `AWS-RunShellScript` permission and cannot send arbitrary commands.
- **Private viewing.** The bucket blocks all public access. CloudFront reads it through Origin Access Control, and a
  CloudFront Function asks for a login (HTTP basic auth) checked against a hash held in a CloudFront KeyValueStore.
  The hash is set by an operator outside Terraform, so no password or hash is in the repo or the Terraform state.
- **Prices** (optional): the read-only Web3 key from a Secrets Manager secret, so equity and drawdown charts work.
- **Wallet**: the monitor's wallet and opening balances come from configuration, so the same stack serves the final
  wallet (the RC7 monitor hard-codes the dev wallet).

## Pass criteria (written before any test is run)

| # | Pass when | How |
|---|---|---|
| A1 | One handler run uploads `index.html` and `data.json` (redacted: no `0x` with 8 or more hex digits) and the monitor state; a second run continues from that state; a run whose poll fails uploads nothing and raises | handler test with fake S3, SSM and monitor |
| A2 | The handler sends only the two named SSM documents to the configured instance, never `AWS-RunShellScript`; the IAM policy allows `ssm:SendCommand` only on those two documents and that instance | handler test; `terraform test` with a mock provider |
| A3 | The bucket blocks all public access and allows only the CloudFront distribution; CloudFront runs the login function on every viewer request | `terraform test` |
| A4 | Hourly schedule, reserved concurrency 1, timeout at most 300 s | `terraform test` |
| A5 | The package is deterministic and holds only the listed files (no `.env`, keys or tests); the handler imports from it | package test |
| A6 | The login function refuses a request without, or with a wrong, `Authorization` header and passes the right one | Node test of the function with a fake KeyValueStore |
| A7 | `terraform fmt -check` and `terraform validate` pass | Terraform 1.13.5, AWS provider 6.61.0 |

Not claimed: an apply in AWS or a real invocation (owners' step), whether SSM read access stays open during the scored
run (PAGES01), or the final wallet's opening balances.

## Results (2026-10-24, offline; nothing applied)

Files: `tools/dashboard/aws/` (`handler.py`, `package.py`, `viewer-auth.js`, `versions.tf`, `variables.tf`,
`main.tf`, `outputs.tf`, `dashboard.example.tfvars`, `tests/dashboard.tftest.hcl`), `tools/dashboard/refresh.py`
(pluggable SSM runner, configurable wallet and opening values, best-effort export), `tests/test_dashboard_aws.py`,
`docs/build/DASHBOARD.md` "Automated private hosting on AWS". The tests were written with the code (new module), and
two mutations were run to check they bite: a runner sending `AWS-RunShellScript` fails A2; a partial upload before a
failing poll fails A1.

| # | Result | Evidence |
|---|---|---|
| A1 | **pass** | `test_a1_runs_upload_the_page_and_state_and_continue`: page and state uploaded, redacted, `no-cache`; the configured wallet and start nonce reach the monitor and PnL is restated against `START_USDT`; a second run continues (one transaction, two polls). `test_a1_a_failed_run_uploads_nothing`. Added while writing the guide: `test_a1_without_the_decisions_export_the_trades_still_refresh` (SSM refused: trades refresh, the last decisions stay, `export_error` reported). |
| A2 | **pass** | Handler: only the two document names, only the primary, never `AWS-RunShellScript`, the tx document once (seeding); an unknown script is refused. Terraform: `ssm:SendCommand` resources are exactly the two documents and the instance; no secret read without `web3_secret_arn`, only that ARN with it. |
| A3 | **pass** | Terraform test: all four public-access blocks on; the bucket policy's only statement is CloudFront reading `site/*` for this distribution; the login function is on `viewer-request`; HTTPS redirect. |
| A4 | **pass** | `rate(1 hour)`, reserved concurrency 1, timeout 300 s. |
| A5 | **pass** | Two builds are byte-identical (43,823 bytes); exactly the listed files plus the `.git` marker; the unmodified RC7 monitor finds its root inside the extracted package and the handler imports (`python -I`). |
| A6 | **pass** | Node: the right credential passes; missing header, wrong credential, a non-Basic scheme, a missing key and an empty stored hash each get 401. |
| A7 | **pass** | Terraform 1.13.5 (checksum-verified download), AWS provider 6.61.0: `fmt -check`, `validate`, `terraform test` 4 passed (mock provider, plan only). |

Also fixed while testing: loading the RC7 monitor wrote `__pycache__` into its pinned run-sheet folder, which failed
`tests/runtime/test_run4_sheet.py`; `refresh.chain_monitor` now loads it without writing bytecode.

Open for the owners: review and apply (Isaac, Keegan); the backend state key; the Web3 read-only secret; setting the
login hash; then stopping the Claude session's hourly task. PAGES01: SSM read access in the scored run, and the final
wallet's start nonce and opening USDT.

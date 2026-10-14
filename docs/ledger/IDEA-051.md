### IDEA-051 — Deployment pre-setup for the first hosted shadow run (Gate A)
- Date / author: 2026-10-15 SGT (2026-10-14 UTC) / Yao Zhu with Claude Code
- Status: open
- What: prepare everything for the first hosted run that doesn't need spending, a secret in chat, or an unmade team decision. That means a checked state of the AWS stack, a hidden-prompt script the team runs to fill the two service secrets, a tool that fills each host config's infrastructure values from `terraform output`, and one checklist for deployment day ([DEPLOYMENT_DAY.md](../build/DEPLOYMENT_DAY.md)).
- Why it might help: the Oct 14 Gate A milestone (DEPLOYMENT_BUILD.md) slipped. Once the reviews and final tests pass, the remaining host steps should be mechanical, with every blocker named in advance.
- Cost / risk: no AWS spend in this entry. Starting hosts (≈ $23/month more) and applying the new credit budget need Yao Zhu's OK. Secret values never pass through chat, Git, argv or logs. **This entry gives no signing permission:** the Executor capability gate and the swap decoder (Isaac, GAP-29) still refuse every swap, so a hosted run can only be a shadow run (`execution: "shadow"`).
- Links: AWS_RUNBOOK.md; runbook.md; IDEA-046, IDEA-047, IDEA-049-D (D-DN-05, R-01, R-07), IDEA-050; GAP-04, GAP-29; #25, #32, #33, #62.

## State checked 2026-10-14 16:50 UTC (read-only)
- `aws sts get-caller-identity --profile larp`: signed in to the credit account.
- `terraform plan` (`deploy/aws`, `development.tfvars`, `-lock=false`) against `0820b0d`: **1 to add, 1 to change, 0 to destroy**. The add is `aws_budgets_budget.credit[0]` (IDEA-049-D D-FND-016); the change is an in-place update of `aws_budgets_budget.monthly[0]`. Nothing else has drifted. Not applied.
- `terraform output`: `host_ids = {}` (no hosts), `signing_enabled = false`. Secrets `larp-dev/runtime`, `larp-dev/uploader` and `larp-dev/evidence` exist with **0 versions** (no values stored yet).

## Pass criteria (written before the tools run)
1. **`tools/deploy/put_service_secrets.sh`**
   - Never echoes or saves a value, and never passes one on a command line (values reach `aws secretsmanager put-secret-value` on stdin).
   - Writes only `larp-dev/runtime` = {`AI_SEEDS_ADDRESS`, `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`} and `larp-dev/uploader` = {`AI_SEEDS_ADDRESS`, `AI_SEEDS_SECRET`}, matching `RUNTIME_SECRETS` (`larp/runtime/live.py`) and `ALLOWED_SECRETS` (`larp/audit/service.py`).
   - Refuses an address that isn't `0x` + 40 hex characters, or an `AI_SEEDS_SECRET` that isn't 64 hex characters.
   - Checked by a test that runs it against a fake `aws` on the PATH.
2. **`tools/deploy/render_host_configs.py`**
   - From a `terraform output -json` file, a wallet address and an optional RDS CA SHA-256, writes `runtime.json`, `execution.json`, `signer.json`, `uploader.json` and `operations.json` into a git-ignored directory.
   - Each file is the matching example with only infrastructure values filled. The secret IDs come from the secret ARNs (`<name>/runtime`, `<name>/uploader`).
   - Every value it leaves unset is listed by file. It reads no secret, refuses a directory Git would track, and doesn't overwrite without `--force`.
   - Checked by unit tests on a synthetic Terraform output.
3. **The full suite stays green**, with both new tests included.

## Results
- 2026-10-14 UTC: criteria committed at `3c156f7`, before the tools existed. Tools and tests committed at `426a7a5`, before any run.
- **Criterion 1: PASS (synthetic).** `PutServiceSecrets` uses a fake `aws` on the PATH. It checks that exactly the runtime and uploader names are written, that values arrive on stdin only (never in argv, stdout or stderr), that declining writes nothing, and that a bad address, bad audit secret, bad name or empty key are refused. A real AWS CLI call with a dummy `{}` against a non-existent secret ID reached the API (`ResourceNotFoundException`), so `file:///dev/stdin` is accepted. **No real secret value was written.**
- **Criterion 2: PASS (synthetic).** `RenderHostConfigs`: only infrastructure keys are filled; secret IDs come from the ARNs; the wallet is lowercased; a filled uploader config passes `larp.audit.service.validate_config`; there are refusals for wallet, ARN, account mix and missing output; files are `0600`; it refuses a non-ignored directory; there is no overwrite without `--force`. A parse-only run against the real `terraform output -json` resolved name `larp-dev`, region `ap-southeast-2` and secret IDs `larp-dev/{runtime,uploader,evidence}`, and listed every unset value. **No config was written** (no wallet address yet).
- **Criterion 3: PASS locally, CI pending.** Full suite on macOS, Python 3.12.15, without PostgreSQL: 1007 passed, 262 skipped (database and Linux-only cases), 1460 subtests. Linux CI with PostgreSQL runs on the PR.
- **Findings for deployment day:**
  - The SNS alarm subscription is `PendingConfirmation`.
  - The Session Manager plugin is not installed on the Mac.
  - The latest AL2023 x86_64 AMI is `ami-0c82c1a90be4dccc1` (2026-10-14).
  - A `dev` run needs a LIVE profile (`larp/runtime/service.py:191`), which needs a measured `QuoteCostSummary.v1` that no tool produces yet. This blocks Gate A until Isaac/Keith supply it.
- **2026-10-14 ~17:10 UTC: applied (Yao Zhu's OK in chat, after reviewing the saved plan).** The saved plan from `deploy/aws` (code identical to `0820b0d`) ran with `terraform apply <saved plan>`: **1 added, 1 changed, 0 destroyed.**
  - Added `larp-dev-credit`: $100, 2026-10-01 → 2027-04-12, with alerts at actual 50/75/90% and forecast 100%.
  - Changed `larp-dev-monthly`: `include_credit` went from true to false, so spend is counted before credits and the alerts can fire.
  - A fresh plan shows **No changes**. `describe-budgets` confirms both budgets with `IncludeCredit = False`.
  - No hosts and no cost: budgets are free.
  - `CalculatedSpend` still read 0.0 right after the change; AWS recalculates budgets periodically, so check it again within a day.

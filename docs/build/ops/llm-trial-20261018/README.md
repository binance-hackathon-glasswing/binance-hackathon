# LLM-trial deployment scripts (templates, 2026-10-18)

These are the exact scripts used for IDEA-066 PC-DEPLOY02 (redeploying a new build into a fresh trial database
while keeping the shared model-budget ledger). They hold no secrets, private RPC URLs or database hosts: those are read
at run time from git-ignored files on the operator's Mac (`deploy/activation/tf-output.json`, `.env`,
`deploy/activation/balance-rpc/selected-providers.json`, `deploy/activation/gate-a-prepared-20261017/`).

**Before using them:** copy this folder into the git-ignored `deploy/activation/<new name>/`. The SSM helpers write
their results next to themselves, and some host output names the database endpoint, which must never be committed.
Update the hard-coded values (build ID, bundle name/hash, run ID, database name, checkout path, review reference) for
the new build. Paths assume the original operator's Mac (`/Users/songyaozhu/...`); change them for yours.

| Step | Runs on | Script | What it does |
|---|---|---|---|
| R1 | host | `host/r1-pause-runtime.sh` | stop `larp-runtime` only (no new rounds); evidence/uploader/archive keep running |
| R2 | Mac | `db/run-db-setup.sh <db> <checkout> <commit>` | SSM port-forward, admin secret in memory only, create the new `larp_trialN`, migrations, `roles.sql` with only the DB name changed. Needs `LARP_PG_PYTHON` (venv with psycopg 3.3.6) |
| R3 | host | `host/r3-preserve-stop-all.sh <old run> <old build>` | after the next hourly anchor ACK: stop the rest, move configs to `/etc/larp-history/`, SQLite-backup the evidence store and the ledger (ledger stays in place) |
| R4 | Mac | `mac/r4-upload-bundle.sh` | upload the bundle, its `.sha256` and `.release.json` to the artifact bucket `releases/` |
| R5 | host | `host/r5-provision.sh @artifact_bucket` | download, hash-check, run the bundle's own `provision.sh`; re-disable `larp-execution` |
| R6 | Mac | `mac/r6-prepare.py` | fresh wallet capture + `prepare` from the exact clean checkout via `prepare_trial_db.py` (only `database_name` overridden), package check, upload; prints the R7 command |
| R7 | host | `host/r7-install-keep-ledger.sh @artifact_bucket <prefix> name=sha...` | install configs with the right owners/modes, registration evidence; read-only check that the existing ledger's policies match the routing (no init/migration) |
| R8 | host | `host/r8-bind-activate-start.sh` | bind, preflight, `service check`, route check (to a file), time sync, `service init`, `activate`, start unsigned services |
| R9 | Mac | `mac/r9-cleanup-s3-package.sh <prefix>` | delete the S3 transfer copies (runtime.json carries private RPC URLs) |

Host steps are sent with `python3.12 -I ssm_run.py host/<script> [args]`; `@artifact_bucket` is resolved locally from
`tf-output.json` and never printed. Read-only checks (`checks/*.sh`) are sent with
`python3.12 -I checks/ssm_read.py checks/<script> <name>`.

Gotchas learned on 2026-10-18 (IDEA-066 PC-DEPLOY01/02):
- `runs` is UNIQUE(wallet_id, chain_id) and `activate` refuses another build: a new build or profile on the same
  wallet needs a NEW trial database until reviewed version-switch support exists.
- `render_host_configs.py` refuses a database name other than the example's `larp`; use `prepare_trial_db.py`.
- `service activate --review-ref` accepts at most 200 characters.
- `larp.runtime.routes` prints every destination host, including the database endpoint; keep its output in a file.
- `session-manager-plugin` outlives the `aws ssm start-session` parent; the DB script now kills it on exit.
- Never run `model_budget init` on an existing ledger; `status`/`export` advance its clock watermark (owner actions).

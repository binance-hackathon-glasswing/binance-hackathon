# IDEA-045 — AWS hosting step 1: hosted database authentication and local tooling

- Date / owner: 2026-10-12 / Yao Zhu with Claude. Hosting owners remain Keegan + Isaac (`docs/build/architecture-deployment.md`).
- Status: **complete for step 1 (offline engineering scope)**. H01–H06 pass on pushed head `63082a3`; nothing was provisioned and no AWS credentials were used. Real hosted verification (token login, TLS, grants on RDS) waits for step 2+.
- Branch: `codex/hosting-step1-20261012`, cut from `codex/system-testing-review-20261012` at `393c2d8` (PR #18, not merged). Main is not touched.
- What: close IDEA-044 V10/V11 so that the existing Terraform/SQL design can authenticate every hosted database identity, and install pinned local tooling to validate the deployment definitions. **No cloud resources, AWS credentials, plans against an account, or paid actions** are part of this step; those wait for the user's region, environment, budget and retention decisions and an explicit approval.
- Links: IDEA-044 V10/V11; IDEA-042 X2 (role grants); IDEA-028 RT10–13; `docs/build/architecture-deployment.md` steps 3–6; G-17 (jurisdiction), G-47 (retention).

## Design choice (recorded before implementation)

The six-host template has no dedicated execution host, and the coordinator drives the execution service. The execution service (`larp_execution`) is therefore placed on the **primary and standby** hosts beside the runtime coordinator (`larp_runtime`). Each host's IAM role may request `rds-db:connect` tokens for exactly the SQL roles mapped to it. Process separation inside a host is enforced by the SQL grants (IDEA-042 X2), not by IAM; a dedicated execution host remains an option for Keegan + Isaac (extra cost). The standby is still never promoted automatically.

## Prospective acceptance (before implementation/testing)

| ID | Expected outcome |
|---|---|
| H01 | Terraform maps each database host to an explicit set of SQL roles: primary/standby → `larp_runtime` and `larp_execution`; archive → `larp_archive`; uploader → `larp_uploader`; signer → `larp_signer`; evidence → none. The host policy grants `rds-db:connect` for exactly those users, and every role in `deploy/postgres/roles.sql` that has `rds_iam` is reachable by at least one host. A `terraform test` asserts the mapping and that the evidence host gets no database access. |
| H02 | The runtime service accepts exactly one database connection setting: `database_dsn_file` (local/offline) **or** RDS IAM settings (`database_host`, `database_user` = `larp_runtime`, `database_name`, `database_ca_file`, `database_ca_sha256`, `region`). Both, neither, a partial IAM set, another user, a missing CA bundle or a CA hash mismatch refuse before secrets, database sessions or driver construction. |
| H03 | With IAM settings the service generates a fresh RDS token for **every** connection, over `sslmode=verify-full` with the pinned CA, using the same store as operations (shared module; operations behaviour unchanged). A mocked RDS client sees one token request per transaction, and the token never appears in errors or reprs. |
| H04 | Existing behaviour is unchanged: DSN-file configs, manifest/config binding (R19/R25), `NOT_INTEGRATED` refusal, operations maintenance tests and the role-grant PostgreSQL tests pass; no adopted policy value or live gate changes. |
| H05 | Pinned local tooling: Terraform 1.13.5 installed from the official HashiCorp zip with the same SHA-256 that CI checks, outside the repository; AWS CLI v2 installed outside the repository. `terraform fmt -check`, `init -backend=false -lockfile=readonly`, `validate` and `test` pass locally for `deploy/aws` and `deploy/bootstrap`, using no AWS credentials. |
| H06 | Full local suite against disposable PostgreSQL and Linux CI (pytest, isolated demo, Docker smoke, both Terraform directories) pass at the published head. Any skip is reported with its reason. |

Validation results: see below. Criteria were committed at `34d820b` before any implementation or execution.

## Results (2026-10-12)

Commits (each pushed before it ran): `6132ec5` implementation and tests; `26adee1` darwin_arm64 provider checksum; `63082a3` test fix. Environment: fresh clones of the pushed branch, Python 3.12.14 venv from `deploy/requirements-test.lock`, disposable PostgreSQL (`larp-hosting-20261012`, loopback 55432), `env -i` with no AWS or other credentials and `AWS_EC2_METADATA_DISABLED=true`.

| ID | Result | Evidence |
|---|---|---|
| H01 | PASS | `deploy/aws` `terraform test`: 6/6 runs pass, including `host_database_users_match_sql_roles` with the new role-list mapping, the evidence-host exclusion and the every-`rds_iam`-role-reachable assertions. |
| H02 | PASS | `test_database_connection_is_exactly_one_pinned_choice`: DSN only, IAM only and DSN plus `region` accepted; neither, both, partial IAM, `larp_archive`, CA hash mismatch, missing CA and empty region refused. |
| H03 | PASS | `test_runtime_service_iam_store_uses_fresh_verified_tls_token_per_connection` on real PostgreSQL: one distinct token per connection, `sslmode=verify-full` with the pinned CA, user `larp_runtime`, token absent from the repr. Operations' existing IAM test still passes against the moved class. |
| H04 | PASS | Full local suite at `63082a3`: 1060 passed, 4 skipped (1 opt-in external artifacts, 3 Linux bubblewrap), 1337 subtests. Red/green: both new runtime tests fail against code at `393c2d8` and pass here. |
| H05 | PASS | Terraform 1.13.5 darwin_arm64 from releases.hashicorp.com, installed at `~/.local/opt/terraform-1.13.5/`: the SHA256SUMS file's linux_amd64 line equals the CI pin, and the zip matches SUMS. AWS CLI 2.37.12 via Homebrew. `fmt -check`, `init -backend=false -lockfile=readonly`, `validate`, `test` pass locally for `deploy/aws` (6/6) and `deploy/bootstrap` (1/1), with no credentials. Readonly init first failed because the locks held only the linux_amd64 `h1:` hash; `26adee1` adds the HashiCorp-signed darwin_arm64 `h1:` line, one line per lock, with Linux checksums unchanged. |
| H06 | PASS | Linux CI by workflow_dispatch (this branch has no PR): runs [38254601060](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38254601060) and [38254590162](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38254590162) on `63082a3`, all jobs PASS; pytest 1063 passed, 1 skipped (opt-in external artifacts); isolated demo, Docker smoke, Terraform for both directories. The duplicate run came from a dispatch that returned HTTP 500 but was still created. |

Incidents during validation (no effect on results): the first full-suite attempt failed every database test because Docker Desktop had stopped (socket missing); Docker and the disposable database were restarted, then everything was rerun. The first version of the H03 test counted the comparison store's own connection (3 tokens vs 4 connections); fixed in `63082a3` before the recorded run.

Remaining for later hosting steps: real RDS token login, TLS and grants for each role on the provisioned instance (architecture-deployment steps 3–6, after the user decides region, environment, budget and retention and approves a reviewed plan).

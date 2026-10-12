# IDEA-045 — AWS hosting step 1: hosted database authentication and local tooling

- Date / owner: 2026-10-12 / Yao Zhu with Claude. Hosting owners remain Keegan + Isaac (`docs/build/architecture-deployment.md`).
- Status: open (prospective criteria recorded before implementation or execution).
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

Validation results: pending publication and execution.

# IDEA-046 — Lean two-host AWS deployment (Option B) within a $100 credit cap

- Date / owner: 2026-10-12 / Yao Zhu (decision) with Claude. Hosting owners remain Keegan + Isaac.
- Status: **implemented and validated offline** (L01–L08 PASS, 2026-10-12). Not applied to AWS; the first plan/apply waits for the user's explicit approval of a reviewed saved plan.
- Branch: `codex/hosting-option-b-20261012`, stacked on PR #19 (`codex/hosting-step1-20261012`). Nothing is applied to AWS by this entry.
- Links: IDEA-028 (six-host design this replaces for deployment), IDEA-045 (IAM database login), G-17 / Q-12 (jurisdiction), G-47 (archive retention), F-15/F-17 (scored run Oct 29 – Nov 12, winner audit Nov 16–20), F-62 (write-once trace uploads).

## Decisions (Yao Zhu, 2026-10-12)

| ID | Decision | Reason / risk |
|---|---|---|
| B1 | Replace the six-host template with **two hosts**: `primary` (coordinator, execution, evidence worker, uploader, archive maintenance) and `signer` (wallet key only). Single-AZ RDS PostgreSQL `db.t4g.micro`. No NAT gateways, no interface endpoints. | Six hosts plus endpoints and NAT cost ≈ $355–380/month against a $100 credit budget. Two hosts keep the most important boundary: the wallet key never sits on an internet-facing host. Lost: per-service IAM separation on `primary`, standby host, Multi-AZ database. |
| B2 | The signer's wallet key is a **root-only file** on the signer's encrypted disk, not a Secrets Manager entry. The signer has **no internet route**: only the database and the free S3 gateway endpoint (release artifacts). | Saves the ≈ $9.50/month Secrets Manager interface endpoint. Weaker than a managed secret: the key's protection is disk encryption, file mode and host isolation. The signer service that reads it is not built yet (`NOT_INTEGRATED`); its loader must refuse a file readable by group/other. |
| B3 | **Region: Sydney (`ap-southeast-2`) for now.** The account is a new-AWS-experience project (Free plan, $100 credits, expiry 2027-04-12). An AWS-managed service control policy denies `ap-southeast-1`, and new projects get Sydney automatically. | **Risk:** the agent would trade from an Australian address while the team is in Singapore (G-17; Q-12 open). Sydney prices for every Option B item equal Singapore's (official price list, 2026-10-12). **Revisit before final activation (Oct 27):** move to a Singapore account, or keep Sydney with a written jurisdiction check. **Closed 2026-10-14:** organiser answer F-118 (relayed by Yao Zhu): Sydney is fine. |
| B4 | Cost controls: burstable instances use **`standard` CPU credits** (no surplus charge); AWS Budgets alerts; short CloudWatch retention and no database log export by default; teardown after the winner audit. | The Free plan caps charges at the credits but closes the account when they are used up, which would stop the agent mid-run. The budget must leave margin. |

Estimated cost at official Sydney prices (730 h): `t3.small` $19.27, `t3.micro` $9.64, `db.t4g.micro` single-AZ $18.25, 20 GB RDS gp3 $2.76, 2 × 20 GB EBS gp3 $3.84, one public IPv4 $3.65, KMS $1, ≈ 4 secrets incl. RDS-managed $1.60, alarms/metrics ≈ $1, logs/S3 < $1.50 → **≈ $62/month**, ≈ $66 from now to Nov 12. Model API, gas and trading funds are separate and not AWS costs.

## Prospective acceptance (before implementation/testing)

| ID | Expected outcome |
|---|---|
| L01 | Terraform declares exactly two hosts, `primary` and `signer`. `primary` may obtain RDS tokens for `larp_runtime`, `larp_execution`, `larp_archive` and `larp_uploader`; `signer` only for `larp_signer`. Every `rds_iam` role in `roles.sql` is reachable. |
| L02 | No NAT gateway, Elastic IP or interface VPC endpoint exists in any configuration; the only VPC endpoint is the S3 gateway endpoint. |
| L03 | With `enable_external_https = false` (default) nothing can reach the internet: no internet gateway route, no public IP, no 0.0.0.0/0 egress. With it enabled, only `primary` gets a public IP and HTTPS egress; `signer` never has an internet route, public IP or Secrets Manager read permission. |
| L04 | Both instances use `cpu_credits = "standard"`, IMDSv2, encrypted disks, and per-host instance types (defaults `t3.small` / `t3.micro`). An EC2 system-status alarm per host triggers automatic recovery. |
| L05 | The database is private, encrypted, IAM-authenticated, single-AZ by default, with no log export by default. Deletion protection and instance termination protection stay on unless `allow_teardown = true`. The archive bucket (Object Lock COMPLIANCE, ≥ 82 days) and KMS key keep `prevent_destroy`. |
| L06 | A monthly AWS cost budget with ACTUAL-spend notifications at 50/75/90 % is created when notification emails are supplied; no email or account identifier is committed. |
| L07 | `terraform fmt/init/validate/test` pass for `deploy/aws` and `deploy/bootstrap` with mock providers and no credentials; Linux CI green; the Python suite is unaffected. No `terraform plan` against the real account in this step. |
| L08 | Documentation states the two-host layout, the signer key-file requirement, the cost table, the Sydney risk and revisit date, and a teardown checklist that keeps the archive and audit material through Nov 20. |

Validation results (2026-10-12). Criteria committed at `62f53e0` before implementation. Code `721d865`, docs `02453f7`; PR #20 (stacked on #19).

| ID | Result | Evidence |
|---|---|---|
| L01 | PASS | `host_database_users_match_sql_roles`: two hosts, the role map as specified, every `rds_iam` role reachable. `safe_defaults`: 2 IAM roles. |
| L02 | PASS | NAT, Elastic IP and interface-endpoint resources removed from the configuration; `safe_defaults` asserts the only VPC endpoint is the S3 gateway. |
| L03 | PASS | `safe_defaults`: no internet gateway or route by default. `host_isolation`: no public IP and no external egress by default. `internet_reaches_primary_only`: with egress enabled, only `primary` gets a public IP, HTTPS egress and the internet route, and the signer reads no managed secret. |
| L04 | PASS | `host_isolation`: standard CPU credits, IMDSv2, encrypted disks, termination protection, default `t3.small`/`t3.micro`, one recovery alarm per host. `non_burstable_types_are_refused`. |
| L05 | PASS | `safe_defaults`: private, encrypted, IAM-authenticated, single-AZ, no log export, deletion-protected. `teardown_lifts_only_operational_protection`: `allow_teardown` lifts database, instance and artifact protection, while the archive keeps COMPLIANCE and is never force-destroyed. Archive bucket and KMS key keep `prevent_destroy` (configuration). |
| L06 | PASS | `budget_alerts_with_recipient`: one budget, `90.00` USD, 3 actual-spend notifications. `safe_defaults`: no budget without a recipient. Recipients are a sensitive variable; the example file has placeholders only. |
| L07 | PASS | Local Terraform 1.13.5 with mock providers and no credentials: `deploy/aws` 10/10, `deploy/bootstrap` 1/1, fmt/validate clean. Linux CI run [38261464804](https://github.com/binance-hackathon-glasswing/binance-hackathon/actions/runs/38261464804): all jobs PASS (Terraform 10/10 and 1/1; pytest 1063 passed, 1 opt-in skip; demo; Docker smoke). No plan against the real account. |
| L08 | PASS | `docs/build/architecture-deployment.md`: lean target, cost, signer key-file and offline-image requirements, Sydney risk with the Oct 27 revisit, teardown checklist. Open items in `docs/INCOMPLETE_WORK.md`. |

Read-only account checks used for B3 (2026-10-12, profile `larp`, role `AccountFullAccessRole`): Free plan ACTIVE, $100.00 credits, expiry 2027-04-12. Singapore EC2/RDS calls are denied by an AWS-managed SCP. In Sydney: no instances, databases, addresses, endpoints, NAT gateways, buckets or budgets, and the needed services are readable. PostgreSQL 14.24 is orderable on `db.t4g.micro`. Readable is not proof that creating is allowed; check creation permissions before the first apply.

## AWS setup, free steps (2026-10-14, Claude for Yao Zhu)

Yao Zhu approved the free steps only, stopping at a saved plan (2026-10-14). The account IDs are not recorded here (L06).

- **Account:** Yao Zhu signed in to a **different AWS account** from the one checked on 2026-10-12, and confirmed it is the team's credit project.
  - Read-only checks: Free plan `ACTIVE`, $100.00 credits, expiry 2027-04-12.
  - Singapore EC2 calls are denied by the same AWS-managed service control policy, so Sydney remains (B3).
  - Sydney held no instances, databases, buckets or budgets beforehand. PostgreSQL 14.24 is orderable on `db.t4g.micro`.
  - Creation permissions: dry runs of `t3.small`/`t3.micro` launches (standard credits, IMDSv2), a VPC and an S3 gateway endpoint all return `DryRunOperation`. RDS has no dry run; creating the database is first tried at apply.
- **Applied:**
  1. `deploy/bootstrap`: the state bucket (versioned, AES256, public access blocked, TLS-only). Its local state stays in the ignored `deploy/bootstrap/terraform.tfstate`.
  2. The budget only: `terraform apply` of a saved plan targeting `aws_budgets_budget.monthly` ($90/month, alerts at 50/75/90 % of actual spend to the account owner's email).
- **Saved, not applied:** `deploy/aws/development.tfplan` (git-ignored), 51 resources.
  - Included: VPC, private subnets, S3 gateway endpoint, security groups, KMS key, archive bucket (COMPLIANCE, 82 days) and artifact bucket, 3 service secrets, host IAM roles, the RDS instance and its groups, log groups, alarms, and the alarm SNS topic with one email subscription.
  - Not included: instances, an internet gateway, NAT or public IPs (`enable_hosts`/`enable_external_https` off).
  - Database: `db.t4g.micro`, 14.24, single-AZ, 20 GiB gp3 (autoscaling to 30), private, IAM auth, deletion protection, 7-day backups.
  - Estimated cost with hosts off: about $24/month (database $21, KMS $1, secrets ≈ $1.60, alarms and logs cents). The KMS key and the locked archive outlive teardown (L05).
- **Tooling note:** Terraform 1.13.5's S3 backend cannot read the CLI's new `aws login` session (`login_session` profiles); the AWS provider can. Run Terraform with `eval "$(aws configure export-credentials --profile larp --format env)"` and `AWS_PROFILE` unset. The credentials are short-lived and never written to a file.
- **Next (needs Yao Zhu's OK, real spend):** review and apply `development.tfplan`. Then run the migrations and `roles.sql`, and verify IAM token login, TLS and grants for each role against the two-host map (IDEA-045's remaining check).

## Core stack applied (2026-10-14, Claude; Yao Zhu said "apply")

- **Applied** the saved plan with hosts and egress off. 51 resources now match the configuration (`terraform plan`: no changes). The database `larp-dev` is `available`: PostgreSQL 14.24, `db.t4g.micro`, single-AZ, private, encrypted, IAM authentication.
- **Free plan limit:** the first apply created 47 resources, then RDS refused 7-day automated backups (`FreeTierRestrictionError`: backup retention above the Free plan maximum).
  - The ignored `development.tfvars` now sets `backup_retention_days = 1`, and the database was created with 1 day.
  - This only shortens RDS's own point-in-time window. The daily logical backup to the COMPLIANCE archive (`larp-archive`, G-47) is unchanged.
  - The example settings now say 1, and the deployment guide's "7-day backups" is corrected.
- **Credentials:** `aws configure export-credentials` tokens last about 15 minutes. One expired during the database wait, so Terraform could not save state (`errored.tfstate`) and marked the database tainted although AWS created it correctly.
  - Recovery: release my own stale lock, `terraform state push errored.tfstate`, `terraform untaint aws_db_instance.larp`, then re-plan (3 small resources left) and apply.
  - Run Terraform through a scratch AWS config whose `credential_process` re-exports the `larp` login, so tokens refresh (`docs/build/architecture-deployment.md`).
- **Cost now:** ≈ $24/month (database ≈ $21, KMS $1, secrets, alarms).
- **Next (needs hosts):** migrations, `roles.sql` and the per-role IAM/TLS checks. The database is private with no public route, and there is no host yet, so this needs `primary` (`enable_hosts`, plus egress and development SSM to reach it): ≈ $19/month for `t3.small` plus $3.65 for its public IPv4. Waiting for Yao Zhu's OK.

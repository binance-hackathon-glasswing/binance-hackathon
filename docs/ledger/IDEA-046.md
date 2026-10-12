# IDEA-046 — Lean two-host AWS deployment (Option B) within a $100 credit cap

- Date / owner: 2026-10-12 / Yao Zhu (decision) with Claude. Hosting owners remain Keegan + Isaac.
- Status: open (decisions and prospective criteria recorded before implementation or execution).
- Branch: `codex/hosting-option-b-20261012`, stacked on PR #19 (`codex/hosting-step1-20261012`). Nothing is applied to AWS by this entry.
- Links: IDEA-028 (six-host design this replaces for deployment), IDEA-045 (IAM database login), G-17 / Q-12 (jurisdiction), G-47 (archive retention), F-15/F-17 (scored run Oct 29 – Nov 12, winner audit Nov 16–20), F-62 (write-once trace uploads).

## Decisions (Yao Zhu, 2026-10-12)

| ID | Decision | Reason / risk |
|---|---|---|
| B1 | Replace the six-host template with **two hosts**: `primary` (coordinator, execution, evidence worker, uploader, archive maintenance) and `signer` (wallet key only). Single-AZ RDS PostgreSQL `db.t4g.micro`. No NAT gateways, no interface endpoints. | Six hosts plus endpoints and NAT cost ≈ $355–380/month against a $100 credit budget. Two hosts keep the most important boundary: the wallet key never sits on an internet-facing host. Lost: per-service IAM separation on `primary`, standby host, Multi-AZ database. |
| B2 | The signer's wallet key is a **root-only file** on the signer's encrypted disk, not a Secrets Manager entry. The signer has **no internet route**: only the database and the free S3 gateway endpoint (release artifacts). | Saves the ≈ $9.50/month Secrets Manager interface endpoint. Weaker than a managed secret: the key's protection is disk encryption, file mode and host isolation. The signer service that reads it is not built yet (`NOT_INTEGRATED`); its loader must refuse a file readable by group/other. |
| B3 | **Region: Sydney (`ap-southeast-2`) for now.** The account is a new-AWS-experience project (Free plan, $100 credits, expiry 2027-04-12). An AWS-managed service control policy denies `ap-southeast-1`, and new projects get Sydney automatically. | **Risk:** the agent would trade from an Australian address while the team is in Singapore (G-17; Q-12 open). Sydney prices for every Option B item equal Singapore's (official price list, 2026-10-12). **Revisit before final activation (Oct 27):** move to a Singapore account, or keep Sydney with a written jurisdiction check. |
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

Validation results: pending.

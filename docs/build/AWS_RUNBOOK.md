# AWS runbook: current state and how to resume

Last updated 2026-10-14 (Claude for Yao Zhu). Read this first when continuing the AWS deployment in a new thread. Background and decisions are in [IDEA-046](../ledger/IDEA-046.md) (layout, cost, apply log) and [IDEA-047](../ledger/IDEA-047.md) (host services, review fixes, offline readiness). The full deployment guide is [architecture-deployment.md](architecture-deployment.md).

## Rules that still apply

- **Spend:** every step that costs money needs Yao Zhu's explicit OK in that thread. Never share AWS passwords or keys in chat or in commits.
- **Hosts:** they stay off until the team has reviewed and fixed PR #20 (Yao Zhu, 2026-10-14). Do not set `enable_hosts` before that.
- **Region:** Sydney (`ap-southeast-2`). The organisers said it is fine (SKILL.md F-118). The account's AWS-managed policy blocks Singapore.
- **Never commit** the ignored files listed below, any state or plan file, or the account ID.

## What exists in AWS now

The team's credit project: Free plan, $100 credits, expiring 2027-04-12. Run `aws sts get-caller-identity --profile larp` for the account ID. It is **not** the account that was checked on Oct 12.

| Applied | When | Cost |
|---|---|---|
| Terraform state bucket (`deploy/bootstrap`) | 2026-10-14 | cents/month |
| Budget `larp-dev-monthly`: $90/month, emails at 50/75/90 % of actual spend | 2026-10-14 | free |
| Core stack (`deploy/aws`, hosts and egress off): VPC, private subnets, S3 gateway endpoint, security groups, KMS key, archive bucket (COMPLIANCE, 82 days), artifact bucket, 3 service secrets, host IAM roles, alarms, an SNS alarm topic with one email subscription, and RDS `larp-dev` | 2026-10-14 | ≈ $24/month in total, almost all the database |

Database `larp-dev`:
- PostgreSQL 14.24 on `db.t4g.micro`, single-AZ, private, encrypted, IAM authentication.
- **1-day automated backups**, because the Free plan refuses more. The daily logical backup to the locked archive is separate.
- **Not migrated yet:** no tables, and no service roles (`roles.sql` not run).

No EC2 instance, internet gateway, NAT gateway or public IP exists.

**Pending on the next core-stack apply (2026-10-15, IDEA-049 WR-L2, #61):** the configuration no longer defines the unused `evidence` service secret (nothing reads it). The next `terraform plan` should show `aws_secretsmanager_secret.service["evidence"]` destroyed (AWS keeps it for the 30-day recovery window) and primary's role policy losing that one read grant, and nothing else from this change.

The alarm email subscription must be confirmed from the email AWS sent to the account owner's address.

## Local files (git-ignored, on Yao Zhu's Mac)

| File | Holds |
|---|---|
| `deploy/aws/development.tfvars` | account ID, bucket names, alert emails, `backup_retention_days = 1`, `enable_hosts = false`, `enable_external_https = false` |
| `deploy/aws/backend.local.hcl` | state bucket, key `development/terraform.tfstate`, region, lock file |
| `deploy/bootstrap/bootstrap.tfvars`, `deploy/bootstrap/terraform.tfstate` | the state bucket's own (local) state; keep it safe |

Terraform 1.13.5 is at `~/.local/opt/terraform-1.13.5/terraform`, and AWS CLI 2 is on the PATH.

## Log in and run Terraform

1. **Log in.** Yao Zhu runs `aws login --profile larp --region ap-southeast-2` and finishes the browser sign-in. If the CLI asks to overwrite the profile with a *different* account, stop and check which account holds the credits.
2. **Point Terraform at refreshing credentials.** Terraform's S3 backend cannot read an `aws login` session. Plain exported tokens expire in about 15 minutes, which on 2026-10-14 broke the database create and needed a state recovery. So use a throwaway AWS config whose `credential_process` refreshes them:

   ```bash
   cfg=$(mktemp -d)/aws-tf.config
   printf '[profile larp-tf]\nregion = ap-southeast-2\ncredential_process = /usr/bin/env AWS_CONFIG_FILE=%s/.aws/config aws configure export-credentials --profile larp --format process\n' "$HOME" > "$cfg"
   export AWS_CONFIG_FILE=$cfg AWS_PROFILE=larp-tf AWS_REGION=ap-southeast-2 PATH=$HOME/.local/opt/terraform-1.13.5:$PATH
   cd deploy/aws
   terraform init -input=false -reconfigure -backend-config=backend.local.hcl
   terraform plan -input=false -var-file=development.tfvars -out=development.tfplan   # review, then apply only with OK
   ```

3. **If an apply fails mid-way with "Failed to save state":** check that no other Terraform process is running. Then run `terraform force-unlock <id>` (only for your own lock), `terraform state push errored.tfstate`, and `terraform untaint <resource>` if AWS did create it. Re-plan, and confirm "No changes" or only the expected additions.

## Next steps, in order

1. **Team review of PR #20** (Keegan, Isaac, Keith), fixes, then merge into `codex/system-testing-20261012`. Re-run CI, and `tools/system_test.py` if code changed (see [SYSTEM_TESTING.md](SYSTEM_TESTING.md)). The runner only accepts `codex/system-testing-*` branches, so for another head push an alias branch at the same commit.
2. **Evidence service live settings** (Yao Zhu): set every `parameters.*.live` in `config/intelligence/intelligence.v1.json` with provenance, and capture the source terms hashes. Until then `larp-evidence` refuses to start (exit 4). Claude can draft values for approval.
3. **Release bundle:** download the CI artifact `larp-bundle-x86_64` (the `.tar.gz`, its `.sha256` and the `.release.json` release manifest, kept 90 days) from the `host-bundle` job of the merged head's CI run. Do not rebuild it locally. Check that `sha256sum` of the bundle and of the `.release.json` match the job summary, and record the CI run ID and both SHA-256 values in the activation pack (#49, #62 item 3, [IDEA-049-D](../ledger/IDEA-049-D.md) D-FND-011 and WR-D3). The bundle carries the same manifest as `release-manifest.json`. Upload the `.tar.gz` and `.sha256` to `s3://<artifact bucket>/releases/`.
4. **Start `primary`** (≈ $23/month more; needs OK):
   - Pin a reviewed AL2023 x86_64 AMI ID. To find the latest: `aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64`.
   - In `development.tfvars` set `ami_id`, `enable_hosts = true`, `enable_external_https = true` and, for access during development, `enable_development_ssm = true`. This also starts `signer`, and the service alarms appear.
   - Plan, review, apply.
5. **Provision each host.** On `primary`, through SSM:

   `enable_development_ssm` attaches only to `primary` and requires development mode and `enable_external_https`;
   unsupported combinations fail the plan. It provides no signer access.

   **Open decision before this step: how to reach `signer`.** It has no internet route and no SSM endpoints (IDEA-046 B2, cost), and there is no SSH access. Options, none chosen yet:
   - (a) an EC2 Instance Connect Endpoint (no hourly charge), with SSH from that endpoint only, during provisioning;
   - (b) temporary SSM interface endpoints (`ssm`, `ssmmessages`, `ec2messages`, about $0.01/hour each per AZ), destroyed after provisioning;
   - (c) a user-data script that fetches the bundle from the artifact bucket and runs `provision.sh` with the pinned hash at boot. This needs no interactive access, but the key file still has to be placed.

   Whichever is chosen, it needs a Terraform change, tests, an IDEA entry and a review.

   ```bash
   aws s3 cp s3://<artifact bucket>/releases/<bundle> /root/
   bash provision.sh <primary|signer> /root/<bundle> --expect-sha256 <CI hash>
   ```
6. **Migrations and roles** (IDEA-045's remaining check). This needs the RDS admin password (`terraform output database_admin_secret_arn`), which no host role can read, by design.
   - Recommended, still to be decided ([IDEA-049-D](../ledger/IDEA-049-D.md) D-DN-05; never during the scored run): from the Mac, run an SSM port-forward through `primary` to the database endpoint (`AWS-StartPortForwardingSessionToRemoteHost`; needs the Session Manager plugin). Then run `PostgresStore.migrate()` and `deploy/postgres/roles.sql` locally with the admin secret, so it never lands on a host.
   - Then verify IAM token login, TLS with the pinned CA and the grants for each role against the two-host map: `primary` gets runtime, execution, archive and uploader; `signer` gets the signer role.
7. **Configs and manifest on the hosts.** Fill `config/hosts/*.example.json`, `config/runtime/runtime.example.json` and `config/runtime/operations.example.json` as root-owned files in `/etc/larp`. Secret IDs follow Terraform's `${name}/…` names (for example `larp-dev/runtime` and `larp-dev/uploader`); set `cycle_timeout_seconds` in `runtime.json`. The release manifest is CI's: `provision.sh` installs the bundle's `release-manifest.json` read-only into the release. Bind it on each host, which only verifies it (every file, the services list and the deviations register exactly as CI recorded them) and adds what CI cannot know, the registration evidence and the hashes of this host's configs: `python -m larp.runtime.preflight --bind /opt/larp/current/release-manifest.json --root /opt/larp/current --build-output /etc/larp/release.json --registration-evidence <file> --runtime-config /etc/larp/runtime.json --service-config NAME=/etc/larp/NAME.json`, one `--service-config` per service config on that host. It needs no git and refuses to replace an existing `/etc/larp/release.json`. Write the signer key as `/etc/larp/signer/wallet.key` (root, `0600`); it is a file, not a Secrets Manager entry.
   - The manifest's code identity comes from CI (#62 item 3, WR-D3): the bundle hash checked in step 5 covers it, and `--bind` refuses a release that differs from it. The host configs stay out of Git (account-specific, IDEA-051), so their hashes are the only fields a host adds.
8. **First-host checks** (`docs/INCOMPLETE_WORK.md`, IDEA-047 item 3), then the rehearsal (AT01–20, five-plus days) before final activation, Oct 27–29.

## Open items not owned by this runbook

- The round driver is built (IDEA-050); its run activation (`service init`/`activate`) is in `docs/build/runbook.md` §1.6. The Executor's capability gate stays with Isaac (next item).
- The verified swap decoder (Isaac, GAP-29).
- Signer version binding (Keegan).
- Journald log shipping (Keegan).

They are listed in `docs/INCOMPLETE_WORK.md`.

## Teardown (not before Nov 20)

Follow the checklist in [architecture-deployment.md](architecture-deployment.md#teardown-after-the-winner-audit-not-before-nov-20-f-17).

To pause spending before then: stop the instances (disks still bill). Stopping the database is also possible, but AWS restarts it after 7 days.

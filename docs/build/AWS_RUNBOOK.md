# AWS runbook: current state and how to resume

Last updated 2026-10-16 UTC (Claude for Yao Zhu; hosts started, see IDEA-066 PC-AWS02). Read this first when continuing the AWS deployment in a new thread. Background and decisions are in [IDEA-046](../ledger/IDEA-046.md) (layout, cost, apply log) and [IDEA-047](../ledger/IDEA-047.md) (host services, review fixes, offline readiness). The full deployment guide is [architecture-deployment.md](architecture-deployment.md).

**2026-10-16 input-preparation update (IDEA-058):** use [GATE_A.md](GATE_A.md)
for the reviewed dev-shadow settings, read-only metadata/balance capture and
pinned host-input assembly. Driver/activation/calendar and the four section
review fixes are on main via PR #81 (`e410e49`), but IDEA-058 also needs #84's
balance check (IDEA-055), which is on `codex/system-testing-20261012` and not yet on
main: build from that branch plus IDEA-058, or from main once that integration
branch is promoted (updated 2026-10-16 after the PR #87 retarget). Yao Zhu supplies the
public wallet address and SEC contact locally. The user's cost-summary/profile
tool supplies the separately reviewed measured rehearsal profile. The AWS state
below is the last recorded state, not a fresh observation on Oct 16.

## Rules that still apply

- **Spend:** every step that costs money needs Yao Zhu's explicit OK in that thread. Never share AWS passwords or keys in chat or in commits.
- **Hosts:** PR #20 was reviewed and promoted (PR #81). Yao Zhu approved and applied `enable_hosts` on 2026-10-16 UTC; both hosts now bill while running, even before LARP is installed. Stopping them (disks still bill) or re-planning with `enable_hosts = false` needs the same approval.
- **Region:** Sydney (`ap-southeast-2`). The organisers said it is fine (SKILL.md F-118). The account's AWS-managed policy blocks Singapore.
- **Never commit** the ignored files listed below, any state or plan file, or the account ID.

## What exists in AWS now

The team's credit project: Free plan, $100 credits, expiring 2027-04-12. Run `aws sts get-caller-identity --profile larp` for the account ID. It is **not** the account that was checked on Oct 12.

| Applied | When | Cost |
|---|---|---|
| Terraform state bucket (`deploy/bootstrap`) | 2026-10-14 | cents/month |
| Budget `larp-dev-monthly`: $90/month, emails at 50/75/90 % of actual spend | 2026-10-14 | free |
| Core stack (`deploy/aws`, initially hosts and egress off): VPC, private subnets, S3 gateway endpoint, security groups, KMS key, archive bucket (COMPLIANCE, 82 days), artifact bucket, 3 service secrets, host IAM roles, alarms, an SNS alarm topic with one email subscription, and RDS `larp-dev` | 2026-10-14 | ≈ $24/month in total, almost all the database |

Database `larp-dev`:
- PostgreSQL 14.24 on `db.t4g.micro`, single-AZ, private, encrypted, IAM authentication.
- **1-day automated backups**, because the Free plan refuses more. The daily logical backup to the locked archive is separate.
- **Migrated 2026-10-17** (IDEA-066 PC-AWS06): migrations 001–013 and `roles.sql` applied through an SSM port-forward from Yao Zhu's Mac; 21 tables and the five IAM-only service roles exist.

| Hosts and primary egress (`deploy/aws`, Gate A plan, IDEA-066 PC-AWS02): `primary` t3.small (public IPv4, HTTPS-only egress through a new internet gateway on the public route table, development SSM) and `signer` t3.micro (private subnet, no public IP, no SSM), AL2023 x86_64 `ami-0587b5bb1bc9eab99`, encrypted 20 GiB gp3, IMDSv2, termination protection; 6 host and 5 service alarms | 2026-10-16 UTC | ≈ $23/month more |

Instance IDs: `primary` `i-040fc5fea8b700e9a` (rebuilt 2026-10-16 so SSM works; SSM `Online`; read-only host smoke check passed, IDEA-066 PC-AWS02), `signer` `i-0f8fe5d5fe5ccba36` (also `terraform output host_ids`). No NAT gateway exists. `primary` is provisioned with build `bb46234` from the mirror-CI bundle (IDEA-066 PC-AWS06; units enabled, none started); `signer` carries only the cloud-init role file. The service alarms (`treat_missing_data = breaching`) sit in ALARM until the services publish metrics.

**Applied 2026-10-16 UTC with the host plan (IDEA-049 WR-L2, #61):** the configuration no longer defines the unused `evidence` service secret (nothing reads it). The plan showed `aws_secretsmanager_secret.service["evidence"]` destroyed (AWS keeps it for the 30-day recovery window) and primary's role policy losing that one read grant, and nothing else from this change; both were applied.

The alarm email subscription must be confirmed from the email AWS sent to the account owner's address.

## Local files (git-ignored, on Yao Zhu's Mac)

| File | Holds |
|---|---|
| `deploy/aws/development.tfvars` | account ID, bucket names, alert emails, `backup_retention_days = 1`, `enable_hosts = false`, `enable_external_https = false` |
| `deploy/aws/backend.local.hcl` | state bucket, key `development/terraform.tfstate`, region, lock file |
| `deploy/bootstrap/bootstrap.tfvars`, `deploy/bootstrap/terraform.tfstate` | the state bucket's own (local) state; keep it safe |

Terraform 1.13.5 is at `~/.local/opt/terraform-1.13.5/terraform`, and AWS CLI 2 is on the PATH.

**2026-10-17 check from Isaac's checkout (IDEA-066 PC-AWS01):** those are
Yao Zhu's local files/tool paths. This Mac has no AWS CLI/Terraform/Session
Manager plugin on PATH or at the documented/common install locations, no
`~/.aws/config` or credentials file, no project-local `.aws` directory, no AWS
environment-variable names in the process or `.env`, and neither private
Terraform input file. The prepared Gate A directory and reviewed rehearsal
profile are also absent. No AWS connection or live stack observation was made.
Resume on the already-configured Mac, or restore access to the same account and
its existing private backend/input files locally before proceeding. Do not
initialize a replacement stack to work around missing local files. The last
recorded applied AWS state above is not a fresh observation.

From the repository root on the configured Mac, this connects and makes a saved
plan only (no infrastructure apply):

```bash
aws login --profile larp --region ap-southeast-2
aws sts get-caller-identity --profile larp --region ap-southeast-2

(
  set -e
  test -f deploy/aws/backend.local.hcl
  test -f deploy/aws/development.tfvars
  larp_tf_config=$(mktemp)
  chmod 600 "$larp_tf_config"
  trap 'rm -f "$larp_tf_config"' EXIT
  printf '[profile larp-tf]\nregion = ap-southeast-2\ncredential_process = /usr/bin/env AWS_CONFIG_FILE=%s/.aws/config aws configure export-credentials --profile larp --format process\n' "$HOME" > "$larp_tf_config"
  export AWS_CONFIG_FILE="$larp_tf_config" AWS_PROFILE=larp-tf AWS_REGION=ap-southeast-2
  export PATH="$HOME/.local/opt/terraform-1.13.5:$PATH"
  terraform -chdir=deploy/aws init -input=false -reconfigure -backend-config=backend.local.hcl
  terraform -chdir=deploy/aws plan -input=false -var-file=development.tfvars -out=gate-a.tfplan
)
```

**SSM attach order (learned 2026-10-16, IDEA-066 PC-AWS02):** the development SSM policy must be attached before `primary` first boots. If the agent starts without it, it registers the instance for account-wide Default Host Management, saves that on disk and keeps failing after the policy arrives (reboot does not clear it). Without a shell, the fix is to rebuild `primary` (nothing is installed on a fresh host): `aws ec2 modify-instance-attribute --instance-id <primary id> --no-disable-api-termination`, then plan/apply with `-replace='aws_instance.host["primary"]'` (expect 1 add, 3 alarm updates, 1 destroy; the new instance gets termination protection back). Do not enable Default Host Management: it is account-wide and would cover `signer`. When using `aws iam simulate-principal-policy`, pass `--context-entries ContextKeyName=aws:RequestedRegion,ContextKeyValues=ap-southeast-2,ContextKeyType=string`; without it the account's region restriction shows a false `explicitDeny`.

Confirm the account matches the team's existing credit project. This plan uses
the current flags in `development.tfvars`; if they remain false it does not
start hosts. For a host-start plan, use the reviewed AMI and three flags in
"Next steps" step 4, then re-plan using the same refreshing-credential setup.
Only apply a reviewed saved plan with the spend approval required above. The
plan block's subshell deletes its temporary AWS config on exit, so a bare
`terraform apply` afterwards would run without the `larp-tf` profile. Apply in
a subshell that rebuilds the same refreshing-credential setup (re-run
`aws login` first if the session has expired; `init` already ran above):

```bash
(
  set -e
  test -f deploy/aws/gate-a.tfplan
  larp_tf_config=$(mktemp)
  chmod 600 "$larp_tf_config"
  trap 'rm -f "$larp_tf_config"' EXIT
  printf '[profile larp-tf]\nregion = ap-southeast-2\ncredential_process = /usr/bin/env AWS_CONFIG_FILE=%s/.aws/config aws configure export-credentials --profile larp --format process\n' "$HOME" > "$larp_tf_config"
  export AWS_CONFIG_FILE="$larp_tf_config" AWS_PROFILE=larp-tf AWS_REGION=ap-southeast-2
  export PATH="$HOME/.local/opt/terraform-1.13.5:$PATH"
  terraform -chdir=deploy/aws apply gate-a.tfplan
)
```

Starting hosts is only infrastructure provisioning: it still needs the exact CI
bundle, input preparation, migrations, manifest binding and unsigned activation
below. As checked on 2026-10-17, #98/#49 (CI/bundle), #118–120 (measured profile)
and #92 (hosted RPC) remain open; #127 tracks the hosted evidence.

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

1. **Reviewed release.** PR #20 and the later integration/review work were promoted to main by PR #81. IDEA-058 (PR #87) targets `codex/system-testing-20261012`, which also carries #84 (IDEA-055); review/integrate it there, then qualify the exact pushed release head and its CI bundle; use the current accepted branch formats in [SYSTEM_TESTING.md](SYSTEM_TESTING.md) for the system runner. Existing main acceptance does not qualify a later runtime change.
2. **Evidence settings and terms** (Yao Zhu): Gate A uses the user-approved unsigned `shadow` settings in `config/intelligence/intelligence.shadow.v1.json`, with the corresponding `dev`/`shadow` runtime configuration and `LARP_EVIDENCE_CONFIG_MODE=shadow`. The poller verifies this config against the bound manifest; signed/final operation cannot use these settings. Capture missing source terms and install all original terms bytes in the host artifact store before startup. For Gate B/final, the pending `parameters.*.live` values in `intelligence.v1.json` still need review and provenance; do not bypass them with development mode.
3. **Release bundle** (from the CI mirror; accepted release builds since 2026-10-17, IDEA-066 PC-DEC01): download the CI artifact `larp-bundle-x86_64` (the `.tar.gz`, its `.sha256` and the `.release.json` release manifest, kept 90 days) from the `host-bundle` job of the merged head's CI run. Do not rebuild it locally. Check that `sha256sum` of the bundle and of the `.release.json` match the job summary, and record the CI run ID and both SHA-256 values in the activation pack (#49, #62 item 3, [IDEA-049-D](../ledger/IDEA-049-D.md) D-FND-011 and WR-D3). The bundle carries the same manifest as `release-manifest.json`. Upload the `.tar.gz` and `.sha256` to `s3://<artifact bucket>/releases/`.
4. **Start `primary`** (≈ $23/month more; needs OK):
   - Pin a reviewed AL2023 x86_64 AMI ID. To find the latest: `aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64`.
   - In `development.tfvars` set `ami_id`, `enable_hosts = true`, `enable_external_https = true` and, for access during development, `enable_development_ssm = true`. This also starts `signer`, and the service alarms appear.
   - Plan, review, apply.
5. **Provision each host.** On `primary`, through SSM:

   `enable_development_ssm` attaches only to `primary` and requires development mode and `enable_external_https`;
   unsupported combinations fail the plan. It provides no signer access.

   **Open decision before this step: how to reach `signer`.** It has no internet route and no SSM endpoints (IDEA-046 B2, cost), and there is no SSH access. Options (**(b) chosen 2026-10-17 by Keegan, [IDEA-080](../ledger/IDEA-080.md)**; Yao Zhu builds it, with pass criteria SA1–SA7):
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
7. **Configs and manifest on the hosts.** Fill `config/hosts/*.example.json`, `config/runtime/runtime.example.json` and `config/runtime/operations.example.json` as root-owned files in `/etc/larp`. Secret IDs follow Terraform's `${name}/…` names (for example `larp-dev/runtime` and `larp-dev/uploader`); set `cycle_timeout_seconds` in `runtime.json`. The release manifest is CI's: `provision.sh` installs the bundle's `release-manifest.json` read-only into the release. Bind it on each host, which only verifies it (every file, the services list and the deviations register exactly as CI recorded them) and adds what CI cannot know, the registration evidence and the hashes of this host's configs: `python -m larp.runtime.preflight --bind /opt/larp/current/release-manifest.json --root /opt/larp/current --output /etc/larp/release.json --registration-evidence <file> --runtime-config /etc/larp/runtime.json --service-config NAME=/etc/larp/NAME.json`, one `--service-config` per service config on that host. It needs no git and refuses to replace an existing `/etc/larp/release.json`. Write the signer key as `/etc/larp/signer/wallet.key` (root, `0600`); it is a file, not a Secrets Manager entry.
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

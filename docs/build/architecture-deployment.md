# Creating the LARP architecture — IDEA-028 RT10–13

This is the complete deployment work list for the runtime architecture. Infrastructure
definitions and local tests exist; AWS resources have **not** been created. The user
authorized implementing what is possible, but has not selected an account, region,
budget, image, retention durations or registered deployment. No credentials are needed
to reproduce the local checks. Isaac's independent review remains required.

## What is now implemented

| Layer | Implemented artifact | Current boundary |
|---|---|---|
| Terraform state | `deploy/bootstrap/`: private, encrypted, versioned S3 state bucket; deletion protection | Bootstrap apply and secured state migration require an account; state is never committed |
| Network | `deploy/aws/network.tf`: two private subnets/AZs, separate service security groups, S3 gateway and private AWS service endpoints | No public host addresses or inbound service ports; optional NAT/HTTPS only for evidence/uploader; application RPC and destination allowlists await owner adapters |
| Database | Encrypted private RDS PostgreSQL, managed admin secret, IAM authentication, TLS enforcement, backups, Multi-AZ default, deletion protection | User chooses version/class/storage/retention; migration and IAM role binding need a deployed database |
| Archive | S3 versioning/Object Lock COMPLIANCE, KMS, public-access denial, conditional creation and deletion denial; separate release bucket | Explicit retention/account/bucket/namespace required; hosted lock verification still unrun |
| Identity | Separate primary/standby/archive/uploader/evidence/signer IAM roles; service secret metadata without secret values in Terraform | Primary/standby/signer database grants and authenticated service communication need reviewed adapters; signer has no public internet access |
| Hosts | Optional six private encrypted EC2 hosts, IMDSv2, role-specific profiles; standby in second AZ | Disabled by default; selected immutable AMI and service provisioning still needed; no user-data trading startup or automatic promotion |
| Maintenance | `larp.runtime.maintenance`: durable hourly anchors and configured backup cadence, exact outbox bytes, bounded attempts, restart/clock handling | No historical anchor backfill; current-time anchors after recovery expose missed intervals; backup size/memory limits must be measured |
| S3 transport | `larp.storage.archive`: conditional PUT, exact-version GET verification, SHA256, COMPLIANCE retention/KMS validation, checksum-pinned restore | Real AWS calls require role permissions; SDK fixtures do not prove hosted durability |
| Service/release | `larp.runtime.operations`, `preflight`; systemd archive service/timer; dedicated database grants | Missing config, certificate hash, registration evidence, code/config hashes or installed pins fail startup; real registration evidence is supplied externally |
| Monitoring | CloudWatch database/host checks, archive health and missing-heartbeat alarms; audit deadline/failure counts included in health | Alarm destinations default empty; no notifications sent. Host log groups exist, but selected AMI's log shipping/clock/disk agent still needs installation and rehearsal |
| CI | Python/real-Postgres tests, protocol fixtures, pinned Terraform/provider with mocked plans, container checks | Never runs Terraform apply, creates cloud resources, or enables live trading |

## Everything needed next, in order

1. **Keegan/team — select deployment inputs.** AWS account and region; allowed host
   jurisdiction/connectivity; spending ceiling; environment (`development`, `rehearsal`,
   or `final`); two AZs; nonoverlapping VPC CIDR; globally unique state/archive/artifact
   bucket names. The template includes RDS, private endpoints and optional six hosts /
   two NAT gateways: estimate the selected configuration's cost before applying it.
2. **Keegan/team — select retention and recovery objectives.** Archive retention must
   preserve the declared audit period (plan G-47: through at least Nov 20 and any later
   technical review); choose the actual duration, RDS retention, log retention, backup
   cadence, tolerated data loss/recovery time and size/attempt budgets. No shortened
   commitment is adopted. S3 COMPLIANCE retention cannot be undone early.
3. **Keegan — bootstrap protected Terraform state, then review a saved AWS plan.** Use
   separate state prefixes and hosts for development and final environments. Restrict
   backend access to the deployment role. Keep `.tfvars`, state and plan files out of Git.
   No AWS access key or service secret belongs in Terraform variables or outputs.
4. **Keegan — provision the reviewed infrastructure.** Select an exact PostgreSQL engine
   version/family available in the region, class/storage, backup settings and alarms.
   `enable_hosts=false`, `enable_external_https=false`, and empty alarm destinations are
   initial defaults. The cloud plan must be reviewed before any paid resources are created.
5. **Keegan + Isaac — build and verify the host image.** Pin the OS/AMI, Python 3.12.15,
   installed packages, RDS CA bundle/hash and application build. Run worker-isolation
   tests on that image, enable clock/disk monitoring and verify logs contain no secrets.
   Use root-owned immutable release directories. Archive/uploader/model/signing hosts
   must not share credentials. No generic runtime user receives the RDS admin secret.
6. **Keegan — apply migrations and service grants.** Use a provisioning identity for
   `PostgresStore.migrate()`; apply `deploy/postgres/roles.sql` once in database `larp`,
   schema `public`. Runtime uses short-lived RDS IAM tokens over certificate-verified
   TLS: `/etc/larp/runtime.json` sets `database_host`, `database_user` = `larp_runtime`,
   `database_name`, `database_ca_file`, `database_ca_sha256` and `region` instead of
   `database_dsn_file` (exactly one of the two is accepted), and the runtime hosts install
   `deploy/requirements-aws.lock` (Secrets Manager and RDS tokens). The execution service
   (`larp_execution`) runs on the primary/standby hosts beside the coordinator (IDEA-045). The archive role can read snapshots and update only maintenance tables plus
   the lock-required `runs.clock_ms` column; it cannot change projection/balances.
7. **Keegan — configure and install archive maintenance.** Fill intentional nulls in
   `operations.example.json` with nonsecret resource references. Use a unique
   `archive/<environment>/<deployment-generation>` prefix. Provision the configuration
   and release evidence as root-owned files in `/etc/larp`; follow the commands below.
   Verify a real PUT/GET/version/retention and backup restore before relying on them.
8. **Owners — integrate the actual application through the published ports.** Keith:
   policy/risk/planner/accounting; Yao Zhu: verified evidence/provider tools and thesis
   scheduling; Isaac: market/execution/reconciliation and narrow signer. Define and
   test authenticated private service channels, least-privilege database grants, and
   approved network destinations; keep blocked capabilities closed until implemented.
9. **Isaac + Keegan — establish independent wallet authority.** The external signer
   must persist/enforce monotonic ownership beyond a database restore; independently
   reconcile every outstanding signed/broadcast transaction. RDS failover, a local
   epoch, or this archive service is not proof that the old primary cannot sign.
   Standby promotion remains disabled; no second active agent is started automatically.
10. **Team — fill activation evidence.** Registered repository/build/wallet binding,
    actual funding/gas observations, selected policy/risk profiles, provider/data rights,
    operational parameters, scored UTC window, applicable registration procedures and
    version/service/deviation records. Never paste populated secrets into chat.
11. **Keegan/Isaac + team — qualify the hosted system.** Exercise real receiver loss,
    local-disk exhaustion, database failover, corrupt/stale backup restore, secret access
    denial, clock jumps, model outage and host restart; measure recovery/slack/retention.
    Confirm CloudWatch alarms reach the selected destinations only after they are authorized.
12. **Team — complete AT01–20 and the declared five-plus-day rehearsal including a
    weekend, then review/freeze the manifested build.** Passing local fixtures does not
    complete these steps. Deployment scripts never remove the live activation block.

## No-cloud reproduction

Use the commands in `runtime-operations.md` for Python/PostgreSQL. Install
`deploy/requirements-test.lock` (includes the AWS test profile), then:

```sh
python -m pip check
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p no:cacheprovider
terraform -chdir=deploy/aws init -backend=false -input=false -lockfile=readonly
terraform -chdir=deploy/aws fmt -check -recursive
terraform -chdir=deploy/aws validate
terraform -chdir=deploy/aws test
terraform -chdir=deploy/bootstrap init -backend=false -input=false -lockfile=readonly
terraform -chdir=deploy/bootstrap validate
terraform -chdir=deploy/bootstrap test
```

Terraform is pinned to 1.13.5, provider to 6.61.0 with provider checksums. CI downloads
the Linux Terraform archive only after matching SHA256
`0dbe3fcc268eb670801af6a6456799d1ae26e72e73797f6c6167e18aafd1fd9a`.
Terraform test uses mocked AWS, not a real account. The test account/bucket names,
AMI and retention values are synthetic examples, not selected destinations.

## Deployment commands once settings and access are selected

Create ignored local variables files using the inputs declared in each module. For
bootstrap: `region`, `account_id`, `state_bucket_name`. For the main module, every
variable without a default in `deploy/aws/variables.tf` needs an explicit selection.
Use an authenticated short-lived deployment role, not long-lived credentials in files.

```sh
terraform -chdir=deploy/bootstrap init
terraform -chdir=deploy/bootstrap plan -var-file=deployment.tfvars -out=bootstrap.tfplan
# After reviewing the saved plan and selected cost/retention choices:
terraform -chdir=deploy/bootstrap apply bootstrap.tfplan

terraform -chdir=deploy/aws init -backend-config=backend.local.hcl
terraform -chdir=deploy/aws plan -var-file=deployment.tfvars -out=deployment.tfplan
# After reviewing this saved plan:
terraform -chdir=deploy/aws apply deployment.tfplan
```

`backend.local.hcl` must set the created bucket, environment-specific `key`, `region`,
`encrypt=true` and `use_lockfile=true`. Scope deployment-role permissions to the state
prefix and its lock file. Preserve the bootstrap state securely and migrate it to a
separate protected state key after adding the corresponding backend block; do not
delete it or commit it. Object Lock belongs on the archive bucket, not Terraform's
mutable state/lock keys. Infrastructure protection is procedural as well as technical:
changing Terraform protection settings can weaken future protection and needs review.

## Archive host provisioning and release gate

Prepare `/opt/larp/releases/<commit>` from the exact clean pushed checkout, retaining
the paths covered by `release_files()`. Create its `.venv` with Python 3.12.15 and
install `deploy/requirements-aws.lock`. Keep the release root and `/etc/larp` writable
only by the provisioning identity; the service account `larp-archive` is unprivileged.
Point `/opt/larp/current` to this release only through the reviewed deployment process.
The image must include the configured RDS CA bundle; its exact SHA256 is checked.

Before packaging, create a manifest **outside the checkout** from the clean pushed
source. The services document names actual services; registration evidence is a JSON
object with `schema: RegistrationEvidence.v1`, exact `build_id`, exact `repository`
URL, and an `evidence_ref` pointing to independently obtained registration evidence.
The code checks consistency and preserves the reference; it cannot prove an organiser
accepted a build. Keep this evidence root-owned. Without it service startup fails.

```sh
python -m larp.runtime.preflight --root . \
  --build-output /secure/release.json --services /secure/services.json \
  --registration-evidence /secure/registration.json --config /secure/operations.json \
  --runtime-config /secure/runtime.json
python -m larp.runtime.operations check --config /secure/operations.json
```

Omitting registration evidence can generate an unregistered review manifest, but it
will not pass service preflight. Hashes bind code, migrations, deployment/config
files, dependency locks, actual operations settings and the RDS certificate. No
secret value is needed in the manifest. Dependency package versions are rechecked
at service startup. Container/OS authenticity is the host-image qualification step.

Install the supplied `larp-archive.service` and `.timer` in `/etc/systemd/system`,
the selected configuration as `/etc/larp/operations.json`, and manifest as
`/etc/larp/release.json`. After a one-shot check on the reviewed host, enable the timer
with `systemctl enable --now larp-archive.timer`. This timer checks once per minute;
the PostgreSQL outbox deduplicates hourly anchors and the configured backup slots.
Do not start a trading process or uploader merely because the archive timer works.

## Backup restore and failure disposition

Keep the exact `ArchiveReceipt.v1` (bucket, key, immutable version, SHA256, retention)
outside the primary database; current receipts are in `archive_outbox.acknowledgement`.
The cloud archive retains its own version metadata. Operators with separately granted
read/list privileges can recover receipts from that protected archive if the primary
is lost. Runtime archive IAM intentionally has no deletion or broad administrative grant.

On an empty, separately migrated target, provide its DSN in a protected temporary
credential file and run the explicit restore command:

```sh
python -m larp.runtime.operations restore --config /secure/operations.json \
  --receipt /secure/backup-receipt.json --target-dsn-file /secure/empty-target-dsn
```

Restoration reads that exact object version, checks its digest and journal, increments
epochs and quarantines every run. It does not start services or promote a signer.
`Backup.v1` deliberately excludes archive delivery payloads/clock to prevent recursively
embedding every earlier backup. Their immutable remote history remains retained. Keep
the old namespace read-only and use a new deployment-generation prefix only after
external reconciliation; never continue an old backup slot with changed bytes.

Attempts and failures survive normal restart. Lost ACK resends the exact queued bytes.
Different bytes at the same key, missing compliance retention, changed encryption or
checksum failure are permanent incidents. Transient errors exhaust the configured
attempt budget and remain visible. No retry budget resets or records disappear on
restart. A missed hourly interval is not backfilled with a fabricated historic state.
The service publishes `Healthy=0` on operational failure and missing heartbeat alarms
cover inability to publish. The 64 MiB test transport default is not a production
capacity claim: select limits and test real export size/time before enabling it.

## Primary references checked

AWS [conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html),
[enforced conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes-enforce.html),
[PutObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html),
[Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html),
[RDS backup recovery](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html),
and [IAM secret access](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_iam-policies.html).
Pinned provider schema and botocore request models are validated locally. The challenge
guardrails are the repository SKILL.md, recorded official sources and IDEA-021/028;
cloud product documentation does not decide challenge policy or activation permission.

# Creating the LARP architecture — IDEA-028 RT10–13

This is the complete deployment work list for the runtime architecture. Infrastructure
definitions and local tests exist; AWS resources have **not** been created. The user
authorized implementing what is possible, but has not selected an account, region,
budget, image, retention durations or registered deployment. No credentials are needed
to reproduce the local checks. Isaac's independent review remains required.

## Current target: lean two-host deployment (IDEA-046, 2026-10-12)

**Current AWS state, login steps and the next steps in order: [AWS_RUNBOOK.md](AWS_RUNBOOK.md).**

The six-host design below is **superseded for deployment** by IDEA-046 Option B, which fits the team's $100 AWS
credit budget. Rows below that say six hosts, NAT or interface endpoints describe the earlier template; Git history keeps it.

| Item | Lean deployment |
|---|---|
| Account / region | New-AWS-experience project on the Free plan ($100 credits). An AWS-managed policy denies Singapore, so **Sydney (`ap-southeast-2`) for now**. The agent would trade from an Australian address (G-17; Q-12 open): **revisit before final activation (Oct 27)**, either a Singapore account or a written jurisdiction check. |
| Hosts | `primary` (`t3.small`): coordinator, execution service, evidence worker, uploader, archive maintenance, each as its own Linux user and systemd unit. `signer` (`t3.micro`): wallet key only. Both use standard CPU credits (never billed above baseline), IMDSv2, encrypted disks, and automatic EC2 recovery. |
| Network | No NAT gateway, no interface endpoints. `enable_external_https` (default off) adds an internet gateway route, a public IPv4 and HTTPS egress for `primary` only. `signer` sits in a private subnet with no internet route; it reaches only the database and the free S3 gateway endpoint. |
| Secrets | Managed secrets `runtime` and `uploader`, readable only by `primary`. The evidence poller reads no secret, so it has none (#61; IDEA-049 WR-L2 removed the unused `evidence` secret). **The wallet key is a root-only file on the signer's encrypted disk** (no Secrets Manager entry or endpoint), handed to the signer service by systemd `LoadCredential`; `larp.signer.keyfile` refuses anything but a regular single-link file owned by root or the service user with no group/other bits (IDEA-047). |
| Signer image | No internet: the release bundle (`tools/build_release_bundle.py`) carries CPython 3.12.15, every wheel, the RDS CA bundle and the release; `deploy/host/provision.sh` installs it offline from the artifact bucket via the S3 gateway endpoint (IDEA-047). |
| Database | RDS PostgreSQL 14.24 `db.t4g.micro`, single zone, 20 GiB gp3, IAM login, TLS, 1-day automated backups (the AWS Free plan refuses longer; the daily logical backup to the locked archive is separate), no CloudWatch log export by default. `primary` may log in as `larp_runtime`, `larp_execution`, `larp_archive`, `larp_uploader`; `signer` only as `larp_signer`. |
| Cost guard | Monthly budget (default $90) alerting at 50/75/90 % of usage cost before credit offsets (`include_credit=false`) when `budget_notification_emails` is set. The Free plan never bills beyond the credits, but closes the account when they run out, which would stop the agent: keep the margin. |
| Settings | Copy `deploy/aws/development.example.tfvars` to an ignored `development.tfvars`. Terraform's S3 backend cannot read an `aws login` session, and exported tokens expire in about 15 minutes (too short for a database create). Run Terraform with `AWS_CONFIG_FILE` pointing to a file outside the repo holding `[profile larp-tf]` with `credential_process = /usr/bin/env AWS_CONFIG_FILE=$HOME/.aws/config aws configure export-credentials --profile larp --format process`, and `AWS_PROFILE=larp-tf` (IDEA-046, 2026-10-14). |

Estimated cost (official Sydney prices, 2026-10-12, 730 h): servers $28.91, database $21.01, disks $3.84, public IPv4
$3.65, KMS/secrets ≈ $2.60, alarms/logs/S3 ≈ $2.50 → **≈ $62/month**, ≈ $66 to Nov 12. Hosts and the public IPv4 cost
nothing while `enable_hosts`/`enable_external_https` are off; stopped instances bill only their disks.

The monthly budget resets in November and does not measure the remaining lifetime $100 credit balance. The account
owner checks the remaining credits separately in Billing before each approved deployment step and through the run;
include usage since account creation when planning the margin. This code correction does not update the already
applied budget: its next saved Terraform plan must include the cost-type change and receive the owner's approval.
Development SSM is available only for `primary`, with HTTPS egress enabled; signer provisioning remains the open
decision in `AWS_RUNBOOK.md` step 5.

### Host services, bundle and provisioning (IDEA-047, 2026-10-14)

| Host | Unit (user) | Entry point | Config (pinned in the release manifest) |
|---|---|---|---|
| primary | `larp-runtime` | `larp.runtime.service` | `/etc/larp/runtime.json` |
| primary | `larp-execution` | `larp.execution_live.main` (composes the live ports; stops `NOT_INTEGRATED` at the Executor's capability gate until the verified decoder, GAP-29) | `/etc/larp/execution.json` |
| primary | `larp-uploader` | `larp.audit.service` (reads only `AI_SEEDS_SECRET` from `larp/uploader`) | `/etc/larp/uploader.json` |
| primary | `larp-evidence` | `larp.sources.live run --release-manifest …` | `/etc/larp/evidence.env` (non-secret) |
| primary | `larp-archive` (timer) | `larp.runtime.operations` | `/etc/larp/operations.json` |
| signer | `larp-signer` | `larp.signer.service` (key via `LoadCredential`) | `/etc/larp/signer.json` |

The execution service and the signer talk only through the database: the execution service writes an immutable
signing request (migration `009`) with its gate snapshot; the signer re-checks fencing, the journaled attempt, the
G-01 allow-list, the step sequence, the gas budget and its own clock, then signs once through the fenced registry or
records a refusal. Swaps are refused until a verified router decoder exists (GAP-29). Examples: `config/hosts/`.

Build and install (no AWS cost to build; each AWS step still needs the owner's OK):

```bash
python tools/build_release_bundle.py --arch x86_64 --out dist   # from the pushed branch head
bash tools/test_host_bundle.sh dist/larp-<build>-x86_64.tar.gz  # optional: offline AL2023 container check
# upload dist/*.tar.gz and .sha256 to s3://<artifact bucket>/releases/, then on each host as root:
#   aws s3 cp s3://<artifact bucket>/releases/<bundle> /root/
#   bash provision.sh <primary|signer> /root/<bundle> --expect-sha256 <SHA-256 from the CI job summary>
```

**Bundle authenticity (IDEA-047 R6).** `SHA256SUMS` and the Python pin come from inside the bundle, so they only show
the bundle is self-consistent. The `host-bundle` CI job writes the bundle's SHA-256 to its job summary; record that
value (with the build ID) in the activation pack, and pass it to `provision.sh --expect-sha256`. Provisioning refuses
a missing or different hash before extracting anything. Upload the CI-built bundle, not a local rebuild, unless its
hash matches the CI value.

Then, as root: write each service's config (the RDS CA SHA-256 printed by the builder goes in `database_ca_sha256`),
bind `/etc/larp/release.json` from the CI-built `release-manifest.json` that provisioning installed:
`python -m larp.runtime.preflight --bind /opt/larp/current/release-manifest.json --root /opt/larp/current
--output /etc/larp/release.json --registration-evidence … --service-config NAME=PATH` for every service config
(it verifies CI's code identity and adds only the evidence and config hashes; #62 item 3), and on the signer write the key as `/etc/larp/signer/wallet.key` (root, `0600`). Provisioning
never writes configs or keys and never starts a service. Still to check on the first real hosts: `LoadCredential`
ownership/mode, RDS IAM login per role, Amazon Time Sync, and the units under systemd (`docs/INCOMPLETE_WORK.md`).

**Disk budget for balance-check observations (#96, IDEA-055; estimate, not yet measured on a host).** Every RPC
call of the balance check writes one `ChainObservation.v1` file under `<market_artifact_root>/chain` on `primary`'s
20 GiB root disk, and these files are audit evidence: never delete them during the run. A check makes 12 calls once
`decimals()` is cached (18 until two reads of it agree, normally the first two checks of each process): chain ID, the finalized block and its re-check, the
native balance, six `balanceOf()` and two nonces. The two block files carry the block's transaction-hash list (about
16 KB at 200 transactions); every other file is under 400 bytes but takes a whole 4 KiB filesystem block. That is
about 70–100 KiB per check. At the normal 10-minute interval: about 144 checks and 10–15 MiB a day. Worst case, every
check skipped and retried every 60 s (pending nonce, ledger ahead of the finalized block, RPC down): about 1,440
checks, 100–140 MiB and 17,000 files a day, so about 2 GiB over the 14-day run. Budget 3 GiB for these files from
first hosted start to the winner audit. Measure the real rate with `du -s` and `df -i` in the Gate A hosted shadow
run, and size the memory and disk decision for `primary` together (#60, D-DN-08).

**Evidence store sharing (IDEA-047 R3, decided 2026-10-14).** The poller's SQLite store and artifacts under
`/var/lib/larp-evidence` are group `larp-evidence` (`StateDirectoryMode=0770`, `UMask=0007`); others get nothing. The
coordinator (`larp-runtime`) joins that group (`SupplementaryGroups=`) and opens the store with
`SQLiteEvidenceStore(path, read_only=True)`, which refuses every write. The shared writer uses `journal_mode='DELETE'`
(IDEA-047 R15), so readers require no WAL/SHM file creation or writable evidence mount. `ProtectSystem=strict`
keeps the evidence directory read-only for runtime. Private stores keep WAL by default; an explicit private WAL
reader uses `journal_mode='WAL'`. Artifact reads verify each file's hash.
The live writer explicitly publishes document files at `0640` before linking/fsync (IDEA-047 R12); umask alone
does not change the `0600` mode of a temporary file. Other artifact sinks retain their private `0600` default.

For an evidence directory populated by an earlier build, before rehearsal and with both evidence/runtime services
stopped, migrate only file permissions as root (never change artifact bytes):

```bash
find /var/lib/larp-evidence/artifacts -type f -exec chgrp larp-evidence {} +
find /var/lib/larp-evidence/artifacts -type f -exec chmod 0640 {} +
```

Keep the directory group/traversal permissions from R3. Verify an artifact read as `larp-runtime` with its
supplementary group before starting the reviewed release. This migration is not run by this PR.

If an earlier build populated the shared evidence database in WAL mode, keep both services stopped and preserve
a protected copy of the database **and all its sidecars together** before migration. Restore their writer ownership
as root if the old runtime created incompatible sidecars:

```bash
find /var/lib/larp-evidence -maxdepth 1 -type f -name 'evidence.sqlite*' -exec chown larp-evidence:larp-evidence {} +
```

Start the reviewed evidence writer first: it recovers any committed WAL data and selects DELETE journaling before
the runtime reads it. The runtime refuses a legacy WAL database before opening it rather than recreating sidecars.
Do not delete an old WAL to fix permissions: it may hold committed records. After a crash with a hot rollback journal,
writer recovery must finish before read-only consumption can resume. These host steps remain unperformed here.

**The evidence unit cannot start yet (IDEA-047 R4).** Its live preflight refuses while
`config/intelligence/intelligence.v1.json` has null `live` parameters and the enabled sources have null
`terms_evidence_sha256` (DR-12, GAP-23). A refused start exits 4 and the unit stays stopped
(`RestartPreventExitStatus=4`) instead of restarting every minute. Set the live parameters and capture the terms
(`python -m larp.sources.live terms --write-register`) in a reviewed, pushed commit first.

Release verification for every long-running unit now uses `larp.runtime.launch` inside `ExecStart` (IDEA-047 R13):
a preflight refusal exits 4 and stays stopped; success execs the service on the same PID. `RestartPreventExitStatus` covers only the main process, so it cannot
stop an `ExecStartPre` failure loop. Older systemd also restarts failed `ExecCondition` checks with `Restart=always`;
the wrapper avoids that version dependency. Archive maintenance remains timer-driven. The upstream semantics are in the
[systemd service documentation](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml#L1001-L1006).

**Monitoring (IDEA-047 R5).** `larp-archive` (every minute, as `larp_archive`) publishes to `LARP/Runtime`:
- `runtime` `Heartbeat` (an open session heartbeat at most 10 minutes old), `Halted` (active HALT reasons) and
  `Quarantined`;
- `uploader` `OverdueLogs` (round logs past their upload deadline);
- `signer` `UnansweredRequests` (signing requests older than 120 s with neither a signature nor a refusal).

While `enable_hosts` is on, each has an alarm that treats missing data as breaching. Alarms notify an SNS topic whose
email subscribers come from `alarm_notification_emails` in the uncommitted tfvars (each address must confirm the AWS
subscription email), plus any `alarm_topic_arns`. Not shipped: journald to CloudWatch Logs (no agent is installed),
and per-unit liveness of the evidence poller (its gaps show in the DR-12 report, `live report`).

**Uploader secret recovery (IDEA-047 R14).** Failure to fetch the secret is a sanitized exit-1 failure: the unit
retries through its existing Restart=always. Invalid configuration, malformed secret response/content, wrong-wallet
binding and foreign credentials remain permanent exit-4 refusals. No fetch failure authorizes an upload.

**Signer logs.** The signer has no internet route and no Logs or Monitoring endpoint (IDEA-046, cost). Its outcomes
(signatures and refusals with reasons) are database rows, archived with the daily backup; its liveness is judged
from `primary` (`UnansweredRequests`). Its journald log stays on its encrypted disk (`/var/log/journal`). After a
rehearsal, or at teardown, collect it from an EBS snapshot of the signer's volume attached to a temporary instance;
never by opening an internet route to the signer.

**Signer trust boundary.** On two hosts `larp_execution` (on `primary`) can write `execution_records`, so the signer's
"registered, AUTHORIZED attempt" check is not independent of a compromised `primary`, and neither are the G-01 checks
against the intent (spender = intent router, amount = intent amount). What the signer enforces on its own comes from
its pinned config (`signing_policy` in `/etc/larp/signer.json`, larp/signer/policy.py; WR02, #44): allowed spenders
and tokens, a per-token input cap, a per-transaction fee cap, no unlimited approve, and the swap block until a
verified decoder exists (GAP-29). The cap values are a team decision (IDEA-049-C WR-C). That is IDEA-046 B1's
accepted trade-off. It sits next to the open
**signer version binding** item: the signer verifies its own release but not the run's registered version, because
`larp_signer` cannot read `events`.

### Teardown after the winner audit (not before Nov 20, F-17)

1. Download the archive, final logs and a database export; keep them with the registered version records.
2. Set `allow_teardown = true` and apply: this lifts database deletion protection, instance termination protection and artifact-bucket protection.
3. Destroy everything except the archive and its KMS key, which keep `prevent_destroy` (COMPLIANCE objects cannot be deleted before their retention date):
   `terraform -chdir=deploy/aws destroy -var-file=development.tfvars -target=aws_vpc.larp -target=aws_iam_role.host -target=aws_secretsmanager_secret.service -target=aws_cloudwatch_log_group.host -target=aws_s3_bucket.artifacts -target=aws_cloudwatch_metric_alarm.database_storage -target=aws_cloudwatch_metric_alarm.maintenance -target=aws_cloudwatch_metric_alarm.service -target=aws_sns_topic.alarms -target=aws_db_parameter_group.larp`
   (destroying the VPC also destroys every host, the database and the network that depend on it). Review the destroy plan before confirming.
4. Delete the RDS final snapshot once the export is verified (it bills per GB-month).
5. Next day, check Billing → Bills and Cost Explorer. What remains is the KMS key (≈ $1/month) and the archive (cents) until the retention date; then delete them and close the account.

## Approved network destinations (two-host layout; IDEA-062, #32)

**Status: proposed, awaiting approval by Keegan + Isaac** (the owners #32 names). Every destination below is derived
by `larp/runtime/routes.py` from the manifested service configs, `config/sources/sources.v1.json` and the clients'
own endpoint constants; `tests/runtime/test_routes.py` R8 checks this table against that derivation. `<region>` is
the config's `region` (`ap-southeast-2` now).

| From | Unit | Destination | Port | Purpose |
|---|---|---|---|---|
| primary | larp-runtime, larp-execution | `web3.binance.com` | 443 | Binance Web3 Open API: market data, quotes, transaction building, broadcast (F-90..F-106) |
| primary | larp-runtime | host of each `driver.balance_rpc_providers` URL in `runtime.json` (primary first, then backups; or the legacy `driver.balance_rpc_url`) | 443 | BSC RPC for the finalized chain-balance check (IDEA-055) with failover (PR 5); account-specific, chosen by Isaac (#92), declared as `bsc-rpc` in `config/release/services.v1.json` and bound to the manifest through the runtime config hash |
| primary | larp-execution | host of `rpc_url` in `execution.json` | 443 | BSC RPC for chain reads and receipts; account-specific |
| primary | larp-uploader | `api.commonservice.io` | 443 | ai-seeds event log (F-99..F-101) |
| primary | larp-runtime, larp-execution, larp-uploader | `secretsmanager.<region>.amazonaws.com` | 443 | service secrets (public endpoint; no interface endpoint, IDEA-046) |
| primary | larp-archive | `s3.<region>.amazonaws.com` | 443 | archive and hourly anchors through the S3 gateway endpoint |
| primary | larp-archive | `monitoring.<region>.amazonaws.com` | 443 | CloudWatch metrics |
| primary | larp-runtime, larp-execution, larp-uploader, larp-archive | `database_host` (RDS) | 5432 | PostgreSQL with RDS IAM tokens over verified TLS |
| primary | larp-evidence | `data.sec.gov`, `www.sec.gov` | 443 | EDGAR submissions and filing archives, SEC press |
| primary | larp-evidence | `www.federalregister.gov`, `www.justice.gov`, `ec.europa.eu` | 443 | the enabled official sources; a disabled source's host is not approved |
| signer | larp-signer | `database_host` (RDS) | 5432 | signing requests and results (migration `009`); the only transport between the execution service and the signer |
| signer | provision.sh | `s3.<region>.amazonaws.com` | 443 | release bundle through the S3 gateway endpoint |
| signer | none | `web3.binance.com`, `api.commonservice.io`, `data.sec.gov`, `secretsmanager.<region>.amazonaws.com` | 443 | **must be refused**: the signer has no internet route (IDEA-046 B2) |

- **Internal transports.** All `primary` services share one host, so none of them talks to another over the network:
  the runtime reads the evidence store from local disk (IDEA-047 R3) and hands work to the execution service through
  the database. The signer is reached only through the database, under its own role `larp_signer`. Every database
  login is a per-role RDS IAM token over certificate-verified TLS (`deploy/postgres/roles.sql`).
- **Not approved yet.** Hosted model endpoints (`api.anthropic.com`, `api.openai.com`) stay off this list until the
  assessor decision (DR-11 / services B8): the runtime refuses any assessor but the deterministic one. SSM endpoints
  are used only by the development SSM agent on `primary`.
- **Enforcement.** The security group allows HTTPS to any address from `primary` (AWS security groups cannot filter by
  host name), so this list is enforced by the application, which calls only the hosts above: fixed constants, the
  manifested configs and each source's `allow` list. The signer's isolation is enforced by the network (no route, no
  public address; Terraform `internet_reaches_primary_only`).
- **Route check (Gate A, R-07).** On each host, from the installed release, without credentials:
  `python -m larp.runtime.routes --role primary --config runtime=/etc/larp/runtime.json --config execution=/etc/larp/execution.json --config uploader=/etc/larp/uploader.json --config operations=/etc/larp/operations.json --root /opt/larp/current --output <new file>`
  and `python -m larp.runtime.routes --role signer --config signer=/etc/larp/signer.json --root /opt/larp/current --output <new file>`.
  Each destination gets DNS, a TCP connect and a verified TLS handshake; no HTTP request, credential or round log is
  sent. Exit 0 means every `primary` destination answered, or every signer internet destination was refused while
  the database and S3 answered. An unset RPC URL or database host fails the check. The report (`RouteCheck.v1`)
  names host and port only. It shows the host's routes, not each unit's systemd sandbox (for example `larp-evidence`'s `IPAddressDeny`).

## What is now implemented

| Layer | Implemented artifact | Current boundary |
|---|---|---|
| Terraform state | `deploy/bootstrap/`: private, encrypted, versioned S3 state bucket; deletion protection | Bootstrap apply and secured state migration require an account; state is never committed |
| Network | `deploy/aws/network.tf`: two private subnets/AZs, separate service security groups, S3 gateway and private AWS service endpoints | No public host addresses or inbound service ports; optional NAT/HTTPS only for evidence/uploader (six-host template, superseded: the two-host destinations and route check are in "Approved network destinations" above, IDEA-062) |
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

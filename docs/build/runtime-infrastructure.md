# Proposed deployment destinations — IDEA-028 RT09

Status: recommendation, 2026-10-10. The user confirmed no database, backup/anchor or
hosting destinations are selected. Nothing has been provisioned or purchased. This
choice does not resolve registration, funded-wallet, policy or rehearsal gates.

Follow-up implementation: `architecture-deployment.md` now provides the full ordered
work list and commands; `deploy/aws/` and `deploy/bootstrap/` define the architecture,
and the durable S3 archive/maintenance service is implemented. Those artifacts are
still unprovisioned; this recommendation has not become a selected AWS destination.

## Recommended starting architecture

Use one AWS account/project for operations, with a separately controlled audit
archive where feasible. Keep PostgreSQL private and use TLS and separate service
roles. Choose a region only after checking the selected provider/venue connectivity
and the team's operating requirements. Singapore is a candidate, not a commitment.

| Need | Recommendation | Reason and qualification |
|---|---|---|
| Database | Amazon RDS for PostgreSQL; small development instance first; Multi-AZ DB instance for rehearsal/production if the budget supports it | Multi-AZ DB instances maintain a synchronous standby in a different availability zone. This handles database availability; it does not establish exclusive wallet signing authority. [AWS Multi-AZ documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZSingleStandby.html) |
| Backups | RDS automated backups plus tested logical exports into protected artifact storage | Automated backups support recovery to a point within the configured retention period. Exercise the application's quarantine/verify/reconcile process after recovery. [AWS backup documentation](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html) |
| Audit archive and hourly anchors | Separate versioned S3 bucket with Object Lock; restricted writer role; independently readable anchor records | Object Lock protects retained versions. Compliance mode prevents shortening a protected version's retention or deleting it, including by root; choose the retention policy before enabling it. Governance mode's bypass permission needs separate consideration. [AWS Object Lock documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) |
| Runtime hosting | Linux EC2 primary and fenced cold standby, with a separate signer host and separate uploader/provider identities | Engineering recommendation based on the tested Linux namespace worker. Run the isolation suite on the selected image. Nested worker sandboxing on a managed container service has not been established by this branch. A database failover must not automatically promote a signer. |
| Secrets | AWS Secrets Manager, scoped to each service's exact secret IDs using IAM roles | IAM policies can grant an EC2 role access to individual secrets. Only signer identity gets wallet material; only uploader gets the audit secret; provider/Web3 workers get their own credentials. Generic model sandboxes inherit none. [AWS secret-access documentation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/auth-and-access_iam-policies.html) |

This is a recommendation for reducing database/backup operations work while keeping
the tested host isolation model. It is not an endorsement of untested cloud failover,
a cost estimate, or a change to the submitted primary/cold-standby and write-once
audit commitments. Start with the existing disposable local stack for development;
select cloud sizes after measuring load rather than extrapolating from 55 short tests.

IDEA-044 role correction (2026-10-12): primary and standby IAM database logins use
the provisioned `larp_runtime` role; archive, uploader and signer use their matching
service roles. The signer also reads committed execution records and their journal
to verify attempt authorization. Its record lock requires PostgreSQL `UPDATE`
privilege on one column, restricted to `revision`; changing it fails the serialized
revision/hash checks. The signer cannot update transaction state, state hashes,
terminal flags, journal rows or existing signature bytes. These grants support
the current registry API; production deployment and signing remain gated.

IDEA-044 release checks also bind the exact runtime service configuration bytes
using `preflight --runtime-config`; the service refuses an absent or changed hash
before loading credentials or constructing a driver. Operations enforces the same
82-day archive retention floor as Terraform, since an explicit object expiry can
override the bucket default. This preserves the deployed policy and is not a new
claim about official retention rules.
Runtime startup also compares the manifest's exact SHA-256 with the durable
`VERSION_REGISTERED` record, including when the code build is unchanged, and
requires the configured mode to match the stored run. Register the verified
manifest before starting a dev/live service; startup cannot create that authority.

## Concrete choices still needed before provisioning

Keegan and the team select account/region, spending limit, database version and size,
backup retention, audit retention, encryption ownership, recovery point/time targets
and allowed operator access. Record the resulting nonsecret resource references in
the deployment manifest; keep credentials in the secret store. Do not replace the
intentional nulls in `config/runtime/activation.example.json` with guessed names.

Keegan deploys and verifies the implemented S3 write-once receiver, scheduled hourly
anchors, backup export/verification and monitoring, then performs the restore drill
on those destinations. Isaac must
review external signer fencing and reconciliation before either primary or standby
can sign. Yao Zhu validates the provider worker's actual capability/network isolation;
Keith supplies the manifested financial and policy configuration. Full cross-owner
acceptance and the declared five-plus-day rehearsal remain necessary.

Avoid assigning a retention duration from this recommendation alone: preserve the
existing declaration until the team records its concrete duration and policy. The
current code has no compaction/deletion path and keeps the 3600-second anchor setting.
No change to official challenge requirements is asserted by the AWS recommendations.

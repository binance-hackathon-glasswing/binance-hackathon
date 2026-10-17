# IDEA-080 — How the signer host is reached for provisioning and key placement

- Date / owner: 2026-10-17 SGT / decided by Keegan (pre-trading checklist, Gate B setup, PR #133); recorded with Claude Code at Keegan's request. Builder of the Terraform change and every AWS step: Yao Zhu (the only team member with AWS access, IDEA-066 PC-AWS01). Key placement: Isaac (DR-03).
- Status: decided (option b); Terraform change and tests built 2026-10-17 (not applied), awaiting Keegan's review.
- Links: `docs/build/AWS_RUNBOOK.md` step 5 (the three options); IDEA-049-D D-DN-05 (routes for migrations and signer provisioning); IDEA-046 B2 (no SSM endpoints, for cost); `deploy/aws/hosts.tf` (development SSM attaches to `primary` only); `deploy/aws/network.tf` (S3 gateway endpoint); #44 (signer policy values); DR-03.
- ID: from the IDEA-080..084 block that PR #126 reserves for the rehearsal and operations work.

## Decision

`signer` has no internet route, no SSM endpoints and no SSH, so nobody can reach it to install the bundle, `/etc/larp/signer.json` or the key file. Of the three options in AWS_RUNBOOK step 5, the team takes **(b): temporary SSM interface endpoints** (`ssm`, `ssmmessages`, `ec2messages`) in the signer's private subnet. They exist only while the signer is being provisioned or its key is being placed, and are destroyed afterwards.

**Why (b)**
- It reuses what Yao Zhu already runs for `primary`: SSM sessions, no SSH keys and no inbound port. Each session start is an AWS API call that CloudTrail records.
- Isaac needs an interactive session for the key file. (c), the user-data script, cannot place the key, so it would still need (a) or (b).
- (a), an EC2 Instance Connect Endpoint, has no hourly charge, but it needs sshd and a security-group path into the signer, and a second access method that we don't use anywhere else.
- Cost: the runbook gives about $0.01/hour per endpoint per AZ, so a few cents for each provisioning window.

## What the change must do (pass criteria, written before any change or apply)

Yao Zhu builds the Terraform change. Keegan reviews the plan output, and the change goes through the repo's Terraform tests.

| ID | Criterion |
|---|---|
| SA1 | Off by default: with the default variables, the plan creates no interface endpoint and adds no SSM permission to the signer's role. A Terraform test asserts this. |
| SA2 | Development only: enabling it outside development mode fails the plan, in the same way that `enable_development_ssm` is guarded today. |
| SA3 | Narrow: the endpoints sit only in the signer's private subnet. Their security group admits HTTPS (443) only from the signer's security group, and private DNS is enabled. |
| SA4 | No internet: with the endpoints up, `signer` still has no route to the internet. Yao Zhu checks this on the host with `python -m larp.runtime.routes --role signer` and sends Keegan the report. |
| SA5 | Torn down: after provisioning and key placement, the variable is set back to off and applied. A plan then shows no endpoints, `aws ec2 describe-vpc-endpoints` lists none for the three services, and the time is recorded here. |
| SA6 | Key handling: the key exists only as `/etc/larp/signer/wallet.key` (root, `0600`) on the signer host. It is never in S3, Secrets Manager, the repo, a chat or a shell history file (DR-03, never-do 7). |
| SA7 | Never during the scored run (F-114): the endpoints are created only before final activation. The final-wallet key (Oct 26–29) uses the same window, and the endpoints are torn down again before Oct 29 00:00 UTC. |

The bundle can reach `signer` from the artifact bucket through the existing S3 gateway endpoint (`deploy/aws/network.tf`), as D-DN-05 (a) describes. Whether the signer's role may read that bucket is for Yao Zhu to confirm in the same change.

## Order of work

1. Yao Zhu: Terraform change with SA1–SA3 tests, after #44's caps are approved. Keegan reviews the plan.
2. Yao Zhu: apply, provision `signer` with the pinned CI bundle hash, install the decided `/etc/larp/signer.json`, and run SA4.
3. Isaac: place the key file over an SSM session (SA6).
4. Yao Zhu: tear down and record SA5 here.

## Results

### Terraform change built, 2026-10-17 (Yao Zhu, with Claude Code; not applied)

Built ahead of #44 so Keegan can review it while the caps are settled; only the apply waits for #44. It follows SA3 **as corrected** in PR #143 and adds SA8 from there.

- `deploy/aws/signer_access.tf` (new): variable `enable_signer_provisioning` (default `false`, in `variables.tf`) creates, only while true, an endpoint security group, interface endpoints `ssm`, `ssmmessages` and `ec2messages` in `aws_subnet.private[0]` (the signer's subnet) with private DNS, HTTPS ingress from the `primary` and `signer` host groups only, one signer egress rule (TCP 443 to the endpoint group only) and `AmazonSSMManagedInstanceCore` on the signer role. The endpoint group and the SSM attachment refuse any environment but `development`.
- The signer role already reads `releases/*` in the artifact bucket (with `kms:Decrypt` via S3), so the bundle download needs no new permission. This answers the question left open above.
- Tests: `safety.tftest.hcl` `signer_access_off_by_default` (SA1) and `signer_access_development_only` (SA2); `signer_access.tftest.hcl` `signer_access_is_narrow` (SA3 corrected, SA8, plus no internet egress or public address for the signer), a plan-only file whose mock fills IDs at plan time. `terraform validate` OK; `terraform test` 19 passed, 0 failed.
- Mutations, each restored: endpoints admitting the signer only (the uncorrected SA3) fails `signer_access_is_narrow`; removing the signer egress rule fails it; defaulting the variable to `true` fails the suite.
- Real plans against the account (no apply): with the normal private tfvars, "No changes"; with `-var enable_signer_provisioning=true`, "Plan: 8 to add, 0 to change, 0 to destroy" (the three endpoints, their group, two ingress rules, the signer egress rule, the SSM attachment).
- Not yet done: Keegan's review of this change and of #143; the apply, provisioning, `signer.json`, SA4/SA9 checks, key placement and teardown (SA5), which follow #44's approval.

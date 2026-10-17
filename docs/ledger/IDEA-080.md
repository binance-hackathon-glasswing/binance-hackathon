# IDEA-080 — How the signer host is reached for provisioning and key placement

- Date / owner: 2026-10-17 SGT / decided by Keegan (pre-trading checklist, Gate B setup, PR #133); recorded with Claude Code at Keegan's request. Builder of the Terraform change and every AWS step: Yao Zhu (the only team member with AWS access, IDEA-066 PC-AWS01). Key placement: Isaac (DR-03).
- Status: decided (option b); Terraform change and tests built 2026-10-17 (not applied); repository review and local merge verification PASS.
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

1. Yao Zhu: Terraform change with SA1–SA3 and SA8 tests (SA3 as corrected below), after #44's caps are approved. Keegan reviews the plan.
2. Yao Zhu: apply, provision `signer` with the pinned CI bundle hash, install the decided `/etc/larp/signer.json`, and run SA4 and SA9.
3. Isaac: place the key file over an SSM session (SA6).
4. Yao Zhu: tear down and record SA5 here.

## Amendment 2026-10-17: review of SA3 (Yao Zhu, with Claude Code; for Keegan's review)

Checked against `deploy/aws/network.tf` before any change is built. SA1–SA7 stay as written; SA3 is corrected and two criteria are added, because the change could pass SA3 and still not work:

- **The signer could never reach the endpoints.** The signer's security group allows egress only to the database and the S3 prefix list (`aws_vpc_security_group_egress_rule.database`, `.s3`; `external_https` is `primary` only). Without an egress rule to the endpoints, the SSM agent on `signer` cannot register.
- **Private DNS is VPC-wide.** The VPC has `enable_dns_support` and `enable_dns_hostnames` on, so an interface endpoint with private DNS makes `ssm.<region>.amazonaws.com` (and `ssmmessages`, `ec2messages`) resolve to the endpoint for **every** host. `primary` reaches SSM over the public endpoint today; while the endpoints exist it would hit them instead, and an endpoint security group that admits only the signer would cut Yao Zhu's SSM sessions and run-command on `primary`.

| ID | Criterion |
|---|---|
| SA3 (corrected) | The endpoints sit only in the signer's private subnet, with private DNS on. Their security group admits HTTPS (443) from the signer's **and** `primary`'s security groups, and from nothing else. |
| SA8 | While enabled, the signer's security group gets one egress rule: TCP 443 to the endpoint security group only. It is removed with the endpoints (SA5). A Terraform test asserts the rule exists only when enabled and targets only the endpoint security group. |
| SA9 | With the endpoints up, an SSM session to `primary` still starts. Yao Zhu checks this in the same window as SA4 and records the time here. |

## Results

### Terraform change built, 2026-10-17 (Yao Zhu, with Claude Code; not applied)

Built ahead of #44 so Keegan can review it while the caps are settled; only the apply waits for #44. It follows SA3 **as corrected** in PR #143 and adds SA8 from there.

- `deploy/aws/signer_access.tf` (new): variable `enable_signer_provisioning` (default `false`, in `variables.tf`) creates, only while true, an endpoint security group, interface endpoints `ssm`, `ssmmessages` and `ec2messages` in `aws_subnet.private[0]` (the signer's subnet) with private DNS, HTTPS ingress from the `primary` and `signer` host groups only, one signer egress rule (TCP 443 to the endpoint group only) and `AmazonSSMManagedInstanceCore` on the signer role. The endpoint group and the SSM attachment refuse any environment but `development`.
- The signer role already reads `releases/*` in the artifact bucket (with `kms:Decrypt` via S3), so the bundle download needs no new permission. This answers the question left open above.
- Tests: `safety.tftest.hcl` `signer_access_off_by_default` (SA1) and `signer_access_development_only` (SA2); `signer_access.tftest.hcl` `signer_access_is_narrow` (SA3 corrected, SA8, plus no internet egress or public address for the signer), a plan-only file whose mock fills IDs at plan time. `terraform validate` OK; `terraform test` 19 passed, 0 failed.
- Mutations, each restored: endpoints admitting the signer only (the uncorrected SA3) fails `signer_access_is_narrow`; removing the signer egress rule fails it; defaulting the variable to `true` fails the suite.
- Real plans against the account (no apply): with the normal private tfvars, "No changes"; with `-var enable_signer_provisioning=true`, "Plan: 8 to add, 0 to change, 0 to destroy" (the three endpoints, their group, two ingress rules, the signer egress rule, the SSM attachment).
- Not yet done: Keegan's review of this change and of #143; the apply, provisioning, `signer.json`, SA4/SA9 checks, key placement and teardown (SA5), which follow #44's approval.

### MR-143–153 — integration merge criteria (2026-10-17)

Keegan requests conflict resolution and integration merges for the reviewed
PRs #143/#144/#148/#149/#151/#153. Preserve history with merge commits;
merge #143 before #149, retaining the corrected SA3 and SA8/SA9 amendment,
Terraform implementation/results and all unrelated ledger rows. Preserve both
the signing-lifetime SL-01 and cap-proposal CP-01 records when they overlap.
Neither proposal becomes an adopted numeric policy through this merge.

Prospective verification: no conflict markers or duplicate ledger IDs in
resolved files; existing Terraform mock tests for signer provisioning pass;
combined Gate A/package/RPC and cap-proposal regression checks pass on exact
Git bytes. Run changed decision/trading/logging code only after it is pushed.
Record test limits and merge SHAs; do not infer hosted acceptance or apply
Terraform. Actions billing (#98) and existing hosted/owner gates remain open.

### MR-143–153 verification (2026-10-17)

PR143 resolves the index conflict while preserving the router, S1 strategy and
experiment rows; merged at `6648934`. PR144 merged at `362e44d`. PR148's
resolution `902a5a6` preserves both CP-01 and SL-01 and a combined section C
index row; eight proposal/policy tests pass on its exact Git tree with the
existing Linux test environment. PR148 merged at `f9a3ac8`.

PR149 resolution `82610c7` preserves the corrected SA3/SA8/SA9 amendment,
implementation evidence and these prospective merge criteria. Static checks
find no conflict markers or duplicate ledger IDs and exactly one copy of each
proposal. Terraform 1.13.5 / AWS provider 6.61.0 validation PASS; **19 mock
tests pass, zero failures**, on exact Git blobs in a temporary Linux checkout
with `init -backend=false` and the existing local provider. No real backend,
AWS plan/apply, key placement or host action is performed by this verification.
The preceding author's real-plan evidence remains a separate dated result.

This completes repository review and conflict-resolution verification;
the earlier pending code-review bullet is superseded. Yao Zhu still owns
approved configuration installation, apply, SA4/SA9 host checks and SA5
teardown; Isaac owns key placement after the existing numeric-policy approval.
The cap/lifetime proposals remain unadopted. Combined final-branch Python
verification and the remaining PR merge SHAs will be recorded in IDEA-058
GA15c. Full CI and all hosted/live gates remain open.

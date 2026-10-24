# Isaac task 2: section C network destination review (#32)

Reviewed integration `47c8e6c`; implementation record IDEA-062 NC-01; issue #136.
The authoritative table is [architecture-deployment.md](architecture-deployment.md#approved-network-destinations-two-host-layout-idea-062-32).
Keegan approved section B on 2026-10-16; **Isaac approved the reviewed section C
application destination scope on 2026-10-17** (IDEA-062 NC-01 D1). This review also corrects the route checker;
it grants no AWS, signing or hosted readiness authority.

| Boundary reviewed | Intended scope | Evidence checked |
|---|---|---|
| Primary → Web3, TCP443 | Market data, quote/transaction construction and the Web3 broadcast path | Client constants; `routes.fixed_hosts`; execution-service boundaries |
| Primary → configured RPCs, TCP443 | Runtime balance providers and execution provider are separately manifested read-only inputs | `routes.plan`, `chain.Rpc` method allowlist; provider selection in separate PR135 does not qualify execution/native tracing |
| Primary → official audit receiver, TCP443 | Uploader's durable round-log delivery | `larp.audit.delivery.BASE_URL`; uploader-only secret loading |
| Primary → model APIs, TCP443 | Same fixed AIand/OpenAI hosts; signed/live application scope approved by SP-NET D2, with separate provider/adoption/host gates | Runtime assessor scope gate and `routes.plan`; Anthropic stays outside the table |
| Primary → enabled evidence sources, TCP443 | Release-registered SEC/FR/DOJ/EC destinations; no disabled-source approval | Enabled source listing/allow hosts; EDGAR constants; evidence-unit metadata deny remains a separate sandbox check |
| Primary → AWS APIs, TCP443 | Secrets Manager for the configured service secrets; CloudWatch metrics; configured S3 buckets | Client region/config; host IAM policy and bucket/object-scoped grants |
| Both hosts → RDS, TCP5432 | Per-service IAM token login over pinned-CA TLS; execution ↔ signer uses database handoffs | Host DB security-group references, SQL-role map, runtime database client |
| Signer → S3 gateway, TCP443 | Release objects from the configured artifact bucket | Private route table, gateway prefix list, release-object IAM scope |
| Signer → public Web3/audit/SEC/Secrets Manager | No approved internet route | Terraform configuration plus required applied-network evidence; route probe alone is insufficient |

The application table and Terraform are different enforcement boundaries:
primary currently has public TCP443 egress. A table approval does not make that
an FQDN or per-process firewall. Release/config integrity and source/client
allowlists constrain intended application destinations; the evidence systemd
sandbox and IAM/SQL grants need their own hosted checks. Development SSM and
provisioning access are separate from application approval. No Terraform or
network permission changes are part of this task.

Two limitations are now explicit. The S3 route test is a regional canary, while
actual clients may use a configured bucket's virtual-hosted hostname; actual
release downloads and stored archive/anchor ACKs must prove that path. The RDS
probe sends no PostgreSQL bytes, so it proves no IAM login or database TLS.
Yao Zhu must retain that evidence on the actual hosts. No real host was probed
by this review.

The corrected signer check treats DNS failure as **INCONCLUSIVE** and exits 1;
unknown statuses also fail. A successful TCP connection—even if TLS fails—is
an unexpected route. Resolved connect failure is only a sampled negative
connection result. Applied route tables, public-address absence and security
groups must establish the wider isolation boundary; a remote service being
down is not proof of an absent internet route.

**Decision recorded — NC-01 D1 (2026-10-17):** Isaac selected “Approve reviewed
destination scope (Recommended)”. Approval covers the application destination
table, retaining primary's general HTTPS egress and signer access limited to
RDS and the S3 gateway. DNS failures do not prove isolation. Yao Zhu retains
real-host route/SG, sandbox, IAM/TLS and configured-bucket S3 evidence. No AWS
permission change, deployment or whole readiness item is approved/completed;
#32 remains open for hosted acceptance.

Verification: the DNS regression was RED at pushed `62ef585`; the repaired
route/security suite at pushed `b720b2a` has **27 passed / 5 opt-in systemd
skips**, macOS/Python3.13. The existing mock-credential test needed pinned
botocore in a disposable test directory; no AWS client or real host was used.
IDEA-062 NC-01 records the commands, environment correction and limits.

## SP-NET D2 — signed/live application scope (2026-10-18)

Isaac authorizes carrying out the exact SP-NET proposal in its own PR. The
architecture table now approves the same two fixed primary/runtime HTTPS
model endpoints for explicitly adopted signed/live builds. This supersedes the
earlier review-only refusal and stale shadow-only capability description. No
client URL/allowlist, model choice, credential, runtime config, AWS permission
or signer isolation change. Provider-policy/account/model rights, funding,
trial/quality/adoption, services and release/host prerequisites remain required.
Criteria/results: IDEA-062 SP-NET D2; current owner checklist: PR133.

# V3-REL01 — next unsigned LLM trial release

2026-10-18 UTC. Branch `codex/llm-v3-trial-release-20261018` derives from latest
integration `817eb71`, including merged PR167 (`4312cd1`) and PR165 (`817eb71`).
This is a new candidate; `7a0ea14` and its published handoff ZIP are historical.
No artifact/run/hash from that older release identifies this candidate.

## Scope and approved protocol

User authorizes this unsigned release, ordinary merges and direct push/dispatch
to `Cookiemunchrr/larp-ci-mirror`. PR133 stays open; PR126 is untouched. No AWS
provisioning or host deployment occurs here. Keith's merged PR168 protocol and
blind rubric were approved by Yao in PC-REL05. Selected protocol/rubric/provider
register and public manifests are carried from PR133 snapshot
`8b0b2381d82d0c596b3ccc33b50579dd159fa78b`; the checklist branch itself was not
merged into integration. No repeated protocol approval is required.

`services.v1.json` and DEV-19 declare opt-in OpenAI `gpt-6.1-sol` medium primary,
independent AIand Kimi K3 high then GLM-5.3 high review/fallback. Required-review
failure grants no authority; verified disagreement abstains. The default remains
deterministic shadow until explicit prepared routing. PROVISIONING describes
pending actual account/host qualification, not an undecided model selection.
Signed/scored adoption remains separate, including the provider financial-use
policy question in the provider register.

V3 uses US$50 total, US$2 owner-reported prior spend and zero permanent reserve,
with cumulative pacing; existing v2's US$40/US$10 policy is historical/separate.
Actual start/config hashes, P0 identity/effort, P1/P2, account billing units,
provider rights and in-flight enforcement of the US$8 trial / US$2.50 UTC-day
caps remain host prerequisites. The protocol explicitly says PR167 implements
account/pacing admission, not those operator sublimits. Paid evaluation must
wait unless Yao records an enforcement method that guarantees them. No paid
calls or new affordability/quality verdict are claimed here.

## KMP-P2 remediation

Criteria were pushed at `4b15756` before new tests. Initial fixture-only errors
at `00431b6` were corrected before assessing the product. The corrected pushed
red regression at `9b5b7cd` has four failures: at/after-cutoff dispatch, rollback
and missing accounting all permit transport. Two controls pass. Fix `6955eaf`
adds a per-call callback immediately before actual transport, after body/artifact
and header preparation. The durable ledger rechecks its clock/window and safety
latch. Refused known-unsent reservations settle at zero in the same transaction;
refusal commits the clock watermark. Storage failures retain reservations and
block further local OpenAI dispatch. Sent timeouts/unknown usage remain fully
reserved, and settlement never clears an existing safety latch. V1/v2 paths
retain their existing behavior.

Focused routing/provider/pacing verification at `6955eaf`: **85 passed, 111
subtests passed**, 3.36 s. Covers actual transport suppression at end and end+1,
rollback/concurrent latch, storage loss, zero-charge durable settlement,
successful dispatch and sent timeout. Full combined results follow below.

## PR165 review and inclusion decision

Retain PR165, already merged into latest integration at `817eb71`; do not delay
the unsigned release or activate S1. Reviewed its changes against merge parent,
including frozen calendar windows, durable attempt/closed-slot accounting,
quote-child reuse, planner expiry, independent signer/economic matching,
broadcast-boundary checks, unbroadcast revocation and continued reconciliation.
Non-S1 baseline checks retain existing behavior. New S1 parameter values remain
proposed; EXP007/B4/B5/B7 and host acceptance remain outstanding. PR165 has no
GitHub review comments or submitted reviews as of this review. Existing execution,
integration and strategy bound regressions are included in combined validation.

## PC-AWS06-RV1 — review of Yao's existing migration/role/TLS evidence

Reviewed the PC-AWS06 report on PR133, source bundle
`bb46234f1b997dae968e2c3f3668d73627857376`, bundle SHA-256
`dd2d1945748876cd74ab2a4c8adf08db1429af2933d2822ce35e82eead627379`, manifest
`ee77d97a2acbdf80dba7d99b0dd1f229806d751fd04dbc61323755d48e95e2f4`, CA
`d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b`.
Compared current `migrations/001..013`, `deploy/postgres/roles.sql` and
`larp/runtime/database.py`: no changes from that source to this candidate.

The report is internally consistent with those files: an initially empty RDS
became 21 tables with migrations001–013; all five application roles have
`rds_iam`. Admin migration used TLS1.2 **verify-ca** via SSM port-forward.
Actual primary-role runtime/execution/archive/uploader logins used TLS1.2
**verify-full** with the pinned CA, each checking one expected and one forbidden
privilege. Signer login from primary was correctly refused. Preserve the first
runtime ConnectionTimeout and the successful four-role rerun one minute later.

Accept this as the reported empty-DB migration and limited primary IAM/TLS
review. It does not prove a populated-database upgrade, every privilege grant,
signer-host login or the new release's installation. In particular, migration013
ran with no existing execution rows; that does not exercise unsafe-row refusal
on RDS. The 13/13 route report predates model endpoints and execution-host checks.
Four distinct terms files cover six source entries; do not report six distinct
files. Raw reports remain on Yao's host/private evidence store; this reviewer
made no new AWS observations. Actual provisioning/deployment and signer checks
remain with Yao/IDEA080 and are not closed by this document.

## Gap report follow-up

Review Yao's fixed Oct17 11:00 UTC–Oct18 11:00 UTC report once produced after
Oct18 11:00 UTC / 19:00 SGT. Pending report does not delay the bundle. Apply
existing PC-GAP01 only to the two historical backfill explanations, retain raw
poll evidence and INCOMPLETE coverage, and do not waive later runtime failures.
No future report or 24-hour coverage pass is claimed.

## CI provenance and delivery

Before freezing, require all jobs green on the exact pushed SHA in the named
mirror and fetch its original `larp-bundle-x86_64` artifact. Verify the original
tarball against `.sha256`, manifest identity/source, manifest SHA and CA hash;
record run ID and upload those original bytes to a new GitHub release. Do not
substitute a rebuilt local bundle, source ZIP or handoff-only ZIP.

Initial mirror Git/API reads both return repository-not-found while the
registered repository works. Actual push/dispatch outcomes and validation are
recorded below when attempted. This document grants no CI/artifact acceptance.

### Combined validation and actual mirror block

Pushed validation source `61a123aa32af34f17e5640bbc9778293851e460e`:
**2029 passed, 6 skipped, 2981 subtests passed**, 174.77 s, exit0, Linux /
Python3.12.14 / pinned test lock / disposable PostgreSQL14.24. Three Linux
bubblewrap tests ran. Five actual-systemd tests remain skipped because this
container does not run systemd; one external recorded-response corpus is opt-in.
No xfails, golden regeneration or changed acceptance thresholds. Command:

```sh
env -u AWS_PROFILE PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PIP_CACHE_DIR=/workspace/.cache/pip \
  LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/larp_test \
  .venv-runtime/bin/python -m pytest -q -ra -p no:cacheprovider
```

Full raw log `/workspace/larp-cloud/llm-v3-release-20261018/full.log`, SHA-256
`163d29469c38653bfe0540793279df6c05a35a15bcfea63097ece7932f7e2380`. Release-register tests, bundle/provenance
regressions and PR165 strategy/integration/execution/signer cases pass in that
run. Separate `tools/render_deviations.py --check`, dependency `pip check`,
`git diff --check` and offline PostgreSQL recovery/audit demo pass. The first
manual demo invocation omitted the required disposable DB variable and was
refused before execution; supplying it passed. This is local verification, not
mirror CI or actual provider/host qualification.

Actual authorized mirror push of this SHA to
`refs/heads/codex/llm-v3-trial-release-20261018` returned exit128:
`remote: Repository not found.` Direct
`gh workflow run runtime.yml --repo Cookiemunchrr/larp-ci-mirror --ref codex/llm-v3-trial-release-20261018`
returned exit1 / HTTP404 for the workflow endpoint. The registered-repository
push works. Asked for the existing GitHub connection's mirror repository access
to be restored, without asking for a token or repeated release authorization.

**Release status: CI/ARTIFACT BLOCKED, not frozen/accepted.** No new mirror run
ID, original tarball, checksum, external manifest or verified new CA hash exists
here. Do not reuse PC-AWS06's CA hash as verification of a nonexistent new bundle.
Once access works, the release agent retries the direct push and dispatch, waits
for all jobs green at the exact published SHA, downloads and verifies the original
artifact and attaches those original bytes to a new GitHub release. AWS and host
deployment remain with Yao. The pending 19:00 SGT gap report is separate.

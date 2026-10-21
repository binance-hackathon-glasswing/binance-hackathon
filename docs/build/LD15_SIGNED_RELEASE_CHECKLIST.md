# LD15 — signed release qualification checklist (Keegan)

Status: **RC2 CANONICAL CANDIDATE QUALIFIED; actual signed-release/configuration and host bindings OPEN.**
The latest receipt below records canonical `b22207e` and original artifact12352993133.
It lists what must be true before Keegan cuts the exact signed
development release that LD16–LD21 install and drill. The same procedure, re-run on the frozen commit, produces the
final activation release (LD24). Owners and gates come from the #133 noticeboard (LD01–LD24) and
[DEPLOYMENT_BUILD.md](DEPLOYMENT_BUILD.md) DR-18/DR-20. Old unsigned bundles (`ea25b52`, `c5be269`) do not qualify
signed bytes.

## 1. Inputs that must be merged into canonical first

| Input | Source | State on 2026-10-20 |
|---|---|---|
| Untrusted-router policy and hash (LD03) | IDEA-070 LD03, `untrusted-router-policy-ld03-20261020.json` `05759e90…` | merged (#205) |
| Fresh calldata / gas evidence (LD02b) | #211 | open |
| #27 finite authority code (LD04) | #200 | merged |
| L = 660, m = 30 in the LIVE profile (LD04-P) | #210 | open; Keith reviews (#120) |
| Allowance recovery (LD06) | #202 | merged; numeric/host acceptance open |
| Initial-only gas scope (LD07/LD08) | #199, #207 | #207 open |
| Abnormal-fill disposition (LD05) | Keith | open |
| Measured profile, fees and gas (LD09) and #44 caps (LD10) | Keith, Isaac | open |
| Model/assessor scope (LD11) | Keith; adoption at LD22 | PF-01 direction selected; PR206 repairs under review, evidence/adoption open |
| Operations settings (LD13/LD14) | Keegan, Isaac | LD13 merged; LD14 open |

2026-10-21 LD04-P-RV01 update: #207 and #210 are merged. Combined initial-only+L/m
candidates regenerate exactly (20 authority checks and full local suite PASS;
see IDEA-049-C/PR210 receipt). The table above preserves its dated snapshot.
Regenerate the actual selected S1 or permitted fallback profile with reviewed
measurements/calendar and `--initial-gas-only` plus all four authority flags,
then pin the reviewed profile hash after #120/#44 acceptance.

### §1 state on 2026-10-21 (RC1, IDEA-083 AB-REL-RC1)

| Input | State | Remaining owner action |
|---|---|---|
| LD02b fresh calldata / gas | merged (#211); LD02c/LD02d measured | none |
| LD03 untrusted router `05759e90…` | merged (#205) | none |
| LD04 / LD04-P (#27, L 660, m 30) | merged (#200, #210) | none |
| LD06 allowance recovery | merged (#202) | numeric/host acceptance at LD20/LD21 |
| LD07/LD08 initial-only gas | merged (#199, #207) | none |
| LD09 gas budget (option B) | merged (#216); candidates `54eb6fba…` (rehearsal), `07e8e8c9…` (final) | Keith: confirm #120 ([RV120-01](QUOTE_COST_REVIEW_120_20261021.md)), set the new rehearsal `WINDOWS` (DEV-24) and rebuild the candidates, pin the hash |
| LD05 abnormal-fill disposition | open | Keith |
| LD10 #44 caps and holdings coverage | CAP-02 numeric signer ceilings set; coverage open | Isaac |
| LD11 model/assessor scope | #206 repairs merged; adoption at LD22 | Keith |
| LD12/LD13 operations | merged (#217, #221; LD13) | none |
| LD14 operations values | interim rehearsal values merged (#227, LD14-I01): watchdog 300 s, delivery-age 600 s, MemoryMax unchanged | Isaac: final values from rehearsal measurements before LD24 |
| KG-DEC-01 pre-sign simulation | exact-payload gas-limit check in `Executor.prepare` merged (#223) and host-checked (#224) | Isaac: PS-01 RPC `eth_call` (separate branch) if adopted |
| RG2 fault hook | merged (#222) | drills at LD21 |
| Deviations register | `--check` PASS; 15 FINAL, 9 DRAFT (DEV-01–04/07/19/22/23/24) | DRAFT rows decided before LD24 (live refuses DRAFT) |

**RC1** is canonical `0ba4f44`. It is CI-qualified on the mirror (see the RC1 section below). A rebuilt profile or
any further release-code change makes a new candidate that needs its own run; a PASS doesn't carry over.

## 2. Source identity

- [ ] The release commit is the pushed head of `codex/system-testing-20261012` (or the challenge branch), with no
  history rewrite. `tools/build_release_bundle.py` refuses anything else.
- [ ] `config/release/repository.v1.json` names the registered repository. `services.v1.json` and
  `deviations.v1.json` are complete for the selected scope: DEV-23 (untrusted router), the initial-only gas scope,
  and any short-rehearsal deviation.
- [ ] `python tools/render_deviations.py --check` passes. Live mode refuses OPEN/DRAFT deviations, so every row
  needs its decision before LD24.

## 3. Required checks on the exact commit (CI `Runtime acceptance`, on the accepted mirror while org billing is broken)

| Job / check | Command | Pass |
|---|---|---|
| infrastructure (`deploy/aws`, `deploy/bootstrap`) | `terraform fmt -check -recursive`, `init -backend=false`, `validate`, `test` | all four |
| runtime suite | `pip install -r deploy/requirements-test.lock`, `pip check`, `pytest -q -p no:cacheprovider` with PostgreSQL 14.24 and bubblewrap | 0 failures; skips explained |
| real systemd | `LARP_TEST_SYSTEMD=1 pytest -q tests/runtime/test_systemd_conditions.py` | 5/5 |
| demo and container | `python -m larp.runtime.demo`; `docker build -f deploy/Dockerfile`; `docker run --network none --read-only --cap-drop ALL` | exit 0 |
| host bundle | `python tools/build_release_bundle.py --arch x86_64 --out DIR`; `bash tools/test_host_bundle.sh DIR/larp-*-x86_64.tar.gz` | both roles provision twice, offline |

Record the CI run ID, the bundle `.tar.gz` and `.release.json` SHA-256 from the job summary, and the artifact ID.
Download the original artifact; **never rebuild locally for installation**. A local build is a dry run only.

## 4. Bindings the release must carry (checked at LD16/LD17)

- [ ] Profile file and StrategyProfile.v1 hashes (LD09/LD04-P), pinned in `runtime.json`.
- [ ] `untrusted_router_policy_file` / `_sha256` = `05759e90…` in both `execution.json` and `signer.json`, with no
  `router_evidence_*` pair.
- [ ] Signer policy caps from LD10 (never the example cap labels), the gas limit/price caps, `initial_gas_only`
  matching the profile, and a qualified execution RPC (PF-01 selects BNB Chain public then NodeReal public for read-side qualification; balance-read approval alone does not qualify execution).
- [ ] RDS CA SHA-256 (`d7389074…`, unchanged in the dry run below) in each service config.
- [ ] `python -m larp.runtime.preflight --bind` on each host with the registration evidence and every service
  config. It refuses to replace an existing bound manifest.
- [ ] Version event (`Coordinator.register_version`) before any execution command; `service activate` with a named
  reviewer and review reference.

## 5. Record (append to IDEA-083 as a new AB-REL entry)

Commit, CI run ID, job results with counts, bundle/manifest/artifact hashes, BUNDLE.env identity, inputs from §1
with their hashes, open exceptions, and the reviewer. Missing evidence keeps LD15 open; a PASS on an older commit
does not carry over.

## Dry run — canonical `72bb62c` (2026-10-20, local, not a release)

- **Bundle build: PASS.** `larp-72bb62cf5149-x86_64.tar.gz`, SHA-256
  `3826716816df9578482c48d32e7c4a8ae277626cde77a79c549de351b9790eca`; release manifest
  `02b372e5ee29b26a225eb4198a170834b60b63646af904f14132c091adfc6d82`. Python 3.12.15 (`0e56475e…`), RDS CA
  `d73890748b5a95551800df8a6f07c9c800e32ed34da7e6c9505918bf8ac2398b` (matches the CA recorded for the host).
- **Host-bundle provisioning: NOT_RUN.** Docker Hub returned 429 Too Many Requests for the pinned
  `amazonlinux:2023@sha256:8ed3c0a9…` image twice. CI's `host-bundle` job runs this on the mirror.
- Terraform and real-systemd checks were not run locally (no Terraform binary, no systemd PID 1 here). The full
  suite on this canonical head was not re-run for the dry run; the most recent full runs on branches carrying it
  passed (#210: 2237 passed; #211: 2229 passed).

The dry run shows the builder works on current canonical and that the CA and Python pins are unchanged. It
qualifies nothing: §1 inputs are still open.

## RC1 — canonical `0ba4f44` (2026-10-21, mirror CI, candidate only)

- Mirror [run 39601143671](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39601143671): all four §3
  jobs passed.
- Artifact 12345743795: zip `83addcc6…e1b3`, bundle `b3b4fad3…2414`, manifest `9e7bb0df…68fe`, CA `d7389074…`
  (unchanged).
- Record: IDEA-083 AB-REL-RC1.
- **Not the release.** §1 still lacks Keith's #120/DEV-24 window and rebuilt profile, LD05, the LD11 scope, LD10
  coverage, PS-01 if adopted, and the DRAFT deviation decisions. Any of these that changes a tracked file needs a new
  candidate and run.

## RC2 inputs — scoped rehearsal (2026-10-21; canonical candidate qualified)

[Exact input/coverage packet](evidence/rehearsal-qualified-inputs-20261021/README.md).
LD05-Q01 implements raw abnormal receipt/gas accounting and sustained quarantine;
LD11-RH01 selects the user-confirmed deterministic EQUAL_WEIGHT rehearsal, model
claims SHADOW and no hosted calls. Gate A scope checks restrict that exception to dev
REHEARSAL. LD10-Q01 supplies fresh holdings/nonce/zero allowances and all15 request-bound
minimum/max BUY and max-position SELL quotes; real numeric reviewer50/50 COVERED.
The selected profile is41332056… / StrategyProfileeb61ca86…, signer policy3241abd3… and router
05759e90… . Its complete pair gas envelope is384000000000000wei, four exits1536000000000000wei;
conservative N=15 seed target0.007296BNB, funding still separate.
**Superseded by LD10-P03** ([exit split](evidence/rehearsal-exit-split-20261021/README.md)):
balanced exit children and an eight-action reserve 3072000000000000wei, profile
e95d5842… / ddb82813…, target 0.008832BNB. That changes runtime code, so RC2 does
not qualify it; a new candidate, run and fresh child-quote coverage are required.

## RC3 — canonical `5bee006` (2026-10-21, LD10-P03 source)

Mirror [run 39637679504](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39637679504):
all four jobs PASS; runtime 2452 passed / 7 explained skips / 3859 subtests on
PostgreSQL 14.24, real-systemd 5/5, demo and Docker PASS. Original artifact
12363800624 zip `fa446a15…` matches GitHub's digest; bundle `749e2fc2…`, 244/244
checksums, inner manifest `847dc027…` byte-identical to the published one, and all
205 manifested files match `5bee006`. Not rebuilt locally.
[Receipt](evidence/ab-rel-rc3-20261021.json). LD10-P04 fresh coverage binds this
build. Unbound candidate: LD16/LD17 bindings, funding and acceptance remain.

The numeric tool retains OWNER_REVIEW_REQUIRED; this is delegated technical coverage,
not a forged Keith/Isaac attestation or an installed configuration. Their exact#120 /
LD16 owner bindings plus actual final release/run/DB/RPC/CA configuration remain.
#119 actual fee confirmation follows LD19/20; optional extra PS-01 RPC eth_call is
not adopted for this scope (merged exact-calldata prepare gas simulation retained).
Final S1/model/deviation/final-wallet scope remains before LD24. No signing is enabled.
Canonical CI/original artifact identities are recorded as AB-REL-RC2 below.
Release-code PASS on any previous commit does not qualify this candidate.


2026-10-21 LD10-Q01-R1 / LD11-RH01 final scope binding: selected file
`rehearsal-deterministic.json`, file SHA-25641332056bf18e9f07a35f0d4446e2fb02a3d7ebbddabd25b054e03203c3a0a7a,
StrategyProfile.v1 eb61ca8646a42cfb59816888576555d10e8aef3502d973ae06e00daacc6670a4.
Both evidence_mode and effective falsifier_authority are SHADOW. Fresh primary-only
packet at14:10Z rechecks all holdings/nonce/allowances and15 max-position quotes;
50/50 numeric checks COVERED under exact CAP-02 policy. Earlier bad7f160 profile
binding is historical and superseded. Selected public coverage/scope files use the
`-deterministic` name (see packet README); private packet/review remain outside Git.


### RC2 branch outcome — commands pass; explicit merge exception

[Public receipt](evidence/ab-rel-rc2-20261021.json) records exact source a8bdaf7,
mirror39614839775 and verified original artifact12352148043. All required commands
pass (2416 runtime tests,5 systemd tests,demo,Docker; all244 original bundle file
checksums). Runtime job/run metadata remains in_progress, so this is not a finalized
four-job PASS. Auto-review refused merging PR231 on that unresolved prerequisite.
Keegan then explicitly replied "Approve merge despite pending status"; PR231 was
merged at `b22207e050ea50338d48cf7129378caf480ef290`. The exception covers the
repository merge only. Canonical mirror run39617977531 and its original artifact
pass qualification below; no installation is approved.

### RC2 installation inputs that remain separate

The selected profile is `rehearsal-deterministic.json` (file41332056…,
StrategyProfile.v1 eb61ca86…), not the earlier superseded bad7f160… candidate.
Before LD17, the approved database-role application must include the merged
`deploy/postgres/roles.sql` column grant: `SELECT (run_id,observation)` on
`execution_observations` for `larp_signer`. It enables the independent durable
abnormal-outcome fence. Actual-role qualification passed in CI; production grants
have not been changed. Apply and verify only within the separately approved host/
database installation. LD16 final run/release/DB/RPC/CA and owner bindings, LD17
per-host approval, LD18 key placement and funding remain open.

### RC2 canonical outcome — PASS (candidate only)

Canonical `b22207e050ea50338d48cf7129378caf480ef290` is CI-qualified by mirror
[39617977531](https://github.com/Keegan4/Keegan4-larp-ci-mirror/actions/runs/39617977531),
completed/success at2026-10-21T14:43:58Z. All four jobs SUCCESS. Runtime2416 passed,
7 skips,3808 subtests (496.41s); real-systemd5/5 plus5 subtests; demo/Docker and
offline both-role bundle provisioning PASS. The five systemd tests skipped in the
ordinary run pass separately; two external/private-fixture tests remain opt-in.

Original artifact12352993133 was downloaded and verified without rebuilding:
ZIP307d4c4b…8657, bundleecc589a5…ba2a, manifest427a8cc6…f8b0;244 bundle checksums
and205 manifest source/config hashes PASS. BUNDLE.env identifies canonical b22207e,
x86_64, Python3.12.15 and unchanged pinned CA. Full identities and retained original
paths are in [the public receipt](evidence/ab-rel-rc2-20261021.json).

This completes the requested canonical candidate requalification. LD16 owner/config
acceptance and actual registration/runtime/operations binding remain; the artifact
manifest is intentionally unbound. Production roles.sql, host writes/session, key,
funding and the bounded round remain separate. No code changed in this result-only
documentation update, so the receipt continues to identify the immutable b22207e
artifact rather than implying a new bundle at the later documentation commit.

### #120 owner evidence update — RV120-RV01

Keith's PR226 review5602037122 (2026-10-21T15:23:22Z) confirms original distributions
reproduce and supports17bp MSFTB. Both inline documentation findings are addressed in
[the corrected review](QUOTE_COST_REVIEW_120_20261021.md): directional quote movement
is separate from actual reverts, and router minimum-output/recipient enforcement
remains an accepted unverified assumption. Review state COMMENTED; no explicit exact
current-profile/gas/model/config adoption is inferred. This update changes no profile,
policy or runtime bytes and needs no replacement of the original qualified artifact.

PR230/LD10-P02 remains BLOCKED_EXECUTION_CASH_CAP: the retained hypothetical
max-position NVDAB SELL exceeds20.10USDT. Full exit-sizing/count/reserve and fresh
coverage acceptance precede LD16. Original RC2 qualifies only b22207e; PR230's
changed checker needs the subsequent applicable source qualification. RV120-RV01
does not replace that requirement or change any limits/profile.

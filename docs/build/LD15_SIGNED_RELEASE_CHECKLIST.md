# LD15 — signed release qualification checklist (Keegan)

Status: **PREPARED.** Nothing here is a release. It lists what must be true before Keegan cuts the exact signed
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

# IDEA-062 — Approved network destinations and a read-only route check per host role (#32 slice)

- Date / owner: 2026-10-16 SGT / Claude Code at the user's request. Reviewers to approve the destination list: Keegan + Isaac (the owners #32 names).
- Status: open (criteria pre-registered; nothing built yet). 2026-10-16 update: built and supported offline, see Results; hosted checks open
- Links: #32 (R10, P1), #33 (R11, P1); IDEA-046 (two-host layout, L03 `internet_reaches_primary_only`); IDEA-049-D R-07 and D-DN-05; IDEA-051 (Gate A); IDEA-055 (balance RPC); `docs/build/DEPLOYMENT_DAY.md` step 9; GAP-65.

## Triage of #32 and #33 at `7a8a246` (`codex/system-testing-20261012`)

The review baseline was `b4dc6bb`. Since then IDEA-046 replaced the six-host layout with two hosts: `primary` runs the coordinator, execution service, evidence worker, uploader and archive maintenance and has the only HTTPS egress; `signer` has no internet route and talks to the execution service only through the database (signing requests, migration `009`). So the "primary/standby cannot reach Web3/RPC" and "no private channel to a relay or signer" findings no longer describe the code.

**#32 acceptance criteria**
1. *Document approved Web3/RPC destinations and authenticated internal transports for the actual layout.* **Partly met.** The transport is documented (signer via the database, IAM/TLS login, `docs/build/architecture-deployment.md`). No per-unit destination list exists; the "What is now implemented" table still says "optional NAT/HTTPS only for evidence/uploader; application RPC and destination allowlists await owner adapters", which is stale. Code/doc work: this entry. Approving the list: Keegan + Isaac.
2. *Demonstrate market, chain, signer and evidence communication from provisioned hosts.* **Not met; hosted action.** No hosts are running (IDEA-051). It needs Yao Zhu's spend OK for `enable_hosts`/`enable_external_https`, then the Gate A run. No tool exists for the read-only route check that DEPLOYMENT_DAY step 9 asks for: this entry builds it. The signer half also needs the signer access route (D-DN-05 / AWS_RUNBOOK step 5, team decision) and the account-specific RPC URLs (`balance_rpc_url`, `rpc_url`).
3. *Signer isolation and least-privilege boundaries remain enforced.* **Met in code** (Terraform tests `host_isolation`, `internet_reaches_primary_only`; `roles.sql` grants), to be re-confirmed on the hosted plan and by the signer-role route check (expected BLOCKED results).

**#33 acceptance criteria** (no code slice here; recorded so the owners see the current state)
1. *Production driver and qualified ports.* **Driver met offline** (PR #66, IDEA-050). "Qualified" ports need the hosted Gate A/B runs.
2. *Router decoder, fenced release, manifested live configuration with measured profiles and captured terms.* **Not met.** Fenced release is built (PR #66). Open: the GAP-29 byte-bound swap decoder and the fake-only Executor gate (Isaac, section C); C-OPEN-005 native settlement; the measured `QuoteCostSummary.v1` (producer in open PR #88, captures by Isaac/Keith); live intelligence values and terms hashes (Yao Zhu, DR-12/GAP-23; PR #87 adds shadow-only settings); hosted assessor (DR-11/B8, decision).
3. *Run the systemd entry point end to end in the authorized rehearsal.* **Not met; hosted** (Gate B, then the rehearsal from Oct 21, D-DN-02).

## What this builds

`larp/runtime/routes.py`, shipped in the release bundle and run as `python -m larp.runtime.routes`:
- derives each host role's destinations from the manifested service configs, the release's `config/sources/sources.v1.json` and the clients' own endpoint constants (one source of truth);
- checks each with DNS, a TCP connect and, for HTTPS, a certificate-verified TLS handshake. It sends no application data: no HTTP request, no credentials, nothing to ai-seeds (never-do #13), no PostgreSQL protocol bytes;
- writes a `RouteCheck.v1` report that names only host and port.

Plus an "Approved network destinations" table in `docs/build/architecture-deployment.md`, the stale row corrected, and DEPLOYMENT_DAY step 9 naming the command.

## Pre-registered pass criteria (written before any test or code)

Tests in `tests/runtime/test_routes.py`. Each must fail before the build and pass after it.

| ID | Criterion |
|---|---|
| R1 | **Primary destinations.** From the example configs with synthetic values filled in, `plan('primary', …)` returns exactly: `web3.binance.com:443` (larp-runtime, larp-execution); the runtime's `balance_rpc_url` host `:443` (larp-runtime); the execution `rpc_url` host `:443` (larp-execution); `api.commonservice.io:443` (larp-uploader); `secretsmanager.<region>.amazonaws.com:443` (runtime, execution, uploader); `monitoring.<region>.amazonaws.com:443` and `s3.<region>.amazonaws.com:443` (larp-archive); `database_host:5432` (runtime, execution, uploader, archive); `data.sec.gov:443`, `www.sec.gov:443` and every host named by an **enabled** source's `listing_url` or `allow` (larp-evidence). No host from a disabled source (e.g. `www.ftc.gov`). All expected REACHABLE. The Web3, ai-seeds and SEC hosts equal the hosts of the constants the clients use (`larp.marketdata.web3.BASE`, `larp.audit.delivery.BASE_URL`, `larp.intelligence.edgar`). |
| R2 | **Signer destinations.** `plan('signer', …)` expects `database_host:5432` and `s3.<region>.amazonaws.com:443` REACHABLE, and `web3.binance.com`, `api.commonservice.io`, `data.sec.gov` and `secretsmanager.<region>.amazonaws.com` (all `:443`) BLOCKED. |
| R3 | **Refusals before any network call.** A configured URL that is not `https`, carries a user or password, has a fragment, has no host, or names a port other than 443 (the security group allows only 443) is refused with exit 2 and the probe is never called. A required config missing for the role (runtime, uploader, operations on `primary`; signer on `signer`) is refused the same way. A null destination value (e.g. `balance_rpc_url: null`) gives an `UNSET` result that fails the check; it is not skipped. A missing execution config is listed under `not_checked` (Gate A runs without `larp-execution`). |
| R4 | **No secrets in output.** For an RPC URL whose path and query carry a token, neither the report file nor stdout/stderr contains the path, the query or the token: destinations are host and port only. Exception text is never recorded, only a status. |
| R5 | **Probe on real local sockets.** An unresolvable `.invalid` host gives `DNS_FAILED`; a closed local port `CONNECT_FAILED`; a listener that is not TLS `TLS_FAILED`; a local TLS server whose certificate is not trusted `TLS_FAILED` (verification on); the same server with its certificate trusted `OK` (skipped if `openssl` is unavailable to make the certificate). The TCP-only database probe gets `OK` from a listener that receives zero bytes. Every byte the TLS probe sends is a TLS record (first byte `0x16`), never an HTTP request line. |
| R6 | **Verdicts and exit codes.** `primary` passes (exit 0) only when every REACHABLE destination is `OK`. `signer` passes only when its REACHABLE destinations are `OK` and every BLOCKED one is `DNS_FAILED` or `CONNECT_FAILED`; a BLOCKED destination that connects (`OK` or `TLS_FAILED`) is `UNEXPECTED_ROUTE` and exits 1. |
| R7 | **Report.** `RouteCheck.v1` JSON with role, `checked_at`, the SHA-256 of each config and of the sources file, results, `not_checked` and `passed`. `--output` refuses an existing file (exit 2, file unchanged). |
| R8 | **Shipped and documented.** `larp/runtime/routes.py` is in `larp.runtime.preflight.release_files` (so it is in the bundle and can run on a host). Every host `plan` derives from the example configs for both roles, other than the account-specific RPC, database and synthetic hosts, appears in the "Approved network destinations" section of `docs/build/architecture-deployment.md`. |

**Overall:** supported if R1–R8 pass, each test was red before the build, a mutation of the key lines is caught, and the full suite shows no new failure against the base. This closes no acceptance criterion of #32 by itself: criterion 1 needs Keegan + Isaac to approve the table, criterion 2 needs the hosted run of this check from both roles.

## Results (2026-10-16, branch `claude/issue-32-33-deploy-routes`)

Order: criteria `dd5eb08` → red tests `f7f418f` (every test red: module missing, R8 doc section missing) → build `ce75e54`.

| ID | Result | Evidence (`tests/runtime/test_routes.py`) |
|---|---|---|
| R1 | PASS | `test_r1_primary_destinations_come_from_configs_sources_and_client_constants` |
| R2 | PASS | `test_r2_signer_reaches_only_the_database_and_s3` |
| R3 | PASS | `test_r3_bad_urls_are_refused_before_any_probe` (6 URLs), `test_r3_missing_required_config_is_refused` (4 cases), `test_r3_unset_destination_fails_and_missing_execution_is_listed` |
| R4 | PASS | `test_r4_report_and_output_name_hosts_only` |
| R5 | PASS | `test_r5_dns_connect_and_non_tls_failures`, `test_r5_tcp_probe_sends_nothing`, `test_r5_tls_handshake_verifies_the_certificate` (ran; `openssl` present) |
| R6 | PASS | `test_r6_primary_passes_only_when_every_destination_is_ok`, `test_r6_signer_fails_on_any_unexpected_route` |
| R7 | PASS | `test_r7_report_shape_and_exclusive_output` |
| R8 | PASS | `test_r8_module_ships_in_the_release`, `test_r8_every_fixed_destination_is_in_the_approved_table` |

**Mutations** (each applied to the committed `larp/runtime/routes.py`, run, then restored with `git checkout`): all 5 caught.
1. A signer destination that completes TCP but fails TLS no longer counts as a route (`CONNECTED = {'OK'}`): R6 fails.
2. The RPC URL is copied into the purpose text: R4 fails.
3. Disabled sources are no longer skipped: R1, R3, R4, R6, R7 and R8 fail.
4. TLS without certificate verification (`ssl._create_unverified_context()`): R5 fails.
5. Ports other than 443 accepted: R3 fails (the `:8545` subtest).

**Full suite** (Python 3.12, PostgreSQL 16.15, database `larp_c`): base `7a8a246` **1546 passed, 7 skipped, 2147 subtests passed**; this branch at `ce75e54` **1560 passed, 7 skipped, 2162 subtests passed** (+14 tests, +15 subtests, no new failure). `git diff --check` clean.

**Verdict: supported (offline).** No AWS action, no network call to any real destination, no credential read. The checks of #32 that remain:
- **Criterion 1:** Keegan + Isaac approve or amend the destination table (decision). The account-specific `balance_rpc_url` and `rpc_url` providers are chosen and manifested by Isaac + Keith (IDEA-055).
- **Criterion 2:** run `--role primary` on the provisioned `primary` during Gate A and keep the report (Keegan + Isaac; needs Yao Zhu's spend OK for `enable_hosts`/`enable_external_https`). Run `--role signer` once the signer access route is chosen (D-DN-05, AWS_RUNBOOK step 5, team decision).
- **Criterion 3:** re-confirmed by the signer report's BLOCKED results on the real host.

#33 has no code change here. It stays blocked on the GAP-29 decoder and the Executor's fake-only gate (Isaac), C-OPEN-005, the measured profile (PR #88 plus captures, Isaac/Keith), live evidence values and terms (Yao Zhu), the DR-11 assessor decision, and the hosted Gate B and rehearsal runs.

### Criterion 1: section B approval (2026-10-16)

Keegan (section B) approves the "Approved network destinations" table in `docs/build/architecture-deployment.md` as proposed, and the table's status line now says so. Isaac's approval for section C is still needed. Criteria 2 and 3, the route checker on the real hosts at Gate A, are unchanged.

## NC-01 — Isaac checklist task 2: section C destination review (2026-10-17, prospective)

User authorizes implementing Isaac's checklist in order, with each task on a separate branch/PR and owner decisions presented explicitly. Task 1 selection was settled in PR135 (BNB Chain primary, NodeReal backup for development balance reads); this task is separate on `codex/isaac-02-network-review-20261017`, from integration `47c8e6c`. Scope is reviewing the application destination table and preparing Isaac's section C approval decision, plus correcting a demonstrated route-check false positive. No AWS action, provider change, deployment or signer access occurs here. #32 retains Yao Zhu's real-host evidence.

Static review findings and sources:

- **NC-F1:** `routes.verdict('BLOCKED', 'DNS_FAILED')` currently returns PASS. The existing R6 fixture even expects DNS failure to prove signer isolation. A name that never resolved cannot test the network route. Unknown statuses also PASS. Correct this engineering result before recommending the table; do not call synthetic/local checks a hosted isolation proof.
- **NC-F2:** table says the S3 destination is the regional hostname only, while S3 supports bucket virtual-hosted names; `S3Archive` supplies `Bucket` to the SDK. The route checker currently checks only the regional canary and cannot establish the actual bucket/API route or write-once archive behavior. Document approved configured-bucket naming and this coverage limit; actual artifact/anchor operations and their recorded ACKs remain hosted gates. Primary source checked: [AWS S3 virtual hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html).
- **NC-F3:** primary's security group grants public TCP443, not per-unit domain filtering. The application table is a release/config policy, not a Terraform FQDN firewall or per-process identity boundary. The signer's network restriction is defined separately by its private route table, RDS security-group reference and S3 gateway prefix list (`deploy/aws/network.tf`). Record that actual applied-network evidence and systemd/DB-IAM/TLS checks remain required. Primary sources: [AWS security-group destinations](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html) and [prefix-list references](https://docs.aws.amazon.com/vpc/latest/userguide/managed-prefix-lists-referencing.html).
- Fixed Web3, audit and SEC destinations match client constants; enabled-source hosts come from the release register. Runtime balance RPC and execution RPC are separately manifested; model hosts remain limited to the already approved shadow trial. The signer has no approved Web3/model/audit/Secrets Manager destination. Development SSM/bootstrapping is separate from this application table. No extra external service or port is proposed.

Prospective criteria, before covered-code/test execution:

- **NC1:** a new regression must fail on the unchanged source: DNS failure for any expected-blocked signer host produces INCONCLUSIVE, `passed=false`, CLI exit1; unknown statuses fail, while a TCP/TLS connection remains UNEXPECTED_ROUTE. A resolved connect failure retains the existing sampled-check PASS.
- **NC2:** repair only the verdict mapping and the old positive fixture. Preserve host derivation, protocol behavior, no-credential/no-HTTP probes, schema and output privacy. Unknown/DNS states cannot create a PASS.
- **NC3:** document the corrected non-pass result, configured-bucket S3 naming and regional-canary limit, Gate A's optional absent execution config, and the distinct host/app/IAM/TLS enforcement checks. Do not label Isaac approved before their decision; no whole #32/GAP closes.
- **NC4:** after pushing criteria/test source, run the new regression RED before repair; after a separate pushed repair, run route tests and related host/security/config tests feasible here. Account for skipped host/DB tests. Record exact SHAs, result counts and the concrete recommended approval scope. No real destination, AWS, credential, wallet or official receiver is contacted.

### NC-01 RED (2026-10-17)

At pushed `62ef585`, `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.runtime.test_routes.Cli.test_nc1_dns_failure_never_proves_signer_isolation -v` fails as expected: actual PASS versus required INCONCLUSIVE for `DNS_FAILED`. This reproduces NC-F1 on unchanged production code. The regression also checks unknown states and the complete CLI/report boundary after repair; its first assertion currently stops it. No network or credentials used.

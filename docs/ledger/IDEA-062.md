# IDEA-062 — Approved network destinations and a read-only route check per host role (#32 slice)

- Date / owner: 2026-10-16 SGT / Claude Code at the user's request. Reviewers to approve the destination list: Keegan + Isaac (the owners #32 names).
- Status: open (criteria pre-registered; nothing built yet)
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

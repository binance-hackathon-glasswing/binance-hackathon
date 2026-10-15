# IDEA-057 — Gate A configuration assembly and startup qualification

- Date / owner: 2026-10-16 SGT / Keegan with Codex.
- Status: open; prospective criteria only, tests NOT RUN.
- Request: work on remaining readiness tasks and remove Gate A functional blockers. The user is concurrently building the quote-cost summary / live strategy profile tool; do not duplicate or modify that work.
- Base: current main `e410e49` (PR81), fetched 2026-10-16. The earlier assessment used stale local `c829fae`; its missing-driver/activation/calendar findings are superseded by IDEA-050/054 and the review merges. No hosted state is inferred from Git.
- Scope: assemble and validate a strictly unsigned dev-shadow deployment from measured, pinned inputs, supply missing input producers where possible, and verify the production composition with synthetic external transports and disposable PostgreSQL. Never fabricate measured costs, balances, exchange identities, terms captures or hosted acceptance. Preserve signed/live refusals and all gates.
- Dependencies: the user owns QuoteCostSummary/profile generation; team owns SEC contact, approval of operational parameters, AWS-connected deployment, and real measurements. AWS spending follows AWS_RUNBOOK; no host starts or wallet transaction is implied by this coding work.

## Prospective acceptance (before implementation or execution)

| ID | Pass criterion |
|---|---|
| GA01 | A shadow preparation path consumes explicit infrastructure, reviewed LIVE profile, initial state and public token metadata, pins exact bytes and validates all five issuer IDs separately from their observed underlying tickers. Wrong/missing/duplicate contracts, tickers or scales refuse; no unverified share ratio becomes verified. |
| GA02 | It emits only a dev-shadow runtime (no signing), uploader/operations configuration and the pinned input files into ignored deployment storage; names all missing prerequisites; refuses overwrite, fixture profiles, wrong wallet/run, invalid state and incompatible inputs. No secrets are read or printed. |
| GA03 | Operational shadow settings are explicit and scoped to unsigned development only. Signed/final settings remain gated. No silent development-mode fallback in a live/signed run. The user's settings answer is recorded before enabling proposed values. |
| GA04 | A pushed-code read-only input capture can supply public token metadata and the wallet's actual balances without signing, sending transactions or uploading round logs. Artifacts remain outside tracked files; unknown/unrepresentable holdings and malformed responses refuse initialization. Provenance and hashes accompany the state. |
| GA05 | Qualification checks identify configuration/manifest/input/startup blockers without starting services, fetching secrets or authorizing a run. Host-only checks (receiver ACK, routes, IAM/TLS, time, restart, alarms, anchoring, 24h ingest) remain separately NOT RUN until evidenced. |
| GA06 | Exercise the assembled runtime through init/activate, real build_driver, one unsigned round, settlement/round log and restart/replay where local PostgreSQL is available; synthetic transports and credentials only. Negative tests prove service/live execution cannot use shadow-only settings. |
| GA07 | Run focused regressions and the full feasible suite from committed/pushed code. Record exact SHA, environment, skips, failures and remaining host/Gate B work. Update ledger/backlog/runbooks without closing partially complete GAPs. |

## Findings and results

- 2026-10-16 user decision: use existing bounded evidence defaults explicitly for unsigned dev-shadow operation, 15-minute cadence and 5-minute UTC day-roll window. Deployment will use Yao Zhu's AWS environment. SEC contact not supplied; it remains a required host input. Signed/final parameters stay unadopted. Implementation uses a separate `shadow` evidence mode, never fills the pending `live` values.

- 2026-10-16: `git fetch origin` succeeded after sandbox elevation; branch `codex/gate-a-readiness-20261016` starts at current main. The current tree already contains the driver and `init`/`activate`; Gate A's active blockers are deployment inputs and host evidence. Python 3.14 is on PATH; Linux/PostgreSQL availability still to be checked. No application code or tests run in this session yet.

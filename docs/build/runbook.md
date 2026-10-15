# LARP runbook (draft) — start, restart, HALT, restore, version, final-wallet switch

Draft for the activation pack (DR-22; [IDEA-042](../ledger/IDEA-042.md) T2). Each step names the code that does it and the test that shows it. Steps marked **host** still need their drill on the provisioned environment (Gates A–C in [DEPLOYMENT_BUILD.md](DEPLOYMENT_BUILD.md)).

**During the scored run nobody acts on the agent** (F-114, F-117, never-do #1). Restart, HALT, clearing and quarantine below are all automatic. People only watch alarms, record what they see, and act before activation or after the run.

## 1. Start (before anything trades)

1. **Release check:** `python -m larp.runtime.preflight --manifest /etc/larp/release.json --root /opt/larp/current`. The manifest is built in CI with the host bundle (`release-manifest.json` in the bundle, `larp-<build>-x86_64.release.json` in the CI artifact) and never on a host; a host only verifies and binds it once, with its registration evidence and config hashes: `python -m larp.runtime.preflight --bind /opt/larp/current/release-manifest.json --root /opt/larp/current --output /etc/larp/release.json --registration-evidence <file> --runtime-config /etc/larp/runtime.json --service-config NAME=/etc/larp/NAME.json` (#62 item 3, [IDEA-049-D](../ledger/IDEA-049-D.md) WR-D3). It refuses a file not in the manifest, a changed services list or deviations register, and missing registration evidence (`larp/runtime/preflight.py`; tests `tests/runtime/test_operations.py`, `tests/runtime/test_release_register.py`).
2. **Version event:** `Coordinator.register_version(manifest, now)` commits `VERSION_REGISTERED`. A coordinator with `require_version=True` commits no execution command before it (`tests/runtime/test_release_register.py`).
3. **Live-start checks:** in `dev`/`live` mode, `larp.runtime.service run` refuses to open a session when:
   - a port is a fake;
   - a runtime secret is missing;
   - a wallet key or the audit secret is on the runtime host;
   - the addresses disagree;
   - a record directory belongs to another wallet.

   It exits 4 with the reason and never a secret value (`larp/runtime/live.py`; `tests/runtime/test_live_start.py`). systemd does not restart it.

   **Secrets (IDEA-042 S1–S4):** in `dev` and `live` the service reads one AWS Secrets Manager entry, named by `runtime_secret_id` (and `region`) in `/etc/larp/runtime.json`. It never reads the process environment.
   - The entry is `<name>/runtime`, readable only by the primary and standby hosts.
   - It is a JSON object with `AI_SEEDS_ADDRESS`, `BINANCE_API_KEY` and `BINANCE_SECRET_KEY`, and nothing else for this host.
   - The audit secret `AI_SEEDS_SECRET` belongs in `<name>/uploader` (for example `larp-dev/uploader`; the uploader's `uploader_secret_id`). Either it or a wallet key in the runtime entry refuses the start.
   - The wallet key is **not** in Secrets Manager. It is a root-only file, `/etc/larp/signer/wallet.key` (`0600`), on the signer host's encrypted disk, which systemd hands to `larp-signer` with `LoadCredential` (IDEA-046 B2; `deploy/aws/hosts.tf`, `larp/signer/keyfile.py`). Terraform creates no `signer` secret.
   - Values are put in by the team, never through Terraform or Git.
4. **Process session:** one durable session per process (`larp/runtime/supervision.py` `Sessions`).

5. **Round driver ([IDEA-048](../ledger/IDEA-048.md), completed in [IDEA-050](../ledger/IDEA-050.md)):** the `driver` block of `/etc/larp/runtime.json` (example: `config/runtime/runtime.example.json`) names:
   - the strategy profile and session calendar files, each with its SHA-256;
   - the evidence root (`evidence.sqlite` and `artifacts/`, written by the separate ingestion process `python -m larp.sources.live run`; the runtime opens it read-only);
   - the market artifact directory (under `/var/lib/larp-runtime`), the intelligence configuration mode and the cadence;
   - `issuers` (issuer ID → token and the market's `underlying_id`);
   - `execution`: `"shadow"` (every planned order ends `NOT_SUBMITTED`, reason `SHADOW_NO_SIGNING`) or `"service"` (committed commands go to the execution service), with `expiry_grace_ms` for service;
   - optionally `day_roll_window_ms` (daily risk anchor), `max_quote_rounds` and `max_quote_requests` (quote follow-up);
   - `balance_rpc_url` (HTTPS), `balance_rpc_source_id`, `balance_check_interval_ms` and `balance_check_max_age_ms` for the chain-balance check ([IDEA-055](../ledger/IDEA-055.md), #36); required in `dev` and `live`, so a start without them exits 4;
   - `assessor: "deterministic"`; a hosted model assessor exits 2 (not integrated).

   `cycle_timeout_seconds` (top level of `runtime.json`, required in `dev` and `live`; example 600 s) is the watchdog: a cycle that runs longer ends the process for a supervised restart of the same build ([IDEA-049-D](../ledger/IDEA-049-D.md) D-FND-004, #35).

   Each cycle: journal the execution service's observations and end commands that expired unclaimed (`COMMAND_EXPIRED_UNCLAIMED`); close finished rounds; **commit nothing while a command still waits for the execution service to claim it**; when nothing is in flight and a check is due, read the wallet's balances at a finalized block and compare them with the ledger (a deficit blocks new spending and caps that asset's sales at the chain units; a surplus is only recorded; the ledger is never rewritten; until this process's first good check, no new risk); roll the daily anchor in the first `day_roll_window_ms` after UTC midnight (no roll means no new risk that day); then run at most one round (a scheduled review job first, then an ingested filing, otherwise one cadence round per slot), fetching the market before the round so its decision time follows the data. A round that asked for quotes gets at most `max_quote_rounds` follow-up rounds, only when an executable quote comes back. A missing or mismatched file, hash, issuer or setting exits 4. systemd restarts neither 2 nor 4. Round logs are uploaded by the uploader process, not by the runtime.

6. **Run activation (operator, before the scored run and after any restore; IDEA-050):**
   - `python -m larp.runtime.service init --config /etc/larp/runtime.json --manifest /etc/larp/release.json --root /opt/larp/current` creates the configured `dev`/`live` run, quarantined, from `initial_state_file` (a `PortfolioState.v1` pinned by `initial_state_sha256`: the wallet's attested starting balances). It refuses an existing run or a wallet that already has one.
   - `python -m larp.runtime.service activate … --reviewer NAME --review-ref REF` is the reviewed step that authorizes the run: it verifies the full journal and the release, refuses if a round is open or an execution record is unfinished, lifts the quarantine under a new epoch, registers the running build if none is registered (another registered build is refused), and journals `RUN_ACTIVATED` with the reviewer and reference. Start `larp-runtime` and `larp-execution` only after it.

7. **Execution service (`larp-execution`, IDEA-050):** each cycle it claims current commands, advances every execution and writes its facts to `execution_observations`; the runtime journals them. Its guard facts come from the journal at every step, so a HALT stops the next signature of an execution already under way, while reconciliation of a possible send continues. Today `run` exits 2 `NOT_INTEGRATED` with reason `EXECUTOR_CAPABILITY_GATE`: the W04 Executor accepts only fake capability bundles until the verified router decoder exists (GAP-29, Isaac). The broadcast path is `FencedRelease`: it re-checks the durable possible-send record, then submits through the Web3 Open API `broadcast-transaction` endpoint with its own submit-only authenticated client (F-104; PR #66 R1).

## 2. Automatic restart (C5) — **host** drill at Gate A

- Unit: `deploy/systemd/larp-runtime.service`: `Restart=always`, `RestartSec=10`, no start limit, preflight before every start, `KillMode=control-group`.
- A crash leaves the session open, so the next start commits one `INCIDENT` (RESTART) journal event naming the crashed session. The restart runs the same build: another build is refused.
- Exit codes 2 (not integrated), 3 (quarantined) and 4 (start refused: live-start checks, configuration, release, another build or a reused session) are not restarted, because restarting cures none of them. A failure inside a round still exits 1 and restarts.
- Tests: `tests/runtime/test_supervision.py` (H1, H2).
- **Host drill:** `systemctl kill -s SIGKILL larp-runtime`. Expect the unit back within about 10 s and one RESTART incident in the journal.

## 3. HALT and its automatic clearing — **host** drill at Gate B

| Trigger | Effect | Clears |
|---|---|---|
| Decision clock behind the last committed decision | HALT `CLOCK` | Never during the run (latched) |
| A round log past its upload deadline (next UTC midnight + 2 h) | HALT `DELIVERY_DEADLINE` | Automatically, once nothing is overdue |
| N consecutive failed rounds (planner, plan, commit, policy, context, audit content) | HALT `REPEATED_FAILURES` | Automatically, after the configured number of successful **probe** rounds (below) |
| Journal fails verification | Run **quarantined** (every write and signature fenced) | Not during the run |

While halted:
- every round still runs and is logged (`HALTED:<reasons>`, no orders);
- if the only reason is `REPEATED_FAILURES`, the round probes policy and planner and discards the plan: a probe failure keeps the HALT, a probe success counts towards clearing it. A round blocked for any other reason does not count either way;
- no command is committed;
- `store.command()` refuses every signature, mandatory exits included.

Every HALT and clear is a journal event. Tests: `tests/runtime/test_supervision.py` (H3–H6).

**Host drill:** set the guard's clock input behind the last decision on the rehearsal build. Expect `HALT:CLOCK`, rounds still logged, and the signer receiving nothing.

## 4. Restore — **host** drill at Gate B

1. `python -m larp.runtime.operations restore --config /etc/larp/operations.json --receipt <pinned backup receipt> --target-dsn-file <empty database DSN>` restores into an empty, migrated database. It verifies the backup checksum and every run's journal, and leaves every run **quarantined** with a new epoch.
2. Verify against the hourly anchors read back from the Object Lock archive: `larp.runtime.maintenance.verify_anchors(store, run_id, anchors)`.
   - A restore behind the latest anchor is refused as stale.
   - A rewritten journal is refused.
3. A quarantined run accepts no session, round or signature until a reviewed takeover before the run. During the scored run a quarantine stays: it means the agent has stopped trading.

Backups include the journal, outboxes, process sessions and the execution store. Tests: `tests/runtime/test_maintenance.py`, `tests/runtime/test_anchors_roles.py` (A1–A3).

## 5. Final-wallet switch (Oct 27–29; GAP-52, C7) — **host** rehearsal at Gate C

1. **By Oct 26:** confirm the final wallet's new `AI_SEEDS_SECRET` (C7). Place the final secrets in Secrets Manager, each in its own entry: runtime (`AI_SEEDS_ADDRESS`, Binance keys) and uploader (`AI_SEEDS_ADDRESS`, `AI_SEEDS_SECRET`). The final wallet key is not a Secrets Manager entry: replace `/etc/larp/signer/wallet.key` (root, `0600`) on the signer host and set the final `wallet_address` in `/etc/larp/signer.json`.
2. **Old run:** after the development run's last round, it must have no open round, reservation or pending command, and hold no token.
3. **Switch:** `larp.runtime.live.switch_wallet(...)` opens a fresh run for the final wallet with its own `.ai-seeds/` and nonce directories, marked for that wallet. The new run starts quarantined. The switch record (old run, final head, new run) goes into the activation pack.
4. **New run:** register the version for the final build (step 1.2) and start. The live-start checks refuse any address mismatch.

Tests: `tests/runtime/test_live_start.py` (W1–W4, including a throwaway-configuration rehearsal).

## 6. Owed by the team

- **On-call rota (GAP-37):** names, hours (SGT), backup cover, and what each person watches (alarms, daily delivery, anchors). Due Oct 20.
- **Alarm recipients and AWS inputs (B9):** due Oct 14.
- **This runbook's host drills:** results go into IDEA-042, with each owner's sign-off at Gate C.

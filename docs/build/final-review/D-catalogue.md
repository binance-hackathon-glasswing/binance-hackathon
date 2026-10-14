# Final review D: requirements catalogue (accountability and operations)

IDEA-049 section D. Reviewer: Yao Zhu, with Claude. Record: [`docs/ledger/IDEA-049-D.md`](../../ledger/IDEA-049-D.md).

## 1. Basis

- **Base:** `codex/system-testing-20261012` at `c1b6daf` (merge of PR #66, round driver). Branch `review/final-d-20261014`.
- **Method:** phase 1 of [the protocol](00-common-protocol.md). Written from the requirement sources only: `docs/official/source_page.md`; `docs/official/kit/` (Guide PDF pp. 1–3 and 12–18 read in full, `PROTOCOL.md`, `logging.md`, `ai-seeds-sdk-README.md`, `README.md`); the vendored SDK (`vendor/ai-seeds-sdk-0.3.0/`: wheel unpacked to a scratch directory and `client.py`/`wire.py` read, `manual_push.sh`); SKILL.md F/K/G/Q items; `docs/proposal/proposal_answers.md`; and the decision records listed in protocol §1.1 and D's scope inventory (plan.md declared values, §6.5, D-05, G-40..G-47; IDEA-035 §1–§4, §7–§10.1; IDEA-036; IDEA-042 design criteria; IDEA-045; IDEA-046; IDEA-047 scope, design and R1–R7; DEPLOYMENT_BUILD.md gates and DR list; IDEA-021 AT01–AT20; the GAP lines in D's inventory).
- **Not opened in phase 1:** `larp/`, `tests/`, `tools/`, `deploy/` (except `compose.test.yml` and `requirements-test.lock` to set up the environment), `migrations/`, other ledger entries, build prompts, other sections' records and catalogues, the prior-issue inventory and tracker #22.
- **Local checks run for §1.2:** both PROTOCOL §2 test vectors reproduced with Python `hmac`/`hashlib` (realtime signature `451191a2…ac27`, file signature `997222a8…3fc` — match); vendored wheel and `manual_push.sh` SHA-256 match their reference hashes.
- **Labels:** sources use the protocol's labels (`RULE-PAGE`, `RULE-KIT`, `ORGANISER`, `DECLARED`, `DECIDED`). Guardrails are cited with their own tag. "Owned by X" means another section owns that aspect.
- **Split ownership:** D owns the recording, delivery, versioning and operating aspects. Content of decision records (evidence, policy, risk, execution facts) belongs to A/B/C; D owns the container, ordering, durability and delivery.
- Amendments after the freeze are appended as dated rows in §9 with a reason; frozen rows are never edited silently.


## 2. Requirements (frozen 2026-10-14)

| ID | Statement | Source | Obligation | Acceptance | Use cases | Offline-testable? |
|---|---|---|---|---|---|---|
| D-REQ-001 | When a decision round starts, the system must produce exactly one ai-seeds round log (one logical event) for it, including hold-only rounds with `orders=[]`. | RULE-KIT Guide p.13 / PROTOCOL §1: "A round is one complete agent run ... Log once per round."; Guide p.3 "including rounds that only hold (orders=[])" | MUST | Per round ID, exactly one durable round-log event exists; a hold round's event has `orders: []`. Observed with real PostgreSQL and a fake receiver. | D-UC-001, D-UC-034, D-UC-067, D-UC-069 | yes |
| D-REQ-002 | When a round ends without broadcasting an order it decided (quote failure, risk block, abort, timeout, HALT), the system must still log the round, listing that order without `tx_hash`. | RULE-KIT Guide p.13: "Orders that were never broadcast (the order failed, or risk controls blocked it) still go in orders, just without tx_hash." | MUST | Inject a failure before broadcast at each step; the round's single log lists the order without `tx_hash`; the reason is in `output` (F-106 (b) convention). | D-UC-002, D-UC-034, D-UC-069 | yes |
| D-REQ-003 | When a swap transaction has been broadcast, its `tx_hash` must appear in the `orders` of the round log of the round that decided it, whether it succeeded, reverted or is unconfirmed. | RULE-KIT Guide p.13: "required once the swap has been broadcast, whether it then succeeds, reverts or is still unconfirmed"; F-99, never-do #12 | MUST | For every broadcast swap in a fault-injected run (success, revert, timeout, crash after broadcast), one round log carries its hash; no swap hash is missing. | D-UC-003, D-UC-004, D-UC-006, D-UC-056 | yes |
| D-REQ-004 | The system must never put an approve transaction's hash, or an approval, into round-log `orders`. | RULE-KIT Guide p.3: "Approvals are not orders: never log an approve transaction." | MUST | A round with approve + swap logs only the swap hash; no order entry carries the approve hash. | D-UC-056 | yes |
| D-REQ-005 | Every round log must satisfy PROTOCOL §1: non-empty `input`/`cot`/`output`; `orders` a list; `side` `BUY`/`SELL`; `amount` USDT spent (buy) or tokens sold (sell); `tx_hash` `^0x[0-9a-fA-F]{64}$` when present; integer-ms `timestamp`. | RULE-KIT PROTOCOL §1 field table; Guide p.13 | MUST | A validator implementing PROTOCOL §1/§6 accepts every log the system builds across all round kinds; the official file test vector reproduces. | D-UC-001, D-UC-002 | yes |
| D-REQ-006 | A round log's `input` must contain everything given to the agent that round (system prompt, tool definitions, market and position context; for a model round the full model request). | RULE-KIT PROTOCOL §1: "Everything given to the agent this round, e.g. system prompt, tool definitions, market and position context" | MUST | For a model round, `input` contains the recorded model request(s) and tool definitions; for a deterministic round, the policy input/context. Byte-compare with the journal record. | D-UC-050, D-UC-059 | yes |
| D-REQ-007 | A round log's `cot` must hold the reasoning of every model call in order; when no model ran it must be a non-empty plain statement of the deterministic path, never presented as model reasoning. | RULE-KIT PROTOCOL §1 `data.cot`; ORGANISER-example F-106 (a) (convention); Q-36 answered by example | MUST (non-empty, ordered) / SHOULD (convention wording) | Model round: `cot` equals the ordered reasoning summaries; deterministic round: `cot` non-empty and states no model call. | D-UC-001, D-UC-059, D-UC-069 | yes |
| D-REQ-008 | A round log's `orders` must list what the code finally decided to place after risk checks (not the model's raw output). | RULE-KIT Guide p.13: "The orders your code finally decided to place this round (after risk checks ... not necessarily what the model output)" | MUST | A round whose proposal is cut by risk logs the post-risk orders only. | D-UC-002 | yes |
| D-REQ-009 | Round-log `orders[].symbol` must be one of NVDAB, GOOGLB, SKHYB, TSLAB, MSFTB, except `BNB` as the single BUY of a gas top-up round. | RULE-KIT F-110/K11 (server does not check symbols; our job); DECIDED IDEA-035 B11 (2026-10-11, Keegan + SYZ) | MUST | Building or verifying a log with any other symbol, or BNB outside a gas top-up round, is refused before it is committed. | D-UC-006 | yes |
| D-REQ-010 | Every round log must carry the round ID, the decision ID(s) and the registered `version_id`, so a `tx_hash` joins its round log, decision record and version. | RULE-PAGE F-34 (one version, one unique decision record); G-04 [RULE: F-34]: "each ai-seeds log carries our decision_id(s) and version_id inside input/output" | MUST | For every logged swap, `tx_hash` → round log → decision ID → decision record → version ID resolves uniquely in the journal. | D-UC-033 | yes |
| D-REQ-011 | Every resend of a round log must reuse its original event ID and identical bytes (chunks), including after a crash between send and acknowledgement. | RULE-KIT PROTOCOL §1: "every resend must reuse the same event ID"; DECIDED DR-07 | MUST | Crash after receiver STORED and before the local ACK; restart resends the same event ID and bytes; the receiver holds one logical event. | D-UC-010 | yes |
| D-REQ-012 | A round log must count as delivered only when every chunk has a durably stored receiver acknowledgement; a normal return, an empty spool or an empty outbox is never delivery proof. | RULE-KIT Guide p.14: "A normal return from log() does not mean the log was delivered"; DECIDED DR-07 ("delivery proven only by a durable per-event/chunk acknowledgement") | MUST | Delivery status lists an event DELIVERED only with ACK rows for all its chunks; lost ACK → not delivered. | D-UC-010 | yes |
| D-REQ-013 | On a transient upload failure (network error, timeout, 429, 5xx incl. 503 WRITE_UNCONFIRMED) the system must keep retrying the same event and chunk, with backoff and no attempt cap, until acknowledged. | RULE-KIT PROTOCOL §3/§5: "Retry only on network errors, 5xx and 429, reusing the same eventId and chunkIndex"; DECIDED IDEA-047 R1 | MUST | 20+ consecutive transient failures followed by a healthy receiver end with ACK; backoff grows and is capped. | D-UC-007, D-UC-008, D-UC-030 | yes |
| D-REQ-014 | On a non-transient upload rejection the system must keep the event visible as undelivered, must not resend identical bytes in a tight loop, and must deliver it autonomously once the cause clears (clock back in sync, credential registered). | RULE-KIT PROTOCOL §5 (client actions per code); ORGANISER F-114 (no human action); RULE-PAGE F-62 "Buffer locally during outages and upload within the published grace window" | MUST | 401 TIMESTAMP_SKEW then clock fixed → same event ACKed without a person; 401 INVALID_SIGNATURE/CREDENTIAL stays FAILED-visible and is retried at a bounded slow cadence; nothing disappears. | D-UC-011, D-UC-053 | yes |
| D-REQ-015 | Before a round log is committed for delivery, the system must validate it against PROTOCOL §1/§6 so that a 400 VALIDATION_FAILED or 413 PAYLOAD_TOO_LARGE cannot occur for a log the system built. | RULE-KIT PROTOCOL §6: "The SDK checks the same rules before sending"; §5 400/413 "Fix it and send again; do not retry" | MUST | Property test: every built log passes a local PROTOCOL validator; each chunk's stored record stays ≤ 256 KB after JSON escaping. | D-UC-009 | yes |
| D-REQ-016 | When a round's log would exceed 128 chunks of 65,536 bytes, the system must still close the round with exactly one valid log (bounded fallback referencing the full record's hash) and commit no command for it. | RULE-KIT PROTOCOL §3/§6 (≤ 128 chunks); DECIDED DR-07 (size limits), IDEA-042 L6 | MUST | A synthetic oversized model I/O round produces one valid fallback log ≤ limit and no execution command. | D-UC-009 | yes |
| D-REQ-017 | Uploads must follow PROTOCOL §2–§3: signed string as specified, fresh timestamp and nonce per attempt, chunking on character boundaries with constant `chunkCount`/`totalBytes`/`contentSha256`. | RULE-KIT PROTOCOL §2 ("every implementation must pass these" test vectors), §3 | MUST | Both official test vectors reproduce; multi-byte text split into chunks reassembles exactly; each retry carries a new nonce and timestamp. | D-UC-010 | yes |
| D-REQ-018 | Every round log for UTC day D must be acknowledged before 02:00 UTC on D+1 whenever the receiver is reachable; a breach must be recorded as an incident (never backdated) and delivery must continue. | RULE-KIT Guide p.3: "a day's logs must arrive before 02:00 UTC the next day. If they arrive later, the related fills are first flagged" (stated under batch mode; conservative reading for all modes, D-CON-02) | MUST | With a receiver outage 23:00–01:30 UTC all D logs ACK before 02:00; with an outage to 03:00 the breach is journaled with its real time and logs ACK after recovery. | D-UC-007, D-UC-008, D-UC-040 | yes |
| D-REQ-019 | A round log's bytes and timestamp must never be changed or backdated after creation; a round logged on restart must say it was recovered and when. | RULE-PAGE F-62: "No end-of-event backfilling."; never-do #9; G-19 [RULE-DERIVED] | MUST | Event bytes are immutable in storage (update refused); a recovered round's log has the recovery time and a recovery marker in `output`. | D-UC-007 | yes |
| D-REQ-020 | When a process dies mid-round, the interrupted round must be closed and logged on restart before any new round starts. | G-19 [RULE-DERIVED: F-99, F-100]: "If the process dies mid-round, the round is logged on restart ..., before any new round" | MUST | Crash at each durable step; on restart exactly one log for the interrupted round precedes the next round's log. | D-UC-004, D-UC-005, D-UC-013 | yes |
| D-REQ-021 | No code may run with the registered wallet's ai-seeds credentials unless it is committed, pushed and manifested. | RULE-KIT Guide p.3 "Demo and example runs upload real logs under your wallet"; never-do #13; F-103 | MUST | The uploader refuses to start without a verified release manifest and config hash. | D-UC-038 | yes |
| D-REQ-022 | Round logs from development and rehearsal runs should carry the kit's test marker (`"example": true` in `input`), and never carry placeholder `tx_hash` values. | ORGANISER-example F-106 (c); Q-37 answered in practice; GAP-48 | SHOULD | A dev/rehearsal coordinator adds the marker; a live coordinator does not; no placeholder hash passes validation. | D-UC-039 | yes |
| D-REQ-023 | Credentials (wallet key/mnemonic, Web3 API secret, `AI_SEEDS_SECRET`, database passwords/tokens) must never appear in round logs, the journal, process logs, error texts, reprs, manifests, metrics, backups or anchors. | RULE-PAGE F-62: "Credentials never appear in logs."; RULE-KIT Guide p.3; never-do #7 | MUST | Marker-secret tests across every service's output paths, error paths, manifests, metrics and backup/anchor payloads find no marker. | D-UC-035 | yes |
| D-REQ-024 | Each registered wallet must have its own `AI_SEEDS_SECRET`, its own upload outbox/data directory and nonce records; a directory or secret belonging to another wallet must be refused. | RULE-KIT F-101/Guide p.13 "do not share this directory between processes"; G-09 [RULE-DERIVED]; DECIDED DR-17 | MUST | Start with a data directory marked for another wallet, or with `AI_SEEDS_ADDRESS` ≠ configured wallet ≠ run wallet, is refused. | D-UC-024, D-UC-036 | yes |
| D-REQ-025 | Before any new swap is signed, the round record that will carry its `tx_hash` must be durable, and new swaps must not be signed while round-log delivery is overdue beyond the configured bound. | never-do #12: "Never broadcast a swap whose tx_hash will not reach an ai-seeds round log"; F-100 | MUST | With delivery overdue (receiver down past the bound) the signing gate refuses; it allows again after ACK. | D-UC-007, D-UC-008, D-UC-053 | yes |
| D-REQ-026 | Every day the system must check that each broadcast swap of the previous UTC day has its `tx_hash` in an acknowledged round log, and raise an incident and degraded mode on any gap. | RULE-KIT Guide p.18 "Every day, all fills from the previous day are checked"; G-43 [RULE-DERIVED] kit addition | MUST | A swap with no ACKed log is reported by the daily check and journaled as an incident. | D-UC-040, D-UC-041 | yes |
| D-REQ-030 | Every transaction the agent broadcasts (trades, approvals, gas top-ups, failed transactions) must map to exactly one registered version and one unique write-ahead decision record. | RULE-PAGE F-34, F-48 "no unmapped trades", F-60; never-do #2; G-04 [RULE: F-34] | MUST | For every signature in a fault-injected run, the journal has one decision record and the registered version; no signature without both. | D-UC-003, D-UC-005, D-UC-006, D-UC-056, D-UC-066 | yes |
| D-REQ-031 | The decision record for an order must be durable before its payload is signed. | DECLARED Proposal p.1: "Every trade is written as a decision record before signing"; Reproducibility: "Decision records, written before signing" | MUST | Crash between record and signature leaves the record and no signature; the signer refuses a request without a committed record. | D-UC-005, D-UC-027, D-UC-029, D-UC-056 | yes |
| D-REQ-032 | Decision records must hold: input hashes and pointers with source and retrieval times; evidence-step tool calls/results and full model requests/responses incl. reasoning summaries; check outcomes (claim verification, probability vector or its v1.0 replacement, selection/policy/risk); a short reason summary, the intended order and quote ID; and, appended after execution, tx hash, fill, fees and gas or an abort status. | DECLARED Reproducibility plan "Decision records, written before signing" (five bullets); G-04 | MUST (container and append-only completion owned by D; field content by A/B/C) | Schema/integration test: a settled round's record contains each field class; abort rounds carry the abort status. | D-UC-056 | yes |
| D-REQ-033 | HOLD and abstain decisions must be journaled as decisions so inactivity is traceable. | DECLARED Reproducibility: "HOLD and abstain decisions are logged too, so inactivity is traceable." | MUST | A hold round has a journal decision event and a round log. | D-UC-001, D-UC-034 | yes |
| D-REQ-034 | The journal must be append-only, sequence-numbered and hash-chained; any update, delete, gap or reorder must be detected by verification. | DECLARED Reproducibility Logs: "The journal is append-only, sequence-numbered and hash-chained."; G-07 [PRACTICE] | MUST | DB refuses UPDATE/DELETE on journal rows for service roles; verification fails on an altered, deleted or reordered event. | D-UC-017 | yes |
| D-REQ-035 | The journal (with its chain head) must be uploaded to write-once storage daily, and after any incident. | DECLARED Reproducibility Logs: "It is uploaded daily, and after any incident, to write-once storage with the chain head"; RULE-PAGE F-62 | MUST | A daily export/backup with head lands in the archive; an incident triggers an extra upload; both are verifiable. | D-UC-057, D-UC-068 | partly (host for real S3) |
| D-REQ-036 | The journal head must be anchored to write-once storage outside the database once per UTC hour; a missed slot is never backfilled and is recorded as an incident. | DECLARED "anchored hourly"; DECIDED IDEA-035 §4 GAP-35 (2026-10-11), IDEA-036 criteria 1–2 | MUST | Scheduler test across hours: one anchor per slot; a skipped slot yields an incident and no late anchor for it. | D-UC-019, D-UC-041, D-UC-058, D-UC-067 | partly (24 h cadence on host) |
| D-REQ-037 | Verification against the anchored heads must fail if any anchored journal event was altered, and a restore older than the latest anchor must be rejected as stale. | DECLARED "The hash chain shows tampering after anchoring."; DECIDED IDEA-036 criteria 3 and 5 | MUST | Alter one anchored event → verify fails; restore a pre-anchor backup → refused as stale. | D-UC-018, D-UC-046 | yes |
| D-REQ-038 | Anchor records must contain only hashes, identifiers and times — no keys, credentials or private model/evidence text. | DECIDED IDEA-036 criterion 6 | MUST | Anchor payload schema has only id/time/sequence/head/epoch fields; marker test. | D-UC-058 | yes |
| D-REQ-039 | Completeness must be checkable: reconciliation of on-chain transactions ↔ execution records ↔ decision records ↔ version events ↔ non-trade balance changes, hourly and fully once a day, with any mismatch putting the agent into degraded mode. | DECLARED Logs: "Completeness is shown separately: by reconciling every on-chain transaction, execution record, decision record and version event"; G-43 [POLICY hourly, RULE-DERIVED daily]; DECLARED Failure modes "A reconciliation mismatch puts the agent into degraded mode" | MUST (daily, degraded mode) / SHOULD (hourly) | Scheduler runs the reconciler on both cadences; an injected mismatch sets degraded mode (no new risk) and an incident. | D-UC-043 | partly |
| D-REQ-040 | The runtime must record heartbeats durably so heartbeat gaps are measurable from the journal/database. | DECLARED Logs: "by gaps in sequence numbers and heartbeats"; RULE-PAGE F-51 (heartbeat gaps as diagnostics) | MUST | Heartbeat rows advance while running; a stopped process leaves a measurable gap. | D-UC-001, D-UC-032, D-UC-044 | yes |
| D-REQ-041 | Every incident class must be journaled: outage, restart, failed tx, reconciliation mismatch, missed heartbeat, disk/database near full, clock breach, HALT/clear, quarantine, upload rejection, outbox overdue, rate-limit bursts, swap revert, confirmation timeout. | G-44 [RULE-DERIVED: F-62] incident list (over-report); RULE-PAGE F-33 "Failures and recovery ... appear as audit evidence" | MUST | Each injected condition produces exactly one incident event of its class. | D-UC-002, D-UC-003, D-UC-014, D-UC-016, D-UC-019, D-UC-026, D-UC-029, D-UC-043, D-UC-057, D-UC-065, D-UC-068, D-UC-069 | partly |
| D-REQ-042 | Complete model inputs/outputs, prompts and tool definitions, and reasoning output must be retained (journal/evidence store, backups, archive) through the winner audit and any technical review. | RULE-PAGE F-49, F-62 "make sure your logging captures it"; G-06 [RULE-DERIVED] (retention side); G-47 | MUST (retention; capture content owned by A) | Model I/O stored with the decision is included in backups/export and survives restore. | D-UC-059 | partly |
| D-REQ-050 | Every build must have a manifest whose hash covers the commit, dependency lockfiles, prompts and tool schemas, configs/risk parameters/thresholds, and model checkpoint hashes or API snapshot IDs. | DECLARED Reproducibility Versions ("Every build has a manifest hash covering ..."); G-03 [RULE-DERIVED] | MUST | Changing any covered input changes the manifest hash; the manifest lists each covered file hash. | D-UC-060 | yes |
| D-REQ-051 | The manifest must declare the third-party services (services list) and embed the deviations register, both hashed. | RULE-PAGE F-61: "Third-party services are declared in your manifest"; G-11 [RULE-DERIVED]; DECIDED IDEA-042 R1/R4 | MUST | Preflight refuses a manifest whose services list or register is missing, invalid or hash-mismatched. | D-UC-060 | yes |
| D-REQ-052 | Every component (runtime/agent, execution service, signer, uploader, evidence worker, archive/reconciler) must verify its installed release and its own config against the active registered manifest at start-up and refuse to start on any mismatch. | DECLARED: "Every component checks its hash against the active registered version before it runs: the agent, signer, uploader, tools and reconciler at start-up"; G-03 | MUST | For each service: altered file, altered config, unrecorded config or other build → start refused with a reason. | D-UC-020, D-UC-022 | yes |
| D-REQ-053 | The agent must re-verify its version against the registered version before every order (command/signature). | DECLARED: "the agent again before every order"; G-03 "Before each order" | MUST | A command or signing request after a build/manifest mismatch is refused. | D-UC-023, D-UC-049 | yes |
| D-REQ-054 | No order may be signed for a run until that run's build is registered by a version event in the journal that names the manifest. | RULE-PAGE F-60: "New versions must be committed, manifested and logged in a version event before they trade."; never-do #5 | MUST | Before VERSION_REGISTERED/activation no command is planned or signed; after it, commands carry that version. | D-UC-023, D-UC-049, D-UC-060 | yes |
| D-REQ-055 | A release must be built only from a clean commit that is on the registered remote, and a host must install it only if its hash equals the CI-built bundle hash. | RULE-PAGE F-61: "All code affecting decisions, trades or logging must be pushed to your registered repo before it runs — including code on your own remote services."; DECIDED IDEA-047 R6 | MUST | Bundle build refuses dirty/unpushed trees; provisioning refuses a missing or different expected hash before extracting. | D-UC-021, D-UC-038 | yes |
| D-REQ-056 | Dependencies must be pinned (lockfiles with versions and hashes; model snapshot IDs), and the installed set must match the lock. | G-12 [RULE-DERIVED: F-61]: "Model snapshot IDs, checkpoint hashes and dependency lockfiles pinned" | MUST | Host install uses the locked wheelhouse offline; any unpinned or hash-less dependency in a deployable lock is reported. | D-UC-060 | yes |
| D-REQ-057 | During the scored run the registered build and its configuration must not change: a start with any other build or config for the run is refused, and no release path exists that a person must operate. | ORGANISER F-114 "no changes allowed — period", F-117; G-46 [RULE-DERIVED]; DECIDED DEV-13 (2026-10-08) | MUST | Runtime start with a build ≠ the run's registered build is refused; a changed config is refused. | D-UC-022, D-UC-025, D-UC-042 | yes |
| D-REQ-058 | Every version that produced any transaction or log (development included) must stay retrievable with its manifest and commit, with no gaps in version history. | RULE-PAGE F-48 "no version gaps", F-17 (version history, commits, manifests) | MUST | Audit export lists every version event with its manifest; each journaled version ID resolves to a manifest. | D-UC-033, D-UC-049 | partly |
| D-REQ-059 | The deviations register must list every deviation from the submitted proposal with reason and evidence, be rendered unchanged into plan.md §6.5, and have no OPEN row at the final freeze. | G-11 [RULE-DERIVED: F-48, F-66]; RULE-PAGE F-66 ("false declarations"); plan.md §6.5 "Final at the Oct 26 freeze" | MUST | Register validator: verbatim quotes, evidence IDs resolve, rendered table matches; freeze check refuses OPEN rows. | D-UC-055, D-UC-060, D-UC-063 | yes |
| D-REQ-060 | Fallbacks for engineering unknowns must be recorded in the manifest (e.g. deterministic assessor, disabled capabilities). | DECLARED Onboarding gates: "Engineering unknowns: each gets a documented fallback recorded in the manifest." | MUST | Manifest/services/deviations entries name each fallback in force. | D-UC-060 | yes |
| D-REQ-061 | The challenge branch history must never be rewritten (no force-push, rebase or amend of pushed commits). | RULE-PAGE F-61: "no force-pushes, no rewrites"; never-do #6; G-40 | MUST | Procedural (AGENTS.md); release builds refuse commits not on the remote. Branch protection unavailable (G-40). | D-UC-061, D-UC-064 | process only |
| D-REQ-062 | No secret, key, credential or private training/label data may be committed; a secret scan must run on every push. | RULE-PAGE F-61: "Never commit secrets, keys or private training data."; G-41 ("CI scan on every push [TEST]") | MUST | CI job scans each push and fails on a planted secret pattern. | D-UC-061 | yes |
| D-REQ-070 | During the scored run every safety action, HALT, recovery, restart and resumption must happen autonomously from the registered build, with no human step. | ORGANISER F-114, F-117; never-do #1; G-08 [RULE: F-60, F-48] | MUST | Every recovery path in the use-case list completes in tests without operator input; runbook has no in-run human step. | D-UC-008, D-UC-025, D-UC-029, D-UC-043 | partly (host drills) |
| D-REQ-071 | After a crash, a supervisor must restart the same registered version automatically, and the restart must be journaled as an incident. | DECIDED IDEA-035 C5 (team position 2026-10-11); DR-13 | MUST | Kill the runtime: it restarts on the same build; one RESTART incident names the previous session; a different build is refused. | D-UC-004, D-UC-013, D-UC-030, D-UC-045 | partly (systemd on host) |
| D-REQ-072 | A crash loop must neither leave the agent stopped for good nor cause repeated economic actions; each restart is bounded and recorded. | DECIDED IDEA-021 AT14 ("No unlimited economic retry or restart loop"); ORGANISER F-114 | MUST | Units restart without a start limit and with a delay; repeated crashes do not duplicate any signature or command. | D-UC-014 | partly |
| D-REQ-073 | Autonomous HALT triggers must include: clock behind the last committed decision time, round-log delivery deadline breach, and N consecutive failed rounds; an integrity failure must quarantine the run. | DECIDED DEV-14 (2026-10-11): "HALT is autonomous code (clock, delivery deadline, repeated failures; integrity quarantines)"; IDEA-042 H3 + amendment | MUST | Each trigger injected → HALT (or quarantine) event with its reason. | D-UC-007, D-UC-011, D-UC-012, D-UC-014, D-UC-015, D-UC-016, D-UC-017, D-UC-069 | yes |
| D-REQ-074 | While halted, every round must still run and be logged (no orders) and no new command, reservation or signature may be created. | never-do #12 (log every round); DECIDED IDEA-042 H4 | MUST | Halted round: one log, `orders: []`, no command; pending command refused at the signing gate. | D-UC-008 | yes |
| D-REQ-075 | Every HALT must clear autonomously once its cause is gone, by a journaled clear event; nothing may require a person to clear it. | ORGANISER F-114 (zero human action); D prompt done criterion; DECIDED IDEA-042 H5 (automatic clearing only) | MUST | Delivery HALT clears after ACK; repeated-failure HALT clears after N successes; clock HALT … (see D-CON-09). | D-UC-007, D-UC-008, D-UC-011, D-UC-012, D-UC-015, D-UC-016 | yes |
| D-REQ-076 | A hung but alive process (no progress, no heartbeat) must be detected and restarted autonomously. | DECIDED IDEA-021 AT14 ("Each blocked state exposes reason, last progress, bounded next action"); RULE-PAGE F-22 (monitoring, recovery); ORGANISER F-114 | MUST | A process that stops heartbeating is killed and restarted by the supervisor (watchdog) and an incident is journaled. | D-UC-032, D-UC-044 | partly |
| D-REQ-077 | Each restart, HALT, clear, quarantine and incident must be a journal event that replays to the same head. | G-44; DECIDED IDEA-042 H6; DECLARED replay | MUST | Replay of a journal with these events reproduces the head. | D-UC-015, D-UC-057, D-UC-066 | yes |
| D-REQ-078 | Execution and reconciliation must continue to completion for already-broadcast actions after a restart, before new economic actions (recovery precedes new rounds). | G-18 (d) "Reconcile outstanding signed authorizations before creating any replacement economic action"; DECLARED Recovery | MUST (runtime ordering; mechanics owned by C) | Crash after broadcast → on restart the observation is ingested and settled before a new round commits commands. | D-UC-004, D-UC-005, D-UC-013 | yes |
| D-REQ-079 | Execution facts reported by the execution side must be journaled exactly once each, in causal order (an approval before its swap's fill), and a fact whose stored bytes no longer match its recorded hash must be refused. | DECLARED Decision records "Appended after execution: the transaction or order hash, fill, fees and gas, or an abort status"; RULE-PAGE F-34/F-48 (mapping integrity); DECLARED journal append-only | MUST (runtime ingestion; fact production owned by C) | Duplicate and reordered facts → one journal event each, causal order; a tampered fact row is refused with an incident. | D-UC-066 | yes |
| D-REQ-085 | The database must be backed up off-box daily into the write-once archive, and a restore into an empty database must verify against the anchors before use. | G-47 [PRACTICE] "off-box journal backups"; DECIDED IDEA-036 criterion 5; DR-16 (restore drill) | MUST | Backup → restore into empty DB → verify against anchors passes; restored run stays quarantined until verified. | D-UC-018, D-UC-067, D-UC-068 | partly (S3 on host) |
| D-REQ-086 | The archive (backups, anchors, exports, manifests) must be retained, undeletable, through at least 2026-12-31. | DECIDED IDEA-036 criterion 1 ("at least Dec 31, 2026"); G-47 (through Nov 20 and any technical review); IDEA-046 L05 | MUST | Terraform refuses retention shorter than the floor; Object Lock COMPLIANCE; archive outlives teardown. | D-UC-042, D-UC-052 | partly |
| D-REQ-087 | The deterministic layers must re-run on recorded inputs/model outputs and reproduce the same decisions and journal head; a changed recorded value must be detected. | DECLARED Rerun: "must reproduce the same decisions"; DECIDED IDEA-021 AT13; DR-19 | MUST | Replay of a recorded multi-round day (incl. settled swaps, HALT, incidents) into an empty store reaches the identical head; tampering changes it. | D-UC-018 | yes |
| D-REQ-088 | A full audit export (journal, round logs and ACKs, manifests, version events, model I/O, incidents) must be producible from the database/archive alone. | RULE-PAGE F-47 ("complete local logs"), F-17; DECIDED IDEA-021 AT20 ("complete audit export") | MUST | Export command over a test run yields every class of record and verifies against anchors. | D-UC-033, D-UC-042, D-UC-052, D-UC-059 | yes |
| D-REQ-089 | Disk, database and archive growth over the 14-day run (plus rehearsal) must fit the provisioned capacity with margin, and nearing capacity must raise an incident/alarm. | G-44 (disk > [80]%), G-47 (disk alerts); RULE-PAGE F-15/F-19 (14 days count) | MUST | Growth estimate from measured bytes per round × rounds/day × 18 days < capacity × 0.8; alarm exists. | D-UC-025, D-UC-026, D-UC-027 | partly |
| D-REQ-100 | Deployment must use two hosts: `primary` (coordinator, execution, evidence, uploader, archive) and `signer` (wallet key only); the signer must have no internet route. | DECIDED IDEA-046 B1, B2 (Yao Zhu, 2026-10-12) | MUST | Terraform tests: exactly two hosts; signer has no public IP/egress/internet route. | D-UC-062 | yes (mocked plans) |
| D-REQ-101 | The wallet key must exist only as a root-only file on the signer's encrypted disk, delivered to the signer service by systemd credentials; no other host or service may hold it. | DECIDED IDEA-046 B2; IDEA-047 scope (Yao Zhu, 2026-10-14) | MUST (deployment side; loader owned by C) | Unit/static tests: only the signer unit loads the credential; runtime config with a key is refused. | D-UC-037, D-UC-048 | yes |
| D-REQ-102 | Hosting must be in AWS Sydney (`ap-southeast-2`) and must never use a VPN or relay to reach any service. | DECIDED IDEA-046 B3; ORGANISER F-118 (relayed); never-do #10; G-17 [RULE: F-70, F-71] | MUST | Terraform region pinned; no VPN/proxy resources or settings. | D-UC-062 | yes |
| D-REQ-103 | Hosting cost must stay within the $100 AWS credits through the winner audit, with budget alerts at 50/75/90% of actual spend. | DECIDED IDEA-046 B4 ("The Free plan ... closes the account when they are used up, which would stop the agent mid-run") | MUST | Budget resource with three ACTUAL notifications; cost projection to Nov 20 < remaining credits with margin. | D-UC-025, D-UC-028, D-UC-051 | partly |
| D-REQ-104 | Monitoring must alarm on runtime heartbeat loss, HALT, quarantine, overdue logs, unanswered signing requests and archive health, treating missing data as breaching, and notify a real destination. | RULE-PAGE F-22 ("monitoring"); DECIDED DR-16, IDEA-047 R5 | MUST | Terraform test: alarms exist with breaching missing data when hosts run; publisher emits the metrics; alarm reaches a person (host). | D-UC-017, D-UC-026, D-UC-027, D-UC-031, D-UC-032, D-UC-065 | partly |
| D-REQ-105 | Each host must be automatically recovered by AWS on a system-status failure. | DECIDED IDEA-046 L04 | MUST | Terraform test: one recovery alarm per host. | D-UC-030, D-UC-062 | yes (mocked) |
| D-REQ-106 | The database must be private, encrypted, IAM-authenticated with per-role least privilege, and deletion-protected. | DECIDED IDEA-046 L05, IDEA-045 H01–H03, IDEA-042 G1–G2 | MUST | Terraform + roles.sql tests on real PostgreSQL: each role refused outside its grants. | D-UC-062 | yes |
| D-REQ-107 | Host provisioning must be offline from a verified bundle, idempotent, and install only the role's units with per-service users. | DECIDED IDEA-047 H02, R6 | MUST | Container test with `--network none`, run twice; wrong/missing hash refused. | D-UC-021, D-UC-062 | yes (Docker) |
| D-REQ-108 | There must be a defined, credential-safe route to apply database migrations and roles on the hosted database, and to provision the signer host, that needs no step during the scored run. | RULE-PAGE F-22 (host and operate); DECIDED DR-16 (hosting), IDEA-046 B2 (signer has no internet) | MUST | A documented, tested procedure exists; NOT-OFFLINE for the real account. | D-UC-047, D-UC-048 | only on a host |
| D-REQ-109 | Service logs (journald) of both hosts must be retained for the audit as part of the complete local logs. | RULE-PAGE F-47/F-17 ("complete local logs"); G-47 retention | MUST | Procedure + retention; signer journald collected before teardown. | D-UC-051, D-UC-052 | only on a host |
| D-REQ-110 | The deployment must be either primary plus a fenced cold standby (as declared) or a recorded, decided deviation with reason and evidence. | DECLARED Team capability: "The deployment is one primary runtime plus a fenced cold standby."; G-11; DECIDED IDEA-046 B1 (no standby host); DEV-18 OPEN | MUST | Either standby fencing tests pass or DEV-18 is decided with evidence (D-CON-03). | D-UC-045, D-UC-046 | yes |
| D-REQ-111 | Every host clock must be synchronised so the uploader stays within ±5 min of the receiver and the agent's clock checks hold; drift must stop trading. | RULE-KIT Guide p.2 ("Turn on time sync (NTP)"), F-101; DECLARED "The server clock is checked, and trading stops if it drifts." | MUST | Clock check in runtime HALTs on drift (test); NTP configured on hosts (host). | D-UC-011, D-UC-012 | partly |
| D-REQ-120 | A week-one checkpoint commit and progress note, and end-to-end self-check evidence, must exist by the end of development (Oct 26). | RULE-PAGE F-13 ("A week-one checkpoint commit and progress note; end-to-end self-check evidence") | MUST | Commit + note recorded; self-check evidence (system test reports) linked. | D-UC-054 | only live (deliverable) |
| D-REQ-121 | Recovery must be tested during development (crash/restart/HALT/restore drills). | RULE-PAGE F-13 ("test recovery"); DECLARED Oct 19–26 "recovery drills, soak and fault injection"; DR-13, DR-16 | MUST | Offline drills in CI; host drills recorded before Gate B/C. | D-UC-054 | partly |
| D-REQ-122 | At final activation the system must run from a fresh final wallet with a new run, its own secret and data directories, and the commit and manifest of the starting build must be ready to submit. | RULE-PAGE F-14; DECIDED DR-17, DR-22, IDEA-035 C7 | MUST | Wallet switch rehearsal with throwaway config; activation pack checklist. | D-UC-024, D-UC-053, D-UC-063 | partly |
| D-REQ-123 | The scored run (Oct 29 – Nov 12) must run 14 days unattended with daily trace uploads and automatic reconciliation. | RULE-PAGE F-15, F-19, F-46; ORGANISER F-114 | MUST | Accelerated multi-day soak in CI (time-warp) with no human input; resource budgets hold. | D-UC-025 | only in rehearsal/live |
| D-REQ-124 | For the winner audit the team must be able to hand over version history, commits, manifests and complete local logs, plus thinking output, prompts/tool definitions and model I/O. | RULE-PAGE F-17, F-47, F-49 | MUST | Audit export (D-REQ-088) plus archive retention (D-REQ-086). | D-UC-033 | partly |
| D-REQ-125 | The declared rehearsal (full pipeline, 5+ days including a weekend, at minimum size, signer on) must be run, or its shortfall recorded as a decided deviation. | DECLARED Plan Oct 19–26: "full pipeline for 5+ days including a weekend, at minimum size"; DECIDED DR-21; GAP-04 | MUST | Daily rehearsal log on the host, or a decided deviation (D-CON-04). | D-UC-055 | only in rehearsal |
| D-REQ-126 | Anything not working by the Oct 22 cut line must be cut and recorded as a deviation, not delayed. | DECLARED: "Anything not working by Oct 22 is cut, not delayed." | MUST | Freeze review lists cut items in the register. | D-UC-055 | process only |
| D-REQ-127 | An activation pack (frozen commit, manifest, final-wallet config with secret slot, runbook, on-call rota) must be ready by Oct 26. | DECIDED DR-22 | MUST | Checklist signed off; rota present (GAP-37). | D-UC-063 | process only |
| D-REQ-128 | The repository must stay private with read-only access for the designated Binance audit account. | RULE-PAGE F-24, F-12 | MUST | Team statement (Q-33 C6); not testable offline. | D-UC-064 | only live |
| D-REQ-135 | A compromised or buggy primary host must not be able to obtain a signature outside the signer's own allow-list checks, nor read the wallet key. | DECIDED IDEA-046 B1/B2, IDEA-047 design (signer re-checks); G-01 (owned by C) | MUST (isolation boundary; allow-list by C) | Signer refusal tests with a patched primary (C); no key path on primary (D). | D-UC-037 | yes |
| D-REQ-136 | A tampered release (file differs from manifest or bundle hash) must be refused by every service before it handles data. | G-03; DECIDED IDEA-047 R6 | MUST | Flip one byte in an installed file → preflight refuses. | D-UC-020 | yes |
| D-REQ-137 | A runtime configured with a wallet other than the run's registered wallet, or other than `AI_SEEDS_ADDRESS`, must refuse to start. | G-09 [RULE-DERIVED: F-92]; DECIDED IDEA-042 W1 | MUST | Mismatch configs refused before any session opens. | D-UC-024, D-UC-036 | yes |
| D-REQ-138 | Large or hostile content (prompt injection, oversized documents/model output) must not break round logging, the journal or delivery budgets. | DECIDED IDEA-021 AT19 ("response and storage budgets hold under worst-case input"); AT11 (oversized model I/O) | MUST | Oversized/hostile content round → one valid log, journal intact, no crash. | D-UC-009, D-UC-050 | yes |

## 3. Assumptions register

| ID | Assumption and where it is relied on | Status | Evidence | How to validate | If wrong |
|---|---|---|---|---|---|
| D-ASM-001 | The ai-seeds service is the official write-once trace storage of F-15/F-62 (D-REQ-001..018). | PARTIAL | Q-34 answered in practice (F-99 "organizers audit every on-chain fill against these logs"); no organiser statement that it is F-62's write-once storage. | Organiser question (Q-34) if the official rules do not settle it. | Our own write-once journal upload (D-REQ-035) still covers F-62; not blocking. |
| D-ASM-002 | The 02:00 UTC next-day arrival deadline applies to every round log, not only batch mode (D-REQ-018). | UNVALIDATED | Guide p.3 states it under "Batch mode:"; silent for realtime spool delivery. | Conservative reading adopted (D-CON-02); organiser question listed. | If stricter, nothing breaks; if looser, only margin is lost. Not blocking. |
| D-ASM-003 | Re-uploading a log is harmless: the receiver de-duplicates by event ID + chunk index (D-REQ-011/013). | VALIDATED | PROTOCOL §4: "Logs are de-duplicated by event ID + chunk index, so uploading again is harmless." | — | — |
| D-ASM-004 | A 200 response with `status: STORED` means the chunk was durably written; 503 WRITE_UNCONFIRMED means it may not be (D-REQ-012). | VALIDATED | PROTOCOL §3 "Success 200: {...\"status\":\"STORED\"}"; §5 503 "could not confirm the write". | — | — |
| D-ASM-005 | Each 64 KiB chunk stays ≤ 256 KB as a stored record after JSON escaping (D-REQ-015). | VALIDATED (arithmetic) | Compact JSON log text escapes control characters itself; re-escaping inside `payload` at most doubles ASCII (`"`, `\\`) and at most triples 2-byte UTF-8 under \\u escaping: 65,536 × 3 = 196,608 B + < 1 KB envelope < 262,144 B. | Phase-2 property test on worst-case text. | If wrong: 413 on large rounds → undelivered logs (P0). |
| D-ASM-006 | Hosts' clocks stay within ±5 min of the receiver (Amazon Time Sync) (D-REQ-111). | UNVALIDATED | Not measurable offline. | Host check: chrony status at Gate A; runtime clock checks. | 401 TIMESTAMP_SKEW → late logs; blocking only if no autonomous recovery (D-REQ-014). |
| D-ASM-007 | The AWS Free plan limits RDS automated backups to 1 day. | PARTIAL | IDEA-046 records a `FreeTierRestrictionError`; not re-checked here (no AWS access allowed). | Record as deployment risk; rely on daily logical backup (D-REQ-085). | RPO up to 24 h if PITR is lost; blocking for zero-loss claims. |
| D-ASM-008 | When the $100 credits are used up the Free plan closes the account, stopping the agent. | UNVALIDATED | IDEA-046 B4 team statement; AWS documentation not checked in this review. | Team reads AWS Free plan terms before Gate C; cost projection. | Agent stops mid-run (P0 operational). |
| D-ASM-009 | ≈ $62/month with hosts on keeps total spend within $100 through Nov 20. | PARTIAL | IDEA-046 estimate; actual spend since 2026-10-14 not visible offline. | Budget alerts + Cost Explorer check at Gates B/C. | Same as D-ASM-008. |
| D-ASM-010 | EC2 system-status auto-recovery keeps the instance, EBS volumes, private IP and systemd units, so services resume without a person. | UNVALIDATED | AWS behaviour, not testable offline. | Host drill or AWS doc citation (team). | If not, host failure needs a person (F-114 breach risk). |
| D-ASM-011 | An OS-level hang (instance-status failure) is also recovered automatically. | UNVALIDATED | System-status recovery does not cover instance-status checks. | Phase 2: check Terraform for an instance-status reboot alarm. | A hung host stops the agent until a person acts. |
| D-ASM-012 | RDS maintenance/minor-version upgrades will not be applied during the scored run. | UNVALIDATED | Depends on Terraform `auto_minor_version_upgrade` and maintenance window. | Phase 2 Terraform read. | Unplanned DB restart; must be survivable (D-UC-047). |
| D-ASM-013 | S3 Object Lock COMPLIANCE with ≥ 82-day default retention keeps every object written on or after Oct 11 until at least 2026-12-31. | VALIDATED (arithmetic) | Oct 11 + 81 days = Dec 31 (Oct 20 + Nov 30 + Dec 31). | — | — |
| D-ASM-014 | Hosting from AWS Sydney is acceptable to the organisers. | VALIDATED (relayed) | F-118 organiser answer relayed by SYZ 2026-10-14 (paraphrase). | — | — |
| D-ASM-015 | From Sydney, `web3.binance.com` and `api.commonservice.io` are reachable without geo-restriction. | UNVALIDATED | No network calls allowed in this review. | Gate A host check (read-only). | No trading/logging from the host (blocking). |
| D-ASM-016 | An automatic supervisor restart of the same registered build is not a prohibited change (Q-40). | UNVALIDATED | Team position C5; F-114 does not name restarts. | Organiser question Q-40 (team). | If prohibited, any crash ends the run's compliance; design keeps restarts logged as incidents. |
| D-ASM-017 | Our journal `VERSION_REGISTERED` event plus the committed manifest satisfy "logged in a version event" (F-60). | UNVALIDATED | Procedure never issued (Q-33); team treats it as our obligation. | Re-check against official rules when issued. | Possible version-gap finding at audit. |
| D-ASM-018 | The final wallet gets a new `AI_SEEDS_SECRET`, installed before the run starts (Q-35). | UNVALIDATED | IDEA-035 C7 team assumption. | Team confirms by Oct 26 (GAP-52). | Logs for the final wallet rejected 401 (blocking). |
| D-ASM-019 | Signer journald collected from an EBS snapshot at teardown is enough for "complete local logs". | PARTIAL | IDEA-047 R7 design; refusals/signatures are also in the DB. | Phase 2: check the procedure and what signer journald alone holds. | Audit gap if the snapshot is lost (signer instance replaced). |
| D-ASM-020 | Deployable lockfiles are fully pinned with hashes (G-12). | CONTRADICTED (test lock) | Observed at setup: `pip install --require-hashes -r deploy/requirements-test.lock` fails — psycopg 3.3.6 has no hash. Runtime locks not yet checked. | Phase 2: check runtime/signer/aws locks and the host install mode. | Unpinned artefacts on hosts (P1 if a deployable lock lacks hashes). |
| D-ASM-021 | The release bundle built locally equals the CI-built bundle (deterministic build). | UNVALIDATED | — | Phase 2: build twice / compare. | Hash comparison (D-REQ-055) would fail or be meaningless. |
| D-ASM-022 | 20 GB EBS and 20→30 GB RDS hold 14+ days of journal including full model I/O. | UNVALIDATED | Bytes per round not measured. | Phase 2: measure bytes/round in system tests; project. | Disk/DB full mid-run (P0). |
| D-ASM-023 | Alarm notifications reach a person (SNS email confirmed). | UNVALIDATED | Host-only. | Gate A alarm test. | Silent failures; under F-114 a person may only observe. |
| D-ASM-024 | The organisers' receiver has no published SLA; outages past 02:00 UTC are possible. | VALIDATED (absence) | Kit has no SLA (K18 lists no availability statement). | — | Late logs flagged "fill without log" (manual review), not loss; D-REQ-025 limits exposure. |
| D-ASM-025 | The official test-round marker `"example": true` is acceptable for development rounds. | PARTIAL | F-106 (c) organiser example code; Q-37 answered in practice. | — | Auditors might misread dev logs; low. |
| D-ASM-026 | UTC-based schedules (anchor slots, day roll, 02:00 deadline, daily checks) are unaffected by the US DST end on Nov 1. | UNVALIDATED | — | Phase 2 clock tests across 2026-11-01. | Duplicate/missed slots (P1). |
| D-ASM-027 | The vendored ai-seeds SDK is used, if at all, only in a way that respects one Client per process and a non-shared data directory; otherwise our own PROTOCOL client is used. | UNVALIDATED | Code not read in phase 1. | Phase 2 trace. | Shared data dir → duplicate/lost logs. |
| D-ASM-028 | An integrity quarantine (journal fails verification) is rare enough that failing closed for the rest of the run is acceptable. | UNVALIDATED | No measurement; zero-human rule means no recovery. | Team decision (D-CON-09). | Trading stops for the rest of the run. |
| D-ASM-029 | The kit's demo-code conventions behind F-106/F-111 are as summarised. | UNVALIDATED (input gap) | The demo code and SDK `examples/` are not preserved in the repo (only Guide, PROTOCOL, READMEs, wheel, manual_push.sh), so F-106 (a)–(d) cannot be re-checked against verbatim text. | Keep F-106 as convention (SHOULD) only. | Low: conventions are not rules. |
| D-ASM-030 | No published grace window exists for the "upload after any material incident" (F-62, Q-14). | VALIDATED (absence) | Kit silent (K18); official rules not issued (F-90). | Conservative: upload incident journal within the next archive cycle. | — |

## 4. Use cases

| ID | Trigger and state | Expected behaviour | Requirements |
|---|---|---|---|
| D-UC-001 | Hold-only round (no candidate passes): normal operation. | One journal decision + one round log `orders: []`, ACKed. | D-REQ-001, D-REQ-005, D-REQ-007, D-REQ-033, D-REQ-040 |
| D-UC-002 | Round fails before broadcast: quote expired / risk block / approve fails. | One log; order without `tx_hash`; reason in `output`; incident if a failure class. | D-REQ-002, D-REQ-005, D-REQ-008, D-REQ-041 |
| D-UC-003 | Round fails after broadcast: swap reverts. | One log with the swap hash; settlement; incident `revert`. | D-REQ-003, D-REQ-030, D-REQ-041 |
| D-UC-004 | Crash after broadcast, before receipt. | Restart: same version, incident; observation ingested; interrupted round closed with the hash before any new round. | D-REQ-003, D-REQ-020, D-REQ-071, D-REQ-078 |
| D-UC-005 | Crash before broadcast, after signature durable. | Restart; reconcile; no second signature; one log. | D-REQ-020, D-REQ-030, D-REQ-031, D-REQ-078 |
| D-UC-006 | Gas top-up round (BNB below floor). | Own round; one BUY `BNB` order with hash; `cot` says gas top-up. | D-REQ-009, D-REQ-003, D-REQ-030 |
| D-UC-007 | Receiver down 23:00–03:00 UTC. | Logs buffered; retried with same IDs; D logs ACK after 03:00; breach journaled with real time; signing stops once delivery is overdue past the bound; HALT clears after ACK. | D-REQ-013, D-REQ-018, D-REQ-019, D-REQ-025, D-REQ-073, D-REQ-075 |
| D-UC-008 | Receiver down for two days. | No new swaps signed while overdue; rounds still logged locally; everything ACKs after recovery in order; incidents recorded; no human step. | D-REQ-013, D-REQ-018, D-REQ-025, D-REQ-070, D-REQ-074, D-REQ-075 |
| D-UC-009 | Round log over the size limit (huge model I/O). | One valid fallback log with the full record's hash; no command. | D-REQ-015, D-REQ-016, D-REQ-138 |
| D-UC-010 | Duplicate chunk / resend after lost ACK. | Same event ID and bytes; receiver de-dups; one logical event. | D-REQ-011, D-REQ-012, D-REQ-017 |
| D-UC-011 | Clock skew > 5 min on the uploader. | 401 TIMESTAMP_SKEW; event stays undelivered and visible; clock check HALTs trading; once the clock is fixed the same event is delivered without a person. | D-REQ-014, D-REQ-111, D-REQ-073, D-REQ-075 |
| D-UC-012 | Clock steps backward (NTP correction / reboot). | Clock HALT; no decision with a time earlier than the last; clears or stays latched per D-CON-09; no duplicate round. | D-REQ-073, D-REQ-075, D-REQ-111 |
| D-UC-013 | Restart mid-round (SIGKILL at each durable step). | Exactly one log per round; no duplicate command/signature. | D-REQ-020, D-REQ-071, D-REQ-078 |
| D-UC-014 | Crash loop (bad host state, repeated failure at start). | Supervisor keeps restarting with delay; incidents; no economic duplication; repeated-failure HALT if rounds fail. | D-REQ-072, D-REQ-073, D-REQ-041 |
| D-UC-015 | HALT that must clear on its own (delivery deadline breach). | HALT journaled; clears automatically after ACK; trading resumes. | D-REQ-073, D-REQ-075, D-REQ-077 |
| D-UC-016 | Repeated failed rounds (dependency down). | HALT after N failures; clears after N successes; incidents. | D-REQ-073, D-REQ-075, D-REQ-041 |
| D-UC-017 | Integrity failure: journal row altered/corrupt. | Quarantine: no write or signature; reported through health/alarm. | D-REQ-034, D-REQ-073, D-REQ-104 |
| D-UC-018 | Backup restore into an empty DB and replay of a whole day. | Restore verified against anchors; replay reaches the same head; stale restore refused. | D-REQ-037, D-REQ-085, D-REQ-087 |
| D-UC-019 | Anchor gap (archive unavailable for 3 hours). | Missed slots recorded as incidents, never backfilled; next slot anchors the current head. | D-REQ-036, D-REQ-041 |
| D-UC-020 | Release files differ from the manifest. | Every service refuses to start. | D-REQ-052, D-REQ-136 |
| D-UC-021 | Installed bundle hash ≠ CI-built hash. | Provisioning refuses before extracting. | D-REQ-055, D-REQ-107 |
| D-UC-022 | Config changed after the manifest. | Start refused (config hash). | D-REQ-052, D-REQ-057 |
| D-UC-023 | Version event before the first trade. | No command until VERSION_REGISTERED / activation; commands carry that version. | D-REQ-054, D-REQ-053 |
| D-UC-024 | Final activation with a fresh wallet and new run. | Old run closed; new run quarantined until activated; separate secret/outbox/nonce dirs; address mismatch refused. | D-REQ-024, D-REQ-122, D-REQ-137 |
| D-UC-025 | Whole 14-day scored run with zero human action. | Rounds, logs, anchors, backups, reconciliation and recoveries run autonomously; no release; resources hold. | D-REQ-070, D-REQ-123, D-REQ-057, D-REQ-089, D-REQ-103 |
| D-UC-026 | Disk on primary fills (journald / evidence artifacts). | Alarm/incident before full; services fail closed, no lost committed record. | D-REQ-089, D-REQ-041, D-REQ-104 |
| D-UC-027 | Database storage fills. | Alarm at threshold; autoscaling to cap; writes fail closed (no signing without durable record). | D-REQ-089, D-REQ-031, D-REQ-104 |
| D-UC-028 | AWS credits run out. | Budget alerts earlier; projection shows margin; if exhausted the account closes (deployment risk). | D-REQ-103 |
| D-UC-029 | RDS restart / maintenance / single-AZ failure. | Services see `Unavailable`, fail closed, retry; no signing without DB; resume automatically; incidents. | D-REQ-070, D-REQ-031, D-REQ-041 |
| D-UC-030 | Host replaced/recovered by EC2 auto-recovery. | Same disks; services start under systemd; restart incident; uploader resumes outbox. | D-REQ-105, D-REQ-071, D-REQ-013 |
| D-UC-031 | Alarms with hosts off (dev pauses). | No service alarm spam; archive alarms still meaningful. | D-REQ-104 |
| D-UC-032 | Alarms with hosts on: heartbeat stops. | Alarm fires with missing data breaching; notification sent. | D-REQ-104, D-REQ-040, D-REQ-076 |
| D-UC-033 | Winner audit asks for complete local logs, manifests, version history for a sampled trade. | Export yields tx → round log → decision record → version → manifest, plus model I/O. | D-REQ-010, D-REQ-058, D-REQ-088, D-REQ-124 |
| D-UC-034 | Auditor samples a hold round and a failed round. | Both have journal decisions and round logs. | D-REQ-001, D-REQ-002, D-REQ-033 |
| D-UC-035 | Secret leakage path: exception while loading `AI_SEEDS_SECRET` or DB token. | Error text/journald/repr contain no secret. | D-REQ-023 |
| D-UC-036 | Wrong wallet configured on the runtime/uploader. | Refuse to start. | D-REQ-024, D-REQ-137 |
| D-UC-037 | Compromised primary forges a signing request. | Signer refuses outside its own checks; primary holds no key. | D-REQ-135, D-REQ-101 |
| D-UC-038 | Development round with registered dev credentials from a dirty tree. | Uploader/runtime refuse (unverified release). | D-REQ-021, D-REQ-055 |
| D-UC-039 | Dev/rehearsal rounds visible to auditors. | Marked `"example": true`; no placeholder hashes. | D-REQ-022 |
| D-UC-040 | UTC midnight / day roll during an outage. | Day's logs still tracked against their day's deadline; daily fill-vs-log check runs on recovery. | D-REQ-018, D-REQ-026 |
| D-UC-041 | US DST end Nov 1. | UTC schedules unchanged; no duplicate/missed anchor or check. | D-REQ-036, D-REQ-026 |
| D-UC-042 | End-of-run window and after Nov 12. | No release; logs continue until stop; final export and archive retained. | D-REQ-057, D-REQ-088, D-REQ-086 |
| D-UC-043 | Reconciliation mismatch (unexplained balance change). | Degraded mode, incident; recovery automatic after reconciliation passes. | D-REQ-039, D-REQ-041, D-REQ-070 |
| D-UC-044 | Hung coordinator (alive, no heartbeat). | Watchdog restarts it; incident. | D-REQ-076, D-REQ-040 |
| D-UC-045 | Two runtime processes at once (stale owner after restart). | Fencing: only the epoch owner commits/signs; the other refuses. | D-REQ-071, D-REQ-110 |
| D-UC-046 | Restore from backup while an old primary still runs (zombie). | Stale restore refused; fencing prevents dual signing. | D-REQ-037, D-REQ-110 |
| D-UC-047 | Migration needed on the hosted DB before Gate A. | Defined credential-safe route; not during the run. | D-REQ-108 |
| D-UC-048 | Signer host needs the bundle and key without internet. | Defined provisioning route; key never transits the primary. | D-REQ-108, D-REQ-101 |
| D-UC-049 | Version gap: a transaction under an unregistered build. | Impossible: start and signing refuse. | D-REQ-054, D-REQ-053, D-REQ-058 |
| D-UC-050 | Hostile document/prompt injection in model I/O. | Logged faithfully, escaped; size bounded; no crash. | D-REQ-138, D-REQ-006 |
| D-UC-051 | Oversized journald or CloudWatch volume. | Short retention locally; journald retained for audit export; costs bounded. | D-REQ-109, D-REQ-103 |
| D-UC-052 | Teardown after the audit. | Archive and audit material kept through Dec 31; DB/hosts removed only after export. | D-REQ-086, D-REQ-088, D-REQ-109 |
| D-UC-053 | ai-seeds credential not yet registered for final wallet at activation (401 INVALID_SIGNATURE). | Events stay FAILED-visible; retried slowly; trading blocked by delivery bound; clears once registered. | D-REQ-014, D-REQ-025, D-REQ-122 |
| D-UC-054 | Week-one checkpoint and self-check evidence due. | Commit + note + system-test report recorded. | D-REQ-120, D-REQ-121 |
| D-UC-055 | Rehearsal cannot sign in time for 5 days incl. a weekend. | Deviation decided and recorded; no silent shortening. | D-REQ-125, D-REQ-059, D-REQ-126 |
| D-UC-056 | Normal buy: approve, confirm, re-quote, swap, receipt. | Decision record before signing; only the swap hash in the round log; record completed with fill, fees and gas. | D-REQ-003, D-REQ-004, D-REQ-030, D-REQ-031, D-REQ-032 |
| D-UC-057 | Incident (restart, HALT) and the daily journal upload. | Extra journal upload with chain head after the incident; daily upload lands in write-once storage. | D-REQ-035, D-REQ-041, D-REQ-077 |
| D-UC-058 | Hourly anchor written. | Payload carries only ids/times/sequence/head; one per slot. | D-REQ-036, D-REQ-038 |
| D-UC-059 | Model round with a tool loop; auditor asks for thinking output and full model I/O. | Round log input/cot/output per kit; full records retained and exported. | D-REQ-006, D-REQ-007, D-REQ-042, D-REQ-088 |
| D-UC-060 | Prompt/config/lockfile change during development produces a new build. | New manifest hash with services and register; fallbacks listed; version event before it trades. | D-REQ-050, D-REQ-051, D-REQ-056, D-REQ-060, D-REQ-059, D-REQ-054 |
| D-UC-061 | A teammate fixes a bad pushed commit, or a secret is staged. | Fix by new commit (no rewrite); CI secret scan fails the push. | D-REQ-061, D-REQ-062 |
| D-UC-062 | Provisioning the two-host stack (mocked plan). | Two hosts, signer without internet, Sydney, private encrypted IAM DB, recovery alarms, offline idempotent install. | D-REQ-100, D-REQ-102, D-REQ-105, D-REQ-106, D-REQ-107 |
| D-UC-063 | Activation pack review on Oct 26. | Frozen commit, manifest, register without OPEN rows, final-wallet config with secret slot, runbook, rota. | D-REQ-127, D-REQ-122, D-REQ-059 |
| D-UC-064 | The designated Binance audit account reviews the repository. | Read-only access to the private registered repo with full history. | D-REQ-128, D-REQ-061 |
| D-UC-065 | CloudWatch API unavailable or metric publish fails. | Services unaffected; alarms treat missing data as breaching; incident if the publisher fails repeatedly. | D-REQ-104, D-REQ-041 |
| D-UC-066 | Execution facts arrive duplicated or out of order; one fact row is altered. | Each fact journaled once in causal order; altered row refused; incident. | D-REQ-079, D-REQ-030, D-REQ-077 |
| D-UC-067 | Weekend or US market holiday (no market change, tokens possibly closed). | Rounds still run and log (holds); anchors, backups and checks continue on UTC schedules. | D-REQ-001, D-REQ-036, D-REQ-085 |
| D-UC-068 | Archive write (S3) fails during the daily backup/journal upload. | Retried; incident; database untouched; the next successful upload carries the current head. | D-REQ-035, D-REQ-085, D-REQ-041 |
| D-UC-069 | Model provider or EDGAR times out mid-round. | One round log with non-empty cot (deterministic path statement) and the failure reason; incident; repeated-failure HALT if it persists. | D-REQ-001, D-REQ-002, D-REQ-007, D-REQ-041, D-REQ-073 |

## 5. Conflicts and ambiguities

| ID | Topic | Text A | Text B | Conservative reading followed | Open question (organisers' wording) or owner |
|---|---|---|---|---|---|
| D-CON-01 | Scored-run changes | F-15: "14 days of live operation. Keep improving — every version must be committed and logged before it trades" | F-114: "Once the competition starts, no changes allowed — period."; F-117 (paraphrase): improve during development only. | No version, config or release change from final activation to the end of the run (G-46, DEV-13). Restart of the same build only (C5). | Settled for planning by F-114/F-117; Q-40 still open: "During the scored run, may a supervisor automatically restart the same registered build after a crash, and may the agent's own code pause and resume trading by itself?" |
| D-CON-02 | Log arrival deadline | Guide p.3, under "Batch mode:": "a day's logs must arrive before 02:00 UTC the next day" | Realtime mode (default) re-sends from a spool with no stated deadline. | Treat 02:00 UTC next day as the deadline for every round log (D-REQ-018). | "Does the 02:00 UTC next-day deadline also apply to round logs uploaded in realtime mode that were delayed by an outage?" |
| D-CON-03 | Standby | Proposal: "The deployment is one primary runtime plus a fenced cold standby." | IDEA-046 B1 (decision 2026-10-12): two hosts, "Lost: ... standby host"; DEV-18 still OPEN; GAP-02 open. | Declared text binds until the deviation is decided and recorded (G-11). DECISION-NEEDED (team). | Team decision, not an organiser question. |
| D-CON-04 | Rehearsal length | Proposal: "full pipeline for 5+ days including a weekend, at minimum size" | plan.md §9: signer ON ≥ [2] days, shadow otherwise; IDEA-035 §8.3 shadow until blockers close; DR-21 / Gate B Oct 20. | Declared 5+ days binds (G-11); a shorter signed rehearsal needs a decided deviation (GAP-04). DECISION-NEEDED if Gate B slips. | Team decision. |
| D-CON-05 | Scoring basis | F-43/F-45/F-50 (equity %, drawdown tie-break, trades not scored) | F-115 (PnL, drawdown, logs, code repo together) | Owned by B; for D both readings require complete logs and repo integrity, so D requirements are unchanged. | Q-39 (owned by B). |
| D-CON-06 | Version-event procedure | F-60/F-15 require version events. | No procedure issued (Q-33); team: our own obligation (C6). | Journal VERSION_REGISTERED + manifest committed + version ID in every round log (D-REQ-010/054). Not presented as open (Q-33 answered in practice). | None (settled in practice). |
| D-CON-07 | Incident upload deadline | F-62: "plus one after any material incident ... within the published grace window" | No grace window published (Q-14; K18). | Upload the journal/incident record at the next archive cycle and keep realtime round logs (D-REQ-035). | Q-14 remains with the team's list. |
| D-CON-08 | Human HALT | Proposal: "Humans can halt the agent but never trade." | F-114 / F-117. | DEV-14 decided (2026-10-11): HALT is autonomous code only. | None. |
| D-CON-09 | Latched HALTs vs autonomous recovery | IDEA-042 H5: integrity and clock HALTs "latched for the run". | F-114 zero human action ⇒ a latched HALT ends trading for the rest of the run; F-115 ("if you don't trade at all? That's definitely not what this competition is about.") | Failing closed is rule-compliant (no rule requires trading), but loses the run. DECISION-NEEDED: keep latching, or define an autonomous clear for the clock HALT (e.g. after N minutes of sane, monotonic, NTP-synced time) with integrity quarantine still latched. | Team decision. |
| D-CON-10 | Two write-once uploads | F-62 daily trace uploads to write-once storage. | Proposal: the journal is uploaded daily to write-once storage with the chain head, and anchored hourly. | Both apply: ai-seeds round logs (official trace) and our journal backup/anchors (declared). | None. |
| D-CON-11 | Retention horizon | G-47: through at least Nov 20 and any later technical review (Q-28). | IDEA-036: at least Dec 31, 2026; IDEA-046 B4: teardown after the winner audit. | Keep the archive (and exported local logs) to ≥ Dec 31; tear down compute/DB only after export. | None. |
| D-CON-12 | Safe-mode build | Proposal: "registered safe-mode build"; G-14 [PRACTICE]. | F-117/G-46: one build only. | DEV-15 decided: safe behaviour inside the one build. | None. |
| D-CON-13 | Pre-final integrity check content | F-14: "clear the pre-final integrity check" | Not specified anywhere (kit silent). | Be ready to show commit, manifest, bundle hash, services and deviations; change nothing after activation. | "What does the pre-final integrity check at final activation consist of, and what must we submit for it?" |

## 6. Summary verification (protocol §1.2)

| Item | Verbatim source checked | Verdict |
|---|---|---|
| F-01..F-07 | source_page.md body and sidebar; re-verification note (API timestamps) | Faithful. |
| F-08 | source_page.md Overview | Faithful ("produce a decision trail that proves how it got there"). |
| F-09..F-19 | source_page.md timeline table (image transcription) and banner | Faithful; F-15 annotation of F-117 is labelled as an organiser answer. |
| F-21..F-24 | source_page.md The Challenge | Faithful. |
| F-33, F-34 | source_page.md What makes a strong entry | Faithful. |
| F-40, F-41 | source_page.md Stage 1 | Faithful (marked not applicable below). |
| F-47, F-48, F-51 | source_page.md Stage 3 / Not scored | Faithful. |
| F-60..F-62, F-66 | source_page.md Rules & Restrictions | Faithful. |
| F-70, F-72 | source_page.md Eligibility | Faithful. |
| F-80 | source_page.md header notes | Faithful (page-state snapshot; not applicable). |
| F-90 | Guide p.2 ("If anything here conflicts with the official competition rules, the official rules prevail.") | Faithful. |
| F-99 | Guide p.2, p.13; PROTOCOL §1 | Faithful. |
| F-100 | Guide p.3, p.13, p.18 | Faithful. |
| F-101 | Guide p.3, p.13–14, p.18; PROTOCOL §1–§6; SDK `client.py` | Faithful. Note: the 02:00 UTC quote sits under "Batch mode" in Guide p.3; F-101 places it under batch too (correct). Its application to realtime is our conservative reading (D-CON-02), not a kit statement. |
| F-103 | Guide p.3, p.15, p.17 | Faithful. |
| F-106 | Demo and SDK `examples/` code | NOT VERIFIABLE: those files are not preserved in the repo (input gap D-ASM-029). Kept as convention (SHOULD). |
| F-109 | SDK `client.py`, `wire.py`, README, Guide p.12–14, p.17–18 | Faithful: retries 3 × (0.5, 1, 2 s), spool + 30 s flush incl. previous runs, 4xx not saved, batch day starts at process start, 30-min retries until next 00:00 UTC. Additional verified detail (not in F-109): the spool flush re-sends via `POST /v1/files` and puts back failed parts even on 4xx, so a spooled log retries forever. |
| F-110 | PROTOCOL §1–§6; test vectors reproduced 2026-10-14 (both match) | Faithful. |
| F-111 | Demo code | NOT VERIFIABLE (same input gap as F-106); not a requirement source. |
| F-112 | vendor README hashes; `shasum -a 256` 2026-10-14: wheel `2bd16fec…e4e3bb`, manual_push.sh `24795c09…004c61b` match | Faithful for the vendored files; the stale `SHA256SUMS` itself is not in the repo. |
| F-113, F-114, F-117, F-118 | SKILL.md §1.10 (relayed; F-117/F-118 paraphrases) | Recorded as relayed; no verbatim source to check further. |
| K10 | SDK `client.py`; README | Faithful. |
| K11 | PROTOCOL §1, §6 | Faithful. |
| K12 | PROTOCOL §2–§6; vectors reproduced | Faithful. |
| K13 | Guide p.13–14, p.17–18; `client.py`; `manual_push.sh` | Faithful; the engineering caveat is labelled as ours. |
| K14 | Guide p.2–3, p.13, p.15–17 | Faithful (L1–L14). |
| K17 | vendor/kit READMEs | D1/D3/D11/D12 consistent with repo copies; D2/D4–D9 refer to files not in the repo (not re-checked). |
| K18 | Kit as a whole | Consistent with what the verbatim copies contain. |

### 6.1 DECIDED items: decider, date, supersession

| Record | Decider / date | Status |
|---|---|---|
| IDEA-035 C5 (automatic restart) | Team position relayed by SYZ, 2026-10-11 | Not superseded; DEV-14 and IDEA-042 H1–H2 implement it. Not an organiser answer (Q-40). |
| IDEA-035 §4 GAP-35 (hourly anchoring as declared) | SYZ, 2026-10-11 | Not superseded; IDEA-036 criteria. |
| IDEA-035 §4 GAP-02 (standby after exploring AWS) | SYZ, 2026-10-11 | Followed by IDEA-046 B1 (2026-10-12, Yao Zhu): two hosts, standby host lost. DEV-18 still OPEN → D-CON-03. |
| IDEA-035 §4 GAP-04 (rehearsal from Oct 12–13, shadow) | SYZ, 2026-10-11 | Superseded in timing by DEPLOYMENT_BUILD (signed rehearsal from Oct 21); declared 5+ days still binds → D-CON-04. |
| IDEA-035 B9 (deployment inputs) | Deferred 2026-10-11 | Answered in part by IDEA-046 B1–B4. |
| IDEA-035 B11 (gas top-up log format) | Keegan + SYZ, 2026-10-11 | Not superseded. |
| IDEA-035 C7 (new secret for the final wallet) | Team assumption, 2026-10-11 | Assumption, not a decision (D-ASM-018). |
| IDEA-036 criteria 1–6 | SYZ, 2026-10-11 (decided to build) | Not superseded. |
| IDEA-042 L1–L8, P1–P4, H1–H6 (+H3 amendment), R1–R5, W1–W4, A1–A4, G1–G2 | Keegan's build record, 2026-10-11; criteria merged via PR #13 | Engineering design records, not team policy decisions; used as DECIDED engineering acceptance. H5 latching conflicts with F-114 autonomy (D-CON-09). |
| IDEA-045 H01–H06 | Yao Zhu, 2026-10-12 | Not superseded; adapted to two hosts by IDEA-046. |
| IDEA-046 B1–B4, L01–L08 | Yao Zhu, 2026-10-12 | B3 closed by F-118 (2026-10-14). B1 conflicts with the declared standby (D-CON-03). |
| IDEA-047 scope; R3 (evidence store shared read-only) | Yao Zhu, 2026-10-14 | Not superseded. |
| IDEA-047 R1–R7 | Review fixes, 2026-10-14 | Not superseded; R5 amended (alarms only with hosts on). |
| plan.md D-05 | Not decided | Only the C5 restart annotation is decided. |
| plan.md §6.5 register | Rows decided 2026-10-03..2026-10-11; DEV-18..20 OPEN; all DRAFT | Final at the Oct 26 freeze (D-REQ-059). |
| DEPLOYMENT_BUILD DR-01..DR-22, Gates A–C | IDEA-038 team brief, 2026-10-11 | Readiness checklist; dates passed for Gate A (Oct 14–16). |
| IDEA-021 AT01–AT20 | Adopted as engineering acceptance tests (protocol §1.1) | AT ownership per IDEA-021 §8; D claims AT10/11/13/14/15/19 (recovery/upload side)/20. |
| G-46 (no releases during the run) | Rewritten 2026-10-08 after F-117 | Not superseded. |

## 7. Coverage of D's scope inventory (protocol §1.7)

| Inventory item | Requirement IDs, owner or reason |
|---|---|
| F-01 | Not applicable: event identity/hosting platform; "Binance ... verifies the record" is served by D-REQ-030/088. |
| F-02, F-03, F-04, F-06 | Not applicable: prize, team size, finalist count, tags (no system behaviour). |
| F-05 | D-REQ-123 (2-week scored run), D-REQ-120/125 (2-week build). |
| F-07 | Not applicable to the system; DoraHacks deadline is a team deliverable question (Q-18, I-60). |
| F-08 (decision trail) | D-REQ-030..042, D-REQ-010, D-REQ-088. |
| F-09 | Not applicable: banner dates, consistent with F-13..F-15. |
| F-10, F-11 | Not applicable: past phases (proposal submitted, finalist). |
| F-12 | D-REQ-128 (repo with audit access); dev-wallet registration owned by C; declaration not requested (Q-33). |
| F-13 | D-REQ-120, D-REQ-121, D-REQ-125. |
| F-14 | D-REQ-122, D-REQ-127, D-REQ-055; integrity check D-CON-13. |
| F-15 | D-REQ-123, D-REQ-001..018 (daily traces), D-REQ-057 (version events, D-CON-01). |
| F-16 | D-REQ-088 (final export); trading stop owned by B (end-of-run). |
| F-17 | D-REQ-124, D-REQ-058, D-REQ-086, D-REQ-088. |
| F-18 | Not applicable: list of onboarding documents; status in F-90. |
| F-19 | D-REQ-123 (full window uptime). |
| F-21 | D-REQ-037 (no rewind: stale restore refused), D-REQ-019. |
| F-22 (hosting, monitoring, logging, recovery) | D-REQ-100..111, D-REQ-070..078, D-REQ-001..026. |
| F-23 | Not applicable (Binance's ownership); supports never-do #11 below. |
| F-24 | D-REQ-128; D-REQ-062. |
| F-33 | D-REQ-041, D-REQ-077. |
| F-34 | D-REQ-030, D-REQ-010, D-REQ-032, D-REQ-079. |
| F-40, F-41 | Not applicable: Stage 1 proposal judging (complete). |
| F-47 | D-REQ-088, D-REQ-042, D-REQ-109. |
| F-48 | D-REQ-030, D-REQ-058, D-REQ-070, D-REQ-059. |
| F-51 | D-REQ-040, D-REQ-041. |
| F-60 | D-REQ-054, D-REQ-030, D-REQ-070. |
| F-61 | D-REQ-055, D-REQ-061, D-REQ-062, D-REQ-051, D-REQ-056. |
| F-62 | D-REQ-018, D-REQ-019, D-REQ-023, D-REQ-035, D-REQ-042, D-REQ-014. |
| F-66 | D-REQ-030, D-REQ-059, D-REQ-023. |
| F-70 | D-REQ-102. |
| F-72 | Not applicable: personal eligibility. |
| F-80 | Not applicable: page-state snapshot. |
| F-90 | All kit-derived rows use the conservative reading; re-check when official rules arrive (D-CON-01/02/13). |
| F-99 | D-REQ-001, 005..008, 010. |
| F-100 | D-REQ-002..004, D-REQ-026. |
| F-101 | D-REQ-011..018, D-REQ-024, D-REQ-111. |
| F-103 | D-REQ-021, D-REQ-022, D-REQ-023. |
| F-106 | D-REQ-002 (reason in output), D-REQ-007, D-REQ-022 (SHOULD; D-ASM-029). |
| F-109 | D-REQ-012, 013, 024; D-ASM-027 (SDK use). |
| F-110 | D-REQ-005, 009, 014, 015, 017. |
| F-111 | D-REQ-001/002/020 (do not copy demo omissions). |
| F-112 | D-REQ-056 (pinned vendored artefacts with our hashes). |
| F-113 | D-REQ-024 (secret per wallet); issuance owned by C/team. |
| F-114, F-117 | D-REQ-057, D-REQ-070..076. |
| F-118 | D-REQ-102. |
| K10 | D-REQ-012, 013, 024, D-ASM-027. |
| K11 | D-REQ-005, 011, 015, 016. |
| K12 | D-REQ-013, 014, 017. |
| K13 | D-REQ-012, 013, 018; manual push is a human step → replaced by D-REQ-014 autonomy. |
| K14 | D-REQ-001..010, 021..023. |
| K17 | D-REQ-056. |
| K18 | D-CON-02, 07, 13; D-ASM-024, 030. |
| Never-do #1 | D-REQ-070. |
| Never-do #2 | D-REQ-030, D-REQ-031. |
| Never-do #5 | D-REQ-054, D-REQ-052, D-REQ-055. |
| Never-do #6 | D-REQ-061. |
| Never-do #7 | D-REQ-023, D-REQ-062. |
| Never-do #9 | D-REQ-019, D-REQ-018, D-REQ-035. |
| Never-do #10 | D-REQ-102. |
| Never-do #11 | Documentation rule; checked for D's docs and the deviations register in phase 2 (D-REQ-059). |
| Never-do #12 | D-REQ-001, 003, 025. |
| Never-do #13 | D-REQ-021. |
| Never-do #3, #4, #8 | Owned by C (#3, #4) and A (#8). |
| G-03 | D-REQ-050..055, 136. |
| G-04 | D-REQ-010, 030..032. |
| G-06 (retention) | D-REQ-042 (capture content owned by A). |
| G-07 | D-REQ-012, 018, 034..036. |
| G-08 (operations) | D-REQ-070..076. |
| G-11 | D-REQ-059, D-REQ-110. |
| G-12 | D-REQ-056. |
| G-14 | D-CON-12 (superseded by G-46/DEV-15). |
| G-17 | D-REQ-102. |
| G-19 | D-REQ-001, 002, 020. |
| G-40 | D-REQ-061. |
| G-41 | D-REQ-062. |
| G-43 (scheduling) | D-REQ-039, D-REQ-026 (content owned by B). |
| G-44 | D-REQ-041. |
| G-45 | D-REQ-120 (SHOULD: replay agreement figures in the week-one note) — PRACTICE. |
| G-46 | D-REQ-057. |
| G-47 | D-REQ-085, 086, 089. |
| Declared: Reproducibility — Versions (4 sentences) | D-REQ-050, 052, 053, 061 ("protected" → DEV-17). |
| Declared: Reproducibility — Decision records (6 bullets) | D-REQ-031, 032, 033. |
| Declared: Reproducibility — Logs (4 sentences) | D-REQ-034, 035, 036, 037, 039, 040. |
| Declared: Reproducibility — Rerun (4 sentences) | D-REQ-087; "Self-hosted model weights are archived": not applicable in v1.0 (no self-hosted model, DEV-01/DEV-12); reasoning capture → D-REQ-042 (content A). |
| Declared: Reproducibility — Recovery (3 sentences) | Owned by C (signing at most once, observable identifiers, unresolved blocks); runtime ordering D-REQ-078. |
| Declared: Reproducibility — Onboarding gates (3) | D-REQ-060; eligibility/prerequisites owned by A/C. |
| Declared: Team capability — roles | Not applicable (team roles; owners nominal). |
| Declared: Team capability — v1.0 deliverables | "version gating, audit logging, reconciliation and recovery" → D-REQ-052, 001, 039, 070; others A/B/C; planner DEV-20 OPEN (B). |
| Declared: "Anything not working by Oct 22 is cut, not delayed." | D-REQ-126. |
| Declared: "one primary runtime plus a fenced cold standby" | D-REQ-110, D-CON-03. |
| Declared: Plan Sep 30 – Oct 10 | Not applicable: past (skeleton deferred by team decision 2026-10-03). |
| Declared: Plan Oct 12–18 | D-REQ-120 (week-one checkpoint), D-REQ-001 (trace uploads), D-REQ-040 (heartbeat), D-REQ-039 (reconciliation); minimum-size trade owned by C. |
| Declared: Plan Oct 19–26 | D-REQ-125, D-REQ-121, D-REQ-126, D-REQ-120 (self-check). |
| Declared: Plan Oct 27–29 | D-REQ-122, D-REQ-127; "registered safe-mode build" → DEV-15 (D-CON-12). |
| Declared: Plan Oct 29 – Nov 12 | D-REQ-123; "Improvements are versioned releases ..." → DEV-13 (D-CON-01). |
| Declared: Plan Nov 13–20 | D-REQ-124, D-REQ-088. |
| Declared: "Every trade is written as a decision record before signing and is tied to one registered version." | D-REQ-031, D-REQ-030. |
| Declared: "a version gate", "a reconciler", "a write-once audit uploader" | D-REQ-052, D-REQ-039, D-REQ-001/035. |
| Declared: "Stack: Python, PostgreSQL, and write-once object storage." | D-REQ-085, 086 (stack fact). |
| Declared: Failure modes (incident record; reconciliation mismatch → degraded) | D-REQ-041, D-REQ-039 (HOLD/no-new-risk content owned by B). |
| Declared: Governance (versioned config hashed; limits change only by version event; humans can halt) | D-REQ-050, D-REQ-057; human halt → DEV-14 (D-CON-08); "never loosened" owned by B. |
| Declared: "The server clock is checked, and trading stops if it drifts." | D-REQ-111, D-REQ-073. |
| Declared: "Changes during the run are made only on non-P&L evidence ..., each through a logged version event." | Superseded by DEV-13 (D-CON-01); D-REQ-057. |
| DR-07 | D-REQ-001..018. |
| DR-13 | D-REQ-071..076. |
| DR-15 | D-REQ-036..038. |
| DR-16 | D-REQ-085, 100..108. |
| DR-17 (release and run side) | D-REQ-024, D-REQ-122, D-REQ-137 (key/wallet side owned by C). |
| DR-18 | D-REQ-050, 051, 054, 059. |
| DR-19 | D-REQ-087. |
| DR-20 | D-REQ-123 (acceptance suite), integration step (protocol §3.5). |
| DR-21 | D-REQ-125. |
| DR-22 | D-REQ-127. |
| DR-01..DR-06, DR-08..DR-12, DR-14 | Owned by A/B/C per DEPLOYMENT_BUILD owners. |
| AT10 | D-REQ-011, 012, 017, 010. |
| AT11 | D-REQ-013, 014, 016, 018, 025. |
| AT13 | D-REQ-087. |
| AT14 | D-REQ-072, 076, 070. |
| AT15 (runtime clocks/timers) | D-REQ-036, 073, 018; D-UC-012, 041. |
| AT19 (recovery/upload not starved; storage budgets) | D-REQ-138. |
| AT20 | D-REQ-085, 088, 110, 125, 055. |
| AT01..AT09, AT12, AT16..AT18 | Owned by A/B/C (IDEA-021 §8). |
| GAP-02 | D-REQ-110, D-CON-03. |
| GAP-04 | D-REQ-125, D-CON-04. |
| GAP-05 | D-REQ-126; mandatory-component list to be re-stated at integration. |
| GAP-33 | D-REQ-052, 055 (registration proof via release/manifest; safe mode superseded by DEV-15). |
| GAP-34 | D-REQ-011, 012, 034, 085. |
| GAP-35 | D-REQ-036..038. |
| GAP-36 | D-REQ-085, 086, 089, 100..108 (RTO/RPO stated as deployment risk). |
| GAP-37 | D-REQ-127 (rota as deployment risk). |
| GAP-38 | Integration (status from evidence). |
| GAP-45 | D-REQ-056, D-ASM-020. |
| GAP-46 | D-REQ-001..018. |
| GAP-48 | D-REQ-021, 022. |
| GAP-62 | D-REQ-051, 059, 060. |
| GAP-65 | D-REQ-087, 078 (runtime side). |

## 8. Trace (phase 2)

Not started. Filled only after this catalogue is frozen and pushed (protocol §2).

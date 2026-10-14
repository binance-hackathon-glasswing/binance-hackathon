# Final review D: accountability and operations (logging, audit, release, runtime, hosting)

**Assigned to: Yao Zhu** (random draw, 2026-10-14).

You are one of four reviewers running LARP's final pre-deployment review (IDEA-049). LARP is our agent for the Binance Agentic AI Challenge. Your section is **the decision trail and the platform it runs on**:
- the coordinator and rounds;
- write-ahead decision records;
- the journal;
- ai-seeds round logs and their delivery;
- versioning, manifests and release;
- the deviations register;
- supervision, autonomous HALT, restart and recovery;
- storage, backups, anchors and restore;
- hosting (AWS), provisioning and monitoring;
- the timeline and deliverables;
- **integrating all four sections at the end.**

**Before anything else, read `docs/build/final-review/00-common-protocol.md` in full. It is part of this prompt.** Then read `AGENTS.md`, and `docs/skill/SKILL.md` §0 (reading contract, never-do list). Follow the protocol's phases exactly:
1. Independent requirements catalogue.
2. Trace and tests.
3. Fix loop.
4. Repeat until a full pass finds nothing new.

Branch `review/final-d-<yyyymmdd>`. Record: `docs/ledger/IDEA-049-D.md`. Catalogue: `docs/build/final-review/D-catalogue.md`.

**No AWS actions** (protocol §0.6). Hosting requirements are tested with Terraform's mocked plans, the container provisioning test and documents. Anything that needs the real account is `NOT-OFFLINE`, and goes into `docs/build/AWS_RUNBOOK.md` as a named check.

## Scope inventory (every item must appear in your coverage table)

Where an item is split between sections, you own only the aspect named here.

- **Official page:**
  - F-01..F-07, F-08 (the decision-trail aspect), F-09..F-19 (timeline and deliverables per phase, incl. F-14's commit, manifest and pre-final integrity check);
  - F-21, F-22 (hosting, monitoring, logging, recovery), F-23, F-24, F-33, F-34, F-47, F-48, F-51, F-60, F-61, F-62, F-66, F-70, F-72;
  - F-40/F-41 and F-80 may be marked not applicable, with the reason.
- **Kit:**
  - F-90 (kit status);
  - F-99 (one log per round, its fields);
  - F-100 (`tx_hash` rules and the daily fill-vs-log check);
  - F-101 (upload modes, the 02:00 UTC deadline, "a normal return from `log()` does not mean the log was delivered", one `Client` per process, clock ±5 min, size limits);
  - F-103 (test-log hygiene: demo runs upload real logs);
  - F-106 (logging conventions);
  - F-109, F-110 (SDK behaviour, log schema and server errors);
  - F-111 (the logging pitfalls);
  - F-112 (kit defects);
  - K10–K14, K17, K18, each checked against the verbatim `PROTOCOL.md`, `logging.md`, `ai-seeds-sdk-README.md`, the Guide pages and the vendored SDK code.
- **Organiser:** F-113 (secret issuance), F-114 and F-117 (no changes once the run starts; zero human action, so every recovery is autonomous), F-118 (hosting in Sydney is fine).
- **Never-do lines (SKILL.md §0.3):**
  - #1 (allowed human actions vs F-114/F-117);
  - #2 (version and decision-record mapping);
  - #5 (nothing trades unless committed, pushed, manifested and version-evented);
  - #6 (no history rewrite);
  - #7 (no secrets in repo or logs);
  - #9 (no backfilled logs; daily write-once uploads; buffering);
  - #10 (no VPN or relay);
  - #11 (no POLICY called a rule);
  - #12 (every broadcast swap's `tx_hash` reaches a round log; every round logged);
  - #13 (no demo code with the registered wallet's credentials).
- **Guardrails:** G-03, G-04, G-06 (the retention side), G-07, G-08 (no human interaction, operations side), G-11 (manifest and deviations), G-12 (lockfile pinning), G-14, G-17, G-19, G-40, G-41, G-43 (reconciliation scheduling), G-44, G-45, G-46, G-47.
- **Declared proposal** (`docs/proposal/proposal_answers.md`):
  - "Reproducibility plan", every sentence;
  - "Team capability + intended scope" (delivery commitments);
  - every sentence about logging, audit, hosting, recovery, monitoring and standby (D-05).
- **Decided items:**
  - IDEA-035 (C5 automatic restart, hourly anchoring as declared, §4 decisions on standby and rehearsal);
  - IDEA-036 criteria;
  - IDEA-042 decided parts;
  - IDEA-045/046/047 decisions (two hosts, root-only key, Sydney, budget, R1–R7);
  - plan.md D-05 and §6.5;
  - `docs/build/DEPLOYMENT_BUILD.md` gates A, B and C.
- **Readiness and acceptance:** DR-07, DR-13, DR-15, DR-16, DR-17 (the release and run side), DR-18, DR-19, DR-20, DR-21, DR-22; AT items about runtime, audit, storage, restore, replay, release and isolation (`docs/ledger/IDEA-021.md`).
- **Backlog items to resolve or re-state:** GAP-02 (standby), 04, 05, 33, 34, 35, 36, 37 (rota, as a deployment risk), 38, 45, 46, 48, 62, 65.

## Exclusive paths (you may edit)

- Code: `larp/runtime/`, `larp/audit/`, `larp/storage/`, `larp/integration/` except `contract.py`, `larp/contracts.py`, `larp/ports.py`.
- Infrastructure: `migrations/` (new files only; coordinate numbering with C), `deploy/`, `.github/`.
- Tools: `tools/system_test.py`, `tools/build_release_bundle.py`, `tools/test_host_bundle.sh`, `tools/render_deviations.py`.
- Config: `config/release/`, `config/runtime/`, `config/hosts/uploader.example.json`, `config/hosts/evidence.example.env`.
- Tests: `tests/runtime/`, `tests/audit/`, `tests/storage/`, `tests/integration/`, `tests/redteam/`, `tests/support.py`, `tests/host_support.py`, `tests/test_contracts.py`.
- Records: your catalogue and record.
- **Shared docs**, at integration only: `docs/LEDGER.md`, `docs/INCOMPLETE_WORK.md`, `README.md`, `docs/build/AWS_RUNBOOK.md`, `docs/build/architecture-deployment.md`.

## Use-case prompts (in addition to protocol §1.5)

Make sure your use cases include at least:
- a hold-only round;
- a round that fails before, during or after a broadcast;
- a gas top-up round;
- the ai-seeds receiver down from 23:00 to 03:00 UTC (past the deadline), and for two days;
- a log over the size limits;
- a duplicate chunk;
- clock skew over 5 minutes;
- a restart mid-round;
- a crash loop;
- a HALT that must clear on its own;
- quarantine after an integrity failure;
- a backup restore and a replay of a whole day;
- an anchor gap;
- a release whose files differ from the manifest, or that does not match the CI-built bundle hash;
- a config changed after the manifest;
- a version event before the first trade;
- a final activation with a fresh wallet and run;
- **the whole 14-day scored run with zero human action**, including disk, database and credit exhaustion;
- AWS credits running out;
- RDS failover or restart;
- a host replaced by EC2 auto-recovery;
- alarms when hosts are off and when they are on;
- the winner audit asking for complete local logs, manifests and version history (F-47, F-49).

## After your catalogue is frozen (not before)

Only then compare with these areas, which earlier work left open or flagged. They are hints for phase 2, not requirements:
- **Round driver:** the round driver integration is on Keegan's IDEA-048 branch (shadow only). Check its contract against your requirements and C's.
- **Logs and monitoring:** no journald shipping exists. Signer logs are collected from a disk snapshot. Service alarms exist only while hosts run (IDEA-047 R5).
- **Signer access:** there is no route to the signer host for provisioning (`docs/build/AWS_RUNBOOK.md` step 5). Specify the requirement, compare the options, and record DECISION-NEEDED.
- **Migrations:** they need the RDS admin secret, which no host can read (runbook step 6).
- **Backups:** the AWS Free plan caps RDS automated backups at 1 day. Check that the archive's daily logical backup and restore meet the recovery requirements alone.
- **Rehearsal:** the rehearsal requirement conflicts between the declared "5+ days including a weekend" and the plan (GAP-04).
- **Version events:** registration and version-event procedures are not issued by the organisers (Q-33).

## Integration (you run this last)

When A, B and C have opened their PRs:
1. Merge them and yours into `codex/system-testing-20261012` in an agreed order, with merge commits only, after each one's CI is green.
2. Apply every section's "Requested shared edits".
3. Run the full suite, `tools/system_test.py`, the Terraform tests and `tools/test_host_bundle.sh` on the merged head. Confirm Linux CI.
4. Merge the four catalogues' coverage tables into `docs/build/final-review/MASTER-coverage.md`. Every F-item, K section, never-do line, `[RULE]`/`[RULE-DERIVED]` G-item, declared sentence, DR item and AT item must map to exactly one owning requirement or a stated "not applicable". Anything unowned goes back to the closest section for one more loop.
5. Write the IDEA-049 result in `docs/ledger/IDEA-049.md`, with:
   - final counts and CI links;
   - the open DECISION-NEEDED items with options;
   - the deployment risks, each with owner, validation step and deadline;
   - an explicit statement of what is **not** established offline.
6. Give the team the go / no-go inputs for starting hosts. The decision itself is the team's. Promotion to `main` is a separate team decision.

## Done means

Protocol §4, plus:
- a test proves every possible round path produces exactly one round log, delivered with a stored acknowledgement, or a HALT that clears once it is delivered;
- every trade-capable path is blocked unless the running release verifies against a registered manifest;
- every recovery the scored run can need is autonomous, with no step that requires a person.

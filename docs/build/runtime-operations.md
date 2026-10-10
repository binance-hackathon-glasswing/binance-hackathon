# Runtime/audit implementation — IDEA-028

This branch delivers the offline runtime foundation from the shared kickoff
`e10eae2`. It is not a registered or activated trading build. Isaac reviews this
component; the other owners' implementations have not been merged.

## What is implemented

- Additive Protocol ports and immutable documents; the original 13 tests remain.
- PostgreSQL migrations with applied-content checksums; atomic event/hash-chain,
  projection, policy/execution state, reservations, jobs and command/audit outboxes.
- Expected-version and owner-epoch checks, duplicate-ID integrity checks, durable
  command-release checks, verified journal reconstruction and quarantined restore.
- Thin coordinator using assessment, policy, independent planner and execution
  ports. Its fixture financial reducer never settles a proposal or a quote.
- Bounded Linux namespace workers: no inherited credential environment, home,
  project `.env`, network or writable application mounts. JSON-only communication,
  response/memory/CPU/wall-time bounds. Separate bounded service lanes preserve
  safety/reconciliation/audit capacity while evidence work hangs.
- Durable jobs with immutable identity, priority, attempts, lease, UTC high-water
  mark, expiration/catch-up disposition and calendar/tzdata provenance.
- Protocol 2.0 audit adapter with immutable event/chunk bytes, stable retry identity,
  explicit per-chunk ACK/permanent/exhausted states and deadline-breach reporting.
  Protocol signing vectors are tested. No calls to vendor `Client.log()` recreate IDs.
- Consistent full-state logical backup, checksum verification and quarantined
  restore, including upload attempts/ACKs, jobs and issued command checks. An
  external anchored head/minimum version can reject a stale restore. A restore is
  never proof of current signing authority.
- Digest-pinned Linux image, dependency profiles and GitHub CI; no live default.

## Reproduce

Use the runtime test profile when testing this component alone. The full research
environment remains `requirements.lock`; model packages are unnecessary in the
coordinator image. Do not load `.env` for these tests. In accordance with AGENTS.md,
commit and push changed decision/logging code and test criteria before running it.

On Linux with Python 3.12.15, PostgreSQL and bubblewrap installed:

```sh
python3.12 -m venv .venv-runtime
.venv-runtime/bin/python -m pip install -r deploy/requirements-test.lock
.venv-runtime/bin/python -m pip check
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export LARP_TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/larp_test
.venv-runtime/bin/python -m pytest -q -p no:cacheprovider
.venv-runtime/bin/python -m larp.runtime.demo > /tmp/larp-offline-trace.json
```

`docker compose -f deploy/compose.test.yml up -d --wait` supplies a disposable
loopback-only PostgreSQL database. `docker compose -f deploy/compose.test.yml down`
removes that test instance. Its trust authentication is a test-only choice; never
copy it into a production database. Tests create unique `larp_test_*` schemas and
remove their own schemas. The demo retains its unique `larp_demo_*` schema so the
journal and outboxes can be inspected; never use a registered wallet database.

This session also used an isolated PostgreSQL 14.24 cluster in Ubuntu 22.04 WSL,
with Python 3.12.15 and bubblewrap. Its dedicated directory is
`/home/theruin08/.local/share/larp-runtime-test`; database `larp_test`, port `55432`.
Its reproducible test command is the above with username `theruin08` and Python
`/home/theruin08/.local/share/larp-runtime-test/venv/bin/python`. The original
Windows environment is `C:/Users/keega/anaconda3/envs/binance-hackathon/python.exe`
(Python 3.12.14). On Windows, PostgreSQL and Linux sandbox cases intentionally
skip when their required environment is absent; Linux CI requires them to run.

Build and inspect the image without credentials or a network:

```sh
docker build -f deploy/Dockerfile -t larp-runtime:review .
docker run --rm --network none --read-only --cap-drop ALL larp-runtime:review
```

The image's default command is an inspection message. Worker sandboxing is tested
on Linux hosts, not nested inside this restricted container. A production worker
host must pass the same isolation tests. Never enable privileged containers as an
implicit workaround. No provider credentials or model packages are mounted into
the generic offline sandbox; a reviewed provider worker needs separate capability
and network allow-list deployment.

## Interface and recovery rules

`runtime-contracts.md` defines versioned document vocabulary. The demo outputs
concrete requests, market observations, assessments, plans, committed batches,
execution observations and audit chunks as synthetic fixtures. `FakePlanner`,
`FakeExecution`, `FakeMarket` and `settle` are intentionally small integration
fakes, not alternate production trading/accounting engines. Replace those objects
through the existing ports with reviewed owner modules.

Only `PostgresStore.commit` changes portfolio projections and reservations.
Execution observations have their own immutable IDs; repeat identical observations
are idempotent. Same ID/different facts fails. Quotes/signatures do not settle
balances. `command()` is an execution request check, not a transaction signer;
the live adapter must additionally enforce route, nonce, finality, wallet, current
risk and ownership at each sign/broadcast boundary. New state versions invalidate
unused old command authorizations. Takeover fences old epochs; it cannot revoke
previously emitted signed bytes. Production takeover remains quarantined here.

Round input is durable before assessment. The plan and complete received policy/
assessment records are durable before an execution request can be released. A
pending round is closed on restart with its known possibly-broadcast swap hashes;
late receipts are appended as new observations, never changes to an uploaded log.
Approval hashes are rejected by the swap-mapping schema. If another authorized
swap attempt is needed after closure, Isaac's adapter must use a linked new round.

Database write failure stops command release. Remote audit failure does not become
a local-disk error: bytes remain pending/permanent/exhausted with attempts and a
deadline. ACK bodies must match event ID and chunk index. Exhausted delivery needs
a separately registered bounded recovery policy; the current worker never resets
its retry budget on restart. It reports a missed deadline without backdating.

## Backup, anchoring and retention

`larp.storage.backup.export(store)` takes a repeatable-read snapshot of all runtime
tables. Write the returned document durably to protected artifact storage; it may
contain private model/evidence records and must never be committed. After migrating
an **empty** target database, `restore(store, document)` verifies bytes and journal
projections and quarantines every restored run while increasing its local epoch.
Use `verify(run_id, minimum_version=..., anchored_head=...)` against independently
retained authority/anchor evidence. Database restore alone cannot regain wallet
authority, and `offline=True` cannot activate a dev/live run.

`anchor(...)` validates the selected sequence/head, passes an immutable head record
to a write-once receiver and stores its acknowledgement. The declared hourly anchor
interval remains 3600 seconds in the example config. Actual destination, worker
schedule, retention duration, protection policy and disaster-recovery tests require
deployment configuration. There is no deletion/compaction path; existing data is
retained. No shorter retention or rehearsal has been adopted.

## Missing configuration and owner checklist

All nulls in `config/runtime/activation.example.json` are intentional missing
settings, not defaults. `capabilities()` rejects dev/live startup. Even a fully
populated configuration remains rejected until the reviewed live capability bundle
and cross-component acceptance are implemented.

| Owner | Remaining input or work |
|---|---|
| Keegan + team | Database/host destinations, DB roles and TLS, backup and Object Lock destination, retention and recovery objectives, hourly anchor service and alerts, external authority checkpoint, signed/registered release procedure, dependency/image upgrade policy |
| Isaac | Review; real adapters, signer key isolation/binding, payload validation, nonce/finality reconciliation, external signer/broadcaster epoch enforcement, actual funding/BNB evidence, gas-swap logging convention |
| Keith | Financial reducer, risk/plan semantics, reservation/settlement arithmetic, selected risk/policy profiles and measured operational parameters |
| Yao Zhu | Verified claims and thesis/job semantics, model/provider and rights, full provider worker isolation, model I/O storage limits, real evidence ingestion |
| Team | Scored UTC window/valuation, service declarations, registered repo/build evidence, dev/final wallet separation and full 5+ day rehearsal including weekend |

Provision `LARP_DATABASE_URL` only to the relevant database services. The test CLI
uses only `LARP_TEST_DATABASE_URL`. Give `AI_SEEDS_ADDRESS` and `AI_SEEDS_SECRET`
only to the uploader, `WALLET_PRIVATE_KEY` or `WALLET_MNEMONIC` only to the signer,
and provider/Web3 credentials only to the corresponding workers. Leave
`AI_SEEDS_URL` unset; this adapter uses the documented endpoint directly. Do not
paste populated credentials into chat. No registered credentials were used here.

## Acceptance interpretation

See IDEA-028 for tested commits/results and the AT01–20 matrix. Passing this suite
establishes the documented synthetic/storage boundaries only. It does not establish
full engine readiness, live adapter parity, profitable policy, actual hosted restore
or the submitted rehearsal. Human review and the other owners' branches are still
required. No main merge or live activation is part of this change.

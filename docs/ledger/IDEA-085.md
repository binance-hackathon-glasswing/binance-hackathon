# IDEA-085 — Reuse database connections instead of one IAM login per transaction

- Date / author: 2026-10-23 / Yao Zhu (decision), Claude Code (build)
- Status: open (pre-registered below; built on branch `claude/db-connection-reuse-20261023`)
- What: `IamPostgresStore` keeps a small per-process pool of open connections. Each connection does one RDS IAM login
  and is reused by later transactions for up to 10 minutes, instead of a new TLS connection and IAM login for every
  transaction. A plain-DSN `PostgresStore` (tests, local tools) keeps today's connection-per-transaction behaviour.
- Why it might help: the SJ-06 J8 incident (IDEA-049-C, 2026-10-23). On `db.t4g.micro` (1 GiB, the largest size the
  AWS free plan allows), the signed dev rehearsal did thousands of IAM logins an hour. After about 7 hours, RDS's
  in-instance auth helper and Postgres were short of memory. Logins timed out for every role from 20:45Z, every
  service then failed in the same second, and the restart storm kept the database down; there were no trades. The
  database held only 30 MB of data, so size was not the cause. Fewer logins remove the load on the auth helper and the
  per-connection start-up cost; a per-process pool of a few connections cuts logins by about two orders of magnitude.
- Cost / risk: changes the one database chokepoint every hosted service uses (runtime, execution, uploader, archive,
  signer). Risks:
  - state leaking between transactions on one connection (mitigated: the code uses only `SET LOCAL`, transaction-level
    isolation and `pg_advisory_xact_lock`; there is no session-level `SET`, advisory lock, `LISTEN` or temp table
    outside migrations);
  - a pooled connection the server closed while idle (mitigated: one retry on a fresh connection, only when the very
    first statement of the transaction fails, before any caller work);
  - thread safety (mitigated: a connection is checked out by one transaction at a time; the pool is lock-protected).
- Links: IDEA-049-C SJ-06 J8 incident and SJ-06-DB01; `docs/INCOMPLETE_WORK.md` SJ-06-DB01; `larp/storage/postgres.py`;
  `larp/runtime/database.py`; never-do and version rules in `docs/skill/SKILL.md` (G-03, G-11; F-60).

## Pass criteria (written before any test is run)

Tests on the branch, with the disposable PostgreSQL 14.24 from `deploy/compose.test.yml`:

- **R1 fewer logins:** with `IamPostgresStore` and a fake RDS client, 50 sequential transactions generate exactly one
  IAM token and open one connection.
- **R2 recycling:** a connection older than the maximum age (600 s) is closed and replaced at the next checkout, never
  mid-transaction. At most 4 idle connections are kept.
- **R3 no leaked state:** on one reused real connection, `SET LOCAL statement_timeout`, `lock_timeout` and
  `synchronous_commit` are back to their server defaults after each transaction. A `REPEATABLE READ, READ ONLY`
  transaction does not make the next transaction read-only.
- **R4 failure handling:**
  - a caller exception rolls back, and the connection is reused only when it is idle and not broken;
  - a broken connection is discarded;
  - a pooled connection killed by the server (`pg_terminate_backend`) while idle is replaced transparently on the next
    transaction;
  - a failure after caller work started is never retried;
  - errors keep today's mapping (`IntegrityError` with SQLSTATE and constraint only; otherwise `Unavailable`, with no
    DSN or token in the message).
- **R5 concurrency:** two nested transactions use two different connections; 8 threads running 25 transactions each
  complete with no shared connection in use by two transactions at once.
- **R6 unchanged default:** a plain `PostgresStore` opens and closes one connection per transaction, as before.
- **R7 no regression:** the full local suite passes with the database configured, with no new failures or skips
  compared with the base `f56bcf6` run in the same environment.

Release and host (later, not in this change): mirror CI on all four jobs, Keegan's release review, then installation
through a new run (the signer refuses a build other than the one the run registered at P4). The host check is the
login rate in the database log, plus no auth time-out over a soak of at least 8 hours on `db.t4g.micro`.

## Results

2026-10-23, local Mac, Python 3.12 with `deploy/requirements-test.lock`, disposable PostgreSQL 14.24
(`deploy/compose.test.yml`), code commit `31b0949`. Offline only: no host, AWS or wallet action.

- **R1–R6 PASS.** `tests/storage/test_connection_reuse.py` has 16 tests: 10 with fake connections and 6 on real
  PostgreSQL, including `pg_terminate_backend` of a pooled connection while idle and mid-transaction. Together with
  the 8 tests in `tests/runtime/test_review_boundaries.py`, 24 passed with 0 skipped.
  - R1: 50 transactions use 1 token and 1 connection.
  - R2: an aged connection is replaced only at checkout, and at most 4 are kept idle.
  - R3: statement and lock timeouts and the read-only/isolation settings are back to the server defaults on the
    reused backend.
  - R4: a killed idle connection is replaced; a kill mid-transaction raises `Unavailable` and is not retried;
    SQLSTATE mapping is unchanged.
  - R5: nested transactions use separate backends; 8 threads × 25 transactions never share one in use.
  - R6: the plain store opens one connection per transaction.
- **Red proof:** the same file against base `f56bcf6` gives **15 failed, 1 passed**. The one that passes is the
  connect-error mapping, which is meant to be unchanged. R6 fails at base only because the fake connection has no
  context-manager methods, which the old code needed. That is a test-harness artifact, not a behaviour difference.
- **Updated tests:** the two tests in `test_review_boundaries.py` that asserted one IAM login per transaction (more
  than 5 tokens; at least 3 connections) now assert one fresh token per pooled connection, with at most 4 connections.
- **R7 PASS:**

  | Run | Passed | Skipped | Subtests | Time |
  |---|---|---|---|---|
  | base `f56bcf6` | 2468 | 10 | 3882 | 301 s |
  | branch | 2484 | 10 | 3882 | 303 s |

  The branch adds exactly the 16 new tests. The 10 skips are identical, all environmental: bubblewrap 3, systemd
  runner 5, external market artifact 1, private fixture 1. There are no failures.

Verdict: **R1–R7 supported (offline).** Still open: mirror CI on all four jobs, Keegan's review and release
qualification, and the host soak on `db.t4g.micro` (database-log login rate and no auth time-out over at least 8 h)
through a new run.

## RV1 — review fix: bound a dead pooled socket (2026-10-23, assistant review of PR257)

**Finding.** Before IDEA-085 every transaction opened a fresh connection with `connect_timeout=5`. A pooled
connection can now sit idle for up to `MAX_CONNECTION_AGE_S` (600 s). If the database host vanishes without closing
the socket, the next statement waits for the kernel's TCP retransmission timeout, which is about 15 minutes on Linux
defaults, or longer for an idle socket with no keepalive. The service then stalls instead of failing into the
existing `Unavailable` path. The `_begin` retry only helps once the socket actually errors.

**Fix.** `SOCKET_OPTIONS` in `larp/storage/postgres.py`, used by both `PostgresStore._connect` and
`IamPostgresStore._connect`:
- `connect_timeout=5`, unchanged;
- `keepalives=1`, `keepalives_idle=30`, `keepalives_interval=10`, `keepalives_count=3`: a dead idle socket is detected
  in about 60 s;
- `tcp_user_timeout=30000`: unacknowledged sends fail after 30 s. A healthy server ACKs at the TCP level while a
  query runs, so this cannot cut short a statement that `statement_timeout` (15 s) allows.

**Pass criteria (written before the runs):**
- RV1-1: both connect paths pass exactly `SOCKET_OPTIONS`, and the test fails if the keepalive and user-timeout
  options are removed.
- RV1-2: a real PostgreSQL connection reports `keepalives=1`, `keepalives_idle=30`, `keepalives_count=3` and
  `tcp_user_timeout=30000`.
- RV1-3: full offline suite with no failures beyond the environment-only ones on the same machine.

**Not tested:** an actual dead peer, for example a dropped route mid-idle. Only option presence and propagation are
verified. Kernel behaviour is standard libpq/Linux semantics, and the host soak remains the real check.

**RV1 results** (2026-10-23, Linux, Python 3.12 test venv without the torch/transformers stack, disposable
PostgreSQL 16):
- **RV1-1 and RV1-2 PASS.** `tests/storage/test_connection_reuse.py` and `tests/runtime/test_review_boundaries.py`:
  26 passed, 0 skipped. With the keepalive and user-timeout options removed, both new tests fail (red proof).
- **RV1-3 PASS.** Full suite: 2482 passed, 11 skipped, 3 failed. The 3 failures are
  `test_service_configs` ×2 and `test_fault_points` ×1. They fail identically on canonical `f56bcf6` in the same venv
  ("Installed operations dependency differs from manifest lock"), because that venv omits locked packages. They are
  environmental, not caused by this change.

## Review RV01 (2026-10-23, Keith with Claude Code): dead-peer check of RV1, comment fix, notes

An independent review of the PR head `2ba46cb` found the same dead-socket problem that RV1 fixes, and built a
fix with the same settings. RV1 landed first, so this review keeps RV1's code and adds what RV1 left open.

- **Reproduced the review base.** The 24 targeted tests pass on a fresh disposable PostgreSQL 14.24 (Python 3.12.14,
  psycopg 3.3.6). The 8-thread test passed 30 times out of 30 with the same connection count each run, so it is not
  flaky. No session state leaks: there is no session-level `SET`, advisory lock, `LISTEN`, `autocommit`/`row_factory`
  change or server-side cursor in `larp/`. Every hosted service uses its store from one thread (background threads
  never touch it), so 4 idle connections cover the nesting. Through a proxy that resets the socket with no
  PostgreSQL error message, a pooled connection was replaced without the caller seeing it.
- **Dead peer, the case RV1 lists as not tested: PASS on RV1's code.** Written before the run: a pooled connection
  whose server is cut off from the network raises `Unavailable` within 60 s, while without the options it is still
  blocked at 90 s. Method: a client container from the CI runner image (Linux, Python 3.12.15, psycopg 3.3.6) and a
  separate disposable PostgreSQL 14.24 on their own Docker network. After one pooled transaction, PostgreSQL was
  disconnected from the network (`docker network disconnect`, no reset) and the next transaction started:
  - with `SOCKET_OPTIONS` at `eadd5d4`: `Unavailable` after 30.5 s (the retry on a fresh connection then failed at
    once);
  - control, the same code with `SOCKET_OPTIONS` cut back to `connect_timeout=5` (the behaviour before RV1): still
    blocked at 90 s.
  An earlier local run through a proxy that stops answering also showed the next pooled transaction still blocked
  at 20 s without the options.
- **Comment fix (RV01-F2).** `larp/runtime/database.py` said the IAM token is not kept after connecting. libpq
  keeps it in memory for the connection's life (`connection.info.password`), now up to 600 s. That is still less than
  the token's own 15-minute validity, and the token is still never logged or put in an error. Comment only; no
  behaviour change.
- **Noted, no change:**
  - psycopg prepares a statement on the server after 5 runs on one connection, so prepared statements now last up to
    600 s per pooled connection. That is harmless here (explicit column lists; the backup's `SELECT * … LIMIT 0` runs
    once per table), but backend memory should be watched in the host soak.
  - A server that accepts packets but stops answering (for example, memory-starved) still blocks a statement with no
    client-side limit, as it did mid-transaction before. TCP settings cannot detect it; only the runtime's watchdog
    bounds it.
  - The linked SJ-06-DB01 item is added by PR253, which is still open; it is not on this base. Once both merge, its
    remaining work becomes this entry's open items.

Still open, unchanged: mirror CI on all four jobs, Keegan's review and release, and the host soak on
`db.t4g.micro`. Add to the soak: no `Unavailable` from a dead path, and backend memory with long-lived connections.

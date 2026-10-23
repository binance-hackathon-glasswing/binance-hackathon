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

(none yet)

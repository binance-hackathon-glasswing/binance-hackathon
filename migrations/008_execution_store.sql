-- IDEA-042 item 2 (DR-04): durable store for the W04 execution machine (larp.execution.Store), shared with the
-- execution service (prompt 06). One row per economic intent; events and state commit together; the wallet barrier
-- allows one active execution per wallet and chain across runs. Signed bytes live only in execution_signatures,
-- which only the signer role can read (deploy/postgres/roles.sql).
CREATE TABLE IF NOT EXISTS execution_authority (
    run_id text PRIMARY KEY REFERENCES runs, version bigint NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS executions (
    key text PRIMARY KEY, run_id text NOT NULL REFERENCES runs, wallet text NOT NULL, chain bigint NOT NULL,
    terminal boolean NOT NULL, revision bigint NOT NULL, state bytea NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS executions_wallet_barrier ON executions(wallet,chain) WHERE NOT terminal;
CREATE TABLE IF NOT EXISTS execution_events (
    sequence bigserial PRIMARY KEY, key text NOT NULL REFERENCES executions, revision bigint NOT NULL,
    event bytea NOT NULL, UNIQUE(key,revision)
);
CREATE TABLE IF NOT EXISTS execution_signatures (
    attempt text PRIMARY KEY, payload text NOT NULL, signed text NOT NULL
);
-- A pending EXECUTION_REQUEST is handed to exactly one W04 execution (PostgresStore.claim_command).
ALTER TABLE commands ADD COLUMN IF NOT EXISTS execution_key text;

-- IDEA-042 §4 X1 (DR-04): the execution service's store, adopted from Isaac's proposed schema
-- (larp/execution_live/store.py:SCHEMA, IDEA-039 at 28613da), DDL unchanged so that his test-only installer is a
-- no-op after the migrations. One row per economic intent with its hash-chained public journal; the wallet barrier
-- allows one active execution per wallet and chain across runs. Signed bytes live only in execution_signatures and
-- immutable final observations in execution_observations; grants in deploy/postgres/roles.sql.
CREATE TABLE IF NOT EXISTS execution_records (
    economic_key text PRIMARY KEY, run_id text NOT NULL REFERENCES runs,
    wallet text NOT NULL, chain_id bigint NOT NULL, terminal boolean NOT NULL,
    revision bigint NOT NULL, state bytea NOT NULL, state_hash text NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS execution_wallet_barrier
    ON execution_records(wallet,chain_id) WHERE NOT terminal;
CREATE TABLE IF NOT EXISTS execution_journal (
    economic_key text REFERENCES execution_records, revision bigint NOT NULL,
    event bytea NOT NULL, state_hash text NOT NULL, previous_hash text NOT NULL, head text NOT NULL,
    PRIMARY KEY(economic_key,revision)
);
CREATE TABLE IF NOT EXISTS execution_signatures (
    attempt_id text PRIMARY KEY, run_id text NOT NULL REFERENCES runs,
    payload_hash text NOT NULL, signed bytea NOT NULL, signed_hash text NOT NULL
);
CREATE TABLE IF NOT EXISTS execution_observations (
    event_id text PRIMARY KEY, run_id text NOT NULL REFERENCES runs,
    observation bytea NOT NULL, observation_hash text NOT NULL
);

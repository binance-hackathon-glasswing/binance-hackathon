-- Transactions use synchronous_commit=on. Application roles must not edit history.
CREATE TABLE IF NOT EXISTS runs (
    run_id text PRIMARY KEY, wallet_id text NOT NULL, chain_id bigint NOT NULL,
    version bigint NOT NULL DEFAULT 0, epoch bigint NOT NULL DEFAULT 1,
    quarantined boolean NOT NULL DEFAULT true, head text NOT NULL,
    initial bytea NOT NULL, projection bytea NOT NULL,
    policy_state bytea NOT NULL, execution_state bytea NOT NULL,
    clock_ms bigint NOT NULL DEFAULT 0,
    UNIQUE(wallet_id, chain_id)
);
CREATE TABLE IF NOT EXISTS events (
    run_id text REFERENCES runs, event_id text NOT NULL, sequence bigint NOT NULL,
    batch bytea NOT NULL, batch_hash text NOT NULL, event_hash text NOT NULL,
    previous_hash text NOT NULL, head text NOT NULL, receipt bytea NOT NULL,
    PRIMARY KEY(run_id,event_id), UNIQUE(run_id,sequence)
);
CREATE TABLE IF NOT EXISTS reservations (
    run_id text REFERENCES runs, intent_id text NOT NULL, asset text NOT NULL,
    units numeric(78,0) NOT NULL CHECK(units >= 0),
    PRIMARY KEY(run_id,intent_id,asset)
);
CREATE TABLE IF NOT EXISTS commands (
    run_id text REFERENCES runs, command_id text NOT NULL, payload bytea NOT NULL,
    epoch bigint NOT NULL, state_version bigint NOT NULL,
    status text NOT NULL DEFAULT 'PENDING', PRIMARY KEY(run_id,command_id)
);
CREATE TABLE IF NOT EXISTS rounds (
    run_id text REFERENCES runs, round_id text NOT NULL, request bytea NOT NULL,
    status text NOT NULL DEFAULT 'OPEN', PRIMARY KEY(run_id,round_id)
);
CREATE TABLE IF NOT EXISTS audit_events (
    run_id text REFERENCES runs, event_id text NOT NULL, round_id text NOT NULL,
    document bytea NOT NULL, PRIMARY KEY(run_id,event_id), UNIQUE(run_id,round_id)
);
CREATE TABLE IF NOT EXISTS audit_chunks (
    run_id text NOT NULL, event_id text NOT NULL, chunk_index integer NOT NULL,
    body bytea NOT NULL, status text NOT NULL DEFAULT 'PENDING',
    attempts integer NOT NULL DEFAULT 0, next_ms bigint NOT NULL DEFAULT 0,
    last_code text, acknowledgement bytea,
    PRIMARY KEY(run_id,event_id,chunk_index),
    FOREIGN KEY(run_id,event_id) REFERENCES audit_events
);
CREATE TABLE IF NOT EXISTS swap_owners (
    run_id text REFERENCES runs, tx_hash text NOT NULL, round_id text NOT NULL,
    decision_id text NOT NULL, version_id text NOT NULL,
    PRIMARY KEY(run_id,tx_hash)
);
CREATE TABLE IF NOT EXISTS jobs (
    run_id text REFERENCES runs, job_id text NOT NULL, document bytea NOT NULL,
    lane text NOT NULL, status text NOT NULL DEFAULT 'PENDING',
    attempts integer NOT NULL DEFAULT 0, next_ms bigint NOT NULL,
    lease_until_ms bigint NOT NULL DEFAULT 0, claimed_epoch bigint,
    PRIMARY KEY(run_id,job_id)
);
CREATE TABLE IF NOT EXISTS anchors (
    run_id text REFERENCES runs, sequence bigint NOT NULL, head text NOT NULL,
    stored_ms bigint NOT NULL, acknowledgement bytea NOT NULL,
    PRIMARY KEY(run_id,sequence)
);

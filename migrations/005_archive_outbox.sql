-- The archive outbox is deliberately outside Backup.v1: including backup payloads
-- in their own next backup causes recursive exponential growth. Restored runs are
-- quarantined and need a new archive namespace before maintenance can resume.
CREATE TABLE IF NOT EXISTS archive_clock (
    run_id text PRIMARY KEY REFERENCES runs,
    last_ms bigint NOT NULL
);
CREATE TABLE IF NOT EXISTS archive_outbox (
    run_id text REFERENCES runs, kind text NOT NULL CHECK(kind IN ('anchor','backup')),
    slot_ms bigint NOT NULL, payload bytea NOT NULL, sha256 text NOT NULL,
    status text NOT NULL DEFAULT 'PENDING', attempts integer NOT NULL DEFAULT 0,
    next_ms bigint NOT NULL DEFAULT 0, last_error text, acknowledgement bytea,
    PRIMARY KEY(run_id,kind,slot_ms)
);
CREATE INDEX IF NOT EXISTS archive_due ON archive_outbox(run_id,status,next_ms);

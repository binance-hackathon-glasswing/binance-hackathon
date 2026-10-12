-- IDEA-042 item 5 (DR-13): durable runtime process sessions. A session that never recorded its end was not shut
-- down cleanly; the next start commits a RESTART incident to the journal. Sessions only append and close.
CREATE TABLE IF NOT EXISTS process_sessions (
    run_id text REFERENCES runs, session_id text NOT NULL, build_id text NOT NULL,
    started_ms bigint NOT NULL, heartbeat_ms bigint NOT NULL, ended_ms bigint,
    PRIMARY KEY(run_id,session_id)
);

-- IDEA-047 S01: the signer host has no internet and reaches only the database (IDEA-046 B2), so the execution service
-- asks for signatures here. Every row is immutable. `signing_attempts` binds an attempt ID to one payload hash; a
-- request for that attempt with another payload hash fails the foreign key. A request is keyed by its own content
-- hash, so an identical re-send is a no-op and a request with fresh gates (after a timeout or a reauthorization) is a
-- new row. The signer answers with a signature in execution_signatures (at most one per attempt) or a refusal for
-- that one request. Grants in deploy/postgres/roles.sql.
CREATE TABLE IF NOT EXISTS signing_attempts (
    attempt_id text PRIMARY KEY, run_id text NOT NULL REFERENCES runs,
    economic_key text NOT NULL, payload_hash text NOT NULL,
    UNIQUE(attempt_id,payload_hash)
);
CREATE TABLE IF NOT EXISTS signing_requests (
    request_id text PRIMARY KEY, run_id text NOT NULL REFERENCES runs,
    attempt_id text NOT NULL, payload_hash text NOT NULL,
    request bytea NOT NULL, requested_s bigint NOT NULL,
    FOREIGN KEY(attempt_id,payload_hash) REFERENCES signing_attempts(attempt_id,payload_hash)
);
CREATE INDEX IF NOT EXISTS signing_requests_run ON signing_requests(run_id,requested_s);
CREATE TABLE IF NOT EXISTS signing_refusals (
    request_id text PRIMARY KEY REFERENCES signing_requests, run_id text NOT NULL REFERENCES runs,
    reason text NOT NULL, refused_s bigint NOT NULL
);

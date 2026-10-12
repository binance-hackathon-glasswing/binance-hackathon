CREATE TABLE command_checks (
    check_id bigserial PRIMARY KEY, run_id text NOT NULL REFERENCES runs,
    command_id text NOT NULL, epoch bigint NOT NULL, state_version bigint NOT NULL,
    checked_ms bigint NOT NULL
);

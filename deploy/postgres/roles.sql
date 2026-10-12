-- Provision after migrations as the database owner, once per environment.
-- Runtime hosts use RDS IAM authentication: no passwords in this script/state.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='larp_archive') THEN
    CREATE ROLE larp_archive LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='larp_uploader') THEN
    CREATE ROLE larp_uploader LOGIN;
  END IF;
  -- IDEA-042 item 7: coordinator/journal, W04 execution store, signer registry.
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='larp_runtime') THEN
    CREATE ROLE larp_runtime LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='larp_execution') THEN
    CREATE ROLE larp_execution LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='larp_signer') THEN
    CREATE ROLE larp_signer LOGIN;
  END IF;
END $$;
GRANT rds_iam TO larp_archive, larp_uploader, larp_runtime, larp_execution, larp_signer;
GRANT CONNECT ON DATABASE larp TO larp_archive, larp_uploader, larp_runtime, larp_execution, larp_signer;
GRANT USAGE ON SCHEMA public TO larp_archive, larp_uploader, larp_runtime, larp_execution, larp_signer;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT SELECT ON runs,events,reservations,commands,rounds,audit_events,audit_chunks,
  swap_owners,jobs,command_checks,process_sessions,execution_records,execution_journal,
  execution_observations TO larp_archive;  -- the daily backup exports every table larp.storage.backup restores
-- Signed transaction bytes are never readable by the archive role or written to a backup (IDEA-042 V8).
REVOKE SELECT ON execution_signatures FROM larp_archive;
GRANT SELECT (attempt_id,run_id,payload_hash,signed_hash) ON execution_signatures TO larp_archive;
-- SELECT ... FOR UPDATE needs update privilege; restrict it to the clock column.
-- The archive/uploader implementations only lock runs; they never write this field.
GRANT UPDATE (clock_ms) ON runs TO larp_archive, larp_uploader;
GRANT SELECT,INSERT,UPDATE ON archive_clock,archive_outbox TO larp_archive;
GRANT SELECT ON runs,audit_events,audit_chunks TO larp_uploader;
-- Re-running this script must also remove the earlier broad table privilege.
REVOKE UPDATE ON audit_chunks FROM larp_uploader;
GRANT UPDATE (status,attempts,next_ms,last_code,acknowledgement) ON audit_chunks TO larp_uploader;
-- No DELETE/DDL, trading command creation or wallet state mutation grants for the two roles above.

-- Coordinator and journal (larp.runtime). Never the execution store or the signer registry; never the run's
-- identity or initial projection.
GRANT SELECT,INSERT ON runs TO larp_runtime;
GRANT UPDATE (version,epoch,quarantined,head,projection,policy_state,execution_state,clock_ms) ON runs TO larp_runtime;
GRANT SELECT,INSERT ON events,commands,audit_events,audit_chunks,swap_owners,command_checks TO larp_runtime;
GRANT SELECT,INSERT,UPDATE ON reservations,rounds,jobs,process_sessions TO larp_runtime;
GRANT USAGE ON SEQUENCE command_checks_check_id_seq TO larp_runtime;

-- Execution service (Isaac's larp.execution_live, IDEA-042 §4 X2). Reads the journal to verify it and takes
-- commands through PostgresStore.command; never writes the run journal. Locking runs needs an UPDATE privilege:
-- only the clock column. Reads signed bytes to broadcast them; never writes them.
GRANT SELECT ON runs,events,reservations,commands,rounds,audit_events,audit_chunks,swap_owners,jobs TO larp_execution;
GRANT UPDATE (clock_ms) ON runs TO larp_execution;
GRANT SELECT,INSERT ON command_checks TO larp_execution;
GRANT USAGE ON SEQUENCE command_checks_check_id_seq TO larp_execution;
GRANT SELECT,INSERT,UPDATE ON execution_records TO larp_execution;
GRANT SELECT,INSERT ON execution_journal,execution_observations TO larp_execution;
GRANT SELECT ON execution_signatures TO larp_execution;

-- Signer registry only (signed bytes; the wallet key itself never enters the database). The registry write is
-- fenced on the run's owner epoch and version, which locks the run row.
GRANT SELECT ON runs TO larp_signer;
GRANT UPDATE (clock_ms) ON runs TO larp_signer;
GRANT SELECT,INSERT ON execution_signatures TO larp_signer;

-- The coordinator settles from the public execution journal and final observations; never the state or signatures.
GRANT SELECT ON execution_journal,execution_observations TO larp_runtime;

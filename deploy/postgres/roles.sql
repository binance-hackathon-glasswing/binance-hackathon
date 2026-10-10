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
END $$;
GRANT rds_iam TO larp_archive, larp_uploader;
GRANT CONNECT ON DATABASE larp TO larp_archive, larp_uploader;
GRANT USAGE ON SCHEMA public TO larp_archive, larp_uploader;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT SELECT ON runs,events,reservations,commands,rounds,audit_events,audit_chunks,
  swap_owners,jobs,anchors,command_checks TO larp_archive;
-- SELECT ... FOR UPDATE needs update privilege; restrict it to the clock column.
-- The archive/uploader implementations only lock runs; they never write this field.
GRANT UPDATE (clock_ms) ON runs TO larp_archive, larp_uploader;
GRANT SELECT,INSERT,UPDATE ON archive_clock,archive_outbox TO larp_archive;
GRANT SELECT ON runs,audit_events,audit_chunks TO larp_uploader;
-- Re-running this script must also remove the earlier broad table privilege.
REVOKE UPDATE ON audit_chunks FROM larp_uploader;
GRANT UPDATE (status,attempts,next_ms,last_code,acknowledgement) ON audit_chunks TO larp_uploader;
-- No DELETE/DDL, trading command creation or wallet state mutation grants.
-- Primary/standby/signer roles require owner-specific grants during integration.

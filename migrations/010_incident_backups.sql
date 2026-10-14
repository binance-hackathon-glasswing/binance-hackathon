-- IDEA-049 D-FND-008: the journal is uploaded daily and after any incident (declared, proposal "Logs"). A backup
-- records the run version it covers, so maintenance can tell whether an incident (RESTART, HALT) committed since the
-- latest backup still needs its own upload. NULL for backups queued before this migration.
ALTER TABLE archive_outbox ADD COLUMN IF NOT EXISTS covers_sequence bigint;

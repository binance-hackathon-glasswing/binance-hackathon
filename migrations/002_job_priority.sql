ALTER TABLE jobs ADD COLUMN IF NOT EXISTS priority integer NOT NULL DEFAULT 100;
CREATE INDEX IF NOT EXISTS ready_jobs ON jobs(run_id,lane,status,priority,next_ms);
CREATE INDEX IF NOT EXISTS ready_audit_chunks ON audit_chunks(run_id,status,next_ms);

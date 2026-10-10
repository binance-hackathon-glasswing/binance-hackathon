-- RT18 #6: the upload-deadline query filters on the event timestamp without loading
-- audit documents. Existing rows take the value from their own canonical document.
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS timestamp_ms bigint;
UPDATE audit_events SET timestamp_ms=(convert_from(document,'UTF8')::jsonb->>'timestamp_ms')::bigint
    WHERE timestamp_ms IS NULL;
ALTER TABLE audit_events ALTER COLUMN timestamp_ms SET NOT NULL;
-- RT18 #9: Anchor.v1 was never written; the live anchor is Anchor.v2 in archive_outbox.
DROP TABLE IF EXISTS anchors;

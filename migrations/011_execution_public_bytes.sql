-- #23 acceptance 2 (IDEA-042 V8, IDEA-049-D WR-D2): the archive role may SELECT execution_records and
-- execution_journal, because the daily backup exports them, so neither table may ever hold signed transaction bytes.
-- Those bytes live only in execution_signatures.signed, which the archive role cannot read (roles.sql).
-- ExecutionStore.commit already refuses such a write (larp.storage.backup.without_signed_bytes, which also finds a
-- whole RLP-encoded signed transaction under any key). This trigger is the database's own guard for every writer:
-- a stored state or event must be UTF-8 JSON with no non-null signed-bytes field at any depth. The one value
-- allowed in such a field is backup.SIGNED_MARKER, which a restore writes in place of legacy bytes.
-- Limit: the trigger matches field names only. A signed transaction stored as a bare hex string under another key
-- is caught by ExecutionStore.commit and by the backup export, not here.
CREATE OR REPLACE FUNCTION execution_public_bytes_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    value jsonb;
BEGIN
    BEGIN
        -- jsonb refuses the escape \u0000, which a legitimate state may hold (canonical JSON escapes NUL). Only this
        -- check's copy is changed, never the stored bytes; the result is still valid JSON whether the sequence is an
        -- escape or follows an escaped backslash.
        value := replace(convert_from(decode(substr(to_jsonb(NEW) ->> TG_ARGV[0], 3), 'hex'), 'UTF8'),
                         '\u0000', '\u0020')::jsonb;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION '%.% must be JSON without signed transaction bytes (#23)', TG_TABLE_NAME, TG_ARGV[0]
            USING ERRCODE = 'check_violation';
    END;
    IF jsonb_path_exists(value,
            'lax $.** ? ((@.raw_hex != null && @.raw_hex != $m) || (@.signedTransaction != null && @.signedTransaction != $m)'
            ' || (@.signed_transaction != null && @.signed_transaction != $m)'
            ' || (@.rawTransaction != null && @.rawTransaction != $m)'
            ' || (@.raw_transaction != null && @.raw_transaction != $m))',
            jsonb_build_object('m', '[redacted: signed bytes are never backed up (#23)]')) THEN
        RAISE EXCEPTION '%.% must be JSON without signed transaction bytes (#23)', TG_TABLE_NAME, TG_ARGV[0]
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
DROP TRIGGER IF EXISTS execution_records_public_bytes ON execution_records;
CREATE TRIGGER execution_records_public_bytes BEFORE INSERT OR UPDATE OF state ON execution_records
    FOR EACH ROW EXECUTE FUNCTION execution_public_bytes_check('state');
DROP TRIGGER IF EXISTS execution_journal_public_bytes ON execution_journal;
CREATE TRIGGER execution_journal_public_bytes BEFORE INSERT OR UPDATE OF event ON execution_journal
    FOR EACH ROW EXECUTE FUNCTION execution_public_bytes_check('event');

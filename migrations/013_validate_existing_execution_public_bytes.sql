-- ALLPR-R108: fail closed when rows accepted before 012 contain forbidden signed-byte fields.
-- Reuse the installed trigger on a transaction-local copy; never UPDATE or rewrite journal bytes.
CREATE TEMP TABLE larp_execution_public_validation (payload bytea) ON COMMIT DROP;
CREATE TRIGGER larp_validate_execution_public_bytes BEFORE INSERT ON larp_execution_public_validation
    FOR EACH ROW EXECUTE FUNCTION execution_public_bytes_check('payload');
INSERT INTO larp_execution_public_validation(payload) SELECT state FROM execution_records;
TRUNCATE larp_execution_public_validation;
INSERT INTO larp_execution_public_validation(payload) SELECT event FROM execution_journal;
DROP TABLE larp_execution_public_validation;

-- IDEA-049-D PR99-RV1: preserve migration 011 and repair its trigger for existing installations.
-- JSONPath comparisons with a string do not reject object/array values. Walk the JSON tree and
-- check field types explicitly. Use json rather than jsonb so duplicate keys cannot hide bytes.
-- Only JSON null and the exact restore-marker string are allowed under the five signed-byte keys.
-- This remains a field-name guard: alternate keys/encodings are not a complete archive-read boundary.
CREATE OR REPLACE FUNCTION execution_public_bytes_check() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    value json;
    pending json[];
    field record;
    element json;
BEGIN
    BEGIN
        -- Preserve 011's handling of legitimate NUL escapes in the check's copy; stored bytes are unchanged.
        value := replace(convert_from(decode(substr(to_jsonb(NEW) ->> TG_ARGV[0], 3), 'hex'), 'UTF8'),
                         '\u0000', '\u0020')::json;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION '%.% must be JSON without signed transaction bytes (#23)', TG_TABLE_NAME, TG_ARGV[0]
            USING ERRCODE = 'check_violation';
    END;
    pending := ARRAY[value];
    WHILE cardinality(pending) > 0 LOOP
        value := pending[cardinality(pending)];
        pending := trim_array(pending, 1);
        IF json_typeof(value) = 'object' THEN
            FOR field IN SELECT * FROM json_each(value) LOOP
                IF field.key IN ('raw_hex', 'signedTransaction', 'signed_transaction',
                                 'rawTransaction', 'raw_transaction')
                   AND json_typeof(field.value) <> 'null'
                   AND NOT (json_typeof(field.value) = 'string'
                            AND field.value #>> '{}' = '[redacted: signed bytes are never backed up (#23)]') THEN
                    RAISE EXCEPTION '%.% must be JSON without signed transaction bytes (#23)', TG_TABLE_NAME, TG_ARGV[0]
                        USING ERRCODE = 'check_violation';
                END IF;
                pending := array_append(pending, field.value);
            END LOOP;
        ELSIF json_typeof(value) = 'array' THEN
            FOR element IN SELECT * FROM json_array_elements(value) LOOP
                pending := array_append(pending, element);
            END LOOP;
        END IF;
    END LOOP;
    RETURN NEW;
END
$$;

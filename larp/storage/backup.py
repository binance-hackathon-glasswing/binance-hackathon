"""Consistent logical export and quarantined restore, including all outboxes.

Exports belong in protected artifact storage, never Git. External hourly anchor
(Anchor.v2, written by Maintenance) and signer epoch are required before any restored
live authority can be considered.
"""

import base64
from decimal import Decimal

from larp.contracts import Document
from larp.storage.postgres import IntegrityError,doc,digest

TABLES=('runs','events','reservations','commands','rounds','audit_events','audit_chunks','swap_owners','jobs','command_checks',
        # IDEA-042 item 5 and §4 X2: process sessions and the execution service's store recover with the journal
        # (FK order: records before their journal).
        'process_sessions','execution_records','execution_journal','execution_signatures','execution_observations',
        # IDEA-047 S01: signing requests and refusals (FK order: attempts, requests, refusals).
        'signing_attempts','signing_requests','signing_refusals')
# Payloads of earlier backups must never be embedded recursively in new backups.
# These delivery tables are rebuilt only after quarantine/reconciliation and a new
# archive namespace; remote object versions/receipts are retained independently.
MAINTENANCE_TABLES=('archive_clock','archive_outbox')
# Signed transaction bytes never leave the database (IDEA-042 V8): anyone holding a backup could otherwise broadcast
# a swap the runtime had abandoned. The archive role cannot read the column; the export writes this marker instead,
# so a restored registry lookup fails its digest check (closed) rather than returning usable bytes.
REDACTED={'execution_signatures':{'signed':b'{"redacted":"signed bytes are never backed up (IDEA-042 V8)"}'}}


def select_sql(db,table):
    """The export query for `table`: every column, with redacted columns replaced by their marker."""
    # Column names from the catalogue: `SELECT *` would need the redacted column's privilege.
    columns=[r[0] for r in db.execute('SELECT attname FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 '
                                       'AND NOT attisdropped ORDER BY attnum',(table,))]
    redacted=REDACTED.get(table,{})
    names=','.join(f'%s::bytea AS {c}' if c in redacted else c for c in columns)
    return f'SELECT {names} FROM {table} ORDER BY 1,2',[redacted[c] for c in columns if c in redacted]


def export(store):
    data={}
    with store.transaction() as db:
        # Must precede first query; SET LOCAL statements do not start a snapshot.
        db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        for run_id, in db.execute('SELECT run_id FROM runs').fetchall():
            store._verify(db,run_id,store._run(db,run_id,lock=False))
        for table in TABLES:
            cursor=db.execute(*select_sql(db,table))
            columns=[d.name for d in cursor.description]
            rows=[]
            for row in cursor:
                rows.append([{'bytes':base64.b64encode(bytes(v)).decode('ascii')} if isinstance(v,(bytes,memoryview))
                             else int(v) if isinstance(v,Decimal) else v for v in row])
            data[table]=dict(columns=columns,rows=rows)
    payload=doc(data)
    return doc(dict(schema='Backup.v1',sha256=digest(payload.payload),tables=data))


def restore(store,backup):
    b=backup.read()
    if b.get('schema')!='Backup.v1' or digest(doc(b['tables']).payload)!=b['sha256']:
        raise IntegrityError('Backup checksum mismatch')
    if set(b['tables'])!=set(TABLES):
        raise IntegrityError('Incomplete backup')
    with store.transaction() as db:
        for table in MAINTENANCE_TABLES:
            if db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]:
                raise IntegrityError('Restore requires empty maintenance tables')
        for table in TABLES:
            if db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]:
                raise IntegrityError('Restore requires an empty target database')
            item=b['tables'][table]
            columns=[d.name for d in db.execute(f'SELECT * FROM {table} LIMIT 0').description]
            if columns!=item['columns']:
                raise IntegrityError('Backup schema mismatch')
            for row in item['rows']:
                values=[base64.b64decode(v['bytes'],validate=True) if isinstance(v,dict) else v for v in row]
                db.execute(f'INSERT INTO {table}({",".join(columns)}) VALUES({",".join(["%s"]*len(values))})',values)
        for run_id, in db.execute('SELECT run_id FROM runs').fetchall():
            store._verify(db,run_id,store._run(db,run_id))
        db.execute('UPDATE runs SET quarantined=true,epoch=epoch+1')
        db.execute("SELECT setval(pg_get_serial_sequence('command_checks','check_id'), "
                   "COALESCE((SELECT max(check_id) FROM command_checks),1), "
                   "EXISTS(SELECT 1 FROM command_checks))")

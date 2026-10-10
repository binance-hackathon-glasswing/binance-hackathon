"""Consistent logical export and quarantined restore, including all outboxes.

Exports belong in protected artifact storage, never Git. External hourly anchor
and signer epoch are required before any restored live authority can be considered.
"""

import base64
from decimal import Decimal

from larp.contracts import Document
from larp.storage.postgres import IntegrityError,doc,digest

TABLES=('runs','events','reservations','commands','rounds','audit_events','audit_chunks','swap_owners','jobs','anchors','command_checks')
# Payloads of earlier backups must never be embedded recursively in new backups.
# These delivery tables are rebuilt only after quarantine/reconciliation and a new
# archive namespace; remote object versions/receipts are retained independently.
MAINTENANCE_TABLES=('archive_clock','archive_outbox')


def export(store):
    data={}
    with store.transaction() as db:
        # Must precede first query; SET LOCAL statements do not start a snapshot.
        db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        for table in TABLES:
            cursor=db.execute(f'SELECT * FROM {table} ORDER BY 1,2')
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


def anchor(store,run_id,receiver,now_ms):
    """Receiver must durably write immutable anchor ID; receipt is kept locally."""
    current=store.load(run_id).read()
    store.verify(run_id,minimum_version=current['version'],anchored_head=current['head'])
    value=doc(dict(schema='Anchor.v1',run_id=run_id,sequence=current['version'],head=current['head'],
                   owner_epoch=current['epoch']))
    receipt=receiver.deliver(value)
    r=receipt.read()
    if r.get('status')!='STORED' or r.get('head')!=current['head']:
        raise IntegrityError('Anchor not acknowledged')
    with store.transaction() as db:
        db.execute('INSERT INTO anchors VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                   (run_id,current['version'],current['head'],now_ms,receipt.payload))
    return value

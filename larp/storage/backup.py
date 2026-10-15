"""Consistent logical export and quarantined restore, including all outboxes.

Exports belong in protected artifact storage, never Git. External hourly anchor
(Anchor.v2, written by Maintenance) and signer epoch are required before any restored
live authority can be considered.
"""

import base64
from decimal import Decimal
import json
import re

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
# Signed bytes inside any other exported value (#23, IDEA-049-D WR-D2). New execution state holds none (C-FND-010), but
# a legacy or forged row may: a signed-bytes field, or a signed transaction under any key. Such a value is replaced by
# this marker and every stored hash is kept, so the restored record fails its state/journal check (closed), as the
# signature marker does. Whole values that cannot be parsed are replaced where execution state is kept.
SIGNED_MARKER='[redacted: signed bytes are never backed up (#23)]'
SIGNED_KEYS=frozenset({'raw_hex','signedTransaction','signed_transaction','rawTransaction','raw_transaction'})
OPAQUE={'execution_records':'state','execution_journal':'event'}
HEX=re.compile(r'(?:0[xX])?((?:[0-9a-fA-F]{2}){80,})')  # at least 80 bytes: shorter than any signed transaction


def _rlp(data,i):
    """(item, end) of the RLP item at `i`: bytes, or a list of items. ValueError if it runs past `data`."""
    if i>=len(data):
        raise ValueError('rlp')
    b=data[i]
    if b<0x80:
        return data[i:i+1],i+1
    if b<0xc0:
        start,n=(i+1,b-0x80) if b<0xb8 else (i+1+b-0xb7,int.from_bytes(data[i+1:i+1+b-0xb7],'big'))
        if start+n>len(data):
            raise ValueError('rlp')
        return data[start:start+n],start+n
    start,n=(i+1,b-0xc0) if b<0xf8 else (i+1+b-0xf7,int.from_bytes(data[i+1:i+1+b-0xf7],'big'))
    end,items,j=start+n,[],start
    if end>len(data):
        raise ValueError('rlp')
    while j<end:
        item,j=_rlp(data,j)
        items.append(item)
    if j!=end:
        raise ValueError('rlp')
    return items,end


def signed_transaction(data):
    """True if `data` is a whole RLP-encoded signed transaction (legacy, or typed 1-4) with a nonzero r and s."""
    typed=bool(data) and data[0] in (1,2,3,4)
    body=data[1:] if typed else data
    try:
        items,end=_rlp(body,0)
    except ValueError:
        return False
    if end!=len(body) or type(items) is not list or len(items)<(11 if typed else 9) or (not typed and len(items)!=9):
        return False
    return all(type(x) is bytes and 0<len(x)<=32 for x in items[-2:])


def _strip(value):
    """(value without signed bytes, changed)."""
    if isinstance(value,dict):
        out,changed={},False
        for key,item in value.items():
            if key in SIGNED_KEYS and item is not None and item!=SIGNED_MARKER:
                out[key],changed=SIGNED_MARKER,True
            else:
                out[key],c=_strip(item)
                changed=changed or c
        return out,changed
    if isinstance(value,list):
        pairs=[_strip(item) for item in value]
        return [v for v,_ in pairs],any(c for _,c in pairs)
    if isinstance(value,str):
        match=HEX.fullmatch(value)
        if match and signed_transaction(bytes.fromhex(match.group(1))):
            return SIGNED_MARKER,True
    return value,False


def without_signed_bytes(table,column,raw):
    """`raw` unchanged when it holds no signed bytes; otherwise the same document with them replaced by the marker."""
    try:
        value=json.loads(bytes(raw))
    except (ValueError,UnicodeDecodeError):
        if OPAQUE.get(table)==column:
            return json.dumps({'redacted':SIGNED_MARKER,'reason':'unparseable execution value'},
                              sort_keys=True,separators=(',',':')).encode()
        return raw
    value,changed=_strip(value)
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode() if changed else raw


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
                rows.append([{'bytes':base64.b64encode(without_signed_bytes(table,c,bytes(v))).decode('ascii')}
                             if isinstance(v,(bytes,memoryview)) else int(v) if isinstance(v,Decimal) else v
                             for c,v in zip(columns,row)])
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
                # A backup written before #23's fix may still hold signed bytes: they never reach the target database.
                values=[without_signed_bytes(table,c,base64.b64decode(v['bytes'],validate=True))
                        if isinstance(v,dict) else v for c,v in zip(columns,row)]
                db.execute(f'INSERT INTO {table}({",".join(columns)}) VALUES({",".join(["%s"]*len(values))})',values)
        for run_id, in db.execute('SELECT run_id FROM runs').fetchall():
            store._verify(db,run_id,store._run(db,run_id))
        db.execute('UPDATE runs SET quarantined=true,epoch=epoch+1')
        db.execute("SELECT setval(pg_get_serial_sequence('command_checks','check_id'), "
                   "COALESCE((SELECT max(check_id) FROM command_checks),1), "
                   "EXISTS(SELECT 1 FROM command_checks))")

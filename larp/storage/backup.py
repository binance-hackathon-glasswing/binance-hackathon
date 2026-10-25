"""Consistent logical export and quarantined restore, including all outboxes.

Exports belong in protected artifact storage, never Git. External hourly anchor
(Anchor.v2, written by Maintenance) and signer epoch are required before any restored
live authority can be considered.

Backup.v1 (`export`/`restore`) is one in-memory JSON document of every table. The archive job writes Backup.v2
segments (`export_segment`/`restore_chain`, IDEA-094): the journal rows after the newest acknowledged backup plus
every other table, streamed through gzip under a byte bound, without the copies the journal already holds.
"""

import base64
from collections import namedtuple
from decimal import Decimal
import gzip
import hashlib
import io
import json
import re

from larp.contracts import ContractError,Document
from larp.storage.postgres import FIELDS,OUTBOXES,IntegrityError,doc,digest

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


# --- Backup.v2 segments (IDEA-094) ------------------------------------------------------------------------------
# A Backup.v1 export of a 14-day journal does not fit the archive host: every journal row carries full copies of the
# run's projection and states, so the journal grows faster than linearly. A segment holds:
#   - the journal rows after its base (the newest acknowledged backup), each row's projection/policy_state/
#     execution_state as a delta against the previous row of the segment;
#   - every other table in full, except value columns the journal already holds (DERIVED), which are written as
#     their SHA-256 and rebuilt from the journal on restore.
# restore_chain rebuilds exact bytes; the journal hash chain and outbox verification (`_verify`) are the check, so a
# reconstruction error fails closed. Lines are canonical JSON through a deterministic gzip stream (mtime 0).
SEGMENT='Backup.v2'
GZIP_MAGIC=b'\x1f\x8b'
DERIVED={table:column for table,_,column,_ in OUTBOXES}|{'audit_chunks':'body'}
EXPORT_FETCH_ROWS={'events':1}  # other tables: TABLE_FETCH_ROWS; one journal row can be megabytes
TABLE_FETCH_ROWS=64
Segment=namedtuple('Segment','payload through events')


class BackupOverBound(ContractError):
    """The compressed segment would exceed the configured bound; nothing is truncated or queued."""


def _line(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')


def _same(a,b):
    """JSON equality that keeps true and 1 apart (Python's == does not)."""
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return a.keys()==b.keys() and all(_same(v,b[k]) for k,v in a.items())
    if type(a) is list:
        return len(a)==len(b) and all(_same(x,y) for x,y in zip(a,b))
    return a==b


def _diff(a,b):
    """A patch turning JSON value `a` into `b`: {'=': b}, {'+': appended list items} or {'o': object changes}."""
    if type(a) is dict and type(b) is dict:
        changes,gone={},sorted(k for k in a if k not in b)
        for key,value in b.items():
            if key not in a:
                changes[key]={'=':value}
            elif not _same(a[key],value):
                changes[key]=_diff(a[key],value)
        return {'o':dict(**({'-':gone} if gone else {}),**({'~':changes} if changes else {}))}
    if type(a) is list and type(b) is list and len(b)>len(a) and _same(a,b[:len(a)]):
        return {'+':b[len(a):]}
    return {'=':b}


def _apply(a,patch):
    if type(patch) is not dict or len(patch)!=1:
        raise IntegrityError('Malformed backup delta')
    (kind,value),=patch.items()
    if kind=='=':
        return value
    if kind=='+' and type(a) is list and type(value) is list:
        return a+value
    if kind!='o' or type(a) is not dict or type(value) is not dict or set(value)-{'-','~'}:
        raise IntegrityError('Malformed backup delta')
    out=dict(a)
    for key in value.get('-',[]):
        if key not in out:
            raise IntegrityError('Malformed backup delta')
        del out[key]
    for key,sub in value.get('~',{}).items():
        if key not in out and (type(sub) is not dict or set(sub)!={'='}):
            raise IntegrityError('Malformed backup delta')
        out[key]=_apply(out.get(key),sub)
    return out


class _Writer:
    """Canonical JSON lines into a deterministic gzip stream; refused as soon as the compressed size passes the bound."""

    def __init__(self,max_bytes):
        if type(max_bytes) is not int or max_bytes<1:
            raise ContractError('Invalid backup bound')
        self.max_bytes,self.out,self.hash,self.lines=max_bytes,io.BytesIO(),hashlib.sha256(),0
        self.stream=gzip.GzipFile(fileobj=self.out,mode='wb',compresslevel=6,mtime=0)

    def write(self,value):
        raw=_line(value)+b'\n'
        self.hash.update(raw)
        self.lines+=1
        self.stream.write(raw)
        if self.out.tell()>self.max_bytes:
            raise BackupOverBound('Backup exceeds configured bound; no truncation performed')

    def close(self,trailer):
        self.stream.write(_line(dict(end=dict(trailer,lines=self.lines,sha256=self.hash.hexdigest())))+b'\n')
        self.stream.close()
        payload=self.out.getvalue()
        if len(payload)>self.max_bytes:
            raise BackupOverBound('Backup exceeds configured bound; no truncation performed')
        return payload


def _columns(db,table):
    return [r[0] for r in db.execute('SELECT attname FROM pg_attribute WHERE attrelid=%s::regclass AND attnum>0 '
                                     'AND NOT attisdropped ORDER BY attnum',(table,))]


def _verified(store,db,run_id):
    """Verify this run in the export snapshot. A checkpoint from this process's own earlier full verification (the
    hour's anchor) is continued when the snapshot still extends it, so a daily backup does not re-hash the whole
    journal a second time; otherwise the verification is full."""
    run=store._run(db,run_id,lock=False)
    with store._checkpoint_lock:
        base=store._checkpoints.get(run_id)
    if base is not None and not store._continues(db,run_id,run,base):
        base=None
    store._verify(db,run_id,run,base)
    return run


def export_segment(store,*,max_bytes,base=None):
    """One Backup.v2 segment of every run, after `base` = {sha256, slot_ms, through: {run_id: sequence}} or None."""
    if base is not None and (type(base) is not dict or set(base)!={'sha256','slot_ms','through'}
                             or type(base['through']) is not dict):
        raise ContractError('Invalid backup base')
    writer,counts,ranges,through,heads=_Writer(max_bytes),{},{},{},{}
    with store.transaction() as db:
        db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        for run_id, in db.execute('SELECT run_id FROM runs ORDER BY run_id').fetchall():
            run=_verified(store,db,run_id)
            through[run_id],heads[run_id]=run['version'],run['head']
        after={run_id:(base['through'].get(run_id,0) if base else 0) for run_id in through}
        if base and (set(base['through'])!=set(through) or any(after[r]>through[r] for r in through)):
            raise IntegrityError('Backup base does not cover this journal')
        writer.write(dict(schema=SEGMENT,base=base,tables=list(TABLES)))
        for table in TABLES:
            columns=_columns(db,table)
            redacted,derived=REDACTED.get(table,{}),DERIVED.get(table)
            select=','.join(f'%s::bytea AS {c}' if c in redacted else
                            f"encode(sha256({c}),'hex') AS {c}" if c==derived else c for c in columns)
            params=[redacted[c] for c in columns if c in redacted]
            if table=='events':
                sql=(f'SELECT {select} FROM events WHERE sequence>(%s::jsonb->>run_id)::bigint '
                     'ORDER BY run_id,sequence')
                params.append(json.dumps(after))
            else:
                sql=f'SELECT {select} FROM {table} ORDER BY 1,2'
            writer.write(dict(table=table,columns=columns))
            counts[table],previous=0,{}
            with db.cursor(name='larp_backup_'+table,binary=True) as cursor:  # bytea as bytes, not hex text
                cursor.itersize=EXPORT_FETCH_ROWS.get(table,TABLE_FETCH_ROWS)
                cursor.execute(sql,params)
                for row in cursor:
                    cells=[]
                    for column,value in zip(columns,row):
                        if column==derived:
                            cells.append({'journal':value})
                        elif table=='events' and column=='batch':
                            cells.append(_batch_cell(bytes(value),previous,row[0]))
                        elif isinstance(value,(bytes,memoryview)):
                            raw=without_signed_bytes(table,column,bytes(value))
                            cells.append({'bytes':base64.b64encode(raw).decode('ascii')})
                        else:
                            cells.append(int(value) if isinstance(value,Decimal) else value)
                    writer.write(cells)
                    counts[table]+=1
                    if table=='events':
                        ranges.setdefault(row[0],[row[2],row[2]])[1]=row[2]
    events={run_id:ranges.get(run_id,[]) for run_id in through}
    payload=writer.close(dict(through=through,heads=heads,events=events,rows=counts))
    return Segment(payload,through,events)


def _batch_cell(raw,previous,run_id):
    """A journal batch as {'batch': {rest, full|patch}}; raw bytes when they are not plain canonical JSON."""
    redacted=without_signed_bytes('events','batch',raw)
    try:
        value=json.loads(raw)
    except ValueError:
        value=None
    if redacted!=raw or type(value) is not dict or _line(value)!=raw:
        # Signed bytes (replaced, so the restored row fails its hash check: closed) or non-canonical legacy bytes.
        previous.pop(run_id,None)
        return {'bytes':base64.b64encode(redacted).decode('ascii')}
    fields={f:value.pop(f) for f in FIELDS if f in value}
    prior=previous.get(run_id)
    previous[run_id]=fields
    if prior is None or set(prior)!=set(fields):
        return {'batch':{'rest':value,'full':fields}}
    return {'batch':{'rest':value,'patch':{f:_diff(prior[f],fields[f]) for f in fields}}}


def _read_lines(payload):
    """Parsed lines of a segment; the last is the verified trailer. IntegrityError on any malformed or altered byte."""
    if type(payload) is not bytes or payload[:2]!=GZIP_MAGIC:
        raise IntegrityError('Not a Backup.v2 segment')
    running=hashlib.sha256()
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(payload),mode='rb') as stream:
            pending=None
            for raw in stream:
                if pending is not None:
                    running.update(pending[0])
                    yield pending[1]
                value=json.loads(raw)
                pending=(raw,value)
    except (OSError,EOFError,ValueError,UnicodeDecodeError):
        raise IntegrityError('Backup.v2 segment is not readable') from None
    trailer=(pending or (b'',None))[1]
    if type(trailer) is not dict or set(trailer)!={'end'} or trailer['end'].get('sha256')!=running.hexdigest():
        raise IntegrityError('Backup.v2 segment checksum mismatch')
    yield trailer


def segment_header(payload):
    """{'base', 'tables', 'through', 'heads', 'events', 'rows', 'lines'} of a verified segment."""
    header,trailer=None,None
    for value in _read_lines(payload):
        if header is None:
            header=value
        trailer=value
    if type(header) is not dict or header.get('schema')!=SEGMENT or header.get('tables')!=list(TABLES):
        raise IntegrityError('Not a Backup.v2 segment of this schema')
    end=trailer['end']
    return dict(base=header['base'],tables=header['tables'],through=end.get('through'),heads=end.get('heads'),
                events=end.get('events'),rows=end.get('rows'),lines=end.get('lines'))


def _chain(payloads):
    """The provided segments ordered from the base-less one to the target; every one must be on that path."""
    info={}
    for payload in payloads:
        key=digest(payload) if type(payload) is bytes else None
        if key in info:
            raise IntegrityError('Backup segment provided twice')
        info[key]=segment_header(payload),payload
    referenced={h['base']['sha256'] for h,_ in info.values() if h['base']}
    targets=[k for k in info if k not in referenced]
    if len(targets)!=1:
        raise IntegrityError('Backup segments do not form one chain')
    chain,key=[],targets[0]
    while key is not None:
        if key not in info:
            raise IntegrityError('Backup chain is missing a base segment')
        header,payload=info[key]
        chain.append((header,payload))
        key=header['base']['sha256'] if header['base'] else None
    if len(chain)!=len(info):
        raise IntegrityError('Backup segment outside the restored chain')
    chain.reverse()
    for (parent,_),(child,_) in zip(chain,chain[1:]):
        if child['base']['through']!=parent['through']:
            raise IntegrityError('Backup segment does not continue its base')
    for header,_ in chain:
        after=(header['base'] or {}).get('through',{})
        if set(header['events'])!=set(header['through']):
            raise IntegrityError('Backup segment does not continue its base')
        for run_id,span in header['events'].items():
            first=after.get(run_id,0)
            if (span and span!=[first+1,header['through'][run_id]]) or (not span and header['through'][run_id]!=first):
                raise IntegrityError('Backup segment does not continue its base')
    return chain


def restore_chain(store,payloads):
    """Restore a Backup.v2 chain (any order) into an empty database; every restored run is quarantined."""
    chain=_chain(payloads)
    with store.transaction() as db:
        for table in MAINTENANCE_TABLES+TABLES:
            if db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]:
                raise IntegrityError('Restore requires an empty target database')
        schema={t:[d.name for d in db.execute(f'SELECT * FROM {t} LIMIT 0').description] for t in TABLES}
        target=chain[-1][1]
        # FK order: the target's runs, the journal from every segment (oldest first), then the target's other tables;
        # outbox values held by the journal last, rebuilt from it.
        passes=[(target,lambda t:t=='runs')]+[(payload,lambda t:t=='events') for _,payload in chain]+[
            (target,lambda t:t not in ('runs','events'))]
        pending={}
        for payload,wanted in passes:
            table,previous=None,{}
            for value in _read_lines(payload):
                if type(value) is dict:
                    if 'table' in value:
                        table=value['table']
                        if value.get('columns')!=schema.get(table):
                            raise IntegrityError('Backup schema mismatch')
                    continue
                if table is None or not wanted(table):
                    continue
                _restore_row(db,table,schema[table],value,previous,pending)
        _restore_derived(db,pending)
        for run_id, in db.execute('SELECT run_id FROM runs').fetchall():
            store._verify(db,run_id,store._run(db,run_id))
        db.execute('UPDATE runs SET quarantined=true,epoch=epoch+1')
        db.execute("SELECT setval(pg_get_serial_sequence('command_checks','check_id'), "
                   "COALESCE((SELECT max(check_id) FROM command_checks),1), "
                   "EXISTS(SELECT 1 FROM command_checks))")


def _restore_row(db,table,columns,cells,previous,pending):
    if type(cells) is not list or len(cells)!=len(columns):
        raise IntegrityError('Malformed backup row')
    values=[]
    for column,cell in zip(columns,cells):
        if type(cell) is not dict:
            values.append(cell)
        elif set(cell)=={'bytes'}:
            values.append(without_signed_bytes(table,column,base64.b64decode(cell['bytes'],validate=True)))
        elif set(cell)=={'journal'} and DERIVED.get(table)==column:
            values.append(cell)
        elif set(cell)=={'batch'} and table=='events' and column=='batch':
            values.append(_rebuild(cell['batch'],previous,dict(zip(columns,cells))['run_id']))
        else:
            raise IntegrityError('Malformed backup cell')
    if table=='events' and type(cells[columns.index('batch')]) is dict and 'bytes' in cells[columns.index('batch')]:
        previous.pop(dict(zip(columns,cells))['run_id'],None)
    if table in DERIVED:
        row=dict(zip(columns,values))
        key=(table,row['run_id'],row['event_id'],row['chunk_index']) if table=='audit_chunks' else \
            (table,row['run_id'],row[_ID[table]])
        if key in pending:
            raise IntegrityError('Duplicate backup row')
        pending[key]=row
        return
    db.execute(f'INSERT INTO {table}({",".join(columns)}) VALUES({",".join(["%s"]*len(values))})',values)


_ID={table:id_column for table,id_column,_,_ in OUTBOXES}


def _rebuild(cell,previous,run_id):
    if type(cell) is not dict or type(cell.get('rest')) is not dict or len(cell)!=2:
        raise IntegrityError('Malformed backup batch')
    if 'full' in cell:
        fields=cell['full']
    elif 'patch' in cell and run_id in previous and set(cell['patch'])==set(previous[run_id]):
        fields={f:_apply(previous[run_id][f],p) for f,p in cell['patch'].items()}
    else:
        raise IntegrityError('Malformed backup batch')
    if type(fields) is not dict or set(fields)-set(FIELDS) or set(fields)&set(cell['rest']):
        raise IntegrityError('Malformed backup batch')
    previous[run_id]=fields
    return _line(dict(cell['rest'],**fields))


def _restore_derived(db,pending):
    """Insert the outbox rows whose values the journal holds, rebuilt from the restored journal, in FK order."""
    done=set()
    with db.cursor(name='larp_restore_journal',binary=True) as cursor:
        cursor.itersize=1
        cursor.execute('SELECT run_id,batch FROM events ORDER BY run_id,sequence')
        for run_id,raw in cursor:
            b=json.loads(bytes(raw))
            for table,id_column,column,key in OUTBOXES:
                for item in b.get(key,[]):
                    ident=(table,run_id,item[id_column])
                    if ident in done:
                        continue
                    row=pending.pop(ident,None)
                    if row is None:
                        continue  # another check (_verify) refuses an outbox row missing from the database
                    _insert_derived(db,table,column,row,doc(item).payload)
                    done.add(ident)
                    if table=='audit_events':
                        for index,chunk in enumerate(item['chunks']):
                            part=pending.pop(('audit_chunks',run_id,item['event_id'],index),None)
                            if part is not None:
                                _insert_derived(db,'audit_chunks','body',part,chunk.encode('utf-8'))
    if pending:
        raise IntegrityError('Backup row has no journal source')


def _insert_derived(db,table,column,row,raw):
    value=without_signed_bytes(table,column,raw)
    if digest(value)!=row[column]['journal']:
        raise IntegrityError('Outbox/job definition differs from journal')
    row=dict(row,**{column:value})
    db.execute(f'INSERT INTO {table}({",".join(row)}) VALUES({",".join(["%s"]*len(row))})',list(row.values()))

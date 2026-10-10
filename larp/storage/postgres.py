"""One transactional authority for ordering and reservations.

No network call is made inside a wallet transaction except PostgreSQL itself.
This store does not validate trading economics or grant a live signing capability.
"""

from contextlib import contextmanager
import hashlib
from pathlib import Path
import threading

from larp.contracts import ContractError, Document

ZERO = '0' * 64
FIELDS = ('projection','policy_state','execution_state')
# Outbox tables whose rows must equal the journal: (table, id column, value column, batch key).
OUTBOXES = (('audit_events','event_id','document','audit'),('commands','command_id','payload','commands'),
            ('jobs','job_id','document','jobs'))


class Conflict(ContractError):
    pass


class IntegrityError(ContractError):
    pass


class Unavailable(RuntimeError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def doc(value):
    return Document.from_dict(value)


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ContractError('Invalid integer')
    return value


class PostgresStore:
    def __init__(self, dsn):
        self._dsn = dsn
        # Per-process verified position per run (see verified_snapshot). Never persisted:
        # a new process starts with a full verification.
        self._checkpoints = {}
        self._checkpoint_lock = threading.Lock()

    @contextmanager
    def transaction(self):
        import psycopg
        try:
            with psycopg.connect(self._dsn, connect_timeout=5) as connection:
                connection.execute("SET LOCAL synchronous_commit = on")
                connection.execute("SET LOCAL lock_timeout = '5s'")
                connection.execute("SET LOCAL statement_timeout = '15s'")
                yield connection
        except psycopg.IntegrityError as exc:
            # A constraint violation is deterministic: retrying the same write fails
            # again, so it is not reported as a transient outage. Only the SQLSTATE and
            # constraint name are kept; server messages can echo row data.
            raise IntegrityError('Database constraint rejected the transaction: '
                                 f'{exc.sqlstate} {exc.diag.constraint_name}') from None
        except psycopg.Error as exc:
            # DSNs and server messages can contain credentials; don't echo them.
            raise Unavailable('Database transaction failed; signing blocked') from None

    def migrate(self):
        directory = Path(__file__).resolve().parents[2] / 'migrations'
        with self.transaction() as db:
            db.execute('SELECT pg_advisory_xact_lock(28001)')
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations(name text PRIMARY KEY,sha256 text NOT NULL)')
            for sql in sorted(directory.glob('*.sql')):
                source=sql.read_text(encoding='utf-8').replace('\r\n','\n')
                checksum=digest(source.encode('utf-8'))
                row=db.execute('SELECT sha256 FROM schema_migrations WHERE name=%s',(sql.name,)).fetchone()
                if row and row[0]!=checksum:
                    raise IntegrityError('Applied migration changed')
                if not row:
                    db.execute(source)
                    db.execute('INSERT INTO schema_migrations VALUES(%s,%s)',(sql.name,checksum))

    def initialize(self, run_id, wallet_id, chain_id, projection, *, mode='offline'):
        """New runs start quarantined. Caller must explicitly attest offline mode."""
        if not run_id or not wallet_id or type(projection) is not Document:
            raise ContractError('Invalid run identity/projection')
        integer(chain_id, 1)
        if mode not in ('offline','paper','dev','live'):
            raise ContractError('Invalid run mode')
        with self.transaction() as db:
            db.execute('INSERT INTO runs(run_id,wallet_id,chain_id,head,initial,projection,'
                       'policy_state,execution_state,mode) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                       (run_id,wallet_id,chain_id,ZERO,projection.payload,projection.payload,
                        doc({}).payload,doc({}).payload,mode))

    @staticmethod
    def _run(db, run_id, *, lock=True):
        row = db.execute('SELECT wallet_id,chain_id,version,epoch,quarantined,head,'
                         'projection,policy_state,execution_state,clock_ms,mode,initial FROM runs '
                         'WHERE run_id=%s' + (' FOR UPDATE' if lock else ''), (run_id,)).fetchone()
        if row is None:
            raise Conflict('Unknown run')
        return dict(zip(('wallet_id','chain_id','version','epoch','quarantined','head',
                         'projection','policy_state','execution_state','clock_ms','mode','initial'),row))

    def load(self, run_id):
        # Read-only: writers re-check the version under their own row lock.
        with self.transaction() as db:
            value = self._run(db,run_id,lock=False)
            for key in ('projection','policy_state','execution_state','initial'):
                value[key] = Document(bytes(value[key])).read()
            value['run_id'] = run_id
            value['reservations'] = [dict(intent_id=r[0],asset=r[1],units=int(r[2])) for r in
                db.execute('SELECT intent_id,asset,units FROM reservations WHERE run_id=%s AND units<>0 '
                           'ORDER BY intent_id,asset',(run_id,))]
            return doc(value)

    def takeover(self, run_id, expected_epoch, *, offline=False):
        """Fence old controller. Production remains quarantined until external review.

        Previously emitted signed bytes cannot be revoked. Offline does not enable
        any signer and must never be used by an execution adapter as live authority.
        """
        with self.transaction() as db:
            run = self._run(db,run_id)
            if run['epoch'] != expected_epoch:
                raise Conflict('Stale ownership')
            if offline and run['mode'] not in ('offline','paper'):
                raise Conflict('Offline takeover cannot activate a trading run')
            self._verify(db,run_id,run)
            epoch = expected_epoch + 1
            db.execute('UPDATE runs SET epoch=%s,quarantined=%s WHERE run_id=%s',
                       (epoch,not offline,run_id))
            return epoch

    def quarantine(self, run_id):
        with self.transaction() as db:
            db.execute('UPDATE runs SET quarantined=true,epoch=epoch+1 WHERE run_id=%s',(run_id,))

    @staticmethod
    def _owned(run, epoch):
        if run['quarantined'] or run['epoch'] != epoch:
            raise Conflict('Quarantined or stale owner')

    @staticmethod
    def _immutable(db, table, id_column, run_id, identity, raw, extra_columns=(), extra_values=()):
        # Table/column names are internal constants, never client inputs.
        existing = db.execute(f'SELECT payload FROM {table} WHERE run_id=%s AND {id_column}=%s',
                              (run_id,identity)).fetchone()
        if existing:
            if bytes(existing[0]) != raw:
                raise IntegrityError('Immutable command ID reused with different bytes')
            return
        columns = ('run_id',id_column,'payload') + extra_columns
        db.execute(f'INSERT INTO {table}({",".join(columns)}) '
                   f'VALUES({",".join(["%s"] * len(columns))})',
                   (run_id,identity,raw)+extra_values)

    def commit(self, batch):
        b = batch.read()
        if b.get('schema') != 'CommitBatch.v1':
            raise ContractError('Expected CommitBatch.v1')
        raw_hash = digest(batch.payload)
        verified = self.verified_snapshot(b['run_id'],full=False)
        with self.transaction() as db:
            run = self._run(db,b['run_id'])
            old = db.execute('SELECT batch_hash,receipt FROM events WHERE run_id=%s AND event_id=%s',
                             (b['run_id'],b['event_id'])).fetchone()
            if old:
                if old[0] != raw_hash:
                    raise IntegrityError('Event ID reused with different bytes')
                return Document(bytes(old[1]))
            self._owned(run,b['owner_epoch'])
            self._same_snapshot(verified,run)
            if (b['wallet_id'],b['chain_id'],b['expected_version']) != (
                    run['wallet_id'],run['chain_id'],run['version']):
                raise Conflict('Stale version or wrong wallet/chain')
            sequence = run['version'] + 1
            event_hash = digest(doc(b['event']).payload)
            head = digest(bytes.fromhex(run['head']) + bytes.fromhex(raw_hash))
            self._reserve(db,b)
            for job in b.get('jobs',[]):
                self._job(db,b['run_id'],job)
            for command in b.get('commands',[]):
                self._immutable(db,'commands','command_id',b['run_id'],command['command_id'],
                                doc(command).payload,('epoch','state_version'),(run['epoch'],sequence))
            for audit in b.get('audit',[]):
                self._audit(db,b['run_id'],audit)
            receipt = doc(dict(schema='CommitReceipt.v1',run_id=b['run_id'],event_id=b['event_id'],
                               version=sequence,head=head,event_hash=event_hash,batch_hash=raw_hash))
            db.execute('INSERT INTO events VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                       (b['run_id'],b['event_id'],sequence,batch.payload,raw_hash,event_hash,
                        run['head'],head,receipt.payload))
            db.execute('UPDATE runs SET version=%s,head=%s,projection=%s,policy_state=%s,'
                       'execution_state=%s WHERE run_id=%s',
                       (sequence,head,doc(b['projection']).payload,doc(b['policy_state']).payload,
                        doc(b['execution_state']).payload,b['run_id']))
            return receipt

    @staticmethod
    def _reserve(db,b):
        for delta in b.get('reservation_deltas',[]):
            if type(delta['units']) is not int:
                raise ContractError('Reservation units must be integers')
            row = db.execute('SELECT units FROM reservations WHERE run_id=%s AND intent_id=%s AND asset=%s',
                             (b['run_id'],delta['intent_id'],delta['asset'])).fetchone()
            units = (int(row[0]) if row else 0) + delta['units']
            if units < 0:
                raise Conflict('Reservation underflow')
            db.execute('INSERT INTO reservations VALUES(%s,%s,%s,%s) ON CONFLICT '
                       '(run_id,intent_id,asset) DO UPDATE SET units=EXCLUDED.units',
                       (b['run_id'],delta['intent_id'],delta['asset'],units))
        balances = b['projection'].get('balances',{})
        for units in balances.values():
            integer(units)
        for asset,units in db.execute('SELECT asset,sum(units) FROM reservations WHERE run_id=%s GROUP BY asset',
                                      (b['run_id'],)):
            if int(units) > balances.get(asset,0):
                raise Conflict('Insufficient settled resource for reservations')

    @staticmethod
    def _job(db,run_id,job):
        from larp.runtime.scheduler import validate_job
        validate_job(job)
        raw = doc(job).payload
        row = db.execute('SELECT document FROM jobs WHERE run_id=%s AND job_id=%s',
                         (run_id,job['job_id'])).fetchone()
        if row:
            if bytes(row[0]) != raw:
                raise IntegrityError('Job ID reused with changed definition')
            return
        count = db.execute("SELECT count(*) FROM jobs WHERE run_id=%s AND lane=%s AND status IN ('PENDING','RUNNING')",
                           (run_id,job['lane'])).fetchone()[0]
        if count >= 1024:
            raise Conflict('Lane queue capacity reached')
        db.execute('INSERT INTO jobs(run_id,job_id,document,lane,next_ms,priority) VALUES(%s,%s,%s,%s,%s,%s)',
                   (run_id,job['job_id'],raw,job['lane'],job['due_ms'],job.get('priority',100)))

    @staticmethod
    def _audit(db,run_id,audit):
        from larp.audit.protocol import verify_event
        verify_event(doc(audit))
        raw = doc(audit).payload
        row = db.execute('SELECT document FROM audit_events WHERE run_id=%s AND event_id=%s',
                         (run_id,audit['event_id'])).fetchone()
        if row:
            if bytes(row[0]) != raw:
                raise IntegrityError('Immutable audit ID changed')
            return
        for mapping in audit['swap_mappings']:
            db.execute('INSERT INTO swap_owners VALUES(%s,%s,%s,%s,%s)',
                       (run_id,mapping['tx_hash'].lower(),audit['round_id'],mapping['decision_id'],audit['version_id']))
        db.execute('INSERT INTO audit_events(run_id,event_id,round_id,document,timestamp_ms) VALUES(%s,%s,%s,%s,%s)',
                   (run_id,audit['event_id'],audit['round_id'],raw,audit['timestamp_ms']))
        for index,chunk in enumerate(audit['chunks']):
            db.execute('INSERT INTO audit_chunks(run_id,event_id,chunk_index,body) VALUES(%s,%s,%s,%s)',
                       (run_id,audit['event_id'],index,chunk.encode('utf-8')))
        db.execute("UPDATE rounds SET status='CLOSED' WHERE run_id=%s AND round_id=%s",(run_id,audit['round_id']))

    def open_round(self,run_id,round_id,request,epoch):
        with self.transaction() as db:
            self._owned(self._run(db,run_id),epoch)
            row = db.execute('SELECT request FROM rounds WHERE run_id=%s AND round_id=%s',(run_id,round_id)).fetchone()
            if row and bytes(row[0]) != request.payload:
                raise IntegrityError('Round identity changed')
            if not row:
                db.execute('INSERT INTO rounds(run_id,round_id,request) VALUES(%s,%s,%s)',(run_id,round_id,request.payload))

    def open_rounds(self,run_id):
        with self.transaction() as db:
            return [(r[0],Document(bytes(r[1]))) for r in db.execute(
                "SELECT round_id,request FROM rounds WHERE run_id=%s AND status='OPEN' ORDER BY round_id",(run_id,))]

    def receipt(self,run_id,event_id):
        with self.transaction() as db:
            row=db.execute('SELECT receipt FROM events WHERE run_id=%s AND event_id=%s',(run_id,event_id)).fetchone()
            return Document(bytes(row[0])) if row else None

    def event(self,run_id,event_id):
        with self.transaction() as db:
            row=db.execute('SELECT batch FROM events WHERE run_id=%s AND event_id=%s',(run_id,event_id)).fetchone()
            return Document(bytes(row[0])).read()['event'] if row else None

    def command(self,run_id,command_id,epoch,now_ms):
        verified=self.verified_snapshot(run_id,full=False)
        with self.transaction() as db:
            run = self._run(db,run_id)
            self._owned(run,epoch)
            self._same_snapshot(verified,run)
            row = db.execute('SELECT payload,epoch,state_version,status FROM commands WHERE run_id=%s AND command_id=%s',
                             (run_id,command_id)).fetchone()
            if not row or row[1] != epoch or row[2] != run['version'] or row[3] != 'PENDING':
                raise Conflict('Command needs current reauthorization')
            result = Document(bytes(row[0]))
            if result.read()['expires_ms'] <= now_ms:
                raise Conflict('Expired command')
            # A read-only health query cannot establish local write-ahead health.
            # This commits durably before returning an execution request.
            db.execute('INSERT INTO command_checks(run_id,command_id,epoch,state_version,checked_ms) '
                       'VALUES(%s,%s,%s,%s,%s)',(run_id,command_id,epoch,run['version'],now_ms))
            return result

    @staticmethod
    def _verify(db,run_id,run,base=None):
        """Verify the journal, projection, reservations and outboxes; return a checkpoint.

        base=None verifies everything from the genesis. With a checkpoint from an earlier
        verification of this run, only the events after it are re-hashed and only their
        outbox rows are compared byte for byte; the reservations table, the run row and
        the row counts of every outbox table are still checked in full. A change to an
        older row is found by the next full verification, not by this one.
        """
        if base is None:
            base=dict(version=0,head=ZERO,fields=None,initial=digest(bytes(run['initial'])),reservations={},
                      ids={table:frozenset() for table,*_ in OUTBOXES},chunks=0)
        head,version,last = base['head'],base['version'],None
        reservations=dict(base['reservations']); new={table:{} for table,*_ in OUTBOXES}
        for raw,bhash,ehash,previous,stored,sequence in db.execute(
                'SELECT batch,batch_hash,event_hash,previous_hash,head,sequence FROM events '
                'WHERE run_id=%s AND sequence>%s ORDER BY sequence',(run_id,base['version'])):
            raw = bytes(raw)
            b = Document(raw).read()
            if (b['run_id'],b['wallet_id'],b['chain_id'])!=(run_id,run['wallet_id'],run['chain_id']):
                raise IntegrityError('Journal identity differs from wallet authority')
            version += 1
            expected = digest(bytes.fromhex(head)+bytes.fromhex(digest(raw)))
            if (digest(raw),digest(doc(b['event']).payload),previous,stored,sequence) != (
                    bhash,ehash,head,expected,version):
                raise IntegrityError('Journal corruption')
            head,last = stored,b
            for delta in b.get('reservation_deltas',[]):
                key=(delta['intent_id'],delta['asset'])
                reservations[key]=reservations.get(key,0)+delta['units']
            for table,id_column,_,key in OUTBOXES:
                for item in b.get(key,[]): new[table][item[id_column]]=doc(item).payload
        if (head,version) != (run['head'],run['version']):
            raise IntegrityError('Truncated or rewound journal')
        if digest(bytes(run['initial']))!=base['initial']:
            raise IntegrityError('Initial projection changed')
        if last:
            for field in FIELDS:
                if doc(last[field]).payload != bytes(run[field]):
                    raise IntegrityError('Projection does not match journal')
        elif base['fields'] is None:
            if bytes(run['projection'])!=bytes(run['initial']):
                raise IntegrityError('Initial projection changed')
        elif {field:digest(bytes(run[field])) for field in FIELDS}!=base['fields']:
            raise IntegrityError('Projection does not match journal')
        actual={(r[0],r[1]):int(r[2]) for r in db.execute(
            'SELECT intent_id,asset,units FROM reservations WHERE run_id=%s',(run_id,))}
        if actual!=reservations:
            raise IntegrityError('Reservations differ from journal')
        ids={}
        for table,id_column,value_column,_ in OUTBOXES:
            ids[table]=base['ids'][table]|frozenset(new[table])
            # Table/column names are internal constants, never client inputs.
            rows={r[0]:bytes(r[1]) for r in db.execute(
                f'SELECT {id_column},{value_column} FROM {table} WHERE run_id=%s AND {id_column}=ANY(%s::text[])',
                (run_id,list(new[table])))}
            count=db.execute(f'SELECT count(*) FROM {table} WHERE run_id=%s',(run_id,)).fetchone()[0]
            if rows!=new[table] or count!=len(ids[table]):
                raise IntegrityError('Outbox/job definition differs from journal')
        chunks,expected_chunks,timestamps=base['chunks'],{},{}
        for event_id,raw in new['audit_events'].items():
            audit=Document(raw).read()
            timestamps[event_id]=audit['timestamp_ms']
            if event_id not in base['ids']['audit_events']:
                chunks+=len(audit['chunks'])
            for index,chunk in enumerate(audit['chunks']):
                expected_chunks[(event_id,index)]=chunk.encode('utf-8')
        # The deadline query filters on this column, so it must equal the document.
        if timestamps!=dict(db.execute('SELECT event_id,timestamp_ms FROM audit_events WHERE run_id=%s '
                                       'AND event_id=ANY(%s::text[])',(run_id,list(timestamps))).fetchall()):
            raise IntegrityError('Audit timestamp differs from journal')
        actual_chunks={(r[0],r[1]):bytes(r[2]) for r in db.execute(
            'SELECT event_id,chunk_index,body FROM audit_chunks WHERE run_id=%s AND event_id=ANY(%s::text[])',
            (run_id,list(new['audit_events'])))}
        count=db.execute('SELECT count(*) FROM audit_chunks WHERE run_id=%s',(run_id,)).fetchone()[0]
        if actual_chunks!=expected_chunks or count!=chunks:
            raise IntegrityError('Audit chunk bytes differ from journal')
        return dict(version=version,head=head,fields={field:digest(bytes(run[field])) for field in FIELDS},
                    initial=base['initial'],reservations=reservations,ids=ids,chunks=chunks)

    def verified_snapshot(self,run_id,*,full=True):
        """Verify one coherent MVCC snapshot without locking the wallet row.

        Writers compare this authority under their short row lock. Any concurrent
        state change requires a fresh verification rather than trusting stale data.
        full=False (the write paths) continues from this process's last verified
        checkpoint instead of re-reading the whole journal; a checkpoint that no longer
        matches the database is discarded and the full verification runs instead.
        """
        with self.transaction() as db:
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            run=self._run(db,run_id,lock=False)
            base=None
            if not full:
                with self._checkpoint_lock:
                    base=self._checkpoints.get(run_id)
                if base is not None and not self._continues(db,run_id,run,base):
                    base=None
            checkpoint=self._verify(db,run_id,run,base)
        with self._checkpoint_lock:
            known=self._checkpoints.get(run_id)
            if known is None or base is None or known['version']<=checkpoint['version']:
                self._checkpoints[run_id]=checkpoint
        return run

    @staticmethod
    def _continues(db,run_id,run,base):
        """True if the database still extends the journal this checkpoint verified."""
        if run['version']<base['version'] or digest(bytes(run['initial']))!=base['initial']:
            return False
        if base['version']==0:
            return base['head']==ZERO
        row=db.execute('SELECT head FROM events WHERE run_id=%s AND sequence=%s',(run_id,base['version'])).fetchone()
        return row is not None and row[0]==base['head']

    @staticmethod
    def _same_snapshot(verified,run):
        if any(verified[key]!=run[key] for key in verified if key!='clock_ms'):
            raise Conflict('Authority changed during integrity verification; retry from fresh state')

    def verify(self,run_id, *, minimum_version=0, anchored_head=None):
        run=self.verified_snapshot(run_id)
        if run['version'] < minimum_version or (anchored_head is not None and run['head'] != anchored_head):
            raise IntegrityError('Restore behind external authority/anchor')
        return run['head']

    def journal(self,run_id):
        self.verify(run_id)
        with self.transaction() as db:
            return [Document(bytes(r[0])) for r in db.execute(
                'SELECT batch FROM events WHERE run_id=%s ORDER BY sequence',(run_id,))]

    def metrics(self,run_id):
        with self.transaction() as db:
            run = self._run(db,run_id,lock=False)
            return doc(dict(version=run['version'],owner_epoch=run['epoch'],quarantined=run['quarantined'],
                audit_pending=db.execute("SELECT count(*) FROM audit_chunks WHERE run_id=%s AND status<>'ACK'",(run_id,)).fetchone()[0],
                open_rounds=db.execute("SELECT count(*) FROM rounds WHERE run_id=%s AND status='OPEN'",(run_id,)).fetchone()[0],
                jobs_pending=db.execute("SELECT count(*) FROM jobs WHERE run_id=%s AND status IN ('PENDING','RUNNING')",(run_id,)).fetchone()[0]))

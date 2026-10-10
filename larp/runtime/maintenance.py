"""Durable archive maintenance, independent of model and trade scheduling."""

from larp.contracts import ContractError, Document
from larp.storage.backup import export
from larp.storage.postgres import Conflict, IntegrityError, Unavailable, digest, doc

HOUR_MS = 3600000


class Maintenance:
    def __init__(self, store, archive, *, backup_interval_ms, max_attempts=8,
                 retry_ms=60000, max_payload_bytes=64 * 1024 * 1024):
        for number in (backup_interval_ms, max_attempts, retry_ms, max_payload_bytes):
            if type(number) is not int or number < 1:
                raise ContractError('Maintenance budgets must be positive integers')
        if backup_interval_ms < HOUR_MS or retry_ms < 1000:
            raise ContractError('Invalid maintenance cadence')
        self.store, self.archive = store, archive
        self.backup_interval_ms, self.max_attempts = backup_interval_ms, max_attempts
        self.retry_ms, self.max_payload_bytes = retry_ms, max_payload_bytes

    def prepare(self, run_id, now_ms):
        if type(now_ms) is not int or now_ms < 0:
            raise ContractError('Invalid maintenance time')
        with self.store.transaction() as db:
            run = self.store._run(db, run_id)
            if run['quarantined']:
                raise Conflict('Quarantined runs cannot resume scheduled archival')
            self.store._verify(db, run_id, run)
            row = db.execute('SELECT last_ms FROM archive_clock WHERE run_id=%s', (run_id,)).fetchone()
            if row and now_ms < row[0]:
                raise Conflict('Maintenance clock moved backwards')
            db.execute('INSERT INTO archive_clock VALUES(%s,%s) ON CONFLICT(run_id) '
                       'DO UPDATE SET last_ms=EXCLUDED.last_ms', (run_id, now_ms))
            slot = now_ms // HOUR_MS * HOUR_MS
            payload = doc(dict(schema='Anchor.v2', run_id=run_id, slot_ms=slot,
                               captured_ms=now_ms, sequence=run['version'], head=run['head'],
                               owner_epoch=run['epoch']))
            self._enqueue(db, run_id, 'anchor', slot, payload)
            backup_slot = now_ms // self.backup_interval_ms * self.backup_interval_ms
            needs_backup = not db.execute('SELECT 1 FROM archive_outbox WHERE run_id=%s '
                                          "AND kind='backup' AND slot_ms=%s", (run_id, backup_slot)).fetchone()
        if needs_backup:
            # Snapshot in a separate repeatable-read transaction. Competing
            # preparers keep the first persisted payload for this immutable slot.
            payload = export(self.store)
            if len(payload.payload) > self.max_payload_bytes:
                raise ContractError('Backup exceeds configured bound; no truncation performed')
            with self.store.transaction() as db:
                run = self.store._run(db, run_id)
                if run['quarantined']:
                    raise Conflict('Run quarantined during backup preparation')
                self._enqueue(db, run_id, 'backup', backup_slot, payload)

    @staticmethod
    def _enqueue(db, run_id, kind, slot, payload):
        db.execute('INSERT INTO archive_outbox(run_id,kind,slot_ms,payload,sha256) '
                   'VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                   (run_id, kind, slot, payload.payload, digest(payload.payload)))

    def once(self, run_id, now_ms):
        with self.store.transaction() as db:
            run = self.store._run(db, run_id)
            if run['quarantined']:
                raise Conflict('Quarantined run')
            clock = db.execute('SELECT last_ms FROM archive_clock WHERE run_id=%s', (run_id,)).fetchone()
            if not clock or now_ms < clock[0]:
                raise Conflict('Maintenance clock missing or backwards')
            db.execute('UPDATE archive_clock SET last_ms=%s WHERE run_id=%s', (now_ms, run_id))
            row = db.execute("SELECT kind,slot_ms,payload,sha256,attempts FROM archive_outbox "
                             "WHERE run_id=%s AND status='PENDING' AND next_ms<=%s "
                             'ORDER BY slot_ms,kind LIMIT 1 FOR UPDATE SKIP LOCKED', (run_id, now_ms)).fetchone()
            if not row:
                return False
            kind, slot, raw, expected, attempts = row
            raw = bytes(raw)
            if attempts >= self.max_attempts:
                db.execute("UPDATE archive_outbox SET status='EXHAUSTED' WHERE run_id=%s AND kind=%s AND slot_ms=%s",
                           (run_id, kind, slot))
                return True
            db.execute('UPDATE archive_outbox SET attempts=attempts+1,next_ms=%s '
                       'WHERE run_id=%s AND kind=%s AND slot_ms=%s',
                       (now_ms + self.retry_ms, run_id, kind, slot))
        # No remote I/O while the run's database transaction is held.
        receipt, error, status = None, None, 'PENDING'
        try:
            if digest(raw) != expected:
                raise IntegrityError('Archive outbox bytes changed')
            run_key = digest(run_id.encode('utf-8'))
            receipt = self.archive.put(f'{run_key}/{kind}/{slot}.json', raw,
                                       created_ms=slot, now_ms=now_ms)
            if receipt.read().get('status') != 'STORED' or receipt.read().get('sha256') != expected:
                raise IntegrityError('Archive acknowledgement mismatch')
            status = 'ACK'
        except (ContractError, Unavailable) as exc:
            error = type(exc).__name__  # Never persist SDK messages/credentials.
            status = 'PERMANENT' if isinstance(exc, ContractError) else (
                'EXHAUSTED' if attempts + 1 >= self.max_attempts else 'PENDING')
        with self.store.transaction() as db:
            # A late failure must never overwrite another worker's ACK. An old
            # attempt cannot clobber a later attempt, even after lease expiration.
            db.execute('UPDATE archive_outbox SET status=%s,last_error=%s,acknowledgement=%s '
                       "WHERE run_id=%s AND kind=%s AND slot_ms=%s AND status<>'ACK' AND attempts=%s",
                       (status, error, receipt.payload if status == 'ACK' else None,
                        run_id, kind, slot, attempts + 1))
        return True

    def health(self, run_id, now_ms):
        with self.store.transaction() as db:
            run = self.store._run(db, run_id)
            last_clock = db.execute('SELECT last_ms FROM archive_clock WHERE run_id=%s', (run_id,)).fetchone()
            counts = dict(db.execute('SELECT status,count(*) FROM archive_outbox WHERE run_id=%s GROUP BY status', (run_id,)))
            latest = dict(db.execute("SELECT kind,max(slot_ms) FROM archive_outbox WHERE run_id=%s "
                                     "AND status='ACK' GROUP BY kind", (run_id,)))
            audit_failures = db.execute("SELECT count(*) FROM audit_chunks WHERE run_id=%s "
                                        "AND status IN ('PERMANENT','EXHAUSTED')", (run_id,)).fetchone()[0]
            pending = db.execute("SELECT DISTINCT a.document FROM audit_events a JOIN audit_chunks c "
                                 "USING(run_id,event_id) WHERE a.run_id=%s AND c.status<>'ACK'", (run_id,)).fetchall()
        breaches = sum(now_ms >= ((Document(bytes(raw)).read()['timestamp_ms'] // 86400000 + 1)
                                  * 86400000 + 7200000) for raw, in pending)
        ages = {kind: max(0, now_ms - latest[kind]) if kind in latest else None for kind in ('anchor', 'backup')}
        reasons = []
        if run['quarantined']:
            reasons.append('QUARANTINED')
        if last_clock and now_ms < last_clock[0]:
            reasons.append('CLOCK_BACKWARD')
        for kind, limit in (('anchor', 2 * HOUR_MS), ('backup', 2 * self.backup_interval_ms)):
            if ages[kind] is None or ages[kind] > limit:
                reasons.append(kind.upper() + '_STALE')
        if counts.get('PERMANENT', 0) or counts.get('EXHAUSTED', 0):
            reasons.append('ARCHIVE_DELIVERY_BLOCKED')
        if audit_failures or breaches:
            reasons.append('AUDIT_DELIVERY_BLOCKED')
        return doc(dict(schema='MaintenanceHealth.v1', healthy=not reasons, reasons=reasons,
                        counts=counts, age_ms=ages, audit_failures=audit_failures,
                        audit_deadline_breaches=breaches, signing_enabled=False))

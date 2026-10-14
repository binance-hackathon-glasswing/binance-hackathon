"""Durable archive maintenance, independent of model and trade scheduling."""

from larp.audit.delivery import deadline_breaches
from larp.contracts import ContractError, Document
from larp.storage.backup import export
from larp.storage.postgres import Conflict, IntegrityError, Unavailable, digest, doc

HOUR_MS = 3600000
RUNTIME_HEARTBEAT_MS = 600000   # a runtime session heartbeat older than this counts as down (IDEA-047 R5)
SIGNER_ANSWER_S = 120           # a signing request unanswered for longer counts against the signer (IDEA-047 R5)
# An anchor carries identifiers, times and hashes only: never keys, credentials or evidence text (IDEA-036 #6).
ANCHOR_FIELDS = frozenset(('schema', 'run_id', 'slot_ms', 'captured_ms', 'sequence', 'head', 'owner_epoch'))
ZERO_HEAD = '0' * 64


def verify_anchors(store, run_id, anchors):
    """Check every anchored (sequence, head) against the verified journal (IDEA-036 #3, #5; IDEA-042 A1-A3).

    `anchors`: Anchor.v2 documents as read back from the write-once archive. A journal rewritten after an anchor no
    longer reproduces its head; a restore behind the latest anchor is stale. Returns the newest anchored sequence.
    """
    head = store.verify(run_id)
    items = [a.read() if isinstance(a, Document) else a for a in anchors]
    for a in items:
        if a.get('schema') != 'Anchor.v2' or set(a) != ANCHOR_FIELDS or a['run_id'] != run_id:
            raise IntegrityError('Not an Anchor.v2 record of this run')
    with store.transaction() as db:
        version = store._run(db, run_id, lock=False)['version']
        heads = dict(db.execute('SELECT sequence,head FROM events WHERE run_id=%s AND sequence=ANY(%s)',
                                (run_id, [a['sequence'] for a in items])).fetchall())
    for a in items:
        if a['sequence'] > version:
            raise IntegrityError('Restore is behind an anchored head; stale')
        if (ZERO_HEAD if a['sequence'] == 0 else heads.get(a['sequence'])) != a['head']:
            raise IntegrityError('Journal differs from an anchored head')
    return dict(head=head, anchors=len(items), latest_sequence=max((a['sequence'] for a in items), default=None))


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
        slot = now_ms // HOUR_MS * HOUR_MS
        backup_slot = now_ms // self.backup_interval_ms * self.backup_interval_ms
        with self.store.transaction() as db:
            run = self.store._run(db, run_id, lock=False)
            if run['quarantined']:
                raise Conflict('Quarantined runs cannot resume scheduled archival')
            db.execute('INSERT INTO archive_clock VALUES(%s,%s) ON CONFLICT DO NOTHING',(run_id,now_ms))
            row = db.execute('SELECT last_ms FROM archive_clock WHERE run_id=%s FOR UPDATE', (run_id,)).fetchone()
            if row and now_ms < row[0]:
                raise Conflict('Maintenance clock moved backwards')
            db.execute('INSERT INTO archive_clock VALUES(%s,%s) ON CONFLICT(run_id) '
                       'DO UPDATE SET last_ms=EXCLUDED.last_ms', (run_id, now_ms))
            needs_anchor = not db.execute('SELECT 1 FROM archive_outbox WHERE run_id=%s '
                                          "AND kind='anchor' AND slot_ms=%s", (run_id, slot)).fetchone()
            needs_backup = not db.execute('SELECT 1 FROM archive_outbox WHERE run_id=%s '
                                          "AND kind='backup' AND slot_ms=%s", (run_id, backup_slot)).fetchone()
        if needs_anchor:
            # Full verification uses a read-only snapshot, never a wallet lock.
            # The anchor identifies that snapshot even if new rounds commit later.
            run = self.store.verified_snapshot(run_id)
            if run['quarantined']:
                raise Conflict('Quarantined runs cannot prepare new anchors')
            payload = doc(dict(schema='Anchor.v2', run_id=run_id, slot_ms=slot,
                               captured_ms=now_ms, sequence=run['version'], head=run['head'],
                               owner_epoch=run['epoch']))
            with self.store.transaction() as db:
                self._enqueue(db, run_id, 'anchor', slot, payload)
        if needs_backup:
            # Snapshot in a separate repeatable-read transaction. Competing
            # preparers keep the first persisted payload for this immutable slot.
            payload = export(self.store)
            if len(payload.payload) > self.max_payload_bytes:
                raise ContractError('Backup exceeds configured bound; no truncation performed')
            with self.store.transaction() as db:
                run = self.store._run(db, run_id, lock=False)
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
            # Sending already committed evidence cannot grant trading authority;
            # it must remain possible during quarantine or preparation failure.
            self.store._run(db, run_id, lock=False)
            db.execute('INSERT INTO archive_clock VALUES(%s,%s) ON CONFLICT DO NOTHING',(run_id,now_ms))
            clock = db.execute('SELECT last_ms FROM archive_clock WHERE run_id=%s FOR UPDATE', (run_id,)).fetchone()
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

    def service_health(self, run_id, now_ms):
        """Service-level signals for CloudWatch (IDEA-047 R5), read with the larp_archive grants only.

        Runtime: age of the newest open process-session heartbeat (None: no running session), active HALT reasons and
        quarantine. Uploader: audit events past their upload deadline. Signer: signing requests older than
        SIGNER_ANSWER_S with neither a refusal nor a signature for their attempt and payload. The signer has no
        internet route (IDEA-046 B2), so its liveness is judged from the database by this primary-side check."""
        now_s = now_ms // 1000
        with self.store.transaction() as db:
            run = self.store._run(db, run_id, lock=False)
            projection = Document(bytes(run['projection'])).read()
            beat = db.execute('SELECT max(heartbeat_ms) FROM process_sessions WHERE run_id=%s AND ended_ms IS NULL',
                              (run_id,)).fetchone()[0]
            overdue = len(deadline_breaches(db, run_id, now_ms))
            unanswered, oldest = db.execute(
                'SELECT count(*),min(r.requested_s) FROM signing_requests r WHERE r.run_id=%s AND r.requested_s<%s '
                'AND NOT EXISTS (SELECT 1 FROM signing_refusals f WHERE f.request_id=r.request_id) '
                'AND NOT EXISTS (SELECT 1 FROM execution_signatures s WHERE s.attempt_id=r.attempt_id '
                'AND s.payload_hash=r.payload_hash)', (run_id, now_s - SIGNER_ANSWER_S)).fetchone()
        age = None if beat is None else max(0, now_ms - beat)
        return doc(dict(schema='ServiceHealth.v1', runtime_heartbeat_age_ms=age,
                        runtime_alive=age is not None and age <= RUNTIME_HEARTBEAT_MS,
                        halt_reasons=sorted((projection.get('halt') or {}).get('reasons', {})),
                        quarantined=bool(run['quarantined']), audit_overdue=overdue,
                        signing_unanswered=unanswered,
                        signing_oldest_unanswered_s=None if oldest is None else now_s - oldest,
                        signing_enabled=False))

    def health(self, run_id, now_ms):
        with self.store.transaction() as db:
            run = self.store._run(db, run_id, lock=False)
            last_clock = db.execute('SELECT last_ms FROM archive_clock WHERE run_id=%s', (run_id,)).fetchone()
            counts = dict(db.execute('SELECT status,count(*) FROM archive_outbox WHERE run_id=%s GROUP BY status', (run_id,)))
            latest = dict(db.execute("SELECT kind,max(slot_ms) FROM archive_outbox WHERE run_id=%s "
                                     "AND status='ACK' GROUP BY kind", (run_id,)))
            audit_failures = db.execute("SELECT count(*) FROM audit_chunks WHERE run_id=%s "
                                        "AND status IN ('PERMANENT','EXHAUSTED')", (run_id,)).fetchone()[0]
            breaches = len(deadline_breaches(db, run_id, now_ms))
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

"""Durable archive maintenance, independent of model and trade scheduling."""

import json
import os
from pathlib import Path

from larp.audit.delivery import deadline_breaches, unlogged_rounds
from larp.contracts import ContractError, Document
from larp.storage.backup import GZIP_MAGIC, export_segment
from larp.storage.postgres import Conflict, IntegrityError, Unavailable, digest, doc

HOUR_MS = 3600000
RUNTIME_HEARTBEAT_MS = 600000   # a runtime session heartbeat older than this counts as down (IDEA-047 R5)
SIGNER_ANSWER_S = 120           # a signing request unanswered for longer counts against the signer (IDEA-047 R5)
# An anchor carries identifiers, times and hashes only: never keys, credentials or evidence text (IDEA-036 #6).
ANCHOR_FIELDS = frozenset(('schema', 'run_id', 'slot_ms', 'captured_ms', 'sequence', 'head', 'owner_epoch'))
ZERO_HEAD = '0' * 64
# A backup slot is attempted once (IDEA-094): its outbox row is PREPARING before the export starts, PENDING with the
# payload after it, PERMANENT with the error class if it fails. A PREPARING row older than this was left by a killed
# process (the unit's TimeoutStartSec is shorter) and is closed as PreparationInterrupted.
PREPARING_STALE_MS = 30 * 60000


class VerificationState:
    """The archive host's verification checkpoint and full-check times, one JSON file per run in the unit's
    StateDirectory (IDEA-095). It lies outside the database's trust domain, as the runtime's in-memory checkpoint does.
    A file that is missing or does not parse as this run's state reads as empty: the next anchor verifies in full."""
    SCHEMA = 'ArchiveVerification.v1'

    def __init__(self, directory):
        self.directory = Path(directory)

    def path(self, run_id):
        return self.directory / (digest(run_id.encode('utf-8')) + '.json')

    def load(self, run_id):
        try:
            value = json.loads(self.path(run_id).read_bytes())
        except (OSError, ValueError):
            return {}
        return value if type(value) is dict and value.get('schema') == self.SCHEMA and value.get('run_id') == run_id \
            else {}

    def save(self, run_id, **changes):
        value = dict(self.load(run_id), **changes, schema=self.SCHEMA, run_id=run_id)
        path = self.path(run_id)
        partial = path.with_name(path.name + '.partial')
        with open(partial, 'wb') as out:
            out.write(json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8'))
            out.flush()
            os.fsync(out.fileno())
        os.replace(partial, path)


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
                 retry_ms=60000, max_payload_bytes=64 * 1024 * 1024, preparing_stale_ms=PREPARING_STALE_MS,
                 verification=None):
        for number in (backup_interval_ms, max_attempts, retry_ms, max_payload_bytes, preparing_stale_ms):
            if type(number) is not int or number < 1:
                raise ContractError('Maintenance budgets must be positive integers')
        if backup_interval_ms < HOUR_MS or retry_ms < 1000:
            raise ContractError('Invalid maintenance cadence')
        self.store, self.archive = store, archive
        self.backup_interval_ms, self.max_attempts = backup_interval_ms, max_attempts
        self.retry_ms, self.max_payload_bytes = retry_ms, max_payload_bytes
        self.preparing_stale_ms = preparing_stale_ms
        self.verification = verification  # a VerificationState, or None: every anchor verifies in full

    def prepare(self, run_id, now_ms):
        self.prepare_anchor(run_id, now_ms)
        self.prepare_backup(run_id, now_ms)

    def _tick(self, db, run_id, now_ms):
        if type(now_ms) is not int or now_ms < 0:
            raise ContractError('Invalid maintenance time')
        run = self.store._run(db, run_id, lock=False)
        if run['quarantined']:
            raise Conflict('Quarantined runs cannot resume scheduled archival')
        db.execute('INSERT INTO archive_clock VALUES(%s,%s) ON CONFLICT DO NOTHING',(run_id,now_ms))
        row = db.execute('SELECT last_ms FROM archive_clock WHERE run_id=%s FOR UPDATE', (run_id,)).fetchone()
        if row and now_ms < row[0]:
            raise Conflict('Maintenance clock moved backwards')
        db.execute('INSERT INTO archive_clock VALUES(%s,%s) ON CONFLICT(run_id) '
                   'DO UPDATE SET last_ms=EXCLUDED.last_ms', (run_id, now_ms))
        return run

    def prepare_anchor(self, run_id, now_ms):
        """Queue this hour's anchor. Independent of the backup: a failed or killed export never delays it."""
        with self.store.transaction() as db:
            self._tick(db, run_id, now_ms)
            slot = now_ms // HOUR_MS * HOUR_MS
            needs_anchor = not db.execute('SELECT 1 FROM archive_outbox WHERE run_id=%s '
                                          "AND kind='anchor' AND slot_ms=%s", (run_id, slot)).fetchone()
        if needs_anchor:
            # Verification uses a read-only snapshot, never a wallet lock.
            # The anchor identifies that snapshot even if new rounds commit later.
            run = self._verified(run_id, now_ms)
            if run['quarantined']:
                raise Conflict('Quarantined runs cannot prepare new anchors')
            payload = doc(dict(schema='Anchor.v2', run_id=run_id, slot_ms=slot,
                               captured_ms=now_ms, sequence=run['version'], head=run['head'],
                               owner_epoch=run['epoch']))
            with self.store.transaction() as db:
                self._enqueue(db, run_id, 'anchor', slot, payload)

    def _verified(self, run_id, now_ms):
        """Full verification, or, with a saved checkpoint, only the events after it (IDEA-095): each run of
        `operations once` is a new process, and a full one reads the whole journal from the database."""
        if self.verification is None:
            return self.store.verified_snapshot(run_id)
        seeded = self.store.adopt_checkpoint(run_id, self.verification.load(run_id).get('checkpoint'))
        try:
            run = self.store.verified_snapshot(run_id, full=not seeded)
        except IntegrityError:
            self._keep(run_id, checkpoint=None)  # the next run verifies in full
            raise
        self._keep(run_id, checkpoint=self.store.export_checkpoint(run_id), **({} if seeded else dict(full_ms=now_ms)))
        return run

    def _keep(self, run_id, **changes):
        """Save after an anchor's verification. An unwritable state directory never costs the anchor: later anchors
        then verify in full, and the full check's own save fails and reports it."""
        try:
            self.verification.save(run_id, **changes)
        except OSError:
            pass

    def full_check(self, run_id, now_ms):
        """Once per backup interval, last in `operations once` (IDEA-095): verify the whole journal. The attempt is
        saved before it starts, so a run killed inside it (TimeoutStartSec) is not repeated until the next interval. A
        failure discards the checkpoint: the next anchor verifies in full and refuses. True if a check ran."""
        if self.verification is None:
            return False
        saved = self.verification.load(run_id)
        slot = now_ms // self.backup_interval_ms * self.backup_interval_ms
        if any(type(saved.get(key)) is int and saved[key] >= slot for key in ('full_ms', 'attempt_ms')):
            return False
        self.verification.save(run_id, attempt_ms=now_ms,
                               **({} if type(saved.get('first_attempt_ms')) is int else dict(first_attempt_ms=now_ms)))
        try:
            self.store.verified_snapshot(run_id)
        except IntegrityError:
            self.verification.save(run_id, checkpoint=None)
            raise
        self.verification.save(run_id, checkpoint=self.store.export_checkpoint(run_id), full_ms=now_ms)
        return True

    def verification_reasons(self, run_id, now_ms):
        """FULL_VERIFICATION_OVERDUE when no full verification completed within two backup intervals (IDEA-095)."""
        if self.verification is None:
            return []
        saved = self.verification.load(run_id)
        # Before any full verification completed, the clock starts at the first full-check attempt.
        since = next((saved[key] for key in ('full_ms', 'first_attempt_ms') if type(saved.get(key)) is int), None)
        return ['FULL_VERIFICATION_OVERDUE'] if since is not None and now_ms - since > 2 * self.backup_interval_ms \
            else []

    def prepare_backup(self, run_id, now_ms):
        """Prepare at most one backup segment (IDEA-094). Returns the slot attempted, or None. A refused or failed
        export is recorded on its slot (PERMANENT, error class) and re-raised; the slot is never exported twice."""
        backup_slot = now_ms // self.backup_interval_ms * self.backup_interval_ms
        with self.store.transaction() as db:
            run = self._tick(db, run_id, now_ms)
            # A PREPARING row left by a killed export is closed for good; the next slot starts a new segment.
            db.execute("UPDATE archive_outbox SET status='PERMANENT',last_error='PreparationInterrupted' "
                       "WHERE run_id=%s AND kind='backup' AND status='PREPARING' AND next_ms<%s",
                       (run_id, now_ms - self.preparing_stale_ms))
            needs_backup = not db.execute('SELECT 1 FROM archive_outbox WHERE run_id=%s '
                                          "AND kind='backup' AND slot_ms=%s", (run_id, backup_slot)).fetchone()
            # Declared: the journal is uploaded daily "and after any incident" (IDEA-049 D-FND-008). An incident
            # (supervisor restart, HALT) committed after the newest backup gets one more backup now.
            incident = db.execute("SELECT max(sequence) FROM events WHERE run_id=%s "
                                  "AND (event_id LIKE 'incident:%%' OR event_id LIKE 'halt:%%')", (run_id,)).fetchone()[0]
            covered = db.execute("SELECT max(covers_sequence) FROM archive_outbox WHERE run_id=%s AND kind='backup'",
                                 (run_id,)).fetchone()[0]
            # At most one incident backup per hour: a crash loop journals an incident every few seconds (IDEA-049
            # D-FND-021). Scheduled backups sit on interval boundaries.
            recent = db.execute("SELECT 1 FROM archive_outbox WHERE run_id=%s AND kind='backup' "
                                'AND slot_ms %% %s <> 0 AND slot_ms > %s LIMIT 1',
                                (run_id, self.backup_interval_ms, now_ms - HOUR_MS)).fetchone()
            preparing = db.execute("SELECT 1 FROM archive_outbox WHERE run_id=%s AND kind='backup' "
                                   "AND status='PREPARING' LIMIT 1", (run_id,)).fetchone()
            version = run['version']
            needs_incident_backup = (incident is not None and (covered is None or covered < incident)
                                     and recent is None)
            if preparing or not (needs_backup or needs_incident_backup):
                return None
            slot = backup_slot if needs_backup else now_ms
            # The base is the newest acknowledged segment: an unacknowledged one may never arrive (IDEA-094).
            # A database holding other runs too gets self-contained segments (a base names this run only).
            base = None
            single = db.execute('SELECT count(*) FROM runs').fetchone()[0] == 1
            for receipt, covers, sha256, base_slot in [] if not single else db.execute(
                    "SELECT acknowledgement,covers_sequence,sha256,slot_ms FROM archive_outbox WHERE run_id=%s "
                    "AND kind='backup' AND status='ACK' AND covers_sequence IS NOT NULL "
                    'ORDER BY covers_sequence DESC,slot_ms DESC', (run_id,)).fetchall():
                if Document(bytes(receipt)).read().get('key', '').endswith('.json.gz'):
                    base = dict(sha256=sha256, slot_ms=base_slot, through={run_id: covers})
                    break
            # Committed before the export starts, so a process killed inside it leaves a durable record.
            inserted = db.execute("INSERT INTO archive_outbox(run_id,kind,slot_ms,payload,sha256,status,next_ms,"
                                  "covers_sequence) VALUES(%s,'backup',%s,''::bytea,'',"
                                  "'PREPARING',%s,%s) ON CONFLICT DO NOTHING RETURNING 1",
                                  (run_id, slot, now_ms, version)).fetchone()
        if not inserted:
            return None
        if self.verification is not None and self.store.export_checkpoint(run_id) is None:
            # An incident backup in a later run of the hour: continue from the saved checkpoint (IDEA-095).
            self.store.adopt_checkpoint(run_id, self.verification.load(run_id).get('checkpoint'))
        try:
            # Snapshot in a separate repeatable-read transaction, taken after `version` was read.
            segment = export_segment(self.store, max_bytes=self.max_payload_bytes, base=base)
            with self.store.transaction() as db:
                run = self.store._run(db, run_id, lock=False)
                if run['quarantined']:
                    raise Conflict('Run quarantined during backup preparation')
                db.execute("UPDATE archive_outbox SET status='PENDING',payload=%s,sha256=%s,next_ms=0,"
                           'covers_sequence=%s WHERE run_id=%s AND kind=%s AND slot_ms=%s AND status=%s',
                           (segment.payload, digest(segment.payload), segment.through[run_id], run_id, 'backup',
                            slot, 'PREPARING'))
        except Exception as exc:
            with self.store.transaction() as db:
                db.execute("UPDATE archive_outbox SET status='PERMANENT',last_error=%s "
                           "WHERE run_id=%s AND kind='backup' AND slot_ms=%s AND status='PREPARING'",
                           (type(exc).__name__, run_id, slot))  # the class only: never SDK or database text
            raise
        return slot

    @staticmethod
    def _enqueue(db, run_id, kind, slot, payload, covers=None):
        db.execute('INSERT INTO archive_outbox(run_id,kind,slot_ms,payload,sha256,covers_sequence) '
                   'VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                   (run_id, kind, slot, payload.payload, digest(payload.payload), covers))

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
            # Binary results: a text-format bytea arrives hex-encoded, three times the payload in memory (IDEA-094).
            row = db.execute("SELECT kind,slot_ms,payload,sha256,attempts FROM archive_outbox "
                             "WHERE run_id=%s AND status='PENDING' AND next_ms<=%s "
                             'ORDER BY slot_ms,kind LIMIT 1 FOR UPDATE SKIP LOCKED', (run_id, now_ms),
                             binary=True).fetchone()
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
            suffix = '.json.gz' if raw[:2] == GZIP_MAGIC else '.json'  # Backup.v2 segments are gzip (IDEA-094)
            receipt = self.archive.put(f'{run_key}/{kind}/{slot}{suffix}', raw,
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
            # Once the write-once archive holds the bytes (receipt and SHA-256 kept), the database copy is released,
            # so daily and incident backups do not accumulate in the database (IDEA-049 D-FND-021).
            db.execute("UPDATE archive_outbox SET status=%s,last_error=%s,acknowledgement=%s,"
                       "payload=CASE WHEN %s THEN ''::bytea ELSE payload END "
                       "WHERE run_id=%s AND kind=%s AND slot_ms=%s AND status<>'ACK' AND attempts=%s",
                       (status, error, receipt.payload if status == 'ACK' else None, status == 'ACK',
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
            overdue = len(deadline_breaches(db, run_id, now_ms)) + len(unlogged_rounds(projection, now_ms))
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
                        gas_pair_unaffordable=(projection.get('gas_health') or {}).get('pair_unaffordable', False),
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
            failed = db.execute("SELECT kind,slot_ms FROM archive_outbox WHERE run_id=%s "
                                "AND status IN ('PERMANENT','EXHAUSTED') ORDER BY kind,slot_ms", (run_id,)).fetchall()
            # The newest backup slot whose preparation failed (refused, errored or killed; IDEA-094).
            refused = db.execute("SELECT slot_ms,last_error FROM archive_outbox WHERE run_id=%s AND kind='backup' "
                                 "AND status='PERMANENT' AND attempts=0 ORDER BY slot_ms DESC LIMIT 1",
                                 (run_id,)).fetchone()
            audit_failures = db.execute("SELECT count(*) FROM audit_chunks WHERE run_id=%s "
                                        "AND status IN ('PERMANENT','EXHAUSTED')", (run_id,)).fetchone()[0]
            projection = Document(bytes(run['projection'])).read()
            breaches = len(deadline_breaches(db, run_id, now_ms)) + len(unlogged_rounds(projection, now_ms))
        ages = {kind: max(0, now_ms - latest[kind]) if kind in latest else None for kind in ('anchor', 'backup')}
        reasons = []
        if run['quarantined']:
            reasons.append('QUARANTINED')
        if last_clock and now_ms < last_clock[0]:
            reasons.append('CLOCK_BACKWARD')
        for kind, limit in (('anchor', 2 * HOUR_MS), ('backup', 2 * self.backup_interval_ms)):
            if ages[kind] is None or ages[kind] > limit:
                reasons.append(kind.upper() + '_STALE')
        # A slot that could not be delivered is never written late (IDEA-036 #2); it is listed as missed for good.
        # It blocks health only until a newer slot of its kind is acknowledged: a later anchor and a later full
        # backup supersede it (IDEA-049 D-FND-009, #64 item 1).
        missed = {kind: [slot for k, slot in failed if k == kind] for kind in ('anchor', 'backup')}
        if any(slot >= latest.get(kind, -1) for kind, slots in missed.items() for slot in slots):
            reasons.append('ARCHIVE_DELIVERY_BLOCKED')
        backup_failure = None
        if refused and refused[0] >= latest.get('backup', -1):
            backup_failure = dict(slot_ms=refused[0], error=refused[1])
            reasons.append('BACKUP_PREPARATION_FAILED')
        if audit_failures or breaches:
            reasons.append('AUDIT_DELIVERY_BLOCKED')
        return doc(dict(schema='MaintenanceHealth.v1', healthy=not reasons, reasons=reasons,
                        counts=counts, age_ms=ages, missed=missed, audit_failures=audit_failures,
                        backup_failure=backup_failure,
                        audit_deadline_breaches=breaches, signing_enabled=False))

"""SLM-01: background assessors, append-only private audit, main-thread authority only.

One slot per assessor instance (IDEA-093 PL: `assessment_workers`; one assessor is the original single slot). At most
one pending job per company. A hung model retains its own slot only. It never blocks safety ticks or creates an
unbounded executor queue. Restart outcomes stay tied to their original request.
"""
import hashlib
import json
import os
from pathlib import Path
import threading

from larp.contracts import ContractError, Document

MAX_EVENT = 8 * 1024 * 1024


def encoded(value):
    return Document.from_dict(value).payload


class DeferredAssessments:
    def __init__(self, assessor, *, root, run_id, build_id, profile_hash):
        # A list gives one slot per independent assessor instance (IDEA-093 PL); one assessor is the single slot.
        self.assessors = list(assessor) if isinstance(assessor, (list, tuple)) else [assessor]
        if not self.assessors:
            raise ContractError('At least one assessor is required')
        self.assessor = self.assessors[0]
        self.identity = dict(run_id=run_id, build_id=build_id, profile_hash=profile_hash)
        root = Path(root)
        if root.is_symlink():
            raise ContractError('Model journal directory cannot be a symlink')
        namespace = hashlib.sha256(encoded(self.identity)).hexdigest()
        self.root = root / namespace
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink():
            raise ContractError('Model journal directory cannot be a symlink')
        self._writer_lock = threading.RLock()
        self._slot_lock = threading.Lock()
        self._free = list(self.assessors)
        self.pending, self.active = {}, None
        self._running, self._issuer = {}, {}  # round ID -> finished event (this process) / company
        self.finished = threading.Event()
        for path in sorted(self.root.glob('*.jsonl')):
            events = self._read(path)
            if not events or events[0].get('kind') != 'REQUEST':
                raise ContractError('Model journal lacks request')
            first = events[0]
            self._identity(first['request'])
            if first.get('identity') != self.identity:
                raise ContractError('Model journal identity mismatch')
            if events[-1]['kind'] != 'ACK':
                self.pending[first['round_id']] = path
                self._issuer[first['round_id']] = first['request'].get('issuer_id')

    @property
    def busy(self):
        return len(self.pending) >= len(self.assessors)

    def issuers(self):
        """Companies with a pending (unacknowledged) job."""
        return set(self._issuer.values())

    def running(self, round_id):
        done = self._running.get(round_id)
        return done is not None and not done.is_set()

    def round_ids(self):
        return set(self.pending)

    def _identity(self, request):
        if (request.get('run_id') != self.identity['run_id'] or
                request.get('policy_profile_hash') != self.identity['profile_hash']):
            raise ContractError('Deferred request identity mismatch')

    def _read(self, path):
        if path.is_symlink():
            raise ContractError('Model journal cannot be a symlink')
        previous, events = '0' * 64, []
        with path.open('rb') as stream:
            for line in stream:
                if len(line) > MAX_EVENT or not line.endswith(b'\n'):
                    raise ContractError('Incomplete or oversized model journal')
                try:
                    value = json.loads(line)
                    event = value['event']
                    sha = hashlib.sha256(encoded(dict(previous=previous, event=event))).hexdigest()
                    if value != dict(previous=previous, event=event, sha256=sha):
                        raise ValueError
                except (ValueError, TypeError, KeyError):
                    raise ContractError('Model journal hash mismatch') from None
                events.append(event)
                previous = sha
        return events

    def _append(self, path, event):
        with self._writer_lock:
            return self._append_locked(path,event)

    def _append_locked(self, path, event):
        # All reviewer callbacks serialize head/read/hash/write/fsync; ACK follows worker drain.
        events = self._read(path)
        previous = '0' * 64
        if events:
            with path.open('rb') as stream:
                for line in stream:
                    previous = json.loads(line)['sha256']
        sha = hashlib.sha256(encoded(dict(previous=previous, event=event))).hexdigest()
        raw = encoded(dict(previous=previous, event=event, sha256=sha)) + b'\n'
        if len(raw) > MAX_EVENT:
            raise ContractError('Model audit event exceeds budget')
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'ab') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())

    def submit(self, round_id, request, *, claim=None):
        self._identity(request.read())
        issuer = request.read().get('issuer_id')
        if self.busy or issuer in self.issuers():
            return False
        with self._slot_lock:
            if not self._free:
                return False  # every free slot's assessor is still held by a hung call
            assessor = self._free.pop(0)
        path = self.root / (hashlib.sha256(round_id.encode()).hexdigest() + '.jsonl')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        self._append(path, dict(kind='REQUEST', round_id=round_id, request=request.read(),
                                identity=self.identity, claim=claim))
        self.pending[round_id] = path
        self._issuer[round_id] = issuer
        self.active = round_id
        done = self.finished = self._running[round_id] = threading.Event()

        def run():
            try:
                hook = lambda event: self._append(path, event)
                deferred = getattr(assessor, 'assess_deferred', None)
                if deferred is not None:
                    # The real router must drain inner hard-timeout workers before RESULT/ACK.
                    # A returned UNAVAILABLE result alone does not prove that a provider has exited.
                    result = deferred(request, audit_hook=hook)
                else:
                    assessor.audit_hook = hook
                    result = assessor.assess(request)
                self._append(path, dict(kind='RESULT', result=result.read()))
            except Exception as error:
                # Never persist exception text: provider/OS exceptions can include credentials.
                self._append(path, dict(kind='ERROR', error=type(error).__name__))
            finally:
                with self._slot_lock:
                    self._free.append(assessor)  # only a call that returned frees its instance
                done.set()
        threading.Thread(target=run, name='larp-assessment', daemon=True).start()
        return True

    def ready(self):
        for round_id, path in self.pending.items():  # submission order within a process
            if self.running(round_id):
                continue
            events = self._read(path)
            first, last = events[0], events[-1]
            result = last.get('result') if last['kind'] == 'RESULT' else None
            state = 'COMPLETE' if result is not None else 'FAILED' if last['kind'] == 'ERROR' else 'INTERRUPTED'
            return dict(round_id=round_id, request=first['request'], result=result, claim=first.get('claim'),
                        audit=dict(state=state, events=events))
        return None

    def ack(self, round_id):
        path = self.pending[round_id]
        if self.running(round_id):
            raise ContractError('Cannot acknowledge a running assessment')
        self._append(path, dict(kind='ACK'))
        del self.pending[round_id]
        self._issuer.pop(round_id, None)
        self._running.pop(round_id, None)
        if round_id == self.active:
            self.active = None

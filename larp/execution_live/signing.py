"""Signing requests between the execution service and the signer host (IDEA-047 S01-S04; migration 009).

The signer host has no internet and reaches only the database (IDEA-046 B2), so the execution service on `primary`
cannot call it. `RemoteSigner` (the execution side's W04 Signer port) writes an immutable request carrying the gate
snapshot it just evaluated and waits a bounded time for the signer's answer: the signature in the fenced registry
(`execution_signatures`, at most one per attempt) or a refusal for that request. The signer side is
larp/signer/service.py. No key, and no signed byte other than the registry's, passes through these tables.
"""

from dataclasses import asdict, fields
import json
import time

from larp.execution import Blocked, Conflict, Gates, canonical, digest

SCHEMA = 'SigningRequest.v1'
REASON_LIMIT = 200


def request_document(state, attempt, gates, now_s):
    return dict(schema=SCHEMA, run_id=state.intent.run_id, economic_key=state.intent.key,
                attempt_id=attempt.attempt_id, step=attempt.step, payload_hash=attempt.payload.hash,
                epoch=attempt.epoch, guard_version=attempt.guard_version, gates=asdict(gates), requested_s=now_s)


GATE_INTEGERS = ('epoch', 'state_version', 'observed_at', 'expires_at')
GATE_OPTIONAL_INTEGERS = ('nonce', 'execution_version')


def _check_gates(gates):
    """Every gate field has its declared type, so a malformed request is refused instead of raising later in the
    signer's checks (IDEA-047 R2). A bool is never accepted where an int is required."""
    for field in fields(gates):
        value = getattr(gates, field.name)
        if field.name in GATE_INTEGERS:
            ok = type(value) is int
        elif field.name in GATE_OPTIONAL_INTEGERS:
            ok = value is None or type(value) is int
        else:
            ok = type(value) is bool
        if not ok:
            raise ValueError(field.name)


def read_request(request_id, raw):
    """The stored request, refused unless its bytes hash to its ID and it has the expected shape."""
    try:
        value = json.loads(bytes(raw))
        if (type(value) is not dict or value.get('schema') != SCHEMA or digest(value) != request_id
                or canonical(value).encode() != bytes(raw)):
            raise ValueError
        gates = Gates(**value['gates'])
        _check_gates(gates)
        for key in ('run_id', 'economic_key', 'attempt_id', 'step', 'payload_hash'):
            if type(value[key]) is not str or not value[key]:
                raise ValueError
        for key in ('epoch', 'guard_version', 'requested_s'):
            if type(value[key]) is not int:
                raise ValueError
    except (ValueError, TypeError, KeyError):
        raise Blocked('malformed signing request') from None
    return value, gates


def submit(store, request):
    """Insert the request (an identical re-send is a no-op); returns its ID. Another payload for the attempt fails."""
    raw, request_id = canonical(request).encode(), digest(request)
    with store.transaction() as db:
        db.execute('INSERT INTO signing_attempts VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                   (request['attempt_id'], request['run_id'], request['economic_key'], request['payload_hash']))
        row = db.execute('SELECT run_id,economic_key,payload_hash FROM signing_attempts WHERE attempt_id=%s',
                         (request['attempt_id'],)).fetchone()
        if tuple(row) != (request['run_id'], request['economic_key'], request['payload_hash']):
            raise Conflict('attempt already bound to another payload')
        db.execute('INSERT INTO signing_requests VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                   (request_id, request['run_id'], request['attempt_id'], request['payload_hash'], raw,
                    request['requested_s']))
        stored = db.execute('SELECT request FROM signing_requests WHERE request_id=%s', (request_id,)).fetchone()
        if bytes(stored[0]) != raw:
            raise Conflict('signing request bytes changed')
    return request_id


def pending(store, run_id, limit):
    """Requests of `run_id` with neither a refusal nor a signature for their attempt, oldest first."""
    with store.transaction() as db:
        return [(r[0], bytes(r[1])) for r in db.execute(
            'SELECT r.request_id,r.request FROM signing_requests r WHERE r.run_id=%s '
            'AND NOT EXISTS (SELECT 1 FROM signing_refusals f WHERE f.request_id=r.request_id) '
            'AND NOT EXISTS (SELECT 1 FROM execution_signatures s WHERE s.attempt_id=r.attempt_id) '
            'ORDER BY r.requested_s,r.request_id LIMIT %s', (run_id, limit))]


def refuse(store, run_id, request_id, reason, now_s):
    with store.transaction() as db:
        db.execute('INSERT INTO signing_refusals VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                   (request_id, run_id, str(reason)[:REASON_LIMIT], now_s))


def refusal(store, request_id):
    with store.transaction() as db:
        row = db.execute('SELECT reason FROM signing_refusals WHERE request_id=%s', (request_id,)).fetchone()
    return None if row is None else row[0]


class RemoteSigner:
    """The execution service's Signer port: asks the signer host through the database and waits a bounded time."""
    mode = 'live'

    def __init__(self, *, execution, guards, clock_s, timeout_s=20.0, poll_s=0.5, sleep=time.sleep,
                 monotonic=time.monotonic):
        if not timeout_s > 0 or not poll_s > 0:
            raise ValueError('Invalid signer wait budget')
        self.execution, self.guards, self.clock = execution, guards, clock_s
        self.timeout, self.poll, self.sleep, self.monotonic = timeout_s, poll_s, sleep, monotonic

    def sign(self, attempt_id, payload, epoch, guard_version):
        state, attempt = self.execution.attempt(attempt_id)
        if attempt.payload.hash != payload.hash or (attempt.epoch, attempt.guard_version) != (epoch, guard_version):
            raise Blocked('signing request does not match the authorized attempt')
        stored = self.lookup(attempt_id, payload.hash)
        if stored is not None:  # idempotent, as LocalSigner: the registry's bytes, never a second signature
            return self._checked(payload, stored)
        if attempt.state != 'AUTHORIZED':
            raise Blocked('attempt is not authorized for signing')
        gates = self.guards.snapshot(state.intent, self.clock())
        if (gates.epoch, gates.authority_version) != (epoch, guard_version):
            raise Blocked('authorization invalidated before signing')
        request_id = submit(self.execution.store, request_document(state, attempt, gates, gates.observed_at))
        deadline = self.monotonic() + self.timeout
        while True:
            stored = self.lookup(attempt_id, payload.hash)
            if stored is not None:
                return self._checked(payload, stored)
            reason = refusal(self.execution.store, request_id)
            if reason is not None:
                raise Blocked('signer refused: ' + reason)
            if self.monotonic() >= deadline:
                raise Blocked('signer timeout')
            self.sleep(self.poll)

    def _checked(self, payload, signed):
        if not self.verify(payload, signed):
            raise Blocked('signer bytes do not bind the authorized payload')
        return signed

    def verify(self, payload, signed):
        from larp.signer.local import verify
        return verify(payload, signed)

    def lookup(self, attempt_id, payload_hash):
        return self.execution.lookup(attempt_id, payload_hash)

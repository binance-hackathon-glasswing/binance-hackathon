"""Supervisor restart incidents and the autonomous HALT (DR-13; IDEA-042 item 5, C5).

No human action is part of either (F-114, never-do #1). The supervisor (deploy/systemd/larp-runtime.service) restarts
the same process on the same host only after systemd has ended the previous one, so the restarted process keeps the
run's owner epoch; epoch takeover stays reserved for standby promotion, which is disabled (GAP-02).

- `Sessions` records one durable row per process. A start that finds a session without a recorded end commits one
  INCIDENT (RESTART) journal event. A start whose build differs from the run's registered build is refused.
- `Guard` runs before each round. HALT stops new risk and signing (the coordinator plans nothing and the store refuses
  every command) while rounds keep running and logging. Clock HALTs are latched for the run. A delivery-deadline HALT
  clears once nothing is overdue; a repeated-failure HALT clears after enough consecutive successful rounds. Each
  HALT and each clear is a journal event. A journal that fails verification cannot accept a commit, so an integrity
  failure quarantines the run (every write and signature fenced) and reports the incident through the health check.
"""

from larp.audit.delivery import deadline_breaches, unlogged_rounds
from larp.contracts import ContractError, Document
from larp.runtime.coordinator import batch_for, halt_reasons
from larp.storage.postgres import IntegrityError

LATCHED = ('CLOCK',)
CLEARABLE = ('DELIVERY_DEADLINE', 'REPEATED_FAILURES')


def _commit(store, run_id, event_id, event, change):
    current = store.load(run_id)
    projection = current.read()['projection']
    change(projection)
    return store.commit(batch_for(current, event_id, event, projection=projection))


class Sessions:
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id

    def begin(self, *, session_id, build_id, now_ms):
        """Open this process's session. Returns the RESTART incident event if the previous process ended uncleanly."""
        if not session_id or not build_id or type(now_ms) is not int:
            raise ContractError('Session identity, build and time are required')
        with self.store.transaction() as db:
            run = self.store._run(db, self.run_id, lock=False)
            registered = (Document(bytes(run['projection'])).read().get('registered_version') or {}).get('build_id')
            rows = db.execute('SELECT session_id,build_id,ended_ms FROM process_sessions WHERE run_id=%s '
                              'ORDER BY started_ms,session_id', (self.run_id,)).fetchall()
        if any(r[0] == session_id for r in rows):
            raise ContractError('Session ID reused')
        expected = registered or (rows[-1][1] if rows else None)
        if expected is not None and build_id != expected:
            raise ContractError('Build differs from the registered version; a version change needs a version event')
        unclean = [r[0] for r in rows if r[2] is None]
        incident = None
        if unclean:
            # Journal first: if the process dies before the sessions are closed, the next start reports them again
            # under its own incident ID rather than losing the restart.
            incident = dict(kind='INCIDENT', incident=dict(type='RESTART', session_id=session_id, build_id=build_id,
                                                           previous_sessions=unclean, at_ms=now_ms))
            _commit(self.store, self.run_id, 'incident:restart:' + session_id, incident, lambda p: None)
        with self.store.transaction() as db:
            db.execute('UPDATE process_sessions SET ended_ms=%s WHERE run_id=%s AND ended_ms IS NULL',
                       (now_ms, self.run_id))
            db.execute('INSERT INTO process_sessions(run_id,session_id,build_id,started_ms,heartbeat_ms) '
                       'VALUES(%s,%s,%s,%s,%s)', (self.run_id, session_id, build_id, now_ms, now_ms))
        return incident

    def heartbeat(self, session_id, now_ms):
        with self.store.transaction() as db:
            db.execute('UPDATE process_sessions SET heartbeat_ms=%s WHERE run_id=%s AND session_id=%s AND ended_ms IS NULL',
                       (now_ms, self.run_id, session_id))

    def end(self, session_id, now_ms):
        """Clean shutdown only (SIGTERM handled). A crash never reaches this."""
        with self.store.transaction() as db:
            db.execute('UPDATE process_sessions SET ended_ms=%s WHERE run_id=%s AND session_id=%s AND ended_ms IS NULL',
                       (now_ms, self.run_id, session_id))


class Guard:
    def __init__(self, store, run_id, *, max_failures, clear_after):
        if type(max_failures) is not int or max_failures < 1 or type(clear_after) is not int or clear_after < 1:
            raise ContractError('Guard thresholds must be positive integers')
        self.store, self.run_id = store, run_id
        self.max_failures, self.clear_after = max_failures, clear_after

    def _halt(self, reason, now_ms, detail):
        event = dict(kind='HALT', reason=reason, latched=reason in LATCHED, at_ms=now_ms, detail=detail)

        def change(projection):
            reasons = dict((projection.get('halt') or {}).get('reasons', {}))
            reasons[reason] = dict(since_ms=now_ms, latched=reason in LATCHED, detail=detail)
            projection['halt'] = dict(reasons=reasons)
        _commit(self.store, self.run_id, f'halt:{reason}:{now_ms}', event, change)

    def _clear(self, reason, now_ms, detail):
        event = dict(kind='HALT_CLEARED', reason=reason, at_ms=now_ms, detail=detail)

        def change(projection):
            reasons = dict(projection['halt']['reasons'])
            reasons.pop(reason)
            if reasons:
                projection['halt'] = dict(reasons=reasons)
            else:
                projection.pop('halt')
        _commit(self.store, self.run_id, f'clear:{reason}:{now_ms}', event, change)

    def evaluate(self, now_ms):
        """Run every check; returns the actions taken, e.g. ['HALT:CLOCK'] or ['QUARANTINED:INTEGRITY']."""
        try:
            self.store.verified_snapshot(self.run_id, full=False)
        except IntegrityError:
            self.store.quarantine(self.run_id)
            return ['QUARANTINED:INTEGRITY']
        projection = self.store.load(self.run_id).read()['projection']
        active = set(halt_reasons(projection))
        actions = []
        last = projection.get('last_decision_ms')
        if type(now_ms) is not int or (last is not None and now_ms < last):
            if 'CLOCK' not in active:
                self._halt('CLOCK', now_ms if type(now_ms) is int else -1, dict(last_decision_ms=last))
                actions.append('HALT:CLOCK')
            return actions  # no other check is meaningful against a clock that moved backward
        with self.store.transaction() as db:
            overdue = deadline_breaches(db, self.run_id, now_ms)
        overdue = overdue + ['round:' + r for r in unlogged_rounds(projection, now_ms)]
        if overdue and 'DELIVERY_DEADLINE' not in active:
            self._halt('DELIVERY_DEADLINE', now_ms, dict(events=overdue[:20], count=len(overdue)))
            actions.append('HALT:DELIVERY_DEADLINE')
        elif not overdue and 'DELIVERY_DEADLINE' in active:
            self._clear('DELIVERY_DEADLINE', now_ms, dict(overdue=0))
            actions.append('CLEAR:DELIVERY_DEADLINE')
        health = projection.get('round_health') or {'failures': 0, 'successes': 0}
        if health['failures'] >= self.max_failures and 'REPEATED_FAILURES' not in active:
            self._halt('REPEATED_FAILURES', now_ms, dict(consecutive_failures=health['failures']))
            actions.append('HALT:REPEATED_FAILURES')
        elif 'REPEATED_FAILURES' in active and health['successes'] >= self.clear_after:
            self._clear('REPEATED_FAILURES', now_ms, dict(consecutive_successes=health['successes']))
            actions.append('CLEAR:REPEATED_FAILURES')
        return actions

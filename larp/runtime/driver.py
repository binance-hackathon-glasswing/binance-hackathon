"""Round driver for the supervised runtime (IDEA-048; IDEA-042 item 10). Shadow only: nothing is ever signed.

`Service` calls `RoundDriver.once(now_ms)` once per tick. A cycle:

1. ends every open round's pending intents through `ShadowExecution` (NOT_SUBMITTED, reason SHADOW_NO_SIGNING) and
   closes the round;
2. lets `Coordinator.recover` close any other closable round (an interrupted one closes truthfully);
3. runs at most one unit of evidence work (`EvidenceWork.next`) as one coordinator round;
4. repeats step 1, so a round planned in this cycle also closes in it.

Work comes, in priority order, from planner review jobs in the PostgreSQL scheduler (lane `evidence`), from ingestion
jobs the separate ingestion process wrote to the evidence store, and from a cadence round per slot when nothing else
is due. Round IDs follow from the job ID or the slot, so a restart never runs the same work twice.

The signing path (I3 -> execution service -> signer) is Gate B and is not wired here: `build_driver` in
larp/runtime/service.py refuses a configuration that asks for it.
"""

from datetime import datetime, timezone

from larp.contracts import ContractError, Document
from larp.intelligence.agent import build_request
from larp.intelligence.common import digest
from larp.intelligence.gate import initial_state
from larp.integration.settlement import settle
from larp.runtime.coordinator import halt_reasons
from larp.runtime.scheduler import Scheduler
from larp.storage.postgres import IntegrityError

SHADOW_REASON = 'SHADOW_NO_SIGNING'
SOURCE = 'sec-edgar'
MAX_ATTEMPTS = 3


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def _instant_ms(value):
    return int(datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp() * 1000)


class SessionCalendar:
    """`calendar(now_ms)` for the context builder from a frozen USRegularSessions.v1 document.

    `index` is the latest session whose open time has passed; `remaining` counts the sessions not yet closed. A time
    before the first session or after the last one is refused: the calendar must cover the whole run."""

    def __init__(self, document):
        c = document.read() if hasattr(document, 'read') else document
        if type(c) is not dict or c.get('schema') != 'USRegularSessions.v1' or not c.get('calendar_id'):
            raise ContractError('Expected a USRegularSessions.v1 calendar')
        sessions, previous = [], None
        for s in c.get('sessions') or []:
            index, opened, closed = s['session_index'], _instant_ms(s['open_at']), _instant_ms(s['close_at'])
            if type(index) is not int or index < 0 or not opened < closed:
                raise ContractError('Invalid calendar session')
            if previous is not None and (index != previous[0] + 1 or opened < previous[2]):
                raise ContractError('Calendar sessions must be consecutive and ordered')
            sessions.append((index, opened, closed))
            previous = sessions[-1]
        if not sessions:
            raise ContractError('Calendar has no sessions')
        self.sessions = tuple(sessions)

    def __call__(self, now_ms):
        if type(now_ms) is not int or now_ms < self.sessions[0][1] or now_ms >= self.sessions[-1][2]:
            raise ContractError('Decision time outside the session calendar')
        index = max(i for i, opened, _ in self.sessions if opened <= now_ms)
        return {'index': index, 'remaining': sum(1 for _, _, closed in self.sessions if closed > now_ms)}


class RuntimeHealth:
    """Planner gates from the store (larp/risk/planner.py; config/strategy/LIVE.md `new_spending_ok`)."""

    def __init__(self, store, run_id, epoch):
        self.store, self.run_id, self.epoch = store, run_id, epoch

    def __call__(self, current):
        try:
            self.store.verified_snapshot(self.run_id, full=False)
            journal = True
        except (IntegrityError, ContractError):
            journal = False
        projection = current['projection']
        # The guard latches a CLOCK HALT when decision time runs behind the last decision (supervision.py).
        gates = dict(integrity_ok=not current['quarantined'], journal_ok=journal,
                     ownership_ok=current['epoch'] == self.epoch,
                     clock_ok='CLOCK' not in halt_reasons(projection))
        pending = any(r.get('execution_pending') for r in projection.get('round_records', {}).values())
        gates['new_spending_ok'] = all(gates.values()) and not pending and not current['reservations']
        return gates


class ShadowExecution:
    """Ends every pending intent of every open round without signing, then closes the round.

    Each intent gets one ExecutionObservation.v1 of kind NOT_SUBMITTED with reason SHADOW_NO_SIGNING through the
    settlement reducer: reservations are released, balances do not change, and the round log lists the order without
    a tx hash and with the reason in `output.aborted`. The store's signing gate (`store.command`) is never called."""

    def __init__(self, coordinator, *, reducer=settle):
        self.coordinator, self.reducer = coordinator, reducer

    def settle_open(self, now_ms):
        c = self.coordinator
        closed = []
        for round_id, _ in c.store.open_rounds(c.run_id):
            current = c.store.load(c.run_id).read()
            record = current['projection'].get('round_records', {}).get(round_id)
            if record is None or not record.get('execution_pending'):
                continue
            final = set(record.get('final_intents', []))
            pending = [i for i in record['plan'].get('intents', []) if i['intent_id'] not in final]
            for n, intent in enumerate(pending):
                observation = dict(schema='ExecutionObservation.v1', run_id=c.run_id, wallet_id=current['wallet_id'],
                                   round_id=round_id, intent_id=intent['intent_id'],
                                   event_id='shadow:' + intent['intent_id'], kind='NOT_SUBMITTED',
                                   observed_at=iso(now_ms), settlement='FINAL', origin='EXECUTION_RECONCILER',
                                   intent_terminal=True, round_terminal=n == len(pending) - 1, reason=SHADOW_REASON)
                c.observe(observation['event_id'], Document.from_dict(observation), self.reducer)
            closed.append(c.close(round_id, now_ms, 'COMPLETE'))
        return closed


class EvidenceWork:
    """The next unit of evidence work for a round, or None.

    `issuers` maps issuer ID -> {"token", "underlying_id"} (the context builder's map); its order is the cadence order.
    """

    def __init__(self, *, store, evidence_store, run_id, config, issuers, profile_hash, cadence_ms,
                 lifecycle_policy=None, lease_ms=120_000):
        if type(cadence_ms) is not int or cadence_ms < 60_000:
            raise ContractError('Cadence must be at least one minute')
        self.store, self.evidence, self.run_id, self.config = store, evidence_store, run_id, config
        self.issuers, self.profile_hash, self.cadence = list(issuers), profile_hash, cadence_ms
        self.lifecycle_policy = lifecycle_policy
        self.scheduler = Scheduler(store, lease_ms=lease_ms)

    def round_for(self, base):
        """The round ID for the next attempt at `base`, or None when it is done. A round that planned (or recorded
        a rejection) is done; one that `recover` closed as interrupted is tried again under the next attempt number,
        up to MAX_ATTEMPTS, so a crash during assessment does not lose a filing."""
        open_ids = {r for r, _ in self.store.open_rounds(self.run_id)}
        for attempt in range(1, MAX_ATTEMPTS + 1):
            round_id = f'{base}#{attempt}'
            if any(self.store.receipt(self.run_id, p + round_id) for p in ('plan:', 'rejected:')) or round_id in open_ids:
                return None
            if not self.store.receipt(self.run_id, 'close:' + round_id):
                return round_id
        return None

    def _records(self, issuer, now_ms):
        records = [d.read() for d in self.evidence.records(issuer)]
        return [r for r in records if r['available_ms'] <= now_ms and r['quality'] != 'MISSING']

    def _latest(self, issuer, now_ms):
        held = self._records(issuer, now_ms)
        return [max(held, key=lambda r: (r['available_ms'], r['revision'], r['record_id']))] if held else []

    def _review(self, now_ms, epoch):
        claim = self.scheduler.claim(self.run_id, epoch, 'evidence', now_ms)
        if claim is None:
            return None
        job = claim.read()['job']
        issuer = job['payload'].get('issuer_id')
        records = self._latest(issuer, now_ms) if issuer in self.issuers else []
        return dict(round_id=self.round_for('review:' + job['job_id'][len('evidence:'):]), job=job,
                    issuer_id=issuer, records=records, claim=claim)

    def _ingested(self, now_ms):
        jobs = [j for j in self.evidence.jobs() if j.get('lane') == 'evidence'
                and (j.get('payload') or {}).get('kind') == 'ASSESS_FILING'
                and j['payload'].get('issuer_id') in self.issuers
                and j['due_ms'] <= now_ms < j['valid_until_ms']]
        for job in sorted(jobs, key=lambda j: (j['priority'], j['due_ms'], j['job_id'])):
            round_id = self.round_for('filing:' + job['job_id'][len('evidence:'):])
            if round_id is None:
                continue
            p = job['payload']
            records = [r for r in self._records(p['issuer_id'], now_ms) if r['record_id'] == p['record_id']]
            if not records:
                continue  # not yet available at this cutoff
            return dict(round_id=round_id, job=job, issuer_id=p['issuer_id'], records=records, claim=None)
        return None

    def _cadence(self, now_ms):
        slot = now_ms // self.cadence
        round_id = self.round_for(f'cadence:{slot}')
        if round_id is None or not self.issuers:
            return None
        issuer = self.issuers[slot % len(self.issuers)]
        records = self._latest(issuer, now_ms)
        if not records:
            return None  # nothing to assess for this slot's issuer
        payload = dict(kind='REASSESS_ISSUER', issuer_id=issuer, reason='SCHEDULED_CADENCE', slot=slot)
        job = dict(job_id='evidence:' + digest('larp.runtime.cadence-job.v1', payload), lane='evidence',
                   due_ms=slot * self.cadence, valid_until_ms=(slot + 1) * self.cadence, max_attempts=1,
                   priority=60, calendar_id='UTC', tzdata_version='utc-only-no-tzdata', missed='expire',
                   payload=payload)
        return dict(round_id=round_id, job=job, issuer_id=issuer, records=records, claim=None)

    def next(self, now_ms, epoch):
        return self._review(now_ms, epoch) or self._ingested(now_ms) or self._cadence(now_ms)

    def request(self, item, current, now_ms):
        issuer = item['issuer_id']
        state = (current['projection'].get('evidence') or {}).get(issuer) or initial_state(
            issuer, self.profile_hash, lifecycle_policy=self.lifecycle_policy)
        cursor = self.evidence.read_cursor(SOURCE, issuer)
        health = None
        if cursor is not None:
            h = cursor.read()['health']
            health = {'status': h['status'], 'last_success_ms': h['last_success_ms']}
        return build_request(job=item['job'], run_id=self.run_id, issuer_id=issuer, records=item['records'],
                             cutoff_ms=now_ms, context=state['context'], policy_profile_hash=self.profile_hash,
                             allowed_tools=list(self.config.tools), tool_calls=self.config.max_tool_calls,
                             deadline_ms=self.config.max_deadline_ms, source_health=health)


class RoundDriver:
    """`Service` driver: `ports` for the live-start checks, `once(now_ms)` per tick."""

    signing = False

    def __init__(self, coordinator, work, *, ports=None, execution=None):
        self.coordinator, self.work = coordinator, work
        self.execution = execution or ShadowExecution(coordinator)
        self.ports = dict(ports or {})

    def once(self, now_ms):
        c = self.coordinator
        summary = dict(closed=len(self.execution.settle_open(now_ms)), round_id=None)
        c.recover(now_ms)
        current = c.store.load(c.run_id).read()
        item = self.work.next(now_ms, current['epoch'])
        if item is not None:
            summary['round_id'] = item['round_id']
            if item['round_id'] is not None and item['records']:
                c.start(item['round_id'], self.work.request(item, current, now_ms), now_ms)
            if item['claim'] is not None:
                # Finished only after its round committed: a crash leaves the job to be claimed again once its lease
                # ends, and the round ID makes the rerun return the recorded round.
                self.work.scheduler.finish(c.run_id, item['claim'])
            summary['closed'] += len(self.execution.settle_open(now_ms))
        return summary

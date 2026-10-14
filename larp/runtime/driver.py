"""Round driver for the supervised runtime (IDEA-048, IDEA-050; IDEA-042 item 10).

`Service` calls `RoundDriver.once(now_ms)` once per tick. A cycle:

1. the execution step: `ShadowExecution` ends every pending intent unsigned (NOT_SUBMITTED, SHADOW_NO_SIGNING);
   `ServiceExecution` instead journals the execution service's observations (I4) and ends intents whose command
   expired unclaimed;
2. `Coordinator.recover` closes every closable round (an interrupted one closes truthfully);
3. while a committed command still waits to be claimed by the execution service, nothing else is committed: any
   commit would make the command stale (I3, `PostgresStore.command` needs the run's current version);
4. the first cycle of a UTC day rolls the daily risk anchor at the prefetched marks (`DayRoll`);
5. at most one unit of evidence work (`EvidenceWork.next`) runs as one coordinator round, after the market
   observations are fetched, so the decision time is never before them (#24); if the round asked for quotes and an
   executable one comes back, a bounded follow-up round plans from it;
6. step 1 again, so a shadow round planned in this cycle also closes in it.

Work comes, in priority order, from planner review jobs in the PostgreSQL scheduler (lane `evidence`), from ingestion
jobs the separate ingestion process wrote to the evidence store, and from a cadence round per slot when nothing else
is due. Round IDs follow from the job ID or the slot, so a restart never runs the same work twice.

The runtime never signs. Signing happens in the execution service (larp/execution_live/loop.py) and the signer host,
behind their own capability gates.
"""

from datetime import datetime, timezone
from fractions import Fraction
import json

from larp.contracts import ContractError, Document
from larp.execution import digest as execution_digest
from larp.intelligence.agent import build_request
from larp.intelligence.common import digest
from larp.intelligence.gate import initial_state
from larp.integration.runtime import ledger_from
from larp.integration.settlement import settle
from larp.risk.accounting import roll_day
from larp.runtime.coordinator import batch_for, halt_reasons
from larp.runtime.scheduler import Scheduler
from larp.storage.postgres import Conflict, IntegrityError
from larp.strategy.schema import equity, market_view

SHADOW_REASON = 'SHADOW_NO_SIGNING'
EXPIRED_REASON = 'COMMAND_EXPIRED_UNCLAIMED'
SOURCE = 'sec-edgar'
MAX_ATTEMPTS = 3
DAY_MS = 86_400_000
STEP_ORDER = {'approve': 0, 'swap': 1}


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

    def waiting(self, now_ms):
        return []  # nothing is handed to an execution service

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


def not_submitted(current, round_id, intent_id, event_id, now_ms, reason, round_terminal):
    """A final NOT_SUBMITTED fact for an intent that never reached the chain (larp/ports.py I4)."""
    return dict(schema='ExecutionObservation.v1', run_id=current['run_id'], wallet_id=current['wallet_id'],
                round_id=round_id, intent_id=intent_id, event_id=event_id, kind='NOT_SUBMITTED',
                observed_at=iso(now_ms), settlement='FINAL', origin='EXECUTION_RECONCILER', intent_terminal=True,
                round_terminal=round_terminal, reason=reason)


class ServiceExecution:
    """The runtime side of I3/I4 when a separate execution service executes committed commands.

    - `ingest` journals the observations the execution service wrote to `execution_observations` (the only table it
      shares with the runtime for facts), each event ID once. A row whose bytes do not hash to its stored hash is never
      committed. Facts are applied in causal order (approval before swap, broadcast before final); the reducer refuses
      a fact that arrives before the one it depends on, and passes repeat until none makes progress.
    - `expire` ends a planned intent that has no execution record once its command expired more than `grace_ms` ago:
      the execution service can no longer claim it (`PostgresStore.command` refuses an expired command and
      `Executor.create` an expired intent), so the round would otherwise stay open forever (#26).
    - `waiting` lists intents whose command is still claimable. The driver commits nothing while one exists.

    `wallet` is the execution wallet address: an execution record's key is derived from it (`Intent.key`).
    """

    def __init__(self, coordinator, *, wallet, grace_ms, reducer=settle):
        if type(grace_ms) is not int or grace_ms < 0:
            raise ContractError('Invalid expiry grace')
        if type(wallet) is not str or not wallet.startswith('0x') or len(wallet) != 42:
            raise ContractError('Execution wallet address required')
        self.coordinator, self.wallet, self.grace, self.reducer = coordinator, wallet.lower(), grace_ms, reducer

    def key(self, intent_id):
        c = self.coordinator
        return execution_digest([c.run_id, 56, self.wallet, intent_id])  # larp.execution.Intent.key

    def _pending(self, current):
        """(round_id, record, intent) for every planned intent of an open round that has no final fact yet."""
        for round_id, record in sorted(current['projection'].get('round_records', {}).items()):
            if not record.get('execution_pending'):
                continue
            final = set(record.get('final_intents', []))
            for intent in record['plan'].get('intents', []):
                if intent['intent_id'] not in final:
                    yield round_id, record, intent

    def _records(self, keys):
        if not keys:
            return set()
        with self.coordinator.store.transaction() as db:
            return {r[0] for r in db.execute('SELECT DISTINCT economic_key FROM execution_journal '
                                             'WHERE economic_key=ANY(%s)', (list(keys),))}

    def waiting(self, now_ms):
        c = self.coordinator
        current = c.store.load(c.run_id).read()
        if halt_reasons(current['projection']) or current['quarantined']:
            return []  # no command can be claimed; they end at expiry
        pending = [(r, i) for r, _, i in self._pending(current) if now_ms < i['expires_ms']]
        if not pending:
            return []
        claimed = self._records([self.key(i['intent_id']) for _, i in pending])
        with c.store.transaction() as db:
            versions = dict(db.execute('SELECT command_id,state_version FROM commands WHERE run_id=%s '
                                       'AND command_id=ANY(%s)', (c.run_id, [i['intent_id'] for _, i in pending])))
        return [i['intent_id'] for _, i in pending if self.key(i['intent_id']) not in claimed
                and versions.get(i['intent_id']) == current['version']]

    def reauthorize(self, now_ms):
        """Re-bind still-valid, unclaimed commands that a later commit made stale (PR #66 R3).

        A restart journals a RESTART incident, which moves the run version past a command planned just before the
        crash; `PostgresStore.command` would then refuse it. A command is reauthorized only if its intent is still
        planned in an open round, not final, holds its reservation, is unexpired, has no execution record, and the run
        is neither halted nor quarantined and still registered to this build. One journaled COMMAND_REAUTHORIZED event
        moves the commands' authority (epoch, state version) to that event; their bytes never change."""
        c = self.coordinator
        current = c.store.load(c.run_id).read()
        if halt_reasons(current['projection']) or current['quarantined']:
            return []
        if (current['projection'].get('registered_version') or {}).get('build_id') != c.version_id:
            return []
        held = {}
        for r in current['reservations']:
            held[r['intent_id']] = held.get(r['intent_id'], 0) + r['units']
        pending = [i for _, _, i in self._pending(current) if now_ms < i['expires_ms'] and held.get(i['intent_id'], 0) > 0]
        if not pending:
            return []
        claimed = self._records([self.key(i['intent_id']) for i in pending])
        with c.store.transaction() as db:
            versions = dict(db.execute("SELECT command_id,state_version FROM commands WHERE run_id=%s "
                                       "AND status='PENDING' AND command_id=ANY(%s)",
                                       (c.run_id, [i['intent_id'] for i in pending])))
        stale = sorted(i['intent_id'] for i in pending if self.key(i['intent_id']) not in claimed
                       and i['intent_id'] in versions and versions[i['intent_id']] != current['version'])
        if not stale:
            return []
        event = dict(kind='COMMAND_REAUTHORIZED', commands=stale, at_ms=now_ms)
        c.store.commit(batch_for(Document.from_dict(current), f"reauthorize:{current['version'] + 1}", event,
                                 reauthorize=stale))
        return stale

    def ingest(self):
        """Journal every new execution observation; returns (applied, refused) event IDs."""
        c = self.coordinator
        with c.store.transaction() as db:
            rows = db.execute('SELECT o.event_id,o.observation,o.observation_hash FROM execution_observations o '
                              'WHERE o.run_id=%s AND NOT EXISTS (SELECT 1 FROM events e WHERE e.run_id=o.run_id '
                              'AND e.event_id=o.event_id) ORDER BY o.event_id', (c.run_id,)).fetchall()
        pending, refused, applied = [], [], []
        for event_id, raw, stored_hash in rows:
            try:
                value = json.loads(bytes(raw))
                if type(value) is not dict or execution_digest(value) != stored_hash or value.get('event_id') != event_id:
                    raise ValueError
            except ValueError:
                refused.append(event_id)  # an execution outbox row changed after it was written
                continue
            pending.append(value)
        # Causal order within an intent: the approval before the swap, a broadcast before its final fact. A final
        # swap fact ends the intent, so an approval fact applied after it would be refused for good (and its gas
        # never accounted). Passes below still absorb ordering across intents.
        pending.sort(key=lambda v: (v.get('round_id', ''), v.get('intent_id', ''),
                                    STEP_ORDER.get(v.get('step'), 2), v.get('kind') != 'BROADCAST_ATTEMPTED',
                                    v.get('observed_at', ''), v['event_id']))
        progress = True
        while pending and progress:
            progress, later = False, []
            for value in pending:
                try:
                    c.observe(value['event_id'], Document.from_dict(value), self.reducer)
                except (ContractError, KeyError, TypeError) as error:
                    if isinstance(error, (Conflict, IntegrityError)):
                        raise
                    later.append(value)  # depends on a fact not journaled yet, or invalid: retried next pass
                else:
                    applied.append(value['event_id']); progress = True
            pending = later
        return applied, refused + [v['event_id'] for v in pending]

    def expire(self, now_ms):
        c = self.coordinator
        current = c.store.load(c.run_id).read()
        due = [(r, rec, i) for r, rec, i in self._pending(current) if now_ms >= i['expires_ms'] + self.grace]
        claimed = self._records([self.key(i['intent_id']) for _, _, i in due])
        ended = []
        for round_id, record, intent in due:
            if self.key(intent['intent_id']) in claimed:
                continue  # the execution service owns it and reports its outcome
            current = c.store.load(c.run_id).read()
            record = current['projection']['round_records'][round_id]
            final = set(record.get('final_intents', [])) | {intent['intent_id']}
            remaining = [i for i in record['plan'].get('intents', []) if i['intent_id'] not in final]
            fact = not_submitted(current, round_id, intent['intent_id'], 'expired:' + intent['intent_id'], now_ms,
                                 EXPIRED_REASON, not remaining)
            c.observe(fact['event_id'], Document.from_dict(fact), self.reducer)
            ended.append(intent['intent_id'])
        return ended

    def settle_open(self, now_ms):
        applied, refused = self.ingest()
        self.ingested, self.refused = applied, refused
        self.expired = self.expire(now_ms)
        return []  # rounds close through Coordinator.recover once every intent is final


class MarketFeed:
    """The context builder's market port: observations fetched once per round, before the round starts.

    `refresh` performs the I/O; the coordinator reads its decision clock afterwards, so no observation is future data
    at the round's cutoff (#24). Quoted observations from `quote` replace the plain ones for their symbol until
    `clear_quotes`; a port failure is replayed to the builder, which records CONTEXT_UNAVAILABLE as before."""

    def __init__(self, port, *, gas=None):
        self.port, self.gas, self.result, self.quoted, self.gas_result = port, gas, None, {}, []

    def refresh(self, now_ms):
        try:
            self.result = (True, self.port(now_ms))
        except Exception as error:
            self.result = (False, error)
        if self.gas is not None:
            try:
                self.gas_result = list(self.gas(now_ms))
            except Exception:
                self.gas_result = []  # no gas quote: the planner asks again and tops up nothing
        return self.result[0]

    def gas_quotes(self, now_ms):
        """The builder's `gas_quotes` port: native top-up quotes fetched with the market (PR #41 NativeGasQuotePort)."""
        if self.result is None:
            self.refresh(now_ms)
        return list(self.gas_result)

    def observations(self):
        ok, value = self.result if self.result is not None else (False, ContractError('Market not fetched'))
        return value if ok else None

    def __call__(self, now_ms):
        if self.result is None:
            self.refresh(now_ms)
        ok, value = self.result
        if not ok:
            raise value
        return [self.quoted.get(o.get('symbol'), o) for o in value]

    def quote(self, request):
        """One MarketRequest.v1 through the port's quote path; True when it returned an executable quote."""
        observation = self.port.observe(request)
        if observation.get('quotes'):
            self.quoted[observation['symbol']] = observation
            return True
        return False

    def clear_quotes(self):
        self.quoted = {}


class DayRoll:
    """The daily risk anchor (#31): `roll_day` at the first cycle of a UTC day, inside `window_ms` of midnight.

    The anchor is the equity at the marks fetched for that cycle. Without a usable mark for every held position, or
    outside the window, nothing is committed: the planner keeps refusing new risk for a day whose anchor is missing
    (`risk.day` is not today). One DAY_ROLLED event per day; replay recommits it as a recorded fact."""

    def __init__(self, coordinator, *, window_ms):
        if type(window_ms) is not int or not 0 < window_ms < DAY_MS:
            raise ContractError('Invalid day-roll window')
        self.coordinator, self.window = coordinator, window_ms

    def due(self, current, now_ms):
        projection = current['projection']
        risk = projection.get('risk_state') or projection['portfolio'].get('risk') or {}
        today = datetime.fromtimestamp(now_ms / 1000, timezone.utc).date().isoformat()
        return type(risk.get('day')) is str and risk['day'] < today

    def __call__(self, now_ms, observations):
        c = self.coordinator
        current = c.store.load(c.run_id).read()
        if not self.due(current, now_ms):
            return None
        midnight = now_ms - now_ms % DAY_MS
        if now_ms - midnight > self.window:
            return 'OUTSIDE_WINDOW'
        if observations is None:
            return 'MARKET_UNAVAILABLE'
        builder = c.context_builder
        projection = current['projection']
        ledger = ledger_from(projection, current['reservations'])
        try:
            market = market_view(observations, builder.universe, datetime.fromtimestamp(now_ms / 1000, timezone.utc),
                                 builder.profile)
            anchor = int(equity(ledger, market))
        except (ContractError, KeyError, TypeError, ValueError):
            return 'MARK_UNAVAILABLE'
        if anchor < 1:
            return 'MARK_UNAVAILABLE'
        boundary = datetime.fromtimestamp(midnight / 1000, timezone.utc).isoformat()
        ledger.pop('reservations', None)
        rolled = roll_day(Document.from_dict(dict(ledger, reservations={})), boundary=boundary,
                          anchor_units=anchor).read()['risk']
        projection['risk_state'] = rolled
        marks = sorted((m['symbol'], m.get('content_hash')) for m in observations if type(m) is dict)
        event = dict(kind='DAY_ROLLED', day=rolled['day'], boundary=boundary, anchor_units=anchor,
                     decided_ms=now_ms, marks=[list(m) for m in marks])
        c.store.commit(batch_for(Document.from_dict(current), 'day:' + rolled['day'], event, projection=projection))
        return 'ROLLED'


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
    """`Service` driver: `ports` for the live-start checks, `once(now_ms)` per tick.

    `market` (a MarketFeed) enables the decision cutoff after the fetch, the quote follow-up and, with `day_roll`, the
    daily anchor. Without it the driver runs as IDEA-048's tests built it: the builder's port is called inside the
    round."""

    signing = False

    def __init__(self, coordinator, work, *, ports=None, execution=None, market=None, day_roll=None,
                 max_quote_rounds=0, max_quote_requests=2):
        self.coordinator, self.work = coordinator, work
        self.execution = execution or ShadowExecution(coordinator)
        self.ports = dict(ports or {})
        self.market, self.day_roll = market, day_roll
        if type(max_quote_rounds) is not int or max_quote_rounds < 0 or type(max_quote_requests) is not int \
                or max_quote_requests < 1:
            raise ContractError('Invalid quote follow-up bounds')
        self.max_quote_rounds, self.max_quote_requests = max_quote_rounds, max_quote_requests

    def _plan(self, round_id):
        event = self.coordinator.store.event(self.coordinator.run_id, 'plan:' + round_id)
        return (event or {}).get('record', {}).get('plan') or {}

    def _round(self, round_id, item, now_ms):
        c = self.coordinator
        if self.market is not None:
            self.market.refresh(now_ms)  # before the round: its decision time follows the fetch (#24)
        current = c.store.load(c.run_id).read()
        c.start(round_id, self.work.request(item, current, now_ms), now_ms)

    def _quotes(self, round_id, item, now_ms, summary):
        """Bounded follow-up rounds while the last plan asked for quotes and an executable one came back."""
        for n in range(1, self.max_quote_rounds + 1):
            plan = self._plan(round_id)
            requests = [r for r in plan.get('quote_requests', []) if r.get('symbol') != 'BNB']
            if plan.get('intents') or not requests:
                return
            executable = False
            for request in requests[:self.max_quote_requests]:
                try:
                    executable |= self.market.quote(request)
                except Exception as error:  # an unavailable quote is a hold, never a failed round
                    summary.setdefault('quote_errors', []).append(type(error).__name__)
            summary.setdefault('quotes_requested', 0)
            summary['quotes_requested'] += min(len(requests), self.max_quote_requests)
            if not executable:
                self.market.clear_quotes()
                return
            round_id = f"{item['round_id']}/quote{n}"
            summary['quote_round_id'] = round_id
            try:
                c = self.coordinator
                current = c.store.load(c.run_id).read()
                # The quoted observations stand in for this round's fetch; the decision clock follows them.
                c.start(round_id, self.work.request(item, current, now_ms), now_ms)
            finally:
                self.market.clear_quotes()

    def once(self, now_ms):
        c = self.coordinator
        summary = dict(closed=len(self.execution.settle_open(now_ms)), round_id=None)
        for key in ('ingested', 'refused', 'expired'):
            if getattr(self.execution, key, None):
                summary[key] = list(getattr(self.execution, key))
        c.recover(now_ms)
        reauthorize = getattr(self.execution, 'reauthorize', None)
        if reauthorize is not None:
            reauthorized = reauthorize(now_ms)
            if reauthorized:
                summary['reauthorized'] = reauthorized
        waiting = self.execution.waiting(now_ms)
        if waiting:
            # I3 hand-off: any commit now would make these commands stale before the execution service claims them.
            summary['waiting_for_claim'] = waiting
            return summary
        if self.day_roll is not None and self.market is not None:
            current = c.store.load(c.run_id).read()
            if self.day_roll.due(current, now_ms):
                self.market.refresh(now_ms)
                # The marks are stamped when their responses arrive: value them at a time read after the fetch, and
                # check the day and the window again at that time (PR #66 R2).
                decided = max(now_ms, c.clock())
                summary['day_roll'] = self.day_roll(decided, self.market.observations())
        current = c.store.load(c.run_id).read()
        item = self.work.next(now_ms, current['epoch'])
        if item is not None:
            summary['round_id'] = item['round_id']
            if item['round_id'] is not None and item['records']:
                self._round(item['round_id'], item, now_ms)
                if self.market is not None and self.max_quote_rounds:
                    self._quotes(item['round_id'], item, now_ms, summary)
            if item['claim'] is not None:
                # Finished only after its round committed: a crash leaves the job to be claimed again once its lease
                # ends, and the round ID makes the rerun return the recorded round.
                self.work.scheduler.finish(c.run_id, item['claim'])
            if not self.execution.waiting(now_ms):  # never ingest over a command that still awaits its claim
                summary['closed'] += len(self.execution.settle_open(now_ms))
        return summary

"""Round driver for the supervised runtime (IDEA-048, IDEA-050; IDEA-042 item 10).

`Service` calls `RoundDriver.once(now_ms)` once per tick. A cycle:

1. the execution step: `ShadowExecution` ends every pending intent unsigned (NOT_SUBMITTED, SHADOW_NO_SIGNING);
   `ServiceExecution` instead journals the execution service's observations (I4) and ends intents whose command
   expired unclaimed;
2. `Coordinator.recover` closes every closable round (an interrupted one closes truthfully);
3. while a committed command still waits to be claimed by the execution service, nothing else is committed: any
   commit would make the command stale (I3, `PostgresStore.command` needs the run's current version);
4. the first cycle of a UTC day rolls the daily risk anchor at the prefetched marks (`DayRoll`);
   a round whose orders are all broadcast or final is logged at once (`log_disposed`), before receipts are final;
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
from larp.execution import Blocked, DependencyUnavailable
from larp.execution import digest as execution_digest
from larp.intelligence.agent import build_request
from larp.intelligence.common import digest
from larp.intelligence.gate import initial_state
from larp.integration.runtime import ledger_from
from larp.runtime import halts
from larp.integration.settlement import balances_of, settle
from larp.risk.accounting import roll_day
from larp.risk.reconcile import adjust_ledger, compare_balances
from larp.runtime.coordinator import batch_for, halt_reasons
from larp.runtime.scheduler import Scheduler
from larp.storage.postgres import Conflict, IntegrityError
from larp.strategy.schema import equity, market_view

SHADOW_REASON = 'SHADOW_NO_SIGNING'
EXPIRED_REASON = 'COMMAND_EXPIRED_UNCLAIMED'
SOURCE = 'sec-edgar'
MAX_ATTEMPTS = 3
MAX_QUOTE_CHAIN = 8  # follow-up depth the work scans for an interrupted child; the driver bounds what it runs
DAY_MS = 86_400_000
STEP_ORDER = {'approve': 0, 'swap': 1}


def quote_drop_reason(error):
    """A journaled reason for a refused quote: our own refusal classes carry fixed messages; any other exception is
    named by class only, since its text may hold a provider URL or credential (IDEA-088 QV8)."""
    from larp.marketdata.web3 import Unavailable
    name = type(error).__name__
    if isinstance(error, Unavailable) and 'DIRTY_ROUTER_ALLOWANCE:' in str(error):
        return 'DIRTY_ROUTER_ALLOWANCE:' + str(error).split('DIRTY_ROUTER_ALLOWANCE:', 1)[1]
    if isinstance(error, (Unavailable, Blocked, ContractError)):
        return (name + ': ' + str(error))[:200]
    return name


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

    def window(self, now_ms):
        """B6 regular-session bounds; off-hours keep the latest opened session.

        Use the frozen calendar, including early closes and the next actual open,
        rather than midnight/weekday arithmetic. The last close ends coverage.
        """
        index = self(now_ms)['index']
        position = next(n for n, s in enumerate(self.sessions) if s[0] == index)
        _, opened, closed = self.sessions[position]
        next_open = self.sessions[position + 1][1] if position + 1 < len(self.sessions) else closed
        return dict(index=index, open_ms=opened, close_ms=closed, next_open_ms=next_open)


class RuntimeHealth:
    """Planner gates from the store (larp/risk/planner.py; config/strategy/LIVE.md `new_spending_ok`)."""

    def __init__(self, store, run_id, epoch, *, balances=None):
        self.store, self.run_id, self.epoch = store, run_id, epoch
        self.balances = balances  # a BalanceCheck adds `balances_ok` (IDEA-055); offline fixtures have none

    def __call__(self, current):
        try:
            self.store.verified_snapshot(self.run_id, full=False)
            journal = True
        except (IntegrityError, ContractError):
            journal = False
        projection = current['projection']
        # The guard latches a CLOCK HALT when decision time runs behind the last decision (supervision.py).
        gates = dict(integrity_ok=not current['quarantined'] and not projection.get('abnormal_outcomes'), journal_ok=journal,
                     ownership_ok=current['epoch'] == self.epoch,
                     clock_ok='CLOCK' not in halt_reasons(projection))
        if self.balances is not None:
            # Feeds only new_spending_ok, never the planner's global gates: sales and the flatten continue (#36).
            gates['balances_ok'] = self.balances.ok(projection)
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
        if current['quarantined']:
            return []  # no command can be claimed; they end at expiry
        # Under a HALT only a pausing HALT's planned mandatory sells can be claimed (D-DN-09); the rest end at expiry.
        pending = [(r, i) for r, _, i in self._pending(current) if now_ms < i['expires_ms']
                   and halts.permits(current['projection'], r, i['intent_id'])]
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
        if current['quarantined']:
            return []
        if (current['projection'].get('registered_version') or {}).get('build_id') != c.version_id:
            return []
        held = {}
        for r in current['reservations']:
            held[r['intent_id']] = held.get(r['intent_id'], 0) + r['units']
        pending = [i for r, _, i in self._pending(current) if now_ms < i['expires_ms'] and held.get(i['intent_id'], 0) > 0
                   and halts.permits(current['projection'], r, i['intent_id'])]
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

    def seal(self):
        """Clear `execution_pending` for every round whose planned intents all have a terminal fact in the journal.

        The execution service attests `round_terminal` from what the journal held when it built each fact, so two
        intents that finish before the runtime journals either both say false (PR #66 Y1). The journal's own terminal
        facts are the authority the coordinator checks the attestation against; once every planned intent has one, the
        round is terminal whatever the attestations said. One ROUND_SEALED event per round; replay recommits it."""
        c = self.coordinator
        sealed = []
        current = c.store.load(c.run_id).read()
        for round_id, record in sorted(current['projection'].get('round_records', {}).items()):
            planned = {i['intent_id'] for i in record['plan'].get('intents', [])}
            if not record.get('execution_pending') or not planned or not planned <= set(record.get('final_intents', [])):
                continue
            current = c.store.load(c.run_id).read()
            projection = current['projection']
            projection['round_records'][round_id]['execution_pending'] = False
            event = dict(kind='ROUND_SEALED', round_id=round_id, final_intents=sorted(planned))
            c.store.commit(batch_for(Document.from_dict(current), 'sealed:' + round_id, event, projection=projection))
            sealed.append(round_id)
        return sealed

    def log_disposed(self, now_ms):
        """Log every open round whose orders are all disposed (broadcast or final) but not yet final (#28)."""
        c = self.coordinator
        logged = []
        for round_id, record in sorted(c.store.load(c.run_id).read()['projection'].get('round_records', {}).items()):
            if record.get('execution_pending') and not record.get('logged') and c.disposed(record):
                c.log_round(round_id, now_ms)
                logged.append(round_id)
        return logged

    def settle_open(self, now_ms):
        applied, refused = self.ingest()
        self.ingested, self.refused = applied, refused
        self.expired = self.expire(now_ms)
        self.sealed = self.seal()
        self.logged = self.log_disposed(now_ms)
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
        """One MarketRequest.v1 through the port's quote path; True when it returned an executable quote. Otherwise
        `refused` holds the port's quote status (IDEA-088 QV8)."""
        observation = self.port.observe(request)
        if observation.get('quotes'):
            self.quoted[observation['symbol']] = observation
            return True
        self.refused = observation.get('quote_status') or 'NO_EXECUTABLE_QUOTE'
        return False

    def clear_quotes(self):
        self.quoted = {}


class DayRoll:
    """The daily risk anchor (#31): `roll_day` at the first cycle of a UTC day, inside `window_ms` of midnight.

    The anchor is the equity at the marks fetched for that cycle. Without a usable mark for every held position, or
    outside the window, nothing is committed: the planner keeps refusing new risk for a day whose anchor is missing
    (`risk.day` is not today). One DAY_ROLLED event per day; replay recommits it as a recorded fact.

    A price-jump hold inside the window defers the roll; the deferred day then rolls on the first cycle after the hold
    clears or expires, even past the window (IDEA-055 R2). The deferred day is journaled so a process restart cannot lose it."""

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
        projection = current['projection']
        deferred = projection.get('day_roll_deferred_ms')
        if now_ms - midnight > self.window and deferred != midnight:
            return 'OUTSIDE_WINDOW'
        if active_holds(current['projection'], now_ms):
            return self._defer(current, midnight, now_ms)
        if observations is None:
            return 'MARKET_UNAVAILABLE'
        builder = c.context_builder
        projection = current['projection']
        # The midnight fetch can be the first observation of a split. The round that journals its hold runs
        # after DayRoll, so checking only persisted holds would anchor old units at the newly changed price.
        if getattr(builder, 'price_jump', None) is not None:
            marks, holds = builder._jumps(projection, observations, now_ms)
            if holds:
                return self._defer(current, midnight, now_ms, jumps=dict(marks=marks, price_jump=holds))
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
        projection.pop('day_roll_deferred_ms', None)
        marks = sorted((m['symbol'], m.get('content_hash')) for m in observations if type(m) is dict)
        event = dict(kind='DAY_ROLLED', day=rolled['day'], boundary=boundary, anchor_units=anchor,
                     decided_ms=now_ms, marks=[list(m) for m in marks])
        c.store.commit(batch_for(Document.from_dict(current), 'day:' + rolled['day'], event, projection=projection))
        return 'ROLLED'

    def _defer(self, current, midnight, now_ms, *, jumps=None):
        """Persist both an existing hold and one first discovered by the midnight fetch (RR2-R2, PR115-C02)."""
        projection = current['projection']
        if (projection.get('day_roll_deferred_ms') != midnight
                or any(projection.get(k) != value for k, value in (jumps or {}).items())):
            projection.update(jumps or {})
            projection['day_roll_deferred_ms'] = midnight
            day = datetime.fromtimestamp(midnight / 1000, timezone.utc).date().isoformat()
            event = dict(kind='DAY_ROLL_DEFERRED', day=day, midnight_ms=midnight, deferred_ms=now_ms)
            event_id = f"day-deferred:{day}:{current['version'] + 1}"
            self.coordinator.store.commit(batch_for(Document.from_dict(current), event_id, event,
                                                     projection=projection))
        return 'PRICE_JUMP_HOLD'


def active_holds(projection, now_ms):
    """Price-jump holds (IDEA-055 PR 4) that have not expired: {symbol: hold}."""
    return {s: h for s, h in (projection.get('price_jump') or {}).items() if now_ms < h['until_ms']}


class BalanceCheck:
    """Chain-balance reconciliation (IDEA-055, #36; owner decisions 2026-10-16): the chain wins.

    `reader(now_ms)` returns a ChainBalances.v1 (larp/execution_live/balances.py). With reservations, an open round or
    an execution pending, nothing is read or journaled: the chain would differ from the ledger by the trade in flight.
    A check is journaled as BALANCE_CHECKED (a recorded fact on replay) when it is this process's first, when its
    outcome differs from the last journaled one, or after `heartbeat_ms` without a journaled check; every commit copies
    the projection, so an unchanged result every interval would only grow the journal. A deficit or a newly surplus
    asset is also an INCIDENT.

    A mismatch on an eligible asset is adopted only when the next comparable check, `retry_ms` later, reads the same
    chain units with the same ledger units and `settled_block`, and no wallet activity occurred in between
    (reservations, commands or receipts). Journal-proven hold-only rounds may continue (PR115-C04).
    One bad read never becomes the ledger. Adoption is one BALANCE_ADJUSTED event
    (`adjust_ledger`: units only, cost unchanged) plus one INCIDENT per asset. The candidate is kept in memory only.
    Until adoption a deficit is subtracted in the planner's view (ContextBuilder, D1) and new spending waits (`ok`);
    sales and the flatten continue. `ok` counts only a check made by this process, so a restored or restarted run
    reconciles before it takes new risk. A comparable check after a price jump clears that symbol's hold when the
    asset matches or is adopted."""

    COMPARABLE = ('MATCH', 'SURPLUS_ONLY', 'DEFICIT')

    def __init__(self, coordinator, reader, *, interval_ms, max_age_ms, retry_ms=60_000, heartbeat_ms=3_600_000):
        if (not all(type(v) is int and v > 0 for v in (interval_ms, max_age_ms, retry_ms, heartbeat_ms))
                or max_age_ms < interval_ms):
            raise ContractError('Invalid balance-check interval, maximum age, retry or heartbeat')
        self.coordinator, self.reader = coordinator, reader
        self.interval, self.max_age, self.retry, self.heartbeat = interval_ms, max_age_ms, retry_ms, heartbeat_ms
        self.next_ms = 0  # the first cycle checks
        self.ok_ms = None  # the last check of this process that left no unadopted deficit
        self.journaled_ms = None
        self.candidate = None  # the first read of a mismatch, awaiting its confirming read
        self.attempt_ms = None  # the last time this process tried a check

    def due(self, now_ms, projection=None):
        if now_ms >= self.next_ms:
            return True
        # A price jump newer than the last attempt is checked at once (IDEA-055 PR 4).
        holds = active_holds(projection or {}, now_ms)
        return self.attempt_ms is not None and any(h['jump_ms'] >= self.attempt_ms for h in holds.values())

    def ok(self, projection):
        state = projection.get('balance_check') or {}
        return (self.ok_ms is not None and state.get('comparable_status') in ('MATCH', 'SURPLUS_ONLY')
                and self.coordinator.clock() - self.ok_ms < self.max_age)

    def in_flight(self, current):
        c = self.coordinator
        rounds = current['projection'].get('round_records', {}).values()
        return bool(current['reservations'] or c.store.open_rounds(c.run_id)
                    or any(r.get('execution_pending') for r in rounds))

    def _confirm(self, current, check, observation, observation_hash, now_ms):
        """Adjustments this check confirms; the rest of its mismatches become the next candidate.

        Confirmation needs `retry_ms` since the first read and a strictly newer block (R1, ALLPR-R1): an earlier
        check, such as the one a price jump triggers, keeps the first read as the candidate."""
        mismatched = {a: r for a, r in check['assets'].items() if r['class'] != 'MATCH'}
        first, confirmed = self.candidate, []
        comparable = (first is not None and first['settled_block'] == check['settled_block']
                      and first['epoch'] == current['epoch']
                      and (first['version'] == current['version'] or self._quiet_since(first, current)))
        if comparable and now_ms - first['checked_ms'] < self.retry:
            # An identical early read preserves the first candidate's time, but an early contradictory read
            # breaks the sequence for that asset. Otherwise A -> MATCH/B -> A could confirm the original A.
            first['assets'] = {asset: seen for asset, seen in first['assets'].items()
                               if asset in mismatched and
                               (seen['chain_units'], seen['ledger_units']) ==
                               (mismatched[asset]['chain_units'], mismatched[asset]['ledger_units'])}
            if not first['assets']:
                self.candidate = None
            return confirmed
        if comparable and check['block_number'] > first['block_number']:
            positions = current['projection']['portfolio']['positions']
            for asset, row in sorted(mismatched.items()):
                seen = first['assets'].get(asset)
                if seen is None or (seen['chain_units'], seen['ledger_units']) != (row['chain_units'],
                                                                                    row['ledger_units']):
                    continue
                adjustment = dict(asset=asset, ledger_before=row['ledger_units'], chain_units=row['chain_units'],
                                  delta=row['difference'], reason='SURPLUS' if row['difference'] > 0 else 'DEFICIT',
                                  first_block=first['block_number'], confirm_block=check['block_number'],
                                  first_observation_sha256=first['observation_sha256'],
                                  confirm_observation_sha256=observation_hash)
                if asset not in ('USDT', 'BNB'):
                    adjustment['decimals'] = (positions[asset]['decimals'] if asset in positions
                                              else observation['tokens'][asset]['decimals'])
                confirmed.append(adjustment)
        adopted = {a['asset'] for a in confirmed}
        rest = {a: r for a, r in mismatched.items() if a not in adopted}
        self.candidate = (dict(assets=rest, block_number=check['block_number'], settled_block=check['settled_block'],
                               observation_sha256=observation_hash, version=current['version'], checked_ms=now_ms,
                               epoch=current['epoch'], portfolio=current['projection']['portfolio'],
                               execution_state=current['execution_state'])
                          if rest else None)
        return confirmed

    def _quiet_since(self, first, current):
        """Prove that intervening commits are wallet-neutral; checking only the final ledger misses transient
        reservations. A bounded journal suffix preserves that evidence without exporting the whole run."""
        allowed = {'ROUND_PLANNED', 'PLAN_REJECTED', 'ROUND_LOGGED', 'ROUND_CLOSED',
                   'BALANCE_CHECKED', 'INCIDENT', 'HALT', 'HALT_CLEARED', 'DAY_ROLLED', 'DAY_ROLL_DEFERRED'}
        # A suffix read from this process's checkpoint: a full verification here runs inside the cycle watchdog and
        # grows with the run (IDEA-095).
        batches = self.coordinator.store.journal(self.coordinator.run_id, after_version=first['version'],
                                                  through_version=current['version'], full=False)
        if len(batches) != current['version'] - first['version']:
            return False
        for batch in batches:
            b = batch.read()
            event, projection = b['event'], b['projection']
            if (event['kind'] not in allowed or b['owner_epoch'] != first['epoch']
                    or b['commands'] or b['reservation_deltas']
                    or b['execution_state'] != first['execution_state']
                    or projection['portfolio'] != first['portfolio']
                    or projection.get('settled_block') != first['settled_block']):
                return False
            record = event.get('record') or {}
            plan = record.get('plan') or {}
            if record.get('execution_pending') or plan.get('intents') or plan.get('reservation_deltas'):
                return False
        return True

    def _commit(self, current, event_id, event, projection=None):
        """Commit one event; this process's own commits do not count as activity between two checks."""
        c = self.coordinator
        before = current.read()['version']
        c.store.commit(batch_for(current, event_id, event, projection=projection))
        after = c.store.load(c.run_id)
        if (self.candidate is not None and self.candidate['version'] == before
                and after.read()['version'] == before + 1):
            committed = after.read()
            self.candidate.update(version=committed['version'], portfolio=committed['projection']['portfolio'],
                                  execution_state=committed['execution_state'])
        return after

    def __call__(self, now_ms):
        c = self.coordinator
        self.attempt_ms = now_ms
        current = c.store.load(c.run_id).read()
        if self.in_flight(current):
            self.next_ms = now_ms + self.retry
            return 'IN_FLIGHT'
        projection = current['projection']
        previous = projection.get('balance_check') or {}
        observation_hash = None
        try:
            observation = self.reader(now_ms)
            check = compare_balances(projection['portfolio'], observation,
                                     settled_block=projection.get('settled_block'))
            observation_hash = Document.from_dict(observation).digest('ChainBalances.v1')
        except DependencyUnavailable:
            check = dict(schema='BalanceCheck.v1', status='SKIPPED', reason='RPC_UNAVAILABLE')
        except (Blocked, ContractError, KeyError, TypeError, ValueError):
            check = dict(schema='BalanceCheck.v1', status='SKIPPED', reason='OBSERVATION_INVALID')
        status = check['status']
        state = dict(previous, status=status, reason=check.get('reason'), checked_ms=now_ms)
        incidents, adjustments = [], []
        holds = dict(projection.get('price_jump') or {})
        if status in self.COMPARABLE:
            new_surplus = sorted(set(check['surplus']) - set(previous.get('surplus_assets', [])))
            if status == 'DEFICIT' and check['deficits'] != previous.get('deficits'):
                incidents.append(dict(type='BALANCE_DEFICIT', deficits=check['deficits']))
            if new_surplus:
                incidents.append(dict(type='BALANCE_SURPLUS', assets=new_surplus,
                                      differences={a: check['assets'][a]['difference'] for a in new_surplus}))
            state.update(comparable_status=status, deficits=check['deficits'], surplus_assets=check['surplus'],
                         block_number=check['block_number'])
            adjustments = self._confirm(current, check, observation, observation_hash, now_ms)
            for symbol, hold in list(holds.items()):
                row = check['assets'].get(symbol)
                # R3: the finalized block read just after a jump may predate the split; wait retry_ms before a MATCH
                # counts as the chain agreeing.
                if now_ms - hold['jump_ms'] >= self.retry and row is not None and row['class'] == 'MATCH':
                    del holds[symbol]  # the chain agrees after the jump: the mark is real
            pending = self.candidate is not None or bool(active_holds(dict(price_jump=holds), now_ms))
            self.next_ms = now_ms + (self.retry if pending else self.interval)
        else:
            self.next_ms = now_ms + self.retry  # a skip keeps the last deficits, the last good time and the candidate
        outcome = ('status', 'reason', 'comparable_status', 'deficits', 'surplus_assets')
        changed = any(state.get(k) != previous.get(k) for k in outcome) or holds != (projection.get('price_jump') or {})
        result = status if status in self.COMPARABLE else 'SKIPPED:' + check['reason']
        if adjustments:
            result = 'ADJUSTED'
        elif not (changed or incidents or self.journaled_ms is None or now_ms - self.journaled_ms >= self.heartbeat):
            self._settle_gate(status, state, now_ms)
            return result
        self.journaled_ms = now_ms
        projection['balance_check'] = state
        if 'price_jump' in projection or holds:
            projection['price_jump'] = holds
        event = dict(kind='BALANCE_CHECKED', check=check, checked_ms=now_ms, observation_sha256=observation_hash)
        document = self._commit(Document.from_dict(current), f'balance:{now_ms}', event, projection=projection)
        for incident in incidents:
            event = dict(kind='INCIDENT', incident=dict(incident, block_number=check['block_number'], at_ms=now_ms))
            document = self._commit(document, f"incident:{incident['type'].lower()}:{now_ms}", event)
        if adjustments:
            # The comparison was made against current. Only our BALANCE_CHECKED and INCIDENT writes may
            # intervene before adoption; a reload containing another writer's commit is not fresh confirmation.
            if document.read()['version'] != current['version'] + 1 + len(incidents):
                self.candidate = None
                self.ok_ms = None
                self.next_ms = now_ms + self.retry
                return 'SKIPPED:CONCURRENT_ACTIVITY'
            document = self._adopt(document, adjustments, check, now_ms)
            state = document.read()['projection']['balance_check']
        self._settle_gate(status, state, now_ms)
        return result

    def _adopt(self, document, adjustments, check, now_ms):
        """The chain wins: one BALANCE_ADJUSTED event, then one incident per asset (IDEA-055 D2/D4)."""
        projection = document.read()['projection']
        adopted = {a['asset'] for a in adjustments}
        portfolio = adjust_ledger(projection['portfolio'], adjustments)
        deficits = {a: u for a, u in check['deficits'].items() if a not in adopted}
        surplus = [a for a in check['surplus'] if a not in adopted]
        remaining = 'DEFICIT' if deficits else ('SURPLUS_ONLY' if surplus else 'MATCH')
        projection.update(portfolio=portfolio, balances=balances_of(portfolio))
        projection['balance_check'] = dict(projection['balance_check'], comparable_status=remaining,
                                           deficits=deficits, surplus_assets=surplus, adjusted_ms=now_ms)
        holds = projection.get('price_jump') or {}
        if any(s in adopted for s in holds):
            projection['price_jump'] = {s: h for s, h in holds.items() if s not in adopted}
        event = dict(kind='BALANCE_ADJUSTED', adjustments=adjustments, adjusted_ms=now_ms)
        document = self._commit(document, f'balance-adjusted:{now_ms}', event, projection=projection)
        for adjustment in adjustments:
            incident = dict(type='BALANCE_ADJUSTED', **{k: v for k, v in adjustment.items() if k != 'decimals'},
                            at_ms=now_ms)
            event = dict(kind='INCIDENT', incident=incident)
            document = self._commit(document, f"incident:balance_adjusted:{adjustment['asset'].lower()}:{now_ms}",
                                    event)
        return document

    def _settle_gate(self, status, state, now_ms):
        if status in self.COMPARABLE:  # a skip keeps the last good time
            self.ok_ms = now_ms if state.get('comparable_status') != 'DEFICIT' else None


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
        self.tried = set()  # quote follow-up children resumed by this process

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

    def _done(self, round_id):
        return any(self.store.receipt(self.run_id, p + round_id) for p in ('plan:', 'rejected:'))

    @staticmethod
    def child_attempts(parent, n):
        return [f'{parent}/quote{n}' + ('' if a == 1 else f'#{a}') for a in range(1, MAX_ATTEMPTS + 1)]

    def child_round(self, parent, n):
        """The next attempt ID of quote follow-up `n` of `parent`; None once one planned or the attempts are spent."""
        open_ids = {r for r, _ in self.store.open_rounds(self.run_id)}
        for round_id in self.child_attempts(parent, n):
            if self._done(round_id) or round_id in open_ids:
                return None
            if not self.store.receipt(self.run_id, 'close:' + round_id):
                return round_id
        return None

    def quote_resume(self, base):
        """(source round, n, child round) when a quote follow-up of `base`'s planned round was interrupted (PR #66 Y2).

        A follow-up child opens only after an executable quote came back, so an interrupted child is the only sign
        that the follow-up was due; a parent whose follow-up never started is not resumed. Each child is retried at
        most once per process (`tried`), and at most MAX_ATTEMPTS times in all."""
        parent = next((f'{base}#{a}' for a in range(MAX_ATTEMPTS, 0, -1)
                       if self.store.receipt(self.run_id, f'plan:{base}#{a}')), None)
        if parent is None:
            return None
        source = parent
        for n in range(1, MAX_QUOTE_CHAIN + 1):
            attempts = self.child_attempts(parent, n)
            planned = next((r for r in attempts if self._done(r)), None)
            if planned is not None:
                source = planned
                continue
            if not any(self.store.receipt(self.run_id, 'close:' + r) for r in attempts):
                return None
            child = self.child_round(parent, n)
            return None if child is None or child in self.tried else (source, n, child)
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
        base = 'review:' + job['job_id'][len('evidence:'):]
        round_id = self.round_for(base)
        return dict(round_id=round_id, job=job, issuer_id=issuer, records=records, claim=claim,
                    resume=None if round_id is not None else self.quote_resume(base))

    def _ingested(self, now_ms):
        jobs = [j for j in self.evidence.jobs() if j.get('lane') == 'evidence'
                and (j.get('payload') or {}).get('kind') == 'ASSESS_FILING'
                and j['payload'].get('issuer_id') in self.issuers
                and j['due_ms'] <= now_ms < j['valid_until_ms']]
        for job in sorted(jobs, key=lambda j: (j['priority'], j['due_ms'], j['job_id'])):
            base = 'filing:' + job['job_id'][len('evidence:'):]
            round_id = self.round_for(base)
            resume = self.quote_resume(base) if round_id is None else None
            if round_id is None and resume is None:
                continue
            p = job['payload']
            records = [r for r in self._records(p['issuer_id'], now_ms) if r['record_id'] == p['record_id']]
            if not records:
                continue  # not yet available at this cutoff
            return dict(round_id=round_id, job=job, issuer_id=p['issuer_id'], records=records, claim=None,
                        resume=resume)
        return None

    def _cadence(self, now_ms):
        slot = now_ms // self.cadence
        round_id = self.round_for(f'cadence:{slot}')
        resume = self.quote_resume(f'cadence:{slot}') if round_id is None else None
        if (round_id is None and resume is None) or not self.issuers:
            return None
        issuer = self.issuers[slot % len(self.issuers)]
        records = self._latest(issuer, now_ms)
        # IDEA-090 (S2-F2): a slot whose issuer has no records still plans, on the evidence already accepted and
        # with no new assessment, so trading and mandatory exits never wait for an issuer with a filing.
        payload = dict(kind='REASSESS_ISSUER', issuer_id=issuer,
                       reason='SCHEDULED_CADENCE' if records else 'SCHEDULED_DECISION', slot=slot)
        job = dict(job_id='evidence:' + digest('larp.runtime.cadence-job.v1', payload), lane='evidence',
                   due_ms=slot * self.cadence, valid_until_ms=(slot + 1) * self.cadence, max_attempts=1,
                   priority=60, calendar_id='UTC', tzdata_version='utc-only-no-tzdata', missed='expire',
                   payload=payload)
        item = dict(round_id=round_id, job=job, issuer_id=issuer, records=records, claim=None, resume=resume)
        if not records:
            item['planning_only'] = True
        return item

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
                 max_quote_rounds=0, max_quote_requests=2, balance_check=None, assessments=None, gas_check=None,
                 allowance_check=None):
        self.coordinator, self.work = coordinator, work
        self.assessments = assessments
        self.balance_check = balance_check
        self.gas_check = gas_check
        self.allowance_check = allowance_check
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

    @staticmethod
    def runnable(item):
        """An item with records to assess, or a planning-only cadence slot (IDEA-090)."""
        return bool(item['records']) or item.get('planning_only') is True

    def _round(self, round_id, item, now_ms):
        c = self.coordinator
        if self.market is not None:
            self.market.refresh(now_ms)  # before the round: its decision time follows the fetch (#24)
        current = c.store.load(c.run_id).read()
        c.start(round_id, self.work.request(item, current, now_ms), now_ms,
                **(dict(assessment_override=None, use_accepted_evidence=True) if item.get('planning_only') else {}))

    def _quotes(self, round_id, item, now_ms, summary, *, first=1, child=None):
        """Bounded follow-up rounds while the last plan asked for quotes and an executable one came back.

        `round_id` is the round whose plan holds the quote requests; a resumed follow-up (PR #66 Y2) starts at
        follow-up `first` with the given `child` attempt ID."""
        parent = round_id.split('/quote')[0]
        for n in range(first, self.max_quote_rounds + 1):
            plan = self._plan(round_id)
            requests = [r for r in plan.get('quote_requests', []) if r.get('symbol') != 'BNB']
            if plan.get('intents') or not requests:
                return
            executable, dropped = False, []
            for request in requests[:self.max_quote_requests]:
                reason = None
                try:
                    if self.market.quote(request):
                        executable = True
                    else:
                        reason = getattr(self.market, 'refused', None) or 'NO_EXECUTABLE_QUOTE'
                except Exception as error:  # an unavailable quote is a hold, never a failed round
                    summary.setdefault('quote_errors', []).append(type(error).__name__)
                    reason = quote_drop_reason(error)
                if reason is not None:
                    dropped.append(dict(symbol=request.get('symbol'), side=request.get('side'),
                                        pay_units=request.get('pay_units'), reason=reason))
            summary.setdefault('quotes_requested', 0)
            summary['quotes_requested'] += min(len(requests), self.max_quote_requests)
            if not executable:
                self.market.clear_quotes()
                summary['quote_incident'] = self._journal_dropped(round_id, dropped, now_ms)
                return
            source_round = round_id
            round_id = child if (n == first and child is not None) else self.work.child_round(parent, n)
            if round_id is None:
                self.market.clear_quotes()
                return
            summary['quote_round_id'] = round_id
            try:
                c = self.coordinator
                current = c.store.load(c.run_id).read()
                # The quoted observations stand in for this round's fetch; the decision clock follows them.
                c.start(round_id, self.work.request(item, current, now_ms), now_ms,
                        **(dict(execution_parent_round=source_round)
                           if getattr(c.context_builder, 'profile', {}).get('baseline') == 'TREND_GUARDED_VOL' else {}),
                        **(dict(assessment_override=None, use_accepted_evidence=True)
                           if self.assessments or item.get('planning_only') else {}))
            finally:
                self.market.clear_quotes()

    def _journal_dropped(self, round_id, dropped, now_ms):
        """IDEA-088 QV8: a quote follow-up that ends without an executable quote is journaled, never silent. The
        round's plan had no intents, so no command waits for a claim behind this commit."""
        c = self.coordinator
        current = c.store.load(c.run_id)
        run = current.read()
        incident = dict(type='QUOTE_NOT_EXECUTABLE', round_id=round_id, requests=dropped, at_ms=now_ms)
        try:
            c.store.commit(batch_for(current, f"incident:quote:{run['epoch']}:{run['version'] + 1}",
                                     dict(kind='INCIDENT', incident=incident)))
        except Conflict:
            return 'CONFLICT'
        return 'JOURNALED'

    def once(self, now_ms):
        c = self.coordinator
        summary = dict(closed=len(self.execution.settle_open(now_ms)), round_id=None)
        for key in ('ingested', 'refused', 'expired', 'sealed', 'logged'):
            if getattr(self.execution, key, None):
                summary[key] = list(getattr(self.execution, key))
        c.recover(now_ms, **(dict(skip_rounds=self.assessments.round_ids()) if self.assessments else {}))
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
        if self.balance_check is not None and self.balance_check.due(now_ms, c.store.load(c.run_id).read()['projection']):
            summary['balance_check'] = self.balance_check(now_ms)  # before the round, so it sees the result
        if self.gas_check is not None and ('balance_check' in summary or self.gas_check.due(now_ms)):
            summary['gas_check'] = self.gas_check(now_ms)  # at its interval, and after every reconciliation
        if self.allowance_check is not None:
            summary['allowance_check'] = self.allowance_check(now_ms)
        if self.day_roll is not None and self.market is not None:
            current = c.store.load(c.run_id).read()
            if self.day_roll.due(current, now_ms):
                self.market.refresh(now_ms)
                # The marks are stamped when their responses arrive: value them at a time read after the fetch, and
                # check the day and the window again at that time (PR #66 R2).
                decided = max(now_ms, c.clock())
                summary['day_roll'] = self.day_roll(decided, self.market.observations())
        current = c.store.load(c.run_id).read()
        if self.assessments is not None:
            return self._signed_cycle(now_ms, summary)
        item = self.work.next(now_ms, current['epoch'])
        if item is not None:
            summary['round_id'] = item['round_id']
            resume = item.get('resume')
            if item['round_id'] is not None and self.runnable(item):
                self._round(item['round_id'], item, now_ms)
                if self.market is not None and self.max_quote_rounds:
                    self._quotes(item['round_id'], item, now_ms, summary)
            elif resume is not None and self.runnable(item) and self.market is not None:
                source, n, child = resume
                self.work.tried.add(child)
                summary['quote_resume'] = child
                if n <= self.max_quote_rounds:
                    self.market.refresh(now_ms)
                    self._quotes(source, item, now_ms, summary, first=n, child=child)
            if item['claim'] is not None:
                # Finished only after its round committed: a crash leaves the job to be claimed again once its lease
                # ends, and the round ID makes the rerun return the recorded round.
                self.work.scheduler.finish(c.run_id, item['claim'])
            if not self.execution.waiting(now_ms):  # never ingest over a command that still awaits its claim
                summary['closed'] += len(self.execution.settle_open(now_ms))
        return summary

    def _signed_cycle(self, now_ms, summary):
        """No provider call on this thread: complete old evidence, plan safety, then queue one new job."""
        c, queue = self.coordinator, self.assessments
        ready = queue.ready()
        if ready is not None:
            if self.market is not None:
                self.market.refresh(now_ms)
            decided = max(now_ms, c.clock())
            result = Document.from_dict(ready['result']) if ready['result'] is not None else None
            c.start(ready['round_id'], Document.from_dict(ready['request']), decided,
                    assessment_override=result, assessment_audit=ready['audit'], use_accepted_evidence=True)
            queue.ack(ready['round_id'])  # only after the result and its original I/O are journaled
            if ready.get('claim') is not None:
                try:
                    self.work.scheduler.finish(c.run_id, Document.from_dict(ready['claim']))
                except Conflict:
                    summary['model_claim_expired'] = True  # the committed round still fences duplicate planning
            summary['assessment_round_id'] = ready['round_id']
            if self.execution.waiting(decided):
                return summary
        # Mandatory risk and existing accepted evidence remain usable even when there is no filing,
        # or the sole worker is hung. The worker never supplies a proposal or writes the projection.
        if self.market is not None:
            self.market.refresh(now_ms)
        decided = max(now_ms, c.clock())
        current = c.store.load(c.run_id).read()
        round_id = f"safety:{decided}:{current['version']}"
        issuer = self.work.issuers[0]
        item = dict(issuer_id=issuer, records=self.work._latest(issuer, decided), claim=None,
                    job=dict(job_id=round_id, lane='evidence', due_ms=decided,
                             valid_until_ms=decided+self.work.cadence, max_attempts=1, priority=0,
                             calendar_id='UTC', tzdata_version='utc-only-no-tzdata', missed='expire',
                             payload=dict(kind='REASSESS_ISSUER', issuer_id=issuer, reason='SAFETY_TICK')))
        c.start(round_id, self.work.request(item, current, decided), decided,
                assessment_override=None, use_accepted_evidence=True)
        summary['round_id'] = round_id
        if self.market is not None and self.max_quote_rounds and not self.execution.waiting(decided):
            self._quotes(round_id, item, decided, summary)
        if self.execution.waiting(decided):
            return summary
        summary['closed'] += len(self.execution.settle_open(decided))
        if not queue.busy:
            current = c.store.load(c.run_id).read()
            work = self.work.next(decided, current['epoch'])
            if work is not None:
                if work['round_id'] is not None and work['records']:
                    request = self.work.request(work, current, decided)
                    from larp.runtime.schema import assessment_request
                    assessment_request(request, c.run_id, c.profile_hash, decided)
                    c.store.open_round(c.run_id, work['round_id'], request, current['epoch'])
                    queue.submit(work['round_id'], request,
                                 claim=work['claim'].read() if work['claim'] is not None else None)
                    summary['assessment_queued'] = work['round_id']
                elif work['claim'] is not None:
                    self.work.scheduler.finish(c.run_id, work['claim'])
        return summary

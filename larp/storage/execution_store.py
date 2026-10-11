"""PostgreSQL store for the W04 execution machine (`larp.execution.Store`; IDEA-042 item 2, DR-04).

One store instance serves one run. Every commit, in one transaction:
- fences on the run's owner epoch (read under a share lock, so a takeover waits) and the execution guard version;
- compares and swaps the execution revision;
- writes the state and its event together;
- keeps the wallet barrier: one active (non-terminal) execution per wallet and chain, across runs.

Signed bytes belong to the signer's registry (`execution_signatures`), never to events. The execution state may hold
`raw_hex` for recovery; it is readable only by the execution role.
"""

from dataclasses import asdict, replace
import json

from larp.execution import TERMINAL, Attempt, Conflict, Execution, Intent, Payload, canonical
from larp.storage.postgres import IntegrityError


def _execution(raw):
    value = json.loads(bytes(raw))
    value['intent'] = Intent(**value['intent'])
    value['attempts'] = tuple(Attempt(**{**item, 'payload': Payload(**item['payload'])}) for item in value['attempts'])
    return Execution(**value)


class PostgresExecutionStore:
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id
        self.before_write = None  # fault-injection hook for tests; runs inside the transaction

    def ensure(self):
        with self.store.transaction() as db:
            db.execute('INSERT INTO execution_authority(run_id) VALUES(%s) ON CONFLICT DO NOTHING', (self.run_id,))

    def authority(self):
        with self.store.transaction() as db:
            return self._authority(db, lock=False)

    def _authority(self, db, *, lock):
        run = db.execute('SELECT epoch,quarantined FROM runs WHERE run_id=%s' + (' FOR SHARE' if lock else ''),
                         (self.run_id,)).fetchone()
        row = db.execute('SELECT version FROM execution_authority WHERE run_id=%s' + (' FOR UPDATE' if lock else ''),
                         (self.run_id,)).fetchone()
        if run is None or row is None:
            raise Conflict('Unknown run or execution authority not initialised')
        if run[1]:
            raise Conflict('Run is quarantined')
        return int(run[0]), int(row[0])

    def advance_guard(self):
        """A guard fact changed (HALT, version event, market state): every outstanding authorization is stale."""
        with self.store.transaction() as db:
            db.execute('UPDATE execution_authority SET version=version+1 WHERE run_id=%s', (self.run_id,))

    def check_authority(self, epoch, version):
        if self.authority() != (epoch, version):
            raise Conflict('fenced or stale state version')

    def load(self, key):
        with self.store.transaction() as db:
            row = db.execute('SELECT state FROM executions WHERE key=%s', (key,)).fetchone()
        return _execution(row[0]) if row else None

    def commit(self, previous, current, event, epoch, guard_version):
        try:
            with self.store.transaction() as db:
                if self._authority(db, lock=True) != (epoch, guard_version):
                    raise Conflict('fenced or stale state version')
                row = db.execute('SELECT revision,run_id FROM executions WHERE key=%s FOR UPDATE',
                                 (current.intent.key,)).fetchone()
                if (row is None) != (previous is None) or (row and int(row[0]) != previous.revision):
                    raise Conflict('stale execution revision')
                if row and row[1] != self.run_id or current.intent.run_id != self.run_id:
                    raise Conflict('execution belongs to another run')
                if self.before_write:
                    self.before_write()
                new = replace(current, revision=(previous.revision + 1 if previous else 1))
                state = canonical(asdict(new)).encode('utf-8')
                terminal = new.status in TERMINAL
                if row is None:
                    db.execute('INSERT INTO executions VALUES(%s,%s,%s,%s,%s,%s,%s)',
                               (new.intent.key, self.run_id, new.intent.wallet, new.intent.chain_id, terminal,
                                new.revision, state))
                else:
                    db.execute('UPDATE executions SET terminal=%s,revision=%s,state=%s WHERE key=%s',
                               (terminal, new.revision, state, new.intent.key))
                db.execute('INSERT INTO execution_events(key,revision,event) VALUES(%s,%s,%s)',
                           (new.intent.key, new.revision, canonical({**event, 'revision': new.revision}).encode('utf-8')))
                return new
        except IntegrityError as error:
            raise Conflict('wallet-wide active intent barrier') from error

    def events(self):
        with self.store.transaction() as db:
            return [json.loads(bytes(r[0])) for r in db.execute(
                'SELECT e.event FROM execution_events e JOIN executions x USING(key) WHERE x.run_id=%s '
                'ORDER BY e.sequence', (self.run_id,))]

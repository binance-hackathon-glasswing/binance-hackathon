"""W04 CAS/registry adapter using W02 PostgreSQL transactions and run fencing.

Schema is a proposed owner-local extension for Keegan to adopt in migrations.
It is explicitly installed in disposable tests, never installed by live startup.
Restricted state/signature tables must be accessible only to execution/signer roles.
Public events contain no signed bytes. Production release/round integration is separate.
"""
from dataclasses import asdict, replace
import json

from larp.execution import (Attempt, Conflict, Execution, Intent, Payload, Signed,
                            TERMINAL, canonical, digest)
from larp.storage.postgres import IntegrityError
from larp.contracts import Document

SCHEMA = '''
CREATE TABLE IF NOT EXISTS execution_records (
    economic_key text PRIMARY KEY, run_id text NOT NULL REFERENCES runs,
    wallet text NOT NULL, chain_id bigint NOT NULL, terminal boolean NOT NULL,
    revision bigint NOT NULL, state bytea NOT NULL, state_hash text NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS execution_wallet_barrier
    ON execution_records(wallet,chain_id) WHERE NOT terminal;
CREATE TABLE IF NOT EXISTS execution_journal (
    economic_key text REFERENCES execution_records, revision bigint NOT NULL,
    event bytea NOT NULL, state_hash text NOT NULL, previous_hash text NOT NULL, head text NOT NULL,
    PRIMARY KEY(economic_key,revision)
);
CREATE TABLE IF NOT EXISTS execution_signatures (
    attempt_id text PRIMARY KEY, run_id text NOT NULL REFERENCES runs,
    payload_hash text NOT NULL, signed bytea NOT NULL, signed_hash text NOT NULL
);
CREATE TABLE IF NOT EXISTS execution_observations (
    event_id text PRIMARY KEY, run_id text NOT NULL REFERENCES runs,
    observation bytea NOT NULL, observation_hash text NOT NULL
);
'''


def _decode(raw):
    try:
        value = json.loads(bytes(raw))
        value['intent'] = Intent(**value['intent'])
        value['attempts'] = tuple(Attempt(**{**a, 'payload': Payload(**a['payload'])}) for a in value['attempts'])
        return Execution(**value)
    except (ValueError, TypeError, KeyError):
        raise Conflict('execution record schema/integrity rejected') from None


class ExecutionStore:
    revokes_unbroadcast = True
    def __init__(self, store, *, run_id, wallet):
        self.store, self.run_id, self.wallet = store, run_id, wallet

    def install_test_schema(self):
        with self.store.transaction() as db:
            run = self.store._run(db, self.run_id)
            if run['mode'] != 'offline':
                raise Conflict('automatic schema installation is offline-test only')
            db.execute(SCHEMA)

    def _authority(self, db, epoch, version):
        run = self.store._run(db, self.run_id)
        self.store._owned(run, epoch)
        if run['version'] != version or run['chain_id'] != 56:
            raise Conflict('execution authority changed')
        return run

    def authority(self):
        run = self.store.load(self.run_id).read()
        return run['epoch'], run['version']

    def check_authority(self, epoch, version):
        with self.store.transaction() as db:
            self._release_authority(db, epoch, version)

    def _release_authority(self, db, epoch, version):
        run = self.store._run(db, self.run_id)
        self.store._owned(run, epoch)
        if version != epoch or run['chain_id'] != 56:
            raise Conflict('execution release authority changed')
        return run

    def execution_authority(self):
        run = self.store.load(self.run_id).read()
        return run['epoch'], run['epoch']

    def _attempt(self, db, attempt_id):
        keys = db.execute('SELECT economic_key FROM execution_records WHERE run_id=%s', (self.run_id,)).fetchall()
        for key, in keys:
            state = self._load(db, key)
            for attempt in state.attempts:
                if attempt.attempt_id == attempt_id:
                    return state, attempt
        raise Conflict('unknown registered execution attempt')

    def attempt(self, attempt_id):
        """(execution, attempt) for a registered attempt, journal verified; Conflict if unknown."""
        with self.store.transaction() as db:
            return self._attempt(db, attempt_id)

    def check_broadcast(self, signed, epoch, version):
        with self.store.transaction() as db:
            self._release_authority(db, epoch, version)
            keys = db.execute('SELECT economic_key FROM execution_records WHERE run_id=%s', (self.run_id,)).fetchall()
            for key, in keys:
                state = self._load(db, key)
                for attempt in state.attempts:
                    if (state.status == 'ACTIVE' and attempt.state == 'BROADCAST_ATTEMPTED'
                            and attempt.broadcast_at is not None and attempt.tx_hash == signed.tx_hash
                            and attempt.raw_hex == signed.raw_hex and attempt.epoch == epoch
                            and attempt.guard_version == version):
                        return
            raise Conflict('signed bytes have no current possible-send authority')

    def _load(self, db, key):
        row = db.execute('SELECT state,state_hash,revision,run_id,wallet FROM execution_records '
                         'WHERE economic_key=%s FOR UPDATE', (key,)).fetchone()
        if row is None:
            return None
        value = _decode(row[0])
        if (digest(asdict(value)) != row[1] or value.revision != row[2]
                or value.intent.key != key or row[3] != self.run_id or row[4] != self.wallet):
            raise Conflict('execution state integrity or namespace mismatch')
        rows = db.execute('SELECT revision,event,state_hash,previous_hash,head FROM execution_journal '
                          'WHERE economic_key=%s ORDER BY revision', (key,)).fetchall()
        previous = '0' * 64
        for sequence, record in enumerate(rows, 1):
            revision, event, state_hash, prior, head = record
            expected = digest([prior, json.loads(bytes(event)), state_hash])
            if revision != sequence or prior != previous or expected != head:
                raise Conflict('execution journal integrity failure')
            previous = head
        if len(rows) != value.revision or not rows or rows[-1][2] != row[1]:
            raise Conflict('execution journal/state mismatch')
        return value

    def load(self, key):
        with self.store.transaction() as db:
            return self._load(db, key)

    def commit(self, previous, current, event, epoch, guard_version):
        if current.intent.run_id != self.run_id or current.intent.wallet != self.wallet:
            raise Conflict('execution run/wallet mismatch')
        current.intent.validate()
        try:
            with self.store.transaction() as db:
                self._authority(db, epoch, guard_version)
                stored = self._load(db, current.intent.key)
                if (stored is None) != (previous is None) or (stored is not None and stored != previous):
                    raise Conflict('stale execution CAS')
                if stored is not None and stored.intent != current.intent:
                    raise Conflict('immutable economic intent changed')
                if event.get('type') == 'ABORTED_UNBROADCAST':
                    if (stored is None or stored.status != 'ACTIVE' or not stored.attempts
                            or stored.attempts[-1].broadcast_at is not None
                            or current.status != 'ABORTED' or current.attempts[-1].state != 'ABORTED'):
                        raise Conflict('no-positive-unbroadcast evidence for revocation')
                new = replace(current, revision=1 if previous is None else previous.revision + 1)
                raw, checksum = canonical(asdict(new)).encode(), digest(asdict(new))
                if stored is None:
                    db.execute('INSERT INTO execution_records VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                               (new.intent.key, self.run_id, self.wallet, 56, new.status in TERMINAL,
                                new.revision, raw, checksum))
                    prior = '0' * 64
                else:
                    db.execute('UPDATE execution_records SET terminal=%s,revision=%s,state=%s,state_hash=%s '
                               'WHERE economic_key=%s', (new.status in TERMINAL, new.revision, raw,
                                                         checksum, new.intent.key))
                    prior = db.execute('SELECT head FROM execution_journal WHERE economic_key=%s '
                                       'AND revision=%s', (new.intent.key, stored.revision)).fetchone()[0]
                public = {**event, 'revision': new.revision}
                if 'raw_hex' in canonical(public) or 'signedTransaction' in canonical(public):
                    raise Conflict('signed bytes cannot enter public execution journal')
                head = digest([prior, public, checksum])
                db.execute('INSERT INTO execution_journal VALUES(%s,%s,%s,%s,%s,%s)',
                           (new.intent.key, new.revision, canonical(public).encode(), checksum, prior, head))
                return new
        except IntegrityError:
            raise Conflict('wallet barrier or execution uniqueness conflict') from None

    def lookup(self, attempt_id, payload_hash):
        with self.store.transaction() as db:
            row = db.execute('SELECT payload_hash,signed,signed_hash,run_id FROM execution_signatures '
                             'WHERE attempt_id=%s', (attempt_id,)).fetchone()
            if row is None:
                return None
            state, attempt = self._attempt(db, attempt_id)
            if state.status == 'ABORTED' or attempt.state == 'ABORTED':
                raise Conflict('attempt signing authority revoked')
            value = json.loads(bytes(row[1]))
            if row[0] != payload_hash or row[2] != digest(value) or row[3] != self.run_id:
                raise Conflict('immutable signer registry mismatch')
            return Signed(**value)

    def put_if_absent(self, attempt_id, payload_hash, signed, epoch, version):
        with self.store.transaction() as db:
            run = self._release_authority(db, epoch, version)
            state, attempt = self._attempt(db, attempt_id)
            self.check_signing_run(run, state.intent)
            if (state.status != 'ACTIVE' or attempt.state != 'AUTHORIZED'
                    or attempt.payload.hash != payload_hash or attempt.epoch != epoch
                    or attempt.guard_version != version):
                raise Conflict('attempt has no current signing authority')
            value = asdict(signed)
            db.execute('INSERT INTO execution_signatures VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                       (attempt_id, self.run_id, payload_hash, canonical(value).encode(), digest(value)))
            row = db.execute('SELECT payload_hash,signed,signed_hash,run_id FROM execution_signatures '
                             'WHERE attempt_id=%s', (attempt_id,)).fetchone()
            stored = json.loads(bytes(row[1]))
            if row[0] != payload_hash or row[2] != digest(stored) or row[3] != self.run_id:
                raise Conflict('immutable attempt signature conflicts')
            return Signed(**stored)

    @staticmethod
    def check_signing_run(run, intent, build_id=None):
        """Independent signing facts from the locked run, writable only by runtime.

        This check is specific to new signatures. Receipt publication and lookup
        keep using release authority so HALT never prevents reconciliation.
        """
        projection = Document(bytes(run['projection'])).read()
        if (projection.get('halt') or {}).get('reasons'):
            raise Conflict('run is halted; signing blocked')
        registered = projection.get('registered_version')
        if registered is not None and type(registered) is not dict:
            raise Conflict('invalid registered signing version')
        version = (registered or {}).get('build_id')
        if run['mode'] != 'offline' or registered is not None:
            if not version or version != intent.version_id:
                raise Conflict('intent differs from registered signing version')
        if build_id is not None and (version != build_id or intent.version_id != build_id):
            raise Conflict('signer build differs from registered signing version')
        if run['mode'] != 'offline' and str(run['wallet_id']).lower() != intent.wallet:
            raise Conflict('registered signing wallet mismatch')

    def lookup_observation(self, event_id):
        with self.store.transaction() as db:
            row = db.execute('SELECT observation,observation_hash,run_id FROM execution_observations '
                             'WHERE event_id=%s', (event_id,)).fetchone()
            if row is None:
                return None
            value = json.loads(bytes(row[0]))
            if digest(value) != row[1] or row[2] != self.run_id or value['event_id'] != event_id:
                raise Conflict('immutable execution observation corrupted')
            return value

    def put_observation(self, observation, epoch, version):
        if observation.get('run_id') != self.run_id:
            raise Conflict('observation run mismatch')
        with self.store.transaction() as db:
            self._release_authority(db, epoch, version)
            checksum = digest(observation)
            db.execute('INSERT INTO execution_observations VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                       (observation['event_id'], self.run_id, canonical(observation).encode(), checksum))
            row = db.execute('SELECT observation_hash,run_id FROM execution_observations WHERE event_id=%s',
                             (observation['event_id'],)).fetchone()
            if row != (checksum, self.run_id):
                raise Conflict('immutable execution observation changed')
        return observation

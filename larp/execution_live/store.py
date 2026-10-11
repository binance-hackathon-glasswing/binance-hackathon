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
'''


def _decode(raw):
    value = json.loads(bytes(raw))
    value['intent'] = Intent(**value['intent'])
    value['attempts'] = tuple(Attempt(**{**a, 'payload': Payload(**a['payload'])}) for a in value['attempts'])
    return Execution(**value)


class ExecutionStore:
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
            self._authority(db, epoch, version)

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
            value = json.loads(bytes(row[1]))
            if row[0] != payload_hash or row[2] != digest(value) or row[3] != self.run_id:
                raise Conflict('immutable signer registry mismatch')
            return Signed(**value)

    def put_if_absent(self, attempt_id, payload_hash, signed, epoch, version):
        with self.store.transaction() as db:
            self._authority(db, epoch, version)
            value = asdict(signed)
            db.execute('INSERT INTO execution_signatures VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                       (attempt_id, self.run_id, payload_hash, canonical(value).encode(), digest(value)))
            row = db.execute('SELECT payload_hash,signed,signed_hash,run_id FROM execution_signatures '
                             'WHERE attempt_id=%s', (attempt_id,)).fetchone()
            stored = json.loads(bytes(row[1]))
            if row[0] != payload_hash or row[2] != digest(stored) or row[3] != self.run_id:
                raise Conflict('immutable attempt signature conflicts')
            return Signed(**stored)

"""Offline W04 adapters. SQLite is a fixture, not the W02 production store."""
from dataclasses import asdict, replace
import json
import sqlite3

from larp.execution import (Attempt, Blocked, Conflict, Execution, Gates, Intent,
                            Outcome, Payload, Signed, SwapEconomics, canonical, digest)

WALLET = "0x" + "1" * 40
ROUTER = "0x" + "2" * 40
TOKEN = "0x02fca66c1d1afb4e2a7884261eb00f63598a7436"
BLOCK = "0x" + "3" * 64


def intent(**changes):
    from larp.execution import USDT
    return replace(Intent("run", "round", "decision", "economic-1", "version",
                          "reservation-1", WALLET, USDT, TOKEN, 100, 90, ROUTER,
                          1000, 200000, 10, 1000000), **changes)


class SQLiteFixture:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS authority (id INTEGER PRIMARY KEY, epoch INTEGER, version INTEGER);
            INSERT OR IGNORE INTO authority VALUES (1, 1, 1);
            CREATE TABLE IF NOT EXISTS executions (
                key TEXT PRIMARY KEY, wallet TEXT, chain INTEGER, terminal INTEGER,
                revision INTEGER, state TEXT);
            CREATE UNIQUE INDEX IF NOT EXISTS wallet_barrier ON executions(wallet, chain) WHERE terminal=0;
            CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY, event TEXT);
            CREATE TABLE IF NOT EXISTS signatures (attempt TEXT PRIMARY KEY, payload TEXT, signed TEXT);
        ''')
        self.fail_next = False

    def close(self):
        self.db.close()

    def authority(self):
        return self.db.execute("SELECT epoch,version FROM authority WHERE id=1").fetchone()

    def advance_authority(self, epoch=False):
        self.db.execute("UPDATE authority SET version=version+1,epoch=epoch+? WHERE id=1", (int(epoch),))

    def check_authority(self, epoch, version):
        if self.authority() != (epoch, version):
            raise Conflict("fenced or stale state version")

    def load(self, key):
        row = self.db.execute("SELECT state FROM executions WHERE key=?", (key,)).fetchone()
        if not row:
            return None
        value = json.loads(row[0])
        value["intent"] = Intent(**value["intent"])
        value["attempts"] = tuple(Attempt(**{**item, "payload": Payload(**item["payload"])}) for item in value["attempts"])
        return Execution(**value)

    def commit(self, previous, current, event, epoch, guard_version):
        from larp.execution import TERMINAL
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.check_authority(epoch, guard_version)
            stored = self.load(current.intent.key)
            if (stored is None) != (previous is None) or (stored and stored.revision != previous.revision):
                raise Conflict("stale execution revision")
            if self.fail_next:
                self.fail_next = False
                raise OSError("injected storage fault")
            new = replace(current, revision=(previous.revision + 1 if previous else 1))
            if stored is None:
                self.db.execute("INSERT INTO executions VALUES (?,?,?,?,?,?)",
                                (new.intent.key, new.intent.wallet, new.intent.chain_id,
                                 int(new.status in TERMINAL), new.revision, canonical(asdict(new))))
            else:
                self.db.execute("UPDATE executions SET terminal=?,revision=?,state=? WHERE key=?",
                                (int(new.status in TERMINAL), new.revision, canonical(asdict(new)), new.intent.key))
            self.db.execute("INSERT INTO events(event) VALUES (?)", (canonical({**event, "revision": new.revision}),))
            self.db.execute("COMMIT")
            return new
        except Exception as error:
            self.db.execute("ROLLBACK")
            if isinstance(error, sqlite3.IntegrityError):
                raise Conflict("wallet-wide active intent barrier") from error
            raise

    def events(self):
        return [json.loads(row[0]) for row in self.db.execute("SELECT event FROM events ORDER BY sequence")]


class FakeGuards:
    mode = "fake"

    def __init__(self, store):
        self.store = store
        self.nonce = 0
        self.changes = {}

    def snapshot(self, economic_intent, now):
        epoch, version = self.store.authority()
        return Gates(epoch, version, self.nonce, now, now + 30, **self.changes)

    def change(self, **changes):
        self.changes.update(changes)
        self.store.advance_authority()


class FakeDecoder:
    mode = "fake"

    def decode(self, payload):
        if not payload.data.startswith("0xfafafafa"):
            raise Blocked("unknown fake selector")
        try:
            value = json.loads(bytes.fromhex(payload.data[10:]))
            return SwapEconomics(**value)
        except (ValueError, TypeError):
            raise Blocked("malformed fake route") from None


class FakeSigner:
    mode = "fake"

    def __init__(self, store):
        self.store = store
        self.calls = 0

    @staticmethod
    def expected(payload):
        # Deliberately NOT an EVM signature/RLP. It cannot authorize a real tx.
        raw = ("W04-FAKE-UNBROADCASTABLE:" + canonical(asdict(payload))).encode().hex()
        return Signed(raw, "0x" + digest(["FAKE", raw]))

    def sign(self, attempt_id, payload, epoch, guard_version):
        self.store.check_authority(epoch, guard_version)
        row = self.store.db.execute("SELECT payload,signed FROM signatures WHERE attempt=?", (attempt_id,)).fetchone()
        if row:
            if row[0] != payload.hash:
                raise Conflict("attempt ID reused with different signing bytes")
            return Signed(**json.loads(row[1]))
        signed = self.expected(payload)
        self.store.db.execute("INSERT INTO signatures VALUES (?,?,?)", (attempt_id, payload.hash, canonical(asdict(signed))))
        self.calls += 1
        return signed

    def verify(self, payload, signed):
        return signed == self.expected(payload)

    def lookup(self, attempt_id, payload_hash):
        row = self.store.db.execute("SELECT payload,signed FROM signatures WHERE attempt=?", (attempt_id,)).fetchone()
        if row:
            if row[0] != payload_hash:
                raise Conflict("durable signer registry payload mismatch")
            return Signed(**json.loads(row[1]))
        return None


class FakeVenue:
    mode = "fake"

    def __init__(self, store):
        self.store = store
        self.quote_calls = 0
        self.broadcasts = []
        self.outcomes = {}
        self.estimate = 100000
        self.broadcast_fault = None
        self.quote_mutation = None

    def quote(self, economic_intent, nonce):
        self.quote_calls += 1
        economics = SwapEconomics(economic_intent.pay_token, economic_intent.receive_token,
                                 economic_intent.amount, economic_intent.wallet,
                                 economic_intent.minimum_output, economic_intent.valid_until, 0)
        payload = Payload(56, economic_intent.wallet, economic_intent.router, 0, nonce,
                          100000, 1, "0xfafafafa" + canonical(asdict(economics)).encode().hex())
        return self.quote_mutation(payload) if self.quote_mutation else payload

    def approve(self, economic_intent, nonce):
        return Payload(56, economic_intent.wallet, economic_intent.pay_token, 0, nonce, 100000, 1,
                       "0x095ea7b3" + "0" * 24 + economic_intent.router[2:] + format(economic_intent.amount, "064x"))

    def estimate_gas(self, payload):
        return self.estimate

    def broadcast(self, signed, epoch, guard_version):
        self.store.check_authority(epoch, guard_version)
        self.broadcasts.append(signed.tx_hash)
        if self.broadcast_fault:
            raise self.broadcast_fault
        return signed.tx_hash

    def outcome(self, tx_hash):
        return self.outcomes.get(tx_hash, Outcome(tx_hash, WALLET, 0, "UNKNOWN"))


def finalized(attempt, status="SUCCESS", **changes):
    return replace(Outcome(attempt.tx_hash, WALLET, attempt.payload.nonce, status,
                           BLOCK, BLOCK, 10, 12, True, 50000), **changes)

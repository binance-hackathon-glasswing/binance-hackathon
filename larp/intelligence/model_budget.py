"""Durable conservative OpenAI admission; shared across runs/wallets on one primary host.

Explicit initialization is required: runtime never silently recreates a missing ledger. Each
reservation is charged before dispatch. Missing/failed/abandoned usage keeps its full bound.
This is an allocated runtime budget, not a claim to know unrelated account/console spending.
"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import uuid

from larp.intelligence.common import IntelligenceError


class ModelBudget:
    def __init__(self, path, account, *, total=50_000_000, reserve=10_000_000):
        self.path = Path(path).resolve()
        self.account, self.total, self.reserve = account, total, reserve
        if type(account) is not str or not account or len(account) > 100 or \
                type(total) is not int or type(reserve) is not int or not 0 <= reserve < total:
            raise IntelligenceError('Invalid model budget settings')
        if not self.path.is_file() or self.path.stat().st_mode & 0o077:
            raise IntelligenceError('Model budget must already exist with private permissions')
        self.snapshot()  # schema/account/limits must match the provisioned ledger

    @classmethod
    def initialize(cls, path, account, *, initial_spent, total=50_000_000, reserve=10_000_000):
        if type(initial_spent) is not int or not 0 <= initial_spent <= total:
            raise IntelligenceError('Explicit nonnegative prior OpenAI spend required')
        path = Path(path).absolute()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        with sqlite3.connect(path) as db:
            db.executescript('''PRAGMA synchronous=FULL;
                CREATE TABLE account (id INTEGER PRIMARY KEY CHECK(id=1), name TEXT NOT NULL,
                  total INTEGER NOT NULL, reserve INTEGER NOT NULL, external_only INTEGER NOT NULL,
                  reason TEXT NOT NULL);
                CREATE TABLE charges (id TEXT PRIMARY KEY, amount INTEGER NOT NULL CHECK(amount>=0),
                  state TEXT NOT NULL, request_id TEXT NOT NULL);
                CREATE TABLE switches (id INTEGER PRIMARY KEY, reason TEXT NOT NULL);''')
            db.execute('INSERT INTO account VALUES(1,?,?,?,?,?)', (account, total, reserve, 0, ''))
            db.execute('INSERT INTO charges VALUES(?,?,?,?)', ('initial', initial_spent, 'SETTLED', 'prior-usage'))
        return cls(path, account, total=total, reserve=reserve)

    @contextmanager
    def transaction(self):
        try:
            # mode=rw refuses recreation after deletion. Each worker opens its own connection.
            db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=1)
            try:
                db.execute('PRAGMA synchronous=FULL')
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT name,total,reserve FROM account WHERE id=1').fetchone()
                if row != (self.account, self.total, self.reserve):
                    raise IntelligenceError('Model budget account/limits mismatch')
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()
        except sqlite3.Error:
            raise IntelligenceError('Model budget storage unavailable or malformed') from None

    def _snapshot(self, db):
        only, reason = db.execute('SELECT external_only,reason FROM account WHERE id=1').fetchone()
        spent = db.execute('SELECT COALESCE(SUM(amount),0) FROM charges').fetchone()[0]
        return dict(account=self.account, total_micro_usd=self.total, reserve_micro_usd=self.reserve,
                    charged_micro_usd=spent, available_micro_usd=max(0, self.total-self.reserve-spent),
                    external_only=bool(only), reason=reason)

    def snapshot(self):
        with self.transaction() as db:
            return self._snapshot(db)

    @staticmethod
    def _switch(db, reason):
        db.execute('UPDATE account SET external_only=1,reason=? WHERE id=1 AND external_only=0', (reason,))
        db.execute('INSERT INTO switches(reason) VALUES(?)', (reason,))

    def external_only(self, reason):
        with self.transaction() as db:
            self._switch(db, reason)

    def admit(self, amount, request_id):
        if type(amount) is not int or amount <= 0:
            raise IntelligenceError('Positive bounded model reservation required')
        with self.transaction() as db:
            s = self._snapshot(db)
            if s['external_only']:
                return None
            if amount > s['available_micro_usd']:
                self._switch(db, 'OPENAI_OPERATING_LIMIT')
                return None
            token = uuid.uuid4().hex
            db.execute('INSERT INTO charges VALUES(?,?,?,?)', (token, amount, 'RESERVED', request_id))
            return token

    def settle(self, token, actual):
        with self.transaction() as db:
            row = db.execute('SELECT amount,state FROM charges WHERE id=?', (token,)).fetchone()
            if row is None or row[1] != 'RESERVED':
                raise IntelligenceError('Unknown or already settled model reservation')
            if actual is None:
                db.execute("UPDATE charges SET state='UNKNOWN' WHERE id=?", (token,))
                return  # conservative full reservation remains consumed
            if type(actual) is not int or actual < 0:
                raise IntelligenceError('Invalid model usage charge')
            db.execute("UPDATE charges SET amount=?,state='SETTLED' WHERE id=?", (actual, token))
            if actual > row[0]:
                self._switch(db, 'OPENAI_USAGE_EXCEEDED_BOUND')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'status'))
    parser.add_argument('--path', required=True)
    parser.add_argument('--account', required=True)
    parser.add_argument('--initial-spent-micro-usd', type=int)
    args = parser.parse_args(argv)
    if args.command == 'init':
        budget = ModelBudget.initialize(args.path, args.account, initial_spent=args.initial_spent_micro_usd)
    else:
        budget = ModelBudget(args.path, args.account)
    print(json.dumps(budget.snapshot(), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

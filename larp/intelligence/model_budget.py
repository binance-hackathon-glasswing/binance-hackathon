"""Durable conservative OpenAI admission; shared across runs/wallets on one primary host.

Explicit initialization is required: runtime never silently recreates a missing ledger. Each
reservation is charged before dispatch. Missing/failed/abandoned usage keeps its full bound.
This is an allocated runtime budget, not a claim to know unrelated account/console spending.
"""
import argparse
import hashlib
from contextlib import closing, contextmanager
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

from larp.intelligence.common import IntelligenceError


def validate_pacing(policy):
    fields = {'schema', 'total_micro_usd', 'prior_spent_micro_usd', 'start_ms', 'end_ms', 'period_ms'}
    if (type(policy) is not dict or set(policy) != fields or policy['schema'] != 'OpenAIPacing.v1'
            or any(type(policy[k]) is not int for k in fields - {'schema'})
            or not 0 <= policy['prior_spent_micro_usd'] < policy['total_micro_usd'] < 2**63
            or not 0 <= policy['start_ms'] < policy['end_ms'] < 2**63
            or not 0 < policy['period_ms'] <= policy['end_ms'] - policy['start_ms']):
        raise IntelligenceError('Invalid frozen OpenAI pacing policy')


def _policy_bytes(policy):
    return json.dumps(policy, sort_keys=True, separators=(',', ':'))


def _bound_pacing(pacing, trial):
    if trial is None:
        return _policy_bytes(pacing)
    return _policy_bytes(dict(pacing, trial_policy_sha256=hashlib.sha256(_policy_bytes(trial).encode()).hexdigest()))


DAY_MS = 86_400_000


def validate_trial(policy):
    fields = {'schema', 'trial_id', 'start_ms', 'end_ms', 'total_micro_usd', 'utc_day_micro_usd'}
    if (type(policy) is not dict or set(policy) != fields or policy['schema'] != 'OpenAITrial.v1'
            or type(policy['trial_id']) is not str or not policy['trial_id'].strip() or len(policy['trial_id']) > 100
            or any(type(policy[k]) is not int for k in fields - {'schema', 'trial_id'})
            or not 0 <= policy['start_ms'] < policy['end_ms'] < 2**63
            or not 0 < policy['utc_day_micro_usd'] < 2**63
            or not 0 < policy['total_micro_usd'] < 2**63):
        raise IntelligenceError('Invalid frozen OpenAI trial policy')


class AdmissionDeferred(IntelligenceError):
    """A temporary refusal: preserve future eligibility and disclose its audit reason."""
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _private_parent(path):
    # The runbook requires a private ledger directory: owned by this user, no group/other bits.
    try:
        st = path.parent.stat()
    except OSError:
        raise IntelligenceError('Model budget directory missing') from None
    if st.st_uid != os.geteuid() or st.st_mode & 0o077:
        raise IntelligenceError('Model budget directory must be private and owned by the runtime user')


class ModelBudget:
    def __init__(self, path, account, *, total=50_000_000, reserve=10_000_000,
                 pacing=None, trial=None, clock_ms=None):
        self.path = Path(path).resolve()
        self.account, self.total, self.reserve = account, total, reserve
        if pacing is not None:
            validate_pacing(pacing)
        self.pacing = json.loads(_policy_bytes(pacing)) if pacing is not None else None
        if trial is not None:
            validate_trial(trial)
            if (pacing is None or trial['total_micro_usd'] > total or trial['utc_day_micro_usd'] > total
                    or not pacing['start_ms'] <= trial['start_ms'] < trial['end_ms'] <= pacing['end_ms']):
                raise IntelligenceError('Trial requires matching paced allocation/window')
        self.trial = json.loads(_policy_bytes(trial)) if trial is not None else None
        self.clock = clock_ms if clock_ms is not None else lambda: time.time_ns() // 1_000_000
        if self.pacing is not None:
            if total != self.pacing['total_micro_usd'] or reserve != 0:
                raise IntelligenceError('Pacing requires matching total and no permanent reserve')
        if type(account) is not str or not account or len(account) > 100 or \
                type(total) is not int or type(reserve) is not int or not 0 <= reserve < total:
            raise IntelligenceError('Invalid model budget settings')
        _private_parent(self.path)
        if not self.path.is_file() or self.path.stat().st_mode & 0o077:
            raise IntelligenceError('Model budget must already exist with private permissions')
        self.snapshot()  # schema/account/limits must match the provisioned ledger

    @classmethod
    def initialize(cls, path, account, *, initial_spent, total=50_000_000, reserve=10_000_000,
                   pacing=None, trial=None, clock_ms=None):
        if trial is not None:
            validate_trial(trial)
            if (pacing is None or trial['total_micro_usd'] > total or trial['utc_day_micro_usd'] > total
                    or not pacing['start_ms'] <= trial['start_ms'] < trial['end_ms'] <= pacing['end_ms']):
                raise IntelligenceError('Trial requires matching paced allocation/window')
        if pacing is not None:
            validate_pacing(pacing)
            if initial_spent != pacing['prior_spent_micro_usd'] or total != pacing['total_micro_usd'] or reserve != 0:
                raise IntelligenceError('Pacing initialization must match reviewed prior spend/limits')
        if type(initial_spent) is not int or not 0 <= initial_spent <= total:
            raise IntelligenceError('Explicit nonnegative prior OpenAI spend required')
        path = Path(path).absolute()
        _private_parent(path)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(path)) as db, db:
            db.executescript('''PRAGMA synchronous=FULL;
                CREATE TABLE account (id INTEGER PRIMARY KEY CHECK(id=1), name TEXT NOT NULL,
                  total INTEGER NOT NULL, reserve INTEGER NOT NULL, external_only INTEGER NOT NULL,
                  reason TEXT NOT NULL);
                CREATE TABLE charges (id TEXT PRIMARY KEY, amount INTEGER NOT NULL CHECK(amount>=0),
                  state TEXT NOT NULL, request_id TEXT NOT NULL);
                CREATE TABLE switches (id INTEGER PRIMARY KEY, reason TEXT NOT NULL);''')
            db.execute('INSERT INTO account VALUES(1,?,?,?,?,?)', (account, total, reserve, 0, ''))
            db.execute('INSERT INTO charges VALUES(?,?,?,?)', ('initial', initial_spent, 'SETTLED', 'prior-usage'))
            if pacing is not None:
                cls._create_pacing(db, pacing)
            if trial is not None:
                cls._create_trial(db, trial)
        return cls(path, account, total=total, reserve=reserve, pacing=pacing, trial=trial, clock_ms=clock_ms)

    @staticmethod
    def _create_trial(db, policy):
        pacing = json.loads(db.execute('SELECT policy FROM pacing WHERE id=1').fetchone()[0])
        # The pre-cap release compares this entire string on every transaction.
        # Bind the trial here so old in-memory workers also fail closed after migration.
        db.execute('UPDATE pacing SET policy=? WHERE id=1', (_bound_pacing(pacing, policy),))
        db.execute('CREATE TABLE trial (id INTEGER PRIMARY KEY CHECK(id=1), policy TEXT NOT NULL, '
                   'last_ms INTEGER NOT NULL, stopped INTEGER NOT NULL, reason TEXT NOT NULL)')
        db.execute('INSERT INTO trial VALUES(1,?,-1,0,\'\')', (_policy_bytes(policy),))
        db.execute('CREATE TABLE trial_charges (charge_id TEXT PRIMARY KEY, utc_day INTEGER NOT NULL, '
                   'admitted_ms INTEGER NOT NULL, dispatched_ms INTEGER)')

    @classmethod
    def enable_trial(cls, path, account, *, trial, pacing, total=50_000_000, reserve=0, clock_ms=None):
        """Attach a first trial only to an unused paced ledger; never guess old dispatch days."""
        validate_trial(trial)
        if (trial['total_micro_usd'] > total or trial['utc_day_micro_usd'] > total or
                not pacing['start_ms'] <= trial['start_ms'] < trial['end_ms'] <= pacing['end_ms']):
            raise IntelligenceError('Trial window must fit pacing window')
        old = cls(path, account, pacing=pacing, total=total, reserve=reserve, clock_ms=clock_ms)
        with old.transaction() as db:
            if db.execute("SELECT 1 FROM charges WHERE id != 'initial' LIMIT 1").fetchone():
                raise IntelligenceError('Prior request attribution requires reconciliation before trial migration')
            cls._create_trial(db, trial)
        return cls(path, account, trial=trial, pacing=pacing, total=total, reserve=reserve, clock_ms=clock_ms)

    @staticmethod
    def _create_pacing(db, policy):
        db.execute('CREATE TABLE pacing (id INTEGER PRIMARY KEY CHECK(id=1), policy TEXT NOT NULL, '
                   'last_ms INTEGER NOT NULL)')
        db.execute('INSERT INTO pacing VALUES(1,?,-1)', (_policy_bytes(policy),))

    @classmethod
    def enable_pacing(cls, path, account, *, pacing, total=50_000_000, reserve=10_000_000,
                      trial=None, clock_ms=None):
        """Explicit development migration. Never clear charges, unknowns or a safety latch."""
        validate_pacing(pacing)
        if total != pacing['total_micro_usd']:
            raise IntelligenceError('Pacing migration total mismatch')
        if trial is not None:
            validate_trial(trial)
            if (trial['total_micro_usd'] > total or trial['utc_day_micro_usd'] > total or
                    not pacing['start_ms'] <= trial['start_ms'] < trial['end_ms'] <= pacing['end_ms']):
                raise IntelligenceError('Trial window must fit paced allocation')
        old = cls(path, account, total=total, reserve=reserve)
        with old.transaction() as db:
            initial = db.execute("SELECT amount,state FROM charges WHERE id='initial'").fetchone()
            if initial != (pacing['prior_spent_micro_usd'], 'SETTLED'):
                raise IntelligenceError('Pacing migration prior spend mismatch; reconciliation required')
            if trial is not None and db.execute("SELECT 1 FROM charges WHERE id!='initial' LIMIT 1").fetchone():
                raise IntelligenceError('Prior request attribution requires reconciliation before trial migration')
            cls._create_pacing(db, pacing)
            db.execute('UPDATE account SET reserve=0 WHERE id=1')
            if trial is not None:
                cls._create_trial(db, trial)
        return cls(path, account, total=total, reserve=0, pacing=pacing, trial=trial, clock_ms=clock_ms)

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
                has_pacing = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pacing'").fetchone()
                if bool(has_pacing) != (self.pacing is not None):
                    raise IntelligenceError('Model budget pacing policy mismatch')
                if has_pacing and db.execute('SELECT policy FROM pacing WHERE id=1').fetchone() != (_bound_pacing(self.pacing, self.trial),):
                    raise IntelligenceError('Model budget pacing policy mismatch')
                has_trial = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='trial'").fetchone()
                if bool(has_trial) != (self.trial is not None) or (has_trial and
                        db.execute('SELECT policy FROM trial WHERE id=1').fetchone() != (_policy_bytes(self.trial),)):
                    raise IntelligenceError('Model budget trial policy mismatch')
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
        now = self.clock()
        only, reason = db.execute('SELECT external_only,reason FROM account WHERE id=1').fetchone()
        spent = db.execute('SELECT COALESCE(SUM(amount),0) FROM charges').fetchone()[0]
        result = dict(account=self.account, total_micro_usd=self.total, reserve_micro_usd=self.reserve,
                    charged_micro_usd=spent, available_micro_usd=max(0, self.total-self.reserve-spent),
                    external_only=bool(only), reason=reason)
        if self.pacing is not None:
            p = self.pacing
            if type(now) is not int or not 0 <= now < 2**63:
                raise IntelligenceError('Invalid model budget clock')
            last = db.execute('SELECT last_ms FROM pacing WHERE id=1').fetchone()[0]
            periods = (p['end_ms'] - p['start_ms'] + p['period_ms'] - 1) // p['period_ms']
            current = min(periods, max(0, (now - p['start_ms']) // p['period_ms'] + 1))
            released = (self.total - p['prior_spent_micro_usd']) * current // periods
            blocked = ('OPENAI_CLOCK_ROLLBACK' if now < last else
                       'OPENAI_PACING_NOT_STARTED' if now < p['start_ms'] else
                       'OPENAI_PACING_WINDOW_ENDED' if now >= p['end_ms'] else '')
            if now >= last:
                db.execute('UPDATE pacing SET last_ms=? WHERE id=1', (now,))
            result['remaining_allocation_micro_usd'] = max(0, self.total-spent)
            result['pacing'] = dict(policy=json.loads(_policy_bytes(p)), observed_ms=now, period_count=periods,
                                    released_micro_usd=released, admission_block=blocked)
            result['available_micro_usd'] = 0 if blocked else max(0, min(self.total-spent,
                p['prior_spent_micro_usd'] + released - spent))
        if self.trial is not None:
            result['trial'] = self._trial_snapshot(db, now=now)
        return result

    def _trial_snapshot(self, db, *, exclude=None, now=None):
        now = self.clock() if now is None else now
        if type(now) is not int or not 0 <= now < 2**63:
            raise IntelligenceError('Invalid model budget clock')
        last, stopped, reason = db.execute('SELECT last_ms,stopped,reason FROM trial WHERE id=1').fetchone()
        p, day = self.trial, now // DAY_MS
        rows = db.execute('SELECT c.id,c.amount,t.utc_day,t.admitted_ms,t.dispatched_ms FROM charges c JOIN trial_charges t '
                          'ON c.id=t.charge_id').fetchall()
        if type(last) is not int or last < -1 or stopped not in (0, 1) or type(reason) is not str:
            raise IntelligenceError('Invalid trial clock/stop accounting')
        for token, amount, d, admitted, dispatched in rows:
            if (type(admitted) is not int or not p['start_ms'] <= admitted < p['end_ms']
                    or dispatched is not None and (type(dispatched) is not int or
                        not admitted <= dispatched < p['end_ms'])
                    or type(d) is not int or d != (admitted if dispatched is None else dispatched)//DAY_MS):
                raise IntelligenceError('Invalid trial dispatch attribution')
        total = sum(amount for token, amount, *_ in rows if token != exclude)
        daily = sum(amount for token, amount, d, *_ in rows if token != exclude and d == day)
        # A missing attribution row is corrupt accounting, never free headroom.
        if db.execute("SELECT 1 FROM charges c LEFT JOIN trial_charges t ON c.id=t.charge_id "
                      "WHERE c.id!='initial' AND t.charge_id IS NULL LIMIT 1").fetchone():
            raise IntelligenceError('Model trial attribution missing')
        block = (reason if stopped else 'OPENAI_TRIAL_CLOCK_ROLLBACK' if now < last else
                 'OPENAI_TRIAL_NOT_STARTED' if now < p['start_ms'] else
                 'OPENAI_TRIAL_WINDOW_ENDED' if now >= p['end_ms'] else '')
        if now >= last:
            db.execute('UPDATE trial SET last_ms=? WHERE id=1', (now,))
        return dict(policy=json.loads(_policy_bytes(p)), charged_micro_usd=total,
                    remaining_micro_usd=max(0, p['total_micro_usd']-total),
                    utc_day=day, utc_day_charged_micro_usd=daily,
                    utc_day_remaining_micro_usd=max(0, p['utc_day_micro_usd']-daily),
                    stopped=bool(stopped), reason=reason, admission_block=block, observed_ms=now)

    def _trial_reason(self, db, amount, *, exclude=None, now=None):
        state = self._trial_snapshot(db, exclude=exclude, now=now)
        return (state['admission_block'] or
                ('OPENAI_TRIAL_TOTAL_LIMIT' if amount >= state['remaining_micro_usd'] else
                 'OPENAI_TRIAL_DAILY_LIMIT' if amount >= state['utc_day_remaining_micro_usd'] else ''))

    def snapshot(self):
        with self.transaction() as db:
            return self._snapshot(db)

    def guard_trial(self):
        """Block paid external continuation after trial expiry/stop or untrusted accounting."""
        state = self.snapshot()
        if self.trial is not None:
            reason = state['trial']['admission_block'] or (
                state['pacing']['admission_block']
                if state['pacing']['admission_block'] == 'OPENAI_CLOCK_ROLLBACK' else '') or (
                state['reason'] if state['reason'] == 'OPENAI_USAGE_EXCEEDED_BOUND' else '')
            if reason:
                raise AdmissionDeferred(reason)

    def export(self):
        """Private accounting export, including unknowns and original dispatch UTC attribution."""
        with self.transaction() as db:
            state = self._snapshot(db)
            state['charges'] = [dict(id=r[0], amount_micro_usd=r[1], state=r[2], request_id=r[3])
                                for r in db.execute('SELECT id,amount,state,request_id FROM charges ORDER BY id')]
            if self.trial is not None:
                state['trial_dispatch'] = [dict(charge_id=r[0], utc_day=r[1], admitted_ms=r[2], dispatched_ms=r[3]) for r in
                                          db.execute('SELECT * FROM trial_charges ORDER BY charge_id')]
            return state

    @staticmethod
    def _switch(db, reason):
        # One switches row per real switch; repeating it while already external-only is a no-op.
        if db.execute('UPDATE account SET external_only=1,reason=? WHERE id=1 AND external_only=0',
                      (reason,)).rowcount:
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
            trial_refusal = self._trial_reason(db, amount, now=s['trial']['observed_ms']) if self.trial is not None else ''
            if self.pacing is not None:
                if s['remaining_allocation_micro_usd'] == 0:
                    self._switch(db, 'OPENAI_ALLOCATION_EXHAUSTED')
                    return None
                deferred = trial_refusal or s['pacing']['admission_block'] or (
                    'OPENAI_REQUEST_EXCEEDS_REMAINING' if amount > s['remaining_allocation_micro_usd'] else
                    'OPENAI_PACING_LIMIT' if amount > s['available_micro_usd'] else '')
                if not deferred:
                    token = uuid.uuid4().hex
                    db.execute('INSERT INTO charges VALUES(?,?,?,?)', (token, amount, 'RESERVED', request_id))
                    if self.trial is not None:
                        now = s['trial']['observed_ms']
                        db.execute('INSERT INTO trial_charges VALUES(?,?,?,NULL)', (token, now//DAY_MS, now))
                    return token
                # Exit/commit the clock watermark before raising this temporary refusal.
            elif amount > s['available_micro_usd']:
                self._switch(db, 'OPENAI_OPERATING_LIMIT')
                return None
            else:
                token = uuid.uuid4().hex
                db.execute('INSERT INTO charges VALUES(?,?,?,?)', (token, amount, 'RESERVED', request_id))
                return token
        raise AdmissionDeferred(deferred)

    def before_dispatch(self, token):
        """Recheck a reserved POST at the transport boundary; refund only known-unsent work.

        The caller must invoke this before transport, never after an uncertain send.
        Commit the refusal/refund and clock watermark before raising. Storage failures
        roll back and retain the original conservative reservation.
        """
        with self.transaction() as db:
            row = db.execute('SELECT state,amount FROM charges WHERE id=?', (token,)).fetchone()
            if row is None or row[0] != 'RESERVED':
                raise IntelligenceError('Unknown or already settled model reservation')
            if self.trial is not None and db.execute(
                    'SELECT dispatched_ms FROM trial_charges WHERE charge_id=?', (token,)).fetchone() != (None,):
                raise IntelligenceError('Trial reservation already dispatched or missing')
            s = self._snapshot(db)
            reason = s['reason'] if s['external_only'] else (
                self._trial_reason(db, row[1], exclude=token, now=s['trial']['observed_ms']) if self.trial is not None else
                s['pacing']['admission_block'] if self.pacing is not None else '')
            reason = reason or (s['pacing']['admission_block'] if self.pacing is not None else '')
            if not reason:
                if self.trial is not None:
                    now = s['trial']['observed_ms']
                    db.execute('UPDATE trial_charges SET utc_day=?,dispatched_ms=? WHERE charge_id=?',
                               (now//DAY_MS, now, token))
                return
            db.execute("UPDATE charges SET amount=0,state='SETTLED' WHERE id=?", (token,))
        raise AdmissionDeferred(reason)

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
            if self.trial is not None:
                # Settlement never reassigns a charge to today's UTC bucket.
                p = self.trial
                total = db.execute('SELECT COALESCE(SUM(c.amount),0) FROM charges c JOIN trial_charges t '
                                   'ON c.id=t.charge_id').fetchone()[0]
                day = db.execute('SELECT utc_day FROM trial_charges WHERE charge_id=?', (token,)).fetchone()[0]
                daily = db.execute('SELECT COALESCE(SUM(c.amount),0) FROM charges c JOIN trial_charges t '
                                   'ON c.id=t.charge_id WHERE t.utc_day=?', (day,)).fetchone()[0]
                reason = ('OPENAI_TRIAL_TOTAL_STOP' if total >= p['total_micro_usd'] else
                          'OPENAI_TRIAL_DAILY_STOP' if daily >= p['utc_day_micro_usd'] else '')
                if reason:
                    db.execute("UPDATE trial SET stopped=1,reason=? WHERE id=1 AND stopped=0", (reason,))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'status', 'export', 'enable-pacing', 'enable-trial'))
    parser.add_argument('--path', required=True)
    parser.add_argument('--account', required=True)
    parser.add_argument('--initial-spent-micro-usd', type=int)
    parser.add_argument('--routing-file', help='Reviewed v3/v4 routing JSON; required for paced ledgers')
    args = parser.parse_args(argv)
    options = {}
    if args.routing_file:
        from larp.intelligence.routing import validate_routing_spec
        spec = json.loads(Path(args.routing_file).read_bytes())
        validate_routing_spec(spec)
        if spec['schema'] not in ('AIandRouting.v3', 'AIandRouting.v4') or spec['budget_account'] != args.account:
            parser.error('A matching reviewed v3/v4 routing file is required')
        options = dict(pacing=spec['openai_pacing'], total=spec['openai_pacing']['total_micro_usd'], reserve=0)
        if spec.get('openai_trial') is not None:
            options['trial'] = spec['openai_trial']
    if args.command == 'enable-trial':
        if 'trial' not in options:
            parser.error('enable-trial requires reviewed trial routing')
        budget = ModelBudget.enable_trial(args.path, args.account, **options)
    elif args.command == 'enable-pacing':
        if not options:
            parser.error('enable-pacing requires --routing-file')
        budget = ModelBudget.enable_pacing(args.path, args.account, pacing=options['pacing'],
                                           total=options['total'], trial=options.get('trial'))
    elif args.command == 'init':
        budget = ModelBudget.initialize(args.path, args.account, initial_spent=args.initial_spent_micro_usd, **options)
    else:
        budget = ModelBudget(args.path, args.account, **options)
    print(json.dumps(budget.export() if args.command == 'export' else budget.snapshot(), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""S5-DEPLOY01: explicitly retire an expired trial binding without resetting model accounting.

Run with every model worker stopped, as the ledger owner. No provider calls. Exact expected hashes and
an exclusive SQLite transaction fence stale inputs; the original bytes and trial tables remain available.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

from larp.contracts import ContractError
from larp.intelligence.model_budget import _bound_pacing, _policy_bytes, _private_parent, validate_trial
from larp.intelligence.routing import validate_routing_spec


def retire(path, routing_raw, *, expected_sha256, routing_sha256, backup_dir, now_ms):
    path, backup_dir = Path(path).absolute(), Path(backup_dir).absolute()
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ContractError('Private regular ledger required')
    _private_parent(path)
    if hashlib.sha256(routing_raw).hexdigest() != routing_sha256:
        raise ContractError('Routing hash mismatch')
    spec = json.loads(routing_raw)
    validate_routing_spec(spec)
    if 'openai_trial' in spec or 'openai_pacing' not in spec:
        raise ContractError('Explicit paced non-trial routing required')
    db = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=1)
    try:
        if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
            raise ContractError('Stopped DELETE-journal ledger required')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN EXCLUSIVE')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ContractError('Ledger hash mismatch')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables != {'account', 'charges', 'switches', 'pacing', 'trial', 'trial_charges'}:
            raise ContractError('Expected original trial schema required')
        account = db.execute('SELECT * FROM account ORDER BY id').fetchall()
        charges = db.execute('SELECT * FROM charges ORDER BY id').fetchall()
        switches = db.execute('SELECT * FROM switches ORDER BY id').fetchall()
        pacing_row = db.execute('SELECT policy,last_ms FROM pacing WHERE id=1').fetchone()
        trial_rows = db.execute('SELECT * FROM trial ORDER BY id').fetchall()
        attribution = db.execute('SELECT * FROM trial_charges ORDER BY charge_id').fetchall()
        trial = json.loads(trial_rows[0][1]) if len(trial_rows) == 1 else None
        validate_trial(trial)
        p = spec['openai_pacing']
        if (account != [(1, spec['budget_account'], p['total_micro_usd'], 0, 0, '')]
                or db.execute("SELECT amount,state FROM charges WHERE id='initial'").fetchone()
                    != (p['prior_spent_micro_usd'], 'SETTLED')
                or any(r[2] not in ('SETTLED', 'UNKNOWN') for r in charges)
                or sum(r[1] for r in charges) > p['total_micro_usd']
                or pacing_row[0] != _bound_pacing(p, trial)
                or now_ms < max(trial['end_ms'], pacing_row[1], trial_rows[0][2])
                or trial_rows[0][3:] != (0, '')):
            raise ContractError('Trial expiry/accounting/pacing/safety state mismatch')
        # No request may lose its historic dispatch attribution. Initial spend predates the trial.
        if {r[0] for r in attribution} != {r[0] for r in charges if r[0] != 'initial'}:
            raise ContractError('Complete historical request attribution required')
        backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        _private_parent(backup_dir / 'check')
        backup = backup_dir / ('trial-' + expected_sha256 + '.sqlite')
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        directory_fd = os.open(backup_dir, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        db.execute('ALTER TABLE trial RENAME TO retired_trial')
        db.execute('ALTER TABLE trial_charges RENAME TO retired_trial_charges')
        db.execute('UPDATE pacing SET policy=? WHERE id=1', (_policy_bytes(p),))
        db.execute('CREATE TABLE trial_retirements (source_sha256 TEXT PRIMARY KEY, routing_sha256 TEXT NOT NULL, '
                   'retired_ms INTEGER NOT NULL, trial_policy TEXT NOT NULL)')
        db.execute('INSERT INTO trial_retirements VALUES(?,?,?,?)',
                   (expected_sha256, routing_sha256, now_ms, _policy_bytes(trial)))
        if (account != db.execute('SELECT * FROM account ORDER BY id').fetchall()
                or charges != db.execute('SELECT * FROM charges ORDER BY id').fetchall()
                or switches != db.execute('SELECT * FROM switches ORDER BY id').fetchall()
                or trial_rows != db.execute('SELECT * FROM retired_trial ORDER BY id').fetchall()
                or attribution != db.execute('SELECT * FROM retired_trial_charges ORDER BY charge_id').fetchall()
                or pacing_row[1] != db.execute('SELECT last_ms FROM pacing WHERE id=1').fetchone()[0]):
            raise ContractError('Accounting preservation check failed')
        db.commit()
        return dict(status='EXPIRED_TRIAL_RETIRED', source_sha256=expected_sha256,
            routing_sha256=routing_sha256, backup_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
            charged_micro_usd=sum(r[1] for r in charges),
            unknown_micro_usd=sum(r[1] for r in charges if r[2] == 'UNKNOWN'),
            charges_preserved=len(charges), attribution_preserved=len(attribution), trial_id=trial['trial_id'])
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', required=True)
    parser.add_argument('--routing-file', required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--routing-sha256', required=True)
    parser.add_argument('--backup-dir', required=True)
    args = parser.parse_args(argv)
    try:
        result = retire(args.ledger, Path(args.routing_file).read_bytes(),
            expected_sha256=args.expected_sha256, routing_sha256=args.routing_sha256,
            backup_dir=args.backup_dir, now_ms=time.time_ns() // 1_000_000)
    except (ContractError, OSError, ValueError, sqlite3.Error, TypeError, IndexError) as exc:
        print(json.dumps(dict(status='TRIAL_RETIREMENT_REFUSED', reason=type(exc).__name__)))
        return 4
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

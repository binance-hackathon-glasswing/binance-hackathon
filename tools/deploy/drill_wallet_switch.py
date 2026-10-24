"""RG6 wallet-switch harness (REHEARSAL_GATES_20261019.md RG6; runbook §5; IDEA-042 LD21-H).

`preflight` is read-only: every `switch_wallet` precondition is checked separately inside READ ONLY database
transactions, and the final wallet's directories are inspected without being created or marked. It prints one
JSON report and exits 0 only when the switch would be accepted.

`switch` is the operator's drill/activation step on an approved target. It repeats the preflight, needs the old run
ID typed back (`--confirm-old-run`), calls `larp.runtime.live.switch_wallet` and writes its record to a new file.

    python tools/deploy/drill_wallet_switch.py preflight --config /etc/larp/runtime.json \\
        --new-wallet 0x... --new-ai-seeds-dir DIR --new-nonce-dir DIR
    python tools/deploy/drill_wallet_switch.py switch --config ... (same) --new-run RUN \\
        --initial-projection FILE --confirm-old-run OLD_RUN --record-out NEW_FILE

No credentials, DSNs or secret values are printed. Wallet addresses are public and belong in the switch record.
"""

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sys

from larp.runtime.live import ADDRESS, MARKER, LiveStartRefused, switch_wallet


def read_only(store):
    """A copy of `store` whose transactions are READ ONLY; a write inside one fails. `store` itself is unchanged."""
    import copy
    inner, store = store.transaction, copy.copy(store)

    @contextmanager
    def transaction():
        with inner() as db:
            db.execute('SET TRANSACTION READ ONLY')
            yield db
    store.transaction = transaction
    return store


def directory_state(path, wallet):
    """What `bind_directory` would find, without creating or marking anything."""
    path = Path(path)
    if not path.exists():
        ancestor = next(p for p in path.parents if p.exists())  # bind_directory creates missing parents
        return 'WILL_CREATE' if ancestor.is_dir() else 'ANCESTOR_NOT_DIRECTORY'
    if not path.is_dir():
        return 'NOT_A_DIRECTORY'
    marker = path / MARKER
    if marker.exists():
        return 'BOUND_TO_NEW_WALLET' if marker.read_text(encoding='utf-8').strip() == wallet.lower() else 'BOUND_TO_OTHER_WALLET'
    return 'EMPTY' if not any(path.iterdir()) else 'UNMARKED_RECORDS'


def preflight(store, *, old_run, new_wallet, old_dirs, new_dirs):
    """The switch's preconditions as a report; `ready` is true only if `switch_wallet` would accept them."""
    old = store.load(old_run).read()
    blockers = []
    valid = bool(ADDRESS.fullmatch(new_wallet or '')) and new_wallet.lower() != str(old['wallet_id']).lower()
    if not valid:
        blockers.append('NEW_WALLET_INVALID_OR_SAME')
    open_rounds = len(store.open_rounds(old_run))
    if open_rounds:
        blockers.append('OPEN_ROUNDS')
    if old['reservations']:
        blockers.append('RESERVATIONS')
    with store.transaction() as db:
        pending = db.execute('SELECT count(*) FROM execution_records WHERE run_id=%s AND NOT terminal',
                             (old_run,)).fetchone()[0]
    if pending:
        blockers.append('UNFINISHED_EXECUTIONS')
    held = sorted(k for k, v in (old['projection'].get('balances') or {}).items() if k not in ('USDT', 'BNB') and v)
    if held:
        blockers.append('NOT_FLAT')
    resolved_old = {Path(d).resolve() for d in old_dirs}
    resolved_new = [Path(d).resolve() for d in new_dirs]
    if any(d in resolved_old for d in resolved_new) or len(set(resolved_new)) != 2:
        blockers.append('DIRECTORIES_NOT_SEPARATE')
    dirs = {str(d): directory_state(d, new_wallet if valid else '') for d in new_dirs}
    if any(state not in ('WILL_CREATE', 'EMPTY', 'BOUND_TO_NEW_WALLET') for state in dirs.values()):
        blockers.append('DIRECTORY_UNUSABLE')
    return dict(schema='WalletSwitchPreflight.v1', old_run=old_run, old_wallet=str(old['wallet_id']).lower(),
                new_wallet=(new_wallet or '').lower(), old_version=old['version'], open_rounds=open_rounds,
                reservations=len(old['reservations']), unfinished_executions=pending, held_tokens=held,
                balances={k: v for k, v in (old['projection'].get('balances') or {}).items() if v},
                new_directories=dirs, blockers=blockers, ready=not blockers)


def _store(config):
    from larp.runtime.database import open_service_store
    return open_service_store(config)


def main(argv=None, *, open_store=_store):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('preflight', 'switch'):
        p = sub.add_parser(name)
        p.add_argument('--config', required=True, help='the dev runtime.json (old run, its directories, database)')
        p.add_argument('--new-wallet', required=True)
        p.add_argument('--new-ai-seeds-dir', required=True)
        p.add_argument('--new-nonce-dir', required=True)
        if name == 'switch':
            p.add_argument('--new-run', required=True)
            p.add_argument('--initial-projection', required=True, help='JSON opening projection for the new run')
            p.add_argument('--confirm-old-run', required=True, help='type the old run ID back')
            p.add_argument('--record-out', required=True, help='new file for the WalletSwitch.v1 record')
    args = parser.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    old_run, old_dirs = config['run_id'], [config['ai_seeds_dir'], config['nonce_dir']]
    new_dirs = [args.new_ai_seeds_dir, args.new_nonce_dir]
    report = preflight(read_only(open_store(config)), old_run=old_run, new_wallet=args.new_wallet,
                       old_dirs=old_dirs, new_dirs=new_dirs)
    if args.command == 'preflight' or not report['ready']:
        print(json.dumps(report, sort_keys=True))
        return 0 if report['ready'] else 3
    if args.confirm_old_run != old_run:
        print(json.dumps(dict(status='REFUSED', reason='CONFIRMATION_MISMATCH')))
        return 2
    record_path = Path(args.record_out)
    if record_path.exists():
        print(json.dumps(dict(status='REFUSED', reason='RECORD_EXISTS')))
        return 2
    projection = json.loads(Path(args.initial_projection).read_text(encoding='utf-8'))
    try:
        record = switch_wallet(open_store(config), old_run=old_run, new_run=args.new_run, new_wallet=args.new_wallet,
                               chain_id=56, initial_projection=projection, old_dirs=old_dirs, new_dirs=new_dirs)
    except LiveStartRefused as refusal:
        print(json.dumps(dict(status='REFUSED', reason=str(refusal))))
        return 3
    with open(record_path, 'x', encoding='utf-8') as stream:
        stream.write(json.dumps(record, sort_keys=True, indent=2) + '\n')
    print(json.dumps(dict(status='SWITCHED', record=record), sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())

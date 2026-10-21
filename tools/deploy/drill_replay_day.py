"""RG8 actual-day replay harness (REHEARSAL_GATES_20261019.md RG8; DR-19; IDEA-042 LD21-H).

Replays a run's journal into an isolated, empty, migrated target database with `larp.integration.replay.replay_live`
and checks that the replayed head equals the original head. The source is read in READ ONLY transactions. Every
live port of the rebuilt context builder raises, so only the answers recorded in each round's context are used.

The context builder, planner and policy are rebuilt from the run's own pinned runtime configuration exactly as
`larp.runtime.service.build_driver` builds them (profile, session calendar, intelligence settings, issuers,
price-jump settings), without secrets, market clients or the evidence store.

    python tools/deploy/drill_replay_day.py --config /etc/larp/runtime.json \\
        --target-dsn-file PRIVATE_DSN_FILE [--through-sequence N]

Exit 0: the replayed head equals the source head at that sequence. 1: it differs or replay refused. 2: a refused
target (not empty, or the source database itself).
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drill_wallet_switch import read_only  # noqa: E402

from larp.contracts import ContractError, Document  # noqa: E402


class LivePortCalled(RuntimeError):
    """A replay reached a live port: the recorded context did not cover it."""


DEAD_CALLS = []  # every live-port call, even one the coordinator records as a context failure


def dead(*args):
    DEAD_CALLS.append(1)
    raise LivePortCalled('replay must not call a live port')


def builder_from_config(config):
    """(context builder, planner, profile, profile hash) as `build_driver` builds them, with every port dead."""
    from larp.integration.runtime import ContextBuilder, RuntimePlanner
    from larp.intelligence.config import load_config, load_registry
    from larp.intelligence.gate import lifecycle_policy_from
    from larp.runtime.driver import SessionCalendar
    from larp.runtime.service import _pinned_json, balance_settings
    d = config['driver']
    profile = _pinned_json(d['strategy_profile_file'], d['strategy_profile_sha256'], 'Strategy profile')
    calendar = SessionCalendar(_pinned_json(d['session_calendar_file'], d['session_calendar_sha256'],
                                            'Session calendar'))
    profile_hash = Document.from_dict(profile).digest('StrategyProfile.v1')
    intelligence = load_config(d['intelligence_mode'])
    registry = load_registry()
    issuers = {}
    for issuer_id, meta in d['issuers'].items():
        known = [e for e in registry.entries if e.issuer_id == issuer_id]
        if not known or meta.get('token') != known[0].token or not meta.get('underlying_id'):
            raise ContractError('Driver issuer does not match the issuer registry: ' + issuer_id)
        issuers[issuer_id] = dict(token=meta['token'], underlying_id=meta['underlying_id'])
    builder = ContextBuilder(profile=profile, profile_hash=profile_hash, run_id=config['run_id'], issuers=issuers,
                             market=dead, health=dead, calendar=calendar,
                             lifecycle_policy=lifecycle_policy_from(intelligence),
                             gas_quotes=dead if 'gas_floor_bnb_units' in profile else None)
    balance = balance_settings(d, config.get('mode', 'offline'))
    if balance is not None:
        builder.price_jump = dict(bps=balance['price_jump_bps'], hold_ms=balance['max_age_ms'])
    planner = RuntimePlanner(job_validity_ms=intelligence.p('job_validity_ms'),
                             job_max_attempts=intelligence.p('job_max_attempts'), issuers=issuers)
    return builder, planner, profile, profile_hash


def replay_run(source, target, *, run_id, builder, planner, profile, profile_hash, version_id, address,
               test_rounds, through_sequence=None, require_version=True):
    """A ReplayDrill.v1 report and exit code. `source` should be read-only; `target` must not hold the run."""
    from larp.integration.replay import replay_live
    from larp.integration.runtime import StrategyPolicy, initial_policy_state
    from larp.integration.settlement import ExecutionBridge, settle
    with target.transaction() as db:
        if db.execute('SELECT count(*) FROM runs WHERE run_id=%s', (run_id,)).fetchone()[0]:
            return dict(schema='ReplayDrill.v1', run_id=run_id, status='REFUSED', reason='TARGET_NOT_EMPTY'), 2
    with source.transaction() as db:
        wallet_id, chain_id, initial, version = db.execute(
            'SELECT wallet_id,chain_id,initial,version FROM runs WHERE run_id=%s', (run_id,)).fetchone()
        through = version if through_sequence is None else min(through_sequence, version)
        expected = db.execute('SELECT head FROM events WHERE run_id=%s AND sequence=%s', (run_id, through)).fetchone()
    journal = source.journal(run_id, through_version=through)
    calls_before = len(DEAD_CALLS)
    report = dict(schema='ReplayDrill.v1', run_id=run_id, through_sequence=through, batches=len(journal),
                  source_version=version, expected_head=expected[0] if expected else None)
    try:
        head = replay_live(journal, Document(bytes(initial)), target, builder=builder, run_id=run_id,
                           wallet_id=wallet_id, chain_id=chain_id, version_id=version_id, profile_hash=profile_hash,
                           address=address, policy=StrategyPolicy(), planner=planner, execution=ExecutionBridge(),
                           reducer=settle, initial_policy_state=initial_policy_state(run_id, profile),
                           test_rounds=test_rounds, require_version=require_version)
    except Exception as error:  # an IntegrityError/ContractError means the replay diverged from the journal
        reason = 'LIVE_PORT_CALLED' if len(DEAD_CALLS) > calls_before else type(error).__name__
        return dict(report, status='FAIL', reason=reason), 1
    if len(DEAD_CALLS) > calls_before:
        return dict(report, replayed_head=head, status='FAIL', reason='LIVE_PORT_CALLED'), 1
    report.update(replayed_head=head, status='PASS' if head == report['expected_head'] else 'FAIL')
    return report, 0 if report['status'] == 'PASS' else 1


def same_database(config, target_dsn):
    """True when the target DSN names the source's database host and name (the drill must use another database)."""
    from psycopg.conninfo import conninfo_to_dict
    target = conninfo_to_dict(target_dsn)
    if config.get('database_dsn_file'):
        source = conninfo_to_dict(Path(config['database_dsn_file']).read_text(encoding='utf-8').strip())
    else:
        source = dict(host=config.get('database_host'), dbname=config.get('database_name'))
    return (target.get('host'), target.get('dbname')) == (source.get('host'), source.get('dbname'))


def main(argv=None, *, open_source=None, open_target=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--config', required=True, help='the run\'s runtime.json')
    parser.add_argument('--target-dsn-file', required=True, help='private DSN of the empty migrated drill database')
    parser.add_argument('--through-sequence', type=int, help='replay a prefix; default is the whole journal')
    args = parser.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    dsn = Path(args.target_dsn_file).read_text(encoding='utf-8').strip()
    if same_database(config, dsn):
        print(json.dumps(dict(schema='ReplayDrill.v1', status='REFUSED', reason='TARGET_IS_SOURCE')))
        return 2
    if open_source is None:
        from larp.runtime.database import open_service_store as open_source
    if open_target is None:
        from larp.storage.postgres import PostgresStore as open_target
    builder, planner, profile, profile_hash = builder_from_config(config)
    report, code = replay_run(read_only(open_source(config)), open_target(dsn), run_id=config['run_id'],
                              builder=builder, planner=planner, profile=profile, profile_hash=profile_hash,
                              version_id=config['build_id'], address=config['wallet_address'],
                              test_rounds=config.get('mode') != 'live', through_sequence=args.through_sequence)
    print(json.dumps(report, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())

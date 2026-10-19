"""Offline RG-02 packet integrity checks; never certifies drills or enables signing."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_JSON = 1_048_576
MAX_ARTIFACT = 16_777_216
CRITERIA = {
    'RG1': ('release_bindings', 'execution_prerequisites', 'first_round_chain_ack'),
    'RG2': ('boundary_matrix', 'automatic_restart', 'unknown_fencing', 'reservation_nonce_reconciliation', 'round_mapping', 'measured_recovery'),
    'RG3': ('automatic_halt', 'no_execution_while_halted', 'logged_rounds', 'automatic_clear', 'quarantine_fencing', 'measured_latency'),
    'RG4': ('destination_retention', 'hourly_cadence', 'head_verification', 'storage_immutability', 'restore_and_stale_refusal', 'no_secrets'),
    'RG5': ('empty_target_restore', 'checksum_heads', 'quarantine_epoch', 'no_signed_bytes', 'measured_rto_rpo', 'real_alert_ack'),
    'RG6': ('old_run_drained', 'isolated_wallet_records', 'address_mismatch_refused', 'switch_head_and_quarantine', 'shared_ledger_preserved'),
    'RG7': ('adopted_profile_dates', 'no_new_risk_boundary', 'mandatory_exit_obligations', 'no_reinvestment', 'authority_expiry'),
    'RG8': ('immutable_original_inputs', 'shadow_day_head', 'signed_day_head', 'original_build_config', 'no_live_writes'),
    'RG9': ('daily_signed_intervals', 'five_days_and_weekend_or_reviewed_shortfall', 'minimum_size', 'rounds_ack_incidents', 'model_cost_latency', 'separate_unsigned_verdict', 'strategy_t4_review'),
    'RG10': ('dr01_22_signoffs', 'gate_a_b_reviews', 'final_deviations_services', 'frozen_release', 'final_wallet_disposition', 'runbook_rota', 'activation_approval'),
}
IDENTITY = ('source_commit', 'bundle_sha256', 'manifest_sha256', 'profile_sha256',
            'bound_config_sha256', 'run_id', 'wallet_public_address')


class Refused(ValueError):
    pass


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refused('DUPLICATE_KEY')
        result[key] = value
    return result


def load(path):
    with open(path, 'rb') as stream:
        data = stream.read(MAX_JSON + 1)
    if len(data) > MAX_JSON:
        raise Refused('INPUT_TOO_LARGE')
    return json.loads(data, object_pairs_hook=unique)


def identity_valid(value):
    if type(value) is not dict or set(value) != set(IDENTITY):
        return False
    patterns = dict(source_commit=r'[0-9a-f]{40}', run_id=r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',
                    wallet_public_address=r'0x[0-9a-f]{40}')
    return all(type(value[k]) is str and re.fullmatch(patterns.get(k, r'[0-9a-f]{64}'), value[k])
               for k in IDENTITY)


def template():
    return dict(schema='RehearsalEvidenceIndex.v1', identity=dict.fromkeys(IDENTITY), gates=[
        dict(gate=gate, status='NOT_RUN', identity=None, evidence_scope=None,
             operator=None, reviewer=None, started_at_utc=None, ended_at_utc=None,
             procedure_ref=None, approval_ref=None, review_ref=None,
             criteria=dict.fromkeys(criteria, 'NOT_RUN'), artifacts=[])
        for gate, criteria in CRITERIA.items()])


def utc(value):
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
        raise Refused('UTC_REQUIRED')
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')


def artifact_matches(root_fd, item):
    # Flat sanitized export directory only. No nested paths or symlink following.
    if (type(item) is not dict or set(item) != {'file', 'sha256'}
            or type(item['file']) is not str
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', item['file'])
            or type(item['sha256']) is not str or not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])):
        return False
    try:
        fd = os.open(item['file'], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
        with os.fdopen(fd, 'rb') as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode) or not 0 < metadata.st_size <= MAX_ARTIFACT:
                return False
            data = stream.read(MAX_ARTIFACT + 1)
        return len(data) <= MAX_ARTIFACT and hashlib.sha256(data).hexdigest() == item['sha256']
    except OSError:
        return False


def record_reasons(row, expected, root_fd):
    if set(row) != set(template()['gates'][0]):
        return ['RECORD_SCHEMA']
    status = row['status']
    if status not in ('NOT_RUN', 'BLOCKED', 'FAIL', 'INCONCLUSIVE', 'REVIEWED'):
        return ['RECORD_STATUS']
    if status != 'REVIEWED':
        return ['NOT_REVIEWED']
    reasons = []
    if row['identity'] != expected:
        reasons.append('IDENTITY_MISMATCH')
    if row['evidence_scope'] != 'OBSERVED_HOST':
        reasons.append('HOST_EVIDENCE_REQUIRED')
    refs = ('operator', 'reviewer', 'procedure_ref', 'approval_ref', 'review_ref')
    if any(type(row[k]) is not str or not row[k].strip() for k in refs):
        reasons.append('ATTRIBUTION_REQUIRED')
    if row['operator'] == row['reviewer']:
        reasons.append('INDEPENDENT_REVIEW_REQUIRED')
    try:
        if utc(row['ended_at_utc']) < utc(row['started_at_utc']):
            reasons.append('TIME_ORDER')
    except (ValueError, TypeError):
        reasons.append('INVALID_UTC_INTERVAL')
    criteria = row['criteria']
    if (type(criteria) is not dict or set(criteria) != set(CRITERIA[row['gate']])
            or any(value != 'PASS' for value in criteria.values())):
        reasons.append('CRITERIA_INCOMPLETE')
    artifacts = row['artifacts']
    if (type(artifacts) is not list or not 1 <= len(artifacts) <= 100
            or not all(artifact_matches(root_fd, item) for item in artifacts)):
        reasons.append('ARTIFACT_INTEGRITY')
    elif len({item['file'] for item in artifacts}) != len(artifacts):
        reasons.append('DUPLICATE_ARTIFACT')
    return reasons


def check(packet, expected, root):
    if not identity_valid(expected):
        raise Refused('EXPECTED_IDENTITY_REQUIRED')
    if (type(packet) is not dict or set(packet) != {'schema', 'identity', 'gates'}
            or packet['schema'] != 'RehearsalEvidenceIndex.v1' or packet['identity'] != expected):
        raise Refused('PACKET_IDENTITY_OR_SCHEMA')
    rows = packet['gates']
    if type(rows) is not list or len(rows) != len(CRITERIA):
        raise Refused('EXACT_GATE_SET_REQUIRED')
    if any(type(row) is not dict or type(row.get('gate')) is not str for row in rows):
        raise Refused('EXACT_GATE_SET_REQUIRED')
    if {row['gate'] for row in rows} != set(CRITERIA):
        raise Refused('EXACT_GATE_SET_REQUIRED')
    # Disallow root symlinks (including ancestors) as well as artifact symlinks.
    root = Path(root).absolute()
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise Refused('EVIDENCE_DIRECTORY_REFUSED')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        results = [dict(gate=row['gate'], reasons=record_reasons(row, expected, fd)) for row in rows]
    finally:
        os.close(fd)
    complete = not any(row['reasons'] for row in results)
    return dict(schema='RehearsalEvidenceCheck.v1',
                scope='LOCAL_INDEX_AND_ARTIFACT_INTEGRITY_ONLY',
                packet_complete=complete, gate_c_accepted=False, signing_enabled=False,
                host_results_verified=False, results=results)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--out', required=True)
    verify = sub.add_parser('check')
    verify.add_argument('--packet', required=True)
    verify.add_argument('--identity', required=True)
    verify.add_argument('--evidence-root', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            with open(args.out, 'x', encoding='utf-8') as stream:
                stream.write(json.dumps(template(), indent=2) + '\n')
            print(json.dumps(dict(created=True, gate_c_accepted=False, signing_enabled=False)))
            return 0
        result = check(load(args.packet), load(args.identity), args.evidence_root)
        print(json.dumps(result, sort_keys=True))
        return 0 if result['packet_complete'] else 1
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        # Do not expose input content, filenames, URLs, credentials or raw exceptions.
        print(json.dumps(dict(error='PACKET_REFUSED', gate_c_accepted=False, signing_enabled=False)))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

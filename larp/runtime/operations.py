"""Explicit maintenance CLI. It has no signer, trading loop or promotion command."""

import argparse
import json
import os
from pathlib import Path
import time

from larp.contracts import ContractError, Document
from larp.runtime.database import IamPostgresStore, check_iam_settings
from larp.runtime.maintenance import Maintenance, HOUR_MS, VerificationState
from larp.storage.archive import S3Archive
from larp.storage.backup import GZIP_MAGIC, restore, restore_chain
from larp.storage.postgres import PostgresStore, Unavailable, doc


def validate_config(value):
    if not isinstance(value, dict):
        raise ContractError('Invalid operations configuration object')
    required = ('deployment', 'region', 'account_id', 'run_id', 'archive_bucket',
                'archive_prefix', 'kms_key', 'retention_days', 'backup_interval_hours',
                'database_host', 'database_user', 'database_name', 'database_ca_file', 'database_ca_sha256',
                'max_attempts', 'retry_seconds', 'max_archive_bytes')
    if value.get('schema') != 'OperationsConfiguration.v1':
        raise ContractError('Invalid operations configuration schema')
    missing = [key for key in required if value.get(key) is None or value.get(key) == '']
    if missing:
        raise ContractError('Missing operations settings: ' + ','.join(missing))
    for key in ('retention_days', 'backup_interval_hours', 'max_attempts', 'retry_seconds', 'max_archive_bytes'):
        if type(value[key]) is not int or value[key] < 1:
            raise ContractError('Invalid positive integer setting: ' + key)
    if 'max_exports_per_day' in value and (type(value['max_exports_per_day']) is not int
                                           or value['max_exports_per_day'] < 1):
        raise ContractError('Invalid positive integer setting: max_exports_per_day')
    # Explicit per-object Object Lock expiry overrides the bucket default.
    # Match deploy/aws/variables.tf, including the full archive retention window.
    if value['retention_days'] < 82:
        raise ContractError('Archive retention must be at least 82 days')
    if value['archive_prefix'].split('/')[0] != 'archive':
        raise ContractError('Archive namespace must begin with archive/')
    if value['database_user'] != 'larp_archive':
        raise ContractError('Maintenance requires the dedicated larp_archive database role')
    check_iam_settings(value, 'larp_archive')
    return value


def cloud_clients(c):
    import boto3
    from botocore.config import Config
    session = boto3.Session(region_name=c['region'])
    settings = Config(connect_timeout=5, read_timeout=15, retries={'total_max_attempts': 2, 'mode': 'standard'},
                      ignore_configured_endpoint_urls=True)
    return {name: session.client(name, config=settings) for name in ('s3', 'rds', 'cloudwatch')}


# IDEA-100 DB5: after a run whose heavy steps failed, those steps (backup export, daily full check) wait 60 s, then
# twice as long after each further failure, up to an hour. The anchor, delivery and health keep the timer's cadence.
BACKOFF_FIRST_S, BACKOFF_MAX_S = 60, 3600
MAX_EXPORTS_PER_DAY = 3


def backoff_seconds(failures):
    """The pause after `failures` consecutive failed runs (1 -> 60 s, 2 -> 120 s, ... capped at an hour)."""
    return min(BACKOFF_FIRST_S * 2 ** (failures - 1), BACKOFF_MAX_S)


def _metric(deployment, service, name, value):
    return dict(MetricName=name, Value=value, Unit='Count',
                Dimensions=[dict(Name='Deployment', Value=deployment), dict(Name='Service', Value=service)])


def publish_health(client, deployment, healthy, services=None):
    """Archive heartbeat and health, plus the service-level signals (IDEA-047 R5). `services` is a ServiceHealth.v1
    dict, or None when the database could not be read: then only the runtime heartbeat is sent, as 0, and the other
    service alarms see missing data, which they treat as breaching."""
    data = [_metric(deployment, 'archive', 'Heartbeat', 1), _metric(deployment, 'archive', 'Healthy', int(healthy))]
    if services is None:
        data.append(_metric(deployment, 'runtime', 'Heartbeat', 0))
    else:
        data += [_metric(deployment, 'runtime', 'Heartbeat', int(services['runtime_alive'])),
                 _metric(deployment, 'runtime', 'Halted', len(services['halt_reasons'])),
                 _metric(deployment, 'runtime', 'Quarantined', int(services['quarantined'])),
                 _metric(deployment, 'runtime', 'GasPairUnaffordable', int(services.get('gas_pair_unaffordable', False))),
                 _metric(deployment, 'uploader', 'OverdueLogs', services['audit_overdue']),
                 _metric(deployment, 'signer', 'UnansweredRequests', services['signing_unanswered'])]
    client.put_metric_data(Namespace='LARP/Runtime', MetricData=data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'once', 'health', 'restore'))
    parser.add_argument('--config', required=True)
    parser.add_argument('--receipt', action='append', help='a backup receipt; repeat for every Backup.v2 segment')
    parser.add_argument('--target-dsn-file')
    args = parser.parse_args(argv)
    clients, c = None, None
    try:
        c = validate_config(json.loads(Path(args.config).read_text(encoding='utf-8')))
        if args.command == 'check':
            print(json.dumps(dict(configuration_valid=True, signing_enabled=False, cloud_verified=False)))
            return 0
        clients = cloud_clients(c)
        archive = S3Archive(clients['s3'], bucket=c['archive_bucket'], account_id=c['account_id'],
                            kms_key=c['kms_key'], prefix=c['archive_prefix'], retention_days=c['retention_days'],
                            max_bytes=c['max_archive_bytes'])
        if args.command == 'restore':
            if not args.receipt or not args.target_dsn_file:
                raise ContractError('Restore requires a pinned receipt and an empty-target DSN credential file')
            payloads = [archive.fetch(Document(Path(p).read_bytes())) for p in args.receipt]
            target = PostgresStore(Path(args.target_dsn_file).read_text(encoding='utf-8').strip())
            # Migrations must already be applied with a provisioning role.
            if len(payloads) == 1 and payloads[0][:2] != GZIP_MAGIC:
                restore(target, Document(payloads[0]))  # Backup.v1
            else:
                restore_chain(target, payloads)  # Backup.v2: every segment receipt of the chain, in any order
            print(json.dumps(dict(restored=True, quarantined=True, signing_enabled=False)))
            return 0
        # IDEA-095: systemd's StateDirectory= holds the verification checkpoint between runs.
        verification = VerificationState(os.environ['STATE_DIRECTORY']) if os.environ.get('STATE_DIRECTORY') else None
        worker = Maintenance(IamPostgresStore(c, clients['rds']), archive,
                             backup_interval_ms=c['backup_interval_hours'] * HOUR_MS,
                             max_attempts=c['max_attempts'], retry_ms=c['retry_seconds'] * 1000,
                             max_payload_bytes=c['max_archive_bytes'], verification=verification,
                             max_exports_per_day=c.get('max_exports_per_day', MAX_EXPORTS_PER_DAY))
        failures = []
        # The backoff lives in the unit's state directory with the verification checkpoint, so a restart keeps it.
        # Without one there is no backoff (as without IDEA-095's checkpoint).
        now_ms = int(time.time() * 1000)
        saved = verification.load(c['run_id']) if verification else {}
        paused = type(saved.get('resume_ms')) is int and now_ms < saved['resume_ms']

        def deliver():
            # Per invocation bound; timer supplies subsequent delivery capacity.
            for _ in range(4):
                if not worker.once(c['run_id'], int(time.time() * 1000)):
                    break

        def report():
            health = worker.health(c['run_id'], int(time.time() * 1000)).read()
            overdue = worker.verification_reasons(c['run_id'], int(time.time() * 1000)) if verification else []
            if overdue:
                health['healthy'] = False
                health['reasons'] = sorted(set(health['reasons'] + overdue))
            if failures:
                health['healthy'] = False
                health['reasons'] = sorted(set(health['reasons'] + ['ARCHIVE_PREPARATION_FAILED']))
                health['preparation_error'] = ','.join(sorted(set(failures)))
            if paused:
                health['healthy'] = False
                health['reasons'] = sorted(set(health['reasons'] + ['ARCHIVE_BACKOFF']))
                health['resume_ms'] = saved['resume_ms']
            health['services'] = worker.service_health(c['run_id'], int(time.time() * 1000)).read()
            publish_health(clients['cloudwatch'], c['deployment'], health['healthy'], health['services'])
            return health
        if args.command == 'once':
            # IDEA-094: the hour's anchor is queued and sent, and health is published, before any backup export
            # starts. A killed or refused export then cannot cost the anchor or the metric; its slot is recorded and
            # is not exported again, so the next run reports it (BACKUP_PREPARATION_FAILED).
            try:
                worker.prepare_anchor(c['run_id'], int(time.time() * 1000))
            except Exception as exc:
                failures.append(type(exc).__name__)
            deliver()
            health = report()
            if not paused:
                try:
                    if worker.prepare_backup(c['run_id'], int(time.time() * 1000)) is not None:
                        deliver()
                except Exception as exc:
                    failures.append(type(exc).__name__)
                # IDEA-095: anchors verify from the saved checkpoint; the whole journal is re-read once per backup
                # interval, last, so a run killed inside it has already sent its anchor, health and backup.
                try:
                    if verification is not None:
                        worker.full_check(c['run_id'], int(time.time() * 1000))
                except Exception as exc:
                    failures.append(type(exc).__name__)
                if verification is not None:
                    # Only a run that tried the heavy steps moves the backoff: a failure lengthens it, success clears it.
                    count = saved.get('failures') if type(saved.get('failures')) is int else 0
                    try:
                        verification.save(c['run_id'], **(
                            dict(failures=count + 1, resume_ms=now_ms + backoff_seconds(count + 1) * 1000)
                            if failures else dict(failures=0, resume_ms=None)))
                    except OSError:
                        failures.append('BackoffStateUnwritable')
            health = report()
        else:
            health = report()
        print(json.dumps(health, sort_keys=True))
        return 0 if health['healthy'] else 1
    except Exception:
        # SDK, filesystem and database exceptions may include credentials or raw I/O.
        # Never print arbitrary exception text. Missing heartbeat also alarms.
        if clients and c:
            try:
                publish_health(clients['cloudwatch'], c['deployment'], False)
            except Exception:
                pass
        print(json.dumps(dict(healthy=False, reason='OPERATIONS_FAILED', signing_enabled=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

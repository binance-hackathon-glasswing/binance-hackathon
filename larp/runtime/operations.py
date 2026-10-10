"""Explicit maintenance CLI. It has no signer, trading loop or promotion command."""

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import time

from larp.contracts import ContractError, Document
from larp.runtime.maintenance import Maintenance, HOUR_MS
from larp.storage.archive import S3Archive
from larp.storage.backup import restore
from larp.storage.postgres import PostgresStore, Unavailable, doc


def validate_config(value):
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
    if value['archive_prefix'].split('/')[0] != 'archive':
        raise ContractError('Archive namespace must begin with archive/')
    if value['database_user'] != 'larp_archive':
        raise ContractError('Maintenance requires the dedicated larp_archive database role')
    if not Path(value['database_ca_file']).is_file():
        raise ContractError('Pinned RDS certificate bundle is missing')
    if hashlib.sha256(Path(value['database_ca_file']).read_bytes()).hexdigest() != value['database_ca_sha256']:
        raise ContractError('RDS certificate bundle hash differs from configuration')
    return value


class IamPostgresStore(PostgresStore):
    def __init__(self, config, rds):
        self.config, self.rds = config, rds

    @contextmanager
    def transaction(self):
        from psycopg.conninfo import make_conninfo
        c = self.config
        # Generate a fresh short-lived IAM token for every database connection.
        token = self.rds.generate_db_auth_token(DBHostname=c['database_host'], Port=5432,
                                                DBUsername=c['database_user'], Region=c['region'])
        dsn = make_conninfo(host=c['database_host'], port=5432, user=c['database_user'], password=token,
                            dbname=c['database_name'], sslmode='verify-full', sslrootcert=c['database_ca_file'])
        with PostgresStore(dsn).transaction() as db:
            yield db


def cloud_clients(c):
    import boto3
    from botocore.config import Config
    session = boto3.Session(region_name=c['region'])
    settings = Config(connect_timeout=5, read_timeout=15, retries={'total_max_attempts': 2, 'mode': 'standard'},
                      ignore_configured_endpoint_urls=True)
    return {name: session.client(name, config=settings) for name in ('s3', 'rds', 'cloudwatch')}


def publish_health(client, deployment, healthy):
    dimensions = [dict(Name='Deployment', Value=deployment), dict(Name='Service', Value='archive')]
    client.put_metric_data(Namespace='LARP/Runtime', MetricData=[
        dict(MetricName='Heartbeat', Value=1, Unit='Count', Dimensions=dimensions),
        dict(MetricName='Healthy', Value=int(healthy), Unit='Count', Dimensions=dimensions)])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'once', 'health', 'restore'))
    parser.add_argument('--config', required=True)
    parser.add_argument('--receipt')
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
            receipt = Document(Path(args.receipt).read_bytes())
            payload = Document(archive.fetch(receipt))
            target = PostgresStore(Path(args.target_dsn_file).read_text(encoding='utf-8').strip())
            # Migrations must already be applied with a provisioning role.
            restore(target, payload)
            print(json.dumps(dict(restored=True, quarantined=True, signing_enabled=False)))
            return 0
        worker = Maintenance(IamPostgresStore(c, clients['rds']), archive,
                             backup_interval_ms=c['backup_interval_hours'] * HOUR_MS,
                             max_attempts=c['max_attempts'], retry_ms=c['retry_seconds'] * 1000,
                             max_payload_bytes=c['max_archive_bytes'])
        now = int(time.time() * 1000)
        if args.command == 'once':
            worker.prepare(c['run_id'], now)
            # Per invocation bound; timer supplies subsequent delivery capacity.
            for _ in range(4):
                if not worker.once(c['run_id'], int(time.time() * 1000)):
                    break
        health = worker.health(c['run_id'], int(time.time() * 1000)).read()
        publish_health(clients['cloudwatch'], c['deployment'], health['healthy'])
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

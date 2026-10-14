"""Hosted database connections: a fresh short-lived RDS IAM token per connection over verified TLS.

Hosted SQL roles are IAM-only (`deploy/postgres/roles.sql` grants `rds_iam`), so a static DSN cannot log in for
longer than one token lifetime. No token or DSN is ever kept, logged or included in an error.
"""

from contextlib import contextmanager
import hashlib
from pathlib import Path

from larp.contracts import ContractError
from larp.storage.postgres import PostgresStore

IAM_SETTINGS = ('database_host', 'database_user', 'database_name', 'database_ca_file', 'database_ca_sha256', 'region')


def check_iam_settings(value: dict, user: str) -> None:
    """Refuse incomplete RDS IAM settings, another SQL role, or a CA bundle that differs from its pinned hash."""
    missing = [key for key in IAM_SETTINGS if value.get(key) is None or value.get(key) == '']
    if missing:
        raise ContractError('Missing database settings: ' + ','.join(missing))
    if value['database_user'] != user:
        raise ContractError(f'This service requires the dedicated {user} database role')
    if not Path(value['database_ca_file']).is_file():
        raise ContractError('Pinned RDS certificate bundle is missing')
    if hashlib.sha256(Path(value['database_ca_file']).read_bytes()).hexdigest() != value['database_ca_sha256']:
        raise ContractError('RDS certificate bundle hash differs from configuration')


def rds_client(region: str):
    import boto3
    from botocore.config import Config
    return boto3.Session(region_name=region).client('rds', config=Config(
        connect_timeout=5, read_timeout=15, retries={'total_max_attempts': 2, 'mode': 'standard'},
        ignore_configured_endpoint_urls=True))


class IamPostgresStore(PostgresStore):
    def __init__(self, config, rds):
        # Snapshot verification owns per-process checkpoints even though this
        # adapter generates its DSN afresh inside every transaction.
        super().__init__(None)
        self.config, self.rds = config, rds

    def __repr__(self):
        return f"IamPostgresStore({self.config['database_user']!r})"

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

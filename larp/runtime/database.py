"""Hosted database connections: a fresh short-lived RDS IAM token per connection over verified TLS.

Hosted SQL roles are IAM-only (`deploy/postgres/roles.sql` grants `rds_iam`), so a static DSN cannot log in for
longer than one token lifetime. The token is needed only to open a connection; an open connection is reused by later
transactions until it reaches the store's maximum age (IDEA-085), so a service logs in a few times an hour instead of
once per transaction. No token or DSN is ever kept, logged or included in an error.
"""

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


def check_database_settings(value: dict, user: str) -> None:
    """Exactly one connection: a local DSN file, or RDS IAM settings for `user` (hosted roles are IAM-only)."""
    dsn = value.get('database_dsn_file') not in (None, '')
    iam = any(value.get(key) not in (None, '') for key in IAM_SETTINGS if key != 'region')
    if dsn == iam:
        raise ContractError('Configure exactly one database connection: database_dsn_file or RDS IAM settings')
    if iam:
        check_iam_settings(value, user)


def open_service_store(config: dict):
    """The store for a configuration that passed check_database_settings."""
    if config.get('database_dsn_file'):
        return PostgresStore(Path(config['database_dsn_file']).read_text(encoding='utf-8').strip())
    return IamPostgresStore(config, rds_client(config['region']))


def rds_client(region: str):
    import boto3
    from botocore.config import Config
    return boto3.Session(region_name=region).client('rds', config=Config(
        connect_timeout=5, read_timeout=15, retries={'total_max_attempts': 2, 'mode': 'standard'},
        ignore_configured_endpoint_urls=True))


class IamPostgresStore(PostgresStore):
    # One IAM login per pooled connection, not per transaction (IDEA-085, SJ-06 J8 incident): thousands of logins an
    # hour exhausted a db.t4g.micro's memory and every service restart-looped.
    REUSE_CONNECTIONS = True

    def __init__(self, config, rds):
        # Snapshot verification owns per-process checkpoints; the DSN is built afresh for every new connection.
        super().__init__(None)
        self.config, self.rds = config, rds

    def __repr__(self):
        return f"IamPostgresStore({self.config['database_user']!r})"

    def _connect(self):
        import psycopg
        from psycopg.conninfo import make_conninfo
        c = self.config
        # A fresh short-lived IAM token for every new database connection; it is not kept after connecting.
        token = self.rds.generate_db_auth_token(DBHostname=c['database_host'], Port=5432,
                                                DBUsername=c['database_user'], Region=c['region'])
        return psycopg.connect(make_conninfo(host=c['database_host'], port=5432, user=c['database_user'],
                                             password=token, dbname=c['database_name'], sslmode='verify-full',
                                             sslrootcert=c['database_ca_file']), connect_timeout=5)

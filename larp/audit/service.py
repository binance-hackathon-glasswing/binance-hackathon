"""Uploader service on `primary` (IDEA-047 U01). Run by deploy/systemd/larp-uploader.service.

    python -m larp.audit.service check|run --config /etc/larp/uploader.json --manifest /etc/larp/release.json --root R

Delivers the round logs the coordinator committed (`audit_chunks`) to the ai-seeds receiver with `DeliveryWorker`.
It holds the audit secret only: `AI_SEEDS_SECRET` from the `uploader` Secrets Manager entry, never the environment,
and it refuses a secret that also carries a wallet key or the runtime's market-data keys (IDEA-042 S1-S3). It follows
the run's current owner epoch each cycle and keeps delivering while the run is quarantined: logs of a failed run
still have to reach the receiver (F-62). It never signs, trades or writes the run journal.

Exit codes: 0 clean stop; 1 failure (restart); 4 start refused.
"""

import argparse
import json
import math
from pathlib import Path
import re
import signal
import time

from larp.contracts import ContractError, Document

EXIT_REFUSED = 4
SCHEMA = 'UploaderService.v1'
SERVICE = 'uploader'
DATABASE_USER = 'larp_uploader'
ALLOWED_SECRETS = ('AI_SEEDS_SECRET', 'AI_SEEDS_ADDRESS')
_ADDRESS = re.compile(r'0x[0-9a-f]{40}')
_SECRET = re.compile(r'[0-9a-fA-F]{64}')


class StartRefused(ContractError):
    pass


def validate_config(value):
    if type(value) is not dict or value.get('schema') != SCHEMA:
        raise ContractError('Invalid uploader service configuration schema')
    missing = [k for k in ('run_id', 'build_id', 'mode', 'wallet_address', 'uploader_secret_id', 'region',
                           'interval_seconds') if value.get(k) in (None, '')]
    if missing:
        raise ContractError('Missing uploader settings: ' + ','.join(missing))
    if value['mode'] not in ('dev', 'live'):
        raise ContractError('Round logs upload only for dev or live runs')
    if type(value['wallet_address']) is not str or not _ADDRESS.fullmatch(value['wallet_address']):
        raise ContractError('Invalid wallet address')
    interval = value['interval_seconds']
    if type(interval) not in (int, float) or not math.isfinite(interval) or interval <= 0:
        raise ContractError('Invalid uploader interval')
    for key, default in (('max_attempts', 8), ('retry_ms', 30000), ('batch', 50)):
        if type(value.get(key, default)) is not int or value.get(key, default) < 1:
            raise ContractError('Invalid positive integer setting: ' + key)
    foreign = [k for k in value if (k.endswith('_secret_id') and k != 'uploader_secret_id')
               or 'private_key' in k or 'mnemonic' in k or k in ('key_file', 'key_credential')]
    if foreign:
        raise ContractError('Uploader configuration names another service secret: ' + ','.join(sorted(foreign)))
    from larp.runtime.database import check_database_settings
    check_database_settings(value, DATABASE_USER)
    return value


class Secret(str):
    """The audit secret; its repr never shows the value."""

    def __repr__(self):
        return 'Secret(AI_SEEDS_SECRET)'

    __str__ = __repr__


def load_uploader_secret(client, secret_id, wallet_address):
    try:
        raw = client.get_secret_value(SecretId=secret_id)['SecretString']
    except Exception as exc:  # the provider's message is not trusted to be value-free
        raise StartRefused('Uploader secret unavailable: ' + type(exc).__name__) from None
    try:
        values = json.loads(raw)
    except (TypeError, ValueError):
        raise StartRefused('Uploader secret is not a JSON object') from None
    if type(values) is not dict or not all(type(k) is str and type(v) is str for k, v in values.items()):
        raise StartRefused('Uploader secret must map names to strings')
    foreign = sorted(set(values) - set(ALLOWED_SECRETS))
    if foreign:
        raise StartRefused('Secret for another service present in the uploader secret: ' + ', '.join(foreign))
    if not _SECRET.fullmatch(values.get('AI_SEEDS_SECRET', '')):
        raise StartRefused('AI_SEEDS_SECRET missing or not 64 hex characters')
    if values.get('AI_SEEDS_ADDRESS', wallet_address).lower() != wallet_address:
        raise StartRefused('AI_SEEDS_ADDRESS differs from the configured wallet')
    return Secret(values['AI_SEEDS_SECRET'])


def secrets_client(region):
    import boto3
    from botocore.config import Config
    return boto3.Session(region_name=region).client('secretsmanager', config=Config(
        connect_timeout=5, read_timeout=15, retries={'total_max_attempts': 2, 'mode': 'standard'},
        ignore_configured_endpoint_urls=True))


class Uploader:
    def __init__(self, store, run_id, wallet, worker, *, batch=50):
        self.store, self.run_id, self.wallet, self.worker, self.batch = store, run_id, wallet, worker, batch

    def once(self, now_ms):
        """Deliver up to `batch` due chunks under the run's current epoch; returns how many were attempted."""
        from larp.storage.postgres import Conflict, PostgresStore
        with self.store.transaction() as db:
            run = PostgresStore._run(db, self.run_id, lock=False)
        if str(run['wallet_id']).lower() != self.wallet:
            raise StartRefused('Run wallet differs from the uploader configuration')
        attempted = 0
        try:
            while attempted < self.batch and self.worker.once(self.run_id, run['epoch'], now_ms):
                attempted += 1
        except Conflict:
            pass  # the owner changed mid-cycle: the next cycle resends the same bytes under the new epoch
        return attempted


def load_config(args):
    from larp.runtime.preflight import verify_release, verify_service_config
    try:
        raw = Path(args.config).read_bytes()
        config = validate_config(json.loads(raw))
        manifest = verify_release(Document(Path(args.manifest).read_bytes()), args.root)
        verify_service_config(manifest, SERVICE, raw)
        if manifest['build_id'] != config['build_id']:
            raise ContractError('Configured build differs from the verified release')
    except (ContractError, ValueError, OSError) as refused:
        raise StartRefused(type(refused).__name__) from None
    return config


def main(argv=None, *, client_factory=secrets_client, receiver_factory=None,
         clock_ms=lambda: time.time_ns() // 1_000_000, sleep=time.sleep, max_cycles=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'run'))
    parser.add_argument('--config', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--root', required=True)
    args = parser.parse_args(argv)
    try:
        config = load_config(args)
        if args.command == 'check':
            print(json.dumps(dict(configuration_valid=True, signing_enabled=False)))
            return 0
        secret = load_uploader_secret(client_factory(config['region']), config['uploader_secret_id'],
                                      config['wallet_address'])
        from larp.audit.delivery import DeliveryWorker, HttpReceiver
        from larp.runtime.database import open_service_store
        store = open_service_store(config)
        receiver = (receiver_factory or HttpReceiver)(config['wallet_address'], secret)
        uploader = Uploader(store, config['run_id'], config['wallet_address'],
                            DeliveryWorker(store, receiver, max_attempts=config.get('max_attempts', 8),
                                           retry_ms=config.get('retry_ms', 30000)),
                            batch=config.get('batch', 50))
        stopping = []
        signal.signal(signal.SIGTERM, lambda *a: stopping.append(True))
        print(json.dumps(dict(started=True, signing_enabled=False)))
        cycles = 0
        while not stopping and (max_cycles is None or cycles < max_cycles):
            if not uploader.once(clock_ms()):
                sleep(config['interval_seconds'])
            cycles += 1
        return 0
    except StartRefused as refused:
        # Refusal texts are fixed and name no secret value.
        print(json.dumps(dict(started=False, reason='START_REFUSED', detail=str(refused), signing_enabled=False)))
        return EXIT_REFUSED
    except Exception:
        print(json.dumps(dict(started=False, reason='UPLOADER_FAILED', signing_enabled=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

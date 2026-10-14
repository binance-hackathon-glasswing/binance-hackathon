"""Execution service process on `primary` (IDEA-047 E01). Run by deploy/systemd/larp-execution.service.

    python -m larp.execution_live.main check|run --config /etc/larp/execution.json --manifest /etc/larp/release.json --root R

The service will drive the W04 Executor through `ExecutionService` with the database-backed `RemoteSigner`
(larp/execution_live/signing.py): it never holds a wallet key, and a configuration that names one is refused. Until the
round driver lands (IDEA-042 item 10; `larp.runtime.service.build_driver`), `run` verifies the release, its pinned
configuration and the run binding, then exits 2 NOT_INTEGRATED, which systemd does not restart.

Exit codes as the runtime service: 0 clean stop; 1 failure; 2 not integrated; 4 start refused.
"""

import argparse
import json
import math
from pathlib import Path
import re

from larp.contracts import ContractError, Document

EXIT_NOT_INTEGRATED, EXIT_REFUSED = 2, 4
SCHEMA = 'ExecutionService.v1'
SERVICE = 'execution'
DATABASE_USER = 'larp_execution'
_ADDRESS = re.compile(r'0x[0-9a-f]{40}')


class StartRefused(ContractError):
    pass


class NotIntegrated(ContractError):
    pass


def validate_config(value):
    if type(value) is not dict or value.get('schema') != SCHEMA:
        raise ContractError('Invalid execution service configuration schema')
    missing = [k for k in ('run_id', 'build_id', 'mode', 'wallet_address', 'interval_seconds')
               if value.get(k) in (None, '')]
    if missing:
        raise ContractError('Missing execution settings: ' + ','.join(missing))
    if value['mode'] not in ('dev', 'live'):
        raise ContractError('The execution service runs only for dev or live runs')
    if type(value['wallet_address']) is not str or not _ADDRESS.fullmatch(value['wallet_address']):
        raise ContractError('Invalid wallet address')
    for key, default in (('interval_seconds', None), ('signer_timeout_seconds', 20)):
        number = value.get(key, default)
        if type(number) not in (int, float) or not math.isfinite(number) or number <= 0:
            raise ContractError('Invalid positive number setting: ' + key)
    # The wallet key lives only on the signer host (IDEA-046 B2, G-09).
    keyed = [k for k in value if 'private_key' in k or 'mnemonic' in k or k in ('key_file', 'key_credential')]
    if keyed:
        raise ContractError('Execution configuration names a wallet key: ' + ','.join(sorted(keyed)))
    from larp.runtime.database import check_database_settings
    check_database_settings(value, DATABASE_USER)
    return value


def build_execution(config, store):
    raise NotIntegrated('Execution needs the round driver (IDEA-042 item 10)')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'run'))
    parser.add_argument('--config', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--root', required=True)
    args = parser.parse_args(argv)
    try:
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
        if args.command == 'check':
            print(json.dumps(dict(configuration_valid=True, signing_enabled=False)))
            return 0
        from larp.runtime.database import open_service_store
        from larp.storage.postgres import PostgresStore
        store = open_service_store(config)
        with store.transaction() as db:
            run = PostgresStore._run(db, config['run_id'], lock=False)
        if run['mode'] != config['mode'] or str(run['wallet_id']).lower() != config['wallet_address']:
            raise StartRefused('run differs from the execution configuration')
        try:
            build_execution(config, store)
        except NotIntegrated:
            print(json.dumps(dict(started=False, reason='NOT_INTEGRATED', signing_enabled=False)))
            return EXIT_NOT_INTEGRATED
        return 0
    except StartRefused:
        print(json.dumps(dict(started=False, reason='START_REFUSED', signing_enabled=False)))
        return EXIT_REFUSED
    except Exception:
        print(json.dumps(dict(started=False, reason='EXECUTION_FAILED', signing_enabled=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

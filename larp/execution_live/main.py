"""Execution service process on `primary` (IDEA-047 E01). Run by deploy/systemd/larp-execution.service.

    python -m larp.execution_live.main check|run --config /etc/larp/execution.json --manifest /etc/larp/release.json --root R

The service drives the W04 Executor through `ExecutionService` and `ExecutionLoop` (larp/execution_live/loop.py) with
the database-backed `RemoteSigner` (larp/execution_live/signing.py): it never holds a wallet key, and a configuration
that names one is refused. `build_execution` composes the live ports (IDEA-050). The `Executor` accepts them only with
a swap decoder pinned to router evidence (`router_evidence_file` + `router_evidence_sha256`; IDEA-070, GAP-29).
Without that evidence `run` stops with exit 2 NOT_INTEGRATED and reason EXECUTOR_CAPABILITY_GATE, which systemd does
not restart.

Exit codes as the runtime service: 0 clean stop; 1 failure; 2 not integrated; 3 run quarantined; 4 start refused.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import signal
import time

from larp.contracts import ContractError, Document

EXIT_NOT_INTEGRATED, EXIT_QUARANTINED, EXIT_REFUSED = 2, 3, 4
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
    if type(value.get('native_trace', False)) is not bool:
        raise ContractError('native_trace must explicitly enable a qualified provider')
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


BUILD_KEYS = ('market_artifact_root', 'chain_artifact_root', 'rpc_url', 'rpc_source_id', 'router', 'token_decimals', 'max_gas', 'max_gas_price', 'gas_budget', 'strategy_profile_file',
              'strategy_profile_sha256')


def _pinned_json(path, sha256, what):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ContractError(what + ' differs from its pinned hash')
    return json.loads(raw)


def execution_mapping(config, profile, decimals, *, wallet):
    """`map_command` settings: profile limits, configured gas limits, and native settlement only when the RPC traces
    native transfers (`native_trace`), the one path that can settle a gas top-up's fill (#30, IDEA-061)."""
    return dict(wallet=wallet, version_id=config['build_id'], router=config['router'], token_decimals=decimals,
                limits=dict(per_trade_cap_units=profile['per_trade_cap_units'], slippage_bps=profile['slippage_bps'],
                            max_gas=config['max_gas'], max_gas_price=config['max_gas_price'],
                            gas_budget=config['gas_budget']),
                native_settlement=config.get('native_trace', False) is True)


def router_decoder(config):
    """The swap decoder: pinned to router evidence when configured (IDEA-070), else `UnverifiedRouter`, which keeps
    the Executor's capability gate closed (exit 2). Evidence for another router than the configured one is refused."""
    from larp.execution_live.router import evidence_settings, load_evidence
    from larp.execution_live.venue import UnverifiedRouter
    settings = evidence_settings(config)
    if settings is None:
        return UnverifiedRouter()
    decoder = load_evidence(*settings)
    if decoder.router != config['router']:
        raise ContractError('Router evidence is for another router than the configured one')
    return decoder


def build_execution(config, store, secrets, *, clock_s=None, manifest_sha256=None):
    """The execution loop over live ports (IDEA-050). Raises NotIntegrated at the Executor's capability gate.

    Mapping limits come from the pinned strategy profile (per-trade cap, slippage: #40, C-OPEN-001) and the configured
    gas limits; quotes request the profile slippage. A missing or inconsistent input is a ContractError (exit 4)."""
    from larp.execution import Blocked, Executor
    from larp.execution_live.chain import ChainEvidence, Rpc
    from larp.execution_live.guards import LiveGuards
    from larp.execution_live.loop import (ExecutionLoop, FencedRelease, PlanValuation, RoundTerminal,
                                         RunAuthorization, Web3Broadcaster)
    from larp.execution_live.service import ExecutionService
    from larp.execution_live.settlement import ReceiptFacts
    from larp.execution_live.signing import RemoteSigner
    from larp.execution_live.store import ExecutionStore
    from larp.execution_live.venue import LiveVenue
    from larp.marketdata.port import MarketPort, TOKENS
    from larp.marketdata.web3 import Artifacts, Web3Client
    clock_s = clock_s or (lambda: int(time.time()))
    missing = [k for k in BUILD_KEYS if config.get(k) in (None, '')]
    if missing:
        raise ContractError('Missing execution settings: ' + ','.join(missing))
    if not _ADDRESS.fullmatch(str(config['router'])):
        raise ContractError('Invalid router address')
    decimals = config['token_decimals']
    if type(decimals) is not dict or set(decimals) != set(TOKENS) or any(
            type(v) is not int or not 0 <= v <= 30 for v in decimals.values()):
        raise ContractError('token_decimals must give each bStock its decimals')
    for key in ('max_gas', 'max_gas_price', 'gas_budget'):
        if type(config[key]) is not int or config[key] <= 0:
            raise ContractError('Invalid positive integer setting: ' + key)
    profile = _pinned_json(config['strategy_profile_file'], config['strategy_profile_sha256'], 'Strategy profile')
    if type(profile) is not dict or profile.get('schema') != 'StrategyProfile.v1' or profile.get('mode') != 'LIVE':
        raise ContractError('Execution needs the run\'s LIVE StrategyProfile.v1')
    key, secret = secrets.get('BINANCE_API_KEY'), secrets.get('BINANCE_SECRET_KEY')
    if not key or not secret:
        raise ContractError('Quotes need the Web3 key pair')
    run_id, wallet = config['run_id'], config['wallet_address']
    registry = ExecutionStore(store, run_id=run_id, wallet=wallet)
    epoch, _ = registry.execution_authority()
    client = Web3Client(key, secret, artifacts=Artifacts(config['market_artifact_root']))
    chain = ChainEvidence(Rpc(config['rpc_url'], artifacts=Artifacts(config['chain_artifact_root']),
                              source_id=config['rpc_source_id'], native_trace=config.get('native_trace', False)))
    market = MarketPort(client, wallet, quote_limits=profile)
    guards = LiveGuards(store=registry, market=market, chain=chain,
                        authorization=RunAuthorization(store, run_id=run_id, build_id=config['build_id'],
                                                       manifest_sha256=manifest_sha256))
    decoder = router_decoder(config)
    venue = LiveVenue(client, chain, decoder=decoder,
                      release=FencedRelease(registry, Web3Broadcaster(
                          key, secret, wallet=wallet,
                          artifacts=str(Path(config['market_artifact_root']) / 'broadcast'))))
    signer = RemoteSigner(execution=registry, guards=guards, clock_s=clock_s,
                          timeout_s=config.get('signer_timeout_seconds', 20))
    try:
        executor = Executor(registry, guards, venue, signer, decoder)
    except Blocked:
        raise NotIntegrated('EXECUTOR_CAPABILITY_GATE') from None
    terminal = RoundTerminal(store, run_id=run_id)
    loop = ExecutionLoop(store=store, registry=registry, service=None, run_id=run_id, wallet=wallet, epoch=epoch)
    valuation = PlanValuation(store, registry, run_id=run_id)
    facts = ReceiptFacts(chain, wallet_id=wallet, valuation=valuation, bnb_decimals=valuation.bnb_decimals,
                         registry=registry, epoch=epoch, authority_version=epoch, round_terminal=terminal)
    mapping = execution_mapping(config, profile, decimals, wallet=wallet)
    loop.service = ExecutionService(store=store, executor=executor, mapping=mapping, observe=loop.publish,
                                    wallet_id=wallet, epoch=epoch, authority_version=epoch, settlement=facts,
                                    round_terminal=terminal)
    return loop


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
            manifest_document = Document(Path(args.manifest).read_bytes())
            manifest = verify_release(manifest_document, args.root)
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
        if run['quarantined']:
            print(json.dumps(dict(started=False, reason='QUARANTINED', signing_enabled=False)))
            return EXIT_QUARANTINED
        registered = Document(bytes(run['projection'])).read().get('registered_version')
        manifest_sha256 = hashlib.sha256(manifest_document.payload).hexdigest()
        if (type(registered) is not dict or registered.get('build_id') != config['build_id']
                or registered.get('manifest_sha256') != manifest_sha256):
            raise StartRefused('execution release differs from the registered manifest')
        from larp.runtime.credentials import runtime_secrets
        secrets = runtime_secrets(config)
        try:
            loop = build_execution(config, store, secrets, manifest_sha256=manifest_sha256)
        except NotIntegrated as gate:
            print(json.dumps(dict(started=False, reason='NOT_INTEGRATED', detail=str(gate), signing_enabled=False)))
            return EXIT_NOT_INTEGRATED
        except (ContractError, ValueError, OSError) as refused:
            raise StartRefused(type(refused).__name__) from None
        stopping = []
        signal.signal(signal.SIGTERM, lambda *a: stopping.append(True))
        while not stopping:
            loop.once(time.time_ns() // 1_000_000)
            if not stopping:
                time.sleep(config['interval_seconds'])
        return 0
    except StartRefused:
        print(json.dumps(dict(started=False, reason='START_REFUSED', signing_enabled=False)))
        return EXIT_REFUSED
    except Exception:
        print(json.dumps(dict(started=False, reason='EXECUTION_FAILED', signing_enabled=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

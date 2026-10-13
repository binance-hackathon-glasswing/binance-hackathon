"""Supervised runtime process (DR-13; IDEA-042 item 5). Run by deploy/systemd/larp-runtime.service.

One durable session per process. SIGTERM ends the session cleanly; a crash or kill leaves it open, so the next start
records a RESTART incident. Before every round the guard may HALT or quarantine the run. The process never changes
its build: the release preflight and the session check both refuse a build other than the registered one.

Exit codes the supervisor uses: 0 clean stop; 1 failure (restart); 2 not integrated yet; 3 run quarantined; 4 start
refused (live-start checks, configuration, release or session contract). 2, 3 and 4 do not restart
(`RestartPreventExitStatus`): none is cured by restarting (IDEA-042 V4).
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import signal
import time
import uuid

from larp.audit.protocol import ADDRESS
from larp.contracts import ContractError, Document
from larp.runtime.database import IAM_SETTINGS, check_iam_settings
from larp.runtime.live import LiveStartRefused, check_live_start
from larp.runtime.supervision import Guard, Sessions

EXIT_NOT_INTEGRATED, EXIT_QUARANTINED, EXIT_REFUSED = 2, 3, 4


class NotIntegrated(ContractError):
    """A configuration asks for a path that is not built yet: signing (Gate B) or a hosted model assessor (DR-11)."""


class StartRefused(ContractError):
    """A start that restarting the same build cannot cure: exit 4 (IDEA-042 V4)."""


class Service:
    def __init__(self, store, run_id, build_id, *, guard, driver, clock_ms, interval_s=5.0, sleep=time.sleep,
                 session_id=None, start_check=None):
        self.store, self.run_id, self.build_id = store, run_id, build_id
        self.guard, self.driver, self.clock, self.interval, self.sleep = guard, driver, clock_ms, interval_s, sleep
        self.session_id = session_id or 'session:' + uuid.uuid4().hex
        self.sessions = Sessions(store, run_id)
        self.stopping = False
        self.start_check = start_check  # live/dev refusals (larp/runtime/live.py), before any session opens

    def stop(self, *args):
        self.stopping = True

    def run(self, *, max_cycles=None):
        """Returns an exit code. An exception escapes on purpose: the session stays open and counts as a crash."""
        from larp.storage.postgres import Conflict, IntegrityError
        try:
            if self.start_check is not None:
                self.start_check()
            if self.store.metrics(self.run_id).read()['quarantined']:
                return EXIT_QUARANTINED  # e.g. after a restore: restarting cannot cure it, so systemd stops here
            self.sessions.begin(session_id=self.session_id, build_id=self.build_id, now_ms=self.clock())
        except (LiveStartRefused, Conflict, IntegrityError):
            raise  # reported on its own, or a storage outcome a later start may not repeat
        except ContractError as refused:
            raise StartRefused(str(refused)) from refused  # e.g. another build, a reused session ID
        cycles = 0
        while not self.stopping and (max_cycles is None or cycles < max_cycles):
            now = self.clock()
            if 'QUARANTINED:INTEGRITY' in self.guard.evaluate(now):
                return EXIT_QUARANTINED  # no clean end: the next start reports the stop as an incident
            self.driver.once(now)
            self.sessions.heartbeat(self.session_id, self.clock())
            cycles += 1
            if not self.stopping and (max_cycles is None or cycles < max_cycles):
                self.sleep(self.interval)
        self.sessions.end(self.session_id, self.clock())
        return 0


def validate_config(value):
    required = ('run_id', 'build_id', 'max_failures', 'clear_after', 'interval_seconds')
    if type(value) is not dict or value.get('schema') != 'RuntimeService.v1':
        raise ContractError('Invalid runtime service configuration schema')
    missing = [k for k in required if value.get(k) in (None, '')]
    if missing:
        raise ContractError('Missing runtime settings: ' + ','.join(missing))
    for key in ('max_failures', 'clear_after'):
        if type(value[key]) is not int or value[key] < 1:
            raise ContractError('Invalid positive integer setting: ' + key)
    interval = value['interval_seconds']
    if type(interval) not in (int, float) or not math.isfinite(interval) or interval <= 0:
        raise ContractError('Invalid runtime interval')
    if value.get('mode', 'offline') not in ('offline', 'paper', 'dev', 'live'):
        raise ContractError('Unknown runtime mode')
    # Exactly one connection: a local DSN file, or RDS IAM settings (hosted roles are IAM-only).
    # `region` alone also serves the secret store, so it does not select IAM.
    dsn = value.get('database_dsn_file') not in (None, '')
    iam = any(value.get(key) not in (None, '') for key in IAM_SETTINGS if key != 'region')
    if dsn == iam:
        raise ContractError('Configure exactly one database connection: database_dsn_file or RDS IAM settings')
    if iam:
        check_iam_settings(value, 'larp_runtime')
    return value


def open_store(config):
    if config.get('database_dsn_file'):
        from larp.storage.postgres import PostgresStore
        return PostgresStore(Path(config['database_dsn_file']).read_text(encoding='utf-8').strip())
    from larp.runtime.database import IamPostgresStore, rds_client
    return IamPostgresStore(config, rds_client(config['region']))


DRIVER_KEYS = ('signing', 'assessor', 'intelligence_mode', 'evidence_root', 'market_artifact_root', 'cadence_ms',
               'strategy_profile_file', 'strategy_profile_sha256', 'session_calendar_file', 'session_calendar_sha256',
               'issuers')


def _pinned_json(path, sha256, what):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ContractError(what + ' differs from its pinned hash')
    return json.loads(raw)


def build_driver(config, store, secrets, *, clock_ms=None):
    """The shadow round driver (IDEA-047) from the `driver` block of the manifest-bound runtime configuration.

    Signing (Gate B) and hosted model assessors (DR-11) are not integrated: asking for either raises NotIntegrated.
    Any other missing or inconsistent input is a ContractError, which `main` turns into a start refusal (exit 4)."""
    from larp.integration.runtime import ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state
    from larp.integration.settlement import ExecutionBridge
    from larp.intelligence.agent import EvidenceAssessor
    from larp.intelligence.config import load_config, load_registry
    from larp.intelligence.gate import lifecycle_policy_from
    from larp.intelligence.models import RuleBaselineModel
    from larp.intelligence.tools import PortEvidenceReader
    from larp.marketdata.port import MarketPort
    from larp.marketdata.web3 import Artifacts, Web3Client
    from larp.runtime.coordinator import Coordinator
    from larp.runtime.driver import EvidenceWork, RoundDriver, RuntimeHealth, SessionCalendar
    from larp.sources.store import FileArtifacts, SQLiteEvidenceStore
    clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
    d = config.get('driver')
    if type(d) is not dict:
        raise ContractError('Runtime configuration has no driver block')
    missing = [k for k in DRIVER_KEYS if d.get(k) in (None, '')]
    if missing:
        raise ContractError('Missing driver settings: ' + ','.join(missing))
    if d['signing'] is not False:
        raise NotIntegrated('Signing is not integrated (Gate B: DR-02/03/04)')
    if d['assessor'] != 'deterministic':
        raise NotIntegrated('Only the deterministic assessor is integrated (DR-11)')
    mode = config.get('mode', 'offline')
    profile = _pinned_json(d['strategy_profile_file'], d['strategy_profile_sha256'], 'Strategy profile')
    if type(profile) is not dict or profile.get('schema') != 'StrategyProfile.v1':
        raise ContractError('Expected a StrategyProfile.v1 file')
    if mode in ('dev', 'live') and profile.get('mode') != 'LIVE':
        raise ContractError('A dev or live run needs a LIVE strategy profile')
    calendar = SessionCalendar(_pinned_json(d['session_calendar_file'], d['session_calendar_sha256'],
                                            'Session calendar'))
    profile_hash = Document.from_dict(profile).digest('StrategyProfile.v1')
    intelligence = load_config(d['intelligence_mode'])
    registry = load_registry()
    issuers = d['issuers']
    if type(issuers) is not dict or not issuers:
        raise ContractError('Driver issuers must map issuer IDs to tokens')
    for issuer_id, meta in issuers.items():
        known = [e for e in registry.entries if e.issuer_id == issuer_id]
        if (not known or type(meta) is not dict or meta.get('token') != known[0].token
                or type(meta.get('underlying_id')) is not str or not meta['underlying_id']):
            raise ContractError('Driver issuer does not match the issuer registry: ' + issuer_id)
    if type(d['cadence_ms']) is not int:
        raise ContractError('Invalid cadence')
    root = Path(d['evidence_root'])
    if not (root / 'evidence.sqlite').is_file():
        raise ContractError('Evidence store missing; the ingestion process creates it')
    evidence = SQLiteEvidenceStore(str(root / 'evidence.sqlite'))
    artifacts = FileArtifacts(str(root / 'artifacts'))
    key, secret, wallet = secrets.get('BINANCE_API_KEY'), secrets.get('BINANCE_SECRET_KEY'), config.get('wallet_address')
    if not key or not secret or type(wallet) is not str or not ADDRESS.fullmatch(wallet):
        raise ContractError('Market data needs the Web3 key pair and the public wallet address')
    market = MarketPort(Web3Client(key, secret, artifacts=Artifacts(d['market_artifact_root'])), wallet)
    run = store.load(config['run_id']).read()
    lifecycle = lifecycle_policy_from(intelligence)
    builder = ContextBuilder(profile=profile, profile_hash=profile_hash, run_id=config['run_id'],
                             issuers={i: dict(token=m['token'], underlying_id=m['underlying_id'])
                                      for i, m in issuers.items()},
                             market=market, health=RuntimeHealth(store, config['run_id'], run['epoch']),
                             calendar=calendar, lifecycle_policy=lifecycle)
    assessor = EvidenceAssessor(registry=registry, reader=PortEvidenceReader(evidence, artifacts),
                                model=RuleBaselineModel(clock_ms), config=intelligence, clock_ms=clock_ms)
    coordinator = Coordinator(store, assessor, StrategyPolicy(),
                              RuntimePlanner(job_validity_ms=intelligence.p('job_validity_ms'),
                                             job_max_attempts=intelligence.p('job_max_attempts')),
                              execution=ExecutionBridge(), run_id=config['run_id'], version_id=config['build_id'],
                              profile_hash=profile_hash, address=wallet, context_builder=builder,
                              initial_policy_state=initial_policy_state(config['run_id'], profile), clock_ms=clock_ms,
                              test_rounds=mode != 'live', require_version=True)
    work = EvidenceWork(store=store, evidence_store=evidence, run_id=config['run_id'], config=intelligence,
                        issuers=list(issuers), profile_hash=profile_hash, cadence_ms=d['cadence_ms'],
                        lifecycle_policy=lifecycle)
    return RoundDriver(coordinator, work, ports=dict(market=market, assessor=assessor, evidence=evidence))


def verify_registered_manifest(store, config, manifest):
    """Bind the local release to the journaled authority, including configuration."""
    run = store.verified_snapshot(config['run_id'])
    if run['mode'] != config.get('mode', 'offline'):
        raise StartRefused('Configured mode differs from the registered run')
    registered = Document(bytes(run['projection'])).read().get('registered_version')
    if not registered:
        if run['mode'] in ('dev', 'live'):
            raise StartRefused('Live run requires prior version registration')
        return
    if (registered.get('build_id') != config['build_id']
            or registered.get('manifest_sha256') != hashlib.sha256(manifest.payload).hexdigest()):
        raise StartRefused('Release differs from the registered manifest')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'run'))
    parser.add_argument('--config', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--root', required=True)
    args = parser.parse_args(argv)
    try:
        from larp.runtime.preflight import verify_release, verify_runtime_config
        try:
            raw_config = Path(args.config).read_bytes()
            c = validate_config(json.loads(raw_config))
            manifest_document = Document(Path(args.manifest).read_bytes())
            manifest = verify_release(manifest_document, args.root)
            verify_runtime_config(manifest, raw_config)
            if manifest['build_id'] != c['build_id']:
                raise ContractError('Configured build differs from the verified release')
        except (ContractError, ValueError, OSError) as refused:
            raise StartRefused(type(refused).__name__) from None
        if args.command == 'check':
            print(json.dumps(dict(configuration_valid=True, signing_enabled=False)))
            return 0
        store = open_store(c)
        verify_registered_manifest(store, c, manifest_document)
        # Secrets only from the configured Secrets Manager entry, never the environment (IDEA-042 S2).
        from larp.runtime.credentials import runtime_secrets
        secrets = runtime_secrets(c)
        try:
            driver = build_driver(c, store, secrets)
        except NotIntegrated:
            print(json.dumps(dict(started=False, reason='NOT_INTEGRATED', signing_enabled=False)))
            return EXIT_NOT_INTEGRATED
        except (ContractError, ValueError, OSError) as refused:
            raise StartRefused(type(refused).__name__) from None  # restarting the same inputs cannot cure it
        def start_check():
            check_live_start(mode=c.get('mode', 'offline'), ports=getattr(driver, 'ports', {}), secrets=secrets,
                             wallet_address=c.get('wallet_address'), run_wallet=store.load(c['run_id']).read()['wallet_id'],
                             ai_seeds_dir=c.get('ai_seeds_dir'), nonce_dir=c.get('nonce_dir'))
        service = Service(store, c['run_id'], c['build_id'], driver=driver,
                          guard=Guard(store, c['run_id'], max_failures=c['max_failures'], clear_after=c['clear_after']),
                          clock_ms=lambda: time.time_ns() // 1_000_000, interval_s=c['interval_seconds'],
                          start_check=start_check)
        signal.signal(signal.SIGTERM, service.stop)
        return service.run()
    except LiveStartRefused as refused:
        # The reason names the failed check, never a secret value (larp/runtime/live.py).
        print(json.dumps(dict(started=False, reason='LIVE_START_REFUSED', detail=str(refused), signing_enabled=False)))
        return EXIT_REFUSED
    except StartRefused:
        # Configuration, release or session refusal: restarting the same files cannot cure it. The text may name
        # paths, so it is not printed.
        print(json.dumps(dict(started=False, reason='START_REFUSED', signing_enabled=False)))
        return EXIT_REFUSED
    except Exception:
        # Exception text can carry DSNs or secrets; the journal and health check hold the detail.
        print(json.dumps(dict(started=False, reason='RUNTIME_FAILED', signing_enabled=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Supervised runtime process (DR-13; IDEA-042 item 5). Run by deploy/systemd/larp-runtime.service.

One durable session per process. SIGTERM ends the session cleanly; a crash or kill leaves it open, so the next start
records a RESTART incident. Before every round the guard may HALT or quarantine the run. The process never changes
its build: the release preflight and the session check both refuse a build other than the registered one.

Operator commands (not run by systemd): `init` creates the configured dev/live run, quarantined, from a pinned
starting state; `activate --reviewer NAME --review-ref REF` is the reviewed step that lifts its quarantine, registers
the running build and journals who reviewed it (IDEA-050).

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
    """A configuration asks for an assessor that is not integrated (DR-11)."""


class StartRefused(ContractError):
    """A start that restarting the same build cannot cure: exit 4 (IDEA-042 V4)."""


class Service:
    def __init__(self, store, run_id, build_id, *, guard, driver, clock_ms, interval_s=5.0, sleep=time.sleep,
                 session_id=None, start_check=None, cycle_timeout_s=None, on_hang=None):
        self.store, self.run_id, self.build_id = store, run_id, build_id
        self.guard, self.driver, self.clock, self.interval, self.sleep = guard, driver, clock_ms, interval_s, sleep
        self.session_id = session_id or 'session:' + uuid.uuid4().hex
        self.sessions = Sessions(store, run_id)
        self.stopping = False
        self.start_check = start_check  # live/dev refusals (larp/runtime/live.py), before any session opens
        # A cycle longer than this ends the process for a supervised restart (larp/runtime/watchdog.py, #35).
        self.watchdog = None
        if cycle_timeout_s is not None:
            from larp.runtime.watchdog import Watchdog
            self.watchdog = Watchdog(cycle_timeout_s, **({} if on_hang is None else dict(on_hang=on_hang)))

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
        if self.watchdog is not None:
            self.watchdog.start()
        try:
            while not self.stopping and (max_cycles is None or cycles < max_cycles):
                if self.watchdog is not None:
                    self.watchdog.begin()
                now = self.clock()
                if 'QUARANTINED:INTEGRITY' in self.guard.evaluate(now):
                    return EXIT_QUARANTINED  # no clean end: the next start reports the stop as an incident
                self.driver.once(now)
                self.sessions.heartbeat(self.session_id, self.clock())
                if self.watchdog is not None:
                    self.watchdog.end()
                cycles += 1
                if not self.stopping and (max_cycles is None or cycles < max_cycles):
                    self.sleep(self.interval)
        finally:
            if self.watchdog is not None:
                self.watchdog.stop()
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
    # D-DN-04 (IDEA-049-D LD13): optional, no default; Isaac decides the value from measured dispatch/ACK delays.
    age = value.get('delivery_age_halt_seconds')
    if age is not None and (type(age) is not int or age < 1):
        raise ContractError('Invalid positive integer setting: delivery_age_halt_seconds')
    interval = value['interval_seconds']
    if type(interval) not in (int, float) or not math.isfinite(interval) or interval <= 0:
        raise ContractError('Invalid runtime interval')
    if value.get('mode', 'offline') not in ('offline', 'paper', 'dev', 'live'):
        raise ContractError('Unknown runtime mode')
    # A hosted run needs the hung-cycle watchdog (#35): without it a stuck cycle is never restarted.
    timeout = value.get('cycle_timeout_seconds')
    if timeout is not None or value.get('mode', 'offline') in ('dev', 'live'):
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ContractError('Invalid or missing cycle_timeout_seconds')
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


DRIVER_KEYS = ('execution', 'assessor', 'intelligence_mode', 'evidence_root', 'market_artifact_root', 'cadence_ms',
               'strategy_profile_file', 'strategy_profile_sha256', 'session_calendar_file', 'session_calendar_sha256',
               'issuers')
OPTIONAL_DRIVER_INTEGERS = ('expiry_grace_ms', 'day_roll_window_ms', 'max_quote_rounds', 'max_quote_requests',
                            'balance_check_interval_ms', 'balance_check_max_age_ms', 'price_jump_check_bps')
# IDEA-055 (#36): chain-balance reconciliation. Required in dev and live; account-specific, never committed.
# `price_jump_check_bps` is the price-jump guard's threshold (IDEA-055 PR 4); its hold lasts the maximum age.
# The RPC is `balance_rpc_providers`, an ordered list of {url, source_id} tried in turn (PR 5), or the legacy single
# provider `balance_rpc_url` + `balance_rpc_source_id`.
BALANCE_KEYS = ('balance_check_interval_ms', 'balance_check_max_age_ms', 'price_jump_check_bps')
LEGACY_RPC_KEYS = ('balance_rpc_url', 'balance_rpc_source_id')
MAX_BALANCE_PROVIDERS = 4


def balance_providers(d):
    """[{url, source_id}] in order from either form, or None when neither form is named."""
    listed = d.get('balance_rpc_providers')
    legacy = [k for k in LEGACY_RPC_KEYS if d.get(k) not in (None, '')]
    if listed is not None and legacy:
        raise ContractError('Name balance_rpc_providers or the legacy balance_rpc_url pair, not both')
    if listed is None:
        if not legacy:
            return None
        listed = [dict(url=d.get('balance_rpc_url'), source_id=d.get('balance_rpc_source_id'))]
    if type(listed) is not list or not 0 < len(listed) <= MAX_BALANCE_PROVIDERS:
        raise ContractError(f'balance_rpc_providers must list 1 to {MAX_BALANCE_PROVIDERS} providers')
    for p in listed:
        if (type(p) is not dict or set(p) != {'url', 'source_id'} or type(p['url']) is not str
                or not p['url'].startswith('https://') or type(p['source_id']) is not str or not p['source_id']):
            raise ContractError('Each balance RPC provider needs an HTTPS url and a source_id')
    if len({p['source_id'] for p in listed}) != len(listed):
        raise ContractError('Balance RPC source IDs must be unique')
    return [dict(url=p['url'], source_id=p['source_id']) for p in listed]


def balance_settings(d, mode):
    """The balance-check settings of a driver block, or None for an offline/paper run that names none of them."""
    present = [k for k in BALANCE_KEYS if d.get(k) not in (None, '')]
    named = d.get('balance_rpc_providers') is not None or any(d.get(k) not in (None, '') for k in LEGACY_RPC_KEYS)
    if not present and not named and mode not in ('dev', 'live'):
        return None
    missing = [k for k in BALANCE_KEYS if k not in present] + ([] if named else ['balance_rpc_providers'])
    if missing:
        raise ContractError('Missing balance-check settings: ' + ','.join(missing))
    providers = balance_providers(d)
    interval, max_age = d['balance_check_interval_ms'], d['balance_check_max_age_ms']
    if type(interval) is not int or type(max_age) is not int or not 0 < interval <= max_age:
        raise ContractError('Invalid balance-check interval or maximum age')
    jump = d['price_jump_check_bps']
    if type(jump) is not int or not 0 < jump <= 10_000:
        raise ContractError('Invalid price-jump threshold')
    return dict(providers=providers, interval_ms=interval, max_age_ms=max_age, price_jump_bps=jump)


def _pinned_json(path, sha256, what):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ContractError(what + ' differs from its pinned hash')
    return json.loads(raw)


def quote_verifier(d, profile, *, wallet, rpcs, projection):
    """The market port's quote verifier (IDEA-088, SJ-11-QV01), or None when the driver block names no
    `untrusted_router_policy_file` / `_sha256` pair; without one every quote stays CAPABILITY_PROOF_REQUIRED.

    The policy is the signer's own UntrustedRouterPolicy.v1 (IDEA-070 B02-U, DEV-23), loaded by its pinned hash and
    bound to the balance RPC providers for the live router preflight. A missing input refuses the start."""
    from larp.execution_live.config import untrusted_router_settings
    settings = untrusted_router_settings(d)
    if settings is None:
        return None
    if not rpcs:
        raise ContractError('The untrusted-router quote verifier needs balance_rpc_providers for its preflight')
    from larp.execution_live.untrusted_router import load_policy
    from larp.marketdata.quote_verifier import ProviderRpc, UntrustedQuoteVerifier
    scale = (projection.get('portfolio') or {}).get('bnb_decimals')
    return UntrustedQuoteVerifier(load_policy(*settings).bind(ProviderRpc(rpcs)), profile, wallet=wallet,
                                  bnb_decimals=scale)


def build_driver(config, store, secrets, *, clock_ms=None):
    """The round driver (IDEA-048, IDEA-050) from the `driver` block of the manifest-bound runtime configuration.

    `execution: "shadow"` ends every intent unsigned; `execution: "service"` hands committed commands to the execution
    service (larp/execution_live/loop.py) and journals its observations. AIand/OpenAI routing is integrated for
    shadow use or explicitly reviewed service/live use through a bounded background lane. Missing or inconsistent input is a ContractError, which
    `main` turns into a start refusal (exit 4)."""
    from larp.integration.runtime import ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state
    from larp.integration.settlement import ExecutionBridge
    from larp.intelligence.agent import EvidenceAssessor
    from larp.intelligence.config import load_config, load_registry
    from larp.intelligence.gate import lifecycle_policy_from
    from larp.intelligence.models import RuleBaselineModel
    from larp.intelligence.tools import PortEvidenceReader
    from larp.marketdata.port import MarketPort, NativeGasQuotePort
    from larp.marketdata.web3 import Artifacts, Web3Client
    from larp.runtime.coordinator import Coordinator
    from larp.runtime.driver import (BalanceCheck, DayRoll, EvidenceWork, MarketFeed, RoundDriver, RuntimeHealth,
                                     ServiceExecution, SessionCalendar, ShadowExecution)
    from larp.sources.store import FileArtifacts, SQLiteEvidenceStore
    clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
    d = config.get('driver')
    if type(d) is not dict:
        raise ContractError('Runtime configuration has no driver block')
    missing = [k for k in DRIVER_KEYS if d.get(k) in (None, '')]
    if missing:
        raise ContractError('Missing driver settings: ' + ','.join(missing))
    if 'signing' in d:
        raise ContractError('The driver block names `execution`, not `signing` (IDEA-050)')
    if d['execution'] not in ('shadow', 'service'):
        raise ContractError('Driver execution must be shadow or service')
    for key in OPTIONAL_DRIVER_INTEGERS:
        if key in d and (type(d[key]) is not int or d[key] < 0):
            raise ContractError('Invalid driver setting: ' + key)
    if d['execution'] == 'service' and 'expiry_grace_ms' not in d:
        raise ContractError('Service execution needs expiry_grace_ms')
    if d['assessor'] not in ('deterministic', 'aiand_routed'):
        raise NotIntegrated('Supported assessors are deterministic and aiand_routed (DR-11)')
    signed_model = d['assessor'] == 'aiand_routed' and (d['execution'] == 'service' or config.get('mode') == 'live')
    if signed_model and (d['execution'] != 'service' or type(d.get('model_adoption_ref')) is not str
                         or not d['model_adoption_ref'].strip()):
        raise ContractError('Signed routed assessments need service execution and a reviewed model_adoption_ref')
    if d['assessor'] == 'aiand_routed' and any(type(d.get(k)) is not str or not d[k].strip() for k in (
            'model_routing_file', 'model_routing_sha256', 'model_budget_root')):
        raise ContractError('AIand routing needs a pinned file and shared model budget root')
    mode = config.get('mode', 'offline')
    if d['intelligence_mode'] == 'shadow' and (mode != 'dev' or d['execution'] != 'shadow'):
        raise ContractError('Shadow evidence settings require an unsigned dev run')
    if mode in ('dev', 'live') and d['intelligence_mode'] != 'live' and not (
            mode == 'dev' and d['execution'] == 'shadow' and d['intelligence_mode'] == 'shadow'):
        raise ContractError('Hosted runs require live settings or explicit dev-shadow settings')
    profile = _pinned_json(d['strategy_profile_file'], d['strategy_profile_sha256'], 'Strategy profile')
    if type(profile) is not dict or profile.get('schema') != 'StrategyProfile.v1':
        raise ContractError('Expected a StrategyProfile.v1 file')
    if mode in ('dev', 'live') and profile.get('mode') != 'LIVE':
        raise ContractError('A dev or live run needs a LIVE strategy profile')
    from larp.strategy.execution_bounds import require_open_state_scope
    require_open_state_scope(profile, mode)  # IDEA-089 S2-1: weekend hours only in a dev SHADOW REHEARSAL
    if signed_model and mode in ('dev', 'live'):
        from larp.strategy.profiles import validate_live
        validate_live(profile)
        if profile.get('environment') != ('FINAL' if mode == 'live' else 'REHEARSAL'):
            raise ContractError('Signed model profile environment differs from the run')
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
    # The evidence poller owns the store; the runtime only reads it (IDEA-047 R3).
    evidence = SQLiteEvidenceStore(str(root / 'evidence.sqlite'), read_only=True)
    artifacts = FileArtifacts(str(root / 'artifacts'))
    key, secret, wallet = secrets.get('BINANCE_API_KEY'), secrets.get('BINANCE_SECRET_KEY'), config.get('wallet_address')
    if not key or not secret or type(wallet) is not str or not ADDRESS.fullmatch(wallet):
        raise ContractError('Market data needs the Web3 key pair and the public wallet address')
    client = Web3Client(key, secret, artifacts=Artifacts(d['market_artifact_root']))
    # Quotes request the profile's own slippage limit and pass its consumer check (PR #41, #40). The basis check uses
    # the token -> underlying tickers this run pinned and the check above bound to the issuer registry (IDEA-086).
    from larp.marketdata.basis import BasisVerifier
    run = store.load(config['run_id']).read()
    balance = balance_settings(d, mode)  # refuses a dev/live start without them, before any port makes a request
    rpcs = None
    if balance is not None:
        from larp.execution_live.chain import Rpc
        chain = Artifacts(str(Path(d['market_artifact_root']) / 'chain'))
        rpcs = [Rpc(p['url'], artifacts=chain, source_id=p['source_id']) for p in balance['providers']]
    market = MarketPort(client, wallet, quote_limits=profile, basis_verifier=BasisVerifier(
        {meta['token']: meta['underlying_id'] for meta in issuers.values()}),
        quote_verifier=quote_verifier(d, profile, wallet=wallet, rpcs=rpcs, projection=run['projection']))
    gas = None
    if 'gas_floor_bnb_units' in profile:
        gas = NativeGasQuotePort(client, wallet, quote_limits=profile, pay_units=profile['gas_top_up_cash_units'],
                                 receive_decimals=run['projection']['portfolio']['bnb_decimals'])
    feed = MarketFeed(market, gas=gas)
    lifecycle = lifecycle_policy_from(intelligence)
    # One registry-validated issuer map for evidence contexts and review jobs (#25).
    issuer_map = {i: dict(token=m['token'], underlying_id=m['underlying_id']) for i, m in issuers.items()}
    health = RuntimeHealth(store, config['run_id'], run['epoch'])
    builder = ContextBuilder(profile=profile, profile_hash=profile_hash, run_id=config['run_id'], issuers=issuer_map,
                             market=feed, health=health,
                             calendar=calendar, lifecycle_policy=lifecycle,
                             gas_quotes=feed.gas_quotes if gas is not None else None)
    from larp.sources.store import OverlayArtifacts
    # The runtime has no writable evidence mount on the host (IDEA-047 R15): artifacts it produces itself (tool
    # results; for the routed path also model request/reply bytes and stage results) go to a private store in the
    # unit's state directory; evidence is read as before (IDEA-057 SG-1, SG-7).
    model_artifacts = FileArtifacts(str(Path(d['market_artifact_root']) / 'model'))
    reader = PortEvidenceReader(evidence, OverlayArtifacts(artifacts, model_artifacts))
    if d['assessor'] == 'aiand_routed':
        from larp.intelligence.routing import build_routed_assessor
        spec = _pinned_json(d['model_routing_file'], d['model_routing_sha256'], 'Model routing')
        if spec.get('openai_trial') is not None and (d['execution'] != 'shadow' or config['mode'] != 'dev'):
            raise ContractError('Unsigned trial routing requires dev/shadow runtime')
        assessor = build_routed_assessor(spec, registry=registry, reader=reader, config=intelligence,
            clock_ms=clock_ms, artifacts=model_artifacts, secrets=secrets, budget_root=d['model_budget_root'])
    else:
        assessor = EvidenceAssessor(registry=registry, reader=reader,
                                    model=RuleBaselineModel(clock_ms), config=intelligence, clock_ms=clock_ms)
    coordinator = Coordinator(store, assessor, StrategyPolicy(),
                              RuntimePlanner(job_validity_ms=intelligence.p('job_validity_ms'),
                                             job_max_attempts=intelligence.p('job_max_attempts'), issuers=issuer_map),
                              execution=ExecutionBridge(), run_id=config['run_id'], version_id=config['build_id'],
                              profile_hash=profile_hash, address=wallet, context_builder=builder,
                              initial_policy_state=initial_policy_state(config['run_id'], profile), clock_ms=clock_ms,
                              test_rounds=mode != 'live', require_version=True)
    work = EvidenceWork(store=store, evidence_store=evidence, run_id=config['run_id'], config=intelligence,
                        issuers=list(issuers), profile_hash=profile_hash, cadence_ms=d['cadence_ms'],
                        lifecycle_policy=lifecycle)
    execution = (ServiceExecution(coordinator, wallet=wallet, grace_ms=d['expiry_grace_ms'])
                 if d['execution'] == 'service' else ShadowExecution(coordinator))
    day_roll = DayRoll(coordinator, window_ms=d['day_roll_window_ms']) if d.get('day_roll_window_ms') else None
    balance_check = None
    if balance is not None:
        from larp.execution_live.balances import BalanceProviders, DecimalsCache
        # Primary first, then backups; a check fails only when every provider fails (IDEA-055 PR 5).
        read = BalanceProviders(rpcs, wallet=wallet, decimals=DecimalsCache(),
                                min_block=lambda: store.load(config['run_id']).read()['projection'].get('settled_block'))
        balance_check = BalanceCheck(coordinator, read, interval_ms=balance['interval_ms'],
                                     max_age_ms=balance['max_age_ms'])
        health.balances = balance_check
        builder.price_jump = dict(bps=balance['price_jump_bps'], hold_ms=balance['max_age_ms'])  # IDEA-055 PR 4
    deferred = None
    if signed_model:
        from larp.runtime.deferred_models import DeferredAssessments
        deferred = DeferredAssessments(assessor, root=Path(d['market_artifact_root']) / 'model' / 'assessments',
                                       run_id=config['run_id'], build_id=config['build_id'], profile_hash=profile_hash)
    from larp.strategy.schema import initial_gas_only
    from larp.runtime.gas import InitialGasCheck, RetiredGasCheck
    gas_check = (InitialGasCheck if initial_gas_only(profile) else RetiredGasCheck)(coordinator, profile)
    return RoundDriver(coordinator, work, ports=dict(market=market, assessor=assessor, evidence=evidence),
                       execution=execution, market=feed, day_roll=day_roll, balance_check=balance_check,
                       assessments=deferred, gas_check=gas_check,
                       max_quote_rounds=d.get('max_quote_rounds', 0), max_quote_requests=d.get('max_quote_requests', 2))


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


def init_run(config, store):
    """Create the configured dev/live run, quarantined, from the PortfolioState.v1 file pinned in the configuration.

    Its starting balances are the operator's attested wallet state; the run stays quarantined until `activate_run`."""
    from larp.integration.runtime import initial_projection
    from larp.storage.postgres import Conflict, IntegrityError, doc
    mode = config.get('mode', 'offline')
    if mode not in ('dev', 'live'):
        raise StartRefused('init creates dev or live runs; offline runs are fixtures')
    if not config.get('initial_state_file') or not config.get('initial_state_sha256'):
        raise StartRefused('init needs initial_state_file and initial_state_sha256')
    try:
        ledger = _pinned_json(config['initial_state_file'], config['initial_state_sha256'], 'Initial state')
    except (ContractError, ValueError, OSError) as refused:
        raise StartRefused(type(refused).__name__) from None
    wallet = config.get('wallet_address')
    if (type(ledger) is not dict or ledger.get('schema') != 'PortfolioState.v1' or ledger.get('run_id') != config['run_id']
            or ledger.get('wallet_id') != wallet or type(wallet) is not str or not ADDRESS.fullmatch(wallet)):
        raise StartRefused('Initial state must be a PortfolioState.v1 for this run and wallet')
    try:
        store.load(config['run_id'])
    except Conflict:
        pass
    else:
        raise StartRefused('Run already exists')
    projection = initial_projection(ledger)
    try:
        store.initialize(config['run_id'], wallet, 56, doc(projection), mode=mode)
    except IntegrityError:
        raise StartRefused('Another run already uses this wallet on chain 56') from None
    return dict(initialized=True, run_id=config['run_id'], mode=mode, quarantined=True)


def activate_run(config, store, manifest, *, reviewer, review_ref, now_ms):
    """The reviewed step that authorizes a dev/live run (IDEA-050): lift quarantine, register the running build if no
    version is registered, and journal who reviewed it. Run by a person before the scored run, and after a restore.

    A different registered build is refused (never-do #5). A crash after the quarantine is lifted is finished by
    running the same command again."""
    from larp.runtime.coordinator import Coordinator, batch_for
    from larp.storage.postgres import Conflict, IntegrityError
    for name, value in (('reviewer', reviewer), ('review reference', review_ref)):
        if type(value) is not str or not value.strip() or len(value) > 200:
            raise StartRefused('Activation needs a ' + name)
    run_id = config['run_id']
    run = store.load(run_id).read()
    if run['mode'] != config.get('mode', 'offline') or run['mode'] not in ('dev', 'live'):
        raise StartRefused('Configured mode differs from the run, or the run is not dev/live')
    if run['wallet_id'] != config.get('wallet_address'):
        raise StartRefused('Configured wallet differs from the run')
    if run['mode'] == 'live':
        # The final build runs unchanged for the whole scored run (F-117), so its declared deviations must be final
        # before it is activated: no OPEN decision and no DRAFT row (G-11; plan.md §6.5; IDEA-049 D-FND-010).
        register = manifest.read().get('release_register') or {}
        if register.get('open_deviations') != [] or register.get('draft_deviations') != []:
            raise StartRefused('Final activation needs a final deviations register: no OPEN or DRAFT rows')
    registered = run['projection'].get('registered_version')
    manifest_sha = hashlib.sha256(manifest.payload).hexdigest()
    if registered and (registered.get('build_id') != config['build_id']
                       or registered.get('manifest_sha256') != manifest_sha):
        raise StartRefused('Another build is registered for this run')
    try:
        epoch = store.activate(run_id, run['epoch']) if run['quarantined'] else run['epoch']
    except (Conflict, IntegrityError) as refused:
        raise StartRefused(str(refused)) from None
    if store.receipt(run_id, f'activate:{epoch}') is not None:
        raise StartRefused('Run is already active')
    coordinator = Coordinator(store, None, None, None, execution=None, run_id=run_id, version_id=config['build_id'],
                              profile_hash='', address=config.get('wallet_address'))
    if not registered:
        coordinator.register_version(manifest, now_ms)
    current = store.load(run_id)
    event = dict(kind='RUN_ACTIVATED', epoch=epoch, build_id=config['build_id'], manifest_sha256=manifest_sha,
                 reviewer=reviewer.strip(), review_ref=review_ref.strip(), at_ms=now_ms)
    store.commit(batch_for(current, f'activate:{epoch}', event))
    return dict(activated=True, run_id=run_id, epoch=epoch, signing_enabled=False)


def runtime_guard(store, c):
    """The supervised runtime's HALT guard, with the kernel clock signal for the D-DN-10 automatic CLOCK clear."""
    from larp.runtime.supervision import CLOCK_CLEAR_AFTER_MS, kernel_clock_synchronized
    age = c.get('delivery_age_halt_seconds')
    return Guard(store, c['run_id'], max_failures=c['max_failures'], clear_after=c['clear_after'],
                 clock_sync=kernel_clock_synchronized, clock_clear_after_ms=CLOCK_CLEAR_AFTER_MS,
                 delivery_age_ms=None if age is None else age * 1000)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'run', 'init', 'activate'))
    parser.add_argument('--config', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--reviewer', help='activate: the person who reviewed the run')
    parser.add_argument('--review-ref', help='activate: where the review is recorded (ledger ID, issue or commit)')
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
        if args.command == 'init':
            print(json.dumps(init_run(c, store)))
            return 0
        if args.command == 'activate':
            print(json.dumps(activate_run(c, store, manifest_document, reviewer=args.reviewer,
                                          review_ref=args.review_ref, now_ms=time.time_ns() // 1_000_000)))
            return 0
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
                          guard=runtime_guard(store, c),
                          clock_ms=lambda: time.time_ns() // 1_000_000, interval_s=c['interval_seconds'],
                          start_check=start_check, cycle_timeout_s=c.get('cycle_timeout_seconds'))
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

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

from larp.contracts import ContractError, Document
from larp.runtime.live import LiveStartRefused, check_live_start
from larp.runtime.supervision import Guard, Sessions

EXIT_NOT_INTEGRATED, EXIT_QUARANTINED, EXIT_REFUSED = 2, 3, 4


class NotIntegrated(ContractError):
    """The round driver (scheduler -> coordinator with live ports) arrives with IDEA-042 item 10."""


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
    required = ('run_id', 'build_id', 'database_dsn_file', 'max_failures', 'clear_after', 'interval_seconds')
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
    return value


def build_driver(config, store, secrets):
    raise NotIntegrated('Round driver not integrated yet (IDEA-042 item 10)')


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
        from larp.storage.postgres import PostgresStore
        store = PostgresStore(Path(c['database_dsn_file']).read_text(encoding='utf-8').strip())
        verify_registered_manifest(store, c, manifest_document)
        # Secrets only from the configured Secrets Manager entry, never the environment (IDEA-042 S2).
        from larp.runtime.credentials import runtime_secrets
        secrets = runtime_secrets(c)
        try:
            driver = build_driver(c, store, secrets)
        except NotIntegrated:
            print(json.dumps(dict(started=False, reason='NOT_INTEGRATED', signing_enabled=False)))
            return EXIT_NOT_INTEGRATED
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

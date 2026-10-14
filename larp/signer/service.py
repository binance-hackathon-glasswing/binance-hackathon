"""Signer host service (IDEA-047 S02-S05; IDEA-046 B2). Run by deploy/systemd/larp-signer.service.

    python -m larp.signer.service check|run --config /etc/larp/signer.json --manifest /etc/larp/release.json --root R

The signer has no internet route; it reaches only the database. It answers signing requests that the execution
service writes (larp/execution_live/signing.py). For each request it checks for itself everything it can see: the
run is this run, not quarantined and still owned by the request's epoch; the attempt is registered in the
hash-chained execution record, is the last one, is AUTHORIZED and carries the requested payload hash and authority;
the payload passes the G-01 allow-list (`validate_payload`), the step sequence and gas budget (`validate_sequence`);
and its own clock lies inside the gate window and before the intent expires. The gate facts it cannot observe
offline (wallet nonce, market open, risk, health) come from the request, as the execution service evaluated them.
A swap needs a verified router decoder; none exists yet (GAP-29), so swap requests are refused.

It signs through `LocalSigner`, whose fenced registry keeps at most one signature per attempt. A failed check becomes
a refusal row for that request; a database outage is not a refusal and stops the cycle.

Exit codes as the runtime service: 0 clean stop; 1 failure (restart); 3 run quarantined; 4 start refused.
"""

import argparse
import json
import math
import os
from pathlib import Path
import re
import signal
import time

from larp.contracts import ContractError, Document
from larp.execution import Blocked, Gates, address, validate_sequence
from larp.execution_live import signing
from larp.execution_live.store import ExecutionStore
from larp.execution_live.venue import UnverifiedRouter
from larp.signer.keyfile import load_key_file
from larp.signer.local import LocalSigner

EXIT_QUARANTINED, EXIT_REFUSED = 3, 4
SCHEMA = 'SignerService.v1'
SERVICE = 'signer'
DATABASE_USER = 'larp_signer'
_CREDENTIAL = re.compile(r'[A-Za-z0-9_.-]{1,64}')
MALFORMED = (TypeError, ValueError, KeyError, AttributeError, OverflowError, RecursionError)


class StartRefused(ContractError):
    pass


class SignerService:
    def __init__(self, *, store, run_id, wallet, credentials, clock_s, decoder=None, max_skew_s=2, batch=16,
                 build_id=None):
        self.store, self.run_id, self.clock = store, run_id, clock_s
        self.build_id = build_id
        self.decoder = decoder if decoder is not None else UnverifiedRouter()
        self.max_skew, self.batch = max_skew_s, batch
        self.registry = ExecutionStore(store, run_id=run_id, wallet=address(wallet))
        self._current = None
        self.signer = LocalSigner.from_secret_store(dict(credentials, AI_SEEDS_ADDRESS=wallet),
                                                    registry=self.registry, authorization=self._authorize,
                                                    signer_host=True)

    def _authorize(self, attempt_id, payload, epoch, guard_version):
        if self._current is None or self._current[0] != attempt_id:
            raise Blocked('no current signing request')
        return self._current[1:]

    def once(self):
        """Answer up to `batch` pending requests; returns how many were answered."""
        handled = 0
        for request_id, raw in signing.pending(self.store, self.run_id, self.batch):
            now = self.clock()
            try:
                self._sign(request_id, raw, now)
            except (Blocked, ContractError) as refused:
                signing.refuse(self.store, self.run_id, request_id, refused, now)
            except MALFORMED as error:
                # A request whose content breaks a check is refused, never retried: left unanswered it would be
                # served first again after every restart (IDEA-047 R2). A database outage (`Unavailable`, a
                # RuntimeError) is not in MALFORMED and still stops the cycle.
                signing.refuse(self.store, self.run_id, request_id, 'malformed signing request: '
                               + type(error).__name__, now)
            handled += 1
        return handled

    def _sign(self, request_id, raw, now):
        request, gates = signing.read_request(request_id, raw)
        if request['run_id'] != self.run_id:
            raise Blocked('request for another run')
        state, attempt = self.registry.attempt(request['attempt_id'])
        if state.status != 'ACTIVE' or attempt.attempt_id != state.attempts[-1].attempt_id:
            raise Blocked('attempt is not the active step')
        if attempt.state != 'AUTHORIZED':
            raise Blocked('attempt is not authorized')
        if (state.intent.key != request['economic_key'] or attempt.step != request['step']
                or attempt.payload.hash != request['payload_hash']):
            raise Blocked('request does not match the registered attempt')
        authority = (attempt.epoch, attempt.guard_version)
        if authority != (request['epoch'], request['guard_version']) or authority != (gates.epoch,
                                                                                      gates.authority_version):
            raise Blocked('stale signing authority')
        # Primary-supplied gate flags cannot override the signer's own release,
        # the registered run identity, or a HALT raised since it queued the request.
        with self.store.transaction() as db:
            run = self.registry._release_authority(db, *authority)
            if run['mode'] != 'offline' and not self.build_id:
                raise Blocked('verified signer build identity required')
            self.registry.check_signing_run(run, state.intent, self.build_id)
        if now + self.max_skew < gates.observed_at:
            raise Blocked('signer clock is behind the request')
        validate_sequence(state, attempt.step, attempt.payload, gates)
        self._current = (attempt.attempt_id, state.intent, attempt.step, gates, max(now, gates.observed_at),
                         self.decoder)
        try:
            return self.signer.sign(attempt.attempt_id, attempt.payload, *authority)
        finally:
            self._current = None


def validate_config(value):
    if type(value) is not dict or value.get('schema') != SCHEMA:
        raise ContractError('Invalid signer service configuration schema')
    missing = [k for k in ('run_id', 'build_id', 'mode', 'wallet_address', 'interval_seconds')
               if value.get(k) in (None, '')]
    if missing:
        raise ContractError('Missing signer settings: ' + ','.join(missing))
    if value['mode'] not in ('dev', 'live'):
        raise ContractError('The signer runs only for dev or live runs')
    try:
        address(value['wallet_address'])
    except Blocked:
        raise ContractError('Invalid wallet address') from None
    interval = value['interval_seconds']
    if type(interval) not in (int, float) or not math.isfinite(interval) or interval <= 0:
        raise ContractError('Invalid signer interval')
    skew = value.get('max_clock_skew_seconds', 2)
    if type(skew) is not int or not 0 <= skew <= 30:
        raise ContractError('Invalid clock skew allowance')
    # The key arrives as a file (systemd LoadCredential); never as a value, an environment variable or a secret ID.
    forbidden = [k for k in value if k.endswith('_secret_id') or 'private_key' in k or 'mnemonic' in k]
    if forbidden:
        raise ContractError('Signer configuration names a secret source: ' + ','.join(sorted(forbidden)))
    if (value.get('key_file') in (None, '')) == (value.get('key_credential') in (None, '')):
        raise ContractError('Configure exactly one of key_file or key_credential')
    if value.get('key_credential') not in (None, '') and not (
            type(value['key_credential']) is str and _CREDENTIAL.fullmatch(value['key_credential'])):
        raise ContractError('Invalid key credential name')
    from larp.runtime.database import check_database_settings
    check_database_settings(value, DATABASE_USER)
    return value


def key_path(config, environ=os.environ):
    if config.get('key_file'):
        return Path(config['key_file'])
    directory = environ.get('CREDENTIALS_DIRECTORY')
    if not directory:
        raise Blocked('systemd credentials directory missing')
    return Path(directory) / config['key_credential']


def load_config(args):
    """Validated configuration bound to the verified release (G-03); StartRefused otherwise."""
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


def run_state(store, run_id):
    from larp.storage.postgres import PostgresStore
    with store.transaction() as db:
        return PostgresStore._run(db, run_id, lock=False)


def main(argv=None, *, environ=os.environ, clock_s=lambda: int(time.time()), sleep=time.sleep, max_cycles=None):
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
        from larp.runtime.database import open_service_store
        store = open_service_store(config)
        run = run_state(store, config['run_id'])
        if run['mode'] != config['mode'] or str(run['wallet_id']).lower() != config['wallet_address']:
            raise StartRefused('run differs from the signer configuration')
        if run['quarantined']:
            print(json.dumps(dict(started=False, reason='QUARANTINED', signing_enabled=False)))
            return EXIT_QUARANTINED
        try:
            credentials = load_key_file(key_path(config, environ))
            service = SignerService(store=store, run_id=config['run_id'], wallet=config['wallet_address'],
                                    credentials=credentials, clock_s=clock_s,
                                    max_skew_s=config.get('max_clock_skew_seconds', 2), build_id=config['build_id'])
        except Blocked as refused:
            # Key-file and wallet-binding refusals are fixed texts that never carry key material.
            print(json.dumps(dict(started=False, reason='KEY_REFUSED', detail=str(refused), signing_enabled=False)))
            return EXIT_REFUSED
        stopping = []
        signal.signal(signal.SIGTERM, lambda *a: stopping.append(True))
        print(json.dumps(dict(started=True, signing_enabled=True, swap_decoder='UNVERIFIED')))
        cycles = 0
        while not stopping and (max_cycles is None or cycles < max_cycles):
            if run_state(store, config['run_id'])['quarantined']:
                print(json.dumps(dict(stopped=True, reason='QUARANTINED', signing_enabled=False)))
                return EXIT_QUARANTINED
            if not service.once():
                sleep(config['interval_seconds'])
            cycles += 1
        return 0
    except StartRefused:
        print(json.dumps(dict(started=False, reason='START_REFUSED', signing_enabled=False)))
        return EXIT_REFUSED
    except Exception:
        # Exception text can carry DSNs; never key material, which only the loader and LocalSigner touch.
        print(json.dumps(dict(started=False, reason='SIGNER_FAILED', signing_enabled=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

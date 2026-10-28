"""The execution service's cycle on `primary` (IDEA-050): claim committed commands, advance executions, publish facts.

The runtime and the execution service share facts only through the database:

- I3: the runtime commits an `EXECUTION_REQUEST` command with its round. `ExecutionLoop` claims it once through
  `ExecutionService.create_from_command` (which calls the fenced `PostgresStore.command`) while it is current.
- I4: every observation the service produces (broadcast attempts, final receipt facts, NOT_SUBMITTED for an aborted
  intent) is written to `execution_observations`, fenced by the run epoch. The runtime driver journals them
  (larp/runtime/driver.py `ServiceExecution`); this process never writes the run journal.

`RunAuthorization` gives the guards the run facts they need at every step, read from the journal each time: the
registered build, HALT and quarantine, the intent's reservation and round, the durable plan record, journal integrity
and the decision clock. A HALT therefore stops the next signature of an execution already under way, and an intent the
runtime has ended can never be created or signed afterwards.

Nothing here lifts a capability gate: the `Executor` still refuses a live bundle, `UnverifiedRouter` still refuses every
swap, and the signer host still checks every request itself.
"""

import json

from larp.contracts import Document
from larp.execution import Blocked, Conflict, Rejected, TERMINAL, digest, possibly_submitted
from larp.storage.postgres import IntegrityError
from larp.contracts import ContractError
from larp.runtime import halts


def intent_key(run_id, wallet, intent_id):
    return digest([run_id, 56, wallet.lower(), intent_id])  # larp.execution.Intent.key


class RunAuthorization:
    """`LiveGuards.authorization`: run facts for one intent, from the journal at the moment of the snapshot."""

    def __init__(self, store, *, run_id, build_id, manifest_sha256=None, settlement_hold=None, clock_s=None):
        self.store, self.run_id, self.build_id = store, run_id, build_id
        self.manifest_sha256 = manifest_sha256
        # Untrusted-router mode (IDEA-070 B02-U): True while a terminal execution has no stored final fact, e.g. a
        # fill settlement refused below its minimum. No new signature until it is resolved.
        self.settlement_hold = settlement_hold
        # IDEA-111: the decision clock is checked against a reading taken after the projection is loaded. The
        # caller's time is the cycle start, and a round the runtime commits mid-cycle is not a clock fault.
        self.clock_s = clock_s

    def facts(self, intent, now_s):
        from larp.runtime.coordinator import halt_reasons
        facts = dict(expires_at=intent.valid_until, audit_durable=False, reservation_valid=False, version_valid=False,
                     risk_valid=False, health_valid=False, clock_trusted=False, native_resource_route_valid=False)
        try:
            self.store.verified_snapshot(self.run_id, full=False)
            facts['health_valid'] = True
        except (IntegrityError, ContractError):
            return facts
        run = self.store.load(self.run_id).read()
        projection = run['projection']
        halted = halt_reasons(projection)
        registered = projection.get('registered_version')
        facts['version_valid'] = (type(registered) is dict and registered.get('build_id') == self.build_id
            and intent.version_id == self.build_id
            and ((self.manifest_sha256 is not None
                  and registered.get('manifest_sha256') == self.manifest_sha256)
                 or (run['mode'] == 'offline' and self.manifest_sha256 is None)))
        # D-DN-09: under a pausing HALT, only a planned mandatory bStock sell keeps valid risk authority.
        facts['risk_valid'] = not run['quarantined'] and halts.permits(projection, intent.round_id, intent.intent_id)
        from larp.strategy.execution_bounds import permitted
        facts['risk_valid'] = facts['risk_valid'] and permitted(projection, intent, now_s * 1000)
        if facts['risk_valid'] and self.settlement_hold is not None and self.settlement_hold() is not False:
            facts['risk_valid'] = False
        last = projection.get('last_decision_ms')
        observed_s = now_s
        if self.clock_s is not None:
            observed_s = self.clock_s()
            if type(observed_s) is not int or observed_s < now_s:
                observed_s = None  # a malformed or backward reading is never trusted
        facts['clock_trusted'] = ('CLOCK' not in halted and observed_s is not None
                                  and (last is None or observed_s * 1000 >= last - 1000))
        record = projection.get('round_records', {}).get(intent.round_id)
        planned = record is not None and any(i['intent_id'] == intent.intent_id
                                             for i in record['plan'].get('intents', []))
        final = record is not None and intent.intent_id in record.get('final_intents', [])
        facts['reservation_valid'] = planned and not final and self.resources_reserved(run, intent)
        plan = self.store.event(self.run_id, 'plan:' + intent.round_id)
        facts['audit_durable'] = bool(plan) and any(
            i['intent_id'] == intent.intent_id for i in plan.get('record', {}).get('plan', {}).get('intents', []))
        return facts

    def resources_reserved(self, run, intent):
        """Keep pay-token and BNB units separate; the parent gas cap covers all steps.

        Production accounting scales come from the durable portfolio. Historical
        untyped offline fixtures can attest only positive per-asset reservations.
        """
        from larp.execution import USDT
        from larp.execution_live.store import ExecutionStore
        from larp.marketdata.port import TOKENS
        pay_asset = ('USDT' if intent.pay_token == USDT else
                     next((s for s, token in TOKENS.items() if token == intent.pay_token), None))
        if pay_asset is None:
            return False
        held = {r['asset']: r['units'] for r in run['reservations'] if r['intent_id'] == intent.intent_id}
        pay, gas = held.get(pay_asset, 0), held.get('BNB', 0)
        if type(pay) is not int or type(gas) is not int or pay <= 0 or gas <= 0:
            return False
        scale = (run['projection'].get('portfolio') or {}).get('bnb_decimals')
        if scale is None and run['mode'] == 'offline':
            return True
        if type(scale) is not int or not 0 <= scale <= 18:
            return False
        if pay * (10**12 if pay_asset == 'USDT' else 1) < intent.amount:
            return False
        try:
            state = ExecutionStore(self.store, run_id=self.run_id, wallet=intent.wallet).load(intent.key)
        except Conflict:
            return False
        spent = 0
        if state is not None:
            if state.intent != intent:
                return False
            for attempt in state.attempts:
                if attempt.state in ('FINAL_SUCCESS', 'FINAL_REVERT'):
                    if type(attempt.gas_used) is not int or attempt.gas_used < 0:
                        return False
                    spent += attempt.gas_used * attempt.payload.gas_price
        remaining = intent.gas_budget - spent
        return remaining > 0 and gas * 10**(18 - scale) >= remaining

    def __call__(self, intent, epoch, state_version, now):
        return self.facts(intent, now)


class RoundTerminal:
    """`round_terminal` attestation: every other intent of the round is final in the journal, or ended there."""

    def __init__(self, store, *, run_id):
        self.store, self.run_id = store, run_id

    def __call__(self, state):
        if state.status not in TERMINAL:
            return False
        record = self.store.load(self.run_id).read()['projection'].get('round_records', {}).get(state.intent.round_id)
        if record is None:
            return False
        final = set(record.get('final_intents', [])) | {state.intent.intent_id}
        return all(i['intent_id'] in final for i in record['plan'].get('intents', []))


class PlanValuation:
    """The BNB price an attempt's gas is valued at: the one the round planned with, so a retried fact keeps its bytes
    (`ReceiptFacts` requires a persisted price, never the current one)."""

    def __init__(self, store, registry, *, run_id):
        self.store, self.registry, self.run_id = store, registry, run_id

    def portfolio(self, attempt_id):
        state, _ = self.registry.attempt(attempt_id)
        plan = self.store.event(self.run_id, 'plan:' + state.intent.round_id)
        if not plan:
            raise Blocked('attempt has no durable round plan')
        return ((plan['record'].get('policy_input') or {}).get('context') or {}).get('portfolio') or {}

    def __call__(self, attempt_id):
        price = self.portfolio(attempt_id).get('bnb_price_units')
        if type(price) is not int or price <= 0:
            raise Blocked('round plan carries no BNB valuation')
        return price

    def bnb_decimals(self, attempt_id):
        scale = self.portfolio(attempt_id).get('bnb_decimals')
        if type(scale) is not int or not 0 <= scale <= 18:
            raise Blocked('round plan carries no supported BNB accounting scale')
        return scale


class FencedRelease:
    """`LiveVenue.release`: the only path to submission. It re-checks that these exact bytes are the current possible
    send of an active attempt under this epoch and authority (`ExecutionStore.check_broadcast`), submits them through
    the Web3 Open API (`Web3Broadcaster`), and accepts only the transaction's own hash back."""

    def __init__(self, registry, submitter, *, clock_s=None, decoder=None):
        self.registry, self.submitter, self.clock, self.decoder = registry, submitter, clock_s, decoder

    def __call__(self, signed, epoch, guard_version):
        options = {} if self.clock is None else {'now_ms': self.clock() * 1000}
        if self.decoder is not None:
            options['decoder'] = self.decoder
        self.registry.check_broadcast(signed, epoch, guard_version, **options)
        tx_hash = self.submitter.send(signed.raw_hex)
        if type(tx_hash) is not str or tx_hash.lower() != signed.tx_hash.lower():
            raise Blocked('submission returned another transaction hash')
        return signed.tx_hash


# A node's own refusal of a transaction (WR12, #54), matched in the API error message. A message that also says the
# transaction is already known is ambiguous and never a rejection.
REJECTIONS = (('insufficient funds', 'INSUFFICIENT_FUNDS'), ('nonce too low', 'NONCE_TOO_LOW'),
              ('intrinsic gas too low', 'INTRINSIC_GAS_TOO_LOW'), ('exceeds block gas limit', 'GAS_LIMIT_EXCEEDED'),
              ('invalid sender', 'INVALID_SENDER'))
AMBIGUOUS = ('already known', 'known transaction', 'replacement')


def rejection_reason(record):
    """The fixed reason for a definite rejection in a stored (already redacted) broadcast record, else None."""
    body = record.get('response') if type(record) is dict else None
    if record is None or record.get('outcome') != 'api_or_http_error' or type(body) is not dict:
        return None
    code = body.get('code')
    if type(code) is not int or code == 0:
        return None
    message = ' '.join(v for v in (body.get('msg'), body.get('error'), body.get('message')) if type(v) is str).lower()
    if any(marker in message for marker in AMBIGUOUS):
        return None
    return next((reason for marker, reason in REJECTIONS if marker in message), None)


class _Recorded:
    """The broadcaster's artifact store, keeping the last stored record in memory so a rejection can be classified.
    The record is the client's redacted artifact (hashes of the signed bytes only); nothing new is persisted."""

    def __init__(self, artifacts):
        self.artifacts, self.last = artifacts, None

    def put(self, record):
        self.last = record
        return self.artifacts.put(record)


class Web3Broadcaster:
    """The submitter for `FencedRelease`: the Web3 Open API's `broadcast-transaction` endpoint, the only order channel
    the kit allows (F-104, never-do #3; guide p.8). A separate authenticated client allows that one endpoint and
    nothing else, so the read/build client still cannot send. The artifact record keeps a hash of the signed bytes,
    never the bytes. Any failure is "possibly sent": the attempt stays a possible send and reconciles from the chain;
    it is never re-signed with another nonce. The one exception is a definite node rejection (`Rejected`, a fixed
    reason code), which reconciliation can end as NOT_SUBMITTED once the chain nonce proves it (WR12, #54)."""

    ENDPOINT = ('POST', 'pre-transaction/broadcast-transaction')

    def __init__(self, key, secret, *, wallet, artifacts, opener=None):
        from larp.marketdata.web3 import Artifacts, Web3Client

        class Client(Web3Client):
            endpoints = frozenset({self.ENDPOINT})
            private_params = ('signedTransaction',)

        if type(wallet) is not str or not wallet.startswith('0x') or len(wallet) != 42:
            raise Blocked('broadcast wallet address required')
        self.wallet = wallet.lower()
        self.records = _Recorded(Artifacts(artifacts))
        self.client = Client(key, secret, artifacts=self.records, opener=opener)

    def send(self, raw_hex):
        from larp.execution import DependencyUnavailable
        from larp.marketdata.web3 import Unavailable, single
        if type(raw_hex) is not str or not raw_hex.startswith('0x') or len(raw_hex) < 4:
            raise Blocked('signed transaction bytes required')
        self.records.last = None
        try:
            record = self.client.request(*self.ENDPOINT, dict(binanceChainId='56', signedTransaction=raw_hex,
                                                              address=self.wallet))
            tx_hash = single(record)['txHash']
        except Unavailable:
            reason = rejection_reason(self.records.last)
            if reason is not None:
                raise Rejected(reason) from None
            raise DependencyUnavailable('broadcast outcome unknown') from None
        except (KeyError, TypeError):
            raise DependencyUnavailable('broadcast outcome unknown') from None
        if type(tx_hash) is not str:
            raise DependencyUnavailable('broadcast outcome unknown')
        return tx_hash


class ExecutionLoop:
    """One cycle per tick: claim, advance, publish. Returns a summary without secret values or signed bytes."""

    def __init__(self, *, store, registry, service, run_id, wallet, epoch, batch=8):
        self.store, self.registry, self.service = store, registry, service
        self.run_id, self.wallet, self.epoch, self.batch = run_id, wallet.lower(), epoch, batch

    def publish(self, observation):
        """`ExecutionService.observe`: the immutable outbox the runtime driver journals."""
        return self.registry.put_observation(observation, self.epoch, self.epoch)

    def _commands(self, now_ms):
        run = self.store.load(self.run_id).read()
        with self.store.transaction() as db:
            rows = db.execute('SELECT command_id,payload,state_version FROM commands WHERE run_id=%s '
                              "AND status='PENDING' ORDER BY state_version,command_id", (self.run_id,)).fetchall()
            known = {r[0] for r in db.execute('SELECT economic_key FROM execution_records WHERE run_id=%s',
                                              (self.run_id,))}
        claimable = []
        for command_id, raw, state_version in rows:
            command = Document(bytes(raw)).read()
            if (state_version != run['version'] or command.get('expires_ms', 0) <= now_ms
                    or intent_key(self.run_id, self.wallet, command_id) in known):
                continue  # stale, expired or already claimed: never claimed again
            claimable.append(command_id)
        return claimable[:self.batch]

    def _active(self):
        with self.store.transaction() as db:
            return [r[0] for r in db.execute('SELECT economic_key FROM execution_records WHERE run_id=%s '
                                             'AND NOT terminal ORDER BY economic_key', (self.run_id,))]

    def _unpublished_terminal(self):
        """Terminal records whose final fact never reached the outbox (a crash between the two commits)."""
        with self.store.transaction() as db:
            keys = [r[0] for r in db.execute('SELECT economic_key FROM execution_records WHERE run_id=%s '
                                             'AND terminal ORDER BY economic_key', (self.run_id,))]
        missing = []
        for key in keys:
            state = self.registry.load(key)
            if state.status == 'ABORTED' and not any(a.step == 'SWAP' and possibly_submitted(a)
                                                     for a in state.attempts):
                expected = [state.intent.key + ':not-submitted']
            else:
                expected = [a.attempt_id + ':final' for a in state.attempts
                            if a.state in ('FINAL_SUCCESS', 'FINAL_REVERT')]
            if any(self.registry.lookup_observation(event_id) is None for event_id in expected):
                missing.append(key)
        return missing

    def once(self, now_ms):
        summary = dict(claimed=[], advanced=[], blocked=[])
        for command_id in self._commands(now_ms):
            try:
                self.service.create_from_command(self.run_id, command_id, self.epoch, now_ms)
                summary['claimed'].append(command_id)
            except (Blocked, Conflict, ContractError) as refused:
                summary['blocked'].append([command_id, type(refused).__name__])
        for key in self._active() + self._unpublished_terminal():
            try:
                state = self.service.advance(key, now_ms // 1000)
                summary['advanced'].append([key, state.status])
            except (Blocked, Conflict, ContractError) as refused:
                # A guard refusal (HALT, expiry, stale authority) is a hold: the next cycle tries again from the
                # durable state, and reconciliation of possible sends is never skipped by it.
                summary['blocked'].append([key, type(refused).__name__])
        return summary

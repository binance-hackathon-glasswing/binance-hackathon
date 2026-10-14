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
from larp.execution import Blocked, Conflict, TERMINAL, digest
from larp.storage.postgres import IntegrityError
from larp.contracts import ContractError


def intent_key(run_id, wallet, intent_id):
    return digest([run_id, 56, wallet.lower(), intent_id])  # larp.execution.Intent.key


class RunAuthorization:
    """`LiveGuards.authorization`: run facts for one intent, from the journal at the moment of the snapshot."""

    def __init__(self, store, *, run_id, build_id):
        self.store, self.run_id, self.build_id = store, run_id, build_id

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
        facts['version_valid'] = (projection.get('registered_version') or {}).get('build_id') == self.build_id
        facts['risk_valid'] = not halted and not run['quarantined']
        last = projection.get('last_decision_ms')
        facts['clock_trusted'] = 'CLOCK' not in halted and (last is None or now_s * 1000 >= last - 1000)
        record = projection.get('round_records', {}).get(intent.round_id)
        planned = record is not None and any(i['intent_id'] == intent.intent_id
                                             for i in record['plan'].get('intents', []))
        final = record is not None and intent.intent_id in record.get('final_intents', [])
        held = sum(r['units'] for r in run['reservations'] if r['intent_id'] == intent.intent_id)
        facts['reservation_valid'] = planned and not final and held > 0
        plan = self.store.event(self.run_id, 'plan:' + intent.round_id)
        facts['audit_durable'] = bool(plan) and any(
            i['intent_id'] == intent.intent_id for i in plan.get('record', {}).get('plan', {}).get('intents', []))
        return facts

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

    def __call__(self, attempt_id):
        state, _ = self.registry.attempt(attempt_id)
        plan = self.store.event(self.run_id, 'plan:' + state.intent.round_id)
        if not plan:
            raise Blocked('attempt has no durable round plan')
        portfolio = ((plan['record'].get('policy_input') or {}).get('context') or {}).get('portfolio') or {}
        price = portfolio.get('bnb_price_units')
        if type(price) is not int or price <= 0:
            raise Blocked('round plan carries no BNB valuation')
        return price


class FencedRelease:
    """`LiveVenue.release`: the only path to submission. It re-checks that these exact bytes are the current possible
    send of an active attempt under this epoch and authority (`ExecutionStore.check_broadcast`), submits them through
    the Web3 Open API (`Web3Broadcaster`), and accepts only the transaction's own hash back."""

    def __init__(self, registry, submitter):
        self.registry, self.submitter = registry, submitter

    def __call__(self, signed, epoch, guard_version):
        self.registry.check_broadcast(signed, epoch, guard_version)
        tx_hash = self.submitter.send(signed.raw_hex)
        if type(tx_hash) is not str or tx_hash.lower() != signed.tx_hash.lower():
            raise Blocked('submission returned another transaction hash')
        return signed.tx_hash


class Web3Broadcaster:
    """The submitter for `FencedRelease`: the Web3 Open API's `broadcast-transaction` endpoint, the only order channel
    the kit allows (F-104, never-do #3; guide p.8). A separate authenticated client allows that one endpoint and
    nothing else, so the read/build client still cannot send. The artifact record keeps a hash of the signed bytes,
    never the bytes. Any failure is "possibly sent": the attempt stays a possible send and reconciles from the chain;
    it is never re-signed with another nonce."""

    ENDPOINT = ('POST', 'pre-transaction/broadcast-transaction')

    def __init__(self, key, secret, *, wallet, artifacts, opener=None):
        from larp.marketdata.web3 import Artifacts, Web3Client

        class Client(Web3Client):
            endpoints = frozenset({self.ENDPOINT})
            private_params = ('signedTransaction',)

        if type(wallet) is not str or not wallet.startswith('0x') or len(wallet) != 42:
            raise Blocked('broadcast wallet address required')
        self.wallet = wallet.lower()
        self.client = Client(key, secret, artifacts=Artifacts(artifacts), opener=opener)

    def send(self, raw_hex):
        from larp.execution import DependencyUnavailable
        from larp.marketdata.web3 import Unavailable, single
        if type(raw_hex) is not str or not raw_hex.startswith('0x') or len(raw_hex) < 4:
            raise Blocked('signed transaction bytes required')
        try:
            record = self.client.request(*self.ENDPOINT, dict(binanceChainId='56', signedTransaction=raw_hex,
                                                              address=self.wallet))
            tx_hash = single(record)['txHash']
        except (Unavailable, KeyError, TypeError):
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
            if state.status == 'ABORTED' and not any(a.step == 'SWAP' and a.broadcast_at is not None
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

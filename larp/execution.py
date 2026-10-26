"""W04 execution machine and integration ports.

No network, credential lookup, wallet signing, scheduler or portfolio ledger.
The Executor accepts an all-fake bundle, or live ports only with a swap decoder pinned to router evidence
(larp/execution_live/router.py; IDEA-070, GAP-29).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import re
from typing import Protocol

from larp.runtime import faults

USDT = "0x55d398326f99059ff775485246999027b3197955"
NATIVE_BNB = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
BSTOCKS = frozenset({
    "0x02fca66c1d1afb4e2a7884261eb00f63598a7436",
    "0x3f53de71c126bdabae20f9cd64848d317f6c3238",
    "0xca750ef65f295bbecd685abf54e82caf297bdb61",
    "0x5b1910eaad6450e50f816082aa078c41f10c292f",
    "0x80106cb3ead06659a5ad19df39d9b4733863b9b0",
})
REVOKE_TOKENS = {'REVOKE:' + token: token for token in BSTOCKS | {USDT}}


def approval_step(step):
    """Trade approval or one of the six zero-only maintenance steps (LD06)."""
    return step == 'APPROVE' or type(step) is str and step in REVOKE_TOKENS


FINAL = frozenset({"FINAL_SUCCESS", "FINAL_REVERT", "ABORTED", "NOT_SUBMITTED"})
TERMINAL = frozenset({"COMPLETED", "FAILED", "ABORTED"})


class Blocked(RuntimeError):
    """A missing prerequisite, not permission to bypass an execution guard."""


class Conflict(Blocked):
    """Stale revision, ownership or wallet-wide concurrency conflict."""


class DependencyUnavailable(Blocked):
    """A sanitized transient port failure, never evidence of transaction absence."""


class Rejected(Blocked):
    """The node definitely refused these signed bytes (WR12, #54). Never a timeout or a lost response.

    The message is the fixed reason code only, never response text. A rejected attempt keeps its wallet barrier
    until reconciliation proves non-submission (Executor.reconcile)."""
    REASONS = frozenset({'INSUFFICIENT_FUNDS', 'NONCE_TOO_LOW', 'INTRINSIC_GAS_TOO_LOW', 'GAS_LIMIT_EXCEEDED',
                         'INVALID_SENDER'})

    def __init__(self, reason):
        if reason not in self.REASONS:
            raise ValueError('unknown rejection reason')
        super().__init__(reason)
        self.reason = reason


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-f]{40}", value):
        raise Blocked("address must be normalized lowercase hex")
    return value


def integer(value, positive=False):
    if type(value) is not int or value < (1 if positive else 0) or value >= 2**256:
        raise Blocked("invalid integer quantity")
    return value


@dataclass(frozen=True)
class Intent:
    run_id: str
    round_id: str
    decision_id: str
    intent_id: str
    version_id: str
    reservation_id: str
    wallet: str
    pay_token: str
    receive_token: str
    amount: int
    minimum_output: int
    router: str
    valid_until: int
    max_gas: int
    max_gas_price: int
    gas_budget: int
    chain_id: int = 56
    max_prepare_probes: int = 3
    max_recovery_probes: int = 8
    probe_interval: int = 3
    timeout: int = 120
    kind: str = "BSTOCK_TRADE"
    max_cash_units: int | None = None
    max_slippage_bps: int = 50
    # #27 Option A (IDEA-049-C LD04): seconds that must remain before the authority end and each route deadline.
    authority_margin: int = 0

    @property
    def key(self):
        # Economic identity deliberately excludes round/decision: reparenting
        # cannot evade duplicate-economic-intent protection.
        return digest([self.run_id, self.chain_id, self.wallet, self.intent_id])

    def validate(self):
        for field in (self.run_id, self.round_id, self.decision_id, self.intent_id,
                      self.version_id, self.reservation_id):
            if not isinstance(field, str) or not field.strip():
                raise Blocked("missing immutable identity")
        for value in (self.wallet, self.pay_token, self.receive_token, self.router):
            address(value)
        if self.chain_id != 56 or type(self.chain_id) is not int:
            raise Blocked("only chain 56")
        bstock = self.kind == "BSTOCK_TRADE" and (
            (self.pay_token == USDT and self.receive_token in BSTOCKS)
            or (self.receive_token == USDT and self.pay_token in BSTOCKS))
        gas_top_up = (self.kind == "GAS_TOP_UP" and self.pay_token == USDT
                      and self.receive_token == NATIVE_BNB)
        if not (bstock or gas_top_up):
            raise Blocked("unsupported economic action")
        integer(self.max_slippage_bps)
        if self.max_slippage_bps >= 10000:
            raise Blocked('invalid slippage authorization')
        integer(self.authority_margin)
        if self.max_cash_units is not None:
            integer(self.max_cash_units, positive=True)
            if self.pay_token == USDT and self.amount > self.max_cash_units * 10**12:
                raise Blocked('per-trade cash cap exceeded')
        for value in (self.amount, self.minimum_output, self.valid_until, self.max_gas,
                      self.max_gas_price, self.gas_budget, self.max_prepare_probes,
                      self.max_recovery_probes, self.probe_interval, self.timeout):
            integer(value, positive=True)


@dataclass(frozen=True)
class Payload:
    chain_id: int
    sender: str
    to: str
    value: int
    nonce: int
    gas: int
    gas_price: int
    data: str

    @property
    def hash(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class SwapEconomics:
    pay_token: str
    receive_token: str
    amount: int
    recipient: str
    minimum_output: int
    deadline: int
    native_value: int


@dataclass(frozen=True)
class Gates:
    epoch: int
    state_version: int
    nonce: int | None
    observed_at: int
    expires_at: int
    audit_durable: bool = False
    reservation_valid: bool = False
    version_valid: bool = False
    risk_valid: bool = False
    health_valid: bool = False
    token_market_open: bool = False
    underlying_market_open: bool = False
    clock_trusted: bool = False
    execution_version: int | None = None

    @property
    def authority_version(self):
        return self.state_version if self.execution_version is None else self.execution_version

    def check(self, intent, now):
        integer(now)
        integer(self.observed_at)
        integer(self.expires_at, positive=True)
        if not (self.observed_at <= now < self.expires_at and now < intent.valid_until):
            raise Blocked("stale/expired authorization or clock regression")
        if self.nonce is None:
            raise Blocked("missing wallet nonce evidence")
        integer(self.nonce)
        integer(self.epoch)
        integer(self.state_version)
        if not all(value is True for value in (self.audit_durable, self.reservation_valid, self.version_valid,
                    self.risk_valid, self.health_valid, self.token_market_open,
                    self.underlying_market_open, self.clock_trusted)):
            raise Blocked("current execution prerequisite failed")


@dataclass(frozen=True)
class Attempt:
    attempt_id: str
    step: str
    state: str
    payload: Payload
    epoch: int
    guard_version: int
    raw_hex: str | None = None  # Offline fixtures only; PostgreSQL state strips bytes before committing.
    tx_hash: str | None = None
    broadcast_at: int | None = None
    probes: int = 0
    next_probe: int = 0
    included_block: str | None = None
    gas_used: int | None = None
    finalized_at: int | None = None
    dependency_failures: int = 0


@dataclass(frozen=True)
class Execution:
    intent: Intent
    revision: int = 0
    status: str = "ACTIVE"
    attempts: tuple[Attempt, ...] = ()
    prepare_probes: int = 0
    blocked_reason: str | None = None
    last_observed_at: int = 0
    abort_pending: bool = False  # durable, no further positive approval or swap authority


@dataclass(frozen=True)
class Signed:
    raw_hex: str
    tx_hash: str


@dataclass(frozen=True)
class Outcome:
    tx_hash: str
    sender: str | None
    nonce: int | None
    status: str  # PENDING, UNKNOWN, SUCCESS, REVERT
    block_hash: str | None = None
    canonical_block_hash: str | None = None
    block_number: int | None = None
    finalized_height: int | None = None
    finality_verified: bool = False
    gas_used: int | None = None


class Store(Protocol):
    """W02 must enforce CAS + epoch/state-version + wallet barrier atomically.

    Persist events and state together. Keys are globally unique economic keys;
    only one ACTIVE execution per wallet/chain across runs. Signed bytes belong
    in restricted state, never general events. No transaction spans port I/O.
    """
    def load(self, key: str) -> Execution | None: ...
    def commit(self, previous: Execution | None, current: Execution, event: dict,
               epoch: int, guard_version: int) -> Execution: ...


class GuardPort(Protocol):
    mode: str
    def snapshot(self, intent: Intent, now: int) -> Gates: ...


class Venue(Protocol):
    mode: str
    def quote(self, intent: Intent, nonce: int) -> Payload: ...
    def approve(self, intent: Intent, nonce: int) -> Payload: ...
    def estimate_gas(self, payload: Payload) -> int | None: ...
    def broadcast(self, signed: Signed, epoch: int, guard_version: int) -> str: ...
    def outcome(self, tx_hash: str) -> Outcome: ...


class Signer(Protocol):
    mode: str
    def sign(self, attempt_id: str, payload: Payload, epoch: int, guard_version: int) -> Signed: ...
    def verify(self, payload: Payload, signed: Signed) -> bool: ...
    def lookup(self, attempt_id: str, payload_hash: str) -> Signed | None: ...


class Decoder(Protocol):
    mode: str
    def decode(self, payload: Payload) -> SwapEconomics: ...


def validate_payload(intent, step, payload, gates, now, decoder):
    gates.check(intent, now)
    margin = intent.authority_margin
    if now + margin >= intent.valid_until:
        raise Blocked("no submission margin left inside the execution authority")
    if (payload.chain_id != intent.chain_id or type(payload.chain_id) is not int
            or payload.sender != intent.wallet or payload.nonce != gates.nonce):
        raise Blocked("chain/wallet/nonce mismatch")
    address(payload.to)
    for value in (payload.value, payload.nonce):
        integer(value)
    integer(payload.gas, positive=True)
    integer(payload.gas_price, positive=True)
    if (payload.gas > intent.max_gas or payload.gas_price > intent.max_gas_price
            or payload.gas * payload.gas_price > intent.gas_budget):
        raise Blocked("gas exceeds authorization budget")
    if not isinstance(payload.data, str) or not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})+", payload.data):
        raise Blocked("malformed calldata")
    if approval_step(step):
        revoke = step in REVOKE_TOKENS
        token, amount = (REVOKE_TOKENS[step], 0) if revoke else (intent.pay_token, intent.amount)
        if revoke and (getattr(decoder, 'mode', None) != 'untrusted'
                       or getattr(decoder, 'router', None) != intent.router or intent.kind != 'BSTOCK_TRADE'):
            raise Blocked('allowance recovery requires a stock intent and its selected untrusted router')
        if payload.to != token or payload.value != 0:
            raise Blocked("approve destination/value mismatch")
        if not re.fullmatch(r"0x095ea7b3[0-9a-fA-F]{128}", payload.data):
            raise Blocked("unknown approve selector/shape")
        if payload.data[10:34] != "0" * 24:
            raise Blocked("noncanonical spender padding")
        if ("0x" + payload.data[34:74].lower() != intent.router
                or int(payload.data[74:], 16) != amount):
            raise Blocked("approve spender/amount mismatch")
    elif step == "SWAP":
        if payload.to != intent.router or payload.value != 0:
            raise Blocked("swap destination/value mismatch")
        economics = decoder.decode(payload)  # MUST bind decoded fields to bytes.
        for value in (economics.amount, economics.minimum_output, economics.deadline):
            integer(value, positive=True)
        # Only an untrusted-router decoder may leave the recipient unverified (IDEA-070 B02-U, DEV-23); its
        # preflight bounds what the router can take instead.
        unverified = economics.recipient is None and getattr(decoder, "mode", None) == "untrusted"
        if (economics.pay_token != intent.pay_token or economics.receive_token != intent.receive_token
                or economics.amount != intent.amount or (economics.recipient != intent.wallet and not unverified)
                or economics.minimum_output < intent.minimum_output
                or not now + margin < economics.deadline <= intent.valid_until
                or economics.native_value != payload.value):
            raise Blocked("encoded swap economics mismatch/expired")
    else:
        raise Blocked("unsupported transaction step")


def validate_sequence(state, step, payload, gates):
    """Checks across the execution's steps; the remote signer repeats them (larp/signer/service.py)."""
    matching = [a for a in state.attempts if a.step == step]
    if len(matching) > 1:
        raise Blocked('duplicate execution step')
    prior = tuple(a for a in state.attempts if a.step != step)
    aborting = getattr(state, 'abort_pending', False)  # historical public validation fixtures predate F3
    if aborting:
        if (step != 'REVOKE:' + state.intent.pay_token
                or not any(a.step == 'APPROVE' and a.state == 'FINAL_SUCCESS' for a in prior)
                or any(a.step == 'SWAP' and not (a.state == 'NOT_SUBMITTED' or
                           a.state == 'ABORTED' and a.broadcast_at is None)
                       for a in prior)):
            raise Blocked('aborting intent only authorizes its pay-token zero approval')
        prior = tuple(a for a in prior if a.state not in {'ABORTED', 'NOT_SUBMITTED'})
    if (len({a.step for a in prior}) != len(prior)
            or any(not approval_step(a.step) or a.state != 'FINAL_SUCCESS' for a in prior)
            or any(a.step == 'APPROVE' for a in prior[:-1])):
        raise Blocked('invalid preceding execution steps')
    if step in REVOKE_TOKENS and not aborting and any(a.step == 'APPROVE' for a in prior):
        raise Blocked('allowance cleanup cannot follow trade approval')
    if step == "SWAP" and prior and prior[-1].step != 'APPROVE':
        raise Blocked('swap requires final trade approval after cleanup')
    if prior:
        if gates.nonce != prior[-1].payload.nonce + 1:
            raise Blocked("approved nonce consumption and current wallet count disagree")
    previous_cost = sum((attempt.gas_used if attempt.state in {"FINAL_SUCCESS", "FINAL_REVERT"}
                         and attempt.gas_used is not None
                         else attempt.payload.gas) * attempt.payload.gas_price
                        for attempt in state.attempts if attempt.step != step
                        and not (attempt.state == 'NOT_SUBMITTED' or
                                 attempt.state == 'ABORTED' and attempt.broadcast_at is None))
    if previous_cost + payload.gas * payload.gas_price > state.intent.gas_budget:
        raise Blocked("parent gas budget exceeded")


class Executor:
    def __init__(self, store: Store, guards: GuardPort, venue: Venue, signer: Signer, decoder: Decoder,
                 *, allowance_recovery=False):
        # A bundle is all fake (offline fixtures), or all live with a swap decoder built from pinned router
        # evidence (IDEA-070; GAP-29) or an untrusted-router policy bound to a live RPC for its preflight (B02-U).
        # Never a mix, and never live with UnverifiedRouter.
        ports = tuple(getattr(port, "mode", None) for port in (guards, venue, signer))
        fake = ports == ("fake",) * 3 and getattr(decoder, "mode", None) == "fake"
        live = False
        if ports == ("live",) * 3:
            from larp.execution_live.router import PinnedRouterDecoder
            from larp.execution_live.untrusted_router import UntrustedRouterDecoder
            live = (type(decoder) is PinnedRouterDecoder
                    or (type(decoder) is UntrustedRouterDecoder and decoder.rpc is not None))
        if not (fake or live):
            raise Blocked("live execution needs live ports and a decoder pinned to router evidence")
        if type(allowance_recovery) is not bool or allowance_recovery and getattr(decoder, 'mode', None) != 'untrusted':
            raise Blocked('allowance recovery must explicitly select the untrusted router')
        self.allowance_recovery = allowance_recovery
        self.store, self.guards, self.venue, self.signer, self.decoder = store, guards, venue, signer, decoder

    def create(self, intent: Intent, now: int):
        intent.validate()
        existing = self.store.load(intent.key)
        if existing:
            if existing.intent != intent:
                raise Conflict("economic identity reused with changed intent")
            return existing
        gates = self.guards.snapshot(intent, now)
        gates.check(intent, now)
        return self._save(None, Execution(intent, last_observed_at=now), "INTENT_CREATED", gates)

    def _load(self, key):
        state = self.store.load(key)
        if state is None:
            raise Blocked("unknown intent")
        return state

    def _save(self, old, new, event_type, gates):
        attempt = new.attempts[-1] if new.attempts else None
        event = {"type": event_type, "intent_key": new.intent.key,
                 "run_id": new.intent.run_id, "round_id": new.intent.round_id,
                 "decision_id": new.intent.decision_id, "version_id": new.intent.version_id,
                 "reservation_id": new.intent.reservation_id, "status": new.status,
                 "attempt_id": attempt.attempt_id if attempt else None,
                 "step": attempt.step if attempt else None,
                 "state": attempt.state if attempt else None,
                 "payload_hash": attempt.payload.hash if attempt else None,
                 "tx_hash": attempt.tx_hash if attempt else None,
                 "blocked_reason": new.blocked_reason}
        return self.store.commit(old, new, event, gates.epoch, gates.state_version)

    def _update_attempt(self, old, attempt, event_type, gates, **changes):
        new = replace(old, attempts=old.attempts[:-1] + (attempt,), **changes)
        return self._save(old, new, event_type, gates)

    def _validate(self, state, step, payload, gates, now):
        if now < state.last_observed_at:
            raise Blocked("clock regression")
        validate_payload(state.intent, step, payload, gates, now, self.decoder)
        validate_sequence(state, step, payload, gates)
        if step in REVOKE_TOKENS:
            if not self.allowance_recovery:
                raise Blocked('allowance recovery is disabled')
            self.decoder.allowances(state.intent)  # current code/facet pins; no relaxed swap preflight
        if step == "SWAP" and getattr(self.decoder, "mode", None) == "untrusted":
            # The live router state still bounds the swap (B02-U); before this execution's approve, the approve will
            # overwrite the pay token's allowance.
            approved = any(a.step == "APPROVE" and a.state == "FINAL_SUCCESS" for a in state.attempts)
            self.decoder.preflight(state.intent, payload, approved=approved)

    def prepare(self, key, now):
        state = self._load(key)
        if state.status != "ACTIVE":
            return state
        if state.attempts and state.attempts[-1].state != "FINAL_SUCCESS" and not (
                state.abort_pending and state.attempts[-1].state in {'ABORTED', 'NOT_SUBMITTED'}):
            return state  # No second step while outgoing outcome is uncertain.
        integer(now)
        if now < state.last_observed_at:
            raise Blocked("clock regression")
        if state.prepare_probes >= state.intent.max_prepare_probes:
            raise Blocked('prepare probe budget exhausted')
        gates = self.guards.snapshot(state.intent, now)
        approved = any(a.step == 'APPROVE' and a.state == 'FINAL_SUCCESS' for a in state.attempts)
        step = "SWAP" if approved else "APPROVE"
        # Persist the work budget before any quote/estimate I/O; restart cannot reset it.
        state = self._save(state, replace(state, prepare_probes=state.prepare_probes + 1,
                           last_observed_at=now), "PREPARE_PROBE", gates)
        try:
            gates.check(state.intent, now)
            if state.abort_pending:
                step = 'REVOKE:' + state.intent.pay_token
                allowances = self.decoder.allowances(state.intent)
                if not allowances[state.intent.pay_token]:
                    return self._save(state, replace(state, status='ABORTED', last_observed_at=now),
                                      'ABORT_CLEAN', gates)
                if any(a.step == step for a in state.attempts):
                    raise Blocked('confirmed cleanup did not clear allowance; no repeat authority')
            else:
                quote = self.venue.quote(state.intent, gates.nonce)
            if self.allowance_recovery and not approved and not state.abort_pending:
                # Validate fresh quote economics before spending cleanup gas. Every zero-only step
                # remains inside this original intent's authority and aggregate reservation.
                validate_payload(state.intent, 'SWAP', quote, gates, now, self.decoder)
                allowances = self.decoder.allowances(state.intent)
                dirty = sorted(token for token, amount in allowances.items()
                               if amount and token != state.intent.pay_token)
                if dirty:
                    step = 'REVOKE:' + dirty[0]
                    if any(a.step == step for a in state.attempts):
                        raise Blocked('confirmed cleanup did not clear allowance; no repeat authority')
            if step in REVOKE_TOKENS:
                payload = self.venue.revoke(state.intent, REVOKE_TOKENS[step], gates.nonce)
            else:
                if self.allowance_recovery and not approved:
                    self.decoder.preflight(state.intent, quote, approved=False)
                else:
                    self._validate(state, "SWAP", quote, gates, now)
                payload = self.venue.approve(state.intent, gates.nonce) if step == "APPROVE" else quote
            estimate = self.venue.estimate_gas(payload)
            integer(estimate, positive=True)  # Missing estimate cannot use quote fallback.
            payload = replace(payload, gas=max(payload.gas, (estimate * 6 + 4) // 5))
            self._validate(state, step, payload, gates, now)
            if step == "SWAP" and payload.to != state.intent.router:
                raise Blocked("requoted router differs from approved spender")
        except Blocked as error:
            state = self._save(state, replace(state, blocked_reason=str(error)), "PREPARE_BLOCKED", gates)
            if approved and self.allowance_recovery and not state.abort_pending:
                return self.abort_unsigned(key, now)
            return state
        except (TimeoutError, ConnectionError):
            return self._save(state, replace(state, blocked_reason="quote/gas dependency unavailable"),
                              "PREPARE_BLOCKED", gates)
        attempt = Attempt(digest([key, step]), step, "PREPARED", payload, gates.epoch, gates.authority_version)
        return self._save(state, replace(state, attempts=state.attempts + (attempt,), blocked_reason=None),
                          "PREPARED", gates)

    def authorize(self, key, now):
        state = self._load(key)
        attempt = state.attempts[-1]
        if attempt.state != "PREPARED":
            return state
        gates = self.guards.snapshot(state.intent, now)
        self._validate(state, attempt.step, attempt.payload, gates, now)
        return self._update_attempt(state, replace(attempt, state="AUTHORIZED", epoch=gates.epoch,
                                   guard_version=gates.authority_version), "AUTHORIZED", gates, last_observed_at=now)

    def sign(self, key, now):
        state = self._load(key)
        attempt = state.attempts[-1]
        if attempt.state != "AUTHORIZED":
            return state
        gates = self.guards.snapshot(state.intent, now)
        if (gates.epoch, gates.authority_version) != (attempt.epoch, attempt.guard_version):
            raise Conflict("authorization invalidated before signing")
        self._validate(state, attempt.step, attempt.payload, gates, now)
        signed = self.signer.sign(attempt.attempt_id, attempt.payload, attempt.epoch, attempt.guard_version)
        if not self.signer.verify(attempt.payload, signed):
            raise Blocked("signed bytes/hash do not bind authorized payload")
        faults.point("F5")
        return self._update_attempt(state, replace(attempt, state="SIGNED_DURABLE",
                                   raw_hex=signed.raw_hex, tx_hash=signed.tx_hash), "SIGNED_DURABLE", gates, last_observed_at=now)

    def broadcast(self, key, now):
        state = self._load(key)
        attempt = state.attempts[-1]
        if attempt.state != "SIGNED_DURABLE":
            return state  # Possibly sent bytes are never blindly resubmitted.
        if attempt.broadcast_at is not None:
            raise Blocked("possible submission cannot obtain a fresh recovery budget")
        gates = self.guards.snapshot(state.intent, now)
        if (gates.epoch, gates.authority_version) != (attempt.epoch, attempt.guard_version):
            raise Conflict("issued signature must reconcile after authority change")
        self._validate(state, attempt.step, attempt.payload, gates, now)
        signed = self.signer.lookup(attempt.attempt_id, attempt.payload.hash)
        if signed is None:
            raise Blocked('issued signature registry evidence missing')
        if signed.tx_hash != attempt.tx_hash or not self.signer.verify(attempt.payload, signed):
            raise Blocked('durable signer bytes mismatch')
        # Initialize post-submission recovery in the same durable transition as
        # the first possible send. Earlier absence checks cannot consume it;
        # retries/restarts of a possibly submitted attempt never reset it.
        attempt = replace(attempt, state="BROADCAST_ATTEMPTED", broadcast_at=now,
                          probes=0, next_probe=now)
        state = self._update_attempt(state, attempt, "BROADCAST_ATTEMPTED", gates, last_observed_at=now)
        faults.point("F7a")
        try:
            tx_hash = self.venue.broadcast(signed, attempt.epoch, attempt.guard_version)
            faults.point("F7b")
            phase = "PENDING" if tx_hash == attempt.tx_hash else "UNKNOWN"
        except Rejected as rejection:
            # Still non-terminal: reconcile ends it only after the timeout and a nonce check.
            return self._update_attempt(state, replace(attempt, state="REJECTED"), "BROADCAST_REJECTED", gates,
                                        blocked_reason="broadcast rejected: " + rejection.reason)
        except (TimeoutError, ConnectionError):
            phase = "UNKNOWN"
        # If this save fails, BROADCAST_ATTEMPTED still preserves possible submission.
        return self._update_attempt(state, replace(attempt, state=phase), phase, gates)

    def reconcile(self, key, now):
        state = self._load(key)
        if not state.attempts or state.status in TERMINAL:
            return state
        attempt = state.attempts[-1]
        if attempt.state in FINAL or attempt.tx_hash is None:
            return state
        gates = self.guards.snapshot(state.intent, now)
        # Reconciliation remains permitted after market/expiry/nonce gates fail.
        if now < state.last_observed_at or now < attempt.next_probe:
            return state
        interval = state.intent.probe_interval
        if attempt.probes >= state.intent.max_recovery_probes:
            if getattr(self.venue, 'periodic_reconciliation', False) is not True:
                return state  # Legacy fixtures retain their explicit bounded behavior.
            interval = max(60, interval)
        attempt = replace(attempt, probes=attempt.probes + 1, next_probe=now + interval)
        state = self._update_attempt(state, attempt, "RECOVERY_PROBE", gates, last_observed_at=now)
        try:
            outcome = self.venue.outcome(attempt.tx_hash)
        except (TimeoutError, ConnectionError, DependencyUnavailable):
            outcome = Outcome(attempt.tx_hash, state.intent.wallet, attempt.payload.nonce, "UNKNOWN")
            attempt = replace(attempt, probes=attempt.probes - 1,
                              dependency_failures=attempt.dependency_failures + 1,
                              next_probe=now + min(3600, 3 * 2**min(attempt.dependency_failures + 1, 10)))
            return self._update_attempt(state, attempt, 'RECOVERY_DEPENDENCY_UNAVAILABLE', gates,
                                        blocked_reason='receipt dependency unavailable; wallet barrier retained')
        except Blocked:
            return self._update_attempt(state, attempt, 'RECOVERY_BLOCKED', gates,
                                        blocked_reason='receipt evidence rejected; wallet barrier retained')
        faults.point("F8")
        absent = outcome.status == 'UNKNOWN' and outcome.sender is None and outcome.nonce is None
        if absent:
            outcome = replace(outcome, sender=state.intent.wallet, nonce=attempt.payload.nonce)
        if (outcome.tx_hash != attempt.tx_hash or outcome.sender != state.intent.wallet
                or type(outcome.nonce) is not int or outcome.nonce != attempt.payload.nonce
                or outcome.status not in {"PENDING", "UNKNOWN", "SUCCESS", "REVERT"}):
            return self._update_attempt(state, replace(attempt, state="UNKNOWN"), "OUTCOME_MISMATCH", gates,
                                        blocked_reason="unexplained transaction/nonce evidence")
        timed_out = attempt.broadcast_at is not None and now >= attempt.broadcast_at + state.intent.timeout
        if attempt.state == "REJECTED" and absent:
            # WR12 (#54): the node refused these bytes. Release only once the timeout has passed and the wallet's
            # chain nonce (latest = pending) still equals this attempt's nonce, so nothing used it; otherwise hold.
            if timed_out and type(gates.nonce) is int and gates.nonce == attempt.payload.nonce:
                rejected = replace(state, attempts=state.attempts[:-1] + (replace(attempt, state='NOT_SUBMITTED'),))
                cleanup = self._cleanup_due(rejected, now)
                return self._update_attempt(state, replace(attempt, state="NOT_SUBMITTED"), "NOT_SUBMITTED", gates,
                                            status='ACTIVE' if cleanup else 'ABORTED', abort_pending=cleanup,
                                            prepare_probes=0 if cleanup else state.prepare_probes,
                                            blocked_reason="broadcast rejected; not submitted")
            return self._update_attempt(state, attempt, "REJECTED_UNRESOLVED", gates, blocked_reason=(
                "rejected broadcast nonce unresolved; wallet barrier retained" if timed_out
                else "broadcast rejected; wallet barrier retained until timeout"))
        if outcome.status in {"PENDING", "UNKNOWN"}:
            if (outcome.status == "UNKNOWN" and attempt.state == "SIGNED_DURABLE"
                    and attempt.broadcast_at is None):
                # Absence is no evidence of submission. Keep unused bytes eligible
                # for the original, fully guarded first broadcast; never demote a
                # durable possible-send record back into this state.
                return self._update_attempt(state, attempt, "UNBROADCAST_RECONCILED", gates)
            return self._update_attempt(state, replace(attempt, state=outcome.status), outcome.status, gates,
                                        blocked_reason="transaction unresolved" if timed_out else None)
        if outcome.gas_used is not None:
            integer(outcome.gas_used, positive=True)
            if outcome.gas_used > attempt.payload.gas:
                raise Blocked("receipt gas exceeds signed limit")
        canonical_block = (isinstance(outcome.block_hash, str)
                           and re.fullmatch(r"0x[0-9a-f]{64}", outcome.block_hash)
                           and outcome.block_hash == outcome.canonical_block_hash)
        finalized = (canonical_block and outcome.finality_verified is True
                     and type(outcome.block_number) is int and outcome.block_number >= 0
                     and type(outcome.finalized_height) is int
                     and outcome.finalized_height >= outcome.block_number)
        phase = ("FINAL_" if finalized else "INCLUDED_") + ("SUCCESS" if outcome.status == "SUCCESS" else "REVERT")
        status = state.status
        if finalized and outcome.status == "REVERT":
            status = "FAILED"
        elif finalized and attempt.step == "SWAP":
            status = "COMPLETED"
        elif finalized and state.abort_pending and attempt.step in REVOKE_TOKENS:
            # A separate read in prepare confirms the zero allowance before releasing the barrier.
            status = 'ACTIVE'
        return self._update_attempt(state, replace(attempt, state=phase, included_block=outcome.block_hash,
                                                  finalized_at=now if finalized else None,
                                   gas_used=outcome.gas_used), phase, gates, status=status,
                                   prepare_probes=0 if finalized and approval_step(attempt.step) else state.prepare_probes,
                                   blocked_reason=("receipt gas unavailable; signed gas allowance retained"
                                                   if finalized and outcome.gas_used is None
                                                   else None if finalized else "canonical finality unproved"))

    def replace_transaction(self, *args, **kwargs):
        raise Blocked("same-nonce replacement is disabled")

    def reauthorize_unbroadcast(self, key, now):
        state = self._load(key)
        attempt = state.attempts[-1]
        if attempt.broadcast_at is not None or attempt.state not in {'AUTHORIZED', 'SIGNED_DURABLE'}:
            raise Blocked('possible submission cannot be reauthorized')
        gates = self.guards.snapshot(state.intent, now)
        self._validate(state, attempt.step, attempt.payload, gates, now)
        signed = self.signer.lookup(attempt.attempt_id, attempt.payload.hash)
        if attempt.state == 'SIGNED_DURABLE' and signed is None:
            raise Blocked('issued signature registry evidence missing')
        if signed is not None and not self.signer.verify(attempt.payload, signed):
            raise Blocked('recovered signature does not bind payload')
        updated = replace(attempt, epoch=gates.epoch, guard_version=gates.authority_version,
                          state='SIGNED_DURABLE' if signed else 'AUTHORIZED',
                          raw_hex=signed.raw_hex if signed else None, tx_hash=signed.tx_hash if signed else None)
        return self._update_attempt(state, updated, 'REAUTHORIZED_UNBROADCAST', gates, last_observed_at=now)

    def abort_unbroadcast(self, key, now):
        state = self._load(key)
        if state.status in TERMINAL:
            return state
        attempt = state.attempts[-1]
        if attempt.broadcast_at is not None or attempt.state not in {'AUTHORIZED', 'SIGNED_DURABLE'}:
            raise Blocked('possible submission cannot be aborted')
        if getattr(self.store, 'revokes_unbroadcast', False) is not True:
            raise Blocked('atomic registry/release revocation not implemented')
        gates = self.guards.snapshot(state.intent, now)
        if now < state.last_observed_at:
            raise Blocked('clock regression')
        cleanup = self._cleanup_due(state, now)
        return self._update_attempt(state, replace(attempt, state='ABORTED'), 'ABORTED_UNBROADCAST', gates,
                                    status='ACTIVE' if cleanup else 'ABORTED', abort_pending=cleanup,
                                    prepare_probes=0 if cleanup else state.prepare_probes, last_observed_at=now)

    def recover_signature(self, key, now):
        state = self._load(key)
        attempt = state.attempts[-1]
        if attempt.state != "AUTHORIZED":
            return state
        signed = self.signer.lookup(attempt.attempt_id, attempt.payload.hash)
        if signed is None:
            return state
        if not self.signer.verify(attempt.payload, signed):
            raise Blocked("durable signer bytes mismatch")
        gates = self.guards.snapshot(state.intent, now)
        return self._update_attempt(state, replace(attempt, state="SIGNED_DURABLE",
                                   raw_hex=signed.raw_hex, tx_hash=signed.tx_hash), "SIGNATURE_RECOVERED", gates)

    def abort_unsigned(self, key, now):
        state = self._load(key)
        if state.status in TERMINAL:
            return state
        integer(now)
        if now < state.last_observed_at:
            raise Blocked("clock regression")
        attempts = state.attempts
        if attempts and attempts[-1].state not in FINAL | {"PREPARED"}:
            raise Blocked("issued or possibly issued capability must reconcile")
        if attempts and attempts[-1].state == "PREPARED":
            attempts = attempts[:-1] + (replace(attempts[-1], state="ABORTED"),)
        gates = self.guards.snapshot(state.intent, now)
        cleanup = self._cleanup_due(state, now)
        return self._save(state, replace(state, status='ACTIVE' if cleanup else 'ABORTED',
                                        abort_pending=cleanup, attempts=attempts,
                                        prepare_probes=0 if cleanup else state.prepare_probes,
                                        last_observed_at=now), "ABORTED_UNSIGNED", gates)

    def _cleanup_due(self, state, now):
        # Never extend the parent authority. If cleanup cannot finish here, F2 handles its allowance
        # under the next independently authorized intent. Unknown submissions always retain their barrier.
        return (self.allowance_recovery and not state.abort_pending
                and now + state.intent.authority_margin < state.intent.valid_until
                and any(a.step == 'APPROVE' and a.state == 'FINAL_SUCCESS' for a in state.attempts)
                and not any(a.step == 'SWAP' and possibly_submitted(a) for a in state.attempts))


def possibly_submitted(attempt):
    """A send was attempted and is not proved absent (a rejected attempt is proved only once NOT_SUBMITTED)."""
    return attempt.broadcast_at is not None and attempt.state != "NOT_SUBMITTED"


def possible_swap_hashes(state):
    """For W06 round closure: possible-broadcast swaps only, never approvals."""
    return tuple(attempt.tx_hash for attempt in state.attempts
                 if attempt.step == "SWAP" and possibly_submitted(attempt) and attempt.tx_hash)

"""W04 execution machine and integration ports. Fake capability bundles only.

No network, credential lookup, wallet signing, scheduler or portfolio ledger.
Production adapters require W01/W02/W06 integration and W08 capability proof.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import re
from typing import Protocol

USDT = "0x55d398326f99059ff775485246999027b3197955"
NATIVE_BNB = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
BSTOCKS = frozenset({
    "0x02fca66c1d1afb4e2a7884261eb00f63598a7436",
    "0x3f53de71c126bdabae20f9cd64848d317f6c3238",
    "0xca750ef65f295bbecd685abf54e82caf297bdb61",
    "0x5b1910eaad6450e50f816082aa078c41f10c292f",
    "0x80106cb3ead06659a5ad19df39d9b4733863b9b0",
})
FINAL = frozenset({"FINAL_SUCCESS", "FINAL_REVERT", "ABORTED"})
TERMINAL = frozenset({"COMPLETED", "FAILED", "ABORTED"})


class Blocked(RuntimeError):
    """A missing prerequisite, not permission to bypass an execution guard."""


class Conflict(Blocked):
    """Stale revision, ownership or wallet-wide concurrency conflict."""


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
    raw_hex: str | None = None  # Restricted store only; omitted from audit events.
    tx_hash: str | None = None
    broadcast_at: int | None = None
    probes: int = 0
    next_probe: int = 0
    included_block: str | None = None
    gas_used: int | None = None


@dataclass(frozen=True)
class Execution:
    intent: Intent
    revision: int = 0
    status: str = "ACTIVE"
    attempts: tuple[Attempt, ...] = ()
    prepare_probes: int = 0
    blocked_reason: str | None = None
    last_observed_at: int = 0


@dataclass(frozen=True)
class Signed:
    raw_hex: str
    tx_hash: str


@dataclass(frozen=True)
class Outcome:
    tx_hash: str
    sender: str
    nonce: int
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
    if step == "APPROVE":
        if payload.to != intent.pay_token or payload.value != 0:
            raise Blocked("approve destination/value mismatch")
        if not re.fullmatch(r"0x095ea7b3[0-9a-fA-F]{128}", payload.data):
            raise Blocked("unknown approve selector/shape")
        if payload.data[10:34] != "0" * 24:
            raise Blocked("noncanonical spender padding")
        if ("0x" + payload.data[34:74].lower() != intent.router
                or int(payload.data[74:], 16) != intent.amount):
            raise Blocked("approve spender/amount mismatch")
    elif step == "SWAP":
        if payload.to != intent.router or payload.value != 0:
            raise Blocked("swap destination/value mismatch")
        economics = decoder.decode(payload)  # MUST bind decoded fields to bytes.
        for value in (economics.amount, economics.minimum_output, economics.deadline):
            integer(value, positive=True)
        if (economics.pay_token != intent.pay_token or economics.receive_token != intent.receive_token
                or economics.amount != intent.amount or economics.recipient != intent.wallet
                or economics.minimum_output < intent.minimum_output
                or not now < economics.deadline <= intent.valid_until
                or economics.native_value != payload.value):
            raise Blocked("encoded swap economics mismatch/expired")
    else:
        raise Blocked("unsupported transaction step")


class Executor:
    def __init__(self, store: Store, guards: GuardPort, venue: Venue, signer: Signer, decoder: Decoder):
        if any(getattr(port, "mode", None) != "fake" for port in (guards, venue, signer, decoder)):
            raise Blocked("only fake capability bundles are implemented")
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
        if step == "SWAP" and state.attempts:
            approval = state.attempts[0]
            if approval.state != "FINAL_SUCCESS" or gates.nonce != approval.payload.nonce + 1:
                raise Blocked("approved nonce consumption and current wallet count disagree")
        previous_cost = sum((attempt.gas_used if attempt.state in {"FINAL_SUCCESS", "FINAL_REVERT"}
                             and attempt.gas_used is not None
                             else attempt.payload.gas) * attempt.payload.gas_price
                            for attempt in state.attempts if attempt.step != step)
        if previous_cost + payload.gas * payload.gas_price > state.intent.gas_budget:
            raise Blocked("parent gas budget exceeded")

    def prepare(self, key, now):
        state = self._load(key)
        if state.status != "ACTIVE":
            return state
        if state.attempts and state.attempts[-1].state != "FINAL_SUCCESS":
            return state  # No second step while outgoing outcome is uncertain.
        integer(now)
        if now < state.last_observed_at:
            raise Blocked("clock regression")
        if state.prepare_probes >= state.intent.max_prepare_probes:
            raise Blocked("prepare probe budget exhausted")
        gates = self.guards.snapshot(state.intent, now)
        step = "SWAP" if state.attempts else "APPROVE"
        # Persist the work budget before any quote/estimate I/O; restart cannot reset it.
        state = self._save(state, replace(state, prepare_probes=state.prepare_probes + 1,
                           last_observed_at=now), "PREPARE_PROBE", gates)
        try:
            gates.check(state.intent, now)
            quote = self.venue.quote(state.intent, gates.nonce)
            self._validate(state, "SWAP", quote, gates, now)
            payload = self.venue.approve(state.intent, gates.nonce) if step == "APPROVE" else quote
            estimate = self.venue.estimate_gas(payload)
            integer(estimate, positive=True)  # Missing estimate cannot use quote fallback.
            payload = replace(payload, gas=max(payload.gas, (estimate * 6 + 4) // 5))
            self._validate(state, step, payload, gates, now)
            if step == "SWAP" and payload.to != state.intent.router:
                raise Blocked("requoted router differs from approved spender")
        except Blocked as error:
            return self._save(state, replace(state, blocked_reason=str(error)), "PREPARE_BLOCKED", gates)
        except (TimeoutError, ConnectionError):
            return self._save(state, replace(state, blocked_reason="quote/gas dependency unavailable"),
                              "PREPARE_BLOCKED", gates)
        attempt = Attempt(digest([key, step]), step, "PREPARED", payload, gates.epoch, gates.state_version)
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
                                   guard_version=gates.state_version), "AUTHORIZED", gates, last_observed_at=now)

    def sign(self, key, now):
        state = self._load(key)
        attempt = state.attempts[-1]
        if attempt.state != "AUTHORIZED":
            return state
        gates = self.guards.snapshot(state.intent, now)
        if (gates.epoch, gates.state_version) != (attempt.epoch, attempt.guard_version):
            raise Conflict("authorization invalidated before signing")
        self._validate(state, attempt.step, attempt.payload, gates, now)
        signed = self.signer.sign(attempt.attempt_id, attempt.payload, attempt.epoch, attempt.guard_version)
        if not self.signer.verify(attempt.payload, signed):
            raise Blocked("signed bytes/hash do not bind authorized payload")
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
        if (gates.epoch, gates.state_version) != (attempt.epoch, attempt.guard_version):
            raise Conflict("issued signature must reconcile after authority change")
        self._validate(state, attempt.step, attempt.payload, gates, now)
        # Initialize post-submission recovery in the same durable transition as
        # the first possible send. Earlier absence checks cannot consume it;
        # retries/restarts of a possibly submitted attempt never reset it.
        attempt = replace(attempt, state="BROADCAST_ATTEMPTED", broadcast_at=now,
                          probes=0, next_probe=now)
        state = self._update_attempt(state, attempt, "BROADCAST_ATTEMPTED", gates, last_observed_at=now)
        try:
            tx_hash = self.venue.broadcast(Signed(attempt.raw_hex, attempt.tx_hash), attempt.epoch, attempt.guard_version)
            phase = "PENDING" if tx_hash == attempt.tx_hash else "UNKNOWN"
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
        if attempt.probes >= state.intent.max_recovery_probes:
            return state  # Budget exhaustion never releases issued capabilities.
        attempt = replace(attempt, probes=attempt.probes + 1, next_probe=now + state.intent.probe_interval)
        state = self._update_attempt(state, attempt, "RECOVERY_PROBE", gates, last_observed_at=now)
        try:
            outcome = self.venue.outcome(attempt.tx_hash)
        except (TimeoutError, ConnectionError):
            outcome = Outcome(attempt.tx_hash, state.intent.wallet, attempt.payload.nonce, "UNKNOWN")
        if (outcome.tx_hash != attempt.tx_hash or outcome.sender != state.intent.wallet
                or type(outcome.nonce) is not int or outcome.nonce != attempt.payload.nonce
                or outcome.status not in {"PENDING", "UNKNOWN", "SUCCESS", "REVERT"}):
            return self._update_attempt(state, replace(attempt, state="UNKNOWN"), "OUTCOME_MISMATCH", gates,
                                        blocked_reason="unexplained transaction/nonce evidence")
        timed_out = attempt.broadcast_at is not None and now >= attempt.broadcast_at + state.intent.timeout
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
        return self._update_attempt(state, replace(attempt, state=phase, included_block=outcome.block_hash,
                                   gas_used=outcome.gas_used), phase, gates, status=status,
                                   blocked_reason=("receipt gas unavailable; signed gas allowance retained"
                                                   if finalized and outcome.gas_used is None
                                                   else None if finalized else "canonical finality unproved"))

    def replace_transaction(self, *args, **kwargs):
        raise Blocked("same-nonce replacement is disabled")

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
        attempts = state.attempts
        if attempts and attempts[-1].state not in FINAL | {"PREPARED"}:
            raise Blocked("issued or possibly issued capability must reconcile")
        if attempts and attempts[-1].state == "PREPARED":
            attempts = attempts[:-1] + (replace(attempts[-1], state="ABORTED"),)
        gates = self.guards.snapshot(state.intent, now)
        return self._save(state, replace(state, status="ABORTED", attempts=attempts), "ABORTED_UNSIGNED", gates)


def possible_swap_hashes(state):
    """For W06 round closure: possible-broadcast swaps only, never approvals."""
    return tuple(attempt.tx_hash for attempt in state.attempts
                 if attempt.step == "SWAP" and attempt.broadcast_at is not None and attempt.tx_hash)

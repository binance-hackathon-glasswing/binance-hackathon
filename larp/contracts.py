"""Offline policy boundary for IDEA-021 ENG-02, not an order authorization layer.

Canonical JSON uses sorted keys, UTF-8 and integer-only numeric values. Policy
weights are exact fractions. Durability, independent risk and process isolation
are separate requirements; these types alone do not provide those capabilities.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from fractions import Fraction
import hashlib
import json


class ContractError(ValueError):
    """Input violates the policy boundary contract."""


def _identifier(value: str) -> None:
    if type(value) is not str or not value or value.strip() != value:
        raise ContractError("Identifiers must be nonempty, trimmed strings")


def _counter(value: int) -> None:
    if type(value) is not int or value < 0:
        raise ContractError("Counters must be nonnegative integers")


def _utc(value: datetime) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError("Timestamps require an explicit timezone")
    return value.astimezone(timezone.utc)


def _json_value(value: object) -> None:
    if value is None or type(value) in (str, int, bool):
        return
    if type(value) is list:
        for item in value:
            _json_value(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _json_value(item)
        return
    raise ContractError("Documents allow JSON objects, lists, strings, integers, booleans and null only")


def _encode(value: dict) -> bytes:
    if type(value) is not dict:
        raise ContractError("Document root must be an object")
    _json_value(value)
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise ContractError("Document is not valid UTF-8 JSON") from exc


@dataclass(frozen=True, slots=True)
class Document:
    """Immutable canonical bytes; read() returns a detached mutable copy."""

    payload: bytes

    def __post_init__(self) -> None:
        if type(self.payload) is not bytes:
            raise ContractError("Document payload must be immutable bytes")
        try:
            if _encode(json.loads(self.payload)) != self.payload:
                raise ContractError("Document bytes are not canonical")
        except (ValueError, UnicodeError) as exc:
            raise ContractError("Invalid canonical document") from exc

    @classmethod
    def from_dict(cls, value: dict) -> "Document":
        return cls(_encode(value))

    def read(self) -> dict:
        return json.loads(self.payload)

    def digest(self, domain: str) -> str:
        _identifier(domain)
        return hashlib.sha256(domain.encode("utf-8") + b"\x00" + self.payload).hexdigest()


@dataclass(frozen=True, slots=True)
class PolicyState:
    run_id: str
    policy_id: str
    schema: str
    version: int
    data: Document

    def __post_init__(self) -> None:
        for value in (self.run_id, self.policy_id, self.schema):
            _identifier(value)
        _counter(self.version)
        if type(self.data) is not Document:
            raise ContractError("Policy state requires a canonical document")

    def record(self) -> dict:
        return {"run_id": self.run_id, "policy_id": self.policy_id, "schema": self.schema,
                "version": self.version, "data": self.data.read()}


@dataclass(frozen=True, slots=True)
class DecisionSnapshot:
    run_id: str
    wallet_id: str
    engine_version: str
    policy_profile_hash: str
    event_sequence: int
    observed_at: datetime
    universe: tuple[str, ...]
    policy_state: PolicyState
    context: Document

    def __post_init__(self) -> None:
        for value in (self.run_id, self.wallet_id, self.engine_version):
            _identifier(value)
        if (type(self.policy_profile_hash) is not str or len(self.policy_profile_hash) != 64
                or any(c not in "0123456789abcdef" for c in self.policy_profile_hash)):
            raise ContractError("Policy profile requires a lowercase SHA-256 hash")
        _counter(self.event_sequence)
        object.__setattr__(self, "observed_at", _utc(self.observed_at))
        if type(self.universe) is not tuple or not self.universe:
            raise ContractError("Universe must be a nonempty immutable tuple")
        for symbol in self.universe:
            _identifier(symbol)
        if len(set(self.universe)) != len(self.universe):
            raise ContractError("Duplicate universe symbol")
        object.__setattr__(self, "universe", tuple(sorted(self.universe)))
        if type(self.policy_state) is not PolicyState or self.policy_state.run_id != self.run_id:
            raise ContractError("Snapshot and policy state must belong to the same run")
        if type(self.context) is not Document:
            raise ContractError("Snapshot context requires a canonical document")

    @property
    def snapshot_id(self) -> str:
        return Document.from_dict({
            "schema": "larp.snapshot.v1", "run_id": self.run_id, "wallet_id": self.wallet_id,
            "engine_version": self.engine_version, "policy_profile_hash": self.policy_profile_hash,
            "event_sequence": self.event_sequence, "observed_at": self.observed_at.isoformat(),
            "universe": list(self.universe), "policy_state": self.policy_state.record(),
            "context": self.context.read(),
        }).digest("larp.snapshot.v1")


class TargetKind(str, Enum):
    KEEP_QUANTITY = "KEEP_QUANTITY"
    TARGET_WEIGHT = "TARGET_WEIGHT"
    EXIT = "EXIT"


@dataclass(frozen=True, slots=True)
class Target:
    symbol: str
    kind: TargetKind
    reason: str
    weight: Fraction | None = None

    def __post_init__(self) -> None:
        _identifier(self.symbol)
        _identifier(self.reason)
        if type(self.kind) is not TargetKind:
            raise ContractError("Unknown target instruction")
        if self.kind is TargetKind.TARGET_WEIGHT:
            if type(self.weight) is not Fraction or not 0 <= self.weight <= 1:
                raise ContractError("Weight must be an exact rational in [0, 1]")
        elif self.weight is not None:
            raise ContractError("KEEP_QUANTITY and EXIT cannot carry a weight")

    def record(self) -> dict:
        return {"symbol": self.symbol, "kind": self.kind.value, "reason": self.reason,
                "weight": None if self.weight is None else [self.weight.numerator, self.weight.denominator]}


@dataclass(frozen=True, slots=True)
class Proposal:
    snapshot_id: str
    policy_id: str
    valid_until: datetime
    targets: tuple[Target, ...]
    next_policy_state: PolicyState

    def __post_init__(self) -> None:
        _identifier(self.snapshot_id)
        _identifier(self.policy_id)
        object.__setattr__(self, "valid_until", _utc(self.valid_until))
        if type(self.targets) is not tuple or any(type(t) is not Target for t in self.targets):
            raise ContractError("Targets must be an immutable tuple of Target values")
        if type(self.next_policy_state) is not PolicyState:
            raise ContractError("Next state requires PolicyState")

    @property
    def proposal_id(self) -> str:
        return Document.from_dict({
            "schema": "larp.proposal.v1", "snapshot_id": self.snapshot_id,
            "policy_id": self.policy_id, "valid_until": self.valid_until.isoformat(),
            "targets": [t.record() for t in sorted(self.targets, key=lambda t: t.symbol)],
            "next_policy_state": self.next_policy_state.record(),
        }).digest("larp.proposal.v1")


def validate_proposal(snapshot: DecisionSnapshot, proposal: Proposal, *, now: datetime) -> tuple[Target, ...]:
    """Return explicit instructions for all names, without mutating engine state.

    The caller must supply the CURRENT snapshot and time. The future storage
    compare-and-set must prevent races after validation. A valid proposal is not
    a fill, risk approval, reservation, durable commit or execution authorization.
    """
    now = _utc(now)
    if proposal.snapshot_id != snapshot.snapshot_id:
        raise ContractError("Stale or mismatched snapshot")
    current, following = snapshot.policy_state, proposal.next_policy_state
    if proposal.policy_id != current.policy_id:
        raise ContractError("Wrong policy")
    if (following.run_id, following.policy_id, following.schema, following.version) != (
            current.run_id, current.policy_id, current.schema, current.version + 1):
        raise ContractError("Stale or mismatched next policy state")
    if now < snapshot.observed_at or proposal.valid_until <= now:
        raise ContractError("Future snapshot or expired proposal")
    targets = {target.symbol: target for target in proposal.targets}
    if len(targets) != len(proposal.targets):
        raise ContractError("Duplicate target symbol")
    if targets.keys() - set(snapshot.universe):
        raise ContractError("Unknown target symbol")
    if sum((t.weight for t in proposal.targets if t.weight is not None), Fraction(0)) > 1:
        raise ContractError("Explicit weights exceed one")
    return tuple(targets.get(symbol, Target(symbol, TargetKind.KEEP_QUANTITY, "NO_TARGET"))
                 for symbol in snapshot.universe)

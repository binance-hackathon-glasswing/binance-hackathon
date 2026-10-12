"""Shared, additive development ports. Implementations receive immutable values.

No port alone grants signing authority. See docs/build/PARALLEL_BUILD.md.
"""

from datetime import datetime
import re
from typing import Protocol

from larp.contracts import ContractError, DecisionSnapshot, Document, PolicyState, Proposal


class Assessor(Protocol):
    def assess(self, request: Document) -> Document: ...


class Market(Protocol):
    def observe(self, request: Document) -> Document: ...


class Policy(Protocol):
    def decide(self, snapshot: DecisionSnapshot, state: PolicyState) -> Proposal: ...


class Planner(Protocol):
    def plan(self, snapshot: DecisionSnapshot, proposal_or_none: Proposal | None) -> Document: ...


class Execution(Protocol):
    def advance(self, state: Document, observation: Document) -> Document: ...


class Store(Protocol):
    def commit(self, batch: Document) -> Document: ...


class Receiver(Protocol):
    def deliver(self, event: Document) -> Document: ...


# ---------------------------------------------------------------------------------------------------------
# Deployment interfaces I3, I4, I5, I7 (docs/build/DEPLOYMENT_BUILD.md, IDEA-042 item 1). Each validator is the
# runtime side's contract; the consumer's own validator (Isaac's Intent.validate, Keith's advance_accounting)
# still applies on top. A change needs both owners' agreement, recorded in both build records.
# ---------------------------------------------------------------------------------------------------------

BSTOCKS = frozenset(("NVDAB", "GOOGLB", "SKHYB", "TSLAB", "MSFTB"))
TX_HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")
DECIMAL = re.compile(r"^(0|[1-9][0-9]*)(\.[0-9]*[1-9])?$")
INTENT_KINDS = ("BSTOCK_TRADE", "GAS_TOP_UP")  # I7: a gas top-up is its own round with exactly one USDT -> BNB intent
OBSERVATION_KINDS = ("BROADCAST_ATTEMPTED", "APPROVAL", "FILL", "REVERT", "NOT_SUBMITTED")
FINAL_KINDS = ("APPROVAL", "FILL", "REVERT", "NOT_SUBMITTED")
# Accounting fields: a broadcast attempt must not carry them (I4 boundary 1).
ACCOUNTING_FIELDS = ("token_units", "cash_units", "fee_units", "gas_bnb_units", "gas_value_units")
ORIGINS = ("SCRIPTED_FAKE", "EXECUTION_RECONCILER")


def _int(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ContractError(f"{name} must be an integer >= {minimum}")
    return value


def _text(value, name):
    if type(value) is not str or not value:
        raise ContractError(f"{name} must be a non-empty string")
    return value


def _instant(value, name):
    try:
        parsed = datetime.fromisoformat(_text(value, name).replace("Z", "+00:00"))
    except ValueError:
        raise ContractError(f"{name} must be an ISO-8601 instant") from None
    if parsed.tzinfo is None:
        raise ContractError(f"{name} needs a timezone")
    return parsed


def decimal_string(units: int, decimals: int) -> str:
    """Exact decimal string of integer base units; the only amount form the round log and venue accept."""
    _int(units, "units"); _int(decimals, "decimals")
    whole, frac = divmod(units, 10 ** decimals)
    if not decimals or not frac:
        return str(whole)
    return f"{whole}.{str(frac).rjust(decimals, '0').rstrip('0')}"


def validate_execution_request(command: dict) -> dict:
    """I3: one `EXECUTION_REQUEST` command as the coordinator commits it (Keegan -> Isaac).

    Envelope: command_id == payload.intent_id, kind, round_id, decision_id == payload.decision_id, expires_ms.
    Payload: Keith's exact-input intent plus the runtime's decision_id, expires_ms and amount (A10: BUY amount is
    the USDT paid at money scale 6, SELL amount the tokens sold at the token's decimals). I7: the intent's `kind` is
    BSTOCK_TRADE (the default when absent) or GAS_TOP_UP, the only intent that may buy BNB, and only with USDT. Same
    field and values as Keith's planner and Isaac's map_command (IDEA-042 §4 X3).
    """
    if type(command) is not dict or command.get("kind") != "EXECUTION_REQUEST":
        raise ContractError("Expected an EXECUTION_REQUEST command")
    p = command.get("payload")
    if type(p) is not dict:
        raise ContractError("Command payload must be an object")
    for key in ("command_id", "round_id", "decision_id"):
        _text(command.get(key), key)
    for key in ("intent_id", "decision_id", "quote_id"):
        _text(p.get(key), "payload." + key)
    if command["command_id"] != p["intent_id"] or command["decision_id"] != p["decision_id"]:
        raise ContractError("Command identity differs from its intent")
    if _int(command.get("expires_ms"), "expires_ms", 1) != p.get("expires_ms"):
        raise ContractError("Command expiry differs from its intent")
    kind = p.get("kind", "BSTOCK_TRADE")
    if kind not in INTENT_KINDS or "purpose" in p:
        raise ContractError("Unknown intent kind")
    side, symbol = p.get("side"), p.get("symbol")
    if p.get("amount_kind") != "EXACT_IN" or type(p.get("mandatory")) is not bool:
        raise ContractError("Intent must be exact-input with an explicit mandatory flag")
    for key in ("token_units", "pay_units", "min_receive_units"):
        _int(p.get(key), "payload." + key, 1)
    for key in ("cash_units", "fee_units", "gas_bnb_units"):
        _int(p.get(key), "payload." + key)
    _int(p.get("decimals"), "payload.decimals"); _int(p.get("receive_decimals"), "payload.receive_decimals")
    _instant(p.get("quote_expiry"), "payload.quote_expiry")
    if kind == "GAS_TOP_UP":
        if (symbol, side, p.get("pay_asset")) != ("BNB", "BUY", "USDT"):
            raise ContractError("A gas top-up is exactly one USDT -> BNB buy")
    elif symbol not in BSTOCKS or side not in ("BUY", "SELL"):
        raise ContractError("Trade intents are bStock BUY/SELL only")
    elif p.get("pay_asset") != ("USDT" if side == "BUY" else symbol):
        raise ContractError("Pay asset does not match the side")
    if side == "SELL" and p["pay_units"] != p["token_units"]:
        raise ContractError("A sell pays exactly its token quantity")
    expected = decimal_string(p["pay_units"], 6) if side == "BUY" else decimal_string(p["token_units"], p["decimals"])
    if p.get("amount") != expected or not DECIMAL.fullmatch(p["amount"]):
        raise ContractError("Amount must be the exact decimal of the paid units (A10)")
    return command


def validate_execution_observation(observation: dict) -> dict:
    """I4: `ExecutionObservation.v1` (Isaac -> Keegan's settlement reducer; final facts also -> Keith's accounting).

    Two boundaries. BROADCAST_ATTEMPTED carries the step and its tx hash only and never accounting fields.
    Final facts (`settlement: FINAL`, receipt evidence `block_hash` + `canonical: true`) carry gas for every kind and
    fill amounts for FILL. `intent_terminal` ends the intent; `round_terminal` is the execution owner's attestation
    that every command of the round is terminal. NOT_SUBMITTED (proposed 2026-10-11, needs Isaac's agreement) ends an
    intent that was never broadcast (expired or refused before signing): no tx, no gas, reservations released, and an
    optional `reason` that the round log shows in `output.aborted`.
    """
    o = observation
    if type(o) is not dict or o.get("schema") != "ExecutionObservation.v1":
        raise ContractError("Expected ExecutionObservation.v1")
    for key in ("run_id", "wallet_id", "round_id", "intent_id", "event_id"):
        _text(o.get(key), key)
    kind = o.get("kind")
    if kind not in OBSERVATION_KINDS:
        raise ContractError("Unknown execution observation kind")
    _instant(o.get("observed_at"), "observed_at")
    if kind == "BROADCAST_ATTEMPTED":
        if o.get("step") not in ("approve", "swap") or not TX_HASH.fullmatch(o.get("tx_hash") or ""):
            raise ContractError("A broadcast attempt names its step and transaction hash")
        if any(key in o for key in ACCOUNTING_FIELDS + ("settlement",)):
            raise ContractError("A broadcast attempt cannot carry settlement or accounting facts")
        return o
    if o.get("settlement") != "FINAL" or o.get("origin") not in ORIGINS:
        raise ContractError("Only final facts from the execution reconciler change accounting")
    if type(o.get("intent_terminal")) is not bool or type(o.get("round_terminal")) is not bool:
        raise ContractError("Final facts state intent_terminal and round_terminal")
    if o["round_terminal"] and not o["intent_terminal"]:
        raise ContractError("A round cannot be terminal while this intent is not")
    if kind == "NOT_SUBMITTED":
        if not o["intent_terminal"] or any(key in o for key in ACCOUNTING_FIELDS + ("tx_hash",)):
            raise ContractError("NOT_SUBMITTED is terminal and has no transaction or gas")
        if "reason" in o:
            _text(o["reason"], "reason")
        return o
    if not TX_HASH.fullmatch(o.get("tx_hash") or "") or not TX_HASH.fullmatch(o.get("block_hash") or "") \
            or o.get("canonical") is not True:
        raise ContractError("Final facts need the tx hash and canonical receipt evidence")
    _int(o.get("gas_bnb_units"), "gas_bnb_units"); _int(o.get("gas_value_units"), "gas_value_units")
    if kind == "APPROVAL" and o["intent_terminal"]:
        raise ContractError("An approval never ends its intent")
    if kind == "FILL":
        if o.get("side") not in ("BUY", "SELL") or type(o.get("symbol")) is not str or not o["intent_terminal"]:
            raise ContractError("A fill names symbol and side and ends its intent")
        _int(o.get("token_units"), "token_units", 1); _int(o.get("cash_units"), "cash_units")
        _int(o.get("fee_units"), "fee_units")
    return o


class RoundLogBuilder(Protocol):
    """I5: one ai-seeds round log per decision round (DR-07). `record` is the durable round record; the result is an
    `AuditEvent.v1` that `larp.audit.protocol.verify_event` accepts. Orders come only from executed intents."""

    def build(self, record: dict, *, round_id: str, status: str, now_ms: int, head: str) -> Document: ...

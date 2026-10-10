"""Shared helpers for the evidence path: hashing, canonical documents and authority checks.

Nothing here opens a network connection, reads a credential or can express a trade.
"""

from fractions import Fraction
import hashlib

from larp.contracts import ContractError, Document

QUALITY = ("VALID", "MISSING", "STALE", "UNKNOWN", "SYNTHETIC")

# Keys that would give an assessment, tool or model output trade or signing authority.
FORBIDDEN_KEYS = frozenset({
    "order", "orders", "side", "target", "targets", "buy", "sell", "action_size", "tx_hash",
    "signature", "signed_tx", "broadcast", "private_key", "mnemonic", "wallet_key",
    "ai_seeds_secret", "weight", "weights", "quantity",
})


class IntelligenceError(ContractError):
    """Input or output violates the evidence-path contract."""


def sha256_hex(data: bytes) -> str:
    if type(data) is not bytes:
        raise IntelligenceError("Hash input must be bytes")
    return hashlib.sha256(data).hexdigest()


def is_hash(value: object) -> bool:
    return (type(value) is str and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def require_hash(value: object, what: str) -> str:
    if not is_hash(value):
        raise IntelligenceError(f"{what} must be a lowercase SHA-256 hex digest")
    return value


def require_ms(value: object, what: str) -> int:
    if type(value) is not int or value < 0:
        raise IntelligenceError(f"{what} must be a nonnegative integer of UTC epoch milliseconds")
    return value


def require_text(value: object, what: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise IntelligenceError(f"{what} must be a nonempty trimmed string")
    return value


def digest(domain: str, value: dict) -> str:
    """Domain-separated SHA-256 of the canonical document form of `value`."""
    return Document.from_dict(value).digest(domain)


def frac(value: Fraction) -> list:
    if type(value) is not Fraction:
        raise IntelligenceError("Exact values must be Fraction instances")
    return [value.numerator, value.denominator]


def unfrac(pair: object) -> Fraction:
    if (type(pair) is not list or len(pair) != 2 or any(type(v) is not int for v in pair)
            or pair[1] <= 0):
        raise IntelligenceError("Exact values are [numerator, positive denominator] integer pairs")
    return Fraction(pair[0], pair[1])


def forbidden_key_paths(value: object, path: str = "$") -> list:
    """Every object key, at any depth, that names a trade/signing field."""
    found = []
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is str and key.lower() in FORBIDDEN_KEYS:
                found.append(f"{path}.{key}")
            found.extend(forbidden_key_paths(item, f"{path}.{key}"))
    elif type(value) is list:
        for index, item in enumerate(value):
            found.extend(forbidden_key_paths(item, f"{path}[{index}]"))
    return found


def assert_no_trade_fields(value: dict, what: str) -> None:
    paths = forbidden_key_paths(value)
    if paths:
        raise IntelligenceError(f"{what} cannot carry trade or signing fields: {', '.join(paths)}")

"""Issuer registry: which SEC filer and which forms belong to each eligible token.

An issuer is the filing entity. A security is one listed instrument of that issuer
(e.g. Korean common shares and a US listing of SK hynix are two securities). A token is
the on-chain bStock. These are never interchangeable: the registry stores no conversion
ratio unless one is verified, and the token -> underlying security link is recorded as
UNVERIFIED until the organisers or the API establish it (F-95: `referencePrice` "is a
derived per-share reference price, not an official stock market quote").
"""

from dataclasses import dataclass
from fractions import Fraction

from larp.intelligence.common import IntelligenceError, require_text

DOMESTIC_FORMS = {"8-K": "CURRENT", "8-K/A": "CURRENT", "10-Q": "QUARTERLY", "10-Q/A": "QUARTERLY",
                  "10-K": "ANNUAL", "10-K/A": "ANNUAL"}
FOREIGN_PRIVATE_FORMS = {"6-K": "CURRENT", "6-K/A": "CURRENT", "20-F": "ANNUAL", "20-F/A": "ANNUAL"}
FORMS_BY_CLASS = {"DOMESTIC": DOMESTIC_FORMS, "FOREIGN_PRIVATE": FOREIGN_PRIVATE_FORMS}
STATUSES = ("VERIFIED", "UNVERIFIED")


@dataclass(frozen=True, slots=True)
class Security:
    security_id: str
    kind: str
    currency: str
    ratio_to_common: Fraction | None
    ratio_status: str

    def record(self) -> dict:
        ratio = None if self.ratio_to_common is None else [self.ratio_to_common.numerator,
                                                           self.ratio_to_common.denominator]
        return {"security_id": self.security_id, "kind": self.kind, "currency": self.currency,
                "ratio_to_common": ratio, "ratio_status": self.ratio_status}


@dataclass(frozen=True, slots=True)
class IssuerEntry:
    issuer_id: str
    token: str
    cik: int
    entity_name: str
    filer_class: str
    reporting_currency: str
    securities: tuple
    token_underlying: str | None
    token_underlying_status: str

    @property
    def forms(self) -> dict:
        return FORMS_BY_CLASS[self.filer_class]

    def form_class(self, form: str) -> str | None:
        """CURRENT / QUARTERLY / ANNUAL for an expected form, None for any other form."""
        return self.forms.get((form or "").strip().upper())

    def security(self, security_id: str) -> Security | None:
        return next((s for s in self.securities if s.security_id == security_id), None)


class IssuerRegistry:
    def __init__(self, entries: tuple, provenance: dict):
        tokens, ciks, ids = set(), set(), set()
        for entry in entries:
            if entry.token in tokens or entry.cik in ciks or entry.issuer_id in ids:
                raise IntelligenceError("Each token, CIK and issuer ID must appear once")
            tokens.add(entry.token), ciks.add(entry.cik), ids.add(entry.issuer_id)
        self.entries = tuple(sorted(entries, key=lambda e: e.issuer_id))
        self.provenance = provenance

    @classmethod
    def from_dict(cls, value: dict) -> "IssuerRegistry":
        if value.get("schema") != "IssuerRegistry.v1":
            raise IntelligenceError("Unknown issuer registry schema")
        entries = []
        for raw in value["issuers"]:
            if raw["filer_class"] not in FORMS_BY_CLASS:
                raise IntelligenceError("Unknown filer class")
            if type(raw["cik"]) is not int or raw["cik"] <= 0:
                raise IntelligenceError("CIK must be a positive integer")
            securities = []
            for s in raw["securities"]:
                if s["ratio_status"] not in STATUSES:
                    raise IntelligenceError("Unknown ratio status")
                ratio = s.get("ratio_to_common")
                if (ratio is None) != (s["ratio_status"] == "UNVERIFIED"):
                    raise IntelligenceError("A ratio is present exactly when it is verified")
                securities.append(Security(require_text(s["security_id"], "security_id"), s["kind"],
                                           s["currency"], None if ratio is None else Fraction(*ratio),
                                           s["ratio_status"]))
            underlying = raw["token_underlying"]
            if underlying["status"] not in STATUSES:
                raise IntelligenceError("Unknown token-underlying status")
            if underlying["security_id"] is not None and underlying["security_id"] not in {
                    s.security_id for s in securities}:
                raise IntelligenceError("Token underlying must be one of the issuer's securities")
            if underlying["status"] == "VERIFIED" and underlying["security_id"] is None:
                raise IntelligenceError("A verified token mapping needs a security")
            entries.append(IssuerEntry(require_text(raw["issuer_id"], "issuer_id"), require_text(raw["token"], "token"),
                                       raw["cik"], require_text(raw["entity_name"], "entity_name"), raw["filer_class"],
                                       raw["reporting_currency"], tuple(securities), underlying["security_id"],
                                       underlying["status"]))
        return cls(tuple(entries), value.get("provenance", {}))

    def by_token(self, token: str) -> IssuerEntry:
        for entry in self.entries:
            if entry.token == token:
                return entry
        raise IntelligenceError(f"Token {token!r} has no registered issuer")

    def by_issuer(self, issuer_id: str) -> IssuerEntry:
        for entry in self.entries:
            if entry.issuer_id == issuer_id:
                return entry
        raise IntelligenceError(f"Issuer {issuer_id!r} is not registered")

    def by_cik(self, cik: int) -> IssuerEntry:
        for entry in self.entries:
            if entry.cik == cik:
                return entry
        raise IntelligenceError(f"CIK {cik} is not registered")

    def instrument_relation(self, a: str, b: str) -> str:
        """SAME, SAME_ISSUER_DIFFERENT_INSTRUMENT or UNRELATED; tokens count as instruments."""
        if a == b:
            return "SAME"
        owners = []
        for x in (a, b):
            owner = next((e.issuer_id for e in self.entries
                          if x == e.token or e.security(x) is not None), None)
            owners.append(owner)
        if owners[0] is not None and owners[0] == owners[1]:
            return "SAME_ISSUER_DIFFERENT_INSTRUMENT"
        return "UNRELATED"

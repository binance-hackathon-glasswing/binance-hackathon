"""SourceRegister.v1: which free sources exist, which are enabled, and on what rights basis (AC-D01)."""

from dataclasses import dataclass
from pathlib import Path
import json

from larp.intelligence.common import IntelligenceError, sha256_hex

CONFIG = Path(__file__).resolve().parents[2] / "config" / "sources" / "sources.v1.json"
FORMATS = ("RSS", "FR_DOCUMENTS_JSON", "FR_PUBLIC_INSPECTION_JSON", "DOJ_PRESS_JSON", "NONE")
REQUIRED_RIGHTS = ("basis", "licence_id", "terms_url", "terms_checked", "attribution", "exclusions")


@dataclass(frozen=True, slots=True)
class Source:
    source_id: str
    publisher: str
    original_publisher: str
    kind: str
    actor: str
    enabled: bool
    status_reason: str
    format: str
    listing_url: str | None
    allow: tuple
    rights: dict
    limits: dict
    requires_user_agent: str | None


def load_register(path: Path = CONFIG) -> tuple:
    """(sources by id, issuer aliases, register sha256). Enabled sources must carry a complete rights basis."""
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if data.get("schema") != "SourceRegister.v1":
        raise IntelligenceError("Unknown source register schema")
    sources = {}
    for s in data["sources"]:
        if s["format"] not in FORMATS:
            raise IntelligenceError(f"Unknown source format for {s['source_id']}")
        if s["enabled"]:
            missing = [k for k in REQUIRED_RIGHTS if not s["rights"].get(k)]
            if missing or s["rights"]["basis"] == "NOT_ESTABLISHED" or not s["allow"] or not s["listing_url"]:
                raise IntelligenceError(f"Enabled source {s['source_id']} lacks rights basis or allowlist: {missing}")
            if s.get("body_retrieval") is False and s["kind"] != "DISCOVERY_METADATA":
                raise IntelligenceError("Only discovery metadata may disable body retrieval")
        if s["kind"] == "DISCOVERY_METADATA" and s["enabled"]:
            raise IntelligenceError("Discovery metadata sources are not ingested as evidence in this build")
        sources[s["source_id"]] = Source(
            s["source_id"], s["publisher"], s.get("original_publisher", s["publisher"]), s["kind"], s["actor"],
            s["enabled"], s["status_reason"], s["format"], s["listing_url"], tuple(dict(a) for a in s["allow"]),
            dict(s["rights"]), dict(s["limits"]), s.get("requires_user_agent"))
    return sources, {k: list(v) for k, v in data["issuer_aliases"].items()}, sha256_hex(raw)

"""SourceRegister.v1: which free sources exist, which are enabled, and on what rights basis (AC-D01)."""

from dataclasses import dataclass
from pathlib import Path
import json
import os

from larp.intelligence.common import IntelligenceError, is_hash, sha256_hex

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
        evidence = s["rights"].get("terms_evidence_sha256")
        if evidence is not None and not is_hash(evidence):
            raise IntelligenceError(f"terms_evidence_sha256 of {s['source_id']} is not a SHA-256")
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


def load_edgar_terms(path: Path = CONFIG) -> dict:
    """The EDGAR filings path's rights entry (`edgar` in the register): source_id, terms URL, capture date and hash."""
    data = json.loads(Path(path).read_bytes().decode("utf-8"))
    edgar = data.get("edgar")
    if type(edgar) is not dict or edgar.get("source_id") != "sec-edgar" or type(edgar.get("rights")) is not dict:
        raise IntelligenceError("The source register lacks the EDGAR rights entry")
    rights = edgar["rights"]
    missing = [k for k in REQUIRED_RIGHTS if not rights.get(k)]
    evidence = rights.get("terms_evidence_sha256")
    if missing or (evidence is not None and not is_hash(evidence)):
        raise IntelligenceError(f"EDGAR rights entry incomplete or malformed: {missing}")
    return {"source_id": "sec-edgar", "requires_user_agent": edgar.get("requires_user_agent"), **rights}


def live_preflight(sources: dict, env: dict, edgar: dict | None = None) -> list:
    """Reasons live ingestion must not start (IDEA-041 AC-1.1, DR-12); empty means it may start.

    Every enabled source needs a dated terms capture (`terms_evidence_sha256`, GAP-23), and so does the EDGAR
    filings path (`edgar`, default: the committed register's entry); a source that needs a User-Agent needs a real
    one with contact details (SEC fair access; no placeholder); EDGAR filings always need the SEC User-Agent;
    `LARP_ARTIFACT_ROOT` must be an absolute, writable directory outside the repository.
    """
    from larp.intelligence.config import sec_user_agent
    reasons = []
    for source in sorted(sources.values(), key=lambda x: x.source_id):
        if not source.enabled:
            continue
        if not source.rights.get("terms_evidence_sha256"):
            reasons.append(f"TERMS_EVIDENCE_MISSING:{source.source_id}")
        if source.requires_user_agent and not env.get(source.requires_user_agent):
            reasons.append(f"USER_AGENT_MISSING:{source.source_id}:{source.requires_user_agent}")
    try:
        edgar = load_edgar_terms() if edgar is None else edgar
    except IntelligenceError:
        reasons.append("TERMS_EVIDENCE_MISSING:sec-edgar")
    else:
        if not edgar.get("terms_evidence_sha256"):
            reasons.append("TERMS_EVIDENCE_MISSING:sec-edgar")
    try:
        sec_user_agent(env)
    except IntelligenceError:
        reasons.append("SEC_USER_AGENT_INVALID:LARP_SEC_USER_AGENT")
    root = env.get("LARP_ARTIFACT_ROOT")
    repo = Path(__file__).resolve().parents[2]
    if not root:
        reasons.append("ARTIFACT_ROOT_MISSING:LARP_ARTIFACT_ROOT")
    elif not Path(root).is_absolute():
        reasons.append("ARTIFACT_ROOT_NOT_ABSOLUTE")
    else:
        path = Path(root).resolve()
        if path == repo or repo in path.parents:
            reasons.append("ARTIFACT_ROOT_INSIDE_REPOSITORY")
        elif path.exists() and not (path.is_dir() and os.access(path, os.W_OK)):
            reasons.append("ARTIFACT_ROOT_NOT_WRITABLE")
    return reasons

"""Validated evidence-path configuration and opt-in live settings.

Development mode uses the labelled synthetic defaults in config/intelligence/.
Shadow mode uses the explicitly approved unsigned-development settings (IDEA-058);
runtime/ingestion entry points enforce its dev-shadow scope. Live mode
refuses to start while any live parameter is unset, while the prompt file differs from its
pinned hash, or while the model/EDGAR environment settings are missing. Secret values are
returned only inside `LiveModelSettings` and never appear in its repr or in any document.
"""

from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import re

from larp.intelligence.common import IntelligenceError, require_hash, sha256_hex
from larp.intelligence.issuers import IssuerRegistry

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config" / "intelligence"
KNOWN_TOOLS = ("fetch_document", "prior_context", "compare_facts")
MODES = ("development", "shadow", "live")


def _load(name: str, base: Path) -> tuple:
    raw = (base / name).read_bytes()
    return json.loads(raw.decode("utf-8")), sha256_hex(raw)


@dataclass(frozen=True, slots=True)
class IntelligenceConfig:
    mode: str
    config_sha256: str
    max_tool_calls: int
    max_deadline_ms: int
    tools: tuple
    prompt_text: str
    prompt_sha256: str
    limits: dict
    params: dict
    severity: dict
    default_falsifiers: tuple

    def p(self, name: str) -> int:
        return self.params[name]


def load_config(mode: str = "development", base: Path = CONFIG_DIR) -> IntelligenceConfig:
    if mode not in MODES:
        raise IntelligenceError("Unknown configuration mode")
    # Keep the existing development/live configuration bytes and hashes stable.
    # Shadow is a separately versioned operational choice, not a mutation of the
    # synthetic evaluation inputs or pending final/live parameters (IDEA-058).
    raw, config_hash = _load("intelligence.shadow.v1.json" if mode == "shadow" else "intelligence.v1.json", base)
    if raw.get("schema") != "IntelligenceConfig.v1":
        raise IntelligenceError("Unknown evidence configuration schema")
    budget = raw["budget"]
    # G-50 [POLICY] is the declared ceiling; config may tighten it, never loosen it.
    if not (type(budget["max_tool_calls"]) is int and 0 <= budget["max_tool_calls"] <= 6
            and type(budget["max_deadline_ms"]) is int and 0 < budget["max_deadline_ms"] <= 60000
            and budget["max_tool_types"] <= 3):
        raise IntelligenceError("Evidence budget exceeds the G-50 declaration")
    tools = tuple(raw["tools"])
    if len(tools) > budget["max_tool_types"] or set(tools) - set(KNOWN_TOOLS) or len(set(tools)) != len(tools):
        raise IntelligenceError("Tool allowlist is not a subset of the implemented tools")
    prompt_bytes = (base / raw["prompt"]["path"]).read_bytes()
    pinned = require_hash(raw["prompt"]["sha256"], "prompt sha256")
    if sha256_hex(prompt_bytes) != pinned:
        raise IntelligenceError("Prompt template does not match its pinned hash")
    params = {}
    for name, values in raw["parameters"].items():
        value = values[mode]
        if value is None:
            raise IntelligenceError(f"Live parameter {name!r} is unset; live startup refused")
        if type(value) is not int or value < 0:
            raise IntelligenceError(f"Parameter {name!r} must be a nonnegative integer")
        params[name] = value
    return IntelligenceConfig(mode, config_hash, budget["max_tool_calls"], budget["max_deadline_ms"],
                              tools, prompt_bytes.decode("utf-8"), pinned, dict(raw["limits"]), params,
                              raw["severity"], tuple(raw["default_falsifiers"]))


def load_registry(base: Path = CONFIG_DIR, name: str = "issuers.v1.json") -> IssuerRegistry:
    raw, _ = _load(name, base)
    return IssuerRegistry.from_dict(raw)


@dataclass(frozen=True)
class LiveModelSettings:
    provider: str
    model_id: str
    api_key: str | None = field(default=None, repr=False)
    path: str | None = None


def live_model_settings(env=None) -> LiveModelSettings:
    """Proposed LARP_MODEL_* conventions (PARALLEL_BUILD.md); not ai-seeds variables."""
    env = os.environ if env is None else env
    provider, model_id = env.get("LARP_MODEL_PROVIDER"), env.get("LARP_MODEL_ID")
    key, path = env.get("LARP_MODEL_API_KEY"), env.get("LARP_MODEL_PATH")
    if not provider or not model_id:
        raise IntelligenceError("LARP_MODEL_PROVIDER and LARP_MODEL_ID are required for a live model")
    if bool(key) == bool(path):
        raise IntelligenceError("Set exactly one of LARP_MODEL_API_KEY (hosted) or LARP_MODEL_PATH (local)")
    return LiveModelSettings(provider, model_id, key or None, path or None)


# Template text copied from instructions, and the RFC 2606 example domains. sec.gov answers such agents with 403
# (IDEA-066 PC-TERMS01: "LARP Team Your Name your.real@email" passed the earlier check).
_PLACEHOLDERS = ("<", ">", "example.com", "example.net", "example.org", "contact email", "you@",
                 "your name", "yourname", "your.name", "your_name", "your real", "your.real", "your email",
                 "youremail", "your.email", "your_email", "first last", "firstname", "lastname")
# One whitespace-delimited address whose domain has a dotted ending of two or more letters.
_SEC_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_SEC_AGENT_HELP = ("set LARP_SEC_USER_AGENT to a team or person name followed by a contact email that someone reads, "
                   "with no brackets or quotes")


def sec_user_agent(env=None) -> str:
    """Declared SEC User-Agent (fair-access rules: a name and a contact email). LARP_SEC_USER_AGENT; legacy
    SEC_USER_AGENT. Refusals name the failed rule, never the value."""
    env = os.environ if env is None else env
    new, old = env.get("LARP_SEC_USER_AGENT"), env.get("SEC_USER_AGENT")
    if new and old and new != old:
        raise IntelligenceError("LARP_SEC_USER_AGENT and SEC_USER_AGENT disagree")
    agent = (new or old or "").strip()
    words = agent.split()
    if not agent:
        reason = "it is not set"
    elif any(p in agent.lower() for p in _PLACEHOLDERS):
        reason = "it contains template text, brackets or an example domain"
    elif not any(_SEC_EMAIL.fullmatch(w) for w in words):
        reason = "it has no email address with a domain ending such as .com or .edu.sg"
    elif all(_SEC_EMAIL.fullmatch(w) or "@" in w for w in words):
        reason = "it has no name before the email"
    else:
        return agent
    raise IntelligenceError(f"A real SEC User-Agent is required: {reason}; {_SEC_AGENT_HELP}")

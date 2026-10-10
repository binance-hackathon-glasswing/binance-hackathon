"""Provider-neutral evidence-model adapters with pinned identities, costs and latency.

Every adapter implements `step(request: Document, remaining_ms: int) -> Document` with
`ModelRequest.v1` in and `ModelResponse.v1` out. The response carries the raw output for the
audit record (F-49 (c): complete request/response records), its hash, usage, cost with an
explicit basis and measured latency on the injected clock. A late or failed response is a
TIMEOUT/ERROR status, never an empty success.

Adapters:
- RuleBaselineModel: the verified extraction/severity baseline. Deterministic, no prompt,
  no fitted weights; its identity hash covers the code that makes its choices.
- ScriptedModel: deterministic fake for tests (scripted outputs and latencies).
- HostedChatModel: OpenAI-compatible chat-completions codec over an injected transport.
  NOT VERIFIED against any live provider; no provider is selected (GAP-57/D-03).
- LocalCheckpointModel: local weights whose SHA-256 must equal the pinned hash before use.
  No checkpoint exists: training is NOT RUN (training.py).
"""

from dataclasses import dataclass
from pathlib import Path
import json
import socket
import time
from urllib.parse import urlsplit

from larp.contracts import ContractError, Document
from larp.intelligence.common import (
    IntelligenceError, assert_no_trade_fields, digest, forbidden_key_paths, is_hash, require_hash, sha256_hex,
)

_HERE = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    provider: str
    model_id: str
    revision: str
    checkpoint_sha256: str
    kind: str  # RULE | FAKE | HOSTED | LOCAL

    def __post_init__(self):
        require_hash(self.checkpoint_sha256, "checkpoint_sha256")
        if self.kind not in ("RULE", "FAKE", "HOSTED", "LOCAL"):
            raise IntelligenceError("Unknown model kind")

    def record(self) -> dict:
        return {"provider": self.provider, "model_id": self.model_id, "revision": self.revision,
                "checkpoint_sha256": self.checkpoint_sha256, "kind": self.kind}

    @property
    def model_hash(self) -> str:
        return digest("larp.intel.model.v1", self.record())


def code_identity(*names: str) -> str:
    return sha256_hex(b"".join(name.encode() + b"\x00" + (_HERE / name).read_bytes() for name in names))


def response(request: dict, *, status: str, output, latency_ms: int, usage=None, cost=None,
             raw: bytes = b"", reasoning: str | None = None, error: str | None = None) -> Document:
    if output is not None:
        try:  # floats, NaN or other non-canonical JSON from a provider make the output invalid
            Document.from_dict({"output": output})
        except ContractError:
            status, output, error = "INVALID", None, "OUTPUT_NOT_CANONICAL_JSON"
    return Document.from_dict({
        "schema": "ModelResponse.v1", "request_id": request["request_id"], "status": status, "output": output,
        "latency_ms": latency_ms, "usage": usage or {"input_tokens": 0, "output_tokens": 0},
        "cost": cost or {"amount_micro_usd": 0, "basis": "LOCAL_NO_PROVIDER_CHARGE"},
        "raw_response_sha256": sha256_hex(raw), "reasoning_summary": reasoning, "error": error})


ACTIONS = {"CALL_TOOL": {"action", "tool", "args"}, "FINISH": {"action", "claims", "notes"}}


def parse_output(output: object) -> dict:
    """Strict schema for model output. Raises IntelligenceError with a stable reason code."""
    if type(output) is not dict:
        raise IntelligenceError("MODEL_OUTPUT_NOT_OBJECT")
    if forbidden_key_paths(output):
        raise IntelligenceError("MODEL_OUTPUT_TRADE_FIELD")
    action = output.get("action")
    if action not in ACTIONS or set(output) - ACTIONS[action] or "action" not in output:
        raise IntelligenceError("MODEL_OUTPUT_SCHEMA")
    if action == "CALL_TOOL" and (type(output.get("tool")) is not str or type(output.get("args")) is not dict):
        raise IntelligenceError("MODEL_OUTPUT_SCHEMA")
    if action == "FINISH" and type(output.get("claims", [])) is not list:
        raise IntelligenceError("MODEL_OUTPUT_SCHEMA")
    return output


class RuleBaselineModel:
    """Closes the harness-computed gaps in a fixed order, then confirms the extracted facts."""

    def __init__(self, clock_ms):
        self.clock = clock_ms
        self.identity = ModelIdentity("larp", "rule-baseline", "v1",
                                      code_identity("facts.py", "verify.py", "models.py"), "RULE")

    def step(self, request: Document, remaining_ms: int) -> Document:
        r = request.read()
        started = self.clock()
        state = r["input"]
        output = {"action": "FINISH", "claims": state["claimable"], "notes": "deterministic rule path"}
        if state["remaining_tool_calls"] > 0:
            for gap in state["gaps"]:
                if gap["tool"] in state["allowed_tools"]:
                    output = {"action": "CALL_TOOL", "tool": gap["tool"], "args": gap["args"]}
                    break
        raw = json.dumps(output, sort_keys=True).encode()
        return response(r, status="OK", output=output, latency_ms=self.clock() - started, raw=raw,
                        reasoning=f"Rule baseline: {'close gap ' + output['tool'] if output['action'] == 'CALL_TOOL' else 'no open gap within budget; finish'}.")


class ScriptedModel:
    """Test double: returns scripted outputs (dicts or callables of the input) with set latencies."""

    def __init__(self, clock, script: list, *, model_id: str = "scripted-fake"):
        self.clock, self.script, self.calls = clock, list(script), 0
        self.identity = ModelIdentity("fake", model_id, "v1", sha256_hex(json.dumps(
            [s if not callable(s.get("output")) else {"latency_ms": s.get("latency_ms", 0), "output": "callable"}
             for s in script], sort_keys=True, default=str).encode()), "FAKE")

    def step(self, request: Document, remaining_ms: int) -> Document:
        r = request.read()
        entry = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        latency = entry.get("latency_ms", 0)
        if latency > remaining_ms:  # like a transport timeout set to the remaining budget
            self.clock.advance(remaining_ms)
            return response(r, status="TIMEOUT", output=None, latency_ms=remaining_ms, error="DEADLINE_EXCEEDED")
        self.clock.advance(latency)
        if entry.get("error"):
            return response(r, status="ERROR", output=None, latency_ms=latency, error=entry["error"])
        output = entry["output"](r["input"]) if callable(entry["output"]) else entry["output"]
        return response(r, status="OK", output=output, latency_ms=latency,
                        usage=entry.get("usage"), raw=json.dumps(output, sort_keys=True, default=str).encode())


def _openai_chat_transport(url: str, headers: dict, body: bytes, timeout_s: float) -> tuple:
    import urllib.request
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout_s) as reply:  # noqa: S310 - endpoint allowlisted
        return reply.status, reply.read()


class HostedChatModel:
    """OpenAI-compatible chat-completions codec. Not verified against a live provider.

    `price` = {"input_micro_usd_per_mtok": int, "output_micro_usd_per_mtok": int, "source": str}
    from the provider's published price list; without it cost basis is UNKNOWN.
    """

    def __init__(self, *, provider: str, model_id: str, revision: str, endpoint: str, allowed_hosts: frozenset,
                 api_key: str, prompt_text: str, prompt_sha256: str, clock_ms, price: dict | None = None,
                 transport=None):
        parts = urlsplit(endpoint)
        if parts.scheme != "https" or parts.hostname not in allowed_hosts:
            raise IntelligenceError("Hosted model endpoint is outside the declared allowlist")
        if not api_key:
            raise IntelligenceError("Hosted model needs a credential from the runtime secret store")
        if sha256_hex(prompt_text.encode("utf-8")) != require_hash(prompt_sha256, "prompt_sha256"):
            raise IntelligenceError("Prompt text does not match its pinned hash")
        if not revision or revision in ("latest", "default"):
            raise IntelligenceError("Hosted model needs an exact pinned model revision/snapshot")
        self._endpoint, self._key, self._prompt = endpoint, api_key, prompt_text
        self._transport, self.clock, self.price = transport or _openai_chat_transport, clock_ms, price
        # Weights are unavailable for hosted models: the identity pins provider/model/revision.
        self.identity = ModelIdentity(provider, model_id, revision,
                                      sha256_hex(f"{provider}\x00{model_id}\x00{revision}".encode()), "HOSTED")

    def __repr__(self):
        return f"HostedChatModel({self.identity.provider!r}, {self.identity.model_id!r})"

    def step(self, request: Document, remaining_ms: int) -> Document:
        r = request.read()
        body = json.dumps({"model": self.identity.model_id, "temperature": 0,
                           "response_format": {"type": "json_object"},
                           "messages": [{"role": "system", "content": self._prompt},
                                        {"role": "user", "content": json.dumps(r["input"], sort_keys=True)}]},
                          sort_keys=True).encode("utf-8")
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        started = self.clock()
        try:
            status, raw = self._transport(self._endpoint, headers, body, max(remaining_ms, 1) / 1000)
        except (socket.timeout, TimeoutError):
            return response(r, status="TIMEOUT", output=None, latency_ms=self.clock() - started,
                            error="DEADLINE_EXCEEDED")
        except OSError as exc:
            return response(r, status="ERROR", output=None, latency_ms=self.clock() - started,
                            error=type(exc).__name__)
        latency = self.clock() - started
        if latency > remaining_ms:
            return response(r, status="TIMEOUT", output=None, latency_ms=latency, raw=raw, error="DEADLINE_EXCEEDED")
        if status != 200:
            return response(r, status="ERROR", output=None, latency_ms=latency, raw=raw, error=f"HTTP {status}")
        try:
            payload = json.loads(raw.decode("utf-8"))
            message = payload["choices"][0]["message"]
            output = json.loads(message["content"])
            usage = {"input_tokens": int(payload["usage"]["prompt_tokens"]),
                     "output_tokens": int(payload["usage"]["completion_tokens"])}
        except (KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError):
            return response(r, status="ERROR", output=None, latency_ms=latency, raw=raw, error="RESPONSE_UNPARSEABLE")
        cost = {"amount_micro_usd": None, "basis": "UNKNOWN_NO_PRICE_SOURCE"}
        if self.price:
            cost = {"amount_micro_usd": (usage["input_tokens"] * self.price["input_micro_usd_per_mtok"]
                                         + usage["output_tokens"] * self.price["output_micro_usd_per_mtok"]) // 1_000_000,
                    "basis": "TOKENS_X_PUBLISHED_PRICE:" + self.price["source"]}
        reasoning = message.get("reasoning_content") if type(message.get("reasoning_content")) is str else None
        return response(r, status="OK", output=output, latency_ms=latency, usage=usage, cost=cost, raw=raw,
                        reasoning=reasoning)


class LocalCheckpointModel:
    """Local evidence model. Refuses to load unless the file hash equals the pinned checkpoint."""

    def __init__(self, *, path: str, checkpoint_sha256: str, model_id: str, revision: str, infer, clock_ms):
        data = Path(path).read_bytes()
        if not is_hash(checkpoint_sha256) or sha256_hex(data) != checkpoint_sha256:
            raise IntelligenceError("Local checkpoint does not match its pinned SHA-256")
        self.identity = ModelIdentity("local", model_id, revision, checkpoint_sha256, "LOCAL")
        self._infer, self.clock = infer, clock_ms

    def step(self, request: Document, remaining_ms: int) -> Document:
        r = request.read()
        started = self.clock()
        output = self._infer(r["input"])
        latency = self.clock() - started
        if latency > remaining_ms:
            return response(r, status="TIMEOUT", output=None, latency_ms=latency, error="DEADLINE_EXCEEDED")
        return response(r, status="OK", output=output, latency_ms=latency,
                        raw=json.dumps(output, sort_keys=True, default=str).encode())


def wall_clock_ms() -> int:
    return time.monotonic_ns() // 1_000_000


__all__ = ["ModelIdentity", "RuleBaselineModel", "ScriptedModel", "HostedChatModel", "LocalCheckpointModel",
           "parse_output", "assert_no_trade_fields", "wall_clock_ms"]

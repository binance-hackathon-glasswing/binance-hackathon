"""Provider-neutral evidence-model adapters with pinned identities, costs and latency.

Every adapter implements `step(request: Document, remaining_ms: int) -> Document` with
`ModelRequest.v1` in and `ModelResponse.v1` out. The response carries the parsed output, the
raw response hash, usage, cost with an explicit basis and measured latency on the injected
clock. Adapters given an artifact sink also store the exact nonsecret request payload and raw
response bytes (including malformed or rejected replies) and return their content addresses
(F-49 (c): complete request/response records). A late or failed response is a TIMEOUT/ERROR
status, never an empty success.

Adapters:
- RuleBaselineModel: the verified extraction/severity baseline. Deterministic, no prompt,
  no fitted weights; its identity hash covers the code that makes its choices.
- ScriptedModel: deterministic fake for tests (scripted outputs and latencies).
- HostedChatModel: OpenAI-compatible chat-completions codec over an injected transport. The
  request names the pinned snapshot (`revision`), and a reply naming another model is
  rejected. NOT VERIFIED against any live provider; no provider is selected (GAP-57/D-03).
- LocalCheckpointModel: runs an existing local model whose weight file's SHA-256 must equal the
  pinned hash before use, in a worker process that is terminated at the deadline. No local
  model is selected. Model training is out of scope for this build (IDEA-021 §8.1/§8.5).
"""

from dataclasses import dataclass
from pathlib import Path
import json
import multiprocessing
import pickle
import socket
import threading
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


def _store(artifacts, data: bytes | None) -> str | None:
    if artifacts is None or data is None:
        return None
    address = artifacts.put(data)
    if address != sha256_hex(data):
        raise IntelligenceError("Artifact store returned a different content address")
    return address


def response(request: dict, *, status: str, output, latency_ms: int, usage=None, cost=None,
             raw: bytes | None = None, reasoning: str | None = None, error: str | None = None,
             artifacts=None, request_payload: bytes | None = None, served_model: str | None = None) -> Document:
    """ModelResponse.v1. `raw` is None when no reply arrived (timeout, connection error); with an
    artifact sink, the request payload and any reply bytes are stored before anything is parsed."""
    request_ref, raw_ref = _store(artifacts, request_payload), _store(artifacts, raw)
    if output is not None:
        try:  # floats, NaN, deep nesting or other non-canonical JSON from a provider make the output invalid
            Document.from_dict({"output": output})
        except (ContractError, RecursionError, MemoryError):
            status, output, error = "INVALID", None, "OUTPUT_NOT_CANONICAL_JSON"
    return Document.from_dict({
        "schema": "ModelResponse.v1", "request_id": request["request_id"], "status": status, "output": output,
        "latency_ms": latency_ms, "usage": usage or {"input_tokens": 0, "output_tokens": 0},
        "cost": cost or {"amount_micro_usd": 0, "basis": "LOCAL_NO_PROVIDER_CHARGE"},
        "raw_response_sha256": None if raw is None else sha256_hex(raw), "raw_response_artifact": raw_ref,
        "request_payload_sha256": None if request_payload is None else sha256_hex(request_payload),
        "request_payload_artifact": request_ref, "served_model": served_model,
        "reasoning_summary": reasoning, "error": error})


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
    # The shared transport uses a direct bounded HTTPS exchange and never follows
    # redirects, so an Authorization header cannot escape to a Location target.
    from larp.intelligence.providers import https_post
    return https_post(url, headers, body, timeout_s)


def allowed_endpoint(endpoint: str, hosts: frozenset) -> bool:
    try:
        parts = urlsplit(endpoint)
        return (parts.scheme == "https" and parts.hostname in hosts and parts.port in (None, 443)
                and not parts.username and not parts.password and not parts.fragment)
    except ValueError:
        return False


class HostedChatModel:
    """OpenAI-compatible chat-completions codec. Not verified against a live provider.

    `revision` is the provider's immutable snapshot identifier and is the `model` named in every
    request (e.g. a dated snapshot, never an alias such as "...-latest"); `model_id` is the
    family name kept for people reading the record. A reply that names a different model is an
    ERROR. Every request payload (no credential: that travels only in a header) and every reply
    byte is stored through `artifacts` before parsing, so the audit record can recover exactly
    what was sent and returned, including malformed or rejected replies.

    `price` = {"input_micro_usd_per_mtok": int, "output_micro_usd_per_mtok": int, "source": str}
    from the provider's published price list; without it cost basis is UNKNOWN.
    """

    def __init__(self, *, provider: str, model_id: str, revision: str, endpoint: str, allowed_hosts: frozenset,
                 api_key: str, prompt_text: str, prompt_sha256: str, clock_ms, artifacts, price: dict | None = None,
                 transport=None):
        if not allowed_endpoint(endpoint, allowed_hosts):
            raise IntelligenceError("Hosted model endpoint is outside the declared allowlist")
        if not api_key:
            raise IntelligenceError("Hosted model needs a credential from the runtime secret store")
        if sha256_hex(prompt_text.encode("utf-8")) != require_hash(prompt_sha256, "prompt_sha256"):
            raise IntelligenceError("Prompt text does not match its pinned hash")
        if type(revision) is not str or not revision or revision.strip() != revision or \
                revision.lower() == "default" or "latest" in revision.lower():
            raise IntelligenceError("Hosted model needs the provider's exact immutable snapshot identifier")
        if artifacts is None:
            raise IntelligenceError("Hosted model needs an artifact sink for its request/response records")
        self._endpoint, self._key, self._prompt, self._artifacts = endpoint, api_key, prompt_text, artifacts
        self._transport, self.clock, self.price = transport or _openai_chat_transport, clock_ms, price
        # Weights are unavailable for hosted models: the identity pins provider/model/revision.
        self.identity = ModelIdentity(provider, model_id, revision,
                                      sha256_hex(f"{provider}\x00{model_id}\x00{revision}".encode()), "HOSTED")

    def __repr__(self):
        return f"HostedChatModel({self.identity.provider!r}, {self.identity.revision!r})"

    def request_payload(self, request: Document) -> bytes:
        r = request.read()
        return json.dumps({"model": self.identity.revision, "temperature": 0,
                           "response_format": {"type": "json_object"},
                           "messages": [{"role": "system", "content": self._prompt},
                                        {"role": "user", "content": json.dumps(r["input"], sort_keys=True)}]},
                          sort_keys=True).encode("utf-8")

    def has_artifact(self, digest: str) -> bool:
        return self._artifacts.get(digest) is not None

    def step(self, request: Document, remaining_ms: int) -> Document:
        from larp.intelligence.providers import LateReply, MAX_USAGE_TOKENS, _ProviderReply, _json_object
        r = request.read()
        body = self.request_payload(request)
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        record = dict(artifacts=self._artifacts, request_payload=body)
        _store(self._artifacts, body)  # a timed-out or abandoned paid call still has its exact request
        started = self.clock()
        try:
            status, raw = self._transport(self._endpoint, headers, body, max(remaining_ms, 1) / 1000)
        except LateReply as exc:
            return response(r, status="TIMEOUT", output=None, latency_ms=self.clock() - started,
                            error="DEADLINE_EXCEEDED", raw=exc.raw, **record)
        except (socket.timeout, TimeoutError):
            return response(r, status="TIMEOUT", output=None, latency_ms=self.clock() - started,
                            error="DEADLINE_EXCEEDED", **record)
        except OSError as exc:
            return response(r, status="ERROR", output=None, latency_ms=self.clock() - started,
                            error=type(exc).__name__, **record)
        if type(raw) is not bytes:
            return response(r, status="ERROR", output=None, latency_ms=self.clock() - started,
                            error="TRANSPORT_REPLY_NOT_BYTES", **record)
        _store(self._artifacts, raw)  # persist before parsing even adversarially malformed JSON
        record["raw"] = raw
        latency = self.clock() - started
        if latency > remaining_ms:
            return response(r, status="TIMEOUT", output=None, latency_ms=latency, error="DEADLINE_EXCEEDED", **record)
        if status != 200:
            return response(r, status="ERROR", output=None, latency_ms=latency, error=f"HTTP {status}", **record)
        try:
            payload = json.loads(raw.decode("utf-8"))
            served = payload.get("model")
            choice = payload["choices"][0]
            message = choice["message"]
            if message.get("refusal"):
                raise _ProviderReply("PROVIDER_REFUSAL", served)
            if choice.get("finish_reason") != "stop":
                raise _ProviderReply("INCOMPLETE_RESPONSE", served)
            output = _json_object(message["content"])
            usage = {"input_tokens": payload["usage"]["prompt_tokens"],
                     "output_tokens": payload["usage"]["completion_tokens"]}
            if not all(type(value) is int and 0 <= value <= MAX_USAGE_TOKENS for value in usage.values()):
                raise _ProviderReply("USAGE_MALFORMED", served)
        except _ProviderReply as exc:
            return response(r, status="ERROR", output=None, latency_ms=latency, error=exc.code,
                            served_model=exc.served, **record)
        except (AttributeError, KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError, OverflowError,
                RecursionError, MemoryError):
            return response(r, status="ERROR", output=None, latency_ms=latency, error="RESPONSE_UNPARSEABLE", **record)
        if served != self.identity.revision:
            return response(r, status="ERROR", output=None, latency_ms=latency, error="SERVED_MODEL_MISMATCH",
                            served_model=str(served), **record)
        cost = {"amount_micro_usd": None, "basis": "UNKNOWN_NO_PRICE_SOURCE"}
        if self.price:
            cost = {"amount_micro_usd": (usage["input_tokens"] * self.price["input_micro_usd_per_mtok"]
                                         + usage["output_tokens"] * self.price["output_micro_usd_per_mtok"]) // 1_000_000,
                    "basis": "TOKENS_X_PUBLISHED_PRICE:" + self.price["source"]}
        reasoning = message.get("reasoning_content") if type(message.get("reasoning_content")) is str else None
        return response(r, status="OK", output=output, latency_ms=latency, usage=usage, cost=cost,
                        reasoning=reasoning, served_model=served, **record)


def _local_worker(infer, conn) -> None:
    """Worker-process loop: one JSON reply per input; an inference error is reported, not raised."""
    while True:
        try:
            message = conn.recv()
        except (EOFError, OSError):
            return
        try:
            reply = ("OK", json.dumps(infer(message), sort_keys=True).encode("utf-8"))
        except Exception as exc:
            reply = ("ERROR", type(exc).__name__)
        conn.send(reply)


class LocalCheckpointModel:
    """Local evidence model. Refuses to load unless the file hash equals the pinned checkpoint.

    Inference runs in a separate worker process (spawn start method, so the same on every
    platform), which makes the deadline enforceable: if no reply arrives within the remaining
    budget the worker is terminated, its late reply can never be read, and the next step starts
    a fresh worker. `infer(input) -> output` must be an importable top-level callable because it
    is sent to that process.
    """

    def __init__(self, *, path: str, checkpoint_sha256: str, model_id: str, revision: str, infer, clock_ms,
                 artifacts=None):
        data = Path(path).read_bytes()
        if not is_hash(checkpoint_sha256) or sha256_hex(data) != checkpoint_sha256:
            raise IntelligenceError("Local checkpoint does not match its pinned SHA-256")
        try:
            pickle.dumps(infer)
        except Exception:
            raise IntelligenceError("infer must be an importable top-level callable (it runs in a worker process)") \
                from None
        self.identity = ModelIdentity("local", model_id, revision, checkpoint_sha256, "LOCAL")
        self._infer, self.clock, self._artifacts = infer, clock_ms, artifacts
        self._process = self._conn = None
        self._lock = threading.Lock()  # one inference at a time per worker pipe

    def _start(self) -> None:
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(target=_local_worker, args=(self._infer, child), daemon=True,
                                  name=f"larp-local-model:{self.identity.model_id}")
        process.start()
        child.close()
        self._process, self._conn = process, parent

    def worker_alive(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def close(self) -> None:
        """Stop the worker (terminate, then kill if it does not exit); any pending reply is lost."""
        process, conn, self._process, self._conn = self._process, self._conn, None, None
        if conn is not None:
            conn.close()
        if process is not None:
            process.terminate()
            process.join(5)
            if process.is_alive():
                process.kill()
                process.join()

    def step(self, request: Document, remaining_ms: int) -> Document:
        r = request.read()
        payload = json.dumps(r["input"], sort_keys=True).encode("utf-8")
        record = dict(artifacts=self._artifacts, request_payload=payload)
        with self._lock:
            started, wall = self.clock(), time.monotonic()
            try:
                if not self.worker_alive():
                    self.close()
                    self._start()
                self._conn.send(r["input"])
                wait_s = remaining_ms / 1000 - (time.monotonic() - wall)
                ready = wait_s > 0 and self._conn.poll(wait_s)
                if not ready:
                    self.close()  # the late reply dies with the worker
                    return response(r, status="TIMEOUT", output=None, error="DEADLINE_EXCEEDED",
                                    latency_ms=max(self.clock() - started, remaining_ms), **record)
                kind, reply = self._conn.recv()
            except (EOFError, OSError) as exc:
                self.close()
                return response(r, status="ERROR", output=None, latency_ms=self.clock() - started,
                                error=f"WORKER_{type(exc).__name__}", **record)
        latency = self.clock() - started
        if kind != "OK":
            return response(r, status="ERROR", output=None, latency_ms=latency, error=f"INFER_{reply}", **record)
        if latency > remaining_ms:
            return response(r, status="TIMEOUT", output=None, latency_ms=latency, raw=reply,
                            error="DEADLINE_EXCEEDED", **record)
        return response(r, status="OK", output=json.loads(reply), latency_ms=latency, raw=reply, **record)


def wall_clock_ms() -> int:
    return time.monotonic_ns() // 1_000_000


__all__ = ["ModelIdentity", "RuleBaselineModel", "ScriptedModel", "HostedChatModel", "LocalCheckpointModel",
           "parse_output", "assert_no_trade_fields", "wall_clock_ms"]

"""Hosted assessor adapters for the two candidate providers (B8, IDEA-041 part 2, interface I5).

The team will choose between Claude and ChatGPT after system testing (IDEA-035 B8); until then the deterministic
`RuleBaselineModel` is the default and the fallback. These adapters implement the same `step(request,
remaining_ms) -> ModelResponse.v1` port as `larp.intelligence.models`, so the assessor, verifier and budget are
unchanged whichever model runs:

- `AnthropicMessagesModel`: Anthropic Messages API (`POST /v1/messages`), adaptive thinking with
  `display: "summarized"` so the provider's reasoning summary can be logged as the round's `cot` (F-102,
  participant-kit.md K15; SKILL.md Q-16), effort set explicitly, optional structured JSON output.
- `OpenAIResponsesModel`: OpenAI Responses API (`POST /v1/responses`), `reasoning.summary: "auto"` for the
  reasoning summary, JSON output, `store: false`.

Both talk raw HTTPS through an injected transport rather than a provider SDK: the audit record must hold the exact
request and reply bytes (F-49 (c)), which are stored through the artifact sink before anything is parsed, and the
pinned dependency lock (Keegan's) is not changed. The credential travels only in a header and is never stored.

What each adapter refuses or reports:
- an endpoint outside the declared allowlist, a missing credential or artifact sink, a prompt that differs
  from its pinned hash, a model ID that is empty, padded or an alias ("latest", "default");
- a reply naming a different model (SERVED_MODEL_MISMATCH). Anthropic's server-side `fallbacks` are
  deliberately NOT enabled: a fallback answers with a different model than the declared one. A provider
  refusal is an ERROR (PROVIDER_REFUSAL), so the assessment is UNAVAILABLE and nothing is cleared;
- a reply cut short (max tokens, incomplete), unparseable or not JSON: ERROR, never an empty success;
- a reply after the remaining budget: TIMEOUT.

The request payload is stored before the call and the reply bytes as soon as the transport returns, before anything
is parsed, so a reply that breaks the parser (an overflowing number, deep nesting) is still kept (PR #15 review R06).
The default transport ends the whole exchange by the remaining budget (R10): a call the assessor abandoned at its
deadline cannot run on and spend.

`ACTION_SCHEMA` is closed at every level, as Anthropic's structured outputs require (every object
`additionalProperties: false`; no length or numeric constraints; at most 24 optional and 16 union-typed parameters;
an unsupported schema is refused with HTTP 400; platform.claude.com "JSON schema limitations", read 2026-10-12).
It names the three tools' arguments and the claim fields the verifier accepts from a model (R02); the claim fields
the harness sets itself (`basis`, `precision_exp10`) and the source's provenance beyond its record ID are not
offered. `anthropic_schema_problems` re-checks those limits, and the adapter refuses to start with a schema that
breaks them. Not yet confirmed with a live call (no key in this build).

NOT VERIFIED against either live provider in this build (no key or budget yet; IDEA-041 AC-2.1). The response
shapes parsed here follow the providers' documented formats and are tested with recorded-shape fakes.
"""

import http.client
import json
import socket
import ssl
import threading
import time
from urllib.parse import urlsplit

from larp.contracts import reflects_secret
from larp.intelligence.common import IntelligenceError, require_hash, sha256_hex
from larp.intelligence.models import ModelIdentity, allowed_endpoint, response

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_HOSTS = frozenset({"api.anthropic.com"})
ANTHROPIC_VERSION = "2023-06-01"
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
OPENAI_HOSTS = frozenset({"api.openai.com"})
EFFORTS = ("low", "medium", "high", "xhigh", "max")
MAX_REPLY_BYTES = 8_000_000
MAX_USAGE_TOKENS = 10**9


def _nullable(schema: dict) -> dict:
    return {"anyOf": [schema, {"type": "null"}]}


_SPAN = {"type": "object", "additionalProperties": False, "required": ["doc", "start", "end", "text"],
         "properties": {"doc": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"},
                        "text": {"type": "string"}}}
_STATEMENT = {"type": "object", "additionalProperties": False, "required": ["assertion", "actor", "temporal", "effective"],
              "properties": {"assertion": {"enum": ["OCCURRED", "ANNOUNCED_FUTURE", "ATTRIBUTED_REPORT", "FORECAST",
                                                    "CONDITIONAL_RISK", "NEGATED", "MENTION_ONLY", None]},
                             "actor": {"enum": ["ISSUER", "THIRD_PARTY", "UNSPECIFIED", None]},
                             "temporal": {"enum": ["CURRENT", "HISTORICAL", "FUTURE", "UNKNOWN", None]},
                             "effective": _nullable({"type": "string"})}}
# One claim (prompts/assessor.v2.txt; verify.claim_schema_error). Every field is required, null when not stated: a
# closed schema with optional fields would exceed the provider's 24-optional-parameter limit.
_CLAIM = {"type": "object", "additionalProperties": False,
          "required": ["kind", "metric", "period", "value", "range", "tolerance_pct", "unit", "scale_exp10", "direction",
                       "security_scope", "span", "period_span", "scale_span", "statement", "source"],
          "properties": {"kind": {"enum": ["REPORTED", "GUIDANCE", "EVENT"]}, "metric": {"type": "string"},
                         "period": _nullable({"type": "string"}), "value": _nullable({"type": "string"}),
                         "range": _nullable({"type": "array", "items": {"type": "string"}}),
                         "tolerance_pct": _nullable({"type": "string"}),
                         "unit": {"enum": ["USD", "KRW", "PERCENT", None]}, "scale_exp10": {"type": "integer"},
                         "direction": _nullable({"type": "string"}), "security_scope": _nullable({"type": "string"}),
                         "span": _nullable(_SPAN), "period_span": _nullable(_SPAN), "scale_span": _nullable(_SPAN),
                         "statement": _nullable(_STATEMENT),
                         "source": _nullable({"type": "object", "additionalProperties": False, "required": ["record_id"],
                                              "properties": {"record_id": {"type": "string"}}})}}
# The model's reply: one assessor action. Enforced again by models.parse_output (exact keys per action) and the tools.
ACTION_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["action"],
    "properties": {
        "action": {"enum": ["CALL_TOOL", "FINISH"]},
        "tool": {"enum": ["fetch_document", "prior_context", "compare_facts"]},
        "args": {"anyOf": [
            {"type": "object", "additionalProperties": False, "required": ["accession", "name"],
             "properties": {"accession": {"type": "string"}, "name": {"type": "string"}}},
            {"type": "object", "additionalProperties": False, "required": ["metric"],
             "properties": {"metric": {"type": "string"}}}]},
        "claims": {"type": "array", "items": _CLAIM},
        "notes": {"type": "string"}},
}
_SCHEMA_KEYWORDS = frozenset({"type", "properties", "required", "additionalProperties", "items", "enum", "const",
                              "anyOf", "description", "minItems", "default", "format"})
_FORMATS = frozenset({"date-time", "time", "date", "duration", "email", "hostname", "uri", "ipv4", "ipv6", "uuid"})
_MAX_SCHEMA_DEPTH = 32


class TransportError(ConnectionError):
    """A transport failure with a stable reason code (recorded as the step's error)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class LateReply(TimeoutError):
    """The whole reply arrived, but after the deadline: still a timeout, and its bytes are kept for the record."""

    def __init__(self, status: int, raw: bytes):
        super().__init__("DEADLINE_EXCEEDED")
        self.status, self.raw = status, raw


def anthropic_schema_problems(schema: dict) -> list:
    """Ways `schema` breaks Anthropic's documented structured-output limits (empty when it meets them)."""
    problems, counts = [], {"optional": 0, "union": 0}

    def walk(node, path):
        if type(node) is not dict:
            problems.append(f"{path}: not a schema object")
            return
        if path.count(".") + path.count("[") + path.count("|") > _MAX_SCHEMA_DEPTH:
            problems.append(f"{path}: nested too deep (recursive?)")
            return
        problems.extend(f"{path}: unsupported keyword {k}" for k in sorted(set(node) - _SCHEMA_KEYWORDS))
        if "format" in node and node["format"] not in _FORMATS:
            problems.append(f"{path}: unsupported format {node['format']!r}")
        if "enum" in node and (type(node["enum"]) is not list or
                               any(type(v) not in (str, int, float, bool, type(None)) for v in node["enum"])):
            problems.append(f"{path}: enum must list scalars")
        if type(node.get("type")) is list or "anyOf" in node:
            counts["union"] += 1
        if node.get("type") == "object" or "properties" in node:
            if node.get("additionalProperties") is not False:
                problems.append(f"{path}: object without additionalProperties false")
            props = node.get("properties") or {}
            counts["optional"] += len(set(props) - set(node.get("required") or []))
            for key in sorted(props):
                walk(props[key], f"{path}.{key}")
        if "items" in node:
            walk(node["items"], f"{path}[]")
        if "minItems" in node and not (type(node["minItems"]) is int and node["minItems"] in (0, 1)):
            problems.append(f"{path}: minItems other than 0 or 1")
        for i, branch in enumerate(node.get("anyOf") or []):
            walk(branch, f"{path}|{i}")
    walk(schema, "$")
    if counts["optional"] > 24:
        problems.append(f"{counts['optional']} optional parameters (limit 24)")
    if counts["union"] > 16:
        problems.append(f"{counts['union']} union-typed parameters (limit 16)")
    return problems


def post_with_deadline(connection, path: str, headers: dict, body: bytes, timeout_s: float, *,
                       tls_context=None, capture_headers=False) -> tuple:
    """(status, reply bytes) over an http.client connection, with the exchange ending by `timeout_s`.

    A per-socket-operation timeout alone lets a slow reply run far past the budget (each read is quick). Here the
    TCP connect gets the time left, the TLS handshake (when `tls_context` is given) runs on a socket the watchdog
    can cut, and a watchdog shuts the socket down at the deadline, which ends any blocked handshake, send or read;
    the call then raises TimeoutError. A reply that arrived whole but late raises LateReply with its bytes. An HTTP
    error status returns its body too, so a rejected call is recorded as well. Name resolution is not interruptible.
    """
    deadline = time.monotonic() + timeout_s
    expired, held = threading.Event(), {}

    def left() -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or expired.is_set():
            raise TimeoutError("DEADLINE_EXCEEDED")
        return remaining

    def cut():
        expired.set()
        sock = held.get("sock")  # http.client drops connection.sock once a reply owns it
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
    watchdog = threading.Timer(timeout_s, cut)
    watchdog.daemon = True
    watchdog.start()
    try:
        raw_sock = socket.create_connection((connection.host, connection.port), timeout=left())
        held["sock"] = raw_sock
        raw_sock.settimeout(left())
        if tls_context is not None:
            sock = tls_context.wrap_socket(raw_sock, server_hostname=connection.host, do_handshake_on_connect=False)
            held["sock"] = sock
            sock.settimeout(left())
            sock.do_handshake()
        else:
            sock = raw_sock
        connection.sock = sock
        left()
        connection.request("POST", path, body=body, headers=headers)
        reply = connection.getresponse()
        delimited_by_close = reply.length is None and not reply.chunked  # a cut would look like a normal end
        chunks, size = [], 0
        while True:
            chunk = reply.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_REPLY_BYTES:
                raise TransportError("REPLY_TOO_LARGE")
            chunks.append(chunk)
        data = b"".join(chunks)
        if expired.is_set() or time.monotonic() > deadline:
            if delimited_by_close and expired.is_set():
                raise TimeoutError("DEADLINE_EXCEEDED")  # the cut, not the server, may have ended it
            raise LateReply(reply.status, data)
        if capture_headers:
            allowed = {'x-model', 'x-reasoning-effort', 'x-request-id'}
            return reply.status, data, {k.lower(): v for k, v in reply.getheaders() if k.lower() in allowed}
        return reply.status, data
    except (TimeoutError, TransportError):
        raise
    except (OSError, http.client.HTTPException, ValueError, AttributeError) as exc:
        if expired.is_set() or time.monotonic() > deadline:
            raise TimeoutError("DEADLINE_EXCEEDED") from None
        if isinstance(exc, OSError):
            raise
        raise TransportError(f"HTTP_PROTOCOL:{type(exc).__name__}") from None
    finally:
        watchdog.cancel()
        connection.close()
        sock = held.get("sock")
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass


def https_post(url: str, headers: dict, body: bytes, timeout_s: float) -> tuple:
    """(status, reply bytes) from an allowlisted HTTPS endpoint within `timeout_s` (post_with_deadline). Direct
    connection only: proxy environment variables are not used (the hosted runtime connects directly)."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise TransportError("HTTPS_REQUIRED")
    connection = http.client.HTTPSConnection(parts.hostname, parts.port or 443, timeout=max(timeout_s, 0.001))
    return post_with_deadline(connection, parts.path + (f"?{parts.query}" if parts.query else ""), headers, body,
                              timeout_s, tls_context=ssl.create_default_context())


def https_post_metadata(url, headers, body, timeout_s):
    """AIand identity/effort metadata; never capture auth/cookie/arbitrary headers."""
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.hostname != 'api.aiand.com' or parts.path != '/v1/chat/completions':
        raise TransportError('AIAND_ENDPOINT_REFUSED')
    connection = http.client.HTTPSConnection(parts.hostname, 443, timeout=max(timeout_s, .001))
    return post_with_deadline(connection, parts.path, headers, body, timeout_s,
                              tls_context=ssl.create_default_context(), capture_headers=True)


class _ProviderReply(Exception):
    """The reply cannot be used; `code` is the recorded error."""

    def __init__(self, code: str, served: str | None = None):
        super().__init__(code)
        self.code, self.served = code, served if type(served) is str else None


class HostedModel:
    """Shared validation, timing, byte recording and cost for the provider adapters."""

    provider = "hosted"

    def __init__(self, *, model_id: str, endpoint: str, allowed_hosts: frozenset, api_key: str, prompt_text: str,
                 prompt_sha256: str, clock_ms, artifacts, price: dict | None = None, transport=None,
                 max_output_tokens: int = 16000):
        if not allowed_endpoint(endpoint, allowed_hosts):
            raise IntelligenceError("Hosted model endpoint is outside the declared allowlist")
        if not api_key:
            raise IntelligenceError("Hosted model needs a credential from the runtime secret store")
        if sha256_hex(prompt_text.encode("utf-8")) != require_hash(prompt_sha256, "prompt_sha256"):
            raise IntelligenceError("Prompt text does not match its pinned hash")
        if type(model_id) is not str or not model_id or model_id.strip() != model_id or \
                model_id.lower() in ("default", "auto") or "latest" in model_id.lower():
            raise IntelligenceError("Hosted model needs the provider's exact model identifier, not an alias")
        if artifacts is None:
            raise IntelligenceError("Hosted model needs an artifact sink for its request/response records")
        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise IntelligenceError("max_output_tokens must be a positive integer")
        if price is not None and not (type(price.get("input_micro_usd_per_mtok")) is int
                                      and type(price.get("output_micro_usd_per_mtok")) is int and price.get("source")):
            raise IntelligenceError("price needs integer micro-USD per million tokens and a source")
        self._endpoint, self._key, self._prompt, self._artifacts = endpoint, api_key, prompt_text, artifacts
        self._transport, self.clock, self.price = transport or https_post, clock_ms, price
        self.max_output_tokens = max_output_tokens
        # Weights are unavailable for hosted models: the identity pins provider, model and request settings.
        self.identity = ModelIdentity(self.provider, model_id, self._revision(), sha256_hex(
            f"{self.provider}\x00{model_id}\x00{self._revision()}".encode()), "HOSTED")

    def __repr__(self):
        return f"{type(self).__name__}({self.identity.model_id!r})"

    def _revision(self) -> str:
        """Request settings that change behaviour, part of the model identity (and so of the assessment key)."""
        raise NotImplementedError

    def _body(self, model_input: dict) -> dict:
        raise NotImplementedError

    def _headers(self) -> dict:
        raise NotImplementedError

    def _parse(self, payload: dict) -> tuple:
        """(served model, output object, {"input_tokens", "output_tokens"}, reasoning summary or None)."""
        raise NotImplementedError

    def _parse_reply(self, payload, metadata):
        return self._parse(payload)

    def _served_matches(self, served):
        return served == self.identity.model_id

    def request_payload(self, request) -> bytes:
        """The exact request bytes sent for a ModelRequest.v1 (deterministic; no credential)."""
        body = json.dumps(self._body(request.read()["input"]), sort_keys=True, separators=(",", ":")).encode("utf-8")
        if reflects_secret(body, (self._key,)):
            raise IntelligenceError("Credential-bearing model request refused before capture or transport")
        return body

    def has_artifact(self, digest: str) -> bool:
        return self._artifacts.get(digest) is not None

    def _keep(self, data: bytes) -> None:
        if self._artifacts.put(data) != sha256_hex(data):
            raise IntelligenceError("Artifact store returned a different content address")

    def step(self, request, remaining_ms: int):
        r = request.read()
        body = self.request_payload(request)
        record = dict(artifacts=self._artifacts, request_payload=body)
        self._keep(body)  # before the call: a call cut off or abandoned at the deadline still has its request
        started = self.clock()
        try:
            result = self._transport(self._endpoint, self._headers(), body, max(remaining_ms, 1) / 1000)
            status, raw = result[:2]
            metadata = result[2] if len(result) == 3 else {}
        except LateReply as exc:  # paid for and complete, but late: a timeout whose bytes are kept
            if type(exc.raw) is bytes and not reflects_secret(exc.raw, (self._key,)):
                self._keep(exc.raw)
                record["raw"] = exc.raw
            return response(r, status="TIMEOUT", output=None, latency_ms=self.clock() - started,
                            error="DEADLINE_EXCEEDED", **record)
        except (socket.timeout, TimeoutError):
            return response(r, status="TIMEOUT", output=None, latency_ms=self.clock() - started,
                            error="DEADLINE_EXCEEDED", **record)
        except OSError as exc:
            return response(r, status="ERROR", output=None, latency_ms=self.clock() - started,
                            error="TRANSPORT_ERROR", **record)
        if type(raw) is not bytes:
            return response(r, status="ERROR", output=None, latency_ms=self.clock() - started,
                            error="TRANSPORT_REPLY_NOT_BYTES", **record)
        if reflects_secret(raw, (self._key,)):  # an echoed credential never reaches the artifact store
            return response(r, status="ERROR", output=None, latency_ms=self.clock() - started,
                            error="CREDENTIAL_REFLECTION", **record)
        if metadata:
            allowed = {'x-model', 'x-reasoning-effort', 'x-request-id'}
            metadata = {k.lower(): v for k, v in metadata.items() if k.lower() in allowed}
            if not all(type(v) is str for v in metadata.values()) or reflects_secret(
                    json.dumps(metadata).encode(), (self._key,)):
                return response(r, status='ERROR', output=None, latency_ms=self.clock() - started,
                                error='CREDENTIAL_REFLECTION', **record)
            record['provider_metadata'] = metadata
        self._keep(raw)  # before any parsing
        record["raw"] = raw
        latency = self.clock() - started
        if latency > remaining_ms:
            return response(r, status="TIMEOUT", output=None, latency_ms=latency, error="DEADLINE_EXCEEDED", **record)
        if status != 200:
            if self.provider == 'openai':
                try:
                    error = json.loads(raw).get('error') or {}
                    if error.get('code') in ('insufficient_quota', 'billing_hard_limit_reached',
                            'credit_balance_exhausted', 'organization_spend_limit_exceeded',
                            'project_spend_limit_exceeded', 'organization_usage_limit_exceeded') or \
                            error.get('type') == 'insufficient_quota':
                        return response(r, status='ERROR', output=None, latency_ms=latency,
                                        error='OPENAI_CREDIT_EXHAUSTED', **record)
                except (ValueError, AttributeError, RecursionError):
                    pass
            return response(r, status="ERROR", output=None, latency_ms=latency, error=f"HTTP {status}", **record)
        try:
            payload = json.loads(raw.decode("utf-8"))
            if type(payload) is not dict:
                raise _ProviderReply("RESPONSE_UNPARSEABLE")
            served, output, usage, reasoning = self._parse_reply(payload, metadata)
            if not all(type(usage.get(k)) is int and 0 <= usage[k] <= MAX_USAGE_TOKENS
                       for k in ("input_tokens", "output_tokens")):
                raise _ProviderReply("USAGE_MALFORMED", served)
        except _ProviderReply as exc:
            return response(r, status="ERROR", output=None, latency_ms=latency, error=exc.code,
                            served_model=exc.served, **record)
        except (AttributeError, KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError, OverflowError,
                RecursionError, MemoryError):
            return response(r, status="ERROR", output=None, latency_ms=latency, error="RESPONSE_UNPARSEABLE", **record)
        if not self._served_matches(served):
            return response(r, status="ERROR", output=None, latency_ms=latency, error="SERVED_MODEL_MISMATCH",
                            served_model=str(served), **record)
        cost = {"amount_micro_usd": None, "basis": "UNKNOWN_NO_PRICE_SOURCE"}
        if self.price:
            cost = {"amount_micro_usd": (usage["input_tokens"] * self.price["input_micro_usd_per_mtok"]
                                         + usage["output_tokens"] * self.price["output_micro_usd_per_mtok"]) // 1_000_000,
                    "basis": "TOKENS_X_PUBLISHED_PRICE:" + self.price["source"]}
        return response(r, status="OK", output=output, latency_ms=latency, usage=usage, cost=cost,
                        reasoning=reasoning, served_model=served, **record)


def _json_object(text: str):
    value = json.loads(text)
    if type(value) is not dict:
        raise _ProviderReply("OUTPUT_NOT_JSON_OBJECT")
    pending = [(value, 0)]
    while pending:
        node, depth = pending.pop()
        if depth > 64:
            raise _ProviderReply("OUTPUT_TOO_DEEP")
        if type(node) is dict:
            pending.extend((v, depth + 1) for v in node.values())
        elif type(node) is list:
            pending.extend((v, depth + 1) for v in node)
    return value


class AnthropicMessagesModel(HostedModel):
    """Anthropic Messages API. `effort` is sent explicitly (model defaults differ); thinking is adaptive with a
    summarized display, which is what the round log's `cot` records. No server-side fallbacks (see module)."""

    provider = "anthropic"

    def __init__(self, *, effort: str = "medium", structured_output: bool = True, endpoint: str = ANTHROPIC_ENDPOINT,
                 allowed_hosts: frozenset = ANTHROPIC_HOSTS, **kwargs):
        if effort not in EFFORTS:
            raise IntelligenceError(f"Unknown effort {effort!r}")
        if structured_output and anthropic_schema_problems(ACTION_SCHEMA):
            raise IntelligenceError(f"ACTION_SCHEMA breaks the provider's structured-output limits: "
                                    f"{anthropic_schema_problems(ACTION_SCHEMA)[:3]}")
        self.effort, self.structured_output = effort, structured_output
        super().__init__(endpoint=endpoint, allowed_hosts=allowed_hosts, **kwargs)

    def _revision(self) -> str:
        return f"messages/{ANTHROPIC_VERSION};thinking=adaptive-summarized;effort={self.effort};" \
               f"format={'json_schema' if self.structured_output else 'prompt'};max_tokens={self.max_output_tokens}"

    def _body(self, model_input: dict) -> dict:
        output_config = {"effort": self.effort}
        if self.structured_output:
            output_config["format"] = {"type": "json_schema", "schema": ACTION_SCHEMA}
        return {"model": self.identity.model_id, "max_tokens": self.max_output_tokens, "system": self._prompt,
                "thinking": {"type": "adaptive", "display": "summarized"}, "output_config": output_config,
                "messages": [{"role": "user", "content": json.dumps(model_input, sort_keys=True)}]}

    def _headers(self) -> dict:
        return {"x-api-key": self._key, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"}

    def _parse(self, payload: dict) -> tuple:
        served = payload.get("model")
        if payload.get("type") == "error":
            raise _ProviderReply("PROVIDER_ERROR", served)
        stop = payload.get("stop_reason")
        if stop == "refusal":
            raise _ProviderReply("PROVIDER_REFUSAL", served)
        if stop != "end_turn":
            raise _ProviderReply(f"STOP_{str(stop).upper()}", served)
        blocks = payload["content"]
        texts = [b["text"] for b in blocks if b.get("type") == "text"]
        thinking = [b["thinking"] for b in blocks if b.get("type") == "thinking" and b.get("thinking")]
        if len(texts) != 1:
            raise _ProviderReply("OUTPUT_NOT_ONE_TEXT_BLOCK", served)
        usage = {"input_tokens": payload["usage"]["input_tokens"], "output_tokens": payload["usage"]["output_tokens"]}
        return served, _json_object(texts[0]), usage, "\n\n".join(thinking) or None


class OpenAIResponsesModel(HostedModel):
    """OpenAI Responses API with a reasoning summary and JSON output; nothing is stored at the provider."""

    provider = "openai"

    def __init__(self, *, effort: str = "medium", endpoint: str = OPENAI_ENDPOINT,
                 allowed_hosts: frozenset = OPENAI_HOSTS, **kwargs):
        if effort not in ("low", "medium", "high"):
            raise IntelligenceError(f"Unknown reasoning effort {effort!r}")
        self.effort = effort
        super().__init__(endpoint=endpoint, allowed_hosts=allowed_hosts, **kwargs)

    def _revision(self) -> str:
        return f"responses;reasoning={self.effort}+summary-auto;format=json_object;store=false;" \
               f"max_output_tokens={self.max_output_tokens}"

    def _body(self, model_input: dict) -> dict:
        return {"model": self.identity.model_id, "instructions": self._prompt,
                "input": json.dumps(model_input, sort_keys=True), "reasoning": {"effort": self.effort, "summary": "auto"},
                "text": {"format": {"type": "json_object"}}, "max_output_tokens": self.max_output_tokens,
                "store": False}

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}

    def _parse(self, payload: dict) -> tuple:
        served = payload.get("model")
        if payload.get("error"):
            raise _ProviderReply("PROVIDER_ERROR", served)
        if payload.get("status") != "completed":
            raise _ProviderReply(f"STATUS_{str(payload.get('status')).upper()}", served)
        texts, summaries = [], []
        for item in payload["output"]:
            if item.get("type") == "reasoning":
                summaries += [s["text"] for s in item.get("summary") or [] if s.get("type") == "summary_text"]
            elif item.get("type") == "message":
                for part in item["content"]:
                    if part.get("type") == "refusal":
                        raise _ProviderReply("PROVIDER_REFUSAL", served)
                    if part.get("type") == "output_text":
                        texts.append(part["text"])
        if len(texts) != 1:
            raise _ProviderReply("OUTPUT_NOT_ONE_TEXT_BLOCK", served)
        usage = {"input_tokens": payload["usage"]["input_tokens"], "output_tokens": payload["usage"]["output_tokens"]}
        return served, _json_object(texts[0]), usage, "\n\n".join(summaries) or None


PROVIDERS = {"anthropic": AnthropicMessagesModel, "openai": OpenAIResponsesModel}


def hosted_model(settings, *, prompt_text: str, prompt_sha256: str, clock_ms, artifacts, price=None,
                 transport=None, **options) -> HostedModel:
    """An adapter from `config.LiveModelSettings` (LARP_MODEL_PROVIDER / LARP_MODEL_ID / LARP_MODEL_API_KEY)."""
    cls = PROVIDERS.get(settings.provider)
    if cls is None or not settings.api_key:
        raise IntelligenceError("LARP_MODEL_PROVIDER must be 'anthropic' or 'openai' with LARP_MODEL_API_KEY set")
    return cls(model_id=settings.model_id, api_key=settings.api_key, prompt_text=prompt_text,
               prompt_sha256=prompt_sha256, clock_ms=clock_ms, artifacts=artifacts, price=price, transport=transport,
               **options)


__all__ = ["HostedModel", "AnthropicMessagesModel", "OpenAIResponsesModel", "PROVIDERS", "hosted_model",
           "ACTION_SCHEMA", "anthropic_schema_problems", "post_with_deadline", "https_post", "LateReply",
           "TransportError"]

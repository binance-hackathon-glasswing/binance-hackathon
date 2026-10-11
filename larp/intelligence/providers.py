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

NOT VERIFIED against either live provider in this build (no key or budget yet; IDEA-041 AC-2.1). The response
shapes parsed here follow the providers' documented formats and are tested with recorded-shape fakes.
"""

import json
import socket
from urllib.parse import urlsplit

from larp.intelligence.common import IntelligenceError, require_hash, sha256_hex
from larp.intelligence.models import ModelIdentity, response

ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_HOSTS = frozenset({"api.anthropic.com"})
ANTHROPIC_VERSION = "2023-06-01"
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
OPENAI_HOSTS = frozenset({"api.openai.com"})
EFFORTS = ("low", "medium", "high", "xhigh", "max")
# The model's reply: one assessor action (prompts/assessor.v2.txt). Enforced again by models.parse_output.
ACTION_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["action"],
    "properties": {"action": {"type": "string", "enum": ["CALL_TOOL", "FINISH"]},
                   "tool": {"type": "string"}, "args": {"type": "object"},
                   "claims": {"type": "array", "items": {"type": "object"}}, "notes": {"type": "string"}},
}


def https_post(url: str, headers: dict, body: bytes, timeout_s: float) -> tuple:
    """(status, reply bytes). An HTTP error status returns its body too, so a rejected call is recorded as well."""
    import urllib.error
    import urllib.request
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as reply:  # noqa: S310 - endpoint allowlisted
            return reply.status, reply.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() if exc.fp is not None else b""


class _ProviderReply(Exception):
    """The reply cannot be used; `code` is the recorded error."""

    def __init__(self, code: str, served: str | None = None):
        super().__init__(code)
        self.code, self.served = code, served


class HostedModel:
    """Shared validation, timing, byte recording and cost for the provider adapters."""

    provider = "hosted"

    def __init__(self, *, model_id: str, endpoint: str, allowed_hosts: frozenset, api_key: str, prompt_text: str,
                 prompt_sha256: str, clock_ms, artifacts, price: dict | None = None, transport=None,
                 max_output_tokens: int = 16000):
        parts = urlsplit(endpoint)
        if parts.scheme != "https" or parts.hostname not in allowed_hosts:
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

    def step(self, request, remaining_ms: int):
        r = request.read()
        body = json.dumps(self._body(r["input"]), sort_keys=True, separators=(",", ":")).encode("utf-8")
        record = dict(artifacts=self._artifacts, request_payload=body)
        started = self.clock()
        try:
            status, raw = self._transport(self._endpoint, self._headers(), body, max(remaining_ms, 1) / 1000)
        except (socket.timeout, TimeoutError):
            return response(r, status="TIMEOUT", output=None, latency_ms=self.clock() - started,
                            error="DEADLINE_EXCEEDED", **record)
        except OSError as exc:
            return response(r, status="ERROR", output=None, latency_ms=self.clock() - started,
                            error=type(exc).__name__, **record)
        record["raw"] = raw
        latency = self.clock() - started
        if latency > remaining_ms:
            return response(r, status="TIMEOUT", output=None, latency_ms=latency, error="DEADLINE_EXCEEDED", **record)
        if status != 200:
            return response(r, status="ERROR", output=None, latency_ms=latency, error=f"HTTP {status}", **record)
        try:
            payload = json.loads(raw.decode("utf-8"))
            if type(payload) is not dict:
                raise _ProviderReply("RESPONSE_UNPARSEABLE")
            served, output, usage, reasoning = self._parse(payload)
        except _ProviderReply as exc:
            return response(r, status="ERROR", output=None, latency_ms=latency, error=exc.code,
                            served_model=exc.served, **record)
        except (AttributeError, KeyError, IndexError, TypeError, ValueError, UnicodeDecodeError):
            return response(r, status="ERROR", output=None, latency_ms=latency, error="RESPONSE_UNPARSEABLE", **record)
        if served != self.identity.model_id:
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
    return value


class AnthropicMessagesModel(HostedModel):
    """Anthropic Messages API. `effort` is sent explicitly (model defaults differ); thinking is adaptive with a
    summarized display, which is what the round log's `cot` records. No server-side fallbacks (see module)."""

    provider = "anthropic"

    def __init__(self, *, effort: str = "medium", structured_output: bool = True, endpoint: str = ANTHROPIC_ENDPOINT,
                 allowed_hosts: frozenset = ANTHROPIC_HOSTS, **kwargs):
        if effort not in EFFORTS:
            raise IntelligenceError(f"Unknown effort {effort!r}")
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
        usage = {"input_tokens": int(payload["usage"]["input_tokens"]),
                 "output_tokens": int(payload["usage"]["output_tokens"])}
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
        usage = {"input_tokens": int(payload["usage"]["input_tokens"]),
                 "output_tokens": int(payload["usage"]["output_tokens"])}
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
           "ACTION_SCHEMA"]

"""Provider-neutral adapters (fake transports only) and the model output schema."""

import hashlib
import json
import socket
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError
from larp.intelligence.config import load_config
from larp.intelligence.fakes import FakeClock, MemoryArtifacts
from larp.intelligence.models import (
    HostedChatModel, LocalCheckpointModel, RuleBaselineModel, ScriptedModel, parse_output,
)

from . import local_infer

SECRET = "sk-synthetic-never-real-0123456789"


def request(input_=None):
    return Document.from_dict({"schema": "ModelRequest.v1", "request_id": "r:1", "model": {}, "prompt_sha256": "0" * 64,
                               "input": input_ or {"gaps": []}})


class HostedAdapterTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.clock = FakeClock(1_000)
        self.sent = []
        self.artifacts = MemoryArtifacts()

    def model(self, transport, **kw):
        args = dict(provider="example-provider", model_id="example-model", revision="example-model-2026-09-01",
                    endpoint="https://api.example-provider.test/v1/chat/completions",
                    allowed_hosts=frozenset({"api.example-provider.test"}), api_key=SECRET,
                    prompt_text=self.config.prompt_text, prompt_sha256=self.config.prompt_sha256,
                    clock_ms=self.clock, artifacts=self.artifacts, transport=transport)
        args.update(kw)
        return HostedChatModel(**args)

    def reply(self, content, latency=1200, reasoning=None, status=200, served="echo"):
        def transport(url, headers, body, timeout):
            self.sent.append((url, headers, body, timeout))
            self.clock.advance(latency)
            message = {"role": "assistant", "content": content}
            if reasoning:
                message["reasoning_content"] = reasoning
            payload = {"choices": [{"message": message, "finish_reason": "stop"}],
                       "usage": {"prompt_tokens": 1000, "completion_tokens": 200}}
            if served is not None:
                payload["model"] = json.loads(body)["model"] if served == "echo" else served
            return status, json.dumps(payload).encode()
        return transport

    def test_construction_requires_allowlisted_https_pinned_revision_and_prompt(self):
        ok = self.reply("{}")
        for change in ({"endpoint": "https://evil.test/v1"}, {"endpoint": "http://api.example-provider.test/v1"},
                       {"endpoint": "https://user:password@api.example-provider.test/v1"},
                       {"endpoint": "https://api.example-provider.test:444/v1"},
                       {"endpoint": "https://api.example-provider.test:invalid/v1"},
                       {"revision": "latest"}, {"revision": "example-model-latest"}, {"revision": ""},
                       {"revision": "default"}, {"api_key": ""}, {"prompt_sha256": "0" * 64}, {"artifacts": None}):
            with self.subTest(change=change), self.assertRaises(IntelligenceError):
                self.model(ok, **change)

    def test_success_records_usage_cost_latency_and_reasoning_without_the_credential(self):
        output = {"action": "FINISH", "claims": [], "notes": "nothing new"}
        model = self.model(self.reply(json.dumps(output), reasoning="checked guidance"),
                           price={"input_micro_usd_per_mtok": 270_000, "output_micro_usd_per_mtok": 1_100_000,
                                  "source": "synthetic price list"})
        response = model.step(request(), 60_000)
        r = response.read()
        self.assertEqual((r["status"], r["output"], r["latency_ms"]), ("OK", output, 1200))
        self.assertEqual(r["usage"], {"input_tokens": 1000, "output_tokens": 200})
        self.assertEqual(r["cost"]["amount_micro_usd"], (1000 * 270_000 + 200 * 1_100_000) // 1_000_000)
        self.assertEqual(r["reasoning_summary"], "checked guidance")
        self.assertEqual(self.sent[0][1]["Authorization"], f"Bearer {SECRET}")
        self.assertNotIn(SECRET.encode(), response.payload)
        self.assertNotIn(SECRET, repr(model))
        body = json.loads(self.sent[0][2])
        self.assertEqual((body["temperature"], body["messages"][0]["content"]), (0, self.config.prompt_text))
        self.assertEqual((body["model"], r["served_model"]), ("example-model-2026-09-01", "example-model-2026-09-01"))

    def test_the_pinned_revision_selects_the_snapshot_and_a_different_served_model_is_rejected(self):
        output = json.dumps({"action": "FINISH", "claims": [], "notes": ""})
        first = self.model(self.reply(output))
        second = self.model(self.reply(output), revision="example-model-2026-10-01")
        first.step(request(), 60_000), second.step(request(), 60_000)
        self.assertEqual([json.loads(sent[2])["model"] for sent in self.sent],
                         ["example-model-2026-09-01", "example-model-2026-10-01"])
        self.assertNotEqual(first.identity.model_hash, second.identity.model_hash)
        swapped = self.model(self.reply(output, served="example-model-2026-11-15")).step(request(), 60_000).read()
        self.assertEqual((swapped["status"], swapped["error"], swapped["output"]),
                         ("ERROR", "SERVED_MODEL_MISMATCH", None))
        self.assertEqual(swapped["served_model"], "example-model-2026-11-15")
        unstated = self.model(self.reply(output, served=None)).step(request(), 60_000).read()
        self.assertEqual((unstated["status"], unstated["error"]), ("ERROR", "SERVED_MODEL_MISMATCH"))

    def test_request_and_reply_bytes_are_recoverable_and_exclude_the_credential(self):
        def malformed(url, headers, body, timeout):
            self.sent.append((url, headers, body, timeout))
            return 200, b'{"choices": [{"message": {"content": "not json at all"}}], "id": "\xff'
        r = self.model(malformed).step(request(), 60_000).read()
        self.assertEqual((r["status"], r["error"]), ("ERROR", "RESPONSE_UNPARSEABLE"))
        raw = self.artifacts.get(r["raw_response_artifact"])
        self.assertEqual(raw, b'{"choices": [{"message": {"content": "not json at all"}}], "id": "\xff')
        self.assertEqual(hashlib.sha256(raw).hexdigest(), r["raw_response_sha256"])
        self.assertEqual(self.artifacts.get(r["request_payload_artifact"]), self.sent[0][2])
        self.assertEqual(self.sent[0][1]["Authorization"], f"Bearer {SECRET}")
        for blob in self.artifacts.blobs.values():
            self.assertNotIn(SECRET.encode(), blob)
        refused = self.model(self.reply("{}", status=500)).step(request(), 60_000).read()
        self.assertIsNotNone(self.artifacts.get(refused["raw_response_artifact"]))  # rejected replies are kept

        def times_out(*a):
            raise socket.timeout("synthetic")

        late = self.model(times_out).step(request(), 60_000).read()
        self.assertEqual((late["status"], late["raw_response_artifact"], late["raw_response_sha256"]),
                         ("TIMEOUT", None, None))  # no reply bytes exist; the request is still recorded
        self.assertIsNotNone(self.artifacts.get(late["request_payload_artifact"]))

    def test_unknown_price_timeouts_errors_and_unparseable_replies(self):
        r = self.model(self.reply(json.dumps({"action": "FINISH", "claims": [], "notes": ""}))).step(request(), 60_000).read()
        self.assertEqual((r["cost"]["amount_micro_usd"], r["cost"]["basis"]), (None, "UNKNOWN_NO_PRICE_SOURCE"))

        def times_out(*a):
            raise socket.timeout("synthetic")

        self.assertEqual(self.model(times_out).step(request(), 60_000).read()["status"], "TIMEOUT")
        self.assertEqual(self.model(self.reply("{}", latency=70_000)).step(request(), 60_000).read()["status"], "TIMEOUT")
        self.assertEqual(self.model(self.reply("{}", status=500)).step(request(), 60_000).read()["error"], "HTTP 500")
        self.assertEqual(self.model(self.reply("not json")).step(request(), 60_000).read()["error"], "RESPONSE_UNPARSEABLE")
        self.assertEqual(self.model(self.reply('{"x": 0.5}')).step(request(), 60_000).read()["status"], "INVALID")

        def refused(*a):
            raise ConnectionRefusedError()

        self.assertEqual(self.model(refused).step(request(), 60_000).read()["status"], "ERROR")

    def test_credential_echo_is_never_stored(self):
        from larp.intelligence.providers import LateReply
        escaped = SECRET.replace("s", "\\u0073", 1)
        for raw in (json.dumps({"error": SECRET}).encode(), ('{"error":"%s","error":null}' % escaped).encode()):
            for late in (False, True):
                with self.subTest(raw=raw, late=late):
                    self.artifacts = MemoryArtifacts()
                    def transport(*_):
                        if late:
                            raise LateReply(200, raw)
                        return 200, raw
                    reply = self.model(transport).step(request(), 60_000).read()
                    self.assertEqual(reply["status"], "TIMEOUT" if late else "ERROR")
                    self.assertIsNone(reply["raw_response_artifact"])
                    self.assertFalse(any(SECRET.encode() in blob or escaped.encode() in blob
                                         for blob in self.artifacts.blobs.values()))

    def test_default_transport_uses_bounded_no_redirect_provider_transport(self):
        from larp.intelligence.models import _openai_chat_transport
        with patch("larp.intelligence.providers.https_post", return_value=(302, b"redirect")) as post:
            result = _openai_chat_transport("https://api.example-provider.test/v1", {"Authorization": SECRET}, b"{}", 1)
        self.assertEqual(result, (302, b"redirect"))
        post.assert_called_once_with("https://api.example-provider.test/v1", {"Authorization": SECRET}, b"{}", 1)

    def test_request_is_persisted_before_transport_and_bad_replies_are_retained(self):
        output = json.dumps({"action": "FINISH", "claims": [], "notes": ""})
        base = {"model": "example-model-2026-09-01", "choices": [{"finish_reason": "stop",
                "message": {"content": output}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
        cases = [(dict(base, choices=[{"finish_reason": "length", "message": {"content": output}}]),
                  "INCOMPLETE_RESPONSE"),
                 (dict(base, choices=[{"finish_reason": "stop", "message": {"refusal": "declined"}}]),
                  "PROVIDER_REFUSAL"),
                 (dict(base, model={"malformed": 0.5}, choices=[{"finish_reason": "length", "message": {}}]),
                  "INCOMPLETE_RESPONSE")]
        cases += [(dict(base, usage={"prompt_tokens": value, "completion_tokens": 1}), "USAGE_MALFORMED")
                  for value in (-1, True, "10", 10**10)]
        cases.append((dict(base, choices=[{"finish_reason": "stop", "message": {
            "content": '{"nested":' * 65 + '{}' + '}' * 65}}]), "OUTPUT_TOO_DEEP"))  # bound is depth 64
        for payload, error in cases:
            raw = json.dumps(payload).encode()
            def transport(url, headers, body, timeout):
                self.assertEqual(self.artifacts.get(hashlib.sha256(body).hexdigest()), body)
                return 200, raw
            with self.subTest(error=error):
                reply = self.model(transport).step(request(), 60_000).read()
                self.assertEqual((reply["status"], reply["error"]), ("ERROR", error))
                self.assertEqual(self.artifacts.get(reply["raw_response_artifact"]), raw)


class LocalAndRuleModelTests(unittest.TestCase):
    def local(self, tmp, infer=local_infer.finish, **kw):
        path = Path(tmp) / "weights.bin"
        path.write_bytes(b"synthetic weights")
        digest = hashlib.sha256(b"synthetic weights").hexdigest()
        model = LocalCheckpointModel(path=str(path), checkpoint_sha256=kw.pop("checkpoint_sha256", digest),
                                     model_id="student", revision="r1", infer=infer, clock_ms=FakeClock(0), **kw)
        self.addCleanup(model.close)
        return model

    def test_local_checkpoint_must_match_its_pinned_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = MemoryArtifacts()
            model = self.local(tmp, artifacts=artifacts)
            r = model.step(request(), 30_000).read()
            self.assertEqual((r["status"], r["output"]["notes"]), ("OK", "local"))
            self.assertEqual(json.loads(artifacts.get(r["raw_response_artifact"])), r["output"])
            self.assertEqual(model.identity.kind, "LOCAL")
            with self.assertRaises(IntelligenceError):
                self.local(tmp, checkpoint_sha256="0" * 64)
            with self.assertRaises(IntelligenceError):  # cannot be sent to a worker process
                self.local(tmp, infer=lambda state: {"action": "FINISH", "claims": [], "notes": ""})

    def test_a_blocked_local_inference_is_stopped_at_the_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = self.local(tmp)
            self.assertEqual(model.step(request(), 30_000).read()["status"], "OK")
            worker = model._process
            started = time.monotonic()
            r = model.step(request({"block": True}), 1_500).read()
            self.assertEqual((r["status"], r["error"], r["output"]), ("TIMEOUT", "DEADLINE_EXCEEDED", None))
            self.assertLess(time.monotonic() - started, 10)  # bounded by the deadline, not by the 120 s sleep
            self.assertFalse(worker.is_alive())  # the worker was terminated; its late reply cannot arrive
            self.assertIsNotNone(worker.exitcode)
            self.assertFalse(model.worker_alive())
            again = model.step(request(), 30_000).read()  # a fresh worker serves the next step
            self.assertEqual(again["status"], "OK")
            self.assertIsNot(model._process, worker)

    def test_local_inference_errors_are_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.local(tmp, infer=local_infer.broken).step(request(), 30_000).read()
            self.assertEqual((r["status"], r["error"]), ("ERROR", "INFER_RuntimeError"))

    def test_rule_baseline_identity_is_stable_and_covers_its_code(self):
        a, b = RuleBaselineModel(FakeClock(0)), RuleBaselineModel(FakeClock(5))
        self.assertEqual(a.identity.model_hash, b.identity.model_hash)
        self.assertEqual((a.identity.kind, a.identity.provider), ("RULE", "larp"))

    def test_scripted_model_honours_deadline(self):
        clock = FakeClock(0)
        model = ScriptedModel(clock, [{"latency_ms": 5000, "output": {"action": "FINISH", "claims": [], "notes": ""}}])
        self.assertEqual(model.step(request(), 4000).read()["status"], "TIMEOUT")
        self.assertEqual(clock(), 4000)


class OutputSchemaTests(unittest.TestCase):
    def test_strict_output_schema(self):
        parse_output({"action": "FINISH", "claims": [], "notes": "ok"})
        parse_output({"action": "CALL_TOOL", "tool": "compare_facts", "args": {"metric": "revenue"}})
        bad = ({"action": "BUY"}, {"action": "FINISH", "claims": [], "orders": []},
               {"action": "FINISH", "claims": [{"kind": "REPORTED", "side": "SELL"}]},
               {"action": "CALL_TOOL", "tool": "x"}, {"action": "FINISH", "claims": {}}, [],
               {"action": "FINISH", "claims": [], "confidence_probability": 1})
        for output in bad:
            with self.subTest(output=output), self.assertRaises(IntelligenceError):
                parse_output(output)


if __name__ == "__main__":
    unittest.main()

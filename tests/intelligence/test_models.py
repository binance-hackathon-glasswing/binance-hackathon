"""Provider-neutral adapters (fake transports only), output schema, training gate."""

import hashlib
import json
import socket
import tempfile
import unittest
from pathlib import Path

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError
from larp.intelligence.config import load_config
from larp.intelligence.fakes import FakeClock
from larp.intelligence.models import (
    HostedChatModel, LocalCheckpointModel, RuleBaselineModel, ScriptedModel, parse_output,
)
from larp.intelligence.training import check_training_manifest

SECRET = "sk-synthetic-never-real-0123456789"


def request(input_=None):
    return Document.from_dict({"schema": "ModelRequest.v1", "request_id": "r:1", "model": {}, "prompt_sha256": "0" * 64,
                               "input": input_ or {"gaps": []}})


class HostedAdapterTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.clock = FakeClock(1_000)
        self.sent = []

    def model(self, transport, **kw):
        args = dict(provider="example-provider", model_id="example-model", revision="2026-09-01",
                    endpoint="https://api.example-provider.test/v1/chat/completions",
                    allowed_hosts=frozenset({"api.example-provider.test"}), api_key=SECRET,
                    prompt_text=self.config.prompt_text, prompt_sha256=self.config.prompt_sha256,
                    clock_ms=self.clock, transport=transport)
        args.update(kw)
        return HostedChatModel(**args)

    def reply(self, content, latency=1200, reasoning=None, status=200):
        def transport(url, headers, body, timeout):
            self.sent.append((url, headers, body, timeout))
            self.clock.advance(latency)
            message = {"role": "assistant", "content": content}
            if reasoning:
                message["reasoning_content"] = reasoning
            return status, json.dumps({"choices": [{"message": message}],
                                       "usage": {"prompt_tokens": 1000, "completion_tokens": 200}}).encode()
        return transport

    def test_construction_requires_allowlisted_https_pinned_revision_and_prompt(self):
        ok = self.reply("{}")
        for change in ({"endpoint": "https://evil.test/v1"}, {"endpoint": "http://api.example-provider.test/v1"},
                       {"revision": "latest"}, {"api_key": ""}, {"prompt_sha256": "0" * 64}):
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


class LocalAndRuleModelTests(unittest.TestCase):
    def test_local_checkpoint_must_match_its_pinned_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "weights.bin"
            path.write_bytes(b"synthetic weights")
            digest = hashlib.sha256(b"synthetic weights").hexdigest()
            infer = lambda state: {"action": "FINISH", "claims": [], "notes": "local"}
            model = LocalCheckpointModel(path=str(path), checkpoint_sha256=digest, model_id="student", revision="r1",
                                         infer=infer, clock_ms=FakeClock(0))
            self.assertEqual(model.step(request(), 1000).read()["status"], "OK")
            self.assertEqual(model.identity.kind, "LOCAL")
            with self.assertRaises(IntelligenceError):
                LocalCheckpointModel(path=str(path), checkpoint_sha256="0" * 64, model_id="student", revision="r1",
                                     infer=infer, clock_ms=FakeClock(0))

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


class TrainingGateTests(unittest.TestCase):
    def test_training_is_not_run_without_rights_criteria_and_checkpoint_details(self):
        status = check_training_manifest(None)
        self.assertEqual(status["status"], "NOT_RUN")
        self.assertIn("label_rights_reference", status["missing"])

    def test_claude_outputs_and_the_synthetic_pack_are_never_training_labels(self):
        manifest = {k: "x" for k in ("label_rights_reference", "experiment_record_commit", "base_checkpoint_id",
                                     "base_checkpoint_revision", "base_checkpoint_licence", "compute", "budget")}
        manifest.update(base_checkpoint_sha256="a" * 64, dataset_manifest_sha256="b" * 64)
        for source, teacher, problem in (("claude labels", "none", "LABEL_SOURCE_NOT_PERMITTED"),
                                         ("synthetic-eval-pack", "none", "LABEL_SOURCE_NOT_PERMITTED"),
                                         ("team gold set", "Claude via API", "TEACHER_NOT_PERMITTED")):
            with self.subTest(source=source):
                status = check_training_manifest(dict(manifest, label_source=source, teacher=teacher))
                self.assertEqual(status["status"], "NOT_RUN")
                self.assertIn(problem, status["problems"])
        ready = check_training_manifest(dict(manifest, label_source="team gold set", teacher="none"))
        self.assertEqual(ready["status"], "READY_FOR_REVIEW")
        self.assertIn("not approval", ready["note"])


if __name__ == "__main__":
    unittest.main()

"""IDEA-041 AC-2.1..2.3, AC-5.1: hosted adapters for both candidate providers, and the assessment budget.

Transports are fakes that return the providers' documented reply shapes; nothing here reaches a provider.
"""

import json
import time
import unittest

from larp.contracts import Document
from larp.intelligence.common import IntelligenceError
from larp.intelligence.config import LiveModelSettings, load_config
from larp.intelligence.fakes import FakeClock, MemoryArtifacts
from larp.intelligence.providers import ACTION_SCHEMA, AnthropicMessagesModel, OpenAIResponsesModel, hosted_model
from larp.intelligence.scenarios import EXSEMI, build_world
from larp.runtime.schema import assessment_request, assessment_result

SECRET = "sk-synthetic-never-real-0123456789"
FINISH = {"action": "FINISH", "claims": [], "notes": "nothing to add"}


def request(input_=None):
    return Document.from_dict({"schema": "ModelRequest.v1", "request_id": "r:1", "model": {}, "prompt_sha256": "0" * 64,
                               "input": input_ or {"gaps": []}})


def anthropic_reply(output, *, served=None, stop="end_turn", summary="Checked the open gaps; none remain."):
    def make(body):
        content = [{"type": "thinking", "thinking": summary, "signature": "sig-synthetic"}] if summary else []
        content.append({"type": "text", "text": output if isinstance(output, str) else json.dumps(output)})
        return {"id": "msg_synthetic", "type": "message", "role": "assistant", "model": served or body["model"],
                "content": content, "stop_reason": stop, "usage": {"input_tokens": 1200, "output_tokens": 300}}
    return make


def openai_reply(output, *, served=None, status="completed", summary="Compared the facts with the gaps.", refusal=False):
    def make(body):
        part = ({"type": "refusal", "refusal": "no"} if refusal else
                {"type": "output_text", "text": output if isinstance(output, str) else json.dumps(output)})
        out = [{"type": "reasoning", "id": "rs_1", "summary": [{"type": "summary_text", "text": summary}]}] if summary else []
        out.append({"type": "message", "role": "assistant", "content": [part]})
        return {"id": "resp_synthetic", "object": "response", "model": served or body["model"], "status": status,
                "output": out, "usage": {"input_tokens": 1500, "output_tokens": 250}}
    return make


class Adapters(unittest.TestCase):
    def setUp(self):
        self.config, self.clock, self.artifacts, self.sent = load_config(), FakeClock(1_000), MemoryArtifacts(), []

    def transport(self, make, *, latency=900, status=200):
        def send(url, headers, body, timeout_s):
            self.sent.append((url, headers, body, timeout_s))
            self.clock.advance(latency)
            return status, json.dumps(make(json.loads(body))).encode()
        return send

    def build(self, cls, make=None, **kw):
        args = dict(model_id="example-model-id", api_key=SECRET, prompt_text=self.config.prompt_text,
                    prompt_sha256=self.config.prompt_sha256, clock_ms=self.clock, artifacts=self.artifacts,
                    transport=self.transport(make or (anthropic_reply(FINISH) if cls is AnthropicMessagesModel
                                                      else openai_reply(FINISH))),
                    price={"input_micro_usd_per_mtok": 4_000_000, "output_micro_usd_per_mtok": 20_000_000,
                           "source": "synthetic-test-price"})
        args.update(kw)
        return cls(**args)

    def test_construction_refusals(self):
        for cls in (AnthropicMessagesModel, OpenAIResponsesModel):
            for change in ({"endpoint": "https://evil.test/v1/messages"}, {"api_key": ""},
                           {"prompt_sha256": "0" * 64}, {"model_id": "model-latest"}, {"model_id": " padded"},
                           {"model_id": ""}, {"artifacts": None}, {"effort": "extreme"},
                           {"price": {"input_micro_usd_per_mtok": 1.5, "output_micro_usd_per_mtok": 1, "source": "x"}}):
                with self.subTest(cls=cls.__name__, change=change), self.assertRaises(IntelligenceError):
                    self.build(cls, **change)

    def test_anthropic_request_shape_and_recorded_bytes(self):
        model = self.build(AnthropicMessagesModel, effort="high")
        reply = model.step(request(), 60_000).read()
        url, headers, body, _ = self.sent[0]
        sent = json.loads(body)
        self.assertEqual(url, "https://api.anthropic.com/v1/messages")
        self.assertEqual((headers["x-api-key"], headers["anthropic-version"]), (SECRET, "2023-06-01"))
        self.assertEqual(sent["thinking"], {"type": "adaptive", "display": "summarized"})
        self.assertEqual(sent["output_config"], {"effort": "high", "format": {"type": "json_schema",
                                                                             "schema": ACTION_SCHEMA}})
        self.assertNotIn("fallbacks", sent)  # a fallback would answer with an undeclared model
        self.assertEqual((reply["status"], reply["output"], reply["served_model"]), ("OK", FINISH, "example-model-id"))
        self.assertEqual(reply["reasoning_summary"], "Checked the open gaps; none remain.")
        self.assertEqual(reply["usage"], {"input_tokens": 1200, "output_tokens": 300})
        self.assertEqual(reply["cost"]["amount_micro_usd"], (1200 * 4_000_000 + 300 * 20_000_000) // 1_000_000)
        stored = self.artifacts.get(reply["request_payload_artifact"])
        self.assertEqual(stored, body)
        self.assertNotIn(SECRET.encode(), stored)
        self.assertIn(b"sig-synthetic", self.artifacts.get(reply["raw_response_artifact"]))
        self.assertNotIn(SECRET, repr(model))
        self.assertIn("effort=high", model.identity.revision)

    def test_openai_request_shape_and_summary(self):
        model = self.build(OpenAIResponsesModel)
        reply = model.step(request(), 60_000).read()
        url, headers, body, _ = self.sent[0]
        sent = json.loads(body)
        self.assertEqual(url, "https://api.openai.com/v1/responses")
        self.assertEqual(headers["Authorization"], f"Bearer {SECRET}")
        self.assertEqual((sent["reasoning"], sent["text"], sent["store"]),
                         ({"effort": "medium", "summary": "auto"}, {"format": {"type": "json_object"}}, False))
        self.assertEqual((reply["status"], reply["output"], reply["reasoning_summary"]),
                         ("OK", FINISH, "Compared the facts with the gaps."))
        self.assertNotIn(SECRET.encode(), self.artifacts.get(reply["request_payload_artifact"]))

    def test_unusable_replies_are_errors_or_timeouts_never_empty_success(self):
        cases = [
            (AnthropicMessagesModel, anthropic_reply(FINISH, served="other-model"), {}, "ERROR", "SERVED_MODEL_MISMATCH"),
            (AnthropicMessagesModel, anthropic_reply(FINISH, stop="refusal"), {}, "ERROR", "PROVIDER_REFUSAL"),
            (AnthropicMessagesModel, anthropic_reply(FINISH, stop="max_tokens"), {}, "ERROR", "STOP_MAX_TOKENS"),
            (AnthropicMessagesModel, anthropic_reply("not json"), {}, "ERROR", "RESPONSE_UNPARSEABLE"),
            (AnthropicMessagesModel, anthropic_reply("[1, 2]"), {}, "ERROR", "OUTPUT_NOT_JSON_OBJECT"),
            (AnthropicMessagesModel, anthropic_reply(FINISH), {"status": 429}, "ERROR", "HTTP 429"),
            (AnthropicMessagesModel, anthropic_reply(FINISH), {"latency": 70_000}, "TIMEOUT", "DEADLINE_EXCEEDED"),
            (OpenAIResponsesModel, openai_reply(FINISH, status="incomplete"), {}, "ERROR", "STATUS_INCOMPLETE"),
            (OpenAIResponsesModel, openai_reply(FINISH, refusal=True), {}, "ERROR", "PROVIDER_REFUSAL"),
            (OpenAIResponsesModel, openai_reply(FINISH, served="other-model"), {}, "ERROR", "SERVED_MODEL_MISMATCH"),
        ]
        for cls, make, net, status, error in cases:
            with self.subTest(cls=cls.__name__, error=error):
                model = self.build(cls, transport=self.transport(make, **net))
                reply = model.step(request(), 60_000).read()
                self.assertEqual((reply["status"], reply["error"], reply["output"]), (status, error, None))
                self.assertIsNotNone(reply["raw_response_artifact"])  # what came back is kept

    def test_network_failure_and_transport_timeout(self):
        def broken(*_):
            raise ConnectionResetError()

        def slow(*_):
            raise TimeoutError()
        for transport, status in ((broken, "ERROR"), (slow, "TIMEOUT")):
            reply = self.build(AnthropicMessagesModel, transport=transport).step(request(), 60_000).read()
            self.assertEqual(reply["status"], status)
            self.assertIsNone(reply["raw_response_artifact"])
            self.assertIsNotNone(reply["request_payload_artifact"])

    def test_settings_select_the_provider(self):
        settings = LiveModelSettings("openai", "example-model-id", api_key=SECRET)
        model = hosted_model(settings, prompt_text=self.config.prompt_text, prompt_sha256=self.config.prompt_sha256,
                             clock_ms=self.clock, artifacts=self.artifacts)
        self.assertIsInstance(model, OpenAIResponsesModel)
        with self.assertRaises(IntelligenceError):
            hosted_model(LiveModelSettings("other", "m", api_key=SECRET), prompt_text=self.config.prompt_text,
                         prompt_sha256=self.config.prompt_sha256, clock_ms=self.clock, artifacts=self.artifacts)


class ThroughTheAssessor(unittest.TestCase):
    """The adapters behind the real assessor, verifier and budget (AC-2.2, AC-2.3, AC-5.1)."""

    def setUp(self):
        self.w = build_world(["EXSEMI_Q2_8K", "EXSEMI_Q3_8K"])

    def model(self, cls, decide, *, latency=800, real_sleep_s=0.0):
        def send(url, headers, body, timeout_s):
            if real_sleep_s:
                time.sleep(real_sleep_s)
            self.w.clock.advance(latency)
            sent = json.loads(body)
            state = json.loads(sent["messages"][0]["content"] if cls is AnthropicMessagesModel else sent["input"])
            make = anthropic_reply if cls is AnthropicMessagesModel else openai_reply
            return 200, json.dumps(make(decide(state))(sent)).encode()
        return cls(model_id="example-model-id", api_key=SECRET, prompt_text=self.w.config.prompt_text,
                   prompt_sha256=self.w.config.prompt_sha256, clock_ms=self.w.clock, artifacts=self.w.artifacts,
                   transport=send)

    def assess(self, model, **kw):
        request = self.w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="hosted", **kw)
        started = time.monotonic()
        result = self.w.assessor(model).assess(request)
        return request, result, time.monotonic() - started

    @staticmethod
    def rule(state):
        """Behave like the rule baseline: close the first open gap, then confirm the claimable facts."""
        if state["remaining_tool_calls"] > 0 and state["gaps"]:
            gap = state["gaps"][0]
            return {"action": "CALL_TOOL", "tool": gap["tool"], "args": gap["args"]}
        return {"action": "FINISH", "claims": state["claimable"], "notes": "confirmed extracted facts"}

    def test_both_providers_assess_and_records_pass_the_consumer_validator(self):
        for cls in (AnthropicMessagesModel, OpenAIResponsesModel):
            with self.subTest(provider=cls.provider):
                request, result, _ = self.assess(self.model(cls, self.rule))
                r = result.read()
                self.assertEqual(r["status"], "ASSESSED", r["reasons"])
                assessment_request(request, r["run_id"], r["policy_profile_hash"], self.w.clock())
                assessment_result(result, request, self.w.clock())
                self.assertTrue(r["model_io"]["steps"])
                for step in r["model_io"]["steps"]:
                    response = step["response"]
                    for key in ("request_payload_artifact", "raw_response_artifact"):
                        self.assertIsNotNone(self.w.artifacts.get(response[key]))
                self.assertTrue(r["model_io"]["cot"])
                self.assertEqual(r["model"]["provider"], cls.provider)
                self.assertLessEqual(r["budget_used"]["tool_calls"], 6)

    def test_tool_calls_never_exceed_the_budget(self):
        greedy = lambda state: {"action": "CALL_TOOL", "tool": "prior_context", "args": {"metric": "revenue"}}
        _, result, _ = self.assess(self.model(AnthropicMessagesModel, greedy))
        r = result.read()
        self.assertEqual(r["budget_used"]["tool_calls"], 6)
        # Harness facts only, unconfirmed by the model: recorded as incomplete, so the evidence cannot look clear.
        self.assertIn("TOOL_BUDGET_EXHAUSTED", r["missingness"])
        self.assertFalse(r["coverage"]["complete"])

    def test_over_deadline_model_gives_unavailable_within_the_deadline(self):
        """AC-2.3: a model slower than the deadline cannot block the round; the result is not ASSESSED."""
        _, result, elapsed = self.assess(self.model(AnthropicMessagesModel, self.rule, real_sleep_s=2.0),
                                         deadline_ms=300)
        r = result.read()
        self.assertLess(elapsed, 1.5)
        self.assertEqual((r["status"], r["reasons"]), ("UNAVAILABLE", ["ASSESSMENT_DEADLINE_EXCEEDED"]))
        self.assertIsNone(r["proposed_thesis"])
        _, result, _ = self.assess(self.model(AnthropicMessagesModel, self.rule, latency=61_000))
        self.assertEqual(result.read()["reasons"], ["MODEL_TIMEOUT"])

    def test_invalid_model_output_abstains(self):
        for output in ({"action": "FINISH", "claims": [], "notes": "x", "orders": []}, {"action": "SELL"}):
            with self.subTest(output=output):
                _, result, _ = self.assess(self.model(AnthropicMessagesModel, lambda state, o=output: o))
                self.assertEqual(result.read()["status"], "ABSTAIN")


if __name__ == "__main__":
    unittest.main()

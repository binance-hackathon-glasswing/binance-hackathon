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


# ---------------------------------------------------------------------------------------- R02, R06, R10 (PR #15 review)
# Anthropic structured outputs (platform.claude.com, "JSON schema limitations", read 2026-10-12): every object needs
# additionalProperties false; no numeric/string-length constraints; arrays only minItems 0 or 1; no recursion; at
# most 24 optional and 16 union-typed parameters per request; an unsupported schema is refused with HTTP 400.
ALLOWED_KEYWORDS = {"type", "properties", "required", "additionalProperties", "items", "enum", "const", "anyOf",
                    "allOf", "description", "minItems", "default", "format", "$ref", "$defs", "definitions"}


def provider_schema_violations(schema) -> list:
    """Independent re-implementation of the documented limits, so the test does not trust the production checker."""
    out, counts = [], {"optional": 0, "union": 0}

    def walk(node, path):
        if not isinstance(node, dict):
            out.append(f"{path}: not a schema object")
            return
        out.extend(f"{path}: unsupported keyword {k}" for k in set(node) - ALLOWED_KEYWORDS)
        if "$ref" in node:
            out.append(f"{path}: $ref (recursion risk) not expected here")
        types = node.get("type")
        if isinstance(types, list) or "anyOf" in node:
            counts["union"] += 1
        if types == "object" or "properties" in node:
            if node.get("additionalProperties") is not False:
                out.append(f"{path}: object without additionalProperties false")
            props = node.get("properties", {})
            counts["optional"] += len(set(props) - set(node.get("required", [])))
            out.extend(f"{path}: required {k} not a property" for k in set(node.get("required", [])) - set(props))
            for key, sub in props.items():
                walk(sub, f"{path}.{key}")
        if "items" in node:
            walk(node["items"], f"{path}[]")
        if node.get("minItems") not in (None, 0, 1):
            out.append(f"{path}: minItems {node['minItems']}")
        for i, sub in enumerate(node.get("anyOf", [])):
            walk(sub, f"{path}|{i}")
    walk(schema, "$")
    if counts["optional"] > 24:
        out.append(f"{counts['optional']} optional parameters > 24")
    if counts["union"] > 16:
        out.append(f"{counts['union']} union-typed parameters > 16")
    return out


def schema_errors(value, schema, path="$") -> list:
    """Minimal JSON-schema instance check for the keywords the action schema uses (what constrained decoding allows)."""
    if "anyOf" in schema:
        return [] if any(not schema_errors(value, s, path) for s in schema["anyOf"]) else [f"{path}: no anyOf branch"]
    if "const" in schema and value != schema["const"]:
        return [f"{path}: not {schema['const']!r}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}: {value!r} not in enum"]
    kinds = {"object": dict, "array": list, "string": str, "null": type(None), "boolean": bool}
    wanted = schema.get("type")
    if wanted is not None:
        names = wanted if isinstance(wanted, list) else [wanted]
        ok = any((type(value) is int if n == "integer" else type(value) in (int, float) if n == "number"
                  else type(value) is kinds[n]) for n in names)
        if not ok:
            return [f"{path}: type {type(value).__name__} not {wanted}"]
    errors = []
    if isinstance(value, dict) and "properties" in schema:
        errors += [f"{path}: extra key {k}" for k in set(value) - set(schema["properties"])]
        errors += [f"{path}: missing {k}" for k in schema.get("required", []) if k not in value]
        for k, v in value.items():
            if k in schema["properties"]:
                errors += schema_errors(v, schema["properties"][k], f"{path}.{k}")
    if isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            errors += schema_errors(v, schema["items"], f"{path}[{i}]")
    return errors


def model_claim(claim: dict) -> dict:
    """A claimable fact as a model states it under the schema: decimals as strings, the source by its record ID, and
    nothing the harness sets itself (basis, precision)."""
    from decimal import Decimal

    def dec(v):
        return None if v is None else (str(Decimal(v[0]) / Decimal(v[1])) if isinstance(v, list) else v)
    out = {k: claim.get(k) for k in ("kind", "metric", "period", "unit", "scale_exp10", "direction", "security_scope",
                                      "span", "period_span", "scale_span", "statement")}
    out.update(value=dec(claim.get("value")), tolerance_pct=dec(claim.get("tolerance_pct")),
               range=None if claim.get("range") is None else [dec(v) for v in claim["range"]],
               source=None if not (claim.get("source") or {}).get("record_id") else
               {"record_id": claim["source"]["record_id"]})
    if out["statement"] is not None:
        out["statement"] = {k: out["statement"].get(k) for k in ("assertion", "actor", "temporal", "effective")}
    return out


class AnthropicSchema(unittest.TestCase):
    """R02 (Keith P1, Keegan 2): a closed, provider-compatible schema that still admits every valid action."""

    def setUp(self):
        self.w = build_world(["EXSEMI_Q2_8K", "EXSEMI_Q3_8K", "EXSEMI_402_8K"])

    def claimable(self, key):
        from larp.intelligence.models import RuleBaselineModel
        r = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(
            self.w.request([key], issuer_id=EXSEMI, job_id=f"c-{key}")).read()
        return r["model_io"]["steps"][-1]["request"]["input"]["claimable"]

    def test_schema_meets_the_documented_limits(self):
        from larp.intelligence.providers import anthropic_schema_problems
        self.assertEqual(provider_schema_violations(ACTION_SCHEMA), [])
        self.assertEqual(anthropic_schema_problems(ACTION_SCHEMA), [])
        for bad in ({"type": "object", "additionalProperties": False, "properties": {"a": {"type": "array",
                                                                                          "minItems": True}}},
                    {"type": "object", "additionalProperties": False, "properties": {"a": {"type": "string",
                                                                                          "format": "regex"}}},
                    {"type": "object", "additionalProperties": False, "properties": {"a": {"enum": [{"x": 1}]}}}):
            with self.subTest(production_checker=bad):
                self.assertTrue(anthropic_schema_problems(bad))
        deep = {"type": "string"}
        for _ in range(60):
            deep = {"type": "object", "additionalProperties": False, "required": ["a"], "properties": {"a": deep}}
        self.assertTrue(anthropic_schema_problems(deep))
        for bad in ({"type": "object", "properties": {"a": {"type": "object"}}},
                    {"type": "object", "additionalProperties": False, "properties": {"a": {"type": "string",
                                                                                          "minLength": 1}}},
                    {"type": "object", "additionalProperties": False,
                     "properties": {f"p{i}": {"type": "string"} for i in range(25)}}):
            with self.subTest(bad=bad):
                self.assertTrue(provider_schema_violations(bad))
                self.assertTrue(anthropic_schema_problems(bad))

    def test_valid_actions_pass_schema_parser_and_claim_checks(self):
        from larp.intelligence.models import parse_output
        from larp.intelligence.verify import claim_schema_error
        claims = [model_claim(c) for key in ("EXSEMI_Q3_8K", "EXSEMI_402_8K") for c in self.claimable(key)]
        kinds = {(c["kind"], c["metric"].split(":")[0] if c["metric"].startswith(("ITEM:", "STATEMENT:")) else "x")
                 for c in claims}
        self.assertTrue({("REPORTED", "x"), ("EVENT", "ITEM")} <= kinds, kinds)
        record = self.w.record("EXSEMI_402_8K")
        examples = [
            {"action": "CALL_TOOL", "tool": "fetch_document", "args": {"accession": record["accession"],
                                                                       "name": record["documents"][0]["name"]}},
            {"action": "CALL_TOOL", "tool": "prior_context", "args": {"metric": "revenue"}},
            {"action": "CALL_TOOL", "tool": "compare_facts", "args": {"metric": "revenue"}},
            {"action": "FINISH", "claims": claims, "notes": "confirmed"},
            {"action": "FINISH", "claims": [], "notes": "nothing verifiable"},
        ]
        for example in examples:
            with self.subTest(action=example["action"], tool=example.get("tool")):
                self.assertEqual(schema_errors(example, ACTION_SCHEMA), [])
                self.assertEqual(parse_output(example), example)
                for claim in example.get("claims", []):
                    self.assertIsNone(claim_schema_error(claim))

    def test_open_or_extra_fields_are_refused_by_the_schema(self):
        claim = model_claim(self.claimable("EXSEMI_Q3_8K")[0])
        for bad in ({"action": "CALL_TOOL", "tool": "prior_context", "args": {"metric": "revenue", "url": "x"}},
                    {"action": "CALL_TOOL", "tool": "browse", "args": {"metric": "revenue"}},
                    {"action": "FINISH", "claims": [dict(claim, basis="TABLE_V1")], "notes": "x"},
                    {"action": "FINISH", "claims": [dict(claim, source={"record_id": "r", "accession": "a"})], "notes": "x"},
                    {"action": "FINISH", "claims": [], "notes": "x", "orders": []},
                    {"action": "SELL"}):
            with self.subTest(bad=bad):
                self.assertTrue(schema_errors(bad, ACTION_SCHEMA))

    def test_adapter_refuses_a_schema_the_provider_would_refuse(self):
        from unittest import mock
        from larp.intelligence import providers
        with mock.patch.object(providers, "ACTION_SCHEMA", {"type": "object", "properties": {"args": {"type": "object"}}}):
            with self.assertRaises(IntelligenceError):
                AnthropicMessagesModel(model_id="example-model-id", api_key=SECRET, prompt_text=self.w.config.prompt_text,
                                       prompt_sha256=self.w.config.prompt_sha256, clock_ms=self.w.clock,
                                       artifacts=self.w.artifacts)

    def test_strict_fake_drives_the_assessor_with_every_claim_verified(self):
        """The fake sends only what the provider's constrained decoding could produce from the schema it was sent."""
        problems = []

        def send(url, headers, body, timeout_s):
            self.w.clock.advance(700)
            sent = json.loads(body)
            schema = sent["output_config"]["format"]["schema"]
            problems.extend(provider_schema_violations(schema))
            state = json.loads(sent["messages"][0]["content"])
            if state["remaining_tool_calls"] > 0 and state["gaps"]:
                output = {"action": "CALL_TOOL", "tool": state["gaps"][0]["tool"], "args": state["gaps"][0]["args"]}
            else:
                output = {"action": "FINISH", "claims": [model_claim(c) for c in state["claimable"]], "notes": "ok"}
            problems.extend(schema_errors(output, schema))
            return 200, json.dumps(anthropic_reply(output)(sent)).encode()
        for key in ("EXSEMI_Q3_8K", "EXSEMI_402_8K"):
            with self.subTest(filing=key):
                model = AnthropicMessagesModel(model_id="example-model-id", api_key=SECRET,
                                               prompt_text=self.w.config.prompt_text,
                                               prompt_sha256=self.w.config.prompt_sha256, clock_ms=self.w.clock,
                                               artifacts=self.w.artifacts, transport=send)
                r = self.w.assessor(model).assess(self.w.request([key], issuer_id=EXSEMI, job_id=f"strict-{key}")).read()
                self.assertEqual(problems, [])
                self.assertEqual(r["status"], "ASSESSED", r["reasons"])
                self.assertEqual(r["rejected_claims"], [])
                self.assertTrue(r["claims"])
                # A restated harness fact confirms that fact; it is not a second, differently identified copy.
                from larp.intelligence.models import RuleBaselineModel
                base = self.w.assessor(RuleBaselineModel(self.w.clock)).assess(
                    self.w.request([key], issuer_id=EXSEMI, job_id=f"base-{key}")).read()
                self.assertEqual(sorted(c["fact_id"] for c in r["claims"]),
                                 sorted(c["fact_id"] for c in base["claims"]))
                self.assertTrue(all(c["model_confirmed"] for c in r["claims"]))


class BytesBeforeParsing(unittest.TestCase):
    """R06 (Keegan 3): request bytes are stored before the call and reply bytes before any parsing."""

    def setUp(self):
        self.config, self.clock, self.artifacts = load_config(), FakeClock(1_000), MemoryArtifacts()

    def model(self, raw, status=200):
        def send(url, headers, body, timeout_s):
            from larp.intelligence.common import sha256_hex
            self.assertEqual(self.artifacts.get(sha256_hex(body)), body)  # stored before the call
            return status, raw
        return AnthropicMessagesModel(model_id="example-model-id", api_key=SECRET, prompt_text=self.config.prompt_text,
                                      prompt_sha256=self.config.prompt_sha256, clock_ms=self.clock,
                                      artifacts=self.artifacts, transport=send)

    def test_hostile_replies_are_errors_and_their_bytes_are_kept(self):
        from larp.intelligence.common import sha256_hex
        text = json.dumps(json.dumps(FINISH))
        message = ('{"id":"m","type":"message","model":"example-model-id","stop_reason":"end_turn",'
                   '"content":[{"type":"text","text":' + text + '}],"usage":{"input_tokens":%s,"output_tokens":1}}')
        cases = {"overflow": (message % "1e400").encode(), "float usage": (message % "12.5").encode(),
                 "negative usage": (message % "-3").encode(), "bool usage": (message % "true").encode(),
                 "huge usage": (message % ("9" * 400)).encode(),
                 "deep nesting": b"[" * 100_000 + b"]" * 100_000, "not utf-8": b"\xff\xfe{}"}
        nested = json.dumps('{"action": ' + "[" * 990 + "]" * 990 + "}")  # parses, but too deep for the record
        cases["parseable deep output"] = (message.replace(text, nested) % "5").encode()
        for name, raw in cases.items():
            with self.subTest(case=name):
                reply = self.model(raw).step(request(), 60_000).read()
                self.assertIn(reply["status"], ("ERROR", "INVALID"))
                self.assertIsNone(reply["output"])
                self.assertEqual(reply["raw_response_artifact"], sha256_hex(raw))
                self.assertEqual(self.artifacts.get(reply["raw_response_artifact"]), raw)
                self.assertIsNotNone(self.artifacts.get(reply["request_payload_artifact"]))


class LateReplyIsKept(unittest.TestCase):
    """Review of R10: a whole reply that arrives after the deadline is a timeout whose bytes are still recorded."""

    def test_late_reply_bytes_are_recorded(self):
        from larp.intelligence.providers import LateReply
        config, artifacts = load_config(), MemoryArtifacts()
        raw = json.dumps(anthropic_reply(FINISH)({"model": "example-model-id"})).encode()

        def late(url, headers, body, timeout_s):
            raise LateReply(200, raw)
        model = AnthropicMessagesModel(model_id="example-model-id", api_key=SECRET, prompt_text=config.prompt_text,
                                       prompt_sha256=config.prompt_sha256, clock_ms=FakeClock(1), artifacts=artifacts,
                                       transport=late)
        reply = model.step(request(), 60_000).read()
        self.assertEqual((reply["status"], reply["output"]), ("TIMEOUT", None))
        self.assertEqual(artifacts.get(reply["raw_response_artifact"]), raw)


class HardTransportDeadline(unittest.TestCase):
    """R10 (Keegan 7): the transport ends the whole exchange by its timeout, even when every single read is quick."""

    def setUp(self):
        import http.server
        import threading

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                trickle = self.path == "/trickle"
                payload = b'{"ok": true}' * (1 if not trickle else 40)
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                try:
                    for i in range(0, len(payload), 4 if trickle else len(payload)):
                        self.wfile.write(payload[i:i + (4 if trickle else len(payload))])
                        self.wfile.flush()
                        if trickle:
                            time.sleep(0.05)
                except OSError:
                    pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def post(self, path, timeout_s):
        import http.client
        from larp.intelligence.providers import post_with_deadline
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=timeout_s)
        return post_with_deadline(conn, path, {"Content-Type": "application/json"}, b"{}", timeout_s)

    def test_fast_reply_is_returned(self):
        self.assertEqual(self.post("/fast", 2.0), (200, b'{"ok": true}'))

    def test_trickling_reply_is_cut_at_the_deadline(self):
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            self.post("/trickle", 0.3)  # 120 bytes, 4 every 50 ms: about 1.5 s in total, each read quick
        self.assertLess(time.monotonic() - started, 0.8)


class InFlightAtTheDeadline(unittest.TestCase):
    """R10: an abandoned assessment points at the stored request bytes of the call still in flight."""

    def test_in_flight_call_is_recorded(self):
        from larp.intelligence.common import sha256_hex
        w, bodies = build_world(["EXSEMI_Q2_8K", "EXSEMI_Q3_8K"]), []

        def send(url, headers, body, timeout_s):
            bodies.append(body)
            time.sleep(1.0)
            return 200, json.dumps(anthropic_reply(FINISH)(json.loads(body))).encode()
        model = AnthropicMessagesModel(model_id="example-model-id", api_key=SECRET, prompt_text=w.config.prompt_text,
                                       prompt_sha256=w.config.prompt_sha256, clock_ms=w.clock, artifacts=w.artifacts,
                                       transport=send)
        r = w.assessor(model).assess(w.request(["EXSEMI_Q3_8K"], issuer_id=EXSEMI, job_id="late",
                                               deadline_ms=200)).read()
        self.assertEqual(r["reasons"], ["ASSESSMENT_DEADLINE_EXCEEDED"])
        flight = r["model_io"]["in_flight"]
        self.assertEqual(flight["request_id"], "late:step:0")
        self.assertEqual(flight["request_payload_sha256"], sha256_hex(bodies[0]))
        self.assertEqual(w.artifacts.get(flight["request_payload_artifact"]), bodies[0])


if __name__ == "__main__":
    unittest.main()

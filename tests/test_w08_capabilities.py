"""Synthetic boundary tests, not evidence of real venue support."""
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from tools import w08_capabilities as w


class Response(io.BytesIO):
    code = 200
    headers = {}


class FakeOpener:
    def __init__(self, raw=b'{"code":0,"data":[]}', error=None):
        self.raw, self.error, self.requests = raw, error, []

    def open(self, request, timeout):
        self.requests.append(request)
        if self.error:
            raise self.error
        return Response(self.raw)


class Boundaries(unittest.TestCase):
    def test_submission_and_path_injection_rejected_before_network(self):
        opener = FakeOpener()
        client = w.ReadClient("fake-key", "fake-secret", opener)
        for method, path in [("POST", "pre-transaction/broadcast-transaction"),
                             ("POST", "aggregator/order"),
                             ("GET", "aggregator/supported/chain?evil=1"),
                             ("GET", "../broadcast-transaction"),
                             ("POST", "aggregator/quote-and-swap")]:
            with self.assertRaises(ValueError):
                client.request(method, path, {})
        self.assertEqual(opener.requests, [])

    def test_signed_get_bytes_equal_transmitted_target(self):
        opener = FakeOpener()
        client = w.ReadClient("fake-key", "fake-secret", opener)
        with patch.object(w, "utc", return_value="2026-10-10T00:00:00.000Z"):
            client.request("GET", "aggregator/supported/chain", {"binanceChainId": "56", "test": "a b&c"})
        request = opener.requests[0]
        target = request.full_url.removeprefix("https://web3.binance.com")
        expected = base64.b64encode(hmac.new(b"fake-secret", ("2026-10-10T00:00:00.000ZGET" + target).encode(), hashlib.sha256).digest()).decode()
        self.assertEqual(request.get_header("X-oc-sign"), expected)

    def test_signed_post_bytes_equal_transmitted_body(self):
        opener = FakeOpener()
        client = w.ReadClient("fake-key", "fake-secret", opener)
        with patch.object(w, "utc", return_value="2026-10-10T00:00:00.000Z"):
            client.request("POST", "pre-transaction/gas-limit", {"binanceChainId": "56", "evmTx": {"value": "0"}})
        request = opener.requests[0]
        message = b"2026-10-10T00:00:00.000ZPOST" + request.full_url.removeprefix("https://web3.binance.com").encode() + request.data
        self.assertEqual(request.get_header("X-oc-sign"), base64.b64encode(hmac.new(b"fake-secret", message, hashlib.sha256).digest()).decode())

    def test_no_redirect_can_forward_credentials(self):
        self.assertIsNone(w.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example"))

    def test_classification_does_not_call_every_403_geoblocking(self):
        self.assertEqual(w.classify(403, {"code": 40304}), "compliance_restriction")
        self.assertEqual(w.classify(403, {}), "http_forbidden_unclassified")
        self.assertEqual(w.classify(200, {"code": 40102}), "authentication_error")
        self.assertEqual(w.classify(200, {"code": 42900}), "rate_limited")
        self.assertNotEqual(w.classify(500, {"code": 0}), "ok")
        self.assertNotEqual(w.classify(200, {"code": False}), "ok")

    def test_retry_after_date_and_seconds(self):
        now = datetime(2026, 10, 10, tzinfo=timezone.utc).timestamp()
        self.assertEqual(w.retry_after("Sat, 10 Oct 2026 00:00:10 GMT", now), 10)
        self.assertEqual(w.retry_after("12", now), 12)
        self.assertIsNone(w.retry_after("bad", now))

    def test_transport_errors_do_not_persist_exception_secrets(self):
        client = w.ReadClient("fake-key", "fake-secret", FakeOpener(error=URLError("fake-secret")))
        record = client.request("GET", "aggregator/supported/chain", {})
        self.assertEqual(record["outcome"], "transport_error")
        self.assertNotIn("fake-secret", json.dumps(record))

    def test_nonjson_and_nonobject_are_not_success(self):
        for raw in [b"<html>fake-secret</html>", b"[]", b"null"]:
            client = w.ReadClient("fake-key", "fake-secret", FakeOpener(raw))
            record = client.request("GET", "aggregator/supported/chain", {})
            self.assertNotEqual(record["outcome"], "ok")
            self.assertNotIn("fake-secret", json.dumps(record))

    def test_json_echoed_credentials_are_redacted(self):
        client = w.ReadClient("fake-key", "fake-secret", FakeOpener(b'{"code":0,"msg":"fake-key fake-secret"}'))
        record = client.request("GET", "aggregator/supported/chain", {})
        self.assertEqual(record["response"]["msg"], "[REDACTED] [REDACTED]")
        self.assertEqual(record["response_sha256"], hashlib.sha256(b'{"code":0,"msg":"fake-key fake-secret"}').hexdigest())

    def test_env_parser_only_selects_permitted_fields_and_environment_wins(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "env"
            path.write_text('WALLET_PRIVATE_KEY="never-use"\nAI_SEEDS_SECRET="never-use"\nBINANCE_API_KEY="file-key"\nBINANCE_SECRET_KEY="file-secret" # comment\n')
            with patch.dict(os.environ, {"BINANCE_API_KEY": "environment-key"}, clear=True):
                self.assertEqual(w.selected_env(path), {"BINANCE_API_KEY": "environment-key", "BINANCE_SECRET_KEY": "file-secret"})

    def test_approve_exact_match_and_malicious_mutations(self):
        data = "0x095ea7b3" + "0" * 24 + w.USDT[2:] + format(17, "064x")
        self.assertEqual(w.inspect_approve(data, w.USDT.upper().replace("0X", "0x"), "17")["amount_base_units"], "17")
        for altered in [data + "00", data[:-2], "0xdeadbeef" + data[10:],
                        data[:10] + "1" + data[11:], data[:-64] + format(18, "064x"),
                        data[:34] + "1" * 40 + data[74:]]:
            with self.assertRaises(ValueError):
                w.inspect_approve(altered, w.USDT, "17")

    def test_unknown_swap_never_trusts_json_minimum_or_expiry(self):
        record = {"outcome": "ok", "response": {"data": [{"tx": {
            "data": "0xdeadbeef" + "0" * 64, "to": w.USDT,
            "minReceiveAmount": "123", "deadline": "9999999999"}}]}}
        result = w.inspect_quote(record)
        self.assertEqual(result["selector"], "0xdeadbeef")
        for field in ["signable", "encoded_deadline_verified", "encoded_minimum_verified"]:
            self.assertFalse(result[field])
        record["response"]["data"].append({"tx": {}})
        self.assertEqual(w.inspect_quote(record)["outcome"], "missing_or_ambiguous_payload")

    def test_compliance_stops_after_first_call(self):
        client = w.ReadClient("fake-key", "fake-secret", FakeOpener(b'{"code":40304}'))
        with self.assertRaises(RuntimeError):
            w.collect(client, w.USDT, ["NVDAB"], "1", [])
        self.assertEqual(len(client.records), 1)

    def test_invalid_amounts_rejected(self):
        for amount in ["0", "-1", "1.5", "01", "1e18", str(2**256), None]:
            with self.assertRaises(ValueError):
                w.positive_units(amount)


if __name__ == "__main__":
    unittest.main()

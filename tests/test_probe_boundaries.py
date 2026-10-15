"""Offline signed-probe boundaries; never load private credentials or contact a host."""
import base64
from contextlib import ExitStack, redirect_stdout
import hashlib
import hmac
import io
import json
import unittest
from unittest.mock import patch

import requests

import binance_test
from tools import probe_candles, probe_quote
from tools.probe_http import ProbeStopped


class Response:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status
        self.content = json.dumps(body).encode()
        self.headers = {"Location": "https://other.example", "Retry-After": "infinity"}

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


class ProbeBoundaries(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(binance_test, "api_key", "fixture-key"))
        self.stack.enter_context(patch.object(binance_test, "secret_key", "fixture-secret"))
        for module in (probe_quote, probe_candles):
            self.stack.enter_context(patch.object(module, "API_KEY", "fixture-key"))
            self.stack.enter_context(patch.object(module, "SECRET", "fixture-secret"))
            self.stack.enter_context(patch.object(module, "_last_call", 0))
            self.stack.enter_context(patch.object(module.time, "sleep"))
        self.stack.enter_context(patch.object(probe_quote, "RAW", []))

    @staticmethod
    def invoke(module):
        with redirect_stdout(io.StringIO()):
            if module is binance_test:
                return module.binance_get("/api/v1/dex/aggregator/supported/chain", {"space": "a b&c"})[1]
            result = module.get("/api/v1/dex/aggregator/supported/chain", {"space": "a b&c"})
            return result[1] if module is probe_quote else result

    def test_no_redirect_and_credential_echo_redacted_with_identical_signed_target(self):
        for module in (binance_test, probe_quote, probe_candles):
            signatures = []

            def request(url, *, headers, timeout, allow_redirects):
                self.assertFalse(allow_redirects)
                signature = headers["X-OC-SIGN"]
                signatures.append(signature)
                target = url.removeprefix("https://web3.binance.com")
                expected = base64.b64encode(hmac.new(b"fixture-secret",
                    (headers["X-OC-TIMESTAMP"] + "GET" + target).encode(), hashlib.sha256).digest()).decode()
                self.assertEqual(signature, expected)
                return Response({"code": 0, "fixture-key": ["fixture-secret", {signature: signature}]})

            with self.subTest(module=module.__name__), patch.object(module.requests, "get", side_effect=request):
                body = self.invoke(module)
                stored = json.dumps({"body": body, "raw": probe_quote.RAW})
                self.assertEqual(body["code"], 0)
                for secret in ("fixture-key", "fixture-secret", *signatures):
                    self.assertNotIn(secret, stored)

    def test_malformed_or_http_error_never_success(self):
        for module in (binance_test, probe_quote, probe_candles):
            for body, status in [(None, 200), ([], 200), ({"code": False}, 200),
                                 ({"code": 0.0}, 200), ({"code": 0}, 500), ({"code": 0}, 302)]:
                with self.subTest(module=module.__name__, body=body, status=status), patch.object(
                        module.requests, "get", return_value=Response(body, status)) as request:
                    self.assertIsNone(self.invoke(module)["code"])
                    self.assertEqual(request.call_count, 1)

    def test_all_refusals_stop_candle_discovery_and_quote_collection(self):
        for module in (probe_quote, probe_candles):
            for code, status in [(40100, 200), (40101, 200), (40102, 200), (40103, 200),
                                 (40104, 200), (40304, 200), (42900, 200), (1, 401),
                                 (1, 403), (1, 429)]:
                with self.subTest(module=module.__name__, code=code, status=status), patch.object(
                        module.requests, "get", return_value=Response({"code": code}, status)) as request:
                    with self.assertRaises(ProbeStopped):
                        if module is probe_candles:
                            module.find_max_limit(module.TOKENS["NVDAB"], [])
                        else:
                            module.quote_swap(1, module.USDT, module.TOKENS["NVDAB"], module.USDT, "1")
                    self.assertEqual(request.call_count, 1)

    def test_network_failure_is_sanitized_and_retry_bounded(self):
        for module in (probe_quote, probe_candles):
            with self.subTest(module=module.__name__), patch.object(module.requests, "get", side_effect=
                    requests.RequestException("fixture-key fixture-secret")) as request:
                body = self.invoke(module)
                self.assertIsNone(body["code"])
                self.assertEqual(request.call_count, 4)
                stored = json.dumps({"body": body, "raw": probe_quote.RAW})
                self.assertNotIn("fixture-key", stored)
                self.assertNotIn("fixture-secret", stored)

    def test_nonjson_output_does_not_echo_body(self):
        response = Response(None)
        response.body = ValueError("fixture-secret")
        response.content = b"<html>fixture-key fixture-secret</html>"
        for module in (binance_test, probe_quote, probe_candles):
            with self.subTest(module=module.__name__), patch.object(module.requests, "get", return_value=response):
                body = self.invoke(module)
                self.assertIsNone(body["code"])
                self.assertNotIn("fixture-secret", json.dumps(body))

    def test_malformed_quote_never_becomes_sell_amount(self):
        for data in [False, "text", [None], [{}, {}], {"routerResult": []},
                     {"routerResult": {"toTokenAmount": "NaN"}},
                     {"routerResult": {"toTokenAmount": "-1"}},
                     {"routerResult": {"toTokenAmount": str(2**256)}},
                     {"routerResult": {"toTokenAmount": "1"}, "tx": "wrong"}]:
            with self.subTest(data=data), patch.object(probe_quote.requests, "get",
                    return_value=Response({"code": 0, "data": data})):
                result, error = probe_quote.quote_swap(1, probe_quote.USDT, probe_quote.TOKENS["NVDAB"],
                                                       probe_quote.USDT, "1")
                self.assertIsNone(result)
                self.assertTrue(error)

    def test_malformed_candle_rows_have_explicit_unavailable_summary(self):
        for rows in ["text", {}, [None], [[1]], [[1, 2, 3, 4, 5, "bad"]],
                     [[1, 2, 3, 4, 5, 10**100]]]:
            with self.subTest(rows=rows):
                result = probe_candles.summarise(rows, "1h", 10)
                self.assertEqual(result["rows"], 0)

    def test_importing_signed_helpers_does_not_load_dotenv(self):
        import importlib
        import dotenv

        with patch.object(dotenv, "load_dotenv") as load:
            for module in (binance_test, probe_quote, probe_candles):
                importlib.reload(module)
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()

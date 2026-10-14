"""IDEA-047 R9: parsing a pending request has bounded size/depth and never poisons later requests."""
from dataclasses import asdict
import json
import unittest
from unittest.mock import patch

from larp.execution import Blocked, Gates, canonical, digest
from larp.execution_live import signing


def request():
    return dict(schema=signing.SCHEMA, run_id='synthetic', economic_key='order', attempt_id='attempt',
                step='APPROVE', payload_hash='a' * 64, epoch=1, guard_version=1, requested_s=1,
                gates=asdict(Gates(epoch=1, state_version=1, nonce=0, observed_at=1, expires_at=2)))


class RequestBudgets(unittest.TestCase):
    def test_size_and_depth_are_checked_before_json_parsing(self):
        for raw in (b' ' * (signing.MAX_REQUEST_BYTES + 1),
                    b'{"x":' * (signing.MAX_REQUEST_DEPTH + 1) + b'0' + b'}' * (signing.MAX_REQUEST_DEPTH + 1)):
            with self.subTest(size=len(raw)), patch.object(signing.json, 'loads') as loads:
                with self.assertRaises(Blocked):
                    signing.read_request('unused', raw)
                loads.assert_not_called()

    def test_budget_ignores_brackets_and_escaped_quotes_in_strings(self):
        value = request()
        value['economic_key'] = '[{' * 100 + '"\\' + '}]' * 100
        parsed, _ = signing.read_request(digest(value), canonical(value).encode())
        self.assertEqual(parsed, value)

    def test_last_allowed_depth_parses_and_recursion_error_is_a_refusal(self):
        value = request()
        nested = 0
        for _ in range(signing.MAX_REQUEST_DEPTH - 1):
            nested = [nested]
        value['extra'] = nested
        signing.read_request(digest(value), canonical(value).encode())
        with patch.object(signing.json, 'loads', side_effect=RecursionError):
            with self.assertRaisesRegex(Blocked, 'malformed signing request'):
                signing.read_request('unused', b'{}')

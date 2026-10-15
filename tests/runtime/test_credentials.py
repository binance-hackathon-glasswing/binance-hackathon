"""Runtime secrets from Secrets Manager, never the environment (IDEA-042 S1-S3; review comment V4)."""

import json
import os
import unittest
from unittest.mock import patch

from larp.runtime.credentials import Secrets, load_runtime_secrets, runtime_secrets
from larp.runtime.live import LiveStartRefused

WALLET = '0x' + 'a' * 40
VALUES = dict(AI_SEEDS_ADDRESS=WALLET, BINANCE_API_KEY='api-key-value', BINANCE_SECRET_KEY='s3cret-value')


class Client:
    """A fake Secrets Manager client; `fail` raises an error whose text carries a value, as a provider's might."""

    def __init__(self, secret=None, fail=False):
        self.secret, self.fail, self.calls = secret, fail, []

    def get_secret_value(self, SecretId):
        self.calls.append(SecretId)
        if self.fail:
            # A definite refusal whose text carries a value. Unclassified and transient failures are retried by the
            # supervisor instead of refused (IDEA-049 D-FND-003, tests/runtime/test_final_review_d.py).
            from botocore.exceptions import ClientError
            raise ClientError({'Error': {'Code': 'AccessDeniedException',
                                         'Message': 'denied while reading s3cret-value'}}, 'GetSecretValue')
        return {'SecretString': self.secret}


class Loader(unittest.TestCase):
    def refused(self, fragment, client, secret_id='larp/runtime'):
        with self.assertRaises(LiveStartRefused) as caught:
            load_runtime_secrets(client, secret_id)
        self.assertIn(fragment, str(caught.exception))
        for value in VALUES.values():
            if value != WALLET:
                self.assertNotIn(value, str(caught.exception))  # S1: never a value in an error
        return caught.exception

    def test_s1_one_read_returns_the_runtime_names_only(self):
        client = Client(json.dumps(dict(VALUES, NOTE='ignored')))
        secrets = load_runtime_secrets(client, 'larp/runtime')
        self.assertEqual(client.calls, ['larp/runtime'])
        self.assertEqual(dict(secrets), VALUES)
        self.assertEqual(repr(secrets), 'Secrets(AI_SEEDS_ADDRESS, BINANCE_API_KEY, BINANCE_SECRET_KEY)')
        self.assertNotIn('s3cret-value', str(secrets))

    def test_s1_s3_refusals(self):
        self.refused('another host', Client(json.dumps(dict(VALUES, AI_SEEDS_SECRET='audit-secret'))))
        self.refused('another host', Client(json.dumps(dict(VALUES, WALLET_PRIVATE_KEY='key'))))
        self.refused('another host', Client(json.dumps(dict(VALUES, WALLET_MNEMONIC='words'))))
        self.refused('not a JSON object', Client('s3cret-value'))
        self.refused('non-empty strings', Client(json.dumps(dict(VALUES, BINANCE_API_KEY=''))))
        self.refused('non-empty strings', Client(json.dumps(['s3cret-value'])))
        self.refused('unavailable: AccessDeniedException', Client(fail=True))
        self.refused('No runtime secret source', Client(json.dumps(VALUES)), secret_id='')


class Service(unittest.TestCase):
    def test_s2_offline_and_paper_load_nothing(self):
        for mode in ('offline', 'paper'):
            self.assertEqual(runtime_secrets(dict(mode=mode), client_factory=lambda: self.fail('no load')), {})

    def test_s2_live_needs_a_secret_id_and_ignores_the_environment(self):
        with patch.dict(os.environ, dict(VALUES, AI_SEEDS_SECRET='audit-secret')):
            with self.assertRaises(LiveStartRefused):
                runtime_secrets(dict(mode='live'), client_factory=lambda: Client(json.dumps(VALUES)))
            with self.assertRaises(LiveStartRefused):  # no region: refused, not a crash
                runtime_secrets(dict(mode='live', runtime_secret_id='larp/runtime'))
            secrets = runtime_secrets(dict(mode='dev', runtime_secret_id='larp/runtime'),
                                      client_factory=lambda: Client(json.dumps(dict(VALUES, BINANCE_API_KEY='from-sm'))))
        self.assertIsInstance(secrets, Secrets)
        self.assertEqual(secrets['BINANCE_API_KEY'], 'from-sm')  # the store's value, not the environment's
        self.assertNotIn('AI_SEEDS_SECRET', secrets)

    def test_s2_the_service_never_reads_the_environment(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[2] / 'larp/runtime/service.py').read_text(encoding='utf-8')
        self.assertNotIn('os.environ', source)
        self.assertNotIn('import os', source)

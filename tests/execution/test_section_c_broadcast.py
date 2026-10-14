"""C-REQ-007/008/010/011/012: fake HTTP only; no real transaction bytes."""
import base64
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from larp.execution import DependencyUnavailable
from larp.execution_live.loop import Web3Broadcaster
from tests.marketdata.test_transport import Opener


class BroadcastRequirements(unittest.TestCase):
    wallet = '0x' + '5' * 40
    raw = '0x' + 'f8ab' * 40  # arbitrary fixture bytes, not an EVM signature
    tx_hash = '0x' + 'c' * 64

    def client(self, root, opener):
        client = Web3Broadcaster('fixture-key', 'fixture-secret', wallet=self.wallet,
                                artifacts=root, opener=opener)
        client.client.min_interval = 0
        return client

    def test_c_req_012_signed_parameter_reflections_are_not_exported(self):
        echoes = (self.raw, self.raw[2:], self.raw.upper(), self.raw[2:].upper())
        variants = [json.dumps(dict(code=0, data=[dict(txHash=self.tx_hash)], echo=v)).encode()
                    for v in echoes]
        variants += [
            json.dumps(dict(code=0, data=[dict(txHash=self.tx_hash)], echo={self.raw: [self.raw]})).encode(),
            ('{"code":0,"echo":"\\u0030' + self.raw[1:] + '","echo":"safe",'
             '"data":[{"txHash":"' + self.tx_hash + '"}]}').encode(),
        ]
        for response in variants:
            with self.subTest(response=response), tempfile.TemporaryDirectory() as root:
                opener = Opener(response)
                self.assertEqual(self.client(root, opener).send(self.raw), self.tx_hash)
                self.assertEqual(len(opener.calls), 1)
                [path] = list(Path(root).glob('*.json'))
                record = json.loads(path.read_bytes())
                self.assertNotIn('response_body_base64', record)
                for echo in echoes:
                    self.assertNotIn(echo, path.read_text())
                self.assertEqual(record['params']['signedTransaction'],
                                 'sha256:' + hashlib.sha256(self.raw.encode()).hexdigest())
                self.assertEqual(record['response_sha256'], hashlib.sha256(response).hexdigest())

    def test_c_req_012_business_rejection_does_not_export_signed_bytes(self):
        response = json.dumps(dict(code=50000, msg=self.raw, data=[])).encode()
        with tempfile.TemporaryDirectory() as root:
            opener = Opener(response)
            with self.assertRaises(DependencyUnavailable) as error:
                self.client(root, opener).send(self.raw)
            self.assertNotIn(self.raw, str(error.exception))
            self.assertEqual(len(opener.calls), 1)
            [path] = list(Path(root).glob('*.json'))
            record = json.loads(path.read_bytes())
            self.assertEqual(record['outcome'], 'api_or_http_error')
            self.assertNotIn('response_body_base64', record)
            self.assertNotIn(self.raw[2:], path.read_text())

    def test_c_req_007_broadcast_hmac_binds_exact_body_and_retains_public_evidence(self):
        response = b'{ "code":0,"data":[{"txHash":"' + self.tx_hash.encode() + b'","orderId":"o-1"}] }'
        stamp = '2026-10-15T00:00:00.123Z'
        with tempfile.TemporaryDirectory() as root, patch('larp.marketdata.web3.utc', return_value=stamp):
            opener = Opener(response)
            self.assertEqual(self.client(root, opener).send(self.raw), self.tx_hash)
            [request] = opener.calls
            body = request.data
            expected = base64.b64encode(hmac.new(
                b'fixture-secret', stamp.encode() + b'POST/build/api/v1/dex/pre-transaction/broadcast-transaction'
                + body, hashlib.sha256).digest()).decode()
            self.assertEqual(request.get_header('X-oc-sign'), expected)
            self.assertEqual(json.loads(body), dict(binanceChainId='56', signedTransaction=self.raw,
                                                   address=self.wallet))
            [path] = list(Path(root).glob('*.json'))
            self.assertEqual(base64.b64decode(json.loads(path.read_bytes())['response_body_base64']), response)

    def test_c_req_011_ambiguous_transport_failure_is_not_retried(self):
        class Timeout:
            calls = 0

            def open(inner, request, timeout):
                inner.calls += 1
                raise URLError(self.raw)

        with tempfile.TemporaryDirectory() as root:
            opener = Timeout()
            with self.assertRaises(DependencyUnavailable) as error:
                self.client(root, opener).send(self.raw)
            self.assertEqual(opener.calls, 1)
            self.assertNotIn(self.raw, str(error.exception))
            [path] = list(Path(root).glob('*.json'))
            self.assertNotIn(self.raw[2:], path.read_text())

    def test_c_req_010_malformed_success_envelopes_stay_unknown(self):
        for body in ({'code': False, 'data': [{'txHash': self.tx_hash}]},
                     {'code': '0', 'data': [{'txHash': self.tx_hash}]},
                     {'data': [{'txHash': self.tx_hash}]}, {'code': 0, 'data': []},
                     {'code': 0, 'data': [{'txHash': None}]}):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as root:
                opener = Opener(json.dumps(body).encode())
                with self.assertRaises(DependencyUnavailable):
                    self.client(root, opener).send(self.raw)
                self.assertEqual(len(opener.calls), 1)

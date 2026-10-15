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
        mixed = '0x' + 'f8Ab' * 40
        echoes = (self.raw, self.raw[2:], self.raw.upper(), self.raw[2:].upper(), mixed,
                  base64.b64encode(self.raw.encode()).decode(),
                  base64.b64encode(bytes.fromhex(self.raw[2:])).decode())
        variants = [json.dumps(dict(code=0, data=[dict(txHash=self.tx_hash)], echo=v)).encode()
                    for v in echoes]
        variants += [
            json.dumps(dict(code=0, data=[dict(txHash=self.tx_hash)], echo={self.raw: [self.raw]})).encode(),
            ('{"code":0,"echo":"\\u0030' + self.raw[1:] + '","echo":"safe",'
             '"data":[{"txHash":"' + self.tx_hash + '"}]}').encode(),
            ('{"code":0,"echo":"\\u0030' + mixed[1:] + '","echo":"safe",'
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

    def encoded_echoes(self):
        mixed = '0x' + 'f8Ab' * 40
        representations = dict(binary=bytes.fromhex(self.raw[2:]), hex=self.raw.encode(),
                               prefixless=self.raw[2:].encode(), mixed=mixed.encode(),
                               mixed_prefixless=mixed[2:].encode(), upper=self.raw.upper().encode(),
                               upper_prefixless=self.raw[2:].upper().encode())
        return {(name, alphabet, padding): encode(raw).decode().rstrip('=') if padding == 'unpadded'
                else encode(raw).decode()
                for name, raw in representations.items()
                for alphabet, encode in (('standard', base64.b64encode), ('urlsafe', base64.urlsafe_b64encode))
                for padding in ('padded', 'unpadded')}

    def test_c_req_012_equivalent_base64_reflections_are_not_exported(self):
        for variant, echo in self.encoded_echoes().items():
            for code in (0, 50000):
                with self.subTest(variant=variant, code=code), tempfile.TemporaryDirectory() as root:
                    response = json.dumps(dict(code=code, data=[dict(txHash=self.tx_hash)],
                                               msg='request: ' + echo, echo={echo: [echo]})).encode()
                    opener = Opener(response)
                    client = self.client(root, opener)
                    if code == 0:
                        self.assertEqual(client.send(self.raw), self.tx_hash)
                    else:
                        with self.assertRaises(DependencyUnavailable) as error:
                            client.send(self.raw)
                        self.assertNotIn(echo, str(error.exception))
                    self.assertEqual(len(opener.calls), 1)
                    [path] = list(Path(root).glob('*.json'))
                    record = json.loads(path.read_bytes())
                    self.assertEqual(record['outcome'], 'ok' if code == 0 else 'api_or_http_error')
                    self.assertNotIn(echo, path.read_text())
                    self.assertNotIn('response_body_base64', record)
                    self.assertEqual(record['raw_body_omitted'], 'private_parameter_reflection')
                    self.assertEqual(record['params']['signedTransaction'],
                                     'sha256:' + hashlib.sha256(self.raw.encode()).hexdigest())
                    self.assertEqual(record['response_sha256'], hashlib.sha256(response).hexdigest())

    def test_c_req_012_overwritten_escaped_base64_reflections_omit_raw_body(self):
        for variant, echo in self.encoded_echoes().items():
            for nested in (False, True):
                with self.subTest(variant=variant, nested=nested), tempfile.TemporaryDirectory() as root:
                    # Escape a Base64 character before the final parser discards
                    # this value. Only the duplicate-preserving scan sees it.
                    escaped = json.dumps('\\u%04x' % ord(echo[0]) + echo[1:]).replace('\\\\u', '\\u')
                    reflected = '"echo":' + escaped + ',"echo":"safe"'
                    if nested:
                        reflected = '"diagnostic":{' + reflected + '}'
                    response = ('{"code":0,' + reflected
                                + ',"data":[{"txHash":"' + self.tx_hash + '"}]}').encode()
                    opener = Opener(response)
                    self.assertEqual(self.client(root, opener).send(self.raw), self.tx_hash)
                    self.assertEqual(len(opener.calls), 1)
                    [path] = list(Path(root).glob('*.json'))
                    record = json.loads(path.read_bytes())
                    self.assertNotIn(echo, path.read_text())
                    self.assertNotIn('response_body_base64', record)
                    self.assertEqual(record['raw_body_omitted'], 'private_parameter_reflection')
                    self.assertEqual(record['response_sha256'], hashlib.sha256(response).hexdigest())

    def test_c_req_012_unrelated_base64_keeps_exact_public_evidence(self):
        echo = base64.urlsafe_b64encode(b'unrelated public response evidence').decode().rstrip('=')
        response = json.dumps(dict(code=0, data=[dict(txHash=self.tx_hash)], public=echo)).encode()
        with tempfile.TemporaryDirectory() as root:
            opener = Opener(response)
            self.assertEqual(self.client(root, opener).send(self.raw), self.tx_hash)
            self.assertEqual(len(opener.calls), 1)
            [path] = list(Path(root).glob('*.json'))
            record = json.loads(path.read_bytes())
            self.assertEqual(record['response']['public'], echo)
            self.assertEqual(base64.b64decode(record['response_body_base64']), response)

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

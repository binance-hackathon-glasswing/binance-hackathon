"""Malformed and concurrent RPC evidence never becomes execution authority."""
import http.client
import json
import tempfile
import unittest

from larp.execution import Blocked, DependencyUnavailable
from larp.execution_live.chain import ChainEvidence, Rpc, quantity
from larp.marketdata.web3 import Artifacts
from tests.execution.test_live_boundaries import RPC, HASH
from tests.marketdata.test_transport import Opener, Response


class RpcBoundaryTests(unittest.TestCase):
    def test_malformed_envelopes_are_rejected(self):
        for response in ([], None, True, {'jsonrpc': '2.0', 'id': True, 'result': '0x38'},
                         {'jsonrpc': '2.0', 'id': 2, 'result': '0x38'}):
            with self.subTest(response=response), tempfile.TemporaryDirectory() as root:
                rpc = Rpc('https://rpc.example', artifacts=Artifacts(root), source_id='fixture',
                          opener=Opener(json.dumps(response).encode()))
                with self.assertRaises(Blocked):
                    rpc.call('eth_chainId', [])

    def test_a_truncated_or_malformed_http_response_is_unavailable(self):
        # #64 (WR22) item 2: http.client.HTTPException is neither URLError nor OSError.
        class Truncated(Response):
            def read(self, n): raise http.client.IncompleteRead(b'{"jsonrpc":"2.0","id":1,"res', 100)
        class TruncatedOpener:
            def open(self, request, timeout): return Truncated(b'')
        class BadStatus:
            def open(self, request, timeout): raise http.client.BadStatusLine('garbled')
        for opener in (TruncatedOpener(), BadStatus()):
            with self.subTest(opener=type(opener).__name__), tempfile.TemporaryDirectory() as root:
                rpc = Rpc('https://rpc.example', artifacts=Artifacts(root), source_id='fixture', opener=opener)
                with self.assertRaisesRegex(DependencyUnavailable, 'RPC unavailable'):
                    rpc.call('eth_chainId', [])

    def test_interleaved_requests_bind_their_own_response_ids(self):
        class InterleavingOpener:
            rpc = None
            def __init__(self): self.ids = []
            def open(self, request, timeout):
                request_id = json.loads(request.data)['id']
                self.ids.append(request_id)
                if request_id == 1:
                    self.rpc.call('eth_chainId', [])
                return Response(json.dumps({'jsonrpc': '2.0', 'id': request_id, 'result': '0x38'}).encode())
        with tempfile.TemporaryDirectory() as root:
            opener = InterleavingOpener()
            opener.rpc = Rpc('https://rpc.example', artifacts=Artifacts(root), source_id='fixture', opener=opener)
            self.assertEqual(opener.rpc.call('eth_chainId', []), '0x38')
            self.assertEqual(opener.ids, [1, 2])

    def test_malformed_receipt_and_transaction_fields_are_sanitized(self):
        for method, response in (('eth_getTransactionByHash', []),
                                 ('eth_getTransactionReceipt', {'untrusted': 'PRIVATE_MARKER'}),
                                 ('eth_getBlockByNumber', 'PRIVATE_MARKER')):
            class Malformed(RPC):
                def call(self, current, params):
                    return response if current == method else super().call(current, params)
            with self.subTest(method=method), self.assertRaisesRegex(Blocked, 'RPC evidence schema rejected'):
                ChainEvidence(Malformed()).outcome(HASH)

    def test_canonical_final_head_must_bind_height_as_well_as_hash(self):
        class WrongHeight(RPC):
            def call(self, method, params):
                result = super().call(method, params)
                if method == 'eth_getBlockByNumber' and params == ['0xc', False]:
                    result = dict(result, number='0xb')
                return result
        with self.assertRaisesRegex(Blocked, 'finalized head is not canonical'):
            ChainEvidence(WrongHeight()).outcome(HASH)

    def test_rpc_quantities_are_bounded_to_uint256(self):
        self.assertEqual(quantity(hex(2**256 - 1)), 2**256 - 1)
        with self.assertRaises(Blocked):
            quantity(hex(2**256))

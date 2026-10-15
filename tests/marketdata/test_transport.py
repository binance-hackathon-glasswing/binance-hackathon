import base64
import hashlib
import hmac
import json
import tempfile
import unittest
from larp.marketdata.web3 import Web3Client,Artifacts,Unavailable,NoRedirect

class Response:
    code=200
    def __init__(self,body):self.body=body
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def read(self,n):return self.body
class Opener:
    def __init__(self,body):self.body=body;self.calls=[]
    def open(self,request,timeout):self.calls.append(request);return Response(self.body)

class TransportTests(unittest.TestCase):
    def test_exact_signed_post_bytes_and_read_allowlist(self):
        with tempfile.TemporaryDirectory() as root:
            o=Opener(b'{"code":0,"data":[]}');c=Web3Client('fixture-api-key','fixture-secret',artifacts=Artifacts(root),opener=o)
            c.request('POST','balance/token-balances-by-address',{'address':'0x'+'1'*40})
            r=o.calls[0];stamp=r.get_header('X-oc-timestamp')
            expected=base64.b64encode(hmac.new(b'fixture-secret',stamp.encode()+b'POST/build/api/v1/dex/balance/token-balances-by-address'+r.data,hashlib.sha256).digest()).decode()
            self.assertEqual(r.get_header('X-oc-sign'),expected)
            with self.assertRaises(Unavailable):c.request('POST','pre-transaction/broadcast-transaction',{})
            self.assertEqual(len(o.calls),1)
    def test_reflected_credentials_are_redacted(self):
        with tempfile.TemporaryDirectory() as root:
            o=Opener(b'{"code":0,"data":{"echo":"fixture-secret"}}')
            r=Web3Client('fixture-api-key','fixture-secret',artifacts=Artifacts(root),opener=o).request('GET','market/rwa/tokens',{})
            self.assertNotIn('fixture-secret',json.dumps(r))

    def test_escaped_credential_reflections_never_retain_reversible_raw_body(self):
        for raw in (b'{"code":0,"data":{"echo":"fixture-\\u0073ecret"}}',
                    b'{"code":0,"data":{"fixture-\\u0073ecret":"echo"}}',
                    b'{"code":0,"data":"fixture-\\u0073ecret","data":[]}',  # an earlier duplicate key
                    b'{"code":0,"data":["fixture\\u002d\\u0073ecret"]}'):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as root:
                r = Web3Client('fixture-api-key', 'fixture-secret', artifacts=Artifacts(root),
                               opener=Opener(raw)).request('GET', 'market/rwa/tokens', {})
                self.assertNotIn('response_body_base64', r)
                self.assertEqual(r['raw_body_omitted'], 'credential_reflection')
                from pathlib import Path
                artifact = json.loads((Path(root) / (r['artifact_sha256'] + '.json')).read_bytes())
                self.assertNotIn('fixture-secret', json.dumps(artifact))
                self.assertNotIn('response_body_base64', artifact)

    def test_untainted_response_keeps_exact_raw_evidence(self):
        raw = b'{ "code":0, "data":{"public":"value"} }'
        with tempfile.TemporaryDirectory() as root:
            r = Web3Client('fixture-api-key', 'fixture-secret', artifacts=Artifacts(root),
                           opener=Opener(raw)).request('GET', 'market/rwa/tokens', {})
            self.assertEqual(base64.b64decode(r['response_body_base64']), raw)
    def test_business_error_and_redirect_do_not_succeed(self):
        with tempfile.TemporaryDirectory() as root:
            c=Web3Client('fixture-api-key','fixture-secret',artifacts=Artifacts(root),opener=Opener(b'{"code":40435,"data":[]}'))
            with self.assertRaises(Unavailable):c.request('GET','market/rwa/tokens',{})
        self.assertIsNone(NoRedirect().redirect_request(None,None,None,None,None,None))
    def test_http_200_auth_rate_and_compliance_codes_stop_collection(self):
        for code, outcome in ((40102,'authentication_error'),(42900,'rate_limited'),(40304,'compliance_restriction')):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as root:
                c=Web3Client('fixture-api-key','fixture-secret',artifacts=Artifacts(root),
                             opener=Opener(json.dumps({'code':code}).encode()))
                with self.assertRaisesRegex(Unavailable,outcome):c.request('GET','market/rwa/tokens',{})
    def test_a_truncated_or_malformed_http_response_is_a_transport_error(self):
        # #64 (WR22) item 2: http.client.HTTPException is neither URLError nor OSError.
        import http.client
        from pathlib import Path
        class Truncated(Response):
            def read(self,n):raise http.client.IncompleteRead(b'{"code":0,"da',100)
        class TruncatedOpener(Opener):
            def open(self,request,timeout):return Truncated(b'')
        class BadStatus(Opener):
            def open(self,request,timeout):raise http.client.BadStatusLine('fixture-secret')
        for opener in (TruncatedOpener(b''),BadStatus(b'')):
            with self.subTest(opener=type(opener).__name__), tempfile.TemporaryDirectory() as root:
                c=Web3Client('fixture-api-key','fixture-secret',artifacts=Artifacts(root),opener=opener)
                with self.assertRaisesRegex(Unavailable,'transport_error'):c.request('GET','market/rwa/tokens',{})
                [artifact]=[json.loads(p.read_bytes()) for p in Path(root).glob('*.json')]
                self.assertEqual(artifact['outcome'],'transport_error')
                self.assertNotIn('fixture-secret',json.dumps(artifact))

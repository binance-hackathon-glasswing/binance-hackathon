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
    def test_business_error_and_redirect_do_not_succeed(self):
        with tempfile.TemporaryDirectory() as root:
            c=Web3Client('fixture-api-key','fixture-secret',artifacts=Artifacts(root),opener=Opener(b'{"code":40435,"data":[]}'))
            with self.assertRaises(Unavailable):c.request('GET','market/rwa/tokens',{})
        self.assertIsNone(NoRedirect().redirect_request(None,None,None,None,None,None))

import importlib.util
import unittest
from dataclasses import replace
from larp.execution import Blocked, Gates, Payload
from larp.signer.local import LocalSigner, verify
from tests.execution_fixtures import intent, ROUTER, TOKEN

class Registry:
    def __init__(self):self.rows={};self.authority=(1,1)
    def check_authority(self,e,v):
        if (e,v)!=self.authority:raise Blocked('fenced')
    def lookup(self,a,h):
        if a in self.rows and self.rows[a][0]!=h:raise Blocked('attempt reused')
        return self.rows.get(a,(None,None))[1]
    def put_if_absent(self,a,h,s,e,v):
        self.check_authority(e,v)
        prior=self.lookup(a,h)
        if prior:return prior
        self.rows[a]=(h,s);return s

@unittest.skipUnless(importlib.util.find_spec('eth_account'),'signer dependency not in runtime CI lock; requested from Keegan')
class SignerTests(unittest.TestCase):
    def setUp(self):
        from eth_account import Account
        self.account=Account.create();self.registry=Registry()
        self.intent=replace(intent(),wallet=self.account.address.lower())
        self.gates=Gates(1,1,0,1,999,True,True,True,True,True,True,True,True)
        data='0x095ea7b3'+'0'*24+ROUTER[2:]+format(self.intent.amount,'064x')
        self.payload=Payload(56,self.intent.wallet,self.intent.pay_token,0,0,50000,10,data)
        self.signer=LocalSigner(account=self.account,expected_address=self.intent.wallet,registry=self.registry,
          authorization=lambda *a:(self.intent,'APPROVE',self.gates,2,None),signer_host=True)
    def test_signed_bytes_match_every_field_and_recover_exactly(self):
        a=self.signer.sign('a',self.payload,1,1)
        self.assertTrue(verify(self.payload,a));self.assertEqual(a,self.signer.sign('a',self.payload,1,1))
        self.assertFalse(verify(replace(self.payload,nonce=1),a))
        self.assertFalse(verify(replace(self.payload,to=TOKEN),a))
    def test_fencing_and_wallet_binding(self):
        self.registry.authority=(2,2)
        with self.assertRaises(Blocked):self.signer.sign('a',self.payload,1,1)
        with self.assertRaises(Blocked):LocalSigner(account=self.account,expected_address=ROUTER,
          registry=self.registry,authorization=None,signer_host=True)

    def test_secret_loader_requires_one_source_and_isolated_host(self):
        args = dict(registry=self.registry, authorization=self.signer.authorization, signer_host=True)
        for values in ({}, {'WALLET_PRIVATE_KEY':'bad', 'WALLET_MNEMONIC':'bad'},
                       {'WALLET_PRIVATE_KEY':'invalid-credential'}):
            with self.subTest(values=tuple(values)), self.assertRaises(Blocked):
                LocalSigner.from_secret_store(dict(values, AI_SEEDS_ADDRESS=self.intent.wallet), **args)
        key = self.account.key.hex()
        secrets = dict(WALLET_PRIVATE_KEY=key, AI_SEEDS_ADDRESS=self.intent.wallet)
        with self.assertRaises(Blocked):
            LocalSigner.from_secret_store(secrets, registry=self.registry, authorization=None, signer_host=False)
        self.assertEqual(LocalSigner.from_secret_store(secrets, **args).account.address, self.account.address)

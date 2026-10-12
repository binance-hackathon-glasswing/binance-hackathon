import unittest
from dataclasses import replace
from larp.execution import Blocked, NATIVE_BNB, USDT
from larp.execution_live.chain import ChainEvidence, quantity
from larp.execution_live.service import map_command
from tests.execution_fixtures import intent, WALLET, ROUTER, TOKEN

HASH='0x'+'a'*64; BLOCK='0x'+'b'*64; HEAD='0x'+'c'*64
class RPC:
    def call(self,method,params):
        if method=='eth_chainId':return '0x38'
        if method=='eth_getTransactionCount':return '0x3'
        if method=='eth_getTransactionByHash':return dict(hash=HASH,blockHash=BLOCK,blockNumber='0xa',nonce='0x3',**{'from':WALLET})
        if method=='eth_getTransactionReceipt':return dict(transactionHash=HASH,blockHash=BLOCK,blockNumber='0xa',status='0x1',gasUsed='0x5208',**{'from':WALLET})
        if method=='eth_getBlockByNumber':
            return dict(hash=BLOCK,number='0xa',transactions=[HASH]) if params[0]=='0xa' else dict(hash=HEAD,number='0xc',transactions=[])
        raise AssertionError(method)

class LiveBoundaries(unittest.TestCase):
    def test_nonce_and_finality_bind_canonical_receipt(self):
        c=ChainEvidence(RPC());self.assertEqual(c.nonce(WALLET),3)
        o=c.outcome(HASH)
        self.assertTrue(o.finality_verified);self.assertEqual(o.gas_used,21000)
        self.assertEqual((o.sender,o.nonce,o.status),(WALLET,3,'SUCCESS'))
    def test_missing_finality_and_pending_nonce_block(self):
        class Pending(RPC):
            def call(self,m,p):return '0x4' if m=='eth_getTransactionCount' and p[-1]=='pending' else super().call(m,p)
        with self.assertRaises(Blocked):ChainEvidence(Pending()).nonce(WALLET)
        class NoFinal(RPC):
            def call(self,m,p):return None if p==['finalized',False] else super().call(m,p)
        with self.assertRaises(Blocked):ChainEvidence(NoFinal()).outcome(HASH)
    def test_reorg_is_not_final(self):
        class Reorg(RPC):
            def call(self,m,p):
                r=super().call(m,p)
                return dict(r,hash=HEAD) if m=='eth_getBlockByNumber' and p[0]=='0xa' else r
        self.assertIsNone(ChainEvidence(Reorg()).receipt(HASH))
    def command(self,side='BUY'):
        p=dict(intent_id='i',decision_id='d',expires_ms=1000000,symbol='NVDAB',side=side,amount_kind='EXACT_IN',
               pay_asset='USDT' if side=='BUY' else 'NVDAB',pay_units=40000000,min_receive_units=30000000,
               receive_decimals=18 if side=='BUY' else 6, cash_units=40000000, fee_units=0)
        return dict(kind='EXECUTION_REQUEST',command_id='i',decision_id='d',expires_ms=1000000,round_id='r',payload=p)
    def mapped(self,c):
        return map_command(c,run_id='run',wallet=WALLET,version_id='v',router=ROUTER,
                           token_decimals={'NVDAB':18},limits=dict(max_gas=1000000,max_gas_price=10,gas_budget=20000000,
                                                               per_trade_cap_units=50000000),now_ms=100)
    def test_command_units_identity_and_expiry(self):
        buy=self.mapped(self.command());self.assertEqual(buy.amount,40*10**18)
        sell=self.mapped(self.command('SELL'));self.assertEqual(sell.minimum_output,30*10**18)
        c=self.command();c['payload']['decision_id']='other'
        with self.assertRaises(Blocked):self.mapped(c)
    def test_gas_topup_is_explicit_and_narrow(self):
        with self.assertRaises(Blocked):replace(intent(),receive_token=NATIVE_BNB).validate()
        replace(intent(),receive_token=NATIVE_BNB,kind='GAS_TOP_UP').validate()
        with self.assertRaises(Blocked):replace(intent(),pay_token=TOKEN,receive_token=NATIVE_BNB,kind='GAS_TOP_UP').validate()
    def test_unknown_router_blocks_before_signing(self):
        from larp.execution_live.venue import UnverifiedRouter
        with self.assertRaises(Blocked):UnverifiedRouter().decode(None)

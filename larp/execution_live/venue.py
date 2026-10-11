"""Read/build venue adapter. Broadcast capability remains separately gated by runtime readiness."""
from larp.execution import Blocked, Payload
from larp.marketdata.web3 import single
from larp.marketdata.port import integer


class LiveVenue:
    mode='live'
    def __init__(self,client,chain,*,decoder,release=None):
        self.client,self.chain,self.decoder,self.release=client,chain,decoder,release
    def quote(self,intent,nonce):
        r=self.client.request('GET','aggregator/quote-and-swap',dict(binanceChainId='56',amount=str(intent.amount),
             fromTokenAddress=intent.pay_token,toTokenAddress=intent.receive_token,userWalletAddress=intent.wallet,
             vendor='LiquidMesh',slippagePercent='0.5'))
        d=single(r);tx=d['tx']
        if d.get('executionMode')!='SWAP' or d.get('rfq') is not None:raise Blocked('unknown execution mode')
        payload=Payload(56,intent.wallet,str(tx['to']).lower(),integer(tx['value']),nonce,
                        integer(tx['gas']),integer(tx['gasPrice']),tx['data'])
        self.decoder.decode(payload)  # A byte-bound decoder must exist; unknown ABI blocks before approval.
        return payload
    def approve(self,intent,nonce):
        r=self.client.request('GET','aggregator/approve-transaction',dict(binanceChainId='56',
            tokenContractAddress=intent.pay_token,approveAmount=str(intent.amount),vendor='LiquidMesh'))
        d=single(r)
        if str(d['dexContractAddress']).lower()!=intent.router:raise Blocked('approve spender mismatch')
        return Payload(56,intent.wallet,intent.pay_token,0,nonce,integer(d['gasLimit']),integer(d['gasPrice']),d['data'])
    def estimate_gas(self,payload):
        r=self.client.request('POST','pre-transaction/gas-limit',dict(binanceChainId='56',evmTx=dict(
            **{'from':payload.sender},to=payload.to,data=payload.data,value=str(payload.value))))
        estimate=integer(single(r)['gasLimit'])
        if estimate<=0:raise Blocked('missing positive exact-payload gas estimate')
        return estimate
    def broadcast(self,signed,epoch,guard_version):
        # The read/build client deliberately has no submission endpoint. Runtime must install a fenced
        # release boundary with durable write-ahead/round mapping after all capability gates pass.
        if self.release is None:raise Blocked('runtime broadcast release boundary unavailable')
        return self.release(signed,epoch,guard_version)
    def outcome(self,tx_hash):return self.chain.outcome(tx_hash)


class UnverifiedRouter:
    mode='blocked'
    def decode(self,payload):
        raise Blocked('verified router ABI/nested route/encoded expiry proof required')

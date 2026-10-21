"""Read/build venue adapter. Broadcast capability remains separately gated by runtime readiness."""
from functools import wraps
from larp.execution import Blocked, DependencyUnavailable, Payload, REVOKE_TOKENS
from larp.marketdata.web3 import single, Unavailable
from larp.marketdata.port import integer, slippage_percent


def boundary(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Unavailable as error:
            if str(error) in ('authentication_error', 'compliance_restriction', 'http_forbidden_unclassified'):
                raise Blocked('venue access refused') from None
            raise DependencyUnavailable('venue dependency unavailable') from None
        except (KeyError, TypeError, ValueError, AttributeError):
            raise Blocked('venue response schema rejected') from None
    return wrapped


class LiveVenue:
    mode='live'
    periodic_reconciliation = True
    def __init__(self,client,chain,*,decoder,release=None):
        self.client,self.chain,self.decoder,self.release=client,chain,decoder,release
        self.vendors = {}
    @boundary
    def quote(self,intent,nonce):
        r=self.client.request('GET','aggregator/quote-and-swap',dict(binanceChainId='56',amount=str(intent.amount),
             fromTokenAddress=intent.pay_token,toTokenAddress=intent.receive_token,userWalletAddress=intent.wallet,
             vendor='LiquidMesh',slippagePercent=slippage_percent(intent.max_slippage_bps)))
        d=single(r);tx=d['tx']
        if d.get('executionMode')!='SWAP' or d.get('rfq') is not None:raise Blocked('unknown execution mode')
        vendor = d.get('routerResult', {}).get('vendorName')
        if vendor != 'LiquidMesh':raise Blocked('unexpected quote vendor')
        received = integer(d['routerResult']['toTokenAmount'])
        minimum = integer(tx['minReceiveAmount'])
        if not 0 < minimum <= received or minimum < received * (10000 - intent.max_slippage_bps) // 10000:
            raise Blocked('fresh quote minimum output exceeds intent slippage limit')
        cash = intent.amount if intent.pay_token == '0x55d398326f99059ff775485246999027b3197955' else integer(d['routerResult']['toTokenAmount'])
        if intent.max_cash_units is not None and cash > intent.max_cash_units * 10**12:
            raise Blocked('fresh quote exceeds execution cash cap')
        payload=Payload(56,intent.wallet,str(tx['to']).lower(),integer(tx['value']),nonce,
                        integer(tx['gas']),integer(tx['gasPrice']),tx['data'])
        self.decoder.decode(payload)  # A byte-bound decoder must exist; unknown ABI blocks before approval.
        self.vendors[intent.key] = vendor
        return payload
    @boundary
    def approve(self,intent,nonce):
        if intent.key not in self.vendors:raise Blocked('fresh validated quote required before approval')
        r=self.client.request('GET','aggregator/approve-transaction',dict(binanceChainId='56',
            tokenContractAddress=intent.pay_token,approveAmount=str(intent.amount),vendor=self.vendors[intent.key]))
        d=single(r)
        if str(d['dexContractAddress']).lower()!=intent.router:raise Blocked('approve spender mismatch')
        return Payload(56,intent.wallet,intent.pay_token,0,nonce,integer(d['gasLimit']),integer(d['gasPrice']),d['data'])
    @boundary
    def revoke(self, intent, token, nonce):
        """Zero-only supporting approval via the same Web3 API; validated independently before signing."""
        if token not in REVOKE_TOKENS.values() or intent.key not in self.vendors:
            raise Blocked('eligible token and fresh quote required before cleanup')
        r = self.client.request('GET', 'aggregator/approve-transaction', dict(binanceChainId='56',
            tokenContractAddress=token, approveAmount='0', vendor=self.vendors[intent.key]))
        d = single(r)
        if str(d['dexContractAddress']).lower() != intent.router:
            raise Blocked('cleanup spender mismatch')
        return Payload(56, intent.wallet, token, 0, nonce, integer(d['gasLimit']), integer(d['gasPrice']), d['data'])
    @boundary
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
    @boundary
    def outcome(self,tx_hash):return self.chain.outcome(tx_hash)


class UnverifiedRouter:
    mode='blocked'
    def decode(self,payload):
        raise Blocked('verified router ABI/nested route/encoded expiry proof required')

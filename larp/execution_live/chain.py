"""Read-only chain-56 RPC evidence; finalized-tag support is mandatory, never guessed."""
import http.client
import json
import re
from functools import wraps
from itertools import count
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from urllib.error import URLError

from larp.execution import Blocked, DependencyUnavailable, Outcome
from larp.marketdata.web3 import NoRedirect, encoded, utc

METHODS = frozenset(('eth_chainId', 'eth_getTransactionCount', 'eth_getTransactionByHash',
                     'eth_getTransactionReceipt', 'eth_getBlockByNumber', 'eth_getBalance', 'eth_getCode'))


def quantity(v):
    if not isinstance(v,str) or not re.fullmatch(r'0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)',v):
        raise Blocked('invalid RPC quantity')
    result = int(v,16)
    if result >= 2**256:
        raise Blocked('RPC quantity exceeds uint256')
    return result


def hash_value(v):
    if not isinstance(v,str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}',v):
        raise Blocked('invalid RPC hash')
    return v.lower()


def evidence_boundary(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
            raise Blocked('RPC evidence schema rejected') from None
    return wrapped


class Rpc:
    mode='live'
    def __init__(self,url,*,artifacts,source_id,opener=None):
        parsed=urlsplit(url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or not source_id:
            raise Blocked('manifested HTTPS RPC endpoint required')
        self.url,self.artifacts,self.source_id=url,artifacts,source_id
        self.opener=opener or build_opener(NoRedirect())
        self.sequence=count(1)

    def call(self,method,params):
        if method not in METHODS:
            raise Blocked('RPC method outside read-only allowlist')
        request_id=next(self.sequence)
        body=encoded(dict(jsonrpc='2.0',id=request_id,method=method,params=params))
        req=Request(self.url,data=body,headers={'Content-Type':'application/json'},method='POST')
        try:
            with self.opener.open(req,timeout=20) as response:
                raw=response.read(2*1024*1024+1)
            if len(raw)>2*1024*1024:raise Blocked('RPC response too large')
            result=json.loads(raw)
        except (URLError,OSError,ValueError,http.client.HTTPException):
            raise DependencyUnavailable('RPC unavailable') from None
        if (not isinstance(result,dict) or result.get('jsonrpc')!='2.0'
                or type(result.get('id')) is not int or result['id']!=request_id
                or 'error' in result or 'result' not in result):
            raise Blocked('RPC response rejected')
        self.artifacts.put(dict(schema='ChainObservation.v1',source_id=self.source_id,method=method,params=params,
                                result=result['result'],available_at=utc()))
        return result['result']


class ChainEvidence:
    mode='live'
    def __init__(self,rpc):self.rpc=rpc
    def check_chain(self):
        if quantity(self.rpc.call('eth_chainId',[]))!=56:raise Blocked('wrong RPC chain')
    @evidence_boundary
    def nonce(self,wallet):
        self.check_chain()
        latest=quantity(self.rpc.call('eth_getTransactionCount',[wallet,'latest']))
        pending=quantity(self.rpc.call('eth_getTransactionCount',[wallet,'pending']))
        if pending!=latest:raise Blocked('pending wallet nonce requires journal reconciliation')
        return latest
    @evidence_boundary
    def receipt(self,tx_hash):
        self.check_chain();tx_hash=hash_value(tx_hash)
        tx=self.rpc.call('eth_getTransactionByHash',[tx_hash])
        receipt=self.rpc.call('eth_getTransactionReceipt',[tx_hash])
        if tx is None or receipt is None:return None
        if hash_value(tx['hash'])!=tx_hash or hash_value(receipt['transactionHash'])!=tx_hash:
            raise Blocked('receipt transaction mismatch')
        height=quantity(receipt['blockNumber']);block_hash=hash_value(receipt['blockHash'])
        if quantity(tx['blockNumber'])!=height or hash_value(tx['blockHash'])!=block_hash:
            raise Blocked('receipt inclusion mismatch')
        block=self.rpc.call('eth_getBlockByNumber',[hex(height),False])
        finalized=self.rpc.call('eth_getBlockByNumber',['finalized',False])
        if not block or not finalized:raise Blocked('canonical/finalized evidence missing')
        if quantity(block['number'])!=height or hash_value(block['hash'])!=block_hash:
            return None  # Provisional reorg; never a final outcome.
        if tx_hash not in [hash_value(h) for h in block['transactions']]:
            raise Blocked('transaction missing from canonical block')
        final_height=quantity(finalized['number'])
        final_block=self.rpc.call('eth_getBlockByNumber',[hex(final_height),False])
        if (not final_block or quantity(final_block['number'])!=final_height
                or hash_value(final_block['hash'])!=hash_value(finalized['hash'])):
            raise Blocked('finalized head is not canonical')
        # Recheck receipt block after finalized-head reads to detect a concurrent reorg.
        again=self.rpc.call('eth_getBlockByNumber',[hex(height),False])
        if not again or quantity(again['number'])!=height or hash_value(again['hash'])!=block_hash:return None
        status=quantity(receipt['status'])
        if status not in (0,1):raise Blocked('unknown receipt status')
        if str(receipt['from']).lower()!=str(tx['from']).lower():raise Blocked('receipt sender mismatch')
        return dict(tx=tx,receipt=receipt,block_hash=block_hash,block_number=height,
                    finalized_height=final_height,finality_verified=height<=final_height)
    @evidence_boundary
    def outcome(self,tx_hash):
        tx_hash=hash_value(tx_hash)
        proof=self.receipt(tx_hash)
        if proof is None:
            tx = self.rpc.call('eth_getTransactionByHash', [tx_hash])
            if tx is None:
                return Outcome(tx_hash,None,None,'UNKNOWN')
            if hash_value(tx['hash']) != tx_hash:
                raise Blocked('pending transaction identity mismatch')
            return Outcome(tx_hash,tx['from'].lower(),quantity(tx['nonce']),
                           'PENDING' if tx.get('blockNumber') is None else 'UNKNOWN')
        tx,r=proof['tx'],proof['receipt']
        return Outcome(tx_hash,tx['from'].lower(),quantity(tx['nonce']),
                       'SUCCESS' if quantity(r['status'])==1 else 'REVERT',proof['block_hash'],proof['block_hash'],
                       proof['block_number'],proof['finalized_height'],proof['finality_verified'],quantity(r['gasUsed']))

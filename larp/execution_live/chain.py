"""Read-only chain-56 RPC evidence; finalized-tag support is mandatory, never guessed."""
import hashlib
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


def native_trace_options():
    return dict(tracer='prestateTracer', tracerConfig=dict(diffMode=True, disableCode=True, disableStorage=True))


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
    def __init__(self,url,*,artifacts,source_id,opener=None,native_trace=False):
        parsed=urlsplit(url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or not source_id:
            raise Blocked('manifested HTTPS RPC endpoint required')
        self.url,self.artifacts,self.source_id=url,artifacts,source_id
        if type(native_trace) is not bool:
            raise Blocked('explicit native tracing capability required')
        self.native_trace = native_trace
        self.opener=opener or build_opener(NoRedirect())
        self.sequence=count(1)

    def call(self,method,params):
        trace = (self.native_trace and method == 'debug_traceTransaction'
                 and type(params) is list and len(params) == 2 and params[1] == native_trace_options())
        if method not in METHODS and not trace:
            raise Blocked('RPC method outside read-only allowlist')
        request_id=next(self.sequence)
        body=encoded(dict(jsonrpc='2.0',id=request_id,method=method,params=params))
        req=Request(self.url,data=body,headers={'Content-Type':'application/json'},method='POST')
        try:
            with self.opener.open(req,timeout=20) as response:
                raw=response.read(2*1024*1024+1)
            if len(raw)>2*1024*1024:raise Blocked('RPC response too large')
            result=json.loads(raw)
        except (URLError,OSError,ValueError):
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
    def native_receipt(self, tx_hash):
        """Trusted-provider transaction-local native state, never a block balance delta.

        Requires explicit provider qualification; Geth traces are not cryptographic
        proofs. Receipt inclusion/finality is checked again after the trace.
        """
        if getattr(self.rpc, 'native_trace', False) is not True:
            raise Blocked('qualified transaction-native tracing required')
        tx_hash = hash_value(tx_hash)
        before = self.receipt(tx_hash)
        if before is None or before.get('finality_verified') is not True:
            raise Blocked('final native receipt required')
        if quantity(before['receipt']['status']) == 0:
            return before  # A revert spends gas; it receives no native output.
        wallet = str(before['tx']['from']).lower()
        if not re.fullmatch(r'0x[0-9a-f]{40}', wallet):
            raise Blocked('native trace wallet rejected')
        nonce = quantity(before['tx']['nonce'])
        trace = self.rpc.call('debug_traceTransaction', [tx_hash, native_trace_options()])
        if type(trace) is not dict or set(trace) != {'pre', 'post'}:
            raise Blocked('transaction-native trace required')
        accounts = []
        for phase in ('pre', 'post'):
            rows = trace[phase]
            if type(rows) is not dict or any(type(a) is not str or not re.fullmatch(r'0x[0-9a-fA-F]{40}', a) for a in rows):
                raise Blocked('native trace accounts rejected')
            matches = [v for k, v in rows.items() if k.lower() == wallet]
            if len(matches) != 1 or type(matches[0]) is not dict:
                raise Blocked('native trace wallet missing or ambiguous')
            accounts.append(matches[0])
        pre, post = accounts
        # Geth omits a zero pre-nonce and unchanged post-balance; sender nonce
        # nevertheless increments in this transaction. Missing wallet is not zero.
        pre_nonce, post_nonce = pre.get('nonce', 0), post.get('nonce')
        if (type(pre_nonce) is not int or type(post_nonce) is not int
                or not 0 <= pre_nonce < 2**64 or pre_nonce != nonce or post_nonce != nonce + 1):
            raise Blocked('native trace nonce differs from transaction')
        initial = quantity(pre['balance'])
        final = quantity(post.get('balance', pre['balance']))
        after = self.receipt(tx_hash)
        if (after is None or after.get('finality_verified') is not True
                or before['block_hash'] != after['block_hash'] or before['block_number'] != after['block_number']
                or before['tx'] != after['tx'] or before['receipt'] != after['receipt']):
            raise Blocked('native trace canonical receipt changed')
        source = getattr(self.rpc, 'source_id', None)
        if type(source) is not str or not source:
            raise Blocked('native trace source required')
        after['native_balance'] = dict(schema='TransactionNativeBalance.v1', method='GETH_PRESTATE_DIFF',
            source_id=source, tx_hash=tx_hash, block_hash=after['block_hash'], wallet=wallet, nonce=nonce,
            before_wei=initial, after_wei=final, trace_sha256=hashlib.sha256(encoded(trace)).hexdigest())
        return after
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

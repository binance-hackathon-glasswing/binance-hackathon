"""SJ-05 Part B: read-only public RPC reads of the dev wallet's approvals (IDEA-049-C SJ-05)."""
import json, sys, time, urllib.request
RPCS = ['https://bsc-dataseed.bnbchain.org', 'https://bsc-dataseed1.bnbchain.org']
WALLET = '0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479'
ROUTER = '0xb44446b0c8e56988c34f7ff73ae904982b5fdda5'
TOKENS = dict(USDT='0x55d398326f99059ff775485246999027b3197955', GOOGLB='0x3f53de71c126bdabae20f9cd64848d317f6c3238',
              MSFTB='0x80106cb3ead06659a5ad19df39d9b4733863b9b0', NVDAB='0x02fca66c1d1afb4e2a7884261eb00f63598a7436',
              SKHYB='0xca750ef65f295bbecd685abf54e82caf297bdb61', TSLAB='0x5b1910eaad6450e50f816082aa078c41f10c292f')
SEEDS = ['0x24683de219c18cc78a2d7aeb37c94e733a6a383b1c3a58d3a403f95df7da5c55',
         '0xab19e680522a72632fd3e0ad296c69b9901643de66d3fa218795bf35c57a168d']
APPROVAL = '0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
OWNER = '0x' + '0' * 24 + WALLET[2:]
log = []

def rpc(method, params):
    last = None
    for url in RPCS:
        body = json.dumps(dict(jsonrpc='2.0', id=1, method=method, params=params)).encode()
        req = urllib.request.Request(url, body, {'Content-Type': 'application/json', 'User-Agent': 'larp-sj05'})
        try:
            out = json.load(urllib.request.urlopen(req, timeout=20))
        except Exception as e:
            last = type(e).__name__; continue
        if 'error' in out:
            last = str(out['error'])[:120]; continue
        log.append(dict(method=method, rpc=url, ok=True))
        return out['result']
    log.append(dict(method=method, ok=False, error=last))
    return None

result = dict(schema='SJ05Allowances.v1', wallet=WALLET, seeds=[], approvals=[], allowances=[])
nonces = {}
for h in SEEDS:
    tx, rc = rpc('eth_getTransactionByHash', [h]), rpc('eth_getTransactionReceipt', [h])
    block = int(rc['blockNumber'], 16)
    nonces[int(tx['nonce'], 16)] = h
    result['seeds'].append(dict(hash=h, nonce=int(tx['nonce'], 16), block=block, to=tx['to'], status=rc['status'],
                                approvals_in_receipt=[(l['address'], '0x' + l['topics'][2][26:], int(l['data'], 16))
                                                      for l in rc['logs'] if l['topics'][:1] == [APPROVAL]
                                                      and l['topics'][1].lower() == OWNER]))
    # Approval(owner=wallet) on any contract in the window before each swap (the approve precedes it).
    for start in range(block - 1200, block + 1, 200):
        logs = rpc('eth_getLogs', [dict(fromBlock=hex(start), toBlock=hex(min(start + 199, block)), topics=[APPROVAL, OWNER])])
        if logs is None:
            result.setdefault('refused_windows', []).append([start, min(start + 199, block)]); continue
        for l in logs:
            entry = dict(token=l['address'].lower(), spender='0x' + l['topics'][2][26:], value=int(l['data'], 16),
                         block=int(l['blockNumber'], 16), tx=l['transactionHash'])
            if entry not in result['approvals']:
                result['approvals'].append(entry)
for a in result['approvals']:
    tx = rpc('eth_getTransactionByHash', [a['tx']])
    if tx and tx['from'].lower() == WALLET:
        nonces[int(tx['nonce'], 16)] = a['tx']
        a['nonce'] = int(tx['nonce'], 16)
result['nonces_accounted'] = sorted(nonces)
fin = rpc('eth_getBlockByNumber', ['finalized', False])
result['finalized'] = dict(number=int(fin['number'], 16), hash=fin['hash'], utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(fin['timestamp'], 16))))
result['finalized_nonce'] = int(rpc('eth_getTransactionCount', [WALLET, fin['number']]), 16)
pairs = {(t, ROUTER) for t in TOKENS.values()} | {(a['token'], a['spender'].lower()) for a in result['approvals']}
for token, spender in sorted(pairs):
    data = '0xdd62ed3e' + '0' * 24 + WALLET[2:] + '0' * 24 + spender[2:]
    v = rpc('eth_call', [dict(to=token, data=data), fin['number']])
    result['allowances'].append(dict(token=token, spender=spender, value=None if v is None else int(v, 16)))
result['reads'] = dict(ok=sum(1 for r in log if r['ok']), refused=sum(1 for r in log if not r['ok']))
json.dump(result, sys.stdout, indent=1)

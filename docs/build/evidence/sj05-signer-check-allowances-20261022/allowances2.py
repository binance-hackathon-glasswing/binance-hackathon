"""SJ-05 Part B follow-up: find nonces 0 and 2 by block scan; read MetaMask-router/Permit2 allowances."""
import json, sys, urllib.request
URL = 'https://bsc-dataseed.bnbchain.org'
WALLET = '0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479'
MM = '0x1a1ec25dc08e98e5e93f1104b5e5cdd298707d31'
PERMIT2 = '0x000000000022d473030f116ddee9f6b43ac78ba3'
TOKENS = dict(USDT='0x55d398326f99059ff775485246999027b3197955', GOOGLB='0x3f53de71c126bdabae20f9cd64848d317f6c3238',
              MSFTB='0x80106cb3ead06659a5ad19df39d9b4733863b9b0', NVDAB='0x02fca66c1d1afb4e2a7884261eb00f63598a7436',
              SKHYB='0xca750ef65f295bbecd685abf54e82caf297bdb61', TSLAB='0x5b1910eaad6450e50f816082aa078c41f10c292f')
FIN = int(sys.argv[1])
stats = dict(ok=0, refused=0)

def batch(calls):
    body = json.dumps([dict(jsonrpc='2.0', id=i, method=m, params=p) for i, (m, p) in enumerate(calls)]).encode()
    req = urllib.request.Request(URL, body, {'Content-Type': 'application/json', 'User-Agent': 'larp-sj05'})
    out = {r['id']: r for r in json.load(urllib.request.urlopen(req, timeout=30))}
    res = []
    for i in range(len(calls)):
        r = out.get(i, {})
        stats['ok' if 'result' in r else 'refused'] += 1
        res.append(r.get('result'))
    return res

found = {}
for swap_block in (127946341, 128977934):
    for top in range(swap_block, swap_block - 400, -10):
        blocks = batch([('eth_getBlockByNumber', [hex(b), True]) for b in range(top, top - 10, -1)])
        for b in blocks:
            for tx in (b or {}).get('transactions', []):
                if tx['from'].lower() == WALLET:
                    found[int(tx['nonce'], 16)] = dict(hash=tx['hash'], block=int(b['number'], 16), to=tx['to'],
                                                       selector=tx['input'][:10], input_len=len(tx['input']))
        if len([n for n in found if n in (0, 2)]) == (1 if swap_block < 128e6 else 2):
            break
for n, t in found.items():
    if t['selector'] == '0x095ea7b3':
        raw = [batch([('eth_getTransactionByHash', [t['hash']])])[0]['input']][0]
        t['approve_spender'] = '0x' + raw[34:74]
        t['approve_value'] = int(raw[74:138], 16)
        t['receipt_status'] = batch([('eth_getTransactionReceipt', [t['hash']])])[0]['status']
pairs = [(name, tok, sp) for name, tok in TOKENS.items() for sp in (MM, PERMIT2)]
vals = batch([('eth_call', [dict(to=tok, data='0xdd62ed3e' + '0' * 24 + WALLET[2:] + '0' * 24 + sp[2:]), hex(FIN)])
              for _, tok, sp in pairs])
json.dump(dict(finalized_block=FIN, wallet_txs=dict(sorted(found.items())),
               allowances=[dict(token=n, spender=sp, value=None if v is None else int(v, 16))
                           for (n, _, sp), v in zip(pairs, vals)], reads=stats), sys.stdout, indent=1)

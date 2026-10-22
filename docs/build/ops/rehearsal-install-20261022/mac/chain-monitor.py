"""Live, read-only trade monitor for the dev rehearsal wallet (IDEA-049-C SJ-08). Runs on the Mac; no host access.

  <venv python from requirements.lock> docs/build/ops/rehearsal-install-20261022/mac/chain-monitor.py [--once] [--interval 60]

Anyone with a checkout can run it. Output goes to $LARP_MONITOR_DIR (default <repo>/deploy/activation/rehearsal-monitor,
which is git-ignored). Prices need a Web3 key pair in $LARP_ENV_FILE (default <repo>/.env); without one the fill book,
holdings, gas and alerts still work and price_error is set.

Every poll: finalized block, nonce, on-chain holdings, router allowances and Web3 token prices. When the nonce
moves, it finds the wallet's new transactions in the blocks since the last poll and decodes each receipt's
Approval/Transfer logs into fills. It keeps average cost per token, realized and unrealized PnL in USDT, and gas
spent in BNB, and it flags anything that looks like an error. Appends to monitor/{snapshots,transactions,alerts}.jsonl
next to this folder and prints one summary line per poll. Public chain data plus the team's read-only Web3 key
(prices only). Nothing is signed or sent.
"""
import argparse, json, os, sys, time, urllib.request
from fractions import Fraction
from pathlib import Path

# The checkout this file sits in (docs/build/ops/... or a copy under deploy/activation/...).
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'larp').is_dir() and (p / '.git').exists())
OUT = Path(os.environ.get('LARP_MONITOR_DIR') or ROOT / 'deploy/activation/rehearsal-monitor')
ENV_FILE = os.environ.get('LARP_ENV_FILE') or str(ROOT / '.env')
RPC = 'https://bsc-dataseed.bnbchain.org'
WALLET = '0x62b8ed6c1b3bcae61d9bfa5551dfd77b6e7bd479'
ROUTER = '0xb44446b0c8e56988c34f7ff73ae904982b5fdda5'
USDT = '0x55d398326f99059ff775485246999027b3197955'
STOCKS = dict(NVDAB='0x02fca66c1d1afb4e2a7884261eb00f63598a7436', GOOGLB='0x3f53de71c126bdabae20f9cd64848d317f6c3238',
              SKHYB='0xca750ef65f295bbecd685abf54e82caf297bdb61', TSLAB='0x5b1910eaad6450e50f816082aa078c41f10c292f',
              MSFTB='0x80106cb3ead06659a5ad19df39d9b4733863b9b0')
SYMBOL = {USDT: 'USDT', **{v: k for k, v in STOCKS.items()}}
# Run start (M4 capture 2026-10-22 11:11Z; initial-state ff572495...): 96 USDT, this BNB, no stocks, nonce 4.
START = dict(usdt=96 * 10**18, bnb=5325625054330011, nonce=4)
EXIT_RESERVE_WEI = 3072000000000000
TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
APPROVAL = '0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
E18 = 10**18


def rpc(method, params, batch=None):
    body = [dict(jsonrpc='2.0', id=i, method=m, params=p) for i, (m, p) in enumerate(batch)] if batch else \
        dict(jsonrpc='2.0', id=1, method=method, params=params)
    req = urllib.request.Request(RPC, json.dumps(body).encode(), {'Content-Type': 'application/json', 'User-Agent': 'larp-sj08'})
    out = json.load(urllib.request.urlopen(req, timeout=30))
    if batch:
        rows = {r['id']: r for r in out}
        return [rows.get(i, {}).get('result') for i in range(len(batch))]
    if 'error' in out:
        raise RuntimeError(str(out['error'])[:120])
    return out['result']


def word(address):
    return '0' * 24 + address[2:].lower()


def balances(block):
    calls = [('eth_getBalance', [WALLET, block])] + [
        ('eth_call', [dict(to=t, data='0x70a08231' + word(WALLET)), block]) for t in [USDT, *STOCKS.values()]] + [
        ('eth_call', [dict(to=t, data='0xdd62ed3e' + word(WALLET) + word(ROUTER)), block]) for t in [USDT, *STOCKS.values()]]
    r = rpc(None, None, batch=calls)
    if any(v is None for v in r):
        raise RuntimeError('balance read refused')
    n = 1 + 1 + len(STOCKS)
    held = dict(BNB=int(r[0], 16), USDT=int(r[1], 16), **{s: int(v, 16) for s, v in zip(STOCKS, r[2:n])})
    allowance = {SYMBOL[t]: int(v, 16) for t, v in zip([USDT, *STOCKS.values()], r[n:])}
    return held, allowance


def prices():
    """Web3 Open API rwa/price, USD per token (read-only key). None when unavailable."""
    try:
        sys.path.insert(0, str(ROOT))
        from larp.marketdata.web3 import Web3Client, Artifacts, credentials
        k = credentials(ENV_FILE)
        c = Web3Client(k['BINANCE_API_KEY'], k['BINANCE_SECRET_KEY'], artifacts=Artifacts(str(OUT / 'web3')))
        out = {}
        for s, t in STOCKS.items():
            r = c.request('GET', 'market/rwa/price', {'binanceChainId': '56', 'tokenContractAddresses': t})
            data = r['response'].get('data')
            row = data[0] if isinstance(data, list) and data else {}
            out[s] = Fraction(str(row['tokenPrice'])) if row.get('tokenPrice') else None
        return out
    except Exception as e:  # prices are optional for the ledger of fills
        return {s: None for s in STOCKS} | {'_error': type(e).__name__}


def wallet_txs(start, end):
    """Transactions sent by the wallet in blocks [start, end] (full-block scan, 20 per batch)."""
    found = []
    for lo in range(start, end + 1, 20):
        nums = list(range(lo, min(lo + 20, end + 1)))
        for b in rpc(None, None, batch=[('eth_getBlockByNumber', [hex(n), True]) for n in nums]):
            for tx in (b or {}).get('transactions', []):
                if tx['from'].lower() == WALLET:
                    found.append(tx)
    return found


def decode(tx):
    rc = rpc('eth_getTransactionReceipt', [tx['hash']])
    gas = int(rc['gasUsed'], 16) * int(rc['effectiveGasPrice'], 16)
    moves, approvals = {}, []
    for log in rc['logs']:
        t, topics = log['address'].lower(), log['topics']
        if topics[:1] == [TRANSFER] and len(topics) == 3:
            src, dst, amount = '0x' + topics[1][26:], '0x' + topics[2][26:], int(log['data'], 16)
            sym = SYMBOL.get(t, t)
            if src == WALLET:
                moves[sym] = moves.get(sym, 0) - amount
            if dst == WALLET:
                moves[sym] = moves.get(sym, 0) + amount
        if topics[:1] == [APPROVAL] and len(topics) == 3 and '0x' + topics[1][26:] == WALLET:
            approvals.append(dict(token=SYMBOL.get(t, t), spender='0x' + topics[2][26:], value=int(log['data'], 16)))
    kind = 'APPROVE' if tx['input'][:10] == '0x095ea7b3' else 'SWAP' if tx['to'] and tx['to'].lower() == ROUTER else 'OTHER'
    return dict(hash=tx['hash'], nonce=int(tx['nonce'], 16), block=int(rc['blockNumber'], 16), to=tx['to'],
                kind=kind, status=int(rc['status'], 16), gas_bnb_wei=gas, token_moves=moves, approvals=approvals)


def append(name, row):
    with (OUT / name).open('a') as f:
        f.write(json.dumps(row, sort_keys=True, default=str) + '\n')


def load_state():
    p = OUT / 'state.json'
    if p.exists():
        s = json.loads(p.read_text())
        s['cost'] = {k: Fraction(v) for k, v in s['cost'].items()}
        s['realized'] = Fraction(s['realized'])
        return s
    return dict(nonce=START['nonce'], block=None, cost={s: Fraction(0) for s in STOCKS}, units={s: 0 for s in STOCKS},
                realized=Fraction(0), gas=0, trades=0, failed=0)


def save_state(s):
    out = dict(s, cost={k: str(v) for k, v in s['cost'].items()}, realized=str(s['realized']))
    (OUT / 'state.json').write_text(json.dumps(out, sort_keys=True))


def apply_fill(s, d, alerts):
    """Average-cost book of USDT<->stock fills from the receipt's own Transfer logs."""
    m = d['token_moves']
    stocks = {k: v for k, v in m.items() if k in STOCKS and v}
    unknown = [k for k, v in m.items() if v and k not in STOCKS and k != 'USDT']
    if unknown:
        alerts.append(dict(kind='UNEXPECTED_TOKEN', tx=d['hash'], tokens=unknown))
    usdt = m.get('USDT', 0)
    if d['kind'] == 'SWAP' and d['status'] == 1 and len(stocks) != 1:
        alerts.append(dict(kind='SWAP_WITHOUT_ONE_STOCK_LEG', tx=d['hash'], moves=m))
    for sym, units in stocks.items():
        if units > 0:  # BUY: paid USDT
            if usdt >= 0:
                alerts.append(dict(kind='BUY_WITHOUT_USDT_DEBIT', tx=d['hash'], moves=m))
            s['cost'][sym] += Fraction(-usdt, E18)
            s['units'][sym] += units
            d['fill'] = dict(side='BUY', symbol=sym, units=units, usdt=-usdt,
                             price=float(Fraction(-usdt, units)) if units else None)
        else:  # SELL: received USDT
            sold = -units
            if usdt <= 0:
                alerts.append(dict(kind='SELL_WITHOUT_USDT_CREDIT', tx=d['hash'], moves=m))
            held = s['units'][sym]
            basis = s['cost'][sym] * Fraction(sold, held) if held else Fraction(0)
            s['realized'] += Fraction(usdt, E18) - basis
            s['cost'][sym] -= basis
            s['units'][sym] = held - sold
            d['fill'] = dict(side='SELL', symbol=sym, units=sold, usdt=usdt,
                             price=float(Fraction(usdt, sold)) if sold else None,
                             realized_usdt=float(Fraction(usdt, E18) - basis))


def poll(s):
    alerts, hold_scan = [], False
    fin = rpc('eth_getBlockByNumber', ['finalized', False])
    block, tag = int(fin['number'], 16), fin['number']
    nonce = int(rpc('eth_getTransactionCount', [WALLET, tag]), 16)
    if nonce > s['nonce']:
        start = s['block'] + 1 if s['block'] else block - 1200
        txs = sorted(wallet_txs(start, block), key=lambda t: int(t['nonce'], 16))
        seen = {int(t['nonce'], 16) for t in txs}
        missing = [n for n in range(s['nonce'], nonce) if n not in seen]
        if missing:
            alerts.append(dict(kind='NONCES_NOT_FOUND_IN_SCAN', nonces=missing, scanned=[start, block]))
        for tx in txs:
            if int(tx['nonce'], 16) < s['nonce']:
                continue
            d = decode(tx)
            s['gas'] += d['gas_bnb_wei']
            if d['status'] != 1:
                s['failed'] += 1
                alerts.append(dict(kind='TX_FAILED', tx=d['hash'], nonce=d['nonce'], tx_kind=d['kind']))
            if d['kind'] == 'OTHER':
                alerts.append(dict(kind='TX_NOT_APPROVE_OR_ROUTER_SWAP', tx=d['hash'], to=d['to']))
            for a in d['approvals']:
                if a['spender'] != ROUTER:
                    alerts.append(dict(kind='APPROVAL_TO_OTHER_SPENDER', tx=d['hash'], **a))
            if d['kind'] == 'SWAP':
                s['trades'] += 1
                apply_fill(s, d, alerts)
            append('transactions.jsonl', d)
        if missing:
            # Keep the scan start, so the next poll searches these blocks again.
            hold_scan = True
        else:
            s['nonce'] = nonce
    held, allowance = balances(tag)
    px = prices()
    for sym in STOCKS:
        if held[sym] != s['units'][sym]:
            alerts.append(dict(kind='HOLDING_DIFFERS_FROM_FILLS', symbol=sym, chain=held[sym], fills=s['units'][sym]))
    lingering = {k: v for k, v in allowance.items() if v}
    if lingering:
        alerts.append(dict(kind='ROUTER_ALLOWANCE_OPEN', allowances=lingering))
    if held['BNB'] < EXIT_RESERVE_WEI:
        alerts.append(dict(kind='BNB_BELOW_EXIT_RESERVE', bnb_wei=held['BNB'], reserve_wei=EXIT_RESERVE_WEI))
    value = {k: (Fraction(held[k], E18) * px[k]) if px.get(k) is not None else None for k in STOCKS}
    stock_value = sum(v for v in value.values() if v is not None) if all(v is not None for v in value.values()) else None
    unreal = (stock_value - sum(s['cost'].values())) if stock_value is not None else None
    equity = Fraction(held['USDT'], E18) + stock_value if stock_value is not None else None
    snap = dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(fin['timestamp'], 16))), block=block, nonce=nonce,
                usdt=float(Fraction(held['USDT'], E18)), bnb=float(Fraction(held['BNB'], E18)),
                units={k: float(Fraction(held[k], E18)) for k in STOCKS if held[k]},
                value_usdt={k: float(v) for k, v in value.items() if v is not None and held[k]},
                equity_ex_bnb_usdt=float(equity) if equity is not None else None,
                pnl_vs_start_ex_bnb_usdt=float(equity - 96) if equity is not None else None,
                realized_usdt=float(s['realized']), unrealized_usdt=float(unreal) if unreal is not None else None,
                gas_spent_bnb=float(Fraction(s['gas'], E18)), trades=s['trades'], failed_txs=s['failed'],
                price_error=px.get('_error'), alerts=len(alerts))
    append('snapshots.jsonl', snap)
    for a in alerts:
        append('alerts.jsonl', dict(a, utc=snap['utc'], block=block))
    if not hold_scan:
        s['block'] = block
    save_state(s)
    return snap, alerts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--interval', type=int, default=60)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    s = load_state()
    while True:
        try:
            snap, alerts = poll(s)
            print(json.dumps(snap, sort_keys=True), flush=True)
            for a in alerts:
                print('ALERT ' + json.dumps(a, sort_keys=True, default=str), flush=True)
        except Exception as e:
            print(json.dumps(dict(poll_error=type(e).__name__, detail=str(e)[:160])), flush=True)
        if args.once:
            return
        time.sleep(args.interval)


if __name__ == '__main__':
    main()

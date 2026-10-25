"""Generate an in-memory-only primary-host LD10 probe from the reviewed LD02 collector.

The selected profile travels via stdin; no host files, configs, services or ledger are written.
The compressed sanitized result includes private exact quote/portfolio evidence. Keep it outside Git.
"""
import argparse
import base64
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

# LD10-P03 D5: the installed host build predates the balanced exit split, so the probe
# carries this self-contained copy; tests pin it to caps_review.exit_children.
EXIT_CHILDREN = """
def exit_children(whole, proceeds, cap_raw, limit):
    children, remaining = [], whole
    while remaining and len(children) < limit:
        value = proceeds * remaining
        parts = max(1, -(-value * 10100 // (whole * 10000 * cap_raw)))
        children.append(remaining if parts == 1 else remaining // parts)
        remaining -= children[-1]
    return children + ([remaining] if remaining else [])
"""


# IDEA-103 FI4: a FINAL install captures a fresh final wallet while a dev run is still installed on primary.
TARGET = (
    ("    wallet = config['wallet_address'].lower()\n",
     "    wallet = TARGET_WALLET  # IDEA-103: the fresh final wallet, not the installed run's\n"),
    ("    check = compare_balances(portfolio, plain, settled_block=projection.get('settled_block'))\n",
     "    # IDEA-103: a fresh wallet has no ledger; reconcile against an empty book, so every unit shows as chain units.\n"
     "    fresh = dict(portfolio, cash_units=0, bnb_units=0, reservations={},\n"
     "                 positions={s: dict(p, units=0, cost_basis_units=0) for s, p in portfolio['positions'].items()})\n"
     "    check = compare_balances(fresh, plain, settled_block=None)\n"
     "    if check['status'] != 'SKIPPED':\n"
     "        check = dict(check, status='FRESH_TARGET')\n"),
    ("        run=dict(version=run[1], epoch=run[2], quarantined=run[3]))\n",
     "        run=dict(version=run[1], epoch=run[2], quarantined=run[3]), target='FRESH_FINAL_WALLET')\n"),
)


def script(profile_bytes, target_wallet=None):
    if target_wallet is not None and (type(target_wallet) is not str
                                      or not re.fullmatch(r'0x[0-9a-fA-F]{40}', target_wallet)):
        raise ValueError('target wallet must be a 0x-prefixed 40-hex address')
    source = (ROOT / 'docs/build/ops/ld02-20261020/execution-packet.sh').read_text()
    source = source.split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    source = 'SELECTED_PROFILE_B64 = ' + repr(base64.b64encode(profile_bytes).decode()) + '\n' + source
    if target_wallet is not None:
        for old, new in TARGET:
            assert source.count(old) == 1, old
            source = source.replace(old, new, 1)
        source = 'TARGET_WALLET = ' + repr(target_wallet.lower()) + '\n' + source
    needle = "    driver = config['driver']\n"
    source = source.replace(needle, "    selected_raw = base64.b64decode(SELECTED_PROFILE_B64)\n    profile = json.loads(selected_raw)\n" + needle, 1)
    source = source.replace("    forbidden = forbidden_values(config, secrets, providers)\n", "    forbidden = [v for v in forbidden_values(config, secrets, providers) if not isinstance(v, str) or v.lower() not in (wallet, wallet[2:])]\n", 1)
    loop = ("        for side, units in (('BUY', minimum), ('BUY', cap), ('SELL', None)):\n"
            "            if side == 'SELL':\n                units = sell_units\n")
    assert source.count(loop) == 1
    source = source.replace(loop, "        steps = [('BUY', minimum), ('BUY', cap), ('SELL', None)]\n"
        "        for side, units in steps:\n            if side == 'SELL' and units is None:\n"
        "                units = sell_units\n", 1)
    # Request every planned balanced child of the full-size exit after its sizing quote.
    child = "                row = quote_row(symbol, side, units, amount, decimals, record, module, TOKENS, USDT)\n"
    assert source.count(child) == 1
    source = source.replace(child, child +
        "                if side == 'SELL' and len(steps) == 3:\n"
        "                    steps.extend(('SELL', c) for c in sorted(set(exit_children(\n"
        "                        units, row['receive_units'], cap * 10**12, 2))) if c != units)\n", 1)
    source = EXIT_CHILDREN + source
    source = source.replace("                if side == 'BUY' and units == minimum:\n",
        "                if side == 'BUY':\n                    sell_units = max(sell_units or 0, row['receive_units'])\n"
        "                if side == 'BUY' and units == minimum:\n", 1)
    source = source.replace("    return packet, forbidden\n", """    packet['selected_profile_sha256'] = hashlib.sha256(selected_raw).hexdigest()
    packet['portfolio_source_sha256'] = Document.from_dict(portfolio).digest('PortfolioState.v1')
    caps_portfolio = {k: portfolio[k] for k in ('schema', 'wallet_id', 'run_id', 'mode', 'cash_units',
                                               'bnb_units', 'bnb_decimals', 'positions', 'reservations')}
    packet['private_caps_inputs'] = dict(wallet=wallet, portfolio=caps_portfolio,
        token_decimals={s: observation['tokens'][s]['decimals'] for s in TOKENS},
        quote_artifacts=web3.records)
    # Private review needs the public wallet address. Continue refusing secrets,
    # provider URLs and database endpoints; omit only public token image metadata.
    for record in packet['private_caps_inputs']['quote_artifacts']:
        record['original_record_sha256'] = hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        record.pop('response_body_base64', None)  # exact upstream response_sha256 is retained
        response_data = record.get('response', {}).get('data')
        rows = response_data if isinstance(response_data, list) else [response_data]
        projected = []
        for row in rows:
            if isinstance(row, dict):
                rr, tx = row.get('routerResult', {}), row.get('tx', {})
                projected.append(dict(executionMode=row.get('executionMode'), rfq=row.get('rfq'),
                    routerResult=dict(fromToken={k: v for k, v in rr.get('fromToken', {}).items()
                                                 if k in ('tokenContractAddress', 'decimal')},
                                      toToken={k: v for k, v in rr.get('toToken', {}).items()
                                               if k in ('tokenContractAddress', 'decimal')},
                                      fromTokenAmount=rr.get('fromTokenAmount'),
                                      toTokenAmount=rr.get('toTokenAmount')),
                    tx={k: v for k, v in tx.items() if k in ('to', 'from', 'chainId', 'value', 'gas',
                                                           'gasPrice', 'minReceiveAmount')},
                    calldata_sha256=hashlib.sha256(str(tx.get('data', '')).encode()).hexdigest()))
        if isinstance(record.get('response'), dict):
            record['response'] = dict(code=record['response'].get('code'),
                                      data=projected if isinstance(response_data, list) else projected[0])
    return packet, forbidden
""", 1)
    source = source.replace('    print(text)\n', "    print(base64.b64encode(zlib.compress(text.encode(), 9)).decode())\n", 1)
    return "set -eu\ncd /opt/larp/current\nenv PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'\n" + source + '\nPY\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target-wallet', help='IDEA-103 FINAL: read this fresh wallet instead of the installed run\'s')
    args = parser.parse_args()
    with args.output.open('x') as stream:
        stream.write(script(args.profile.read_bytes(), target_wallet=args.target_wallet))


if __name__ == '__main__':
    main()

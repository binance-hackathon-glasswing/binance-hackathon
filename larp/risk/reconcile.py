"""IDEA-055 (#36): compare the ledger with the chain, and the planner's view while a deficit is recorded.

Pure functions. Nothing here writes the ledger: a mismatch is reported, never booked, and no fill is invented.

Settlement books stock units as raw chain units, floors USDT credits to the 6-decimal money scale and refuses any
debit that is not exact in the ledger scale (larp/execution_live/settlement.py). So after flooring the chain's units
to the ledger scale, the chain is never below the ledger without a defect: any shortfall is a DEFICIT (tolerance
zero), and USDT rounding dust is at most a SURPLUS.
"""

from copy import deepcopy

from larp.contracts import ContractError
from larp.strategy.schema import MONEY_SCALE

CASH_DECIMALS = len(str(MONEY_SCALE)) - 1
NATIVE_DECIMALS = 18


def _floor_to(units, chain_decimals, ledger_decimals):
    if type(units) is not int or units < 0 or type(chain_decimals) is not int or type(ledger_decimals) is not int:
        raise ContractError('Balance units and decimals must be non-negative integers')
    if ledger_decimals > chain_decimals:
        raise ContractError('The ledger cannot be finer than the chain')
    return units // 10 ** (chain_decimals - ledger_decimals)


def compare_balances(ledger, observation, *, settled_block):
    """BalanceCheck.v1 for a ledger (PortfolioState.v1 fields) and a ChainBalances.v1 observation.

    SKIPPED when the comparison would not mean anything: a transaction still pending at the node, or an observation
    block older than the newest receipt the ledger has applied (`settled_block`, None before the first)."""
    o = observation
    base = dict(schema='BalanceCheck.v1', block_number=o['block_number'], block_hash=o['block_hash'],
                settled_block=settled_block, assets={}, deficits={}, surplus=[])
    if o['pending_nonce'] != o['latest_nonce']:
        return dict(base, status='SKIPPED', reason='PENDING_NONCE')
    if settled_block is not None and o['block_number'] < settled_block:
        return dict(base, status='SKIPPED', reason='BLOCK_BEHIND_LEDGER')
    tokens = o['tokens']
    positions = ledger['positions']
    unknown = sorted(s for s, p in positions.items() if s not in tokens and p.get('units'))
    if unknown or 'USDT' not in tokens:
        raise ContractError('The observation lacks a ledger asset: ' + ','.join(unknown or ['USDT']))
    pairs = {'USDT': (ledger['cash_units'], _floor_to(tokens['USDT']['units'], tokens['USDT']['decimals'],
                                                      CASH_DECIMALS)),
             'BNB': (ledger['bnb_units'], _floor_to(o['native_wei'], NATIVE_DECIMALS, ledger['bnb_decimals']))}
    for symbol, row in tokens.items():
        if symbol == 'USDT':
            continue
        position = positions.get(symbol)
        decimals = position['decimals'] if position else row['decimals']
        pairs[symbol] = ((position or {}).get('units', 0), _floor_to(row['units'], row['decimals'], decimals))
    assets, deficits, surplus = {}, {}, []
    for asset, (book, chain) in sorted(pairs.items()):
        if type(book) is not int or book < 0:
            raise ContractError('Ledger units must be non-negative integers')
        kind = 'MATCH' if chain == book else ('SURPLUS' if chain > book else 'DEFICIT')
        assets[asset] = {'ledger_units': book, 'chain_units': chain, 'difference': chain - book, 'class': kind}
        if kind == 'DEFICIT':
            deficits[asset] = book - chain
        elif kind == 'SURPLUS':
            surplus.append(asset)
    status = 'DEFICIT' if deficits else ('SURPLUS_ONLY' if surplus else 'MATCH')
    return dict(base, status=status, assets=assets, deficits=deficits, surplus=surplus)


def spendable_view(ledger, deficits):
    """The ledger as the planner may use it while `deficits` ({asset: units}) are recorded: each asset less its
    deficit, never below zero. A copy; the journaled ledger is unchanged. After a capped sale settles, the leftover
    phantom units equal the deficit, so the view of them is zero and no order is made for them."""
    if not deficits:
        return ledger
    view = deepcopy(ledger)
    for asset, units in deficits.items():
        if type(units) is not int or units < 0:
            raise ContractError('Recorded deficits must be non-negative integers')
        if asset == 'USDT':
            view['cash_units'] = max(0, view['cash_units'] - units)
        elif asset == 'BNB':
            view['bnb_units'] = max(0, view['bnb_units'] - units)
        elif asset in view['positions']:
            position = view['positions'][asset]
            position['units'] = max(0, position['units'] - units)
    return view

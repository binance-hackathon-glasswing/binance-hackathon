"""IDEA-104 S5-SIZE01: cash-funded opening lots, scoped to the S5 rehearsal.

The measured entry minimum and all exact-quote gates remain unchanged. A larger
opening lot makes a smaller wallet's targets executable without counting gas.
"""
from fractions import Fraction

from larp.contracts import ContractError
from .schema import ceil, floor, integer


def name_target(p, cfg, nominal, *, level, capital_scale, safe_equity, enabled=True):
    """A high-level target bounded by the existing allocation and hard-name caps.

    Policy and independent risk admission each apply this bound. Held names keep
    the same high-level target so a fill cannot immediately create a sell-back.
    Reduced levels and deep-cut handling use the ordinary target.
    """
    lot = p.get('s5_entry_lot_units')
    if lot is None or not enabled or level != cfg['high'] * capital_scale or safe_equity <= 0:
        return nominal
    ceiling = min(cfg['high'] * cfg['cap'] * capital_scale, cfg['hard'])
    weight = Fraction(lot, safe_equity)
    return max(nominal, weight) if weight <= ceiling else nominal


def opening_cash_check(p, cash_units):
    """Pre-install feasibility on a fresh flat book; never counts BNB or assumes a fill.

    Quote execution, cash reservations, gas and market/provider checks still occur
    at runtime. This check replaces the obsolete fixed 98.32 USDT guard.
    """
    from .profiles import validate_live
    from .s1 import config
    validate_live(p)
    if 's5_entry_lot_units' not in p:
        raise ContractError('S5 sizing check requires its opening-lot profile')
    cash = integer(cash_units)
    cfg = config(p)
    stock = max(0, cash - p['cost_reserve_units'])
    lot = p['s5_entry_lot_units']
    if lot > cfg['high'] * cfg['cap'] * stock or lot > cfg['hard'] * stock:
        raise ContractError('S5 cash cannot fund its opening lot within the existing name caps')
    desired = max(lot, ceil(cfg['high'] * max(cfg['weights'].values()) * stock))
    entry = min(desired, p['per_trade_cap_units'] - p['cost_reserve_units'])
    slots = min(len(cfg['weights']), floor(cfg['high'] * stock / entry),
                cash // (entry + p['cost_reserve_units']))
    if entry < p['minimum_trade_units'] or slots < 1:
        raise ContractError('S5 cash cannot fund an executable opening lot')
    return dict(stock_capital_units=stock, opening_lot_units=entry, maximum_opening_lots=slots)

"""IDEA-093 SC (GAP-74, F-125): the activation self-check on the final wallet, in the same run as the scored run.

Before `trade_after`, one BUY of about `pay_units` of `symbol`, then a mandatory SELL of the whole position. The phase
comes from the profile, the persisted risk state, the ledger and the time, so the policy and the independent planner
agree. The planner commits BOUGHT and DONE (or EXPIRED) to the risk state; DONE and EXPIRED are never undone. Profiles
without the key are unaffected (phase None).

IDEA-110: an optional `max_cost_units` makes it a micro self-check: `pay_units` may lie below the minimum trade, and
the planner bounds that one BUY's cost absolutely instead of by the bps entry-cost cap.
"""
from larp.contracts import ContractError
from .schema import SYMBOLS, instant, integer

KEY = 'activation_self_check'
FIELDS = frozenset({'symbol', 'buy_after', 'buy_until', 'flat_by', 'pay_units'})
OPTIONAL = frozenset({'max_cost_units'})  # IDEA-110 micro self-check
SCOPE = 'An activation self-check needs a FINAL TREND_GUARDED_VOL profile (IDEA-093 SC, GAP-74)'
REASON = 'ACTIVATION_SELF_CHECK'


def config(profile):
    """The checked self-check block, or None when the profile has none."""
    if KEY not in profile:
        return None
    value = profile[KEY]
    if type(value) is not dict or not FIELDS <= set(value) <= FIELDS | OPTIONAL or value['symbol'] not in SYMBOLS:
        raise ContractError('activation_self_check needs exactly: ' + ','.join(sorted(FIELDS))
                            + ' (optional: ' + ','.join(sorted(OPTIONAL)) + ')')
    try:
        buy_after, buy_until, flat_by = (instant(value[k]) for k in ('buy_after', 'buy_until', 'flat_by'))
    except (ContractError, TypeError, ValueError, AttributeError):
        raise ContractError('activation_self_check times must be ISO-8601 UTC instants') from None
    if not buy_after < buy_until < flat_by <= instant(profile['trade_after']):
        raise ContractError('activation_self_check must satisfy buy_after < buy_until < flat_by <= trade_after')
    pay = integer(value['pay_units'], 1)
    micro = 'max_cost_units' in value
    if micro and not 0 < integer(value['max_cost_units'], 1) <= profile['cost_reserve_units']:
        raise ContractError('activation_self_check max_cost_units must lie in (0, cost_reserve_units]')
    floor_units = 1 if micro else profile['minimum_trade_units']
    if not floor_units <= pay <= profile['per_trade_cap_units'] - profile['cost_reserve_units']:
        raise ContractError('activation_self_check pay_units must lie between the minimum trade and the cap')
    cfg = dict(symbol=value['symbol'], buy_after=buy_after, buy_until=buy_until, flat_by=flat_by, pay_units=pay)
    if micro:
        cfg['max_cost_units'] = value['max_cost_units']
    return cfg


def require_scope(profile):
    """The self-check is decided only for the scored FINAL profile (validate_live)."""
    if KEY not in profile:
        return
    if profile.get('environment') != 'FINAL' or profile.get('baseline') != 'TREND_GUARDED_VOL':
        raise ContractError(SCOPE)
    config(profile)


def phase(profile, risk, ledger, now):
    """None, WAIT, BUY, SELL, DONE or EXPIRED."""
    cfg = config(profile)
    if cfg is None:
        return None
    recorded = risk.get(KEY) if type(risk) is dict else None
    if recorded in ('DONE', 'EXPIRED'):
        return recorded
    if now >= cfg['flat_by']:
        return 'EXPIRED'
    units = ledger['positions'].get(cfg['symbol'], {}).get('units', 0)
    if units > profile.get('dust_units', 0):
        return 'SELL'
    if ledger['reservations']:
        return 'WAIT'  # a self-check leg is in flight; never stack another
    if recorded == 'BOUGHT':
        return 'DONE'
    return 'BUY' if cfg['buy_after'] <= now < cfg['buy_until'] else 'WAIT'


def recorded(phase_value):
    """The risk-state value the planner commits for a phase, or None to leave it unset."""
    return {'SELL': 'BOUGHT', 'DONE': 'DONE', 'EXPIRED': 'EXPIRED'}.get(phase_value)

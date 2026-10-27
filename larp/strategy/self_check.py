"""IDEA-093 SC (GAP-74, F-125): the activation self-check on the final wallet, in the same run as the scored run.

Before `trade_after`, one BUY of about `pay_units` of `symbol`, then a mandatory SELL of the whole position. The phase
comes from the profile, the persisted risk state, the ledger and the time, so the policy and the independent planner
agree. The planner commits BOUGHT and DONE (or EXPIRED) to the risk state; DONE and EXPIRED are never undone. Profiles
without the key are unaffected (phase None).

IDEA-110 TEMP-SC: the temporary `larp-final-selfcheck-temp-v1` policy is only this self-check, below 1 USDT, on its
own entry-cost floor (`self_check_entry_cost_cap_bps`), and must end by the F-127 pause. No other BUY is allowed.
"""
from fractions import Fraction

from larp.contracts import ContractError
from .schema import SYMBOLS, ceil, instant, integer

KEY = 'activation_self_check'
FIELDS = frozenset({'symbol', 'buy_after', 'buy_until', 'flat_by', 'pay_units'})
SCOPE = 'An activation self-check needs a FINAL TREND_GUARDED_VOL profile (IDEA-093 SC, GAP-74)'
REASON = 'ACTIVATION_SELF_CHECK'
TEMP_POLICY_ID = 'larp-final-selfcheck-temp-v1'
TEMP_COST_KEY = 'self_check_entry_cost_cap_bps'
TEMP_COST_CAP_BPS = 1000
TEMP_MAX_PAY_UNITS = 999_999  # total stock bought stays under 1 USDT
TEMP_PAUSE = '2026-10-28T10:00:00Z'  # F-127: a temp run never reaches the scored phase
TEMP_SCOPE = 'The temporary self-check needs the FINAL S1 temp policy, its 1000bp floor and an end by the F-127 pause'


def temp(profile):
    """IDEA-110: the temporary sub-1-USDT self-check policy."""
    return profile.get('policy_id') == TEMP_POLICY_ID


def temp_floor(profile):
    """IDEA-110: the self-check BUY's own minimum, validate_live's gas formula at the temp entry-cost cap."""
    summary = profile['quote_cost_summary']
    sizing = integer(profile['gas_sizing_budget_units'] if 'gas_sizing_budget_units' in profile
                     else profile['gas_action_budget_units'], 1)
    gas_value = ceil(Fraction(sizing * summary['bnb_price_units'], 10**summary['bnb_decimals']))
    return max(ceil(Fraction(gas_value * 10000, profile[TEMP_COST_KEY] - row['spread_bps']
                             - min(50, 2 * row['median_impact_bps']) - row['fee_bps']))
               for row in summary['symbols'].values())


def config(profile):
    """The checked self-check block, or None when the profile has none."""
    if KEY not in profile:
        return None
    value = profile[KEY]
    if type(value) is not dict or set(value) != FIELDS or value['symbol'] not in SYMBOLS:
        raise ContractError('activation_self_check needs exactly: ' + ','.join(sorted(FIELDS)))
    try:
        buy_after, buy_until, flat_by = (instant(value[k]) for k in ('buy_after', 'buy_until', 'flat_by'))
    except (ContractError, TypeError, ValueError, AttributeError):
        raise ContractError('activation_self_check times must be ISO-8601 UTC instants') from None
    if not buy_after < buy_until < flat_by <= instant(profile['trade_after']):
        raise ContractError('activation_self_check must satisfy buy_after < buy_until < flat_by <= trade_after')
    pay = integer(value['pay_units'], 1)
    if temp(profile):
        if not temp_floor(profile) <= pay <= min(TEMP_MAX_PAY_UNITS,
                                                 profile['per_trade_cap_units'] - profile['cost_reserve_units']):
            raise ContractError('Temporary self-check pay_units must lie between its 1000bp floor and 1 USDT')
    elif not profile['minimum_trade_units'] <= pay <= profile['per_trade_cap_units'] - profile['cost_reserve_units']:
        raise ContractError('activation_self_check pay_units must lie between the minimum trade and the cap')
    return dict(symbol=value['symbol'], buy_after=buy_after, buy_until=buy_until, flat_by=flat_by, pay_units=pay)


def require_scope(profile):
    """The self-check is decided only for the scored FINAL profile (validate_live)."""
    if temp(profile) or TEMP_COST_KEY in profile:
        if (not temp(profile) or KEY not in profile or profile.get('environment') != 'FINAL'
                or profile.get('mode') != 'LIVE' or profile.get('baseline') != 'TREND_GUARDED_VOL'
                or type(profile.get(TEMP_COST_KEY)) is not int or profile[TEMP_COST_KEY] != TEMP_COST_CAP_BPS
                or any(instant(profile[k]) > instant(TEMP_PAUSE)
                       for k in ('trade_after', 'new_risk_end', 'flatten_start', 'signing_end'))):
            raise ContractError(TEMP_SCOPE)
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

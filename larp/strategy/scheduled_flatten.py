"""IDEA-092 S3: a scheduled sell-all inside the window, then the profile's strategy (S2) resumes from a fresh book.

From `scheduled_flatten_at` every held name is a mandatory SELL and no BUY is planned until the book is flat. The first
round at or after that time that sees every stock at or below `dust_units` and no reservations records
`scheduled_flatten: DONE` in the persisted risk state; DONE is never undone (a one-time switch). Profiles without the
key are unaffected (state None).
"""
from larp.contracts import ContractError
from .schema import instant

KEY = 'scheduled_flatten_at'
SCOPE = 'A scheduled flatten needs a REHEARSAL with KIT_OPEN_STATE hours (IDEA-092 S3)'


def at(profile):
    """The checked instant, or None when the profile has no scheduled flatten."""
    if KEY not in profile:
        return None
    value = profile[KEY]
    try:
        when = instant(value)
    except (ContractError, TypeError, ValueError, AttributeError):
        raise ContractError('scheduled_flatten_at must be an ISO-8601 UTC instant') from None
    if not instant(profile['trade_after']) < when < instant(profile['new_risk_end']):
        raise ContractError('scheduled_flatten_at must fall after trade_after and before new_risk_end')
    return when


def require_scope(profile):
    """S3 relaxes nothing, but it is decided only for S2's REHEARSAL; S2-1's own check covers SHADOW and `dev`."""
    if KEY not in profile:
        return
    from .execution_bounds import open_state_hours
    if profile.get('environment') != 'REHEARSAL' or not open_state_hours(profile):
        raise ContractError(SCOPE)
    at(profile)


def buy_deadline(profile, risk):
    """Pre-flatten BUY authority ends at the schedule; a committed DONE plan reopens it.

    Consumers use the independent plan's risk state, including the first flat/DONE round, rather than the
    policy proposal or the pre-plan ledger. Already submitted transactions still reconcile normally.
    """
    when = at(profile)
    if when is None or (type(risk) is dict and risk.get('scheduled_flatten') == 'DONE'):
        return None
    return when


def state(profile, risk, ledger, now):
    """None (no scheduled flatten), BEFORE, PENDING or DONE."""
    when = at(profile)
    if when is None:
        return None
    if type(risk) is dict and risk.get('scheduled_flatten') == 'DONE':
        return 'DONE'
    if now < when:
        return 'BEFORE'
    # Dust counts as flat (the planner never sells at or below `dust_units`), so a residue cannot block S2 forever.
    dust = profile.get('dust_units', 0)
    flat = all(pos['units'] <= dust for pos in ledger['positions'].values()) and not ledger['reservations']
    return 'DONE' if flat else 'PENDING'

"""IDEA-097 S4: a REHEARSAL may start from the previous run's exported book instead of a stock-flat wallet.

`holdings_carry_over: "RUN_EXPORT"` declares that `gate_a.initial_state` must take each stock's units and cost basis
from a reviewed `HoldingsCarryOver.v1` export of the previous run (exact on-chain units, the run's own recorded cost).
Without the key the stock-flat rule is unchanged.
"""
from larp.contracts import ContractError

KEY = 'holdings_carry_over'
VALUE = 'RUN_EXPORT'
SCOPE = 'A holdings carry-over needs a REHEARSAL with KIT_OPEN_STATE hours and no scheduled flatten (IDEA-097 S4)'


def declared(profile):
    """True when the profile requires a carried-over book; refuses any other value."""
    if KEY not in profile:
        return False
    if profile[KEY] != VALUE:
        raise ContractError('holdings_carry_over must be "RUN_EXPORT"')
    return True


def require_scope(profile):
    """S4 relaxes only the stock-flat start, and only for S2's REHEARSAL on the dev wallet (S2-1's scope check covers
    SHADOW and `dev`). S3's scheduled flatten is a different test and is not combined with it."""
    if not declared(profile):
        return
    from .execution_bounds import open_state_hours
    from .scheduled_flatten import KEY as SCHEDULED
    if profile.get('environment') != 'REHEARSAL' or not open_state_hours(profile) or SCHEDULED in profile:
        raise ContractError(SCOPE)

"""What a HALT still allows (D-DN-09, IDEA-049-B; #34, #52). Pure functions over the run projection.

CLOCK, and any reason not listed in PAUSING, blocks every signature: the time or the run cannot be trusted. The pausing
reasons say the receiver is behind (DELIVERY_DEADLINE) or rounds keep failing (REPEATED_FAILURES); they stop new
spending and discretionary trades only. Under a HALT made only of pausing reasons, a planned mandatory bStock SELL
(Class 1 and falsifier exits, deep cut, hard-cap trims, terminal flatten) still executes under every other check. The
integrity quarantine is separate and fences everything.

Shared by the coordinator, the command store, the driver, the execution guards and the signer's own run check, so the
rule has one definition. No runtime imports: the signer host loads this module too.
"""

PAUSING = frozenset(('DELIVERY_DEADLINE', 'REPEATED_FAILURES'))


def reasons(projection):
    return sorted((projection.get('halt') or {}).get('reasons', {}))


def pausing_only(projection):
    """True when the run is halted and every reason only pauses new spending."""
    active = reasons(projection)
    return bool(active) and set(active) <= PAUSING


def mandatory_reduction(intent):
    """A planned intent that a pausing HALT still lets through: a mandatory SELL of a bStock."""
    return (type(intent) is dict and intent.get('mandatory') is True and intent.get('side') == 'SELL'
            and intent.get('kind', 'BSTOCK_TRADE') == 'BSTOCK_TRADE')


def permits(projection, round_id, intent_id):
    """May this planned intent proceed under the run's current HALT? True when the run is not halted (other gates
    decide); under a HALT, only a mandatory bStock SELL that the open round itself planned, and only for pausing
    reasons."""
    if not reasons(projection):
        return True
    if not pausing_only(projection):
        return False
    record = (projection.get('round_records') or {}).get(round_id)
    if type(record) is not dict:
        return False
    return any(type(i) is dict and i.get('intent_id') == intent_id and mandatory_reduction(i)
               for i in (record.get('plan') or {}).get('intents', []))


__all__ = ['PAUSING', 'reasons', 'pausing_only', 'mandatory_reduction', 'permits']

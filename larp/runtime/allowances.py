"""IDEA-096 F4: one low-severity incident per quiet decision boundary with nonzero router allowances."""
from larp.marketdata.allowances import observe
from larp.runtime.coordinator import batch_for
from larp.storage.postgres import Conflict


class RouterAllowanceCheck:
    def __init__(self, coordinator, decoder, wallet):
        self.coordinator, self.decoder, self.wallet = coordinator, decoder, wallet
        self.next_ms = 0

    def __call__(self, now_ms):
        if now_ms < self.next_ms:
            return 'NOT_DUE'  # before any store read: this runs on every driver cycle
        c = self.coordinator
        current = c.store.load(c.run_id)
        run = current.read()
        projection = run['projection']
        if (run['reservations'] or c.store.open_rounds(c.run_id)
                or any(r.get('execution_pending') for r in projection.get('round_records', {}).values())):
            return 'DEFERRED_IN_FLIGHT'
        boundary = projection.get('last_decision_ms', 0)
        self.next_ms = now_ms + 60_000
        identity = 'allowance:' + str(boundary)
        if c.store.event(c.run_id, identity) is not None:
            return 'CHECKED'
        try:
            value = observe(self.decoder, self.wallet)
        except (RuntimeError, OSError):
            # Passive monitor: Blocked/DependencyUnavailable, an artifact write failure or a full disk must not
            # stop the round or its exits (as InitialGasCheck's SKIPPED).
            return 'ALLOWANCE_READ_UNAVAILABLE'
        if value['reason'] == 'CLEAN':
            return 'CLEAN'
        try:
            c.store.commit(batch_for(current, identity, dict(kind='INCIDENT', incident=dict(
                type='DIRTY_ROUTER_ALLOWANCE', severity='LOW', at_ms=now_ms, decision_ms=boundary,
                allowances=value['allowances'], symbols=value['symbols']))))
        except Conflict:
            return 'CONFLICT'
        return 'DIRTY_ROUTER_ALLOWANCE'

"""LD08-IG01: initial-only gas incidents at a quiet execution boundary.

No RPC, signing, funding or HALT. The pinned profile supplies the action gas
budget; actual measurement/cleanup coverage and numeric approval remain LD09/10.
The planner and execution service independently enforce every action's gas.
"""
from copy import deepcopy

from larp.contracts import ContractError, Document
from larp.integration.runtime import ledger_from
from larp.risk.reconcile import spendable_view
from larp.runtime.coordinator import batch_for
from larp.strategy.profiles import validate_live
from larp.strategy.schema import initial_gas_only, integer


class InitialGasCheck:
    def __init__(self, coordinator, profile):
        validate_live(profile)
        if not initial_gas_only(profile):
            raise ContractError('Initial gas monitor requires initial-only scope')
        self.coordinator = coordinator
        self.action_budget = profile['gas_action_budget_units']
        self.reserve = profile['exit_gas_reserve_units']
        self.decimals = profile['quote_cost_summary']['bnb_decimals']
        self.profile_hash = Document.from_dict(profile).digest('StrategyProfile.v1')

    def __call__(self, now_ms):
        c = self.coordinator
        current = c.store.load(c.run_id)
        run = current.read()
        projection = run['projection']
        previous = projection.get('gas_health') or {}
        last = max(previous.get('at_ms', 0), projection.get('last_decision_ms', 0))
        if type(now_ms) is not int or now_ms < last:
            return 'CLOCK_REFUSED'
        # Never introduce a journal version between I3 hand-off and claim, or
        # compare settled gas with gas still owned by an unresolved attempt.
        if (run['reservations'] or c.store.open_rounds(c.run_id)
                or any(r.get('execution_pending') for r in projection.get('round_records', {}).values())):
            return 'DEFERRED_IN_FLIGHT'
        ledger = ledger_from(projection, run['reservations'])
        ledger = spendable_view(ledger, (projection.get('balance_check') or {}).get('deficits') or {})
        if ledger['bnb_decimals'] != self.decimals:
            raise ContractError('Gas budget and ledger BNB scales differ')
        available = integer(ledger['bnb_units'])
        status = ('PAIR_UNAFFORDABLE' if available < self.action_budget else
                  'BELOW_EXIT_RESERVE' if available < self.reserve else 'OK')
        if status == previous.get('status', 'OK') and previous.get('profile_hash', self.profile_hash) == self.profile_hash:
            return status
        state = dict(status=status, pair_unaffordable=status == 'PAIR_UNAFFORDABLE',
                     spendable_bnb_units=available, bnb_decimals=self.decimals,
                     action_budget_units=self.action_budget, exit_reserve_units=self.reserve,
                     profile_hash=self.profile_hash, at_ms=now_ms)
        changed = deepcopy(projection)
        changed['gas_health'] = state
        incident = dict(type='LOW_GAS_CLEARED' if status == 'OK' else 'LOW_GAS', **state)
        event_id = f"incident:gas:{run['epoch']}:{run['version'] + 1}"
        c.store.commit(batch_for(current, event_id, dict(kind='INCIDENT', incident=incident), projection=changed))
        return status

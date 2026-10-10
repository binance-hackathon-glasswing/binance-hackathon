"""Execution observations -> coordinator state (RT21 G3, G4).

ExecutionObservation.v1 (as Keith's accounting reads it) carries one of:
APPROVAL, FILL, REVERT: final, settled facts reduced by Keith's advance_accounting;
BROADCAST_ATTEMPTED: a swap was submitted; it maps the tx hash for the audit only.
Every observation names run_id, wallet_id, event_id, intent_id and round_id.
"""

from copy import deepcopy

from larp.contracts import ContractError, Document
from larp.integration.strategy import balances
from larp.risk.accounting import advance_accounting

TX_PREFIX = '0x'


class ExecutionBridge:
    """ports.Execution: per-round intent tracking and terminal-round attestation."""

    def advance(self, state, observation):
        s, o = state.read(), observation.read()
        if s.get('schema') != 'ExecutionState.v1':
            raise ContractError('Unexpected execution state')
        intents = dict(s.get('intents', {}))
        intent_id, round_id, kind = o['intent_id'], o['round_id'], o['kind']
        entry = dict(intents.get(intent_id, {'round_id': round_id, 'status': 'ACTIVE'}))
        if entry['round_id'] != round_id:
            raise ContractError('Observation names another round for this intent')
        terminal = []
        if kind == 'BROADCAST_ATTEMPTED':
            entry['status'] = 'SUBMITTED'
            intents[intent_id] = entry
        elif kind == 'APPROVAL':
            intents[intent_id] = entry
        elif kind in ('FILL', 'REVERT') and o.get('intent_terminal') is True:
            intents.pop(intent_id, None)  # terminal intents leave the live state
            if not any(v['round_id'] == round_id for v in intents.values()):
                terminal = [round_id]
        else:
            raise ContractError('Unsupported execution observation')
        return Document.from_dict({'schema': 'ExecutionTransition.v1',
                                   'next_state': {'schema': 'ExecutionState.v1', 'intents': intents},
                                   'commands': [], 'observation_ids': [o['event_id']],
                                   'terminal_rounds': terminal})


def strategy_reducer(current, observation):
    """Coordinator reducer: Keith's accounting plus store reservation releases.

    Store reservations are released as gas is spent (BNB) and in full at the
    intent's terminal event; the `balances` mirror tracks the portfolio for the
    store's resource check. A swap broadcast maps its tx hash to the round's order
    and decision so the round's audit event carries it.
    """
    c, o = current.read(), observation.read()
    projection = deepcopy(c['projection'])
    portfolio = projection['portfolio']
    record = projection.get('round_records', {}).get(o['round_id'])
    if record is None:
        raise ContractError('Execution observation has no open round record')
    intent = next((i for i in record['plan']['intents'] if i['intent_id'] == o['intent_id']), None)
    if intent is None:
        raise ContractError('Observation names an intent its round did not plan')
    held = {r['asset']: r['units'] for r in c['reservations'] if r['intent_id'] == o['intent_id']}
    deltas = []
    if o['kind'] == 'BROADCAST_ATTEMPTED':
        tx = o['tx_hash']
        if type(tx) is not str or not tx.startswith(TX_PREFIX):
            raise ContractError('Broadcast observation needs a transaction hash')
        index = record['plan']['intents'].index(intent)
        record['orders'][index]['tx_hash'] = tx
        if not any(m['tx_hash'] == tx for m in record['swap_mappings']):
            record['swap_mappings'].append({'tx_hash': tx, 'decision_id': intent['decision_id'], 'step': 'swap'})
        return Document.from_dict({'projection': projection, 'reservation_deltas': []})
    accounted = {k: v for k, v in o.items() if k != 'round_id'}
    after = advance_accounting(Document.from_dict(portfolio), Document.from_dict(accounted)).read()
    if o['intent_terminal'] is True:
        deltas = [{'intent_id': o['intent_id'], 'asset': asset, 'units': -units}
                  for asset, units in sorted(held.items()) if units]
    elif o['gas_bnb_units'] and held.get('BNB'):
        deltas = [{'intent_id': o['intent_id'], 'asset': 'BNB', 'units': -min(held['BNB'], o['gas_bnb_units'])}]
    projection['portfolio'] = after
    projection['balances'] = balances(after)
    return Document.from_dict({'projection': projection, 'reservation_deltas': deltas})

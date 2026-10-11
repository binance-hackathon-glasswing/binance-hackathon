"""Canonical receipt facts for I4. Quotes and broadcasts never imply a fill."""
from datetime import datetime, timezone
from fractions import Fraction

from larp.execution import Blocked, USDT, NATIVE_BNB, integer
from .chain import hash_value, quantity

TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'


def _net_transfers(receipt, wallet, token):
    total = 0
    for log in receipt['logs']:
        if str(log.get('address', '')).lower() != token:
            continue
        topics = log.get('topics', [])
        if not topics or str(topics[0]).lower() != TRANSFER:
            continue
        if len(topics) != 3 or log.get('removed') is True:
            raise Blocked('malformed or removed transfer log')
        source, destination = [hash_value(t)[-40:] for t in topics[1:]]
        if any(hash_value(t)[2:26] != '0' * 24 for t in topics[1:]):
            raise Blocked('noncanonical transfer address')
        amount = int(hash_value(log['data']), 16)
        total += amount * ((destination == wallet[2:]) - (source == wallet[2:]))
    return total


def final_observation(state, attempt, proof, *, wallet_id, bnb_price_units, observed_at):
    intent = state.intent
    if not proof or proof.get('finality_verified') is not True:
        raise Blocked('canonical finalized receipt required')
    tx, receipt = proof['tx'], proof['receipt']
    payload = attempt.payload
    if (hash_value(tx['hash']) != attempt.tx_hash or hash_value(receipt['transactionHash']) != attempt.tx_hash
            or str(tx['from']).lower() != intent.wallet or str(receipt['from']).lower() != intent.wallet
            or quantity(tx['nonce']) != payload.nonce or str(tx['to']).lower() != payload.to
            or str(tx['input']).lower() != payload.data.lower() or quantity(tx['value']) != payload.value
            or quantity(tx['chainId']) != 56 or quantity(tx['gas']) != payload.gas
            or quantity(tx['gasPrice']) != payload.gas_price
            or hash_value(receipt['blockHash']) != proof['block_hash']
            or quantity(receipt['blockNumber']) != proof['block_number']
            or proof['finalized_height'] < proof['block_number']):
        raise Blocked('receipt fact conflicts with signed attempt')
    gas_used = quantity(receipt['gasUsed'])
    gas_price = quantity(receipt['effectiveGasPrice'])
    if not 0 < gas_used <= payload.gas or not 0 < gas_price <= payload.gas_price:
        raise Blocked('receipt gas exceeds signed authorization')
    gas = gas_used * gas_price
    price = integer(bnb_price_units, positive=True)
    gas_value = Fraction(gas * price, 10**18)
    status = quantity(receipt['status'])
    if status not in (0, 1):
        raise Blocked('unknown receipt status')
    kind = 'REVERT' if status == 0 else ('APPROVAL' if attempt.step == 'APPROVE' else 'FILL')
    if not wallet_id or not observed_at:
        raise Blocked('run wallet identity and observation time required')
    result = dict(schema='ExecutionObservation.v1', origin='EXECUTION_RECONCILER', kind=kind,
                  settlement='FINAL', run_id=intent.run_id, wallet_id=wallet_id,
                  round_id=intent.round_id, intent_id=intent.intent_id, attempt_id=attempt.attempt_id,
                  event_id=attempt.attempt_id + ':final', tx_hash=attempt.tx_hash,
                  decision_id=intent.decision_id, version_id=intent.version_id, observed_at=observed_at,
                  gas_bnb_units=gas, gas_value_units=-(-gas_value.numerator // gas_value.denominator),
                  intent_terminal=kind in ('FILL', 'REVERT'),
                  receipt_evidence=dict(block_hash=proof['block_hash'], block_number=proof['block_number'],
                                        finalized_height=proof['finalized_height'], canonical=True,
                                        gas_used=gas_used, effective_gas_price=gas_price))
    if kind == 'FILL':
        if intent.receive_token == NATIVE_BNB:
            raise Blocked('native top-up accounting needs Keith native-balance proof contract')
        side = 'BUY' if intent.pay_token == USDT else 'SELL'
        token = intent.receive_token if side == 'BUY' else intent.pay_token
        from larp.marketdata.port import TOKENS
        symbol = next((s for s, t in TOKENS.items() if t == token), None)
        if symbol is None:
            raise Blocked('unsupported settled token')
        token_delta = _net_transfers(receipt, intent.wallet, token)
        cash_delta = _net_transfers(receipt, intent.wallet, USDT)
        pay, received = (-cash_delta, token_delta) if side == 'BUY' else (-token_delta, cash_delta)
        if pay != intent.amount or received < intent.minimum_output:
            raise Blocked('actual transfers violate exact input or minimum receive')
        cash_raw = -cash_delta if side == 'BUY' else cash_delta
        if cash_raw <= 0 or cash_raw % 10**12:
            raise Blocked('actual cash cannot be represented exactly in accounting scale')
        # All wallet cash transfers, including any route fees, are netted above.
        # No separately assumed quote fee is booked a second time.
        result.update(symbol=symbol, side=side, token_units=abs(token_delta), cash_units=cash_raw // 10**12,
                      fee_units=0, fee_convention='ALL_USDT_TRANSFERS_INCLUDED_IN_NET_CASH',
                      actual_cash_chain_units=cash_raw)
    return result

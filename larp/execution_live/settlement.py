"""Canonical receipt facts for I4. Quotes and broadcasts never imply a fill."""
from datetime import datetime, timezone
from fractions import Fraction
import re

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


def final_observation(state, attempt, proof, *, wallet_id, bnb_price_units, observed_at, bnb_decimals=18):
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
    if type(bnb_decimals) is not int or not 0 <= bnb_decimals <= 18:
        raise Blocked('explicit BNB accounting scale required')
    factor = 10**(18 - bnb_decimals)
    if gas % factor:
        raise Blocked('actual gas cannot be represented exactly in accounting scale')
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
                  gas_bnb_units=gas // factor, gas_value_units=-(-gas_value.numerator // gas_value.denominator),
                  intent_terminal=kind in ('FILL', 'REVERT'), round_terminal=False,
                  step=attempt.step.lower(), block_hash=proof['block_hash'], canonical=True,
                  receipt=dict(tx_hash=attempt.tx_hash, block_hash=proof['block_hash'],
                               block_number=proof['block_number'], canonical=True,
                               finality='FINAL', chain_id=56, status=status),
                  receipt_evidence=dict(block_hash=proof['block_hash'], block_number=proof['block_number'],
                                        finalized_height=proof['finalized_height'], canonical=True,
                                        gas_used=gas_used, effective_gas_price=gas_price,
                                        gas_chain_units=gas, bnb_decimals=bnb_decimals))
    if kind == 'FILL':
        if intent.receive_token == NATIVE_BNB:
            native = proof.get('native_balance')
            if (intent.kind != 'GAS_TOP_UP' or intent.pay_token != USDT or type(native) is not dict
                    or native.get('schema') != 'TransactionNativeBalance.v1'
                    or native.get('method') != 'GETH_PRESTATE_DIFF'
                    or type(native.get('source_id')) is not str or not native['source_id']
                    or native.get('tx_hash') != attempt.tx_hash or native.get('block_hash') != proof['block_hash']
                    or native.get('wallet') != intent.wallet or type(native.get('nonce')) is not int
                    or native['nonce'] != payload.nonce or type(native.get('before_wei')) is not int
                    or type(native.get('after_wei')) is not int
                    or not 0 <= native['before_wei'] < 2**256 or not 0 <= native['after_wei'] < 2**256
                    or type(native.get('trace_sha256')) is not str
                    or not re.fullmatch(r'[0-9a-f]{64}', native['trace_sha256'])):
                raise Blocked('transaction-bound native balance proof required')
            received = native['after_wei'] - native['before_wei'] + gas
            cash_raw = -_net_transfers(receipt, intent.wallet, USDT)
            if (cash_raw != intent.amount or cash_raw <= 0 or cash_raw % 10**12
                    or not intent.minimum_output <= received < 2**256 or received % factor):
                raise Blocked('native fill violates exact input, minimum output or accounting scale')
            result.update(symbol='BNB', side='BUY', token_units=received // factor, cash_units=cash_raw // 10**12,
                          fee_units=0, fee_convention='ALL_USDT_TRANSFERS_INCLUDED_IN_NET_CASH',
                          actual_cash_chain_units=cash_raw, actual_native_chain_units=received,
                          native_receipt_evidence=native)
            return result
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
        if cash_raw <= 0 or (side == 'BUY' and cash_raw % 10**12):
            raise Blocked('actual cash cannot be represented exactly in accounting scale')
        # All wallet cash transfers, including any route fees, are netted above.
        # No separately assumed quote fee is booked a second time.
        result.update(symbol=symbol, side=side, token_units=abs(token_delta), cash_units=cash_raw // 10**12,
                      fee_units=0, fee_convention='ALL_USDT_TRANSFERS_INCLUDED_IN_NET_CASH',
                      actual_cash_chain_units=cash_raw)
        result['cash_dust_chain_units'] = cash_raw % 10**12
    return result


class ReceiptFacts:
    """Service callback. Finalization time is durable, so retries retain event bytes.

    The valuation callback must return the same persisted price for an attempt,
    not the current BNB price. Publishing belongs to the atomic runtime outbox.
    """
    def __init__(self, chain, *, wallet_id, valuation, registry, epoch, authority_version, round_terminal=None,
                 bnb_decimals=None):
        self.chain, self.wallet_id, self.valuation = chain, wallet_id, valuation
        self.registry = registry
        self.round_terminal = round_terminal or (lambda state: False)
        self.epoch, self.authority_version = epoch, authority_version
        self.bnb_decimals = bnb_decimals or (lambda _: 18)  # historical offline callers
        if not all(callable(getattr(registry, name, None)) for name in
                   ('lookup_observation', 'put_observation', 'check_authority')):
            raise Blocked('durable immutable receipt-fact registry required')

    def __call__(self, state, attempt):
        self.registry.check_authority(self.epoch, self.authority_version)
        if attempt.finalized_at is None:
            raise Blocked('durable finalization time required')
        existing = self.registry.lookup_observation(attempt.attempt_id + ':final')
        if existing is not None:
            if existing.get('tx_hash') != attempt.tx_hash or existing.get('intent_id') != state.intent.intent_id:
                raise Blocked('stored receipt fact conflicts with attempt')
            self.registry.check_authority(self.epoch, self.authority_version)
            return existing
        native_fill = (state.intent.receive_token == NATIVE_BNB and attempt.step == 'SWAP'
                       and attempt.state == 'FINAL_SUCCESS')
        proof = (self.chain.native_receipt(attempt.tx_hash) if native_fill else self.chain.receipt(attempt.tx_hash))
        stamp = datetime.fromtimestamp(attempt.finalized_at, timezone.utc).isoformat()
        fact = final_observation(state, attempt, proof, wallet_id=self.wallet_id,
                                 bnb_price_units=self.valuation(attempt.attempt_id), observed_at=stamp,
                                 bnb_decimals=self.bnb_decimals(attempt.attempt_id))
        fact["round_terminal"] = fact["intent_terminal"] and self.round_terminal(state)
        return self.registry.put_observation(fact, self.epoch, self.authority_version)

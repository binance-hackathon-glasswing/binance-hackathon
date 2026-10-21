"""GE-01: integer upper bounds for configured approve/swap and optional cleanup.

These are numeric coverage bounds, not route, funding or installation approval.
"""
from larp.contracts import ContractError
from larp.execution import REVOKE_TOKENS
from larp.strategy.schema import integer


def configured_envelope(config):
    cleanup = config.get('allowance_recovery', False)
    if type(cleanup) is not bool:
        raise ContractError('allowance_recovery must be a boolean')
    per_transaction = integer(config['max_gas'], 1) * integer(config['max_gas_price'], 1)
    transactions = 2 + (len(REVOKE_TOKENS) if cleanup else 0)
    return dict(max_transactions=transactions, cleanup_transactions=transactions - 2,
                transaction_limit_wei=per_transaction,
                required_action_wei=transactions * per_transaction,
                configured_action_wei=integer(config['gas_budget'], 1))


def units_to_wei_floor(units, decimals):
    """A funding cap cannot claim a fraction of a wei; refuse malformed native scales."""
    integer(decimals, 1)
    if decimals > 30:
        raise ContractError('Unsupported native scale')
    return integer(units) * 10**18 // 10**decimals


def rounded_measured_action(approve_gas, swap_gas, price_wei, numerator=5, denominator=4):
    """Round EACH transaction's gas limit up before pricing, rather than rounding a fractional pair fee."""
    integer(numerator, 1)
    integer(denominator, 1)
    if numerator < denominator:
        raise ContractError('Gas margin cannot shrink the measured limit')
    limits = [(integer(gas, 1) * numerator + denominator - 1) // denominator
              for gas in (approve_gas, swap_gas)]
    return dict(approve_gas_limit=limits[0], swap_gas_limit=limits[1],
                action_wei=sum(limits) * integer(price_wei, 1))

"""IDEA-055 (#36): the wallet's balances at one finalized block, read-only.

The kit's `token-balances-by-address` answer has no block identity, so a comparison against the ledger could not tell
an old read from a missed receipt. This reads the manifested RPC instead: the finalized block, then every balance at
that numeric block, then the block again (same hash), then the nonces. `rpc` is `chain.Rpc`, whose allowlist admits
only the two ERC-20 views used here (`chain.balance_call`).
"""

from datetime import datetime, timezone
import re

from larp.execution import USDT, Blocked, DependencyUnavailable
from larp.execution_live.chain import BALANCE_OF_CALL, DECIMALS_CALL, hash_value, quantity

ADDRESS = re.compile(r'0x[0-9a-f]{40}')


def assets():
    """The pinned contracts: USDT and the five bStocks. BNB is native."""
    from larp.marketdata.port import TOKENS
    return {'USDT': USDT, **TOKENS}


class DecimalsCache:
    """Per-process cache of each pinned token's `decimals()` (#96). A value is reused only after two consecutive reads
    agree, so one bad RPC answer is never kept for the life of the process (restarts are automatic only, F-124)."""

    def __init__(self):
        self.confirmed, self.last = {}, {}

    def get(self, name):
        return self.confirmed.get(name)

    def seen(self, name, value):
        if self.last.get(name) == value:
            self.confirmed[name] = value
        self.last[name] = value


def word(value):
    """One ABI-encoded uint256 return value."""
    if type(value) is not str or not re.fullmatch(r'0x[0-9a-fA-F]{64}', value):
        raise Blocked('invalid ABI word')
    return int(value, 16)


def read_balances(rpc, *, wallet, observed_at, decimals=None):
    """ChainBalances.v1 for `wallet`; raises Blocked (or the RPC's DependencyUnavailable) instead of guessing.

    `decimals`, if given, is the caller's `DecimalsCache` (#96). The value is a constant of the contract, so once two
    reads agree it is reused: each later read makes six fewer RPC calls, and archives six fewer observations.
    """
    wallet = str(wallet).lower()
    if not ADDRESS.fullmatch(wallet):
        raise Blocked('public wallet address required')
    if quantity(rpc.call('eth_chainId', [])) != 56:
        raise Blocked('wrong RPC chain')
    finalized = rpc.call('eth_getBlockByNumber', ['finalized', False])
    height, block_hash = quantity(finalized['number']), hash_value(finalized['hash'])
    tag = hex(height)
    native = quantity(rpc.call('eth_getBalance', [wallet, tag]))
    tokens = {}
    for name, contract in assets().items():
        places = decimals.get(name) if decimals is not None else None
        if places is None:
            places = word(rpc.call('eth_call', [dict(to=contract, data=DECIMALS_CALL), tag]))
            if places > 77:
                raise Blocked('implausible token decimals')
            if decimals is not None:
                decimals.seen(name, places)
        units = word(rpc.call('eth_call', [dict(to=contract, data=BALANCE_OF_CALL + '0' * 24 + wallet[2:]), tag]))
        tokens[name] = dict(contract=contract, decimals=places, units=units)
    again = rpc.call('eth_getBlockByNumber', [tag, False])
    if quantity(again['number']) != height or hash_value(again['hash']) != block_hash:
        raise Blocked('finalized block identity changed')
    latest = quantity(rpc.call('eth_getTransactionCount', [wallet, 'latest']))
    pending = quantity(rpc.call('eth_getTransactionCount', [wallet, 'pending']))
    return dict(schema='ChainBalances.v1', chain_id=56, wallet=wallet, block_number=height, block_hash=block_hash,
                native_wei=native, tokens=tokens, latest_nonce=latest, pending_nonce=pending, observed_at=observed_at)


class BalanceProviders:
    """The balance check's reader over an ordered list of RPC providers, primary first (IDEA-055 D5, PR 5).

    Each call tries the providers in order with a whole `read_balances`, so one observation never mixes providers (its
    block identity is re-checked per provider). A provider that is unavailable or gives a rejected or malformed answer is skipped
    for this call. The observation names the `source_id` that served it. The call fails only when every provider
    failed: DependencyUnavailable if every failure was unavailability, Blocked otherwise.
    `min_block`, when supplied, is a callback returning the current settled-block floor; a provider below it is
    skipped before its observation can be returned, so a stuck primary cannot suppress a healthy backup. The next call starts again
    at the primary. One DecimalsCache serves all providers: decimals are a constant of each contract."""

    def __init__(self, providers, *, wallet, decimals=None, min_block=None):
        if not providers or any(not getattr(p, 'source_id', None) for p in providers):
            raise Blocked('at least one named balance RPC provider required')
        self.providers, self.wallet, self.decimals = list(providers), wallet, decimals
        self.min_block = min_block or (lambda: None)

    def __call__(self, now_ms):
        observed = datetime.fromtimestamp(now_ms / 1000, timezone.utc).isoformat()
        floor = self.min_block()
        if floor is not None and (type(floor) is not int or floor < 0):
            raise Blocked('invalid settled-block floor')
        failures = []
        for rpc in self.providers:
            try:
                o = read_balances(rpc, wallet=self.wallet, observed_at=observed, decimals=self.decimals)
                if floor is not None and o['block_number'] < floor:
                    raise Blocked('balance RPC is behind the settled ledger block')
            except DependencyUnavailable as error:
                failures.append(error)
                continue
            except (Blocked, KeyError, TypeError, ValueError) as error:  # a rejected or malformed answer
                failures.append(Blocked(str(error) or type(error).__name__))
                continue
            return dict(o, source_id=rpc.source_id)
        if all(isinstance(e, DependencyUnavailable) for e in failures):
            raise DependencyUnavailable('every balance RPC provider is unavailable')
        raise Blocked('no balance RPC provider gave a valid observation')

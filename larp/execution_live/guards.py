"""Current run facts plus actual venue status/nonce. Facts never default true.

Guards run at every execution step, so they read the market's open state only (WR11, #53): the bStock list (token
`openState`) and the underlying market's `openState`, with no price or cost quotes. One observation is reused across
the steps of an attempt while it is fresher than `market_freshness_s` and belongs to the same round; after that, or
in a new round, both are read again. The wallet nonce is read fresh at every step.
"""
from larp.execution import Blocked, Conflict, StateVersionConflict, Gates, integer
from larp.marketdata.port import TOKENS
from larp.marketdata.web3 import Unavailable, single

MAX_FRESHNESS_S = 30


class LiveGuards:
    mode = 'live'

    def __init__(self, *, store, market, chain, authorization, market_freshness_s=10):
        if any(getattr(p, 'mode', None) != 'live' for p in (market, chain)) or not callable(authorization):
            raise Blocked('real market/chain and authorization ports required')
        if type(market_freshness_s) is not int or not 0 < market_freshness_s <= MAX_FRESHNESS_S:
            raise Blocked('market freshness window must be 1-30 seconds')
        self.store, self.market, self.chain, self.authorization = store, market, chain, authorization
        self.freshness = market_freshness_s
        self._round = None  # (round_id, observed_at, metadata, {symbol: (token_open, underlying_open)})

    def _open_state(self, intent, now):
        """(token_open, underlying_open) for the intent's bStock, observed within the freshness window."""
        cached = self._round
        if cached is None or cached[0] != intent.round_id or not 0 <= now - cached[1] < self.freshness:
            cached = self._round = (intent.round_id, now, self.market.metadata(), {})
        _, _, metadata, open_state = cached
        symbol = next((s for s, (row, _) in metadata.items()
                       if row['tokenContractAddress'].lower() in (intent.pay_token, intent.receive_token)), None)
        if symbol is None:
            raise Blocked('missing eligible market identity')
        if symbol not in open_state:
            row = metadata[symbol][0]
            underlying = single(self.market.call('market/rwa/underlying-market',
                                                 {'tokenContractAddress': TOKENS[symbol]}))
            if str(underlying.get('tokenContractAddress', '')).lower() != TOKENS[symbol]:
                raise Unavailable('underlying identity mismatch')
            open_state[symbol] = ((row.get('statusInfo') or {}).get('openState') is True,
                                  (underlying.get('statusInfo') or {}).get('openState') is True)
        return open_state[symbol]

    def snapshot(self, intent, now):
        original_authority = self.store.execution_authority()
        # Gas top-ups have no stock market; the authorization source must explicitly
        # authorize the native resource route. No unconditional market-open default.
        if intent.kind == 'GAS_TOP_UP':
            token_open = underlying_open = False
        else:
            try:
                token_open, underlying_open = self._open_state(intent, now)
            except (Blocked, Unavailable, KeyError, TypeError, ValueError, AttributeError):
                self._round = None  # a failed observation is never reused
                token_open = underlying_open = False
        try:
            nonce = self.chain.nonce(intent.wallet)
        except Blocked:
            nonce = None  # Missing signing evidence must not prevent receipt reconciliation.
        # External observations precede the journal fence. Authorization must describe
        # one stable version, with no market/RPC operation left before returning it.
        epoch, state_version = self.store.authority()
        owner_epoch, execution_version = self.store.execution_authority()
        if epoch != owner_epoch or original_authority != (owner_epoch, execution_version):
            raise Conflict('ownership changed while acquiring guards')
        facts = self.authorization(intent, epoch, state_version, now)
        if intent.kind == 'GAS_TOP_UP':
            token_open = underlying_open = facts.get('native_resource_route_valid') is True
        if self.store.execution_authority() != (owner_epoch, execution_version):
            raise Conflict('ownership changed while authorizing guards')
        if self.store.authority() != (epoch, state_version):
            raise StateVersionConflict('execution facts changed while acquiring guards')
        return Gates(epoch, state_version, nonce, now,
                     integer(facts['expires_at'], positive=True),
                     **{k: facts.get(k) is True for k in ('audit_durable', 'reservation_valid', 'version_valid',
                                                        'risk_valid', 'health_valid', 'clock_trusted')},
                     token_market_open=token_open, underlying_market_open=underlying_open,
                     execution_version=execution_version)

"""Current run facts plus actual venue status/nonce. Facts never default true."""
from larp.execution import Blocked, Gates, integer


class LiveGuards:
    mode = 'live'

    def __init__(self, *, store, market, chain, authorization):
        if any(getattr(p, 'mode', None) != 'live' for p in (market, chain)) or not callable(authorization):
            raise Blocked('real market/chain and authorization ports required')
        self.store, self.market, self.chain, self.authorization = store, market, chain, authorization

    def snapshot(self, intent, now):
        epoch, state_version = self.store.authority()
        owner_epoch, execution_version = self.store.execution_authority()
        if epoch != owner_epoch:
            raise Blocked('ownership changed while acquiring guards')
        facts = self.authorization(intent, epoch, state_version, now)
        # Gas top-ups have no stock market; the authorization source must explicitly
        # authorize the native resource route. No unconditional market-open default.
        if intent.kind == 'GAS_TOP_UP':
            token_open = underlying_open = facts.get('native_resource_route_valid') is True
        else:
            metadata = self.market.metadata()
            symbol = next((s for s, (row, _) in metadata.items()
                           if row['tokenContractAddress'].lower() in (intent.pay_token, intent.receive_token)), None)
            if symbol is None:
                raise Blocked('missing eligible market identity')
            observation = self.market.observation(symbol, metadata[symbol])
            token_open, underlying_open = observation['token_open'], observation['underlying_open']
        return Gates(epoch, state_version, self.chain.nonce(intent.wallet), now,
                     integer(facts['expires_at'], positive=True),
                     **{k: facts.get(k) is True for k in ('audit_durable', 'reservation_valid', 'version_valid',
                                                        'risk_valid', 'health_valid', 'clock_trusted')},
                     token_market_open=token_open, underlying_market_open=underlying_open,
                     execution_version=execution_version)

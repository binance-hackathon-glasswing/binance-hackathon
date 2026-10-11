"""Live observation producer. Unknown route/gas/fee evidence never becomes execution authority."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import re

from larp.execution import USDT
from .web3 import Unavailable, data, encoded, single

TOKENS = dict(NVDAB='0x02fca66c1d1afb4e2a7884261eb00f63598a7436',
 GOOGLB='0x3f53de71c126bdabae20f9cd64848d317f6c3238', SKHYB='0xca750ef65f295bbecd685abf54e82caf297bdb61',
 TSLAB='0x5b1910eaad6450e50f816082aa078c41f10c292f', MSFTB='0x80106cb3ead06659a5ad19df39d9b4733863b9b0')
NATIVE = '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'


def number(v):
    try:
        n = Decimal(str(v))
    except InvalidOperation:
        raise Unavailable('invalid numeric observation') from None
    if not n.is_finite() or n < 0:
        raise Unavailable('invalid numeric observation')
    return n


def units(v, decimals):
    with localcontext() as context:
        context.prec = 100
        n = number(v) * 10 ** decimals
    if n != n.to_integral_value():
        raise Unavailable('nonintegral asset units')
    return int(n)


def integer(v):
    if not re.fullmatch(r'0|[1-9][0-9]*', str(v)):
        raise Unavailable('invalid integer observation')
    return int(v)


class MarketPort:
    mode = 'live'

    def __init__(self, client, wallet, *, basis_verifier=None):
        if not re.fullmatch(r'0x[0-9a-fA-F]{40}', wallet or ''):
            raise Unavailable('public wallet address required')
        self.client, self.wallet = client, wallet.lower()
        self.basis_verifier = basis_verifier

    def call(self, endpoint, params=None, method='GET'):
        return self.client.request(method, endpoint, {'binanceChainId': '56', **(params or {})})

    def metadata(self):
        r = self.call('market/rwa/tokens', {'platformId': 'bstock'})
        rows = data(r)
        if not isinstance(rows, list):
            raise Unavailable('token metadata must be a list')
        result = {}
        for symbol, token in TOKENS.items():
            found = [x for x in rows if str(x.get('tokenContractAddress', '')).lower() == token]
            if len(found) != 1:
                raise Unavailable('missing/duplicate eligible token')
            row = found[0]
            if row.get('tokenSymbol') != symbol or str(row.get('binanceChainId')) != '56':
                raise Unavailable('token identity mismatch')
            decimals = integer(row['decimals'])
            if decimals > 30:
                raise Unavailable('unsupported token decimals')
            result[symbol] = (row, r)
        return result

    def observation(self, symbol, entry):
        row, metadata = entry
        r = self.call('market/rwa/underlying-market', {'tokenContractAddress': TOKENS[symbol]})
        underlying = single(r)
        if str(underlying.get('tokenContractAddress', '')).lower() != TOKENS[symbol]:
            raise Unavailable('underlying identity mismatch')
        stamp = max(metadata['available_at'], r['available_at'])
        basis = bool(self.basis_verifier and self.basis_verifier(row, underlying) is True)
        price = int(number(row['tokenPrice']) * 1000000)
        if price <= 0 or not row.get('underlyingTicker'):
            raise Unavailable('missing positive price/underlying identity')
        return dict(schema='MarketObservation.v1', symbol=symbol, underlying_id=row['underlyingTicker'],
                    token_id=TOKENS[symbol], decimals=integer(row['decimals']), currency='USDT', money_scale=1000000,
                    price_units=price, source_id='BINANCE_WEB3', content_hash=hashlib.sha256(encoded(
                        [metadata['artifact_sha256'], r['artifact_sha256']])).hexdigest(), quality='VALID',
                    observed_at=stamp, available_at=stamp, close_at=stamp,
                    token_open=row.get('statusInfo', {}).get('openState') is True,
                    underlying_open=underlying.get('statusInfo', {}).get('openState') is True,
                    basis_verified=basis, quotes=[], observation_hashes=[metadata['artifact_sha256'], r['artifact_sha256']])

    def __call__(self, now_ms):
        # Caller establishes its decision cutoff after this I/O. No observation is backdated to now_ms.
        metadata = self.metadata()
        return [self.observation(s, metadata[s]) for s in TOKENS]

    def quote(self, symbol, side, pay_units, decimals, slippage='0.5'):
        if symbol not in TOKENS or side not in ('BUY', 'SELL') or type(pay_units) is not int or pay_units <= 0:
            raise Unavailable('invalid quote request')
        pay, receive = (USDT, TOKENS[symbol]) if side == 'BUY' else (TOKENS[symbol], USDT)
        return self.call('aggregator/quote-and-swap', dict(amount=str(pay_units), fromTokenAddress=pay,
                        toTokenAddress=receive, userWalletAddress=self.wallet, vendor='LiquidMesh', slippagePercent=slippage))

    def observe(self, request):
        if hasattr(request, 'read'):
            request = request.read()
        if request.get('schema') != 'MarketRequest.v1' or request.get('amount_kind') != 'EXACT_IN':
            raise Unavailable('unsupported market request')
        symbol, side = request['symbol'], request['side']
        if symbol not in TOKENS or side not in ('BUY', 'SELL'):
            raise Unavailable('unsupported market entity')
        metadata = self.metadata()
        observation = self.observation(symbol, metadata[symbol])
        expected_asset = 'USDT' if side == 'BUY' else symbol
        scale = 6 if side == 'BUY' else observation['decimals']
        if request.get('pay_asset') != expected_asset or request.get('pay_decimals') != scale:
            raise Unavailable('pay asset/scale mismatch')
        amount = integer(request['pay_units'])
        if amount <= 0:
            raise Unavailable('positive request amount required')
        # Chain USDT has 18 decimals (kit); bind this again against the quote's token metadata.
        raw = self.quote(symbol, side, amount * 10**12 if side == 'BUY' else amount, observation['decimals'])
        q = single(raw); rr = q.get('routerResult', {}); tx = q.get('tx', {})
        pay, receive = (USDT, TOKENS[symbol]) if side == 'BUY' else (TOKENS[symbol], USDT)
        if (str(rr.get('fromToken', {}).get('tokenContractAddress', '')).lower() != pay
                or str(rr.get('toToken', {}).get('tokenContractAddress', '')).lower() != receive
                or integer(rr['fromToken']['decimal']) != (18 if side == 'BUY' else observation['decimals'])
                or integer(rr['toToken']['decimal']) != (observation['decimals'] if side == 'BUY' else 18)
                or integer(rr['fromTokenAmount']) != (amount * 10**12 if side == 'BUY' else amount)):
            raise Unavailable('quote token/amount binding failed')
        # ABI, encoded deadline, exact post-approval gas and fee denomination are still unproved.
        # Preserve measurements, but expose no executable quote until the live venue proves them.
        observation.update(quote_status='CAPABILITY_PROOF_REQUIRED', quotes=[], quote_measurement=dict(
            artifact_sha256=raw['artifact_sha256'], pay_units=amount, pay_asset=expected_asset,
            receive_units=integer(rr['toTokenAmount']), receive_decimals=integer(rr['toToken']['decimal']),
            impact_bps=str(number(rr['priceImpactPercent']) * 100), fee_amount=rr.get('feeAmount'),
            trade_fee=rr.get('tradeFee'), vendor=rr.get('vendorName'), router=tx.get('to'),
            minimum_receive_raw=tx.get('minReceiveAmount'), quoted_gas=tx.get('gas'), available_at=raw['available_at']))
        observation['quote_measurement']['unsigned_transaction'] = tx
        stamp = max(observation['available_at'], raw['available_at'])
        observation.update(observed_at=stamp, available_at=stamp, close_at=stamp,
                           content_hash=hashlib.sha256(encoded([observation['content_hash'], raw['artifact_sha256']])).hexdigest())
        return observation

    def candles(self, symbol, *, bar='1m', limit=100):
        if symbol not in TOKENS or bar not in ('1m', '5m', '15m', '1h', '4h', '1d') or type(limit) is not int or not 1 <= limit <= 1000:
            raise Unavailable('invalid candle request')
        r = self.call('market/candles', dict(tokenContractAddress=TOKENS[symbol], bar=bar, limit=limit))
        return dict(schema='RawTokenCandles.v1', symbol=symbol, token_id=TOKENS[symbol], bar=bar,
                    rows=data(r), available_at=r['available_at'], content_hash=r['artifact_sha256'],
                    timestamp_semantics='KIT_TIMESTAMP_MS; consumer must establish open/close semantics')

    def balances(self):
        r = self.client.request('POST', 'balance/token-balances-by-address', dict(address=self.wallet,
            tokenContractAddresses=[dict(binanceChainId='56', tokenContractAddress=t) for t in ('', USDT, *TOKENS.values())]))
        return r

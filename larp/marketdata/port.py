"""Live observation producer. Unknown route/gas/fee evidence never becomes execution authority."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from functools import wraps
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
    n = int(v)
    if n >= 2**256:
        raise Unavailable('quantity exceeds uint256')
    return n


def slippage_percent(bps):
    """An independently accepted integer bp limit, expressed as an API percent."""
    if type(bps) is not int or not 0 <= bps < 10000:
        raise Unavailable('invalid independent slippage limit')
    value = format(Decimal(bps) / 100, 'f')
    return value.rstrip('0').rstrip('.') if '.' in value else value


def observation_boundary(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError, InvalidOperation):
            raise Unavailable('market response schema rejected') from None
    return wrapped


class MarketPort:
    mode = 'live'

    def __init__(self, client, wallet, *, basis_verifier=None, quote_verifier=None, quote_limits=None, cost_observation=None):
        if not re.fullmatch(r'0x[0-9a-fA-F]{40}', wallet or ''):
            raise Unavailable('public wallet address required')
        self.client, self.wallet = client, wallet.lower()
        self.basis_verifier = basis_verifier
        self.quote_verifier = quote_verifier
        self.quote_limits = quote_limits
        self.cost_observation = cost_observation

    def call(self, endpoint, params=None, method='GET'):
        return self.client.request(method, endpoint, {'binanceChainId': '56', **(params or {})})

    @observation_boundary
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

    @observation_boundary
    def observation(self, symbol, entry):
        row, metadata = entry
        r = self.call('market/rwa/underlying-market', {'tokenContractAddress': TOKENS[symbol]})
        underlying = single(r)
        if str(underlying.get('tokenContractAddress', '')).lower() != TOKENS[symbol]:
            raise Unavailable('underlying identity mismatch')
        prices = self.call('market/rwa/price', {'tokenContractAddresses': TOKENS[symbol]})
        price_row = single(prices)
        if str(price_row.get('tokenContractAddress', '')).lower() != TOKENS[symbol]:
            raise Unavailable('price token identity mismatch')
        stamp = min(metadata['available_at'], r['available_at'], prices['available_at'])
        available = max(metadata['available_at'], r['available_at'], prices['available_at'])
        basis = bool(self.basis_verifier and self.basis_verifier(row, underlying) is True)
        price = int(number(price_row['tokenPrice']) * 1000000)
        if price <= 0 or not row.get('underlyingTicker'):
            raise Unavailable('missing positive price/underlying identity')
        result = dict(schema='MarketObservation.v1', origin='WEB3_OPEN_API', symbol=symbol, underlying_id=row['underlyingTicker'],
                    token_id=TOKENS[symbol], decimals=integer(row['decimals']), currency='USDT', money_scale=1000000,
                    price_units=price, source_id='BINANCE_WEB3', content_hash=hashlib.sha256(encoded(
                        [metadata['artifact_sha256'], r['artifact_sha256'], prices['artifact_sha256']])).hexdigest(), quality='VALID',
                    observed_at=stamp, available_at=available, close_at=stamp,
                    token_open=row.get('statusInfo', {}).get('openState') is True,
                    underlying_open=underlying.get('statusInfo', {}).get('openState') is True,
                    basis_verified=basis, quotes=[], observation_hashes=[metadata['artifact_sha256'], r['artifact_sha256'], prices['artifact_sha256']],
                    token_status=row.get('statusInfo'), underlying_status=underlying.get('statusInfo'))
        result.update(measured_roundtrip_bps=None, cost_status='UNAVAILABLE')
        try:
            cost = (self.cost_observation(symbol) if self.cost_observation is not None
                    else self.measure_cost(symbol, result['decimals']))
        except Unavailable as error:
            if str(error) in ('authentication_error', 'compliance_restriction',
                              'http_forbidden_unclassified', 'rate_limited'):
                raise
            cost = None
        if cost is not None:
            if (cost.get('symbol') != symbol or cost.get('origin') != 'WEB3_OPEN_API'
                    or not re.fullmatch('[0-9a-f]{64}', cost.get('content_hash', ''))
                    or not cost.get('available_at') or not cost.get('observed_at')):
                raise Unavailable('cost measurement identity/provenance rejected')
            result.update(measured_roundtrip_bps=integer(cost['measured_roundtrip_bps']),
                          cost_status='MEASURED', cost_observation=cost,
                          available_at=max(available, cost['available_at']),
                          observed_at=min(stamp, cost['observed_at']), close_at=min(stamp, cost['observed_at']),
                          content_hash=hashlib.sha256(encoded([result['content_hash'], cost['content_hash']])).hexdigest())
        return result

    def measure_cost(self, symbol, decimals, *, cash_units=40000000):
        """Sequential EXACT_IN quote cost proxy; retains signed price-movement noise.

        Negative measured net cost receives no cost credit in the planner. This
        is a current sampled proxy, not the multi-day spread/impact calibration.
        """
        def receive(raw, pay, recv, amount, pay_decimals, recv_decimals):
            rr = single(raw)['routerResult']
            if (str(rr['fromToken']['tokenContractAddress']).lower() != pay
                    or str(rr['toToken']['tokenContractAddress']).lower() != recv
                    or integer(rr['fromToken']['decimal']) != pay_decimals
                    or integer(rr['toToken']['decimal']) != recv_decimals
                    or integer(rr['fromTokenAmount']) != amount):
                raise Unavailable('cost quote economic binding failed')
            result = integer(rr['toTokenAmount'])
            if result <= 0:raise Unavailable('cost quote has no receive amount')
            return result
        try:
            pay = cash_units * 10**12
            buy = self.quote(symbol, 'BUY', pay, decimals)
            quantity = receive(buy, USDT, TOKENS[symbol], pay, 18, decimals)
            sell = self.quote(symbol, 'SELL', quantity, decimals)
            proceeds = receive(sell, TOKENS[symbol], USDT, quantity, decimals, 18)
            with localcontext() as context:
                context.prec = 100
                signed = Decimal(pay - proceeds) * 10000 / pay
            return dict(symbol=symbol, origin='WEB3_OPEN_API',
                        measured_roundtrip_bps=max(0, int(signed.to_integral_value(rounding='ROUND_CEILING'))),
                        signed_roundtrip_bps=str(signed), pay_units=cash_units,
                        measurement='SEQUENTIAL_EFFECTIVE_QUOTE_COST; no negative-cost credit',
                        observed_at=buy['available_at'], available_at=sell['available_at'],
                        content_hash=hashlib.sha256(encoded([buy['artifact_sha256'], sell['artifact_sha256']])).hexdigest())
        except (KeyError, TypeError, ValueError):
            raise Unavailable('cost response schema rejected') from None

    def __call__(self, now_ms):
        # Caller establishes its decision cutoff after this I/O. No observation is backdated to now_ms.
        metadata = self.metadata()
        return [self.observation(s, metadata[s]) for s in TOKENS]

    def quote(self, symbol, side, pay_units, decimals, slippage=None):
        if symbol not in TOKENS or side not in ('BUY', 'SELL') or type(pay_units) is not int or pay_units <= 0:
            raise Unavailable('invalid quote request')
        if self.quote_limits is not None:
            configured = slippage_percent(self.quote_limits.get('slippage_bps'))
            if slippage is not None and number(slippage) > number(configured):
                raise Unavailable('quote cannot widen independent slippage limit')
            slippage = configured if slippage is None else str(slippage)
        elif slippage is None:
            slippage = '0.5'  # Unqualified read-only measurements retain the legacy sampling setting.
        pay, receive = (USDT, TOKENS[symbol]) if side == 'BUY' else (TOKENS[symbol], USDT)
        return self.call('aggregator/quote-and-swap', dict(amount=str(pay_units), fromTokenAddress=pay,
                        toTokenAddress=receive, userWalletAddress=self.wallet, vendor='LiquidMesh', slippagePercent=slippage))

    @observation_boundary
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
        observation['quote_measurement']['elapsed_ms'] = raw.get('elapsed_ms')
        observation['quote_measurement']['unsigned_transaction'] = tx
        stamp = max(observation['available_at'], raw['available_at'])
        observation.update(available_at=stamp,
                           content_hash=hashlib.sha256(encoded([observation['content_hash'], raw['artifact_sha256']])).hexdigest())
        if self.quote_verifier is not None:
            proof = self.quote_verifier(raw, request, observation)
            if proof is not None:
                self._executable_quote(observation, request, raw, proof)
        return observation

    def _executable_quote(self, observation, request, raw, proof):
        from larp.risk.planner import _quote_at_cap
        from larp.execution import Payload, SwapEconomics
        q = single(raw)
        rr, tx = q['routerResult'], q['tx']
        if proof.get('source_hash') != raw['artifact_sha256']:
            raise Unavailable('quote proof is not bound to response bytes')
        decoded, payload = proof.get('economics'), proof.get('payload')
        if not isinstance(decoded, SwapEconomics) or not isinstance(payload, Payload):
            raise Unavailable('verified payload and decoded economics required')
        side = request['side']
        pay, receive = (USDT, observation['token_id']) if side == 'BUY' else (observation['token_id'], USDT)
        amount = request['pay_units'] * (10**12 if side == 'BUY' else 1)
        if (payload.chain_id != 56 or payload.sender != self.wallet or payload.data != tx['data']
                or payload.to != str(tx['to']).lower() or payload.value != integer(tx['value'])
                or decoded.pay_token != pay or decoded.receive_token != receive
                or decoded.amount != amount or decoded.recipient != self.wallet
                or decoded.minimum_output != integer(tx['minReceiveAmount'])
                or decoded.native_value != payload.value or proof.get('route_valid') is not True):
            raise Unavailable('decoded route does not bind quote economics')
        received = integer(rr['toTokenAmount'])
        cash = request['pay_units'] if side == 'BUY' else received // 10**12
        minimum = decoded.minimum_output if side == 'BUY' else decoded.minimum_output // 10**12
        impact = number(rr['priceImpactPercent']) * 100
        quote = dict(origin='WEB3_OPEN_API', amount_kind='EXACT_IN', side=side, pay_asset=request['pay_asset'],
                     pay_units=request['pay_units'], token_units=received if side == 'BUY' else amount,
                     cash_units=cash, min_receive_units=minimum,
                     fee_units=integer(proof['fee_units']), gas_bnb_units=integer(proof['gas_bnb_units']),
                     slippage_bps=integer(proof['slippage_bps']), impact_bps=int(impact.to_integral_value(rounding='ROUND_CEILING')),
                     route_valid=True, quote_id=raw['artifact_sha256'], observed_at=raw['available_at'],
                     available_at=raw['available_at'], expires_at=datetime.fromtimestamp(decoded.deadline, timezone.utc).isoformat())
        if quote['gas_bnb_units'] <= 0 or proof.get('exact_gas_verified') is not True:
            raise Unavailable('exact payload gas evidence required')
        now = datetime.fromisoformat(raw['available_at'].replace('Z', '+00:00'))
        if self.quote_limits is None:
            raise Unavailable('independent policy quote limits required')
        test = _quote_at_cap(dict(observation, quotes=[quote]), side, request['pay_units'],
                            self.quote_limits,
                            now, quote['token_units'])
        if test[0] is None:
            raise Unavailable('quote fails consumer validator')
        observation.update(quotes=[quote], quote_status='VERIFIED_EXECUTABLE')

    def session_candles(self, symbol, *, entity_id, timestamp_kind, timestamp_evidence_hash,
                        token_adjustment_version, bar='1h', limit=300):
        if (timestamp_kind != 'OPEN' or not entity_id or not token_adjustment_version
                or not re.fullmatch('[0-9a-f]{64}', timestamp_evidence_hash or '')):
            raise Unavailable('verified candle semantics/adjustment provenance required')
        raw = self.candles(symbol, bar=bar, limit=limit)
        seconds = {'1m':60, '5m':300, '15m':900, '1h':3600, '4h':14400, '1d':86400}[bar]
        return dict(schema='TokenCandles.v1', origin='WEB3_OPEN_API', symbol=symbol,
                    token_id=TOKENS[symbol], entity_id=entity_id, source_id='BINANCE_WEB3',
                    candles=raw['rows'], bar_seconds=seconds, timestamp_kind=timestamp_kind,
                    timestamp_evidence_hash=timestamp_evidence_hash,
                    token_adjustment_version=token_adjustment_version,
                    available_at=raw['available_at'], content_hash=raw['content_hash'])

    @observation_boundary
    def candles(self, symbol, *, bar='1m', limit=100):
        if symbol not in TOKENS or bar not in ('1m', '5m', '15m', '1h', '4h', '1d') or type(limit) is not int or not 1 <= limit <= 300:
            raise Unavailable('invalid candle request')
        r = self.call('market/candles', dict(tokenContractAddress=TOKENS[symbol], bar=bar, limit=limit))
        rows = data(r)
        if not isinstance(rows, list):
            raise Unavailable('candles must be a list')
        stamps = []
        previous = -1
        for row in rows:
            if not isinstance(row, list) or len(row) < 7:
                raise Unavailable('invalid raw candle row')
            timestamp = integer(row[5])
            if timestamp <= previous:
                raise Unavailable('candle timestamps are not strictly ascending')
            previous = timestamp
            stamps.append(dict(reported_at=datetime.fromtimestamp(timestamp / 1000, timezone.utc).isoformat(),
                               open_at=None, close_at=None))
        return dict(schema='RawTokenCandles.v1', symbol=symbol, token_id=TOKENS[symbol], bar=bar,
                    rows=rows, timestamps=stamps, available_at=r['available_at'], content_hash=r['artifact_sha256'],
                    timestamp_semantics='KIT_TIMESTAMP_MS; consumer must establish open/close semantics')

    def balances(self):
        r = self.client.request('POST', 'balance/token-balances-by-address', dict(address=self.wallet,
            tokenContractAddresses=[dict(binanceChainId='56', tokenContractAddress=t) for t in ('', USDT, *TOKENS.values())]))
        return r


class NativeGasQuotePort:
    """USDT -> native BNB quote input for the existing resource planner.

    An injected verifier must establish route bytes, exact gas and fee units.
    The port provides no signer, broadcaster, receipt/trace proof or driver wiring.
    Missing proof yields no execution authority; timestamps are never backdated.
    """
    mode = 'live'

    def __init__(self, client, wallet, *, quote_limits, pay_units, receive_decimals,
                 quote_verifier=None):
        if not re.fullmatch(r'0x[0-9a-fA-F]{40}', wallet or ''):
            raise Unavailable('public wallet address required')
        if type(pay_units) is not int or pay_units <= 0:
            raise Unavailable('positive gas quote cash amount required')
        if type(receive_decimals) is not int or not 0 <= receive_decimals <= 18:
            raise Unavailable('unsupported native accounting scale')
        self.client, self.wallet = client, wallet.lower()
        self.limits = dict(quote_limits)
        self.slippage = slippage_percent(self.limits.get('slippage_bps'))
        self.pay_units, self.receive_decimals = integer(pay_units), receive_decimals
        self.verifier = quote_verifier

    @observation_boundary
    def __call__(self, now_ms):
        from larp.execution import Payload, SwapEconomics
        amount = self.pay_units * 10**12
        integer(amount)
        request = dict(schema='MarketRequest.v1', symbol='BNB', kind='GAS_TOP_UP', side='BUY',
                       amount_kind='EXACT_IN', pay_asset='USDT', pay_units=self.pay_units, pay_decimals=6,
                       receive_decimals=self.receive_decimals)
        raw = self.client.request('GET', 'aggregator/quote-and-swap', dict(binanceChainId='56',
            amount=str(amount), fromTokenAddress=USDT, toTokenAddress=NATIVE,
            userWalletAddress=self.wallet, vendor='LiquidMesh', slippagePercent=self.slippage))
        q = single(raw); rr, tx = q['routerResult'], q['tx']
        if (q.get('executionMode') != 'SWAP' or q.get('rfq') is not None
                or rr.get('vendorName') != 'LiquidMesh'
                or str(rr['fromToken']['tokenContractAddress']).lower() != USDT
                or str(rr['toToken']['tokenContractAddress']).lower() != NATIVE
                or integer(rr['fromToken']['decimal']) != 18
                or integer(rr['toToken']['decimal']) != 18
                or integer(rr['fromTokenAmount']) != amount or integer(tx['value']) != 0):
            raise Unavailable('native quote identity/economics rejected')
        received, minimum = integer(rr['toTokenAmount']), integer(tx['minReceiveAmount'])
        if not 0 < minimum <= received or minimum < received * (10000 - self.limits['slippage_bps']) // 10000:
            raise Unavailable('native quote minimum output exceeds slippage limit')
        proof = self.verifier(raw, request) if self.verifier is not None else None
        if proof is None:
            return []
        economics, payload = proof.get('economics'), proof.get('payload')
        if (proof.get('source_hash') != raw['artifact_sha256']
                or not re.fullmatch('[0-9a-f]{64}', raw['artifact_sha256'])
                or proof.get('route_valid') is not True or proof.get('exact_gas_verified') is not True
                or not isinstance(economics, SwapEconomics) or not isinstance(payload, Payload)
                or type(payload.chain_id) is not int or payload.chain_id != 56
                or payload.sender != self.wallet or payload.to != str(tx['to']).lower()
                or payload.data != tx['data'] or payload.value != 0
                or economics.pay_token != USDT or economics.receive_token != NATIVE
                or economics.amount != amount or economics.recipient != self.wallet
                or economics.minimum_output != minimum or economics.native_value != 0):
            raise Unavailable('native quote proof is not bound to exact route bytes')
        if (not re.fullmatch(r'0x[0-9a-f]{40}', payload.to)
                or not re.fullmatch(r'0x(?:[0-9a-fA-F]{2})+', payload.data)
                or any(type(v) is not int or not 0 <= v < 2**256
                       for v in (payload.value, payload.nonce, economics.native_value, economics.deadline))
                or any(type(v) is not int or not 0 < v < 2**256 for v in (payload.gas, payload.gas_price))):
            raise Unavailable('native quote decoded payload fields rejected')
        available = datetime.fromisoformat(raw['available_at'].replace('Z', '+00:00'))
        if available.tzinfo is None:
            raise Unavailable('native quote availability must be timezone aware')
        deadline = integer(economics.deadline)
        if deadline <= available.timestamp():
            raise Unavailable('native quote expired at retrieval completion')
        # Do not silently weaken a minimum by rounding it to an accounting scale.
        factor = 10 ** (18 - self.receive_decimals)
        if received % factor or minimum % factor:
            raise Unavailable('native quote cannot be represented exactly in accounting scale')
        fee, gas = integer(proof['fee_units']), integer(proof['gas_bnb_units'])
        if gas <= 0 or (fee and (proof.get('fee_asset') != 'USDT' or proof.get('fee_decimals') != 6)):
            raise Unavailable('native quote gas/fee denomination proof required')
        if gas * factor < payload.gas * payload.gas_price:
            raise Unavailable('native quote gas allowance underreserves decoded payload')
        impact = int((number(rr['priceImpactPercent']) * 100).to_integral_value(rounding='ROUND_CEILING'))
        if (impact > self.limits['impact_bps']
                or self.pay_units + fee > self.limits['per_trade_cap_units']):
            raise Unavailable('native quote exceeds independent policy limits')
        return [dict(kind='GAS_TOP_UP', symbol='BNB', side='BUY', receive_asset='BNB',
            receive_decimals=self.receive_decimals, origin='WEB3_OPEN_API', quote_id=raw['artifact_sha256'],
            amount_kind='EXACT_IN', pay_asset='USDT', pay_units=self.pay_units, cash_units=self.pay_units,
            fee_units=fee, gas_bnb_units=gas, token_units=received // factor, min_receive_units=minimum // factor,
            route_valid=True, slippage_bps=self.limits['slippage_bps'], impact_bps=impact,
            observed_at=raw['available_at'], available_at=raw['available_at'],
            expires_at=datetime.fromtimestamp(deadline, timezone.utc).isoformat())]

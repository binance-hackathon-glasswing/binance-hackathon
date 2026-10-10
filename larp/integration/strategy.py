"""Coordinator <-> strategy/risk adapters (RT21 G1, G2).

G1 StrategyContextProvider builds Keith's StrategyContext.v1 for the coordinator's
single decision snapshot. G2 StrategyPlanner turns Keith's PlanResult into the
coordinator's executable intents and per-asset store reservations.
"""

from copy import deepcopy
from decimal import Decimal

from larp.contracts import ContractError, Document
from larp.strategy.schema import instant

DERIVED = ('assessments', 'assessment_requests')  # rebuilt from the round's request/assessment


def epoch_ms(value):
    moment = instant(value)
    return int(moment.timestamp() * 1000)


def balances(portfolio):
    """The store's per-asset resource view of Keith's PortfolioState.v1 (integer units)."""
    result = {'USDT': portfolio['cash_units'], 'BNB': portfolio['bnb_units']}
    for symbol, position in portfolio['positions'].items():
        result[symbol] = position['units']
    return result


class StrategyContextProvider:
    """Builds StrategyContext.v1 from the coordinator's state and injected sources.

    sources: markets(now_ms) -> [MarketObservation.v1 without quotes]; series(now_ms) ->
    {symbol: PriceSeries.v1}; calendar(now_ms) -> {session_index, remaining_sessions};
    health(current) -> {integrity_ok, journal_ok, ownership_ok, clock_ok};
    quotes: a Market port, observe(MarketRequest.v1) -> quote document.
    """

    MAX_QUOTE_PASSES = 3

    def __init__(self, *, profile, markets, series, calendar, health, quotes, decide, plan):
        self.profile = profile
        self.markets, self.series, self.calendar, self.health = markets, series, calendar, health
        self.quotes, self.decide, self.plan = quotes, decide, plan

    @property
    def profile_hash(self):
        return Document.from_dict(self.profile).digest('StrategyProfile.v1')

    def base(self, current, request, assessment, now_ms):
        projection = current['projection']
        calendar = self.calendar(now_ms)
        context = {
            'schema': 'StrategyContext.v1', 'origin': 'RUNTIME_PROVIDER', 'profile': deepcopy(self.profile),
            'portfolio': deepcopy(projection['portfolio']), 'markets': self.markets(now_ms),
            'series': self.series(now_ms), 'session_index': calendar['session_index'],
            'remaining_sessions': calendar['remaining_sessions'], 'reduction_constraints': [],
            'last_discretionary_session': projection.get('last_discretionary_session'),
            'health': self.health(current)}
        return self.expand(context, request, assessment)

    @staticmethod
    def expand(context, request, assessment):
        context = deepcopy(context)
        context['assessments'] = [assessment] if assessment is not None else []
        issuer = request.get('issuer_id')
        context['assessment_requests'] = {issuer: request} if issuer else {}
        return context

    @staticmethod
    def compact(context):
        return {k: v for k, v in context.items() if k not in DERIVED}

    def context(self, current, request, assessment, now_ms, snapshot_for):
        """Context plus every exact-size quote the planner asks for (bounded pre-pass).

        The pre-pass calls the pure decide/plan functions on provisional snapshots only
        to discover quote sizes; the coordinator's own snapshot is built afterwards.
        """
        context = self.base(current, request, assessment, now_ms)
        seen = set()
        for _ in range(self.MAX_QUOTE_PASSES):
            snapshot = snapshot_for(context)
            try:
                proposal = self.decide(snapshot, snapshot.policy_state)
            except Exception:
                proposal = None  # the planner runs mandatory risk without a proposal
            requests = [r for r in self.plan(snapshot, proposal).read()['quote_requests']
                        if (r['symbol'], r['side'], r['pay_units']) not in seen]
            if not requests:
                break
            for r in requests:
                seen.add((r['symbol'], r['side'], r['pay_units']))
                quote = self.quotes.observe(Document.from_dict(r)).read()
                market = next(m for m in context['markets'] if m['symbol'] == r['symbol'])
                market.setdefault('quotes', []).append(quote)
        return context

    def recorded(self, compact_context):
        """A provider that replays one round's recorded context, never live sources."""
        return _Recorded(compact_context)


class _Recorded:
    def __init__(self, compact_context):
        self._context = compact_context

    def context(self, current, request, assessment, now_ms, snapshot_for):
        return StrategyContextProvider.expand(self._context, request, assessment)

    @staticmethod
    def compact(context):
        return StrategyContextProvider.compact(context)


def _decimal(units, decimals):
    text = format(Decimal(units).scaleb(-decimals).normalize(), 'f')
    if text in ('0', '-0'):
        raise ContractError('Zero order amount')
    return text


class StrategyPlanner:
    """Adapts Keith's plan(snapshot, proposal) to the coordinator's PlanResult.v1."""

    MONEY_DECIMALS = 6  # owner-local USDT scale (strategy.schema.MONEY_SCALE)

    def __init__(self, plan):
        self._plan = plan

    def plan(self, snapshot, proposal_or_none):
        result = self._plan(snapshot, proposal_or_none).read()
        intents, deltas, economic = [], [], {}
        for i in result['intents']:
            if i['side'] == 'BUY':
                amount = _decimal(i['pay_units'], self.MONEY_DECIMALS)  # USDT spent
            else:
                amount = _decimal(i['token_units'], i['decimals'])  # tokens sold
            intents.append({'intent_id': i['intent_id'], 'decision_id': 'decision:' + i['intent_id'],
                            'symbol': i['symbol'], 'side': i['side'], 'amount': amount,
                            'expires_ms': epoch_ms(i['quote_expiry']), 'economic': i})
        for d in result['reservation_deltas']:
            economic[d['intent_id']] = d
            for asset, units in (('USDT', d['cash_units']), ('BNB', d['bnb_units']),
                                 (d['symbol'], d['token_units'] if d['side'] == 'SELL' else 0)):
                if units:
                    deltas.append({'intent_id': d['intent_id'], 'asset': asset, 'units': units})
        out = {k: v for k, v in result.items() if k not in ('intents', 'reservation_deltas')}
        out.update(intents=intents, reservation_deltas=deltas, jobs=[], proposed_state={},
                   economic_reservations=economic)
        return Document.from_dict(out)


def on_plan(projection, plan):
    """Copy the plan's economic reservations into the portfolio (same atomic commit)."""
    projection['portfolio']['reservations'].update(deepcopy(plan['economic_reservations']))
    return projection

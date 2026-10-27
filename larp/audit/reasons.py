"""Concise reason summary for every round log (IDEA-099; F-34 "a concise reason summary", G-04).

A pure function of the stored round record: one sentence per order from its side, amount, symbol, `mandatory`
flag, the planner's `reasons` codes, the policy target for that symbol and any per-trade-cap split; and, for a round
with no order, one sentence naming its errors or the planner's rejections. No model text or outside values are
used, so replay gives the same bytes. An unknown code is shown as the code itself.
"""
from fractions import Fraction

# Planner `reasons` and policy target reasons (larp/risk/planner.py, larp/strategy/*).
ORDER = {
    'TERMINAL_FLATTEN': 'terminal flatten: sell positions before signing ends',
    'TERMINAL_REQUIREMENT': 'terminal flatten: sell positions before signing ends',
    'SCHEDULED_FLATTEN': 'scheduled flatten: sell positions at the scheduled time',
    'CLASS_1_EXIT': 'exit after a verified Class 1 filing red flag',
    'MANDATORY_FALSIFIER_REDUCTION': 'reduction required by a verified filing red flag',
    'BOUNDED_FALSIFIER': 'exit proposed after a verified filing red flag',
    'ACTIVATION_SELF_CHECK': 'activation self-check: sell the test position',
    'POSITION_CAP': 'trim to the per-name position cap',
    'GROSS_OR_REGIME_CAP': 'trim to the gross exposure cap',
    'DEEP_DRAWDOWN': 'trim for the latched deep drawdown limit',
    'POSITION_COUNT_CAP': 'sale above the position count cap',
    'PRICE_REASSESSMENT_EXIT': 'exit after a price reassessment',
    'S1_LEVEL_CHANGE': 'trend-guard exposure level changed',
    'S1_TOP_UP': 'top-up toward the target weight',
    'ACTIVATION_SELF_CHECK_BUY': 'activation self-check buy',
    'TOP_UP_TO_EQUAL_WEIGHT': 'top-up toward equal weight',
    'UNVALIDATED_BASELINE_ENTRY': 'baseline entry',
    'REVIEW_RESIZE': 'resize after review',
}
# Planner rejections (why a name was not traded this round).
REJECTION = {
    'MINIMUM_TRADE': 'below the minimum trade size',
    'DUST_OR_MINIMUM_TRADE': 'below the minimum trade size',
    'DUST_OR_UNEXECUTABLE': 'dust or not executable',
    'ENTRY_COST_CAP': 'entry cost above its cap',
    'ENTRY_IMPACT_CAP': 'price impact above its cap',
    'S1_REDUCTION_COST_CAP': 'reduction cost above its cap',
    'COST_RESERVE_INSUFFICIENT': 'cost reserve too low',
    'CASH_OR_EXIT_RESERVE': 'cash or exit reserve too low',
    'INSUFFICIENT_GAS': 'not enough gas',
    'UNAFFORDABLE_EXIT_FEE': 'exit fee not affordable',
    'NEW_RISK_HALTED': 'new risk halted',
    'PRICE_JUMP_HOLD': 'price jump hold',
    'MISSING_MARKET': 'market data missing',
    'MARKET_CLOSED_OR_UNKNOWN': 'market closed or openState unknown',
    'DISCRETIONARY_CADENCE': 'discretionary trade already made this session',
    'POSITION_COUNT_CAP': 'position count cap reached',
    'SCHEDULED_FLATTEN_PENDING': 'flatten still pending',
    'EXECUTION_BLOCKED': 'execution blocked',
    'NO_POLICY_PROPOSAL': 'no policy proposal',
    'PARTIAL_VALUATION_NEW_RISK_BLOCKED': 'incomplete valuation blocks new risk',
    'QUOTE_PENDING': 'waiting for a quote',
    'MANDATORY_REDUCTION_PENDING': 'mandatory reduction pending',
    'TEMP_SELF_CHECK_ONLY': 'temporary self-check run: no other buy',
    'TEMP_SELF_CHECK_SIZE': 'temporary self-check buy would reach 1 USDT',
}
MAX_PHRASES = 3
UNAVAILABLE = 'Reason summary unavailable: the round record has an unexpected shape.'


def _percent(weight):
    if type(weight) is not list or len(weight) != 2 or not all(type(v) is int for v in weight) or weight[1] <= 0:
        return None
    value = Fraction(weight[0], weight[1]) * 100
    return f'{value.numerator // value.denominator}%' if value.denominator == 1 else f'{float(value):.2f}%'


def _strings(values):
    return [v for v in values if type(v) is str and v] if type(values) is list else []


def order_sentence(intent, *, target=None, split=False, abort_reason=None):
    side, amount, symbol = intent.get('side'), intent.get('amount'), intent.get('symbol')
    # I3 / A10: BUY amount is cash spent in USDT; SELL amount is the token quantity.
    action = f'BUY {symbol} for {amount} USDT' if side == 'BUY' else f'{side} {amount} {symbol}'
    ending = f'; not submitted ({abort_reason}).' if abort_reason is not None else '.'
    if intent.get('kind') == 'GAS_TOP_UP':
        return f'{action}, gas top-up for transaction fees' + ending
    codes = _strings(intent.get('reasons'))
    phrases = list(dict.fromkeys(ORDER.get(code, code) for code in codes)) or ['no reason code recorded']
    if len(phrases) > MAX_PHRASES:
        phrases = phrases[:MAX_PHRASES] + [f'and {len(phrases) - MAX_PHRASES} more']
    text = '; '.join(phrases)
    weight = _percent(target.get('weight')) if type(target) is dict else None
    if weight is not None and intent.get('mandatory') is not True:
        text += f' (target weight {weight})'
    if split:
        text += '; split by the per-trade cap'
    kind = 'mandatory' if intent.get('mandatory') is True else 'discretionary'
    return f'{action}, {kind}: {text}' + ending


def _hold_sentence(record, plan):
    errors = _strings(record.get('errors'))
    if errors:
        return 'No order this round: ' + ', '.join(list(dict.fromkeys(errors))[:MAX_PHRASES]) + '.'
    grouped = {}
    for rejection in plan.get('rejections') or []:
        if type(rejection) is dict and type(rejection.get('reason')) is str:
            names = grouped.setdefault(rejection['reason'], [])
            # The symbol it applied to, or for a whole-round block its gates (EXECUTION_BLOCKED).
            for name in [rejection.get('symbol')] + _strings(rejection.get('gates')):
                if type(name) is str and name not in names:
                    names.append(name)
    for request in plan.get('quote_requests') or []:
        if type(request) is dict and type(request.get('symbol')) is str:
            names = grouped.setdefault('QUOTE_PENDING', [])
            if request['symbol'] not in names:
                names.append(request['symbol'])
    for requirement in plan.get('requirements') or []:
        if (type(requirement) is dict and type(requirement.get('symbol')) is str
                and type(requirement.get('remaining_sell_units')) is int and requirement['remaining_sell_units'] > 0):
            names = grouped.setdefault('MANDATORY_REDUCTION_PENDING', [])
            status = requirement.get('status')
            name = requirement['symbol'] + (f': {status}' if type(status) is str and status else '')
            if name not in names:
                names.append(name)
    if not grouped:
        return 'No order this round: no target change.'
    parts = [REJECTION.get(code, code) + (f' ({", ".join(names)})' if names else '')
             for code, names in list(grouped.items())[:MAX_PHRASES]]
    return 'No order this round: ' + '; '.join(parts) + '.'


def round_summary(record):
    """(`reason_summary`, `decision_summaries`) for one round record. Never raises."""
    try:
        plan = record.get('plan') if type(record.get('plan')) is dict else {}
        intents = [i for i in plan.get('intents') or [] if type(i) is dict]
        orders = record.get('orders') if type(record.get('orders')) is list else []
        output = record.get('policy_output') if type(record.get('policy_output')) is dict else {}
        targets = {t.get('symbol'): t for t in output.get('targets') or [] if type(t) is dict}
        splits = {c.get('symbol') for c in plan.get('clamps') or []
                  if type(c) is dict and c.get('reason') == 'PER_TRADE_CAP'}
        # Settlement binds non-submission to intent_id; symbol alone can identify several orders.
        aborted = {a['intent_id']: a.get('reason') or 'NOT_SUBMITTED' for a in record.get('aborted') or []
                   if type(a) is dict and type(a.get('intent_id')) is str}
        # `orders` is built from the intents in order; an emptied list (rejected or fallback round) has no orders.
        placed = intents if orders and len(orders) == len(intents) else []
        decisions = [dict(decision_id=i.get('decision_id'), symbol=i.get('symbol'), side=i.get('side'),
                          amount=i.get('amount'),
                          summary=order_sentence(i, target=targets.get(i.get('symbol')),
                                                 split=i.get('symbol') in splits,
                                                 abort_reason=aborted.get(i.get('intent_id'))))
                     for i in placed]
        if not decisions:
            return _hold_sentence(record, plan), []
        if len(decisions) == 1:
            return decisions[0]['summary'], decisions
        return f'{len(decisions)} orders: ' + ' '.join(d['summary'] for d in decisions[:MAX_PHRASES]), decisions
    except Exception:
        return UNAVAILABLE, []

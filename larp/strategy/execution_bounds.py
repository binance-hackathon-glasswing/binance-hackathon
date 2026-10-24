"""S1 B6: deterministic session/attempt authority, shared by planning and execution.

The runtime journals the budget with the round, not with a successful fill. Fresh
round/intent IDs and an execution-service restart cannot restore spent attempts.
Mandatory sales use a separate lane and bypass the discretionary time window.

IDEA-089 S2: `execution.hours` KIT_OPEN_STATE gives discretionary legs the mandatory lane's interval (session open
to the next open), for both the planner and execution admission. It is a dev REHEARSAL test setting only (S2-1); the
planner's `openState` check (F-95) and the profile window still apply.
"""
from larp.contracts import ContractError, Document
from .schema import SYMBOLS, integer

BASELINE = 'TREND_GUARDED_VOL'
SCHEMA = 'S1ExecutionBounds.v1'


HOURS = ('NYSE_SESSION', 'KIT_OPEN_STATE')
SCOPE = 'KIT_OPEN_STATE hours need a dev REHEARSAL with SHADOW evidence and falsifiers (IDEA-089 S2-1)'


def parameters(value):
    keys = {'open_delay_seconds', 'close_buffer_seconds', 'max_attempts_per_leg_session'}
    if type(value) is not dict or not keys <= set(value) <= keys | {'hours'}:
        raise ContractError('S1 execution needs explicit delay, buffer and attempt limit')
    if 'hours' in value and value['hours'] not in HOURS:
        raise ContractError('S1 execution hours must be NYSE_SESSION or KIT_OPEN_STATE')
    result = {k: integer(v) for k, v in value.items() if k != 'hours'}
    if (result['open_delay_seconds'] > 14400 or result['close_buffer_seconds'] > 14400
            or not 1 <= result['max_attempts_per_leg_session'] <= 5):
        raise ContractError('S1 execution parameters outside supported bounds')
    if 'hours' in value:
        result['hours'] = value['hours']  # absent: today's config, so existing profiles keep their meaning
    return result


def open_state_hours(profile):
    """True when a profile's S1 block sets `execution.hours` KIT_OPEN_STATE (IDEA-089 S2)."""
    s = profile.get('s1') if type(profile) is dict else None
    execution = s.get('execution') if type(s) is dict else None
    return type(execution) is dict and execution.get('hours') == 'KIT_OPEN_STATE'


def require_open_state_scope(profile, mode):
    """S2-1: refuse KIT_OPEN_STATE outside a REHEARSAL with SHADOW evidence and falsifiers, and outside a `dev`
    run. `mode` None is validate_live, which sees only the profile; preparation, the gate check and both service
    starts pass their run mode."""
    if open_state_hours(profile) and not (
            profile.get('environment') == 'REHEARSAL' and profile.get('evidence_mode') == 'SHADOW'
            and profile.get('falsifier_authority') == 'SHADOW' and mode in (None, 'dev')):
        raise ContractError(SCOPE)


def session(context):
    value = context.get('execution_session')
    keys = {'index', 'open_ms', 'close_ms', 'next_open_ms'}
    if type(value) is not dict or set(value) != keys:
        raise ContractError('S1 execution needs frozen calendar session bounds')
    result = {k: integer(v) for k, v in value.items()}
    if (result['index'] != context['session_index']
            or not result['open_ms'] < result['close_ms'] <= result['next_open_ms']):
        raise ContractError('S1 execution session identity/order mismatch')
    return result


def leg_key(symbol, side, mandatory):
    if symbol not in SYMBOLS or side not in ('BUY', 'SELL') or type(mandatory) is not bool:
        raise ContractError('Invalid S1 execution leg')
    if mandatory and side != 'SELL':
        raise ContractError('Mandatory S1 stock action must sell')
    return ('SAFETY' if mandatory else 'DISCRETIONARY') + ':' + side + ':' + symbol


def budget(value, current_session):
    """Malformed/future state cannot masquerade as a fresh allowance."""
    if value is None:
        return {'session': current_session, 'counts': {}, 'closed': {}}
    if type(value) is not dict or not {'session', 'counts'} <= set(value) <= {'session', 'counts', 'closed'}:
        raise ContractError('Malformed S1 execution attempt budget')
    prior = integer(value['session'])
    counts = value['counts']
    valid_keys = {leg_key(s, side, mandatory) for s in SYMBOLS for side in ('BUY', 'SELL')
                  for mandatory in (False, True) if not mandatory or side == 'SELL'}
    if type(counts) is not dict or not set(counts) <= valid_keys:
        raise ContractError('Malformed S1 execution attempt counts')
    counts = {k: integer(v, 1) for k, v in counts.items()}
    closed = value.get('closed', {})
    if type(closed) is not dict or not set(closed) <= set(counts):
        raise ContractError('Malformed S1 closed attempt slots')
    closed = {k: integer(v, 1) for k, v in closed.items()}
    if any(v > counts[k] for k, v in closed.items()):
        raise ContractError('Closed S1 attempt exceeds the reserved count')
    if prior > current_session:
        raise ContractError('S1 execution attempt session moved backwards')
    return {'session': current_session, 'counts': counts if prior == current_session else {},
            'closed': closed if prior == current_session else {}}


def interval(context, cfg, mandatory):
    s = session(context)
    limits = cfg['execution']
    if mandatory or limits.get('hours') == 'KIT_OPEN_STATE':
        return s['open_ms'], s['next_open_ms']
    return (s['open_ms'] + limits['open_delay_seconds'] * 1000,
            s['close_ms'] - limits['close_buffer_seconds'] * 1000)


def parent_authority(record):
    """Only the bounded driver's previous committed quote round may supply this.

    Preserve a small nonrecursive record for audit; the coordinator reconstructs
    it from the journal again during replay, rather than trusting a model field.
    """
    context = record.get('policy_input', {}).get('context', {})
    return dict(round_id=record['round_id'], profile_hash=Document.from_dict(context['profile']).digest('StrategyProfile.v1'),
                session_index=context['session_index'], attempts=record['plan'].get('execution_attempts', []),
                quote_requests=record['plan'].get('quote_requests', []))


def requested_legs(context):
    """(symbol, side) pairs whose quotes this round's parent requested, in the same session; else empty (IDEA-090).

    Ordering only: whether the parent's attempt may be reused is still decided by `_reuse`."""
    parent = context.get('execution_parent')
    if type(parent) is not dict or parent.get('session_index') != context.get('session_index'):
        return set()
    requests = parent.get('quote_requests')
    return {(r.get('symbol'), r.get('side')) for r in requests if type(r) is dict} if type(requests) is list else set()


def _reuse(context, state, key, start, end, symbol, side, quotes):
    if type(quotes) not in (list, tuple) or any(type(q) is not dict for q in quotes):
        return None
    parent = context.get('execution_parent')
    if type(parent) is not dict or parent.get('session_index') != state['session']:
        return None
    if parent.get('profile_hash') != Document.from_dict(context['profile']).digest('StrategyProfile.v1'):
        return None
    # A child may reuse only a requested exact-input quote that is actually in
    # its market input. An unrelated/ordinary new round cannot recycle a slot.
    matching = any(r.get('symbol') == symbol and r.get('side') == side
                   and any(q.get('side') == side and q.get('pay_asset') == r.get('pay_asset')
                           and q.get('pay_units') == r.get('pay_units') for q in quotes)
                   for r in parent.get('quote_requests', []))
    if not matching:
        return None
    for item in parent.get('attempts', []):
        a = item.get('authority', {})
        if (a.get('schema') == SCHEMA and a.get('session_index') == state['session'] and a.get('leg') == key
                and a.get('ordinal') == state['counts'].get(key) and a.get('valid_from_ms') == start
                and a.get('valid_until_ms') == end and state['closed'].get(key, 0) < a['ordinal']):
            return dict(a)
    return None


def reserve(context, cfg, state, symbol, side, mandatory, now_ms, *, quotes=()):
    """Consume one quote-evaluation round; return (authority, refusal)."""
    start, end = interval(context, cfg, mandatory)
    if not start <= now_ms < end:
        return None, 'EXECUTION_WINDOW_CLOSED'
    key = leg_key(symbol, side, mandatory)
    reused = _reuse(context, state, key, start, end, symbol, side, quotes)
    if reused is not None and reused['ordinal'] <= cfg['execution']['max_attempts_per_leg_session']:
        return reused, None
    ordinal = state['counts'].get(key, 0) + 1
    if ordinal > cfg['execution']['max_attempts_per_leg_session']:
        return None, 'LEG_ATTEMPT_LIMIT'
    state['counts'][key] = ordinal
    return dict(schema=SCHEMA, session_index=state['session'], leg=key, ordinal=ordinal,
                valid_from_ms=start, valid_until_ms=end), None


def close(state, authority):
    """A terminal quote refusal or an issued intent ends quote-slot reuse.

    This is durable even if execution later aborts before submission. A fresh
    retry needs a fresh slot, never an older ancestor's quote-round reference.
    """
    state['closed'][authority['leg']] = authority['ordinal']


def permitted(projection, intent, now_ms):
    """Reconstruct authority from the runtime-owned round, never primary's gate flags.

    Non-S1 historical/offline records retain their existing checks. An S1 record
    with absent, mismatched or expired bounds fails closed. Reconciliation does
    not call this function to decide whether receipt observations may be saved.
    """
    record = projection.get('round_records', {}).get(intent.round_id)
    if type(record) is not dict:
        return True  # reservation/audit checks separately require a planned round
    context = record.get('policy_input', {}).get('context', {})
    p = context.get('profile', {})
    if p.get('baseline') != BASELINE:
        return True
    try:
        from .s1 import config
        planned = next(i for i in record['plan']['intents'] if i['intent_id'] == intent.intent_id)
        if planned.get('kind') == 'GAS_TOP_UP':
            return intent.kind == 'GAS_TOP_UP'  # separate native-resource controls, not an S1 stock leg
        cfg = config(p)
        from larp.execution import USDT
        from larp.marketdata.port import TOKENS
        token = TOKENS[planned['symbol']]
        buy = planned['side'] == 'BUY'
        if (intent.kind != 'BSTOCK_TRADE'
                or intent.pay_token != (USDT if buy else token)
                or intent.receive_token != (token if buy else USDT)
                or intent.amount != planned['pay_units'] * (10**12 if buy else 1)
                or intent.minimum_output != planned['min_receive_units'] * (1 if buy else 10**12)):
            return False  # a BUY cannot borrow a mandatory SELL's after-hours authority
        authority = planned['execution_bounds']
        start, end = interval(context, cfg, planned['mandatory'])
        key = leg_key(planned['symbol'], planned['side'], planned['mandatory'])
        slots = budget(record['plan']['execution_attempt_budget'], context['session_index'])
        count = slots['counts'][key]
        ordinal = integer(authority['ordinal'], 1)
        return (authority == dict(schema=SCHEMA, session_index=context['session_index'], leg=key,
                                  ordinal=ordinal, valid_from_ms=start, valid_until_ms=end)
                and ordinal == count == slots['closed'].get(key) <= cfg['execution']['max_attempts_per_leg_session']
                and start <= now_ms < end)
    except (ContractError, KeyError, TypeError, ValueError, AttributeError, StopIteration):
        return False

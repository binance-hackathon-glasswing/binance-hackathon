"""IDEA-076 EB1/2/3: synthetic prices and frozen calendar, no venue calls."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import json
import unittest

from larp.contracts import ContractError, Document
from larp.integration.runtime import RuntimePlanner
from larp.research.fixtures import changed, with_quotes
from larp.risk.planner import plan
from larp.runtime.driver import SessionCalendar
from larp.strategy import execution_bounds as bounds, s1
from larp.strategy.policy import decide
from tests.strategy.test_s1_core import block
from tests.strategy.test_s1_plan import snap, settled, NAMES, AT_95, FALLING


def milliseconds(value):
    return int(datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()*1000)


def at(value, *, held=None, state=None, path=None, **context):
    """Retimestamp synthetic observations; retain one explicitly synthetic session."""
    result = snap(held, state=state, path=path, **context)
    now = datetime.fromisoformat(value.replace('Z', '+00:00'))
    markets = result.context.read()['markets']
    for market in markets:
        for key in ('observed_at', 'available_at', 'close_at'):
            market[key] = now.isoformat()
    return replace(changed(result, markets=markets), observed_at=now)


def run(snapshot):
    return plan(snapshot, decide(snapshot, snapshot.policy_state)).read()


class Configuration(unittest.TestCase):
    def test_explicit_execution_parameters_required_without_defaults(self):
        for value in (None, {}, dict(open_delay_seconds=0, close_buffer_seconds=0),
                      dict(open_delay_seconds=True, close_buffer_seconds=0, max_attempts_per_leg_session=3),
                      dict(open_delay_seconds=0, close_buffer_seconds=0, max_attempts_per_leg_session=0),
                      dict(open_delay_seconds=0, close_buffer_seconds=0, max_attempts_per_leg_session=6),
                      dict(open_delay_seconds=14401, close_buffer_seconds=0, max_attempts_per_leg_session=3)):
            with self.subTest(value=value), self.assertRaises(ContractError):
                s1.config({'s1': block(execution=value)})
        value = block()
        del value['execution']
        with self.assertRaises(ContractError):
            s1.config({'s1': value})

    def test_real_frozen_calendar_supplies_dst_holiday_and_early_close_bounds(self):
        root = Path(__file__).resolve().parents[2]
        calendar = SessionCalendar(json.loads((root/'config/runtime/session-calendar.2026.json').read_text()))
        for stamp, opened, closed in (
            ('2026-10-30T14:00:00Z', '2026-10-30T13:30:00Z', '2026-10-30T20:00:00Z'),
            ('2026-11-02T15:00:00Z', '2026-11-02T14:30:00Z', '2026-11-02T21:00:00Z'),
            ('2026-11-27T15:00:00Z', '2026-11-27T14:30:00Z', '2026-11-27T18:00:00Z')):
            with self.subTest(stamp=stamp):
                self.assertEqual((calendar.window(milliseconds(stamp))['open_ms'],
                                  calendar.window(milliseconds(stamp))['close_ms']),
                                 (milliseconds(opened), milliseconds(closed)))
        friday = calendar.window(milliseconds('2026-10-30T22:00:00Z'))
        weekend = calendar.window(milliseconds('2026-11-01T23:00:00Z'))
        self.assertEqual(friday, weekend)
        self.assertEqual(friday['next_open_ms'], milliseconds('2026-11-02T14:30:00Z'))
        thanksgiving = calendar.window(milliseconds('2026-11-26T15:00:00Z'))
        self.assertEqual(thanksgiving['next_open_ms'], milliseconds('2026-11-27T14:30:00Z'))


class Planning(unittest.TestCase):
    def test_discretionary_buy_and_sell_window_edges(self):
        for sell in (False, True):
            for stamp, allowed in (('2026-10-10T13:59:59Z', False), ('2026-10-10T14:00:00Z', True),
                                   ('2026-10-10T19:44:59Z', True), ('2026-10-10T19:45:00Z', False),
                                   ('2026-10-10T23:00:00Z', False)):
                with self.subTest(sell=sell, stamp=stamp):
                    snapshot = at(stamp, **(dict(held={n: AT_95 for n in NAMES},
                                                 state=settled([19, 20]), path=FALLING) if sell else {}))
                    result = run(snapshot)
                    self.assertEqual(bool(result['execution_attempts']), allowed, result)
                    self.assertEqual(bool(result['quote_requests']), allowed, result)
                    if not allowed:
                        self.assertIn('EXECUTION_WINDOW_CLOSED', {r['reason'] for r in result['rejections']})

    def test_same_round_quote_refinement_consumes_one_attempt(self):
        snapshot = with_quotes(at('2026-10-10T14:00:00Z'))
        first = run(snapshot)
        self.assertTrue(first['intents'], first)
        self.assertEqual(first, run(snapshot))  # deterministic replan does not mutate input budget
        item = first['intents'][0]
        self.assertEqual(item['execution_bounds']['ordinal'], 1)
        self.assertEqual(first['execution_attempt_budget']['counts'][item['execution_bounds']['leg']], 1)
        self.assertEqual(first['execution_attempts'][0]['authority'], item['execution_bounds'])

    def test_quote_and_cost_refusals_exhaust_attempts_across_rounds(self):
        for bad_cost in (False, True):
            with self.subTest(bad_cost=bad_cost):
                snapshot = at('2026-10-10T14:00:00Z')
                snapshot = changed(snapshot, markets=[m for m in snapshot.context.read()['markets']
                                                      if m['symbol'] == 'NVDAB'])
                if bad_cost:
                    snapshot = with_quotes(snapshot, spread_bps=100)
                for ordinal in range(1, 4):
                    result = run(snapshot)
                    self.assertFalse(result['intents'], result)
                    self.assertTrue(result['execution_attempts'], result)
                    self.assertTrue(all(i['authority']['ordinal'] == ordinal for i in result['execution_attempts']))
                    snapshot = changed(snapshot, execution_attempt_budget=result['execution_attempt_budget'])
                refused = run(snapshot)
                self.assertFalse(refused['intents'])
                self.assertFalse(refused['quote_requests'])
                self.assertFalse(refused['execution_attempts'])
                self.assertIn('LEG_ATTEMPT_LIMIT', {r['reason'] for r in refused['rejections']})

    def test_quote_child_reuses_only_its_committed_parent_attempt(self):
        snapshot = at('2026-10-10T14:00:00Z')
        first = run(snapshot)
        self.assertEqual(len(first['quote_requests']), 1)
        parent = bounds.parent_authority(dict(round_id='parent', policy_input=dict(context=snapshot.context.read()),
                                               plan=first))
        snapshot = changed(with_quotes(snapshot), execution_attempt_budget=first['execution_attempt_budget'],
                           execution_parent=parent)
        result = run(snapshot)
        self.assertTrue(result['intents'], result)
        self.assertEqual(result['intents'][0]['execution_bounds']['ordinal'], 1)
        ordinary = run(changed(snapshot, execution_parent=None))
        self.assertEqual(ordinary['intents'][0]['execution_bounds']['ordinal'], 2)
        # Wrong profile/session or quote request cannot provide free retries.
        for changes in ({'profile_hash': '0'*64}, {'session_index': 81}, {'quote_requests': []}):
            with self.subTest(changes=changes):
                result = run(changed(snapshot, execution_parent=dict(parent, **changes)))
                self.assertEqual(result['intents'][0]['execution_bounds']['ordinal'], 2)

    def test_mandatory_exit_bypasses_window_and_has_its_own_bounded_lane(self):
        snapshot = at('2026-10-10T23:00:00Z', held={'NVDAB': 8000},
                      execution_attempt_budget={'session': 80, 'counts': {'DISCRETIONARY:SELL:NVDAB': 3}})
        for ordinal in range(1, 4):
            result = run(snapshot)
            self.assertTrue(result['requirements'])
            self.assertEqual(result['execution_attempts'][0]['authority']['ordinal'], ordinal)
            self.assertTrue(result['execution_attempts'][0]['mandatory'])
            snapshot = changed(snapshot, execution_attempt_budget=result['execution_attempt_budget'])
        refused = run(snapshot)
        self.assertFalse(refused['intents'])
        self.assertEqual(refused['requirements'][0]['status'], 'LEG_ATTEMPT_LIMIT')
        self.assertGreater(refused['requirements'][0]['remaining_sell_units'], 0)

    def test_missing_or_malformed_session_and_budget_refuse_without_resetting(self):
        values = [dict(execution_session=None), dict(execution_session={}),
                  dict(execution_attempt_budget={'session': 81, 'counts': {}}),
                  dict(execution_attempt_budget={'session': 80, 'counts': {'invented': 1}}),
                  dict(execution_attempt_budget={'session': 80, 'counts': {'DISCRETIONARY:BUY:NVDAB': True}})]
        for changes in values:
            with self.subTest(changes=changes):
                result = run(changed(snap(), **changes))
                self.assertFalse(result['intents'])
                self.assertFalse(result['quote_requests'])
                self.assertIn('EXECUTION_BOUNDS_INVALID', {r['reason'] for r in result['rejections']})

    def test_budget_resets_only_on_actual_session_rollover(self):
        state = {'session': 80, 'counts': {'DISCRETIONARY:BUY:NVDAB': 3}, 'closed': {}}
        self.assertEqual(bounds.budget(state, 80), state)
        self.assertEqual(bounds.budget(state, 81), {'session': 81, 'counts': {}, 'closed': {}})
        with self.assertRaises(ContractError):
            bounds.budget(state, 79)

    def test_consumed_quote_parent_cannot_recycle_an_attempt(self):
        snapshot = at('2026-10-10T14:00:00Z')
        initial = run(snapshot)
        parent = bounds.parent_authority(dict(round_id='parent', policy_input=dict(context=snapshot.context.read()),
                                               plan=initial))
        snapshot = changed(with_quotes(snapshot), execution_attempt_budget=initial['execution_attempt_budget'],
                           execution_parent=parent)
        for ordinal in range(1, 4):
            result = run(snapshot)
            intent = result['intents'][0]
            self.assertEqual(intent['execution_bounds']['ordinal'], ordinal)
            self.assertEqual(result['execution_attempt_budget']['closed'][intent['execution_bounds']['leg']], ordinal)
            snapshot = changed(snapshot, execution_attempt_budget=result['execution_attempt_budget'])
        refused = run(snapshot)
        # Another name may be considered, but this name cannot reuse slot 1.
        self.assertNotIn(initial['quote_requests'][0]['symbol'], [i['symbol'] for i in refused['intents']])
        self.assertIn({'symbol': initial['quote_requests'][0]['symbol'], 'reason': 'LEG_ATTEMPT_LIMIT'},
                      refused['rejections'])

    def test_command_expiry_cannot_outlive_the_execution_window(self):
        snapshot = with_quotes(at('2026-10-10T19:44:59Z'))
        result = RuntimePlanner(job_validity_ms=60000, job_max_attempts=3).plan(
            snapshot, decide(snapshot, snapshot.policy_state)).read()
        self.assertTrue(result['intents'], result)
        self.assertTrue(all(i['expires_ms'] == milliseconds('2026-10-10T19:45:00Z') for i in result['intents']))


def round_record(*, mandatory=False, ordinal=1):
    context = snap().context.read()
    cfg = s1.config(context['profile'])
    state = bounds.budget(None, context['session_index'])
    key = bounds.leg_key('NVDAB', 'SELL' if mandatory else 'BUY', mandatory)
    if ordinal > 1:
        state['counts'][key] = ordinal-1
    authority, refused = bounds.reserve(context, cfg, state, 'NVDAB', 'SELL' if mandatory else 'BUY',
                                        mandatory, milliseconds('2026-10-10T14:00:00Z'))
    assert refused is None
    bounds.close(state, authority)
    return dict(policy_input=dict(context=context), plan=dict(execution_attempt_budget=state,
        intents=[dict(intent_id='economic-1', symbol='NVDAB', side='SELL' if mandatory else 'BUY',
                      pay_units=100, min_receive_units=90, mandatory=mandatory, execution_bounds=authority)]))


class DurableAuthority(unittest.TestCase):
    def test_reconstructs_from_durable_plan_and_refuses_mutated_authority(self):
        from tests.execution_fixtures import intent
        economic = intent(amount=100*10**12)
        record = round_record()
        projection = dict(round_records={'round': record})
        self.assertTrue(bounds.permitted(projection, economic, milliseconds('2026-10-10T14:00:00Z')))
        for stamp in ('2026-10-10T13:59:59Z', '2026-10-10T19:45:00Z', '2026-10-11T14:00:00Z'):
            self.assertFalse(bounds.permitted(projection, economic, milliseconds(stamp)))
        for changes in ({'ordinal': 2}, {'valid_until_ms': milliseconds('2026-10-11T20:00:00Z')},
                        {'leg': 'SAFETY:SELL:NVDAB'}, {'session_index': 81}):
            mutated = deepcopy(record)
            mutated['plan']['intents'][0]['execution_bounds'].update(changes)
            self.assertFalse(bounds.permitted(dict(round_records={'round': mutated}), economic,
                                             milliseconds('2026-10-10T14:00:00Z')))
        del record['plan']['intents'][0]['execution_bounds']
        self.assertFalse(bounds.permitted(projection, economic, milliseconds('2026-10-10T14:00:00Z')))

    def test_safety_authority_is_valid_after_hours_but_not_next_session(self):
        from tests.execution_fixtures import intent
        from larp.execution import USDT
        from larp.marketdata.port import TOKENS
        projection = dict(round_records={'round': round_record(mandatory=True)})
        economic = intent(pay_token=TOKENS['NVDAB'], receive_token=USDT, min_receive=90*10**12)
        self.assertTrue(bounds.permitted(projection, economic, milliseconds('2026-10-10T23:00:00Z')))
        self.assertFalse(bounds.permitted(projection, economic, milliseconds('2026-10-11T13:30:00Z')))
        self.assertFalse(bounds.permitted(projection, intent(amount=100*10**12),
                                          milliseconds('2026-10-10T23:00:00Z')))
        self.assertFalse(bounds.permitted(projection, replace(economic, amount=101),
                                          milliseconds('2026-10-10T23:00:00Z')))
        self.assertFalse(bounds.permitted(projection, replace(economic, min_receive=89*10**12),
                                          milliseconds('2026-10-10T23:00:00Z')))

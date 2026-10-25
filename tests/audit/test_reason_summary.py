"""Concise reason summary in every round log (IDEA-099 RS1-RS5; F-34, G-04)."""

import json
import re
import unittest
from copy import deepcopy

from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePolicy
from larp.storage.postgres import doc
from tests.audit.test_round_logging import ADDRESS, NOW, TX, ModelAssessor, Planned, intent, mapping_reducer
from tests.support import DatabaseCase, request


def sentences(text):
    return [s for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s]


class Rejecting:
    """A planner that plans nothing and reports rejections, as the real planner does."""

    def __init__(self, rejections):
        self.rejections = rejections

    def plan(self, snapshot, proposal):
        return doc(dict(schema='PlanResult.v1', snapshot_id=snapshot.snapshot_id, reasons=['SYNTHETIC'],
                        intents=[], reservation_deltas=[], proposed_state={}, jobs=[], rejections=self.rejections))


class Logged(DatabaseCase):
    def test_rv2_oversize_fallback_has_empty_decision_summaries(self):
        c = Coordinator(self.store, ModelAssessor('x' * (5 * 1024 * 1024)), FakePolicy(),
                        Planned([intent('x')], [dict(intent_id='intent:x', asset='USDT', units=1)]),
                        execution=FakeExecution(), run_id='run', version_id='synthetic', profile_hash='a' * 64,
                        address=ADDRESS, clock_ms=lambda: NOW)
        c.start('fallback', request('BUY'), NOW)
        with self.store.transaction() as db:
            event = json.loads(bytes(db.execute('SELECT document FROM audit_events WHERE run_id=%s',
                                               ('run',)).fetchone()[0]).decode())
            self.assertEqual(db.execute('SELECT count(*) FROM commands WHERE run_id=%s',
                                        ('run',)).fetchone()[0], 0)
        log = json.loads(event['log'])['data']
        self.assertEqual(log['orders'], [])
        self.assertEqual(log['output']['decision_summaries'], [])
        self.assertIn('AUDIT_CONTENT_UNSUPPORTED', log['output']['reason_summary'])

    def run_round(self, planner, round_id='r', *, settle=False):
        c = Coordinator(self.store, FakeAssessor(), FakePolicy(), planner, execution=FakeExecution(), run_id='run',
                        version_id='synthetic', profile_hash='a' * 64, address=ADDRESS, clock_ms=lambda: NOW)
        c.start(round_id, request('BUY'), NOW)
        if settle:  # an executed round is logged when it closes
            for kind in ('BROADCAST_ATTEMPTED', 'FINAL_SUCCESS'):
                c.observe(kind, doc(dict(kind=kind, observation_id=kind, round_id=round_id, tx_hash=TX,
                                         simulated=True)), mapping_reducer)
            c.recover(NOW + 1)
        with self.store.transaction() as db:
            events = [json.loads(bytes(r[0]).decode())['log'] for r in db.execute(
                'SELECT document FROM audit_events WHERE run_id=%s AND round_id=%s', ('run', round_id))]
        self.assertEqual(len(events), 1)
        return json.loads(events[0])['data']

    def test_rs1_one_order_has_one_matching_summary(self):
        planned = intent('x', symbol='NVDAB', side='SELL', amount='0.05', mandatory=True,
                         reasons=['TERMINAL_FLATTEN'])
        log = self.run_round(Planned([planned], [dict(intent_id='intent:x', asset='USDT', units=1)]), settle=True)
        out = log['output']
        self.assertEqual(len(log['orders']), 1)
        self.assertEqual([(d['decision_id'], d['symbol'], d['side'], d['amount']) for d in out['decision_summaries']],
                         [('decision:x', 'NVDAB', 'SELL', '0.05')])
        summary = out['reason_summary']
        self.assertIsInstance(summary, str)
        self.assertTrue(summary.strip())
        self.assertLessEqual(len(summary), 400)
        self.assertLessEqual(len(sentences(summary)), 3)
        self.assertEqual(summary, out['decision_summaries'][0]['summary'])
        self.assertIn('SELL 0.05 NVDAB', summary)
        self.assertIn('mandatory', summary)
        self.assertIn('terminal flatten', summary)

    def test_rs3_hold_round_names_planner_rejections(self):
        log = self.run_round(Rejecting([dict(symbol='NVDAB', reason='MINIMUM_TRADE'),
                                        dict(symbol='TSLAB', reason='MINIMUM_TRADE'),
                                        dict(symbol='GOOGLB', reason='ENTRY_COST_CAP'),
                                        dict(symbol='SKHYB', reason='NEW_RISK_HALTED'),
                                        dict(symbol='MSFTB', reason='PRICE_JUMP_HOLD')]))
        out = log['output']
        self.assertEqual((log['orders'], out['decision_summaries']), ([], []))
        summary = out['reason_summary']
        self.assertTrue(summary.startswith('No order this round'))
        self.assertLessEqual(len(sentences(summary)), 3)
        self.assertIn('below the minimum trade size', summary)
        self.assertIn('entry cost above its cap', summary)
        self.assertIn('new risk halted', summary)
        self.assertNotIn('price jump', summary)  # at most three distinct reasons

    def test_rs3_a_rejected_commit_has_no_order_and_says_why(self):
        planned = intent('x', reasons=['S1_LEVEL_CHANGE'])
        log = self.run_round(Planned([planned], [dict(intent_id='intent:x', asset='USDT', units=1000)]))
        out = log['output']
        self.assertEqual((log['orders'], out['decision_summaries']), ([], []))
        self.assertIn('COMMIT_REJECTED', out['reason_summary'])

    def test_rs5_orders_keep_the_kit_schema(self):
        planned = intent('x', reasons=['S1_LEVEL_CHANGE'], mandatory=False)
        log = self.run_round(Planned([planned], [dict(intent_id='intent:x', asset='USDT', units=10)]), settle=True)
        self.assertEqual(log['orders'], [dict(symbol='NVDAB', side='BUY', amount='10', tx_hash=TX)])
        self.assertIn('BUY NVDAB for 10 USDT', log['output']['reason_summary'])


class Phrases(unittest.TestCase):
    def test_rv6_real_planner_quote_request_is_not_no_target_change(self):
        from larp.audit.reasons import round_summary
        from larp.research.fixtures import snapshot
        from larp.risk.planner import plan
        from larp.strategy.policy import decide
        s = snapshot()
        planned = plan(s, decide(s, s.policy_state)).read()
        self.assertEqual(planned['intents'], [])
        self.assertTrue(planned['quote_requests'])
        summary, decisions = round_summary(dict(plan=planned, orders=[], errors=[]))
        self.assertEqual(decisions, [])
        self.assertIn('waiting for a quote', summary)
        self.assertIn(planned['quote_requests'][0]['symbol'], summary)
        self.assertNotIn('no target change', summary)

    def test_rv6_blocked_mandatory_reduction_names_symbol_and_status(self):
        from larp.audit.reasons import round_summary
        for status in ('BLOCKED_MARK', 'BLOCKED_INPUT'):
            with self.subTest(status=status):
                record = dict(orders=[], errors=[], plan=dict(requirements=[
                    dict(symbol='NVDAB', remaining_sell_units=100, status=status),
                    dict(symbol='GOOGLB', remaining_sell_units=0, status='DONE')]))
                summary, decisions = round_summary(record)
                self.assertEqual(decisions, [])
                self.assertIn(f'mandatory reduction pending (NVDAB: {status})', summary)
                self.assertNotIn('GOOGLB', summary)
                self.assertNotIn('no target change', summary)

    def test_rv5_buy_cash_and_sell_token_units_are_explicit(self):
        for symbol in ('NVDAB', 'BNB'):
            with self.subTest(symbol=symbol):
                fields = dict(symbol=symbol, side='BUY', amount='32.262', mandatory=False)
                if symbol == 'BNB':
                    fields['kind'] = 'GAS_TOP_UP'
                summary, decisions = self.summarize(fields)
                self.assertTrue(summary.startswith(f'BUY {symbol} for 32.262 USDT,'))
                self.assertEqual(decisions[0]['amount'], '32.262')
                self.assertEqual(decisions[0]['symbol'], symbol)
        summary = self.one(side='SELL', amount='0.05', symbol='NVDAB')
        self.assertTrue(summary.startswith('SELL 0.05 NVDAB,'))
        self.assertNotIn('USDT', summary)

    def test_rv1_actions_do_not_claim_completion_or_current_drawdown(self):
        for code in ('TERMINAL_FLATTEN', 'SCHEDULED_FLATTEN', 'ACTIVATION_SELF_CHECK'):
            with self.subTest(code=code):
                summary = self.one(reasons=[code])
                self.assertIn('sell', summary)
                self.assertNotIn('is sold', summary)
        summary = self.one(reasons=['DEEP_DRAWDOWN'])
        self.assertIn('latched', summary)
        self.assertNotIn('equity at or below', summary)
        summary = self.one(reasons=['BOUNDED_FALSIFIER'], mandatory=False)
        self.assertIn('discretionary', summary)
        self.assertNotIn('required', summary)

    def test_rv1_abort_matches_intent_identity_in_order(self):
        from larp.audit.reasons import round_summary
        intents = [intent('first', reasons=['TERMINAL_FLATTEN'], side='SELL', mandatory=True),
                   intent('second', reasons=['ACTIVATION_SELF_CHECK'], side='SELL', mandatory=True)]
        record = dict(plan=dict(intents=intents), orders=[dict(symbol=i['symbol'], side=i['side'],
                      amount=i['amount']) for i in intents], aborted=[
                          dict(intent_id='intent:second', reason='QUOTE_EXPIRED')])
        before = deepcopy(record)
        summary, decisions = round_summary(record)
        self.assertEqual([d['decision_id'] for d in decisions], ['decision:first', 'decision:second'])
        self.assertNotIn('not submitted', decisions[0]['summary'])
        self.assertIn('not submitted (QUOTE_EXPIRED)', decisions[1]['summary'])
        self.assertEqual(summary, '2 orders: ' + ' '.join(d['summary'] for d in decisions))
        self.assertEqual(record, before)
        self.assertEqual(round_summary(record), (summary, decisions))

    def test_rv1_gas_top_up_abort_is_explicit(self):
        from larp.audit.reasons import round_summary
        top = intent('gas', symbol='BNB', kind='GAS_TOP_UP')
        summary, _ = round_summary(dict(plan=dict(intents=[top]), orders=[dict(symbol='BNB', side='BUY',
                                  amount='10')], aborted=[dict(intent_id='intent:gas')]))
        self.assertIn('gas top-up', summary)
        self.assertIn('not submitted (NOT_SUBMITTED)', summary)

    def test_rv3_malformed_optional_shapes_do_not_raise(self):
        from larp.audit.reasons import UNAVAILABLE, round_summary
        for record in (None, [], dict(plan=dict(intents=7)),
                       dict(policy_output=dict(targets=[dict(symbol=[])]))):
            with self.subTest(record=record):
                self.assertEqual(round_summary(record), (UNAVAILABLE, []))

    def summarize(self, intent_fields, *, targets=None, clamps=(), rejections=(), errors=()):
        from larp.audit.reasons import round_summary
        intents = [dict(intent_id='intent:x', decision_id='decision:x', **intent_fields)]
        record = dict(errors=list(errors), orders=[dict(symbol=i['symbol'], side=i['side'], amount=i['amount'])
                                                   for i in intents],
                      plan=dict(intents=intents, clamps=list(clamps), rejections=list(rejections)),
                      policy_output=None if targets is None else dict(targets=targets))
        return round_summary(record)

    def one(self, **fields):
        fields.setdefault('symbol', 'SKHYB')
        fields.setdefault('side', 'SELL')
        fields.setdefault('amount', '0.068939879194155372')
        fields.setdefault('mandatory', True)
        summary, decisions = self.summarize(fields)
        self.assertEqual(len(decisions), 1)
        self.assertLessEqual(len(sentences(summary)), 3)
        return summary

    def test_rs2_each_known_code_has_a_phrase(self):
        expected = {'TERMINAL_FLATTEN': 'terminal flatten', 'SCHEDULED_FLATTEN': 'scheduled flatten',
                    'CLASS_1_EXIT': 'verified Class 1 filing', 'ACTIVATION_SELF_CHECK': 'activation self-check',
                    'POSITION_CAP': 'per-name position cap', 'GROSS_OR_REGIME_CAP': 'gross exposure cap',
                    'DEEP_DRAWDOWN': 'deep drawdown', 'POSITION_COUNT_CAP': 'position count cap'}
        for code, phrase in expected.items():
            with self.subTest(code=code):
                self.assertIn(phrase, self.one(reasons=[code]))

    def test_rs2_discretionary_orders_cite_the_policy_target(self):
        for code, phrase in (('S1_LEVEL_CHANGE', 'exposure level changed'), ('S1_TOP_UP', 'top-up toward'),
                             ('ACTIVATION_SELF_CHECK_BUY', 'activation self-check buy')):
            with self.subTest(code=code):
                summary, _ = self.summarize(dict(symbol='NVDAB', side='BUY', amount='32', mandatory=False,
                                                 reasons=[code]),
                                            targets=[dict(symbol='NVDAB', kind='TARGET_WEIGHT', reason=code,
                                                          weight=[19, 100])])
                self.assertIn('BUY NVDAB for 32 USDT', summary)
                self.assertIn('discretionary', summary)
                self.assertIn(phrase, summary)
                self.assertIn('19%', summary)

    def test_rs2_gas_top_up(self):
        summary, _ = self.summarize(dict(symbol='BNB', side='BUY', amount='1', kind='GAS_TOP_UP'))
        self.assertIn('gas top-up', summary)

    def test_rs2_per_trade_cap_split_is_stated(self):
        summary, _ = self.summarize(dict(symbol='SKHYB', side='SELL', amount='0.06', mandatory=True,
                                         reasons=['TERMINAL_FLATTEN']),
                                    clamps=[dict(symbol='SKHYB', reason='PER_TRADE_CAP', requested_units=2,
                                                 planned_units=1)])
        self.assertIn('per-trade cap', summary)

    def test_rs2_unknown_code_is_shown_verbatim(self):
        self.assertIn('NEW_CODE_X', self.one(reasons=['NEW_CODE_X']))

    def test_rs3_errors_come_first(self):
        from larp.audit.reasons import round_summary
        summary, decisions = round_summary(dict(errors=['HALTED:CLOCK', 'VERSION_NOT_REGISTERED'], orders=[],
                                                plan=dict(intents=[], rejections=[dict(reason='MINIMUM_TRADE')])))
        self.assertEqual(decisions, [])
        self.assertIn('HALTED:CLOCK', summary)
        self.assertIn('VERSION_NOT_REGISTERED', summary)
        self.assertNotIn('minimum trade', summary)

    def test_rs3_a_blocked_round_names_its_gates(self):
        from larp.audit.reasons import round_summary
        summary, _ = round_summary(dict(errors=[], orders=[], plan=dict(intents=[], rejections=[
            dict(reason='EXECUTION_BLOCKED', gates=['WALLET_PENDING', 'SIGNING_END'])])))
        self.assertEqual(summary, 'No order this round: execution blocked (WALLET_PENDING, SIGNING_END).')

    def test_rs3_nothing_to_do(self):
        from larp.audit.reasons import round_summary
        summary, _ = round_summary(dict(errors=[], orders=[], plan=dict(intents=[])))
        self.assertEqual(summary, 'No order this round: no target change.')

    def test_rs4_pure(self):
        fields = dict(symbol='SKHYB', side='SELL', amount='0.06', mandatory=True, reasons=['CLASS_1_EXIT'])
        self.assertEqual(self.summarize(dict(fields)), self.summarize(dict(fields)))

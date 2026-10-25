"""Concise reason summary in every round log (IDEA-099 RS1-RS5; F-34, G-04)."""

import json
import re
import unittest

from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePolicy
from larp.storage.postgres import doc
from tests.audit.test_round_logging import ADDRESS, NOW, TX, Planned, intent, mapping_reducer
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


class Phrases(unittest.TestCase):
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
                self.assertIn('BUY 32 NVDAB', summary)
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

    def test_rs3_nothing_to_do(self):
        from larp.audit.reasons import round_summary
        summary, _ = round_summary(dict(errors=[], orders=[], plan=dict(intents=[])))
        self.assertEqual(summary, 'No order this round: no target change.')

    def test_rs4_pure(self):
        fields = dict(symbol='SKHYB', side='SELL', amount='0.06', mandatory=True, reasons=['CLASS_1_EXIT'])
        self.assertEqual(self.summarize(dict(fields)), self.summarize(dict(fields)))

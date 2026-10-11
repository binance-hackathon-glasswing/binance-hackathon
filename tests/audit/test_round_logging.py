"""Official round logging on every path (DR-07; IDEA-042 item 3, criteria L1-L7)."""

import json

from larp.audit.delivery import DeliveryWorker
from larp.audit.protocol import build_event
from larp.contracts import ContractError, Document
from larp.runtime.coordinator import Coordinator
from larp.runtime.fixtures import FakeAssessor, FakeExecution, FakePlanner, FakePolicy, FakeReceiver, settle
from larp.storage.postgres import doc
from tests.support import DatabaseCase, request

NOW = 1791590400000
ADDRESS = '0x' + '1' * 40
TX = '0x' + 'b' * 64


class Raising:
    def __init__(self, method):
        setattr(self, method, self.fail)

    @staticmethod
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic failure')


class Planned:
    """A planner returning fixed intents and reservations in the runtime vocabulary."""

    def __init__(self, intents, reservations):
        self.intents, self.reservations = intents, reservations

    def plan(self, snapshot, proposal):
        return doc(dict(schema='PlanResult.v1', snapshot_id=snapshot.snapshot_id, reasons=['SYNTHETIC'],
                        intents=self.intents, reservation_deltas=self.reservations, proposed_state={}, jobs=[]))


def intent(identity, symbol='NVDAB', side='BUY', amount='10', **extra):
    return dict(intent_id='intent:' + identity, decision_id='decision:' + identity, symbol=symbol, side=side,
                amount=amount, pay_units=10, receive_units=2, gas_units=1, expires_ms=NOW + 60000, **extra)


class ModelAssessor(FakeAssessor):
    def __init__(self, cot, steps=1):
        self.cot, self.steps = cot, steps

    def assess(self, req):
        value = super().assess(req).read()
        value['model_io'] = dict(steps=[dict(request={}, response={'reasoning_summary': None})] * self.steps,
                                 tool_calls=[], cot=self.cot)
        return doc(value)


def mapping_reducer(current, observation):
    """Maps the swap hash on broadcast; releases the round's reservations on the final fact."""
    c, o = current.read(), observation.read()
    projection = c['projection']
    record = projection['round_records'][o['round_id']]
    item = record['plan']['intents'][0]
    if o['kind'] == 'BROADCAST_ATTEMPTED':
        record['orders'][0]['tx_hash'] = o['tx_hash']
        record['swap_mappings'].append(dict(tx_hash=o['tx_hash'], decision_id=item['decision_id'], step='swap'))
        return doc(dict(projection=projection, reservation_deltas=[]))
    return doc(dict(projection=projection, reservation_deltas=[
        dict(intent_id=r['intent_id'], asset=r['asset'], units=-r['units']) for r in c['reservations']]))


class RoundLogging(DatabaseCase):
    def coordinator(self, *, assessor=None, planner=None, builder=None, test_rounds=False):
        return Coordinator(self.store, assessor or FakeAssessor(), FakePolicy(), planner or FakePlanner(),
                           execution=FakeExecution(), run_id='run', version_id='synthetic', profile_hash='a' * 64,
                           address=ADDRESS, clock_ms=lambda: NOW, context_builder=builder, test_rounds=test_rounds)

    def events(self, round_id):
        with self.store.transaction() as db:
            return [Document(bytes(r[0])).read() for r in db.execute(
                'SELECT document FROM audit_events WHERE run_id=%s AND round_id=%s', ('run', round_id))]

    def one_log(self, round_id):
        events = self.events(round_id)
        self.assertEqual(len(events), 1, 'exactly one log per round')
        log = json.loads(events[0]['log'])['data']
        for key in ('input', 'cot', 'output'):
            self.assertTrue(log[key], key)
        return events[0], log

    def commands(self, round_id):
        """Execution commands committed for the round (each test runs one round per run)."""
        with self.store.transaction() as db:
            return db.execute('SELECT count(*) FROM commands WHERE run_id=%s', ('run',)).fetchone()[0]

    # ---------------------------------------------------------------- L3: every path closes with exactly one log
    def test_l3_hold(self):
        self.coordinator().start('r', request('HOLD'), NOW)
        _, log = self.one_log('r')
        self.assertEqual(log['orders'], [])
        self.assertEqual(log['output']['status'], 'COMPLETE')

    def test_l3_assessment_unavailable(self):
        self.coordinator(assessor=Raising('assess')).start('r', request('BUY'), NOW)
        _, log = self.one_log('r')
        self.assertIn('ASSESSMENT_UNAVAILABLE', log['output']['errors'])
        self.assertTrue(log['cot'].startswith('No model call this round. Assessment unavailable'))

    def test_l3_context_unavailable(self):
        def builder(*args):
            raise ValueError('market port down')
        self.coordinator(builder=builder).start('r', request('BUY'), NOW)
        _, log = self.one_log('r')
        self.assertIn('CONTEXT_UNAVAILABLE:ValueError', log['output']['errors'])
        self.assertEqual(log['orders'], [])

    def test_l3_planner_unavailable(self):
        self.coordinator(planner=Raising('plan')).start('r', request('BUY'), NOW)
        _, log = self.one_log('r')
        self.assertIn('PLANNER_UNAVAILABLE', log['output']['errors'])

    def test_l3_plan_invalid_and_bnb_in_a_trade_round(self):
        planner = Planned([intent('x', symbol='BNB')], [dict(intent_id='intent:x', asset='USDT', units=10)])
        self.coordinator(planner=planner).start('r', request('BUY'), NOW)
        _, log = self.one_log('r')
        self.assertIn('PLAN_INVALID', log['output']['errors'])
        self.assertEqual((log['orders'], self.commands('r')), ([], 0))

    def test_l3_commit_rejected(self):
        planner = Planned([intent('x')], [dict(intent_id='intent:x', asset='USDT', units=1000)])  # > balance
        self.coordinator(planner=planner).start('r', request('BUY'), NOW)
        _, log = self.one_log('r')
        self.assertIn('COMMIT_REJECTED', log['output']['errors'])
        self.assertEqual((log['orders'], log['output']['status']), ([], 'REJECTED'))

    def test_l3_interrupted_round_closed_by_recovery(self):
        self.store.open_round('run', 'r', request('BUY'), self.epoch)
        self.coordinator().recover(NOW)
        _, log = self.one_log('r')
        self.assertEqual(log['output']['status'], 'INTERRUPTED_UNRESOLVED')

    def test_l3_l2_executed_round_logs_its_swap(self):
        c = self.coordinator()
        c.start('r', request('BUY'), NOW)
        c.observe('b', doc(dict(kind='BROADCAST_ATTEMPTED', observation_id='b', round_id='r', tx_hash=TX,
                                simulated=True)), settle)
        c.observe('f', doc(dict(kind='FINAL_SUCCESS', observation_id='f', round_id='r', tx_hash=TX,
                                simulated=True)), settle)
        c.recover(NOW + 1)
        event, log = self.one_log('r')
        self.assertEqual(log['orders'], [dict(symbol='NVDAB', side='BUY', amount='10', tx_hash=TX)])
        self.assertEqual(log['input']['decision_ids'], ['decision:job'])
        self.assertNotIn('round_kind', event)  # trade rounds keep the existing envelope bytes

    def test_l3_l4_gas_topup_round(self):
        top = intent('gas', symbol='BNB', amount='1', purpose='GAS_TOPUP')
        planner = Planned([top], [dict(intent_id='intent:gas', asset='USDT', units=1)])
        c = self.coordinator(planner=planner)
        c.start('g', request('BUY'), NOW)
        c.observe('b', doc(dict(kind='BROADCAST_ATTEMPTED', observation_id='b', round_id='g', tx_hash=TX,
                                simulated=True)), mapping_reducer)
        c.observe('f', doc(dict(kind='FINAL_SUCCESS', observation_id='f', round_id='g', tx_hash=TX,
                                simulated=True)), mapping_reducer)
        c.recover(NOW + 1)
        event, log = self.one_log('g')
        self.assertEqual(event['round_kind'], 'GAS_TOPUP')
        self.assertEqual(log['orders'], [dict(symbol='BNB', side='BUY', amount='1', tx_hash=TX)])
        self.assertTrue(log['cot'].startswith('Gas top-up round'))

    def test_l4_a_top_up_mixed_with_trades_is_refused(self):
        planner = Planned([intent('gas', symbol='BNB', amount='1', purpose='GAS_TOPUP'), intent('x')],
                          [dict(intent_id='intent:x', asset='USDT', units=10)])
        self.coordinator(planner=planner).start('r', request('BUY'), NOW)
        _, log = self.one_log('r')
        self.assertIn('PLAN_INVALID', log['output']['errors'])

    def test_l4_verify_refuses_bnb_outside_a_gas_round(self):
        common = dict(event_id='evt-1-abc', round_id='r', version_id='v', decision_ids=['d'], address=ADDRESS,
                      timestamp_ms=NOW, input_record={'x': 1}, rationale='r', output={'y': 1})
        bnb = [dict(symbol='BNB', side='BUY', amount='1')]
        with self.assertRaises(ContractError):
            build_event(orders=bnb, **common)
        with self.assertRaises(ContractError):
            build_event(orders=bnb + [dict(symbol='NVDAB', side='BUY', amount='1')], round_kind='GAS_TOPUP',
                        **common)
        with self.assertRaises(ContractError):
            build_event(orders=[dict(symbol='BNB', side='SELL', amount='1')], round_kind='GAS_TOPUP', **common)
        build_event(orders=bnb, round_kind='GAS_TOPUP', **common)

    # ---------------------------------------------------------------- L1: cot and input content
    def test_l1_cot_is_the_providers_summaries_in_order(self):
        self.coordinator(assessor=ModelAssessor(['first step', 'second step'])).start('r', request('HOLD'), NOW)
        _, log = self.one_log('r')
        self.assertEqual(log['cot'], ['first step', 'second step'])
        self.assertEqual(log['input']['assessment']['model_io']['cot'], ['first step', 'second step'])

    def test_l1_model_without_summary_is_not_called_no_model(self):
        self.coordinator(assessor=ModelAssessor([])).start('r', request('HOLD'), NOW)
        _, log = self.one_log('r')
        self.assertTrue(log['cot'].startswith('Model called; the provider returned no reasoning summary'))

    def test_l1_deterministic_round_says_no_model_call(self):
        self.coordinator().start('r', request('HOLD'), NOW)
        _, log = self.one_log('r')
        self.assertTrue(log['cot'].startswith('No model call this round. Deterministic assessment'))
        self.assertEqual(log['input']['version_id'], 'synthetic')

    # ---------------------------------------------------------------- L5, L6
    def test_l5_test_rounds_are_marked_only_when_asked(self):
        self.coordinator(test_rounds=True).start('t', request('HOLD'), NOW)
        self.coordinator().start('u', request('HOLD', job='other'), NOW)
        self.assertIs(self.one_log('t')[1]['input']['example'], True)
        self.assertNotIn('example', self.one_log('u')[1]['input'])

    def test_l6_oversize_round_logs_once_and_places_nothing(self):
        class Huge(FakeAssessor):
            def assess(self, req):
                value = super().assess(req).read()
                value['rationale'] = 'x' * (5 * 1024 * 1024)
                return doc(value)
        self.coordinator(assessor=Huge()).start('r', request('BUY'), NOW)
        _, log = self.one_log('r')
        self.assertEqual((log['orders'], self.commands('r')), ([], 0))
        self.assertIn('AUDIT_CONTENT_UNSUPPORTED', log['output']['errors'])

    # ---------------------------------------------------------------- L7: delivery proof
    def test_l7_delivered_only_with_every_chunk_acknowledged(self):
        empty = DeliveryWorker(self.store, FakeReceiver()).status('run')
        self.assertEqual((empty['events'], empty['pending_chunks'], empty['delivered']), ({}, 0, []))
        self.coordinator().start('r', request('HOLD'), NOW)
        receiver = FakeReceiver(lose_ack=True)
        worker = DeliveryWorker(self.store, receiver, retry_ms=1)
        (event_id,) = [e['event_id'] for e in self.events('r')]
        self.assertEqual(worker.status('run')['events'], {event_id: 'PENDING'})
        worker.once('run', self.epoch, NOW + 1)  # stored remotely, acknowledgement lost
        self.assertEqual(worker.status('run')['events'], {event_id: 'PENDING'})
        first = dict(receiver.stored)
        worker.once('run', self.epoch, NOW + 2)  # resend: same event ID and bytes (FakeReceiver refuses changes)
        self.assertEqual(receiver.stored, first)
        status = worker.status('run')
        self.assertEqual((status['events'], status['delivered'], status['pending_chunks']),
                         ({event_id: 'DELIVERED'}, [event_id], 0))

    def test_l7_refused_upload_stays_visible(self):
        self.coordinator().start('r', request('HOLD'), NOW)
        worker = DeliveryWorker(self.store, FakeReceiver(code=400), retry_ms=1)
        worker.once('run', self.epoch, NOW + 1)
        status = worker.status('run')
        self.assertEqual(list(status['events'].values()), ['FAILED'])
        self.assertEqual((status['delivered'], status['pending_chunks']), ([], 0))  # empty outbox, not delivered

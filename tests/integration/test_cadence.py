"""IDEA-044 C09: economic submissions consume the persisted session allowance."""
from datetime import datetime, timezone
from larp.contracts import Document
from larp.integration.replay import replay_live
from larp.integration.runtime import RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection
from larp.integration.settlement import ExecutionBridge, settle
from larp.storage.postgres import doc
from tests.integration import test_evidence_pipeline as pipeline
from tests.integration.test_settlement import observation

RUN = pipeline.RUN


class Cadence(pipeline.PipelineHarness):
    def runtime(self, authority='DISCRETIONARY_EXIT'):
        c = self.coordinator(authority)
        c.execution = ExecutionBridge()
        def market(now):
            values = self.market(now)
            for m in values:
                for q in m['quotes']:
                    q['quoted_depth_units'] = 200000
            return values
        c.context_builder.market = market
        return c

    def intent(self, name):
        return self.store.load(RUN).read()['projection']['round_records'][name]['plan']['intents'][0]

    def send(self, c, intent, name, event, kind, **fields):
        fields.setdefault('observed_at', datetime.fromtimestamp(self.w.clock() / 1000, timezone.utc).isoformat())
        o = observation(intent, name, event, kind, **fields)
        return c.observe(event, Document.from_dict(o), settle)

    def test_discretionary_broadcast_survives_restart_blocks_repeat_and_replays(self):
        c = self.runtime()
        self.round(c, 'first', 'EXSEMI_402_8K')
        intent = self.intent('first')
        self.assertFalse(intent['mandatory'])
        self.send(c, intent, 'first', 'broadcast', 'BROADCAST_ATTEMPTED')
        self.assertEqual(self.store.load(RUN).read()['projection']['last_discretionary_session'], 80)

        self.send(c, intent, 'first', 'revert', 'REVERT')
        c.close('first', self.w.clock(), 'COMPLETE')
        restarted = self.runtime()
        self.round(restarted, 'second', 'EXSEMI_402_8K')
        self.assertEqual(len(self.commands()), 1)
        records = [b.read()['event'].get('record', {}) for b in self.store.journal(RUN)]
        second = next(r for r in records if r.get('round_id') == 'second')
        self.assertIn('DISCRETIONARY_CADENCE', second['plan']['reasons'])
        journal, expected = self.store.journal(RUN), self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        actual = replay_live(journal, doc(initial_projection(pipeline.pipeline_ledger())), self.store,
            builder=restarted.context_builder, run_id=RUN, wallet_id='fake-wallet', chain_id=56,
            version_id='integration-fixture', profile_hash=self.h, address='0x' + '1' * 40,
            policy=StrategyPolicy(), planner=RuntimePlanner(job_validity_ms=86400000, job_max_attempts=3),
            execution=ExecutionBridge(), reducer=settle, initial_policy_state=initial_policy_state(RUN, self.profile))
        self.assertEqual(actual, expected)
        self.assertEqual(self.store.load(RUN).read()['projection']['last_discretionary_session'], 80)

    def test_broadcast_after_session_boundary_consumes_actual_session(self):
        c = self.runtime()
        started = self.w.clock()
        self.round(c, 'boundary', 'EXSEMI_402_8K')
        intent = self.intent('boundary')
        at = datetime.fromtimestamp((started + 1000) / 1000, timezone.utc).isoformat()
        self.send(c, intent, 'boundary', 'broadcast', 'BROADCAST_ATTEMPTED', observed_at=at)
        self.send(c, intent, 'boundary', 'revert', 'REVERT', observed_at=at)
        c.close('boundary', started + 1000, 'COMPLETE')
        current = self.store.load(RUN).read()
        c.context_builder.calendar = lambda ms: {'index': 80 if ms < started + 1000 else 81, 'remaining': 10}
        context, updates = c.context_builder(current, {}, None, started + 2000)
        self.assertEqual(context['last_discretionary_session'], 81)
        self.assertEqual(updates['last_discretionary_session'], 81)
        from larp.integration.replay import RecordedPorts
        recorded = RecordedPorts(c.context_builder).builder_for({'policy_input': {'context': context}})
        c.context_builder.calendar = lambda ms: (_ for _ in ()).throw(AssertionError('live calendar used'))
        replayed, replay_updates = recorded(current, {}, None, started + 2000)
        self.assertEqual(replayed, context)
        self.assertEqual(replay_updates, updates)

    def test_approval_and_unsigned_abort_do_not_consume_cadence(self):
        c = self.runtime()
        self.round(c, 'unsigned', 'EXSEMI_402_8K')
        intent = self.intent('unsigned')
        self.send(c, intent, 'unsigned', 'approve', 'BROADCAST_ATTEMPTED', step='approve')
        self.assertIsNone(self.store.load(RUN).read()['projection']['last_discretionary_session'])
        self.send(c, intent, 'unsigned', 'approved', 'APPROVAL', step='approve')
        self.send(c, intent, 'unsigned', 'aborted', 'NOT_SUBMITTED')
        self.assertIsNone(self.store.load(RUN).read()['projection']['last_discretionary_session'])

    def test_mandatory_broadcast_does_not_consume_discretionary_allowance(self):
        c = self.runtime('MANDATORY_REDUCTION')
        self.round(c, 'mandatory', 'EXSEMI_402_8K')
        intent = self.intent('mandatory')
        self.assertTrue(intent['mandatory'])
        self.send(c, intent, 'mandatory', 'broadcast', 'BROADCAST_ATTEMPTED')
        self.assertIsNone(self.store.load(RUN).read()['projection']['last_discretionary_session'])

    def test_future_dated_broadcast_blocks_only_discretionary_cadence(self):
        # An execution-host clock step must not make every later context unavailable (which
        # would also stop mandatory reductions); it spends the current session's allowance.
        c = self.runtime()
        started = self.w.clock()
        self.round(c, 'clock-step', 'EXSEMI_402_8K')
        intent = self.intent('clock-step')
        future = datetime.fromtimestamp((started + 10 * 86400000) / 1000, timezone.utc).isoformat()
        self.send(c, intent, 'clock-step', 'broadcast', 'BROADCAST_ATTEMPTED', observed_at=future)
        self.send(c, intent, 'clock-step', 'revert', 'REVERT', observed_at=future)
        c.close('clock-step', started + 1000, 'COMPLETE')
        current = self.store.load(RUN).read()
        c.context_builder.calendar = lambda ms: {'index': 80 if ms < started + 1000 else 81, 'remaining': 10}
        context, updates = c.context_builder(current, {}, None, started + 2000)
        self.assertEqual((context['session_index'], context['last_discretionary_session']), (81, 81))
        self.assertEqual(updates['last_discretionary_session'], 81)
        from larp.integration.replay import RecordedPorts
        recorded = RecordedPorts(c.context_builder).builder_for({'policy_input': {'context': context}})
        c.context_builder.calendar = lambda ms: (_ for _ in ()).throw(AssertionError('live calendar used'))
        replayed, _ = recorded(current, {}, None, started + 2000)
        self.assertEqual(replayed, context)

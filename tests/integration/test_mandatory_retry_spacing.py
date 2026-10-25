"""IDEA-102 MC7/8: durable retry slots, historical replay and eight aborted exits on real PostgreSQL."""
from datetime import datetime, timezone

from larp.contracts import Document
from larp.integration.runtime import initial_projection
from larp.integration.settlement import settle
from larp.research.fixtures import changed, with_quotes
from larp.storage.postgres import doc
from tests.integration.test_execution_bounds import DurableBudget as _DurableBudget, unclaimed_fact
from tests.strategy.test_execution_bounds import at
from tests.strategy.test_mandatory_retry_spacing import LEG, SLOT


class MandatoryRetry(_DurableBudget):
    test_quote_child_reuses_parent_and_replays_from_the_parent_journal = None
    test_closed_rounds_restart_and_duplicate_round_cannot_restore_attempts = None
    test_budget_survives_midnight_weekend_and_resets_at_next_open = None
    test_exact_replay_reconstructs_budget_without_live_calendar_or_market = None

    def setUp(self):
        super().setUp()
        self.template = at('2026-10-12T14:00:00Z', held={'NVDAB': 2000}, profile_changes={
            'new_risk_end': '2026-10-12T12:00:00Z', 'flatten_start': '2026-10-12T13:00:00Z'})
        self.template = changed(self.template, execution_session=self.calendar.window(self.now))
        self.context = self.template.context.read()
        self.profile = self.context['profile']
        self.h = Document.from_dict(self.profile).digest('StrategyProfile.v1')
        self.initial = initial_projection(self.context['portfolio'])
        self.initial['portfolio']['risk']['day'] = '2026-10-09'
        self.initial['portfolio']['run_id'] = 'run'
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        self.store.initialize('run', 'fake-wallet', 56, doc(self.initial))
        self.store.takeover('run', 1, offline=True)

    def child(self, coordinator, name):
        self.quote_template = None
        self.start(coordinator, name)
        self.quote_template = next(m['quotes'] for m in with_quotes(self.template).context.read()['markets']
                                   if m['symbol'] == 'NVDAB')
        self.start(coordinator, name + '/quote1', parent=name)
        return self.store.load('run').read()['projection']['round_records'][name + '/quote1']['plan']['intents'][0]

    def abort(self, coordinator, intent, name):
        coordinator.observe(name + '-abort', doc(unclaimed_fact(intent, name + '/quote1', name + '-abort', self.now,
            reason='PRICE_CHECK_ABORT')), settle)
        coordinator.close(name + '/quote1', self.now, 'COMPLETE')

    def test_mc7_historical_journal_retains_old_budget_and_replays_with_new_builder(self):
        coordinator = self.coordinator()
        coordinator.context_builder.execution_attempt_policy = None  # produce historical-format journal
        for n in range(3):
            intent = self.child(coordinator, 'legacy' + str(n))
            self.assertEqual(intent['execution_bounds']['ordinal'], n + 1)
            self.abort(coordinator, intent, 'legacy' + str(n))
        self.start(coordinator, 'legacy-capped')
        record = self.store.event('run', 'plan:legacy-capped')['record']
        self.assertIn('LEG_ATTEMPT_LIMIT', record['plan']['reasons'])
        self.assertNotIn('last_ms', record['plan']['execution_attempt_budget'])
        self.assertNotIn('execution_attempt_policy', record['policy_input']['context'])
        coordinator.context_builder = self.coordinator().context_builder  # current default builder
        self.assert_replay(coordinator)

    def test_mc8_eight_price_aborts_then_fill_to_dust_survive_restart_and_exact_replay(self):
        coordinator = self.coordinator()
        for n in range(8):
            name = 'attempt' + str(n)
            intent = self.child(coordinator, name)
            self.assertEqual(intent['execution_bounds']['ordinal'], n + 1)
            self.abort(coordinator, intent, name)
            self.start(coordinator, name + '-same-slot')
            record = self.store.event('run', 'plan:' + name + '-same-slot')['record']
            self.assertIn('MANDATORY_RETRY_SPACING', record['plan']['reasons'])
            self.assertFalse(record['plan']['quote_requests'])
            self.now += SLOT
            coordinator = self.coordinator()  # restarts cannot restore slot authority
        intent = self.child(coordinator, 'filled')
        self.assertEqual(intent['execution_bounds']['ordinal'], 9)
        from larp.execution_live.service import map_command
        from larp.strategy.execution_bounds import permitted
        mapped = map_command(dict(kind='EXECUTION_REQUEST', command_id=intent['intent_id'], payload=intent,
            round_id='filled/quote1', decision_id=intent['decision_id'], expires_ms=intent['expires_ms']),
            run_id='run', wallet='0x'+'1'*40, version_id='fixture-build', router='0x'+'2'*40,
            token_decimals={m['symbol']: m['decimals'] for m in self.context['markets']}, now_ms=self.now,
            limits=dict(per_trade_cap_units=self.profile['per_trade_cap_units'], max_gas=100000,
                        max_gas_price=1, gas_budget=100000))
        self.assertTrue(permitted(self.store.load('run').read()['projection'], mapped, self.now))
        tx = '0x' + 'a'*64
        base = dict(schema='ExecutionObservation.v1', run_id='run', wallet_id='fake-wallet',
                    round_id='filled/quote1', intent_id=intent['intent_id'],
                    observed_at=datetime.fromtimestamp(self.now/1000, timezone.utc).isoformat(), tx_hash=tx)
        coordinator.observe('broadcast', doc(dict(base, event_id='broadcast', kind='BROADCAST_ATTEMPTED', step='swap')), settle)
        coordinator.observe('fill', doc(dict(base, event_id='fill', kind='FILL', settlement='FINAL', origin='SCRIPTED_FAKE',
            block_hash='0x'+'b'*64, canonical=True, gas_bnb_units=10000, gas_value_units=10000,
            intent_terminal=True, round_terminal=True, symbol=intent['symbol'], side='SELL',
            token_units=intent['token_units'], cash_units=intent['cash_units'], fee_units=intent['fee_units'])), settle)
        coordinator.close('filled/quote1', self.now, 'COMPLETE')
        projection = self.store.load('run').read()['projection']
        self.assertLessEqual(projection['portfolio']['positions']['NVDAB']['units'], self.profile['dust_units'])
        self.assertEqual(projection['execution_attempt_budget']['counts'][LEG], 9)
        self.assertFalse(self.store.load('run').read()['reservations'])
        self.assert_replay(coordinator)

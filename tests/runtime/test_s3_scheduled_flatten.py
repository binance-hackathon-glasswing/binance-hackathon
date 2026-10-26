"""PR277-RV01 RV2: real PostgreSQL/ContextBuilder/coordinator/settlement/replay, synthetic external ports only."""
from copy import deepcopy
from datetime import datetime, timezone

from larp.contracts import Document
from larp.integration.replay import replay_live
from larp.integration.runtime import (ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state,
                                      initial_projection, ledger_from)
from larp.integration.settlement import ExecutionBridge, settle
from larp.runtime.coordinator import Coordinator
from larp.storage.postgres import doc
from tests.integration.test_settlement import observation
from tests.strategy.test_execution_bounds import at, milliseconds
from tests.strategy.test_s3_scheduled_flatten import AFTER_CLOSE, S3
from larp.research.fixtures import with_quotes
from tests.support import DatabaseCase, request

RUN = 'synthetic-run'


class ScheduledFlattenPersistence(DatabaseCase):
    def coordinator(self):
        return Coordinator(self.store, None, StrategyPolicy(),
            RuntimePlanner(job_validity_ms=60000, job_max_attempts=3), execution=ExecutionBridge(),
            run_id=RUN, version_id='s3-review-fixture', profile_hash=self.profile_hash, address='0x' + '1' * 40,
            context_builder=self.builder, initial_policy_state=initial_policy_state(RUN, self.profile),
            clock_ms=lambda: self.now)

    def start(self, coordinator, name):
        req = request(job=name, cutoff=self.now).read()
        req.update(run_id=RUN, policy_profile_hash=self.profile_hash, evidence_refs=[])
        coordinator.start(name, doc(req), self.now, use_accepted_evidence=True)
        return self.store.event(RUN, 'plan:' + name)['record']['plan']

    def test_done_survives_commit_restart_buy_settlement_and_exact_replay(self):
        fixture = with_quotes(at(AFTER_CLOSE, profile_changes=S3))
        context = fixture.context.read()
        self.profile, self.profile_hash = context['profile'], fixture.policy_profile_hash
        self.now = milliseconds(AFTER_CLOSE)
        initial = initial_projection(context['portfolio'])
        self.store.initialize(RUN, 'fake-wallet', 56, doc(initial))
        self.store.takeover(RUN, 1, offline=True)

        def market(now):
            rows = deepcopy(context['markets'])
            stamp = datetime.fromtimestamp(now / 1000, timezone.utc).isoformat()
            for row in rows:
                for field in ('observed_at', 'available_at', 'close_at'):
                    row[field] = stamp
            return rows

        def calendar(now):
            return dict(index=80, remaining=10)
        calendar.window = lambda now: context['execution_session']
        self.builder = ContextBuilder(profile=self.profile, profile_hash=self.profile_hash, run_id=RUN,
            issuers={}, market=market, health=lambda current: context['health'], calendar=calendar)
        coordinator = self.coordinator()
        first = self.start(coordinator, 'flat')
        self.assertEqual(first['risk_state']['scheduled_flatten'], 'DONE')
        self.assertTrue(first['intents'], first)
        planned = first['intents'][0]
        self.assertEqual(planned['side'], 'BUY')
        self.assertEqual(self.store.load(RUN).read()['projection']['risk_state']['scheduled_flatten'], 'DONE')
        coordinator = self.coordinator()  # new object reloads the committed state and reservations
        for event, kind, fields in (
            ('broadcast', 'BROADCAST_ATTEMPTED', {}),
            ('fill', 'FILL', dict(symbol=planned['symbol'], side='BUY', token_units=planned['min_receive_units'],
                                 cash_units=planned['pay_units'], fee_units=0))):
            o = observation(planned, 'flat', event, kind, observed_at=AFTER_CLOSE, **fields)
            coordinator.observe(event, Document.from_dict(o), settle)
        coordinator.close('flat', self.now, 'COMPLETE')
        current = self.store.load(RUN).read()
        ledger = ledger_from(current['projection'], current['reservations'])
        self.assertGreater(ledger['positions'][planned['symbol']]['units'], 0)
        self.assertEqual(ledger['risk']['scheduled_flatten'], 'DONE')
        self.now += 1000
        second = self.start(self.coordinator(), 'rebuilt')
        self.assertEqual(second['risk_state']['scheduled_flatten'], 'DONE')
        self.assertFalse(any('SCHEDULED_FLATTEN' in r['reasons'] for r in second['requirements']))

        journal, expected = self.store.journal(RUN), self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        dead = lambda *a: (_ for _ in ()).throw(AssertionError('external port called in replay'))
        self.builder.market = self.builder.health = self.builder.calendar = dead
        actual = replay_live(journal, doc(initial), self.store, builder=self.builder, run_id=RUN,
            wallet_id='fake-wallet', chain_id=56, version_id='s3-review-fixture', profile_hash=self.profile_hash,
            address='0x' + '1' * 40, policy=StrategyPolicy(),
            planner=RuntimePlanner(job_validity_ms=60000, job_max_attempts=3), execution=ExecutionBridge(),
            reducer=settle, initial_policy_state=initial_policy_state(RUN, self.profile))
        self.assertEqual(actual, expected)
        self.assertEqual(self.store.load(RUN).read()['projection']['risk_state']['scheduled_flatten'], 'DONE')

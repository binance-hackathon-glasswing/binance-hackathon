"""IDEA-103: fetched five-name history is journaled and replays with every external port disabled."""
from larp.contracts import Document
from larp.integration.replay import replay_live
from larp.integration.runtime import ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection
from larp.integration.settlement import ExecutionBridge, settle
from larp.research.fixtures import changed, with_quotes
from larp.runtime.coordinator import Coordinator
from larp.runtime.driver import SessionCalendar
from larp.runtime.fixtures import FakeAssessor
from larp.storage.postgres import doc
from tests.marketdata.test_session_history import NOW, Port, reader, rows, CALENDAR
from tests.strategy.test_history_trend import snapshot
from tests.support import DatabaseCase, request


class HistoryReplay(DatabaseCase):
    def test_history_driven_sale_replays_exactly_without_network_or_cache(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            s = snapshot()
            profile = s.context.read()['profile']
            history = reader(root,Port(source=rows(prices=(100,99,98,97,90,90))),profile=profile)
            s = with_quotes(changed(s,series=history(NOW)))
            context = s.context.read()
            ph = Document.from_dict(profile).digest('StrategyProfile.v1')
            initial = initial_projection(context['portfolio'])
            with self.store.transaction() as db:
                db.execute('TRUNCATE runs CASCADE')
            self.store.initialize(s.run_id,s.wallet_id,56,doc(initial))
            self.store.takeover(s.run_id,1,offline=True)
            builder = ContextBuilder(profile=profile,profile_hash=ph,run_id=s.run_id,issuers={},
                market=lambda _:context['markets'],health=lambda _:context['health'],calendar=SessionCalendar(CALENDAR),
                series=history)
            planner = RuntimePlanner(job_validity_ms=60000,job_max_attempts=3,issuers={})
            coordinator = Coordinator(self.store,FakeAssessor(),StrategyPolicy(),planner,execution=ExecutionBridge(),
                run_id=s.run_id,version_id='synthetic-history',profile_hash=ph,address='0x'+'1'*40,
                context_builder=builder,initial_policy_state=initial_policy_state(s.run_id,profile),clock_ms=lambda:NOW)
            req = request(job='history',cutoff=NOW).read()
            req.update(run_id=s.run_id,policy_profile_hash=ph)
            coordinator.start('history',doc(req),NOW)
            record = self.store.event(s.run_id,'plan:history')['record']
            assert record['plan']['intents'],record
            assert record['plan']['intents'][0]['side'] == 'SELL'
            assert record['policy_input']['context']['series'] == history(NOW)
            item = record['plan']['intents'][0]
            coordinator.observe('abort',doc(dict(schema='ExecutionObservation.v1',run_id=s.run_id,wallet_id=s.wallet_id,
                round_id='history',intent_id=item['intent_id'],event_id='abort',kind='NOT_SUBMITTED',settlement='FINAL',
                origin='EXECUTION_RECONCILER',observed_at=s.observed_at.isoformat(),intent_terminal=True,
                round_terminal=True,reason='SYNTHETIC_NO_BROADCAST')),settle)
            coordinator.close('history',NOW,'COMPLETE')
            batches,expected = self.store.journal(s.run_id),self.store.verify(s.run_id)
            def dead(*args): raise AssertionError('Replay called live history/market/calendar')
            builder.market=builder.calendar=builder.series=builder.health=dead
            with self.store.transaction() as db:
                db.execute('TRUNCATE runs CASCADE')
            actual = replay_live(batches,doc(initial),self.store,builder=builder,run_id=s.run_id,wallet_id=s.wallet_id,
                chain_id=56,version_id='synthetic-history',profile_hash=ph,address='0x'+'1'*40,policy=StrategyPolicy(),
                planner=planner,execution=ExecutionBridge(),reducer=settle,
                initial_policy_state=initial_policy_state(s.run_id,profile))
            assert actual == expected

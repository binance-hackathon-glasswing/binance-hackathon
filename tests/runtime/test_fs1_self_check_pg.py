"""IDEA-093 SC-8: the activation self-check on real PostgreSQL: BUY, restart, SELL, DONE and exact replay."""
from copy import deepcopy

from larp.contracts import Document
from larp.integration.replay import replay_live
from larp.integration.runtime import (ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state,
                                      initial_projection, ledger_from)
from larp.integration.settlement import ExecutionBridge, settle
from larp.research.fixtures import changed, with_quotes
from larp.runtime.coordinator import Coordinator
from larp.storage.postgres import doc
from tests.integration.test_settlement import observation
from tests.strategy.test_equal_weight import with_state
from tests.strategy.test_fs1_self_check import DURING, at_time
from tests.support import DatabaseCase, request

RUN = 'synthetic-run'


class SelfCheckPersistence(DatabaseCase):
    def test_sc8_buy_restart_sell_done_and_exact_replay(self):
        fixture = at_time(DURING)
        context = fixture.context.read()
        p, ph = context['profile'], fixture.policy_profile_hash
        now = int(fixture.observed_at.timestamp() * 1000)
        initial = initial_projection(context['portfolio'])
        self.store.initialize(RUN, 'fake-wallet', 56, doc(initial))
        self.store.takeover(RUN, 1, offline=True)
        rows = []

        def calendar(_):
            return dict(index=context['session_index'], remaining=10)
        calendar.window = lambda _: context['execution_session']
        builder = ContextBuilder(profile=p, profile_hash=ph, run_id=RUN, issuers={},
            market=lambda _: deepcopy(rows), health=lambda _: context['health'], calendar=calendar)

        def leg(k):
            current = self.store.load(RUN).read()
            snapshot = changed(fixture, portfolio=ledger_from(current['projection'], current['reservations']))
            if current.get('policy_state'):
                snapshot = with_state(snapshot, current['policy_state']['data'])
            rows[:] = with_quotes(snapshot).context.read()['markets']
            # A new coordinator every leg: everything authoritative comes from PostgreSQL (restart between legs).
            coordinator = Coordinator(self.store, None, StrategyPolicy(),
                RuntimePlanner(job_validity_ms=60000, job_max_attempts=3), execution=ExecutionBridge(),
                run_id=RUN, version_id='fs1-self-check', profile_hash=ph, address='0x' + '1' * 40,
                context_builder=builder, initial_policy_state=initial_policy_state(RUN, p), clock_ms=lambda: now)
            name = 'self-check-' + str(k)
            req = request(job=name, cutoff=now).read()
            req.update(run_id=RUN, policy_profile_hash=ph, evidence_refs=[])
            coordinator.start(name, doc(req), now, use_accepted_evidence=True)
            result = self.store.event(RUN, 'plan:' + name)['record']['plan']
            for planned in result['intents']:
                fill = dict(symbol=planned['symbol'], side=planned['side'], fee_units=0,
                            token_units=planned['min_receive_units'] if planned['side'] == 'BUY' else planned['pay_units'],
                            cash_units=planned['pay_units'] if planned['side'] == 'BUY' else planned['min_receive_units'])
                for kind, fields in [('BROADCAST_ATTEMPTED', {}), ('FILL', fill)]:
                    event = name + '-' + kind
                    o = observation(planned, name, event, kind, observed_at=fixture.observed_at.isoformat(),
                                    tx_hash='0x' + format(k + 1, '064x'), **fields)
                    coordinator.observe(event, Document.from_dict(o), settle)
            coordinator.close(name, now, 'COMPLETE')
            return result

        bought = leg(0)
        assert [(i['symbol'], i['side']) for i in bought['intents']] == [('SKHYB', 'BUY')], bought
        sold = leg(1)
        assert [(i['symbol'], i['side'], i['mandatory']) for i in sold['intents']] == [('SKHYB', 'SELL', True)], sold
        assert sold['risk_state']['activation_self_check'] == 'BOUGHT'
        done = leg(2)
        assert done['risk_state']['activation_self_check'] == 'DONE' and not done['intents']
        settled = self.store.load(RUN).read()
        ledger = ledger_from(settled['projection'], settled['reservations'])
        assert ledger['positions']['SKHYB']['units'] == 0 and not ledger['reservations']
        journal, expected = self.store.journal(RUN), self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        dead = lambda *a: (_ for _ in ()).throw(AssertionError('external port called in replay'))
        builder.market = builder.calendar = builder.health = dead
        actual = replay_live(journal, doc(initial), self.store, builder=builder, run_id=RUN,
            wallet_id='fake-wallet', chain_id=56, version_id='fs1-self-check', profile_hash=ph,
            address='0x' + '1' * 40, policy=StrategyPolicy(),
            planner=RuntimePlanner(job_validity_ms=60000, job_max_attempts=3), execution=ExecutionBridge(),
            reducer=settle, initial_policy_state=initial_policy_state(RUN, p))
        assert actual == expected

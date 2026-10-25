"""PR278-RV01-GAS: final funding shape, recovery, five settled legs, restart and exact PostgreSQL replay."""
from copy import deepcopy

from larp.contracts import Document
from larp.integration.replay import replay_live
from larp.integration.runtime import ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection, ledger_from
from larp.integration.settlement import ExecutionBridge, settle
from larp.research.fixtures import changed, with_quotes
from larp.runtime.coordinator import Coordinator
from larp.storage.postgres import doc
from tests.integration.test_settlement import observation
from tests.strategy.test_equal_weight import with_state
from tests.strategy.test_fs1_review import gas_wallet, NAMES
from tests.support import DatabaseCase, request

RUN = 'synthetic-run'


class Fs1Persistence(DatabaseCase):
    def test_gas_wallet_builds_all_five_after_restart_and_replays_exactly(self):
        fixture = gas_wallet()
        context = fixture.context.read()
        p, ph = context['profile'], fixture.policy_profile_hash
        now = int(fixture.observed_at.timestamp() * 1000)
        initial = initial_projection(context['portfolio'])
        self.store.initialize(RUN, 'fake-wallet', 56, doc(initial))
        self.store.takeover(RUN, 1, offline=True)
        active_rows = []

        def calendar(_):
            return dict(index=context['session_index'], remaining=10)
        calendar.window = lambda _: context['execution_session']
        builder = ContextBuilder(profile=p, profile_hash=ph, run_id=RUN, issuers={},
            market=lambda _: deepcopy(active_rows), health=lambda _: context['health'], calendar=calendar)
        symbols = []
        for k in range(5):
            current = self.store.load(RUN).read()
            ledger = ledger_from(current['projection'], current['reservations'])
            snapshot = changed(fixture, portfolio=ledger)
            if current.get('policy_state'):
                snapshot = with_state(snapshot, current['policy_state']['data'])
            active_rows[:] = with_quotes(snapshot).context.read()['markets']
            # Recreate the coordinator for every leg: all authoritative state must come from PostgreSQL.
            coordinator = Coordinator(self.store, None, StrategyPolicy(),
                RuntimePlanner(job_validity_ms=60000, job_max_attempts=3), execution=ExecutionBridge(),
                run_id=RUN, version_id='fs1-gas-review', profile_hash=ph, address='0x' + '1' * 40,
                context_builder=builder, initial_policy_state=initial_policy_state(RUN, p), clock_ms=lambda: now)
            name = 'gas-leg-' + str(k)
            req = request(job=name, cutoff=now).read()
            req.update(run_id=RUN, policy_profile_hash=ph, evidence_refs=[])
            coordinator.start(name, doc(req), now, use_accepted_evidence=True)
            result = self.store.event(RUN, 'plan:' + name)['record']['plan']
            self.assertFalse(result['risk_state']['run_halt'])
            self.assertEqual(len(result['intents']), 1, result)
            planned = result['intents'][0]
            self.assertEqual(planned['side'], 'BUY')
            self.assertLessEqual(planned['pay_units'], 32_262_000)
            symbols.append(planned['symbol'])
            for kind, fields in [('BROADCAST_ATTEMPTED', {}), ('FILL', dict(symbol=planned['symbol'],
                side='BUY', token_units=planned['min_receive_units'], cash_units=planned['pay_units'], fee_units=0))]:
                event = name + '-' + kind
                o = observation(planned, name, event, kind, observed_at=fixture.observed_at.isoformat(),
                                tx_hash='0x' + format(k + 1, '064x'), **fields)
                coordinator.observe(event, Document.from_dict(o), settle)
            coordinator.close(name, now, 'COMPLETE')
            settled = self.store.load(RUN).read()
            ledger = ledger_from(settled['projection'], settled['reservations'])
            self.assertGreater(ledger['cash_units'], 0)
            self.assertGreaterEqual(ledger['bnb_units'], p['exit_gas_reserve_units'])
        self.assertEqual(set(symbols), set(NAMES))
        self.assertEqual(len(symbols), len(set(symbols)))
        self.assertTrue(all(ledger['positions'][s]['units'] > 0 for s in NAMES))
        journal, expected = self.store.journal(RUN), self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        dead = lambda *a: (_ for _ in ()).throw(AssertionError('external port called in replay'))
        builder.market = builder.calendar = builder.health = dead
        actual = replay_live(journal, doc(initial), self.store, builder=builder, run_id=RUN,
            wallet_id='fake-wallet', chain_id=56, version_id='fs1-gas-review', profile_hash=ph,
            address='0x' + '1' * 40, policy=StrategyPolicy(),
            planner=RuntimePlanner(job_validity_ms=60000, job_max_attempts=3), execution=ExecutionBridge(),
            reducer=settle, initial_policy_state=initial_policy_state(RUN, p))
        self.assertEqual(actual, expected)

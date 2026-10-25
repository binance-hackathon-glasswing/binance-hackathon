"""IDEA-096 AL2/AL3: real coordinator, planner, PostgreSQL execution registry and settlement; synthetic chain."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone

from larp.contracts import Document
from larp.execution import Executor, REVOKE_TOKENS, USDT
from larp.execution_live.service import map_command
from larp.execution_live.store import ExecutionStore
from larp.integration.runtime import ContextBuilder, initial_projection, ledger_from
from larp.integration.settlement import settle
from larp.research.fixtures import with_quotes
from larp.storage.postgres import doc
from tests import execution_fixtures as f
from tests.execution.test_allowance_recovery import Harness, Venue
from tests.execution.test_postgres_execution import ExecutionGuards, RegistrySigner
from tests.execution import test_untrusted_router as u
from tests.integration.test_settlement import observation, command
from tests.runtime.test_s3_scheduled_flatten import ScheduledFlattenPersistence, RUN
from tests.strategy.test_s3_scheduled_flatten import AFTER_CLOSE, S3
from tests.strategy.test_execution_bounds import at, milliseconds
from tests.strategy.test_s1_plan import AT_95, NAMES


class FlattenRecovery(ScheduledFlattenPersistence):
    def test_dirty_stock_and_usdt_reach_flat_through_real_planner_execution_and_settlement(self):
        for dirty in (USDT, u.u.TOKENS - {USDT}):
            with self.subTest(dirty=dirty):
                with self.store.transaction() as db:
                    db.execute('TRUNCATE runs CASCADE')
                fixture = with_quotes(at(AFTER_CLOSE, profile_changes=S3, held={s: AT_95 for s in NAMES}))
                context = fixture.context.read()
                context['portfolio'].update(wallet_id=f.WALLET, bnb_units=10**9, bnb_decimals=18)
                quote_template = next(q for m in context['markets'] for q in m['quotes'] if q['side'] == 'SELL')
                for row in context['markets']:
                    row['quotes'] = [dict(quote_template, quote_id='synthetic-exit-' + row['symbol'])]
                    for quote in row.get('quotes', []):
                        quote['gas_bnb_units'] = 10**7
                self.profile, self.profile_hash = context['profile'], fixture.policy_profile_hash
                self.now = milliseconds(AFTER_CLOSE)
                self.store.initialize(RUN, f.WALLET, 56, doc(initial_projection(context['portfolio'])))
                self.store.takeover(RUN, 1, offline=True)

                def market(now):
                    rows = deepcopy(context['markets'])
                    stamp = datetime.fromtimestamp(now / 1000, timezone.utc).isoformat()
                    for row in rows:
                        row.update(observed_at=stamp, available_at=stamp, close_at=stamp)
                        for quote in row.get('quotes', []):
                            quote.update(observed_at=stamp, available_at=stamp, expires_at=datetime.fromtimestamp(
                                now / 1000 + 600, timezone.utc).isoformat())
                    return rows
                calendar = lambda now: dict(index=80, remaining=10)
                calendar.window = lambda now: context['execution_session']
                self.builder = ContextBuilder(profile=self.profile, profile_hash=self.profile_hash, run_id=RUN,
                    issuers={}, market=market, health=lambda current: context['health'], calendar=calendar)
                registry = ExecutionStore(self.store, run_id=RUN, wallet=f.WALLET)
                registry.install_test_schema()
                h = Harness.__new__(Harness)
                h.store, h.now = registry, self.now // 1000
                h.decoder = u.u.UntrustedRouterDecoder(u.policy())
                h.rpc = u.FakeRpc(h.decoder, f.WALLET, USDT, 0)
                h.decoder.bind(h.rpc)
                tokens = [dirty] if isinstance(dirty, str) else dirty
                for token in tokens:
                    h.rpc.allowances[token] = 123
                class Guards(ExecutionGuards):
                    mode = 'live'
                class Signer(RegistrySigner):
                    mode = 'live'
                class DynamicVenue(Venue):
                    def quote(self, i, nonce):
                        p = super().quote(i, nonce)
                        data = p.data
                        for index, value, inner in ((u.u.AMOUNT, i.amount, False),
                                (u.u.MINIMUM, i.minimum_output, False), (u.u.QUOTED, i.minimum_output, False),
                                (u.u.INNER_AMOUNT, i.amount, True), (u.u.INNER_MINIMUM, i.minimum_output, True)):
                            data = u.u._set_word(data, index, value, inner=inner)
                        return replace(p, data=data)
                h.guards, h.venue = Guards(registry), DynamicVenue(registry)
                h.executor = Executor(registry, h.guards, h.venue, Signer(registry), h.decoder, allowance_recovery=True)
                sold = set()
                for n in range(15):
                    self.now = h.now * 1000
                    c = self.coordinator()
                    name = 'flatten-' + str(n)
                    plan = self.start(c, name)
                    if not plan['intents']:
                        remaining = self.store.load(RUN).read()['projection']['portfolio']['positions']
                        self.assertTrue(all(p['units'] <= self.profile['dust_units'] for p in remaining.values()), plan)
                        break
                    for planned in plan['intents']:
                        self.assertEqual(planned['side'], 'SELL')
                        i = map_command(command(planned, name), run_id=RUN, wallet=f.WALLET,
                            version_id='s3-review-fixture', router=h.decoder.router,
                            token_decimals={s: 4 for s in NAMES}, limits=dict(per_trade_cap_units=50_000_000,
                                max_gas=300000, max_gas_price=10, gas_budget=10**7), now_ms=self.now)
                        h.executor.create(i, h.now)
                        while h.executor._load(i.key).status == 'ACTIVE':
                            state = h.finish_step(i)
                            a = state.attempts[-1]
                            stamp = datetime.fromtimestamp(h.now, timezone.utc).isoformat()
                            identity = a.attempt_id
                            common = dict(run_id=RUN, wallet_id=f.WALLET, observed_at=stamp, tx_hash=a.tx_hash,
                                          attempt_id=identity, step=a.step.lower())
                            maintenance = (dict(maintenance='ALLOWANCE_REVOKE', token_contract=REVOKE_TOKENS[a.step],
                                                spender=i.router, approved_amount='0')
                                           if a.step in REVOKE_TOKENS else {})
                            c.observe(identity + ':send', Document.from_dict(observation(planned, name,
                                identity + ':send', 'BROADCAST_ATTEMPTED', **common, **maintenance)), settle)
                            fill = dict(symbol=planned['symbol'], side='SELL', token_units=planned['token_units'],
                                        cash_units=planned['min_receive_units'], fee_units=0) if a.step == 'SWAP' else {}
                            c.observe(identity + ':final', Document.from_dict(observation(planned, name,
                                identity + ':final', 'FILL' if a.step == 'SWAP' else 'APPROVAL', **common,
                                **maintenance, **fill, gas_bnb_units=a.gas_used, gas_value_units=1,
                                intent_terminal=a.step == 'SWAP',
                                round_terminal=a.step == 'SWAP' and planned == plan['intents'][-1])), settle)
                        sold.add(planned['symbol'])
                    c.close(name, h.now * 1000, 'COMPLETE')
                    h.now += 1
                current = self.store.load(RUN).read()
                ledger = ledger_from(current['projection'], current['reservations'])
                self.assertEqual(sold, set(NAMES))
                self.assertTrue(all(p['units'] <= self.profile['dust_units'] for p in ledger['positions'].values()))
                self.assertFalse(current['reservations'])
                self.assertFalse(any(h.rpc.allowances.values()))

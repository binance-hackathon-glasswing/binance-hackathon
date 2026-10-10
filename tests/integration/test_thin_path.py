"""Step 1 thin path (IDEA-028 RT21): all four real components, external services faked.

Evidence: Yao's EvidenceAssessor over his synthetic filings world (rule baseline model).
Strategy/risk/accounting: Keith's decide, plan and advance_accounting, synthetic profile.
Execution: Isaac's Executor with his fake guards/venue/signer/decoder and SQLite fixture.
Runtime: this coordinator, PostgreSQL store, audit outbox and journal replay.
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile

from larp.contracts import Document
from larp.execution import USDT, Executor, Intent
from larp.integration.settlement import ExecutionBridge, strategy_reducer
from larp.integration.strategy import StrategyContextProvider, StrategyPlanner, balances, on_plan
from larp.intelligence.agent import EMPTY_CONTEXT, build_request
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import EXSEMI, build_world
from larp.research.fixtures import snapshot as strategy_fixture
from larp.risk import planner as keith_planner
from larp.runtime.coordinator import Coordinator
from larp.runtime.replay import replay
from larp.storage.postgres import doc
from larp.strategy import policy as keith_policy
from larp.strategy.schema import floor, value
from tests.execution_fixtures import (ROUTER, WALLET, FakeDecoder, FakeGuards, FakeSigner, FakeVenue,
                                      SQLiteFixture, finalized)
from tests.support import DatabaseCase

RUN, WALLET_ID, ADDRESS = 'thin-run', 'thin-wallet', '0x' + '1' * 40
TOKENS = {  # verbatim from docs/official/kit/bstocks-trading-guide.md
    'NVDAB': '0x02fca66c1d1afb4e2a7884261eb00f63598a7436',
    'GOOGLB': '0x3f53de71c126bdabae20f9cd64848d317f6c3238',
    'SKHYB': '0xca750ef65f295bbecd685abf54e82caf297bdb61',
    'TSLAB': '0x5b1910eaad6450e50f816082aa078c41f10c292f',
    'MSFTB': '0x80106cb3ead06659a5ad19df39d9b4733863b9b0',
}
APPROVE_GAS, SWAP_GAS = 4000, 6000  # BNB units, within the quote's 10000 reservation


class FakeQuotes:
    """Market port fake (same pricing as larp.research.fixtures.with_quotes)."""

    def __init__(self, markets, now, spread_bps=10, gas=10000):
        self.markets, self.now, self.spread, self.gas = {m['symbol']: m for m in markets}, now, spread_bps, gas

    def observe(self, request):
        r = request.read()
        m, pay = self.markets[r['symbol']], r['pay_units']
        if r['side'] == 'BUY':
            cash, q = pay, pay * 10**m['decimals'] * 10000 // (m['price_units'] * (10000 + self.spread))
            minimum = max(1, q * 9980 // 10000)
        else:
            q, cash = pay, floor(value(pay, m)) * (10000 - self.spread) // 10000
            minimum = cash * 9980 // 10000
        return Document.from_dict({
            'quote_id': f"fake-{r['symbol']}-{r['side']}-{pay}", 'side': r['side'], 'token_units': q,
            'amount_kind': 'EXACT_IN', 'pay_asset': r['pay_asset'], 'pay_units': pay, 'min_receive_units': minimum,
            'cash_units': cash, 'fee_units': 0, 'gas_bnb_units': self.gas, 'route_valid': True,
            'slippage_bps': 20, 'impact_bps': self.spread, 'quoted_depth_units': q * 100,
            'available_at': self.now.isoformat(), 'observed_at': self.now.isoformat(),
            'expires_at': (self.now + timedelta(seconds=30)).isoformat(), 'origin': 'SCRIPTED_FAKE'})


class ThinPath:
    """Builds the integrated runtime around one PostgreSQL store (owned by the test case)."""

    def __init__(self, store):
        self.store = store
        self.world = build_world(['EXSEMI_Q2_8K', 'EXSEMI_Q3_8K'])
        self.now_ms = self.world.clock()
        self.now = datetime.fromtimestamp(self.now_ms / 1000, timezone.utc)
        fixture = strategy_fixture(now=self.now).context.read()
        self.profile = fixture['profile']
        markets, series = fixture['markets'], fixture['series']
        # The evidence fixture's issuer stands behind NVDAB, so the assessment reaches the policy.
        markets[0]['underlying_id'] = EXSEMI
        series[markets[0]['symbol']]['entity_id'] = EXSEMI
        self.markets, self.series = markets, series
        portfolio = deepcopy(fixture['portfolio'])
        portfolio.update(run_id=RUN, wallet_id=WALLET_ID)
        self.initial = {'portfolio': portfolio, 'balances': balances(portfolio)}
        self.provider = StrategyContextProvider(
            profile=self.profile, markets=lambda now_ms: deepcopy(self.markets),
            series=lambda now_ms: deepcopy(self.series),
            calendar=lambda now_ms: {'session_index': 80, 'remaining_sessions': 10},
            health=lambda current: {'integrity_ok': True, 'journal_ok': True, 'ownership_ok': True, 'clock_ok': True},
            quotes=FakeQuotes(markets, self.now), decide=keith_policy.decide, plan=keith_planner.plan)
        self.options = dict(policy_identity=(self.profile['policy_id'], 'Lifecycle.v1'), on_plan=on_plan)

    class Policy:
        decide = staticmethod(keith_policy.decide)

    def initialize(self):
        self.store.initialize(RUN, WALLET_ID, 56, doc(self.initial))
        return self.store.takeover(RUN, 1, offline=True)

    def coordinator(self):
        return Coordinator(self.store, self.world.assessor(RuleBaselineModel(self.world.clock)), self.Policy(),
                           StrategyPlanner(keith_planner.plan), execution=ExecutionBridge(), run_id=RUN,
                           version_id='thin-path-fixture', profile_hash=self.provider.profile_hash,
                           address=ADDRESS, context_provider=self.provider, **self.options)

    def request(self, job='thin-job'):
        cursor = self.world.store.read_cursor('sec-edgar', EXSEMI).read()
        return build_request(job={'job_id': job}, run_id=RUN, issuer_id=EXSEMI,
                             records=[self.world.record('EXSEMI_Q3_8K')], cutoff_ms=self.now_ms,
                             context=EMPTY_CONTEXT, policy_profile_hash=self.provider.profile_hash,
                             allowed_tools=list(self.world.config.tools), tool_calls=6, deadline_ms=60000,
                             source_health={'status': cursor['health']['status'],
                                            'last_success_ms': cursor['health']['last_success_ms']})

    def observation(self, command, kind, **fields):
        e = command['payload']['economic']
        base = {'schema': 'ExecutionObservation.v1', 'origin': 'SCRIPTED_FAKE', 'run_id': RUN,
                'wallet_id': WALLET_ID, 'intent_id': command['command_id'], 'round_id': command['round_id'],
                'observed_at': self.now.isoformat(), 'kind': kind, 'symbol': e['symbol'], 'side': e['side']}
        base.update(fields)
        base['event_id'] = f"{kind.lower()}:{command['command_id']}"
        return doc(base)

    def execute(self, runtime, command, directory):
        """Run Isaac's Executor through approve then swap; report each fact to the coordinator."""
        e = command['payload']['economic']
        store = SQLiteFixture(Path(directory) / 'execution.sqlite')
        guards, venue = FakeGuards(store), FakeVenue(store)
        engine = Executor(store, guards, venue, FakeSigner(store), FakeDecoder())
        t = self.now_ms // 1000  # the execution machine's clock must never move backwards
        pay, receive = (USDT, TOKENS[e['symbol']]) if e['side'] == 'BUY' else (TOKENS[e['symbol']], USDT)
        intent = Intent(RUN, command['round_id'], command['decision_id'], command['command_id'], 'thin-path-fixture',
                        command['command_id'], WALLET, pay, receive, e['pay_units'], e['min_receive_units'],
                        ROUTER, t + 60, 200000, 10, 1000000)
        key = intent.key
        engine.create(intent, t)
        for offset, step in ((0, 'APPROVE'), (3, 'SWAP')):
            engine.prepare(key, t + offset)
            engine.authorize(key, t + offset)
            engine.sign(key, t + offset)
            state = engine.broadcast(key, t + offset + 1)
            attempt = state.attempts[-1]
            if step == 'SWAP':
                runtime.observe(f"broadcast:{command['command_id']}",
                                self.observation(command, 'BROADCAST_ATTEMPTED', tx_hash=attempt.tx_hash),
                                strategy_reducer)
            venue.outcomes[attempt.tx_hash] = finalized(attempt)
            state = engine.reconcile(key, t + offset + 2)
            if step == 'APPROVE':
                runtime.observe(f"approval:{command['command_id']}", self.observation(
                    command, 'APPROVAL', settlement='FINAL', gas_bnb_units=APPROVE_GAS,
                    gas_value_units=APPROVE_GAS, intent_terminal=False), strategy_reducer)
                guards.nonce = 1  # positive adapter observation of the next nonce
        fill = self.observation(command, 'FILL', settlement='FINAL', gas_bnb_units=SWAP_GAS,
                                gas_value_units=SWAP_GAS, intent_terminal=True,
                                token_units=e['token_units'], cash_units=e['pay_units'], fee_units=e['fee_units'])
        runtime.observe(f"fill:{command['command_id']}", fill, strategy_reducer)
        store.close()
        return state, attempt.tx_hash


class ThinPathTests(DatabaseCase):
    def commands(self):
        with self.store.transaction() as db:
            return [Document(bytes(r[0])).read() for r in
                    db.execute('SELECT payload FROM commands WHERE run_id=%s', (RUN,)).fetchall()]

    def test_round_through_all_components_settles_audits_and_replays(self):
        path = ThinPath(self.store)
        path.initialize()
        runtime = path.coordinator()
        runtime.start('r1', path.request(), path.now_ms, defer_close=True)
        # Criterion 1: the strategy's baseline intent is committed as exactly one command.
        record = self.store.event(RUN, 'plan:r1')['record']
        self.assertIn('ASSESSMENT_ACCEPTED',
                      [d['reason'] for d in record['policy_output']['next_policy_state']['data']['assessment_diagnostics']])
        commands = self.commands()
        self.assertEqual(1, len(commands))
        command = {'command_id': commands[0]['command_id'], 'round_id': 'r1',
                   'decision_id': commands[0]['decision_id'], 'payload': commands[0]['payload']}
        economic = command['payload']['economic']
        self.assertEqual('BUY', economic['side'])
        before = self.store.load(RUN).read()
        self.assertTrue(before['reservations'])
        with tempfile.TemporaryDirectory() as directory:
            state, swap_tx = path.execute(runtime, command, directory)
        self.assertEqual('COMPLETED', state.status)
        self.assertEqual(1, len(path.coordinator().recover(path.now_ms + 1000)))  # closes r1
        # Criterion 2: settled portfolio, released reservations, closed round.
        after = self.store.load(RUN).read()
        portfolio = after['projection']['portfolio']
        old = before['projection']['portfolio']
        self.assertEqual(old['positions'][economic['symbol']]['units'] + economic['token_units'],
                         portfolio['positions'][economic['symbol']]['units'])
        self.assertEqual(old['cash_units'] - economic['pay_units'] - economic['fee_units'], portfolio['cash_units'])
        self.assertEqual(APPROVE_GAS + SWAP_GAS, portfolio['accounting']['gas_value_units'])
        self.assertEqual({}, portfolio['reservations'])
        self.assertEqual([], after['reservations'])
        self.assertEqual(0, self.store.metrics(RUN).read()['open_rounds'])
        # Criterion 1 (audit): the order carries the swap hash; the approve is not an order.
        with self.store.transaction() as db:
            audit = Document(bytes(db.execute('SELECT document FROM audit_events WHERE run_id=%s',
                                              (RUN,)).fetchone()[0])).read()
        log = json.loads(audit['log'])['data']
        self.assertEqual(1, len(log['orders']))
        self.assertEqual(swap_tx, log['orders'][0]['tx_hash'])
        self.assertEqual([{'tx_hash': swap_tx, 'decision_id': command['decision_id'], 'step': 'swap'}],
                         audit['swap_mappings'])
        # Criterion 3: restart sees no open work; replay reproduces the head exactly.
        self.assertEqual([], path.coordinator().recover(path.now_ms + 2000))
        journal = self.store.journal(RUN)
        expected = self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        replay(journal, doc(path.initial), self.store, run_id=RUN, wallet_id=WALLET_ID, chain_id=56,
               version_id='thin-path-fixture', profile_hash=path.provider.profile_hash, address=ADDRESS,
               policy=ThinPath.Policy(), planner=StrategyPlanner(keith_planner.plan), execution=ExecutionBridge(),
               reducer=strategy_reducer, context_provider=path.provider, **path.options)
        self.assertEqual(expected, self.store.verify(RUN))

    def test_decision_time_follows_a_later_assessment(self):
        """G6: an assessment completing after the round time is accepted at its completion time."""
        path = ThinPath(self.store)
        path.initialize()
        late = path.world.assessor(RuleBaselineModel(path.world.clock))

        class LateAssessor:
            def assess(self, request):
                result = late.assess(request).read()
                result['completed_ms'] = path.now_ms + 5000
                return doc(result)

        runtime = path.coordinator()
        runtime.assessor = LateAssessor()
        runtime.start('late', path.request('late-job'), path.now_ms, defer_close=True)
        record = self.store.event(RUN, 'plan:late')['record']
        self.assertEqual(path.now_ms + 5000, record['decision_ms'])
        self.assertIn('ASSESSMENT_ACCEPTED',
                      [d['reason'] for d in record['policy_output']['next_policy_state']['data']['assessment_diagnostics']])

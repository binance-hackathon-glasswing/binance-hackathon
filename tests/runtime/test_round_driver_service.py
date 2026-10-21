"""IDEA-050 E1-E8, E10: the complete round driver on real PostgreSQL. External ports are synthetic.

Real modules: EvidenceWork -> EvidenceAssessor -> ContextBuilder -> strategy -> RuntimePlanner -> Coordinator ->
commands (I3) -> ExecutionLoop -> ExecutionService -> W04 Executor -> RemoteSigner -> SignerService (ephemeral key) ->
execution_observations (I4) -> ServiceExecution -> settlement -> round log -> uploader -> replay.
The venue, chain and market are fakes; the signed bytes come from a throwaway key and are never broadcast.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

from larp.audit.delivery import DeliveryWorker
from larp.contracts import ContractError, Document
from larp.execution import Executor, USDT
from larp.execution_live.loop import (ExecutionLoop, FencedRelease, PlanValuation, RoundTerminal, RunAuthorization,
                                      intent_key)
from larp.execution_live.service import ExecutionService
from larp.execution_live.settlement import ReceiptFacts
from larp.execution_live.signing import RemoteSigner
from larp.execution_live.store import ExecutionStore
from larp.integration.replay import replay_live
from larp.integration.runtime import (ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state,
                                      initial_projection)
from larp.integration.settlement import ExecutionBridge, settle
from larp.intelligence.gate import lifecycle_policy_from
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import EXSEMI
from larp.research.fixtures import synthetic_profile
from larp.runtime.coordinator import Coordinator, batch_for
from larp.runtime.driver import (EXPIRED_REASON, DayRoll, MarketFeed, RoundDriver, RuntimeHealth, ServiceExecution,
                                 EvidenceWork)
from larp.runtime.fixtures import FakeReceiver
from larp.runtime.service import StartRefused, activate_run, init_run
from larp.runtime.supervision import Guard
from larp.storage.postgres import doc
from larp.strategy.schema import equity, market_view
from tests.execution.test_postgres_execution import ExecutionGuards, RegistrySigner
from tests.execution.test_settlement import log
from tests.execution_fixtures import BLOCK, FakeDecoder, FakeVenue, ROUTER, TOKEN, finalized
from tests.integration import test_evidence_pipeline as pipeline
from tests.runtime.test_driver import HOUR, DriverHarness
from tests.signer.test_service import fixture_policy

RUN = pipeline.RUN
VERSION = 'integration-fixture'
HAS_ETH = importlib.util.find_spec('eth_account') is not None
SECOND = 1000


class RemoteFixture(RemoteSigner):
    mode = 'fake'  # the W04 Executor accepts fake capability bundles only; the port is the live one (IDEA-047)


class JournalGuards(ExecutionGuards):
    """Fake nonce and market, but every run fact from RunAuthorization, i.e. from the journal."""

    def __init__(self, store, authorization):
        super().__init__(store)
        self.authorization = authorization

    def snapshot(self, economic_intent, now):
        gates = super().snapshot(economic_intent, now)
        facts = self.authorization(economic_intent, gates.epoch, gates.state_version, now)
        return replace(gates, expires_at=facts['expires_at'],
                       **{k: facts[k] for k in ('audit_durable', 'reservation_valid', 'version_valid', 'risk_valid',
                                                'health_valid', 'clock_trusted')})


class FencedVenue(FakeVenue):
    """Fake quotes and outcomes; every broadcast goes through the real FencedRelease boundary."""

    def __init__(self, registry, wallet):
        super().__init__(registry)
        self.registry, self.wallet, self.estimate, self.raw = registry, wallet, 1000, {}
        self.release = FencedRelease(registry, self)
        self.finalize = True

    def quote(self, i, nonce):
        return replace(super().quote(i, nonce), gas=1000)

    def approve(self, i, nonce):
        return replace(super().approve(i, nonce), gas=1000)

    def send(self, raw_hex):  # the submitter: the fake chain accepts the bytes and returns their hash
        return self.raw[raw_hex]

    def broadcast(self, signed, epoch, guard_version):
        self.raw[signed.raw_hex] = signed.tx_hash
        tx = self.release(signed, epoch, guard_version)
        self.broadcasts.append(tx)
        return tx

    def attempt(self, tx_hash):
        with self.registry.store.transaction() as db:
            keys = [r[0] for r in db.execute('SELECT economic_key FROM execution_records')]
        for key in keys:
            for a in self.registry.load(key).attempts:
                if a.tx_hash == tx_hash:
                    return a
        return None

    def outcome(self, tx_hash):
        a = self.attempt(tx_hash)
        if a is None or not self.finalize:
            return super().outcome(tx_hash)
        return finalized(a, sender=self.wallet, gas_used=500)


class Chain:
    """Receipt proof for ReceiptFacts, built from the attempt the fake chain finalized."""

    def __init__(self, venue, wallet):
        self.venue, self.wallet = venue, wallet

    def receipt(self, tx_hash):
        a = self.venue.attempt(tx_hash)
        state = next(self.venue.registry.load(k) for k in self.keys() if any(
            x.tx_hash == tx_hash for x in self.venue.registry.load(k).attempts))
        logs = [] if a.step == 'APPROVE' else [log(TOKEN, self.wallet, ROUTER, state.intent.amount),
                                               log(USDT, ROUTER, self.wallet, state.intent.minimum_output)]
        return dict(finality_verified=True, block_hash=BLOCK, block_number=10, finalized_height=12,
                    tx=dict(hash=tx_hash, nonce=hex(a.payload.nonce), to=a.payload.to, input=a.payload.data,
                            value=hex(a.payload.value), chainId='0x38', gas=hex(a.payload.gas),
                            gasPrice=hex(a.payload.gas_price), **{'from': self.wallet}),
                    receipt=dict(transactionHash=tx_hash, blockHash=BLOCK, blockNumber='0xa', gasUsed=hex(500),
                                 effectiveGasPrice='0x1', status='0x1', logs=logs, **{'from': self.wallet}))

    def keys(self):
        with self.venue.registry.store.transaction() as db:
            return [r[0] for r in db.execute('SELECT economic_key FROM execution_records')]


class Execution:
    """The execution process of one test: loop, service, executor and (optionally) the signer host."""

    def __init__(self, case, *, remote):
        self.case = case
        store, wallet = case.store, case.wallet
        self.registry = ExecutionStore(store, run_id=RUN, wallet=wallet)
        self.guards = JournalGuards(self.registry, RunAuthorization(store, run_id=RUN, build_id=VERSION))
        self.venue = FencedVenue(self.registry, wallet)
        if remote:
            from larp.signer.service import SignerService
            self.signer_host = SignerService(store=store, run_id=RUN, wallet=wallet,
                                             credentials=dict(WALLET_PRIVATE_KEY=case.account.key.hex()),
                                             clock_s=lambda: case.w.clock() // SECOND, decoder=FakeDecoder(),
                                             policy=fixture_policy())
            ticks = iter(range(10**6))
            signer = RemoteFixture(execution=self.registry, guards=self.guards, clock_s=lambda: case.w.clock() // SECOND,
                                   sleep=lambda s: self.signer_host.once(), monotonic=lambda: next(ticks),
                                   timeout_s=5, poll_s=1, pre_sign_swap=lambda payload: True)
        else:
            signer = RegistrySigner(self.registry)
        self.executor = Executor(self.registry, self.guards, self.venue, signer, FakeDecoder())
        epoch = self.registry.execution_authority()[0]
        self.loop = ExecutionLoop(store=store, registry=self.registry, service=None, run_id=RUN, wallet=wallet,
                                  epoch=epoch)
        terminal = RoundTerminal(store, run_id=RUN)
        facts = ReceiptFacts(Chain(self.venue, wallet), wallet_id='fake-wallet',
                             valuation=PlanValuation(store, self.registry, run_id=RUN), registry=self.registry,
                             epoch=epoch, authority_version=epoch, round_terminal=terminal)
        mapping = dict(wallet=wallet, version_id=VERSION, router=ROUTER, token_decimals={'NVDAB': 4},
                       limits=dict(max_gas=2000, max_gas_price=1, gas_budget=5000, per_trade_cap_units=50_000_000,
                                   slippage_bps=50))
        self.loop.service = ExecutionService(store=store, executor=self.executor, mapping=mapping,
                                             observe=self.loop.publish, wallet_id='fake-wallet', epoch=epoch,
                                             authority_version=epoch, settlement=facts, round_terminal=terminal)

    def once(self, now_ms):
        summary = self.loop.once(now_ms)
        for key in self.case.keys():
            state = self.registry.load(key)
            a = state.attempts[-1] if state.attempts else None
            if a is not None and a.step == 'APPROVE' and a.state == 'FINAL_SUCCESS':
                self.guards.nonce = a.payload.nonce + 1  # the fake chain's wallet count after the approval
        return summary


class ServiceHarness(DriverHarness):
    def setUp(self):
        super().setUp()
        if HAS_ETH:
            from eth_account import Account
            self.account = Account.create()
            self.wallet = self.account.address.lower()
        else:
            self.account, self.wallet = None, '0x' + '4' * 40
        self.world(['EXSEMI_402_8K'])
        current = self.store.load(RUN)
        projection = current.read()['projection']
        projection['registered_version'] = dict(build_id=VERSION, manifest_sha256='0' * 64)
        self.store.commit(batch_for(current, 'version:fixture', dict(kind='VERSION_REGISTERED',
                                                                   version=projection['registered_version']),
                                    projection=projection))

    def service_driver(self, *, grace_ms=5 * SECOND, market=None, day_roll_window_ms=None, max_quote_rounds=0,
                       cadence=False, clock=None, planner=None):
        self.profile = synthetic_profile(falsifier_ids=['F-ITEM-4.02'], falsifier_authority='MANDATORY_REDUCTION')
        self.h = pipeline.profile_hash(self.profile)
        lifecycle = lifecycle_policy_from(self.w.config)
        feed = MarketFeed(market or self.market)
        builder = ContextBuilder(profile=self.profile, profile_hash=self.h, run_id=RUN,
                                 issuers={EXSEMI: {'token': 'NVDAB', 'underlying_id': EXSEMI}}, market=feed,
                                 health=RuntimeHealth(self.store, RUN, self.epoch),
                                 calendar=lambda now: {'index': 80, 'remaining': 10}, lifecycle_policy=lifecycle)
        coordinator = Coordinator(self.store, self.w.assessor(RuleBaselineModel(self.w.clock)), StrategyPolicy(),
                                  planner or RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                                  execution=ExecutionBridge(), run_id=RUN, version_id=VERSION, profile_hash=self.h,
                                  address='0x' + '1' * 40, context_builder=builder,
                                  initial_policy_state=initial_policy_state(RUN, self.profile),
                                  clock_ms=clock or self.w.clock, require_version=True)
        work = EvidenceWork(store=self.store, evidence_store=self.w.store, run_id=RUN, config=self.w.config,
                            issuers=[EXSEMI], profile_hash=self.h, cadence_ms=HOUR, lifecycle_policy=lifecycle)
        if not cadence:
            work._cadence = lambda now_ms: None  # one unit of work per test; cadence is IDEA-048 D3
        execution = ServiceExecution(coordinator, wallet=self.wallet, grace_ms=grace_ms)
        day_roll = DayRoll(coordinator, window_ms=day_roll_window_ms) if day_roll_window_ms else None
        return RoundDriver(coordinator, work, execution=execution, market=feed, day_roll=day_roll,
                           max_quote_rounds=max_quote_rounds)

    def keys(self):
        with self.store.transaction() as db:
            return [r[0] for r in db.execute('SELECT economic_key FROM execution_records WHERE run_id=%s', (RUN,))]

    def commands(self):
        with self.store.transaction() as db:
            return [r[0] for r in db.execute('SELECT command_id FROM commands WHERE run_id=%s', (RUN,))]

    def planned(self):
        rounds = self.store.load(RUN).read()['projection'].get('round_records', {})
        return {r: rec for r, rec in rounds.items() if rec['plan'].get('intents')}

    def version(self):
        return self.store.load(RUN).read()['version']

    def run_both(self, driver, execution, *, ticks=60, until=None):
        for _ in range(ticks):
            self.w.clock.now += SECOND
            driver.once(self.w.clock())
            execution.once(self.w.clock())
            if until is not None and until():
                return True
        return False

    def closed(self, round_id):
        return self.store.receipt(RUN, 'close:' + round_id) is not None

    def replay_head(self, driver):
        journal, expected = self.store.journal(RUN), self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        builder = driver.coordinator.context_builder
        head = replay_live(journal, doc(initial_projection(pipeline.pipeline_ledger())), self.store, builder=builder,
                           run_id=RUN, wallet_id='fake-wallet', chain_id=56, version_id=VERSION,
                           profile_hash=self.h, address='0x' + '1' * 40, policy=StrategyPolicy(),
                           planner=RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                           execution=ExecutionBridge(), reducer=settle,
                           initial_policy_state=initial_policy_state(RUN, self.profile), require_version=True)
        return head, expected


class HandOff(ServiceHarness):
    def test_e1_nothing_is_committed_until_the_execution_service_claims_the_command(self):
        driver = self.service_driver()
        driver.work._cadence = EvidenceWork._cadence.__get__(driver.work)  # cadence work is due on later ticks
        first = driver.once(self.w.clock())
        [round_id] = self.planned()
        [command] = self.commands()
        version = self.version()
        for _ in range(3):
            self.w.clock.now += SECOND
            summary = driver.once(self.w.clock())
            self.assertEqual(summary['waiting_for_claim'], [command])
            self.assertIsNone(summary['round_id'])
        self.assertEqual(self.version(), version)  # no cadence round, nothing ingested
        self.assertEqual(first['round_id'], round_id)
        execution = Execution(self, remote=False)
        claimed = execution.loop.once(self.w.clock())
        self.assertEqual(claimed['claimed'], [command])
        self.assertEqual(self.keys(), [intent_key(RUN, self.wallet, command)])
        self.assertNotIn('waiting_for_claim', driver.once(self.w.clock()))


class EndToEnd(ServiceHarness):
    def test_e3_evidence_to_fill_settlement_round_log_upload_and_replay(self):
        if not HAS_ETH:
            self.skipTest('signer dependency not installed')
        driver = self.service_driver()
        execution = Execution(self, remote=True)
        driver.once(self.w.clock())
        [round_id] = self.planned()
        intent = self.planned()[round_id]['plan']['intents'][0]
        self.assertEqual((intent['side'], intent['symbol'], intent['mandatory']), ('SELL', 'NVDAB', True))
        self.assertTrue(self.run_both(driver, execution, until=lambda: self.closed(round_id)))
        current = self.store.load(RUN).read()
        self.assertEqual(current['reservations'], [])
        self.assertEqual(current['projection']['portfolio']['positions']['NVDAB']['units'], 0)
        self.assertEqual(len(execution.venue.broadcasts), 2)  # approve and swap, both through FencedRelease
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM execution_signatures').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT count(*) FROM signing_refusals').fetchone()[0], 0)
        log_data = self.logs()[round_id]
        swap = execution.venue.broadcasts[-1]
        self.assertEqual([o.get('tx_hash') for o in log_data['orders']], [swap])
        with self.store.transaction() as db:
            raw = db.execute('SELECT document FROM audit_events WHERE run_id=%s AND round_id=%s',
                             (RUN, round_id)).fetchone()[0]
        self.assertEqual([m['tx_hash'] for m in Document(bytes(raw)).read()['swap_mappings']], [swap])
        self.assertNotIn('aborted', log_data['output'])
        uploader = DeliveryWorker(self.store, FakeReceiver(), retry_ms=1)
        while uploader.once(RUN, self.epoch, self.w.clock()):
            pass
        self.assertEqual(len(uploader.status(RUN)['delivered']), 1)
        head, expected = self.replay_head(driver)
        self.assertEqual(head, expected)


class Ingestion(ServiceHarness):
    def execute_without_driver(self):
        driver = self.service_driver()
        execution = Execution(self, remote=False)
        driver.once(self.w.clock())
        [round_id] = self.planned()
        for _ in range(60):
            self.w.clock.now += SECOND
            execution.once(self.w.clock())
            if all(self.registry_state(k).status == 'COMPLETED' for k in self.keys()) and self.keys():
                execution.once(self.w.clock())  # the cycle after completion publishes the final fact
                break
        with self.store.transaction() as db:
            rows = [r[0] for r in db.execute('SELECT event_id FROM execution_observations WHERE run_id=%s', (RUN,))]
        return round_id, rows

    def registry_state(self, key):
        return ExecutionStore(self.store, run_id=RUN, wallet=self.wallet).load(key)

    def test_e2_every_observation_is_journaled_once_in_an_order_the_reducer_accepts(self):
        before = self.store.load(RUN).read()['projection']['portfolio']['bnb_units']
        round_id, rows = self.execute_without_driver()
        self.assertEqual(len(rows), 4)  # approve broadcast + final, swap broadcast + final
        driver = self.service_driver()  # a restarted runtime
        self.w.clock.now += SECOND
        summary = driver.once(self.w.clock())
        self.assertEqual(sorted(summary['ingested']), sorted(rows))
        self.assertNotIn('refused', summary)
        self.assertTrue(self.closed(round_id))
        # Both receipts' gas (500 units each at price 1) is accounted: the approval was journaled before the fill.
        self.assertEqual(self.store.load(RUN).read()['projection']['portfolio']['bnb_units'], before - 1000)
        for event_id in rows:
            self.assertIsNotNone(self.store.event(RUN, event_id))
        again = self.service_driver()
        self.w.clock.now += SECOND
        self.assertNotIn('ingested', again.once(self.w.clock()))

    def test_e2_a_changed_outbox_row_is_refused_and_never_journaled(self):
        round_id, rows = self.execute_without_driver()
        with self.store.transaction() as db:
            rows = db.execute("SELECT event_id,observation FROM execution_observations WHERE run_id=%s", (RUN,))
            event_id, value = next((e, json.loads(bytes(raw))) for e, raw in rows
                                   if json.loads(bytes(raw))['kind'] == 'FILL')
            value['cash_units'] += 1  # a changed fact keeps its old hash
            db.execute('UPDATE execution_observations SET observation=%s WHERE event_id=%s',
                       (json.dumps(value).encode(), event_id))
        driver = self.service_driver()
        self.w.clock.now += SECOND
        summary = driver.once(self.w.clock())
        self.assertIn(event_id, summary['refused'])
        self.assertIsNone(self.store.event(RUN, event_id))
        self.assertFalse(self.closed(round_id))


class Expiry(ServiceHarness):
    def test_e4_an_unclaimed_command_ends_not_submitted_only_after_the_grace(self):
        driver = self.service_driver(grace_ms=5 * SECOND)
        driver.once(self.w.clock())
        [round_id] = self.planned()
        intent = self.planned()[round_id]['plan']['intents'][0]
        self.w.clock.now = intent['expires_ms'] + 5 * SECOND - 1
        summary = driver.once(self.w.clock())
        self.assertNotIn('expired', summary)
        self.assertNotIn('waiting_for_claim', summary)  # expired: nothing waits for it any more
        self.assertFalse(self.closed(round_id))
        self.w.clock.now += 1
        summary = driver.once(self.w.clock())
        self.assertEqual(summary['expired'], [intent['intent_id']])
        self.assertTrue(self.closed(round_id))
        self.assertEqual(self.store.load(RUN).read()['reservations'], [])
        log_data = self.logs()[round_id]
        self.assertEqual([a['reason'] for a in log_data['output']['aborted']], [EXPIRED_REASON])
        execution = Execution(self, remote=False)
        self.assertEqual(execution.loop.once(self.w.clock())['claimed'], [])
        self.assertEqual(self.keys(), [])
        from larp.execution import Intent
        ended = Intent(RUN, round_id, intent['decision_id'], intent['intent_id'], VERSION, intent['intent_id'],
                       self.wallet, TOKEN, USDT, 2000, 1, ROUTER, intent['expires_ms'] // 1000, 2000, 1, 5000)
        facts = RunAuthorization(self.store, run_id=RUN, build_id=VERSION).facts(ended, self.w.clock() // SECOND)
        self.assertFalse(facts['reservation_valid'])  # an intent the journal ended can never be created or signed


class Halt(ServiceHarness):
    def test_e5_a_halt_after_the_approval_stops_the_swap_signature(self):
        driver = self.service_driver()
        execution = Execution(self, remote=False)
        driver.once(self.w.clock())
        [round_id] = self.planned()

        def approved():
            return any(a.step == 'APPROVE' and a.state == 'FINAL_SUCCESS'
                       for k in self.keys() for a in execution.registry.load(k).attempts)
        self.assertTrue(self.run_both(driver, execution, until=approved))
        # D-DN-09: CLOCK blocks every signature. A pausing HALT (DELIVERY_DEADLINE) would let this mandatory sell
        # finish; that case is tests/runtime/test_halt_split.py HS5.
        Guard(self.store, RUN, max_failures=3, clear_after=2)._halt('CLOCK', self.w.clock(), {})
        self.run_both(driver, execution, ticks=60, until=lambda: self.closed(round_id))
        [key] = self.keys()
        state = execution.registry.load(key)
        self.assertEqual([a.step for a in state.attempts], ['APPROVE'])  # no swap was prepared, signed or sent
        with self.store.transaction() as db:
            signed = db.execute('SELECT count(*) FROM execution_signatures').fetchone()[0]
        self.assertEqual(signed, 1)
        self.assertEqual(len(execution.venue.broadcasts), 1)
        self.assertTrue(self.closed(round_id))  # aborted before the swap: NOT_SUBMITTED, approval gas accounted
        self.assertEqual(self.store.load(RUN).read()['projection']['portfolio']['positions']['NVDAB']['units'], 2000)

    def test_e5_reconciliation_of_a_broadcast_swap_continues_under_halt(self):
        driver = self.service_driver()
        execution = Execution(self, remote=False)
        driver.once(self.w.clock())
        [round_id] = self.planned()

        def swap_sent():
            return any(a.step == 'SWAP' and a.broadcast_at is not None
                       for k in self.keys() for a in execution.registry.load(k).attempts)
        execution.venue.finalize = True
        self.assertTrue(self.run_both(driver, execution, until=swap_sent))
        Guard(self.store, RUN, max_failures=3, clear_after=2)._halt('DELIVERY_DEADLINE', self.w.clock(), {})
        self.assertTrue(self.run_both(driver, execution, until=lambda: self.closed(round_id)))
        self.assertEqual(self.store.load(RUN).read()['projection']['portfolio']['positions']['NVDAB']['units'], 0)


class QuoteMarket:
    """No quote in the plain fetch; an executable one from the quote path."""

    def __init__(self, case, executable=True):
        self.case, self.executable, self.requests = case, executable, []

    def __call__(self, now_ms):
        return [dict(m, quotes=[]) for m in self.case.market(now_ms)]

    def observe(self, request):
        self.requests.append(dict(request))
        quoted = next(m for m in self.case.market(self.case.w.clock()) if m['symbol'] == request['symbol'])
        if not self.executable:
            return dict(quoted, quotes=[], quote_status='CAPABILITY_PROOF_REQUIRED')
        return quoted


class Quotes(ServiceHarness):
    def test_e6_a_quote_request_leads_to_one_follow_up_round_with_the_executable_quote(self):
        market = QuoteMarket(self)
        driver = self.service_driver(market=market, max_quote_rounds=1)
        summary = driver.once(self.w.clock())
        base = summary['round_id']
        self.assertEqual([r['symbol'] for r in market.requests], ['NVDAB'])
        self.assertEqual(summary['quote_round_id'], base + '/quote1')
        self.assertEqual(list(self.planned()), [base + '/quote1'])
        first = self.store.event(RUN, 'plan:' + base)['record']['plan']
        self.assertEqual((first['intents'], [r['symbol'] for r in first['quote_requests']]), ([], ['NVDAB']))

    def test_e6_without_an_executable_quote_no_follow_up_round_runs(self):
        market = QuoteMarket(self, executable=False)
        driver = self.service_driver(market=market, max_quote_rounds=3)
        summary = driver.once(self.w.clock())
        self.assertEqual(len(market.requests), 1)
        self.assertNotIn('quote_round_id', summary)
        self.assertEqual(self.planned(), {})

    def test_e6_quote_rounds_are_bounded(self):
        driver = self.service_driver(market=QuoteMarket(self), max_quote_rounds=0)
        summary = driver.once(self.w.clock())
        self.assertNotIn('quotes_requested', summary)


class TickClock:
    def __init__(self, clock):
        self.clock = clock

    def __call__(self):
        self.clock.now += 1
        return self.clock.now


class Cutoff(ServiceHarness):
    def test_e7_the_decision_time_is_never_before_the_market_observations(self):
        clock = TickClock(self.w.clock)
        stamped = lambda now_ms: self.market(clock())  # available_at = the fetch's own completion time
        driver = self.service_driver(market=stamped, clock=clock)
        driver.once(self.w.clock())
        [record] = self.planned().values()
        decision = record['decision_ms']
        markets = record['policy_input']['context']['markets']
        self.assertTrue(all(datetime.fromisoformat(m['available_at']).timestamp() * 1000 <= decision
                            for m in markets))
        self.assertEqual(record['plan']['intents'][0]['symbol'], 'NVDAB')

    def test_e7_without_the_prefetch_the_same_market_is_future_data(self):
        # The #24 defect the prefetch removes: the builder fetching inside the round sees observations newer than
        # its decision time, so the held name is unvalued and no mandatory sale is planned.
        clock = TickClock(self.w.clock)
        stamped = lambda now_ms: self.market(clock())
        driver = self.service_driver(market=stamped, clock=clock)
        driver.market = None
        driver.coordinator.context_builder.market = stamped
        driver.once(self.w.clock())
        self.assertEqual(self.planned(), {})


class DayRolls(ServiceHarness):
    def risk_day(self):
        projection = self.store.load(RUN).read()['projection']
        return (projection.get('risk_state') or projection['portfolio']['risk'])['day']

    def midnight_after(self, day, days=1):
        d = datetime.fromisoformat(day).replace(tzinfo=timezone.utc) + timedelta(days=days)
        return int(d.timestamp() * 1000)

    def test_e8_one_roll_per_day_at_the_prefetched_marks(self):
        day = self.risk_day()
        driver = self.service_driver(day_roll_window_ms=15 * 60 * SECOND)
        self.w.clock.now = self.midnight_after(day) + 60 * SECOND
        summary = driver.once(self.w.clock())
        self.assertEqual(summary['day_roll'], 'ROLLED')
        rolled = self.store.event(RUN, 'day:' + self.risk_day())
        self.assertIsNotNone(rolled)
        self.assertGreater(self.risk_day(), day)
        current = self.store.load(RUN).read()
        ledger = current['projection']['portfolio']
        marks = market_view(self.market(self.w.clock()), driver.coordinator.context_builder.universe,
                            datetime.fromtimestamp(self.w.clock() / 1000, timezone.utc), self.profile)
        self.assertEqual(rolled['anchor_units'], int(equity(ledger, marks)))
        self.w.clock.now += SECOND
        self.assertNotIn('day_roll', driver.once(self.w.clock()))
        head, expected = self.replay_head(driver)
        self.assertEqual(head, expected)

    def test_r2_the_roll_values_marks_at_a_time_read_after_the_fetch(self):
        # The real client stamps available_at when the response arrives, after the cycle's clock was read.
        def fetching(now_ms):
            self.w.clock.now += 1500
            return self.market(self.w.clock())
        day = self.risk_day()
        driver = self.service_driver(market=fetching, day_roll_window_ms=15 * 60 * SECOND)
        self.w.clock.now = self.midnight_after(day) + 60 * SECOND
        self.assertEqual(driver.once(self.w.clock())['day_roll'], 'ROLLED')
        self.assertGreater(self.risk_day(), day)

    def test_r2_a_fetch_that_ends_after_the_window_does_not_roll(self):
        def fetching(now_ms):
            self.w.clock.now += 1500
            return self.market(self.w.clock())
        day = self.risk_day()
        driver = self.service_driver(market=fetching, day_roll_window_ms=15 * 60 * SECOND)
        self.w.clock.now = self.midnight_after(day) + 15 * 60 * SECOND - 500
        self.assertEqual(driver.once(self.w.clock())['day_roll'], 'OUTSIDE_WINDOW')
        self.assertEqual(self.risk_day(), day)

    def test_e8_no_roll_outside_the_window_or_without_a_mark(self):
        day = self.risk_day()
        driver = self.service_driver(day_roll_window_ms=15 * 60 * SECOND)
        self.w.clock.now = self.midnight_after(day) + 20 * 60 * SECOND
        self.assertEqual(driver.once(self.w.clock())['day_roll'], 'OUTSIDE_WINDOW')
        unmarked = lambda now_ms: [m for m in self.market(now_ms) if m['symbol'] != 'NVDAB']
        driver = self.service_driver(market=unmarked, day_roll_window_ms=15 * 60 * SECOND)
        self.w.clock.now = self.midnight_after(day, 2) + 60 * SECOND
        self.assertEqual(driver.once(self.w.clock())['day_roll'], 'MARK_UNAVAILABLE')
        self.assertEqual(self.risk_day(), day)


class Lifecycle(ServiceHarness):
    BUILD = 'b' * 40

    def manifest(self, build=None):
        return Document.from_dict(dict(schema='ReleaseManifest.v1', build_id=build or self.BUILD, repository='fixture',
                                       release_register=dict(services_sha256='a' * 64, deviations_sha256='c' * 64)))

    def config(self, run_id='dev-run', **changes):
        # One run per wallet and chain (runs_wallet_id_chain_id_key): each refusal case has its own wallet.
        wallet = self.wallet if run_id == 'dev-run' else '0x' + hashlib.sha256(run_id.encode()).hexdigest()[:40]
        ledger = dict(pipeline.pipeline_ledger(), run_id=run_id, wallet_id=wallet, mode='LIVE')
        raw = json.dumps(ledger).encode()
        path = Path(self.tmp.name) / f'{run_id}-initial.json'
        path.write_bytes(raw)
        return dict(schema='RuntimeService.v1', run_id=run_id, build_id=self.BUILD, mode='dev',
                    wallet_address=wallet, initial_state_file=str(path),
                    initial_state_sha256=hashlib.sha256(raw).hexdigest(), **changes)

    def activate(self, config, **kwargs):
        return activate_run(config, self.store, kwargs.pop('manifest', self.manifest()), reviewer='Keegan',
                            review_ref='IDEA-050', now_ms=self.w.clock(), **kwargs)

    def test_e10_init_then_activate_registers_the_build_and_records_the_reviewer(self):
        config = self.config()
        self.assertTrue(init_run(config, self.store)['quarantined'])
        run = self.store.load('dev-run').read()
        self.assertEqual((run['mode'], run['quarantined'], run['wallet_id']), ('dev', True, self.wallet))
        with self.assertRaises(StartRefused):
            init_run(config, self.store)  # never twice
        result = self.activate(config)
        run = self.store.load('dev-run').read()
        self.assertFalse(run['quarantined'])
        self.assertEqual(result['epoch'], run['epoch'])
        self.assertEqual(run['projection']['registered_version']['build_id'], self.BUILD)
        activated = self.store.event('dev-run', f"activate:{run['epoch']}")
        self.assertEqual((activated['kind'], activated['reviewer'], activated['review_ref']),
                         ('RUN_ACTIVATED', 'Keegan', 'IDEA-050'))
        with self.assertRaises(StartRefused):
            self.activate(config)  # already active
        journal, expected = self.store.journal('dev-run'), self.store.verify('dev-run')
        target_run = 'dev-run'
        with self.store.transaction() as db:
            db.execute('DELETE FROM events WHERE run_id=%s', (target_run,))
            db.execute('DELETE FROM runs WHERE run_id=%s', (target_run,))
        from larp.runtime.replay import replay
        head = replay(journal, doc(initial_projection(dict(pipeline.pipeline_ledger(), run_id=target_run,
                                                         wallet_id=self.wallet, mode='LIVE'))), self.store,
                      run_id=target_run, wallet_id=self.wallet, chain_id=56, version_id=self.BUILD, profile_hash='',
                      address=self.wallet, policy=None, planner=None, execution=None, reducer=settle)
        self.assertEqual(head, expected)

    def test_e10_refusals(self):
        with self.subTest('pinned file'), self.assertRaises(StartRefused):
            init_run(dict(self.config('r1'), initial_state_sha256='0' * 64), self.store)
        with self.subTest('mode'):
            init_run(self.config('r2'), self.store)
            with self.assertRaises(StartRefused):
                self.activate(dict(self.config('r2'), mode='live'))
        with self.subTest('another build registered'):
            init_run(self.config('r3'), self.store)
            self.activate(self.config('r3'))
            self.store.quarantine('r3')
            with self.assertRaises(StartRefused):
                self.activate(dict(self.config('r3'), build_id='d' * 40), manifest=self.manifest('d' * 40))
        with self.subTest('open round'):
            init_run(self.config('r4'), self.store)
            self.activate(self.config('r4'))
            run = self.store.load('r4').read()
            self.store.open_round('r4', 'open-round', doc({'x': 1}), run['epoch'])
            self.store.quarantine('r4')
            with self.assertRaises(StartRefused):
                self.activate(self.config('r4'))
        with self.subTest('unfinished execution'):
            init_run(self.config('r5'), self.store)
            with self.store.transaction() as db:
                db.execute('INSERT INTO execution_records VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                           ('k' * 64, 'r5', self.wallet, 56, False, 1, b'{}', 's' * 64))
            with self.assertRaises(StartRefused):
                self.activate(self.config('r5'))
        with self.subTest('journal does not verify'):
            init_run(self.config('r6'), self.store)
            self.activate(self.config('r6'))
            self.store.quarantine('r6')
            with self.store.transaction() as db:
                db.execute("UPDATE runs SET head=%s WHERE run_id='r6'", ('f' * 64,))
            with self.assertRaises(StartRefused):
                self.activate(self.config('r6'))
        with self.subTest('offline run'):
            with self.assertRaises(StartRefused):
                init_run(dict(self.config('r7'), mode='offline'), self.store)
        with self.subTest('wallet already has a run'):
            with self.assertRaises(StartRefused):
                init_run(dict(self.config('r2'), run_id='r8'), self.store)


class Restart(ServiceHarness):
    """R3: a crash between planning and claiming, then a real `Service` start (RESTART incident)."""

    def service(self, driver):
        from larp.runtime.service import Service
        return Service(self.store, RUN, VERSION, guard=Guard(self.store, RUN, max_failures=3, clear_after=2),
                       driver=driver, clock_ms=self.w.clock, sleep=lambda s: None)

    def crash_after_planning(self):
        crashed = self.service(self.service_driver())
        crashed.sessions.begin(session_id=crashed.session_id, build_id=VERSION, now_ms=self.w.clock())
        crashed.driver.once(self.w.clock())  # plans the command; the process dies before the claim
        [command] = self.commands()
        return command

    def events(self, prefix):
        with self.store.transaction() as db:
            return [Document(bytes(r[0])).read()['event'] for r in db.execute(
                'SELECT batch FROM events WHERE run_id=%s AND event_id LIKE %s ORDER BY sequence', (RUN, prefix + '%'))]

    def test_r3_a_restart_reauthorizes_the_unclaimed_command_and_execution_claims_it(self):
        command = self.crash_after_planning()
        self.w.clock.now += SECOND
        restarted = self.service(self.service_driver())
        self.assertEqual(restarted.run(max_cycles=1), 0)
        self.assertEqual([e['incident']['type'] for e in self.events('incident:restart:')], ['RESTART'])
        [event] = self.events('reauthorize:')
        self.assertEqual((event['kind'], event['commands']), ('COMMAND_REAUTHORIZED', [command]))
        execution = Execution(self, remote=False)
        self.assertEqual(execution.loop.once(self.w.clock())['claimed'], [command])
        with self.store.transaction() as db:
            payloads = {r[0] for r in db.execute('SELECT payload FROM commands WHERE run_id=%s', (RUN,))}
        self.assertEqual(len(payloads), 1)  # the command's bytes never change, only its authority
        head, expected = self.replay_head(restarted.driver)
        self.assertEqual(head, expected)

    def not_reauthorized(self, prepare):
        self.crash_after_planning()
        self.w.clock.now += SECOND
        prepare()
        self.service(self.service_driver()).run(max_cycles=1)
        self.assertEqual(self.events('reauthorize:'), [])

    def test_r3_an_expired_intent_is_not_reauthorized(self):
        def expire():
            intent = next(iter(self.planned().values()))['plan']['intents'][0]
            self.w.clock.now = intent['expires_ms']
        self.not_reauthorized(expire)

    def test_r3_a_halted_run_reauthorizes_nothing(self):
        # CLOCK is latched: the restarted guard does not clear it in the same cycle.
        self.not_reauthorized(lambda: Guard(self.store, RUN, max_failures=3, clear_after=2)._halt(
            'CLOCK', self.w.clock(), {}))

    def test_r3_a_claimed_intent_is_not_reauthorized(self):
        self.not_reauthorized(lambda: Execution(self, remote=False).loop.once(self.w.clock()))


class SplitPlanner(RuntimePlanner):
    """The real planner with its single SELL child split into two intents: a multi-intent round, which the coordinator
    and settlement accept although the risk planner itself plans one child per round."""

    def __init__(self):
        super().__init__(job_validity_ms=86_400_000, job_max_attempts=3)

    def plan(self, snapshot, proposal):
        from larp.ports import decimal_string
        p = super().plan(snapshot, proposal).read()
        if len(p['intents']) != 1 or p['intents'][0]['side'] != 'SELL':
            return Document.from_dict(p)
        [i] = p['intents']
        intents, deltas = [], []
        for part in ('a', 'b'):
            token = i['token_units'] // 2
            identity = hashlib.sha256((i['intent_id'] + part).encode()).hexdigest()
            intents.append(dict(i, token_units=token, pay_units=token, cash_units=i['cash_units'] // 2,
                                min_receive_units=i['min_receive_units'] // 2, gas_bnb_units=i['gas_bnb_units'] // 2,
                                intent_id=identity, decision_id='decision:' + identity,
                                amount=decimal_string(token, i['decimals'])))
            deltas += [dict(intent_id=identity, asset=i['symbol'], units=token),
                       dict(intent_id=identity, asset='BNB', units=i['gas_bnb_units'] // 2)]
        return Document.from_dict(dict(p, intents=intents, reservation_deltas=deltas))


class TwoIntents(ServiceHarness):
    def completed(self, execution, count):
        states = [execution.registry.load(k).status for k in self.keys()]
        return len(states) >= count and sum(s == 'COMPLETED' for s in states) >= count

    def run_execution_only(self, execution, count):
        for _ in range(120):
            self.w.clock.now += SECOND
            execution.once(self.w.clock())
            if self.completed(execution, count):
                execution.once(self.w.clock())  # publishes the last final fact
                return
        self.fail('executions did not complete')

    def test_y1_two_intents_that_finish_before_any_ingestion_close_their_round(self):
        driver = self.service_driver(planner=SplitPlanner())
        execution = Execution(self, remote=False)
        driver.once(self.w.clock())
        [round_id] = self.planned()
        self.assertEqual(len(self.planned()[round_id]['plan']['intents']), 2)
        self.run_execution_only(execution, 2)  # the runtime is stopped while both execute
        self.w.clock.now += SECOND
        self.service_driver(planner=SplitPlanner()).once(self.w.clock())  # restarted runtime
        self.assertTrue(self.closed(round_id))
        self.assertEqual(self.store.load(RUN).read()['projection']['portfolio']['positions']['NVDAB']['units'], 0)
        self.assertIsNotNone(self.store.event(RUN, 'sealed:' + round_id))

    def test_y1_a_round_with_an_unfinished_intent_is_never_sealed(self):
        driver = self.service_driver(planner=SplitPlanner())
        execution = Execution(self, remote=False)
        driver.once(self.w.clock())
        [round_id] = self.planned()
        self.run_execution_only(execution, 1)
        self.w.clock.now += SECOND
        driver.once(self.w.clock())  # journals the first intent's facts; the second is not final
        self.assertFalse(self.closed(round_id))
        self.assertIsNone(self.store.event(RUN, 'sealed:' + round_id))
        self.assertTrue(self.run_both(driver, execution, until=lambda: self.closed(round_id)))


class Crash(Exception):
    pass


class QuoteResume(ServiceHarness):
    def crash_in_child(self, driver):
        c = driver.coordinator
        original = c.start

        def start(round_id, request, now_ms, **kwargs):
            if '/quote' in round_id:  # the child opens, then the process dies before its plan commits
                c.store.open_round(c.run_id, round_id, request, c.store.load(c.run_id).read()['epoch'])
                raise Crash()
            return original(round_id, request, now_ms, **kwargs)
        c.start = start

    def parent(self):
        [base] = [r for r in self.logs() if '/quote' not in r]
        return base

    def test_y2_an_interrupted_quote_follow_up_runs_again_after_a_restart(self):
        driver = self.service_driver(market=QuoteMarket(self), max_quote_rounds=1)
        self.crash_in_child(driver)
        with self.assertRaises(Crash):
            driver.once(self.w.clock())
        base = self.parent()
        self.w.clock.now += SECOND
        market = QuoteMarket(self)
        summary = self.service_driver(market=market, max_quote_rounds=1).once(self.w.clock())
        self.assertEqual(summary['quote_round_id'], base + '/quote1#2')
        self.assertEqual([r['symbol'] for r in market.requests], ['NVDAB'])  # quotes fetched again
        self.assertEqual(list(self.planned()), [base + '/quote1#2'])
        self.assertEqual(self.logs()[base + '/quote1']['output']['errors'], ['PROCESS_INTERRUPTED'])

    def test_y2_without_an_executable_quote_the_resume_is_tried_once_per_process(self):
        driver = self.service_driver(market=QuoteMarket(self), max_quote_rounds=1)
        self.crash_in_child(driver)
        with self.assertRaises(Crash):
            driver.once(self.w.clock())
        market = QuoteMarket(self, executable=False)
        restarted = self.service_driver(market=market, max_quote_rounds=1)
        for _ in range(3):
            self.w.clock.now += SECOND
            restarted.once(self.w.clock())
        self.assertEqual(len(market.requests), 1)
        self.assertEqual(self.planned(), {})

"""IDEA-093 PL-1..PL-9: per-stock parallel assessments (signed path) and trade continuation rounds (cadence path).

Synthetic providers and ports; no keys or network. Trades stay one at a time (wallet barrier, G-18): only model
assessments run concurrently, and continuation rounds only plan sooner.
"""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.intelligence.scenarios import EXSEMI
from tests.integration import test_evidence_pipeline as pipeline
from tests.runtime.test_driver import HOUR, RUN, DriverHarness
from tests.runtime.test_round_driver_service import ServiceHarness

ISSUERS = ('A', 'B', 'C', 'D', 'E')


def request(issuer, run_id='r', profile_hash='a' * 64, job='job'):
    return Document.from_dict(dict(schema='AssessmentRequest.v1', run_id=run_id, job_id=job + ':' + issuer,
        issuer_id=issuer, policy_profile_hash=profile_hash, context_hash='b' * 64, cutoff_ms=1000, evidence_refs=[],
        budget=dict(tool_calls=3, deadline_ms=1000)))


class Gate:
    """A synthetic assessor whose calls block until released, one gate per issuer."""

    def __init__(self):
        self.entered = {i: threading.Event() for i in ISSUERS}
        self.release = {i: threading.Event() for i in ISSUERS}
        self.calls, self.audit_hook, self.threads = [], None, set()

    def assess(self, req, hook=None):
        hook = hook or self.audit_hook
        issuer = req.read()['issuer_id']
        self.calls.append(issuer)
        self.threads.add(threading.get_ident())
        hook(dict(kind='MODEL_REQUEST', stage='routine', request={'issuer': issuer}))
        self.entered[issuer].set()
        if not self.release[issuer].wait(5):
            raise TimeoutError('synthetic test did not release ' + issuer)
        r = req.read()
        return Document.from_dict(dict(schema='AssessmentResult.v2', run_id=r['run_id'], job_id=r['job_id'],
            issuer_id=issuer, policy_profile_hash=r['policy_profile_hash'], context_hash='b' * 64, cutoff_ms=1000,
            started_ms=1000, completed_ms=1100, expiry_ms=2000, model_hash='c' * 64, prompt_hash='d' * 64,
            rationale='synthetic ' + issuer, model_io=dict(cot=['summary ' + issuer], model_called=True)))


class Pool:
    """N assessors that share one Gate (so a test can release by issuer) but are distinct objects."""

    def __init__(self, n):
        self.gate = Gate()
        self.members = [Member(self.gate, k) for k in range(n)]


class Member:
    def __init__(self, gate, index):
        self.gate, self.index, self.audit_hook, self.used = gate, index, None, []

    def assess(self, req):
        self.used.append(req.read()['issuer_id'])
        return self.gate.assess(req, self.audit_hook)  # each instance writes to its own job's journal


def queue(assessors, root, **identity):
    from larp.runtime.deferred_models import DeferredAssessments
    return DeferredAssessments(assessors, root=root, **{**dict(run_id='r', build_id='e' * 40, profile_hash='a' * 64),
                                                        **identity})


def wait_for(predicate, seconds=3):
    event = threading.Event()
    for _ in range(int(seconds * 100)):
        if predicate():
            return True
        event.wait(0.01)
    return predicate()


class ParallelQueue(unittest.TestCase):
    def test_pl1_one_assessor_keeps_the_single_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            pool = Pool(1)
            self.addCleanup(lambda: [e.set() for e in pool.gate.release.values()])
            q = queue(pool.members[0], tmp)  # a single assessor, as today
            self.assertTrue(q.submit('a', request('A')))
            self.assertTrue(q.busy)
            self.assertFalse(q.submit('b', request('B')))
            pool.gate.release['A'].set()
            self.assertTrue(q.finished.wait(2))
            self.assertEqual(q.ready()['round_id'], 'a')

    def test_pl2_three_companies_run_at_once_on_distinct_assessors_and_one_job_per_company(self):
        with tempfile.TemporaryDirectory() as tmp:
            pool = Pool(5)
            self.addCleanup(lambda: [e.set() for e in pool.gate.release.values()])
            q = queue(pool.members, tmp)
            for issuer in 'ABC':
                self.assertTrue(q.submit('round-' + issuer, request(issuer)), issuer)
            for issuer in 'ABC':
                self.assertTrue(pool.gate.entered[issuer].wait(2), issuer)  # all three in flight together
            self.assertEqual(sorted(i for m in pool.members for i in m.used), ['A', 'B', 'C'])
            self.assertTrue(all(len(m.used) <= 1 for m in pool.members))  # one job per assessor instance
            self.assertEqual(len(pool.gate.threads), 3)
            self.assertFalse(q.submit('round-A2', request('A', job='second')))  # A already has a pending job
            self.assertEqual(q.issuers(), {'A', 'B', 'C'})
            self.assertFalse(q.busy)  # two of five slots free
            for issuer in 'ABC':
                pool.gate.release[issuer].set()
            self.assertTrue(wait_for(lambda: q.ready() is not None and len(q.round_ids()) == 3))
            self.assertTrue(wait_for(lambda: all(not q.running(r) for r in q.round_ids())))
            order = []
            while (ready := q.ready()) is not None:
                order.append(ready['round_id'])
                q.ack(ready['round_id'])
            self.assertEqual(order, ['round-A', 'round-B', 'round-C'])  # submission order
            self.assertTrue(q.submit('round-A2', request('A', job='second')))
            pool.gate.release['A'].set()
            self.assertTrue(wait_for(lambda: not q.running('round-A2')))  # finish before the directory goes

    def test_pl4_a_hung_job_holds_only_its_own_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            pool = Pool(2)
            self.addCleanup(lambda: [e.set() for e in pool.gate.release.values()])
            q = queue(pool.members, tmp)
            self.assertTrue(q.submit('round-A', request('A')))  # never released while B and C run
            self.assertTrue(q.submit('round-B', request('B')))
            self.assertTrue(q.busy)
            pool.gate.release['B'].set()
            self.assertTrue(wait_for(lambda: q.ready() is not None))
            ready = q.ready()
            self.assertEqual(ready['round_id'], 'round-B')
            with self.assertRaises(ContractError):
                q.ack('round-A')  # still running
            q.ack('round-B')
            self.assertTrue(q.submit('round-C', request('C')))  # B's freed slot, while A still hangs
            self.assertTrue(pool.gate.entered['C'].wait(2))
            pool.gate.release['C'].set()
            self.assertTrue(wait_for(lambda: (q.ready() or {}).get('round_id') == 'round-C'))
            self.assertTrue(q.running('round-A'))  # A still hangs: it held only its own slot throughout
            pool.gate.release['A'].set()
            self.assertTrue(wait_for(lambda: not q.running('round-A')))  # finish before the directory goes

    def test_pl5_restart_recovers_every_pending_journal_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            pool = Pool(3)
            self.addCleanup(lambda: [e.set() for e in pool.gate.release.values()])
            q = queue(pool.members, tmp)
            for issuer in 'AB':
                q.submit('round-' + issuer, request(issuer))
            pool.gate.release['A'].set()
            self.assertTrue(wait_for(lambda: not q.running('round-A')))
            self.assertTrue(pool.gate.entered['B'].wait(2))
            restarted = queue(Pool(3).members, tmp)  # B's journal has no RESULT: interrupted at the crash
            self.assertEqual(restarted.round_ids(), {'round-A', 'round-B'})
            seen = {}
            while (ready := restarted.ready()) is not None:
                seen[ready['round_id']] = ready['audit']['state']
                restarted.ack(ready['round_id'])
            self.assertEqual(seen, {'round-A': 'COMPLETE', 'round-B': 'INTERRUPTED'})
            self.assertEqual(queue(Pool(3).members, tmp).round_ids(), set())
            pool.gate.release['B'].set()
            self.assertTrue(wait_for(lambda: not q.running('round-B')))  # the original process's thread ends

    def test_pl6_an_empty_assessor_list_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ContractError):
            queue([], tmp)


class SignedFill(ServiceHarness):
    """PL-2/PL-3 at the driver: `_signed_cycle` fills every free slot in one tick and commits one result per tick."""

    def test_pl2_pl3_one_tick_submits_one_job_per_company_and_results_commit_one_per_tick(self):
        from larp.runtime.deferred_models import DeferredAssessments
        h = self
        driver = h.service_driver()
        c = driver.coordinator
        pool = Pool(5)
        self.addCleanup(lambda: [e.set() for e in pool.gate.release.values()])
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        q = DeferredAssessments(pool.members, root=tmp.name, run_id=c.run_id, build_id=c.version_id,
                                profile_hash=c.profile_hash)
        driver.assessments = q
        items = iter([dict(round_id='filing:' + i + '#1', issuer_id=i, records=[{'record_id': i}], claim=None,
                           job={}) for i in 'ABC'])
        seen_busy = []

        def next_item(now_ms, epoch, busy=frozenset()):
            seen_busy.append(set(busy))
            return next(items, None)

        starts = []
        real_start = c.start

        def start(round_id, req, now_ms, **kw):
            if 'assessment_override' in kw and kw['assessment_override'] is not None:
                starts.append(round_id)
                return None
            return real_start(round_id, req, now_ms, **kw)

        with ExitStack() as stack:
            stack.enter_context(patch.object(driver.work, 'next', side_effect=next_item))
            stack.enter_context(patch.object(driver.work, 'request',
                                             side_effect=lambda w, cur, now: request(w['issuer_id'], c.run_id,
                                                                                     c.profile_hash)))
            stack.enter_context(patch('larp.runtime.schema.assessment_request'))
            stack.enter_context(patch.object(c, 'start', side_effect=start))
            summary = driver.once(h.w.clock())
            self.assertEqual(summary['assessment_queued'], 'filing:A#1')
            self.assertEqual(summary['assessments_queued'], ['filing:A#1', 'filing:B#1', 'filing:C#1'])
            self.assertEqual(seen_busy[:3], [set(), {'A'}, {'A', 'B'}])
            for issuer in 'ABC':
                self.assertTrue(pool.gate.entered[issuer].wait(2), issuer)
                pool.gate.release[issuer].set()
            self.assertTrue(wait_for(lambda: all(not q.running(r) for r in q.round_ids())))
            for expected in ('filing:A#1', 'filing:B#1', 'filing:C#1'):
                h.w.clock.now += 1000
                summary = driver.once(h.w.clock())
                self.assertEqual(summary['assessment_round_id'], expected)
            self.assertEqual(starts, ['filing:A#1', 'filing:B#1', 'filing:C#1'])
            self.assertFalse(q.round_ids())


class Composition(unittest.TestCase):
    def test_pl6_assessment_workers_bounds_and_distinct_routed_assessors(self):
        from larp.intelligence.model_budget import ModelBudget
        from larp.intelligence.routing import RoutedAssessor
        from larp.runtime import gate_a
        from larp.runtime.service import build_driver
        from tests.runtime.test_driver import Composition as Fixture, Store
        raw = (gate_a.ROOT / 'config/intelligence/aiand-routing.example.json').read_bytes()
        for workers, ok in ((1, True), (5, True), (0, False), (6, False), (True, False), ('2', False)):
            with self.subTest(workers=workers):
                fixture = Fixture(); fixture.setUp()
                try:
                    (fixture.root / 'routing.json').write_bytes(raw)
                    ModelBudget.initialize(fixture.root / 'openai-budget.sqlite', json.loads(raw)['budget_account'],
                                           initial_spent=0)
                    cfg = fixture.config(assessor='aiand_routed', execution='service', expiry_grace_ms=5000,
                                         intelligence_mode='live', model_routing_file=str(fixture.root / 'routing.json'),
                                         model_routing_sha256=hashlib.sha256(raw).hexdigest(),
                                         model_budget_root=str(fixture.root), model_adoption_ref='SYNTHETIC PL-6',
                                         assessment_workers=workers)
                    secrets = dict(fixture.secrets, LARP_AIAND_API_KEY='synthetic-aiand-runtime-key')
                    if not ok:
                        with self.assertRaises(ContractError):
                            build_driver(cfg, Store(), secrets)
                        continue
                    with patch('socket.create_connection', side_effect=AssertionError('no network')):
                        driver = build_driver(cfg, Store(), secrets)
                    driver.ports['evidence'].close()
                    pool = driver.assessments.assessors
                    self.assertEqual(len(pool), workers)
                    self.assertTrue(all(isinstance(a, RoutedAssessor) for a in pool))
                    self.assertEqual(len({id(a) for a in pool}), workers)
                    self.assertEqual(len({id(a.budget) for a in pool}), workers)  # own connection object each
                    self.assertEqual({a.budget.path for a in pool}, {pool[0].budget.path})  # one shared ledger
                finally:
                    fixture.doCleanups()

    def test_pl6_concurrent_admissions_never_exceed_the_released_allowance(self):
        from larp.intelligence.model_budget import AdmissionDeferred, ModelBudget
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'budget.sqlite'
            ModelBudget.initialize(path, 'synthetic', initial_spent=0, total=1_000_000, reserve=0)
            results, lock = [], threading.Lock()
            start = threading.Barrier(10)

            def admit(k):
                budget = ModelBudget(path, 'synthetic', total=1_000_000, reserve=0)
                start.wait()
                try:
                    token = budget.admit(300_000, 'request-' + str(k))
                except AdmissionDeferred:
                    token = None
                with lock:
                    results.append(token)
            threads = [threading.Thread(target=admit, args=(k,)) for k in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(10)
            admitted = [t for t in results if t is not None]
            self.assertEqual(len(results), 10)
            self.assertLessEqual(300_000 * len(admitted), 1_000_000)
            self.assertEqual(len(admitted), 3)


class Continuation(DriverHarness):
    """PL-7/PL-8 on the cadence path, with the real driver, store and replay (shadow execution settles at once)."""

    def driver(self, authority='MANDATORY_REDUCTION', *, issuers=(EXSEMI,), cadence_ms=HOUR, continuation=4):
        driver = super().driver(authority, issuers=issuers, cadence_ms=cadence_ms)
        driver.work.continuation_rounds = continuation
        return driver

    def held_and_flagged(self):
        """The 4.02 filing makes the NVDAB reduction mandatory; shadow execution never fills, so it stays due."""
        self.world(['EXSEMI_402_8K'])
        driver = self.driver()
        first = self.tick(driver)
        self.assertTrue(first['round_id'].startswith('filing:'))
        return driver

    def slot_start(self):
        return self.w.clock() // HOUR + 2

    def test_pl7_after_a_planned_trade_settles_the_next_tick_plans_again_up_to_the_limit(self):
        driver = self.held_and_flagged()
        slot = self.slot_start()
        self.w.clock.now = slot * HOUR
        ids = [self.tick(driver)['round_id']]
        for _ in range(6):
            ids.append(self.tick(driver)['round_id'])
        self.assertEqual(ids[:5], [f'cadence:{slot}#1'] + [f'cadence:{slot}:next{k}#1' for k in range(1, 5)])
        self.assertEqual(ids[5:], [None, None])  # the limit: 4 continuations in this slot
        for round_id in ids[:5]:
            plan = self.store.event(RUN, 'plan:' + round_id)['record']['plan']
            self.assertTrue(any(i['mandatory'] and i['side'] == 'SELL' for i in plan['intents']), round_id)
            record = self.store.event(RUN, 'plan:' + round_id)['record']
            if ':next' in round_id:
                self.assertEqual(record['accepted_evidence'], 'ONLY')
                self.assertEqual(record['request']['evidence_refs'], [])
        self.w.clock.now = (slot + 1) * HOUR
        self.assertEqual(self.tick(driver)['round_id'], f'cadence:{slot + 1}#1')

    def test_pl7_zero_continuations_keeps_todays_cadence(self):
        self.world(['EXSEMI_402_8K'])
        driver = self.driver(continuation=0)
        self.tick(driver)
        slot = self.slot_start()
        self.w.clock.now = slot * HOUR
        self.assertEqual(self.tick(driver)['round_id'], f'cadence:{slot}#1')
        self.assertIsNone(self.tick(driver)['round_id'])

    def test_pl7_a_round_that_plans_nothing_ends_the_chain(self):
        self.world(['EXSEMI_Q2_8K'])  # nothing to do: no holding, no trade
        driver = self.driver('SHADOW')
        for _ in range(5):
            self.tick(driver)
        slot = self.slot_start()
        self.w.clock.now = slot * HOUR
        self.assertEqual(self.tick(driver)['round_id'], f'cadence:{slot}#1')
        self.assertFalse(self.store.event(RUN, f'plan:cadence:{slot}#1')['record']['plan']['intents'])
        self.assertIsNone(self.tick(driver)['round_id'])

    def test_pl7_no_continuation_while_an_intent_is_in_flight(self):
        driver = self.held_and_flagged()
        slot = self.slot_start()
        self.w.clock.now = slot * HOUR
        with patch.object(driver.execution, 'settle_open', return_value=[]):  # the trade has not settled
            self.assertEqual(self.tick(driver)['round_id'], f'cadence:{slot}#1')
            self.assertIsNone(self.tick(driver)['round_id'])
            self.assertIsNone(self.tick(driver)['round_id'])
        self.assertEqual(self.tick(driver)['round_id'], f'cadence:{slot}:next1#1')

    def test_pl8_continuations_replay_and_a_restart_does_not_duplicate_one(self):
        from larp.integration.replay import replay_live
        from larp.integration.runtime import RuntimePlanner, StrategyPolicy, initial_policy_state, initial_projection
        from larp.integration.settlement import ExecutionBridge, settle
        from larp.storage.postgres import doc
        driver = self.held_and_flagged()
        slot = self.slot_start()
        self.w.clock.now = slot * HOUR
        self.assertEqual(self.tick(driver)['round_id'], f'cadence:{slot}#1')
        self.assertEqual(self.tick(driver)['round_id'], f'cadence:{slot}:next1#1')
        restarted = self.driver()
        self.assertEqual(self.tick(restarted)['round_id'], f'cadence:{slot}:next2#1')
        rounds = [r for r in self.logs() if r.startswith(f'cadence:{slot}')]
        self.assertEqual(rounds, [f'cadence:{slot}#1', f'cadence:{slot}:next1#1', f'cadence:{slot}:next2#1'])
        journal, expected = self.store.journal(RUN), self.store.verify(RUN)
        with self.store.transaction() as db:
            db.execute('TRUNCATE runs CASCADE')
        builder = driver.coordinator.context_builder
        dead = lambda *a: (_ for _ in ()).throw(AssertionError('live port called in replay'))
        builder.market = builder.health = builder.calendar = dead
        head = replay_live(journal, doc(initial_projection(pipeline.pipeline_ledger())), self.store, builder=builder,
                           run_id=RUN, wallet_id='fake-wallet', chain_id=56, version_id='integration-fixture',
                           profile_hash=self.h, address='0x' + '1' * 40, policy=StrategyPolicy(),
                           planner=RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                           execution=ExecutionBridge(), reducer=settle,
                           initial_policy_state=initial_policy_state(RUN, self.profile))
        self.assertEqual(head, expected)


class Configuration(unittest.TestCase):
    def test_pl9_examples_carry_both_settings_and_preparation_writes_them(self):
        from larp.runtime import gate_a
        for name in ('runtime.example.json', 'runtime.aiand-shadow.example.json'):
            driver = json.loads((gate_a.ROOT / 'config/runtime' / name).read_bytes())['driver']
            self.assertEqual((driver['assessment_workers'], driver['continuation_rounds']), (5, 4), name)
        from tests.strategy.test_fs1_final import live_prepared, profile
        runtime = json.loads(live_prepared(profile())['runtime.json'])['driver']
        self.assertEqual((runtime['assessment_workers'], runtime['continuation_rounds']), (5, 4))

    def test_pl9_continuation_rounds_bounds(self):
        from larp.runtime.service import build_driver
        from tests.runtime.test_driver import Composition as Fixture, Store
        for value, ok in ((0, True), (10, True), (-1, False), (11, False), (True, False)):
            with self.subTest(value=value):
                fixture = Fixture(); fixture.setUp()
                try:
                    cfg = fixture.config(continuation_rounds=value)
                    if ok:
                        driver = build_driver(cfg, Store(), fixture.secrets)
                        driver.ports['evidence'].close()
                        self.assertEqual(driver.work.continuation_rounds, value)
                    else:
                        with self.assertRaises(ContractError):
                            build_driver(cfg, Store(), fixture.secrets)
                finally:
                    fixture.doCleanups()

    def test_pl9_fs1_live_runtime_builds_five_routed_assessors_from_the_prepared_runtime(self):
        from larp.intelligence.model_budget import ModelBudget
        from larp.intelligence.routing import RoutedAssessor
        from larp.runtime import gate_a
        from larp.runtime.service import build_driver
        from tests.runtime.test_driver import Composition as Fixture, Store
        from tests.strategy.test_fs1_final import PROFILE, ROUTING, live_prepared, profile
        prepared = json.loads(live_prepared(profile())['runtime.json'])['driver']
        fixture = Fixture(); fixture.setUp()
        try:
            raw = ROUTING.read_bytes()
            spec = json.loads(raw)
            pacing = spec['openai_pacing']
            (fixture.root / 'routing.json').write_bytes(raw)
            ModelBudget.initialize(fixture.root / 'openai-budget.sqlite', spec['budget_account'],
                                   initial_spent=pacing['prior_spent_micro_usd'], total=pacing['total_micro_usd'],
                                   reserve=0, pacing=pacing)
            cfg = fixture.config(execution='service', intelligence_mode='live', expiry_grace_ms=5000,
                                 assessor='aiand_routed', model_routing_file=str(fixture.root / 'routing.json'),
                                 model_routing_sha256=hashlib.sha256(raw).hexdigest(),
                                 model_budget_root=str(fixture.root), model_adoption_ref='SYNTHETIC IDEA-093 PL-9',
                                 assessment_workers=prepared['assessment_workers'],
                                 continuation_rounds=prepared['continuation_rounds'])
            base = json.loads((gate_a.ROOT / 'config/runtime/runtime.example.json').read_bytes())['driver']
            for key in ('balance_check_interval_ms', 'balance_check_max_age_ms', 'price_jump_check_bps'):
                cfg['driver'][key] = base[key]
            cfg['driver']['balance_rpc_providers'] = [dict(url='https://rpc.invalid/', source_id='synthetic-rpc')]
            (fixture.root / 'profile.json').write_bytes(PROFILE.read_bytes())
            cfg['driver']['strategy_profile_sha256'] = gate_a.digest(PROFILE.read_bytes())
            from tests.marketdata.test_session_history import SEMANTICS
            from tests.runtime.test_gate_a import captured
            history_raw = json.dumps(SEMANTICS).encode()
            (fixture.root / 'token-history.json').write_bytes(history_raw)
            cfg['driver'].update(token_history_file=str(fixture.root / 'token-history.json'),
                                 token_history_sha256=hashlib.sha256(history_raw).hexdigest(),
                                 issuers=gate_a.issuer_map(captured()))
            cfg['mode'] = 'live'
            secrets = dict(fixture.secrets, LARP_AIAND_API_KEY='synthetic-aiand-runtime-key')
            with patch('socket.create_connection', side_effect=AssertionError('no network')):
                driver = build_driver(cfg, Store(), secrets)
            driver.ports['evidence'].close()
            pool = driver.assessments.assessors
            self.assertEqual(len(pool), 5)
            self.assertTrue(all(isinstance(a, RoutedAssessor) for a in pool))
            self.assertEqual(len({id(a) for a in pool}), 5)
            self.assertEqual(driver.work.continuation_rounds, 4)
        finally:
            fixture.doCleanups()

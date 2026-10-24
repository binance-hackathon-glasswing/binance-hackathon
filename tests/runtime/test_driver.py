"""IDEA-048 D1-D7: the shadow round driver over real components; external ports synthetic, nothing signed.

Real modules: Ingestor (fake EDGAR) -> SQLiteEvidenceStore jobs -> EvidenceWork -> EvidenceAssessor -> ContextBuilder
-> strategy -> RuntimePlanner -> Coordinator/PostgresStore -> ShadowExecution -> settlement -> round log -> replay.
"""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.intelligence.gate import lifecycle_policy_from
from larp.intelligence.models import RuleBaselineModel
from larp.intelligence.scenarios import EXMEM, EXSEMI, NOW, build_world
from larp.integration.replay import replay_live
from larp.integration.runtime import (ContextBuilder, RuntimePlanner, StrategyPolicy, initial_policy_state,
                                      initial_projection)
from larp.integration.settlement import ExecutionBridge, settle
from larp.research.fixtures import synthetic_profile
from larp.runtime.coordinator import Coordinator, batch_for
from larp.runtime.driver import SHADOW_REASON, EvidenceWork, RoundDriver, RuntimeHealth, SessionCalendar
from larp.runtime.live import check_live_start
from larp.runtime.service import EXIT_NOT_INTEGRATED, EXIT_REFUSED, NotIntegrated, build_driver, main
from larp.sources.store import SQLiteEvidenceStore
from larp.storage.postgres import doc
from tests.integration import test_evidence_pipeline as pipeline

RUN = pipeline.RUN
HOUR = 3_600_000


class DriverHarness(pipeline.PipelineHarness):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def world(self, keys, now_ms=0):
        evidence = SQLiteEvidenceStore(str(Path(self.tmp.name) / f'evidence-{len(keys)}-{now_ms}.sqlite'))
        self.addCleanup(evidence.close)
        self.w = build_world(keys, now_ms=now_ms, extra_filings=pipeline.EXTRA, store=evidence)
        return self.w

    def driver(self, authority='SHADOW', *, issuers=(EXSEMI,), cadence_ms=HOUR):
        self.profile = synthetic_profile(falsifier_ids=['F-ITEM-4.02'], falsifier_authority=authority)
        self.h = pipeline.profile_hash(self.profile)
        lifecycle = lifecycle_policy_from(self.w.config)
        builder = ContextBuilder(profile=self.profile, profile_hash=self.h, run_id=RUN,
                                 issuers={EXSEMI: {'token': 'NVDAB', 'underlying_id': EXSEMI}}, market=self.market,
                                 health=RuntimeHealth(self.store, RUN, self.epoch),
                                 calendar=lambda now: {'index': 80, 'remaining': 10}, lifecycle_policy=lifecycle)
        coordinator = Coordinator(self.store, self.w.assessor(RuleBaselineModel(self.w.clock)), StrategyPolicy(),
                                  RuntimePlanner(job_validity_ms=86_400_000, job_max_attempts=3),
                                  execution=ExecutionBridge(), run_id=RUN, version_id='integration-fixture',
                                  profile_hash=self.h, address='0x' + '1' * 40, context_builder=builder,
                                  initial_policy_state=initial_policy_state(RUN, self.profile), clock_ms=self.w.clock)
        work = EvidenceWork(store=self.store, evidence_store=self.w.store, run_id=RUN, config=self.w.config,
                            issuers=list(issuers), profile_hash=self.h, cadence_ms=cadence_ms,
                            lifecycle_policy=lifecycle)
        return RoundDriver(coordinator, work)

    def tick(self, driver, step_ms=1000):
        self.w.clock.now += step_ms
        return driver.once(self.w.clock())

    def logs(self):
        with self.store.transaction() as db:
            rows = db.execute('SELECT round_id,document FROM audit_events WHERE run_id=%s ORDER BY round_id',
                              (RUN,)).fetchall()
        return {r: json.loads(Document(bytes(raw)).read()['log'])['data'] for r, raw in rows}


class Driver(DriverHarness):
    def test_d1_an_ingested_filing_runs_once_across_cycles_and_restart(self):
        self.world(['EXSEMI_402_8K'])
        first = self.tick(self.driver())
        self.assertTrue(first['round_id'].startswith('filing:') and first['round_id'].endswith('#1'))
        self.assertEqual(first['closed'], 0)  # no intents under SHADOW authority: start closed it
        self.assertEqual(list(self.logs()), [first['round_id']])
        self.assertFalse(self.store.open_rounds(RUN))
        for driver in (self.driver(), self.driver()):  # the next cycle, then a restarted driver
            summary = self.tick(driver)
            self.assertFalse((summary['round_id'] or '').startswith('filing:'))
        filings = [r for r in self.logs() if r.startswith('filing:')]
        self.assertEqual(filings, [first['round_id']])

    def test_d1b_a_round_interrupted_before_planning_is_retried_under_the_next_attempt(self):
        self.world(['EXSEMI_402_8K'])
        driver = self.driver()
        item = driver.work.next(self.w.clock(), self.epoch)
        crashed = item['round_id']
        self.assertTrue(crashed.endswith('#1'))
        # A crash after the round opened and before its plan committed (e.g. during assessment).
        self.store.open_round(RUN, crashed, driver.work.request(item, self.store.load(RUN).read(), self.w.clock()),
                              self.epoch)
        summary = self.tick(driver)
        self.assertEqual(summary['round_id'], crashed[:-1] + '2')
        logs = self.logs()
        self.assertEqual(sorted(logs), [crashed, summary['round_id']])
        self.assertEqual(logs[crashed]['output']['errors'], ['PROCESS_INTERRUPTED'])
        self.assertFalse((self.tick(driver)['round_id'] or '').startswith('filing:'))

    def test_d2_shadow_ends_every_intent_unsigned_and_releases_reservations(self):
        self.world(['EXSEMI_402_8K'])
        before = self.store.load(RUN).read()['projection']['balances']
        driver = self.driver('MANDATORY_REDUCTION')
        with patch.object(self.store, 'command', side_effect=AssertionError('signing gate called')):
            summary = self.tick(driver)
        self.assertEqual(summary['closed'], 1)
        current = self.store.load(RUN).read()
        self.assertEqual(current['reservations'], [])
        self.assertEqual(current['projection']['balances'], before)
        self.assertFalse(self.store.open_rounds(RUN))
        log = self.logs()[summary['round_id']]
        self.assertTrue(log['orders'])
        self.assertEqual([o['side'] for o in log['orders']], ['SELL'])
        self.assertTrue(all('tx_hash' not in o for o in log['orders']))
        self.assertEqual([a['reason'] for a in log['output']['aborted']], [SHADOW_REASON] * len(log['orders']))

    def test_d3_cadence_rounds_run_once_per_slot_and_skip_issuers_without_records(self):
        self.world(['EXSEMI_Q2_8K'], now_ms=NOW)
        driver = self.driver(issuers=(EXSEMI, EXMEM))
        slot = self.w.clock() // HOUR + 2
        slot += slot % 2  # an even slot: EXSEMI, the issuer with a record
        self.w.clock.now = slot * HOUR
        self.assertEqual(self.tick(driver)['round_id'], f'cadence:{slot}#1')
        self.assertIsNone(self.tick(driver)['round_id'])  # same slot
        self.w.clock.now = (slot + 1) * HOUR
        self.assertIsNone(self.tick(driver)['round_id'])  # EXMEM has no record
        self.w.clock.now = (slot + 2) * HOUR
        self.assertEqual(self.tick(driver)['round_id'], f'cadence:{slot + 2}#1')
        self.assertEqual(sorted(self.logs()), [f'cadence:{slot}#1', f'cadence:{slot + 2}#1'])

    def test_d4_a_scheduled_review_job_runs_first_and_is_finished(self):
        self.world(['EXSEMI_402_8K'])
        payload = {'kind': 'REASSESS_ISSUER', 'issuer_id': EXSEMI, 'reason': 'SESSION_REVIEW', 'session': 80}
        job = {'job_id': 'evidence:' + 'a' * 64, 'lane': 'evidence', 'due_ms': self.w.clock(),
               'valid_until_ms': self.w.clock() + HOUR, 'max_attempts': 3, 'priority': 50, 'calendar_id': 'UTC',
               'tzdata_version': 'utc-only-no-tzdata', 'missed': 'catch_up', 'payload': payload}
        current = self.store.load(RUN)
        self.store.commit(batch_for(current, 'test:review-job', dict(kind='TEST_JOB'), jobs=[job]))
        driver = self.driver()
        self.assertEqual(self.tick(driver)['round_id'], 'review:' + 'a' * 64 + '#1')
        with self.store.transaction() as db:
            status = db.execute('SELECT status FROM jobs WHERE run_id=%s AND job_id=%s',
                                (RUN, job['job_id'])).fetchone()[0]
        self.assertEqual(status, 'DONE')
        self.assertTrue(self.tick(driver)['round_id'].startswith('filing:'))

    def test_d5_the_driver_journal_replays_to_the_same_head_without_live_ports(self):
        self.world(['EXSEMI_402_8K'])
        driver = self.driver('MANDATORY_REDUCTION')
        self.tick(driver)
        self.w.clock.now = (self.w.clock() // HOUR + 1) * HOUR  # next slot: a cadence round as well
        self.assertTrue(self.tick(driver)['round_id'].startswith('cadence:'))
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


def calendar_doc():
    sessions = []
    for n, day in enumerate(('2026-10-29', '2026-10-30', '2026-11-02')):
        sessions.append({'session_index': 100 + n, 'open_at': f'{day}T13:30:00+00:00',
                         'close_at': f'{day}T20:00:00+00:00'})
    return {'schema': 'USRegularSessions.v1', 'calendar_id': 'fixture-us-regular', 'content_hash': 'c' * 64,
            'sessions': sessions}


def ms(value):
    from datetime import datetime
    return int(datetime.fromisoformat(value).timestamp() * 1000)


class Calendar(unittest.TestCase):
    def test_d6_index_and_remaining_across_session_boundaries(self):
        c = SessionCalendar(calendar_doc())
        self.assertEqual(c(ms('2026-10-29T13:30:00+00:00')), {'index': 100, 'remaining': 3})
        self.assertEqual(c(ms('2026-10-29T20:00:00+00:00')), {'index': 100, 'remaining': 2})
        self.assertEqual(c(ms('2026-10-31T12:00:00+00:00')), {'index': 101, 'remaining': 1})  # weekend
        self.assertEqual(c(ms('2026-11-02T19:59:59+00:00')), {'index': 102, 'remaining': 1})
        for outside in ('2026-10-29T13:29:59+00:00', '2026-11-02T20:00:00+00:00'):
            with self.subTest(outside), self.assertRaises(ContractError):
                c(ms(outside))
        broken = calendar_doc()
        broken['sessions'][2]['session_index'] = 105
        with self.assertRaises(ContractError):
            SessionCalendar(broken)


class Store:
    def load(self, run_id):
        return doc(dict(epoch=2, wallet_id='0x' + '1' * 40, projection={'portfolio': {'bnb_decimals': 18}}))


class Composition(unittest.TestCase):
    wallet = '0x' + '1' * 40

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / 'evidence').mkdir()
        # The poller's DELETE-journal store; the runtime opens it read-only (IDEA-047 R15).
        SQLiteEvidenceStore(str(self.root / 'evidence' / 'evidence.sqlite'), journal_mode='DELETE').close()
        profile = json.dumps(synthetic_profile()).encode()
        calendar = json.dumps(calendar_doc()).encode()
        (self.root / 'profile.json').write_bytes(profile)
        (self.root / 'calendar.json').write_bytes(calendar)
        self.driver_block = dict(execution='shadow', assessor='deterministic', intelligence_mode='development',
                                 evidence_root=str(self.root / 'evidence'),
                                 market_artifact_root=str(self.root / 'market'), cadence_ms=HOUR,
                                 strategy_profile_file=str(self.root / 'profile.json'),
                                 strategy_profile_sha256=hashlib.sha256(profile).hexdigest(),
                                 session_calendar_file=str(self.root / 'calendar.json'),
                                 session_calendar_sha256=hashlib.sha256(calendar).hexdigest(),
                                 issuers={'SEC-CIK-0001045810': {'token': 'NVDAB', 'underlying_id': 'NVDA'}})
        self.secrets = dict(AI_SEEDS_ADDRESS=self.wallet, BINANCE_API_KEY='synthetic-key',
                            BINANCE_SECRET_KEY='synthetic-secret')

    def config(self, **driver):
        return dict(schema='RuntimeService.v1', run_id='run', build_id='a' * 40, mode='offline',
                    wallet_address=self.wallet, driver=dict(self.driver_block, **driver))

    def test_d7_valid_configuration_builds_real_ports_that_pass_the_live_start_check(self):
        driver = build_driver(self.config(), Store(), self.secrets)
        self.assertIsInstance(driver, RoundDriver)
        self.assertFalse(driver.signing)
        check_live_start(mode='dev', ports=driver.ports, secrets=self.secrets, wallet_address=self.wallet,
                         run_wallet=self.wallet, ai_seeds_dir=str(self.root / 'ai-seeds'),
                         nonce_dir=str(self.root / 'nonce'))

    def test_d7_hosted_models_are_not_integrated(self):
        with self.assertRaises(NotIntegrated):
            build_driver(self.config(assessor='anthropic:model:high'), Store(), self.secrets)

    def test_ar7_aiand_routing_is_pinned_opt_in_and_shadow_only(self):
        from larp.intelligence.model_budget import ModelBudget
        from larp.intelligence.routing import RoutedAssessor
        raw = (Path(__file__).resolve().parents[2] / 'config/intelligence/aiand-routing.example.json').read_bytes()
        spec = json.loads(raw)
        path = self.root / 'routing.json'
        path.write_bytes(raw)
        ModelBudget.initialize(self.root / 'openai-budget.sqlite', spec['budget_account'], initial_spent=0)
        settings = dict(assessor='aiand_routed', model_routing_file=str(path),
                        model_routing_sha256=hashlib.sha256(raw).hexdigest(), model_budget_root=str(self.root))
        secrets = dict(self.secrets, LARP_AIAND_API_KEY='synthetic-aiand-runtime-key')
        driver = build_driver(self.config(**settings), Store(), secrets)
        self.assertIsInstance(driver.coordinator.assessor, RoutedAssessor)
        self.assertFalse(driver.signing)
        for change in (dict(execution='service', expiry_grace_ms=5000), dict(model_routing_sha256='0'*64)):
            with self.subTest(change=change), self.assertRaises(ContractError):
                build_driver(self.config(**dict(settings, **change)), Store(), secrets)
        with self.assertRaises(ValueError):
            build_driver(self.config(**settings), Store(), self.secrets)

    def routed_settings(self):
        from larp.intelligence.model_budget import ModelBudget
        raw = (Path(__file__).resolve().parents[2] / 'config/intelligence/aiand-routing.example.json').read_bytes()
        (self.root / 'routing.json').write_bytes(raw)
        ModelBudget.initialize(self.root / 'openai-budget.sqlite', json.loads(raw)['budget_account'],
                               initial_spent=0)
        return dict(model_routing_file=str(self.root / 'routing.json'),
                    model_routing_sha256=hashlib.sha256(raw).hexdigest(), model_budget_root=str(self.root))

    def test_sg1_routed_model_artifacts_go_to_a_private_runtime_store(self):
        from larp.sources.store import FileArtifacts, OverlayArtifacts
        secrets = dict(self.secrets, LARP_AIAND_API_KEY='synthetic-aiand-runtime-key')
        driver = build_driver(self.config(assessor='aiand_routed', **self.routed_settings()), Store(), secrets)
        router = driver.coordinator.assessor
        model_root = (self.root / 'market' / 'model').resolve()
        self.assertIsInstance(router.artifacts, FileArtifacts)
        self.assertEqual(router.artifacts.root, model_root)
        for model in (router.routine, *router.external):
            self.assertIs(model._artifacts, router.artifacts)
        reader = router.make_assessor(router.routine).reader
        self.assertIsInstance(reader.artifacts, OverlayArtifacts)
        self.assertIs(reader.artifacts.private, router.artifacts)
        self.assertEqual(reader.artifacts.shared.root, (self.root / 'evidence' / 'artifacts').resolve())
        # SG-7a: the deterministic path writes its tool results to the same private store.
        plain = build_driver(self.config(), Store(), self.secrets).coordinator.assessor
        self.assertIsInstance(plain.reader.artifacts, OverlayArtifacts)
        self.assertEqual(plain.reader.artifacts.private.root, model_root)
        self.assertEqual(plain.reader.artifacts.shared.root, (self.root / 'evidence' / 'artifacts').resolve())

    def test_sg3_shadow_example_builds_in_dev_shadow_and_refuses_service_or_live(self):
        from larp.intelligence.routing import RoutedAssessor
        root = Path(__file__).resolve().parents[2] / 'config/runtime'
        base = json.loads((root / 'runtime.example.json').read_text())
        example = json.loads((root / 'runtime.aiand-shadow.example.json').read_text())
        routing = ('assessor', 'execution', 'model_routing_file', 'model_routing_sha256', 'model_budget_root')
        self.assertEqual({k: v for k, v in example.items() if k != 'driver'}, {k: v for k, v in base.items() if k != 'driver'})
        self.assertEqual({k: v for k, v in example['driver'].items() if k not in routing},
                         {k: v for k, v in base['driver'].items() if k not in routing + ('expiry_grace_ms',)})
        d = example['driver']
        self.assertEqual((d['assessor'], d['execution'], d['model_routing_sha256']), ('aiand_routed', 'shadow', None))
        for key in ('model_budget_root', 'market_artifact_root'):
            self.assertTrue(d[key].startswith('/var/lib/larp-runtime/'), key)  # the unit's StateDirectory
        self.assertTrue(d['model_routing_file'].startswith('/etc/larp/'))
        # Fill the placeholders and host paths with synthetic values; every other setting comes from the example.
        live_profile = json.dumps(synthetic_profile(mode='LIVE')).encode()
        (self.root / 'live-profile.json').write_bytes(live_profile)
        # With PR #87 (IDEA-058) a hosted dev run takes only the explicit `shadow` evidence settings (GA03); before
        # it, `development` stands in, since the `live` values are unset.
        shadow = (root.parents[1] / 'config/intelligence/intelligence.shadow.v1.json').exists()
        filled = dict(self.driver_block, **self.routed_settings(),
                      balance_rpc_providers=[dict(url='https://rpc.invalid/', source_id='synthetic-rpc')],
                      intelligence_mode='shadow' if shadow else 'development', day_roll_window_ms=900_000,
                      strategy_profile_file=str(self.root / 'live-profile.json'),
                      strategy_profile_sha256=hashlib.sha256(live_profile).hexdigest())
        driver_block = dict(d, **{k: v for k, v in filled.items() if k not in ('assessor', 'execution')})
        self.assertFalse([k for k, v in driver_block.items() if v is None])  # every placeholder filled
        config = dict(example, run_id='run', build_id='a' * 40, wallet_address=self.wallet, driver=driver_block)
        self.assertEqual(config['mode'], 'dev')
        secrets = dict(self.secrets, LARP_AIAND_API_KEY='synthetic-aiand-runtime-key')
        driver = build_driver(config, Store(), secrets)
        self.assertIsInstance(driver.coordinator.assessor, RoutedAssessor)
        self.assertFalse(driver.signing)
        for change in (dict(config, driver=dict(driver_block, execution='service')),
                       dict(config, driver=dict(driver_block, execution='service', expiry_grace_ms=30000)),
                       dict(config, mode='live')):
            with self.subTest(execution=change['driver']['execution'], mode=change['mode']), \
                    self.assertRaises(ContractError):
                build_driver(change, Store(), secrets)

    def test_e9_service_execution_builds_and_binds_the_profile_to_quotes(self):
        from larp.runtime.driver import ServiceExecution, ShadowExecution
        driver = build_driver(self.config(execution='service', expiry_grace_ms=5000, day_roll_window_ms=900_000,
                                          max_quote_rounds=1), Store(), self.secrets)
        self.assertIsInstance(driver.execution, ServiceExecution)
        self.assertIsNotNone(driver.day_roll)
        self.assertEqual(driver.max_quote_rounds, 1)
        market = driver.ports['market']
        self.assertEqual(market.quote_limits['slippage_bps'], synthetic_profile()['slippage_bps'])
        self.assertIs(driver.coordinator.context_builder.market, driver.market)  # the prefetched feed (#24)
        self.assertTrue(driver.ports['evidence'].read_only)
        shadow = build_driver(self.config(), Store(), self.secrets)
        self.assertIsInstance(shadow.execution, ShadowExecution)
        self.assertIsNone(shadow.day_roll)

    def test_hosted_market_port_gets_the_basis_check_with_the_pinned_tickers(self):
        """IDEA-086 (SJ-10-BASIS01): without a verifier every observation is unverified and no entry is planned."""
        from larp.marketdata.basis import BasisVerifier
        for execution in ('shadow', 'service'):
            extra = dict(expiry_grace_ms=5000, day_roll_window_ms=900_000) if execution == 'service' else {}
            with self.subTest(execution=execution):
                market = build_driver(self.config(execution=execution, **extra), Store(), self.secrets).ports['market']
                self.assertIsInstance(market.basis_verifier, BasisVerifier)
                self.assertEqual(market.basis_verifier.expected, {'NVDAB': 'NVDA'})

    def untrusted_settings(self, **changes):
        """IDEA-088 QV7: the run-3 S1 profile (initial-only gas), a pinned test router policy and balance RPCs."""
        from tests.execution.test_untrusted_router import policy
        raw = json.dumps(policy()).encode()
        (self.root / 'router-policy.json').write_bytes(raw)
        profile = (Path(__file__).resolve().parents[2] / 'docs/build/evidence/s1-rehearsal-profile-20261023/'
                   'rehearsal-s1-deterministic.json').read_bytes()
        (self.root / 's1-profile.json').write_bytes(profile)
        value = dict(untrusted_router_policy_file=str(self.root / 'router-policy.json'),
                     untrusted_router_policy_sha256=hashlib.sha256(raw).hexdigest(),
                     strategy_profile_file=str(self.root / 's1-profile.json'),
                     strategy_profile_sha256=hashlib.sha256(profile).hexdigest(),
                     balance_rpc_providers=[dict(url='https://rpc-a.invalid/', source_id='a'),
                                            dict(url='https://rpc-b.invalid/', source_id='b')],
                     balance_check_interval_ms=600_000, balance_check_max_age_ms=1_800_000,
                     price_jump_check_bps=3000)
        value.update(changes)
        return {k: v for k, v in value.items() if v is not None}

    def test_qv7_a_pinned_untrusted_router_policy_gives_the_market_port_its_quote_verifier(self):
        from larp.marketdata.quote_verifier import ProviderRpc, UntrustedQuoteVerifier
        settings = self.untrusted_settings()
        market = build_driver(self.config(**settings), Store(), self.secrets).ports['market']
        verifier = market.quote_verifier
        self.assertIsInstance(verifier, UntrustedQuoteVerifier)
        self.assertEqual((verifier.decoder.mode, verifier.decoder.policy_sha256),
                         ('untrusted', settings['untrusted_router_policy_sha256']))
        self.assertIsInstance(verifier.decoder.rpc, ProviderRpc)
        self.assertEqual([p.source_id for p in verifier.decoder.rpc.providers], ['a', 'b'])
        self.assertIsNone(build_driver(self.config(), Store(), self.secrets).ports['market'].quote_verifier)

    def test_qv7_the_policy_pair_is_pinned_complete_and_needs_its_inputs(self):
        top_up = json.dumps(synthetic_profile()).encode()
        (self.root / 'top-up-profile.json').write_bytes(top_up)
        for name, change in (
                ('hash', dict(untrusted_router_policy_sha256='0' * 64)),
                ('file only', dict(untrusted_router_policy_sha256=None)),
                ('hash only', dict(untrusted_router_policy_file=None)),
                ('no balance providers', dict(balance_rpc_providers=None, balance_check_interval_ms=None,
                                              balance_check_max_age_ms=None, price_jump_check_bps=None)),
                ('top-up profile', dict(strategy_profile_file=str(self.root / 'top-up-profile.json'),
                                        strategy_profile_sha256=hashlib.sha256(top_up).hexdigest()))):
            with self.subTest(name), self.assertRaises(ContractError):
                build_driver(self.config(**self.untrusted_settings(**change)), Store(), self.secrets)

    def test_e9_execution_mode_must_be_named_and_known(self):
        for change in (dict(execution=None), dict(execution='sign'), dict(signing=False),
                       dict(execution='service'),  # no expiry grace
                       dict(execution='service', expiry_grace_ms=-1), dict(max_quote_rounds='2')):
            with self.subTest(change), self.assertRaises(ContractError):
                build_driver(self.config(**change), Store(), self.secrets)

    def test_d7_inconsistent_inputs_refuse_the_start(self):
        refused = [dict(strategy_profile_sha256='0' * 64), dict(session_calendar_sha256='0' * 64),
                   dict(issuers={'SEC-CIK-0001045810': {'token': 'TSLAB', 'underlying_id': 'NVDA'}}),
                   dict(issuers={'SEC-CIK-0000000001': {'token': 'NVDAB', 'underlying_id': 'NVDA'}}),
                   dict(evidence_root=str(self.root / 'missing')), dict(cadence_ms=1000), dict(issuers=None)]
        for change in refused:
            with self.subTest(change), self.assertRaises(ContractError):
                build_driver(self.config(**change), Store(), self.secrets)
        for config, secrets in ((dict(self.config(), mode='dev'), self.secrets),  # dev needs a LIVE profile
                                ({k: v for k, v in self.config().items() if k != 'driver'}, self.secrets),
                                (self.config(), {})):
            with self.subTest(config=config.get('mode'), secrets=bool(secrets)), self.assertRaises(ContractError):
                build_driver(config, Store(), secrets)

    def test_e9_the_runtime_example_names_every_setting_the_service_reads(self):
        from larp.runtime.service import DRIVER_KEYS, OPTIONAL_DRIVER_INTEGERS, validate_config
        example = json.loads((Path(__file__).resolve().parents[2] / 'config/runtime/runtime.example.json').read_text())
        self.assertEqual(example['schema'], 'RuntimeService.v1')
        self.assertTrue(set(DRIVER_KEYS) | set(OPTIONAL_DRIVER_INTEGERS) <= set(example['driver']))
        for key in ('ai_seeds_dir', 'nonce_dir'):
            self.assertTrue(example[key].startswith('/var/lib/larp-runtime/'))  # the unit's StateDirectory
        self.assertTrue(example['driver']['market_artifact_root'].startswith('/var/lib/larp-runtime/'))
        self.assertFalse([k for k in json.dumps(example).lower().split('"') if 'private' in k or 'mnemonic' in k])
        ca = self.root / 'rds-ca.pem'
        ca.write_bytes(b'-----BEGIN CERTIFICATE-----\nfixture\n-----END CERTIFICATE-----\n')
        filled = dict(example, run_id='run', build_id='a' * 40, wallet_address=self.wallet, database_host='db.invalid',
                      database_ca_file=str(ca), database_ca_sha256=hashlib.sha256(ca.read_bytes()).hexdigest())
        validate_config(filled)

    def test_d7_main_maps_refusals_to_exit_codes_without_restart_loops(self):
        raw = json.dumps(dict(self.config(), database_dsn_file='/synthetic', max_failures=3, clear_after=2,
                              interval_seconds=5)).encode()
        (self.root / 'runtime.json').write_bytes(raw)
        (self.root / 'manifest.json').write_bytes(b'{}')
        options = ['run', '--config', str(self.root / 'runtime.json'), '--manifest', str(self.root / 'manifest.json'),
                   '--root', str(self.root)]
        manifest = dict(build_id='a' * 40, runtime_config_sha256=hashlib.sha256(raw).hexdigest())
        for error, code in ((ContractError('refused'), EXIT_REFUSED), (NotIntegrated('later'), EXIT_NOT_INTEGRATED)):
            with self.subTest(code=code), patch('larp.runtime.preflight.verify_release', return_value=manifest), \
                    patch('larp.runtime.service.open_store'), patch('larp.runtime.service.verify_registered_manifest'), \
                    patch('larp.runtime.credentials.runtime_secrets', return_value={}), \
                    patch('larp.runtime.service.build_driver', side_effect=error), patch('builtins.print'):
                self.assertEqual(main(options), code)

    def test_d7_an_unbindable_record_directory_refuses_the_start_with_exit_4(self):
        # #59 (WR17): an OSError while binding ai_seeds_dir must not crash into Restart=always.
        blocker = self.root / 'blocker'
        blocker.write_text('not a directory')
        raw = json.dumps(dict(self.config(), mode='dev', database_dsn_file='/synthetic', max_failures=3,
                              clear_after=2, interval_seconds=5, cycle_timeout_seconds=30,
                              ai_seeds_dir=str(blocker / '.ai-seeds'), nonce_dir=str(self.root / 'nonce'))).encode()
        (self.root / 'runtime.json').write_bytes(raw)
        (self.root / 'manifest.json').write_bytes(b'{}')
        options = ['run', '--config', str(self.root / 'runtime.json'), '--manifest', str(self.root / 'manifest.json'),
                   '--root', str(self.root)]
        manifest = dict(build_id='a' * 40, runtime_config_sha256=hashlib.sha256(raw).hexdigest())
        with patch('larp.runtime.preflight.verify_release', return_value=manifest), \
                patch('larp.runtime.service.open_store', return_value=Store()), \
                patch('larp.runtime.service.verify_registered_manifest'), \
                patch('larp.runtime.credentials.runtime_secrets', return_value=self.secrets), \
                patch('larp.runtime.service.build_driver', return_value=type('Driver', (), dict(ports={}))()), \
                patch('larp.runtime.service.signal.signal'), patch('builtins.print') as printed:
            self.assertEqual(main(options), EXIT_REFUSED)
        self.assertEqual(json.loads(printed.call_args.args[0])['reason'], 'LIVE_START_REFUSED')
        self.assertFalse((self.root / 'nonce').exists())  # refused before any directory was bound


if __name__ == '__main__':
    unittest.main()

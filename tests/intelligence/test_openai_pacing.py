"""OP-01 prospective regressions: synthetic accounting and real verifier, no network."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from larp.contracts import ContractError, Document
from larp.intelligence.common import IntelligenceError
from larp.intelligence.model_budget import AdmissionDeferred, ModelBudget, main as budget_cli, validate_pacing
from larp.intelligence.routing import validate_routing_spec
from larp.runtime import gate_a
from tests.intelligence import test_aiand_routing as fixtures


def policy(start=1000):
    return dict(schema='OpenAIPacing.v1', total_micro_usd=50_000_000,
                prior_spent_micro_usd=2_000_000, start_ms=start,
                end_ms=start+4000, period_ms=1000)


class Pacing(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'budget.sqlite'; self.now=1000; self.p=policy()

    def init(self):
        return ModelBudget.initialize(self.path,'paced',initial_spent=2_000_000,
            total=50_000_000,reserve=0,pacing=self.p,clock_ms=lambda:self.now)

    def reopen(self, **kw):
        return ModelBudget(self.path,'paced',total=50_000_000,reserve=0,
                           pacing=kw.get('pacing',self.p),clock_ms=lambda:self.now)

    def test_period_carry_forward_and_final_release(self):
        b=self.init(); self.assertEqual(b.snapshot()['available_micro_usd'],12_000_000)
        token=b.admit(1_000_000,'one'); b.settle(token,500_000)
        self.now=2000
        self.assertEqual(self.reopen().snapshot()['available_micro_usd'],23_500_000)
        self.now=4000
        self.assertEqual(b.snapshot()['available_micro_usd'],47_500_000)
        self.assertFalse(b.snapshot()['external_only'])

    def test_temporary_refusal_recovers_next_period(self):
        b=self.init(); token=b.admit(12_000_000,'first')
        with self.assertRaises(IntelligenceError): b.admit(1,'paced')
        self.assertFalse(self.reopen().snapshot()['external_only'])
        b.settle(token,None); self.now=2000
        self.assertIsNotNone(self.reopen().admit(12_000_000,'later'))

    def test_atomic_workers_do_not_overspend_period_or_latch(self):
        self.init()
        def attempt(n):
            try: return self.reopen().admit(8_000_000,str(n))
            except IntelligenceError: return None
        with ThreadPoolExecutor(max_workers=4) as pool: tokens=list(pool.map(attempt,range(4)))
        self.assertEqual(sum(t is not None for t in tokens),1)
        self.assertFalse(self.reopen().snapshot()['external_only'])

    def test_policy_binding_and_legacy_bypass_refused(self):
        self.init()
        with self.assertRaises(IntelligenceError): ModelBudget(self.path,'paced',reserve=0)
        changed=deepcopy(self.p); changed['end_ms']+=1
        with self.assertRaises(IntelligenceError): self.reopen(pacing=changed)
        with self.assertRaises(FileExistsError): self.init()

    def test_windows_clock_rollback_and_restart_fail_closed_without_latching(self):
        self.now=999; b=self.init()
        with self.assertRaisesRegex(AdmissionDeferred,'NOT_STARTED'): b.admit(1,'early')
        self.now=3000; self.assertEqual(b.snapshot()['available_micro_usd'],36_000_000)
        self.now=2000
        with self.assertRaisesRegex(AdmissionDeferred,'CLOCK_ROLLBACK'): self.reopen().admit(1,'backward')
        self.assertFalse(b.snapshot()['external_only'])
        self.now=3000; self.assertIsNotNone(b.admit(1,'caught-up'))
        self.now=5000
        with self.assertRaisesRegex(AdmissionDeferred,'WINDOW_ENDED'): b.admit(1,'late')
        self.assertFalse(b.snapshot()['external_only'])

    def test_full_allocation_latches_but_oversize_request_does_not(self):
        b=self.init()
        with self.assertRaisesRegex(AdmissionDeferred,'EXCEEDS_REMAINING'): b.admit(49_000_000,'too-big')
        token=b.admit(1_000_000,'small'); b.settle(token,0)
        self.now=4000; token=b.admit(48_000_000,'last-period')
        self.assertIsNone(b.admit(1,'fully-allocated'))
        b.settle(token,1)  # refunds never clear a safety latch
        again=self.reopen()
        self.assertTrue(again.snapshot()['external_only'])
        self.assertEqual(again.snapshot()['reason'],'OPENAI_ALLOCATION_EXHAUSTED')
        self.assertIsNone(again.admit(1,'no-reset'))

    def test_underestimated_usage_latches_and_unknown_usage_keeps_bound(self):
        b=self.init(); token=b.admit(100,'unknown'); b.settle(token,None)
        self.assertEqual(self.reopen().snapshot()['charged_micro_usd'],2_000_100)
        token=b.admit(100,'underestimated'); b.settle(token,101)
        self.assertEqual(self.reopen().snapshot()['reason'],'OPENAI_USAGE_EXCEEDED_BOUND')

    def test_explicit_migration_preserves_all_rows_and_latches(self):
        old=ModelBudget.initialize(self.path,'paced',initial_spent=2_000_000)
        reserved=old.admit(100,'in-flight'); unknown=old.admit(200,'unknown')
        old.settle(unknown,None); old.external_only('OPENAI_CREDIT_EXHAUSTED')
        def rows():
            with sqlite3.connect(self.path) as db:
                return (db.execute('SELECT * FROM charges ORDER BY id').fetchall(),
                        db.execute('SELECT * FROM switches ORDER BY id').fetchall())
        before=rows()
        b=ModelBudget.enable_pacing(self.path,'paced',pacing=self.p,clock_ms=lambda:self.now)
        self.assertEqual(rows(),before)
        self.assertEqual(b.snapshot()['charged_micro_usd'],2_000_300)
        self.assertEqual(b.snapshot()['reserve_micro_usd'],0)
        self.assertEqual(b.snapshot()['reason'],'OPENAI_CREDIT_EXHAUSTED')
        with self.assertRaises(IntelligenceError): old.admit(1,'stale-worker')
        b.settle(reserved,50)  # outstanding reservations survive and remain settleable
        self.assertTrue(b.snapshot()['external_only'])
        with self.assertRaises(IntelligenceError): ModelBudget.enable_pacing(self.path,'paced',pacing=self.p)

    def test_migration_with_wrong_baseline_leaves_legacy_ledger_unchanged(self):
        old=ModelBudget.initialize(self.path,'paced',initial_spent=3_000_000)
        with self.assertRaises(IntelligenceError):
            ModelBudget.enable_pacing(self.path,'paced',pacing=self.p)
        self.assertEqual(old.snapshot()['charged_micro_usd'],3_000_000)
        self.assertEqual(old.snapshot()['reserve_micro_usd'],10_000_000)

    def test_invalid_policy_refused_before_ledger_creation(self):
        changes=[dict(start_ms=True),dict(period_ms=0),dict(end_ms=1000),dict(total_micro_usd=2_000_000),
                 dict(prior_spent_micro_usd=-1),dict(period_ms=1.5),dict(schema='OpenAIPacing.v2'),
                 dict(extra='PRIVATE_INPUT_SENTINEL'),dict(total_micro_usd=2**63)]
        for change in changes:
            p=dict(self.p,**change)
            with self.subTest(change=change),self.assertRaises(IntelligenceError): validate_pacing(p)
        with self.assertRaises(IntelligenceError):
            ModelBudget.initialize(self.path,'paced',initial_spent=0,total=50_000_000,reserve=0,pacing=self.p)
        self.assertFalse(self.path.exists())

    def test_non_divisible_window_releases_all_by_final_partial_period(self):
        self.p['end_ms']=4500
        b=self.init(); self.assertEqual(b.snapshot()['available_micro_usd'],12_000_000)
        self.now=4000; self.assertEqual(b.snapshot()['available_micro_usd'],48_000_000)


class Preferred(unittest.TestCase):
    def setUp(self):
        # Reuse only the synthetic HTTP/evidence fixture, not its legacy test cases.
        self.fx=fixtures.Routing(); self.fx.setUp(); self.addCleanup(self.fx.doCleanups)
        f=self.fx; (f.root/'openai-budget.sqlite').unlink()
        f.s=json.loads((fixtures.ROOT/'config/intelligence/aiand-routing.openai-preferred.example.json').read_bytes())
        f.s['openai_pacing']=policy(f.w.clock())
        ModelBudget.initialize(f.root/'openai-budget.sqlite',f.s['budget_account'],
            initial_spent=2_000_000,total=50_000_000,reserve=0,
            pacing=f.s['openai_pacing'],clock_ms=f.w.clock)

    def _dispatch_cutoff(self, overshoot):
        f=self.fx; primary=f.build().openai
        end=f.s['openai_pacing']['end_ms']
        f.w.clock.advance(end-1-f.w.clock())
        keep=primary.model._keep
        def prepare(body):
            keep(body); f.w.clock.advance(1+overshoot)
        with patch.object(primary.model, '_keep', side_effect=prepare):
            reply=primary.step(fixtures.request(dict(gaps=[], claimable=[])), 1000).read()
        self.assertEqual(reply['error'], 'OPENAI_PACING_WINDOW_ENDED')
        self.assertFalse(f.calls)
        self.assertEqual(primary.budget.snapshot()['charged_micro_usd'], 2_000_000)
        self.assertFalse(primary.budget.snapshot()['external_only'])
        with sqlite3.connect(primary.budget.path) as db:
            rows=db.execute("SELECT amount,state FROM charges WHERE request_id='r:1'").fetchall()
        self.assertEqual(rows, [(0, 'SETTLED')])

    def test_dispatch_at_cutoff_after_request_artifact_preparation_refunds_unsent(self):
        self._dispatch_cutoff(0)

    def test_dispatch_after_cutoff_after_request_artifact_preparation_refunds_unsent(self):
        self._dispatch_cutoff(1)

    def test_dispatch_rechecks_clock_and_latch_without_clearing_safety_state(self):
        f=self.fx; primary=f.build().openai; keep=primary.model._keep
        def rollback(body):
            keep(body); f.w.clock.now -= 1  # explicit simulated wall-clock rollback
        with patch.object(primary.model, '_keep', side_effect=rollback):
            reply=primary.step(fixtures.request(dict(gaps=[], claimable=[])), 1000).read()
        self.assertEqual(reply['error'], 'OPENAI_CLOCK_ROLLBACK')
        f.w.clock.advance(1)
        def latch(body):
            keep(body); primary.budget.external_only('OPENAI_CREDIT_EXHAUSTED')
        with patch.object(primary.model, '_keep', side_effect=latch):
            reply=primary.step(fixtures.request(dict(gaps=[], claimable=[])), 1000).read()
        self.assertEqual(reply['error'], 'OPENAI_CREDIT_EXHAUSTED')
        self.assertFalse(f.calls)
        snapshot=primary.budget.snapshot()
        self.assertEqual(snapshot['charged_micro_usd'], 2_000_000)
        self.assertEqual(snapshot['reason'], 'OPENAI_CREDIT_EXHAUSTED')

    def test_dispatch_accounting_failure_keeps_bound_and_sends_nothing(self):
        f=self.fx; primary=f.build().openai; keep=primary.model._keep
        def unavailable(body):
            keep(body); primary.budget.path.rename(f.root/'temporarily-unavailable.sqlite')
        with patch.object(primary.model, '_keep', side_effect=unavailable):
            reply=primary.step(fixtures.request(dict(gaps=[], claimable=[])), 1000).read()
        self.assertEqual(reply['error'], 'MODEL_BUDGET_UNAVAILABLE')
        self.assertFalse(f.calls)
        self.assertFalse(primary.budget.path.exists())
        (f.root/'temporarily-unavailable.sqlite').rename(primary.budget.path)
        self.assertGreater(primary.budget.snapshot()['charged_micro_usd'], 2_000_000)
        self.assertTrue(primary.budget_unavailable)

    def test_dispatch_before_cutoff_settles_but_sent_timeout_keeps_bound(self):
        from tests.intelligence.test_providers import openai_reply
        f=self.fx; primary=f.build().openai; sent=[]
        def success(url, headers, body, timeout):
            sent.append(body)
            return 200, json.dumps(openai_reply(fixtures.FINISH)(json.loads(body))).encode()
        with patch.object(primary.model, '_transport', side_effect=success):
            reply=primary.step(fixtures.request(dict(gaps=[], claimable=[])), 1000).read()
        self.assertEqual(reply['status'], 'OK')
        self.assertEqual(len(sent), 1)
        before=primary.budget.snapshot()['charged_micro_usd']
        self.assertEqual(before, 2_000_000+reply['cost']['amount_micro_usd'])
        def timeout(*args):
            sent.append(args[2]); raise TimeoutError('synthetic sent request')
        with patch.object(primary.model, '_transport', side_effect=timeout):
            reply=primary.step(fixtures.request(dict(gaps=[], claimable=[])), 1000).read()
        self.assertEqual(reply['status'], 'TIMEOUT')
        self.assertEqual(len(sent), 2)
        self.assertGreater(primary.budget.snapshot()['charged_micro_usd'], before)
        with sqlite3.connect(primary.budget.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM charges WHERE state='UNKNOWN'").fetchone()[0], 1)

    def test_openai_is_first_and_aiand_reviews_original_evidence(self):
        f=self.fx; _,result=f.run_assessment(f.build())
        self.assertEqual(f.calls[0][0],'openai')
        self.assertEqual(result['routing']['stages'][0]['stage'],'openai-primary')
        self.assertTrue(any(c[:3]==('aiand','moonshotai/kimi-k3','high') for c in f.calls))
        self.assertEqual(result['routing']['budget']['reserve_micro_usd'],0)

    def test_missing_openai_key_uses_high_effort_fallback(self):
        f=self.fx; _,result=f.run_assessment(f.build(key=False))
        self.assertEqual(f.calls[0][:3],('aiand','moonshotai/kimi-k3','high'))
        self.assertEqual(result['status'],'ASSESSED')

    def test_model_identity_is_stable_across_key_and_period_changes(self):
        f=self.fx; identity=f.build().model.identity
        self.assertEqual(identity,f.build(key=False).model.identity)
        f.w.clock.advance(1000)
        self.assertEqual(identity,f.build().model.identity)

    def test_clean_primary_needs_no_external_review_when_not_sampled(self):
        f=self.fx; f.s['audit_sample_bps']=0
        with patch('larp.intelligence.routing._review_reasons',return_value=[]):
            # Control the review classifier, exercising only the no-review branch here.
            _,result=f.run_assessment(f.build())
        self.assertEqual(result['status'],'ASSESSED')
        self.assertTrue(f.calls)
        self.assertTrue(all(c[0]=='openai' for c in f.calls))
        self.assertEqual(len(result['routing']['stages']),1)

    def test_temporary_pacing_uses_aiand_then_restores_openai_next_period(self):
        f=self.fx; router=f.build(); b=router.budget
        token=b.admit(b.snapshot()['available_micro_usd'],'synthetic-other-work'); b.settle(token,None)
        _,result=f.run_assessment(router)
        self.assertFalse(any(c[0]=='openai' for c in f.calls))
        self.assertEqual(f.calls[0][:3],('aiand','moonshotai/kimi-k3','high'))
        self.assertFalse(result['routing']['budget']['external_only'])
        steps=result['model_io']['steps']
        self.assertEqual(steps[0]['response']['error'],'OPENAI_PACING_LIMIT')
        f.w.clock.advance(1000); f.calls.clear(); f.run_assessment(f.build())
        self.assertEqual(f.calls[0][0],'openai')

    def test_credit_exhaustion_uses_fallback_and_persists_across_rebuild(self):
        f=self.fx; f.openai_error='credit_balance_exhausted'
        _,result=f.run_assessment(f.build())
        self.assertEqual(f.calls[0][0],'openai')
        self.assertEqual(result['status'],'ASSESSED')
        self.assertEqual(result['routing']['budget']['reason'],'OPENAI_CREDIT_EXHAUSTED')
        self.assertGreater(result['routing']['budget']['charged_micro_usd'],2_000_000)
        f.openai_error=None; f.calls.clear(); f.run_assessment(f.build())
        self.assertFalse(any(c[0]=='openai' for c in f.calls))

    def test_rate_limit_does_not_latch_exhaustion(self):
        f=self.fx; f.openai_error='rate_limit_exceeded'
        _,result=f.run_assessment(f.build())
        self.assertEqual(result['status'],'ASSESSED')
        self.assertFalse(result['routing']['budget']['external_only'])
        f.openai_error=None; f.calls.clear(); f.run_assessment(f.build())
        self.assertEqual(f.calls[0][0],'openai')

    def test_both_external_failures_strip_required_review_authority(self):
        f=self.fx; f.fail_external=True
        _,result=f.run_assessment(f.build())
        self.assertNotEqual(result['status'],'ASSESSED')
        self.assertFalse(result['findings'])
        self.assertFalse(result['event_findings'])
        self.assertEqual([c[:3] for c in f.calls if c[0]=='aiand'],
                         [('aiand','moonshotai/kimi-k3','high'),('aiand','zai-org/glm-5.3','high')])

    def test_disagreement_abstains_instead_of_selecting_a_model(self):
        f=self.fx
        original=f.openai
        def disagree(*args):
            status,raw=original(*args); payload=json.loads(raw)
            payload['output'][0]['content'][0]['text']=json.dumps(fixtures.FINISH)
            return status,json.dumps(payload).encode()
        f.openai=disagree
        _,result=f.run_assessment(f.build())
        self.assertEqual(result['status'],'ABSTAIN')
        self.assertIn('ROUTING_FINDING_DISAGREEMENT',result['reasons'])
        self.assertFalse(result['findings'])

    def test_missing_storage_does_not_recreate_or_dispatch_openai(self):
        f=self.fx; router=f.build(); (f.root/'openai-budget.sqlite').unlink()
        _,result=f.run_assessment(router)
        self.assertFalse(any(c[0]=='openai' for c in f.calls))
        self.assertEqual(result['routing']['budget']['reason'],'MODEL_BUDGET_UNAVAILABLE')
        self.assertEqual(result['status'],'ASSESSED')
        self.assertFalse((f.root/'openai-budget.sqlite').exists())

    def test_original_evidence_and_exact_stage_prompt_survive_deferred_audit_wrapper(self):
        f=self.fx; router=f.build(); events=[]
        request=f.w.request(['EXSEMI_Q3_8K'],issuer_id=fixtures.EXSEMI,job_id='audit-primary')
        result=router.assess_deferred(request,audit_hook=events.append).read()
        self.assertEqual(result['status'],'ASSESSED')
        requests=[e for e in events if e['kind']=='MODEL_REQUEST']
        self.assertEqual(requests[0]['stage'],'openai-primary')
        for e in requests:
            stage=e['stage']; model=router.openai if stage=='openai-primary' else router.external[int(stage[-1])]
            # The provider refuses a mismatched prompt hash before its synthetic HTTP transport.
            provider=model.model if stage=='openai-primary' else model
            self.assertEqual(e['request']['prompt_sha256'],sha256(provider._prompt.encode()).hexdigest())
        for stage in result['routing']['stages']:
            record=json.loads(f.w.artifacts.get(stage['result_artifact']))
            self.assertTrue({r['record_id'] for r in request.read()['evidence_refs']} <=
                            {r['record_id'] for r in record['evidence_used']})
        self.assertLessEqual(result['budget_used']['tool_calls'],request.read()['budget']['tool_calls'])
        for key in (fixtures.OPENAI_KEY,fixtures.AIAND_KEY): self.assertNotIn(key,json.dumps(events))

    def test_primary_timeout_keeps_deferred_lane_until_actual_provider_exits(self):
        from larp.runtime.deferred_models import DeferredAssessments
        f=self.fx; entered=threading.Event(); release=threading.Event(); timed_out=threading.Event()
        original=f.openai; workers=[]; join=threading.Thread.join
        def blocked(*args):
            workers.append(threading.current_thread()); entered.set()
            if not release.wait(5): raise TimeoutError('Synthetic transport not released')
            return original(*args)
        def observe(worker,timeout=None):
            join(worker,timeout)
            if timeout is not None and worker.name.startswith('larp-assess:') and worker.is_alive(): timed_out.set()
        f.openai=blocked; router=f.build()
        req=f.w.request(['EXSEMI_Q3_8K'],issuer_id=fixtures.EXSEMI,job_id='blocked',deadline_ms=200)
        q=DeferredAssessments(router,root=f.root/'deferred',run_id=req.read()['run_id'],
                              build_id='e'*40,profile_hash=req.read()['policy_profile_hash'])
        def cleanup():
            release.set(); q.finished.wait(5)
            for w in workers: join(w,5)
        self.addCleanup(cleanup)
        with patch.object(threading.Thread,'join',observe):
            self.assertTrue(q.submit('blocked',req)); self.assertTrue(entered.wait(2)); self.assertTrue(timed_out.wait(2))
            self.assertFalse(q.finished.is_set()); self.assertFalse(q.submit('other',req))
            with self.assertRaises(ContractError): q.ack('blocked')
            f.w.clock.advance(200)  # exhaust the shared request budget before releasing the late primary
            release.set(); self.assertTrue(q.finished.wait(2))
        ready=q.ready(); self.assertEqual(ready['result']['status'],'UNAVAILABLE')
        self.assertEqual(len(workers),1)
        self.assertFalse(any(c[0]=='aiand' for c in f.calls))
        self.assertEqual(ready['audit']['events'][-1]['kind'],'RESULT')
        self.assertTrue(any(e['kind']=='MODEL_RESPONSE' for e in ready['audit']['events']))
        q.ack('blocked')


class Preparation(unittest.TestCase):
    def setUp(self):
        self.raw=(fixtures.ROOT/'config/intelligence/aiand-routing.openai-preferred.example.json').read_bytes()

    def test_v3_preparation_is_offline_pinned_and_reports_actual_primary(self):
        from tests.runtime.test_gate_a import assembled
        with ExitStack() as stack:
            for name in ('ModelBudget','AIandChatModel','OpenAIResponsesModel'):
                stack.enter_context(patch('larp.intelligence.routing.'+name,side_effect=AssertionError('Offline only')))
            files=assembled(model_routing_raw=self.raw,model_routing_sha256=gate_a.digest(self.raw))
        self.assertEqual(files['model-routing.json'],self.raw)
        report=json.loads(files['preparation-report.json'])['model_routing']
        self.assertEqual(report['routine'],'gpt-6.1-sol')
        self.assertEqual(report['reviewer'],'moonshotai/kimi-k3')
        self.assertEqual(report['reserve_micro_usd'],0)
        self.assertEqual(set(report['checks'].values()),{'NOT_RUN'})
        self.assertEqual(report['openai_pacing'],json.loads(self.raw)['openai_pacing'])

    def test_bad_v3_policy_and_low_effort_fallback_refuse_offline(self):
        for mutate in (lambda s:s['openai_pacing'].update(period_ms=True),
                       lambda s:s['openai_pacing'].update(end_ms=0),
                       lambda s:s['external_reviewers'][0].update(effort='low'),
                       lambda s:s['external_reviewers'].__setitem__(0,None),
                       lambda s:s.update(openai_pacing={}),lambda s:s.pop('openai_pacing')):
            s=json.loads(self.raw); mutate(s)
            with self.subTest(spec=s),self.assertRaises(IntelligenceError): validate_routing_spec(s)

    def test_budget_cli_initializes_and_reopens_only_matching_paced_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); config=root/'routing.json'; config.write_bytes(self.raw)
            args=['--path',str(root/'budget.sqlite'),'--account','larp-openai-2026','--routing-file',str(config)]
            with redirect_stdout(StringIO()) as out:
                self.assertEqual(budget_cli(['init',*args,'--initial-spent-micro-usd','2000000']),0)
            self.assertEqual(json.loads(out.getvalue())['reserve_micro_usd'],0)
            with redirect_stdout(StringIO()) as out: budget_cli(['status',*args])
            self.assertEqual(json.loads(out.getvalue())['charged_micro_usd'],2_000_000)
            with self.assertRaises(IntelligenceError):
                budget_cli(['status','--path',str(root/'budget.sqlite'),'--account','larp-openai-2026'])

"""IDEA-083 AB1–AB15: synthetic regression witnesses, written before implementation."""
from copy import deepcopy
import itertools
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from larp.contracts import Document
from larp.intelligence import routing
from larp.intelligence.common import digest
from larp.intelligence.config import load_config
from larp.runtime.deferred_models import DeferredAssessments
from tests.intelligence import test_openai_pacing as pacing
from tests.intelligence.test_aiand_routing import EXSEMI


class Outcomes(unittest.TestCase):
    def test_ab15_complete_selection_matrix_in_both_arrival_orders(self):
        primary = dict(status='ASSESSED', findings=[{'finding': 'primary'}],
                       event_findings=[], falsifiers=[], rationale='primary', result_id='primary')
        variants = [dict(primary), dict(primary, findings=[{'finding': 'different'}]),
                    dict(primary, status='ABSTAIN'), dict(primary, status='TIMEOUT'),
                    dict(primary, status='ERROR'), dict(primary, status='UNAVAILABLE'), None]
        for pstatus, a, b, order in itertools.product(
                ('ASSESSED', 'ABSTAIN', 'UNAVAILABLE', 'ERROR', 'TIMEOUT', None),
                range(len(variants)), range(len(variants)), ((0, 1), (1, 0))):
            with self.subTest(primary=pstatus, reviewers=(a, b), order=order):
                p = dict(primary, status=pstatus) if pstatus else None
                arrivals = {i: deepcopy(variants[(a, b)[i]]) for i in order}
                reviews = [arrivals[i] for i in (0, 1)]
                selected, outcome, verdicts = routing.review_decision(p, reviews)
                if pstatus == 'ASSESSED':
                    expected = 'DISSENT' if a in (1, 2) or b in (1, 2) else \
                        'CONFIRMED' if 0 in (a, b) else 'INCOMPLETE'
                    self.assertEqual(outcome, expected)
                    self.assertEqual(selected['status'], 'ABSTAIN' if expected == 'DISSENT' else 'ASSESSED')
                    if expected != 'DISSENT':
                        self.assertEqual(selected, p)
                else:
                    assessed = [v for v in reviews if v and v['status'] == 'ASSESSED']
                    expected = 'DISSENT' if a in (0, 1) and b in (0, 1) and a != b else \
                        'FALLBACK' if assessed else 'NONE_AVAILABLE'
                    self.assertEqual(outcome, expected)
                    if expected == 'FALLBACK':
                        self.assertEqual(selected, assessed[0])
                self.assertEqual(len(verdicts), 2)

    def test_ab6_declared_maximum(self):
        for mode in ('development', 'shadow'):
            self.assertEqual(load_config(mode=mode).max_deadline_ms, 180000)

    def test_ab6_absolute_bound_equality_and_rollback(self):
        from larp.intelligence.deadlines import Deadline
        clock, mono = [1000], [1.0]
        bound = Deadline(180000, lambda: clock[0], monotonic=lambda: mono[0])
        clock[0] += 40000
        self.assertEqual(bound.remaining(), 140000)
        mono[0] += 180
        self.assertEqual(bound.remaining(), 0)  # wall time cannot extend authority
        clock[0] = 999
        self.assertEqual(bound.remaining(), 0)
        clock[0] = 1000
        self.assertEqual(bound.remaining(), 0)  # rollback cancellation never refreshes


class RoutedConcurrency(unittest.TestCase):
    def setUp(self):
        self.owner = pacing.Preferred(); self.owner.setUp(); self.addCleanup(self.owner.doCleanups)
        self.fx = self.owner.fx

    def test_ab3_reviewers_overlap_and_primary_content_is_preserved(self):
        f = self.fx
        barrier = threading.Barrier(2)
        transport = f.aiand
        arrived = set()
        lock = threading.Lock()
        def send(url, headers, raw, timeout):
            model = json.loads(raw)['model']
            with lock:
                first = model not in arrived
                arrived.add(model)
            if first:
                barrier.wait(2)
            return transport(url, headers, raw, timeout)
        f.aiand = send
        request, value = f.run_assessment(f.build())
        self.assertEqual(value['status'], 'ASSESSED')
        self.assertEqual(value['routing']['review_outcome'], 'CONFIRMED')
        self.assertEqual(len(value['routing']['reviewers']), 2)
        primary = json.loads(f.w.artifacts.get(value['routing']['stages'][0]['result_artifact']))
        self.assertEqual(value['routing']['primary_result_id'], primary['result_id'])
        for key in ('claims', 'findings', 'event_findings', 'falsifiers', 'proposed_thesis', 'rationale', 'confidence'):
            self.assertEqual(value[key], primary[key], key)
        without = {k: v for k, v in value.items() if k != 'result_id'}
        self.assertEqual(value['result_id'], 'res:' + digest('larp.intel.result.v1', without))
        self.assertLessEqual(value['budget_used']['tool_calls'], 6)

    def test_ab4_primary_drain_does_not_prevent_review_dispatch(self):
        f = self.fx
        release, entered = threading.Event(), threading.Event()
        reviewers = {m['model_id']: threading.Event() for m in f.s['external_reviewers']}
        original, external = f.openai, f.aiand
        def blocked(*args):
            entered.set()
            release.wait(3)
            return original(*args)
        def review(url, headers, raw, timeout):
            reviewers[json.loads(raw)['model']].set()
            return external(url, headers, raw, timeout)
        f.openai, f.aiand = blocked, review
        router = f.build()
        req = f.w.request(['EXSEMI_Q3_8K'], issuer_id=EXSEMI, job_id='owned', deadline_ms=600)
        q = DeferredAssessments(router, root=f.root/'owned', run_id=req.read()['run_id'],
                                build_id='e'*40, profile_hash=req.read()['policy_profile_hash'])
        try:
            self.assertTrue(q.submit('round', req))
            self.assertTrue(entered.wait(1))
            for event in reviewers.values():
                self.assertTrue(event.wait(1), 'reviewer blocked by primary drain')
            self.assertIsNone(q.ready())
            self.assertFalse(q.submit('replacement', req))
        finally:
            release.set()
            self.assertTrue(q.finished.wait(3))
        events = q.ready()['audit']['events']
        self.assertEqual(events[-1]['kind'], 'RESULT')
        self.assertTrue(any(e['kind'] == 'MODEL_RESPONSE' and e['stage'] == 'openai-primary' for e in events))

    def test_ab6_provider_preparation_cannot_dispatch_after_deadline(self):
        f = self.fx
        provider = f.build().external[0]
        # Exercise the real HTTP adapter after its own request/artifact preparation.
        while hasattr(provider, 'model'):
            provider = provider.model
        keep = provider._keep
        def slow_keep(raw):
            keep(raw)
            f.w.clock.advance(101)
        provider._keep = slow_keep
        from tests.intelligence.test_providers import request
        result = provider.step(request(), 100).read()
        self.assertEqual(result['status'], 'TIMEOUT')
        self.assertFalse(f.calls)

    def test_ab11_both_hung_reviewers_leave_primary_frozen_and_owned(self):
        f = self.fx
        release = threading.Event()
        entered = threading.Barrier(3)
        original = f.aiand
        def blocked(*args):
            entered.wait(2)
            release.wait(3)
            return original(*args)
        f.aiand = blocked
        router = f.build()
        req = f.w.request(['EXSEMI_Q3_8K'], issuer_id=EXSEMI, job_id='late', deadline_ms=600)
        try:
            box = {}
            caller = threading.Thread(target=lambda: box.update(result=router.assess(req).read()))
            caller.start()
            entered.wait(2)
            caller.join(2)
            self.assertFalse(caller.is_alive())
            result = box['result']
            self.assertEqual(result['routing']['review_outcome'], 'INCOMPLETE')
            self.assertEqual(result['status'], 'ASSESSED')
            self.assertEqual(len(result['model_io']['in_flight_calls']), 2)
            self.assertEqual(router.assess(req).read()['reasons'], ['ASSESSMENT_GROUP_BUSY'])
            frozen = Document.from_dict(result).payload
        finally:
            release.set()
            for worker in router._workers:
                worker.join(3)
        self.assertEqual(Document.from_dict(result).payload, frozen)

    def test_ab1_observed_timings_dissent_and_non_assessed_fallback(self):
        f = self.fx
        router = f.build()
        req, template = f.run_assessment(router)
        original_factory = router.make_assessor
        for primary_status in ('ASSESSED', 'UNAVAILABLE'):
            start = f.w.clock()
            barrier = threading.Barrier(2)
            clock_lock = threading.Lock()
            allowances = []
            def factory(model):
                delegate = original_factory(model)
                class Scripted:
                    request_namespace = ''
                    _validate = delegate._validate
                    _abandoned = delegate._abandoned
                    registry = delegate.registry
                    _reviews = delegate._reviews
                    def assess(inner, request, **kwargs):
                        label = inner.request_namespace.rstrip(':')
                        value = deepcopy(template)
                        value['model_io'] = dict(steps=[], tool_calls=[], cot=[], model_called=False,
                                                 requests_started=0, no_model_call_reason='SYNTHETIC')
                        allowances.append(request.read()['budget']['tool_calls'])
                        if label == 'openai-primary':
                            f.w.clock.advance(18000)
                            value['status'] = primary_status
                        else:
                            barrier.wait(2)
                            with clock_lock:
                                f.w.clock.now = max(f.w.clock(), start+18000+(34000 if label.endswith('0') else 10000))
                            value['status'] = 'ABSTAIN' if label.endswith('0') else 'ASSESSED'
                        value['result_id'] = label
                        return Document.from_dict(value)
                return Scripted()
            router.make_assessor = factory
            raw = req.read(); raw['budget']['deadline_ms'] = 180000
            value = router.assess(Document.from_dict(raw)).read()
            self.assertEqual(value['status'], 'ABSTAIN' if primary_status == 'ASSESSED' else 'ASSESSED')
            self.assertEqual(value['routing']['review_outcome'], 'DISSENT' if primary_status == 'ASSESSED' else 'FALLBACK')
            self.assertEqual(f.w.clock()-start, 52000)
            self.assertEqual(sorted(allowances), [1, 2, 3])
            self.assertLessEqual(sum(allowances), 6)
            router.make_assessor = original_factory


class JournalConcurrency(unittest.TestCase):
    def test_ab7_audit_failure_cannot_publish_accepted_result(self):
        from tests.runtime.test_signed_models import Blocking, request
        with tempfile.TemporaryDirectory() as tmp:
            model = Blocking(); model.release.set()
            q = DeferredAssessments(model, root=tmp, run_id='r', build_id='e'*40, profile_hash='a'*64)
            original = q._append_locked
            def fail(path, event):
                if event['kind'] == 'MODEL_RESPONSE':
                    raise OSError('synthetic private endpoint must not be logged')
                return original(path, event)
            with patch.object(q, '_append_locked', fail):
                q.submit('failed', request())
                self.assertTrue(q.finished.wait(2))
            ready = q.ready()
            self.assertIsNone(ready['result'])
            self.assertEqual(ready['audit']['state'], 'FAILED')
            self.assertNotIn('private endpoint', json.dumps(ready))
            from larp.contracts import ContractError
            with self.assertRaises(ContractError):
                q.ack('failed')
            reopened = DeferredAssessments(model, root=tmp, **q.identity)
            with self.assertRaises(ContractError):
                reopened.ack('failed')
            with self.assertRaises(ContractError):
                reopened.submit('another', request())

    def test_ab7_simultaneous_append_has_one_valid_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            q = DeferredAssessments(None, root=tmp, run_id='r', build_id='e'*40, profile_hash='a'*64)
            path = q.root/'race.jsonl'; path.touch()
            barrier = threading.Barrier(2)
            original = q._read
            def synchronized_read(p):
                result = original(p)
                try:
                    barrier.wait(.15)
                except threading.BrokenBarrierError:
                    pass
                return result
            errors = []
            def write(i):
                try:
                    q._append(path, dict(kind='STAGE', stage=str(i)))
                except Exception as exc:
                    errors.append(type(exc).__name__)
            with patch.object(q, '_read', synchronized_read):
                workers = [threading.Thread(target=write, args=(i,)) for i in range(2)]
                for w in workers: w.start()
                for w in workers: w.join(2)
            self.assertFalse(errors)
            self.assertEqual({e['stage'] for e in q._read(path)}, {'0', '1'})

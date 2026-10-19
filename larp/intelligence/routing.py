"""Opt-in IDEA-057 routing, sharing one deadline/tool budget.

Every stage runs the real EvidenceAssessor/verifier against original evidence. The OpenAI
budget is durable and independent of wallet/run IDs. All-external operation includes hard
reviews; an unavailable reviewer never turns a failed assessment into CLEAR evidence.
"""
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
import time
import threading
from types import SimpleNamespace

from larp.contracts import ContractError, Document
from larp.intelligence.agent import EvidenceAssessor, _structured_assessment
from larp.intelligence.aiand import AIandChatModel, validate_settings
from larp.intelligence.common import IntelligenceError, digest, require_hash, sha256_hex
from larp.intelligence.deadlines import Deadline, MAX_ASSESSMENT_MS, MAX_PRIMARY_MS, MAX_REVIEW_MS
from larp.intelligence.config import CONFIG_DIR
from larp.intelligence.model_budget import AdmissionDeferred, ModelBudget, validate_pacing, validate_trial
from larp.intelligence.models import ModelIdentity, response
from larp.intelligence.providers import OpenAIResponsesModel

# Stage prompts (IDEA-081): Markdown addenda appended to the core assessor prompt, read only from the release.
STAGE_PROMPT_DIR = CONFIG_DIR / 'prompts' / 'routing'
MAX_STAGE_PROMPT_BYTES = 16 * 1024
OPENAI_PRICE = dict(input_micro_usd_per_mtok=2_000_000, output_micro_usd_per_mtok=10_000_000,
                    source='https://developers.openai.com/api/docs/models/gpt-6.1-sol;2026-10-15;standard')


def validate_routing_spec(spec, prompt_dir=None):
    """Validate public configuration without credentials, budget storage, models or network I/O.

    AIandRouting.v2 adds one pinned stage prompt per model (IDEA-081); each is read from the
    release's routing prompt directory and checked against its hash here, so preparation
    refuses what startup would refuse. V3 additionally freezes OpenAI-primary credit pacing."""
    fields = {'schema', 'provenance', 'routine', 'external_reviewers', 'openai_model', 'openai_effort',
              'max_output_tokens', 'budget_account', 'audit_sample_bps', 'audit_seed'}
    preferred = type(spec) is dict and spec.get('schema') == 'AIandRouting.v3'
    staged = type(spec) is dict and spec.get('schema') in ('AIandRouting.v2', 'AIandRouting.v3')
    entry_fields = {'model_id', 'effort', 'catalog'} | ({'prompt'} if staged else set())
    if staged:
        fields = fields | {'openai_prompt'}
    if preferred:
        fields = fields | {'openai_pacing'}
        if 'openai_trial' in spec:
            fields = fields | {'openai_trial'}
    if (type(spec) is not dict or set(spec) != fields or spec['schema'] not in ('AIandRouting.v1', 'AIandRouting.v2', 'AIandRouting.v3')
            or spec['openai_model'] != 'gpt-6.1-sol'
            or type(spec['openai_effort']) is not str or spec['openai_effort'] not in ('low', 'medium', 'high')
            or type(spec['max_output_tokens']) is not int or not 0 < spec['max_output_tokens'] <= 16000
            or type(spec['budget_account']) is not str or not spec['budget_account'].strip()
            or len(spec['budget_account']) > 100
            or type(spec['audit_sample_bps']) is not int or not 0 <= spec['audit_sample_bps'] <= 10000
            or type(spec['audit_seed']) is not str or not spec['audit_seed'].strip()
            or type(spec['provenance']) is not dict
            or set(spec['provenance']) != {'source', 'checked', 'scope'}
            or any(type(v) is not str or not v.strip() for v in spec['provenance'].values())
            or type(spec['external_reviewers']) is not list or not 1 <= len(spec['external_reviewers']) <= 2):
        raise IntelligenceError('Invalid AIand routing specification')
    if preferred:
        validate_pacing(spec['openai_pacing'])
        if 'openai_trial' in spec:
            validate_trial(spec['openai_trial'])
            if not spec['openai_pacing']['start_ms'] <= spec['openai_trial']['start_ms'] < \
                    spec['openai_trial']['end_ms'] <= spec['openai_pacing']['end_ms']:
                raise IntelligenceError('Trial window must fit pacing window')
    for entry in [spec['routine'], *spec['external_reviewers']]:
        if type(entry) is not dict or set(entry) != entry_fields:
            raise IntelligenceError('Invalid AIand routing model entry')
        validate_settings(entry['model_id'], entry['effort'], entry['catalog'], spec['max_output_tokens'])
    if preferred and any(entry['effort'] not in ('high', 'max') for entry in spec['external_reviewers']):
        raise IntelligenceError('OpenAI preferred routing requires high-effort external fallback')
    if staged:
        for prompt in [spec['routine']['prompt'], *(e['prompt'] for e in spec['external_reviewers']),
                       spec['openai_prompt']]:
            stage_prompt_bytes(prompt, STAGE_PROMPT_DIR if prompt_dir is None else prompt_dir)
    # The runtime hashes the spec as a Document (no floats); refuse here so preparation cannot pass what startup refuses.
    try:
        Document.from_dict(spec)
    except ContractError:
        raise IntelligenceError('AIand routing specification is not a canonical document') from None


class BudgetedOpenAI:
    """Reserve before every actual POST; a crash/unknown usage retains the full charge."""
    def __init__(self, model, budget, *, monotonic=time.monotonic):
        self.model, self.budget, self.identity = model, budget, model.identity
        self.monotonic = monotonic
        self.budget_unavailable = False

    def request_payload(self, request):
        return self.model.request_payload(request)

    def has_artifact(self, value):
        return self.model.has_artifact(value)

    def step(self, request, remaining_ms):
        started, wall = self.model.clock(), self.monotonic()
        if self.budget_unavailable:
            return response(request.read(), status='ERROR', output=None, latency_ms=0,
                            error='MODEL_BUDGET_UNAVAILABLE')
        # UTF-8 byte bound plus protocol margin; deliberately over-reserve instead of assuming
        # English chars/4. Refuse long-context pricing rather than charging short-context rates.
        input_bound = len(self.request_payload(request)) * 2 + 8192
        if remaining_ms <= 0 or input_bound > 272000:
            return response(request.read(), status='ERROR', output=None, latency_ms=0,
                            error='OPENAI_INPUT_OR_TIME_BOUND')
        maximum = (input_bound * 2_000_000 + self.model.max_output_tokens * 10_000_000 + 999999) // 1_000_000
        try:
            token = self.budget.admit(maximum, request.read()['request_id'])
        except AdmissionDeferred as error:
            return response(request.read(), status='ERROR', output=None, latency_ms=0, error=error.reason)
        if token is None:
            return response(request.read(), status='ERROR', output=None, latency_ms=0,
                            error='OPENAI_OPERATING_LIMIT')
        elapsed = max(self.model.clock() - started, math.ceil((self.monotonic() - wall) * 1000))
        remaining_ms -= elapsed
        if remaining_ms <= 0:
            # Keep the durable reservation conservatively; no POST is allowed after abandonment.
            return response(request.read(), status='TIMEOUT', output=None, latency_ms=elapsed,
                            error='DEADLINE_EXCEEDED')
        # The reservation is durable even if step raises, the worker is abandoned, or the process dies.
        if getattr(self.budget, 'pacing', None) is not None:
            try:
                reply = self.model.step(request, remaining_ms,
                    before_dispatch=lambda: self.budget.before_dispatch(token))
            except AdmissionDeferred as error:
                # The boundary check durably settled this known-unsent POST at zero.
                return response(request.read(), status='ERROR', output=None,
                                latency_ms=max(0, self.model.clock()-started), error=error.reason)
            except IntelligenceError:
                # No reliable accounting means no dispatch. Do not invent a refund.
                self.budget_unavailable = True
                return response(request.read(), status='ERROR', output=None,
                                latency_ms=max(0, self.model.clock()-started),
                                error='MODEL_BUDGET_UNAVAILABLE')
        else:
            reply = self.model.step(request, remaining_ms)
        value = reply.read()
        usage = value.get('usage') or {}
        actual = None
        if value['status'] == 'OK':
            actual = (usage['input_tokens'] * 2_000_000 + usage['output_tokens'] * 10_000_000 + 999999) // 1_000_000
        try:
            self.budget.settle(token, actual)
            if actual is not None and (actual > maximum or usage['input_tokens'] > input_bound or
                                        usage['output_tokens'] > self.model.max_output_tokens):
                self.budget.external_only('OPENAI_USAGE_EXCEEDED_BOUND')
                value.update(status='ERROR', output=None, error='OPENAI_USAGE_EXCEEDED_BOUND')
                return Document.from_dict(value)
            if value.get('error') == 'OPENAI_CREDIT_EXHAUSTED':
                self.budget.external_only('OPENAI_CREDIT_EXHAUSTED')
        except IntelligenceError:
            # The provider already replied: retain its exact artifacts, usage and reasoning even
            # when accounting fails. Block further dispatch locally without relying on a DB write.
            self.budget_unavailable = True
            value['provider_outcome'] = dict(status=value['status'], error=value.get('error'))
            value.update(status='ERROR', output=None, error='MODEL_BUDGET_UNAVAILABLE')
            return Document.from_dict(value)
        return reply


class TrialGuardedExternal:
    """No new paid AIand POST outside a trial or after its durable accounting stop."""
    def __init__(self, model, budget, *, accounting_guard=None):
        self.model, self.budget = model, budget
        self.accounting_guard = accounting_guard

    def __getattr__(self, name):
        return getattr(self.model, name)

    def _before_dispatch(self):
        if self.accounting_guard is not None:
            self.accounting_guard()
        self.budget.guard_trial()

    def step(self, request, remaining_ms):
        try:
            return self.model.step(request, remaining_ms, before_dispatch=self._before_dispatch)
        except IntelligenceError as error:
            reason = error.reason if isinstance(error, AdmissionDeferred) else 'MODEL_BUDGET_UNAVAILABLE'
            return response(request.read(), status='ERROR', output=None, latency_ms=0, error=reason)


def _review_reasons(result, request, sample_bps, seed):
    if result['status'] == 'REJECTED_REQUEST':
        return []
    reasons = []
    if result['status'] != 'ASSESSED':
        reasons.append('ROUTINE_NOT_ASSESSED')
    if result.get('red_flag_checks'):
        reasons.append('INDEPENDENT_ITEM_CANDIDATE')
    if result.get('event_findings') or result.get('event_statements'):
        reasons.append('EVENT_INTERPRETATION')
    if result.get('conflicts') or result.get('missingness') or not result.get('coverage', {}).get('complete'):
        reasons.append('INCOMPLETE_OR_CONFLICTING_EVIDENCE')
    sample = int(digest('larp.routing.audit.v1', dict(seed=seed, issuer=request.get('issuer_id'),
                                                   evidence=request.get('evidence_refs'),
                                                   cutoff=request.get('cutoff_ms'))), 16) % 10000
    if sample < sample_bps:
        reasons.append('SEEDED_CLEAN_CASE_AUDIT')
    return reasons


def _signature(result):
    # Compare the actual verified consequences and evidence, not just finding labels: two
    # guidance cuts with different amounts/severity or event assertions can share a label.
    return (sorted(Document.from_dict(f).payload for f in result.get('findings', [])),
            sorted(Document.from_dict(f).payload for f in result.get('event_findings', [])),
            sorted(Document.from_dict(f).payload for f in result.get('falsifiers', [])))


def review_decision(primary, reviewers):
    """B11: stable precedence, evidence dissent, and no replacement of assessed primary."""
    assessed = primary is not None and primary['status'] == 'ASSESSED'
    verdicts = []
    for value in reviewers:
        verdicts.append('no result' if value is None or value['status'] not in ('ASSESSED', 'ABSTAIN')
                        else 'dissent' if value['status'] == 'ABSTAIN' or
                        (assessed and _signature(value) != _signature(primary)) else 'confirm')
    if assessed:
        if 'dissent' in verdicts:
            reason = 'ROUTING_FINDING_DISAGREEMENT' if any(
                v and v['status'] == 'ASSESSED' and _signature(v) != _signature(primary)
                for v in reviewers) else 'ROUTING_REVIEW_DISSENT'
            return dict(primary, status='ABSTAIN', reasons=[reason]), 'DISSENT', verdicts
        return primary, 'CONFIRMED' if 'confirm' in verdicts else 'INCOMPLETE', verdicts
    available = [v for v in reviewers if v is not None and v['status'] == 'ASSESSED']
    if available:
        if any(_signature(v) != _signature(available[0]) for v in available[1:]):
            return dict(available[0], status='ABSTAIN', reasons=['ROUTING_FINDING_DISAGREEMENT']), 'DISSENT', verdicts
        return available[0], 'FALLBACK', verdicts
    return None, 'NONE_AVAILABLE', verdicts


class AuditedModel:
    """Record a call before dispatch and its reply before verification, without headers/keys."""
    def __init__(self, model, hook, stage):
        self.model, self.hook, self.stage = model, hook, stage

    def __getattr__(self, name):
        return getattr(self.model, name)

    def step(self, request, remaining_ms):
        self.hook(dict(kind='MODEL_REQUEST', stage=self.stage, model=self.identity.record(), request=request.read()))
        reply = self.model.step(request, remaining_ms)
        self.hook(dict(kind='MODEL_RESPONSE', stage=self.stage, model=self.identity.record(), response=reply.read()))
        return reply


class RoutedAssessor:
    def __init__(self, *, routine, external_reviewers, openai, budget, make_assessor, clock_ms,
                 policy, artifacts, monotonic=time.monotonic):
        if not 1 <= len(external_reviewers) <= 2:
            raise IntelligenceError('One or two external difficult-case reviewers are required')
        if type(policy.get('audit_sample_bps')) is not int or not 0 <= policy['audit_sample_bps'] <= 10000 or \
                type(policy.get('audit_seed')) is not str or not policy['audit_seed']:
            raise IntelligenceError('Routing needs a frozen audit fraction/seed')
        self.routine, self.external, self.openai, self.budget = routine, tuple(external_reviewers), openai, budget
        self.make_assessor, self.clock, self.policy, self.monotonic = make_assessor, clock_ms, deepcopy(policy), monotonic
        self.artifacts = artifacts
        self._lane_lock = threading.Lock()
        self._workers = []
        binding = dict(algorithm='bounded-parallel-b11.v1', policy=policy, routine=routine.identity.record(),
                       external=[m.identity.record() for m in self.external],
                       openai_declared=policy['spec_hash'],
                       account=budget.account, total=budget.total, reserve=budget.reserve)
        name = 'openai-preferred-paced' if policy.get('openai_preferred') else 'aiand-external-first'
        identity = ModelIdentity('larp-router', name, 'v1:' + digest('larp.routing.v1', binding),
                                 digest('larp.routing.models.v1', binding), 'HOSTED')
        self.model = SimpleNamespace(identity=identity)

    def _budget_state(self):
        # Legacy routing may fall back externally; trial routing separately guards every paid POST.
        try:
            if self.openai is not None and self.openai.budget_unavailable:
                raise IntelligenceError('Model budget reconciliation required')
            return self.budget.snapshot()
        except IntelligenceError:
            return dict(account=self.budget.account, external_only=True, reason='MODEL_BUDGET_UNAVAILABLE')

    def assess_deferred(self, request, *, audit_hook):
        """Keep timed-out stage workers owned until their actual calls and audit writes end."""
        return self._assess(request, audit_hook=audit_hook, wait_for_workers=True)

    def assess(self, request):
        return self._assess(request, audit_hook=getattr(self, 'audit_hook', None))

    def _assess(self, request, *, audit_hook=None, wait_for_workers=False):
        # Synchronous callers also retain ownership: another job cannot accumulate hung workers.
        start = self.clock()
        r = request.read()
        budget = r.get('budget')
        raw_limit = budget.get('deadline_ms', 0) if type(budget) is dict else 0
        bound = Deadline(raw_limit if type(raw_limit) is int else 0, self.clock, monotonic=self.monotonic)
        validator = self.make_assessor(self.routine)
        if not self._lane_lock.acquire(blocking=False):
            return validator._rejected(r, 'ASSESSMENT_GROUP_BUSY', self.clock())
        try:
            self._workers = [w for w in self._workers if w.is_alive()]
            if self._workers:
                return validator._rejected(r, 'ASSESSMENT_GROUP_BUSY', self.clock())
            return self._assess_group(request, audit_hook=audit_hook, start=start, bound=bound)
        finally:
            if wait_for_workers:
                # Deferred caller only. A frozen verdict never releases live provider/audit ownership.
                # Wrapper workers may register inner workers before exit, so drain in insertion order.
                for worker in self._workers:
                    worker.join()
            self._lane_lock.release()

    def _assess_group(self, request, *, audit_hook, start, bound):
        r = request.read()
        validator = self.make_assessor(self.routine)
        try:
            validated = validator._validate(r)
        except (IntelligenceError, KeyError, TypeError):
            return validator.assess(request)
        total = r['budget']['deadline_ms']
        if not 0 < total <= MAX_ASSESSMENT_MS:
            return validator._rejected(r, 'BUDGET_EXCEEDS_DECLARATION', start)
        original_tools = r['budget']['tool_calls']
        stages = []

        def run(model, label, allowance, tool_allowance, stage_bound):
            if stage_bound.remaining() <= 0:
                return None
            stage = deepcopy(r)
            stage['budget'] = dict(tool_calls=tool_allowance, deadline_ms=allowance)
            assessor = self.make_assessor(AuditedModel(model, audit_hook, label) if audit_hook else model)
            assessor.request_namespace = label + ':'
            result = assessor.assess(Document.from_dict(stage), worker_group=self._workers,
                                     deadline=stage_bound).read()
            payload = Document.from_dict(result).payload
            ref = self.artifacts.put(payload)
            if ref != sha256_hex(payload):
                raise IntelligenceError('Routing artifact content address mismatch')
            record = dict(stage=label, model=model.identity.record(), result=result, artifact=ref)
            if audit_hook is not None:
                audit_hook(dict(kind='STAGE', stage=label, result=result, artifact=ref))
            return record

        preferred = self.policy.get('openai_preferred')
        primary_model = self.openai if preferred else self.routine
        primary = None
        allocation = min(original_tools, 3)
        share = max(1, min(MAX_PRIMARY_MS, total//3))
        if primary_model is not None and (not preferred or not self._budget_state()['external_only']):
            record = run(primary_model, 'openai-primary' if preferred else 'routine', share,
                         allocation, Deadline(share, self.clock, parent=bound))
            if record is not None:
                stages.append(record)
                primary = record['result']
        else:
            allocation = 0
        reasons = _review_reasons(primary, r, self.policy['audit_sample_bps'], self.policy['audit_seed']) \
            if primary is not None else ['OPENAI_NOT_AVAILABLE']
        if preferred:
            reasons = ['PRIMARY_NOT_ASSESSED' if x == 'ROUTINE_NOT_ASSESSED' else x for x in reasons]
        selected, outcome, verdicts, reviews = primary, 'NOT_TRIGGERED', [], []
        models = []
        if reasons:
            # Legacy v1/v2 retain their OpenAI-review stage; the external pair then uses B11 too.
            # Fixed partitions reserve capacity even for workers that outlive their cutoff.
            remainder = max(0, original_tools-allocation)
            if not preferred and self.openai is not None and not self._budget_state()['external_only']:
                allowance = min(MAX_REVIEW_MS, bound.remaining())
                if allowance > 0:
                    tools = remainder//2
                    record = run(self.openai, 'openai-review', allowance, tools,
                                 Deadline(allowance, self.clock, parent=bound))
                    remainder -= tools
                    if record:
                        stages.append(record)
                        reviews.append(record['result'])
                        models.append((self.openai, 'openai-review'))
            if preferred or not reviews or reviews[-1]['status'] != 'ASSESSED':
                pair = list(self.external)
                allowance = min(MAX_REVIEW_MS, bound.remaining())
                boxes = [{} for _ in pair]
                workers = []
                # Allocate the odd token by declared reviewer precedence, never arrival order.
                for i, model in enumerate(pair):
                    tools = remainder//len(pair) + (i < remainder % len(pair))
                    stage_bound = Deadline(allowance, self.clock, parent=bound)
                    def work(i=i, model=model, tools=tools, stage_bound=stage_bound):
                        try:
                            boxes[i]['record'] = run(model, 'external-review-'+str(i), allowance, tools, stage_bound)
                        except BaseException as error:
                            boxes[i]['error'] = error
                    worker = threading.Thread(target=work, name='larp-review-'+str(i), daemon=True)
                    self._workers.append(worker)
                    workers.append(worker)
                    worker.start()
                for worker in workers:
                    worker.join(bound.remaining()/1000)
                for i, box in enumerate(boxes):
                    if 'error' in box:
                        raise box['error']
                    record = box.get('record')
                    if record:
                        stages.append(record)
                    reviews.append(record['result'] if record else None)
                    models.append((pair[i], 'external-review-'+str(i)))
            selected, outcome, verdicts = review_decision(primary, reviews)
        if selected is None:
            selected = validator._abandoned(r, validated, start, dict(steps=[], tool_calls=[], started=0)).read()
            selected.update(status='UNAVAILABLE', reasons=['ROUTING_DEADLINE_EXHAUSTED'])
        metadata = dict(review_outcome=outcome, primary_result_id=primary['result_id'] if primary else None,
                        reviewers=[dict(stage=label, model=model.identity.record(), verdict=verdict,
                                        status=value['status'] if value else 'NOT_FINISHED',
                                        reasons=value.get('reasons', []) if value else [])
                                   for (model, label), value, verdict in zip(models, reviews, verdicts)])
        return self._combine(r, selected, stages, reasons, start, metadata=metadata)

    def _combine(self, request, selected, stages, reasons, start, *, metadata=None):
        result = deepcopy(selected)
        result.pop('result_id', None)
        result['job_id'] = request.get('job_id')
        result['model'] = self.model.identity.record()
        result['model_hash'] = self.model.identity.model_hash
        result['assessment_key'] = digest('larp.routing.assessment.v1', dict(
            models=result['model_hash'], request=request, stages=[s['result']['result_id'] for s in stages]))
        if result['status'] in ('ABSTAIN', 'UNAVAILABLE'):
            # Failed required review cannot inherit clean/adverse authority from a different stage.
            result.update(claims=[], findings=[], event_findings=[], proposed_thesis=None,
                          impact='UNKNOWN', severity=None,
                          confidence=dict(level='UNKNOWN', calibrated=False, basis='Required routing review unavailable'))
            result['falsifiers'] = [dict(f, state='UNKNOWN') for f in result.get('falsifiers', [])]
            result['rationale'] = 'Required routing review did not establish an accepted assessment: ' + ','.join(result['reasons'])
        steps, calls, in_flight, summaries = [], [], [], []
        for s in stages:
            io = s['result']['model_io']
            steps.extend(dict(x, routing_stage=s['stage'], model=s['model']) for x in io.get('steps', []))
            for t in io.get('tool_calls', []):
                calls.append(dict(t, index=len(calls), routing_stage=s['stage']))
            if io.get('in_flight'):
                in_flight.append(dict(io['in_flight'], routing_stage=s['stage'], model=s['model']))
            summaries.extend(io.get('cot', []))
        result['model_io'] = dict(steps=steps, tool_calls=calls, cot=summaries,
                                 model_called=any(s['result']['model_io']['model_called'] for s in stages),
                                 requests_started=sum(s['result']['model_io'].get('requests_started', 0) for s in stages),
                                 no_model_call_reason=None, in_flight=in_flight[0] if in_flight else None,
                                 in_flight_calls=in_flight)
        if not result['model_io']['model_called']:
            result['model_io']['no_model_call_reason'] = selected['model_io'].get('no_model_call_reason')
        result['started_ms'], result['completed_ms'] = start, self.clock()
        result['budget_used'] = dict(tool_calls=len(calls), model_steps=len(steps), elapsed_ms=self.clock()-start)
        result['routing'] = dict(reasons=reasons, budget=self._budget_state(),
                                 stages=[dict(stage=s['stage'], model=s['model'], result_id=s['result']['result_id'],
                                              status=s['result']['status'], result_artifact=s['artifact']) for s in stages])
        result['routing'].update(metadata or {})
        costs = [s['result']['cost'] for s in stages]
        result['cost'] = dict(amount_micro_usd=None if any(c['amount_micro_usd'] is None for c in costs)
                             else sum(c['amount_micro_usd'] for c in costs),
                             basis=sorted({b for c in costs for b in c['basis']}))
        if set(result.get('reasons', [])) & {'ROUTING_FINDING_DISAGREEMENT', 'ROUTING_REVIEW_DISSENT'}:
            assessor = self.make_assessor(self.routine)
            entry = next(e for e in assessor.registry.entries if e.issuer_id == request['issuer_id'])
            result['review_requests'] = assessor._reviews(request, entry, 'ABSTAIN',
                ['MODEL_OUTPUT_ROUTING_DISAGREEMENT'], result.get('missingness', []),
                result['assessment_key'], self.clock())
        for review in result.get('review_requests', []):
            payload = review['job']['payload']
            payload['after_assessment_key'] = result['assessment_key']
            job_id = 'evidence:' + digest('larp.intel.review.v1', payload)
            review['request_id'] = review['job']['job_id'] = job_id
        result['completed_ms'] = self.clock()
        result['budget_used']['elapsed_ms'] = result['completed_ms'] - start
        result['structured_assessment'] = _structured_assessment(result)
        result['result_id'] = 'res:' + digest('larp.intel.result.v1', result)
        return Document.from_dict(result)


def stage_prompt_bytes(prompt, prompt_dir=STAGE_PROMPT_DIR):
    """The exact bytes of a pinned stage prompt (IDEA-081), refused unless name and hash match."""
    if type(prompt) is not dict or set(prompt) != {'name', 'sha256'} or type(prompt['name']) is not str:
        raise IntelligenceError('Stage prompt needs exactly a name and a sha256')
    name = prompt['name']
    if (not name.endswith('.md') or name != Path(name).name or name.startswith('.')
            or any(part in name for part in ('\\', '..', '\x00'))):
        raise IntelligenceError('Stage prompt must be a Markdown file name in the routing prompt directory')
    pinned = require_hash(prompt['sha256'], 'stage prompt sha256')
    try:
        path = Path(prompt_dir) / name
        if path.is_symlink() or not path.is_file():
            raise ValueError
        with path.open('rb') as stream:
            raw = stream.read(MAX_STAGE_PROMPT_BYTES + 1)
        if len(raw) > MAX_STAGE_PROMPT_BYTES or not raw.decode('utf-8').strip():
            raise ValueError
    except (OSError, ValueError):
        raise IntelligenceError('Stage prompt must be bounded UTF-8 text in the release directory') from None
    if sha256_hex(raw) != pinned:
        raise IntelligenceError('Stage prompt does not match its pinned hash')
    return raw


def stage_config(config, prompt, prompt_dir=STAGE_PROMPT_DIR):
    """The core config with the stage's pinned addendum appended to its prompt (IDEA-081).

    The composed text and its hash replace the core prompt for that stage only, so the adapter's
    hash check, the recorded prompt hash and the assessment key all name what the model was sent."""
    raw = stage_prompt_bytes(prompt, prompt_dir)
    text = config.prompt_text.rstrip('\n') + '\n\n' + raw.decode('utf-8')
    return replace(config, prompt_text=text, prompt_sha256=sha256_hex(text.encode('utf-8')))


def build_routed_assessor(spec, *, registry, reader, config, clock_ms, artifacts, secrets, budget_root,
                          transports=None, prompt_dir=STAGE_PROMPT_DIR):
    """Construct without network I/O. Spec bytes are pinned by the runtime config before this call.

    AIandRouting.v2 pins one stage prompt per model (`prompt` on each entry, `openai_prompt`);
    v1 sends every stage the core prompt, as before. V3 prefers OpenAI under frozen pacing."""
    validate_routing_spec(spec, prompt_dir=prompt_dir)
    preferred = spec['schema'] == 'AIandRouting.v3'
    staged = spec['schema'] in ('AIandRouting.v2', 'AIandRouting.v3')
    configs = {}

    def config_for(prompt):
        return stage_config(config, prompt, prompt_dir) if staged else config
    if not secrets.get('LARP_AIAND_API_KEY'):
        raise IntelligenceError('AIand routing requires LARP_AIAND_API_KEY in the runtime secret')
    transports = transports or {}
    common = dict(clock_ms=clock_ms, artifacts=artifacts, max_output_tokens=spec['max_output_tokens'])
    openai = None

    def primary_accounting_guard():
        # A transient storage recovery cannot lift a quarantine caused by an uncertain settlement.
        # Keep the same stop across all subsequent trial stages/jobs until owner reconciliation.
        if openai is not None and openai.budget_unavailable:
            raise IntelligenceError('Model budget reconciliation required')

    def external(entry):
        c = config_for(entry.get('prompt'))
        model = AIandChatModel(model_id=entry['model_id'], effort=entry['effort'],
                               catalog=entry['catalog'], api_key=secrets['LARP_AIAND_API_KEY'],
                               transport=transports.get('aiand'), prompt_text=c.prompt_text,
                               prompt_sha256=c.prompt_sha256, **common)
        if spec.get('openai_trial') is not None:
            model = TrialGuardedExternal(model, budget, accounting_guard=primary_accounting_guard)
        configs[model] = c
        return model

    budget_options = dict(pacing=spec['openai_pacing'], total=spec['openai_pacing']['total_micro_usd'],
                          reserve=0, clock_ms=clock_ms) if preferred else {}
    if spec.get('openai_trial') is not None:
        budget_options['trial'] = spec['openai_trial']
    budget = ModelBudget(Path(budget_root) / 'openai-budget.sqlite', spec['budget_account'], **budget_options)
    routine = external(spec['routine'])
    reviewers = [external(e) for e in spec['external_reviewers']]
    openai_config = config_for(spec.get('openai_prompt'))  # checked even without a key: the spec is all-or-nothing
    if secrets.get('LARP_MODEL_API_KEY'):
        openai = BudgetedOpenAI(OpenAIResponsesModel(model_id=spec['openai_model'],
            effort=spec['openai_effort'], api_key=secrets['LARP_MODEL_API_KEY'], price=OPENAI_PRICE,
            transport=transports.get('openai'), prompt_text=openai_config.prompt_text,
            prompt_sha256=openai_config.prompt_sha256, **common), budget)
        configs[openai] = openai_config
    def make(model):
        # Audit wrappers retain the exact stage prompt/config, including on the deferred lane.
        stage_model = model.model if isinstance(model, AuditedModel) else model
        return EvidenceAssessor(registry=registry, reader=reader, model=model,
                                config=configs.get(stage_model, config), clock_ms=clock_ms)
    return RoutedAssessor(routine=routine, external_reviewers=reviewers, openai=openai, budget=budget,
                          make_assessor=make, clock_ms=clock_ms, artifacts=artifacts,
                          policy=dict(audit_sample_bps=spec['audit_sample_bps'], audit_seed=spec['audit_seed'],
                                      **(dict(openai_preferred=True) if preferred else {}),
                                      spec_hash=sha256_hex(Document.from_dict(spec).payload)))

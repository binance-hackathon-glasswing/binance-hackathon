"""Opt-in IDEA-057 external-first assessor, sharing one deadline/tool budget.

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
from types import SimpleNamespace

from larp.contracts import Document
from larp.intelligence.agent import EvidenceAssessor, _structured_assessment
from larp.intelligence.aiand import AIandChatModel
from larp.intelligence.common import IntelligenceError, digest, require_hash, sha256_hex
from larp.intelligence.config import CONFIG_DIR
from larp.intelligence.model_budget import ModelBudget
from larp.intelligence.models import ModelIdentity, response
from larp.intelligence.providers import OpenAIResponsesModel

# Stage prompts (IDEA-081): Markdown addenda appended to the core assessor prompt, read only from the release.
STAGE_PROMPT_DIR = CONFIG_DIR / 'prompts' / 'routing'
OPENAI_PRICE = dict(input_micro_usd_per_mtok=2_000_000, output_micro_usd_per_mtok=10_000_000,
                    source='https://developers.openai.com/api/docs/models/gpt-6.1-sol;2026-10-15;standard')


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
        token = self.budget.admit(maximum, request.read()['request_id'])
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
        binding = dict(policy=policy, routine=routine.identity.record(),
                       external=[m.identity.record() for m in self.external],
                       openai_declared=policy['spec_hash'],
                       account=budget.account, total=budget.total, reserve=budget.reserve)
        identity = ModelIdentity('larp-router', 'aiand-external-first', 'v1:' + digest('larp.routing.v1', binding),
                                 digest('larp.routing.models.v1', binding), 'HOSTED')
        self.model = SimpleNamespace(identity=identity)

    def _budget_state(self):
        # Missing/locked/corrupt storage blocks OpenAI (admission raises too), never the external path.
        try:
            if self.openai is not None and self.openai.budget_unavailable:
                raise IntelligenceError('Model budget reconciliation required')
            return self.budget.snapshot()
        except IntelligenceError:
            return dict(account=self.budget.account, external_only=True, reason='MODEL_BUDGET_UNAVAILABLE')

    def assess(self, request):
        r = request.read()
        # Let the normal validator reject malformed requests without any inference or billing.
        validator = self.make_assessor(self.routine)
        try:
            validated = validator._validate(r)
        except (IntelligenceError, KeyError, TypeError):
            return validator.assess(request)
        total = r.get('budget', {}).get('deadline_ms')
        if type(total) is not int or not 0 < total <= 60000:
            return self.make_assessor(self.routine).assess(request)
        start, wall = self.clock(), self.monotonic()
        stages, tools = [], 0
        original_tools = r.get('budget', {}).get('tool_calls', 0)

        def left():
            return max(0, total - max(self.clock() - start, int((self.monotonic() - wall) * 1000)))

        def run(model, label, allowance=None):
            nonlocal tools
            remaining = left()
            if remaining <= 0:
                return None
            stage = deepcopy(r)
            tool_allowance = max(0, original_tools-tools)
            if label == 'routine':
                tool_allowance = min(tool_allowance, 3)  # leave independent review a retrieval budget
            stage['budget'] = dict(tool_calls=tool_allowance,
                                   deadline_ms=min(remaining, allowance or remaining))
            assessor = self.make_assessor(model)
            assessor.request_namespace = label + ':'
            result = assessor.assess(Document.from_dict(stage)).read()
            tools += result.get('budget_used', {}).get('tool_calls') or 0
            payload = Document.from_dict(result).payload
            ref = self.artifacts.put(payload)
            if ref != sha256_hex(payload):
                raise IntelligenceError('Routing artifact content address mismatch')
            stages.append(dict(stage=label, model=model.identity.record(), result=result, artifact=ref))
            return result

        chosen = run(self.routine, 'routine', max(1, total//2))
        if chosen is None:
            return validator._abandoned(r, validated, start, dict(steps=[], tool_calls=[], started=0))
        reasons = _review_reasons(chosen, r, self.policy['audit_sample_bps'], self.policy['audit_seed'])
        if reasons:
            reviewed = None
            if self.openai is not None and not self._budget_state()['external_only']:
                reviewed = run(self.openai, 'openai-review')
            # Missing key, exhausted/limited credits, error, invalid claims or a timeout all have
            # a bounded external review path. Generic rate limits do not latch credit exhaustion.
            if reviewed is None or reviewed['status'] != 'ASSESSED':
                for index, model in enumerate(self.external):
                    candidate = run(model, 'external-review-' + str(index))
                    if candidate is not None:
                        reviewed = candidate
                    if reviewed is not None and reviewed['status'] == 'ASSESSED':
                        break
            if reviewed is None:
                chosen = dict(chosen, status='UNAVAILABLE', reasons=['ROUTING_DEADLINE_EXHAUSTED'])
            else:
                if chosen['status'] == reviewed['status'] == 'ASSESSED' and _signature(chosen) != _signature(reviewed):
                    reviewed = dict(reviewed, status='ABSTAIN', reasons=['ROUTING_FINDING_DISAGREEMENT'])
                chosen = reviewed
        return self._combine(r, chosen, stages, reasons, start)

    def _combine(self, request, selected, stages, reasons, start):
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
        costs = [s['result']['cost'] for s in stages]
        result['cost'] = dict(amount_micro_usd=None if any(c['amount_micro_usd'] is None for c in costs)
                             else sum(c['amount_micro_usd'] for c in costs),
                             basis=sorted({b for c in costs for b in c['basis']}))
        if 'ROUTING_FINDING_DISAGREEMENT' in result.get('reasons', []):
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


def stage_config(config, prompt, prompt_dir=STAGE_PROMPT_DIR):
    """The core config with the stage's pinned addendum appended to its prompt (IDEA-081).

    The composed text and its hash replace the core prompt for that stage only, so the adapter's
    hash check, the recorded prompt hash and the assessment key all name what the model was sent."""
    if type(prompt) is not dict or set(prompt) != {'name', 'sha256'} or type(prompt['name']) is not str:
        raise IntelligenceError('Stage prompt needs exactly a name and a sha256')
    name = prompt['name']
    if not name.endswith('.md') or name != Path(name).name or name.startswith('.'):
        raise IntelligenceError('Stage prompt must be a Markdown file name in the routing prompt directory')
    pinned = require_hash(prompt['sha256'], 'stage prompt sha256')
    try:
        raw = (prompt_dir / name).read_bytes()
    except OSError:
        raise IntelligenceError('Stage prompt file is missing: ' + name) from None
    if sha256_hex(raw) != pinned:
        raise IntelligenceError('Stage prompt does not match its pinned hash: ' + name)
    text = config.prompt_text.rstrip('\n') + '\n\n' + raw.decode('utf-8')
    return replace(config, prompt_text=text, prompt_sha256=sha256_hex(text.encode('utf-8')))


def build_routed_assessor(spec, *, registry, reader, config, clock_ms, artifacts, secrets, budget_root,
                          transports=None, prompt_dir=STAGE_PROMPT_DIR):
    """Construct without network I/O. Spec bytes are pinned by the runtime config before this call.

    AIandRouting.v2 pins one stage prompt per model (`prompt` on each entry, `openai_prompt`);
    v1 sends every stage the core prompt, as before."""
    if spec.get('schema') not in ('AIandRouting.v1', 'AIandRouting.v2') or spec.get('openai_model') != 'gpt-6.1-sol':
        raise IntelligenceError('Unsupported routing schema or OpenAI model')
    staged = spec['schema'] == 'AIandRouting.v2'
    entries = [spec.get('routine'), *(spec.get('external_reviewers') or [])]
    if any(type(e) is not dict for e in entries):
        raise IntelligenceError('Routing model entries must be objects')
    if not staged and ('openai_prompt' in spec or any('prompt' in e for e in entries)):
        raise IntelligenceError('Stage prompts need schema AIandRouting.v2')
    if staged and ('openai_prompt' not in spec or any('prompt' not in e for e in entries)):
        raise IntelligenceError('AIandRouting.v2 needs a stage prompt for every model')
    configs = {}

    def config_for(prompt):
        return stage_config(config, prompt, prompt_dir) if staged else config
    if type(spec.get('max_output_tokens')) is not int or not 0 < spec['max_output_tokens'] <= 16000:
        raise IntelligenceError('Routing output limit must be 1..16000')
    if not secrets.get('LARP_AIAND_API_KEY'):
        raise IntelligenceError('AIand routing requires LARP_AIAND_API_KEY in the runtime secret')
    transports = transports or {}
    common = dict(clock_ms=clock_ms, artifacts=artifacts, max_output_tokens=spec['max_output_tokens'])

    def external(entry):
        c = config_for(entry.get('prompt'))
        model = AIandChatModel(model_id=entry['model_id'], effort=entry['effort'],
                               catalog=entry['catalog'], api_key=secrets['LARP_AIAND_API_KEY'],
                               transport=transports.get('aiand'), prompt_text=c.prompt_text,
                               prompt_sha256=c.prompt_sha256, **common)
        configs[model] = c
        return model

    budget = ModelBudget(Path(budget_root) / 'openai-budget.sqlite', spec['budget_account'])
    routine = external(spec['routine'])
    reviewers = [external(e) for e in spec['external_reviewers']]
    openai = None
    openai_config = config_for(spec.get('openai_prompt'))  # checked even without a key: the spec is all-or-nothing
    if secrets.get('LARP_MODEL_API_KEY'):
        openai = BudgetedOpenAI(OpenAIResponsesModel(model_id=spec['openai_model'],
            effort=spec['openai_effort'], api_key=secrets['LARP_MODEL_API_KEY'], price=OPENAI_PRICE,
            transport=transports.get('openai'), prompt_text=openai_config.prompt_text,
            prompt_sha256=openai_config.prompt_sha256, **common), budget)
        configs[openai] = openai_config
    make = lambda model: EvidenceAssessor(registry=registry, reader=reader, model=model,
                                          config=configs.get(model, config), clock_ms=clock_ms)
    return RoutedAssessor(routine=routine, external_reviewers=reviewers, openai=openai, budget=budget,
                          make_assessor=make, clock_ms=clock_ms, artifacts=artifacts,
                          policy=dict(audit_sample_bps=spec['audit_sample_bps'], audit_seed=spec['audit_seed'],
                                      spec_hash=sha256_hex(Document.from_dict(spec).payload)))

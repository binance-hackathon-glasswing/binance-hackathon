"""Versioned observation and assessment boundary validation."""

import hashlib

from larp.contracts import ContractError,Document


def require_hash(value):
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ContractError('Expected SHA-256 identity')


def fact(document,cutoff_ms):
    d=document.read()
    for field in ('source','quality'):
        if not isinstance(d.get(field),str) or not d[field]:
            raise ContractError('Observation provenance missing')
    for field in ('observed_ms','available_ms'):
        if type(d.get(field)) is not int or d[field]>cutoff_ms or d[field]<0:
            raise ContractError('Future or malformed observation timestamp')
    require_hash(d['content_hash'])
    if d['quality'] not in ('VALID','MISSING','STALE','UNKNOWN','SYNTHETIC'):
        raise ContractError('Unknown quality state')
    return document


def assessment_request(document,run_id,profile_hash,now_ms):
    r=document.read()
    if (r.get('schema'),r.get('run_id'),r.get('policy_profile_hash')) != (
            'AssessmentRequest.v1',run_id,profile_hash):
        raise ContractError('Request identity/profile mismatch')
    if type(r['cutoff_ms']) is not int or r['cutoff_ms']>now_ms:
        raise ContractError('Invalid assessment cutoff')
    require_hash(r['context_hash']); require_hash(r['policy_profile_hash'])
    budget=r['budget']
    if (type(budget['tool_calls']) is not int or not 0<=budget['tool_calls']<=6 or
        type(budget['deadline_ms']) is not int or not 0<budget['deadline_ms']<=60000):
        raise ContractError('Assessment budget exceeds declaration')
    for reference in r['evidence_refs']:
        fact(Document.from_dict(reference),r['cutoff_ms'])
    return document


def assessment_result(document,request,now_ms):
    a=document.read(); r=request.read()
    for key in ('job_id','run_id','issuer_id','context_hash','policy_profile_hash'):
        if a.get(key)!=r.get(key):
            raise ContractError('Assessment context mismatch')
    # v2 is the evidence producer (IDEA-031); v1 remains for the synthetic runtime fixtures.
    if a.get('schema') not in ('AssessmentResult.v1','AssessmentResult.v2') or type(a['expiry_ms']) is not int or a['expiry_ms']<=now_ms:
        raise ContractError('Expired or malformed assessment')
    if a.get('schema') == 'AssessmentResult.v2':
        if (any(type(a.get(k)) is not int or a[k]<0 for k in ('cutoff_ms','started_ms','completed_ms'))
            or a['cutoff_ms']!=r['cutoff_ms']
            or not a['cutoff_ms']<=a['started_ms']<=a['completed_ms']<=now_ms):
            raise ContractError('Future or mismatched assessment timestamps')
    if {'orders','side','targets','buy','sell'} & {key.lower() for key in a}:
        raise ContractError('Assessment cannot grant trade authority')
    for key in ('model_hash','prompt_hash','rationale','model_io'):
        if not a.get(key):
            raise ContractError('Missing assessment provenance or I/O')
    return document

"""AIand's fixed Chat Completions surface (IDEA-057); no automatic model selection.

Catalog capabilities are pinned public metadata, not proof of account entitlement or real accuracy.
The API key is carried only in Authorization. Exact request/reply bytes and selected response
headers are recorded by HostedModel; no provider SDK or inference is used during construction.
"""
import json

from larp.intelligence.common import IntelligenceError, digest
from larp.intelligence.providers import (HostedModel, _ProviderReply, _json_object,
                                         https_post_metadata)

ENDPOINT = 'https://api.aiand.com/v1/chat/completions'
MODELS = frozenset(('moonshotai/kimi-k3', 'zai-org/glm-5.3'))


def validate_settings(model_id, effort, catalog, maximum):
    """Pure validation shared by preparation and the provider constructor."""
    if type(model_id) is not str or model_id not in MODELS:
        raise IntelligenceError('AIand model must be an explicitly supported catalog ID')
    if (type(catalog) is not dict or catalog.get('id') != model_id
            or type(catalog.get('capabilities')) is not list
            or 'reasoning' not in catalog['capabilities']
            or type(catalog.get('reasoning_efforts')) is not list
            or type(effort) is not str or effort not in ('low', 'high', 'max')
            or effort not in catalog['reasoning_efforts']):
        raise IntelligenceError('AIand catalog identity/effort mismatch')
    if (type(maximum) is not int or any(type(catalog.get(k)) is not int
                                      for k in ('max_output_tokens', 'context_window'))
            or not 0 < maximum <= catalog['max_output_tokens'] < catalog['context_window']):
        raise IntelligenceError('AIand catalog output/context bound invalid')


class AIandChatModel(HostedModel):
    provider = 'aiand'

    def __init__(self, *, model_id, effort, catalog, transport=None, **kwargs):
        validate_settings(model_id, effort, catalog, kwargs.get('max_output_tokens', 16000))
        self.effort = effort
        self.catalog_hash = digest('larp.aiand.catalog-model.v1', catalog)
        endpoint = kwargs.pop('endpoint', ENDPOINT)
        if endpoint != ENDPOINT:
            raise IntelligenceError('AIand endpoint is fixed')
        super().__init__(model_id=model_id, endpoint=endpoint, allowed_hosts=frozenset(('api.aiand.com',)),
                         transport=transport or https_post_metadata, **kwargs)

    def _revision(self):
        return (f'chat-completions;endpoint={ENDPOINT};effort={self.effort};'
                f'json-object;max_output_tokens={self.max_output_tokens};catalog={self.catalog_hash}')

    def _headers(self):
        return {'Authorization': f'Bearer {self._key}', 'Content-Type': 'application/json'}

    def _body(self, model_input):
        return dict(model=self.identity.model_id, stream=False, reasoning_effort=self.effort,
                    max_completion_tokens=self.max_output_tokens,
                    response_format={'type': 'json_object'},
                    messages=[{'role': 'system', 'content': self._prompt},
                              {'role': 'user', 'content': json.dumps(model_input, sort_keys=True)}])

    def _served_matches(self, served):
        return type(served) is str and served.casefold() == self.identity.model_id.casefold()

    def _parse_reply(self, payload, metadata):
        served = payload.get('model')
        if payload.get('error'):
            raise _ProviderReply('PROVIDER_ERROR', served)
        if not self._served_matches(metadata.get('x-model')):
            raise _ProviderReply('AIAND_HEADER_MODEL_MISMATCH', served)
        if metadata.get('x-reasoning-effort') != self.effort:
            raise _ProviderReply('AIAND_APPLIED_EFFORT_MISMATCH', served)
        choices = payload['choices']
        if type(choices) is not list or len(choices) != 1 or choices[0].get('finish_reason') != 'stop':
            raise _ProviderReply('AIAND_INCOMPLETE_OR_MULTIPLE_CHOICES', served)
        message = choices[0]['message']
        if message.get('refusal') or message.get('tool_calls'):
            raise _ProviderReply('AIAND_REFUSAL_OR_NATIVE_TOOL_CALL', served)
        reasoning = message.get('reasoning_content') or message.get('reasoning')
        if reasoning is not None and type(reasoning) is not str:
            raise _ProviderReply('AIAND_REASONING_MALFORMED', served)
        if message.get('reasoning_content') is not None and message.get('reasoning') is not None and \
                message['reasoning_content'] != message['reasoning']:
            raise _ProviderReply('AIAND_REASONING_CONFLICT', served)
        usage = payload['usage']
        return (served, _json_object(message['content']),
                dict(input_tokens=usage['prompt_tokens'], output_tokens=usage['completion_tokens']), reasoning)

"""Runtime secrets from AWS Secrets Manager (IDEA-042 S1-S3; review comment V4).

The coordinator host holds only what the coordinator uses: the public wallet address and the Web3 market-data key pair.
The audit secret belongs to the uploader host and the wallet key to the signer host (docs/build/runtime-infrastructure.md).
Secrets never come from the process environment, which child processes inherit. No value ever appears in an error,
a log line or a repr.
"""

import json

from larp.runtime.live import RUNTIME_SECRETS, LiveStartRefused, NOT_ON_RUNTIME

OPTIONAL_MODEL_SECRETS = ('LARP_AIAND_API_KEY', 'LARP_MODEL_API_KEY')


# Definite answers from Secrets Manager: restarting the same configuration cannot cure them, so the start is refused
# (exit 4). Every other failure (throttling, 5xx, timeouts, connection errors, credentials not yet available at boot)
# is retried by the supervisor (exit 1): a refusal there would leave the agent down until a person acts (F-114;
# IDEA-049 D-FND-003, #43).
DEFINITE_SECRET_ERRORS = frozenset(('ResourceNotFoundException', 'AccessDeniedException', 'AccessDenied',
                                    'InvalidParameterException', 'InvalidRequestException', 'DecryptionFailure'))


class SecretsUnavailable(RuntimeError):
    """A transient secret-store failure; carries the error type only, never provider text or a value."""


class Secrets(dict):
    """A name -> value mapping whose repr names the keys only."""

    def __repr__(self):
        return 'Secrets(' + ', '.join(sorted(self)) + ')'

    __str__ = __repr__


def load_runtime_secrets(client, secret_id):
    """One GetSecretValue for `secret_id`; returns the runtime's names only. Refuses any secret not meant for it."""
    if type(secret_id) is not str or not secret_id.strip():
        raise LiveStartRefused('No runtime secret source configured (runtime_secret_id)')
    try:
        raw = client.get_secret_value(SecretId=secret_id)['SecretString']
    except Exception as exc:  # the provider's message is not trusted to be value-free; only its type/code is kept
        code = getattr(exc, 'response', {}).get('Error', {}).get('Code') if isinstance(
            getattr(exc, 'response', None), dict) else None
        if code in DEFINITE_SECRET_ERRORS:
            raise LiveStartRefused('Runtime secret unavailable: ' + code) from None
        raise SecretsUnavailable('Runtime secret temporarily unavailable: ' + (
            code if type(code) is str and code.isalnum() else type(exc).__name__)) from None
    try:
        values = json.loads(raw)
    except (TypeError, ValueError):
        raise LiveStartRefused('Runtime secret is not a JSON object') from None
    if type(values) is not dict or not all(type(k) is str and type(v) is str and v.strip() for k, v in values.items()):
        raise LiveStartRefused('Runtime secret must map names to non-empty strings')
    foreign = sorted(set(values) & set(NOT_ON_RUNTIME))
    if foreign:
        raise LiveStartRefused('Secret for another host present in the runtime secret: ' + ', '.join(foreign))
    return Secrets({name: values[name] for name in RUNTIME_SECRETS + OPTIONAL_MODEL_SECRETS if name in values})


def runtime_secrets(config, client_factory=None):
    """The service's secrets: loaded only for `dev` and `live`, and only from the configured secret ID."""
    if config.get('mode', 'offline') not in ('dev', 'live'):
        return Secrets()
    secret_id = config.get('runtime_secret_id')
    if not secret_id:
        raise LiveStartRefused('No runtime secret source configured (runtime_secret_id)')
    if client_factory is None:
        if not config.get('region'):
            raise LiveStartRefused('No AWS region configured for the runtime secret')

        def client_factory():
            import boto3
            from botocore.config import Config
            return boto3.Session(region_name=config['region']).client('secretsmanager', config=Config(
                connect_timeout=5, read_timeout=15, retries={'total_max_attempts': 2, 'mode': 'standard'},
                ignore_configured_endpoint_urls=True))
    return load_runtime_secrets(client_factory(), secret_id)

"""Fixed-origin signed Binance Web3 transport and immutable public response evidence."""
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shlex
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from larp.contracts import reflects_secret

BASE = 'https://web3.binance.com/build/api/v1/dex/'
READS = frozenset({('GET', p) for p in (
    'aggregator/supported/chain', 'market/rwa/tokens', 'market/rwa/price',
    'market/rwa/underlying-market', 'market/candles', 'aggregator/quote-and-swap',
    'aggregator/approve-transaction', 'post-transaction/transaction-detail-by-txhash')}) | frozenset({
    ('POST', 'balance/token-balances-by-address'), ('POST', 'pre-transaction/gas-limit')})
ENV_NAMES = ('BINANCE_API_KEY', 'BINANCE_SECRET_KEY', 'BN_WEB3_API_KEY',
             'BN_WEB3_API_SECRET', 'BN_WEB3_SECRET_KEY', 'AI_SEEDS_ADDRESS')


def utc():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def encoded(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def redact(value, secrets, *, ignore_case=False):
    if isinstance(value, dict):
        return {redact(k, secrets, ignore_case=ignore_case): redact(v, secrets, ignore_case=ignore_case)
                for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secrets, ignore_case=ignore_case) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = (re.sub(re.escape(secret), '[REDACTED]', value, flags=re.IGNORECASE)
                         if ignore_case else value.replace(secret, '[REDACTED]'))
    return value


class Unavailable(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def credentials(env_file=None, environ=None):
    selected = {k: v for k, v in (os.environ if environ is None else environ).items() if k in ENV_NAMES and v}
    if env_file:
        for line in Path(env_file).read_text().splitlines():
            key, sep, val = line.removeprefix('export ').partition('=')
            key = key.strip()
            if sep and key in ENV_NAMES:
                parts = shlex.split(val, comments=True)
                if not parts or parts == ['']:
                    continue  # optional empty fields do not replace supplied credentials
                if len(parts) != 1 or '$' in parts[0] or '`' in parts[0]:
                    raise Unavailable('credentials must be literal values')
                if key in selected and selected[key] != parts[0]:
                    raise Unavailable('conflicting process/file credentials')
                selected[key] = parts[0]
    for primary, aliases in (('BINANCE_API_KEY', ('BN_WEB3_API_KEY',)),
                             ('BINANCE_SECRET_KEY', ('BN_WEB3_API_SECRET', 'BN_WEB3_SECRET_KEY'))):
        values = [selected[k] for k in (primary, *aliases) if selected.get(k)]
        if len(set(values)) > 1:
            raise Unavailable('conflicting credential aliases')
        if not values:
            raise Unavailable('missing Web3 credentials')
        selected[primary] = values[0]
    return selected


class Artifacts:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def put(self, observation):
        raw = encoded(observation)
        sha = hashlib.sha256(raw).hexdigest()
        path = self.root / (sha + '.json')
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            if path.read_bytes() != raw:
                raise Unavailable('artifact integrity failure')
        else:
            with os.fdopen(fd, 'wb') as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
            fd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        return sha


class Web3Client:
    # The read/build client can never submit a transaction; a submit-only subclass replaces this set
    # (larp/execution_live/loop.py Web3Broadcaster). Values of `private_params` are stored only as hashes.
    endpoints = READS
    private_params = ()

    mode = 'live'

    def __init__(self, key, secret, *, artifacts, opener=None, min_interval=0.35, timeout=20):
        if not key or not secret or min_interval < 0.3 or not 0 < timeout <= 30:
            raise Unavailable('invalid transport configuration')
        self.key, self.secret, self.artifacts = key, secret, artifacts
        self.opener = opener or build_opener(NoRedirect())
        self.min_interval, self.timeout, self.last = min_interval, timeout, 0

    def request(self, method, endpoint, params):
        if (method, endpoint) not in self.endpoints:
            raise Unavailable('endpoint outside read/build allowlist')
        time.sleep(max(0, self.min_interval - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        target = '/api/v1/dex/' + endpoint
        payload = encoded(params) if method == 'POST' else b''
        if method == 'GET':
            target += '?' + urlencode(params)
        stamp = utc()
        sig = base64.b64encode(hmac.new(self.secret.encode(), stamp.encode() + method.encode()
              + b'/build' + target.encode() + payload, hashlib.sha256).digest()).decode()
        req = Request('https://web3.binance.com/build' + target, method=method,
                      data=payload if method == 'POST' else None,
                      headers={'X-OC-APIKEY': self.key, 'X-OC-TIMESTAMP': stamp, 'X-OC-SIGN': sig,
                               'Content-Type': 'application/json'})
        private_values = []
        for name in self.private_params:
            value = params.get(name)
            if isinstance(value, str) and value:
                private_values.append(value)
                private_values.append(base64.b64encode(value.encode()).decode())
                if value.startswith('0x'):
                    # A prefix or hex case change still leaves usable signed bytes.
                    private_values.append(value[2:])
                    try:
                        private_values.append(base64.b64encode(bytes.fromhex(value[2:])).decode())
                    except ValueError:
                        pass  # non-hex private parameters are still redacted
        secrets = (self.key, self.secret, sig, *private_values)
        stored = {k: ('sha256:' + hashlib.sha256(str(v).encode()).hexdigest() if k in self.private_params else v)
                  for k, v in params.items()}
        record = dict(schema='Web3Observation.v1', source_id='BINANCE_WEB3', endpoint=endpoint,
                      method=method, params=stored, requested_at=stamp)
        start = time.monotonic()
        try:
            try:
                response = self.opener.open(req, timeout=self.timeout)
            except HTTPError as e:
                response = e
            with response:
                raw = response.read(2 * 1024 * 1024 + 1)
                status = response.code
            record['http_status'] = status
            record['response_sha256'] = hashlib.sha256(raw).hexdigest()
            if len(raw) > 2 * 1024 * 1024:
                raise Unavailable('response_too_large')
            try:
                body = json.loads(raw)
            except (ValueError, UnicodeError):
                raise Unavailable('non_json_response') from None
            code = body.get('code') if isinstance(body, dict) else None
            if code == 40304:
                outcome = 'compliance_restriction'
            elif status == 403:
                outcome = 'http_forbidden_unclassified'
            elif status == 401 or code in (40100, 40101, 40102, 40103, 40104):
                outcome = 'authentication_error'
            elif status == 429 or code == 42900:
                outcome = 'rate_limited'
            elif 200 <= status < 300 and type(body) is dict and type(body.get('code')) is int and body['code'] == 0:
                outcome = 'ok'
            else:
                outcome = 'api_or_http_error'
            record.update(outcome=outcome, response=body)
            # Keep exact public response bytes only if no credential or private
            # request value is reflected, including overwritten JSON keys.
            # JSON escapes or a duplicate key can hide a reflected credential in the raw bytes.
            # Inspect every parsed key/value too before retaining a reversible copy.
            private_reflection = False
            if private_values:
                # Preserve all pairs for screening: a parser's last-key-wins rule
                # must not hide an escaped/mixed-case private value in raw exports.
                pairs = json.loads(raw, object_pairs_hook=lambda items: [list(item) for item in items])
                private_reflection = redact(pairs, private_values, ignore_case=True) != pairs
            if not private_reflection and not reflects_secret(raw, secrets) and redact(body, secrets) == body:
                record['response_body_base64'] = base64.b64encode(raw).decode()
            else:
                record['raw_body_omitted'] = ('private_parameter_reflection'
                    if private_reflection or reflects_secret(raw, private_values)
                    else 'credential_reflection')
        except (URLError, TimeoutError, OSError):
            record['outcome'] = 'transport_error'
        except Unavailable as e:
            record['outcome'] = str(e)
        record.update(available_at=utc(), elapsed_ms=round((time.monotonic() - start) * 1000))
        # Headers and exceptions are never captured. Private parameters must also
        # be removed from parsed response values and keys before artifact storage.
        record = redact(record, secrets)
        record = redact(record, private_values, ignore_case=True)
        record['artifact_sha256'] = self.artifacts.put(record)
        if record['outcome'] != 'ok':
            raise Unavailable(record['outcome'])
        return record


def data(record):
    return record['response']['data']


def single(record):
    result = data(record)
    if isinstance(result, list) and len(result) == 1:
        result = result[0]
    if type(result) is not dict:
        raise Unavailable('unexpected response shape')
    return result

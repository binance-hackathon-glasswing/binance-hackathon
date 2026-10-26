"""IDEA-103 TH-01: bounded, point-in-time Web3 token history for S1 session trends.

Timestamp/adjustment qualification is an explicit pinned installation input. This
module never infers it from a candle label and never substitutes share prices.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re

from larp.contracts import ContractError, Document
from larp.marketdata.port import TOKENS
from larp.marketdata.web3 import Unavailable
from larp.strategy.schema import instant
from larp.strategy.sessions import token_sessions
from larp.strategy.s1 import config as s1_config

CONFIG_FILE = '/etc/larp/token-history.json'
MAX_CONFIG_BYTES = 4096
MAX_PAGES = 2
PAGE_SIZE = 300
HOUR_MS = 3_600_000
RETRY_MS = 900_000
MAX_CAPTURE_LAG_MS = 60_000  # ten bounded five-second requests, plus transport spacing


def requires_history(profile):
    return (profile.get('baseline') == 'TREND_GUARDED_VOL'
            and profile.get('policy_id') in ('larp-fs1-final-v1', 'larp-fs1-rehearsal-v1'))


def configuration(value):
    keys = {'schema', 'timestamp_kind', 'timestamp_evidence_sha256', 'token_adjustment_version'}
    if (type(value) is not dict or set(value) != keys or value.get('schema') != 'TokenHistoryConfig.v1'
            or value.get('timestamp_kind') != 'OPEN'
            or type(value.get('timestamp_evidence_sha256')) is not str
            or not re.fullmatch('[0-9a-f]{64}', value['timestamp_evidence_sha256'])
            or type(value.get('token_adjustment_version')) is not str
            or not 1 <= len(value['token_adjustment_version'].strip()) <= 128):
        raise ContractError('Qualified hourly candle OPEN semantics and token adjustment version required')
    return dict(value)


def settings(driver, profile):
    path, sha = driver.get('token_history_file'), driver.get('token_history_sha256')
    if path is None and sha is None:
        if requires_history(profile):
            raise ContractError('FS1 requires pinned token history configuration (IDEA-103)')
        return None
    if (profile.get('baseline') != 'TREND_GUARDED_VOL' or type(path) is not str or not path.startswith('/')
            or type(sha) is not str or not re.fullmatch('[0-9a-f]{64}', sha)):
        raise ContractError('Token history requires an S1 profile, absolute file and SHA-256 together')
    return path, sha


def _ms(value):
    return int(instant(value).timestamp() * 1000)


def _iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


class SessionHistory:
    """One callback shared by all rounds, backed by a compact restart cache.

    Fetch at most ten pages per refresh. No network on a cache hit or in replay.
    Unavailable history is explicit data; it must not abort mandatory risk planning.
    """
    def __init__(self, port, *, profile, calendar, calendar_sha256, issuers, semantics, root):
        self.port, self.cfg = port, s1_config(profile)
        self.semantics = configuration(semantics)
        self.identities = {m['token']: m['underlying_id'] for m in issuers.values()}
        if set(self.identities) != set(TOKENS):
            raise ContractError('Token history requires all five pinned issuer identities')
        self.calendar = dict(calendar, content_hash=calendar_sha256)
        self.sessions = [(s['session_index'], _ms(s['open_at']), _ms(s['close_at'])) for s in calendar['sessions']]
        if (not self.sessions or any(b[0] != a[0] + 1 or b[1] <= a[2]
                                     for a, b in zip(self.sessions, self.sessions[1:]))):
            raise ContractError('Token history requires the frozen ordered session calendar')
        self.binding = Document.from_dict(dict(profile=profile, calendar=self.calendar,
            identities=self.identities, semantics=self.semantics)).digest('larp.session-history-binding.v1')
        self.path = Path(root) / 'session-history-cache.json'
        self.cache = self._load()

    def _missing(self, reason):
        return {s: dict(schema='PriceSeries.v1', instrument_kind='TOKEN', symbol=s, token_id=TOKENS[s],
                        entity_id=self.identities[s], quality='UNAVAILABLE', history_status=reason, bars=[])
                for s in sorted(TOKENS)}

    def _load(self):
        try:
            if self.path.is_symlink():
                return None
            with self.path.open('rb') as stream:
                raw = stream.read(256 * 1024 + 1)
            if len(raw) > 256 * 1024:
                return None
            wrapper = json.loads(raw)
            value = wrapper['value']
            if (type(value) is not dict or value.get('schema') != 'SessionHistoryCache.v1'
                    or type(value.get('series')) is not dict or set(value['series']) != set(TOKENS)
                    or type(value.get('complete')) is not bool
                    or any(type(value.get(k)) is not int or value[k] < 0
                           for k in ('target', 'attempted_ms', 'available_ms'))
                    or any(type(v) is not dict or v.get('token_id') != TOKENS[s]
                           or v.get('entity_id') != self.identities[s] for s,v in value['series'].items())
                    or value.get('binding') != self.binding or wrapper['sha256'] !=
                    Document.from_dict(value).digest('larp.session-history-cache.v1')):
                return None
            return value
        except (OSError, ValueError, KeyError, TypeError, AttributeError, ContractError):
            return None

    def _save(self, value):
        wrapper = Document.from_dict(dict(value=value,
            sha256=Document.from_dict(value).digest('larp.session-history-cache.v1'))).payload
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.path.with_name(self.path.name + '.tmp')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(wrapper)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)

    def __call__(self, now_ms):
        eligible = [s for s in self.sessions if s[2] + self.cfg['delay'] * 1000 <= now_ms]
        if len(eligible) < self.cfg['window']:
            return self._missing('INSUFFICIENT_CALENDAR_HISTORY')
        window = eligible[-self.cfg['window']:]
        target = window[-1][0]
        cached = self.cache
        if (type(cached) is dict and cached.get('target') == target
                and type(cached.get('attempted_ms')) is int and cached['attempted_ms'] <= now_ms
                and type(cached.get('available_ms')) is int
                and cached['available_ms'] <= cached['attempted_ms'] + MAX_CAPTURE_LAG_MS
                and (cached.get('complete') is True
                     or cached['attempted_ms'] // RETRY_MS == now_ms // RETRY_MS)):
            if cached['available_ms'] > now_ms:
                return self._missing('AWAITING_CAPTURE_CUTOFF')
            return deepcopy(cached['series'])
        value = dict(schema='SessionHistoryCache.v1', binding=self.binding, target=target, attempted_ms=now_ms,
                     available_ms=now_ms, complete=False, series=self._missing('HISTORY_UNAVAILABLE'))
        try:
            series = {s: self._fetch(s, window, now_ms) for s in sorted(TOKENS)}
            value.update(series=series, complete=all(v['quality'] == 'VALID' for v in series.values()),
                         available_ms=max(_ms(v['available_at']) for v in series.values()))
        except (Unavailable, ContractError, OSError, ValueError, KeyError, TypeError, OverflowError):
            # Never retain exception text: transport/provider messages can contain reflected secrets.
            value.update(series=self._missing('HISTORY_UNAVAILABLE'), complete=False, available_ms=now_ms)
        try:
            self._save(value)  # failed attempts also retain restart-safe request backoff
        except OSError:
            value.update(series=self._missing('HISTORY_CACHE_UNAVAILABLE'), complete=False, available_ms=now_ms)
        self.cache = value
        if value['available_ms'] > now_ms:
            return self._missing('AWAITING_CAPTURE_CUTOFF')
        return deepcopy(value['series'])

    def _fetch(self, symbol, window, now_ms):
        earliest = window[0][1] - window[0][1] % HOUR_MS
        latest = window[-1][2]
        rows, hashes, available, cursor, previous_oldest = {}, [], [], None, None
        for _ in range(MAX_PAGES):
            raw = self.port.candles(symbol, bar='1h', limit=PAGE_SIZE,
                                    **({'after': cursor} if cursor is not None else {}))
            if raw.get('symbol') != symbol or raw.get('token_id') != TOKENS[symbol] or raw.get('bar') != '1h':
                raise ContractError('Historical candle identity differs')
            acquired = _ms(raw['available_at'])
            if acquired < latest or acquired > now_ms + MAX_CAPTURE_LAG_MS:
                raise ContractError('Historical capture is future-dated')
            available.append(acquired)
            sha = raw['content_hash']
            if type(sha) is not str or not re.fullmatch('[0-9a-f]{64}', sha):
                raise ContractError('Historical candle provenance missing')
            hashes.append(sha)
            page = raw['rows']
            if type(page) is not list or len(page) > PAGE_SIZE:
                raise ContractError('Historical candle page outside budget')
            stamps = []
            for row in page:
                if type(row) is not list or len(row) != 7:
                    raise ContractError('Malformed historical candle')
                stamp = int(row[5]) if type(row[5]) is str and row[5].isdigit() else row[5]
                if type(stamp) is not int or stamp < 0 or stamp % HOUR_MS or (stamps and stamp <= stamps[-1]):
                    raise ContractError('Historical candle interval/ordering differs')
                values = []
                for n, cell in enumerate(row[:5]):
                    if type(cell) not in (str, int, float) or len(str(cell)) > 128:
                        raise ContractError('Malformed historical candle quantity')
                    try:
                        number = Decimal(str(cell))
                    except InvalidOperation as exc:
                        raise ContractError('Malformed historical candle quantity') from exc
                    if not number.is_finite() or (number <= 0 if n < 4 else number < 0):
                        raise ContractError('Invalid historical candle quantity')
                    if len(number.as_tuple().digits) > 64 or abs(number.as_tuple().exponent) > 64:
                        raise ContractError('Historical candle precision outside bounded representation')
                    values.append(format(number, 'f'))
                opened, high, low, closed = map(Decimal, values[:4])
                if high < max(opened, closed) or low > min(opened, closed) or high < low:
                    raise ContractError('Inconsistent historical OHLC range')
                trades = int(row[6]) if type(row[6]) is str and row[6].isdigit() else row[6]
                if trades is not None and (type(trades) is not int or trades < 0):
                    raise ContractError('Invalid historical trade count')
                row = values + [stamp, trades]  # immutable Documents use decimal strings, never JSON floats
                if stamp in rows and rows[stamp] != row:
                    raise ContractError('Conflicting historical candle overlap')
                rows[stamp] = row
                stamps.append(stamp)
            if not stamps:
                break
            oldest = stamps[0]
            if previous_oldest is not None and oldest >= previous_oldest:
                raise ContractError('Historical candle paging made no progress')
            if oldest <= earliest:
                break
            cursor, previous_oldest = oldest - 1, oldest
        acquired = max(available)
        capture = Document.from_dict(dict(schema='TokenCandles.v1', symbol=symbol, token_id=TOKENS[symbol],
            entity_id=self.identities[symbol], source_id='BINANCE_WEB3', content_hash=Document.from_dict(
                dict(source_hashes=hashes)).digest('larp.session-history-pages.v1'),
            available_at=_iso(acquired), timestamp_kind=self.semantics['timestamp_kind'],
            timestamp_evidence_hash=self.semantics['timestamp_evidence_sha256'],
            token_adjustment_version=self.semantics['token_adjustment_version'], bar_seconds=3600,
            candles=[r for stamp, r in sorted(rows.items()) if earliest <= stamp and stamp + HOUR_MS <= latest]))
        cal = Document.from_dict(dict(self.calendar, sessions=[s for s in self.calendar['sessions']
            if window[0][0] <= s['session_index'] <= window[-1][0]]))
        result = token_sessions(capture, cal, cutoff=instant(_iso(max(now_ms, acquired))),
                                allow_calendar_close=True, exact_prices=True).read()
        result.update(available_at=_iso(acquired), timestamp_evidence_hash=self.semantics['timestamp_evidence_sha256'],
                      source_hashes=hashes, history_status='READY')
        if [b['session_index'] for b in result['bars']] != [s[0] for s in window]:
            result.update(quality='UNAVAILABLE', history_status='INCOMPLETE_SESSION_WINDOW')
        return result

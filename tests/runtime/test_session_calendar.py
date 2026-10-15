"""IDEA-054: the frozen 2026 session calendar the runtime pins (criteria 1, 2, 4, 5)."""
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from zoneinfo import ZoneInfo

from larp.contracts import ContractError, Document
from larp.runtime.driver import SessionCalendar
from larp.runtime.service import _pinned_json
from larp.strategy.schema import instant
from larp.strategy.sessions import token_sessions
from tools import build_session_calendar as tool

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / 'config' / 'runtime' / 'session-calendar.2026.json'
ET = ZoneInfo('America/New_York')
HOLIDAYS = {date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 4, 3), date(2026, 5, 25),
            date(2026, 6, 19), date(2026, 7, 3), date(2026, 9, 7), date(2026, 11, 26), date(2026, 12, 25)}


def ms(value):
    return int(instant(value).timestamp() * 1000)


def load():
    return json.loads(FILE.read_bytes())


class Sessions(unittest.TestCase):
    def test_c1_every_2026_trading_weekday_once_in_order(self):
        sessions = load()['sessions']
        self.assertEqual(len(sessions), 251)
        self.assertEqual([s['session_index'] for s in sessions], list(range(251)))
        days = [date.fromisoformat(s['date']) for s in sessions]
        self.assertEqual((days[0], days[-1]), (date(2026, 1, 2), date(2026, 12, 31)))
        expected = [date(2026, 1, 1) + timedelta(days=n) for n in range(365)]
        expected = [d for d in expected if d.weekday() < 5 and d not in HOLIDAYS]
        self.assertEqual(days, expected)
        self.assertEqual({date.fromisoformat(h['date']) for h in load()['holidays']}, HOLIDAYS)

    def test_c2_open_and_close_in_new_york_time_with_two_early_closes(self):
        early = []
        for s in load()['sessions']:
            opened, closed = instant(s['open_at']).astimezone(ET), instant(s['close_at']).astimezone(ET)
            self.assertEqual(opened.date().isoformat(), s['date'])
            self.assertEqual((opened.date(), opened.time()), (closed.date(), time(9, 30)))
            if s.get('early_close'):
                early.append(s['date'])
                self.assertEqual(closed.time(), time(13, 0))
            else:
                self.assertNotIn('early_close', s)
                self.assertEqual(closed.time(), time(16, 0))
        self.assertEqual(early, ['2026-11-27', '2026-12-24'])
        by_day = {s['date']: s for s in load()['sessions']}
        for day, key, value in (('2026-03-06', 'open_at', '2026-03-06T14:30:00Z'),
                                ('2026-03-09', 'open_at', '2026-03-09T13:30:00Z'),
                                ('2026-10-30', 'open_at', '2026-10-30T13:30:00Z'),
                                ('2026-11-02', 'open_at', '2026-11-02T14:30:00Z'),
                                ('2026-11-27', 'close_at', '2026-11-27T18:00:00Z')):
            self.assertEqual(by_day[day][key], value)


class Consumers(unittest.TestCase):
    def test_c4_runtime_calendar_covers_the_shadow_rehearsal_and_final_windows(self):
        calendar = SessionCalendar(load())
        step = 15 * 60_000
        for now in range(ms('2026-10-15T00:00:00Z'), ms('2026-11-11T16:00:00Z') + 1, step):
            calendar(now)
        index = {s['date']: s['session_index'] for s in load()['sessions']}
        self.assertEqual(calendar(ms('2026-10-30T15:00:00Z')),
                         {'index': index['2026-10-30'], 'remaining': 251 - index['2026-10-30']})
        # Weekend across the DST change: still Friday's session, Friday already closed.
        self.assertEqual(calendar(ms('2026-11-01T12:00:00Z')),
                         {'index': index['2026-10-30'], 'remaining': 251 - index['2026-11-02']})
        self.assertEqual(calendar(ms('2026-11-02T14:29:59Z'))['index'], index['2026-10-30'])
        self.assertEqual(calendar(ms('2026-11-02T14:30:00Z'))['index'], index['2026-11-02'])
        self.assertEqual(index['2026-11-02'], index['2026-10-30'] + 1)
        for outside in ('2026-01-02T14:29:59Z', '2026-12-31T21:00:00Z'):
            with self.subTest(outside), self.assertRaises(ContractError):
                calendar(ms(outside))

    def test_c4_token_sessions_keep_full_days_and_leave_early_closes_missing(self):
        cal = load()
        index = {s['date']: s['session_index'] for s in cal['sessions']}
        rows = []
        for day in (date(2026, 10, 30), date(2026, 11, 27)):
            start = datetime.combine(day, time(9, 0), ET)
            for i in range(7):
                ts = int((start + timedelta(hours=i)).astimezone(timezone.utc).timestamp() * 1000)
                rows.append(['10', '11', '9', str(10 + i), '5', ts, 1])
        capture = {'schema': 'TokenCandles.v1', 'symbol': 'GOOGLB', 'token_id': 'fixture-googl-token',
                   'entity_id': 'fixture-googl-issuer', 'source_id': 'SYNTHETIC_WEB3_ROWS', 'content_hash': 'a' * 64,
                   'available_at': '2026-11-30T00:00:00Z', 'timestamp_kind': 'OPEN', 'bar_seconds': 3600,
                   'token_adjustment_version': 'synthetic-no-actions', 'candles': rows}
        series = token_sessions(Document.from_dict(capture), Document.from_dict(cal),
                                cutoff=instant('2026-11-30T00:00:00Z')).read()
        self.assertEqual([b['session_index'] for b in series['bars']], [index['2026-10-30']])
        self.assertEqual(series['bars'][0]['close_at'], '2026-10-30T20:00:00+00:00')
        self.assertIn(index['2026-11-27'], series['missing_sessions'])
        self.assertEqual(series['calendar_hash'], cal['content_hash'])


class Pinning(unittest.TestCase):
    def test_c5_content_hash_and_byte_for_byte_regeneration(self):
        raw = FILE.read_bytes()
        self.assertEqual(load()['content_hash'], tool.content_hash(load()))
        self.assertEqual(tool.build(), raw)
        self.assertEqual(tool.main(['--check']), 0)
        with tempfile.TemporaryDirectory() as tmp:
            changed = Path(tmp) / 'calendar.json'
            changed.write_bytes(raw.replace(b'"2026-10-30T13:30:00Z"', b'"2026-10-30T13:31:00Z"', 1))
            self.assertNotEqual(changed.read_bytes(), raw)
            self.assertEqual(tool.main(['--check', '--output', str(changed)]), 1)

    def test_c5_runtime_example_pins_the_committed_file(self):
        example = json.loads((ROOT / 'config' / 'runtime' / 'runtime.example.json').read_text())
        pinned = example['driver']['session_calendar_sha256']
        self.assertEqual(pinned, hashlib.sha256(FILE.read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp) / 'session-calendar.json'  # the host copies the file to /etc/larp (DEPLOYMENT_DAY step 7)
            shutil.copyfile(FILE, host)
            SessionCalendar(_pinned_json(str(host), pinned, 'Session calendar'))
            host.write_bytes(host.read_bytes() + b' ')
            with self.assertRaises(ContractError):
                _pinned_json(str(host), pinned, 'Session calendar')


if __name__ == '__main__':
    unittest.main()

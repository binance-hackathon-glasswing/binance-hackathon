"""Build the frozen USRegularSessions.v1 calendar the runtime pins (IDEA-054).

Every NYSE regular session of 2026: 09:30-16:00 America/New_York, 13:00 on the
two early-close days, converted to UTC. Holidays and early closes are copied
from the NYSE Group release cited in SOURCE; nothing is inferred from a rule.

    python tools/build_session_calendar.py            # write the file
    python tools/build_session_calendar.py --check    # verify the committed file byte for byte
"""
import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from larp.contracts import Document  # noqa: E402

ET = ZoneInfo('America/New_York')
YEAR = 2026
OUTPUT = ROOT / 'config' / 'runtime' / f'session-calendar.{YEAR}.json'
CALENDAR_ID = f'nyse-regular-{YEAR}'
SOURCE = {
    'publisher': 'NYSE Group',
    'title': 'NYSE Group Announces 2026, 2027 and 2028 Holiday and Early Closings Calendar',
    'published': '2025-12-23',
    'urls': ['https://www.businesswire.com/news/home/20251223981478/en/',
             'https://www.nyse.com/markets/hours-calendars'],
    'cross_check': 'exchange_calendars 4.13.2 XNYS schedule, identical (IDEA-054 criterion 3)',
}
HOLIDAYS = {
    date(2026, 1, 1): "New Year's Day",
    date(2026, 1, 19): 'Martin Luther King, Jr. Day',
    date(2026, 2, 16): "Washington's Birthday",
    date(2026, 4, 3): 'Good Friday',
    date(2026, 5, 25): 'Memorial Day',
    date(2026, 6, 19): 'Juneteenth National Independence Day',
    date(2026, 7, 3): 'Independence Day (observed)',
    date(2026, 9, 7): 'Labor Day',
    date(2026, 11, 26): 'Thanksgiving Day',
    date(2026, 12, 25): 'Christmas Day',
}
EARLY_CLOSES = {date(2026, 11, 27), date(2026, 12, 24)}
OPEN, CLOSE, EARLY_CLOSE = time(9, 30), time(16, 0), time(13, 0)


def _utc(day, at):
    return datetime.combine(day, at, ET).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def build():
    sessions, day = [], date(YEAR, 1, 1)
    while day.year == YEAR:
        if day.weekday() < 5 and day not in HOLIDAYS:
            early = day in EARLY_CLOSES
            session = {'session_index': len(sessions), 'date': day.isoformat(), 'open_at': _utc(day, OPEN),
                       'close_at': _utc(day, EARLY_CLOSE if early else CLOSE)}
            if early:
                session['early_close'] = True
            sessions.append(session)
        day += timedelta(days=1)
    body = {'schema': 'USRegularSessions.v1', 'calendar_id': CALENDAR_ID, 'exchange': 'XNYS',
            'timezone': 'America/New_York', 'regular_hours': '09:30-16:00', 'early_close_hours': '09:30-13:00',
            'holidays': [{'date': d.isoformat(), 'name': n} for d, n in sorted(HOLIDAYS.items())],
            'early_closes': sorted(d.isoformat() for d in EARLY_CLOSES),
            'provenance': {'source': SOURCE, 'decision_id': 'IDEA-054'},
            'sessions': sessions}
    body['content_hash'] = Document.from_dict(body).digest('USRegularSessions.v1')
    return (json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')


def content_hash(document):
    """The calendar's own hash: its canonical bytes without `content_hash`."""
    return Document.from_dict({k: v for k, v in document.items() if k != 'content_hash'}).digest(
        'USRegularSessions.v1')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--check', action='store_true', help='verify the committed file instead of writing it')
    p.add_argument('--output', type=Path, default=OUTPUT)
    args = p.parse_args(argv)
    raw = build()
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != raw:
            print('MISMATCH', args.output, file=sys.stderr)
            return 1
        print('OK', args.output, hashlib.sha256(raw).hexdigest())
        return 0
    args.output.write_bytes(raw)
    print(args.output, hashlib.sha256(raw).hexdigest())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

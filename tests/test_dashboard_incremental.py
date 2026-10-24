"""IDEA-092 E1-E3: the incremental decisions export reads only new events, streamed. Synthetic journal; no database."""
import json
from pathlib import Path
import tempfile
import unittest

from tests.test_dashboard_decisions import EXPORT, events, load_export, planned
from tools.dashboard import decisions as dec


def journal(evs):
    """(sequence, raw batch bytes) pairs, as the export's cursor yields them."""
    return [(seq, json.dumps(dict(event=e)).encode()) for seq, e in evs]


class Counting:
    def __init__(self):
        self.calls = 0

    def __call__(self, raw):
        self.calls += 1
        return json.loads(raw)


def summary(lines):
    return json.loads(lines[-1])


class Incremental(unittest.TestCase):
    def setUp(self):
        self.x = load_export()

    def test_e1_rows_oldest_first_cursor_and_trimmed_rows_come_next(self):
        rows = journal(events())
        lines = self.x['emit_since'](rows, 'run', 0, Counting())
        s = summary(lines)
        self.assertEqual((s['since'], s['last_seq'], s['complete'], s['exported']), (0, 8, True, 3))
        ids = [json.loads(l)['round_id'] for l in lines[:-1]]
        self.assertEqual(ids, ['cadence:100#1', 'cadence:101#1', 'filing:job-7#1'])  # oldest first
        # A small budget trims: the summary stops before the first row left out, and the next export brings it.
        first = self.x['emit_since'](rows, 'run', 0, Counting(), budget=2200)
        s1 = summary(first)
        self.assertFalse(s1['complete'])
        self.assertLess(s1['last_seq'], 8)
        rest = self.x['emit_since'](rows, 'run', s1['last_seq'], Counting(), budget=2200)
        got = [json.loads(l)['round_id'] for l in first[:-1] + rest[:-1]]
        self.assertEqual(got[:3], ids)

    def test_e1_a_round_planned_earlier_gets_a_closure_line(self):
        rows = journal(events() + [(9, dict(kind='ROUND_CLOSED', status='COMPLETE', round_id='cadence:100#1'))])
        lines = self.x['emit_since'](rows, 'run', 8, Counting())
        self.assertEqual([json.loads(l) for l in lines[:-1]],
                         [dict(section='closure', schema='LarpDecisionExport.v1', seq=9, round_id='cadence:100#1',
                               status='COMPLETE')])

    def test_e1_the_database_part_streams_after_the_cursor(self):
        db = EXPORT.read_text().split('# ---- database')[1]
        self.assertIn("db.cursor(name='larp_dashboard_export')", db)
        self.assertIn('cur.itersize = 20', db)
        self.assertIn('sequence>%s', db)
        self.assertNotIn('fetchall', db)

    def test_e2_successive_exports_merge_to_the_same_result_as_one(self):
        full = events() + [(9, dict(kind='ROUND_CLOSED', status='COMPLETE', round_id='cadence:100#1')),
                           planned(10, 'cadence:102#1', 30), (11, dict(kind='ROUND_CLOSED', status='COMPLETE',
                                                                         round_id='cadence:102#1'))]
        with tempfile.TemporaryDirectory() as tmp:
            once, step = Path(tmp) / 'once', Path(tmp) / 'step'
            dec.merge('\n'.join(self.x['emit_since'](journal(full), 'run', 0, Counting())), once)
            for upto in (3, 5, 8, 9, 11):  # the journal grows between exports
                while True:
                    lines = self.x['emit_since'](journal(full[:upto]), 'run', dec.cursor(step), Counting(), budget=2200)
                    dec.merge('\n'.join(lines), step)
                    if summary(lines)['complete']:
                        break
            self.assertEqual((step / dec.FILE).read_text(), (once / dec.FILE).read_text())
            self.assertEqual(dec.cursor(step), 11)
            closed = {json.loads(l)['round_id']: json.loads(l)['status'] for l in (step / dec.FILE).read_text().splitlines()}
            self.assertEqual(closed['cadence:100#1'], 'COMPLETE')

    def test_e3_only_new_events_are_decoded(self):
        old = [(n, dict(kind='OBSERVATION', note='x' * 2000)) for n in range(1, 1001)]
        new = [planned(1001, 'cadence:500#1', 0)] + [(n, dict(kind='OBSERVATION')) for n in range(1002, 1006)]
        load = Counting()
        lines = self.x['emit_since'](journal(old + new), 'run', 1000, load)
        self.assertEqual(load.calls, 5)
        self.assertEqual((summary(lines)['decoded'], summary(lines)['last_seq']), (5, 1005))


if __name__ == '__main__':
    unittest.main()

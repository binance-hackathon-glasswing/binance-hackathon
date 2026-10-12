import tempfile
from pathlib import Path
import unittest
from larp.sources.live import PollLog, LiveRunner, gap_report

class PollRecovery(unittest.TestCase):
    def test_torn_bytes_remain_visible_and_complete_records_keep_cadence(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = PollLog(Path(tmp) / 'polls.jsonl')
            torn = b'{"schema":"LivePoll.v1","target":"edgar:ISS-A"\xff'
            log.path.write_bytes(torn)
            record = dict(schema='LivePoll.v1', target='edgar:ISS-A', started_ms=1000000,
                          cadence_ms=300000, status='OK')
            log.append(record)
            self.assertTrue(log.path.read_bytes().startswith(torn + b'\n'))
            lines = log.lines()  # a corrupt entry also carries the torn bytes' length and SHA-256
            self.assertEqual(([l.get('corrupt') for l in lines], lines[1]), ([True, None], record))
            runner = LiveRunner(register={}, issuers=['ISS-A'], source_ingestor=None,
                                edgar_ingestor=None, log=log, clock_ms=lambda:1060000)
            self.assertEqual(runner.due(1060000), [])
            log.append(dict(record, started_ms=1300000))
            self.assertEqual(len(log.lines()), 3)

    def test_gap_report_cannot_be_relaxed_by_cli_cadence(self):
        lines = [dict(target='edgar:ISS-A', started_ms=t, cadence_ms=60000, status='OK')
                 for t in (0, 200000, 400000)]
        report = gap_report(lines, cadences={'edgar:ISS-A':300000}, start_ms=0,
                            end_ms=400000, required_ms=400000)
        self.assertEqual(report['verdict'], 'FAIL')
        # cadence_ms reports the declared cadence; the run's own logged cadence is listed and governs when stricter
        self.assertEqual(report['targets']['edgar:ISS-A']['logged_cadences_ms'], [60000])

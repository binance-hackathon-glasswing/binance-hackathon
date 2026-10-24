"""IDEA-087 DX1-DX4: the agent's decisions on the Pages dashboard, from synthetic round events. No database, no
network."""
from copy import deepcopy
import json
from pathlib import Path
import re
import tempfile
import unittest

from tests.test_dashboard import keys, write_monitor
from tools.dashboard import build as b
from tools.dashboard import decisions as dec

EXPORT = Path(__file__).resolve().parents[1] / 'tools/dashboard/decisions-export.sh'
PLANTED = ['0x' + 'ab' * 20, '0x' + 'cd' * 32, 'quote-7f3e9a', 'intent-55c1d2', 'I expect NVDA to rally because',
           'postgres://larp@db.internal/larp', 'https://example.invalid/filing', 'cadence:100#1', 'filing:job-7#1']
MS = 1792821600000  # 2026-10-24T06:00:00Z


def export_code():
    """The export's Python, up to its database part: the shaping and emitting functions only."""
    text = EXPORT.read_text()
    body = text[text.index("<<'PY'\n") + len("<<'PY'\n"):text.rindex('\nPY\n')]
    return body[:body.index('# ---- database')]


def load_export():
    scope = {}
    exec(compile(export_code(), str(EXPORT), 'exec'), scope)
    return scope


def planned(seq, round_id, minute, **record):
    plan = dict(schema='PlanResult.v1', snapshot_id='snap-1', intents=record.pop('intents', []),
                rejections=record.pop('rejections', []), clamps=record.pop('clamps', []),
                reservation_deltas=[], jobs=[])
    if 'reasons' in record:
        plan['reasons'] = record.pop('reasons')
    base = dict(round_id=round_id, request=dict(prompt=PLANTED[4]), plan=plan, errors=record.pop('errors', []),
                started_ms=MS + minute * 60000 - 4000, decision_ms=MS + minute * 60000, orders=[],
                policy_input=dict(dsn=PLANTED[5]), proposal_id='prop-1', swap_mappings=[])
    base.update(record)
    kind = record.pop('kind', None) or 'ROUND_PLANNED'
    base.pop('kind', None)
    return seq, dict(kind=kind, record=base)


def events():
    buy = dict(symbol='SKHYB', side='BUY', token_units=137879758, cash_units=18951721, mandatory=False,
               reasons=['S1_ENTRY'], intent_id=PLANTED[3], quote_id=PLANTED[2], pay_asset=PLANTED[0],
               decision_id=PLANTED[1], amount='18.951721')
    return [
        (1, dict(kind='RUN_ACTIVATED', detail=PLANTED[5])),
        planned(2, 'cadence:100#1', 0, intents=[buy], orders=[dict(symbol='SKHYB', side='BUY', amount='18.951721',
                                                                   tx_hash=PLANTED[1])],
                policy_output=dict(targets=[dict(symbol='SKHYB', kind='TARGET_WEIGHT', reason='S1_ENTRY', weight=[19, 100]),
                                            dict(symbol='NVDAB', kind='TARGET_WEIGHT', reason='S1_ENTRY', weight=[19, 100])],
                                   next_policy_state=dict(note=PLANTED[4]), valid_until='2026-10-24T06:15:00+00:00'),
                rejections=[dict(symbol='NVDAB', reason='DISCRETIONARY_CADENCE'),
                            dict(reason='INVALID_REQUIRED_INPUT', detail=PLANTED[5])],
                clamps=[dict(symbol='SKHYB', reason='PER_TRADE_CAP', requested_units=5, planned_units=4)],
                execution_pending=True,
                assessment=dict(issuer_id='SKHY', status='ACCEPTED', reasons=['FRESH_FILING'],
                                model_io=dict(cot=PLANTED[4]), url=PLANTED[6])),
        (3, dict(kind='ROUND_LOGGED', round_id='cadence:100#1')),
        planned(4, 'cadence:101#1', 15, rejections=[
            dict(symbol='NVDAB', reason='NEW_RISK_HALTED'), dict(symbol='TSLAB', reason='NEW_RISK_HALTED'),
            dict(reason='EXECUTION_BLOCKED', gates=['WALLET_PENDING', 'not a code']),
            dict(reason='PARTIAL_VALUATION_NEW_RISK_BLOCKED', symbols=['MSFTB', PLANTED[0]])],
            policy_output=dict(targets=[dict(symbol='NVDAB', kind='EXIT', reason=PLANTED[4], weight=None)])),
        (5, dict(kind='ROUND_CLOSED', status='COMPLETE', round_id='cadence:101#1')),
        planned(6, 'filing:job-7#1', 20, kind='PLAN_REJECTED', reasons=['HALTED'],
                errors=['POLICY_REJECTED', 'COMMIT_REJECTED', PLANTED[4]]),
        (7, dict(kind='ROUND_CLOSED', status='REJECTED', round_id='filing:job-7#1')),
        planned(8, 'review:' + PLANTED[1] + '#1', 25),  # a round ID carrying a hash is never exported
    ]


def merged_folder(root, export_lines):
    folder = write_monitor(Path(root) / 'monitor')
    dec.merge('\n'.join(export_lines) + '\n', folder)
    return folder


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.x = load_export()

    def test_dx1_export_is_allow_listed(self):
        lines = self.x['emit'](events(), 30, 'larp-dev-rehearsal-20261024-s2')
        text = '\n'.join(lines)
        for value in PLANTED[:7]:
            self.assertNotIn(value, text)
        self.assertIsNone(re.search(r'0x[0-9a-fA-F]{8,}', text))
        rows = [json.loads(line) for line in lines]
        summary = rows.pop()
        self.assertEqual(summary, dict(section='decisions_summary', schema='LarpDecisionExport.v1',
                                       run_id='larp-dev-rehearsal-20261024-s2', rounds=3, exported=3, closed=2))
        self.assertEqual([(r['round_id'], r['event'], r['status']) for r in rows],
                         [('cadence:100#1', 'PLANNED', None), ('cadence:101#1', 'PLANNED', 'COMPLETE'),
                          ('filing:job-7#1', 'REJECTED', 'REJECTED')])
        first, second, third = rows
        self.assertEqual(first['orders'], [dict(symbol='SKHYB', side='BUY', amount='18.951721')])
        self.assertEqual(first['intents'], [dict(symbol='SKHYB', side='BUY', mandatory=False, reasons=['S1_ENTRY'])])
        self.assertEqual(first['targets'][0], dict(symbol='SKHYB', kind='TARGET_WEIGHT', reason='S1_ENTRY', weight=[19, 100]))
        self.assertEqual(first['rejections'], [dict(symbol='NVDAB', reason='DISCRETIONARY_CADENCE'),
                                               dict(symbol=None, reason='INVALID_REQUIRED_INPUT')])
        self.assertEqual(first['assessment'], dict(issuer='SKHY', status='ACCEPTED', reasons=['FRESH_FILING']))
        self.assertTrue(first['execution_pending'])
        self.assertEqual(second['targets'], [dict(symbol='NVDAB', kind='EXIT', reason='OTHER', weight=None)])
        self.assertIn(dict(symbol=None, reason='EXECUTION_BLOCKED', gates=['WALLET_PENDING', 'OTHER']), second['rejections'])
        self.assertIn(dict(symbol=None, reason='PARTIAL_VALUATION_NEW_RISK_BLOCKED', symbols=['MSFTB']), second['rejections'])
        self.assertEqual(third['errors'], ['POLICY_REJECTED', 'COMMIT_REJECTED', 'OTHER'])
        self.assertEqual(third['rejections'], [dict(symbol=None, reason='HALTED')])
        allowed = {'section', 'schema', 'seq', 'round_id', 'event', 'started_ms', 'decision_ms', 'round_kind', 'errors',
                   'execution_pending', 'orders', 'intents', 'targets', 'rejections', 'clamps', 'assessment', 'status',
                   'symbol', 'side', 'amount', 'mandatory', 'reasons', 'kind', 'reason', 'weight', 'gates', 'symbols',
                   'issuer'}
        self.assertLessEqual(keys(rows), allowed)

    def test_dx1_export_limit(self):
        lines = self.x['emit'](events(), 2, 'run')
        self.assertEqual([json.loads(line).get('round_id') for line in lines], ['cadence:101#1', 'filing:job-7#1', None])
        self.assertEqual(json.loads(lines[-1])['exported'], 2)

    def test_rv01_default_export_fits_ssm_and_keeps_the_newest_complete_rows(self):
        dense = []
        for seq in range(1, 31):
            event = deepcopy(events()[1][1])
            event['record']['round_id'] = f'cadence:{seq}#1'
            dense.append((seq, event))
        lines = self.x['emit'](dense, 30, 'larp-dev-rehearsal-20261024-s2')
        self.assertLessEqual(sum(len(line.encode('utf-8')) + 1 for line in lines), 22000)
        parsed = [json.loads(line) for line in lines]
        summary = parsed.pop()
        self.assertEqual(summary['section'], 'decisions_summary')
        self.assertGreater(summary['omitted_for_size'], 0)
        self.assertEqual(summary['exported'] + summary['omitted_for_size'], 30)
        self.assertEqual([r['seq'] for r in parsed], list(range(31 - summary['exported'], 31)))
        _, report = dec.parse('\n'.join(lines))
        self.assertEqual(report['summary']['omitted_for_size'], summary['omitted_for_size'])
        # A single dense row must not force an incomplete JSON line or displace the summary.
        huge = deepcopy(dense[-1][1])
        huge['record']['policy_output']['targets'] *= 100
        emit = self.x['emit']
        globals_ = emit.__globals__
        previous = globals_.get('MAX_EXPORT_BYTES')
        try:
            globals_['MAX_EXPORT_BYTES'] = 250
            bounded = emit([(30, huge)], 30, 'run')
            self.assertLessEqual(sum(len(line.encode('utf-8')) + 1 for line in bounded), 250)
            self.assertEqual(len(bounded), 1)
            self.assertEqual(json.loads(bounded[0])['omitted_for_size'], 1)
        finally:
            if previous is None:
                globals_.pop('MAX_EXPORT_BYTES', None)
            else:
                globals_['MAX_EXPORT_BYTES'] = previous

    def test_dx1_database_part_is_read_only(self):
        text = EXPORT.read_text()
        db = text[text.index('# ---- database'):]
        self.assertIn("SET TRANSACTION READ ONLY", db)
        self.assertIn('with s.transaction() as db:', db)
        self.assertEqual(re.findall(r"db\.execute\('([A-Z]+)", db), ['SET', 'SELECT'])
        self.assertIsNone(re.search(r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|COPY)\b', text))


class MergeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.x = load_export()

    def tearDown(self):
        self.tmp.cleanup()

    def test_dx2_merge_is_idempotent_and_updates_closed_rounds(self):
        all_events = events()
        early = self.x['emit'](all_events[:3], 30, 'run')  # cadence:100#1 planned, still open
        folder = self.root / 'monitor'
        noise = ['== larp-runtime journal', '{"section":"run"}', 'not json', '{"schema":"LarpDecisionExport.v1"}']
        report = dec.merge('\n'.join(noise + early), folder)
        self.assertEqual((report['decisions'], report['skipped'], report['rounds'], report['added']), (1, 4, 1, 1))
        path = folder / dec.FILE
        first = path.read_bytes()
        self.assertEqual(json.loads(first)['status'], None)
        dec.merge('\n'.join(early), folder)
        self.assertEqual(path.read_bytes(), first)
        closed = all_events + [(9, dict(kind='ROUND_CLOSED', status='COMPLETE', round_id='cadence:100#1'))]
        report = dec.merge('\n'.join(self.x['emit'](closed, 30, 'run')), folder)
        self.assertEqual((report['rounds'], report['added']), (3, 2))
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual([(r['round_id'], r['status']) for r in rows],
                         [('cadence:100#1', 'COMPLETE'), ('cadence:101#1', 'COMPLETE'), ('filing:job-7#1', 'REJECTED')])
        # An older export (the round still open) never undoes a closed status.
        dec.merge('\n'.join(early), folder)
        self.assertEqual(json.loads(path.read_text().splitlines()[0])['status'], 'COMPLETE')
        # Merging into a fresh folder in another order gives the same bytes.
        other = self.root / 'other'
        dec.merge('\n'.join(self.x['emit'](closed, 30, 'run')), other)
        dec.merge('\n'.join(early), other)
        self.assertEqual((other / dec.FILE).read_bytes(), path.read_bytes())


class BuildDecisionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        lines = load_export()['emit'](events(), 30, 'run')
        self.monitor = merged_folder(self.root, lines)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dx3_numbers(self):
        d = b.dashboard_data(self.monitor)['decisions']
        self.assertEqual((d['total'], d['with_orders'], d['buys'], d['sells']), (3, 1, 1, 0))
        self.assertEqual(d['by_status'], dict(OPEN=1, COMPLETE=1, REJECTED=1))
        self.assertEqual(d['top_reasons'][0], ['NEW_RISK_HALTED', 2])
        self.assertEqual(len(d['top_reasons']), 8)
        self.assertEqual(d['latest_utc'], '2026-10-24T06:20:00Z')
        self.assertEqual([r['utc'] for r in d['rows']],
                         ['2026-10-24T06:20:00Z', '2026-10-24T06:15:00Z', '2026-10-24T06:00:00Z'])
        newest, middle, oldest = d['rows']
        self.assertEqual((newest['source'], newest['event'], newest['status']), ('FILING', 'REJECTED', 'REJECTED'))
        self.assertEqual((oldest['source'], oldest['status'], oldest['execution_pending']), ('CADENCE', None, True))
        self.assertAlmostEqual(oldest['targets'][0]['weight_pct'], 19.0, delta=1e-9)
        self.assertEqual(oldest['orders'], [dict(symbol='SKHYB', side='BUY', amount='18.951721')])
        self.assertEqual(middle['targets'][0]['weight_pct'], None)

    def test_dx3_rows_are_capped(self):
        rows = [dict(section='decision', schema=dec.SCHEMA, seq=i, round_id='cadence:%d#1' % i, event='PLANNED',
                     decision_ms=MS + i * 60000) for i in range(b.MAX_DECISIONS + 5)]
        folder = self.root / 'many'
        dec.merge('\n'.join(json.dumps(r) for r in rows), folder)
        d = b.dashboard_data(folder)['decisions']
        self.assertEqual((d['total'], len(d['rows'])), (b.MAX_DECISIONS + 5, b.MAX_DECISIONS))
        self.assertEqual(d['rows'][0]['utc'], b.ms_utc(MS + (b.MAX_DECISIONS + 4) * 60000))

    def test_dx4_redacted_build_has_no_round_ids_or_planted_values(self):
        site = self.root / 'site'
        data = b.build(self.monitor, site)
        self.assertNotIn('round_id', keys(data))
        for name in b.OUTPUTS:
            text = (site / name).read_text()
            self.assertIsNone(re.search(r'0x[0-9a-fA-F]{8,}', text), name)
            for value in PLANTED:
                self.assertNotIn(value, text, name)
        full = b.build(self.monitor, self.root / 'full', redact=False)
        self.assertEqual([r['round_id'] for r in full['decisions']['rows']],
                         ['filing:job-7#1', 'cadence:101#1', 'cadence:100#1'])

    def test_dx4_build_does_not_trust_the_file(self):
        bad = dict(section='decision', schema=dec.SCHEMA, seq=1, round_id='review:' + PLANTED[0], event=PLANTED[4],
                   status=PLANTED[5], round_kind='trade', errors=[PLANTED[6]], decision_ms='soon',
                   orders=[dict(symbol=PLANTED[0], side='HOLD', amount=PLANTED[4])],
                   targets=[dict(symbol='NVDAB', kind='EXIT', reason=PLANTED[4], weight=[1, 0])],
                   rejections=[dict(symbol=PLANTED[0], reason=PLANTED[4], detail=PLANTED[5], gates=[PLANTED[6]])],
                   assessment=dict(issuer=PLANTED[1], status=PLANTED[4], reasons=[PLANTED[5]], cot=PLANTED[4]))
        folder = self.root / 'bad'
        folder.mkdir()
        (folder / dec.FILE).write_text(json.dumps(bad) + '\n')
        for redact in (True, False):
            data = b.dashboard_data(folder, redact=redact)
            text = b.encode(data)
            for value in PLANTED:
                self.assertNotIn(value, text)
            row = data['decisions']['rows'][0]
            self.assertEqual((row['event'], row['status'], row['round_kind'], row['utc']), ('OTHER', 'OTHER', 'OTHER', None))
            self.assertEqual(row['orders'], [dict(symbol='OTHER', side=None, amount=None)])
            self.assertEqual(row['targets'][0]['weight_pct'], None)
        self.assertIsNone(b.dashboard_data(folder, redact=False)['decisions']['rows'][0]['round_id'])

    def test_dx5_no_decisions_file(self):
        folder = write_monitor(self.root / 'plain')
        data = b.dashboard_data(folder)
        self.assertEqual(data['decisions'], dict(total=0, by_status={}, with_orders=0, buys=0, sells=0, top_reasons=[],
                                                 latest_utc=None, rows=[]))
        self.assertFalse(data['inputs'][dec.FILE]['present'])


if __name__ == '__main__':
    unittest.main()

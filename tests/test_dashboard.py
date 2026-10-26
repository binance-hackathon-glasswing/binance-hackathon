"""IDEA-087 D1-D6: the Pages dashboard from synthetic chain-monitor files. No real wallet data, no network."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.dashboard import build as b
from tools.dashboard import publish as p

ROUTER = '0x' + 'b4' * 20
SPENDER = '0x' + 'c7' * 20
HASHES = ['0x' + ('%02x' % i) * 32 for i in (0xa1, 0xa2, 0xa3, 0xa4)]
E18 = 10**18
GIT_ENV = dict(GIT_AUTHOR_NAME='Dashboard Test', GIT_AUTHOR_EMAIL='test@example.invalid',
               GIT_COMMITTER_NAME='Dashboard Test', GIT_COMMITTER_EMAIL='test@example.invalid',
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')


def snapshot(minute, block, usdt, equity=None, units=None, value=None, realized=0.0, unrealized=None, trades=0,
             failed=0, gas=0.0, price_error=None):
    return dict(utc='2026-10-23T00:%02d:00Z' % minute, block=block, nonce=4 + trades, usdt=usdt, bnb=0.0053,
                units=units or {}, value_usdt=value or {}, equity_ex_bnb_usdt=equity,
                pnl_vs_start_ex_bnb_usdt=None if equity is None else equity - 96,
                realized_usdt=realized, unrealized_usdt=unrealized, gas_spent_bnb=gas, trades=trades,
                failed_txs=failed, price_error=price_error, alerts=0)


SNAPSHOTS = [
    snapshot(0, 100, 96.0, 96.0, unrealized=0.0),
    snapshot(1, 120, 48.0, 95.9, {'NVDAB': 0.25}, {'NVDAB': 47.9}, unrealized=-0.1, trades=1, gas=0.0001),
    snapshot(2, 140, 48.0, 97.0, {'NVDAB': 0.25}, {'NVDAB': 49.0}, unrealized=1.0, trades=1, gas=0.0001),
    snapshot(3, 160, 48.0, None, {'NVDAB': 0.25}, trades=1, gas=0.0001, price_error='HTTPError'),
    snapshot(4, 180, 48.0, 94.5, {'NVDAB': 0.25}, {'NVDAB': 46.5}, unrealized=-1.5, trades=1, gas=0.0001),
    snapshot(5, 200, 71.5, 94.9, {'NVDAB': 0.125}, {'NVDAB': 23.4}, realized=-0.5, unrealized=-0.6, trades=2,
             failed=1, gas=0.0002),
]
GAS = 5 * 10**13
TRANSACTIONS = [
    dict(hash=HASHES[0], nonce=4, block=110, to='0x' + '55' * 20, kind='APPROVE', status=1, gas_bnb_wei=GAS,
         token_moves={}, approvals=[dict(token='USDT', spender=ROUTER, value=48 * E18)]),
    dict(hash=HASHES[1], nonce=5, block=115, to=ROUTER, kind='SWAP', status=1, gas_bnb_wei=GAS,
         token_moves={'USDT': -48 * E18, 'NVDAB': E18 // 4}, approvals=[],
         fill=dict(side='BUY', symbol='NVDAB', units=E18 // 4, usdt=48 * E18, price=192.0)),
    dict(hash=HASHES[2], nonce=6, block=190, to='0x' + '02' * 20, kind='APPROVE', status=0, gas_bnb_wei=GAS,
         token_moves={}, approvals=[]),
    dict(hash=HASHES[3], nonce=7, block=195, to=ROUTER, kind='SWAP', status=1, gas_bnb_wei=GAS,
         token_moves={'USDT': 47 * E18 // 2, 'NVDAB': -E18 // 8}, approvals=[],
         fill=dict(side='SELL', symbol='NVDAB', units=E18 // 8, usdt=47 * E18 // 2, price=188.0, realized_usdt=-0.5)),
]
ALERTS = [
    dict(kind='ROUTER_ALLOWANCE_OPEN', allowances={'USDT': 1}, utc='2026-10-23T00:01:00Z', block=120),
    dict(kind='HOLDING_DIFFERS_FROM_FILLS', symbol='NVDAB', chain=1, fills=0, utc='2026-10-23T00:02:00Z', block=140),
    dict(kind='APPROVAL_TO_OTHER_SPENDER', tx=HASHES[2], token='NVDAB', spender=SPENDER, value=1,
         utc='2026-10-23T00:05:00Z', block=200),
    dict(kind='TX_FAILED', tx=HASHES[2], nonce=6, tx_kind='APPROVE', utc='2026-10-23T00:05:00Z', block=200),
    dict(kind='ROUTER_ALLOWANCE_OPEN', allowances={'NVDAB': 1}, utc='2026-10-23T00:05:00Z', block=200),
]


def write_monitor(folder, snapshots=SNAPSHOTS, transactions=TRANSACTIONS, alerts=ALERTS):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name, rows in zip(b.FILES, (snapshots, transactions, alerts)):
        with (folder / name).open('w') as f:  # the monitor's own format: one sorted JSON object per line
            for row in rows:
                f.write(json.dumps(row, sort_keys=True, default=str) + '\n')
    return folder


def keys(value):
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in keys(v)}
    return set()


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.monitor = write_monitor(self.root / 'monitor')

    def tearDown(self):
        self.tmp.cleanup()

    def test_d1_numbers_match_hand_computation(self):
        data = b.dashboard_data(self.monitor, redact=False)
        s = data['summary']
        expected = dict(equity_usdt=94.9, start_equity_usdt=96.0, return_usdt=-1.1, return_pct=-1.1 / 96 * 100,
                        max_drawdown_pct=2.5 / 97 * 100, current_drawdown_pct=2.1 / 97 * 100, realized_usdt=-0.5,
                        unrealized_usdt=-0.6, gas_spent_bnb=0.0002)
        for key, value in expected.items():
            self.assertAlmostEqual(s[key], value, delta=1e-9, msg=key)
        self.assertEqual((s['max_drawdown_peak_utc'], s['max_drawdown_trough_utc']),
                         ('2026-10-23T00:02:00Z', '2026-10-23T00:04:00Z'))
        self.assertEqual((s['swaps'], s['failed_txs'], s['snapshots'], s['priced_snapshots']), (2, 1, 6, 5))
        self.assertEqual((s['as_of_utc'], s['priced_as_of_utc']), ('2026-10-23T00:05:00Z',) * 2)
        self.assertEqual(s['price_error'], None)
        self.assertEqual([h['symbol'] for h in data['holdings']], ['NVDAB', 'USDT'])
        self.assertAlmostEqual(data['holdings'][0]['weight_pct'], 23.4 / 94.9 * 100, delta=1e-9)
        self.assertAlmostEqual(data['holdings'][1]['weight_pct'], 71.5 / 94.9 * 100, delta=1e-9)
        # The opening value is the first peak, so the first fill's spread is already a drawdown.
        self.assertEqual([pt[0][11:16] for pt in data['equity']['points']], ['00:00', '00:01', '00:02', '00:04', '00:05'])
        self.assertAlmostEqual(data['equity']['points'][1][2], -0.1 / 96 * 100, delta=1e-4)

    def test_d1_transactions_and_alerts(self):
        data = b.dashboard_data(self.monitor, redact=False)
        rows = data['transactions']['rows']
        self.assertEqual(data['transactions']['total'], 4)
        self.assertEqual([r['nonce'] for r in rows], [7, 6, 5, 4])  # newest first
        sell, failed, buy, approve = rows
        self.assertEqual((sell['side'], sell['symbol'], sell['units'], sell['usdt'], sell['realized_usdt']),
                         ('SELL', 'NVDAB', 0.125, 23.5, -0.5))
        self.assertEqual((buy['side'], buy['units'], buy['usdt'], buy['price']), ('BUY', 0.25, 48.0, 192.0))
        self.assertEqual((failed['ok'], failed['kind']), (False, 'APPROVE'))
        self.assertEqual((approve['kind'], approve['symbol'], approve['gas_bnb']), ('APPROVE', 'USDT', 0.00005))
        self.assertEqual([r['seen_utc'][11:16] for r in rows], ['00:05', '00:05', '00:01', '00:01'])
        alerts = {(a['kind'], a['symbol']): a for a in data['alerts']}
        self.assertEqual(alerts[('ROUTER_ALLOWANCE_OPEN', None)]['count'], 2)
        self.assertTrue(alerts[('ROUTER_ALLOWANCE_OPEN', None)]['active'])
        self.assertFalse(alerts[('HOLDING_DIFFERS_FROM_FILLS', 'NVDAB')]['active'])
        self.assertEqual(alerts[('TX_FAILED', None)]['severity'], 'critical')
        self.assertEqual(alerts[('ROUTER_ALLOWANCE_OPEN', None)]['severity'], 'warning')
        self.assertEqual(data['alerts'][-1]['kind'], 'ROUTER_ALLOWANCE_OPEN')  # critical kinds sort first

    def test_d2_redacted_site_has_no_identifiers(self):
        site = self.root / 'site'
        data = b.build(self.monitor, site)
        self.assertTrue(data['redacted'])
        self.assertFalse(keys(data) & {'hash', 'block', 'nonce', 'last_block', 'detail', 'to', 'spender', 'tx'})
        for name in b.OUTPUTS:
            text = (site / name).read_text()
            self.assertIsNone(re.search(r'0x[0-9a-fA-F]{8,}', text), name)
            for secret in HASHES + [ROUTER, SPENDER]:
                self.assertNotIn(secret[2:12], text.lower(), name)
        # The full build does keep them, so the redaction is doing the work.
        full = b.dashboard_data(self.monitor, redact=False)
        self.assertIn(HASHES[3], json.dumps(full))

    def test_d2_redaction_is_an_allow_list(self):
        odd = [dict(TRANSACTIONS[1], fill=dict(TRANSACTIONS[1]['fill'], symbol=ROUTER, venue=SPENDER),
                    kind='0x' + 'de' * 20, extra=HASHES[0])]
        alerts = [dict(kind=HASHES[1], symbol=SPENDER, utc='2026-10-23T00:05:00Z', block=200)]
        snaps = [dict(SNAPSHOTS[-1], price_error='0x' + 'ef' * 20, units={ROUTER: 1.0}, value_usdt={ROUTER: 1.0})]
        site = self.root / 'odd'
        b.build(write_monitor(self.root / 'odd-monitor', snaps, odd, alerts), site)
        for name in b.OUTPUTS:
            self.assertIsNone(re.search(r'0x[0-9a-fA-F]{8,}', (site / name).read_text()), name)

    def test_d3_build_is_deterministic(self):
        one, two = self.root / 'one', self.root / 'two'
        b.build(self.monitor, one)
        with patch('time.time', return_value=0), patch('time.gmtime', side_effect=AssertionError('clock read')):
            b.build(self.monitor, two)
        for name in b.OUTPUTS:
            self.assertEqual((one / name).read_bytes(), (two / name).read_bytes(), name)
        self.assertNotIn('2026-10-23T00:06', (one / 'index.html').read_text())
        embedded = re.search(r'<script id="dashboard-data" type="application/json">(.*?)</script>',
                             (one / 'index.html').read_text(), re.S).group(1)
        self.assertEqual(embedded + '\n', (one / 'data.json').read_text())

    def test_d4_missing_or_empty_folder(self):
        for folder in (self.root / 'absent', self.root / 'empty'):
            if folder.name == 'empty':
                folder.mkdir()
                for name in b.FILES:
                    (folder / name).write_text('')
            data = b.build(folder, self.root / ('site-' + folder.name))
            self.assertEqual(data['summary']['snapshots'], 0)
            self.assertIsNone(data['summary']['equity_usdt'])
            self.assertEqual(data['equity']['points'], [])
            self.assertEqual(data['inputs']['snapshots.jsonl']['present'], folder.name == 'empty')

    def test_d4_truncated_tail_and_malformed_line(self):
        path = self.monitor / 'snapshots.jsonl'
        lines = path.read_text().splitlines(keepends=True)
        path.write_text(''.join(lines[:2]) + '{not json\n' + ''.join(lines[2:]) + '{"utc": "2026-10-23T00:06')
        data = b.build(self.monitor, self.root / 'site')
        report = data['inputs']['snapshots.jsonl']
        self.assertEqual((report['rows'], report['malformed'], report['truncated_tail']), (6, 1, True))
        self.assertAlmostEqual(data['summary']['equity_usdt'], 94.9, delta=1e-9)

    def test_d4_latest_poll_without_prices(self):
        snaps = SNAPSHOTS + [snapshot(6, 220, 71.5, None, {'NVDAB': 0.125}, realized=-0.5, trades=2, failed=1,
                                      gas=0.0002, price_error='HTTPError')]
        data = b.build(write_monitor(self.root / 'm2', snaps), self.root / 'site')
        s = data['summary']
        self.assertEqual((s['as_of_utc'], s['priced_as_of_utc']), ('2026-10-23T00:06:00Z', '2026-10-23T00:05:00Z'))
        self.assertEqual(s['price_error'], 'HTTPError')
        self.assertAlmostEqual(s['equity_usdt'], 94.9, delta=1e-9)
        self.assertEqual(data['holdings'][0]['value_usdt'], None)
        self.assertEqual(data['holdings'][0]['weight_pct'], None)

    def test_d4_downsampling_keeps_the_trough(self):
        snaps = [snapshot(0, 1, 96.0, 96.0)]
        for i in range(1, 5000):
            equity = 90.0 if i == 2777 else 96.0 + (i % 7) * 0.01
            snaps.append(dict(snapshot(0, i + 1, 96.0, equity), utc='2026-10-%02dT%02d:%02d:00Z' % (
                23 + i // 1440, i // 60 % 24, i % 60)))
        data = b.dashboard_data(write_monitor(self.root / 'long', snaps, [], []))
        self.assertEqual(data['equity']['total'], 5000)
        self.assertLessEqual(len(data['equity']['points']), 4 * b.MAX_BUCKETS + 2)
        self.assertIn(90.0, [pt[1] for pt in data['equity']['points']])
        self.assertAlmostEqual(data['summary']['max_drawdown_pct'], (96.06 - 90) / 96.06 * 100, delta=1e-9)

    def test_d5_no_network_and_reads_only_monitor_files(self):
        (self.monitor / '.env').write_text('BINANCE_SECRET_KEY=never-read\n')
        read, original = [], Path.read_bytes

        def recording(path):
            read.append(Path(path).resolve())
            return original(path)

        def no_socket(*args, **kwargs):
            raise AssertionError('network access')
        with patch.object(Path, 'read_bytes', recording), patch.object(socket, 'socket', no_socket), \
                patch.object(socket, 'create_connection', no_socket):
            b.build(self.monitor, self.root / 'site')
        allowed = {(self.monitor / f).resolve() for f in b.FILES + (b.DECISIONS,)} | {b.TEMPLATE.resolve()}
        self.assertTrue(read)
        self.assertLessEqual(set(read), allowed)


class PublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, GIT_ENV)
        self.env.start()
        self.monitor = write_monitor(self.root / 'monitor')
        self.remote = self.root / 'pages.git'
        self.run_git('init', '--quiet', '--bare', '--initial-branch=main', str(self.remote))
        self.clone = self.root / 'clone'
        self.calls = []
        real = p.git

        def recording(*args, **kwargs):
            self.calls.append(args)
            return real(*args, **kwargs)
        self.recorder = patch.object(p, 'git', recording)
        self.recorder.start()

    def tearDown(self):
        self.recorder.stop()
        self.env.stop()
        self.tmp.cleanup()

    def run_git(self, *args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd or self.root, capture_output=True, text=True, check=True).stdout.strip()

    def publish(self):
        return p.publish_once(self.monitor, 'team/larp-dashboard', clone=self.clone, remote_url=str(self.remote))

    def head(self):
        return self.run_git('rev-parse', 'refs/heads/gh-pages', cwd=self.remote)

    def test_d6_first_publish_then_only_on_change(self):
        first = self.publish()
        self.assertTrue(first['changed'])
        self.assertEqual(first['commit'], self.head())
        files = self.run_git('ls-tree', '--name-only', 'gh-pages', cwd=self.remote).split('\n')
        self.assertEqual(sorted(files), sorted(b.OUTPUTS))
        again = self.publish()
        self.assertFalse(again['changed'])
        self.assertEqual(self.head(), first['commit'])
        self.assertEqual(self.run_git('rev-list', '--count', 'gh-pages', cwd=self.remote), '1')
        write_monitor(self.monitor, SNAPSHOTS + [snapshot(6, 220, 71.5, 95.2, {'NVDAB': 0.125}, {'NVDAB': 23.7},
                                                          realized=-0.5, unrealized=-0.3, trades=2, failed=1)])
        third = self.publish()
        self.assertTrue(third['changed'])
        self.assertEqual(self.run_git('rev-parse', 'gh-pages^', cwd=self.remote), first['commit'])  # fast-forward
        self.assertEqual(self.run_git('rev-list', '--count', 'gh-pages', cwd=self.remote), '2')
        for call in self.calls:
            self.assertFalse({'--force', '-f', '--force-with-lease', '--mirror'} & set(call), call)
            self.assertFalse(any(a.startswith(('+', '--force')) for a in call if isinstance(a, str)), call)

    def test_d6_keeps_other_files_on_the_branch(self):
        self.publish()
        other = self.root / 'other'
        self.run_git('clone', '--quiet', '--branch', 'gh-pages', str(self.remote), str(other))
        (other / 'CNAME').write_text('dashboard.example.invalid\n')
        self.run_git('add', 'CNAME', cwd=other)
        self.run_git('commit', '--quiet', '-m', 'add CNAME', cwd=other)
        self.run_git('push', '--quiet', 'origin', 'gh-pages', cwd=other)
        write_monitor(self.monitor, SNAPSHOTS[:-1])
        self.assertTrue(self.publish()['changed'])
        self.assertIn('CNAME', self.run_git('ls-tree', '--name-only', 'gh-pages', cwd=self.remote).split('\n'))

    def test_d6_diverged_remote_stops_without_writing(self):
        self.publish()
        other = self.root / 'other'
        self.run_git('clone', '--quiet', '--branch', 'gh-pages', str(self.remote), str(other))
        (other / 'index.html').write_text('someone else\n')
        self.run_git('commit', '--quiet', '-am', 'remote change', cwd=other)
        self.run_git('push', '--quiet', 'origin', 'gh-pages', cwd=other)
        remote_head = self.head()
        (self.clone / 'data.json').write_text('{}\n')  # a local commit whose push never happened
        self.run_git('commit', '--quiet', '-am', 'unpushed', cwd=self.clone)
        with self.assertRaisesRegex(p.PublishError, 'diverged'):
            self.publish()
        self.assertEqual(self.head(), remote_head)
        self.assertEqual((self.clone / 'data.json').read_text(), '{}\n')

    def test_d6_retries_a_failed_push(self):
        self.publish()
        write_monitor(self.monitor, SNAPSHOTS[:-1])
        real = p.git

        def push_fails(*args, **kwargs):
            if args[0] == 'push':
                raise p.PublishError('git push failed: network')
            return real(*args, **kwargs)
        before = self.head()
        with patch.object(p, 'git', push_fails), self.assertRaises(p.PublishError):
            self.publish()
        self.assertEqual(self.head(), before)
        out = self.publish()  # nothing new to commit, but the earlier commit is still unpushed
        self.assertFalse(out['changed'])
        self.assertNotEqual(self.head(), before)
        self.assertEqual(self.run_git('rev-parse', 'HEAD', cwd=self.clone), self.head())

    def test_d6_refuses_the_main_repository(self):
        origin = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=p.ROOT, capture_output=True, text=True)
        main = p.slug(origin.stdout.strip())
        if not main:
            self.skipTest('this checkout has no GitHub origin to compare against')
        with self.assertRaisesRegex(p.PublishError, 'private main repository'):
            p.publish_once(self.monitor, main, clone=self.clone)
        with self.assertRaisesRegex(p.PublishError, 'private main repository'):
            p.publish_once(self.monitor, 'team/other', clone=self.clone, remote_url='git@github.com:%s.git' % main)
        self.assertFalse(self.clone.exists())

    def test_d6_refuses_the_registered_repository_without_a_github_origin(self):
        registered = p.registered_repository()
        self.assertEqual(registered, 'binance-hackathon-glasswing/binance-hackathon')
        real = p.git

        def proxied_origin(*args, **kwargs):
            if args[:3] == ('remote', 'get-url', 'origin') and kwargs.get('cwd') == p.ROOT:
                return subprocess.CompletedProcess(args, 0, 'http://127.0.0.1:9/git/mirror/larp\n', '')
            return real(*args, **kwargs)
        with patch.object(p, 'git', proxied_origin):
            for repo, url in ((registered, None), ('team/other', 'https://github.com/%s.git' % registered),
                              ('team/other', 'git@github.com:%s' % registered.upper())):
                with self.assertRaisesRegex(p.PublishError, 'private main repository'):
                    p.publish_once(self.monitor, repo, clone=self.clone, remote_url=url)
        self.assertFalse(self.clone.exists())

    def test_rejects_bad_names(self):
        for repo, branch in (('no-slash', 'gh-pages'), ('a/b c', 'gh-pages'), ('a/b', '../main'), ('a/b', '-x')):
            with self.assertRaises(p.PublishError):
                p.publish_once(self.monitor, repo, branch=branch, clone=self.clone, remote_url=str(self.remote))

    def test_pages_url(self):
        self.assertEqual(p.pages_url('Team-X/larp-dashboard'), 'https://team-x.github.io/larp-dashboard/')
        self.assertEqual(p.pages_url('team/team.github.io'), 'https://team.github.io/')


if __name__ == '__main__':
    unittest.main()

"""IDEA-092 A1, A2 (handler), A5, A6: the AWS dashboard refresh, offline. Fake S3, SSM and chain monitor; no AWS."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tests.test_dashboard_decisions import events, load_export
from tools.dashboard import refresh
from tools.dashboard.aws import handler, package

ENV = dict(BUCKET='bucket', PRIMARY_INSTANCE_ID='i-0123456789abcdef0', DECISIONS_DOCUMENT='larp-dashboard-decisions',
           TX_DOCUMENT='larp-dashboard-tx', WALLET='0x' + 'AB' * 20, START_NONCE='4', START_USDT='96')
TX = '0x' + 'cd' * 32


class Missing(Exception):
    response = {'Error': {'Code': '404'}}


class S3:
    def __init__(self):
        self.objects, self.uploads = {}, []

    def download_file(self, bucket, key, filename):
        if key not in self.objects:
            raise Missing(key)
        Path(filename).write_bytes(self.objects[key])

    def upload_file(self, filename, bucket, key, ExtraArgs=None):
        self.objects[key] = Path(filename).read_bytes()
        self.uploads.append((key, ExtraArgs))


class SSM:
    class exceptions:
        InvocationDoesNotExist = KeyError

    def __init__(self):
        self.sent = []

    def send_command(self, **kwargs):
        self.sent.append(kwargs)
        return {'Command': {'CommandId': 'cmd-%d' % len(self.sent)}}

    def get_command_invocation(self, CommandId, InstanceId):
        sent = self.sent[int(CommandId.split('-')[1]) - 1]
        if sent['DocumentName'] == ENV['DECISIONS_DOCUMENT']:
            limit = int(sent['Parameters']['limit'][0])
            out = '\n'.join(load_export()['emit'](events(), limit, 'run'))
        else:
            out = json.dumps(dict(section='tx', tx_hash=TX)) + '\n' + json.dumps(dict(section='tx_summary', hashes=1))
        return {'Status': 'Success', 'StandardOutputContent': out}


class Monitor:
    """Stands in for the RC7 chain monitor: one transaction on the first poll, then a snapshot per poll."""
    fail = False

    def __init__(self, folder):
        self.OUT, self.WALLET, self.START = Path(folder), '0x' + '00' * 20, dict(nonce=0)
        self.seeds = None

    def load_state(self):
        p = self.OUT / 'state.json'
        return json.loads(p.read_text()) if p.exists() else dict(nonce=self.START['nonce'], block=None, trades=0)

    def rpc(self, method, params, batch=None):
        if batch:
            return [dict(blockNumber=hex(129462303)) if m == 'eth_getTransactionReceipt' else
                    dict(transactions=[dict(nonce=hex(4), **{'from': self.WALLET})]) for m, _ in batch]
        if method == 'eth_getTransactionCount':
            return hex(5)
        return None

    def wallet_txs(self, start, end):
        raise AssertionError('full block scan')

    def balances(self, tag):
        return {}, {}

    def poll(self, state):
        if Monitor.fail:
            raise RuntimeError('balance read refused')
        if state['block'] is None:  # the nonce moved: find the transactions the way the real monitor does
            self.balances('finalized')
            assert [int(t['nonce'], 16) for t in self.wallet_txs(129462000, 129462403)] == [4]
            with (self.OUT / 'transactions.jsonl').open('a') as f:
                f.write(json.dumps(dict(hash=TX, nonce=4, block=129462303, kind='APPROVE', status=1)) + '\n')
        state = dict(state, block=(state['block'] or 129462303) + 100, nonce=5)
        snap = dict(utc='2026-10-24T11:%02d:00Z' % (state['block'] % 60), block=state['block'], nonce=5, usdt=77.0,
                    bnb=0.005, units={}, value_usdt={}, equity_ex_bnb_usdt=95.0, pnl_vs_start_ex_bnb_usdt=-1.0,
                    realized_usdt=0.0, unrealized_usdt=0.0, gas_spent_bnb=0.0, trades=0, failed_txs=0,
                    price_error=None, alerts=0)
        with (self.OUT / 'snapshots.jsonl').open('a') as f:
            f.write(json.dumps(snap, sort_keys=True) + '\n')
        (self.OUT / 'state.json').write_text(json.dumps(state))
        return snap, []


class Lambda(unittest.TestCase):
    def setUp(self):
        self.s3, self.ssm = S3(), SSM()
        self.clients = dict(s3=self.s3, ssm=self.ssm, secretsmanager=None)
        self.monitors = []

        def fake_monitor(folder):
            m = Monitor(folder)
            self.monitors.append(m)
            return m
        Monitor.fail = False
        for p in (patch.object(refresh, 'chain_monitor', fake_monitor), patch.object(refresh.time, 'sleep'),
                  patch.object(handler, 'POLL_S', 0)):
            p.start()
            self.addCleanup(p.stop)

    def test_a1_runs_upload_the_page_and_state_and_continue(self):
        first = handler.run(ENV, self.clients)
        self.assertEqual(first['rounds'], 3)
        for key in ('site/index.html', 'site/data.json', 'state/state.json', 'state/snapshots.jsonl',
                    'state/transactions.jsonl', 'state/decisions.jsonl', 'state/refresh-state.json'):
            self.assertIn(key, self.s3.objects)
        for key in ('site/index.html', 'site/data.json'):
            self.assertIsNone(re.search(rb'0x[0-9a-fA-F]{8,}', self.s3.objects[key]), key)
        self.assertEqual(dict(self.s3.uploads)['site/index.html']['CacheControl'], 'no-cache')
        self.assertEqual(json.loads(self.s3.objects['state/refresh-state.json']), dict(blocks=[129462303]))
        # The configured wallet and opening values reached the monitor; PnL is restated against START_USDT.
        self.assertEqual((self.monitors[0].WALLET, self.monitors[0].START['nonce']), (ENV['WALLET'].lower(), 4))
        snap = json.loads(self.s3.objects['state/snapshots.jsonl'].splitlines()[-1])
        self.assertEqual(snap['pnl_vs_start_ex_bnb_usdt'], 95.0 - 96)
        handler.run(ENV, self.clients)  # continues from the stored state: no second transaction, two polls
        self.assertEqual(len(self.s3.objects['state/transactions.jsonl'].splitlines()), 1)
        self.assertEqual(len(self.s3.objects['state/snapshots.jsonl'].splitlines()), 2)

    def test_a1_a_failed_run_uploads_nothing(self):
        handler.run(ENV, self.clients)
        before = dict(self.s3.objects)
        Monitor.fail = True
        with self.assertRaises(RuntimeError):
            handler.run(ENV, self.clients)
        self.assertEqual(self.s3.objects, before)

    def test_a1_without_the_decisions_export_the_trades_still_refresh(self):
        handler.run(ENV, self.clients)
        decided = self.s3.objects['state/decisions.jsonl']

        def refused(**kwargs):
            raise PermissionError('AccessDenied')  # SSM closed for the scored run
        self.ssm.send_command = refused
        summary = handler.run(ENV, self.clients)
        self.assertEqual((summary['export_error'], summary['rounds']), ('PermissionError', 3))
        self.assertEqual(self.s3.objects['state/decisions.jsonl'], decided)  # the last decisions are kept
        self.assertEqual(len(self.s3.objects['state/snapshots.jsonl'].splitlines()), 2)  # the trades refreshed

    def test_a2_only_the_two_documents_run_and_only_on_the_primary(self):
        handler.run(ENV, self.clients)
        handler.run(ENV, self.clients)
        self.assertEqual({s['DocumentName'] for s in self.ssm.sent}, {ENV['DECISIONS_DOCUMENT'], ENV['TX_DOCUMENT']})
        self.assertEqual({tuple(s['InstanceIds']) for s in self.ssm.sent}, {(ENV['PRIMARY_INSTANCE_ID'],)})
        self.assertNotIn('AWS-RunShellScript', json.dumps(self.ssm.sent))
        self.assertEqual([s['DocumentName'] for s in self.ssm.sent].count(ENV['TX_DOCUMENT']), 1)  # seeding, once
        runner = handler.document_runner(self.ssm, ENV['PRIMARY_INSTANCE_ID'], {'decisions-export.sh': 'd'})
        with self.assertRaises(PermissionError):
            runner(Path('anything-else.sh'))


class Package(unittest.TestCase):
    def test_a5_the_package_is_deterministic_minimal_and_importable(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.zip', Path(tmp) / 'b.zip'
            self.assertEqual(package.package(a), package.package(b))
            self.assertEqual(hashlib.sha256(a.read_bytes()).hexdigest(), hashlib.sha256(b.read_bytes()).hexdigest())
            names = zipfile.ZipFile(a).namelist()
            self.assertEqual(sorted(names), sorted(package.FILES + package.MARKERS))
            self.assertFalse([n for n in names if re.search(r'(^|/)(\.env|tests?/)|key|secret', n)])
            root = Path(tmp) / 'task'
            zipfile.ZipFile(a).extractall(root)
            probe = ('import importlib.util, sys; sys.path.insert(0, sys.argv[1]);'
                     'import tools.dashboard.aws.handler as h;'
                     'from tools.dashboard import refresh;'
                     'spec = importlib.util.spec_from_file_location("m", refresh.MONITOR);'
                     'm = importlib.util.module_from_spec(spec); spec.loader.exec_module(m);'
                     'print(m.ROOT == refresh.ROOT, h.lambda_handler.__name__)')
            out = subprocess.run([sys.executable, '-I', '-c', probe, str(root)], capture_output=True, text=True,
                                 cwd=tmp)
            self.assertEqual(out.stdout.split(), ['True', 'lambda_handler'], out.stderr)


@unittest.skipIf(shutil.which('node') is None, 'node is not installed')
class ViewerAuth(unittest.TestCase):
    def test_a6_the_login_function_refuses_wrong_or_missing_credentials(self):
        code = (Path(handler.__file__).with_name('viewer-auth.js')).read_text()
        good = 'dXNlcjpwYXNzd29yZA=='  # base64 of user:password (test only)
        script = r'''
const crypto = require('crypto');
let source = require('fs').readFileSync(0, 'utf8').replace(/^import .*$/mg, '');
const run = (store) => {
  const cf = { kvs: () => ({ get: async (k) => { if (!(k in store)) throw new Error('missing'); return store[k]; } }) };
  return new Function('cf', 'crypto', source + '\nreturn handler;')(cf, crypto);
};
const hash = crypto.createHash('sha256').update(process.argv[1]).digest('hex');
const req = (h) => ({ request: { uri: '/', headers: h === undefined ? {} : { authorization: { value: h } } } });
(async () => {
  const ok = run({ 'basic-auth-sha256': hash });
  const out = [
    (await ok(req('Basic ' + process.argv[1]))).uri === '/',
    (await ok(req())).statusCode,
    (await ok(req('Basic d3Jvbmc6d3Jvbmc='))).statusCode,
    (await ok(req('Bearer ' + process.argv[1]))).statusCode,
    (await run({})(req('Basic ' + process.argv[1]))).statusCode,
    (await run({ 'basic-auth-sha256': '' })(req('Basic ' + process.argv[1]))).statusCode,
  ];
  console.log(JSON.stringify(out));
})();
'''
        out = subprocess.run(['node', '-e', script, good], input=code, capture_output=True, text=True)
        self.assertEqual(json.loads(out.stdout), [True, 401, 401, 401, 401, 401], out.stderr)


if __name__ == '__main__':
    unittest.main()

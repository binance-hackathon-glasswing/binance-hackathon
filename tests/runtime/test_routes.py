"""IDEA-062 R1-R8: approved network destinations and the read-only route check per host role (#32)."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
REGION = 'ap-southeast-2'
DB = 'larp-dev.abc123.ap-southeast-2.rds.amazonaws.com'
BALANCE_RPC = 'https://balance-rpc.example/v1/BALANCESECRET?apikey=QUERYSECRET'
BACKUP_RPC = 'https://balance-rpc-backup.example/v1/BACKUPSECRET'
CHAIN_RPC = 'https://chain-rpc.example/v2/CHAINSECRET'
EXAMPLES = {
    'runtime': 'config/runtime/runtime.example.json',
    'execution': 'config/hosts/execution.example.json',
    'uploader': 'config/hosts/uploader.example.json',
    'operations': 'config/runtime/operations.example.json',
    'runtime_aiand': 'config/runtime/runtime.aiand-shadow.example.json',
    'signer': 'config/hosts/signer.example.json',
}
PRIMARY = ('runtime', 'execution', 'uploader', 'operations')


def load(name):
    return json.loads((ROOT / EXAMPLES[name]).read_text(encoding='utf-8'))


def configs(names=PRIMARY):
    out = {}
    for name in names:
        c = load(name)
        c['database_host'], c['region'] = DB, REGION
        out[name] = c
    if 'runtime' in out:  # the ordered balance RPC providers (IDEA-055 PR 5)
        out['runtime']['driver']['balance_rpc_providers'] = [dict(url=BALANCE_RPC, source_id='balance-rpc'),
                                                             dict(url=BACKUP_RPC, source_id='balance-rpc-backup')]
    if 'execution' in out:
        out['execution']['rpc_url'], out['execution']['rpc_source_id'] = CHAIN_RPC, 'chain-rpc'
    return out


def sources():
    return json.loads((ROOT / 'config/sources/sources.v1.json').read_text(encoding='utf-8'))


def by_endpoint(plan):
    return {(d['host'], d['port']): d for d in plan['destinations']}


def host(url):
    return urlsplit(url).hostname


class Plans(unittest.TestCase):
    def test_r1_primary_destinations_come_from_configs_sources_and_client_constants(self):
        from larp.runtime import routes
        from larp.audit.delivery import BASE_URL
        from larp.intelligence.edgar import ARCHIVES, SUBMISSIONS
        from larp.marketdata.web3 import BASE
        plan = routes.plan('primary', configs(), sources())
        got = {k: (set(d['units']), d['expect'], d['tls']) for k, d in by_endpoint(plan).items()}
        evidence = {'larp-evidence'}
        expected = {
            (host(BASE), 443): ({'larp-runtime', 'larp-execution'}, 'REACHABLE', True),
            ('balance-rpc.example', 443): ({'larp-runtime'}, 'REACHABLE', True),
            ('balance-rpc-backup.example', 443): ({'larp-runtime'}, 'REACHABLE', True),  # IDEA-055 PR 5
            ('chain-rpc.example', 443): ({'larp-execution'}, 'REACHABLE', True),
            (host(BASE_URL), 443): ({'larp-uploader'}, 'REACHABLE', True),
            (f'secretsmanager.{REGION}.amazonaws.com', 443):
                ({'larp-runtime', 'larp-execution', 'larp-uploader'}, 'REACHABLE', True),
            (f'monitoring.{REGION}.amazonaws.com', 443): ({'larp-archive'}, 'REACHABLE', True),
            (f's3.{REGION}.amazonaws.com', 443): ({'larp-archive'}, 'REACHABLE', True),
            (DB, 5432): ({'larp-runtime', 'larp-execution', 'larp-uploader', 'larp-archive'}, 'REACHABLE', False),
            (host(SUBMISSIONS), 443): (evidence, 'REACHABLE', True),
        }
        expected[(host(ARCHIVES), 443)] = (evidence, 'REACHABLE', True)
        for s in sources()['sources']:
            if s['enabled']:
                for h in [host(s['listing_url'])] + [a['host'] for a in s['allow']]:
                    expected[(h, 443)] = (evidence, 'REACHABLE', True)
        self.assertEqual(got, expected)
        self.assertEqual(host(BASE), 'web3.binance.com')
        self.assertEqual(host(BASE_URL), 'api.commonservice.io')
        self.assertEqual({host(SUBMISSIONS), host(ARCHIVES)}, {'data.sec.gov', 'www.sec.gov'})
        for h in ('www.federalregister.gov', 'www.justice.gov', 'ec.europa.eu'):
            self.assertIn((h, 443), got)
        self.assertNotIn(('www.ftc.gov', 443), got)
        self.assertEqual(plan['not_checked'], [])

    def test_sg2_aiand_shadow_runtime_adds_the_model_hosts(self):
        from larp.runtime import routes
        from larp.intelligence.aiand import ENDPOINT
        from larp.intelligence.providers import OPENAI_ENDPOINT
        cfgs = configs()
        cfgs['runtime'] = dict(cfgs['runtime'], driver=dict(load('runtime_aiand')['driver'],
                               balance_rpc_providers=cfgs['runtime']['driver']['balance_rpc_providers']))
        routed = by_endpoint(routes.plan('primary', cfgs, sources()))
        plain = by_endpoint(routes.plan('primary', configs(), sources()))
        self.assertEqual({host(ENDPOINT), host(OPENAI_ENDPOINT)}, {'api.aiand.com', 'api.openai.com'})
        for h in ('api.aiand.com', 'api.openai.com'):
            d = routed[(h, 443)]
            self.assertEqual((d['units'], d['expect'], d['tls']), (['larp-runtime'], 'REACHABLE', True))
            self.assertNotIn((h, 443), plain)
        self.assertEqual(set(routed) - set(plain), {('api.aiand.com', 443), ('api.openai.com', 443)})
        for plan_ in (routed, plain):
            self.assertNotIn(('api.anthropic.com', 443), plan_)
        signer = routes.plan('signer', configs(('signer',)), sources())
        self.assertNotIn('api.aiand.com', {d['host'] for d in signer['destinations']})

    def test_r2_signer_reaches_only_the_database_and_s3(self):
        from larp.runtime import routes
        plan = routes.plan('signer', configs(('signer',)), sources())
        got = {k: (d['expect'], d['tls']) for k, d in by_endpoint(plan).items()}
        self.assertEqual(got, {
            (DB, 5432): ('REACHABLE', False),
            (f's3.{REGION}.amazonaws.com', 443): ('REACHABLE', True),
            ('web3.binance.com', 443): ('BLOCKED', True),
            ('api.commonservice.io', 443): ('BLOCKED', True),
            ('data.sec.gov', 443): ('BLOCKED', True),
            (f'secretsmanager.{REGION}.amazonaws.com', 443): ('BLOCKED', True),
        })


class FakeProbe:
    def __init__(self, statuses=None, default='OK'):
        self.calls, self.statuses, self.default = [], statuses or {}, default

    def __call__(self, host, port, *, tls, timeout):
        self.calls.append((host, port, tls))
        return self.statuses.get((host, port), self.default)


class Cli(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)

    def write(self, cfgs):
        args = []
        for name, c in cfgs.items():
            path = self.dir / f'{name}.json'
            path.write_text(json.dumps(c), encoding='utf-8')
            args += ['--config', f'{name}={path}']
        return args

    def run_cli(self, role, cfgs, probe, extra=()):
        from larp.runtime import routes
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = routes.main(['--role', role, '--root', str(ROOT)] + self.write(cfgs) + list(extra), probe=probe)
        return code, out.getvalue(), err.getvalue()

    def test_r3_bad_urls_are_refused_before_any_probe(self):
        bad = ['http://balance-rpc.example/', 'https://user:pw@balance-rpc.example/', 'https://balance-rpc.example/#x',
               'https:///nohost', 'https://balance-rpc.example:8545/', 'wss://balance-rpc.example/']
        for url in bad:
            with self.subTest(url=url):
                cfgs = configs()
                cfgs['runtime']['driver']['balance_rpc_providers'][0]['url'] = url
                probe = FakeProbe()
                code, out, err = self.run_cli('primary', cfgs, probe)
                self.assertEqual(code, 2)
                self.assertEqual(probe.calls, [])

    def test_r3_missing_required_config_is_refused(self):
        for role, names, drop in (('primary', PRIMARY, 'runtime'), ('primary', PRIMARY, 'uploader'),
                                  ('primary', PRIMARY, 'operations'), ('signer', ('signer',), 'signer')):
            with self.subTest(role=role, drop=drop):
                cfgs = configs(names)
                del cfgs[drop]
                probe = FakeProbe()
                code, _, _ = self.run_cli(role, cfgs, probe)
                self.assertEqual(code, 2)
                self.assertEqual(probe.calls, [])

    def test_r3_unset_destination_fails_and_missing_execution_is_listed(self):
        cfgs = configs()
        cfgs['runtime']['driver']['balance_rpc_providers'][0]['url'] = None
        del cfgs['execution']
        report = self.dir / 'report.json'
        code, _, _ = self.run_cli('primary', cfgs, FakeProbe(), ['--output', str(report)])
        self.assertEqual(code, 1)
        r = json.loads(report.read_text(encoding='utf-8'))
        unset = [x for x in r['results'] if x['status'] == 'UNSET']
        self.assertEqual(len(unset), 1)
        self.assertEqual(unset[0]['units'], ['larp-runtime'])
        self.assertIsNone(unset[0]['host'])
        self.assertEqual(unset[0]['verdict'], 'FAIL')
        self.assertEqual(r['not_checked'], ['larp-execution'])
        self.assertFalse(r['passed'])

    def test_r4_report_and_output_name_hosts_only(self):
        report = self.dir / 'report.json'
        code, out, err = self.run_cli('primary', configs(), FakeProbe(), ['--output', str(report)])
        self.assertEqual(code, 0)
        text = report.read_text(encoding='utf-8') + out + err
        for secret in ('BALANCESECRET', 'BACKUPSECRET', 'QUERYSECRET', 'CHAINSECRET', 'apikey', '/v1/', '/v2/'):
            self.assertNotIn(secret, text)
        self.assertIn('balance-rpc.example', text)
        code, out, err = self.run_cli('primary', configs(), FakeProbe())
        self.assertEqual(code, 0)
        for secret in ('BALANCESECRET', 'BACKUPSECRET', 'QUERYSECRET', 'CHAINSECRET'):
            self.assertNotIn(secret, out + err)

    def test_r6_primary_passes_only_when_every_destination_is_ok(self):
        self.assertEqual(self.run_cli('primary', configs(), FakeProbe())[0], 0)
        for status in ('DNS_FAILED', 'CONNECT_FAILED', 'TLS_FAILED'):
            with self.subTest(status=status):
                probe = FakeProbe({('api.commonservice.io', 443): status})
                self.assertEqual(self.run_cli('primary', configs(), probe)[0], 1)

    def test_r6_signer_fails_on_any_unexpected_route(self):
        blocked = {('web3.binance.com', 443): 'CONNECT_FAILED', ('api.commonservice.io', 443): 'CONNECT_FAILED',
                   ('data.sec.gov', 443): 'DNS_FAILED',
                   (f'secretsmanager.{REGION}.amazonaws.com', 443): 'CONNECT_FAILED'}
        report = self.dir / 'ok.json'
        code, _, _ = self.run_cli('signer', configs(('signer',)), FakeProbe(blocked), ['--output', str(report)])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(report.read_text(encoding='utf-8'))['passed'])
        for status in ('OK', 'TLS_FAILED'):
            with self.subTest(status=status):
                statuses = dict(blocked)
                statuses[('web3.binance.com', 443)] = status
                report = self.dir / f'bad-{status}.json'
                code, _, _ = self.run_cli('signer', configs(('signer',)), FakeProbe(statuses),
                                          ['--output', str(report)])
                self.assertEqual(code, 1)
                r = json.loads(report.read_text(encoding='utf-8'))
                web3 = [x for x in r['results'] if x['host'] == 'web3.binance.com'][0]
                self.assertEqual(web3['verdict'], 'UNEXPECTED_ROUTE')
        statuses = dict(blocked)
        statuses[(DB, 5432)] = 'CONNECT_FAILED'
        self.assertEqual(self.run_cli('signer', configs(('signer',)), FakeProbe(statuses))[0], 1)

    def test_r7_report_shape_and_exclusive_output(self):
        import hashlib
        cfgs = configs()
        report = self.dir / 'report.json'
        code, _, _ = self.run_cli('primary', cfgs, FakeProbe(), ['--output', str(report)])
        self.assertEqual(code, 0)
        r = json.loads(report.read_text(encoding='utf-8'))
        self.assertEqual(r['schema'], 'RouteCheck.v1')
        self.assertEqual(r['role'], 'primary')
        self.assertTrue(r['passed'])
        self.assertRegex(r['checked_at'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
        for name in PRIMARY:
            self.assertEqual(r['config_sha256'][name],
                             hashlib.sha256((self.dir / f'{name}.json').read_bytes()).hexdigest())
        self.assertEqual(r['sources_sha256'],
                         hashlib.sha256((ROOT / 'config/sources/sources.v1.json').read_bytes()).hexdigest())
        self.assertTrue(all(x['verdict'] == 'PASS' for x in r['results']))
        before = report.read_bytes()
        code, _, _ = self.run_cli('primary', cfgs, FakeProbe(), ['--output', str(report)])
        self.assertEqual(code, 2)
        self.assertEqual(report.read_bytes(), before)

    def test_nc1_dns_failure_never_proves_signer_isolation(self):
        from larp.runtime.routes import verdict
        self.assertEqual(verdict('BLOCKED', 'DNS_FAILED'), 'INCONCLUSIVE')
        self.assertEqual(verdict('BLOCKED', 'UNKNOWN_STATUS'), 'FAIL')
        blocked = {('web3.binance.com', 443): 'CONNECT_FAILED',
                   ('api.commonservice.io', 443): 'CONNECT_FAILED',
                   ('data.sec.gov', 443): 'DNS_FAILED',
                   (f'secretsmanager.{REGION}.amazonaws.com', 443): 'CONNECT_FAILED'}
        report = self.dir / 'dns-inconclusive.json'
        code, _, _ = self.run_cli('signer', configs(('signer',)), FakeProbe(blocked),
                                  ['--output', str(report)])
        self.assertEqual(code, 1)
        result = json.loads(report.read_bytes())
        self.assertFalse(result['passed'])
        dns = next(row for row in result['results'] if row['host'] == 'data.sec.gov')
        self.assertEqual(dns['verdict'], 'INCONCLUSIVE')


class Listener:
    """A local TCP listener that records every byte it receives; `reply` is sent once on accept."""

    def __init__(self, reply=b'', tls_context=None):
        self.sock = socket.socket()
        self.sock.bind(('127.0.0.1', 0))
        self.sock.listen(1)
        self.sock.settimeout(5)
        self.port, self.received, self.reply, self.tls = self.sock.getsockname()[1], bytearray(), reply, tls_context
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        try:
            conn, _ = self.sock.accept()
        except OSError:
            return
        conn.settimeout(2)
        try:
            if self.tls is not None:
                try:
                    conn = self.tls.wrap_socket(conn, server_side=True)
                except (ssl.SSLError, OSError):
                    return
            if self.reply:
                conn.sendall(self.reply)
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                self.received.extend(chunk)
        except (OSError, ssl.SSLError):
            pass
        finally:
            conn.close()

    def close(self):
        self.thread.join(5)
        self.sock.close()


class Probe(unittest.TestCase):
    def test_r5_dns_connect_and_non_tls_failures(self):
        from larp.runtime.routes import probe
        self.assertEqual(probe('route-check.invalid', 443, tls=True, timeout=2), 'DNS_FAILED')
        s = socket.socket()
        s.bind(('127.0.0.1', 0))
        closed = s.getsockname()[1]
        s.close()
        self.assertEqual(probe('127.0.0.1', closed, tls=True, timeout=2), 'CONNECT_FAILED')
        listener = Listener(reply=b'not tls at all\r\n')
        self.assertEqual(probe('127.0.0.1', listener.port, tls=True, timeout=2), 'TLS_FAILED')
        listener.close()
        self.assertTrue(listener.received, 'the TLS probe sends a ClientHello')
        self.assertEqual(listener.received[0], 0x16)
        for line in (b'GET ', b'POST ', b'PUT ', b'HTTP/'):
            self.assertNotIn(line, bytes(listener.received))

    def test_r5_tcp_probe_sends_nothing(self):
        from larp.runtime.routes import probe
        listener = Listener()
        self.assertEqual(probe('127.0.0.1', listener.port, tls=False, timeout=2), 'OK')
        listener.close()
        self.assertEqual(bytes(listener.received), b'')

    @unittest.skipUnless(shutil.which('openssl'), 'openssl is needed to make a local test certificate')
    def test_r5_tls_handshake_verifies_the_certificate(self):
        from larp.runtime.routes import probe
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=localhost',
                        '-addext', 'subjectAltName=DNS:localhost', '-keyout', str(d / 'key.pem'),
                        '-out', str(d / 'cert.pem')], check=True, capture_output=True)
        server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server.load_cert_chain(d / 'cert.pem', d / 'key.pem')
        untrusted = Listener(tls_context=server)
        self.assertEqual(probe('localhost', untrusted.port, tls=True, timeout=3), 'TLS_FAILED')
        untrusted.close()
        trusted = Listener(tls_context=server)
        self.assertEqual(probe('localhost', trusted.port, tls=True, timeout=3, cafile=str(d / 'cert.pem')), 'OK')
        trusted.close()
        self.assertEqual(bytes(trusted.received), b'', 'no application data after the handshake')


class Shipping(unittest.TestCase):
    def test_r8_module_ships_in_the_release(self):
        from larp.runtime.preflight import release_files
        self.assertIn('larp/runtime/routes.py', release_files(ROOT))

    def test_r8_every_fixed_destination_is_in_the_approved_table(self):
        from larp.runtime import routes
        doc = (ROOT / 'docs/build/architecture-deployment.md').read_text(encoding='utf-8')
        self.assertIn('## Approved network destinations', doc)
        section = doc.split('## Approved network destinations', 1)[1].split('\n## ', 1)[0]
        account_specific = {DB, 'balance-rpc.example', 'balance-rpc-backup.example', 'chain-rpc.example'}
        hosts = set()
        routed = configs()
        routed['runtime'] = dict(routed['runtime'], driver=dict(load('runtime_aiand')['driver'],
                                 balance_rpc_providers=routed['runtime']['driver']['balance_rpc_providers']))
        for role, cfgs in (('primary', configs()), ('primary', routed), ('signer', configs(('signer',)))):
            for d in routes.plan(role, cfgs, sources())['destinations']:
                if d['host'] not in account_specific:
                    hosts.add(d['host'].replace(REGION, '<region>'))
        self.assertTrue(hosts)
        for h in sorted(hosts):
            self.assertIn(f'`{h}`', section, h)
        for field in ('driver.balance_rpc_providers', 'rpc_url', 'database_host'):
            self.assertIn(f'`{field}`', section)
        self.assertIn('api.aiand.com', hosts)
        table = [line for line in section.splitlines() if line.startswith('| ')]
        self.assertFalse([line for line in table if 'api.anthropic.com' in line])  # stays unapproved


if __name__ == '__main__':
    unittest.main()

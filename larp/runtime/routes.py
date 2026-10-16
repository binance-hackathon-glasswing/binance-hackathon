"""Approved network destinations per host role and a read-only route check (IDEA-062, #32).

    python -m larp.runtime.routes --role primary --config runtime=/etc/larp/runtime.json \
        --config execution=/etc/larp/execution.json --config uploader=/etc/larp/uploader.json \
        --config operations=/etc/larp/operations.json --root /opt/larp/current --output <new file>
    python -m larp.runtime.routes --role signer --config signer=/etc/larp/signer.json --root /opt/larp/current

The destinations come from the manifested service configs, the release's `config/sources/sources.v1.json` and the
clients' own endpoint constants, so the check tests what the services would actually call. Each destination gets a
DNS lookup, a TCP connect and, for HTTPS, a certificate-verified TLS handshake. Nothing else is sent: no HTTP
request, no credentials, no round log (never-do #13), no PostgreSQL protocol bytes. The report names host and port
only, because a configured RPC URL can carry an API key in its path or query.

`primary` passes when every destination is reachable. `signer` passes when it reaches the database and the S3
gateway endpoint and every internet destination is refused (IDEA-046 B2); a connection to one is UNEXPECTED_ROUTE.
Exit codes: 0 passed, 1 failed, 2 refused (bad or missing configuration, existing output file).
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import socket
import ssl
import sys
import time
from urllib.parse import urlsplit

from larp.contracts import ContractError

HTTPS, DATABASE = 443, 5432
UNITS = {'runtime': 'larp-runtime', 'execution': 'larp-execution', 'uploader': 'larp-uploader',
         'operations': 'larp-archive', 'signer': 'larp-signer'}
# role -> (required configs, optional configs). Gate A runs `primary` without larp-execution.
ROLES = {'primary': (('runtime', 'uploader', 'operations'), ('execution',)), 'signer': (('signer',), ())}
CONNECTED = {'OK', 'TLS_FAILED'}
HOSTNAME = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*')
REGION = re.compile(r'[a-z]{2}(?:-[a-z]+)+-\d')


def https_host(url, field):
    """The host of an https URL to port 443; the message never repeats the URL (it may carry a key)."""
    refused = ContractError(f'{field} must be an https URL to port 443 with a host and no user, password or fragment')
    if type(url) is not str:
        raise refused
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        raise refused from None
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.fragment or port not in (None, HTTPS)):
        raise refused
    return parsed.hostname.lower()


def fixed_hosts():
    """The hosts the clients call, from their own constants."""
    from larp.audit.delivery import BASE_URL
    from larp.intelligence.edgar import ARCHIVES, SUBMISSIONS
    from larp.marketdata.web3 import BASE
    return dict(web3=https_host(BASE, 'larp.marketdata.web3.BASE'),
                ai_seeds=https_host(BASE_URL, 'larp.audit.delivery.BASE_URL'),
                edgar=[https_host(SUBMISSIONS.split('{')[0], 'larp.intelligence.edgar.SUBMISSIONS'),
                       https_host(ARCHIVES.split('{')[0], 'larp.intelligence.edgar.ARCHIVES')])


class Plan:
    def __init__(self):
        self.entries = {}

    def add(self, host, port, unit, purpose, *, tls=True, expect='REACHABLE', field=None):
        key = (host, port) if host is not None else (None, field, unit)
        entry = self.entries.setdefault(key, dict(host=host, port=port, tls=tls, expect=expect, units=set(),
                                                  purposes=set()))
        if (entry['tls'], entry['expect']) != (tls, expect):
            raise ContractError(f'Conflicting expectations for one destination ({purpose})')
        if unit:
            entry['units'].add(unit)
        entry['purposes'].add(purpose)

    def rows(self):
        rows = [dict(e, units=sorted(e['units']), purposes=sorted(e['purposes'])) for e in self.entries.values()]
        return sorted(rows, key=lambda r: (r['host'] is None, r['host'] or '', r['port'], r['units']))


def _region(config, name):
    value = config.get('region')
    if value is None:
        return None
    if type(value) is not str or not REGION.fullmatch(value):
        raise ContractError(f'{name}.region is not an AWS region name')
    return value


def _database(plan, config, name, unit):
    value = config.get('database_host')
    if value is None:
        plan.add(None, DATABASE, unit, f'database ({name}.database_host unset)', tls=False,
                 field=f'{name}.database_host')
        return
    if type(value) is not str or not HOSTNAME.fullmatch(value):
        raise ContractError(f'{name}.database_host is not a host name')
    plan.add(value.lower(), DATABASE, unit, 'PostgreSQL (IAM token over TLS)', tls=False)


def _aws(plan, config, name, unit, service, purpose, *, expect='REACHABLE'):
    region = _region(config, name)
    if region is None:
        plan.add(None, HTTPS, unit, f'{purpose} ({name}.region unset)', field=f'{name}.region')
    else:
        plan.add(f'{service}.{region}.amazonaws.com', HTTPS, unit, purpose, expect=expect)


def _url(plan, url, field, unit, purpose):
    if url is None:
        plan.add(None, HTTPS, unit, f'{purpose} ({field} unset)', field=field)
    else:
        plan.add(https_host(url, field), HTTPS, unit, purpose)


def _evidence_hosts(sources):
    hosts = set(fixed_hosts()['edgar'])
    for i, url in enumerate((sources.get('edgar') or {}).get('endpoints') or ()):
        hosts.add(https_host(url, f'sources.edgar.endpoints[{i}]'))
    for s in sources.get('sources') or ():
        if s.get('enabled') is not True:
            continue
        sid = s.get('source_id')
        hosts.add(https_host(s.get('listing_url'), f'sources[{sid}].listing_url'))
        for rule in s.get('allow') or ():
            h = rule.get('host')
            if type(h) is not str or not HOSTNAME.fullmatch(h):
                raise ContractError(f'sources[{sid}].allow has an invalid host')
            hosts.add(h.lower())
    return hosts


def plan(role, configs, sources):
    """{'destinations': [...], 'not_checked': [unit, ...]} for a host role; refuses a bad or missing config."""
    if role not in ROLES:
        raise ContractError('role must be primary or signer')
    required, optional = ROLES[role]
    for name in configs:
        if name not in required + optional:
            raise ContractError(f'config {name!r} does not belong to role {role}')
    for name in required:
        if not isinstance(configs.get(name), dict):
            raise ContractError(f'role {role} needs the {name} config')
    fixed, p = fixed_hosts(), Plan()
    if role == 'signer':
        c = configs['signer']
        _database(p, c, 'signer', UNITS['signer'])
        _aws(p, c, 'signer', 'provision.sh', 's3', 'release bundle through the S3 gateway endpoint')
        blocked = 'no internet route from the signer (IDEA-046 B2)'
        for h in (fixed['web3'], fixed['ai_seeds'], fixed['edgar'][0]):
            p.add(h, HTTPS, None, blocked, expect='BLOCKED')
        _aws(p, c, 'signer', None, 'secretsmanager', blocked, expect='BLOCKED')
        return dict(destinations=p.rows(), not_checked=[])
    if 'runtime' in configs:
        c, u = configs['runtime'], UNITS['runtime']
        p.add(fixed['web3'], HTTPS, u, 'Binance Web3 Open API')
        driver = c.get('driver') if isinstance(c.get('driver'), dict) else {}
        listed = driver.get('balance_rpc_providers')
        if listed is None:  # the legacy single provider
            _url(p, driver.get('balance_rpc_url'), 'runtime.driver.balance_rpc_url', u, 'BSC RPC (balance check)')
        elif type(listed) is not list or not listed or any(type(x) is not dict for x in listed):
            raise ContractError('runtime.driver.balance_rpc_providers must be a non-empty list of providers')
        else:  # every provider, primary first (IDEA-055 PR 5)
            for i, provider in enumerate(listed):
                _url(p, provider.get('url'), f'runtime.driver.balance_rpc_providers[{i}].url', u,
                     'BSC RPC (balance check, ' + ('primary' if i == 0 else f'backup {i}') + ')')
        _aws(p, c, 'runtime', u, 'secretsmanager', 'Secrets Manager (runtime secret)')
        _database(p, c, 'runtime', u)
    if 'execution' in configs:
        c, u = configs['execution'], UNITS['execution']
        p.add(fixed['web3'], HTTPS, u, 'Binance Web3 Open API')
        _url(p, c.get('rpc_url'), 'execution.rpc_url', u, 'BSC RPC (chain reads and receipts)')
        _aws(p, c, 'execution', u, 'secretsmanager', 'Secrets Manager (runtime secret)')
        _database(p, c, 'execution', u)
    c, u = configs['uploader'], UNITS['uploader']
    p.add(fixed['ai_seeds'], HTTPS, u, 'ai-seeds event log')
    _aws(p, c, 'uploader', u, 'secretsmanager', 'Secrets Manager (uploader secret)')
    _database(p, c, 'uploader', u)
    c, u = configs['operations'], UNITS['operations']
    _aws(p, c, 'operations', u, 's3', 'archive through the S3 gateway endpoint')
    _aws(p, c, 'operations', u, 'monitoring', 'CloudWatch metrics')
    _database(p, c, 'operations', u)
    for h in sorted(_evidence_hosts(sources)):
        p.add(h, HTTPS, 'larp-evidence', 'evidence source (config/sources/sources.v1.json, EDGAR)')
    return dict(destinations=p.rows(), not_checked=sorted(UNITS[n] for n in optional if n not in configs))


def probe(host, port, *, tls, timeout, cafile=None):
    """DNS, TCP connect and (for TLS) a verified handshake. Sends no application data; returns a status only."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError):
        return 'DNS_FAILED'
    sock = None
    for family, kind, proto, _, address in infos:
        candidate = socket.socket(family, kind, proto)
        candidate.settimeout(timeout)
        try:
            candidate.connect(address)
        except OSError:
            candidate.close()
            continue
        sock = candidate
        break
    if sock is None:
        return 'CONNECT_FAILED'
    try:
        if not tls:
            return 'OK'
        context = ssl.create_default_context(cafile=cafile)
        try:
            context.wrap_socket(sock, server_hostname=host).close()
        except (ssl.SSLError, ssl.CertificateError, OSError):
            return 'TLS_FAILED'
        return 'OK'
    finally:
        sock.close()


def verdict(expect, status):
    if expect == 'BLOCKED':
        return 'UNEXPECTED_ROUTE' if status in CONNECTED else ('FAIL' if status == 'UNSET' else 'PASS')
    return 'PASS' if status == 'OK' else 'FAIL'


def check(role, configs, sources, *, probe=probe, timeout=5.0):
    planned = plan(role, configs, sources)
    results = []
    for d in planned['destinations']:
        status = 'UNSET' if d['host'] is None else probe(d['host'], d['port'], tls=d['tls'], timeout=timeout)
        results.append(dict(d, status=status, verdict=verdict(d['expect'], status)))
    return dict(results=results, not_checked=planned['not_checked'],
                passed=all(r['verdict'] == 'PASS' for r in results))


def _read(path, label):
    try:
        raw = Path(path).read_bytes()
        return raw, json.loads(raw)
    except (OSError, ValueError):
        raise ContractError(f'cannot read {label} as JSON') from None


def main(argv=None, *, probe=probe):
    parser = argparse.ArgumentParser(prog='python -m larp.runtime.routes', description=__doc__.split('\n\n')[0])
    parser.add_argument('--role', required=True, choices=sorted(ROLES))
    parser.add_argument('--config', action='append', default=[], metavar='NAME=PATH')
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[2]), help='release root')
    parser.add_argument('--sources', help='default: <root>/config/sources/sources.v1.json')
    parser.add_argument('--output', help='new file for the report (refuses an existing file); default stdout')
    parser.add_argument('--timeout', type=float, default=5.0)
    args = parser.parse_args(argv)
    try:
        if args.output and Path(args.output).exists():
            raise ContractError('the output file already exists')
        configs, hashes = {}, {}
        for item in args.config:
            name, sep, path = item.partition('=')
            if not sep or not path or name not in UNITS or name in configs:
                raise ContractError('each --config is NAME=PATH, with a known service name given once')
            raw, configs[name] = _read(path, f'the {name} config')
            hashes[name] = hashlib.sha256(raw).hexdigest()
        raw, sources = _read(args.sources or Path(args.root) / 'config/sources/sources.v1.json', 'the sources file')
        report = check(args.role, configs, sources, probe=probe, timeout=args.timeout)
    except ContractError as e:
        print(f'refused: {e}', file=sys.stderr)
        return 2
    report = dict(schema='RouteCheck.v1', role=args.role, checked_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  config_sha256=hashes, sources_sha256=hashlib.sha256(raw).hexdigest(), **report)
    text = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output:
        try:
            with open(args.output, 'x', encoding='utf-8') as f:
                f.write(text)
        except OSError:
            print('refused: cannot create the output file', file=sys.stderr)
            return 2
        for r in report['results']:
            where = f"{r['host']}:{r['port']}" if r['host'] else f"unset:{r['port']}"
            print(f"{r['verdict']:<16} {r['status']:<14} {where} {','.join(r['units'])}")
    else:
        sys.stdout.write(text)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())

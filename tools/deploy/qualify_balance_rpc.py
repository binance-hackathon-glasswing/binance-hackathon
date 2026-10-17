"""Isaac task 1 / #92: read-only qualification of private BSC balance RPC candidates.

Uses the exact production Rpc and Gate A balance capture with the public zero
address. Never reads .env, a wallet key or ai-seeds credentials. No signing,
broadcast, upload, runtime-config change or AWS call. See RPC_QUALIFICATION.md.
"""
import argparse
import http.client
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from larp.contracts import ContractError  # noqa: E402
from larp.execution import Blocked, DependencyUnavailable  # noqa: E402
from larp.execution_live.chain import Rpc  # noqa: E402
from larp.marketdata.web3 import Artifacts, encoded, utc  # noqa: E402
from larp.runtime.gate_a import chain_capture, digest  # noqa: E402
from larp.runtime.routes import https_host  # noqa: E402
from larp.runtime.service import balance_providers  # noqa: E402
from larp.sources.live import Refused, git_state, require_committed  # noqa: E402

PROBE_WALLET = '0x' + '0' * 40
SOURCE_ID = re.compile(r'[A-Z][A-Z0-9_]{2,63}')


class TransportDiagnostics:
    """Observe a fixed error category before Rpc sanitizes it; never keep exception text or retry."""
    def __init__(self, opener):
        self.opener, self.reason, self.http_status = opener, None, None

    def open(self, request, timeout):
        try:
            return self.opener.open(request, timeout=timeout)
        except HTTPError as error:
            self.http_status = error.code
            self.reason = 'HTTP_REDIRECT' if 300 <= error.code < 400 else 'HTTP_REFUSED'
            raise
        except URLError as error:
            self.reason = ('TLS_VERIFICATION_FAILED' if isinstance(error.reason, ssl.SSLCertVerificationError)
                           else 'TRANSPORT_UNAVAILABLE')
            raise
        except (OSError, http.client.HTTPException):
            self.reason = 'TRANSPORT_UNAVAILABLE'
            raise


def providers_from(value):
    if type(value) is not dict or set(value) != {'balance_rpc_providers'}:
        raise ContractError('Expected private ordered provider configuration')
    providers = balance_providers(value)
    if not providers:
        raise ContractError('At least one provider required')
    for row in providers:
        if not SOURCE_ID.fullmatch(row['source_id']):
            raise ContractError('Public source ID required')
        https_host(row['url'], 'RPC')
    return providers


def private_config(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        raise ContractError('Invalid private config file')
    if path.absolute().is_relative_to(ROOT) or path.resolve().is_relative_to(ROOT):
        ignored = subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', str(path.resolve())],
                                 capture_output=True, timeout=10)
        if ignored.returncode != 0:
            raise ContractError('Provider config inside the repository must be ignored')
    return providers_from(json.loads(path.read_bytes()))


def new_output(path):
    path = Path(path)
    if path.absolute().is_relative_to(ROOT) or path.resolve().is_relative_to(ROOT) or path.is_symlink():
        raise ContractError('Probe output must stay outside the repository')
    # Exclusive directory creation: a frozen run cannot be overwritten or mixed with an earlier probe.
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    return path.resolve()


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def probe(providers, output, *, build_id, rpc_factory=Rpc):
    report = dict(schema='BalanceRpcQualification.v1', build_id=build_id, checked_at=utc(),
                  scope='PUBLIC_ZERO_ADDRESS_CAPABILITY_ONLY', signing_enabled=False,
                  round_logs_uploaded=False, providers_adopted=False, hosted_check='NOT_RUN',
                  native_trace='NOT_RUN', uptime_qualified=False, results=[])
    for provider in providers:
        source_id = provider['source_id']
        directory = output / source_id
        artifacts = Artifacts(directory)
        start = time.monotonic()
        status, capture_hash = 'REFUSED', None
        diagnostics = None
        try:
            rpc = rpc_factory(provider['url'], artifacts=artifacts, source_id=source_id)
            diagnostics = TransportDiagnostics(rpc.opener)
            rpc.opener = diagnostics
            capture = chain_capture(rpc, PROBE_WALLET, observed_at=utc())
            raw = encoded(capture) + b'\n'
            write_new(directory / 'chain-capture.json', raw)
            capture_hash = digest(raw)
            status = 'PASS'
        except DependencyUnavailable:
            status = 'UNAVAILABLE'
        except (Blocked, ContractError, KeyError, TypeError, ValueError, AttributeError, OSError):
            status = 'REFUSED'
        # Never reflect endpoint strings, arbitrary response fields or exception messages into the public report.
        hashes = sorted(p.stem for p in directory.glob('*.json') if re.fullmatch('[0-9a-f]{64}', p.stem))
        report['results'].append(dict(source_id=source_id, status=status,
                                      reason=(None if status == 'PASS' else
                                              (diagnostics.reason if diagnostics and diagnostics.reason else
                                               'RPC_OR_EVIDENCE_REFUSED')),
                                      http_status=diagnostics.http_status if diagnostics else None,
                                      elapsed_ms=int((time.monotonic() - start) * 1000),
                                      observation_count=len(hashes), observation_hashes=hashes,
                                      capture_sha256=capture_hash))
    report['all_passed'] = all(r['status'] == 'PASS' for r in report['results'])
    write_new(output / 'report.json', encoded(report) + b'\n')
    return report


def main(argv=None, *, state=None, rpc_factory=Rpc):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True, help='private JSON: balance_rpc_providers array')
    parser.add_argument('--out', type=Path, required=True, help='new directory outside the repository')
    args = parser.parse_args(argv)
    try:
        state = git_state() if state is None else state
        require_committed(state, False)
        providers = private_config(args.config)
        output = new_output(args.out)
        report = probe(providers, output, build_id=state['commit'], rpc_factory=rpc_factory)
        print(json.dumps(report, sort_keys=True))
        return 0 if report['all_passed'] else 1
    except (Refused, ContractError, Blocked, OSError, ValueError, KeyError, TypeError, AttributeError,
            subprocess.SubprocessError):
        print(json.dumps(dict(qualified=False, reason='PROBE_INPUTS_REFUSED', signing_enabled=False)))
        return 4


if __name__ == '__main__':
    raise SystemExit(main())

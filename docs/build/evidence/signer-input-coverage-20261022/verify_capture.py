"""SJ-01: verify the archive in origin/capture without extracting or publishing raw data.

Offline only. The JSON report contains counts, source hashes and missing-input
boundaries, never credentials, URLs, wallet addresses or raw response bodies.
Archive dates remain historical; this is not the live numeric caps reviewer.
"""
import argparse
import base64
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[4]
ARCHIVE = 'captures/LARP-capture-complete-20261020T031658Z.zip'
ARCHIVE_SHA = '2dcb92c67c4e041019aeba759518e1aeb699182a59e4cb5016db2937be6f4755'
PROFILE = 'docs/build/evidence/rehearsal-exit-split-20261021/rehearsal-deterministic.json'
PROFILE_SHA = 'e95d5842d15c07e0e2bb5dab761e6a1730f69aed4af4cfce2596eec68e070250'
TOKENS = {
    '0x02fca66c1d1afb4e2a7884261eb00f63598a7436': 'NVDAB',
    '0x3f53de71c126bdabae20f9cd64848d317f6c3238': 'GOOGLB',
    '0xca750ef65f295bbecd685abf54e82caf297bdb61': 'SKHYB',
    '0x5b1910eaad6450e50f816082aa078c41f10c292f': 'TSLAB',
    '0x80106cb3ead06659a5ad19df39d9b4733863b9b0': 'MSFTB',
}
USDT = '0x55d398326f99059ff775485246999027b3197955'


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True).stdout


def instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def verify():
    checked = datetime.now(timezone.utc)
    raw = git('show', 'origin/capture:' + ARCHIVE)
    archive_sha = hashlib.sha256(raw).hexdigest()
    if archive_sha != ARCHIVE_SHA:
        raise ValueError('Archive identity differs')
    profile_raw = (ROOT / PROFILE).read_bytes()
    if hashlib.sha256(profile_raw).hexdigest() != PROFILE_SHA:
        raise ValueError('Selected profile identity differs')
    profile = json.loads(profile_raw)
    buys, sells, endpoints, schemas = defaultdict(Counter), Counter(), Counter(), Counter()
    requested, rows, response_hashes = [], Counter(), 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC differs')
        names = [n for n in archive.namelist() if not n.startswith('__MACOSX/') and not n.endswith('/')]
        manifest_name = next(n for n in names if n.endswith('/SHA256SUMS'))
        prefix = manifest_name.rsplit('/', 1)[0] + '/'
        manifests = archive.read(manifest_name).decode().splitlines()
        for line in manifests:
            expected, relative = line.split(maxsplit=1)
            relative = relative.lstrip('*')
            if PurePosixPath(relative).is_absolute() or '..' in PurePosixPath(relative).parts:
                raise ValueError('Unsafe payload path')
            if hashlib.sha256(archive.read(prefix + relative)).hexdigest() != expected:
                raise ValueError('Payload checksum differs')
        for name in names:
            if name.endswith('.jsonl'):
                for line in archive.read(name).splitlines():
                    if line.strip():
                        row = json.loads(line)
                        rows[row.get('kind', 'UNKNOWN')] += 1
            if '/artifacts/' not in name or not name.endswith('.json'):
                continue
            record = json.loads(archive.read(name))
            schemas[record.get('schema', 'UNKNOWN')] += 1
            endpoints[record.get('endpoint', 'UNKNOWN')] += 1
            if record.get('response_body_base64') is not None:
                body = base64.b64decode(record['response_body_base64'], validate=True)
                if hashlib.sha256(body).hexdigest() != record['response_sha256']:
                    raise ValueError('Decoded response checksum differs')
                response_hashes += 1
            if record.get('endpoint') != 'aggregator/quote-and-swap':
                continue
            requested.append(instant(record['requested_at']))
            params = record.get('params') or {}
            pay = str(params.get('fromTokenAddress', '')).lower()
            receive = str(params.get('toTokenAddress', '')).lower()
            if pay == USDT and receive in TOKENS:
                buys[TOKENS[receive]][str(params['amount'])] += 1
            elif pay in TOKENS and receive == USDT:
                sells[TOKENS[pay]] += 1
    minimum, cap = profile['minimum_trade_units'] * 10**12, profile['per_trade_cap_units'] * 10**12
    newest = max(requested)
    return dict(
        schema='CaptureSignerCoverageReview.v1', decision_id='IDEA-049-C SJ-01',
        scope='OFFLINE_ARCHIVE_AND_SELECTED_PROFILE_COMPARISON', checked_at=checked.isoformat(),
        canonical_commit=git('rev-parse', 'origin/codex/system-testing-20261012').decode().strip(),
        capture_commit=git('rev-parse', 'origin/capture').decode().strip(),
        archive=dict(path=ARCHIVE, bytes=len(raw), sha256=archive_sha, zip_crc_valid=True,
                     manifest_payload_files_verified=len(manifests), decoded_response_bodies_verified=response_hashes),
        selected_profile=dict(path=PROFILE, sha256=PROFILE_SHA, minimum_buy_raw=str(minimum),
                              maximum_buy_raw=str(cap), exit_reserve_wei=str(profile['exit_gas_reserve_units'])),
        archive_quote_range=dict(first=min(requested).isoformat(), last=newest.isoformat(),
                                 newest_age_seconds=int((checked - newest).total_seconds()), freshness_limit_seconds=300),
        capture_rows=dict(sorted(rows.items())), artifact_schemas=dict(sorted(schemas.items())),
        endpoints=dict(sorted(endpoints.items())),
        stock_quotes={symbol: dict(buy_requested_amount_counts=dict(sorted(buys[symbol].items())),
                                 selected_minimum_buy_matches=buys[symbol][str(minimum)],
                                 selected_maximum_buy_matches=buys[symbol][str(cap)],
                                 sell_requests=sells[symbol]) for symbol in sorted(TOKENS.values())},
        coverage_status='BLOCKED_NOT_CURRENT_LD10_PACKET',
        blockers=['ARCHIVE_PREDATES_SELECTED_PR235_PROFILE', 'QUOTES_OUTSIDE_300_SECOND_REVIEW_WINDOW',
                  'NO_CURRENT_RECONCILED_HOLDINGS_NONCE_ALLOWANCE_RESERVATION_PACKET',
                  'NO_SELECTED_PROFILE_FULL_EXIT_AND_CHILD_QUOTE_PACKET'],
        task_1_complete=False, ready_to_install=False, signing_enabled=False,
        primary_capture_performed=False, numeric_coverage_review_performed=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = verify()
    with args.output.open('x') as stream:
        json.dump(report, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ('coverage_status', 'task_1_complete', 'signing_enabled')}))


if __name__ == '__main__':
    main()

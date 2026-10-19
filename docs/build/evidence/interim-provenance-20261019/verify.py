"""YP-01: verify recovered originals against hash-pinned prefixes of the later export.

Run from repository root: PYTHONPATH=. python <this file>. No network, profiles or writes.
"""
import hashlib
import json
from pathlib import Path

from larp.contracts import ContractError
from larp.marketdata.cost_summary import summarize

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def verify():
    files = {}
    for line in (HERE/'SHA256SUMS').read_text().splitlines():
        expected, name = line.split()
        raw = (HERE/name).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        assert actual == expected, name
        files[name] = dict(bytes=len(raw), sha256=actual)
    summary = json.loads((HERE/'quote-cost-summary.json').read_bytes())
    report = json.loads((HERE/'quote-cost-summary.report.json').read_bytes())
    metadata = json.loads((HERE/'run-metadata.json').read_bytes())
    assert summary['capture_hash'] == report['capture_hash'] == metadata['summary_capture_hash']
    for name, expected in metadata['output_sha256'].items():
        assert files[name]['sha256'] == expected, name
    assert report['coverage'] == metadata['coverage']
    assert (report['parameters']['min_days'], report['parameters']['min_samples'],
            report['parameters']['require_weekend']) == (2, 9, True)
    assert hashlib.sha256((ROOT/'config/runtime/session-calendar.2026.json').read_bytes()).hexdigest() == \
        metadata['parameters']['session_calendar_sha256']

    # Exact byte counts and pre-existing hashes select the original snapshot.
    # No timestamp filtering, row editing, reserialization or replacement capture.
    records, prefixes = [], []
    for item in metadata['files']:
        later = ROOT/'docs/build/evidence/quotes-interim-20261018'/item['name']
        original = later.read_bytes()[:item['bytes']]
        assert len(original) == item['bytes'] and original.endswith(b'\n'), item['name']
        assert hashlib.sha256(original).hexdigest() == item['sha256'], item['name']
        rows = [json.loads(row) for row in original.splitlines()]
        assert len(rows) == item['records'], item['name']
        records.extend(rows)
        prefixes.append(item)
    reproduced, current_report = summarize(records, min_days=2, min_samples=9)
    assert reproduced == summary
    assert current_report['coverage'] == report['coverage']
    assert current_report['symbols'] == report['symbols']
    assert sum(x['fallback_gas_estimates'] for x in report['symbols'].values()) == 860
    try:
        summarize(records)  # final 3-day/10-sample defaults must still refuse
    except ContractError as exc:
        refusal = str(exc)
        assert 'Capture coverage incomplete' in refusal
    else:
        raise AssertionError('Interim records unexpectedly passed final defaults')
    return dict(schema='InterimProvenanceVerification.v1', record_id='YP-01', result='PASS',
                original_files=files, original_capture_prefixes=prefixes,
                capture_hash=summary['capture_hash'], capture_records=len(records),
                summary_reproduction='EXACT_OBJECT_EQUALITY',
                report_coverage_and_symbols='EXACT_OBJECT_EQUALITY',
                raw_api_response_reverification='NOT_RUN', final_defaults='REFUSED',
                final_refusal=refusal, profile_generated=False, profile_approved=False,
                fee_netting='UNVERIFIED', gas='ALL_860_SWAP_ESTIMATES_FALLBACK')


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2, sort_keys=True))

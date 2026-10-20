"""Read-only PR204 diagnostic report from an immutable private trial export.

python -m tools.report_captured_trial --data-dir <final-data> --output-dir <new-private-dir>

No inference, ledger writes or decision replay. Original results and frozen M5
denominators are retained; validated rejected/late usage is reported separately.
Missing stage budgets remain unknown. Outputs contain private identities and
must not be committed or posted. Historical protocol overrides are explicit.
"""
import argparse
import base64
import json
from pathlib import Path
import re

from larp.contracts import Document
from larp.intelligence.bakeoff import metrics
from larp.intelligence.common import IntelligenceError, digest, sha256_hex


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def _inside(root, relative):
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
        raise IntelligenceError('Export path escaped the immutable data directory')
    return path


def _decode(value):
    if type(value) is dict and set(value) == {'bytes'}:
        return base64.b64decode(value['bytes'], validate=True)
    return value


def captured_report(data_dir, *, historical_deadline_ms=None):
    root = Path(data_dir).resolve()
    checksums = _inside(root, 'SHA256SUMS').read_bytes()
    for line in checksums.decode().splitlines():
        expected, name = line.split('  ', 1)
        if sha256_hex(_inside(root, name).read_bytes()) != expected:
            raise IntelligenceError('Immutable export file checksum mismatch')
    backup_raw = _inside(root, 'postgres-backup.json').read_bytes()
    backup = json.loads(backup_raw)
    if sha256_hex(_canonical(backup['tables'])) != backup['sha256']:
        raise IntelligenceError('Backup table checksum mismatch')
    table = backup['tables']['events']
    events = [dict(zip(table['columns'], map(_decode, row))) for row in table['rows']]
    records, head = [], '0'*64
    for sequence, row in enumerate(sorted(events, key=lambda event: event['sequence']), 1):
        raw = row['batch']; batch = json.loads(raw)
        batch_hash = sha256_hex(raw)
        if (row['sequence'] != sequence or row['previous_hash'] != head or
                row['batch_hash'] != batch_hash or row['event_hash'] != sha256_hex(_canonical(batch['event']))):
            raise IntelligenceError('Captured event chain mismatch')
        head = sha256_hex(bytes.fromhex(head) + bytes.fromhex(batch_hash))
        if row['head'] != head:
            raise IntelligenceError('Captured event head mismatch')
        record = (batch.get('event') or {}).get('record') or {}
        if record.get('assessment'):
            records.append(record)

    def artifact(ref):
        if type(ref) is not str or not re.fullmatch('[0-9a-f]{64}', ref):
            raise IntelligenceError('Invalid artifact reference')
        for folder in ('source-artifacts', 'market/model'):
            path = root / folder / ref[:2] / ref
            if path.exists():
                raw = _inside(root, path.relative_to(root)).read_bytes()
                if sha256_hex(raw) != ref:
                    raise IntelligenceError('Captured artifact hash mismatch')
                return raw
        return None

    results, requests, identities = [], [], []
    for record in records:
        result, request = record['assessment'], record['request']
        for field in ('job_id', 'issuer_id', 'context_hash', 'cutoff_ms'):
            if result[field] != request[field]:
                raise IntelligenceError('Captured assessment/request identity mismatch')
        original = dict(result); result_id = original.pop('result_id')
        if result_id != 'res:' + digest('larp.intel.result.v1', original):
            raise IntelligenceError('Captured result identity mismatch')
        results.append(result); requests.append(request)
        identities.append(dict(job_id=result['job_id'], result_id=result_id,
            request_sha256=sha256_hex(Document.from_dict(request).payload),
            config_sha256=result.get('config_sha256'), prompt_hash=result.get('prompt_hash'),
            model_hash=result.get('model_hash'), sources=request['evidence_refs'],
            stages=result.get('routing', {}).get('stages', [])))
    statistics = metrics(results, requests=requests, artifact_reader=artifact,
                         historical_deadline_ms=historical_deadline_ms)
    source = Path(__file__).resolve().parents[1]
    return dict(schema='CapturedTrialDiagnostics.v1', export_checksums_sha256=sha256_hex(checksums),
        reporter_source_sha256={name: sha256_hex((source/name).read_bytes()) for name in (
            'tools/report_captured_trial.py', 'larp/intelligence/bakeoff.py', 'larp/intelligence/providers.py')},
        backup_sha256=sha256_hex(backup_raw), event_head=head, event_count=len(events),
        identities=identities,
        metrics=statistics,
        reporting=dict(historical_deadline_ms=historical_deadline_ms,
            missing_stage_budgets='UNKNOWN', frozen_m5_denominator='UNCHANGED',
            decisions='ORIGINAL_RESULTS_ONLY', accounting='READ_ONLY_NO_REFUNDS',
            labels='NOT_SUPPLIED', profitability='NOT_ESTABLISHED'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--historical-deadline-ms', type=int)
    args = parser.parse_args(argv)
    root, output = Path(args.data_dir).resolve(), Path(args.output_dir).resolve()
    if output.is_relative_to(root) or root.is_relative_to(output):
        parser.error('Output must be separate from the immutable input directory')
    report = captured_report(root, historical_deadline_ms=args.historical_deadline_ms)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    (output / 'diagnostics.json').write_bytes(_canonical(report) + b'\n')
    (output / 'diagnostics.json').chmod(0o600)
    print('Private diagnostic report written; original evidence and ledger unchanged.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""RG4 anchor harness (REHEARSAL_GATES_20261019.md RG4; IDEA-036 criteria 3, 5; IDEA-042 LD21-H).

Read-only. Verifies `Anchor.v2` documents read back from the write-once archive against the run's journal with the
production `larp.runtime.maintenance.verify_anchors`, inside READ ONLY transactions, and reports hourly slot
coverage. The operator downloads the anchor objects first (for example `aws s3 cp --recursive` from the archive
prefix into a private directory); this harness never contacts the archive and never writes.

    python tools/deploy/drill_verify_anchors.py --config /etc/larp/operations.json --anchors-dir DIR [--run RUN]

Exit 0: every anchor matches the journal. 1: a mismatch or stale restore (IntegrityError). 3: no anchors found.
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drill_wallet_switch import read_only  # noqa: E402  (same directory; READ ONLY copy of the store)

from larp.runtime.maintenance import HOUR_MS, verify_anchors  # noqa: E402
from larp.storage.postgres import IntegrityError  # noqa: E402


def load_anchors(directory, run_id):
    """Anchor.v2 documents of `run_id` under `directory` (recursive), and how many other files were skipped."""
    anchors, skipped = [], 0
    for path in sorted(Path(directory).rglob('*')):
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_bytes())
        except ValueError:
            skipped += 1
            continue
        if type(value) is dict and value.get('schema') == 'Anchor.v2' and value.get('run_id') == run_id:
            anchors.append(value)
        else:
            skipped += 1
    return anchors, skipped


def coverage(anchors):
    """Hourly slots present, the span they cover and every missing hourly slot inside it."""
    slots = sorted({a['slot_ms'] for a in anchors})
    if not slots:
        return dict(slots=0, hours_spanned=0, missing_slots=[])
    expected = range(slots[0], slots[-1] + HOUR_MS, HOUR_MS)
    return dict(slots=len(slots), first_slot_ms=slots[0], last_slot_ms=slots[-1],
                hours_spanned=(slots[-1] - slots[0]) // HOUR_MS + 1,
                missing_slots=[s for s in expected if s not in set(slots)])


def check(store, run_id, directory):
    anchors, skipped = load_anchors(directory, run_id)
    report = dict(schema='AnchorDrill.v1', run_id=run_id, anchors=len(anchors), skipped_files=skipped,
                  **coverage(anchors))
    if not anchors:
        return dict(report, status='NO_ANCHORS'), 3
    try:
        result = verify_anchors(read_only(store), run_id, anchors)
    except IntegrityError as error:
        return dict(report, status='FAIL', reason=str(error)), 1
    return dict(report, status='PASS', journal_head=result['head'], latest_sequence=result['latest_sequence']), 0


def _store(config):
    from larp.runtime.database import open_service_store
    return open_service_store(config)


def main(argv=None, *, open_store=_store):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--config', required=True, help='a service config with database settings and run_id')
    parser.add_argument('--anchors-dir', required=True)
    parser.add_argument('--run', help='run ID; default is the config run_id')
    args = parser.parse_args(argv)
    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    report, code = check(open_store(config), args.run or config['run_id'], args.anchors_dir)
    print(json.dumps(report, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())

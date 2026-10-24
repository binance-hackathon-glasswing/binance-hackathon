"""Merge a decisions export into the dashboard's monitor folder (IDEA-087 DX).

  python -m tools.dashboard.decisions merge results/decisions-export-stdout.txt --monitor-dir deploy/activation/rehearsal-monitor

The export (tools/dashboard/decisions-export.sh, run over SSM) prints the latest rounds only, so each merge adds its
rounds to <monitor dir>/decisions.jsonl, keyed by round ID: a newer export of a round (for example once it has closed)
replaces the older one. Lines that are not decision rows are skipped and counted. The file is rewritten sorted and
atomically, so the same input always gives the same bytes.
"""
import argparse
import json
import os
from pathlib import Path

FILE = 'decisions.jsonl'
CURSOR = 'decisions-cursor.json'  # the last event sequence an incremental export covered (IDEA-092 E2)
SCHEMA = 'LarpDecisionExport.v1'


def parse(text):
    """Decision rows of an export's stdout, and counts of what was skipped."""
    rows, _, report = parse_all(text)
    return rows, report


def parse_all(text):
    """Decision rows and closure lines of an export's stdout, and counts of what was skipped."""
    rows, closures, report = [], [], dict(decisions=0, closures=0, summary=None, skipped=0)
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            row = None
        if not isinstance(row, dict) or row.get('schema') != SCHEMA:
            report['skipped'] += 1
        elif row.get('section') == 'decisions_summary':
            report['summary'] = {k: row.get(k) for k in ('rounds', 'exported', 'closed')}
            for key in ('omitted_for_size', 'since', 'last_seq', 'complete'):
                if key in row:
                    report['summary'][key] = row[key]
        elif row.get('section') == 'decision' and isinstance(row.get('round_id'), str):
            rows.append(row)
            report['decisions'] += 1
        elif row.get('section') == 'closure' and isinstance(row.get('round_id'), str):
            closures.append(row)
            report['closures'] += 1
        else:
            report['skipped'] += 1
    return rows, closures, report


def order(row):
    seq = row.get('seq')
    return (seq if type(seq) is int else -1, row['round_id'])


def newer(new, old):
    """A later export of the same round wins; a closed status is never lost to an older open copy."""
    if old is None:
        return new
    if (order(new)[0], new.get('status') is not None) < (order(old)[0], old.get('status') is not None):
        return old
    return new


def cursor(monitor_dir):
    """The sequence the next incremental export starts after (0 before the first)."""
    try:
        value = json.loads((Path(monitor_dir) / CURSOR).read_text()).get('since')
    except (OSError, ValueError, AttributeError):
        return 0
    return value if type(value) is int and value >= 0 else 0


def merge(export_text, monitor_dir):
    folder = Path(monitor_dir)
    path = folder / FILE
    current = {}
    if path.is_file():
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and isinstance(row.get('round_id'), str):
                current[row['round_id']] = row
    rows, closures, report = parse_all(export_text)
    before = len(current)
    for row in rows:
        current[row['round_id']] = newer(row, current.get(row['round_id']))
    report['orphan_closures'] = 0
    for closure in closures:  # a round planned in an earlier export closed in this one
        planned = current.get(closure['round_id'])
        if planned is None:
            report['orphan_closures'] += 1
        elif planned.get('status') is None:
            current[closure['round_id']] = dict(planned, status=closure.get('status'))
    text = ''.join(json.dumps(r, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in sorted(current.values(), key=order))
    folder.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(FILE + '.tmp')
    tmp.write_text(text)
    os.replace(tmp, path)
    last = (report['summary'] or {}).get('last_seq')
    if type(last) is int and last > cursor(folder):
        (folder / CURSOR).write_text(json.dumps(dict(since=last), sort_keys=True) + '\n')
    report.update(rounds=len(current), added=len(current) - before, file=str(path), since=cursor(folder))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    m = sub.add_parser('merge', help='merge an export into <monitor dir>/decisions.jsonl')
    m.add_argument('export', help='stdout of tools/dashboard/decisions-export.sh (results/decisions-export-stdout.txt)')
    m.add_argument('--monitor-dir', required=True, help='chain-monitor output folder (LARP_MONITOR_DIR)')
    args = ap.parse_args()
    print(json.dumps(merge(Path(args.export).read_text(), args.monitor_dir), sort_keys=True))


if __name__ == '__main__':
    main()

# LD12-M01 read-only collection (IDEA-066 LD12-M01): delivery/cycle/archive/restart/resource/clock raw numbers.
# Run on primary only, never the signer. Prints the sanitized packet (gzip+base64 of two JSON lines: host, database)
# and its SHA-256. Writes nothing, not even a temp file (output passes through shell variables). No unit, file,
# config, ledger or AWS change: SQL runs in READ ONLY transactions; host reads use systemctl show, journalctl, du, df,
# chronyc tracking and free. Raw numbers only; no event IDs, addresses, endpoints or secrets.
set -eu
cd /opt/larp/current
HOST_JSON=$(env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
import json, re, subprocess, time
from pathlib import Path

UNITS = ('larp-runtime', 'larp-evidence', 'larp-uploader', 'larp-execution', 'larp-archive.service',
         'larp-archive.timer', 'larp-signer')
PROPS = ('LoadState', 'ActiveState', 'SubState', 'UnitFileState', 'NRestarts', 'MemoryCurrent', 'MemoryPeak', 'MemoryMax',
         'MemoryHigh', 'MemorySwapMax', 'CPUUsageNSec', 'ExecMainStartTimestamp', 'WatchdogUSec', 'Restart',
         'RestartUSec')
SINCE = '2026-10-18 16:00:00 UTC'
PATTERNS = dict(oom=r'out of memory|oom-kill|oom_reaper|killed process', watchdog=r'watchdog',
                main_exit=r'main process exited', scheduled_restart=r'scheduled restart job',
                started=r'^started |started larp', failed=r'failed with result')


def run(*args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        raise ValueError('HOST_READ_FAILED') from None
    if result.returncode != 0:
        absent_signer = (args[:3] == ('systemctl', 'show', 'larp-signer')
                         and 'LoadState=not-found' in result.stdout.splitlines()
                         and 'ActiveState=inactive' in result.stdout.splitlines())
        if not absent_signer:
            raise ValueError('HOST_READ_FAILED')
    return result.stdout


try:
    x = dict(section='host', checked_at_ms=time.time_ns() // 1000000, units={}, journal={})
    for unit in UNITS:
        out = run('systemctl', 'show', unit, *[f'-p{p}' for p in PROPS])
        x['units'][unit] = dict(line.split('=', 1) for line in out.splitlines() if '=' in line)
    for unit in UNITS[:5]:
        text = run('journalctl', '-u', unit, '--since', SINCE, '--no-pager', '-o', 'cat').lower().splitlines()
        x['journal'][unit] = dict(lines=len(text), **{k: sum(bool(re.search(p, line)) for line in text)
                                                     for k, p in PATTERNS.items()})
    kernel = run('journalctl', '-k', '--since', SINCE, '--no-pager', '-o', 'cat').lower().splitlines()
    x['journal']['kernel'] = dict(lines=len(kernel), oom=sum(bool(re.search(PATTERNS['oom'], l)) for l in kernel))
    with subprocess.Popen(['journalctl', '--no-pager', '-q', '-o', 'short-iso'], stdout=subprocess.PIPE, text=True) as p:
        x['journal']['oldest_entry'] = (re.match(r'^\d{4}-\d{2}-\d{2}T[0-9:.+-]+', p.stdout.readline()) or [''])[0]
        p.kill()
    x['journal']['disk_usage'] = run('journalctl', '--disk-usage').strip()
    x['disk'] = {}
    for d in sorted(Path('/var/lib').glob('larp*')) + [Path('/var/log/journal')]:
        out = run('du', '-sb', str(d)).split()
        x['disk'][str(d)] = int(out[0]) if out and out[0].isdigit() else None
    df = run('df', '-B1', '--output=size,used,avail', '/').split()
    x['disk']['root_fs'] = dict(zip(('size', 'used', 'avail'), map(int, df[3:6]))) if len(df) >= 6 else None
    mem = run('free', '-b').split()
    x['memory'] = dict(total=int(mem[7]), used=int(mem[8]), available=int(mem[12])) if len(mem) > 12 else None
    swap = [l.split() for l in run('free', '-b').splitlines() if l.lower().startswith('swap')]
    x['memory_swap_total'] = int(swap[0][1]) if swap else None
    x['nproc'] = run('nproc').strip()
    x['boot'] = run('uptime', '-s').strip()
    x['systemd_version'] = run('systemctl', '--version').splitlines()[0] if run('systemctl', '--version') else None
    tracking = run('chronyc', 'tracking')
    keep = ('Stratum', 'System time', 'Last offset', 'RMS offset', 'Leap status', 'Skew', 'Update interval')
    x['chrony'] = {k.strip(): v.strip() for k, v in (l.split(':', 1) for l in tracking.splitlines() if ':' in l)
                   if k.strip() in keep}
    uploader = json.loads(Path('/etc/larp/uploader.json').read_bytes())
    x['uploader'] = {k: uploader.get(k) for k in ('retry_ms', 'max_backoff_ms', 'interval_seconds', 'batch', 'run_id',
                                                  'build_id', 'mode')}
    operations = json.loads(Path('/etc/larp/operations.json').read_bytes())
    x['operations'] = {k: operations.get(k) for k in ('run_id', 'build_id', 'database_name', 'backup_interval_hours',
                                                      'retry_seconds', 'max_attempts')}
    runtime = json.loads(Path('/etc/larp/runtime.json').read_bytes())
    x['runtime'] = {k: runtime.get(k) for k in ('run_id', 'build_id', 'mode')}
    x['runtime']['execution'] = (runtime.get('driver') or {}).get('execution')
    print(json.dumps(x, sort_keys=True))
except Exception:
    print(json.dumps(dict(error='LD12_REFUSED', reason='HOST_READ_FAILED')))
    raise SystemExit(2)

PY
)
DB_JSON=$(sudo -u larp-archive env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
from contextlib import contextmanager
from pathlib import Path
import json, time
from larp.runtime.database import IamPostgresStore, rds_client


class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY')
            yield db


c = json.loads(Path('/etc/larp/operations.json').read_text())
store, run_id = RO(c, rds_client(c['region'])), c['run_id']
x = dict(section='database', checked_at_ms=time.time_ns() // 1000000, errors={})


def q(name, sql, params=(run_id,), shape=None):
    try:
        with store.transaction() as db:
            rows = db.execute(sql, params).fetchall()
        x[name] = [list(r) for r in rows] if shape is None else shape(rows)
    except Exception as error:
        x['errors'][name] = type(error).__name__


q('run', 'SELECT version, quarantined, epoch, clock_ms FROM runs WHERE run_id=%s')
q('sessions', 'SELECT started_ms, heartbeat_ms, ended_ms, build_id FROM process_sessions WHERE run_id=%s '
              'ORDER BY started_ms')
q('chunks', 'SELECT a.timestamp_ms, c.chunk_index, c.attempts, c.next_ms, c.status, c.last_code, '
            'c.acknowledgement IS NOT NULL, dense_rank() OVER (ORDER BY a.event_id) FROM audit_chunks c JOIN audit_events a USING (run_id, event_id) '
            'WHERE c.run_id=%s ORDER BY a.timestamp_ms, c.chunk_index')
q('ack_body_keys', 'SELECT acknowledgement FROM audit_chunks WHERE run_id=%s AND acknowledgement IS NOT NULL LIMIT 1',
  shape=lambda rows: sorted(set(json.loads(bytes(rows[0][0]))) & {'status', 'eventId', 'chunkIndex'}) if rows else [])
q('anchors', 'SELECT sequence, stored_ms FROM anchors WHERE run_id=%s ORDER BY sequence')
q('archive', 'SELECT kind, slot_ms, status, attempts, next_ms, (last_error IS NOT NULL AND last_error <> \'\') '
             'FROM archive_outbox WHERE run_id=%s ORDER BY kind, slot_ms')
q('jobs', 'SELECT lane, status, attempts, count(*) FROM jobs WHERE run_id=%s GROUP BY 1, 2, 3 ORDER BY 1, 2, 3')
q('rounds', 'SELECT status, count(*) FROM rounds WHERE run_id=%s GROUP BY 1')
q('db_size', 'SELECT pg_database_size(current_database())', params=(), shape=lambda rows: rows[0][0])
q('tables', "SELECT relname, pg_total_relation_size(c.oid) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE relkind='r' AND nspname='public' ORDER BY 2 DESC LIMIT 12", params=())


def events(rows):
    """Per round: start, decision, assessment start/complete and log time; plus event-kind counts."""
    rounds, kinds = {}, {}
    for sequence, raw in rows:
        event = (json.loads(bytes(raw)).get('event') or {})
        kind = event.get('kind', '?')
        kinds[kind] = kinds.get(kind, 0) + 1
        record = event.get('record') or {}
        rid = record.get('round_id') or event.get('round_id')
        if not rid:
            continue
        r = rounds.setdefault(rid, dict(sequence=sequence))
        if kind in ('ROUND_PLANNED', 'PLAN_REJECTED', 'ROUND_CLOSED') and record:
            a = record.get('assessment') or {}
            r.update(kind=kind, started_ms=record.get('started_ms'), decision_ms=record.get('decision_ms'),
                     assessment_started_ms=a.get('started_ms'), assessment_completed_ms=a.get('completed_ms'),
                     round_kind=record.get('round_kind'), intents=len((record.get('plan') or {}).get('intents') or []))
        if kind == 'ROUND_LOGGED':
            r['logged_ms'] = event.get('at_ms')
    return dict(kinds=kinds, rounds=rounds)


q('events', 'SELECT sequence, batch FROM events WHERE run_id=%s ORDER BY sequence', shape=events)
q('audit_times', 'SELECT round_id, timestamp_ms FROM audit_events WHERE run_id=%s ORDER BY timestamp_ms',
  shape=lambda rows: rows)
if 'events' in x and 'audit_times' in x:
    # Attach each round's log time, then drop round IDs from the output.
    for rid, ms in x['audit_times']:
        x['events']['rounds'].setdefault(rid, {})['log_ms'] = ms
    x['audit_times'] = sorted(ms for _, ms in x['audit_times'])
if 'events' in x:
    x['events']['rounds'] = list(x['events']['rounds'].values())
x['run_id'], x['database_name'] = run_id, c.get('database_name')
print(json.dumps(x, sort_keys=True, default=str))
PY
)
HOST_JSON="$HOST_JSON" DB_JSON="$DB_JSON" env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'
import base64, gzip, hashlib, json, os, re
from pathlib import Path
from urllib.parse import urlsplit


def refuse(reason):
    print(json.dumps(dict(error='LD12_REFUSED', reason=reason)))
    raise SystemExit(2)


try:
    host, db = os.environ['HOST_JSON'].strip(), os.environ['DB_JSON'].strip()
    h, d = json.loads(host), json.loads(db)
    c = json.loads(Path('/etc/larp/operations.json').read_bytes())
    runtime = json.loads(Path('/etc/larp/runtime.json').read_bytes())
    forbidden = []
    def private_values(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, str) and re.search(r'host|wallet|url|dsn|secret|password|credential|api_key|authorization', key, re.I):
                    if child:
                        forbidden.append(child)
                        if child.startswith('0x'): forbidden.append(child[2:])
                        if '://' in child:
                            forbidden.append(urlsplit(child).hostname or '')
                private_values(child)
        elif isinstance(value, list):
            for child in value: private_values(child)
    private_values(c)
    private_values(runtime)
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, child in value.items():
                yield str(key)
                yield from strings(child)
        elif isinstance(value, list):
            for child in value: yield from strings(child)
    for text in (host, db, *strings(h), *strings(d)):
        if '://' in text or any(f and f.lower() in text.lower() for f in forbidden):
            refuse('SANITIZER')
    if any(type(row[-1]) is not bool for row in d.get('archive', [])):
        refuse('FREE_FORM_ERROR')
    expected_run = 'larp-dev-llm-trial-20261018t170339z'
    expected_build = 'ea25b52325656a19b29e8ddb07b94dd792be6e18'
    expected_db = 'larp_trial2'
    if (any(h['units'].get(u, {}).get('ActiveState') != 'inactive' for u in
            ('larp-runtime', 'larp-evidence', 'larp-uploader', 'larp-execution', 'larp-archive.service',
             'larp-archive.timer', 'larp-signer'))
            or any(v.get('run_id') != expected_run for v in
                   (h['runtime'], h['uploader'], h['operations'], d, runtime, c))
            or any(v.get('build_id') != expected_build or v.get('mode') != 'dev'
                   for v in (h['runtime'], h['uploader'], runtime))
            or h['runtime'].get('execution') != 'shadow'
            or (runtime.get('driver') or {}).get('execution') != 'shadow'
            or h['operations'].get('database_name') != expected_db
            or d.get('database_name') != expected_db or c.get('database_name') != expected_db
            or len(d.get('run', [])) != 1):
        refuse('UNEXPECTED_STATE')
    packet = (host + '\n' + db).encode()
    print(json.dumps(dict(packet_gzip_b64=base64.b64encode(gzip.compress(packet, mtime=0)).decode(),
                         packet_sha256=hashlib.sha256(packet).hexdigest(), bytes=len(packet))))
except Exception:
    refuse('INVALID_PACKET')
PY

# Read-only #92 check (IDEA-055 RPC-H03): this process's balance checks and the balances_ok gate its rounds recorded.
set -eu
cd /opt/larp/current
echo "larp-runtime $(systemctl show larp-runtime -p MainPID -p ActiveEnterTimestamp -p NRestarts | tr '\n' ' ')"
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from datetime import datetime, timezone
import json


def iso(ms):
    return None if ms is None else datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec='milliseconds')[:-6] + 'Z'


def load(b):
    try: return json.loads(bytes(b))
    except Exception: return None


def summarize(rows, start_ms, keep=8):
    """rows: (sequence, batch) oldest first. Only IDs, times, statuses, short hashes and gate booleans are kept."""
    checks, rounds = [], []
    for q, b in rows:
        e = (load(b) or {}).get('event') or {}
        if e.get('kind') == 'BALANCE_CHECKED':
            check = e.get('check') or {}
            checks.append(dict(seq=q, checked_utc=iso(e.get('checked_ms')), status=check.get('status'),
                               reason=check.get('reason'), block=check.get('block_number'),
                               observation=(e.get('observation_sha256') or '')[:16],
                               this_process=(e.get('checked_ms') or 0) >= start_ms))
        elif e.get('kind') == 'ROUND_PLANNED':
            rec = e.get('record') or {}
            health = ((rec.get('policy_input') or {}).get('context') or {}).get('health')
            ms = rec.get('decision_ms', rec.get('started_ms'))
            rounds.append(dict(seq=q, round_id=str(rec.get('round_id'))[:80], decided_utc=iso(ms),
                               this_process=(ms or 0) >= start_ms,
                               health=None if not isinstance(health, dict) else
                               {k: v for k, v in health.items() if isinstance(v, bool)}))
    return dict(balance_checks=checks[-keep:], rounds=rounds[-keep:])


if __name__ == '__main__':
    from contextlib import contextmanager
    from pathlib import Path
    import subprocess, time
    from larp.runtime.database import IamPostgresStore, rds_client

    class RO(IamPostgresStore):
        @contextmanager
        def transaction(self):
            with super().transaction() as db:
                db.execute('SET TRANSACTION READ ONLY'); yield db

    c = json.loads(Path('/etc/larp/runtime.json').read_text()); r = c['run_id']
    entered = int(subprocess.run(['systemctl', 'show', 'larp-runtime', '-p', 'ActiveEnterTimestampMonotonic', '--value'],
                                 capture_output=True, text=True, check=True).stdout.strip())
    # Wall-clock process start: now minus the time since the unit entered "active" (both clocks in microseconds).
    now_ms = time.time_ns() // 1000000
    start_ms = now_ms - (time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1000 - entered) // 1000
    with RO(c, rds_client(c['region'])).transaction() as db:
        rows = db.execute('SELECT sequence,batch FROM events WHERE run_id=%s ORDER BY sequence DESC LIMIT 1500',
                          (r,)).fetchall()
    x = dict(now_utc=iso(now_ms), run_id=r, build_id=c.get('build_id'), process_start_utc=iso(start_ms),
             **summarize(list(reversed(rows)), start_ms))
    print(json.dumps(x, sort_keys=True))
PY

# Read-only #92 check (IDEA-055 RPC-H03): this process's balance checks and the balances_ok gate its rounds recorded.
set -eu
cd /opt/larp/current
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


def process_state():
    import re
    import subprocess
    keys = ('ActiveState', 'SubState', 'MainPID', 'InvocationID',
            'ExecMainStartTimestampMonotonic', 'NRestarts')
    output = subprocess.run(['systemctl', 'show', 'larp-runtime', '--no-pager',
                             '--property=' + ','.join(keys)], capture_output=True,
                            text=True, check=True, timeout=10).stdout
    state = dict(line.split('=', 1) for line in output.splitlines() if '=' in line)
    if (set(state) != set(keys) or state['ActiveState'] != 'active'
            or state['SubState'] != 'running'
            or not state['MainPID'].isdigit() or int(state['MainPID']) <= 0
            or not re.fullmatch(r'[0-9a-f]{32}', state['InvocationID'])
            or not state['ExecMainStartTimestampMonotonic'].isdigit()
            or int(state['ExecMainStartTimestampMonotonic']) <= 0
            or not state['NRestarts'].isdigit()):
        raise ValueError('PROCESS_IDENTITY_REQUIRED')
    return state


def inspect_process(c, read_state, read_rows, clocks):
    before = read_state()
    now_ms, monotonic_us = clocks()
    entered = int(before['ExecMainStartTimestampMonotonic'])
    if entered > monotonic_us:
        raise ValueError('PROCESS_START_INVALID')
    start_ms = now_ms - (monotonic_us - entered) // 1000
    rows = read_rows(c)
    if before != read_state():
        raise ValueError('PROCESS_CHANGED')
    return dict(now_utc=iso(now_ms), run_id=c['run_id'], build_id=c.get('build_id'),
                process=before, process_identity_stable=True, process_start_utc=iso(start_ms),
                **summarize(list(reversed(rows)), start_ms))


def main():
    from contextlib import contextmanager
    from pathlib import Path
    import time
    from larp.runtime.database import IamPostgresStore, rds_client

    class RO(IamPostgresStore):
        @contextmanager
        def transaction(self):
            with super().transaction() as db:
                db.execute('SET TRANSACTION READ ONLY'); yield db

    def read_rows(c):
        with RO(c, rds_client(c['region'])).transaction() as db:
            return db.execute(
                'SELECT sequence,batch FROM events WHERE run_id=%s ORDER BY sequence DESC LIMIT 1500',
                (c['run_id'],)).fetchall()

    config_path = Path('/etc/larp/runtime.json')
    raw = config_path.read_bytes()
    c = json.loads(raw)
    result = inspect_process(c, process_state, read_rows,
                             lambda: (time.time_ns() // 1000000,
                                      time.clock_gettime_ns(time.CLOCK_MONOTONIC) // 1000))
    if config_path.read_bytes() != raw:
        raise ValueError('CONFIG_CHANGED')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Do not emit config content, database exceptions or partial attribution.
        print(json.dumps(dict(error='BALANCE_HEALTH_REFUSED', process_identity_stable=False)))
        raise SystemExit(2)
PY

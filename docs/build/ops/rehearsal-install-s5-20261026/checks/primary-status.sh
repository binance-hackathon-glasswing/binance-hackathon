# Read-only (primary): unit states, the services' fixed JSON status lines and the archive health of the run.
#   python3.12 -I ssm_run.py checks/primary-status.sh
set -eu
for u in larp-evidence larp-uploader larp-runtime larp-execution larp-archive.timer; do
  echo "$u $(systemctl is-active $u || true) restarts=$(systemctl show $u -p NRestarts --value)"
done
for u in larp-runtime larp-execution; do
  echo "== $u (last JSON lines)"
  journalctl -u $u --since "-30 min" --no-pager -o cat | grep -E '^\{' | tail -5 || true
done
cd /opt/larp/current
sudo -u larp-archive env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from contextlib import contextmanager
from pathlib import Path
import json, time
from larp.runtime.database import IamPostgresStore, rds_client
from larp.runtime.maintenance import Maintenance, HOUR_MS
class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY'); yield db
try:
    c = json.loads(Path('/etc/larp/operations.json').read_text()); s = RO(c, rds_client(c['region']))
    now = time.time_ns() // 1000000
    h = Maintenance(s, None, backup_interval_ms=c['backup_interval_hours'] * HOUR_MS).health(c['run_id'], now).read()
    x = dict(run_id=c['run_id'], checked_at_ms=now, healthy=h.get('healthy'), reasons=h.get('reasons'))
    with s.transaction() as db:
        x['archive_tasks'] = [dict(kind=r[0], status=r[1], count=r[2]) for r in db.execute(
            'SELECT kind,status,count(*) FROM archive_outbox WHERE run_id=%s GROUP BY kind,status ORDER BY kind,status',
            (c['run_id'],)).fetchall()]
    print(json.dumps(x, sort_keys=True))
except Exception as e:
    print(json.dumps({'status': 'REFUSED', 'error_type': type(e).__name__})); raise SystemExit(4)
PY

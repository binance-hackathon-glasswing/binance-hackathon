# Read-only (primary; IDEA-100 DB2): the 15 statements that used the most database time since the statistics were last
# reset, from pg_stat_statements. One READ ONLY transaction as larp_execution. Query texts are normalised by the
# extension (constants as $1, $2 ...) and cut to 160 characters, so no parameter values are printed. Before the
# extension exists (DB2: parameter group, one reboot, then the admin creates the extension) it prints "n/a UndefinedTable".
# Without pg_read_all_stats, other roles' query texts show as "<insufficient privilege>"; the timings still count.
#   python3.12 -I ssm_run.py checks/db-top-queries.sh      (then read results/db-top-queries-stdout.txt)
set -eu
cd /opt/larp/current
runuser -u larp-execution -- env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from contextlib import contextmanager
from pathlib import Path
import json
from larp.runtime.database import IamPostgresStore, rds_client
class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY'); yield db
c = json.loads(Path('/etc/larp/execution.json').read_text())
s = RO(c, rds_client(c['region']))
out = {}
with s.transaction() as db:
    db.execute("SET LOCAL statement_timeout = '30s'")
    try:
        with db.transaction():
            total = db.execute('SELECT sum(total_exec_time) FROM pg_stat_statements').fetchone()[0] or 0
            rows = db.execute(
                'SELECT calls, total_exec_time, mean_exec_time, rows, left(query, 160) FROM pg_stat_statements '
                'ORDER BY total_exec_time DESC LIMIT 15').fetchall()
        out['total_ms'] = round(float(total), 1)
        out['top'] = [dict(calls=n, total_ms=round(float(t), 1), mean_ms=round(float(m), 2), rows=r,
                           share_pct=round(100 * float(t) / float(total), 1) if total else None, query=q)
                      for n, t, m, r, q in rows]
    except Exception as e:
        out['top'] = 'n/a ' + type(e).__name__
print(json.dumps(out, indent=1, default=str))
PY
echo TOP_QUERIES_DONE

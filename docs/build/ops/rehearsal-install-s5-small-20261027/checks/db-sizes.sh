# Read-only (primary; SJ-06 J8 incident): how big the run's data has grown. Database and per-table sizes, row counts
# for the largest tables, archive_outbox rows by kind/status with payload sizes, and the events table's size. One READ ONLY
# transaction as larp_execution; prints sizes and counts only, never row contents.
#   python3.12 -I ssm_run.py checks/db-sizes.sh            (then read results/db-sizes-stdout.txt)
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
c = json.loads(Path('/etc/larp/execution.json').read_text()); r = c['run_id']
s = RO(c, rds_client(c['region']))
out = {}
with s.transaction() as db:
    db.execute("SET LOCAL statement_timeout = '60s'")
    def q(name, sql, params=(), shape=lambda rows: rows):
        # Each query in its own savepoint, so a missing grant on one table does not abort the rest.
        try:
            with db.transaction():
                out[name] = shape(db.execute(sql, params).fetchall())
        except Exception as e:
            out[name] = 'n/a ' + type(e).__name__
    mb = lambda b: round(float(b or 0) / 2**20, 2)
    q('database_mb', 'SELECT pg_database_size(current_database())', shape=lambda x: mb(x[0][0]))
    q('shared_buffers', "SELECT current_setting('shared_buffers')", shape=lambda x: x[0][0])
    q('tables_mb', 'SELECT relname, pg_total_relation_size(relid) FROM pg_stat_user_tables ORDER BY 2 DESC LIMIT 12',
      shape=lambda x: {t: mb(b) for t, b in x})
    q('live_rows', 'SELECT relname, n_live_tup FROM pg_stat_user_tables '
      'ORDER BY pg_total_relation_size(relid) DESC LIMIT 12', shape=dict)
    q('archive_outbox', 'SELECT kind, status, count(*), sum(octet_length(payload)) FROM archive_outbox '
      'WHERE run_id=%s GROUP BY kind, status ORDER BY kind, status', (r,),
      shape=lambda x: [dict(kind=k, status=st, rows=n, payload_mb=mb(b)) for k, st, n, b in x])
    q('events', 'SELECT count(*), sum(octet_length(batch) + octet_length(receipt)) FROM events WHERE run_id=%s', (r,),
      shape=lambda x: dict(rows=x[0][0], bytes_mb=mb(x[0][1])))
print(json.dumps(out, indent=1, default=str))
PY
echo SIZES_DONE

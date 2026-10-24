# Read-only (primary; IDEA-087 DR): the transaction hashes in this run's execution records, one per line, then a
# summary. One READ ONLY transaction. Prints public chain identifiers only; used to seed a new chain monitor.
#   python3.12 -I ssm_run.py ../../../tools/dashboard/tx-export.sh     (from the copied run folder)
set -eu
cd /opt/larp/current
# larp_execution can SELECT every table read here (deploy/postgres/roles.sql); larp_runtime cannot.
runuser -u larp-execution -- env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
import json, re
from contextlib import contextmanager
from pathlib import Path
from larp.runtime.database import IamPostgresStore, rds_client
HASH = re.compile(r'^0x[0-9a-f]{64}$')
class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY'); yield db
c = json.loads(Path('/etc/larp/execution.json').read_text()); r = c['run_id']
s = RO(c, rds_client(c['region']))
with s.transaction() as db:
    states = [bytes(row[0]) for row in db.execute('SELECT state FROM execution_records WHERE run_id=%s', (r,)).fetchall()]
hashes = set()
for raw in states:
    try:
        state = json.loads(raw)
    except ValueError:
        continue
    for attempt in state.get('attempts') or []:
        h = str((attempt or {}).get('tx_hash') or '').lower()
        if HASH.match(h):
            hashes.add(h)
for h in sorted(hashes):
    print(json.dumps(dict(section='tx', tx_hash=h)))
print(json.dumps(dict(section='tx_summary', records=len(states), hashes=len(hashes))))
PY

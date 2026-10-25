# X1 (primary, read-only; IDEA-097 S4): export retired run 5's book as HoldingsCarryOver.v1 for run 6's starting state.
# Run right after R1p (run 5's units stopped and its configs moved to /etc/larp-history/) and before P2 (which replaces
# /opt/larp/current). One READ ONLY transaction as larp_execution; prints public values only (units, cost, hashes).
#   python3.12 -I ssm_run.py host/x1-export-holdings.sh        (then python3.12 -I mac/x1-save-export.py)
set -euo pipefail
RUN=larp-dev-rehearsal-20261025-s4; BUILD=7fc9f6019b54dccaf13b886c2e1123e703abf67a
H=/etc/larp-history/${BUILD:0:7}-$RUN
[[ -f $H/execution.json ]] || { echo "run 5 is not retired to $H (run R1p first)"; exit 3; }
for u in larp-execution larp-runtime larp-uploader larp-evidence; do
  state=$(systemctl is-active $u || true)
  [[ $state != active && $state != activating ]] || { echo "$u still running; retire run 5 first"; exit 3; }
done
cd /opt/larp/current
readlink -f /opt/larp/current | grep -q "${BUILD:0:12}" || { echo "/opt/larp/current is not run 5's build; export before P2"; exit 3; }
# /etc/larp-history is root-only (R1p), so root reads the config and hands it to larp-execution in the environment.
CONFIG_JSON=$(cat "$H/execution.json")
runuser -u larp-execution -- env PYTHONDONTWRITEBYTECODE=1 CONFIG_JSON="$CONFIG_JSON" RUN="$RUN" .venv/bin/python - <<'PY'
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, os
from larp.runtime.database import IamPostgresStore, rds_client
class RO(IamPostgresStore):
    @contextmanager
    def transaction(self):
        with super().transaction() as db:
            db.execute('SET TRANSACTION READ ONLY'); yield db
c = json.loads(os.environ['CONFIG_JSON'])
assert c['run_id'] == os.environ['RUN'], 'history config names another run'
s = RO(c, rds_client(c['region']))
with s.transaction() as db:
    version, projection = db.execute('SELECT version,projection FROM runs WHERE run_id=%s', (c['run_id'],)).fetchone()
    # The projection's portfolio never carries live reservations (ledger_from rebuilds them from this table), so the
    # in-flight check reads the table and the execution barrier itself.
    reserved = db.execute('SELECT intent_id,asset,units FROM reservations WHERE run_id=%s AND units<>0 '
                          'ORDER BY intent_id,asset', (c['run_id'],)).fetchall()
    unfinished = db.execute('SELECT count(*) FROM execution_records WHERE run_id=%s AND NOT terminal',
                            (c['run_id'],)).fetchone()[0]
raw = bytes(projection)
reservations = {}
for intent, asset, units in reserved:
    reservations.setdefault(intent, {})[asset] = int(units)
if unfinished:
    reservations['UNFINISHED_EXECUTION_RECORDS'] = {'count': int(unfinished)}  # refused by gate_a and X1-save
portfolio = json.loads(raw)['portfolio']
positions = {sym: dict(units=p['units'], decimals=p['decimals'], cost_basis_units=p['cost_basis_units'])
             for sym, p in sorted(portfolio['positions'].items())}
export = dict(schema='HoldingsCarryOver.v1', source_run_id=c['run_id'], wallet_id=portfolio['wallet_id'],
              source_version=version, projection_sha256=hashlib.sha256(raw).hexdigest(),
              reservations=reservations, positions=positions,
              exported_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
print('CARRY_OVER ' + json.dumps(export, sort_keys=True, separators=(',', ':')))
PY
echo X1_DONE

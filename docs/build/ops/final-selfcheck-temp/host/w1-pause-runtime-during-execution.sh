# W1 (primary, host mutation; IDEA-110 TA-02, the S5-COST03 workaround): while an execution record is non-terminal,
# stop larp-runtime so its journal writes cannot invalidate the executor's preparation CAS (StateVersionConflict ->
# approve, abort, zero revoke). Restart it once every record is terminal. Execution, signer, evidence and uploader keep
# running; nothing here signs, plans or sends. Loops for at most ${1:-25} minutes (SSM timeout 30 min), then leaves
# the runtime running. Prints times, states and record statuses only.
#   ssm_run.py host/w1-pause-runtime-during-execution.sh [minutes]
set -euo pipefail
MIN=${1:-25}; END=$(( $(date +%s) + MIN * 60 )); MAX_PAUSE=480
grep -q '"run_id": *"larp-final-selfcheck-temp"' /etc/larp/runtime.json || { echo "unexpected run"; exit 3; }
paused_by_me=0
cleanup() { if [[ $paused_by_me == 1 ]]; then systemctl start larp-runtime; echo "$(date -u +%T) runtime restarted (exit)"; fi; }
trap cleanup EXIT
active() {
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
with RO(c, rds_client(c['region'])).transaction() as db:
    rows = db.execute('SELECT economic_key, terminal FROM execution_records WHERE run_id=%s', (c['run_id'],)).fetchall()
print(sum(1 for _, t in rows if not t), len(rows))
PY
}
[[ $(systemctl is-active larp-execution) == active ]] || { echo "execution not active"; exit 5; }
since=0
while (( $(date +%s) < END )); do
  read -r open total < <(active)
  if [[ $open -gt 0 && $paused_by_me == 0 ]]; then
    systemctl stop larp-runtime; paused_by_me=1; since=$(date +%s)
    echo "$(date -u +%T) open=$open total=$total -> runtime paused"
  elif [[ $paused_by_me == 1 && ( $open == 0 || $(( $(date +%s) - since )) -gt $MAX_PAUSE ) ]]; then
    systemctl start larp-runtime; paused_by_me=0
    echo "$(date -u +%T) open=$open total=$total -> runtime restarted"
  fi
  sleep 2
done
echo "$(date -u +%T) loop ended; runtime $(systemctl is-active larp-runtime) execution $(systemctl is-active larp-execution) restarts=$(systemctl show larp-execution -p NRestarts --value)"
echo W1_DONE

# S5-COST02: finish only expired source-run8 work through its installed, registered code.
# No planning, signing, broadcasting, journal rewriting or fabricated settlement.
set -euo pipefail
[[ $(readlink -f /opt/larp/current) == /opt/larp/releases/bdd515f80dbc57e80ffeb60c6001091d6e1d7c08 ]]
for u in larp-runtime larp-execution; do
 state=$(systemctl is-active "$u" || true)
 [[ $state != active && $state != activating ]] || { echo "$u must be stopped"; exit 5; }
done
cd /opt/larp/current
runuser -u larp-runtime -- env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,time
from larp.contracts import Document
from larp.runtime.service import validate_config,open_store,verify_registered_manifest
from larp.runtime.preflight import verify_release,verify_runtime_config
from larp.runtime.coordinator import Coordinator
from larp.runtime.driver import ServiceExecution
raw=Path('/etc/larp/runtime.json').read_bytes();c=validate_config(json.loads(raw))
assert (c['run_id'],c['database_name'],c['build_id']) == ('larp-dev-rehearsal-20261027-s5-small','larp_rehearsal8','bdd515f80dbc57e80ffeb60c6001091d6e1d7c08')
manifest=Document(Path('/etc/larp/release.json').read_bytes());m=verify_release(manifest,Path.cwd())
verify_runtime_config(m,raw);assert m['build_id']==c['build_id']
s=open_store(c);verify_registered_manifest(s,c,manifest)
with s.transaction() as db:
 assert db.execute('SELECT count(*) FROM execution_records WHERE run_id=%s AND NOT terminal',(c['run_id'],)).fetchone()[0]==0
praw=Path(c['driver']['strategy_profile_file']).read_bytes()
assert hashlib.sha256(praw).hexdigest()==c['driver']['strategy_profile_sha256']
coordinator=Coordinator(s,None,None,None,execution=None,run_id=c['run_id'],version_id=c['build_id'],
 profile_hash=Document(praw).digest('StrategyProfile.v1'),address=c['wallet_address'],test_rounds=True,require_version=True)
execution=ServiceExecution(coordinator,wallet=c['wallet_address'],grace_ms=c['driver']['expiry_grace_ms'])
now=time.time_ns()//1000000
execution.settle_open(now);closed=coordinator.recover(now)
current=s.load(c['run_id']).read()
held=sum(r['units']>0 for r in current['reservations'])
open_rounds=len(s.open_rounds(c['run_id']))
print(json.dumps(dict(source_run=c['run_id'],expired=len(execution.expired),ingested=len(execution.ingested),
 refused=len(execution.refused),closed=len(closed),held_reservation_rows=held,open_rounds=open_rounds)))
assert held==0 and open_rounds==0
PY
echo SOURCE_RECONCILED

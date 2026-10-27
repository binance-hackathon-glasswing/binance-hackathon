# Run8 revision2 host start. Exact source/profile/identity/window must match before any start.
set -euo pipefail
umask 077

python3 - <<'WINDOW'
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
r=json.loads(Path('/etc/larp/runtime.json').read_text())
p=Path('/etc/larp/strategy-profile.json');v=json.loads(p.read_bytes())
ok=(r.get('run_id')=='larp-dev-rehearsal-20261027-s5-cost01' and r.get('database_name')=='larp_rehearsal8cost01'
    and r.get('build_id')=='3ae830981b9ce1c4b80a46dbeb086825d91ae7ec'
    and hashlib.sha256(p.read_bytes()).hexdigest()=='f26c332aad317631ee7308a6d7669761104e2b4f8d1864300a5d6ff40e487dec'
    and datetime.now(timezone.utc)<datetime.fromisoformat(v['new_risk_end'].replace('Z','+00:00')))
if not ok:sys.exit('s5-cost01 identity/profile/window refusal; no start')
WINDOW

state=$(systemctl is-active larp-execution || true)
restarts=$(systemctl show larp-execution -p NRestarts --value)
[[ $state == active && $restarts == 0 ]] || { echo "executor is not healthy; runtime not started"; exit 5; }
systemctl start larp-runtime
sleep 30
for u in larp-runtime larp-execution; do
  state=$(systemctl is-active "$u" || true); restarts=$(systemctl show "$u" -p NRestarts --value)
  echo "$u $state restarts=$restarts"
  [[ $state == active && $restarts == 0 ]] || { echo "a service is not healthy; no P6_DONE"; exit 5; }
done
echo P6_DONE

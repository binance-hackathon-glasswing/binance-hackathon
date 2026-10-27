# Run8 revision2 host start. Exact source/profile/identity/window must match before any start.
set -euo pipefail
umask 077

python3 - <<'WINDOW'
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
r=json.loads(Path('/etc/larp/runtime.json').read_text())
p=Path('/etc/larp/strategy-profile.json');v=json.loads(p.read_bytes())
ok=(r.get('run_id')=='larp-dev-rehearsal-20261027-s5-small-r2' and r.get('database_name')=='larp_rehearsal8r2'
    and r.get('build_id')=='a22527603ad34c545ff30b5ef996f575b3435b53'
    and hashlib.sha256(p.read_bytes()).hexdigest()=='1dbb52b12b6b8e379a1b3996d427b2ab83b520f98ec6275d29f536600f327e4c'
    and datetime.now(timezone.utc)<datetime.fromisoformat(v['new_risk_end'].replace('Z','+00:00')))
if not ok:sys.exit('run8r2 identity/profile/window refusal; no start')
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

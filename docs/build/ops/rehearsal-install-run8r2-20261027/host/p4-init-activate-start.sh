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

RUN=larp-dev-rehearsal-20261027-s5-small-r2
REVIEWER=${1:?reviewer name}; APPROVAL=${2:?IDEA-104 record of the run-8 approval}
REF="IDEA-104 S5: $APPROVAL; dev signed rehearsal $RUN, larp_rehearsal8r2, S5 1dbb52b1 FS1 routing+history"
[[ ${#REF} -le 200 ]] || { echo "review reference too long"; exit 3; }
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/runtime.json || { echo "unexpected runtime.json run"; exit 3; }
grep -q '"database_name": *"larp_rehearsal8r2"' /etc/larp/runtime.json || { echo "unexpected database"; exit 3; }
cd /opt/larp/current
P=".venv/bin/python"; export PYTHONDONTWRITEBYTECODE=1
AS_RT="runuser -u larp-runtime -g larp-runtime -G larp-evidence --"
[[ $(systemctl is-active larp-runtime || true) == inactive && $(systemctl is-active larp-execution || true) == inactive ]] \
  || { echo "runtime/execution already active; refusing initialization"; exit 5; }
$AS_RT $P -m larp.runtime.service init --config /etc/larp/runtime.json --manifest /etc/larp/release.json --root /opt/larp/current
$AS_RT $P -m larp.runtime.service activate --config /etc/larp/runtime.json --manifest /etc/larp/release.json \
  --root /opt/larp/current --reviewer "$REVIEWER" --review-ref "$REF"
systemctl start larp-evidence
sleep 5
systemctl start larp-uploader
systemctl start larp-archive.timer
sleep 30
bad=0
for u in larp-evidence larp-uploader larp-runtime larp-execution larp-archive.timer; do
  state=$(systemctl is-active $u || true); restarts=$(systemctl show $u -p NRestarts --value)
  echo "$u $state restarts=$restarts"
  # PR296-RV01: runtime and execution must still be off. A timer has
  # no NRestarts property (empty value), so it only has to be active (SJ-06 P4 finding).
  if [[ $u == larp-execution || $u == larp-runtime ]]; then [[ $state == inactive ]] || bad=1
  elif [[ $u == *.timer ]]; then [[ $state == active ]] || bad=1
  else [[ $state == active && $restarts == 0 ]] || bad=1; fi
done
[[ $bad == 0 ]] || { echo "a unit is not in its expected state; stop here (no P4_DONE)"; exit 5; }
echo P4_DONE

# P4 (primary, host mutation; FS1 FINAL run sheet): create and activate the FINAL run in larp_final, then start evidence
# and delivery only. Runtime stays off until S2 -> P5 -> P6: the executor must be healthy before the first intent.
# The activation self-check may buy before scored entries open on 2026-10-29 14:00 UTC.
# Flatten starts 2026-11-10 19:00 UTC; signing ends 2026-11-11 14:45 UTC (IDEA-093).
#   ssm_run.py host/p4-init-activate-start.sh "<reviewer>" "<IDEA-093 record of the FINAL approval>"
# The reviewer and approval reference are arguments: this sheet was drafted before the approval existed.
set -euo pipefail
RUN=larp-final-fs1
REVIEWER=${1:?reviewer name}; APPROVAL=${2:?IDEA-093 record of the FINAL approval}
REF="IDEA-093 FS1 FINAL: $APPROVAL; live FINAL $RUN, larp_final, FS1 FINAL b8ba06e2 FS1 routing+history"
[[ ${#REF} -le 200 ]] || { echo "review reference too long"; exit 3; }
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/runtime.json || { echo "unexpected runtime.json run"; exit 3; }
grep -q '"database_name": *"larp_final"' /etc/larp/runtime.json || { echo "unexpected database"; exit 3; }
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

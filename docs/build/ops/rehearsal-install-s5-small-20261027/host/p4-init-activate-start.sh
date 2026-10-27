# P4 (primary, host mutation; S5 run sheet): create and activate run 8 (S5) in larp_rehearsal8, then start evidence
# and delivery only. Runtime stays off until S2 -> P5 -> P6: the executor must be healthy before the first intent.
# S5-SMALL01 buys after2026-10-27 04:00UTC, stops new risk10:00UTC,
# sells all from11:00UTC (19:00SGT), and signs until15:00UTC (23:00SGT).
#   ssm_run.py host/p4-init-activate-start.sh "<reviewer>" "<IDEA-104 record of the run-8 approval>"
# The reviewer and approval reference are arguments: this sheet was drafted before the approval existed.
set -euo pipefail
RUN=larp-dev-rehearsal-20261027-s5-small
REVIEWER=${1:?reviewer name}; APPROVAL=${2:?IDEA-104 record of the run-8 approval}
REF="IDEA-104 S5: $APPROVAL; dev signed rehearsal $RUN, larp_rehearsal8, S5 10882b9a FS1 routing+history"
[[ ${#REF} -le 200 ]] || { echo "review reference too long"; exit 3; }
grep -q "\"run_id\": *\"$RUN\"" /etc/larp/runtime.json || { echo "unexpected runtime.json run"; exit 3; }
grep -q '"database_name": *"larp_rehearsal8"' /etc/larp/runtime.json || { echo "unexpected database"; exit 3; }
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
